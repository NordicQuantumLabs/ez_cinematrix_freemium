# -*- coding: utf-8 -*-
from ..EZ_ENGINES.engine_ez_03_cinematrix_image_lora_splitter import _get_convrot_hadamard_matrix, _is_non_unet_or_video_only_for_image, _is_baked_krea2_turbo_unet, _classify_image_unet_architecture, list_dynamic_image_models, list_dynamic_clip_encoders, list_dynamic_vaes, list_dynamic_loras_by_role, apply_krea2_dynamic_shift_patch, _parse_comfy_quant_tensor, _pre_dequantize_convrot_state_dict, _dequantize_rowwise_module_fallback, _ensure_int8_convrot_quant_compat, _load_diffusion_model_convrot_safe, load_and_split_image_models_with_loras, _H4_BASE, _CONVROT_HADAMARD_CACHE

import json
import math
import os
import gc
import torch
import folder_paths
import comfy.sd
import comfy.utils
import comfy.model_management
import comfy.model_sampling
import comfy.ops

class EzCinematrixImageLoaderAdapter:
    """Adapter orchestrating dynamic model loading, Stage 1/2 LoRA splitting, and CLIP encoding."""

    @staticmethod
    def execute_hub(unet_name, clip_name, clip_type, vae_name, stop_at_clip_layer, sampling_mode, style_lora_1, style_strength_1, style_lora_2, style_strength_2, style_lora_3, style_strength_3, turbo_acceleration_lora_LOCKED, turbo_strength, positive_prompt, negative_prompt, style_clip_strength_1=1.0, style_clip_strength_2=1.0, style_clip_strength_3=1.0, style_lora_4='None', style_strength_4=0.4, style_clip_strength_4=0.35, enable_style_lora_1=True, enable_style_lora_2=True, enable_style_lora_3=True, enable_style_lora_4=True, enable_turbo_lora=True, cinematrix_bus=None, image_model_spec=None, image_lora_spec=None):
        bus = dict(cinematrix_bus) if isinstance(cinematrix_bus, dict) else {}
        m_spec = image_model_spec if isinstance(image_model_spec, dict) else bus.get('civitai_image_model_spec') if isinstance(bus.get('civitai_image_model_spec'), dict) else None
        l_spec = image_lora_spec if isinstance(image_lora_spec, dict) else bus.get('civitai_image_lora_spec') if isinstance(bus.get('civitai_image_lora_spec'), dict) else None
        if isinstance(m_spec, dict):
            if str(m_spec.get('modality', 'IMAGE')).upper() != 'IMAGE':
                raise ValueError('[EZ-MODALITY-LOCK] Video-checkpoint får EJ skickas till EZ [03] Image Loader!')
            spec_unet = str(m_spec.get('unet_name', 'None') or 'None')
            has_spec_unet = bool(spec_unet and spec_unet != 'None' and (not _is_non_unet_or_video_only_for_image(spec_unet)))
            if has_spec_unet:
                unet_name = spec_unet
                if m_spec.get('clip_type'):
                    clip_type = str(m_spec['clip_type'])
            if (not clip_name or clip_name == 'None') and m_spec.get('clip_name') and (m_spec['clip_name'] != 'None'):
                clip_name = str(m_spec['clip_name'])
            if (not vae_name or vae_name == 'None') and m_spec.get('vae_name') and (m_spec['vae_name'] != 'None'):
                vae_name = str(m_spec['vae_name'])
        raw_style_pairs = [
            (style_lora_1, style_strength_1, style_clip_strength_1),
            (style_lora_2, style_strength_2, style_clip_strength_2),
            (style_lora_3, style_strength_3, style_clip_strength_3),
            (style_lora_4, style_strength_4, style_clip_strength_4),
        ]
        slot_enables = [bool(enable_style_lora_1), bool(enable_style_lora_2), bool(enable_style_lora_3), bool(enable_style_lora_4)]
        turbo_enabled = bool(enable_turbo_lora)
        trig_extra = ''
        if isinstance(l_spec, dict):
            if str(l_spec.get('modality', 'IMAGE')).upper() != 'IMAGE':
                raise ValueError('[EZ-MODALITY-LOCK] Video-LoRA får EJ skickas till EZ [03] Image Loader!')
            spec_loras = l_spec.get('style_loras')
            if isinstance(spec_loras, list) and any((item[0] != 'None' for item in spec_loras if isinstance(item, (list, tuple)) and len(item) >= 2)):
                parsed_spec = [(str(item[0]), float(item[1]), float(item[2]) if len(item) >= 3 else float(item[1])) for item in spec_loras if isinstance(item, (list, tuple)) and len(item) >= 2]
                while len(parsed_spec) < 4:
                    parsed_spec.append(raw_style_pairs[len(parsed_spec)])
                raw_style_pairs = parsed_spec[:4]
            spec_enables = l_spec.get('style_enables')
            if isinstance(spec_enables, list) and len(spec_enables) >= 4:
                slot_enables = [bool(slot_enables[idx] and bool(spec_enables[idx])) for idx in range(4)]
            if 'enable_turbo_lora' in l_spec:
                turbo_enabled = bool(turbo_enabled and bool(l_spec.get('enable_turbo_lora', True)))
            if l_spec.get('turbo_lora') and l_spec['turbo_lora'] != 'None':
                turbo_acceleration_lora_LOCKED = str(l_spec['turbo_lora'])
                turbo_strength = float(l_spec.get('turbo_strength', turbo_strength))
            trig_extra = str(l_spec.get('trigger_words', '') or '').strip()
        style_pairs = []
        for idx_s, sp in enumerate(raw_style_pairs):
            is_on = slot_enables[idx_s] if idx_s < len(slot_enables) else True
            if not is_on:
                if sp[0] and sp[0] != 'None':
                    print(f"[EZ-03-BYPASS] 🔇 Style LoRA {idx_s + 1} Bypassed (OFF): {sp[0]}")
                style_pairs.append(('None', 0.0, 0.0))
            else:
                style_pairs.append(sp)
        if not turbo_enabled:
            if turbo_acceleration_lora_LOCKED and turbo_acceleration_lora_LOCKED != 'None':
                print(f"[EZ-03-BYPASS] 🔇 Image Turbo LoRA Bypassed (OFF): {turbo_acceleration_lora_LOCKED}")
            turbo_acceleration_lora_LOCKED = 'None'
            turbo_strength = 0.0
        w = int(bus.get('base_width', 1248) or 1248)
        h = int(bus.get('base_height', 832) or 832)
        tier_prof = dict(bus.get('hardware_tier_profile', {})) if isinstance(bus.get('hardware_tier_profile'), dict) else {}
        is_nsfw = not str(bus.get('content_rating_mode', 'Uncensored')).strip().lower().startswith('sfw')
        if not is_nsfw:
            nsfw_lora_pat = ('nsfw', 'xxx', 'mysticxxx', 'nude', 'naked', 'sex', 'erotic', 'hentai', 'porn', 'cum', 'boob', 'tit', 'pussy', 'penis', 'blowjob', 'fuck', 'slut', 'lewd')
            filtered_pairs = []
            for lp in style_pairs:
                ln_low = str(lp[0] or '').lower()
                if any((tok in ln_low for tok in nsfw_lora_pat)):
                    print(f"[EZ-SFW-GUARD] 🛡️ SFW-läge aktivt i [03] -> Inaktiverar NSFW Bild-LoRA: {lp[0]}")
                    filtered_pairs.append(('None', 0.0, 0.0))
                else:
                    filtered_pairs.append(lp)
            style_pairs = filtered_pairs
            if any((tok in trig_extra.lower() for tok in nsfw_lora_pat)):
                trig_extra = ''
        raw_bus_style = str(bus.get('style_target', '') or '').strip().lower()
        raw_bus_age = str(bus.get('subject_1_age', '') or '').strip()
        live_qwen_style = ''
        live_qwen_age = ''
        try:
            from .adapter_ez_02_cinematrix_qwenvl_timeline import _ACTIVE_QWENVL_SCENE_STATE
            if isinstance(_ACTIVE_QWENVL_SCENE_STATE, dict):
                live_qwen_style = str(_ACTIVE_QWENVL_SCENE_STATE.get('style_target', '') or '').strip().lower()
                live_qwen_age = str(_ACTIVE_QWENVL_SCENE_STATE.get('subject_1_age', '') or '').strip()
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
                                live_qwen_style = cand_st
                            cand_age = str(n_in.get('custom_subject_1_age', '') or '').strip() or str(n_in.get('subject_1_age', '') or '').strip()
                            if cand_age and not isinstance(n_in.get('subject_1_age'), list):
                                live_qwen_age = cand_age
                            break
        except Exception:
            pass
        if live_qwen_style:
            raw_bus_style = live_qwen_style
        if live_qwen_age:
            raw_bus_age = live_qwen_age
        style_low = raw_bus_style or 'realism'
        if style_low.startswith('original'):
            style_low = 'original'
        import re
        from ..EZ_ENGINES.engine_ez_02_cinematrix_qwenvl_timeline import _parse_subject_age_years, _build_age_authority_profile, _extract_prompt_morphology_profile
        eff_pos = str(positive_prompt or '').strip() or str(bus.get('krea2_image_prompt', '') or '').strip()
        raw_user_03 = str(bus.get('raw_user_scene_input', '') or '').strip()
        morph_03 = _extract_prompt_morphology_profile(raw_user_03 if raw_user_03 else eff_pos)
        has_orc_tusks_03 = bool(morph_03['has_tusks'])
        if not has_orc_tusks_03 and eff_pos:
            eff_pos = re.sub(r'(?i)^Featuring\s+a\s+orc\s+warrior\s+with\s+deep\s+crimson-red\s+skin\s+and\s+two\s+sharp\s+protruding\s+white\s+lower-jaw\s+tusks[^,]*,\s*', '', eff_pos).strip()
        age_years = int(bus.get('subject_1_age_num') or _parse_subject_age_years(raw_bus_age or '25-year-old'))
        age_prof_03 = _build_age_authority_profile(raw_bus_age or f'{age_years}-year-old', has_orc_tusks=has_orc_tusks_03, style_target=style_low, tusk_descriptor=morph_03['feat_desc'])
        unscaled_style_pairs = list(style_pairs)
        from ..EZ_ENGINES.engine_ez_03_cinematrix_image_lora_splitter import scale_style_loras_for_target
        style_pairs = scale_style_loras_for_target(unscaled_style_pairs, style_low, age_years=age_years, has_orc_tusks=has_orc_tusks_03)
        default_core_neg = '(text, logo, watermark, signature, censored, mosaic censorship:1.5), 色调艳丽, 过曝, 静态, 细节模糊不清, 字幕, 风格, 作品, 画作, 画面, 静止, 整体发灰, 最差质量, 低质量, JPEG压缩残留, 丑陋的, 残缺的, 多余的手指, 画得不好的手部, 画得不好的脸部, 畸形的, 毁容的, 形态畸形的肢体, 手指融合, 静止不动的画面, 杂乱的背景, 三条腿, 背景人很多, 倒着走,' if is_nsfw else '(nsfw, nude, naked, nipples, breasts, cleavage, lingerie, bikini, explicit, cum, white cum, milky liquid, text, logo, watermark:1.6), 色调艳丽, 过曝, 静态, 细节模糊不清, 字幕, 风格, 作品, 画作, 画面, 静止, 整体发灰, 最差质量, 低质量, JPEG压缩残留, 丑陋的, 残缺的, 多余的手指, 画得不好的手部, 画得不好的脸部, 畸形的, 毁容的, 形态畸形的肢体, 手指融合, 静止不动的画面, 杂乱的背景, 三条腿, 背景人很多, 倒着走,'
        if eff_pos and trig_extra and (trig_extra.lower() not in eff_pos.lower()):
            eff_pos = f'{trig_extra}, {eff_pos}'.strip(', ')
        if has_orc_tusks_03 and eff_pos and ('tusk' not in eff_pos[:320].lower()) and morph_03['feat_desc']:
            eff_pos = f"Featuring {morph_03['feat_desc']}, {eff_pos}"
        (is_pony_mode, is_illustrious_mode, is_sdxl_base_mode, is_sdxl_any_mode) = _classify_image_unet_architecture(unet_name, clip_type)
        resolved_arch_03 = 'illustrious' if is_illustrious_mode else ('pony' if is_pony_mode else ('sdxl' if is_sdxl_any_mode else 'krea2'))
        is_baked_krea_turbo = (not is_sdxl_any_mode) and _is_baked_krea2_turbo_unet(unet_name)
        is_baked_sdxl_turbo = bool(is_sdxl_any_mode and _is_baked_krea2_turbo_unet(unet_name))
        if is_sdxl_any_mode and turbo_acceleration_lora_LOCKED and turbo_acceleration_lora_LOCKED != 'None':
            t_low_03 = str(turbo_acceleration_lora_LOCKED).lower()
            if any((dk in t_low_03 for dk in ('krea', 'flux', 'qwen', 'snofs'))):
                print(f'[EZ-03-PONY/ILXL] 🛡️ Kopplar ur Krea2/Flux Turbo-LoRA "{os.path.basename(str(turbo_acceleration_lora_LOCKED))}" vid körning av {resolved_arch_03.upper()} (använd SDXL Single-Stage eller dmd2_sdxl_4step_lora).')
                turbo_acceleration_lora_LOCKED = 'None'
                turbo_strength = 0.0
        if is_baked_krea_turbo:
            if turbo_acceleration_lora_LOCKED and turbo_acceleration_lora_LOCKED != 'None' and (abs(float(turbo_strength)) > 1e-05):
                print(f'[EZ-03-TURBO-GUARD] ⚡ Bild-UNet "{os.path.basename(str(unet_name))}" har redan inbakad Turbo-destillering -> kopplar ur extern Stage-2 Turbo-LoRA ({float(turbo_strength):.2f} -> 0.00) och låser sampling_mode="turbo_fixed".')
            turbo_acceleration_lora_LOCKED = 'None'
            turbo_strength = 0.0
            if str(sampling_mode or '').strip().lower() != 'bypass':
                sampling_mode = 'turbo_fixed'
        if is_pony_mode and eff_pos and ('score_9' not in eff_pos.lower()):
            pony_2d_tag = 'source_anime, anime coloring, flat color, cel shading, ' if style_low in ('anime', 'cartoonish') else ''
            eff_pos = f'score_9, score_8_up, score_7_up, {pony_2d_tag}{eff_pos}'
        elif is_illustrious_mode and eff_pos and ('masterpiece' not in eff_pos.lower() and 'absurdres' not in eff_pos.lower()):
            ilxl_2d_tag = 'anime coloring, anime screencap, cel shading, flat color, crisp lineart, ' if style_low in ('anime', 'cartoonish') else ''
            eff_pos = f'masterpiece, best quality, newest, absurdres, highres, {ilxl_2d_tag}{eff_pos}'
        elif is_sdxl_base_mode and eff_pos and ('best quality' not in eff_pos.lower() and 'ultra-detailed' not in eff_pos.lower()):
            for stale_p in ('score_9,', 'score_8_up,', 'score_7_up,', 'score_9', 'score_8_up', 'score_7_up'):
                eff_pos = eff_pos.replace(stale_p, '').strip(', ')
            eff_pos = f'masterpiece, best quality, ultra-detailed, sharp focus, {eff_pos}'
        elif not is_pony_mode and not is_illustrious_mode and not is_sdxl_base_mode and eff_pos:
            for stale_tag in ('score_9,', 'score_8_up,', 'score_7_up,', 'score_9', 'score_8_up', 'score_7_up', 'source_pony,', 'absurdres,'):
                if stale_tag in eff_pos:
                    eff_pos = eff_pos.replace(stale_tag, '').strip(', ')
            eff_pos = re.sub(r'\(([^():\n]+):\s*\d+(?:\.\d+)?\)', r'\1', eff_pos)
        if (is_pony_mode or is_illustrious_mode) and eff_pos:
            eff_pos = re.sub(r'(?<!\\)\(([a-zA-Z0-9_\s\-]{2,28})(?<!\\)\)(?!\s*:)', lambda m: m.group(0) if ':' in m.group(1) else f'\\({m.group(1)}\\)', eff_pos)
        if not is_nsfw and 'safe-for-work' not in eff_pos.lower() and 'fully clothed' not in eff_pos.lower():
            eff_pos = f'{eff_pos} Strictly Safe-For-Work (SFW), subject is wearing complete, modest, full-coverage clothing.'.strip()
        eff_neg = str(negative_prompt or '').strip() or str(bus.get('adaptive_negative_prompt', '') or default_core_neg)
        if not has_orc_tusks_03 and eff_neg:
            eff_neg = re.sub(r'(?i)\([^()]*missing\s+tusks[^()]*\),\s*', '', eff_neg).strip()
        eff_neg = re.sub(r'(?i)\bmale\s+orc\s+face\b', 'masculine male jaw', eff_neg)
        if age_prof_03['neg_tokens'][:24].lower() not in eff_neg.lower():
            eff_neg = f"{age_prof_03['neg_tokens']}, {eff_neg}"
        if is_pony_mode and 'score_4' not in eff_neg.lower():
            eff_neg = f'score_4, score_5, score_6, source_pony, lowres, bad anatomy, bad hands, {eff_neg}'
        elif is_illustrious_mode and 'worst quality' not in eff_neg.lower():
            ilxl_neg_2d = '3d, realistic, photorealistic, semi-realistic, cgi, smooth 3d shading, ' if style_low in ('anime', 'cartoonish') else ''
            eff_neg = f'worst quality, low quality, old, early, lowres, bad anatomy, bad hands, {ilxl_neg_2d}{eff_neg}'
        elif is_sdxl_base_mode and 'worst quality' not in eff_neg.lower():
            eff_neg = f'worst quality, low quality, blurry, bad anatomy, deformed hands, extra digits, {eff_neg}'
        old_wrinkled_tok = ', old wrinkled face' if age_years <= 37 else ''
        tusk_neg_tok = f", {morph_03['neg_guard'].strip('()').split(':')[0]}" if (has_orc_tusks_03 and morph_03['neg_guard']) else ''
        eff_neg_head_03 = eff_neg[:260].lower()
        if style_low in ('cartoonish', 'anime') and 'photorealistic' not in eff_neg.lower():
            eff_neg = f'(photorealistic, semi-realistic, 2.5d, 3d shading, soft airbrushed gradients, glossy 3d skin, raw photo, live-action photograph, 3d render, unreal engine, rotoscoped photo filter, muddy brown colors, double mouth, smudged lips, realistic 3d nose bridge, realistic skin pores, subsurface scattering, 35mm film{tusk_neg_tok}:1.90), {eff_neg}'
        elif style_low in ('realism', 'cinematic-film-35mm', 'dark-fantasy-real', 'dark-fantasy', 'original') and not any(tok in eff_neg_head_03 for tok in ('semi-realistic', '2d illustration', '2d digital painting')):
            eff_neg = f'(2d digital painting, 2d painted illustration, fantasy book cover, wlop style, semi-realistic, stylized 3d, 3d cgi, video game render, concept art, fantasy illustration, flat painted background, airbrushed skin, plastic doll skin, smooth porcelain skin, painted hair ribbons, clumped stylized hair{tusk_neg_tok}{old_wrinkled_tok}, anime, manga, cel-shading, cartoon, cartoonish, 2d illustration, lineart:1.90), {eff_neg}'
        elif style_low == 'dark-fantasy-cgi' and not any(tok in eff_neg_head_03 for tok in ('fantasy book cover', '2d digital painting', '2d illustration')):
            eff_neg = f'(2d digital painting, 2d painted illustration, flat 2d, fantasy book cover, concept art, oil painting, wlop style, painterly brushwork, flat canvas, painted 2d background, raw candid documentary photo{tusk_neg_tok}{old_wrinkled_tok}, anime, manga, cel-shading, cartoon, cartoonish, 2d illustration, lineart:1.88), {eff_neg}'
        elif style_low == 'semi-real' and 'raw candid photograph' not in eff_neg.lower():
            eff_neg = f'(raw candid photograph, documentary photo, unretouched skin pores, harsh camera flash, grainy CCTV{tusk_neg_tok}{old_wrinkled_tok}, flat 2d anime, cel-shading, cartoon lineart:1.75), {eff_neg}'
        elif style_low == 'unreal-engine-5' and 'flat shading' not in eff_neg.lower():
            eff_neg = f'(anime, manga, cel-shading, 2d illustration, cartoon, lineart, flat shading{old_wrinkled_tok}{tusk_neg_tok}:1.75), {eff_neg}'
        elif has_orc_tusks_03 and morph_03['neg_guard'] and 'missing tusks' not in eff_neg.lower():
            eff_neg = f"{morph_03['neg_guard']}, {eff_neg}"
        import hashlib
        stable_pos_sig = str(bus.get('krea2_image_config_sig') or eff_pos)
        bypass_krea_turbo_2d = bool((style_low in ('cartoonish', 'anime')) and (not is_sdxl_any_mode) and (not is_baked_krea_turbo))
        if bypass_krea_turbo_2d and turbo_acceleration_lora_LOCKED and turbo_acceleration_lora_LOCKED != 'None' and (abs(float(turbo_strength)) > 1e-05):
            print(f'[EZ-03-ANIME-TURBO-BYPASS] 🎨 2D Anime/Cartoon aktivt på Krea 2 -> Kopplar ur Stage-2 Turbo-LoRA "{os.path.basename(str(turbo_acceleration_lora_LOCKED))}" så Steg 2 kör full CFG & negativ prompt mot 3D-skuggning.')
        eff_turbo_name = 'None' if bypass_krea_turbo_2d else turbo_acceleration_lora_LOCKED
        eff_turbo_str = 0.0 if bypass_krea_turbo_2d else float(turbo_strength)
        loader_sig_raw = json.dumps(['v22_illustrious_sdxl_and_flat_2d_anime', unet_name, clip_name, clip_type, vae_name, int(stop_at_clip_layer), sampling_mode, w, h, style_pairs, eff_turbo_name, round(eff_turbo_str, 4), stable_pos_sig, style_low, int(age_years), bool(has_orc_tusks_03), is_nsfw, bool(is_baked_krea_turbo), resolved_arch_03], ensure_ascii=False)
        loader_03_sig = hashlib.sha256(loader_sig_raw.encode('utf-8')).hexdigest()[:24]
        cached_03 = getattr(EzCinematrixImageLoaderAdapter, '_last_loader_cache', None)
        if isinstance(cached_03, dict) and cached_03.get('sig') == loader_03_sig and cached_03.get('out') is not None:
            (s1_m, s2_m, pos_c, neg_c, vae_obj, clip_obj) = cached_03['out']
        else:
            (s1_m, s2_m, pos_c, neg_c, vae_obj, clip_obj) = load_and_split_image_models_with_loras(unet_name=unet_name, clip_name=clip_name, clip_type_str=clip_type, vae_name=vae_name, stop_at_clip_layer=stop_at_clip_layer, sampling_mode=sampling_mode, width=w, height=h, style_loras=style_pairs, turbo_lora_name=eff_turbo_name, turbo_strength=eff_turbo_str, positive_text=eff_pos, negative_text=eff_neg, tier_profile=tier_prof)
            for m_obj in (s1_m, s2_m):
                if m_obj is not None:
                    setattr(m_obj, '_ez_baked_in_turbo', bool(is_baked_krea_turbo))
                    setattr(m_obj, '_ez_baked_sdxl_turbo', bool(is_baked_sdxl_turbo))
                    setattr(m_obj, '_ez_image_arch', resolved_arch_03)
                    setattr(m_obj, '_ez_raw_style_loras', list(unscaled_style_pairs))
                    setattr(m_obj, '_ez_active_image_unet', str(unet_name or ''))
                    setattr(m_obj, '_ez_active_style_loras', list(style_pairs))
                    setattr(m_obj, '_ez_turbo_spec', (turbo_acceleration_lora_LOCKED, float(turbo_strength), 'bypass' if is_sdxl_any_mode else sampling_mode, int(w), int(h), bool(is_sdxl_any_mode)))
                    setattr(m_obj, '_ez_applied_style_low', style_low)
                    setattr(m_obj, '_ez_applied_style_age_key', f'{style_low}:{age_years}:{int(bool(has_orc_tusks_03))}')
            EzCinematrixImageLoaderAdapter._last_loader_cache = {'sig': loader_03_sig, 'out': (s1_m, s2_m, pos_c, neg_c, vae_obj, clip_obj)}
        sdxl_dmd2_flag = bool(is_baked_sdxl_turbo or getattr(s1_m, '_ez_sdxl_dmd2_active', False))
        eff_active_turbo_bus = eff_turbo_name if (not is_sdxl_any_mode or sdxl_dmd2_flag) else 'None'
        bus.update({'active_image_unet': unet_name, 'active_image_arch': resolved_arch_03, 'sdxl_dmd2_active': sdxl_dmd2_flag, 'active_turbo_lora': eff_active_turbo_bus, 'baked_in_image_turbo': bool(is_baked_krea_turbo), 'active_style_loras': style_pairs, 'style_target': style_low, 'image_trigger_words': trig_extra, 'image_clip_obj': clip_obj, 'krea2_loader_03_sig': loader_03_sig, 'subject_1_age': age_prof_03['age_label'], 'subject_1_age_num': age_years, 'pre_encoded_pos_cond': pos_c, 'pre_encoded_neg_cond': neg_c, 'pre_encoded_pos_str': eff_pos, 'pre_encoded_neg_str': eff_neg})
        return (s1_m, s2_m, pos_c, neg_c, vae_obj, clip_obj, bus)
