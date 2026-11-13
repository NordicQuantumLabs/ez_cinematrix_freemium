# -*- coding: utf-8 -*-
import torch
from ..EZ_ENGINES.engine_ez_01_cinematrix_canvas_ingest import THERMAL_SHIELD_PRESETS
from ..EZ_ENGINES.engine_ez_14_cinematrix_pipeline_switchboard import (
    PIPELINE_EXECUTION_MODE_CHOICES,
    BYPASS_BEHAVIOR_CHOICES,
)
from ..EZ_ADAPTERS.adapter_ez_14_cinematrix_pipeline_switchboard import (
    EzCinematrixPipelineSwitchboardAdapter,
)


class EZCinematrixPipelineSwitchboard:
    """🎛️ [ZONE 14] Native Fast Bypass Remote Control & Pipeline Switchboard (Image Only / Full Studio / Video Only + Module Toggles)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "pipeline_execution_mode": (
                    PIPELINE_EXECUTION_MODE_CHOICES,
                    {"default": PIPELINE_EXECUTION_MODE_CHOICES[0]},
                ),
                "enable_qwenvl_compiler_02": ("BOOLEAN", {"default": True}),
                "enable_krea2_image_03_04": ("BOOLEAN", {"default": True}),
                "enable_minimax_video_05_08": ("BOOLEAN", {"default": True}),
                "enable_suno_music_12": ("BOOLEAN", {"default": True}),
                "enable_omni_reference_13": ("BOOLEAN", {"default": True}),
                "enable_anatomy_dock_09": ("BOOLEAN", {"default": True}),
                "bypass_behavior": (
                    BYPASS_BEHAVIOR_CHOICES,
                    {"default": BYPASS_BEHAVIOR_CHOICES[0]},
                ),
            },
            "optional": {
                "thermal_protection_mode": (
                    THERMAL_SHIELD_PRESETS,
                    {
                        "default": THERMAL_SHIELD_PRESETS[0],
                        "tooltip": "DEVOPS VÄRME- & EFFEKTSKYDD (Thermal Sentinel Shield): Styr aktiv temperaturgräns (GPU/CPU), mellanstegspaus och CPU-trådbroms för hela kedjan [01]->[08].",
                    },
                ),
                "cinematrix_bus": ("MINIMAX_GUIDE",),
            },
        }

    RETURN_TYPES = ("MINIMAX_GUIDE", "STRING")
    RETURN_NAMES = ("cinematrix_bus", "switchboard_status_summary")
    FUNCTION = "run_pipeline_switchboard"
    OUTPUT_NODE = False
    CATEGORY = "EZ_Cinematrix_Core/14_Pipeline_Switchboard"

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        return True

    @torch.inference_mode()
    def run_pipeline_switchboard(
        self,
        pipeline_execution_mode,
        enable_qwenvl_compiler_02=True,
        enable_krea2_image_03_04=True,
        enable_minimax_video_05_08=True,
        enable_suno_music_12=True,
        enable_omni_reference_13=True,
        enable_anatomy_dock_09=True,
        bypass_behavior="bypass_mode_4 (ComfyUI Bypass — Skicka data genom noden, 0s / 0 VRAM)",
        thermal_protection_mode="auto_devops_shield (Auto DevOps Skydd — GPU 78°C / CPU 85°C + Smart Kylpaus)",
        cinematrix_bus=None,
    ):
        return EzCinematrixPipelineSwitchboardAdapter.execute_switchboard(
            pipeline_execution_mode=pipeline_execution_mode,
            enable_qwenvl_compiler_02=enable_qwenvl_compiler_02,
            enable_krea2_image_03_04=enable_krea2_image_03_04,
            enable_minimax_video_05_08=enable_minimax_video_05_08,
            enable_suno_music_12=enable_suno_music_12,
            enable_omni_reference_13=enable_omni_reference_13,
            enable_anatomy_dock_09=enable_anatomy_dock_09,
            bypass_behavior=bypass_behavior,
            thermal_protection_mode=thermal_protection_mode,
            cinematrix_bus=cinematrix_bus,
        )


NODE_SUITE_VERSION = 'v1.0 Freemium'
NODE_CLASS_MAPPINGS = {"EZCinematrixPipelineSwitchboard": EZCinematrixPipelineSwitchboard}
NODE_DISPLAY_NAME_MAPPINGS = {
    "EZCinematrixPipelineSwitchboard": "🎛️ EZ [14] Cinematrix Pipeline Switchboard & Fast Bypass — Freemium v1.0"
}

