# -*- coding: utf-8 -*-
from ..EZ_ENGINES.engine_ez_02_cinematrix_qwenvl_timeline import _verify_cinematrix_license_active, _resolve_dropdown_custom_or_random, discover_dynamic_vlm_models, _tensor_to_pil_and_b64, _resolve_local_vlm_path, _run_local_transformers_vlm, _normalize_qwenvl_two_block_output, execute_qwenvl_story_compiler, _resolve_audio_soundtrack_mode, _resolve_content_rating_tier, _analyze_scene_cast_and_extras, _detect_subject_taxonomy_and_species_lock, resolve_scene_continuity_mode, MASTER_DURATION_PRESETS, STYLE_TARGET_PRESETS, CAMERA_ZOOM_PRESETS, LIGHTING_AMBIENT_PRESETS, SUBJECT_AGE_PRESETS, AGE_DIFFERENCE_PRESETS, CAMERA_MOVEMENT_PRESETS, AUDIO_SOUNDTRACK_MODE_PRESETS, CONTENT_RATING_MODE_PRESETS, SUBJECT_STANCE_POSTURE_PRESETS, BODY_CHOREOGRAPHY_PRESETS, CAMERA_TRAJECTORY_ARC_PRESETS, BACKGROUND_EXTRAS_CROWD_PRESETS, SCENE_CONTINUITY_MODES
from ..EZ_ADAPTERS.adapter_ez_02_cinematrix_qwenvl_timeline import EzCinematrixQwenVLAdapter

import base64
import gc
import hashlib
import hmac
import json
import os
import random
import re
import struct
import urllib.request
import zlib
from datetime import datetime
from pathlib import Path
import torch
import folder_paths
import comfy.model_management

class EZCinematrixQwenVLTimelineCompiler:
    """🔮 [ZONE 2] Qwen3-VL Autoprompt Enhancer, Dynamic Cast & Background Extras (Statister) Selector & Instant VRAM Cleaner."""

    @classmethod
    def INPUT_TYPES(cls):
        vlm_choices = discover_dynamic_vlm_models()
        seed_mode_choices = ['auto_from_bus_or_local', 'use_local_compiler_seed', 'sync_with_master_seed_01']
        rating_choices = list(CONTENT_RATING_MODE_PRESETS)
        extras_choices = BACKGROUND_EXTRAS_CROWD_PRESETS + ['random']
        return {'required': {'user_input': ('STRING', {'default': 'A cinematic warrior standing in a neon rain courtyard.', 'multiline': True}), 'content_rating_mode': (rating_choices, {'default': rating_choices[0], 'tooltip': '3 lägen: (1) Uncensored Artistic / Action (ingen censur av loincloth/blod/strid, men förbjuder oombedd genitalie-hallucination), (2) SFW (heltäckande klädsel), (3) NSFW Explicit Adult / Erotic (aktiv erotik & full anatomi).'}), 'audio_soundtrack_mode': (AUDIO_SOUNDTRACK_MODE_PRESETS, {'default': AUDIO_SOUNDTRACK_MODE_PRESETS[0], 'tooltip': 'Välj ljudläge för videoklipp: Endast ljudeffekter (ingen musik), Ljudeffekter & Tal (ingen musik), Bakgrundsmusik UTAN sång, Bakgrundsmusik MED sång, eller Auto.'}), 'vlm_model_name': (vlm_choices, {'default': vlm_choices[0]}), 'master_duration': (MASTER_DURATION_PRESETS + ['random', 'custom'], {'default': '20-second'}), 'style_target': (STYLE_TARGET_PRESETS + ['random', 'custom'], {'default': 'original', 'tooltip': "Välj 'original' för vanlig I2I/I2V som bevarar källbildens stil, eller en specifik stil för att aktivera Native Krea 2 Style-Embedding Projector."}), 'camera_zoom': (CAMERA_ZOOM_PRESETS + ['random', 'custom'], {'default': 'medium-shot'}), 'lighting_ambient': (LIGHTING_AMBIENT_PRESETS + ['random', 'custom'], {'default': 'auto'}), 'subject_1_age': (SUBJECT_AGE_PRESETS + ['random', 'custom'], {'default': '25-year-old'}), 'age_difference': (AGE_DIFFERENCE_PRESETS + ['random', 'custom'], {'default': 'same age'}), 'camera_movement': (CAMERA_MOVEMENT_PRESETS + ['random', 'custom'], {'default': CAMERA_MOVEMENT_PRESETS[0]}), 'subject_stance_posture': (SUBJECT_STANCE_POSTURE_PRESETS + ['random'], {'default': SUBJECT_STANCE_POSTURE_PRESETS[0], 'tooltip': 'Universal 3-Axis Director Axel 1: Kroppshållning & Grupp/Crowd/Multi-Akt-komposition.'}), 'body_choreography_preset': (BODY_CHOREOGRAPHY_PRESETS + ['random'], {'default': BODY_CHOREOGRAPHY_PRESETS[0], 'tooltip': 'Universal 3-Axis Director Axel 2: Kroppsrörelse & Koreografi.'}), 'camera_trajectory_arc': (CAMERA_TRAJECTORY_ARC_PRESETS + ['random'], {'default': CAMERA_TRAJECTORY_ARC_PRESETS[0], 'tooltip': 'Universal 3-Axis Director Axel 3: Kamerabana, Vinkelbåge & 180° Outro Track ➔ Follow.'}), 'custom_subject_1_age': ('STRING', {'default': '', 'tooltip': "Eget värde när subject_1_age står på 'custom' (t.ex. '28-year-old')."}), 'custom_age_difference': ('STRING', {'default': '', 'tooltip': "Eget värde när age_difference står på 'custom' (t.ex. '7 years older')."}), 'custom_camera_movement': ('STRING', {'default': '', 'tooltip': "Egen kamerarörelse när camera_movement står på 'custom'."}), 'custom_style_or_lighting': ('STRING', {'default': '', 'tooltip': "Egen stil eller ljussättning när style_target/lighting_ambient står på 'custom'."}), 'custom_duration_seconds': ('FLOAT', {'default': 0.0, 'min': 0.0, 'max': 86400.0, 'step': 1.0}), 'compiler_seed': ('INT', {'default': 42, 'min': 0, 'max': 9007199254740991, 'step': 1, 'control_after_generate': True}), 'seed_mode': (seed_mode_choices, {'default': seed_mode_choices[0]}), 'lm_studio_endpoint': ('STRING', {'default': 'http://127.0.0.1:1234/v1/chat/completions'}), 'vram_cleanup_after': ('BOOLEAN', {'default': True})}, 'optional': {'reference_image': ('IMAGE',), 'cinematrix_bus': ('MINIMAX_GUIDE',), 'background_extras_crowd': (extras_choices, {'default': extras_choices[0], 'tooltip': 'Statister & Bakgrundskaraktärer (Dropdown): Auto från Prompt (lägger automatiskt till passande statister vid slagsmål, älskog, barhäng, stadsvy etc.), Inga Statister (endast huvudkaraktärer), Få Statister (2–4 pers), Barhäng/Taverna, Stadsvy/Gata, Slagsmål/Arena, TV-Studio/Publik eller Intim Grupp.'}), 'scene_continuity_mode': (SCENE_CONTINUITY_MODES, {'default': SCENE_CONTINUITY_MODES[0], 'tooltip': '🎬 Scen- & Klippläge (100% Generellt & Promptstyrt): Auto från Prompt, Låst Rum & Miljö (Musikvideo/Porträtt), One-Shot Lång Tagning (Obruten kameraåkning genom skiftande miljöer), eller Hollywood Multi-Scene Cuts (Äkta filmklipp mellan akter & miljöer med karaktärslås).'}), 'custom_negative_prompt': ('STRING', {'default': '', 'multiline': False, 'tooltip': 'Valfri manuell Negative Prompt (hanteras via knappen [🛡️ NEGATIVE PROMPT] i noden). Lämna tom för automatisk generering.'})}}
    RETURN_TYPES = ('STRING', 'STRING', 'STRING', 'MINIMAX_GUIDE')
    RETURN_NAMES = ('krea2_image_prompt', 'h3_video_timeline_prompt', 'adaptive_negative_prompt', 'cinematrix_bus')
    FUNCTION = 'compile_timeline'
    OUTPUT_NODE = True
    CATEGORY = 'EZ_Cinematrix_Core/02_QwenVL_Prompt'

    @torch.inference_mode()
    def compile_timeline(self, user_input, vlm_model_name, master_duration, style_target, camera_zoom, lighting_ambient, subject_1_age, age_difference, camera_movement, content_rating_mode='Uncensored Artistic / Action (Ingen Censur — Följer Prompten)', audio_soundtrack_mode='sfx_only_no_music (Endast Ljudeffekter / Ingen Musik)', subject_stance_posture='auto_from_prompt (Auto från Prompt / Bild)', body_choreography_preset='auto_from_prompt_or_audio (Auto från Prompt / Ljud)', camera_trajectory_arc='follow_02_camera_setting (Följ [02] Kamerainställning / Auto)', custom_subject_1_age='', custom_age_difference='', custom_camera_movement='', custom_style_or_lighting='', custom_duration_seconds=0.0, compiler_seed=42, seed_mode='auto_from_bus_or_local', lm_studio_endpoint='http://127.0.0.1:1234/v1/chat/completions', vram_cleanup_after=True, reference_image=None, cinematrix_bus=None, background_extras_crowd='auto_from_prompt (Auto från Prompt — Slagsmål / Älskog / Barhäng / Stadsvy / Solo)', scene_continuity_mode=SCENE_CONTINUITY_MODES[0], custom_negative_prompt=''):
        (b1, b2, neg, bus) = EzCinematrixQwenVLAdapter.run_compiler(user_input=user_input, vlm_model_name=vlm_model_name, master_duration=master_duration, style_target=style_target, subject_1_age=subject_1_age, age_difference=age_difference, camera_movement=camera_movement, lm_studio_endpoint=lm_studio_endpoint, vram_cleanup_after=vram_cleanup_after, camera_zoom=camera_zoom, lighting_ambient=lighting_ambient, custom_subject_1_age=custom_subject_1_age, custom_age_difference=custom_age_difference, custom_camera_movement=custom_camera_movement, custom_style_or_lighting=custom_style_or_lighting, custom_duration_seconds=custom_duration_seconds, compiler_seed=compiler_seed, seed_mode=seed_mode, content_rating_mode=content_rating_mode, audio_soundtrack_mode=audio_soundtrack_mode, subject_stance_posture=subject_stance_posture, body_choreography_preset=body_choreography_preset, camera_trajectory_arc=camera_trajectory_arc, background_extras_crowd=background_extras_crowd, reference_image=reference_image, cinematrix_bus=cinematrix_bus, custom_negative_prompt=custom_negative_prompt, scene_continuity_mode=scene_continuity_mode)
        auto_neg = str(bus.get('auto_generated_negative_prompt', neg) if isinstance(bus, dict) else neg)
        return {'ui': {'ez_qwen_prompts': [{'b1': str(b1), 'b2': str(b2), 'neg': str(neg), 'auto_neg': auto_neg}]}, 'result': (b1, b2, neg, bus)}
NODE_SUITE_VERSION = 'v1.0 Freemium'
NODE_CLASS_MAPPINGS = {'EZCinematrixQwenVLTimelineCompiler': EZCinematrixQwenVLTimelineCompiler}
NODE_DISPLAY_NAME_MAPPINGS = {'EZCinematrixQwenVLTimelineCompiler': '🔮 EZ [02] Cinematrix Qwen3-VL Timeline Compiler & VRAM Cleaner — Freemium v1.0'}

