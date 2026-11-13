# -*- coding: utf-8 -*-
from ..EZ_ENGINES.engine_ez_01_cinematrix_canvas_ingest import compute_cinematrix_dual_dimensions, execute_canvas_ingest_and_pad, _check_canvas_license_active, resolve_cinematrix_hardware_tier_profile, FIXED_ASPECT_RATIOS, RANDOM_ASPECT_RATIO_MODES, THERMAL_SHIELD_PRESETS
from ..EZ_ADAPTERS.adapter_ez_01_cinematrix_canvas_ingest import EzCinematrixCanvasAdapter

import math
import os
import random
import gc
from pathlib import Path
import torch
import numpy as np
from PIL import Image, ImageOps
import folder_paths
import comfy.model_management
import comfy.utils

class EZCinematrixCanvasIngest:
    """🎬 [ZONE 1] Unified T2I/I2I Canvas Ingest, Dual-Megapixel Selector, Outpaint Extender & Tier 1-4 Optimizer."""

    @classmethod
    def INPUT_TYPES(cls):
        input_dir = folder_paths.get_input_directory()
        files = []
        if os.path.exists(input_dir):
            for (r_dir, sub_dirs, f_list) in os.walk(input_dir):
                sub_dirs[:] = [d for d in sub_dirs if not d.startswith('.') and d.lower() not in ('3d', '__pycache__')]
                for f in f_list:
                    if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif')):
                        files.append(os.path.relpath(os.path.join(r_dir, f), input_dir).replace('\\', '/'))
        image_choices = ['None'] + sorted(set(files))
        ratio_choices = list(RANDOM_ASPECT_RATIO_MODES.keys()) + list(FIXED_ASPECT_RATIOS.keys())
        seed_sync_choices = ['individual_per_node (Separate Seeds for [02], [04], [07])', 'sync_all_to_master_seed (Lock [02] + [04] + [07] to [01])']
        tier_choices = ['auto_from_devops_tier', 'tier_1_rtx5070ti_16gb', 'tier_2_rtx5090_32gb', 'tier_3_rtx6000ada_48gb', 'tier_4_nvlink_cluster_80gb']
        return {'required': {'generation_mode': (['T2I (Empty Canvas)', 'I2I / I2V (Use Source Image)'], {'default': 'T2I (Empty Canvas)'}), 'source_image': (image_choices, {'default': image_choices[0], 'image_upload': True}), 'aspect_ratio': (ratio_choices, {'default': '3:2'}), 'base_megapixels': ('FLOAT', {'default': 1.0, 'min': 0.2, 'max': 8.0, 'step': 0.1}), 'final_megapixels': ('FLOAT', {'default': 3.0, 'min': 0.5, 'max': 16.0, 'step': 0.1}), 'multiple': ('INT', {'default': 16, 'min': 8, 'max': 64, 'step': 8}), 'outpaint_align_pct': ('INT', {'default': 50, 'min': 0, 'max': 100, 'step': 1}), 'random_seed': ('INT', {'default': 860481191328700, 'min': 0, 'max': 9007199254740991, 'step': 1, 'control_after_generate': True}), 'seed_sync_mode': (seed_sync_choices, {'default': seed_sync_choices[0]}), 'hardware_tier': (tier_choices, {'default': 'auto_from_devops_tier'})}, 'optional': {'thermal_protection_mode': (THERMAL_SHIELD_PRESETS, {'default': THERMAL_SHIELD_PRESETS[0], 'tooltip': 'DEVOPS VÄRME- & EFFEKTSKYDD (Thermal Sentinel Shield): Låser GPU/CPU-temperaturer och lägger in automatiska kylpauser + trådbroms under tunga Krea 2 [04], MiniMax [07] och Vault [08]-körningar så att datorn aldrig överhettas eller kraschar.'}), 'optional_image': ('IMAGE',), 'ref_image_2_person': ('IMAGE',), 'ref_image_3_clothing': ('IMAGE',), 'ref_image_4_background': ('IMAGE',), 'cinematrix_bus': ('MINIMAX_GUIDE',)}}
    RETURN_TYPES = ('IMAGE', 'MASK', 'INT', 'INT', 'INT', 'INT', 'MINIMAX_GUIDE')
    RETURN_NAMES = ('image', 'mask', 'base_width', 'base_height', 'final_width', 'final_height', 'cinematrix_bus')
    FUNCTION = 'execute_ingest'
    CATEGORY = 'EZ_Cinematrix_Core/01_Ingest'

    @torch.inference_mode()
    def execute_ingest(self, generation_mode, source_image, aspect_ratio, base_megapixels, final_megapixels, multiple, outpaint_align_pct, random_seed, seed_sync_mode='individual_per_node (Separate Seeds for [02], [04], [07])', hardware_tier='auto_from_devops_tier', thermal_protection_mode='auto_devops_shield (Auto DevOps Skydd — GPU 78°C / CPU 85°C + Smart Kylpaus)', optional_image=None, ref_image_2_person=None, ref_image_3_clothing=None, ref_image_4_background=None, cinematrix_bus=None):
        return EzCinematrixCanvasAdapter.process(generation_mode=generation_mode, image_name=source_image, aspect_ratio=aspect_ratio, base_megapixels=base_megapixels, final_megapixels=final_megapixels, multiple=multiple, outpaint_align_pct=outpaint_align_pct, random_seed=random_seed, seed_sync_mode=seed_sync_mode, hardware_tier=hardware_tier, thermal_protection_mode=thermal_protection_mode, optional_image=optional_image, ref_image_2_person=ref_image_2_person, ref_image_3_clothing=ref_image_3_clothing, ref_image_4_background=ref_image_4_background, cinematrix_bus=cinematrix_bus)
NODE_SUITE_VERSION = 'v1.0 Freemium'
NODE_CLASS_MAPPINGS = {'EZCinematrixCanvasIngest': EZCinematrixCanvasIngest}
NODE_DISPLAY_NAME_MAPPINGS = {'EZCinematrixCanvasIngest': '🎬 EZ [01] Cinematrix Canvas & Dual-Resolution Ingest — Freemium v1.0'}

