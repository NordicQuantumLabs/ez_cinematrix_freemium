# -*- coding: utf-8 -*-
from ..EZ_ENGINES.engine_ez_04_cinematrix_krea2_sampler import _sigma_schedule, _percent_schedule_index, _nearest_schedule_index, build_three_stage_sigma_triplet, _zero_out_conditioning, _maybe_upscale_latent, _create_empty_krea2_latent, sample_stage_with_sigmas, _gaussian_blur_2d, _capsule_sdf_2d, _detect_skeletal_keypoints_rcnn, _compute_neural_anatomy_zones, compute_downscaled_latent_anatomy_zones, _render_anatomy_preview_bhwc, _stabilize_latent_anatomy_outliers, _anchor_original_style_latent, _anchor_orc_tusk_mouth_latent, _apply_2d_cel_and_ink_stylization_bchw, _restore_i2i_orc_tusks_bhwc, _apply_frequency_separation_polish, _compose_multi_reference_canvas, _compute_krea2_generation_signature, _try_load_cached_krea2_keyframe, _store_cached_krea2_keyframe, _resolve_date_subfolder_path, UPSCALE_METHODS, DATE_FOLDER_FORMAT_PRESETS, _KEYPOINT_RCNN_CACHE, _KREA2_KEYFRAME_VAULT
from ..EZ_ADAPTERS.adapter_ez_04_cinematrix_krea2_sampler import EzCinematrixThreeStageAdapter

import math
import gc
import torch
import comfy.model_management
import comfy.sample
import comfy.samplers
import comfy.utils
import latent_preview
import nodes

class EZCinematrixKrea2ThreeStageSampler:
    """🎨 [ZONE 4] Krea 2 Three-Stage Keyframe Sampler (Composition -> Turbo Handoff -> HiRes Polish + Self-Driving Neural Anatomy & Skin Polish)."""

    @classmethod
    def INPUT_TYPES(cls):
        seed_mode_choices = ['auto_from_bus_or_local', 'reuse_latest_keyframe_image', 'use_local_image_seed', 'sync_with_master_seed_01', 'sync_with_qwenvl_seed_02']
        return {'required': {'stage1_model': ('MODEL',), 'stage2_model': ('MODEL',), 'image_vae': ('VAE',), 'seed': ('INT', {'default': 860481191328700, 'min': 0, 'max': 9007199254740991, 'step': 1, 'control_after_generate': True}), 'seed_mode': (seed_mode_choices, {'default': seed_mode_choices[0]}), 'i2i_denoise': ('FLOAT', {'default': 0.75, 'min': 0.05, 'max': 1.0, 'step': 0.01, 'round': 0.01, 'tooltip': 'Styr hur mycket källbilden (source_image) bevaras vid Image-to-Image i steg om 0.01 (0.60-0.70 låser klädsel/detaljer hårt, 0.72-0.78 balanserad realism/ålder, 0.82-0.90 bryter målad källbild till foto, 1.0 = T2I).'}), 'handoff_percent': ('FLOAT', {'default': 58.0, 'min': 1.0, 'max': 100.0, 'step': 0.01, 'round': 0.01}), 'stage3_handoff_percent': ('FLOAT', {'default': 90.0, 'min': 5.0, 'max': 99.0, 'step': 0.01, 'round': 0.01}), 'stage1_steps': ('INT', {'default': 52, 'min': 4, 'max': 200}), 'stage1_cfg': ('FLOAT', {'default': 3.0, 'min': 0.5, 'max': 30.0, 'step': 0.1}), 'stage1_sampler_name': (comfy.samplers.KSampler.SAMPLERS,), 'stage1_scheduler': (comfy.samplers.KSampler.SCHEDULERS,), 'stage2_steps': ('INT', {'default': 14, 'min': 0, 'max': 100}), 'stage2_cfg': ('FLOAT', {'default': 1.0, 'min': 0.5, 'max': 20.0, 'step': 0.1}), 'stage2_sampler_name': (comfy.samplers.KSampler.SAMPLERS,), 'stage2_scheduler': (comfy.samplers.KSampler.SCHEDULERS,), 'final_width': ('INT', {'default': 1728, 'min': 0, 'max': nodes.MAX_RESOLUTION, 'step': 8}), 'final_height': ('INT', {'default': 1152, 'min': 0, 'max': nodes.MAX_RESOLUTION, 'step': 8}), 'upscale_method': (UPSCALE_METHODS, {'default': 'bislerp'}), 'enable_frequency_polish': ('BOOLEAN', {'default': False}), 'skin_blur_radius': ('FLOAT', {'default': 1.8, 'min': 0.0, 'max': 32.0, 'step': 0.1}), 'skin_texture_strength': ('FLOAT', {'default': 1.12, 'min': 0.0, 'max': 2.0, 'step': 0.01, 'round': 0.01}), 'skin_polish_opacity': ('FLOAT', {'default': 0.25, 'min': 0.0, 'max': 1.0, 'step': 0.01, 'round': 0.01}), 'save_keyframe_to_disk': ('BOOLEAN', {'default': True}), 'save_metadata': ('BOOLEAN', {'default': True}), 'date_folder_format': (DATE_FOLDER_FORMAT_PRESETS, {'default': 'YYYY-MM-DD'})}, 'optional': {'source_image': ('IMAGE',), 'image_clip': ('CLIP',), 'krea2_image_prompt': ('STRING', {'forceInput': True}), 'adaptive_negative_prompt': ('STRING', {'forceInput': True}), 'positive': ('CONDITIONING',), 'negative': ('CONDITIONING',), 'anatomy_dock': ('ANATOMY_DOCK',), 'cinematrix_bus': ('MINIMAX_GUIDE',)}}
    RETURN_TYPES = ('IMAGE', 'LATENT', 'MINIMAX_GUIDE', 'IMAGE')
    RETURN_NAMES = ('keyframe_image', 'sampled_latent', 'cinematrix_bus', 'anatomy_mask_preview')
    FUNCTION = 'sample_three_stage'
    OUTPUT_NODE = True
    CATEGORY = 'EZ_Cinematrix_Core/04_Krea2_Samplers'

    @torch.inference_mode()
    def sample_three_stage(self, stage1_model, stage2_model, image_vae, seed, handoff_percent, stage3_handoff_percent, stage1_steps, stage1_cfg, stage1_sampler_name, stage1_scheduler, stage2_steps, stage2_cfg, stage2_sampler_name, stage2_scheduler, final_width, final_height, seed_mode='auto_from_bus_or_local', i2i_denoise=0.75, upscale_method='bislerp', enable_frequency_polish=False, skin_blur_radius=3.5, skin_texture_strength=1.08, skin_polish_opacity=0.65, save_keyframe_to_disk=True, save_metadata=True, date_folder_format='YYYY-MM-DD', source_image=None, image_clip=None, krea2_image_prompt='', adaptive_negative_prompt='', positive=None, negative=None, anatomy_dock=None, cinematrix_bus=None, **_extra_kwargs):
        from ..EZ_ADAPTERS import adapter_ez_04_cinematrix_krea2_sampler as _adp_mod_04
        live_adp_cls = getattr(_adp_mod_04, 'EzCinematrixThreeStageAdapter', EzCinematrixThreeStageAdapter)
        call_kwargs = {'stage1_model': stage1_model, 'stage2_model': stage2_model, 'image_vae': image_vae, 'source_image': source_image, 'seed': seed, 'handoff_percent': handoff_percent, 'stage3_handoff_percent': stage3_handoff_percent, 'stage1_steps': stage1_steps, 'stage1_cfg': stage1_cfg, 'stage1_sampler_name': stage1_sampler_name, 'stage1_scheduler': stage1_scheduler, 'stage2_steps': stage2_steps, 'stage2_cfg': stage2_cfg, 'stage2_sampler_name': stage2_sampler_name, 'stage2_scheduler': stage2_scheduler, 'final_width': final_width, 'final_height': final_height, 'upscale_method': upscale_method, 'positive': positive, 'negative': negative, 'image_clip': image_clip, 'krea2_image_prompt': krea2_image_prompt, 'adaptive_negative_prompt': adaptive_negative_prompt, 'save_keyframe_to_disk': save_keyframe_to_disk, 'save_metadata': save_metadata, 'date_folder_format': date_folder_format, 'seed_mode': seed_mode, 'i2i_denoise': i2i_denoise, 'enable_frequency_polish': enable_frequency_polish, 'skin_blur_radius': skin_blur_radius, 'skin_texture_strength': skin_texture_strength, 'skin_polish_opacity': skin_polish_opacity, 'anatomy_dock': anatomy_dock, 'cinematrix_bus': cinematrix_bus}
        return live_adp_cls.run_three_stage(**call_kwargs)
NODE_SUITE_VERSION = 'v1.0 Freemium'
NODE_CLASS_MAPPINGS = {'EZCinematrixKrea2ThreeStageSampler': EZCinematrixKrea2ThreeStageSampler}
NODE_DISPLAY_NAME_MAPPINGS = {'EZCinematrixKrea2ThreeStageSampler': '🎨 EZ [04] Cinematrix Krea 2 Three-Stage Keyframe Sampler — Freemium v1.0'}
