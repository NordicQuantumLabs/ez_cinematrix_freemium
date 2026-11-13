# -*- coding: utf-8 -*-
from typing import Any, Dict, List, Tuple

PIPELINE_EXECUTION_MODE_CHOICES: List[str] = [
    "full_studio_image_and_video (Full Studio: Bild [03-04] + Video [05-08])",
    "image_only_krea2_studio (Endast Bild: Kör Krea 2 [03-04] — Bypass Video [05-08])",
    "video_only_direct_i2v (Endast Video: Kör Video [05-08] — Bypass Krea 2 [03-04])",
    "custom_manual_switches (Manuella Modul-Switchar nedan)",
]

BYPASS_BEHAVIOR_CHOICES: List[str] = [
    "bypass_mode_4 (ComfyUI Bypass — Skicka data genom noden, 0s / 0 VRAM)",
    "mute_mode_2 (ComfyUI Mute — Tysta noden helt)",
]

SWITCHBOARD_TARGET_NODE_GROUPS: Dict[str, Tuple[str, ...]] = {
    "qwenvl_02": ("EZCinematrixQwenVLTimelineCompiler",),
    "krea2_image_03_04": (
        "EZCinematrixImageModelAndLoraSplitter",
        "EZCinematrixKrea2ThreeStageSampler",
        "EZCinematrixKrea2DualStageSampler",
    ),
    "minimax_video_05_08": (
        "EZCinematrixVideoEngineAndLoraStack",
        "EZCinematrixVideoDirectorAndGuide",
        "EZCinematrixJointAVTemporalSampler",
        "EZCinematrixCinemaVaultPostAndCombine",
    ),
    "suno_music_12": ("EZCinematrixSunoMusicVideoStudio",),
    "omni_reference_13": ("EZCinematrixOmniReferenceLoader",),
    "anatomy_dock_09": ("EZCinematrixNeuralAnatomyContinuityDock",),
}


def resolve_switchboard_execution_flags(
    pipeline_execution_mode: str,
    enable_qwenvl_compiler_02: bool = True,
    enable_krea2_image_03_04: bool = True,
    enable_minimax_video_05_08: bool = True,
    enable_suno_music_12: bool = True,
    enable_omni_reference_13: bool = True,
    enable_anatomy_dock_09: bool = True,
    bypass_behavior: str = "bypass_mode_4 (ComfyUI Bypass — Skicka data genom noden, 0s / 0 VRAM)",
) -> Dict[str, Any]:
    raw_mode = str(pipeline_execution_mode or "").strip().lower()
    eff_krea2 = bool(enable_krea2_image_03_04)
    eff_video = bool(enable_minimax_video_05_08)
    resolved_preset = "custom_manual_switches"

    if raw_mode.startswith("image_only") or "endast bild" in raw_mode:
        eff_krea2 = True
        eff_video = False
        resolved_preset = "image_only_krea2_studio"
    elif raw_mode.startswith("video_only") or "endast video" in raw_mode:
        eff_krea2 = False
        eff_video = True
        resolved_preset = "video_only_direct_i2v"
    elif raw_mode.startswith("full_studio") or "full studio" in raw_mode:
        eff_krea2 = True
        eff_video = True
        resolved_preset = "full_studio_image_and_video"

    use_mute = str(bypass_behavior or "").strip().lower().startswith("mute_mode_2")
    inactive_litegraph_mode = 2 if use_mute else 4

    node_modes: Dict[str, int] = {}
    group_states = {
        "qwenvl_02": bool(enable_qwenvl_compiler_02),
        "krea2_image_03_04": bool(eff_krea2),
        "minimax_video_05_08": bool(eff_video),
        "suno_music_12": bool(enable_suno_music_12),
        "omni_reference_13": bool(enable_omni_reference_13),
        "anatomy_dock_09": bool(enable_anatomy_dock_09),
    }
    for grp_key, cls_tuple in SWITCHBOARD_TARGET_NODE_GROUPS.items():
        is_on = group_states.get(grp_key, True)
        lg_mode = 0 if is_on else inactive_litegraph_mode
        for cls_name in cls_tuple:
            node_modes[cls_name] = lg_mode

    return {
        "resolved_preset": resolved_preset,
        "inactive_litegraph_mode": inactive_litegraph_mode,
        "enable_qwenvl_compiler_02": bool(enable_qwenvl_compiler_02),
        "enable_krea2_image_03_04": bool(eff_krea2),
        "enable_minimax_video_05_08": bool(eff_video),
        "enable_suno_music_12": bool(enable_suno_music_12),
        "enable_omni_reference_13": bool(enable_omni_reference_13),
        "enable_anatomy_dock_09": bool(enable_anatomy_dock_09),
        "node_modes": node_modes,
    }


def compile_pipeline_switchboard_state(
    pipeline_execution_mode: str,
    enable_qwenvl_compiler_02: bool = True,
    enable_krea2_image_03_04: bool = True,
    enable_minimax_video_05_08: bool = True,
    enable_suno_music_12: bool = True,
    enable_omni_reference_13: bool = True,
    enable_anatomy_dock_09: bool = True,
    bypass_behavior: str = "bypass_mode_4 (ComfyUI Bypass — Skicka data genom noden, 0s / 0 VRAM)",
    thermal_protection_mode: str = "auto_devops_shield (Auto DevOps Skydd — GPU 78°C / CPU 85°C + Smart Kylpaus)",
    cinematrix_bus: Dict[str, Any] | None = None,
) -> Tuple[Dict[str, Any], str, Dict[str, Any]]:
    flags = resolve_switchboard_execution_flags(
        pipeline_execution_mode=pipeline_execution_mode,
        enable_qwenvl_compiler_02=enable_qwenvl_compiler_02,
        enable_krea2_image_03_04=enable_krea2_image_03_04,
        enable_minimax_video_05_08=enable_minimax_video_05_08,
        enable_suno_music_12=enable_suno_music_12,
        enable_omni_reference_13=enable_omni_reference_13,
        enable_anatomy_dock_09=enable_anatomy_dock_09,
        bypass_behavior=bypass_behavior,
    )
    updated_bus = dict(cinematrix_bus) if isinstance(cinematrix_bus, dict) else {}
    try:
        from .engine_ez_01_cinematrix_canvas_ingest import resolve_cinematrix_thermal_shield_config
        t_cfg = resolve_cinematrix_thermal_shield_config(thermal_protection_mode=thermal_protection_mode, tier_id=str(updated_bus.get("hardware_tier", "1")))
        updated_bus["thermal_protection_mode"] = t_cfg["mode_key"]
        updated_bus["thermal_shield"] = t_cfg
        if isinstance(updated_bus.get("hardware_tier_profile"), dict):
            hp = dict(updated_bus["hardware_tier_profile"])
            hp["thermal_protection_mode"] = t_cfg["mode_key"]
            hp["thermal_shield"] = t_cfg
            updated_bus["hardware_tier_profile"] = hp
    except Exception:
        t_cfg = {"mode_key": "auto_devops_shield", "trigger_gpu_c": 78.0}
    updated_bus["pipeline_switchboard"] = dict(flags)
    updated_bus["bypass_krea2_image"] = not bool(flags["enable_krea2_image_03_04"])
    updated_bus["bypass_minimax_video"] = not bool(flags["enable_minimax_video_05_08"])
    updated_bus["bypass_qwenvl_compiler"] = not bool(flags["enable_qwenvl_compiler_02"])
    updated_bus["bypass_suno_music"] = not bool(flags["enable_suno_music_12"])
    updated_bus["bypass_omni_reference"] = not bool(flags["enable_omni_reference_13"])
    updated_bus["bypass_anatomy_dock"] = not bool(flags["enable_anatomy_dock_09"])

    badge = lambda ok: "ON" if ok else ("MUTE" if flags["inactive_litegraph_mode"] == 2 else "BYPASS")
    summary = (
        f"[EZ-SWITCHBOARD-14] Mode={flags['resolved_preset']} | Thermal={t_cfg.get('mode_key', 'auto')} ({t_cfg.get('trigger_gpu_c', 78.0):.0f}°C) | "
        f"[02] Qwen3-VL: {badge(flags['enable_qwenvl_compiler_02'])} | "
        f"[03-04] Krea2: {badge(flags['enable_krea2_image_03_04'])} | "
        f"[05-08] Video: {badge(flags['enable_minimax_video_05_08'])} | "
        f"[12] Suno: {badge(flags['enable_suno_music_12'])} | "
        f"[13] OmniRef: {badge(flags['enable_omni_reference_13'])} | "
        f"[09] Anatomy: {badge(flags['enable_anatomy_dock_09'])}"
    )
    ui_payload = {
        "preset": flags["resolved_preset"],
        "summary": summary,
        "flags": flags,
    }
    return updated_bus, summary, ui_payload

