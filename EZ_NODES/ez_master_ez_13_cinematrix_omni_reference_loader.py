# -*- coding: utf-8 -*-
from ..EZ_ADAPTERS.adapter_ez_13_cinematrix_omni_reference_loader import (
    EzCinematrixOmniReferenceLoaderAdapter,
    SLOT1_FOCUS_MODES,
    SLOT1_INPAINT_MODES,
    SLOT2_FOCUS_MODES,
    SLOT3_FOCUS_MODES,
    SLOT4_FOCUS_MODES,
    SLOT5_FOCUS_MODES,
    SLOT5_DURATION_MODES,
    list_comfy_input_images,
    list_comfy_input_videos,
)


class EZCinematrixOmniReferenceLoader:
    """EZ [13] Cinematrix Omni-Reference Load Image & Control Studio — Freemium v1.0.
    Unified 5-Slot Reference Image & Video Loader with dedicated headers (rubriker) and focused conditioning
    for Inpainting, IP-Adapter-Advanced + AnimateDiff/TemporalNet, ControlNet OpenPose/Canny/Lineart,
    ReActor Face-ID + ADetailer + AdvancedLivePortrait, OOTDiffusion + LayerDiffusion, DepthAnything/MiDaS,
    and 3D-VAE Latent Motion Capture Reference Video."""

    @classmethod
    def INPUT_TYPES(cls):
        input_files = list_comfy_input_images(include_none=True)
        video_files = list_comfy_input_videos(include_none=True)
        return {
            'required': {
                'rubrik_slot_1': (
                    ['═══ 🎯 [1] HUVUDBILD / INPAINT / POSE / CANNY / TEMPORALNET ═══'],
                    {'default': '═══ 🎯 [1] HUVUDBILD / INPAINT / POSE / CANNY / TEMPORALNET ═══'},
                ),
                'slot1_master_image': (input_files, {'image_upload': True}),
                'slot1_focus_mode': (SLOT1_FOCUS_MODES, {'default': SLOT1_FOCUS_MODES[0]}),
                'slot1_strength': ('FLOAT', {'default': 1.0, 'min': 0.0, 'max': 2.0, 'step': 0.05}),
                'slot1_inpaint_mask_mode': (SLOT1_INPAINT_MODES, {'default': SLOT1_INPAINT_MODES[0]}),
                'slot1_feather_radius': ('FLOAT', {'default': 12.0, 'min': 0.0, 'max': 64.0, 'step': 1.0}),
                'rubrik_slot_2': (
                    ['═══ 👤 [2] PERSON / REACTOR FACE-ID / ADETAILER / LIVEPORTRAIT ═══'],
                    {'default': '═══ 👤 [2] PERSON / REACTOR FACE-ID / ADETAILER / LIVEPORTRAIT ═══'},
                ),
                'slot2_person_image': (input_files, {'default': 'None'}),
                'slot2_focus_mode': (SLOT2_FOCUS_MODES, {'default': SLOT2_FOCUS_MODES[0]}),
                'slot2_identity_strength': ('FLOAT', {'default': 1.0, 'min': 0.0, 'max': 2.0, 'step': 0.05}),
                'slot2_adetailer_denoise': ('FLOAT', {'default': 0.32, 'min': 0.05, 'max': 0.85, 'step': 0.01}),
                'rubrik_slot_3': (
                    ['═══ 👗 [3] KLÄDER / OOTDIFFUSION / LAYERDIFFUSION GARMENT ═══'],
                    {'default': '═══ 👗 [3] KLÄDER / OOTDIFFUSION / LAYERDIFFUSION GARMENT ═══'},
                ),
                'slot3_clothing_image': (input_files, {'default': 'None'}),
                'slot3_focus_mode': (SLOT3_FOCUS_MODES, {'default': SLOT3_FOCUS_MODES[0]}),
                'slot3_ootd_strength': ('FLOAT', {'default': 0.95, 'min': 0.0, 'max': 2.0, 'step': 0.05}),
                'slot3_preserve_neck_and_hands': ('BOOLEAN', {'default': True}),
                'rubrik_slot_4': (
                    ['═══ 🌆 [4] BAKGRUND / DEPTH-ANYTHING / MIDAS / CONTROLNET TILE ═══'],
                    {'default': '═══ 🌆 [4] BAKGRUND / DEPTH-ANYTHING / MIDAS / CONTROLNET TILE ═══'},
                ),
                'slot4_background_image': (input_files, {'default': 'None'}),
                'slot4_focus_mode': (SLOT4_FOCUS_MODES, {'default': SLOT4_FOCUS_MODES[0]}),
                'slot4_depth_and_tile_strength': ('FLOAT', {'default': 0.90, 'min': 0.0, 'max': 2.0, 'step': 0.05}),
                'slot4_horizon_relight_match': ('FLOAT', {'default': 0.55, 'min': 0.0, 'max': 1.0, 'step': 0.05}),
                'rubrik_slot_5': (
                    ['═══ 🎬 [5] REFERENSVIDEO / MOTION CAPTURE & KINETIC GUIDE ═══'],
                    {'default': '═══ 🎬 [5] REFERENSVIDEO / MOTION CAPTURE & KINETIC GUIDE ═══'},
                ),
                'slot5_reference_video': (video_files, {'default': 'None', 'tooltip': 'Välj en referensvideo (.mp4, .mkv, .webp, .mov, .webm, .gif) från ComfyUI/input eller ComfyUI/output för att styra karaktärens rörelser (MoCap). Skickas automatiskt via cinematrix_bus till EZ [06]!'}),
                'slot5_start_offset_sec': ('FLOAT', {'default': 0.0, 'min': 0.0, 'max': 600.0, 'step': 0.5, 'tooltip': 'Startposition i sekunder (Start Offset) i referensvideon (.mp4, .mkv, .webp) varifrån rörelse och ljud läses in (likt Suno-nodens start offset).'}),
                'slot5_duration_mode': (SLOT5_DURATION_MODES, {'default': SLOT5_DURATION_MODES[0], 'tooltip': 'Styr hur lång tid (i sekunder) som läses in från referensvideon. Standard: Följ Master-Tidslängd [02] / [06] automatiskt!'}),
                'slot5_duration_seconds': ('FLOAT', {'default': 0.0, 'min': 0.0, 'max': 600.0, 'step': 0.5, 'tooltip': '0.0 = Följ Master-Tidslängd [02] / [06] automatiskt! Ange sekunder (>0) om du vill styra referensklippets längd manuellt i sekunder istället för bildrutor.'}),
                'slot5_focus_mode': (SLOT5_FOCUS_MODES, {'default': SLOT5_FOCUS_MODES[0]}),
                'slot5_motion_strength': ('FLOAT', {'default': 0.65, 'min': 0.0, 'max': 1.5, 'step': 0.05, 'tooltip': 'Styr hur starkt referensvideon driver 5D-rörelsevektorerna i EZ [06] & EZ [07].'}),
                'target_width': ('INT', {'default': 1248, 'min': 256, 'max': 4096, 'step': 16}),
                'target_height': ('INT', {'default': 832, 'min': 256, 'max': 4096, 'step': 16}),
            },
            'optional': {
                'opt_slot1_image': ('IMAGE',),
                'opt_slot1_mask': ('MASK',),
                'opt_slot2_person': ('IMAGE',),
                'opt_slot3_clothing': ('IMAGE',),
                'opt_slot4_background': ('IMAGE',),
                'opt_slot5_video': ('IMAGE',),
                'cinematrix_bus': ('MINIMAX_GUIDE',),
            },
        }

    RETURN_TYPES = ('IMAGE', 'MASK', 'IMAGE', 'IMAGE', 'IMAGE', 'IMAGE', 'MINIMAX_GUIDE', 'IMAGE')
    RETURN_NAMES = (
        'master_composite_image',
        'inpaint_mask',
        'person_reactor_image',
        'clothing_ootd_image',
        'background_depth_image',
        'control_maps_preview',
        'cinematrix_bus',
        'reference_motion_video',
    )
    FUNCTION = 'execute'
    CATEGORY = 'EZ_Cinematrix_Core/13_Omni_Reference'

    def execute(
        self,
        rubrik_slot_1,
        slot1_master_image,
        slot1_focus_mode,
        slot1_strength,
        slot1_inpaint_mask_mode,
        slot1_feather_radius,
        rubrik_slot_2,
        slot2_person_image,
        slot2_focus_mode,
        slot2_identity_strength,
        slot2_adetailer_denoise,
        rubrik_slot_3,
        slot3_clothing_image,
        slot3_focus_mode,
        slot3_ootd_strength,
        slot3_preserve_neck_and_hands,
        rubrik_slot_4,
        slot4_background_image,
        slot4_focus_mode,
        slot4_depth_and_tile_strength,
        slot4_horizon_relight_match,
        rubrik_slot_5='═══ 🎬 [5] REFERENSVIDEO / MOTION CAPTURE & KINETIC GUIDE ═══',
        slot5_reference_video='None',
        slot5_start_offset_sec=0.0,
        slot5_duration_mode=SLOT5_DURATION_MODES[0],
        slot5_duration_seconds=0.0,
        slot5_focus_mode=SLOT5_FOCUS_MODES[0],
        slot5_motion_strength=0.65,
        slot5_max_frames=0,
        target_width=1248,
        target_height=832,
        opt_slot1_image=None,
        opt_slot1_mask=None,
        opt_slot2_person=None,
        opt_slot3_clothing=None,
        opt_slot4_background=None,
        opt_slot5_video=None,
        cinematrix_bus=None,
    ):
        return EzCinematrixOmniReferenceLoaderAdapter.run_omni_reference_studio(
            rubrik_slot_1=rubrik_slot_1,
            slot1_master_image=slot1_master_image,
            slot1_focus_mode=slot1_focus_mode,
            slot1_strength=slot1_strength,
            slot1_inpaint_mask_mode=slot1_inpaint_mask_mode,
            slot1_feather_radius=slot1_feather_radius,
            rubrik_slot_2=rubrik_slot_2,
            slot2_person_image=slot2_person_image,
            slot2_focus_mode=slot2_focus_mode,
            slot2_identity_strength=slot2_identity_strength,
            slot2_adetailer_denoise=slot2_adetailer_denoise,
            rubrik_slot_3=rubrik_slot_3,
            slot3_clothing_image=slot3_clothing_image,
            slot3_focus_mode=slot3_focus_mode,
            slot3_ootd_strength=slot3_ootd_strength,
            slot3_preserve_neck_and_hands=slot3_preserve_neck_and_hands,
            rubrik_slot_4=rubrik_slot_4,
            slot4_background_image=slot4_background_image,
            slot4_focus_mode=slot4_focus_mode,
            slot4_depth_and_tile_strength=slot4_depth_and_tile_strength,
            slot4_horizon_relight_match=slot4_horizon_relight_match,
            rubrik_slot_5=rubrik_slot_5,
            slot5_reference_video=slot5_reference_video,
            slot5_start_offset_sec=slot5_start_offset_sec,
            slot5_duration_mode=slot5_duration_mode,
            slot5_duration_seconds=slot5_duration_seconds,
            slot5_focus_mode=slot5_focus_mode,
            slot5_motion_strength=slot5_motion_strength,
            slot5_max_frames=slot5_max_frames,
            target_width=target_width,
            target_height=target_height,
            opt_slot1_image=opt_slot1_image,
            opt_slot1_mask=opt_slot1_mask,
            opt_slot2_person=opt_slot2_person,
            opt_slot3_clothing=opt_slot3_clothing,
            opt_slot4_background=opt_slot4_background,
            opt_slot5_video=opt_slot5_video,
            cinematrix_bus=cinematrix_bus,
        )


NODE_SUITE_VERSION = 'v1.0 Freemium'
NODE_CLASS_MAPPINGS = {
    'EZCinematrixOmniReferenceLoader': EZCinematrixOmniReferenceLoader,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    'EZCinematrixOmniReferenceLoader': '🖼️ EZ [13] Cinematrix Omni-Reference Load Image & Control Studio — Freemium v1.0',
}
