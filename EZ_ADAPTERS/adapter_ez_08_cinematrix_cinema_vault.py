# -*- coding: utf-8 -*-
from ..EZ_ENGINES.engine_ez_08_cinematrix_cinema_vault import list_dynamic_upscale_models, list_dynamic_1x_detailer_models, list_dynamic_rife_models, _resolve_vault_frame_rate, _resolve_vault_quality_crf, _resolve_ffmpeg_binary, _vault_gaussian_blur_2d, _vault_capsule_sdf_2d, _compute_vault_anatomy_zones, _render_vault_anatomy_preview, _apply_vault_frequency_polish, _decode_single_vae_chunk, _normalize_single_audio_tensor_to_np, _suppress_vocal_formant_chatter_in_sfx, _decode_audio_latent_to_wav, _encode_video_with_pyav, _encode_video_with_ffmpeg, _apply_real_upscale_model, _execute_optical_flow_rife_interpolation, _resolve_vault_date_subfolder, decode_and_postprocess_cinema_stream, FRAME_RATE_PRESETS, QUALITY_CRF_PRESETS, VAULT_DATE_FOLDER_FORMAT_PRESETS, _VAULT_KEYPOINT_CACHE

import gc
import os
import shutil
import subprocess
import wave
from datetime import datetime
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import torch
import folder_paths
import comfy.model_management
import comfy.utils

class EzCinematrixVaultAdapter:
    """Adapter handling VAE decoding, RIFE optical-flow interpolation, Neural Anatomy Frequency Skin Polish, and FFmpeg H.264/H.265/AV1 + Audio export."""

    @staticmethod
    def finalize_vault(sampled_video_latent, video_vae, frame_rate, enable_2x_frame_interpolation, enable_rtx_lanczos_2x, upscale_model_name, filename_prefix, save_frames_to_disk, codec='H.264', container='MP4', bit_depth='Auto', quality=18, pingpong=False, save_metadata=True, date_folder_format='YYYY-MM-DD', save_first_and_last_frame=False, crop_to_audio=False, audio_codec='Auto', audio_bitrate='192k', enable_frequency_polish=True, skin_blur_radius=2.5, skin_texture_strength=1.06, skin_polish_opacity=0.55, rife_model='rife49.pth', rife_multiplier='2x', rife_strength=1.0, detailer_1x_model_name='None', audio_vae=None, anatomy_dock=None, cinematrix_bus=None, custom_frame_rate=24.0, custom_quality_crf=18, suno_audio=None, **_extra_kwargs):
        bus = dict(cinematrix_bus) if isinstance(cinematrix_bus, dict) else {}
        dock_cfg = dict(anatomy_dock) if isinstance(anatomy_dock, dict) else dict(bus.get('anatomy_dock', {})) if isinstance(bus.get('anatomy_dock'), dict) else {}
        sat_str_08 = float(bus.get('color_saturation_strength', (sampled_video_latent.get('color_saturation_strength', 0.80) if isinstance(sampled_video_latent, dict) else 0.80)) or 0.80)
        style_08 = str(bus.get('style_target') or (sampled_video_latent.get('style_target') if isinstance(sampled_video_latent, dict) else '') or dock_cfg.get('style_target') or 'realism').strip()
        dock_cfg['color_saturation_strength'] = sat_str_08
        dock_cfg['style_target'] = style_08
        bus['anatomy_dock'] = dock_cfg
        bus_aud_mode = str(bus.get('audio_soundtrack_mode') or (sampled_video_latent.get('audio_soundtrack_mode') if isinstance(sampled_video_latent, dict) else '') or '').strip().lower()
        eff_direct_aud = suno_audio if (isinstance(suno_audio, dict) and isinstance(suno_audio.get('waveform'), torch.Tensor)) else (sampled_video_latent.get('suno_direct_audio') if (isinstance(sampled_video_latent, dict) and isinstance(sampled_video_latent.get('suno_direct_audio'), dict) and isinstance(sampled_video_latent['suno_direct_audio'].get('waveform'), torch.Tensor)) else (bus.get('suno_direct_audio') if (isinstance(bus.get('suno_direct_audio'), dict) and isinstance(bus['suno_direct_audio'].get('waveform'), torch.Tensor)) else None))
        has_direct_suno = isinstance(eff_direct_aud, dict) and isinstance(eff_direct_aud.get('waveform'), torch.Tensor) and float(eff_direct_aud['waveform'].abs().max().item()) > 1e-04
        is_suno_bypassed = False if has_direct_suno else (bool(bus.get('suno_bypassed', False)) or (isinstance(sampled_video_latent, dict) and bool(sampled_video_latent.get('suno_bypassed', False))))
        raw_suno_cfg = {} if is_suno_bypassed else (dict(bus.get('suno_music_studio', {})) if isinstance(bus.get('suno_music_studio'), dict) else (dict(sampled_video_latent.get('suno_music_studio', {})) if isinstance(sampled_video_latent, dict) and isinstance(sampled_video_latent.get('suno_music_studio'), dict) else {}))
        skip_suno_mux = is_suno_bypassed or (not raw_suno_cfg.get('active') and not has_direct_suno)
        suno_cfg = {} if skip_suno_mux else raw_suno_cfg
        if isinstance(sampled_video_latent, dict):
            sampled_video_latent = dict(sampled_video_latent)
            sampled_video_latent['audio_soundtrack_mode'] = 'bgm_with_vocals' if (suno_cfg.get('active') or has_direct_suno) else (bus_aud_mode or 'sfx_only')
            if skip_suno_mux or (not suno_cfg.get('active') and not has_direct_suno):
                sampled_video_latent.pop('suno_music_studio', None)
                sampled_video_latent.pop('suno_direct_audio', None)
            else:
                if suno_cfg.get('active'):
                    sampled_video_latent['suno_music_studio'] = suno_cfg
                if has_direct_suno:
                    sampled_video_latent['suno_direct_audio'] = eff_direct_aud
        tier_prof = dict(bus.get('hardware_tier_profile', {})) if isinstance(bus.get('hardware_tier_profile'), dict) else {}
        eff_fps = _resolve_vault_frame_rate(frame_rate, custom_frame_rate)
        lat_fps = float(sampled_video_latent.get('frame_rate', 0.0) or bus.get('frame_rate', 0.0) or 0.0) if isinstance(sampled_video_latent, dict) else float(bus.get('frame_rate', 0.0) or 0.0)
        if lat_fps > 1.0 and str(frame_rate).strip().lower() != 'custom' and abs(eff_fps - 24.0) < 0.01 and abs(lat_fps - eff_fps) > 0.5:
            eff_fps = lat_fps
        eff_crf = _resolve_vault_quality_crf(quality, custom_quality_crf)
        v_fsm = getattr(video_vae, 'first_stage_model', video_vae)
        a_fsm = getattr(audio_vae, 'first_stage_model', audio_vae) if audio_vae is not None else None
        v_is_aud = 'audio' in (str(getattr(v_fsm, '__class__', type(v_fsm)).__name__) + '.' + str(getattr(v_fsm, '__class__', type(v_fsm)).__module__)).lower()
        a_is_aud = 'audio' in (str(getattr(a_fsm, '__class__', type(a_fsm)).__name__) + '.' + str(getattr(a_fsm, '__class__', type(a_fsm)).__module__)).lower() if a_fsm is not None else False
        if v_is_aud:
            if audio_vae is not None and (not a_is_aud):
                print('[EZ-VAULT] 🔄 Detekterade korskopplade VAE-kablar (video_vae <-> audio_vae) i EZ [08] — växlar automatiskt!')
                (video_vae, audio_vae) = (audio_vae, video_vae)
            else:
                bus_v_vae = bus.get('video_vae_obj') or (sampled_video_latent.get('video_vae_obj') if isinstance(sampled_video_latent, dict) else None)
                if bus_v_vae is not None:
                    print('[EZ-VAULT] 🛡️ Detekterade MiniMaxH3AudioVAE på video_vae-ingången i EZ [08] — återställer rätt MiniMaxH3VideoVAE automatiskt!')
                    if audio_vae is None or not a_is_aud:
                        audio_vae = video_vae
                    video_vae = bus_v_vae
        if audio_vae is None or not ('audio' in (str(getattr(getattr(audio_vae, 'first_stage_model', audio_vae), '__class__', type(audio_vae)).__name__)).lower()):
            bus_a_vae = bus.get('audio_vae_obj') or (sampled_video_latent.get('audio_vae_obj') if isinstance(sampled_video_latent, dict) else None)
            if bus_a_vae is not None:
                audio_vae = bus_a_vae
        vae_vmeta = getattr(video_vae, '_ez_video_model_meta', None) or getattr(audio_vae, '_ez_video_model_meta', None)
        if isinstance(vae_vmeta, dict):
            for vk, vv in vae_vmeta.items():
                if vv and not bus.get(vk):
                    bus[vk] = vv
        vault_meta_from_bus = {
            k: bus[k]
            for k in (
                'video_model',
                'active_video_unet',
                'video_unet_fl2va',
                'video_unet_ref2va',
                'video_clip_name',
                'video_clip_type',
                'video_vae_name',
                'audio_vae_name',
                'active_video_loras',
                'video_turbo_lora',
                'turbo_video_strength',
                'turbo_audio_strength',
                'shift_video',
                'shift_audio',
                'active_image_unet',
                'active_style_loras',
                'krea2_image_prompt',
                'h3_video_timeline_prompt',
                'adaptive_negative_prompt',
                'style_target',
                'subject_1_age',
                'canvas_seed',
                'qwenvl_seed',
                'image_sampler_seed',
                'video_sampler_seed',
                'keyframe_filename',
                'krea2_saved_metadata',
            )
            if k in bus and bus[k] is not None
        }
        (frames_out, fps_out, path_out, ui_images, anatomy_preview) = decode_and_postprocess_cinema_stream(sampled_video_latent=sampled_video_latent, video_vae=video_vae, frame_rate=eff_fps, enable_2x_frame_interpolation=enable_2x_frame_interpolation, enable_rtx_lanczos_2x=enable_rtx_lanczos_2x, filename_prefix=filename_prefix, save_frames_to_disk=save_frames_to_disk, tier_profile=tier_prof, audio_vae=audio_vae, codec=codec, container=container, bit_depth=bit_depth, quality=eff_crf, pingpong=pingpong, save_metadata=save_metadata, date_folder_format=date_folder_format, save_first_and_last_frame=save_first_and_last_frame, crop_to_audio=crop_to_audio, audio_codec=audio_codec, audio_bitrate=audio_bitrate, enable_frequency_polish=enable_frequency_polish, skin_blur_radius=skin_blur_radius, skin_texture_strength=skin_texture_strength, skin_polish_opacity=skin_polish_opacity, dock_cfg=dock_cfg, custom_frame_rate=custom_frame_rate, custom_quality_crf=custom_quality_crf, upscale_model_name=upscale_model_name, rife_model=rife_model, rife_multiplier=rife_multiplier, rife_strength=rife_strength, detailer_1x_model_name=detailer_1x_model_name, vault_metadata=vault_meta_from_bus)
        bus.update({'final_fps': fps_out, 'last_saved_path': path_out, 'upscale_model_selected': upscale_model_name, 'detailer_1x_model_selected': detailer_1x_model_name, 'rife_model': rife_model, 'rife_multiplier': rife_multiplier, 'rife_strength': float(rife_strength), 'vault_codec': codec, 'vault_container': container, 'vault_quality': int(eff_crf), 'date_folder_format': date_folder_format})
        return {'ui': {'ez_video': ui_images, 'gifs': ui_images}, 'result': (frames_out, fps_out, path_out, bus, anatomy_preview)}
