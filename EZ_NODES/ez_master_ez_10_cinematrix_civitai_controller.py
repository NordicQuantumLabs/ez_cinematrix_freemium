# -*- coding: utf-8 -*-
from ..EZ_ENGINES.engine_ez_10_cinematrix_civitai_controller import _get_suite_root, get_civitai_cache_dir, get_civitai_credentials_path, _get_asset_url_registry_path, load_asset_url_registry, register_asset_download_metadata, verify_civitai_license_status, load_civitai_api_key, save_civitai_api_key, purge_civitai_cache, classify_modality_from_metadata, inspect_safetensors_modality, _find_local_asset_full_path, ensure_civitai_asset_local, enforce_modality_lock, _normalize_arch_key, resolve_architecture_companions, download_architecture_companions, cache_civitai_media_thumbnail, _resolve_sort_label, _resolve_period_label, query_civitai_catalog, _get_recipes_file, load_civitai_recipes, save_civitai_recipe, delete_civitai_recipe, _find_sidecar_preview, scan_local_comfyui_assets, download_civitai_asset_to_comfyui, build_civitai_controller_specs, register_civitai_promptserver_routes, CACHE_TTL_DAYS, CACHE_TTL_SECONDS, IMAGE_BASE_MODELS, VIDEO_BASE_MODELS, CIVITAI_SORT_PRESETS, CIVITAI_PERIOD_PRESETS, CIVITAI_DOMAIN_PRESETS, CIVITAI_MODALITY_PRESETS, COMPANION_ARCH_PROFILES
from ..EZ_ADAPTERS.adapter_ez_10_cinematrix_civitai_controller import EzCinematrixCivitaiControllerAdapter

import hashlib
import json
import os
import struct
import time
import urllib.parse
import urllib.request
from pathlib import Path
import folder_paths
import torch

class EZCinematrixCivitaiController:
    """🌐 [ZONE 10] Civitai Controller & Recipe Hub (Strict Image [KREA2] vs Video [MiniMax H3] Modality Lock + 30d Cache)."""
    _ROUTES_READY = register_civitai_promptserver_routes()

    @classmethod
    def INPUT_TYPES(cls):
        register_civitai_promptserver_routes()
        all_unets = ['None'] + sorted(set((folder_paths.get_filename_list('diffusion_models') if 'diffusion_models' in folder_paths.folder_names_and_paths else []) + (folder_paths.get_filename_list('unet') if 'unet' in folder_paths.folder_names_and_paths else []) + (folder_paths.get_filename_list('checkpoints') if 'checkpoints' in folder_paths.folder_names_and_paths else [])))
        all_loras = ['None'] + sorted(set(folder_paths.get_filename_list('loras') if 'loras' in folder_paths.folder_names_and_paths else []))
        recipes = ['None'] + [str(r.get('name')) for r in load_civitai_recipes() if isinstance(r, dict) and r.get('name')]
        return {
            'required': {
                'controller_modality': (CIVITAI_MODALITY_PRESETS, {'default': CIVITAI_MODALITY_PRESETS[0]}),
                'civitai_domain': (CIVITAI_DOMAIN_PRESETS, {'default': CIVITAI_DOMAIN_PRESETS[0]}),
                'sort_by': (CIVITAI_SORT_PRESETS, {'default': CIVITAI_SORT_PRESETS[0]}),
                'time_period': (CIVITAI_PERIOD_PRESETS, {'default': CIVITAI_PERIOD_PRESETS[0]}),
                'image_architecture': (list(IMAGE_BASE_MODELS), {'default': 'KREA2'}),
                'image_unet_name': (all_unets, {'default': 'None'}),
                'enable_image_lora_1': ('BOOLEAN', {'default': True, 'label_on': '🟢 ON (Active)', 'label_off': '🔇 BYPASS (Off)'}),
                'image_style_lora_1': (all_loras, {'default': 'None'}),
                'image_style_strength_1': ('FLOAT', {'default': 0.8, 'min': -4.0, 'max': 4.0, 'step': 0.05}),
                'enable_image_lora_2': ('BOOLEAN', {'default': True, 'label_on': '🟢 ON (Active)', 'label_off': '🔇 BYPASS (Off)'}),
                'image_style_lora_2': (all_loras, {'default': 'None'}),
                'image_style_strength_2': ('FLOAT', {'default': 0.65, 'min': -4.0, 'max': 4.0, 'step': 0.05}),
                'enable_image_lora_3': ('BOOLEAN', {'default': True, 'label_on': '🟢 ON (Active)', 'label_off': '🔇 BYPASS (Off)'}),
                'image_style_lora_3': (all_loras, {'default': 'None'}),
                'image_style_strength_3': ('FLOAT', {'default': 0.45, 'min': -4.0, 'max': 4.0, 'step': 0.05}),
                'enable_image_lora_4': ('BOOLEAN', {'default': True, 'label_on': '🟢 ON (Active)', 'label_off': '🔇 BYPASS (Off)'}),
                'image_style_lora_4': (all_loras, {'default': 'None'}),
                'image_style_strength_4': ('FLOAT', {'default': 0.4, 'min': -4.0, 'max': 4.0, 'step': 0.05}),
                'enable_image_turbo_lora': ('BOOLEAN', {'default': True, 'label_on': '⚡ TURBO ON', 'label_off': '🔇 TURBO BYPASS (Off)'}),
                'image_turbo_lora': (all_loras, {'default': 'None'}),
                'image_turbo_strength': ('FLOAT', {'default': 0.9, 'min': 0.0, 'max': 2.5, 'step': 0.05}),
                'video_architecture': (list(VIDEO_BASE_MODELS), {'default': 'MiniMax H3'}),
                'video_unet_fl2va': (all_unets, {'default': 'None'}),
                'enable_video_lora_1': ('BOOLEAN', {'default': True, 'label_on': '🟢 ON (Active)', 'label_off': '🔇 BYPASS (Off)'}),
                'video_lora_1': (all_loras, {'default': 'None'}),
                'video_lora_1_strength': ('FLOAT', {'default': 0.6, 'min': -4.0, 'max': 4.0, 'step': 0.05}),
                'enable_video_lora_2': ('BOOLEAN', {'default': True, 'label_on': '🟢 ON (Active)', 'label_off': '🔇 BYPASS (Off)'}),
                'video_lora_2': (all_loras, {'default': 'None'}),
                'video_lora_2_strength': ('FLOAT', {'default': 0.5, 'min': -4.0, 'max': 4.0, 'step': 0.05}),
                'enable_video_lora_3': ('BOOLEAN', {'default': True, 'label_on': '🟢 ON (Active)', 'label_off': '🔇 BYPASS (Off)'}),
                'video_lora_3': (all_loras, {'default': 'None'}),
                'video_lora_3_strength': ('FLOAT', {'default': 0.4, 'min': -4.0, 'max': 4.0, 'step': 0.05}),
                'enable_video_lora_4': ('BOOLEAN', {'default': True, 'label_on': '🟢 ON (Active)', 'label_off': '🔇 BYPASS (Off)'}),
                'video_lora_4': (all_loras, {'default': 'None'}),
                'video_lora_4_strength': ('FLOAT', {'default': 0.35, 'min': -4.0, 'max': 4.0, 'step': 0.05}),
                'enable_video_turbo_lora': ('BOOLEAN', {'default': True, 'label_on': '⚡ TURBO ON', 'label_off': '🔇 TURBO BYPASS (Off)'}),
                'video_turbo_lora': (all_loras, {'default': 'None'}),
                'video_turbo_strength': ('FLOAT', {'default': 1.0, 'min': 0.0, 'max': 2.5, 'step': 0.05}),
                'trigger_words': ('STRING', {'default': '', 'multiline': False}),
                'active_recipe_name': (recipes, {'default': 'None'}),
                'auto_purge_30d_cache': ('BOOLEAN', {'default': True}),
            },
            'optional': {'cinematrix_bus': ('MINIMAX_GUIDE',)},
        }
    RETURN_TYPES = ('EZ_IMAGE_MODEL_SPEC', 'EZ_IMAGE_LORA_SPEC', 'EZ_VIDEO_MODEL_SPEC', 'EZ_VIDEO_LORA_SPEC', 'STRING', 'MINIMAX_GUIDE')
    RETURN_NAMES = ('image_model_spec', 'image_lora_spec', 'video_model_spec', 'video_lora_spec', 'trigger_words_prompt', 'cinematrix_bus')
    FUNCTION = 'run_civitai_controller'
    CATEGORY = 'EZ_Cinematrix_Core/00_Civitai_Controller'

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        return True

    @torch.inference_mode()
    def run_civitai_controller(self, controller_modality, civitai_domain, sort_by, time_period, image_architecture, image_unet_name, image_style_lora_1, image_style_strength_1, image_style_lora_2, image_style_strength_2, image_style_lora_3, image_style_strength_3, image_turbo_lora, image_turbo_strength, video_architecture, video_unet_fl2va, video_lora_1, video_lora_1_strength, video_lora_2, video_lora_2_strength, video_lora_3, video_lora_3_strength, video_turbo_lora, video_turbo_strength, image_style_lora_4='None', image_style_strength_4=0.4, enable_image_lora_1=True, enable_image_lora_2=True, enable_image_lora_3=True, enable_image_lora_4=True, enable_image_turbo_lora=True, video_lora_4='None', video_lora_4_strength=0.35, enable_video_lora_1=True, enable_video_lora_2=True, enable_video_lora_3=True, enable_video_lora_4=True, enable_video_turbo_lora=True, trigger_words='', active_recipe_name='None', auto_purge_30d_cache=True, cinematrix_bus=None):
        return EzCinematrixCivitaiControllerAdapter.execute_controller(controller_modality=controller_modality, civitai_domain=civitai_domain, sort_by=sort_by, time_period=time_period, image_architecture=image_architecture, image_unet_name=image_unet_name, image_style_lora_1=image_style_lora_1, image_style_strength_1=image_style_strength_1, image_style_lora_2=image_style_lora_2, image_style_strength_2=image_style_strength_2, image_style_lora_3=image_style_lora_3, image_style_strength_3=image_style_strength_3, image_turbo_lora=image_turbo_lora, image_turbo_strength=image_turbo_strength, video_architecture=video_architecture, video_unet_fl2va=video_unet_fl2va, video_lora_1=video_lora_1, video_lora_1_strength=video_lora_1_strength, video_lora_2=video_lora_2, video_lora_2_strength=video_lora_2_strength, video_lora_3=video_lora_3, video_lora_3_strength=video_lora_3_strength, video_turbo_lora=video_turbo_lora, video_turbo_strength=video_turbo_strength, image_style_lora_4=image_style_lora_4, image_style_strength_4=image_style_strength_4, enable_image_lora_1=enable_image_lora_1, enable_image_lora_2=enable_image_lora_2, enable_image_lora_3=enable_image_lora_3, enable_image_lora_4=enable_image_lora_4, enable_image_turbo_lora=enable_image_turbo_lora, video_lora_4=video_lora_4, video_lora_4_strength=video_lora_4_strength, enable_video_lora_1=enable_video_lora_1, enable_video_lora_2=enable_video_lora_2, enable_video_lora_3=enable_video_lora_3, enable_video_lora_4=enable_video_lora_4, enable_video_turbo_lora=enable_video_turbo_lora, trigger_words=trigger_words, active_recipe_name=active_recipe_name, auto_purge_30d_cache=auto_purge_30d_cache, cinematrix_bus=cinematrix_bus)
NODE_SUITE_VERSION = 'v1.0 Freemium'
NODE_CLASS_MAPPINGS = {'EZCinematrixCivitaiController': EZCinematrixCivitaiController}
NODE_DISPLAY_NAME_MAPPINGS = {'EZCinematrixCivitaiController': '🌐 EZ [10] Cinematrix Civitai Controller & Recipe Hub — Freemium v1.0'}
