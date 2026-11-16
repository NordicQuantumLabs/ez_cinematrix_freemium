# -*- coding: utf-8 -*-
import torch
from ..EZ_ENGINES.engine_ez_11_cinematrix_studio_note import (
    NOTE_TOPIC_PRESETS,
    NOTE_LOCALE_CHOICES,
)
from ..EZ_ADAPTERS.adapter_ez_11_cinematrix_studio_note import EzCinematrixStudioNoteAdapter


class EZCinematrixStudioNoteAndGuide:
    """📝 [ZONE 11] Interactive Localized Markdown Note, How-To Flowchart, Model/LoRA & 4x+1x Upscale Handbook."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "topic_preset": (NOTE_TOPIC_PRESETS, {"default": NOTE_TOPIC_PRESETS[0]}),
                "note_locale": (NOTE_LOCALE_CHOICES, {"default": NOTE_LOCALE_CHOICES[0]}),
                "custom_notes": (
                    "STRING",
                    {
                        "default": (
                            "🎬 Studio Notes / v3.5 Senaste Uppdateringar (Local-Priority Shield, PRISM 01–09, Audio-Mute Strip & Långfilms-Muxning):\n"
                            "- NYHET! 🛡️ Local-First LoRA-Skydd i [03] & [05] (remote_hub_mode = local_priority): Dina lokala modell- och LoRA-val i [03]/[05] vinner nu alltid per slot (grön bricka '🛡️ LOKALA VAL VINNER'). Kvarlämnade LoRAs i [10] kan aldrig längre skriva över aktiva slots via bussen!\n"
                            "- NYHET! 🔇 Audio-Mute Key Strip ([05]) & PRISM Foundry v3.5 (I64 Alpha + Zero-Up Kaiming Guard): Håll lora_X_audio_strength = 0.00 på alla visuella merges (ez_h3_01–04, 07–09) så raderas ensidiga ljudnycklar fysiskt före injektion och 32 kHz Audio-VAE förblir 100 % kristallren. På SingularityV2_PRISM2 kör du ~25–30 % lägre vikt (0.50–0.65 i Slot 1) + shift_video = 5.0.\n"
                            "- NYHET! 🧹 Qwen3-VL Meta-Direktiv-Scrubber ([02]) & -f ffmetadata Långfilms-Muxning ([08] + [12]): Tvättar bort ekade kompilatorregler ur [Shot 1..N], eliminerar Windows 32k CLI-gräns i FFmpeg via temporär metadatafil och synkar 48 kHz fltp stereo i PyAV."
                        ),
                        "multiline": True,
                    },
                ),
            },
            "optional": {
                "cinematrix_bus": ("MINIMAX_GUIDE",),
            },
        }

    RETURN_TYPES = ("STRING", "MINIMAX_GUIDE")
    RETURN_NAMES = ("compiled_guide_text", "cinematrix_bus")
    FUNCTION = "run_studio_note"
    OUTPUT_NODE = True
    CATEGORY = "EZ_Cinematrix_Core/11_Studio_Note_Guide"

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        return True

    @torch.inference_mode()
    def run_studio_note(
        self,
        topic_preset,
        note_locale="Auto (Follow Active UI Locale)",
        custom_notes="",
        cinematrix_bus=None,
    ):
        return EzCinematrixStudioNoteAdapter.execute_studio_note(
            topic_preset=topic_preset,
            note_locale=note_locale,
            custom_notes=custom_notes,
            cinematrix_bus=cinematrix_bus,
        )


NODE_SUITE_VERSION = 'v1.0 Freemium'
NODE_CLASS_MAPPINGS = {"EZCinematrixStudioNoteAndGuide": EZCinematrixStudioNoteAndGuide}
NODE_DISPLAY_NAME_MAPPINGS = {
    "EZCinematrixStudioNoteAndGuide": "📝 EZ [11] Cinematrix Studio Note, How-To & Model Guide — Freemium v1.0"
}
