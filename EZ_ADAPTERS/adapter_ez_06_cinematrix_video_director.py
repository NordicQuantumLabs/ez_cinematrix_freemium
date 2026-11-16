# -*- coding: utf-8 -*-
from ..EZ_ENGINES.engine_ez_06_cinematrix_video_director import MASTER_DURATION_PRESETS, MOTION_PHYSICS_MODES, SUBJECT_STANCE_POSTURE_PRESETS, BODY_CHOREOGRAPHY_PRESETS, CAMERA_TRAJECTORY_ARC_PRESETS, TEMPORAL_WINDOW_HORIZON_MODES, SCENE_CONTINUITY_MODES, KINEMATIC_MOTION_PROTOTYPES, resolve_effective_motion_physics_mode, resolve_effective_window_horizon_seconds, resolve_scene_continuity_mode, extract_editorial_scenecut_window_indices, _resolve_content_rating_tier, _scrub_unrequested_genital_hallucinations, _scrub_sfx_vocal_triggers, _apply_3axis_window_directives_to_acts, _build_director_preset_and_species_authority, project_video_kinematic_conditioning, _synthesize_start_mid_end_keyframes, _resolve_window_fl2va_start_mid_end, _extract_latent_motion_capture_deltas, _extract_chronological_shot_prompts, _build_reference_video_audio_packet, build_temporal_director_conditioning_and_latent


import re
import math
import gc
import random
import torch
import comfy.utils
import comfy.model_management

class EzCinematrixDirectorAdapter:
    """Adapter routing I2VA/T2VA/REF2VA modes, keyframe anchoring, kinematic motion physics, reference video audio lip-sync, and continuity metadata."""

    @staticmethod
    def compile_guide(video_model_fl2va, video_clip, video_vae, production_mode, timeline_prompt, negative_prompt, video_width, video_height, duration_seconds, frame_rate, overlap_frames, master_duration='20-second', motion_physics_mode='auto_from_style_and_audio (Auto från Stil & Ljud)', motion_transfer_strength=0.65, subject_stance_posture='auto_from_prompt (Auto från Prompt / Bild)', body_choreography_preset='auto_from_prompt_or_audio (Auto från Prompt / Ljud)', camera_trajectory_arc='follow_02_camera_setting (Följ [02] Kamerainställning / Auto)', video_model_ref2va=None, audio_vae=None, keyframe_image=None, ref_image_2_person=None, ref_image_3_clothing=None, ref_image_4_background=None, reference_motion_video=None, reference_video_audio=None, cinematrix_bus=None, temporal_window_horizon=TEMPORAL_WINDOW_HORIZON_MODES[0], scene_continuity_mode=SCENE_CONTINUITY_MODES[0]):
        bus = dict(cinematrix_bus) if isinstance(cinematrix_bus, dict) else {}
        tier_prof = dict(bus.get('hardware_tier_profile', {})) if isinstance(bus.get('hardware_tier_profile'), dict) else {}
        if isinstance(cinematrix_bus, dict) and 'duration_seconds' in bus and float(bus['duration_seconds']) > 0.0:
            eff_duration = float(bus['duration_seconds'])
            resolved_master_dur = str(bus.get('master_duration', f'{int(round(eff_duration))}-second'))
        else:
            md_str = str(master_duration or '20-second').strip().lower()
            if md_str == 'custom' and float(duration_seconds) > 0.0:
                eff_duration = float(duration_seconds)
                resolved_master_dur = f'{int(round(eff_duration))}-second'
            elif md_str == 'random':
                picked = random.choice(MASTER_DURATION_PRESETS)
                m_r = re.search('(\\d+(?:\\.\\d+)?)', picked)
                eff_duration = float(m_r.group(1)) if m_r else 20.0
                resolved_master_dur = picked
            else:
                m_d = re.search('(\\d+(?:\\.\\d+)?)', md_str)
                if m_d and (abs(float(duration_seconds) - 20.0) < 0.0001 or abs(float(duration_seconds) - float(m_d.group(1))) < 0.0001):
                    eff_duration = float(m_d.group(1))
                    resolved_master_dur = str(master_duration)
                else:
                    eff_duration = float(duration_seconds) if float(duration_seconds) > 0.0 else 20.0
                    resolved_master_dur = f'{int(round(eff_duration))}-second'
        has_02_master = isinstance(cinematrix_bus, dict) and not bool(bus.get('qwenvl_02_bypassed', False))
        bus_stance = str(bus.get('subject_stance_posture', '') or '').strip()
        bus_choreo = str(bus.get('body_choreography_preset', '') or '').strip()
        bus_arc = str(bus.get('camera_trajectory_arc', '') or '').strip()
        bus_cont_mode = str(bus.get('scene_continuity_mode', '') or '').strip()
        bus_resolved_cont = str(bus.get('resolved_scene_continuity_mode', '') or '').strip()
        eff_stance = str(subject_stance_posture or '').strip()
        if has_02_master and bus_stance and not bus_stance.lower().startswith('auto_from_prompt'):
            eff_stance = bus_stance
        elif (not eff_stance or eff_stance.lower().startswith('auto_from_prompt')) and bus_stance:
            eff_stance = bus_stance
        elif eff_stance.lower() == 'random':
            eff_stance = random.choice(SUBJECT_STANCE_POSTURE_PRESETS[1:])
        eff_choreo = str(body_choreography_preset or '').strip()
        if has_02_master and bus_choreo and not bus_choreo.lower().startswith('auto_from_prompt'):
            eff_choreo = bus_choreo
        elif (not eff_choreo or eff_choreo.lower().startswith('auto_from_prompt')) and bus_choreo:
            eff_choreo = bus_choreo
        elif eff_choreo.lower() == 'random':
            eff_choreo = random.choice(BODY_CHOREOGRAPHY_PRESETS[1:])
        eff_arc = str(camera_trajectory_arc or '').strip()
        if has_02_master and bus_arc and not bus_arc.lower().startswith('follow_02'):
            eff_arc = bus_arc
        elif (not eff_arc or eff_arc.lower().startswith('follow_02')) and bus_arc:
            eff_arc = bus_arc
        elif eff_arc.lower() == 'random':
            eff_arc = random.choice(CAMERA_TRAJECTORY_ARC_PRESETS[1:])
        eff_cont_mode = str(scene_continuity_mode or SCENE_CONTINUITY_MODES[0]).strip()
        if (not eff_cont_mode or eff_cont_mode.lower().startswith('auto_from_prompt')) and bus_cont_mode and not bus_cont_mode.lower().startswith('auto_from_prompt'):
            eff_cont_mode = bus_cont_mode
        elif eff_cont_mode.lower().startswith('auto_from_prompt') and has_02_master and bus_resolved_cont in ('locked_stage_environment', 'continuous_one_shot', 'hollywood_multi_scene_cuts'):
            eff_cont_mode = bus_resolved_cont
        elif eff_cont_mode.lower() == 'random':
            eff_cont_mode = random.choice(SCENE_CONTINUITY_MODES[1:])
        bus['subject_stance_posture'] = eff_stance
        bus['body_choreography_preset'] = eff_choreo
        bus['camera_trajectory_arc'] = eff_arc
        bus['scene_continuity_mode'] = eff_cont_mode
        eff_pos = str(timeline_prompt or '').strip() or str(bus.get('h3_video_timeline_prompt', ''))
        has_multi_cast_06 = int(bus.get('main_cast_count', 1) or 1) >= 2 or bool(bus.get('has_background_extras', False)) or bool(re.search(r'(?i)(?:<\s*(?:main[_\s-]*)?subject\s*2\s*>|\bcharacter\s*2\b|\btwo[-\s]?shot\b|\binterview(?:ing)?\b)', eff_pos))
        is_crowd_scene = has_multi_cast_06 or bool(bus.get('is_multi_subject_crowd', False)) or any(eff_stance.lower().startswith(k) for k in ('standing_social', 'epic_battlefield', 'nsfw_threesome', 'nsfw_orgy'))
        is_outro_follow = eff_arc.lower().startswith('outro_track_to_follow')
        user_scene_in_06 = str(bus.get('user_scene_input') or eff_pos).strip()
        resolved_cont_06 = resolve_scene_continuity_mode(eff_cont_mode, user_scene_in_06, eff_stance, eff_choreo, eff_arc)
        force_3ax_cam = (resolved_cont_06 != 'locked_stage_environment') or (bool(eff_arc.strip()) and not eff_arc.lower().startswith(('follow_02', 'auto'))) or eff_stance.lower().startswith('story_vehicle') or eff_choreo.lower().startswith(('running_action', 'catwalk_runway', 'story_multi_act'))
        rating_tier = str(bus.get('content_rating_tier', '') or '').strip().lower()
        if not rating_tier:
            rating_tier = _resolve_content_rating_tier(str(bus.get('content_rating_mode', 'Uncensored')), eff_pos, eff_stance, eff_choreo)
        elif rating_tier != 'sfw' and (eff_stance.lower().startswith('nsfw_') or eff_choreo.lower().startswith('nsfw_')):
            rating_tier = 'nsfw_explicit'
        is_nsfw = (rating_tier != 'sfw')
        style_low = str(bus.get('style_target', '') or '').strip().lower()
        default_core_neg = '(text, logo, watermark, signature, censored, mosaic censorship:1.5), 色调艳丽, 过曝, 静态, 细节模糊不清, 字幕, 风格, 作品, 画作, 画面, 静止, 整体发灰, 最差质量, 低质量, JPEG压缩残留, 丑陋的, 残缺的, 多余的手指, 画得不好的手部, 画得不好的脸部, 畸形的, 毁容的, 形态畸形的肢体, 手指融合, 静止不动的画面, 杂乱的背景, 三条腿, 背景人很多, 倒着走,'
        if rating_tier == 'sfw':
            default_core_neg = f'(nsfw, nude, naked, nipples, breasts, cleavage, lingerie, bikini, cum, white cum, milky liquid:1.6), {default_core_neg}'
            eff_pos = _scrub_unrequested_genital_hallucinations(eff_pos, '')
        eff_neg = str(negative_prompt or '').strip() or str(bus.get('adaptive_negative_prompt', '') or default_core_neg).strip()
        bus['adaptive_negative_prompt'] = eff_neg
        allow_cam_move = bool(bus.get('allow_camera_movement', False)) or bool(force_3ax_cam)
        if not allow_cam_move and 'allow_camera_movement' not in bus:
            try:
                from ..EZ_ENGINES.engine_ez_02_cinematrix_qwenvl_timeline import _is_intentional_camera_movement_requested
                allow_cam_move = _is_intentional_camera_movement_requested(str(bus.get('camera_movement', '')), '', eff_pos)
            except Exception:
                allow_cam_move = False
        omni_b = bus.get('omni_reference_bundle') if isinstance(bus.get('omni_reference_bundle'), dict) else {}
        suno_cfg = dict(bus.get('suno_music_studio', {})) if (not bus.get('suno_bypassed') and isinstance(bus.get('suno_music_studio'), dict)) else {}
        has_direct_ref_aud = isinstance(reference_video_audio, dict) and isinstance(reference_video_audio.get('waveform'), torch.Tensor) and float(reference_video_audio['waveform'].detach().abs().max().item()) > 1e-04
        eff_ref_aud = (
            reference_video_audio
            if has_direct_ref_aud
            else (
                (
                    bus.get('reference_video_audio')
                    if isinstance(bus.get('reference_video_audio'), dict) and isinstance(bus['reference_video_audio'].get('waveform'), torch.Tensor)
                    else omni_b.get('slot5_reference_audio')
                )
                if not suno_cfg.get('active')
                else None
            )
        )
        bus_aud_mode = str(bus.get('audio_soundtrack_mode', '') or '').strip().lower()
        wants_vocal_mocap = str(motion_physics_mode or '').strip().lower().startswith('expressive_vocal') or (eff_ref_aud is not None)
        if not suno_cfg.get('active') and eff_ref_aud is not None:
            ref_aud_pkt = _build_reference_video_audio_packet(eff_ref_aud, eff_duration, float(frame_rate or 24.0))
            if isinstance(ref_aud_pkt, dict) and ref_aud_pkt.get('active'):
                suno_cfg = ref_aud_pkt
                bus['suno_music_studio'] = suno_cfg
                bus['suno_bypassed'] = False
                bus['reference_video_audio'] = eff_ref_aud
        if not suno_cfg.get('active'):
            try:
                from ..EZ_ENGINES.engine_ez_12_cinematrix_suno_music_studio import resolve_or_preexecute_active_suno_packet
                resolved_suno = resolve_or_preexecute_active_suno_packet(bus, eff_duration)
                if isinstance(resolved_suno, dict) and resolved_suno.get('active'):
                    suno_cfg = dict(resolved_suno)
                    bus['suno_music_studio'] = suno_cfg
                    bus['suno_bypassed'] = False
            except Exception:
                pass
        if suno_cfg.get('active') and bus_aud_mode in ('sfx_only', 'sfx_and_speech', ''):
            bus_aud_mode = 'bgm_with_vocals' if (suno_cfg.get('wants_lipsync') or wants_vocal_mocap) else 'instrumental_bgm'
            bus['audio_soundtrack_mode'] = bus_aud_mode
        elif wants_vocal_mocap and bus_aud_mode in ('sfx_only', ''):
            bus_aud_mode = 'bgm_with_vocals'
            bus['audio_soundtrack_mode'] = bus_aud_mode
        if bus_aud_mode in ('sfx_only', 'sfx_and_speech') and not suno_cfg.get('active') and not wants_vocal_mocap:
            suno_cfg = {}
            eff_pos = re.sub(r'(?is)\[Non-Diegetic Music\][\s\S]*$', '', eff_pos).strip()
            if bus_aud_mode == 'sfx_only':
                eff_pos = _scrub_sfx_vocal_triggers(eff_pos, user_scene_in_06)
        elif bus_aud_mode == 'instrumental_bgm' and not wants_vocal_mocap:
            if suno_cfg.get('active'):
                suno_cfg['wants_lipsync'] = False
            eff_pos = _scrub_sfx_vocal_triggers(eff_pos, user_scene_in_06)
        if suno_cfg.get('active'):
            if wants_vocal_mocap:
                suno_cfg['wants_lipsync'] = True
            if bool(suno_cfg.get('lock_video_duration')) and float(suno_cfg.get('duration_sec', 0.0) or 0.0) > 0.0:
                eff_duration = float(suno_cfg['duration_sec'])
                resolved_master_dur = f'{int(round(eff_duration))}-second'
            elif not suno_cfg.get('is_reference_video_audio'):
                try:
                    from ..EZ_ENGINES.engine_ez_12_cinematrix_suno_music_studio import reslice_suno_packet_to_duration
                    suno_cfg = reslice_suno_packet_to_duration(suno_cfg, eff_duration)
                    bus['suno_music_studio'] = suno_cfg
                except Exception:
                    pass
            if suno_cfg.get('prompt_injection') and 'SUNO' not in eff_pos and bus_aud_mode not in ('sfx_only', 'sfx_and_speech', 'instrumental_bgm'):
                eff_pos = f"{eff_pos}\n\n{suno_cfg['prompt_injection']}".strip()
        def _valid_ref_img(t_cand):
            return t_cand if isinstance(t_cand, torch.Tensor) and t_cand.ndim == 4 and float(t_cand.detach().abs().max().item()) > 1e-04 else None
        prod_upper = str(production_mode or 'I2VA').strip().upper()
        use_bus_extra_refs = prod_upper.startswith('REF2VA')
        eff_kf = _valid_ref_img(keyframe_image) if _valid_ref_img(keyframe_image) is not None else (_valid_ref_img(bus.get('keyframe_image')) if _valid_ref_img(bus.get('keyframe_image')) is not None else _valid_ref_img(bus.get('ingest_image')))
        eff_ref2 = _valid_ref_img(ref_image_2_person) if _valid_ref_img(ref_image_2_person) is not None else (_valid_ref_img(bus.get('ref_image_2_person')) if (use_bus_extra_refs or eff_kf is None) else None)
        eff_ref3 = _valid_ref_img(ref_image_3_clothing) if _valid_ref_img(ref_image_3_clothing) is not None else (_valid_ref_img(bus.get('ref_image_3_clothing')) if (use_bus_extra_refs or eff_kf is None) else None)
        eff_ref4 = _valid_ref_img(ref_image_4_background) if _valid_ref_img(ref_image_4_background) is not None else (_valid_ref_img(bus.get('ref_image_4_background')) if (use_bus_extra_refs or eff_kf is None) else None)
        raw_w = float(video_width or 1152)
        raw_h = float(video_height or 640)
        if eff_kf is not None and int(eff_kf.shape[1]) >= 64 and int(eff_kf.shape[2]) >= 64:
            kf_ar = float(eff_kf.shape[2]) / float(max(1, int(eff_kf.shape[1])))
            req_ar = raw_w / max(1.0, raw_h)
            is_default_res = (int(round(raw_w)) in (768, 832, 1152) and int(round(raw_h)) in (512, 576, 640))
            if is_default_res or abs(req_ar - kf_ar) > 0.08:
                base_area = 1152.0 * 640.0 if (int(round(raw_w)) == 768 and int(round(raw_h)) == 512) else max(768.0 * 512.0, raw_w * raw_h)
                target_area = min(1152.0 * 640.0, max(768.0 * 512.0, base_area))
                raw_h = math.sqrt(target_area / max(0.25, min(4.0, kf_ar)))
                raw_w = raw_h * kf_ar
        if raw_w * raw_h > 1216 * 672:
            scale_cap = math.sqrt((1152.0 * 640.0) / max(1.0, raw_w * raw_h))
            raw_w = raw_w * scale_cap
            raw_h = raw_h * scale_cap
        aligned_w = max(64, int(round(raw_w / 32.0) * 32))
        aligned_h = max(64, int(round(raw_h / 32.0) * 32))
        v_cls = str(getattr(getattr(video_vae, 'first_stage_model', video_vae), '__class__', type(video_vae)).__name__).lower()
        a_cls = str(getattr(getattr(audio_vae, 'first_stage_model', audio_vae), '__class__', type(audio_vae)).__name__).lower() if audio_vae is not None else ''
        if 'audio' in v_cls:
            if audio_vae is not None and 'audio' not in a_cls:
                (video_vae, audio_vae) = (audio_vae, video_vae)
            elif bus.get('video_vae_obj') is not None:
                if audio_vae is None:
                    audio_vae = video_vae
                video_vae = bus['video_vae_obj']
        if audio_vae is None and bus.get('audio_vae_obj') is not None:
            audio_vae = bus['audio_vae_obj']
        has_direct_ref_vid = isinstance(reference_motion_video, torch.Tensor) and reference_motion_video.ndim == 4 and int(reference_motion_video.shape[0]) >= 2
        allow_bus_ref_vid = (prod_upper == 'FL2VA') or bool(bus.get('has_reference_motion_video', False)) or isinstance(omni_b.get('slot5_reference_video'), torch.Tensor)
        eff_ref_vid = (
            reference_motion_video
            if has_direct_ref_vid
            else (
                (
                    bus.get('reference_motion_video')
                    if isinstance(bus.get('reference_motion_video'), torch.Tensor) and int(bus['reference_motion_video'].shape[0]) >= 2
                    else omni_b.get('slot5_reference_video')
                )
                if allow_bus_ref_vid
                else None
            )
        )
        s5_vpath = str(bus.get('slot5_video_path') or omni_b.get('slot5_video_path') or '').strip()
        s5_follow_master = bool(bus.get('slot5_follow_master_duration', omni_b.get('slot5_follow_master_duration', True)))
        s5_loaded_dur = float(bus.get('slot5_loaded_duration_sec', omni_b.get('slot5_duration_seconds', 0.0)) or 0.0)
        if not has_direct_ref_vid and allow_bus_ref_vid and s5_follow_master and s5_vpath and abs(s5_loaded_dur - float(eff_duration)) > 0.5:
            try:
                from ..EZ_ENGINES.engine_ez_13_cinematrix_omni_reference_loader import load_video_frames_from_slot
                s5_off = float(bus.get('slot5_start_offset_sec', omni_b.get('slot5_start_offset_sec', 0.0)) or 0.0)
                re_v, _ = load_video_frames_from_slot(s5_vpath, max_frames=0, target_w=min(int(aligned_w), 768), target_h=min(int(aligned_h), 512), start_offset_sec=s5_off, target_duration_sec=float(eff_duration))
                if isinstance(re_v, torch.Tensor) and re_v.ndim == 4 and int(re_v.shape[0]) >= 2:
                    eff_ref_vid = re_v
                    bus['reference_motion_video'] = re_v
                    bus['slot5_loaded_duration_sec'] = float(eff_duration)
            except Exception:
                pass
        eff_motion_str = float(motion_transfer_strength)
        if math.isclose(eff_motion_str, 0.65) and 'slot5_motion_strength' in bus:
            eff_motion_str = float(bus['slot5_motion_strength'])
        eff_horizon_mode = str(temporal_window_horizon or TEMPORAL_WINDOW_HORIZON_MODES[0]).strip()
        (active_m, pos_c, neg_c, lat_d, fps_out) = build_temporal_director_conditioning_and_latent(video_model_fl2va=video_model_fl2va, video_model_ref2va=video_model_ref2va, video_clip=video_clip, video_vae=video_vae, production_mode=production_mode, timeline_prompt=eff_pos, negative_prompt=eff_neg, video_width=aligned_w, video_height=aligned_h, duration_seconds=eff_duration, frame_rate=frame_rate, overlap_frames=overlap_frames, keyframe_image=eff_kf, audio_vae=audio_vae, tier_profile=tier_prof, ref_image_2_person=eff_ref2, ref_image_3_clothing=eff_ref3, ref_image_4_background=eff_ref4, motion_physics_mode=motion_physics_mode, motion_transfer_strength=eff_motion_str, reference_motion_video=eff_ref_vid, reference_video_audio=eff_ref_aud, style_target=style_low, is_nsfw=is_nsfw, allow_camera_movement=allow_cam_move, subject_stance_posture=eff_stance, body_choreography_preset=eff_choreo, camera_trajectory_arc=eff_arc, rating_tier=rating_tier, temporal_window_horizon=eff_horizon_mode, user_scene_input=user_scene_in_06, scene_continuity_mode=eff_cont_mode)
        eff_neg = str((lat_d.get('ez_continuation_ctx') or {}).get('negative_prompt') or eff_neg).strip()
        bus['adaptive_negative_prompt'] = eff_neg
        bus['raw_motion_physics_mode'] = str(motion_physics_mode or '')
        bus['is_non_human_subject'] = bool(lat_d.get('is_non_human_subject', bus.get('is_non_human_subject', False)))
        if hasattr(comfy.model_management, 'unload_all_models'):
            comfy.model_management.unload_all_models()
        if hasattr(comfy.model_management, 'soft_empty_cache'):
            comfy.model_management.soft_empty_cache()
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        sat_str_06 = float(bus.get('color_saturation_strength', 0.80) or 0.80)
        vm_meta_06 = {}
        for m_cand in (video_model_fl2va, video_model_ref2va, video_vae, audio_vae, active_m):
            cand_d = getattr(m_cand, '_ez_video_model_meta', None) if m_cand is not None else None
            if isinstance(cand_d, dict) and cand_d:
                vm_meta_06 = dict(cand_d)
                break
        if not vm_meta_06:
            try:
                from .adapter_ez_05_cinematrix_video_lora_stack import EzCinematrixVideoLoaderAdapter
                if isinstance(getattr(EzCinematrixVideoLoaderAdapter, '_last_video_model_meta', None), dict):
                    vm_meta_06 = dict(EzCinematrixVideoLoaderAdapter._last_video_model_meta)
            except Exception:
                pass
        for vk in ('video_model', 'active_video_unet', 'video_unet_fl2va', 'video_unet_ref2va', 'video_clip_name', 'video_clip_type', 'video_vae_name', 'audio_vae_name', 'active_video_loras', 'video_turbo_lora', 'turbo_video_strength', 'turbo_audio_strength', 'shift_video', 'shift_audio'):
            if bus.get(vk) and not vm_meta_06.get(vk):
                vm_meta_06[vk] = bus[vk]
        is_ref2va_mode = prod_upper.startswith('REF2VA') and (video_model_ref2va is not None)
        chosen_v_unet = str(vm_meta_06.get('video_unet_ref2va') if is_ref2va_mode and str(vm_meta_06.get('video_unet_ref2va', 'None')) not in ('', 'None') else (vm_meta_06.get('video_unet_fl2va') or vm_meta_06.get('active_video_unet') or ''))
        if chosen_v_unet:
            vm_meta_06['active_video_unet'] = chosen_v_unet
            vm_meta_06['video_model'] = chosen_v_unet
        if active_m is not None and vm_meta_06:
            try:
                setattr(active_m, '_ez_video_model_meta', dict(vm_meta_06))
            except Exception:
                pass
        bus.update({**vm_meta_06, 'production_mode': production_mode, 'video_width': int(aligned_w), 'video_height': int(aligned_h), 'master_duration': resolved_master_dur, 'duration_seconds': eff_duration, 'frame_rate': fps_out, 'overlap_frames': int(overlap_frames), 'video_vae_obj': video_vae, 'audio_vae_obj': audio_vae, 'audio_soundtrack_mode': bus_aud_mode or 'sfx_only', 'suno_bypassed': not bool(suno_cfg.get('active')), 'motion_physics_mode': lat_d.get('motion_physics_mode', 'natural_organic'), 'motion_transfer_strength': eff_motion_str, 'allow_camera_movement': bool(lat_d.get('allow_camera_movement', allow_cam_move)), 'subject_stance_posture': eff_stance, 'body_choreography_preset': eff_choreo, 'camera_trajectory_arc': eff_arc, 'scene_continuity_mode': eff_cont_mode, 'resolved_scene_continuity_mode': str(lat_d.get('resolved_scene_continuity_mode', resolved_cont_06)), 'editorial_scenecut_indices': list(lat_d.get('editorial_scenecut_indices', [])), 'temporal_window_horizon': eff_horizon_mode, 'window_horizon_seconds': float(lat_d.get('window_horizon_seconds', 5.0)), 'pro_focus_seam_active': bool(lat_d.get('pro_focus_seam_active', True)), 'is_multi_subject_crowd': bool(is_crowd_scene), 'color_saturation_strength': sat_str_06})
        lat_d['video_vae_obj'] = video_vae
        lat_d['audio_vae_obj'] = audio_vae
        lat_d['audio_soundtrack_mode'] = bus_aud_mode or 'sfx_only'
        lat_d['suno_bypassed'] = not bool(suno_cfg.get('active'))
        lat_d['allow_camera_movement'] = bool(lat_d.get('allow_camera_movement', allow_cam_move))
        lat_d['subject_stance_posture'] = eff_stance
        lat_d['body_choreography_preset'] = eff_choreo
        lat_d['camera_trajectory_arc'] = eff_arc
        lat_d['scene_continuity_mode'] = eff_cont_mode
        lat_d['resolved_scene_continuity_mode'] = str(lat_d.get('resolved_scene_continuity_mode', resolved_cont_06))
        lat_d['temporal_window_horizon'] = eff_horizon_mode
        lat_d['is_multi_subject_crowd'] = bool(is_crowd_scene)
        lat_d['color_saturation_strength'] = sat_str_06
        if suno_cfg.get('active'):
            lat_d['suno_music_studio'] = suno_cfg
            if isinstance(lat_d.get('ez_continuation_ctx'), dict):
                lat_d['ez_continuation_ctx']['suno_music_studio'] = suno_cfg
            if eff_ref_aud is not None:
                lat_d['suno_direct_audio'] = eff_ref_aud
                bus['suno_direct_audio'] = eff_ref_aud
        else:
            lat_d.pop('suno_music_studio', None)
        lat_d['seed_bus'] = {'canvas_seed': bus.get('canvas_seed', bus.get('master_seed', 0)), 'qwenvl_seed': bus.get('qwenvl_seed', 0), 'image_sampler_seed': bus.get('image_sampler_seed', 0), 'seed_sync_mode': bus.get('seed_sync_mode', ''), 'sync_all_seeds': bool(bus.get('sync_all_seeds', False))}
        kf_saved = dict(bus.get('krea2_saved_metadata', {})) if isinstance(bus.get('krea2_saved_metadata'), dict) else {}
        if kf_saved and vm_meta_06:
            kf_saved.update(vm_meta_06)
            bus['krea2_saved_metadata'] = kf_saved
        lat_d['ez_vault_metadata'] = {
            **vm_meta_06,
            'active_image_unet': str(bus.get('active_image_unet') or kf_saved.get('active_image_unet') or ''),
            'active_style_loras': bus.get('active_style_loras') if bus.get('active_style_loras') else kf_saved.get('active_style_loras', []),
            'krea2_image_prompt': str(bus.get('krea2_image_prompt', '') or ''),
            'h3_video_timeline_prompt': eff_pos,
            'adaptive_negative_prompt': eff_neg,
            'style_target': style_low,
            'subject_1_age': str(bus.get('subject_1_age', '') or ''),
            'camera_zoom': str(bus.get('camera_zoom', '') or ''),
            'lighting_ambient': str(bus.get('lighting_ambient', '') or ''),
            'camera_movement': str(bus.get('camera_movement', '') or ''),
            'master_duration': str(bus.get('master_duration', '') or ''),
            'production_mode': str(production_mode),
            'motion_physics_mode': str(motion_physics_mode),
            'keyframe_filename': str(bus.get('keyframe_filename', '') or ''),
            'krea2_saved_metadata': kf_saved,
        }
        return (active_m, pos_c, neg_c, lat_d, fps_out, bus)
