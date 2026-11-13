# -*- coding: utf-8 -*-
from ..EZ_ENGINES.engine_ez_03_cinematrix_image_lora_splitter import _get_convrot_hadamard_matrix, list_dynamic_image_models, list_dynamic_clip_encoders, list_dynamic_vaes, list_dynamic_loras_by_role, apply_krea2_dynamic_shift_patch, _parse_comfy_quant_tensor, _pre_dequantize_convrot_state_dict, _dequantize_rowwise_module_fallback, _ensure_int8_convrot_quant_compat, _load_diffusion_model_convrot_safe, load_and_split_image_models_with_loras, _H4_BASE, _CONVROT_HADAMARD_CACHE
from ..EZ_ADAPTERS.adapter_ez_03_cinematrix_image_lora_splitter import EzCinematrixImageLoaderAdapter

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

class EZCinematrixImageModelAndLoraSplitter:
    """🧬 [ZONE 3] Dynamic Image Model/CLIP/VAE Loader & Dual-Stage LoRA Splitter (Locked Turbo Slot)."""

    @classmethod
    def INPUT_TYPES(cls):
        unet_list = list_dynamic_image_models()
        clip_list = list_dynamic_clip_encoders()
        vae_list = list_dynamic_vaes()
        style_lora_list = list_dynamic_loras_by_role(lock_turbo_only=False)
        turbo_lora_list = list_dynamic_loras_by_role(lock_turbo_only=True)
        return {
            'required': {
                'unet_name': (unet_list,),
                'clip_name': (clip_list,),
                'clip_type': (['krea2', 'flux', 'sdxl', 'pony', 'illustrious', 'sd3', 'qwen_image', 'stable_diffusion', 'wan'], {'default': 'krea2'}),
                'vae_name': (vae_list,),
                'stop_at_clip_layer': ('INT', {'default': -1, 'min': -24, 'max': -1, 'step': 1}),
                'sampling_mode': (['raw_dynamic', 'turbo_fixed', 'manual', 'bypass'], {'default': 'raw_dynamic'}),
                'enable_style_lora_1': ('BOOLEAN', {'default': True, 'label_on': '🟢 ON (Active)', 'label_off': '🔇 BYPASS (Off)'}),
                'style_lora_1': (style_lora_list, {'default': 'None'}),
                'style_strength_1': ('FLOAT', {'default': 0.8, 'min': -4.0, 'max': 4.0, 'step': 0.05}),
                'style_clip_strength_1': ('FLOAT', {'default': 1.0, 'min': -4.0, 'max': 4.0, 'step': 0.05}),
                'enable_style_lora_2': ('BOOLEAN', {'default': True, 'label_on': '🟢 ON (Active)', 'label_off': '🔇 BYPASS (Off)'}),
                'style_lora_2': (style_lora_list, {'default': 'None'}),
                'style_strength_2': ('FLOAT', {'default': 0.65, 'min': -4.0, 'max': 4.0, 'step': 0.05}),
                'style_clip_strength_2': ('FLOAT', {'default': 0.8, 'min': -4.0, 'max': 4.0, 'step': 0.05}),
                'enable_style_lora_3': ('BOOLEAN', {'default': True, 'label_on': '🟢 ON (Active)', 'label_off': '🔇 BYPASS (Off)'}),
                'style_lora_3': (style_lora_list, {'default': 'None'}),
                'style_strength_3': ('FLOAT', {'default': 0.45, 'min': -4.0, 'max': 4.0, 'step': 0.05}),
                'style_clip_strength_3': ('FLOAT', {'default': 0.45, 'min': -4.0, 'max': 4.0, 'step': 0.05}),
                'enable_style_lora_4': ('BOOLEAN', {'default': True, 'label_on': '🟢 ON (Active)', 'label_off': '🔇 BYPASS (Off)'}),
                'style_lora_4': (style_lora_list, {'default': 'None'}),
                'style_strength_4': ('FLOAT', {'default': 0.4, 'min': -4.0, 'max': 4.0, 'step': 0.05}),
                'style_clip_strength_4': ('FLOAT', {'default': 0.35, 'min': -4.0, 'max': 4.0, 'step': 0.05}),
                'enable_turbo_lora': ('BOOLEAN', {'default': True, 'label_on': '⚡ TURBO ON', 'label_off': '🔇 TURBO BYPASS (Off)'}),
                'turbo_acceleration_lora_LOCKED': (turbo_lora_list, {'default': 'None', 'tooltip': '⚡ LOCKED TURBO LORA SLOT: Filters Turbo/Step-Distilled LoRAs and injects exclusively into Stage 2 model stream.'}),
                'turbo_strength': ('FLOAT', {'default': 0.9, 'min': 0.0, 'max': 2.5, 'step': 0.05}),
                'positive_prompt': ('STRING', {'default': '', 'multiline': True}),
                'negative_prompt': ('STRING', {'default': '', 'multiline': True}),
            },
            'optional': {
                'image_model_spec': ('EZ_IMAGE_MODEL_SPEC',),
                'image_lora_spec': ('EZ_IMAGE_LORA_SPEC',),
                'cinematrix_bus': ('MINIMAX_GUIDE',),
            },
        }
    RETURN_TYPES = ('MODEL', 'MODEL', 'CONDITIONING', 'CONDITIONING', 'VAE', 'CLIP', 'MINIMAX_GUIDE')
    RETURN_NAMES = ('stage1_model', 'stage2_model', 'positive', 'negative', 'image_vae', 'image_clip', 'cinematrix_bus')
    FUNCTION = 'load_and_split'
    CATEGORY = 'EZ_Cinematrix_Core/03_Krea2_Loaders'

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        return True

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        qwen_tag = ''
        try:
            from server import PromptServer
            ps = getattr(PromptServer, 'instance', None)
            pq = getattr(ps, 'prompt_queue', None) if ps is not None else None
            running = getattr(pq, 'currently_running', None) if pq is not None else None
            if isinstance(running, dict) and len(running) > 0:
                active_item = next(iter(running.values()))
                p_graph = active_item[2] if isinstance(active_item, (list, tuple)) and len(active_item) > 2 and isinstance(active_item[2], dict) else None
                if isinstance(p_graph, dict):
                    for n_def in p_graph.values():
                        if isinstance(n_def, dict) and ('QwenVL' in str(n_def.get('class_type', '')) or 'EZ_02' in str(n_def.get('class_type', ''))):
                            n_in = n_def.get('inputs') if isinstance(n_def.get('inputs'), dict) else {}
                            qwen_tag = f"{n_in.get('style_target', '')}|{n_in.get('subject_1_age', '')}|{n_in.get('custom_subject_1_age', '')}|{n_in.get('content_rating_mode', '')}"
                            break
        except Exception:
            pass
        return f"{kwargs.get('unet_name', '')}|{kwargs.get('style_lora_1', '')}|{kwargs.get('style_lora_2', '')}|{kwargs.get('style_lora_3', '')}|{kwargs.get('style_lora_4', '')}|{qwen_tag}"

    @torch.inference_mode()
    def load_and_split(self, unet_name, clip_name, clip_type, vae_name, stop_at_clip_layer, sampling_mode, style_lora_1, style_strength_1, style_lora_2, style_strength_2, style_lora_3, style_strength_3, turbo_acceleration_lora_LOCKED, turbo_strength, style_clip_strength_1=1.0, style_clip_strength_2=0.8, style_clip_strength_3=0.45, style_lora_4='None', style_strength_4=0.4, style_clip_strength_4=0.35, enable_style_lora_1=True, enable_style_lora_2=True, enable_style_lora_3=True, enable_style_lora_4=True, enable_turbo_lora=True, positive_prompt='', negative_prompt='', image_model_spec=None, image_lora_spec=None, cinematrix_bus=None):
        return EzCinematrixImageLoaderAdapter.execute_hub(unet_name=unet_name, clip_name=clip_name, clip_type=clip_type, vae_name=vae_name, stop_at_clip_layer=stop_at_clip_layer, sampling_mode=sampling_mode, style_lora_1=style_lora_1, style_strength_1=style_strength_1, style_lora_2=style_lora_2, style_strength_2=style_strength_2, style_lora_3=style_lora_3, style_strength_3=style_strength_3, turbo_acceleration_lora_LOCKED=turbo_acceleration_lora_LOCKED, turbo_strength=turbo_strength, positive_prompt=positive_prompt, negative_prompt=negative_prompt, style_clip_strength_1=style_clip_strength_1, style_clip_strength_2=style_clip_strength_2, style_clip_strength_3=style_clip_strength_3, style_lora_4=style_lora_4, style_strength_4=style_strength_4, style_clip_strength_4=style_clip_strength_4, enable_style_lora_1=enable_style_lora_1, enable_style_lora_2=enable_style_lora_2, enable_style_lora_3=enable_style_lora_3, enable_style_lora_4=enable_style_lora_4, enable_turbo_lora=enable_turbo_lora, cinematrix_bus=cinematrix_bus, image_model_spec=image_model_spec, image_lora_spec=image_lora_spec)
NODE_SUITE_VERSION = 'v1.0 Freemium'
NODE_CLASS_MAPPINGS = {'EZCinematrixImageModelAndLoraSplitter': EZCinematrixImageModelAndLoraSplitter}
NODE_DISPLAY_NAME_MAPPINGS = {'EZCinematrixImageModelAndLoraSplitter': '🧬 EZ [03] Cinematrix Image Model & Dual-Stage Turbo LoRA Splitter — Freemium v1.0'}
