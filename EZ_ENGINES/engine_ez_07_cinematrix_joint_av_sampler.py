# -*- coding: utf-8 -*-

import gc
import math
import re
import sys
import time
import torch
import comfy.model_management
import comfy.sample
import comfy.samplers
import comfy.utils
import latent_preview

def _is_nested_av_latent(x) -> bool:
    return bool(getattr(x, 'is_nested', False) or hasattr(x, 'tensors'))

def _unpack_av_tensors(x) -> list:
    if _is_nested_av_latent(x):
        return list(x.tensors) if hasattr(x, 'tensors') else list(x.unbind())
    return [x]

def _repack_av_tensors(template_x, tensor_list: list):
    if _is_nested_av_latent(template_x):
        import comfy.nested_tensor as _comfy_nt
        return _comfy_nt.NestedTensor(tensor_list)
    return tensor_list[0]

def _offload_completed_chunk_to_cpu(tensor_chunk):
    if _is_nested_av_latent(tensor_chunk):
        cpu_list = []
        for sub_t in _unpack_av_tensors(tensor_chunk):
            if isinstance(sub_t, torch.Tensor):
                cpu_list.append(sub_t.detach().to('cpu', non_blocking=True) if sub_t.is_cuda else sub_t.detach())
            else:
                cpu_list.append(sub_t)
        return _repack_av_tensors(tensor_chunk, cpu_list)
    if isinstance(tensor_chunk, torch.Tensor):
        return tensor_chunk.detach().to('cpu', non_blocking=True) if tensor_chunk.is_cuda else tensor_chunk.detach()
    return tensor_chunk

def _resolve_audio_time_dim(t: torch.Tensor) -> int:
    if not isinstance(t, torch.Tensor) or t.ndim != 4:
        return 1
    if t.shape[2] == 32 and t.shape[3] != 32:
        return 3
    if t.shape[3] == 32 and t.shape[2] != 32:
        return 2
    non_32 = [d for d in (1, 2, 3) if int(t.shape[d]) != 32]
    if non_32:
        return max(non_32, key=lambda d: int(t.shape[d]))
    return 3

def _slice_tensor_along_dim(t: torch.Tensor, dim: int, start: int, end: int) -> torch.Tensor:
    total = int(t.shape[dim])
    raw_len = max(1, end - start)
    length = max(2, raw_len // 2 * 2) if total >= 4 else raw_len
    length = min(total, length)
    safe_start = min(max(0, start // 2 * 2 if total >= 4 else start), max(0, total - length))
    return torch.narrow(t, dim, safe_start, length).clone()

def _slice_av_temporal_window(samples_obj, t_start: int, t_end: int, total_t: int):
    t_list = _unpack_av_tensors(samples_obj)
    sliced = []
    for (idx, t) in enumerate(t_list):
        if not isinstance(t, torch.Tensor):
            sliced.append(t)
            continue
        if t.ndim == 5:
            sliced.append(t[:, :, t_start:t_end, :, :].clone())
        elif t.ndim == 4:
            a_time_dim = _resolve_audio_time_dim(t)
            a_total = int(t.shape[a_time_dim])
            a_s = int(round(float(t_start) * float(a_total) / float(max(1, total_t))))
            a_e = max(a_s + 2, int(round(float(t_end) * float(a_total) / float(max(1, total_t)))))
            sliced.append(_slice_tensor_along_dim(t, a_time_dim, a_s, a_e))
        elif t.ndim == 3:
            a_time_dim = 2 if t.shape[1] == 32 and t.shape[2] != 32 else 1
            a_total = int(t.shape[a_time_dim])
            a_s = int(round(float(t_start) * float(a_total) / float(max(1, total_t))))
            a_e = max(a_s + 2, int(round(float(t_end) * float(a_total) / float(max(1, total_t)))))
            sliced.append(_slice_tensor_along_dim(t, a_time_dim, a_s, a_e))
        else:
            sliced.append(t.clone())
    return _repack_av_tensors(samples_obj, sliced)

_EZ_H3_FRAME_PERIOD = (1, 4, 4, 4, 4)
_EZ_H3_24CH_SPIKE_AXIS = (
    0.021, -0.081, 0.017, 0.119, -0.009, -0.203, -0.023, 0.016,
    -0.062, 0.020, -0.068, 0.045, -0.316, 0.004, -0.258, -0.278,
    -0.029, 0.508, -0.045, 0.367, 0.001, 0.239, 0.465, 0.109,
)
_EZ_H3_24CH_MEAN = (
    0.85809034, -0.96065915, 1.06616402, -0.50903255, -0.27275819, -1.36754143,
    -0.25532550, -0.26907554, -0.53768408, -0.04640973, 0.66573703, 0.19690128,
    -0.54606080, -0.40353420, -0.23683025, 0.25928453, -0.30133945, 0.21134199,
    -1.12068486, 0.35819334, -0.04225144, 0.26048300, 0.22864093, 0.70560318,
)
_EZ_H3_24CH_STD = (
    1.22237742, 1.27672637, 1.68317747, 1.75494552, 1.56362164, 2.19414353,
    0.96531379, 1.05698860, 0.84194893, 0.77299529, 1.89559376, 0.94684184,
    0.79968095, 0.44988900, 0.71973997, 0.69362932, 2.96109509, 2.76941991,
    3.04961848, 2.10880542, 3.27622628, 3.16273570, 2.28168130, 2.61278439,
)

def _h3_tokens_to_frames(tokens: int) -> int:
    (q_per, r_rem) = divmod(max(0, int(tokens)), 5)
    return 17 * q_per + sum(_EZ_H3_FRAME_PERIOD[:r_rem])

def _h3_frames_to_audio_steps(frames: int) -> int:
    return max(1, int(round(float(max(1, int(frames))) * 40.0 / 24.0)))

def _snap_h3_window_frames(frames: int) -> int:
    f_val = max(5, int(frames))
    return 17 * max(0, int(round(float(f_val - 5) / 17.0))) + 5

def _compute_audio_overlap_steps(aud_tensor: torch.Tensor, overlap_t: int, cur_len: int) -> int:
    a_time_dim = _resolve_audio_time_dim(aud_tensor)
    a_len = int(aud_tensor.shape[a_time_dim])
    if isinstance(aud_tensor, torch.Tensor) and aud_tensor.ndim == 4 and int(aud_tensor.shape[1]) == 32:
        ov_px = max(5, _h3_tokens_to_frames(max(2, int(overlap_t))))
        raw_ov = _h3_frames_to_audio_steps(ov_px)
        return max(1, min(max(1, a_len // 3), raw_ov))
    ov_px = max(1, (max(1, int(overlap_t)) - 1) * 4 + 1)
    total_px = max(5, (max(1, int(cur_len)) - 1) * 4 + 1)
    raw_ov = max(1, int(round(float(ov_px) * float(a_len) / float(total_px))))
    return max(1, min(max(1, a_len // 4), raw_ov))

def _inject_overlap_into_av_window(win_obj, accum_obj, overlap_t: int, cur_len: int):
    w_list = _unpack_av_tensors(win_obj)
    a_list = _unpack_av_tensors(accum_obj)
    out_list = []
    for (idx, w_t) in enumerate(w_list):
        a_t = a_list[idx] if idx < len(a_list) else None
        if isinstance(w_t, torch.Tensor) and isinstance(a_t, torch.Tensor):
            if w_t.ndim == 5 and a_t.ndim == 5 and (w_t.shape[2] > overlap_t) and (a_t.shape[2] >= overlap_t):
                w_copy = w_t.clone()
                ov_t = max(1, min(int(overlap_t), int(a_t.shape[2]), int(w_t.shape[2]) - 1))
                if float(w_copy[:, :, 0:1, :, :].abs().max().item()) <= 1e-04:
                    w_copy[:, :, 0:1, :, :] = a_t[:, :, -ov_t:-ov_t + 1 if ov_t > 1 else None, :, :].to(device=w_copy.device, dtype=w_copy.dtype)
                if ov_t > 1:
                    a_tail_4f = a_t[:, :, -(ov_t - 1):, :, :].to(device=w_copy.device, dtype=w_copy.dtype)
                    w_copy[:, :, 1:ov_t, :, :] = a_tail_4f
                out_list.append(w_copy)
                continue
            if w_t.ndim == 4 and a_t.ndim == 4:
                a_time_dim = _resolve_audio_time_dim(w_t)
                aud_ov = _compute_audio_overlap_steps(w_t, overlap_t, cur_len)
                if w_t.shape[a_time_dim] > aud_ov and a_t.shape[a_time_dim] >= aud_ov:
                    w_copy = w_t.clone()
                    tail = torch.narrow(a_t, a_time_dim, int(a_t.shape[a_time_dim]) - aud_ov, aud_ov)
                    torch.narrow(w_copy, a_time_dim, 0, aud_ov).copy_(tail)
                    out_list.append(w_copy)
                    continue
        out_list.append(w_t)
    return _repack_av_tensors(win_obj, out_list)

def _build_av_overlap_noise_mask(win_obj, base_mask, overlap_t: int, cur_len: int):
    import math
    w_list = _unpack_av_tensors(win_obj)
    m_list = _unpack_av_tensors(base_mask) if base_mask is not None else []
    out_masks = []
    for (idx, w_t) in enumerate(w_list):
        existing_m = m_list[idx].clone().detach().cpu().float() if idx < len(m_list) and isinstance(m_list[idx], torch.Tensor) else None
        if not isinstance(w_t, torch.Tensor):
            out_masks.append(existing_m)
            continue
        if w_t.ndim == 5:
            t_len = int(w_t.shape[2])
            tail_lock_val = None
            if existing_m is not None and existing_m.ndim == 5 and (existing_m.shape[2] == t_len):
                if t_len >= 3 and float(existing_m[:, :, -1:, :, :].mean().item()) < 0.95:
                    tail_lock_val = existing_m[:, :, -1:, :, :].clone()
                vm = existing_m
            else:
                vm = torch.ones((1, 1, t_len, 1, 1), dtype=torch.float32, device='cpu')
            ov_v = max(1, min(int(overlap_t or 1), t_len - 1))
            vm[:, :, 0:1, :, :] = 0.0
            if ov_v > 1 and t_len > ov_v:
                ramp_v = torch.linspace(0.55, 0.85, steps=ov_v - 1, dtype=torch.float32, device='cpu').view(1, 1, ov_v - 1, 1, 1)
                vm[:, :, 1:ov_v, :, :] = ramp_v.expand_as(vm[:, :, 1:ov_v, :, :])
                vm[:, :, ov_v:, :, :] = 1.0
            elif t_len > 1:
                vm[:, :, 1:, :, :] = 1.0
            if tail_lock_val is not None and t_len > ov_v + 1:
                vm[:, :, -1:, :, :] = tail_lock_val
            out_masks.append(vm)
        elif w_t.ndim == 4:
            a_time_dim = _resolve_audio_time_dim(w_t)
            a_len = int(w_t.shape[a_time_dim])
            if existing_m is not None and existing_m.ndim == 4 and (existing_m.shape[a_time_dim] == a_len):
                am = existing_m
            else:
                am_shape = [1, 1, 1, 1]
                am_shape[a_time_dim] = a_len
                am = torch.ones(am_shape, dtype=torch.float32, device='cpu')
            aud_ov = _compute_audio_overlap_steps(w_t, overlap_t, cur_len)
            if a_len > aud_ov and aud_ov >= 2:
                lock_half = max(1, aud_ov // 2)
                ramp_half = max(1, aud_ov - lock_half)
                lin_r = torch.linspace(0.0, 1.0, steps=ramp_half, dtype=torch.float32)
                smooth_r = 0.55 * (0.5 - 0.5 * torch.cos(lin_r * math.pi))
                full_r = torch.cat([torch.zeros(lock_half, dtype=torch.float32), smooth_r], dim=0)[:aud_ov]
                r_shape = [1, 1, 1, 1]
                r_shape[a_time_dim] = aud_ov
                target_slice = torch.narrow(am, a_time_dim, 0, aud_ov)
                target_slice.copy_(full_r.reshape(*r_shape).expand_as(target_slice))
            out_masks.append(am)
        else:
            out_masks.append(existing_m if existing_m is not None else torch.ones_like(w_t, dtype=torch.float32, device='cpu'))
    return _repack_av_tensors(base_mask if base_mask is not None else win_obj, out_masks)

def _stabilize_3d_video_latent_outliers(
    win_obj,
    outlier_strength: float = 0.35,
    motion_physics_mode: str = 'natural_organic',
    motion_strength: float = 0.65,
    anatomical_zones: dict = None,
):
    import torch.nn.functional as F
    t_list = _unpack_av_tensors(win_obj)
    out_list = []
    eff_sup = max(0.0, min(1.0, float(outlier_strength or 0.0)))
    anat_core = anatomical_zones.get('anat_core') if isinstance(anatomical_zones, dict) else None
    dock_cfg_z = anatomical_zones.get('dock_cfg') if isinstance(anatomical_zones, dict) and isinstance(anatomical_zones.get('dock_cfg'), dict) else {}
    if isinstance(anatomical_zones, dict) and isinstance(dock_cfg_z, dict) and len(dock_cfg_z) > 0 and isinstance(anatomical_zones.get('face'), torch.Tensor):
        try:
            wf = max(0.0, min(2.0, float(dock_cfg_z.get('lock_face_and_eyes', 1.0) or 1.0) / 1.0))
            wh = max(0.0, min(2.0, float(dock_cfg_z.get('lock_hands_and_fingers', 1.25) or 1.25) / 1.25))
            wt = max(0.0, min(2.0, float(dock_cfg_z.get('lock_torso_and_breasts', 1.10) or 1.10) / 1.10))
            wp = max(0.0, min(2.0, float(dock_cfg_z.get('lock_intimate_pelvic_anatomy', 1.35) or 1.35) / 1.35))
            wft = max(0.0, min(2.0, float(dock_cfg_z.get('lock_feet_and_toes', 1.15) or 1.15) / 1.15))
            mf = anatomical_zones['face'].float() * wf
            mh = anatomical_zones.get('hands', torch.zeros_like(mf)).float() * wh
            mt = anatomical_zones.get('torso', torch.zeros_like(mf)).float() * wt
            mp = anatomical_zones.get('pelvic', torch.zeros_like(mf)).float() * wp
            mft = anatomical_zones.get('feet', torch.zeros_like(mf)).float() * wft
            anat_core = torch.clamp(torch.maximum(torch.maximum(mp, mt), torch.maximum(mh, torch.maximum(mft, mf))), 0.0, 1.35)
        except Exception:
            pass
    for (idx, t) in enumerate(t_list):
        if isinstance(t, torch.Tensor):
            clean_t = torch.nan_to_num(t.float(), nan=0.0, posinf=12.0, neginf=-12.0)
            if idx == 0 and clean_t.ndim == 5 and eff_sup > 0.01 and clean_t.numel() > 32:
                if int(clean_t.shape[1]) == 24 and int(clean_t.shape[3]) >= 4 and int(clean_t.shape[4]) >= 4:
                    try:
                        axis_v = torch.tensor(_EZ_H3_24CH_SPIKE_AXIS, dtype=torch.float32, device=clean_t.device).view(1, 24, 1, 1, 1)
                        axis_norm_sq = torch.clamp((axis_v * axis_v).sum(), min=1e-06)
                        proj_s = (clean_t * axis_v).sum(dim=1, keepdim=True)
                        med_g = proj_s.median()
                        mad_g = torch.clamp(1.4826 * (proj_s - med_g).abs().median(), min=1e-05)
                        z_burn = (proj_s - med_g).abs() / mad_g
                        seed_hi = (z_burn > 11.2).float()
                        if float(seed_hi.max().item()) > 0.5:
                            cand_lo = (z_burn > 6.5).float()
                            hyst_m = seed_hi
                            for _ in range(2):
                                dil_m = F.max_pool3d(F.pad(hyst_m, (1, 1, 1, 1, 1, 1), mode='replicate'), kernel_size=3, stride=1)
                                hyst_m = torch.maximum(seed_hi, dil_m * cand_lo)
                            soft_m = F.avg_pool3d(F.pad(hyst_m, (1, 1, 1, 1, 0, 0), mode='replicate'), kernel_size=(1, 3, 3), stride=1)
                            keep_w = torch.clamp(1.0 - hyst_m, min=0.05)
                            k6 = torch.zeros((1, 1, 3, 3, 3), dtype=torch.float32, device=clean_t.device)
                            k6[0, 0, 1, 1, 0] = k6[0, 0, 1, 1, 2] = k6[0, 0, 1, 0, 1] = k6[0, 0, 1, 2, 1] = 1.0
                            if int(clean_t.shape[2]) >= 3:
                                k6[0, 0, 0, 1, 1] = k6[0, 0, 2, 1, 1] = 1.0
                            pad_p = F.pad(proj_s * keep_w, (1, 1, 1, 1, 1, 1), mode='replicate')
                            pad_w = F.pad(keep_w, (1, 1, 1, 1, 1, 1), mode='replicate')
                            ref_proj = F.conv3d(pad_p, k6) / torch.clamp(F.conv3d(pad_w, k6), min=1e-04)
                            proj_delta = (proj_s - ref_proj) * soft_m * min(0.92, eff_sup * 1.75)
                            clean_t = clean_t - proj_delta * (axis_v / axis_norm_sq)
                    except Exception:
                        pass
                sigma_cap = 7.0 if str(motion_physics_mode or '').startswith('hyper_kinetic') else 6.4
                mean_c = clean_t.mean(dim=(-2, -1), keepdim=True)
                std_c = torch.clamp(clean_t.std(dim=(-2, -1), keepdim=True), min=1e-04)
                z = (clean_t - mean_c) / std_c
                excess = torch.clamp(torch.abs(z) - sigma_cap, min=0.0)
                damped_z = torch.sign(z) * (torch.minimum(torch.abs(z), torch.full_like(z, sigma_cap)) + torch.tanh(excess / 2.0) * 1.8)
                damped_t = mean_c + damped_z * std_c
                if isinstance(anat_core, torch.Tensor) and anat_core.shape[-2:] == clean_t.shape[-2:]:
                    m_5d = torch.clamp(anat_core.to(device=clean_t.device, dtype=clean_t.dtype).unsqueeze(2), 0.0, 1.35)
                    core_area = float(torch.clamp(m_5d, 0.0, 1.0).mean().item())
                    fg_damp = eff_sup * (0.02 if core_area < 0.28 else 0.05)
                    bg_damp = eff_sup * 0.09
                    clean_t = torch.lerp(clean_t, damped_t, torch.clamp(m_5d * fg_damp + torch.clamp(1.0 - m_5d, 0.0, 1.0) * bg_damp, 0.0, 0.35))
                else:
                    clean_t = torch.lerp(clean_t, damped_t, eff_sup * 0.08)
            out_list.append(clean_t.to(dtype=t.dtype))
        else:
            out_list.append(t)
    return _repack_av_tensors(win_obj, out_list)

def _blend_and_cat_av_windows(accum_obj, win_obj, overlap_t: int, cur_len: int, temporal_rigidity: float=0.85):
    import math
    a_list = _unpack_av_tensors(accum_obj)
    w_list = _unpack_av_tensors(win_obj)
    merged = []
    rig = max(0.0, min(1.0, float(temporal_rigidity)))
    for (idx, (a_t, w_t)) in enumerate(zip(a_list, w_list)):
        if not isinstance(a_t, torch.Tensor) or not isinstance(w_t, torch.Tensor):
            merged.append(w_t)
            continue
        if a_t.ndim == 5 and w_t.ndim == 5:
            ov = min(int(overlap_t), int(a_t.shape[2]) - 1, int(w_t.shape[2]) - 1)
            if ov >= 1:
                lin_v = torch.linspace(0.0, 1.0, steps=ov, dtype=torch.float32, device=w_t.device)
                alpha_v = ((0.5 - 0.5 * torch.cos(lin_v * math.pi)) * (1.0 - 0.18 * rig)).to(dtype=w_t.dtype).reshape(1, 1, ov, 1, 1)
                a_head = a_t[:, :, :-ov, :, :]
                a_tail = a_t[:, :, -ov:, :, :]
                w_head = w_t[:, :, :ov, :, :]
                w_tail = w_t[:, :, ov:, :, :]
                seam_frames = torch.lerp(a_tail, w_head, alpha_v)
                merged.append(torch.cat([a_head, seam_frames, w_tail], dim=2))
            else:
                merged.append(torch.cat([a_t, w_t], dim=2))
        elif a_t.ndim == 4 and w_t.ndim == 4:
            a_time_dim = _resolve_audio_time_dim(w_t)
            aud_ov = _compute_audio_overlap_steps(w_t, overlap_t, cur_len)
            if overlap_t > 0 and w_t.shape[a_time_dim] > aud_ov and (a_t.shape[a_time_dim] >= aud_ov):
                a_len = int(a_t.shape[a_time_dim])
                w_len = int(w_t.shape[a_time_dim])
                alpha_shape = [1, 1, 1, 1]
                alpha_shape[a_time_dim] = aud_ov
                lin_a = torch.linspace(0.0, 1.0, steps=aud_ov, dtype=torch.float32, device=w_t.device)
                alpha = (0.5 - 0.5 * torch.cos(lin_a * math.pi)).to(dtype=w_t.dtype).reshape(*alpha_shape)
                a_head = torch.narrow(a_t, a_time_dim, 0, a_len - aud_ov)
                a_tail = torch.narrow(a_t, a_time_dim, a_len - aud_ov, aud_ov)
                w_head = torch.narrow(w_t, a_time_dim, 0, aud_ov)
                w_tail = torch.narrow(w_t, a_time_dim, aud_ov, w_len - aud_ov)
                blended = torch.lerp(a_tail, w_head, alpha)
                merged.append(torch.cat([a_head, blended, w_tail], dim=a_time_dim))
            else:
                merged.append(torch.cat([a_t, w_t], dim=a_time_dim))
        else:
            merged.append(w_t)
    return _repack_av_tensors(accum_obj, merged)

_WAN21_LATENT_RGB_FACTORS = (
    (-0.1299, -0.1692, 0.2932),
    (0.0671, 0.0406, 0.0442),
    (0.3568, 0.2548, 0.1747),
    (0.0372, 0.2344, 0.142),
    (0.0313, 0.0189, -0.0328),
    (0.0296, -0.0956, -0.0665),
    (-0.3477, -0.4059, -0.2925),
    (0.0166, 0.1902, 0.1975),
    (-0.0412, 0.0267, -0.1364),
    (-0.1293, 0.074, 0.1636),
    (0.068, 0.3019, 0.1128),
    (0.0032, 0.0581, 0.0639),
    (-0.1251, 0.0927, 0.1699),
    (0.006, -0.0633, 0.0005),
    (0.3477, 0.2275, 0.295),
    (0.1984, 0.0913, 0.1861),
)
_WAN21_LATENT_RGB_BIAS = (-0.1839, -0.0868, -0.336)

def _project_5d_latent_to_rgb_u8(vid_5d: torch.Tensor, max_frames: int=36, target_w: int=320):
    import numpy as np
    if not isinstance(vid_5d, torch.Tensor) or vid_5d.ndim != 5:
        return None
    x = vid_5d[0].detach().cpu().float()
    (c, t, h, w) = x.shape
    step_t = max(1, t // max(1, max_frames))
    x = x[:, ::step_t, :, :]
    use_c = min(16, c)
    factors = torch.tensor(_WAN21_LATENT_RGB_FACTORS[:use_c], dtype=torch.float32)
    bias = torch.tensor(_WAN21_LATENT_RGB_BIAS, dtype=torch.float32).view(1, 3, 1, 1)
    rgb = torch.einsum('cthw,cr->trhw', x[:use_c], factors) + bias
    rgb = ((rgb + 1.0) * 0.5).clamp(0.0, 1.0)
    out_w = max(128, int(target_w) // 2 * 2)
    out_h = max(96, int(round(h * (out_w / float(max(1, w))))) // 2 * 2)
    rgb = torch.nn.functional.interpolate(rgb, size=(out_h, out_w), mode='bilinear', align_corners=False)
    return (rgb.permute(0, 2, 3, 1).contiguous().numpy() * 255.0).clip(0, 255).astype(np.uint8)

def _emit_minipyav_live_video_preview(latent_av_obj, win_idx: int, total_wins: int, step_idx: int, total_steps: int, fps: float=24.0):
    try:
        import time
        from pathlib import Path
        from PIL import Image
        import folder_paths
        vid_t = _unpack_av_tensors(latent_av_obj)[0]
        rgb_u8 = _project_5d_latent_to_rgb_u8(vid_t, max_frames=36, target_w=320)
        if rgb_u8 is None or rgb_u8.shape[0] == 0:
            return
        temp_dir = Path(folder_paths.get_temp_directory())
        temp_dir.mkdir(parents=True, exist_ok=True)
        stamp = int(time.time() * 1000) % 1000000
        fname = f'ez_live_stream_{stamp}.mp4'
        fpath = temp_dir / fname
        wrote_mp4 = False
        try:
            import av
            container = av.open(str(fpath), mode='w')
            stream = container.add_stream('libx264', rate=max(8, int(round(fps))))
            stream.width = int(rgb_u8.shape[2])
            stream.height = int(rgb_u8.shape[1])
            stream.pix_fmt = 'yuv420p'
            stream.options = {'preset': 'ultrafast', 'crf': '26', 'tune': 'zerolatency'}
            for frame_arr in rgb_u8:
                vf = av.VideoFrame.from_ndarray(frame_arr, format='rgb24')
                for pkt in stream.encode(vf):
                    container.mux(pkt)
            for pkt in stream.encode():
                container.mux(pkt)
            container.close()
            wrote_mp4 = fpath.exists() and fpath.stat().st_size > 128
        except Exception:
            wrote_mp4 = False
        if not wrote_mp4:
            fname = f'ez_live_stream_{stamp}.webp'
            fpath = temp_dir / fname
            pils = [Image.fromarray(arr) for arr in rgb_u8]
            pils[0].save(str(fpath), save_all=True, append_images=pils[1:], duration=max(30, int(1000.0 / max(8.0, fps))), loop=0, quality=72)
        try:
            from server import PromptServer
            if getattr(PromptServer, 'instance', None) is not None:
                PromptServer.instance.send_sync('ez_cinematrix_live_preview', {'filename': fname, 'subfolder': '', 'type': 'temp', 'format': 'mp4' if wrote_mp4 else 'webp', 'window': int(win_idx + 1), 'total_windows': int(total_wins), 'step': int(step_idx), 'total_steps': int(total_steps), 'frames': int(vid_t.shape[2] * 4 - 3) if vid_t.ndim == 5 else 1})
        except Exception:
            pass
    except Exception:
        pass

def _inject_handoff_into_5d_cond_tensor(orig_v: torch.Tensor, sliced_v: torch.Tensor, key_name: str, accum_vid: torch.Tensor, overlap_t: int) -> torch.Tensor:
    if not isinstance(sliced_v, torch.Tensor) or sliced_v.ndim != 5 or (not isinstance(accum_vid, torch.Tensor)) or (accum_vid.ndim != 5):
        return sliced_v
    out_v = sliced_v.clone()
    is_single_start_cond = float(orig_v[:, :, -1:, :, :].abs().max().item()) < 1e-05 and orig_v.shape[2] > 1
    anchor_f = 1 if is_single_start_cond else max(1, min(int(overlap_t), max(1, int(out_v.shape[2]) // 3), int(accum_vid.shape[2])))
    k_low = str(key_name or '').lower()
    if 'mask' in k_low or out_v.shape[1] == 1:
        locked_val = orig_v[:, :, 0:1, :, :].to(device=out_v.device, dtype=out_v.dtype)
        free_val = orig_v[:, :, -1:, :, :].to(device=out_v.device, dtype=out_v.dtype)
        out_v[:, :, :anchor_f, :, :] = locked_val.expand(out_v.shape[0], out_v.shape[1], anchor_f, out_v.shape[3], out_v.shape[4])
        if out_v.shape[2] > anchor_f:
            out_v[:, :, anchor_f:, :, :] = free_val.expand(out_v.shape[0], out_v.shape[1], out_v.shape[2] - anchor_f, out_v.shape[3], out_v.shape[4])
        return out_v
    if out_v.shape[1] == accum_vid.shape[1] and out_v.shape[3:] == accum_vid.shape[3:]:
        start_idx = max(0, int(accum_vid.shape[2]) - int(overlap_t))
        handoff_slice = accum_vid[:, :, start_idx:start_idx + anchor_f, :, :].clone().float()
        actual_f = int(handoff_slice.shape[2])
        if actual_f > 0:
            if is_single_start_cond:
                out_v.zero_()
            out_v[:, :, :actual_f, :, :] = handoff_slice.to(device=out_v.device, dtype=out_v.dtype)
    return out_v

def _slice_conditioning_for_window(cond_list, t_start: int, t_end: int, total_t: int, accumulated_cpu=None, overlap_t: int=5, is_positive: bool=True):
    if not isinstance(cond_list, list):
        return cond_list
    accum_vid = _unpack_av_tensors(accumulated_cpu)[0] if accumulated_cpu is not None else None
    has_handoff = isinstance(accum_vid, torch.Tensor) and accum_vid.ndim == 5 and (t_start > 0) and (accum_vid.shape[2] >= 1)
    out_cond = []
    for entry in cond_list:
        if not isinstance(entry, (list, tuple)) or len(entry) < 2 or (not isinstance(entry[1], dict)):
            out_cond.append(entry)
            continue
        cond_tensor = entry[0]
        meta = dict(entry[1])
        if is_positive and isinstance(meta.get('ez_chronological_act_tensors'), list):
            act_list = meta['ez_chronological_act_tensors']
            if len(act_list) >= 2:
                prog = float(t_start) / float(max(1, total_t))
                act_idx = min(len(act_list) - 1, max(0, int(prog * len(act_list))))
                cand_t = act_list[act_idx]
                if isinstance(cand_t, torch.Tensor):
                    cond_tensor = cand_t.to(device=entry[0].device, dtype=entry[0].dtype) if isinstance(entry[0], torch.Tensor) else cand_t
        for (k, v) in list(meta.items()):
            if k == 'ez_chronological_act_tensors':
                continue
            if _is_nested_av_latent(v):
                sliced_nv = _slice_av_temporal_window(v, t_start, t_end, total_t)
                if has_handoff:
                    orig_sub = _unpack_av_tensors(v)
                    sl_sub = _unpack_av_tensors(sliced_nv)
                    if len(orig_sub) > 0 and len(sl_sub) > 0 and isinstance(sl_sub[0], torch.Tensor) and (sl_sub[0].ndim == 5):
                        sl_sub[0] = _inject_handoff_into_5d_cond_tensor(orig_sub[0], sl_sub[0], k, accum_vid, overlap_t)
                        sliced_nv = _repack_av_tensors(sliced_nv, sl_sub)
                meta[k] = sliced_nv
            elif isinstance(v, torch.Tensor) and v.ndim == 5 and (v.shape[2] == total_t):
                sliced_5d = _slice_av_temporal_window(v, t_start, t_end, total_t)
                if has_handoff:
                    sliced_5d = _inject_handoff_into_5d_cond_tensor(v, sliced_5d, k, accum_vid, overlap_t)
                meta[k] = sliced_5d
            elif isinstance(v, torch.Tensor) and v.ndim == 4 and (v.shape[2] == 32 or v.shape[3] == 32) and (max(v.shape[2], v.shape[3]) > 32):
                meta[k] = _slice_av_temporal_window(v, t_start, t_end, total_t)
            elif has_handoff and isinstance(v, torch.Tensor) and (v.ndim == 5) and (1 <= v.shape[2] < total_t) and (v.shape[1] == accum_vid.shape[1]) and (v.shape[3:] == accum_vid.shape[3:]):
                ref_len = min(int(v.shape[2]), int(accum_vid.shape[2]))
                start_r = max(0, int(accum_vid.shape[2]) - max(ref_len, int(overlap_t)))
                meta[k] = accum_vid[:, :, start_r:start_r + ref_len, :, :].clone().to(device=v.device, dtype=v.dtype)
            elif has_handoff and isinstance(v, list):
                new_list = []
                for item_v in v:
                    if isinstance(item_v, torch.Tensor) and item_v.ndim == 5 and (item_v.shape[1] == accum_vid.shape[1]) and (item_v.shape[3:] == accum_vid.shape[3:]):
                        r_len = min(int(item_v.shape[2]), int(accum_vid.shape[2]))
                        s_idx = max(0, int(accum_vid.shape[2]) - max(r_len, int(overlap_t)))
                        new_list.append(accum_vid[:, :, s_idx:s_idx + r_len, :, :].clone().to(device=item_v.device, dtype=item_v.dtype))
                    else:
                        new_list.append(item_v)
                meta[k] = new_list
        out_cond.append([cond_tensor, meta])
    return out_cond

def _ez_head_chunked_sdpa(q, k, v, heads: int, mask=None, skip_reshape: bool=False, skip_output_reshape: bool=False):
    if skip_reshape:
        (b, q_h, seq_q, dim_head) = q.shape
        heads = int(q_h)
        (q_4d, k_4d, v_4d) = (q, k, v)
    else:
        (b, seq_q, dim_total) = q.shape
        dim_head = dim_total // heads
        kv_heads_infer = max(1, int(k.shape[-1]) // max(1, dim_head)) if k.ndim == 3 else heads
        q_4d = q.view(b, seq_q, heads, dim_head).transpose(1, 2)
        k_4d = k.view(b, -1, kv_heads_infer, dim_head).transpose(1, 2)
        v_4d = v.view(b, -1, kv_heads_infer, dim_head).transpose(1, 2)
    kv_heads = max(1, int(k_4d.shape[1]))
    gqa_rep = max(1, heads // kv_heads) if heads % kv_heads == 0 else 1
    step_h = max(gqa_rep, min(max(gqa_rep, 6 // gqa_rep * gqa_rep), heads))
    try:
        out_4d = torch.empty((b, heads, seq_q, dim_head), dtype=q.dtype, device=q.device)
    except Exception:
        if hasattr(comfy.model_management, 'soft_empty_cache'):
            comfy.model_management.soft_empty_cache()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        out_4d = torch.empty((b, heads, seq_q, dim_head), dtype=q.dtype, device=q.device)
    for hs in range(0, heads, step_h):
        he = min(heads, hs + step_h)
        q_sub = q_4d[:, hs:he]
        if kv_heads == heads:
            k_sub = k_4d[:, hs:he]
            v_sub = v_4d[:, hs:he]
        elif gqa_rep > 1:
            k_sub = k_4d[:, hs // gqa_rep:max(hs // gqa_rep + 1, he // gqa_rep)].repeat_interleave(gqa_rep, dim=1)[:, :he - hs]
            v_sub = v_4d[:, hs // gqa_rep:max(hs // gqa_rep + 1, he // gqa_rep)].repeat_interleave(gqa_rep, dim=1)[:, :he - hs]
        else:
            k_sub = k_4d
            v_sub = v_4d
        m_sub = mask[:, hs:he] if isinstance(mask, torch.Tensor) and mask.ndim == 4 and (mask.shape[1] == heads) else mask
        out_4d[:, hs:he].copy_(torch.nn.functional.scaled_dot_product_attention(q_sub, k_sub, v_sub, attn_mask=m_sub, dropout_p=0.0, is_causal=False))
    if skip_output_reshape:
        return out_4d
    return out_4d.transpose(1, 2).reshape(b, seq_q, heads * dim_head)

def _install_sage_attention_oom_guard(model=None):
    import sys
    try:
        if torch.cuda.is_available():
            vram_gb = torch.cuda.get_device_properties(0).total_memory / 1024.0 ** 3
            if vram_gb < 20.0:
                cur_res = int(getattr(comfy.model_management, 'EXTRA_RESERVED_VRAM', 0) or 0)
                comfy.model_management.EXTRA_RESERVED_VRAM = min(max(cur_res, 400 * 1024 * 1024), 600 * 1024 * 1024)
        import comfy.ldm.modules.attention as comfy_attn
        orig_opt = getattr(comfy_attn, '_ez_true_orig_opt', None) or getattr(comfy_attn, 'optimized_attention', None)
        orig_pt = getattr(comfy_attn, '_ez_true_orig_pt', None) or getattr(comfy_attn, 'attention_pytorch', None)
        if callable(orig_opt) and (not getattr(orig_opt, '_ez_oom_guarded_v2', False)):
            comfy_attn._ez_true_orig_opt = orig_opt
            if callable(orig_pt) and (not getattr(orig_pt, '_ez_oom_guarded_v2', False)):
                comfy_attn._ez_true_orig_pt = orig_pt

            def _guarded_optimized_attention(q, k, v, heads, mask=None, attn_precision=None, skip_reshape=False, skip_output_reshape=False, **kwargs):
                try:
                    return comfy_attn._ez_true_orig_opt(q, k, v, heads, mask=mask, attn_precision=attn_precision, skip_reshape=skip_reshape, skip_output_reshape=skip_output_reshape, **kwargs)
                except torch.cuda.OutOfMemoryError:
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    return _ez_head_chunked_sdpa(q, k, v, int(heads), mask=mask, skip_reshape=skip_reshape, skip_output_reshape=skip_output_reshape)
                except Exception:
                    if callable(comfy_attn._ez_true_orig_pt):
                        return comfy_attn._ez_true_orig_pt(q, k, v, heads, mask=mask, attn_precision=attn_precision, skip_reshape=skip_reshape, skip_output_reshape=skip_output_reshape, **kwargs)
                    return _ez_head_chunked_sdpa(q, k, v, int(heads), mask=mask, skip_reshape=skip_reshape, skip_output_reshape=skip_output_reshape)
            _guarded_optimized_attention._ez_oom_guarded = True
            _guarded_optimized_attention._ez_oom_guarded_v2 = True
            comfy_attn.optimized_attention = _guarded_optimized_attention
            for (mod_name, mod_obj) in list(sys.modules.items()):
                if mod_obj is not None and mod_name.startswith('comfy.ldm'):
                    if hasattr(mod_obj, 'optimized_attention'):
                        setattr(mod_obj, 'optimized_attention', _guarded_optimized_attention)
    except Exception:
        pass

def _decode_handoff_frame_from_accum(accumulated_cpu, video_vae, overlap_t: int=1, tile_sz: int=512, master_first_frame=None, seg_pixel_frames: int=481, anatomical_zones: dict=None, allow_camera_movement: bool=False, pro_focus_seam_active: bool=True):
    if accumulated_cpu is None or video_vae is None:
        return None
    try:
        vid_t = _unpack_av_tensors(accumulated_cpu)[0]
        if not isinstance(vid_t, torch.Tensor) or vid_t.ndim != 5 or vid_t.shape[2] < 1:
            return None
        comfy.model_management.soft_empty_cache()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        tail_start = max(0, int(vid_t.shape[2]) - min(2, int(vid_t.shape[2])))
        tail_lat = vid_t[:, :, tail_start:, :, :].clone()
        fsm = getattr(video_vae, 'first_stage_model', None)
        if hasattr(fsm, 'latents_mean') and getattr(fsm.latents_mean, 'ndim', 0) >= 2 and int(fsm.latents_mean.shape[1]) > 0:
            exp_ch = int(fsm.latents_mean.shape[1])
            if tail_lat.shape[1] > exp_ch:
                tail_lat = tail_lat[:, :exp_ch]
            elif tail_lat.shape[1] < exp_ch:
                pad_s = list(tail_lat.shape)
                pad_s[1] = exp_ch - tail_lat.shape[1]
                tail_lat = torch.cat([tail_lat, torch.zeros(pad_s, dtype=tail_lat.dtype, device=tail_lat.device)], dim=1)
        with torch.no_grad():
            try:
                dec = video_vae.decode(tail_lat)
            except Exception:
                comfy.model_management.soft_empty_cache()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                dec = video_vae.decode_tiled(tail_lat, tile_x=int(tile_sz or 512), tile_y=int(tile_sz or 512))
        del tail_lat
        if isinstance(dec, torch.Tensor) and dec.numel() > 0:
            if dec.ndim == 5:
                dec = dec[0]
            dec = torch.clamp(dec.detach().cpu().float(), 0.0, 1.0)
            if isinstance(anatomical_zones, dict):
                anatomical_zones['_ez_handoff_reanchored'] = False
                anatomical_zones['_ez_handoff_trim_px'] = 0
            dec_all = dec
            dec = dec_all[-1:].clone()
            if int(dec_all.shape[0]) >= 3:
                try:
                    ref_tail = dec_all[-min(4, int(dec_all.shape[0])):-1, :, :, :3].mean(dim=0, keepdim=True)
                    d_mean = dec[:, :, :, :3].mean(dim=(1, 2), keepdim=True)
                    d_std = torch.clamp(dec[:, :, :, :3].std(dim=(1, 2), keepdim=True), min=1e-04)
                    r_mean = ref_tail.mean(dim=(1, 2), keepdim=True)
                    r_std = torch.clamp(ref_tail.std(dim=(1, 2), keepdim=True), min=1e-04)
                    tail_matched = torch.clamp((dec[:, :, :, :3] - d_mean) * torch.clamp(r_std / d_std, 0.97, 1.03) + r_mean, 0.0, 1.0)
                    dec[:, :, :, :3] = torch.lerp(dec[:, :, :, :3], tail_matched, 0.20)
                except Exception:
                    pass
            mf_aligned = None
            if isinstance(master_first_frame, torch.Tensor) and master_first_frame.ndim == 4 and master_first_frame.numel() > 16:
                try:
                    mf_raw = master_first_frame[-1:, :, :, :3].detach().cpu().float()
                    if int(mf_raw.shape[1]) != int(dec.shape[1]) or int(mf_raw.shape[2]) != int(dec.shape[2]):
                        mf_aligned = comfy.utils.common_upscale(mf_raw.movedim(-1, 1), int(dec.shape[2]), int(dec.shape[1]), 'lanczos', 'center').movedim(1, -1)
                    else:
                        mf_aligned = mf_raw
                except Exception:
                    mf_aligned = None
            w0_anchor = anatomical_zones.get('_ez_w0_rgb_anchor') if isinstance(anatomical_zones, dict) else None
            ref_src = w0_anchor if (isinstance(w0_anchor, torch.Tensor) and w0_anchor.ndim == 4 and w0_anchor.numel() > 16) else mf_aligned
            if isinstance(ref_src, torch.Tensor):
                try:
                    import torch.nn.functional as F
                    rf = ref_src[-1:, :, :, :3].detach().cpu().float()
                    if int(rf.shape[1]) != int(dec.shape[1]) or int(rf.shape[2]) != int(dec.shape[2]):
                        rf = comfy.utils.common_upscale(rf.movedim(-1, 1), int(dec.shape[2]), int(dec.shape[1]), 'lanczos', 'center').movedim(1, -1)
                    dec_rgb = dec[:, :, :, :3].float()
                    dec_std_val = float(dec_rgb.std().item())
                    if dec_std_val < 0.012:
                        dec[:, :, :, :3] = rf.clone()
                        if isinstance(anatomical_zones, dict):
                            anatomical_zones['_ez_handoff_reanchored'] = True
                    else:
                        d_bchw = dec_rgb.permute(0, 3, 1, 2)
                        r_bchw = rf.permute(0, 3, 1, 2)
                        d_lf = F.avg_pool2d(F.pad(d_bchw, (2, 2, 2, 2), mode='reflect'), kernel_size=5, stride=1)
                        r_lf = F.avg_pool2d(F.pad(r_bchw, (2, 2, 2, 2), mode='reflect'), kernel_size=5, stride=1)
                        d_hf = d_bchw - d_lf
                        r_hf = r_bchw - r_lf
                        d_hf_std = torch.clamp(d_hf.std(dim=(2, 3), keepdim=True), min=1e-04)
                        r_hf_std = torch.clamp(r_hf.std(dim=(2, 3), keepdim=True), min=1e-04)
                        hf_gain = torch.clamp(r_hf_std / d_hf_std, 0.62, 1.01)
                        d_hf_damped = d_hf * torch.lerp(torch.ones_like(hf_gain), hf_gain, 0.85)
                        d_lf_mean = d_lf.mean(dim=(2, 3), keepdim=True)
                        r_lf_mean = r_lf.mean(dim=(2, 3), keepdim=True)
                        d_lf_std = torch.clamp(d_lf.std(dim=(2, 3), keepdim=True), min=1e-04)
                        r_lf_std = torch.clamp(r_lf.std(dim=(2, 3), keepdim=True), min=1e-04)
                        lf_gain = torch.clamp(r_lf_std / d_lf_std, 0.74, 1.01)
                        mean_gap = float((d_lf_mean - r_lf_mean).abs().mean().item())
                        mean_blend = 0.48 if (isinstance(w0_anchor, torch.Tensor) or mean_gap <= 0.11) else 0.10
                        eff_lf_mean = torch.lerp(d_lf_mean, r_lf_mean, mean_blend)
                        d_lf_damped = (d_lf - d_lf_mean) * torch.lerp(torch.ones_like(lf_gain), lf_gain, 0.72) + eff_lf_mean
                        rebuilt = torch.clamp(d_lf_damped + d_hf_damped, 0.0, 1.0).permute(0, 2, 3, 1)
                        dec[:, :, :, :3] = rebuilt
                except Exception:
                    pass
            comfy.model_management.soft_empty_cache()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            return dec
    except Exception as dec_exc:
        print(f'[EZ-SAMPLER-07] Handoff frame decode notice: {dec_exc}')
        return None
    return None

def _rebuild_window_h3_conditioning(cont_ctx: dict, handoff_img, cur_len: int, t_start: int, total_t: int):
    if not isinstance(cont_ctx, dict):
        return (None, None, None, None)
    video_clip = cont_ctx.get('video_clip')
    video_vae = cont_ctx.get('video_vae')
    audio_vae = cont_ctx.get('audio_vae')
    video_arch = str(cont_ctx.get('video_arch', 'minimax_h3') or 'minimax_h3').lower()
    if video_clip is None or video_vae is None:
        return (None, None, None, None)
    try:
        comfy.model_management.soft_empty_cache()
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        w = max(64, int(round(float(cont_ctx.get('width', 736) or 736) / 32.0) * 32))
        h = max(64, int(round(float(cont_ctx.get('height', 512) or 512) / 32.0) * 32))
        prod_mode = str(cont_ctx.get('production_mode', 'I2VA') or 'I2VA')
        act_list = cont_ctx.get('act_prompts') if isinstance(cont_ctx.get('act_prompts'), list) else []
        if act_list and int(t_start) < len(act_list):
            act_str = str(act_list[max(0, int(t_start))] or '').strip()
        elif act_list:
            act_str = str(act_list[int(t_start) % len(act_list)] or '').strip()
        else:
            act_str = str(cont_ctx.get('timeline_prompt', '') or '').strip()
        frame_in = None
        if isinstance(handoff_img, torch.Tensor) and handoff_img.ndim == 4:
            nchw_all = handoff_img[-1:, :, :, :3].movedim(-1, 1)
            frame_in = comfy.utils.common_upscale(nchw_all, w, h, 'lanczos', 'center').movedim(1, -1).detach().cpu()
        master_kf_in = cont_ctx.get('first_frame_in')
        if isinstance(master_kf_in, torch.Tensor) and master_kf_in.ndim == 4:
            nchw_m = master_kf_in[-1:, :, :, :3].movedim(-1, 1)
            master_kf_in = comfy.utils.common_upscale(nchw_m, w, h, 'lanczos', 'center').movedim(1, -1).detach().cpu()
        else:
            master_kf_in = None
        r2_in = cont_ctx.get('r2_in')
        r3_in = cont_ctx.get('r3_in')
        r4_in = cont_ctx.get('r4_in')
        pro_routing = cont_ctx.get('pro_speaker_routing') if isinstance(cont_ctx.get('pro_speaker_routing'), dict) else {}
        if bool(pro_routing.get('active', False)) and bool(pro_routing.get('has_second_person_ref', False)) and isinstance(r2_in, torch.Tensor) and r2_in.ndim == 4:
            win_sp_ids = pro_routing.get('window_speaker_ids') if isinstance(pro_routing.get('window_speaker_ids'), list) else []
            cut_indices = pro_routing.get('scenecut_window_indices') if isinstance(pro_routing.get('scenecut_window_indices'), list) else []
            cur_sp_id = int(win_sp_ids[int(t_start)]) if 0 <= int(t_start) < len(win_sp_ids) else 0
            is_pro_cut = int(t_start) in cut_indices
            if cur_sp_id == 1:
                nchw_r2 = r2_in[-1:, :, :, :3].movedim(-1, 1)
                r2_scaled = comfy.utils.common_upscale(nchw_r2, w, h, 'lanczos', 'center').movedim(1, -1).detach().cpu()
                master_kf_in = r2_scaled
                if is_pro_cut or frame_in is None:
                    frame_in = r2_scaled
            elif cur_sp_id == 0 and is_pro_cut and isinstance(master_kf_in, torch.Tensor):
                frame_in = master_kf_in
        pre_cache = cont_ctx.get('pre_encoded_clip_cache') if isinstance(cont_ctx.get('pre_encoded_clip_cache'), dict) else {}

        class _CachedClipProxy:

            def __init__(self, real_clip, cache_map, master_kf_tensor=None, handoff_kf_tensor=None):
                self._real = real_clip
                self._cache = cache_map
                self._master_kf = master_kf_tensor
                self._handoff_kf = handoff_kf_tensor if isinstance(handoff_kf_tensor, torch.Tensor) else master_kf_tensor
                self._pending_cache_key = None
                self._last_key_str = None
                self._last_tok_kwargs = {}

            def tokenize(self, text, **kwargs):
                key_str = str(text or '').strip()
                self._last_key_str = key_str
                win_act_key = f'__EZ_WIN_ACT_{max(0, int(t_start))}__'
                if key_str in self._cache:
                    self._pending_cache_key = None
                    return {'__ez_cached_key__': key_str}
                if key_str == act_str or (act_str and act_str in key_str):
                    cand_keys = (win_act_key, act_str, '__EZ_WIN_ACT_0__', '__EZ_MASTER_KF_COND__')
                    for fallback_k in cand_keys:
                        if fallback_k in self._cache:
                            self._pending_cache_key = None
                            return {'__ez_cached_key__': fallback_k}
                tok_kw = dict(kwargs)
                has_img = any((k in tok_kw and tok_kw[k] is not None for k in ('images', 'image', 'vl_images')))
                if has_img and self._master_kf is not None and not prod_mode.startswith('REF2VA'):
                    for img_k in ('images', 'image', 'vl_images'):
                        if img_k in tok_kw and tok_kw[img_k] is not None:
                            tok_kw[img_k] = [self._master_kf] if isinstance(tok_kw[img_k], (list, tuple)) else self._master_kf
                self._last_tok_kwargs = dict(tok_kw)
                self._pending_cache_key = win_act_key if (key_str == act_str or (act_str and act_str in key_str)) else key_str
                return self._real.tokenize(text, **tok_kw)

            def encode_from_tokens_scheduled(self, tokens, **kwargs):
                if isinstance(tokens, dict) and '__ez_cached_key__' in tokens:
                    cached_cond = self._cache.get(tokens['__ez_cached_key__'])
                    if isinstance(cached_cond, list):
                        cloned = []
                        for item in cached_cond:
                            if isinstance(item, (list, tuple)) and len(item) >= 2:
                                t_c = item[0].clone() if isinstance(item[0], torch.Tensor) else item[0]
                                m_c = {mk: mv.clone() if isinstance(mv, torch.Tensor) else mv for (mk, mv) in (item[1].items() if isinstance(item[1], dict) else [])}
                                cloned.append([t_c, m_c])
                            else:
                                cloned.append(item)
                        return cloned
                encoded_res = self._real.encode_from_tokens_scheduled(tokens, **kwargs)
                if self._pending_cache_key and isinstance(encoded_res, list):
                    cpu_cached = [[it[0].detach().cpu() if isinstance(it[0], torch.Tensor) else it[0], {mk: _offload_completed_chunk_to_cpu(mv) for (mk, mv) in (it[1].items() if isinstance(it[1], dict) else [])}] if isinstance(it, (list, tuple)) and len(it) >= 2 else it for it in encoded_res]
                    self._cache[self._pending_cache_key] = cpu_cached
                    if int(t_start) <= 0 and self._last_key_str:
                        self._cache[self._last_key_str] = cpu_cached
                    if int(t_start) <= 0 and (self._last_key_str == act_str or (act_str and act_str in str(self._last_key_str or ''))):
                        self._cache['__EZ_MASTER_KF_COND__'] = cpu_cached
                        self._cache['__EZ_WIN_ACT_0__'] = cpu_cached
                        if len(act_list) >= 2:
                            for (act_i, raw_act_p) in enumerate(act_list):
                                cand_raw = str(raw_act_p or '').strip()
                                w_key = f'__EZ_WIN_ACT_{act_i}__'
                                if not cand_raw or w_key in self._cache:
                                    continue
                                try:
                                    cand_txt = self._last_key_str.replace(act_str, cand_raw, 1) if (act_str and act_str in str(self._last_key_str or '')) else cand_raw
                                    sub_tok = self._real.tokenize(cand_txt, **self._last_tok_kwargs)
                                    sub_enc = self._real.encode_from_tokens_scheduled(sub_tok, **kwargs)
                                    if isinstance(sub_enc, list):
                                        sub_cpu = [[it[0].detach().cpu() if isinstance(it[0], torch.Tensor) else it[0], {mk: _offload_completed_chunk_to_cpu(mv) for (mk, mv) in (it[1].items() if isinstance(it[1], dict) else [])}] if isinstance(it, (list, tuple)) and len(it) >= 2 else it for it in sub_enc]
                                        self._cache[w_key] = sub_cpu
                                        self._cache[cand_raw] = sub_cpu
                                        self._cache[cand_txt] = sub_cpu
                                except Exception:
                                    pass
                    self._pending_cache_key = None
                return encoded_res

            def __getattr__(self, name):
                return getattr(self._real, name)
        clip_proxy = _CachedClipProxy(video_clip, pre_cache, master_kf_tensor=master_kf_in, handoff_kf_tensor=frame_in)
        if video_arch == 'minimax_h3':
            win_pixel_frames = _snap_h3_window_frames(int(cur_len) if int(cur_len) >= 22 else _h3_tokens_to_frames(int(cur_len)))
        else:
            win_pixel_frames = int(cur_len) if int(cur_len) >= 65 else max(5, (int(cur_len) - 1) * 4 + 1)
            win_pixel_frames = max(5, (win_pixel_frames - 1) // 4 * 4 + 1)
        win_motion_mode = str(cont_ctx.get('motion_physics_mode', 'natural_organic') or 'natural_organic')
        win_motion_str = float(cont_ctx.get('motion_transfer_strength', 0.65) or 0.65)
        win_is_nsfw = bool(cont_ctx.get('is_nsfw', True))
        if isinstance(frame_in, torch.Tensor) and frame_in.ndim == 4:
            try:
                from .engine_ez_04_cinematrix_krea2_sampler import compute_downscaled_latent_anatomy_zones
                prev_zones = cont_ctx.get('anatomical_latent_zones') if isinstance(cont_ctx.get('anatomical_latent_zones'), dict) else {}
                prev_reanchored = bool(prev_zones.get('_ez_handoff_reanchored', False))
                master_rgb_stats = prev_zones.get('zone_rgb_stats')
                master_hf_stats = prev_zones.get('zone_hf_stats')
                master_face_crop = prev_zones.get('face_crop_bhwc')
                master_torso_crop = prev_zones.get('torso_crop_bhwc')
                master_pelvic_crop = prev_zones.get('pelvic_crop_bhwc')
                new_zones = compute_downscaled_latent_anatomy_zones(frame_in, max(8, h // 16), max(8, w // 16))
                if isinstance(new_zones, dict):
                    new_zones['_ez_handoff_reanchored'] = prev_reanchored
                    if isinstance(master_rgb_stats, dict):
                        new_zones['zone_rgb_stats'] = master_rgb_stats
                    if isinstance(master_hf_stats, dict):
                        new_zones['zone_hf_stats'] = master_hf_stats
                    if isinstance(master_face_crop, torch.Tensor):
                        new_zones['face_crop_bhwc'] = master_face_crop
                    if isinstance(master_torso_crop, torch.Tensor):
                        new_zones['torso_crop_bhwc'] = master_torso_crop
                    if isinstance(master_pelvic_crop, torch.Tensor):
                        new_zones['pelvic_crop_bhwc'] = master_pelvic_crop
                    cont_ctx['anatomical_latent_zones'] = new_zones
            except Exception:
                pass
        from .engine_ez_06_cinematrix_video_director import project_video_kinematic_conditioning, _resolve_window_fl2va_start_mid_end
        relay_anchors = cont_ctx.get('keyframe_relay_anchors') if isinstance(cont_ctx.get('keyframe_relay_anchors'), list) else []
        (win_start_kf, win_mid_kf, win_end_kf) = _resolve_window_fl2va_start_mid_end(
            relay_anchors,
            seg_idx=int(t_start),
            total_wins=int(total_t),
            handoff_img=frame_in if frame_in is not None else master_kf_in,
        )
        has_explicit_fl2va_end = bool(cont_ctx.get('has_explicit_fl2va_end', False))
        eff_start_in = frame_in if frame_in is not None else (win_start_kf if win_start_kf is not None else master_kf_in)
        use_dual_anchor_win = bool(has_explicit_fl2va_end)
        eff_end_in = (win_end_kf if win_end_kf is not None else (master_kf_in if master_kf_in is not None else eff_start_in)) if (eff_start_in is not None and use_dual_anchor_win) else None
        if video_arch in ('wan22', 'wan21'):
            import comfy_extras.nodes_wan as nodes_wan
            pos_raw = clip_proxy.encode_from_tokens_scheduled(clip_proxy.tokenize(act_str))
            neg_str = str(cont_ctx.get('negative_prompt', '') or '').strip()
            neg_raw = clip_proxy.encode_from_tokens_scheduled(clip_proxy.tokenize(neg_str))
            (pos_raw, neg_raw) = project_video_kinematic_conditioning(
                video_clip,
                pos_raw,
                neg_raw,
                motion_physics_mode=win_motion_mode,
                motion_strength=win_motion_str,
                video_arch=video_arch,
                is_nsfw=win_is_nsfw,
            )
            if video_arch == 'wan22' and hasattr(nodes_wan, 'Wan22ImageToVideoLatent'):
                wan_lat = nodes_wan.Wan22ImageToVideoLatent.execute(video_vae, w, h, win_pixel_frames, 1, eff_start_in)[0]
                return (pos_raw, neg_raw, _offload_completed_chunk_to_cpu(wan_lat['samples']), wan_lat.get('noise_mask'))
            elif hasattr(nodes_wan, 'WanImageToVideo'):
                wan_res = nodes_wan.WanImageToVideo.execute(pos_raw, neg_raw, video_vae, w, h, win_pixel_frames, 1, eff_start_in, eff_end_in)
                w_d = wan_res[2]
                return (wan_res[0], wan_res[1], _offload_completed_chunk_to_cpu(w_d['samples']), w_d.get('noise_mask'))
        from comfy_extras.nodes_minimax_h3 import MiniMaxH3ImageToVideo
        h3_res = None
        if prod_mode.startswith('REF2VA') and audio_vae is not None:
            try:
                from comfy_extras.nodes_minimax_h3 import MiniMaxH3ReferenceToVideo
                ref_list = [im for im in (eff_start_in, r2_in if r2_in is not None else master_kf_in, r3_in, r4_in) if isinstance(im, torch.Tensor) and im.ndim == 4]
                ref_batch = torch.cat(ref_list, dim=0) if ref_list else None
                h3_res = MiniMaxH3ReferenceToVideo.execute(clip_proxy, video_vae, audio_vae, act_str, w, h, win_pixel_frames, 'match', ref_batch, None, None, None)
            except Exception:
                h3_res = None
        if h3_res is None:
            h3_res = MiniMaxH3ImageToVideo.execute(clip_proxy, video_vae, act_str, w, h, win_pixel_frames, eff_start_in, eff_end_in)
        pos_c = h3_res[0]
        lat_d = h3_res[1]
        lat_s = lat_d['samples'] if isinstance(lat_d, dict) and 'samples' in lat_d else lat_d
        n_mask = lat_d.get('noise_mask') if isinstance(lat_d, dict) else None
        if isinstance(n_mask, torch.Tensor) and n_mask.ndim == 5 and int(n_mask.shape[2]) >= 3 and eff_end_in is not None:
            n_mask = n_mask.clone()
            end_min_noise = 0.28 if has_explicit_fl2va_end else 0.45
            n_mask[:, :, -1:, :, :] = torch.clamp(n_mask[:, :, -1:, :, :], min=end_min_noise)
        if video_arch == 'minimax_h3':
            try:
                from comfy.nested_tensor import NestedTensor
                t_existing = list(lat_s.tensors) if hasattr(lat_s, 'tensors') else ([lat_s] if isinstance(lat_s, torch.Tensor) else [])
                if len(t_existing) == 1 and isinstance(t_existing[0], torch.Tensor):
                    vid_5d = t_existing[0]
                    aud_t_len = _h3_frames_to_audio_steps(win_pixel_frames)
                    aud_4d = torch.zeros((int(vid_5d.shape[0]), 32, 2, aud_t_len), dtype=vid_5d.dtype, device=vid_5d.device)
                    lat_s = NestedTensor([vid_5d, aud_4d])
                    if isinstance(n_mask, torch.Tensor):
                        am_4d = torch.ones((int(vid_5d.shape[0]), 1, 1, aud_t_len), dtype=n_mask.dtype, device=n_mask.device)
                        n_mask = NestedTensor([n_mask, am_4d])
            except Exception:
                pass
        pos_meta = dict(pos_c[0][1]) if pos_c and len(pos_c[0]) > 1 and isinstance(pos_c[0][1], dict) else {}
        neg_str = str(cont_ctx.get('negative_prompt', '') or '').strip()
        if neg_str and float(cont_ctx.get('active_cfg', 1.0)) > 1.05:
            raw_neg = clip_proxy.encode_from_tokens_scheduled(clip_proxy.tokenize(neg_str))
            neg_c = [[item[0], {**pos_meta, **(dict(item[1]) if len(item) > 1 and isinstance(item[1], dict) else {})}] for item in raw_neg]
        else:
            neg_c = [[torch.zeros_like(t[0]), dict(t[1])] for t in pos_c]
        try:
            from .engine_ez_06_cinematrix_video_director import project_video_kinematic_conditioning
            (pos_c, neg_c) = project_video_kinematic_conditioning(
                video_clip,
                pos_c,
                neg_c,
                motion_physics_mode=win_motion_mode,
                motion_strength=win_motion_str,
                video_arch=video_arch,
                is_nsfw=win_is_nsfw,
            )
        except Exception:
            pass
        out_tuple = (
            [[t[0].detach().cpu() if isinstance(t[0], torch.Tensor) else t[0], {mk: _offload_completed_chunk_to_cpu(mv) for (mk, mv) in (it_m.items() if isinstance(it_m, dict) else [])}] for (t, it_m) in ((it, it[1] if len(it) > 1 else {}) for it in pos_c)],
            [[t[0].detach().cpu() if isinstance(t[0], torch.Tensor) else t[0], {mk: _offload_completed_chunk_to_cpu(mv) for (mk, mv) in (it_m.items() if isinstance(it_m, dict) else [])}] for (t, it_m) in ((it, it[1] if len(it) > 1 else {}) for it in neg_c)],
            _offload_completed_chunk_to_cpu(lat_s),
            _offload_completed_chunk_to_cpu(n_mask) if n_mask is not None else None,
        )
        comfy.model_management.soft_empty_cache()
        gc.collect()
        return out_tuple
    except Exception:
        return (None, None, None, None)

def _prism_extract_latent_channel_spectrum(kf_lat: torch.Tensor) -> dict:
    if not isinstance(kf_lat, torch.Tensor) or kf_lat.ndim != 5 or kf_lat.shape[2] < 1:
        return {}
    try:
        with torch.no_grad():
            f0 = kf_lat[0, :, 0, :, :].detach().cpu().float()
            c_dim = int(f0.shape[0])
            flat_c = f0.reshape(c_dim, -1)
            mean_c = flat_c.mean(dim=1, keepdim=True)
            centered = flat_c - mean_c
            u_mat, s_vec, _ = torch.linalg.svd(centered, full_matrices=False)
            n_pix = max(1.0, math.sqrt(float(flat_c.shape[1])))
            return {
                'u_basis': u_mat.detach().cpu(),
                'sigma_ref': (s_vec / n_pix).detach().cpu(),
                'mean_c': mean_c.detach().cpu(),
            }
    except Exception:
        return {}


def _prism_restore_latent_spectral_energy(v_frames: torch.Tensor, prism_spec: dict, blend_weight: float = 0.045) -> torch.Tensor:
    if not isinstance(v_frames, torch.Tensor) or v_frames.ndim != 5 or not isinstance(prism_spec, dict):
        return v_frames
    u_basis = prism_spec.get('u_basis')
    sigma_ref = prism_spec.get('sigma_ref')
    if not isinstance(u_basis, torch.Tensor) or not isinstance(sigma_ref, torch.Tensor):
        return v_frames
    try:
        with torch.no_grad():
            b_sz, c_sz, t_sz, h_sz, w_sz = v_frames.shape
            if int(u_basis.shape[0]) != c_sz or t_sz < 1:
                return v_frames
            orig_dt = v_frames.dtype
            vf = v_frames.float()
            u_dev = u_basis.to(device=vf.device, dtype=torch.float32)
            s_ref_dev = sigma_ref.to(device=vf.device, dtype=torch.float32).view(1, c_sz, 1, 1)
            flat_sp = vf.reshape(b_sz, c_sz, t_sz, h_sz * w_sz)
            m_sp = flat_sp.mean(dim=-1, keepdim=True)
            centered_sp = flat_sp - m_sp
            proj = torch.einsum('dc,bctk->bdtk', u_dev.t(), centered_sp)
            cur_sigma = torch.sqrt(torch.clamp((proj * proj).mean(dim=-1, keepdim=True), min=1e-7))
            gain = torch.clamp(s_ref_dev / cur_sigma, 0.96, 1.07)
            proj_cal = proj * gain
            rebuilt = (torch.einsum('cd,bdtk->bctk', u_dev, proj_cal) + m_sp).reshape(b_sz, c_sz, t_sz, h_sz, w_sz)
            return torch.lerp(vf, rebuilt, float(blend_weight)).to(dtype=orig_dt)
    except Exception:
        return v_frames


def _inject_h3_native_latent_tail_keyframes(pos_cond, neg_cond, prev_seg_cpu, overlap_t: int, master_lat_stats: dict = None, force_tail_replace: bool = False, act_cond_override: torch.Tensor = None, act_cond_meta_override: dict = None):
    if prev_seg_cpu is None or not isinstance(pos_cond, list):
        return (pos_cond, neg_cond)
    try:
        prev_list = _unpack_av_tensors(prev_seg_cpu)
        prev_vid = prev_list[0] if len(prev_list) > 0 and isinstance(prev_list[0], torch.Tensor) else None
        prev_aud = prev_list[1] if len(prev_list) > 1 and isinstance(prev_list[1], torch.Tensor) else None
        if not isinstance(prev_vid, torch.Tensor) or prev_vid.ndim != 5 or int(prev_vid.shape[1]) != 24 or int(prev_vid.shape[2]) < 1:
            return (pos_cond, neg_cond)
        tail_v = prev_vid[:, :, -1:, :, :].clone().detach().cpu()
        tail_a = None
        if isinstance(prev_aud, torch.Tensor) and prev_aud.ndim == 4 and int(prev_aud.shape[1]) == 32:
            a_dim = _resolve_audio_time_dim(prev_aud)
            a_len = int(prev_aud.shape[a_dim])
            ov_a = min(max(1, a_len - 1), _h3_frames_to_audio_steps(1))
            if ov_a >= 1 and a_len > ov_a:
                tail_a = torch.narrow(prev_aud, a_dim, a_len - ov_a, ov_a).clone().detach().cpu()

        def _patch_cond_keyframes(c_list, is_pos: bool = False):
            if not isinstance(c_list, list):
                return c_list
            patched = []
            for item in c_list:
                if not isinstance(item, (list, tuple)) or len(item) < 2 or not isinstance(item[1], dict):
                    patched.append(item)
                    continue
                md = dict(item[1])
                raw_kfs = md.get('minimax_keyframes')
                if is_pos and isinstance(act_cond_meta_override, dict):
                    for (mk, mv) in act_cond_meta_override.items():
                        if mk != 'minimax_keyframes':
                            md[mk] = mv.clone() if isinstance(mv, torch.Tensor) else mv
                if isinstance(raw_kfs, (list, tuple)):
                    existing_kf0 = next((dict(k) for k in raw_kfs if isinstance(k, dict) and int(k.get('resolved_frame_index', -1)) == 0 and isinstance(k.get('latent'), torch.Tensor)), None)
                    keep_end_kfs = bool((master_lat_stats or {}).get('has_explicit_fl2va_end', False))
                    new_kfs = [dict(k) for k in raw_kfs if isinstance(k, dict) and int(k.get('resolved_frame_index', -1)) != 0] if keep_end_kfs else []
                    if not force_tail_replace and existing_kf0 is not None and isinstance(existing_kf0.get('latent'), torch.Tensor) and existing_kf0['latent'].shape == tail_v.shape:
                        enc_lat = existing_kf0['latent'].detach().cpu().float()
                        if isinstance(master_lat_stats, dict) and isinstance(master_lat_stats.get('mean'), torch.Tensor) and isinstance(master_lat_stats.get('std'), torch.Tensor):
                            m_mean = master_lat_stats['mean'].to(device=enc_lat.device, dtype=torch.float32)
                            m_std = master_lat_stats['std'].to(device=enc_lat.device, dtype=torch.float32)
                            if float(m_std.mean().item()) > 0.05:
                                e_mean = enc_lat.mean(dim=(2, 3, 4), keepdim=True)
                                e_std = torch.clamp(enc_lat.std(dim=(2, 3, 4), keepdim=True), min=1e-04)
                                e_matched = (enc_lat - e_mean) * torch.clamp(m_std / e_std, 0.78, 1.02) + torch.lerp(e_mean, m_mean, 0.35)
                                enc_lat = torch.lerp(enc_lat, e_matched, 0.55)
                        kf0_lat = enc_lat.to(dtype=tail_v.dtype)
                    else:
                        kf0_lat = tail_v.clone()
                        if isinstance(master_lat_stats, dict) and isinstance(master_lat_stats.get('mean'), torch.Tensor) and isinstance(master_lat_stats.get('std'), torch.Tensor):
                            m_mean = master_lat_stats['mean'].to(device=kf0_lat.device, dtype=torch.float32)
                            m_std = master_lat_stats['std'].to(device=kf0_lat.device, dtype=torch.float32)
                            if float(m_std.mean().item()) > 0.05:
                                k_f = kf0_lat.float()
                                k_mean = k_f.mean(dim=(2, 3, 4), keepdim=True)
                                k_std = torch.clamp(k_f.std(dim=(2, 3, 4), keepdim=True), min=1e-04)
                                k_matched = (k_f - k_mean) * torch.clamp(m_std / k_std, 0.72, 1.02) + torch.lerp(k_mean, m_mean, 0.50)
                                kf0_lat = torch.lerp(k_f, k_matched, 0.72).to(dtype=tail_v.dtype)
                    kf0_entry = {'resolved_frame_index': 0, 'latent': kf0_lat}
                    if tail_a is not None and not bool((master_lat_stats or {}).get('suno_active', False)):
                        kf0_entry['audio_latent'] = tail_a.clone()
                    new_kfs.insert(0, kf0_entry)
                    md['minimax_keyframes'] = new_kfs
                tok_t = act_cond_override.clone().to(device=item[0].device, dtype=item[0].dtype) if (is_pos and isinstance(act_cond_override, torch.Tensor) and isinstance(item[0], torch.Tensor) and act_cond_override.ndim == item[0].ndim) else item[0]
                patched.append([tok_t, md])
            return patched

        return (_patch_cond_keyframes(pos_cond, is_pos=True), _patch_cond_keyframes(neg_cond, is_pos=False) if isinstance(neg_cond, list) else neg_cond)
    except Exception:
        return (pos_cond, neg_cond)

def _attach_temporal_continuity_lock(
    model,
    accum_so_far,
    overlap_t: int,
    cur_len: int,
    temporal_rigidity: float = 0.85,
    suno_audio_anchor=None,
    master_lat_stats: dict = None,
    viseme_env_win=None,
    mocap_deltas_win=None,
    motion_physics_mode: str = 'natural_organic',
    motion_strength: float = 0.65,
    anatomical_zones: dict = None,
    win_start_latent=None,
    win_mid_latent=None,
    win_end_latent=None,
    allow_camera_movement: bool = False,
):
    has_suno_aud = isinstance(suno_audio_anchor, torch.Tensor) and suno_audio_anchor.numel() > 16
    has_viseme = isinstance(viseme_env_win, torch.Tensor) and viseme_env_win.ndim == 2 and viseme_env_win.shape[0] >= 4
    has_mocap = isinstance(mocap_deltas_win, torch.Tensor) and mocap_deltas_win.ndim == 5
    is_vocal_mode = has_suno_aud or has_viseme or str(motion_physics_mode or '').startswith('expressive_vocal')
    accum_vid = _unpack_av_tensors(accum_so_far)[0] if accum_so_far is not None else None
    ov = max(1, int(overlap_t or 1))
    has_accum_ov = isinstance(accum_vid, torch.Tensor) and accum_vid.ndim == 5 and int(accum_vid.shape[2]) >= ov
    has_master_stats = (
        isinstance(master_lat_stats, dict)
        and isinstance(master_lat_stats.get('mean'), torch.Tensor)
        and isinstance(master_lat_stats.get('std'), torch.Tensor)
        and float(master_lat_stats['std'].float().mean().item()) > 0.05
    )
    if model is None or (not has_suno_aud and not has_viseme and not has_mocap and not has_accum_ov and not has_master_stats):
        return model
    try:
        suno_aud_cpu = suno_audio_anchor.detach().cpu().clone() if has_suno_aud else None
        vis_cpu = viseme_env_win.detach().cpu().float() if has_viseme else None
        mocap_cpu = mocap_deltas_win.detach().cpu().float() if has_mocap else None
        accum_tail_cpu = accum_vid[:, :, -ov:, :, :].detach().cpu().clone() if has_accum_ov else None
        m_mean_cpu = master_lat_stats['mean'].detach().cpu().float() if has_master_stats else None
        m_std_cpu = master_lat_stats['std'].detach().cpu().float() if has_master_stats else None
        kf_lat_cpu = master_lat_stats.get('master_kf_latent') if isinstance(master_lat_stats, dict) else None
        if isinstance(kf_lat_cpu, torch.Tensor) and float(kf_lat_cpu.float().abs().max().item()) <= 1e-04:
            kf_lat_cpu = None
        f0_win_cpu = (
            win_start_latent.detach().cpu().float()
            if isinstance(win_start_latent, torch.Tensor) and win_start_latent.ndim == 5 and float(win_start_latent.float().abs().max().item()) > 1e-04
            else kf_lat_cpu
        )
        f_mid_win_cpu = (
            win_mid_latent.detach().cpu().float()
            if isinstance(win_mid_latent, torch.Tensor) and win_mid_latent.ndim == 5 and float(win_mid_latent.float().abs().max().item()) > 1e-04
            else f0_win_cpu
        )
        f_end_win_cpu = (
            win_end_latent.detach().cpu().float()
            if isinstance(win_end_latent, torch.Tensor) and win_end_latent.ndim == 5 and float(win_end_latent.float().abs().max().item()) > 1e-04
            else f0_win_cpu
        )
        anat_core_cpu = anatomical_zones.get('anat_core') if isinstance(anatomical_zones, dict) else None
        anat_head_cpu = (anatomical_zones.get('face') if isinstance(anatomical_zones.get('face'), torch.Tensor) else anatomical_zones.get('anat_head')) if isinstance(anatomical_zones, dict) else None
        anat_torso_cpu = anatomical_zones.get('torso') if isinstance(anatomical_zones, dict) else None
        anat_pelvic_cpu = anatomical_zones.get('pelvic') if isinstance(anatomical_zones, dict) else None
        rig_box_info = anatomical_zones.get('skeletal_rig') if isinstance(anatomical_zones, dict) and isinstance(anatomical_zones.get('skeletal_rig'), dict) else {}
        head_box_norm = rig_box_info.get('head_box_norm', (0.04, 0.22, 0.42, 0.78))
        anat_ref_lat = f0_win_cpu if isinstance(f0_win_cpu, torch.Tensor) else kf_lat_cpu
        anat_mean_cpu = None
        anat_std_cpu = None
        if isinstance(anat_ref_lat, torch.Tensor) and isinstance(anat_core_cpu, torch.Tensor) and anat_ref_lat.ndim == 5 and anat_core_cpu.ndim == 4 and (anat_ref_lat.shape[3:] == anat_core_cpu.shape[2:]):
            w_mask = torch.clamp(anat_core_cpu.unsqueeze(2).float(), 0.0, 1.0)
            w_sum = torch.clamp(w_mask.sum(dim=(2, 3, 4), keepdim=True), min=1e-04)
            if float(w_mask.max().item()) > 0.05:
                anat_mean_cpu = (anat_ref_lat.float() * w_mask).sum(dim=(2, 3, 4), keepdim=True) / w_sum
                anat_var_cpu = ((anat_ref_lat.float() - anat_mean_cpu) ** 2 * w_mask).sum(dim=(2, 3, 4), keepdim=True) / w_sum
                anat_std_cpu = torch.sqrt(torch.clamp(anat_var_cpu, min=1e-05))
        has_explicit_traj = (
            isinstance(f0_win_cpu, torch.Tensor)
            and isinstance(f_end_win_cpu, torch.Tensor)
            and f0_win_cpu.shape == f_end_win_cpu.shape
            and float((f_end_win_cpu - f0_win_cpu).abs().mean().item()) > 0.02
        )
        prism_spec_cpu = master_lat_stats.get('prism_spec') if isinstance(master_lat_stats, dict) and isinstance(master_lat_stats.get('prism_spec'), dict) else None
        rig = max(0.0, min(1.0, float(temporal_rigidity)))
        m_str = max(0.1, min(1.5, float(motion_strength or 0.65)))
        m_opts_lock = getattr(model, 'model_options', {}) if hasattr(model, 'model_options') and isinstance(getattr(model, 'model_options'), dict) else {}
        is_turbo_lock = bool(m_opts_lock.get('has_turbo_lora', False)) or bool(m_opts_lock.get('unet_has_baked_turbo', False))
        cloned_m = model.clone()

        def _ez_overlap_post_cfg_anchor(args):
            denoised = args.get('denoised')
            sigma = args.get('sigma')
            if denoised is None:
                return denoised
            try:
                sig_val = float(sigma.flatten()[0].item()) if isinstance(sigma, torch.Tensor) and sigma.numel() > 0 else float(sigma or 0.0)
                d_list = _unpack_av_tensors(denoised)
                modified = False
                cond_den = args.get('cond_denoised')
                if is_turbo_lock and cond_den is not None and sig_val < 0.60:
                    c_list = _unpack_av_tensors(cond_den)
                    if len(c_list) > 0 and len(d_list) > 0 and isinstance(c_list[0], torch.Tensor) and isinstance(d_list[0], torch.Tensor) and c_list[0].shape == d_list[0].shape:
                        taper_w = min(0.88, max(0.0, (0.60 - sig_val) / 0.60) * 0.88)
                        if taper_w > 0.02:
                            d_list[0] = torch.lerp(d_list[0], c_list[0].to(device=d_list[0].device, dtype=d_list[0].dtype), taper_w)
                            modified = True
                if len(d_list) > 0 and isinstance(d_list[0], torch.Tensor) and d_list[0].ndim == 5:
                    v_den = d_list[0]
                    is_h3_24c = (int(v_den.shape[1]) == 24)
                    if not is_h3_24c:
                        if accum_tail_cpu is not None and v_den.shape[3:] == accum_tail_cpu.shape[3:] and sig_val >= 0.05:
                            a_dev = accum_tail_cpu.to(device=v_den.device, dtype=v_den.dtype)
                            v_den = v_den.clone()
                            w_f0 = 0.24 * min(1.0, max(0.20, sig_val))
                            v_den[:, :, 0:1, :, :] = torch.lerp(v_den[:, :, 0:1, :, :], a_dev[:, :, -1:, :, :], w_f0)
                            d_list[0] = v_den
                            modified = True
                            if ov >= 2 and v_den.shape[2] > ov and sig_val >= 0.20:
                                w_ov = min(0.24, (0.10 + 0.08 * min(1.0, sig_val)) * rig)
                                v_den[:, :, 1:ov, :, :] = torch.lerp(v_den[:, :, 1:ov, :, :], a_dev[:, :, -ov + 1:, :, :], w_ov)
                                d_list[0] = v_den
                                modified = True
                    if mocap_cpu is not None and v_den.shape[2] > 1 and sig_val >= 0.16:
                        v_den = d_list[0].clone() if not modified else d_list[0]
                        t_mc = min(int(v_den.shape[2]) - 1, int(mocap_cpu.shape[2]))
                        if t_mc >= 1 and mocap_cpu.shape[3:] == v_den.shape[3:]:
                            mc_ch = min(int(v_den.shape[1]), int(mocap_cpu.shape[1]))
                            mc_dev = mocap_cpu[:, :mc_ch, :t_mc, :, :].to(device=v_den.device, dtype=v_den.dtype)
                            mc_gain = (0.11 if is_h3_24c else 0.14) * m_str * min(1.0, sig_val)
                            v_den[:, :mc_ch, 1:1 + t_mc, :, :] = v_den[:, :mc_ch, 1:1 + t_mc, :, :] + mc_dev * mc_gain
                            d_list[0] = v_den
                            modified = True
                    if vis_cpu is not None and v_den.shape[2] > 1 and sig_val >= 0.14:
                        v_den = d_list[0].clone() if not modified else d_list[0]
                        t_vis = min(int(v_den.shape[2]) - 1, int(vis_cpu.shape[2]) - 1)
                        if t_vis >= 1:
                            hl_v = int(v_den.shape[3])
                            wl_v = int(v_den.shape[4])
                            hy0, hx0, hy1, hx1 = head_box_norm if (isinstance(head_box_norm, (tuple, list)) and len(head_box_norm) == 4) else (0.04, 0.34, 0.32, 0.68)
                            jy0 = max(0, min(hl_v - 1, int(round((hy0 + 0.52 * (hy1 - hy0)) * hl_v))))
                            jy1 = max(jy0 + 1, min(hl_v, int(round((hy1 + 0.04 * (hy1 - hy0)) * hl_v))))
                            jx0 = max(0, min(wl_v - 1, int(round((hx0 + 0.18 * (hx1 - hx0)) * wl_v))))
                            jx1 = max(jx0 + 1, min(wl_v, int(round((hx1 - 0.18 * (hx1 - hx0)) * wl_v))))
                            jaw_env = vis_cpu[:, 0:1, 1:1 + t_vis, :, :].to(device=v_den.device, dtype=v_den.dtype)
                            plosive_env = (vis_cpu[:, 2:3, 1:1 + t_vis, :, :] if vis_cpu.shape[1] >= 3 else vis_cpu[:, 0:1, 1:1 + t_vis, :, :]).to(device=v_den.device, dtype=v_den.dtype)
                            jaw_centered = (jaw_env - jaw_env.mean(dim=2, keepdim=True)) + 0.35 * (plosive_env - plosive_env.mean(dim=2, keepdim=True))
                            f0_mouth = v_den[:, :, 0:1, jy0:jy1, jx0:jx1]
                            mouth_slice_cur = v_den[:, :, 1:1 + t_vis, jy0:jy1, jx0:jx1]
                            mouth_std = torch.clamp(f0_mouth.std(dim=(3, 4), keepdim=True), min=0.08, max=1.25)
                            vis_gain = 0.22 * min(1.0, sig_val)
                            v_den[:, :, 1:1 + t_vis, jy0:jy1, jx0:jx1] = mouth_slice_cur + jaw_centered * mouth_std * vis_gain
                            d_list[0] = v_den
                            modified = True
                if len(d_list) > 1 and isinstance(d_list[1], torch.Tensor):
                    a_den = d_list[1]
                    if suno_aud_cpu is not None and sig_val >= 0.005 and suno_aud_cpu.shape == a_den.shape:
                        suno_dev = suno_aud_cpu.to(device=a_den.device, dtype=a_den.dtype)
                        d_list[1] = torch.lerp(a_den, suno_dev, 0.98)
                        modified = True
                if modified:
                    return _repack_av_tensors(denoised, d_list)
            except Exception:
                pass
            return denoised
        if hasattr(cloned_m, 'set_model_sampler_post_cfg_function'):
            cloned_m.set_model_sampler_post_cfg_function(_ez_overlap_post_cfg_anchor)
        return cloned_m
    except Exception:
        return model

def _sanitize_minimax_patchify_tree(obj):
    if getattr(obj, 'is_nested', False) or hasattr(obj, 'tensors'):
        t_list = [_sanitize_minimax_patchify_tree(t) for t in (list(obj.tensors) if hasattr(obj, 'tensors') else list(obj.unbind()))]
        return _repack_av_tensors(obj, t_list)
    if isinstance(obj, torch.Tensor):
        if obj.ndim == 5 and obj.shape[1] in (16, 24, 32, 48) and ((obj.shape[-2] % 2 != 0) or (obj.shape[-1] % 2 != 0)):
            import torch.nn.functional as F
            return F.pad(obj, (0, obj.shape[-1] % 2, 0, obj.shape[-2] % 2), mode='replicate')
        return obj
    if isinstance(obj, dict):
        return {k: _sanitize_minimax_patchify_tree(v) for (k, v) in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_minimax_patchify_tree(x) for x in obj]
    if isinstance(obj, tuple):
        return tuple((_sanitize_minimax_patchify_tree(x) for x in obj))
    return obj

def _sample_single_temporal_window(
    model,
    noise_w,
    steps,
    cfg,
    sampler_name,
    scheduler,
    positive,
    negative,
    latent_w,
    denoise,
    noise_mask_w,
    disable_pbar,
    seed,
    win_idx: int = 0,
    total_wins: int = 1,
    accum_so_far=None,
    overlap_t: int = 2,
    temporal_rigidity: float = 0.85,
    suno_audio_anchor=None,
    master_lat_stats: dict = None,
    viseme_env_win=None,
    mocap_deltas_win=None,
    motion_physics_mode: str = 'natural_organic',
    motion_strength: float = 0.65,
    anatomical_zones: dict = None,
    allow_camera_movement: bool = False,
):
    positive = _sanitize_minimax_patchify_tree(positive)
    negative = _sanitize_minimax_patchify_tree(negative)
    latent_w = _sanitize_minimax_patchify_tree(latent_w)
    noise_w = _sanitize_minimax_patchify_tree(noise_w)
    lat_v = _unpack_av_tensors(latent_w)[0]
    cur_t_len = int(lat_v.shape[2]) if isinstance(lat_v, torch.Tensor) and lat_v.ndim == 5 else 21
    f0_win = lat_v[:, :, 0:1, :, :].detach().cpu().float() if isinstance(lat_v, torch.Tensor) and lat_v.ndim == 5 and lat_v.shape[2] >= 1 else None
    f_end_win = lat_v[:, :, -1:, :, :].detach().cpu().float() if isinstance(lat_v, torch.Tensor) and lat_v.ndim == 5 and lat_v.shape[2] >= 2 and float(lat_v[:, :, -1:, :, :].detach().abs().max().item()) > 1e-04 else f0_win
    f_mid_win = (0.5 * (f0_win + f_end_win)) if (isinstance(f0_win, torch.Tensor) and isinstance(f_end_win, torch.Tensor)) else f0_win
    active_m = _attach_temporal_continuity_lock(
        model,
        accum_so_far if win_idx > 0 else None,
        overlap_t=overlap_t,
        cur_len=cur_t_len,
        temporal_rigidity=temporal_rigidity,
        suno_audio_anchor=suno_audio_anchor,
        master_lat_stats=master_lat_stats,
        viseme_env_win=viseme_env_win,
        mocap_deltas_win=mocap_deltas_win,
        motion_physics_mode=motion_physics_mode,
        motion_strength=motion_strength,
        anatomical_zones=anatomical_zones,
        win_start_latent=f0_win,
        win_mid_latent=f_mid_win,
        win_end_latent=f_end_win,
        allow_camera_movement=allow_camera_movement,
    )
    try:
        from .engine_ez_01_cinematrix_canvas_ingest import enforce_cinematrix_thermal_shield
        enforce_cinematrix_thermal_shield(f'MiniMax-Win{win_idx + 1}/{total_wins}-Start', force_inter_stage_pause=True)
    except Exception:
        enforce_cinematrix_thermal_shield = None
    base_cb = latent_preview.prepare_callback(active_m, steps)

    def _ez_av_callback(step, x0, x, total_steps):
        if callable(enforce_cinematrix_thermal_shield):
            enforce_cinematrix_thermal_shield(
                f'MiniMax-Win{win_idx + 1}/{total_wins}-Step{step + 1}/{total_steps}',
                step_idx=int(step),
                total_steps=int(total_steps),
            )
        if callable(base_cb):
            try:
                v0 = _unpack_av_tensors(x0)[0]
                frame_4d = v0[:, :, v0.shape[2] // 2, :, :] if isinstance(v0, torch.Tensor) and v0.ndim == 5 else v0
                base_cb(step, frame_4d, x, total_steps)
            except Exception:
                pass
        if step == total_steps - 1 or (step > 0 and step % max(2, total_steps // 2) == 0):
            _emit_minipyav_live_video_preview(x0, win_idx, total_wins, step + 1, total_steps)
    prev_fp16_acc = getattr(torch.backends.cuda.matmul, 'allow_fp16_accumulation', False) if hasattr(torch.backends, 'cuda') and hasattr(torch.backends.cuda, 'matmul') else False
    raw_sample_fn = getattr(comfy.sample.sample, '_multigpu_original', getattr(comfy.sample.sample, '__wrapped__', comfy.sample.sample))
    try:
        if hasattr(torch.backends, 'cuda') and hasattr(torch.backends.cuda, 'matmul'):
            torch.backends.cuda.matmul.allow_fp16_accumulation = True
        out_w = raw_sample_fn(active_m, noise_w, steps, cfg, sampler_name, scheduler, positive, negative, latent_w, denoise=denoise, disable_noise=False, start_step=None, last_step=None, force_full_denoise=True, noise_mask=noise_mask_w, callback=_ez_av_callback, disable_pbar=disable_pbar, seed=seed)
    finally:
        if hasattr(torch.backends, 'cuda') and hasattr(torch.backends.cuda, 'matmul'):
            torch.backends.cuda.matmul.allow_fp16_accumulation = prev_fp16_acc
    return _offload_completed_chunk_to_cpu(out_w)

def execute_temporal_chunked_sampling(model, positive, negative, latent_dict: dict, seed: int, steps: int, cfg: float, sampler_name: str, scheduler: str, denoise: float, enable_latent_2x_upscale: bool, previous_latent_opt=None, tier_profile: dict=None, anatomy_cfg: dict=None):
    if hasattr(comfy.model_management, 'throw_exception_if_processing_interrupted'):
        comfy.model_management.throw_exception_if_processing_interrupted()
    _install_sage_attention_oom_guard(model=model)
    prof = dict(tier_profile) if isinstance(tier_profile, dict) else dict(latent_dict.get('hardware_tier_profile', {})) if isinstance(latent_dict.get('hardware_tier_profile'), dict) else {}
    anat = dict(anatomy_cfg) if isinstance(anatomy_cfg, dict) else {}
    is_auto_dock = str(anat.get('autopilot_mode', 'auto')).lower().startswith('auto')
    outlier_suppression = 0.35 if is_auto_dock else max(0.28, float(anat.get('latent_outlier_suppression', 0.35)))
    temporal_rigidity = float(anat.get('temporal_identity_rigidity', 0.88))
    is_licensed = bool(prof.get('is_licensed', True))
    m_opts = getattr(model, 'model_options', {}) if hasattr(model, 'model_options') and isinstance(getattr(model, 'model_options'), dict) else {}
    has_turbo_lora = bool(m_opts.get('has_turbo_lora', False)) or bool(m_opts.get('unet_has_baked_turbo', False))
    unet_baked_turbo = bool(m_opts.get('unet_has_baked_turbo', False))
    cum_lora_gain = float(m_opts.get('cumulative_lora_vis_gain', 0.0) or 0.0)
    is_turbo_run = has_turbo_lora or int(steps) <= 12
    if has_turbo_lora and float(cfg) >= 2.2:
        cfg = 1.05
    elif unet_baked_turbo and cum_lora_gain >= 0.45 and float(cfg) > 1.10:
        cfg = 1.05
    elif (not has_turbo_lora) and ('has_turbo_lora' in m_opts) and int(steps) <= 12 and float(cfg) <= 1.15:
        cfg = 2.5
        steps = max(int(steps), 14)
    if float(denoise) < 0.999:
        denoise = 1.0
    if is_turbo_run and abs(float(m_opts.get('shift_video', 5.0)) - 11.0) < 0.05 and str(m_opts.get('ez_video_arch', 'minimax_h3')) == 'minimax_h3':
        try:
            from comfy_extras.nodes_minimax_h3 import MiniMaxH3SigmaShift
            s_out = MiniMaxH3SigmaShift.execute(model, 5.0, 3.0)
            model = s_out[0] if isinstance(s_out, (tuple, list)) or hasattr(s_out, '__getitem__') else s_out
        except Exception:
            pass
    upscale_chunk_t = max(4, int(prof.get('upscale_chunk_t', 8) or 8))
    aggressive_purge = bool(prof.get('aggressive_vram_purge', not is_licensed))
    inter_window_purge = bool(prof.get('inter_window_vram_purge', False))
    cont_ctx = dict(latent_dict.get('ez_continuation_ctx')) if isinstance(latent_dict.get('ez_continuation_ctx'), dict) else {}
    cont_ctx['active_cfg'] = float(cfg)
    active_motion_mode = str(latent_dict.get('motion_physics_mode', cont_ctx.get('motion_physics_mode', 'natural_organic')) or 'natural_organic')
    active_motion_strength = float(latent_dict.get('motion_transfer_strength', cont_ctx.get('motion_transfer_strength', 0.65)) or 0.65)
    full_mocap_deltas = latent_dict.get('mocap_latent_deltas') if isinstance(latent_dict.get('mocap_latent_deltas'), torch.Tensor) else cont_ctx.get('mocap_latent_deltas')
    active_anat_zones = latent_dict.get('anatomical_latent_zones') if isinstance(latent_dict.get('anatomical_latent_zones'), dict) else cont_ctx.get('anatomical_latent_zones')
    if isinstance(active_anat_zones, dict) and isinstance(anat, dict) and len(anat) > 0:
        active_anat_zones = dict(active_anat_zones)
        active_anat_zones['dock_cfg'] = dict(anat)
    if aggressive_purge or not bool(prof.get('persistent_vram_weights', False)):
        if hasattr(comfy.model_management, 'unload_all_models'):
            comfy.model_management.unload_all_models()
        comfy.model_management.soft_empty_cache()
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    raw_samples = _offload_completed_chunk_to_cpu(latent_dict['samples'])
    base_noise_mask = latent_dict.get('noise_mask', None)
    is_h3_arch = str(m_opts.get('ez_video_arch', cont_ctx.get('video_arch', 'minimax_h3'))).lower() == 'minimax_h3'
    if is_h3_arch:
        try:
            from comfy.nested_tensor import NestedTensor
            u_raw = _unpack_av_tensors(raw_samples)
            if len(u_raw) == 1 and isinstance(u_raw[0], torch.Tensor) and u_raw[0].ndim == 5:
                v_5d = u_raw[0]
                v_px = _h3_tokens_to_frames(int(v_5d.shape[2]))
                a_t = _h3_frames_to_audio_steps(v_px)
                a_4d = torch.zeros((int(v_5d.shape[0]), 32, 2, a_t), dtype=v_5d.dtype, device=v_5d.device)
                raw_samples = NestedTensor([v_5d, a_4d])
                if isinstance(base_noise_mask, torch.Tensor):
                    am_4d = torch.ones((int(v_5d.shape[0]), 1, 1, a_t), dtype=base_noise_mask.dtype, device=base_noise_mask.device)
                    base_noise_mask = NestedTensor([base_noise_mask, am_4d])
        except Exception:
            pass
    fixed_samples = comfy.sample.fix_empty_latent_channels(model, raw_samples)
    batch_inds = latent_dict.get('batch_index', None)
    disable_pbar = not comfy.utils.PROGRESS_BAR_ENABLED
    raw_overlap = int(latent_dict.get('overlap_frames', 8))
    overlap_t = (2 if raw_overlap < 14 else 7) if is_h3_arch else max(1, min(3, max(1, (raw_overlap + 3) // 4)))
    primary_vid_t = _unpack_av_tensors(fixed_samples)[0]
    total_t = int(primary_vid_t.shape[2]) if isinstance(primary_vid_t, torch.Tensor) and primary_vid_t.ndim == 5 else 1
    num_macro_segments = max(1, int(cont_ctx.get('num_macro_segments', 1) or 1))
    seg_pixel_frames = int(cont_ctx.get('macro_segment_frames', latent_dict.get('total_frames', 243 if is_h3_arch else 241)) or (243 if is_h3_arch else 241))
    if float(cfg) > 1.05 and cont_ctx.get('video_clip') is not None and str(cont_ctx.get('negative_prompt', '') or '').strip():
        try:
            if isinstance(negative, list) and len(negative) > 0 and isinstance(negative[0][0], torch.Tensor) and (float(negative[0][0].abs().max().item()) < 1e-06):
                v_clip = cont_ctx['video_clip']
                neg_str = str(cont_ctx['negative_prompt']).strip()
                raw_neg = v_clip.encode_from_tokens_scheduled(v_clip.tokenize(neg_str))
                pos_meta = dict(positive[0][1]) if positive and len(positive[0]) > 1 and isinstance(positive[0][1], dict) else {}
                negative = [[item[0].detach().cpu(), {**pos_meta, **(dict(item[1]) if len(item) > 1 and isinstance(item[1], dict) else {})}] for item in raw_neg]
        except Exception:
            pass
    def _inject_suno_audio_latent_conditioning(av_lat_obj, mask_obj, seg_i: int=0, n_wins: int=1, eff_ov_t: int=1):
        latent_dict.pop('_ez_active_suno_audio_latent', None)
        latent_dict.pop('_ez_active_viseme_envelope', None)
        latent_dict.pop('_ez_active_mocap_deltas', None)
        t_list = _unpack_av_tensors(av_lat_obj)
        vid_t = t_list[0] if len(t_list) > 0 and isinstance(t_list[0], torch.Tensor) else None
        if isinstance(full_mocap_deltas, torch.Tensor) and full_mocap_deltas.ndim == 5 and isinstance(vid_t, torch.Tensor) and vid_t.ndim == 5 and vid_t.shape[2] >= 2:
            try:
                import torch.nn.functional as F
                req_dt = max(1, int(vid_t.shape[2]) - 1)
                tot_dt = int(full_mocap_deltas.shape[2])
                if n_wins <= 1 or tot_dt <= req_dt:
                    mc_slice = full_mocap_deltas
                else:
                    dt_stride = max(1, (tot_dt - req_dt) // max(1, n_wins - 1))
                    d0 = min(max(0, seg_i * dt_stride), max(0, tot_dt - req_dt))
                    mc_slice = full_mocap_deltas[:, :, d0:d0 + req_dt, :, :]
                if mc_slice.shape[2:] != (req_dt, int(vid_t.shape[3]), int(vid_t.shape[4])):
                    mc_slice = F.interpolate(mc_slice.float(), size=(req_dt, int(vid_t.shape[3]), int(vid_t.shape[4])), mode='trilinear', align_corners=False)
                latent_dict['_ez_active_mocap_deltas'] = mc_slice.detach().cpu().float()
            except Exception:
                pass
        s_cfg = latent_dict.get('suno_music_studio') or cont_ctx.get('suno_music_studio')
        a_vae = latent_dict.get('audio_vae_obj') or cont_ctx.get('audio_vae')
        if not isinstance(s_cfg, dict) or not s_cfg.get('active') or a_vae is None or not _is_nested_av_latent(av_lat_obj):
            return (av_lat_obj, mask_obj)
        if len(t_list) < 2 or not isinstance(t_list[0], torch.Tensor) or not isinstance(t_list[1], torch.Tensor):
            return (av_lat_obj, mask_obj)
        wave_32k = s_cfg.get('waveform_32k')
        if not isinstance(wave_32k, torch.Tensor) or wave_32k.numel() < 512:
            return (av_lat_obj, mask_obj)
        try:
            import torch.nn.functional as F
            vid_t = t_list[0]
            aud_tmpl = t_list[1]
            w_3d = wave_32k.detach().cpu().float()
            if w_3d.ndim == 2:
                w_3d = w_3d.unsqueeze(0)
            n_tot = int(w_3d.shape[-1])
            sr_32k = int(s_cfg.get('sample_rate_32k', 32000) or 32000)
            fps_val = max(1.0, float(latent_dict.get('frame_rate', cont_ctx.get('frame_rate', 24.0)) or 24.0))
            if vid_t.ndim == 5 and int(vid_t.shape[1]) == 24:
                win_px_frames = max(5, int(seg_pixel_frames) if int(seg_pixel_frames) >= 22 else _h3_tokens_to_frames(int(vid_t.shape[2])))
                ov_px_stride = 1
            else:
                win_px_frames = max(5, (int(vid_t.shape[2]) - 1) * 4 + 1) if vid_t.ndim == 5 else int(seg_pixel_frames)
                ov_px_stride = max(4, (max(1, int(eff_ov_t)) - 1) * 4 + 1) if int(eff_ov_t) > 1 else 4
            stride_px_frames = max(1, win_px_frames - ov_px_stride)
            start_sec = float(seg_i * stride_px_frames) / fps_val
            win_dur_sec = float(win_px_frames) / fps_val
            vis_4d = s_cfg.get('viseme_envelope_4d')
            if isinstance(vis_4d, torch.Tensor) and vis_4d.ndim == 2 and vis_4d.shape[0] >= 4 and vid_t.ndim == 5:
                v_f0 = max(0, int(round(start_sec * fps_val)))
                v_f1 = v_f0 + win_px_frames
                tot_vf = int(vis_4d.shape[1])
                if v_f0 >= tot_vf:
                    v_f0 = max(0, tot_vf - win_px_frames)
                    v_f1 = tot_vf
                v_seg = vis_4d[:4, v_f0:min(tot_vf, v_f1)].detach().cpu().float()
                if v_seg.shape[1] >= 2:
                    v_lat_env = F.interpolate(v_seg.unsqueeze(0), size=int(vid_t.shape[2]), mode='linear', align_corners=False).squeeze(0)
                    latent_dict['_ez_active_viseme_envelope'] = v_lat_env.detach().cpu()
            s0 = max(0, int(round(start_sec * sr_32k)))
            req_samples = max(1600, int(round(win_dur_sec * sr_32k)))
            s1 = s0 + req_samples
            if s0 >= n_tot:
                s0 = max(0, n_tot - req_samples)
                s1 = s0 + req_samples
            seg_w = w_3d[:, :, s0:min(n_tot, s1)].contiguous()
            if int(seg_w.shape[-1]) < req_samples:
                seg_w = F.pad(seg_w, (0, req_samples - int(seg_w.shape[-1])))
            enc_a = None
            for cand_in in ({'waveform': seg_w, 'sample_rate': int(s_cfg.get('sample_rate_32k', 32000) or 32000)}, seg_w.movedim(1, -1).unsqueeze(1).contiguous(), seg_w.movedim(1, -1).contiguous(), seg_w):
                try:
                    raw_e = a_vae.encode(cand_in)
                    if isinstance(raw_e, dict) and 'samples' in raw_e:
                        raw_e = raw_e['samples']
                    if isinstance(raw_e, torch.Tensor) and raw_e.numel() > 16:
                        enc_a = raw_e.detach().cpu().float()
                        break
                except Exception:
                    continue
            fsm = getattr(a_vae, 'first_stage_model', None)
            if enc_a is None and fsm is not None and hasattr(fsm, 'encode'):
                try:
                    if hasattr(a_vae, 'patcher') and a_vae.patcher is not None:
                        comfy.model_management.load_model_gpu(a_vae.patcher)
                    v_dev = getattr(a_vae, 'device', comfy.model_management.get_torch_device())
                    v_dt = getattr(a_vae, 'vae_dtype', torch.float32)
                    for fsm_in in (seg_w.movedim(1, -1).contiguous().to(device=v_dev, dtype=v_dt), seg_w.to(device=v_dev, dtype=v_dt)):
                        try:
                            with torch.no_grad():
                                r_out = fsm.encode(fsm_in)
                            if hasattr(r_out, 'mode') and callable(r_out.mode):
                                r_out = r_out.mode()
                            elif hasattr(r_out, 'sample') and callable(r_out.sample):
                                r_out = r_out.sample()
                            elif isinstance(r_out, (tuple, list)) and len(r_out) > 0:
                                r_out = r_out[0]
                            elif isinstance(r_out, dict):
                                r_out = r_out.get('samples', r_out.get('latent', None))
                            if isinstance(r_out, torch.Tensor) and r_out.numel() > 16:
                                if hasattr(a_vae, 'process_latent_in') and callable(a_vae.process_latent_in):
                                    try:
                                        r_out = a_vae.process_latent_in(r_out)
                                    except Exception:
                                        pass
                                enc_a = r_out.detach().cpu().float()
                                break
                        except Exception:
                            continue
                except Exception:
                    pass
            if enc_a is None or aud_tmpl.ndim not in (3, 4):
                return (av_lat_obj, mask_obj)
            if aud_tmpl.ndim == 3:
                while enc_a.ndim > 3 and enc_a.shape[0] == 1:
                    enc_a = enc_a.squeeze(0)
                while enc_a.ndim < 3:
                    enc_a = enc_a.unsqueeze(0)
                if enc_a.shape[1] != aud_tmpl.shape[1] and enc_a.shape[2] == aud_tmpl.shape[1]:
                    enc_a = enc_a.transpose(1, 2).contiguous()
                if enc_a.shape[1] == aud_tmpl.shape[1] and enc_a.shape[2] != aud_tmpl.shape[2]:
                    enc_a = F.interpolate(enc_a, size=int(aud_tmpl.shape[2]), mode='linear', align_corners=False)
                elif enc_a.shape[2] == aud_tmpl.shape[2] and enc_a.shape[1] != aud_tmpl.shape[1]:
                    enc_a = F.interpolate(enc_a.transpose(1, 2), size=int(aud_tmpl.shape[1]), mode='linear', align_corners=False).transpose(1, 2).contiguous()
                elif enc_a.shape[1:] != aud_tmpl.shape[1:]:
                    enc_a = F.interpolate(enc_a.unsqueeze(1), size=(int(aud_tmpl.shape[1]), int(aud_tmpl.shape[2])), mode='bilinear', align_corners=False).squeeze(1)
            else:
                while enc_a.ndim > 4 and enc_a.shape[0] == 1:
                    enc_a = enc_a.squeeze(0)
                if enc_a.ndim == 2:
                    enc_a = enc_a.unsqueeze(0)
                if enc_a.ndim == 3:
                    if enc_a.shape[1] != aud_tmpl.shape[1] and enc_a.shape[2] == aud_tmpl.shape[1]:
                        enc_a = enc_a.transpose(1, 2).contiguous()
                    if aud_tmpl.shape[2] == 1:
                        enc_a = enc_a.unsqueeze(2)
                    elif aud_tmpl.shape[3] == 1:
                        enc_a = enc_a.unsqueeze(3)
                    else:
                        enc_a = enc_a.unsqueeze(2)
                while enc_a.ndim < 4:
                    enc_a = enc_a.unsqueeze(0)
                if enc_a.shape[1] != aud_tmpl.shape[1] and enc_a.shape[-1] == aud_tmpl.shape[1]:
                    enc_a = enc_a.movedim(-1, 1).contiguous()
                if enc_a.shape[2] == aud_tmpl.shape[3] and enc_a.shape[3] == aud_tmpl.shape[2] and (aud_tmpl.shape[2] != aud_tmpl.shape[3]):
                    enc_a = enc_a.transpose(2, 3).contiguous()
                if enc_a.shape[1] > aud_tmpl.shape[1]:
                    enc_a = enc_a[:, :aud_tmpl.shape[1]]
                elif enc_a.shape[1] < aud_tmpl.shape[1]:
                    enc_a = F.pad(enc_a, (0, 0, 0, 0, 0, int(aud_tmpl.shape[1] - enc_a.shape[1])))
                if enc_a.shape[2:] != aud_tmpl.shape[2:]:
                    if aud_tmpl.shape[2] == 1 and enc_a.shape[2] == 1:
                        enc_a = F.interpolate(enc_a.squeeze(2), size=int(aud_tmpl.shape[3]), mode='linear', align_corners=False).unsqueeze(2)
                    elif aud_tmpl.shape[3] == 1 and enc_a.shape[3] == 1:
                        enc_a = F.interpolate(enc_a.squeeze(3), size=int(aud_tmpl.shape[2]), mode='linear', align_corners=False).unsqueeze(3)
                    else:
                        enc_a = F.interpolate(enc_a, size=(int(aud_tmpl.shape[2]), int(aud_tmpl.shape[3])), mode='bilinear', align_corners=False)
            enc_a = torch.nan_to_num(enc_a, nan=0.0, posinf=4.0, neginf=-4.0)
            a_std = float(enc_a.std().item())
            if a_std > 4.0:
                enc_a = enc_a * (1.25 / a_std)
            t_list[1] = enc_a.to(device=aud_tmpl.device, dtype=aud_tmpl.dtype)
            latent_dict['_ez_active_suno_audio_latent'] = enc_a.detach().cpu().clone()
            av_lat_obj = _repack_av_tensors(av_lat_obj, t_list)
            m_list = _unpack_av_tensors(mask_obj) if mask_obj is not None else []
            if len(m_list) > 0 and isinstance(m_list[0], torch.Tensor) and m_list[0].ndim == 5 and (m_list[0].shape[2] == vid_t.shape[2]):
                vm = m_list[0].clone().detach().cpu().float()
            else:
                vm = torch.ones((1, 1, int(vid_t.shape[2]), 1, 1), dtype=torch.float32, device='cpu')
            a_time_dim = _resolve_audio_time_dim(aud_tmpl)
            am_shape = [1] * int(aud_tmpl.ndim)
            am_shape[a_time_dim] = int(aud_tmpl.shape[a_time_dim])
            am = torch.zeros(am_shape, dtype=torch.float32, device='cpu')
            mask_obj = _repack_av_tensors(av_lat_obj, [vm, am])
            print(f'[EZ-SAMPLER-07] 🎙️ Kodade in Suno 32kHz vokal-latent + 4D Viseme Envelope i Joint AV DiT (Fönster {seg_i + 1}/{n_wins}, t={start_sec:.2f}s..{start_sec + win_dur_sec:.2f}s, shape={tuple(enc_a.shape)}, fysik={active_motion_mode})!')
        except Exception as aud_err:
            print(f'[EZ-SAMPLER-07] Suno audio-latent conditioning notice: {aud_err}')
        return (av_lat_obj, mask_obj)

    master_lat_stats = {}
    try:
        kf_init = None
        if isinstance(positive, list) and len(positive) > 0 and isinstance(positive[0], (list, tuple)) and len(positive[0]) > 1 and isinstance(positive[0][1], dict):
            raw_kfs0 = positive[0][1].get('minimax_keyframes')
            if isinstance(raw_kfs0, (list, tuple)) and len(raw_kfs0) > 0 and isinstance(raw_kfs0[0], dict) and isinstance(raw_kfs0[0].get('latent'), torch.Tensor):
                cand_kf = raw_kfs0[0]['latent'].float().detach().cpu()
                if cand_kf.ndim == 5 and float(cand_kf.abs().max().item()) > 1e-04:
                    kf_init = cand_kf[:, :, 0:1, :, :]
        if kf_init is None and isinstance(primary_vid_t, torch.Tensor) and primary_vid_t.ndim == 5 and primary_vid_t.shape[2] >= 1:
            cand_p = primary_vid_t[:, :, 0:1, :, :].float().detach().cpu()
            if float(cand_p.abs().max().item()) > 1e-04:
                kf_init = cand_p
        if kf_init is not None:
            master_lat_stats['mean'] = kf_init.mean(dim=(2, 3, 4), keepdim=True)
            master_lat_stats['std'] = torch.clamp(kf_init.std(dim=(2, 3, 4), keepdim=True), min=1e-04)
            master_lat_stats['master_kf_latent'] = kf_init
            master_lat_stats['prism_spec'] = _prism_extract_latent_channel_spectrum(kf_init)
        master_lat_stats['allow_camera_movement'] = bool((cont_ctx or {}).get('allow_camera_movement', latent_dict.get('allow_camera_movement', False)))
    except Exception:
        pass
    allow_cam_global = bool((cont_ctx or {}).get('allow_camera_movement', latent_dict.get('allow_camera_movement', False)))
    macro_segment_latents = []
    if not isinstance(primary_vid_t, torch.Tensor) or primary_vid_t.ndim != 5 or (num_macro_segments <= 1 and total_t <= (72 if is_h3_arch else 65)):
        (fixed_samples, base_noise_mask) = _inject_suno_audio_latent_conditioning(fixed_samples, base_noise_mask, seg_i=0, n_wins=1, eff_ov_t=overlap_t)
        noise = comfy.sample.prepare_noise(fixed_samples, seed, batch_inds)
        sampled_cpu = _sample_single_temporal_window(
            model,
            noise,
            steps,
            cfg,
            sampler_name,
            scheduler,
            positive,
            negative,
            fixed_samples,
            denoise,
            base_noise_mask,
            disable_pbar,
            seed,
            win_idx=0,
            total_wins=1,
            overlap_t=overlap_t,
            temporal_rigidity=temporal_rigidity,
            suno_audio_anchor=latent_dict.get('_ez_active_suno_audio_latent'),
            master_lat_stats=master_lat_stats,
            viseme_env_win=latent_dict.get('_ez_active_viseme_envelope'),
            mocap_deltas_win=latent_dict.get('_ez_active_mocap_deltas'),
            motion_physics_mode=active_motion_mode,
            motion_strength=active_motion_strength,
            anatomical_zones=active_anat_zones,
            allow_camera_movement=allow_cam_global,
        )
        sampled_cpu = _stabilize_3d_video_latent_outliers(
            sampled_cpu,
            outlier_strength=outlier_suppression,
            motion_physics_mode=active_motion_mode,
            motion_strength=active_motion_strength,
            anatomical_zones=active_anat_zones,
        )
        _emit_minipyav_live_video_preview(sampled_cpu, 0, 1, steps, steps)
    else:
        total_wins = max(2, num_macro_segments)
        prev_seg_cpu = None
        stitched_accum_cpu = None
        master_kf = cont_ctx.get('first_frame_in') if cont_ctx else None
        stale_cache_detected = False
        if isinstance(cont_ctx, dict):
            try:
                from .engine_ez_06_cinematrix_video_director import _extract_chronological_shot_prompts, _scrub_sfx_vocal_triggers, _scrub_unrequested_genital_hallucinations
                old_acts = list(cont_ctx.get('act_prompts') or [])
                raw_src = str(cont_ctx.get('raw_timeline_prompt') or cont_ctx.get('timeline_prompt') or '').strip()
                is_ref_mode = str(cont_ctx.get('production_mode', '')).startswith('REF2VA')
                s_cfg_check = latent_dict.get('suno_music_studio') or cont_ctx.get('suno_music_studio')
                if isinstance(s_cfg_check, dict) and bool(s_cfg_check.get('active')):
                    master_lat_stats['suno_active'] = True
                is_vocal_run = (
                    bool(cont_ctx.get('is_vocal_scene'))
                    or bool(latent_dict.get('is_vocal_scene'))
                    or str(active_motion_mode).startswith('expressive_vocal')
                    or (isinstance(s_cfg_check, dict) and bool(s_cfg_check.get('active')) and bool(s_cfg_check.get('wants_lipsync', True)))
                )
                allow_cam_move_run = bool(cont_ctx.get('allow_camera_movement', latent_dict.get('allow_camera_movement', False)))
                master_lat_stats['allow_camera_movement'] = allow_cam_move_run
                allow_cam_global = allow_cam_move_run
                master_lat_stats['has_explicit_fl2va_end'] = bool(cont_ctx.get('has_explicit_fl2va_end', False))
                is_nsfw_run = bool(cont_ctx.get('is_nsfw', True))
                rating_tier_run = str(cont_ctx.get('rating_tier', 'uncensored_action' if is_nsfw_run else 'sfw') or '').strip().lower()
                user_scene_run = str(cont_ctx.get('user_scene_input') or raw_src).strip()
                already_sanitized = (str(cont_ctx.get('sanitizer_version', '')) == 'v19_env_beat_multiband_lock') and bool(old_acts)
                cam_dirty_clause = '' if allow_cam_move_run else r'dolly-in|push-in|zoom-in|85mm\s+portrait|'
                nsfw_dirty_clause = '' if is_nsfw_run else r'vulva|vagina|labia|pussy|clit|penis|cock|dick|loincloth\s+shifts|loincloth\s+parts|'
                dirty_pat = rf'(?i)(?<!no\s)(?<!zero\s)(?<!zero\scamera\s)(?<!no\scamera\s)(?<!without\s)\b(?:{cam_dirty_clause}{nsfw_dirty_clause}hitting\s+the\s+ground|crashing\s+down|down\s+on\s+the\s+ground|away\s+from\s+her\s+abdomen|as\s+if\s+it\s+w(?:h)?ere\s+a\s+cross|above\s+her\s+head|over\s+her\s+head|at\s+6\.5s|at\s+13\.5s|Act\s*1\s*\(0\.0s|maintaining\s+her\s+exact\s+initial\s+stance)\b'
                has_dirty_act = (not already_sanitized) and any((re.search(dirty_pat, str(a)) for a in old_acts))
                if (not old_acts or not already_sanitized or has_dirty_act) and raw_src:
                    if rating_tier_run == 'sfw':
                        src_for_acts = _scrub_unrequested_genital_hallucinations(raw_src, '')
                    elif rating_tier_run == 'nsfw_explicit':
                        src_for_acts = raw_src
                    else:
                        src_for_acts = _scrub_unrequested_genital_hallucinations(raw_src, user_scene_run)
                    if not is_vocal_run:
                        src_for_acts = _scrub_sfx_vocal_triggers(src_for_acts)
                    fresh_acts = _extract_chronological_shot_prompts(src_for_acts, num_windows=total_wins, is_ref2va=is_ref_mode, is_vocal_override=is_vocal_run, user_scene_input=user_scene_run, allow_camera_movement=allow_cam_move_run)
                    if fresh_acts:
                        stale_cache_detected = True
                        cont_ctx['act_prompts'] = fresh_acts
                        cont_ctx['sanitizer_version'] = 'v19_env_beat_multiband_lock'
                        cont_ctx['pre_encoded_clip_cache'] = {}
            except Exception:
                pass
        for seg_idx in range(total_wins):
            if hasattr(comfy.model_management, 'throw_exception_if_processing_interrupted'):
                comfy.model_management.throw_exception_if_processing_interrupted()
            eff_win_ov = overlap_t
            if seg_idx == 0:
                if stale_cache_detected and master_kf is not None:
                    (h3_p0, h3_n0, h3_l0, h3_m0) = _rebuild_window_h3_conditioning(cont_ctx, master_kf, seg_pixel_frames, 0, total_wins)
                    if h3_p0 is not None and h3_n0 is not None and (h3_l0 is not None):
                        positive = h3_p0
                        negative = h3_n0
                        fixed_samples = comfy.sample.fix_empty_latent_channels(model, h3_l0)
                        base_noise_mask = h3_m0
                win_pos = positive
                win_neg = negative
                win_lat = fixed_samples
                win_mask = base_noise_mask
            else:
                eff_win_ov = max(1, overlap_t)
                if isinstance(cont_ctx.get('anatomical_latent_zones'), dict):
                    active_anat_zones = cont_ctx['anatomical_latent_zones']
                allow_cam_win = bool((cont_ctx or {}).get('allow_camera_movement', latent_dict.get('allow_camera_movement', False)))
                pro_rt = cont_ctx.get('pro_speaker_routing') if isinstance(cont_ctx.get('pro_speaker_routing'), dict) else {}
                has_valid_2p = bool(pro_rt.get('active', False)) and bool(pro_rt.get('has_second_person_ref', False)) and isinstance(cont_ctx.get('r2_in'), torch.Tensor)
                pro_cuts = pro_rt.get('scenecut_window_indices') if (has_valid_2p and isinstance(pro_rt.get('scenecut_window_indices'), list)) else []
                pro_sp_ids = pro_rt.get('window_speaker_ids') if (has_valid_2p and isinstance(pro_rt.get('window_speaker_ids'), list)) else []
                is_pro_scenecut_win = int(seg_idx) in pro_cuts
                cur_win_sp = int(pro_sp_ids[int(seg_idx)]) if 0 <= int(seg_idx) < len(pro_sp_ids) else 0
                eff_master_for_win = cont_ctx.get('r2_in') if (has_valid_2p and cur_win_sp == 1) else master_kf
                pro_seam_flag = bool((cont_ctx or {}).get('pro_focus_seam_active', latent_dict.get('pro_focus_seam_active', True)))
                if is_pro_scenecut_win and isinstance(eff_master_for_win, torch.Tensor):
                    handoff_img = eff_master_for_win
                    if isinstance(active_anat_zones, dict):
                        active_anat_zones['_ez_handoff_reanchored'] = True
                        active_anat_zones['_ez_handoff_trim_px'] = 0
                else:
                    try:
                        from .engine_ez_01_cinematrix_canvas_ingest import enforce_cinematrix_thermal_shield
                        sh_state = enforce_cinematrix_thermal_shield(f'MiniMax-Handoff-Decode-Win{seg_idx + 1}', tier_profile=prof, force_inter_stage_pause=True)
                        rt_ov = sh_state.get('runtime_overrides') if isinstance(sh_state, dict) and isinstance(sh_state.get('runtime_overrides'), dict) else {}
                        if rt_ov.get('tile_size'):
                            cont_ctx['tile_size'] = int(rt_ov['tile_size'])
                        if rt_ov.get('inter_window_vram_purge') is not None:
                            inter_window_purge = bool(rt_ov['inter_window_vram_purge'])
                        if rt_ov.get('upscale_chunk_t'):
                            upscale_chunk_t = max(2, int(rt_ov['upscale_chunk_t']))
                    except Exception:
                        pass
                    handoff_img = _decode_handoff_frame_from_accum(prev_seg_cpu, cont_ctx.get('video_vae'), overlap_t=eff_win_ov, tile_sz=int(cont_ctx.get('tile_size', 512) or 512), master_first_frame=eff_master_for_win, seg_pixel_frames=seg_pixel_frames, anatomical_zones=active_anat_zones, allow_camera_movement=allow_cam_win, pro_focus_seam_active=pro_seam_flag)
                was_reanchored = bool(is_pro_scenecut_win) or (bool(active_anat_zones.get('_ez_handoff_reanchored', False)) if isinstance(active_anat_zones, dict) else False)
                (h3_pos, h3_neg, h3_lat, h3_mask) = _rebuild_window_h3_conditioning(cont_ctx, handoff_img if handoff_img is not None else eff_master_for_win, seg_pixel_frames, seg_idx, total_wins)
                if isinstance(cont_ctx.get('anatomical_latent_zones'), dict):
                    active_anat_zones = cont_ctx['anatomical_latent_zones']
                    if is_pro_scenecut_win:
                        active_anat_zones['_ez_handoff_reanchored'] = True
                if h3_pos is not None and h3_neg is not None and (h3_lat is not None):
                    win_pos = h3_pos
                    win_neg = h3_neg
                    win_lat = comfy.sample.fix_empty_latent_channels(model, h3_lat)
                    win_mask = h3_mask
                    win_vid_0 = _unpack_av_tensors(win_lat)[0]
                    seg_v_t = int(win_vid_0.shape[2]) if isinstance(win_vid_0, torch.Tensor) and win_vid_0.ndim == 5 else total_t
                    is_h3_win = isinstance(win_vid_0, torch.Tensor) and win_vid_0.ndim == 5 and int(win_vid_0.shape[1]) == 24
                    if not was_reanchored:
                        (win_pos, win_neg) = _inject_h3_native_latent_tail_keyframes(win_pos, win_neg, prev_seg_cpu, 1, master_lat_stats=master_lat_stats, force_tail_replace=False)
                        if not is_h3_win:
                            win_lat = _inject_overlap_into_av_window(win_lat, prev_seg_cpu, eff_win_ov, seg_v_t)
                            win_mask = _build_av_overlap_noise_mask(win_lat, win_mask, eff_win_ov, seg_v_t)
                else:
                    win_pos = positive
                    win_neg = negative
                    win_lat = fixed_samples
                    win_mask = base_noise_mask
                    seg_v_t = int(_unpack_av_tensors(win_lat)[0].shape[2]) if isinstance(_unpack_av_tensors(win_lat)[0], torch.Tensor) and _unpack_av_tensors(win_lat)[0].ndim == 5 else total_t
                    if not was_reanchored:
                        (win_pos, win_neg) = _inject_h3_native_latent_tail_keyframes(win_pos, win_neg, prev_seg_cpu, 1, master_lat_stats=master_lat_stats, force_tail_replace=False)
                        win_lat = _inject_overlap_into_av_window(win_lat, prev_seg_cpu, eff_win_ov, seg_v_t)
                    win_pos = _slice_conditioning_for_window(win_pos, 1, seg_v_t + 1, seg_v_t, accumulated_cpu=prev_seg_cpu, overlap_t=eff_win_ov, is_positive=True)
                    win_neg = _slice_conditioning_for_window(win_neg, 1, seg_v_t + 1, seg_v_t, accumulated_cpu=prev_seg_cpu, overlap_t=eff_win_ov, is_positive=False)
                    if not was_reanchored:
                        win_mask = _build_av_overlap_noise_mask(win_lat, win_mask, eff_win_ov, seg_v_t)
            (win_lat, win_mask) = _inject_suno_audio_latent_conditioning(win_lat, win_mask, seg_i=seg_idx, n_wins=total_wins, eff_ov_t=eff_win_ov)
            win_seed = int(seed) + seg_idx
            win_noise = comfy.sample.prepare_noise(win_lat, win_seed, batch_inds)
            sampled_win_cpu = _sample_single_temporal_window(
                model,
                win_noise,
                steps,
                cfg,
                sampler_name,
                scheduler,
                win_pos,
                win_neg,
                win_lat,
                denoise,
                win_mask,
                disable_pbar,
                win_seed,
                win_idx=seg_idx,
                total_wins=total_wins,
                accum_so_far=prev_seg_cpu if not (seg_idx > 0 and isinstance(active_anat_zones, dict) and active_anat_zones.get('_ez_handoff_reanchored', False)) else None,
                overlap_t=eff_win_ov,
                temporal_rigidity=temporal_rigidity,
                suno_audio_anchor=latent_dict.get('_ez_active_suno_audio_latent'),
                master_lat_stats=master_lat_stats,
                viseme_env_win=latent_dict.get('_ez_active_viseme_envelope'),
                mocap_deltas_win=latent_dict.get('_ez_active_mocap_deltas'),
                motion_physics_mode=active_motion_mode,
                motion_strength=active_motion_strength,
                anatomical_zones=active_anat_zones,
                allow_camera_movement=allow_cam_global,
            )
            sampled_win_cpu = _stabilize_3d_video_latent_outliers(
                sampled_win_cpu,
                outlier_strength=outlier_suppression,
                motion_physics_mode=active_motion_mode,
                motion_strength=active_motion_strength,
                anatomical_zones=active_anat_zones,
            )
            if seg_idx == 0:
                try:
                    import torch.nn.functional as F
                    v0_stat = _unpack_av_tensors(sampled_win_cpu)[0]
                    if isinstance(v0_stat, torch.Tensor) and v0_stat.ndim == 5 and int(v0_stat.shape[2]) > 2:
                        v0_body = v0_stat[:, :, 1:, :, :].float()
                        head_slice = v0_body[:, :, :min(6, int(v0_body.shape[2])), :, :]
                        m_all = v0_body.mean(dim=(2, 3, 4), keepdim=True)
                        s_all = torch.clamp(v0_body.std(dim=(2, 3, 4), keepdim=True), min=1e-04)
                        m_head = head_slice.mean(dim=(2, 3, 4), keepdim=True)
                        s_head = torch.clamp(head_slice.std(dim=(2, 3, 4), keepdim=True), min=1e-04)
                        master_lat_stats['mean'] = (0.75 * m_head + 0.25 * m_all).detach().cpu()
                        master_lat_stats['std'] = (0.75 * s_head + 0.25 * s_all).detach().cpu()
                        b0, c0, t0, h0, w0 = v0_body.shape
                        v0_2d = v0_body.permute(0, 2, 1, 3, 4).reshape(b0 * t0, c0, h0, w0)
                        v0_lf = F.avg_pool2d(F.pad(v0_2d, (1, 1, 1, 1), mode='reflect'), kernel_size=3, stride=1)
                        v0_hf = (v0_2d - v0_lf).reshape(b0, t0, c0, h0, w0).permute(0, 2, 1, 3, 4)
                        master_lat_stats['w0_hf_std'] = torch.clamp(v0_hf.std(dim=(2, 3, 4), keepdim=True), min=1e-04).detach().cpu()
                        master_lat_stats['init_mean'] = master_lat_stats['mean'].clone()
                        master_lat_stats['init_std'] = master_lat_stats['std'].clone()
                        if not isinstance(master_lat_stats.get('master_kf_latent'), torch.Tensor):
                            master_lat_stats['master_kf_latent'] = v0_stat[:, :, 0:1, :, :].float().detach().cpu()
                        master_lat_stats['prev_tail_latent'] = v0_stat[:, :, -1:, :, :].float().detach().cpu()
                        if isinstance(active_anat_zones, dict) and '_ez_w0_rgb_anchor' not in active_anat_zones and cont_ctx and cont_ctx.get('video_vae') is not None:
                            mid_i = min(int(v0_stat.shape[2]) - 1, max(1, int(v0_stat.shape[2]) // 3))
                            w0_mid_lat = _repack_av_tensors(sampled_win_cpu, [v0_stat[:, :, :mid_i + 1, :, :]])
                            w0_rgb_ref = _decode_handoff_frame_from_accum(w0_mid_lat, cont_ctx.get('video_vae'), overlap_t=1, tile_sz=int(cont_ctx.get('tile_size', 512) or 512), master_first_frame=None, seg_pixel_frames=seg_pixel_frames, anatomical_zones=None)
                            if isinstance(w0_rgb_ref, torch.Tensor) and w0_rgb_ref.numel() > 16:
                                active_anat_zones['_ez_w0_rgb_anchor'] = w0_rgb_ref.detach().cpu()
                except Exception:
                    pass
            elif seg_idx >= 1 and isinstance(master_lat_stats.get('w0_hf_std'), torch.Tensor):
                try:
                    import torch.nn.functional as F
                    cur_list_hf = _unpack_av_tensors(sampled_win_cpu)
                    vk = cur_list_hf[0] if len(cur_list_hf) > 0 and isinstance(cur_list_hf[0], torch.Tensor) else None
                    if isinstance(vk, torch.Tensor) and vk.ndim == 5 and int(vk.shape[2]) > 2:
                        orig_vk_dt = vk.dtype
                        vk_f = vk.float()
                        bk, ck, tk, hk, wk = vk_f.shape
                        vk_2d = vk_f.permute(0, 2, 1, 3, 4).reshape(bk * tk, ck, hk, wk)
                        vk_lf = F.avg_pool2d(F.pad(vk_2d, (1, 1, 1, 1), mode='reflect'), kernel_size=3, stride=1).reshape(bk, tk, ck, hk, wk).permute(0, 2, 1, 3, 4)
                        vk_hf = vk_f - vk_lf
                        cur_hf_s = torch.clamp(vk_hf[:, :, 1:, :, :].std(dim=(2, 3, 4), keepdim=True), min=1e-04)
                        ref_hf_s = master_lat_stats['w0_hf_std'].to(device=vk_f.device, dtype=torch.float32)
                        hf_scale = torch.clamp(ref_hf_s / cur_hf_s, 0.65, 1.01)
                        vk_damped = vk_lf + vk_hf * torch.lerp(torch.ones_like(hf_scale), hf_scale, 0.82)
                        if isinstance(master_lat_stats.get('mean'), torch.Tensor) and isinstance(master_lat_stats.get('std'), torch.Tensor):
                            lf_m = vk_damped[:, :, 1:, :, :].mean(dim=(2, 3, 4), keepdim=True)
                            lf_s = torch.clamp(vk_damped[:, :, 1:, :, :].std(dim=(2, 3, 4), keepdim=True), min=1e-04)
                            m0 = master_lat_stats['mean'].to(device=vk_f.device, dtype=torch.float32)
                            s0 = master_lat_stats['std'].to(device=vk_f.device, dtype=torch.float32)
                            g_scale = torch.clamp(s0 / lf_s, 0.72, 1.01)
                            vk_damped[:, :, 1:, :, :] = (vk_damped[:, :, 1:, :, :] - lf_m) * torch.lerp(torch.ones_like(g_scale), g_scale, 0.70) + torch.lerp(lf_m, m0, 0.45)
                        cur_list_hf[0] = vk_damped.to(dtype=orig_vk_dt)
                        sampled_win_cpu = _repack_av_tensors(sampled_win_cpu, cur_list_hf)
                except Exception:
                    pass
            macro_segment_latents.append((sampled_win_cpu, int(seg_pixel_frames)))
            prev_seg_cpu = sampled_win_cpu
            if stitched_accum_cpu is None:
                stitched_accum_cpu = sampled_win_cpu
            else:
                cur_v_len = int(_unpack_av_tensors(sampled_win_cpu)[0].shape[2])
                stitched_accum_cpu = _blend_and_cat_av_windows(stitched_accum_cpu, sampled_win_cpu, 1 if is_h3_arch else eff_win_ov, cur_v_len, temporal_rigidity=temporal_rigidity)
            _emit_minipyav_live_video_preview(stitched_accum_cpu if stitched_accum_cpu is not None else sampled_win_cpu, seg_idx, total_wins, steps, steps)
            del win_lat, win_noise
            if inter_window_purge or bool(prof.get('inter_window_vram_purge', False)):
                comfy.model_management.soft_empty_cache()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            else:
                gc.collect()
        sampled_cpu = stitched_accum_cpu if stitched_accum_cpu is not None else (macro_segment_latents[0][0] if macro_segment_latents else fixed_samples)
    if isinstance(previous_latent_opt, dict) and 'samples' in previous_latent_opt:
        prev_s = _offload_completed_chunk_to_cpu(previous_latent_opt['samples'])
        prev_vid = _unpack_av_tensors(prev_s)[0]
        if isinstance(prev_vid, torch.Tensor) and prev_vid.ndim == 5 and (prev_vid.shape[2] > 1) and isinstance(primary_vid_t, torch.Tensor) and (prev_vid.shape[3:] == primary_vid_t.shape[3:]):
            prev_m = previous_latent_opt.get('ez_macro_segment_latents')
            if isinstance(prev_m, list) and len(prev_m) > 0:
                macro_segment_latents = list(prev_m) + (macro_segment_latents if macro_segment_latents else [(sampled_cpu, int(seg_pixel_frames))])
            else:
                macro_segment_latents = [(prev_s, int(previous_latent_opt.get('total_frames', seg_pixel_frames)))] + (macro_segment_latents if macro_segment_latents else [(sampled_cpu, int(seg_pixel_frames))])
    if enable_latent_2x_upscale and len(macro_segment_latents) <= 1:
        s_list = _unpack_av_tensors(sampled_cpu)
        vid_s = s_list[0]
        if isinstance(vid_s, torch.Tensor) and vid_s.ndim == 5:
            (b, c, t, h, w) = vid_s.shape
            use_h3_norm = (int(c) == 24)
            h3_m = torch.tensor(_EZ_H3_24CH_MEAN, dtype=torch.float32, device=vid_s.device).view(1, 24, 1, 1) if use_h3_norm else None
            h3_s = torch.tensor(_EZ_H3_24CH_STD, dtype=torch.float32, device=vid_s.device).view(1, 24, 1, 1) if use_h3_norm else None
            up_chunks = []
            for ts in range(0, t, upscale_chunk_t):
                te = min(t, ts + upscale_chunk_t)
                sub = vid_s[:, :, ts:te, :, :].permute(0, 2, 1, 3, 4).reshape(b * (te - ts), c, h, w)
                if use_h3_norm:
                    sub_n = (sub.float() - h3_m) / h3_s
                    up_n = comfy.utils.common_upscale(sub_n, w * 2, h * 2, 'bislerp', 'disabled')
                    up_sub = (up_n * h3_s + h3_m).to(dtype=vid_s.dtype).reshape(b, te - ts, c, h * 2, w * 2).permute(0, 2, 1, 3, 4)
                else:
                    up_sub = comfy.utils.common_upscale(sub, w * 2, h * 2, 'bislerp', 'disabled').reshape(b, te - ts, c, h * 2, w * 2).permute(0, 2, 1, 3, 4)
                up_chunks.append(up_sub.detach().cpu())
            s_list[0] = torch.cat(up_chunks, dim=2)
            sampled_cpu = _repack_av_tensors(sampled_cpu, s_list)
        elif isinstance(vid_s, torch.Tensor) and vid_s.ndim == 4:
            (b, c, h, w) = vid_s.shape
            s_list[0] = comfy.utils.common_upscale(vid_s, w * 2, h * 2, 'bislerp', 'disabled').detach().cpu()
            sampled_cpu = _repack_av_tensors(sampled_cpu, s_list)
    if aggressive_purge or not bool(prof.get('persistent_vram_weights', False)):
        if hasattr(comfy.model_management, 'unload_all_models'):
            comfy.model_management.unload_all_models()
        comfy.model_management.soft_empty_cache()
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    out_latent = latent_dict.copy()
    if isinstance(active_anat_zones, dict) and active_anat_zones:
        out_latent['ez_character_identity_anchor'] = {
            'skeletal_rig': dict(active_anat_zones.get('skeletal_rig', {})) if isinstance(active_anat_zones.get('skeletal_rig'), dict) else {},
            'zone_rgb_stats': dict(active_anat_zones.get('zone_rgb_stats', {})) if isinstance(active_anat_zones.get('zone_rgb_stats'), dict) else {},
            'zone_hf_stats': dict(active_anat_zones.get('zone_hf_stats', {})) if isinstance(active_anat_zones.get('zone_hf_stats'), dict) else {},
            'face_crop_bhwc': active_anat_zones['face_crop_bhwc'].detach().cpu().to(dtype=torch.float16) if isinstance(active_anat_zones.get('face_crop_bhwc'), torch.Tensor) else None,
            'torso_crop_bhwc': active_anat_zones['torso_crop_bhwc'].detach().cpu().to(dtype=torch.float16) if isinstance(active_anat_zones.get('torso_crop_bhwc'), torch.Tensor) else None,
            'pelvic_crop_bhwc': active_anat_zones['pelvic_crop_bhwc'].detach().cpu().to(dtype=torch.float16) if isinstance(active_anat_zones.get('pelvic_crop_bhwc'), torch.Tensor) else None,
        }
    out_latent.pop('ez_continuation_ctx', None)
    out_latent['samples'] = sampled_cpu
    if len(macro_segment_latents) >= 2:
        out_latent['ez_macro_segment_latents'] = macro_segment_latents
        out_latent['ez_overlap_t'] = overlap_t
    final_vid_t = _unpack_av_tensors(sampled_cpu)[0]
    frame_cnt = int(latent_dict.get('total_frames', final_vid_t.shape[2] if isinstance(final_vid_t, torch.Tensor) and final_vid_t.ndim == 5 else 1))
    ticket = f'EZ_H3_TICKET_SEED_{seed}_FRAMES_{frame_cnt}'
    return (out_latent, ticket)
