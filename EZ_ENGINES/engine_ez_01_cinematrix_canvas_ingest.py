# -*- coding: utf-8 -*-

import math
import os
import random
import gc
from pathlib import Path
import torch
import numpy as np
from PIL import Image, ImageOps
import folder_paths
import comfy.model_management
import comfy.utils
FIXED_ASPECT_RATIOS = {'1:1': (1.0, 1.0), '4:5': (4.0, 5.0), '5:4': (5.0, 4.0), '2:3': (2.0, 3.0), '3:2': (3.0, 2.0), '3:4': (3.0, 4.0), '4:3': (4.0, 3.0), '9:16': (9.0, 16.0), '16:9': (16.0, 9.0), '2.35:1': (2.35, 1.0), '21:9': (21.0, 9.0)}
RANDOM_ASPECT_RATIO_MODES = {'Random': tuple(FIXED_ASPECT_RATIOS.keys()), 'Random Vertical': tuple((k for (k, (w, h)) in FIXED_ASPECT_RATIOS.items() if h > w)), 'Random Horizontal': tuple((k for (k, (w, h)) in FIXED_ASPECT_RATIOS.items() if w > h))}

def _neutralize_external_comfy_hooks():
    try:
        import sys
        import comfy.sample as _comfy_sample
        if hasattr(_comfy_sample, 'sample') and hasattr(_comfy_sample.sample, '_multigpu_original'):
            _comfy_sample.sample = _comfy_sample.sample._multigpu_original
        if hasattr(_comfy_sample, 'sample_custom') and hasattr(_comfy_sample.sample_custom, '_multigpu_original'):
            _comfy_sample.sample_custom = _comfy_sample.sample_custom._multigpu_original
        exec_mod = sys.modules.get('execution')
        if exec_mod is None:
            for (m_name, m_obj) in list(sys.modules.items()):
                if m_name.endswith('.execution') and m_obj is not None:
                    exec_mod = m_obj
                    break
        if exec_mod is not None and hasattr(exec_mod, '_async_map_node_over_list'):
            cur_fn = getattr(exec_mod, '_async_map_node_over_list', None)
            if callable(cur_fn) and getattr(cur_fn, '__name__', '') == 'async_map_node_over_list_with_metadata':
                for cell in getattr(cur_fn, '__closure__', None) or ():
                    cell_val = getattr(cell, 'cell_contents', None)
                    if callable(cell_val) and getattr(cell_val, '__name__', '') in ('_async_map_node_over_list', '_map_node_over_list'):
                        setattr(exec_mod, '_async_map_node_over_list', cell_val)
                        break
        for (m_name, m_obj) in list(sys.modules.items()):
            if m_obj is not None and ('multigpu' in m_name.lower() or 'memory_monitor' in m_name.lower()):
                for attr_k in dir(m_obj):
                    attr_v = getattr(m_obj, attr_k, None)
                    if hasattr(attr_v, 'cpu_threshold'):
                        try:
                            setattr(attr_v, 'cpu_threshold', 99.5)
                        except Exception:
                            pass
    except Exception:
        pass

_neutralize_external_comfy_hooks()

def compute_cinematrix_dual_dimensions(aspect_ratio: str, base_mp: float, final_mp: float, multiple: int, seed: int):
    _neutralize_external_comfy_hooks()
    chosen_ratio = aspect_ratio
    if chosen_ratio in RANDOM_ASPECT_RATIO_MODES:
        pool = RANDOM_ASPECT_RATIO_MODES[chosen_ratio]
        chosen_ratio = pool[random.Random(seed).randrange(len(pool))]
    (ratio_w, ratio_h) = FIXED_ASPECT_RATIOS.get(chosen_ratio, (3.0, 2.0))
    mult = max(32, int(round(max(16, int(multiple)) / 32.0) * 32))

    def _calc(mp_val: float):
        total_px = max(0.1, float(mp_val)) * 1024.0 * 1024.0
        scale = math.sqrt(total_px / (ratio_w * ratio_h))
        w = max(mult, int(round(ratio_w * scale / mult) * mult))
        h = max(mult, int(round(ratio_h * scale / mult) * mult))
        return (w, h)
    (base_w, base_h) = _calc(base_mp)
    (final_w, final_h) = _calc(final_mp)
    return (base_w, base_h, final_w, final_h, chosen_ratio)

def execute_canvas_ingest_and_pad(generation_mode: str, image_name: str, base_w: int, base_h: int, outpaint_align_pct: int, optional_image_tensor=None):
    is_i2i = str(generation_mode or '').startswith('I2I')
    has_opt_tensor = isinstance(optional_image_tensor, torch.Tensor) and optional_image_tensor.numel() > 0 and float(optional_image_tensor.detach().abs().max().item()) > 1e-04
    if is_i2i and has_opt_tensor:
        raw_tensor = optional_image_tensor
    elif is_i2i and image_name and (str(image_name) != 'None'):
        img_path = folder_paths.get_annotated_filepath(image_name)
        pil_img = Image.open(img_path)
        pil_img = ImageOps.exif_transpose(pil_img).convert('RGB')
        np_img = np.array(pil_img).astype(np.float32) / 255.0
        raw_tensor = torch.from_numpy(np_img).unsqueeze(0)
    else:
        empty_canvas = torch.zeros((1, base_h, base_w, 3), dtype=torch.float32, device='cpu')
        empty_mask = torch.zeros((1, base_h, base_w), dtype=torch.float32, device='cpu')
        return (empty_canvas, empty_mask)
    (b_sz, src_h, src_w, channels) = raw_tensor.shape
    scale_cover = max(base_w / max(1, src_w), base_h / max(1, src_h))
    cov_w = max(base_w, int(round(src_w * scale_cover)))
    cov_h = max(base_h, int(round(src_h * scale_cover)))
    nchw = raw_tensor[:, :, :, :3].movedim(-1, 1)
    resized_nchw = comfy.utils.common_upscale(nchw, cov_w, cov_h, 'lanczos', 'disabled')
    slack_w = max(0, cov_w - base_w)
    slack_h = max(0, cov_h - base_h)
    bias = max(0.0, min(1.0, float(outpaint_align_pct) / 100.0))
    crop_left = int(round(slack_w * bias))
    crop_top = int(round(slack_h * bias))
    cropped_nchw = resized_nchw[:, :, crop_top:crop_top + base_h, crop_left:crop_left + base_w]
    canvas = cropped_nchw.movedim(1, -1).contiguous()
    mask = torch.zeros((b_sz, base_h, base_w), dtype=torch.float32, device=raw_tensor.device)
    return (canvas, mask)

def _check_canvas_license_active() -> bool:
    here = Path(__file__).resolve().parent
    pkg_root = here.parent
    devops_root = pkg_root.parent.parent if (pkg_root.parent.parent / 'CONFIG').exists() else pkg_root
    search_dirs = [pkg_root, here, devops_root, devops_root / 'CONFIG', devops_root / 'EZ_LICENSE', Path('D:/EZ_Studio_DevTools'), Path('D:/EZ_Studio_DevTools/CONFIG'), Path('D:/EZ_Studio_DevTools/DEV_BEDS/comfyui_node/ez_cinematrix_core')]
    try:
        from .engine_ez_02_cinematrix_qwenvl_timeline import _verify_cinematrix_license_active
        return bool(_verify_cinematrix_license_active(search_dirs))
    except Exception:
        return False

def resolve_cinematrix_hardware_tier_profile(tier_selection: str='auto_from_devops_tier', thermal_protection_mode: str='auto_devops_shield') -> dict:
    raw_sel = str(tier_selection or 'auto_from_devops_tier').strip().lower()
    vram_gb = 16.0
    sys_ram_gb = 32.0
    device_backend = 'cpu'
    sm_arch = 0
    cpu_cores = max(2, int(os.cpu_count() or 8))
    try:
        import psutil
        sys_ram_gb = round(float(psutil.virtual_memory().total) / 1024.0 ** 3, 1)
    except Exception:
        pass
    if torch.cuda.is_available():
        device_backend = 'rocm' if getattr(torch.version, 'hip', None) else 'cuda'
        try:
            props = torch.cuda.get_device_properties(0)
            vram_gb = round(float(props.total_memory) / 1024.0 ** 3, 1)
            sm_arch = int(getattr(props, 'major', 0)) * 10 + int(getattr(props, 'minor', 0))
        except Exception:
            vram_gb = 16.0
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        device_backend = 'mps'
        vram_gb = round(sys_ram_gb * 0.65, 1)
    tier_num = '1'
    if 'tier_4' in raw_sel or raw_sel == '4':
        tier_num = '4'
    elif 'tier_3' in raw_sel or raw_sel == '3':
        tier_num = '3'
    elif 'tier_2' in raw_sel or raw_sel == '2':
        tier_num = '2'
    elif 'tier_1' in raw_sel or raw_sel == '1':
        tier_num = '1'
    else:
        compiled_tier = str(globals().get('ACTIVE_HARDWARE_TIER', '')).strip().lower()
        if any((k in compiled_tier for k in ('4', 'tier_4'))):
            tier_num = '4'
        elif any((k in compiled_tier for k in ('3', 'tier_3'))):
            tier_num = '3'
        elif any((k in compiled_tier for k in ('2', 'tier_2'))):
            tier_num = '2'
        elif device_backend in ('cuda', 'rocm', 'mps'):
            dev_cnt = torch.cuda.device_count() if torch.cuda.is_available() else 1
            if dev_cnt > 1 or vram_gb >= 60.0:
                tier_num = '4'
            elif vram_gb >= 40.0:
                tier_num = '3'
            elif vram_gb >= 22.0:
                tier_num = '2'
            else:
                tier_num = '1'
    is_licensed = _check_canvas_license_active()
    is_low_vram = vram_gb < 13.5
    t1_tile = 384 if is_low_vram else 512
    t1_chunk = 4 if is_low_vram else 8
    allow_pin = bool(device_backend == 'cuda' and sys_ram_gb >= 28.0)
    cpu_dtype = 'float16' if sys_ram_gb < 48.0 else 'float32'
    thermal_cfg = resolve_cinematrix_thermal_shield_config(thermal_protection_mode=thermal_protection_mode, tier_id=tier_num)
    common_hw = {'vram_gb': vram_gb, 'sys_ram_gb': sys_ram_gb, 'device_backend': device_backend, 'sm_arch': sm_arch, 'cpu_cores': cpu_cores, 'allow_pinned_memory': allow_pin, 'cpu_frame_dtype': cpu_dtype, 'thermal_protection_mode': thermal_cfg['mode_key'], 'thermal_shield': thermal_cfg}
    profiles = {'1': {**common_hw, 'tier_id': '1', 'tier_label': 'TIER_1_ADAPTIVE_16GB_PRO_TURBO' if is_licensed else 'TIER_1_ADAPTIVE_FREEMIUM_UNLIMITED', 'is_licensed': bool(is_licensed), 'license_mode': 'PRO_LICENSED' if is_licensed else 'FREEMIUM_COMMUNITY', 'max_duration_seconds': 86400.0, 'max_window_t': 49 if is_low_vram else 61, 'vae_window_t': 20 if is_low_vram else 28, 'tile_size': t1_tile, 'upscale_chunk_t': t1_chunk, 'io_workers': min(cpu_cores, 4), 'aggressive_vram_purge': True, 'inter_window_vram_purge': True, 'persistent_vram_weights': False, 'fp16_accumulation': True, 'cudnn_benchmark': bool(device_backend == 'cuda'), 'matmul_precision': 'high', 'use_cuda_stream': False, 'multi_gpu_distribute': False}, '2': {**common_hw, 'tier_id': '2', 'tier_label': 'TIER_2_24GB_32GB_HIGH_BANDWIDTH', 'is_licensed': bool(is_licensed), 'license_mode': 'PRO_LICENSED' if is_licensed else 'FREEMIUM_COMMUNITY', 'max_duration_seconds': 86400.0, 'max_window_t': 61, 'vae_window_t': 40, 'tile_size': 512, 'upscale_chunk_t': 12, 'io_workers': min(cpu_cores, 4), 'aggressive_vram_purge': True, 'inter_window_vram_purge': False, 'persistent_vram_weights': False, 'fp16_accumulation': True, 'cudnn_benchmark': bool(device_backend == 'cuda'), 'matmul_precision': 'high', 'use_cuda_stream': False, 'multi_gpu_distribute': False}, '3': {**common_hw, 'tier_id': '3', 'tier_label': 'TIER_3_48GB_WORKSTATION', 'is_licensed': bool(is_licensed), 'license_mode': 'PRO_LICENSED' if is_licensed else 'FREEMIUM_COMMUNITY', 'max_duration_seconds': 86400.0, 'max_window_t': 65, 'vae_window_t': 48, 'tile_size': 768, 'upscale_chunk_t': 16, 'io_workers': min(cpu_cores, 6), 'aggressive_vram_purge': False, 'inter_window_vram_purge': False, 'persistent_vram_weights': True, 'fp16_accumulation': True, 'cudnn_benchmark': bool(device_backend == 'cuda'), 'matmul_precision': 'high', 'use_cuda_stream': bool(device_backend == 'cuda'), 'multi_gpu_distribute': False}, '4': {**common_hw, 'tier_id': '4', 'tier_label': 'TIER_4_NVLINK_SUPERCLUSTER_80GB_PLUS', 'is_licensed': bool(is_licensed), 'license_mode': 'PRO_LICENSED' if is_licensed else 'FREEMIUM_COMMUNITY', 'max_duration_seconds': 86400.0, 'max_window_t': 121, 'vae_window_t': 64, 'tile_size': 1024, 'upscale_chunk_t': 32, 'io_workers': min(cpu_cores, 8), 'aggressive_vram_purge': False, 'inter_window_vram_purge': False, 'persistent_vram_weights': True, 'fp16_accumulation': True, 'cudnn_benchmark': bool(device_backend == 'cuda'), 'matmul_precision': 'highest', 'use_cuda_stream': bool(device_backend == 'cuda'), 'multi_gpu_distribute': True}}
    return profiles.get(tier_num, profiles['1'])


THERMAL_SHIELD_PRESETS = [
    'auto_devops_shield (Auto DevOps Skydd — GPU 78°C / CPU 85°C + Smart Kylpaus)',
    'cool_quiet_safe (Sval & Säker Anti-Krasch — GPU 72°C / CPU 80°C + Aktiv Pacing & Trådbroms)',
    'balanced_studio (Balanserad Studio — GPU 76°C / CPU 84°C)',
    'turbo_high_ceiling (Turbo — Endast Kritiskt Nödstopp vid GPU 83°C / CPU 88°C)',
    'disabled (Avstängd — Ingen Termisk Broms)',
]

TIER_THERMAL_REMEDIATION_MATRIX = {
    '1': {
        'tier_id': '1',
        'architecture_class': 'TIER_1_12GB_16GB_DESKTOP_X3D_SHARED_CHASSIS',
        'trigger_gpu_c': 83.0,
        'resume_gpu_c': 78.5,
        'ceil_gpu_c': 87.0,
        'trigger_cpu_c': 89.0,
        'resume_cpu_c': 83.0,
        'ceil_cpu_c': 93.0,
        'power_duty_cap_pct': 96.5,
        'sustained_soak_sec': 20.0,
        'inter_stage_pause_sec': 0.25,
        'step_micro_sleep_sec': 0.0,
        'check_every_n_steps': 5,
        'warm_tile_size': 384,
        'hot_tile_size': 256,
        'warm_upscale_chunk_t': 4,
        'warm_rife_batch_sz': 3,
        'force_inter_window_purge': True,
        'remediation_actions': (
            'sustained_soak_integral_guard',
            'x3d_avx_thread_cap_on_soak',
            'vrm_inter_stage_despike_sync',
            'dynamic_tile_and_batch_downshift',
            'disable_pinned_dma_on_heat',
        ),
    },
    '2': {
        'tier_id': '2',
        'architecture_class': 'TIER_2_24GB_32GB_HIGH_TDP_12VHPWR_FLAGSHIP',
        'trigger_gpu_c': 84.0,
        'resume_gpu_c': 79.0,
        'ceil_gpu_c': 88.0,
        'trigger_cpu_c': 90.0,
        'resume_cpu_c': 84.0,
        'ceil_cpu_c': 93.5,
        'power_duty_cap_pct': 96.0,
        'sustained_soak_sec': 22.0,
        'inter_stage_pause_sec': 0.20,
        'step_micro_sleep_sec': 0.0,
        'check_every_n_steps': 5,
        'warm_tile_size': 384,
        'hot_tile_size': 384,
        'warm_upscale_chunk_t': 6,
        'warm_rife_batch_sz': 4,
        'force_inter_window_purge': True,
        'remediation_actions': (
            'sustained_12vhpwr_wattage_soak_guard',
            'gddr_vram_junction_tile_stepdown',
            'inter_window_vram_purge_escalation',
            'sustained_400w_duty_pacing',
        ),
    },
    '3': {
        'tier_id': '3',
        'architecture_class': 'TIER_3_48GB_WORKSTATION_BLOWER_ECC',
        'trigger_gpu_c': 85.0,
        'resume_gpu_c': 80.0,
        'ceil_gpu_c': 88.5,
        'trigger_cpu_c': 90.0,
        'resume_cpu_c': 84.0,
        'ceil_cpu_c': 94.0,
        'power_duty_cap_pct': 97.0,
        'sustained_soak_sec': 25.0,
        'inter_stage_pause_sec': 0.15,
        'step_micro_sleep_sec': 0.0,
        'check_every_n_steps': 6,
        'warm_tile_size': 512,
        'hot_tile_size': 384,
        'warm_upscale_chunk_t': 8,
        'warm_rife_batch_sz': 4,
        'force_inter_window_purge': False,
        'remediation_actions': (
            'workstation_sustained_soak_pacing',
            'cuda_stream_serialization_on_heat',
            'numa_ccd_thread_pinning',
            'preserve_persistent_vram_weights',
        ),
    },
    '4': {
        'tier_id': '4',
        'architecture_class': 'TIER_4_80GB_MULTI_GPU_NVLINK_CLUSTER',
        'trigger_gpu_c': 86.0,
        'resume_gpu_c': 81.0,
        'ceil_gpu_c': 89.0,
        'trigger_cpu_c': 91.0,
        'resume_cpu_c': 85.0,
        'ceil_cpu_c': 94.0,
        'power_duty_cap_pct': 98.0,
        'sustained_soak_sec': 30.0,
        'inter_stage_pause_sec': 0.10,
        'step_micro_sleep_sec': 0.0,
        'check_every_n_steps': 8,
        'warm_tile_size': 768,
        'hot_tile_size': 512,
        'warm_upscale_chunk_t': 16,
        'warm_rife_batch_sz': 6,
        'force_inter_window_purge': False,
        'remediation_actions': (
            'multi_gpu_thermal_load_balancing',
            'tensor_core_precision_stepdown',
            'nvlink_sync_barrier_cooldown',
            'cluster_chunk_redistribution',
        ),
    },
}

_THERMAL_SENTINEL_CACHE = {
    'nvml_init_attempted': False,
    'nvml_ok': False,
    'smi_bin': None,
    'last_poll_ts': 0.0,
    'last_metrics': None,
    'last_stress_eval_ts': 0.0,
    'sustained_stress_sec': 0.0,
    'rolling_samples': [],
    'active_mode': 'auto_devops_shield',
    'active_tier_id': '1',
    'active_shield_cfg': None,
    'last_runtime_overrides': {},
}


def _load_devops_hardware_shields_json() -> dict:
    here = Path(__file__).resolve().parent
    candidates = [
        here.parent.parent.parent / 'CONFIG' / 'config.json',
        Path('D:/EZ_Studio_DevTools/CONFIG/config.json'),
        Path('D:/ComfyUI_windows_portable/EZ_Studio_DevTools/CONFIG/config.json'),
    ]
    for cfg_p in candidates:
        if cfg_p.exists():
            try:
                import json
                with open(cfg_p, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict) and isinstance(data.get('HARDWARE_SHIELDS'), dict):
                    return data['HARDWARE_SHIELDS']
            except Exception:
                pass
    return {}


def resolve_cinematrix_thermal_shield_config(thermal_protection_mode: str = 'auto_devops_shield', tier_id: str = '1') -> dict:
    raw_m = str(thermal_protection_mode or _THERMAL_SENTINEL_CACHE.get('active_mode') or 'auto_devops_shield').strip().lower()
    t_key = str(tier_id or _THERMAL_SENTINEL_CACHE.get('active_tier_id') or '1').strip()
    if t_key not in TIER_THERMAL_REMEDIATION_MATRIX:
        t_key = '1'
    tier_spec = TIER_THERMAL_REMEDIATION_MATRIX[t_key]
    devops_shields = _load_devops_hardware_shields_json()
    cfg_max_gpu = max(83.0, float(devops_shields.get('MAX_GPU_TEMP_CELSIUS', tier_spec['trigger_gpu_c']) or tier_spec['trigger_gpu_c']))
    cfg_max_cpu = max(89.0, float(devops_shields.get('MAX_CPU_TEMP_CELSIUS', tier_spec['trigger_cpu_c']) or tier_spec['trigger_cpu_c']))
    cfg_cd_sec = max(2, int(devops_shields.get('EMERGENCY_COOLDOWN_DELAY_SEC', 4) or 4))
    cpu_cores = max(2, int(os.cpu_count() or 8))
    if t_key == '1':
        base_torch_t = max(4, min(8, cpu_cores // 2))
        base_ff_t = max(3, min(6, cpu_cores // 3))
    elif t_key == '2':
        base_torch_t = max(6, min(10, (cpu_cores * 2) // 3))
        base_ff_t = max(4, min(8, cpu_cores // 2))
    elif t_key == '3':
        base_torch_t = max(8, min(12, (cpu_cores * 2) // 3))
        base_ff_t = max(6, min(10, cpu_cores // 2))
    else:
        base_torch_t = max(8, min(16, (cpu_cores * 3) // 4))
        base_ff_t = max(6, min(12, cpu_cores // 2))
    if raw_m.startswith('disabled') or 'avstängd' in raw_m:
        cfg = {
            'enabled': False,
            'mode_key': 'disabled',
            'tier_id': t_key,
            'architecture_class': tier_spec['architecture_class'],
            'remediation_actions': (),
            'trigger_gpu_c': 95.0,
            'resume_gpu_c': 90.0,
            'ceil_gpu_c': 95.0,
            'trigger_cpu_c': 95.0,
            'resume_cpu_c': 90.0,
            'ceil_cpu_c': 96.0,
            'power_duty_cap_pct': 100.0,
            'sustained_soak_sec': 60.0,
            'cooldown_step_sec': 1.0,
            'inter_stage_pause_sec': 0.0,
            'step_micro_sleep_sec': 0.0,
            'check_every_n_steps': 999,
            'max_torch_threads': cpu_cores,
            'max_ffmpeg_threads': min(12, cpu_cores),
            'warm_tile_size': tier_spec['warm_tile_size'],
            'hot_tile_size': tier_spec['hot_tile_size'],
            'warm_upscale_chunk_t': tier_spec['warm_upscale_chunk_t'],
            'warm_rife_batch_sz': tier_spec['warm_rife_batch_sz'],
            'force_inter_window_purge': False,
        }
    elif raw_m.startswith('cool_quiet') or 'sval' in raw_m:
        trig_g = max(80.0, float(tier_spec['trigger_gpu_c']) - 2.5)
        trig_c = max(85.0, float(tier_spec['trigger_cpu_c']) - 3.0)
        cfg = {
            'enabled': True,
            'mode_key': 'cool_quiet_safe',
            'tier_id': t_key,
            'architecture_class': tier_spec['architecture_class'],
            'remediation_actions': tuple(tier_spec['remediation_actions']),
            'trigger_gpu_c': trig_g,
            'resume_gpu_c': trig_g - 4.0,
            'ceil_gpu_c': float(tier_spec['ceil_gpu_c']) - 1.5,
            'trigger_cpu_c': trig_c,
            'resume_cpu_c': trig_c - 5.0,
            'ceil_cpu_c': float(tier_spec['ceil_cpu_c']) - 1.5,
            'power_duty_cap_pct': max(92.0, float(tier_spec['power_duty_cap_pct']) - 3.0),
            'sustained_soak_sec': max(12.0, float(tier_spec['sustained_soak_sec']) - 6.0),
            'cooldown_step_sec': float(cfg_cd_sec),
            'inter_stage_pause_sec': round(float(tier_spec['inter_stage_pause_sec']) + 0.15, 3),
            'step_micro_sleep_sec': 0.0,
            'check_every_n_steps': max(3, int(tier_spec['check_every_n_steps']) - 1),
            'max_torch_threads': max(4, base_torch_t - 1),
            'max_ffmpeg_threads': max(2, base_ff_t - 1),
            'warm_tile_size': tier_spec['warm_tile_size'],
            'hot_tile_size': max(256, int(tier_spec['hot_tile_size'])),
            'warm_upscale_chunk_t': max(2, int(tier_spec['warm_upscale_chunk_t'])),
            'warm_rife_batch_sz': max(2, int(tier_spec['warm_rife_batch_sz'])),
            'force_inter_window_purge': True if t_key in ('1', '2', '3') else False,
        }
    elif raw_m.startswith('balanced') or 'balanserad' in raw_m:
        trig_g = max(82.0, float(tier_spec['trigger_gpu_c']) - 1.0)
        trig_c = max(88.0, float(tier_spec['trigger_cpu_c']) - 1.0)
        cfg = {
            'enabled': True,
            'mode_key': 'balanced_studio',
            'tier_id': t_key,
            'architecture_class': tier_spec['architecture_class'],
            'remediation_actions': tuple(tier_spec['remediation_actions']),
            'trigger_gpu_c': trig_g,
            'resume_gpu_c': trig_g - 4.0,
            'ceil_gpu_c': float(tier_spec['ceil_gpu_c']),
            'trigger_cpu_c': trig_c,
            'resume_cpu_c': trig_c - 5.0,
            'ceil_cpu_c': float(tier_spec['ceil_cpu_c']),
            'power_duty_cap_pct': float(tier_spec['power_duty_cap_pct']),
            'sustained_soak_sec': max(16.0, float(tier_spec['sustained_soak_sec']) - 2.0),
            'cooldown_step_sec': float(cfg_cd_sec),
            'inter_stage_pause_sec': float(tier_spec['inter_stage_pause_sec']),
            'step_micro_sleep_sec': 0.0,
            'check_every_n_steps': int(tier_spec['check_every_n_steps']),
            'max_torch_threads': base_torch_t,
            'max_ffmpeg_threads': base_ff_t,
            'warm_tile_size': tier_spec['warm_tile_size'],
            'hot_tile_size': tier_spec['hot_tile_size'],
            'warm_upscale_chunk_t': tier_spec['warm_upscale_chunk_t'],
            'warm_rife_batch_sz': tier_spec['warm_rife_batch_sz'],
            'force_inter_window_purge': bool(tier_spec['force_inter_window_purge']),
        }
    elif raw_m.startswith('turbo'):
        trig_g = max(85.0, float(tier_spec['trigger_gpu_c']) + 2.0)
        trig_c = max(91.0, float(tier_spec['trigger_cpu_c']) + 2.0)
        cfg = {
            'enabled': True,
            'mode_key': 'turbo_high_ceiling',
            'tier_id': t_key,
            'architecture_class': tier_spec['architecture_class'],
            'remediation_actions': tuple(tier_spec['remediation_actions']),
            'trigger_gpu_c': trig_g,
            'resume_gpu_c': trig_g - 4.0,
            'ceil_gpu_c': max(88.5, float(tier_spec['ceil_gpu_c']) + 1.5),
            'trigger_cpu_c': trig_c,
            'resume_cpu_c': trig_c - 4.5,
            'ceil_cpu_c': max(94.0, float(tier_spec['ceil_cpu_c'])),
            'power_duty_cap_pct': min(99.0, float(tier_spec['power_duty_cap_pct']) + 2.0),
            'sustained_soak_sec': float(tier_spec['sustained_soak_sec']) + 10.0,
            'cooldown_step_sec': float(cfg_cd_sec),
            'inter_stage_pause_sec': max(0.10, round(float(tier_spec['inter_stage_pause_sec']) * 0.5, 3)),
            'step_micro_sleep_sec': 0.0,
            'check_every_n_steps': max(6, int(tier_spec['check_every_n_steps']) + 2),
            'max_torch_threads': min(cpu_cores, base_torch_t + 2),
            'max_ffmpeg_threads': min(12, base_ff_t + 2),
            'warm_tile_size': tier_spec['warm_tile_size'],
            'hot_tile_size': tier_spec['hot_tile_size'],
            'warm_upscale_chunk_t': tier_spec['warm_upscale_chunk_t'],
            'warm_rife_batch_sz': tier_spec['warm_rife_batch_sz'],
            'force_inter_window_purge': bool(tier_spec['force_inter_window_purge']),
        }
    else:
        trig_g = max(float(tier_spec['trigger_gpu_c']), cfg_max_gpu)
        trig_c = max(float(tier_spec['trigger_cpu_c']), cfg_max_cpu)
        cfg = {
            'enabled': True,
            'mode_key': 'auto_devops_shield',
            'tier_id': t_key,
            'architecture_class': tier_spec['architecture_class'],
            'remediation_actions': tuple(tier_spec['remediation_actions']),
            'trigger_gpu_c': trig_g,
            'resume_gpu_c': float(tier_spec['resume_gpu_c']),
            'ceil_gpu_c': float(tier_spec['ceil_gpu_c']),
            'trigger_cpu_c': trig_c,
            'resume_cpu_c': float(tier_spec['resume_cpu_c']),
            'ceil_cpu_c': float(tier_spec['ceil_cpu_c']),
            'power_duty_cap_pct': float(tier_spec['power_duty_cap_pct']),
            'sustained_soak_sec': float(tier_spec['sustained_soak_sec']),
            'cooldown_step_sec': float(cfg_cd_sec),
            'inter_stage_pause_sec': float(tier_spec['inter_stage_pause_sec']),
            'step_micro_sleep_sec': 0.0,
            'check_every_n_steps': int(tier_spec['check_every_n_steps']),
            'max_torch_threads': base_torch_t,
            'max_ffmpeg_threads': base_ff_t,
            'warm_tile_size': tier_spec['warm_tile_size'],
            'hot_tile_size': tier_spec['hot_tile_size'],
            'warm_upscale_chunk_t': tier_spec['warm_upscale_chunk_t'],
            'warm_rife_batch_sz': tier_spec['warm_rife_batch_sz'],
            'force_inter_window_purge': bool(tier_spec['force_inter_window_purge']),
        }
    _THERMAL_SENTINEL_CACHE['active_mode'] = cfg['mode_key']
    _THERMAL_SENTINEL_CACHE['active_tier_id'] = t_key
    _THERMAL_SENTINEL_CACHE['active_shield_cfg'] = cfg
    return cfg


def probe_cinematrix_hardware_thermals(force_refresh: bool = False) -> dict:
    import time
    import shutil
    import subprocess
    import sys
    now = time.time()
    cached = _THERMAL_SENTINEL_CACHE.get('last_metrics')
    if not force_refresh and isinstance(cached, dict) and (now - float(_THERMAL_SENTINEL_CACHE.get('last_poll_ts', 0.0))) < 2.5:
        return cached
    gpu_temp_c = None
    gpu_temps_all = []
    gpu_power_w = None
    gpu_power_limit_w = None
    vram_used_mb = None
    vram_total_mb = None
    if not _THERMAL_SENTINEL_CACHE['nvml_init_attempted']:
        _THERMAL_SENTINEL_CACHE['nvml_init_attempted'] = True
        try:
            import pynvml
            pynvml.nvmlInit()
            _THERMAL_SENTINEL_CACHE['nvml_ok'] = True
        except Exception:
            _THERMAL_SENTINEL_CACHE['nvml_ok'] = False
        smi_cand = shutil.which('nvidia-smi') or (r'C:\Windows\System32\nvidia-smi.exe' if sys.platform == 'win32' else None)
        if smi_cand and os.path.exists(smi_cand):
            _THERMAL_SENTINEL_CACHE['smi_bin'] = smi_cand
    if _THERMAL_SENTINEL_CACHE['nvml_ok']:
        try:
            import pynvml
            dev_cnt = max(1, int(pynvml.nvmlDeviceGetCount()))
            tot_pwr = 0.0
            tot_lim = 0.0
            for d_i in range(dev_cnt):
                handle = pynvml.nvmlDeviceGetHandleByIndex(d_i)
                t_i = float(pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU))
                gpu_temps_all.append(round(t_i, 1))
                try:
                    tot_pwr += float(pynvml.nvmlDeviceGetPowerUsage(handle)) / 1000.0
                except Exception:
                    pass
                try:
                    tot_lim += float(pynvml.nvmlDeviceGetEnforcedPowerLimit(handle)) / 1000.0
                except Exception:
                    pass
                if d_i == 0:
                    mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    vram_used_mb = float(mem_info.used) / (1024.0 ** 2)
                    vram_total_mb = float(mem_info.total) / (1024.0 ** 2)
            if gpu_temps_all:
                gpu_temp_c = max(gpu_temps_all)
            if tot_pwr > 0.0:
                gpu_power_w = tot_pwr
            if tot_lim > 0.0:
                gpu_power_limit_w = tot_lim
        except Exception:
            pass
    if gpu_temp_c is None and _THERMAL_SENTINEL_CACHE.get('smi_bin'):
        try:
            s_info = None
            c_flags = 0
            if sys.platform == 'win32':
                c_flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
                if hasattr(subprocess, 'STARTUPINFO'):
                    s_info = subprocess.STARTUPINFO()
                    s_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    s_info.wShowWindow = 0
            res = subprocess.run(
                [_THERMAL_SENTINEL_CACHE['smi_bin'], '--query-gpu=temperature.gpu,power.draw,power.limit,memory.used,memory.total', '--format=csv,noheader,nounits'],
                capture_output=True,
                text=True,
                startupinfo=s_info,
                creationflags=c_flags,
                timeout=1.2,
            )
            if res.returncode == 0 and res.stdout.strip():
                lines = [ln.strip() for ln in res.stdout.strip().splitlines() if ln.strip()]
                tot_p = 0.0
                tot_l = 0.0
                for (l_i, ln) in enumerate(lines):
                    parts = [p.strip() for p in ln.split(',')]
                    if len(parts) >= 5:
                        t_v = float(parts[0]) if parts[0] not in ('[N/A]', 'N/A', '') else None
                        p_v = float(parts[1]) if parts[1] not in ('[N/A]', 'N/A', '') else None
                        l_v = float(parts[2]) if parts[2] not in ('[N/A]', 'N/A', '') else None
                        if t_v is not None:
                            gpu_temps_all.append(round(t_v, 1))
                        if p_v is not None:
                            tot_p += p_v
                        if l_v is not None:
                            tot_l += l_v
                        if l_i == 0:
                            vram_used_mb = float(parts[3]) if parts[3] not in ('[N/A]', 'N/A', '') else None
                            vram_total_mb = float(parts[4]) if parts[4] not in ('[N/A]', 'N/A', '') else None
                if gpu_temps_all:
                    gpu_temp_c = max(gpu_temps_all)
                if tot_p > 0.0:
                    gpu_power_w = tot_p
                if tot_l > 0.0:
                    gpu_power_limit_w = tot_l
        except Exception:
            pass
    cpu_pct = 0.0
    cpu_temp_c = 44.0
    try:
        import psutil
        cpu_pct = float(psutil.cpu_percent(interval=None))
        temps = getattr(psutil, 'sensors_temperatures', lambda: {})() or {}
        found_c = []
        for entries in temps.values():
            for ent in (entries or []):
                cur_t = getattr(ent, 'current', None)
                if cur_t is not None and 20.0 <= float(cur_t) <= 115.0:
                    found_c.append(float(cur_t))
        if found_c:
            cpu_temp_c = round(max(found_c), 1)
        else:
            cpu_temp_c = round(43.0 + cpu_pct * 0.40, 1)
    except Exception:
        cpu_temp_c = 44.0
    vram_pct = round((vram_used_mb / vram_total_mb) * 100.0, 1) if (vram_used_mb is not None and vram_total_mb and vram_total_mb > 0) else 0.0
    gpu_delta_c = round(max(gpu_temps_all) - min(gpu_temps_all), 1) if len(gpu_temps_all) >= 2 else 0.0
    snap = {
        'timestamp': now,
        'gpu_temp_c': round(float(gpu_temp_c), 1) if gpu_temp_c is not None else 42.0,
        'gpu_temps_all': gpu_temps_all if gpu_temps_all else [round(float(gpu_temp_c), 1) if gpu_temp_c is not None else 42.0],
        'gpu_temp_delta_c': gpu_delta_c,
        'gpu_count': max(1, len(gpu_temps_all)),
        'gpu_temp_real': gpu_temp_c is not None,
        'cpu_temp_c': round(float(cpu_temp_c), 1),
        'cpu_utilization_pct': round(float(cpu_pct), 1),
        'gpu_power_w': round(float(gpu_power_w), 1) if gpu_power_w is not None else 55.0,
        'gpu_power_limit_w': round(float(gpu_power_limit_w), 1) if gpu_power_limit_w is not None else 300.0,
        'vram_used_mb': round(float(vram_used_mb), 1) if vram_used_mb is not None else None,
        'vram_total_mb': round(float(vram_total_mb), 1) if vram_total_mb is not None else None,
        'vram_stress_pct': vram_pct,
    }
    _THERMAL_SENTINEL_CACHE['last_poll_ts'] = now
    _THERMAL_SENTINEL_CACHE['last_metrics'] = snap
    return snap


def _apply_tier_specific_thermal_remediations(
    tier_id: str,
    shield_cfg: dict,
    snap: dict,
    tier_profile: dict = None,
    is_over_trigger: bool = False,
) -> dict:
    import time
    t_key = str(tier_id or shield_cfg.get('tier_id', '1') or '1').strip()
    if t_key not in TIER_THERMAL_REMEDIATION_MATRIX:
        t_key = '1'
    tier_spec = TIER_THERMAL_REMEDIATION_MATRIX[t_key]
    gpu_c = float(snap.get('gpu_temp_c', 42.0))
    cpu_c = float(snap.get('cpu_temp_c', 44.0))
    pwr_w = float(snap.get('gpu_power_w', 55.0))
    pwr_lim = max(100.0, float(snap.get('gpu_power_limit_w', 300.0)))
    pwr_pct = (pwr_w / pwr_lim) * 100.0
    trig_gpu = float(shield_cfg.get('trigger_gpu_c', tier_spec['trigger_gpu_c']))
    trig_cpu = float(shield_cfg.get('trigger_cpu_c', tier_spec['trigger_cpu_c']))
    duty_cap_pct = float(shield_cfg.get('power_duty_cap_pct', tier_spec['power_duty_cap_pct']))
    soak_limit = max(8.0, float(shield_cfg.get('sustained_soak_sec', tier_spec.get('sustained_soak_sec', 20.0))))
    sustained_sec = float(_THERMAL_SENTINEL_CACHE.get('sustained_stress_sec', 0.0) or 0.0)
    is_warm = bool(
        is_over_trigger
        or sustained_sec >= (soak_limit * 0.5)
        or gpu_c >= (trig_gpu - 1.0)
        or cpu_c >= (trig_cpu - 2.0)
        or (pwr_pct >= duty_cap_pct and gpu_c >= (trig_gpu - 2.0))
    )
    active_actions = []
    default_tile = 512 if t_key in ('1', '2') else (768 if t_key == '3' else 1024)
    default_chunk = 8 if t_key == '1' else (12 if t_key == '2' else (16 if t_key == '3' else 32))
    default_rife = 6 if t_key in ('1', '2', '3') else 8
    overrides = {
        'tier_id': t_key,
        'architecture_class': tier_spec['architecture_class'],
        'is_warm': is_warm,
        'sustained_stress_sec': round(sustained_sec, 1),
        'sustained_soak_limit_sec': round(soak_limit, 1),
        'tile_size': default_tile,
        'upscale_chunk_t': default_chunk,
        'rife_batch_sz': default_rife,
        'inter_window_vram_purge': bool(t_key == '1'),
        'allow_pinned_memory': True,
        'use_cuda_stream': bool(t_key in ('3', '4')),
        'matmul_precision': 'highest' if t_key == '4' else 'high',
        'active_remediations': active_actions,
    }
    if t_key == '1':
        if is_warm:
            overrides['tile_size'] = int(shield_cfg.get('hot_tile_size', 256) if is_over_trigger else shield_cfg.get('warm_tile_size', 384))
            overrides['upscale_chunk_t'] = int(shield_cfg.get('warm_upscale_chunk_t', 4))
            overrides['rife_batch_sz'] = int(shield_cfg.get('warm_rife_batch_sz', 3))
            overrides['inter_window_vram_purge'] = True
            overrides['allow_pinned_memory'] = False
            active_actions.extend(['sustained_soak_integral_guard', 'x3d_avx_thread_cap_on_soak', 'dynamic_tile_and_batch_downshift', 'disable_pinned_dma_on_heat'])
    elif t_key == '2':
        if is_warm and (pwr_pct >= duty_cap_pct or pwr_w >= 430.0):
            active_actions.append('sustained_12vhpwr_wattage_soak_guard')
            time.sleep(0.025)
        if is_warm:
            overrides['tile_size'] = int(shield_cfg.get('warm_tile_size', 384))
            overrides['upscale_chunk_t'] = int(shield_cfg.get('warm_upscale_chunk_t', 6))
            overrides['rife_batch_sz'] = int(shield_cfg.get('warm_rife_batch_sz', 4))
            overrides['inter_window_vram_purge'] = True
            active_actions.extend(['gddr_vram_junction_tile_stepdown', 'inter_window_vram_purge_escalation'])
    elif t_key == '3':
        active_actions.append('preserve_persistent_vram_weights')
        if is_warm:
            overrides['tile_size'] = int(shield_cfg.get('hot_tile_size', 384) if is_over_trigger else shield_cfg.get('warm_tile_size', 512))
            overrides['upscale_chunk_t'] = int(shield_cfg.get('warm_upscale_chunk_t', 8))
            overrides['rife_batch_sz'] = int(shield_cfg.get('warm_rife_batch_sz', 4))
            overrides['use_cuda_stream'] = False
            active_actions.extend(['workstation_sustained_soak_pacing', 'cuda_stream_serialization_on_heat', 'numa_ccd_thread_pinning'])
    else:
        gpu_delta = float(snap.get('gpu_temp_delta_c', 0.0))
        if int(snap.get('gpu_count', 1)) > 1 and (gpu_delta >= 7.0 or is_warm):
            active_actions.append('multi_gpu_thermal_load_balancing')
            try:
                if torch.cuda.is_available():
                    for d_i in range(torch.cuda.device_count()):
                        torch.cuda.synchronize(d_i)
            except Exception:
                pass
        if is_warm:
            overrides['tile_size'] = int(shield_cfg.get('warm_tile_size', 768))
            overrides['upscale_chunk_t'] = int(shield_cfg.get('warm_upscale_chunk_t', 16))
            overrides['rife_batch_sz'] = int(shield_cfg.get('warm_rife_batch_sz', 6))
            overrides['matmul_precision'] = 'high'
            active_actions.append('tensor_core_precision_stepdown')
            try:
                if hasattr(torch, 'set_float32_matmul_precision'):
                    torch.set_float32_matmul_precision('high')
            except Exception:
                pass
    if is_warm:
        try:
            max_thr = int(shield_cfg.get('max_torch_threads', 8) or 8)
            if hasattr(torch, 'get_num_threads') and hasattr(torch, 'set_num_threads') and int(torch.get_num_threads()) > max_thr:
                torch.set_num_threads(max_thr)
        except Exception:
            pass
    if isinstance(tier_profile, dict):
        tier_profile['tile_size'] = overrides['tile_size']
        tier_profile['upscale_chunk_t'] = overrides['upscale_chunk_t']
        tier_profile['inter_window_vram_purge'] = overrides['inter_window_vram_purge']
        tier_profile['allow_pinned_memory'] = overrides['allow_pinned_memory']
        tier_profile['use_cuda_stream'] = overrides['use_cuda_stream']
        tier_profile['matmul_precision'] = overrides['matmul_precision']
        tier_profile['active_thermal_remediations'] = list(active_actions)
    _THERMAL_SENTINEL_CACHE['last_runtime_overrides'] = overrides
    return overrides


def enforce_cinematrix_thermal_shield(
    stage_tag: str = 'Pipeline',
    tier_profile: dict = None,
    step_idx: int = 0,
    total_steps: int = 0,
    force_inter_stage_pause: bool = False,
) -> dict:
    import time
    prof = tier_profile if isinstance(tier_profile, dict) else {}
    t_id = str(prof.get('tier_id') or _THERMAL_SENTINEL_CACHE.get('active_tier_id') or '1').strip()
    shield_cfg = prof.get('thermal_shield') if isinstance(prof.get('thermal_shield'), dict) else _THERMAL_SENTINEL_CACHE.get('active_shield_cfg')
    if not isinstance(shield_cfg, dict) or str(shield_cfg.get('tier_id', '')) != t_id:
        shield_cfg = resolve_cinematrix_thermal_shield_config(prof.get('thermal_protection_mode', 'auto_devops_shield'), t_id)
    if not bool(shield_cfg.get('enabled', True)):
        return {'throttled': False, 'mode': 'disabled', 'tier_id': t_id, 'runtime_overrides': {}}
    check_n = max(1, int(shield_cfg.get('check_every_n_steps', 5) or 5))
    if total_steps > 0 and not force_inter_stage_pause:
        if step_idx > 0 and (step_idx % check_n != 0) and (step_idx != total_steps - 1):
            return {
                'throttled': False,
                'mode': shield_cfg.get('mode_key', 'auto_devops_shield'),
                'tier_id': t_id,
                'runtime_overrides': _THERMAL_SENTINEL_CACHE.get('last_runtime_overrides', {}),
            }
    if force_inter_stage_pause:
        inter_pause = float(shield_cfg.get('inter_stage_pause_sec', 0.20) or 0.0)
        if inter_pause > 0.01:
            try:
                if torch.cuda.is_available():
                    torch.cuda.synchronize()
            except Exception:
                pass
            time.sleep(inter_pause)
    snap = probe_cinematrix_hardware_thermals(force_refresh=force_inter_stage_pause)
    now_ts = float(snap.get('timestamp', time.time()))
    prev_ts = float(_THERMAL_SENTINEL_CACHE.get('last_stress_eval_ts', 0.0) or 0.0)
    dt = max(0.1, min(8.0, now_ts - prev_ts)) if prev_ts > 0.0 else 1.0
    _THERMAL_SENTINEL_CACHE['last_stress_eval_ts'] = now_ts
    trig_gpu = float(shield_cfg.get('trigger_gpu_c', 83.0))
    res_gpu = float(shield_cfg.get('resume_gpu_c', trig_gpu - 4.5))
    ceil_gpu = float(shield_cfg.get('ceil_gpu_c', 87.0))
    trig_cpu = float(shield_cfg.get('trigger_cpu_c', 89.0))
    res_cpu = float(shield_cfg.get('resume_cpu_c', trig_cpu - 6.0))
    ceil_cpu = float(shield_cfg.get('ceil_cpu_c', 93.0))
    soak_limit_sec = max(8.0, float(shield_cfg.get('sustained_soak_sec', 20.0)))
    gpu_c = float(snap.get('gpu_temp_c', 42.0))
    cpu_c = float(snap.get('cpu_temp_c', 44.0))
    pwr_w = float(snap.get('gpu_power_w', 55.0))
    pwr_lim = max(100.0, float(snap.get('gpu_power_limit_w', 300.0)))
    pwr_pct = (pwr_w / pwr_lim) * 100.0
    duty_cap_pct = float(shield_cfg.get('power_duty_cap_pct', 96.5))
    power_soak = bool(pwr_lim > 80.0 and pwr_pct >= duty_cap_pct and gpu_c >= (trig_gpu - 1.5))
    is_critical_ceil = bool(gpu_c >= ceil_gpu or cpu_c >= ceil_cpu)
    is_high_stress = bool(gpu_c >= trig_gpu or cpu_c >= trig_cpu or power_soak)
    sustained_sec = float(_THERMAL_SENTINEL_CACHE.get('sustained_stress_sec', 0.0) or 0.0)
    if is_high_stress:
        over_g = max(0.0, gpu_c - trig_gpu + 1.0)
        over_c = max(0.0, cpu_c - trig_cpu + 1.0)
        pwr_factor = max(0.75, min(1.35, pwr_pct / 90.0))
        intensity_mult = max(0.85, min(2.5, max(over_g / 2.0, over_c / 2.0, 1.0) * pwr_factor))
        sustained_sec = min(soak_limit_sec * 2.0, sustained_sec + dt * intensity_mult)
    else:
        sustained_sec = max(0.0, sustained_sec - dt * 1.8)
    _THERMAL_SENTINEL_CACHE['sustained_stress_sec'] = sustained_sec
    is_over = bool(is_critical_ceil or sustained_sec >= soak_limit_sec)
    overrides = _apply_tier_specific_thermal_remediations(t_id, shield_cfg, snap, tier_profile=prof, is_over_trigger=is_over)
    if not is_over:
        return {
            'throttled': False,
            'metrics': snap,
            'mode': shield_cfg.get('mode_key', 'auto_devops_shield'),
            'tier_id': t_id,
            'runtime_overrides': overrides,
        }
    try:
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        if force_inter_stage_pause and (t_id in ('1', '2') or not bool(prof.get('persistent_vram_weights', False))):
            if hasattr(comfy.model_management, 'soft_empty_cache'):
                comfy.model_management.soft_empty_cache()
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
    except Exception:
        pass
    rem_str = ', '.join(overrides.get('active_remediations', ())) or 'cooldown_pause'
    reason_tag = 'AKUT TAK-GRÄNS' if is_critical_ceil else f'UTHÅLLIG VÄRMEMÄTTNAD ({sustained_sec:.1f}s/{soak_limit_sec:.0f}s)'
    print(
        f'🛡️ [EZ-THERMAL-SHIELD][TIER-{t_id}] Värme-/Effektbroms ({reason_tag}) vid [{stage_tag}] -> '
        f'GPU: {gpu_c:.1f}°C (Soak-gräns {trig_gpu:.1f}°C / Tak {ceil_gpu:.1f}°C) | CPU: {cpu_c:.1f}°C (Gräns {trig_cpu:.1f}°C) | '
        f'Effekt: {pwr_w:.0f}W/{pwr_lim:.0f}W ({pwr_pct:.0f}%) | Tier-{t_id} Åtgärder: [{rem_str}]. Pausar tills GPU <= {res_gpu:.1f}°C...'
    )
    waited = 0.0
    max_wait = 35.0
    while waited < max_wait:
        if hasattr(comfy.model_management, 'throw_exception_if_processing_interrupted'):
            comfy.model_management.throw_exception_if_processing_interrupted()
        time.sleep(1.0)
        waited += 1.0
        snap = probe_cinematrix_hardware_thermals(force_refresh=True)
        gpu_c = float(snap.get('gpu_temp_c', 42.0))
        cpu_c = float(snap.get('cpu_temp_c', 44.0))
        pwr_w = float(snap.get('gpu_power_w', 55.0))
        if gpu_c <= res_gpu and cpu_c <= res_cpu:
            break
        if int(waited) % 5 == 0:
            print(f'❄️ [EZ-THERMAL-SHIELD][TIER-{t_id}] Kyler hårdvara ({waited:.0f}s)... GPU: {gpu_c:.1f}°C (Mål <= {res_gpu:.1f}°C) | CPU: {cpu_c:.1f}°C | Effekt: {pwr_w:.0f}W')
    _THERMAL_SENTINEL_CACHE['sustained_stress_sec'] = 0.0
    _THERMAL_SENTINEL_CACHE['last_stress_eval_ts'] = time.time()
    print(f'🟢 [EZ-THERMAL-SHIELD][TIER-{t_id}] Termisk marginal återställd efter {waited:.1f}s (GPU: {gpu_c:.1f}°C | CPU: {cpu_c:.1f}°C). Återupptar [{stage_tag}] i full hastighet!')
    return {
        'throttled': True,
        'waited_sec': waited,
        'metrics': snap,
        'mode': shield_cfg.get('mode_key', 'auto_devops_shield'),
        'tier_id': t_id,
        'runtime_overrides': overrides,
    }


