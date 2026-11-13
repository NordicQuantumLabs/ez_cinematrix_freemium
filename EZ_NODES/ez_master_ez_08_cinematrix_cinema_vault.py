# -*- coding: utf-8 -*-
from ..EZ_ENGINES.engine_ez_08_cinematrix_cinema_vault import list_dynamic_upscale_models, list_dynamic_1x_detailer_models, list_dynamic_rife_models, _resolve_vault_frame_rate, _resolve_vault_quality_crf, _resolve_ffmpeg_binary, _vault_gaussian_blur_2d, _vault_capsule_sdf_2d, _compute_vault_anatomy_zones, _render_vault_anatomy_preview, _apply_vault_frequency_polish, _decode_single_vae_chunk, _normalize_single_audio_tensor_to_np, _decode_audio_latent_to_wav, _encode_video_with_pyav, _encode_video_with_ffmpeg, _apply_real_upscale_model, _execute_optical_flow_rife_interpolation, _resolve_vault_date_subfolder, decode_and_postprocess_cinema_stream, FRAME_RATE_PRESETS, QUALITY_CRF_PRESETS, VAULT_DATE_FOLDER_FORMAT_PRESETS, _VAULT_KEYPOINT_CACHE
from ..EZ_ADAPTERS.adapter_ez_08_cinematrix_cinema_vault import EzCinematrixVaultAdapter

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

class EZCinematrixCinemaVaultPostAndCombine:
    """💾 [ZONE 8] Cinema Vault Decoder, Neural Anatomy Skin Polish, RIFE Optical-Flow Interpolation & FFmpeg Multi-Codec Video/Audio Archiver."""

    @classmethod
    def INPUT_TYPES(cls):
        upscale_choices = list_dynamic_upscale_models()
        detailer_choices = list_dynamic_1x_detailer_models()
        rife_choices = list_dynamic_rife_models()
        return {'required': {'sampled_video_latent': ('LATENT',), 'video_vae': ('VAE',), 'frame_rate': (FRAME_RATE_PRESETS, {'default': '24 fps ★ [STANDARD - Biograf / Film]'}), 'custom_frame_rate': ('FLOAT', {'default': 24.0, 'min': 1.0, 'max': 240.0, 'step': 0.5}), 'codec': (['H.264', 'H.265 (HEVC)', 'AV1', 'VP9', 'ProRes 422', 'Animated WebP'], {'default': 'H.264'}), 'container': (['MP4', 'MKV', 'MOV', 'WEBM', 'WEBP'], {'default': 'MP4'}), 'bit_depth': (['Auto', '8-bit (yuv420p)', '10-bit (yuv420p10le)'], {'default': 'Auto'}), 'quality': (QUALITY_CRF_PRESETS, {'default': 'CRF 20 — Hög Produktionskvalitet (90% kvalitet, optimal balans)'}), 'custom_quality_crf': ('INT', {'default': 19, 'min': 0, 'max': 51, 'step': 1}), 'pingpong': ('BOOLEAN', {'default': False}), 'save_metadata': ('BOOLEAN', {'default': True}), 'date_folder_format': (VAULT_DATE_FOLDER_FORMAT_PRESETS, {'default': 'YYYY-MM-DD'}), 'save_first_and_last_frame': ('BOOLEAN', {'default': False}), 'crop_to_audio': ('BOOLEAN', {'default': False}), 'audio_codec': (['Auto', 'AAC', 'Opus', 'FLAC', 'WAV (PCM)', 'Mute'], {'default': 'Auto'}), 'audio_bitrate': (['128k', '192k', '256k', '320k'], {'default': '192k'}), 'enable_2x_frame_interpolation': ('BOOLEAN', {'default': False}), 'rife_model': (rife_choices, {'default': rife_choices[0]}), 'rife_multiplier': (['2x', '3x', '4x'], {'default': '2x'}), 'rife_strength': ('FLOAT', {'default': 1.0, 'min': 0.0, 'max': 1.0, 'step': 0.05, 'tooltip': 'Styrka på RIFE / Optical-Flow rörelsekompensering (1.0 = full optisk flödeswarp, 0.0 = av).'}), 'enable_rtx_lanczos_2x': ('BOOLEAN', {'default': False}), 'upscale_model_name': (upscale_choices, {'default': 'None'}), 'detailer_1x_model_name': (detailer_choices, {'default': 'None'}), 'enable_frequency_polish': ('BOOLEAN', {'default': True}), 'skin_blur_radius': ('FLOAT', {'default': 2.5, 'min': 0.0, 'max': 32.0, 'step': 0.1}), 'skin_texture_strength': ('FLOAT', {'default': 1.06, 'min': 0.0, 'max': 2.0, 'step': 0.02}), 'skin_polish_opacity': ('FLOAT', {'default': 0.55, 'min': 0.0, 'max': 1.0, 'step': 0.05}), 'filename_prefix': ('STRING', {'default': '30FPS/Vids/EZ_Cinematrix'}), 'save_frames_to_disk': ('BOOLEAN', {'default': True})}, 'optional': {'audio_vae': ('VAE',), 'suno_audio': ('AUDIO',), 'anatomy_dock': ('ANATOMY_DOCK',), 'cinematrix_bus': ('MINIMAX_GUIDE',)}}
    RETURN_TYPES = ('IMAGE', 'FLOAT', 'STRING', 'MINIMAX_GUIDE', 'IMAGE')
    RETURN_NAMES = ('video_frames', 'final_fps', 'saved_output_path', 'cinematrix_bus', 'anatomy_mask_preview')
    FUNCTION = 'execute_vault'
    OUTPUT_NODE = True
    CATEGORY = 'EZ_Cinematrix_Core/08_Cinema_Vault'

    @torch.inference_mode()
    def execute_vault(self, sampled_video_latent, video_vae, frame_rate='24 fps ★ [STANDARD - Biograf / Film]', custom_frame_rate=24.0, enable_2x_frame_interpolation=False, rife_model='rife49.pth', rife_multiplier='2x', rife_strength=1.0, enable_rtx_lanczos_2x=False, upscale_model_name='None', detailer_1x_model_name='None', filename_prefix='30FPS/Vids/EZ_Cinematrix', save_frames_to_disk=True, codec='H.264', container='MP4', bit_depth='Auto', quality='CRF 20 — Hög Produktionskvalitet (90% kvalitet, optimal balans)', custom_quality_crf=19, pingpong=False, save_metadata=True, date_folder_format='YYYY-MM-DD', save_first_and_last_frame=False, crop_to_audio=False, audio_codec='Auto', audio_bitrate='192k', enable_frequency_polish=True, skin_blur_radius=2.5, skin_texture_strength=1.06, skin_polish_opacity=0.55, audio_vae=None, suno_audio=None, anatomy_dock=None, cinematrix_bus=None, **_extra_kwargs):
        from ..EZ_ADAPTERS import adapter_ez_08_cinematrix_cinema_vault as _adp_mod_08
        live_vault_cls = getattr(_adp_mod_08, 'EzCinematrixVaultAdapter', EzCinematrixVaultAdapter)
        call_kwargs = {'sampled_video_latent': sampled_video_latent, 'video_vae': video_vae, 'frame_rate': frame_rate, 'enable_2x_frame_interpolation': enable_2x_frame_interpolation, 'enable_rtx_lanczos_2x': enable_rtx_lanczos_2x, 'upscale_model_name': upscale_model_name, 'detailer_1x_model_name': detailer_1x_model_name, 'filename_prefix': filename_prefix, 'save_frames_to_disk': save_frames_to_disk, 'codec': codec, 'container': container, 'bit_depth': bit_depth, 'quality': quality, 'pingpong': pingpong, 'save_metadata': save_metadata, 'date_folder_format': date_folder_format, 'save_first_and_last_frame': save_first_and_last_frame, 'crop_to_audio': crop_to_audio, 'audio_codec': audio_codec, 'audio_bitrate': audio_bitrate, 'enable_frequency_polish': enable_frequency_polish, 'skin_blur_radius': skin_blur_radius, 'skin_texture_strength': skin_texture_strength, 'skin_polish_opacity': skin_polish_opacity, 'rife_model': rife_model, 'rife_multiplier': rife_multiplier, 'rife_strength': rife_strength, 'audio_vae': audio_vae, 'anatomy_dock': anatomy_dock, 'cinematrix_bus': cinematrix_bus, 'custom_frame_rate': custom_frame_rate, 'custom_quality_crf': custom_quality_crf, 'suno_audio': suno_audio}
        return live_vault_cls.finalize_vault(**call_kwargs)
NODE_SUITE_VERSION = 'v1.0 Freemium'
NODE_CLASS_MAPPINGS = {'EZCinematrixCinemaVaultPostAndCombine': EZCinematrixCinemaVaultPostAndCombine}
NODE_DISPLAY_NAME_MAPPINGS = {'EZCinematrixCinemaVaultPostAndCombine': '💾 EZ [08] Cinematrix Cinema Vault, 2x Interpolation & RTX Refiner — Freemium v1.0'}
