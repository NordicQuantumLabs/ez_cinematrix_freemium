# -*- coding: utf-8 -*-
from ..EZ_ENGINES.engine_ez_05_cinematrix_video_lora_stack import _get_video_convrot_hadamard, get_dynamic_video_unets, get_dynamic_video_clips, get_dynamic_video_vaes, get_dynamic_video_loras, _parse_video_comfy_quant_tensor, _pre_dequantize_video_convrot_state_dict, _dequantize_video_rowwise_fallback, _ensure_video_quant_compat, _load_video_diffusion_model_convrot_safe, _load_video_vae_convrot_safe, _apply_modality_separated_av_lora, load_video_engine_and_apply_av_loras, _H4_BASE, _VIDEO_HADAMARD_CACHE
from ..EZ_ADAPTERS.adapter_ez_05_cinematrix_video_lora_stack import EzCinematrixVideoLoaderAdapter

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

class EZCinematrixVideoEngineAndLoraStack:
    """🎥 [ZONE 5] Dynamic Video/Audio Engine Loader & Dual-Strength LoRA Stack (Locked Video Turbo Slot)."""

    @classmethod
    def INPUT_TYPES(cls):
        unets = get_dynamic_video_unets()
        ref_unets = ['Same as Primary (fl2va)'] + unets
        clips = get_dynamic_video_clips()
        vaes = get_dynamic_video_vaes()
        std_loras = get_dynamic_video_loras(lock_turbo_only=False)
        turbo_loras = get_dynamic_video_loras(lock_turbo_only=True)
        return {
            'required': {
                'video_unet_fl2va': (unets,),
                'video_unet_ref2va': (ref_unets, {'default': 'Same as Primary (fl2va)'}),
                'video_clip_name': (clips,),
                'clip_type': (['minimax', 'wan', 'wan2.2', 'ltxv', 'hunyuan_video', 'mochi', 'stable_diffusion'], {'default': 'minimax'}),
                'video_vae_name': (vaes,),
                'audio_vae_name': (vaes, {'default': 'None'}),
                'enable_video_lora_1': ('BOOLEAN', {'default': True, 'label_on': '🟢 ON (Active)', 'label_off': '🔇 BYPASS (Off)'}),
                'video_lora_1': (std_loras, {'default': 'None'}),
                'lora_1_video_strength': ('FLOAT', {'default': 0.25, 'min': -4.0, 'max': 4.0, 'step': 0.05}),
                'lora_1_vis_strength': ('FLOAT', {'default': 1.0, 'min': -4.0, 'max': 4.0, 'step': 0.05}),
                'lora_1_audio_strength': ('FLOAT', {'default': 0.0, 'min': -4.0, 'max': 4.0, 'step': 0.05}),
                'lora_1_clip_strength': ('FLOAT', {'default': 0.0, 'min': -4.0, 'max': 4.0, 'step': 0.05}),
                'enable_video_lora_2': ('BOOLEAN', {'default': True, 'label_on': '🟢 ON (Active)', 'label_off': '🔇 BYPASS (Off)'}),
                'video_lora_2': (std_loras, {'default': 'None'}),
                'lora_2_video_strength': ('FLOAT', {'default': 0.2, 'min': -4.0, 'max': 4.0, 'step': 0.05}),
                'lora_2_vis_strength': ('FLOAT', {'default': 1.0, 'min': -4.0, 'max': 4.0, 'step': 0.05}),
                'lora_2_audio_strength': ('FLOAT', {'default': 0.0, 'min': -4.0, 'max': 4.0, 'step': 0.05}),
                'lora_2_clip_strength': ('FLOAT', {'default': 0.0, 'min': -4.0, 'max': 4.0, 'step': 0.05}),
                'enable_video_lora_3': ('BOOLEAN', {'default': True, 'label_on': '🟢 ON (Active)', 'label_off': '🔇 BYPASS (Off)'}),
                'video_lora_3': (std_loras, {'default': 'None'}),
                'lora_3_video_strength': ('FLOAT', {'default': 0.2, 'min': -4.0, 'max': 4.0, 'step': 0.05}),
                'lora_3_vis_strength': ('FLOAT', {'default': 1.0, 'min': -4.0, 'max': 4.0, 'step': 0.05}),
                'lora_3_audio_strength': ('FLOAT', {'default': 0.0, 'min': -4.0, 'max': 4.0, 'step': 0.05}),
                'lora_3_clip_strength': ('FLOAT', {'default': 0.0, 'min': -4.0, 'max': 4.0, 'step': 0.05}),
                'enable_video_lora_4': ('BOOLEAN', {'default': True, 'label_on': '🟢 ON (Active)', 'label_off': '🔇 BYPASS (Off)'}),
                'video_lora_4': (std_loras, {'default': 'None'}),
                'lora_4_video_strength': ('FLOAT', {'default': 0.2, 'min': -4.0, 'max': 4.0, 'step': 0.05}),
                'lora_4_vis_strength': ('FLOAT', {'default': 1.0, 'min': -4.0, 'max': 4.0, 'step': 0.05}),
                'lora_4_audio_strength': ('FLOAT', {'default': 0.0, 'min': -4.0, 'max': 4.0, 'step': 0.05}),
                'lora_4_clip_strength': ('FLOAT', {'default': 0.0, 'min': -4.0, 'max': 4.0, 'step': 0.05}),
                'enable_video_turbo_lora': ('BOOLEAN', {'default': True, 'label_on': '⚡ TURBO ON', 'label_off': '🔇 TURBO BYPASS (Off)'}),
                'video_turbo_lora_LOCKED': (turbo_loras, {'default': 'None', 'tooltip': '⚡ LOCKED VIDEO TURBO LORA SLOT: Dedicated slot for MiniMax H3 / Wan 2.2 / LTX step-distilled & Turbo video LoRAs.'}),
                'turbo_video_strength': ('FLOAT', {'default': 1.0, 'min': 0.0, 'max': 2.5, 'step': 0.05}),
                'turbo_vis_strength': ('FLOAT', {'default': 1.0, 'min': 0.0, 'max': 2.5, 'step': 0.05}),
                'turbo_audio_strength': ('FLOAT', {'default': 1.0, 'min': 0.0, 'max': 2.5, 'step': 0.05}),
                'shift_video': ('FLOAT', {'default': 5.0, 'min': 0.0, 'max': 30.0, 'step': 0.5}),
                'shift_audio': ('FLOAT', {'default': 3.0, 'min': 0.0, 'max': 30.0, 'step': 0.5}),
                'enable_fp16_accumulation': ('BOOLEAN', {'default': True}),
            },
            'optional': {
                'video_model_spec': ('EZ_VIDEO_MODEL_SPEC',),
                'video_lora_spec': ('EZ_VIDEO_LORA_SPEC',),
                'cinematrix_bus': ('MINIMAX_GUIDE',),
            },
        }
    RETURN_TYPES = ('MODEL', 'MODEL', 'CLIP', 'VAE', 'VAE', 'MINIMAX_GUIDE')
    RETURN_NAMES = ('video_model_fl2va', 'video_model_ref2va', 'video_clip', 'video_vae', 'audio_vae', 'cinematrix_bus')
    FUNCTION = 'load_video_stack'
    CATEGORY = 'EZ_Cinematrix_Core/05_Video_Loaders'

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        return True

    @torch.inference_mode()
    def load_video_stack(self, video_unet_fl2va, video_unet_ref2va, video_clip_name, clip_type, video_vae_name, audio_vae_name, video_lora_1, lora_1_video_strength, lora_1_audio_strength, video_lora_2, lora_2_video_strength, lora_2_audio_strength, video_lora_3, lora_3_video_strength, lora_3_audio_strength, video_turbo_lora_LOCKED, turbo_video_strength, turbo_audio_strength, shift_video, shift_audio, enable_fp16_accumulation, lora_1_vis_strength=1.0, lora_1_clip_strength=0.0, lora_2_vis_strength=1.0, lora_2_clip_strength=0.0, lora_3_vis_strength=1.0, lora_3_clip_strength=0.0, video_lora_4='None', lora_4_video_strength=0.2, lora_4_vis_strength=1.0, lora_4_audio_strength=0.0, lora_4_clip_strength=0.0, enable_video_lora_1=True, enable_video_lora_2=True, enable_video_lora_3=True, enable_video_lora_4=True, enable_video_turbo_lora=True, turbo_vis_strength=1.0, video_model_spec=None, video_lora_spec=None, cinematrix_bus=None, **_extra_kwargs):
        return EzCinematrixVideoLoaderAdapter.load_stack(video_unet_fl2va=video_unet_fl2va, video_unet_ref2va=video_unet_ref2va, video_clip_name=video_clip_name, clip_type=clip_type, video_vae_name=video_vae_name, audio_vae_name=audio_vae_name, video_lora_1=video_lora_1, lora_1_video_strength=lora_1_video_strength, lora_1_audio_strength=lora_1_audio_strength, video_lora_2=video_lora_2, lora_2_video_strength=lora_2_video_strength, lora_2_audio_strength=lora_2_audio_strength, video_lora_3=video_lora_3, lora_3_video_strength=lora_3_video_strength, lora_3_audio_strength=lora_3_audio_strength, video_turbo_lora_LOCKED=video_turbo_lora_LOCKED, turbo_video_strength=turbo_video_strength, turbo_audio_strength=turbo_audio_strength, shift_video=shift_video, shift_audio=shift_audio, enable_fp16_accumulation=enable_fp16_accumulation, lora_1_vis_strength=lora_1_vis_strength, lora_1_clip_strength=lora_1_clip_strength, lora_2_vis_strength=lora_2_vis_strength, lora_2_clip_strength=lora_2_clip_strength, lora_3_vis_strength=lora_3_vis_strength, lora_3_clip_strength=lora_3_clip_strength, video_lora_4=video_lora_4, lora_4_video_strength=lora_4_video_strength, lora_4_vis_strength=lora_4_vis_strength, lora_4_audio_strength=lora_4_audio_strength, lora_4_clip_strength=lora_4_clip_strength, enable_video_lora_1=enable_video_lora_1, enable_video_lora_2=enable_video_lora_2, enable_video_lora_3=enable_video_lora_3, enable_video_lora_4=enable_video_lora_4, enable_video_turbo_lora=enable_video_turbo_lora, turbo_vis_strength=turbo_vis_strength, cinematrix_bus=cinematrix_bus, video_model_spec=video_model_spec, video_lora_spec=video_lora_spec, **_extra_kwargs)
NODE_SUITE_VERSION = 'v1.0 Freemium'
NODE_CLASS_MAPPINGS = {'EZCinematrixVideoEngineAndLoraStack': EZCinematrixVideoEngineAndLoraStack}
NODE_DISPLAY_NAME_MAPPINGS = {'EZCinematrixVideoEngineAndLoraStack': '🎥 EZ [05] Cinematrix Video/Audio Engine & Locked Turbo LoRA Stack — Freemium v1.0'}
