# -*- coding: utf-8 -*-
from ..EZ_ENGINES.engine_ez_07_cinematrix_joint_av_sampler import _is_nested_av_latent, _unpack_av_tensors, _repack_av_tensors, _offload_completed_chunk_to_cpu, _resolve_audio_time_dim, _slice_tensor_along_dim, _slice_av_temporal_window, _compute_audio_overlap_steps, _inject_overlap_into_av_window, _build_av_overlap_noise_mask, _stabilize_3d_video_latent_outliers, _blend_and_cat_av_windows, _project_5d_latent_to_rgb_u8, _emit_minipyav_live_video_preview, _inject_handoff_into_5d_cond_tensor, _slice_conditioning_for_window, _ez_head_chunked_sdpa, _install_sage_attention_oom_guard, _decode_handoff_frame_from_accum, _rebuild_window_h3_conditioning, _attach_temporal_continuity_lock, _sample_single_temporal_window, resolve_preset_coupled_temporal_rigidity, execute_temporal_chunked_sampling

import gc
import torch
import comfy.model_management
import comfy.sample
import comfy.samplers
import comfy.utils
import latent_preview

class EzCinematrixTemporalSamplerAdapter:
    """Adapter managing temporal sampling, continuity stitching, and optional 2x latent upscale."""

    @staticmethod
    def run_sampler(active_video_model, positive, negative, latent_video_audio, seed, steps, cfg, sampler_name, scheduler, denoise, enable_latent_2x_upscale, seed_mode='auto_from_bus_or_local', previous_segment_latent=None, anatomy_dock=None, cinematrix_bus=None):
        bus = dict(cinematrix_bus) if isinstance(cinematrix_bus, dict) else {}
        if isinstance(anatomy_dock, dict):
            bus['anatomy_dock'] = dict(anatomy_dock)
        active_dock = dict(anatomy_dock) if isinstance(anatomy_dock, dict) else dict(bus.get('anatomy_dock', {})) if isinstance(bus.get('anatomy_dock'), dict) else {}
        lat_seed_bus = dict(latent_video_audio.get('seed_bus', {})) if isinstance(latent_video_audio, dict) and isinstance(latent_video_audio.get('seed_bus'), dict) else {}
        merged_seed_bus = {**lat_seed_bus, **bus}
        master_seed = int(merged_seed_bus.get('canvas_seed', merged_seed_bus.get('master_seed', seed)) or seed)
        image_seed = int(merged_seed_bus.get('image_sampler_seed', master_seed) or master_seed)
        qwen_seed = int(merged_seed_bus.get('qwenvl_seed', master_seed) or master_seed)
        sync_all = bool(merged_seed_bus.get('sync_all_seeds', False)) or str(merged_seed_bus.get('seed_sync_mode', '')).lower().startswith('sync_all')
        mode_low = str(seed_mode or 'auto_from_bus_or_local').lower()
        if 'sync_with_master' in mode_low:
            eff_seed = master_seed
        elif 'sync_with_image' in mode_low:
            eff_seed = image_seed
        elif 'sync_with_qwenvl' in mode_low:
            eff_seed = qwen_seed
        elif 'use_local' in mode_low:
            eff_seed = int(seed)
        else:
            eff_seed = master_seed if sync_all or int(seed) == 0 else int(seed)
        tier_prof = dict(bus.get('hardware_tier_profile', {})) if isinstance(bus.get('hardware_tier_profile'), dict) else {}
        is_suno_bypassed = bool(bus.get('suno_bypassed', False)) or (isinstance(latent_video_audio, dict) and bool(latent_video_audio.get('suno_bypassed', False)))
        aud_mode = str(bus.get('audio_soundtrack_mode') or (latent_video_audio.get('audio_soundtrack_mode') if isinstance(latent_video_audio, dict) else '') or '').strip().lower()
        suno_cfg = None
        if not is_suno_bypassed:
            cand_suno = bus.get('suno_music_studio') or (latent_video_audio.get('suno_music_studio') if isinstance(latent_video_audio, dict) else None)
            if isinstance(cand_suno, dict) and cand_suno.get('active'):
                suno_cfg = dict(cand_suno)
        if not isinstance(suno_cfg, dict) or not suno_cfg.get('active'):
            try:
                from ..EZ_ENGINES.engine_ez_12_cinematrix_suno_music_studio import resolve_or_preexecute_active_suno_packet
                resolved_suno = resolve_or_preexecute_active_suno_packet(bus)
                if isinstance(resolved_suno, dict) and resolved_suno.get('active'):
                    suno_cfg = dict(resolved_suno)
                    is_suno_bypassed = False
                    bus['suno_bypassed'] = False
                    bus['suno_music_studio'] = dict(suno_cfg)
            except Exception:
                pass
        if not isinstance(suno_cfg, dict) or not suno_cfg.get('active'):
            is_suno_bypassed = True
        if isinstance(latent_video_audio, dict):
            latent_video_audio = dict(latent_video_audio)
            if aud_mode:
                latent_video_audio['audio_soundtrack_mode'] = aud_mode
            latent_video_audio['suno_bypassed'] = bool(is_suno_bypassed)
            if isinstance(suno_cfg, dict) and suno_cfg.get('active') and not is_suno_bypassed:
                latent_video_audio['suno_music_studio'] = dict(suno_cfg)
                if isinstance(latent_video_audio.get('ez_continuation_ctx'), dict):
                    latent_video_audio['ez_continuation_ctx']['suno_music_studio'] = dict(suno_cfg)
            else:
                latent_video_audio.pop('suno_music_studio', None)
        (out_lat, ticket_str) = execute_temporal_chunked_sampling(model=active_video_model, positive=positive, negative=negative, latent_dict=latent_video_audio, seed=eff_seed, steps=steps, cfg=cfg, sampler_name=sampler_name, scheduler=scheduler, denoise=denoise, enable_latent_2x_upscale=enable_latent_2x_upscale, previous_latent_opt=previous_segment_latent, tier_profile=tier_prof, anatomy_cfg=active_dock)
        if isinstance(out_lat, dict):
            if aud_mode:
                out_lat['audio_soundtrack_mode'] = aud_mode
            out_lat['suno_bypassed'] = bool(is_suno_bypassed)
            if isinstance(suno_cfg, dict) and suno_cfg.get('active') and not is_suno_bypassed:
                out_lat['suno_music_studio'] = dict(suno_cfg)
                bus['suno_music_studio'] = dict(suno_cfg)
            else:
                out_lat.pop('suno_music_studio', None)
                bus.pop('suno_music_studio', None)
            prev_vmeta = dict(latent_video_audio.get('ez_vault_metadata', {})) if isinstance(latent_video_audio, dict) and isinstance(latent_video_audio.get('ez_vault_metadata'), dict) else {}
            m_vmeta = getattr(active_video_model, '_ez_video_model_meta', None) if active_video_model is not None else None
            if isinstance(m_vmeta, dict):
                for mk, mv in m_vmeta.items():
                    if mv and not prev_vmeta.get(mk):
                        prev_vmeta[mk] = mv
                    if mv and not bus.get(mk):
                        bus[mk] = mv
            prev_vmeta.update({
                'video_sampler_seed': int(eff_seed),
                'video_seed_mode': str(seed_mode),
                'video_steps': int(steps),
                'video_cfg': float(cfg),
                'video_sampler_name': str(sampler_name),
                'video_scheduler': str(scheduler),
                'video_denoise': float(denoise),
                'enable_latent_2x_upscale': bool(enable_latent_2x_upscale),
                'canvas_seed': int(master_seed),
                'qwenvl_seed': int(qwen_seed),
                'image_sampler_seed': int(image_seed),
                'continuity_ticket': str(ticket_str),
            })
            for bk in ('video_model', 'active_video_unet', 'video_unet_fl2va', 'video_unet_ref2va', 'video_clip_name', 'video_clip_type', 'video_vae_name', 'audio_vae_name', 'active_video_loras', 'video_turbo_lora', 'turbo_video_strength', 'turbo_audio_strength', 'shift_video', 'shift_audio', 'active_image_unet', 'active_style_loras', 'krea2_image_prompt', 'h3_video_timeline_prompt', 'adaptive_negative_prompt', 'style_target', 'subject_1_age', 'keyframe_filename', 'krea2_saved_metadata'):
                if bus.get(bk) and not prev_vmeta.get(bk):
                    prev_vmeta[bk] = bus.get(bk)
            out_lat['ez_vault_metadata'] = prev_vmeta
        bus['suno_bypassed'] = bool(is_suno_bypassed)
        if aud_mode:
            bus['audio_soundtrack_mode'] = aud_mode
        bus['continuity_ticket'] = ticket_str
        bus['video_sampler_seed'] = int(eff_seed)
        return (out_lat, ticket_str, bus)
