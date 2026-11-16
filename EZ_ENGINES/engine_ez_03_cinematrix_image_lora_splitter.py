# -*- coding: utf-8 -*-

import json
import math
import os
import gc
import torch
import folder_paths
import comfy.sd
import comfy.utils
import comfy.model_management
import comfy.model_sampling
import comfy.ops
_H4_BASE = ((1.0, 1.0, 1.0, -1.0), (1.0, 1.0, -1.0, 1.0), (1.0, -1.0, 1.0, 1.0), (-1.0, 1.0, 1.0, 1.0))
_CONVROT_HADAMARD_CACHE = {}
_IMAGE_CLIP_COND_CACHE = {}

def _get_convrot_hadamard_matrix(group_size: int, device, dtype=torch.float32):
    grp = int(group_size or 256)
    if grp < 4:
        return None
    key = (grp, str(device), str(dtype))
    if key in _CONVROT_HADAMARD_CACHE:
        return _CONVROT_HADAMARD_CACHE[key]
    h4 = torch.tensor(_H4_BASE, dtype=torch.float32, device=device)
    h = h4
    while h.shape[0] < grp:
        h = torch.kron(h, h4)
    if h.shape[0] != grp:
        return None
    h = (h / math.sqrt(float(grp))).to(dtype=dtype)
    _CONVROT_HADAMARD_CACHE[key] = h
    return h

def _is_non_unet_or_video_only_for_image(rel_name: str) -> bool:
    b_low = os.path.basename(str(rel_name or '')).lower()
    if any(tag in b_low for tag in ('_ez_fp8_e4m3fn_cache', '_ez_fp16_vae_cache', '_ez_hadamard_v2_fp8', '_ez_hadamard_v2_fp16_vae')):
        return True
    try:
        from .engine_ez_05_cinematrix_video_lora_stack import _inspect_safetensors_header, _resolve_candidate_model_path
        full_p = _resolve_candidate_model_path(rel_name)
        if full_p and full_p.lower().endswith(('.safetensors', '.sft')):
            sig = _inspect_safetensors_header(full_p)
            if sig['role'] in ('lora', 'vae', 'text_encoder', 'video_unet'):
                return True
            if sig['role'] == 'image_unet':
                return False
    except Exception:
        pass
    if any((k in b_low for k in ('qwen3vl', 'qwen3-vl', 'qwen3_vl', 'qwen2.5-vl', 'qwen-vl', 'qwen_vl', 'huihui', 't5xxl', 'umt5', 'clip_l', 'clip_g', 'llava', 'mmproj', 'florence', 'text_encoder', '_vae', 'video_vae', 'audio_vae'))):
        return True
    if b_low in ('ae.safetensors', 'ae.sft', 'qwen_image_vae.safetensors', 'wan_2.1_vae.safetensors', 'wan_2.2_vae.safetensors', 'sdxl_vae.safetensors'):
        return True
    if any((vk in b_low for vk in ('minimax', 'h3', 'fl2va', 'ref2va', 'hailuo', 'wan2', 'wan_', 'ltxv', 'hunyuan_video', 'mochi', 'vid_'))) and not any((ik in b_low for ik in ('krea', 'flux', 'sdxl', 'qwen_image'))):
        return True
    return False


def _is_baked_krea2_turbo_unet(unet_name: str) -> bool:
    b_low = os.path.basename(str(unet_name or '').replace('\\', '/')).lower()
    if not b_low or b_low == 'none':
        return False
    baked_turbo_tokens = ('turbo', 'schnell', 'cfgdistill', 'dmd2', 'lightning', 'hyper8', '4step', '8step')
    return any((tok in b_low for tok in baked_turbo_tokens))


def _classify_image_unet_architecture(unet_name: str, clip_type_str: str = 'krea2', unet_path: str = '') -> tuple:
    u_path_low = str(unet_name or '').replace('\\', '/').lower()
    u_low = os.path.basename(u_path_low)
    ct_low = str(clip_type_str or 'krea2').strip().lower()
    is_explicit_dit = any((dk in u_low for dk in ('krea', 'flux', 'qwen', 'chroma', 'schnell')))
    pony_tokens = ('pony', 'pdxl', 'autismmix', 'cyberrealistic_pony', 'cyberrealisticpony', 'ponyxl', 'pony_v6', 'pony-v6', 'prefect_pony', 'everclear_pony')
    ilxl_tokens = ('illustrious', 'ilxl', 'il-noob', 'il_noob', 'noobai', 'noob', 'wainsfw', 'wai-nsfw', 'wai_nsfw', 'wai-illustrious', 'wai_illustrious', 'wai-ani', 'inanime', 'arblend', 'hassaku', 'novaanime', 'nova_anime', 'miaomiao', 'amanatsu', 'cyberillustrious', 'prefect', 'obsessed')
    sdxl_tokens = ('sdxl', 'juggernaut', 'realvis', 'lustify', 'bigasp', 'dreamshaperxl', 'albedobase', 'zavychromaxl', 'copaxtimeless', 'epicrealismxl')
    is_pony = (not is_explicit_dit) and (ct_low == 'pony' or any((pk in u_path_low for pk in pony_tokens)))
    is_illustrious = (not is_explicit_dit) and (not is_pony) and (ct_low == 'illustrious' or any((ik in u_path_low for ik in ilxl_tokens)))
    is_sdxl_base = (not is_explicit_dit) and (not is_pony and not is_illustrious) and (ct_low in ('sdxl', 'stable_diffusion') or any((sk in u_path_low for sk in sdxl_tokens)))
    if (not is_explicit_dit) and (not is_pony) and (not is_illustrious) and (not is_sdxl_base) and u_low and u_low != 'none':
        try:
            from .engine_ez_05_cinematrix_video_lora_stack import _inspect_safetensors_header, _resolve_candidate_model_path
            full_p = unet_path or (folder_paths.get_full_path('checkpoints', unet_name) if hasattr(folder_paths, 'get_full_path') else None) or _resolve_candidate_model_path(unet_name)
            if full_p and os.path.exists(full_p):
                hdr = _inspect_safetensors_header(full_p)
                hdr_arch = str(hdr.get('arch', '') or '').lower()
                if hdr_arch == 'illustrious':
                    is_illustrious = True
                elif hdr_arch == 'pony':
                    is_pony = True
                elif hdr_arch == 'sdxl':
                    is_sdxl_base = True
        except Exception:
            pass
    is_sdxl_any = bool(is_pony or is_illustrious or is_sdxl_base)
    return (is_pony, is_illustrious, is_sdxl_base, is_sdxl_any)


def _resolve_canonical_image_arch_tag(unet_name: str, clip_type_str: str = 'krea2', unet_path: str = '') -> str:
    u_path_low = str(unet_name or '').replace('\\', '/').lower()
    u_low = os.path.basename(u_path_low)
    ct_low = str(clip_type_str or 'krea2').strip().lower()
    is_krea_name = any((kk in u_path_low for kk in ('krea', 'musebystableyogi', 'snofssexnudes')))
    is_qwen_name = (not is_krea_name) and any((qk in u_path_low for qk in ('qwen_image', 'qwen-image', 'qwenimage')))
    is_flux_name = (not is_krea_name) and (not is_qwen_name) and any((fk in u_path_low for fk in ('flux1', 'flux.1', 'flux-dev', 'flux_dev', 'flux-schnell', 'flux_schnell', 'schnell', 'chroma', 'shuttle', 'pixelwave_flux', 'acorn_is_spinning', 'flux')))
    if is_krea_name:
        return 'krea2'
    if is_qwen_name:
        return 'qwen_image'
    if is_flux_name:
        return 'flux'
    (is_pony, is_illustrious, is_sdxl_base, is_sdxl_any) = _classify_image_unet_architecture(unet_name, clip_type_str, unet_path=unet_path)
    if is_illustrious:
        return 'illustrious'
    if is_pony:
        return 'pony'
    if is_sdxl_base or is_sdxl_any:
        return 'sdxl'
    if u_low and u_low != 'none':
        try:
            from .engine_ez_05_cinematrix_video_lora_stack import _inspect_safetensors_header, _resolve_candidate_model_path
            full_p = unet_path or (folder_paths.get_full_path('diffusion_models', unet_name) if hasattr(folder_paths, 'get_full_path') else None) or (folder_paths.get_full_path('checkpoints', unet_name) if hasattr(folder_paths, 'get_full_path') else None) or _resolve_candidate_model_path(unet_name)
            if full_p and os.path.exists(full_p):
                hdr = _inspect_safetensors_header(full_p)
                hdr_arch = str(hdr.get('arch', '') or '').lower()
                if hdr_arch in ('flux', 'chroma'):
                    return 'flux'
                if hdr_arch == 'qwen_image':
                    return 'qwen_image'
        except Exception:
            pass
    if ct_low == 'flux':
        return 'flux'
    if ct_low == 'qwen_image':
        return 'qwen_image'
    return 'krea2'


def _resolve_flux_dual_clip_paths(clip_name: str) -> list:
    all_clips = [c for c in list_dynamic_clip_encoders() if c and c != 'None']
    t5_cands = sorted(
        [c for c in all_clips if any((tk in c.lower() for tk in ('t5xxl', 'umt5'))) and '32b' not in c.lower()],
        key=lambda x: (0 if 'fp8_e4m3fn_scaled' in x.lower() else (1 if 'fp8' in x.lower() else 2), len(x)),
    )
    clip_l_cands = sorted(
        [c for c in all_clips if ('clip_l' in c.lower() or 'vit-l' in c.lower()) and 't5' not in c.lower()],
        key=lambda x: (0 if os.path.basename(x).lower() == 'clip_l.safetensors' else 1, len(x)),
    )
    chosen_rel = []
    c_low = str(clip_name or '').lower()
    if clip_name and clip_name != 'None' and not any((bad in c_low for bad in ('qwen', 'krea', '32b', 'minimax', 'sdxl', 'pony', 'illustrious'))):
        if 't5' in c_low:
            if clip_l_cands:
                chosen_rel.append(clip_l_cands[0])
            chosen_rel.append(clip_name)
        elif 'clip_l' in c_low or 'vit-l' in c_low:
            chosen_rel.append(clip_name)
            if t5_cands:
                chosen_rel.append(t5_cands[0])
        else:
            chosen_rel.append(clip_name)
    if not chosen_rel:
        if clip_l_cands and t5_cands:
            chosen_rel = [clip_l_cands[0], t5_cands[0]]
        elif t5_cands:
            chosen_rel = [t5_cands[0]]
        elif clip_l_cands:
            chosen_rel = [clip_l_cands[0]]
        elif clip_name and clip_name != 'None':
            chosen_rel = [clip_name]
    resolved_paths = []
    for rel_c in chosen_rel:
        cp = folder_paths.get_full_path('text_encoders', rel_c) or folder_paths.get_full_path('clip', rel_c)
        if cp and cp not in resolved_paths:
            resolved_paths.append(cp)
    return resolved_paths


def _is_lora_sd_compatible_with_arch(lora_sd: dict, is_sdxl_family: bool) -> bool:
    if not isinstance(lora_sd, dict) or not lora_sd:
        return False
    sample_keys = [str(k).lower() for k in list(lora_sd.keys())[:96]]
    has_sdxl_keys = any(('lora_unet_input_blocks' in k or 'lora_unet_down_blocks' in k or 'lora_unet_middle_block' in k or 'lora_unet_output_blocks' in k or 'lora_te1_' in k or 'lora_te2_' in k or 'input_blocks.' in k or 'down_blocks.' in k) for k in sample_keys)
    has_dit_keys = any(('double_blocks' in k or 'single_blocks' in k or 'transformer_blocks' in k or 'joint_blocks' in k or 'lora_unet_double_blocks' in k or 'lora_unet_single_blocks' in k) for k in sample_keys)
    if is_sdxl_family and has_dit_keys and not has_sdxl_keys:
        return False
    if (not is_sdxl_family) and has_sdxl_keys and not has_dit_keys:
        return False
    return True



def list_dynamic_image_models():
    models = []
    for k in ('diffusion_models', 'unet', 'checkpoints', 'unet_gguf'):
        if k in folder_paths.folder_names_and_paths:
            models.extend(folder_paths.get_filename_list(k))
    cleaned = sorted((m for m in set(models) if not _is_non_unet_or_video_only_for_image(m)))
    return cleaned if cleaned else ['None']

def list_dynamic_clip_encoders():
    clips = []
    for k in ('text_encoders', 'clip', 'clip_gguf'):
        if k in folder_paths.folder_names_and_paths:
            clips.extend(folder_paths.get_filename_list(k))
    cleaned = sorted(set(clips))
    return cleaned if cleaned else ['None']

def list_dynamic_vaes():
    vaes = folder_paths.get_filename_list('vae') if 'vae' in folder_paths.folder_names_and_paths else []
    cleaned = sorted((v for v in set(vaes) if not any((tag in str(v).lower() for tag in ('_ez_fp16_vae_cache', '_ez_hadamard_v2_fp16_vae')))))
    return cleaned if cleaned else ['None']

def list_dynamic_loras_by_role(lock_turbo_only: bool=False):
    all_loras = sorted(set(folder_paths.get_filename_list('loras'))) if 'loras' in folder_paths.folder_names_and_paths else []
    if not lock_turbo_only:
        return ['None'] + all_loras
    turbo_keywords = ('turbo', 'step', 'distill', 'hyper', 'lcm', 'lightning', 'dmd', 'fast')
    turbo_filtered = [l for l in all_loras if any((tok in l.lower() for tok in turbo_keywords))]
    if turbo_filtered:
        return ['None'] + turbo_filtered
    return ['None'] + all_loras

def _detect_image_model_family(model) -> str:
    if model is None:
        return 'unknown'
    m_cfg = getattr(getattr(model, 'model', None), 'model_config', None)
    cfg_cls = str(getattr(m_cfg, '__class__', type(m_cfg)).__name__).lower()
    if 'flux' in cfg_cls or 'krea' in cfg_cls or 'chroma' in cfg_cls:
        return 'flux'
    if 'sd3' in cfg_cls or 'auraflow' in cfg_cls or 'wan' in cfg_cls or 'qwen' in cfg_cls or 'lumina' in cfg_cls:
        return 'sd3_flow'
    if 'sdxl' in cfg_cls or 'xl' in cfg_cls:
        return 'sdxl'
    return 'sd_unet'

def apply_krea2_dynamic_shift_patch(model, sampling_mode: str, width: int, height: int, manual_shift: float):
    if sampling_mode == 'bypass' or model is None:
        return model
    arch_fam = _detect_image_model_family(model)
    if arch_fam in ('sdxl', 'sd_unet'):
        return model
    if sampling_mode == 'raw_dynamic':
        (min_tokens, max_tokens) = (256.0, 6400.0)
        (min_shift, max_shift) = (0.5, 1.15)
        sw = math.ceil(max(64, int(width)) / 16.0) * 16.0
        sh = math.ceil(max(64, int(height)) / 16.0) * 16.0
        img_tokens = sw * sh / 256.0
        slope = (max_shift - min_shift) / (max_tokens - min_tokens)
        shift_val = slope * img_tokens + (min_shift - slope * min_tokens)
    elif sampling_mode == 'turbo_fixed':
        shift_val = 1.15 if arch_fam == 'flux' else 3.0
    else:
        shift_val = float(manual_shift)
    if arch_fam == 'sd3_flow' and hasattr(comfy.model_sampling, 'ModelSamplingSD3'):
        class ModelSamplingUniversalFlow(comfy.model_sampling.ModelSamplingSD3, comfy.model_sampling.CONST):
            _ez_flow_shift = True
        ms_obj = ModelSamplingUniversalFlow(model.model.model_config)
        ms_obj.set_parameters(shift=max(1.0, shift_val))
    else:
        class ModelSamplingKrea2(comfy.model_sampling.ModelSamplingFlux, comfy.model_sampling.CONST):
            _ez_krea2_shift = True
        ms_obj = ModelSamplingKrea2(model.model.model_config)
        ms_obj.set_parameters(shift=shift_val)
    cloned = model.clone()
    cloned.add_object_patch('model_sampling', ms_obj)
    return cloned

def _parse_comfy_quant_tensor(cq_tensor) -> dict:
    if not isinstance(cq_tensor, torch.Tensor):
        return {}
    try:
        raw_bytes = bytes((b for b in cq_tensor.detach().cpu().to(dtype=torch.uint8).view(-1).tolist() if b != 0))
        return json.loads(raw_bytes.decode('utf-8', errors='ignore').strip())
    except Exception:
        return {}

def _pre_dequantize_convrot_state_dict(sd: dict, metadata: dict=None, model_path: str='') -> bool:
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
    import importlib as _il
    try:
        q_ops_mod = _il.import_module('comfy.quant_ops')
    except Exception:
        q_ops_mod = getattr(comfy, 'quant_ops', None)
    native_algos = set(getattr(q_ops_mod, 'QUANT_ALGOS', {}).keys()) | {
        'float8_e4m3fn', 'float8_e5m2', 'int8_tensorwise', 'int8_blockwise',
        'nvfp4', 'mxfp8', 'asym_w4a8_int8', 'w6a8_int8', 'convrot_w4a4',
    }
    file_name_has_convrot = 'convrot' in os.path.basename(str(model_path or '')).lower()
    use_bf16 = hasattr(comfy.model_management, 'should_use_bf16') and comfy.model_management.should_use_bf16()
    fallback_fp16_dtype = torch.bfloat16 if use_bf16 else torch.float16
    vram_gb = 16.0
    if torch.cuda.is_available():
        try:
            vram_gb = float(torch.cuda.get_device_properties(0).total_memory) / (1024.0 ** 3)
        except Exception:
            vram_gb = 16.0
    allow_fp8_cast = bool(vram_gb < 28.0)
    fp8_dtype = getattr(torch, 'float8_e4m3fn', fallback_fp16_dtype) if allow_fp8_cast else fallback_fp16_dtype
    fp16_keep_tokens = (
        'patch_embedding', 'img_in', 'txt_in', 'final_layer', 'proj_out',
        'norm', 'time_in', 'vector_in', 'guidance_in', 'modulation', 'adaln', 'embed',
    )
    calc_dev = comfy.model_management.get_torch_device() if torch.cuda.is_available() else torch.device('cpu')
    weight_keys = [k for k in list(sd.keys()) if k.endswith('.weight') or k == 'weight']
    modified = False
    for w_key in weight_keys:
        w_t = sd.get(w_key, None)
        if not isinstance(w_t, torch.Tensor):
            continue
        prefix = w_key[:-6]
        layer_name = prefix[:-1] if prefix.endswith('.') else prefix
        cq_key = prefix + 'comfy_quant'
        q_cfg = _parse_comfy_quant_tensor(sd.get(cq_key, None))
        if not q_cfg and isinstance(meta_layers, dict):
            q_cfg = meta_layers.get(layer_name, {}) if isinstance(meta_layers.get(layer_name), dict) else {}
        q_fmt = str(q_cfg.get('format', '') or '').lower()
        scale_t = None
        for sc_suffix in ('weight_scale', 'scale_weight', 'weight.scale', 'scale'):
            if prefix + sc_suffix in sd and isinstance(sd[prefix + sc_suffix], torch.Tensor):
                scale_t = sd[prefix + sc_suffix]
                break
        has_rot_tensor = any((prefix + rs in sd for rs in ('hadamard_matrix', 'rot_matrix', 'rotation_matrix', 'hadamard')))
        layer_has_hadamard = (
            bool(q_cfg.get('convrot', False))
            or ('convrot' in q_fmt and q_fmt != 'convrot_w4a4')
            or ('hadamard' in q_fmt)
            or has_rot_tensor
            or (file_name_has_convrot and q_cfg.get('convrot') is not False and 'rowwise' not in q_fmt and 'tensorwise' not in q_fmt and scale_t is not None)
        )
        unsupported_fmt = bool(q_fmt and q_fmt not in native_algos)
        layer_needs_dequant = layer_has_hadamard or ('rowwise' in q_fmt) or unsupported_fmt
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
                elif w_fp32.ndim == 4 and blk > 0:
                    flat_in = int(w_fp32.shape[1] * w_fp32.shape[2] * w_fp32.shape[3])
                    if flat_in % blk == 0:
                        w_fp32 = (w_fp32.reshape(w_fp32.shape[0], -1, blk) @ rmat.T).reshape(w_fp32.shape)
                        explicit_rot = True
                break
        if not explicit_rot and layer_has_hadamard and (w_fp32.ndim >= 2):
            grp = int(q_cfg.get('convrot_groupsize') or q_cfg.get('group_size') or 256)
            flat_in = int(w_fp32.shape[1]) if w_fp32.ndim == 2 else int(w_fp32[0].numel())
            if grp >= 4 and flat_in % grp == 0:
                h_mat = _get_convrot_hadamard_matrix(grp, calc_dev, torch.float32)
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
        modified = True
    if modified:
        for k in [k for k in list(sd.keys()) if k.endswith('.comfy_quant') or k in ('last.down.weight', 'last.up.weight')]:
            sd.pop(k, None)
        if isinstance(metadata, dict):
            metadata.pop('_quantization_metadata', None)
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    return modified

def _dequantize_rowwise_module_fallback(module, _load_from_state_dict, state_dict, prefix, local_metadata, strict, missing_keys, unexpected_keys, error_msgs):
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
    q_cfg = _parse_comfy_quant_tensor(state_dict.get(prefix + 'comfy_quant', None))
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
            h_mat = _get_convrot_hadamard_matrix(grp, w_fp32.device, torch.float32)
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

def _ensure_int8_convrot_quant_compat(tier_profile: dict=None):
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
                from pathlib import Path as _P
                bp = _P(str(broken_path))
                stem_low = bp.stem.lower()
                is_minimax = any(k in stem_low for k in ('minimax', 'h3', 'vid_', 'wan', 'ltx', 'hunyuan')) and not any(dk in stem_low for dk in ('krea', 'flux', 'qwen'))
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

def _load_diffusion_model_convrot_safe(unet_path: str, tier_profile: dict=None):
    from pathlib import Path
    from .engine_ez_05_cinematrix_video_lora_stack import _inspect_safetensors_header
    _ensure_int8_convrot_quant_compat(tier_profile)
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
            except Exception:
                pass
    hdr_info = _inspect_safetensors_header(str(unet_path))
    if not hdr_info.get('needs_convrot_dequant', False):
        try:
            return comfy.sd.load_diffusion_model(str(unet_path))
        except Exception:
            pass
    try:
        loaded = comfy.utils.load_torch_file(unet_path, return_metadata=True)
        (sd, metadata) = loaded if isinstance(loaded, tuple) and len(loaded) == 2 else (loaded, None)
    except TypeError:
        sd = comfy.utils.load_torch_file(unet_path)
        metadata = None
    was_dequantized = _pre_dequantize_convrot_state_dict(sd, metadata=metadata, model_path=unet_path)
    if was_dequantized:
        return comfy.sd.load_diffusion_model_state_dict(sd)
    try:
        return comfy.sd.load_diffusion_model_state_dict(sd, metadata=metadata)
    except TypeError:
        return comfy.sd.load_diffusion_model_state_dict(sd)

_PRISM_IMAGE_LORA_CACHE: dict = {}


def _ez_prism_denoise_and_orthogonalize_lora_sd(
    lora_sd: dict,
    primary_basis_map: dict = None,
    is_primary: bool = False,
    is_turbo: bool = False,
    tail_threshold: float = 0.06,
    orth_strength: float = 0.65,
    cache_id: str = '',
) -> dict:
    if not isinstance(lora_sd, dict) or not lora_sd:
        return lora_sd
    if cache_id and cache_id in _PRISM_IMAGE_LORA_CACHE and primary_basis_map is None:
        return _PRISM_IMAGE_LORA_CACHE[cache_id]
    out_sd = dict(lora_sd)
    down_suffixes = ('.lora_down.weight', '.lora_a.weight', '_lora.down.weight')
    up_map = {
        '.lora_down.weight': '.lora_up.weight',
        '.lora_a.weight': '.lora_b.weight',
        '_lora.down.weight': '_lora.up.weight',
    }
    processed_pairs = 0
    try:
        with torch.no_grad():
            for k_down, v_down in list(lora_sd.items()):
                if not isinstance(v_down, torch.Tensor) or v_down.ndim != 2:
                    continue
                matched_sfx = next((sfx for sfx in down_suffixes if str(k_down).endswith(sfx)), None)
                if not matched_sfx:
                    continue
                stem = str(k_down)[:-len(matched_sfx)]
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
                    processed_pairs += 1
    except Exception:
        return lora_sd
    if cache_id and processed_pairs > 0 and primary_basis_map is None:
        if len(_PRISM_IMAGE_LORA_CACHE) >= 12:
            _PRISM_IMAGE_LORA_CACHE.pop(next(iter(_PRISM_IMAGE_LORA_CACHE)), None)
        _PRISM_IMAGE_LORA_CACHE[cache_id] = out_sd
    return out_sd


def load_and_split_image_models_with_loras(unet_name: str, clip_name: str, clip_type_str: str, vae_name: str, stop_at_clip_layer: int, sampling_mode: str, width: int, height: int, style_loras: list, turbo_lora_name: str, turbo_strength: float, positive_text: str, negative_text: str, tier_profile: dict=None):
    _ensure_int8_convrot_quant_compat(tier_profile)
    if hasattr(comfy.model_management, 'soft_empty_cache'):
        comfy.model_management.soft_empty_cache()
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    if not unet_name or unet_name == 'None' or _is_non_unet_or_video_only_for_image(unet_name):
        valid_img_unets = [u for u in list_dynamic_image_models() if u and u != 'None']
        krea_first = [u for u in valid_img_unets if 'krea' in os.path.basename(u).lower()] or valid_img_unets
        if krea_first:
            print(f'[EZ-03-SELF-HEAL] 🛡️ Ogiltig Bild-UNet "{unet_name}" (t.ex. Qwen3-VL/CLIP) -> Väljer automatiskt Krea 2 UNet: {krea_first[0]}')
            unet_name = krea_first[0]
    ckpt_only_path = folder_paths.get_full_path('checkpoints', unet_name)
    unet_path = folder_paths.get_full_path('diffusion_models', unet_name) or folder_paths.get_full_path('unet', unet_name) or ckpt_only_path
    unet_low = str(unet_name or '').lower()
    resolved_arch_tag = _resolve_canonical_image_arch_tag(unet_name, clip_type_str, unet_path=str(unet_path or ''))
    (is_pony_arch, is_illustrious_arch, _is_sdxl_base_arch, is_sdxl_family) = _classify_image_unet_architecture(unet_name, clip_type_str, unet_path=str(unet_path or ''))
    if resolved_arch_tag in ('illustrious', 'pony', 'sdxl'):
        is_sdxl_family = True
    is_flux_arch = (resolved_arch_tag == 'flux')
    is_flux_schnell = bool(is_flux_arch and 'schnell' in unet_low)
    ct_low = resolved_arch_tag if resolved_arch_tag in ('krea2', 'flux', 'qwen_image', 'illustrious', 'pony', 'sdxl') else str(clip_type_str or 'krea2').strip().lower()
    is_baked_krea_turbo = (not is_sdxl_family) and _is_baked_krea2_turbo_unet(unet_name)
    base_model = None
    embedded_clip = None
    embedded_vae = None
    if is_sdxl_family or (is_flux_arch and ckpt_only_path and str(unet_path) == str(ckpt_only_path)):
        try:
            ckpt_out = comfy.sd.load_checkpoint_guess_config(unet_path, output_vae=True, output_clip=True, embedding_directory=folder_paths.get_folder_paths('embeddings'))
            if isinstance(ckpt_out, (tuple, list)) and len(ckpt_out) >= 3 and (ckpt_out[0] is not None):
                (base_model, embedded_clip, embedded_vae) = (ckpt_out[0], ckpt_out[1], ckpt_out[2])
        except Exception:
            base_model = None
    if base_model is None:
        if resolved_arch_tag == 'krea2':
            print(f"[EZ-KREA2-03] 🧬 Active Architecture: KREA 2 (UNet: {os.path.basename(str(unet_name))} | TE: {os.path.basename(str(clip_name))} [Krea2TEModel_] | VAE: {os.path.basename(str(vae_name))}) — Note: ComfyUI logs 'model_type FLUX' internally because Krea 2 shares the 19/38 MMDiT block structure.")
        elif is_flux_arch:
            print(f"[EZ-03-FLUX-AUTO] 🧬 Active Architecture: FLUX.1 ({'Schnell 4-Step' if is_flux_schnell else 'Dev/Chroma'} | UNet: {os.path.basename(str(unet_name))})")
        base_model = _load_diffusion_model_convrot_safe(unet_path, tier_profile=tier_profile)
    clip_low = str(clip_name or '').lower()
    if ct_low in ('krea2', 'qwen_image') and (not clip_name or clip_name == 'None' or any((bk in clip_low for bk in ('32b', 'minimax_h3', 't5xxl', 'umt5', 'clip_l', 'clip_g', 'sdxl', 'pony', 'illustrious')))):
        all_img_clips = [c for c in list_dynamic_clip_encoders() if c and c != 'None']
        krea_4b_clips = [c for c in all_img_clips if any((k in c.lower() for k in ('4b', 'krea2', 'abliteratedcomfyui', 'qwen3vl_4b'))) and '32b' not in c.lower()]
        if krea_4b_clips:
            print(f'[EZ-03-SELF-HEAL] 🛡️ Byter felkopplad CLIP "{clip_name}" -> Krea 2 4B Text Encoder: {krea_4b_clips[0]}')
            clip_name = krea_4b_clips[0]
            clip_low = str(clip_name or '').lower()
    if is_sdxl_family and embedded_clip is not None:
        print(f'[EZ-03-{resolved_arch_tag.upper()}] 🧬 Använder inbakad Dual CLIP-L/G direkt från checkpoint: {os.path.basename(str(unet_name))}')
        clip_target = embedded_clip
    elif is_flux_arch and embedded_clip is not None:
        print(f'[EZ-03-FLUX-AUTO] 🧬 Använder inbakad Dual CLIP (CLIP-L + T5) direkt från Flux-checkpoint: {os.path.basename(str(unet_name))}')
        clip_target = embedded_clip
    elif is_flux_arch:
        flux_clip_paths = _resolve_flux_dual_clip_paths(clip_name)
        print(f"[EZ-03-FLUX-AUTO] 🧬 Laddar Flux Text Encoder(s): {[os.path.basename(p) for p in flux_clip_paths]}")
        clip_target = comfy.sd.load_clip(ckpt_paths=flux_clip_paths, embedding_directory=folder_paths.get_folder_paths('embeddings'), clip_type=getattr(comfy.sd.CLIPType, 'FLUX', comfy.sd.CLIPType.STABLE_DIFFUSION))
    else:
        clip_path = folder_paths.get_full_path('text_encoders', clip_name) or folder_paths.get_full_path('clip', clip_name)
        krea2_native_key = 'KREA2' if hasattr(comfy.sd.CLIPType, 'KREA2') else 'FLUX'
        clip_alias_map = {'KREA2': krea2_native_key, 'FLUX': 'FLUX', 'SDXL': 'STABLE_DIFFUSION', 'PONY': 'STABLE_DIFFUSION', 'ILLUSTRIOUS': 'STABLE_DIFFUSION', 'SD3': 'SD3', 'QWEN_IMAGE': 'QWEN_IMAGE', 'WAN': 'WAN', 'STABLE_DIFFUSION': 'STABLE_DIFFUSION'}
        mapped_clip_key = clip_alias_map.get(ct_low.upper(), ct_low.upper() or krea2_native_key)
        resolved_clip_type = getattr(comfy.sd.CLIPType, mapped_clip_key, getattr(comfy.sd.CLIPType, krea2_native_key, comfy.sd.CLIPType.STABLE_DIFFUSION))
        clip_target = comfy.sd.load_clip(ckpt_paths=[clip_path], embedding_directory=folder_paths.get_folder_paths('embeddings'), clip_type=resolved_clip_type)
    eff_clip_layer = -2 if (is_pony_arch or is_illustrious_arch) and int(stop_at_clip_layer) == -1 else int(stop_at_clip_layer)
    if eff_clip_layer < -1 and (is_sdxl_family or ct_low in ('stable_diffusion', 'sdxl', 'pony', 'illustrious')):
        clip_target = clip_target.clone()
        clip_target.clip_layer(eff_clip_layer)
    vae_low = str(vae_name or '').lower()
    image_vae = None
    if is_sdxl_family and (not vae_name or vae_name == 'None' or any((vk in vae_low for vk in ('qwen', 'krea', 'ae.safetensors', 'ae.sft', 'flux', 'minimax', 'h3', 'video_vae', 'audio_vae', 'wan', 'hunyuan')))):
        sdxl_vaes = [v for v in list_dynamic_vaes() if v and v != 'None' and any((sk in v.lower() for sk in ('sdxl', 'pony', 'illustrious')))]
        if embedded_vae is not None:
            print(f'[EZ-03-{resolved_arch_tag.upper()}] 🎨 Använder inbakad 4ch {resolved_arch_tag.upper()}-VAE direkt från checkpoint: {os.path.basename(str(unet_name))}')
            image_vae = embedded_vae
        elif sdxl_vaes:
            print(f'[EZ-03-{resolved_arch_tag.upper()}] 🛡️ Byter 16ch Krea/Flux-VAE "{vae_name}" -> 4ch SDXL-VAE: {sdxl_vaes[0]}')
            vae_name = sdxl_vaes[0]
            vae_low = str(vae_name or '').lower()
    elif is_flux_arch and (not vae_name or vae_name == 'None' or any((vk in vae_low for vk in ('qwen_image_vae', 'krea', 'minimax', 'h3', 'video_vae', 'audio_vae', 'hunyuan', 'sdxl', 'pony', 'illustrious')))):
        all_vaes = [v for v in list_dynamic_vaes() if v and v != 'None']
        flux_vaes = sorted(
            [v for v in all_vaes if (os.path.basename(v).lower() in ('ae.safetensors', 'ae.sft') or 'flux_vae' in v.lower() or 'flux' in v.lower()) and not any((vk in v.lower() for vk in ('minimax', 'video_vae', 'audio_vae', 'sdxl', 'pony', 'illustrious')))],
            key=lambda x: (0 if os.path.basename(x).lower() in ('ae.safetensors', 'ae.sft') else 1, len(x)),
        )
        if embedded_vae is not None:
            print(f'[EZ-03-FLUX-AUTO] 🎨 Använder inbakad 16ch Flux-VAE direkt från checkpoint: {os.path.basename(str(unet_name))}')
            image_vae = embedded_vae
        elif flux_vaes:
            print(f'[EZ-03-FLUX-AUTO] 🛡️ Byter "{vae_name}" -> 16ch Flux VAE: {flux_vaes[0]}')
            vae_name = flux_vaes[0]
            vae_low = str(vae_name or '').lower()
    elif any((vk in vae_low for vk in ('minimax', 'h3', 'video_vae', 'audio_vae', 'hunyuan_video', '_ez_hadamard_v2_fp16_vae', '_ez_fp16_vae_cache', 'sdxl', 'pony', 'illustrious'))) or (resolved_arch_tag == 'krea2' and ('flux_vae' in vae_low or os.path.basename(vae_low) in ('ae.safetensors', 'ae.sft'))) or not vae_name or vae_name == 'None':
        all_vaes = [v for v in list_dynamic_vaes() if v and v != 'None']
        krea_qwen_vaes = [v for v in all_vaes if ('qwen_image_vae' in v.lower() or 'krea' in v.lower()) and not any((vk in v.lower() for vk in ('minimax', 'video_vae', 'audio_vae', 'sdxl', 'pony', 'illustrious')))]
        fallback_16ch = [v for v in all_vaes if (os.path.basename(v).lower() in ('ae.safetensors', 'ae.sft') or 'flux_vae' in v.lower()) and not any((vk in v.lower() for vk in ('minimax', 'video_vae', 'audio_vae', 'sdxl', 'pony', 'illustrious')))]
        chosen_krea_vaes = krea_qwen_vaes or fallback_16ch
        if chosen_krea_vaes and vae_name != chosen_krea_vaes[0]:
            print(f'[EZ-03-SELF-HEAL] 🛡️ Byter felkopplad VAE "{vae_name}" -> 16ch Krea2/Qwen Image-VAE: {chosen_krea_vaes[0]}')
            vae_name = chosen_krea_vaes[0]
    if image_vae is None:
        vae_path = folder_paths.get_full_path('vae', vae_name)
        loaded_vae = comfy.utils.load_torch_file(vae_path, return_metadata=True)
        (vae_sd, vae_meta) = loaded_vae if isinstance(loaded_vae, tuple) and len(loaded_vae) == 2 else (loaded_vae, None)
        try:
            image_vae = comfy.sd.VAE(sd=vae_sd, metadata=vae_meta)
        except TypeError:
            image_vae = comfy.sd.VAE(sd=vae_sd)
    patched_model = base_model
    patched_clip = clip_target
    sdxl_lora_tokens = ('pony', 'pdxl', 'illustrious', 'ilxl', 'il-noob', 'il_noob', 'lora-ilxl', 'noobai', 'sdxl', 'dmd2', 'sdxl_lightning', 'wai_nsfw', 'wainsfw', 'flatline', 'bring_back_flat', 'anime_screencap')
    dit_lora_tokens = ('krea', 'qwen', 'flux', 'snofs')
    krea_only_tokens = ('krea', 'snofs', 'raw_to_turbo', 'qwen_image', 'qwen-image')
    flux_turbo_only_tokens = ('flux_turbo', 'flux-turbo', 'flux.1-turbo', 'hyper-flux', 'hyper_flux')
    lora_ram_cache = globals().setdefault('_EZ_LORA_SD_RAM_CACHE', {})
    applied_style_count = 0
    for lora_entry in style_loras:
        if not isinstance(lora_entry, (list, tuple)) or len(lora_entry) < 2:
            continue
        lora_file = lora_entry[0]
        m_str = float(lora_entry[1])
        c_str = float(lora_entry[2]) if len(lora_entry) >= 3 else m_str
        if lora_file and lora_file != 'None' and (abs(m_str) > 1e-05 or abs(c_str) > 1e-05):
            l_low = str(lora_file).lower()
            if is_sdxl_family and any((kk in l_low for kk in dit_lora_tokens)):
                print(f'[EZ-03-{resolved_arch_tag.upper()}] 🛡️ Ignorerar Krea2/Flux-LoRA "{lora_file}" vid körning av {resolved_arch_tag.upper()}.')
                continue
            if not is_sdxl_family and any((sk in l_low for sk in sdxl_lora_tokens)):
                print(f'[EZ-03-{resolved_arch_tag.upper()}] 🛡️ Ignorerar SDXL/Pony/Illustrious-LoRA "{lora_file}" vid körning av {resolved_arch_tag.upper()}.')
                continue
            if is_flux_arch and any((kt in l_low for kt in krea_only_tokens)):
                print(f'[EZ-03-FLUX-AUTO] 🛡️ Ignorerar Krea2/Qwen-specifik LoRA "{lora_file}" vid körning av Flux.1.')
                continue
            l_path = folder_paths.get_full_path('loras', lora_file)
            if l_path:
                if l_path in lora_ram_cache:
                    lora_sd = lora_ram_cache[l_path]
                else:
                    lora_sd = comfy.utils.load_torch_file(l_path, safe_load=True)
                    lora_sd = _ez_prism_denoise_and_orthogonalize_lora_sd(
                        lora_sd,
                        primary_basis_map=None,
                        is_primary=(applied_style_count == 0),
                        is_turbo=False,
                        tail_threshold=0.0,
                        orth_strength=0.0,
                    )
                    if len(lora_ram_cache) >= 8:
                        lora_ram_cache.pop(next(iter(lora_ram_cache)), None)
                    lora_ram_cache[l_path] = lora_sd
                if not _is_lora_sd_compatible_with_arch(lora_sd, is_sdxl_family):
                    print(f'[EZ-03-ARCH-SHIELD] 🛡️ Ignorerade arkitektur-inkompatibel LoRA "{lora_file}" (SDXL={is_sdxl_family}) via tensor-nyckelkontroll.')
                    continue
                has_te_keys = any(('lora_te' in str(k).lower() or 'text_model' in str(k).lower() or 'clip_' in str(k).lower() or 'te_' in str(k).lower()) for k in lora_sd.keys())
                eff_clip_arg = patched_clip if (has_te_keys and abs(c_str) > 1e-05) else None
                (patched_model, next_clip) = comfy.sd.load_lora_for_models(patched_model, eff_clip_arg, lora_sd, m_str, c_str if eff_clip_arg is not None else 0.0)
                if next_clip is not None:
                    patched_clip = next_clip
                applied_style_count += 1
    if is_baked_krea_turbo:
        if turbo_lora_name and turbo_lora_name != 'None' and (abs(float(turbo_strength)) > 1e-05):
            print(f'[EZ-03-TURBO-GUARD] ⚡ Bild-UNet "{os.path.basename(str(unet_name))}" har redan inbakad Turbo-destillering -> kopplar ur extern Stage-2 Turbo-LoRA ({float(turbo_strength):.2f} -> 0.00) för att förhindra dubbel-turbo och kontrastfritering.')
        turbo_lora_name = 'None'
        turbo_strength = 0.0
    eff_sampling_mode = 'bypass' if is_sdxl_family else ('turbo_fixed' if (is_baked_krea_turbo and sampling_mode != 'bypass') else sampling_mode)
    stage1_model = apply_krea2_dynamic_shift_patch(patched_model.clone(), eff_sampling_mode, width, height, 1.15)
    stage2_model = patched_model.clone()
    t_low = str(turbo_lora_name or '').lower()
    sdxl_dmd2_active = False
    flux_turbo_lora_active = False
    cross_dit_turbo_mismatch = bool((is_flux_arch and any((kt in t_low for kt in krea_only_tokens))) or (resolved_arch_tag == 'krea2' and any((ft in t_low for ft in flux_turbo_only_tokens))))
    if cross_dit_turbo_mismatch and turbo_lora_name and turbo_lora_name != 'None' and (abs(float(turbo_strength)) > 1e-05):
        print(f'[EZ-03-ARCH-SHIELD] 🛡️ Ignorerar arkitektur-inkompatibel Turbo-LoRA "{turbo_lora_name}" vid körning av {resolved_arch_tag.upper()}.')
    has_valid_turbo = bool((not is_baked_krea_turbo) and (not cross_dit_turbo_mismatch) and turbo_lora_name and turbo_lora_name != 'None' and (abs(float(turbo_strength)) > 1e-05) and (not (is_sdxl_family and any((kk in t_low for kk in dit_lora_tokens)))) and (not (not is_sdxl_family and any((sk in t_low for sk in sdxl_lora_tokens)))))
    if has_valid_turbo:
        t_path = folder_paths.get_full_path('loras', turbo_lora_name)
        if t_path:
            if t_path in lora_ram_cache:
                turbo_sd = lora_ram_cache[t_path]
            else:
                turbo_sd = comfy.utils.load_torch_file(t_path, safe_load=True)
                lora_ram_cache[t_path] = turbo_sd
            if _is_lora_sd_compatible_with_arch(turbo_sd, is_sdxl_family):
                (stage2_model, _) = comfy.sd.load_lora_for_models(stage2_model, None, turbo_sd, float(turbo_strength), 0.0)
                if is_sdxl_family:
                    (stage1_model, _) = comfy.sd.load_lora_for_models(stage1_model, None, turbo_sd, float(turbo_strength), 0.0)
                    sdxl_dmd2_active = True
                elif is_flux_arch:
                    (stage1_model, _) = comfy.sd.load_lora_for_models(stage1_model, None, turbo_sd, float(turbo_strength), 0.0)
                    flux_turbo_lora_active = True
            else:
                print(f'[EZ-03-ARCH-SHIELD] 🛡️ Hoppar över inkompatibel Turbo-LoRA "{turbo_lora_name}" (SDXL={is_sdxl_family}).')
                has_valid_turbo = False
        if has_valid_turbo:
            stage2_shift_mode = 'turbo_fixed' if eff_sampling_mode != 'bypass' else 'bypass'
            stage2_model = apply_krea2_dynamic_shift_patch(stage2_model, stage2_shift_mode, width, height, 1.15)
        else:
            stage2_model = apply_krea2_dynamic_shift_patch(stage2_model, eff_sampling_mode, width, height, 1.15)
    else:
        stage2_model = apply_krea2_dynamic_shift_patch(stage2_model, eff_sampling_mode, width, height, 1.15)
    setattr(stage1_model, '_ez_base_model', base_model)
    setattr(stage1_model, '_ez_base_clip', clip_target)
    setattr(stage1_model, '_ez_baked_in_turbo', bool(is_baked_krea_turbo))
    setattr(stage2_model, '_ez_baked_in_turbo', bool(is_baked_krea_turbo))
    setattr(stage1_model, '_ez_image_arch', resolved_arch_tag)
    setattr(stage2_model, '_ez_image_arch', resolved_arch_tag)
    setattr(stage1_model, '_ez_sdxl_dmd2_active', bool(sdxl_dmd2_active))
    setattr(stage2_model, '_ez_sdxl_dmd2_active', bool(sdxl_dmd2_active))
    setattr(stage1_model, '_ez_flux_schnell_active', bool(is_flux_schnell))
    setattr(stage2_model, '_ez_flux_schnell_active', bool(is_flux_schnell))
    setattr(stage1_model, '_ez_flux_turbo_lora_active', bool(flux_turbo_lora_active))
    setattr(stage2_model, '_ez_flux_turbo_lora_active', bool(flux_turbo_lora_active))
    setattr(stage1_model, '_ez_turbo_spec', (turbo_lora_name if has_valid_turbo else 'None', float(turbo_strength) if has_valid_turbo else 0.0, eff_sampling_mode, int(width), int(height), bool(is_sdxl_family)))
    setattr(patched_clip, '_ez_cond_cache', _IMAGE_CLIP_COND_CACHE)
    pos_clean = str(positive_text or '').strip()
    neg_clean = str(negative_text or '').strip()
    if pos_clean:
        clip_lora_sig = tuple((str(x[0]), round(float(x[2]), 3)) for x in (style_loras or []) if isinstance(x, (list, tuple)) and len(x) >= 3 and x[0] and x[0] != 'None' and abs(float(x[2])) > 1e-05)
        clip_ns = (str(unet_name or ''), str(clip_name or ''), ct_low, int(eff_clip_layer), clip_lora_sig)
        pos_key = ('pos', clip_ns, pos_clean)
        neg_key = ('neg', clip_ns, neg_clean)
        pair_key = (clip_ns, pos_clean, neg_clean)
        did_encode = False
        if pos_key in _IMAGE_CLIP_COND_CACHE:
            pos_cond = _IMAGE_CLIP_COND_CACHE[pos_key]
        elif pair_key in _IMAGE_CLIP_COND_CACHE:
            pos_cond = _IMAGE_CLIP_COND_CACHE[pair_key][0]
            _IMAGE_CLIP_COND_CACHE[pos_key] = pos_cond
        else:
            pos_tokens = patched_clip.tokenize(pos_clean)
            pos_cond = patched_clip.encode_from_tokens_scheduled(pos_tokens)
            _IMAGE_CLIP_COND_CACHE[pos_key] = pos_cond
            did_encode = True
        if neg_key in _IMAGE_CLIP_COND_CACHE:
            neg_cond = _IMAGE_CLIP_COND_CACHE[neg_key]
        elif pair_key in _IMAGE_CLIP_COND_CACHE:
            neg_cond = _IMAGE_CLIP_COND_CACHE[pair_key][1]
            _IMAGE_CLIP_COND_CACHE[neg_key] = neg_cond
        else:
            neg_tokens = patched_clip.tokenize(neg_clean)
            neg_cond = patched_clip.encode_from_tokens_scheduled(neg_tokens)
            _IMAGE_CLIP_COND_CACHE[neg_key] = neg_cond
            did_encode = True
        _IMAGE_CLIP_COND_CACHE[pair_key] = (pos_cond, neg_cond)
        if did_encode and hasattr(comfy.model_management, 'soft_empty_cache'):
            comfy.model_management.soft_empty_cache()
    else:
        pos_cond = None
        neg_cond = None
    return (stage1_model, stage2_model, pos_cond, neg_cond, image_vae, patched_clip)


def scale_style_loras_for_target(raw_style_loras: list, style_low: str, age_years: int = 25, has_orc_tusks: bool = False) -> list:
    s_low = str(style_low or 'realism').strip().lower()
    if s_low.startswith('original'):
        s_low = 'original'
    yrs = max(18, min(95, int(age_years or 25)))
    if yrs <= 20:
        age_pore_mult = 0.35
        age_snofs_mult = 0.55
    elif yrs <= 24:
        age_pore_mult = 0.52
        age_snofs_mult = 0.72
    elif yrs <= 29:
        age_pore_mult = 0.68
        age_snofs_mult = 0.85
    elif yrs <= 39:
        age_pore_mult = 0.92
        age_snofs_mult = 1.0
    else:
        age_pore_mult = 1.25
        age_snofs_mult = 1.15
    if has_orc_tusks:
        age_pore_mult *= 0.78
        age_snofs_mult *= 0.55
    pore_photo_pat = ('realism', 'realistic', 'photoreal', 'photoslider', 'photo_slider', 'skin_detail', 'skindetail', 'skin-detail', 'pores', 'raw_photo', '35mm', 'dslr', 'amateur_photo', 'detailer', 'ultra_real', 'ultrareal', 'real_3d', 'real3d', 'goodgirl')
    snofs_pat = ('snofs',)
    anime_2d_pat = ('2d_anime', 'anime_screencap', 'screencap', 'cartoon', 'manga', 'cel_shad', 'cel-shad', 'celshad', 'lineart', 'ghibli', 'flat_color', 'flatline', 'bring_back_flat')
    out_pairs = []
    for lp in (raw_style_loras or []):
        if not isinstance(lp, (list, tuple)) or len(lp) < 2:
            continue
        l_name = str(lp[0] or 'None')
        m_w = float(lp[1])
        c_w = float(lp[2]) if len(lp) >= 3 else m_w
        if l_name == 'None' or (abs(m_w) <= 1e-5 and abs(c_w) <= 1e-5):
            out_pairs.append(('None', 0.0, 0.0))
            continue
        ln_low = os.path.basename(str(l_name).replace('\\', '/')).lower()
        is_2d_anime = any((tok in ln_low for tok in anime_2d_pat))
        is_pore_photo = any((tok in ln_low for tok in pore_photo_pat)) and not is_2d_anime
        is_snofs = any((tok in ln_low for tok in snofs_pat)) and not is_pore_photo and not is_2d_anime
        if s_low in ('cartoonish', 'anime'):
            if is_pore_photo or is_snofs:
                if m_w < -1e-05:
                    eff_neg_c = c_w if c_w <= 0.0 else -abs(c_w) * 0.5
                    out_pairs.append((l_name, round(max(-1.25, m_w), 3), round(max(-1.25, eff_neg_c), 3)))
                else:
                    out_pairs.append(('None', 0.0, 0.0))
            else:
                out_pairs.append((l_name, round(m_w, 3), round(c_w, 3)))
        elif (is_pore_photo or is_snofs) and m_w < -1e-05:
            print(f'[EZ-03-ANTI3D-GUARD] 🛡️ 3D/Foto-stil ({s_low}) aktiv -> Kopplar automatiskt ur negativ Anti-3D slider "{os.path.basename(str(l_name))}" ({m_w:+.2f}) så 3D-djupet bevaras.')
            out_pairs.append(('None', 0.0, 0.0))
        elif is_2d_anime and s_low in ('realism', 'cinematic-film-35mm', 'dark-fantasy-real', 'dark-fantasy-cgi', 'dark-fantasy', 'unreal-engine-5'):
            out_pairs.append(('None', 0.0, 0.0))
        elif s_low == 'semi-real':
            if is_pore_photo:
                out_pairs.append(('None', 0.0, 0.0))
            elif is_snofs:
                out_pairs.append((l_name, round(m_w * 0.20 * age_snofs_mult, 3), round(c_w * 0.20 * age_snofs_mult, 3)))
            else:
                out_pairs.append((l_name, round(m_w * 0.85 if ('illustrious' in str(l_name).lower() or 'ilxl' in str(l_name).lower()) else m_w * 0.55, 3), round(c_w * 0.85 if ('illustrious' in str(l_name).lower() or 'ilxl' in str(l_name).lower()) else c_w * 0.55, 3)))
        elif s_low == 'original':
            if is_pore_photo:
                out_pairs.append((l_name, round(min(1.0, m_w * 0.90 * age_pore_mult), 3), round(min(1.0, c_w * 0.90 * age_pore_mult), 3)))
            elif is_snofs:
                out_pairs.append((l_name, round(min(1.0, m_w * 0.88 * age_snofs_mult), 3), round(min(1.0, c_w * 0.88 * age_snofs_mult), 3)))
            else:
                out_pairs.append((l_name, round(m_w * 0.90, 3), round(c_w * 0.90, 3)))
        elif s_low == 'unreal-engine-5':
            if is_pore_photo:
                out_pairs.append((l_name, round(m_w * 0.28 * age_pore_mult, 3), round(c_w * 0.28 * age_pore_mult, 3)))
            elif is_snofs:
                out_pairs.append((l_name, round(m_w * 0.40 * age_snofs_mult, 3), round(c_w * 0.40 * age_snofs_mult, 3)))
            else:
                out_pairs.append((l_name, round(m_w * 0.65, 3), round(c_w * 0.65, 3)))
        elif s_low in ('dark-fantasy-real', 'dark-fantasy'):
            if is_pore_photo:
                out_pairs.append((l_name, round(min(1.0, m_w * 0.92 * age_pore_mult), 3), round(min(1.0, c_w * 0.92 * age_pore_mult), 3)))
            elif is_snofs:
                out_pairs.append((l_name, round(min(1.0, m_w * 0.90 * age_snofs_mult), 3), round(min(1.0, c_w * 0.90 * age_snofs_mult), 3)))
            else:
                out_pairs.append((l_name, round(min(1.0, m_w * 0.95), 3), round(min(1.0, c_w * 0.95), 3)))
        elif s_low == 'dark-fantasy-cgi':
            if is_pore_photo:
                out_pairs.append((l_name, round(m_w * 0.65 * age_pore_mult, 3), round(c_w * 0.65 * age_pore_mult, 3)))
            elif is_snofs:
                out_pairs.append((l_name, round(m_w * 0.70 * age_snofs_mult, 3), round(c_w * 0.70 * age_snofs_mult, 3)))
            else:
                out_pairs.append((l_name, round(m_w * 0.88, 3), round(c_w * 0.88, 3)))
        elif s_low == 'cinematic-film-35mm':
            if is_pore_photo:
                out_pairs.append((l_name, round(min(1.0, m_w * 0.82 * age_pore_mult), 3), round(min(1.0, c_w * 0.82 * age_pore_mult), 3)))
            elif is_snofs:
                out_pairs.append((l_name, round(min(1.0, m_w * 0.85 * age_snofs_mult), 3), round(min(1.0, c_w * 0.85 * age_snofs_mult), 3)))
            else:
                out_pairs.append((l_name, round(m_w, 3), round(c_w, 3)))
        else:
            if is_pore_photo:
                out_pairs.append((l_name, round(min(1.0, m_w * age_pore_mult), 3), round(min(1.0, c_w * age_pore_mult), 3)))
            elif is_snofs:
                out_pairs.append((l_name, round(min(1.0, m_w * age_snofs_mult), 3), round(min(1.0, c_w * age_snofs_mult), 3)))
            else:
                out_pairs.append((l_name, round(m_w, 3), round(c_w, 3)))
    return out_pairs


def rebuild_models_for_style_target(stage1_model, stage2_model, image_clip, style_low: str, age_years: int = 25, has_orc_tusks: bool = False):
    s_low = str(style_low or 'realism').strip().lower()
    if s_low.startswith('original'):
        s_low = 'original'
    yrs = max(18, min(95, int(age_years or 25)))
    tusk_flag = int(bool(has_orc_tusks))
    target_key = f'{s_low}:{yrs}:{tusk_flag}'
    if stage1_model is None or getattr(stage1_model, '_ez_applied_style_age_key', None) == target_key:
        return (stage1_model, stage2_model, image_clip)
    base_model = getattr(stage1_model, '_ez_base_model', None)
    base_clip = getattr(stage1_model, '_ez_base_clip', image_clip)
    raw_loras = getattr(stage1_model, '_ez_raw_style_loras', None)
    turbo_spec = getattr(stage1_model, '_ez_turbo_spec', None)
    if base_model is None or not isinstance(raw_loras, list) or not isinstance(turbo_spec, tuple):
        return (stage1_model, stage2_model, image_clip)
    (turbo_lora_name, turbo_strength, eff_sampling_mode, width, height, is_sdxl_family) = turbo_spec
    scaled_loras = scale_style_loras_for_target(raw_loras, s_low, age_years=yrs, has_orc_tusks=bool(has_orc_tusks))
    lora_ram_cache = globals().setdefault('_EZ_LORA_SD_RAM_CACHE', {})
    patched_model = base_model
    patched_clip = base_clip
    sdxl_lora_tokens = ('pony', 'pdxl', 'illustrious', 'ilxl', 'il-noob', 'il_noob', 'lora-ilxl', 'noobai', 'sdxl', 'dmd2', 'sdxl_lightning', 'wai_nsfw', 'flatline', 'bring_back_flat', 'anime_screencap')
    dit_lora_tokens = ('krea', 'qwen', 'flux', 'snofs')
    applied_cnt = 0
    for lp in scaled_loras:
        l_file, m_str, c_str = lp[0], float(lp[1]), float(lp[2])
        if l_file and l_file != 'None' and (abs(m_str) > 1e-5 or abs(c_str) > 1e-5):
            l_low = str(l_file).lower()
            if (is_sdxl_family and any((kk in l_low for kk in dit_lora_tokens))) or (not is_sdxl_family and any((sk in l_low for sk in sdxl_lora_tokens))):
                continue
            l_path = folder_paths.get_full_path('loras', l_file)
            if l_path:
                lora_sd = lora_ram_cache.get(l_path)
                if lora_sd is None:
                    lora_sd = comfy.utils.load_torch_file(l_path, safe_load=True)
                    lora_sd = _ez_prism_denoise_and_orthogonalize_lora_sd(lora_sd, primary_basis_map=None, is_primary=(applied_cnt == 0), is_turbo=False, tail_threshold=0.0, orth_strength=0.0)
                    lora_ram_cache[l_path] = lora_sd
                if not _is_lora_sd_compatible_with_arch(lora_sd, is_sdxl_family):
                    continue
                has_te = any(('lora_te' in str(k).lower() or 'text_model' in str(k).lower() or 'clip_' in str(k).lower() or 'te_' in str(k).lower()) for k in lora_sd.keys())
                eff_c = patched_clip if (has_te and abs(c_str) > 1e-5) else None
                (patched_model, next_c) = comfy.sd.load_lora_for_models(patched_model, eff_c, lora_sd, m_str, c_str if eff_c is not None else 0.0)
                if next_c is not None:
                    patched_clip = next_c
                applied_cnt += 1
    new_s1 = apply_krea2_dynamic_shift_patch(patched_model.clone(), eff_sampling_mode, width, height, 1.15)
    new_s2 = patched_model.clone()
    t_low = str(turbo_lora_name or '').lower()
    bypass_krea_turbo_2d = bool((s_low in ('cartoonish', 'anime')) and (not is_sdxl_family))
    sdxl_dmd2_active = False
    has_valid_turbo = bool((not bypass_krea_turbo_2d) and turbo_lora_name and turbo_lora_name != 'None' and (abs(float(turbo_strength)) > 1e-05) and (not (is_sdxl_family and any((kk in t_low for kk in dit_lora_tokens)))) and (not (not is_sdxl_family and any((sk in t_low for sk in sdxl_lora_tokens)))))
    if has_valid_turbo:
        t_path = folder_paths.get_full_path('loras', turbo_lora_name)
        if t_path:
            turbo_sd = lora_ram_cache.get(t_path) or comfy.utils.load_torch_file(t_path, safe_load=True)
            lora_ram_cache[t_path] = turbo_sd
            if _is_lora_sd_compatible_with_arch(turbo_sd, is_sdxl_family):
                eff_t_str = float(turbo_strength)
                (new_s2, _) = comfy.sd.load_lora_for_models(new_s2, None, turbo_sd, eff_t_str, 0.0)
                if is_sdxl_family:
                    (new_s1, _) = comfy.sd.load_lora_for_models(new_s1, None, turbo_sd, eff_t_str, 0.0)
                    sdxl_dmd2_active = True
            else:
                has_valid_turbo = False
        if has_valid_turbo:
            stage2_shift_mode = 'turbo_fixed' if eff_sampling_mode != 'bypass' else 'bypass'
            new_s2 = apply_krea2_dynamic_shift_patch(new_s2, stage2_shift_mode, width, height, 1.15)
        else:
            new_s2 = apply_krea2_dynamic_shift_patch(new_s2, eff_sampling_mode, width, height, 1.15)
    else:
        new_s2 = apply_krea2_dynamic_shift_patch(new_s2, eff_sampling_mode, width, height, 1.15)
    baked_flag = bool(getattr(stage1_model, '_ez_baked_in_turbo', False))
    prev_unet_name = str(getattr(stage1_model, '_ez_active_image_unet', '') or '')
    prev_arch_tag = str(getattr(stage1_model, '_ez_image_arch', 'sdxl' if is_sdxl_family else 'krea2') or ('sdxl' if is_sdxl_family else 'krea2'))
    for m_obj in (new_s1, new_s2):
        setattr(m_obj, '_ez_base_model', base_model)
        setattr(m_obj, '_ez_base_clip', base_clip)
        setattr(m_obj, '_ez_baked_in_turbo', baked_flag)
        setattr(m_obj, '_ez_image_arch', prev_arch_tag)
        setattr(m_obj, '_ez_sdxl_dmd2_active', bool(sdxl_dmd2_active))
        setattr(m_obj, '_ez_active_image_unet', prev_unet_name)
        setattr(m_obj, '_ez_active_style_loras', list(scaled_loras))
        setattr(m_obj, '_ez_raw_style_loras', list(raw_loras))
        setattr(m_obj, '_ez_turbo_spec', turbo_spec)
        setattr(m_obj, '_ez_applied_style_low', s_low)
        setattr(m_obj, '_ez_applied_style_age_key', target_key)
    if patched_clip is not None:
        setattr(patched_clip, '_ez_cond_cache', _IMAGE_CLIP_COND_CACHE)
    print(f"[EZ-03-STYLE-SYNC] 🎨 Synkroniserade Bild-LoRA-profilen till style_target='{s_low}' (arch={prev_arch_tag}, age={yrs}, orc_tusks={bool(has_orc_tusks)}) -> {[f'{x[0]}:{x[1]}' for x in scaled_loras if x[0] != 'None']}")
    return (new_s1, new_s2, patched_clip)

