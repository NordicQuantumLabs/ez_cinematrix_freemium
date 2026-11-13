# -*- coding: utf-8 -*-
from ..EZ_ENGINES.engine_ez_05_cinematrix_video_lora_stack import _get_video_convrot_hadamard, _is_non_unet_or_image_only_for_video, get_dynamic_video_unets, get_dynamic_video_clips, get_dynamic_video_vaes, get_dynamic_video_loras, _parse_video_comfy_quant_tensor, _pre_dequantize_video_convrot_state_dict, _dequantize_video_rowwise_fallback, _ensure_video_quant_compat, _load_video_diffusion_model_convrot_safe, _load_video_vae_convrot_safe, _apply_modality_separated_av_lora, _attach_minimax_condition_proj_guard, load_video_engine_and_apply_av_loras, _H4_BASE, _VIDEO_HADAMARD_CACHE

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

class EzCinematrixVideoLoaderAdapter:
    """Adapter managing dual video UNETs, dual VAEs, and Audio/Video + Locked Turbo LoRA stacks."""

    @staticmethod
    def load_stack(video_unet_fl2va, video_unet_ref2va, video_clip_name, clip_type, video_vae_name, audio_vae_name, video_lora_1, lora_1_video_strength, lora_1_audio_strength, video_lora_2, lora_2_video_strength, lora_2_audio_strength, video_lora_3, lora_3_video_strength, lora_3_audio_strength, video_turbo_lora_LOCKED, turbo_video_strength, turbo_audio_strength, shift_video, shift_audio, enable_fp16_accumulation, lora_1_vis_strength=1.0, lora_1_clip_strength=0.0, lora_2_vis_strength=1.0, lora_2_clip_strength=0.0, lora_3_vis_strength=1.0, lora_3_clip_strength=0.0, video_lora_4='None', lora_4_video_strength=0.2, lora_4_vis_strength=1.0, lora_4_audio_strength=0.0, lora_4_clip_strength=0.0, enable_video_lora_1=True, enable_video_lora_2=True, enable_video_lora_3=True, enable_video_lora_4=True, enable_video_turbo_lora=True, turbo_vis_strength=1.0, cinematrix_bus=None, video_model_spec=None, video_lora_spec=None, **_extra_kwargs):
        bus = dict(cinematrix_bus) if isinstance(cinematrix_bus, dict) else {}
        vm_spec = video_model_spec if isinstance(video_model_spec, dict) else bus.get('civitai_video_model_spec') if isinstance(bus.get('civitai_video_model_spec'), dict) else None
        vl_spec = video_lora_spec if isinstance(video_lora_spec, dict) else bus.get('civitai_video_lora_spec') if isinstance(bus.get('civitai_video_lora_spec'), dict) else None
        if isinstance(vm_spec, dict):
            if str(vm_spec.get('modality', 'VIDEO')).upper() != 'VIDEO':
                raise ValueError('[EZ-MODALITY-LOCK] Bild-checkpoint (KREA2/Flux/SDXL) får EJ skickas till EZ [05] Video Loader!')
            spec_vunet = str(vm_spec.get('video_unet_fl2va', 'None') or 'None')
            has_spec_vunet = bool(spec_vunet and spec_vunet != 'None' and (not _is_non_unet_or_image_only_for_video(spec_vunet)))
            if has_spec_vunet:
                video_unet_fl2va = spec_vunet
                if vm_spec.get('clip_type'):
                    clip_type = str(vm_spec['clip_type'])
            if (not video_clip_name or video_clip_name == 'None') and vm_spec.get('video_clip_name') and (vm_spec['video_clip_name'] != 'None'):
                video_clip_name = str(vm_spec['video_clip_name'])
            if (not video_vae_name or video_vae_name == 'None') and vm_spec.get('video_vae_name') and (vm_spec['video_vae_name'] != 'None'):
                video_vae_name = str(vm_spec['video_vae_name'])
            if (not audio_vae_name or audio_vae_name == 'None') and vm_spec.get('audio_vae_name') and (vm_spec['audio_vae_name'] != 'None'):
                audio_vae_name = str(vm_spec['audio_vae_name'])
        raw_lora_entries = [
            (video_lora_1, lora_1_video_strength, lora_1_audio_strength, lora_1_vis_strength, lora_1_clip_strength),
            (video_lora_2, lora_2_video_strength, lora_2_audio_strength, lora_2_vis_strength, lora_2_clip_strength),
            (video_lora_3, lora_3_video_strength, lora_3_audio_strength, lora_3_vis_strength, lora_3_clip_strength),
            (video_lora_4, lora_4_video_strength, lora_4_audio_strength, lora_4_vis_strength, lora_4_clip_strength),
        ]
        vslot_enables = [bool(enable_video_lora_1), bool(enable_video_lora_2), bool(enable_video_lora_3), bool(enable_video_lora_4)]
        vturbo_enabled = bool(enable_video_turbo_lora)
        if isinstance(vl_spec, dict):
            if str(vl_spec.get('modality', 'VIDEO')).upper() != 'VIDEO':
                raise ValueError('[EZ-MODALITY-LOCK] Bild-LoRA (KREA2/Flux/SDXL) får EJ skickas till EZ [05] Video Loader!')
            spec_vloras = vl_spec.get('video_loras')
            if isinstance(spec_vloras, list) and any((item[0] != 'None' for item in spec_vloras if isinstance(item, (list, tuple)) and len(item) >= 2)):
                parsed_vloras = [(str(item[0]), float(item[1]), float(item[2]) if len(item) >= 3 else 0.0, float(item[3]) if len(item) >= 4 else 1.0, float(item[4]) if len(item) >= 5 else 0.0) for item in spec_vloras if isinstance(item, (list, tuple)) and len(item) >= 2]
                while len(parsed_vloras) < 4:
                    parsed_vloras.append(raw_lora_entries[len(parsed_vloras)])
                raw_lora_entries = parsed_vloras[:4]
            spec_venables = vl_spec.get('video_enables')
            if isinstance(spec_venables, list) and len(spec_venables) >= 4:
                vslot_enables = [bool(vslot_enables[idx] and bool(spec_venables[idx])) for idx in range(4)]
            if 'enable_video_turbo_lora' in vl_spec:
                vturbo_enabled = bool(vturbo_enabled and bool(vl_spec.get('enable_video_turbo_lora', True)))
            if vl_spec.get('video_turbo_lora') and vl_spec['video_turbo_lora'] != 'None':
                video_turbo_lora_LOCKED = str(vl_spec['video_turbo_lora'])
                turbo_video_strength = float(vl_spec.get('turbo_video_strength', turbo_video_strength))
                turbo_audio_strength = float(vl_spec.get('turbo_audio_strength', turbo_audio_strength))
                turbo_vis_strength = float(vl_spec.get('turbo_vis_strength', turbo_vis_strength))
        lora_entries = []
        for idx_v, ve in enumerate(raw_lora_entries):
            is_on = vslot_enables[idx_v] if idx_v < len(vslot_enables) else True
            if not is_on:
                if ve[0] and ve[0] != 'None':
                    print(f"[EZ-05-BYPASS] 🔇 Video LoRA {idx_v + 1} Bypassed (OFF): {ve[0]}")
                lora_entries.append(('None', 0.0, 0.0, 1.0, 0.0))
            else:
                lora_entries.append(ve)
        if not vturbo_enabled:
            if video_turbo_lora_LOCKED and video_turbo_lora_LOCKED != 'None':
                print(f"[EZ-05-BYPASS] 🔇 Video Turbo LoRA Bypassed (OFF): {video_turbo_lora_LOCKED}")
            video_turbo_lora_LOCKED = 'None'
            turbo_video_strength = 0.0
            turbo_audio_strength = 0.0
        rating_raw = str(bus.get('content_rating_mode', 'Uncensored') or 'Uncensored').strip().lower()
        is_nsfw = (not rating_raw.startswith('sfw')) and (str(bus.get('rating_tier', 'uncensored_action') or '').strip().lower() != 'sfw')
        style_low_05 = str(bus.get('style_target', 'realism') or 'realism').strip().lower()
        prompt_blob_05 = f"{bus.get('krea2_image_prompt', '')} {bus.get('h3_video_timeline_prompt', '')}".lower()
        has_orc_tusks_05 = bool(bus.get('has_orc_tusks', False)) or any((tok in prompt_blob_05 for tok in ('orc', 'tusk', 'tusks', 'half-orc')))
        nsfw_vlora_pat = ('nsfw', 'xxx', 'mysticxxx', 'nude', 'naked', 'sex', 'erotic', 'hentai', 'porn', 'cum', 'boob', 'tit', 'pussy', 'penis', 'blowjob', 'fuck', 'slut', 'lewd', 'moan')
        photo_vlora_pat = ('realism', 'realistic', 'photo', 'skin', 'pore', 'snofs', 'detailer', '4k', '8k', 'dslr')
        styled_vloras = []
        for vle in lora_entries:
            vln_low = str(vle[0] or '').lower()
            if (not is_nsfw) and any((tok in vln_low for tok in nsfw_vlora_pat)):
                print(f"[EZ-SFW-GUARD] 🛡️ SFW-läge aktivt i [05] -> Inaktiverar NSFW Video-LoRA: {vle[0]}")
                styled_vloras.append(('None', 0.0, 0.0, 0.0, 0.0))
                continue
            v_mult = 1.0
            if style_low_05 in ('anime', 'cartoonish') and any((tok in vln_low for tok in photo_vlora_pat)):
                v_mult = 0.0
            elif style_low_05 == 'original' and any((tok in vln_low for tok in photo_vlora_pat)):
                v_mult = 0.15
            elif style_low_05 in ('semi-real', 'unreal-engine-5', 'dark-fantasy-cgi') and any((tok in vln_low for tok in ('snofs', 'photoslider', 'realism_engine'))):
                v_mult = 0.35 if style_low_05 == 'semi-real' else (0.65 if style_low_05 == 'dark-fantasy-cgi' else 0.50)
            if has_orc_tusks_05 and ('snofs' in vln_low or 'lip' in vln_low or 'portrait' in vln_low):
                v_mult = min(v_mult, 0.55)
            if v_mult <= 1e-04:
                styled_vloras.append(('None', 0.0, 0.0, 0.0, 0.0))
            elif abs(v_mult - 1.0) > 1e-03:
                styled_vloras.append((vle[0], round(float(vle[1]) * v_mult, 4), float(vle[2]), float(vle[3]), round(float(vle[4]) * v_mult, 4)))
            else:
                styled_vloras.append(vle)
        lora_entries = styled_vloras
        tier_prof = dict(bus.get('hardware_tier_profile', {})) if isinstance(bus.get('hardware_tier_profile'), dict) else {}
        (m_fl2va, m_ref2va, v_clip, v_vae, a_vae) = load_video_engine_and_apply_av_loras(video_unet_fl2va=video_unet_fl2va, video_unet_ref2va=video_unet_ref2va, video_clip_name=video_clip_name, clip_type_str=clip_type, video_vae_name=video_vae_name, audio_vae_name=audio_vae_name, lora_entries=lora_entries, video_turbo_lora=video_turbo_lora_LOCKED, turbo_video_strength=turbo_video_strength, turbo_audio_strength=turbo_audio_strength, shift_video=shift_video, shift_audio=shift_audio, enable_fp16_accumulation=enable_fp16_accumulation, tier_profile=tier_prof, turbo_vis_strength=turbo_vis_strength)
        v_cls = str(getattr(getattr(v_vae, 'first_stage_model', v_vae), '__class__', type(v_vae)).__name__).lower()
        a_cls = str(getattr(getattr(a_vae, 'first_stage_model', a_vae), '__class__', type(a_vae)).__name__).lower() if a_vae is not None else ''
        if 'audio' in v_cls and a_vae is not None and ('audio' not in a_cls):
            (v_vae, a_vae) = (a_vae, v_vae)
        active_vloras_meta = [
            [str(ve[0]), float(ve[1]), float(ve[2]), float(ve[3]) if len(ve) >= 4 else 1.0, float(ve[4]) if len(ve) >= 5 else 0.0]
            for ve in lora_entries
            if isinstance(ve, (list, tuple)) and len(ve) >= 2 and str(ve[0]) not in ('', 'None')
        ]
        video_model_meta = {
            'video_model': str(video_unet_fl2va or ''),
            'active_video_unet': str(video_unet_fl2va or ''),
            'video_unet_fl2va': str(video_unet_fl2va or ''),
            'video_unet_ref2va': str(video_unet_ref2va or ''),
            'video_clip_name': str(video_clip_name or ''),
            'video_clip_type': str(clip_type or ''),
            'video_vae_name': str(video_vae_name or ''),
            'audio_vae_name': str(audio_vae_name or ''),
            'active_video_loras': active_vloras_meta,
            'video_turbo_lora': str(video_turbo_lora_LOCKED or ''),
            'turbo_video_strength': float(turbo_video_strength),
            'turbo_audio_strength': float(turbo_audio_strength),
            'shift_video': float(shift_video),
            'shift_audio': float(shift_audio),
        }
        EzCinematrixVideoLoaderAdapter._last_video_model_meta = dict(video_model_meta)
        for v_obj in (m_fl2va, m_ref2va, v_clip, v_vae, a_vae):
            if v_obj is not None:
                try:
                    setattr(v_obj, '_ez_video_model_meta', dict(video_model_meta))
                except Exception:
                    pass
        if isinstance(bus.get('krea2_saved_metadata'), dict):
            bus['krea2_saved_metadata'].update(video_model_meta)
        sidecar_p = str(bus.get('keyframe_sidecar_path', '') or '').strip()
        try:
            from ..EZ_ENGINES.engine_ez_04_cinematrix_krea2_sampler import _KREA2_KEYFRAME_VAULT
            if isinstance(_KREA2_KEYFRAME_VAULT.get('krea2_saved_metadata'), dict):
                _KREA2_KEYFRAME_VAULT['krea2_saved_metadata'].update(video_model_meta)
            if not sidecar_p:
                sidecar_p = str(_KREA2_KEYFRAME_VAULT.get('keyframe_sidecar_path', '') or '').strip()
        except Exception:
            pass
        if sidecar_p and Path(sidecar_p).exists():
            try:
                sc_data = json.loads(Path(sidecar_p).read_text(encoding='utf-8'))
                if isinstance(sc_data, dict):
                    sc_data.update(video_model_meta)
                    Path(sidecar_p).write_text(json.dumps(sc_data, indent=2, ensure_ascii=False), encoding='utf-8')
            except Exception:
                pass
        bus.update({**video_model_meta, 'video_vae_obj': v_vae, 'audio_vae_obj': a_vae})
        return (m_fl2va, m_ref2va, v_clip, v_vae, a_vae, bus)
