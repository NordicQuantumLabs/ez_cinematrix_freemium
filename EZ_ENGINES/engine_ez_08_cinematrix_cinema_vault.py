# -*- coding: utf-8 -*-

import gc
import math
import os
import re
import shutil
import subprocess
import sys
import wave
from datetime import datetime
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw, PngImagePlugin
import torch
import folder_paths
import comfy.model_management
import comfy.utils
FRAME_RATE_PRESETS = ['16 fps — Klassisk AI / Låg VRAM', '23.976 fps — NTSC Bio / Broadcast', '24 fps ★ [STANDARD - Biograf / Film]', '25 fps — PAL TV / Europa', '29.97 fps — NTSC TV / Sändning', '30 fps — Standard Webb / YouTube / Social', '48 fps — HFR Bio (High Frame Rate)', '50 fps — PAL HFR / Sport & Rörelse', '60 fps — Ultra-mjuk 60Hz Gaming & Webb', '120 fps — Extrem Slow-Motion / 120Hz Master', 'Custom (Använd custom_frame_rate nedan)']
QUALITY_CRF_PRESETS = ['CRF 0 — Lossless / Råmaster (100% förlustfri, extremt stor fil)', 'CRF 14 — Arkiv & Grading Master (99% kvalitet, nära förlustfri)', 'CRF 18 ★ [STANDARD - Visuellt Förlustfri Studio] (95% kvalitet, knivskarp)', 'CRF 20 — Hög Produktionskvalitet (90% kvalitet, optimal balans)', 'CRF 23 — Standard Webb & Social (80% kvalitet, halverad filstorlek)', 'CRF 28 — Kompakt Förhandsvisning / Proxy (65% kvalitet, liten fil)', 'CRF 35 — Snabb Utkast / Låg-bandbredd (45% kvalitet, minimal fil)', 'Custom (Använd custom_quality_crf nedan)']
VAULT_DATE_FOLDER_FORMAT_PRESETS = ['YYYY-MM-DD', 'None', 'YYYYMMDD', 'YYYY-MM', 'YYYY/MM/DD', 'YYYY_MM_DD', 'YYYY-MM-DD_HH-MM']
_VAULT_KEYPOINT_CACHE = {'detector': None, 'raft_net': None}


def _resolve_vault_date_subfolder(base_folder: Path, date_folder_format: str = 'YYYY-MM-DD', now_dt=None) -> Path:
    out_p = Path(base_folder)
    dt = now_dt if now_dt is not None else datetime.now()
    raw_fmt = str(date_folder_format or 'YYYY-MM-DD').strip()
    fmt_key = raw_fmt.split('(')[0].strip() if '(' in raw_fmt else raw_fmt
    if not fmt_key or fmt_key.lower() in ('none', 'off', 'false', 'disabled'):
        out_p.mkdir(parents=True, exist_ok=True)
        return out_p
    fmt_map = {
        'YYYY-MM-DD': '%Y-%m-%d',
        'YYYYMMDD': '%Y%m%d',
        'YYYY-MM': '%Y-%m',
        'YYYY/MM/DD': '%Y/%m/%d',
        'YYYY_MM_DD': '%Y_%m_%d',
        'YYYY-MM-DD_HH-MM': '%Y-%m-%d_%H-%M',
    }
    strf_pat = fmt_map.get(fmt_key.upper(), fmt_key if '%' in fmt_key else '%Y-%m-%d')
    sub_str = dt.strftime(strf_pat).strip('/\\')
    if sub_str and out_p.name != sub_str:
        target_p = out_p / sub_str
    else:
        target_p = out_p
    target_p.mkdir(parents=True, exist_ok=True)
    return target_p

def _ensure_portable_vault_torch_hub() -> str:
    try:
        from .engine_ez_hot_reload import unlock_and_bind_portable_torch_hub
        return unlock_and_bind_portable_torch_hub()
    except Exception:
        import sys
        exe_dir = Path(sys.executable).resolve().parent
        hub_dir = exe_dir / '.cache' / 'torch' / 'hub'
        (hub_dir / 'checkpoints').mkdir(parents=True, exist_ok=True)
        os.environ['TORCH_HOME'] = str(exe_dir / '.cache' / 'torch')
        try:
            torch.hub.set_dir(str(hub_dir))
        except Exception:
            pass
        return str(hub_dir)

def _get_cached_vault_raft_model(dev: torch.device):
    _ensure_portable_vault_torch_hub()
    raft_net = _VAULT_KEYPOINT_CACHE.get('raft_net')
    if raft_net is None:
        try:
            import torchvision.models.optical_flow as tv_flow
            weights = tv_flow.Raft_Small_Weights.DEFAULT
            raft_net = tv_flow.raft_small(weights=weights, progress=False).eval()
            _VAULT_KEYPOINT_CACHE['raft_net'] = raft_net
        except Exception:
            return None
    return raft_net.to(device=dev, dtype=torch.float32).eval()

def list_dynamic_upscale_models():
    models = folder_paths.get_filename_list('upscale_models') if 'upscale_models' in folder_paths.folder_names_and_paths else []
    cleaned = sorted(set(models))
    return ['None'] + cleaned if cleaned else ['None']

def list_dynamic_1x_detailer_models():
    models = folder_paths.get_filename_list('upscale_models') if 'upscale_models' in folder_paths.folder_names_and_paths else []
    cleaned = sorted(set(models))
    pref = [m for m in cleaned if ('1x' in m.lower() or 'skin' in m.lower() or 'detail' in m.lower())]
    rest = [m for m in cleaned if m not in pref]
    return ['None'] + pref + rest if cleaned else ['None']

def list_dynamic_rife_models():
    found = ['Optical_Flow_PyTorch_GridSample (Self-Contained)', 'rife49.pth', 'rife47.pth']
    try:
        base_m = Path(folder_paths.models_dir)
        for sub_d in ('rife', 'vfi', 'frame_interpolation'):
            cand_d = base_m / sub_d
            if cand_d.exists():
                for pth in cand_d.rglob('*.pth'):
                    if pth.name not in found:
                        found.append(pth.name)
    except Exception:
        pass
    return found

def _resolve_vault_frame_rate(frame_rate_sel, custom_frame_rate: float=24.0) -> float:
    import re
    if isinstance(frame_rate_sel, (int, float)):
        return max(1.0, min(240.0, float(frame_rate_sel)))
    s = str(frame_rate_sel or '').strip()
    if 'custom' in s.lower():
        return max(1.0, min(240.0, float(custom_frame_rate or 24.0)))
    m = re.match('^\\s*([0-9]+(?:\\.[0-9]+)?)', s)
    if m:
        return max(1.0, min(240.0, float(m.group(1))))
    return max(1.0, min(240.0, float(custom_frame_rate or 24.0)))

def _resolve_vault_quality_crf(quality_sel, custom_quality_crf: int=18) -> int:
    import re
    if isinstance(quality_sel, (int, float)):
        return max(0, min(51, int(round(float(quality_sel)))))
    s = str(quality_sel or '').strip()
    if 'custom' in s.lower():
        return max(0, min(51, int(round(float(custom_quality_crf if custom_quality_crf is not None else 18)))))
    m = re.search('CRF\\s*([0-9]+)', s, re.IGNORECASE) or re.match('^\\s*([0-9]+)\\s*$', s)
    if m:
        return max(0, min(51, int(m.group(1))))
    return max(0, min(51, int(round(float(custom_quality_crf if custom_quality_crf is not None else 18)))))

def _resolve_ffmpeg_binary() -> str:
    sys_ff = shutil.which('ffmpeg')
    if sys_ff:
        return sys_ff
    try:
        import imageio_ffmpeg
        ff_exe = imageio_ffmpeg.get_ffmpeg_exe()
        if ff_exe and os.path.exists(ff_exe):
            return ff_exe
    except Exception:
        pass
    try:
        base_p = Path(folder_paths.base_path)
        for cand in (base_p / 'ffmpeg.exe', base_p.parent / 'ffmpeg.exe', base_p.parent / 'python_embeded' / 'Scripts' / 'ffmpeg.exe', base_p.parent / 'ffmpeg' / 'bin' / 'ffmpeg.exe'):
            if cand.exists():
                return str(cand)
    except Exception:
        pass
    return ''

def _vault_gaussian_blur_2d(tensor_bchw: torch.Tensor, radius: float) -> torch.Tensor:
    if radius <= 0.05:
        return tensor_bchw.clone()
    import torch.nn.functional as F
    k_size = max(3, int(2 * int(3.0 * float(radius) + 0.5) + 1))
    sigma = max(0.1, float(radius))
    coords = torch.arange(k_size, dtype=tensor_bchw.dtype, device=tensor_bchw.device) - (k_size - 1) * 0.5
    k_1d = torch.exp(-coords ** 2 / (2.0 * sigma * sigma))
    k_1d = k_1d / k_1d.sum()
    ch = int(tensor_bchw.shape[1])
    k_horiz = k_1d.view(1, 1, 1, k_size).expand(ch, 1, 1, k_size).contiguous()
    k_vert = k_1d.view(1, 1, k_size, 1).expand(ch, 1, k_size, 1).contiguous()
    pad = k_size // 2
    padded_h = F.pad(tensor_bchw, (pad, pad, 0, 0), mode='reflect')
    blurred_h = F.conv2d(padded_h, k_horiz, groups=ch)
    padded_v = F.pad(blurred_h, (0, 0, pad, pad), mode='reflect')
    return F.conv2d(padded_v, k_vert, groups=ch)

def _vault_capsule_sdf_2d(grid_y: torch.Tensor, grid_x: torch.Tensor, y1: float, x1: float, y2: float, x2: float, radius: float) -> torch.Tensor:
    vy = float(y2 - y1)
    vx = float(x2 - x1)
    seg_len_sq = max(1e-06, vy * vy + vx * vx)
    t_proj = torch.clamp(((grid_y - float(y1)) * vy + (grid_x - float(x1)) * vx) / seg_len_sq, 0.0, 1.0)
    proj_y = float(y1) + t_proj * vy
    proj_x = float(x1) + t_proj * vx
    dist = torch.sqrt((grid_y - proj_y) ** 2 + (grid_x - proj_x) ** 2 + 1e-06)
    rad = max(2.0, float(radius))
    return torch.clamp(1.0 - torch.clamp((dist - rad * 0.65) / (rad * 0.75), 0.0, 1.0), 0.0, 1.0)

def _compute_vault_anatomy_zones(bchw: torch.Tensor, dock_cfg: dict=None, use_keypoint_detector: bool=False):
    import torch.nn.functional as F
    cfg = dict(dock_cfg) if isinstance(dock_cfg, dict) else {}
    (b_sz, _, h, w) = bchw.shape
    dev = bchw.device
    sens = float(cfg.get('detection_sensitivity', 0.45))
    feather_r = max(1.0, min(6.0, float(cfg.get('mask_feather_radius', 5.0))))
    (r_ch, g_ch, b_ch) = (bchw[:, 0:1], bchw[:, 1:2], bchw[:, 2:3])
    y_luma = 0.299 * r_ch + 0.587 * g_ch + 0.114 * b_ch
    cr = (r_ch - y_luma) * 0.713 + 0.5
    cb = (b_ch - y_luma) * 0.564 + 0.5
    tol = max(0.08, 0.22 - 0.12 * sens)
    human_skin = torch.exp(-(((cr - 0.575) / tol) ** 2 + ((cb - 0.435) / tol) ** 2))
    crimson_orc_skin = torch.exp(-(((cr - 0.655) / (tol * 1.45)) ** 2 + ((cb - 0.445) / (tol * 1.35)) ** 2)) * torch.clamp((r_ch - g_ch) * 2.4 + 0.25, 0.0, 1.0)
    orc_olive_skin = torch.exp(-(((cr - 0.465) / (tol * 1.25)) ** 2 + ((cb - 0.445) / (tol * 1.25)) ** 2)) * torch.clamp((g_ch - b_ch) * 2.5 + 0.35, 0.0, 1.0)
    fantasy_cool_skin = torch.exp(-(((cr - 0.48) / (tol * 1.3)) ** 2 + ((cb - 0.56) / (tol * 1.3)) ** 2))
    skin_chroma = torch.maximum(torch.maximum(human_skin, crimson_orc_skin * 0.96), torch.maximum(orc_olive_skin * 0.9, fantasy_cool_skin * 0.85))
    midtone = 1.0 - torch.clamp(torch.abs(y_luma - 0.52) * 1.45, 0.0, 0.85)
    base_skin = torch.clamp(0.72 * skin_chroma + 0.28 * midtone, 0.0, 1.0)
    gx = F.pad(y_luma[:, :, :, 1:] - y_luma[:, :, :, :-1], (0, 1, 0, 0))
    gy = F.pad(y_luma[:, :, 1:, :] - y_luma[:, :, :-1, :], (0, 0, 0, 1))
    grad_mag = torch.clamp(torch.sqrt(gx * gx + gy * gy + 1e-06) * 4.5, 0.0, 1.0)
    specular_eye = torch.clamp((y_luma - 0.78) * 4.0, 0.0, 1.0) * grad_mag
    ny = torch.arange(h, dtype=torch.float32, device=dev).view(1, 1, h, 1).expand(b_sz, 1, h, w) / float(max(1, h))
    nx = torch.arange(w, dtype=torch.float32, device=dev).view(1, 1, 1, w).expand(b_sz, 1, h, w) / float(max(1, w))
    fg_skin = torch.clamp(base_skin * (0.65 + 0.35 * grad_mag), 0.0, 1.0)
    face_m = torch.zeros((b_sz, 1, h, w), dtype=torch.float32, device=dev)
    eyes_m = torch.zeros((b_sz, 1, h, w), dtype=torch.float32, device=dev)
    mouth_m = torch.zeros((b_sz, 1, h, w), dtype=torch.float32, device=dev)
    torso_m = torch.zeros((b_sz, 1, h, w), dtype=torch.float32, device=dev)
    pelvic_m = torch.zeros((b_sz, 1, h, w), dtype=torch.float32, device=dev)
    hands_m = torch.zeros((b_sz, 1, h, w), dtype=torch.float32, device=dev)
    feet_m = torch.zeros((b_sz, 1, h, w), dtype=torch.float32, device=dev)
    kps_found = False
    if use_keypoint_detector:
        try:
            _ensure_portable_vault_torch_hub()
            import torchvision
            detector = _VAULT_KEYPOINT_CACHE.get('detector')
            if detector is None:
                weights = torchvision.models.detection.KeypointRCNN_ResNet50_FPN_Weights.DEFAULT
                detector = torchvision.models.detection.keypointrcnn_resnet50_fpn(weights=weights)
                detector.eval()
                _VAULT_KEYPOINT_CACHE['detector'] = detector
            detector = detector.to(device=dev)
            det_scale = min(1.0, 384.0 / float(max(h, w, 1)))
            nh = max(64, int(round(h * det_scale)))
            nw = max(64, int(round(w * det_scale)))
            small_bchw = F.interpolate(bchw.clamp(0.0, 1.0), size=(nh, nw), mode='bilinear', align_corners=False) if det_scale < 0.999 else bchw.clamp(0.0, 1.0)
            preds_all = []
            with torch.no_grad():
                for f_s in range(0, b_sz, 4):
                    f_e = min(b_sz, f_s + 4)
                    preds_all.extend(detector([small_bchw[i] for i in range(f_s, f_e)]))
            min_sc = max(0.18, 0.55 - 0.45 * sens)
            gy_1 = torch.arange(h, dtype=torch.float32, device=dev).view(1, 1, h, 1).expand(1, 1, h, w)
            gx_1 = torch.arange(w, dtype=torch.float32, device=dev).view(1, 1, 1, w).expand(1, 1, h, w)
            scale_r = max(12.0, min(float(h), float(w)) * 0.055)
            last_valid_kps = None
            for (f_idx, pred_f) in enumerate(preds_all):
                frame_kps = []
                if isinstance(pred_f, dict) and ('keypoints' in pred_f) and (pred_f['keypoints'].shape[0] > 0):
                    scores = pred_f['scores']
                    kps_tensor = pred_f['keypoints']
                    for p_i in range(min(4, int(kps_tensor.shape[0]))):
                        if scores.numel() > p_i and float(scores[p_i].item()) < min_sc and p_i > 0:
                            continue
                        if scores.numel() > 0 and float(scores[0].item()) < 0.18:
                            break
                        kp_np = kps_tensor[p_i].detach().cpu().numpy().copy()
                        if kp_np.shape[0] >= 17:
                            kp_np[:, 0] = kp_np[:, 0] / det_scale
                            kp_np[:, 1] = kp_np[:, 1] / det_scale
                            frame_kps.append(kp_np)
                if frame_kps:
                    last_valid_kps = frame_kps
                elif last_valid_kps is not None:
                    frame_kps = last_valid_kps
                if frame_kps:
                    kps_found = True
                    f_m1 = torch.zeros((1, 1, h, w), dtype=torch.float32, device=dev)
                    e_m1 = torch.zeros((1, 1, h, w), dtype=torch.float32, device=dev)
                    m_m1 = torch.zeros((1, 1, h, w), dtype=torch.float32, device=dev)
                    t_m1 = torch.zeros((1, 1, h, w), dtype=torch.float32, device=dev)
                    p_m1 = torch.zeros((1, 1, h, w), dtype=torch.float32, device=dev)
                    h_m1 = torch.zeros((1, 1, h, w), dtype=torch.float32, device=dev)
                    ft_m1 = torch.zeros((1, 1, h, w), dtype=torch.float32, device=dev)
                    for kp_np in frame_kps:
                        neck_y = (kp_np[5][1] + kp_np[6][1]) * 0.5
                        neck_x = (kp_np[5][0] + kp_np[6][0]) * 0.5
                        f_cap = _vault_capsule_sdf_2d(gy_1, gx_1, kp_np[0][1], kp_np[0][0], neck_y, neck_x, scale_r * 1.35)
                        e_cap = torch.clamp(_vault_capsule_sdf_2d(gy_1, gx_1, kp_np[1][1], kp_np[1][0], kp_np[2][1], kp_np[2][0], scale_r * 0.55), 0.0, 1.0)
                        m_y1 = kp_np[0][1] + (neck_y - kp_np[0][1]) * 0.22
                        m_x1 = kp_np[0][0] + (neck_x - kp_np[0][0]) * 0.22
                        m_y2 = kp_np[0][1] + (neck_y - kp_np[0][1]) * 0.68
                        m_x2 = kp_np[0][0] + (neck_x - kp_np[0][0]) * 0.68
                        m_cap = torch.clamp(_vault_capsule_sdf_2d(gy_1, gx_1, m_y1, m_x1, m_y2, m_x2, scale_r * 0.78), 0.0, 1.0)
                        t_cap = _vault_capsule_sdf_2d(gy_1, gx_1, neck_y, neck_x, (kp_np[11][1] + kp_np[12][1]) * 0.5, (kp_np[11][0] + kp_np[12][0]) * 0.5, scale_r * 1.85)
                        p_cap = _vault_capsule_sdf_2d(gy_1, gx_1, kp_np[11][1], kp_np[11][0], kp_np[12][1], kp_np[12][0], scale_r * 1.55)
                        h_cap = torch.clamp(_vault_capsule_sdf_2d(gy_1, gx_1, kp_np[7][1], kp_np[7][0], kp_np[9][1], kp_np[9][0], scale_r * 0.95) + _vault_capsule_sdf_2d(gy_1, gx_1, kp_np[8][1], kp_np[8][0], kp_np[10][1], kp_np[10][0], scale_r * 0.95), 0.0, 1.0)
                        ft_cap = torch.clamp(_vault_capsule_sdf_2d(gy_1, gx_1, kp_np[13][1], kp_np[13][0], kp_np[15][1], kp_np[15][0], scale_r * 1.05) + _vault_capsule_sdf_2d(gy_1, gx_1, kp_np[14][1], kp_np[14][0], kp_np[16][1], kp_np[16][0], scale_r * 1.05), 0.0, 1.0)
                        f_m1 = torch.maximum(f_m1, f_cap)
                        e_m1 = torch.maximum(e_m1, e_cap)
                        m_m1 = torch.maximum(m_m1, m_cap)
                        t_m1 = torch.maximum(t_m1, t_cap)
                        p_m1 = torch.maximum(p_m1, p_cap)
                        h_m1 = torch.maximum(h_m1, h_cap)
                        ft_m1 = torch.maximum(ft_m1, ft_cap)
                    face_m[f_idx:f_idx + 1] = _vault_gaussian_blur_2d(f_m1, feather_r * 0.4)
                    eyes_m[f_idx:f_idx + 1] = _vault_gaussian_blur_2d(e_m1, max(1.0, feather_r * 0.2))
                    mouth_m[f_idx:f_idx + 1] = _vault_gaussian_blur_2d(m_m1, max(1.0, feather_r * 0.22))
                    torso_m[f_idx:f_idx + 1] = _vault_gaussian_blur_2d(t_m1, feather_r * 0.45)
                    pelvic_m[f_idx:f_idx + 1] = _vault_gaussian_blur_2d(p_m1, feather_r * 0.45)
                    hands_m[f_idx:f_idx + 1] = _vault_gaussian_blur_2d(h_m1, feather_r * 0.35)
                    feet_m[f_idx:f_idx + 1] = _vault_gaussian_blur_2d(ft_m1, feather_r * 0.35)
            if kps_found:
                skin_gate = torch.clamp(base_skin * 0.85 + grad_mag * 0.25, 0.20, 1.0)
                face_m = torch.clamp(face_m * skin_gate, 0.0, 1.0)
                torso_m = torch.clamp(torso_m * skin_gate, 0.0, 1.0)
                pelvic_m = torch.clamp(pelvic_m * skin_gate, 0.0, 1.0)
                hands_m = torch.clamp(hands_m * skin_gate, 0.0, 1.0)
                feet_m = torch.clamp(feet_m * skin_gate, 0.0, 1.0)
                base_skin = torch.clamp(base_skin + 0.55 * torch.clamp(face_m + torso_m + pelvic_m + hands_m + feet_m, 0.0, 1.0), 0.0, 1.0)
            detector.to(device='cpu')
        except Exception:
            pass
    if not kps_found:
        w_sum = torch.clamp(fg_skin.sum(dim=(-2, -1), keepdim=True), min=1e-05)
        cx_s = (fg_skin * nx).sum(dim=(-2, -1), keepdim=True) / w_sum
        cy_s = (fg_skin * ny).sum(dim=(-2, -1), keepdim=True) / w_sum
        face_m = _vault_gaussian_blur_2d(fg_skin * torch.exp(-(((ny - torch.clamp(cy_s - 0.22, 0.08, 0.85)) / 0.15) ** 2 + ((nx - cx_s) / 0.24) ** 2)), feather_r * 0.5)
        eyes_m = _vault_gaussian_blur_2d(torch.clamp(face_m * (0.55 * grad_mag + 0.45 * specular_eye) * 2.2, 0.0, 1.0), max(1.0, feather_r * 0.25))
        mouth_raw = face_m * torch.exp(-(((ny - torch.clamp(cy_s - 0.14, 0.10, 0.88)) / 0.075) ** 2 + ((nx - cx_s) / 0.12) ** 2)) * (0.55 * grad_mag + 0.45 * specular_eye)
        mouth_peak = torch.clamp(mouth_raw.amax(dim=(-2, -1), keepdim=True), min=0.12)
        mouth_m = _vault_gaussian_blur_2d(torch.clamp(mouth_raw / mouth_peak, 0.0, 1.0), max(1.0, feather_r * 0.22))
        torso_m = _vault_gaussian_blur_2d(fg_skin * torch.exp(-(((ny - cy_s) / 0.18) ** 2 + ((nx - cx_s) / 0.26) ** 2)), feather_r * 0.65)
        pelvic_m = _vault_gaussian_blur_2d(fg_skin * torch.exp(-(((ny - torch.clamp(cy_s + 0.22, 0.15, 0.92)) / 0.15) ** 2 + ((nx - cx_s) / 0.23) ** 2)), feather_r * 0.6)
        hands_m = _vault_gaussian_blur_2d(fg_skin * torch.clamp(grad_mag * 1.35, 0.2, 1.0) * (1.0 - 0.65 * face_m), feather_r * 0.45)
        feet_m = _vault_gaussian_blur_2d(fg_skin * torch.exp(-((ny - torch.clamp(cy_s + 0.42, 0.25, 0.96)) / 0.11) ** 2), feather_r * 0.45)
    contour_shield = torch.clamp(grad_mag * (0.65 * hands_m + 0.75 * pelvic_m + 0.6 * feet_m + 0.85 * eyes_m + 0.92 * mouth_m), 0.0, 1.0)
    return {'base_skin': base_skin, 'face': face_m, 'eyes': eyes_m, 'mouth': mouth_m, 'hands': hands_m, 'torso': torso_m, 'pelvic': pelvic_m, 'feet': feet_m, 'contour_shield': contour_shield}

def _render_vault_anatomy_preview(bchw_first: torch.Tensor, zones_first: dict) -> torch.Tensor:
    dim_bg = bchw_first * 0.32
    r = dim_bg[:, 0:1] + 0.05 * zones_first['face'] + 0.1 * zones_first['hands'] + 0.92 * zones_first['torso'] + 0.96 * zones_first['pelvic'] + 0.66 * zones_first['feet'] + 0.95 * zones_first['eyes']
    g = dim_bg[:, 1:2] + 0.94 * zones_first['face'] + 0.82 * zones_first['hands'] + 0.28 * zones_first['torso'] + 0.62 * zones_first['pelvic'] + 0.33 * zones_first['feet'] + 0.98 * zones_first['eyes']
    b = dim_bg[:, 2:3] + 0.98 * zones_first['face'] + 0.5 * zones_first['hands'] + 0.6 * zones_first['torso'] + 0.08 * zones_first['pelvic'] + 0.96 * zones_first['feet'] + 0.98 * zones_first['eyes']
    overlay = torch.cat([r, g, b], dim=1)
    return torch.clamp(overlay.permute(0, 2, 3, 1).contiguous().detach().cpu(), 0.0, 1.0)

def _apply_edge_directed_lanczos_2x(frames_bhwc: torch.Tensor, batch_step: int=8) -> torch.Tensor:
    if not isinstance(frames_bhwc, torch.Tensor) or frames_bhwc.ndim != 4 or int(frames_bhwc.shape[0]) < 1:
        return frames_bhwc
    import torch.nn.functional as F
    (n_f, h_f, w_f, _) = frames_bhwc.shape
    target_h = int(h_f) * 2
    target_w = int(w_f) * 2
    dev = comfy.model_management.get_torch_device() if torch.cuda.is_available() else torch.device('cpu')
    step = max(1, min(16, int(batch_step or 8)))
    up_chunks = []
    bi = 0
    while bi < n_f:
        cur_end = min(n_f, bi + step)
        try:
            with torch.inference_mode():
                sub_cpu = frames_bhwc[bi:cur_end, :, :, :3].movedim(-1, 1)
                lanczos_nchw = comfy.utils.common_upscale(sub_cpu, target_w, target_h, 'lanczos', 'disabled').to(device=dev, dtype=torch.float32, non_blocking=True)
                src_dev = sub_cpu.to(device=dev, dtype=torch.float32, non_blocking=True)
                bilin_nchw = F.interpolate(src_dev, size=(target_h, target_w), mode='bilinear', align_corners=False)
                luma = 0.299 * lanczos_nchw[:, 0:1] + 0.587 * lanczos_nchw[:, 1:2] + 0.114 * lanczos_nchw[:, 2:3]
                gx = F.pad(luma[:, :, :, 1:] - luma[:, :, :, :-1], (0, 1, 0, 0))
                gy = F.pad(luma[:, :, 1:, :] - luma[:, :, :-1, :], (0, 0, 0, 1))
                grad_mag = torch.sqrt(gx * gx + gy * gy + 1e-06)
                edge_coh = torch.clamp(grad_mag * 6.5, 0.0, 1.0)
                local_min = -F.max_pool2d(-F.pad(bilin_nchw, (1, 1, 1, 1), mode='replicate'), kernel_size=3, stride=1)
                local_max = F.max_pool2d(F.pad(bilin_nchw, (1, 1, 1, 1), mode='replicate'), kernel_size=3, stride=1)
                clamped_lanczos = torch.clamp(lanczos_nchw, local_min - 0.015, local_max + 0.015)
                edge_dir_base = torch.lerp(lanczos_nchw, clamped_lanczos, edge_coh * 0.72)
                fine_blur = _vault_gaussian_blur_2d(edge_dir_base, 0.68)
                edge_unsharp = torch.clamp(edge_dir_base - fine_blur, -0.045, 0.045)
                sharpened = torch.clamp(edge_dir_base + edge_unsharp * (0.28 + 0.34 * edge_coh), 0.0, 1.0)
                up_chunks.append(sharpened.movedim(1, -1).contiguous().detach().cpu())
            bi = cur_end
        except RuntimeError as oom_exc:
            if 'out of memory' in str(oom_exc).lower() and step > 1:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                step = max(1, step // 2)
                continue
            nchw_fb = frames_bhwc[bi:cur_end, :, :, :3].movedim(-1, 1)
            up_chunks.append(comfy.utils.common_upscale(nchw_fb, target_w, target_h, 'lanczos', 'disabled').movedim(1, -1).detach().cpu())
            bi = cur_end
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return torch.cat(up_chunks, dim=0)


def _apply_vault_frequency_polish(frames_bhwc: torch.Tensor, blur_radius: float=2.5, texture_strength: float=1.06, mix_opacity: float=0.55, dock_cfg: dict=None, batch_step: int=8, identity_anchor: dict=None) -> torch.Tensor:
    if not isinstance(frames_bhwc, torch.Tensor) or frames_bhwc.ndim != 4 or float(mix_opacity) <= 0.01:
        return frames_bhwc
    (n_f, h_f, w_f, _) = frames_bhwc.shape
    res_scale = min(1.0, float(min(h_f, w_f)) / 1080.0)
    if res_scale < 0.65 and float(blur_radius) > 1.2:
        eff_blur = max(0.55, float(blur_radius) * res_scale * 0.58)
        eff_opac = float(mix_opacity) * 0.40
    else:
        eff_blur = max(0.60, float(blur_radius) * res_scale)
        eff_opac = float(mix_opacity)
    cfg = dict(dock_cfg) if isinstance(dock_cfg, dict) else {}
    w_face = float(cfg.get('lock_face_and_eyes', 1.0))
    w_hands = float(cfg.get('lock_hands_and_fingers', 1.25))
    w_torso = float(cfg.get('lock_torso_and_breasts', 1.1))
    w_pelvic = float(cfg.get('lock_intimate_pelvic_anatomy', 1.35))
    w_feet = float(cfg.get('lock_feet_and_toes', 1.15))
    raw_shield = float(cfg.get('eye_and_contour_sharpness_shield', 0.9))
    auto_mode_str = str(cfg.get('autopilot_mode', 'auto_self_driving')).strip().lower()
    shield_str = max(0.85, raw_shield) if auto_mode_str.startswith('auto') else max(0.35, raw_shield)
    hf_bank = identity_anchor.get('zone_hf_stats') if isinstance(identity_anchor, dict) and isinstance(identity_anchor.get('zone_hf_stats'), dict) else {}
    ref_face_hf = float((hf_bank.get('face') or {}).get('fine_hf_energy', 0.018) if isinstance(hf_bank.get('face'), dict) else 0.018)
    ref_torso_hf = float((hf_bank.get('torso') or {}).get('fine_hf_energy', 0.018) if isinstance(hf_bank.get('torso'), dict) else 0.018)
    ref_pelvic_hf = float((hf_bank.get('pelvic') or {}).get('fine_hf_energy', 0.020) if isinstance(hf_bank.get('pelvic'), dict) else 0.020)
    dev = comfy.model_management.get_torch_device() if torch.cuda.is_available() else torch.device('cpu')
    step = max(1, min(16, int(batch_step or 8)))
    prev_face_ema = None
    prev_eyes_ema = None
    prev_hands_ema = None
    prev_torso_ema = None
    prev_pelvic_ema = None
    bi = 0
    while bi < n_f:
        cur_end = min(n_f, bi + step)
        try:
            with torch.inference_mode():
                sub = frames_bhwc[bi:cur_end, :, :, :3].to(device=dev, dtype=torch.float32, non_blocking=True)
                bchw = sub.permute(0, 3, 1, 2).contiguous()
                zones = _compute_vault_anatomy_zones(bchw, dock_cfg=cfg, use_keypoint_detector=False)
                f_mask = zones['face']
                e_mask = zones['eyes']
                m_mask = zones.get('mouth', torch.zeros_like(e_mask))
                h_mask = zones['hands']
                t_mask = zones['torso']
                p_mask = zones['pelvic']
                if prev_face_ema is not None and prev_face_ema.shape[2:] == f_mask.shape[2:]:
                    f_mask = 0.65 * f_mask + 0.35 * prev_face_ema
                    e_mask = 0.65 * e_mask + 0.35 * prev_eyes_ema
                    h_mask = 0.65 * h_mask + 0.35 * prev_hands_ema
                    t_mask = 0.65 * t_mask + 0.35 * prev_torso_ema
                    p_mask = 0.65 * p_mask + 0.35 * prev_pelvic_ema
                prev_face_ema = f_mask[-1:].detach()
                prev_eyes_ema = e_mask[-1:].detach()
                prev_hands_ema = h_mask[-1:].detach()
                prev_torso_ema = t_mask[-1:].detach()
                prev_pelvic_ema = p_mask[-1:].detach()
                face_area = float(f_mask.mean().item())
                skin_area = float(zones['base_skin'].mean().item())
                is_distant_shot = (face_area < 0.065 or skin_area < 0.25)
                dist_scale = max(0.30, min(1.0, face_area / 0.070))
                cur_blur = max(0.45, eff_blur * dist_scale)
                low_freq = _vault_gaussian_blur_2d(bchw, cur_blur)
                raw_hf = bchw - low_freq
                mild_tex = 1.0 + 0.14 * max(0.0, float(texture_strength) - 1.0)
                recombined = torch.clamp(low_freq + raw_hf * mild_tex, 0.0, 1.0)
                anat_union = torch.clamp(0.65 * zones['base_skin'] + 0.45 * torch.clamp(w_face * f_mask + w_torso * t_mask + w_pelvic * p_mask + w_hands * h_mask + w_feet * zones['feet'], 0.0, 1.0), 0.0, 1.0)
                luma_c = 0.299 * bchw[:, 0:1] + 0.587 * bchw[:, 1:2] + 0.114 * bchw[:, 2:3]
                spec_highlight_shield = torch.clamp((luma_c - 0.68) * 3.2, 0.0, 1.0) * torch.clamp(p_mask + t_mask + f_mask, 0.0, 1.0)
                sharp_shield = torch.clamp(shield_str * (e_mask + 0.92 * m_mask + 0.85 * f_mask + 0.78 * zones['contour_shield'] + 0.55 * p_mask + 0.40 * t_mask + 0.65 * spec_highlight_shield), 0.0, 0.98)
                eff_alpha = _vault_gaussian_blur_2d(anat_union * (1.0 - sharp_shield), 0.85) * min(0.14, eff_opac * 0.20 * dist_scale)
                fine_hf = bchw - _vault_gaussian_blur_2d(bchw, 0.65)
                face_crisp_mask = torch.clamp(e_mask + 0.92 * m_mask + 0.80 * f_mask + 0.35 * zones['contour_shield'], 0.0, 1.0)
                crisp_gain = min(0.10, 0.06 * shield_str + 0.35 * max(0.0, float(texture_strength) - 1.0))
                crisp_bchw = torch.clamp((eff_alpha * recombined + (1.0 - eff_alpha) * bchw) + fine_hf * (face_crisp_mask * crisp_gain), 0.0, 1.0)
                sat_str_v = max(0.15, min(1.25, float(cfg.get('color_saturation_strength', 0.80) or 0.80)))
                style_low_v = str(cfg.get('style_target', 'realism') or 'realism').strip().lower()
                preserve_vivid_v = style_low_v in ('anime', 'cartoonish', 'unreal-engine-5', 'dark-fantasy-real', 'dark-fantasy-cgi', 'dark-fantasy')
                if (not preserve_vivid_v) and sat_str_v < 0.86:
                    lum_v = 0.299 * crisp_bchw[:, 0:1] + 0.587 * crisp_bchw[:, 1:2] + 0.114 * crisp_bchw[:, 2:3]
                    chroma_v = crisp_bchw - lum_v
                    c_span_v = crisp_bchw.amax(dim=1, keepdim=True) - crisp_bchw.amin(dim=1, keepdim=True)
                    knee_thr = 0.42 if style_low_v == 'original' else 0.36
                    neon_ex_v = torch.clamp(c_span_v - knee_thr, min=0.0)
                    soft_sp_v = torch.minimum(c_span_v, torch.full_like(c_span_v, knee_thr)) + torch.tanh(neon_ex_v / 0.24) * 0.14
                    roll_sc_v = soft_sp_v / torch.clamp(c_span_v, min=1e-05)
                    hi_desat_v = 1.0 - 0.24 * torch.clamp((lum_v - 0.74) / 0.26, 0.0, 1.0)
                    skin_guard_v = 1.0 - 0.14 * zones['base_skin'] * torch.clamp((c_span_v - 0.34) / 0.25, 0.0, 1.0)
                    eff_sat = max(0.92, sat_str_v) if style_low_v == 'original' else sat_str_v
                    graded_v = torch.clamp(lum_v + chroma_v * roll_sc_v * eff_sat * hi_desat_v * skin_guard_v, 0.0, 1.0)
                else:
                    graded_v = crisp_bchw
                blended = graded_v.permute(0, 2, 3, 1).contiguous()
                frames_bhwc[bi:cur_end, :, :, :3] = torch.clamp(blended.detach().cpu(), 0.0, 1.0)
            bi = cur_end
        except RuntimeError as oom_exc:
            if 'out of memory' in str(oom_exc).lower() and step > 1:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                step = max(1, step // 2)
                continue
            bi = cur_end
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return frames_bhwc

def _is_audio_vae_instance(vae_obj) -> bool:
    if vae_obj is None:
        return False
    fsm = getattr(vae_obj, 'first_stage_model', vae_obj)
    cls_tag = (str(getattr(fsm, '__class__', type(fsm)).__name__) + '.' + str(getattr(fsm, '__class__', type(fsm)).__module__)).lower()
    if 'audio' in cls_tag:
        return True
    if int(getattr(vae_obj, 'latent_channels', 0) or 0) == 32 or int(getattr(fsm, 'latent_dim', 0) or 0) == 32:
        return True
    return False

def _decode_single_vae_chunk(video_vae, chunk_latent, tile_sz: int=512, aggressive_purge: bool=True, target_pixel_frames: int=0) -> torch.Tensor:
    if _is_audio_vae_instance(video_vae):
        raise ValueError('[EZ-VAULT] Fel VAE-typ: MiniMaxH3AudioVAE (32ch Ljud-VAE) är inkopplad på video_vae-ingången i EZ [08]. Koppla video_vae från EZ [05] till video_vae i EZ [08] (och audio_vae till audio_vae)!')
    vid_only = chunk_latent
    if getattr(chunk_latent, 'is_nested', False) or hasattr(chunk_latent, 'tensors'):
        t_list = list(chunk_latent.tensors) if hasattr(chunk_latent, 'tensors') else list(chunk_latent.unbind())
        if t_list:
            vid_only = t_list[0]
    try:
        dec = video_vae.decode(vid_only)
    except Exception:
        if aggressive_purge:
            comfy.model_management.soft_empty_cache()
        dec = video_vae.decode_tiled(vid_only, tile_x=tile_sz, tile_y=tile_sz)
    if dec.ndim == 5:
        (b, t, h, w, c) = dec.shape
        out_f = dec.reshape(b * t, h, w, c).detach().cpu().float()
    else:
        out_f = dec.detach().cpu().float()
    if int(target_pixel_frames) > 0 and out_f.shape[0] > int(target_pixel_frames):
        out_f = out_f[:int(target_pixel_frames)]
    return torch.clamp(out_f, 0.0, 1.0)

def _resolve_audio_vae_sample_rate(audio_vae) -> int:
    fsm = getattr(audio_vae, 'first_stage_model', None)
    for cand in (getattr(audio_vae, 'audio_sample_rate', None), getattr(fsm, 'audio_sample_rate', None), getattr(audio_vae, 'sample_rate', None), getattr(fsm, 'sample_rate', None), getattr(audio_vae, 'sampling_rate', None), getattr(fsm, 'sampling_rate', None)):
        if isinstance(cand, (int, float)) and int(cand) >= 8000:
            return int(cand)
    return 32000

def _normalize_single_audio_tensor_to_np(wav_tensor: torch.Tensor):
    if not isinstance(wav_tensor, torch.Tensor):
        return None
    w_np = wav_tensor.detach().cpu().float().numpy()
    while w_np.ndim > 2 and w_np.shape[0] == 1:
        w_np = w_np[0]
    if w_np.ndim == 1:
        w_np = w_np[:, None]
    elif w_np.ndim == 2 and w_np.shape[0] <= 2 and (w_np.shape[1] > w_np.shape[0]):
        w_np = w_np.T
    if w_np.size > 0:
        w_np = np.nan_to_num(w_np, nan=0.0, posinf=0.0, neginf=0.0)
        w_np = w_np - np.mean(w_np, axis=0, keepdims=True)
    return w_np

def _suppress_vocal_formant_chatter_in_sfx(w_np: np.ndarray, sr: int, audio_mode: str = '') -> np.ndarray:
    if w_np is None or w_np.size < 256:
        return w_np
    try:
        arr = w_np.astype(np.float32, copy=True)
        arr = arr - np.mean(arr, axis=0, keepdims=True)
        n_s = int(arr.shape[0])
        sr_f = float(max(8000, int(sr)))
        freqs = np.fft.rfftfreq(n_s, d=1.0 / sr_f)
        hp_curve = np.clip((freqs - 24.0) / 28.0, 0.0, 1.0).astype(np.float32)
        lp_curve = np.clip((15200.0 - freqs) / 1800.0, 0.15, 1.0).astype(np.float32)
        eq_curve = hp_curve * lp_curve
        mode_low = str(audio_mode or '').strip().lower()
        is_non_vocal_sfx = ('sfx_only' in mode_low or 'no_music' in mode_low or mode_low == 'sfx_only')
        is_inst_bgm = ('instrumental' in mode_low)
        if is_non_vocal_sfx or is_inst_bgm:
            f0_notch = 1.0 - (0.85 if is_non_vocal_sfx else 0.45) * np.exp(-0.5 * ((freqs - 240.0) / 135.0) ** 2)
            f1_notch = 1.0 - (0.88 if is_non_vocal_sfx else 0.56) * np.exp(-0.5 * ((freqs - 680.0) / 360.0) ** 2)
            f2_notch = 1.0 - (0.88 if is_non_vocal_sfx else 0.58) * np.exp(-0.5 * ((freqs - 1850.0) / 700.0) ** 2)
            f3_notch = 1.0 - (0.76 if is_non_vocal_sfx else 0.48) * np.exp(-0.5 * ((freqs - 3100.0) / 560.0) ** 2)
            eq_curve = (eq_curve * f0_notch * f1_notch * f2_notch * f3_notch).astype(np.float32)
        if arr.ndim == 2:
            spec = np.fft.rfft(arr, axis=0)
            arr = np.fft.irfft(spec * eq_curve[:, None], n=n_s, axis=0).astype(np.float32)
        else:
            spec = np.fft.rfft(arr)
            arr = np.fft.irfft(spec * eq_curve, n=n_s).astype(np.float32)
        if is_non_vocal_sfx and n_s >= int(sr_f * 0.08):
            win_len = max(64, int(sr_f * 0.035))
            env = np.sqrt(np.convolve(np.mean(arr ** 2, axis=-1) if arr.ndim == 2 else arr ** 2, np.ones(win_len, dtype=np.float32) / float(win_len), mode='same') + 1e-08)
            p85 = float(np.percentile(env, 85.0))
            if p85 > 1e-05:
                duck_gain = np.clip(p85 / np.maximum(env, p85), 0.32, 1.0).astype(np.float32)
                arr = arr * (duck_gain[:, None] if arr.ndim == 2 else duck_gain)
        fade_len = min(int(sr * 0.015), n_s // 8)
        if fade_len >= 8:
            fade_in = np.linspace(0.0, 1.0, fade_len, dtype=np.float32)
            fade_out = np.linspace(1.0, 0.0, fade_len, dtype=np.float32)
            if arr.ndim == 2:
                arr[:fade_len] *= fade_in[:, None]
                arr[-fade_len:] *= fade_out[:, None]
            else:
                arr[:fade_len] *= fade_in
                arr[-fade_len:] *= fade_out
        return np.tanh(arr * 1.08) / np.tanh(1.08)
    except Exception:
        return w_np

def _decode_audio_latent_to_wav(audio_vae, audio_latent, temp_wav_path: Path, audio_win_latents: list=None, overlap_t: int=2, audio_soundtrack_mode: str='', **kwargs) -> bool:
    if audio_vae is None or (audio_latent is None and (not audio_win_latents)):
        return False
    try:
        sr = _resolve_audio_vae_sample_rate(audio_vae)
        native_fps = max(1.0, float(kwargs.get('native_fps', 24.0) or 24.0))
        target_dur_sec = float(kwargs.get('target_duration_sec', 0.0) or 0.0)
        w_np = None
        if audio_latent is not None:
            try:
                aud_in = audio_latent
                if getattr(audio_latent, 'is_nested', False) or hasattr(audio_latent, 'tensors'):
                    t_l = list(audio_latent.tensors) if hasattr(audio_latent, 'tensors') else list(audio_latent.unbind())
                    aud_in = t_l[1] if len(t_l) > 1 else t_l[0]
                wav_tensor = audio_vae.decode(aud_in)
                if isinstance(wav_tensor, dict) and 'waveform' in wav_tensor:
                    sr = int(wav_tensor.get('sample_rate', sr) or sr)
                    wav_tensor = wav_tensor['waveform']
                cand_np = _normalize_single_audio_tensor_to_np(wav_tensor)
                if cand_np is not None and cand_np.shape[0] >= 64:
                    w_np = cand_np
            except Exception:
                w_np = None
        if w_np is None and isinstance(audio_win_latents, list) and len(audio_win_latents) >= 2:
            pcm_accum = None
            ov_tok = max(1, int(overlap_t or 1))
            ov_px = max(1, 17 * (ov_tok // 5) + sum((1, 4, 4, 4, 4)[:ov_tok % 5]))
            for (w_lat, _cur_v_len) in audio_win_latents:
                aud_in = w_lat
                if getattr(w_lat, 'is_nested', False) or hasattr(w_lat, 'tensors'):
                    t_l = list(w_lat.tensors) if hasattr(w_lat, 'tensors') else list(w_lat.unbind())
                    aud_in = t_l[1] if len(t_l) > 1 else t_l[0]
                dec_w = audio_vae.decode(aud_in)
                if isinstance(dec_w, dict) and 'waveform' in dec_w:
                    sr = int(dec_w.get('sample_rate', sr) or sr)
                    dec_w = dec_w['waveform']
                cur_pcm = _normalize_single_audio_tensor_to_np(dec_w)
                if cur_pcm is None or cur_pcm.shape[0] < 16:
                    continue
                seg_f_cnt = max(22, int(_cur_v_len or 243))
                target_seg_samples = max(64, int(round(float(seg_f_cnt) / native_fps * float(sr))))
                if cur_pcm.shape[0] > target_seg_samples:
                    cur_pcm = cur_pcm[:target_seg_samples]
                elif cur_pcm.shape[0] < target_seg_samples:
                    pad_len = target_seg_samples - cur_pcm.shape[0]
                    pad_shape = (pad_len, cur_pcm.shape[1]) if cur_pcm.ndim == 2 else (pad_len,)
                    cur_pcm = np.concatenate([cur_pcm, np.zeros(pad_shape, dtype=cur_pcm.dtype)], axis=0)
                if pcm_accum is None:
                    pcm_accum = cur_pcm
                else:
                    prop_ov = max(1, int(round(float(ov_px) / native_fps * float(sr))))
                    ov_s = min(prop_ov, cur_pcm.shape[0] // 3, pcm_accum.shape[0] // 3)
                    if ov_s >= 32:
                        fade_t = np.linspace(0.0, 0.5 * np.pi, ov_s, dtype=np.float32)[:, None]
                        w_in = np.sin(fade_t)
                        w_out = np.cos(fade_t)
                        cross = pcm_accum[-ov_s:] * w_out + cur_pcm[:ov_s] * w_in
                        pcm_accum = np.concatenate([pcm_accum[:-ov_s], cross, cur_pcm[ov_s:]], axis=0)
                    else:
                        pcm_accum = np.concatenate([pcm_accum, cur_pcm[ov_s:]], axis=0)
            w_np = pcm_accum
        if w_np is None or w_np.size == 0:
            return False
        if target_dur_sec > 0.1:
            tgt_total_samples = max(64, int(round(target_dur_sec * float(sr))))
            if w_np.shape[0] > tgt_total_samples:
                w_np = w_np[:tgt_total_samples]
        w_np = np.nan_to_num(w_np, nan=0.0, posinf=0.0, neginf=0.0)
        eff_aud_mode = str(audio_soundtrack_mode or '').strip() or 'sfx_only'
        w_np = _suppress_vocal_formant_chatter_in_sfx(w_np, sr, eff_aud_mode)
        peak = float(np.max(np.abs(w_np)))
        if peak > 0.95:
            w_np = w_np * (0.95 / peak)
        pcm16 = np.clip(w_np * 32767.0, -32768, 32767).astype(np.int16)
        channels = int(pcm16.shape[1]) if pcm16.ndim == 2 else 1
        with wave.open(str(temp_wav_path), 'wb') as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(pcm16.tobytes())
        return temp_wav_path.exists() and temp_wav_path.stat().st_size > 128
    except Exception:
        return False

def _encode_video_with_pyav(frames_bhwc: torch.Tensor, fps: float, output_path: Path, codec: str, quality: int, audio_wav_path: Path=None, audio_codec: str='Auto', save_metadata: bool=True, metadata_payload: dict=None) -> bool:
    if not isinstance(frames_bhwc, torch.Tensor) or frames_bhwc.shape[0] == 0:
        return False
    try:
        import av
        from fractions import Fraction
        (n_frames, h, w, _) = frames_bhwc.shape
        even_w = max(16, int(w) // 2 * 2)
        even_h = max(16, int(h) // 2 * 2)
        codec_low = str(codec or 'H.264').lower()
        crf_val = str(max(0, min(51, int(quality))))
        v_codec = 'libx265' if 'h.265' in codec_low or 'hevc' in codec_low else 'libvpx-vp9' if 'vp9' in codec_low else 'libx264'
        fps_frac = Fraction(max(1.0, float(fps))).limit_denominator(1000)
        container = av.open(str(output_path), mode='w')
        if save_metadata and isinstance(metadata_payload, dict):
            try:
                container.metadata['title'] = str(metadata_payload.get('video_filename') or output_path.stem)
                container.metadata['artist'] = 'EZ Cinematrix Studio v2.6'
                container.metadata['comment'] = json.dumps(metadata_payload, ensure_ascii=False)
            except Exception:
                pass
        v_stream = container.add_stream(v_codec, rate=fps_frac)
        v_stream.width = even_w
        v_stream.height = even_h
        v_stream.pix_fmt = 'yuv420p'
        if v_codec in ('libx264', 'libx265'):
            v_stream.options = {'crf': crf_val, 'preset': 'fast'}
        chunk_sz = 32
        for s_idx in range(0, n_frames, chunk_sz):
            e_idx = min(n_frames, s_idx + chunk_sz)
            sub_t = frames_bhwc[s_idx:e_idx, :even_h, :even_w, :3]
            batch_u8 = (sub_t * 255.0).clamp(0.0, 255.0).to(torch.uint8).contiguous().numpy()
            for f_arr in batch_u8:
                vf = av.VideoFrame.from_ndarray(f_arr, format='rgb24')
                for pkt in v_stream.encode(vf):
                    container.mux(pkt)
        for pkt in v_stream.encode():
            container.mux(pkt)
        has_audio = audio_wav_path is not None and audio_wav_path.exists() and (str(audio_codec).lower() != 'mute')
        if has_audio:
            try:
                in_aud = av.open(str(audio_wav_path), mode='r')
                if in_aud.streams.audio:
                    in_a_stream = in_aud.streams.audio[0]
                    a_codec_name = 'aac' if str(output_path.suffix).lower() in ('.mp4', '.mov', '.mkv') else 'libopus'
                    out_a_stream = container.add_stream(a_codec_name, rate=int(in_a_stream.rate or 44100))
                    for a_frame in in_aud.decode(in_a_stream):
                        a_frame.pts = None
                        for pkt in out_a_stream.encode(a_frame):
                            container.mux(pkt)
                    for pkt in out_a_stream.encode():
                        container.mux(pkt)
                in_aud.close()
            except Exception:
                pass
        container.close()
        return output_path.exists() and output_path.stat().st_size > 512
    except Exception:
        return False

_FFMPEG_ENC_CACHE = {}

def _probe_available_ffmpeg_encoders(ffmpeg_bin: str) -> set:
    if not ffmpeg_bin:
        return set()
    if ffmpeg_bin in _FFMPEG_ENC_CACHE:
        return _FFMPEG_ENC_CACHE[ffmpeg_bin]
    avail = set()
    try:
        res = subprocess.run([ffmpeg_bin, '-hide_banner', '-encoders'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=5, check=False)
        out_txt = res.stdout or ''
        for cand in ('libx264', 'libx265', 'libsvtav1', 'libvpx-vp9', 'prores_ks', 'h264_nvenc', 'hevc_nvenc', 'av1_nvenc', 'h264_amf', 'hevc_amf', 'h264_videotoolbox', 'hevc_videotoolbox', 'h264_qsv', 'hevc_qsv'):
            if cand in out_txt:
                avail.add(cand)
    except Exception:
        avail = {'libx264', 'libx265'}
    _FFMPEG_ENC_CACHE[ffmpeg_bin] = avail
    return avail

def _encode_video_with_ffmpeg(frames_bhwc: torch.Tensor, fps: float, output_path: Path, codec: str, container: str, bit_depth: str, quality: int, audio_wav_path: Path=None, audio_codec: str='Auto', audio_bitrate: str='192k', crop_to_audio: bool=False, save_metadata: bool=True, metadata_payload: dict=None) -> bool:
    if not isinstance(frames_bhwc, torch.Tensor) or frames_bhwc.shape[0] == 0:
        return False
    ffmpeg_bin = _resolve_ffmpeg_binary()
    if not ffmpeg_bin:
        return _encode_video_with_pyav(frames_bhwc, fps, output_path, codec, quality, audio_wav_path, audio_codec, save_metadata=save_metadata, metadata_payload=metadata_payload)
    (n_frames, h, w, _) = frames_bhwc.shape
    even_w = max(16, int(w) // 2 * 2)
    even_h = max(16, int(h) // 2 * 2)
    codec_low = str(codec or 'H.264').lower()
    cont_low = str(container or 'MP4').lower()
    depth_low = str(bit_depth or 'Auto').lower()
    pix_fmt = 'yuv420p10le' if '10-bit' in depth_low else 'yuv420p'
    crf_val = str(max(0, min(51, int(quality))))
    try:
        from .engine_ez_01_cinematrix_canvas_ingest import enforce_cinematrix_thermal_shield, _THERMAL_SENTINEL_CACHE
        enforce_cinematrix_thermal_shield('Vault-FFmpeg-Encode', force_inter_stage_pause=True)
        sh_cfg = _THERMAL_SENTINEL_CACHE.get('active_shield_cfg') or {}
        max_ff_t = int(sh_cfg.get('max_ffmpeg_threads', max(2, min(6, int(os.cpu_count() or 8) // 2))))
    except Exception:
        max_ff_t = max(2, min(6, int(os.cpu_count() or 8) // 2))
    cpu_thr = str(max(2, min(12, max_ff_t)))
    avail_enc = _probe_available_ffmpeg_encoders(ffmpeg_bin)
    has_nv = bool(torch.cuda.is_available() and (not getattr(torch.version, 'hip', None)))
    has_amf = bool(torch.cuda.is_available() and getattr(torch.version, 'hip', None))
    has_vt = bool(hasattr(torch.backends, 'mps') and torch.backends.mps.is_available())
    encoder_profiles = []
    if 'h.265' in codec_low or 'hevc' in codec_low:
        if has_nv and 'hevc_nvenc' in avail_enc and pix_fmt == 'yuv420p':
            encoder_profiles.append(['-c:v', 'hevc_nvenc', '-rc', 'vbr', '-cq', crf_val, '-preset', 'p5', '-tune', 'hq', '-pix_fmt', pix_fmt, '-tag:v', 'hvc1'])
        elif has_amf and 'hevc_amf' in avail_enc and pix_fmt == 'yuv420p':
            encoder_profiles.append(['-c:v', 'hevc_amf', '-rc', 'cqp', '-qp_i', crf_val, '-qp_p', crf_val, '-pix_fmt', pix_fmt, '-tag:v', 'hvc1'])
        elif has_vt and 'hevc_videotoolbox' in avail_enc and pix_fmt == 'yuv420p':
            encoder_profiles.append(['-c:v', 'hevc_videotoolbox', '-q:v', str(max(35, 100 - int(quality) * 2)), '-pix_fmt', pix_fmt, '-tag:v', 'hvc1'])
        encoder_profiles.append(['-c:v', 'libx265', '-crf', crf_val, '-preset', 'fast', '-threads', cpu_thr, '-pix_fmt', pix_fmt, '-tag:v', 'hvc1'])
    elif 'av1' in codec_low:
        if has_nv and 'av1_nvenc' in avail_enc and pix_fmt == 'yuv420p':
            encoder_profiles.append(['-c:v', 'av1_nvenc', '-rc', 'vbr', '-cq', crf_val, '-preset', 'p5', '-pix_fmt', pix_fmt])
        encoder_profiles.append(['-c:v', 'libsvtav1', '-crf', crf_val, '-preset', '8', '-pix_fmt', pix_fmt])
    elif 'vp9' in codec_low:
        encoder_profiles.append(['-c:v', 'libvpx-vp9', '-crf', crf_val, '-b:v', '0', '-deadline', 'good', '-cpu-used', '4', '-row-mt', '1', '-pix_fmt', pix_fmt])
    elif 'prores' in codec_low:
        encoder_profiles.append(['-c:v', 'prores_ks', '-profile:v', '2', '-threads', cpu_thr, '-pix_fmt', 'yuv422p10le'])
    else:
        if has_nv and 'h264_nvenc' in avail_enc and pix_fmt == 'yuv420p':
            encoder_profiles.append(['-c:v', 'h264_nvenc', '-rc', 'vbr', '-cq', crf_val, '-preset', 'p5', '-tune', 'hq', '-bf', '2', '-g', '48', '-pix_fmt', pix_fmt])
        elif has_amf and 'h264_amf' in avail_enc and pix_fmt == 'yuv420p':
            encoder_profiles.append(['-c:v', 'h264_amf', '-rc', 'cqp', '-qp_i', crf_val, '-qp_p', crf_val, '-pix_fmt', pix_fmt])
        elif has_vt and 'h264_videotoolbox' in avail_enc and pix_fmt == 'yuv420p':
            encoder_profiles.append(['-c:v', 'h264_videotoolbox', '-q:v', str(max(35, 100 - int(quality) * 2)), '-pix_fmt', pix_fmt])
        encoder_profiles.append(['-c:v', 'libx264', '-crf', crf_val, '-preset', 'fast', '-profile:v', 'high', '-bf', '2', '-g', '48', '-threads', cpu_thr, '-pix_fmt', pix_fmt])
    has_audio = audio_wav_path is not None and audio_wav_path.exists() and (str(audio_codec).lower() != 'mute')
    for v_args in encoder_profiles:
        cmd = [ffmpeg_bin, '-y', '-hide_banner', '-loglevel', 'error', '-f', 'rawvideo', '-vcodec', 'rawvideo', '-s', f'{w}x{h}', '-pix_fmt', 'rgb24', '-r', f'{max(1.0, float(fps)):.4f}', '-i', '-']
        if has_audio:
            cmd.extend(['-i', str(audio_wav_path)])
        if even_w != w or even_h != h:
            cmd.extend(['-vf', f'scale={even_w}:{even_h}:flags=lanczos'])
        cmd.extend(v_args)
        if has_audio:
            vid_dur_s = float(n_frames) / max(1.0, float(fps))
            cmd.extend(['-af', f'aresample=async=1:first_pts=0,apad=whole_dur={vid_dur_s:.3f}', '-t', f'{vid_dur_s:.3f}'])
            ac_low = str(audio_codec or 'Auto').lower()
            ab_str = str(audio_bitrate or '192k')
            if 'opus' in ac_low or (ac_low == 'auto' and cont_low == 'webm'):
                cmd.extend(['-c:a', 'libopus', '-b:a', ab_str])
            elif 'flac' in ac_low:
                cmd.extend(['-c:a', 'flac'])
            elif 'wav' in ac_low or 'pcm' in ac_low:
                cmd.extend(['-c:a', 'pcm_s16le'])
            else:
                cmd.extend(['-c:a', 'aac', '-b:a', ab_str])
            if crop_to_audio:
                cmd.append('-shortest')
        if save_metadata:
            if isinstance(metadata_payload, dict) and metadata_payload:
                meta_json_str = json.dumps(metadata_payload, ensure_ascii=False)
                desc_str = str(metadata_payload.get('h3_video_timeline_prompt') or metadata_payload.get('krea2_image_prompt') or 'EZ Cinematrix Studio v2.6')[:1024]
                cmd.extend([
                    '-metadata', f'title={output_path.stem}',
                    '-metadata', 'artist=EZ Cinematrix Studio v2.6',
                    '-metadata', f'description={desc_str}',
                    '-metadata', f'comment={meta_json_str}',
                ])
            else:
                cmd.extend(['-metadata', 'comment=EZ Cinematrix Studio v2.6'])
        else:
            cmd.extend(['-map_metadata', '-1'])
        if cont_low in ('mp4', 'mov'):
            cmd.extend(['-movflags', '+faststart'])
        cmd.append(str(output_path))
        proc = None
        try:
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, bufsize=16 * 1024 * 1024)
            chunk_sz = 32
            for s_idx in range(0, n_frames, chunk_sz):
                if proc.poll() is not None:
                    break
                e_idx = min(n_frames, s_idx + chunk_sz)
                batch_u8 = (frames_bhwc[s_idx:e_idx] * 255.0).clamp(0.0, 255.0).to(torch.uint8).contiguous().numpy()
                proc.stdin.write(memoryview(batch_u8))
            try:
                proc.stdin.close()
            except Exception:
                pass
            proc.wait(timeout=180)
            if proc.returncode == 0 and output_path.exists() and (output_path.stat().st_size > 512):
                return True
        except Exception:
            if proc is not None:
                try:
                    proc.kill()
                except Exception:
                    pass
            if output_path.exists() and output_path.stat().st_size > 4096:
                return True
    return _encode_video_with_pyav(frames_bhwc, fps, output_path, codec, quality, audio_wav_path, audio_codec, save_metadata=save_metadata, metadata_payload=metadata_payload)

def _apply_real_upscale_model(frames_bhwc: torch.Tensor, upscale_model_name: str, tile_sz: int=512, target_scale_cap: int=2, batch_step: int=8) -> torch.Tensor:
    if not upscale_model_name or str(upscale_model_name) == 'None' or frames_bhwc.shape[0] == 0:
        return frames_bhwc
    try:
        m_name = str(upscale_model_name)
        m_low = m_name.lower()
        m_path = folder_paths.get_full_path('upscale_models', m_name)
        if not m_path:
            return frames_bhwc
        sd = comfy.utils.load_torch_file(m_path, safe_load=True)
        try:
            from spandrel import ModelLoader
            up_model = ModelLoader().load_from_state_dict(sd).eval()
        except Exception:
            from comfy_extras.chainner_models import model_loading
            up_model = model_loading.load_state_dict(sd).eval()
        dev = comfy.model_management.get_torch_device()
        model_dt = torch.float16 if dev.type == 'cuda' else torch.float32
        try:
            up_model = up_model.to(device=dev, dtype=model_dt)
        except Exception:
            model_dt = torch.float32
            up_model = up_model.to(device=dev)
        raw_scale = int(getattr(up_model, 'scale', 0) or (1 if '1x' in m_low else 4 if '4x' in m_low else 8 if '8x' in m_low else 2))
        scale_f = float(max(1, raw_scale))
        (total_f, h, w, _c) = frames_bhwc.shape
        cap_scale = max(1, int(target_scale_cap or 2))
        target_h = int(h * cap_scale)
        target_w = int(w * cap_scale)
        blend_1x = 0.08 if 'contrast' in m_low else 0.11
        is_inplace_1x = (cap_scale == 1 and raw_scale == 1)
        key_stride = 1
        key_indices = list(range(0, total_f))
        max_b = 8 if raw_scale >= 4 else 16
        step = max(1, min(max_b, int(batch_step or max_b)))
        eff_tile = max(384, min(int(tile_sz or 768), 768 if max(h, w) <= 1024 else 512))
        key_results = {}
        ki = 0
        tot_up_batches = max(1, (len(key_indices) + step - 1) // step)
        while ki < len(key_indices):
            if hasattr(comfy.model_management, 'throw_exception_if_processing_interrupted'):
                comfy.model_management.throw_exception_if_processing_interrupted()
            try:
                from .engine_ez_01_cinematrix_canvas_ingest import enforce_cinematrix_thermal_shield
                sh_res = enforce_cinematrix_thermal_shield(
                    f'Vault-Upscale-{m_name}',
                    step_idx=ki // max(1, step),
                    total_steps=tot_up_batches,
                    force_inter_stage_pause=(ki == 0),
                )
                rt_ov = sh_res.get('runtime_overrides') if isinstance(sh_res, dict) and isinstance(sh_res.get('runtime_overrides'), dict) else {}
                if bool(rt_ov.get('is_warm', False)):
                    if rt_ov.get('tile_size'):
                        eff_tile = max(256, min(eff_tile, int(rt_ov['tile_size'])))
                    if rt_ov.get('upscale_chunk_t'):
                        step = max(1, min(step, int(rt_ov['upscale_chunk_t'])))
            except Exception:
                pass
            cur_end = min(len(key_indices), ki + step)
            batch_ids = key_indices[ki:cur_end]
            try:
                with torch.inference_mode():
                    sub_bhwc = frames_bhwc[batch_ids, :, :, :3]
                    in_bchw = sub_bhwc.movedim(-1, 1).contiguous()
                    up_bchw = comfy.utils.tiled_scale(
                        in_bchw,
                        lambda a: up_model(a.to(device=dev, dtype=model_dt)).float(),
                        tile_x=eff_tile,
                        tile_y=eff_tile,
                        overlap=16,
                        upscale_amount=scale_f,
                        output_device=dev,
                        pbar=None,
                    )
                    if is_inplace_1x and up_bchw.shape[-2:] == (h, w):
                        base_dev = in_bchw.to(device=up_bchw.device, dtype=up_bchw.dtype)
                        delta_1x = torch.clamp(up_bchw - base_dev, -0.032, 0.032) * blend_1x
                        chunk_delta = delta_1x.movedim(1, -1).detach().cpu().float()
                        for (b_pos, f_id) in enumerate(batch_ids):
                            key_results[f_id] = chunk_delta[b_pos]
                    else:
                        if int(up_bchw.shape[-2]) != target_h or int(up_bchw.shape[-1]) != target_w:
                            up_bchw = comfy.utils.common_upscale(up_bchw, target_w, target_h, 'lanczos', 'disabled')
                        lanczos_ref = comfy.utils.common_upscale(in_bchw, target_w, target_h, 'lanczos', 'disabled').to(device=up_bchw.device, dtype=up_bchw.dtype)
                        up_bchw = torch.lerp(lanczos_ref, up_bchw, 0.68)
                        chunk_out = torch.clamp(up_bchw.movedim(1, -1).detach().cpu().float(), 0.0, 1.0)
                        for (b_pos, f_id) in enumerate(batch_ids):
                            key_results[f_id] = chunk_out[b_pos]
                ki = cur_end
            except (torch.OutOfMemoryError, RuntimeError) as oom_exc:
                if 'out of memory' in str(oom_exc).lower() and (step > 1 or eff_tile > 256):
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    if step > 1:
                        step = max(1, step // 2)
                    else:
                        eff_tile = max(256, eff_tile // 2)
                    continue
                raise
        up_model.to('cpu')
        del up_model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        if is_inplace_1x:
            for f_id in range(total_f):
                if f_id in key_results:
                    frames_bhwc[f_id, :, :, :3] = torch.clamp(frames_bhwc[f_id, :, :, :3] + key_results[f_id], 0.0, 1.0)
            return frames_bhwc
        return torch.stack([key_results[i] for i in range(total_f)], dim=0)
    except Exception as up_exc:
        print(f'[EZ-VAULT] Upscaler fallback notice ({upscale_model_name}): {up_exc}')
        return frames_bhwc

def _blend_segment_seam_with_optical_flow(prev_frames: torch.Tensor, next_frames: torch.Tensor, overlap_px: int, dev: torch.device) -> torch.Tensor:
    if not isinstance(prev_frames, torch.Tensor) or not isinstance(next_frames, torch.Tensor):
        return next_frames
    if prev_frames.shape[0] < 1 or next_frames.shape[0] < 1:
        return torch.cat([prev_frames, next_frames], dim=0)
    if next_frames.shape[0] == 1:
        return prev_frames
    ov = min(max(1, int(overlap_px or 2)), int(prev_frames.shape[0]), int(next_frames.shape[0]))
    f_prev = prev_frames[-ov:].float()
    f_next = next_frames[:ov].float()
    next_rest = next_frames[ov:].float()
    try:
        ref_p = prev_frames[-min(4, int(prev_frames.shape[0])):, :, :, :3].float().mean(dim=0, keepdim=True)
        ref_n = next_frames[:min(4, int(next_frames.shape[0])), :, :, :3].float().mean(dim=0, keepdim=True)
        p_mean = ref_p.mean(dim=(1, 2), keepdim=True)
        p_std = torch.clamp(ref_p.std(dim=(1, 2), keepdim=True), min=1e-04)
        n_mean = ref_n.mean(dim=(1, 2), keepdim=True)
        n_std = torch.clamp(ref_n.std(dim=(1, 2), keepdim=True), min=1e-04)
        gain_c = torch.clamp(p_std / n_std, 0.78, 1.22)
        f_next_matched = torch.clamp((f_next[:, :, :, :3] - n_mean) * gain_c + p_mean, 0.0, 1.0)
        f_next = f_next.clone()
        f_next[:, :, :, :3] = torch.lerp(f_next[:, :, :, :3], f_next_matched, 0.75)
        if next_rest.shape[0] > 0:
            fade_len = min(28, int(next_rest.shape[0]))
            sub_r = next_rest[:fade_len, :, :, :3]
            r_matched = torch.clamp((sub_r - n_mean) * gain_c + p_mean, 0.0, 1.0)
            lin_f = torch.linspace(0.0, 1.0, steps=fade_len, device=next_rest.device, dtype=torch.float32).view(fade_len, 1, 1, 1)
            fade_w = 0.68 * (0.5 + 0.5 * torch.cos(lin_f * math.pi))
            next_rest = next_rest.clone()
            next_rest[:fade_len, :, :, :3] = torch.lerp(sub_r, r_matched, fade_w)
    except Exception:
        pass
    alpha = torch.linspace(1.0 / float(ov + 1), float(ov) / float(ov + 1), ov, device=f_prev.device, dtype=torch.float32).view(ov, 1, 1, 1)
    blend_w = 0.5 - 0.5 * torch.cos(alpha * math.pi)
    seam_ov = torch.clamp(torch.lerp(f_prev, f_next, blend_w), 0.0, 1.0)
    return torch.cat([prev_frames[:-ov], seam_ov, next_rest], dim=0)

def _resolve_rife_checkpoint_path(rife_model: str):
    if not rife_model or 'optical_flow' in str(rife_model).lower() or 'raft' in str(rife_model).lower() or str(rife_model) == 'None':
        return None
    clean_name = Path(str(rife_model)).name
    base_m = Path(folder_paths.models_dir)
    base_c = Path(getattr(folder_paths, 'base_path', base_m.parent))
    search_dirs = [
        base_m / 'rife',
        base_m / 'vfi',
        base_m / 'frame_interpolation',
        base_m / 'upscale_models',
        base_c / 'custom_nodes' / 'ComfyUI-Frame-Interpolation' / 'ckpts' / 'rife',
        base_c / 'models' / 'rife',
    ]
    for s_dir in search_dirs:
        if not s_dir.exists():
            continue
        direct = s_dir / clean_name
        if direct.exists():
            return direct
        for pth in s_dir.rglob('*.pth'):
            if pth.name.lower() == clean_name.lower():
                return pth
    return None

def _build_and_load_rife_ifnet(ckpt_path: Path, dev: torch.device):
    import torch.nn as nn
    import torch.nn.functional as F
    cache_key = f'rife_ifnet::{ckpt_path}'
    cached = _VAULT_KEYPOINT_CACHE.get(cache_key)
    if cached is not None:
        return cached.to(device=dev, dtype=torch.float32).eval()
    raw_sd = comfy.utils.load_torch_file(str(ckpt_path), safe_load=True)
    sd = {k.replace('module.', ''): v for (k, v) in raw_sd.items()}
    if hasattr(raw_sd, 'eval') and callable(raw_sd):
        _VAULT_KEYPOINT_CACHE[cache_key] = raw_sd.eval()
        return raw_sd.to(device=dev, dtype=torch.float32).eval()
    has_head = any(k.startswith('encode.') for k in sd.keys())

    def _conv(in_p, out_p, k=3, s=1, p=1):
        return nn.Sequential(nn.Conv2d(in_p, out_p, kernel_size=k, stride=s, padding=p, bias=True), nn.LeakyReLU(0.2, True))

    class _IFBlock(nn.Module):
        def __init__(self, in_planes, c=64):
            super().__init__()
            self.conv0 = nn.Sequential(_conv(in_planes, c // 2, 3, 2, 1), _conv(c // 2, c, 3, 2, 1))
            self.convblock = nn.Sequential(*[_conv(c, c) for _ in range(8)])
            self.lastconv = nn.ConvTranspose2d(c, 5, 4, 2, 1)

        def forward(self, x, flow=None, scale=1):
            x = F.interpolate(x, scale_factor=1.0 / scale, mode='bilinear', align_corners=False) if scale != 1 else x
            if flow is not None:
                flow = F.interpolate(flow, scale_factor=1.0 / scale, mode='bilinear', align_corners=False) / scale if scale != 1 else flow
                x = torch.cat((x, flow), 1)
            feat = self.conv0(x)
            feat = self.convblock(feat)
            tmp = self.lastconv(feat)
            tmp = F.interpolate(tmp, scale_factor=scale * 2, mode='bilinear', align_corners=False)
            return (tmp[:, :4] * scale * 2, tmp[:, 4:5])

    class _RifeIFNet(nn.Module):
        def __init__(self, use_encode: bool):
            super().__init__()
            if use_encode:
                self.encode = nn.Sequential(nn.Conv2d(3, 16, 3, 2, 1), nn.ConvTranspose2d(16, 4, 4, 2, 1))
                b0_in = int(sd.get('block0.conv0.0.0.weight', torch.empty(1, 15, 3, 3)).shape[1])
                b1_in = int(sd.get('block1.conv0.0.0.weight', torch.empty(1, 20, 3, 3)).shape[1])
                b2_in = int(sd.get('block2.conv0.0.0.weight', torch.empty(1, 20, 3, 3)).shape[1])
                b3_in = int(sd.get('block3.conv0.0.0.weight', torch.empty(1, 20, 3, 3)).shape[1])
            else:
                self.encode = None
                b0_in = int(sd.get('block0.conv0.0.0.weight', torch.empty(1, 7, 3, 3)).shape[1])
                b1_in = int(sd.get('block1.conv0.0.0.weight', torch.empty(1, 12, 3, 3)).shape[1])
                b2_in = int(sd.get('block2.conv0.0.0.weight', torch.empty(1, 12, 3, 3)).shape[1])
                b3_in = int(sd.get('block3.conv0.0.0.weight', torch.empty(1, 12, 3, 3)).shape[1])
            c0 = int(sd.get('block0.conv0.1.0.weight', torch.empty(192, 1, 3, 3)).shape[0])
            c1 = int(sd.get('block1.conv0.1.0.weight', torch.empty(128, 1, 3, 3)).shape[0])
            c2 = int(sd.get('block2.conv0.1.0.weight', torch.empty(96, 1, 3, 3)).shape[0])
            c3 = int(sd.get('block3.conv0.1.0.weight', torch.empty(64, 1, 3, 3)).shape[0])
            self.block0 = _IFBlock(b0_in, c=c0)
            self.block1 = _IFBlock(b1_in, c=c1)
            self.block2 = _IFBlock(b2_in, c=c2)
            self.block3 = _IFBlock(b3_in, c=c3)

        def _warp(self, img, flow):
            (b_n, _, h_n, w_n) = flow.shape
            gy = torch.linspace(-1.0, 1.0, steps=h_n, device=flow.device, dtype=flow.dtype).view(1, h_n, 1).expand(b_n, h_n, w_n)
            gx = torch.linspace(-1.0, 1.0, steps=w_n, device=flow.device, dtype=flow.dtype).view(1, 1, w_n).expand(b_n, h_n, w_n)
            grid = torch.stack([gx + flow[:, 0] * (2.0 / max(1.0, float(w_n - 1))), gy + flow[:, 1] * (2.0 / max(1.0, float(h_n - 1)))], dim=-1)
            return F.grid_sample(img, grid, mode='bilinear', padding_mode='border', align_corners=True)

        def forward(self, img0, img1, timestep=0.5, scale_list=(8, 4, 2, 1)):
            eff_scales = (4, 2, 1, 1) if max(int(img0.shape[-2]), int(img0.shape[-1])) <= 1088 else scale_list
            ts = (img0[:, :1].clone() * 0.0 + 1.0) * float(timestep)
            if self.encode is not None:
                f0 = self.encode(img0[:, :3])
                f1 = self.encode(img1[:, :3])
            else:
                (f0, f1) = (None, None)
            (warped0, warped1) = (img0, img1)
            (wf0, wf1) = (f0, f1)
            (flow, mask) = (None, None)
            blocks = (self.block0, self.block1, self.block2, self.block3)
            for i in range(4):
                if flow is None:
                    in_t = torch.cat((img0[:, :3], img1[:, :3], f0, f1, ts), 1) if self.encode is not None else torch.cat((img0[:, :3], img1[:, :3], ts), 1)
                    (flow, mask) = blocks[i](in_t, None, scale=eff_scales[i])
                else:
                    in_t = torch.cat((warped0[:, :3], warped1[:, :3], wf0, wf1, ts, mask), 1) if self.encode is not None else torch.cat((warped0[:, :3], warped1[:, :3], ts, mask), 1)
                    (fd, md) = blocks[i](in_t, flow, scale=eff_scales[i])
                    flow = flow + fd
                    mask = mask + md
                warped0 = self._warp(img0, flow[:, :2])
                warped1 = self._warp(img1, flow[:, 2:4])
                if self.encode is not None:
                    wf0 = self._warp(f0, flow[:, :2])
                    wf1 = self._warp(f1, flow[:, 2:4])
            m_sig = torch.sigmoid(mask)
            photometric_err = (warped0[:, :3] - warped1[:, :3]).abs().mean(dim=1, keepdim=True)
            occ_gate = torch.clamp((photometric_err - 0.045) * 9.0, 0.0, 1.0)
            sharp_m = torch.where(m_sig >= 0.5, torch.lerp(m_sig, torch.ones_like(m_sig), occ_gate), torch.lerp(m_sig, torch.zeros_like(m_sig), occ_gate))
            return warped0 * sharp_m + warped1 * (1.0 - sharp_m)

    net = _RifeIFNet(use_encode=has_head)
    net.load_state_dict(sd, strict=True)
    net.eval()
    _VAULT_KEYPOINT_CACHE[cache_key] = net
    return net.to(device=dev, dtype=torch.float32).eval()

def _execute_optical_flow_rife_interpolation(frames_bhwc: torch.Tensor, rife_model: str='rife49.pth', rife_multiplier: str='2x', rife_strength: float=1.0) -> tuple:
    import torch.nn.functional as F
    mult_str = str(rife_multiplier or '2x').lower()
    mult = 4 if '4' in mult_str else 3 if '3' in mult_str else 2
    strength = max(0.0, min(1.0, float(rife_strength)))
    (total_f, h, w, c) = frames_bhwc.shape
    if total_f < 2 or strength <= 0.001:
        return (frames_bhwc, 1)
    dev = comfy.model_management.get_torch_device() if torch.cuda.is_available() else torch.device('cpu')
    rife_net = None
    rife_ckpt = _resolve_rife_checkpoint_path(rife_model)
    if rife_ckpt is not None:
        try:
            rife_net = _build_and_load_rife_ifnet(rife_ckpt, dev)
        except Exception:
            rife_net = None
    raft_net = None if rife_net is not None else _get_cached_vault_raft_model(dev)
    max_flow_side = 1536 if rife_net is not None else 640
    flow_scale = min(1.0, float(max_flow_side) / float(max(h, w, 1)))
    pad_div = 32 if rife_net is not None else 8
    fh = max(pad_div, int(round(h * flow_scale / pad_div)) * pad_div) if flow_scale < 0.999 else ((h + pad_div - 1) // pad_div) * pad_div
    fw = max(pad_div, int(round(w * flow_scale / pad_div)) * pad_div) if flow_scale < 0.999 else ((w + pad_div - 1) // pad_div) * pad_div
    base_y = torch.linspace(-1.0, 1.0, steps=h, device=dev, dtype=torch.float32).view(1, h, 1).expand(1, h, w)
    base_x = torch.linspace(-1.0, 1.0, steps=w, device=dev, dtype=torch.float32).view(1, 1, w).expand(1, h, w)
    base_grid = torch.stack([base_x, base_y], dim=-1)
    out_batches = []
    batch_sz = 6 if (rife_net is not None or raft_net is not None) else 24
    idx = 0
    tot_rife_batches = max(1, (total_f - 1 + batch_sz - 1) // batch_sz)
    try:
        while idx < total_f - 1:
            if hasattr(comfy.model_management, 'throw_exception_if_processing_interrupted'):
                comfy.model_management.throw_exception_if_processing_interrupted()
            try:
                from .engine_ez_01_cinematrix_canvas_ingest import enforce_cinematrix_thermal_shield
                sh_rife = enforce_cinematrix_thermal_shield(
                    f'Vault-RIFE-{rife_model}',
                    step_idx=idx // max(1, batch_sz),
                    total_steps=tot_rife_batches,
                    force_inter_stage_pause=(idx == 0),
                )
                rt_ov = sh_rife.get('runtime_overrides') if isinstance(sh_rife, dict) and isinstance(sh_rife.get('runtime_overrides'), dict) else {}
                if bool(rt_ov.get('is_warm', False)) and rt_ov.get('rife_batch_sz'):
                    batch_sz = max(1, min(batch_sz, int(rt_ov['rife_batch_sz'])))
            except Exception:
                pass
            end_i = min(total_f - 1, idx + batch_sz)
            try:
                with torch.inference_mode():
                    f0 = frames_bhwc[idx:end_i].to(device=dev, dtype=torch.float32).permute(0, 3, 1, 2).contiguous()
                    f1 = frames_bhwc[idx + 1:end_i + 1].to(device=dev, dtype=torch.float32).permute(0, 3, 1, 2).contiguous()
                    b_cur = f0.shape[0]
                    sub_frames = [f0.permute(0, 2, 3, 1).detach().cpu()]
                    if rife_net is not None:
                        pad_h = max(0, fh - h)
                        pad_w = max(0, fw - w)
                        use_pad_only = (flow_scale >= 0.999 and fh >= h and fw >= w)
                        p0 = (F.pad(f0, (0, pad_w, 0, pad_h), mode='reflect') if (pad_h > 0 or pad_w > 0) else f0) if use_pad_only else F.interpolate(f0, size=(fh, fw), mode='bilinear', align_corners=False)
                        p1 = (F.pad(f1, (0, pad_w, 0, pad_h), mode='reflect') if (pad_h > 0 or pad_w > 0) else f1) if use_pad_only else F.interpolate(f1, size=(fh, fw), mode='bilinear', align_corners=False)
                        for m_step in range(1, mult):
                            alpha = float(m_step) / float(mult)
                            pred_low = rife_net(p0, p1, timestep=alpha)
                            pred = pred_low[:, :, :h, :w] if use_pad_only else F.interpolate(pred_low, size=(h, w), mode='bilinear', align_corners=False)
                            near_f = f0 if alpha <= 0.5 else f1
                            if strength < 0.999:
                                pred = torch.lerp(near_f, pred, strength)
                            sub_frames.append(torch.clamp(pred.permute(0, 2, 3, 1).detach().cpu(), 0.0, 1.0))
                    elif raft_net is not None:
                        in0 = F.interpolate(f0 * 2.0 - 1.0, size=(fh, fw), mode='bilinear', align_corners=False) if (fh != h or fw != w) else (f0 * 2.0 - 1.0)
                        in1 = F.interpolate(f1 * 2.0 - 1.0, size=(fh, fw), mode='bilinear', align_corners=False) if (fh != h or fw != w) else (f1 * 2.0 - 1.0)
                        flow_01_low = raft_net(in0, in1, num_flow_updates=4)[-1] * strength
                        flow_10_low = raft_net(in1, in0, num_flow_updates=4)[-1] * strength
                        flow_01 = F.interpolate(flow_01_low, size=(h, w), mode='bilinear', align_corners=False)
                        flow_10 = F.interpolate(flow_10_low, size=(h, w), mode='bilinear', align_corners=False)
                        norm_x = 2.0 / max(1.0, float(fw - 1))
                        norm_y = 2.0 / max(1.0, float(fh - 1))
                        f01_norm = torch.stack([flow_01[:, 0] * norm_x, flow_01[:, 1] * norm_y], dim=-1)
                        f10_norm = torch.stack([flow_10[:, 0] * norm_x, flow_10[:, 1] * norm_y], dim=-1)
                        fb_err = (f01_norm + f10_norm).norm(dim=-1, keepdim=True).permute(0, 3, 1, 2)
                        occ_gate = torch.exp(-fb_err * 22.0)
                        grid_b = base_grid.expand(b_cur, h, w, 2)
                        for m_step in range(1, mult):
                            alpha = float(m_step) / float(mult)
                            w0 = F.grid_sample(f0, grid_b + alpha * f10_norm, mode='bilinear', padding_mode='border', align_corners=True)
                            w1 = F.grid_sample(f1, grid_b + (1.0 - alpha) * f01_norm, mode='bilinear', padding_mode='border', align_corners=True)
                            photo_err = (w0 - w1).abs().mean(dim=1, keepdim=True)
                            conf = occ_gate * torch.exp(-photo_err * 12.0)
                            blend_mid = (1.0 - alpha) * w0 + alpha * w1
                            sharp_anchor = w0 if alpha <= 0.5 else w1
                            mid = torch.lerp(sharp_anchor, blend_mid, conf).permute(0, 2, 3, 1).detach().cpu()
                            sub_frames.append(torch.clamp(mid, 0.0, 1.0))
                    else:
                        for m_step in range(1, mult):
                            alpha = float(m_step) / float(mult)
                            near_f = f0 if alpha <= 0.5 else f1
                            lin_f = (1.0 - alpha) * f0 + alpha * f1
                            photo_d = (f0 - f1).abs().mean(dim=1, keepdim=True)
                            safe_w = torch.exp(-photo_d * 14.0) * strength
                            mid = torch.lerp(near_f, lin_f, safe_w).permute(0, 2, 3, 1).detach().cpu()
                            sub_frames.append(torch.clamp(mid, 0.0, 1.0))
                    stacked = torch.stack(sub_frames, dim=1).reshape(b_cur * mult, h, w, c)
                    out_batches.append(stacked)
                idx = end_i
            except (torch.OutOfMemoryError, RuntimeError) as oom_exc:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                if batch_sz > 1:
                    batch_sz = max(1, batch_sz // 2)
                    continue
                rife_net = None
                raft_net = None
                continue
    finally:
        if rife_net is not None:
            rife_net.to('cpu')
        if raft_net is not None:
            raft_net.to('cpu')
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    out_batches.append(frames_bhwc[-1:].float().detach().cpu())
    return (torch.cat(out_batches, dim=0), mult)

def decode_and_postprocess_cinema_stream(sampled_video_latent: dict, video_vae, frame_rate, enable_2x_frame_interpolation: bool, enable_rtx_lanczos_2x: bool, filename_prefix: str, save_frames_to_disk: bool, tier_profile: dict=None, audio_vae=None, codec: str='H.264', container: str='MP4', bit_depth: str='Auto', quality=18, pingpong: bool=False, save_metadata: bool=True, date_folder_format: str='YYYY-MM-DD', save_first_and_last_frame: bool=False, crop_to_audio: bool=False, audio_codec: str='Auto', audio_bitrate: str='192k', enable_frequency_polish: bool=True, skin_blur_radius: float=2.5, skin_texture_strength: float=1.06, skin_polish_opacity: float=0.55, dock_cfg: dict=None, custom_frame_rate: float=24.0, custom_quality_crf: int=18, upscale_model_name: str='None', rife_model: str='rife49.pth', rife_multiplier: str='2x', rife_strength: float=1.0, detailer_1x_model_name: str='None', vault_metadata: dict=None):
    from concurrent.futures import ThreadPoolExecutor
    _ensure_portable_vault_torch_hub()
    frame_rate = _resolve_vault_frame_rate(frame_rate, custom_frame_rate)
    quality = _resolve_vault_quality_crf(quality, custom_quality_crf)
    prof = dict(tier_profile) if isinstance(tier_profile, dict) else dict(sampled_video_latent.get('hardware_tier_profile', {})) if isinstance(sampled_video_latent.get('hardware_tier_profile'), dict) else {}
    vae_window_t = max(24, int(prof.get('vae_window_t', 28) or 28))
    tile_sz = max(256, int(prof.get('tile_size', 512) or 512))
    io_workers = max(1, int(prof.get('io_workers', 4) or 4))
    aggressive_purge = bool(prof.get('aggressive_vram_purge', True))
    if hasattr(comfy.model_management, 'EXTRA_RESERVED_VRAM'):
        comfy.model_management.EXTRA_RESERVED_VRAM = min(int(getattr(comfy.model_management, 'EXTRA_RESERVED_VRAM', 0) or 0), 600 * 1024 * 1024)
    if aggressive_purge:
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
    if _is_audio_vae_instance(video_vae):
        if audio_vae is not None and (not _is_audio_vae_instance(audio_vae)):
            (video_vae, audio_vae) = (audio_vae, video_vae)
        elif isinstance(sampled_video_latent, dict) and sampled_video_latent.get('video_vae_obj') is not None and (not _is_audio_vae_instance(sampled_video_latent.get('video_vae_obj'))):
            if audio_vae is None or not _is_audio_vae_instance(audio_vae):
                audio_vae = video_vae
            video_vae = sampled_video_latent['video_vae_obj']
    if (audio_vae is None or not _is_audio_vae_instance(audio_vae)) and isinstance(sampled_video_latent, dict) and _is_audio_vae_instance(sampled_video_latent.get('audio_vae_obj')):
        audio_vae = sampled_video_latent['audio_vae_obj']
    raw_av = sampled_video_latent['samples']
    audio_latent = None
    macro_segs = sampled_video_latent.get('ez_macro_segment_latents') if isinstance(sampled_video_latent.get('ez_macro_segment_latents'), list) else None
    audio_win_latents = macro_segs if macro_segs and len(macro_segs) >= 2 else (sampled_video_latent.get('ez_audio_window_latents') if isinstance(sampled_video_latent.get('ez_audio_window_latents'), list) else None)
    overlap_t = int(sampled_video_latent.get('ez_overlap_t', 2) or 2)
    target_total_frames = int(sampled_video_latent.get('total_frames', 0) or 0)
    if getattr(raw_av, 'is_nested', False) or hasattr(raw_av, 'tensors'):
        av_list = list(raw_av.tensors) if hasattr(raw_av, 'tensors') else list(raw_av.unbind())
        samples = av_list[0].detach().cpu()
        if len(av_list) > 1 and isinstance(av_list[1], torch.Tensor):
            audio_latent = av_list[1].detach().cpu()
    else:
        samples = raw_av.detach().cpu()
        audio_latent = samples
    if macro_segs and len(macro_segs) >= 2:
        seam_dev = comfy.model_management.get_torch_device() if torch.cuda.is_available() else torch.device('cpu')
        is_h3_lat = isinstance(samples, torch.Tensor) and samples.ndim == 5 and int(samples.shape[1]) == 24
        ov_t_val = max(1, overlap_t)
        ov_px = 1 if is_h3_lat else max(1, (ov_t_val - 1) * 4 + 1)
        stitched_frames = None
        w0_lf_mean = None
        w0_lf_std = None
        w0_hf_std = None
        for (s_idx, (seg_lat, seg_p_frames)) in enumerate(macro_segs):
            try:
                from .engine_ez_01_cinematrix_canvas_ingest import enforce_cinematrix_thermal_shield
                sh_vae = enforce_cinematrix_thermal_shield(f'Vault-VAE-Decode-Win{s_idx + 1}/{len(macro_segs)}', tier_profile=prof, force_inter_stage_pause=True)
                rt_ov = sh_vae.get('runtime_overrides') if isinstance(sh_vae, dict) and isinstance(sh_vae.get('runtime_overrides'), dict) else {}
                if bool(rt_ov.get('is_warm', False)) and rt_ov.get('tile_size'):
                    tile_sz = max(256, min(tile_sz, int(rt_ov['tile_size'])))
            except Exception:
                pass
            v_in = seg_lat.tensors[0] if getattr(seg_lat, 'is_nested', False) or hasattr(seg_lat, 'tensors') else seg_lat
            seg_f = _decode_single_vae_chunk(video_vae, v_in, tile_sz=tile_sz, aggressive_purge=False, target_pixel_frames=int(seg_p_frames or 0))
            if isinstance(seg_f, torch.Tensor) and seg_f.ndim == 4 and seg_f.shape[0] >= 1:
                try:
                    import torch.nn.functional as F
                    seg_rgb = seg_f[:, :, :, :3].float()
                    f_cnt = int(seg_rgb.shape[0])
                    if s_idx == 0 or w0_lf_std is None:
                        s_i0 = min(4, max(0, f_cnt - 1)) if f_cnt >= 8 else 0
                        ref_head = seg_rgb[s_i0:min(s_i0 + 20, f_cnt)].permute(0, 3, 1, 2)
                        r_lf = F.avg_pool2d(F.pad(ref_head, (2, 2, 2, 2), mode='reflect'), kernel_size=5, stride=1)
                        r_hf = ref_head - r_lf
                        w0_lf_mean = r_lf.mean(dim=(0, 2, 3), keepdim=True)
                        w0_lf_std = torch.clamp(r_lf.std(dim=(0, 2, 3), keepdim=True), min=1e-04)
                        w0_hf_std = torch.clamp(r_hf.std(dim=(0, 2, 3), keepdim=True), min=1e-04)
                    elif s_idx >= 1 and w0_lf_std is not None and w0_hf_std is not None:
                        cur_bchw = seg_rgb.permute(0, 3, 1, 2)
                        c_lf = F.avg_pool2d(F.pad(cur_bchw, (2, 2, 2, 2), mode='reflect'), kernel_size=5, stride=1)
                        c_hf = cur_bchw - c_lf
                        cur_lf_m = c_lf.mean(dim=(0, 2, 3), keepdim=True)
                        cur_lf_s = torch.clamp(c_lf.std(dim=(0, 2, 3), keepdim=True), min=1e-04)
                        cur_hf_s = torch.clamp(c_hf.std(dim=(0, 2, 3), keepdim=True), min=1e-04)
                        lf_gain = torch.clamp(w0_lf_std / cur_lf_s, 0.70, 1.01)
                        hf_gain = torch.clamp(w0_hf_std / cur_hf_s, 0.62, 1.01)
                        eff_lf_m = torch.lerp(cur_lf_m, w0_lf_mean, 0.65) if w0_lf_mean is not None else cur_lf_m
                        c_lf_damped = (c_lf - cur_lf_m) * torch.lerp(torch.ones_like(lf_gain), lf_gain, 0.78) + eff_lf_m
                        c_hf_damped = c_hf * torch.lerp(torch.ones_like(hf_gain), hf_gain, 0.88)
                        seg_damped = torch.clamp(c_lf_damped + c_hf_damped, 0.0, 1.0).permute(0, 2, 3, 1)
                        seg_f = seg_f.clone()
                        seg_f[:, :, :, :3] = seg_damped.to(dtype=seg_f.dtype)
                except Exception:
                    pass
            if stitched_frames is None:
                stitched_frames = seg_f
            else:
                stitched_frames = _blend_segment_seam_with_optical_flow(stitched_frames, seg_f, ov_px, seam_dev)
        frames = stitched_frames[:target_total_frames] if (target_total_frames > 0 and stitched_frames.shape[0] > target_total_frames) else stitched_frames
    else:
        frames = _decode_single_vae_chunk(video_vae, samples, tile_sz=tile_sz, aggressive_purge=False, target_pixel_frames=target_total_frames)
    up_str = str(upscale_model_name or 'None')
    det_str = str(detailer_1x_model_name or 'None')
    is_up_1x = up_str != 'None' and (up_str.lower().startswith('1x') or 'skindiff' in up_str.lower() or 'skincontrast' in up_str.lower())
    eff_up_model = up_str if (up_str != 'None' and (not is_up_1x or enable_rtx_lanczos_2x)) else 'None'
    eff_1x_model = det_str if det_str != 'None' else (up_str if (is_up_1x and eff_up_model == 'None') else 'None')
    tier_chunk_t = max(2, min(32, int(prof.get('upscale_chunk_t', 8) or 8)))
    identity_anchor = sampled_video_latent.get('ez_character_identity_anchor') if isinstance(sampled_video_latent, dict) and isinstance(sampled_video_latent.get('ez_character_identity_anchor'), dict) else (sampled_video_latent.get('anatomical_latent_zones') if isinstance(sampled_video_latent, dict) and isinstance(sampled_video_latent.get('anatomical_latent_zones'), dict) else None)
    if frames.shape[0] > 0:
        if eff_1x_model != 'None':
            frames = _apply_real_upscale_model(frames, eff_1x_model, tile_sz=tile_sz, target_scale_cap=1, batch_step=tier_chunk_t)
        if eff_up_model != 'None':
            frames = _apply_real_upscale_model(frames, eff_up_model, tile_sz=tile_sz, target_scale_cap=2, batch_step=tier_chunk_t)
        elif enable_rtx_lanczos_2x:
            frames = _apply_edge_directed_lanczos_2x(frames, batch_step=tier_chunk_t)
        vault_style_low = str((dock_cfg or {}).get('style_target') or (vault_metadata or {}).get('style_target') or 'realism').strip().lower()
        if enable_frequency_polish and vault_style_low not in ('anime', 'cartoonish'):
            eff_pol_op = float(skin_polish_opacity) * 0.45 if eff_1x_model != 'None' else float(skin_polish_opacity)
            frames = _apply_vault_frequency_polish(frames, skin_blur_radius, skin_texture_strength, eff_pol_op, dock_cfg=dock_cfg, batch_step=tier_chunk_t, identity_anchor=identity_anchor)
    anatomy_preview = frames[:1].clone() if frames.shape[0] > 0 else torch.zeros((1, 512, 512, 3), dtype=torch.float32)
    if frames.shape[0] > 0:
        try:
            dev_p = comfy.model_management.get_torch_device() if torch.cuda.is_available() else torch.device('cpu')
            f0_bchw = frames[:1].to(device=dev_p, dtype=torch.float32).permute(0, 3, 1, 2).contiguous()
            use_rcnn_kp = bool(isinstance(dock_cfg, dict) and dock_cfg.get('enable_rcnn_keypoints', False))
            z0 = _compute_vault_anatomy_zones(f0_bchw, dock_cfg=dock_cfg, use_keypoint_detector=use_rcnn_kp)
            anatomy_preview = _render_vault_anatomy_preview(f0_bchw, z0)
        except Exception:
            pass
    final_fps = float(frame_rate)
    if enable_2x_frame_interpolation and frames.shape[0] >= 2:
        (frames, interp_mult) = _execute_optical_flow_rife_interpolation(frames, rife_model=rife_model, rife_multiplier=rife_multiplier, rife_strength=rife_strength)
        final_fps = final_fps * float(interp_mult)
    if pingpong and frames.shape[0] > 2:
        rev_frames = torch.flip(frames[1:-1], dims=[0])
        frames = torch.cat([frames, rev_frames], dim=0)
    out_dir = Path(folder_paths.get_output_directory())
    temp_dir = Path(folder_paths.get_temp_directory())
    temp_dir.mkdir(parents=True, exist_ok=True)
    now_dt = datetime.now()
    ts_str = now_dt.strftime('%Y-%m-%d_%H-%M-%S')
    raw_prefix_expanded = re.sub(r'\[time\(([^)]+)\)\]', lambda m: now_dt.strftime(m.group(1)), str(filename_prefix or 'EZ_Cinematrix'))
    safe_prefix = raw_prefix_expanded.replace('\\', '/').strip('/')
    date_root_folder = _resolve_vault_date_subfolder(out_dir, date_folder_format, now_dt=now_dt)
    prefix_parent = Path(safe_prefix).parent
    if str(prefix_parent) not in ('', '.'):
        rel_parts = [p for p in prefix_parent.parts if p not in ('', '.') and p != date_root_folder.name]
        target_folder = date_root_folder.joinpath(*rel_parts) if rel_parts else date_root_folder
    else:
        target_folder = date_root_folder
    target_folder.mkdir(parents=True, exist_ok=True)
    stem_name = Path(safe_prefix).name or 'EZ_Cinematrix'
    cont_ext_map = {'mp4': 'mp4', 'mkv': 'mkv', 'mov': 'mov', 'webm': 'webm', 'webp': 'webp'}
    ext = cont_ext_map.get(str(container or 'MP4').lower(), 'mp4')
    if 'webp' in str(codec or '').lower():
        ext = 'webp'
    video_filename = f'{stem_name}_{ts_str}_video.{ext}'
    saved_manifest_path = str(target_folder / video_filename)
    lat_vmeta = dict(sampled_video_latent.get('ez_vault_metadata', {})) if isinstance(sampled_video_latent, dict) and isinstance(sampled_video_latent.get('ez_vault_metadata'), dict) else {}
    seed_b = dict(sampled_video_latent.get('seed_bus', {})) if isinstance(sampled_video_latent, dict) and isinstance(sampled_video_latent.get('seed_bus'), dict) else {}
    bus_vmeta = dict(vault_metadata) if isinstance(vault_metadata, dict) else {}
    vae_meta_fb = getattr(video_vae, '_ez_video_model_meta', None) or getattr(audio_vae, '_ez_video_model_meta', None) or {}
    merged_meta = {**(vae_meta_fb if isinstance(vae_meta_fb, dict) else {}), **seed_b, **lat_vmeta, **bus_vmeta}
    kf_sub_meta = dict(merged_meta.get('krea2_saved_metadata', {})) if isinstance(merged_meta.get('krea2_saved_metadata'), dict) else {}
    res_vid_unet = str(merged_meta.get('active_video_unet') or merged_meta.get('video_unet_fl2va') or kf_sub_meta.get('active_video_unet') or kf_sub_meta.get('video_unet_fl2va') or '')
    if not res_vid_unet:
        try:
            from .engine_ez_04_cinematrix_krea2_sampler import _resolve_pipeline_video_model_metadata
            fb_vm = _resolve_pipeline_video_model_metadata(merged_meta)
            for fbk, fbv in fb_vm.items():
                if fbv and not merged_meta.get(fbk):
                    merged_meta[fbk] = fbv
            res_vid_unet = str(merged_meta.get('active_video_unet') or merged_meta.get('video_unet_fl2va') or '')
        except Exception:
            pass
    if kf_sub_meta and res_vid_unet and not kf_sub_meta.get('active_video_unet'):
        kf_sub_meta['video_model'] = res_vid_unet
        kf_sub_meta['active_video_unet'] = res_vid_unet
        kf_sub_meta['video_unet_fl2va'] = str(merged_meta.get('video_unet_fl2va') or res_vid_unet)
        kf_sub_meta['active_video_loras'] = merged_meta.get('active_video_loras', [])
    fh_px = int(frames.shape[1]) if frames.ndim == 4 and frames.shape[0] > 0 else 0
    fw_px = int(frames.shape[2]) if frames.ndim == 4 and frames.shape[0] > 0 else 0
    full_vault_meta = {
        'generator': 'EZ Cinematrix Studio v2.6 // Node [08] Cinema Vault',
        'timestamp': now_dt.strftime('%Y-%m-%d %H:%M:%S'),
        'video_filename': video_filename,
        'date_folder_format': str(date_folder_format),
        'resolution': f'{fw_px}x{fh_px}',
        'frames': int(frames.shape[0]),
        'native_fps': round(float(frame_rate), 3),
        'final_fps': round(float(final_fps), 3),
        'codec': str(codec),
        'container': str(ext).upper(),
        'bit_depth': str(bit_depth),
        'quality_crf': int(quality),
        'audio_codec': str(audio_codec),
        'audio_bitrate': str(audio_bitrate),
        'video_model': res_vid_unet,
        'active_video_unet': res_vid_unet,
        'video_unet_fl2va': str(merged_meta.get('video_unet_fl2va') or res_vid_unet),
        'video_unet_ref2va': str(merged_meta.get('video_unet_ref2va', '')),
        'video_clip_name': str(merged_meta.get('video_clip_name', '')),
        'video_vae_name': str(merged_meta.get('video_vae_name', '')),
        'audio_vae_name': str(merged_meta.get('audio_vae_name', '')),
        'active_video_loras': merged_meta.get('active_video_loras', []),
        'video_turbo_lora': str(merged_meta.get('video_turbo_lora', '')),
        'shift_video': float(merged_meta.get('shift_video', 0.0) or 0.0),
        'shift_audio': float(merged_meta.get('shift_audio', 0.0) or 0.0),
        'active_image_unet': str(merged_meta.get('active_image_unet') or kf_sub_meta.get('active_image_unet') or ''),
        'active_style_loras': merged_meta.get('active_style_loras') if merged_meta.get('active_style_loras') else kf_sub_meta.get('active_style_loras', []),
        'upscale_model_name': str(upscale_model_name),
        'detailer_1x_model_name': str(detailer_1x_model_name),
        'enable_2x_frame_interpolation': bool(enable_2x_frame_interpolation),
        'rife_model': str(rife_model),
        'rife_multiplier': str(rife_multiplier),
        'rife_strength': round(float(rife_strength), 3),
        'enable_rtx_lanczos_2x': bool(enable_rtx_lanczos_2x),
        'enable_frequency_polish': bool(enable_frequency_polish),
        'pingpong': bool(pingpong),
        'style_target': str(merged_meta.get('style_target', '')),
        'subject_1_age': str(merged_meta.get('subject_1_age', '')),
        'canvas_seed': int(merged_meta.get('canvas_seed', 0) or 0),
        'qwenvl_seed': int(merged_meta.get('qwenvl_seed', 0) or 0),
        'image_sampler_seed': int(merged_meta.get('image_sampler_seed', 0) or 0),
        'video_sampler_seed': int(merged_meta.get('video_sampler_seed', 0) or 0),
        'video_steps': int(merged_meta.get('video_steps', 0) or 0),
        'video_cfg': float(merged_meta.get('video_cfg', 0.0) or 0.0),
        'video_sampler_name': str(merged_meta.get('video_sampler_name', '')),
        'video_scheduler': str(merged_meta.get('video_scheduler', '')),
        'video_denoise': float(merged_meta.get('video_denoise', 1.0) or 1.0),
        'krea2_image_prompt': str(merged_meta.get('krea2_image_prompt', '')),
        'h3_video_timeline_prompt': str(merged_meta.get('h3_video_timeline_prompt', '')),
        'adaptive_negative_prompt': str(merged_meta.get('adaptive_negative_prompt', '')),
        'krea2_saved_metadata': kf_sub_meta,
    }
    ui_images = []
    if save_frames_to_disk and frames.shape[0] > 0:
        if save_first_and_last_frame:
            first_u8 = (frames[0] * 255.0).clamp(0.0, 255.0).to(torch.uint8).numpy()
            last_u8 = (frames[-1] * 255.0).clamp(0.0, 255.0).to(torch.uint8).numpy()
            if save_metadata:
                fl_info = PngImagePlugin.PngInfo()
                fl_info.add_text('prompt', full_vault_meta['h3_video_timeline_prompt'] or full_vault_meta['krea2_image_prompt'])
                fl_info.add_text('negative_prompt', full_vault_meta['adaptive_negative_prompt'])
                fl_info.add_text('cinematrix_metadata', json.dumps(full_vault_meta, ensure_ascii=False))
                Image.fromarray(first_u8).save(str(target_folder / f'{stem_name}_{ts_str}_first_frame.png'), pnginfo=fl_info)
                Image.fromarray(last_u8).save(str(target_folder / f'{stem_name}_{ts_str}_last_frame.png'), pnginfo=fl_info)
            else:
                Image.fromarray(first_u8).save(str(target_folder / f'{stem_name}_{ts_str}_first_frame.png'))
                Image.fromarray(last_u8).save(str(target_folder / f'{stem_name}_{ts_str}_last_frame.png'))
        if ext == 'webp':
            webp_q = max(15, min(98, 100 - int(quality) * 2))

            def _frame_to_pil(idx_val: int):
                return Image.fromarray((frames[idx_val] * 255.0).clamp(0.0, 255.0).to(torch.uint8).numpy())
            if io_workers > 1 and frames.shape[0] >= 8:
                with ThreadPoolExecutor(max_workers=io_workers) as pool:
                    pil_frames = list(pool.map(_frame_to_pil, range(frames.shape[0])))
            else:
                pil_frames = [_frame_to_pil(i) for i in range(frames.shape[0])]
            duration_ms = max(10, int(round(1000.0 / max(1.0, final_fps))))
            pil_frames[0].save(saved_manifest_path, save_all=True, append_images=pil_frames[1:], duration=duration_ms, loop=0, quality=webp_q)
        else:
            temp_wav = temp_dir / f'ez_audio_{ts_str}.wav'
            vid_dur_sec = float(frames.shape[0]) / max(1.0, float(final_fps))
            suno_cfg = sampled_video_latent.get('suno_music_studio') if isinstance(sampled_video_latent, dict) and isinstance(sampled_video_latent.get('suno_music_studio'), dict) else {}
            suno_direct = sampled_video_latent.get('suno_direct_audio') if isinstance(sampled_video_latent, dict) and isinstance(sampled_video_latent.get('suno_direct_audio'), dict) else None
            suno_src_str = str(suno_cfg.get('source_audio_path') or suno_cfg.get('master_wav_path') or '') if suno_cfg.get('active') else ''
            suno_wav = Path(suno_src_str) if suno_src_str else None
            suno_master_wav = Path(str(suno_cfg.get('master_wav_path', ''))) if suno_cfg.get('active') and suno_cfg.get('master_wav_path') else None
            if (suno_wav is None or not suno_wav.exists()) and suno_master_wav is not None and suno_master_wav.exists():
                suno_wav = suno_master_wav
            if str(audio_codec).lower() != 'mute' and suno_wav is not None and suno_wav.exists() and suno_wav.stat().st_size > 1024:
                ffmpeg_bin = _resolve_ffmpeg_binary()
                start_off_s = float(suno_cfg.get('start_offset_sec', 0.0) or 0.0) if suno_wav != suno_master_wav else 0.0
                fade_start = max(0.0, vid_dur_sec - 1.2)
                if ffmpeg_bin:
                    try:
                        trim_cmd = [ffmpeg_bin, '-y', '-ss', f'{max(0.0, start_off_s):.3f}', '-i', str(suno_wav), '-t', f'{vid_dur_sec:.3f}', '-af', f'aresample=async=1:first_pts=0,afade=t=out:st={fade_start:.2f}:d=1.2', '-ac', '2', '-ar', '48000', '-c:a', 'pcm_s16le', str(temp_wav)]
                        subprocess.run(trim_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                    except Exception:
                        pass
                if not temp_wav.exists() or temp_wav.stat().st_size < 1024:
                    shutil.copy2(str(suno_master_wav if (suno_master_wav and suno_master_wav.exists()) else suno_wav), str(temp_wav))
                has_wav = True
                print(f"[EZ-VAULT] 🎵 Muxar 48kHz Studio Master Suno-ljudspår ({suno_cfg.get('bpm', 124.0)} BPM, {vid_dur_sec:.2f}s) i exakt A/V-synk till slutvideon!")
            elif str(audio_codec).lower() != 'mute' and isinstance(suno_direct, dict) and isinstance(suno_direct.get('waveform'), torch.Tensor):
                w_np = _normalize_single_audio_tensor_to_np(suno_direct['waveform'])
                sr_d = int(suno_direct.get('sample_rate', 32000) or 32000)
                if w_np is not None and w_np.size > 0:
                    tgt_s = int(round(vid_dur_sec * float(sr_d)))
                    if w_np.shape[0] > tgt_s and tgt_s > 32:
                        w_np = w_np[:tgt_s]
                    pcm16 = np.clip(w_np * 32767.0, -32768, 32767).astype(np.int16)
                    ch_d = int(pcm16.shape[1]) if pcm16.ndim == 2 else 1
                    with wave.open(str(temp_wav), 'wb') as wf:
                        wf.setnchannels(ch_d)
                        wf.setsampwidth(2)
                        wf.setframerate(sr_d)
                        wf.writeframes(pcm16.tobytes())
                has_wav = temp_wav.exists() and temp_wav.stat().st_size > 1024
            else:
                vault_aud_mode = str(sampled_video_latent.get('audio_soundtrack_mode', '') if isinstance(sampled_video_latent, dict) else '').strip() or 'sfx_only'
                has_wav = _decode_audio_latent_to_wav(audio_vae, audio_latent, temp_wav, audio_win_latents=audio_win_latents, overlap_t=overlap_t, audio_soundtrack_mode=vault_aud_mode, target_duration_sec=vid_dur_sec, native_fps=float(frame_rate)) if str(audio_codec).lower() != 'mute' else False
            _encode_video_with_ffmpeg(frames_bhwc=frames, fps=final_fps, output_path=Path(saved_manifest_path), codec=codec, container=container, bit_depth=bit_depth, quality=quality, audio_wav_path=temp_wav if has_wav else None, audio_codec=audio_codec, audio_bitrate=audio_bitrate, crop_to_audio=crop_to_audio, save_metadata=save_metadata, metadata_payload=full_vault_meta)
            if temp_wav.exists():
                try:
                    temp_wav.unlink()
                except Exception:
                    pass
            stray_webp = target_folder / f'{stem_name}_{ts_str}_video.webp'
            if stray_webp.exists():
                try:
                    stray_webp.unlink()
                except Exception:
                    pass
            for stale_tmp in temp_dir.glob('ez_live_stream_*.webp'):
                try:
                    stale_tmp.unlink()
                except Exception:
                    pass
        if save_metadata:
            try:
                sidecar_json = target_folder / f'{stem_name}_{ts_str}_video.metadata.json'
                sidecar_json.write_text(json.dumps(full_vault_meta, indent=2, ensure_ascii=False), encoding='utf-8')
            except Exception:
                pass
        file_mb = round(Path(saved_manifest_path).stat().st_size / (1024.0 * 1024.0), 2) if Path(saved_manifest_path).exists() else 0.0
        rel_sub = target_folder.relative_to(out_dir).as_posix()
        clean_sub = '' if rel_sub == '.' else rel_sub
        anat_png_name = f'EZ_Vault_Anatomy_{ts_str}.png'
        anat_png_path = temp_dir / anat_png_name
        try:
            if isinstance(anatomy_preview, torch.Tensor) and anatomy_preview.ndim == 4 and (anatomy_preview.shape[0] > 0):
                anat_u8 = (anatomy_preview[0] * 255.0).clamp(0.0, 255.0).to(torch.uint8).numpy()
                Image.fromarray(anat_u8).save(str(anat_png_path))
        except Exception:
            pass
        v_meta = {'filename': video_filename, 'subfolder': clean_sub, 'type': 'output', 'preview_webp': '', 'anatomy_png': anat_png_name, 'fps': int(round(final_fps)), 'codec': str(codec), 'container': ext.upper(), 'quality': int(quality), 'size_mb': file_mb, 'frames': int(frames.shape[0]), 'format': ext}
        ui_images.append(v_meta)
        try:
            from server import PromptServer
            if getattr(PromptServer, 'instance', None) is not None:
                PromptServer.instance.send_sync('ez_cinematrix_vault_ready', v_meta)
        except Exception:
            pass
    if aggressive_purge or not bool(prof.get('persistent_vram_weights', False)):
        comfy.model_management.soft_empty_cache()
        gc.collect()
    return (frames, final_fps, saved_manifest_path, ui_images, anatomy_preview)
