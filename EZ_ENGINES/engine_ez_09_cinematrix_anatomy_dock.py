# -*- coding: utf-8 -*-

import math
import torch
import comfy.model_management

def _dock_blur_2d(tensor_bchw: torch.Tensor, radius: float) -> torch.Tensor:
    if radius <= 0.05:
        return tensor_bchw.clone()
    import torch.nn.functional as F
    k_size = max(3, int(2 * int(3.0 * float(radius) + 0.5) + 1))
    sigma = max(0.1, float(radius))
    coords = torch.arange(k_size, dtype=tensor_bchw.dtype, device=tensor_bchw.device) - (k_size - 1) * 0.5
    k_1d = torch.exp(-coords ** 2 / (2.0 * sigma * sigma))
    k_1d = k_1d / k_1d.sum()
    k_2d = (k_1d[:, None] * k_1d[None, :]).expand(tensor_bchw.shape[1], 1, k_size, k_size).contiguous()
    pad = k_size // 2
    padded = F.pad(tensor_bchw, (pad, pad, pad, pad), mode='reflect')
    return F.conv2d(padded, k_2d, groups=tensor_bchw.shape[1])

def build_anatomy_dock_payload(autopilot_mode: str, lock_face_and_eyes: float, lock_hands_and_fingers: float, lock_torso_and_breasts: float, lock_intimate_pelvic_anatomy: float, lock_feet_and_toes: float, eye_and_contour_sharpness_shield: float, latent_outlier_suppression: float, temporal_identity_rigidity: float, mask_feather_radius: float, detection_sensitivity: float, reference_face_lock_strength: float=0.78, inspect_image=None):
    mode_low = str(autopilot_mode or '').strip().lower()
    is_disabled = mode_low.startswith(('off', 'disable', 'bypass'))
    w_face = 0.0 if is_disabled else max(0.0, float(lock_face_and_eyes))
    w_hands = 0.0 if is_disabled else max(0.0, float(lock_hands_and_fingers))
    w_torso = 0.0 if is_disabled else max(0.0, float(lock_torso_and_breasts))
    w_pelvic = 0.0 if is_disabled else max(0.0, float(lock_intimate_pelvic_anatomy))
    w_feet = 0.0 if is_disabled else max(0.0, float(lock_feet_and_toes))
    w_sharp = 0.0 if is_disabled else max(0.0, float(eye_and_contour_sharpness_shield))
    w_outlier = 0.0 if is_disabled else max(0.0, float(latent_outlier_suppression))
    w_rigid = 0.0 if is_disabled else max(0.0, float(temporal_identity_rigidity))
    w_feather = max(0.0, float(mask_feather_radius))
    w_sens = max(0.05, min(0.95, float(detection_sensitivity)))
    w_ref_lock = 0.0 if is_disabled else max(0.0, min(1.0, float(reference_face_lock_strength)))
    dock_payload = {
        'active': not is_disabled,
        'autopilot_mode': str(autopilot_mode),
        'use_keypoint_detector': not is_disabled,
        'lock_face_and_eyes': w_face,
        'lock_hands_and_fingers': w_hands,
        'lock_torso_and_breasts': w_torso,
        'lock_intimate_pelvic_anatomy': w_pelvic,
        'lock_feet_and_toes': w_feet,
        'eye_and_contour_sharpness_shield': w_sharp,
        'latent_outlier_suppression': w_outlier,
        'temporal_identity_rigidity': w_rigid,
        'mask_feather_radius': w_feather,
        'detection_sensitivity': w_sens,
        'reference_face_lock_strength': w_ref_lock,
    }
    if not isinstance(inspect_image, torch.Tensor) or inspect_image.ndim != 4 or float(inspect_image.detach().abs().max().item()) <= 1e-04:
        empty_prev = torch.zeros((1, 256, 256, 3), dtype=torch.float32)
        empty_mask = torch.zeros((1, 256, 256), dtype=torch.float32)
        return (dock_payload, empty_prev, empty_mask)
    from .engine_ez_04_cinematrix_krea2_sampler import _compute_neural_anatomy_zones, _render_anatomy_preview_bhwc
    dev = comfy.model_management.get_torch_device() if torch.cuda.is_available() else torch.device('cpu')
    sub = inspect_image[:1].to(device=dev, dtype=torch.float32)
    bchw = sub.permute(0, 3, 1, 2).contiguous()
    zones = _compute_neural_anatomy_zones(bchw, dock_cfg=dock_payload)
    weighted_zones = dict(zones)
    weighted_zones['face'] = torch.clamp(zones['face'] * (w_face / 1.0), 0.0, 1.0)
    weighted_zones['torso'] = torch.clamp(zones['torso'] * (w_torso / 1.1), 0.0, 1.0)
    weighted_zones['pelvic'] = torch.clamp(zones['pelvic'] * (w_pelvic / 1.35), 0.0, 1.0)
    weighted_zones['hands'] = torch.clamp(zones['hands'] * (w_hands / 1.25), 0.0, 1.0)
    weighted_zones['feet'] = torch.clamp(zones['feet'] * (w_feet / 1.15), 0.0, 1.0)
    preview_bhwc = _render_anatomy_preview_bhwc(bchw, weighted_zones)
    raw_union = weighted_zones['face'] + weighted_zones['torso'] + weighted_zones['pelvic'] + weighted_zones['hands'] + weighted_zones['feet']
    if w_feather > 0.5:
        raw_union = _dock_blur_2d(torch.clamp(raw_union, 0.0, 1.0), w_feather * 0.15)
    union_mask = torch.clamp(raw_union.squeeze(1).detach().cpu(), 0.0, 1.0)
    del sub, bchw, zones, weighted_zones
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return (dock_payload, preview_bhwc, union_mask)

