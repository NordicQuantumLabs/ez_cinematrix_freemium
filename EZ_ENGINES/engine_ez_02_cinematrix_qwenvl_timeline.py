# -*- coding: utf-8 -*-

import base64
import gc
import hashlib
import hmac
import json
import math
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
_EZ_MASTER_SALT = b'EMPIRE_HUD_QUANTUM_CORE_SALT_2026_AES256_HYBRID'
_AES_SBOX = (99, 124, 119, 123, 242, 107, 111, 197, 48, 1, 103, 43, 254, 215, 171, 118, 202, 130, 201, 125, 250, 89, 71, 240, 173, 212, 162, 175, 156, 164, 114, 192, 183, 253, 147, 38, 54, 63, 247, 204, 52, 165, 229, 241, 113, 216, 49, 21, 4, 199, 35, 195, 24, 150, 5, 154, 7, 18, 128, 226, 235, 39, 178, 117, 9, 131, 44, 26, 27, 110, 90, 160, 82, 59, 214, 179, 41, 227, 47, 132, 83, 209, 0, 237, 32, 252, 177, 91, 106, 203, 190, 57, 74, 76, 88, 207, 208, 239, 170, 251, 67, 77, 51, 133, 69, 249, 2, 127, 80, 60, 159, 168, 81, 163, 64, 143, 146, 157, 56, 245, 188, 182, 218, 33, 16, 255, 243, 210, 205, 12, 19, 236, 95, 151, 68, 23, 196, 167, 126, 61, 100, 93, 25, 115, 96, 129, 79, 220, 34, 42, 144, 136, 70, 238, 184, 20, 222, 94, 11, 219, 224, 50, 58, 10, 73, 6, 36, 92, 194, 211, 172, 98, 145, 149, 228, 121, 231, 200, 55, 109, 141, 213, 78, 169, 108, 86, 244, 234, 101, 122, 174, 8, 186, 120, 37, 46, 28, 166, 180, 198, 232, 221, 116, 31, 75, 189, 139, 138, 112, 62, 181, 102, 72, 3, 246, 14, 97, 53, 87, 185, 134, 193, 29, 158, 225, 248, 152, 17, 105, 217, 142, 148, 155, 30, 135, 233, 206, 85, 40, 223, 140, 161, 137, 13, 191, 230, 66, 104, 65, 153, 45, 15, 176, 84, 187, 22)
_AES_RCON = (0, 1, 2, 4, 8, 16, 32, 64, 128, 27, 54)
MASTER_DURATION_PRESETS = ['5-second', '10-second', '15-second', '20-second', '30-second', '45-second', '60-second', '120-second', '300-second', '600-second', '1800-second', '3600-second']
STYLE_TARGET_PRESETS = ['original', 'realism', 'semi-real', 'anime', 'cartoonish', 'cinematic-film-35mm', 'unreal-engine-5', 'dark-fantasy-real', 'dark-fantasy-cgi']
CAMERA_ZOOM_PRESETS = ['extreme-close-up', 'close-up', 'medium-close-up', 'medium-shot', 'medium-wide', 'wide-shot', 'extreme-wide-establishing']
LIGHTING_AMBIENT_PRESETS = ['auto', 'natural-muted-cinema', 'desaturated-low-chroma', 'bleach-bypass-gritty', 'cinematic-dark', 'volumetric-day', 'neon-cyberpunk', 'golden-hour', 'moonlit-noir', 'studio-rim-light', 'overcast-soft']
SUBJECT_AGE_PRESETS = ['auto_from_prompt_or_ref', '18-year-old', '21-year-old', '25-year-old', '30-year-old', '35-year-old', '40-year-old', '45-year-old', '50-year-old', '60-year-old', 'ageless-cyborg']
AGE_DIFFERENCE_PRESETS = ['same age', '2 years younger', '2 years older', '5 years younger', '5 years older', '10 years younger', '10 years older', '15 years older', 'none (single subject)']
CAMERA_MOVEMENT_PRESETS = [
    'locked-off tripod 50mm anamorphic master shot with shallow depth of field',
    'intentional slow dolly-in push toward subject (Aktiv Dolly-In Zoom)',
    'steady 85mm portrait lens at f/1.4 slowly drifting in a dolly-in motion',
    'low-angle medium-wide tracking shot with a handheld camera aesthetic',
    'slow 360-degree orbit around the midline axis',
    'smooth crane-up reveal transitioning into an anamorphic push-in',
    'dynamic whip-pan tracking subject velocity with subtle motion blur',
    'fpv drone glide weaving through foreground elements toward subject',
]
AUDIO_SOUNDTRACK_MODE_PRESETS = [
    'sfx_only_no_music (Endast Ljudeffekter / Ingen Musik)',
    'sfx_and_speech_no_music (Ljudeffekter & Tal / Ingen Musik)',
    'instrumental_bgm_no_vocals (Bakgrundsmusik UTAN Sång)',
    'bgm_with_vocals (Bakgrundsmusik MED Sång / Lip-Sync)',
    'auto_from_prompt_or_suno (Auto från Prompt / Suno [12])',
]
CONTENT_RATING_MODE_PRESETS = [
    'Uncensored Artistic / Action (Ingen Censur — Följer Prompten)',
    'SFW (Safe For Work — Heltäckande Klädsel)',
    'NSFW Explicit Adult / Erotic (Aktiv Erotik & Anatomi)',
]
SUBJECT_STANCE_POSTURE_PRESETS = [
    'auto_from_prompt (Auto från Prompt / Bild)',
    'standing_upright (Stående / Upright)',
    'sitting_table_bar_or_cockpit (Sittande — Bord / Barstol / Cockpit)',
    'reclining_lounging (Halvliggande / Reclining)',
    'lying_horizontal (Liggande / Horizontal)',
    'kneeling_crouching (På knä / Crouching)',
    'standing_social_bar_or_city (Social Scen — Huvudkaraktär + Sällskap i Bakgrund)',
    'epic_battlefield_army (Episkt Slagfält — Hjälte + Arméer i Bakgrund)',
    'story_vehicle_or_scene_transition (Multi-Akt — Gata ➔ Fordon/Cockpit ➔ Flyg)',
    'nsfw_solo_or_couple (NSFW Solo / Par — 1–2 pers)',
    'nsfw_threesome_or_group (NSFW Trekant / Grupp — 3–5 pers)',
    'nsfw_orgy_or_harem_scene (NSFW Orgie / Harem — 6+ pers)',
]
BODY_CHOREOGRAPHY_PRESETS = [
    'auto_from_prompt_or_audio (Auto från Prompt / Ljud)',
    'dance_music_video_groove (Beat-Synkad Musikvideodans)',
    'dance_sensual_club (Sensuell Klubbdans — Body-Roll & Hip-Sway)',
    'catwalk_runway_strut (Catwalk / Gå Framåt mot Kameran)',
    'running_action_sprint (Löpning / Action-Sprint med Dynamiskt Flöde)',
    'combat_guard_and_parry (Stridsställning, Parering & Närkamp)',
    'combat_heavy_weapon_strikes (Tunga Vapensvingar & Attackkombinationer)',
    'social_toast_dining_chat (Skåla, Äta, Dricka, Prata & Gestikulera)',
    'story_multi_act_progression (Multi-Akt Story — Följ Akt 1 ➔ Akt 2 ➔ Akt 3)',
    'nsfw_sensual_solo_tease (NSFW Sensuell Solo-Posering & Tease)',
    'nsfw_rhythmic_intimate_motion (NSFW Rytmisk Intim Rörelse)',
]
CAMERA_TRAJECTORY_ARC_PRESETS = [
    'follow_02_camera_setting (Följ [02] Kamerainställning / Auto)',
    'backward_track_low_to_high (Backward Track: Låg ➔ Hög Vinkel — 100% Ansikte)',
    'backward_track_mid_to_low (Backward Track: Mitten ➔ Låg Vinkel — 100% Ansikte)',
    'backward_track_low_to_mid (Backward Track: Låg ➔ Mitten — 100% Ansikte)',
    'backward_track_high_to_low (Backward Track: Hög ➔ Låg Vinkel — 100% Ansikte)',
    'backward_track_mid_to_mid (Backward Track: Rak Ögonhöjd — 100% Ansikte)',
    'outro_track_to_follow_low_to_high (Outro Track ➔ Follow: Framifrån Akt 1–2 ➔ 180° Ryggvy i Akt 3 [Låg➔Hög])',
    'outro_track_to_follow_mid_to_mid (Outro Track ➔ Follow: Framifrån Akt 1–2 ➔ 180° Ryggvy i Akt 3 [Mitten➔Mitten])',
    'outro_track_to_follow_mid_to_low (Outro Track ➔ Follow: Framifrån Akt 1–2 ➔ 180° Ryggvy i Akt 3 [Mitten➔Låg])',
    'outro_track_to_follow_low_to_low (Outro Track ➔ Follow: Framifrån Akt 1–2 ➔ 180° Ryggvy i Akt 3 [Låg➔Låg])',
    'crane_ascent_street_to_aerial (Crane / Drone Ascent: Gatuplan ➔ Höghöjdsvy över Stad)',
]
BACKGROUND_EXTRAS_CROWD_PRESETS = [
    'auto_from_prompt (Auto från Prompt — Slagsmål / Älskog / Barhäng / Stadsvy / Solo)',
    'none_isolated_main_cast (Inga Statister — Endast Huvudkaraktärer från Prompt)',
    'sparse_2_to_4_extras (Få Statister — 2–4 Bakgrundskaraktärer)',
    'social_bar_tavern_club_patrons (Barhäng / Taverna / Klubb — Gäster, Bartender & Sällskap)',
    'city_street_pedestrians_crowd (Stadsvy / Gata / Torg — Fotgängare & Stadsmyller)',
    'brawl_combat_fighters_arena (Slagsmål / Arena / Slagfält — Stridande Kombattanter & Armé)',
    'studio_crew_or_audience (TV-Studio / Scen / Konsert — Publik & Kamerateam i Bakgrund)',
    'intimate_group_companions (Älskog / Intim — Partner / Grupp / Harem-Sällskap)',
]
SCENE_CONTINUITY_MODES = [
    'auto_from_prompt (Auto från Prompt — Låst Scen / One-Shot Åkning / Hollywood Scenklipp)',
    'locked_stage_environment (Låst Rum & Miljö — Samma Plats, Ljus & Scen [Musikvideo/Porträtt])',
    'continuous_one_shot (One-Shot Lång Tagning — Obruten Kameraåkning genom Skiftande Miljöer)',
    'hollywood_multi_scene_cuts (Hollywood Multi-Scene Cuts — Äkta Filmklipp mellan Akter & Miljöer)',
]


def resolve_scene_continuity_mode(
    scene_continuity_mode: str = '',
    user_scene_input: str = '',
    subject_stance_posture: str = '',
    body_choreography_preset: str = '',
    camera_trajectory_arc: str = '',
) -> str:
    m_low = str(scene_continuity_mode or '').strip().lower()
    if m_low.startswith('locked_stage'):
        return 'locked_stage_environment'
    if m_low.startswith('continuous_one_shot'):
        return 'continuous_one_shot'
    if m_low.startswith('hollywood_multi_scene'):
        return 'hollywood_multi_scene_cuts'
    raw_u = str(user_scene_input or '').strip()
    raw_u = re.sub(r'(?is)\[MANDATORY MULTI-IMAGE REFERENCE BINDING\]:.*?\n\n', '', raw_u)
    raw_u = re.sub(r'(?is)\[SUNO\s+RHYTHMIC[\s\S]*$', '', raw_u)
    raw_u = re.sub(
        r'(?i)\b(?:no|zero|without)\s+(?:hard\s+|jump\s+|scene\s+|camera\s+)?(?:cuts?|scene\s+changes?|room\s+changes?)\b',
        ' ',
        raw_u,
    )
    st_low = str(subject_stance_posture or '').strip().lower()
    ch_low = str(body_choreography_preset or '').strip().lower()
    arc_low = str(camera_trajectory_arc or '').strip().lower()
    wants_explicit_oneshot = bool(
        re.search(
            r'(?i)\b(?:one[-\s]?shot|single[-\s]?take|long[-\s]?take|unbroken\s+(?:single\s+)?take|continuous\s+tracking\s+shot|obruten\s+tagning|lång\s+tagning|i\s+en\s+enda\s+tagning)\b',
            raw_u,
        )
    )
    has_explicit_cut_grammar = bool(
        re.search(
            r'(?i)(?:\[\s*(?:SCENE[\s_-]*CUT|HARD[\s_-]*CUT|SMASH[\s_-]*CUT|ACT\s*[2-9]|SCENE\s*[2-9])\s*\]|\b(?:cut\s+to|cuts\s+to|smash\s+cut\s+to|match\s+cut\s+to|cross[-\s]?cut\s+to|hard\s+cut\s+to|scene\s+cut\s+to|in\s+the\s+next\s+scene|switches?\s+scenes?\s+to|meanwhile\s+in\s+another|klipp\s+till|klipper\s+till|scenklipp\s+till|scenbyte\s+till|i\s+nästa\s+scen)\b)',
            raw_u,
        )
    )
    has_spatial_traversal = bool(
        re.search(
            r'(?i)\b(?:walks?\s+(?:out\s+of|out\s+into|into|through|outside|across\s+into)|steps?\s+(?:out\s+of|out\s+into|into|outside|through)|runs?\s+(?:out\s+of|out\s+into|into|through)|emerges?\s+(?:from|out\s+of|into)|exits?\s+(?:the|into|from)|leaves?\s+the\s+[\w\-]+\s+(?:and|into|out\s+into|to\s+enter)|passes?\s+through\s+the\s+(?:door(?:way)?|gate(?:way)?|portal|corridor|hallway|archway|exit)|går\s+(?:ut\s+ur|ut\s+i|ut\s+från|in\s+i|genom)|kliver\s+(?:ut\s+ur|ut\s+i|in\s+i|genom)|springer\s+(?:ut\s+ur|ut\s+i|in\s+i|genom)|lämnar\s+[\wåäöÅÄÖ\-]+\s+och\s+(?:går|kliver|springer|kommer)\s+(?:ut|in))\b',
            raw_u,
        )
    )
    has_vehicle_or_mount_departure = bool(
        re.search(
            r'(?i)\b(?:gets?\s+into|climbs?\s+(?:into|aboard|onto)|steps?\s+(?:into|aboard)|boards?|mounts?|enters?\s+the\s+(?:cockpit|cabin|vehicle|car|ship|craft)|sits?\s+(?:down\s+)?in(?:side)?\s+(?:a|an|the|her|his)|sätter\s+sig\s+i|kliver\s+(?:in\s+i|ombord)|hoppar\s+(?:in\s+i|upp\s+på)|stiger\s+(?:in\s+i|ombord))\b[\s\S]{0,160}\b(?:flies?\s+(?:away|off|up)|drives?\s+(?:away|off)|rides?\s+(?:away|off)|sails?\s+(?:away|off)|speeds?\s+(?:away|off)|takes?\s+off|launches?|soars?|liftoff|ascends?\s+into|flyger\s+(?:iväg|bort|upp)|kör\s+(?:iväg|bort)|rider\s+(?:iväg|bort)|svävar\s+iväg|lyfter\s+(?:mot|upp))\b',
            raw_u,
        )
    )
    if wants_explicit_oneshot and not has_explicit_cut_grammar:
        return 'continuous_one_shot'
    if has_explicit_cut_grammar:
        return 'hollywood_multi_scene_cuts'
    if has_vehicle_or_mount_departure and (has_spatial_traversal or st_low.startswith('story_vehicle') or ch_low.startswith('story_multi_act')):
        return 'hollywood_multi_scene_cuts'
    if st_low.startswith('story_vehicle') and not wants_explicit_oneshot:
        return 'hollywood_multi_scene_cuts'
    if has_spatial_traversal or arc_low.startswith(('outro_track_to_follow', 'crane_ascent')) or ch_low.startswith('story_multi_act'):
        return 'continuous_one_shot'
    return 'locked_stage_environment'


def _split_general_narrative_beats(user_scene_input: str, num_shots: int, continuity_mode: str = 'locked_stage_environment') -> list:
    target_n = max(1, int(num_shots or 1))
    if continuity_mode not in ('continuous_one_shot', 'hollywood_multi_scene_cuts'):
        return []
    txt = str(user_scene_input or '').strip()
    txt = re.sub(r'(?is)\[MANDATORY MULTI-IMAGE REFERENCE BINDING\]:.*?\n\n', '', txt).strip()
    txt = re.sub(r'(?is)\[SUNO\s+RHYTHMIC[\s\S]*$', '', txt).strip()
    txt = re.sub(r'(?is)\bBLOCK\s*\d+\b|\[\s*IMAGE\s*\]', ' ', txt).strip()
    if not txt:
        return []
    explicit_cut_split = re.split(
        r'(?i)(?:\[\s*(?:SCENE[\s_-]*CUT|HARD[\s_-]*CUT|SMASH[\s_-]*CUT)\s*\]|\b(?:smash\s+cut\s+to|match\s+cut\s+to|hard\s+cut\s+to|scene\s+cut\s+to|cut\s+to|klipp\s+till|scenklipp\s+till|scenbyte\s+till)\b)\s*[:,\-]?\s*',
        txt,
    )
    explicit_segments = [re.sub(r'\s+', ' ', seg).strip(' ,;:-') for seg in explicit_cut_split if len(seg.strip(' ,;:-')) >= 6]
    has_user_cut_tokens = len(explicit_segments) >= 2
    raw_clauses = []
    cut_flags = []
    source_pool = explicit_segments if has_user_cut_tokens else [txt]
    clause_delim = re.compile(
        r'(?:(?<=[.!?])\s+|;\s+|\s*,\s*(?=(?:and\s+then|then\s+(?:she|he|they|the)|before\s+\w+ing|after\s+which|sedan\s+|och\s+sedan|varefter\s+|och\s+(?:går|kliver|springer|sätter\s+sig|flyger|kör|rider)|and\s+(?:walks?|steps?|runs?|exits?|emerges?|gets?\s+into|climbs?\s+into|boards?|mounts?|sits?\s+in|flies?\s+away|drives?\s+away|rides?\s+away|takes?\s+off|soars?))\b)|\s+(?=(?:och\s+(?:sätter\s+sig|flyger\s+iväg|kör\s+iväg|rider\s+iväg)|and\s+(?:flies?\s+away|drives?\s+away|rides?\s+away|takes?\s+off))\b))',
        flags=re.IGNORECASE,
    )
    for seg_i, seg_txt in enumerate(source_pool):
        sub_parts = [re.sub(r'\s+', ' ', p).strip(' ,;:-') for p in clause_delim.split(seg_txt) if len(p.strip(' ,;:-')) >= 6]
        if not sub_parts:
            continue
        for sub_i, sp in enumerate(sub_parts):
            cleaned_sp = re.sub(r'^(?:and\s+then|and|och\s+sedan|sedan|och)\s+', '', sp, flags=re.IGNORECASE).strip()
            if not cleaned_sp:
                continue
            if not re.match(r'(?i)^(?:<subject\s*1>|she|he|they|the\s+|a\s+|an\s+|in\s+|inside\s+|outside\s+|out\s+|hon|han|de|karaktären)\b', cleaned_sp):
                cleaned_sp = f'<Subject 1> {cleaned_sp}'
            raw_clauses.append(cleaned_sp)
            cut_flags.append(bool(seg_i > 0 and sub_i == 0))
    if len(raw_clauses) < 2:
        return []
    mapped = []
    prev_beat_idx = -1
    for s_idx in range(target_n):
        b_idx = min(len(raw_clauses) - 1, int(math.floor(s_idx * len(raw_clauses) / float(target_n))))
        beat_txt = raw_clauses[b_idx]
        is_new_beat = (s_idx > 0 and b_idx != prev_beat_idx)
        if continuity_mode == 'hollywood_multi_scene_cuts':
            is_cut = bool(is_new_beat and (cut_flags[b_idx] or not has_user_cut_tokens))
        else:
            is_cut = False
        mapped.append({'shot_idx': s_idx + 1, 'beat_idx': b_idx, 'text': beat_txt, 'is_scene_cut': is_cut})
        prev_beat_idx = b_idx
    return mapped


def _analyze_scene_cast_and_extras(
    user_scene_input: str = '',
    subject_stance_posture: str = '',
    background_extras_crowd: str = '',
    slot2_is_dual_subject: bool = False,
    age_difference: str = '',
) -> dict:
    raw_u = str(user_scene_input or '').strip()
    clean_u_cast = re.sub(r'(?is)\[MANDATORY MULTI-IMAGE REFERENCE BINDING\]:.*?\n\n', '', raw_u)
    clean_u_cast = re.split(r'(?i)\b(?:Use Reference Slot #1|Preserve the primary protagonist|Preserve the primary character|Use Reference Video Slot #5)\b', clean_u_cast)[0].strip()
    raw_u = clean_u_cast
    u_low = raw_u.lower()
    st_low = str(subject_stance_posture or '').strip().lower()
    ex_low = str(background_extras_crowd or '').strip().lower()
    ad_low = str(age_difference or '').strip().lower()
    main_subj_tags = [int(m.group(1)) for m in re.finditer(r'(?i)<\s*main[_\s-]*subject\s*(\d+)\s*>', raw_u)]
    legacy_subj_tags = [int(m.group(1)) for m in re.finditer(r'(?i)<\s*subject\s*(\d+)\s*>', raw_u)]
    if main_subj_tags:
        max_subj_tag = max(main_subj_tags)
    elif legacy_subj_tags:
        max_subj_tag = max(legacy_subj_tags)
    else:
        max_subj_tag = 2 if slot2_is_dual_subject else 1
    is_explicit_single_subject = ('single subject' in ad_low or ad_low.startswith(('none', 'single'))) and (not slot2_is_dual_subject) and (max_subj_tag < 2)
    has_two_person_combat = bool(
        re.search(
            r'(?i)\b(?:brawl(?:ing)?|fistfight|bar\s+fight|street\s+fight|duel(?:ing)?\s+(?:with|against)|sparring\s+with|fighting\s+(?:with|against)\s+(?:a|an|the|another|his|her|two)|clashing\s+with|wrestling\s+with|grappling\s+with|slagsmål|krogslagsmål|duell(?:erar)?\s+med|slåss\s+mot)\b',
            raw_u,
        )
    )
    is_brawl = st_low.startswith('epic_battlefield') or has_two_person_combat
    is_intimate = st_low.startswith(('nsfw_solo_or_couple', 'nsfw_threesome', 'nsfw_orgy')) or bool(
        re.search(r'(?i)\b(?:making\s+love|lovemaking|having\s+sex|intercourse|passionate\s+kiss(?:ing)?|kissing\s+(?:a|her|his|their)|embracing|cuddling|lovers|romantic\s+couple|threesome|foursome|orgy|gangbang|harem|älskog|älskar|kärlekspar|trekant|orgie)\b', raw_u)
    )
    is_bar = bool(
        re.search(r'(?i)\b(?:bar|tavern|pub|nightclub|club\s+lounge|saloon|inn|bartender|barstool|barhäng|taverna|krog|nattklubb)\b', raw_u)
    )
    is_city = bool(
        re.search(r'(?i)\b(?:city\s+street|busy\s+street|downtown|marketplace|bazaar|plaza|town\s+square|sidewalk|crosswalk|pedestrians|urban\s+crowd|stadsvy|stadsgata|torg|marknad|folkmassa|stadsmyller)\b', raw_u)
    )
    is_dialogue = bool(
        re.search(r'(?i)\b(?:interview(?:ing|s|ed)?|co-?anchor|co-?host|talk\s+show|podcast|debate|conversing\s+with|talking\s+(?:with|to)|chatting\s+with|sitting\s+(?:across\s+from|beside|next\s+to)\s+(?:a|an|the|another|her|his)|intervju(?:ar)?|samtal(?:ar)?|pratar\s+med)\b', raw_u)
    )
    is_studio = bool(
        re.search(r'(?i)\b(?:broadcast\s+studio|television\s+studio|news\s+desk|concert\s+stage|live\s+audience|studio\s+audience|tv-studio|publik)\b', raw_u)
    )
    if is_explicit_single_subject:
        main_cast_count = 1
    elif st_low.startswith('nsfw_orgy') or re.search(r'(?i)\b(?:orgy|gangbang|harem|orgie|6\+\s*pers)\b', raw_u):
        main_cast_count = max(max_subj_tag, 4)
    elif st_low.startswith('nsfw_threesome') or re.search(r'(?i)\b(?:threesome|foursome|trekant|three\s+(?:characters|people|subjects|lovers|fighters|orcs)|3\s+(?:characters|people|subjects))\b', raw_u):
        main_cast_count = max(max_subj_tag, 3)
    elif max_subj_tag >= 2 or slot2_is_dual_subject or is_dialogue or has_two_person_combat or (is_intimate and not re.search(r'(?i)\b(?:solo|masturbat(?:ing|ion)|alone|ensam)\b', raw_u)) or re.search(r'(?i)\b(?:two\s+(?:characters|people|subjects|women|men|fighters|warriors|lovers|partners|figures)|romantic\s+couple|married\s+couple|co-?star|opponent)\b', raw_u):
        main_cast_count = max(max_subj_tag, 2)
    else:
        main_cast_count = 1
    has_multi_main_cast = (main_cast_count >= 2)
    if is_brawl:
        scene_archetype = 'brawl_combat'
    elif is_intimate:
        scene_archetype = 'intimate_lovemaking'
    elif is_dialogue:
        scene_archetype = 'dialogue_interview'
    elif is_bar:
        scene_archetype = 'bar_social'
    elif is_city:
        scene_archetype = 'city_street'
    elif is_studio:
        scene_archetype = 'studio_stage'
    else:
        scene_archetype = 'solo_or_custom'
    if ex_low.startswith('none_isolated'):
        extras_mode = 'none_isolated_main_cast'
    elif ex_low.startswith('sparse_2_to_4'):
        extras_mode = 'sparse_2_to_4_extras'
    elif ex_low.startswith('social_bar'):
        extras_mode = 'social_bar_tavern_club_patrons'
    elif ex_low.startswith('city_street'):
        extras_mode = 'city_street_pedestrians_crowd'
    elif ex_low.startswith('brawl_combat'):
        extras_mode = 'brawl_combat_fighters_arena'
    elif ex_low.startswith('studio_crew'):
        extras_mode = 'studio_crew_or_audience'
    elif ex_low.startswith('intimate_group'):
        extras_mode = 'intimate_group_companions'
    else:
        explicit_bar_crowd = bool(re.search(r'(?i)\b(?:bartender|bar\s+patrons|tavern\s+patrons|crowded\s+(?:bar|tavern|pub|club|nightclub)|gäster\s+i\s+baren|krogmiljö\s+med\s+gäster)\b', raw_u))
        explicit_city_crowd = bool(re.search(r'(?i)\b(?:pedestrians|urban\s+crowd|crowded\s+street|busy\s+(?:city|street|boulevard|plaza|market)|bustling\s+(?:city|street|market)|myllrande\s+stad|stadsmyller|folkmassa|fotgängare)\b', raw_u))
        if st_low.startswith('standing_social') or explicit_bar_crowd:
            extras_mode = 'social_bar_tavern_club_patrons'
        elif explicit_city_crowd:
            extras_mode = 'city_street_pedestrians_crowd'
        elif st_low.startswith('epic_battlefield') or (is_brawl and re.search(r'(?i)\b(?:battlefield|army|armies|arena\s+crowd|surrounding\s+fighters|slagfält|armé)\b', raw_u)):
            extras_mode = 'brawl_combat_fighters_arena'
        elif st_low.startswith(('nsfw_threesome', 'nsfw_orgy')) or (is_intimate and main_cast_count >= 3):
            extras_mode = 'intimate_group_companions'
        elif is_studio and re.search(r'(?i)\b(?:audience|crowd|spectators|camera\s+crew|publik|åskådare)\b', raw_u):
            extras_mode = 'studio_crew_or_audience'
        elif re.search(r'(?i)\b(?:statister|background\s+extras|bystanders\s+in\s+the\s+background)\b', raw_u):
            extras_mode = 'sparse_2_to_4_extras'
        else:
            extras_mode = 'none_isolated_main_cast'
    has_background_extras = (extras_mode != 'none_isolated_main_cast')
    extras_phrase_map = {
        'sparse_2_to_4_extras': 'with 2 to 4 natural background extras (statister) positioned in the midground and background depth with distinct anatomical separation',
        'social_bar_tavern_club_patrons': 'with lively social bar/tavern patrons, a bartender, and conversing guests (statister) populating the background tables and counter',
        'city_street_pedestrians_crowd': 'with natural city pedestrians and urban street crowd extras (statister) walking through the background street and plaza depth',
        'brawl_combat_fighters_arena': 'with dynamic brawling combatants and arena/battlefield fighters (statister) clashing in the surrounding background environment',
        'studio_crew_or_audience': 'with an engaged studio audience and production crew extras (statister) seated in the background studio depth',
        'intimate_group_companions': 'with sensual adult companions and group participants positioned in cohesive proximity with distinct anatomical separation and zero limb fusion',
    }
    extras_sound_map = {
        'sparse_2_to_4_extras': 'subtle background presence and room ambience',
        'social_bar_tavern_club_patrons': 'lively bar/tavern crowd murmur, clinking glasses, and warm social room acoustics',
        'city_street_pedestrians_crowd': 'authentic urban city street ambience, distant footsteps, and city life acoustics',
        'brawl_combat_fighters_arena': 'visceral combat impacts, crowd commotion, and dynamic brawl foley',
        'studio_crew_or_audience': 'authentic live studio room acoustics and subtle audience presence',
        'intimate_group_companions': 'intimate skin-on-skin contact foley and natural room acoustics',
    }
    extras_phrase = extras_phrase_map.get(extras_mode, '')
    extras_sound = extras_sound_map.get(extras_mode, '')
    clean_u_cast = re.sub(r'(?is)\[MANDATORY MULTI-IMAGE REFERENCE BINDING\]:.*?\n\n', '', raw_u)
    clean_u_cast = re.split(r'(?i)\b(?:Use Reference Slot #1|Preserve the primary character|Use Reference Video Slot #5)\b', clean_u_cast)[0].strip()
    m_subj1_desc = re.search(r'(?i)((?:a|an|the)\s+[^.;\n]{6,140}?),\s*<\s*(?:main[_\s-]*)?subject\s*1\s*>', clean_u_cast)
    if not m_subj1_desc:
        m_subj1_desc = re.search(r'(?i)<\s*(?:main[_\s-]*)?subject\s*1\s*>\s*(?:is\s+|:\s*|,\s*)?((?:a|an|the)\s+[^.;\n]{6,140})', clean_u_cast)
    if not m_subj1_desc:
        m_subj1_desc = re.search(
            r'(?i)^[^a-zA-Z]*((?:a|an|the)\s+[^.;\n]{8,130}?)\s+(?:is\s+seated|seated|sitting|standing|interviewing|talking|conversing|fighting|dueling|kissing|making\s+love)',
            clean_u_cast,
        )
    subj1_summary = re.sub(r'(?i)<\s*(?:main[_\s-]*)?subject\s*\d+\s*>', '', m_subj1_desc.group(1)).strip(' ,.') if m_subj1_desc else ''
    if len(subj1_summary) > 115:
        subj1_summary = subj1_summary[:115].rsplit(' ', 1)[0].strip(' ,.')
    m_subj2_desc = re.search(
        r'(?i)(?:while\s+(?:she|he)\s+is\s+interviewing|interviewing|talking\s+(?:with|to)|conversing\s+with|fighting(?:\s+with|\s+against)?|dueling(?:\s+with)?|kissing|making\s+love\s+(?:with|to)|embracing|beside|next\s+to|across\s+from)\s+((?:a|an|the|another|his|her|two|three)\s+[^.;\n]+?)(?:,\s*<\s*(?:main[_\s-]*)?subject\s*2\s*>|\.\s*|$)',
        clean_u_cast,
    )
    if not m_subj2_desc:
        m_subj2_desc = re.search(r'(?i)((?:a|an|the)\s+[^.;\n]{4,110}?),\s*<\s*(?:main[_\s-]*)?subject\s*2\s*>', clean_u_cast)
    if not m_subj2_desc:
        m_subj2_desc = re.search(r'(?i)<\s*(?:main[_\s-]*)?subject\s*2\s*>\s*(?:is\s+|:\s*|,\s*)?((?:a|an|the)\s+[^.;\n]{4,110})', clean_u_cast)
    subj2_summary = re.sub(r'(?i)<\s*(?:main[_\s-]*)?subject\s*\d+\s*>', '', m_subj2_desc.group(1)).strip(' ,.') if m_subj2_desc else ''
    if len(subj2_summary) > 125:
        subj2_summary = subj2_summary[:125].rsplit(' ', 1)[0].strip(' ,.')

    main_subjects_list = []
    for k_idx in range(1, main_cast_count + 1):
        if k_idx == 1:
            k_desc = subj1_summary or 'primary foreground protagonist from Reference Slot 1'
        elif k_idx == 2:
            k_desc = subj2_summary or 'distinct second foreground co-star with their own individual identity and attire from prompt/Slot 2'
        else:
            m_k = re.search(rf'(?i)<\s*(?:main[_\s-]*)?subject\s*{k_idx}\s*>\s*(?:is\s+|:\s*|,\s*)?([^.;\n]{{4,100}})', clean_u_cast)
            if not m_k:
                m_k = re.search(rf'(?i)((?:a|an|the)\s+[^.;\n]{{4,100}}?),\s*<\s*(?:main[_\s-]*)?subject\s*{k_idx}\s*>', clean_u_cast)
            k_desc = re.sub(r'(?i)<\s*(?:main[_\s-]*)?subject\s*\d+\s*>', '', m_k.group(1)).strip(' ,.') if m_k else f'distinct foreground main character #{k_idx} as specified in the prompt'
        main_subjects_list.append({'index': k_idx, 'tag': f'<Main_Subject {k_idx}>', 'desc': k_desc})

    active_extra_roles_map = {
        'sparse_2_to_4_extras': [
            'active background extra moving naturally in the midground environment',
            'secondary background extra observing and interacting in the background depth',
        ],
        'social_bar_tavern_club_patrons': [
            'active bartender pouring drinks and tending the bar counter in the background',
            'active bar patrons conversing and clinking glasses at the background tables',
        ],
        'city_street_pedestrians_crowd': [
            'active city pedestrian walking across the background street depth',
            'active urban bystander moving naturally through the background plaza',
        ],
        'brawl_combat_fighters_arena': [
            'active combatant clashing weapons in the midground arena',
            'active brawling fighter grappling and trading blows in the background',
        ],
        'studio_crew_or_audience': [
            'active studio camera operator tracking the broadcast desk in the background',
            'active live studio audience member reacting in the background seating',
        ],
        'intimate_group_companions': [
            'active adult companion participating closely in the midground',
            'secondary adult companion moving with distinct anatomical separation',
        ],
    }
    raw_active_extras = []
    if main_subj_tags and legacy_subj_tags:
        for s_idx in sorted(set(legacy_subj_tags)):
            m_ex = re.search(rf'(?i)<\s*subject\s*{s_idx}\s*>\s*(?:is\s+|:\s*|,\s*)?([^.;\n]{{4,100}})', clean_u_cast)
            if not m_ex:
                m_ex = re.search(rf'(?i)((?:a|an|the)\s+[^.;\n]{{4,100}}?),\s*<\s*subject\s*{s_idx}\s*>', clean_u_cast)
            ex_d = m_ex.group(1).strip(' ,.') if m_ex else f'active background extra #{s_idx}'
            raw_active_extras.append(ex_d)
    for m_bg_act in re.finditer(
        r'(?i)\b(?:in\s+the\s+background|behind\s+(?:her|him|them)|at\s+the\s+bar|in\s+the\s+crowd|meanwhile)\s*,?\s*((?:a|an|the|two|three|several)\s+[^.;\n]{8,95})',
        clean_u_cast,
    ):
        cand_act = re.sub(r'(?i)<\s*(?:main[_\s-]*)?subject\s*\d+\s*>', '', m_bg_act.group(1)).strip(' ,.')
        if cand_act and cand_act not in raw_active_extras:
            raw_active_extras.append(cand_act)
    if has_background_extras and not raw_active_extras:
        raw_active_extras.extend(active_extra_roles_map.get(extras_mode, []))
    active_extra_subjects = [
        {'index': idx_e + 1, 'tag': f'<Subject {idx_e + 1}>', 'desc': desc_e}
        for idx_e, desc_e in enumerate(raw_active_extras)
    ]
    active_subject_count = len(active_extra_subjects)
    if active_extra_subjects:
        active_subj_tags_str = '; '.join([f"{item['tag']} ({item['desc']})" for item in active_extra_subjects])
        extras_phrase = f"{extras_phrase} [{active_subj_tags_str}]" if extras_phrase else f"with active background extras [{active_subj_tags_str}]"

    clip77_split_header = ''
    if has_multi_main_cast:
        s1_short = subj1_summary if subj1_summary else 'the primary character from Reference Slot 1'
        s2_short = subj2_summary if subj2_summary else 'a distinct second main character with their own individual appearance and attire from the prompt'
        extra_main_str = (
            '; ' + '; '.join([f"{m['tag']} ({m['desc']})" for m in main_subjects_list[2:]])
            if len(main_subjects_list) > 2 else ''
        )
        clip77_split_header = (
            f"MULTI-CHARACTER SCENE ({main_cast_count} MAIN SUBJECTS): "
            f"ON THE LEFT is <Main_Subject 1> ({s1_short}); "
            f"ON THE RIGHT is <Main_Subject 2> ({s2_short}, a separate individual with their own facial identity and attributes as specified in the prompt — never a cloned duplicate of <Main_Subject 1>){extra_main_str}."
        )
        subj2_distinct_clause = (
            f"On the right side of the frame is <Main_Subject 2> ({subj2_summary}), rendered with their own individual facial identity, morphology, and attire as specified in the prompt — never an identical clone of <Main_Subject 1>"
            if subj2_summary else
            "On the right side of the frame is <Main_Subject 2>, rendered with their own distinct individual facial identity, morphology, and attire as specified in the prompt — never an identical clone of <Main_Subject 1>"
        )
        if scene_archetype == 'brawl_combat':
            cast_b1 = f"Dynamic foreground multi-character combat framing in razor-sharp 35mm f/5.6 deep focus: on the left is <Main_Subject 1> ({s1_short}) and on the right is <Main_Subject 2> ({s2_short}) engaging face-to-face on the exact same foreground combat plane at matching full-scale proportions ({subj2_distinct_clause})"
        elif scene_archetype == 'intimate_lovemaking':
            cast_b1 = f"Intimate foreground {main_cast_count}-character framing in razor-sharp 35mm f/5.6 deep focus where <Main_Subject 1> ({s1_short}) on the left and <Main_Subject 2> ({s2_short}) on the right share the exact same foreground plane in close physical contact with distinct anatomical separation and zero limb fusion ({subj2_distinct_clause})"
        elif scene_archetype == 'dialogue_interview':
            cast_b1 = f"Balanced foreground {main_cast_count}-character framing in razor-sharp 35mm f/5.6 deep focus: on the left is <Main_Subject 1> ({s1_short}) and on the right is <Main_Subject 2> ({s2_short}) positioned side-by-side on the exact same foreground plane at matching co-star scale ({subj2_distinct_clause})"
        else:
            cast_b1 = f"Balanced foreground {main_cast_count}-character composition in razor-sharp 35mm f/5.6 deep focus keeping all {main_cast_count} main subjects ({', '.join([m['tag'] for m in main_subjects_list])}) on the same foreground plane at matching scale ({subj2_distinct_clause})"
        if extras_phrase:
            cast_b1 = f'{cast_b1}, {extras_phrase}.'
        else:
            cast_b1 = f'{cast_b1} (strictly {main_cast_count} distinct foreground main subjects, zero unrequested background heads).'
    elif extras_phrase:
        cast_b1 = f'Foreground protagonist <Main_Subject 1> in razor-sharp focus {extras_phrase}.'
    else:
        cast_b1 = ''
    vlm_cast_lines = []
    if has_multi_main_cast:
        vlm_cast_lines.append(
            f'- DYNAMIC MULTI-CHARACTER FOREGROUND CAST ({main_cast_count} DISTINCT MAIN SUBJECTS — ARCHETYPE: {scene_archetype.upper()}): Increment <Main_Subject 1> through <Main_Subject {main_cast_count}> for each foreground protagonist. Stage <Main_Subject 1> ({subj1_summary or "primary character"}) on the left and <Main_Subject 2>'
            + (f' ({subj2_summary})' if subj2_summary else '')
            + (', plus ' + ', '.join([f"{m['tag']} ({m['desc']})" for m in main_subjects_list[2:]]) if len(main_subjects_list) > 2 else '')
            + ' on the right on the EXACT SAME FOREGROUND PLANE in razor-sharp 35mm f/5.6 deep focus at matching full-scale proportions. CRITICAL INDIVIDUALITY RULE: Each <Main_Subject k> is a distinct individual — bind Reference Slot #1 strictly to <Main_Subject 1>, and render <Main_Subject 2> strictly according to <Main_Subject 2>\'s own description in the user prompt (preserving each character\'s own prompted morphology, gender, and attire) without cloning <Main_Subject 1>\'s exact face onto <Main_Subject 2>!'
        )
    if extras_phrase:
        vlm_cast_lines.append(
            f'- ACTIVE BACKGROUND EXTRAS / STATISTER ({extras_mode} — {active_subject_count} ACTIVE SUBJECTS): Increment <Subject 1> through <Subject {max(1, active_subject_count)}> for each active background extra (statist) performing an action in the scene ({extras_phrase}), keeping <Subject m> background extras visually distinct from the foreground <Main_Subject k> protagonists.'
        )
    elif not has_multi_main_cast:
        vlm_cast_lines.append(
            '- ISOLATED SOLO CAST (none_isolated_main_cast): Render strictly ONE unified foreground protagonist (<Main_Subject 1>) in frame with zero unrequested background characters or extra heads.'
        )
    if has_multi_main_cast and has_background_extras:
        continuity_lock = f'Maintain all {main_cast_count} distinct foreground protagonists (<Main_Subject 1> .. <Main_Subject {main_cast_count}>) in razor-sharp f/5.6 deep focus on the same foreground plane alongside the {active_subject_count} active background extras (<Subject 1> .. <Subject {max(1, active_subject_count)}>)'
    elif has_multi_main_cast:
        continuity_lock = f'Maintain all {main_cast_count} distinct foreground protagonists (<Main_Subject 1> on the left and <Main_Subject 2> on the right) in razor-sharp f/5.6 deep focus on the same foreground plane at matching scale without cloning <Main_Subject 1>\'s face onto <Main_Subject 2>'
    elif has_background_extras:
        continuity_lock = f'Maintain the foreground protagonist <Main_Subject 1> in sharp focus while preserving the {active_subject_count} active background extras (<Subject 1> .. <Subject {max(1, active_subject_count)}>) in the environment'
    else:
        continuity_lock = 'Maintain one single unified protagonist (<Main_Subject 1>) in frame'
    return {
        'main_cast_count': main_cast_count,
        'main_subjects': main_subjects_list,
        'active_subject_count': active_subject_count,
        'active_subjects': active_extra_subjects,
        'has_multi_main_cast': has_multi_main_cast,
        'scene_archetype': scene_archetype,
        'extras_mode': extras_mode,
        'has_background_extras': has_background_extras,
        'extras_phrase': extras_phrase,
        'extras_sound': extras_sound,
        'subj1_summary': subj1_summary,
        'subj2_summary': subj2_summary,
        'clip77_split_header': clip77_split_header,
        'cast_b1_injection': cast_b1,
        'cast_vlm_directive': '\n'.join(vlm_cast_lines),
        'cast_continuity_lock': continuity_lock,
    }


def _resolve_3axis_director_directives(subject_stance_posture: str = '', body_choreography_preset: str = '', camera_trajectory_arc: str = '', user_scene_input: str = '', background_extras_crowd: str = '', slot2_is_dual_subject: bool = False, age_difference: str = '') -> dict:
    st_low = str(subject_stance_posture or '').strip().lower()
    ch_low = str(body_choreography_preset or '').strip().lower()
    arc_low = str(camera_trajectory_arc or '').strip().lower()
    u_low = str(user_scene_input or '').strip().lower()
    cast_info = _analyze_scene_cast_and_extras(user_scene_input, subject_stance_posture, background_extras_crowd, slot2_is_dual_subject=slot2_is_dual_subject, age_difference=age_difference)
    is_crowd = any(st_low.startswith(k) for k in ('standing_social', 'epic_battlefield', 'nsfw_threesome', 'nsfw_orgy')) or bool(cast_info['has_background_extras']) or bool(cast_info['has_multi_main_cast'])
    force_cam = (bool(arc_low) and not arc_low.startswith(('follow_02', 'auto'))) or st_low.startswith('story_vehicle') or ch_low.startswith(('running_action', 'catwalk_runway', 'story_multi_act'))
    sit_phrase = 'seated naturally in a grounded, comfortable sitting posture matching the scene environment'
    stance_map = {
        'standing_upright': 'standing tall and upright in a grounded full-posture stance',
        'sitting_table_bar_or_cockpit': sit_phrase,
        'reclining_lounging': 'reclining comfortably in a relaxed lounging posture',
        'lying_horizontal': 'lying horizontally in a supple reclined position',
        'kneeling_crouching': 'poised in an intentional kneeling or low crouching stance',
        'standing_social_bar_or_city': 'standing in sharp foreground focus with lively social companions and patrons visible in the background depth',
        'epic_battlefield_army': 'standing as a heroic foreground commander in razor-sharp focus with a massive battlefield army formation fighting in the background',
        'story_vehicle_or_scene_transition': 'executing a multi-act spatial progression transitioning smoothly across environments or into a vehicle/mount as described in the prompt',
        'nsfw_solo_or_couple': 'staged in an uninhibited 1-to-2 subject intimate adult posture with natural skin contact and coherent anatomical proportions following the user prompt',
        'nsfw_threesome_or_group': 'staged in a multi-subject 3-to-5 person intimate adult group composition with distinct anatomical separation and zero limb fusion following the user prompt',
        'nsfw_orgy_or_harem_scene': 'staged in a multi-subject 6+ person adult ensemble composition with coherent companions and zero limb fusion following the user prompt',
    }
    stance_transition_map = {
        'standing_upright': 'smoothly transitions from the initial starting pose of <Picture 1> (Frame 0) into a tall, grounded upright standing stance',
        'sitting_table_bar_or_cockpit': f'smoothly transitions from the initial starting pose of <Picture 1> (Frame 0) into {sit_phrase}',
        'reclining_lounging': 'smoothly leans back and transitions from the initial starting pose of <Picture 1> (Frame 0) into a relaxed reclining lounging posture',
        'lying_horizontal': 'smoothly lowers and transitions from the initial starting pose of <Picture 1> (Frame 0) into a supple horizontal lying position',
        'kneeling_crouching': 'smoothly lowers their center of gravity and transitions from the initial starting pose of <Picture 1> (Frame 0) down into an intentional kneeling or low crouching stance',
        'standing_social_bar_or_city': 'smoothly transitions from the initial starting pose of <Picture 1> (Frame 0) into a poised foreground standing stance while social companions animate in the background depth',
        'epic_battlefield_army': 'smoothly transitions from the initial starting pose of <Picture 1> (Frame 0) into a commanding heroic battlefield stance as the army clashes in the background',
        'story_vehicle_or_scene_transition': 'initiates the multi-act spatial progression from the initial starting pose of <Picture 1> (Frame 0), moving naturally into the prompted environment or vehicle transition',
        'nsfw_solo_or_couple': 'smoothly transitions from the initial starting pose of <Picture 1> (Frame 0) into the prompted intimate adult posture with natural skin physics and coherent anatomical proportions',
        'nsfw_threesome_or_group': 'smoothly transitions from the initial starting pose of <Picture 1> (Frame 0) into the prompted 3-to-5 person intimate group posture with distinct anatomical separation',
        'nsfw_orgy_or_harem_scene': 'smoothly transitions from the initial starting pose of <Picture 1> (Frame 0) into the prompted 6+ person adult ensemble posture with coherent companions and zero limb fusion',
    }
    choreo_map = {
        'dance_music_video_groove': 'executing beat-synchronized music video dance choreography with rhythmic shoulder, torso, and hip groove',
        'dance_sensual_club': 'performing fluid sensual club dance movements with smooth body-rolls and rhythmic hip-sway',
        'catwalk_runway_strut': 'striding forward directly toward the retreating camera lens in a confident runway catwalk strut',
        'running_action_sprint': 'sprinting forward at high velocity with dynamic athletic stride and natural momentum',
        'combat_guard_and_parry': 'executing poised martial combat guard, defensive parries, and agile close-quarters footwork',
        'combat_heavy_weapon_strikes': 'unleashing powerful heavy weapon strikes and fluid attack combinations while keeping facial features clear',
        'social_toast_dining_chat': 'raising a glass in a social toast, drinking, conversing, and gesturing naturally',
        'story_multi_act_progression': 'progressing chronologically across distinct narrative acts (Act 1 setup ➔ Act 2 transition ➔ Act 3 culmination) faithful to the user prompt',
        'nsfw_sensual_solo_tease': 'performing unhurried sensual solo posing, supple spine and hip articulation, natural breathing, and alluring expressive gaze faithful to the user prompt',
        'nsfw_rhythmic_intimate_motion': 'maintaining continuous rhythmic intimate pelvic and torso motion with natural skin-on-skin physics, synchronized breathing, and coherent anatomical contact faithful to the user prompt',
    }
    arc_map = {
        'backward_track_low_to_high': 'smooth backward-tracking dolly retreating ahead of the subject while sweeping vertically from a low heroic angle up to a high angle (100% front-facing face visibility)',
        'backward_track_mid_to_low': 'smooth backward-tracking dolly retreating ahead of the subject while descending from eye-level mid-angle down to a low heroic angle (100% front-facing face visibility)',
        'backward_track_low_to_mid': 'smooth backward-tracking dolly retreating ahead of the subject while rising from a low angle to steady eye-level mid-framing (100% front-facing face visibility)',
        'backward_track_high_to_low': 'smooth backward-tracking dolly retreating ahead of the subject while sweeping from an elevated high angle down to a low heroic angle (100% front-facing face visibility)',
        'backward_track_mid_to_mid': 'smooth eye-level backward-tracking Steadicam retreating at constant distance ahead of the forward-moving subject (100% front-facing face visibility)',
        'outro_track_to_follow_low_to_high': 'front-facing backward-tracking dolly in Shots 1–2 that smoothly orbits 180 degrees in Shot 3 into a rear follow-cam rising from low to high angle as the subject moves toward the horizon',
        'outro_track_to_follow_mid_to_mid': 'front-facing eye-level backward-tracking dolly in Shots 1–2 that smoothly arcs 180 degrees in Shot 3 into an eye-level rear follow-cam behind the subject moving into the environment',
        'outro_track_to_follow_mid_to_low': 'front-facing mid-angle backward-tracking dolly in Shots 1–2 that smoothly arcs 180 degrees in Shot 3 into a low-angle rear follow-cam behind the departing subject',
        'outro_track_to_follow_low_to_low': 'front-facing low-angle backward-tracking dolly in Shots 1–2 that smoothly arcs 180 degrees in Shot 3 into a low-angle rear follow-cam behind the departing subject',
        'crane_ascent_street_to_aerial': 'continuous cinema crane and drone ascent starting at ground level in Shot 1 and rising high into a sweeping aerial view by the final shot',
    }
    stance_neg_map = {
        'standing_upright': '(sitting down, seated on chair, lying down, kneeling on floor, crouching low:1.65)',
        'sitting_table_bar_or_cockpit': '(standing upright, standing tall, walking across room, running sprint, lying flat on floor:1.70)',
        'reclining_lounging': '(standing upright, standing tall, stiff rigid upright posture, running sprint:1.70)',
        'lying_horizontal': '(standing upright, standing tall, walking around, seated upright at desk, running:1.75)',
        'kneeling_crouching': '(standing upright, standing tall, seated high on chair, walking tall:1.75)',
        'standing_social_bar_or_city': '(empty deserted void background, isolated empty room without background depth:1.55)',
        'epic_battlefield_army': '(peaceful empty studio room, isolated indoor portrait without battlefield depth:1.60)',
        'story_vehicle_or_scene_transition': '(frozen static room, motionless background without spatial progression:1.60)',
        'nsfw_solo_or_couple': '(censored, mosaic censorship, bar censor, stiff mannequin pose, unrequested extra crowd heads, fused limbs:1.75)',
        'nsfw_threesome_or_group': '(censored, mosaic censorship, solo isolated single person only, fused bodies, merged limbs, extra disembodied heads:1.75)',
        'nsfw_orgy_or_harem_scene': '(censored, mosaic censorship, solo isolated single person only, empty background, fused bodies, merged limbs:1.75)',
    }
    stance_conflict_map = {
        'standing_upright': (
            r'(?i)\b(?:sitting\s+(?:down|on|in|at)|seated\s+(?:on|in|at)|lying\s+(?:down|flat|horizontally)|kneeling\s+(?:down|low|on))\b',
            'standing tall and upright in a grounded stance',
        ),
        'sitting_table_bar_or_cockpit': (
            r'(?i)\b(?:standing\s+tall(?:\s+and\s+upright)?|stands?\s+tall(?:\s+and\s+upright)?|standing\s+upright|staying\s+upright|walking\s+across\s+the\s+room)\b',
            'remaining comfortably seated in a grounded sitting posture',
        ),
        'reclining_lounging': (
            r'(?i)\b(?:standing\s+tall(?:\s+and\s+upright)?|stands?\s+tall(?:\s+and\s+upright)?|standing\s+upright|staying\s+upright)\b',
            'reclining comfortably in a relaxed lounging posture',
        ),
        'lying_horizontal': (
            r'(?i)\b(?:standing\s+tall(?:\s+and\s+upright)?|stands?\s+tall(?:\s+and\s+upright)?|standing\s+upright|staying\s+upright|walking\s+across)\b',
            'lying horizontally in a supple reclined position',
        ),
        'kneeling_crouching': (
            r'(?i)\b(?:standing\s+tall(?:\s+and\s+upright)?|stands?\s+tall(?:\s+and\s+upright)?|standing\s+in\s+a\s+wide(?:\s*,\s*grounded)?\s+combat\s+stance(?:\s+with\s+one\s+leg\s+raised)?|in\s+her\s+grounded\s+raised-leg\s+stance|standing\s+upright|staying\s+upright(?:\s+in\s+frame)?)\b',
            'kneeling low on the knees in a grounded crouching posture',
        ),
    }
    choreo_neg_map = {
        'dance_music_video_groove': '(static frozen pose, motionless body, stiff rigid torso, standing still like a statue:1.75)',
        'dance_sensual_club': '(static frozen pose, stiff wooden hips, motionless rigid torso, robotic stillness:1.75)',
        'catwalk_runway_strut': '(standing stationary in place, sitting down, walking backward away from camera, static pose:1.70)',
        'running_action_sprint': '(standing still, slow sluggish walk, sitting down, static frozen legs, motionless pose:1.80)',
        'combat_guard_and_parry': '(passive relaxed slouching, hands in pockets, lifeless static posture:1.70)',
        'combat_heavy_weapon_strikes': '(passive motionless stance, limp arms, weak sluggish swing, static frozen pose:1.75)',
        'social_toast_dining_chat': '(frozen mannequin hands, stiff robotic arms, combat weapon swinging:1.60)',
        'story_multi_act_progression': '(frozen repetitive loop, identical static pose across all shots:1.65)',
        'nsfw_sensual_solo_tease': '(stiff rigid mannequin pose, frozen hips, lifeless static body, abrupt jerky twitching:1.75)',
        'nsfw_rhythmic_intimate_motion': '(static frozen pose, motionless hips, stiff rigid pelvis, frozen statue stillness, broken anatomical contact, detached floating limbs:1.85)',
    }
    arc_neg_map = {
        'backward_track_low_to_high': '(static locked-off camera, turned back, rear view, back of head, zoom-in on forehead:1.65)',
        'backward_track_mid_to_low': '(static locked-off camera, turned back, rear view, back of head, zoom-in on forehead:1.65)',
        'backward_track_low_to_mid': '(static locked-off camera, turned back, rear view, back of head, zoom-in on forehead:1.65)',
        'backward_track_high_to_low': '(static locked-off camera, turned back, rear view, back of head, zoom-in on forehead:1.65)',
        'backward_track_mid_to_mid': '(static locked-off camera, turned back, rear view, back of head, zoom-in on forehead:1.65)',
        'outro_track_to_follow_low_to_high': '(static locked-off tripod camera without movement, abrupt jump cut:1.60)',
        'outro_track_to_follow_mid_to_mid': '(static locked-off tripod camera without movement, abrupt jump cut:1.60)',
        'outro_track_to_follow_mid_to_low': '(static locked-off tripod camera without movement, abrupt jump cut:1.60)',
        'outro_track_to_follow_low_to_low': '(static locked-off tripod camera without movement, abrupt jump cut:1.60)',
        'crane_ascent_street_to_aerial': '(static locked-off eye-level tripod camera, cramped indoor close-up in final shot:1.65)',
    }
    st_key = next((k for k in stance_map if st_low.startswith(k)), '')
    ch_key = next((k for k in choreo_map if ch_low.startswith(k)), '')
    arc_key = next((k for k in arc_map if arc_low.startswith(k)), '')
    st_phrase = stance_map.get(st_key, '')
    st_trans_phrase = stance_transition_map.get(st_key, '')
    ch_phrase = choreo_map.get(ch_key, '')
    arc_phrase = arc_map.get(arc_key, '')
    st_neg = stance_neg_map.get(st_key, '')
    ch_neg = choreo_neg_map.get(ch_key, '')
    arc_neg = arc_neg_map.get(arc_key, '')
    (st_conf_pat, st_conf_repl) = stance_conflict_map.get(st_key, ('', ''))
    combined_3ax_neg = ', '.join([x for x in (st_neg, ch_neg, arc_neg) if x])
    vlm_lines = []
    if st_phrase:
        vlm_lines.append(
            f'- MANDATORY VIDEO POSTURE PROGRESSION ({st_key}): In BLOCK 1 ([IMAGE]), preserve the original starting pose from the reference image if provided, or follow the user prompt in T2I mode. In BLOCK 2 (VIDEO TIMELINE), start [Shot 1] from Frame 0 and animate <Subject 1> as they {st_trans_phrase}, then maintain {st_phrase} across subsequent shots while prioritizing all specific actions in the user prompt.'
        )
    if ch_phrase:
        vlm_lines.append(f'- MANDATORY BODY_CHOREOGRAPHY ({ch_key}): Animate the cast {ch_phrase} while faithfully executing every specific beat written in the user prompt.')
    if arc_phrase:
        vlm_lines.append(f'- MANDATORY CAMERA_TRAJECTORY_ARC ({arc_key}): Execute {arc_phrase}.')
    if cast_info['cast_vlm_directive']:
        vlm_lines.append(cast_info['cast_vlm_directive'])
    return {
        'stance_key': st_key,
        'choreo_key': ch_key,
        'arc_key': arc_key,
        'stance_phrase': st_phrase,
        'stance_transition_phrase': st_trans_phrase,
        'choreo_phrase': ch_phrase,
        'arc_phrase': arc_phrase,
        'stance_neg_tokens': st_neg,
        'choreo_neg_tokens': ch_neg,
        'arc_neg_tokens': arc_neg,
        'combined_3axis_neg': combined_3ax_neg,
        'stance_conflict_pat': st_conf_pat,
        'stance_conflict_repl': st_conf_repl,
        'is_multi_subject_crowd': is_crowd,
        'is_outro_follow': arc_key.startswith('outro_track_to_follow'),
        'force_camera_move': force_cam,
        'cast_info': cast_info,
        'vlm_directive': '\n'.join(vlm_lines),
    }


_EXPLICIT_EROTIC_PROMPT_REGEX = re.compile(
    r'(?i)\b(?:nude|nudity|naked|topless|bottomless|unclothed|undressed|strip(?:ping|ped|s)?|nip\s*slip|nipples?|areolas?|pussy|vagina|labia|vulva|clit(?:oris)?|penis|dick|cock|erection|phallus|testicles?|balls|anus|anal|genitals?|genitalia|sex|sexual|intercourse|penetration|penetrat(?:ing|ed)|blowjob|fellatio|cunnilingus|masturbat(?:ion|ing)|orgasm|climax|cum(?:ming)?|semen|sperm|ejaculat(?:ion|ing)|milky\s+liquid|spread\s+legs|making\s+love|lovemaking|threesome|foursome|orgy|gangbang|harem|naken|nakna|avklädd|klär\s+av\s+sig|tar\s+av\s+sig|älskog|älskar|knulla(?:r|nde)?|suger|slickar|stönar|bröstvårt\w*|fitta\w*|kuk\w*|slida\w*|trekant|orgie|erotisk\w*)\b'
)
_EXPLICIT_CAMERA_MOTION_PROMPT_REGEX = re.compile(
    r'(?i)(?<!no\s)(?<!zero\s)(?<!without\s)\b(?:dolly[-\s]?in|dolly[-\s]?out|push[-\s]?in|pull[-\s]?out|zoom[-\s]?in|zoom[-\s]?out|zooms?\s+in|zooms?\s+out|zooming\s+in|zooming\s+out|camera\s+(?:pans?|panning|orbits?|orbiting|tracks?|tracking|zooms?|zooming|pushes\s+in|pulls\s+out|glides?|moves?|tilts?)|panning\s+shot|tracking\s+shot|360[-\s]?degree\s+orbit|crane[-\s]?up|whip[-\s]?pan|fpv\s+drone|zooma(?:r)?\s+in|zooma(?:r)?\s+ut|panorera(?:r)?|kamerarörelse|kamera\s+förflyttning)\b'
)


def _is_intentional_camera_movement_requested(camera_movement_sel: str, custom_camera_movement: str = '', user_scene_input: str = '') -> bool:
    sel_low = str(camera_movement_sel or '').strip().lower()
    cust_low = str(custom_camera_movement or '').strip().lower()
    clean_user_txt = re.split(r'(?i)\[SUNO\s+RHYTHMIC', str(user_scene_input or ''))[0]
    prompt_has_cam = bool(_EXPLICIT_CAMERA_MOTION_PROMPT_REGEX.search(clean_user_txt))
    if sel_low == 'random':
        return True
    if sel_low == 'custom' and cust_low:
        return not any(k in cust_low for k in ('locked-off', 'locked off', 'static', 'tripod', 'constant distance', 'statisk', 'ingen'))
    if prompt_has_cam:
        return True
    if not sel_low or 'locked-off' in sel_low or 'static' in sel_low or 'statisk' in sel_low:
        return False
    if sel_low == 'steady 85mm portrait lens at f/1.4 slowly drifting in a dolly-in motion':
        return False
    return True


def _prompt_requests_explicit_erotica(user_scene_input: str) -> bool:
    return bool(_EXPLICIT_EROTIC_PROMPT_REGEX.search(str(user_scene_input or '')))


def _resolve_content_rating_tier(content_rating_mode: str, user_scene_input: str = '', subject_stance_posture: str = '', body_choreography_preset: str = '', background_extras_crowd: str = '') -> str:
    m_low = str(content_rating_mode or '').strip().lower()
    if m_low.startswith('sfw'):
        return 'sfw'
    if 'explicit' in m_low or 'erotic' in m_low or m_low.startswith('nsfw'):
        return 'nsfw_explicit'
    st_low = str(subject_stance_posture or '').strip().lower()
    ch_low = str(body_choreography_preset or '').strip().lower()
    ex_low = str(background_extras_crowd or '').strip().lower()
    if st_low.startswith('nsfw_') or ch_low.startswith('nsfw_') or ex_low.startswith('intimate_group') or _prompt_requests_explicit_erotica(user_scene_input):
        return 'nsfw_explicit'
    if m_low.startswith('uncensored'):
        return 'uncensored_action'
    return 'uncensored_action'


def _resolve_audio_soundtrack_mode(audio_soundtrack_mode: str, clean_in: str = '') -> str:
    m_low = str(audio_soundtrack_mode or '').strip().lower()
    if m_low.startswith('sfx_only'):
        return 'sfx_only'
    if m_low.startswith('sfx_and_speech'):
        return 'sfx_and_speech'
    if m_low.startswith('instrumental_bgm'):
        return 'instrumental_bgm'
    if m_low.startswith('bgm_with_vocals'):
        return 'bgm_with_vocals'
    in_low = str(clean_in or '').lower()
    if re.search(r'(?i)\b(?:singing|sings|sung|vocalist|lead\s+vocals|song\s+lyrics|choir|ballad|lip[-\s]?sync|suno\s+rhythmic|sjunger|sjunga|sång)\b', in_low):
        return 'bgm_with_vocals'
    if re.search(r'(?i)\b(?:speaks?|speaking|speech|dialogue|talks?|talking|monologue|whispers?|whispering|pratar|säger|dialog)\b', in_low):
        return 'sfx_and_speech'
    if re.search(r'(?i)\b(?:background\s+music|musical\s+score|orchestral\s+score|soundtrack|orchestra|symphony|synth\s+pad|ambient\s+music|bgm|instrumental\s+music)\b', in_low):
        return 'instrumental_bgm'
    return 'sfx_only'

def _aes256_ctr_decrypt_bytes(data: bytes, key32: bytes, nonce12: bytes, initial_counter: int = 1) -> bytes:
    xtime = lambda a: (a << 1 ^ 27) & 255 if a & 128 else a << 1
    kw = [list(key32[i:i + 4]) for i in range(0, 32, 4)]
    for i in range(8, 60):
        t = list(kw[i - 1])
        if i % 8 == 0:
            t = [_AES_SBOX[t[(j + 1) % 4]] for j in range(4)]
            t[0] ^= _AES_RCON[i // 8]
        elif i % 8 == 4:
            t = [_AES_SBOX[b] for b in t]
        kw.append([kw[i - 8][j] ^ t[j] for j in range(4)])
    rks = [[b for c in range(4) for b in kw[r * 4 + c]] for r in range(15)]
    out = bytearray(len(data))
    counter = int(initial_counter)
    for off in range(0, len(data), 16):
        blk = nonce12 + struct.pack('>I', counter)
        st = [blk[i] ^ rks[0][i] for i in range(16)]
        for rnd in range(1, 14):
            st = [_AES_SBOX[b] for b in st]
            st = [st[0], st[5], st[10], st[15], st[4], st[9], st[14], st[3], st[8], st[13], st[2], st[7], st[12], st[1], st[6], st[11]]
            for c in range(4):
                idx = c * 4
                (s0, s1, s2, s3) = (st[idx], st[idx + 1], st[idx + 2], st[idx + 3])
                tm = s0 ^ s1 ^ s2 ^ s3
                st[idx] ^= tm ^ xtime(s0 ^ s1)
                st[idx + 1] ^= tm ^ xtime(s1 ^ s2)
                st[idx + 2] ^= tm ^ xtime(s2 ^ s3)
                st[idx + 3] ^= tm ^ xtime(s3 ^ s0)
            rk = rks[rnd]
            st = [st[i] ^ rk[i] for i in range(16)]
        st = [_AES_SBOX[b] for b in st]
        st = [st[0], st[5], st[10], st[15], st[4], st[9], st[14], st[3], st[8], st[13], st[2], st[7], st[12], st[1], st[6], st[11]]
        ks = bytes((st[i] ^ rks[14][i] for i in range(16)))
        chunk = data[off:off + 16]
        for (j, b) in enumerate(chunk):
            out[off + j] = b ^ ks[j]
        counter += 1
    return bytes(out)

def _decrypt_ez_aes256_container(b64_envelope: str):
    raw_outer = base64.b64decode(b64_envelope.strip().encode('utf-8'))
    outer = json.loads(raw_outer.decode('utf-8'))
    if outer.get('magic') != 'EZ_AES256_HYBRID_ENC_V2':
        raise ValueError('Unsupported .enc header')
    salt16 = base64.b64decode(outer['salt_b64'])
    nonce12 = base64.b64decode(outer['nonce_b64'])
    tag = base64.b64decode(outer['tag_b64'])
    ciphertext = base64.b64decode(outer['ciphertext_b64'])
    key32 = hashlib.pbkdf2_hmac('sha256', _EZ_MASTER_SALT, salt16, 60000, dklen=32)
    expected_tag = hmac.new(key32, salt16 + nonce12 + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(expected_tag, tag):
        raise PermissionError('AES-256 authentication tag mismatch')
    cipher_mode = outer.get('cipher', 'AES-256-CTR-FIPS197')
    if cipher_mode == 'AES-256-GCM':
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            compressed = AESGCM(key32).decrypt(nonce12, ciphertext, salt16)
        except Exception:
            compressed = _aes256_ctr_decrypt_bytes(ciphertext[:-16], key32, nonce12, initial_counter=2)
    else:
        compressed = _aes256_ctr_decrypt_bytes(ciphertext, key32, nonce12, initial_counter=1)
    inner = json.loads(zlib.decompress(compressed).decode('utf-8'))
    payload = inner['payload']
    sig_bundle = inner.get('hybrid_signature', {})
    canonical_json = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode('utf-8')
    expected_hmac = hmac.new(_EZ_MASTER_SALT, canonical_json, hashlib.sha512).hexdigest()
    if not hmac.compare_digest(expected_hmac, str(sig_bundle.get('hmac_sha512', ''))):
        raise PermissionError('HMAC-SHA512 signature mismatch')
    return payload

def _verify_cinematrix_license_active(search_dirs) -> bool:
    candidates = []
    for d in search_dirs:
        p = Path(d)
        if not p.exists():
            continue
        for name in ('signature.enc', 'license.enc', 'devops_master_license.enc'):
            cand = p / name
            if cand.exists():
                candidates.append(cand)
        for ez_f in p.glob('EZ-T*.enc'):
            candidates.append(ez_f)
    for lic_file in candidates:
        try:
            raw_bytes = lic_file.read_bytes()
            if raw_bytes.startswith(b'EMPIRE_HUD_V82_HYBRID_ENC'):
                body = raw_bytes[len(b'EMPIRE_HUD_V82_HYBRID_ENC'):]
                dec = bytes((b ^ _EZ_MASTER_SALT[i % len(_EZ_MASTER_SALT)] for (i, b) in enumerate(body)))
                legacy_obj = json.loads(zlib.decompress(dec).decode('utf-8'))
                if legacy_obj.get('verification_anchor') == 'EMPIRE_HUD_VERIFIED_RELEASE' or legacy_obj.get('anchor') == 'EMPIRE_HUD_VERIFIED_RELEASE':
                    return True
            payload = _decrypt_ez_aes256_container(raw_bytes.decode('utf-8', errors='ignore'))
            if payload.get('verification_anchor') != 'EMPIRE_HUD_VERIFIED_RELEASE':
                continue
            if str(payload.get('status', 'ACTIVE')).upper() in ('REVOKED', 'EXPIRED'):
                continue
            valid_until = str(payload.get('valid_until', 'PERPETUAL'))
            if valid_until != 'PERPETUAL':
                exp_dt = datetime.strptime(valid_until, '%Y-%m-%d %H:%M:%S')
                if datetime.now() > exp_dt:
                    continue
            return True
        except Exception:
            continue
    return False

def _resolve_dropdown_custom_or_random(selected_val: str, preset_list: list, custom_val: str, rng: random.Random, fallback_default: str) -> str:
    clean_sel = str(selected_val or '').strip()
    clean_custom = str(custom_val or '').strip()
    if clean_sel.lower() == 'custom':
        return clean_custom if clean_custom else fallback_default
    if clean_sel.lower() == 'random':
        pool = [p for p in preset_list if p.lower() not in ('random', 'custom')]
        return rng.choice(pool) if pool else fallback_default
    if clean_custom and clean_sel == fallback_default:
        return clean_custom
    return clean_sel if clean_sel else fallback_default

def _get_default_vault_search_dirs() -> list:
    here = Path(__file__).resolve().parent
    pkg_root = here.parent
    devops_root = pkg_root.parent.parent if (pkg_root.parent.parent / 'CONFIG').exists() else pkg_root
    return [
        pkg_root,
        here,
        devops_root,
        devops_root / 'CONFIG',
        Path('D:/EZ_Studio_DevTools'),
        Path('D:/EZ_Studio_DevTools/CONFIG'),
        Path('D:/EZ_Studio_DevTools/DEV_BEDS/comfyui_node/ez_cinematrix_core'),
    ]


def _load_licensed_allan_ballan_vault(search_dirs=None) -> dict:
    dirs = search_dirs if search_dirs is not None else _get_default_vault_search_dirs()
    if not _verify_cinematrix_license_active(dirs):
        return {}
    for d in dirs:
        enc_file = Path(d) / 'allan_ballan_core.enc'
        if enc_file.exists():
            try:
                vault = _decrypt_ez_aes256_container(enc_file.read_text(encoding='utf-8', errors='ignore'))
                if isinstance(vault, dict) and vault.get('verification_anchor') == 'EMPIRE_HUD_VERIFIED_RELEASE':
                    return vault
            except Exception:
                continue
    return {}


def _load_freemium_light_bundle(search_dirs=None) -> dict:
    dirs = search_dirs if search_dirs is not None else _get_default_vault_search_dirs()
    raw_text = ''
    for d in dirs:
        lt_file = Path(d) / 'system_prompt_light.txt'
        if lt_file.exists():
            try:
                raw_text = lt_file.read_text(encoding='utf-8', errors='ignore').strip()
                if raw_text:
                    break
            except Exception:
                continue
    style_map = {}
    neg_map = {}
    prompt_body = raw_text
    if '[STYLE_PROFILES]' in raw_text:
        parts = raw_text.split('[STYLE_PROFILES]', 1)
        prompt_body = parts[0].strip()
        rest = parts[1]
        if '[NEGATIVE_PROMPT_DEFAULTS]' in rest:
            style_sec, neg_sec = rest.split('[NEGATIVE_PROMPT_DEFAULTS]', 1)
        else:
            style_sec, neg_sec = rest, ''
        for line in style_sec.splitlines():
            if '=' in line:
                k, v = line.split('=', 1)
                style_map[k.strip().lower()] = v.strip()
        for line in neg_sec.splitlines():
            if '=' in line:
                k, v = line.split('=', 1)
                neg_map[k.strip().lower()] = v.strip()
    return {'prompt_body': prompt_body, 'style_map': style_map, 'neg_map': neg_map}


def _extract_prompt_morphology_profile(user_scene_input: str) -> dict:
    raw_u = str(user_scene_input or '').strip()
    raw_u = re.sub(
        r'(?i)while\s+(?:100%\s+|strictly\s+)?(?:prioritizing|preserving)[^.()\n]*?(?:tusks/fangs(?:/horns)?|creature/species\s+morphology)[^.()\n]*',
        '',
        raw_u,
    )
    raw_u = re.sub(r'(?i)\btusks/fangs(?:/horns)?\b', '', raw_u)
    has_boar = bool(re.search(r'(?i)\b(?:vildsvin\w*|boar(?:\s+head|\s+snout|\s+warrior|\s+man|\s+woman|\s+tusks?)?|warthog\w*|razorback|svinhuvud)\b', raw_u))
    has_dragon = bool(re.search(r'(?i)\b(?:dragon\w*|drake|drakar\w*|wyvern|draconic)\b', raw_u))
    has_ogre_troll = bool(re.search(r'(?i)\b(?:ogre\w*|troll\w*|oni\b|cyclops|minotaur\w*)\b', raw_u))
    has_orc = bool(re.search(r'(?i)\b(?:orc\w*|half[-\s]?orc|orch\w*)\b', raw_u))
    has_human = bool(re.search(r'(?i)\b(?:human\w*|människ\w*|normal\s+man|normal\s+woman)\b', raw_u))
    has_tusks = bool(has_boar or has_orc or has_ogre_troll or re.search(r'(?i)\b(?:tusks?|tusked|protruding\s+tusks?|betar\w*|underkäksbetar|vildsvinsbetar)\b', raw_u))
    has_fangs = bool(has_dragon or re.search(r'(?i)\b(?:fangs?|fanged|huggtänder|werewolf|varulv|vampire|vampyr|demon\w*|tiefling)\b', raw_u))
    has_elf_ears = bool(re.search(r'(?i)\b(?:pointed\s+(?:elven[-\s]?like\s+|elf\s+)?ears|elven[-\s]?like\s+ears|elf\s+ears|spetsiga\s+öron)\b', raw_u))
    has_fantasy_anatomy = bool(has_tusks or has_fangs or has_boar or has_dragon or has_ogre_troll or has_orc or has_elf_ears or re.search(r'(?i)\b(?:goblin\w*|beastman|beastwoman|monster|horned|horns|scales|scaled|winged|non[-\s]?human)\b', raw_u))
    ear_sub = ' and long pointed ears' if has_elf_ears else ''
    if has_boar:
        feat_desc = f'a wild boar head with a bristled snout and two sharp protruding white lower-jaw tusks curving upward{ear_sub}'
        neg_guard = '(flat human face without boar snout, missing boar head, missing tusks, no tusks, human mouth without tusks, hidden tusks:1.95)'
    elif has_dragon and not has_tusks:
        feat_desc = f'draconic reptile morphology with textured scales, horns, and sharp protruding jaws and fangs{ear_sub}'
        neg_guard = '(plain human face without draconic features, smooth human skin without scales, missing fangs, missing horns:1.90)'
    elif has_tusks:
        feat_desc = f'two sharp protruding white lower-jaw tusks growing upward out from the lower jaw{ear_sub}'
        human_ear_neg = '' if (has_human and not has_elf_ears) else ', round human ears' if has_elf_ears else ''
        neg_guard = f'(missing tusks, no tusks, mouth without tusks, hidden tusks, closed lips hiding tusks, human teeth without tusks{human_ear_neg}:1.95)'
    elif has_fangs:
        feat_desc = f'sharp protruding fangs visible in the jaw{ear_sub}'
        neg_guard = '(missing fangs, blunt human teeth without fangs, hidden fangs:1.90)'
    else:
        feat_desc = ''
        neg_guard = ''
    return {
        'has_tusks': has_tusks,
        'has_fangs': has_fangs,
        'has_boar': has_boar,
        'has_dragon': has_dragon,
        'has_ogre_troll': has_ogre_troll,
        'has_orc': has_orc,
        'has_human': has_human,
        'has_elf_ears': has_elf_ears,
        'has_fantasy_anatomy': has_fantasy_anatomy,
        'feat_desc': feat_desc,
        'neg_guard': neg_guard,
    }


_SUBJECT_HUMAN_HUMANOID_REGEX = re.compile(
    r'(?i)\b(?:woman|women|man|men|girl|boy|person|people|lady|gentleman|human|humanoid|cyborg|android|elf|elven|orc|half[-\s]?orc|dwarf|goblin|tiefling|vampire|princess|prince|queen|king|priestess|heroine|warrior|knight|bartender|anchor|singer|vocalist|dancer|lover|couple|she|her|he|him|kvinna|kvinnor|manlig|män|tjej|flicka|kille|pojke|människ\w*)\b'
)
_SUBJECT_AVIAN_REGEX = re.compile(
    r'(?i)\b(?:bird|birds|sparrow|robin|finch|swallow|hummingbird|eagle|hawk|falcon|owl|crow|raven|magpie|parrot|macaw|cockatoo|swan|duck|goose|seagull|pigeon|dove|peacock|penguin|phoenix|griffin|fågel|fåglar|sparv|örn|hök|falk|uggla|kråka|korp|skata|papegoja|svan|anka|mås|duva)\b'
)
_SUBJECT_ANIMAL_CREATURE_REGEX = re.compile(
    r'(?i)\b(?:mouse|mice|rat|rats|rodent|hamster|gerbil|squirrel|chipmunk|beaver|rabbit|bunny|hare|hedgehog|ferret|otter|badger|weasel|stoat|cat|cats|kitten|feline|lion|tiger|panther|leopard|cheetah|jaguar|lynx|cougar|dog|dogs|puppy|hound|canine|wolf|wolves|fox|foxes|coyote|bear|bears|panda|koala|horse|stallion|mare|foal|pony|deer|stag|doe|fawn|moose|elk|reindeer|caribou|elephant|rhino|rhinoceros|hippo|giraffe|zebra|bison|buffalo|cow|bull|goat|sheep|ram|pig|boar|hog|monkey|chimp|ape|gorilla|orangutan|lemur|sloth|bat|whale|dolphin|orca|seal|walrus|shark|fish|salmon|koi|goldfish|octopus|squid|jellyfish|crab|lobster|shrimp|turtle|tortoise|frog|toad|salamander|axolotl|snake|serpent|cobra|viper|python|lizard|gecko|iguana|chameleon|crocodile|alligator|dinosaur|raptor|t-rex|trex|dragon|wyvern|hydra|kaiju|butterfly|moth|bee|bumblebee|wasp|beetle|ladybug|ant|spider|tarantula|scorpion|mantis|dragonfly|snail|mus|möss|råtta|råttor|gnagare|ekorre|bäver|kanin|hare|igelkott|utter|grävling|katt|katter|kattunge|lejon|tiger|panter|lodjur|hund|hundar|valp|varg|vargar|räv|björn|häst|hjort|rådjur|älg|ren|elefant|nosörning|flodhäst|giraff|apa|gorilla|val|delfin|säl|haj|fisk|bläckfisk|krabba|sköldpadda|groda|padda|orm|ödla|krokodil|dinosaurie|drake|fjäril|bi|humla|geting|skalbagge|myra|spindel|snigel)\b'
)
_SUBJECT_VEHICLE_OBJECT_REGEX = re.compile(
    r'(?i)\b(?:sports\s+car|race\s+car|vehicle|automobile|sedan|suv|truck|pickup|motorcycle|motorbike|spaceship|starship|spacecraft|fighter\s+jet|airliner|aircraft|helicopter|drone|mecha|submarine|battleship|sailboat|yacht|locomotive|train|sportbil|racerbil|svävare|lastbil|motorcykel|rymdskepp|flygplan|stridsflygplan|helikopter|drönare|ubåt|segelbåt|lokomotiv|tåg)\b'
)
_EXPLICIT_METAMORPHOSIS_REGEX = re.compile(
    r'(?i)\b(?:transform(?:s|ing|ed)?\s+into|morph(?:s|ing|ed)?\s+into|turn(?:s|ing|ed)?\s+into|shapeshift\w*|metamorphos\w*|transmut(?:e|es|ing|ed)\s+into|förvandlas\s+till|förvandlar\s+sig\s+till|blir\s+till\s+en)\b'
)


def _detect_subject_taxonomy_and_species_lock(
    user_scene_input: str = '',
    compiled_raw: str = '',
    subject_1_age: str = '',
    custom_subject_1_age: str = '',
    has_reference_image: bool = False,
) -> dict:
    def _strip_compiler_boilerplate(s_in: str) -> str:
        s0 = str(s_in or '')
        s0 = re.sub(r'(?is)\[MANDATORY MULTI-IMAGE REFERENCE BINDING\]:.*?\n\n', ' ', s0)
        s0 = re.sub(r'(?is)\[ACTIVE RUNTIME COMPILER PARAMETERS\][\s\S]*$', ' ', s0)
        s0 = re.sub(r'(?is)\[SUNO\s+RHYTHMIC[\s\S]*$', ' ', s0)
        return s0.strip()

    u_clean = _strip_compiler_boilerplate(user_scene_input)
    vlm_clean = _strip_compiler_boilerplate(compiled_raw)
    vlm_b1 = re.split(r'(?i)\bBLOCK\s*2\b|\[Shot\s*1\]', vlm_clean)[0] if vlm_clean else ''
    scan_u = u_clean
    scan_all = f'{u_clean} {vlm_b1}'.strip()
    age_sel_low = str(subject_1_age or '').strip().lower()
    has_explicit_user_age = bool(str(custom_subject_1_age or '').strip()) or bool(re.search(r'(?i)\b\d{1,2}[-\s]?(?:year|yr)s?[-\s]?old\b|\b\d{1,2}\s*år\b', u_clean))
    allows_metamorphosis = bool(_EXPLICIT_METAMORPHOSIS_REGEX.search(u_clean))
    u_has_human = bool(_SUBJECT_HUMAN_HUMANOID_REGEX.search(scan_u)) or has_explicit_user_age
    u_avian_m = _SUBJECT_AVIAN_REGEX.search(scan_u)
    u_animal_m = _SUBJECT_ANIMAL_CREATURE_REGEX.search(scan_u)
    u_veh_m = _SUBJECT_VEHICLE_OBJECT_REGEX.search(scan_u)
    v_has_human = bool(_SUBJECT_HUMAN_HUMANOID_REGEX.search(vlm_b1))
    v_avian_m = _SUBJECT_AVIAN_REGEX.search(vlm_b1)
    v_animal_m = _SUBJECT_ANIMAL_CREATURE_REGEX.search(vlm_b1)
    v_veh_m = _SUBJECT_VEHICLE_OBJECT_REGEX.search(vlm_b1)
    avian_m = u_avian_m or (v_avian_m if not u_has_human else None)
    animal_m = u_animal_m or (v_animal_m if not u_has_human else None)
    veh_m = u_veh_m or (v_veh_m if not u_has_human else None)
    has_avian_traits_prompted = bool(avian_m) or bool(re.search(r'(?i)\b(?:wings?|winged|feathers?|feathered|beak|talons?|vingar|fjädrar|näbb)\b', scan_all))
    is_animal = bool(avian_m or animal_m) and (not u_has_human) and (bool(u_avian_m or u_animal_m) or not v_has_human)
    is_vehicle = (not is_animal) and bool(veh_m) and (not u_has_human) and (bool(u_veh_m) or not v_has_human)
    is_non_human = bool(is_animal or is_vehicle)
    matched_species = (avian_m.group(0).lower() if avian_m else (animal_m.group(0).lower() if animal_m else (veh_m.group(0).lower() if veh_m else '')))
    if is_animal:
        category = 'avian_animal' if bool(avian_m) else 'non_avian_animal'
        surf_tex = 'natural plumage and feathers' if bool(avian_m) else 'natural coat, fur, or skin texture'
        species_lock_clause = (
            f'preserving exact {matched_species} species anatomy, {surf_tex}, head morphology, and authentic biological proportions'
            if matched_species else
            f'preserving exact animal species morphology, {surf_tex}, and authentic biological proportions'
        )
        if allows_metamorphosis:
            species_neg_guard = ''
        elif bool(avian_m) or has_avian_traits_prompted:
            species_neg_guard = '(species swap, morphing into mammal or rodent, four-legged mammal body, human face on bird, human hands, human clothes:1.90)'
        else:
            species_neg_guard = '(species swap, morphing into another animal, turning into a bird, unrequested wings, feathers, beak, avian talons, human face on animal, human hands, human clothes, anthropomorphic human body:1.92)'
    elif is_vehicle:
        category = 'vehicle_or_object'
        species_lock_clause = f'preserving exact {matched_species or "object"} mechanical geometry, chassis proportions, and physical surface materials'
        species_neg_guard = '' if allows_metamorphosis else '(morphing into animal or bird, organic flesh on vehicle, unrequested human face:1.80)'
    else:
        category = 'human_or_humanoid'
        species_lock_clause = ''
        if has_reference_image and not allows_metamorphosis and not has_avian_traits_prompted:
            species_neg_guard = '(species mutation from reference image, morphing subject into bird or different animal, unrequested wings or beak:1.75)'
        else:
            species_neg_guard = ''
    use_auto_age = bool(is_non_human or age_sel_low.startswith('auto')) and not has_explicit_user_age
    return {
        'is_non_human': is_non_human,
        'is_animal_creature': is_animal,
        'is_avian': bool(avian_m),
        'is_vehicle_or_object': is_vehicle,
        'allows_metamorphosis': allows_metamorphosis,
        'use_auto_age_bypass': use_auto_age,
        'category': category,
        'matched_species': matched_species,
        'species_lock_clause': species_lock_clause,
        'species_neg_guard': species_neg_guard,
    }


def _get_style_compiler_profile(resolved_style: str, user_scene_input: str = '') -> dict:
    style_low = str(resolved_style or 'realism').strip().lower()
    if style_low.startswith('original'):
        style_low = 'original'
    vault = _load_licensed_allan_ballan_vault()
    vault_styles = vault.get('style_profiles', {}) if isinstance(vault, dict) else {}
    light_bundle = _load_freemium_light_bundle() if not vault_styles else {}
    light_styles = light_bundle.get('style_map', {}) if isinstance(light_bundle, dict) else {}
    raw_u = str(user_scene_input or '').strip()
    morph = _extract_prompt_morphology_profile(raw_u)
    realism_lead = (
        'RAW unretouched 35mm live-action cinema photograph shot on ARRI Alexa 65 with Zeiss Master Prime 50mm f/1.4 lens, photorealistic live-action practical-effects and biological creature cinematography with real biological epidermis, natural subsurface scattering, visible pore micro-relief, real physical bone and enamel ivory, individual physical hair strands, and authentic physical materials while 100% preserving the exact prompted species, head morphology, skin pigment, and attire (strictly real-world live-action camera photography — NEVER a 2D painted illustration, digital painting, or cartoon).'
        if morph['has_fantasy_anatomy'] else
        'RAW unretouched 35mm live-action cinema photograph shot on ARRI Alexa 65 with Zeiss Master Prime 50mm f/1.4 lens, grounded real-world live-action reality with natural human and animal anatomy, lifelike translucent skin and fur physics with natural subsurface scattering and visible micro-texture, and authentic physical fabrics and surface materials.'
    )
    baseline_profiles = {
        'original': {
            'lead': light_styles.get('original') or 'Authentic full-fidelity capture preserving 100% of the reference image\'s exact original photographic realism, natural surface micro-texture, optical lens depth, color grading, lighting, subject species/morphology, and physical material authenticity.',
            'tail': 'Captured in the exact original visual medium of the reference image with authentic surface micro-texture, natural subsurface scattering, and true-to-source optical depth.',
            'video_lead': 'Continuous motion sequence preserving the exact original photographic realism, natural surface micro-texture, lighting, and physical materials of <Picture 1>.',
            'rule': 'preserving 100% of the exact original photographic realism, natural surface micro-texture, lighting, and physical material fidelity of the reference image.',
            'vlm_directive': '- MANDATORY STYLE_TARGET OVERRIDE (original — PRESERVE EXACT REFERENCE MEDIUM, SPECIES & PHOTOGRAPHIC REALISM): Preserve 100% of the reference image\'s exact visual medium, photographic realism, subject species/morphology, natural surface micro-texture, lighting, attire/coat, and color palette. NEVER turn a photograph into semi-realistic CGI, digital painting, 3D game art, or cartoon illustration.',
            'neg_prefix': '(semi-realistic, stylized 3d, 3d cgi, digital painting, concept art, fantasy illustration, airbrushed skin, plastic doll skin, smooth porcelain skin, cartoon, cartoonish, anime, manga, cel-shading, 2d illustration, lineart, blurry textures, double-exposed details, ghosted overlays:1.85)',
            'strip_pat': r'(?i)\b(?:semi[-\s]?realistic|stylized\s+3d(?:\s+game)?|digital\s+painting|concept\s+art|2d\s+illustration|cartoon(?:ish)?|cel[-\s]?shad(?:ed|ing))\b',
            'strip_repl': 'authentic reference-matched',
        },
        'cartoonish': {
            'lead': light_styles.get('cartoonish') or "Authentic flat 2D cel-shaded cartoon animation frame in classic Western animated series style, bold black ink outlines, discrete flat 2-tone cel color fills without 3D gradients, stylized 2D cartoon proportions, and hand-drawn 2D background art while strictly preserving the subject's exact species, facial/body traits, skin or fur tone, accessories, and attire (strictly flat 2D cartoon cel frame, NEVER semi-realistic 2.5D, NEVER 3D CGI, NEVER photorealistic).",
            'tail': 'Drawn entirely as a flat 2D cel-shaded cartoon animation frame with bold black ink outlines and discrete flat cel shadow steps without 3D gradients while preserving exact subject species, morphology, and attire.',
            'video_lead': 'Flat 2D traditional cel-shaded cartoon animation sequence with bold black ink outlines, discrete flat 2D color fills, and expressive 2D hand-drawn frame-by-frame motion.',
            'rule': 'authentic flat 2D traditional cel-shaded cartoon animation style with bold black ink outlines, discrete flat cel color fills without 3D gradients, and expressive stylized 2D proportions while preserving exact subject species, surface tone, and attire.',
            'vlm_directive': "- MANDATORY STYLE_TARGET OVERRIDE (cartoonish — FLAT 2D CEL-SHADED CARTOON FRAME): Translate the ENTIRE scene into a 100% flat 2D cel-shaded Western cartoon animation frame with bold black ink outlines and discrete flat color fills without 3D gradients while strictly preserving the subject's exact species, morphology, colors, accessories, and attire. NEVER use camera lens mm terms ('85mm', '50mm', '35mm', 'f/1.4', 'shallow depth of field'), 'semi-realistic', '2.5D', 'photorealistic', 'live-action', '3D', 'CGI', or 'skin pores'.",
            'neg_prefix': '(photorealistic, semi-realistic, 2.5d, 3d shading, soft airbrushed gradients, glossy 3d skin, live-action photograph, raw photo, 35mm film, DSLR, 3d render, 3d cgi, unreal engine, octane render, raytracing, subsurface scattering, realistic skin pores, realistic nose bridge, lifelike photography, volumetric studio photo, chiaroscuro photo, rotoscoped photo filter:1.88)',
            'strip_pat': r'(?i)(?:shot\s+on\s+arri\s+alexa[^.,;]*|\b(?:raw\s+candid\s+35mm\s+live-action\s+photograph|35mm\s+live-action\s+motion\s+picture|photorealistic|semi[-\s]?real(?:istic)?|2\.5d|live[-\s]?action(?:\s+photograph|\s+cinematography)?|raw\s+photo|\d{2,3}mm\s+(?:portrait\s+|macro\s+|anamorphic\s+|master\s+prime\s+)?(?:master\s+shot|lens)(?:\s+at\s+f/\d+(?:\.\d+)?)?(?:\s+with\s+shallow\s+depth\s+of\s+field)?|shallow\s+depth\s+of\s+field|at\s+f/\d+(?:\.\d+)?|f/\d+(?:\.\d+)?\s+aperture|(?:authentic\s+|visible\s+|human\s+|natural\s+)*skin\s+pores|natural\s+subsurface\s+scattering|subsurface\s+scattering|realistic\s+physical\s+surface\s+materials|3d\s+(?:shading|cinematic\s+cgi|cgi|render|game\s+engine)|soft\s+airbrushed(?:\s+gradients)?|specular\s+skin|unreal\s+engine(?:\s+5(?:\.5)?)?|nanite|lumen|path[-\s]?traced|ray[-\s]?traced)\b)',
            'strip_repl': 'flat 2D cel-shaded cartoon illustration with bold black outlines',
        },
        'anime': {
            'lead': light_styles.get('anime') or "Authentic flat 2D Japanese TV anime cel-shaded keyframe screenshot (anime screencap, flat color, cel shading), crisp hand-drawn black ink lineart outlines, discrete 2-tone flat cel shadow steps with sharp hard shadow boundaries, flat matte 2D anime color fills without 3D gradients, classic stylized 2D anime proportions and expressive flat 2D anime eyes, and hand-painted 2D anime background art while strictly preserving the subject's exact species, morphology, colors, accessories, and attire (strictly flat 2D Japanese TV cel-animation frame, NEVER semi-realistic 2.5D, NEVER 3D CGI, NEVER photorealistic).",
            'tail': 'Illustrated strictly as an authentic flat 2D Japanese TV anime cel-shaded keyframe screenshot with crisp black ink lineart outlines and discrete 2-tone flat cel shadows without 3D airbrushed gradients while strictly preserving exact subject species, morphology, colors, and attire.',
            'video_lead': 'Authentic flat 2D Japanese TV anime cel-shaded animation sequence with crisp black ink lineart, discrete 2-tone flat cel shadows, expressive 2D anime acting, and clean 2D keyframe motion.',
            'rule': 'authentic flat 2D Japanese TV anime cel-shaded keyframe style (anime screencap, flat color, discrete 2-tone cel shading) with crisp black ink outlines, flat matte 2D color fills without 3D gradients, and classic 2D anime styling while strictly preserving exact subject species, colors, and attire.',
            'vlm_directive': "- MANDATORY STYLE_TARGET OVERRIDE (anime — AUTHENTIC FLAT 2D JAPANESE TV ANIME CEL-SHADED KEYFRAME): Translate the ENTIRE scene into a 100% flat 2D Japanese TV anime cel-shaded keyframe screenshot (anime screencap, flat color, discrete 2-tone cel shading with sharp hard shadow edges and crisp black ink lineart) without any 3D gradients or airbrushed rendering while strictly preserving the subject's exact species, morphology, colors, glasses/accessories, and attire from the prompt and reference. NEVER write 'semi-realistic', '2.5D', 'Ufotable', 'luminous', 'specular', '3D anime', '3D', 'CGI', 'photorealistic', 'live-action', '85mm', '50mm', '35mm', 'f/1.4', 'shallow depth of field', 'skin pores', or 'subsurface scattering'.",
            'neg_prefix': '(photorealistic, semi-realistic, 2.5d, 3d shading, soft airbrushed gradients, glossy 3d skin, painterly 3d render, cgi doll, live-action photograph, raw photo, 35mm film, DSLR, 3d render, 3d cgi, 3d anime, unreal engine, western cartoon, american comic book, rotoscoped photo filter, traced photo, muddy brown colors, dull desaturated vintage anime, thick heavy marker outlines, double mouth, smudged lips, realistic human lips, realistic 3d nose bridge, subsurface scattering, realistic skin pores:1.92)',
            'strip_pat': r'(?i)(?:shot\s+on\s+arri\s+alexa[^.,;]*|\b(?:raw\s+candid\s+35mm\s+live-action\s+photograph|35mm\s+live-action\s+motion\s+picture|photorealistic|semi[-\s]?real(?:istic)?|2\.5d|live[-\s]?action(?:\s+photograph|\s+cinematography)?|raw\s+photo|\d{2,3}mm\s+(?:portrait\s+|macro\s+|anamorphic\s+|master\s+prime\s+)?(?:master\s+shot|lens)(?:\s+at\s+f/\d+(?:\.\d+)?)?(?:\s+with\s+shallow\s+depth\s+of\s+field)?|shallow\s+depth\s+of\s+field|at\s+f/\d+(?:\.\d+)?|f/\d+(?:\.\d+)?\s+aperture|(?:authentic\s+|visible\s+|human\s+|natural\s+)*skin\s+pores|natural\s+subsurface\s+scattering|subsurface\s+scattering|realistic\s+physical\s+surface\s+materials|3d\s+anime|3d\s+(?:shading|cinematic\s+cgi|cgi|render|game\s+engine)|soft\s+airbrushed(?:\s+gradients)?|specular\s+skin|luminous\s+multi[-\s]?tone|ufotable|unreal\s+engine(?:\s+5(?:\.5)?)?|nanite|lumen|path[-\s]?traced|ray[-\s]?traced)\b)',
            'strip_repl': 'flat 2D Japanese cel-shaded anime keyframe',
        },
        'semi-real': {
            'lead': light_styles.get('semi-real') or 'Stylized 3D semi-realistic video game cinematic art in Arcane and Blizzard cinematic style, hand-painted stylized brush-stroke PBR surface textures, sculpted stylized geometry, and dramatic stylized 3D CGI rim shading while preserving exact subject species, morphology, colors, and attire (stylized semi-real painterly 3D game art, NOT raw live-action camera photograph, NOT flat 2D cartoon).',
            'tail': 'Rendered in stylized semi-realistic 3D video game cinematics with sculpted stylized proportions, hand-painted 3D surface brush textures, and stylized CGI shading.',
            'video_lead': 'Stylized 3D semi-realistic game cinematic sequence with sculpted stylized proportions, hand-painted PBR brush textures, and fluid 3D CGI animation.',
            'rule': 'stylized 3D semi-realistic game cinematic aesthetic blending sculpted stylized proportions with hand-painted 3D shading.',
            'vlm_directive': "- MANDATORY STYLE_TARGET OVERRIDE (semi-real — STYLIZED PAINTERLY 3D GAME CINEMATIC CGI): Render the scene as stylized semi-realistic 3D video game cinematic art (blending sculpted stylized proportions with hand-painted 3D PBR brush textures while prioritizing exact prompted species, distinctive anatomy, colors, and attire). Avoid raw live-action camera photography terms ('RAW 35mm live-action photograph', 'skin pores', 'ARRI Alexa') and avoid flat 2D cartoon terms.",
            'neg_prefix': '(raw candid photograph, live-action documentary photo, unretouched skin pores, 35mm film grain, ARRI Alexa live-action, flat 2d cartoon, flat 2d anime, lineart, sketch, comic strip:1.65)',
            'strip_pat': r'(?i)\b(?:raw\s+candid\s+35mm\s+live-action\s+photograph|raw\s+unretouched\s+35mm\s+live-action\s+camera\s+photograph|live[-\s]?action\s+photograph|raw\s+photo|shot\s+on\s+arri\s+alexa[^.,;]*|(?:authentic\s+|visible\s+|genuine\s+|epidermal\s+|human\s+)*skin\s+pore(?:\s+micro[-\s]?relief|\s+micro[-\s]?texture|s)?|2d\s+traditional\s+cel-shaded\s+cartoon|2d\s+illustration)\b',
            'strip_repl': 'stylized 3D semi-realistic game cinematic render',
        },
        'unreal-engine-5': {
            'lead': light_styles.get('unreal-engine-5') or 'Unreal Engine 5.5 next-gen 3D video game engine render with Nanite micro-polygon geometry, Lumen ray-traced global illumination, physically based 3D game shaders, and crisp real-time 3D rendering while preserving exact subject species, morphology, colors, and attire.',
            'tail': 'Rendered in Unreal Engine 5.5 with Lumen ray-traced reflections and Nanite 3D geometry.',
            'video_lead': 'Unreal Engine 5.5 real-time 3D cinematic sequence with Lumen global illumination and Nanite 3D geometry.',
            'rule': 'hyper-detailed Unreal Engine 5.5 Lumen global illumination and Nanite 3D micro-polygon surface rendering.',
            'vlm_directive': '- MANDATORY STYLE_TARGET OVERRIDE (unreal-engine-5): Render the entire scene as a hyper-detailed Unreal Engine 5.5 3D render with Lumen global illumination and Nanite geometry while preserving exact subject species, morphology, colors, and attire. Prohibit 2D anime or flat cartoon terms.',
            'neg_prefix': '(2d flat anime, flat cel-shading, 2d cartoon, lineart, hand-drawn sketch, watercolor, vintage film grain:1.6)',
            'strip_pat': r'(?i)\b(?:anime|manga|cel[-\s]?shad(?:ed|ing)|2d\s*illustration|cartoon(?:ish)?|comic[-\s]?book)\b',
            'strip_repl': 'Unreal Engine 5.5 3D render',
        },
        'cinematic-film-35mm': {
            'lead': light_styles.get('cinematic-film-35mm') or 'Anamorphic 35mm Kodak Vision3 500T motion picture film still shot on Panavision Primo anamorphic cinema lens with deep foreground-to-midground optical sharpness, fine cinema color grading, and theatrical rim lighting while preserving exact prompted species, physical anatomy, colors, and attire.',
            'tail': 'Captured on 35mm Kodak Vision3 motion picture film stock with crisp foreground focus and authentic Panavision cinema optics.',
            'video_lead': 'Anamorphic 35mm Kodak Vision3 500T motion picture film sequence shot on Panavision Primo cinema lens with crisp foreground focus and theatrical color grading.',
            'rule': 'authentic 35mm Kodak Vision3 motion picture film stock with crisp foreground optical sharpness and Panavision cinema color grading.',
            'vlm_directive': '- MANDATORY STYLE_TARGET OVERRIDE (cinematic-film-35mm): Translate the entire scene into an authentic 35mm Kodak Vision3 motion picture film frame shot on Panavision anamorphic lenses with crisp foreground focus while preserving exact prompted species, colors, and attire. Prohibit 2D painted illustration, anime, cartoon, or 3D video game CGI terms.',
            'neg_prefix': '(2d illustration, 2d painted, digital painting, fantasy painting, concept art, anime, manga, cel-shading, cartoon, comic, lineart, flat shading, 3d video game cgi, plastic doll skin, heavy halation bloom:1.80)',
            'strip_pat': r'(?i)\b(?:anime|manga|cel[-\s]?shad(?:ed|ing)|2d\s*illustration|cartoon(?:ish)?|comic[-\s]?book|digital\s+painting|fantasy\s+illustration|concept\s+art|3d\s+game\s+engine)\b',
            'strip_repl': '35mm Kodak Vision3 motion picture film',
        },
        'dark-fantasy-real': {
            'lead': light_styles.get('dark-fantasy-real') or 'Live-action grimdark dark-fantasy cinema photograph shot on ARRI Alexa 65 with Panavision Primo anamorphic 35mm f/1.8 shallow depth of field, authentic biological surface micro-texture and subsurface scattering, tactile physical dark-fantasy environment and material textures, deep abyssal chiaroscuro shadow contrast, cold slate-blue nocturnal mist clashing with scorching molten ember rim lighting, and deep optical Z-axis background bokeh while strictly preserving exact subject species, anatomy, and prompted or reference attire without inventing unrequested armor.',
            'tail': 'Captured on ARRI Alexa 65 anamorphic 35mm f/1.8 live-action cinema optics with authentic biological micro-texture, tactile physical dark-fantasy atmosphere, deep chiaroscuro shadows, and deep 3D Z-axis bokeh (never a 2D painting, book cover, or 3D video game render).',
            'video_lead': 'Live-action grimdark dark-fantasy motion picture sequence shot on ARRI Alexa 65 anamorphic 35mm f/1.8 with authentic biological subsurface scattering, tactile physical materials, volumetric nocturnal mist, molten ember rim lighting, and deep Z-axis optical bokeh.',
            'rule': 'authentic live-action ARRI Alexa 65 anamorphic 35mm f/1.8 grimdark dark-fantasy cinema (The Witcher / Nosferatu practical cinema aesthetic) with authentic biological surface micro-texture, deep chiaroscuro contrast, cold mist vs molten ember rim lighting, and deep Z-axis optical depth of field.',
            'vlm_directive': '- MANDATORY STYLE_TARGET OVERRIDE (dark-fantasy-real — LIVE-ACTION ARRI ALEXA 65 GRIMDARK DARK-FANTASY CINEMA): Render the scene as a 100% live-action grimdark dark-fantasy motion picture photograph shot on ARRI Alexa 65 with anamorphic 35mm f/1.8 shallow depth of field. Enforce authentic biological surface micro-texture and subsurface scattering, cold slate-blue mist vs molten ember rim lighting, and deep 3D Z-axis spatial depth while strictly preserving the subject\'s exact species, morphology, and prompted or reference attire (NEVER invent unrequested battle gear or helmets unless requested in the prompt). Strictly prohibit 2D digital paintings, book-cover art, concept art, anime, cartoon, and 3D video-game CGI.',
            'neg_prefix': '(2d digital painting, 2d painted illustration, flat 2d, fantasy book cover, concept art, oil painting, wlop style, painterly brushwork, flat canvas, painted 2d background, airbrushed doll skin, smooth plastic skin, 3d cgi, 3d video game render, unreal engine, arcane style, bright sunny daylight, flat neutral studio lighting, mundane modern office, anime, manga, cel-shading, cartoon, comic strip, lineart:1.90)',
            'strip_pat': r'(?i)\b(?:anime|manga|cel[-\s]?shad(?:ed|ing)|2d\s*illustration|2d\s*painted|cartoon(?:ish)?|comic[-\s]?book|digital\s+painting|fantasy\s+(?:painting|illustration)|concept\s+art|book\s+cover(?:\s+art)?|3d\s+(?:cgi|game\s+engine|video\s+game)|unreal\s+engine|painterly(?:\s+pbr|\s+textures|\s+shading)?)\b',
            'strip_repl': 'live-action ARRI Alexa 65 grimdark dark-fantasy cinema',
        },
        'dark-fantasy-cgi': {
            'lead': light_styles.get('dark-fantasy-cgi') or 'Pre-rendered next-gen 3D VFX dark-fantasy cinematic cutscene in Diablo IV and Blur Studio offline path-traced aesthetic, ray-traced global illumination, tactile 3D PBR surface and material micro-detail with subsurface scattering, deep abyssal chiaroscuro shadow contrast, volumetric multi-plane cold slate-blue mist, drifting molten ember sparks, and 35mm f/1.8 cinema lens Z-axis spatial depth while strictly preserving exact subject species, anatomy, and prompted or reference attire without inventing unrequested armor.',
            'tail': 'Pre-rendered in offline path-traced Diablo IV / Blur Studio 3D VFX cinema quality with ray-traced PBR shaders, volumetric Z-axis depth of field, cold abyssal mist, and molten ember rim highlights (never a flat 2D digital painting or painted book cover).',
            'video_lead': 'Pre-rendered Diablo IV / Blur Studio offline path-traced 3D VFX dark-fantasy cinematic cutscene sequence with ray-traced PBR materials, volumetric multi-plane nocturnal fog, drifting molten embers, and deep Z-axis cinema depth of field.',
            'rule': 'pre-rendered Diablo IV / Blur Studio offline path-traced 3D VFX dark-fantasy cutscene aesthetic with ray-traced PBR shaders, deep chiaroscuro contrast, volumetric multi-plane fog, molten ember rim lighting, and deep 3D Z-axis camera depth separation.',
            'vlm_directive': '- MANDATORY STYLE_TARGET OVERRIDE (dark-fantasy-cgi — DIABLO IV / BLUR STUDIO PRE-RENDERED 3D VFX DARK-FANTASY CUTSCENE): Render the scene as an offline path-traced next-gen 3D VFX dark-fantasy cinematic cutscene (Diablo IV / Elden Ring CGI trailer by Blur Studio). Enforce tangible 3D PBR micro-surface detail, volumetric multi-plane nocturnal mist, glowing ember sparks, and deep 35mm f/1.8 Z-axis spatial separation while strictly preserving exact subject species, morphology, and prompted or reference attire (NEVER invent unrequested battle gear unless requested in the prompt). Strictly prohibit flat 2D digital paintings, 2D book-cover illustrations, painterly 2D brushwork, raw candid documentary snapshots, anime, and flat cel-shading.',
            'neg_prefix': '(2d digital painting, 2d painted illustration, flat 2d, fantasy book cover, tabletop illustration, concept art, oil painting, wlop style, painterly brushwork, flat canvas, painted 2d background, flat stone relief wall, raw candid documentary photo, grainy CCTV, bright sunny daylight, flat neutral studio lighting, mundane modern office, anime, manga, cel-shading, cartoon, comic strip, lineart, sketch:1.88)',
            'strip_pat': r'(?i)\b(?:anime|manga|cel[-\s]?shad(?:ed|ing)|2d\s*illustration|2d\s*painted|cartoon(?:ish)?|comic[-\s]?book|digital\s+painting|fantasy\s+(?:painting|illustration)|concept\s+art|book\s+cover(?:\s+art)?|painterly(?:\s+brushwork|\s+shading)?|raw\s+candid\s+35mm\s+live-action\s+photograph|shot\s+on\s+arri\s+alexa[^.,;]*)\b',
            'strip_repl': 'pre-rendered Diablo IV 3D VFX dark-fantasy cutscene',
        },
        'dark-fantasy': {
            'lead': light_styles.get('dark-fantasy-real') or light_styles.get('dark-fantasy') or 'Live-action grimdark dark-fantasy cinema photograph shot on ARRI Alexa 65 with Panavision Primo anamorphic 35mm f/1.8 shallow depth of field, authentic biological surface micro-texture and subsurface scattering, tactile physical dark-fantasy environment and material textures, deep abyssal chiaroscuro shadow contrast, cold slate-blue nocturnal mist clashing with molten ember rim lighting, and deep optical Z-axis background bokeh while preserving exact subject species, anatomy, and attire.',
            'tail': 'Captured on ARRI Alexa 65 anamorphic 35mm f/1.8 live-action cinema optics with authentic biological micro-texture, tactile physical dark-fantasy materials, and deep 3D Z-axis gothic bokeh.',
            'video_lead': 'Live-action grimdark dark-fantasy motion picture sequence shot on ARRI Alexa 65 anamorphic 35mm f/1.8 with authentic biological subsurface scattering, nocturnal mist, and molten ember rim lighting.',
            'rule': 'authentic live-action ARRI Alexa 65 anamorphic 35mm f/1.8 grimdark dark-fantasy cinema with authentic biological surface micro-texture, tactile physical dark-fantasy materials, and deep Z-axis optical depth of field.',
            'vlm_directive': '- MANDATORY STYLE_TARGET OVERRIDE (dark-fantasy — LIVE-ACTION GRIMDARK DARK-FANTASY CINEMA): Render as a live-action ARRI Alexa 65 anamorphic 35mm f/1.8 grimdark dark-fantasy cinema frame with authentic biological micro-texture, tactile physical dark-fantasy atmosphere, and deep Z-axis background bokeh while strictly preserving exact subject species and prompted/reference attire. Prohibit 2D digital paintings, book-cover art, anime, cartoon, and 3D video-game CGI.',
            'neg_prefix': '(2d digital painting, 2d painted illustration, flat 2d, fantasy book cover, concept art, oil painting, wlop style, painterly brushwork, flat canvas, painted 2d background, airbrushed doll skin, 3d cgi, bright sunny daylight, anime, cel-shading, cartoon, lineart:1.90)',
            'strip_pat': r'(?i)\b(?:anime|manga|cel[-\s]?shad(?:ed|ing)|2d\s*illustration|2d\s*painted|cartoon(?:ish)?|comic[-\s]?book|digital\s+painting|fantasy\s+(?:painting|illustration)|concept\s+art|book\s+cover(?:\s+art)?)\b',
            'strip_repl': 'live-action ARRI Alexa 65 grimdark dark-fantasy cinema',
        },
        'realism': {
            'lead': light_styles.get('realism') or realism_lead,
            'tail': 'Captured as an authentic raw 35mm ARRI Alexa 65 live-action photograph with real biological subsurface scattering, authentic physical surface materials, and natural optical depth of field (never a 2D painting or digital illustration).',
            'video_lead': 'RAW 35mm live-action motion picture sequence shot on ARRI Alexa 65 with Zeiss Master Prime lens, natural biological subsurface scattering on skin, individual physical hair strands, and authentic physical fabrics and surface materials.',
            'rule': 'raw unretouched 35mm ARRI Alexa 65 live-action camera photography with real biological epidermis, natural subsurface scattering, individual physical hair strands, and authentic physical materials.',
            'vlm_directive': "- MANDATORY STYLE_TARGET OVERRIDE (realism — RAW UNRETOUCHED 35MM ARRI ALEXA 65 LIVE-ACTION PHOTOGRAPH, NEVER 2D PAINTED): Translate the entire rendering medium into a 100% real-world live-action cinema camera photograph shot on ARRI Alexa 65 (real biological skin pores and subsurface scattering, real physical bone/ivory enamel, individual physical hair strands, authentic physical metal and leather). If the prompt describes normal humans or animals, depict grounded real-world humans/animals; if the prompt describes a fantasy creature or tusks/fangs/boar-head/orc/ogre/dragon, render it as a 100% photorealistic live-action physical creature with real biological skin and bone — NEVER as a 2D painting, digital illustration, concept art, CGI cartoon, or anime.",
            'neg_prefix': '(2d illustration, 2d painted, flat 2d, digital painting, fantasy painting, oil painting, concept art, book cover art, tabletop illustration, semi-realistic, stylized 3d, 3d render, 3d cgi, video game cgi, arcane style, blizzard style, unreal engine, octane render, painterly brushwork, painted hair ribbons, stylized art, video game graphics, airbrushed doll skin, smooth plastic skin, anime, manga, cel-shading, cartoon, comic, lineart:1.95)',
            'strip_pat': r'(?i)\b(?:anime|manga|cel[-\s]?shad(?:ed|ing)|2d\s*illustration|2d\s*painted|cartoon(?:ish)?|comic[-\s]?book|digital\s+painting|fantasy\s+illustration|fantasy\s+painting|concept\s+art|semi[-\s]?realistic|stylized\s+3d(?:\s+game)?|3d\s+(?:cgi|render|game\s+art)|unreal\s+engine|painterly(?:\s+pbr|\s+textures|\s+shading)?|hand[-\s]?painted)\b',
            'strip_repl': 'raw unretouched 35mm ARRI Alexa 65 live-action photograph',
        },
    }
    if style_low in baseline_profiles:
        prof = dict(baseline_profiles[style_low])
        if isinstance(vault_styles, dict) and isinstance(vault_styles.get(style_low), dict):
            for vk, vv in vault_styles[style_low].items():
                if vk not in prof or not prof.get(vk):
                    prof[vk] = vv
        if style_low == 'realism' and morph['has_fantasy_anatomy']:
            prof['lead'] = realism_lead
    elif isinstance(vault_styles, dict) and style_low in vault_styles:
        prof = dict(vault_styles[style_low])
    else:
        prof = {
            'lead': f'Rendered in {resolved_style} art style with distinct {resolved_style} visual medium and textures.',
            'tail': f'Strictly rendered in {resolved_style} aesthetic.',
            'video_lead': f'Animated and rendered in {resolved_style} visual style.',
            'rule': f'{resolved_style} aesthetic with high-fidelity textures and coherent visual styling.',
            'vlm_directive': f"- MANDATORY STYLE_TARGET OVERRIDE ({resolved_style}): Strictly enforce the '{resolved_style}' visual medium across both BLOCK 1 and BLOCK 2.",
            'neg_prefix': '(low quality, blurry, inconsistent art style:1.4)',
            'strip_pat': None,
            'strip_repl': resolved_style,
        }
    cast_prof_info = _analyze_scene_cast_and_extras(raw_u)
    wants_dual_subj = bool(cast_prof_info['has_multi_main_cast'] or cast_prof_info['has_background_extras'])
    if wants_dual_subj:
        for k_field in ('lead', 'tail', 'video_lead', 'rule'):
            val_d = str(prof.get(k_field, ''))
            val_d = re.sub(r'(?i)\b50mm\s+f/1\.4\s+lens\b', '35mm f/5.6 deep-focus cinema lens keeping all foreground characters in razor-sharp focus on the same camera plane', val_d)
            val_d = re.sub(r'(?i)\band\s+natural\s+optical\s+depth\s+of\s+field\b', 'and crisp f/5.6 deep-focus optics across all active characters', val_d)
            prof[k_field] = re.sub(r'\s{2,}', ' ', val_d).strip()
    if morph['feat_desc']:
        feat_d = morph['feat_desc']
        tusk_front = f'prominently featuring {feat_d}'
        cur_lead = str(prof.get('lead', '')).strip()
        if 'tusk' not in cur_lead[:220].lower() and 'fang' not in cur_lead[:220].lower() and 'boar' not in cur_lead[:220].lower():
            if ',' in cur_lead[:120]:
                head_c, rest_c = cur_lead.split(',', 1)
                prof['lead'] = f'{head_c}, {tusk_front},{rest_c}'.strip()
            else:
                prof['lead'] = f'Featuring {feat_d}, {cur_lead}'.strip()
        if 'tusk' not in str(prof.get('tail', '')).lower() and 'fang' not in str(prof.get('tail', '')).lower():
            prof['tail'] = f"{str(prof.get('tail', '')).rstrip('. ')}, prominently featuring {feat_d}.".strip()
        if 'tusk' not in str(prof.get('vlm_directive', '')).lower() and 'fang' not in str(prof.get('vlm_directive', '')).lower():
            prof['vlm_directive'] = f"{str(prof.get('vlm_directive', '')).rstrip()} CRITICAL PROMPT MORPHOLOGY LOCK: Explicitly describe {feat_d} in the opening sentences of BLOCK 1 ([IMAGE]) and BLOCK 2 exactly as prompted — NEVER omit, hide, or flatten prompted tusks, fangs, animal heads, or creature anatomy."
        if morph['neg_guard']:
            cur_neg_p = str(prof.get('neg_prefix', '')).strip()
            if morph['neg_guard'][:28].lower() not in cur_neg_p.lower():
                prof['neg_prefix'] = f"{morph['neg_guard']}, {cur_neg_p}" if cur_neg_p else morph['neg_guard']
    return prof


def _has_explicit_prompt_framing_override(user_scene_input: str) -> bool:
    u_txt = str(user_scene_input or '').strip()
    if not u_txt:
        return False
    if 'Reference Video Slot #5' in u_txt:
        return True
    return bool(
        re.search(
            r'(?i)\b(?:extreme[-\s]?close[-\s]?up|close[-\s]?up|macro\s+shot|medium[-\s]?close[-\s]?up|chest[-\s]?up|waist[-\s]?up|medium[-\s]?shot|medium[-\s]?wide|knee[-\s]?up|wide[-\s]?shot|wide[-\s]?angle\s+shot|full[-\s]?body|head[-\s]?to[-\s]?toe|establishing\s+shot|närbild|extrem\s+närbild|halvbild|helbild|vidvinkel)\b',
            u_txt,
        )
    )


def _get_zoom_and_lighting_specs(resolved_zoom: str, resolved_lighting: str, style_low: str, user_scene_input: str = '', background_extras_crowd: str = '', has_reference_image: bool = False) -> tuple:
    is_2d = style_low in ('cartoonish', 'anime')
    z_low = str(resolved_zoom or 'medium-shot').strip().lower()
    cast_z = _analyze_scene_cast_and_extras(user_scene_input, background_extras_crowd=background_extras_crowd)
    wants_dual_subj = bool(cast_z['has_multi_main_cast'])
    n_cast = int(cast_z['main_cast_count'])
    shot_lbl = 'two-shot' if n_cast == 2 else f'{n_cast}-character ensemble shot'
    zoom_map = {
        'extreme-close-up': 'Extreme macro close-up framing tightly focused on the face and eyes filling the frame',
        'close-up': (
            f'Balanced medium close-up {shot_lbl} framing all {n_cast} foreground characters on the exact same foreground plane in razor-sharp 35mm f/5.6 deep focus'
            if wants_dual_subj else
            'Tight close-up portrait framing from the shoulders and neck up focusing on facial expression'
        ),
        'medium-close-up': (
            f'Balanced medium close-up {shot_lbl} framing all {n_cast} foreground characters on the exact same foreground plane in razor-sharp 35mm f/5.6 deep focus'
            if wants_dual_subj else
            'Medium close-up chest-up framing from the mid-torso to the head'
        ),
        'medium-shot': (
            f'Balanced waist-up medium {shot_lbl} framing all {n_cast} foreground characters at matching scale in razor-sharp 35mm f/5.6 deep focus'
            if wants_dual_subj else
            'Balanced waist-up medium shot framing the subject from the waist to the head'
        ),
        'medium-wide': 'Medium-wide knee-up shot framing the subject from the knees to the head',
        'wide-shot': 'Full-body wide-angle master shot framing the entire subject from head to toe inside the expansive environment',
        'extreme-wide-establishing': 'Extreme wide-angle establishing shot where the vast environment dominates the frame and the full-body subject is seen at a distance',
    }
    if has_reference_image and (not wants_dual_subj) and (not _has_explicit_prompt_framing_override(user_scene_input)):
        zoom_desc = 'Matching the exact camera angle, framing distance, and initial body posture of the reference image'
    else:
        zoom_desc = zoom_map.get(z_low, f'Framed in a {resolved_zoom}')
    l_low = str(resolved_lighting or 'auto').strip().lower()
    light_map = {
        'natural-muted-cinema': 'naturalistic cinema lighting with subdued filmic color saturation, balanced skin tones, and soft highlight roll-off',
        'desaturated-low-chroma': 'desaturated low-chroma atmospheric lighting with muted pastel tones, restrained color intensity, and soft neutral contrast',
        'bleach-bypass-gritty': 'gritty silver-retained bleach-bypass cinema lighting with heavily desaturated colors, metallic midtones, and deep shadows',
        'cinematic-dark': 'dramatic high-contrast chiaroscuro dark lighting with deep shadows and sharp rim light',
        'volumetric-day': 'bright volumetric daylight with sunbeams and god rays cutting through the atmosphere',
        'neon-cyberpunk': 'vibrant neon cyberpunk illumination with saturated cyan and magenta glow and reflections',
        'golden-hour': 'warm low-angle golden hour sunset sunlight with rich amber highlights and long soft shadows',
        'moonlit-noir': 'cold silvery moonlit noir night illumination with deep indigo shadows and pale lunar highlights',
        'studio-rim-light': 'crisp three-point studio key and rim lighting sculpting the silhouette with clean highlights',
        'overcast-soft': 'soft diffused overcast sky illumination with gentle even shadowless ambient light',
    }
    light_desc = light_map.get(l_low, '' if l_low in ('auto', '') else f'{resolved_lighting} illumination')
    if is_2d and light_desc:
        light_desc = light_desc.replace('studio key and rim lighting', '2D cel-shaded rim lighting').replace('chiaroscuro', 'high-contrast 2D')
    return (zoom_desc, light_desc)


def _resolve_color_saturation_strength(resolved_lighting: str, custom_style_or_lighting: str = '', user_scene_input: str = '') -> float:
    l_low = str(resolved_lighting or 'auto').strip().lower()
    combo = f'{l_low} {custom_style_or_lighting or ""} {user_scene_input or ""}'.lower()
    m_num = re.search(r'\b(?:saturation|chroma|mättnad|färgstyrka|color[_\s-]*strength)\s*[:=]?\s*(0\.\d+|1\.\d+|1|0|\d{1,3}\s*%)', combo)
    if m_num:
        raw_v = m_num.group(1).strip()
        val = float(raw_v[:-1].strip()) / 100.0 if raw_v.endswith('%') else float(raw_v)
        return max(0.15, min(1.25, val))
    if 'bleach-bypass' in combo or 'bleach bypass' in combo or 'monochrome' in combo:
        return 0.38
    if any(k in combo for k in ('desaturated', 'low-chroma', 'low chroma', 'tona ner färg', 'mindre färg', 'avmättad', 'washed out')):
        return 0.56
    if any(k in combo for k in ('natural-muted', 'muted', 'subtle color', 'dämpad färg', 'neutral color', 'overcast-soft', 'moonlit-noir')):
        return 0.70
    if 'neon-cyberpunk' in l_low:
        return 0.96
    return 0.80


def _sanitize_camera_movement_for_settings(resolved_cam_move: str, resolved_zoom: str, style_low: str, allow_camera_movement: bool = False, user_scene_input: str = '', background_extras_crowd: str = '') -> str:
    cam_s = str(resolved_cam_move or '').strip()
    z_low = str(resolved_zoom or 'medium-shot').strip().lower()
    is_2d = style_low in ('cartoonish', 'anime')
    cast_cam = _analyze_scene_cast_and_extras(user_scene_input, background_extras_crowd=background_extras_crowd)
    wants_dual_subj = bool(cast_cam['has_multi_main_cast'])
    n_cast = int(cast_cam['main_cast_count'])
    shot_lbl = 'two-shot' if n_cast == 2 else f'{n_cast}-character shot'
    if not allow_camera_movement:
        if is_2d:
            return f'smooth locked-off 2D animation camera holding a steady {z_low} framing at constant camera distance'
        if wants_dual_subj:
            return f'locked-off tripod 35mm f/5.6 deep-focus cinema lens holding a steady {shot_lbl} at constant camera distance keeping all {n_cast} foreground characters in razor-sharp focus'
        return f'locked-off tripod cinema lens holding a steady {z_low} master shot at constant camera distance with zero zoom or pan'
    cam_s = re.sub(r'\s*\([^)]*\)\s*', ' ', cam_s).strip()
    if is_2d:
        cam_s = re.sub(r'(?i)\b\d{2,3}mm\s+(?:portrait\s+|macro\s+|anamorphic\s+)?(?:lens\s+|master\s+shot\s+)?(?:at\s+f/\d+(?:\.\d+)?\s*)?', 'smooth 2D animation camera ', cam_s)
        cam_s = re.sub(r'(?i)\bwith\s+shallow\s+depth\s+of\s+field\b', 'with clean 2D multiplane depth', cam_s)
    elif wants_dual_subj:
        cam_s = re.sub(r'(?i)\bwith\s+shallow\s+depth\s+of\s+field\b', f'with f/5.6 deep focus keeping all {n_cast} foreground characters sharp', cam_s)
    elif 'close-up' in z_low:
        cam_s = re.sub(r'(?i)\bmedium-wide\b', z_low, cam_s)
    return re.sub(r'\s{2,}', ' ', cam_s).strip()


def _resolve_qwenvl_system_prompt(master_duration: str, cut_1: str, cut_2: str, style_target: str, camera_zoom: str, lighting_ambient: str, subject_1_age: str, age_difference: str, camera_movement: str, content_rating_mode: str='Uncensored Artistic / Action (Ingen Censur — Följer Prompten)', audio_soundtrack_mode: str='sfx_only', user_scene_input: str='', allow_camera_movement: bool=False, has_reference_image: bool=False, resolved_continuity_mode: str='locked_stage_environment'):
    search_dirs = _get_default_vault_search_dirs()
    pkg_root = search_dirs[0]
    rating_tier = _resolve_content_rating_tier(content_rating_mode, user_scene_input)
    if rating_tier == 'nsfw_explicit':
        rating_directive = "- CONTENT_RATING_MODE = NSFW ARTISTIC / UNRESTRICTED: Follow the user's prompt and reference attire faithfully without censorship."
    elif rating_tier == 'uncensored_action':
        rating_directive = "- CONTENT_RATING_MODE = UNCENSORED ARTISTIC / ACTION (PROMPT-FAITHFUL): Follow the user's prompt and character attire faithfully without censorship or unrequested alterations."
    else:
        rating_directive = "- CONTENT_RATING_MODE = SFW (STRICTLY SAFE-FOR-WORK / FAMILY-FRIENDLY): All subjects MUST be 100% clothed in modest, non-revealing full-coverage attire. Strictly NO nudity, NO cleavage, NO lingerie/bikini/bra armor, NO bare chest/midriff/pelvis, and NO erotic or sensual language in BLOCK 1 or BLOCK 2."
    style_low = str(style_target or 'realism').strip().lower()
    style_prof = _get_style_compiler_profile(style_target, user_scene_input)
    style_override_rule = style_prof['vlm_directive']
    (zoom_desc, light_desc) = _get_zoom_and_lighting_specs(camera_zoom, lighting_ambient, style_low, user_scene_input=user_scene_input, has_reference_image=has_reference_image)
    clean_cam_move = _sanitize_camera_movement_for_settings(camera_movement, camera_zoom, style_low, allow_camera_movement=allow_camera_movement, user_scene_input=user_scene_input)
    aud_m = str(audio_soundtrack_mode or 'sfx_only').lower()
    m_dur_num = re.search(r'(\d+(?:\.\d+)?)', str(master_duration or '20-second'))
    dur_sec_sys = float(m_dur_num.group(1)) if m_dur_num else 20.0
    tok_budget_sys = _compute_dynamic_vlm_token_budget(dur_sec_sys)
    target_shot_count = tok_budget_sys['target_shots']
    min_w_sys = tok_budget_sys['min_words']
    max_w_sys = tok_budget_sys['max_words']
    per_shot_w_sys = tok_budget_sys['per_shot_words']
    shot_headers_str = ', '.join((f'[Shot {i}]' for i in range(1, target_shot_count + 1)))
    cont_mode_sys = str(resolved_continuity_mode or 'locked_stage_environment').strip().lower()
    if cont_mode_sys == 'hollywood_multi_scene_cuts':
        master_take_label = 'HOLLYWOOD MULTI-SCENE EDITORIAL SEQUENCE — INTENTIONAL SCENE CUTS BETWEEN ACTS'
        continuity_carryover_rule = f'- MULTI-SCENE HOLLYWOOD EDITORIAL TIMELINE ({target_shot_count} CHRONOLOGICAL 5-SECOND SHOTS: {shot_headers_str} | TARGET LENGTH: {min_w_sys}-{max_w_sys} WORDS TOTAL, ~{per_shot_w_sys} WORDS PER SHOT): Write all {target_shot_count} sequential shot sections ({shot_headers_str}) inside BLOCK 2, distributing the user prompt\'s chronological story acts across the full {master_duration} timeline. Whenever a new location, environment, or major editorial camera angle cut begins in [Shot K] (K >= 2), prefix that shot body with [SCENE CUT] and describe the new environment, camera framing, and lighting clearly while keeping <Subject 1>\'s exact facial identity, hair, and attire 100% consistent with <Picture 1>.'
    elif cont_mode_sys == 'continuous_one_shot':
        master_take_label = 'CONTINUOUS ONE-SHOT LONG TAKE — SEAMLESS CAMERA TRAVERSAL ACROSS EVOLVING SPACES'
        continuity_carryover_rule = f'- CONTINUOUS ONE-SHOT TRAVERSAL & STATE CARRYOVER ({target_shot_count} CHRONOLOGICAL 5-SECOND SHOTS: {shot_headers_str} | TARGET LENGTH: {min_w_sys}-{max_w_sys} WORDS TOTAL, ~{per_shot_w_sys} WORDS PER SHOT): Write all {target_shot_count} sequential shot sections ({shot_headers_str}) inside BLOCK 2 as one unbroken Steadicam/dolly tracking take with zero hard cuts. Distribute the user prompt\'s spatial journey chronologically from [Shot 1] (initial starting environment of <Picture 1>) through intermediate thresholds/transitions into the destination environment in the later shots, explicitly anchoring the ending position and camera motion of [Shot K-1] at the start of [Shot K].'
    else:
        master_take_label = 'SINGLE UNBROKEN CONTINUOUS TAKE — ZERO HARD CUTS'
        continuity_carryover_rule = f'- MULTI-WINDOW CONTINUITY & STATE CARRYOVER ({target_shot_count} CHRONOLOGICAL 5-SECOND SHOTS: {shot_headers_str} | TARGET LENGTH: {min_w_sys}-{max_w_sys} WORDS TOTAL, ~{per_shot_w_sys} WORDS PER SHOT): Write all {target_shot_count} sequential shot sections ({shot_headers_str}) inside BLOCK 2 (1 shot per 5-second continuation window, giving the final [Shot {target_shot_count}] the exact same ~{per_shot_w_sys}-word descriptive richness as [Shot 1]). Every [Shot K] (for K >= 2) MUST begin by explicitly anchoring the exact ending body posture, camera framing, clothing/armor state, and spatial position from the final frame of [Shot K-1] before introducing the next physical progression, ensuring zero sudden pose resets across continuation windows.'
    morph_sys = _extract_prompt_morphology_profile(user_scene_input)
    has_orc_tusks_sys = bool(morph_sys['has_tusks'])
    wants_face_metal_sys = _has_explicit_facial_metal_request(user_scene_input)
    tusk_silent_note = ' (while keeping the two sharp protruding lower-jaw tusks 100% visible outside the lips)' if has_orc_tusks_sys else ''
    if aud_m == 'sfx_only':
        audio_directive = f"- MANDATORY AUDIO_SOUNDTRACK_MODE = SFX ONLY (PURE DIEGETIC FOLEY & NATURAL EXPRESSIONS, NO MUSIC / NO SINGING): In BLOCK 2, preserve all natural facial expressions, breathing, and actions from the user prompt{tusk_silent_note} without unrequested singing or musical score. Describe realistic physical sound effects and environmental foley inside [Overall Soundscape]. Completely OMIT [Non-Diegetic Music]."
    elif aud_m == 'sfx_and_speech':
        audio_directive = f'- MANDATORY AUDIO_SOUNDTRACK_MODE = SFX & NATURAL SPEECH ONLY (MINIMAX H3 <d> DIALOGUE TAG SUPPORT): In BLOCK 2, describe realistic physical sound effects (foley, ambience) and natural spoken dialogue/voice inside [Overall Soundscape] and {shot_headers_str}. Whenever a character speaks dialogue or vocalizes, wrap the spoken line in MiniMax H3 native dialogue tags: <d>[English] (spoken dialogue or vocal expression)</d>. Completely OMIT [Non-Diegetic Music].'
    elif aud_m == 'instrumental_bgm':
        audio_directive = f"- MANDATORY AUDIO_SOUNDTRACK_MODE = INSTRUMENTAL BACKGROUND MUSIC + SFX (NO SINGING LYRICS): In BLOCK 2, preserve all natural facial expressions and physical actions from the user prompt{tusk_silent_note} without unrequested singing lyrics. Include realistic foley in [Overall Soundscape] and a purely instrumental cinematic score in [Non-Diegetic Music]."
    else:
        audio_directive = "- MANDATORY AUDIO_SOUNDTRACK_MODE = BACKGROUND MUSIC WITH VOCALS / LIP-SYNC: In BLOCK 2, include synchronized studio lead vocals and expressive singing in [Overall Soundscape] and [Non-Diegetic Music] with clear mouth and lip articulation."
    eff_zoom_label = 'reference-image-framing' if (has_reference_image and not _has_explicit_prompt_framing_override(user_scene_input)) else camera_zoom
    if cont_mode_sys == 'hollywood_multi_scene_cuts':
        cam_zoom_rule = f"- CAMERA_ZOOM = {eff_zoom_label} ({zoom_desc} in Shot 1, with intentional cinematic framing & camera angle evolution across [SCENE CUT] boundaries) | CAMERA_MOVEMENT = {clean_cam_move}"
        style_env_lock_note = 'LOCK IDENTICAL VISUAL MEDIUM & CHARACTER IDENTITY ACROSS ALL SCENE CUTS WHILE ALLOWING PROMPTED ENVIRONMENT & LIGHTING PROGRESSION'
    elif cont_mode_sys == 'continuous_one_shot':
        cam_zoom_rule = f"- CAMERA_ZOOM = {eff_zoom_label} ({zoom_desc}) | CAMERA_MOVEMENT = {clean_cam_move} (EXECUTE CONTINUOUS UNBROKEN CAMERA TRACKING SMOOTHLY AS THE ENVIRONMENT EVOLVES)"
        style_env_lock_note = 'LOCK IDENTICAL VISUAL MEDIUM & CHARACTER IDENTITY ACROSS THE CONTINUOUS ONE-SHOT JOURNEY WHILE ALLOWING NATURAL SPATIAL & LIGHTING EVOLUTION'
    else:
        cam_zoom_rule = (
            f"- CAMERA_ZOOM = {eff_zoom_label} ({zoom_desc}) | CAMERA_MOVEMENT = {clean_cam_move} (EXECUTE THIS REQUESTED CAMERA MOVEMENT SMOOTHLY ACROSS THE SINGLE UNBROKEN TAKE WITHOUT HARD JUMP CUTS)"
            if allow_camera_movement else
            f"- CAMERA_ZOOM = {eff_zoom_label} ({zoom_desc} — MAINTAIN CONSTANT CAMERA DISTANCE ACROSS ALL SHOTS WITHOUT UNREQUESTED ZOOM-IN, DOLLY-IN, OR JUMP CUTS)\n- CAMERA_MOVEMENT = {clean_cam_move}"
        )
        style_env_lock_note = 'LOCK IDENTICAL TRANSFORMATION, SHADING, AND LIGHTING ACROSS ALL SHOTS'
    subj_tax_sys = _detect_subject_taxonomy_and_species_lock(user_scene_input, '', subject_1_age, has_reference_image=has_reference_image)
    is_non_human_sys = bool(subj_tax_sys['is_non_human'])
    use_auto_age_sys = bool(subj_tax_sys['use_auto_age_bypass'])
    age_prof_sys = _build_age_authority_profile(
        subject_1_age,
        is_female=True,
        has_orc_tusks=has_orc_tusks_sys,
        allow_facial_metal=wants_face_metal_sys,
        style_target=style_target,
        tusk_descriptor=morph_sys['feat_desc'],
        is_non_human=use_auto_age_sys,
        species_lock_phrase=subj_tax_sys['species_lock_clause'],
    )
    age_header_line = (
        '- SUBJECT_TAXONOMY_LOCK = NON-HUMAN / SPECIES-TRUE MORPHOLOGY (DO NOT INVENT HUMAN AGE, HUMAN FACE, OR CLOTHING; NEVER MUTATE SPECIES OR TURN MAMMALS INTO BIRDS)'
        if is_non_human_sys else (
            '- SUBJECT_1_AGE = auto_from_prompt_or_ref (FOLLOW EXACT AGE & SPECIES FROM PROMPT OR REFERENCE IMAGE)'
            if use_auto_age_sys else
            f'- SUBJECT_1_AGE = {subject_1_age} (NODE AGE IS ABSOLUTE LAW OVER PROMPT AND IMAGE)\n- AGE_DIFFERENCE = {age_difference}'
        )
    )
    b1_morph_note = (
        f'exact species morphology ({subj_tax_sys["species_lock_clause"] or "faithful to prompt and reference image"})'
        if use_auto_age_sys else
        f'SUBJECT_1_AGE facial morphology ({age_prof_sys["lead_badge"]})'
    )
    runtime_header = f"\n\n[ACTIVE RUNTIME COMPILER PARAMETERS]\n- MASTER_DURATION = {master_duration} ({master_take_label})\n- SCENE_CONTINUITY_MODE = {cont_mode_sys}\n{continuity_carryover_rule}\n- STYLE_TARGET = {style_target} ({style_prof['lead']} — {style_env_lock_note})\n{cam_zoom_rule}\n- LIGHTING_AMBIENT = {lighting_ambient} ({light_desc or 'scene-adaptive illumination'})\n{age_header_line}\n{age_prof_sys['vlm_rule']}\n{rating_directive}\n{style_override_rule}\n{audio_directive}\n- CRITICAL KREA 2 RULE FOR BLOCK 1: Inside BLOCK 1 under [IMAGE], start the very first sentence with the exact STYLE_TARGET medium ({style_target}), framing ({zoom_desc}), and {b1_morph_note}, incorporate LIGHTING_AMBIENT ({lighting_ambient}), preserve the reference image's exact initial pose and species in I2I mode (unless the user prompt explicitly requests a different starting pose or transformation) or follow the user prompt in T2I mode, and do NOT write '<Subject 1>', 'Subject 1', '(none (single subject))', or raw parameter labels inside BLOCK 1. Use '<Subject 1>' tags ONLY inside BLOCK 2.\n"
    vault = _load_licensed_allan_ballan_vault(search_dirs)
    if vault:
        core_prompt = str(vault.get('system_prompt', '')).strip()
        redacted_base = str(vault.get('lm_studio_redacted_prompt', '')).strip()
        if core_prompt:
            core_prompt = core_prompt.replace('Event_1', cut_1).replace('Event_2', cut_2)
            core_prompt = re.sub(r'strictly between \d+ and \d+ words total', f'strictly between {min_w_sys} and {max_w_sys} words total across all {target_shot_count} shots', core_prompt)
            core_prompt = re.sub(r'(?is)-\s*AUTOMATIC_CONTENT_SCANNER\s*=.*?(?=-\s*OPTICAL_FRAME_COMPILER|\Z)', f'- NODE CONTENT RATING AUTHORITY = {rating_directive}\n', core_prompt)
            core_prompt = re.sub(r'(?i)\bA\s+dynamic\s+low-angle\s+medium-wide\b', 'A balanced eye-level medium-wide', core_prompt)
            core_prompt = re.sub(r'(?i)\band\s+fortress\s+scale\b', 'and spatial depth', core_prompt)
            core_prompt = re.sub(r'(?i)If\s+interior,\s+enforce\s+chiaroscuro\s+studio\s+lighting\.', 'If interior, preserve natural room illumination and depth.', core_prompt)
            core_prompt = re.sub(r'(?i)Re-state\s+the\s+character\'s\s+core\s+visual\s+identity\s+and\s+age\s+profile\.\s*Apply\s+ledföljd\s*\([^)]*\)\s*to\s+prohibit\s+duplicate\s+geometry\.', 'Focus 100% of the shot description on seamless action progression, body choreography, expression, and natural surface/garment physics.', core_prompt)
            core_prompt = re.sub(r'(?i)Re-state\s+the\s+character\'s\s+core\s+visual\s+identity\s+and\s+age\s+profile,\s+and\s+enforce\s+rigid\s+skeletal\s+rigging\s+vectors\s*\([^)]*\)\.', 'Focus 100% of the shot description on completing the prompted choreography, posture transitions, and expressive acting with natural physical momentum.', core_prompt)
            if target_shot_count >= 4 and '[Shot 4]' not in core_prompt and '[Constraints]' in core_prompt:
                extra_shot_blocks = '\n\n'.join((
                    (
                        f'[Shot {s_i}]\nAdvancing the chronological multi-scene story into window {s_i} of {target_shot_count} (prefix with [SCENE CUT] if cutting to a new location or camera setup): Describe the new environment, camera framing, and <Subject 1>\'s action while preserving exact subject species and identity.'
                        if cont_mode_sys == 'hollywood_multi_scene_cuts' else
                        f'[Shot {s_i}]\nContinuing seamlessly from the final frame of [Shot {s_i - 1}] with zero scene cuts: Execute the next chronological phase of the user-prompted choreography, full-body motion, and expressive acting across window {s_i} of {target_shot_count}.'
                    )
                    for s_i in range(4, target_shot_count + 1)
                ))
                core_prompt = core_prompt.replace('[Constraints]', f'{extra_shot_blocks}\n\n[Constraints]', 1)
            if not use_auto_age_sys:
                core_prompt = _apply_age_override_to_text(core_prompt, subject_1_age)
            redacted_base = core_prompt
            print(f"[EZ-QWEN3-VL] 🔒 Valid License Verified ({rating_tier.upper()} | Mode: {cont_mode_sys} | Style: {style_target} | Age: {'species_auto' if use_auto_age_sys else subject_1_age} | Audio: {aud_m} | Shots: {target_shot_count} | MaxTokens: {tok_budget_sys['transformers_max_new_tokens']}/{tok_budget_sys['gguf_max_tokens']}) -> Decrypted allan_ballan_core.enc in RAM.")
            return (core_prompt + runtime_header, redacted_base + runtime_header, 'PRO_LICENSED // allan_ballan_core.enc')
    light_bundle = _load_freemium_light_bundle(search_dirs)
    light_text = str(light_bundle.get('prompt_body', '')).strip()
    if not light_text:
        default_lt_path = pkg_root / 'system_prompt_light.txt'
        light_text = "You are a cinematic prompt assistant. Convert the user's scene description into two plain-text blocks separated by \n\n:\n\nBLOCK 1\n[IMAGE]\nWrite a clean static image prompt for keyframe generation.\n\n[Shot 1]\nOpening camera movement and subject action.\n\n[Shot 2]\nMid-sequence action continuing seamlessly from Shot 1.\n\n[Shot 3]\nConcluding action of the scene.\n\n[Constraints]\nKeep subjects clearly visible in frame.\n\n[Overall Soundscape]\nAmbient sounds and foley.\n\n[Non-Diegetic Music]\nBackground score."
        try:
            default_lt_path.write_text(light_text + '\n', encoding='utf-8')
        except Exception:
            pass
    if target_shot_count >= 4 and '[Shot 4]' not in light_text and '[Constraints]' in light_text:
        extra_lt_shots = '\n\n'.join((
            f'[Shot {s_i}]\nContinuing seamlessly from Shot {s_i - 1}, execute the next phase of the prompted movement and expression across window {s_i} of {target_shot_count}.'
            for s_i in range(4, target_shot_count + 1)
        ))
        light_text = light_text.replace('[Constraints]', f'{extra_lt_shots}\n\n[Constraints]', 1)
    age_lt_str = 'species-auto' if use_auto_age_sys else f'{subject_1_age} ({age_difference})'
    light_runtime = f"\n\n[SCENE SETTINGS]\nDuration: {master_duration} (Cut 1: {cut_1}, Cut 2: {cut_2}) | Target Shots: {target_shot_count} ({shot_headers_str}) | Style: {style_target} | Framing: {camera_zoom} | Lighting: {lighting_ambient} | Subject Age: {age_lt_str} | Camera Motion: {camera_movement}\n{continuity_carryover_rule}\n{age_prof_sys['vlm_rule']}\n{rating_directive}\n{style_override_rule}\n{audio_directive}"
    print(f'[EZ-QWEN3-VL] 🔓 Freemium Community Edition ({rating_tier.upper()} | Age: {age_lt_str} | Audio: {aud_m} | Shots: {target_shot_count}) -> Loaded editable system_prompt_light.txt (multi-window continuation unlocked; upgrade to Pro license + allan_ballan_core.enc for full Allan Ballan Master Compiler).')
    return (light_text + light_runtime, light_text + light_runtime, 'FREEMIUM_COMMUNITY // system_prompt_light.txt')

def discover_dynamic_vlm_models():
    discovered = ['LM_STUDIO_ACTIVE_MODEL']
    try:
        for folder_key in ('LLM', 'text_encoders', 'clip', 'checkpoints'):
            if folder_key not in folder_paths.folder_names_and_paths:
                continue
            base_dirs = folder_paths.get_folder_paths(folder_key)
            hf_pkg_dirs = set()
            for b_dir in base_dirs:
                b_path = Path(b_dir)
                if not b_path.exists():
                    continue
                for cfg_file in b_path.rglob('config.json'):
                    if '.cache' in cfg_file.parts or cfg_file.parent.name.endswith('_ez_q8_safetensors_cache'):
                        continue
                    rel_pkg = str(cfg_file.parent.relative_to(b_path)).replace('/', '\\')
                    hf_pkg_dirs.add(rel_pkg)
                    discovered.append(rel_pkg)
                for gguf_file in b_path.rglob('*.gguf'):
                    if '.cache' in gguf_file.parts or 'mmproj' in gguf_file.name.lower():
                        continue
                    rel_gguf = str(gguf_file.relative_to(b_path)).replace('/', '\\')
                    discovered.append(rel_gguf)
            for fn in folder_paths.get_filename_list(folder_key):
                norm_fn = str(fn).replace('/', '\\')
                low_fn = norm_fn.lower()
                if '.cache' in norm_fn or 'mmproj' in low_fn or '_ez_q8_safetensors_cache' in low_fn:
                    continue
                if low_fn.endswith('.gguf'):
                    discovered.append(norm_fn)
                    continue
                if any((norm_fn.startswith(pkg + '\\') for pkg in hf_pkg_dirs)):
                    continue
                if low_fn.endswith(('.safetensors', '.bin', '.pt', '.pth')):
                    if any((k in low_fn for k in ('qwen', 'vl', 'instruct', 'llava', 'minicpm', 'gemma', 'heretic', 'abliterated', 'unredacted'))):
                        discovered.append(norm_fn)
    except Exception:
        pass
    hf_cache = Path(os.path.expanduser('~')) / '.cache' / 'huggingface' / 'hub'
    if hf_cache.exists():
        for d in sorted(hf_cache.glob('models--*')):
            clean_id = d.name.replace('models--', '', 1).replace('--', '/')
            if any((k in clean_id.lower() for k in ('qwen', 'vl', 'instruct'))):
                discovered.append(clean_id)
    seen = []
    for item in discovered:
        if item not in seen:
            seen.append(item)
    lm_head = seen[:1]
    rest = sorted(
        seen[1:],
        key=lambda x: (
            str(x).lower().endswith('.gguf'),
            not ('huihui' in str(x).lower() or 'abliterated' in str(x).lower()),
            str(x).lower(),
        ),
    )
    return lm_head + rest

def _tensor_to_pil_and_b64(reference_image):
    if reference_image is None or not isinstance(reference_image, torch.Tensor):
        return (None, '')
    try:
        import io
        import numpy as np
        from PIL import Image
        t = reference_image.detach().cpu()
        if t.ndim == 4:
            t = t[0]
        if float(t.max().item()) <= 0.0001:
            return (None, '')
        arr = (t.clamp(0.0, 1.0).numpy() * 255.0).round().astype(np.uint8)
        pil_img = Image.fromarray(arr, mode='RGB')
        max_dim = max(pil_img.size)
        if max_dim > 392:
            scale = 392.0 / float(max_dim)
            new_w = max(56, int(round((pil_img.width * scale) / 28.0) * 28))
            new_h = max(56, int(round((pil_img.height * scale) / 28.0) * 28))
            resample_op = getattr(getattr(Image, 'Resampling', Image), 'BILINEAR', Image.BILINEAR)
            pil_img = pil_img.resize((new_w, new_h), resample_op)
        buf = io.BytesIO()
        pil_img.save(buf, format='PNG')
        b64_str = base64.b64encode(buf.getvalue()).decode('utf-8')
        return (pil_img, f'data:image/png;base64,{b64_str}')
    except Exception:
        return (None, '')


def _detect_reference_orc_species_and_skin(pil_img, user_scene_input: str = '') -> dict:
    info = {
        'is_orc': False,
        'is_crimson_orc': False,
        'is_green_orc': False,
        'has_visible_tusks': False,
        'has_non_human_pigment': False,
        'pigment_label': '',
        'trait_clause': '',
    }
    raw_u = str(user_scene_input or '').strip()
    morph_u = _extract_prompt_morphology_profile(raw_u)
    if pil_img is None or not morph_u['has_fantasy_anatomy']:
        return info
    try:
        import numpy as np
        arr = np.asarray(pil_img.convert('RGB'), dtype=np.float32) / 255.0
        (h, w, _) = arr.shape
        if h < 32 or w < 32:
            return info
        roi = arr[int(h * 0.10):int(h * 0.78), int(w * 0.22):int(w * 0.78)]
        (r, g, b) = (roi[:, :, 0], roi[:, :, 1], roi[:, :, 2])
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        mid_m = (lum > 0.10) & (lum < 0.78)
        mid_cnt = float(max(1, mid_m.sum()))
        crim_m = mid_m & (r > 0.28) & ((r - g) > 0.20) & ((r / np.maximum(g, 0.04)) > 1.65) & (np.abs(g - b) < 0.12)
        green_m = mid_m & (g > 0.22) & ((g - r) > 0.065) & ((g - b) > 0.085)
        blue_m = mid_m & (b > 0.24) & ((b - r) > 0.095) & ((b - g) > 0.055)
        crim_ratio = float(crim_m.sum()) / mid_cnt
        green_ratio = float(green_m.sum()) / mid_cnt
        blue_ratio = float(blue_m.sum()) / mid_cnt
        pigment_lbl = 'deep crimson-red skin' if crim_ratio >= 0.14 else ('emerald-green skin' if green_ratio >= 0.14 else ('cobalt-blue skin' if blue_ratio >= 0.14 else ''))
        if pigment_lbl and morph_u['has_tusks']:
            subj_noun = 'orc character' if morph_u['has_orc'] else 'character'
            feat_lbl = morph_u['feat_desc'] or 'two sharp protruding white lower-jaw tusks'
            info.update({
                'is_orc': bool(morph_u['has_orc']),
                'is_crimson_orc': bool(crim_ratio >= 0.14),
                'is_green_orc': bool(green_ratio >= 0.14),
                'has_visible_tusks': bool(morph_u['has_tusks']),
                'has_non_human_pigment': True,
                'pigment_label': pigment_lbl,
                'trait_clause': f'{subj_noun} with {pigment_lbl} and {feat_lbl}',
            })
    except Exception:
        pass
    return info

def _resolve_local_vlm_path(vlm_model_name: str):
    if not vlm_model_name or vlm_model_name == 'LM_STUDIO_ACTIVE_MODEL':
        return None
    norm_rel = str(vlm_model_name).replace('\\', '/')
    try:
        for folder_key in ('LLM', 'text_encoders', 'clip', 'checkpoints'):
            if folder_key not in folder_paths.folder_names_and_paths:
                continue
            for b_dir in folder_paths.get_folder_paths(folder_key):
                cand = Path(b_dir) / norm_rel
                if cand.exists():
                    return cand
    except Exception:
        pass
    hf_cache = Path(os.path.expanduser('~')) / '.cache' / 'huggingface' / 'hub'
    if '/' in norm_rel and hf_cache.exists():
        cache_dir = hf_cache / ('models--' + norm_rel.replace('/', '--')) / 'snapshots'
        if cache_dir.exists():
            snaps = sorted([d for d in cache_dir.iterdir() if d.is_dir()], key=lambda x: x.stat().st_mtime, reverse=True)
            if snaps:
                return snaps[0]
    direct = Path(vlm_model_name)
    return direct if direct.exists() else None

def _free_cuda_tensor_storage(obj):
    if isinstance(obj, torch.Tensor):
        try:
            if obj.is_cuda:
                obj.detach().untyped_storage().resize_(0)
        except Exception:
            pass
    elif isinstance(obj, dict):
        for v in list(obj.values()):
            _free_cuda_tensor_storage(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _free_cuda_tensor_storage(v)

def _find_companion_mmproj_gguf(gguf_path: Path):
    search_roots = [gguf_path.parent]
    if gguf_path.parent.parent != gguf_path.parent:
        search_roots.append(gguf_path.parent.parent)
    stem_tokens = [t for t in re.split(r'[-_.\s]+', gguf_path.stem.lower()) if t in ('qwen3', 'qwen2', 'qwen2.5', 'vl', '2b', '4b', '7b', '8b', '9b', '27b', '32b')]
    candidates = []
    for s_root in search_roots:
        if not s_root.exists():
            continue
        for p in s_root.rglob('*mmproj*.gguf'):
            if p.is_file():
                score = sum((1 for tok in stem_tokens if tok in p.name.lower()))
                candidates.append((score, p.stat().st_size, p))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return candidates[0][2]

def _compute_dynamic_vlm_token_budget(duration_or_str) -> dict:
    if isinstance(duration_or_str, (int, float)):
        dur_sec = float(duration_or_str)
    else:
        m_d = re.search(r'(\d+(?:\.\d+)?)', str(duration_or_str or '20-second'))
        dur_sec = float(m_d.group(1)) if m_d else 20.0
    dur_sec = max(5.0, min(360.0, dur_sec))
    target_shots = max(3, min(72, int(math.ceil(dur_sec / 5.0)))) if dur_sec >= 20.0 else 3
    min_words = max(180, 90 + target_shots * 32)
    max_words = max(380, 160 + target_shots * 58)
    per_shot_words = max(38, min(68, int(round((min_words + max_words) * 0.42 / float(max(1, target_shots))))))
    transformers_max_new_tokens = min(6144, max(1240, 520 + target_shots * 175))
    gguf_max_tokens = min(6144, max(1320, 560 + target_shots * 180))
    lm_studio_max_tokens = min(8192, max(1450, 620 + target_shots * 190))
    gguf_n_ctx = 4096 if target_shots <= 8 else (8192 if target_shots <= 28 else 12288)
    http_timeout_sec = max(45, min(240, 30 + target_shots * 4))
    return {
        'duration_sec': dur_sec,
        'target_shots': target_shots,
        'min_words': min_words,
        'max_words': max_words,
        'per_shot_words': per_shot_words,
        'transformers_max_new_tokens': transformers_max_new_tokens,
        'gguf_max_tokens': gguf_max_tokens,
        'lm_studio_max_tokens': lm_studio_max_tokens,
        'gguf_n_ctx': gguf_n_ctx,
        'http_timeout_sec': http_timeout_sec,
    }


def _sanitize_krea2_prose_and_runaway_clauses(text_in: str, is_block1_image: bool = False) -> str:
    s = str(text_in or '').strip()
    if not s:
        return ''
    if is_block1_image:
        s = re.sub(r'\(([^():\n]+):\s*\d+(?:\.\d+)?\)', r'\1', s)
        s = re.sub(r'(?i)\b(?:score_\d+(?:_up)?|source_pony|source_anime|rating_explicit|rating_questionable|rating_safe|[1-6](?:girl|boy)s?|solo_focus)\b\s*,?\s*', '', s)
        s = re.sub(r'\b([a-zA-Z]{2,})_([a-zA-Z]{2,})(?:_([a-zA-Z]{2,}))?\b', lambda m: ' '.join(g for g in m.groups() if g), s)
    sents = re.split(r'(?<=[.!?])\s+', s)
    clean_sents = []
    for sent in sents:
        st = sent.strip()
        if not st:
            continue
        if len(st) > 950:
            clauses = [c.strip() for c in st.split(',') if c.strip()]
            dedup_c = []
            seen_c = set()
            for cl in clauses:
                cl_k = re.sub(r'\W+', '', cl.lower())[:36]
                if cl_k and cl_k in seen_c:
                    continue
                if cl_k:
                    seen_c.add(cl_k)
                dedup_c.append(cl)
            st = ', '.join(dedup_c)
            if len(st) > 1400 and ',' in st[:1400]:
                st = st[:1400].rsplit(',', 1)[0].rstrip(',;:') + '.'
        st = re.sub(r'(?i)\s+(?:with\s+a\s+visible|with\s+a|with\s+an|and\s+a|and\s+her|while\s+her)\s*\.$', '.', st)
        clean_sents.append(st)
    return re.sub(r'\s{2,}', ' ', ' '.join(clean_sents)).strip()


def _run_local_gguf_vlm(gguf_path: Path, system_instruction: str, user_scene_input: str, b64_urls: list, compiler_seed: int, max_tokens: int = 760, n_ctx: int = 4096):
    llm = None
    try:
        if hasattr(comfy.model_management, 'unload_all_models'):
            comfy.model_management.unload_all_models()
        if hasattr(comfy.model_management, 'soft_empty_cache'):
            comfy.model_management.soft_empty_cache()
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        from llama_cpp import Llama
        mmproj_path = _find_companion_mmproj_gguf(gguf_path)
        chat_handler = None
        if mmproj_path is not None and b64_urls:
            from llama_cpp import llama_chat_format
            for handler_cls_name in ('Qwen25VLChatHandler', 'Qwen2VLChatHandler', 'Llava15ChatHandler', 'Llava16ChatHandler'):
                h_cls = getattr(llama_chat_format, handler_cls_name, None)
                if h_cls is not None:
                    try:
                        chat_handler = h_cls(clip_model_path=str(mmproj_path), verbose=False)
                        print(f'[EZ-QWEN3-VL] 🧩 Attached GGUF Vision Projector ({handler_cls_name}): {mmproj_path.name}')
                        break
                    except Exception:
                        continue
        eff_n_ctx = max(4096, int(n_ctx or 4096))
        eff_max_tok = max(640, int(max_tokens or 760))
        print(f'[EZ-QWEN3-VL] 🚀 Loading Q8/GGUF model via llama_cpp on GPU: {gguf_path.name} (n_ctx={eff_n_ctx}, max_tokens={eff_max_tok}) ...')
        llm_kwargs = {
            'model_path': str(gguf_path),
            'n_gpu_layers': -1,
            'n_ctx': eff_n_ctx,
            'seed': int(compiler_seed) & 2147483647,
            'verbose': False,
        }
        if chat_handler is not None:
            llm_kwargs['chat_handler'] = chat_handler
        llm = Llama(**llm_kwargs)
        if chat_handler is not None and b64_urls:
            user_content = [{'type': 'image_url', 'image_url': {'url': u}} for u in b64_urls if u]
            user_content.append({'type': 'text', 'text': str(user_scene_input)})
        else:
            user_content = str(user_scene_input)
        resp = llm.create_chat_completion(
            messages=[
                {'role': 'system', 'content': system_instruction},
                {'role': 'user', 'content': user_content},
            ],
            max_tokens=eff_max_tok,
            temperature=0.2,
            top_p=0.9,
            repeat_penalty=1.08,
        )
        out_text = resp.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
        out_text = re.sub(r'(?is)<think>.*?</think>', '', out_text).strip()
        print(f'[EZ-QWEN3-VL] ✅ Local GGUF compiled {len(out_text)} chars.')
        return out_text
    except Exception as gguf_exc:
        print(f'[EZ-QWEN3-VL] Local GGUF notice ({gguf_path.name}): {gguf_exc}')
        return ''
    finally:
        if llm is not None:
            try:
                if hasattr(llm, 'close'):
                    llm.close()
            except Exception:
                pass
            del llm
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

def _run_local_transformers_vlm(model_dir: Path, system_instruction: str, user_scene_input: str, pil_img, compiler_seed: int, extra_pil_imgs=None, max_new_tokens: int = 640):
    model = None
    processor = None
    inputs = None
    gen_ids = None
    try:
        import transformers
        from transformers import AutoProcessor
        if hasattr(comfy.model_management, 'unload_all_models'):
            comfy.model_management.unload_all_models()
        if hasattr(comfy.model_management, 'soft_empty_cache'):
            comfy.model_management.soft_empty_cache()
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            if hasattr(torch.cuda, 'ipc_collect'):
                torch.cuda.ipc_collect()
        is_single_file = model_dir.is_file()
        load_dir = model_dir.parent if is_single_file else model_dir
        print(f'[EZ-QWEN3-VL] 🚀 Loading local VLM from disk: {model_dir} ...')
        torch.manual_seed(int(compiler_seed) & 2147483647)
        try:
            processor = AutoProcessor.from_pretrained(str(load_dir), trust_remote_code=True)
        except Exception:
            processor = AutoProcessor.from_pretrained(str(load_dir), trust_remote_code=True, use_fast=False)
        model_cls = getattr(transformers, 'AutoModelForImageTextToText', None) or getattr(transformers, 'AutoModelForVision2Seq', None) or getattr(transformers, 'AutoModelForCausalLM', None)
        dtype = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16
        dev = 'cuda' if torch.cuda.is_available() else 'cpu'
        vram_gib = torch.cuda.get_device_properties(0).total_memory / 1024.0 ** 3 if torch.cuda.is_available() else 0.0
        free_vram_gib = (torch.cuda.mem_get_info(0)[0] / 1024.0 ** 3) if (torch.cuda.is_available() and hasattr(torch.cuda, 'mem_get_info')) else vram_gib
        weight_files = [model_dir] if is_single_file else (list(model_dir.rglob('*.safetensors')) + list(model_dir.rglob('*.bin')) + list(model_dir.rglob('*.gguf')))
        disk_weight_gib = sum((f.stat().st_size for f in weight_files if f.is_file())) / (1024.0 ** 3)
        safe_full_gpu_gib = max(6.5, min(vram_gib - 4.8, free_vram_gib - 3.2))
        gpu_budget_gib = max(10, int(min(vram_gib - 2.2, max(10.0, free_vram_gib - 1.8)))) if vram_gib > 0 else 10
        max_mem = {0: f'{gpu_budget_gib}GiB', 'cpu': '48GiB'}
        extra_load_kw = {'gguf_file': model_dir.name} if (is_single_file and model_dir.suffix.lower() == '.gguf') else {}
        if dev == 'cuda' and disk_weight_gib > 0.1 and disk_weight_gib <= safe_full_gpu_gib:
            model = model_cls.from_pretrained(str(load_dir), dtype=dtype, attn_implementation='sdpa', low_cpu_mem_usage=True, trust_remote_code=True, **extra_load_kw).to(dev)
        else:
            loaded_8bit = False
            q8_dev_map = {'': 0} if (vram_gib >= 14.0 and disk_weight_gib <= 20.0) else 'auto'
            q8_max_mem = None if q8_dev_map == {'': 0} else max_mem
            q8_cache_dir = load_dir.parent / f'{load_dir.name}_ez_q8_safetensors_cache' if (not is_single_file and not extra_load_kw) else None
            if dev == 'cuda' and q8_cache_dir is not None and (q8_cache_dir / 'config.json').exists() and any(q8_cache_dir.glob('*.safetensors')):
                try:
                    print(f'[EZ-QWEN3-VL] ⚡ Loading pre-quantized NVMe Q8 Safetensors cache: {q8_cache_dir.name} ...')
                    model = model_cls.from_pretrained(str(q8_cache_dir), attn_implementation='sdpa', device_map=q8_dev_map, max_memory=q8_max_mem, low_cpu_mem_usage=True, trust_remote_code=True)
                    loaded_8bit = True
                except Exception:
                    model = None
                    gc.collect()
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
            if dev == 'cuda' and (not loaded_8bit) and (not extra_load_kw) and (disk_weight_gib > safe_full_gpu_gib):
                try:
                    from transformers import BitsAndBytesConfig
                    bnb_cfg = BitsAndBytesConfig(load_in_8bit=True, llm_int8_enable_fp32_cpu_offload=True, llm_int8_skip_modules=['visual', 'model.visual', 'lm_head'])
                    print(f'[EZ-QWEN3-VL] ⚡ Model size ({disk_weight_gib:.1f} GiB) exceeds single-shot VRAM budget ({safe_full_gpu_gib:.1f} GiB) -> Loading with Q8 BitsAndBytes quantization (SDPA)...')
                    model = model_cls.from_pretrained(str(load_dir), quantization_config=bnb_cfg, attn_implementation='sdpa', device_map=q8_dev_map, max_memory=q8_max_mem, low_cpu_mem_usage=True, trust_remote_code=True)
                    loaded_8bit = True
                    if q8_cache_dir is not None and (not (q8_cache_dir / 'config.json').exists()):
                        try:
                            q8_cache_dir.mkdir(parents=True, exist_ok=True)
                            model.save_pretrained(str(q8_cache_dir), safe_serialization=True)
                            processor.save_pretrained(str(q8_cache_dir))
                            print(f'[EZ-QWEN3-VL] 💾 Saved persistent Q8 Safetensors cache to NVMe: {q8_cache_dir.name}')
                        except Exception:
                            pass
                except Exception as bnb_err:
                    print(f'[EZ-QWEN3-VL] Q8 BitsAndBytes notice: {bnb_err}')
                    model = None
                    gc.collect()
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
            if not loaded_8bit:
                print(f'[EZ-QWEN3-VL] ⚡ Splitting {disk_weight_gib:.1f} GiB model across GPU ({gpu_budget_gib} GiB) + System RAM (device_map="auto") to prevent CUDA OOM...')
                model = model_cls.from_pretrained(str(load_dir), dtype=dtype, attn_implementation='sdpa', device_map='auto', max_memory=max_mem, offload_buffers=True, low_cpu_mem_usage=True, trust_remote_code=True, **extra_load_kw)
        model.eval()
        in_dev = next(model.parameters()).device if model is not None else torch.device(dev)
        all_pils = []
        if pil_img is not None:
            all_pils.append(pil_img)
        if isinstance(extra_pil_imgs, (list, tuple)):
            for ep in extra_pil_imgs:
                if ep is not None:
                    all_pils.append(ep)
        user_content = []
        for p_im in all_pils:
            user_content.append({'type': 'image', 'image': p_im})
        user_content.append({'type': 'text', 'text': str(user_scene_input)})
        has_imgs = len(all_pils) > 0
        messages = [{'role': 'system', 'content': [{'type': 'text', 'text': system_instruction}] if has_imgs else system_instruction}, {'role': 'user', 'content': user_content if has_imgs else str(user_scene_input)}]
        prompt_text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        if has_imgs:
            inputs = processor(text=[prompt_text], images=all_pils, padding=True, return_tensors='pt').to(in_dev)
        else:
            inputs = processor(text=[prompt_text], padding=True, return_tensors='pt').to(in_dev)
        prompt_text = ''
        messages.clear()
        system_instruction = ''
        eff_max_new = max(640, int(max_new_tokens or 640))
        with torch.no_grad():
            gen_ids = model.generate(**inputs, max_new_tokens=eff_max_new, do_sample=False, use_cache=True)
        in_len = inputs.input_ids.shape[1]
        trimmed = [out_ids[in_len:].detach().cpu().clone() for out_ids in gen_ids]
        out_text = processor.batch_decode(trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0].strip()
        out_text = re.sub(r'(?is)<think>.*?</think>', '', out_text).strip()
        del trimmed
        print(f'[EZ-QWEN3-VL] ✅ Local VLM compiled {len(out_text)} chars ({len(all_pils)} ref image(s)).')
        return out_text
    except Exception as exc:
        print(f'[EZ-QWEN3-VL] Local VLM fallback notice: {exc}')
        return ''
    finally:
        if inputs is not None:
            try:
                _free_cuda_tensor_storage(getattr(inputs, 'data', inputs))
                for k in list(inputs.keys()):
                    inputs[k] = None
            except Exception:
                pass
        inputs = None
        if gen_ids is not None:
            _free_cuda_tensor_storage(gen_ids)
        gen_ids = None
        processor = None
        if model is not None:
            try:
                from accelerate.hooks import remove_hook_from_submodules
                remove_hook_from_submodules(model)
            except Exception:
                pass
            try:
                for p in list(model.parameters()):
                    _free_cuda_tensor_storage(p)
                for b in list(model.buffers()):
                    _free_cuda_tensor_storage(b)
            except Exception:
                pass
            try:
                for m in model.modules():
                    if hasattr(m, '_parameters') and isinstance(m._parameters, dict):
                        for pk, pv in list(m._parameters.items()):
                            _free_cuda_tensor_storage(pv)
                        m._parameters.clear()
                    if hasattr(m, '_buffers') and isinstance(m._buffers, dict):
                        for bk, bv in list(m._buffers.items()):
                            _free_cuda_tensor_storage(bv)
                        m._buffers.clear()
            except Exception:
                pass
            del model
        if hasattr(comfy.model_management, 'soft_empty_cache'):
            comfy.model_management.soft_empty_cache()
        gc.collect()
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            if hasattr(torch.cuda, 'ipc_collect'):
                torch.cuda.ipc_collect()
            try:
                torch.cuda.reset_peak_memory_stats()
            except Exception:
                pass

def _scrub_nsfw_terms_for_sfw(text_in: str) -> str:
    s = str(text_in or '')
    cov_repl = 'modest full-coverage attire'
    s = re.sub(r'(?i)\btoo\s+small\s+to\s+cover\s+(?:her|his|their)\s+[^.,;]+', 'providing complete modest coverage', s)
    s = re.sub(r'(?i)\b(?:beautiful\s+and\s+)?sexy\b', 'charismatic and poised', s)
    cleaned = re.sub(
        r'(?i)\b(?:nude|nudity|naked|topless|bottomless|unclothed|undressed|strip(?:ping|ped)?|nipples?|areolas?|breasts?|boobs?|tits?|cleavage|underboob|sideboob|lingerie|bikini|thong|panties|underwear|bra|corset|sheer|see[-\s]?through|translucent|revealing|plunging|seductive|sensual|erotic|intimate|nsfw|sex|sexual|intercourse|orgasm|climax|moan(?:ing|s)?|groan(?:ing|s)?|pelvis|pelvic|groin|genitals?|genitalia|pussy|vagina|labia|vulva|penis|dick|cock|erection|testicles?|balls|anus|anal|ass|buttocks|booty|cum|semen|sperm|milky\s+liquid|aroused|lustful|lust(?!\s+for\s+(?:life|living|power|battle|adventure|glory|knowledge|freedom|victory|gold|speed)\b)|lewd|horny|explicit|skimpy|scantily\s+clad|bare\s+(?:skin|chest|breasts?|torso|midriff|hips?|thighs?|buttocks|back))\b',
        cov_repl,
        s,
    )
    return re.sub(rf'(?:{re.escape(cov_repl)}[\s,]*){{2,}}', f'{cov_repl} ', cleaned).strip()


def _reconcile_custom_negative_style_collision(custom_neg_str: str, resolved_style: str, style_neg_lead: str) -> str:
    c_str = str(custom_neg_str or '').strip()
    if not c_str:
        return ''
    st_low = str(resolved_style or '').strip().lower()
    conflict_map = {
        'semi-real': r'(?i)\b(?:semi[-\s]?realistic|stylized\s+3d|arcane\s+style|blizzard\s+style|video\s+game\s+cgi)\b',
        'anime': r'(?i)\b(?:anime|manga|cel[-\s]?shading|2d\s+illustration)\b',
        'cartoonish': r'(?i)\b(?:cartoon(?:ish)?|flat\s+2d\s+cartoon|cel[-\s]?shading)\b',
        'realism': r'(?i)\b(?:raw\s+candid\s+photograph|live[-\s]?action\s+photograph|arri\s+alexa\s+live[-\s]?action|photorealistic,\s*semi[-\s]?realistic,\s*2\.5d)\b',
    }
    pat = conflict_map.get(st_low)
    if not pat or not re.search(pat, c_str):
        return c_str
    def _strip_colliding_paren_group(match_obj) -> str:
        grp = match_obj.group(0)
        if re.search(pat, grp):
            return f'{style_neg_lead}, ' if style_neg_lead else ''
        return grp
    healed = re.sub(r'\([^()]*:1\.\d+\)\s*,?\s*', _strip_colliding_paren_group, c_str)
    if healed == c_str:
        healed = re.sub(rf'{pat}\s*,?\s*', '', c_str)
        if style_neg_lead and style_neg_lead[:24].lower() not in healed.lower():
            healed = f'{style_neg_lead}, {healed}'
    healed = re.sub(r'(?:,\s*){2,}', ', ', healed).strip().strip(',').strip()
    return healed



def _parse_subject_age_years(resolved_age: str) -> int:
    s = str(resolved_age or '25-year-old').strip().lower()
    if 'ageless' in s or 'cyborg' in s:
        return 23
    m = re.search(r'(\d{1,3})', s)
    if m:
        return max(18, min(95, int(m.group(1))))
    if any(k in s for k in ('teen', 'young', 'ung')):
        return 19
    if any(k in s for k in ('elder', 'old', 'ancient', 'gammal', 'äldre')):
        return 60
    if any(k in s for k in ('middle', 'mature', 'medelålders')):
        return 42
    return 25


def _has_explicit_facial_metal_request(text_in: str) -> bool:
    return bool(
        re.search(
            r'(?i)\b(?:face\s+(?:armor|metal|plate|guard|mask)|facial\s+(?:metal|armor|piercing|stud|ring|implant|plate)|chin\s+(?:plate|guard|armor|metal|spike|stud|piercing|strap)|jaw\s+(?:plate|armor|metal|guard)|metal\s+(?:chin|jaw|face|mask|cheek)|lip\s+(?:ring|piercing|stud)|nose\s+(?:ring|piercing|stud|septum)|septum\s+ring|cybernetic\s+face|faceplate|visor|helmet|full[-\s]?helm)\b',
            str(text_in or ''),
        )
    )


def _scrub_unrequested_facial_metal(text_in: str, user_scene_input: str = '') -> str:
    if _has_explicit_facial_metal_request(user_scene_input):
        return str(text_in or '')
    s = str(text_in or '')
    s = re.sub(
        r'(?i)\b(?:metallic|metal|steel|iron|silver|chrome|spiked)\s+(?:chin|jaw|facial|cheek|lip)\s+(?:plate|guard|ornament|stud|spike|armor|piece|trim)s?\b',
        'unarmored natural chin',
        s,
    )
    s = re.sub(
        r'(?i)\b(?:chin|jaw|facial|lip)\s+(?:plate|guard|armor|piercing|stud|ring|spike)s?\b',
        'unarmored natural chin',
        s,
    )
    return s


def _build_age_authority_profile(resolved_age: str, is_female: bool = True, has_orc_tusks: bool = False, allow_facial_metal: bool = False, style_target: str = 'original', tusk_descriptor: str = '', is_non_human: bool = False, species_lock_phrase: str = '', user_scene_input: str = '') -> dict:
    age_s = str(resolved_age or '25-year-old').strip()
    if user_scene_input and not is_non_human:
        _sp_auto = _detect_subject_taxonomy_and_species_lock(user_scene_input, '', age_s)
        if _sp_auto['use_auto_age_bypass']:
            is_non_human = True
            if not species_lock_phrase:
                species_lock_phrase = _sp_auto['species_lock_clause']
    if is_non_human or not age_s or age_s.lower().startswith('auto'):
        spec_id = str(species_lock_phrase or '').strip() or 'preserving exact subject morphology, natural surface texture, and authentic proportions'
        vlm_auto = (
            f'- SUBJECT MORPHOLOGY & TAXONOMY LOCK: Preserve <Subject 1> ({spec_id}) strictly from the prompt and reference image without inventing human age labels, human facial features, or clothing.'
            if species_lock_phrase else
            '- SUBJECT AGE & MORPHOLOGY: Follow the exact age, species, and morphology of <Subject 1> from the prompt and reference image without forced age overrides.'
        )
        return {'age_label': '', 'age_years': 25, 'lead_badge': '', 'face_id_phrase': spec_id, 'vlm_rule': vlm_auto, 'neg_tokens': ''}
    if re.fullmatch(r'\d{1,2}', age_s):
        age_s = f'{age_s}-year-old'
    yrs = _parse_subject_age_years(age_s)
    st_low = str(style_target or 'original').strip().lower()
    skin_adj = 'crisp 2D cel-shaded anime skin' if st_low == 'anime' else ('clean 2D cel-shaded cartoon skin' if st_low == 'cartoonish' else 'natural skin texture')
    vault = _load_licensed_allan_ballan_vault()
    vault_age = (vault.get('age_profiles') or {}) if isinstance(vault, dict) else {}
    chin_guard_clause = ''
    eff_tusk_desc = str(tusk_descriptor or '').strip() or 'two sharp protruding white lower-jaw tusks growing upward out from the lower jaw'
    tusk_clause = f', prominently featuring {eff_tusk_desc}' if has_orc_tusks else ''
    face_metal_vlm = ''
    if yrs <= 20:
        tier_k = '20_and_under'
        alt_k = '18_20'
        def_lead = f'Youthful {age_s} young-adult character with fresh {skin_adj}, bright expressive eyes{chin_guard_clause}{tusk_clause}, and zero aging lines.'
        def_face = f'preserving exact facial bone structure, eye color, nose, lips, and {age_s} youthful {skin_adj}{chin_guard_clause}{tusk_clause}'
        def_neg = "(mature adult, 30-year-old, 40-year-old, 50-year-old, 60-year-old, middle-aged, old face, aged face, elderly, wrinkles, facial lines, nasolabial folds, crow's feet, forehead creases, weathered skin, sagging cheeks:1.95)"
    elif yrs <= 24:
        tier_k = '21_to_24'
        alt_k = '21_24'
        def_lead = f'Fresh {age_s} young adult in their early twenties with smooth {skin_adj}, defined cheekbones, expressive gaze{chin_guard_clause}{tusk_clause}, and zero aging lines.'
        def_face = f'preserving exact facial bone structure, eye color, nose, lips, and {age_s} young-adult {skin_adj}{chin_guard_clause}{tusk_clause}'
        def_neg = "(35-year-old, 40-year-old, 50-year-old, 60-year-old, middle-aged, old face, aged face, elderly, deep wrinkles, nasolabial folds, crow's feet, forehead wrinkles, weathered skin, sagging cheeks:1.9)"
    elif yrs <= 29:
        tier_k = '25_to_29'
        alt_k = '25_29'
        def_lead = f'Poised {age_s} prime young-adult character with sculpted cheekbones, defined jawline, {skin_adj}{chin_guard_clause}{tusk_clause}, and zero middle-aged creases.'
        def_face = f'preserving exact facial bone structure, eye color, nose, lips, and {age_s} young-adult {skin_adj}{chin_guard_clause}{tusk_clause}'
        def_neg = "(baby face, childlike teen face, 40-year-old, 45-year-old, 50-year-old, 60-year-old, middle-aged, old wrinkled face, aged face, elderly, deep nasolabial folds, crow's feet, forehead wrinkles, sagging jowls:1.85)"
    elif yrs <= 37:
        tier_k = '30_to_37'
        alt_k = '30_37'
        def_lead = f'Poised {age_s} adult in their thirties with contoured mature cheekbones, composed facial definition, {skin_adj}{chin_guard_clause}{tusk_clause}, and subtle natural expression lines.'
        def_face = f'preserving exact facial bone structure, eye color, nose, lips, and {age_s} prime-adult {skin_adj}{chin_guard_clause}{tusk_clause}'
        def_neg = '(18-year-old teen face, baby face, juvenile face, 60-year-old elderly face, severe geriatric wrinkles, decrepit aged face:1.75)'
    elif yrs <= 49:
        tier_k = '38_to_49'
        alt_k = '38_49'
        def_lead = f'Seasoned {age_s} middle-aged character in their forties with distinct mature facial structure, visible crow\'s feet, defined nasolabial lines, and mature {skin_adj}{chin_guard_clause}{tusk_clause}.'
        def_face = f'preserving exact facial bone structure, eye color, nose, lips, and {age_s} mature {skin_adj}{chin_guard_clause}{tusk_clause}'
        def_neg = '(18-year-old, 21-year-old, 25-year-old, teenage face, baby-smooth unblemished teen skin, juvenile face, poreless doll skin:1.85)'
    else:
        tier_k = '50_plus'
        alt_k = '50_plus'
        def_lead = f'Aged {age_s} elder character with deep facial wrinkles, pronounced forehead and nasolabial creases, weathered aged {skin_adj}, and silver-streaked hair{chin_guard_clause}{tusk_clause}.'
        def_face = f'preserving exact facial bone structure, eye color, nose, lips, and {age_s} distinguished {skin_adj}{chin_guard_clause}{tusk_clause}'
        def_neg = '(18-year-old, 21-year-old, 25-year-old, 30-year-old, youthful smooth skin, unwrinkled teen face:1.9)'
    tier_cfg = (vault_age.get(tier_k) or vault_age.get(alt_k) or {}) if isinstance(vault_age, dict) else {}
    fmt_map = {'age_s': age_s, 'skin_adj': skin_adj, 'chin_guard_clause': chin_guard_clause, 'tusk_clause': tusk_clause, 'face_metal_vlm': face_metal_vlm}
    raw_lead_tpl = str(tier_cfg.get('lead_tpl') or tier_cfg.get('lead') or def_lead)
    raw_face_tpl = str(tier_cfg.get('face_id_tpl') or tier_cfg.get('face_id') or def_face)
    for k_f, v_f in fmt_map.items():
        raw_lead_tpl = raw_lead_tpl.replace(f'{{{k_f}}}', v_f)
        raw_face_tpl = raw_face_tpl.replace(f'{{{k_f}}}', v_f)
    if has_orc_tusks and 'tusk' not in raw_lead_tpl.lower() and 'fang' not in raw_lead_tpl.lower():
        raw_lead_tpl = f"{raw_lead_tpl.rstrip('. ')}{tusk_clause}."
    if has_orc_tusks and 'tusk' not in raw_face_tpl.lower() and 'fang' not in raw_face_tpl.lower():
        raw_face_tpl = f'{raw_face_tpl}{tusk_clause}'
    lead = raw_lead_tpl
    face_id = raw_face_tpl
    raw_neg = str(tier_cfg.get('neg') or def_neg).strip()
    neg = raw_neg if raw_neg.startswith('(') else f'({raw_neg}:1.85)'
    vlm = f'- ABSOLUTE NODE AGE AUTHORITY ({age_s} — OVERRIDES ALL PROMPT/IMAGE AGES): <Subject 1> MUST be depicted strictly as {age_s} ({face_id}).{face_metal_vlm}'
    return {'age_label': age_s, 'age_years': yrs, 'lead_badge': lead, 'face_id_phrase': face_id, 'vlm_rule': vlm, 'neg_tokens': neg}


def _apply_age_override_to_text(text_in: str, resolved_age: str, is_non_human: bool = False) -> str:
    txt = str(text_in or '')
    age_s = str(resolved_age or '').strip()
    if is_non_human or not age_s or age_s.lower().startswith('auto'):
        return txt
    if re.fullmatch(r'\d{1,2}', age_s):
        age_s = f'{age_s}-year-old'
    yrs = _parse_subject_age_years(age_s)
    has_second_char = bool(
        re.search(r'(?i)(?:<\s*(?:main[_\s-]*)?subject\s*[2-9]\s*>|\bcharacter\s*[2-9]\b|\bon\s+the\s+right\b|\binterviewing\b|\btwo[-\s]?shot\b)', txt)
    )
    if has_second_char:
        return txt
    txt = re.sub(r'(?i)\b\d{1,2}[-\s]?(?:year|yr)s?[-\s]?old\b', age_s, txt)
    txt = re.sub(r'(?i)\b\d{1,2}\s*(?:y/o|yo|år\s+gammal|årig(?:a)?)\b', age_s, txt)
    txt = re.sub(r'(?i)\bage(?:d)?\s+\d{1,2}\b', f'aged {yrs}', txt)
    txt = re.sub(r'(?i)\bin\s+(?:her|his|their)\s+(?:early\s+|mid[-\s]?|late\s+)?(?:teens|twenties|thirties|forties|fifties|sixties|seventies|\d0s)\b', f'at {age_s}', txt)
    if yrs <= 29:
        txt = re.sub(r'(?i)\b(?:middle[-\s]?aged|elderly|geriatric|ancient|old\s+and\s+wrinkled|wrinkled\s+old|old\s+weathered|weathered\s+old|grizzled|deeply\s+wrinkled|heavily\s+wrinkled|battle[-\s]?worn\s+face|weathered\s+face|wrinkled\s+face|medelålders|äldre|gammal|rynkig)\b', f'youthful {age_s}', txt)
        if yrs <= 21:
            txt = re.sub(r'(?i)\b(?:mature\s+woman|mature\s+female|mature\s+adult|seasoned\s+veteran)\b', f'youthful {age_s} young adult', txt)
    elif yrs >= 40:
        txt = re.sub(r'(?i)\b(?:teenage(?:r)?|adolescent|18[-\s]?year[-\s]?old|21[-\s]?year[-\s]?old|25[-\s]?year[-\s]?old|baby[-\s]?smooth|unwrinkled\s+youthful|youthful\s+teen(?:age)?)\b', f'mature {age_s}', txt)
    return txt


def _scrub_unrequested_genital_hallucinations(text_in: str, user_scene_input: str = '') -> str:
    s = str(text_in or '')
    u_raw = str(user_scene_input or '')
    if _prompt_requests_explicit_erotica(u_raw) or re.search(r'(?i)\b(?:nip\s*slip|panties|thong|lingerie|bikini|cleavage|breasts?|boobs?|nude|naked|topless|bottomless|pussy|vagina|labia|vulva|penis|cock|dick|ass|buttocks|squat(?:s|ting)?)\b', u_raw):
        return s
    s = re.sub(
        r'(?i)\bthat\s+(?:partially\s+|barely\s+)?(?:occludes|covers|hides|conceals|exposes|reveals)\s+(?:her|his|their)\s+(?:large\s+|wet\s+|bare\s+)?(?:vulva|vagina|labia(?:\s+majora|\s+minora)?|pussy|clit(?:oris)?|genitals?|genitalia|anus|penis|cock|dick)[^.,;]*',
        'fitting naturally over the lower body',
        s,
    )
    return s


def _scrub_sfx_vocal_triggers(text_in: str, user_scene_input: str = '') -> str:
    s = str(text_in or '')
    if not s:
        return ''
    u_low = str(user_scene_input or '').lower()
    if not any(w in u_low for w in ('sing', 'song', 'choir', 'lyrics', 'chant', 'ballad', 'opera', 'sjung', 'sång')):
        s = re.sub(
            r'(?i)\b(?:singing\s+(?:a\s+song|lyrics|melodiously|aloud)|song\s+lyrics|operatic\s+vocals|backing\s+choir|a\s+cappella\s+vocals)\b',
            'natural ambient acoustics',
            s,
        )
    if bool(_extract_prompt_morphology_profile(s)['has_tusks']):
        s = re.sub(
            r'(?i)\b(?:firmly\s+closed\s+mouth|tightly\s+closed\s+lips|sealed\s+lips)\b',
            'natural expression with two sharp protruding white lower-jaw tusks clearly visible outside the lips',
            s,
        )
    return s


def _extract_shot_carryover_state(shot_text: str, shot_idx: int, resolved_zoom: str, safe_cam_move: str, allow_camera_movement: bool, continuity_mode: str = 'locked_stage_environment', is_scene_cut: bool = False) -> str:
    if continuity_mode == 'hollywood_multi_scene_cuts' and is_scene_cut:
        return '[SCENE CUT] Cutting cleanly to the next cinematic camera setup while preserving <Subject 1>\'s exact identity and morphology from <Picture 1>, '
    s_clean = re.sub(r'\s+', ' ', str(shot_text or '')).strip()
    if not s_clean:
        return ''
    s_clean = re.sub(r'(?i)\[\s*SCENE[\s_-]*CUT\s*\]\s*', '', s_clean).strip()
    for _ in range(4):
        next_s = re.sub(
            r'(?i)^(?:Continuing\s+seamlessly\s+from\s+the\s+final\s+frame\s+of\s+Shot\s+\d+\s*(?:\([^)]*\))?\s*,?\s*|Cutting\s+cleanly\s+to\s+the\s+next\s+cinematic\s+camera\s+setup[^,]*,\s*|Cutting\s+to\s+a\s+new\s+cinematic\s+(?:angle|setup)[^:,\n]*[:,\s]+|From\s+this\s+exact\s+held\s+posture,\s*)',
            '',
            s_clean,
        ).strip()
        if next_s == s_clean:
            break
        s_clean = next_s
    sents = [
        s.strip()
        for s in re.split(r'(?<=[.!?])\s+', s_clean)
        if s.strip() and not re.search(r'(?i)^(?:Locked\s+to|Captured\s+with|Filmed\s+with|<Subject\s*\d+>\s+(?:preserves|keeps\s+a\s+focused)|Maintaining\s+the\s+exact\s+room)', s.strip())
    ]
    last_action = sents[-1] if sents else s_clean[:140]
    last_action = re.sub(r'(?i)^Cutting\s+to\s+a\s+new\s+cinematic\s+(?:angle|setup)[^:,\n]*[:,\s]+', '', last_action).strip()
    last_action = re.sub(r'(?i)\(\s*\d{1,2}-year-old[^)]*\)', '', last_action)
    last_action = re.sub(r'(?i)<\s*(?:main[_\s-]*)?subject\s*\d+\s*>', 'the protagonist', last_action)
    last_action = last_action.replace('(', '').replace(')', '')
    last_action = re.sub(r'\s{2,}', ' ', last_action).strip(' ,;:-.')
    if len(last_action) > 115:
        last_action = last_action[:115].rsplit(' ', 1)[0].strip(' ,;:-.')
    last_action = re.sub(
        r'(?i)(?:[\s,;:\-]+(?:with|and|or|while|as|into|from|of|the|a|an|her|his|their|in|on|at|to|by|across|window|\d+|<subject\s*\d*>))+$',
        '',
        last_action,
    ).strip(' ,;:-.')
    if len(last_action) < 8:
        last_action = 'the active performance and spatial momentum'
    cam_state = f'continuing the {safe_cam_move}' if allow_camera_movement else f'holding the exact {resolved_zoom} camera distance'
    return f'Continuing seamlessly from the final frame of Shot {shot_idx} ({cam_state} following {last_action}), '


def _scrub_leaked_compiler_meta_directives(text_in: str) -> str:
    s = str(text_in or '')
    if not s:
        return ''
    s = re.sub(r'(?is)\[\s*ACTIVE\s+RUNTIME\s+COMPILER\s+PARAMETERS\s*\][\s\S]*$', '', s)
    s = re.sub(r'(?im)^\s*-\s*(?:MASTER_DURATION|SCENE_CONTINUITY_MODE|MULTI-WINDOW\s+CONTINUITY|MULTI-SCENE\s+HOLLYWOOD|CONTINUOUS\s+ONE-SHOT|STYLE_TARGET|CAMERA_ZOOM|CAMERA_MOVEMENT|LIGHTING_MODE|AUDIO_MODE|SUBJECT_1_AGE)\b[^\n]*$', '', s)
    s = re.sub(r'(?is)-?\s*MULTI-WINDOW\s+CONTINUITY\s*&\s*STATE\s+CARRYOVER\s*\([^)]*?WORDS\s+PER\s+SHOT\)\s*:\s*Write\s+all\s+\d+\s+sequential\s+shot\s+sections.*?continuation\s+windows\.?', '', s)
    s = re.sub(r'(?is)\|\s*TARGET\s+LENGTH\s*:\s*\d+\s*-\s*\d+\s*WORDS\s+TOTAL[^.\n]*?(?:descriptive\s+richness(?:\s+as\s+\[Shot\s*1\])?\)?\.?|[\n])', ' ', s)
    s = re.sub(r'(?is)Every\s+\[\s*Shot\s*K\s*\][^\n]*?continuation\s+windows\.?', ' ', s)
    s = re.sub(r'(?is)-\s*STYLE_TARGET\s*=\s*[^\n]*?CAMERA_ZOOM\s*=\s*[a-zA-Z0-9_\-]+\.?', ' ', s)
    s = re.sub(r'(?i)—\s*LOCK\s+IDENTICAL\s+TRANSFORMATION,\s*SHADING,\s*AND\s+LIGHTING\s+ACROSS\s+ALL\s+SHOTS\)?', ' ', s)
    s = re.sub(r'(?:\(\s*(?:,\s*)*\)|(?:\s*,\s*){2,}\)\s*\.?)', ' ', s)
    return re.sub(r'[ \t]{2,}', ' ', s).strip()


def _normalize_qwenvl_two_block_output(compiled_raw: str, clean_in: str, resolved_age: str, age_diff_phrase: str, resolved_zoom: str, resolved_lighting: str, resolved_cam_move: str, aesthetic_rule: str, resolved_duration: str, cut_1: str, cut_2: str, resolved_style: str='realism', is_nsfw: bool=True, resolved_audio_mode: str='sfx_only', rating_tier: str='uncensored_action', allow_camera_movement: bool=False, resolved_stance: str='', background_extras_crowd: str='', slot2_is_dual_subject: bool=False, has_reference_image: bool=False, resolved_continuity_mode: str='locked_stage_environment'):
    raw_txt = _scrub_leaked_compiler_meta_directives(str(compiled_raw or '').replace('```', '').strip())
    subj_tax_norm = _detect_subject_taxonomy_and_species_lock(clean_in, raw_txt, resolved_age, has_reference_image=has_reference_image)
    is_non_human_norm = bool(subj_tax_norm['is_non_human'])
    use_auto_age_norm = bool(subj_tax_norm['use_auto_age_bypass'])
    clean_in = _apply_age_override_to_text(clean_in, resolved_age, is_non_human=use_auto_age_norm)
    raw_txt = _apply_age_override_to_text(raw_txt, resolved_age, is_non_human=use_auto_age_norm)
    if is_non_human_norm:
        if not bool(re.search(r'(?i)\b\d{1,2}[-\s]?(?:year|yr)s?[-\s]?old\b', clean_in)):
            raw_txt = re.sub(r'(?i)\b\d{1,2}[-\s]?(?:year|yr)s?[-\s]?old\s+', '', raw_txt)
        if (not subj_tax_norm['is_avian']) and (not subj_tax_norm['allows_metamorphosis']) and subj_tax_norm['matched_species']:
            raw_txt = _SUBJECT_AVIAN_REGEX.sub(subj_tax_norm['matched_species'], raw_txt)
    if not is_nsfw or rating_tier == 'sfw':
        raw_txt = _scrub_nsfw_terms_for_sfw(raw_txt)
        clean_in = _scrub_nsfw_terms_for_sfw(clean_in)
    if re.search(r'(?i)Continuity\s+part\s*#\s*\d+', clean_in):
        structured_b2 = clean_in.strip()
        m_first_shot = re.search(r'(?i)\[Shot\s*1\]\s*([^\n]+)', structured_b2)
        structured_b1 = m_first_shot.group(1).strip() if m_first_shot else clean_in[:600].strip()
        return (structured_b1, structured_b2)
    m_dur_n = re.search(r'(\d+(?:\.\d+)?)', str(resolved_duration or '20-second'))
    dur_sec_val = float(m_dur_n.group(1)) if m_dur_n else 20.0
    num_target_shots = max(3, min(72, int(math.ceil(dur_sec_val / 5.0)))) if dur_sec_val >= 20.0 else 3
    explicit_shots_found = [int(m.group(1)) for m in re.finditer(r'(?i)\[\s*Shot\s*(\d+)[^\]]*\]', raw_txt)]
    if explicit_shots_found:
        num_target_shots = max(num_target_shots, min(72, max(explicit_shots_found)))
    shot_keys = [f'[Shot {i}]' for i in range(1, num_target_shots + 1)]
    raw_txt = re.sub('(?im)^\\s*[#*\\-\\s]*BLOCK\\s*1[\\s:*#\\-]*$', 'BLOCK 1', raw_txt)
    raw_txt = re.sub('(?im)^\\s*[#*\\-\\s]*BLOCK\\s*2[\\s:*#\\-]*$', 'BLOCK 2', raw_txt)
    raw_txt = re.sub('(?im)^\\s*[#*\\-\\s]*\\[?IMAGE\\]?[\\s:*#\\-]*$', '[IMAGE]', raw_txt)
    for idx in range(1, num_target_shots + 1):
        raw_txt = re.sub(f'(?i)\\[\\s*Shot\\s*{idx}\\b[^\\]\\n]*\\][\\s:*#\\-]*', f'\n[Shot {idx}]\n', raw_txt)
        raw_txt = re.sub(f'(?im)^\\s*[#*\\-\\s]*Shot\\s*{idx}\\b(?:\\s*\\([^)\\n]*\\))?\\s*(?:[:\\-]+\\s*|\\s*$)', f'[Shot {idx}]\n', raw_txt)
    raw_txt = re.sub('(?i)\\[\\s*Constraints[^\\]\\n]*\\][\\s:*#\\-]*', '\n[Constraints]\n', raw_txt)
    raw_txt = re.sub('(?im)^\\s*[#*\\-\\s]*Constraints\\s*(?:[:\\-]+\\s*|\\s*$)', '[Constraints]\n', raw_txt)
    raw_txt = re.sub('(?i)\\[\\s*Overall\\s+Soundscape[^\\]\\n]*\\][\\s:*#\\-]*', '\n[Overall Soundscape]\n', raw_txt)
    raw_txt = re.sub('(?im)^\\s*[#*\\-\\s]*Overall\\s+Soundscape\\s*(?:[:\\-]+\\s*|\\s*$)', '[Overall Soundscape]\n', raw_txt)
    raw_txt = re.sub('(?i)\\[\\s*Non-Diegetic\\s+Music[^\\]\\n]*\\][\\s:*#\\-]*', '\n[Non-Diegetic Music]\n', raw_txt)
    raw_txt = re.sub('(?im)^\\s*[#*\\-\\s]*Non-Diegetic\\s+Music\\s*(?:[:\\-]+\\s*|\\s*$)', '[Non-Diegetic Music]\n', raw_txt)
    style_low = str(resolved_style or 'realism').strip().lower()
    cont_mode_norm = str(resolved_continuity_mode or 'locked_stage_environment').strip().lower()
    is_dynamic_env_mode = cont_mode_norm in ('continuous_one_shot', 'hollywood_multi_scene_cuts')
    if is_dynamic_env_mode:
        allow_camera_movement = True
    style_prof = _get_style_compiler_profile(resolved_style, clean_in)
    style_lead = style_prof['lead']
    style_tail = style_prof['tail']
    video_style_lead = style_prof['video_lead']
    (zoom_desc, light_desc) = _get_zoom_and_lighting_specs(resolved_zoom, resolved_lighting, style_low, user_scene_input=clean_in, background_extras_crowd=background_extras_crowd, has_reference_image=has_reference_image)
    resolved_cam_move = _sanitize_camera_movement_for_settings(resolved_cam_move, resolved_zoom, style_low, allow_camera_movement=allow_camera_movement, user_scene_input=clean_in, background_extras_crowd=background_extras_crowd)
    is_indoor_scene = (not is_dynamic_env_mode) and bool(
        re.search(r'(?i)\b(?:studio|news\s+desk|broadcast|indoor|indoors|interior|room|office|tavern|bar|cockpit|interview(?:ing)?|anchor|teleprompter|desk)\b', clean_in)
    ) and not bool(re.search(r'(?i)\b(?:wind|windy|breeze|storm|gale|blizzard|gusts?)\b', clean_in))
    cast_norm_info = _analyze_scene_cast_and_extras(clean_in, resolved_stance, background_extras_crowd, slot2_is_dual_subject=slot2_is_dual_subject, age_difference=(age_diff_phrase or 'none (single subject)'))
    clean_in_no_suno = re.sub(r'(?is)\[SUNO\s+RHYTHMIC[\s\S]*$', '', clean_in).strip() or clean_in
    clean_in_no_suno = re.sub(r'(?is)\[MANDATORY MULTI-IMAGE REFERENCE BINDING\]:.*?\n\n', '', clean_in_no_suno).strip()
    clean_in_no_suno = re.sub(
        r'(?i)\s*(?:Use Reference Slot #1 strictly for|Preserve the primary protagonist \(<Main_Subject 1>\)|Include the second main protagonist \(<Main_Subject 2>\)|SINGLE SUBJECT ONLY: Render a single unified protagonist|Dress the character seamlessly in the exact armor/clothing|Place the character seamlessly inside the exact environment|Use Reference Video Slot #5)[^.\n]*\.?',
        '',
        clean_in_no_suno,
    ).strip() or clean_in
    narrative_beat_plan = _split_general_narrative_beats(clean_in_no_suno, num_target_shots, cont_mode_norm)
    in_paras = [p.strip() for p in re.split(r'\n\s*\n', clean_in_no_suno) if p.strip()]
    action_marker_pat = r'(?i)(?:^\s*(?:a\s+sequence\s+starting|at\s+the\s+midpoint|from\s+00:|at\s+00:|in\s+shot\s+\d|then\s+she|then\s+he|suddenly\s+she|suddenly\s+he)|\b(?:midpoint\s+of\s+the\s+sequence|initiates\s+a\s+sudden|explosively\s+swinging|slams\s+violently)\b)'
    static_paras = [p for p in in_paras if not re.search(action_marker_pat, p)]
    action_paras = [p for p in in_paras if re.search(action_marker_pat, p)]
    if is_dynamic_env_mode and narrative_beat_plan:
        static_clean_in = narrative_beat_plan[0]['text']
    else:
        static_clean_in = ' '.join(static_paras).strip() if static_paras else (in_paras[0] if in_paras else clean_in_no_suno)
    morph_norm = _extract_prompt_morphology_profile(clean_in_no_suno)
    has_orc_tusks_norm = bool(morph_norm['has_tusks'])
    wants_face_metal_norm = _has_explicit_facial_metal_request(clean_in)
    age_prof = _build_age_authority_profile(resolved_age, is_female=True, has_orc_tusks=has_orc_tusks_norm, allow_facial_metal=wants_face_metal_norm, style_target=resolved_style, tusk_descriptor=morph_norm['feat_desc'], is_non_human=use_auto_age_norm, species_lock_phrase=subj_tax_norm['species_lock_clause'])
    age_lead_badge = age_prof['lead_badge']
    light_sentence = f' Illuminated by {light_desc}.' if light_desc else ''
    if age_prof['age_label']:
        default_b1 = f'{style_lead} {zoom_desc}. {age_lead_badge} {static_clean_in} Depicted strictly as a {age_prof["age_label"]} character{age_diff_phrase}.{light_sentence} {style_tail} Full-bleed edge-to-edge composition.'
    else:
        spec_clause_b1 = subj_tax_norm.get('species_lock_clause') or ''
        spec_sent_b1 = f' {spec_clause_b1[0].upper() + spec_clause_b1[1:]}.' if spec_clause_b1 else ''
        default_b1 = f'{style_lead} {zoom_desc}. {static_clean_in}{spec_sent_b1}{light_sentence} {style_tail} Full-bleed edge-to-edge composition.'
    if 'BLOCK 2' in raw_txt:
        (p1, p2) = raw_txt.split('BLOCK 2', 1)
    elif '[Shot 1]' in raw_txt:
        (p1, p2) = raw_txt.split('[Shot 1]', 1)
        p2 = '[Shot 1]\n' + p2
    else:
        paras = [p.strip() for p in re.split('\\n\\s*\\n', raw_txt) if p.strip()]
        p1 = static_clean_in if (static_paras and action_paras) else (paras[0] if paras else default_b1)
        p2 = '\n\n'.join(action_paras) if action_paras else ('\n\n'.join(paras[1:]) if len(paras) > 1 else clean_in)
    b1 = re.sub('(?:BLOCK\\s*1|\\[IMAGE\\])', '', p1, flags=re.IGNORECASE).strip()
    b1 = re.split('\\[(?:Shot\\s*\\d+|Constraints|Overall Soundscape|Non-Diegetic Music)\\]', b1, flags=re.IGNORECASE)[0].strip()
    b1 = re.sub('<Subject\\s*\\d+>\\s*,?\\s*', '', b1, flags=re.IGNORECASE)
    b1 = re.sub('\\bSubject\\s*\\d+\\s*[:\\-]?\\s*', '', b1, flags=re.IGNORECASE)
    if not cast_norm_info['has_multi_main_cast']:
        b1 = re.sub(r'(?i)<\s*(?:main[_\s-]*)?subject\s*[2-9]\s*>\s*[:,;\-]?\s*', '', b1)
        b1 = re.sub(r'(?i)\b(?:main[_\s-]*subject|character)\s*[2-9]\b\s*[:,;\-]?\s*', '', b1)
    b1 = re.sub('\\(none\\s*\\(single\\s*subject\\)\\)', '', b1, flags=re.IGNORECASE)
    b1 = re.sub('\\(modern\\s*cinematic\\s*cgi\\)', 'modern cinematic CGI', b1, flags=re.IGNORECASE)
    b1 = _apply_age_override_to_text(b1, age_prof['age_label'], is_non_human=use_auto_age_norm)
    p2 = _apply_age_override_to_text(p2, age_prof['age_label'], is_non_human=use_auto_age_norm)
    if style_prof.get('strip_pat'):
        b1 = re.sub(style_prof['strip_pat'], style_prof['strip_repl'], b1)
        p2 = re.sub(style_prof['strip_pat'], style_prof['strip_repl'], p2)
        rep_esc = re.escape(str(style_prof['strip_repl'] or ''))
        if rep_esc:
            dedup_pat = rf'(?i)(?:{rep_esc})(?:(?:\s*,\s*|\s+and\s+|\s+with\s+|\s+in\s+|\s+)(?:{rep_esc}))+'
            b1 = re.sub(dedup_pat, style_prof['strip_repl'], b1)
            p2 = re.sub(dedup_pat, style_prof['strip_repl'], p2)
    l_low = str(resolved_lighting or 'auto').strip().lower()
    if l_low in ('golden-hour', 'volumetric-day', 'neon-cyberpunk', 'moonlit-noir', 'studio-rim-light'):
        b1 = re.sub(r'(?i)\bunder\s+a\s+gloomy\s+gray\s+sky\b', f'under {light_desc}', b1)
        p2 = re.sub(r'(?i)\bunder\s+a\s+gloomy\s+gray\s+sky\b', f'under {light_desc}', p2)
    z_low = str(resolved_zoom or 'medium-shot').strip().lower()
    if not (has_reference_image and not _has_explicit_prompt_framing_override(clean_in)):
        if 'wide' in z_low or 'establishing' in z_low:
            b1 = re.sub(r'(?i)\b(?:extreme\s+close[-\s]?up|tight\s+close[-\s]?up|medium\s+close[-\s]?up|close[-\s]?up\s+portrait|85mm\s+portrait\s+lens(?:\s+at\s+f/1\.4)?)\b', resolved_zoom, b1)
        elif 'close-up' in z_low:
            b1 = re.sub(r'(?i)\b(?:extreme\s+wide[-\s]?angle|wide[-\s]?shot|full[-\s]?body\s+wide)\b', resolved_zoom, b1)
    if is_indoor_scene:
        indoor_wind_pat = r'(?i)\b(?:wind[-\s]?swept\s+hair(?:\s+motion|\s+movement)?|hair\s+blowing\s+in\s+the\s+wind|blowing\s+in\s+the\s+(?:cold\s+|icy\s+)?wind|fluid\s+hair\s+motion\s+in\s+the\s+wind|in\s+the\s+howling\s+wind|cold\s+wind\s+gusts|howling\s+wind\s+gusts)\b'
        indoor_air_repl = 'calm indoor air' if is_non_human_norm else 'calm indoor studio air with naturally settled hair'
        b1 = re.sub(indoor_wind_pat, indoor_air_repl, b1)
        p2 = re.sub(indoor_wind_pat, indoor_air_repl, p2)
    b1 = re.sub('\\s{2,}', ' ', b1).strip()
    if cast_norm_info['cast_b1_injection'] and 'never a twin or clone' not in b1.lower():
        b1 = f"{b1.rstrip('. ')}. {cast_norm_info['cast_b1_injection']}"
    if len(b1) < 24:
        b1 = default_b1
        b1_scene_core = str(default_b1).strip()
    else:
        for old_lead in (style_lead, video_style_lead, zoom_desc, age_lead_badge):
            if old_lead and b1.lower().startswith(old_lead.lower()[:28]):
                b1 = b1[len(old_lead):].lstrip('. ').strip()
        if has_orc_tusks_norm:
            feat_norm = morph_norm['feat_desc'] or 'two sharp protruding white lower-jaw tusks growing upward out from the lower jaw'
            b1 = re.sub(
                r'(?i)\b(?:with\s+(?:a\s+|her\s+|his\s+)?)?(?:firmly\s+closed\s+mouth|tightly\s+closed\s+lips|closed\s+mouth|sealed\s+lips)\b',
                f'with {feat_norm}',
                b1,
            )
            if 'tusk' not in b1.lower() and 'boar' not in b1.lower():
                b1 = f'Featuring {feat_norm}. {b1}'.strip()
        b1_scene_core = str(b1).strip()
        if cast_norm_info['has_multi_main_cast']:
            s1_hdr = cast_norm_info.get('subj1_summary') or (f"{age_prof['age_label']} primary protagonist" if age_prof['age_label'] else 'primary protagonist')
            if age_prof['age_label'] and age_prof['age_label'].lower() not in s1_hdr.lower():
                s1_hdr = f"{age_prof['age_label']} {s1_hdr}"
            s2_hdr = cast_norm_info.get('subj2_summary') or 'distinct second main character with their own individual identity and attributes as described in the prompt'
            extra_m_hdr = (
                '; ' + '; '.join([f"{m['tag']} ({m['desc']})" for m in cast_norm_info.get('main_subjects', [])[2:]])
                if len(cast_norm_info.get('main_subjects', [])) > 2 else ''
            )
            active_ex_hdr = (
                ' Active background extras: ' + ', '.join([f"{e['tag']} ({e['desc']})" for e in cast_norm_info.get('active_subjects', [])]) + '.'
                if cast_norm_info.get('active_subjects') else ''
            )
            multi_med_lead = style_lead.rstrip('. ') if style_lead else 'RAW 35mm f/5.6 deep-focus photograph'
            clip77_lead = (
                f"{multi_med_lead} with {cast_norm_info['main_cast_count']} distinct main subjects: "
                f"ON THE LEFT is <Main_Subject 1> ({s1_hdr}); "
                f"ON THE RIGHT is <Main_Subject 2> ({s2_hdr}, a separate individual with their own distinct identity and attributes from the prompt — never a cloned twin of <Main_Subject 1>){extra_m_hdr}.{active_ex_hdr}"
            )
            tail_parts = []
            if light_desc and str(resolved_lighting).lower() not in b1.lower():
                tail_parts.append(f'illuminated by {light_desc}')
            tail_clause = ('. '.join(tail_parts) + '.') if tail_parts else ''
            b1 = f'{clip77_lead} {zoom_desc}. {b1} {tail_clause} {style_tail}'.strip()
        else:
            active_ex_hdr = (
                ' Active background extras: ' + ', '.join([f"{e['tag']} ({e['desc']})" for e in cast_norm_info.get('active_subjects', [])]) + '.'
                if cast_norm_info.get('active_subjects') else ''
            )
            tail_parts = []
            if age_prof['age_label']:
                tail_parts.append(f'Strictly depicted as a {age_prof["age_label"]} character ({age_prof["face_id_phrase"].rstrip(",")}){age_diff_phrase}')
            elif subj_tax_norm.get('species_lock_clause') and subj_tax_norm['species_lock_clause'][:24].lower() not in b1.lower():
                spec_c = subj_tax_norm['species_lock_clause']
                tail_parts.append(spec_c[0].upper() + spec_c[1:])
            if light_desc and str(resolved_lighting).lower() not in b1.lower():
                tail_parts.append(f'illuminated by {light_desc}')
            tail_clause = ('. '.join(tail_parts) + '.') if tail_parts else ''
            lead_prefix = f'{style_lead} ' if style_lead else ''
            age_badge_part = f'{age_lead_badge} ' if age_lead_badge else ''
            b1 = f'{lead_prefix}{zoom_desc}. {age_badge_part}{b1}{active_ex_hdr} {tail_clause} {style_tail}'.strip()
        b1 = re.sub(r'\s{2,}', ' ', b1)
    static_summary = re.sub(r'\s+', ' ', static_clean_in).strip()
    if len(static_summary) > 680:
        static_summary = static_summary[:680].rsplit('.', 1)[0].strip() + '.'
    b1_core_desc = re.sub(r'(?i)\bStrictly\s+depicted\s+as\s+a\s+[^.]*\.\s*', '', str(b1_scene_core or '')).strip()
    b1_core_desc = re.sub(r'(?i)\s*Preserving\s+the\s+exact\s+visual\s+medium[^.]*\.?\s*$', '', b1_core_desc).strip()
    if b1_core_desc and len(b1_core_desc) > 20:
        b1_first_sent = re.split(r'(?<=[.!?])\s+', b1_core_desc)[0].strip()
        if b1_first_sent and b1_first_sent[:32].lower() not in static_summary.lower():
            if is_non_human_norm:
                static_summary = f'{static_summary.rstrip(". ")}. Subject morphology anchor from <Picture 1>: {b1_first_sent.rstrip(". ")}, preserving exact species morphology and natural surface details.'
            elif is_dynamic_env_mode:
                static_summary = f'{static_summary.rstrip(". ")}. Character identity anchor from <Picture 1>: {b1_first_sent.rstrip(". ")}, preserving exact facial features across evolving environments.'
            else:
                static_summary = f'{static_summary.rstrip(". ")}. Visual anchor from <Picture 1>: {b1_first_sent.rstrip(". ")}, preserving character identity and scene continuity.'
    if cast_norm_info['cast_b1_injection'] and 'never a twin or clone' not in static_summary.lower():
        static_summary = f"{static_summary.rstrip('. ')}. {cast_norm_info['cast_b1_injection']}"
    if cast_norm_info['has_multi_main_cast']:
        visual_anchor = f"{video_style_lead} {zoom_desc}. {cast_norm_info.get('clip77_split_header', '')} {static_summary}".strip()
    else:
        age_va_part = f'{age_lead_badge} ' if age_lead_badge else ''
        visual_anchor = f'{video_style_lead} {zoom_desc}. {age_va_part}{static_summary}'.strip()
    sec_order = shot_keys + ['[Constraints]', '[Overall Soundscape]', '[Non-Diegetic Music]']
    sec_map = {}
    shot_or_pat = '|'.join((f'Shot\\s*{i}\\b' for i in range(1, num_target_shots + 1)))
    pattern = f'(\\[(?:{shot_or_pat}|Constraints|Overall Soundscape|Non-Diegetic Music)\\])'
    parts = re.split(pattern, p2, flags=re.IGNORECASE)
    cur_header = None
    untagged_lines = []
    for tok in parts:
        tok_s = tok.strip()
        if not tok_s:
            continue
        matched_h = None
        for canonical_h in sec_order:
            if re.fullmatch(re.escape(canonical_h), tok_s, flags=re.IGNORECASE):
                matched_h = canonical_h
                break
        if matched_h:
            cur_header = matched_h
            sec_map.setdefault(cur_header, '')
        elif cur_header:
            sec_map[cur_header] = (sec_map[cur_header] + ' ' + re.sub('\\s+', ' ', tok_s)).strip()
        else:
            untagged_lines.append(re.sub('\\s+', ' ', tok_s))
    if not sec_map.get('[Shot 1]') and untagged_lines:
        joined_u = ' '.join(untagged_lines)
        sents = [s.strip() for s in re.split('(?<=[.!?])\\s+', joined_u) if s.strip()]
        n_s = len(sents)
        if n_s >= num_target_shots:
            for s_idx in range(num_target_shots):
                c_start = int(round(s_idx * n_s / float(num_target_shots)))
                c_end = int(round((s_idx + 1) * n_s / float(num_target_shots)))
                sec_map[f'[Shot {s_idx + 1}]'] = ' '.join(sents[c_start:max(c_start + 1, c_end)])
        elif n_s >= 3:
            c1 = max(1, n_s // 3)
            c2 = max(c1 + 1, 2 * n_s // 3)
            sec_map['[Shot 1]'] = ' '.join(sents[:c1])
            sec_map['[Shot 2]'] = ' '.join(sents[c1:c2])
            sec_map['[Shot 3]'] = ' '.join(sents[c2:])
        elif n_s == 2:
            sec_map['[Shot 1]'] = sents[0]
            sec_map['[Shot 2]'] = sents[1]
            sec_map['[Shot 3]'] = sents[1]
        elif joined_u:
            sec_map['[Shot 1]'] = joined_u
    for shot_k in shot_keys:
        raw_st = str(sec_map.get(shot_k, '') or '').strip()
        if raw_st and raw_st[-1] not in '.!?':
            raw_st = re.sub(r'(?i)\s+(?:with|and|while|as|into|from|of|the|a|an|her|his|their|in|on|at|to|by)\s*$', '', raw_st).rstrip(',;:- ')
            if raw_st and raw_st[-1] not in '.!?':
                raw_st = raw_st + '.'
            sec_map[shot_k] = raw_st
    light_clause = f' under {resolved_lighting} lighting' if str(resolved_lighting).lower() not in ('auto', '') else ''
    if cont_mode_norm == 'hollywood_multi_scene_cuts':
        safe_cam_move = str(resolved_cam_move or 'cinematic anamorphic tracking and multi-angle editorial framing')
        shot_setting_lock = f'Filmed with {safe_cam_move}{light_clause} in {resolved_style} aesthetic.'
    elif allow_camera_movement:
        safe_cam_move = str(resolved_cam_move or 'smooth cinematic camera movement')
        shot_setting_lock = f'Captured with {safe_cam_move}{light_clause} in {resolved_style} aesthetic.'
    else:
        safe_cam_move = re.sub(
            r'(?i)\b(?:slowly\s+drifting\s+in\s+a\s+dolly-in\s+motion|dolly-in\s+motion|dolly-in|push-in|zoom-in|zooming\s+in)\b',
            'holding the exact camera angle and framing distance of <Picture 1> with zero scene cuts',
            str(resolved_cam_move or ''),
        )
        shot_setting_lock = f'Locked to the scene continuity and {resolved_zoom} framing of <Picture 1>{light_clause} in {resolved_style} aesthetic.'
    subj1_tag_norm = f'<Subject 1> ({age_prof["age_label"]})' if age_prof['age_label'] else '<Subject 1>'
    attire_or_morph_norm = 'morphology and natural surface' if is_non_human_norm else 'outfit'
    if is_dynamic_env_mode and narrative_beat_plan:
        for beat_item in narrative_beat_plan:
            s_i_b = int(beat_item['shot_idx'])
            sk_b = f'[Shot {s_i_b}]'
            beat_txt_b = str(beat_item['text'] or '').strip().rstrip('.!?')
            is_cut_b = bool(beat_item.get('is_scene_cut', False))
            existing_b = str(sec_map.get(sk_b, '') or '').strip()
            if not existing_b:
                if s_i_b == 1:
                    sec_map[sk_b] = f'{subj1_tag_norm} begins from <Picture 1> ({resolved_zoom}, {safe_cam_move}{light_clause}): {beat_txt_b}.'
                elif is_cut_b:
                    sec_map[sk_b] = f'[SCENE CUT] Cutting to a new cinematic angle in {resolved_style} style: {beat_txt_b}.'
                else:
                    carry_b = _extract_shot_carryover_state(sec_map.get(f'[Shot {s_i_b - 1}]', ''), s_i_b - 1, resolved_zoom, safe_cam_move, True, continuity_mode=cont_mode_norm, is_scene_cut=False)
                    sec_map[sk_b] = f'{carry_b}{beat_txt_b}.'
            else:
                salient_words = [w.lower() for w in re.findall(r'[A-Za-zÅÄÖåäö]{5,}', beat_txt_b) if w.lower() not in ('subject', 'picture', 'camera', 'frame', 'while', 'through', 'inside', 'outside')]
                if salient_words and not any(sw in existing_b.lower() for sw in salient_words[:4]):
                    existing_b = f'{existing_b.rstrip(". ")} — {beat_txt_b}.'
                if is_cut_b and '[scene cut]' not in existing_b.lower():
                    existing_b = f'[SCENE CUT] {existing_b}'
                sec_map[sk_b] = existing_b
    if not sec_map.get('[Shot 1]'):
        env_s1 = f'starting from the initial composition and {attire_or_morph_norm} of <Picture 1>' if is_dynamic_env_mode else f'captured in the exact setting and {attire_or_morph_norm} of <Picture 1>'
        sec_map['[Shot 1]'] = f'{subj1_tag_norm} {env_s1} ({resolved_zoom}, {safe_cam_move}{light_clause}). {static_summary}'
    if not sec_map.get('[Shot 2]'):
        cam_p2 = f'Continuing the {safe_cam_move}' if allow_camera_movement else f'Maintaining the exact setting, {attire_or_morph_norm}, and camera framing of <Picture 1>'
        cut_note_2 = '' if cont_mode_norm == 'hollywood_multi_scene_cuts' else ' with zero scene cuts'
        sec_map['[Shot 2]'] = f'{cam_p2}{light_clause} in {resolved_style} style{cut_note_2}, {subj1_tag_norm} continues the natural movement and expression seamlessly from Shot 1.'
    if not sec_map.get('[Shot 3]'):
        cam_p3 = f'Completing the {safe_cam_move}' if allow_camera_movement else f'Maintaining the exact setting, {attire_or_morph_norm}, and camera framing of <Picture 1>'
        cut_note_3 = '' if cont_mode_norm == 'hollywood_multi_scene_cuts' else ' with zero scene cuts'
        sec_map['[Shot 3]'] = f'{cam_p3}{light_clause} in {resolved_style} style{cut_note_3}, {subj1_tag_norm} sustains the expressive performance over the {resolved_duration} duration.'
    hair_beat_clause = (
        'with natural breathing and organic micro-motion'
        if is_non_human_norm else (
            'with natural breathing and settled indoor hair'
            if is_indoor_scene else
            'with natural breathing and fluid hair motion'
        )
    )
    wants_dance_beat = bool(re.search(r'(?i)\b(?:dance|dancing|dances|dansar|dans|hip[-\s]?hop|groove|body[-\s]?roll|sway(?:s|ing)?|squats?|squatting|hukar|hukande|på\s+huk)\b', clean_in))
    progression_beats = (
        (
            f'continues the energetic dance groove, rhythmic hip-sway, and expressive full-body choreography {hair_beat_clause}',
            'sustains the dynamic beat-locked dance movement, fluid torso articulation, and playful confident expression in frame',
            'carries the full-body dance rhythm and expressive performance forward with natural momentum and unbroken camera framing',
            'completes the continuous dance choreography arc with poised energy and fluid body kinematics',
        )
        if wants_dance_beat else
        (
            f'transitions fluidly into the next phase of the continuous performance {hair_beat_clause}',
            'deepens the rhythmic physical motion while holding the active body posture, gaze, and anatomical proportions locked in frame',
            'sustains the expressive physical cadence with crisp material foley and coherent camera framing',
            'carries the cinematic motion arc forward with poised intensity and natural body kinematics',
        )
    )
    for idx_s in range(4, num_target_shots + 1):
        sk_cur = f'[Shot {idx_s}]'
        sk_prev = f'[Shot {idx_s - 1}]'
        if not sec_map.get(sk_cur):
            carry_prefix = _extract_shot_carryover_state(sec_map.get(sk_prev, ''), idx_s - 1, resolved_zoom, safe_cam_move, allow_camera_movement, continuity_mode=cont_mode_norm)
            beat_phrase = progression_beats[(idx_s - 4) % len(progression_beats)]
            sec_map[sk_cur] = f'{carry_prefix}{subj1_tag_norm} {beat_phrase}.'
    joined_shots_low = ' '.join((str(sec_map.get(k, '') or '') for k in shot_keys)).lower()
    user_sents = [u_s.strip() for u_s in re.split(r'(?<=[.!?])\s+', str(clean_in_no_suno or clean_in or '').strip()) if len(u_s.strip()) > 8]
    missing_beats = []
    clause_stopwords = {
        'that', 'this', 'with', 'from', 'into', 'onto', 'over', 'under', 'while', 'when', 'where', 'then',
        'they', 'them', 'their', 'hers', 'have', 'having', 'gets', 'getting', 'gives', 'giving', 'around',
        'inside', 'outside', 'through', 'across', 'after', 'before', 'about', 'slightly', 'very', 'just',
        'medan', 'genom', 'under', 'över', 'från', 'hennes', 'hans', 'deras',
    }
    for u_sent in (user_sents[1:] if len(user_sents) >= 2 else user_sents):
        sub_clauses = [sc.strip(' ,.;:') for sc in re.split(r'(?i)\b(?:and\s+she\s+|and\s+he\s+|and\s+they\s+|and\s+then\s+|,\s*and\s+|,\s*och\s+)', u_sent) if len(sc.strip()) > 8]
        for sc in sub_clauses:
            content_toks = [
                w.lower() for w in re.findall(r'[A-Za-zÅÄÖåäö]{3,}', sc)
                if len(w) >= 4 and w.lower() not in clause_stopwords
            ]
            if not content_toks:
                continue
            matched_cnt = sum((1 for tok in content_toks if tok in joined_shots_low))
            if matched_cnt < max(1, (len(content_toks) + 2) // 3):
                norm_sc = sc[0].lower() + sc[1:] if len(sc) > 1 else sc.lower()
                if not re.match(r'(?i)^(?:she|he|they|hon|han|de|<subject\s*1>)\b', norm_sc):
                    norm_sc = f'<Subject 1> {norm_sc}'
                else:
                    norm_sc = re.sub(r'(?i)^(?:she|he|hon|han)\b', '<Subject 1>', norm_sc)
                missing_beats.append(norm_sc.rstrip('.!?'))
    if missing_beats:
        climax_idx = max(2, num_target_shots - 1) if num_target_shots >= 4 else max(2, num_target_shots)
        react_idx = num_target_shots
        if len(missing_beats) >= 2 and climax_idx < react_idx:
            c_key = f'[Shot {climax_idx}]'
            r_key = f'[Shot {react_idx}]'
            c_beat = '; '.join(missing_beats[:-1])
            r_beat = missing_beats[-1]
            sec_map[c_key] = f"{sec_map.get(c_key, '').rstrip('. ')} — {c_beat}."
            carry_r = _extract_shot_carryover_state(sec_map.get(c_key, ''), climax_idx, resolved_zoom, safe_cam_move, allow_camera_movement, continuity_mode=cont_mode_norm)
            sec_map[r_key] = f"{carry_r}{r_beat} while continuing the natural performance."
        else:
            t_key = f'[Shot {climax_idx}]'
            all_b = ', and '.join(missing_beats)
            sec_map[t_key] = f"{sec_map.get(t_key, '').rstrip('. ')}. During this motion, {all_b}."
    for idx_s in range(2, num_target_shots + 1):
        sk_cur = f'[Shot {idx_s}]'
        sk_prev = f'[Shot {idx_s - 1}]'
        cur_txt = sec_map.get(sk_cur, '').strip()
        has_cut_tag = bool(re.search(r'(?i)^\[\s*SCENE[\s_-]*CUT\s*\]', cur_txt))
        if cur_txt and not has_cut_tag and not re.search(r'(?i)\b(?:continuing\s+seamlessly\s+from|cutting\s+cleanly\s+to|from\s+the\s+final\s+frame\s+of\s+shot|continuing\s+the|maintaining\s+the\s+exact)\b', cur_txt[:115]):
            carry_prefix = _extract_shot_carryover_state(sec_map.get(sk_prev, ''), idx_s - 1, resolved_zoom, safe_cam_move, allow_camera_movement, continuity_mode=cont_mode_norm, is_scene_cut=False)
            sec_map[sk_cur] = f'{carry_prefix}{cur_txt}'.strip()
    zoom_low = str(resolved_zoom or 'medium-shot').lower()
    if (not allow_camera_movement) and any((w in zoom_low for w in ('wide', 'full-body', 'establishing', 'medium'))):
        closeup_drift_pat = r'(?i)\b(?:extreme\s+close[-\s]?up|tight\s+close[-\s]?up|macro\s+close[-\s]?up|close[-\s]?up\s+on\s+(?:her|his|their|the)\s+face|close[-\s]?up\s+portrait|slowly\s+drifting\s+in\s+a\s+dolly-in\s+motion|dolly-in\s+motion|dolly-in|push-in|zoom-in|zooms?\s+in(?:\s+closely|\s+tightly)?|zooming\s+in|pushes\s+in\s+tightly|cuts?\s+to\s+a\s+close[-\s]?up)\b'
        for shot_k in shot_keys:
            if sec_map.get(shot_k):
                sec_map[shot_k] = re.sub(closeup_drift_pat, f'steady {resolved_zoom} framing at constant camera distance', sec_map[shot_k])
    stance_low_norm = str(resolved_stance or '').strip().lower()
    norm_3ax_stance = _resolve_3axis_director_directives(resolved_stance, '', '', user_scene_input=clean_in)
    stance_conflict_pat_norm = str(norm_3ax_stance.get('stance_conflict_pat') or '')
    stance_conflict_repl_norm = str(norm_3ax_stance.get('stance_conflict_repl') or '')
    if not stance_conflict_pat_norm and bool(re.search(r'(?i)\b(?:kneel|kneeling|on\s+her\s+knees|crouch|crouching|på\s+huk|hukar|hukande|knäböj(?:er|ande)?|på\s+knä)\b', clean_in)):
        stance_conflict_pat_norm = r'(?i)\b(?:standing\s+tall\s+and\s+upright|stands?\s+tall\s+and\s+upright|standing\s+in\s+a\s+wide(?:\s*,\s*grounded)?\s+combat\s+stance(?:\s+with\s+one\s+leg\s+raised)?|in\s+her\s+grounded\s+raised-leg\s+stance|standing\s+upright|staying\s+upright(?:\s+in\s+frame)?)\b'
        stance_conflict_repl_norm = 'kneeling low on the knees in a grounded crouching posture'
    age_prof_shot = _build_age_authority_profile(resolved_age, is_female=True, has_orc_tusks=has_orc_tusks_norm, allow_facial_metal=wants_face_metal_norm, style_target=resolved_style, tusk_descriptor=morph_norm['feat_desc'], is_non_human=use_auto_age_norm, species_lock_phrase=subj_tax_norm['species_lock_clause'])
    face_id_phrase = age_prof_shot['face_id_phrase']
    if cont_mode_norm == 'hollywood_multi_scene_cuts':
        cam_dist_tail = 'across the multi-scene editorial cinematography.'
    elif allow_camera_movement:
        cam_dist_tail = f'following the {safe_cam_move} with zero hard scene cuts.'
    else:
        cam_dist_tail = 'at the constant camera distance of Frame 0 with zero scene cuts.'
    for (s_idx_norm, shot_k) in enumerate(shot_keys):
        s_txt = sec_map.get(shot_k, '').strip()
        if s_txt:
            if s_txt[-1] not in '.!?':
                s_txt = s_txt.rstrip(',;:- ') + '.'
            if stance_conflict_pat_norm and stance_conflict_repl_norm and (s_idx_norm > 0 or stance_low_norm.startswith('standing_upright')):
                s_txt = re.sub(stance_conflict_pat_norm, stance_conflict_repl_norm, s_txt)
            if shot_setting_lock.lower() not in s_txt.lower():
                s_txt = f'{s_txt} {shot_setting_lock}'.strip()
            if face_id_phrase[:24].lower() not in s_txt.lower():
                face_id_clean = re.sub(r'(?i)^preserving\s+', '', face_id_phrase).strip()
                s_txt = f'{s_txt} <Subject 1> preserves {face_id_clean} and natural dynamic body motion {cam_dist_tail}'
            sec_map[shot_k] = s_txt
    if not sec_map.get('[Constraints]'):
        cam_c_tag = safe_cam_move if allow_camera_movement else f'{resolved_zoom} constant camera distance'
        id_lock_tag = (
            f'The subject species and morphology ({face_id_phrase})'
            if (is_non_human_norm or not age_prof_shot['age_label']) else
            f'The character identity ({age_prof_shot["age_label"]}{age_diff_phrase}), {face_id_phrase}, attire materials'
        )
        if cont_mode_norm == 'hollywood_multi_scene_cuts':
            sec_map['[Constraints]'] = f'{id_lock_tag}, and {resolved_style} visual medium remain 100% locked across all editorial scene cuts throughout the {resolved_duration} ({num_target_shots}-window) film sequence.'
        elif cont_mode_norm == 'continuous_one_shot':
            sec_map['[Constraints]'] = f'{id_lock_tag}, {cam_c_tag}, and {resolved_style} visual medium remain 100% locked across the continuous one-shot {resolved_duration} ({num_target_shots}-window) camera traversal as the environment evolves naturally.'
        else:
            sec_map['[Constraints]'] = f'{id_lock_tag}, {cam_c_tag}, {resolved_lighting} lighting, and {resolved_style} visual medium remain 100% locked across the entire unbroken single-take {resolved_duration} ({num_target_shots}-window) duration.'
    aud_mode = str(resolved_audio_mode or 'sfx_only').lower()
    wants_singing = (aud_mode == 'bgm_with_vocals')
    wants_speech = (aud_mode == 'sfx_and_speech')
    wants_music = (aud_mode in ('instrumental_bgm', 'bgm_with_vocals'))
    music_scrub_pat = r'(?i)\b(?:non-diegetic\s+music|background\s+music|musical\s+score|orchestral\s+score|cinematic\s+score|soundtrack|orchestra|orchestral|symphony|symphonic|synth(?:esizer)?(?:\s+pad)?|piano|violin|cello|guitar|drums?\s+beat|melody|harmonic\s+progression|ambient\s+underscore|bgm)\b'
    vocal_scrub_pat = r'(?i)\b(?:with\s+)?(?:ethereal\s+|female\s+|male\s+|haunting\s+|soft\s+|breathy\s+|wordless\s+|operatic\s+|studio\s+|lead\s+)?(?:singing|sings|sung|vocals?|vocalist|lyrics|song\s+lyrics|choir|ballad|voiceover|chant(?:ing)?|a\s+cappella|humming|soprano|alto|tenor|baritone)\b'
    if wants_singing:
        back_pat = r'(?i)\b(?:turns?\s+around(?:\s+and\s+walks?\s+away)?|turning\s+around|spins?\s+around|spinning\s+around|twirls?(?:\s+around)?|twirling|pirouettes?|360[-\s]?degree|walks?\s+away(?:\s+from\s+(?:the\s+)?camera)?|walking\s+away(?:\s+from\s+(?:the\s+)?camera)?|with\s+(?:her|his|their)\s+back\s+(?:turned|to\s+the\s+camera)|from\s+behind|rear[-\s]?view|back\s+of\s+(?:her|his|their)\s+head)\b'
        user_wants_side_gaze = bool(re.search(r'(?i)\b(?:look(?:s|ing)?\s+away|far\s+wall|side\s+profile|scan(?:s|ning)?\s+the\s+(?:room|wall|horizon))\b', str(clean_in or '')))
        side_scan_pat = r'(?i)\b(?:eyes\s+scanning\s+the\s+(?:[\w\'-]+\s+){0,3}(?:far\s+wall|side\s+wall|distant\s+wall)|gaz(?:es|ing)\s+off[-\s]?screen\s+away\s+from\s+(?:the\s+)?camera|turn(?:s|ing)?\s+(?:her|his|their)\s+head\s+sharply\s+away\s+from\s+(?:the\s+)?camera)\b'
        if not is_dynamic_env_mode:
            b1 = re.sub(back_pat, 'facing the camera directly in full posture with natural vocal expression', b1)
        for shot_k in shot_keys:
            if sec_map.get(shot_k):
                s_sing = sec_map[shot_k] if is_dynamic_env_mode else re.sub(back_pat, 'remaining facing the camera lens in full-posture scale and singing expressively with natural lip-sync', sec_map[shot_k])
                if not user_wants_side_gaze and not is_dynamic_env_mode:
                    s_sing = re.sub(side_scan_pat, 'keeping expressive frontal-to-three-quarter eye contact with the camera lens', s_sing)
                s_sing = re.sub(r'(?i)\b(?:firmly\s+closed\s+mouth(?:\s+and\s+(?:fierce|focused)\s+silent\s+expression)?|fierce\s+silent\s+expression|serene\s+silent\s+expression|focused\s+silent\s+expression|silent\s+focused\s+intensity|in\s+silent\s+(?:reverence|focus))\b', 'expressive parted lips singing the lead vocals with natural lip-sync articulation', s_sing)
                if 'singing' not in s_sing.lower() and 'lip-sync' not in s_sing.lower():
                    sing_dist_clause = 'in dynamic cinematic framing' if is_dynamic_env_mode else 'at constant camera distance'
                    s_sing = f'{s_sing.rstrip(".")}. <Subject 1> sings the lead vocals expressively {sing_dist_clause} with synchronized vocal articulation and rhythmic full-body performance.'
                sec_map[shot_k] = s_sing
    elif wants_speech:
        for shot_k in shot_keys:
            if sec_map.get(shot_k):
                s_sp = re.sub(music_scrub_pat, 'natural environmental acoustics', sec_map[shot_k])
                s_sp = re.sub(vocal_scrub_pat, 'natural spoken voice', s_sp)
                s_sp = re.sub(
                    r'(?i)\b(?:firmly\s+closed\s+mouth(?:\s+and\s+(?:fierce|focused)\s+silent\s+expression)?|closed\s+mouth|tightly\s+closed\s+lips|fierce\s+silent\s+expression|serene\s+silent\s+expression|focused\s+silent\s+expression|silent\s+focused\s+intensity|in\s+silent\s+(?:reverence|focus)|without\s+speaking)\b',
                    'expressive parted lips and active jaw articulation speaking with natural syllable-accurate lip-sync',
                    s_sp,
                )
                if 'lip-sync' not in s_sp.lower() and 'speaks' not in s_sp.lower():
                    s_sp = f'{s_sp.rstrip(".")}. <Subject 1> speaks expressively with clear open-mouth lip-sync, moving the lips and lower jaw naturally in synchronization with the spoken dialogue.'
                sec_map[shot_k] = s_sp
    elif wants_music:
        for shot_k in shot_keys:
            if sec_map.get(shot_k):
                cleaned_m = _scrub_sfx_vocal_triggers(re.sub(vocal_scrub_pat, 'crisp diegetic foley', sec_map[shot_k]), clean_in)
                if has_orc_tusks_norm:
                    cleaned_m = re.sub(
                        r'(?i)\b(?:firmly\s+closed\s+mouth(?:\s+and\s+(?:fierce|focused)\s+silent\s+expression)?|tightly\s+closed\s+lips|closed\s+mouth)\b',
                        'natural expression with two sharp protruding white lower-jaw tusks clearly visible outside the lips',
                        cleaned_m,
                    )
                sec_map[shot_k] = cleaned_m
    else:
        for shot_k in shot_keys:
            if sec_map.get(shot_k):
                cleaned_shot = _scrub_sfx_vocal_triggers(re.sub(vocal_scrub_pat, 'crisp diegetic foley', re.sub(music_scrub_pat, 'crisp diegetic foley', sec_map[shot_k])), clean_in)
                if has_orc_tusks_norm:
                    cleaned_shot = re.sub(
                        r'(?i)\b(?:firmly\s+closed\s+mouth(?:\s+and\s+(?:fierce|focused)\s+silent\s+expression)?|tightly\s+closed\s+lips|closed\s+mouth)\b',
                        'natural expression with two sharp protruding white lower-jaw tusks clearly visible outside the lips',
                        cleaned_shot,
                    )
                sec_map[shot_k] = cleaned_shot
    if wants_singing:
        if not sec_map.get('[Overall Soundscape]'):
            sec_map['[Overall Soundscape]'] = 'Clear, upfront studio lead vocals and expressive singing synchronized frame-for-frame with <Subject 1>\'s mouth, lip, and jaw articulation.'
        if not sec_map.get('[Non-Diegetic Music]'):
            sec_map['[Non-Diegetic Music]'] = f'Continuous atmospheric cinematic background score with synchronized lead vocals locked to the scene mood from 0.0s through {cut_2}.'
    elif wants_speech:
        raw_os = sec_map.get('[Overall Soundscape]', '')
        raw_os = re.sub(music_scrub_pat, 'natural room acoustics', raw_os)
        raw_os = re.sub(vocal_scrub_pat, 'natural spoken dialogue', raw_os)
        raw_os = re.sub(r'(?i)\b(?:no\s+background\s+music|no\s+music|no\s+singing|no\s+vocals|no\s+score)[^.;]*[.;]?', '', raw_os).strip()
        sec_map['[Overall Soundscape]'] = (
            f'{raw_os} Clear, natural spoken voice, authentic vocal expressions, and crisp diegetic physical sound effects (foley and environmental ambience) synchronized frame-for-frame with <Subject 1>\'s open-mouth lip and jaw articulation.'
            if len(raw_os) >= 18 else
            'Clear, natural spoken dialogue and authentic vocal expressions combined with realistic diegetic physical sound effects (subtle studio cloth movement and room acoustics) synchronized frame-for-frame with <Subject 1>\'s open-mouth lip and jaw articulation.'
        )
        sec_map.pop('[Non-Diegetic Music]', None)
    elif wants_music:
        raw_os = _scrub_sfx_vocal_triggers(sec_map.get('[Overall Soundscape]', ''))
        raw_os = re.sub(vocal_scrub_pat, 'crisp diegetic foley', raw_os)
        raw_os = re.sub(music_scrub_pat, 'natural environmental acoustics', raw_os)
        sec_map['[Overall Soundscape]'] = raw_os if len(raw_os) >= 18 else 'Clear, balanced diegetic environmental ambience, natural acoustics, and realistic physical foley synchronized with the visual movement.'
        raw_ndm = sec_map.get('[Non-Diegetic Music]', '')
        raw_ndm = re.sub(r'(?i);?\s*strictly\s+no\s+singing[^.]*\.?', '', raw_ndm).strip()
        raw_ndm = re.sub(vocal_scrub_pat, 'instrumental texture', raw_ndm)
        raw_ndm = re.sub(r'(?i)\b(?:no\s+singing|no\s+vocals|no\s+lyrics|no\s+human\s+voice|without\s+vocals)[^.;]*[.;]?', '', raw_ndm).strip()
        sec_map['[Non-Diegetic Music]'] = (
            raw_ndm if len(raw_ndm) >= 18 else
            f'Atmospheric instrumental cinematic underscore with deep rhythmic percussion, strings, and ambient textures from 0.0s through {cut_2}.'
        )
    else:
        raw_os = _scrub_sfx_vocal_triggers(sec_map.get('[Overall Soundscape]', ''))
        raw_os = re.sub(music_scrub_pat, 'crisp physical foley', raw_os)
        raw_os = re.sub(vocal_scrub_pat, 'natural environmental ambience', raw_os)
        raw_os = re.sub(r'(?i)\bcrunching\s+snow(?:\s+underfoot)?,?\s*', 'quiet room ambience, ' if is_indoor_scene else 'natural outdoor ambience, ', raw_os)
        raw_os = re.sub(r'(?i)\b(?:strictly\s+)?(?:no\s+background\s+music|no\s+music|no\s+singing|no\s+vocals|no\s+score|spoken\s+dialogue|speech|zero\s+human\s+speech|zero\s+dialogue|zero\s+singing|human\s+voice|voiceover)[^.;]*[.;]?', '', raw_os).strip()
        base_sfx_os = (
            raw_os if len(raw_os) >= 18 else (
                'Crisp high-definition indoor studio foley recording: quiet room acoustics, subtle garment and surface movement friction synchronized frame-for-frame with every upper-body gesture.'
                if is_indoor_scene else
                'Crisp high-definition environmental foley recording: natural ambient air, garment and gear movement friction, and physical motion acoustics synchronized frame-for-frame with every movement.'
            )
        )
        sec_map['[Overall Soundscape]'] = f'{base_sfx_os.rstrip(".")}; pure environmental foley and physical material acoustics only.'
        sec_map.pop('[Non-Diegetic Music]', None)
    if not is_nsfw or rating_tier == 'sfw':
        sfw_tag = (
            'Strictly Safe-For-Work (SFW) family-friendly scene.'
            if is_non_human_norm else
            'Strictly Safe-For-Work (SFW) scene; the character is fully clothed in modest, non-revealing full-coverage attire.'
        )
        if 'safe-for-work' not in b1.lower() and 'fully clothed' not in b1.lower():
            b1 = f'{b1} {sfw_tag}'.strip()
        for shot_k in shot_keys + ['[Constraints]']:
            if sec_map.get(shot_k):
                sec_map[shot_k] = _scrub_nsfw_terms_for_sfw(sec_map[shot_k])
        sec_map['[Constraints]'] = f"{sec_map.get('[Constraints]', '').strip()} {sfw_tag}".strip()
    b1 = _sanitize_krea2_prose_and_runaway_clauses(b1, is_block1_image=True)
    b2_lines = ['BLOCK 2', f'[Master Scene & Visual Theme]\n{visual_anchor}']
    active_sec_order = sec_order if wants_music else [h for h in sec_order if h != '[Non-Diegetic Music]']
    for h in active_sec_order:
        if h in sec_map and str(sec_map[h]).strip():
            sec_txt = _sanitize_krea2_prose_and_runaway_clauses(sec_map[h].strip(), is_block1_image=False)
            b2_lines.append(f'{h}\n{sec_txt}')
    return (b1, '\n\n'.join(b2_lines))


def execute_qwenvl_story_compiler(user_scene_input: str, vlm_model_name: str, master_duration: str, style_target: str, subject_1_age: str, age_difference: str, camera_movement: str, lm_studio_endpoint: str, vram_cleanup_after: bool, camera_zoom: str='medium-shot', lighting_ambient: str='auto', custom_subject_1_age: str='', custom_age_difference: str='', custom_camera_movement: str='', custom_style_or_lighting: str='', custom_duration_seconds: float=0.0, compiler_seed: int=42, reference_image=None, content_rating_mode: str='Uncensored Artistic / Action (Ingen Censur — Följer Prompten)', ref_image_2_person=None, ref_image_3_clothing=None, ref_image_4_background=None, slot2_is_dual_subject: bool=False, audio_soundtrack_mode: str='sfx_only_no_music (Endast Ljudeffekter / Ingen Musik)', subject_stance_posture: str='auto_from_prompt (Auto från Prompt / Bild)', body_choreography_preset: str='auto_from_prompt_or_audio (Auto från Prompt / Ljud)', camera_trajectory_arc: str='follow_02_camera_setting (Följ [02] Kamerainställning / Auto)', background_extras_crowd: str='auto_from_prompt (Auto från Prompt — Slagsmål / Älskog / Barhäng / Stadsvy / Solo)', custom_negative_prompt: str='', scene_continuity_mode: str=SCENE_CONTINUITY_MODES[0]):
    rng = random.Random(int(compiler_seed))
    eff_audio_mode = _resolve_audio_soundtrack_mode(audio_soundtrack_mode, user_scene_input)
    resolved_stance = _resolve_dropdown_custom_or_random(subject_stance_posture, SUBJECT_STANCE_POSTURE_PRESETS, '', rng, SUBJECT_STANCE_POSTURE_PRESETS[0])
    resolved_choreo = _resolve_dropdown_custom_or_random(body_choreography_preset, BODY_CHOREOGRAPHY_PRESETS, '', rng, BODY_CHOREOGRAPHY_PRESETS[0])
    resolved_arc = _resolve_dropdown_custom_or_random(camera_trajectory_arc, CAMERA_TRAJECTORY_ARC_PRESETS, '', rng, CAMERA_TRAJECTORY_ARC_PRESETS[0])
    resolved_extras = _resolve_dropdown_custom_or_random(background_extras_crowd, BACKGROUND_EXTRAS_CROWD_PRESETS, '', rng, BACKGROUND_EXTRAS_CROWD_PRESETS[0])
    rating_tier = _resolve_content_rating_tier(content_rating_mode, user_scene_input, resolved_stance, resolved_choreo, resolved_extras)
    is_nsfw = (rating_tier != 'sfw')
    resolved_continuity_mode = resolve_scene_continuity_mode(
        scene_continuity_mode=scene_continuity_mode,
        user_scene_input=user_scene_input,
        subject_stance_posture=resolved_stance,
        body_choreography_preset=resolved_choreo,
        camera_trajectory_arc=resolved_arc,
    )
    is_dynamic_continuity = resolved_continuity_mode in ('continuous_one_shot', 'hollywood_multi_scene_cuts')
    dir_3ax = _resolve_3axis_director_directives(resolved_stance, resolved_choreo, resolved_arc, user_scene_input=user_scene_input, background_extras_crowd=resolved_extras, slot2_is_dual_subject=slot2_is_dual_subject, age_difference=age_difference)
    cast_info = dir_3ax['cast_info']
    resolved_age = _resolve_dropdown_custom_or_random(subject_1_age, SUBJECT_AGE_PRESETS, custom_subject_1_age, rng, '25-year-old')
    resolved_age_diff = _resolve_dropdown_custom_or_random(age_difference, AGE_DIFFERENCE_PRESETS, custom_age_difference, rng, 'same age')
    allow_cam_move = _is_intentional_camera_movement_requested(camera_movement, custom_camera_movement, user_scene_input) or bool(dir_3ax['force_camera_move']) or is_dynamic_continuity
    if dir_3ax['arc_phrase']:
        resolved_cam_move = dir_3ax['arc_phrase']
    elif str(camera_movement or '').strip().lower() == 'random':
        moving_pool = [p for p in CAMERA_MOVEMENT_PRESETS if 'locked-off' not in p.lower()]
        resolved_cam_move = rng.choice(moving_pool) if moving_pool else CAMERA_MOVEMENT_PRESETS[0]
    elif is_dynamic_continuity and str(camera_movement or '').strip().lower().startswith('locked-off') and not str(custom_camera_movement or '').strip():
        resolved_cam_move = 'low-angle medium-wide tracking shot with a handheld camera aesthetic' if resolved_continuity_mode == 'continuous_one_shot' else 'smooth crane-up reveal transitioning into an anamorphic push-in'
    elif allow_cam_move:
        resolved_cam_move = _resolve_dropdown_custom_or_random(camera_movement, CAMERA_MOVEMENT_PRESETS, custom_camera_movement, rng, CAMERA_MOVEMENT_PRESETS[0])
    else:
        resolved_cam_move = CAMERA_MOVEMENT_PRESETS[0]
    style_custom_arg = custom_style_or_lighting if str(style_target).strip().lower() == 'custom' or (str(lighting_ambient).strip().lower() != 'custom' and str(style_target).strip().lower() == 'realism') else ''
    light_custom_arg = custom_style_or_lighting if str(lighting_ambient).strip().lower() == 'custom' else ''
    resolved_style = _resolve_dropdown_custom_or_random(style_target, STYLE_TARGET_PRESETS, style_custom_arg, rng, 'realism')
    resolved_zoom = _resolve_dropdown_custom_or_random(camera_zoom, CAMERA_ZOOM_PRESETS, '', rng, 'medium-shot')
    resolved_lighting = _resolve_dropdown_custom_or_random(lighting_ambient, LIGHTING_AMBIENT_PRESETS, light_custom_arg, rng, 'auto')
    md_low = str(master_duration or '20-second').strip().lower()
    if (md_low == 'custom' and float(custom_duration_seconds) > 0.0) or (md_low == '20-second' and float(custom_duration_seconds) > 0.0 and abs(float(custom_duration_seconds) - 20.0) > 0.01):
        resolved_duration = f'{int(round(float(custom_duration_seconds)))}-second'
    else:
        resolved_duration = _resolve_dropdown_custom_or_random(master_duration, MASTER_DURATION_PRESETS, '', rng, '20-second')
    m_num = re.search('(\\d+(?:\\.\\d+)?)', str(resolved_duration))
    dur_seconds_val = float(m_num.group(1)) if m_num else 20.0
    search_dirs = _get_default_vault_search_dirs()
    is_licensed = _verify_cinematrix_license_active(search_dirs)
    dur_map = {'30-second': ('10.0s', '20.0s'), '20-second': ('6.5s', '13.5s'), '15-second': ('5.0s', '10.0s'), '10-second': ('3.3s', '6.6s'), '5-second': ('1.6s', '3.3s')}
    if resolved_duration in dur_map:
        (cut_1, cut_2) = dur_map[resolved_duration]
    else:
        cut_1 = f'{round(dur_seconds_val / 3.0, 2)}s'
        cut_2 = f'{round(dur_seconds_val * 2.0 / 3.0, 2)}s'
    (pil_ref, b64_ref_url) = _tensor_to_pil_and_b64(reference_image)
    (pil_r2, b64_r2_url) = _tensor_to_pil_and_b64(ref_image_2_person)
    (pil_r3, b64_r3_url) = _tensor_to_pil_and_b64(ref_image_3_clothing)
    (pil_r4, b64_r4_url) = _tensor_to_pil_and_b64(ref_image_4_background)
    ref_orc_info = _detect_reference_orc_species_and_skin(pil_ref, user_scene_input)
    eff_user_scene_for_prof = str(user_scene_input or '').strip()
    if ref_orc_info.get('has_visible_tusks') and not _extract_prompt_morphology_profile(eff_user_scene_for_prof)['has_tusks']:
        eff_user_scene_for_prof = f"{ref_orc_info['trait_clause']}. {eff_user_scene_for_prof}".strip('. ')
    style_prof = _get_style_compiler_profile(resolved_style, eff_user_scene_for_prof)
    aesthetic_rule = style_prof['rule']
    style_low = str(resolved_style or 'realism').strip().lower()
    resolved_cam_move = _sanitize_camera_movement_for_settings(resolved_cam_move, resolved_zoom, style_low, allow_camera_movement=allow_cam_move, user_scene_input=eff_user_scene_for_prof, background_extras_crowd=resolved_extras)
    raw_u_scene = str(user_scene_input or '').strip()
    has_slot5_scene_directive = 'Reference Video Slot #5' in raw_u_scene
    is_i2i_ref_framing = bool((pil_ref is not None) and (not has_slot5_scene_directive))
    (system_instruction, redacted_http_instruction, prompt_mode_tag) = _resolve_qwenvl_system_prompt(master_duration=resolved_duration, cut_1=cut_1, cut_2=cut_2, style_target=resolved_style, camera_zoom=resolved_zoom, lighting_ambient=resolved_lighting, subject_1_age=resolved_age, age_difference=resolved_age_diff, camera_movement=resolved_cam_move, content_rating_mode=content_rating_mode, audio_soundtrack_mode=eff_audio_mode, user_scene_input=eff_user_scene_for_prof, allow_camera_movement=allow_cam_move, has_reference_image=is_i2i_ref_framing, resolved_continuity_mode=resolved_continuity_mode)
    if dir_3ax['vlm_directive']:
        system_instruction = f"{system_instruction}\n\n[UNIVERSAL 3-AXIS DIRECTOR & CAST/EXTRAS OVERRIDES]:\n{dir_3ax['vlm_directive']}"
        redacted_http_instruction = f"{redacted_http_instruction}\n\n[UNIVERSAL 3-AXIS DIRECTOR & CAST/EXTRAS OVERRIDES]:\n{dir_3ax['vlm_directive']}"
    extra_pils = []
    extra_b64s = []
    ref_role_lines = []
    img_counter = 0
    subj_tax_pre = _detect_subject_taxonomy_and_species_lock(eff_user_scene_for_prof, '', resolved_age, custom_subject_1_age, has_reference_image=(pil_ref is not None))
    if pil_ref is not None:
        img_counter += 1
        orc_ref_lock = (
            f" MANDATORY MORPHOLOGY & SKIN PIGMENT LOCK FROM IMAGE #{img_counter}: Preserve the subject's {ref_orc_info['trait_clause']} from Image #{img_counter} unless explicitly overridden by the user prompt — NEVER misidentify a tusked subject as an elf and NEVER replace non-human skin pigment with generic tan human skin."
            if ref_orc_info.get('has_visible_tusks') else ''
        )
        species_ref_lock = (
            f" STRICT SPECIES & MORPHOLOGY LOCK FROM IMAGE #{img_counter}: Preserve 100% of Image #{img_counter}'s exact biological species, anatomy, and natural coat/fur/feathers/scales/skin unless the user prompt explicitly requests a transformation — NEVER mutate one animal species into another (e.g., a mouse MUST remain a mouse and NEVER become a bird or grow unrequested wings, feathers, beak, human face, or clothing)."
            if not subj_tax_pre['allows_metamorphosis'] else ''
        )
        if has_slot5_scene_directive or bool(cast_info['has_multi_main_cast']):
            ref_role_lines.append(f"- Image #{img_counter} (PRIMARY PROTAGONIST <Main_Subject 1> IDENTITY, SPECIES, SKIN/COAT & MORPHOLOGY REFERENCE ONLY — DO NOT CLONE ONTO <Main_Subject 2>): Extract ONLY <Main_Subject 1>'s exact species, facial/head likeness, skin/coat color, and anatomical traits from Image #{img_counter}, while using the user prompt (and Reference Video Slot #5 if present) for the scene setting, attire, posture, any additional main characters (<Main_Subject 2>..N), and active background extras (<Subject 1>..M) in '{resolved_style}' style ({aesthetic_rule}).{orc_ref_lock}{species_ref_lock}")
        elif style_low.startswith('original'):
            ref_role_lines.append(f"- Image #{img_counter} (PRIMARY PROTAGONIST <Main_Subject 1> IDENTITY, SPECIES, POSE, STYLE & COMPOSITION REFERENCE): Mandatory visual foundation. Strictly preserve 100% of <Main_Subject 1>'s exact species, facial/head morphology, skin/coat texture, anatomical traits, attire if present, initial starting pose, and original artistic rendering style from Image #{img_counter}.{orc_ref_lock}{species_ref_lock}")
        elif style_low in ('dark-fantasy-real', 'dark-fantasy-cgi', 'dark-fantasy'):
            ref_role_lines.append(f"- Image #{img_counter} (PROTAGONIST <Main_Subject 1> IDENTITY, SPECIES, POSE & DARK-FANTASY ATMOSPHERIC BLUEPRINT): In BLOCK 1 ([IMAGE]), render in '{resolved_style}' ({aesthetic_rule}) while preserving 100% of <Main_Subject 1>'s exact species, facial/head likeness, hair/fur/surface color, eyewear/accessories if present, intrinsic skin/coat tone, body posture, attire/appearance, and camera framing distance from Image #{img_counter}. Apply grimdark obsidian-and-ember atmospheric lighting and expand any flat wall behind the subject into a deep 3D Z-axis gothic/abyssal background with shallow f/1.8 optical bokeh, WITHOUT inventing unrequested armor, pauldrons, chains, or horns that are absent from both Image #{img_counter} and the user prompt.{orc_ref_lock}{species_ref_lock}")
        else:
            ref_role_lines.append(f"- Image #{img_counter} (MANDATORY 1:1 SUBJECT SPECIES, APPEARANCE, POSE, FRAMING & ENVIRONMENT BLUEPRINT — CONVERT RENDERING MEDIUM ONLY UNLESS OVERRIDDEN BY USER PROMPT): In BLOCK 1 ([IMAGE]), translate ONLY the rendering medium into '{resolved_style}' ({aesthetic_rule}) while preserving 100% of every attribute in Image #{img_counter} that is NOT explicitly changed by the user prompt: exact biological species and head/body morphology, exact hair/fur/feather length, silhouette, and color, exact eyewear/headwear/jewelry/garment geometry and motifs if present, exact intrinsic skin/coat albedo under neutral white-balance, exact body posture, camera framing distance, limb placement, expression, and background setting.{orc_ref_lock}{species_ref_lock}")
    if pil_r2 is not None:
        img_counter += 1
        extra_pils.append(pil_r2)
        extra_b64s.append(b64_r2_url)
        if slot2_is_dual_subject or cast_info['has_multi_main_cast']:
            ref_role_lines.append(f'- Image #{img_counter} (SECOND PROTAGONIST <Main_Subject 2> REFERENCE): Include this second main character (<Main_Subject 2>) interacting naturally alongside <Main_Subject 1> on the same foreground plane.')
        else:
            ref_role_lines.append(f'- Image #{img_counter} (FACIAL IDENTITY REFERENCE FOR THE SINGLE MAIN PROTAGONIST <Main_Subject 1>): Render strictly ONE unified protagonist (<Main_Subject 1>) in the scene whose facial features, eyes, and identity match Image #{img_counter} (do NOT add a second person).')
    if pil_r3 is not None:
        img_counter += 1
        extra_pils.append(pil_r3)
        extra_b64s.append(b64_r3_url)
        ref_role_lines.append(f'- Image #{img_counter} (ISOLATED CLOTHING & ARMOR REFERENCE): Dress <Main_Subject 1> seamlessly in the exact armor/clothing design, fabric, and color palette shown in Image #{img_counter}.')
    if pil_r4 is not None:
        img_counter += 1
        extra_pils.append(pil_r4)
        extra_b64s.append(b64_r4_url)
        if has_slot5_scene_directive:
            ref_role_lines.append(f'- Image #{img_counter} (REFERENCE VIDEO SCENE, CAMERA FRAMING & POSTURE TEMPLATE AT START_OFFSET_SEC): Use Image #{img_counter} as the spatial scene layout, camera angle, stage/desk framing, and subject posture template to be re-enacted and transformed according to the user prompt.')
        else:
            ref_role_lines.append(f'- Image #{img_counter} (BACKGROUND ENVIRONMENT REFERENCE): Place the cast inside the exact background setting, architecture, sky, and lighting atmosphere shown in Image #{img_counter}.')
    pre_clean_input = _apply_age_override_to_text(str(user_scene_input or '').strip(), resolved_age, is_non_human=bool(subj_tax_pre['use_auto_age_bypass']))
    if not is_nsfw:
        pre_clean_input = _scrub_nsfw_terms_for_sfw(pre_clean_input)
    vlm_user_input = pre_clean_input
    if ref_role_lines:
        role_block = '[MANDATORY MULTI-IMAGE REFERENCE BINDING]:\n' + '\n'.join(ref_role_lines)
        vlm_user_input = f'{role_block}\n\n{vlm_user_input}'.strip()
    compiled_raw = ''
    all_b64 = ([b64_ref_url] if b64_ref_url else []) + [u for u in extra_b64s if u]
    import hashlib
    b64_sigs = tuple((hashlib.md5(u.encode('utf-8')).hexdigest()[:16] for u in all_b64))
    vlm_cache_key = (
        'v35_preset_authority_and_species_fidelity',
        str(vlm_model_name or '').strip(),
        str(pre_clean_input or '').strip(),
        str(resolved_style or '').strip(),
        str(resolved_zoom or '').strip(),
        str(resolved_lighting or '').strip(),
        str(resolved_age or '').strip(),
        str(resolved_age_diff or '').strip(),
        str(resolved_duration or '').strip(),
        str(resolved_cam_move or '').strip(),
        bool(allow_cam_move),
        str(eff_audio_mode or '').strip(),
        str(rating_tier or '').strip(),
        str(resolved_stance or '').strip(),
        str(resolved_choreo or '').strip(),
        str(resolved_arc or '').strip(),
        str(resolved_extras or '').strip(),
        str(resolved_continuity_mode or '').strip(),
        int(compiler_seed) & 2147483647,
        bool(slot2_is_dual_subject),
        b64_sigs,
    )
    raw_vlm_cache = globals().setdefault('_QWENVL_RAW_VLM_CACHE', {})
    if vlm_cache_key in raw_vlm_cache and raw_vlm_cache[vlm_cache_key]:
        compiled_raw = raw_vlm_cache[vlm_cache_key]
        print(f'[EZ-QWEN3-VL] ⚡ Reusing cached VLM narrative ({len(compiled_raw)} chars) — 0.00s VRAM load!')
    dyn_tok_budget = _compute_dynamic_vlm_token_budget(dur_seconds_val)
    local_vlm_path = _resolve_local_vlm_path(vlm_model_name)
    attempted_local = False
    if not compiled_raw and vlm_model_name and vlm_model_name != 'LM_STUDIO_ACTIVE_MODEL' and (local_vlm_path is not None):
        attempted_local = True
        if local_vlm_path.is_file() and local_vlm_path.suffix.lower() == '.gguf':
            compiled_raw = _run_local_gguf_vlm(gguf_path=local_vlm_path, system_instruction=system_instruction, user_scene_input=vlm_user_input, b64_urls=all_b64, compiler_seed=compiler_seed, max_tokens=dyn_tok_budget['gguf_max_tokens'], n_ctx=dyn_tok_budget['gguf_n_ctx'])
            if not compiled_raw and (local_vlm_path.parent / 'config.json').exists():
                compiled_raw = _run_local_transformers_vlm(model_dir=local_vlm_path, system_instruction=system_instruction, user_scene_input=vlm_user_input, pil_img=pil_ref, compiler_seed=compiler_seed, extra_pil_imgs=extra_pils, max_new_tokens=dyn_tok_budget['transformers_max_new_tokens'])
        elif local_vlm_path.is_dir() or local_vlm_path.is_file():
            compiled_raw = _run_local_transformers_vlm(model_dir=local_vlm_path, system_instruction=system_instruction, user_scene_input=vlm_user_input, pil_img=pil_ref, compiler_seed=compiler_seed, extra_pil_imgs=extra_pils, max_new_tokens=dyn_tok_budget['transformers_max_new_tokens'])
    if not compiled_raw and str(lm_studio_endpoint).strip().startswith('http'):
        ep_url = str(lm_studio_endpoint).strip()
        resolved_lm_model = ''
        try:
            models_url = re.sub(r'/chat/completions/?$', '/models', ep_url)
            with urllib.request.urlopen(urllib.request.Request(models_url, method='GET'), timeout=4) as m_resp:
                if m_resp.status == 200:
                    m_data = json.loads(m_resp.read().decode('utf-8')).get('data', [])
                    if isinstance(m_data, list) and m_data:
                        stem_hint = Path(str(vlm_model_name).replace('\\', '/')).stem.lower()
                        matched_m = next((m.get('id') for m in m_data if isinstance(m, dict) and stem_hint and stem_hint[:14] in str(m.get('id', '')).lower()), None)
                        resolved_lm_model = str(matched_m or m_data[0].get('id', '') or '')
        except Exception:
            resolved_lm_model = ''
        for send_images in ([True, False] if all_b64 else [False]):
            try:
                user_msg_content = ([{'type': 'image_url', 'image_url': {'url': u}} for u in all_b64] + [{'type': 'text', 'text': str(vlm_user_input)}]) if send_images else str(vlm_user_input)
                payload = {'messages': [{'role': 'system', 'content': redacted_http_instruction}, {'role': 'user', 'content': user_msg_content}], 'temperature': 0.2, 'max_tokens': dyn_tok_budget['lm_studio_max_tokens'], 'seed': int(compiler_seed) & 2147483647}
                if resolved_lm_model:
                    payload['model'] = resolved_lm_model
                elif vlm_model_name and vlm_model_name != 'LM_STUDIO_ACTIVE_MODEL':
                    payload['model'] = Path(str(vlm_model_name).replace('\\', '/')).stem
                req = urllib.request.Request(ep_url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
                with urllib.request.urlopen(req, timeout=dyn_tok_budget['http_timeout_sec']) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode('utf-8'))
                        compiled_raw = data.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
                        compiled_raw = re.sub(r'(?is)<think>.*?</think>', '', compiled_raw).strip()
                        if compiled_raw:
                            break
            except Exception as lm_err:
                if send_images:
                    continue
                print(f'[EZ-QWEN3-VL] LM Studio endpoint notice: {lm_err}')
                compiled_raw = ''
    if not compiled_raw and not attempted_local and (local_vlm_path is not None) and local_vlm_path.is_dir():
        compiled_raw = _run_local_transformers_vlm(model_dir=local_vlm_path, system_instruction=system_instruction, user_scene_input=vlm_user_input, pil_img=pil_ref, compiler_seed=compiler_seed, extra_pil_imgs=extra_pils, max_new_tokens=dyn_tok_budget['transformers_max_new_tokens'])
    system_instruction = ''
    redacted_http_instruction = ''
    if compiled_raw:
        if len(raw_vlm_cache) >= 32:
            raw_vlm_cache.pop(next(iter(raw_vlm_cache)), None)
        raw_vlm_cache[vlm_cache_key] = compiled_raw
    subj_tax_mid = _detect_subject_taxonomy_and_species_lock(eff_user_scene_for_prof, compiled_raw, resolved_age, custom_subject_1_age, has_reference_image=(pil_ref is not None))
    age_diff_low = str(resolved_age_diff).lower()
    age_diff_phrase = '' if 'none' in age_diff_low or 'single' in age_diff_low or 'same' in age_diff_low or bool(subj_tax_mid['is_non_human']) else f', {resolved_age_diff}'
    clean_in = _apply_age_override_to_text(eff_user_scene_for_prof, resolved_age, is_non_human=bool(subj_tax_mid['use_auto_age_bypass']))
    if not is_nsfw:
        clean_in = _scrub_nsfw_terms_for_sfw(clean_in)
    if subj_tax_mid['is_animal_creature'] and not subj_tax_mid['is_avian'] and not subj_tax_mid['allows_metamorphosis'] and subj_tax_mid['matched_species'] and compiled_raw:
        sp_keep = subj_tax_mid['matched_species']
        compiled_raw = _SUBJECT_AVIAN_REGEX.sub(sp_keep, compiled_raw)
    user_wants_elf = bool(re.search(r'(?i)\b(?:elf|elven)\b', str(user_scene_input or '')) and not re.search(r'(?i)\b(?:elven[-\s]?like\s+ears|elf\s+ears)\b', str(user_scene_input or '')))
    if ref_orc_info.get('has_visible_tusks') and not user_wants_elf and compiled_raw:
        compiled_raw = re.sub(
            r'(?i)\b(?:a\s+)?(?:\d{1,2}[-\s]?year[-\s]?old\s+)?(?:young[-\s]?adult\s+|mature\s+|youthful\s+)?(?:female\s+)?elf\b',
            ref_orc_info['trait_clause'],
            compiled_raw,
        )
    (block1_clean, block2_clean) = _normalize_qwenvl_two_block_output(compiled_raw=compiled_raw, clean_in=clean_in, resolved_age=resolved_age, age_diff_phrase=age_diff_phrase, resolved_zoom=resolved_zoom, resolved_lighting=resolved_lighting, resolved_cam_move=resolved_cam_move, aesthetic_rule=aesthetic_rule, resolved_duration=resolved_duration, cut_1=cut_1, cut_2=cut_2, resolved_style=resolved_style, is_nsfw=is_nsfw, resolved_audio_mode=eff_audio_mode, rating_tier=rating_tier, allow_camera_movement=allow_cam_move, resolved_stance=resolved_stance, background_extras_crowd=resolved_extras, slot2_is_dual_subject=slot2_is_dual_subject, has_reference_image=is_i2i_ref_framing, resolved_continuity_mode=resolved_continuity_mode)
    if ref_orc_info.get('has_visible_tusks') and not user_wants_elf:
        block1_clean = re.sub(r'(?i)\b(?:female\s+)?elf\b', ref_orc_info['trait_clause'], block1_clean)
        block2_clean = re.sub(r'(?i)\b(?:female\s+)?elf\b', ref_orc_info['trait_clause'], block2_clean)
        pig_lbl = ref_orc_info.get('pigment_label', '')
        if pig_lbl and pig_lbl not in block1_clean.lower() and 'deep red skin' not in block1_clean.lower():
            block1_clean = f"Featuring a {ref_orc_info['trait_clause']}, {block1_clean}"
    wants_facial_metal = _has_explicit_facial_metal_request(clean_in)
    if not wants_facial_metal:
        block1_clean = _scrub_unrequested_facial_metal(block1_clean, clean_in)
        block2_clean = _scrub_unrequested_facial_metal(block2_clean, clean_in)
    if pil_ref is None and dir_3ax['stance_phrase'] and dir_3ax['stance_phrase'][:28].lower() not in block1_clean.lower():
        block1_clean = f"{block1_clean.rstrip('. ')}. Staged {dir_3ax['stance_phrase']}."
    if dir_3ax.get('stance_transition_phrase') and dir_3ax['stance_phrase']:
        trans_p = dir_3ax['stance_transition_phrase']
        hold_p = dir_3ax['stance_phrase']
        if trans_p[:28].lower() not in block2_clean.lower():
            block2_clean = re.sub(
                r'(\[Shot\s*1\]\s*\n)',
                rf"\1<Subject 1> {trans_p}. ",
                block2_clean,
                count=1,
            )
            block2_clean = re.sub(
                r'(\[Shot\s*(?:[2-9]|\d{2,})\]\s*\n)',
                rf"\1Having transitioned into the target posture, <Subject 1> remains {hold_p}. ",
                block2_clean,
                count=1,
            )
    if dir_3ax['choreo_phrase'] and dir_3ax['choreo_phrase'][:28].lower() not in block2_clean.lower():
        block2_clean = re.sub(r'(\[Shot\s*\d+\]\s*\n)', rf"\1<Subject 1> is {dir_3ax['choreo_phrase']}. ", block2_clean)
    if dir_3ax['arc_phrase'] and dir_3ax['arc_phrase'][:28].lower() not in block2_clean.lower():
        block2_clean = re.sub(r'(\[Master Scene & Visual Theme\]\s*\n)', rf"\1Camera Trajectory Arc: {dir_3ax['arc_phrase']}. ", block2_clean, count=1)
    subj_tax_final = _detect_subject_taxonomy_and_species_lock(user_scene_input, f'{compiled_raw} {block1_clean}', resolved_age, custom_subject_1_age, has_reference_image=(pil_ref is not None))
    is_non_human_final = bool(subj_tax_final['is_non_human'])
    morph_final = _extract_prompt_morphology_profile(clean_in)
    has_orc_tusks_final = bool(morph_final['has_tusks']) or bool(ref_orc_info.get('has_visible_tusks'))
    age_prof_final = _build_age_authority_profile(resolved_age, is_female=True, has_orc_tusks=has_orc_tusks_final, allow_facial_metal=wants_facial_metal, style_target=resolved_style, tusk_descriptor=morph_final['feat_desc'], is_non_human=bool(subj_tax_final['use_auto_age_bypass']), species_lock_phrase=subj_tax_final['species_lock_clause'])
    age_years_val = int(age_prof_final['age_years'])
    vault_bundle = _load_licensed_allan_ballan_vault() if is_licensed else None
    light_bundle = _load_freemium_light_bundle()
    neg_templates = (vault_bundle.get('negative_templates') if isinstance(vault_bundle, dict) else None) or light_bundle.get('neg_map') or light_bundle.get('negative_defaults', {})
    glasses_tpl = str(neg_templates.get('glasses') or 'eyeglasses, sunglasses, spectacles, glasses').strip().rstrip(',')
    combined_eyewear_src = f'{clean_in} {block1_clean} {block2_clean}'.lower()
    glasses_neg = '' if any(g in combined_eyewear_src for g in ('glasses', 'eyeglasses', 'sunglasses', 'spectacles')) else f'{glasses_tpl}, '
    face_metal_tpl = str(neg_templates.get('face_metal') or neg_templates.get('unrequested_facial_metal') or 'facial metal, metal on face, chin plate, metal chin guard, jaw armor, metallic chin ornament, chin spike, facial piercings, lip ring, chin stud, nose ring, face armor').strip().rstrip(',')
    face_metal_neg = '' if wants_facial_metal else f'{face_metal_tpl}, '
    has_dual_subj_final = bool(cast_info['has_multi_main_cast'])
    has_bg_extras_final = bool(cast_info['has_background_extras'])
    has_male_cast_final = has_dual_subj_final or bool(re.search(r'(?i)\b(?:male|man|men|boy|senator|gentleman|king|prince|lord|father|brother|husband|guy|he|him|his)\b', clean_in))
    masc_guard = '' if (has_male_cast_final or is_non_human_final) else 'masculine face, '
    if is_non_human_final:
        fem_guard_neg = ''
    elif age_years_val <= 35 and not has_dual_subj_final:
        fem_guard_neg = f'{masc_guard}old wrinkled face, deep forehead wrinkles, nasolabial folds, ' if re.search(r'(?i)\b(?:she|her|female|woman|queen|goddess|heroine)\b', clean_in) else ''
    else:
        fem_guard_neg = f'{masc_guard}' if re.search(r'(?i)\b(?:she|her|female|woman|queen|goddess|heroine)\b', clean_in) else ''
    is_indoor_final = (not is_dynamic_continuity) and (not is_non_human_final) and bool(
        re.search(r'(?i)\b(?:studio|news\s+desk|broadcast|indoor|indoors|interior|room|office|tavern|bar|cockpit|interview(?:ing)?|anchor|teleprompter|desk)\b', clean_in)
    ) and not bool(re.search(r'(?i)\b(?:wind|windy|breeze|storm|gale|blizzard|gusts?)\b', clean_in))
    indoor_wind_tpl = str(neg_templates.get('indoor_wind') or 'wind-blown hair, hair blowing in wind, indoor wind, wind gusts, flying hair strands').strip().rstrip(',')
    indoor_wind_neg = f'{indoor_wind_tpl}, ' if is_indoor_final else ''
    s1_low_final = str(cast_info.get('subj1_summary') or '').lower()
    s2_low_final = str(cast_info.get('subj2_summary') or '').lower()
    s2_has_explicit_other_species = bool(re.search(r'\b(?:goblin|human|elf|elven|dwarf|troll|demon|cyborg|android|vampire)\b', s2_low_final)) and (s1_low_final != s2_low_final)
    s2_trait_guard_neg = 'copying Main_Subject 1 species onto Main_Subject 2, ' if (has_dual_subj_final and s2_has_explicit_other_species) else ''
    clip77_anti_twin_lead = ''
    if has_dual_subj_final and not has_bg_extras_final:
        dual_subj_neg = f'identical twins, cloned character, duplicate of Main_Subject 1, exact same face on both characters, {s2_trait_guard_neg}tiny blurry person far in background, distant out-of-focus second character, extra disembodied head behind shoulder, '
        clip77_anti_twin_lead = f'(identical twins, cloned character, duplicate of Main_Subject 1, {s2_trait_guard_neg}exact same face on both characters, double face, ghosted face, superimposed face overlay:1.95)'
    elif has_dual_subj_final:
        dual_subj_neg = f'identical twins, cloned character, duplicate of Main_Subject 1, exact same face on both characters, {s2_trait_guard_neg}tiny blurry main partner far in background, fused bodies, merged limbs, extra disembodied head behind shoulder, '
        clip77_anti_twin_lead = f'(identical twins, cloned character, duplicate of Main_Subject 1, {s2_trait_guard_neg}exact same face on both characters, double face, ghosted face, superimposed face overlay:1.95)'
    elif not has_bg_extras_final and not is_dynamic_continuity:
        dual_subj_neg = 'unrequested background people, extra heads behind shoulder, crowd in background, '
    else:
        dual_subj_neg = 'fused bodies, merged limbs, extra disembodied head, '
    double_face_tpl = str(neg_templates.get('double_face') or neg_templates.get('double_face_guard') or 'double face, face inside a face, two faces on one head, inner face seam, double forehead, concentric face boundary, face mask seam, ghosted face overlay').strip().rstrip(',')
    double_face_neg = f'{double_face_tpl}, '
    drift_tail_tpl = str(neg_templates.get('drift_tail') or 'ghosting, double limbs, extra arms, afterimage, motion smear, black void background, solid black background, glowing white eyes').strip().rstrip(',')
    drift_neg = f'{glasses_neg}{face_metal_neg}{fem_guard_neg}{double_face_neg}{indoor_wind_neg}{dual_subj_neg}{drift_tail_tpl}, '
    if eff_audio_mode == 'bgm_with_vocals':
        audio_neg = f'closed mouth, static mouth, sealed lips, frozen smile, mute face, turned back, spinning around, walking away from camera, rear view, back of head, {drift_neg}distorted audio, audio clipping, loud static, '
    elif eff_audio_mode == 'sfx_and_speech':
        audio_neg = f'closed mouth, static mouth, sealed lips, frozen smile, mute face, background music, non-diegetic music, musical score, soundtrack, instrumental music, orchestra, synth, drums, guitar, piano, melody, singing, song lyrics, choir, musical ballad, chanting, opera, {drift_neg}distorted audio, audio clipping, loud static, '
    elif eff_audio_mode == 'instrumental_bgm':
        audio_neg = f'singing, lead vocals, song lyrics, choir, musical ballad, opera, spoken voiceover narration, open mouth singing, {drift_neg}distorted audio, audio clipping, loud static, '
    else:
        audio_neg = f'background music, non-diegetic music, musical score, soundtrack, instrumental music, orchestra, synth, drums, guitar, piano, melody, singing, lead vocals, song lyrics, choir, musical ballad, opera, spoken voiceover narration, {drift_neg}distorted audio, audio clipping, loud static, '
    if dir_3ax['is_outro_follow'] or is_dynamic_continuity:
        audio_neg = re.sub(r'(?i)\b(?:turned\s+back,\s*|spinning\s+around,\s*|walking\s+away\s+from\s+camera,\s*|rear\s+view,\s*|back\s+of\s+head,\s*)', '', audio_neg)
    wan_quality_neg = str(neg_templates.get('cn_tail') or neg_templates.get('core_wan_quality') or '色调艳丽, 过曝, 静态, 细节模糊不清, 字幕, 风格, 作品, 画作, 画面, 静止, 整体发灰, 最差质量, 低质量, JPEG压缩残留, 丑陋的, 残缺的, 多余的手指, 画得不好的手部, 画得不好的脸部, 畸形的, 毁容的, 形态畸形的肢体, 手指融合, 静止不动的画面, 杂乱的背景, 三条腿, 背景人很多, 倒着走').strip().rstrip(',')
    if rating_tier in ('nsfw_explicit', 'uncensored_action'):
        base_core_neg = f'({audio_neg}text, logo, watermark, signature, username, censored, mosaic censorship, bar censor:1.6), {wan_quality_neg},'
    else:
        base_core_neg = f'({audio_neg}nsfw, nude, naked, nipples, cleavage, bikini, lingerie, bare breasts, bare midriff, explicit, cum, white cum, milky liquid, text, logo, watermark:1.6), {wan_quality_neg},'
    if dir_3ax['is_multi_subject_crowd'] or has_dual_subj_final or has_bg_extras_final or is_dynamic_continuity:
        base_core_neg = re.sub(r'杂乱的背景,\s*|三条腿,\s*|背景人很多,\s*', '', base_core_neg)
    if dir_3ax.get('choreo_neg_tokens'):
        base_core_neg = re.sub(r'静态,\s*|静止,\s*|静止不动的画面,\s*', '', base_core_neg)
    style_neg_lead = style_prof.get('neg_prefix', '')
    if age_years_val >= 40 and style_neg_lead:
        style_neg_lead = re.sub(r'(?i),?\s*old\s+wrinkled\s+face', '', style_neg_lead)
    age_neg_lead = '' if (has_dual_subj_final or bool(subj_tax_final['use_auto_age_bypass'])) else age_prof_final['neg_tokens']
    preset_3ax_neg = str(dir_3ax.get('combined_3axis_neg') or '').strip()
    cam_lock_neg = '' if (allow_cam_move or 'camera zoom-in' in preset_3ax_neg.lower()) else '(camera zoom-in, dolly-in, push-in, camera pan, whip-pan, zoom-out, hard jump cut:1.65)'
    morph_neg_lead = str(morph_final.get('neg_guard') or '').strip()
    species_neg_lead = str(subj_tax_final.get('species_neg_guard') or '').strip()
    sat_strength_val = _resolve_color_saturation_strength(resolved_lighting, custom_style_or_lighting=custom_style_or_lighting, user_scene_input=user_scene_input)
    sat_guard = str(neg_templates.get('saturation_low') or neg_templates.get('desaturated_chroma_guard') or '(oversaturated colors, hyper-saturated neon skin, radioactive red skin, blown-out neon chroma, glowing magenta-blue oversaturation, artificial color clipping:1.55)').strip().rstrip(',')
    sat_neg_lead = sat_guard if sat_strength_val <= 0.85 else ''
    lead_combo = ', '.join([x for x in (clip77_anti_twin_lead, species_neg_lead, morph_neg_lead, preset_3ax_neg, cam_lock_neg, sat_neg_lead, age_neg_lead, style_neg_lead) if x])
    auto_adaptive_neg = f'{lead_combo}, {base_core_neg}' if lead_combo else base_core_neg
    raw_custom_neg_str = str(custom_negative_prompt or '').strip()
    custom_neg_str = _reconcile_custom_negative_style_collision(raw_custom_neg_str, resolved_style, style_neg_lead)
    adaptive_neg = custom_neg_str if custom_neg_str else auto_adaptive_neg
    if vram_cleanup_after:
        if hasattr(comfy.model_management, 'unload_all_models'):
            comfy.model_management.unload_all_models()
        if hasattr(comfy.model_management, 'soft_empty_cache'):
            comfy.model_management.soft_empty_cache()
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            try:
                torch.cuda.reset_peak_memory_stats()
            except Exception:
                pass
    resolved_meta = {'master_duration': resolved_duration, 'duration_seconds': dur_seconds_val, 'style_target': resolved_style, 'camera_zoom': resolved_zoom, 'lighting_ambient': resolved_lighting, 'color_saturation_strength': float(sat_strength_val), 'subject_1_age': age_prof_final['age_label'] or ('species-auto' if is_non_human_final else 'auto'), 'subject_1_age_num': age_years_val, 'is_non_human_subject': is_non_human_final, 'subject_species_category': str(subj_tax_final['category']), 'matched_subject_species': str(subj_tax_final['matched_species']), 'age_difference': resolved_age_diff, 'camera_movement': resolved_cam_move, 'allow_camera_movement': bool(allow_cam_move), 'scene_continuity_mode': str(scene_continuity_mode), 'resolved_scene_continuity_mode': str(resolved_continuity_mode), 'content_rating_mode': str(content_rating_mode), 'content_rating_tier': rating_tier, 'audio_soundtrack_mode': eff_audio_mode, 'subject_stance_posture': resolved_stance, 'body_choreography_preset': resolved_choreo, 'camera_trajectory_arc': resolved_arc, 'background_extras_crowd': resolved_extras, 'main_cast_count': int(cast_info['main_cast_count']), 'main_subjects': list(cast_info.get('main_subjects', [])), 'active_subject_count': int(cast_info.get('active_subject_count', 0)), 'active_subjects': list(cast_info.get('active_subjects', [])), 'scene_archetype': str(cast_info['scene_archetype']), 'has_background_extras': bool(cast_info['has_background_extras']), 'cast_continuity_lock': str(cast_info['cast_continuity_lock']), 'is_multi_subject_crowd': bool(dir_3ax['is_multi_subject_crowd']), 'prompt_engine_mode': prompt_mode_tag, 'is_licensed': bool(is_licensed), 'auto_negative_prompt': auto_adaptive_neg, 'auto_generated_negative_prompt': auto_adaptive_neg, 'custom_negative_override_active': bool(custom_neg_str)}
    return (block1_clean, block2_clean, adaptive_neg, resolved_meta)

