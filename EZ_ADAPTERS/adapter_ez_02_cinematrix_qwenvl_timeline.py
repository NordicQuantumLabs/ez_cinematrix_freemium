# -*- coding: utf-8 -*-
from ..EZ_ENGINES.engine_ez_02_cinematrix_qwenvl_timeline import _verify_cinematrix_license_active, _resolve_dropdown_custom_or_random, discover_dynamic_vlm_models, _tensor_to_pil_and_b64, _resolve_local_vlm_path, _run_local_transformers_vlm, _parse_subject_age_years, _build_age_authority_profile, _apply_age_override_to_text, _normalize_qwenvl_two_block_output, execute_qwenvl_story_compiler, _resolve_audio_soundtrack_mode, _resolve_content_rating_tier, _is_intentional_camera_movement_requested, _resolve_3axis_director_directives, _analyze_scene_cast_and_extras, MASTER_DURATION_PRESETS, STYLE_TARGET_PRESETS, CAMERA_ZOOM_PRESETS, LIGHTING_AMBIENT_PRESETS, SUBJECT_AGE_PRESETS, AGE_DIFFERENCE_PRESETS, CAMERA_MOVEMENT_PRESETS, AUDIO_SOUNDTRACK_MODE_PRESETS, CONTENT_RATING_MODE_PRESETS, SUBJECT_STANCE_POSTURE_PRESETS, BODY_CHOREOGRAPHY_PRESETS, CAMERA_TRAJECTORY_ARC_PRESETS, BACKGROUND_EXTRAS_CROWD_PRESETS

import base64
import gc
import hashlib
import hmac
import json
import os
import random
import re
import struct
import urllib.request
import zlib
from datetime import datetime
from pathlib import Path
import torch
import folder_paths
import comfy.model_management

class EzCinematrixQwenVLAdapter:
    """Adapter managing Qwen3-VL prompt splitting, dropdown/random/custom resolution, dynamic cast/extras, and VRAM reclamation."""

    @staticmethod
    def run_compiler(user_input: str, vlm_model_name: str, master_duration: str, style_target: str, subject_1_age: str, age_difference: str, camera_movement: str, lm_studio_endpoint: str, vram_cleanup_after: bool, camera_zoom: str='medium-shot', lighting_ambient: str='auto', custom_subject_1_age: str='', custom_age_difference: str='', custom_camera_movement: str='', custom_style_or_lighting: str='', custom_duration_seconds: float=0.0, compiler_seed: int=42, seed_mode: str='auto_from_bus_or_local', content_rating_mode: str='Uncensored Artistic / Action (Ingen Censur — Följer Prompten)', audio_soundtrack_mode: str='sfx_only_no_music (Endast Ljudeffekter / Ingen Musik)', subject_stance_posture: str='auto_from_prompt (Auto från Prompt / Bild)', body_choreography_preset: str='auto_from_prompt_or_audio (Auto från Prompt / Ljud)', camera_trajectory_arc: str='follow_02_camera_setting (Följ [02] Kamerainställning / Auto)', background_extras_crowd: str='auto_from_prompt (Auto från Prompt — Slagsmål / Älskog / Barhäng / Stadsvy / Solo)', reference_image=None, cinematrix_bus=None, custom_negative_prompt: str=''):
        bus = dict(cinematrix_bus) if isinstance(cinematrix_bus, dict) else {}
        master_seed = int(bus.get('canvas_seed', bus.get('master_seed', compiler_seed)))
        sync_all = bool(bus.get('sync_all_seeds', False)) or str(bus.get('seed_sync_mode', '')).lower().startswith('sync_all')
        mode_low = str(seed_mode or 'auto_from_bus_or_local').lower()
        if 'sync_with_master' in mode_low:
            eff_seed = master_seed
        elif 'use_local' in mode_low:
            eff_seed = int(compiler_seed)
        else:
            eff_seed = master_seed if sync_all or int(compiler_seed) == 0 else int(compiler_seed)
        omni_b = bus.get('omni_reference_bundle') if isinstance(bus.get('omni_reference_bundle'), dict) else {}
        is_t2i_bus = str(bus.get('generation_mode', 'I2I') or 'I2I').upper().startswith('T2I') and not bool(bus.get('has_source_image', False))
        has_vid_scene = bool(omni_b.get('has_video_scene_template', False))
        s1_char_crop = omni_b.get('slot1_character_ref_image')
        s5_scene_tmpl = omni_b.get('slot5_scene_template_image')
        has_direct_ref = isinstance(reference_image, torch.Tensor) and reference_image.numel() > 0 and float(reference_image.detach().abs().item() if reference_image.numel() == 1 else reference_image.detach().abs().max().item()) > 1e-04
        if has_direct_ref and not is_t2i_bus:
            eff_ref_img = reference_image
        elif has_vid_scene and isinstance(s1_char_crop, torch.Tensor):
            eff_ref_img = s1_char_crop
        elif omni_b.get('active') and omni_b.get('has_image_slots', True) and isinstance(omni_b.get('master_composite_image'), torch.Tensor) and not is_t2i_bus:
            eff_ref_img = omni_b.get('master_composite_image')
        else:
            eff_ref_img = bus.get('ingest_image')
        eff_ref2 = omni_b.get('slot2_person_image') if omni_b.get('active') and omni_b.get('slot2_person_image') is not None else bus.get('ref_image_2_person')
        eff_ref3 = omni_b.get('slot3_clothing_image') if omni_b.get('active') and omni_b.get('slot3_clothing_image') is not None else bus.get('ref_image_3_clothing')
        raw_ref4 = omni_b.get('slot4_background_image') if omni_b.get('active') and omni_b.get('slot4_background_image') is not None else bus.get('ref_image_4_background')
        eff_ref4 = raw_ref4 if raw_ref4 is not None else (s5_scene_tmpl if (has_vid_scene and isinstance(s5_scene_tmpl, torch.Tensor) and isinstance(s1_char_crop, torch.Tensor)) else None)
        has_any_ref = any(isinstance(x, torch.Tensor) and x.numel() > 0 and float(x.detach().abs().max().item()) > 1e-04 for x in (eff_ref_img, eff_ref2, eff_ref3, eff_ref4))
        suno_explicit_bypass = bool(bus.get('suno_bypassed') or bus.get('bypass_suno_music'))
        suno_cfg = dict(bus.get('suno_music_studio', {})) if (not suno_explicit_bypass and isinstance(bus.get('suno_music_studio'), dict)) else {}
        aud_sel_low = str(audio_soundtrack_mode or '').strip().lower()
        if not suno_cfg.get('active') and not suno_explicit_bypass and not aud_sel_low.startswith(('sfx_only', 'sfx_and_speech')):
            try:
                from ..EZ_ENGINES.engine_ez_12_cinematrix_suno_music_studio import resolve_or_preexecute_active_suno_packet
                resolved_suno = resolve_or_preexecute_active_suno_packet(bus)
                if isinstance(resolved_suno, dict) and resolved_suno.get('active'):
                    suno_cfg = dict(resolved_suno)
                    bus['suno_music_studio'] = suno_cfg
                    bus['suno_bypassed'] = False
                elif bus.get('suno_bypassed'):
                    suno_explicit_bypass = True
            except Exception:
                pass
        if not suno_cfg.get('active') or suno_explicit_bypass or aud_sel_low.startswith(('sfx_only', 'sfx_and_speech')):
            suno_cfg = {}
            bus['suno_bypassed'] = True
            bus.pop('suno_music_studio', None)
        elif aud_sel_low.startswith('instrumental_bgm'):
            suno_cfg['wants_lipsync'] = False
            bus['suno_bypassed'] = False
        else:
            bus['suno_bypassed'] = False
        eff_user_input = str(user_input or '').strip()
        if omni_b.get('active') and omni_b.get('prompt_directives'):
            raw_dir_txt = str(omni_b['prompt_directives']).strip()
            if raw_dir_txt:
                eff_user_input = f"{eff_user_input}\n\n{raw_dir_txt}".strip()
        eff_master_dur = master_duration
        eff_custom_dur = float(custom_duration_seconds or 0.0)
        eff_zoom = camera_zoom
        eff_cam_move = camera_movement
        eff_audio_arg = audio_soundtrack_mode
        if not suno_cfg.get('active') and (suno_explicit_bypass or bus.get('suno_bypassed')):
            if not aud_sel_low.startswith('sfx_and_speech'):
                eff_audio_arg = 'sfx_only_no_music (Endast Ljudeffekter / Ingen Musik)'
        elif suno_cfg.get('active'):
            if aud_sel_low.startswith(('auto', 'sfx_only', 'sfx_and_speech')):
                s_mod = str(suno_cfg.get('audio_modality', 'VOCAL_SONG')).upper()
                if s_mod == 'SPOKEN_WORD':
                    eff_audio_arg = 'sfx_and_speech_no_music'
                elif s_mod == 'INSTRUMENTAL_MUSIC' or not suno_cfg.get('wants_lipsync'):
                    eff_audio_arg = 'instrumental_bgm_no_vocals'
                else:
                    eff_audio_arg = 'bgm_with_vocals'
            if has_any_ref and not str(user_input or '').strip():
                eff_user_input = f"Preserve the exact character identity, face, outfit, environment, and visual composition from the provided reference image(s) while synchronizing motion to the music.\n\n{eff_user_input}".strip()
            if bool(suno_cfg.get('lock_video_duration')) and float(suno_cfg.get('duration_sec', 0.0) or 0.0) > 0.0:
                eff_custom_dur = float(suno_cfg['duration_sec'])
                eff_master_dur = 'custom'
            if suno_cfg.get('wants_lipsync') and not has_any_ref:
                if str(eff_zoom or '').lower() in ('extreme-wide-establishing', ''):
                    eff_zoom = 'medium-shot'
                if any(k in str(eff_cam_move or '').lower() for k in ('orbit', '360', 'low-angle', 'drone', 'whip-pan', 'dolly-in')):
                    eff_cam_move = 'steady locked-off cinema lens maintaining constant camera distance'
        slot2_dual = bool(omni_b.get('slot2_is_dual_subject', False))
        clean_custom_neg = str(custom_negative_prompt or '').strip()
        dir_3ax_sig = _resolve_3axis_director_directives(subject_stance_posture, body_choreography_preset, camera_trajectory_arc, user_scene_input=eff_user_input, background_extras_crowd=background_extras_crowd, slot2_is_dual_subject=slot2_dual, age_difference=age_difference)
        img_sig_parts = [
            'v29_clean_2d_anime_no_tusk_poison',
            str(eff_user_input).strip(),
            str(style_target).strip().lower(),
            str(eff_zoom).strip().lower(),
            str(lighting_ambient).strip().lower(),
            str(subject_1_age).strip().lower(),
            str(age_difference).strip().lower(),
            str(content_rating_mode).strip().lower(),
            ('i2i_initial_pose' if has_any_ref else str(subject_stance_posture).strip().lower()),
            str(background_extras_crowd).strip().lower(),
            str(custom_subject_1_age).strip(),
            str(custom_age_difference).strip(),
            str(custom_style_or_lighting).strip(),
            str(slot2_dual),
            clean_custom_neg,
        ]
        for ref_t in (eff_ref_img, eff_ref2, eff_ref3, eff_ref4):
            if isinstance(ref_t, torch.Tensor) and ref_t.numel() > 0:
                img_sig_parts.append(f'{tuple(ref_t.shape)}:{float(ref_t.float().mean().item()):.5f}')
            else:
                img_sig_parts.append('none')
        img_config_sig = hashlib.sha256('|'.join(img_sig_parts).encode('utf-8')).hexdigest()[:24]
        allow_cam_move_sig = _is_intentional_camera_movement_requested(camera_movement, custom_camera_movement, user_input) or bool(dir_3ax_sig['force_camera_move'])
        vid_sig_parts = [
            'v29_clean_2d_anime_no_tusk_poison',
            img_config_sig,
            str(eff_master_dur).strip().lower(),
            f'{float(eff_custom_dur):.2f}',
            str(eff_cam_move).strip().lower(),
            str(custom_camera_movement).strip(),
            str(subject_stance_posture).strip().lower(),
            str(body_choreography_preset).strip().lower(),
            str(camera_trajectory_arc).strip().lower(),
            str(background_extras_crowd).strip().lower(),
            str(bool(allow_cam_move_sig)),
            str(eff_audio_arg).strip().lower(),
            str(suno_cfg.get('audio_hash', '') if isinstance(suno_cfg, dict) else ''),
            clean_custom_neg,
        ]
        full_qwen_sig = hashlib.sha256('|'.join(vid_sig_parts).encode('utf-8')).hexdigest()[:24]
        qwen_cache_path = Path(folder_paths.get_temp_directory()) / 'ez_qwenvl_last_cache.json'
        if not getattr(EzCinematrixQwenVLAdapter, '_last_img_sig', None) and qwen_cache_path.exists():
            try:
                disk_qc = json.loads(qwen_cache_path.read_text(encoding='utf-8'))
                EzCinematrixQwenVLAdapter._last_img_sig = disk_qc.get('img_sig')
                EzCinematrixQwenVLAdapter._last_full_sig = disk_qc.get('full_sig')
                EzCinematrixQwenVLAdapter._last_b1 = disk_qc.get('b1', '')
                EzCinematrixQwenVLAdapter._last_b2 = disk_qc.get('b2', '')
                EzCinematrixQwenVLAdapter._last_neg = disk_qc.get('neg', '')
                EzCinematrixQwenVLAdapter._last_meta = disk_qc.get('meta', {})
            except Exception:
                pass
        use_locked_seed = ('use_local' in mode_low or 'sync_with' in mode_low)
        if (not use_locked_seed) and getattr(EzCinematrixQwenVLAdapter, '_last_full_sig', None) == full_qwen_sig and getattr(EzCinematrixQwenVLAdapter, '_last_b1', '') and getattr(EzCinematrixQwenVLAdapter, '_last_b2', ''):
            b1 = EzCinematrixQwenVLAdapter._last_b1
            b2 = EzCinematrixQwenVLAdapter._last_b2
            neg = clean_custom_neg if clean_custom_neg else EzCinematrixQwenVLAdapter._last_neg
            resolved_meta = dict(getattr(EzCinematrixQwenVLAdapter, '_last_meta', {}) or {})
            print('[EZ-QWENVL-CACHE] ⚡ Ingen ändring i prompt/kamera/ljud -> Återanvänder cachad Qwen3-VL tidslinje direkt!')
        else:
            (b1, b2, neg, resolved_meta) = execute_qwenvl_story_compiler(user_scene_input=eff_user_input, vlm_model_name=vlm_model_name, master_duration=eff_master_dur, style_target=style_target, subject_1_age=subject_1_age, age_difference=age_difference, camera_movement=eff_cam_move, lm_studio_endpoint=lm_studio_endpoint, vram_cleanup_after=vram_cleanup_after, camera_zoom=eff_zoom, lighting_ambient=lighting_ambient, custom_subject_1_age=custom_subject_1_age, custom_age_difference=custom_age_difference, custom_camera_movement=custom_camera_movement, custom_style_or_lighting=custom_style_or_lighting, custom_duration_seconds=eff_custom_dur, compiler_seed=eff_seed, reference_image=eff_ref_img, content_rating_mode=content_rating_mode, ref_image_2_person=eff_ref2, ref_image_3_clothing=eff_ref3, ref_image_4_background=eff_ref4, slot2_is_dual_subject=slot2_dual, audio_soundtrack_mode=eff_audio_arg, subject_stance_posture=subject_stance_posture, body_choreography_preset=body_choreography_preset, camera_trajectory_arc=camera_trajectory_arc, background_extras_crowd=background_extras_crowd, custom_negative_prompt=clean_custom_neg)
            if (not use_locked_seed) and getattr(EzCinematrixQwenVLAdapter, '_last_img_sig', None) == img_config_sig and getattr(EzCinematrixQwenVLAdapter, '_last_b1', ''):
                b1 = EzCinematrixQwenVLAdapter._last_b1
            else:
                EzCinematrixQwenVLAdapter._last_img_sig = img_config_sig
                EzCinematrixQwenVLAdapter._last_b1 = b1
            EzCinematrixQwenVLAdapter._last_full_sig = full_qwen_sig
            EzCinematrixQwenVLAdapter._last_b2 = b2
            EzCinematrixQwenVLAdapter._last_neg = neg
            EzCinematrixQwenVLAdapter._last_meta = dict(resolved_meta or {})
            try:
                qwen_cache_path.parent.mkdir(parents=True, exist_ok=True)
                qwen_cache_path.write_text(json.dumps({'img_sig': img_config_sig, 'full_sig': full_qwen_sig, 'b1': b1, 'b2': b2, 'neg': neg, 'meta': resolved_meta}, ensure_ascii=False), encoding='utf-8')
            except Exception:
                pass
        if suno_cfg.get('active') and not bool(suno_cfg.get('lock_video_duration')):
            try:
                from ..EZ_ENGINES.engine_ez_12_cinematrix_suno_music_studio import reslice_suno_packet_to_duration
                suno_cfg = reslice_suno_packet_to_duration(suno_cfg, float(resolved_meta.get('duration_seconds', 20.0) or 20.0))
                bus['suno_music_studio'] = suno_cfg
            except Exception:
                pass
        if suno_cfg.get('active') and suno_cfg.get('wants_lipsync') and resolved_meta.get('audio_soundtrack_mode') == 'bgm_with_vocals' and not clean_custom_neg:
            neg = re.sub(r'(?i)\b(?:singing|vocals|lyrics|choir|ballad|voiceover|spoken\s+dialogue),\s*', '', str(neg or ''))
            if 'closed mouth' not in neg.lower():
                neg = f'(closed mouth, static mouth, sealed lips, mute face, spoken narration, text-to-speech monologue, turned back, spinning around, jumping out of frame, walking away from camera, rear view:1.5), {neg}'
            if not has_any_ref and 'facing the camera' not in b1.lower():
                b1 = f'{b1} Framed as a front-facing medium close-up portrait facing the camera directly with clear mouth visibility and expressive parted lips singing toward the lens.'.strip()
            for idx in range(3):
                s_tag = f'[Shot {idx + 1}]'
                lip_cue = f'Maintaining the exact constant medium-wide camera distance, full posture scale, and anatomy of <Picture 1> with zero zoom-in or close-up cuts, <Subject 1> remains facing the camera lens while singing naturally in synchronization with the conditioned 32kHz vocal waveform.'
                if s_tag in b2 and 'singing naturally in synchronization with the conditioned 32kHz vocal waveform' not in b2:
                    b2 = b2.replace(s_tag + '\n', f'{s_tag}\n{lip_cue} ', 1)
            if '[Overall Soundscape]' in b2:
                b2 = re.sub(
                    r'(\[Overall Soundscape\]\s*\n)([^\n]+)',
                    lambda m: f"{m.group(1)}Clear, upfront studio lead vocals and expressive singing locked strictly to the conditioned 32kHz Suno audio waveform from 0.0s (zero spoken TTS narration).",
                    b2,
                    count=1,
                )
        if suno_cfg.get('active') and suno_cfg.get('lock_video_duration') and float(suno_cfg.get('duration_sec', 0.0) or 0.0) > 0.0:
            resolved_meta['duration_seconds'] = float(suno_cfg['duration_sec'])
            resolved_meta['master_duration'] = f"{int(round(float(suno_cfg['duration_sec'])))}-second"
        resolved_meta['allow_camera_movement'] = bool(resolved_meta.get('allow_camera_movement', allow_cam_move_sig))
        bus.update({'raw_user_scene_input': str(user_input or '').strip(), 'krea2_image_prompt': b1, 'krea2_image_config_sig': img_config_sig, 'h3_video_timeline_prompt': b2, 'adaptive_negative_prompt': neg, 'qwenvl_seed': int(eff_seed), **resolved_meta})
        globals()['_ACTIVE_QWENVL_SCENE_STATE'] = {
            'style_target': str(resolved_meta.get('style_target', style_target) or 'realism'),
            'subject_1_age': str(resolved_meta.get('subject_1_age', subject_1_age) or '25-year-old'),
            'subject_1_age_num': int(resolved_meta.get('subject_1_age_num', _parse_subject_age_years(subject_1_age)) or 25),
            'krea2_image_prompt': b1,
            'krea2_image_config_sig': img_config_sig,
            'adaptive_negative_prompt': neg,
            'content_rating_tier': str(resolved_meta.get('content_rating_tier', 'uncensored_action')),
        }
        return (b1, b2, neg, bus)

