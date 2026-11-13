# -*- coding: utf-8 -*-

import re
import math
import gc
import torch
import comfy.utils
import comfy.model_management

MASTER_DURATION_PRESETS = ['5-second', '10-second', '15-second', '20-second', '25-second', '30-second', '45-second', '60-second']
MOTION_PHYSICS_MODES = [
    'auto_from_style_and_audio (Auto från Stil & Ljud)',
    'natural_organic (Naturlig Biologisk Fysik & Tyngd)',
    'expressive_vocal_mocap (Musikvideo & Stark Lip-Sync)',
    'stylized_2d_sakuga (Anime / Cartoon "On-Twos" Snap)',
    'hyper_kinetic_unnatural (Onaturlig / Explosiv / Creature Motion)',
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
TEMPORAL_WINDOW_HORIZON_MODES = [
    'auto_pro_focus_adaptive (PRO Dynamisk Fokus-Skarv — Låser Fönstergräns & Karaktärs-LoRA när Ansiktet är i Fokus)',
    '5s_precision_anchor (5s Fast Intervall — 124r / 37t — Tät Anatomilåsning & 4 Akter/20s)',
    '10s_native_long_take (10s Fast Intervall — 243r / 72t — Native Long-Take & Färre Skarvar)',
]


def resolve_effective_window_horizon_seconds(
    temporal_window_horizon: str = '',
    video_arch: str = 'minimax_h3',
    video_width: int = 768,
    video_height: int = 512,
    duration_seconds: float = 20.0,
    timeline_prompt: str = '',
    subject_stance_posture: str = '',
    body_choreography_preset: str = '',
    camera_trajectory_arc: str = '',
    is_vocal_scene: bool = False,
    is_licensed: bool = True,
) -> float:
    mode_low = str(temporal_window_horizon or '').strip().lower()
    if mode_low.startswith(('5s', '5_sec', '5-sec')):
        return 5.0
    if mode_low.startswith(('10s', '10_sec', '10-sec')):
        return 10.0 if str(video_arch or '').lower() == 'minimax_h3' else 5.0
    if str(video_arch or '').lower() != 'minimax_h3':
        return 5.0
    dur_val = float(duration_seconds or 20.0)
    if dur_val <= 6.0:
        return max(5.0, dur_val)
    return 5.0


def _apply_3axis_window_directives_to_acts(acts: list, subject_stance_posture: str = '', body_choreography_preset: str = '', camera_trajectory_arc: str = '') -> list:
    if not isinstance(acts, list) or not acts:
        return acts
    st_low = str(subject_stance_posture or '').strip().lower()
    ch_low = str(body_choreography_preset or '').strip().lower()
    arc_low = str(camera_trajectory_arc or '').strip().lower()
    if st_low.startswith(('auto', '')) and ch_low.startswith(('auto', '')) and arc_low.startswith(('follow_02', 'auto', '')):
        return acts
    n_wins = len(acts)
    out = []
    for (idx, a_txt) in enumerate(acts):
        cur_act = str(a_txt or '')
        w_tags = []
        if arc_low.startswith('outro_track_to_follow'):
            if idx < max(1, n_wins - 1):
                w_tags.append('Front-facing backward-tracking dolly retreating ahead of the subject with 100% clear facial visibility')
            else:
                w_tags.append('Smooth 180-degree camera orbit transitioning into a dynamic rear follow-cam tracking behind the subject moving forward into the horizon')
        elif arc_low.startswith('backward_track_'):
            w_tags.append('Smooth backward-tracking camera retreating ahead of the subject maintaining 100% front-facing facial visibility')
        elif arc_low.startswith('crane_ascent'):
            if idx == 0:
                w_tags.append('Street-level tracking camera establishing the subject')
            elif idx < n_wins - 1:
                w_tags.append('Ascending cinema crane camera rising smoothly above street level')
            else:
                w_tags.append('High-altitude aerial drone/crane perspective overlooking the expansive cityscape')
        if st_low.startswith('story_vehicle'):
            if idx == 0:
                w_tags.append('Act 1 street-level setup outside the vehicle transitioning from the initial posture of Frame 0 (<Picture 1>)')
            elif idx < n_wins - 1:
                w_tags.append('Act 2 seated inside the vehicle/cockpit interior')
            else:
                w_tags.append('Act 3 high-velocity aerial/vehicle motion sequence')
        elif st_low.startswith('standing_upright'):
            if idx == 0:
                w_tags.append('Posture Transition: Starting from the initial posture of Frame 0 (<Picture 1>), the subject smoothly rises or transitions into a balanced, grounded upright standing posture facing the camera')
            else:
                w_tags.append('Posture Lock: Having transitioned into the target posture, the subject remains standing tall and upright in a grounded full-body stance')
        elif st_low.startswith('kneeling_crouching'):
            if idx == 0:
                w_tags.append('Posture Transition: Starting from the initial posture of Frame 0 (<Picture 1>), the subject smoothly lowers and transitions down onto their knees into a grounded kneeling and crouching posture on the ground facing the camera')
            else:
                cur_act = re.sub(r'(?i)\b(?:standing\s+in\s+a\s+wide(?:\s*,\s*grounded)?\s+combat\s+stance|stands?\s+tall\s+and\s+upright|maintains?\s+her\s+grounded\s+stance|staying\s+upright\s+in\s+her\s+grounded\s+raised-leg\s+stance)\b', 'kneeling low on her knees in a grounded crouching posture on the ground', cur_act)
                w_tags.append('Posture Lock: Having transitioned into the target posture, the subject remains kneeling low on their knees in a grounded crouching posture facing the camera')
        elif st_low.startswith('sitting_'):
            if idx == 0:
                w_tags.append('Posture Transition: Starting from the initial posture of Frame 0 (<Picture 1>), the subject smoothly settles and transitions into a comfortable seated posture')
            else:
                w_tags.append('Posture Lock: Having transitioned into the target posture, the subject remains seated comfortably with natural upper-body posture')
        elif st_low.startswith('reclining_'):
            if idx == 0:
                w_tags.append('Posture Transition: Starting from the initial posture of Frame 0 (<Picture 1>), the subject smoothly leans back and transitions into a relaxed reclining/lounging posture')
            else:
                w_tags.append('Posture Lock: Having transitioned into the target posture, the subject remains reclining in a relaxed lounging posture')
        elif st_low.startswith('lying_'):
            if idx == 0:
                w_tags.append('Posture Transition: Starting from the initial posture of Frame 0 (<Picture 1>), the subject smoothly lowers down and transitions into a horizontal lying posture')
            else:
                w_tags.append('Posture Lock: Having transitioned into the target posture, the subject remains lying down in a horizontal posture')
        elif st_low.startswith(('standing_social', 'epic_battlefield')):
            if idx == 0:
                w_tags.append('Posture Transition: Starting from the initial posture of Frame 0 (<Picture 1>), the primary subject smoothly transitions into a poised foreground standing stance')
            else:
                w_tags.append('Posture Lock: Having transitioned into the target posture, the primary subject maintains a poised foreground standing stance')
        if ch_low.startswith('dance_sensual_club'):
            w_tags.append('Choreography: Sensual club dance with fluid body-rolls, rhythmic hip-sway, and expressive torso articulation')
        elif ch_low.startswith('dance_music_video'):
            w_tags.append('Choreography: Beat-synchronized music-video dance groove with rhythmic shoulder and hip motion')
        if w_tags:
            prefix = ' | '.join(w_tags)
            if '[Shot 1]\n' in cur_act:
                cur_act = cur_act.replace('[Shot 1]\n', f'[Shot 1]\n[{prefix}] ', 1)
            else:
                cur_act = f'[{prefix}] {cur_act}'.strip()
        out.append(cur_act)
    return out

KINEMATIC_MOTION_PROTOTYPES = {
    'natural_organic': {
        'pos': 'Fluid natural human biomechanics, realistic physical weight and momentum, smooth organic joint articulation, natural micro-breathing, grounded center of gravity without temporal jitter.',
        'anti': 'jerky unnatural movement, robotic twitching, floating weightless limbs, temporal flickering, morphing body mass, chaotic frame-to-frame distortion.',
        'alpha': 0.22,
        'token_prefix_len': 14,
    },
    'expressive_vocal_mocap': {
        'pos': 'Expressive on-camera musical performance, phoneme-accurate jaw and lip articulation, dynamic facial micro-expressions, beat-synchronized shoulder and torso groove locked to the rhythm.',
        'anti': 'static frozen mouth, ventriloquist dummy jaw, out-of-sync lip movement, stiff lifeless posture, closed mouth during vocals.',
        'alpha': 0.26,
        'token_prefix_len': 16,
    },
    'stylized_2d_sakuga': {
        'pos': 'Dynamic 2D keyframe animation kinematics, crisp expressive pose-to-pose sakuga timing, snappy anime mouth and eye articulation, clean cel-animated motion arcs.',
        'anti': 'uncanny 3d motion interpolation, floaty soap-opera effect, blurry in-between frames, muddy 3d cg movement.',
        'alpha': 0.25,
        'token_prefix_len': 14,
    },
    'hyper_kinetic_unnatural': {
        'pos': 'Hyper-kinetic explosive physical motion, intense high-velocity impact dynamics, visceral creature and combat momentum, extreme dynamic range of motion.',
        'anti': 'static pose, sluggish slow movement, stiff motionless figure, frozen frame.',
        'alpha': 0.28,
        'token_prefix_len': 14,
    },
}


def resolve_effective_motion_physics_mode(motion_physics_mode: str, style_target: str = '', is_vocal_perf: bool = False) -> str:
    m_low = str(motion_physics_mode or '').strip().lower()
    s_low = str(style_target or '').strip().lower()
    if m_low.startswith('stylized_2d'):
        return 'stylized_2d_sakuga'
    if m_low.startswith('hyper_kinetic'):
        return 'hyper_kinetic_unnatural'
    if m_low.startswith('expressive_vocal'):
        return 'expressive_vocal_mocap'
    if s_low in ('anime', 'cartoonish'):
        return 'stylized_2d_sakuga'
    if is_vocal_perf:
        return 'expressive_vocal_mocap'
    if m_low.startswith('natural_organic'):
        return 'natural_organic'
    return 'natural_organic'


_DIRECTOR_EROTIC_REGEX = re.compile(
    r'(?i)\b(?:nude|nudity|naked|bottomless|unclothed|undressed|pussy|vagina|labia|vulva|clit(?:oris)?|penis|dick|cock|erection|phallus|testicles?|anus|anal|genitals?|genitalia|sex|sexual|intercourse|penetration|orgasm|climax|cum(?:ming)?|semen|sperm|milky\s+liquid|spread\s+legs)\b'
)


def _resolve_content_rating_tier(content_rating_mode: str, timeline_prompt: str = '') -> str:
    m_low = str(content_rating_mode or '').strip().lower()
    if m_low.startswith('sfw'):
        return 'sfw'
    if m_low.startswith('uncensored'):
        return 'uncensored_action'
    if 'explicit' in m_low or 'erotic' in m_low or m_low.startswith('nsfw'):
        return 'nsfw_explicit'
    return 'uncensored_action'


def _scrub_unrequested_genital_hallucinations(text_in: str, user_scene_input: str = '') -> str:
    s = str(text_in or '')
    u_low = str(user_scene_input or '').lower()
    if any(k in u_low for k in ('vulva', 'vagina', 'labia', 'pussy', 'clit', 'penis', 'cock', 'dick', 'genital', 'nude', 'naked', 'nip slip', 'nipple', 'panties', 'bottomless', 'crotchless')):
        return s.strip()
    s = re.sub(
        r'(?i)\bthat\s+(?:partially\s+|barely\s+)?(?:occludes|covers|hides|conceals|exposes|reveals)\s+(?:her|his|their)\s+[^.,;]*',
        'resting securely in place',
        s,
    )
    s = re.sub(
        r'(?i)\b(?:briefly\s+|partially\s+|fully\s+)?(?:exposing|revealing|showing|baring)\s+(?:her|his|their)\s+(?:bare\s+|wet\s+|glistening\s+|shaven\s+|anatomical\s+)?(?:vulva|vagina|labia|pussy|clit(?:oris)?|genitals?|genitalia|groin|pelvis|anus|penis|cock|dick)\b',
        'keeping her attire securely in place',
        s,
    )
    s = re.sub(
        r'(?i)\b(?:vulva|vagina|labia(?:\s+majora|\s+minora)?|pussy|clit(?:oris)?|penis|cock|dick|erection|testicles?|anus|anal|genitals?|genitalia|bottomless|crotchless|intercourse|penetration|orgasm|climax|cum|semen|sperm|milky\s+liquid)\b',
        'intact attire coverage',
        s,
    )
    return re.sub(r'(?:intact attire coverage[\s,]*){2,}', 'intact attire coverage ', s).strip()


def _scrub_sfx_vocal_triggers(text_in: str) -> str:
    s = str(text_in or '')
    has_tusk_ctx = bool(re.search(r'(?i)\b(?:orc|tusks?|half-orc)\b', s))
    s = re.sub(
        r'(?i)\b(?:starts?\s+praying\s+to|praying\s+to|prays?\s+to)\b',
        'stands tall and upright holding in silent reverence',
        s,
    )
    s = re.sub(
        r'(?i)\b(?:praying(?:\s+aloud|\s+fervently|\s+silently)?|prays?|prayer|chanting|chants?|intoning|reciting|uttering|muttering|speaking|speaks?|spoken\s+words?|calling\s+out|invoking)\b',
        'holding a silent composed posture',
        s,
    )
    s = re.sub(
        r'(?i)\b(?:with\s+)?(?:heavy\s+breathing|breathing\s+heavily|ragged\s+breathing|labored\s+breathing|audible\s+breathing|panting(?:\s+heavily)?|gasping(?:\s+for\s+air)?|groaning|groans|grunting|grunts|moaning|moans|sighing|vocal\s+sighs|sighs|roaring|roars|screaming|screams|shouting|shouts|yelling|battle\s+cry|war\s+cry|mumbling|talking|whispering|whispers)\b',
        'silent focused intensity and natural ambient foley',
        s,
    )
    mouth_repl = (
        'fierce silent expression with two sharp protruding white lower-jaw orc tusks clearly visible outside her lips'
        if has_tusk_ctx else
        'firmly closed mouth and fierce silent expression'
    )
    s = re.sub(
        r'(?i)\b(?:parted\s+lips|open\s+mouth|mouth\s+open(?:\s+wide)?|jaw\s+dropped|lips\s+parted|lips\s+moving)\b',
        mouth_repl,
        s,
    )
    return s


def project_video_kinematic_conditioning(
    video_clip,
    positive_cond,
    negative_cond,
    resolved_physics_mode: str = 'natural_organic',
    is_nsfw: bool = True,
    video_arch: str = 'minimax_h3',
    motion_physics_mode: str = None,
    motion_strength: float = 0.65,
):
    if not isinstance(positive_cond, list) or len(positive_cond) == 0:
        return (positive_cond, negative_cond)
    try:
        import torch.nn.functional as F
        eff_mode = str(motion_physics_mode or resolved_physics_mode or 'natural_organic').strip()
        if eff_mode not in KINEMATIC_MOTION_PROTOTYPES:
            eff_mode = resolve_effective_motion_physics_mode(eff_mode)
        proto = KINEMATIC_MOTION_PROTOTYPES.get(eff_mode, KINEMATIC_MOTION_PROTOTYPES['natural_organic'])
        alpha = float(proto.get('alpha', 0.22)) * max(0.15, min(1.35, float(motion_strength or 0.65) / 0.65))
        prefix_len = max(4, int(proto.get('token_prefix_len', 14)))
        t0 = positive_cond[0][0] if isinstance(positive_cond[0], (list, tuple)) and len(positive_cond[0]) >= 1 else None
        if not isinstance(t0, torch.Tensor) or t0.ndim != 3 or int(t0.shape[1]) < 2 or video_clip is None:
            return (positive_cond, negative_cond)
        real_clip = getattr(video_clip, '_real', video_clip)
        cache_dict = getattr(real_clip, '_ez_kinematic_proto_cache', None)
        if not isinstance(cache_dict, dict):
            cache_dict = {}
            try:
                setattr(real_clip, '_ez_kinematic_proto_cache', cache_dict)
            except Exception:
                pass
        dim_d = int(t0.shape[-1])
        ckey = (eff_mode, dim_d)
        dir_vec = cache_dict.get(ckey)
        if not isinstance(dir_vec, torch.Tensor):
            pos_tok = real_clip.tokenize(str(proto['pos']))
            anti_tok = real_clip.tokenize(str(proto['anti']))
            pos_enc = real_clip.encode_from_tokens_scheduled(pos_tok)
            anti_enc = real_clip.encode_from_tokens_scheduled(anti_tok)
            p_t = pos_enc[0][0].detach().cpu().float() if isinstance(pos_enc, list) and len(pos_enc) > 0 and isinstance(pos_enc[0][0], torch.Tensor) else None
            a_t = anti_enc[0][0].detach().cpu().float() if isinstance(anti_enc, list) and len(anti_enc) > 0 and isinstance(anti_enc[0][0], torch.Tensor) else None
            if isinstance(p_t, torch.Tensor) and isinstance(a_t, torch.Tensor) and p_t.shape[-1] == dim_d and a_t.shape[-1] == dim_d:
                raw_diff = p_t.mean(dim=1, keepdim=True) - a_t.mean(dim=1, keepdim=True)
                dir_vec = F.normalize(raw_diff, p=2.0, dim=-1).detach().cpu()
                cache_dict[ckey] = dir_vec
        if not isinstance(dir_vec, torch.Tensor) or str(video_arch or '').lower() == 'minimax_h3':
            return (positive_cond, negative_cond)
        out_pos = []
        for item in positive_cond:
            if isinstance(item, (list, tuple)) and len(item) >= 2 and isinstance(item[0], torch.Tensor) and item[0].ndim == 3 and int(item[0].shape[-1]) == dim_d:
                ct = item[0].clone()
                plen = min(int(ct.shape[1]), prefix_len)
                sub = ct[:, :plen, :].float()
                orig_norm = torch.norm(sub, p=2.0, dim=-1, keepdim=True).clamp(min=1e-05)
                dv = dir_vec.to(device=sub.device, dtype=torch.float32)
                shifted = F.normalize(sub + dv * (orig_norm * alpha * 0.18), p=2.0, dim=-1) * orig_norm
                ct[:, :plen, :] = shifted.to(dtype=ct.dtype)
                out_pos.append([ct, item[1]])
            else:
                out_pos.append(item)
        return (out_pos, negative_cond)
    except Exception:
        return (positive_cond, negative_cond)


def _synthesize_start_mid_end_keyframes(
    start_kf: torch.Tensor,
    reference_motion_video: torch.Tensor = None,
    anatomical_zones: dict = None,
    target_w: int = 768,
    target_h: int = 512,
    mid_kf_opt: torch.Tensor = None,
    end_kf_opt: torch.Tensor = None,
    allow_camera_movement: bool = False,
) -> list:
    if not isinstance(start_kf, torch.Tensor) or start_kf.ndim != 4 or float(start_kf.detach().abs().max().item()) <= 1e-04:
        return []
    import torch.nn.functional as F
    w = max(64, int(target_w))
    h = max(64, int(target_h))

    def _align_to_start(cand_t: torch.Tensor, blend_w: float = 0.25) -> torch.Tensor:
        nchw = cand_t[-1:, :, :, :3].detach().cpu().float().movedim(-1, 1)
        if int(nchw.shape[2]) != h or int(nchw.shape[3]) != w:
            nchw = comfy.utils.common_upscale(nchw, w, h, 'lanczos', 'center')
        bhwc = torch.clamp(nchw.movedim(1, -1).contiguous(), 0.0, 1.0)
        s_mean = s0.mean(dim=(1, 2), keepdim=True)
        s_std = torch.clamp(s0.std(dim=(1, 2), keepdim=True), min=1e-04)
        c_mean = bhwc.mean(dim=(1, 2), keepdim=True)
        c_std = torch.clamp(bhwc.std(dim=(1, 2), keepdim=True), min=1e-04)
        relit = torch.clamp((bhwc - c_mean) * (s_std / c_std) + s_mean, 0.0, 1.0)
        return torch.clamp(torch.lerp(s0, relit, max(0.05, min(0.85, float(blend_w)))), 0.0, 1.0)

    s0_nchw = start_kf[-1:, :, :, :3].detach().cpu().float().movedim(-1, 1)
    if int(s0_nchw.shape[2]) != h or int(s0_nchw.shape[3]) != w:
        s0_nchw = comfy.utils.common_upscale(s0_nchw, w, h, 'lanczos', 'center')
    s0 = torch.clamp(s0_nchw.movedim(1, -1).contiguous(), 0.0, 1.0)

    if isinstance(mid_kf_opt, torch.Tensor) and mid_kf_opt.ndim == 4 and float(mid_kf_opt.detach().abs().max().item()) > 1e-04:
        mid_kf = _align_to_start(mid_kf_opt, blend_w=0.65)
    elif isinstance(reference_motion_video, torch.Tensor) and reference_motion_video.ndim == 4 and int(reference_motion_video.shape[0]) >= 3:
        mid_idx = int(reference_motion_video.shape[0]) // 2
        mid_kf = _align_to_start(reference_motion_video[mid_idx:mid_idx + 1], blend_w=0.28)
    elif not allow_camera_movement:
        mid_kf = s0.clone()
    else:
        rig = anatomical_zones.get('skeletal_rig', {}) if isinstance(anatomical_zones, dict) and isinstance(anatomical_zones.get('skeletal_rig'), dict) else {}
        t_box = rig.get('torso_box_norm', (0.24, 0.18, 0.68, 0.82))
        yy = torch.linspace(-1.0, 1.0, steps=h, dtype=torch.float32).view(1, h, 1, 1).expand(1, h, w, 1)
        xx = torch.linspace(-1.0, 1.0, steps=w, dtype=torch.float32).view(1, 1, w, 1).expand(1, h, w, 1)
        cy = (float(t_box[0]) + float(t_box[2])) - 1.0
        cx = (float(t_box[1]) + float(t_box[3])) - 1.0
        ry = max(0.18, float(t_box[2]) - float(t_box[0]))
        rx = max(0.18, float(t_box[3]) - float(t_box[1]))
        torso_bell = torch.exp(-(((yy - cy) / ry) ** 2 + ((xx - cx) / rx) ** 2))
        dy = -0.0085 * torso_bell
        dx = 0.0045 * torso_bell * (xx - cx)
        grid = torch.cat([xx + dx, yy + dy], dim=-1)
        warped_nchw = F.grid_sample(s0.movedim(-1, 1), grid, mode='bilinear', padding_mode='border', align_corners=True)
        mid_kf = torch.clamp(warped_nchw.movedim(1, -1).contiguous(), 0.0, 1.0)

    if isinstance(end_kf_opt, torch.Tensor) and end_kf_opt.ndim == 4 and float(end_kf_opt.detach().abs().max().item()) > 1e-04:
        end_kf = _align_to_start(end_kf_opt, blend_w=0.65)
    elif isinstance(reference_motion_video, torch.Tensor) and reference_motion_video.ndim == 4 and int(reference_motion_video.shape[0]) >= 3:
        end_kf = _align_to_start(reference_motion_video[-1:], blend_w=0.22)
    elif not allow_camera_movement:
        end_kf = s0.clone()
    else:
        end_kf = torch.clamp(torch.lerp(s0, mid_kf, 0.25), 0.0, 1.0)

    return [s0, mid_kf, end_kf]


def _resolve_window_fl2va_start_mid_end(anchors: list, seg_idx: int, total_wins: int, handoff_img: torch.Tensor = None) -> tuple:
    valid_a = [a for a in (anchors or []) if isinstance(a, torch.Tensor) and a.ndim == 4]
    if not valid_a:
        return (handoff_img, handoff_img, None)
    s_kf = valid_a[0]
    m_kf = valid_a[1] if len(valid_a) >= 2 else s_kf
    e_kf = valid_a[2] if len(valid_a) >= 3 else s_kf
    start_out = handoff_img if isinstance(handoff_img, torch.Tensor) and handoff_img.ndim == 4 else s_kf
    n_wins = max(1, int(total_wins))
    idx = max(0, min(n_wins - 1, int(seg_idx)))
    if n_wins == 1:
        return (start_out, m_kf, e_kf)
    if n_wins == 2:
        if idx == 0:
            return (start_out, torch.lerp(s_kf, m_kf, 0.5), m_kf)
        return (start_out, torch.lerp(m_kf, e_kf, 0.5), e_kf)
    if idx == 0:
        return (start_out, torch.lerp(s_kf, m_kf, 0.5), m_kf)
    if idx < n_wins - 1:
        end_mid = torch.lerp(m_kf, e_kf, 0.60)
        return (start_out, m_kf, end_mid)
    return (start_out, torch.lerp(m_kf, e_kf, 0.80), e_kf)


def _extract_latent_motion_capture_deltas(reference_motion_video: torch.Tensor, video_vae, target_w: int, target_h: int, target_latent_t: int, tile_sz: int = 512, target_first_frame: torch.Tensor = None, slot5_focus_mode: str = ''):
    if not isinstance(reference_motion_video, torch.Tensor) or reference_motion_video.ndim != 4 or reference_motion_video.shape[0] < 2 or video_vae is None or int(target_latent_t) < 2:
        return None
    try:
        import torch.nn.functional as F
        from .engine_ez_04_cinematrix_krea2_sampler import _gaussian_blur_2d, compute_downscaled_latent_anatomy_zones
        s5_mode_low = str(slot5_focus_mode or '').strip().lower()
        if 'first_video_frame_only' in s5_mode_low:
            return None
        max_in_frames = min(int(reference_motion_video.shape[0]), max(9, (int(target_latent_t) - 1) * 4 + 1))
        nchw_v = reference_motion_video[:max_in_frames, :, :, :3].movedim(-1, 1)
        resized_v = comfy.utils.common_upscale(nchw_v, int(target_w), int(target_h), 'bilinear', 'center').movedim(1, -1).detach().cpu().float()
        try:
            enc_v = video_vae.encode(resized_v).detach().cpu().float()
        except Exception:
            enc_v = video_vae.encode_tiled(resized_v, tile_x=int(tile_sz), tile_y=int(tile_sz)).detach().cpu().float()
        if enc_v.ndim == 4:
            enc_v = enc_v.unsqueeze(0).movedim(1, 2)
        if enc_v.ndim != 5 or enc_v.shape[2] < 2:
            return None
        if int(enc_v.shape[2]) != int(target_latent_t):
            enc_v = F.interpolate(enc_v, size=(int(target_latent_t), int(enc_v.shape[3]), int(enc_v.shape[4])), mode='trilinear', align_corners=False)
        (b_sz, c_ch, t_len, lh, lw) = enc_v.shape
        px_diff = (resized_v[1:] - resized_v[:-1]).abs().mean(dim=-1, keepdim=True).permute(0, 3, 1, 2)
        px_saliency = F.interpolate(px_diff.unsqueeze(0).permute(0, 2, 1, 3, 4), size=(t_len - 1, lh, lw), mode='trilinear', align_corners=False)
        s_p90 = float(torch.quantile(px_saliency.flatten(), 0.90).item()) if px_saliency.numel() > 16 else 0.1
        motion_gate = torch.clamp(px_saliency / max(1e-04, s_p90), 0.0, 1.0)
        ref_zones = compute_downscaled_latent_anatomy_zones(resized_v[:1], lh, lw)
        if 'facial_and_vocal' in s5_mode_low and isinstance(ref_zones.get('face'), torch.Tensor):
            face_z = ref_zones['face'].view(1, 1, 1, lh, lw)
            mouth_z = ref_zones['mouth'].view(1, 1, 1, lh, lw) if isinstance(ref_zones.get('mouth'), torch.Tensor) else face_z
            head_gate = torch.clamp(face_z * 1.35 + mouth_z * 1.55, 0.0, 1.0)
            motion_gate = torch.clamp(motion_gate * (0.12 + 0.88 * head_gate), 0.0, 1.0)
        elif 'full_body_choreography' in s5_mode_low and isinstance(ref_zones.get('anat_core'), torch.Tensor):
            ref_core = ref_zones['anat_core'].view(1, 1, 1, lh, lw)
            motion_gate = torch.clamp(motion_gate * (0.65 + 0.45 * ref_core), 0.0, 1.0)
        elif isinstance(ref_zones.get('anat_core'), torch.Tensor):
            ref_core = ref_zones['anat_core'].view(1, 1, 1, lh, lw)
            motion_gate = torch.clamp(motion_gate * (0.35 + 0.65 * ref_core), 0.0, 1.0)
        flat_2d = enc_v.permute(0, 2, 1, 3, 4).reshape(b_sz * t_len, c_ch, lh, lw)
        blur_sigma = 0.85 if 'facial_and_vocal' in s5_mode_low else 1.35
        low_2d = _gaussian_blur_2d(flat_2d, blur_sigma).reshape(b_sz, t_len, c_ch, lh, lw).permute(0, 2, 1, 3, 4)
        raw_deltas = (low_2d[:, :, 1:, :, :] - low_2d[:, :, :-1, :, :]) * motion_gate
        if 'full_body_choreography' not in s5_mode_low and isinstance(target_first_frame, torch.Tensor) and isinstance(ref_zones.get('anat_core'), torch.Tensor):
            tgt_zones = compute_downscaled_latent_anatomy_zones(target_first_frame[:1], lh, lw)
            if isinstance(tgt_zones.get('anat_core'), torch.Tensor):
                gy = torch.linspace(0.0, 1.0, steps=lh).view(1, 1, lh, 1)
                gx = torch.linspace(0.0, 1.0, steps=lw).view(1, 1, 1, lw)
                rc = ref_zones['face'] if ('facial_and_vocal' in s5_mode_low and isinstance(ref_zones.get('face'), torch.Tensor)) else ref_zones['anat_core']
                tc = tgt_zones['face'] if ('facial_and_vocal' in s5_mode_low and isinstance(tgt_zones.get('face'), torch.Tensor)) else tgt_zones['anat_core']
                if float(rc.sum().item()) > 1e-03 and float(tc.sum().item()) > 1e-03:
                    ry = float((rc * gy).sum().item() / rc.sum().item())
                    rx = float((rc * gx).sum().item() / rc.sum().item())
                    ty = float((tc * gy).sum().item() / tc.sum().item())
                    tx = float((tc * gx).sum().item() / tc.sum().item())
                    shift_y = int(round((ty - ry) * lh))
                    shift_x = int(round((tx - rx) * lw))
                    if abs(shift_y) >= 1 or abs(shift_x) >= 1:
                        raw_deltas = torch.roll(raw_deltas, shifts=(shift_y, shift_x), dims=(-2, -1))
        d_std = torch.clamp(raw_deltas.std(dim=(-3, -2, -1), keepdim=True), min=1e-04)
        norm_deltas = torch.tanh(raw_deltas / (2.2 * d_std)) * (1.35 * d_std)
        return norm_deltas.detach().cpu()
    except Exception as mocap_err:
        print(f'[EZ-DIRECTOR-06] Reference motion video extraction notice: {mocap_err}')
        return None


def _build_reference_video_audio_packet(reference_video_audio, duration_seconds: float=20.0, frame_rate: float=24.0) -> dict:
    if not isinstance(reference_video_audio, dict) or not isinstance(reference_video_audio.get('waveform'), torch.Tensor):
        return {'active': False}
    try:
        import torch.nn.functional as F
        raw_w = reference_video_audio['waveform'].detach().cpu().float()
        sr_in = max(8000, int(reference_video_audio.get('sample_rate', 32000) or 32000))
        if raw_w.ndim == 1:
            raw_w = raw_w.unsqueeze(0).unsqueeze(0)
        elif raw_w.ndim == 2:
            raw_w = raw_w.unsqueeze(0)
        elif raw_w.ndim > 3:
            raw_w = raw_w.reshape(1, int(raw_w.shape[-2]), int(raw_w.shape[-1]))
        if int(raw_w.shape[1]) > 2 and int(raw_w.shape[-1]) <= 2:
            raw_w = raw_w.transpose(1, 2).contiguous()
        if int(raw_w.shape[1]) == 1:
            raw_w = raw_w.repeat(1, 2, 1)
        elif int(raw_w.shape[1]) > 2:
            raw_w = raw_w[:, :2, :]
        sr_32k = 32000
        if sr_in != sr_32k and int(raw_w.shape[-1]) > 16:
            tgt_len = max(64, int(round(float(raw_w.shape[-1]) * float(sr_32k) / float(sr_in))))
            wave_32k = F.interpolate(raw_w, size=tgt_len, mode='linear', align_corners=False)
        else:
            wave_32k = raw_w
        peak = float(wave_32k.abs().max().item())
        if peak > 1e-05:
            wave_32k = (wave_32k / peak) * min(0.95, max(0.35, peak))
        dur_in_sec = float(wave_32k.shape[-1]) / float(sr_32k)
        eff_dur = max(1.0, float(duration_seconds or dur_in_sec or 20.0))
        need_samples_32k = max(3200, int(round(eff_dur * float(sr_32k))))
        if int(wave_32k.shape[-1]) < need_samples_32k and int(wave_32k.shape[-1]) > 0:
            reps = int(math.ceil(float(need_samples_32k) / float(wave_32k.shape[-1])))
            wave_32k = wave_32k.repeat(1, 1, max(1, reps))[:, :, :need_samples_32k].contiguous()
        elif int(wave_32k.shape[-1]) > need_samples_32k:
            wave_32k = wave_32k[:, :, :need_samples_32k].contiguous()
        dur_in_sec = float(wave_32k.shape[-1]) / float(sr_32k)
        tot_v_frames = max(9, int(round(eff_dur * max(8.0, float(frame_rate or 24.0)))))
        mono = wave_32k.mean(dim=1)
        win_hop = max(64, int(round(float(sr_32k) / max(8.0, float(frame_rate or 24.0)))))
        need_samples = tot_v_frames * win_hop
        if int(mono.shape[-1]) < need_samples:
            mono_pad = F.pad(mono, (0, need_samples - int(mono.shape[-1])))
        else:
            mono_pad = mono[:, :need_samples]
        frames_audio = mono_pad.view(tot_v_frames, win_hop)
        rms_jaw = torch.sqrt(torch.mean(frames_audio ** 2, dim=-1) + 1e-07)
        diff1 = torch.abs(frames_audio[:, 1:] - frames_audio[:, :-1])
        high_sib = torch.mean(diff1, dim=-1)
        smooth_a = F.avg_pool1d(frames_audio.unsqueeze(1), kernel_size=5, stride=1, padding=2).squeeze(1)
        mid_vowel = torch.sqrt(torch.mean((frames_audio - smooth_a * 0.5) ** 2, dim=-1) + 1e-07)
        onset_tr = F.pad(torch.clamp(rms_jaw[1:] - rms_jaw[:-1], min=0.0), (1, 0))
        vis_4d = torch.stack([rms_jaw, mid_vowel, high_sib, onset_tr], dim=0)
        for ch_i in range(4):
            c_max = float(vis_4d[ch_i].max().item())
            if c_max > 1e-05:
                vis_4d[ch_i] = torch.clamp(vis_4d[ch_i] / c_max, 0.0, 1.0)
        return {
            'active': True,
            'is_reference_video_audio': True,
            'wants_lipsync': True,
            'lock_video_duration': False,
            'duration_sec': dur_in_sec,
            'sample_rate_32k': sr_32k,
            'waveform_32k': wave_32k.detach().cpu(),
            'viseme_envelope_4d': vis_4d.detach().cpu(),
            'prompt_injection': '',
        }
    except Exception as ref_aud_err:
        print(f'[EZ-DIRECTOR-06] Reference video audio packet notice: {ref_aud_err}')
        return {'active': False}


def _analyze_pro_voice_and_scenecut_identity_routing(
    reference_motion_video,
    reference_video_audio,
    num_windows: int=1,
    duration_seconds: float=20.0,
    frame_rate: float=24.0,
    is_licensed: bool=True,
    has_second_person_ref: bool=False,
) -> dict:
    """Freemium Open-Source v1.0: Multi-Character Voice-to-Identity Diarization is exclusive to EZ Cinematrix PRO v3.5."""
    n_wins = max(1, int(num_windows or 1))
    return {
        'active': False,
        'edition': 'FREEMIUM_v1.0',
        'tier': 'FREEMIUM_OPEN_SOURCE_V1_0',
        'has_speaker_switches': False,
        'windows': [],
        'window_speaker_ids': [0] * n_wins,
        'scenecut_window_indices': [],
        'speaker_tags': ['<Picture 1>'] * n_wins,
    }


def _parse_structured_continuity_parts(raw_text: str, is_ref2va: bool=False) -> list:
    parts_iter = list(re.finditer(r'(?im)^\s*(?:-{3,}\s*)?Continuity\s+part\s*#\s*(\d+)[^\n]*$', raw_text))
    if not parts_iter:
        return []
    parsed_acts = []
    for idx, m in enumerate(parts_iter):
        start_pos = m.end()
        end_pos = parts_iter[idx + 1].start() if idx + 1 < len(parts_iter) else len(raw_text)
        chunk = raw_text[start_pos:end_pos].strip()
        if not chunk:
            continue
        m_imd = re.search(r'(?is)integrated_multimodal_description\s*:\s*([\s\S]*?)(?=\boverall_soundscape\s*:|\bnon_diegetic_music\s*:|\Z)', chunk)
        m_os = re.search(r'(?is)overall_soundscape\s*:\s*([\s\S]*?)(?=\bnon_diegetic_music\s*:|\Z)', chunk)
        m_ndm = re.search(r'(?is)non_diegetic_music\s*:\s*([\s\S]*?)\Z', chunk)
        shot_desc = re.sub(r'\s+', ' ', m_imd.group(1) if m_imd else chunk).strip()
        shot_desc = re.sub(r'(?i)^\[\s*Shot\s*\d+\s*\]\s*', '', shot_desc).strip()
        if idx == 0 and is_ref2va and '<picture 1>' not in shot_desc.lower():
            shot_desc = f'<Picture 1> (from [Shot 1]) is fully referenced. {shot_desc}'
        out_blocks = [f'[Shot 1]\n{shot_desc}']
        if m_os and m_os.group(1).strip():
            os_clean = re.sub(r'\s+', ' ', m_os.group(1)).strip()
            out_blocks.append(f'[Overall Soundscape]\n{os_clean}')
        if m_ndm and m_ndm.group(1).strip():
            ndm_clean = re.sub(r'\s+', ' ', m_ndm.group(1)).strip()
            out_blocks.append(f'[Non-Diegetic Music]\n{ndm_clean}')
        parsed_acts.append('\n\n'.join(out_blocks))
    return parsed_acts


def _extract_chronological_shot_prompts(timeline_prompt: str, num_windows: int=3, is_ref2va: bool=False, is_vocal_override: bool=False, user_scene_input: str='', allow_camera_movement: bool=False, subject_stance_posture: str='') -> list:
    raw = str(timeline_prompt or '').strip()
    if not raw:
        return []
    if not str(user_scene_input or '').strip():
        user_scene_input = raw
    target_wins = max(1, int(num_windows or 1))
    structured_acts = _parse_structured_continuity_parts(raw, is_ref2va=is_ref2va)
    if structured_acts:
        while len(structured_acts) < target_wins:
            structured_acts.append(structured_acts[-1])
        return structured_acts[:max(target_wins, len(structured_acts))]
    raw = _scrub_unrequested_genital_hallucinations(raw, user_scene_input)
    ref_pic_lbl = '<Picture 1>' if is_ref2va else 'the initial keyframe'
    ref_subj_lbl = '<Subject 1>' if is_ref2va else 'the primary subject'
    raw = re.sub('(?i)\\[\\s*Master\\s+Scene[^\\]\\n]*\\][\\s:*#\\-]*', '\n[Master Scene & Visual Theme]\n', raw)
    max_shot_scan = max(16, target_wins + 4)
    for idx in range(1, max_shot_scan + 1):
        raw = re.sub(f'(?i)\\[\\s*Shot\\s*{idx}\\b[^\\]\\n]*\\][\\s:*#\\-]*', f'\n[Shot {idx}]\n', raw)
        raw = re.sub(f'(?im)^\\s*[#*\\-\\s]*Shot\\s*{idx}\\b(?:\\s*\\([^)\\n]*\\))?\\s*(?:[:\\-]+\\s*|\\s*$)', f'[Shot {idx}]\n', raw)
    raw = re.sub('(?i)\\[\\s*Constraints[^\\]\\n]*\\][\\s:*#\\-]*', '\n[Constraints]\n', raw)
    raw = re.sub('(?im)^\\s*[#*\\-\\s]*Constraints\\s*(?:[:\\-]+\\s*|\\s*$)', '[Constraints]\n', raw)
    raw = re.sub('(?i)\\[\\s*Overall\\s+Soundscape[^\\]\\n]*\\][\\s:*#\\-]*', '\n[Overall Soundscape]\n', raw)
    raw = re.sub('(?im)^\\s*[#*\\-\\s]*Overall\\s+Soundscape\\s*(?:[:\\-]+\\s*|\\s*$)', '[Overall Soundscape]\n', raw)
    raw = re.sub('(?i)\\[\\s*Non-Diegetic\\s+Music[^\\]\\n]*\\][\\s:*#\\-]*', '\n[Non-Diegetic Music]\n', raw)
    raw = re.sub('(?im)^\\s*[#*\\-\\s]*Non-Diegetic\\s+Music\\s*(?:[:\\-]+\\s*|\\s*$)', '[Non-Diegetic Music]\n', raw)
    raw = re.sub('(?i)following\\s+a\\s+(?:sudden\\s+cinematic\\s+smash|secondary\\s+rapid\\s+cinematic)\\s+cut\\s*,?', 'continuing seamlessly in the exact same continuous shot and camera distance,', raw)
    raw = re.sub('(?i)\\b(?:smash\\s+cut|rapid\\s+cut|jump\\s+cut|hard\\s+cut|cuts?\\s+to)\\b', 'smoothly transitions within the same continuous camera framing', raw)
    if not allow_camera_movement:
        raw = re.sub('(?i)\\blow-angle\\s+cutaway\\s+shot\\s+of\\s+(?:her|his|the)\\s+(?:feet|boots)\\b', 'steady camera framing keeping the subject centered in frame', raw)
    if not is_ref2va:
        raw = re.sub('(?i)<Picture\\s*1>', 'the initial keyframe', raw)
        raw = re.sub('(?i)<Subject\\s*1>', 'the primary subject', raw)
    master_theme = ''
    m_theme = re.search('\\[Master Scene & Visual Theme\\]\\s*([\\s\\S]*?)(?=\\[Shot\\s*1\\]|\\Z)', raw, flags=re.IGNORECASE)
    if m_theme:
        master_theme = re.sub('\\s+', ' ', m_theme.group(1)).strip()
        master_theme = re.sub(r'(?is)\[SUNO\s+RHYTHMIC[\s\S]*$', '', master_theme).strip()
        master_theme = re.sub(r'(?i)\bAct\s*\d+\s*\(\d+(?:\.\d+)?s\s*-\s*\d+(?:\.\d+)?s[^)]*\)\s*:\s*', '', master_theme)
        master_theme = re.sub(r'(?i)\s*\[(?:\d+(?:\.\d+)?s-\d+(?:\.\d+)?s:[A-Z_]+(?:,\s*)?)+\]', '', master_theme)
        master_theme = re.sub('(?i)\\bRAW\\s+candid\\s+35mm\\s+live-action\\s+photograph\\b', 'Cinematic 35mm live-action motion picture sequence', master_theme)
        master_theme = re.sub('(?i)\\b(?:authentic|visible)\\s+(?:human\\s+)?skin\\s+pores,?\\s*', 'authentic epidermal micro-texture, ', master_theme)
        theme_sents = [s.strip() for s in re.split('(?<=[.!?])\\s+', master_theme) if s.strip() and not re.search(r'(?i)\b(?:midpoint|sequence\s+starting|initiates\s+a\s+sudden|explosively\s+swinging|slams\s+violently|use\s+this\s+audio\s+blueprint|critical\s+audio-waveform)\b', s)]
        master_theme = ' '.join(theme_sents[:4]).strip()
        if len(master_theme) > 420:
            master_theme = master_theme[:420].rsplit('.', 1)[0].strip() + '.'
    is_speech_perf = bool(re.search(r'(?i)\b(?:spoken\s+dialogue|spoken\s+voice|speaks\s+expressively|syllable[-\s]?accurate\s+lip[-\s]?sync|interview(?:ing|s|ed)?|late-night\s+television\s+news\s+anchor|teleprompter)\b', raw))
    is_vocal_perf = bool(is_vocal_override) or is_speech_perf or bool(re.search(r'(?i)\b(?:suno\s+rhythmic|32khz\s+vocal\s+waveform|phoneme[-\s]?accurate\s+lip[-\s]?sync|studio\s+lead\s+vocals|expressive\s+singing|singing\s+expressively|singing\s+naturally|vocal\s+envelope|open-mouth\s+lip-sync)\b', raw))
    is_indoor_06 = bool(
        re.search(r'(?i)\b(?:studio|news\s+desk|broadcast|indoor|indoors|interior|room|office|tavern|bar|cockpit|interview(?:ing)?|anchor|teleprompter|desk)\b', raw)
    ) and not bool(re.search(r'(?i)\b(?:wind|windy|breeze|storm|gale|blizzard)\b', str(user_scene_input or '')))
    combined_06_txt = raw + ' ' + str(user_scene_input or '')
    main_subj_tags_06 = [int(m.group(1)) for m in re.finditer(r'(?i)<\s*main[_\s-]*subject\s*(\d+)\s*>', combined_06_txt)]
    subj_tags_06 = [int(m.group(1)) for m in re.finditer(r'(?i)<\s*subject\s*(\d+)\s*>', combined_06_txt)]
    has_bg_extras_06 = bool(subj_tags_06 and main_subj_tags_06) or bool(re.search(r'(?i)\b(?:statister|background\s+extras|bar/tavern\s+patrons|city\s+pedestrians|brawling\s+combatants|studio\s+audience|group\s+participants)\b', combined_06_txt))
    has_dual_subj_06 = (max(main_subj_tags_06) >= 2 if main_subj_tags_06 else (max(subj_tags_06) >= 2 if subj_tags_06 else False)) or bool(
        re.search(
            r'(?i)(?:<\s*(?:main[_\s-]*)?subject\s*2\s*>|\bgoblin\b|\binterview(?:ing|s|ed)?\b|\bco-?anchor\b|\bsenator\b|\btwo[-\s]?shot\b|\btwo\s+characters\b|\bthree\s+characters\b|\bbeside\s+her\b|\bacross\s+from\s+her\b|\b(?:brawl|fistfight|duel(?:ing)?|fighting|sparring|making\s+love|lovemaking|passionate\s+kiss(?:ing)?|lovers|couple|threesome|foursome|orgy|harem|slagsmål|älskog|trekant|orgie)\b)',
            combined_06_txt,
        )
    )
    if is_ref2va:
        raw = re.sub(r'(?i)<\s*main[_\s-]*subject\s*(\d+)\s*>', r'<Subject \1>', raw)
        if has_dual_subj_06:
            ref_subj_lbl = '<Subject 1> and <Subject 2>'
    else:
        raw = re.sub(r'(?i)<\s*main[_\s-]*subject\s*1\s*>', 'the primary protagonist (<Main_Subject 1>)', raw)
        raw = re.sub(r'(?i)<\s*main[_\s-]*subject\s*2\s*>', 'the second co-starring character (<Main_Subject 2>)', raw)
        if has_dual_subj_06:
            ref_subj_lbl = 'both foreground characters (<Main_Subject 1> on the left and <Main_Subject 2> on the right)'
    vocal_action_gerund = 'speaking the dialogue with syllable-accurate open-mouth lip-sync and active lower-jaw articulation' if is_speech_perf else 'singing the lead vocals with natural lip-sync articulation'
    if is_vocal_perf:
        raw = re.sub(
            r'(?i)\b(?:turns?\s+around(?:\s+and\s+walks?\s+away)?|turning\s+around|spins?\s+around|spinning\s+around|twirls?(?:\s+around)?|twirling|pirouettes?|360[-\s]?degree|leaps?\s+(?:high\s+)?(?:into\s+the\s+air|up|forward)|leaping\s+(?:into\s+the\s+air|up)|jumps?\s+(?:high\s+)?(?:into\s+the\s+air|up)|jumping\s+(?:into\s+the\s+air|up)|swings?\s+(?:her|his|their|the)\s+(?:heavy\s+|battle\s+)?(?:axe|sword|weapon|hammer)|walks?\s+away(?:\s+from\s+(?:the\s+)?camera)?|walking\s+away(?:\s+from\s+(?:the\s+)?camera)?|with\s+(?:her|his|their)\s+back\s+(?:turned|to\s+the\s+camera)|from\s+behind|rear[-\s]?view|back\s+of\s+(?:her|his|their)\s+head)\b',
            f'remaining strictly facing the camera lens in the exact constant shot distance of {ref_pic_lbl}',
            raw,
        )
        raw = re.sub(
            r'(?i)(?:None\.\s*Purely\s+diegetic\s+environmental\s+ambience[^.\n]*\.|strictly\s+no\s+singing,?\s*no\s+vocals[^.\n]*\.)',
            f'Continuous spoken dialogue and expressive vocal articulation synchronized frame-for-frame with {ref_subj_lbl} from 0.0s.' if is_speech_perf else f'Continuous studio lead vocals and expressive singing synchronized frame-for-frame with {ref_subj_lbl} from 0.0s.',
            raw,
        )
    if is_indoor_06:
        raw = re.sub(
            r'(?i)\b(?:wind[-\s]?swept\s+hair(?:\s+motion|\s+movement)?|hair\s+blowing\s+in\s+the\s+wind|blowing\s+in\s+the\s+(?:cold\s+|icy\s+)?wind|fluid\s+hair\s+motion\s+in\s+the\s+wind|in\s+the\s+howling\s+wind|cold\s+wind\s+gusts|howling\s+wind\s+gusts)\b',
            'calm indoor studio air with naturally settled hair',
            raw,
        )
    tail_ctx = ''
    tail_match = re.search('(\\[(?:Constraints|Overall Soundscape|Non-Diegetic Music|SUNO RHYTHMIC)\\][\\s\\S]*)$', raw, flags=re.IGNORECASE)
    if tail_match:
        tail_ctx = tail_match.group(1).strip()
        narrative_body = raw[:tail_match.start()].strip()
    else:
        narrative_body = raw
    if tail_ctx:
        tail_ctx = re.sub(r'(?i)\bAct\s*\d+\s*\(\d+(?:\.\d+)?s\s*-\s*\d+(?:\.\d+)?s[^)]*\)\s*:\s*', '', tail_ctx)
        tail_ctx = re.sub(r'(?i)\s*\|\s*(?=[A-Z<])', '. ', tail_ctx)
        tail_ctx = re.sub(r'(?i)\s*\[(?:\d+(?:\.\d+)?s-\d+(?:\.\d+)?s:[A-Z_]+(?:,\s*)?)+\]', '', tail_ctx)
        tail_ctx = re.sub(r'(?i)\bfrom\s+0(?:\.0)?s\s+through\s+\d+(?:\.\d+)?s\b', 'throughout the entire continuous shot', tail_ctx)
    if is_vocal_perf:
        vocal_lock_clause = (
            f'[Overall Soundscape]\nClear upfront spoken dialogue and authentic studio voice synchronized frame-for-frame with {ref_subj_lbl} articulating every syllable with natural open-mouth, lip, and lower-jaw lip-sync motion.'
            if is_speech_perf else
            f'[Overall Soundscape]\nUpfront studio-grade lead vocals and expressive live singing synchronized frame-for-frame with {ref_subj_lbl} articulating every lyric phrase with natural open-mouth, lip, and jaw lip-sync motion.'
        )
        if '[overall soundscape]' not in tail_ctx.lower():
            tail_ctx = f'{tail_ctx}\n{vocal_lock_clause}'.strip() if tail_ctx else vocal_lock_clause
        else:
            tail_ctx = re.sub(r'(?i)(?:None\.\s*)?Purely\s+(?:diegetic|physical)\s+environmental[^.\n]*\.?', vocal_lock_clause.split('\n', 1)[1], tail_ctx)
    else:
        sfx_pure_clause = (
            'Purely physical indoor studio foley acoustics: quiet room ambience and subtle fabric and floor movement.'
            if is_indoor_06 else
            'Purely physical environmental foley acoustics: natural ambient atmosphere and subtle garment and body movement.'
        )
        if '[overall soundscape]' not in tail_ctx.lower():
            sfx_lock = f'[Overall Soundscape]\nCrisp high-definition environmental foley recording: realistic room acoustics and body movement friction synchronized with the visual action. {sfx_pure_clause}'
            tail_ctx = f'{tail_ctx}\n{sfx_lock}'.strip() if tail_ctx else sfx_lock
        else:
            if is_indoor_06:
                tail_ctx = re.sub(r'(?i)\bcrunching\s+snow(?:\s+underfoot)?,?\s*', 'quiet room ambience, ', tail_ctx)
            tail_ctx = re.sub(r'(?i);?\s*(?:strictly\s+)?(?:zero|no)\s+(?:spoken\s+dialogue|human\s+voice|voiceover|narration|singing|background\s+music|instrumental\s+score|music|vocals)[^.\n]*\.?', '', tail_ctx).strip()
    is_fem_subj = bool(re.search(r'(?i)\b(?:she|her|female|woman|girl|queen|goddess|heroine|priestess)\b', raw))
    has_orc_tusk = bool(re.search(r'(?i)\b(?:orc|half[-\s]?orc|tusks?|boar[-\s]?headed|minotaur|ogre|troll|dragon)\b', raw))
    m_age_06 = re.search(r'(?i)\b(\d{1,2}-year-old|ageless-cyborg)\b', raw)
    active_age_06 = m_age_06.group(1) if m_age_06 else '25-year-old'
    m_num_06 = re.search(r'(\d{1,2})', active_age_06)
    age_num_06 = int(m_num_06.group(1)) if m_num_06 else 25
    skin_age_adj = 'youthful baby-smooth unwrinkled' if age_num_06 <= 20 else ('gorgeous smooth unwrinkled' if age_num_06 <= 29 else ('poised mature' if age_num_06 <= 37 else 'seasoned mature'))
    face_desc_tag = (
        f'{skin_age_adj} {active_age_06} facial structure and protruding lower-jaw tusks'
        if has_orc_tusk else
        f'{skin_age_adj} {active_age_06} feminine face'
    )
    cam_lock_clause = '' if allow_camera_movement else ' at a constant camera distance'
    if has_dual_subj_06:
        fem_face_lock = f' Preserve the distinct individual facial identities, species, skin tones, and outfits of both foreground characters from Frame 0{cam_lock_clause} without merging or cloning faces.'
    elif is_fem_subj and has_orc_tusk:
        fem_face_lock = f' Preserve her single unified {skin_age_adj} {active_age_06} facial structure, skin tone, and protruding tusks from Frame 0{cam_lock_clause}.'
    elif is_fem_subj:
        fem_face_lock = f' Preserve her single unified {skin_age_adj} {active_age_06} feminine facial structure and proportions from Frame 0{cam_lock_clause}.'
    else:
        fem_face_lock = ''
    if has_dual_subj_06 and has_bg_extras_06:
        subj_count_lock = 'Maintain all foreground main characters in razor-sharp f/5.6 deep focus on the same foreground plane alongside the coherent background extras (statister)'
    elif has_dual_subj_06:
        subj_count_lock = 'Maintain both distinct foreground main characters (<Subject 1> on the left and <Subject 2> on the right) in razor-sharp f/5.6 deep focus on the exact same foreground plane at matching scale'
    elif has_bg_extras_06:
        subj_count_lock = 'Maintain the foreground protagonist in razor-sharp focus while preserving coherent background extras (statister) in the environment'
    else:
        subj_count_lock = 'Maintain one single subject in frame'
    bg_env_label = 'indoor background environment' if is_indoor_06 else 'background environment'
    wants_dynamic_vertical_choreo_06 = bool(
        re.search(
            r'(?i)\b(?:squats?|squatting|kneels?|kneeling|crouches?|crouching|bends?|bending|dance|dancing|dances|jumps?|jumping|bounces?|bouncing|twirls?|hips?\s+sway(?:ing)?|på\s+huk|hukar|hukande|knäböj(?:er|ande)?|på\s+knä|böjer|dansar|hoppar|snurrar|sitt(?:er|ande)|ligg(?:er|ande))\b',
            combined_06_txt,
        )
    )
    wants_garment_dynamics_06 = bool(re.search(r'(?i)\b(?:slip(?:s|ping)?|shift(?:s|ing)?|part(?:s|ing)?|lift(?:s|ing)?|pull(?:s|ing)?\s+(?:up|down|aside)|reveal(?:s|ing)?|peek(?:s|ing)?)\b', combined_06_txt))
    outfit_lock_tag = 'outfit design and fabric colors' if wants_garment_dynamics_06 else 'outfit geometry'
    id_lock_phrase = f'keeping both characters\' distinct facial identities, species anatomy, and {outfit_lock_tag}' if has_dual_subj_06 else f'keeping her exact facial identity, {face_desc_tag}, hair color and style, and {outfit_lock_tag}'
    if allow_camera_movement:
        continuity_lock_footer = (
            f'\n[Continuity, Intentional Camera Trajectory, Front-Facing, Anatomy & Lip-Sync Lock]\nContinuous single-take cinema camera following the requested camera movement smoothly. {subj_count_lock} facing the camera lens with natural open-mouth lip-sync and jaw articulation.{fem_face_lock} Keep character anatomy, head-to-body scale, skin tone, color grading, and {bg_env_label} locked to {ref_pic_lbl}.'
            if is_vocal_perf else
            f'\n[Continuity, Intentional Camera Trajectory, Facial Identity & Proportion Lock]\nContinuous single-take cinema camera executing the requested camera movement smoothly. {subj_count_lock} {id_lock_phrase} consistent with {ref_pic_lbl} throughout every second.{fem_face_lock}'
        )
    else:
        posture_scale_clause = (
            f'at the exact constant camera distance of {ref_pic_lbl} while executing the prompted full-body choreography, vertical posture transitions, and natural garment dynamics'
            if (wants_dynamic_vertical_choreo_06 or wants_garment_dynamics_06) else
            f'at the exact camera distance and vertical proportions of {ref_pic_lbl}'
        )
        outfit_footer_clause = 'outfit design and fabric colors' if wants_garment_dynamics_06 else 'outfit proportions'
        continuity_lock_footer = (
            f'\n[Continuity, Constant Camera Distance, Full-Posture Scale & Lip-Sync Lock]\nStatic locked-off camera on a heavy tripod maintaining the exact constant camera distance and lens focal length of {ref_pic_lbl} from start to finish. {subj_count_lock} {posture_scale_clause} performing natural open-mouth vocal lip-sync, active lower-jaw articulation, and expressive body performance.{fem_face_lock} Keep character anatomy, {outfit_footer_clause}, head-to-body scale, skin tone, and {bg_env_label} locked to {ref_pic_lbl}.'
            if is_vocal_perf else
            f'\n[Continuity, Constant Camera Distance, Facial Identity & Proportion Lock]\nStatic locked-off camera on a heavy tripod maintaining the exact constant camera distance and lens focal length of {ref_pic_lbl} from start to finish. {subj_count_lock} {id_lock_phrase} {posture_scale_clause} throughout every second.{fem_face_lock}'
        )
    tail_ctx = f'{tail_ctx}\n{continuity_lock_footer}'.strip() if tail_ctx else continuity_lock_footer.strip()
    shot_matches = list(re.finditer('\\[Shot\\s*\\d+[^\\]]*\\]', narrative_body, flags=re.IGNORECASE))
    raw_bodies = []
    if len(shot_matches) >= 2:
        for (idx, m) in enumerate(shot_matches):
            start_pos = m.end()
            end_pos = shot_matches[idx + 1].start() if idx + 1 < len(shot_matches) else len(narrative_body)
            body = re.sub('\\s+', ' ', narrative_body[start_pos:end_pos]).strip()
            if body:
                raw_bodies.append(body)
    if len(raw_bodies) < 2:
        clean_narr = re.sub('(?im)^\\s*BLOCK\\s*\\d+\\s*$', '', narrative_body).strip()
        clean_narr = re.sub('\\[Master Scene & Visual Theme\\]', '', clean_narr, flags=re.IGNORECASE).strip()
        paras = [p.strip() for p in re.split(r'\n\s*\n', clean_narr) if p.strip()]
        act_pat = r'(?i)(?:^\s*(?:a\s+sequence\s+starting|at\s+the\s+midpoint|from\s+00:|at\s+00:|in\s+shot\s+\d|then\s+she|then\s+he|suddenly)|\b(?:sequence\s+starting\s+with|midpoint\s+of\s+the\s+sequence|initiates\s+a\s+sudden|explosively\s+swinging)\b)'
        static_ps = [p for p in paras if not re.search(act_pat, p)]
        action_ps = [p for p in paras if re.search(act_pat, p)]
        if static_ps and action_ps:
            if not master_theme:
                static_sents = [s.strip() for s in re.split('(?<=[.!?])\\s+', re.sub(r'\s+', ' ', ' '.join(static_ps)).strip()) if s.strip()]
                master_theme = ' '.join(static_sents[:3]).strip()
                if len(master_theme) > 380:
                    master_theme = master_theme[:380].rsplit('.', 1)[0].strip() + '.'
            clean_narr = ' '.join(action_ps)
        sents = [s.strip() for s in re.split('(?<=[.!?])\\s+', re.sub('\\s+', ' ', clean_narr)) if s.strip()]
        if len(sents) >= target_wins and target_wins > 3:
            raw_bodies = []
            for s_idx in range(target_wins):
                c_start = int(round(s_idx * len(sents) / float(target_wins)))
                c_end = int(round((s_idx + 1) * len(sents) / float(target_wins)))
                raw_bodies.append(' '.join(sents[c_start:max(c_start + 1, c_end)]))
        elif len(sents) >= 3:
            mid_idx = next((i for (i, s) in enumerate(sents) if i > 0 and re.search(r'(?i)\b(?:at\s+the\s+midpoint|midpoint\s+of\s+the\s+sequence|initiates\s+a\s+sudden|suddenly)\b', s)), None)
            if mid_idx is not None and mid_idx < len(sents) - 1:
                if len(sents) - mid_idx >= 3:
                    raw_bodies = [' '.join(sents[:mid_idx]), ' '.join(sents[mid_idx:-1]), sents[-1]]
                else:
                    raw_bodies = [' '.join(sents[:mid_idx]), sents[mid_idx], ' '.join(sents[mid_idx + 1:])]
            else:
                c1 = max(1, len(sents) // 3)
                c2 = max(c1 + 1, 2 * len(sents) // 3)
                raw_bodies = [' '.join(sents[:c1]), ' '.join(sents[c1:c2]), ' '.join(sents[c2:])]
        elif len(sents) == 2:
            raw_bodies = [sents[0], sents[1], sents[1]]
        else:
            raw_bodies = [clean_narr or raw]
    if raw_bodies:
        if len(raw_bodies) >= 2:
            while len(raw_bodies) < target_wins:
                prev_b = raw_bodies[-1]
                next_win_num = len(raw_bodies) + 1
                raw_bodies.append(f'Continuing seamlessly from the final frame of Shot {next_win_num - 1} in the exact same camera framing and posture, {prev_b}')
            if len(raw_bodies) > target_wins:
                merged_bodies = []
                for w_i in range(target_wins):
                    b_start = (w_i * len(raw_bodies)) // target_wins
                    b_end = max(b_start + 1, ((w_i + 1) * len(raw_bodies)) // target_wins)
                    merged_bodies.append(' '.join(raw_bodies[b_start:b_end]))
                raw_bodies = merged_bodies
            else:
                raw_bodies = raw_bodies[:target_wins]
        else:
            primary_shot_body = raw_bodies[0]
            raw_bodies = [primary_shot_body for _ in range(target_wins)]
    concise_id_theme = master_theme.strip()

    dolly_drift_pat = r'(?i)\b(?:steady\s+85mm\s+portrait\s+lens(?:\s+at\s+f/1\.4)?\s+slowly\s+drifting\s+in\s+a\s+dolly-in\s+motion|slowly\s+drifting\s+in\s+a\s+dolly-in\s+motion|dolly-in\s+motion|dolly-in|push-in|zoom-in|zooming\s+in|zooms?\s+in|anamorphic\s+push-in|85mm\s+portrait\s+lens(?:\s+at\s+f/1\.4)?|85mm\s+medium\s+close-up\s+portrait\s+framing|waist-up\s+medium\s+portrait\s+camera|extreme\s+macro\s+close-up|extreme\s+close-up|tight\s+close-up(?:\s+portrait)?|macro\s+close-up|medium\s+close-up\s+portrait|close-up\s+portrait(?:\s+framing)?|close-up\s+on\s+(?:<subject\s*1>|her|his|the)\s+(?:face|lips|mouth|eyes)|camera\s+(?:pushes|moves|glides|drifts)\s+(?:closer|in|toward))\b'
    if not allow_camera_movement:
        master_theme = _scrub_unrequested_genital_hallucinations(re.sub(dolly_drift_pat, f'steady locked-off camera at the exact constant shot distance of {ref_pic_lbl}', master_theme), user_scene_input)
        concise_id_theme = _scrub_unrequested_genital_hallucinations(re.sub(dolly_drift_pat, f'steady locked-off camera at the exact constant shot distance of {ref_pic_lbl}', concise_id_theme), user_scene_input)
    else:
        master_theme = _scrub_unrequested_genital_hallucinations(master_theme, user_scene_input)
        concise_id_theme = _scrub_unrequested_genital_hallucinations(concise_id_theme, user_scene_input)
    if is_vocal_perf:
        lip_rep_phrase = 'expressive parted lips and active jaw articulation speaking the dialogue with natural lip-sync' if is_speech_perf else 'expressive parted lips singing the lead vocals with natural lip-sync articulation'
        master_theme = re.sub(r'(?i)\b(?:a\s+)?(?:firmly\s+|tightly\s+)?closed\s+(?:mouth|lips)(?:\s+and\s+a\s+(?:fierce|serene)\s+silent\s+expression)?\b', lip_rep_phrase, master_theme)
        concise_id_theme = re.sub(r'(?i)\b(?:a\s+)?(?:firmly\s+|tightly\s+)?closed\s+(?:mouth|lips)(?:\s+and\s+a\s+(?:fierce|serene)\s+silent\s+expression)?\b', lip_rep_phrase, concise_id_theme)

    stance_low_06 = str(subject_stance_posture or '').strip().lower()
    has_explicit_stance_06 = not stance_low_06.startswith(('auto', ''))
    wants_kneeling_06 = stance_low_06.startswith('kneeling_crouching') or bool(
        re.search(r'(?i)\b(?:staged\s+kneeling\s+or\s+crouching|kneels?|kneeling|crouches?|crouching|squats?|squatting|på\s+huk|hukar|hukande|knäböj(?:er|ande)?|på\s+knä)\b', combined_06_txt)
    )

    def _sanitize_upright_eye_level_action(txt_in: str, shot_idx: int = 0) -> str:
        s = _scrub_unrequested_genital_hallucinations(txt_in, user_scene_input)
        s = re.sub(r'(?<=[a-z])\s+(Locked\s+to\s+)', r'. \1', s)
        s = re.sub(r'(?i)\s*Locked\s+to\s+[^.]*\baesthetic(?:\s*\([^)]*\))?\.\s*', ' ', s)
        s = re.sub(r'(?i)\s*<Subject\s*1>\s+preserves\s+[^.]*\bzero\s+(?:hard\s+)?scene\s+cuts\.\s*', ' ', s)
        s = re.sub(r'(?i)\bFrom\s+the\s+first\s+frame\s+of\s+Shot\s+\d+,?\s*', '', s)
        s = re.sub(r'(?i)\bContinuing\s+seamlessly\s+from\s+the\s+final\s+frame\s+of\s+Shot\s+\d+\s*\([^)]*\),?\s*', 'Continuing seamlessly in one unbroken take, ', s)
        s = re.sub(r'(?i)\bMaintaining\s+the\s+exact\s+[^,]+,\s*lighting,\s*and\s+original\s+style\s+of\s+Shot\s+\d+\s+with\s+zero\s+hard\s+cuts,?\s*', '', s)
        if shot_idx > 0 or wants_dynamic_vertical_choreo_06 or wants_garment_dynamics_06:
            s = re.sub(r'(?i)\bHer\s+left\s+hand\s+gently\s+touches\s+her\s+temple\s+while\s+her\s+right\s+arm\s+rests\s+near\s+her\s+hip,?\s*(?:posture\s+poised\s+and\s+slightly\s+coy)?[.,;]?\s*', '', s)
            s = re.sub(r'(?i)<Subject\s*1>\s+maintains\s+her\s+exact\s+initial\s+stance,?\s*clothing,?\s*and\s+framing[^.]*\.\s*', '', s)
        s = re.sub(r'(?i)\s*aligned\s+to\s+acoustic\s+vocal\s+envelope\s*\[[^\]]*\]', '', s)
        s = re.sub(r'(?i)\s*\[(?:\d+(?:\.\d+)?s-\d+(?:\.\d+)?s:[A-Z_]+(?:,\s*)?)+\]', '', s)
        s = re.sub(r'(?i)\bAct\s*\d+\s*\(\d+(?:\.\d+)?s\s*-\s*\d+(?:\.\d+)?s[^)]*\)\s*:\s*', '', s)
        s = re.sub(r'(?i)\b(?:at|from|after|until|up\s+to|around)\s+(?:\d+(?:\.\d+)?\s*(?:s|sec|seconds?)|event_[12])\s*(?:to\s+\d+(?:\.\d+)?\s*(?:s|sec|seconds?))?\s*,?\s*', '', s)
        s = re.sub(r'(?i)\b(?:sudden\s+cinematic\s+smash\s+cut|secondary\s+rapid\s+cinematic\s+cut|smash\s+cut|jump\s+cut|scene\s+cut|cut\s+transition|cuts?\s+to|switches?\s+to)\b', 'continuous unbroken single-take motion', s)
        s = re.sub(r'(?i)\b(?:authentic|visible)\s+(?:human\s+)?skin\s+pores,?\s*', 'authentic epidermal micro-texture, ', s)
        if is_indoor_06:
            s = re.sub(
                r'(?i)\b(?:wind[-\s]?swept\s+hair(?:\s+motion|\s+movement)?|hair\s+blowing\s+in\s+the\s+wind|blowing\s+in\s+the\s+(?:cold\s+|icy\s+)?wind|fluid\s+hair\s+motion\s+in\s+the\s+wind|in\s+the\s+howling\s+wind|cold\s+wind\s+gusts|howling\s+wind\s+gusts)\b',
                'settled indoor hair in calm studio air',
                s,
            )
        if not allow_camera_movement:
            s = re.sub(dolly_drift_pat, f'steady locked-off camera at the exact constant shot distance of {ref_pic_lbl}', s)
        if has_explicit_stance_06 and stance_low_06.startswith('kneeling_crouching') and shot_idx > 0:
            s = re.sub(
                r'(?i)\b(?:standing\s+in\s+a\s+wide(?:\s*,\s*grounded)?\s+combat\s+stance(?:\s+with\s+one\s+leg\s+raised)?|stands?\s+tall\s+and\s+upright|maintains?\s+her\s+grounded\s+stance|staying\s+upright(?:\s+in\s+frame)?)\b',
                'kneeling low on her knees in a grounded crouching posture on the ground',
                s,
            )
        if is_vocal_perf:
            lip_rep_s = 'expressive parted lips and active jaw articulation speaking the dialogue with natural lip-sync' if is_speech_perf else 'expressive parted lips singing the lead vocals with natural lip-sync articulation'
            s = re.sub(r'(?i)\b(?:a\s+)?(?:firmly\s+|tightly\s+)?closed\s+(?:mouth|lips)(?:\s+and\s+a\s+(?:fierce|serene)\s+silent\s+expression)?\b', lip_rep_s, s)
            s = re.sub(r'(?i)\b(?:in\s+silent\s+reverence|fierce\s+silent\s+expression|serene\s+silent\s+expression|silent\s+expression|without\s+speaking\s+or\s+singing)\b', lip_rep_s, s)
        else:
            s = re.sub(r'(?i);?\s*(?:strictly\s+)?(?:zero|no)\s+(?:spoken\s+dialogue|human\s+voice|voiceover|narration|singing|background\s+music|instrumental\s+score|music|vocals)[^.\n]*\.?', '', s)
        s = re.sub(r'\s{2,}', ' ', s).strip()
        if s and s[-1] not in '.!?':
            s = s.rstrip(',;:- ') + '.'
        return s

    acts = []
    hair_motion_clause = 'settled indoor hair' if is_indoor_06 else 'natural hair movement'
    lead_id_clause = 'both characters\' distinct facial identities and proportions' if has_dual_subj_06 else f'her {face_desc_tag} and anatomical proportions'
    posture_lock_clause = 'character anatomy' if (has_explicit_stance_06 or wants_dynamic_vertical_choreo_06 or wants_garment_dynamics_06) else 'posture framing'
    vocal_body_clause = 'active full-body choreography and expressive performance' if (wants_dynamic_vertical_choreo_06 or wants_garment_dynamics_06) else 'expressive body performance'
    wants_room_or_outfit_swap = bool(re.search(r'(?i)\b(?:changes?\s+(?:into|her\s+outfit|clothes|rooms?)|teleports?\s+to|cuts?\s+to\s+another\s+room)\b', str(user_scene_input or '')))
    env_garment_lock = '' if wants_room_or_outfit_swap else f', exact background room decor, and exact outfit of {ref_pic_lbl} (no room change, no added skirt or unrequested clothing)'
    if allow_camera_movement:
        unified_lead = (
            f'Single continuous unbroken shot maintaining the exact shading, lighting{env_garment_lock} while executing the requested camera movement smoothly as {ref_subj_lbl} faces the camera lens {vocal_action_gerund} with {vocal_body_clause}.'
            if is_vocal_perf else
            f'Single continuous unbroken shot maintaining the exact shading, lighting{env_garment_lock} while executing the requested camera movement smoothly with {lead_id_clause} and {hair_motion_clause} locked in proportion.'
        )
    else:
        unified_lead = (
            f'Single continuous locked-off tripod shot maintaining the exact camera angle, {bg_env_label}{env_garment_lock} as {ref_subj_lbl} performs {vocal_action_gerund} with {vocal_body_clause}.'
            if is_vocal_perf else
            f'Single continuous locked-off tripod shot maintaining the exact camera angle, lighting, {posture_lock_clause}{env_garment_lock} while keeping {lead_id_clause} locked in proportion.'
        )
    use_theme_full = concise_id_theme if concise_id_theme else master_theme
    compact_theme = (use_theme_full[:240].rsplit('.', 1)[0].strip() + '.') if len(use_theme_full) > 240 and '.' in use_theme_full[:240] else use_theme_full[:240].strip()
    for (idx, b_txt) in enumerate(raw_bodies):
        clean_b = _sanitize_upright_eye_level_action(b_txt, shot_idx=idx)
        eff_theme = use_theme_full if idx == 0 else compact_theme
        shot_theme_suffix = f' {eff_theme}' if eff_theme and eff_theme[:32].lower() not in clean_b.lower() else ''
        if idx == 0 and is_ref2va and '(from [shot 1]) is fully referenced' not in clean_b.lower():
            pic1_ref_prefix = '<Picture 1> (from [Shot 1]) is fully referenced for the two-character master scene, <Picture 2> anchors <Subject 2> on the right, and <Picture 3> anchors <Subject 1> on the left. ' if has_dual_subj_06 else '<Picture 1> (from [Shot 1]) is fully referenced. '
        else:
            pic1_ref_prefix = ''
        anchored = f'[Shot 1]\n{pic1_ref_prefix}{clean_b} {unified_lead}{shot_theme_suffix}'.strip()
        full_act = f'{anchored}\n\n{tail_ctx}'.strip() if tail_ctx else anchored.strip()
        acts.append(full_act)
    return acts[:max(1, target_wins)]

def _snap_h3_native_frame_count(frames: int) -> int:
    f_val = max(5, int(frames))
    k_periods = max(0, int(round(float(f_val - 5) / 17.0)))
    return 17 * k_periods + 5

def _h3_frames_to_video_tokens(frames: int) -> int:
    (q_per, r_rem) = divmod(max(5, int(frames)), 17)
    return 5 * q_per + (2 if r_rem >= 5 else max(1, (r_rem + 3) // 4))

def _h3_frames_to_audio_tokens(frames: int, fps: float = 24.0) -> int:
    return max(1, int(round(float(max(1, int(frames))) * 40.0 / max(1.0, float(fps)))))

def build_temporal_director_conditioning_and_latent(video_model_fl2va, video_model_ref2va, video_clip, video_vae, production_mode: str, timeline_prompt: str, negative_prompt: str, video_width: int, video_height: int, duration_seconds: float, frame_rate: float, overlap_frames: int, keyframe_image=None, audio_vae=None, tier_profile: dict=None, ref_image_2_person=None, ref_image_3_clothing=None, ref_image_4_background=None, motion_physics_mode: str='auto_from_style_and_audio (Auto från Stil & Ljud)', motion_transfer_strength: float=0.65, reference_motion_video=None, reference_video_audio=None, style_target: str='', is_nsfw: bool=True, allow_camera_movement: bool=False, subject_stance_posture: str='auto_from_prompt (Auto från Prompt / Bild)', body_choreography_preset: str='auto_from_prompt_or_audio (Auto från Prompt / Ljud)', camera_trajectory_arc: str='follow_02_camera_setting (Följ [02] Kamerainställning / Auto)', rating_tier: str='uncensored_action', temporal_window_horizon: str=TEMPORAL_WINDOW_HORIZON_MODES[0], slot5_focus_mode: str='', user_scene_input: str=''):
    prof = dict(tier_profile) if isinstance(tier_profile, dict) else {}
    tile_sz = int(prof.get('tile_size', 512) or 512)
    is_licensed = bool(prof.get('is_licensed', True))
    max_dur = float(prof.get('max_duration_seconds', 86400.0))
    eff_duration = min(float(duration_seconds), max_dur)
    aggressive_purge = bool(prof.get('aggressive_vram_purge', not is_licensed))
    try:
        cur_res = int(getattr(comfy.model_management, 'EXTRA_RESERVED_VRAM', 0) or 0)
        if cur_res > 900 * 1024 * 1024:
            comfy.model_management.EXTRA_RESERVED_VRAM = 600 * 1024 * 1024
    except Exception:
        pass
    if aggressive_purge or not bool(prof.get('persistent_vram_weights', False)):
        if hasattr(comfy.model_management, 'unload_all_models'):
            comfy.model_management.unload_all_models()
        comfy.model_management.soft_empty_cache()
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    def _has_real_ref_pixels(img_t) -> bool:
        return isinstance(img_t, torch.Tensor) and img_t.ndim == 4 and float(img_t.detach().abs().max().item()) > 1e-04
    ref_image_2_person = ref_image_2_person if _has_real_ref_pixels(ref_image_2_person) else None
    ref_image_3_clothing = ref_image_3_clothing if _has_real_ref_pixels(ref_image_3_clothing) else None
    ref_image_4_background = ref_image_4_background if _has_real_ref_pixels(ref_image_4_background) else None
    has_extra_refs = any((x is not None for x in (ref_image_2_person, ref_image_3_clothing, ref_image_4_background)))
    use_ref_model = production_mode.startswith('REF2VA') and video_model_ref2va is not None
    active_model = video_model_ref2va if use_ref_model else video_model_fl2va
    m_opts = getattr(active_model, 'model_options', {}) if hasattr(active_model, 'model_options') and isinstance(getattr(active_model, 'model_options'), dict) else {}
    video_arch = str(m_opts.get('ez_video_arch', '') or '').lower()
    if not video_arch:
        m_cfg_cls = str(getattr(getattr(getattr(active_model, 'model', None), 'model_config', None), '__class__', type(None)).__name__).lower()
        if 'wan22' in m_cfg_cls or 'wan_22' in m_cfg_cls:
            video_arch = 'wan22'
        elif 'wan' in m_cfg_cls:
            video_arch = 'wan21'
        elif 'ltx' in m_cfg_cls:
            video_arch = 'ltxv'
        elif 'hunyuan' in m_cfg_cls:
            video_arch = 'hunyuan_video'
        else:
            video_arch = 'minimax_h3'
    w = max(64, int(round(video_width / 32.0) * 32))
    h = max(64, int(round(video_height / 32.0) * 32))
    clean_full_prompt = str(timeline_prompt or '').strip()
    eff_user_scene_in = str(user_scene_input or '').strip() or clean_full_prompt
    tier_low_06 = str(rating_tier or '').strip().lower()
    if tier_low_06 == 'sfw':
        clean_full_prompt = _scrub_unrequested_genital_hallucinations(clean_full_prompt, '')
    elif tier_low_06 != 'nsfw_explicit':
        clean_full_prompt = _scrub_unrequested_genital_hallucinations(clean_full_prompt, eff_user_scene_in)
    is_vocal_scene = bool(str(motion_physics_mode or '').strip().lower().startswith('expressive_vocal')) or bool(reference_video_audio is not None) or bool(re.search(r'(?i)\b(?:suno\s+rhythmic|32khz\s+vocal\s+waveform|phoneme[-\s]?accurate\s+lip[-\s]?sync|studio\s+lead\s+vocals|expressive\s+singing|singing\s+expressively|vocal\s+envelope)\b', clean_full_prompt))
    resolved_physics_mode = resolve_effective_motion_physics_mode(motion_physics_mode, style_target=style_target, is_vocal_perf=is_vocal_scene)
    if resolved_physics_mode == 'expressive_vocal_mocap':
        is_vocal_scene = True
    if not is_vocal_scene:
        clean_full_prompt = _scrub_sfx_vocal_triggers(clean_full_prompt)
    eff_horizon_sec = resolve_effective_window_horizon_seconds(
        temporal_window_horizon=temporal_window_horizon,
        video_arch=video_arch,
        video_width=w,
        video_height=h,
        duration_seconds=eff_duration,
        timeline_prompt=clean_full_prompt,
        subject_stance_posture=subject_stance_posture,
        body_choreography_preset=body_choreography_preset,
        camera_trajectory_arc=camera_trajectory_arc,
        is_vocal_scene=is_vocal_scene,
        is_licensed=is_licensed,
    )
    pro_focus_seam_active = bool(is_licensed) and str(temporal_window_horizon or 'auto').strip().lower().startswith('auto')
    raw_frames = max(9, int(round(float(eff_duration) * float(frame_rate))))
    if video_arch == 'minimax_h3':
        total_frames = _snap_h3_native_frame_count(raw_frames)
        eff_overlap_t = 2 if int(overlap_frames) < 14 else 7
        ov_px = 5 if eff_overlap_t == 2 else 22
        win_5s_frames = _snap_h3_native_frame_count(max(73, int(round(float(eff_horizon_sec) * float(frame_rate)))))
        max_seg_frames = win_5s_frames
        num_macro_segments = max(1, int(math.ceil(float(total_frames - ov_px) / float(max(17, max_seg_frames - ov_px))))) if total_frames > max_seg_frames else 1
        seg_raw_frames = int(math.ceil(float(total_frames + (num_macro_segments - 1) * ov_px) / float(num_macro_segments))) if num_macro_segments > 1 else total_frames
        seg1_frames = min(max_seg_frames, _snap_h3_native_frame_count(max(22, seg_raw_frames)))
    else:
        total_frames = max(5, (raw_frames - 1) // 4 * 4 + 1)
        eff_overlap_t = max(2, min(5, max(2, (int(overlap_frames) + 3) // 4)))
        ov_px = (eff_overlap_t - 1) * 4 + 1
        win_5s_frames = max(81, int(round(5.0 * float(frame_rate))) // 4 * 4 + 1)
        max_seg_frames = win_5s_frames
        num_macro_segments = max(1, int(math.ceil(float(total_frames - 1) / float(max(1, max_seg_frames - 4))))) if total_frames > max_seg_frames else 1
        seg_raw_frames = int(math.ceil(float(total_frames + (num_macro_segments - 1) * 4) / float(num_macro_segments))) if num_macro_segments > 1 else total_frames
        seg1_frames = min(max_seg_frames + ov_px - 1, max(9, (seg_raw_frames - 1) // 4 * 4 + 1))
    latent_fmt = active_model.get_model_object('latent_format') if hasattr(active_model, 'get_model_object') else None
    sp_down = int(getattr(latent_fmt, 'spacial_downscale_ratio', 16 if video_arch in ('minimax_h3', 'wan22') else 8) or 16)
    latent_t = _h3_frames_to_video_tokens(seg1_frames) if video_arch == 'minimax_h3' else max(1, (seg1_frames - 1) // 4 + 1)
    latent_h = max(1, h // sp_down)
    latent_w = max(1, w // sp_down)
    act_prompts = _extract_chronological_shot_prompts(clean_full_prompt, num_windows=num_macro_segments, is_ref2va=bool(use_ref_model), is_vocal_override=is_vocal_scene, user_scene_input=eff_user_scene_in, allow_camera_movement=bool(allow_camera_movement), subject_stance_posture=subject_stance_posture)
    act_prompts = _apply_3axis_window_directives_to_acts(act_prompts, subject_stance_posture=subject_stance_posture, body_choreography_preset=body_choreography_preset, camera_trajectory_arc=camera_trajectory_arc)
    pro_speaker_routing = _analyze_pro_voice_and_scenecut_identity_routing(
        reference_motion_video,
        reference_video_audio,
        num_windows=num_macro_segments,
        duration_seconds=eff_duration,
        frame_rate=float(frame_rate or 24.0),
        is_licensed=is_licensed,
        has_second_person_ref=(ref_image_2_person is not None),
    )
    if pro_speaker_routing.get('active') and pro_speaker_routing.get('has_speaker_switches'):
        win_routes = pro_speaker_routing.get('windows', [])
        for w_info in win_routes:
            w_idx = int(w_info.get('window_idx', 0))
            if 0 <= w_idx < len(act_prompts) and int(w_info.get('speaker_id', 0)) == 1:
                act_prompts[w_idx] = (
                    act_prompts[w_idx]
                    .replace('<Picture 1>', '<Picture 2>')
                    .replace('<Subject 1>', '<Subject 2>')
                )
    if clean_full_prompt:
        clean_full_prompt = re.sub('(?i)following\\s+a\\s+(?:sudden\\s+cinematic\\s+smash|secondary\\s+rapid\\s+cinematic)\\s+cut\\s*,?', 'continuing seamlessly in the exact same continuous shot and lighting,', clean_full_prompt)
        clean_full_prompt = re.sub('(?i)\\b(?:smash\\s+cut|rapid\\s+cut|jump\\s+cut|hard\\s+cut|cuts?\\s+to)\\b', 'smoothly transitions within the same continuous camera framing and exposure', clean_full_prompt)
        if is_vocal_scene:
            clean_full_prompt = re.sub('(?i);?\\s*strictly\\s+no\\s+singing,?\\s*no\\s+vocals,?\\s*(?:no\\s+human\\s+voice,?\\s*)?(?:and\\s+)?no\\s+lyrics\\.?', '.', clean_full_prompt)
        else:
            clean_full_prompt = re.sub(r'(?i);?\s*(?:strictly\s+)?(?:zero|no)\s+(?:spoken\s+dialogue|human\s+voice|voiceover|narration|singing|background\s+music|instrumental\s+score|music|vocals)[^.\n]*\.?', '', clean_full_prompt)
    first_act_prompt = act_prompts[0] if (num_macro_segments > 1 and act_prompts) else (act_prompts[0] if act_prompts else clean_full_prompt)
    if has_extra_refs and video_arch == 'minimax_h3' and use_ref_model:
        ref_tags = []
        if keyframe_image is not None and '<picture 1>' not in first_act_prompt.lower():
            ref_tags.append('<Picture 1> defines the primary subject/keyframe')
        if ref_image_2_person is not None and '<picture 2>' not in first_act_prompt.lower():
            ref_tags.append('<Picture 2> defines the second person/character identity')
        if ref_image_3_clothing is not None and '<picture 3>' not in first_act_prompt.lower():
            ref_tags.append('<Picture 3> defines the clothing/outfit style')
        if ref_image_4_background is not None and '<picture 4>' not in first_act_prompt.lower():
            ref_tags.append('<Picture 4> defines the background environment and lighting')
        if ref_tags:
            first_act_prompt = f"{'; '.join(ref_tags)}.\n\n{first_act_prompt}".strip()
    positive_cond = None
    negative_cond = None
    base_latent = None
    first_frame_in = None
    r2_in = None
    r3_in = None
    r4_in = None
    h3_noise_mask = None
    pre_encoded_clip_cache = {}
    act_tensors = []

    def _prep_ref_img(img_t):
        if not _has_real_ref_pixels(img_t):
            return None
        nchw_r = img_t[:, :, :, :3].movedim(-1, 1)
        return comfy.utils.common_upscale(nchw_r, w, h, 'lanczos', 'center').movedim(1, -1).detach().cpu()

    def _sanitize_patchify_obj(val):
        if isinstance(val, torch.Tensor):
            t_cpu = val.detach().cpu()
            if t_cpu.ndim == 5 and t_cpu.shape[1] in (16, 24, 32, 48) and ((t_cpu.shape[-2] % 2 != 0) or (t_cpu.shape[-1] % 2 != 0)):
                import torch.nn.functional as F
                t_cpu = F.pad(t_cpu, (0, t_cpu.shape[-1] % 2, 0, t_cpu.shape[-2] % 2), mode='replicate')
            return t_cpu
        if isinstance(val, dict):
            return {k: _sanitize_patchify_obj(v) for (k, v) in val.items()}
        if isinstance(val, list):
            return [_sanitize_patchify_obj(x) for x in val]
        if isinstance(val, tuple):
            return tuple((_sanitize_patchify_obj(x) for x in val))
        return val

    def _offload_cond_list(c_list):
        if not isinstance(c_list, list):
            return c_list
        out_c = []
        for item in c_list:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                t0 = _sanitize_patchify_obj(item[0])
                m0 = _sanitize_patchify_obj(item[1]) if isinstance(item[1], dict) else item[1]
                out_c.append([t0, m0])
            else:
                out_c.append(_sanitize_patchify_obj(item))
        return out_c

    class _BatchPreEncodeClipWrapper:

        def __init__(self, real_clip, acts_list, neg_text, multi_segment: bool=False):
            self._real = real_clip
            self._acts = list(acts_list) if multi_segment else []
            self._neg_text = str(neg_text or '').strip()
            self._multi_seg = bool(multi_segment)
            self._last_text = ''
            self._last_tok_kwargs = {}
            self.act_cond_lists = []
            self.neg_cond_list = None
            self._did_batch = False

        def tokenize(self, text, **kwargs):
            self._last_text = str(text or '')
            self._last_tok_kwargs = dict(kwargs)
            return self._real.tokenize(text, **kwargs)

        def encode_from_tokens_scheduled(self, tokens, **kwargs):
            primary_out = _offload_cond_list(self._real.encode_from_tokens_scheduled(tokens, **kwargs))
            if not self._did_batch:
                self._did_batch = True
                self.act_cond_lists.append(primary_out)
                pre_encoded_clip_cache['__EZ_MASTER_KF_COND__'] = primary_out
                pre_encoded_clip_cache['__EZ_WIN_ACT_0__'] = primary_out
                pre_encoded_clip_cache[self._last_text] = primary_out
                if first_act_prompt:
                    pre_encoded_clip_cache[first_act_prompt] = primary_out
                if self._acts:
                    pre_encoded_clip_cache[self._acts[0]] = primary_out
                if self._multi_seg and len(self._acts) >= 2:
                    base_str = self._acts[0]
                    for (act_i, extra_act) in enumerate(self._acts[1:], start=1):
                        try:
                            if base_str and base_str in self._last_text:
                                cand_txt = self._last_text.replace(base_str, extra_act, 1)
                            else:
                                cand_txt = extra_act
                            if cand_txt == self._last_text or cand_txt in pre_encoded_clip_cache:
                                cached_enc = pre_encoded_clip_cache.get(cand_txt, primary_out)
                                self.act_cond_lists.append(cached_enc)
                                pre_encoded_clip_cache[f'__EZ_WIN_ACT_{act_i}__'] = cached_enc
                                pre_encoded_clip_cache[extra_act] = cached_enc
                                pre_encoded_clip_cache[cand_txt] = cached_enc
                                continue
                            extra_tok = self._real.tokenize(cand_txt, **self._last_tok_kwargs)
                            extra_enc = _offload_cond_list(self._real.encode_from_tokens_scheduled(extra_tok, **kwargs))
                            self.act_cond_lists.append(extra_enc)
                            pre_encoded_clip_cache[f'__EZ_WIN_ACT_{act_i}__'] = extra_enc
                            pre_encoded_clip_cache[extra_act] = extra_enc
                            pre_encoded_clip_cache[cand_txt] = extra_enc
                        except Exception:
                            pass
            return primary_out

        def __getattr__(self, name):
            return getattr(self._real, name)
    if keyframe_image is not None and (production_mode in ('I2VA', 'FL2VA', 'I2V', 'REF2VA') or has_extra_refs):
        first_frame_in = _prep_ref_img(keyframe_image)
    r2_in = _prep_ref_img(ref_image_2_person)
    r3_in = _prep_ref_img(ref_image_3_clothing)
    r4_in = _prep_ref_img(ref_image_4_background)
    if has_extra_refs and first_frame_in is None:
        try:
            from .engine_ez_04_cinematrix_krea2_sampler import _compose_multi_reference_canvas
            first_frame_in = _compose_multi_reference_canvas(first_frame_in, r2_in, r3_in, r4_in, target_w=w, target_h=h)
        except Exception:
            if first_frame_in is None:
                first_frame_in = r2_in if r2_in is not None else (r4_in if r4_in is not None else r3_in)
    anatomical_latent_zones = {}
    anat_src_img = keyframe_image if _has_real_ref_pixels(keyframe_image) else first_frame_in
    if isinstance(anat_src_img, torch.Tensor):
        try:
            from .engine_ez_04_cinematrix_krea2_sampler import compute_downscaled_latent_anatomy_zones
            anatomical_latent_zones = compute_downscaled_latent_anatomy_zones(anat_src_img, latent_h, latent_w)
        except Exception:
            anatomical_latent_zones = {}
    anat_face_crop = _prep_ref_img(anatomical_latent_zones.get('face_crop_bhwc')) if isinstance(anatomical_latent_zones, dict) else None
    anat_torso_crop = _prep_ref_img(anatomical_latent_zones.get('torso_crop_bhwc')) if isinstance(anatomical_latent_zones, dict) else None
    anat_pelvic_crop = _prep_ref_img(anatomical_latent_zones.get('pelvic_crop_bhwc')) if isinstance(anatomical_latent_zones, dict) else None
    has_dual_subj_dir = bool(re.search(r'(?i)(?:<\s*(?:main[_\s-]*)?subject\s*[2-9]\s*>|\bcharacter\s*2\b|\bgoblin\b|\binterview(?:ing|s|ed)?\b|\bco-?anchor\b|\bsenator\b|\btwo[-\s]?shot\b|\btwo\s+characters\b)', clean_full_prompt))
    co_star_right_crop = None
    lead_left_crop = None
    if has_dual_subj_dir and isinstance(first_frame_in, torch.Tensor) and first_frame_in.ndim == 4:
        try:
            (fh_c, fw_c) = (int(first_frame_in.shape[1]), int(first_frame_in.shape[2]))
            y0_c = max(0, int(round(fh_c * 0.04)))
            y1_c = min(fh_c, max(y0_c + 16, int(round(fh_c * 0.94))))
            rx0_c = max(0, int(round(fw_c * 0.48)))
            rx1_c = min(fw_c, max(rx0_c + 16, int(round(fw_c * 0.98))))
            lx0_c = max(0, int(round(fw_c * 0.02)))
            lx1_c = min(fw_c, max(lx0_c + 16, int(round(fw_c * 0.52))))
            co_star_right_crop = _prep_ref_img(first_frame_in[:1, y0_c:y1_c, rx0_c:rx1_c, :3])
            lead_left_crop = _prep_ref_img(first_frame_in[:1, y0_c:y1_c, lx0_c:lx1_c, :3])
        except Exception:
            co_star_right_crop = None
            lead_left_crop = None
    if has_dual_subj_dir and r2_in is None and co_star_right_crop is not None:
        r2_in = co_star_right_crop
    if has_dual_subj_dir and r3_in is None and lead_left_crop is not None:
        r3_in = lead_left_crop
    primary_anchor_in = first_frame_in if first_frame_in is not None else r2_in
    keyframe_relay_anchors = _synthesize_start_mid_end_keyframes(
        primary_anchor_in,
        reference_motion_video=reference_motion_video if (str(production_mode).upper() == 'FL2VA' and not has_dual_subj_dir) else None,
        anatomical_zones=anatomical_latent_zones,
        target_w=w,
        target_h=h,
        allow_camera_movement=bool(allow_camera_movement),
    )
    (win0_start_img, win0_mid_img, win0_end_img) = _resolve_window_fl2va_start_mid_end(
        keyframe_relay_anchors,
        seg_idx=0,
        total_wins=num_macro_segments,
        handoff_img=primary_anchor_in,
    )
    has_explicit_fl2va_end = bool(str(production_mode).upper() == 'FL2VA' and not has_dual_subj_dir and isinstance(reference_motion_video, torch.Tensor) and reference_motion_video.ndim == 4 and int(reference_motion_video.shape[0]) >= 3)
    batch_clip = _BatchPreEncodeClipWrapper(video_clip, act_prompts, negative_prompt, multi_segment=(num_macro_segments > 1))
    if video_arch == 'minimax_h3':
        try:
            from comfy_extras.nodes_minimax_h3 import MiniMaxH3ImageToVideo
            h3_res = None
            if use_ref_model and audio_vae is not None:
                try:
                    from comfy_extras.nodes_minimax_h3 import MiniMaxH3ReferenceToVideo
                    eff_r2 = r2_in if isinstance(r2_in, torch.Tensor) else anat_face_crop
                    eff_r3 = r3_in if isinstance(r3_in, torch.Tensor) else anat_torso_crop
                    eff_r4 = r4_in if isinstance(r4_in, torch.Tensor) else (anat_pelvic_crop if is_nsfw else None)
                    ref_list = [im for im in (first_frame_in, eff_r2, eff_r3, eff_r4) if isinstance(im, torch.Tensor) and im.ndim == 4]
                    ref_batch = torch.cat(ref_list, dim=0) if ref_list else None
                    h3_res = MiniMaxH3ReferenceToVideo.execute(batch_clip, video_vae, audio_vae, first_act_prompt, w, h, seg1_frames, 'match', ref_batch, None, None, None)
                    if h3_res is not None and video_model_ref2va is not None:
                        try:
                            from .engine_ez_05_cinematrix_video_lora_stack import materialize_deferred_ref2va_model
                            active_model = materialize_deferred_ref2va_model(video_model_ref2va)
                        except Exception:
                            active_model = video_model_ref2va
                except Exception:
                    h3_res = None
            if h3_res is None:
                if use_ref_model and video_model_fl2va is not None:
                    active_model = video_model_fl2va
                start_img = win0_start_img if win0_start_img is not None else primary_anchor_in
                use_dual_anchor = bool(has_explicit_fl2va_end)
                end_img_arg = (win0_end_img if win0_end_img is not None else start_img) if (start_img is not None and use_dual_anchor) else None
                h3_res = MiniMaxH3ImageToVideo.execute(batch_clip, video_vae, first_act_prompt, w, h, seg1_frames, start_img, end_img_arg)
            positive_cond = _offload_cond_list(h3_res[0])
            h3_lat_dict = h3_res[1]
            base_latent = h3_lat_dict['samples'] if isinstance(h3_lat_dict, dict) and 'samples' in h3_lat_dict else h3_lat_dict
            if isinstance(h3_lat_dict, dict) and 'noise_mask' in h3_lat_dict:
                h3_noise_mask = h3_lat_dict['noise_mask']
                if isinstance(h3_noise_mask, torch.Tensor) and h3_noise_mask.ndim == 5 and int(h3_noise_mask.shape[2]) >= 3 and end_img_arg is not None:
                    h3_noise_mask = h3_noise_mask.clone()
                    end_min_noise = 0.28 if has_explicit_fl2va_end else 0.45
                    h3_noise_mask[:, :, -1:, :, :] = torch.clamp(h3_noise_mask[:, :, -1:, :, :], min=end_min_noise)
            negative_cond = [[torch.zeros_like(t[0]), dict(t[1])] for t in positive_cond]
            for enc_act in batch_clip.act_cond_lists:
                if isinstance(enc_act, list) and len(enc_act) > 0 and isinstance(enc_act[0][0], torch.Tensor):
                    act_tensors.append(enc_act[0][0].detach().cpu())
        except Exception:
            positive_cond = None
            negative_cond = None
            base_latent = None
    elif video_arch in ('wan22', 'wan21'):
        try:
            pos_tokens = batch_clip.tokenize(first_act_prompt)
            pos_raw = _offload_cond_list(batch_clip.encode_from_tokens_scheduled(pos_tokens))
            neg_tokens = video_clip.tokenize(str(negative_prompt or ''))
            neg_raw = _offload_cond_list(video_clip.encode_from_tokens_scheduled(neg_tokens))
            import comfy_extras.nodes_wan as nodes_wan
            if video_arch == 'wan22' and hasattr(nodes_wan, 'Wan22ImageToVideoLatent'):
                wan_lat_res = nodes_wan.Wan22ImageToVideoLatent.execute(video_vae, w, h, seg1_frames, 1, first_frame_in)
                w_dict = wan_lat_res[0]
                positive_cond = pos_raw
                negative_cond = neg_raw
                base_latent = w_dict['samples']
                h3_noise_mask = w_dict.get('noise_mask')
            elif hasattr(nodes_wan, 'WanImageToVideo'):
                wan_end_arg = win0_end_img if has_explicit_fl2va_end else None
                wan_res = nodes_wan.WanImageToVideo.execute(pos_raw, neg_raw, video_vae, w, h, seg1_frames, 1, first_frame_in, wan_end_arg)
                positive_cond = _offload_cond_list(wan_res[0])
                negative_cond = _offload_cond_list(wan_res[1])
                w_dict = wan_res[2]
                base_latent = w_dict['samples'] if isinstance(w_dict, dict) and 'samples' in w_dict else w_dict
                h3_noise_mask = w_dict.get('noise_mask') if isinstance(w_dict, dict) else None
            for enc_act in batch_clip.act_cond_lists:
                if isinstance(enc_act, list) and len(enc_act) > 0 and isinstance(enc_act[0][0], torch.Tensor):
                    act_tensors.append(enc_act[0][0].detach().cpu())
        except Exception:
            positive_cond = None
            negative_cond = None
            base_latent = None
    if positive_cond is None or negative_cond is None or base_latent is None:
        pos_tokens = batch_clip.tokenize(first_act_prompt)
        positive_cond = _offload_cond_list(batch_clip.encode_from_tokens_scheduled(pos_tokens))
        if str(negative_prompt or '').strip() and video_arch != 'minimax_h3':
            neg_tokens = video_clip.tokenize(str(negative_prompt))
            negative_cond = _offload_cond_list(video_clip.encode_from_tokens_scheduled(neg_tokens))
        else:
            negative_cond = [[torch.zeros_like(t[0]), dict(t[1])] for t in positive_cond]
        pre_encoded_clip_cache[first_act_prompt] = positive_cond
        latent_ch = int(getattr(latent_fmt, 'latent_channels', getattr(video_vae, 'latent_channels', 16 if video_arch in ('wan21', 'hunyuan_video') else 48 if video_arch == 'wan22' else 24)))
        fsm = getattr(video_vae, 'first_stage_model', None)
        if hasattr(fsm, 'latents_mean') and getattr(fsm.latents_mean, 'ndim', 0) >= 2:
            latent_ch = int(fsm.latents_mean.shape[1])
        base_latent = torch.zeros((1, latent_ch, latent_t, latent_h, latent_w), dtype=torch.float32, device='cpu')
        if first_frame_in is not None and production_mode in ('I2VA', 'FL2VA', 'I2V', 'REF2VA'):
            try:
                try:
                    encoded_kf = video_vae.encode(first_frame_in).detach().cpu()
                except Exception:
                    if aggressive_purge:
                        comfy.model_management.soft_empty_cache()
                    encoded_kf = video_vae.encode_tiled(first_frame_in, tile_x=tile_sz, tile_y=tile_sz).detach().cpu()
                if encoded_kf.ndim == 4:
                    encoded_kf = encoded_kf.unsqueeze(2)
                ch = min(base_latent.shape[1], encoded_kf.shape[1])
                t_copy = min(base_latent.shape[2], encoded_kf.shape[2])
                base_latent[:, :ch, :t_copy, :, :] = encoded_kf[:, :ch, :t_copy, :latent_h, :latent_w]
                h3_noise_mask = torch.ones((1, 1, latent_t, 1, 1), dtype=torch.float32, device='cpu')
                h3_noise_mask[:, :, :t_copy, :, :] = 0.0
            except Exception:
                pass
    (positive_cond, negative_cond) = project_video_kinematic_conditioning(video_clip, positive_cond, negative_cond, resolved_physics_mode, is_nsfw=is_nsfw, video_arch=video_arch, motion_strength=float(motion_transfer_strength))
    total_latent_t = _h3_frames_to_video_tokens(total_frames) if video_arch == 'minimax_h3' else max(1, (total_frames - 1) // 4 + 1)
    mocap_latent_deltas = _extract_latent_motion_capture_deltas(reference_motion_video, video_vae, w, h, total_latent_t, tile_sz=tile_sz, target_first_frame=first_frame_in, slot5_focus_mode=slot5_focus_mode)
    if video_arch == 'minimax_h3':
        try:
            from comfy.nested_tensor import NestedTensor
            t_existing = list(base_latent.tensors) if hasattr(base_latent, 'tensors') else ([base_latent] if isinstance(base_latent, torch.Tensor) else [])
            if len(t_existing) == 1 and isinstance(t_existing[0], torch.Tensor):
                vid_5d = t_existing[0]
                aud_t_len = _h3_frames_to_audio_tokens(seg1_frames, frame_rate)
                aud_4d = torch.zeros((int(vid_5d.shape[0]), 32, 2, aud_t_len), dtype=vid_5d.dtype, device=vid_5d.device)
                base_latent = NestedTensor([vid_5d, aud_4d])
                if isinstance(h3_noise_mask, torch.Tensor):
                    am_4d = torch.ones((int(vid_5d.shape[0]), 1, 1, aud_t_len), dtype=h3_noise_mask.dtype, device=h3_noise_mask.device)
                    h3_noise_mask = NestedTensor([h3_noise_mask, am_4d])
        except Exception:
            pass
    try:
        if len(act_tensors) > 0 and '' not in pre_encoded_clip_cache:
            pre_encoded_clip_cache[''] = [[torch.zeros_like(act_tensors[0]), {}]]
        if len(act_tensors) >= 2 and isinstance(positive_cond, list) and (len(positive_cond) > 0) and (len(positive_cond[0]) > 1) and isinstance(positive_cond[0][1], dict):
            positive_cond[0][1]['ez_chronological_act_tensors'] = act_tensors
    except Exception:
        pass
    if aggressive_purge or not bool(prof.get('persistent_vram_weights', False)):
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
    s_kf_out = keyframe_relay_anchors[0] if len(keyframe_relay_anchors) >= 1 else first_frame_in
    m_kf_out = keyframe_relay_anchors[1] if len(keyframe_relay_anchors) >= 2 else s_kf_out
    e_kf_out = keyframe_relay_anchors[2] if len(keyframe_relay_anchors) >= 3 else s_kf_out
    is_crowd_mode = any(str(subject_stance_posture or '').strip().lower().startswith(k) for k in ('standing_social', 'epic_battlefield', 'nsfw_threesome', 'nsfw_orgy'))
    cont_ctx = {'video_arch': video_arch, 'video_clip': video_clip, 'video_vae': video_vae, 'audio_vae': audio_vae, 'width': int(w), 'height': int(h), 'frame_rate': float(frame_rate), 'production_mode': str(production_mode), 'has_explicit_fl2va_end': bool(has_explicit_fl2va_end), 'act_prompts': list(act_prompts), 'sanitizer_version': 'v20_pose_neutral_zero_legacy_traps', 'timeline_prompt': str(clean_full_prompt or first_act_prompt or ''), 'raw_timeline_prompt': str(timeline_prompt or ''), 'user_scene_input': str(eff_user_scene_in), 'rating_tier': str(rating_tier or 'uncensored_action'), 'negative_prompt': str(negative_prompt or ''), 'tile_size': int(tile_sz), 'first_frame_in': first_frame_in, 'start_keyframe': s_kf_out, 'mid_keyframe': m_kf_out, 'end_keyframe': e_kf_out, 'r2_in': r2_in, 'r3_in': r3_in, 'r4_in': r4_in, 'anat_face_crop': anat_face_crop, 'anat_torso_crop': anat_torso_crop, 'anat_pelvic_crop': anat_pelvic_crop if is_nsfw else None, 'keyframe_relay_anchors': keyframe_relay_anchors, 'pre_encoded_clip_cache': pre_encoded_clip_cache, 'num_macro_segments': int(num_macro_segments), 'macro_segment_frames': int(seg1_frames), 'total_target_frames': int(total_frames), 'window_horizon_seconds': float(eff_horizon_sec), 'temporal_window_horizon': str(temporal_window_horizon), 'pro_focus_seam_active': bool(pro_focus_seam_active), 'motion_physics_mode': resolved_physics_mode, 'motion_transfer_strength': float(motion_transfer_strength), 'mocap_latent_deltas': mocap_latent_deltas, 'anatomical_latent_zones': anatomical_latent_zones, 'pro_speaker_routing': pro_speaker_routing, 'is_nsfw': bool(is_nsfw), 'is_vocal_scene': bool(is_vocal_scene), 'allow_camera_movement': bool(allow_camera_movement), 'subject_stance_posture': str(subject_stance_posture), 'body_choreography_preset': str(body_choreography_preset), 'camera_trajectory_arc': str(camera_trajectory_arc), 'is_multi_subject_crowd': bool(is_crowd_mode)}
    latent_dict = {'samples': base_latent, 'overlap_frames': int(overlap_frames), 'total_frames': int(total_frames), 'frame_rate': float(frame_rate), 'production_mode': production_mode, 'hardware_tier_profile': prof, 'window_horizon_seconds': float(eff_horizon_sec), 'temporal_window_horizon': str(temporal_window_horizon), 'pro_focus_seam_active': bool(pro_focus_seam_active), 'motion_physics_mode': resolved_physics_mode, 'motion_transfer_strength': float(motion_transfer_strength), 'mocap_latent_deltas': mocap_latent_deltas, 'anatomical_latent_zones': anatomical_latent_zones, 'pro_speaker_routing': pro_speaker_routing, 'is_vocal_scene': bool(is_vocal_scene), 'allow_camera_movement': bool(allow_camera_movement), 'subject_stance_posture': str(subject_stance_posture), 'body_choreography_preset': str(body_choreography_preset), 'camera_trajectory_arc': str(camera_trajectory_arc), 'is_multi_subject_crowd': bool(is_crowd_mode), 'ez_continuation_ctx': cont_ctx}
    if h3_noise_mask is not None:
        latent_dict['noise_mask'] = h3_noise_mask
    return (active_model, positive_cond, negative_cond, latent_dict, float(frame_rate))
