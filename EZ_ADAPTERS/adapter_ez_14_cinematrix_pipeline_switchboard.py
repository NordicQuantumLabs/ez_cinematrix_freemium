# -*- coding: utf-8 -*-
from ..EZ_ENGINES.engine_ez_14_cinematrix_pipeline_switchboard import (
    PIPELINE_EXECUTION_MODE_CHOICES,
    BYPASS_BEHAVIOR_CHOICES,
    SWITCHBOARD_TARGET_NODE_GROUPS,
    resolve_switchboard_execution_flags,
    compile_pipeline_switchboard_state,
)


class EzCinematrixPipelineSwitchboardAdapter:
    """Adapter for EZ [14] Cinematrix Pipeline Switchboard & Fast Bypass Remote Control."""

    @staticmethod
    def execute_switchboard(
        pipeline_execution_mode: str,
        enable_qwenvl_compiler_02: bool = True,
        enable_krea2_image_03_04: bool = True,
        enable_minimax_video_05_08: bool = True,
        enable_suno_music_12: bool = True,
        enable_omni_reference_13: bool = True,
        enable_anatomy_dock_09: bool = True,
        bypass_behavior: str = "bypass_mode_4 (ComfyUI Bypass — Skicka data genom noden, 0s / 0 VRAM)",
        thermal_protection_mode: str = "auto_devops_shield (Auto DevOps Skydd — GPU 78°C / CPU 85°C + Smart Kylpaus)",
        cinematrix_bus=None,
    ):
        updated_bus, summary, ui_payload = compile_pipeline_switchboard_state(
            pipeline_execution_mode=pipeline_execution_mode,
            enable_qwenvl_compiler_02=enable_qwenvl_compiler_02,
            enable_krea2_image_03_04=enable_krea2_image_03_04,
            enable_minimax_video_05_08=enable_minimax_video_05_08,
            enable_suno_music_12=enable_suno_music_12,
            enable_omni_reference_13=enable_omni_reference_13,
            enable_anatomy_dock_09=enable_anatomy_dock_09,
            bypass_behavior=bypass_behavior,
            thermal_protection_mode=thermal_protection_mode,
            cinematrix_bus=cinematrix_bus if isinstance(cinematrix_bus, dict) else None,
        )
        return {
            "ui": {"ez_pipeline_switchboard": [ui_payload]},
            "result": (updated_bus, summary),
        }

