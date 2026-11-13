# -*- coding: utf-8 -*-
from ..EZ_ENGINES.engine_ez_11_cinematrix_studio_note import (
    NOTE_TOPIC_PRESETS,
    NOTE_LOCALE_CHOICES,
    STUDIO_GUIDE_CHAPTERS,
    resolve_note_locale_code,
    compile_localized_studio_note_markdown,
)


class EzCinematrixStudioNoteAdapter:
    """Adapter for EZ [11] Cinematrix Studio Note, How-To & Model Guide."""

    @staticmethod
    def execute_studio_note(
        topic_preset: str,
        note_locale: str = "Auto (Follow Active UI Locale)",
        custom_notes: str = "",
        cinematrix_bus=None,
    ):
        compiled_text, updated_bus, ui_payload = compile_localized_studio_note_markdown(
            topic_preset=topic_preset,
            note_locale=note_locale,
            custom_notes=custom_notes,
            cinematrix_bus=cinematrix_bus if isinstance(cinematrix_bus, dict) else None,
        )
        return {
            "ui": {"ez_studio_note": [ui_payload]},
            "result": (compiled_text, updated_bus),
        }
