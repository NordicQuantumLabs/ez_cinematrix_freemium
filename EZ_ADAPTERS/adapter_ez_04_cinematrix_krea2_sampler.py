# -*- coding: utf-8 -*-
from ..EZ_ENGINES.engine_ez_04_cinematrix_krea2_sampler import _sigma_schedule, _percent_schedule_index, _nearest_schedule_index, build_three_stage_sigma_triplet, _zero_out_conditioning, _maybe_upscale_latent, _create_empty_krea2_latent, _apply_tier_optimized_native_controlnet, _evict_stage1_controlnet_from_vram, sample_stage_with_sigmas, _gaussian_blur_2d, _capsule_sdf_2d, _detect_skeletal_keypoints_rcnn, _compute_neural_anatomy_zones, compute_downscaled_latent_anatomy_zones, _render_anatomy_preview_bhwc, _stabilize_latent_anatomy_outliers, _anchor_original_style_latent, _anchor_orc_tusk_mouth_latent, _apply_2d_cel_and_ink_stylization_bchw, _detect_crimson_orc_reference_bhwc, _precondition_i2i_source_for_style_bhwc, _restore_i2i_orc_tusks_bhwc, _harmonize_2d_i2i_skin_albedo_bhwc, _blend_i2i_reference_beauty_bhwc, _apply_live_action_photographic_physics_bhwc, _apply_frequency_separation_polish, _compose_multi_reference_canvas, _compute_krea2_generation_signature, _try_load_cached_krea2_keyframe, _store_cached_krea2_keyframe, _resolve_pipeline_video_model_metadata, _sanitize_bus_for_video_handoff, _resolve_date_subfolder_path, UPSCALE_METHODS, DATE_FOLDER_FORMAT_PRESETS, _KEYPOINT_RCNN_CACHE, _KREA2_KEYFRAME_VAULT

import math
import gc
import json
import torch
import comfy.model_management
import comfy.sample
import comfy.samplers
import comfy.utils
import latent_preview
import nodes

def _clamp_sdxl_4ch_resolution_pair(width: int, height: int, max_area: int = 1380000, target_area: int = 1100000) -> tuple:
    w_in = int(width or 0)
    h_in = int(height or 0)
    if w_in <= 0 or h_in <= 0 or (w_in * h_in) <= int(max_area):
        return (w_in, h_in, False)
    scale = math.sqrt(float(target_area) / float(max(1, w_in * h_in)))
    w_clamped = max(512, int(round((float(w_in) * scale) / 16.0) * 16))
    h_clamped = max(512, int(round((float(h_in) * scale) / 16.0) * 16))
    return (w_clamped, h_clamped, True)


def _apply_beginner_multi_arch_sampler_autopilot(
    img_arch: str,
    style_low: str,
    stage1_steps: int,
    stage1_cfg: float,
    stage1_sampler_name: str,
    stage1_scheduler: str,
    stage2_steps: int,
    stage2_cfg: float,
    handoff_percent: float,
    final_width: int,
    final_height: int,
    is_baked_img_turbo: bool = False,
    is_sdxl_dmd2: bool = False,
    is_flux_schnell: bool = False,
    has_flux_turbo_lora: bool = False,
) -> dict:
    arch = str(img_arch or 'krea2').strip().lower()
    s1_steps = int(stage1_steps)
    s1_cfg = float(stage1_cfg)
    s1_sampler = str(stage1_sampler_name or 'euler')
    s1_sched = str(stage1_scheduler or 'beta')
    s2_steps = int(stage2_steps)
    s2_cfg = float(stage2_cfg)
    ho_pct = float(handoff_percent)
    fw = int(final_width or 0)
    fh = int(final_height or 0)
    log_msg = ''
    is_sdxl_arch = arch in ('illustrious', 'pony', 'sdxl')
    if is_sdxl_arch:
        (fw_new, fh_new, did_clamp_res) = _clamp_sdxl_4ch_resolution_pair(fw, fh)
        if did_clamp_res:
            fw, fh = fw_new, fh_new
        if is_sdxl_dmd2:
            if s1_steps > 14 or s1_cfg > 2.2 or s1_sched in ('beta', 'simple') or s2_steps > 0:
                s1_steps = min(12, max(6, s1_steps if s1_steps <= 14 else 8))
                s1_cfg = 1.2 if s1_cfg > 2.2 else s1_cfg
                s2_steps = 0
                ho_pct = 100.0
                if s1_sched in ('beta', 'simple'):
                    s1_sampler = 'euler_ancestral'
                    s1_sched = 'normal'
                log_msg = f'[EZ-04-MULTIARCH-DMD2] ⚡ {arch.upper()} + DMD2/Lightning 4ch -> Single-Stage ({s1_steps} steg, CFG {s1_cfg:.2f}, {s1_sampler}/{s1_sched}, {fw}x{fh}).'
        elif s1_steps >= 40 or s1_cfg <= 3.8 or s1_sched == 'beta' or s2_steps > 0:
            s1_steps = 28 if (s1_steps >= 40 or s1_steps < 16) else s1_steps
            target_cfg = 4.5 if arch == 'illustrious' else (5.5 if arch == 'pony' else 5.0)
            if s1_cfg <= 3.8 or s1_cfg > 7.5:
                s1_cfg = target_cfg
            s2_steps = 0
            ho_pct = 100.0
            if s1_sched == 'beta' or (s1_sampler == 'euler' and s1_sched in ('beta', 'simple')):
                s1_sampler = 'dpmpp_2m_sde' if arch == 'sdxl' else 'euler_ancestral'
                s1_sched = 'karras'
            log_msg = f'[EZ-04-MULTIARCH-AUTO] 🎨 {arch.upper()} 4ch -> Optimal Single-Stage ({s1_steps} steg, CFG {s1_cfg:.1f}, {s1_sampler}/{s1_sched}, {fw}x{fh}).'
        elif did_clamp_res:
            log_msg = f'[EZ-04-MULTIARCH-RES] 📐 {arch.upper()} 4ch -> Skalar ner upplösning till optimal {fw}x{fh} (~1.1 MP) mot kontrastbränning.'
    elif arch == 'flux':
        if is_flux_schnell:
            if s1_steps > 6 or s1_cfg > 1.2 or s2_steps > 0 or s1_sched == 'beta':
                s1_steps = 4
                s1_cfg = 1.0
                s1_sampler = 'euler'
                s1_sched = 'simple'
                s2_steps = 0
                ho_pct = 100.0
                log_msg = f'[EZ-04-FLUX-SCHNELL] ⚡ FLUX.1 Schnell -> Single-Stage ({s1_steps} steg, CFG {s1_cfg:.1f}, {s1_sampler}/{s1_sched}).'
        elif has_flux_turbo_lora:
            if s1_steps > 12 or s1_cfg > 1.35 or s2_steps > 0 or s1_sched == 'beta':
                s1_steps = 8
                s1_cfg = 1.0
                s1_sampler = 'euler'
                s1_sched = 'simple'
                s2_steps = 0
                ho_pct = 100.0
                log_msg = f'[EZ-04-FLUX-TURBO] ⚡ FLUX.1 + Turbo-LoRA -> Single-Stage ({s1_steps} steg, CFG {s1_cfg:.1f}, {s1_sampler}/{s1_sched}).'
        elif s1_steps >= 40 or s1_cfg >= 2.0 or s2_steps > 0 or s1_sched == 'beta':
            s1_steps = 24 if (s1_steps >= 40 or s1_steps < 14) else s1_steps
            s1_cfg = 1.0 if s1_cfg >= 2.0 else s1_cfg
            s1_sampler = 'euler' if s1_sched == 'beta' else s1_sampler
            s1_sched = 'simple' if s1_sched == 'beta' else s1_sched
            s2_steps = 0
            ho_pct = 100.0
            log_msg = f'[EZ-04-FLUX-AUTO] ⚡ FLUX.1 Dev -> Optimal Single-Stage ({s1_steps} steg, CFG {s1_cfg:.1f}, {s1_sampler}/{s1_sched}).'
    elif arch == 'qwen_image':
        if not is_baked_img_turbo and (s1_steps >= 40 or s2_steps > 0 or s1_sched == 'beta'):
            s1_steps = 24 if s1_steps >= 40 else s1_steps
            s1_cfg = 2.5 if s1_cfg >= 2.8 else s1_cfg
            s1_sched = 'simple' if s1_sched == 'beta' else s1_sched
            s2_steps = 0
            ho_pct = 100.0
            log_msg = f'[EZ-04-QWEN-AUTO] 🎨 QWEN-IMAGE -> Optimal Single-Stage ({s1_steps} steg, CFG {s1_cfg:.1f}, {s1_sampler}/{s1_sched}).'
    elif is_baked_img_turbo and style_low not in ('cartoonish', 'anime'):
        if s1_cfg > 1.35 or s1_steps > 10:
            log_msg = f'[EZ-04-TURBO-GUARD] ⚡ Inbakad Krea 2 Turbo aktiv -> Justerar automatiskt CFG ({s1_cfg:.2f} -> 1.00) och stegbudget ({s1_steps} -> {min(8, max(4, s1_steps))}) för ren Blackwell/Turbo-exponering.'
        s1_cfg = min(1.20, s1_cfg) if s1_cfg <= 1.35 else 1.0
        s2_cfg = min(1.20, s2_cfg) if s2_cfg <= 1.35 else 1.0
        s1_steps = min(8, max(4, s1_steps))
        if s2_steps > 0:
            s2_steps = min(6, max(4, s2_steps))
    return {
        'stage1_steps': s1_steps,
        'stage1_cfg': s1_cfg,
        'stage1_sampler_name': s1_sampler,
        'stage1_scheduler': s1_sched,
        'stage2_steps': s2_steps,
        'stage2_cfg': s2_cfg,
        'handoff_percent': ho_pct,
        'final_width': fw,
        'final_height': fh,
        'log_msg': log_msg,
    }


class EzCinematrixThreeStageAdapter:
    """Adapter executing Krea 2 3-stage sampling (Stage 1 -> Bislerp Upscale -> Stage 2 Turbo -> Stage 3 Polish) and VAE keyframe decoding."""

    @staticmethod
    def run_three_stage(stage1_model, stage2_model, image_vae, source_image, seed, handoff_percent, stage3_handoff_percent, stage1_steps, stage1_cfg, stage1_sampler_name, stage1_scheduler, stage2_steps, stage2_cfg, stage2_sampler_name, stage2_scheduler, final_width, final_height, upscale_method, positive=None, negative=None, image_clip=None, krea2_image_prompt='', adaptive_negative_prompt='', save_keyframe_to_disk=True, save_metadata=True, date_folder_format='YYYY-MM-DD', seed_mode='auto_from_bus_or_local', i2i_denoise=0.75, enable_frequency_polish=True, skin_blur_radius=3.5, skin_texture_strength=1.08, skin_polish_opacity=0.65, anatomy_dock=None, cinematrix_bus=None, **_extra_kwargs):
        from datetime import datetime
        from pathlib import Path
        import numpy as np
        from PIL import Image, ImageDraw, ImageFont, PngImagePlugin
        import folder_paths
        bus = dict(cinematrix_bus) if isinstance(cinematrix_bus, dict) else {}
        dock_cfg = dict(anatomy_dock) if isinstance(anatomy_dock, dict) else dict(bus.get('anatomy_dock', {})) if isinstance(bus.get('anatomy_dock'), dict) else {}
        if dock_cfg:
            bus['anatomy_dock'] = dock_cfg
        tier_prof = dict(bus.get('hardware_tier_profile', {})) if isinstance(bus.get('hardware_tier_profile'), dict) else {}
        tile_sz = int(tier_prof.get('tile_size', 512) or 512)
        aggressive_purge = bool(tier_prof.get('aggressive_vram_purge', True))
        master_seed = int(bus.get('canvas_seed', bus.get('master_seed', seed)))
        qwen_seed = int(bus.get('qwenvl_seed', master_seed))
        sync_all = bool(bus.get('sync_all_seeds', False)) or str(bus.get('seed_sync_mode', '')).lower().startswith('sync_all')
        mode_low = str(seed_mode or 'auto_from_bus_or_local').lower()
        if 'sync_with_master' in mode_low:
            eff_seed = master_seed
        elif 'sync_with_qwenvl' in mode_low:
            eff_seed = qwen_seed
        elif 'use_local' in mode_low:
            eff_seed = int(seed)
        else:
            eff_seed = master_seed if sync_all or int(seed) == 0 else int(seed)
        rating_tier = str(bus.get('content_rating_tier', '') or '').strip().lower()
        if not rating_tier:
            raw_rm = str(bus.get('content_rating_mode', 'Uncensored')).lower()
            rating_tier = 'sfw' if raw_rm.startswith('sfw') else ('nsfw_explicit' if 'explicit' in raw_rm else 'uncensored_action')
        is_nsfw = (rating_tier != 'sfw')
        import re
        raw_style = str(bus.get('style_target', '') or '').strip().lower()
        try:
            from .adapter_ez_02_cinematrix_qwenvl_timeline import _ACTIVE_QWENVL_SCENE_STATE
            if isinstance(_ACTIVE_QWENVL_SCENE_STATE, dict):
                q_st = str(_ACTIVE_QWENVL_SCENE_STATE.get('style_target', '') or '').strip().lower()
                if q_st:
                    raw_style = q_st
        except Exception:
            pass
        try:
            from server import PromptServer
            ps = getattr(PromptServer, 'instance', None)
            pq = getattr(ps, 'prompt_queue', None) if ps is not None else None
            running = getattr(pq, 'currently_running', None) if pq is not None else None
            if isinstance(running, dict) and len(running) > 0:
                active_item = next(iter(running.values()))
                p_graph = active_item[2] if isinstance(active_item, (list, tuple)) and len(active_item) > 2 and isinstance(active_item[2], dict) else None
                if isinstance(p_graph, dict):
                    for n_def in p_graph.values():
                        if isinstance(n_def, dict) and ('QwenVL' in str(n_def.get('class_type', '')) or 'EZ_02' in str(n_def.get('class_type', ''))):
                            n_in = n_def.get('inputs') if isinstance(n_def.get('inputs'), dict) else {}
                            cand_st = str(n_in.get('style_target', '') or '').strip().lower()
                            if cand_st and not isinstance(n_in.get('style_target'), list) and cand_st not in ('random', 'custom'):
                                raw_style = cand_st
                            break
        except Exception:
            pass
        if not raw_style:
            p_low = str(krea2_image_prompt or '').lower()
            for st_cand in ('dark-fantasy-real', 'dark-fantasy-cgi', 'dark-fantasy', 'cinematic-film-35mm', 'unreal-engine-5', 'semi-real', 'cartoonish', 'anime', 'realism'):
                if st_cand in p_low or st_cand.replace('-', ' ') in p_low:
                    raw_style = st_cand
                    break
        style_low = 'original' if (not raw_style or raw_style.startswith('original')) else raw_style
        bus['style_target'] = style_low
        style_slug = re.sub(r'[^a-zA-Z0-9_-]+', '_', style_low).strip('_-') or 'original'
        default_core_neg = '(text, logo, watermark, signature, censored, mosaic censorship:1.5), 色调艳丽, 过曝, 静态, 细节模糊不清, 字幕, 风格, 作品, 画作, 画面, 静止, 整体发灰, 最差质量, 低质量, JPEG压缩残留, 丑陋的, 残缺的, 多余的手指, 画得不好的手部, 画得不好的脸部, 畸形的, 毁容的, 形态畸形的肢体, 手指融合, 静止不动的画面, 杂乱的背景, 三条腿, 背景人很多, 倒着走,'
        if rating_tier == 'sfw':
            default_core_neg = f'(nsfw, nude, naked, nipples, cum, white cum, milky liquid:1.5), {default_core_neg}'
        eff_pos_str = str(krea2_image_prompt or bus.get('krea2_image_prompt', '') or '').strip()
        trig_words = str(bus.get('image_trigger_words', '') or '').strip()
        if eff_pos_str and trig_words and (trig_words.lower() not in eff_pos_str.lower()):
            eff_pos_str = f'{trig_words}, {eff_pos_str}'.strip(', ')
        from ..EZ_ENGINES.engine_ez_02_cinematrix_qwenvl_timeline import (
            _parse_subject_age_years,
            _build_age_authority_profile,
            _has_explicit_facial_metal_request,
            _scrub_unrequested_facial_metal,
            _extract_prompt_morphology_profile,
        )
        wants_face_metal = _has_explicit_facial_metal_request(eff_pos_str)
        omni_probe_04 = bus.get('omni_reference_bundle') if isinstance(bus.get('omni_reference_bundle'), dict) else {}
        ref_probe_04 = source_image if (isinstance(source_image, torch.Tensor) and source_image.numel() > 0 and float(source_image.detach().abs().max().item()) > 1e-04) else (omni_probe_04.get('raw_slot1_fullres') if isinstance(omni_probe_04.get('raw_slot1_fullres'), torch.Tensor) else (omni_probe_04.get('master_composite_image') if isinstance(omni_probe_04.get('master_composite_image'), torch.Tensor) else bus.get('ingest_image')))
        raw_user_04 = str(bus.get('raw_user_scene_input', '') or '').strip()
        morph_04 = _extract_prompt_morphology_profile(raw_user_04 if raw_user_04 else eff_pos_str)
        has_orc_tusks_04 = bool(morph_04['has_tusks'])
        if not has_orc_tusks_04 and eff_pos_str:
            eff_pos_str = re.sub(r'(?i)^Featuring\s+a\s+orc\s+warrior\s+with\s+deep\s+crimson-red\s+skin\s+and\s+two\s+sharp\s+protruding\s+white\s+lower-jaw\s+tusks[^,]*,\s*', '', eff_pos_str).strip()
        is_crimson_orc_ref_04 = bool(morph_04['has_orc'] or morph_04['has_tusks']) and _detect_crimson_orc_reference_bhwc(ref_probe_04)
        has_other_species_04 = bool(morph_04['has_boar'] or morph_04['has_dragon'] or morph_04['has_ogre_troll'] or morph_04['has_human'])
        ref_subj_04 = 'warrior' if has_other_species_04 else 'orc warrior'
        if is_crimson_orc_ref_04 and eff_pos_str and morph_04['feat_desc']:
            eff_pos_str = re.sub(
                r'(?i)\b(?:female\s+)?elf\b',
                f"{ref_subj_04} with deep crimson-red skin and {morph_04['feat_desc']}",
                eff_pos_str,
            )
        age_diff_04 = str(bus.get('age_difference', '') or '').strip().lower()
        is_single_subj_04 = ('single subject' in age_diff_04) or age_diff_04.startswith(('none', 'single'))
        has_multi_cast_04 = (not is_single_subj_04) and (int(bus.get('main_cast_count', 1) or 1) >= 2)
        if not wants_face_metal and eff_pos_str:
            eff_pos_str = _scrub_unrequested_facial_metal(eff_pos_str, eff_pos_str)
        raw_age_04 = str(bus.get('subject_1_age', '') or '').strip()
        if not raw_age_04:
            try:
                from .adapter_ez_02_cinematrix_qwenvl_timeline import _ACTIVE_QWENVL_SCENE_STATE
                if isinstance(_ACTIVE_QWENVL_SCENE_STATE, dict):
                    raw_age_04 = str(_ACTIVE_QWENVL_SCENE_STATE.get('subject_1_age', '') or '').strip()
            except Exception:
                pass
        if not raw_age_04 and eff_pos_str:
            m_age_p = re.search(r'(?i)\b(\d{1,2}[-\s]?year[-\s]?old)\b', eff_pos_str)
            if m_age_p:
                raw_age_04 = m_age_p.group(1)
        age_years = int(bus.get('subject_1_age_num') or _parse_subject_age_years(raw_age_04 or '25-year-old'))
        age_prof_04 = _build_age_authority_profile(raw_age_04 or f'{age_years}-year-old', has_orc_tusks=has_orc_tusks_04, allow_facial_metal=wants_face_metal, style_target=style_low, tusk_descriptor=morph_04['feat_desc'])
        bus['subject_1_age'] = age_prof_04['age_label']
        bus['subject_1_age_num'] = age_years
        img_arch_04 = str(bus.get('active_image_arch') or getattr(stage1_model, '_ez_image_arch', 'krea2') or 'krea2').strip().lower()
        is_sdxl_arch_04 = img_arch_04 in ('illustrious', 'pony', 'sdxl')
        if eff_pos_str:
            pos_head_low = eff_pos_str[:180].lower()
            if style_low == 'anime' and '2d japanese' not in pos_head_low and 'anime screencap' not in pos_head_low and not is_sdxl_arch_04:
                eff_pos_str = f'Authentic flat 2D Japanese TV anime cel-shaded keyframe screenshot (anime screencap, flat color, cel shading), crisp black ink lineart outlines, discrete 2-tone flat cel shadows without 3D gradients, flat 2D anime eyes, {eff_pos_str}'
            elif style_low == 'cartoonish' and '2d western cartoon' not in pos_head_low and 'cel-shaded cartoon' not in pos_head_low and not is_sdxl_arch_04:
                eff_pos_str = f'Authentic flat 2D Western cartoon cel-shaded animation frame, bold black ink outlines, discrete flat 2D cel color fills without 3D gradients, {eff_pos_str}'
            elif style_low == 'realism' and morph_04['has_fantasy_anatomy'] and 'live-action practical-effects' not in eff_pos_str[:220].lower() and not is_sdxl_arch_04:
                eff_pos_str = f'RAW unretouched 35mm ARRI Alexa 65 live-action cinema photograph with real biological skin epidermis, natural subsurface scattering, and real physical bone structure (strictly live-action camera photography, never a 2D painting or illustration), {eff_pos_str}'
            feat_04 = morph_04['feat_desc']
            if is_crimson_orc_ref_04 and feat_04 and 'crimson-red skin' not in eff_pos_str[:320].lower() and 'deep red skin' not in eff_pos_str[:320].lower():
                eff_pos_str = f'Featuring a {ref_subj_04} with deep crimson-red skin and {feat_04}, {eff_pos_str}'
            elif has_orc_tusks_04 and feat_04 and 'tusk' not in eff_pos_str[:320].lower() and 'boar' not in eff_pos_str[:320].lower():
                eff_pos_str = f'Featuring {feat_04}, {eff_pos_str}'
        eff_neg_str = str(adaptive_negative_prompt or bus.get('adaptive_negative_prompt', '') or default_core_neg).strip()
        if not has_orc_tusks_04 and eff_neg_str:
            eff_neg_str = re.sub(r'(?i)\([^()]*missing\s+tusks[^()]*\),\s*', '', eff_neg_str).strip()
        eff_neg_str = re.sub(r'(?i)\bmale\s+orc\s+face\b', 'masculine male jaw', eff_neg_str)
        if age_prof_04['neg_tokens'][:24].lower() not in eff_neg_str.lower():
            eff_neg_str = f"{age_prof_04['neg_tokens']}, {eff_neg_str}"
        if has_orc_tusks_04 and 'missing tusks' not in eff_neg_str[:260].lower():
            orc_skin_neg = 'tan human skin, brown human skin, peach human skin, elf without tusks, ' if is_crimson_orc_ref_04 else ''
            base_tusk_neg = morph_04['neg_guard'].strip('()').split(':')[0] if morph_04['neg_guard'] else 'missing tusks, no tusks, mouth without tusks, hidden tusks, closed lips hiding tusks, human teeth without tusks'
            eff_neg_str = f'({orc_skin_neg}{base_tusk_neg}:1.95), {eff_neg_str}'
        eff_neg_head_04 = eff_neg_str[:260].lower()
        if style_low in ('cartoonish', 'anime') and 'photorealistic' not in eff_neg_head_04:
            eff_neg_str = f'(photorealistic, semi-realistic, 2.5d, 3d shading, soft airbrushed gradients, glossy 3d skin, raw photo, live-action photograph, 3d render, 3d cgi, unreal engine, octane render, rotoscoped photo filter, traced photo, muddy brown colors, double mouth, smudged lips, realistic 3d nose bridge, realistic skin pores, subsurface scattering, 35mm film:1.92), {eff_neg_str}'
        elif style_low in ('realism', 'cinematic-film-35mm', 'dark-fantasy-real', 'dark-fantasy', 'original') and not any(tok in eff_neg_head_04 for tok in ('semi-realistic', '2d illustration', '2d digital painting')):
            eff_neg_str = f'(2d illustration, 2d painted, flat 2d, digital painting, fantasy painting, fantasy book cover, wlop style, oil painting, concept art, semi-realistic, stylized 3d, 3d cgi, airbrushed skin, plastic doll skin, smooth porcelain skin, anime, manga, cel-shading, cartoon, cartoonish, lineart:1.95), {eff_neg_str}'
        elif style_low == 'dark-fantasy-cgi' and not any(tok in eff_neg_head_04 for tok in ('fantasy book cover', '2d digital painting', '2d illustration')):
            eff_neg_str = f'(2d illustration, 2d painted, flat 2d, 2d digital painting, fantasy book cover, concept art, oil painting, wlop style, painterly brushwork, flat canvas, painted 2d background, raw candid documentary photo, anime, manga, cel-shading, cartoon, cartoonish, lineart:1.90), {eff_neg_str}'
        bus['krea2_image_prompt'] = eff_pos_str
        bus['adaptive_negative_prompt'] = eff_neg_str
        omni_b = bus.get('omni_reference_bundle') if isinstance(bus.get('omni_reference_bundle'), dict) else {}
        has_vid_scene_04 = bool(omni_b.get('has_video_scene_template', False))
        s5_two_p_04 = bool(omni_b.get('s5_has_two_people', False))
        sat_str_04 = float(bus.get('color_saturation_strength', dock_cfg.get('color_saturation_strength', 0.80)) or 0.80)
        bus['color_saturation_strength'] = sat_str_04
        dock_cfg['color_saturation_strength'] = sat_str_04
        dock_cfg['s5_has_two_people'] = s5_two_p_04
        has_active_inpaint_mask = isinstance(omni_b.get('inpaint_mask'), torch.Tensor) and omni_b.get('inpaint_mask').numel() > 0
        has_direct_src = isinstance(source_image, torch.Tensor) and source_image.numel() > 0 and float(source_image.detach().abs().max().item()) > 1e-04
        has_omni_src = bool(omni_b.get('active') and omni_b.get('has_image_slots', True) and isinstance(omni_b.get('master_composite_image'), torch.Tensor) and float(omni_b['master_composite_image'].detach().abs().max().item()) > 1e-04)
        is_t2i_mode = (
            str(bus.get('generation_mode', 'I2I') or 'I2I').upper().startswith('T2I')
            and not bool(bus.get('has_source_image', False))
            and not has_direct_src
            and not has_omni_src
            and not has_active_inpaint_mask
            and not has_vid_scene_04
        )
        raw_src = source_image if (has_direct_src and not is_t2i_mode) else (omni_b.get('master_composite_image') if (has_omni_src and not is_t2i_mode) else bus.get('ingest_image'))
        ref_p = omni_b.get('slot2_person_image') if omni_b.get('active') and omni_b.get('slot2_person_image') is not None else bus.get('ref_image_2_person')
        ref_c = omni_b.get('slot3_clothing_image') if omni_b.get('active') and omni_b.get('slot3_clothing_image') is not None else bus.get('ref_image_3_clothing')
        ref_bg = omni_b.get('slot4_background_image') if omni_b.get('active') and omni_b.get('slot4_background_image') is not None else bus.get('ref_image_4_background')
        s3_ootd_str = float(omni_b.get('slot3_ootd_strength', 0.85) or 0.85)
        s3_pres_nh = bool(omni_b.get('slot3_preserve_neck_and_hands', True))
        s4_relight = float(omni_b.get('slot4_horizon_relight_match', 0.55) or 0.55) if (ref_bg is not None) else 0.0
        eff_src_img = raw_src if (isinstance(raw_src, torch.Tensor) and raw_src.numel() > 0 and float(raw_src.detach().abs().max().item()) > 1e-04 and not is_t2i_mode) else None
        is_baked_img_turbo = bool(bus.get('baked_in_image_turbo', False) or getattr(stage1_model, '_ez_baked_in_turbo', False))
        is_sdxl_dmd2_04 = bool(is_sdxl_arch_04 and (bus.get('sdxl_dmd2_active', False) or getattr(stage1_model, '_ez_sdxl_dmd2_active', False) or getattr(stage1_model, '_ez_baked_sdxl_turbo', False)))
        is_flux_schnell_04 = bool(img_arch_04 == 'flux' and (bus.get('flux_schnell_active', False) or getattr(stage1_model, '_ez_flux_schnell_active', False)))
        has_flux_turbo_04 = bool(img_arch_04 == 'flux' and (bus.get('flux_turbo_lora_active', False) or getattr(stage1_model, '_ez_flux_turbo_lora_active', False)))
        auto_cfg_04 = _apply_beginner_multi_arch_sampler_autopilot(
            img_arch=img_arch_04,
            style_low=style_low,
            stage1_steps=stage1_steps,
            stage1_cfg=stage1_cfg,
            stage1_sampler_name=stage1_sampler_name,
            stage1_scheduler=stage1_scheduler,
            stage2_steps=stage2_steps,
            stage2_cfg=stage2_cfg,
            handoff_percent=handoff_percent,
            final_width=final_width,
            final_height=final_height,
            is_baked_img_turbo=is_baked_img_turbo,
            is_sdxl_dmd2=is_sdxl_dmd2_04,
            is_flux_schnell=is_flux_schnell_04,
            has_flux_turbo_lora=has_flux_turbo_04,
        )
        stage1_steps = auto_cfg_04['stage1_steps']
        stage1_cfg = auto_cfg_04['stage1_cfg']
        stage1_sampler_name = auto_cfg_04['stage1_sampler_name']
        stage1_scheduler = auto_cfg_04['stage1_scheduler']
        stage2_steps = auto_cfg_04['stage2_steps']
        stage2_cfg = auto_cfg_04['stage2_cfg']
        handoff_percent = auto_cfg_04['handoff_percent']
        final_width = auto_cfg_04['final_width']
        final_height = auto_cfg_04['final_height']
        if auto_cfg_04['log_msg']:
            print(auto_cfg_04['log_msg'])
        krea_sig = _compute_krea2_generation_signature(bus=bus, eff_pos_str=eff_pos_str, style_low=style_low, rating_tier=rating_tier, eff_seed=eff_seed, seed_mode=seed_mode, handoff_percent=handoff_percent, stage3_handoff_percent=stage3_handoff_percent, stage1_steps=stage1_steps, stage1_cfg=stage1_cfg, stage1_sampler_name=stage1_sampler_name, stage1_scheduler=stage1_scheduler, stage2_steps=stage2_steps, stage2_cfg=stage2_cfg, stage2_sampler_name=stage2_sampler_name, stage2_scheduler=stage2_scheduler, final_width=final_width, final_height=final_height, upscale_method=upscale_method, i2i_denoise=i2i_denoise, enable_frequency_polish=enable_frequency_polish, skin_blur_radius=skin_blur_radius, skin_texture_strength=skin_texture_strength, skin_polish_opacity=skin_polish_opacity, dock_cfg=dock_cfg, ref_tensors=(eff_src_img, ref_p, ref_c, ref_bg))
        cached_hit = _try_load_cached_krea2_keyframe(krea_sig, force_reuse_latest=('reuse_latest' in mode_low))
        if cached_hit is not None:
            (c_img, c_s3, c_anat, c_ui, c_fname, c_seed) = cached_hit
            print(f'[EZ-KREA2-CACHE] ⚡ Ingen ändring i Krea 2-parametrar ({c_fname or "RAM"}) -> Hoppar över bildgenerering och skickar senaste bilden direkt till MiniMax!')
            vid_meta_cache = _resolve_pipeline_video_model_metadata(bus)
            prev_kf_meta = dict(_KREA2_KEYFRAME_VAULT.get('krea2_saved_metadata') or {})
            if prev_kf_meta:
                prev_kf_meta.update({k: v for k, v in vid_meta_cache.items() if v})
                if bus.get('h3_video_timeline_prompt'):
                    prev_kf_meta['h3_video_timeline_prompt'] = str(bus.get('h3_video_timeline_prompt'))
                bus['krea2_saved_metadata'] = prev_kf_meta
            sc_cached = str(_KREA2_KEYFRAME_VAULT.get('keyframe_sidecar_path') or '')
            if sc_cached and Path(sc_cached).exists() and prev_kf_meta:
                try:
                    Path(sc_cached).write_text(json.dumps(prev_kf_meta, indent=2, ensure_ascii=False), encoding='utf-8')
                    bus['keyframe_sidecar_path'] = sc_cached
                except Exception:
                    pass
            bus['keyframe_ready'] = True
            bus['keyframe_image'] = c_img
            if c_fname:
                bus['keyframe_filename'] = c_fname
            bus['image_sampler_seed'] = int(c_seed or eff_seed)
            bus = _sanitize_bus_for_video_handoff(bus)
            return {'ui': {'ez_images': c_ui}, 'result': (c_img, c_s3, bus, c_anat)}
        prev_style_key = getattr(stage1_model, '_ez_applied_style_age_key', None) if stage1_model is not None else None
        did_rebuild_04 = False
        try:
            from ..EZ_ENGINES.engine_ez_03_cinematrix_image_lora_splitter import rebuild_models_for_style_target
            (stage1_model, stage2_model, image_clip) = rebuild_models_for_style_target(stage1_model, stage2_model, image_clip, style_low, age_years=age_years, has_orc_tusks=has_orc_tusks_04)
            did_rebuild_04 = (prev_style_key is not None and getattr(stage1_model, '_ez_applied_style_age_key', None) != prev_style_key)
        except Exception:
            pass
        pre_pos_str = str(bus.get('pre_encoded_pos_str', '') or '').strip()
        pre_neg_str = str(bus.get('pre_encoded_neg_str', '') or '').strip()
        if image_clip is not None and (did_rebuild_04 or (eff_pos_str and eff_pos_str != pre_pos_str)):
            positive = None
        if image_clip is not None and (did_rebuild_04 or (eff_neg_str and eff_neg_str != pre_neg_str)):
            negative = None
        if positive is None and not did_rebuild_04 and bus.get('pre_encoded_pos_cond') is not None and (not eff_pos_str or pre_pos_str == eff_pos_str):
            positive = bus.get('pre_encoded_pos_cond')
        if negative is None and not did_rebuild_04 and bus.get('pre_encoded_neg_cond') is not None and (not eff_neg_str or pre_neg_str == eff_neg_str):
            negative = bus.get('pre_encoded_neg_cond')
        if image_clip is not None and (positive is None or negative is None):
            clip_cache = getattr(image_clip, '_ez_cond_cache', None)
            style_cache_tag = getattr(stage1_model, '_ez_applied_style_age_key', style_low)
            pos_key = ('pos', style_cache_tag, eff_pos_str)
            neg_key = ('neg', style_cache_tag, eff_neg_str)
            cache_key = (style_cache_tag, eff_pos_str, eff_neg_str)
            did_encode = False
            if positive is None:
                if isinstance(clip_cache, dict) and pos_key in clip_cache:
                    positive = clip_cache[pos_key]
                elif isinstance(clip_cache, dict) and cache_key in clip_cache:
                    positive = clip_cache[cache_key][0]
                else:
                    pos_tok = image_clip.tokenize(eff_pos_str)
                    positive = image_clip.encode_from_tokens_scheduled(pos_tok)
                    if isinstance(clip_cache, dict):
                        clip_cache[pos_key] = positive
                    did_encode = True
            if negative is None:
                if isinstance(clip_cache, dict) and neg_key in clip_cache:
                    negative = clip_cache[neg_key]
                elif isinstance(clip_cache, dict) and cache_key in clip_cache:
                    negative = clip_cache[cache_key][1]
                else:
                    neg_tok = image_clip.tokenize(eff_neg_str)
                    negative = image_clip.encode_from_tokens_scheduled(neg_tok)
                    if isinstance(clip_cache, dict):
                        clip_cache[neg_key] = negative
                    did_encode = True
            if isinstance(clip_cache, dict) and positive is not None and negative is not None:
                clip_cache[cache_key] = (positive, negative)
            if did_encode and hasattr(comfy.model_management, 'soft_empty_cache'):
                comfy.model_management.soft_empty_cache()
        if positive is None or negative is None:
            raise ValueError('Anslut antingen (image_clip + krea2_image_prompt) eller (positive + negative) till EZ [04] Krea 2 Sampler.')
        has_extra_refs = any(isinstance(x, torch.Tensor) and x.ndim >= 3 and float(x.abs().max().item()) > 1e-04 for x in (ref_p, ref_c, ref_bg))
        has_real_i2i = (isinstance(eff_src_img, torch.Tensor) and eff_src_img.ndim >= 3 and (float(eff_src_img.abs().max().item()) > 1e-04)) or has_extra_refs
        base_w = int(bus.get('base_width', 0) or 0)
        base_h = int(bus.get('base_height', 0) or 0)
        if base_w <= 0 or base_h <= 0:
            if isinstance(eff_src_img, torch.Tensor) and eff_src_img.ndim >= 3:
                base_h = int(eff_src_img.shape[-3])
                base_w = int(eff_src_img.shape[-2])
            else:
                (base_w, base_h) = (1248, 832)
        if is_sdxl_arch_04:
            (base_w, base_h, _) = _clamp_sdxl_4ch_resolution_pair(base_w, base_h)
        single_stage_mode = int(stage2_steps) <= 0 or float(handoff_percent) >= 99.9
        active_s2_turbo_name = str(bus.get('active_turbo_lora', '') or '').strip()
        s2_t_low = active_s2_turbo_name.lower()
        is_dmd2_or_lcm_04 = bool(is_sdxl_dmd2_04 or any((tk in s2_t_low for tk in ('dmd2', 'lcm', 'lightning', 'hyper', '4step', '8step'))))
        has_s2_turbo = bool(is_baked_img_turbo or is_flux_schnell_04 or has_flux_turbo_04 or (active_s2_turbo_name and active_s2_turbo_name != 'None' and (is_dmd2_or_lcm_04 or style_low not in ('cartoonish', 'anime'))))
        eff_s2_cfg = float(stage2_cfg) if has_s2_turbo else (max(3.2, float(stage1_cfg), float(stage2_cfg)) if style_low in ('cartoonish', 'anime') else float(stage2_cfg))
        s2_neg = _zero_out_conditioning(negative) if math.isclose(eff_s2_cfg, 1.0) else negative
        if has_real_i2i:
            eff_final_w = int(final_width) if int(final_width) > 0 else int(bus.get('final_width', base_w) or base_w)
            eff_final_h = int(final_height) if int(final_height) > 0 else int(bus.get('final_height', base_h) or base_h)
            if is_sdxl_arch_04:
                (eff_final_w, eff_final_h, _) = _clamp_sdxl_4ch_resolution_pair(eff_final_w, eff_final_h)
            i2i_w = max(64, int(round(float(eff_final_w) / 16.0) * 16))
            i2i_h = max(64, int(round(float(eff_final_h) / 16.0) * 16))
            if omni_b.get('active') and isinstance(omni_b.get('master_composite_image'), torch.Tensor):
                from ..EZ_ENGINES.engine_ez_13_cinematrix_omni_reference_loader import resize_bhwc
                full_s1 = omni_b.get('raw_slot1_fullres')
                use_raw_s1 = (not has_extra_refs and not has_vid_scene_04 and isinstance(full_s1, torch.Tensor) and float(full_s1.abs().max().item()) > 1e-04)
                src_tensor = full_s1 if use_raw_s1 else omni_b['master_composite_image']
                if isinstance(src_tensor, torch.Tensor) and src_tensor.ndim >= 3 and int(src_tensor.shape[-3]) >= 16 and int(src_tensor.shape[-2]) >= 16:
                    src_aspect = float(src_tensor.shape[-2]) / max(1.0, float(src_tensor.shape[-3]))
                    ui_aspect = float(i2i_w) / max(1.0, float(i2i_h))
                    if abs(math.log(max(0.05, ui_aspect) / max(0.05, src_aspect))) > 0.08:
                        mp_area = float(i2i_w * i2i_h)
                        i2i_w = max(64, int(round(math.sqrt(mp_area * src_aspect) / 16.0) * 16))
                        i2i_h = max(64, int(round(math.sqrt(mp_area / src_aspect) / 16.0) * 16))
                src_bhwc = resize_bhwc(src_tensor, i2i_w, i2i_h)
            else:
                ref_probe = eff_src_img if (isinstance(eff_src_img, torch.Tensor) and eff_src_img.ndim >= 3) else (ref_bg if isinstance(ref_bg, torch.Tensor) else ref_p)
                if isinstance(ref_probe, torch.Tensor) and ref_probe.ndim >= 3 and int(ref_probe.shape[-3]) >= 16 and int(ref_probe.shape[-2]) >= 16:
                    src_aspect = float(ref_probe.shape[-2]) / max(1.0, float(ref_probe.shape[-3]))
                    ui_aspect = float(i2i_w) / max(1.0, float(i2i_h))
                    if abs(math.log(max(0.05, ui_aspect) / max(0.05, src_aspect))) > 0.08:
                        mp_area = float(i2i_w * i2i_h)
                        i2i_w = max(64, int(round(math.sqrt(mp_area * src_aspect) / 16.0) * 16))
                        i2i_h = max(64, int(round(math.sqrt(mp_area / src_aspect) / 16.0) * 16))
                src_bhwc = _compose_multi_reference_canvas(eff_src_img, ref_p, ref_c, ref_bg, target_w=i2i_w, target_h=i2i_h, ootd_strength=s3_ootd_str, preserve_neck_and_hands=s3_pres_nh, horizon_relight_match=s4_relight)
            vae_src_bhwc = src_bhwc if is_sdxl_arch_04 else _precondition_i2i_source_for_style_bhwc(
                src_bhwc,
                style_low=style_low,
                seed=eff_seed,
                dock_cfg=dock_cfg,
                has_multi_cast=has_multi_cast_04,
                has_vid_scene=has_vid_scene_04,
                has_ref_p=(ref_p is not None),
                raw_denoise=float(i2i_denoise),
                has_orc_tusks=has_orc_tusks_04,
            )
            try:
                enc_lat = image_vae.encode(vae_src_bhwc)
            except Exception:
                enc_lat = image_vae.encode_tiled(vae_src_bhwc, tile_x=tile_sz, tile_y=tile_sz)
            if enc_lat.ndim == 5:
                enc_lat = enc_lat[:, :, 0, :, :]
            enc_lat_cpu = enc_lat.detach().cpu()
            latent_input = {'samples': enc_lat_cpu}
            if hasattr(comfy.model_management, 'soft_empty_cache'):
                comfy.model_management.soft_empty_cache()
            inp_mask = omni_b.get('inpaint_mask') if omni_b.get('has_inpaint_mask') else bus.get('outpaint_mask')
            co_star_t2i_mask = None
            if isinstance(inp_mask, torch.Tensor) and float(inp_mask.detach().abs().max().item()) > 0.02:
                m_t = inp_mask.detach().cpu().float()
                if m_t.ndim == 2:
                    m_t = m_t.unsqueeze(0)
                if int(m_t.shape[-2]) != i2i_h or int(m_t.shape[-1]) != i2i_w:
                    m_t = torch.nn.functional.interpolate(m_t.unsqueeze(1), size=(i2i_h, i2i_w), mode='bilinear', align_corners=False).squeeze(1)
                latent_input['noise_mask'] = m_t
            raw_ui_denoise = max(0.08, min(1.0, float(i2i_denoise)))
            if has_multi_cast_04:
                eff_rf_denoise = max(0.78, min(1.0, raw_ui_denoise))
            elif has_vid_scene_04:
                eff_rf_denoise = max(0.08, min(0.92, raw_ui_denoise))
            elif style_low in ('cartoonish', 'anime'):
                eff_rf_denoise = max(0.76, min(0.90, raw_ui_denoise + 0.04)) if raw_ui_denoise >= 0.65 else raw_ui_denoise
            elif style_low == 'original':
                eff_rf_denoise = max(0.08, min(0.58, raw_ui_denoise))
            else:
                eff_rf_denoise = raw_ui_denoise
            ref_lat_zones = compute_downscaled_latent_anatomy_zones(src_bhwc, int(enc_lat_cpu.shape[-2]), int(enc_lat_cpu.shape[-1]), dock_cfg=dock_cfg) if 'noise_mask' not in latent_input else {}
            face_m_lat = ref_lat_zones.get('face') if isinstance(ref_lat_zones, dict) else None
            torso_m_lat = ref_lat_zones.get('torso') if isinstance(ref_lat_zones, dict) else None
            mouth_m_lat = ref_lat_zones.get('mouth') if (has_orc_tusks_04 and isinstance(ref_lat_zones, dict)) else None
            anat_core_lat = ref_lat_zones.get('anat_core') if isinstance(ref_lat_zones, dict) else None
            prop_blood_lat = ref_lat_zones.get('prop_blood') if isinstance(ref_lat_zones, dict) else None
            dock_lock_str = float(dock_cfg.get('reference_face_lock_strength', 0.78)) if isinstance(dock_cfg, dict) else 0.78
            lock_mult = max(0.0, min(1.30, dock_lock_str / 0.78))
            is_2d_style = style_low in ('anime', 'cartoonish')
            if not has_vid_scene_04:
                base_anc = 0.32 if is_2d_style else (0.26 if style_low == 'semi-real' else (0.42 if style_low == 'original' else 0.28))
                anc_str = base_anc * lock_mult
                eff_face_anc_lat = face_m_lat if (age_years <= 35 and not is_2d_style) else None
            else:
                anc_str = (0.14 if is_2d_style else 0.16) * lock_mult
                eff_face_anc_lat = None
            if 'noise_mask' not in latent_input and anc_str > 0.01 and (not is_sdxl_arch_04):
                latent_input['reactor_ref_latent'] = enc_lat_cpu
                latent_input['reactor_struct_weight'] = min(0.34, anc_str * 0.90)
                latent_input['reactor_struct_mask'] = (torch.clamp(1.0 - co_star_t2i_mask, 0.0, 1.0) if isinstance(co_star_t2i_mask, torch.Tensor) else anat_core_lat)
                latent_input['reactor_2d_style'] = bool(is_2d_style)
                if has_orc_tusks_04 and isinstance(mouth_m_lat, torch.Tensor):
                    latent_input['reactor_mouth_mask'] = mouth_m_lat
            (s1_pos_cn, s1_neg_cn, active_cnet) = _apply_tier_optimized_native_controlnet(stage1_model, positive, negative, image_vae, src_bhwc, omni_b=omni_b, tier_profile=tier_prof, co_star_t2i_mask=co_star_t2i_mask, style_low=style_low)
            tusk_w_s1 = 0.52 if is_2d_style else 0.58
            tusk_w_s2 = 0.42 if is_2d_style else 0.52
            tusk_w_s3 = 0.28 if is_2d_style else 0.58
            min_s1_single = 4 if (is_baked_img_turbo or is_sdxl_dmd2_04 or is_flux_schnell_04 or has_flux_turbo_04) else 12
            min_s1_triplet = 6 if (is_baked_img_turbo or is_sdxl_dmd2_04 or is_flux_schnell_04 or has_flux_turbo_04) else 16
            min_s2_triplet = 4 if (is_baked_img_turbo or is_sdxl_dmd2_04 or is_flux_schnell_04 or has_flux_turbo_04) else 8
            if single_stage_mode:
                s1_sig = _sigma_schedule(stage1_model, max(min_s1_single, int(stage1_steps)), stage1_sampler_name, stage1_scheduler, denoise=eff_rf_denoise)
                try:
                    s1_out = sample_stage_with_sigmas(stage1_model, eff_seed, stage1_cfg, stage1_sampler_name, stage1_scheduler, s1_pos_cn, s1_neg_cn, latent_input, s1_sig, disable_noise=False, tier_profile=tier_prof)
                finally:
                    _evict_stage1_controlnet_from_vram(active_cnet, tier_profile=tier_prof)
                if anc_str > 0.01 and 'noise_mask' not in latent_input:
                    if not is_2d_style:
                        s1_out = _anchor_original_style_latent(s1_out, enc_lat_cpu, anchor_strength=anc_str * 0.45, face_mask_lat=eff_face_anc_lat, torso_mask_lat=torso_m_lat, mouth_mask_lat=mouth_m_lat, prop_blood_mask_lat=prop_blood_lat, anat_core_mask_lat=anat_core_lat, co_star_t2i_mask_lat=co_star_t2i_mask, dock_cfg=dock_cfg, ref_lat_zones=ref_lat_zones)
                    if has_orc_tusks_04 and isinstance(mouth_m_lat, torch.Tensor):
                        s1_out = _anchor_orc_tusk_mouth_latent(s1_out, enc_lat_cpu, mouth_mask_lat=mouth_m_lat, style_low=style_low, stage_weight=tusk_w_s3, co_star_t2i_mask_lat=co_star_t2i_mask)
                stage3_out = _stabilize_latent_anatomy_outliers(s1_out, dock_cfg=dock_cfg, anatomy_mask_lat=anat_core_lat, ref_lat_zones=ref_lat_zones)
            else:
                raw_s1_ho = float(handoff_percent)
                min_s1_ho = 56.0 if style_low == 'original' else (58.0 if is_2d_style else 52.0)
                eff_s1_ho = max(min_s1_ho, raw_s1_ho) if (raw_s1_ho < min_s1_ho and float(eff_s2_cfg) <= 1.35) else raw_s1_ho
                eff_s3_ho = max(eff_s1_ho + 12.0, float(stage3_handoff_percent))
                eff_s3_ho = min(98.0, eff_s3_ho)
                (s1_sig, s2_sig, s3_sig) = build_three_stage_sigma_triplet(
                    stage1_model,
                    stage2_model,
                    max(min_s1_triplet, int(stage1_steps)),
                    max(min_s2_triplet, int(stage2_steps)),
                    stage1_sampler_name,
                    stage1_scheduler,
                    stage2_sampler_name,
                    stage2_scheduler,
                    eff_s1_ho,
                    eff_s3_ho,
                    denoise=eff_rf_denoise,
                )
                print(f'[EZ-KREA2-3STAGE] 🎨 I2I Steg 1/3 (Raw 0% -> {eff_s1_ho:.0f}% | {max(1, len(s1_sig)-1)} stp @ {stage1_sampler_name}/{stage1_scheduler}, CFG {stage1_cfg})')
                try:
                    s1_out = sample_stage_with_sigmas(stage1_model, eff_seed, stage1_cfg, stage1_sampler_name, stage1_scheduler, s1_pos_cn, s1_neg_cn, latent_input, s1_sig, disable_noise=False, tier_profile=tier_prof)
                finally:
                    _evict_stage1_controlnet_from_vram(active_cnet, tier_profile=tier_prof)
                if anc_str > 0.01 and 'noise_mask' not in latent_input:
                    s1_anc_mult = 0.0 if is_2d_style else (0.82 if style_low == 'original' else 0.45)
                    if s1_anc_mult > 0.01:
                        s1_out = _anchor_original_style_latent(s1_out, enc_lat_cpu, anchor_strength=anc_str * s1_anc_mult, face_mask_lat=eff_face_anc_lat, torso_mask_lat=torso_m_lat, mouth_mask_lat=None if is_2d_style else mouth_m_lat, prop_blood_mask_lat=prop_blood_lat, anat_core_mask_lat=anat_core_lat, co_star_t2i_mask_lat=co_star_t2i_mask, dock_cfg=dock_cfg, ref_lat_zones=ref_lat_zones)
                    if has_orc_tusks_04 and isinstance(mouth_m_lat, torch.Tensor):
                        s1_out = _anchor_orc_tusk_mouth_latent(s1_out, enc_lat_cpu, mouth_mask_lat=mouth_m_lat, style_low=style_low, stage_weight=tusk_w_s1, co_star_t2i_mask_lat=co_star_t2i_mask)
                print(f'[EZ-KREA2-3STAGE] ⚡ I2I Steg 2/3 (Turbo {eff_s1_ho:.0f}% -> {eff_s3_ho:.0f}% | {max(1, len(s2_sig)-1)} stp @ {stage2_sampler_name}/{stage2_scheduler}, CFG {eff_s2_cfg})')
                s2_out = sample_stage_with_sigmas(stage2_model, eff_seed, eff_s2_cfg, stage2_sampler_name, stage2_scheduler, positive, s2_neg, s1_out, s2_sig, disable_noise=True, tier_profile=tier_prof)
                if has_orc_tusks_04 and 'noise_mask' not in latent_input and isinstance(mouth_m_lat, torch.Tensor):
                    s2_out = _anchor_orc_tusk_mouth_latent(s2_out, enc_lat_cpu, mouth_mask_lat=mouth_m_lat, style_low=style_low, stage_weight=tusk_w_s2, co_star_t2i_mask_lat=co_star_t2i_mask)
                s2_out = _stabilize_latent_anatomy_outliers(s2_out, dock_cfg=dock_cfg, anatomy_mask_lat=anat_core_lat, ref_lat_zones=ref_lat_zones)
                print(f'[EZ-KREA2-3STAGE] 💎 I2I Steg 3/3 (Polish {eff_s3_ho:.0f}% -> 100% | {max(1, len(s3_sig)-1)} stp @ {stage1_sampler_name}/{stage1_scheduler}, CFG {stage1_cfg})')
                s3_out = sample_stage_with_sigmas(stage1_model, eff_seed, stage1_cfg, stage1_sampler_name, stage1_scheduler, positive, negative, s2_out, s3_sig, disable_noise=True, tier_profile=tier_prof)
                if anc_str > 0.01 and 'noise_mask' not in latent_input:
                    s3_anc_mult = 0.0 if is_2d_style else (0.50 if style_low == 'original' else 0.18)
                    if s3_anc_mult > 0.01:
                        s3_out = _anchor_original_style_latent(s3_out, enc_lat_cpu, anchor_strength=anc_str * s3_anc_mult, face_mask_lat=eff_face_anc_lat, torso_mask_lat=torso_m_lat, mouth_mask_lat=mouth_m_lat, prop_blood_mask_lat=prop_blood_lat, anat_core_mask_lat=anat_core_lat, co_star_t2i_mask_lat=co_star_t2i_mask, dock_cfg=dock_cfg, ref_lat_zones=ref_lat_zones)
                    if has_orc_tusks_04 and isinstance(mouth_m_lat, torch.Tensor):
                        s3_out = _anchor_orc_tusk_mouth_latent(s3_out, enc_lat_cpu, mouth_mask_lat=mouth_m_lat, style_low=style_low, stage_weight=tusk_w_s3, co_star_t2i_mask_lat=co_star_t2i_mask)
                stage3_out = _stabilize_latent_anatomy_outliers(s3_out, dock_cfg=dock_cfg, anatomy_mask_lat=anat_core_lat, ref_lat_zones=ref_lat_zones)
        else:
            if hasattr(comfy.model_management, 'unload_all_models'):
                comfy.model_management.unload_all_models()
            if hasattr(comfy.model_management, 'soft_empty_cache'):
                comfy.model_management.soft_empty_cache()
            min_s1_t2i = 4 if (is_baked_img_turbo or is_sdxl_dmd2_04 or is_flux_schnell_04 or has_flux_turbo_04) else 12
            if single_stage_mode:
                s1_run_sig = _sigma_schedule(stage1_model, max(min_s1_t2i, int(stage1_steps)), stage1_sampler_name, stage1_scheduler, denoise=1.0)
            else:
                (s1_sig, s2_sig, s3_sig) = build_three_stage_sigma_triplet(stage1_model, stage2_model, stage1_steps, stage2_steps, stage1_sampler_name, stage1_scheduler, stage2_sampler_name, stage2_scheduler, handoff_percent, stage3_handoff_percent, denoise=1.0)
                upscale_requested = int(final_width) > 0 and int(final_height) > 0
                s1_run_sig = s1_sig.clone()
                if upscale_requested:
                    s1_run_sig[-1] = 0.0
            latent_input = _create_empty_krea2_latent(stage1_model, base_w, base_h)
            if not single_stage_mode:
                print(f'[EZ-KREA2-3STAGE] 🎨 T2I Steg 1/3 (Raw 0% -> {float(handoff_percent):.0f}% | {max(1, len(s1_run_sig)-1)} stp @ {stage1_sampler_name}/{stage1_scheduler}, CFG {stage1_cfg})')
            stage1_out = sample_stage_with_sigmas(stage1_model, eff_seed, stage1_cfg, stage1_sampler_name, stage1_scheduler, positive, negative, latent_input, s1_run_sig, disable_noise=False, tier_profile=tier_prof)
            if single_stage_mode:
                (up_lat, _) = _maybe_upscale_latent(stage1_model, stage1_out, final_width, final_height, upscale_method)
                stage3_out = _stabilize_latent_anatomy_outliers(up_lat, dock_cfg=dock_cfg)
            else:
                (stage2_input, did_upscale) = _maybe_upscale_latent(stage1_model, stage1_out, final_width, final_height, upscale_method)
                stage2_disable_noise = not did_upscale
                print(f'[EZ-KREA2-3STAGE] ⚡ T2I Steg 2/3 (Turbo {float(handoff_percent):.0f}% -> {float(stage3_handoff_percent):.0f}% | {max(1, len(s2_sig)-1)} stp @ {stage2_sampler_name}/{stage2_scheduler}, CFG {eff_s2_cfg}, Bislerp={did_upscale})')
                stage2_out = sample_stage_with_sigmas(stage2_model, eff_seed, eff_s2_cfg, stage2_sampler_name, stage2_scheduler, positive, s2_neg, stage2_input, s2_sig, disable_noise=stage2_disable_noise, tier_profile=tier_prof)
                stage2_out = _stabilize_latent_anatomy_outliers(stage2_out, dock_cfg=dock_cfg)
                print(f'[EZ-KREA2-3STAGE] 💎 T2I Steg 3/3 (Polish {float(stage3_handoff_percent):.0f}% -> 100% | {max(1, len(s3_sig)-1)} stp @ {stage1_sampler_name}/{stage1_scheduler}, CFG {stage1_cfg})')
                stage3_out = sample_stage_with_sigmas(stage1_model, eff_seed, stage1_cfg, stage1_sampler_name, stage1_scheduler, positive, negative, stage2_out, s3_sig, disable_noise=True, tier_profile=tier_prof)
        s3_samples = stage3_out['samples']
        if hasattr(comfy.model_management, 'unload_all_models'):
            comfy.model_management.unload_all_models()
        if hasattr(comfy.model_management, 'soft_empty_cache'):
            comfy.model_management.soft_empty_cache()
        try:
            decoded_image = image_vae.decode(s3_samples)
        except Exception:
            if aggressive_purge:
                comfy.model_management.soft_empty_cache()
            decoded_image = image_vae.decode_tiled(s3_samples, tile_x=tile_sz, tile_y=tile_sz)
        if decoded_image.ndim == 5:
            decoded_image = decoded_image.reshape(-1, decoded_image.shape[-3], decoded_image.shape[-2], decoded_image.shape[-1])
        decoded_image = torch.clamp(decoded_image.detach().cpu().float(), 0.0, 1.0)
        if has_real_i2i and not has_vid_scene_04 and isinstance(src_bhwc, torch.Tensor) and 'noise_mask' not in latent_input:
            if has_orc_tusks_04:
                decoded_image = _restore_i2i_orc_tusks_bhwc(decoded_image, src_bhwc, style_low=style_low, dock_cfg=dock_cfg, has_orc_tusks=has_orc_tusks_04, has_multi_cast=has_multi_cast_04)
            decoded_image = _harmonize_2d_i2i_skin_albedo_bhwc(decoded_image, src_bhwc, style_low=style_low, dock_cfg=dock_cfg, has_multi_cast=has_multi_cast_04, raw_prompt=raw_user_04)
            decoded_image = _blend_i2i_reference_beauty_bhwc(decoded_image, src_bhwc, style_low=style_low, raw_denoise=float(i2i_denoise), dock_cfg=dock_cfg, age_years=age_years, has_multi_cast=has_multi_cast_04)
        decoded_image = _apply_live_action_photographic_physics_bhwc(decoded_image, style_low=style_low, seed=eff_seed, dock_cfg=dock_cfg, age_years=age_years, ref_background=ref_bg, horizon_relight_match=s4_relight)
        anatomy_preview_img = decoded_image.clone()
        allow_skin_polish = bool(enable_frequency_polish) and (style_low not in ('cartoonish', 'anime'))
        if allow_skin_polish and float(skin_polish_opacity) > 0.01:
            try:
                if style_low == 'semi-real':
                    eff_blur_r = max(float(skin_blur_radius), 4.2)
                    eff_tex_s = min(float(skin_texture_strength), 0.90)
                elif age_years <= 20:
                    eff_blur_r = max(float(skin_blur_radius), 3.6)
                    eff_tex_s = min(float(skin_texture_strength), 0.95)
                elif age_years <= 29:
                    eff_blur_r = float(skin_blur_radius)
                    eff_tex_s = min(float(skin_texture_strength), 1.06)
                else:
                    eff_blur_r = min(float(skin_blur_radius), 2.4)
                    eff_tex_s = max(float(skin_texture_strength), 1.24)
                (decoded_image, anatomy_preview_img) = _apply_frequency_separation_polish(decoded_image, blur_radius=eff_blur_r, texture_strength=eff_tex_s, mix_opacity=float(skin_polish_opacity), dock_cfg=dock_cfg)
            except Exception:
                pass
        stage3_out = {'samples': s3_samples.detach().cpu()}
        ui_images = []
        saved_kf_path = ''
        if decoded_image.shape[0] > 0:
            now_dt = datetime.now()
            ts_now = now_dt.strftime('%Y%m%d_%H%M%S')
            arr_u8 = np.clip(decoded_image[0].numpy() * 255.0, 0, 255).astype(np.uint8)
            pure_pil = Image.fromarray(arr_u8)
            vid_meta_04 = _resolve_pipeline_video_model_metadata(bus)
            active_img_unet = str(bus.get('active_image_unet') or getattr(stage1_model, '_ez_active_image_unet', '') or '')
            active_img_loras = bus.get('active_style_loras') if bus.get('active_style_loras') else list(getattr(stage1_model, '_ez_active_style_loras', []) or [])
            kf_meta_payload = {
                'generator': 'EZ Cinematrix Studio v2.6 // Node [04] Krea 2 Three-Stage Sampler',
                'timestamp': now_dt.strftime('%Y-%m-%d %H:%M:%S'),
                'style_target': style_low,
                'seed': int(eff_seed),
                'seed_mode': str(seed_mode),
                'resolution': f'{pure_pil.width}x{pure_pil.height}',
                'i2i_denoise': round(float(i2i_denoise), 3),
                'handoff_percent': round(float(handoff_percent), 2),
                'stage3_handoff_percent': round(float(stage3_handoff_percent), 2),
                'stage1': {'steps': int(stage1_steps), 'cfg': float(stage1_cfg), 'sampler': str(stage1_sampler_name), 'scheduler': str(stage1_scheduler)},
                'stage2': {'steps': int(stage2_steps), 'cfg': float(eff_s2_cfg), 'sampler': str(stage2_sampler_name), 'scheduler': str(stage2_scheduler)},
                'upscale_method': str(upscale_method),
                'enable_frequency_polish': bool(enable_frequency_polish),
                'subject_1_age': str(bus.get('subject_1_age', '')),
                'active_image_unet': active_img_unet,
                'active_style_loras': active_img_loras,
                'video_model': str(vid_meta_04.get('active_video_unet', '')),
                'active_video_unet': str(vid_meta_04.get('active_video_unet', '')),
                'video_unet_fl2va': str(vid_meta_04.get('video_unet_fl2va', '')),
                'video_unet_ref2va': str(vid_meta_04.get('video_unet_ref2va', '')),
                'video_clip_name': str(vid_meta_04.get('video_clip_name', '')),
                'video_vae_name': str(vid_meta_04.get('video_vae_name', '')),
                'audio_vae_name': str(vid_meta_04.get('audio_vae_name', '')),
                'active_video_loras': vid_meta_04.get('active_video_loras', []),
                'video_turbo_lora': str(vid_meta_04.get('video_turbo_lora', '')),
                'krea2_image_prompt': eff_pos_str,
                'h3_video_timeline_prompt': str(bus.get('h3_video_timeline_prompt', '') or ''),
                'adaptive_negative_prompt': eff_neg_str,
            }
            bus['krea2_saved_metadata'] = kf_meta_payload
            if save_keyframe_to_disk:
                base_out_dir = Path(folder_paths.get_output_directory())
                target_out_dir = _resolve_date_subfolder_path(base_out_dir, date_folder_format, now_dt=now_dt)
                out_fname = f'EZ_Krea2_Keyframe_{style_slug}_{ts_now}_{int(eff_seed) % 10000}.png'
                saved_kf_path = str(target_out_dir / out_fname)
                if save_metadata:
                    png_info = PngImagePlugin.PngInfo()
                    param_summary = f"{eff_pos_str}\nNegative prompt: {eff_neg_str}\nSteps: {stage1_steps}+{stage2_steps}, Sampler: {stage1_sampler_name}/{stage1_scheduler}, CFG scale: {stage1_cfg}/{eff_s2_cfg}, Seed: {eff_seed}, Size: {pure_pil.width}x{pure_pil.height}, Style: {style_low}, Denoise: {i2i_denoise}, Image Model: {active_img_unet}, Video Model: {vid_meta_04.get('active_video_unet', '')}"
                    png_info.add_text('parameters', param_summary)
                    png_info.add_text('prompt', eff_pos_str)
                    png_info.add_text('negative_prompt', eff_neg_str)
                    png_info.add_text('cinematrix_metadata', json.dumps(kf_meta_payload, ensure_ascii=False))
                    pure_pil.save(saved_kf_path, pnginfo=png_info)
                    try:
                        meta_sidecar = target_out_dir / f'EZ_Krea2_Keyframe_{style_slug}_{ts_now}_{int(eff_seed) % 10000}.metadata.json'
                        meta_sidecar.write_text(json.dumps(kf_meta_payload, indent=2, ensure_ascii=False), encoding='utf-8')
                        bus['keyframe_sidecar_path'] = str(meta_sidecar)
                    except Exception:
                        pass
                else:
                    pure_pil.save(saved_kf_path)
                bus['keyframe_filename'] = out_fname
            temp_dir = Path(folder_paths.get_temp_directory())
            temp_dir.mkdir(parents=True, exist_ok=True)
            prev_fname = f'EZ_Krea2_Preview_{style_slug}_{ts_now}_{int(eff_seed) % 10000}.png'
            prev_pil = pure_pil.copy()
            try:
                draw = ImageDraw.Draw(prev_pil)
                (pw, ph) = prev_pil.size
                dock_tag = 'DOCK: OVERRIDE' if dock_cfg else 'ANATOMY: AUTO'
                polish_tag = f'FREQ-POLISH: ON ({dock_tag})' if enable_frequency_polish else f'FREQ-POLISH: OFF ({dock_tag})'
                arch_hud_lbl = 'KREA 2' if img_arch_04 == 'krea2' else img_arch_04.upper()
                info_txt = f'EZ [04] {arch_hud_lbl} // STYLE: {style_slug.upper()} // {pw}x{ph} // SEED: {eff_seed} // {polish_tag}'
                font_obj = None
                font_sz = max(22, int(pw * 0.024))
                for cand_sz in range(font_sz, 13, -2):
                    for f_name in ('consolab.ttf', 'arialbd.ttf', 'segoeuib.ttf', 'DejaVuSans-Bold.ttf', 'DejaVuSansMono-Bold.ttf'):
                        try:
                            font_obj = ImageFont.truetype(f_name, cand_sz)
                            break
                        except Exception:
                            continue
                    if font_obj is None:
                        try:
                            font_obj = ImageFont.load_default(size=cand_sz)
                        except Exception:
                            font_obj = ImageFont.load_default()
                    bbox = draw.textbbox((0, 0), info_txt, font=font_obj)
                    if (bbox[2] - bbox[0]) <= (pw - 28):
                        font_sz = cand_sz
                        break
                    font_obj = None
                if font_obj is None:
                    font_obj = ImageFont.load_default(size=18)
                bbox = draw.textbbox((0, 0), info_txt, font=font_obj)
                txt_h = max(16, bbox[3] - bbox[1])
                bar_h = max(36, int(txt_h * 1.85))
                draw.rectangle([(0, ph - bar_h), (pw, ph)], fill=(10, 12, 18))
                draw.line([(0, ph - bar_h), (pw, ph - bar_h)], fill=(0, 240, 255), width=max(2, int(ph * 0.002)))
                txt_y = ph - bar_h + max(4, (bar_h - txt_h) // 2) - bbox[1]
                draw.text((14, txt_y), info_txt, fill=(0, 240, 255), font=font_obj)
            except Exception:
                pass
            prev_pil.save(str(temp_dir / prev_fname))
            anat_fname = f'EZ_Krea2_Anatomy_{style_slug}_{ts_now}_{int(eff_seed) % 10000}.png'
            try:
                if isinstance(anatomy_preview_img, torch.Tensor) and anatomy_preview_img.ndim == 4 and (anatomy_preview_img.shape[0] > 0):
                    a_u8 = np.clip(anatomy_preview_img[0].numpy() * 255.0, 0, 255).astype(np.uint8)
                    Image.fromarray(a_u8).save(str(temp_dir / anat_fname))
            except Exception:
                pass
            k_meta = {'filename': prev_fname, 'anatomy_png': anat_fname, 'subfolder': '', 'type': 'temp'}
            ui_images.append(k_meta)
            try:
                from server import PromptServer
                if getattr(PromptServer, 'instance', None) is not None:
                    PromptServer.instance.send_sync('ez_cinematrix_krea2_ready', k_meta)
            except Exception:
                pass
        if aggressive_purge or not bool(tier_prof.get('persistent_vram_weights', False)):
            loaded_list = getattr(comfy.model_management, 'current_loaded_models', None)
            if isinstance(loaded_list, list):
                while len(loaded_list) > 0:
                    lm = loaded_list.pop()
                    try:
                        lm.currently_used = False
                        lm.model_unload()
                    except Exception:
                        pass
            if hasattr(comfy.model_management, 'unload_all_models'):
                comfy.model_management.unload_all_models()
            comfy.model_management.soft_empty_cache()
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        _store_cached_krea2_keyframe(krea_sig=krea_sig, decoded_image=decoded_image, stage3_out=stage3_out, anatomy_preview_img=anatomy_preview_img, ui_images=ui_images, keyframe_path=saved_kf_path, eff_seed=eff_seed)
        _KREA2_KEYFRAME_VAULT['krea2_saved_metadata'] = dict(bus.get('krea2_saved_metadata') or {})
        _KREA2_KEYFRAME_VAULT['keyframe_sidecar_path'] = str(bus.get('keyframe_sidecar_path') or '')
        bus['keyframe_ready'] = True
        bus['keyframe_image'] = decoded_image
        bus['image_sampler_seed'] = int(eff_seed)
        bus = _sanitize_bus_for_video_handoff(bus)
        return {'ui': {'ez_images': ui_images}, 'result': (decoded_image, stage3_out, bus, anatomy_preview_img)}
