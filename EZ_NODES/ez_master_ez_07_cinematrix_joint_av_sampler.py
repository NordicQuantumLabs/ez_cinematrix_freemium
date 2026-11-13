# -*- coding: utf-8 -*-
from ..EZ_ENGINES.engine_ez_07_cinematrix_joint_av_sampler import _is_nested_av_latent, _unpack_av_tensors, _repack_av_tensors, _offload_completed_chunk_to_cpu, _resolve_audio_time_dim, _slice_tensor_along_dim, _slice_av_temporal_window, _compute_audio_overlap_steps, _inject_overlap_into_av_window, _build_av_overlap_noise_mask, _stabilize_3d_video_latent_outliers, _blend_and_cat_av_windows, _project_5d_latent_to_rgb_u8, _emit_minipyav_live_video_preview, _inject_handoff_into_5d_cond_tensor, _slice_conditioning_for_window, _ez_head_chunked_sdpa, _install_sage_attention_oom_guard, _decode_handoff_frame_from_accum, _rebuild_window_h3_conditioning, _attach_temporal_continuity_lock, _sample_single_temporal_window, execute_temporal_chunked_sampling
from ..EZ_ADAPTERS.adapter_ez_07_cinematrix_joint_av_sampler import EzCinematrixTemporalSamplerAdapter

import gc
import torch
import comfy.model_management
import comfy.sample
import comfy.samplers
import comfy.utils
import latent_preview

class EZCinematrixJointAVTemporalSampler:
    """⚡ [ZONE 7] MiniMax H3 Joint Video+Audio Temporal Sampler, Continuity Stitcher & 3D Latent Upscaler."""

    @classmethod
    def INPUT_TYPES(cls):
        seed_mode_choices = ['auto_from_bus_or_local', 'use_local_video_seed', 'sync_with_master_seed_01', 'sync_with_image_seed_04', 'sync_with_qwenvl_seed_02']
        samplers_list = list(comfy.samplers.KSampler.SAMPLERS)
        def_sampler = 'res_multistep' if 'res_multistep' in samplers_list else samplers_list[0] if samplers_list else 'euler'
        sched_list = list(comfy.samplers.KSampler.SCHEDULERS)
        def_sched = 'simple' if 'simple' in sched_list else sched_list[0] if sched_list else 'normal'
        return {'required': {'active_video_model': ('MODEL',), 'positive': ('CONDITIONING',), 'negative': ('CONDITIONING',), 'latent_video_audio': ('LATENT',), 'seed': ('INT', {'default': 860481191328700, 'min': 0, 'max': 9007199254740991, 'step': 1, 'control_after_generate': True}), 'seed_mode': (seed_mode_choices, {'default': seed_mode_choices[0]}), 'steps': ('INT', {'default': 8, 'min': 1, 'max': 150}), 'cfg': ('FLOAT', {'default': 1.0, 'min': 0.5, 'max': 20.0, 'step': 0.1}), 'sampler_name': (samplers_list, {'default': def_sampler}), 'scheduler': (sched_list, {'default': def_sched}), 'denoise': ('FLOAT', {'default': 1.0, 'min': 0.05, 'max': 1.0, 'step': 0.05}), 'enable_latent_2x_upscale': ('BOOLEAN', {'default': False})}, 'optional': {'previous_segment_latent': ('LATENT',), 'anatomy_dock': ('ANATOMY_DOCK',), 'cinematrix_bus': ('MINIMAX_GUIDE',)}}
    RETURN_TYPES = ('LATENT', 'STRING', 'MINIMAX_GUIDE')
    RETURN_NAMES = ('sampled_video_latent', 'continuity_ticket', 'cinematrix_bus')
    FUNCTION = 'sample_temporal'
    CATEGORY = 'EZ_Cinematrix_Core/07_Video_Samplers'

    @torch.inference_mode()
    def sample_temporal(self, active_video_model, positive, negative, latent_video_audio, seed, steps, cfg, sampler_name, scheduler, denoise, enable_latent_2x_upscale, seed_mode='auto_from_bus_or_local', previous_segment_latent=None, anatomy_dock=None, cinematrix_bus=None):
        return EzCinematrixTemporalSamplerAdapter.run_sampler(active_video_model=active_video_model, positive=positive, negative=negative, latent_video_audio=latent_video_audio, seed=seed, steps=steps, cfg=cfg, sampler_name=sampler_name, scheduler=scheduler, denoise=denoise, enable_latent_2x_upscale=enable_latent_2x_upscale, seed_mode=seed_mode, previous_segment_latent=previous_segment_latent, anatomy_dock=anatomy_dock, cinematrix_bus=cinematrix_bus)
NODE_SUITE_VERSION = 'v1.0 Freemium'
NODE_CLASS_MAPPINGS = {'EZCinematrixJointAVTemporalSampler': EZCinematrixJointAVTemporalSampler}
NODE_DISPLAY_NAME_MAPPINGS = {'EZCinematrixJointAVTemporalSampler': '⚡ EZ [07] Cinematrix Joint AV Temporal Sampler & Continuity Stitcher — Freemium v1.0'}
