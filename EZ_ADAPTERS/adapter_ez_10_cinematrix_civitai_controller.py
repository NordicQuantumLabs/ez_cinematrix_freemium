# -*- coding: utf-8 -*-
from ..EZ_ENGINES.engine_ez_10_cinematrix_civitai_controller import _get_suite_root, get_civitai_cache_dir, get_civitai_credentials_path, _get_asset_url_registry_path, load_asset_url_registry, register_asset_download_metadata, verify_civitai_license_status, load_civitai_api_key, save_civitai_api_key, purge_civitai_cache, classify_modality_from_metadata, inspect_safetensors_modality, _find_local_asset_full_path, ensure_civitai_asset_local, enforce_modality_lock, _normalize_arch_key, resolve_architecture_companions, download_architecture_companions, cache_civitai_media_thumbnail, _resolve_sort_label, _resolve_period_label, query_civitai_catalog, fetch_civitai_model_details, _get_recipes_file, load_civitai_recipes, save_civitai_recipe, delete_civitai_recipe, _find_sidecar_preview, scan_local_comfyui_assets, download_civitai_asset_to_comfyui, build_civitai_controller_specs, register_civitai_promptserver_routes, CACHE_TTL_DAYS, CACHE_TTL_SECONDS, IMAGE_BASE_MODELS, VIDEO_BASE_MODELS, CIVITAI_SORT_PRESETS, CIVITAI_PERIOD_PRESETS, CIVITAI_DOMAIN_PRESETS, CIVITAI_MODALITY_PRESETS, COMPANION_ARCH_PROFILES

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

class EzCinematrixCivitaiControllerAdapter:
    """Adapter routing strictly type-locked Image (KREA2/Flux/SDXL) and Video (MiniMax H3/Wan/LTXV) specs."""

    @staticmethod
    def execute_controller(controller_modality, civitai_domain, sort_by, time_period, image_architecture, image_unet_name, image_style_lora_1, image_style_strength_1, image_style_lora_2, image_style_strength_2, image_style_lora_3, image_style_strength_3, image_turbo_lora, image_turbo_strength, video_architecture, video_unet_fl2va, video_lora_1, video_lora_1_strength, video_lora_2, video_lora_2_strength, video_lora_3, video_lora_3_strength, video_turbo_lora, video_turbo_strength, image_style_lora_4='None', image_style_strength_4=0.4, enable_image_lora_1=True, enable_image_lora_2=True, enable_image_lora_3=True, enable_image_lora_4=True, enable_image_turbo_lora=True, video_lora_4='None', video_lora_4_strength=0.35, enable_video_lora_1=True, enable_video_lora_2=True, enable_video_lora_3=True, enable_video_lora_4=True, enable_video_turbo_lora=True, trigger_words='', active_recipe_name='None', auto_purge_30d_cache=True, cinematrix_bus=None):
        bus = dict(cinematrix_bus) if isinstance(cinematrix_bus, dict) else {}
        (img_m_spec, img_l_spec, vid_m_spec, vid_l_spec, trig_out) = build_civitai_controller_specs(controller_modality=controller_modality, civitai_domain=civitai_domain, sort_by=sort_by, time_period=time_period, image_architecture=image_architecture, image_unet_name=image_unet_name, image_style_lora_1=image_style_lora_1, image_style_strength_1=image_style_strength_1, image_style_lora_2=image_style_lora_2, image_style_strength_2=image_style_strength_2, image_style_lora_3=image_style_lora_3, image_style_strength_3=image_style_strength_3, image_turbo_lora=image_turbo_lora, image_turbo_strength=image_turbo_strength, video_architecture=video_architecture, video_unet_fl2va=video_unet_fl2va, video_lora_1=video_lora_1, video_lora_1_strength=video_lora_1_strength, video_lora_2=video_lora_2, video_lora_2_strength=video_lora_2_strength, video_lora_3=video_lora_3, video_lora_3_strength=video_lora_3_strength, video_turbo_lora=video_turbo_lora, video_turbo_strength=video_turbo_strength, image_style_lora_4=image_style_lora_4, image_style_strength_4=image_style_strength_4, enable_image_lora_1=enable_image_lora_1, enable_image_lora_2=enable_image_lora_2, enable_image_lora_3=enable_image_lora_3, enable_image_lora_4=enable_image_lora_4, enable_image_turbo_lora=enable_image_turbo_lora, video_lora_4=video_lora_4, video_lora_4_strength=video_lora_4_strength, enable_video_lora_1=enable_video_lora_1, enable_video_lora_2=enable_video_lora_2, enable_video_lora_3=enable_video_lora_3, enable_video_lora_4=enable_video_lora_4, enable_video_turbo_lora=enable_video_turbo_lora, trigger_words=trigger_words, active_recipe_name=active_recipe_name, auto_purge_30d_cache=auto_purge_30d_cache)
        act_img_l = [str(it[0]) for it in (img_l_spec.get('style_loras') or []) if isinstance(it, (list, tuple)) and len(it) >= 1 and str(it[0] or '').strip() not in ('', 'None')]
        act_vid_l = [str(it[0]) for it in (vid_l_spec.get('video_loras') or []) if isinstance(it, (list, tuple)) and len(it) >= 1 and str(it[0] or '').strip() not in ('', 'None')]
        if act_img_l or act_vid_l or str(img_m_spec.get('unet_name') or 'None') != 'None' or str(vid_m_spec.get('video_unet_fl2va') or 'None') != 'None':
            print(f"[EZ-10-HUB] ⚡ Aktiva val i [10] Recipe Hub -> Bild-LoRAs={act_img_l or 'Inga'} | Video-LoRAs={act_vid_l or 'Inga'} (OBS: [03]/[05] skyddar lokala val som standard via local_priority).")
        bus['civitai_image_model_spec'] = img_m_spec
        bus['civitai_image_lora_spec'] = img_l_spec
        bus['civitai_video_model_spec'] = vid_m_spec
        bus['civitai_video_lora_spec'] = vid_l_spec
        if trig_out:
            bus['civitai_trigger_words'] = trig_out
        return (img_m_spec, img_l_spec, vid_m_spec, vid_l_spec, trig_out, bus)
