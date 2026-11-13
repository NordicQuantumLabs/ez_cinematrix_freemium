# -*- coding: utf-8 -*-
from ..EZ_ENGINES.engine_ez_09_cinematrix_anatomy_dock import _dock_blur_2d, build_anatomy_dock_payload
from ..EZ_ADAPTERS.adapter_ez_09_cinematrix_anatomy_dock import EzCinematrixAnatomyDockAdapter

import math
import torch
import comfy.model_management

class EZCinematrixNeuralAnatomyContinuityDock:
    """🧭 [OPTIONAL VIDEO ANATOMY DOCK] Plug anatomy_dock into EZ [07] / EZ [08] to control video-frame skeletal tracking and temporal continuity."""

    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'autopilot_mode': (['auto_self_driving (Recommended)', 'manual_surgical_override'], {'default': 'auto_self_driving (Recommended)'}), 'lock_face_and_eyes': ('FLOAT', {'default': 1.0, 'min': 0.0, 'max': 2.0, 'step': 0.05}), 'lock_hands_and_fingers': ('FLOAT', {'default': 1.25, 'min': 0.0, 'max': 2.0, 'step': 0.05}), 'lock_torso_and_breasts': ('FLOAT', {'default': 1.1, 'min': 0.0, 'max': 2.0, 'step': 0.05}), 'lock_intimate_pelvic_anatomy': ('FLOAT', {'default': 1.35, 'min': 0.0, 'max': 2.0, 'step': 0.05}), 'lock_feet_and_toes': ('FLOAT', {'default': 1.15, 'min': 0.0, 'max': 2.0, 'step': 0.05}), 'eye_and_contour_sharpness_shield': ('FLOAT', {'default': 0.9, 'min': 0.0, 'max': 1.0, 'step': 0.05}), 'latent_outlier_suppression': ('FLOAT', {'default': 0.0, 'min': 0.0, 'max': 0.85, 'step': 0.05}), 'temporal_identity_rigidity': ('FLOAT', {'default': 0.85, 'min': 0.0, 'max': 1.0, 'step': 0.05}), 'mask_feather_radius': ('FLOAT', {'default': 10.0, 'min': 1.0, 'max': 48.0, 'step': 0.5}), 'detection_sensitivity': ('FLOAT', {'default': 0.45, 'min': 0.1, 'max': 0.9, 'step': 0.05}), 'reference_face_lock_strength': ('FLOAT', {'default': 0.78, 'min': 0.0, 'max': 1.0, 'step': 0.05})}, 'optional': {'inspect_image': ('IMAGE',), 'cinematrix_bus': ('MINIMAX_GUIDE',)}}
    RETURN_TYPES = ('ANATOMY_DOCK', 'IMAGE', 'MASK', 'MINIMAX_GUIDE')
    RETURN_NAMES = ('anatomy_dock', 'anatomy_mask_preview', 'combined_anatomy_mask', 'cinematrix_bus')
    FUNCTION = 'configure_dock'
    CATEGORY = 'EZ_Cinematrix_Core/09_Anatomy_Dock'

    @torch.inference_mode()
    def configure_dock(self, autopilot_mode='auto_self_driving (Recommended)', lock_face_and_eyes=1.0, lock_hands_and_fingers=1.25, lock_torso_and_breasts=1.1, lock_intimate_pelvic_anatomy=1.35, lock_feet_and_toes=1.15, eye_and_contour_sharpness_shield=0.9, latent_outlier_suppression=0.0, temporal_identity_rigidity=0.85, mask_feather_radius=10.0, detection_sensitivity=0.45, reference_face_lock_strength=0.78, inspect_image=None, cinematrix_bus=None):
        return EzCinematrixAnatomyDockAdapter.execute_dock(autopilot_mode=autopilot_mode, lock_face_and_eyes=lock_face_and_eyes, lock_hands_and_fingers=lock_hands_and_fingers, lock_torso_and_breasts=lock_torso_and_breasts, lock_intimate_pelvic_anatomy=lock_intimate_pelvic_anatomy, lock_feet_and_toes=lock_feet_and_toes, eye_and_contour_sharpness_shield=eye_and_contour_sharpness_shield, latent_outlier_suppression=latent_outlier_suppression, temporal_identity_rigidity=temporal_identity_rigidity, mask_feather_radius=mask_feather_radius, detection_sensitivity=detection_sensitivity, reference_face_lock_strength=reference_face_lock_strength, inspect_image=inspect_image, cinematrix_bus=cinematrix_bus)
NODE_SUITE_VERSION = 'v1.0 Freemium'
NODE_CLASS_MAPPINGS = {'EZCinematrixNeuralAnatomyContinuityDock': EZCinematrixNeuralAnatomyContinuityDock}
NODE_DISPLAY_NAME_MAPPINGS = {'EZCinematrixNeuralAnatomyContinuityDock': '🧭 EZ [09] Cinematrix Neural Anatomy & Continuity Dock (Optional) — Freemium v1.0'}
