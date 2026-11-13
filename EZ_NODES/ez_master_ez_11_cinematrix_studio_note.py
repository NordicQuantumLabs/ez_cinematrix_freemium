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
                            "🎬 Studio Notes / EZ [02] Dynamic 360s/72-Shot VLM Scaling, [03] Dialect Sanitizer, [07] 3D Latent Hysteresis & [13] 5-Slot Studio:\n"
                            "- NEW! 📈 Dynamic Long-Form VLM Token & Context Scaling ([02]): Automatically scales up to 360s (72 shots), raises effective_max_tokens (6144➔8192) & llama_cpp n_ctx (8192➔12288), and enforces a uniform per-shot word quota (~38–68 words/shot) so 4–6 minute videos never truncate before [END_PROMPT].\n"
                            "- NEW! 🧹 Krea 2 Prose Sanitizer ([02]) & Dialect Weight Normalizer ([03]): Strips (tag:1.2) weight brackets and runaway relative clauses on Krea 2 / Flux while escaping unweighted \\(medium\\) parentheses on Pony V6 XL & Illustrious XL. Both krea2_image_prompt and h3_video_timeline_prompt are 100% open STRING outputs ready for any text preview node.\n"
                            "- NEW! ⚡ GPU-Vectorized 3D Dual-Threshold Hysteresis & 24-Channel Orthogonal Residual Spike Projection ([07]): Uses 3D max_pool3d hysteresis (seed_hi > 11.2, cand_lo > 6.5) and projects out only the corruptive 24-channel spike axis while preserving 92% of orthogonal skin pore and fabric texture energy."
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
