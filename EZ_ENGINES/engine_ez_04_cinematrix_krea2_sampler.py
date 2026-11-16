# -*- coding: utf-8 -*-

import re
import math
import gc
import torch
import comfy.model_management
import comfy.sample
import comfy.samplers
import comfy.utils
import latent_preview
import nodes
UPSCALE_METHODS = ['nearest-exact', 'bilinear', 'area', 'bicubic', 'bislerp']
DATE_FOLDER_FORMAT_PRESETS = ['YYYY-MM-DD', 'None', 'YYYYMMDD', 'YYYY-MM', 'YYYY/MM/DD', 'YYYY_MM_DD', 'YYYY-MM-DD_HH-MM']
_KEYPOINT_RCNN_CACHE = {'detector': None}


def _resolve_date_subfolder_path(base_out_dir, date_folder_format: str = 'YYYY-MM-DD', now_dt=None):
    from pathlib import Path
    from datetime import datetime
    out_p = Path(base_out_dir)
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
    target_p = (out_p / sub_str) if sub_str else out_p
    target_p.mkdir(parents=True, exist_ok=True)
    return target_p

def _sigma_schedule(model, steps, sampler_name, scheduler, denoise: float=1.0):
    device = getattr(model, 'load_device', comfy.model_management.get_torch_device())
    eff_denoise = max(0.05, min(1.0, float(denoise)))
    sampler = comfy.samplers.KSampler(model, steps=max(1, int(steps)), device=device, sampler=sampler_name, scheduler=scheduler, denoise=eff_denoise, model_options=model.model_options)
    return sampler.sigmas.detach().cpu()

def _percent_schedule_index(steps, sigmas, handoff_percent, stage_name):
    max_index = len(sigmas) - 2
    if max_index < 1:
        raise ValueError(f'{stage_name} must produce at least one non-terminal handoff sigma.')
    requested = round(steps * handoff_percent / 100.0)
    return max(1, min(max_index, requested))

def _nearest_schedule_index(sigmas, boundary_sigma, minimum_index, stage_name):
    max_index = len(sigmas) - 2
    boundary = float(boundary_sigma)
    candidates = [idx for idx in range(minimum_index, max_index + 1) if float(sigmas[idx - 1]) > boundary]
    if not candidates:
        return max(minimum_index, min(max_index, minimum_index))
    return min(candidates, key=lambda idx: abs(float(sigmas[idx]) - boundary))

def build_three_stage_sigma_triplet(stage1_model, stage2_model, stage1_steps, stage2_steps, stage1_sampler, stage1_scheduler, stage2_sampler, stage2_scheduler, handoff_percent, stage3_handoff_percent, denoise: float=1.0):
    if float(stage3_handoff_percent) <= float(handoff_percent):
        stage3_handoff_percent = min(99.0, float(handoff_percent) + 10.0)
    eff_denoise = max(0.05, min(1.0, float(denoise)))
    s1_full = _sigma_schedule(stage1_model, stage1_steps, stage1_sampler, stage1_scheduler, denoise=eff_denoise)
    s2_full = _sigma_schedule(stage2_model, stage2_steps, stage2_sampler, stage2_scheduler, denoise=eff_denoise)
    eff_s1_steps = max(2, len(s1_full) - 1)
    s3_start = _percent_schedule_index(eff_s1_steps, s1_full, stage3_handoff_percent, 'stage 1')
    s2_end_sigma = s1_full[s3_start].clone()
    s1_end = _percent_schedule_index(eff_s1_steps, s1_full, handoff_percent, 'stage 1')
    if s1_end >= s3_start:
        s1_end = max(1, s3_start - 1)
    s1_end_sigma = s1_full[s1_end].clone()
    s1_custom = s1_full[:s1_end + 1].clone()
    s2_start = _nearest_schedule_index(s2_full, s1_end_sigma, 1, 'stage 2')
    s2_end = _nearest_schedule_index(s2_full, s2_end_sigma, s2_start + 1, 'stage 2')
    s2_custom = torch.cat((s2_full[s2_start:s2_end], s2_end_sigma.reshape(1)))
    s2_custom[0] = s1_end_sigma
    s3_custom = s1_full[s3_start:].clone()
    s3_custom[0] = s2_end_sigma
    return (s1_custom, s2_custom, s3_custom)

def _zero_out_conditioning(conditioning):
    if not conditioning:
        return []
    out = []
    for t in conditioning:
        d = t[1].copy() if len(t) > 1 and isinstance(t[1], dict) else {}
        pooled = d.get('pooled_output', None)
        if isinstance(pooled, torch.Tensor):
            d['pooled_output'] = torch.zeros_like(pooled)
        out.append([torch.zeros_like(t[0]), d])
    return out

def _maybe_upscale_latent(model, latent, final_width, final_height, upscale_method):
    if int(final_width) <= 0 or int(final_height) <= 0:
        return (latent, False)
    latent_format = model.get_model_object('latent_format')
    downscale = int(getattr(latent_format, 'spacial_downscale_ratio', 8) or 8)
    target_lw = max(1, round(int(final_width) / downscale))
    target_lh = max(1, round(int(final_height) / downscale))
    samples = latent['samples']
    if samples.shape[-1] == target_lw and samples.shape[-2] == target_lh:
        return (latent, False)
    out = latent.copy()
    out['samples'] = comfy.utils.common_upscale(samples, target_lw, target_lh, upscale_method, 'disabled')
    return (out, True)

def _create_empty_krea2_latent(model, base_width, base_height):
    latent_format = model.get_model_object('latent_format')
    downscale = int(getattr(latent_format, 'spacial_downscale_ratio', 8) or 8)
    latent_ch = int(getattr(latent_format, 'latent_channels', 16) or 16)
    lw = max(1, int(base_width) // downscale)
    lh = max(1, int(base_height) // downscale)
    device = comfy.model_management.intermediate_device()
    samples = torch.zeros((1, latent_ch, lh, lw), dtype=torch.float32, device=device)
    return {'samples': samples}

class _ControlNet4DVAEProxy:
    def __init__(self, base_vae):
        self._base_vae = base_vae

    def encode(self, pixel_samples):
        out = self._base_vae.encode(pixel_samples)
        if isinstance(out, torch.Tensor) and out.ndim == 5:
            return out[:, :, 0, :, :]
        return out

    def __getattr__(self, name):
        return getattr(self._base_vae, name)


def _apply_tier_optimized_native_controlnet(stage1_model, positive, negative, image_vae, src_bhwc: torch.Tensor, omni_b: dict=None, tier_profile: dict=None, co_star_t2i_mask: torch.Tensor=None, style_low: str='realism'):
    if positive is None or negative is None or not isinstance(src_bhwc, torch.Tensor) or src_bhwc.ndim != 4:
        return (positive, negative, None)
    try:
        import folder_paths
        import comfy.controlnet
        import torch.nn.functional as F
        if 'controlnet' not in folder_paths.folder_names_and_paths:
            return (positive, negative, None)
        cn_files = folder_paths.get_filename_list('controlnet') or []
        if not cn_files:
            return (positive, negative, None)
        prof = dict(tier_profile) if isinstance(tier_profile, dict) else {}
        raw_tid = str(prof.get('tier_id', '1') or '1').strip().lower()
        tier_num = '4' if '4' in raw_tid else ('3' if '3' in raw_tid else ('2' if '2' in raw_tid else '1'))
        vram_gb = float(prof.get('vram_gb', 16.0) or 16.0)
        dev = getattr(stage1_model, 'load_device', comfy.model_management.get_torch_device())
        total_vram_mb = float(comfy.model_management.get_total_memory(dev)) / (1024.0 * 1024.0) if hasattr(comfy.model_management, 'get_total_memory') else (vram_gb * 1024.0)
        unet_size_mb = float(stage1_model.model_size()) / (1024.0 * 1024.0) if hasattr(stage1_model, 'model_size') else 12224.0
        est_headroom_mb = total_vram_mb - unet_size_mb
        m_inner = getattr(stage1_model, 'model', None)
        m_cfg = getattr(m_inner, 'model_config', None)
        cfg_cls = str(getattr(m_cfg, '__class__', type(m_cfg)).__name__).lower()
        diff_mod = getattr(m_inner, 'diffusion_model', None)
        diff_cls = str(getattr(diff_mod, '__class__', type(diff_mod)).__name__).lower()
        cond_meta = positive[0][1] if (isinstance(positive, list) and len(positive) > 0 and isinstance(positive[0], (list, tuple)) and len(positive[0]) > 1 and isinstance(positive[0][1], dict)) else {}
        has_flux_pooled = isinstance(cond_meta.get('pooled_output'), torch.Tensor) and cond_meta['pooled_output'].numel() > 0
        ctx_tensor = positive[0][0] if (isinstance(positive, list) and len(positive) > 0 and isinstance(positive[0], (list, tuple)) and len(positive[0]) > 0 and isinstance(positive[0][0], torch.Tensor)) else None
        ctx_dim = int(ctx_tensor.shape[-1]) if isinstance(ctx_tensor, torch.Tensor) and ctx_tensor.ndim >= 2 else 0
        is_sdxl = ('sdxl' in cfg_cls or 'xl' in cfg_cls)
        is_krea2_arch = (not is_sdxl) and ('krea' in cfg_cls or 'krea' in diff_cls or (not has_flux_pooled and ctx_dim != 4096))
        is_true_flux1 = (not is_sdxl) and (('flux' in cfg_cls or 'flux' in diff_cls) and not is_krea2_arch and has_flux_pooled and ctx_dim == 4096)
        cand_cn = None
        for fn in cn_files:
            fl = str(fn).lower()
            if is_krea2_arch and 'krea' in fl and not any(x in fl for x in ('sd15', 'sdxl', 'wan', 'v1-5')):
                cand_cn = fn
                break
            elif is_true_flux1 and any(k in fl for k in ('flux', 'union', 'instantx', 'shakker', 'xlabs', 'jasper')) and not any(x in fl for x in ('krea', 'sd15', 'sdxl', 'wan', 'v1-5')):
                cand_cn = fn
                if 'union' in fl or 'pro' in fl:
                    break
            elif is_sdxl and any(k in fl for k in ('sdxl', 'xl', 'xinsir', 'mistoline', 'union')) and not any(x in fl for x in ('flux', 'krea', 'sd15')):
                cand_cn = fn
                if 'union' in fl or 'xinsir' in fl:
                    break
        if not cand_cn:
            if is_krea2_arch:
                print('[EZ-CN-GUARD] 🛡️ Krea 2 (Qwen3-VL + WanVAE) detekterad -> Hoppar över inkompatibel Flux.1-ControlNet och kör 0 MB artefaktfri In-Loop Struktur- & Anatomi-styrning.')
            return (positive, negative, None)
        if tier_num == '1' and (vram_gb < 15.0 or est_headroom_mb < 3800.0):
            print(f'[EZ-CN-SHIELD] 🛡️ Tier-1 VRAM-budget ({est_headroom_mb:.0f} MB marginal efter UNet {unet_size_mb:.0f} MB) -> Kör 0 MB In-Loop Struktur-styrning för att undvika VRAM-swapping.')
            return (positive, negative, None)
        cn_path = folder_paths.get_full_path('controlnet', cand_cn)
        if not cn_path:
            return (positive, negative, None)
        is_2d_cn = str(style_low or 'realism').strip().lower() in ('anime', 'cartoonish')
        (ih, iw) = (int(src_bhwc.shape[1]), int(src_bhwc.shape[2]))
        ob = dict(omni_b) if isinstance(omni_b, dict) else {}
        s1_mode = str(ob.get('slot1_focus_mode', '') or '').strip().lower()
        s4_dt_str = max(0.0, min(1.0, float(ob.get('slot4_depth_and_tile_strength', 0.90) or 0.90)))
        c_map = ob.get('canny_map')
        p_map = ob.get('openpose_map')
        d_map = ob.get('depth_1ch')
        if isinstance(c_map, torch.Tensor) and c_map.ndim == 4 and isinstance(d_map, torch.Tensor) and d_map.ndim == 4:
            cm_r = F.interpolate(c_map.float(), size=(ih, iw), mode='bilinear', align_corners=False)
            dm_r = F.interpolate(d_map.float(), size=(ih, iw), mode='bilinear', align_corners=False).expand(1, 3, ih, iw)
            pm_r = F.interpolate(p_map.float(), size=(ih, iw), mode='bilinear', align_corners=False) if (isinstance(p_map, torch.Tensor) and p_map.ndim == 4) else cm_r
            if is_2d_cn:
                (w_c, w_d, w_p) = (0.12, 0.32 * s4_dt_str, 0.56)
            elif 'openpose' in s1_mode:
                (w_c, w_d, w_p) = (0.35, 0.20 * s4_dt_str, 0.55)
            elif 'inpaint' in s1_mode:
                (w_c, w_d, w_p) = (0.50, 0.30 * s4_dt_str, 0.20)
            elif 'temporalnet' in s1_mode or 'liveportrait' in s1_mode:
                (w_c, w_d, w_p) = (0.30, 0.25 * s4_dt_str, 0.50)
            elif 'layerdiffusion' in s1_mode:
                (w_c, w_d, w_p) = (0.55, 0.35 * s4_dt_str, 0.15)
            else:
                (w_c, w_d, w_p) = (0.45, 0.35 * s4_dt_str, 0.30)
            hint_bchw = torch.clamp(cm_r * w_c + dm_r * w_d + pm_r * w_p, 0.0, 1.0)
        else:
            bchw_s = src_bhwc[:1, :, :, :3].detach().cpu().float().permute(0, 3, 1, 2).contiguous()
            lum_s = 0.299 * bchw_s[:, 0:1] + 0.587 * bchw_s[:, 1:2] + 0.114 * bchw_s[:, 2:3]
            gx = F.pad(lum_s[:, :, :, 1:] - lum_s[:, :, :, :-1], (0, 1, 0, 0))
            gy = F.pad(lum_s[:, :, 1:, :] - lum_s[:, :, :-1, :], (0, 0, 0, 1))
            edge_s = torch.clamp(torch.sqrt(gx * gx + gy * gy + 1e-06) * 6.0, 0.0, 1.0)
            hint_bchw = torch.clamp(edge_s.expand(1, 3, ih, iw) * (0.42 if is_2d_cn else 0.65) + bchw_s * (0.18 if is_2d_cn else 0.35), 0.0, 1.0)
        if isinstance(co_star_t2i_mask, torch.Tensor):
            cs_px = F.interpolate(co_star_t2i_mask.detach().cpu().float(), size=(ih, iw), mode='bilinear', align_corners=False)
            hint_bchw = hint_bchw * torch.clamp(1.0 - cs_px, 0.0, 1.0)
        hint_bhwc = hint_bchw.permute(0, 2, 3, 1).contiguous()
        s1_str_raw = float(ob.get('slot1_strength', 0.85) or 0.85)
        if is_2d_cn:
            (cn_str, end_pct) = (min(0.38, s1_str_raw * 0.40), 0.32)
        elif tier_num == '4':
            (cn_str, end_pct) = (min(0.86, s1_str_raw * 0.82), 0.78)
        elif tier_num == '3':
            (cn_str, end_pct) = (min(0.80, s1_str_raw * 0.75), 0.65)
        elif tier_num == '2':
            (cn_str, end_pct) = (min(0.74, s1_str_raw * 0.70), 0.52)
        else:
            (cn_str, end_pct) = (min(0.68, s1_str_raw * 0.64), 0.42)
        cnet_obj = comfy.controlnet.load_controlnet(cn_path)
        if cnet_obj is None:
            return (positive, negative, None)
        safe_vae = _ControlNet4DVAEProxy(image_vae) if image_vae is not None else None
        out_pos = []
        out_neg = []
        for (src_cond, dst_cond) in ((positive, out_pos), (negative, out_neg)):
            for t in src_cond:
                n = [t[0], t[1].copy()]
                c_net = cnet_obj.copy().set_cond_hint(hint_bhwc.movedim(-1, 1), cn_str, (0.0, end_pct), vae=safe_vae)
                if 'control' in n[1]:
                    c_net.set_previous_controlnet(n[1]['control'])
                n[1]['control'] = c_net
                n[1]['control_apply_to_uncond'] = False
                dst_cond.append(n)
        print(f'[EZ-CN-BRIDGE] 🦾 Aktiverade Tier-{tier_num} ControlNet ({cand_cn}) i Stage 1 (Styrka {cn_str:.2f} | Fönster 0% -> {end_pct*100:.0f}% | VRAM: {vram_gb:.0f}GB)')
        return (out_pos, out_neg, cnet_obj)
    except Exception:
        return (positive, negative, None)


def _evict_stage1_controlnet_from_vram(cnet_obj, tier_profile: dict=None):
    if cnet_obj is None:
        return
    try:
        prof = dict(tier_profile) if isinstance(tier_profile, dict) else {}
        if bool(prof.get('persistent_vram_weights', False)):
            return
        if hasattr(cnet_obj, 'cleanup'):
            cnet_obj.cleanup()
        del cnet_obj
        if hasattr(comfy.model_management, 'soft_empty_cache'):
            comfy.model_management.soft_empty_cache()
        gc.collect()
    except Exception:
        return


def sample_stage_with_sigmas(model, seed, cfg, sampler_name, scheduler, positive, negative, latent, sigmas, disable_noise, tier_profile=None, purge_after: bool=False):
    prof = dict(tier_profile) if isinstance(tier_profile, dict) else {}
    if hasattr(comfy.model_management, 'throw_exception_if_processing_interrupted'):
        comfy.model_management.throw_exception_if_processing_interrupted()
    try:
        from .engine_ez_01_cinematrix_canvas_ingest import enforce_cinematrix_thermal_shield
        enforce_cinematrix_thermal_shield('Krea2-Stage-Start', tier_profile=prof, force_inter_stage_pause=True)
    except Exception:
        enforce_cinematrix_thermal_shield = None
    try:
        cur_res = int(getattr(comfy.model_management, 'EXTRA_RESERVED_VRAM', 0) or 0)
        if cur_res > 900 * 1024 * 1024:
            comfy.model_management.EXTRA_RESERVED_VRAM = 600 * 1024 * 1024
    except Exception:
        pass
    latent_image = latent['samples']
    latent_image = comfy.sample.fix_empty_latent_channels(model, latent_image)
    if disable_noise:
        noise = torch.zeros(latent_image.size(), dtype=latent_image.dtype, layout=latent_image.layout, device='cpu')
    else:
        batch_inds = latent.get('batch_index', None)
        noise = comfy.sample.prepare_noise(latent_image, seed, batch_inds)
    noise_mask = latent.get('noise_mask', None)
    steps = max(1, len(sigmas) - 1)
    base_cb = latent_preview.prepare_callback(model, steps)
    reactor_ref_lat = latent.get('reactor_ref_latent', None)
    reactor_struct_w = float(latent.get('reactor_struct_weight', 0.0) or 0.0)
    reactor_mask_lat = latent.get('reactor_struct_mask', None)
    reactor_mouth_lat = latent.get('reactor_mouth_mask', None)
    reactor_is_2d = bool(latent.get('reactor_2d_style', False))
    run_model = model
    if isinstance(reactor_ref_lat, torch.Tensor) and reactor_struct_w > 0.01:
        try:
            import torch.nn.functional as F
            s_max_stage = float(sigmas[0].detach().cpu().item()) if isinstance(sigmas, torch.Tensor) and len(sigmas) > 0 else 1.0
            s_max_norm = (s_max_stage / 1000.0) if s_max_stage > 1.5 else s_max_stage
            s_ceil = max(0.68, min(1.0, s_max_norm))
            s_floor = max(0.70, min(0.88, s_ceil * 0.78)) if reactor_is_2d else max(0.50, min(0.80, s_ceil * 0.65))
            blur_r_struct = 1.65 if reactor_is_2d else 1.15
            ref_f_cpu = reactor_ref_lat.detach().cpu().float()
            ref_low_cpu = _gaussian_blur_2d(ref_f_cpu, blur_r_struct)
            ref_hi_cpu = ref_f_cpu - ref_low_cpu
            lat_mag = ref_f_cpu.abs().mean(dim=1, keepdim=True)
            gx_l = F.pad(lat_mag[:, :, :, 1:] - lat_mag[:, :, :, :-1], (0, 1, 0, 0))
            gy_l = F.pad(lat_mag[:, :, 1:, :] - lat_mag[:, :, :-1, :], (0, 0, 0, 1))
            edge_lat = _gaussian_blur_2d(torch.sqrt(gx_l * gx_l + gy_l * gy_l + 1e-06), 1.15)
            edge_peak = torch.clamp(edge_lat.amax(dim=(-2, -1), keepdim=True), min=1e-04)
            edge_norm = torch.clamp(edge_lat / edge_peak, 0.0, 1.0)
            if isinstance(reactor_mask_lat, torch.Tensor) and reactor_mask_lat.shape[-2:] == ref_f_cpu.shape[-2:]:
                anat_m = torch.clamp(reactor_mask_lat.detach().cpu().float(), 0.0, 1.0)
                spatial_mod_cpu = torch.clamp(0.25 + anat_m * 0.45 + edge_norm * 0.30, 0.25, 1.0)
            else:
                spatial_mod_cpu = torch.clamp(0.30 + 0.50 * edge_norm, 0.30, 0.85)
            spatial_mod_cpu = _gaussian_blur_2d(spatial_mod_cpu, 1.25)
            mouth_mod_cpu = None
            if isinstance(reactor_mouth_lat, torch.Tensor) and reactor_mouth_lat.shape[-2:] == ref_f_cpu.shape[-2:]:
                mm_c = torch.clamp(reactor_mouth_lat.detach().cpu().float(), 0.0, 1.0)
                r_hi_m = ref_hi_cpu.abs().mean(dim=1, keepdim=True) * mm_c
                r_hi_pk = torch.clamp(r_hi_m.amax(dim=(-2, -1), keepdim=True), min=1e-04)
                mouth_mod_cpu = torch.clamp(mm_c * torch.clamp((r_hi_m / r_hi_pk) * 1.75, 0.0, 1.0), 0.0, 1.0)
            run_model = model.clone()

            def _reactor_unet_wrapper(apply_model_fn, args_dict):
                inp_x = args_dict['input']
                t_sig = args_dict['timestep']
                c_dict = args_dict['c']
                pred = apply_model_fn(inp_x, t_sig, **c_dict)
                try:
                    raw_t = float(t_sig.flatten()[0].detach().cpu().item()) if isinstance(t_sig, torch.Tensor) and t_sig.numel() > 0 else 0.0
                    sig_val = (raw_t / 1000.0) if raw_t > 1.5 else raw_t
                    is_5d_t1 = (pred.ndim == 5 and int(pred.shape[2]) == 1)
                    guided_4d = pred.squeeze(2).float() if is_5d_t1 else pred.float()
                    x_4d = inp_x.squeeze(2).float() if (isinstance(inp_x, torch.Tensor) and inp_x.ndim == 5 and int(inp_x.shape[2]) == 1) else (inp_x.float() if isinstance(inp_x, torch.Tensor) else guided_4d)
                    if guided_4d.ndim != 4 or x_4d.ndim != 4 or guided_4d.shape[-2:] != ref_low_cpu.shape[-2:]:
                        return pred
                    sig_safe = max(0.14, min(1.0, float(sig_val)))
                    x0_4d = x_4d - sig_safe * guided_4d
                    if sig_val >= s_floor:
                        phase = min(1.0, max(0.0, (sig_val - s_floor) / max(0.08, s_ceil - s_floor)))
                        taper = 0.5 * (1.0 - math.cos(math.pi * phase))
                        p_low = _gaussian_blur_2d(x0_4d, blur_r_struct)
                        if reactor_is_2d:
                            w_step = min(0.038, reactor_struct_w * 0.12) * taper
                            p_hi = x0_4d - p_low
                            r_hi = ref_hi_cpu.to(device=pred.device, dtype=torch.float32)
                            e_dev = edge_norm.to(device=pred.device, dtype=torch.float32)
                            delta_hi = torch.clamp(r_hi - p_hi, -0.95, 0.95) * torch.clamp(0.18 + 0.82 * e_dev, 0.18, 1.0)
                            guided_4d = guided_4d - (delta_hi * w_step) / sig_safe
                        else:
                            w_step = min(0.055, reactor_struct_w * 0.16) * taper
                            r_low = ref_low_cpu.to(device=pred.device, dtype=torch.float32)
                            m_dev = spatial_mod_cpu.to(device=pred.device, dtype=torch.float32)
                            delta_low = torch.clamp(r_low - p_low, -1.35, 1.35)
                            guided_4d = guided_4d - (delta_low * (w_step * m_dev)) / sig_safe
                    if mouth_mod_cpu is not None and sig_val >= 0.32:
                        m_mouth_dev = mouth_mod_cpu.to(device=pred.device, dtype=torch.float32)
                        r_exact = ref_f_cpu.to(device=pred.device, dtype=torch.float32)
                        w_mouth = min(0.075, max(0.025, reactor_struct_w * 0.22)) * min(1.0, max(0.25, sig_val / max(0.35, s_ceil)))
                        delta_mouth = torch.clamp(r_exact - x0_4d, -1.50, 1.50)
                        guided_4d = guided_4d - (delta_mouth * (w_mouth * m_mouth_dev)) / sig_safe
                    out_pred = guided_4d.unsqueeze(2) if is_5d_t1 else guided_4d
                    if out_pred.shape != pred.shape:
                        return pred
                    return out_pred.to(dtype=pred.dtype)
                except Exception:
                    return pred

            run_model.set_model_unet_function_wrapper(_reactor_unet_wrapper)
        except Exception:
            run_model = model

    def _thermal_krea2_cb(step, x0, x, total_steps):
        if callable(enforce_cinematrix_thermal_shield):
            enforce_cinematrix_thermal_shield(f'Krea2-Step-{step + 1}/{total_steps}', tier_profile=prof, step_idx=int(step), total_steps=int(total_steps))
        if callable(base_cb):
            return base_cb(step, x0, x, total_steps)

    disable_pbar = not comfy.utils.PROGRESS_BAR_ENABLED
    device = getattr(run_model, 'load_device', comfy.model_management.get_torch_device())
    prev_fp16_acc = getattr(torch.backends.cuda.matmul, 'allow_fp16_accumulation', False) if hasattr(torch.backends, 'cuda') and hasattr(torch.backends.cuda, 'matmul') else False
    raw_sample_fn = getattr(comfy.sample.sample, '_multigpu_original', getattr(comfy.sample.sample, '__wrapped__', comfy.sample.sample))
    try:
        if hasattr(torch.backends, 'cuda') and hasattr(torch.backends.cuda, 'matmul'):
            torch.backends.cuda.matmul.allow_fp16_accumulation = True
        samples = raw_sample_fn(run_model, noise, steps, cfg, sampler_name, scheduler, positive, negative, latent_image, denoise=1.0, disable_noise=disable_noise, force_full_denoise=False, noise_mask=noise_mask, sigmas=sigmas.to(device), callback=_thermal_krea2_cb, disable_pbar=disable_pbar, seed=seed)
    finally:
        if hasattr(torch.backends, 'cuda') and hasattr(torch.backends.cuda, 'matmul'):
            torch.backends.cuda.matmul.allow_fp16_accumulation = prev_fp16_acc
    out = latent.copy()
    out.pop('co_star_t2i_boost_mask', None)
    out.pop('reactor_ref_latent', None)
    out.pop('reactor_struct_weight', None)
    out.pop('reactor_struct_mask', None)
    out.pop('reactor_mouth_mask', None)
    out.pop('reactor_2d_style', None)
    out['samples'] = samples
    if purge_after and bool(prof.get('aggressive_vram_purge', True)):
        if hasattr(comfy.model_management, 'soft_empty_cache'):
            comfy.model_management.soft_empty_cache()
        gc.collect()
    return out

def _gaussian_blur_2d(tensor_bchw: torch.Tensor, radius: float) -> torch.Tensor:
    if radius <= 0.05:
        return tensor_bchw.clone()
    import torch.nn.functional as F
    is_5d_t1 = (tensor_bchw.ndim == 5 and int(tensor_bchw.shape[2]) == 1)
    work_4d = tensor_bchw.squeeze(2) if is_5d_t1 else tensor_bchw
    if work_4d.ndim != 4:
        return tensor_bchw.clone()
    k_size = max(3, int(2 * int(2.5 * float(radius) + 0.5) + 1))
    sigma = max(0.1, float(radius))
    coords = torch.arange(k_size, dtype=work_4d.dtype, device=work_4d.device) - (k_size - 1) * 0.5
    k_1d = torch.exp(-coords ** 2 / (2.0 * sigma * sigma))
    k_1d = k_1d / k_1d.sum()
    c_ch = int(work_4d.shape[1])
    kh = k_1d.view(1, 1, 1, k_size).expand(c_ch, 1, 1, k_size).contiguous()
    kv = k_1d.view(1, 1, k_size, 1).expand(c_ch, 1, k_size, 1).contiguous()
    pad = k_size // 2
    blurred_h = F.conv2d(F.pad(work_4d, (pad, pad, 0, 0), mode='reflect'), kh, groups=c_ch)
    blurred_4d = F.conv2d(F.pad(blurred_h, (0, 0, pad, pad), mode='reflect'), kv, groups=c_ch)
    return blurred_4d.unsqueeze(2) if is_5d_t1 else blurred_4d

def _capsule_sdf_2d(grid_y: torch.Tensor, grid_x: torch.Tensor, y1: float, x1: float, y2: float, x2: float, radius: float) -> torch.Tensor:
    vy = float(y2 - y1)
    vx = float(x2 - x1)
    seg_len_sq = max(1e-06, vy * vy + vx * vx)
    t_proj = torch.clamp(((grid_y - float(y1)) * vy + (grid_x - float(x1)) * vx) / seg_len_sq, 0.0, 1.0)
    proj_y = float(y1) + t_proj * vy
    proj_x = float(x1) + t_proj * vx
    dist = torch.sqrt((grid_y - proj_y) ** 2 + (grid_x - proj_x) ** 2 + 1e-06)
    rad = max(2.0, float(radius))
    return torch.clamp(1.0 - torch.clamp((dist - rad * 0.65) / (rad * 0.75), 0.0, 1.0), 0.0, 1.0)

def _detect_skeletal_keypoints_rcnn(frame_3hw: torch.Tensor, conf_thresh: float=0.45):
    try:
        from .engine_ez_hot_reload import unlock_and_bind_portable_torch_hub
        unlock_and_bind_portable_torch_hub()
        import torchvision
        import torch.nn.functional as F
        (_, h_orig, w_orig) = frame_3hw.shape
        sub = frame_3hw[:, ::16, ::16].detach().float()
        kpt_sig = (int(h_orig), int(w_orig), round(float(sub.mean().item()), 5), round(float(sub.std().item()), 5), round(float(conf_thresh), 3))
        res_cache = _KEYPOINT_RCNN_CACHE.setdefault('results', {})
        if kpt_sig in res_cache:
            return res_cache[kpt_sig]
        scale = min(1.0, 384.0 / float(max(h_orig, w_orig, 1)))
        nh = max(64, int(round(h_orig * scale)))
        nw = max(64, int(round(w_orig * scale)))
        run_dev = torch.device('cuda') if torch.cuda.is_available() else frame_3hw.device
        small = F.interpolate(frame_3hw.unsqueeze(0).to(device=run_dev, dtype=torch.float32), size=(nh, nw), mode='bilinear', align_corners=False)[0]
        detector = _KEYPOINT_RCNN_CACHE.get('detector')
        if detector is None:
            weights_enum = getattr(torchvision.models.detection, 'KeypointRCNN_ResNet50_FPN_Weights', None)
            if weights_enum is not None:
                detector = torchvision.models.detection.keypointrcnn_resnet50_fpn(weights=weights_enum.DEFAULT)
            else:
                detector = torchvision.models.detection.keypointrcnn_resnet50_fpn(pretrained=True)
            detector.eval()
            _KEYPOINT_RCNN_CACHE['detector'] = detector
        detector = detector.to(device=run_dev, dtype=torch.float32).eval()
        with torch.no_grad():
            preds = detector([small])[0]
        detector.to('cpu')
        scores = preds.get('scores')
        kpts = preds.get('keypoints')
        if scores is None or kpts is None or scores.numel() == 0:
            res_cache[kpt_sig] = []
            return []
        keep = scores >= float(conf_thresh)
        if not bool(keep.any()):
            keep = scores >= 0.25
        valid_kpts = kpts[keep].detach().cpu().clone()
        valid_kpts[:, :, 0] = valid_kpts[:, :, 0] / scale
        valid_kpts[:, :, 1] = valid_kpts[:, :, 1] / scale
        out_kpts = [valid_kpts[i].tolist() for i in range(min(4, valid_kpts.shape[0]))]
        if len(res_cache) >= 32:
            res_cache.pop(next(iter(res_cache)), None)
        res_cache[kpt_sig] = out_kpts
        return out_kpts
    except Exception:
        return []

def _compute_neural_anatomy_zones(bchw: torch.Tensor, dock_cfg: dict=None):
    import torch.nn.functional as F
    cfg = dict(dock_cfg) if isinstance(dock_cfg, dict) else {}
    (b_sz, _, h, w) = bchw.shape
    dev = bchw.device
    sens = float(cfg.get('detection_sensitivity', 0.45))
    feather_r = max(1.0, float(cfg.get('mask_feather_radius', 10.0)))
    use_rcnn_flag = bool(cfg.get('use_keypoint_detector', True))
    sub_z = bchw[:, :, ::16, ::16].detach().float()
    zone_sig = ('v4_horiz_jaw_capsule', int(b_sz), int(h), int(w), round(float(sub_z.mean().item()), 5), round(float(sub_z.std().item()), 5), round(sens, 3), round(feather_r, 2), use_rcnn_flag)
    zone_cache = _KEYPOINT_RCNN_CACHE.setdefault('zone_masks', {})
    if zone_sig in zone_cache:
        return {zk: zv.to(device=dev) for (zk, zv) in zone_cache[zone_sig].items()}
    (r_ch, g_ch, b_ch) = (bchw[:, 0:1], bchw[:, 1:2], bchw[:, 2:3])
    y_luma = 0.299 * r_ch + 0.587 * g_ch + 0.114 * b_ch
    cr = (r_ch - y_luma) * 0.713 + 0.5
    cb = (b_ch - y_luma) * 0.564 + 0.5
    tol = max(0.08, 0.22 - 0.12 * sens)
    human_skin = torch.exp(-(((cr - 0.575) / tol) ** 2 + ((cb - 0.435) / tol) ** 2))
    crimson_orc_skin = torch.exp(-(((cr - 0.665) / (tol * 1.45)) ** 2 + ((cb - 0.425) / (tol * 1.45)) ** 2)) * torch.clamp((r_ch - g_ch) * 2.2 + 0.25, 0.0, 1.0)
    orc_olive_skin = torch.exp(-(((cr - 0.465) / (tol * 1.25)) ** 2 + ((cb - 0.445) / (tol * 1.25)) ** 2)) * torch.clamp((g_ch - b_ch) * 2.5 + 0.35, 0.0, 1.0)
    fantasy_cool_skin = torch.exp(-(((cr - 0.48) / (tol * 1.3)) ** 2 + ((cb - 0.56) / (tol * 1.3)) ** 2))
    skin_chroma = torch.maximum(torch.maximum(human_skin, crimson_orc_skin * 0.96), torch.maximum(orc_olive_skin * 0.9, fantasy_cool_skin * 0.85))
    luma_gate = torch.clamp(1.0 - torch.abs(y_luma - 0.48) * 1.65, 0.15, 1.0)
    base_skin = torch.clamp(skin_chroma * luma_gate, 0.0, 1.0)
    gx = F.pad(y_luma[:, :, :, 1:] - y_luma[:, :, :, :-1], (0, 1, 0, 0))
    gy = F.pad(y_luma[:, :, 1:, :] - y_luma[:, :, :-1, :], (0, 0, 0, 1))
    grad_mag = torch.clamp(torch.sqrt(gx * gx + gy * gy + 1e-06) * 4.5, 0.0, 1.0)
    specular_eye = torch.clamp((y_luma - 0.78) * 4.0, 0.0, 1.0) * grad_mag
    yy = torch.arange(h, dtype=torch.float32, device=dev).view(1, 1, h, 1).expand(1, 1, h, w)
    xx = torch.arange(w, dtype=torch.float32, device=dev).view(1, 1, 1, w).expand(1, 1, h, w)
    face_m = torch.zeros((1, 1, h, w), dtype=torch.float32, device=dev)
    mouth_m = torch.zeros((1, 1, h, w), dtype=torch.float32, device=dev)
    eyes_m = torch.zeros((1, 1, h, w), dtype=torch.float32, device=dev)
    hands_m = torch.zeros((1, 1, h, w), dtype=torch.float32, device=dev)
    torso_m = torch.zeros((1, 1, h, w), dtype=torch.float32, device=dev)
    pelvic_m = torch.zeros((1, 1, h, w), dtype=torch.float32, device=dev)
    feet_m = torch.zeros((1, 1, h, w), dtype=torch.float32, device=dev)
    use_rcnn = bool(cfg.get('use_keypoint_detector', True))
    kpt_people = _detect_skeletal_keypoints_rcnn(bchw[0], conf_thresh=sens) if use_rcnn and b_sz > 0 else []
    if kpt_people:
        for kp in kpt_people:
            (nose, l_eye, r_eye, l_ear, r_ear) = (kp[0], kp[1], kp[2], kp[3], kp[4])
            (l_sh, r_sh, l_el, r_el, l_wr, r_wr) = (kp[5], kp[6], kp[7], kp[8], kp[9], kp[10])
            (l_hp, r_hp, l_kn, r_kn, l_an, r_an) = (kp[11], kp[12], kp[13], kp[14], kp[15], kp[16])
            sh_span = max(24.0, math.hypot(l_sh[0] - r_sh[0], l_sh[1] - r_sh[1]))
            eye_span = max(12.0, math.hypot(l_eye[0] - r_eye[0], l_eye[1] - r_eye[1]))
            (sh_cx, sh_cy) = (0.5 * (l_sh[0] + r_sh[0]), 0.5 * (l_sh[1] + r_sh[1]))
            (hp_cx, hp_cy) = (0.5 * (l_hp[0] + r_hp[0]), 0.5 * (l_hp[1] + r_hp[1]))
            (eye_cx, eye_cy) = (0.5 * (l_eye[0] + r_eye[0]), 0.5 * (l_eye[1] + r_eye[1]))
            face_scale = max(eye_span, 0.36 * max(16.0, sh_cy - eye_cy), 0.18 * sh_span)
            nose_tip_y = max(float(nose[1]), eye_cy + 0.36 * face_scale)
            face_m = torch.maximum(face_m, _capsule_sdf_2d(yy, xx, eye_cy - face_scale * 0.45, nose[0], nose_tip_y + face_scale * 0.82, nose[0], face_scale * 1.15))
            mouth_mid_y = nose_tip_y + face_scale * 0.40
            below_nose_gate = torch.clamp((yy - (nose_tip_y + face_scale * 0.02)) / max(1.5, face_scale * 0.08), 0.0, 1.0)
            above_neck_gate = torch.clamp(((nose_tip_y + face_scale * 0.92) - yy) / max(1.5, face_scale * 0.12), 0.0, 1.0)
            jaw_cap = _capsule_sdf_2d(yy, xx, mouth_mid_y, nose[0] - face_scale * 0.36, mouth_mid_y, nose[0] + face_scale * 0.36, face_scale * 0.50) * below_nose_gate * above_neck_gate
            mouth_m = torch.maximum(mouth_m, jaw_cap)
            eyes_m = torch.maximum(eyes_m, _capsule_sdf_2d(yy, xx, l_eye[1], l_eye[0], r_eye[1], r_eye[0], eye_span * 0.38))
            for (el, wr) in ((l_el, l_wr), (r_el, r_wr)):
                hx = wr[0] + 0.35 * (wr[0] - el[0])
                hy = wr[1] + 0.35 * (wr[1] - el[1])
                hands_m = torch.maximum(hands_m, _capsule_sdf_2d(yy, xx, wr[1], wr[0], hy, hx, sh_span * 0.34))
            torso_top_y = max(sh_cy + 0.06 * sh_span, nose_tip_y + face_scale * 1.05)
            below_neck_gate = torch.clamp((yy - (sh_cy - 0.04 * sh_span)) / max(2.0, sh_span * 0.08), 0.0, 1.0)
            torso_cap = _capsule_sdf_2d(yy, xx, torso_top_y, sh_cx, hp_cy, hp_cx, sh_span * 0.64) * below_neck_gate
            torso_m = torch.maximum(torso_m, torso_cap)
            pel_y2 = hp_cy + 0.28 * (0.5 * (l_kn[1] + r_kn[1]) - hp_cy)
            pel_x2 = hp_cx + 0.28 * (0.5 * (l_kn[0] + r_kn[0]) - hp_cx)
            pelvic_m = torch.maximum(pelvic_m, _capsule_sdf_2d(yy, xx, hp_cy, hp_cx, pel_y2, pel_x2, sh_span * 0.52))
            for (kn, an) in ((l_kn, l_an), (r_kn, r_an)):
                fx = an[0] + 0.28 * (an[0] - kn[0])
                fy = an[1] + 0.28 * (an[1] - kn[1])
                feet_m = torch.maximum(feet_m, _capsule_sdf_2d(yy, xx, an[1], an[0], fy, fx, sh_span * 0.32))
    else:
        ny = yy / float(max(1, h))
        nx = xx / float(max(1, w))
        fg_skin = torch.clamp(base_skin * (0.65 + 0.35 * grad_mag), 0.0, 1.0)
        w_sum = torch.clamp(fg_skin.sum(dim=(-2, -1), keepdim=True), min=1e-05)
        cx_s = (fg_skin * nx).sum(dim=(-2, -1), keepdim=True) / w_sum
        cy_s = (fg_skin * ny).sum(dim=(-2, -1), keepdim=True) / w_sum
        upper_skin = fg_skin * torch.clamp((0.34 - ny) / 0.09, 0.0, 1.0)
        u_sum = upper_skin.sum(dim=(-2, -1), keepdim=True)
        has_upper = (u_sum > 1e-03).float()
        u_denom = torch.clamp(u_sum, min=1e-05)
        head_cx = has_upper * ((upper_skin * nx).sum(dim=(-2, -1), keepdim=True) / u_denom) + (1.0 - has_upper) * cx_s
        head_cy = has_upper * torch.clamp((upper_skin * ny).sum(dim=(-2, -1), keepdim=True) / u_denom, 0.08, 0.23) + (1.0 - has_upper) * torch.clamp(cy_s - 0.28, 0.08, 0.23)
        head_gate_y = torch.clamp((0.32 - ny) / 0.07, 0.0, 1.0)
        face_raw = torch.exp(-(((ny - head_cy) / 0.095) ** 2 + ((nx - head_cx) / 0.13) ** 2)) * head_gate_y
        mouth_cy_fb = torch.clamp(head_cy + 0.052, 0.12, 0.28)
        below_nose_fb = torch.clamp((ny - (head_cy + 0.022)) / 0.015, 0.0, 1.0)
        mouth_raw = torch.exp(-(((ny - mouth_cy_fb) / 0.032) ** 2 + ((nx - head_cx) / 0.048) ** 2)) * head_gate_y * below_nose_fb
        face_m = face_raw * torch.clamp(fg_skin * 1.45 + 0.25, 0.0, 1.0)
        mouth_m = mouth_raw * torch.clamp(fg_skin * 1.45 + 0.25, 0.0, 1.0)
        eyes_m = torch.clamp(face_m * (0.55 * grad_mag + 0.45 * specular_eye) * 2.2, 0.0, 1.0)
        torso_m = fg_skin * torch.exp(-(((ny - cy_s) / 0.18) ** 2 + ((nx - cx_s) / 0.26) ** 2)) * torch.clamp((ny - (head_cy + 0.09)) / 0.04, 0.0, 1.0)
        pelvic_m = fg_skin * torch.exp(-(((ny - torch.clamp(cy_s + 0.22, 0.15, 0.92)) / 0.14) ** 2 + ((nx - cx_s) / 0.22) ** 2))
        hands_m = fg_skin * torch.clamp(grad_mag * 1.35, 0.2, 1.0) * (1.0 - 0.65 * face_m)
        feet_m = fg_skin * torch.exp(-((ny - torch.clamp(cy_s + 0.42, 0.25, 0.96)) / 0.11) ** 2)
    body_gate = torch.clamp(base_skin * 0.85 + grad_mag * 0.25, 0.22, 1.0)
    face_gate = torch.clamp(base_skin * 0.90 + grad_mag * 0.35 + 0.30, 0.45, 1.0)
    pelvic_m = _gaussian_blur_2d((pelvic_m * body_gate).expand(b_sz, 1, h, w), feather_r * 0.8)
    pelvic_excl = torch.clamp(1.0 - pelvic_m * 1.5, 0.0, 1.0)
    face_m = _gaussian_blur_2d((face_m * face_gate).expand(b_sz, 1, h, w) * pelvic_excl, feather_r * 0.50)
    face_peak = torch.clamp(face_m.amax(dim=(-2, -1), keepdim=True), min=0.18)
    face_m = torch.clamp((face_m / face_peak) * pelvic_excl, 0.0, 1.0)
    eyes_m = _gaussian_blur_2d(torch.clamp(eyes_m.expand(b_sz, 1, h, w) + specular_eye * face_m, 0.0, 1.0) * pelvic_excl, max(1.5, feather_r * 0.25))
    mouth_m = _gaussian_blur_2d((mouth_m * face_gate).expand(b_sz, 1, h, w) * pelvic_excl * torch.clamp(1.0 - eyes_m * 2.5, 0.0, 1.0), max(1.2, feather_r * 0.22))
    mouth_peak = torch.clamp(mouth_m.amax(dim=(-2, -1), keepdim=True), min=0.15)
    mouth_m = torch.clamp((mouth_m / mouth_peak) * pelvic_excl * torch.clamp(1.0 - eyes_m * 2.5, 0.0, 1.0), 0.0, 1.0)
    head_excl = torch.clamp(1.0 - torch.maximum(face_m * 0.95, mouth_m * 1.25), 0.0, 1.0)
    torso_m = _gaussian_blur_2d((torso_m * body_gate).expand(b_sz, 1, h, w) * head_excl, feather_r)
    hands_m = _gaussian_blur_2d((hands_m * body_gate).expand(b_sz, 1, h, w), feather_r * 0.65)
    feet_m = _gaussian_blur_2d((feet_m * body_gate).expand(b_sz, 1, h, w), feather_r * 0.65)
    contour_shield = torch.clamp(grad_mag * (0.65 * hands_m + 0.75 * pelvic_m + 0.6 * feet_m + 0.85 * eyes_m), 0.0, 1.0)
    out_zones = {'base_skin': base_skin, 'face': face_m, 'mouth': mouth_m, 'eyes': eyes_m, 'hands': hands_m, 'torso': torso_m, 'pelvic': pelvic_m, 'feet': feet_m, 'contour_shield': contour_shield}
    if len(zone_cache) >= 16:
        zone_cache.pop(next(iter(zone_cache)), None)
    zone_cache[zone_sig] = {zk: zv.detach().cpu() for (zk, zv) in out_zones.items()}
    return out_zones


def _weighted_zone_bbox_norm(mask_11hw: torch.Tensor, fallback_box: tuple) -> tuple:
    if not isinstance(mask_11hw, torch.Tensor) or mask_11hw.numel() < 16:
        return fallback_box
    m2d = mask_11hw[0, 0].detach().cpu().float()
    (mh, mw) = (int(m2d.shape[0]), int(m2d.shape[1]))
    peak = float(m2d.max().item())
    if peak <= 0.04:
        return fallback_box
    active = torch.nonzero(m2d >= max(0.04, peak * 0.28), as_tuple=False)
    if active.numel() < 4:
        return fallback_box
    y1 = max(0.0, float(active[:, 0].min().item()) / float(max(1, mh)) - 0.05)
    y2 = min(1.0, float(active[:, 0].max().item()) / float(max(1, mh)) + 0.05)
    x1 = max(0.0, float(active[:, 1].min().item()) / float(max(1, mw)) - 0.06)
    x2 = min(1.0, float(active[:, 1].max().item()) / float(max(1, mw)) + 0.06)
    if (y2 - y1) < 0.12 or (x2 - x1) < 0.12:
        return fallback_box
    return (y1, x1, y2, x2)


def _crop_and_upscale_bhwc(img_1hwc: torch.Tensor, box_norm: tuple, out_h: int, out_w: int) -> torch.Tensor:
    (_, ih, iw, _) = img_1hwc.shape
    (ny1, nx1, ny2, nx2) = box_norm
    y1 = max(0, min(ih - 8, int(round(ny1 * ih))))
    y2 = max(y1 + 8, min(ih, int(round(ny2 * ih))))
    x1 = max(0, min(iw - 8, int(round(nx1 * iw))))
    x2 = max(x1 + 8, min(iw, int(round(nx2 * iw))))
    sub_nchw = img_1hwc[:, y1:y2, x1:x2, :3].movedim(-1, 1)
    return comfy.utils.common_upscale(sub_nchw, int(out_w), int(out_h), 'lanczos', 'center').movedim(1, -1).detach().cpu()


def _compute_masked_rgb_stats(bchw_cpu: torch.Tensor, mask_11hw: torch.Tensor) -> tuple:
    w_m = torch.clamp(mask_11hw.detach().cpu().float(), 0.0, 1.0)
    w_sum = torch.clamp(w_m.sum(), min=1e-04)
    if float(w_m.max().item()) <= 0.03:
        return (bchw_cpu.mean(dim=(2, 3), keepdim=True), torch.clamp(bchw_cpu.std(dim=(2, 3), keepdim=True), min=1e-04))
    mean_c = (bchw_cpu * w_m).sum(dim=(2, 3), keepdim=True) / w_sum
    var_c = ((bchw_cpu - mean_c) ** 2 * w_m).sum(dim=(2, 3), keepdim=True) / w_sum
    return (mean_c, torch.sqrt(torch.clamp(var_c, min=1e-06)))


def _compute_masked_hf_and_specular_stats(bchw_cpu: torch.Tensor, mask_11hw: torch.Tensor) -> dict:
    try:
        w_m = torch.clamp(mask_11hw.detach().cpu().float(), 0.0, 1.0)
        if w_m.shape[2:] != bchw_cpu.shape[2:]:
            import torch.nn.functional as F
            w_m = F.interpolate(w_m, size=bchw_cpu.shape[2:], mode='bilinear', align_corners=False)
        w_sum = torch.clamp(w_m.sum(), min=1e-04)
        fine_low = _gaussian_blur_2d(bchw_cpu, 0.65)
        mid_low = _gaussian_blur_2d(bchw_cpu, 1.35)
        fine_hf = (bchw_cpu - fine_low).abs()
        mid_hf = (fine_low - mid_low).abs()
        luma = 0.299 * bchw_cpu[:, 0:1] + 0.587 * bchw_cpu[:, 1:2] + 0.114 * bchw_cpu[:, 2:3]
        if float(w_m.max().item()) <= 0.03:
            fine_std = float(fine_hf.mean().item())
            mid_std = float(mid_hf.mean().item())
            spec_p95 = float(torch.quantile(luma.flatten(), 0.95).item()) if luma.numel() > 0 else 0.75
        else:
            fine_std = float(((fine_hf * w_m).sum() / (w_sum * float(bchw_cpu.shape[1]))).item())
            mid_std = float(((mid_hf * w_m).sum() / (w_sum * float(bchw_cpu.shape[1]))).item())
            active_luma = luma[w_m > 0.15]
            spec_p95 = float(torch.quantile(active_luma, 0.95).item()) if active_luma.numel() >= 16 else float(luma.max().item())
        return {
            'fine_hf_energy': max(1e-04, fine_std),
            'mid_hf_energy': max(1e-04, mid_std),
            'specular_p95': max(0.10, min(1.0, spec_p95)),
        }
    except Exception:
        return {'fine_hf_energy': 0.018, 'mid_hf_energy': 0.014, 'specular_p95': 0.78}


def compute_downscaled_latent_anatomy_zones(img_bhwc: torch.Tensor, latent_h: int, latent_w: int, dock_cfg: dict=None) -> dict:
    if not isinstance(img_bhwc, torch.Tensor) or img_bhwc.ndim != 4 or float(img_bhwc.abs().max().item()) <= 1e-04:
        return {}
    try:
        import torch.nn.functional as F
        cfg = dict(dock_cfg) if isinstance(dock_cfg, dict) else {}
        w_face = max(0.0, min(2.0, float(cfg.get('lock_face_and_eyes', 1.0) or 1.0) / 1.0))
        w_hands = max(0.0, min(2.0, float(cfg.get('lock_hands_and_fingers', 1.25) or 1.25) / 1.25))
        w_torso = max(0.0, min(2.0, float(cfg.get('lock_torso_and_breasts', 1.10) or 1.10) / 1.10))
        w_pelvic = max(0.0, min(2.0, float(cfg.get('lock_intimate_pelvic_anatomy', 1.35) or 1.35) / 1.35))
        w_feet = max(0.0, min(2.0, float(cfg.get('lock_feet_and_toes', 1.15) or 1.15) / 1.15))
        w_shield = max(0.0, min(2.0, float(cfg.get('eye_and_contour_sharpness_shield', 0.90) or 0.90) / 0.90))
        lh = max(1, int(latent_h))
        lw = max(1, int(latent_w))
        src_1hwc = img_bhwc[:1, :, :, :3].detach().cpu().float()
        (_, orig_h, orig_w, _) = src_1hwc.shape
        bchw = src_1hwc.permute(0, 3, 1, 2).contiguous()
        small_h = min(512, max(64, lh * 8))
        small_w = min(512, max(64, lw * 8))
        small_bchw = F.interpolate(bchw, size=(small_h, small_w), mode='bilinear', align_corners=False)
        zones = _compute_neural_anatomy_zones(small_bchw, dock_cfg=dock_cfg)
        m_mouth = F.interpolate(zones['mouth'], size=(lh, lw), mode='bilinear', align_corners=False).detach().cpu()
        m_face = F.interpolate(zones['face'], size=(lh, lw), mode='bilinear', align_corners=False).detach().cpu()
        m_eyes = F.interpolate(zones['eyes'], size=(lh, lw), mode='bilinear', align_corners=False).detach().cpu()
        m_torso = F.interpolate(zones['torso'], size=(lh, lw), mode='bilinear', align_corners=False).detach().cpu()
        m_pelvic = F.interpolate(zones['pelvic'], size=(lh, lw), mode='bilinear', align_corners=False).detach().cpu()
        m_hands = F.interpolate(zones['hands'], size=(lh, lw), mode='bilinear', align_corners=False).detach().cpu()
        m_feet = F.interpolate(zones['feet'], size=(lh, lw), mode='bilinear', align_corners=False).detach().cpu()
        (r_s, g_s, b_s) = (small_bchw[:, 0:1], small_bchw[:, 1:2], small_bchw[:, 2:3])
        y_s = 0.299 * r_s + 0.587 * g_s + 0.114 * b_s
        gx_s = F.pad(y_s[:, :, :, 1:] - y_s[:, :, :, :-1], (0, 1, 0, 0))
        gy_s = F.pad(y_s[:, :, 1:, :] - y_s[:, :, :-1, :], (0, 0, 0, 1))
        grad_s = torch.clamp(torch.sqrt(gx_s * gx_s + gy_s * gy_s + 1e-06) * 5.0, 0.0, 1.0)
        red_dom_s = torch.clamp((r_s - g_s) * 2.8, 0.0, 1.0) * torch.clamp((r_s - b_s) * 2.4, 0.0, 1.0)
        non_core_s = torch.clamp(1.0 - (zones['base_skin'] * 0.92 + zones['face'] * 0.95 + zones['torso'] * 0.85 + zones['pelvic'] * 0.85 + zones['hands'] * 0.85), 0.0, 1.0)
        blood_edge_px = torch.clamp(red_dom_s * (0.45 + 0.55 * grad_s) * non_core_s, 0.0, 1.0)
        m_prop_blood = F.interpolate(_gaussian_blur_2d(blood_edge_px, 1.5), size=(lh, lw), mode='bilinear', align_corners=False).detach().cpu()
        weighted_face = torch.clamp((m_face * 0.85 + m_eyes * 0.35 * w_shield) * w_face, 0.0, 1.0)
        weighted_torso = torch.clamp(m_torso * w_torso, 0.0, 1.0)
        weighted_pelvic = torch.clamp(m_pelvic * w_pelvic, 0.0, 1.0)
        weighted_hands = torch.clamp(m_hands * w_hands, 0.0, 1.0)
        weighted_feet = torch.clamp(m_feet * w_feet, 0.0, 1.0)
        raw_anat_core = torch.clamp(
            torch.maximum(
                torch.maximum(weighted_pelvic, weighted_torso),
                torch.maximum(weighted_hands, torch.maximum(weighted_feet, weighted_face)),
            ),
            0.0,
            1.0,
        )
        anat_core = torch.clamp(raw_anat_core * (1.0 - 0.75 * m_prop_blood), 0.0, 1.0)
        head_box = _weighted_zone_bbox_norm(zones['face'], (0.02, 0.22, 0.42, 0.78))
        torso_box = _weighted_zone_bbox_norm(zones['torso'], (0.24, 0.18, 0.68, 0.82))
        pelvic_box = _weighted_zone_bbox_norm(zones['pelvic'], (0.52, 0.18, 0.96, 0.82))
        head_span_y = max(0.08, head_box[2] - head_box[0])
        torso_span_y = max(0.10, torso_box[2] - torso_box[0])
        torso_span_x = max(0.10, torso_box[3] - torso_box[1])
        pelvic_span_x = max(0.10, pelvic_box[3] - pelvic_box[1])
        skeletal_rig = {
            'head_box_norm': head_box,
            'torso_box_norm': torso_box,
            'pelvic_box_norm': pelvic_box,
            'head_center_ny_nx': (0.5 * (head_box[0] + head_box[2]), 0.5 * (head_box[1] + head_box[3])),
            'spine_to_head_ratio': float(torso_span_y / head_span_y),
            'shoulder_to_hip_ratio': float(torso_span_x / pelvic_span_x),
        }
        (f_mean, f_std) = _compute_masked_rgb_stats(small_bchw.detach().cpu(), zones['face'])
        (t_mean, t_std) = _compute_masked_rgb_stats(small_bchw.detach().cpu(), zones['torso'])
        (p_mean, p_std) = _compute_masked_rgb_stats(small_bchw.detach().cpu(), zones['pelvic'])
        core_full = torch.clamp(torch.maximum(zones['face'], torch.maximum(zones['torso'], zones['pelvic'])), 0.0, 1.0)
        (c_mean, c_std) = _compute_masked_rgb_stats(small_bchw.detach().cpu(), core_full)
        zone_rgb_stats = {
            'face': (f_mean, f_std),
            'torso': (t_mean, t_std),
            'pelvic': (p_mean, p_std),
            'core': (c_mean, c_std),
        }
        zone_hf_stats = {
            'face': _compute_masked_hf_and_specular_stats(bchw, zones['face']),
            'torso': _compute_masked_hf_and_specular_stats(bchw, zones['torso']),
            'pelvic': _compute_masked_hf_and_specular_stats(bchw, zones['pelvic']),
            'core': _compute_masked_hf_and_specular_stats(bchw, core_full),
        }
        face_crop = _crop_and_upscale_bhwc(src_1hwc, head_box, orig_h, orig_w)
        torso_crop = _crop_and_upscale_bhwc(src_1hwc, torso_box, orig_h, orig_w)
        pelvic_crop = _crop_and_upscale_bhwc(src_1hwc, pelvic_box, orig_h, orig_w)
        half_w = max(32, orig_w // 2)
        rem_w = max(32, orig_w - half_w)
        half_h = max(32, orig_h // 2)
        rem_h = max(32, orig_h - half_h)
        upper_body_box = (max(0.0, head_box[0] - 0.02), min(head_box[1], torso_box[1]), min(1.0, torso_box[2] + 0.04), max(head_box[3], torso_box[3]))
        left_panel = _crop_and_upscale_bhwc(src_1hwc, upper_body_box, orig_h, half_w)
        top_right = _crop_and_upscale_bhwc(src_1hwc, head_box, half_h, rem_w)
        bot_right = _crop_and_upscale_bhwc(src_1hwc, (torso_box[0], min(torso_box[1], pelvic_box[1]), pelvic_box[2], max(torso_box[3], pelvic_box[3])), rem_h, rem_w)
        right_panel = torch.cat([top_right, bot_right], dim=1)
        char_sheet = torch.cat([left_panel, right_panel], dim=2)
        return {
            'mouth': torch.clamp(m_mouth, 0.0, 1.0),
            'face': torch.clamp(m_face, 0.0, 1.0),
            'eyes': torch.clamp(m_eyes, 0.0, 1.0),
            'torso': torch.clamp(m_torso, 0.0, 1.0),
            'pelvic': torch.clamp(m_pelvic, 0.0, 1.0),
            'hands': torch.clamp(m_hands, 0.0, 1.0),
            'feet': torch.clamp(m_feet, 0.0, 1.0),
            'anat_core': anat_core,
            'prop_blood': torch.clamp(m_prop_blood, 0.0, 1.0),
            'dock_cfg': cfg,
            'skeletal_rig': skeletal_rig,
            'zone_rgb_stats': zone_rgb_stats,
            'zone_hf_stats': zone_hf_stats,
            'face_crop_bhwc': face_crop,
            'torso_crop_bhwc': torso_crop,
            'pelvic_crop_bhwc': pelvic_crop,
            'character_sheet_bhwc': char_sheet,
        }
    except Exception:
        return {}

def _render_anatomy_preview_bhwc(bchw: torch.Tensor, zones: dict) -> torch.Tensor:
    dim_bg = bchw * 0.32
    r = dim_bg[:, 0:1] + 0.05 * zones['face'] + 0.1 * zones['hands'] + 0.92 * zones['torso'] + 0.96 * zones['pelvic'] + 0.66 * zones['feet'] + 0.95 * zones['eyes']
    g = dim_bg[:, 1:2] + 0.94 * zones['face'] + 0.82 * zones['hands'] + 0.28 * zones['torso'] + 0.62 * zones['pelvic'] + 0.33 * zones['feet'] + 0.98 * zones['eyes']
    b = dim_bg[:, 2:3] + 0.98 * zones['face'] + 0.5 * zones['hands'] + 0.6 * zones['torso'] + 0.08 * zones['pelvic'] + 0.96 * zones['feet'] + 0.98 * zones['eyes']
    overlay = torch.cat([r, g, b], dim=1)
    return torch.clamp(overlay.permute(0, 2, 3, 1).contiguous().detach().cpu(), 0.0, 1.0)

def _stabilize_latent_anatomy_outliers(latent_dict: dict, dock_cfg: dict=None, anatomy_mask_lat: torch.Tensor=None, ref_lat_zones: dict=None) -> dict:
    if not isinstance(latent_dict, dict) or 'samples' not in latent_dict:
        return latent_dict
    s = latent_dict['samples']
    if not isinstance(s, torch.Tensor):
        return latent_dict
    is_5d_s = (s.ndim == 5 and int(s.shape[2]) == 1)
    s_4d = s.squeeze(2) if is_5d_s else s
    if s_4d.ndim != 4:
        return latent_dict
    cfg = dict(dock_cfg) if isinstance(dock_cfg, dict) else {}
    clean_s = torch.nan_to_num(s_4d.float(), nan=0.0, posinf=16.0, neginf=-16.0)
    raw_sup = float(cfg.get('latent_outlier_suppression', 0.32) or 0.32)
    w_face = max(0.0, min(2.0, float(cfg.get('lock_face_and_eyes', 1.0) or 1.0)))
    w_hands = max(0.0, min(2.0, float(cfg.get('lock_hands_and_fingers', 1.25) or 1.25)))
    w_torso = max(0.0, min(2.0, float(cfg.get('lock_torso_and_breasts', 1.10) or 1.10)))
    w_pelvic = max(0.0, min(2.0, float(cfg.get('lock_intimate_pelvic_anatomy', 1.35) or 1.35)))
    w_feet = max(0.0, min(2.0, float(cfg.get('lock_feet_and_toes', 1.15) or 1.15)))
    eff_sup = max(0.0, min(1.0, raw_sup if raw_sup > 0.01 else 0.24 * min(1.5, w_hands)))
    if eff_sup > 0.01 and clean_s.numel() > 16:
        sigma_cap = 6.8
        mean_c = clean_s.mean(dim=(-2, -1), keepdim=True)
        std_c = torch.clamp(clean_s.std(dim=(-2, -1), keepdim=True), min=1e-04)
        z = (clean_s - mean_c) / std_c
        excess = torch.clamp(torch.abs(z) - sigma_cap, min=0.0)
        damped_z = torch.sign(z) * (torch.minimum(torch.abs(z), torch.full_like(z, sigma_cap)) + torch.tanh(excess / 2.0) * 2.0)
        damped_s = mean_c + damped_z * std_c
        if isinstance(ref_lat_zones, dict) and isinstance(ref_lat_zones.get('face'), torch.Tensor) and ref_lat_zones['face'].shape[-2:] == clean_s.shape[-2:]:
            dev_s, dt_s = clean_s.device, clean_s.dtype
            zf_raw = ref_lat_zones['face'].to(device=dev_s, dtype=dt_s) * (w_face / 1.0)
            zm = ref_lat_zones.get('mouth', torch.zeros_like(zf_raw)).to(device=dev_s, dtype=dt_s)
            ze = ref_lat_zones.get('eyes', torch.zeros_like(zf_raw)).to(device=dev_s, dtype=dt_s)
            zf = zf_raw * torch.clamp(1.0 - zm * 0.95 - ze * 0.90, 0.0, 1.0)
            zh = ref_lat_zones.get('hands', torch.zeros_like(zf)).to(device=dev_s, dtype=dt_s) * (w_hands / 1.25)
            zt = ref_lat_zones.get('torso', torch.zeros_like(zf)).to(device=dev_s, dtype=dt_s) * (w_torso / 1.10)
            zp = ref_lat_zones.get('pelvic', torch.zeros_like(zf)).to(device=dev_s, dtype=dt_s) * (w_pelvic / 1.35)
            zft = ref_lat_zones.get('feet', torch.zeros_like(zf)).to(device=dev_s, dtype=dt_s) * (w_feet / 1.15)
            m_lat = torch.clamp(torch.maximum(torch.maximum(zp, zt), torch.maximum(zh, torch.maximum(zft, zf))), 0.0, 1.35)
            clean_s = torch.lerp(clean_s, damped_s, torch.clamp(m_lat * (eff_sup * 0.24), 0.0, 0.55))
        elif isinstance(anatomy_mask_lat, torch.Tensor) and anatomy_mask_lat.shape[-2:] == clean_s.shape[-2:]:
            m_lat = torch.clamp(anatomy_mask_lat.to(device=clean_s.device, dtype=clean_s.dtype), 0.0, 1.0)
            clean_s = torch.lerp(clean_s, damped_s, m_lat * (eff_sup * 0.22))
        else:
            clean_s = torch.lerp(clean_s, damped_s, eff_sup * 0.10)
    out = latent_dict.copy()
    out_s = clean_s.unsqueeze(2) if is_5d_s else clean_s
    out['samples'] = out_s.to(dtype=s.dtype)
    return out


def _anchor_original_style_latent(sampled_dict: dict, ref_latent: torch.Tensor, anchor_strength: float=0.72, face_mask_lat: torch.Tensor=None, torso_mask_lat: torch.Tensor=None, mouth_mask_lat: torch.Tensor=None, prop_blood_mask_lat: torch.Tensor=None, anat_core_mask_lat: torch.Tensor=None, co_star_t2i_mask_lat: torch.Tensor=None, dock_cfg: dict=None, ref_lat_zones: dict=None) -> dict:
    if not isinstance(sampled_dict, dict) or 'samples' not in sampled_dict or not isinstance(ref_latent, torch.Tensor):
        return sampled_dict
    s = sampled_dict['samples']
    if not isinstance(s, torch.Tensor):
        return sampled_dict
    is_5d_s = (s.ndim == 5 and int(s.shape[2]) == 1)
    s_4d = s.squeeze(2) if is_5d_s else s
    r_4d = ref_latent.squeeze(2) if (ref_latent.ndim == 5 and int(ref_latent.shape[2]) == 1) else ref_latent
    if s_4d.ndim != 4 or r_4d.ndim != 4 or s_4d.shape != r_4d.shape:
        return sampled_dict
    w_anc = max(0.0, min(0.95, float(anchor_strength)))
    if w_anc <= 0.005:
        return sampled_dict
    cfg = dict(dock_cfg) if isinstance(dock_cfg, dict) else (dict(ref_lat_zones.get('dock_cfg', {})) if isinstance(ref_lat_zones, dict) and isinstance(ref_lat_zones.get('dock_cfg'), dict) else {})
    w_face = max(0.0, min(2.0, float(cfg.get('lock_face_and_eyes', 1.0) or 1.0) / 1.0))
    w_hands = max(0.0, min(2.0, float(cfg.get('lock_hands_and_fingers', 1.25) or 1.25) / 1.25))
    w_torso = max(0.0, min(2.0, float(cfg.get('lock_torso_and_breasts', 1.10) or 1.10) / 1.10))
    w_pelvic = max(0.0, min(2.0, float(cfg.get('lock_intimate_pelvic_anatomy', 1.35) or 1.35) / 1.35))
    w_feet = max(0.0, min(2.0, float(cfg.get('lock_feet_and_toes', 1.15) or 1.15) / 1.15))
    s_f = s_4d.detach().cpu().float()
    r_f = r_4d.detach().cpu().float()
    spatial_gate = torch.ones((1, 1, int(s_f.shape[-2]), int(s_f.shape[-1])), dtype=torch.float32)
    if isinstance(co_star_t2i_mask_lat, torch.Tensor) and co_star_t2i_mask_lat.shape[-2:] == s_f.shape[-2:]:
        spatial_gate = torch.clamp(1.0 - co_star_t2i_mask_lat.detach().cpu().float(), 0.0, 1.0)
    s_low = _gaussian_blur_2d(s_f, 1.85)
    r_low = _gaussian_blur_2d(r_f, 1.85)
    s_high = s_f - s_low
    base_struct_w = min(0.42, w_anc * 0.68) * spatial_gate
    if isinstance(ref_lat_zones, dict):
        for (z_key, z_mult) in (('torso', w_torso), ('pelvic', w_pelvic), ('hands', w_hands), ('feet', w_feet)):
            z_t = ref_lat_zones.get(z_key)
            if isinstance(z_t, torch.Tensor) and z_t.shape[-2:] == s_f.shape[-2:]:
                zm = torch.clamp(z_t.detach().cpu().float() * z_mult, 0.0, 1.35) * spatial_gate
                base_struct_w = torch.maximum(base_struct_w, zm * min(0.58, w_anc * 0.92))
    elif isinstance(anat_core_mask_lat, torch.Tensor) and anat_core_mask_lat.shape[-2:] == s_f.shape[-2:]:
        ac_m = torch.clamp(anat_core_mask_lat.detach().cpu().float(), 0.0, 1.0) * spatial_gate
        base_struct_w = torch.maximum(base_struct_w, ac_m * min(0.56, w_anc * 0.92))
    merged = torch.lerp(s_low, r_low, torch.clamp(base_struct_w, 0.0, 0.65)) + s_high
    if isinstance(face_mask_lat, torch.Tensor) and face_mask_lat.shape[-2:] == s_f.shape[-2:] and w_face > 0.02:
        fm = torch.clamp(face_mask_lat.detach().cpu().float() * w_face, 0.0, 1.25) * spatial_gate
        if isinstance(torso_mask_lat, torch.Tensor) and torso_mask_lat.shape[-2:] == s_f.shape[-2:]:
            fm = fm * torch.clamp(1.0 - torso_mask_lat.detach().cpu().float() * 1.4, 0.0, 1.0)
        lh = max(1, int(s_f.shape[-2]))
        ly = torch.linspace(0.0, 1.0, steps=lh, dtype=torch.float32).view(1, 1, lh, 1)
        fm = fm * torch.clamp((0.36 - ly) / 0.08, 0.0, 1.0)
        face_w = min(0.52, w_anc * 0.95 * w_face)
        face_target = torch.lerp(s_low, r_low, face_w) + s_high
        merged = torch.lerp(merged, face_target, torch.clamp(fm, 0.0, 1.0))
    if isinstance(mouth_mask_lat, torch.Tensor) and mouth_mask_lat.shape[-2:] == s_f.shape[-2:]:
        mm = torch.clamp(mouth_mask_lat.detach().cpu().float(), 0.0, 1.0) * spatial_gate
        m_peak = torch.clamp(mm.amax(dim=(-2, -1), keepdim=True), min=0.12)
        mm_norm = torch.clamp(mm / m_peak, 0.0, 1.0)
        r_hi_m = (r_f - r_low).abs().mean(dim=1, keepdim=True) * mm_norm
        r_hi_pk = torch.clamp(r_hi_m.amax(dim=(-2, -1), keepdim=True), min=1e-04)
        mm_tusk = mm_norm * torch.clamp((r_hi_m / r_hi_pk) * 1.80, 0.04, 1.0)
        mouth_w = min(0.48, w_anc * 0.85)
        merged = torch.lerp(merged, r_f, mm_tusk * mouth_w)
    if isinstance(prop_blood_mask_lat, torch.Tensor) and prop_blood_mask_lat.shape[-2:] == s_f.shape[-2:]:
        pm = torch.clamp(prop_blood_mask_lat.detach().cpu().float(), 0.0, 1.0) * spatial_gate
        prop_w = min(0.56, w_anc * 1.15)
        prop_target = torch.lerp(s_low, r_low, prop_w) + s_high
        merged = torch.lerp(merged, prop_target, pm)
    out = sampled_dict.copy()
    out_m = merged.unsqueeze(2) if is_5d_s else merged
    out['samples'] = out_m.to(device=s.device, dtype=s.dtype)
    return out


def _anchor_orc_tusk_mouth_latent(sampled_dict: dict, ref_latent: torch.Tensor, mouth_mask_lat: torch.Tensor=None, style_low: str='realism', stage_weight: float=0.58, co_star_t2i_mask_lat: torch.Tensor=None) -> dict:
    if not isinstance(sampled_dict, dict) or 'samples' not in sampled_dict or not isinstance(ref_latent, torch.Tensor) or not isinstance(mouth_mask_lat, torch.Tensor):
        return sampled_dict
    s = sampled_dict['samples']
    if not isinstance(s, torch.Tensor):
        return sampled_dict
    is_5d_s = (s.ndim == 5 and int(s.shape[2]) == 1)
    s_4d = s.squeeze(2) if is_5d_s else s
    r_4d = ref_latent.squeeze(2) if (ref_latent.ndim == 5 and int(ref_latent.shape[2]) == 1) else ref_latent
    if s_4d.ndim != 4 or r_4d.ndim != 4 or s_4d.shape != r_4d.shape or mouth_mask_lat.shape[-2:] != s_4d.shape[-2:]:
        return sampled_dict
    w_stage = max(0.0, min(0.92, float(stage_weight)))
    if w_stage <= 0.01:
        return sampled_dict
    s_f = s_4d.detach().cpu().float()
    r_f = r_4d.detach().cpu().float()
    mm_raw = torch.clamp(mouth_mask_lat.detach().cpu().float(), 0.0, 1.0)
    if isinstance(co_star_t2i_mask_lat, torch.Tensor) and co_star_t2i_mask_lat.shape[-2:] == s_f.shape[-2:]:
        mm_raw = mm_raw * torch.clamp(1.0 - co_star_t2i_mask_lat.detach().cpu().float(), 0.0, 1.0)
    m_peak = float(mm_raw.max().item())
    if m_peak <= 0.03:
        return sampled_dict
    mm = torch.clamp(mm_raw / max(0.12, m_peak), 0.0, 1.0)
    s_low_t = _gaussian_blur_2d(s_f, 1.05)
    r_low_t = _gaussian_blur_2d(r_f, 1.05)
    s_high_t = s_f - s_low_t
    r_high_t = r_f - r_low_t
    ridge_mag = r_high_t.abs().mean(dim=1, keepdim=True) * mm
    ridge_peak = torch.clamp(ridge_mag.amax(dim=(-2, -1), keepdim=True), min=1e-04)
    ridge_sal = torch.clamp(ridge_mag / ridge_peak, 0.0, 1.0)
    tusk_mask = mm * torch.clamp(0.32 + ridge_sal * 1.45, 0.32, 1.0)
    low_blend_w = torch.clamp(tusk_mask * (w_stage * 0.72), 0.0, 0.78)
    high_blend_w = torch.clamp(tusk_mask * (w_stage * 0.88), 0.0, 0.90)
    guided_low = torch.lerp(s_low_t, r_low_t, low_blend_w)
    guided_high = torch.lerp(s_high_t, r_high_t, high_blend_w)
    merged = guided_low + guided_high
    out = sampled_dict.copy()
    out_m = merged.unsqueeze(2) if is_5d_s else merged
    out['samples'] = out_m.to(device=s.device, dtype=s.dtype)
    return out


def _apply_2d_cel_and_ink_stylization_bchw(bchw: torch.Tensor, style_low: str='anime', strength: float=0.86, zones: dict=None) -> torch.Tensor:
    import torch.nn.functional as F
    b_p1 = _gaussian_blur_2d(bchw, 1.55)
    diff_p1 = (bchw - b_p1).pow(2).mean(dim=1, keepdim=True)
    flat_p1 = torch.lerp(bchw, b_p1, torch.exp(-diff_p1 / 0.0055) * 0.88)
    b_p2 = _gaussian_blur_2d(flat_p1, 2.85)
    diff_p2 = (flat_p1 - b_p2).pow(2).mean(dim=1, keepdim=True)
    base_smooth = torch.lerp(flat_p1, b_p2, torch.exp(-diff_p2 / 0.0068) * 0.84)
    (r_c, g_c, b_c) = (base_smooth[:, 0:1], base_smooth[:, 1:2], base_smooth[:, 2:3])
    luma = (0.299 * r_c + 0.587 * g_c + 0.114 * b_c).clamp(1e-04, 1.0)
    lum_macro = _gaussian_blur_2d(luma, 14.0).clamp(0.06, 0.96)
    rel_shade = (luma / lum_macro).clamp(0.35, 1.65)
    step_shadow = torch.sigmoid((rel_shade - 0.88) * 28.0)
    step_hi = torch.sigmoid((rel_shade - 1.13) * 26.0)
    cel_mult = 0.78 + 0.22 * step_shadow + 0.10 * step_hi
    cel_luma = (lum_macro * cel_mult).clamp(0.03, 0.99)
    luma_ratio = (cel_luma / luma).clamp(0.55, 1.45)
    albedo_cel = (base_smooth * luma_ratio).clamp(0.0, 1.0)
    (ar, ag, ab) = (albedo_cel[:, 0:1], albedo_cel[:, 1:2], albedo_cel[:, 2:3])
    a_lum = (0.299 * ar + 0.587 * ag + 0.114 * ab).clamp(1e-04, 1.0)
    chroma_boost = 1.22 if str(style_low or '').lower() == 'cartoonish' else 1.16
    vibrant_cel = torch.cat([
        a_lum + (ar - a_lum) * chroma_boost,
        a_lum + (ag - a_lum) * chroma_boost,
        a_lum + (ab - a_lum) * chroma_boost,
    ], dim=1).clamp(0.0, 1.0)
    if isinstance(zones, dict) and isinstance(zones.get('face'), torch.Tensor):
        f_z = zones['face'].to(device=bchw.device, dtype=torch.float32)
        t_z = zones.get('torso', torch.zeros_like(f_z)).to(device=bchw.device, dtype=torch.float32)
        e_z = zones.get('eyes', torch.zeros_like(f_z)).to(device=bchw.device, dtype=torch.float32)
        skin_z = torch.clamp((f_z + 0.55 * t_z) * (1.0 - e_z * 2.2), 0.0, 1.0)
        flat_skin_mean = _gaussian_blur_2d(vibrant_cel, 6.5)
        vibrant_cel = torch.lerp(vibrant_cel, flat_skin_mean, skin_z * torch.exp(-diff_p1 / 0.0080) * 0.48)
        shadow_lift = torch.clamp(0.54 - a_lum, 0.0, 0.26) * 0.30 * skin_z
        vibrant_cel = (vibrant_cel + shadow_lift).clamp(0.0, 1.0)
    gx_ink = F.pad(luma[:, :, :, 1:] - luma[:, :, :, :-1], (0, 1, 0, 0))
    gy_ink = F.pad(luma[:, :, 1:, :] - luma[:, :, :-1, :], (0, 0, 0, 1))
    grad_mag = torch.sqrt(gx_ink * gx_ink + gy_ink * gy_ink + 1e-06)
    ink_thresh = 0.042 if str(style_low or '').lower() == 'cartoonish' else 0.052
    ink_alpha = torch.clamp((grad_mag - ink_thresh) * 9.5, 0.0, 0.86)
    ink_col = (vibrant_cel * 0.16).clamp(0.02, 0.18)
    cel_inked = torch.lerp(vibrant_cel, ink_col, ink_alpha)
    return torch.lerp(bchw, cel_inked, min(1.0, max(0.0, float(strength)))).clamp(0.0, 1.0)


def _detect_crimson_orc_reference_bhwc(src_bhwc: torch.Tensor) -> bool:
    if not isinstance(src_bhwc, torch.Tensor) or src_bhwc.ndim < 3 or src_bhwc.numel() < 128:
        return False
    try:
        t = src_bhwc[0] if src_bhwc.ndim == 4 else src_bhwc
        (h, w, _) = t.shape
        if h < 32 or w < 32:
            return False
        roi = t[int(h * 0.10):int(h * 0.78), int(w * 0.22):int(w * 0.78), :3].detach().cpu().float()
        (r, g, b) = (roi[:, :, 0], roi[:, :, 1], roi[:, :, 2])
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        mid_m = (lum > 0.10) & (lum < 0.78)
        crim_m = mid_m & (r > 0.28) & ((r - g) > 0.19) & ((r / torch.clamp(g, min=0.04)) > 1.62) & ((g - b).abs() < 0.12)
        crim_ratio = float(crim_m.float().sum().item()) / float(max(1, int(mid_m.float().sum().item())))
        jaw_roi = t[int(h * 0.14):int(h * 0.36), int(w * 0.32):int(w * 0.68), :3].detach().cpu().float()
        (jr, jg, jb) = (jaw_roi[:, :, 0], jaw_roi[:, :, 1], jaw_roi[:, :, 2])
        jlum = 0.299 * jr + 0.587 * jg + 0.114 * jb
        ivory_jaw = (jlum > 0.42) & ((jr - jg) < 0.11) & ((jg - jb) < 0.12)
        return bool(crim_ratio >= 0.14 and int(ivory_jaw.float().sum().item()) >= max(4, int(jaw_roi.shape[0] * jaw_roi.shape[1] * 0.003)))
    except Exception:
        return False


def _precondition_i2i_source_for_style_bhwc(src_bhwc: torch.Tensor, style_low: str='realism', seed: int=42, dock_cfg: dict=None, has_multi_cast: bool=False, has_vid_scene: bool=False, has_ref_p: bool=False, raw_denoise: float=0.75, has_orc_tusks: bool=False) -> torch.Tensor:
    if not isinstance(src_bhwc, torch.Tensor) or src_bhwc.ndim != 4:
        return src_bhwc
    s_low = str(style_low or 'realism').strip().lower()
    if not has_vid_scene and s_low not in ('anime', 'cartoonish'):
        return src_bhwc
    try:
        import torch.nn.functional as F
        dev = comfy.model_management.get_torch_device() if torch.cuda.is_available() else torch.device('cpu')
        bchw = src_bhwc[:1, :, :, :3].to(device=dev, dtype=torch.float32).permute(0, 3, 1, 2).contiguous()
        if s_low in ('anime', 'cartoonish') and not has_vid_scene:
            zones_pre = _compute_neural_anatomy_zones(bchw, dock_cfg=dock_cfg)
            cel_pre = _apply_2d_cel_and_ink_stylization_bchw(bchw, style_low=s_low, strength=0.86, zones=zones_pre)
            if has_orc_tusks:
                mouth_z = torch.clamp(zones_pre['mouth'] * (1.0 - zones_pre['eyes'] * 3.0), 0.0, 1.0)
                (sr, sg, sb) = (bchw[:, 0:1], bchw[:, 1:2], bchw[:, 2:3])
                s_lum = 0.299 * sr + 0.587 * sg + 0.114 * sb
                s_bg_lum = _gaussian_blur_2d(s_lum, 9.5)
                s_red_ex = sr - 0.5 * (sg + sb)
                s_bg_red = _gaussian_blur_2d(s_red_ex, 9.5)
                not_red = torch.maximum(torch.clamp((s_bg_red - s_red_ex - 0.012) / 0.085, 0.0, 1.0), torch.clamp((0.26 - s_red_ex) / 0.12, 0.0, 1.0))
                tusk_iv = torch.clamp((s_lum - s_bg_lum - 0.016) / 0.055, 0.0, 1.0) * torch.clamp((s_lum - 0.18) / 0.15, 0.0, 1.0) * not_red * mouth_z
                tusk_core_pre = torch.clamp((tusk_iv - 0.12) / 0.34, 0.0, 1.0)
                tusk_ink_pre = torch.clamp((_gaussian_blur_2d(tusk_core_pre, 1.4) - tusk_core_pre) * 2.6, 0.0, 1.0) * mouth_z
                ivory_cel = torch.cat([torch.full_like(sr, 0.96), torch.full_like(sg, 0.93), torch.full_like(sb, 0.86)], dim=1)
                ink_cel = torch.cat([torch.full_like(sr, 0.06), torch.full_like(sg, 0.05), torch.full_like(sb, 0.07)], dim=1)
                cel_pre = torch.lerp(cel_pre, ink_cel, torch.clamp(tusk_ink_pre * 0.92, 0.0, 0.92))
                cel_pre = torch.lerp(cel_pre, ivory_cel, torch.clamp(tusk_core_pre * 0.95, 0.0, 0.96))
            return torch.clamp(cel_pre, 0.0, 1.0).permute(0, 2, 3, 1).contiguous().detach().cpu()
        (ih, iw) = (int(bchw.shape[-2]), int(bchw.shape[-1]))
        s5_two_p = bool((dock_cfg or {}).get('s5_has_two_people', False)) if isinstance(dock_cfg, dict) else False
        if has_multi_cast and (not has_ref_p) and (not s5_two_p) and iw >= 64 and ih >= 64:
            xx_n = torch.linspace(0.0, 1.0, steps=iw, device=dev, dtype=torch.float32).view(1, 1, 1, iw).expand(1, 1, ih, iw)
            yy_n = torch.linspace(0.0, 1.0, steps=ih, device=dev, dtype=torch.float32).view(1, 1, ih, 1).expand(1, 1, ih, iw)
            w_left = max(32, int(round(iw * 0.50)))
            w_right = max(32, iw - w_left)
            x0_crop = max(0, int(round(iw * 0.14)))
            x1_crop = min(iw, max(x0_crop + 32, int(round(iw * 0.86))))
            left_sub = F.interpolate(bchw[:, :, :, x0_crop:x1_crop], size=(ih, w_left), mode='bilinear', align_corners=False)
            b_top = bchw[:, :, :max(2, ih // 14), :].mean(dim=(2, 3), keepdim=True)
            b_side = 0.5 * (bchw[:, :, :, :max(2, iw // 16)].mean(dim=(2, 3), keepdim=True) + bchw[:, :, :, -max(2, iw // 16):].mean(dim=(2, 3), keepdim=True))
            yy_r = torch.linspace(0.0, 1.0, steps=ih, device=dev, dtype=torch.float32).view(1, 1, ih, 1).expand(1, 3, ih, w_right)
            bg_grad_r = torch.lerp(b_top.expand(1, 3, ih, w_right), b_side.expand(1, 3, ih, w_right), yy_r)
            raw_right = bchw[:, :, :, w_left:]
            desk_keep_m = torch.clamp((yy_n[:, :, :, w_left:] - 0.78) / 0.08, 0.0, 1.0)
            bg_right = torch.lerp(bg_grad_r, raw_right, desk_keep_m)
            joined_mc = torch.cat([left_sub, bg_right], dim=3)
            seam_m = torch.exp(-(((xx_n - 0.50) / 0.06) ** 2))
            bchw = torch.lerp(joined_mc, _gaussian_blur_2d(joined_mc, 8.0), seam_m)
        if has_vid_scene:
            zones = _compute_neural_anatomy_zones(bchw, dock_cfg=dock_cfg)
            face_inner = _gaussian_blur_2d(torch.clamp(zones['face'] * 1.30 + zones['eyes'] * 1.55 + zones['mouth'] * 1.40, 0.0, 1.0), 4.5)
            bchw = torch.lerp(bchw, _gaussian_blur_2d(bchw, 9.5), torch.clamp(face_inner * 0.76, 0.0, 0.85))
        return torch.clamp(bchw, 0.0, 1.0).permute(0, 2, 3, 1).contiguous().detach().cpu()
    except Exception:
        return src_bhwc


def _restore_i2i_orc_tusks_bhwc(decoded_bhwc: torch.Tensor, ref_bhwc: torch.Tensor, style_low: str='realism', dock_cfg: dict=None, has_orc_tusks: bool=False, has_multi_cast: bool=False) -> torch.Tensor:
    if not has_orc_tusks:
        return decoded_bhwc
    if not isinstance(decoded_bhwc, torch.Tensor) or decoded_bhwc.ndim != 4 or not isinstance(ref_bhwc, torch.Tensor) or ref_bhwc.ndim != 4:
        return decoded_bhwc
    try:
        import torch.nn.functional as F
        dev = comfy.model_management.get_torch_device() if torch.cuda.is_available() else torch.device('cpu')
        s_low = str(style_low or 'realism').strip().lower()
        dec_bchw = decoded_bhwc[:1, :, :, :3].to(device=dev, dtype=torch.float32).permute(0, 3, 1, 2).contiguous()
        src_bchw = ref_bhwc[:1, :, :, :3].to(device=dev, dtype=torch.float32).permute(0, 3, 1, 2).contiguous()
        (ih, iw) = (int(dec_bchw.shape[-2]), int(dec_bchw.shape[-1]))
        if int(src_bchw.shape[-2]) != ih or int(src_bchw.shape[-1]) != iw:
            src_bchw = F.interpolate(src_bchw, size=(ih, iw), mode='bilinear', align_corners=False)
        zones = _compute_neural_anatomy_zones(src_bchw, dock_cfg=dock_cfg)
        zones_dec = _compute_neural_anatomy_zones(dec_bchw, dock_cfg=dock_cfg)
        (sr, sg, sb) = (src_bchw[:, 0:1], src_bchw[:, 1:2], src_bchw[:, 2:3])
        (dr, dg, db) = (dec_bchw[:, 0:1], dec_bchw[:, 1:2], dec_bchw[:, 2:3])
        src_lum = 0.299 * sr + 0.587 * sg + 0.114 * sb
        dec_lum = 0.299 * dr + 0.587 * dg + 0.114 * db
        src_bg_lum = _gaussian_blur_2d(src_lum, 9.5)
        src_fine_lum = _gaussian_blur_2d(src_lum, 1.6)
        src_red_ex = sr - 0.5 * (sg + sb)
        dec_red_ex = dr - 0.5 * (dg + db)
        src_bg_red = _gaussian_blur_2d(src_red_ex, 9.5)
        ref_skin_core = torch.clamp(zones['base_skin'] * (zones['face'] + zones['torso'] + zones['pelvic']), 0.0, 1.0)
        dec_skin_core = torch.clamp(zones_dec['base_skin'] * (zones_dec['face'] + zones_dec['torso'] + zones_dec['pelvic']), 0.0, 1.0)
        sk_sum = float(ref_skin_core.sum().item())
        dec_sk_sum = float(dec_skin_core.sum().item())
        if sk_sum > 64.0 and dec_sk_sum > 64.0:
            mean_sr = float((sr * ref_skin_core).sum().item() / sk_sum)
            mean_sg = max(0.04, float((sg * ref_skin_core).sum().item() / sk_sum))
            mean_sb = max(0.04, float((sb * ref_skin_core).sum().item() / sk_sum))
            mean_slum = max(0.06, 0.299 * mean_sr + 0.587 * mean_sg + 0.114 * mean_sb)
            mean_dr = float((dr * dec_skin_core).sum().item() / dec_sk_sum)
            mean_dg = max(0.04, float((dg * dec_skin_core).sum().item() / dec_sk_sum))
            mean_db = max(0.04, float((db * dec_skin_core).sum().item() / dec_sk_sum))
            mean_dlum = max(0.06, 0.299 * mean_dr + 0.587 * mean_dg + 0.114 * mean_db)
            is_crimson_ref = bool(has_orc_tusks) and (mean_sr - mean_sg) > 0.165 and (mean_sr / mean_sg) > 1.50
            is_green_ref = bool(has_orc_tusks) and (mean_sg - mean_sr) > 0.055 and (mean_sg - mean_sb) > 0.075
            is_blue_ref = bool(has_orc_tusks) and (mean_sb - mean_sr) > 0.085 and (mean_sb - mean_sg) > 0.045
            chroma_drift = abs(mean_sr / mean_slum - mean_dr / mean_dlum) + abs(mean_sg / mean_slum - mean_dg / mean_dlum) + abs(mean_sb / mean_slum - mean_db / mean_dlum)
            if (is_crimson_ref or is_green_ref or is_blue_ref) and chroma_drift > 0.14:
                xx_n = torch.linspace(0.0, 1.0, steps=iw, device=dev, dtype=torch.float32).view(1, 1, 1, iw)
                char_x_gate = torch.sigmoid((xx_n - 0.08) * 32.0) * torch.sigmoid((0.75 - xx_n) * 32.0)
                anat_dec = torch.clamp(zones_dec['base_skin'] * 0.95 + zones_dec['face'] + zones_dec['torso'] + zones_dec['pelvic'] + zones_dec['hands'], 0.0, 1.0)
                warm_tan_skin = (
                    torch.clamp((dr - dg - 0.035) * 9.0, 0.0, 1.0)
                    * torch.clamp((dr - db - 0.065) * 7.0, 0.0, 1.0)
                    * torch.clamp((dg - db + 0.008) * 11.0, 0.0, 1.0)
                )
                mid_lum_gate = torch.clamp((dec_lum - 0.075) / 0.055, 0.0, 1.0) * torch.clamp((0.80 - dec_lum) / 0.12, 0.0, 1.0)
                not_eyes_dec = torch.clamp(1.0 - zones_dec['eyes'] * 3.2, 0.0, 1.0)
                pigment_skin_m = _gaussian_blur_2d(anat_dec * warm_tan_skin * mid_lum_gate * not_eyes_dec * char_x_gate, 0.95)
                if has_multi_cast:
                    pigment_skin_m = pigment_skin_m * torch.sigmoid((0.52 - xx_n) * 24.0)
                if is_crimson_ref:
                    g_tgt = torch.minimum(dg * 0.48, db * 0.92)
                    b_tgt = db * 0.80
                    r_tgt = torch.clamp(dr * 1.26 + (dg - g_tgt) * 0.90, 0.0, 0.94)
                else:
                    r_tgt = torch.clamp(dec_lum * (mean_sr / mean_slum), 0.0, 0.96)
                    g_tgt = torch.clamp(dec_lum * (mean_sg / mean_slum), 0.0, 0.96)
                    b_tgt = torch.clamp(dec_lum * (mean_sb / mean_slum), 0.0, 0.96)
                pigment_rgb = torch.cat([r_tgt, g_tgt, b_tgt], dim=1)
                chroma_str = 0.88 if s_low in ('anime', 'cartoonish') else 0.56
                dec_bchw = torch.lerp(dec_bchw, pigment_rgb, torch.clamp(pigment_skin_m * chroma_str, 0.0, 0.90))
                (dr, dg, db) = (dec_bchw[:, 0:1], dec_bchw[:, 1:2], dec_bchw[:, 2:3])
                dec_lum = 0.299 * dr + 0.587 * dg + 0.114 * db
                dec_red_ex = dr - 0.5 * (dg + db)
        mouth_zone = torch.clamp(zones['mouth'] * (1.0 - zones['eyes'] * 3.0), 0.0, 1.0)
        if has_multi_cast:
            xx_px = torch.linspace(0.0, 1.0, steps=iw, device=dev, dtype=torch.float32).view(1, 1, 1, iw)
            mouth_zone = mouth_zone * torch.sigmoid((0.52 - xx_px) * 24.0)
        if float(mouth_zone.max().item()) <= 0.04:
            return torch.clamp(dec_bchw.permute(0, 2, 3, 1).contiguous().detach().cpu(), 0.0, 1.0)
        not_red_skin = torch.maximum(
            torch.clamp((src_bg_red - src_red_ex - 0.012) / 0.080, 0.0, 1.0),
            torch.clamp((0.26 - src_red_ex) / 0.12, 0.0, 1.0),
        )
        tusk_ivory_core = (
            torch.clamp((src_lum - src_bg_lum - 0.016) / 0.055, 0.0, 1.0)
            * torch.clamp((src_lum - 0.18) / 0.14, 0.0, 1.0)
            * not_red_skin
            * mouth_zone
        )
        if not has_orc_tusks and float(tusk_ivory_core.max().item()) < 0.25:
            return torch.clamp(dec_bchw.permute(0, 2, 3, 1).contiguous().detach().cpu(), 0.0, 1.0)
        yy_g = torch.arange(ih, device=dev, dtype=torch.float32).view(1, 1, ih, 1)
        xx_g = torch.arange(iw, device=dev, dtype=torch.float32).view(1, 1, 1, iw)
        dec_mouth_z = torch.clamp(zones_dec['mouth'] * (1.0 - zones_dec['eyes'] * 3.0), 0.0, 1.0)
        tusk_w_sum = float(tusk_ivory_core.sum().item())
        s_m_sum = float(mouth_zone.sum().item())
        s_mcx = float((tusk_ivory_core * xx_g).sum().item() / tusk_w_sum) if tusk_w_sum > 4.0 else float((mouth_zone * xx_g).sum().item() / max(1.0, s_m_sum))
        s_mcy = float((tusk_ivory_core * yy_g).sum().item() / tusk_w_sum) if tusk_w_sum > 4.0 else float((mouth_zone * yy_g).sum().item() / max(1.0, s_m_sum))
        d_mcx = s_mcx
        d_mcy = s_mcy
        d_eye_span = max(24.0, float(min(ih, iw)) * 0.048)
        d_head_dx = 0.0
        kpt_dec = _detect_skeletal_keypoints_rcnn(dec_bchw[0], conf_thresh=0.35)
        if kpt_dec:
            kp0 = kpt_dec[0]
            (d_nose, d_le, d_re) = (kp0[0], kp0[1], kp0[2])
            d_eye_span = max(18.0, math.hypot(float(d_le[0] - d_re[0]), float(d_le[1] - d_re[1])))
            eye_mx = 0.5 * float(d_le[0] + d_re[0])
            eye_my = 0.5 * float(d_le[1] + d_re[1])
            vx_en = float(d_nose[0]) - eye_mx
            vy_en = max(8.0, float(d_nose[1]) - eye_my)
            d_head_dx = max(-0.35, min(0.35, vx_en / max(12.0, vy_en)))
            d_mcx = float(d_nose[0]) + 0.38 * vx_en
            d_mcy = float(d_nose[1]) + max(0.38 * vy_en, 0.34 * d_eye_span)
        elif float(dec_mouth_z.sum().item()) > 16.0:
            d_m_sum = float(dec_mouth_z.sum().item())
            d_mcx = float((dec_mouth_z * xx_g).sum().item() / d_m_sum)
            d_mcy = float((dec_mouth_z * yy_g).sum().item() / d_m_sum)
        shift_dx = max(-48.0, min(48.0, d_mcx - s_mcx))
        shift_dy = max(-42.0, min(48.0, d_mcy - s_mcy))
        if abs(shift_dx) > 1.0 or abs(shift_dy) > 1.0:
            gy_norm = (yy_g - shift_dy) / max(1.0, float(ih - 1)) * 2.0 - 1.0
            gx_norm = (xx_g - shift_dx) / max(1.0, float(iw - 1)) * 2.0 - 1.0
            grid = torch.stack([gx_norm.expand(1, ih, iw), gy_norm.expand(1, ih, iw)], dim=-1)
            tusk_ivory_core = F.grid_sample(tusk_ivory_core, grid, mode='bilinear', padding_mode='zeros', align_corners=True)
            src_bchw = F.grid_sample(src_bchw, grid, mode='bilinear', padding_mode='border', align_corners=True)
            src_lum = F.grid_sample(src_lum, grid, mode='bilinear', padding_mode='border', align_corners=True)
            src_bg_lum = F.grid_sample(src_bg_lum, grid, mode='bilinear', padding_mode='border', align_corners=True)
            src_fine_lum = F.grid_sample(src_fine_lum, grid, mode='bilinear', padding_mode='border', align_corners=True)
            src_red_ex = F.grid_sample(src_red_ex, grid, mode='bilinear', padding_mode='border', align_corners=True)
            mouth_zone = torch.clamp(F.grid_sample(mouth_zone, grid, mode='bilinear', padding_mode='zeros', align_corners=True), 0.0, 1.0)
        eff_mouth_gate = torch.maximum(mouth_zone, dec_mouth_z)
        if has_orc_tusks:
            half_w = d_eye_span * 0.24
            base_y = d_mcy + d_eye_span * 0.07
            tip_y = d_mcy - d_eye_span * 0.17
            tusk_rad = max(2.2, d_eye_span * 0.075)
            lx_b = d_mcx - half_w
            lx_t = lx_b + d_eye_span * (0.03 + 0.10 * d_head_dx)
            rx_b = d_mcx + half_w
            rx_t = rx_b - d_eye_span * (0.03 - 0.10 * d_head_dx)
            taper_y = torch.clamp((base_y + tusk_rad - yy_g) / max(3.0, base_y - tip_y + tusk_rad), 0.0, 1.0)
            sharp_cone = torch.clamp(1.15 - 0.55 * taper_y, 0.35, 1.0)
            l_tusk = _capsule_sdf_2d(yy_g.expand(1, 1, ih, iw), xx_g.expand(1, 1, ih, iw), base_y, lx_b, tip_y, lx_t, tusk_rad) * sharp_cone
            r_tusk = _capsule_sdf_2d(yy_g.expand(1, 1, ih, iw), xx_g.expand(1, 1, ih, iw), base_y, rx_b, tip_y, rx_t, tusk_rad) * sharp_cone
            synth_tusks = torch.clamp(torch.maximum(l_tusk, r_tusk) * torch.clamp(eff_mouth_gate * 2.5, 0.0, 1.0), 0.0, 1.0)
            tusk_ivory_core = torch.maximum(tusk_ivory_core * eff_mouth_gate, synth_tusks * 0.92)
            mouth_zone = eff_mouth_gate
        illum_ratio = torch.clamp(_gaussian_blur_2d(dec_lum, 12.0) / torch.clamp(_gaussian_blur_2d(src_lum, 12.0), min=0.08), 0.76, 1.35)
        lit_src = torch.clamp(src_bchw * illum_ratio, 0.0, 1.0)
        if s_low in ('anime', 'cartoonish'):
            tusk_core_2d = _gaussian_blur_2d(torch.clamp((tusk_ivory_core - 0.11) / 0.30, 0.0, 1.0), 0.50)
            tusk_core_2d = torch.clamp((tusk_core_2d - 0.06) / 0.46, 0.0, 1.0) * mouth_zone
            tusk_dilated_2d = _gaussian_blur_2d(tusk_core_2d, 1.45)
            tusk_ink_2d = torch.clamp((tusk_dilated_2d - tusk_core_2d) * 2.9, 0.0, 1.0) * mouth_zone
            ivory_hi = torch.cat([torch.full_like(sr, 0.96), torch.full_like(sg, 0.93), torch.full_like(sb, 0.86)], dim=1)
            ivory_mid = torch.cat([torch.full_like(sr, 0.80), torch.full_like(sg, 0.75), torch.full_like(sb, 0.66)], dim=1)
            step_hi = torch.sigmoid((src_lum - src_bg_lum - 0.035) * 36.0)
            cel_tusk = torch.clamp(torch.lerp(ivory_mid, ivory_hi, step_hi) * torch.clamp(illum_ratio, 0.86, 1.16), 0.0, 1.0)
            ink_col = torch.clamp(dec_bchw * 0.10, 0.0, 0.15)
            out_bchw = torch.lerp(dec_bchw, ink_col, torch.clamp(tusk_ink_2d * 0.94, 0.0, 0.95))
            out_bchw = torch.lerp(out_bchw, cel_tusk, torch.clamp(tusk_core_2d * 0.97, 0.0, 0.98))
            return torch.clamp(out_bchw.permute(0, 2, 3, 1).contiguous().detach().cpu(), 0.0, 1.0)
        tusk_dilated = _gaussian_blur_2d(tusk_ivory_core, 1.55)
        tusk_rim_dark = torch.clamp((tusk_dilated - tusk_ivory_core) * 2.4, 0.0, 1.0) * mouth_zone
        tusk_struct_m = _gaussian_blur_2d(torch.clamp(tusk_ivory_core * 1.65 + tusk_rim_dark * 0.82, 0.0, 1.0), 0.60)
        luma_loss = torch.clamp((src_lum - dec_lum + 0.025) / 0.065, 0.68 if has_orc_tusks else 0.0, 1.0)
        red_humanize = torch.clamp((dec_red_ex - src_red_ex + 0.015) / 0.070, 0.64 if has_orc_tusks else 0.0, 1.0)
        need_restore = torch.maximum(luma_loss, red_humanize)
        bone_ivory = torch.cat([torch.full_like(sr, 0.92), torch.full_like(sg, 0.88), torch.full_like(sb, 0.80)], dim=1) * torch.clamp(illum_ratio, 0.82, 1.18)
        base_tusk_col = torch.lerp(bone_ivory, lit_src, torch.clamp((src_lum - 0.35) * 2.5, 0.0, 0.75))
        if s_low in ('unreal-engine-5', 'dark-fantasy-cgi', 'dark-fantasy-real', 'dark-fantasy'):
            ridge_spec = torch.clamp((src_lum - src_fine_lum) * 2.4, -0.06, 0.18)
            bone_tint = torch.cat([base_tusk_col[:, 0:1] * 1.04 + ridge_spec, base_tusk_col[:, 1:2] * 1.02 + ridge_spec, base_tusk_col[:, 2:3] * 0.96 + ridge_spec * 0.85], dim=1)
            tusk_stylized = torch.clamp(bone_tint, 0.0, 1.0)
        else:
            ridge_micro = (src_bchw - _gaussian_blur_2d(src_bchw, 1.2)) * 1.25
            tusk_stylized = torch.clamp(base_tusk_col + ridge_micro, 0.0, 1.0)
        eff_alpha = torch.clamp(tusk_struct_m * need_restore * 0.96, 0.0, 0.98)
        out_bchw = torch.lerp(dec_bchw, tusk_stylized, eff_alpha)
        return torch.clamp(out_bchw.permute(0, 2, 3, 1).contiguous().detach().cpu(), 0.0, 1.0)
    except Exception:
        return decoded_bhwc


def _prompt_requests_skin_tone_override(raw_prompt: str) -> bool:
    txt = str(raw_prompt or '').strip()
    if not txt:
        return False
    skin_pat = (
        r'(?i)\b(?:'
        r'(?:pale|fair|porcelain|ivory|alabaster|milky|tan|tanned|sun[-\s]?tanned|sun[-\s]?kissed|sunburn(?:ed)?|'
        r'bronze|bronzed|olive|caramel|brown|dark|ebony|black|mahogany|obsidian|ash(?:en)?|grey|gray|'
        r'green|emerald|blue|azure|indigo|cyan|red|crimson|scarlet|purple|violet|lavender|pink|golden|metallic|silver)'
        r'[-\s]+(?:skin(?:ned)?|complexion|epidermis)'
        r'|skin\s+(?:tone|color|colour|pigment|complexion)\b'
        r'|(?:sun[-\s]?tanned|tanned|sunburned|albino|goblin|drow|orc|troll|ogre|smurf|na\'vi)\b'
        r'|(?:hudf[aä]rg|hudton|m[oö]rkhyad|ljushyad|solbr[aä]nd|(?:blek|m[oö]rk|brun|svart|gr[oö]n|bl[aå]|r[oö]d|lila|guldf[aä]rgad)\s+hud)\b'
        r')'
    )
    return bool(re.search(skin_pat, txt))


def _harmonize_2d_i2i_skin_albedo_bhwc(decoded_bhwc: torch.Tensor, ref_bhwc: torch.Tensor, style_low: str='anime', dock_cfg: dict=None, has_multi_cast: bool=False, raw_prompt: str='') -> torch.Tensor:
    if has_multi_cast or _prompt_requests_skin_tone_override(raw_prompt) or not isinstance(decoded_bhwc, torch.Tensor) or decoded_bhwc.ndim != 4 or not isinstance(ref_bhwc, torch.Tensor) or ref_bhwc.ndim != 4:
        return decoded_bhwc
    s_low = str(style_low or 'realism').strip().lower()
    if s_low not in ('anime', 'cartoonish'):
        return decoded_bhwc
    try:
        import torch.nn.functional as F
        dev = comfy.model_management.get_torch_device() if torch.cuda.is_available() else torch.device('cpu')
        dec_bchw = decoded_bhwc[:1, :, :, :3].to(device=dev, dtype=torch.float32).permute(0, 3, 1, 2).contiguous()
        src_bchw = ref_bhwc[:1, :, :, :3].to(device=dev, dtype=torch.float32).permute(0, 3, 1, 2).contiguous()
        (ih, iw) = (int(dec_bchw.shape[-2]), int(dec_bchw.shape[-1]))
        if int(src_bchw.shape[-2]) != ih or int(src_bchw.shape[-1]) != iw:
            src_bchw = F.interpolate(src_bchw, size=(ih, iw), mode='bilinear', align_corners=False)
        zones_src = _compute_neural_anatomy_zones(src_bchw, dock_cfg=dock_cfg)
        zones_dec = _compute_neural_anatomy_zones(dec_bchw, dock_cfg=dock_cfg)
        src_lum = 0.299 * src_bchw[:, 0:1] + 0.587 * src_bchw[:, 1:2] + 0.114 * src_bchw[:, 2:3]
        dec_lum = 0.299 * dec_bchw[:, 0:1] + 0.587 * dec_bchw[:, 1:2] + 0.114 * dec_bchw[:, 2:3]
        src_chr = torch.amax(src_bchw, dim=1, keepdim=True) - torch.amin(src_bchw, dim=1, keepdim=True)
        dec_chr = torch.amax(dec_bchw, dim=1, keepdim=True) - torch.amin(dec_bchw, dim=1, keepdim=True)
        src_m = torch.clamp((zones_src['face'] * 1.15 + zones_src['torso'] * 0.65 + zones_src['base_skin'] * 0.45) * (1.0 - zones_src['eyes'] * 2.2 - zones_src['mouth'] * 1.8), 0.0, 1.0)
        src_m = src_m * ((src_lum > 0.08) & (src_lum < 0.95) & (src_chr < 0.52)).float()
        dec_raw = torch.clamp(zones_dec['face'] * 1.10 + zones_dec['torso'] * 0.85 + zones_dec['hands'] * 0.80 + zones_dec['pelvic'] * 0.65 + zones_dec['base_skin'] * 0.75, 0.0, 1.0)
        not_em = torch.clamp(1.0 - zones_dec['eyes'] * 2.4 - zones_dec['mouth'] * 1.8, 0.0, 1.0)
        dec_m = dec_raw * not_em * ((dec_lum > 0.08) & (dec_lum < 0.94) & (dec_chr < 0.52)).float()
        if float(src_m.sum().item()) < 32.0 or float(dec_m.sum().item()) < 32.0:
            return decoded_bhwc
        src_mean = (src_bchw * src_m).sum(dim=(2, 3), keepdim=True) / torch.clamp(src_m.sum(dim=(2, 3), keepdim=True), min=1.0)
        dec_mean = (dec_bchw * dec_m).sum(dim=(2, 3), keepdim=True) / torch.clamp(dec_m.sum(dim=(2, 3), keepdim=True), min=1.0)
        gain_rgb = torch.clamp(src_mean / torch.clamp(dec_mean, min=0.06), 0.72, 1.42)
        src_lum_mean = float((0.299 * src_mean[:, 0] + 0.587 * src_mean[:, 1] + 0.114 * src_mean[:, 2]).mean().item())
        ink_floor = min(0.14, max(0.04, src_lum_mean * 0.52))
        ink_shield = torch.clamp((dec_lum - ink_floor) / 0.10, 0.0, 1.0)
        not_vivid = torch.clamp((0.54 - dec_chr) / 0.14, 0.0, 1.0)
        eff_mask = _gaussian_blur_2d(torch.clamp(dec_raw * not_em * not_vivid, 0.0, 1.0), 1.6) * ink_shield * 0.42
        cal_bchw = torch.clamp(dec_bchw * torch.lerp(torch.ones_like(gain_rgb), gain_rgb, eff_mask), 0.0, 1.0)
        return cal_bchw.permute(0, 2, 3, 1).contiguous().detach().cpu()
    except Exception:
        return decoded_bhwc


def _blend_i2i_reference_beauty_bhwc(decoded_bhwc: torch.Tensor, ref_bhwc: torch.Tensor, style_low: str='realism', raw_denoise: float=0.75, dock_cfg: dict=None, age_years: int=25, has_multi_cast: bool=False) -> torch.Tensor:
    if not isinstance(decoded_bhwc, torch.Tensor) or decoded_bhwc.ndim != 4:
        return decoded_bhwc
    yrs = max(18, min(95, int(age_years or 25)))
    s_low = str(style_low or 'realism').strip().lower()
    if s_low in ('cartoonish', 'anime', 'semi-real', 'dark-fantasy-real', 'dark-fantasy-cgi', 'dark-fantasy', 'unreal-engine-5'):
        return decoded_bhwc
    if s_low != 'original' and float(raw_denoise) >= 0.78:
        return decoded_bhwc
    try:
        import torch.nn.functional as F
        dev = comfy.model_management.get_torch_device() if torch.cuda.is_available() else torch.device('cpu')
        dec_bchw = decoded_bhwc[:1, :, :, :3].to(device=dev, dtype=torch.float32).permute(0, 3, 1, 2).contiguous()
        dock_lock = float(dock_cfg.get('reference_face_lock_strength', 0.78)) if isinstance(dock_cfg, dict) else 0.78
        if dock_lock <= 0.01:
            return decoded_bhwc
        (ih, iw) = (max(1, int(dec_bchw.shape[-2])), max(1, int(dec_bchw.shape[-1])))
        zones = _compute_neural_anatomy_zones(dec_bchw, dock_cfg=dock_cfg)
        (dec_r, dec_g, dec_b) = (dec_bchw[:, 0:1], dec_bchw[:, 1:2], dec_bchw[:, 2:3])
        dec_lum = (0.299 * dec_r + 0.587 * dec_g + 0.114 * dec_b).clamp(0.02, 0.98)
        lead_gate = torch.ones((1, 1, ih, iw), device=dev, dtype=torch.float32)
        if has_multi_cast:
            xx_px = torch.linspace(0.0, 1.0, steps=iw, device=dev, dtype=torch.float32).view(1, 1, 1, iw)
            lead_gate = torch.sigmoid((0.50 - xx_px) * 28.0)
        ny_px = torch.linspace(0.0, 1.0, steps=ih, device=dev, dtype=torch.float32).view(1, 1, ih, 1)
        upper_head_gate = torch.clamp((0.35 - ny_px) / 0.08, 0.0, 1.0)
        body_excl = torch.clamp(zones['torso'] * 1.45 + zones['pelvic'] * 1.5 + zones['hands'] * 1.25, 0.0, 1.0)
        face_raw = _gaussian_blur_2d(torch.clamp((zones['face'] + 0.85 * zones['eyes']) * (1.0 - body_excl) * upper_head_gate, 0.0, 1.0), 2.5)
        face_peak = torch.clamp(face_raw.amax(dim=(-2, -1), keepdim=True), min=0.15)
        face_m = torch.clamp((face_raw / face_peak) * (1.0 - body_excl) * upper_head_gate, 0.0, 1.0) * lead_gate
        dec_ivory = torch.clamp((dec_lum - 0.22) * 4.2, 0.0, 1.0) * torch.clamp(1.0 - (dec_r - dec_g - 0.08) * 3.2, 0.0, 1.0)
        raw_tusk = _gaussian_blur_2d(dec_ivory, 1.8)
        tusk_shield = torch.clamp(zones['mouth'] * raw_tusk * 2.1, 0.0, 0.92)
        effective_face_m = face_m * (1.0 - tusk_shield)
        dec_low = _gaussian_blur_2d(dec_bchw, 2.4)
        dec_very_low = _gaussian_blur_2d(dec_bchw, 5.2)
        dec_mid = dec_low - dec_very_low
        dec_high = dec_bchw - dec_low
        if isinstance(ref_bhwc, torch.Tensor) and ref_bhwc.ndim == 4:
            ref_bchw = ref_bhwc[:1, :, :, :3].to(device=dev, dtype=torch.float32).permute(0, 3, 1, 2).contiguous()
            if int(ref_bchw.shape[-2]) != ih or int(ref_bchw.shape[-1]) != iw:
                ref_bchw = F.interpolate(ref_bchw, size=(ih, iw), mode='bilinear', align_corners=False)
            ref_high = ref_bchw - _gaussian_blur_2d(ref_bchw, 2.2)
            skin_union = torch.clamp((zones['base_skin'] * 0.85 + zones['face'] + zones['torso'] * 0.75) * (1.0 - tusk_shield), 0.0, 1.0) * lead_gate
            hf_gain = 0.42 if s_low == 'original' else 0.24
            dec_bchw = torch.clamp(dec_bchw + ref_high * (hf_gain * skin_union), 0.0, 1.0)
        if yrs <= 24:
            cheek_lift = effective_face_m * (1.0 - zones['eyes']) * 0.010
            blended_face = torch.clamp(dec_bchw + dec_high * (0.08 * effective_face_m) + cheek_lift, 0.0, 1.0)
            face_blend_cap = 0.20
        elif yrs <= 35:
            blended_face = torch.clamp(dec_bchw + dec_mid * (0.05 * effective_face_m) + dec_high * (0.08 * effective_face_m), 0.0, 1.0)
            face_blend_cap = 0.22
        else:
            blended_face = torch.clamp(dec_bchw + dec_mid * (0.08 * effective_face_m) + dec_high * (0.12 * effective_face_m), 0.0, 1.0)
            face_blend_cap = 0.26
        out_bchw = torch.lerp(dec_bchw, blended_face, torch.clamp(effective_face_m, 0.0, face_blend_cap))
        return torch.clamp(out_bchw.permute(0, 2, 3, 1).contiguous().detach().cpu(), 0.0, 1.0)
    except Exception:
        return decoded_bhwc


def _apply_live_action_photographic_physics_bhwc(image_bhwc: torch.Tensor, style_low: str='realism', seed: int=42, dock_cfg: dict=None, age_years: int=25, ref_background: torch.Tensor=None, horizon_relight_match: float=0.0) -> torch.Tensor:
    if not isinstance(image_bhwc, torch.Tensor) or image_bhwc.ndim != 4:
        return image_bhwc
    relight_str = max(0.0, min(1.0, float(horizon_relight_match or 0.0)))
    if relight_str <= 0.01 or not isinstance(ref_background, torch.Tensor) or ref_background.ndim < 3 or float(ref_background.abs().max().item()) <= 1e-04:
        return image_bhwc
    try:
        import torch.nn.functional as F
        dev = comfy.model_management.get_torch_device() if torch.cuda.is_available() else torch.device('cpu')
        bchw = image_bhwc[:1, :, :, :3].to(device=dev, dtype=torch.float32).permute(0, 3, 1, 2).contiguous()
        (ih, iw) = (int(bchw.shape[-2]), int(bchw.shape[-1]))
        zones = _compute_neural_anatomy_zones(bchw, dock_cfg=dock_cfg)
        bg_t = ref_background.detach().to(device=dev, dtype=torch.float32)
        if bg_t.ndim == 3:
            bg_t = bg_t.unsqueeze(0)
        bg_bchw = bg_t[:1, :, :, :3].permute(0, 3, 1, 2).contiguous()
        if int(bg_bchw.shape[-2]) != ih or int(bg_bchw.shape[-1]) != iw:
            bg_bchw = F.interpolate(bg_bchw, size=(ih, iw), mode='bilinear', align_corners=False)
        fg_union = _gaussian_blur_2d(torch.clamp(zones['base_skin'] + zones['face'] + zones['torso'] + zones['pelvic'] + zones['hands'] + zones['feet'], 0.0, 1.0), 4.0)
        rim_band = torch.clamp(_gaussian_blur_2d(fg_union, 6.0) - fg_union * 0.82, 0.0, 1.0)
        bg_amb = bg_bchw.mean(dim=(2, 3), keepdim=True)
        fg_amb = (bchw * fg_union).sum(dim=(2, 3), keepdim=True) / torch.clamp(fg_union.sum(dim=(2, 3), keepdim=True), min=16.0)
        relit_fg = torch.clamp(bchw + (bg_amb - fg_amb) * (relight_str * 0.28) + rim_band * (bg_bchw - bchw) * (relight_str * 0.42), 0.0, 1.0)
        out_bchw = torch.lerp(bchw, relit_fg, torch.clamp(fg_union + rim_band, 0.0, 1.0))
        return torch.clamp(out_bchw, 0.0, 1.0).permute(0, 2, 3, 1).contiguous().detach().cpu()
    except Exception:
        return image_bhwc


def _apply_frequency_separation_polish(image_bhwc: torch.Tensor, blur_radius: float=3.5, texture_strength: float=1.08, mix_opacity: float=0.65, dock_cfg: dict=None):
    if not isinstance(image_bhwc, torch.Tensor) or image_bhwc.ndim != 4:
        return (image_bhwc, image_bhwc)
    cfg = dict(dock_cfg) if isinstance(dock_cfg, dict) else {}
    w_face = float(cfg.get('lock_face_and_eyes', 1.0))
    w_hands = float(cfg.get('lock_hands_and_fingers', 1.25))
    w_torso = float(cfg.get('lock_torso_and_breasts', 1.1))
    w_pelvic = float(cfg.get('lock_intimate_pelvic_anatomy', 1.35))
    w_feet = float(cfg.get('lock_feet_and_toes', 1.15))
    shield_str = float(cfg.get('eye_and_contour_sharpness_shield', 0.9))
    dev = comfy.model_management.get_torch_device() if torch.cuda.is_available() else torch.device('cpu')
    out_chunks = []
    prev_chunks = []
    batch_step = 4
    for bi in range(0, image_bhwc.shape[0], batch_step):
        sub = image_bhwc[bi:bi + batch_step].to(device=dev, dtype=torch.float32)
        bchw = sub.permute(0, 3, 1, 2).contiguous()
        zones = _compute_neural_anatomy_zones(bchw, dock_cfg=cfg)
        prev_chunks.append(_render_anatomy_preview_bhwc(bchw, zones))
        if float(mix_opacity) <= 0.01:
            out_chunks.append(torch.clamp(sub.detach().cpu(), 0.0, 1.0))
            continue
        low_freq = _gaussian_blur_2d(bchw, max(0.5, float(blur_radius) * 0.45))
        high_freq = bchw - low_freq
        tex_gain = min(1.12, max(1.0, float(texture_strength)))
        recombined = torch.clamp(low_freq + high_freq * tex_gain, 0.0, 1.0)
        kpt_union = torch.clamp(w_face * zones['face'] + w_torso * zones['torso'] + w_pelvic * zones['pelvic'] + w_hands * zones['hands'] + w_feet * zones['feet'], 0.0, 1.0)
        anat_union = torch.clamp(zones['base_skin'] * (0.08 + 0.92 * kpt_union), 0.0, 1.0)
        red_blood_grad = torch.clamp((bchw[:, 0:1] - bchw[:, 1:2]) * 2.5, 0.0, 1.0) * zones['contour_shield']
        sharp_shield = torch.clamp(shield_str * (zones['eyes'] + 0.85 * zones['contour_shield'] + 0.90 * red_blood_grad + 0.95 * zones['mouth']), 0.0, 0.96)
        eff_alpha = _gaussian_blur_2d(anat_union * (1.0 - sharp_shield), 1.2) * min(0.18, float(mix_opacity) * 0.25)
        blended = (eff_alpha * recombined + (1.0 - eff_alpha) * bchw).permute(0, 2, 3, 1).contiguous()
        out_chunks.append(torch.clamp(blended.detach().cpu(), 0.0, 1.0))
    return (torch.cat(out_chunks, dim=0), torch.cat(prev_chunks, dim=0))

def _compose_multi_reference_canvas(primary_img, ref_person=None, ref_clothing=None, ref_background=None, target_w: int=1248, target_h: int=832, ootd_strength: float=0.85, preserve_neck_and_hands: bool=True, horizon_relight_match: float=0.55) -> torch.Tensor:
    def _to_bchw(t_in, w_out: int, h_out: int):
        if not isinstance(t_in, torch.Tensor) or t_in.ndim < 3:
            return None
        t = t_in.detach().cpu().float()
        if t.ndim == 3:
            t = t.unsqueeze(0)
        if float(t.abs().max().item()) <= 1e-04:
            return None
        bchw = t[:1, :, :, :3].movedim(-1, 1).contiguous()
        if int(bchw.shape[2]) != h_out or int(bchw.shape[3]) != w_out:
            bchw = comfy.utils.common_upscale(bchw, w_out, h_out, 'lanczos', 'center')
        return torch.clamp(bchw, 0.0, 1.0)

    w = max(64, int(target_w))
    h = max(64, int(target_h))
    p_bchw = _to_bchw(primary_img, w, h)
    r2_bchw = _to_bchw(ref_person, w, h)
    r3_bchw = _to_bchw(ref_clothing, w, h)
    r4_bchw = _to_bchw(ref_background, w, h)
    base_bchw = p_bchw if p_bchw is not None else (r4_bchw if r4_bchw is not None else (r2_bchw if r2_bchw is not None else r3_bchw))
    if base_bchw is None:
        return torch.zeros((1, h, w, 3), dtype=torch.float32, device='cpu')

    def _extract_subject_alpha(img_bchw: torch.Tensor) -> torch.Tensor:
        border_top = img_bchw[:, :, :max(2, h // 16), :].mean(dim=(2, 3), keepdim=True)
        border_left = img_bchw[:, :, :, :max(2, w // 16)].mean(dim=(2, 3), keepdim=True)
        border_right = img_bchw[:, :, :, -max(2, w // 16):].mean(dim=(2, 3), keepdim=True)
        bg_color = (border_top + border_left + border_right) / 3.0
        color_dist = (img_bchw - bg_color).abs().mean(dim=1, keepdim=True)
        color_mask = torch.clamp((color_dist - 0.05) / 0.16, 0.0, 1.0)
        yy = torch.linspace(-1.0, 1.0, h, device=img_bchw.device).view(1, 1, h, 1).expand(1, 1, h, w)
        xx = torch.linspace(-1.0, 1.0, w, device=img_bchw.device).view(1, 1, 1, w).expand(1, 1, h, w)
        spatial_prior = torch.clamp(1.0 - (xx / 0.68) ** 2 - ((yy - 0.08) / 0.88) ** 2, 0.0, 1.0)
        try:
            zones = _compute_neural_anatomy_zones(img_bchw)
            anat_m = torch.clamp(zones['base_skin'] + zones['face'] + zones['torso'] + zones['pelvic'] + zones['hands'] + zones['feet'], 0.0, 1.0)
        except Exception:
            anat_m = torch.zeros_like(color_mask)
        combined = torch.clamp(torch.maximum(anat_m, color_mask * (0.45 + 0.55 * spatial_prior)), 0.0, 1.0)
        if float(combined.mean().item()) < 0.08:
            combined = spatial_prior
        return _gaussian_blur_2d(combined, 6.0).clamp(0.0, 1.0)

    canvas = base_bchw.clone()
    if r4_bchw is not None and p_bchw is not None:
        fg_alpha = _extract_subject_alpha(p_bchw)
        hard_fg = _gaussian_blur_2d(torch.clamp((fg_alpha - 0.22) / 0.58, 0.0, 1.0), 2.5)
        relight_w = max(0.0, min(1.0, float(horizon_relight_match or 0.0))) * 0.28
        bg_mean = r4_bchw.mean(dim=(2, 3), keepdim=True)
        rim_band = torch.clamp(fg_alpha - hard_fg * 0.85, 0.0, 1.0)
        fg_relit = torch.clamp(
            p_bchw * (1.0 - relight_w * 0.45) + bg_mean * (relight_w * 0.45) + rim_band * (r4_bchw - p_bchw) * relight_w,
            0.0,
            1.0,
        )
        canvas = hard_fg * fg_relit + (1.0 - hard_fg) * r4_bchw
    elif r4_bchw is not None:
        canvas = r4_bchw.clone()

    if r3_bchw is not None:
        try:
            from .engine_ez_13_cinematrix_omni_reference_loader import warp_ootdiffusion_garment_to_subject
            canvas, _, _ = warp_ootdiffusion_garment_to_subject(
                canvas,
                r3_bchw,
                ootd_strength=float(ootd_strength if ootd_strength is not None else 0.85),
                preserve_neck_and_hands=bool(preserve_neck_and_hands),
            )
        except Exception:
            pass

    return torch.clamp(canvas.permute(0, 2, 3, 1).contiguous(), 0.0, 1.0)


_KREA2_KEYFRAME_VAULT = {
    'sig': None,
    'decoded_image': None,
    'stage3_out': None,
    'anatomy_preview_img': None,
    'ui_images': None,
    'keyframe_filename': '',
    'eff_seed': 0,
}


def _compute_krea2_generation_signature(bus: dict, eff_pos_str: str, style_low: str, rating_tier: str, eff_seed: int, seed_mode: str, handoff_percent: float, stage3_handoff_percent: float, stage1_steps: int, stage1_cfg: float, stage1_sampler_name: str, stage1_scheduler: str, stage2_steps: int, stage2_cfg: float, stage2_sampler_name: str, stage2_scheduler: str, final_width: int, final_height: int, upscale_method: str, i2i_denoise: float, enable_frequency_polish: bool, skin_blur_radius: float, skin_texture_strength: float, skin_polish_opacity: float, dock_cfg: dict, ref_tensors: tuple) -> str:
    import hashlib
    import json
    mode_low = str(seed_mode or 'auto_from_bus_or_local').strip().lower()
    include_seed = int(eff_seed) if ('use_local' in mode_low or 'sync_with' in mode_low) else 'auto_locked'
    ref_digests = []
    for rt in (ref_tensors or ()):
        if isinstance(rt, torch.Tensor) and rt.numel() > 0:
            ref_digests.append(f'{tuple(rt.shape)}:{float(rt.detach().float().mean().item()):.5f}')
        else:
            ref_digests.append('none')
    payload = [
        'v36_neutral_skin_albedo_with_prompt_override',
        str(bus.get('krea2_image_config_sig') or eff_pos_str),
        str(bus.get('krea2_loader_03_sig') or ''),
        str(bus.get('image_trigger_words') or ''),
        str(style_low),
        round(float(bus.get('color_saturation_strength', 0.80) or 0.80), 3),
        str(bus.get('subject_1_age') or ''),
        int(bus.get('subject_1_age_num') or 25),
        str(rating_tier),
        include_seed,
        round(float(handoff_percent), 3),
        round(float(stage3_handoff_percent), 3),
        int(stage1_steps),
        round(float(stage1_cfg), 3),
        str(stage1_sampler_name),
        str(stage1_scheduler),
        int(stage2_steps),
        round(float(stage2_cfg), 3),
        str(stage2_sampler_name),
        str(stage2_scheduler),
        int(final_width),
        int(final_height),
        str(upscale_method),
        round(float(i2i_denoise), 3),
        bool(enable_frequency_polish),
        round(float(skin_blur_radius), 3),
        round(float(skin_texture_strength), 3),
        round(float(skin_polish_opacity), 3),
        sorted((str(k), str(v)) for k, v in (dock_cfg or {}).items()),
        ref_digests,
    ]
    raw_json = json.dumps(payload, ensure_ascii=False)
    return hashlib.sha256(raw_json.encode('utf-8')).hexdigest()[:24]


def _try_load_cached_krea2_keyframe(krea_sig: str, force_reuse_latest: bool = False):
    from pathlib import Path
    import json
    import numpy as np
    from PIL import Image
    import folder_paths
    if isinstance(_KREA2_KEYFRAME_VAULT.get('decoded_image'), torch.Tensor):
        if force_reuse_latest or _KREA2_KEYFRAME_VAULT.get('sig') == krea_sig:
            return (
                _KREA2_KEYFRAME_VAULT['decoded_image'],
                _KREA2_KEYFRAME_VAULT['stage3_out'],
                _KREA2_KEYFRAME_VAULT['anatomy_preview_img'],
                list(_KREA2_KEYFRAME_VAULT.get('ui_images') or []),
                str(_KREA2_KEYFRAME_VAULT.get('keyframe_filename') or ''),
                int(_KREA2_KEYFRAME_VAULT.get('eff_seed') or 0),
            )
    try:
        temp_dir = Path(folder_paths.get_temp_directory())
        out_dir = Path(folder_paths.get_output_directory())
        meta_path = temp_dir / 'ez_krea2_last_keyframe_meta.json'
        cand_png = None
        meta_seed = 0
        ui_list = []
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding='utf-8'))
            if force_reuse_latest or meta.get('sig') == krea_sig:
                p = Path(str(meta.get('keyframe_path') or ''))
                if p.exists():
                    cand_png = p
                    meta_seed = int(meta.get('eff_seed') or 0)
                    ui_list = meta.get('ui_images') if isinstance(meta.get('ui_images'), list) else []
        if cand_png is None and force_reuse_latest and out_dir.exists():
            pngs = sorted(out_dir.glob('EZ_Krea2_Keyframe_*.png'), key=lambda x: x.stat().st_mtime, reverse=True)
            if pngs:
                cand_png = pngs[0]
        if cand_png is not None and cand_png.exists():
            pil_im = Image.open(str(cand_png)).convert('RGB')
            arr_f = np.asarray(pil_im, dtype=np.float32) / 255.0
            img_t = torch.from_numpy(arr_f).unsqueeze(0).contiguous()
            (h_px, w_px) = (int(img_t.shape[1]), int(img_t.shape[2]))
            dummy_s3 = {'samples': torch.zeros((1, 16, max(1, h_px // 8), max(1, w_px // 8)), dtype=torch.float32)}
            _KREA2_KEYFRAME_VAULT.update({'sig': krea_sig, 'decoded_image': img_t, 'stage3_out': dummy_s3, 'anatomy_preview_img': img_t.clone(), 'ui_images': ui_list, 'keyframe_filename': cand_png.name, 'eff_seed': meta_seed})
            return (img_t, dummy_s3, img_t.clone(), ui_list, cand_png.name, meta_seed)
    except Exception:
        pass
    return None


def _store_cached_krea2_keyframe(krea_sig: str, decoded_image: torch.Tensor, stage3_out: dict, anatomy_preview_img: torch.Tensor, ui_images: list, keyframe_path: str, eff_seed: int):
    from pathlib import Path
    import json
    import folder_paths
    fname = Path(str(keyframe_path)).name if keyframe_path else ''
    _KREA2_KEYFRAME_VAULT.update({
        'sig': krea_sig,
        'decoded_image': decoded_image.detach().cpu(),
        'stage3_out': stage3_out,
        'anatomy_preview_img': anatomy_preview_img.detach().cpu() if isinstance(anatomy_preview_img, torch.Tensor) else decoded_image.detach().cpu(),
        'ui_images': list(ui_images or []),
        'keyframe_filename': fname,
        'eff_seed': int(eff_seed),
    })
    try:
        temp_dir = Path(folder_paths.get_temp_directory())
        temp_dir.mkdir(parents=True, exist_ok=True)
        meta_path = temp_dir / 'ez_krea2_last_keyframe_meta.json'
        meta_path.write_text(json.dumps({'sig': krea_sig, 'keyframe_path': str(keyframe_path or ''), 'keyframe_filename': fname, 'ui_images': list(ui_images or []), 'eff_seed': int(eff_seed)}, ensure_ascii=False), encoding='utf-8')
    except Exception:
        pass


def _resolve_pipeline_video_model_metadata(bus: dict = None) -> dict:
    b = dict(bus) if isinstance(bus, dict) else {}
    vm_spec = b.get('civitai_video_model_spec') if isinstance(b.get('civitai_video_model_spec'), dict) else {}
    vl_spec = b.get('civitai_video_lora_spec') if isinstance(b.get('civitai_video_lora_spec'), dict) else {}
    spec_clean_vloras = [
        list(it) for it in (vl_spec.get('video_loras') or [])
        if isinstance(it, (list, tuple)) and len(it) >= 2 and str(it[0] or '').strip() not in ('', 'None')
    ]
    out = {
        'active_video_unet': str(b.get('active_video_unet') or b.get('video_unet_fl2va') or vm_spec.get('video_unet_fl2va') or '').strip(),
        'video_unet_fl2va': str(b.get('video_unet_fl2va') or b.get('active_video_unet') or vm_spec.get('video_unet_fl2va') or '').strip(),
        'video_unet_ref2va': str(b.get('video_unet_ref2va') or vm_spec.get('video_unet_ref2va') or '').strip(),
        'video_clip_name': str(b.get('video_clip_name') or vm_spec.get('video_clip_name') or '').strip(),
        'video_vae_name': str(b.get('video_vae_name') or vm_spec.get('video_vae_name') or '').strip(),
        'audio_vae_name': str(b.get('audio_vae_name') or vm_spec.get('audio_vae_name') or '').strip(),
        'active_video_loras': list(b.get('active_video_loras') or []),
        'video_turbo_lora': str(b.get('video_turbo_lora') or vl_spec.get('video_turbo_lora') or '').strip(),
    }
    try:
        from ..EZ_ADAPTERS.adapter_ez_05_cinematrix_video_lora_stack import EzCinematrixVideoLoaderAdapter
        cached_vm = getattr(EzCinematrixVideoLoaderAdapter, '_last_video_model_meta', None)
        if isinstance(cached_vm, dict):
            for k_vm, v_vm in cached_vm.items():
                if k_vm in out and (not out[k_vm] or out[k_vm] == 'None') and v_vm:
                    out[k_vm] = v_vm
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
                    if not isinstance(n_def, dict):
                        continue
                    c_type = str(n_def.get('class_type', ''))
                    n_in = n_def.get('inputs') if isinstance(n_def.get('inputs'), dict) else {}
                    if 'EZ_05' in c_type or 'VideoLoraStack' in c_type or 'VideoLoader' in c_type:
                        hub_mode_05 = str(n_in.get('remote_hub_mode', 'local_priority') or 'local_priority').strip().lower()
                        for fk in ('video_unet_fl2va', 'video_unet_ref2va', 'video_clip_name', 'video_vae_name', 'audio_vae_name'):
                            val_s = n_in.get(fk)
                            if isinstance(val_s, str) and val_s.strip() and val_s.strip() != 'None':
                                out[fk] = val_s.strip()
                        if out['video_unet_fl2va'] and out['video_unet_fl2va'] != 'None':
                            out['active_video_unet'] = out['video_unet_fl2va']
                        t_lora = n_in.get('video_turbo_lora_LOCKED')
                        if isinstance(t_lora, str) and t_lora.strip() and bool(n_in.get('enable_video_turbo_lora', True)):
                            out['video_turbo_lora'] = t_lora.strip()
                        g_loras = []
                        for idx_l in range(1, 5):
                            l_name = n_in.get(f'video_lora_{idx_l}')
                            l_en = bool(n_in.get(f'enable_video_lora_{idx_l}', True))
                            if l_en and isinstance(l_name, str) and l_name.strip() not in ('', 'None'):
                                g_loras.append([
                                    l_name.strip(),
                                    float(n_in.get(f'lora_{idx_l}_video_strength', 0.5) or 0.0),
                                    float(n_in.get(f'lora_{idx_l}_audio_strength', 0.0) or 0.0),
                                ])
                        if g_loras and (not hub_mode_05.startswith('hub_override') or not spec_clean_vloras):
                            out['active_video_loras'] = g_loras
                        elif not out['active_video_loras'] and spec_clean_vloras:
                            out['active_video_loras'] = spec_clean_vloras
                    elif ('EZ_10' in c_type or 'CivitAI' in c_type) and (not out['active_video_unet'] or out['active_video_unet'] == 'None'):
                        v_u10 = n_in.get('video_unet_fl2va')
                        if isinstance(v_u10, str) and v_u10.strip() not in ('', 'None'):
                            out['active_video_unet'] = v_u10.strip()
                            out['video_unet_fl2va'] = v_u10.strip()
    except Exception:
        pass
    if (not out['active_video_unet'] or out['active_video_unet'] == 'None'):
        try:
            from .engine_ez_05_cinematrix_video_lora_stack import get_dynamic_video_unets
            cand_unets = [u for u in get_dynamic_video_unets() if u and u != 'None']
            if cand_unets:
                out['active_video_unet'] = str(cand_unets[0])
                out['video_unet_fl2va'] = str(cand_unets[0])
        except Exception:
            pass
    return out


def _sanitize_bus_for_video_handoff(bus: dict) -> dict:
    import gc
    import torch
    import comfy.model_management
    if not isinstance(bus, dict):
        return {}
    clean_bus = dict(bus)
    clip_ref = clean_bus.pop('image_clip_obj', None)
    for img_only_key in (
        'image_trigger_words',
        'civitai_image_model_spec',
        'civitai_image_lora_spec',
        'krea2_loader_03_sig',
        'krea2_image_config_sig',
        'pre_encoded_pos_cond',
        'pre_encoded_neg_cond',
        'pre_encoded_pos_str',
        'pre_encoded_neg_str',
    ):
        clean_bus.pop(img_only_key, None)
    vid_lora_spec = clean_bus.get('civitai_video_lora_spec')
    if isinstance(vid_lora_spec, dict) and str(vid_lora_spec.get('modality', 'VIDEO')).upper() == 'VIDEO':
        v_loras = vid_lora_spec.get('video_loras') or []
        has_active_vid_lora = any((isinstance(it, (list, tuple)) and len(it) > 0 and str(it[0]) not in ('None', '')) for it in v_loras)
        if has_active_vid_lora and vid_lora_spec.get('trigger_words'):
            clean_bus['civitai_trigger_words'] = str(vid_lora_spec.get('trigger_words') or '').strip()
        else:
            clean_bus.pop('civitai_trigger_words', None)
    else:
        clean_bus.pop('civitai_trigger_words', None)
    if clip_ref is not None:
        del clip_ref
        if hasattr(comfy.model_management, 'soft_empty_cache'):
            comfy.model_management.soft_empty_cache()
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    return clean_bus

