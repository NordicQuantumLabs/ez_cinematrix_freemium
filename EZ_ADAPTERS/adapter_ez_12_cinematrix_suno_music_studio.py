# -*- coding: utf-8 -*-
from ..EZ_ENGINES.engine_ez_12_cinematrix_suno_music_studio import (
    SUNO_SOURCE_MODES,
    SUNO_PERFORMANCE_MODES,
    SUNO_DURATION_SYNC_MODES,
    SUNO_MODEL_PRESETS,
    discover_local_audio_files,
    extract_4band_viseme_and_beat_envelope,
    reslice_suno_packet_to_duration,
    execute_suno_music_video_studio,
)


class EzCinematrixSunoMusicStudioAdapter:
    """Adapter for EZ [12] Cinematrix Suno Music Video & Beat-Sync Studio."""

    @staticmethod
    def run_suno_studio(
        source_mode: str,
        performance_mode: str,
        duration_sync_mode: str,
        local_audio_file: str,
        suno_song_url_or_id: str = '',
        custom_audio_path: str = '',
        start_offset_sec: float = 0.0,
        custom_duration_sec: float = 20.0,
        suno_model: str = 'chirp-v4 (Suno v4 Studio)',
        song_style_tags: str = 'dark cyberpunk synthwave, powerful female vocals, heavy sub-bass, 124 bpm',
        lyrics_or_prompt: str = '',
        instrumental_only: bool = False,
        suno_api_endpoint: str = 'https://api.sunoapi.org/api/v1/generate',
        suno_api_key: str = '',
        cinematrix_bus=None,
    ):
        comfy_audio, beat_prompt, fetched_lyrics, bpm_val, updated_bus, ui_meta = execute_suno_music_video_studio(
            source_mode=source_mode,
            performance_mode=performance_mode,
            duration_sync_mode=duration_sync_mode,
            local_audio_file=local_audio_file,
            suno_song_url_or_id=suno_song_url_or_id,
            custom_audio_path=custom_audio_path,
            start_offset_sec=start_offset_sec,
            custom_duration_sec=custom_duration_sec,
            suno_model=suno_model,
            song_style_tags=song_style_tags,
            lyrics_or_prompt=lyrics_or_prompt,
            instrumental_only=instrumental_only,
            suno_api_endpoint=suno_api_endpoint,
            suno_api_key=suno_api_key,
            cinematrix_bus=cinematrix_bus if isinstance(cinematrix_bus, dict) else None,
        )
        return {
            'ui': {'ez_suno_studio': [ui_meta]},
            'result': (comfy_audio, beat_prompt, fetched_lyrics, bpm_val, updated_bus),
        }
