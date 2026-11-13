# -*- coding: utf-8 -*-

import os
import re
import math
from pathlib import Path
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image, ImageOps, ImageDraw
import folder_paths
import comfy.utils
import comfy.model_management
from .engine_ez_04_cinematrix_krea2_sampler import (
    _gaussian_blur_2d,
    _capsule_sdf_2d,
    _detect_skeletal_keypoints_rcnn,
    _compute_neural_anatomy_zones,
)

SLOT1_FOCUS_MODES = [
    'IP_Adapter_Advanced + ControlNet_Tile + TemporalNet (Optimal Hybrid)',
    'ControlNet_OpenPose_17Joint + Canny + Lineart (Pose & Structural Lock)',
    'ControlNet_Inpaint_Masked + Outpaint_Feather (Region Inpainting)',
    'TemporalNet + AdvancedLivePortrait_Driver (Motion & Micro-Expression Lock)',
    'LayerDiffusion_RGBA_Foreground (Transparent Alpha Matte)',
]

SLOT1_INPAINT_MODES = [
    'Disabled_Full_Canvas',
    'Auto_Alpha_Or_Subject_Mask',
    'Keep_Subject_Inpaint_Background',
    'Inpaint_Subject_Keep_Background',
    'Center_Box_Inpaint',
]

SLOT2_FOCUS_MODES = [
    'ReActor_FaceID + ADetailer_Face_Pass + AdvancedLivePortrait (Optimal Hybrid)',
    'IP_Adapter_FaceID_PlusV2 + LAB_Chrominance_Lock (Strict Identity)',
    'ADetailer_Anatomy_And_Eyes_Enhancer (High-Freq Facial Detailer)',
    'Dual_Subject_SideBySide_Interaction (Two-Person Scene Composite)',
]

SLOT3_FOCUS_MODES = [
    'OOTDiffusion_OpenOutfitting + LayerDiffusion_Alpha_Matte (Optimal Hybrid)',
    'OOTDiffusion_Skeletal_Torso_Warp (Keypoint-Aligned Virtual Try-On)',
    'IP_Adapter_Advanced_Fabric_And_Weave (Material & Pattern Transfer)',
    'LayerDiffusion_Direct_Garment_Overlay (Alpha-Segmented Composite)',
]

SLOT4_FOCUS_MODES = [
    'DepthAnything_MiDaS_3D + ControlNet_Tile + LayerDiffusion_Plate (Optimal Hybrid)',
    'DepthAnything_V2_Structural_Depth_Lock (3D Perspective & Horizon)',
    'ControlNet_Tile_Environment_Relight (Ambient Color & Lighting Harmony)',
    'AnimateDiff_Temporal_Background_Anchor (Zero-Flicker Static Stage)',
]

SLOT5_FOCUS_MODES = [
    'Latent_3DVAE_Motion_Capture + RCNN_Centroid_Align (Optimal MoCap)',
    'Full_Body_Choreography_And_Camera_Trajectory (Strict Motion Lock)',
    'Facial_And_Vocal_Micro_Articulation (Lip-Sync & Head Motion)',
    'Extract_Keyframe_From_First_Video_Frame_Only (Static Pose Seed)',
]

SLOT5_DURATION_MODES = [
    'follow_master_duration (Följ Master-Tidslängd [02] / [06] — Auto)',
    'match_full_reference_video (Matcha Hela Referensvideons Längd)',
    '5-second (5s Referens-Klipp)',
    '10-second (10s Referens-Klipp)',
    '15-second (15s Referens-Klipp)',
    '20-second (20s Referens-Klipp)',
    '30-second (30s Referens-Klipp)',
    '45-second (45s Referens-Klipp)',
    '60-second (60s Referens-Klipp)',
    '120-second (120s Referens-Klipp)',
    'custom_seconds (Använd Egen Tid i Sekunder nedan)',
]


def resolve_slot5_target_duration_seconds(slot5_duration_mode: str = '', slot5_duration_seconds: float = 0.0, bus_duration_sec: float = 0.0) -> tuple:
    mode_low = str(slot5_duration_mode or SLOT5_DURATION_MODES[0]).strip().lower()
    raw_sec = float(slot5_duration_seconds or 0.0)
    if math.isclose(raw_sec, 97.0) and not mode_low.startswith('custom_seconds'):
        raw_sec = 0.0
    if mode_low.startswith('match_full'):
        return (0.0, False, True)
    m_num = re.match(r'^(\d+(?:\.\d+)?)\s*-\s*second', mode_low)
    if m_num:
        return (max(1.0, float(m_num.group(1))), False, False)
    if mode_low.startswith('custom_seconds'):
        return (max(1.0, raw_sec if raw_sec > 0.5 else (float(bus_duration_sec) if float(bus_duration_sec or 0.0) > 0.5 else 20.0)), False, False)
    if raw_sec > 0.5:
        return (raw_sec, False, False)
    return (max(0.0, float(bus_duration_sec or 0.0)), True, False)


def list_comfy_input_images(include_none: bool = True):
    register_omni_reference_promptserver_routes()
    img_exts = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif')
    files = []
    seen = set()
    try:
        in_dir = folder_paths.get_input_directory()
        for (root, dirs, fnames) in os.walk(in_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d.lower() not in ('3d', '__pycache__')]
            for fname in fnames:
                if fname.lower().endswith(img_exts):
                    rel_p = os.path.relpath(os.path.join(root, fname), in_dir).replace('\\', '/')
                    if rel_p not in seen:
                        seen.add(rel_p)
                        files.append(rel_p)
    except Exception:
        files = []
    sorted_files = sorted(files)
    if include_none:
        return ['None'] + sorted_files
    return sorted_files if sorted_files else ['None']


def _ensure_unlimited_comfy_upload_size():
    try:
        import server
        ps = getattr(server, 'PromptServer', None)
        inst = getattr(ps, 'instance', None) if ps is not None else None
        app_obj = getattr(inst, 'app', None) if inst is not None else None
        if app_obj is not None:
            ten_gb = 10 * 1024 * 1024 * 1024
            if int(getattr(app_obj, '_client_max_size', 0) or 0) < ten_gb:
                app_obj._client_max_size = ten_gb
    except Exception:
        pass


def register_omni_reference_promptserver_routes():
    try:
        from aiohttp import web
        import server
        ps_cls = getattr(server, 'PromptServer', None)
        ps = getattr(ps_cls, 'instance', None) if ps_cls is not None else None
        if ps is None or getattr(ps, '_ez_omni_ref_routes_registered', False):
            return
        ps._ez_omni_ref_routes_registered = True

        async def _ez_omni_media_list(_request):
            return web.json_response({
                'status': 'ok',
                'images': list_comfy_input_images(include_none=True),
                'videos': list_comfy_input_videos(include_none=True),
            })

        for prefix in ('/ez_cinematrix/omni_ref', '/api/ez_cinematrix/omni_ref'):
            ps.routes.get(f'{prefix}/media_list')(_ez_omni_media_list)
    except Exception:
        pass


_ensure_unlimited_comfy_upload_size()
register_omni_reference_promptserver_routes()


def list_comfy_input_videos(include_none: bool = True):
    _ensure_unlimited_comfy_upload_size()
    vid_exts = ('.mp4', '.mkv', '.webp', '.mov', '.webm', '.avi', '.gif')
    files = []
    seen = set()
    try:
        in_dir = folder_paths.get_input_directory()
        for (root, _dirs, fnames) in os.walk(in_dir):
            for fname in fnames:
                if fname.lower().endswith(vid_exts):
                    rel_p = os.path.relpath(os.path.join(root, fname), in_dir).replace('\\', '/')
                    if rel_p not in seen:
                        seen.add(rel_p)
                        files.append(rel_p)
    except Exception:
        pass
    try:
        out_dir = folder_paths.get_output_directory()
        for (root, _dirs, fnames) in os.walk(out_dir):
            for fname in fnames:
                if fname.lower().endswith(vid_exts):
                    rel_p = os.path.relpath(os.path.join(root, fname), out_dir).replace('\\', '/')
                    tagged = f'{rel_p} [output]'
                    if tagged not in seen:
                        seen.add(tagged)
                        files.append(tagged)
    except Exception:
        pass
    sorted_files = sorted(files)
    if include_none:
        return ['None'] + sorted_files
    return sorted_files if sorted_files else ['None']


def _resolve_slot5_video_filepath(file_choice: str) -> str:
    choice = str(file_choice or '').strip()
    if not choice or choice == 'None':
        return ''
    try:
        vid_path = folder_paths.get_annotated_filepath(choice)
        if vid_path and os.path.isfile(vid_path):
            return vid_path
    except Exception:
        pass
    tag_match = re.search(r'\s+\[(input|output|temp)\]$', choice, flags=re.IGNORECASE)
    clean_rel = choice[:tag_match.start()].strip() if tag_match else choice
    tag_type = tag_match.group(1).lower() if tag_match else 'input'
    search_roots = []
    try:
        if tag_type == 'output':
            search_roots.append(folder_paths.get_output_directory())
        elif tag_type == 'temp':
            search_roots.append(folder_paths.get_temp_directory())
        search_roots.append(folder_paths.get_input_directory())
        search_roots.append(folder_paths.get_output_directory())
    except Exception:
        pass
    for r_dir in search_roots:
        if r_dir:
            cand = os.path.join(r_dir, clean_rel)
            if os.path.isfile(cand):
                return cand
    return choice if os.path.isfile(choice) else ''


def load_video_frames_from_slot(file_choice: str, opt_video: torch.Tensor = None, max_frames: int = 0, target_w: int = 768, target_h: int = 512, start_offset_sec: float = 0.0, target_duration_sec: float = 0.0):
    offset_s = max(0.0, float(start_offset_sec or 0.0))
    req_dur_s = max(0.0, float(target_duration_sec or 0.0))
    is_auto_req = int(max_frames or 0) <= 0 or int(max_frames) == 97
    eff_cap_init = min(481, max(97, int(round((req_dur_s if req_dur_s > 0.5 else 20.0) * 4.8)) + 1)) if is_auto_req else max(2, int(max_frames))
    if isinstance(opt_video, torch.Tensor) and opt_video.ndim == 4 and int(opt_video.shape[0]) >= 2 and float(opt_video.detach().abs().max().item()) > 1e-04:
        v = torch.clamp(opt_video.detach().cpu().float()[:, :, :, :3], 0.0, 1.0)
        if offset_s > 0.0:
            skip_n = min(max(0, int(v.shape[0]) - 2), int(round(offset_s * 24.0)))
            v = v[skip_n:]
        if req_dur_s > 0.5:
            keep_n = max(2, int(round(req_dur_s * 24.0)))
            v = v[:keep_n]
        cap_v = min(481, max(97, int(v.shape[0]))) if is_auto_req else eff_cap_init
        if int(v.shape[0]) > int(cap_v):
            idx = torch.linspace(0, int(v.shape[0]) - 1, steps=int(cap_v)).long()
            v = v.index_select(0, idx)
        return v, ''
    vid_path = _resolve_slot5_video_filepath(file_choice)
    if not vid_path or not os.path.isfile(vid_path):
        return None, ''
    try:
        frames_rgb = []
        cap_lim = eff_cap_init
        try:
            import av
            with av.open(vid_path) as container:
                v_stream = next((s for s in container.streams if s.type == 'video'), None)
                if v_stream is not None:
                    v_stream.thread_type = 'AUTO'
                    fps_est = float(getattr(v_stream, 'average_rate', None) or getattr(v_stream, 'base_rate', None) or 24.0)
                    vid_dur_s = float(v_stream.duration * v_stream.time_base) if (v_stream.duration is not None and v_stream.time_base is not None) else (float(container.duration) / 1000000.0 if getattr(container, 'duration', None) else 0.0)
                    rem_dur_s = max(5.0, vid_dur_s - offset_s) if vid_dur_s > offset_s else 60.0
                    span_s = req_dur_s if req_dur_s > 0.5 else min(180.0, rem_dur_s)
                    if is_auto_req:
                        cap_lim = min(481, max(25, int(round(span_s * 4.8)) + 1))
                    if offset_s > 0.0 and v_stream.time_base is not None:
                        try:
                            seek_ts = int(offset_s / float(v_stream.time_base))
                            container.seek(seek_ts, stream=v_stream, backward=True, any_frame=False)
                        except Exception:
                            pass
                    raw_pil = []
                    max_decode_span = max(cap_lim * 4, int(round(span_s * max(24.0, fps_est))), 720)
                    end_time_s = (offset_s + req_dur_s + 0.05) if req_dur_s > 0.5 else (offset_s + span_s + 0.5)
                    for (f_idx, frame) in enumerate(container.decode(v_stream)):
                        f_time = float(frame.pts * v_stream.time_base) if (frame.pts is not None and v_stream.time_base is not None) else (float(f_idx) / max(1.0, fps_est))
                        if f_time + 1e-03 < offset_s:
                            continue
                        if f_time > end_time_s and len(raw_pil) >= 2:
                            break
                        p_im = frame.to_image().convert('RGB')
                        if p_im.size != (int(target_w), int(target_h)):
                            p_im = p_im.resize((int(target_w), int(target_h)), Image.Resampling.BILINEAR)
                        raw_pil.append(p_im)
                        if len(raw_pil) >= max_decode_span:
                            break
                    if len(raw_pil) > cap_lim:
                        step_idx = np.linspace(0, len(raw_pil) - 1, num=cap_lim, dtype=int)
                        raw_pil = [raw_pil[i] for i in step_idx]
                    for p_im in raw_pil:
                        frames_rgb.append(np.asarray(p_im, dtype=np.float32) / 255.0)
        except Exception:
            frames_rgb = []
        if not frames_rgb and vid_path.lower().endswith(('.gif', '.webp')):
            from PIL import ImageSequence
            with Image.open(vid_path) as im_seq:
                elapsed_ms = 0.0
                target_ms = offset_s * 1000.0
                max_ms = (offset_s + req_dur_s) * 1000.0 if req_dur_s > 0.5 else (offset_s + 180.0) * 1000.0
                for page in ImageSequence.Iterator(im_seq):
                    dur_ms = float(page.info.get('duration', 42.0) or 42.0)
                    if elapsed_ms + dur_ms < target_ms:
                        elapsed_ms += dur_ms
                        continue
                    if elapsed_ms > max_ms and len(frames_rgb) >= 2:
                        break
                    elapsed_ms += dur_ms
                    p_im = page.convert('RGB').resize((int(target_w), int(target_h)), Image.Resampling.BILINEAR)
                    frames_rgb.append(np.asarray(p_im, dtype=np.float32) / 255.0)
                    if len(frames_rgb) >= cap_lim:
                        break
                if len(frames_rgb) == 1:
                    frames_rgb.append(frames_rgb[0].copy())
        if len(frames_rgb) >= 2:
            vid_t = torch.from_numpy(np.stack(frames_rgb, axis=0)).float()
            return torch.clamp(vid_t, 0.0, 1.0), vid_path
    except Exception:
        pass
    return None, ''


def extract_audio_from_video_path(vid_path: str, start_offset_sec: float = 0.0, max_duration_sec: float = 600.0):
    if not vid_path or not os.path.isfile(str(vid_path)):
        return None
    offset_s = max(0.0, float(start_offset_sec or 0.0))
    max_dur_s = max(5.0, float(max_duration_sec or 600.0))
    try:
        import av
        with av.open(str(vid_path)) as container:
            a_stream = next((s for s in container.streams if s.type == 'audio'), None)
            if a_stream is None:
                return None
            sr = int(getattr(a_stream, 'sample_rate', 0) or getattr(a_stream.codec_context, 'sample_rate', 0) or 44100)
            if offset_s > 0.5 and a_stream.time_base is not None:
                try:
                    seek_a_ts = int(max(0.0, offset_s - 0.25) / float(a_stream.time_base))
                    container.seek(seek_a_ts, stream=a_stream, backward=True, any_frame=False)
                except Exception:
                    pass
            resampler = av.AudioResampler(format='fltp', layout='stereo', rate=sr)
            chunks = []
            collected_samples = 0
            max_samples = int(round((max_dur_s + 2.0) * float(sr)))
            skipped_pre_samples = 0
            seek_applied = False
            for frame in container.decode(a_stream):
                if frame.pts is not None and a_stream.time_base is not None:
                    f_end_sec = float(frame.pts * a_stream.time_base) + (float(frame.samples) / max(1.0, float(sr)))
                    if f_end_sec < offset_s:
                        seek_applied = True
                        continue
                out_frames = resampler.resample(frame)
                if not isinstance(out_frames, (list, tuple)):
                    out_frames = [out_frames] if out_frames is not None else []
                for of in out_frames:
                    if of is not None:
                        arr = of.to_ndarray()
                        if arr.ndim == 1:
                            arr = arr[None, :]
                        arr_f32 = arr.astype(np.float32, copy=False)
                        chunks.append(arr_f32)
                        collected_samples += int(arr_f32.shape[-1])
                if seek_applied and collected_samples >= max_samples:
                    break
                if (not seek_applied) and collected_samples >= int(round(offset_s * float(sr))) + max_samples:
                    break
            if not chunks:
                return None
            wav_np = np.concatenate(chunks, axis=-1)
            if (not seek_applied) and offset_s > 0.0:
                start_samp = int(round(offset_s * float(sr)))
                if 0 < start_samp < wav_np.shape[-1]:
                    wav_np = wav_np[:, start_samp:]
            if wav_np.shape[-1] > max_samples:
                wav_np = wav_np[:, :max_samples]
            wav_t = torch.from_numpy(wav_np).float().unsqueeze(0)
            if float(wav_t.abs().max().item()) <= 1e-05:
                return None
            return {'waveform': wav_t, 'sample_rate': sr, 'start_offset_sec': offset_s}
    except Exception:
        return None


def load_image_and_alpha_from_slot(file_choice: str, opt_tensor: torch.Tensor = None, opt_mask: torch.Tensor = None):
    if isinstance(opt_tensor, torch.Tensor) and opt_tensor.ndim >= 3 and float(opt_tensor.detach().abs().max().item()) > 1e-04:
        t = opt_tensor.detach().cpu().float()
        if t.ndim == 3:
            t = t.unsqueeze(0)
        rgb = torch.clamp(t[:1, :, :, :3], 0.0, 1.0)
        h, w = int(rgb.shape[1]), int(rgb.shape[2])
        if isinstance(opt_mask, torch.Tensor) and opt_mask.ndim >= 2:
            m = opt_mask.detach().cpu().float()
            if m.ndim == 2:
                m = m.unsqueeze(0)
            if int(m.shape[-2]) != h or int(m.shape[-1]) != w:
                m = F.interpolate(m.unsqueeze(1), size=(h, w), mode='bilinear', align_corners=False).squeeze(1)
            alpha = torch.clamp(1.0 - m[:1], 0.0, 1.0)
            has_alpha = True
        elif int(t.shape[-1]) == 4:
            alpha = torch.clamp(t[:1, :, :, 3], 0.0, 1.0)
            has_alpha = True
        else:
            alpha = torch.ones((1, h, w), dtype=torch.float32)
            has_alpha = False
        return rgb, alpha, has_alpha

    choice = str(file_choice or '').strip()
    if not choice or choice == 'None':
        return None, None, False
    try:
        img_path = ''
        try:
            cand_ann = folder_paths.get_annotated_filepath(choice)
            if cand_ann and os.path.isfile(cand_ann):
                img_path = cand_ann
        except Exception:
            img_path = ''
        if not img_path or not os.path.isfile(img_path):
            tag_m = re.search(r'\s+\[(input|output|temp)\]$', choice, flags=re.IGNORECASE)
            clean_rel = choice[:tag_m.start()].strip() if tag_m else choice
            tag_kind = tag_m.group(1).lower() if tag_m else 'input'
            roots = []
            if tag_kind == 'output':
                roots.append(folder_paths.get_output_directory())
            elif tag_kind == 'temp':
                roots.append(folder_paths.get_temp_directory())
            roots.append(folder_paths.get_input_directory())
            for r_dir in roots:
                if r_dir:
                    cand = os.path.join(r_dir, clean_rel)
                    if os.path.isfile(cand):
                        img_path = cand
                        break
        if not img_path or not os.path.isfile(img_path):
            return None, None, False
        pil_img = ImageOps.exif_transpose(Image.open(img_path))
        has_alpha = 'A' in pil_img.getbands()
        rgb_np = np.array(pil_img.convert('RGB')).astype(np.float32) / 255.0
        rgb_t = torch.from_numpy(rgb_np)[None,]
        h, w = int(rgb_t.shape[1]), int(rgb_t.shape[2])
        if isinstance(opt_mask, torch.Tensor) and opt_mask.ndim >= 2:
            m = opt_mask.detach().cpu().float()
            if m.ndim == 2:
                m = m.unsqueeze(0)
            if int(m.shape[-2]) != h or int(m.shape[-1]) != w:
                m = F.interpolate(m.unsqueeze(1), size=(h, w), mode='bilinear', align_corners=False).squeeze(1)
            alpha_t = torch.clamp(1.0 - m[:1], 0.0, 1.0)
            has_alpha = True
        elif has_alpha:
            a_np = np.array(pil_img.getchannel('A')).astype(np.float32) / 255.0
            alpha_t = torch.from_numpy(a_np)[None,]
        else:
            alpha_t = torch.ones((1, h, w), dtype=torch.float32)
        return torch.clamp(rgb_t, 0.0, 1.0), torch.clamp(alpha_t, 0.0, 1.0), bool(has_alpha)
    except Exception:
        return None, None, False


def resize_bhwc(img_bhwc: torch.Tensor, target_w: int, target_h: int) -> torch.Tensor:
    if not isinstance(img_bhwc, torch.Tensor) or img_bhwc.ndim != 4:
        return torch.zeros((1, target_h, target_w, 3), dtype=torch.float32)
    if int(img_bhwc.shape[1]) == int(target_h) and int(img_bhwc.shape[2]) == int(target_w):
        return img_bhwc.clone()
    bchw = img_bhwc.movedim(-1, 1).contiguous()
    up = comfy.utils.common_upscale(bchw, int(target_w), int(target_h), 'lanczos', 'center')
    return torch.clamp(up.movedim(1, -1).contiguous(), 0.0, 1.0)


def extract_layerdiffusion_foreground_alpha(img_bchw: torch.Tensor, raw_alpha_bhw: torch.Tensor = None, has_explicit_alpha: bool = False, feather_radius: float = 4.0) -> torch.Tensor:
    _, _, h, w = img_bchw.shape
    dev = img_bchw.device
    if has_explicit_alpha and isinstance(raw_alpha_bhw, torch.Tensor):
        a = raw_alpha_bhw.to(device=dev, dtype=torch.float32)
        if a.ndim == 3:
            a = a.unsqueeze(1)
        if int(a.shape[2]) != h or int(a.shape[3]) != w:
            a = F.interpolate(a, size=(h, w), mode='bilinear', align_corners=False)
        if float(a.std().item()) > 0.02:
            return _gaussian_blur_2d(torch.clamp(a, 0.0, 1.0), max(0.5, float(feather_radius) * 0.4))

    b_sz = max(2, min(h, w) // 16)
    top_s = img_bchw[:, :, :b_sz, :].mean(dim=(2, 3), keepdim=True)
    left_s = img_bchw[:, :, :, :b_sz].mean(dim=(2, 3), keepdim=True)
    right_s = img_bchw[:, :, :, -b_sz:].mean(dim=(2, 3), keepdim=True)
    bot_s = img_bchw[:, :, -b_sz:, :].mean(dim=(2, 3), keepdim=True)
    bg_col = (top_s * 0.35 + left_s * 0.25 + right_s * 0.25 + bot_s * 0.15)
    col_dist = torch.sqrt(((img_bchw - bg_col) ** 2).sum(dim=1, keepdim=True) + 1e-06)
    chroma_mask = torch.clamp((col_dist - 0.075) / 0.22, 0.0, 1.0)

    r, g, b = img_bchw[:, 0:1], img_bchw[:, 1:2], img_bchw[:, 2:3]
    luma = 0.299 * r + 0.587 * g + 0.114 * b
    gx = F.pad(luma[:, :, :, 1:] - luma[:, :, :, :-1], (0, 1, 0, 0))
    gy = F.pad(luma[:, :, 1:, :] - luma[:, :, :-1, :], (0, 0, 0, 1))
    edge_energy = torch.clamp(torch.sqrt(gx * gx + gy * gy + 1e-06) * 5.0, 0.0, 1.0)

    yy = torch.linspace(-1.0, 1.0, h, device=dev).view(1, 1, h, 1).expand(1, 1, h, w)
    xx = torch.linspace(-1.0, 1.0, w, device=dev).view(1, 1, 1, w).expand(1, 1, h, w)
    center_prior = torch.clamp(1.0 - (xx / 0.78) ** 2 - ((yy - 0.05) / 0.92) ** 2, 0.0, 1.0)

    try:
        zones = _compute_neural_anatomy_zones(img_bchw)
        anat_union = torch.clamp(
            zones['base_skin'] * 0.85 + zones['face'] + zones['torso'] + zones['pelvic'] + zones['hands'] + zones['feet'],
            0.0,
            1.0,
        )
    except Exception:
        anat_union = torch.zeros_like(chroma_mask)

    raw_fg = torch.maximum(anat_union, chroma_mask * (0.45 + 0.55 * center_prior) + 0.2 * edge_energy * center_prior)
    dilated = F.max_pool2d(raw_fg, kernel_size=5, stride=1, padding=2)
    eroded = -F.max_pool2d(-dilated, kernel_size=5, stride=1, padding=2)
    alpha_out = _gaussian_blur_2d(torch.clamp(eroded, 0.0, 1.0), max(1.0, float(feather_radius)))
    if float(alpha_out.mean().item()) < 0.05:
        alpha_out = _gaussian_blur_2d(center_prior, max(2.0, float(feather_radius)))
    return torch.clamp(alpha_out, 0.0, 1.0)


def compute_controlnet_openpose_canny_lineart(img_bchw: torch.Tensor) -> dict:
    _, _, h, w = img_bchw.shape
    dev = img_bchw.device
    r, g, b = img_bchw[:, 0:1], img_bchw[:, 1:2], img_bchw[:, 2:3]
    luma = 0.299 * r + 0.587 * g + 0.114 * b

    sobel_x = torch.tensor([[-1.0, 0.0, 1.0], [-2.0, 0.0, 2.0], [-1.0, 0.0, 1.0]], device=dev).view(1, 1, 3, 3)
    sobel_y = torch.tensor([[-1.0, -2.0, -1.0], [0.0, 0.0, 0.0], [1.0, 2.0, 1.0]], device=dev).view(1, 1, 3, 3)
    smooth_luma = _gaussian_blur_2d(luma, 1.2)
    gx = F.conv2d(F.pad(smooth_luma, (1, 1, 1, 1), mode='reflect'), sobel_x)
    gy = F.conv2d(F.pad(smooth_luma, (1, 1, 1, 1), mode='reflect'), sobel_y)
    grad_mag = torch.sqrt(gx * gx + gy * gy + 1e-06)
    p95 = torch.quantile(grad_mag.flatten(), 0.95).clamp(min=1e-04)
    canny_edge = torch.clamp((grad_mag / p95 - 0.22) / 0.65, 0.0, 1.0)

    dog_fine = _gaussian_blur_2d(luma, 0.8)
    dog_coarse = _gaussian_blur_2d(luma, 2.6)
    lineart = torch.clamp((dog_coarse - dog_fine) * 14.0, 0.0, 1.0)

    pose_canvas = torch.zeros((1, 3, h, w), dtype=torch.float32, device=dev)
    yy = torch.arange(h, dtype=torch.float32, device=dev).view(1, 1, h, 1).expand(1, 1, h, w)
    xx = torch.arange(w, dtype=torch.float32, device=dev).view(1, 1, 1, w).expand(1, 1, h, w)
    kpts_list = _detect_skeletal_keypoints_rcnn(img_bchw[0], conf_thresh=0.35)
    limb_pairs = [
        (5, 6, (1.0, 0.35, 0.0)),
        (5, 7, (0.95, 0.85, 0.0)),
        (7, 9, (0.55, 1.0, 0.0)),
        (6, 8, (0.0, 1.0, 0.35)),
        (8, 10, (0.0, 0.95, 0.85)),
        (5, 11, (0.0, 0.55, 1.0)),
        (6, 12, (0.25, 0.25, 1.0)),
        (11, 12, (0.65, 0.0, 1.0)),
        (11, 13, (1.0, 0.0, 0.85)),
        (13, 15, (1.0, 0.0, 0.45)),
        (12, 14, (0.0, 0.85, 1.0)),
        (14, 16, (0.45, 0.85, 1.0)),
        (0, 1, (1.0, 0.2, 0.6)),
        (0, 2, (0.8, 0.2, 1.0)),
    ]
    limb_rad = max(2.5, min(h, w) * 0.0065)
    for kp in kpts_list:
        for idx_a, idx_b, rgb_col in limb_pairs:
            pa, pb = kp[idx_a], kp[idx_b]
            if len(pa) >= 3 and len(pb) >= 3 and float(pa[2]) > 0.2 and float(pb[2]) > 0.2:
                seg = _capsule_sdf_2d(yy, xx, pa[1], pa[0], pb[1], pb[0], limb_rad)
                for c_i in range(3):
                    pose_canvas[:, c_i:c_i + 1] = torch.maximum(pose_canvas[:, c_i:c_i + 1], seg * float(rgb_col[c_i]))
        for j_idx, pt in enumerate(kp):
            if len(pt) >= 3 and float(pt[2]) > 0.2:
                j_dot = _capsule_sdf_2d(yy, xx, pt[1], pt[0], pt[1], pt[0], limb_rad * 1.45)
                pose_canvas[:, 0:1] = torch.maximum(pose_canvas[:, 0:1], j_dot)
                pose_canvas[:, 1:2] = torch.maximum(pose_canvas[:, 1:2], j_dot * (0.9 if j_idx < 5 else 0.4))
                pose_canvas[:, 2:3] = torch.maximum(pose_canvas[:, 2:3], j_dot * (1.0 if j_idx < 5 else 0.2))

    combined_preview = torch.clamp(
        pose_canvas
        + torch.cat([canny_edge * 0.35, canny_edge * 0.78, canny_edge * 0.95], dim=1)
        + torch.cat([lineart * 0.55, lineart * 0.25, lineart * 0.75], dim=1),
        0.0,
        1.0,
    )
    return {
        'canny': canny_edge,
        'lineart': lineart,
        'openpose': pose_canvas,
        'keypoints': kpts_list,
        'preview_bchw': combined_preview,
    }


def compute_depth_anything_midas_map(img_bchw: torch.Tensor) -> dict:
    _, _, h, w = img_bchw.shape
    dev = img_bchw.device
    r, g, b = img_bchw[:, 0:1], img_bchw[:, 1:2], img_bchw[:, 2:3]
    luma = 0.299 * r + 0.587 * g + 0.114 * b

    fine_blur = _gaussian_blur_2d(luma, 1.5)
    mid_blur = _gaussian_blur_2d(luma, 6.0)
    coarse_blur = _gaussian_blur_2d(luma, 18.0)
    local_detail = (luma - fine_blur).abs() * 3.2 + (fine_blur - mid_blur).abs() * 2.1
    local_contrast = _gaussian_blur_2d(torch.clamp(local_detail, 0.0, 1.0), 8.0)

    max_rgb = torch.maximum(r, torch.maximum(g, b))
    min_rgb = torch.minimum(r, torch.minimum(g, b))
    saturation = (max_rgb - min_rgb) / (max_rgb + 1e-05)
    warmth = torch.clamp((r - b) * 0.65 + 0.5, 0.0, 1.0)
    atmo_near = _gaussian_blur_2d(0.55 * saturation + 0.45 * warmth, 10.0)

    yy = torch.linspace(0.0, 1.0, h, device=dev).view(1, 1, h, 1).expand(1, 1, h, w)
    fg_alpha = extract_layerdiffusion_foreground_alpha(img_bchw, feather_radius=8.0)

    raw_depth = (
        0.38 * fg_alpha
        + 0.26 * yy
        + 0.22 * local_contrast
        + 0.14 * atmo_near
        + 0.08 * (1.0 - coarse_blur)
    )
    d_min = raw_depth.amin(dim=(2, 3), keepdim=True)
    d_max = raw_depth.amax(dim=(2, 3), keepdim=True)
    depth_norm = torch.clamp((raw_depth - d_min) / (d_max - d_min + 1e-05), 0.0, 1.0)
    depth_smooth = _gaussian_blur_2d(depth_norm, 2.2)

    dz_dx = F.pad(depth_smooth[:, :, :, 1:] - depth_smooth[:, :, :, :-1], (0, 1, 0, 0)) * 6.0
    dz_dy = F.pad(depth_smooth[:, :, 1:, :] - depth_smooth[:, :, :-1, :], (0, 0, 0, 1)) * 6.0
    nz = torch.ones_like(dz_dx)
    norm_len = torch.sqrt(dz_dx * dz_dx + dz_dy * dz_dy + nz * nz + 1e-06)
    normal_bchw = torch.cat([(-dz_dx / norm_len) * 0.5 + 0.5, (-dz_dy / norm_len) * 0.5 + 0.5, (nz / norm_len) * 0.5 + 0.5], dim=1)

    d_r = torch.clamp(depth_smooth * 1.35 - 0.15, 0.0, 1.0)
    d_g = torch.clamp(1.0 - (depth_smooth - 0.55).abs() * 2.1, 0.0, 1.0)
    d_b = torch.clamp((1.0 - depth_smooth) * 1.25, 0.0, 1.0)
    depth_color_bchw = torch.clamp(0.78 * torch.cat([d_r, d_g, d_b], dim=1) + 0.22 * normal_bchw, 0.0, 1.0)
    return {
        'depth_1ch': depth_smooth,
        'normal_bchw': normal_bchw,
        'preview_bchw': depth_color_bchw,
    }


def _detect_primary_face_geometry(img_bchw: torch.Tensor):
    _, _, h, w = img_bchw.shape
    dev = img_bchw.device
    kpts = _detect_skeletal_keypoints_rcnn(img_bchw[0], conf_thresh=0.30)
    if kpts:
        kp = kpts[0]
        nose, l_eye, r_eye = kp[0], kp[1], kp[2]
        if float(nose[2]) > 0.2 and float(l_eye[2]) > 0.2 and float(r_eye[2]) > 0.2:
            eye_cx = 0.5 * (float(l_eye[0]) + float(r_eye[0]))
            eye_cy = 0.5 * (float(l_eye[1]) + float(r_eye[1]))
            eye_dist = max(14.0, math.hypot(float(l_eye[0]) - float(r_eye[0]), float(l_eye[1]) - float(r_eye[1])))
            angle_rad = math.atan2(float(l_eye[1]) - float(r_eye[1]), float(l_eye[0]) - float(r_eye[0]))
            cx = 0.65 * eye_cx + 0.35 * float(nose[0])
            cy = eye_cy + 0.35 * eye_dist
            rx = max(20.0, eye_dist * 1.45)
            ry = max(24.0, eye_dist * 1.85)
            return {'cx': cx, 'cy': cy, 'rx': rx, 'ry': ry, 'eye_dist': eye_dist, 'angle': angle_rad, 'valid_kpt': True, 'kpt': kp}

    zones = _compute_neural_anatomy_zones(img_bchw)
    face_m = zones['face']
    w_sum = float(face_m.sum().item())
    if w_sum > 25.0:
        yy = torch.arange(h, dtype=torch.float32, device=dev).view(1, 1, h, 1)
        xx = torch.arange(w, dtype=torch.float32, device=dev).view(1, 1, 1, w)
        cx = float((face_m * xx).sum().item() / w_sum)
        cy = float((face_m * yy).sum().item() / w_sum)
        rx = max(24.0, math.sqrt(w_sum) * 0.65)
        ry = max(28.0, math.sqrt(w_sum) * 0.82)
        return {'cx': cx, 'cy': cy, 'rx': rx, 'ry': ry, 'eye_dist': rx * 0.68, 'angle': 0.0, 'valid_kpt': False, 'kpt': None}

    return {'cx': w * 0.5, 'cy': h * 0.28, 'rx': w * 0.16, 'ry': h * 0.20, 'eye_dist': w * 0.10, 'angle': 0.0, 'valid_kpt': False, 'kpt': None}


def apply_reactor_and_adetailer_pass(target_bhwc: torch.Tensor, ref_person_bhwc: torch.Tensor, identity_strength: float = 1.0, adetailer_denoise: float = 0.32, focus_mode: str = '') -> torch.Tensor:
    if not isinstance(target_bhwc, torch.Tensor) or target_bhwc.ndim != 4:
        return target_bhwc
    if float(identity_strength) <= 0.01 or 'dual_subject' in str(focus_mode or '').lower():
        return target_bhwc

    dev = target_bhwc.device
    out_frames = []
    cached_dst_geom = None
    sharpen_gain = max(0.04, min(0.28, float(adetailer_denoise) * 0.45)) * max(0.0, min(1.0, float(identity_strength)))
    for bi in range(int(target_bhwc.shape[0])):
        frame_bchw = target_bhwc[bi:bi + 1, :, :, :3].to(device=dev, dtype=torch.float32).permute(0, 3, 1, 2).contiguous()
        _, _, th, tw = frame_bchw.shape
        if bi == 0 or bi % 8 == 0 or cached_dst_geom is None:
            cached_dst_geom = _detect_primary_face_geometry(frame_bchw)
        dst_geom = cached_dst_geom
        dx1 = max(0, int(round(dst_geom['cx'] - dst_geom['rx'])))
        dx2 = min(tw, int(round(dst_geom['cx'] + dst_geom['rx'])))
        dy1 = max(0, int(round(dst_geom['cy'] - dst_geom['ry'])))
        dy2 = min(th, int(round(dst_geom['cy'] + dst_geom['ry'])))
        box_w, box_h = dx2 - dx1, dy2 - dy1
        if box_w < 16 or box_h < 16:
            out_frames.append(target_bhwc[bi:bi + 1])
            continue

        dst_crop = frame_bchw[:, :, dy1:dy2, dx1:dx2]
        dst_low = _gaussian_blur_2d(dst_crop, max(1.2, min(box_w, box_h) * 0.035))
        dst_high = dst_crop - dst_low
        face_refined = torch.clamp(dst_crop + dst_high * sharpen_gain, 0.0, 1.0)

        yy = torch.linspace(-1.0, 1.0, box_h, device=dev).view(1, 1, box_h, 1).expand(1, 1, box_h, box_w)
        xx = torch.linspace(-1.0, 1.0, box_w, device=dev).view(1, 1, 1, box_w).expand(1, 1, box_h, box_w)
        oval_mask = torch.clamp(1.0 - (xx / 0.82) ** 2 - (yy / 0.86) ** 2, 0.0, 1.0)
        oval_mask = _gaussian_blur_2d(oval_mask, max(2.0, min(box_w, box_h) * 0.08))

        updated_frame = frame_bchw.clone()
        updated_frame[:, :, dy1:dy2, dx1:dx2] = oval_mask * face_refined + (1.0 - oval_mask) * dst_crop
        out_frames.append(torch.clamp(updated_frame.permute(0, 2, 3, 1).contiguous(), 0.0, 1.0))

    return torch.cat(out_frames, dim=0)


def extract_isolated_garment_region(garment_bchw: torch.Tensor, garment_alpha_bchw: torch.Tensor = None):
    _, _, h, w = garment_bchw.shape
    dev = garment_bchw.device
    if garment_alpha_bchw is None:
        garment_alpha_bchw = extract_layerdiffusion_foreground_alpha(garment_bchw, feather_radius=3.0)

    try:
        src_zones = _compute_neural_anatomy_zones(garment_bchw)
        src_skin_head_hands = torch.clamp(
            src_zones['face'] * 1.8
            + src_zones['eyes'] * 2.0
            + src_zones['hands'] * 1.35
            + src_zones['base_skin'] * 0.82,
            0.0,
            1.0,
        )
    except Exception:
        src_skin_head_hands = torch.zeros_like(garment_alpha_bchw)

    kpts = _detect_skeletal_keypoints_rcnn(garment_bchw[0], conf_thresh=0.28)
    yy = torch.linspace(0.0, 1.0, h, device=dev).view(1, 1, h, 1).expand(1, 1, h, w)
    xx = torch.linspace(0.0, 1.0, w, device=dev).view(1, 1, 1, w).expand(1, 1, h, w)
    if kpts and len(kpts[0]) >= 13:
        kp = kpts[0]
        l_sh, r_sh, l_hp, r_hp = kp[5], kp[6], kp[11], kp[12]
        nose = kp[0]
        sh_y = min(float(l_sh[1]), float(r_sh[1])) / max(1.0, float(h))
        hp_y = max(float(l_hp[1]), float(r_hp[1])) / max(1.0, float(h))
        neck_cut_y = max(0.08, sh_y - 0.03)
        if float(nose[2]) > 0.25:
            neck_cut_y = max(neck_cut_y, (float(nose[1]) / max(1.0, float(h))) + 0.07)
        lower_cut_y = min(0.95, hp_y + max(0.22, (hp_y - sh_y) * 0.85))
        sh_cx = 0.5 * (float(l_sh[0]) + float(r_sh[0])) / max(1.0, float(w))
        sh_span = max(0.18, abs(float(l_sh[0]) - float(r_sh[0])) / max(1.0, float(w)))
        vert_band = torch.sigmoid((yy - neck_cut_y) * 32.0) * torch.sigmoid((lower_cut_y - yy) * 24.0)
        horiz_band = torch.clamp(1.0 - ((xx - sh_cx) / max(0.22, sh_span * 1.15)) ** 2, 0.0, 1.0)
        torso_prior = vert_band * horiz_band
    else:
        torso_prior = torch.sigmoid((yy - 0.26) * 24.0) * torch.sigmoid((0.88 - yy) * 24.0) * torch.clamp(1.0 - ((xx - 0.5) / 0.38) ** 2, 0.0, 1.0)

    pure_cloth_mask = torch.clamp(garment_alpha_bchw * torso_prior * (1.0 - src_skin_head_hands), 0.0, 1.0)
    if float(pure_cloth_mask.max().item()) < 0.12:
        pure_cloth_mask = torch.clamp(garment_alpha_bchw * torso_prior, 0.0, 1.0)

    mask_2d = pure_cloth_mask[0, 0] > 0.15
    if bool(mask_2d.any()):
        ys, xs = torch.where(mask_2d)
        cy1 = max(0, int(ys.min().item()))
        cy2 = min(h, int(ys.max().item()) + 1)
        cx1 = max(0, int(xs.min().item()))
        cx2 = min(w, int(xs.max().item()) + 1)
    else:
        cy1, cy2 = int(h * 0.28), int(h * 0.82)
        cx1, cx2 = int(w * 0.25), int(w * 0.75)

    if cy2 - cy1 < 16 or cx2 - cx1 < 16:
        cy1, cy2 = int(h * 0.28), int(h * 0.82)
        cx1, cx2 = int(w * 0.25), int(w * 0.75)

    clean_bg = torch.full_like(garment_bchw, 0.18)
    isolated_full = pure_cloth_mask * garment_bchw + (1.0 - pure_cloth_mask) * clean_bg
    crop_bchw = isolated_full[:, :, cy1:cy2, cx1:cx2]
    crop_resized = F.interpolate(crop_bchw, size=(h, w), mode='bicubic', align_corners=False).clamp(0.0, 1.0)
    return pure_cloth_mask, crop_resized, (cy1, cy2, cx1, cx2)


def warp_ootdiffusion_garment_to_subject(canvas_bchw: torch.Tensor, garment_bchw: torch.Tensor, garment_alpha_bchw: torch.Tensor = None, ootd_strength: float = 0.95, preserve_neck_and_hands: bool = True, focus_mode: str = ''):
    _, _, h, w = canvas_bchw.shape
    dev = canvas_bchw.device
    s3_mode_low = str(focus_mode or '').strip().lower()
    src_cloth_mask, garment_isolated_bchw, _ = extract_isolated_garment_region(garment_bchw, garment_alpha_bchw)

    dst_fg_alpha = extract_layerdiffusion_foreground_alpha(canvas_bchw, feather_radius=3.5)
    try:
        dst_zones = _compute_neural_anatomy_zones(canvas_bchw)
        dst_head_hands = torch.clamp(
            dst_zones['face'] * 2.0
            + dst_zones['eyes'] * 2.2
            + (dst_zones['hands'] * 1.45 if preserve_neck_and_hands else 0.0),
            0.0,
            1.0,
        )
        dst_torso_pelvic = torch.clamp(dst_zones['torso'] * 1.25 + dst_zones['pelvic'] * 1.15, 0.0, 1.0)
        dst_bare_skin = torch.clamp(dst_zones['base_skin'] * (1.0 - 0.35 * dst_torso_pelvic), 0.0, 1.0)
    except Exception:
        dst_head_hands = torch.zeros_like(dst_fg_alpha)
        dst_torso_pelvic = torch.ones_like(dst_fg_alpha)
        dst_bare_skin = torch.zeros_like(dst_fg_alpha)

    kpts = _detect_skeletal_keypoints_rcnn(canvas_bchw[0], conf_thresh=0.28)
    yy = torch.linspace(0.0, 1.0, h, device=dev).view(1, 1, h, 1).expand(1, 1, h, w)
    xx = torch.linspace(0.0, 1.0, w, device=dev).view(1, 1, 1, w).expand(1, 1, h, w)
    if kpts and len(kpts[0]) >= 13:
        kp = kpts[0]
        l_sh, r_sh, l_hp, r_hp = kp[5], kp[6], kp[11], kp[12]
        nose = kp[0]
        sh_y = min(float(l_sh[1]), float(r_sh[1])) / max(1.0, float(h))
        hp_y = max(float(l_hp[1]), float(r_hp[1])) / max(1.0, float(h))
        neck_y = max(0.10, sh_y - 0.02)
        if float(nose[2]) > 0.25:
            neck_y = max(neck_y, (float(nose[1]) / max(1.0, float(h))) + 0.08)
        hem_y = min(0.94, hp_y + max(0.20, (hp_y - sh_y) * 0.78))
        cx_norm = 0.5 * (float(l_sh[0]) + float(r_sh[0])) / max(1.0, float(w))
        span_norm = max(0.18, abs(float(l_sh[0]) - float(r_sh[0])) / max(1.0, float(w)))
        dst_body_band = torch.sigmoid((yy - neck_y) * 28.0) * torch.sigmoid((hem_y - yy) * 22.0) * torch.clamp(1.0 - ((xx - cx_norm) / max(0.24, span_norm * 1.18)) ** 2, 0.0, 1.0)
    else:
        dst_body_band = torch.sigmoid((yy - 0.28) * 24.0) * torch.sigmoid((0.86 - yy) * 22.0) * torch.clamp(1.0 - ((xx - 0.5) / 0.36) ** 2, 0.0, 1.0)

    r_c, g_c, b_c = canvas_bchw[:, 0:1], canvas_bchw[:, 1:2], canvas_bchw[:, 2:3]
    red_hair_guard = torch.clamp((r_c - torch.maximum(g_c, b_c) - 0.12) * 4.5, 0.0, 1.0) * torch.sigmoid((0.48 - yy) * 20.0)

    skin_exclusion = 0.45 if 'skeletal_torso_warp' in s3_mode_low else (0.25 if 'direct_garment_overlay' in s3_mode_low else 0.75)
    target_cloth_region = torch.clamp(
        dst_fg_alpha * dst_body_band * (1.0 - dst_head_hands) * (1.0 - skin_exclusion * dst_bare_skin) * (1.0 - red_hair_guard),
        0.0,
        1.0,
    )
    target_cloth_region = _gaussian_blur_2d(target_cloth_region, 4.0).clamp(0.0, 1.0)

    src_w_sum = src_cloth_mask.sum(dim=(2, 3), keepdim=True).clamp(min=16.0)
    src_mean = (garment_bchw * src_cloth_mask).sum(dim=(2, 3), keepdim=True) / src_w_sum
    src_var = (((garment_bchw - src_mean) ** 2) * src_cloth_mask).sum(dim=(2, 3), keepdim=True) / src_w_sum
    src_std = torch.sqrt(src_var + 1e-05).clamp(min=0.03, max=0.35)

    dst_w_sum = target_cloth_region.sum(dim=(2, 3), keepdim=True).clamp(min=16.0)
    dst_mean = (canvas_bchw * target_cloth_region).sum(dim=(2, 3), keepdim=True) / dst_w_sum
    dst_var = (((canvas_bchw - dst_mean) ** 2) * target_cloth_region).sum(dim=(2, 3), keepdim=True) / dst_w_sum
    dst_std = torch.sqrt(dst_var + 1e-05).clamp(min=0.03, max=0.35)

    dst_luma = 0.299 * r_c + 0.587 * g_c + 0.114 * b_c
    dst_low = _gaussian_blur_2d(canvas_bchw, 3.2)
    dst_shading_detail = canvas_bchw - dst_low

    src_tex_low = _gaussian_blur_2d(garment_isolated_bchw, 5.0)
    tex_gain = 0.65 if 'fabric_and_weave' in s3_mode_low else (0.52 if 'skeletal_torso_warp' in s3_mode_low else 0.35)
    src_tex_micro = (garment_isolated_bchw - src_tex_low) * tex_gain

    recolored_base = (dst_low - dst_mean) * (src_std / dst_std) + src_mean
    recolored_luma = 0.299 * recolored_base[:, 0:1] + 0.587 * recolored_base[:, 1:2] + 0.114 * recolored_base[:, 2:3]
    luma_keep = 0.78 if 'fabric_and_weave' in s3_mode_low else 0.65
    luma_locked = recolored_base * ((luma_keep * dst_luma + (1.0 - luma_keep) * recolored_luma) / (recolored_luma + 1e-04))
    if 'direct_garment_overlay' in s3_mode_low:
        transferred_garment = torch.clamp(0.76 * garment_isolated_bchw + 0.24 * luma_locked + dst_shading_detail * 0.45, 0.0, 1.0)
        strength_mult = 0.90
    elif 'skeletal_torso_warp' in s3_mode_low:
        transferred_garment = torch.clamp(0.42 * garment_isolated_bchw + 0.58 * luma_locked + dst_shading_detail * 0.80 + src_tex_micro, 0.0, 1.0)
        strength_mult = 0.85
    else:
        transferred_garment = torch.clamp(luma_locked + dst_shading_detail * 0.95 + src_tex_micro, 0.0, 1.0)
        strength_mult = 0.76

    eff_strength = max(0.0, min(1.0, float(ootd_strength) * strength_mult))
    eff_alpha = _gaussian_blur_2d(target_cloth_region, 3.5) * eff_strength
    composited = eff_alpha * transferred_garment + (1.0 - eff_alpha) * canvas_bchw
    return torch.clamp(composited, 0.0, 1.0), target_cloth_region, garment_isolated_bchw



def execute_omni_reference_studio(
    slot1_master_image: str,
    slot1_focus_mode: str,
    slot1_strength: float,
    slot1_inpaint_mask_mode: str,
    slot1_feather_radius: float,
    slot2_person_image: str,
    slot2_focus_mode: str,
    slot2_identity_strength: float,
    slot2_adetailer_denoise: float,
    slot3_clothing_image: str,
    slot3_focus_mode: str,
    slot3_ootd_strength: float,
    slot3_preserve_neck_and_hands: bool,
    slot4_background_image: str,
    slot4_focus_mode: str,
    slot4_depth_and_tile_strength: float,
    slot4_horizon_relight_match: float,
    target_width: int = 1248,
    target_height: int = 832,
    slot5_reference_video: str = 'None',
    slot5_start_offset_sec: float = 0.0,
    slot5_duration_mode: str = SLOT5_DURATION_MODES[0],
    slot5_duration_seconds: float = 0.0,
    slot5_focus_mode: str = SLOT5_FOCUS_MODES[0],
    slot5_motion_strength: float = 0.65,
    slot5_max_frames: int = 0,
    opt_slot1_image: torch.Tensor = None,
    opt_slot1_mask: torch.Tensor = None,
    opt_slot2_person: torch.Tensor = None,
    opt_slot3_clothing: torch.Tensor = None,
    opt_slot4_background: torch.Tensor = None,
    opt_slot5_video: torch.Tensor = None,
    cinematrix_bus: dict = None,
):
    bus = dict(cinematrix_bus) if isinstance(cinematrix_bus, dict) else {}
    w = max(64, int(round(float(target_width or bus.get('base_width', 1248) or 1248) / 16.0) * 16))
    h = max(64, int(round(float(target_height or bus.get('base_height', 832) or 832) / 16.0) * 16))
    bus_dur_s = float(bus.get('duration_seconds', 0.0) or 0.0)
    (eff_slot5_dur_s, follow_master_dur, match_full_vid) = resolve_slot5_target_duration_seconds(
        slot5_duration_mode=slot5_duration_mode,
        slot5_duration_seconds=slot5_duration_seconds,
        bus_duration_sec=bus_dur_s,
    )
    def _opt_t_sig(t_in):
        if not isinstance(t_in, torch.Tensor) or t_in.numel() == 0:
            return None
        sub = t_in.detach().float().reshape(-1)[::max(1, t_in.numel() // 128)]
        return (tuple(t_in.shape), round(float(sub.mean().item()), 5), round(float(sub.std().item()), 5))
    omni_cache_key = (
        'v21_preserve_full_reference_aspect_ratio',
        str(slot1_master_image or ''), str(slot1_focus_mode or ''), round(float(slot1_strength or 0.0), 4),
        str(slot1_inpaint_mask_mode or ''), round(float(slot1_feather_radius or 0.0), 3),
        str(slot2_person_image or ''), str(slot2_focus_mode or ''), round(float(slot2_identity_strength or 0.0), 4), round(float(slot2_adetailer_denoise or 0.0), 4),
        str(slot3_clothing_image or ''), str(slot3_focus_mode or ''), round(float(slot3_ootd_strength or 0.0), 4), bool(slot3_preserve_neck_and_hands),
        str(slot4_background_image or ''), str(slot4_focus_mode or ''), round(float(slot4_depth_and_tile_strength or 0.0), 4), round(float(slot4_horizon_relight_match or 0.0), 4),
        int(w), int(h), str(slot5_reference_video or ''), round(float(slot5_start_offset_sec or 0.0), 3), str(slot5_duration_mode or ''), round(float(slot5_duration_seconds or 0.0), 2), str(slot5_focus_mode or ''), round(float(slot5_motion_strength or 0.0), 4), int(slot5_max_frames or 0), round(eff_slot5_dur_s, 2),
        _opt_t_sig(opt_slot1_image), _opt_t_sig(opt_slot1_mask), _opt_t_sig(opt_slot2_person), _opt_t_sig(opt_slot3_clothing), _opt_t_sig(opt_slot4_background), _opt_t_sig(opt_slot5_video),
    )
    omni_exec_cache = globals().setdefault('_OMNI_REF_EXEC_CACHE', {})
    if omni_cache_key in omni_exec_cache:
        (c_master, c_mask, c_person, c_cloth, c_bg, c_preview, c_bundle, c_ref_vid, c_ui_meta, c_bus_delta) = omni_exec_cache[omni_cache_key]
        bus['omni_reference_bundle'] = dict(c_bundle)
        bus.update(c_bus_delta)
        return (c_master, c_mask, c_person, c_cloth, c_bg, c_preview, bus, c_ref_vid, list(c_ui_meta))

    s1_rgb, s1_alpha, s1_has_a = load_image_and_alpha_from_slot(slot1_master_image, opt_slot1_image, opt_slot1_mask)
    s2_rgb, s2_alpha, s2_has_a = load_image_and_alpha_from_slot(slot2_person_image, opt_slot2_person, None)
    s3_rgb, s3_alpha, s3_has_a = load_image_and_alpha_from_slot(slot3_clothing_image, opt_slot3_clothing, None)
    s4_rgb, s4_alpha, s4_has_a = load_image_and_alpha_from_slot(slot4_background_image, opt_slot4_background, None)
    s5_video_bhwc, s5_video_path = load_video_frames_from_slot(
        slot5_reference_video,
        opt_slot5_video,
        max_frames=int(slot5_max_frames or 0),
        target_w=min(w, 768),
        target_h=min(h, 512),
        start_offset_sec=float(slot5_start_offset_sec or 0.0),
        target_duration_sec=eff_slot5_dur_s,
    )
    s5_audio_dict = extract_audio_from_video_path(s5_video_path, start_offset_sec=float(slot5_start_offset_sec or 0.0), max_duration_sec=(eff_slot5_dur_s if eff_slot5_dur_s > 0.5 else 600.0)) if s5_video_path else None

    primary_ref_t = (
        s1_rgb
        if (isinstance(s1_rgb, torch.Tensor) and s1_rgb.ndim >= 3 and int(s1_rgb.shape[-3]) >= 16 and int(s1_rgb.shape[-2]) >= 16)
        else (
            s5_video_bhwc[:1]
            if (isinstance(s5_video_bhwc, torch.Tensor) and s5_video_bhwc.ndim >= 4 and int(s5_video_bhwc.shape[0]) >= 1)
            else s4_rgb
        )
    )
    if isinstance(primary_ref_t, torch.Tensor) and primary_ref_t.ndim >= 3:
        ref_h = int(primary_ref_t.shape[-3])
        ref_w = int(primary_ref_t.shape[-2])
        if ref_w >= 16 and ref_h >= 16:
            ref_aspect = float(ref_w) / max(1.0, float(ref_h))
            ui_aspect = float(w) / max(1.0, float(h))
            if abs(math.log(max(0.05, ui_aspect) / max(0.05, ref_aspect))) > 0.08:
                target_area = float(w * h)
                if (ref_w % 16 == 0) and (ref_h % 16 == 0) and (0.55 * target_area <= float(ref_w * ref_h) <= 1.45 * target_area):
                    (w, h) = (ref_w, ref_h)
                else:
                    w = max(64, int(round(math.sqrt(target_area * ref_aspect) / 16.0) * 16))
                    h = max(64, int(round(math.sqrt(target_area / ref_aspect) / 16.0) * 16))
            bus['base_width'] = int(w)
            bus['base_height'] = int(h)
            bus['source_aspect_ratio'] = round(float(w) / max(1.0, float(h)), 5)

    s1_bhwc = resize_bhwc(s1_rgb, w, h) if s1_rgb is not None else None
    s2_bhwc = resize_bhwc(s2_rgb, w, h) if s2_rgb is not None else None
    s3_bhwc = resize_bhwc(s3_rgb, w, h) if s3_rgb is not None else None
    s4_bhwc = resize_bhwc(s4_rgb, w, h) if s4_rgb is not None else None

    s5_extract_keyframe_only = 'first_video_frame_only' in str(slot5_focus_mode or '').lower()
    use_s5_mocap = (
        s5_video_bhwc is not None
        and int(s5_video_bhwc.shape[0]) >= 2
        and not s5_extract_keyframe_only
    )
    s5_first_bhwc = resize_bhwc(s5_video_bhwc[:1], w, h) if (s5_video_bhwc is not None and int(s5_video_bhwc.shape[0]) >= 1) else None
    if s1_bhwc is None and s5_first_bhwc is not None and s5_extract_keyframe_only:
        s1_bhwc = s5_first_bhwc
        s1_alpha = torch.ones((1, h, w), dtype=torch.float32)
        s1_has_a = False

    s1_char_crop_bhwc = None
    s1_skin_rgb_list = None
    if s1_bhwc is not None:
        s1_orig_bchw = s1_bhwc.permute(0, 3, 1, 2).contiguous()
        try:
            s1_geom = _detect_primary_face_geometry(s1_orig_bchw)
            cx1 = max(0, int(round(s1_geom['cx'] - s1_geom['rx'] * 1.65)))
            cx2 = min(w, int(round(s1_geom['cx'] + s1_geom['rx'] * 1.65)))
            cy1 = max(0, int(round(s1_geom['cy'] - s1_geom['ry'] * 1.45)))
            cy2 = min(h, int(round(s1_geom['cy'] + s1_geom['ry'] * 1.95)))
            if cx2 - cx1 >= 32 and cy2 - cy1 >= 32:
                s1_crop_bchw = F.interpolate(s1_orig_bchw[:, :, cy1:cy2, cx1:cx2], size=(h, w), mode='bicubic', align_corners=False).clamp(0.0, 1.0)
                s1_char_crop_bhwc = s1_crop_bchw.permute(0, 2, 3, 1).contiguous()
            else:
                s1_char_crop_bhwc = s1_bhwc.clone()
        except Exception:
            s1_char_crop_bhwc = s1_bhwc.clone()
        try:
            s1_z = _compute_neural_anatomy_zones(s1_orig_bchw)
            s1_sk_m = torch.clamp(s1_z['face'] * 1.5 + s1_z['base_skin'] * 0.85 - s1_z['eyes'] * 2.0, 0.0, 1.0)
            sk_sum = float(s1_sk_m.sum().item())
            if sk_sum > 24.0:
                mean_c = (s1_orig_bchw * s1_sk_m).sum(dim=(0, 2, 3)) / sk_sum
                s1_skin_rgb_list = [round(float(mean_c[0].item()), 4), round(float(mean_c[1].item()), 4), round(float(mean_c[2].item()), 4)]
        except Exception:
            s1_skin_rgb_list = None

    has_video_scene_template = bool(use_s5_mocap and s5_first_bhwc is not None)
    base_bhwc = s5_first_bhwc if has_video_scene_template else (s1_bhwc if s1_bhwc is not None else (s4_bhwc if s4_bhwc is not None else (s2_bhwc if s2_bhwc is not None else s3_bhwc)))
    has_image_slots = (base_bhwc is not None)
    if base_bhwc is None and s5_first_bhwc is None:
        empty_img = torch.zeros((1, h, w, 3), dtype=torch.float32)
        empty_mask = torch.zeros((1, h, w), dtype=torch.float32)
        return empty_img, empty_mask, empty_img, empty_img, empty_img, empty_img, bus, empty_img, []
    if base_bhwc is None:
        base_bhwc = s5_first_bhwc

    base_bchw = base_bhwc.permute(0, 3, 1, 2).contiguous()
    s1_bchw_raw = base_bchw.clone() if has_video_scene_template else (s1_bhwc.permute(0, 3, 1, 2).contiguous() if s1_bhwc is not None else base_bchw.clone())
    s1_fg_alpha = extract_layerdiffusion_foreground_alpha(s1_bchw_raw, (None if has_video_scene_template else s1_alpha), (False if has_video_scene_template else s1_has_a), feather_radius=float(slot1_feather_radius))
    has_two_s5_people = False
    if has_video_scene_template and s1_skin_rgb_list is not None:
        try:
            s5_z = _compute_neural_anatomy_zones(base_bchw)
            r5, g5, b5 = base_bchw[:, 0:1], base_bchw[:, 1:2], base_bchw[:, 2:3]
            s5_lum = (0.299 * r5 + 0.587 * g5 + 0.114 * b5).clamp(0.02, 0.98)
            warm_skin_hair = torch.clamp((r5 - b5) * 3.2, 0.0, 1.0) * torch.clamp(s1_fg_alpha * 1.35, 0.0, 1.0)
            raw_skin_m = _gaussian_blur_2d(torch.clamp(s5_z['base_skin'] * 1.15 + warm_skin_hair * 0.65, 0.0, 1.0), 14.0)
            kpts_s5 = _detect_skeletal_keypoints_rcnn(base_bchw[0], conf_thresh=0.22)
            xx_s5 = torch.linspace(0.0, 1.0, w, device=base_bchw.device).view(1, 1, 1, w).expand(1, 1, h, w)
            split_x = 0.49
            if isinstance(kpts_s5, list) and len(kpts_s5) >= 2:
                sorted_kpts = sorted(
                    kpts_s5,
                    key=lambda kp_arr: float(kp_arr[0][0]) if len(kp_arr) > 0 and float(kp_arr[0][2]) > 0.1 else 0.5 * (float(kp_arr[5][0]) + float(kp_arr[6][0])),
                )
                kp0, kp1 = sorted_kpts[0], sorted_kpts[1]
                x0_c = (float(kp0[0][0]) if float(kp0[0][2]) > 0.1 else 0.5 * (float(kp0[5][0]) + float(kp0[6][0]))) / max(1.0, float(w))
                x1_c = (float(kp1[0][0]) if float(kp1[0][2]) > 0.1 else 0.5 * (float(kp1[5][0]) + float(kp1[6][0]))) / max(1.0, float(w))
                if abs(x1_c - x0_c) >= 0.14:
                    split_x = max(0.28, min(0.70, 0.5 * (x0_c + x1_c)))
                    has_two_s5_people = True
            else:
                left_sk_mass = float((raw_skin_m[:, :, :, :w // 2] > 0.18).float().mean().item())
                right_sk_mass = float((raw_skin_m[:, :, :, w // 2:] > 0.18).float().mean().item())
                if left_sk_mass > 0.015 and right_sk_mass > 0.015:
                    has_two_s5_people = True
                    split_x = 0.49
            subj1_spatial_gate = torch.sigmoid((split_x - xx_s5) * 32.0) if has_two_s5_people else torch.ones_like(xx_s5)
            subj2_spatial_gate = torch.clamp(1.0 - subj1_spatial_gate, 0.0, 1.0)
            face_deghost_m = _gaussian_blur_2d(torch.clamp(s5_z['face'] * 1.45 + s5_z['eyes'] * 1.65 + s5_z['mouth'] * 1.45, 0.0, 1.0), 6.0)
            smooth_face_bchw = _gaussian_blur_2d(base_bchw, 11.0)
            base_bchw = torch.lerp(base_bchw, smooth_face_bchw, torch.clamp(face_deghost_m * 0.82, 0.0, 0.88))
            if has_two_s5_people:
                subj2_skin_m = torch.clamp(raw_skin_m * subj2_spatial_gate, 0.0, 1.0)
                s2_skin_rgb = None
                if s2_bhwc is not None:
                    try:
                        s2_orig_bchw = s2_bhwc.permute(0, 3, 1, 2).contiguous()
                        s2_z = _compute_neural_anatomy_zones(s2_orig_bchw)
                        s2_sk_m = torch.clamp(s2_z['face'] * 1.5 + s2_z['base_skin'] * 0.85 - s2_z['eyes'] * 2.0, 0.0, 1.0)
                        s2_sum = float(s2_sk_m.sum().item())
                        if s2_sum > 24.0:
                            m2_c = (s2_orig_bchw * s2_sk_m).sum(dim=(0, 2, 3)) / s2_sum
                            s2_skin_rgb = [round(float(m2_c[0].item()), 4), round(float(m2_c[1].item()), 4), round(float(m2_c[2].item()), 4)]
                    except Exception:
                        s2_skin_rgb = None
                if s2_skin_rgb is not None:
                    t2_r, t2_g, t2_b = s2_skin_rgb[0], s2_skin_rgb[1], s2_skin_rgb[2]
                    t2_lum = max(0.12, 0.299 * t2_r + 0.587 * t2_g + 0.114 * t2_b)
                    c2_damp = 0.58 * (1.0 - 0.45 * (s5_lum ** 2))
                    r2_rat = 1.0 + min(0.75, max(-0.65, t2_r / t2_lum - 1.0)) * c2_damp
                    g2_rat = 1.0 + min(0.75, max(-0.65, t2_g / t2_lum - 1.0)) * c2_damp
                    b2_rat = 1.0 + min(0.75, max(-0.65, t2_b / t2_lum - 1.0)) * c2_damp
                    re2_rgb = torch.cat([s5_lum * r2_rat, s5_lum * g2_rat, s5_lum * b2_rat], dim=1).clamp(0.0, 0.92)
                    base_bchw = torch.lerp(base_bchw, re2_rgb, torch.clamp(subj2_skin_m * 0.56, 0.0, 0.74))
                else:
                    neutral_subj2 = torch.cat([s5_lum * 0.82, s5_lum * 0.86, s5_lum * 0.84], dim=1).clamp(0.0, 1.0)
                    base_bchw = torch.lerp(base_bchw, neutral_subj2, torch.clamp(subj2_skin_m * 0.72, 0.0, 0.82))
            soft_skin_m = raw_skin_m * subj1_spatial_gate
            blonde_halo = _gaussian_blur_2d(torch.clamp(warm_skin_hair * (1.0 - s5_z['base_skin']) * torch.clamp((s5_lum - 0.35) * 2.5, 0.0, 1.0), 0.0, 1.0), 10.0) * subj1_spatial_gate
            adj_lum = torch.clamp(s5_lum * (1.0 - blonde_halo * 0.52), 0.02, 0.88)
            t_r, t_g, t_b = s1_skin_rgb_list[0], s1_skin_rgb_list[1], s1_skin_rgb_list[2]
            t_lum = max(0.12, 0.299 * t_r + 0.587 * t_g + 0.114 * t_b)
            c1_damp = 0.58 * (1.0 - 0.48 * (adj_lum ** 2))
            r1_rat = 1.0 + min(0.78, max(-0.65, t_r / t_lum - 1.0)) * c1_damp
            g1_rat = 1.0 + min(0.78, max(-0.65, t_g / t_lum - 1.0)) * c1_damp
            b1_rat = 1.0 + min(0.78, max(-0.65, t_b / t_lum - 1.0)) * c1_damp
            re_rgb = torch.cat([adj_lum * r1_rat, adj_lum * g1_rat, adj_lum * b1_rat], dim=1).clamp(0.0, 0.90)
            base_bchw = torch.clamp(base_bchw * (1.0 - soft_skin_m * 0.56) + re_rgb * (soft_skin_m * 0.56), 0.0, 1.0)
        except Exception:
            pass
    s1_bchw = base_bchw.clone() if has_video_scene_template else s1_bchw_raw
    s1_hard_fg = torch.clamp((s1_fg_alpha - 0.22) / 0.58, 0.0, 1.0)
    s1_hard_fg = _gaussian_blur_2d(s1_hard_fg, max(1.5, float(slot1_feather_radius) * 0.28)).clamp(0.0, 1.0)

    inpaint_mode_low = str(slot1_inpaint_mask_mode or 'Disabled_Full_Canvas').lower()
    if 'keep_subject' in inpaint_mode_low:
        inpaint_mask_bchw = 1.0 - s1_hard_fg
    elif 'inpaint_subject' in inpaint_mode_low:
        inpaint_mask_bchw = s1_hard_fg
    elif 'center_box' in inpaint_mode_low:
        yy = torch.linspace(-1.0, 1.0, h).view(1, 1, h, 1).expand(1, 1, h, w)
        xx = torch.linspace(-1.0, 1.0, w).view(1, 1, 1, w).expand(1, 1, h, w)
        box_m = ((xx.abs() < 0.55) & (yy.abs() < 0.55)).float()
        inpaint_mask_bchw = _gaussian_blur_2d(box_m, max(2.0, float(slot1_feather_radius)))
    elif 'auto_alpha' in inpaint_mode_low and s1_has_a and not has_video_scene_template:
        inpaint_mask_bchw = 1.0 - s1_hard_fg
    else:
        inpaint_mask_bchw = torch.zeros((1, 1, h, w), dtype=torch.float32)

    cn_maps = compute_controlnet_openpose_canny_lineart(s1_bchw)
    canvas_bchw = s1_bchw.clone()
    fusion_noise_mask_bchw = torch.full((1, 1, h, w), 0.35, dtype=torch.float32)

    if s4_bhwc is not None:
        s4_bchw = s4_bhwc.permute(0, 3, 1, 2).contiguous()
        s4_mode_low = str(slot4_focus_mode or '').strip().lower()
        d_tile_str = max(0.0, min(1.0, float(slot4_depth_and_tile_strength)))
        depth_pack = compute_depth_anything_midas_map(s4_bchw)
        if 'depth_lock' in s4_mode_low:
            depth_pack['depth_1ch'] = torch.clamp((depth_pack['depth_1ch'] - 0.5) * (1.0 + 0.45 * d_tile_str) + 0.5, 0.0, 1.0)
        if s1_bhwc is not None or has_video_scene_template:
            relight_mult = (0.34 + 0.16 * d_tile_str) if 'environment_relight' in s4_mode_low else 0.24
            relight_w = max(0.0, min(1.0, float(slot4_horizon_relight_match))) * relight_mult
            bg_mean = s4_bchw.mean(dim=(2, 3), keepdim=True)
            rim_band = torch.clamp(s1_fg_alpha - s1_hard_fg * 0.85, 0.0, 1.0)
            fg_relit = torch.clamp(
                canvas_bchw * (1.0 - relight_w * 0.45) + bg_mean * (relight_w * 0.45) + rim_band * (s4_bchw - canvas_bchw) * relight_w,
                0.0,
                1.0,
            )
            canvas_bchw = s1_hard_fg * fg_relit + (1.0 - s1_hard_fg) * s4_bchw
            bg_Zone = 1.0 - s1_hard_fg
            bg_noise_w = (0.45 * (1.0 - 0.35 * d_tile_str)) if 'temporal_background_anchor' in s4_mode_low else (0.72 * (1.0 - 0.25 * d_tile_str))
            fusion_noise_mask_bchw = torch.maximum(fusion_noise_mask_bchw, bg_Zone * bg_noise_w + rim_band * 0.85)
        else:
            canvas_bchw = s4_bchw.clone()
    else:
        depth_pack = compute_depth_anything_midas_map(canvas_bchw)

    ootd_preview_bchw = torch.zeros((1, 3, h, w), dtype=torch.float32)
    s3_garment_isolated_bhwc = s3_bhwc
    same_s1_s3 = (
        s1_bhwc is not None
        and s3_bhwc is not None
        and float((s1_bhwc - s3_bhwc).abs().mean().item()) < 0.008
    )
    if s3_bhwc is not None:
        s3_bchw = s3_bhwc.permute(0, 3, 1, 2).contiguous()
        s3_fg_alpha = extract_layerdiffusion_foreground_alpha(s3_bchw, s3_alpha, s3_has_a, feather_radius=3.5)
        if same_s1_s3:
            _, placed_gar, _ = extract_isolated_garment_region(s3_bchw, s3_fg_alpha)
            eff_gar_a = _gaussian_blur_2d(s1_hard_fg, 3.0)
        else:
            canvas_bchw, eff_gar_a, placed_gar = warp_ootdiffusion_garment_to_subject(
                canvas_bchw,
                s3_bchw,
                s3_fg_alpha,
                ootd_strength=float(slot3_ootd_strength),
                preserve_neck_and_hands=bool(slot3_preserve_neck_and_hands),
                focus_mode=str(slot3_focus_mode),
            )
            fusion_noise_mask_bchw = torch.maximum(fusion_noise_mask_bchw, eff_gar_a * 0.78)
        s3_garment_isolated_bhwc = torch.clamp(placed_gar.permute(0, 2, 3, 1).contiguous(), 0.0, 1.0)
        ootd_preview_bchw = torch.clamp(placed_gar * 0.85 + canvas_bchw * 0.15, 0.0, 1.0)
    else:
        ootd_preview_bchw = canvas_bchw * 0.45

    face_preview_bchw = s1_char_crop_bhwc.permute(0, 3, 1, 2).contiguous() if (has_video_scene_template and s1_char_crop_bhwc is not None) else canvas_bchw.clone()
    s2_face_crop_bhwc = s2_bhwc
    if s2_bhwc is not None:
        s2_bchw = s2_bhwc.permute(0, 3, 1, 2).contiguous()
        if 'dual_subject' in str(slot2_focus_mode or '').lower() and s1_bhwc is not None:
            w_half = w // 2
            left_p = comfy.utils.common_upscale(canvas_bchw, w_half, h, 'lanczos', 'center')
            right_p2 = comfy.utils.common_upscale(s2_bchw, w - w_half, h, 'lanczos', 'center')
            joined = torch.cat([left_p, right_p2], dim=3)
            if s4_bhwc is not None:
                j_alpha = extract_layerdiffusion_foreground_alpha(joined, feather_radius=5.0)
                canvas_bchw = j_alpha * joined + (1.0 - j_alpha) * s4_bhwc.permute(0, 3, 1, 2).contiguous()
            else:
                canvas_bchw = joined
            face_preview_bchw = canvas_bchw.clone()
        else:
            src_geom = _detect_primary_face_geometry(s2_bchw)
            sx1 = max(0, int(round(src_geom['cx'] - src_geom['rx'] * 1.25)))
            sx2 = min(w, int(round(src_geom['cx'] + src_geom['rx'] * 1.25)))
            sy1 = max(0, int(round(src_geom['cy'] - src_geom['ry'] * 1.25)))
            sy2 = min(h, int(round(src_geom['cy'] + src_geom['ry'] * 1.25)))
            if sx2 - sx1 >= 24 and sy2 - sy1 >= 24:
                f_crop = F.interpolate(s2_bchw[:, :, sy1:sy2, sx1:sx2], size=(h, w), mode='bicubic', align_corners=False).clamp(0.0, 1.0)
                s2_face_crop_bhwc = f_crop.permute(0, 2, 3, 1).contiguous()
                face_preview_bchw = f_crop
            else:
                face_preview_bchw = s2_bchw.clone()
            canvas_bhwc_tmp = canvas_bchw.permute(0, 2, 3, 1).contiguous()
            canvas_bhwc_re = apply_reactor_and_adetailer_pass(
                canvas_bhwc_tmp,
                s2_bhwc,
                identity_strength=float(slot2_identity_strength) * 0.65,
                adetailer_denoise=float(slot2_adetailer_denoise),
                focus_mode=str(slot2_focus_mode),
            )
            canvas_bchw = canvas_bhwc_re.permute(0, 3, 1, 2).contiguous()

    q_h, q_w = max(64, h // 2), max(64, w // 2)
    p1 = F.interpolate(cn_maps['preview_bchw'], size=(q_h, q_w), mode='bilinear', align_corners=False)
    p2 = F.interpolate(face_preview_bchw, size=(q_h, q_w), mode='bilinear', align_corners=False)
    p3 = F.interpolate(ootd_preview_bchw, size=(q_h, q_w), mode='bilinear', align_corners=False)
    p4 = F.interpolate(depth_pack['preview_bchw'], size=(q_h, q_w), mode='bilinear', align_corners=False)
    quad_bchw = torch.cat([torch.cat([p1, p2], dim=3), torch.cat([p3, p4], dim=3)], dim=2)

    empty_canvas_out = torch.zeros((1, h, w, 3), dtype=torch.float32)
    master_out = torch.clamp(canvas_bchw.permute(0, 2, 3, 1).contiguous(), 0.0, 1.0) if has_image_slots else empty_canvas_out
    mask_out = torch.clamp(inpaint_mask_bchw[:, 0, :, :], 0.0, 1.0) if has_image_slots else torch.zeros((1, h, w), dtype=torch.float32)
    adaptive_fusion_mask = torch.clamp(fusion_noise_mask_bchw[:, 0, :, :], 0.0, 1.0)
    person_out = s2_face_crop_bhwc if s2_face_crop_bhwc is not None else empty_canvas_out
    cloth_out = s3_garment_isolated_bhwc if s3_garment_isolated_bhwc is not None else empty_canvas_out
    bg_out = s4_bhwc if s4_bhwc is not None else empty_canvas_out
    preview_out = torch.clamp(quad_bchw.permute(0, 2, 3, 1).contiguous(), 0.0, 1.0)
    ref_video_out = s5_video_bhwc if use_s5_mocap else (s5_video_bhwc[:1] if s5_video_bhwc is not None else master_out)

    prompt_directives = []
    if s1_bhwc is not None:
        if has_video_scene_template:
            prompt_directives.append('Use Reference Slot #1 strictly for the primary protagonist (<Main_Subject 1>) facial identity, species/race, skin color, hair, and anatomical traits, while using Reference Video Slot #5 as the scene layout, camera angle, posture, and action template to be re-enacted according to the user prompt.')
        else:
            prompt_directives.append('Preserve the primary protagonist (<Main_Subject 1>) species/race, skin pigment, facial identity, and anatomical traits from Reference Slot #1 while following the user prompt for scene setting, attire, and posture.')
    if s2_bhwc is not None:
        if 'dual_subject' in str(slot2_focus_mode or '').lower():
            prompt_directives.append('Include the second main protagonist (<Main_Subject 2>) from Reference Slot #2 interacting naturally alongside <Main_Subject 1>.')
        else:
            prompt_directives.append('SINGLE SUBJECT ONLY: Render a single unified protagonist (<Main_Subject 1>) whose facial identity, eyes, and bone structure match Reference Slot #2.')
    if s3_bhwc is not None and not same_s1_s3:
        prompt_directives.append('Dress the character seamlessly in the exact armor/clothing design, materials, and color palette from Reference Slot #3.')
    if s4_bhwc is not None:
        prompt_directives.append('Place the character seamlessly inside the exact environment, architecture, sky, and atmospheric lighting of Reference Slot #4.')
    if use_s5_mocap:
        prompt_directives.append('Use Reference Video Slot #5 (at start_offset_sec) as the scene composition, camera framing, posture, motion trajectory, and audio/dialogue template, transforming the scene and characters according to the user prompt.')

    omni_bundle = {
        'active': True,
        'has_image_slots': bool(has_image_slots),
        'has_video_scene_template': bool(has_video_scene_template),
        's5_has_two_people': bool(has_two_s5_people),
        'master_composite_image': master_out if has_image_slots else None,
        'slot5_scene_template_image': master_out if has_video_scene_template else None,
        'slot1_character_ref_image': s1_char_crop_bhwc,
        'slot1_skin_rgb': s1_skin_rgb_list,
        'raw_slot1_fullres': (master_out if has_video_scene_template else (s1_rgb if s1_rgb is not None else (master_out if has_image_slots else None))),
        'clean_slot1_image': (master_out if has_video_scene_template else (s1_bhwc if s1_bhwc is not None else (master_out if has_image_slots else None))),
        'inpaint_mask': mask_out,
        'has_inpaint_mask': bool(has_image_slots and float(mask_out.max().item()) > 0.02),
        'adaptive_fusion_noise_mask': adaptive_fusion_mask,
        'prompt_directives': ' '.join(prompt_directives),
        'slot1_focus_mode': str(slot1_focus_mode),
        'slot1_strength': float(slot1_strength),
        'slot2_person_image': s2_bhwc,
        'slot2_face_crop': s2_face_crop_bhwc,
        'slot2_focus_mode': str(slot2_focus_mode),
        'slot2_identity_strength': float(slot2_identity_strength),
        'slot2_adetailer_denoise': float(slot2_adetailer_denoise),
        'slot3_clothing_image': s3_garment_isolated_bhwc if s3_bhwc is not None else None,
        'slot3_raw_image': s3_bhwc,
        'slot3_same_as_slot1': bool(same_s1_s3),
        'slot3_focus_mode': str(slot3_focus_mode),
        'slot3_ootd_strength': float(slot3_ootd_strength),
        'slot3_preserve_neck_and_hands': bool(slot3_preserve_neck_and_hands),
        'slot4_background_image': s4_bhwc,
        'slot4_focus_mode': str(slot4_focus_mode),
        'slot4_depth_and_tile_strength': float(slot4_depth_and_tile_strength),
        'slot4_horizon_relight_match': float(slot4_horizon_relight_match),
        'slot5_reference_video': s5_video_bhwc if use_s5_mocap else None,
        'slot5_reference_audio': s5_audio_dict if use_s5_mocap else None,
        'slot5_start_offset_sec': float(slot5_start_offset_sec or 0.0),
        'slot5_duration_mode': str(slot5_duration_mode),
        'slot5_duration_seconds': float(eff_slot5_dur_s),
        'slot5_follow_master_duration': bool(follow_master_dur),
        'slot5_match_full_video': bool(match_full_vid),
        'slot5_focus_mode': str(slot5_focus_mode),
        'slot5_motion_strength': float(slot5_motion_strength),
        'slot5_video_path': str(s5_video_path or ''),
        'control_maps_preview': preview_out,
        'depth_1ch': depth_pack['depth_1ch'].detach().cpu(),
        'openpose_map': cn_maps['openpose'].detach().cpu(),
        'canny_map': cn_maps['canny'].detach().cpu(),
        'lineart_map': cn_maps['lineart'].detach().cpu(),
    }
    bus['omni_reference_bundle'] = omni_bundle
    if has_image_slots:
        bus['ingest_image'] = master_out
        bus['has_source_image'] = True
        bus['generation_mode'] = 'I2I_From_Source_Image'
    else:
        bus['ingest_image'] = None
        bus['has_source_image'] = False
        bus['generation_mode'] = 'T2I_Generate_New_Image'
    if s2_face_crop_bhwc is not None:
        bus['ref_image_2_person'] = s2_face_crop_bhwc
        bus['has_ref_image_2'] = True
    else:
        bus.pop('ref_image_2_person', None)
        bus['has_ref_image_2'] = False
    if s3_garment_isolated_bhwc is not None and not same_s1_s3:
        bus['ref_image_3_clothing'] = s3_garment_isolated_bhwc
        bus['has_ref_image_3'] = True
    if s4_bhwc is not None:
        bus['ref_image_4_background'] = s4_bhwc
        bus['has_ref_image_4'] = True
    if use_s5_mocap:
        bus['reference_motion_video'] = s5_video_bhwc
        bus['has_reference_motion_video'] = True
        bus['slot5_start_offset_sec'] = float(slot5_start_offset_sec or 0.0)
        bus['slot5_duration_mode'] = str(slot5_duration_mode)
        bus['slot5_duration_seconds'] = float(eff_slot5_dur_s)
        bus['slot5_follow_master_duration'] = bool(follow_master_dur)
        bus['slot5_match_full_video'] = bool(match_full_vid)
        bus['slot5_loaded_duration_sec'] = float(eff_slot5_dur_s)
        bus['slot5_motion_strength'] = float(slot5_motion_strength)
        bus['slot5_focus_mode'] = str(slot5_focus_mode)
        bus['slot5_video_path'] = str(s5_video_path or '')
        if isinstance(s5_audio_dict, dict):
            bus['reference_video_audio'] = s5_audio_dict

    ui_meta = []
    try:
        from datetime import datetime
        temp_dir = Path(folder_paths.get_temp_directory())
        temp_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        comp_fname = f'EZ_OmniRef_Master_{ts}.png'
        quad_fname = f'EZ_OmniRef_ControlQuad_{ts}.png'
        c_u8 = np.clip(master_out[0].numpy() * 255.0, 0, 255).astype(np.uint8)
        q_u8 = np.clip(preview_out[0].numpy() * 255.0, 0, 255).astype(np.uint8)
        Image.fromarray(c_u8).save(str(temp_dir / comp_fname))
        q_pil = Image.fromarray(q_u8)
        draw = ImageDraw.Draw(q_pil)
        draw.text((8, 6), '[1] OPENPOSE 17J + CANNY + LINEART', fill=(0, 240, 255))
        draw.text((q_w + 8, 6), '[2] REACTOR FACE-ID + ADETAILER', fill=(250, 204, 21))
        draw.text((8, q_h + 6), '[3] OOTDIFFUSION + LAYERDIFFUSION', fill=(244, 114, 182))
        draw.text((q_w + 8, q_h + 6), '[4] DEPTH-ANYTHING / MIDAS 3D', fill=(52, 211, 153))
        q_pil.save(str(temp_dir / quad_fname))
        ui_meta.append({'filename': comp_fname, 'anatomy_png': quad_fname, 'subfolder': '', 'type': 'temp'})
    except Exception:
        pass

    bus_delta = {
        'ingest_image': master_out,
        'has_source_image': True,
        'generation_mode': 'I2I_From_Source_Image',
        'base_width': int(w),
        'base_height': int(h),
        'source_aspect_ratio': round(float(w) / max(1.0, float(h)), 5),
    }
    if s2_face_crop_bhwc is not None:
        bus_delta['ref_image_2_person'] = s2_face_crop_bhwc
        bus_delta['has_ref_image_2'] = True
    if s3_garment_isolated_bhwc is not None and not same_s1_s3:
        bus_delta['ref_image_3_clothing'] = s3_garment_isolated_bhwc
        bus_delta['has_ref_image_3'] = True
    if s4_bhwc is not None:
        bus_delta['ref_image_4_background'] = s4_bhwc
        bus_delta['has_ref_image_4'] = True
    if use_s5_mocap:
        bus_delta['reference_motion_video'] = s5_video_bhwc
        bus_delta['has_reference_motion_video'] = True
        bus_delta['slot5_start_offset_sec'] = float(slot5_start_offset_sec or 0.0)
        bus_delta['slot5_duration_mode'] = str(slot5_duration_mode)
        bus_delta['slot5_duration_seconds'] = float(eff_slot5_dur_s)
        bus_delta['slot5_follow_master_duration'] = bool(follow_master_dur)
        bus_delta['slot5_match_full_video'] = bool(match_full_vid)
        bus_delta['slot5_loaded_duration_sec'] = float(eff_slot5_dur_s)
        bus_delta['slot5_motion_strength'] = float(slot5_motion_strength)
        bus_delta['slot5_focus_mode'] = str(slot5_focus_mode)
        bus_delta['slot5_video_path'] = str(s5_video_path or '')
        if isinstance(s5_audio_dict, dict):
            bus_delta['reference_video_audio'] = s5_audio_dict
    if len(omni_exec_cache) >= 8:
        omni_exec_cache.pop(next(iter(omni_exec_cache)), None)
    omni_exec_cache[omni_cache_key] = (master_out, mask_out, person_out, cloth_out, bg_out, preview_out, dict(omni_bundle), ref_video_out, list(ui_meta), bus_delta)
    return master_out, mask_out, person_out, cloth_out, bg_out, preview_out, bus, ref_video_out, ui_meta
