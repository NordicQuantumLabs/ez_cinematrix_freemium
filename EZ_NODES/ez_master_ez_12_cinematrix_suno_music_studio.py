# -*- coding: utf-8 -*-
import torch
from ..EZ_ENGINES.engine_ez_12_cinematrix_suno_music_studio import (
    SUNO_SOURCE_MODES,
    SUNO_PERFORMANCE_MODES,
    SUNO_DURATION_SYNC_MODES,
    SUNO_MODEL_PRESETS,
    discover_local_audio_files,
)
from ..EZ_ADAPTERS.adapter_ez_12_cinematrix_suno_music_studio import EzCinematrixSunoMusicStudioAdapter


class EZCinematrixSunoMusicVideoStudio:
    """🎵 [ZONE 12] Suno URL/ID Auto-Lyrics & Audio Fetcher, Suno v4 API & Local Audio Beat-Sync Studio."""

    @classmethod
    def INPUT_TYPES(cls):
        audio_choices = discover_local_audio_files()
        return {
            'required': {
                'source_mode': (SUNO_SOURCE_MODES, {'default': SUNO_SOURCE_MODES[0]}),
                'performance_mode': (SUNO_PERFORMANCE_MODES, {'default': SUNO_PERFORMANCE_MODES[0]}),
                'duration_sync_mode': (SUNO_DURATION_SYNC_MODES, {'default': SUNO_DURATION_SYNC_MODES[0]}),
                'suno_song_url_or_id': (
                    'STRING',
                    {
                        'default': '',
                        'multiline': False,
                    },
                ),
                'local_audio_file': (audio_choices, {'default': audio_choices[0]}),
                'custom_audio_path': ('STRING', {'default': '', 'multiline': False}),
                'start_offset_sec': ('FLOAT', {'default': 0.0, 'min': 0.0, 'max': 600.0, 'step': 0.5}),
                'custom_duration_sec': ('FLOAT', {'default': 20.0, 'min': 5.0, 'max': 300.0, 'step': 1.0}),
                'suno_model': (SUNO_MODEL_PRESETS, {'default': SUNO_MODEL_PRESETS[0]}),
                'song_style_tags': (
                    'STRING',
                    {
                        'default': 'dark cyberpunk synthwave, powerful female vocals, heavy sub-bass, 124 bpm',
                        'multiline': False,
                    },
                ),
                'instrumental_only': ('BOOLEAN', {'default': False}),
                'suno_api_endpoint': (
                    'STRING',
                    {'default': 'https://api.sunoapi.org/api/v1/generate', 'multiline': False},
                ),
                'suno_api_key': ('STRING', {'default': '', 'multiline': False}),
                'lyrics_or_prompt': (
                    'STRING',
                    {
                        'default': '',
                        'multiline': True,
                    },
                ),
            },
            'optional': {
                'cinematrix_bus': ('MINIMAX_GUIDE',),
            },
        }

    RETURN_TYPES = ('AUDIO', 'STRING', 'STRING', 'FLOAT', 'MINIMAX_GUIDE')
    RETURN_NAMES = ('suno_audio', 'beat_timeline_prompt', 'fetched_lyrics', 'detected_bpm', 'cinematrix_bus')
    FUNCTION = 'execute_suno_studio'
    OUTPUT_NODE = True
    CATEGORY = 'EZ_Cinematrix_Core/12_Suno_Music_Studio'

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        return True

    @torch.inference_mode()
    def execute_suno_studio(
        self,
        source_mode,
        performance_mode,
        duration_sync_mode,
        suno_song_url_or_id='',
        local_audio_file='',
        custom_audio_path='',
        start_offset_sec=0.0,
        custom_duration_sec=20.0,
        suno_model='chirp-v4 (Suno v4 Studio)',
        song_style_tags='',
        lyrics_or_prompt='',
        instrumental_only=False,
        suno_api_endpoint='https://api.sunoapi.org/api/v1/generate',
        suno_api_key='',
        cinematrix_bus=None,
    ):
        return EzCinematrixSunoMusicStudioAdapter.run_suno_studio(
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
            cinematrix_bus=cinematrix_bus,
        )


NODE_SUITE_VERSION = 'v1.0 Freemium'
NODE_CLASS_MAPPINGS = {'EZCinematrixSunoMusicVideoStudio': EZCinematrixSunoMusicVideoStudio}
NODE_DISPLAY_NAME_MAPPINGS = {
    'EZCinematrixSunoMusicVideoStudio': '🎵 EZ [12] Cinematrix Suno Music Video & Beat-Sync Studio — Freemium v1.0'
}
