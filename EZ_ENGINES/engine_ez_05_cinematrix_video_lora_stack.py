# -*- coding: utf-8 -*-

import json
import math
import os
import gc
from pathlib import Path
import torch
import folder_paths
import comfy.sd
import comfy.utils
import comfy.model_management
import comfy.ops
_H4_BASE = ((1.0, 1.0, 1.0, -1.0), (1.0, 1.0, -1.0, 1.0), (1.0, -1.0, 1.0, 1.0), (-1.0, 1.0, 1.0, 1.0))
_VIDEO_HADAMARD_CACHE = {}

def _get_video_convrot_hadamard(group_size: int, device, dtype=torch.float32):
    grp = int(group_size or 256)
    if grp < 4:
        return None
    key = (grp, str(device), str(dtype))
    if key in _VIDEO_HADAMARD_CACHE:
        return _VIDEO_HADAMARD_CACHE[key]
    h4 = torch.tensor(_H4_BASE, dtype=torch.float32, device=device)
    h = h4
    while h.shape[0] < grp:
        h = torch.kron(h, h4)
    if h.shape[0] != grp:
        return None
    h = (h / math.sqrt(float(grp))).to(dtype=dtype)
    _VIDEO_HADAMARD_CACHE[key] = h
    return h

_SAFETENSORS_SIG_CACHE = {}

def _load_sidecar_quant_metadata(fpath: str) -> dict:
    if not fpath:
        return {}
    p = Path(str(fpath))
    for cand in (p.with_suffix('.metadata.json'), Path(str(fpath) + '.metadata.json')):
        if cand.exists() and cand.is_file():
            try:
                data = json.loads(cand.read_text(encoding='utf-8', errors='ignore'))
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
    return {}

def _inspect_safetensors_header(fpath: str) -> dict:
    import struct as _st
    res = {'role': 'unknown', 'arch': '', 'needs_convrot_dequant': False}
    if not fpath or not str(fpath).lower().endswith(('.safetensors', '.sft')) or not os.path.exists(fpath):
        return res
    try:
        import importlib as _il
        try:
            q_ops_mod = _il.import_module('comfy.quant_ops')
        except Exception:
            q_ops_mod = getattr(comfy, 'quant_ops', None)
        comfy_native_algos = set(getattr(q_ops_mod, 'QUANT_ALGOS', {}).keys()) | set(getattr(q_ops_mod, 'LAYOUTS', {}).keys()) | {
            'float8_e4m3fn', 'float8_e5m2', 'int8_tensorwise', 'int8_blockwise',
            'nvfp4', 'mxfp8', 'asym_w4a8_int8', 'w6a8_int8', 'convrot_w4a4',
        }
        st = os.stat(fpath)
        ckey = (str(fpath), int(st.st_mtime_ns), int(st.st_size), len(comfy_native_algos))
        if ckey in _SAFETENSORS_SIG_CACHE:
            return _SAFETENSORS_SIG_CACHE[ckey]
        with open(fpath, 'rb') as fh:
            if st.st_size < 16:
                return res
            h_len = _st.unpack('<Q', fh.read(8))[0]
            if h_len <= 0 or h_len > 100_000_000 or (8 + h_len > st.st_size):
                return res
            h_obj = json.loads(fh.read(h_len).decode('utf-8', errors='ignore'))
            if not isinstance(h_obj, dict):
                return res
            meta = h_obj.get('__metadata__', {}) if isinstance(h_obj.get('__metadata__'), dict) else {}
            if '_quantization_metadata' not in meta:
                sidecar = _load_sidecar_quant_metadata(fpath)
                if '_quantization_metadata' in sidecar:
                    meta['_quantization_metadata'] = sidecar['_quantization_metadata']
                elif 'layers' in sidecar:
                    meta['_quantization_metadata'] = sidecar
            needs_convrot = False
            if '_quantization_metadata' in meta:
                try:
                    qm = json.loads(meta['_quantization_metadata']) if isinstance(meta['_quantization_metadata'], str) else meta['_quantization_metadata']
                    layers = qm.get('layers', qm) if isinstance(qm, dict) else {}
                    for l_cfg in (layers.values() if isinstance(layers, dict) else ()):
                        if isinstance(l_cfg, dict):
                            fmt = str(l_cfg.get('format', '') or '').lower()
                            if fmt in ('convrot_w4a4', 'asym_w4a8_int8', 'w6a8_int8', 'nvfp4', 'mxfp8'):
                                continue
                            has_crot = (bool(l_cfg.get('convrot', False)) or 'convrot' in fmt) and (fmt not in comfy_native_algos)
                            if has_crot or ('rowwise' in fmt and fmt not in comfy_native_algos) or (fmt and fmt not in comfy_native_algos):
                                needs_convrot = True
                                break
                except Exception:
                    pass
            t_keys = [k for k in h_obj.keys() if k != '__metadata__']
            fn_low = os.path.basename(str(fpath)).lower()
            if not needs_convrot and 'convrot' in fn_low and 'mixed_int4' not in fn_low and 'nvfp4' not in fn_low:
                if any((tk.endswith('.weight_scale') or (isinstance(h_obj.get(tk), dict) and h_obj[tk].get('dtype') == 'I8') for tk in t_keys[:128])):
                    needs_convrot = True
            cq_checked = 0
            for tk in t_keys:
                if tk.endswith(('hadamard_matrix', 'rot_matrix', 'rotation_matrix', 'hadamard')):
                    needs_convrot = True
                    break
                if not needs_convrot and tk.endswith('.comfy_quant') and cq_checked < 12:
                    offs = h_obj[tk].get('data_offsets') if isinstance(h_obj.get(tk), dict) else None
                    if isinstance(offs, (list, tuple)) and len(offs) >= 2 and 0 < (int(offs[1]) - int(offs[0])) <= 512:
                        fh.seek(8 + h_len + int(offs[0]))
                        raw_cq = bytes((b for b in fh.read(int(offs[1]) - int(offs[0])) if b != 0))
                        try:
                            cq_d = json.loads(raw_cq.decode('utf-8', errors='ignore').strip())
                            fmt = str(cq_d.get('format', '') or '').lower()
                            if fmt not in ('convrot_w4a4', 'asym_w4a8_int8', 'w6a8_int8', 'nvfp4', 'mxfp8'):
                                has_crot = (bool(cq_d.get('convrot', False)) or 'convrot' in fmt) and (fmt not in comfy_native_algos)
                                if has_crot or ('rowwise' in fmt and fmt not in comfy_native_algos) or (fmt and fmt not in comfy_native_algos):
                                    needs_convrot = True
                                    break
                        except Exception:
                            pass
                        cq_checked += 1
        res['needs_convrot_dequant'] = needs_convrot
        has_lora = any(('.lora_up' in k or '.lora_down' in k or '.lora_A' in k or '.hada_w1' in k for k in t_keys[:64]))
        has_diff = any(('double_blocks.' in k or 'single_blocks.' in k or 'patch_embedding.' in k or 'joint_blocks.' in k or 'down_blocks.' in k or 'input_blocks.' in k or 'condition_proj.' in k or 'audio_in.' in k or 'transformer_blocks.' in k for k in t_keys))
        has_vae = any(('decoder.conv_in' in k or 'encoder.conv_in' in k or 'first_stage_model.decoder' in k for k in t_keys))
        has_te = any(('text_model.' in k or 'model.layers.0.self_attn' in k or 'visual.blocks.0' in k or 'encoder.block.0.layer.0' in k or 'token_embd.weight' in k for k in t_keys))
        if has_lora and not has_diff:
            res['role'] = 'lora'
        elif has_vae and not has_diff:
            res['role'] = 'vae'
        elif has_te and not has_diff:
            res['role'] = 'text_encoder'
        elif has_diff:
            has_h3 = any(('condition_proj.' in k or 'audio_in.' in k or 'vid_in.' in k for k in t_keys))
            patch_5d_ch = 0
            for pk in ('patch_embedding.weight', 'model.diffusion_model.patch_embedding.weight', 'diffusion_model.patch_embedding.weight', 'img_in.proj.weight'):
                if pk in h_obj and isinstance(h_obj[pk], dict) and isinstance(h_obj[pk].get('shape'), list) and len(h_obj[pk]['shape']) == 5:
                    patch_5d_ch = int(h_obj[pk]['shape'][1])
                    break
            has_vid_attn = any(('temporal_transformer' in k or 'temp_attentions' in k or 'spatio_temporal' in k or 'txt_in.individual_token_refiner' in k or 'caption_projection' in k for k in t_keys))
            has_sdxl_unet = any(('model.diffusion_model.input_blocks.' in k or k.startswith('input_blocks.') or 'conditioner.embedders.1.' in k) for k in t_keys)
            if has_h3:
                res['role'] = 'video_unet'
                res['arch'] = 'minimax_h3'
            elif patch_5d_ch > 0:
                res['role'] = 'video_unet'
                res['arch'] = 'wan22' if patch_5d_ch >= 36 else 'wan21'
            elif has_vid_attn:
                res['role'] = 'video_unet'
                res['arch'] = 'hunyuan_video' if any('individual_token_refiner' in k for k in t_keys) else 'ltxv'
            elif has_sdxl_unet:
                res['role'] = 'image_unet'
                meta_blob = json.dumps(meta, ensure_ascii=False).lower() if isinstance(meta, dict) else ''
                if any((ik in fn_low or ik in meta_blob for ik in ('illustrious', 'ilxl', 'noobai', 'noob', 'wai-nsfw', 'wai_nsfw'))):
                    res['arch'] = 'illustrious'
                elif any((pk in fn_low or pk in meta_blob for pk in ('pony', 'pdxl', 'autismmix'))):
                    res['arch'] = 'pony'
                else:
                    res['arch'] = 'sdxl'
            else:
                res['role'] = 'image_unet'
                res['arch'] = 'flux'
        _SAFETENSORS_SIG_CACHE[ckey] = res
    except Exception:
        pass
    return res

def _resolve_candidate_model_path(rel_name: str) -> str:
    for fk in ('diffusion_models', 'unet', 'checkpoints', 'vae', 'text_encoders', 'clip'):
        if fk in folder_paths.folder_names_and_paths:
            p = folder_paths.get_full_path(fk, rel_name)
            if p and os.path.exists(p):
                return str(p)
    return ''

def _is_non_unet_or_image_only_for_video(rel_name: str) -> bool:
    r_low = str(rel_name or '').lower()
    b_low = os.path.basename(r_low)
    if b_low.endswith('.json') or any(tag in b_low for tag in ('_ez_fp8_e4m3fn_cache', '_ez_fp16_vae_cache', '_ez_hadamard_v2_fp8', '_ez_hadamard_v2_fp16_vae')):
        return True
    full_p = _resolve_candidate_model_path(rel_name)
    if full_p and full_p.lower().endswith(('.safetensors', '.sft')):
        sig = _inspect_safetensors_header(full_p)
        if sig['role'] in ('lora', 'vae', 'text_encoder', 'image_unet'):
            return True
        if sig['role'] == 'video_unet':
            return False
    if any((k in b_low for k in ('qwen3vl', 'qwen3-vl', 'qwen3_vl', 'qwen2.5-vl', 'qwen-vl', 'qwen_vl', 'huihui', 't5xxl', 'umt5', 'clip_l', 'clip_g', 'llava', 'mmproj', 'florence', 'text_encoder', '_vae', 'video_vae', 'audio_vae'))):
        return True
    if b_low in ('ae.safetensors', 'ae.sft', 'qwen_image_vae.safetensors', 'wan_2.1_vae.safetensors', 'wan_2.2_vae.safetensors', 'sdxl_vae.safetensors'):
        return True
    if any((ik in b_low for ik in ('krea', 'flux', 'sdxl', 'pony', 'illustrious', 'juggernaut', 'qwen_image', 'qwen-image'))) and not any((vk in r_low for vk in ('minimax', 'h3', 'fl2va', 'ref2va', 'singularity', 'prism', 'wan', 'ltx'))):
        return True
    return False


def get_dynamic_video_unets():
    models = []
    for k in ('diffusion_models', 'unet', 'checkpoints', 'unet_gguf'):
        if k in folder_paths.folder_names_and_paths:
            models.extend(folder_paths.get_filename_list(k))
    cleaned = sorted((m for m in set(models) if not _is_non_unet_or_image_only_for_video(m)))
    return cleaned if cleaned else ['None']

def get_dynamic_video_clips():
    clips = []
    for k in ('text_encoders', 'clip', 'clip_gguf'):
        if k in folder_paths.folder_names_and_paths:
            clips.extend(folder_paths.get_filename_list(k))
    cleaned = sorted(set(clips))
    return cleaned if cleaned else ['None']

def get_dynamic_video_vaes():
    vaes = folder_paths.get_filename_list('vae') if 'vae' in folder_paths.folder_names_and_paths else []
    cleaned = sorted((v for v in set(vaes) if not any(tag in str(v).lower() for tag in ('_ez_fp16_vae_cache', '_ez_hadamard_v2_fp16_vae'))))
    return ['None'] + cleaned if cleaned else ['None']

def get_dynamic_video_loras(lock_turbo_only: bool=False):
    all_loras = sorted(set(folder_paths.get_filename_list('loras'))) if 'loras' in folder_paths.folder_names_and_paths else []
    if not lock_turbo_only:
        return ['None'] + all_loras
    turbo_tokens = ('turbo', 'step', 'distill', 'hyper', 'lightning', 'fast')
    turbo_only = [l for l in all_loras if any((t in l.lower() for t in turbo_tokens))]
    return ['None'] + (turbo_only if turbo_only else all_loras)

def _parse_video_comfy_quant_tensor(cq_tensor) -> dict:
    if not isinstance(cq_tensor, torch.Tensor):
        return {}
    try:
        raw_bytes = bytes((b for b in cq_tensor.detach().cpu().to(dtype=torch.uint8).view(-1).tolist() if b != 0))
        return json.loads(raw_bytes.decode('utf-8', errors='ignore').strip())
    except Exception:
        return {}

def _pre_dequantize_video_convrot_state_dict(sd: dict, metadata: dict=None, model_path: str='', allow_fp8_cast: bool=False) -> bool:
    if not isinstance(sd, dict):
        return False
    meta_layers = {}
    if isinstance(metadata, dict) and '_quantization_metadata' in metadata:
        try:
            parsed_qm = json.loads(metadata['_quantization_metadata']) if isinstance(metadata['_quantization_metadata'], str) else metadata['_quantization_metadata']
            if isinstance(parsed_qm, dict):
                meta_layers = parsed_qm.get('layers', parsed_qm)
        except Exception:
            meta_layers = {}
    if not meta_layers and model_path:
        sidecar = _load_sidecar_quant_metadata(model_path)
        if isinstance(sidecar, dict):
            raw_qm = sidecar.get('_quantization_metadata', sidecar)
            if isinstance(raw_qm, str):
                try:
                    raw_qm = json.loads(raw_qm)
                except Exception:
                    raw_qm = {}
            if isinstance(raw_qm, dict):
                meta_layers = raw_qm.get('layers', raw_qm)
    import importlib as _il
    try:
        q_ops_mod = _il.import_module('comfy.quant_ops')
    except Exception:
        q_ops_mod = getattr(comfy, 'quant_ops', None)
    native_algos = set(getattr(q_ops_mod, 'QUANT_ALGOS', {}).keys()) | set(getattr(q_ops_mod, 'LAYOUTS', {}).keys()) | {
        'float8_e4m3fn', 'float8_e5m2', 'int8_tensorwise', 'int8_blockwise',
        'nvfp4', 'mxfp8', 'asym_w4a8_int8', 'w6a8_int8', 'convrot_w4a4',
    }
    bname_low = os.path.basename(str(model_path or '')).lower()
    file_name_has_convrot = 'convrot' in bname_low and 'mixed_int4' not in bname_low
    use_bf16 = hasattr(comfy.model_management, 'should_use_bf16') and comfy.model_management.should_use_bf16()
    fallback_fp16_dtype = torch.bfloat16 if use_bf16 else torch.float16
    fp8_dtype = getattr(torch, 'float8_e4m3fn', fallback_fp16_dtype) if allow_fp8_cast else fallback_fp16_dtype
    fp16_keep_tokens = (
        'patch_embedding', 'img_in', 'vid_in', 'audio_in', 'txt_in', 'condition_proj',
        'final_layer', 'proj_out', 'audio_out', 'norm', 'time_embed', 'vector_in',
        'guidance_in', 'modulation', 'adaln', 'embed',
    )
    calc_dev = comfy.model_management.get_torch_device() if torch.cuda.is_available() else torch.device('cpu')
    weight_keys = [k for k in list(sd.keys()) if k.endswith('.weight') or k == 'weight']
    modified = False
    for w_key in weight_keys:
        w_t = sd.get(w_key, None)
        if not isinstance(w_t, torch.Tensor) or w_t.dtype != torch.int8:
            continue
        prefix = w_key[:-6]
        layer_name = prefix[:-1] if prefix.endswith('.') else prefix
        cq_key = prefix + 'comfy_quant'
        q_cfg = _parse_video_comfy_quant_tensor(sd.get(cq_key, None))
        if not q_cfg and isinstance(meta_layers, dict):
            cand_m = (
                meta_layers.get(layer_name)
                or meta_layers.get(f'diffusion_model.{layer_name}')
                or meta_layers.get(f'model.diffusion_model.{layer_name}')
            )
            q_cfg = cand_m if isinstance(cand_m, dict) else {}
        q_fmt = str(q_cfg.get('format', '') or '').lower()
        if q_fmt in ('convrot_w4a4', 'asym_w4a8_int8', 'w6a8_int8', 'nvfp4', 'mxfp8') or 'w4' in q_fmt or 'int4' in q_fmt or 'fp4' in q_fmt:
            continue
        if q_fmt and q_fmt in native_algos and not bool(q_cfg.get('convrot', False)):
            continue
        scale_t = None
        for sc_suffix in ('weight_scale', 'scale_weight', 'weight.scale', 'scale'):
            if prefix + sc_suffix in sd and isinstance(sd[prefix + sc_suffix], torch.Tensor):
                scale_t = sd[prefix + sc_suffix]
                break
        has_rot_tensor = any((prefix + rs in sd for rs in ('hadamard_matrix', 'rot_matrix', 'rotation_matrix', 'hadamard')))
        layer_has_hadamard = (
            bool(q_cfg.get('convrot', False))
            or ('convrot' in q_fmt and q_fmt not in native_algos)
            or ('hadamard' in q_fmt)
            or has_rot_tensor
            or (file_name_has_convrot and q_cfg.get('convrot') is not False and not q_fmt and scale_t is not None)
        )
        unsupported_fmt = bool(q_fmt and q_fmt not in native_algos)
        layer_needs_dequant = layer_has_hadamard or ('rowwise' in q_fmt and q_fmt not in native_algos) or unsupported_fmt
        if not layer_needs_dequant:
            continue
        try:
            w_fp32 = w_t.detach().to(device=calc_dev, dtype=torch.float32)
        except Exception:
            calc_dev = torch.device('cpu')
            w_fp32 = w_t.detach().to(device=calc_dev, dtype=torch.float32)
        if isinstance(scale_t, torch.Tensor):
            sc = scale_t.detach().to(device=calc_dev, dtype=torch.float32)
            if sc.ndim == 1 and w_fp32.ndim >= 2 and (sc.numel() == w_fp32.shape[0]):
                sc = sc.reshape(w_fp32.shape[0], *[1] * (w_fp32.ndim - 1))
            elif sc.ndim == 2 and w_fp32.ndim > 2 and (sc.shape[0] == w_fp32.shape[0]):
                sc = sc.reshape(sc.shape[0], sc.shape[1], *[1] * (w_fp32.ndim - 2))
            w_fp32 = w_fp32 * sc
        explicit_rot = False
        for rot_suffix in ('hadamard_matrix', 'rot_matrix', 'rotation_matrix', 'hadamard'):
            rot_t = sd.get(prefix + rot_suffix, None)
            if isinstance(rot_t, torch.Tensor) and rot_t.ndim == 2 and (rot_t.shape[0] == rot_t.shape[1]):
                blk = int(rot_t.shape[0])
                rmat = rot_t.detach().to(device=calc_dev, dtype=torch.float32)
                if w_fp32.ndim == 2 and blk > 0 and (w_fp32.shape[1] % blk == 0):
                    w_fp32 = (w_fp32.reshape(w_fp32.shape[0], -1, blk) @ rmat.T).reshape(w_fp32.shape)
                    explicit_rot = True
                elif w_fp32.ndim >= 3 and blk > 0:
                    flat_in = int(w_fp32[0].numel())
                    if flat_in % blk == 0:
                        w_fp32 = (w_fp32.reshape(w_fp32.shape[0], -1, blk) @ rmat.T).reshape(w_fp32.shape)
                        explicit_rot = True
                break
        if not explicit_rot and layer_has_hadamard and (w_fp32.ndim >= 2):
            grp = int(q_cfg.get('convrot_groupsize') or q_cfg.get('group_size') or 256)
            flat_in = int(w_fp32.shape[1]) if w_fp32.ndim == 2 else int(w_fp32[0].numel())
            if grp >= 4 and flat_in % grp == 0:
                h_mat = _get_video_convrot_hadamard(grp, calc_dev, torch.float32)
                if h_mat is not None:
                    w_fp32 = (w_fp32.reshape(w_fp32.shape[0], -1, grp) @ h_mat).reshape(w_fp32.shape)
        w_key_low = w_key.lower()
        use_fp8_for_layer = (
            allow_fp8_cast
            and w_fp32.ndim == 2
            and w_fp32.numel() >= 65536
            and not any((tok in w_key_low for tok in fp16_keep_tokens))
        )
        if use_fp8_for_layer:
            sd[w_key] = torch.clamp(w_fp32, -448.0, 448.0).to(device='cpu', dtype=fp8_dtype)
        else:
            sd[w_key] = w_fp32.to(device='cpu', dtype=fallback_fp16_dtype)
        for aux_suffix in ('comfy_quant', 'weight_scale', 'scale_weight', 'weight.scale', 'scale', 'input_scale', 'scale_input', 'hadamard_matrix', 'rot_matrix', 'rotation_matrix', 'hadamard'):
            sd.pop(prefix + aux_suffix, None)
        if isinstance(meta_layers, dict):
            for rm_ln in (layer_name, f'diffusion_model.{layer_name}', f'model.diffusion_model.{layer_name}'):
                meta_layers.pop(rm_ln, None)
        modified = True
    if modified:
        for k in ('last.down.weight', 'last.up.weight'):
            sd.pop(k, None)
        has_remaining_quant = any((k.endswith('.comfy_quant') for k in sd.keys()))
        if isinstance(metadata, dict):
            if not has_remaining_quant and not meta_layers:
                metadata.pop('_quantization_metadata', None)
            elif meta_layers and '_quantization_metadata' in metadata:
                metadata['_quantization_metadata'] = json.dumps({'format_version': 1, 'layers': meta_layers})
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    return modified

def _dequantize_video_rowwise_fallback(module, _load_from_state_dict, state_dict, prefix, local_metadata, strict, missing_keys, unexpected_keys, error_msgs):
    w_key = prefix + 'weight'
    b_key = prefix + 'bias'
    w_t = state_dict.get(w_key, None)
    if not isinstance(w_t, torch.Tensor):
        w_t = getattr(module, 'weight', None)
    scale_t = None
    for sc_suffix in ('weight_scale', 'scale_weight', 'weight.scale', 'scale'):
        if prefix + sc_suffix in state_dict:
            scale_t = state_dict[prefix + sc_suffix]
            break
    if scale_t is None:
        for sc_attr in ('weight_scale', 'scale_weight', 'scale'):
            cand_sc = getattr(module, sc_attr, None)
            if isinstance(cand_sc, torch.Tensor):
                scale_t = cand_sc
                break
    q_cfg = _parse_video_comfy_quant_tensor(state_dict.get(prefix + 'comfy_quant', None))
    deq_weight = None
    if isinstance(w_t, torch.Tensor):
        w_fp32 = w_t.detach().to(dtype=torch.float32)
        if isinstance(scale_t, torch.Tensor):
            sc = scale_t.detach().to(device=w_fp32.device, dtype=torch.float32)
            if sc.ndim == 1 and w_fp32.ndim >= 2 and (sc.numel() == w_fp32.shape[0]):
                sc = sc.reshape(w_fp32.shape[0], *[1] * (w_fp32.ndim - 1))
            elif sc.ndim == 2 and w_fp32.ndim > 2 and (sc.shape[0] == w_fp32.shape[0]):
                sc = sc.reshape(sc.shape[0], sc.shape[1], *[1] * (w_fp32.ndim - 2))
            w_fp32 = w_fp32 * sc
        grp = int(q_cfg.get('convrot_groupsize') or q_cfg.get('group_size') or 256)
        flat_in = int(w_fp32.shape[1]) if w_fp32.ndim == 2 else (int(w_fp32[0].numel()) if w_fp32.ndim >= 3 else 0)
        if w_fp32.ndim >= 2 and grp >= 4 and (flat_in % grp == 0):
            h_mat = _get_video_convrot_hadamard(grp, w_fp32.device, torch.float32)
            if h_mat is not None:
                w_fp32 = (w_fp32.reshape(w_fp32.shape[0], -1, grp) @ h_mat).reshape(w_fp32.shape)
        fp8_dt = getattr(torch, 'float8_e4m3fn', torch.float16)
        deq_weight = torch.clamp(w_fp32, -448.0, 448.0).to(dtype=fp8_dt) if w_fp32.ndim == 2 else w_fp32.to(dtype=torch.float16)
        state_dict[w_key] = deq_weight
    for k in list(state_dict.keys()):
        if k.startswith(prefix) and k not in (w_key, b_key):
            suffix = k[len(prefix):]
            if '.' not in suffix or suffix.startswith('weight.'):
                state_dict.pop(k, None)
    deq_bias = None
    if b_key in state_dict and isinstance(state_dict[b_key], torch.Tensor):
        b_t = state_dict[b_key].detach()
        if not b_t.is_floating_point():
            b_t = b_t.to(dtype=torch.float16)
            state_dict[b_key] = b_t
        deq_bias = b_t
    if hasattr(module, '_parameters') and isinstance(module._parameters, dict):
        for pk in list(module._parameters.keys()):
            if pk not in ('weight', 'bias'):
                module._parameters.pop(pk, None)
    if hasattr(module, '_buffers') and isinstance(module._buffers, dict):
        for bk in list(module._buffers.keys()):
            if bk not in ('weight', 'bias'):
                module._buffers.pop(bk, None)
    module.is_quantized = False
    module.quant_format = None
    module.comfy_cast_weights = True
    if not hasattr(module, 'weight_function'):
        module.weight_function = []
    if not hasattr(module, 'bias_function'):
        module.bias_function = []
    manual_ops = getattr(comfy.ops, 'manual_cast', None) or getattr(comfy.ops, 'disable_weight_init', None)
    base_cls = getattr(manual_ops, type(module).__name__, None) if manual_ops is not None else None
    if base_cls is not None:
        try:
            module.__class__ = base_cls
        except Exception:
            if hasattr(base_cls, 'forward_comfy_cast_weights'):
                module.forward_comfy_cast_weights = base_cls.forward_comfy_cast_weights.__get__(module, type(module))
            if hasattr(base_cls, 'forward'):
                module.forward = base_cls.forward.__get__(module, type(module))
    try:
        _load_from_state_dict(state_dict, prefix, local_metadata, False, missing_keys, unexpected_keys, error_msgs)
    except Exception:
        pass
    if deq_weight is not None:
        module.__dict__.pop('weight', None)
        if hasattr(module, '_parameters') and isinstance(module._parameters, dict):
            module._parameters['weight'] = torch.nn.Parameter(deq_weight, requires_grad=False)
        else:
            setattr(module, 'weight', torch.nn.Parameter(deq_weight, requires_grad=False))
    if deq_bias is not None:
        module.__dict__.pop('bias', None)
        if hasattr(module, '_parameters') and isinstance(module._parameters, dict):
            module._parameters['bias'] = torch.nn.Parameter(deq_bias, requires_grad=False)
        else:
            setattr(module, 'bias', torch.nn.Parameter(deq_bias, requires_grad=False))
    elif getattr(module, 'bias', None) is None and hasattr(module, '_parameters') and isinstance(module._parameters, dict):
        module._parameters.setdefault('bias', None)
    for rm_key in list(missing_keys):
        if rm_key.startswith(prefix):
            missing_keys.remove(rm_key)
    for err_item in list(error_msgs):
        if prefix in str(err_item):
            error_msgs.remove(err_item)

def _ensure_video_quant_compat(tier_profile: dict=None):
    import struct
    prof = dict(tier_profile) if isinstance(tier_profile, dict) else {}
    try:
        cur_lqm = getattr(comfy.ops, '_load_quantized_module', None)
        if callable(cur_lqm) and getattr(cur_lqm, '_ez_int8_rowwise_patched', False):
            for cell in (getattr(cur_lqm, '__closure__', None) or ()):
                cell_val = getattr(cell, 'cell_contents', None)
                if callable(cell_val) and (not getattr(cell_val, '_ez_int8_rowwise_patched', False)):
                    comfy.ops._load_quantized_module = cell_val
                    break
        if hasattr(torch, 'set_float32_matmul_precision'):
            torch.set_float32_matmul_precision(str(prof.get('matmul_precision', 'high')))
        if hasattr(torch.backends, 'cudnn'):
            setattr(torch.backends.cudnn, 'benchmark', bool(prof.get('cudnn_benchmark', True)))
        if hasattr(torch.backends, 'cuda'):
            if hasattr(torch.backends.cuda, 'matmul'):
                setattr(torch.backends.cuda.matmul, 'allow_tf32', bool(prof.get('allow_tf32', True)))
                setattr(torch.backends.cuda.matmul, 'allow_fp16_accumulation', bool(prof.get('allow_fp16_accum', True)))
            if hasattr(torch.backends.cuda, 'enable_flash_sdp'):
                torch.backends.cuda.enable_flash_sdp(True)
            if hasattr(torch.backends.cuda, 'enable_mem_efficient_sdp'):
                torch.backends.cuda.enable_mem_efficient_sdp(True)
        cur_ltf = getattr(comfy.utils, 'load_torch_file', None)
        orig_ltf = getattr(comfy.utils, '_ez_true_orig_load_torch_file', None)
        if orig_ltf is None and callable(cur_ltf):
            if getattr(cur_ltf, '_ez_safe_ltf_patched', False):
                for cell in (getattr(cur_ltf, '__closure__', None) or ()):
                    c_val = getattr(cell, 'cell_contents', None)
                    if callable(c_val) and (not getattr(c_val, '_ez_safe_ltf_patched', False)):
                        orig_ltf = c_val
                        break
            if orig_ltf is None:
                orig_ltf = cur_ltf
            comfy.utils._ez_true_orig_load_torch_file = orig_ltf
        if callable(orig_ltf) and (not getattr(cur_ltf, '_ez_safe_ltf_v3', False)):

            def _verify_safetensors_complete(fpath: str) -> bool:
                import struct as _st
                try:
                    fsize = os.path.getsize(fpath)
                    if fsize < 16:
                        return False
                    with open(fpath, 'rb') as fh:
                        h_len = _st.unpack('<Q', fh.read(8))[0]
                        if h_len <= 0 or h_len > 100_000_000 or (8 + h_len > fsize):
                            return False
                        h_obj = json.loads(fh.read(h_len).decode('utf-8'))
                    max_end = 0
                    if isinstance(h_obj, dict):
                        for (tk, tv) in h_obj.items():
                            if tk != '__metadata__' and isinstance(tv, dict):
                                offs = tv.get('data_offsets')
                                if isinstance(offs, (list, tuple)) and len(offs) >= 2:
                                    if int(offs[1]) > max_end:
                                        max_end = int(offs[1])
                    return fsize >= (8 + h_len + max_end)
                except Exception:
                    return False

            def _find_intact_fallback_ckpt(broken_path: str) -> str:
                bp = Path(str(broken_path))
                stem_low = bp.stem.lower()
                is_minimax = any(k in stem_low for k in ('minimax', 'h3', 'vid_', 'wan', 'ltx', 'hunyuan'))
                is_krea = 'krea' in stem_low or 'flux' in stem_low
                try:
                    bad_quarantine = bp.with_suffix(bp.suffix + '.corrupt_part')
                    if bp.exists() and not bad_quarantine.exists():
                        os.replace(str(bp), str(bad_quarantine))
                        print(f'[EZ-SELF-HEAL] 🛡️ Isolerade avbruten/korrupt modellfil: {bp.name} -> {bad_quarantine.name}')
                except Exception:
                    pass
                secondary_candidates = []
                for folder_k in ('diffusion_models', 'unet', 'checkpoints'):
                    if folder_k not in folder_paths.folder_names_and_paths:
                        continue
                    for cand_rel in folder_paths.get_filename_list(folder_k):
                        cand_full = folder_paths.get_full_path(folder_k, cand_rel)
                        if not cand_full or str(cand_full) == str(broken_path) or str(cand_full).endswith('.corrupt_part'):
                            continue
                        if str(cand_full).lower().endswith(('.safetensors', '.sft')) and not _verify_safetensors_complete(cand_full):
                            continue
                        c_low = str(cand_rel).lower()
                        if (is_minimax and ('minimax' in c_low or 'h3' in c_low)) or (is_krea and ('krea' in c_low or 'flux' in c_low)):
                            print(f'[EZ-SELF-HEAL] ✅ Automatisk fallback till intakt modell: {cand_rel}')
                            return str(cand_full)
                        if is_minimax and any(vk in c_low for vk in ('wan', 'ltx', 'hunyuan', 'mochi', 'vid_', 'video')):
                            secondary_candidates.append((cand_rel, cand_full))
                if secondary_candidates:
                    chosen_rel, chosen_full = secondary_candidates[0]
                    print(f'[EZ-SELF-HEAL] ✅ Automatisk sekundär fallback till intakt videomodell: {chosen_rel}')
                    return str(chosen_full)
                return str(broken_path)

            def _ez_safe_load_torch_file(ckpt, safe_load=False, device=None, return_metadata=False, **kwargs):
                import struct as _st
                ckpt_str = str(ckpt)
                if ckpt_str.lower().endswith(('.safetensors', '.sft')) and os.path.exists(ckpt_str):
                    if not _verify_safetensors_complete(ckpt_str):
                        ckpt_str = _find_intact_fallback_ckpt(ckpt_str)
                        ckpt = ckpt_str
                try:
                    return orig_ltf(ckpt, safe_load=safe_load, device=device, return_metadata=return_metadata, **kwargs)
                except Exception as first_err:
                    if 'extends past the end of the file' in str(first_err) or 'incomplete metadata' in str(first_err) or 'SafetensorError' in type(first_err).__name__:
                        healed = _find_intact_fallback_ckpt(str(ckpt))
                        if healed != str(ckpt) and os.path.exists(healed):
                            return orig_ltf(healed, safe_load=safe_load, device=device, return_metadata=return_metadata, **kwargs)
                        raise RuntimeError(f'[EZ-SAFE-LOADER] Modellfilen "{ckpt}" är ofullständigt nedladdad (korrupt safetensors). Radera eller ladda ner filen på nytt.') from first_err
                    if hasattr(comfy.model_management, 'unload_all_models'):
                        comfy.model_management.unload_all_models()
                    if hasattr(comfy.model_management, 'soft_empty_cache'):
                        comfy.model_management.soft_empty_cache()
                    gc.collect()
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    try:
                        return orig_ltf(ckpt, safe_load=safe_load, device=device, return_metadata=return_metadata, **kwargs)
                    except Exception:
                        pass
                    if ckpt_str.lower().endswith(('.safetensors', '.sft')):
                        import safetensors.torch
                        meta_out = {}
                        with open(ckpt_str, 'rb') as fh:
                            raw_bytes = fh.read()
                        if len(raw_bytes) > 8:
                            try:
                                h_len = _st.unpack('<Q', raw_bytes[:8])[0]
                                h_obj = json.loads(raw_bytes[8:8 + h_len].decode('utf-8'))
                                if isinstance(h_obj, dict) and isinstance(h_obj.get('__metadata__'), dict):
                                    meta_out = h_obj['__metadata__']
                            except Exception:
                                meta_out = {}
                        sd_out = safetensors.torch.load(raw_bytes)
                        del raw_bytes
                        return (sd_out, meta_out) if return_metadata else sd_out
                    pl_load = torch.load(ckpt_str, map_location=device or 'cpu', weights_only=False)
                    if isinstance(pl_load, dict) and 'state_dict' in pl_load:
                        pl_load = pl_load['state_dict']
                    return (pl_load, {}) if return_metadata else pl_load
            _ez_safe_load_torch_file._ez_safe_ltf_patched = True
            _ez_safe_load_torch_file._ez_safe_ltf_v2 = True
            _ez_safe_load_torch_file._ez_safe_ltf_v3 = True
            comfy.utils.load_torch_file = _ez_safe_load_torch_file
    except Exception:
        pass

def _load_video_diffusion_model_convrot_safe(unet_path: str, tier_profile: dict=None):
    _ensure_video_quant_compat(tier_profile)
    p_orig = Path(str(unet_path))
    for cache_tag in ('_ez_fp8_e4m3fn_cache', '_ez_hadamard_v2_fp8'):
        if p_orig.stem.endswith(cache_tag):
            cand_orig = p_orig.with_name(p_orig.name.replace(cache_tag, ''))
            if cand_orig.exists():
                p_orig = cand_orig
                unet_path = str(cand_orig)
    for stale_tag in ('_ez_fp8_e4m3fn_cache', '_ez_hadamard_v2_fp8'):
        stale_cache = p_orig.with_name(f'{p_orig.stem}{stale_tag}.safetensors')
        if stale_cache.exists():
            try:
                stale_cache.unlink()
                print(f'[EZ-05-CLEANUP] 🧹 Raderade skadad FP8-cachefil: {stale_cache.name}')
            except Exception:
                pass
    hdr_info = _inspect_safetensors_header(str(unet_path))
    if not hdr_info.get('needs_convrot_dequant', False):
        try:
            return comfy.sd.load_diffusion_model(str(unet_path))
        except Exception:
            pass
    vram_gb = 16.0
    if torch.cuda.is_available():
        try:
            vram_gb = float(torch.cuda.get_device_properties(0).total_memory) / (1024.0 ** 3)
        except Exception:
            vram_gb = 16.0
    allow_fp8 = bool(vram_gb < 28.0)
    try:
        loaded = comfy.utils.load_torch_file(str(unet_path), return_metadata=True)
        (sd, metadata) = loaded if isinstance(loaded, tuple) and len(loaded) == 2 else (loaded, None)
    except TypeError:
        sd = comfy.utils.load_torch_file(str(unet_path))
        metadata = None
    was_dequantized = _pre_dequantize_video_convrot_state_dict(sd, metadata=metadata, model_path=str(unet_path), allow_fp8_cast=allow_fp8)
    has_rem_meta = isinstance(metadata, dict) and '_quantization_metadata' in metadata
    if was_dequantized and not has_rem_meta:
        return comfy.sd.load_diffusion_model_state_dict(sd)
    try:
        return comfy.sd.load_diffusion_model_state_dict(sd, metadata=metadata)
    except TypeError:
        return comfy.sd.load_diffusion_model_state_dict(sd)

def _load_video_vae_convrot_safe(vae_path: str):
    if not vae_path:
        raise ValueError('[EZ-MINIMAX-H3] Ingen giltig Video-VAE vald i EZ [05]!')
    p_vae = Path(str(vae_path))
    for v_tag in ('_ez_fp16_vae_cache', '_ez_hadamard_v2_fp16_vae'):
        if p_vae.stem.endswith(v_tag):
            cand_v = p_vae.with_name(p_vae.name.replace(v_tag, ''))
            if cand_v.exists():
                p_vae = cand_v
                vae_path = str(cand_v)
    for stale_v_tag in ('_ez_fp16_vae_cache', '_ez_hadamard_v2_fp16_vae'):
        stale_v_path = p_vae.with_name(f'{p_vae.stem}{stale_v_tag}.safetensors')
        if stale_v_path.exists():
            try:
                stale_v_path.unlink()
            except Exception:
                pass
    try:
        loaded = comfy.utils.load_torch_file(str(vae_path), return_metadata=True)
        (vae_sd, vae_meta) = loaded if isinstance(loaded, tuple) and len(loaded) == 2 else (loaded, None)
    except TypeError:
        vae_sd = comfy.utils.load_torch_file(str(vae_path))
        vae_meta = None
    vae_hdr = _inspect_safetensors_header(str(vae_path))
    if vae_hdr.get('needs_convrot_dequant', False):
        _pre_dequantize_video_convrot_state_dict(vae_sd, metadata=vae_meta, model_path=str(vae_path), allow_fp8_cast=False)
        return comfy.sd.VAE(sd=vae_sd)
    try:
        return comfy.sd.VAE(sd=vae_sd, metadata=vae_meta)
    except TypeError:
        try:
            return comfy.sd.VAE(sd=vae_sd)
        except Exception:
            pass
    except Exception:
        pass
    _pre_dequantize_video_convrot_state_dict(vae_sd, metadata=vae_meta, model_path=str(vae_path), allow_fp8_cast=False)
    return comfy.sd.VAE(sd=vae_sd)

_PRISM_VIDEO_LORA_CACHE: dict = {}


def _ez_prism_process_video_lora_sd(
    lora_sd: dict,
    primary_basis_map: dict = None,
    is_primary: bool = False,
    is_turbo: bool = False,
    tail_threshold: float = 0.065,
    orth_strength: float = 0.68,
) -> dict:
    if not isinstance(lora_sd, dict) or not lora_sd:
        return lora_sd
    out_sd = dict(lora_sd)
    down_suffixes = ('.lora_down.weight', '.lora_a.weight', '_lora.down.weight')
    up_map = {
        '.lora_down.weight': '.lora_up.weight',
        '.lora_a.weight': '.lora_b.weight',
        '_lora.down.weight': '_lora.up.weight',
    }
    audio_tokens = ('audio', 'aud_', '_aud', 'attn_a', 'ff_a', 'norm_a', 'proj_a', 'mod_a', 'q_a', 'k_a', 'v_a', 'out_a', 'a_embed', 'audio_vae', 'vocoder')
    try:
        with torch.no_grad():
            for k_down, v_down in list(lora_sd.items()):
                if not isinstance(v_down, torch.Tensor) or v_down.ndim != 2:
                    continue
                matched_sfx = next((sfx for sfx in down_suffixes if str(k_down).endswith(sfx)), None)
                if not matched_sfx:
                    continue
                stem = str(k_down)[:-len(matched_sfx)]
                if is_turbo and any((at in stem.lower() for at in audio_tokens)):
                    continue
                k_up = stem + up_map[matched_sfx]
                v_up = lora_sd.get(k_up)
                if not isinstance(v_up, torch.Tensor) or v_up.ndim != 2:
                    continue
                r_dim, d_in = int(v_down.shape[0]), int(v_down.shape[1])
                d_out, r_up = int(v_up.shape[0]), int(v_up.shape[1])
                if r_dim != r_up or r_dim < 2 or r_dim > min(d_in, d_out):
                    continue
                orig_dt = v_down.dtype
                orig_dev = v_down.device
                a_f32 = v_down.detach().to(device='cpu', dtype=torch.float32)
                b_f32 = v_up.detach().to(device='cpu', dtype=torch.float32)
                modified_pair = False
                if isinstance(primary_basis_map, dict) and (not is_primary) and (stem in primary_basis_map):
                    u_prin, v_prin = primary_basis_map[stem]
                    if isinstance(u_prin, torch.Tensor) and u_prin.shape[0] == d_out:
                        proj_u = torch.matmul(u_prin, torch.matmul(u_prin.t(), b_f32))
                        b_f32 = b_f32 - float(orth_strength) * proj_u
                        modified_pair = True
                    if isinstance(v_prin, torch.Tensor) and v_prin.shape[0] == d_in and (not is_turbo):
                        proj_v = torch.matmul(torch.matmul(a_f32, v_prin), v_prin.t())
                        a_f32 = a_f32 - (float(orth_strength) * 0.55) * proj_v
                        modified_pair = True
                if (not is_turbo) or is_primary:
                    qb, rb = torch.linalg.qr(b_f32, mode='reduced')
                    qa, ra = torch.linalg.qr(a_f32.t(), mode='reduced')
                    core = torch.matmul(rb, ra.t())
                    u_c, s_vals, vh_c = torch.linalg.svd(core, full_matrices=False)
                    s_max = float(s_vals[0].item()) if s_vals.numel() > 0 else 0.0
                    if s_max > 1e-8:
                        if isinstance(primary_basis_map, dict) and (is_primary or stem not in primary_basis_map):
                            top_k = max(1, min(16, int((s_vals >= 0.22 * s_max).sum().item())))
                            u_p = torch.matmul(qb, u_c[:, :top_k]).detach()
                            v_p = torch.matmul(qa, vh_c[:top_k, :].t()).detach()
                            primary_basis_map[stem] = (u_p, v_p)
                        if not is_turbo and float(tail_threshold) > 0.0:
                            keep_m = s_vals >= (float(tail_threshold) * s_max)
                            if not bool(keep_m.any()):
                                keep_m[0] = True
                            if not bool(keep_m.all()):
                                e_orig = float(torch.linalg.norm(s_vals).item())
                                s_clean = torch.where(keep_m, s_vals, torch.zeros_like(s_vals))
                                e_clean = float(torch.linalg.norm(s_clean).item())
                                if e_clean > 1e-8 and e_orig > e_clean:
                                    s_clean = s_clean * (e_orig / e_clean)
                                sqrt_s = torch.sqrt(torch.clamp(s_clean, min=0.0))
                                b_f32 = torch.matmul(qb, u_c) * sqrt_s.unsqueeze(0)
                                a_f32 = sqrt_s.unsqueeze(1) * torch.matmul(vh_c, qa.t())
                                modified_pair = True
                if modified_pair:
                    out_sd[k_down] = a_f32.to(device=orig_dev, dtype=orig_dt)
                    out_sd[k_up] = b_f32.to(device=orig_dev, dtype=orig_dt)
    except Exception:
        return lora_sd
    return out_sd


def _apply_modality_separated_av_lora(model, clip, lora_sd: dict, video_strength: float, audio_strength: float, vis_strength: float=1.0, clip_strength: float=0.0, lora_name: str='', primary_basis_map: dict=None, is_primary_slot: bool=False):
    v_str = float(video_strength)
    vis_str = float(vis_strength)
    a_str = float(audio_strength)
    c_str = float(clip_strength)
    name_low = str(lora_name or '').lower()
    is_turbo_lora = any((tok in name_low for tok in ('turbo', 'step600', 'step_', 'distill', 'lcm', 'hyper')))
    if is_turbo_lora:
        eff_vis = v_str * vis_str
        eff_aud = v_str * a_str
        c_str = 0.0
    else:
        eff_vis = v_str * vis_str
        eff_aud = v_str * a_str
        has_te_keys = any(('lora_te' in str(k).lower() or 'text_encoder' in str(k).lower() or 'text_model' in str(k).lower() for k in lora_sd.keys()))
        if not has_te_keys:
            c_str = 0.0
    if abs(eff_vis) < 1e-05 and abs(eff_aud) < 1e-05 and (abs(c_str) < 1e-05):
        return (model, clip)
    lora_sd = _ez_prism_process_video_lora_sd(
        lora_sd,
        primary_basis_map=primary_basis_map,
        is_primary=bool(is_primary_slot and not is_turbo_lora),
        is_turbo=is_turbo_lora,
        tail_threshold=0.0 if is_turbo_lora else 0.065,
        orth_strength=0.68 if is_turbo_lora else 0.55,
    )
    target_clip = clip if abs(c_str) >= 1e-05 else None
    if abs(eff_vis - eff_aud) <= 0.0001:
        (out_m, out_c) = comfy.sd.load_lora_for_models(model, target_clip, lora_sd, eff_vis, c_str)
        return (out_m, out_c if target_clip is not None else clip)
    audio_tokens = ('audio', 'aud_', '_aud', 'attn_a', 'ff_a', 'norm_a', 'proj_a', 'mod_a', 'q_a', 'k_a', 'v_a', 'out_a', 'a_embed', 'audio_vae', 'vocoder', 'mel_', 'sound', 'speaker')
    up_tokens = ('.lora_up', '.lora_b', '.hada_w1', '.lokr_w1')
    base_str = eff_vis if abs(eff_vis) >= 1e-05 else eff_aud
    ratio = eff_aud / base_str if abs(base_str) >= 1e-05 else 0.0
    adjusted_sd = {}
    for (k, val) in lora_sd.items():
        low_k = str(k).lower()
        is_aud_key = any((tok in low_k for tok in audio_tokens))
        is_up_weight = any((tok in low_k for tok in up_tokens))
        if isinstance(val, torch.Tensor) and is_up_weight:
            if is_aud_key and abs(eff_vis) >= 1e-05:
                adjusted_sd[k] = val * float(ratio)
            elif not is_aud_key and abs(eff_vis) < 1e-05:
                adjusted_sd[k] = torch.zeros_like(val)
            else:
                adjusted_sd[k] = val
        else:
            adjusted_sd[k] = val
    (out_m, out_c) = comfy.sd.load_lora_for_models(model, target_clip, adjusted_sd, base_str, c_str)
    return (out_m, out_c if target_clip is not None else clip)

def _attach_minimax_condition_proj_guard(model_patcher) -> None:
    try:
        diff_m = getattr(getattr(model_patcher, 'model', None), 'diffusion_model', None)
        cond_proj = getattr(diff_m, 'condition_proj', None) if diff_m is not None else None
        if cond_proj is None or getattr(cond_proj, '_ez_cond_proj_hooked', False):
            return

        def _cond_proj_pre_hook(module, args):
            if not args or not isinstance(args[0], torch.Tensor):
                return None
            x = args[0]
            w = getattr(module, 'weight', None)
            expected_in = int(w.shape[1]) if isinstance(w, torch.Tensor) and w.ndim >= 2 else int(getattr(module, 'in_features', 0) or 0)
            if expected_in > 0 and x.shape[-1] != expected_in:
                if x.shape[-1] * 2 == expected_in:
                    x_fixed = torch.cat([x, x], dim=-1)
                    return (x_fixed,) + tuple(args[1:])
                if x.shape[-1] > expected_in:
                    x_fixed = x[..., :expected_in]
                    return (x_fixed,) + tuple(args[1:])
            return None

        cond_proj.register_forward_pre_hook(_cond_proj_pre_hook)
        cond_proj._ez_cond_proj_hooked = True
    except Exception:
        pass


def materialize_deferred_ref2va_model(model_ref2va):
    if model_ref2va is None:
        return None
    m_opts = getattr(model_ref2va, 'model_options', {}) if hasattr(model_ref2va, 'model_options') and isinstance(getattr(model_ref2va, 'model_options'), dict) else {}
    spec = m_opts.get('ez_deferred_ref2va_spec')
    if not isinstance(spec, dict) or not spec.get('ref_path') or not os.path.exists(str(spec['ref_path'])):
        return model_ref2va
    ref_path = str(spec['ref_path'])
    print(f'[EZ-05-ON-DEMAND] 🔄 Aktiverar dedikerad Ref2VA-modell vid behov: {os.path.basename(ref_path)}')
    try:
        if hasattr(comfy.model_management, 'unload_all_models'):
            comfy.model_management.unload_all_models()
        comfy.model_management.soft_empty_cache()
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        loaded_ref = _load_video_diffusion_model_convrot_safe(ref_path, tier_profile=spec.get('tier_profile'))
        ref_prism_basis: dict = {}
        ref_non_turbo_applied = 0
        for entry in (spec.get('lora_specs') or ()):
            if not isinstance(entry, (list, tuple)) or len(entry) < 3:
                continue
            l_name, v_str, a_str = (entry[0], float(entry[1]), float(entry[2]))
            vis_str = float(entry[3]) if len(entry) >= 4 else 1.0
            l_path = folder_paths.get_full_path('loras', l_name) if l_name and l_name != 'None' else None
            if l_path:
                lora_sd = comfy.utils.load_torch_file(l_path, safe_load=True)
                is_t_lora = any((tok in str(l_name).lower() for tok in ('turbo', 'step600', 'step_', 'distill', 'lcm', 'hyper')))
                (loaded_ref, _) = _apply_modality_separated_av_lora(
                    loaded_ref,
                    None,
                    lora_sd,
                    v_str,
                    a_str,
                    vis_strength=vis_str,
                    clip_strength=0.0,
                    lora_name=l_name,
                    primary_basis_map=ref_prism_basis,
                    is_primary_slot=(ref_non_turbo_applied == 0 and not is_t_lora),
                )
                if not is_t_lora:
                    ref_non_turbo_applied += 1
        _attach_minimax_condition_proj_guard(loaded_ref)
        if str(spec.get('detected_video_arch', 'minimax_h3')) == 'minimax_h3':
            try:
                from comfy_extras.nodes_minimax_h3 import MiniMaxH3SigmaShift
                s_ref = MiniMaxH3SigmaShift.execute(loaded_ref, float(spec.get('shift_video', 5.0)), float(spec.get('shift_audio', 3.0)))
                loaded_ref = s_ref[0] if isinstance(s_ref, (tuple, list)) or hasattr(s_ref, '__getitem__') else s_ref
            except Exception:
                pass
        if hasattr(loaded_ref, 'model_options') and isinstance(loaded_ref.model_options, dict):
            for (ok, ov) in m_opts.items():
                if ok != 'ez_deferred_ref2va_spec':
                    loaded_ref.model_options[ok] = ov
        return loaded_ref
    except Exception as exc:
        print(f'[EZ-05-ON-DEMAND] ⚠️ Kunde inte ladda Ref2VA ({os.path.basename(ref_path)}): {exc} -> Använder primär modell.')
        return model_ref2va


def load_video_engine_and_apply_av_loras(video_unet_fl2va: str, video_unet_ref2va: str, video_clip_name: str, clip_type_str: str, video_vae_name: str, audio_vae_name: str, lora_entries: list, video_turbo_lora: str, turbo_video_strength: float, turbo_audio_strength: float, shift_video: float, shift_audio: float, enable_fp16_accumulation: bool, tier_profile: dict=None, turbo_vis_strength: float=1.0):
    prof = dict(tier_profile) if isinstance(tier_profile, dict) else {}
    if bool(prof.get('aggressive_vram_purge', True)):
        if hasattr(comfy.model_management, 'unload_all_models'):
            comfy.model_management.unload_all_models()
        comfy.model_management.soft_empty_cache()
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    _ensure_video_quant_compat(prof)
    if not video_unet_fl2va or video_unet_fl2va == 'None' or _is_non_unet_or_image_only_for_video(video_unet_fl2va):
        valid_v_unets = [u for u in get_dynamic_video_unets() if u and u != 'None']
        fl2va_first = [u for u in valid_v_unets if 'ref2va' not in u.lower()] or valid_v_unets
        if fl2va_first:
            print(f'[EZ-05-SELF-HEAL] 🛡️ Ogiltig Video-UNet "{video_unet_fl2va}" -> Väljer automatiskt: {fl2va_first[0]}')
            video_unet_fl2va = fl2va_first[0]
    fl2va_path = folder_paths.get_full_path('diffusion_models', video_unet_fl2va) or folder_paths.get_full_path('unet', video_unet_fl2va) or folder_paths.get_full_path('checkpoints', video_unet_fl2va)
    model_fl2va = _load_video_diffusion_model_convrot_safe(fl2va_path, tier_profile=prof)
    vram_gb_det = 16.0
    if torch.cuda.is_available():
        try:
            vram_gb_det = float(torch.cuda.get_device_properties(0).total_memory) / (1024.0 ** 3)
        except Exception:
            vram_gb_det = 16.0
    ref_path = None
    if video_unet_ref2va and video_unet_ref2va not in ('None', 'Same as Primary (fl2va)', video_unet_fl2va):
        ref_path = folder_paths.get_full_path('diffusion_models', video_unet_ref2va) or folder_paths.get_full_path('unet', video_unet_ref2va) or folder_paths.get_full_path('checkpoints', video_unet_ref2va)
        if ref_path == fl2va_path:
            ref_path = None
    has_distinct_ref2va = bool(vram_gb_det >= 28.0 and ref_path)
    model_ref2va = None
    if has_distinct_ref2va:
        model_ref2va = _load_video_diffusion_model_convrot_safe(ref_path, tier_profile=prof)
    clip_low = str(video_clip_name or '').lower()
    unet_low = str(video_unet_fl2va or '').lower()
    unet_is_h3 = any((k in unet_low for k in ('minimax', 'h3', 'fl2va', 'ref2va', 'hailuo', 'singularity', 'prism'))) or _inspect_safetensors_header(str(fl2va_path or '')).get('arch') == 'minimax_h3'
    if unet_is_h3 and ('4b' in clip_low or 'krea2' in clip_low or not video_clip_name or video_clip_name == 'None'):
        all_v_clips = [c for c in get_dynamic_video_clips() if c and c != 'None']
        h3_32b_clips = [c for c in all_v_clips if any((k in c.lower() for k in ('32b', 'minimax_h3', 'nvfp4', 'h3\\', 'h3/'))) and '4b' not in c.lower()]
        if h3_32b_clips:
            print(f'[EZ-05-SELF-HEAL] 🛡️ Byter felkopplad 4B Krea2 CLIP "{video_clip_name}" -> MiniMax H3 32B Text Encoder: {h3_32b_clips[0]}')
            video_clip_name = h3_32b_clips[0]
    clip_path = folder_paths.get_full_path('text_encoders', video_clip_name) or folder_paths.get_full_path('clip', video_clip_name)
    minimax_native_clip_key = next((k for k in ('MINIMAX_H3', 'MINIMAX', 'KREA2', 'WAN') if hasattr(comfy.sd.CLIPType, k)), 'STABLE_DIFFUSION')
    clip_alias_map = {
        'MINIMAX': minimax_native_clip_key,
        'MINIMAX_H3': minimax_native_clip_key,
        'KREA2': minimax_native_clip_key,
        'WAN': 'WAN',
        'WAN2.2': 'WAN',
        'LTXV': 'LTXV',
        'HUNYUAN_VIDEO': 'HUNYUAN_VIDEO',
        'MOCHI': 'MOCHI',
        'STABLE_DIFFUSION': 'STABLE_DIFFUSION',
    }
    raw_ct_up = str(clip_type_str or 'minimax').upper()
    mapped_clip_key = minimax_native_clip_key if raw_ct_up in ('MINIMAX', 'MINIMAX_H3', 'KREA2') else clip_alias_map.get(raw_ct_up, 'WAN')
    resolved_clip_type = getattr(comfy.sd.CLIPType, str(mapped_clip_key), getattr(comfy.sd.CLIPType, minimax_native_clip_key, comfy.sd.CLIPType.STABLE_DIFFUSION))
    video_clip = comfy.sd.load_clip(ckpt_paths=[clip_path], embedding_directory=folder_paths.get_folder_paths('embeddings'), clip_type=resolved_clip_type)
    for v_tag in ('_ez_fp16_vae_cache', '_ez_hadamard_v2_fp16_vae'):
        if v_tag in str(video_vae_name or ''):
            video_vae_name = str(video_vae_name).replace(v_tag, '')
    v_vae_path = folder_paths.get_full_path('vae', video_vae_name)
    if not v_vae_path and unet_is_h3:
        h3_vaes = [v for v in get_dynamic_video_vaes() if any(k in v.lower() for k in ('minimax_h3_video_vae', 'minimax-h3-video_vae', 'video_vae'))]
        h3_vaes.sort(key=lambda x: (0 if any(p in x.lower() for p in ('bf16', 'fp16', 'fp32')) else (2 if 'int8' in x.lower() else 1), x.lower()))
        if h3_vaes:
            video_vae_name = h3_vaes[0]
            v_vae_path = folder_paths.get_full_path('vae', video_vae_name)
    if unet_is_h3 and 'int8' in str(video_vae_name or '').lower():
        print(f'[EZ-05-VAE-NOTICE] ⚠️ Video-VAE "{os.path.basename(str(video_vae_name))}" är 8-bitars kvantiserad (INT8) och ger avrundningsdrift vid flerfönster-omkodning. Byt till MiniMax-H3-video_vae_fp16.safetensors (5.21 GB) eller bf16 för förlustfri kontrast & bakgrundslåsning!')
    video_vae = _load_video_vae_convrot_safe(v_vae_path)
    if audio_vae_name and audio_vae_name != 'None':
        a_vae_path = folder_paths.get_full_path('vae', audio_vae_name)
        audio_vae = comfy.sd.VAE(sd=comfy.utils.load_torch_file(a_vae_path)) if a_vae_path else video_vae
    else:
        audio_vae = video_vae
    baked_turbo_tokens = (
        'hsa_turbo', '_turbo', 'turbo_v', 'cfgdistill', 'pdmd', 'dmad',
        'pikaflex', 'pika_flex', '10eros', 'dasiwa_minimax_h3', 'dasiwahybrid',
        'lightx2v', 'hyperflow', 'fasth3', 'qad', '8step', '8-step', '6step', '4step', '3step',
    )
    unet_has_baked_turbo = any((tk in unet_low for tk in baked_turbo_tokens))
    unet_is_rich_finetune = any((ft in unet_low for ft in ('singularity', '10eros', 'erosmax', 'pinkcherry', 'dasiwa', 'prism')))
    eff_turbo_v_str = float(turbo_video_strength)
    eff_turbo_a_str = float(turbo_audio_strength)
    if unet_has_baked_turbo and video_turbo_lora and video_turbo_lora != 'None' and eff_turbo_v_str > 0.0:
        print(f'[EZ-05-TURBO-GUARD] ⚡ UNet "{os.path.basename(video_unet_fl2va)}" har redan inbakad PikaFlex/10Eros/DMAD/Turbo-destillering -> kopplar ur extern Turbo-LoRA ({eff_turbo_v_str:.2f} -> 0.00) för att förhindra dubbel-destillering och kontrastfritering.')
        eff_turbo_v_str = 0.0
        eff_turbo_a_str = 0.0
    has_turbo_lora = bool((video_turbo_lora and video_turbo_lora != 'None' and (eff_turbo_v_str > 0.05)) or unet_has_baked_turbo)
    norm_entries = []
    for e in lora_entries:
        if isinstance(e, (list, tuple)) and len(e) >= 3 and e[0] and (e[0] != 'None'):
            ev = float(e[1])
            ea = float(e[2])
            evis = float(e[3]) if len(e) >= 4 else 1.0
            ec = float(e[4]) if len(e) >= 5 else 0.0
            norm_entries.append([e[0], ev, ea, evis, ec])
    turbo_toks = ('turbo', 'step600', 'step_', 'distill', 'lcm', 'hyper')
    raw_cum_vis = sum((abs(x[1] * x[3]) for x in norm_entries if not any((t in str(x[0]).lower() for t in turbo_toks))))
    max_vis_budget = 0.68 if unet_is_rich_finetune else 0.85
    if len(norm_entries) >= 2 and raw_cum_vis > max_vis_budget:
        vis_scale = max_vis_budget / max(1e-05, raw_cum_vis)
        for x in norm_entries:
            if not any((t in str(x[0]).lower() for t in turbo_toks)):
                x[1] = round(float(x[1]) * vis_scale, 4)
        print(f'[EZ-05-LORA-HEADROOM] 🎚️ Skalad kumulativ Video-LoRA-styrka ({raw_cum_vis:.2f} -> {max_vis_budget:.2f}) för att skydda rumslåsning (<Picture 1>) och förhindra kontrastklippning.')
    norm_entries = [tuple(x) for x in norm_entries]
    all_lora_specs = list(norm_entries)
    if video_turbo_lora and video_turbo_lora != 'None' and (eff_turbo_v_str > 0.05):
        all_lora_specs.append((video_turbo_lora, eff_turbo_v_str, eff_turbo_a_str, float(turbo_vis_strength), 0.0))
    hdr_arch = _inspect_safetensors_header(str(fl2va_path or '')).get('arch', '')
    m_cfg_cls = str(getattr(getattr(getattr(model_fl2va, 'model', None), 'model_config', None), '__class__', type(None)).__name__).lower()
    diff_m = getattr(getattr(model_fl2va, 'model', None), 'diffusion_model', None)
    ct_low = str(clip_type_str or 'minimax').lower()
    if hasattr(diff_m, 'condition_proj') or hasattr(diff_m, 'audio_in') or 'minimax' in m_cfg_cls or 'flow_av' in m_cfg_cls or hdr_arch == 'minimax_h3':
        detected_video_arch = 'minimax_h3'
    elif 'wan22' in m_cfg_cls or 'wan_22' in m_cfg_cls or hdr_arch == 'wan22' or 'wan2.2' in unet_low or 'wan_2.2' in unet_low or ct_low == 'wan2.2':
        detected_video_arch = 'wan22'
    elif 'wan' in m_cfg_cls or hdr_arch == 'wan21' or 'wan' in unet_low or ct_low == 'wan':
        detected_video_arch = 'wan21'
    elif 'ltx' in m_cfg_cls or hdr_arch == 'ltxv' or 'ltx' in unet_low or ct_low == 'ltxv':
        detected_video_arch = 'ltxv'
    elif 'hunyuan' in m_cfg_cls or hdr_arch == 'hunyuan_video' or 'hunyuan' in unet_low or ct_low == 'hunyuan_video':
        detected_video_arch = 'hunyuan_video'
    elif 'mochi' in m_cfg_cls or hdr_arch == 'mochi' or 'mochi' in unet_low or ct_low == 'mochi':
        detected_video_arch = 'mochi'
    else:
        detected_video_arch = 'minimax_h3'
    prism_video_basis: dict = {}
    non_turbo_applied = 0
    for entry in all_lora_specs:
        if not isinstance(entry, (list, tuple)) or len(entry) < 3:
            continue
        l_name = entry[0]
        v_str = float(entry[1])
        a_str = float(entry[2])
        vis_str = float(entry[3]) if len(entry) >= 4 else 1.0
        c_str = float(entry[4]) if len(entry) >= 5 else v_str
        if not l_name or l_name == 'None':
            continue
        if abs(v_str * vis_str) < 1e-05 and abs(v_str * a_str) < 1e-05 and (abs(c_str) < 1e-05):
            continue
        l_low = str(l_name).lower()
        if detected_video_arch == 'minimax_h3' and any((wk in l_low for wk in ('wan2.1', 'wan2.2', 'wan_', 'causvid', 'ltxv', 'ltx_video', 'hunyuan'))):
            print(f'[EZ-05-H3-GUARD] 🛡️ Ignorerar icke-H3 Video-LoRA "{l_name}" vid körning av MiniMax H3.')
            continue
        if detected_video_arch != 'minimax_h3' and any((hk in l_low for hk in ('minimax', 'h3_', 'step600', 'singularity'))):
            print(f'[EZ-05-VID-GUARD] 🛡️ Ignorerar MiniMax H3-LoRA "{l_name}" vid körning av {detected_video_arch}.')
            continue
        l_path = folder_paths.get_full_path('loras', l_name)
        if not l_path:
            continue
        lora_sd = comfy.utils.load_torch_file(l_path, safe_load=True)
        is_t_lora = any((tok in l_low for tok in ('turbo', 'step600', 'step_', 'distill', 'lcm', 'hyper')))
        is_prim = (non_turbo_applied == 0 and not is_t_lora)
        (model_fl2va, video_clip) = _apply_modality_separated_av_lora(
            model_fl2va,
            video_clip,
            lora_sd,
            v_str,
            a_str,
            vis_strength=vis_str,
            clip_strength=c_str,
            lora_name=l_name,
            primary_basis_map=prism_video_basis,
            is_primary_slot=is_prim,
        )
        if has_distinct_ref2va and model_ref2va is not None:
            (model_ref2va, _) = _apply_modality_separated_av_lora(
                model_ref2va,
                None,
                lora_sd,
                v_str,
                a_str,
                vis_strength=vis_str,
                clip_strength=0.0,
                lora_name=l_name,
                primary_basis_map=prism_video_basis,
                is_primary_slot=False,
            )
        if not is_t_lora:
            non_turbo_applied += 1
    if not has_distinct_ref2va or model_ref2va is None:
        model_ref2va = model_fl2va.clone()
    _attach_minimax_condition_proj_guard(model_fl2va)
    _attach_minimax_condition_proj_guard(model_ref2va)
    fp16_accum_active = bool(enable_fp16_accumulation) or bool(prof.get('allow_fp16_accum', True))
    try:
        if hasattr(torch.backends, 'cuda') and hasattr(torch.backends.cuda, 'matmul'):
            setattr(torch.backends.cuda.matmul, 'allow_fp16_accumulation', fp16_accum_active)
    except Exception:
        pass
    eff_shift_v = 5.0 if has_turbo_lora and abs(float(shift_video) - 11.0) < 0.05 else float(shift_video)
    eff_shift_a = 3.0 if has_turbo_lora and abs(float(shift_audio) - 4.0) < 0.05 else float(shift_audio)
    if detected_video_arch == 'minimax_h3':
        try:
            from comfy_extras.nodes_minimax_h3 import MiniMaxH3SigmaShift
            s_fl2va = MiniMaxH3SigmaShift.execute(model_fl2va, eff_shift_v, eff_shift_a)
            model_fl2va = s_fl2va[0] if isinstance(s_fl2va, (tuple, list)) or hasattr(s_fl2va, '__getitem__') else s_fl2va
            s_ref2va = MiniMaxH3SigmaShift.execute(model_ref2va, eff_shift_v, eff_shift_a)
            model_ref2va = s_ref2va[0] if isinstance(s_ref2va, (tuple, list)) or hasattr(s_ref2va, '__getitem__') else s_ref2va
        except Exception:
            pass
    elif detected_video_arch in ('wan22', 'wan21', 'hunyuan_video', 'mochi') and float(eff_shift_v) > 0.0:
        try:
            import comfy.model_sampling as _comfy_ms
            class ModelSamplingVideoFlow(_comfy_ms.ModelSamplingSD3, _comfy_ms.CONST):
                pass
            for idx_m, m_in in enumerate((model_fl2va, model_ref2va)):
                ms_v = ModelSamplingVideoFlow(m_in.model.model_config)
                ms_v.set_parameters(shift=float(eff_shift_v))
                m_cl = m_in.clone()
                m_cl.add_object_patch('model_sampling', ms_v)
                if idx_m == 0:
                    model_fl2va = m_cl
                else:
                    model_ref2va = m_cl
        except Exception:
            pass
    for m_target in (model_fl2va, model_ref2va):
        if hasattr(m_target, 'model_options') and isinstance(m_target.model_options, dict):
            m_target.model_options['ez_video_arch'] = detected_video_arch
            m_target.model_options['shift_video'] = eff_shift_v
            m_target.model_options['shift_audio'] = eff_shift_a
            m_target.model_options['has_turbo_lora'] = bool(has_turbo_lora)
            m_target.model_options['unet_has_baked_turbo'] = bool(unet_has_baked_turbo)
            m_target.model_options['cumulative_lora_vis_gain'] = float(min(raw_cum_vis, max_vis_budget) if len(norm_entries) >= 2 else raw_cum_vis)
            m_target.model_options['enable_fp16_accumulation'] = fp16_accum_active
            m_target.model_options['hardware_tier'] = str(prof.get('tier_id', 'tier_1_rtx5070ti_16gb'))
    if not has_distinct_ref2va and ref_path and hasattr(model_ref2va, 'model_options') and isinstance(model_ref2va.model_options, dict):
        model_ref2va.model_options['ez_deferred_ref2va_spec'] = {
            'ref_path': str(ref_path),
            'lora_specs': list(all_lora_specs),
            'shift_video': eff_shift_v,
            'shift_audio': eff_shift_a,
            'detected_video_arch': detected_video_arch,
            'tier_profile': dict(prof),
        }
    return (model_fl2va, model_ref2va, video_clip, video_vae, audio_vae)

