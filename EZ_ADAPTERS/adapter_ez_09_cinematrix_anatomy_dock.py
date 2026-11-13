# -*- coding: utf-8 -*-
from ..EZ_ENGINES.engine_ez_09_cinematrix_anatomy_dock import _dock_blur_2d, build_anatomy_dock_payload

import math
import torch
import comfy.model_management

class EzCinematrixAnatomyDockAdapter:
    """Adapter packaging optional surgical overrides for the Neural Anatomy & Continuity Engine across EZ [04], [07], and [08]."""

    @staticmethod
    def execute_dock(autopilot_mode, lock_face_and_eyes, lock_hands_and_fingers, lock_torso_and_breasts, lock_intimate_pelvic_anatomy, lock_feet_and_toes, eye_and_contour_sharpness_shield, latent_outlier_suppression, temporal_identity_rigidity, mask_feather_radius, detection_sensitivity, reference_face_lock_strength=0.78, inspect_image=None, cinematrix_bus=None):
        bus = dict(cinematrix_bus) if isinstance(cinematrix_bus, dict) else {}
        eff_img = inspect_image if isinstance(inspect_image, torch.Tensor) else None
        (dock_payload, prev_img, comb_mask) = build_anatomy_dock_payload(autopilot_mode=autopilot_mode, lock_face_and_eyes=lock_face_and_eyes, lock_hands_and_fingers=lock_hands_and_fingers, lock_torso_and_breasts=lock_torso_and_breasts, lock_intimate_pelvic_anatomy=lock_intimate_pelvic_anatomy, lock_feet_and_toes=lock_feet_and_toes, eye_and_contour_sharpness_shield=eye_and_contour_sharpness_shield, latent_outlier_suppression=latent_outlier_suppression, temporal_identity_rigidity=temporal_identity_rigidity, mask_feather_radius=mask_feather_radius, detection_sensitivity=detection_sensitivity, reference_face_lock_strength=reference_face_lock_strength, inspect_image=eff_img)
        bus['anatomy_dock'] = dock_payload
        return (dock_payload, prev_img, comb_mask, bus)

