# -*- coding: utf-8 -*-
from ..EZ_ENGINES.engine_ez_01_cinematrix_canvas_ingest import compute_cinematrix_dual_dimensions, execute_canvas_ingest_and_pad, _check_canvas_license_active, resolve_cinematrix_hardware_tier_profile, FIXED_ASPECT_RATIOS, RANDOM_ASPECT_RATIO_MODES, THERMAL_SHIELD_PRESETS

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

class EzCinematrixCanvasAdapter:
    """Adapter bridging dynamic aspect ratio math, outpaint padding, and Tier 1-4 hardware profiling."""

    @staticmethod
    def process(generation_mode: str, image_name: str, aspect_ratio: str, base_megapixels: float, final_megapixels: float, multiple: int, outpaint_align_pct: int, random_seed: int, seed_sync_mode: str='individual_per_node (Separate Seeds for [02], [04], [07])', hardware_tier: str='auto_from_devops_tier', thermal_protection_mode: str='auto_devops_shield', optional_image=None, ref_image_2_person=None, ref_image_3_clothing=None, ref_image_4_background=None, cinematrix_bus=None):
        bus = dict(cinematrix_bus) if isinstance(cinematrix_bus, dict) else {}
        eff_thermal = str(thermal_protection_mode or bus.get('thermal_protection_mode') or 'auto_devops_shield')
        tier_profile = resolve_cinematrix_hardware_tier_profile(hardware_tier, thermal_protection_mode=eff_thermal)
        (base_w, base_h, final_w, final_h, resolved_ratio) = compute_cinematrix_dual_dimensions(aspect_ratio, base_megapixels, final_megapixels, multiple, random_seed)
        is_i2i_mode = str(generation_mode or '').startswith('I2I')
        omni_b = bus.get('omni_reference_bundle') if isinstance(bus.get('omni_reference_bundle'), dict) else {}
        def _has_real_px(t):
            return isinstance(t, torch.Tensor) and t.numel() > 0 and float(t.detach().abs().max().item()) > 1e-04
        eff_opt_img = optional_image if _has_real_px(optional_image) else None
        clean_img_name = str(image_name or '').strip()
        has_disk_name = bool(clean_img_name and not clean_img_name.lower().startswith('none'))
        if is_i2i_mode and eff_opt_img is None and not has_disk_name and omni_b.get('active'):
            raw_s1 = omni_b.get('raw_slot1_fullres')
            master_comp = omni_b.get('master_composite_image')
            eff_opt_img = master_comp if _has_real_px(master_comp) else (raw_s1 if _has_real_px(raw_s1) else None)
        (canvas_img, outpaint_mask) = execute_canvas_ingest_and_pad(generation_mode, image_name, base_w, base_h, outpaint_align_pct, eff_opt_img)
        sync_all_active = str(seed_sync_mode or '').lower().startswith('sync_all')
        has_valid_img = is_i2i_mode and _has_real_px(canvas_img)
        if not is_i2i_mode and isinstance(bus.get('omni_reference_bundle'), dict):
            omni_copy = dict(bus['omni_reference_bundle'])
            omni_copy['master_composite_image'] = None
            omni_copy['raw_slot1_fullres'] = None
            omni_copy['clean_slot1_image'] = None
            omni_copy['has_image_slots'] = False
            omni_copy['has_inpaint_mask'] = False
            bus['omni_reference_bundle'] = omni_copy
        eff_r2 = ref_image_2_person if _has_real_px(ref_image_2_person) else (omni_b.get('slot2_person_image') if _has_real_px(omni_b.get('slot2_person_image')) else None)
        eff_r3 = ref_image_3_clothing if _has_real_px(ref_image_3_clothing) else (omni_b.get('slot3_clothing_image') if _has_real_px(omni_b.get('slot3_clothing_image')) else None)
        eff_r4 = ref_image_4_background if _has_real_px(ref_image_4_background) else (omni_b.get('slot4_background_image') if _has_real_px(omni_b.get('slot4_background_image')) else None)
        bus.update({'generation_mode': generation_mode, 'aspect_ratio': resolved_ratio, 'base_width': base_w, 'base_height': base_h, 'final_width': final_w, 'final_height': final_h, 'canvas_seed': int(random_seed), 'master_seed': int(random_seed), 'seed_sync_mode': str(seed_sync_mode), 'sync_all_seeds': bool(sync_all_active), 'hardware_tier': tier_profile['tier_id'], 'hardware_tier_profile': tier_profile, 'thermal_protection_mode': tier_profile.get('thermal_protection_mode', 'auto_devops_shield'), 'thermal_shield': tier_profile.get('thermal_shield', {}), 'has_source_image': bool(has_valid_img), 'ingest_image': canvas_img if has_valid_img else None, 'outpaint_mask': outpaint_mask if has_valid_img else None, 'ref_image_2_person': eff_r2, 'ref_image_3_clothing': eff_r3, 'ref_image_4_background': eff_r4})
        return (canvas_img, outpaint_mask, base_w, base_h, final_w, final_h, bus)
