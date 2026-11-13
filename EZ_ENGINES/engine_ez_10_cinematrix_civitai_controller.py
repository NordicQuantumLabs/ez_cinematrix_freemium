# -*- coding: utf-8 -*-

import hashlib
import json
import os
import re
import shutil
import struct
import time
import urllib.parse
import urllib.request
from pathlib import Path
import folder_paths
import torch
CACHE_TTL_DAYS = 30
CACHE_TTL_SECONDS = 30 * 86400
IMAGE_BASE_MODELS = ('KREA2', 'Krea 2', 'Flux.1 Krea', 'Flux.1 D', 'Flux.1 S', 'SDXL 1.0', 'SD 1.5', 'SD 3.5', 'Pony', 'Pony (SDXL)', 'Illustrious', 'Illustrious (SDXL)', 'Qwen-Image', 'Kolors', 'PixArt')
VIDEO_BASE_MODELS = ('MiniMax H3', 'MiniMax-H3', 'Hailuo H3', 'Wan Video', 'Wan 2.1', 'LTXV', 'LTX-Video', 'Hunyuan Video', 'Mochi', 'CogVideoX', 'SVD', 'AnimateDiff')
CIVITAI_SORT_PRESETS = ['Most Downloaded ★ [STANDARD - Mest Nedladdade]', 'Highest Rated — Högst Betyg', 'Newest — Senast Uppladdade']
CIVITAI_PERIOD_PRESETS = ['AllTime ★ [STANDARD - Alla Tider]', 'Year — Senaste Året', 'Month — Senaste Månaden', 'Week — Senaste Veckan', 'Day — Senaste Dygnet']
CIVITAI_DOMAIN_PRESETS = ['civitai.com (Blue — Freemium & Licensed)', 'civitai.red (Red — Endast Licensierad)', 'Both Domains (civitai.com + civitai.red — Endast Licensierad)']
CIVITAI_MODALITY_PRESETS = ['IMAGE — Bild (KREA2 / Flux.1 / SDXL / Pony [SDXL] / Illustrious [SDXL] / Qwen-Image)', 'VIDEO — Video (MiniMax H3 / Wan 2.1 / LTXV / Hunyuan)']
ARCH_OPTIMAL_SETTINGS_PROFILES = {
    'MINIMAX_H3': {'sampler': 'res_multistep', 'alt_sampler': 'euler', 'scheduler': 'simple', 'steps': 8, 'std_steps': 24, 'cfg': 1.0, 'std_cfg': 3.5, 'denoise': 1.0, 'shift_video': 5.0, 'shift_audio': 3.0, 'rec_lora_strength': 0.25, 'turbo_strength': 1.0, 'turbo_audio_strength': 1.0, 'vis_lora_audio_strength': 0.0, 'clip_strength': 0.0, 'note': '8-Step Turbo: res_multistep + simple, Steps 8, CFG 1.0, Denoise 1.00, Shift V:5.0 / A:3.0. Turbo Audio=1.0, Visuella LoRAs=0.15-0.30 (Audio=0.0, CLIP=0.0).'},
    'KREA2': {'sampler': 'euler', 'alt_sampler': 'res_multistep', 'scheduler': 'beta / simple', 'stage1_scheduler': 'beta', 'stage2_scheduler': 'simple', 'steps': 52, 'handoff_percent': 16.0, 'stage3_handoff_percent': 90.0, 'stage2_steps': 14, 'cfg': 3.0, 'stage2_cfg': 1.0, 'denoise': 0.75, 'shift_video': 0.0, 'shift_audio': 0.0, 'rec_lora_strength': 0.75, 'turbo_strength': 0.9, 'turbo_audio_strength': 0.0, 'vis_lora_audio_strength': 0.0, 'clip_strength': 1.0, 'note': 'Krea2 3-Stegs: Steg 1 (Raw 0->16% av 52 stp = 8 steg): euler + beta @ CFG 3.0 | Steg 2 (Turbo 16->90% på 14-grid): euler + simple @ CFG 1.0 | Steg 3 (HiRes 90->100% = 5 steg).'},
    'WAN': {'sampler': 'uni_pc', 'alt_sampler': 'euler', 'scheduler': 'simple', 'steps': 20, 'std_steps': 30, 'cfg': 5.0, 'std_cfg': 6.0, 'denoise': 1.0, 'shift_video': 5.0, 'shift_audio': 0.0, 'rec_lora_strength': 0.7, 'turbo_strength': 1.0, 'turbo_audio_strength': 0.0, 'vis_lora_audio_strength': 0.0, 'clip_strength': 0.0, 'note': 'Wan 2.1: uni_pc / simple, Steps 20 (8 med Turbo), CFG 5.0 (1.0 med Turbo), Denoise 1.00, Shift 5.0.'},
    'LTXV': {'sampler': 'euler', 'alt_sampler': 'res_multistep', 'scheduler': 'simple', 'steps': 20, 'std_steps': 25, 'cfg': 3.0, 'std_cfg': 3.5, 'denoise': 1.0, 'shift_video': 2.5, 'shift_audio': 0.0, 'rec_lora_strength': 0.75, 'turbo_strength': 1.0, 'turbo_audio_strength': 0.0, 'vis_lora_audio_strength': 0.0, 'clip_strength': 0.0, 'note': 'LTX-Video: euler + simple, Steps 20, CFG 3.0, Denoise 1.00, Shift 2.5.'},
    'HUNYUAN_VIDEO': {'sampler': 'euler', 'alt_sampler': 'uni_pc', 'scheduler': 'simple', 'steps': 20, 'std_steps': 30, 'cfg': 1.0, 'std_cfg': 6.0, 'denoise': 1.0, 'shift_video': 7.0, 'shift_audio': 0.0, 'rec_lora_strength': 0.75, 'turbo_strength': 1.0, 'turbo_audio_strength': 0.0, 'vis_lora_audio_strength': 0.0, 'clip_strength': 0.0, 'note': 'Hunyuan Video: euler + simple, Steps 20, Embedded CFG 1.0, Shift 7.0.'},
    'FLUX': {'sampler': 'euler', 'alt_sampler': 'heunpp2', 'scheduler': 'simple', 'steps': 20, 'std_steps': 28, 'cfg': 1.0, 'std_cfg': 1.0, 'denoise': 1.0, 'shift_video': 0.0, 'shift_audio': 0.0, 'rec_lora_strength': 0.8, 'turbo_strength': 1.0, 'turbo_audio_strength': 0.0, 'vis_lora_audio_strength': 0.0, 'clip_strength': 1.0, 'note': 'Flux.1: euler + simple/beta, Steps 20, CFG 1.0, Style LoRA 0.70-0.90.'},
    'QWEN_IMAGE': {'sampler': 'euler', 'alt_sampler': 'res_multistep', 'scheduler': 'simple', 'steps': 20, 'std_steps': 28, 'cfg': 2.5, 'std_cfg': 3.0, 'denoise': 1.0, 'shift_video': 0.0, 'shift_audio': 0.0, 'rec_lora_strength': 0.75, 'turbo_strength': 0.9, 'turbo_audio_strength': 0.0, 'vis_lora_audio_strength': 0.0, 'clip_strength': 1.0, 'note': 'Qwen-Image: euler + simple, Steps 20, CFG 2.5.'},
    'SDXL': {'sampler': 'dpmpp_2m_sde', 'alt_sampler': 'euler_ancestral', 'scheduler': 'karras', 'steps': 28, 'std_steps': 30, 'cfg': 5.5, 'std_cfg': 6.5, 'denoise': 1.0, 'shift_video': 0.0, 'shift_audio': 0.0, 'rec_lora_strength': 0.8, 'turbo_strength': 0.0, 'turbo_audio_strength': 0.0, 'vis_lora_audio_strength': 0.0, 'clip_strength': 1.0, 'note': 'SDXL 1.0 Basmodell: dpmpp_2m_sde + karras, Steps 28, CFG 5.5, Inbakad Dual CLIP-L/G & 4ch SDXL-VAE.'},
    'PONY': {'sampler': 'euler_ancestral', 'alt_sampler': 'dpmpp_2m_sde', 'scheduler': 'karras', 'stage1_sampler': 'euler_ancestral', 'stage1_scheduler': 'karras', 'stage1_steps': 28, 'stage1_cfg': 6.0, 'stage2_steps': 0, 'handoff_percent': 100.0, 'stage3_handoff_percent': 90.0, 'steps': 28, 'std_steps': 30, 'cfg': 6.0, 'std_cfg': 6.5, 'denoise': 0.75, 'shift_video': 0.0, 'shift_audio': 0.0, 'rec_lora_strength': 0.8, 'turbo_strength': 0.0, 'turbo_audio_strength': 0.0, 'vis_lora_audio_strength': 0.0, 'clip_strength': 1.0, 'note': 'Pony V6 XL (Tillhör SDXL 1.0-basmodellfamiljen — CyberRealistic Pony / AutismMix): euler_ancestral + karras, Steps 28, CFG 6.0, CLIP Skip -2, 4ch SDXL-VAE, Auto-taggar: score_9, score_8_up, score_7_up.'},
    'ILLUSTRIOUS': {'sampler': 'euler_ancestral', 'alt_sampler': 'dpmpp_2m_sde', 'scheduler': 'karras', 'stage1_sampler': 'euler_ancestral', 'stage1_scheduler': 'karras', 'stage1_steps': 28, 'stage1_cfg': 5.5, 'stage2_steps': 0, 'handoff_percent': 100.0, 'stage3_handoff_percent': 90.0, 'steps': 28, 'std_steps': 30, 'cfg': 5.5, 'std_cfg': 6.0, 'denoise': 0.75, 'shift_video': 0.0, 'shift_audio': 0.0, 'rec_lora_strength': 0.8, 'turbo_strength': 0.0, 'turbo_audio_strength': 0.0, 'vis_lora_audio_strength': 0.0, 'clip_strength': 1.0, 'note': 'Illustrious XL (Tillhör SDXL 1.0-basmodellfamiljen — NoobAI-XL / WAI-NSFW / Anime & Semi-Realism): euler_ancestral + karras, Steps 28, CFG 5.5, CLIP Skip -2, 4ch SDXL-VAE, Auto-taggar: masterpiece, best quality, newest, absurdres.'}
}
COMPANION_ARCH_PROFILES = {
    'KREA2': {
        'modality': 'IMAGE',
        'clip_type': 'krea2',
        'unet_match': ('krea-2-raw', 'krea_2_raw', 'krea2_fp8', 'krea-2', 'krea2', 'krea_2', 'krea-dev', 'flux1-krea', 'krea'),
        'turbo_match': ('krea2_raw_to_turbo', 'raw_to_turbo', 'krea_turbo', 'krea2_turbo', 'qwen_image_turbo', 'hyper-flux', 'flux_turbo'),
        'clip_match': ('qwen3vl4babliterated', 'qwen3vl_4b_fp8_scaled', 'qwen3vl_4b', 'qwen3-vl-4b', '4b_fp8', 'full_fp8', 'krea2'),
        'vae_match': ('qwen_image_vae', 'krea_vae', 'ae.safetensors', 'flux_vae'),
        'optimal_blueprint': {
            'unet': 'krea-2-raw-int8-convrot.safetensors (Int8 ConvRot / FP8 Scaled)',
            'unet_why': 'Int8 ConvRot med Hadamard-rotation halverar VRAM-förbrukningen till ~12.2 GB utan kvalitetsförlust på 16 GB GPU.',
            'turbo_lora': 'IMG_krea2_raw_to_turbo_lora.safetensors (Styrka 0.90 i Steg 2)',
            'turbo_why': 'Driver Steg 2 Turbo-handoff (16% -> 90%) @ CFG 1.0 på 14-stegs grid.',
            'clip': 'qwen3VL4BAbliteratedComfyui_v10_full_fp8.safetensors (eller qwen3vl_4b_fp8_scaled)',
            'clip_why': 'Dedikerad Qwen3-VL 4B FP8 Text Encoder (~8.4 GB staged) för Krea 2.',
            'vae': 'qwen_image_vae.safetensors (16-kanals Krea2/Qwen Native VAE)',
            'vae_why': 'Obligatorisk 16-kanals WanVAE/Krea2 latent-dekodare (~241 MB) för Krea 2.',
        },
        'downloads': [
            {'role': 'vae', 'filename': 'qwen_image_vae.safetensors', 'folder': 'vae', 'url': 'https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors'},
        ],
    },
    'FLUX': {
        'modality': 'IMAGE',
        'clip_type': 'flux',
        'unet_match': ('flux1-dev', 'flux1_dev', 'flux', 'chroma'),
        'turbo_match': ('flux_turbo', 'hyper-flux', 'turbo'),
        'clip_match': ('t5xxl_fp8_e4m3fn_scaled', 't5xxl_fp8', 't5xxl', 'clip_l'),
        'vae_match': ('ae.safetensors', 'flux_vae'),
        'optimal_blueprint': {
            'unet': 'flux1-dev-fp8-e4m3fn.safetensors (FP8 Scaled)',
            'unet_why': 'FP8 Scaled körs direkt i 16 GB VRAM utan CPU-offload.',
            'turbo_lora': 'Flux.1-Turbo-Alpha.safetensors (Styrka 0.85–1.0)',
            'turbo_why': 'Snabbar upp Flux-sampling till 8–14 steg @ CFG 1.0.',
            'clip': 't5xxl_fp8_e4m3fn_scaled.safetensors',
            'clip_why': 'FP8 Scaled T5-XXL rekommenderas för <=20 GB VRAM.',
            'vae': 'ae.safetensors (16-kanals Flux VAE)',
            'vae_why': 'Standard 16-kanals VAE för Flux.1.',
        },
        'downloads': [
            {'role': 'vae', 'filename': 'ae.safetensors', 'folder': 'vae', 'url': 'https://huggingface.co/Comfy-Org/Lumina_Image_2.0_Repackaged/resolve/main/split_files/vae/ae.safetensors'},
            {'role': 'clip', 'filename': 't5xxl_fp8_e4m3fn_scaled.safetensors', 'folder': 'text_encoders', 'url': 'https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp8_e4m3fn_scaled.safetensors'},
        ],
    },
    'QWEN_IMAGE': {
        'modality': 'IMAGE',
        'clip_type': 'krea2',
        'unet_match': ('qwen_image', 'qwen-image', 'krea-2', 'krea2', 'krea'),
        'turbo_match': ('qwen_image_turbo', 'krea2_raw_to_turbo', 'raw_to_turbo', 'turbo'),
        'clip_match': ('qwen3vl4babliterated', 'qwen3vl_4b_fp8_scaled', 'qwen3vl_4b', 'qwen2.5'),
        'vae_match': ('qwen_image_vae', 'ae.safetensors'),
        'optimal_blueprint': {
            'unet': 'qwen_image_fp8_e4m3fn.safetensors / krea-2-raw-int8-convrot',
            'unet_why': 'FP8 Scaled / Int8 ConvRot rekommenderas för 16 GB VRAM & Tier 1.',
            'turbo_lora': 'IMG_krea2_raw_to_turbo_lora.safetensors (Styrka 0.90)',
            'turbo_why': 'Steg 2 Turbo-handoff för snabb HiRes-detaljering.',
            'clip': 'qwen3VL4BAbliteratedComfyui_v10_full_fp8.safetensors (eller qwen3vl_4b_fp8_scaled)',
            'clip_why': 'Dedikerad Qwen3-VL 4B FP8 text-encoder.',
            'vae': 'qwen_image_vae.safetensors',
            'vae_why': 'Matchande 16-kanals VAE för Qwen-Image / Krea 2.',
        },
        'downloads': [
            {'role': 'vae', 'filename': 'qwen_image_vae.safetensors', 'folder': 'vae', 'url': 'https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors'},
        ],
    },
    'SDXL': {
        'modality': 'IMAGE',
        'clip_type': 'sdxl',
        'unet_match': ('sdxl', 'juggernaut', 'realvis', 'lustify', 'bigasp'),
        'turbo_match': ('sdxl_lightning', 'dmd2', 'lcm', 'hyper-sdxl', 'turbo'),
        'clip_match': ('clip_g', 'clip_l', 'sdxl'),
        'vae_match': ('sdxl_vae', 'sdxl.vae'),
        'optimal_blueprint': {
            'unet': 'SDXL 1.0 FP16 All-in-One Checkpoint',
            'unet_why': 'SDXL ryms i full FP16 (6.5 GB) på 16 GB VRAM med inbakad Dual CLIP-L/G & VAE.',
            'turbo_lora': 'sdxl_lightning_4step_lora.safetensors (Valfri)',
            'turbo_why': 'Valfri 4-8 stegs accelerations-LoRA.',
            'clip': 'Inbakad Dual CLIP-L/G i Checkpoint (eller separat clip_l + clip_g)',
            'clip_why': 'EZ [03] extraherar automatiskt Dual CLIP-L/G ur SDXL-checkpointen.',
            'vae': 'sdxl_vae.safetensors (FP16 Fix eller inbakad)',
            'vae_why': '4-kanals SDXL VAE förhindrar svarta bildrutor/NaN i FP16.',
        },
        'downloads': [
            {'role': 'vae', 'filename': 'sdxl_vae.safetensors', 'folder': 'vae', 'url': 'https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors'},
        ],
    },
    'PONY': {
        'modality': 'IMAGE',
        'clip_type': 'pony',
        'unet_match': ('pony', 'pdxl', 'autismmix', 'cyberrealistic_pony', 'sdxl'),
        'turbo_match': ('sdxl_lightning', 'dmd2', 'lcm', 'hyper-sdxl', 'turbo'),
        'clip_match': ('clip_g', 'clip_l', 'pony', 'sdxl'),
        'vae_match': ('sdxl_vae', 'sdxl.vae', 'pony'),
        'optimal_blueprint': {
            'unet': 'Pony Diffusion V6 XL / CyberRealistic Pony / AutismMix (Tillhör SDXL 1.0-basmodellen)',
            'unet_why': 'Bygger på SDXL 1.0-arkitekturen (~6.5 GB All-in-One Checkpoint) med inbakad Dual CLIP-L/G & 4ch SDXL-VAE.',
            'turbo_lora': 'Ingen (kör Stage 1 euler_ancestral + karras @ CFG 6.0) eller SDXL Lightning',
            'turbo_why': 'Pony ger högst kvalitet vid 25–30 steg utan Krea2 Turbo-LoRA.',
            'clip': 'Inbakad Pony/SDXL Dual CLIP-L/G (Auto CLIP Skip -2 i EZ [03])',
            'clip_why': 'EZ [03] extraherar automatiskt inbakad CLIP, sätter CLIP Skip -2 och injicerar score_9, score_8_up, score_7_up.',
            'vae': 'Inbakad Pony/SDXL 4ch VAE eller sdxl_vae.safetensors (FP16 Fix)',
            'vae_why': '4-kanals SDXL VAE (byter automatiskt bort Krea2/Qwen 16ch VAE).',
        },
        'downloads': [
            {'role': 'vae', 'filename': 'sdxl_vae.safetensors', 'folder': 'vae', 'url': 'https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors'},
        ],
    },
    'ILLUSTRIOUS': {
        'modality': 'IMAGE',
        'clip_type': 'illustrious',
        'unet_match': ('illustrious', 'ilxl', 'noobai', 'wai-nsfw', 'wai_nsfw', 'sdxl'),
        'turbo_match': ('sdxl_lightning', 'dmd2', 'lcm', 'hyper-sdxl', 'turbo'),
        'clip_match': ('clip_g', 'clip_l', 'illustrious', 'sdxl'),
        'vae_match': ('sdxl_vae', 'sdxl.vae', 'illustrious'),
        'optimal_blueprint': {
            'unet': 'Illustrious XL / NoobAI-XL / WAI-NSFW (Tillhör SDXL 1.0-basmodellen)',
            'unet_why': 'Bygger på SDXL 1.0-arkitekturen (~6.5 GB All-in-One Checkpoint med inbakad Dual CLIP-L/G & 4ch SDXL-VAE) — tränad på Danbooru-taggar för 2D/anime/semi-realism.',
            'turbo_lora': 'Ingen (kör Stage 1 euler_ancestral + karras @ CFG 5.5) eller DMD2/Lightning',
            'turbo_why': 'Illustrious XL presterar bäst vid 24–28 steg @ CFG 5.0–6.0.',
            'clip': 'Inbakad Illustrious/SDXL Dual CLIP-L/G (Auto CLIP Skip -2 i EZ [03])',
            'clip_why': 'EZ [03] extraherar automatiskt inbakad CLIP, sätter CLIP Skip -2 och injicerar masterpiece, best quality, newest, absurdres.',
            'vae': 'Inbakad Illustrious/SDXL 4ch VAE eller sdxl_vae.safetensors (FP16 Fix)',
            'vae_why': '4-kanals SDXL VAE (byter automatiskt bort Krea2/Qwen 16ch VAE).',
        },
        'downloads': [
            {'role': 'vae', 'filename': 'sdxl_vae.safetensors', 'folder': 'vae', 'url': 'https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors'},
        ],
    },
    'MINIMAX_H3': {
        'modality': 'VIDEO',
        'clip_type': 'minimax',
        'unet_match': ('10eros_max_singularity', 'fasth3-omni', 'minimax_h3_hybrid', 'singularity', 'prism', 'minimax_h3_fl2va', 'minimax-h3-fl2va', 'fl2va', 'minimax-h3', 'minimax_h3', 'minimax', 'hailuo'),
        'ref2va_match': ('ref2va', 'minimax_h3_ref2va', 'minimax-h3-ref2va'),
        'turbo_match': ('dmad_8step_full_critic', 'pika_h3_flex', 'minimax_h3_turbo', 'step600', 'vid_minimax'),
        'clip_match': ('qwen3vl_32b_minimax_h3_nvfp4_awq', 'qwen3vl_32b_minimax_h3', 'qwen3vl_32b', 'minimax_h3_nvfp4', '32b_minimax', 'minimax_h3', 'h3\\', 'h3/'),
        'vae_match': ('minimax-h3-video_vae_fp16', 'minimax_h3_video_vae_bf16', 'minimax_h3_video_vae_fp16', 'minimax_h3_video_vae_fp32', 'minimax_h3_video_vae.safetensors', 'minimax_h3_video_vae_fp8mix', 'minimax_h3_video_vae_int8_convrot', 'minimax_h3_video_vae', 'video_vae'),
        'audio_vae_match': ('minimax-h3-audio_vae_fp32', 'minimax_h3_audio_vae_fp32', 'minimax_h3_audio_vae', 'audio_vae'),
        'optimal_blueprint': {
            'hf_repo': 'https://huggingface.co/DeepBeepMeep/MiniMax-H3/tree/main',
            'unet': '10Eros_Max_SingularityV2_PRISM2_PikaFlex_0.85_int8HQ.safetensors (eller FastH3-Omni-NVFP4-QAD 13.8 GB / h3ErosMax_beta5)',
            'unet_why': 'Int8HQ / QAD NVFP4 med Hadamard-rotation ger högsta detaljrikedom & hastighet på 16 GB RTX 5070 Ti.',
            'ref2va': 'dasiwa_minimax_h3_ref2va_v5xs_pruned_graviton_int8_row-wise_convrot_runtime_mixed.safetensors (eller Singularity_ref2va_v2 / 10erosMax_v11)',
            'turbo_lora': 'minimax_h3_dmad_8step_full_critic_lora_bf16.safetensors (Endast på Non-Turbo UNet)',
            'turbo_why': 'Adversarial 8-step Full-Critic-destillering (kopplas automatiskt ur av EZ-05-TURBO-GUARD på PikaFlex/10Eros/FastH3/DaSiWa).',
            'clip': 'qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors (32B 5120-dim NVFP4/AWQ H3 TE)',
            'clip_why': 'Dedikerad 32B 5120-dim NVFP4/AWQ Qwen3-VL Text Encoder — hårdvaruaccelererad i RTX 5070 Ti (Blackwell) Tensor Cores.',
            'vae': 'MiniMax-H3-video_vae_fp16.safetensors (5.21 GB 16-bit FP16 — från DeepBeepMeep/MiniMax-H3)',
            'vae_why': 'Ren 16-bitars FP16/BF16 3D Video-VAE eliminerar 8-bitars (int8_convrot) kvantiserings- och kontrastdrift vid flerfönster encode->decode!',
            'audio_vae': 'MiniMax-H3-audio_vae_fp32.safetensors (605 MB FP32)',
            'audio_vae_why': 'Full FP32 Audio-VAE krävs för kristallren 32kHz sång, lip-sync, tal & SFX utan fasbrus.',
        },
        'downloads': [],
    },
    'WAN': {
        'modality': 'VIDEO',
        'clip_type': 'wan',
        'unet_match': ('wan2.1', 'wan_2.1', 'wan2.2', 'wan_2.2', 'wan'),
        'turbo_match': ('causvid', 'lightx2v', 'wan_turbo', 'self_forcing'),
        'clip_match': ('umt5_xxl_fp8_e4m3fn_scaled', 'umt5_xxl', 'umt5'),
        'vae_match': ('wan_2.2_vae', 'wan_2.1_vae', 'wan_vae', 'wan'),
        'audio_vae_match': (),
        'optimal_blueprint': {
            'unet': 'wan2.1_i2v_720p_14B_fp8_scaled.safetensors',
            'unet_why': 'FP8 Scaled 14B krävs för att rymmas på 16 GB VRAM.',
            'turbo_lora': 'Wan21_CausVid_14B_T2V_lora_rank32.safetensors (8 steg)',
            'turbo_why': 'Reducerar Wan 2.1 från 30 steg till 8 steg @ CFG 1.0.',
            'clip': 'umt5_xxl_fp8_e4m3fn_scaled.safetensors',
            'clip_why': 'FP8 Scaled UMT5-XXL sparar 5.2 GB VRAM.',
            'vae': 'wan_2.1_vae.safetensors',
            'vae_why': 'Temporalt 3D Video-VAE för Wan 2.1.',
        },
        'downloads': [
            {'role': 'vae', 'filename': 'wan_2.1_vae.safetensors', 'folder': 'vae', 'url': 'https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors'},
            {'role': 'clip', 'filename': 'umt5_xxl_fp8_e4m3fn_scaled.safetensors', 'folder': 'text_encoders', 'url': 'https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors'},
        ],
    },
    'LTXV': {
        'modality': 'VIDEO',
        'clip_type': 'ltxv',
        'unet_match': ('ltxv', 'ltx-video', 'ltx_video'),
        'turbo_match': ('ltxv_turbo', 'ltx_turbo'),
        'clip_match': ('t5xxl_fp8', 't5xxl'),
        'vae_match': ('ltxv', 'ltx_video_vae', 'ltx'),
        'audio_vae_match': (),
        'optimal_blueprint': {
            'unet': 'ltx-video-2b-v0.9.5.safetensors',
            'unet_why': 'Snabb 2B/13B DiT-modell för realtidsvideo.',
            'turbo_lora': 'Valfri LTX-Video Detailer / Turbo LoRA',
            'turbo_why': 'Förstärker rörelse och skärpa.',
            'clip': 't5xxl_fp8_e4m3fn_scaled.safetensors',
            'clip_why': 'FP8 Scaled T5-XXL.',
            'vae': 'Inbakad LTXV VAE (eller separat ltx_video_vae)',
            'vae_why': 'LTX-Video temporal VAE.',
        },
        'downloads': [
            {'role': 'clip', 'filename': 't5xxl_fp8_e4m3fn_scaled.safetensors', 'folder': 'text_encoders', 'url': 'https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp8_e4m3fn_scaled.safetensors'},
        ],
    },
    'HUNYUAN_VIDEO': {
        'modality': 'VIDEO',
        'clip_type': 'hunyuan_video',
        'unet_match': ('hunyuan_video', 'hunyuanvideo', 'hunyuan'),
        'turbo_match': ('fastvideo', 'hunyuan_turbo'),
        'clip_match': ('llava_llama3', 'hunyuan'),
        'vae_match': ('hunyuan_video_vae', 'hunyuan'),
        'audio_vae_match': (),
        'optimal_blueprint': {
            'unet': 'hunyuan_video_720_cfgdistill_fp8_e4m3fn.safetensors',
            'unet_why': 'FP8 e4m3fn krävs för 16 GB VRAM.',
            'turbo_lora': 'hunyuan_video_fastvideo_lora.safetensors',
            'turbo_why': 'Snabbar upp Hunyuan Video till 8-12 steg.',
            'clip': 'llava_llama3_fp8_scaled.safetensors',
            'clip_why': 'FP8 Scaled LLaVA-Llama3 Text Encoder.',
            'vae': 'hunyuan_video_vae_bf16.safetensors',
            'vae_why': 'BF16 3D Video-VAE för Hunyuan.',
        },
        'downloads': [
            {'role': 'vae', 'filename': 'hunyuan_video_vae_bf16.safetensors', 'folder': 'vae', 'url': 'https://huggingface.co/Comfy-Org/HunyuanVideo_repackaged/resolve/main/split_files/vae/hunyuan_video_vae_bf16.safetensors'},
            {'role': 'clip', 'filename': 'llava_llama3_fp8_scaled.safetensors', 'folder': 'text_encoders', 'url': 'https://huggingface.co/Comfy-Org/HunyuanVideo_repackaged/resolve/main/split_files/text_encoders/llava_llama3_fp8_scaled.safetensors'},
        ],
    },
}

def _get_suite_root() -> Path:
    return Path(__file__).resolve().parent.parent

def get_civitai_cache_dir() -> Path:
    c_dir = _get_suite_root() / 'EZ_CIVITAI_CACHE'
    (c_dir / 'thumbs').mkdir(parents=True, exist_ok=True)
    (c_dir / 'queries').mkdir(parents=True, exist_ok=True)
    (c_dir / 'recipes').mkdir(parents=True, exist_ok=True)
    return c_dir

def get_civitai_credentials_path() -> Path:
    cfg_dir = _get_suite_root() / 'CONFIG'
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / 'civitai_credentials.json'

def _get_asset_url_registry_path() -> Path:
    cfg_dir = _get_suite_root() / 'CONFIG'
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / 'civitai_asset_urls.json'

def load_asset_url_registry() -> dict:
    p = _get_asset_url_registry_path()
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding='utf-8'))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}

def register_asset_download_metadata(filename: str, download_url: str, asset_type: str='LORA', modality: str='IMAGE', sample_url: str='', trigger_words: list=None, optimal_settings: dict=None, author_desc: str='', sample_metas: list=None, base_model: str='', author_name: str=''):
    fname = str(filename or '').strip()
    d_url = str(download_url or '').strip()
    if not fname or not d_url.startswith('http'):
        return
    reg = load_asset_url_registry()
    base_key = os.path.basename(fname)
    prev_entry = reg.get(base_key) if isinstance(reg.get(base_key), dict) else {}
    entry = {
        'filename': base_key,
        'download_url': d_url,
        'asset_type': str(asset_type or prev_entry.get('asset_type') or 'LORA'),
        'modality': str(modality or prev_entry.get('modality') or 'IMAGE').upper(),
        'sample_url': str(sample_url or prev_entry.get('sample_url') or ''),
        'trigger_words': list(trigger_words or prev_entry.get('trigger_words') or []),
        'optimal_settings': dict(optimal_settings or prev_entry.get('optimal_settings') or {}),
        'author_desc': str(author_desc or prev_entry.get('author_desc') or '')[:3500],
        'sample_metas': list(sample_metas or prev_entry.get('sample_metas') or [])[:8],
        'base_model': str(base_model or prev_entry.get('base_model') or ''),
        'author_name': str(author_name or prev_entry.get('author_name') or ''),
        'updated_at': int(time.time()),
    }
    reg[base_key] = entry
    mod_prefix = 'VID_' if entry['modality'] == 'VIDEO' else 'IMG_'
    if not base_key.upper().startswith(('VID_', 'IMG_')):
        reg[f'{mod_prefix}{base_key}'] = entry
    try:
        _get_asset_url_registry_path().write_text(json.dumps(reg, indent=2), encoding='utf-8')
    except Exception:
        pass

def verify_civitai_license_status() -> dict:
    root = _get_suite_root()
    search_dirs = [root, root / 'EZ_ENGINES', root.parent.parent, root.parent.parent / 'CONFIG', root.parent.parent / 'EZ_LICENSE', root.parent.parent.parent, root.parent.parent.parent / 'CONFIG', root.parent.parent.parent / 'EZ_LICENSE', Path('D:/EZ_Studio_DevTools'), Path('D:/EZ_Studio_DevTools/CONFIG')]
    try:
        from .engine_ez_02_cinematrix_qwenvl_timeline import _verify_cinematrix_license_active
        if _verify_cinematrix_license_active(search_dirs):
            return {'licensed': True, 'tier': 'LICENSED_PRO', 'allowed_domains': ['civitai.com', 'civitai.red', 'both'], 'badge': 'LICENSED PRO (civitai.com + civitai.red)'}
    except Exception:
        pass
    return {'licensed': False, 'tier': 'FREEMIUM', 'allowed_domains': ['civitai.com'], 'badge': 'FREEMIUM (Endast civitai.com Blue)'}

def load_civitai_api_key() -> str:
    cred_path = get_civitai_credentials_path()
    if cred_path.exists():
        try:
            data = json.loads(cred_path.read_text(encoding='utf-8'))
            if isinstance(data, dict):
                return str(data.get('civitai_api_key', '') or '').strip()
        except Exception:
            pass
    return str(os.environ.get('CIVITAI_API_KEY', '') or '').strip()

def save_civitai_api_key(api_key: str) -> dict:
    clean_key = str(api_key or '').strip()
    cred_path = get_civitai_credentials_path()
    payload = {'civitai_api_key': clean_key, 'updated_at': int(time.time())}
    cred_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    try:
        os.chmod(str(cred_path), 384)
    except Exception:
        pass
    masked = f'{clean_key[:4]}...{clean_key[-4:]}' if len(clean_key) >= 8 else 'SET' if clean_key else 'NONE'
    return {'status': 'ok', 'has_key': bool(clean_key), 'masked_key': masked}

def purge_civitai_cache(force_clear_all: bool=False, max_age_days: int=CACHE_TTL_DAYS) -> dict:
    cache_root = get_civitai_cache_dir()
    now_ts = time.time()
    ttl_sec = max(1, int(max_age_days)) * 86400
    removed_count = 0
    freed_bytes = 0
    remaining_count = 0
    for sub in ('thumbs', 'queries'):
        target_d = cache_root / sub
        if not target_d.exists():
            continue
        for fpath in target_d.iterdir():
            if not fpath.is_file():
                continue
            try:
                st = fpath.stat()
                age = now_ts - st.st_mtime
                if force_clear_all or age >= ttl_sec:
                    fsize = st.st_size
                    fpath.unlink()
                    removed_count += 1
                    freed_bytes += fsize
                else:
                    remaining_count += 1
            except Exception:
                pass
    return {'status': 'ok', 'force_cleared': bool(force_clear_all), 'ttl_days': int(max_age_days), 'removed_files': removed_count, 'remaining_files': remaining_count, 'freed_kb': round(freed_bytes / 1024.0, 2)}

_TRUE_TURBO_LORA_REGEX = re.compile(
    r'(?:raw_to_turbo|krea2_turbo|krea_turbo|minimax_h3_turbo|wan_turbo|ltxv?_turbo|hunyuan_turbo|'
    r'flux[\._-]?1?[\._-]?turbo|turbo[\._-]?alpha|turbo[\._-]?lora|sdxl[\._-]?lightning|'
    r'lightning[\._-]?\d+step|hyper[\._-](?:sd|flux|sdxl|lora)|\b(?:4|8)[\._-]?steps?\b|'
    r'step600|causvid|lightx2v|self_forcing|fastvideo|dmd2|\blcm[\._-]?lora\b)',
    re.IGNORECASE,
)
_FALSE_TURBO_STYLE_REGEX = re.compile(
    r'(?:hyper[\._-]?real|hyper[\._-]?detail|hyper[\._-]?skin|hyper[\._-]?body|hyper[\._-]?breast|'
    r'hyperbolic|photoslider|slider|detailer|character|clothing|outfit|pose_lora|breast|nude|nsfw|ero)',
    re.IGNORECASE,
)
_VIDEO_TOKEN_REGEX = re.compile(
    r'(?:\bminimax\b|\bh3\b|\bhailuo\b|\bpdmd\b|\bsingularity\b|\bwan(?:2\.1|2\.2|_2\.1|_2\.2|_video|_i2v|_t2v)?\b|'
    r'\bltxv\b|\bltx[-_]video\b|\bhunyuan[-_\s]?video\b|\bhunyuanvideo\b|\bmochi\b|\bcogvideox?\b|'
    r'\banimatediff\b|\bi2v\b|\bt2v\b|\bfl2va\b|\bref2va\b|\bvbvr\b)',
    re.IGNORECASE,
)
_IMAGE_TOKEN_REGEX = re.compile(
    r'(?:\bkrea2?\b|\bkrea[-_\s]?2\b|\bflux\b|\bsdxl\b|\bsd15\b|\bsd[-_\s]?1\.5\b|\bsd[-_\s]?3\.5\b|'
    r'\bsd3\b|\bpony\b|\bpdxl\b|\billustrious\b|\bilxl\b|\bnoobai\b|\bqwen[-_\s]?image\b|\bkolors\b|'
    r'\bpixart\b|\bjuggernaut\b|\brealvis\b|\blustify\b|\bcyberrealistic\b|\bautismmix\b|\bchroma\b)',
    re.IGNORECASE,
)


def _is_true_turbo_acceleration_lora(name_str: str) -> bool:
    raw = str(name_str or '').replace('\\', '/').strip().lower()
    if not raw or raw == 'none':
        return False
    base_name = os.path.basename(raw)
    if '/turbo/' in f'/{raw}' or raw.startswith('turbo/'):
        return True
    if _FALSE_TURBO_STYLE_REGEX.search(base_name) and not any(
        k in base_name for k in ('raw_to_turbo', 'step600', 'sdxl_lightning', '4step', '8step', 'lcm_lora', 'dmd2', 'causvid')
    ):
        return False
    if _TRUE_TURBO_LORA_REGEX.search(base_name):
        return True
    return False


def classify_modality_from_metadata(base_model_str: str='', name_str: str='', tags: list=None) -> str:
    bm_low = str(base_model_str or '').strip().lower()
    nm_low = str(name_str or '').replace('\\', '/').strip().lower()
    base_fn = os.path.basename(nm_low)
    if base_fn.startswith('vid_') or any(seg in ('h3', 'minimax', 'wan', 'ltxv', 'hunyuan_video', 'video') for seg in nm_low.split('/')[:-1]):
        return 'VIDEO'
    if base_fn.startswith('img_') or any(seg in ('krea2', 'krea', 'flux', 'sdxl', 'pony', 'illustrious', 'image') for seg in nm_low.split('/')[:-1]):
        return 'IMAGE'
    if bm_low:
        if _IMAGE_TOKEN_REGEX.search(bm_low):
            return 'IMAGE'
        if _VIDEO_TOKEN_REGEX.search(bm_low):
            return 'VIDEO'
    if _IMAGE_TOKEN_REGEX.search(nm_low) and not _VIDEO_TOKEN_REGEX.search(nm_low):
        return 'IMAGE'
    if _VIDEO_TOKEN_REGEX.search(nm_low) and not _IMAGE_TOKEN_REGEX.search(nm_low):
        return 'VIDEO'
    if _VIDEO_TOKEN_REGEX.search(base_fn):
        return 'VIDEO'
    if _IMAGE_TOKEN_REGEX.search(base_fn):
        return 'IMAGE'
    explicit_video_tags = {
        'minimax', 'minimax h3', 'hailuo', 'wan', 'wan 2.1', 'wan 2.2', 'wan video',
        'ltxv', 'ltx-video', 'hunyuan video', 'i2v', 't2v', 'text-to-video', 'image-to-video', 'animatediff',
    }
    for t in (tags or []):
        t_clean = str(t or '').strip().lower()
        if t_clean in explicit_video_tags:
            return 'VIDEO'
    return 'IMAGE'


def inspect_safetensors_modality(file_path: str, rel_name: str = '') -> str:
    combined_path = str(rel_name or file_path or '').replace('\\', '/').lower()
    low_name = os.path.basename(file_path or rel_name or '').lower()
    if low_name.startswith('vid_') or any(seg in ('h3', 'minimax', 'wan', 'ltxv', 'hunyuan_video', 'video') for seg in combined_path.split('/')[:-1]):
        return 'VIDEO'
    if low_name.startswith('img_') or any(seg in ('krea2', 'krea', 'flux', 'sdxl', 'pony', 'illustrious', 'image') for seg in combined_path.split('/')[:-1]):
        return 'IMAGE'
    if file_path and os.path.isfile(file_path):
        fp_obj = Path(file_path)
        for sc_cand in (fp_obj.with_suffix('.civitai.info'), fp_obj.with_suffix('.json'), Path(f'{file_path}.civitai.info')):
            if sc_cand.is_file():
                try:
                    sc_data = json.loads(sc_cand.read_text(encoding='utf-8', errors='ignore'))
                    if isinstance(sc_data, dict):
                        sc_bm = str(sc_data.get('baseModel', '') or '').strip()
                        if sc_bm:
                            if _IMAGE_TOKEN_REGEX.search(sc_bm):
                                return 'IMAGE'
                            if _VIDEO_TOKEN_REGEX.search(sc_bm):
                                return 'VIDEO'
                except Exception:
                    pass
    if _IMAGE_TOKEN_REGEX.search(combined_path) and not _VIDEO_TOKEN_REGEX.search(combined_path):
        return 'IMAGE'
    if _VIDEO_TOKEN_REGEX.search(combined_path) and not _IMAGE_TOKEN_REGEX.search(combined_path):
        return 'VIDEO'
    if not file_path or not os.path.isfile(file_path) or (not low_name.endswith(('.safetensors', '.sft'))):
        return 'UNKNOWN'
    try:
        with open(file_path, 'rb') as f:
            header_len_bytes = f.read(8)
            if len(header_len_bytes) < 8:
                return 'UNKNOWN'
            header_len = struct.unpack('<Q', header_len_bytes)[0]
            if header_len <= 0 or header_len > 24 * 1024 * 1024:
                return 'UNKNOWN'
            header_raw = f.read(min(header_len, 512 * 1024)).decode('utf-8', errors='ignore').lower()
            if any(ik in header_raw for ik in (
                'double_blocks.', 'single_blocks.', 'lora_unet_double_blocks_', 'lora_unet_single_blocks_',
                'conditioner.embedders.', 'lora_te1_', 'lora_te2_', 'lora_te_text_model_',
                'down_blocks.0.attentions.', 'up_blocks.1.attentions.', 'ss_base_model_version":"sdxl',
                'ss_base_model_version":"flux', 'ss_base_model_version":"sd_',
            )):
                if not any(vk in header_raw for vk in ('audio_vae', 'audio_blocks', 'minimax', 'wan_video', 'temporal_transformer')):
                    return 'IMAGE'
            if any(vk in header_raw for vk in (
                'audio_vae', 'audio_blocks', 'minimax', 'wan_video', 'ltxv', 'temporal_transformer',
                'temp_attentions', 'time_mixer', 'blocks.0.cross_attn.k_img', 'patch_embedding.weight',
            )):
                return 'VIDEO'
    except Exception:
        return 'UNKNOWN'
    return 'UNKNOWN'

def _find_local_asset_full_path(asset_name: str, folder_category: str='loras') -> tuple:
    clean_name = str(asset_name or 'None').strip()
    if not clean_name or clean_name in ('None', 'Same as Primary (fl2va)'):
        return ('', '')
    cats = [folder_category] + [c for c in ('loras', 'diffusion_models', 'unet', 'checkpoints') if c != folder_category]
    base_only = os.path.basename(clean_name)
    prefixed_candidates = [clean_name, base_only, f'IMG_{base_only}', f'VID_{base_only}']
    for cat in cats:
        if cat not in folder_paths.folder_names_and_paths:
            continue
        for cand_name in prefixed_candidates:
            p = folder_paths.get_full_path(cat, cand_name)
            if p and os.path.isfile(p):
                return (cand_name, p)
        for existing_rel in folder_paths.get_filename_list(cat):
            if os.path.basename(existing_rel).lower() in [c.lower() for c in prefixed_candidates]:
                p = folder_paths.get_full_path(cat, existing_rel)
                if p and os.path.isfile(p):
                    return (existing_rel, p)
    return ('', '')

def ensure_civitai_asset_local(asset_name: str, folder_category: str='loras', expected_modality: str='IMAGE') -> str:
    clean_name = str(asset_name or 'None').strip()
    if not clean_name or clean_name in ('None', 'Same as Primary (fl2va)'):
        return 'None'
    (resolved_rel, full_p) = _find_local_asset_full_path(clean_name, folder_category)
    if full_p:
        return resolved_rel
    reg = load_asset_url_registry()
    base_key = os.path.basename(clean_name)
    meta = reg.get(clean_name) or reg.get(base_key)
    if not meta:
        for (_, v) in reg.items():
            if isinstance(v, dict) and str(v.get('filename', '')).lower() == base_key.lower():
                meta = v
                break
    if isinstance(meta, dict) and str(meta.get('download_url', '')).startswith('http'):
        asset_type = 'LORA' if folder_category == 'loras' else str(meta.get('asset_type', 'Checkpoint'))
        print(f'[EZ-CIVITAI-AUTO] ⬇️ Saknad resurs "{clean_name}" hittades i Civitai-registret — laddar ner automatiskt...')
        dl_res = download_civitai_asset_to_comfyui(download_url=str(meta['download_url']), filename=base_key, asset_type=asset_type, modality=str(expected_modality or meta.get('modality', 'IMAGE')), sample_url=str(meta.get('sample_url', '')))
        if dl_res.get('status') == 'ok' and dl_res.get('filename'):
            return str(dl_res['filename'])
    return clean_name

_INTERNAL_EZ_CACHE_TAGS = ('_ez_fp8_e4m3fn_cache', '_ez_fp16_vae_cache', '_ez_hadamard_v2_fp8', '_ez_hadamard_v2_fp16_vae', '_ez_q8_safetensors_cache')


def _is_internal_ez_cache_file(name_or_path: str) -> bool:
    low = str(name_or_path or '').lower()
    return any((tag in low for tag in _INTERNAL_EZ_CACHE_TAGS))


def _purge_stale_internal_cache_files() -> int:
    removed = 0
    for cat in ('diffusion_models', 'unet', 'checkpoints', 'vae'):
        if cat not in folder_paths.folder_names_and_paths:
            continue
        for root_dir in folder_paths.get_folder_paths(cat):
            if not root_dir or not os.path.isdir(root_dir):
                continue
            for r_str, _, files in os.walk(root_dir):
                for fn in files:
                    fn_low = fn.lower()
                    if any((tag in fn_low for tag in ('_ez_fp8_e4m3fn_cache', '_ez_fp16_vae_cache', '_ez_hadamard_v2_fp8', '_ez_hadamard_v2_fp16_vae'))):
                        fp = os.path.join(r_str, fn)
                        try:
                            os.remove(fp)
                            removed += 1
                            print(f'[EZ-CACHE-CLEANUP] 🧹 Raderade gammal intern cachefil: {fn}')
                        except Exception:
                            pass
    if removed > 0:
        try:
            for (_, v) in folder_paths.folder_names_and_paths.items():
                if isinstance(v, (list, tuple)) and len(v) >= 3 and isinstance(v[2], dict):
                    v[2].clear()
        except Exception:
            pass
    return removed


def _classify_asset_true_role(name_str: str, full_path: str = '', asset_type_hint: str = '') -> str:
    raw = str(name_str or '').strip()
    if not raw or raw in ('None', 'Same as Primary (fl2va)'):
        return 'NONE'
    base_low = os.path.basename(raw).lower()
    for pfx in ('img_', 'vid_'):
        if base_low.startswith(pfx):
            base_low = base_low[len(pfx):]
    if 'mmproj' in base_low and base_low.endswith('.gguf'):
        return 'MMPROJ'
    is_vlm_name = any((k in base_low for k in ('qwen3vl', 'qwen3-vl', 'qwen3_vl', 'qwen2.5-vl', 'qwen2_5_vl', 'qwen-vl', 'qwen_vl', 'huihui', 'llava', 'florence', 'minicpm', 'internvl')))
    if is_vlm_name and base_low.endswith('.gguf'):
        return 'VLM'
    is_comfy_te = any((k in base_low for k in ('comfyui', '4b_fp8', 'full_fp8', 'minimax_h3', 'minimax', 'nvfp4', 'awq', 'krea2', 'te_fp8', 'text_encoder')))
    if is_vlm_name and ('instruct' in base_low or 'chat' in base_low or '8b' in base_low or '7b' in base_low) and (not is_comfy_te):
        return 'VLM'
    if any((k in base_low for k in ('qwen3vl', 'qwen3-vl', 'qwen3_vl', 'qwen2.5-vl', 'qwen-vl', 'qwen_vl', 't5xxl', 'umt5', 'clip_l', 'clip_g', 'text_encoder', 'te_fp8', 'llava_llama3', 'minimax_h3_nvfp4'))):
        return 'CLIP'
    if 'audio_vae' in base_low:
        return 'AUDIO_VAE'
    if base_low in ('ae.safetensors', 'ae.sft', 'qwen_image_vae.safetensors', 'wan_2.1_vae.safetensors', 'wan_2.2_vae.safetensors', 'sdxl_vae.safetensors') or any((k in base_low for k in ('_vae', 'video_vae', 'flux_vae', 'vae_fp16', 'vae_bf16', 'vae_int8'))):
        return 'VAE'
    hint_up = str(asset_type_hint or '').upper()
    fsize_mb = 0.0
    if full_path and os.path.isfile(full_path):
        try:
            fsize_mb = os.path.getsize(full_path) / (1024.0 * 1024.0)
        except Exception:
            fsize_mb = 0.0
        if str(full_path).lower().endswith(('.safetensors', '.sft')):
            try:
                with open(full_path, 'rb') as fh:
                    hl_b = fh.read(8)
                    if len(hl_b) == 8:
                        hl = struct.unpack('<Q', hl_b)[0]
                        if 0 < hl <= 24 * 1024 * 1024:
                            h_str = fh.read(min(hl, 256 * 1024)).decode('utf-8', errors='ignore').lower()
                            has_lora_keys = any(lk in h_str for lk in ('.lora_down.', '.lora_up.', 'lora_unet_', 'lora_te_', '.dora_scale'))
                            has_full_unet = any(uk in h_str for uk in (
                                'double_blocks.0.img_attn.qkv.weight',
                                'model.diffusion_model.input_blocks.0.0.weight',
                                'model.diffusion_model.down_blocks.0.',
                                'patch_embedding.weight',
                                'blocks.0.self_attn.q.weight',
                            )) and (not has_lora_keys)
                            if has_lora_keys and not has_full_unet:
                                return 'LORA'
                            if has_full_unet and fsize_mb > 1400.0:
                                return 'UNET'
                            if ('model.layers.0.self_attn.' in h_str or 'language_model.model.layers.0.' in h_str or 'visual.blocks.0.' in h_str or 'encoder.block.0.layer.0.selfattention' in h_str) and ('double_blocks.' not in h_str and 'single_blocks.' not in h_str and 'patch_embedding' not in h_str and (not has_lora_keys)):
                                return 'CLIP'
            except Exception:
                pass
    if hint_up == 'LORA':
        if fsize_mb > 2200.0 and not re.search(r'(?:^|[\._\-\s])(?:lora|dora|lycoris|locon|loha|slider)(?:$|[\._\-\s])', base_low):
            return 'UNET'
        return 'LORA'
    if re.search(r'(?:^|[\._\-\s])(?:lora|dora|lycoris|locon|loha)(?:$|[\._\-\s])', base_low) and (fsize_mb == 0.0 or fsize_mb < 1500.0):
        return 'LORA'
    return 'UNET'


def enforce_modality_lock(expected_modality: str, asset_name: str, folder_category: str='loras', base_model_hint: str='') -> str:
    clean_name = str(asset_name or 'None').strip()
    if not clean_name or clean_name in ('None', 'Same as Primary (fl2va)'):
        return clean_name
    exp = str(expected_modality or 'IMAGE').upper()
    clean_name = ensure_civitai_asset_local(clean_name, folder_category=folder_category, expected_modality=exp)
    (_, full_p) = _find_local_asset_full_path(clean_name, folder_category)
    if folder_category in ('diffusion_models', 'unet', 'checkpoints', 'unet_gguf'):
        true_role = _classify_asset_true_role(clean_name, full_p, 'Checkpoint')
        if true_role in ('CLIP', 'VLM', 'MMPROJ', 'VAE', 'AUDIO_VAE'):
            print(f'[EZ-ROLE-GUARD] 🛡️ Blockerade "{clean_name}" (detekterad som {true_role}) från att skickas som UNet-huvudmodell till {"[05]" if exp == "VIDEO" else "[03]"}!')
            return 'None'
    detected = inspect_safetensors_modality(full_p) if full_p else 'UNKNOWN'
    if detected == 'UNKNOWN':
        detected = classify_modality_from_metadata(base_model_hint, clean_name)
    if exp == 'IMAGE' and detected == 'VIDEO':
        raise ValueError(f'[EZ-MODALITY-LOCK] SÄKERHETSLÅS: Video-modellen/LoRAn "{clean_name}" (MiniMax H3 / Wan / LTXV) får INTE kopplas till en IMAGE Loader (KREA2 / Flux / SDXL)!')
    if exp == 'VIDEO' and detected == 'IMAGE':
        if any((k in (clean_name + ' ' + str(base_model_hint)).lower() for k in ('krea', 'flux', 'sdxl', 'pony', 'illustrious', 'sd15', 'qwen_image'))):
            raise ValueError(f'[EZ-MODALITY-LOCK] SÄKERHETSLÅS: Bild-modellen/LoRAn "{clean_name}" (KREA2 / Flux / SDXL) får INTE kopplas till en VIDEO Loader (MiniMax H3 / Wan / LTXV)!')
    return clean_name

def _normalize_arch_key(architecture: str, modality: str='IMAGE') -> str:
    low = str(architecture or '').lower()
    if 'minimax' in low or 'h3' in low or 'hailuo' in low:
        return 'MINIMAX_H3'
    if 'wan' in low:
        return 'WAN'
    if 'ltx' in low:
        return 'LTXV'
    if 'hunyuan' in low:
        return 'HUNYUAN_VIDEO'
    if 'krea' in low:
        return 'KREA2'
    if 'qwen' in low:
        return 'QWEN_IMAGE'
    if 'pony' in low or 'pdxl' in low or 'autismmix' in low:
        return 'PONY'
    if 'illustrious' in low or 'ilxl' in low or 'noobai' in low or 'wai-nsfw' in low:
        return 'ILLUSTRIOUS'
    if 'sdxl' in low:
        return 'SDXL'
    if 'flux' in low and 'krea' not in low:
        return 'FLUX'
    if str(modality or 'IMAGE').upper() == 'VIDEO':
        return 'MINIMAX_H3'
    return 'KREA2'

_HEADER_QUANT_CACHE: dict = {}


def _inspect_safetensors_quant_and_arch_profile(file_path: str = '', rel_name: str = '', asset_type: str = 'CHECKPOINT', size_mb: float = 0.0) -> dict:
    nm_l = str(rel_name or os.path.basename(file_path or '')).lower()
    at_u = str(asset_type or 'CHECKPOINT').upper()
    cache_key = ''
    if file_path and os.path.isfile(file_path):
        try:
            st_m = os.stat(file_path)
            cache_key = f'{file_path}:{int(st_m.st_mtime)}:{st_m.st_size}:{at_u}'
            if cache_key in _HEADER_QUANT_CACHE:
                return dict(_HEADER_QUANT_CACHE[cache_key])
        except Exception:
            cache_key = ''
    has_convrot = any((k in nm_l for k in ('convrot', 'hadamard')))
    has_nvfp4_awq = any((k in nm_l for k in ('nvfp4', 'awq', 'int4')))
    has_int8 = ('int8' in nm_l) or has_convrot
    has_fp8_scaled = any((k in nm_l for k in ('fp8_scaled', 'e4m3fn_scaled', 'scaled_fp8', '_scaled')))
    has_fp8 = any((k in nm_l for k in ('fp8', 'e4m3', 'e5m2'))) or has_fp8_scaled
    has_gguf_q8 = ('q8_0' in nm_l) or ('q8' in nm_l and nm_l.endswith('.gguf'))
    has_gguf_sub8 = any((k in nm_l for k in ('q6_k', 'q5_k', 'q5_0', 'q4_k', 'q4_0', 'iq4')))
    has_bf16_fp16 = any((k in nm_l for k in ('bf16', 'fp16', 'f16')))
    has_fp32 = 'fp32' in nm_l or 'f32' in nm_l
    clip_proj_dim = 0
    header_inspected = False
    if file_path and os.path.isfile(file_path) and str(file_path).lower().endswith(('.safetensors', '.sft')):
        try:
            with open(file_path, 'rb') as fh:
                hl_b = fh.read(8)
                if len(hl_b) == 8:
                    hl = struct.unpack('<Q', hl_b)[0]
                    if 0 < hl <= 24 * 1024 * 1024:
                        h_raw = fh.read(min(hl, 384 * 1024)).decode('utf-8', errors='ignore')
                        h_low = h_raw.lower()
                        header_inspected = True
                        if 'qweight' in h_low or 'qzeros' in h_low or 'nvfp4' in h_low:
                            has_nvfp4_awq = True
                        if '_quantization_metadata' in h_low or 'comfy_quant' in h_low:
                            has_convrot = True
                            has_int8 = True
                        if '"dtype":"i8"' in h_low or '"dtype": "i8"' in h_low:
                            has_int8 = True
                        if '"dtype":"f8_e4m3"' in h_low or '"dtype": "f8_e4m3"' in h_low or '"dtype":"f8_e5m2"' in h_low:
                            has_fp8 = True
                            if 'scale_weight' in h_low or 'scale_input' in h_low or 'weight_scale' in h_low:
                                has_fp8_scaled = True
                        if (not has_int8 and (not has_fp8) and (not has_nvfp4_awq)):
                            if '"dtype":"bf16"' in h_low or '"dtype": "bf16"' in h_low or '"dtype":"f16"' in h_low or '"dtype": "f16"' in h_low:
                                has_bf16_fp16 = True
                            elif '"dtype":"f32"' in h_low or '"dtype": "f32"' in h_low:
                                has_fp32 = True
                        if at_u == 'CLIP' or 'visual.merger.' in h_low or 'layers.0.self_attn' in h_low:
                            if 'layers.60.' in h_low or 'layers.63.' in h_low or '32b' in nm_l or 'minimax_h3' in nm_l:
                                clip_proj_dim = 5120
                            elif 'layers.35.' in h_low and 'layers.40.' not in h_low:
                                clip_proj_dim = 2560
                            elif '[5120,' in h_low or ', 5120]' in h_low or ',5120]' in h_low:
                                clip_proj_dim = 5120 if ('32b' in nm_l or 'minimax' in nm_l) else 2560
                            elif '[2560,' in h_low or ', 2560]' in h_low or ',2560]' in h_low:
                                clip_proj_dim = 2560
        except Exception:
            pass
    if at_u == 'CLIP' and clip_proj_dim == 0:
        if any((k in nm_l for k in ('32b', 'minimax_h3', 'minimax'))):
            clip_proj_dim = 5120
        elif any((k in nm_l for k in ('4b', 'abliteratedcomfyui', 'krea2', 'qwen_2.5_vl', 'qwen2.5-vl'))):
            clip_proj_dim = 2560
    is_uncensored_raw = any((k in nm_l for k in ('abliterated', 'uncensored', 'raw', 'nsfw', 'nude', 'sex', 'snofs', 'lustify', 'ero', 'pony', 'adult', 'singularity', 'prism')))
    is_distilled_ckpt = (at_u in ('CHECKPOINT', 'UNET')) and any((k in nm_l for k in ('distill', 'cfgdistill', 'turbo', 'hyper', 'lightning', '4step', '8step')))
    disk_mb = float(size_mb or 0.0)
    auto_quant_active = False
    if has_nvfp4_awq:
        quant_tier = 'NVFP4_AWQ'
        quant_label = 'NVFP4/AWQ 4-Bit Quantized Safetensors'
        quant_rank = 1
        eff_vram_mb = round(disk_mb * 1.02, 1) if disk_mb > 0 else 14900.0
    elif has_convrot or has_int8:
        quant_tier = 'INT8_CONVROT'
        quant_label = 'Int8 ConvRot (Hadamard Safetensors)' if has_convrot else 'Int8 Safetensors'
        quant_rank = 1
        eff_vram_mb = round(disk_mb * 1.02, 1) if disk_mb > 0 else 11200.0
    elif has_fp8_scaled:
        quant_tier = 'FP8_SCALED'
        quant_label = 'FP8 Scaled Safetensors (Dynamic Block-Scale)'
        quant_rank = 1
        eff_vram_mb = round(disk_mb * 1.02, 1) if disk_mb > 0 else 11400.0
    elif has_fp8:
        quant_tier = 'FP8_STANDARD'
        quant_label = 'FP8 e4m3fn Safetensors'
        quant_rank = 1
        eff_vram_mb = round(disk_mb * 1.02, 1) if disk_mb > 0 else 11400.0
    elif at_u in ('CHECKPOINT', 'UNET') and (has_bf16_fp16 or disk_mb > 14500) and (not nm_l.endswith('.gguf')):
        quant_tier = 'AUTO_QUANT_FP8'
        quant_label = 'Safetensors BF16/FP16 -> EZ Auto-Quant FP8 (FP16-Accum)'
        quant_rank = 2
        auto_quant_active = True
        eff_vram_mb = round(disk_mb * 0.52, 1) if disk_mb > 0 else 11500.0
    elif at_u == 'VLM' and (not nm_l.endswith('.gguf')) and disk_mb > 11000:
        quant_tier = 'AUTO_QUANT_NF4'
        quant_label = 'HF Safetensors -> EZ Auto-Quant Q8/NF4 Cache'
        quant_rank = 2
        auto_quant_active = True
        eff_vram_mb = round(disk_mb * 0.50, 1)
    elif has_fp32 and (not nm_l.endswith('.gguf')):
        quant_tier = 'FP32_FULL'
        quant_label = 'FP32 Full Precision Safetensors'
        quant_rank = 1 if at_u == 'AUDIO_VAE' else 3
        eff_vram_mb = disk_mb
    elif has_gguf_q8:
        quant_tier = 'GGUF_Q8_0'
        quant_label = 'GGUF Q8_0 (Legacy Block-Dequant)'
        quant_rank = 4
        eff_vram_mb = round(disk_mb * 1.03, 1) if disk_mb > 0 else 8900.0
    elif has_gguf_sub8:
        quant_tier = 'GGUF_SUB8'
        quant_label = 'GGUF Q6_K/Q4_K_M (Legacy Block-Dequant)'
        quant_rank = 5
        eff_vram_mb = round(disk_mb * 1.03, 1) if disk_mb > 0 else 6500.0
    else:
        quant_tier = 'BF16_NATIVE'
        quant_label = 'BF16/FP16 Native Safetensors'
        quant_rank = 2
        eff_vram_mb = round(disk_mb * (0.52 if at_u in ('CHECKPOINT', 'UNET') and disk_mb > 14500 else 1.0), 1)
    res = {
        'quant_tier': quant_tier,
        'quant_label': quant_label,
        'quant_rank': quant_rank,
        'auto_quant_active': auto_quant_active,
        'disk_size_mb': round(disk_mb, 1),
        'disk_size_gb': round(disk_mb / 1024.0, 2),
        'effective_vram_mb': round(eff_vram_mb, 1),
        'effective_vram_gb': round(eff_vram_mb / 1024.0, 2),
        'clip_proj_dim': clip_proj_dim,
        'is_uncensored_raw': is_uncensored_raw,
        'is_distilled_checkpoint': is_distilled_ckpt,
        'header_inspected': header_inspected,
    }
    if cache_key:
        _HEADER_QUANT_CACHE[cache_key] = dict(res)
    return res


_LOCAL_SAFETENSORS_META_CACHE = {}


def _extract_local_safetensors_training_meta(file_path: str) -> dict:
    if not file_path or not os.path.isfile(file_path):
        return {}
    try:
        st = os.stat(file_path)
        ck = f'{file_path}:{int(st.st_mtime)}:{st.st_size}'
        if ck in _LOCAL_SAFETENSORS_META_CACHE:
            return dict(_LOCAL_SAFETENSORS_META_CACHE[ck])
    except Exception:
        ck = ''
    out = {
        'network_dim': 0,
        'network_alpha': 0.0,
        'clip_skip': 0,
        'base_model_version': '',
        'modelspec_arch': '',
        'modelspec_title': '',
        'resolution': '',
        'trained_tags': [],
        'sidecar_desc': '',
        'sidecar_metas': [],
        'sidecar_words': [],
        'sidecar_base_model': '',
    }
    fp_obj = Path(file_path)
    for sc_cand in (
        fp_obj.with_suffix('.civitai.info'),
        fp_obj.with_suffix('.json'),
        Path(f'{file_path}.civitai.info'),
        Path(f'{file_path}.json'),
    ):
        if sc_cand.is_file():
            try:
                sc_data = json.loads(sc_cand.read_text(encoding='utf-8', errors='ignore'))
                if isinstance(sc_data, dict):
                    m_sub = sc_data.get('model') if isinstance(sc_data.get('model'), dict) else {}
                    out['sidecar_desc'] = f"{sc_data.get('description', '') or ''} {m_sub.get('description', '') or ''}".strip()
                    out['sidecar_base_model'] = str(sc_data.get('baseModel', '') or '')
                    tw = sc_data.get('trainedWords')
                    if isinstance(tw, list):
                        out['sidecar_words'] = [str(w).strip() for w in tw if w and str(w).strip()][:12]
                    imgs = sc_data.get('images')
                    if isinstance(imgs, list):
                        for im in imgs:
                            if isinstance(im, dict) and isinstance(im.get('meta'), dict):
                                out['sidecar_metas'].append(im['meta'])
                    break
            except Exception:
                pass
    if str(file_path).lower().endswith(('.safetensors', '.sft')):
        try:
            with open(file_path, 'rb') as fh:
                hl_b = fh.read(8)
                if len(hl_b) == 8:
                    hl = struct.unpack('<Q', hl_b)[0]
                    if 0 < hl <= 24 * 1024 * 1024:
                        h_raw = fh.read(min(hl, 512 * 1024)).decode('utf-8', errors='ignore')
                        h_json = json.loads(h_raw) if h_raw.strip().startswith('{') else {}
                        meta = h_json.get('__metadata__') if isinstance(h_json, dict) and isinstance(h_json.get('__metadata__'), dict) else {}
                        if meta:
                            dim_raw = str(meta.get('ss_network_dim', '') or '').strip()
                            alpha_raw = str(meta.get('ss_network_alpha', '') or '').strip()
                            cs_raw = str(meta.get('ss_clip_skip', '') or '').strip()
                            if dim_raw.isdigit():
                                out['network_dim'] = int(dim_raw)
                            try:
                                if alpha_raw and alpha_raw.lower() != 'none':
                                    out['network_alpha'] = float(alpha_raw)
                            except Exception:
                                pass
                            if cs_raw.isdigit():
                                out['clip_skip'] = int(cs_raw)
                            out['base_model_version'] = str(meta.get('ss_base_model_version', '') or meta.get('modelspec.architecture', '') or '')
                            out['modelspec_arch'] = str(meta.get('modelspec.architecture', '') or '')
                            out['modelspec_title'] = str(meta.get('modelspec.title', '') or '')
                            out['resolution'] = str(meta.get('ss_resolution', '') or meta.get('modelspec.resolution', '') or '')
                            tf_raw = meta.get('ss_tag_frequency')
                            if isinstance(tf_raw, str) and tf_raw.strip().startswith('{'):
                                try:
                                    tf_dict = json.loads(tf_raw)
                                    tag_counts = {}
                                    for sub_d in tf_dict.values():
                                        if isinstance(sub_d, dict):
                                            for k_tag, cnt in sub_d.items():
                                                t_cl = str(k_tag).strip()
                                                if t_cl and len(t_cl) > 2 and (not t_cl.isdigit()):
                                                    tag_counts[t_cl] = tag_counts.get(t_cl, 0) + int(cnt or 0)
                                    top_tags = [k for (k, _) in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]]
                                    out['trained_tags'] = top_tags
                                except Exception:
                                    pass
        except Exception:
            pass
    if ck:
        _LOCAL_SAFETENSORS_META_CACHE[ck] = dict(out)
    return out


def _resolve_local_asset_full_path(asset_name: str, asset_type: str = 'LORA') -> str:
    clean_n = str(asset_name or '').strip()
    if not clean_n or clean_n == 'None':
        return ''
    if os.path.isfile(clean_n):
        return clean_n
    cats = ('loras',) if str(asset_type or '').upper() == 'LORA' else ('diffusion_models', 'unet', 'checkpoints', 'unet_gguf', 'loras')
    for c in cats:
        if c in folder_paths.folder_names_and_paths:
            try:
                p = folder_paths.get_full_path(c, clean_n)
                if p and os.path.isfile(p):
                    return p
            except Exception:
                pass
    base_only = os.path.basename(clean_n).lower()
    for c in cats:
        if c in folder_paths.folder_names_and_paths:
            try:
                for rel in folder_paths.get_filename_list(c):
                    if os.path.basename(rel).lower() == base_only:
                        p = folder_paths.get_full_path(c, rel)
                        if p and os.path.isfile(p):
                            return p
            except Exception:
                pass
    return ''


def _normalize_author_sampler_and_scheduler(raw_sampler: str, raw_sched: str = '', default_sampler: str = 'euler', default_sched: str = 'simple') -> tuple:
    s_low = f'{raw_sampler or ""} {raw_sched or ""}'.lower().strip()
    sampler = default_sampler
    scheduler = default_sched
    if 'res_multistep' in s_low or 'res multistep' in s_low:
        sampler = 'res_multistep'
    elif 'uni_pc' in s_low or 'unipc' in s_low:
        sampler = 'uni_pc'
    elif 'dpm++ 2m sde' in s_low or 'dpmpp_2m_sde' in s_low or '2m sde' in s_low:
        sampler = 'dpmpp_2m_sde'
    elif 'dpm++ 3m sde' in s_low or 'dpmpp_3m_sde' in s_low or '3m sde' in s_low:
        sampler = 'dpmpp_3m_sde'
    elif 'dpm++ 2m' in s_low or 'dpmpp_2m' in s_low:
        sampler = 'dpmpp_2m'
    elif 'dpm++ sde' in s_low or 'dpmpp_sde' in s_low:
        sampler = 'dpmpp_sde'
    elif 'euler a' in s_low or 'euler_ancestral' in s_low or 'euler ancestral' in s_low:
        sampler = 'euler_ancestral'
    elif 'heun' in s_low:
        sampler = 'heun'
    elif 'lcm' in s_low:
        sampler = 'lcm'
    elif 'ddim' in s_low:
        sampler = 'ddim'
    elif 'euler' in s_low:
        sampler = 'euler'
    if 'karras' in s_low:
        scheduler = 'karras'
    elif 'sgm_uniform' in s_low or 'sgm uniform' in s_low:
        scheduler = 'sgm_uniform'
    elif 'exponential' in s_low:
        scheduler = 'exponential'
    elif 'beta' in s_low:
        scheduler = 'beta'
    elif 'normal' in s_low:
        scheduler = 'normal'
    elif 'simple' in s_low:
        scheduler = 'simple'
    return (sampler, scheduler)


def extract_author_and_arch_optimal_settings(asset_name: str='', modality: str='IMAGE', base_arch: str='', asset_type: str='LORA', author_desc: str='', sample_metas: list=None, active_unet_name: str='', file_path: str='', size_mb: float=0.0, sys_tier: dict=None, stack_lora_count: int=1) -> dict:
    raw_name_only = str(asset_name or '').split(' ')[0].strip()
    local_fp = file_path or _resolve_local_asset_full_path(raw_name_only, asset_type)
    local_meta = _extract_local_safetensors_training_meta(local_fp) if local_fp else {}
    reg = load_asset_url_registry()
    base_fn = os.path.basename(raw_name_only)
    reg_entry = (reg.get(base_fn) or reg.get(str(asset_name or '').strip()) or {}) if isinstance(reg, dict) else {}
    eff_desc = str(author_desc or reg_entry.get('author_desc') or local_meta.get('sidecar_desc') or '')
    eff_metas = list(sample_metas or reg_entry.get('sample_metas') or local_meta.get('sidecar_metas') or [])
    eff_base_arch = str(base_arch or reg_entry.get('base_model') or local_meta.get('sidecar_base_model') or local_meta.get('base_model_version') or '')
    arch_key = _normalize_arch_key(f'{eff_base_arch} {asset_name}', modality)
    prof = dict(ARCH_OPTIMAL_SETTINGS_PROFILES.get(arch_key, ARCH_OPTIMAL_SETTINGS_PROFILES['MINIMAX_H3' if str(modality).upper() == 'VIDEO' else 'KREA2']))
    low_name = str(asset_name or '').lower()
    unet_low = str(active_unet_name or '').lower()
    desc_clean = re.sub(r'<[^>]+>', ' ', eff_desc)
    desc_clean = re.sub(r'\s+', ' ', desc_clean).strip()
    is_turbo = _is_true_turbo_acceleration_lora(asset_name) if str(asset_type).upper() == 'LORA' else any((tk in low_name for tk in ('turbo', 'lightning', 'hyper', 'lcm', 'distill', '4step', '8step', 'step600', 'raw_to_turbo')))
    is_unet_already_distilled = any((tk in unet_low for tk in ('distill', 'cfgdistill', 'turbo', 'hyper', 'lightning', '4step', '8step')))
    is_audio = any((ak in low_name for ak in ('audio', 'sound', 'voice', 'vocal', 'sfx', 'moaw', 'moan', 'whisper'))) and (not is_turbo)
    is_motion = any((mk in low_name for mk in ('motion', 'camera', 'movement', 'action', 'booster')))
    is_vbvr = any((vk in low_name for vk in ('vbvr', 'reasoning', 'physics', 'detailer', 'realism')))
    role = 'TURBO' if is_turbo else 'AUDIO' if is_audio else 'MOTION' if is_motion else 'REASONING_VBVR' if is_vbvr else 'STYLE'
    rec_str = float(prof.get('turbo_strength', 1.0) if is_turbo else (0.18 if is_motion and arch_key == 'MINIMAX_H3' else prof.get('rec_lora_strength', 0.75)))
    vis_str = 1.0
    aud_str = float(prof.get('turbo_audio_strength', 1.0) if (is_turbo and arch_key == 'MINIMAX_H3') else (1.0 if is_audio else prof.get('vis_lora_audio_strength', 0.0)))
    clip_str = float(prof.get('clip_strength', 0.0))
    sampler = str(prof.get('sampler', 'euler'))
    scheduler = str(prof.get('scheduler', 'simple'))
    steps = int(prof.get('steps', 20))
    cfg = float(prof.get('cfg', 1.0))
    denoise = float(prof.get('denoise', 1.0))
    shift_v = float(prof.get('shift_video', 5.0))
    shift_a = float(prof.get('shift_audio', 3.0))
    clip_skip = int(local_meta.get('clip_skip') or (2 if arch_key in ('PONY', 'ILLUSTRIOUS') else 1))
    net_dim = int(local_meta.get('network_dim') or 0)
    net_alpha = float(local_meta.get('network_alpha') or 0.0)
    if net_dim > 0 and str(asset_type).upper() == 'LORA' and (not is_turbo) and arch_key != 'MINIMAX_H3':
        ratio = (net_alpha / float(net_dim)) if net_alpha > 0 else 1.0
        if net_dim >= 128 or ratio >= 1.0:
            rec_str = 0.65
        elif net_dim <= 16 and ratio <= 0.5:
            rec_str = 0.85
    author_found = []
    author_weights_found = []
    author_steps_found = []
    author_cfgs_found = []
    author_sampler_str = ''
    author_scheduler_str = ''
    author_weight_range = ''
    author_steps_range = ''
    author_cfg_range = ''
    for m in eff_metas:
        if not isinstance(m, dict):
            continue
        if m.get('sampler') or m.get('scheduler'):
            (s_norm, sch_norm) = _normalize_author_sampler_and_scheduler(str(m.get('sampler', '') or ''), str(m.get('scheduler', '') or ''), sampler, scheduler)
            if not author_sampler_str:
                author_sampler_str = s_norm
                author_scheduler_str = sch_norm
                sampler = s_norm
                scheduler = sch_norm
                author_found.append(f'Sampler: {sampler}/{scheduler}')
        if m.get('steps') is not None and str(m['steps']).isdigit():
            st_val = int(m['steps'])
            if 4 <= st_val <= 80:
                author_steps_found.append(st_val)
        if m.get('cfgScale') is not None:
            try:
                c_val = float(m['cfgScale'])
                if 0.5 <= c_val <= 18.0:
                    author_cfgs_found.append(round(c_val, 1))
            except Exception:
                pass
        if m.get('clipSkip') is not None and str(m['clipSkip']).lstrip('-').isdigit():
            cs_v = abs(int(m['clipSkip']))
            if 1 <= cs_v <= 4:
                clip_skip = cs_v
                author_found.append(f'Clip Skip: {clip_skip}')
        pr_str = str(m.get('prompt', '') or '')
        for l_m in re.finditer(r'<lora:[^:>]+:([0-9]+(?:\.[0-9]+)?)>', pr_str):
            if not is_turbo:
                try:
                    w_val = float(l_m.group(1))
                    if 0.05 <= w_val <= 2.0:
                        author_weights_found.append(round(w_val, 2))
                except Exception:
                    pass
    if author_steps_found:
        steps = int(round(sum(author_steps_found) / len(author_steps_found)))
        s_min, s_max = (min(author_steps_found), max(author_steps_found))
        author_steps_range = f'{s_min}–{s_max}' if s_min != s_max else str(steps)
        author_found.append(f'Steps: {author_steps_range}')
    if author_cfgs_found:
        cfg = round(sum(author_cfgs_found) / len(author_cfgs_found), 1)
        c_min, c_max = (min(author_cfgs_found), max(author_cfgs_found))
        author_cfg_range = f'{c_min}–{c_max}' if c_min != c_max else str(cfg)
        author_found.append(f'CFG: {author_cfg_range}')
    if author_weights_found and (not is_turbo):
        raw_w_avg = round(sum(author_weights_found) / len(author_weights_found), 2)
        w_min, w_max = (min(author_weights_found), max(author_weights_found))
        author_weight_range = f'{w_min:.2f}–{w_max:.2f}' if w_min != w_max else f'{raw_w_avg:.2f}'
        rec_str = raw_w_avg if arch_key != 'MINIMAX_H3' else min(raw_w_avg, 0.35)
        author_found.append(f'Showcase Weight: {author_weight_range}')
    if desc_clean:
        w_rng_m = re.search(r'(?:weight|strength|styrka|lora\s*weight|recommended\s*weight)[^0-9]{0,18}([0-9]\.[0-9]{1,2})\s*(?:-|~|to|–|till)\s*([0-9]\.[0-9]{1,2})', desc_clean, re.IGNORECASE)
        if w_rng_m and (not is_turbo):
            try:
                w1, w2 = (float(w_rng_m.group(1)), float(w_rng_m.group(2)))
                if 0.05 <= w1 <= 1.8 and 0.05 <= w2 <= 1.8:
                    author_weight_range = f'{min(w1, w2):.2f}–{max(w1, w2):.2f}'
                    w_mid = round((w1 + w2) / 2.0, 2)
                    rec_str = w_mid if arch_key != 'MINIMAX_H3' else min(w_mid, 0.35)
                    author_found.append(f'Author Weight: {author_weight_range}')
            except Exception:
                pass
        else:
            w_match = re.search(r'(?:weight|strength|styrka|recommended\s*weight)\s*[:=-]?\s*([0-9]\.[0-9]{1,2})', desc_clean, re.IGNORECASE)
            if w_match and (not is_turbo):
                try:
                    w_v = float(w_match.group(1))
                    if 0.05 <= w_v <= 1.6:
                        if not author_weight_range:
                            author_weight_range = f'{w_v:.2f}'
                        rec_str = round(w_v if arch_key != 'MINIMAX_H3' else min(w_v, 0.35), 2)
                        author_found.append(f'Author Weight: {w_v:.2f}')
                except Exception:
                    pass
        st_rng_m = re.search(r'(?:steps|sampling\s*steps|steg)\s*[:=-]?\s*([0-9]{1,2})\s*(?:-|~|to|–)\s*([0-9]{1,2})', desc_clean, re.IGNORECASE)
        if st_rng_m:
            try:
                st1, st2 = (int(st_rng_m.group(1)), int(st_rng_m.group(2)))
                if 4 <= st1 <= 80 and 4 <= st2 <= 80:
                    author_steps_range = f'{min(st1, st2)}–{max(st1, st2)}'
                    steps = int(round((st1 + st2) / 2.0))
                    author_found.append(f'Author Steps: {author_steps_range}')
            except Exception:
                pass
        elif not author_steps_found:
            st_single_m = re.search(r'(?:steps|sampling\s*steps)\s*[:=-]?\s*([0-9]{1,2})\b|\b([0-9]{1,2})\s*steps\b', desc_clean, re.IGNORECASE)
            if st_single_m:
                try:
                    st_v = int(st_single_m.group(1) or st_single_m.group(2))
                    if 4 <= st_v <= 80:
                        steps = st_v
                        author_steps_range = str(st_v)
                        author_found.append(f'Author Steps: {st_v}')
                except Exception:
                    pass
        cfg_rng_m = re.search(r'(?:cfg|cfg\s*scale|guidance)\s*[:=-]?\s*([0-9]{1,2}(?:\.[0-9])?)\s*(?:-|~|to|–)\s*([0-9]{1,2}(?:\.[0-9])?)', desc_clean, re.IGNORECASE)
        if cfg_rng_m:
            try:
                c1, c2 = (float(cfg_rng_m.group(1)), float(cfg_rng_m.group(2)))
                if 0.5 <= c1 <= 16.0 and 0.5 <= c2 <= 16.0:
                    author_cfg_range = f'{min(c1, c2):.1f}–{max(c1, c2):.1f}'
                    cfg = round((c1 + c2) / 2.0, 1)
                    author_found.append(f'Author CFG: {author_cfg_range}')
            except Exception:
                pass
        elif not author_cfgs_found:
            cfg_single_m = re.search(r'(?:cfg|cfg\s*scale|guidance)\s*[:=-]?\s*([0-9]{1,2}(?:\.[0-9])?)', desc_clean, re.IGNORECASE)
            if cfg_single_m:
                try:
                    c_v = float(cfg_single_m.group(1))
                    if 0.5 <= c_v <= 16.0:
                        cfg = round(c_v, 1)
                        author_cfg_range = str(cfg)
                        author_found.append(f'Author CFG: {cfg}')
                except Exception:
                    pass
        if not author_sampler_str:
            smp_m = re.search(r'(?:sampler|sampling\s*method)\s*[:=-]?\s*(dpm\+\+\s*[23]m\s*sde\s*karras|dpm\+\+\s*[23]m\s*karras|dpm\+\+\s*sde\s*karras|dpm\+\+\s*[23]m|euler\s*ancestral|euler\s*a|euler|res_multistep|uni_pc|unipc|heun|ddim|lcm)', desc_clean, re.IGNORECASE)
            sch_m = re.search(r'(?:scheduler|schedule\s*type)\s*[:=-]?\s*(karras|simple|beta|sgm_uniform|normal|exponential)', desc_clean, re.IGNORECASE)
            if smp_m or sch_m:
                (sampler, scheduler) = _normalize_author_sampler_and_scheduler(smp_m.group(1) if smp_m else sampler, sch_m.group(1) if sch_m else scheduler, sampler, scheduler)
                author_sampler_str = sampler
                author_scheduler_str = scheduler
                author_found.append(f'Author Sampler: {sampler}/{scheduler}')
        cs_m = re.search(r'clip\s*skip\s*[:=-]?\s*([1-4])', desc_clean, re.IGNORECASE)
        if cs_m:
            clip_skip = int(cs_m.group(1))
            author_found.append(f'Author Clip Skip: {clip_skip}')
        sh_match = re.search(r'shift\s*[:=-]?\s*([0-9]{1,2}(?:\.[0-9])?)', desc_clean, re.IGNORECASE)
        if sh_match and str(modality).upper() == 'VIDEO':
            try:
                sh_v = float(sh_match.group(1))
                if 1.0 <= sh_v <= 15.0:
                    shift_v = sh_v
                    author_found.append(f'Shift: {shift_v}')
            except Exception:
                pass
    if arch_key == 'MINIMAX_H3':
        denoise = 1.0
        if is_turbo:
            rec_str = 0.45 if is_unet_already_distilled else 1.0
            vis_str, aud_str, clip_str = (1.0, 1.0, 0.0)
            steps, cfg, shift_v, shift_a = (8, 1.0, 5.0, 3.0)
    elif is_turbo and is_unet_already_distilled:
        rec_str = 0.45
    active_style_cnt = max(1, int(stack_lora_count or 1))
    stack_scale = 1.0 if (is_turbo or active_style_cnt <= 1) else (0.88 if active_style_cnt == 2 else 0.78)
    stack_balanced_str = round(rec_str * stack_scale, 2)
    eff_sz_mb = float(size_mb or 0.0)
    if eff_sz_mb <= 0.0 and local_fp and os.path.isfile(local_fp):
        try:
            eff_sz_mb = round(os.path.getsize(local_fp) / (1024.0 * 1024.0), 1)
        except Exception:
            pass
    q_info = _inspect_safetensors_quant_and_arch_profile(local_fp, raw_name_only, asset_type, eff_sz_mb)
    st_info = sys_tier if isinstance(sys_tier, dict) else _probe_system_and_project_tier()
    vram_gb = float(st_info.get('actual_vram_gb', 16.0) or 16.0)
    gpu_name = str(st_info.get('gpu_name', 'NVIDIA GPU'))
    tier_short = str(st_info.get('tier_short', 'Tier 1'))
    q_tier = str(q_info.get('quant_tier', 'BF16_NATIVE'))
    disk_gb = float(q_info.get('disk_size_gb', 0.0) or round(eff_sz_mb / 1024.0, 2))
    eff_vram_gb = float(q_info.get('effective_vram_gb', 0.0) or disk_gb)
    if q_tier == 'INT8_CONVROT':
        quant_tech_note = f'🧬 Int8 ConvRot + Walsh-Hadamard Kanalrotation aktiv på {gpu_name} ({vram_gb} GB VRAM / {tier_short}): Roterar aktiverings-outliers över kanaler så att råmodellen körs på ~{eff_vram_gb} GB VRAM med 99% BF16-precision.'
    elif q_tier == 'AUTO_QUANT_FP8' or bool(q_info.get('auto_quant_active')):
        quant_tech_note = f'⚡ EZ Realtids Auto-Quant FP8 (e4m3fn + FP16-Ackumulering) aktiv för {gpu_name} ({vram_gb} GB VRAM / {tier_short}): Komprimerar automatiskt modellen från {disk_gb} GB på disk till ~{eff_vram_gb} GB i VRAM (-48%) vid laddning utan CPU-offload.'
    elif q_tier in ('FP8_SCALED', 'FP8_STANDARD'):
        quant_tech_note = f'🟢 Native FP8 Safetensors ({eff_vram_gb} GB VRAM): Direkt hårdvaruaccelererad 8-bitars precision anpassad för {gpu_name} ({vram_gb} GB VRAM / {tier_short}).'
    elif q_tier == 'NVFP4_AWQ':
        quant_tech_note = f'🚀 NVFP4 / AWQ 4-Bit Kvantisering ({eff_vram_gb} GB VRAM): Komprimerar tung 32B-arkitektur för {gpu_name} ({vram_gb} GB VRAM) med sekventiell VRAM-evakuering.'
    elif str(asset_type).upper() == 'LORA':
        rank_lbl = f'Rank {net_dim} / Alpha {net_alpha:g}' if net_dim > 0 else 'Dynamisk LoRA-patch'
        quant_tech_note = f'🧩 {rank_lbl} ({eff_sz_mb:.0f} MB): Patchas via PRISM Spectral SVD Denoising & Orthogonal Subspace Projection i 16-bitars ackumulering ovanpå {arch_key}-UNet ({tier_short}) utan detaljförlust.'
    else:
        quant_tech_note = f'💿 {q_info.get("quant_label", "Safetensors")} ({disk_gb} GB -> ~{eff_vram_gb} GB VRAM på {gpu_name}, {tier_short}).'
    author_dedup = list(dict.fromkeys(author_found))
    if net_dim > 0 and f'Rank: {net_dim}' not in author_dedup:
        author_dedup.append(f'Tränad Rank/Alpha: {net_dim}/{net_alpha:g}')
    author_summary_line = (
        f"👤 Author & Fil-metadata: {' · '.join(author_dedup)}"
        if author_dedup
        else f"👤 Arkitektur-profil ({arch_key}): {sampler}/{scheduler} · {steps} steg · CFG {cfg} · Clip Skip {clip_skip}"
    )
    arch_note_str = f"{author_summary_line} | {quant_tech_note}"
    if is_unet_already_distilled or (str(asset_type).upper() in ('CHECKPOINT', 'UNET') and is_turbo):
        arch_note_str += ' | ⚡ Destillerad UNet detekterad: Håll extern Turbo-LoRA <= 0.45 eller None.'
    is_three_stage = bool(arch_key == 'KREA2')
    s1_steps = int(prof.get('steps', 52)) if is_three_stage else int(steps)
    s1_cfg = float(prof.get('cfg', 3.0)) if is_three_stage else float(cfg)
    s1_sampler = str(prof.get('sampler', 'euler')) if is_three_stage else str(sampler)
    s1_sched = str(prof.get('stage1_scheduler', 'beta')) if is_three_stage else str(scheduler)
    s2_steps = int(prof.get('stage2_steps', 14)) if is_three_stage else 0
    s2_cfg = float(prof.get('stage2_cfg', 1.0))
    s2_sampler = str(prof.get('sampler', 'euler'))
    s2_sched = str(prof.get('stage2_scheduler', 'simple'))
    ho_pct = float(prof.get('handoff_percent', 16.0)) if is_three_stage else 100.0
    s3_ho_pct = float(prof.get('stage3_handoff_percent', 90.0)) if is_three_stage else 100.0
    badge_auth_tag = '👤 Author' if author_found else f'⚡ {arch_key}'
    badge = f'{badge_auth_tag}: {sampler}/{scheduler} | {steps} stp | CFG {cfg} | CS {clip_skip}'
    if arch_key == 'KREA2' and str(asset_type).upper() != 'LORA' and (not author_found):
        badge = '⚡ 3-Stegs Krea2: Steg 1 euler/beta (0→16%, CFG 3.0) ➜ Steg 2 Turbo euler/simple (16→90%, CFG 1.0) ➜ Steg 3 Polish (90→100%)'
    elif str(modality).upper() == 'VIDEO':
        badge = f'{badge_auth_tag}: {sampler}/{scheduler} | {steps} stp | CFG {cfg} | Shift {shift_v}/{shift_a}'
    if str(asset_type).upper() == 'LORA':
        w_disp = f'{rec_str:.2f} (Author {author_weight_range})' if author_weight_range and author_weight_range != f'{rec_str:.2f}' else f'{rec_str:.2f}'
        rank_tag = f' [R{net_dim}/A{net_alpha:g}]' if net_dim > 0 else ''
        badge = f'{badge_auth_tag} Styrka {w_disp}{rank_tag} (VIS {vis_str:.1f}/Aud {aud_str:.1f}/CLIP {clip_str:.1f}) | {sampler}/{scheduler} ({steps} stp, CFG {cfg})'
    return {
        'asset_name': os.path.basename(raw_name_only) or str(asset_name or ''),
        'arch_key': arch_key,
        'role': role,
        'sampler': sampler,
        'scheduler': scheduler,
        'steps': steps,
        'cfg': cfg,
        'clip_skip': clip_skip,
        'denoise': denoise,
        'is_three_stage': is_three_stage,
        'handoff_percent': ho_pct,
        'stage3_handoff_percent': s3_ho_pct,
        'stage1_steps': s1_steps,
        'stage1_cfg': s1_cfg,
        'stage1_sampler': s1_sampler,
        'stage1_scheduler': s1_sched,
        'stage2_steps': s2_steps,
        'stage2_cfg': s2_cfg,
        'stage2_sampler': s2_sampler,
        'stage2_scheduler': s2_sched,
        'shift_video': shift_v,
        'shift_audio': shift_a,
        'rec_strength': rec_str,
        'stack_balanced_strength': stack_balanced_str,
        'author_weight_range': author_weight_range or f'{rec_str:.2f}',
        'author_steps_range': author_steps_range or str(steps),
        'author_cfg_range': author_cfg_range or str(cfg),
        'network_dim': net_dim,
        'network_alpha': net_alpha,
        'vis_strength': vis_str,
        'audio_strength': aud_str,
        'clip_strength': clip_str,
        'is_distilled_checkpoint': bool(is_unet_already_distilled or (str(asset_type).upper() in ('CHECKPOINT', 'UNET') and is_turbo)),
        'quant_tier': q_tier,
        'quant_label': str(q_info.get('quant_label', 'Safetensors')),
        'auto_quant_active': bool(q_info.get('auto_quant_active', False)),
        'disk_size_gb': disk_gb,
        'effective_vram_gb': eff_vram_gb,
        'quant_tech_note': quant_tech_note,
        'author_summary_line': author_summary_line,
        'has_author_metadata': len(author_found) > 0,
        'summary_badge': badge,
        'arch_note': arch_note_str,
        'author_detected': author_dedup,
        'trained_tags': list(local_meta.get('trained_tags') or local_meta.get('sidecar_words') or reg_entry.get('trigger_words') or []),
    }


def _probe_system_and_project_tier(tier_selection: str = '') -> dict:
    try:
        from .engine_ez_01_cinematrix_canvas_ingest import resolve_cinematrix_hardware_tier_profile
        tier_prof = resolve_cinematrix_hardware_tier_profile(tier_selection)
    except Exception:
        tier_prof = {'tier_id': 1, 'tier_label': 'Tier 1 (<=16-20 GB Optimal FP8/Q8)', 'detected_vram_gb': 16.0, 'gpu_count': 1}
    gpu_name = 'CPU / Okänd GPU'
    actual_vram_gb = float(tier_prof.get('detected_vram_gb', 16.0) or 16.0)
    free_vram_gb = actual_vram_gb
    gpu_count = int(tier_prof.get('gpu_count', 1) or 1)
    try:
        import torch
        if torch.cuda.is_available():
            gpu_count = max(1, int(torch.cuda.device_count()))
            props = torch.cuda.get_device_properties(0)
            gpu_name = str(getattr(props, 'name', 'NVIDIA CUDA GPU') or 'NVIDIA CUDA GPU')
            actual_vram_gb = round(float(props.total_memory) / (1024.0 ** 3), 1)
            try:
                free_b, _ = torch.cuda.mem_get_info(0)
                free_vram_gb = round(float(free_b) / (1024.0 ** 3), 1)
            except Exception:
                free_vram_gb = actual_vram_gb
    except Exception:
        pass
    ram_gb = 32.0
    try:
        import psutil
        ram_gb = round(float(psutil.virtual_memory().total) / (1024.0 ** 3), 1)
    except Exception:
        try:
            import ctypes

            class _MEMSTAT(ctypes.Structure):
                _fields_ = [
                    ('dwLength', ctypes.c_ulong),
                    ('dwMemoryLoad', ctypes.c_ulong),
                    ('ullTotalPhys', ctypes.c_ulonglong),
                    ('ullAvailPhys', ctypes.c_ulonglong),
                    ('ullTotalPageFile', ctypes.c_ulonglong),
                    ('ullAvailPageFile', ctypes.c_ulonglong),
                    ('ullTotalVirtual', ctypes.c_ulonglong),
                    ('ullAvailVirtual', ctypes.c_ulonglong),
                    ('sullAvailExtendedVirtual', ctypes.c_ulonglong),
                ]

            ms = _MEMSTAT()
            ms.dwLength = ctypes.sizeof(_MEMSTAT)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms)):
                ram_gb = round(float(ms.ullTotalPhys) / (1024.0 ** 3), 1)
        except Exception:
            pass
    tier_id = str(tier_prof.get('tier_id', 'TIER_1_16GB_20GB'))
    tier_label = str(tier_prof.get('tier_label', 'Tier 1 (8 GB–16 GB VRAM: Optimal Q8/FP8 Single-Pass)'))
    if 'TIER_4' in tier_id:
        tier_num, tier_short, tier_min_vram = (4, 'Tier 4 (80 GB+ Supercluster)', 60.0)
    elif 'TIER_3' in tier_id:
        tier_num, tier_short, tier_min_vram = (3, 'Tier 3 (48 GB Workstation)', 40.0)
    elif 'TIER_2' in tier_id:
        tier_num, tier_short, tier_min_vram = (2, 'Tier 2 (24–32 GB Prosumer)', 22.0)
    else:
        tier_num, tier_short, tier_min_vram = (1, 'Tier 1 (<=16–20 GB Optimal Int8 ConvRot / FP8 / Auto-Quant)', 8.0)
    effective_vram_gb = min(actual_vram_gb, max(actual_vram_gb, tier_min_vram)) if tier_num <= 2 else actual_vram_gb
    prefers_quantized = (actual_vram_gb < 28.0) or (tier_num <= 2)
    prefers_bf16_full = (actual_vram_gb >= 38.0) and (tier_num >= 3)
    tier_exceeds_hw = tier_min_vram > (actual_vram_gb + 2.5)
    opt_prec_label = (
        'Int8 ConvRot (Hadamard) · FP8 Scaled · EZ Auto-Quant FP8 + GGUF Q8_0'
        if actual_vram_gb < 22.0 or tier_num == 1
        else ('Int8 ConvRot / FP8 Scaled / BF16 Hybrid + Q8_0/BF16 VLM' if actual_vram_gb < 38.0 or tier_num == 2 else 'Native BF16/FP16 Full Precision')
    )
    return {
        'gpu_name': gpu_name,
        'gpu_count': gpu_count,
        'actual_vram_gb': actual_vram_gb,
        'free_vram_gb': free_vram_gb,
        'system_ram_gb': ram_gb,
        'tier_id': tier_id,
        'tier_num': tier_num,
        'tier_short': tier_short,
        'tier_label': tier_label,
        'tier_selection': str(tier_selection or 'auto_from_devops_tier'),
        'effective_vram_gb': effective_vram_gb,
        'prefers_quantized': prefers_quantized,
        'prefers_bf16_full': prefers_bf16_full,
        'tier_exceeds_hw': tier_exceeds_hw,
        'optimal_precision_label': opt_prec_label,
        'auto_quant_engine_active': True,
    }


def _scan_installed_vlm_resources(sys_tier: dict = None) -> dict:
    st = sys_tier or _probe_system_and_project_tier()
    vram_gb = float(st.get('actual_vram_gb', 16.0) or 16.0)
    tier_num = int(st.get('tier_num', 1) or 1)
    max_opt_repo_gb = 11.5 if (vram_gb < 22.0 or tier_num == 1) else (19.0 if (vram_gb < 38.0 or tier_num == 2) else 42.0)
    installed_vlms = []
    mmproj_Pool = []
    mmproj_full_items = []
    cand_roots = []
    if 'LLM' in folder_paths.folder_names_and_paths:
        for p in folder_paths.get_folder_paths('LLM'):
            if p:
                cand_roots.append(Path(p))
    models_root = Path(getattr(folder_paths, 'models_dir', Path.cwd() / 'models'))
    for sub in ('LLM', 'LLM/Qwen-VL', 'LLM/GGUF'):
        p_sub = models_root / sub
        if p_sub.exists() and p_sub not in cand_roots:
            cand_roots.append(p_sub)
    seen_paths = set()
    for r_dir in cand_roots:
        if not r_dir.exists():
            continue
        for root_str, dirs, files in os.walk(str(r_dir)):
            root_p = Path(root_str)
            f_low_map = {f.lower(): f for f in files}
            if 'config.json' in f_low_map and any((f.endswith('.safetensors') for f in f_low_map)):
                rp_str = str(root_p.resolve())
                if rp_str not in seen_paths:
                    seen_paths.add(rp_str)
                    tot_b = sum(((root_p / f).stat().st_size for f in files if (root_p / f).is_file()))
                    sz_gb = round(tot_b / (1024.0 ** 3), 2)
                    rel_lbl = root_p.name
                    lbl_low = rel_lbl.lower()
                    is_qwen_vl = any((k in lbl_low for k in ('qwen3', 'qwen2.5', 'qwen-vl', 'qwen_vl', 'huihui', 'qwen')))
                    is_opt_sys = bool(is_qwen_vl and (sz_gb <= max(18.0, max_opt_repo_gb)))
                    installed_vlms.append({
                        'name': rel_lbl,
                        'type': 'HF_REPO',
                        'size_gb': sz_gb,
                        'size_mb': round(tot_b / (1024.0 ** 2), 1),
                        'full_path': rp_str,
                        'has_mmproj': True,
                        'mmproj_name': 'Native Vision Tower (Safetensors)',
                        'is_qwen_vl': is_qwen_vl,
                        'optimal_for_system': is_opt_sys,
                    })
            for f in files:
                fl = f.lower()
                fp = root_p / f
                if 'mmproj' in fl and fl.endswith('.gguf'):
                    mmproj_Pool.append(f)
                    try:
                        mm_sz = fp.stat().st_size if fp.exists() else 0
                    except Exception:
                        mm_sz = 0
                    mmproj_full_items.append({
                        'name': f,
                        'full_path': str(fp.resolve()),
                        'size_mb': round(mm_sz / (1024.0 ** 2), 1),
                    })
                    continue
                if fl.endswith('.gguf') and ('qwen' in fl or 'vl' in fl or 'huihui' in fl):
                    rp_str = str(fp.resolve())
                    if rp_str in seen_paths:
                        continue
                    seen_paths.add(rp_str)
                    sz_b = fp.stat().st_size if fp.exists() else 0
                    sz_gb = round(sz_b / (1024.0 ** 3), 2)
                    Sib_mm = [m for m in files if 'mmproj' in m.lower() and m.lower().endswith('.gguf')]
                    is_qwen_vl = any((k in fl for k in ('qwen3', 'qwen2.5', 'qwen-vl', 'qwen_vl', 'huihui', 'qwen')))
                    is_opt_sys = False
                    installed_vlms.append({
                        'name': f,
                        'type': 'GGUF',
                        'size_gb': sz_gb,
                        'size_mb': round(sz_b / (1024.0 ** 2), 1),
                        'full_path': rp_str,
                        'has_mmproj': len(Sib_mm) > 0,
                        'mmproj_name': Sib_mm[0] if Sib_mm else '',
                        'is_qwen_vl': is_qwen_vl,
                        'optimal_for_system': is_opt_sys,
                    })
    for v in installed_vlms:
        if v['type'] == 'GGUF' and (not v['has_mmproj']) and mmproj_Pool:
            v['has_mmproj'] = True
            v['mmproj_name'] = mmproj_Pool[0]
    installed_vlms.sort(
        key=lambda x: (
            not x.get('is_qwen_vl', False),
            x['type'] == 'GGUF',
            not x['has_mmproj'],
            not x['optimal_for_system'],
            not ('huihui' in x['name'].lower() or 'abliterated' in x['name'].lower()),
            not ('4b' in x['name'].lower() or '8b' in x['name'].lower() or 'fp8' in x['name'].lower()),
            x['name'],
        )
    )
    active_vlm = installed_vlms[0] if installed_vlms else None
    missing_vlm_dl = []
    if not active_vlm or not active_vlm.get('is_qwen_vl', False):
        missing_vlm_dl.append({
            'role': 'vlm_qwen',
            'repo_id': 'huihui-ai/Huihui-Qwen3-VL-4B-Instruct-abliterated',
            'filename': '__FULL_HF_REPO__',
            'folder': 'LLM/Qwen-VL',
        })
    elif active_vlm['type'] == 'GGUF' and (not active_vlm['has_mmproj']):
        missing_vlm_dl.append({
            'role': 'mmproj',
            'repo_id': 'mradermacher/Huihui-Qwen3-VL-8B-Instruct-abliterated-GGUF',
            'filename': 'Huihui-Qwen3-VL-8B-Instruct-abliterated.mmproj-f16.gguf',
            'folder': 'LLM/Qwen-VL',
        })
    return {
        'has_vlm': bool(active_vlm and active_vlm.get('is_qwen_vl', True)),
        'has_mmproj': bool(active_vlm and active_vlm.get('has_mmproj')),
        'active_vlm_name': active_vlm['name'] if active_vlm else 'None',
        'active_vlm_type': active_vlm['type'] if active_vlm else 'None',
        'active_vlm_size_gb': active_vlm.get('size_gb', 0.0) if active_vlm else 0.0,
        'active_vlm_optimal': bool(active_vlm and active_vlm.get('optimal_for_system', True) and active_vlm.get('is_qwen_vl', True)),
        'active_mmproj_name': active_vlm.get('mmproj_name', '') if active_vlm else '',
        'optimal_recommended_vlm': 'Huihui-Qwen3-VL-4B / 8B-Instruct-abliterated (Native Safetensors + EZ Q8/SDPA Cache)',
        'optimal_recommended_mmproj': 'Native Vision Tower (Safetensors)',
        'optimal_vlm_why': f'Native Safetensors med SDPA & EZ Q8/FP8-cache eliminerar GGUF block-dequantization och ger snabbast regi- & bildanalys på {vram_gb} GB VRAM.',
        'installed_vlms': installed_vlms,
        'installed_mmprojs': mmproj_full_items,
        'missing_vlm_downloads': missing_vlm_dl,
    }


def resolve_architecture_companions(architecture: str, modality: str='IMAGE', selected_model: str='', selected_loras: list=None, tier_selection: str='', content_rating: str='Uncensored') -> dict:
    _purge_stale_internal_cache_files()
    sys_tier = _probe_system_and_project_tier(tier_selection)
    vram_gb = float(sys_tier.get('actual_vram_gb', 16.0) or 16.0)
    tier_short = str(sys_tier.get('tier_short', 'Tier 1'))
    prefers_quant = bool(sys_tier.get('prefers_quantized', True))
    cr_low = str(content_rating or 'Uncensored').lower()
    prefers_uncensored = not cr_low.startswith('sfw')
    explicit_arch = str(architecture or '').strip()
    if explicit_arch and explicit_arch.lower() not in ('all', 'auto', 'none', ''):
        arch_key = _normalize_arch_key(explicit_arch, modality)
    else:
        hint_str = f"{architecture or ''} {selected_model or ''} {' '.join((str(x) for x in (selected_loras or []) if x and str(x) != 'None'))}"
        arch_key = _normalize_arch_key(hint_str if selected_model and str(selected_model) != 'None' else architecture, modality)
    prof = COMPANION_ARCH_PROFILES.get(arch_key, COMPANION_ARCH_PROFILES['KREA2'])
    mod_upper = str(prof.get('modality', modality) or 'IMAGE').upper()
    opt_prof = extract_author_and_arch_optimal_settings(str(selected_model or ''), mod_upper, arch_key, 'Checkpoint', active_unet_name=str(selected_model or ''))
    opt_bp = dict(prof.get('optimal_blueprint') or {})
    raw_vaes = folder_paths.get_filename_list('vae') if 'vae' in folder_paths.folder_names_and_paths else []
    local_vaes = [v for v in raw_vaes if not _is_internal_ez_cache_file(v)]
    local_clips = []
    for ck in ('text_encoders', 'clip', 'clip_gguf'):
        if ck in folder_paths.folder_names_and_paths:
            for c_rel in folder_paths.get_filename_list(ck):
                if not _is_internal_ez_cache_file(c_rel):
                    local_clips.append(c_rel)
    local_unets_raw = []
    for uk in ('diffusion_models', 'unet', 'checkpoints', 'unet_gguf'):
        if uk in folder_paths.folder_names_and_paths:
            for rel_u in folder_paths.get_filename_list(uk):
                if _is_internal_ez_cache_file(rel_u):
                    continue
                t_role = _classify_asset_true_role(rel_u, '', 'Checkpoint')
                if t_role == 'CLIP':
                    local_clips.append(rel_u)
                    continue
                if t_role in ('VLM', 'MMPROJ', 'VAE', 'AUDIO_VAE', 'LORA'):
                    continue
                b_low = os.path.basename(rel_u).lower()
                is_vid_unet = any((vk in b_low for vk in ('minimax', 'h3', 'fl2va', 'ref2va', 'hailuo', 'wan2', 'wan_', 'ltxv', 'hunyuan_video', 'mochi', 'vid_')))
                is_img_unet = any((ik in b_low for ik in ('krea', 'flux', 'sdxl', 'pony', 'illustrious', 'juggernaut', 'qwen_image', 'qwen-image', 'img_')))
                if mod_upper == 'IMAGE' and is_vid_unet and (not is_img_unet):
                    continue
                if mod_upper == 'VIDEO' and is_img_unet and (not is_vid_unet):
                    continue
                local_unets_raw.append(rel_u)
    local_clips = sorted(set(local_clips))
    local_unets = sorted(set(local_unets_raw))
    local_loras = sorted(set(folder_paths.get_filename_list('loras'))) if 'loras' in folder_paths.folder_names_and_paths else []

    def _collect_matches(candidates: list, tokens: tuple, basename_priority: bool = False, role_filter: str = '') -> list:
        out_m = []
        seen_c = set()

        def _tok_matches(tok_l: str, target_s: str, base_s: str) -> bool:
            if tok_l in ('ae', 'ae.safetensors', 'ae.sft'):
                return base_s in ('ae.safetensors', 'ae.sft')
            return tok_l in target_s

        def _role_allowed(cand_s: str, base_s: str) -> bool:
            c_l = cand_s.lower()
            if role_filter == 'IMAGE_VAE':
                if any((vk in c_l for vk in ('minimax', 'video_vae', 'audio_vae', 'hunyuan_video', 'h3\\', 'h3/'))):
                    return False
            elif role_filter == 'VIDEO_VAE':
                if 'audio_vae' in c_l or base_s in ('ae.safetensors', 'ae.sft', 'qwen_image_vae.safetensors', 'sdxl_vae.safetensors'):
                    return False
            elif role_filter == 'PRIMARY_VIDEO_UNET':
                if 'ref2va' in base_s:
                    return False
            return True

        if basename_priority:
            for tok in tokens:
                t_low = tok.lower()
                for cand in candidates:
                    if _is_internal_ez_cache_file(cand):
                        continue
                    b_low = os.path.basename(cand).lower()
                    if not _role_allowed(cand, b_low):
                        continue
                    if _tok_matches(t_low, b_low, b_low) and cand not in seen_c:
                        seen_c.add(cand)
                        out_m.append(cand)
        for tok in tokens:
            t_low = tok.lower()
            for cand in candidates:
                if _is_internal_ez_cache_file(cand):
                    continue
                c_low = cand.lower()
                b_low = os.path.basename(cand).lower()
                if not _role_allowed(cand, b_low):
                    continue
                if _tok_matches(t_low, c_low, b_low) and cand not in seen_c:
                    seen_c.add(cand)
                    out_m.append(cand)
        return out_m

    def _sort_by_tier_precision(items_list: list, keep_token_order: bool = False, role_hint: str = 'UNET') -> list:
        if len(items_list) <= 1 or keep_token_order:
            return items_list

        def _rank_item(cm: str) -> tuple:
            c_low = cm.lower()
            b_low = os.path.basename(cm).lower()
            is_gguf = 1 if c_low.endswith('.gguf') else 0
            is_ref2va = 1 if (role_hint == 'UNET' and 'ref2va' in b_low) else 0
            if role_hint == 'CLIP' and arch_key == 'MINIMAX':
                is_h3_32b_clip = 0 if any((k in c_low for k in ('32b', 'minimax_h3', 'nvfp4', 'h3\\', 'h3/'))) else 1
                is_oversized_32b = is_h3_32b_clip
            else:
                is_oversized_32b = 1 if (role_hint == 'CLIP' and prefers_quant and ('32b' in c_low or '27b' in c_low)) else 0
            is_rank1_quant = (not is_gguf) and any((q in c_low for q in ('convrot', 'int8', 'nvfp4', 'fp8_scaled', 'e4m3fn_scaled', '_scaled', 'full_fp8', '4b_fp8')))
            is_rank2_quant = (not is_gguf) and ('fp8' in c_low)
            is_bf16_fp16 = (not is_gguf) and any((q in c_low for q in ('bf16', 'fp16')))
            if role_hint == 'UNET':
                is_official_primary = any((p in b_low for p in ('krea-2-raw-int8-convrot', 'krea2_fp8', 'krea-2-raw', 'minimax-h3_singularity', 'minimax_h3_fl2va_int8_convrot', 'minimax_h3_fl2va')))
                c_score = 0 if is_official_primary else 1
            else:
                is_uncens = any((u in c_low for u in ('abliterated', 'uncensored', 'raw', 'singularity', 'nsfw')))
                c_score = (0 if is_uncens else 1) if prefers_uncensored else (0 if not is_uncens else 1)
            if prefers_quant:
                q_score = 0 if is_rank1_quant else (1 if is_rank2_quant else (2 if is_bf16_fp16 else 3))
            else:
                q_score = 0 if is_bf16_fp16 else (1 if is_rank1_quant else 2)
            return (is_gguf, is_ref2va, is_oversized_32b, q_score, c_score)

        return sorted(items_list, key=_rank_item)

    raw_unet_matches = _collect_matches(local_unets, prof.get('unet_match', ()), basename_priority=True, role_filter='PRIMARY_VIDEO_UNET' if mod_upper == 'VIDEO' else '')
    if not raw_unet_matches:
        raw_unet_matches = _collect_matches(local_unets, prof.get('unet_match', ()), basename_priority=True)
    unet_matches = _sort_by_tier_precision(raw_unet_matches, role_hint='UNET')
    turbo_matches = _collect_matches(local_loras, prof.get('turbo_match', ()), basename_priority=True)
    clip_matches = _sort_by_tier_precision(_collect_matches(local_clips, prof.get('clip_match', ())), keep_token_order=False, role_hint='CLIP')
    vae_role_filter = 'IMAGE_VAE' if mod_upper == 'IMAGE' else ('VIDEO_VAE' if mod_upper == 'VIDEO' else '')
    vae_matches = _collect_matches(local_vaes, prof.get('vae_match', ()), basename_priority=True, role_filter=vae_role_filter)
    audio_vae_matches = _collect_matches(local_vaes, prof.get('audio_vae_match', ()), basename_priority=True) if prof.get('audio_vae_match') else []
    matched_unet = unet_matches[0] if unet_matches else ''
    matched_turbo = turbo_matches[0] if turbo_matches else ''
    matched_clip = clip_matches[0] if clip_matches else ''
    matched_vae = vae_matches[0] if vae_matches else ''
    matched_audio_vae = audio_vae_matches[0] if audio_vae_matches else ''
    vlm_info = _scan_installed_vlm_resources(sys_tier)
    suboptimal_notices = []
    if sys_tier.get('tier_exceeds_hw'):
        suboptimal_notices.append(
            f"Projektets valda tier ({tier_short}) överstiger detekterad fysisk GPU-VRAM ({vram_gb} GB på {sys_tier.get('gpu_name')}). Risk för VRAM-spill till System-RAM ({sys_tier.get('system_ram_gb')} GB)."
        )
    if matched_clip and ('t5xxl' in matched_clip.lower() or 'umt5' in matched_clip.lower()):
        if prefers_quant and ('fp16' in matched_clip.lower() or 'bf16' in matched_clip.lower()):
            if not any(('fp8' in cm.lower() or 'q8' in cm.lower() for cm in clip_matches)):
                suboptimal_notices.append(
                    f"Tung FP16/BF16 Text Encoder ({os.path.basename(matched_clip)}) aktiv på {vram_gb} GB VRAM ({tier_short}) — FP8 Scaled rekommenderas för detta system och projekt-tier."
                )
        elif sys_tier.get('prefers_bf16_full') and ('fp8' in matched_clip.lower() or 'q4' in matched_clip.lower()):
            suboptimal_notices.append(
                f"Kvantiserad Text Encoder ({os.path.basename(matched_clip)}) aktiv på {vram_gb} GB VRAM ({tier_short}) — ditt system har kapacitet för full BF16/FP16-precision."
            )
    if vlm_info.get('has_vlm') and (not vlm_info.get('active_vlm_optimal', True)):
        suboptimal_notices.append(
            f"VLM ({vlm_info.get('active_vlm_name')}, {vlm_info.get('active_vlm_size_gb')} GB) är suboptimal för {vram_gb} GB VRAM & {tier_short} ({sys_tier.get('optimal_precision_label')})."
        )
    if arch_key in ('SDXL', 'PONY', 'ILLUSTRIOUS') and matched_unet:
        if not matched_clip:
            matched_clip = matched_unet
        if not matched_vae:
            matched_vae = matched_unet
    missing_downloads = []
    for dl in prof.get('downloads', []):
        role = dl.get('role')
        if role == 'vae' and (not matched_vae):
            missing_downloads.append(dl)
        elif role == 'clip' and (not matched_clip):
            missing_downloads.append(dl)
    slot_checklist = [
        {
            'role': 'unet',
            'label': '🏛️ Huvudmodell (UNet / Diffusion)',
            'optimal_target': opt_bp.get('unet', f'{arch_key} UNet FP8/ConvRot'),
            'optimal_why': opt_bp.get('unet_why', ''),
            'matched_local': matched_unet or '',
            'local_alternatives': unet_matches,
            'total_in_category': len(local_unets),
            'status': 'OPTIMAL' if matched_unet else 'MISSING',
        },
        {
            'role': 'turbo_lora',
            'label': '⚡ Turbo-LoRA (Steg-Acceleration)',
            'optimal_target': opt_bp.get('turbo_lora', f'{arch_key} Turbo LoRA'),
            'optimal_why': opt_bp.get('turbo_why', ''),
            'matched_local': matched_turbo or '',
            'local_alternatives': turbo_matches,
            'total_in_category': len(local_loras),
            'status': 'OPTIMAL' if matched_turbo else 'SUBOPTIMAL',
        },
        {
            'role': 'clip',
            'label': '🔤 Text Encoder (CLIP / VLM)',
            'optimal_target': opt_bp.get('clip', f'{arch_key} CLIP FP8'),
            'optimal_why': opt_bp.get('clip_why', ''),
            'matched_local': matched_clip or '',
            'local_alternatives': clip_matches,
            'total_in_category': len(local_clips),
            'status': 'OPTIMAL' if matched_clip else 'MISSING',
        },
        {
            'role': 'vae',
            'label': '🎨 Visuell VAE (Latent Decoder)',
            'optimal_target': opt_bp.get('vae', f'{arch_key} VAE'),
            'optimal_why': opt_bp.get('vae_why', ''),
            'matched_local': matched_vae or '',
            'local_alternatives': vae_matches,
            'total_in_category': len(local_vaes),
            'status': 'OPTIMAL' if matched_vae else 'MISSING',
        },
    ]
    if prof.get('audio_vae_match'):
        slot_checklist.append({
            'role': 'audio_vae',
            'label': '🔊 Audio-VAE (32kHz Ljudmotor)',
            'optimal_target': opt_bp.get('audio_vae', 'minimax_h3_audio_vae_fp32.safetensors'),
            'optimal_why': opt_bp.get('audio_vae_why', ''),
            'matched_local': matched_audio_vae or '',
            'local_alternatives': audio_vae_matches,
            'total_in_category': len(local_vaes),
            'status': 'OPTIMAL' if matched_audio_vae else 'MISSING',
        })
    eff_sel_model = str(selected_model or '').strip()
    if not eff_sel_model or eff_sel_model == 'None':
        eff_sel_model = matched_unet or ''
    active_loras_clean = [str(x).strip() for x in (selected_loras or []) if x and str(x).strip() not in ('None', '')]
    style_loras_only = [
        x for x in active_loras_clean
        if not _is_true_turbo_acceleration_lora(x)
    ]
    eff_style_cnt = max(1, len(style_loras_only))
    opt_prof = extract_author_and_arch_optimal_settings(
        eff_sel_model or arch_key,
        mod_upper,
        arch_key,
        'Checkpoint',
        active_unet_name=eff_sel_model,
        sys_tier=sys_tier,
        stack_lora_count=eff_style_cnt,
    )
    selected_lora_profiles = []
    for l_idx, l_val in enumerate(selected_loras or []):
        l_str = str(l_val or '').strip()
        if not l_str or l_str == 'None':
            continue
        l_opt = extract_author_and_arch_optimal_settings(
            l_str,
            mod_upper,
            arch_key,
            'LORA',
            active_unet_name=eff_sel_model,
            sys_tier=sys_tier,
            stack_lora_count=eff_style_cnt,
        )
        l_opt['slot_index'] = l_idx + 1
        l_opt['lora_name'] = os.path.basename(l_str)
        l_opt['full_rel_name'] = l_str
        selected_lora_profiles.append(l_opt)
        if l_opt.get('has_author_metadata') and (not opt_prof.get('has_author_metadata')) and (not opt_prof.get('is_three_stage')) and mod_upper == 'IMAGE':
            opt_prof['sampler'] = l_opt['sampler']
            opt_prof['scheduler'] = l_opt['scheduler']
            opt_prof['steps'] = l_opt['steps']
            opt_prof['cfg'] = l_opt['cfg']
            opt_prof['clip_skip'] = l_opt.get('clip_skip', opt_prof.get('clip_skip', 1))
            opt_prof['stage1_steps'] = l_opt['steps']
            opt_prof['stage1_cfg'] = l_opt['cfg']
            opt_prof['stage1_sampler'] = l_opt['sampler']
            opt_prof['stage1_scheduler'] = l_opt['scheduler']
    opt_prof['selected_model_name'] = os.path.basename(eff_sel_model) if eff_sel_model else f'{arch_key} (Standard)'
    opt_prof['selected_lora_profiles'] = selected_lora_profiles
    opt_prof['active_style_lora_count'] = len(style_loras_only)
    if len(style_loras_only) >= 2:
        scale_pct = 88 if len(style_loras_only) == 2 else 78
        opt_prof['stack_harmony_note'] = f'🔬 PRISM Orthogonal Multi-LoRA Stack ({len(style_loras_only)} aktiva LoRAs + Turbo-Shield): Slot 2..3 projiceras ortogonalt mot Slot 1:s singulära huvudvektorer (U_k, V_k) med {scale_pct}% bibehållen Author-styrka utan övermättnad eller detaljförlust.'
    elif len(style_loras_only) == 1 and selected_lora_profiles:
        lp0 = selected_lora_profiles[0]
        opt_prof['stack_harmony_note'] = f"🔬 PRISM Spectral Denoising & Turbo-Shield aktiv ({lp0['lora_name']}): Rekommenderad styrka {lp0['rec_strength']:.2f} (Author-intervall {lp0['author_weight_range']}, VIS {lp0['vis_strength']:.1f} / Aud {lp0['audio_strength']:.1f} / CLIP {lp0['clip_strength']:.1f})."
    else:
        opt_prof['stack_harmony_note'] = f"🏛️ Ren basmodell ({opt_prof['selected_model_name']}): Inga extra stil-LoRAs aktiva."
    has_all_req = bool(matched_clip) and bool(matched_vae) and (bool(matched_audio_vae) if prof.get('audio_vae_match') else True) and bool(vlm_info.get('has_vlm')) and bool(vlm_info.get('has_mmproj'))
    if not has_all_req:
        health_state = 'MISSING'
        health_label = f"Röd (Saknas): Obligatoriska resursfiler saknas lokalt för {arch_key} på {sys_tier.get('gpu_name')} ({vram_gb} GB VRAM / {tier_short})."
    elif suboptimal_notices or not matched_unet:
        health_state = 'SUBOPTIMAL'
        health_label = f"Gul (Suboptimal): Resursfiler finns lokalt men kontrollera huvudmodell/precision mot {sys_tier.get('gpu_name')} ({vram_gb} GB VRAM) & {tier_short}."
    else:
        health_state = 'OPTIMAL'
        health_label = f"Grön (Optimal): Alla obligatoriska resursfiler (UNet, VAE, CLIP, Audio VAE, Qwen3-VL + mmproj) finns lokalt på disken och matchar ditt faktiska system ({sys_tier.get('gpu_name')}, {vram_gb} GB VRAM / {sys_tier.get('system_ram_gb')} GB RAM) och projektets tier ({tier_short})."
    return {
        'status': 'ok',
        'architecture': str(architecture or arch_key),
        'arch_key': arch_key,
        'modality': prof.get('modality', modality),
        'clip_type': 'pony' if 'pony' in (str(architecture) + ' ' + str(eff_sel_model or matched_unet)).lower() else ('illustrious' if any((k in (str(architecture) + ' ' + str(eff_sel_model or matched_unet)).lower() for k in ('illustrious', 'ilxl', 'noobai'))) else prof.get('clip_type', 'krea2')),
        'unet_name': matched_unet or 'None',
        'active_selected_model': eff_sel_model or 'None',
        'turbo_lora_name': matched_turbo or 'None',
        'clip_name': matched_clip or 'None',
        'vae_name': matched_vae or 'None',
        'audio_vae_name': matched_audio_vae or 'None',
        'installed_unets': unet_matches,
        'installed_turbo_loras': turbo_matches,
        'installed_clips': clip_matches,
        'installed_vaes': vae_matches,
        'installed_audio_vaes': audio_vae_matches,
        'all_local_unets_count': len(local_unets),
        'all_local_loras_count': len(local_loras),
        'all_local_clips_count': len(local_clips),
        'all_local_vaes_count': len(local_vaes),
        'has_unet': bool(matched_unet),
        'has_turbo_lora': bool(matched_turbo),
        'has_clip': bool(matched_clip),
        'has_vae': bool(matched_vae),
        'has_audio_vae': bool(matched_audio_vae) if prof.get('audio_vae_match') else True,
        'optimal_blueprint': opt_bp,
        'slot_checklist': slot_checklist,
        'can_auto_download': len(missing_downloads) > 0,
        'missing_companions': missing_downloads,
        'suboptimal_notices': suboptimal_notices,
        'health_state': health_state,
        'health_label': health_label,
        'system_tier': sys_tier,
        'vlm_companions': vlm_info,
        'optimal_settings': opt_prof,
    }


def download_architecture_companions(architecture: str, modality: str='IMAGE', tier_selection: str='') -> dict:
    comp = resolve_architecture_companions(architecture, modality, tier_selection=tier_selection)
    downloaded = []
    errors = []
    for item in comp.get('missing_companions', []):
        url = str(item.get('url', '')).strip()
        fname = str(item.get('filename', '')).strip()
        folder_cat = str(item.get('folder', 'vae')).strip()
        if not url or not fname:
            continue
        target_dirs = folder_paths.get_folder_paths(folder_cat) if folder_cat in folder_paths.folder_names_and_paths else []
        if not target_dirs and folder_cat == 'text_encoders' and ('clip' in folder_paths.folder_names_and_paths):
            target_dirs = folder_paths.get_folder_paths('clip')
        target_dir = Path(target_dirs[0]) if target_dirs else _get_suite_root() / 'MODELS' / folder_cat
        target_dir.mkdir(parents=True, exist_ok=True)
        dest_path = target_dir / fname
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'EZ-Cinematrix-Studio/2.0'})
            written = 0
            with urllib.request.urlopen(req, timeout=300) as resp, open(dest_path, 'wb') as out_f:
                while True:
                    chunk = resp.read(4 * 1024 * 1024)
                    if not chunk:
                        break
                    out_f.write(chunk)
                    written += len(chunk)
            _invalidate_comfyui_folder_cache()
            downloaded.append({'filename': fname, 'folder': folder_cat, 'size_mb': round(written / (1024 * 1024), 2)})
        except Exception as exc:
            if dest_path.exists() and dest_path.stat().st_size < 1024:
                try:
                    dest_path.unlink()
                except Exception:
                    pass
            errors.append(f'{fname}: {exc}')
    updated = resolve_architecture_companions(architecture, modality)
    updated['downloaded'] = downloaded
    updated['errors'] = errors
    return updated

def cache_civitai_media_thumbnail(remote_url: str, item_id: str, force_refresh: bool=False) -> dict:
    url_str = str(remote_url or '').strip()
    if not url_str:
        return {'cached_file': '', 'view_url': '', 'media_type': 'image'}
    purge_civitai_cache(force_clear_all=False)
    cache_dir = get_civitai_cache_dir() / 'thumbs'
    parsed = urllib.parse.urlparse(url_str)
    ext = os.path.splitext(parsed.path)[1].lower()
    if ext not in ('.jpg', '.jpeg', '.png', '.webp', '.mp4', '.webm'):
        ext = '.mp4' if 'video' in url_str.lower() else '.jpg'
    media_type = 'video' if ext in ('.mp4', '.webm') else 'image'
    url_hash = hashlib.sha256(url_str.encode('utf-8')).hexdigest()[:16]
    safe_id = ''.join((c for c in str(item_id or 'item') if c.isalnum() or c in ('_', '-')))[:24]
    fname = f'civ_{safe_id}_{url_hash}{ext}'
    fpath = cache_dir / fname
    now_ts = time.time()
    if not force_refresh and fpath.exists():
        try:
            if now_ts - fpath.stat().st_mtime < CACHE_TTL_SECONDS and fpath.stat().st_size > 64:
                return {'cached_file': fname, 'view_url': f'/ez_cinematrix/civitai/thumb?file={urllib.parse.quote(fname)}', 'media_type': media_type}
        except Exception:
            pass
    try:
        headers = {'User-Agent': 'EZ-Cinematrix-Studio/2.0'}
        api_k = load_civitai_api_key()
        if api_k:
            headers['Authorization'] = f'Bearer {api_k}'
        req = urllib.request.Request(url_str, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw_bytes = resp.read(15 * 1024 * 1024)
            if len(raw_bytes) > 64:
                fpath.write_bytes(raw_bytes)
                return {'cached_file': fname, 'view_url': f'/ez_cinematrix/civitai/thumb?file={urllib.parse.quote(fname)}', 'media_type': media_type}
    except Exception:
        pass
    return {'cached_file': '', 'view_url': url_str, 'media_type': media_type}

def _resolve_sort_label(sort_preset: str) -> str:
    low = str(sort_preset or '').lower()
    if 'rated' in low or 'betyg' in low:
        return 'Highest Rated'
    if 'new' in low or 'senast' in low:
        return 'Newest'
    return 'Most Downloaded'

def _resolve_period_label(period_preset: str) -> str:
    low = str(period_preset or '').lower()
    for p in ('Year', 'Month', 'Week', 'Day'):
        if p.lower() in low:
            return p
    return 'AllTime'

def query_civitai_catalog(modality: str='IMAGE', asset_type: str='LORA', base_arch: str='All', sort_by: str='Most Downloaded', period: str='AllTime', domain_mode: str='civitai.com', query_text: str='', limit: int=12, force_refresh: bool=False) -> dict:
    if force_refresh:
        purge_civitai_cache(force_clear_all=True)
    else:
        purge_civitai_cache(force_clear_all=False)
    lic = verify_civitai_license_status()
    req_dom = str(domain_mode or 'civitai.com').lower()
    domains = ['civitai.com']
    domain_notice = ''
    if 'both' in req_dom:
        if lic['licensed']:
            domains = ['civitai.com', 'civitai.red']
        else:
            domains = ['civitai.com']
            domain_notice = 'Freemium-läge aktivt: Låst till civitai.com (Blue). Licens krävs för civitai.red.'
    elif 'civitai.red' in req_dom:
        if lic['licensed']:
            domains = ['civitai.red']
        else:
            domains = ['civitai.com']
            domain_notice = 'Freemium-läge aktivt: civitai.red nekad, använder civitai.com (Blue).'
    mod_clean = 'VIDEO' if 'video' in str(modality or '').lower() else 'IMAGE'
    sort_clean = _resolve_sort_label(sort_by)
    period_clean = _resolve_period_label(period)
    type_clean = 'Checkpoint' if 'check' in str(asset_type or '').lower() else 'LORA'
    q_clean = str(query_text or '').strip()
    arch_clean = str(base_arch or 'All').strip()
    if '(' in arch_clean:
        arch_clean = arch_clean.split('(', 1)[0].strip()
    if '[' in arch_clean:
        arch_clean = arch_clean.split('[', 1)[0].strip()
    if arch_clean.lower() not in ('all', 'alla', ''):
        if arch_clean.lower() not in q_clean.lower():
            q_clean = f'{arch_clean} {q_clean}'.strip()
    cache_key_raw = json.dumps({'m': mod_clean, 't': type_clean, 'a': arch_clean, 's': sort_clean, 'p': period_clean, 'd': domains, 'q': q_clean, 'l': int(limit), 'ver': 'v28'}, sort_keys=True)
    q_hash = hashlib.sha256(cache_key_raw.encode('utf-8')).hexdigest()[:20]
    q_cache_file = get_civitai_cache_dir() / 'queries' / f'query_v28_{q_hash}.json'
    if not force_refresh and q_cache_file.exists():
        try:
            if time.time() - q_cache_file.stat().st_mtime < CACHE_TTL_SECONDS:
                cached_payload = json.loads(q_cache_file.read_text(encoding='utf-8'))
                if isinstance(cached_payload, dict) and 'items' in cached_payload:
                    cached_payload['from_cache'] = True
                    cached_payload['license'] = lic
                    return cached_payload
        except Exception:
            pass
    api_key = load_civitai_api_key()
    aggregated_items = []
    for dom in domains:
        params = {'limit': str(min(25, max(4, int(limit)))), 'types': type_clean, 'sort': sort_clean, 'period': period_clean, 'nsfw': 'true' if dom == 'civitai.red' and lic['licensed'] else 'false'}
        if q_clean:
            params['query'] = q_clean
        url = f'https://{dom}/api/v1/models?{urllib.parse.urlencode(params)}'
        headers = {'User-Agent': 'EZ-Cinematrix-Studio/2.8', 'Accept': 'application/json'}
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                raw_json = json.loads(resp.read().decode('utf-8', errors='ignore'))
            for item in raw_json.get('items') or []:
                if not isinstance(item, dict):
                    continue
                parsed_item = _parse_civitai_model_item(item, dom=dom, mod_clean=mod_clean, arch_clean=arch_clean, type_clean=type_clean, force_refresh=force_refresh)
                if parsed_item:
                    aggregated_items.append(parsed_item)
        except Exception:
            continue
    result_payload = {'status': 'ok', 'from_cache': False, 'modality': mod_clean, 'sort': sort_clean, 'period': period_clean, 'domains_queried': domains, 'domain_notice': domain_notice, 'license': lic, 'items': aggregated_items}
    if aggregated_items:
        try:
            q_cache_file.write_text(json.dumps(result_payload, indent=2), encoding='utf-8')
        except Exception:
            pass
    return result_payload


def _strip_html_to_clean_text(raw_html: str, max_len: int = 1200) -> str:
    if not raw_html:
        return ''
    import html as _html_mod
    import re as _re_mod
    txt = str(raw_html)
    txt = _re_mod.sub(r'(?i)<\s*br\s*/?\s*>', '\n', txt)
    txt = _re_mod.sub(r'(?i)</\s*(?:p|div|li|h[1-6])\s*>', '\n', txt)
    txt = _re_mod.sub(r'<[^>]+>', ' ', txt)
    txt = _html_mod.unescape(txt)
    lines = [' '.join(ln.split()) for ln in txt.splitlines()]
    clean = '\n'.join([ln for ln in lines if ln]).strip()
    return clean[:max_len]


def _infer_file_quantization_and_format(fname: str, meta_obj: dict) -> tuple:
    meta = meta_obj if isinstance(meta_obj, dict) else {}
    fp_raw = str(meta.get('fp', '') or '').strip().upper()
    sz_raw = str(meta.get('size', '') or '').strip().lower()
    fmt_raw = str(meta.get('format', '') or '').strip()
    fn_low = str(fname or '').lower()
    if not fp_raw:
        for tok in ('fp8_e4m3fn', 'fp8_e5m2', 'fp8', 'bf16', 'fp16', 'fp32', 'q8_0', 'q6_k', 'q5_k_m', 'q5_k_s', 'q4_k_m', 'q4_k_s', 'q4_0', 'iq4_xs', 'nf4', 'int8', 'int4'):
            if tok in fn_low:
                fp_raw = tok.upper()
                break
    if not sz_raw:
        if 'pruned' in fn_low:
            sz_raw = 'pruned'
        elif 'full' in fn_low:
            sz_raw = 'full'
    if not fmt_raw:
        if fn_low.endswith('.gguf'):
            fmt_raw = 'GGUF'
        elif fn_low.endswith(('.safetensors', '.sft')):
            fmt_raw = 'SafeTensor'
        elif fn_low.endswith(('.ckpt', '.pt', '.pth', '.bin')):
            fmt_raw = 'PickleTensor'
        else:
            fmt_raw = 'SafeTensor'
    return (fp_raw or 'Auto', sz_raw or 'standard', fmt_raw or 'SafeTensor')


def _extract_civitai_file_entry(f_obj: dict, fallback_dl_url: str = '', version_id: str = '') -> dict:
    if not isinstance(f_obj, dict):
        return {}
    f_id = str(f_obj.get('id', '') or '')
    f_name = str(f_obj.get('name', '') or 'model.safetensors')
    sz_kb = round(float(f_obj.get('sizeKB', 0.0) or 0.0), 1)
    sz_mb = round(sz_kb / 1024.0, 1)
    sz_gb = round(sz_kb / (1024.0 * 1024.0), 2)
    size_label = f'{sz_gb:.2f} GB' if sz_mb >= 1024.0 else f'{sz_mb:.1f} MB'
    meta = f_obj.get('metadata') if isinstance(f_obj.get('metadata'), dict) else {}
    fp_val, sz_var, fmt_val = _infer_file_quantization_and_format(f_name, meta)
    dl_u = str(f_obj.get('downloadUrl') or fallback_dl_url or '').strip()
    if dl_u and f_id and ('type=' not in dl_u) and ('/api/download/models/' in dl_u):
        f_type = str(f_obj.get('type', '') or '')
        q_parts = []
        if f_type:
            q_parts.append(f"type={urllib.parse.quote(f_type)}")
        if fmt_val:
            q_parts.append(f"format={urllib.parse.quote(fmt_val)}")
        if sz_var in ('pruned', 'full'):
            q_parts.append(f"size={urllib.parse.quote(sz_var)}")
        if fp_val and fp_val.lower() in ('fp8', 'fp16', 'bf16', 'fp32', 'nf4'):
            q_parts.append(f"fp={urllib.parse.quote(fp_val.lower())}")
        if q_parts:
            sep = '&' if '?' in dl_u else '?'
            dl_u = f"{dl_u}{sep}{'&'.join(q_parts)}"
    hashes = f_obj.get('hashes') if isinstance(f_obj.get('hashes'), dict) else {}
    badge_parts = [p for p in (fp_val if fp_val != 'Auto' else '', sz_var if sz_var != 'standard' else '', fmt_val, size_label) if p]
    return {
        'file_id': f_id,
        'version_id': str(version_id or ''),
        'name': f_name,
        'size_kb': sz_kb,
        'size_mb': sz_mb,
        'size_gb': sz_gb,
        'size_label': size_label,
        'fp': fp_val,
        'quantization': fp_val,
        'size_variant': sz_var,
        'format': fmt_val,
        'file_type': str(f_obj.get('type', 'Model') or 'Model'),
        'primary': bool(f_obj.get('primary', False)),
        'download_url': dl_u,
        'sha256': str(hashes.get('SHA256', '') or hashes.get('AutoV2', '') or ''),
        'display_label': f"{f_name} ({' · '.join(badge_parts)})",
    }


def _parse_civitai_model_item(item: dict, dom: str = 'civitai.com', mod_clean: str = 'IMAGE', arch_clean: str = 'All', type_clean: str = 'LORA', force_refresh: bool = False, max_versions: int = 10) -> dict:
    if not isinstance(item, dict):
        return {}
    model_id = str(item.get('id', '') or '')
    model_name = str(item.get('name', 'Unnamed Asset') or 'Unnamed Asset')
    model_type = str(item.get('type', type_clean) or type_clean)
    creator = item.get('creator') if isinstance(item.get('creator'), dict) else (item.get('user') if isinstance(item.get('user'), dict) else {})
    author_name = str(creator.get('username') or creator.get('name') or item.get('author') or 'Unknown Creator').strip()
    author_avatar = str(creator.get('image') or '').strip()
    tags_list = [str(t) for t in (item.get('tags') or []) if t] if isinstance(item.get('tags'), list) else []
    model_desc = _strip_html_to_clean_text(item.get('description', ''), max_len=1400)
    versions_raw = item.get('modelVersions') if isinstance(item.get('modelVersions'), list) else []
    latest_ver = versions_raw[0] if versions_raw and isinstance(versions_raw[0], dict) else {}
    base_m = str(latest_ver.get('baseModel', '') or '')
    item_mod = classify_modality_from_metadata(base_m, model_name, tags_list)
    if not base_m and item_mod != mod_clean and arch_clean.lower() in ('minimax h3', 'krea2', 'wan video', 'ltxv', 'flux.1', 'sdxl'):
        item_mod = mod_clean
    versions_parsed = []
    all_sample_metas = []
    for v_idx, v_obj in enumerate(versions_raw[:max_versions]):
        if not isinstance(v_obj, dict):
            continue
        v_id = str(v_obj.get('id', '') or f'v_{v_idx}')
        v_name = str(v_obj.get('name', f'v{v_idx + 1}.0') or f'v{v_idx + 1}.0')
        v_base = str(v_obj.get('baseModel', base_m) or base_m)
        v_dl_url = str(v_obj.get('downloadUrl', '') or (f'https://{dom}/api/download/models/{v_id}' if v_id.isdigit() else ''))
        v_words = [str(tw) for tw in (v_obj.get('trainedWords') or []) if tw] if isinstance(v_obj.get('trainedWords'), list) else []
        v_desc = _strip_html_to_clean_text(v_obj.get('description', ''), max_len=900)
        v_files_raw = v_obj.get('files') if isinstance(v_obj.get('files'), list) else []
        v_files = []
        for f_raw in v_files_raw:
            fe = _extract_civitai_file_entry(f_raw, fallback_dl_url=v_dl_url, version_id=v_id)
            if fe:
                v_files.append(fe)
        if not v_files:
            fallback_fn = f"{model_name}_{v_name}.safetensors"
            fp_v, sz_v, fmt_v = _infer_file_quantization_and_format(fallback_fn, {})
            v_files.append({
                'file_id': f'{v_id}_0',
                'version_id': v_id,
                'name': fallback_fn,
                'size_kb': 0.0,
                'size_mb': 0.0,
                'size_gb': 0.0,
                'size_label': 'Auto',
                'fp': fp_v,
                'quantization': fp_v,
                'size_variant': sz_v,
                'format': fmt_v,
                'file_type': 'Model',
                'primary': True,
                'download_url': v_dl_url,
                'sha256': '',
                'display_label': f'{fallback_fn} ({fp_v} · {fmt_v})',
            })
        v_samples = []
        v_metas = []
        img_limit = 4 if v_idx == 0 else 2
        for img_obj in (v_obj.get('images') or [])[:img_limit]:
            if not isinstance(img_obj, dict) or not img_obj.get('url'):
                continue
            thumb_info = cache_civitai_media_thumbnail(str(img_obj['url']), f"{model_id}_{v_id}_{img_obj.get('id', '0')}", force_refresh=force_refresh)
            meta_obj = img_obj.get('meta') if isinstance(img_obj.get('meta'), dict) else {}
            if meta_obj:
                v_metas.append(meta_obj)
                if v_idx == 0:
                    all_sample_metas.append(meta_obj)
            m_type_str = str(img_obj.get('type') or thumb_info['media_type'] or 'image').lower()
            v_samples.append({
                'url': thumb_info['view_url'] or str(img_obj['url']),
                'remote_url': str(img_obj['url']),
                'cached_file': thumb_info['cached_file'],
                'cached_thumb': thumb_info['cached_file'],
                'media_type': m_type_str,
                'is_video': m_type_str == 'video',
                'prompt': str(meta_obj.get('prompt', '') or '')[:320],
            })
        v_files.sort(
            key=lambda f: (
                not str(f.get('name', '')).lower().endswith(('.safetensors', '.sft')),
                str(f.get('name', '')).lower().endswith('.gguf'),
                not bool(f.get('primary')),
            )
        )
        v_primary = v_files[0]
        v_opt = extract_author_and_arch_optimal_settings(
            asset_name=f"{v_primary['name']} {model_name} {v_name}",
            modality=item_mod,
            base_arch=v_base or arch_clean,
            asset_type=type_clean,
            author_desc=f'{v_desc} {model_desc}',
            sample_metas=v_metas or all_sample_metas,
            size_mb=float(v_primary.get('size_mb', 0.0) or 0.0),
        )
        v_first_remote = v_samples[0]['remote_url'] if v_samples else ''
        for vf in v_files:
            register_asset_download_metadata(
                vf['name'],
                vf['download_url'],
                type_clean,
                item_mod,
                v_first_remote,
                v_words,
                v_opt,
                author_desc=f'{v_desc} {model_desc}',
                sample_metas=v_metas or all_sample_metas,
                base_model=v_base or arch_clean,
                author_name=author_name,
            )
        versions_parsed.append({
            'version_id': v_id,
            'version_name': v_name,
            'base_model': v_base or ('MiniMax H3' if mod_clean == 'VIDEO' else 'KREA2 / Flux.1'),
            'created_at': str(v_obj.get('createdAt', item.get('updatedAt', '')) or '')[:10],
            'download_url': v_primary['download_url'] or v_dl_url,
            'filename': v_primary['name'],
            'size_kb': v_primary['size_kb'],
            'size_mb': v_primary['size_mb'],
            'size_label': v_primary['size_label'],
            'fp': v_primary['fp'],
            'format': v_primary['format'],
            'trigger_words': v_words,
            'description_text': v_desc,
            'files': v_files,
            'samples': v_samples,
            'optimal_settings': v_opt,
        })
    active_ver = versions_parsed[0] if versions_parsed else {
        'version_id': '',
        'version_name': 'v1.0',
        'base_model': base_m or ('MiniMax H3' if mod_clean == 'VIDEO' else 'KREA2 / Flux.1'),
        'created_at': str(item.get('updatedAt', '') or '')[:10],
        'download_url': '',
        'filename': f'{model_name}.safetensors',
        'size_kb': 0.0,
        'size_mb': 0.0,
        'size_label': 'Auto',
        'fp': 'Auto',
        'format': 'SafeTensor',
        'trigger_words': [],
        'description_text': model_desc,
        'files': [],
        'samples': [],
        'optimal_settings': extract_author_and_arch_optimal_settings(model_name, item_mod, base_m or arch_clean, type_clean, model_desc, []),
    }
    stats = item.get('stats') if isinstance(item.get('stats'), dict) else {}
    return {
        'id': model_id,
        'name': model_name,
        'author': author_name,
        'creator': author_name,
        'author_avatar': author_avatar,
        'domain': dom,
        'source_domain': dom,
        'type': model_type,
        'modality': item_mod,
        'base_model': active_ver['base_model'],
        'downloads': int(stats.get('downloadCount', 0) or 0),
        'rating': round(float(stats.get('rating', stats.get('thumbsUpCount', 0)) or 0.0), 2),
        'thumbs_up': int(stats.get('thumbsUpCount', 0) or 0),
        'favorites': int(stats.get('favoriteCount', stats.get('collectedCount', 0)) or 0),
        'comments': int(stats.get('commentCount', 0) or 0),
        'nsfw': bool(item.get('nsfw', False)),
        'tags': tags_list[:16],
        'description_text': model_desc or active_ver.get('description_text', ''),
        'updated_at': active_ver['created_at'],
        'version_id': active_ver['version_id'],
        'version_name': active_ver['version_name'],
        'version_count': len(versions_raw) or len(versions_parsed),
        'versions': versions_parsed,
        'files': active_ver['files'],
        'file_id': active_ver['files'][0]['file_id'] if active_ver['files'] else '',
        'filename': active_ver['filename'],
        'size_kb': active_ver['size_kb'],
        'size_mb': active_ver['size_mb'],
        'size_label': active_ver['size_label'],
        'fp': active_ver['fp'],
        'format': active_ver['format'],
        'download_url': active_ver['download_url'],
        'trigger_words': active_ver['trigger_words'],
        'trained_words': active_ver['trigger_words'],
        'samples': active_ver['samples'],
        'optimal_settings': active_ver['optimal_settings'],
    }


def fetch_civitai_model_details(model_id: str, domain: str = 'civitai.com', modality: str = 'IMAGE') -> dict:
    clean_id = str(model_id or '').strip()
    if not clean_id or not clean_id.isdigit():
        return {'status': 'error', 'message': 'Ogiltigt Civitai model_id.'}
    lic = verify_civitai_license_status()
    dom = 'civitai.red' if ('red' in str(domain or '').lower() and lic.get('licensed')) else 'civitai.com'
    headers = {'User-Agent': 'EZ-Cinematrix-Studio/2.8', 'Accept': 'application/json'}
    api_k = load_civitai_api_key()
    if api_k:
        headers['Authorization'] = f'Bearer {api_k}'
    for try_dom in ([dom, 'civitai.com'] if dom != 'civitai.com' else ['civitai.com']):
        try:
            req = urllib.request.Request(f'https://{try_dom}/api/v1/models/{clean_id}', headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw_item = json.loads(resp.read().decode('utf-8', errors='ignore'))
            if isinstance(raw_item, dict) and raw_item.get('id'):
                mod_clean = 'VIDEO' if 'video' in str(modality or '').lower() else 'IMAGE'
                type_clean = 'Checkpoint' if 'check' in str(raw_item.get('type', '')).lower() else 'LORA'
                parsed = _parse_civitai_model_item(raw_item, dom=try_dom, mod_clean=mod_clean, arch_clean='All', type_clean=type_clean, force_refresh=False, max_versions=20)
                return {'status': 'ok', 'item': parsed}
        except Exception as exc:
            last_err = str(exc)
    return {'status': 'error', 'message': f'Kunde inte hämta modelldetaljer för #{clean_id}: {locals().get("last_err", "Okänt fel")}'}

def _get_recipes_file() -> Path:
    r_dir = _get_suite_root() / 'EZ_RECIPES'
    r_dir.mkdir(parents=True, exist_ok=True)
    return r_dir / 'civitai_recipes.json'

def load_civitai_recipes() -> list:
    r_file = _get_recipes_file()
    if r_file.exists():
        try:
            arr = json.loads(r_file.read_text(encoding='utf-8'))
            if isinstance(arr, list):
                return arr
        except Exception:
            pass
    return []

def save_civitai_recipe(recipe_data: dict) -> dict:
    if not isinstance(recipe_data, dict):
        return {'status': 'error', 'message': 'Invalid recipe payload'}
    recipes = load_civitai_recipes()
    rec_id = str(recipe_data.get('id') or f'recipe_{int(time.time() * 1000)}')
    thumb_url = str(recipe_data.get('thumbnail_url') or recipe_data.get('thumbnail_file') or '').strip()
    cached_thumb = ''
    if thumb_url.startswith('http'):
        t_res = cache_civitai_media_thumbnail(thumb_url, rec_id, force_refresh=False)
        cached_thumb = t_res.get('view_url', thumb_url)
    else:
        cached_thumb = thumb_url
    mod_val = 'VIDEO' if str(recipe_data.get('modality', 'IMAGE')).upper() == 'VIDEO' else 'IMAGE'
    if mod_val == 'VIDEO':
        base_arch = str(recipe_data.get('base_architecture') or recipe_data.get('video_architecture') or 'MiniMax H3')
        m_name = str(recipe_data.get('model_name') or recipe_data.get('video_unet_fl2va') or 'None')
        l1 = str(recipe_data.get('lora_1') or recipe_data.get('video_lora_1') or 'None')
        l1_s = float(recipe_data.get('lora_1_strength', recipe_data.get('video_lora_1_strength', 0.6)))
        l2 = str(recipe_data.get('lora_2') or recipe_data.get('video_lora_2') or 'None')
        l2_s = float(recipe_data.get('lora_2_strength', recipe_data.get('video_lora_2_strength', 0.5)))
        l3 = str(recipe_data.get('lora_3') or recipe_data.get('video_lora_3') or 'None')
        l3_s = float(recipe_data.get('lora_3_strength', recipe_data.get('video_lora_3_strength', 0.4)))
        l4 = str(recipe_data.get('lora_4') or recipe_data.get('video_lora_4') or 'None')
        l4_s = float(recipe_data.get('lora_4_strength', recipe_data.get('video_lora_4_strength', 0.35)))
        t_lora = str(recipe_data.get('turbo_lora') or recipe_data.get('video_turbo_lora') or 'None')
        t_str = float(recipe_data.get('turbo_strength', recipe_data.get('video_turbo_strength', 1.0)))
    else:
        base_arch = str(recipe_data.get('base_architecture') or recipe_data.get('image_architecture') or 'KREA2')
        m_name = str(recipe_data.get('model_name') or recipe_data.get('image_unet_name') or 'None')
        l1 = str(recipe_data.get('lora_1') or recipe_data.get('image_style_lora_1') or 'None')
        l1_s = float(recipe_data.get('lora_1_strength', recipe_data.get('image_style_strength_1', 0.8)))
        l2 = str(recipe_data.get('lora_2') or recipe_data.get('image_style_lora_2') or 'None')
        l2_s = float(recipe_data.get('lora_2_strength', recipe_data.get('image_style_strength_2', 0.65)))
        l3 = str(recipe_data.get('lora_3') or recipe_data.get('image_style_lora_3') or 'None')
        l3_s = float(recipe_data.get('lora_3_strength', recipe_data.get('image_style_strength_3', 0.45)))
        l4 = str(recipe_data.get('lora_4') or recipe_data.get('image_style_lora_4') or 'None')
        l4_s = float(recipe_data.get('lora_4_strength', recipe_data.get('image_style_strength_4', 0.4)))
        t_lora = str(recipe_data.get('turbo_lora') or recipe_data.get('image_turbo_lora') or 'None')
        t_str = float(recipe_data.get('turbo_strength', recipe_data.get('image_turbo_strength', 0.9)))
    entry = {'id': rec_id, 'name': str(recipe_data.get('name') or 'Namnlöst Recept').strip(), 'modality': mod_val, 'base_architecture': base_arch, 'model_name': m_name, 'lora_1': l1, 'lora_1_strength': l1_s, 'lora_2': l2, 'lora_2_strength': l2_s, 'lora_3': l3, 'lora_3_strength': l3_s, 'lora_4': l4, 'lora_4_strength': l4_s, 'turbo_lora': t_lora, 'turbo_strength': t_str, 'image_architecture': str(recipe_data.get('image_architecture') or (base_arch if mod_val == 'IMAGE' else 'KREA2')), 'image_unet_name': str(recipe_data.get('image_unet_name') or (m_name if mod_val == 'IMAGE' else 'None')), 'image_style_lora_1': str(recipe_data.get('image_style_lora_1') or (l1 if mod_val == 'IMAGE' else 'None')), 'image_style_strength_1': float(recipe_data.get('image_style_strength_1', l1_s if mod_val == 'IMAGE' else 0.8)), 'image_style_lora_2': str(recipe_data.get('image_style_lora_2') or (l2 if mod_val == 'IMAGE' else 'None')), 'image_style_strength_2': float(recipe_data.get('image_style_strength_2', l2_s if mod_val == 'IMAGE' else 0.65)), 'image_style_lora_3': str(recipe_data.get('image_style_lora_3') or (l3 if mod_val == 'IMAGE' else 'None')), 'image_style_strength_3': float(recipe_data.get('image_style_strength_3', l3_s if mod_val == 'IMAGE' else 0.45)), 'image_style_lora_4': str(recipe_data.get('image_style_lora_4') or (l4 if mod_val == 'IMAGE' else 'None')), 'image_style_strength_4': float(recipe_data.get('image_style_strength_4', l4_s if mod_val == 'IMAGE' else 0.4)), 'image_turbo_lora': str(recipe_data.get('image_turbo_lora') or (t_lora if mod_val == 'IMAGE' else 'None')), 'image_turbo_strength': float(recipe_data.get('image_turbo_strength', t_str if mod_val == 'IMAGE' else 0.9)), 'video_architecture': str(recipe_data.get('video_architecture') or (base_arch if mod_val == 'VIDEO' else 'MiniMax H3')), 'video_unet_fl2va': str(recipe_data.get('video_unet_fl2va') or (m_name if mod_val == 'VIDEO' else 'None')), 'video_lora_1': str(recipe_data.get('video_lora_1') or (l1 if mod_val == 'VIDEO' else 'None')), 'video_lora_1_strength': float(recipe_data.get('video_lora_1_strength', l1_s if mod_val == 'VIDEO' else 0.6)), 'video_lora_2': str(recipe_data.get('video_lora_2') or (l2 if mod_val == 'VIDEO' else 'None')), 'video_lora_2_strength': float(recipe_data.get('video_lora_2_strength', l2_s if mod_val == 'VIDEO' else 0.5)), 'video_lora_3': str(recipe_data.get('video_lora_3') or (l3 if mod_val == 'VIDEO' else 'None')), 'video_lora_3_strength': float(recipe_data.get('video_lora_3_strength', l3_s if mod_val == 'VIDEO' else 0.4)), 'video_lora_4': str(recipe_data.get('video_lora_4') or (l4 if mod_val == 'VIDEO' else 'None')), 'video_lora_4_strength': float(recipe_data.get('video_lora_4_strength', l4_s if mod_val == 'VIDEO' else 0.35)), 'video_turbo_lora': str(recipe_data.get('video_turbo_lora') or (t_lora if mod_val == 'VIDEO' else 'None')), 'video_turbo_strength': float(recipe_data.get('video_turbo_strength', t_str if mod_val == 'VIDEO' else 1.0)), 'trigger_words': str(recipe_data.get('trigger_words', '')), 'thumbnail_url': cached_thumb, 'media_type': str(recipe_data.get('media_type', 'image')), 'created_at': time.strftime('%Y-%m-%d %H:%M:%S')}
    recipes = [r for r in recipes if isinstance(r, dict) and str(r.get('id')) != rec_id and (str(r.get('name')) != entry['name'])]
    recipes.insert(0, entry)
    _get_recipes_file().write_text(json.dumps(recipes, indent=2), encoding='utf-8')
    return {'status': 'ok', 'recipe': entry, 'recipes': recipes}

def delete_civitai_recipe(recipe_id: str) -> dict:
    target = str(recipe_id or '').strip()
    recipes = [r for r in load_civitai_recipes() if isinstance(r, dict) and str(r.get('id')) != target]
    _get_recipes_file().write_text(json.dumps(recipes, indent=2), encoding='utf-8')
    return {'status': 'ok', 'recipes': recipes}

def _find_sidecar_preview(full_path: str) -> tuple:
    if not full_path or not os.path.isfile(full_path):
        return ('', False)
    base_no_ext = os.path.splitext(full_path)[0]
    for ext in ('.preview.png', '.preview.jpg', '.preview.webp', '.preview.mp4', '.png', '.jpg', '.jpeg', '.webp', '.mp4'):
        cand = base_no_ext + ext
        if os.path.isfile(cand):
            is_vid = cand.lower().endswith(('.mp4', '.webm'))
            return (cand, is_vid)
    return ('', False)

def _normalize_duplicate_stem(rel_name: str) -> str:
    base = os.path.splitext(os.path.basename(str(rel_name or '')))[0].lower()
    base = re.sub(r'^(?:img_|vid_)+', '', base)
    base = re.sub(r'\s*\(\d+\)$', '', base)
    base = re.sub(r'(?:_copy|_dup|-\d+)$', '', base)
    base = re.sub(r'[-_]?(?:fp8_e4m3fn_scaled|fp8_e4m3fn|fp8_scaled|fp8|bf16|fp16|q8_0|q6_k|q5_k_m|q4_k_m)\b', '', base)
    return re.sub(r'[-_\s]+', '_', base).strip('_')


def _compute_fast_asset_fingerprint(full_path: str, size_bytes: int) -> str:
    if not full_path or size_bytes <= 0 or (not os.path.isfile(full_path)):
        return ''
    try:
        h = hashlib.blake2b(digest_size=12)
        h.update(str(size_bytes).encode('utf-8'))
        chunk_sz = 131072
        with open(full_path, 'rb') as f:
            h.update(f.read(chunk_sz))
            if size_bytes > chunk_sz * 2:
                f.seek(size_bytes // 2)
                h.update(f.read(chunk_sz))
            if size_bytes > chunk_sz * 3:
                f.seek(max(0, size_bytes - chunk_sz))
                h.update(f.read(chunk_sz))
        return h.hexdigest()
    except Exception:
        return ''


def _evaluate_file_tier_optimality(rel_name: str, asset_type: str, size_mb: float, prefers_quant: bool, vram_gb: float, tier_short: str, full_path: str = '', content_rating: str = 'Uncensored') -> dict:
    nm_l = str(rel_name or '').lower()
    at_u = str(asset_type or '').upper()
    q_prof = _inspect_safetensors_quant_and_arch_profile(full_path, rel_name, at_u, size_mb)
    q_label = str(q_prof.get('quant_label', 'Auto'))
    q_tier = str(q_prof.get('quant_tier', 'BF16_NATIVE'))
    eff_vram_gb = float(q_prof.get('effective_vram_gb', round(size_mb / 1024.0, 2)))
    disk_gb = float(q_prof.get('disk_size_gb', round(size_mb / 1024.0, 2)))
    is_uncens = bool(q_prof.get('is_uncensored_raw', False))
    is_distilled = bool(q_prof.get('is_distilled_checkpoint', False))
    clip_dim = int(q_prof.get('clip_proj_dim', 0) or 0)
    cr_low = str(content_rating or 'Uncensored').lower()
    content_tag = ' · 🔓 Raw/Uncensored' if is_uncens else ''
    base_meta = {
        'quant_tier': q_tier,
        'quant_label': q_label,
        'quant_rank': int(q_prof.get('quant_rank', 2)),
        'auto_quant_active': bool(q_prof.get('auto_quant_active', False)),
        'effective_vram_mb': float(q_prof.get('effective_vram_mb', size_mb)),
        'effective_vram_gb': eff_vram_gb,
        'disk_size_gb': disk_gb,
        'is_uncensored_raw': is_uncens,
        'is_distilled_checkpoint': is_distilled,
        'clip_proj_dim': clip_dim,
    }
    if at_u == 'VLM':
        is_qwen = any((k in nm_l for k in ('qwen3', 'qwen2.5', 'qwen-vl', 'qwen_vl', 'huihui')))
        if not is_qwen:
            return {
                **base_meta,
                'is_optimal_for_tier': False,
                'optimal_tier_level': 'SUBOPTIMAL',
                'optimal_tier_badge': '⚠️ EJ QWEN-VL (T.ex. Florence-2)',
                'optimal_tier_reason': 'Stöder ej EZ [02] Qwen3-VL multimodal tidslinje/manuskompilering.',
            }
        is_q_or_8b = any((k in nm_l for k in ('q8_0', 'q6_k', 'fp8', '8b', '4b'))) or bool(q_prof.get('auto_quant_active'))
        if prefers_quant and is_q_or_8b:
            v_badge = (
                f'⚡ OPTIMAL QWEN-VL (Auto-NF4 · ~{eff_vram_gb} GB VRAM{content_tag})'
                if q_prof.get('auto_quant_active')
                else f'🏆 OPTIMAL QWEN-VL ({q_label} · ~{eff_vram_gb} GB VRAM{content_tag})'
            )
            return {
                **base_meta,
                'is_optimal_for_tier': True,
                'optimal_tier_level': 'OPTIMAL',
                'optimal_tier_badge': v_badge,
                'optimal_tier_reason': f'Optimal Qwen3-VL för nod [02] på {vram_gb} GB VRAM ({q_label}, effektivt VRAM ~{eff_vram_gb} GB).',
            }
        return {
            **base_meta,
            'is_optimal_for_tier': True,
            'optimal_tier_level': 'COMPATIBLE',
            'optimal_tier_badge': f'🟢 KOMPATIBEL QWEN-VL ({q_label} · ~{eff_vram_gb} GB VRAM)',
            'optimal_tier_reason': 'Kompatibel med nod [02] Qwen-VL.',
        }
    if at_u == 'MMPROJ':
        return {
            **base_meta,
            'is_optimal_for_tier': True,
            'optimal_tier_level': 'OPTIMAL',
            'optimal_tier_badge': '🏆 OPTIMAL VISION MMPROJ (FP16)',
            'optimal_tier_reason': 'Obligatorisk bilduppfattningsmodul för GGUF Qwen3-VL.',
        }
    if at_u == 'AUDIO_VAE':
        is_fp32 = 'fp32' in nm_l or 'audio_vae' in nm_l or q_tier == 'FP32_FULL'
        return {
            **base_meta,
            'is_optimal_for_tier': is_fp32,
            'optimal_tier_level': 'OPTIMAL' if is_fp32 else 'COMPATIBLE',
            'optimal_tier_badge': '🏆 OPTIMAL AUDIO-VAE (FP32 Clean)' if is_fp32 else '🟢 KOMPATIBEL AUDIO-VAE',
            'optimal_tier_reason': 'FP32 Audio-VAE motverkar metalliskt fasbrus i 24/32 kHz MiniMax-ljud.',
        }
    if at_u == 'VAE':
        is_opt_vae = any((k in nm_l for k in ('int8_convrot', 'qwen_image_vae', 'wan_2.1_vae', 'ae.safetensors'))) or q_tier == 'INT8_CONVROT'
        return {
            **base_meta,
            'is_optimal_for_tier': is_opt_vae,
            'optimal_tier_level': 'OPTIMAL' if is_opt_vae else 'COMPATIBLE',
            'optimal_tier_badge': f'🏆 OPTIMAL VAE ({q_label})' if is_opt_vae else f'🟢 KOMPATIBEL VAE ({q_label})',
            'optimal_tier_reason': 'Matchar Krea 2 / MiniMax H3 (Int8 ConvRot Hadamard) / Wan 2.1 utan luma-klippning.' if is_opt_vae else 'Sekundär eller äldre VAE-fil.',
        }
    if at_u == 'CLIP':
        is_fp8_q8 = q_tier in ('INT8_CONVROT', 'FP8_SCALED', 'FP8_STANDARD', 'GGUF_Q8_0')
        dim_tag = f' · {clip_dim}-dim' if clip_dim > 0 else ''
        if clip_dim == 2560:
            return {
                **base_meta,
                'is_optimal_for_tier': False,
                'optimal_tier_level': 'COMPATIBLE',
                'optimal_tier_badge': f'🟡 QWEN-IMAGE 2560-DIM CLIP ({q_label})',
                'optimal_tier_reason': '2560-dim enkel-projektion (endast för Qwen-Image). Ej kompatibel med MiniMax H3 (kräver 5120-dim Krea2/Qwen3-VL CLIP).',
            }
        is_opt_clip = is_fp8_q8 if prefers_quant else True
        return {
            **base_meta,
            'is_optimal_for_tier': is_opt_clip,
            'optimal_tier_level': 'OPTIMAL' if is_opt_clip else 'COMPATIBLE',
            'optimal_tier_badge': f'🏆 OPTIMAL CLIP ({q_label}{dim_tag}{content_tag})' if is_opt_clip else f'⚡ AUTO-CAST CLIP ({q_label}{dim_tag})',
            'optimal_tier_reason': f'{q_label}{dim_tag} Text Encoder lämnar max VRAM-utrymme åt UNet på {vram_gb} GB VRAM (kompatibel med både Krea 2 [03] & MiniMax H3 [05]).',
        }
    if at_u in ('CHECKPOINT', 'UNET'):
        dist_tag = ' · ⚡ Distilled' if is_distilled else ''
        if q_tier in ('INT8_CONVROT', 'FP8_SCALED'):
            return {
                **base_meta,
                'is_optimal_for_tier': True,
                'optimal_tier_level': 'OPTIMAL',
                'optimal_tier_badge': f'🏆 OPTIMAL RANG 1 ({q_label} · ~{eff_vram_gb} GB VRAM{content_tag}{dist_tag})',
                'optimal_tier_reason': f'Högsta visuella precision på {vram_gb} GB VRAM ({q_label} bevarar 99% BF16-dynamik utan kontrastblödning, effektivt VRAM ~{eff_vram_gb} GB).',
            }
        if q_tier == 'AUTO_QUANT_FP8':
            return {
                **base_meta,
                'is_optimal_for_tier': True,
                'optimal_tier_level': 'OPTIMAL',
                'optimal_tier_badge': f'⚡ OPTIMAL AUTO-QUANT (Disk {disk_gb} GB ➜ ~{eff_vram_gb} GB VRAM i FP8{content_tag}{dist_tag})',
                'optimal_tier_reason': f'BF16/FP16-modell ({disk_gb} GB på disk) som automatiskt kvantiseras i realtid till FP8 (~{eff_vram_gb} GB VRAM med FP16-ackumulering) av EZ [03]/[05]-motorn!',
            }
        if q_tier in ('FP8_STANDARD', 'GGUF_Q8_0'):
            return {
                **base_meta,
                'is_optimal_for_tier': True,
                'optimal_tier_level': 'OPTIMAL',
                'optimal_tier_badge': f'🏆 OPTIMAL UNET ({q_label} · ~{eff_vram_gb} GB VRAM{content_tag}{dist_tag})',
                'optimal_tier_reason': f'{q_label} ryms direkt i {vram_gb} GB VRAM (~{eff_vram_gb} GB) utan CPU-offload.',
            }
        if q_tier == 'GGUF_SUB8':
            return {
                **base_meta,
                'is_optimal_for_tier': vram_gb <= 12.0,
                'optimal_tier_level': 'OPTIMAL' if vram_gb <= 12.0 else 'COMPATIBLE',
                'optimal_tier_badge': f'🟢 LÅG-VRAM GGUF ({q_label} · ~{eff_vram_gb} GB VRAM)',
                'optimal_tier_reason': f'Lägre bitdjup ({q_label}) sparar VRAM men Int8 ConvRot / FP8 Scaled ger skarpare detaljer på {vram_gb} GB VRAM.',
            }
        return {
            **base_meta,
            'is_optimal_for_tier': True,
            'optimal_tier_level': 'OPTIMAL',
            'optimal_tier_badge': f'🏆 OPTIMAL MODELL ({q_label} · ~{eff_vram_gb} GB VRAM{content_tag})',
            'optimal_tier_reason': f'Redo att laddas i {tier_short} (~{eff_vram_gb} GB effektivt VRAM).',
        }
    is_turbo = _is_true_turbo_acceleration_lora(rel_name)
    return {
        **base_meta,
        'is_optimal_for_tier': True,
        'optimal_tier_level': 'OPTIMAL' if is_turbo else 'COMPATIBLE',
        'optimal_tier_badge': f'⚡ OPTIMAL TURBO-LORA{content_tag}' if is_turbo else f'🟢 KOMPATIBEL STIL/KARAKTÄRS-LORA{content_tag}',
        'optimal_tier_reason': 'Snabbdistillerad 4-8 stegs LoRA (anpassas automatiskt mot vald UNet).' if is_turbo else 'Redo för LoRA-slot 1-3 med modalitetsseparerad styrka.',
    }


def scan_local_comfyui_assets(tier_selection: str = '', content_rating: str = 'Uncensored') -> dict:
    _purge_stale_internal_cache_files()
    sys_tier = _probe_system_and_project_tier(tier_selection)
    prefers_quant = bool(sys_tier.get('prefers_quantized', True))
    vram_gb = float(sys_tier.get('actual_vram_gb', 16.0) or 16.0)
    tier_short = str(sys_tier.get('tier_short', 'Tier 1'))
    loras_out = []
    models_out = []
    resources_out = []
    seen_loras = set()
    seen_models = set()
    seen_res = set()
    reg = load_asset_url_registry()
    if 'loras' in folder_paths.folder_names_and_paths:
        for rel_name in sorted(folder_paths.get_filename_list('loras')):
            try:
                if not rel_name or rel_name in seen_loras:
                    continue
                if _is_internal_ez_cache_file(rel_name):
                    continue
                seen_loras.add(rel_name)
                full_p = folder_paths.get_full_path('loras', rel_name)
                sz_bytes = os.path.getsize(full_p) if full_p and os.path.isfile(full_p) else 0
                size_mb = round(sz_bytes / (1024 * 1024), 1)
                true_role_in_loras = _classify_asset_true_role(rel_name, full_p or '', 'LORA')
                reg_entry = reg.get(os.path.basename(rel_name)) or {}
                mod = inspect_safetensors_modality(full_p, rel_name) if full_p else 'UNKNOWN'
                if mod == 'UNKNOWN':
                    mod = classify_modality_from_metadata(str(reg_entry.get('base_model', '') or ''), rel_name)
                (sidecar_p, is_vid) = _find_sidecar_preview(full_p)
                prev_url = f'/ez_cinematrix/civitai/local_preview?cat=loras&name={urllib.parse.quote(rel_name)}' if sidecar_p else ''
                if true_role_in_loras == 'UNET' and size_mb > 1800.0:
                    opt_info = extract_author_and_arch_optimal_settings(
                        rel_name,
                        mod,
                        str(reg_entry.get('base_model', '') or ''),
                        'Checkpoint',
                        author_desc=str(reg_entry.get('author_desc', '') or ''),
                        sample_metas=reg_entry.get('sample_metas') or [],
                        active_unet_name=rel_name,
                        file_path=full_p or '',
                        size_mb=size_mb,
                        sys_tier=sys_tier,
                    )
                    tier_eval = _evaluate_file_tier_optimality(rel_name, 'CHECKPOINT', size_mb, prefers_quant, vram_gb, tier_short, full_p or '', content_rating)
                    models_out.append({
                        'name': rel_name,
                        'short_name': os.path.splitext(os.path.basename(rel_name))[0],
                        'subfolder': os.path.dirname(rel_name).replace('\\', '/'),
                        'category': 'loras',
                        'modality': mod,
                        'asset_type': 'Checkpoint',
                        'resource_role': 'UNET',
                        'size_mb': size_mb,
                        '_size_bytes': sz_bytes,
                        '_full_p': full_p or '',
                        'preview_url': prev_url,
                        'is_video': is_vid,
                        'optimal_settings': opt_info,
                        **tier_eval,
                    })
                    continue
                is_turbo = _is_true_turbo_acceleration_lora(rel_name)
                opt_info = extract_author_and_arch_optimal_settings(
                    rel_name,
                    mod,
                    str(reg_entry.get('base_model', '') or ''),
                    'LORA',
                    author_desc=str(reg_entry.get('author_desc', '') or ''),
                    sample_metas=reg_entry.get('sample_metas') or [],
                    file_path=full_p or '',
                    size_mb=size_mb,
                    sys_tier=sys_tier,
                )
                tier_eval = _evaluate_file_tier_optimality(rel_name, 'LORA', size_mb, prefers_quant, vram_gb, tier_short, full_p or '', content_rating)
                loras_out.append({
                    'name': rel_name,
                    'short_name': os.path.splitext(os.path.basename(rel_name))[0],
                    'subfolder': os.path.dirname(rel_name).replace('\\', '/'),
                    'category': 'loras',
                    'modality': mod,
                    'asset_type': 'LORA',
                    'resource_role': 'TURBO_LORA' if is_turbo else 'STYLE_LORA',
                    'is_turbo': is_turbo,
                    'size_mb': size_mb,
                    '_size_bytes': sz_bytes,
                    '_full_p': full_p or '',
                    'preview_url': prev_url,
                    'is_video': is_vid,
                    'optimal_settings': opt_info,
                    **tier_eval,
                })
            except Exception:
                continue
    for cat in ('diffusion_models', 'unet', 'checkpoints', 'unet_gguf'):
        if cat not in folder_paths.folder_names_and_paths:
            continue
        try:
            f_list = sorted(folder_paths.get_filename_list(cat))
        except Exception:
            f_list = []
        for rel_name in f_list:
            try:
                if not rel_name or f'{cat}:{rel_name}' in seen_models:
                    continue
                if _is_internal_ez_cache_file(rel_name):
                    continue
                seen_models.add(f'{cat}:{rel_name}')
                full_p = folder_paths.get_full_path(cat, rel_name)
                sz_bytes = os.path.getsize(full_p) if full_p and os.path.isfile(full_p) else 0
                size_mb = round(sz_bytes / (1024 * 1024), 1)
                true_role = _classify_asset_true_role(rel_name, full_p or '', 'Checkpoint')
                if true_role in ('VLM', 'MMPROJ', 'CLIP', 'VAE', 'AUDIO_VAE'):
                    b_key = os.path.basename(rel_name).lower()
                    res_dedup_k = f'{true_role.lower()}:{b_key}'
                    if res_dedup_k in seen_res:
                        continue
                    seen_res.add(res_dedup_k)
                    r_mod = 'VLM' if true_role in ('VLM', 'MMPROJ') else ('VIDEO' if (true_role == 'AUDIO_VAE' or bool(_VIDEO_TOKEN_REGEX.search(b_key)) or 'umt5' in b_key) else 'IMAGE')
                    t_node = '[02] Qwen3-VL Compiler' if true_role in ('VLM', 'MMPROJ') else ('[03] Image & [05] Video Rig' if true_role == 'CLIP' else ('[05] Video Rig' if r_mod == 'VIDEO' else '[03] Image Rig'))
                    tier_eval = _evaluate_file_tier_optimality(rel_name, true_role, size_mb, prefers_quant, vram_gb, tier_short, full_p or '', content_rating)
                    resources_out.append({
                        'name': rel_name,
                        'short_name': os.path.splitext(os.path.basename(rel_name))[0],
                        'subfolder': cat,
                        'category': cat,
                        'modality': r_mod,
                        'asset_type': 'Resource',
                        'resource_role': true_role,
                        'target_node': t_node,
                        'size_mb': size_mb,
                        '_size_bytes': sz_bytes,
                        '_full_p': full_p or '',
                        'preview_url': '',
                        'is_video': False,
                        **tier_eval,
                    })
                    continue
                reg_entry = reg.get(os.path.basename(rel_name)) or {}
                mod = inspect_safetensors_modality(full_p, rel_name) if full_p else 'UNKNOWN'
                if mod == 'UNKNOWN':
                    mod = classify_modality_from_metadata(str(reg_entry.get('base_model', '') or ''), rel_name)
                (sidecar_p, is_vid) = _find_sidecar_preview(full_p)
                prev_url = f'/ez_cinematrix/civitai/local_preview?cat={cat}&name={urllib.parse.quote(rel_name)}' if sidecar_p else ''
                if true_role == 'LORA':
                    is_turbo = _is_true_turbo_acceleration_lora(rel_name)
                    opt_info = extract_author_and_arch_optimal_settings(
                        rel_name,
                        mod,
                        str(reg_entry.get('base_model', '') or ''),
                        'LORA',
                        author_desc=str(reg_entry.get('author_desc', '') or ''),
                        sample_metas=reg_entry.get('sample_metas') or [],
                        file_path=full_p or '',
                        size_mb=size_mb,
                        sys_tier=sys_tier,
                    )
                    tier_eval = _evaluate_file_tier_optimality(rel_name, 'LORA', size_mb, prefers_quant, vram_gb, tier_short, full_p or '', content_rating)
                    loras_out.append({
                        'name': rel_name,
                        'short_name': os.path.splitext(os.path.basename(rel_name))[0],
                        'subfolder': cat,
                        'category': cat,
                        'modality': mod,
                        'asset_type': 'LORA',
                        'resource_role': 'TURBO_LORA' if is_turbo else 'STYLE_LORA',
                        'is_turbo': is_turbo,
                        'size_mb': size_mb,
                        '_size_bytes': sz_bytes,
                        '_full_p': full_p or '',
                        'preview_url': prev_url,
                        'is_video': is_vid,
                        'optimal_settings': opt_info,
                        **tier_eval,
                    })
                    continue
                opt_info = extract_author_and_arch_optimal_settings(
                    rel_name,
                    mod,
                    str(reg_entry.get('base_model', '') or ''),
                    'Checkpoint',
                    author_desc=str(reg_entry.get('author_desc', '') or ''),
                    sample_metas=reg_entry.get('sample_metas') or [],
                    active_unet_name=rel_name,
                    file_path=full_p or '',
                    size_mb=size_mb,
                    sys_tier=sys_tier,
                )
                tier_eval = _evaluate_file_tier_optimality(rel_name, 'CHECKPOINT', size_mb, prefers_quant, vram_gb, tier_short, full_p or '', content_rating)
                models_out.append({
                    'name': rel_name,
                    'short_name': os.path.splitext(os.path.basename(rel_name))[0],
                    'subfolder': cat,
                    'category': cat,
                    'modality': mod,
                    'asset_type': 'Checkpoint',
                    'resource_role': 'UNET',
                    'size_mb': size_mb,
                    '_size_bytes': sz_bytes,
                    '_full_p': full_p or '',
                    'preview_url': prev_url,
                    'is_video': is_vid,
                    'optimal_settings': opt_info,
                    **tier_eval,
                })
            except Exception:
                continue

    if 'vae' in folder_paths.folder_names_and_paths:
        try:
            vae_list = sorted(folder_paths.get_filename_list('vae'))
        except Exception:
            vae_list = []
        for rel_name in vae_list:
            try:
                if not rel_name or f'vae:{rel_name}' in seen_res:
                    continue
                if _is_internal_ez_cache_file(rel_name):
                    continue
                seen_res.add(f'vae:{rel_name}')
                full_p = folder_paths.get_full_path('vae', rel_name)
                sz_bytes = os.path.getsize(full_p) if full_p and os.path.isfile(full_p) else 0
                size_mb = round(sz_bytes / (1024 * 1024), 1)
                nm_l = rel_name.lower()
                is_aud = 'audio' in nm_l
                is_vid_vae = any((k in nm_l for k in ('minimax', 'h3', 'video', 'wan', 'ltx', 'hunyuan', 'convrot')))
                r_role = 'AUDIO_VAE' if is_aud else 'VAE'
                r_mod = 'VIDEO' if is_vid_vae else 'IMAGE'
                tier_eval = _evaluate_file_tier_optimality(rel_name, r_role, size_mb, prefers_quant, vram_gb, tier_short, full_p or '', content_rating)
                resources_out.append({
                    'name': rel_name,
                    'short_name': os.path.splitext(os.path.basename(rel_name))[0],
                    'subfolder': 'vae',
                    'category': 'vae',
                    'modality': r_mod,
                    'asset_type': 'Resource',
                    'resource_role': r_role,
                    'target_node': '[05] Video Rig' if is_vid_vae else '[03] Image Rig',
                    'size_mb': size_mb,
                    '_size_bytes': sz_bytes,
                    '_full_p': full_p or '',
                    'preview_url': '',
                    'is_video': False,
                    **tier_eval,
                })
            except Exception:
                continue

    for c_cat in ('text_encoders', 'clip', 'clip_gguf'):
        if c_cat not in folder_paths.folder_names_and_paths:
            continue
        try:
            clip_list = sorted(folder_paths.get_filename_list(c_cat))
        except Exception:
            clip_list = []
        for rel_name in clip_list:
            try:
                b_key = os.path.basename(rel_name).lower()
                if not rel_name or f'clip:{b_key}' in seen_res:
                    continue
                seen_res.add(f'clip:{b_key}')
                full_p = folder_paths.get_full_path(c_cat, rel_name)
                sz_bytes = os.path.getsize(full_p) if full_p and os.path.isfile(full_p) else 0
                size_mb = round(sz_bytes / (1024 * 1024), 1)
                nm_l = rel_name.lower()
                is_vid_clip = any((k in nm_l for k in ('umt5', 'abliterated', 'minimax', 'wan', 'ltx')))
                tier_eval = _evaluate_file_tier_optimality(rel_name, 'CLIP', size_mb, prefers_quant, vram_gb, tier_short, full_p or '', content_rating)
                resources_out.append({
                    'name': rel_name,
                    'short_name': os.path.splitext(os.path.basename(rel_name))[0],
                    'subfolder': c_cat,
                    'category': c_cat,
                    'modality': 'VIDEO' if is_vid_clip else 'IMAGE',
                    'asset_type': 'Resource',
                    'resource_role': 'CLIP',
                    'target_node': '[03] Image & [05] Video Rig',
                    'size_mb': size_mb,
                    '_size_bytes': sz_bytes,
                    '_full_p': full_p or '',
                    'preview_url': '',
                    'is_video': False,
                    **tier_eval,
                })
            except Exception:
                continue

    try:
        vlm_info = _scan_installed_vlm_resources(sys_tier)
        for v_it in vlm_info.get('installed_vlms', []):
            v_nm = str(v_it.get('name', ''))
            if not v_nm or f'vlm:{v_nm.lower()}' in seen_res:
                continue
            seen_res.add(f'vlm:{v_nm.lower()}')
            sz_mb = round(float(v_it.get('size_gb', 0.0) or 0.0) * 1024.0, 1)
            v_fp = str(v_it.get('full_path', ''))
            tier_eval = _evaluate_file_tier_optimality(v_nm, 'VLM', sz_mb, prefers_quant, vram_gb, tier_short, v_fp, content_rating)
            resources_out.append({
                'name': v_nm,
                'short_name': os.path.splitext(os.path.basename(v_nm))[0],
                'subfolder': 'LLM',
                'category': 'LLM',
                'modality': 'VLM',
                'asset_type': 'Resource',
                'resource_role': 'VLM',
                'target_node': '[02] Qwen3-VL Compiler',
                'size_mb': sz_mb,
                '_size_bytes': int(sz_mb * 1024 * 1024) if v_it.get('type') == 'GGUF' else 0,
                '_full_p': v_fp,
                'preview_url': '',
                'is_video': False,
                'vision_ready': bool(v_it.get('has_mmproj', True)),
                'mmproj_match': str(v_it.get('mmproj_name', '')),
                **tier_eval,
            })
        for mp_it in vlm_info.get('installed_mmprojs', []):
            mp_nm = str(mp_it.get('name', '')) if isinstance(mp_it, dict) else str(mp_it or '')
            mp_sz = float(mp_it.get('size_mb', 850.0) or 850.0) if isinstance(mp_it, dict) else 850.0
            mp_fp = str(mp_it.get('full_path', '')) if isinstance(mp_it, dict) else ''
            if not mp_nm or f'mmproj:{mp_nm.lower()}' in seen_res:
                continue
            seen_res.add(f'mmproj:{mp_nm.lower()}')
            tier_eval = _evaluate_file_tier_optimality(mp_nm, 'MMPROJ', mp_sz, prefers_quant, vram_gb, tier_short, mp_fp, content_rating)
            resources_out.append({
                'name': mp_nm,
                'short_name': os.path.splitext(os.path.basename(mp_nm))[0],
                'subfolder': 'LLM',
                'category': 'LLM',
                'modality': 'VLM',
                'asset_type': 'Resource',
                'resource_role': 'MMPROJ',
                'target_node': '[02] Qwen3-VL Vision Projector',
                'size_mb': mp_sz,
                '_size_bytes': int(mp_sz * 1024 * 1024),
                '_full_p': mp_fp,
                'preview_url': '',
                'is_video': False,
                **tier_eval,
            })
    except Exception:
        pass

    all_items = loras_out + models_out + resources_out
    by_size = {}
    for it in all_items:
        sb = int(it.get('_size_bytes', 0))
        if sb > 4096:
            by_size.setdefault((it.get('resource_role', it['asset_type']), sb), []).append(it)
    hash_groups = {}
    for (r_role, sb), grp in by_size.items():
        if len(grp) >= 2:
            for it in grp:
                fp_hash = _compute_fast_asset_fingerprint(it.get('_full_p', ''), sb)
                if fp_hash:
                    hash_groups.setdefault((r_role, fp_hash), []).append(it)
    stem_groups = {}
    for it in all_items:
        st = _normalize_duplicate_stem(it['name'])
        if len(st) >= 4:
            stem_groups.setdefault((it.get('resource_role', it['asset_type']), st), []).append(it)
    dup_groups_count = 0
    dup_files_count = 0
    reclaimable_mb = 0.0
    assigned = set()

    def _score_keep_preference(item_obj: dict) -> tuple:
        nm_l = item_obj['name'].lower()
        has_copy_suffix = bool(re.search(r'(?:\(\d+\)|_copy|_dup)', nm_l))
        is_safetensors = nm_l.endswith(('.safetensors', '.sft'))
        is_opt_tier = bool(item_obj.get('is_optimal_for_tier', False))
        if prefers_quant:
            is_opt_prec = is_safetensors and any((q in nm_l for q in ('convrot', 'int8', 'fp8', 'scaled')))
        else:
            is_opt_prec = is_safetensors and (any((q in nm_l for q in ('bf16', 'fp16'))) or (not any((q in nm_l for q in ('fp8', 'q4', 'q5')))))
        has_prev = bool(item_obj.get('preview_url'))
        return (not has_copy_suffix, is_safetensors, is_opt_tier, is_opt_prec, has_prev, -len(nm_l))

    for (atype, fp_h), grp in hash_groups.items():
        if len(grp) < 2:
            continue
        dup_groups_count += 1
        grp_sorted = sorted(grp, key=_score_keep_preference, reverse=True)
        gid = f'BIN_{fp_h[:8]}'
        for idx, it in enumerate(grp_sorted):
            assigned.add(id(it))
            it['is_duplicate'] = True
            it['dup_type'] = 'EXACT_BINARY'
            it['dup_badge'] = '🧬 EXAKT DUBBLETT (100% Identisk)'
            it['dup_group_id'] = gid
            it['keep_recommended'] = (idx == 0)
            it['keep_reason'] = f'Optimal för {vram_gb} GB VRAM ({tier_short})' if idx == 0 else 'Identisk dubblett — kan raderas säkert'
            it['dup_peers'] = [p['name'] for p in grp_sorted if p is not it]
            if idx > 0:
                dup_files_count += 1
                reclaimable_mb += float(it.get('size_mb', 0.0))

    for (atype, st), grp in stem_groups.items():
        unassigned = [it for it in grp if id(it) not in assigned]
        if len(grp) < 2 or not unassigned:
            continue
        real_paths = {it.get('_full_p') for it in grp if it.get('_full_p')}
        if len(real_paths) < 2:
            continue
        dup_groups_count += 1
        grp_sorted = sorted(grp, key=_score_keep_preference, reverse=True)
        gid = f'VAR_{st[:16]}'
        for idx, it in enumerate(grp_sorted):
            if id(it) in assigned:
                continue
            assigned.add(id(it))
            it['is_duplicate'] = True
            it['dup_type'] = 'VARIANT'
            it['dup_badge'] = '⚖️ NAMN- / PRECISIONSDUBBLETT'
            it['dup_group_id'] = gid
            it['keep_recommended'] = (idx == 0)
            it['keep_reason'] = f'Optimal precision för {vram_gb} GB VRAM ({tier_short})' if idx == 0 else f'Sekundär variant för {tier_short}'
            it['dup_peers'] = [p['name'] for p in grp_sorted if p is not it]
            if idx > 0:
                dup_files_count += 1
                reclaimable_mb += float(it.get('size_mb', 0.0))

    for it in all_items:
        it.pop('_size_bytes', None)
        it.pop('_full_p', None)
        if 'is_duplicate' not in it:
            it['is_duplicate'] = False
            it['dup_type'] = ''
            it['dup_badge'] = ''
            it['dup_group_id'] = ''
            it['keep_recommended'] = True
            it['keep_reason'] = ''
            it['dup_peers'] = []
    return {
        'status': 'ok',
        'loras': loras_out,
        'models': models_out,
        'resources': resources_out,
        'system_tier': sys_tier,
        'duplicate_summary': {
            'total_groups': dup_groups_count,
            'total_duplicate_files': dup_files_count,
            'reclaimable_mb': round(reclaimable_mb, 1),
            'reclaimable_gb': round(reclaimable_mb / 1024.0, 2),
        },
    }


def delete_local_comfyui_asset(category: str, rel_name: str) -> dict:
    import gc
    cat = str(category or '').strip()
    rname = str(rel_name or '').strip()
    allowed_cats = ('loras', 'diffusion_models', 'unet', 'checkpoints', 'unet_gguf', 'vae', 'text_encoders', 'clip', 'clip_gguf', 'LLM')
    if cat not in allowed_cats or not rname or '..' in rname.replace('\\', '/').split('/'):
        return {'status': 'error', 'message': f'Ogiltig kategori eller filnamn ({cat} / {rname}).'}
    if cat not in folder_paths.folder_names_and_paths:
        return {'status': 'error', 'message': f'Mappkategorin {cat} saknas i ComfyUI.'}
    full_p = folder_paths.get_full_path(cat, rname)
    if not full_p or not os.path.isfile(full_p):
        return {'status': 'error', 'message': f'Filen "{rname}" hittades inte på disken.'}
    target_path = Path(full_p).resolve()
    allowed_roots = [Path(p).resolve() for p in folder_paths.get_folder_paths(cat) if p and os.path.isdir(p)]
    if not any((str(target_path).startswith(str(r)) for r in allowed_roots)):
        return {'status': 'error', 'message': 'Säkerhetsspärr: Filen ligger utanför tillåtna ComfyUI-modellmappar.'}
    used_in_recipes = [r.get('name') for r in load_civitai_recipes() if isinstance(r, dict) and rname in json.dumps(r)]
    freed_bytes = 0
    removed_files = []
    try:
        try:
            import comfy.model_management
            comfy.model_management.soft_empty_cache()
        except Exception:
            pass
        gc.collect()
        fsize = target_path.stat().st_size
        target_path.unlink()
        freed_bytes += fsize
        removed_files.append(target_path.name)
        base_no_ext = os.path.splitext(str(target_path))[0]
        for s_ext in ('.preview.png', '.preview.jpg', '.preview.webp', '.preview.mp4', '.png', '.jpg', '.jpeg', '.webp', '.mp4', '.civitai.info'):
            sp = Path(base_no_ext + s_ext)
            if sp.is_file():
                try:
                    freed_bytes += sp.stat().st_size
                    sp.unlink()
                    removed_files.append(sp.name)
                except Exception:
                    pass
        reg = load_asset_url_registry()
        bkey = os.path.basename(rname)
        if bkey in reg:
            reg.pop(bkey, None)
            try:
                _get_asset_url_registry_path().write_text(json.dumps(reg, indent=2), encoding='utf-8')
            except Exception:
                pass
        _invalidate_comfyui_folder_cache()
        updated_cat = scan_local_comfyui_assets()
        return {
            'status': 'ok',
            'deleted': rname,
            'category': cat,
            'removed_files': removed_files,
            'freed_mb': round(freed_bytes / (1024.0 * 1024.0), 2),
            'used_in_recipes': used_in_recipes,
            'catalog': updated_cat,
        }
    except Exception as exc:
        return {'status': 'error', 'message': f'Kunde inte radera {rname}: {exc}'}

import threading

_ACTIVE_CIVITAI_DOWNLOADS: dict = {}
_CANCELLED_CIVITAI_DOWNLOADS: set = set()
_CIVITAI_DL_LOCK = threading.Lock()


class _CivitaiNoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Captures 301/302/303/307/308 redirects so we can manually strip Authorization headers before hitting R2/S3."""

    def http_error_301(self, req, fp, code, msg, headers):
        return fp

    def http_error_302(self, req, fp, code, msg, headers):
        return fp

    def http_error_303(self, req, fp, code, msg, headers):
        return fp

    def http_error_307(self, req, fp, code, msg, headers):
        return fp

    def http_error_308(self, req, fp, code, msg, headers):
        return fp


def _open_civitai_download_stream(initial_url: str, api_key: str, user_agent: str, timeout: int = 300):
    cur_url = str(initial_url or '').strip()
    no_redir_opener = urllib.request.build_opener(_CivitaiNoRedirectHandler())
    for _hop in range(8):
        parsed = urllib.parse.urlparse(cur_url)
        host = parsed.netloc.lower()
        is_civitai_host = ('civitai.com' in host) or ('civitai.red' in host)
        req_url = cur_url
        req_headers = {'User-Agent': user_agent, 'Accept': '*/*'}
        if is_civitai_host and api_key:
            req_headers['Authorization'] = f'Bearer {api_key}'
            if '/api/download/' in req_url and 'token=' not in req_url:
                sep = '&' if '?' in req_url else '?'
                req_url = f'{req_url}{sep}token={urllib.parse.quote(api_key)}'
        req = urllib.request.Request(req_url, headers=req_headers)
        resp = no_redir_opener.open(req, timeout=timeout)
        code = int(getattr(resp, 'status', getattr(resp, 'code', 200)) or 200)
        if code in (301, 302, 303, 307, 308):
            loc = resp.headers.get('Location') or resp.headers.get('location')
            try:
                resp.close()
            except Exception:
                pass
            if not loc:
                break
            cur_url = urllib.parse.urljoin(req_url, str(loc).strip())
            continue
        return resp
    raise RuntimeError('För många omdirigeringar (redirects) från Civitai CDN.')


def _resolve_missing_civitai_download_url(model_id: str = '', filename: str = '', version_id: str = '', file_id: str = '') -> tuple:
    clean_id = str(model_id or '').strip()
    clean_ver = str(version_id or '').strip()
    clean_fid = str(file_id or '').strip()
    base_f = os.path.basename(str(filename or '')).strip()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) EZ-Cinematrix/2.8', 'Accept': 'application/json'}
    api_k = load_civitai_api_key()
    if api_k:
        headers['Authorization'] = f'Bearer {api_k}'
    if clean_ver and clean_ver.isdigit():
        try:
            req = urllib.request.Request(f'https://civitai.com/api/v1/model-versions/{clean_ver}', headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                v_data = json.loads(resp.read().decode('utf-8', errors='ignore'))
            files = v_data.get('files') or []
            picked = None
            if clean_fid:
                picked = next((f for f in files if isinstance(f, dict) and str(f.get('id', '')) == clean_fid), None)
            if not picked and base_f:
                picked = next((f for f in files if isinstance(f, dict) and str(f.get('name', '')).lower() == base_f.lower()), None)
            if not picked:
                picked = next((f for f in files if isinstance(f, dict) and f.get('primary')), files[0] if files else {})
            if isinstance(picked, dict):
                fe = _extract_civitai_file_entry(picked, fallback_dl_url=str(v_data.get('downloadUrl', '') or ''), version_id=clean_ver)
                if fe.get('download_url'):
                    return (fe['download_url'], float(fe.get('size_kb', 0.0) or 0.0))
        except Exception:
            pass
    if clean_id and clean_id.isdigit():
        try:
            req = urllib.request.Request(f'https://civitai.com/api/v1/models/{clean_id}', headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8', errors='ignore'))
            versions = data.get('modelVersions') or []
            ver = None
            if clean_ver:
                ver = next((v for v in versions if isinstance(v, dict) and str(v.get('id', '')) == clean_ver), None)
            if not ver and versions and isinstance(versions[0], dict):
                ver = versions[0]
            if isinstance(ver, dict):
                files = ver.get('files') or []
                picked = None
                if clean_fid:
                    picked = next((f for f in files if isinstance(f, dict) and str(f.get('id', '')) == clean_fid), None)
                if not picked and base_f:
                    picked = next((f for f in files if isinstance(f, dict) and str(f.get('name', '')).lower() == base_f.lower()), None)
                if not picked:
                    picked = next((f for f in files if isinstance(f, dict) and f.get('primary')), files[0] if files else {})
                fe = _extract_civitai_file_entry(picked, fallback_dl_url=str(ver.get('downloadUrl', '') or ''), version_id=str(ver.get('id', '') or ''))
                if fe.get('download_url'):
                    return (fe['download_url'], float(fe.get('size_kb', 0.0) or 0.0))
        except Exception:
            pass
    reg = load_asset_url_registry()
    if base_f in reg and reg[base_f].get('download_url'):
        return (str(reg[base_f]['download_url']), float(reg[base_f].get('size_kb', 0.0) or 0.0))
    return ('', 0.0)


def _verify_downloaded_safetensors_valid(fpath: Path) -> tuple:
    try:
        fsize = fpath.stat().st_size
        if fsize < 64:
            return (False, 'Filen är för liten (< 64 bytes).')
        with open(fpath, 'rb') as fh:
            head8 = fh.read(8)
            if head8.startswith((b'<!DOC', b'<html', b'<?xml', b'{"err')):
                return (False, 'Servern returnerade en inloggnings-/felsida istället för modellfilen. Kontrollera att giltig Civitai API-nyckel är sparad i EZ [10].')
            if fpath.name.lower().endswith(('.safetensors', '.sft')):
                h_len = struct.unpack('<Q', head8)[0]
                if h_len <= 0 or h_len > 100_000_000 or (8 + h_len > fsize):
                    return (False, 'Ogiltig safetensors-header (avbruten ström).')
                h_obj = json.loads(fh.read(h_len).decode('utf-8'))
                max_end = 0
                if isinstance(h_obj, dict):
                    for (tk, tv) in h_obj.items():
                        if tk != '__metadata__' and isinstance(tv, dict):
                            offs = tv.get('data_offsets')
                            if isinstance(offs, (list, tuple)) and len(offs) >= 2:
                                if int(offs[1]) > max_end:
                                    max_end = int(offs[1])
                if fsize < (8 + h_len + max_end):
                    return (False, f'Ofullständig safetensors-fil ({round(fsize / 1048576, 1)} MB av {round((8 + h_len + max_end) / 1048576, 1)} MB).')
        return (True, 'OK')
    except Exception as exc:
        return (False, f'Valideringsfel: {exc}')


def get_civitai_downloads_status() -> dict:
    with _CIVITAI_DL_LOCK:
        items = [dict(v) for v in _ACTIVE_CIVITAI_DOWNLOADS.values()]
    items.sort(key=lambda x: float(x.get('started_at', 0.0)), reverse=True)
    active_cnt = sum((1 for x in items if x.get('status') == 'downloading'))
    comp_cnt = sum((1 for x in items if x.get('status') == 'completed'))
    fail_cnt = sum((1 for x in items if x.get('status') in ('failed', 'error')))
    tot_dl_b = sum((int(x.get('downloaded_bytes', 0)) for x in items))
    tot_sz_b = sum((max(int(x.get('downloaded_bytes', 0)), int(x.get('total_bytes', 0))) for x in items))
    tot_spd = sum((float(x.get('speed_mbps', 0.0)) for x in items if x.get('status') == 'downloading'))
    rem_b = max(0, sum((max(0, int(x.get('total_bytes', 0)) - int(x.get('downloaded_bytes', 0))) for x in items if x.get('status') == 'downloading')))
    tot_eta = int(round((rem_b / (1024.0 * 1024.0)) / tot_spd)) if tot_spd > 0.05 and rem_b > 0 else 0
    overall_pct = round((tot_dl_b / tot_sz_b) * 100.0, 1) if tot_sz_b > 0 else (100.0 if comp_cnt > 0 and active_cnt == 0 else 0.0)
    dl_mb = round(tot_dl_b / (1024.0 * 1024.0), 2)
    sz_mb = round(tot_sz_b / (1024.0 * 1024.0), 2)
    return {
        'status': 'ok',
        'downloads': items,
        'files': items,
        'summary': {
            'active_count': active_cnt,
            'completed_count': comp_cnt,
            'failed_count': fail_cnt,
            'total_count': len(items),
            'total_files': len(items),
            'total_downloaded_mb': dl_mb,
            'downloaded_mb': dl_mb,
            'total_size_mb': sz_mb,
            'total_mb': sz_mb,
            'overall_percent': overall_pct,
            'total_speed_mbps': round(tot_spd, 2),
            'total_eta_sec': tot_eta,
        },
    }


def clear_completed_civitai_downloads() -> dict:
    with _CIVITAI_DL_LOCK:
        to_del = [k for (k, v) in _ACTIVE_CIVITAI_DOWNLOADS.items() if v.get('status') in ('completed', 'failed', 'error', 'cancelled')]
        for k in to_del:
            _ACTIVE_CIVITAI_DOWNLOADS.pop(k, None)
            _CANCELLED_CIVITAI_DOWNLOADS.discard(k)
    return get_civitai_downloads_status()


def _purge_partial_download_artifacts(entry: dict) -> list:
    removed = []
    if not isinstance(entry, dict):
        return removed
    for pk in ('part_path', 'dest_path'):
        p_str = str(entry.get(pk, '') or '').strip()
        if p_str:
            p_obj = Path(p_str)
            for cand in (p_obj, Path(f'{p_str}.part')):
                if cand.is_file() and (cand.name.endswith('.part') or entry.get('status') in ('downloading', 'cancelled')):
                    try:
                        cand.unlink()
                        removed.append(cand.name)
                    except Exception:
                        pass
    repo_dir_str = str(entry.get('repo_dest_dir', '') or '').strip()
    if repo_dir_str:
        r_dir = Path(repo_dir_str)
        if r_dir.is_dir():
            for pf in list(r_dir.rglob('*.part')):
                try:
                    pf.unlink()
                    removed.append(pf.name)
                except Exception:
                    pass
            if entry.get('status') in ('downloading', 'cancelled'):
                try:
                    shutil.rmtree(str(r_dir), ignore_errors=True)
                    removed.append(r_dir.name)
                except Exception:
                    pass
    return removed


def cancel_civitai_download(dl_id: str = '', filename: str = '', cancel_all: bool = False) -> dict:
    target_id = str(dl_id or '').strip()
    target_fn = str(filename or '').strip().lower()
    cancelled_ids = []
    removed_files = []
    with _CIVITAI_DL_LOCK:
        for (k, v) in list(_ACTIVE_CIVITAI_DOWNLOADS.items()):
            fn_low = str(v.get('filename', '') or '').lower()
            match_item = cancel_all or (target_id and (k == target_id or v.get('id') == target_id or v.get('dl_id') == target_id)) or (target_fn and fn_low == target_fn)
            if not match_item:
                continue
            _CANCELLED_CIVITAI_DOWNLOADS.add(k)
            cancelled_ids.append(k)
            removed_files.extend(_purge_partial_download_artifacts(v))
            v.update({
                'status': 'cancelled',
                'speed_mbps': 0.0,
                'eta_sec': 0,
                'error': '🛑 Avbruten av användaren — halvfärdig .part-fil raderad från disk.',
            })
    _invalidate_comfyui_folder_cache()
    st_out = get_civitai_downloads_status()
    st_out['cancelled_ids'] = cancelled_ids
    st_out['removed_partial_files'] = removed_files
    return st_out


def _invalidate_comfyui_folder_cache() -> None:
    try:
        if hasattr(folder_paths, 'filename_list_cache') and isinstance(folder_paths.filename_list_cache, dict):
            folder_paths.filename_list_cache.clear()
    except Exception:
        pass


def download_civitai_asset_to_comfyui(download_url: str, filename: str, asset_type: str = 'LORA', modality: str = 'IMAGE', sample_url: str = '', model_id: str = '', expected_size_kb: float = 0.0, version_id: str = '', file_id: str = '', async_bg: bool = False) -> dict:
    url_clean = str(download_url or '').strip()
    if not url_clean.startswith('http') or (version_id and file_id and 'type=' not in url_clean):
        (resolved_u, resolved_kb) = _resolve_missing_civitai_download_url(model_id=model_id, filename=filename, version_id=version_id, file_id=file_id)
        if resolved_u:
            url_clean = resolved_u
            if expected_size_kb <= 0 and resolved_kb > 0:
                expected_size_kb = resolved_kb
    if not url_clean.startswith('http'):
        return {'status': 'error', 'message': 'Ogiltig eller saknad nedladdnings-URL från Civitai.'}
    safe_fname = ''.join((c for c in os.path.basename(str(filename or 'civitai_asset.safetensors')) if c.isalnum() or c in ('_', '-', '.')))
    if not safe_fname.lower().endswith(('.safetensors', '.ckpt', '.pt', '.bin', '.gguf')):
        safe_fname += '.safetensors'
    is_lora = str(asset_type or 'LORA').upper() == 'LORA'
    detected_role = 'LORA' if is_lora else _classify_asset_true_role(safe_fname, '', asset_type)
    if detected_role in ('VLM', 'MMPROJ'):
        target_cat = 'LLM'
        target_dir = _resolve_hf_target_base_dir('LLM/Qwen-VL')
    elif detected_role == 'CLIP':
        target_cat = 'text_encoders'
        target_dirs = folder_paths.get_folder_paths('text_encoders') if 'text_encoders' in folder_paths.folder_names_and_paths else (folder_paths.get_folder_paths('clip') if 'clip' in folder_paths.folder_names_and_paths else [])
        target_dir = Path(target_dirs[0]) if target_dirs else _get_suite_root() / 'MODELS' / 'text_encoders'
    elif detected_role in ('VAE', 'AUDIO_VAE'):
        target_cat = 'vae'
        target_dirs = folder_paths.get_folder_paths('vae') if 'vae' in folder_paths.folder_names_and_paths else []
        target_dir = Path(target_dirs[0]) if target_dirs else _get_suite_root() / 'MODELS' / 'vae'
    else:
        mod_prefix = 'VID_' if str(modality or '').upper() == 'VIDEO' else 'IMG_'
        if inspect_safetensors_modality(safe_fname) == 'UNKNOWN' and (not safe_fname.upper().startswith(('VID_', 'IMG_'))):
            safe_fname = f'{mod_prefix}{safe_fname}'
        target_cat = 'loras' if is_lora else 'diffusion_models'
        target_dirs = folder_paths.get_folder_paths(target_cat) if target_cat in folder_paths.folder_names_and_paths else []
        if not target_dirs and (not is_lora) and ('checkpoints' in folder_paths.folder_names_and_paths):
            target_dirs = folder_paths.get_folder_paths('checkpoints')
        target_dir = Path(target_dirs[0]) if target_dirs else _get_suite_root() / 'MODELS' / target_cat
    target_dir.mkdir(parents=True, exist_ok=True)
    dest_path = target_dir / safe_fname
    part_path = target_dir / f'{safe_fname}.part'
    register_asset_download_metadata(safe_fname, url_clean, asset_type, modality, sample_url)
    dl_id = f'dl_{safe_fname}'
    est_bytes = int(float(expected_size_kb or 0.0) * 1024)
    start_ts = time.time()
    with _CIVITAI_DL_LOCK:
        if dl_id in _ACTIVE_CIVITAI_DOWNLOADS and _ACTIVE_CIVITAI_DOWNLOADS[dl_id].get('status') == 'downloading':
            return {'status': 'downloading', 'dl_id': dl_id, 'filename': safe_fname, 'asset_type': 'LORA' if is_lora else 'Checkpoint', 'resource_role': detected_role, 'target_folder': target_cat, 'modality': str(modality or 'IMAGE').upper(), 'message': 'Nedladdning pågår redan.'}
        _CANCELLED_CIVITAI_DOWNLOADS.discard(dl_id)
        _ACTIVE_CIVITAI_DOWNLOADS[dl_id] = {
            'id': dl_id,
            'dl_id': dl_id,
            'filename': safe_fname,
            'asset_type': 'LORA' if is_lora else 'Checkpoint',
            'resource_role': detected_role,
            'modality': str(modality or 'IMAGE').upper(),
            'target_folder': target_cat,
            'part_path': str(part_path),
            'dest_path': str(dest_path),
            'status': 'downloading',
            'downloaded_bytes': 0,
            'total_bytes': est_bytes,
            'downloaded_mb': 0.0,
            'total_mb': round(est_bytes / (1024.0 * 1024.0), 2),
            'percent': 0.0,
            'speed_mbps': 0.0,
            'eta_sec': 0,
            'started_at': start_ts,
            'error': '',
        }

    def _run_download_worker() -> dict:
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) EZ-Cinematrix/2.8'
        api_k = load_civitai_api_key()
        try:
            written = 0
            resp = _open_civitai_download_stream(url_clean, api_k=api_k, user_agent=user_agent, timeout=300)
            try:
                cl_hdr = resp.headers.get('Content-Length')
                total_b = int(cl_hdr) if (cl_hdr and str(cl_hdr).isdigit()) else est_bytes
                ctype = str(resp.headers.get('Content-Type', '') or '').lower()
                if 'text/html' in ctype:
                    raise RuntimeError('Civitai kräver API-nyckel/inloggning för att ladda ner denna modell (fick HTML-sida istället för binärfil).')
                with open(part_path, 'wb') as out_f:
                    while True:
                        with _CIVITAI_DL_LOCK:
                            is_canc = (dl_id in _CANCELLED_CIVITAI_DOWNLOADS) or (_ACTIVE_CIVITAI_DOWNLOADS.get(dl_id, {}).get('status') == 'cancelled')
                        if is_canc:
                            raise InterruptedError('Nedladdningen avbröts och den halvfärdiga .part-filen raderades.')
                        chunk = resp.read(1024 * 1024)
                        if not chunk:
                            break
                        out_f.write(chunk)
                        written += len(chunk)
                        elapsed = max(0.05, time.time() - start_ts)
                        spd_mbps = (written / (1024.0 * 1024.0)) / elapsed
                        eff_tot = max(total_b, written)
                        pct = round((written / eff_tot) * 100.0, 1) if eff_tot > 0 else 0.0
                        rem_mb = max(0.0, (eff_tot - written) / (1024.0 * 1024.0)) if eff_tot > 0 else 0.0
                        eta_s = int(round(rem_mb / spd_mbps)) if (spd_mbps > 0.02 and eff_tot > 0) else 0
                        with _CIVITAI_DL_LOCK:
                            if dl_id in _ACTIVE_CIVITAI_DOWNLOADS and (dl_id not in _CANCELLED_CIVITAI_DOWNLOADS):
                                _ACTIVE_CIVITAI_DOWNLOADS[dl_id].update({
                                    'downloaded_bytes': written,
                                    'total_bytes': eff_tot,
                                    'downloaded_mb': round(written / (1024.0 * 1024.0), 2),
                                    'total_mb': round(eff_tot / (1024.0 * 1024.0), 2),
                                    'percent': min(99.9, pct),
                                    'speed_mbps': round(spd_mbps, 2),
                                    'eta_sec': eta_s,
                                })
            finally:
                try:
                    resp.close()
                except Exception:
                    pass
            with _CIVITAI_DL_LOCK:
                if (dl_id in _CANCELLED_CIVITAI_DOWNLOADS) or (_ACTIVE_CIVITAI_DOWNLOADS.get(dl_id, {}).get('status') == 'cancelled'):
                    raise InterruptedError('Nedladdningen avbröts och den halvfärdiga .part-filen raderades.')
            (is_valid, v_msg) = _verify_downloaded_safetensors_valid(part_path)
            if not is_valid:
                try:
                    part_path.unlink(missing_ok=True)
                except Exception:
                    pass
                raise RuntimeError(v_msg)
            os.replace(str(part_path), str(dest_path))
            _invalidate_comfyui_folder_cache()
            if sample_url and str(sample_url).startswith('http'):
                try:
                    p_ext = '.mp4' if '.mp4' in sample_url.lower() or '.webm' in sample_url.lower() else '.jpg'
                    prev_dest = dest_path.with_suffix(f'.preview{p_ext}')
                    s_req = urllib.request.Request(str(sample_url), headers={'User-Agent': user_agent})
                    with urllib.request.urlopen(s_req, timeout=15) as s_resp:
                        s_bytes = s_resp.read(15 * 1024 * 1024)
                        if len(s_bytes) > 64:
                            prev_dest.write_bytes(s_bytes)
                except Exception:
                    pass
            with _CIVITAI_DL_LOCK:
                if dl_id in _ACTIVE_CIVITAI_DOWNLOADS:
                    _ACTIVE_CIVITAI_DOWNLOADS[dl_id].update({
                        'status': 'completed',
                        'downloaded_bytes': written,
                        'total_bytes': written,
                        'downloaded_mb': round(written / (1024.0 * 1024.0), 2),
                        'total_mb': round(written / (1024.0 * 1024.0), 2),
                        'percent': 100.0,
                        'eta_sec': 0,
                    })
            return {'status': 'ok', 'dl_id': dl_id, 'filename': safe_fname, 'asset_type': 'LORA' if is_lora else 'Checkpoint', 'resource_role': detected_role, 'target_folder': target_cat, 'modality': str(modality or 'IMAGE').upper(), 'size_mb': round(written / (1024 * 1024), 2)}
        except Exception as exc:
            try:
                if part_path.exists():
                    part_path.unlink()
            except Exception:
                pass
            was_cancelled = isinstance(exc, InterruptedError)
            with _CIVITAI_DL_LOCK:
                if dl_id in _CANCELLED_CIVITAI_DOWNLOADS:
                    was_cancelled = True
                if dl_id in _ACTIVE_CIVITAI_DOWNLOADS:
                    _ACTIVE_CIVITAI_DOWNLOADS[dl_id].update({
                        'status': 'cancelled' if was_cancelled else 'failed',
                        'error': '🛑 Avbruten av användaren — halvfärdig .part-fil raderad från disk.' if was_cancelled else str(exc),
                        'speed_mbps': 0.0,
                        'eta_sec': 0,
                    })
            return {'status': 'cancelled' if was_cancelled else 'error', 'dl_id': dl_id, 'filename': safe_fname, 'message': f'Nedladdningsfel: {exc}'}

    if async_bg:
        t = threading.Thread(target=_run_download_worker, daemon=True)
        t.start()
        return {
            'status': 'started',
            'dl_id': dl_id,
            'filename': safe_fname,
            'asset_type': 'LORA' if is_lora else 'Checkpoint',
            'resource_role': detected_role,
            'target_folder': target_cat,
            'modality': str(modality or 'IMAGE').upper(),
            'total_mb': round(est_bytes / (1024.0 * 1024.0), 2),
        }
    return _run_download_worker()

CURATED_HF_PRESETS = [
    {
        'repo_id': 'huihui-ai/Huihui-Qwen3-VL-4B-Instruct-abliterated',
        'title': 'Huihui Qwen3-VL 4B Instruct Abliterated (Native Safetensors Repo)',
        'category': 'VLM_REPO',
        'target_folder': 'LLM/Qwen-VL',
        'recommended_file': '__FULL_HF_REPO__',
        'mmproj_file': '',
        'size_gb': 8.4,
        'note': 'Fastest native BF16/SDPA Safetensors Vision-Language Compiler for 16 GB GPUs (zero GGUF dequantization overhead).',
    },
    {
        'repo_id': 'huihui-ai/Huihui-Qwen3-VL-8B-Instruct-abliterated',
        'title': 'Huihui Qwen3-VL 8B Instruct Abliterated (Native Safetensors + EZ Q8 Cache)',
        'category': 'VLM_REPO',
        'target_folder': 'LLM/Qwen-VL',
        'recommended_file': '__FULL_HF_REPO__',
        'mmproj_file': '',
        'size_gb': 16.5,
        'note': 'Full 8B Safetensors Vision-Language Repo (auto-caches persistent Q8 Safetensors + SDPA on 16 GB VRAM).',
    },
    {
        'repo_id': 'mradermacher/Huihui-Qwen3-VL-8B-Instruct-abliterated-GGUF',
        'title': 'Huihui Qwen3-VL 8B Instruct Abliterated (Q8_0 GGUF Legacy Fallback)',
        'category': 'VLM_GGUF',
        'target_folder': 'LLM/Qwen-VL',
        'recommended_file': 'Huihui-Qwen3-VL-8B-Instruct-abliterated.Q8_0.gguf',
        'mmproj_file': 'Huihui-Qwen3-VL-8B-Instruct-abliterated.mmproj-f16.gguf',
        'size_gb': 8.7,
        'note': 'Legacy GGUF Q8_0 fallback with mmproj vision projector.',
    },
    {
        'repo_id': 'Mungert/Qwen3-VL-8B-Instruct-Unredacted-MAX-GGUF',
        'title': 'Qwen3-VL 8B Instruct Unredacted MAX (Q8_0 GGUF Legacy Fallback)',
        'category': 'VLM_GGUF',
        'target_folder': 'LLM/GGUF',
        'recommended_file': 'Qwen3-VL-8B-Instruct-Unredacted-MAX-q8_0.gguf',
        'mmproj_file': 'mmproj-model-f16.gguf',
        'size_gb': 8.7,
        'note': 'Uncensored Q8_0 GGUF fallback for [02] Timeline Compiler.',
    },
]

def load_hf_api_token() -> str:
    cred_path = get_civitai_credentials_path()
    if cred_path.exists():
        try:
            data = json.loads(cred_path.read_text(encoding='utf-8'))
            if isinstance(data, dict) and data.get('hf_token'):
                return str(data['hf_token']).strip()
        except Exception:
            pass
    return str(os.environ.get('HF_TOKEN', '') or '').strip()

def save_hf_api_token(hf_token: str) -> dict:
    cred_path = get_civitai_credentials_path()
    data = {}
    if cred_path.exists():
        try:
            data = json.loads(cred_path.read_text(encoding='utf-8'))
        except Exception:
            data = {}
    if not isinstance(data, dict):
        data = {}
    data['hf_token'] = str(hf_token or '').strip()
    cred_path.parent.mkdir(parents=True, exist_ok=True)
    cred_path.write_text(json.dumps(data, indent=2), encoding='utf-8')
    return {'status': 'ok', 'has_hf_token': bool(data['hf_token'])}

def _resolve_hf_target_base_dir(target_folder: str) -> Path:
    tf = str(target_folder or 'LLM/Qwen-VL').replace('\\', '/').strip('/')
    top_key = tf.split('/')[0] if '/' in tf else tf
    sub_rel = tf.split('/', 1)[1] if '/' in tf else ''
    folder_map = {
        'LLM': 'LLM',
        'text_encoders': 'text_encoders',
        'clip': 'clip',
        'diffusion_models': 'diffusion_models',
        'unet': 'unet',
        'loras': 'loras',
        'vae': 'vae',
        'checkpoints': 'checkpoints',
    }
    fk = folder_map.get(top_key, 'LLM')
    base_dir = None
    if fk in folder_paths.folder_names_and_paths:
        paths = folder_paths.get_folder_paths(fk)
        if paths:
            base_dir = Path(paths[0])
    if base_dir is None:
        models_root = Path(getattr(folder_paths, 'models_dir', Path.cwd() / 'models'))
        base_dir = models_root / top_key
    out_dir = (base_dir / sub_rel) if sub_rel else base_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir

def inspect_huggingface_repo_files(repo_id: str) -> dict:
    clean_repo = str(repo_id or '').strip().replace('https://huggingface.co/', '').strip('/')
    if '/blob/' in clean_repo:
        clean_repo = clean_repo.split('/blob/')[0]
    if '/resolve/' in clean_repo:
        clean_repo = clean_repo.split('/resolve/')[0]
    if '/tree/' in clean_repo:
        clean_repo = clean_repo.split('/tree/')[0]
    if not clean_repo or '/' not in clean_repo:
        return {'status': 'error', 'message': 'Ange ett giltigt HuggingFace repo (t.ex. org/model-name).', 'files': []}
    headers = {'User-Agent': 'EZCinematrixStudio/2.0'}
    hf_tok = load_hf_api_token()
    if hf_tok:
        headers['Authorization'] = f'Bearer {hf_tok}'
    files_out = []
    mmproj_files = []
    has_config = False
    total_repo_bytes = 0
    try:
        tree_url = f'https://huggingface.co/api/models/{clean_repo}/tree/main?recursive=true'
        req = urllib.request.Request(tree_url, headers=headers, method='GET')
        with urllib.request.urlopen(req, timeout=15) as resp:
            tree_data = json.loads(resp.read().decode('utf-8'))
        if isinstance(tree_data, list):
            for entry in tree_data:
                if not isinstance(entry, dict) or entry.get('type') != 'file':
                    continue
                rpath = str(entry.get('path', '') or '')
                sz = int(entry.get('size') or (entry.get('lfs') or {}).get('size') or 0)
                low_p = rpath.lower()
                if low_p.endswith('config.json'):
                    has_config = True
                if low_p.endswith(('.safetensors', '.json', '.txt', '.model', '.tiktoken', '.py', '.jinja')):
                    total_repo_bytes += sz
                if 'mmproj' in low_p and low_p.endswith('.gguf'):
                    mmproj_files.append({'path': rpath, 'size_mb': round(sz / (1024.0 * 1024.0), 1)})
                    continue
                if low_p.endswith(('.gguf', '.safetensors', '.bin', '.pth', '.pt')):
                    is_q8 = any((q in low_p for q in ('q8_0', 'q8', 'fp8', 'int8')))
                    files_out.append({
                        'path': rpath,
                        'size_bytes': sz,
                        'size_mb': round(sz / (1024.0 * 1024.0), 1),
                        'size_gb': round(sz / (1024.0 ** 3), 2),
                        'is_gguf': low_p.endswith('.gguf'),
                        'is_q8': is_q8,
                    })
        files_out.sort(key=lambda x: (not x['path'].lower().endswith('.safetensors'), not x['is_q8'], x['is_gguf'], x['path']))
        if has_config:
            files_out.insert(0, {
                'path': '__FULL_HF_REPO__',
                'label': f'📦 Hämta hela HuggingFace-mappen ({clean_repo.split("/")[-1]}) [{round(total_repo_bytes / (1024.0 ** 3), 2)} GB]',
                'size_bytes': total_repo_bytes,
                'size_mb': round(total_repo_bytes / (1024.0 * 1024.0), 1),
                'size_gb': round(total_repo_bytes / (1024.0 ** 3), 2),
                'is_gguf': False,
                'is_q8': False,
            })
        return {
            'status': 'ok',
            'repo_id': clean_repo,
            'files': files_out,
            'mmproj_files': mmproj_files,
            'has_config': has_config,
        }
    except Exception as exc:
        return {'status': 'error', 'repo_id': clean_repo, 'message': str(exc), 'files': []}

def query_huggingface_catalog(query_text: str='', category_filter: str='ALL', limit: int=16) -> dict:
    q = str(query_text or '').strip()
    if q.startswith('https://huggingface.co/'):
        q = q.replace('https://huggingface.co/', '').strip('/')
        if '/blob/' in q:
            q = q.split('/blob/')[0]
        elif '/tree/' in q:
            q = q.split('/tree/')[0]
    headers = {'User-Agent': 'EZCinematrixStudio/2.0'}
    hf_tok = load_hf_api_token()
    if hf_tok:
        headers['Authorization'] = f'Bearer {hf_tok}'
    items = []
    if not q:
        q_search = 'Qwen3-VL GGUF' if category_filter == 'VLM_GGUF' else ('Qwen3-VL' if category_filter.startswith('VLM') else 'Qwen3-VL abliterated')
    else:
        q_search = q
    try:
        params = urllib.parse.urlencode({'search': q_search, 'limit': min(30, max(8, int(limit))), 'sort': 'downloads', 'direction': '-1'})
        url = f'https://huggingface.co/api/models?{params}'
        req = urllib.request.Request(url, headers=headers, method='GET')
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw_list = json.loads(resp.read().decode('utf-8'))
        if isinstance(raw_list, list):
            for entry in raw_list:
                if not isinstance(entry, dict):
                    continue
                rid = str(entry.get('id') or entry.get('modelId') or '').strip()
                if not rid:
                    continue
                tags = [str(t).lower() for t in (entry.get('tags') or [])]
                low_id = rid.lower()
                is_gguf_repo = ('gguf' in low_id) or ('gguf' in tags)
                is_vlm = any((k in low_id for k in ('vl', 'qwen', 'llava', 'vision', 'minicpm'))) or ('image-text-to-text' in tags)
                if category_filter == 'VLM_GGUF' and not is_gguf_repo:
                    continue
                if category_filter == 'VLM_REPO' and is_gguf_repo:
                    continue
                rec_target = 'LLM/GGUF' if is_gguf_repo else ('LLM/Qwen-VL' if is_vlm else 'diffusion_models')
                items.append({
                    'repo_id': rid,
                    'name': rid.split('/')[-1],
                    'author': rid.split('/')[0] if '/' in rid else 'huggingface',
                    'downloads': int(entry.get('downloads') or 0),
                    'likes': int(entry.get('likes') or 0),
                    'is_gguf': is_gguf_repo,
                    'is_vlm': is_vlm,
                    'recommended_target': rec_target,
                    'pipeline_tag': str(entry.get('pipeline_tag') or ('GGUF' if is_gguf_repo else 'Transformers')),
                })
    except Exception as exc:
        return {'status': 'ok', 'items': items, 'curated': CURATED_HF_PRESETS, 'notice': f'HuggingFace API notice: {exc}'}
    return {'status': 'ok', 'items': items[:limit], 'curated': CURATED_HF_PRESETS}

def _stream_url_to_file_with_telemetry(url: str, dest_file: Path, dl_id: str, headers: dict, base_offset: int=0, grand_total: int=0) -> int:
    dest_file.parent.mkdir(parents=True, exist_ok=True)
    part_file = dest_file.with_suffix(dest_file.suffix + '.part')
    with _CIVITAI_DL_LOCK:
        if dl_id in _ACTIVE_CIVITAI_DOWNLOADS:
            _ACTIVE_CIVITAI_DOWNLOADS[dl_id]['part_path'] = str(part_file)
            _ACTIVE_CIVITAI_DOWNLOADS[dl_id]['dest_path'] = str(dest_file)
    req = urllib.request.Request(url, headers=headers, method='GET')
    written_file = 0
    t_start = time.time()
    last_t = t_start
    last_b = 0
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            c_len = int(resp.headers.get('Content-Length') or 0)
            eff_total = grand_total if grand_total > 0 else c_len
            with open(part_file, 'wb') as f_out:
                while True:
                    with _CIVITAI_DL_LOCK:
                        is_canc = (dl_id in _CANCELLED_CIVITAI_DOWNLOADS) or (_ACTIVE_CIVITAI_DOWNLOADS.get(dl_id, {}).get('status') == 'cancelled')
                    if is_canc:
                        raise InterruptedError('Nedladdningen avbröts och den halvfärdiga .part-filen raderades.')
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    f_out.write(chunk)
                    written_file += len(chunk)
                    now = time.time()
                    if now - last_t >= 0.25:
                        dt = max(0.05, now - last_t)
                        spd = ((written_file - last_b) / (1024.0 * 1024.0)) / dt
                        cur_tot_dl = base_offset + written_file
                        pct = min(99.9, (cur_tot_dl * 100.0 / eff_total)) if eff_total > 0 else 50.0
                        rem_mb = max(0.0, (eff_total - cur_tot_dl) / (1024.0 * 1024.0)) if eff_total > 0 else 0.0
                        eta = int(rem_mb / max(0.05, spd)) if eff_total > 0 and spd > 0.01 else 0
                        with _CIVITAI_DL_LOCK:
                            if dl_id in _ACTIVE_CIVITAI_DOWNLOADS and (dl_id not in _CANCELLED_CIVITAI_DOWNLOADS):
                                _ACTIVE_CIVITAI_DOWNLOADS[dl_id].update({
                                    'downloaded_bytes': cur_tot_dl,
                                    'total_bytes': max(cur_tot_dl, eff_total),
                                    'downloaded_mb': round(cur_tot_dl / (1024.0 * 1024.0), 2),
                                    'total_mb': round(max(cur_tot_dl, eff_total) / (1024.0 * 1024.0), 2),
                                    'percent': round(pct, 1),
                                    'speed_mbps': round(spd, 2),
                                    'eta_sec': eta,
                                })
                        last_t = now
                        last_b = written_file
        os.replace(str(part_file), str(dest_file))
        return written_file
    except Exception:
        try:
            if part_file.exists():
                part_file.unlink()
        except Exception:
            pass
        raise

def download_huggingface_asset_to_comfyui(repo_id: str, filename: str='', target_folder: str='LLM/Qwen-VL', include_mmproj: bool=True) -> dict:
    clean_repo = str(repo_id or '').strip().replace('https://huggingface.co/', '').strip('/')
    file_rel = str(filename or '').strip()
    if '/blob/main/' in clean_repo and not file_rel:
        (clean_repo, file_rel) = clean_repo.split('/blob/main/', 1)
    elif '/resolve/main/' in clean_repo and not file_rel:
        (clean_repo, file_rel) = clean_repo.split('/resolve/main/', 1)
    if not clean_repo or '/' not in clean_repo:
        return {'status': 'error', 'message': 'Ogiltigt HuggingFace repo_id (ange t.ex. org/model).'}
    base_dir = _resolve_hf_target_base_dir(target_folder)
    headers = {'User-Agent': 'EZCinematrixStudio/2.0'}
    hf_tok = load_hf_api_token()
    if hf_tok:
        headers['Authorization'] = f'Bearer {hf_tok}'
    inspected = inspect_huggingface_repo_files(clean_repo)
    repo_short = clean_repo.split('/')[-1]
    is_full_repo = (not file_rel) or (file_rel == '__FULL_HF_REPO__')
    dl_id = f'hf_{int(time.time() * 1000)}_{hashlib.md5((clean_repo + ":" + file_rel).encode("utf-8")).hexdigest()[:6]}'
    display_name = f'{repo_short} (HF Repo)' if is_full_repo else os.path.basename(file_rel)
    with _CIVITAI_DL_LOCK:
        _CANCELLED_CIVITAI_DOWNLOADS.discard(dl_id)
        _ACTIVE_CIVITAI_DOWNLOADS[dl_id] = {
            'id': dl_id,
            'dl_id': dl_id,
            'filename': display_name,
            'asset_type': 'VLM' if target_folder.startswith('LLM') else 'Checkpoint',
            'modality': 'VLM' if target_folder.startswith('LLM') else 'IMAGE',
            'repo_dest_dir': str(base_dir / repo_short) if is_full_repo else '',
            'status': 'downloading',
            'downloaded_bytes': 0,
            'total_bytes': 0,
            'downloaded_mb': 0.0,
            'total_mb': 0.0,
            'percent': 0.0,
            'speed_mbps': 0.0,
            'eta_sec': 0,
            'started_at': time.time(),
            'error': '',
        }
    try:
        written_total = 0
        if is_full_repo:
            repo_dest_dir = base_dir / repo_short
            repo_dest_dir.mkdir(parents=True, exist_ok=True)
            tree_url = f'https://huggingface.co/api/models/{clean_repo}/tree/main?recursive=true'
            req = urllib.request.Request(tree_url, headers=headers, method='GET')
            with urllib.request.urlopen(req, timeout=20) as resp:
                tree_data = json.loads(resp.read().decode('utf-8'))
            dl_entries = []
            grand_total = 0
            for entry in (tree_data if isinstance(tree_data, list) else []):
                if not isinstance(entry, dict) or entry.get('type') != 'file':
                    continue
                rpath = str(entry.get('path', '') or '')
                if rpath.startswith('.') or rpath.lower().endswith(('.md', '.gitattributes', '.png', '.jpg', '.gif', '.mp4')):
                    continue
                sz = int(entry.get('size') or (entry.get('lfs') or {}).get('size') or 0)
                dl_entries.append((rpath, sz))
                grand_total += sz
            for (rpath, sz) in dl_entries:
                f_url = f'https://huggingface.co/{clean_repo}/resolve/main/{urllib.parse.quote(rpath)}'
                dest_f = repo_dest_dir / rpath
                if dest_f.exists() and sz > 0 and dest_f.stat().st_size == sz:
                    written_total += sz
                    continue
                written_total += _stream_url_to_file_with_telemetry(f_url, dest_f, dl_id, headers, base_offset=written_total, grand_total=grand_total)
            vlm_rel_val = f'{target_folder.split("/", 1)[1]}\\{repo_short}' if '/' in target_folder else repo_short
        else:
            f_url = f'https://huggingface.co/{clean_repo}/resolve/main/{urllib.parse.quote(file_rel)}'
            dest_f = base_dir / os.path.basename(file_rel)
            mmproj_to_dl = ''
            if include_mmproj and file_rel.lower().endswith('.gguf') and 'mmproj' not in file_rel.lower():
                mm_list = inspected.get('mmproj_files') or []
                if mm_list:
                    mmproj_to_dl = str(mm_list[0].get('path', '') or '')
            written_total += _stream_url_to_file_with_telemetry(f_url, dest_f, dl_id, headers, base_offset=0, grand_total=0)
            if mmproj_to_dl:
                mm_url = f'https://huggingface.co/{clean_repo}/resolve/main/{urllib.parse.quote(mmproj_to_dl)}'
                mm_dest = base_dir / os.path.basename(mmproj_to_dl)
                if not mm_dest.exists():
                    written_total += _stream_url_to_file_with_telemetry(mm_url, mm_dest, dl_id, headers, base_offset=written_total, grand_total=0)
            vlm_rel_val = f'{target_folder.split("/", 1)[1]}\\{dest_f.name}' if '/' in target_folder else dest_f.name
        with _CIVITAI_DL_LOCK:
            if dl_id in _ACTIVE_CIVITAI_DOWNLOADS:
                _ACTIVE_CIVITAI_DOWNLOADS[dl_id].update({
                    'status': 'completed',
                    'downloaded_bytes': written_total,
                    'total_bytes': written_total,
                    'downloaded_mb': round(written_total / (1024.0 * 1024.0), 2),
                    'total_mb': round(written_total / (1024.0 * 1024.0), 2),
                    'percent': 100.0,
                    'eta_sec': 0,
                })
        return {
            'status': 'ok',
            'dl_id': dl_id,
            'repo_id': clean_repo,
            'filename': display_name,
            'vlm_dropdown_value': vlm_rel_val,
            'target_folder': target_folder,
            'size_mb': round(written_total / (1024.0 * 1024.0), 2),
        }
    except Exception as exc:
        was_cancelled = isinstance(exc, InterruptedError)
        with _CIVITAI_DL_LOCK:
            if dl_id in _CANCELLED_CIVITAI_DOWNLOADS:
                was_cancelled = True
            if dl_id in _ACTIVE_CIVITAI_DOWNLOADS:
                if was_cancelled:
                    _purge_partial_download_artifacts(_ACTIVE_CIVITAI_DOWNLOADS[dl_id])
                _ACTIVE_CIVITAI_DOWNLOADS[dl_id].update({
                    'status': 'cancelled' if was_cancelled else 'failed',
                    'error': '🛑 Avbruten av användaren — halvfärdig .part-fil raderad från disk.' if was_cancelled else str(exc),
                    'speed_mbps': 0.0,
                    'eta_sec': 0,
                })
        return {'status': 'cancelled' if was_cancelled else 'error', 'dl_id': dl_id, 'message': f'HuggingFace nedladdningsfel: {exc}'}

def build_civitai_controller_specs(controller_modality: str, civitai_domain: str, sort_by: str, time_period: str, image_architecture: str, image_unet_name: str, image_style_lora_1: str, image_style_strength_1: float, image_style_lora_2: str, image_style_strength_2: float, image_style_lora_3: str, image_style_strength_3: float, image_turbo_lora: str, image_turbo_strength: float, video_architecture: str, video_unet_fl2va: str, video_lora_1: str, video_lora_1_strength: float, video_lora_2: str, video_lora_2_strength: float, video_lora_3: str, video_lora_3_strength: float, video_turbo_lora: str, video_turbo_strength: float, image_style_lora_4: str='None', image_style_strength_4: float=0.4, enable_image_lora_1: bool=True, enable_image_lora_2: bool=True, enable_image_lora_3: bool=True, enable_image_lora_4: bool=True, enable_image_turbo_lora: bool=True, video_lora_4: str='None', video_lora_4_strength: float=0.35, enable_video_lora_1: bool=True, enable_video_lora_2: bool=True, enable_video_lora_3: bool=True, enable_video_lora_4: bool=True, enable_video_turbo_lora: bool=True, trigger_words: str='', active_recipe_name: str='None', auto_purge_30d_cache: bool=True):
    if auto_purge_30d_cache:
        purge_civitai_cache(force_clear_all=False, max_age_days=CACHE_TTL_DAYS)
    lic = verify_civitai_license_status()
    if active_recipe_name and active_recipe_name not in ('None', ''):
        for r in load_civitai_recipes():
            if isinstance(r, dict) and (r.get('name') == active_recipe_name or r.get('id') == active_recipe_name):
                if r.get('image_unet_name') or r.get('image_style_lora_1'):
                    image_unet_name = r.get('image_unet_name') or image_unet_name
                    image_style_lora_1 = r.get('image_style_lora_1') or image_style_lora_1
                    image_style_strength_1 = float(r.get('image_style_strength_1', image_style_strength_1))
                    image_style_lora_2 = r.get('image_style_lora_2') or image_style_lora_2
                    image_style_strength_2 = float(r.get('image_style_strength_2', image_style_strength_2))
                    image_style_lora_3 = r.get('image_style_lora_3') or image_style_lora_3
                    image_style_strength_3 = float(r.get('image_style_strength_3', image_style_strength_3))
                    image_style_lora_4 = r.get('image_style_lora_4') or image_style_lora_4
                    image_style_strength_4 = float(r.get('image_style_strength_4', image_style_strength_4))
                    image_turbo_lora = r.get('image_turbo_lora') or image_turbo_lora
                    image_turbo_strength = float(r.get('image_turbo_strength', image_turbo_strength))
                elif r.get('modality') == 'IMAGE':
                    image_unet_name = r.get('model_name') or image_unet_name
                    image_style_lora_1 = r.get('lora_1') or image_style_lora_1
                    image_style_strength_1 = float(r.get('lora_1_strength', image_style_strength_1))
                    image_style_lora_2 = r.get('lora_2') or image_style_lora_2
                    image_style_strength_2 = float(r.get('lora_2_strength', image_style_strength_2))
                    image_style_lora_3 = r.get('lora_3') or image_style_lora_3
                    image_style_strength_3 = float(r.get('lora_3_strength', image_style_strength_3))
                    image_style_lora_4 = r.get('lora_4') or image_style_lora_4
                    image_style_strength_4 = float(r.get('lora_4_strength', image_style_strength_4))
                    image_turbo_lora = r.get('turbo_lora') or image_turbo_lora
                    image_turbo_strength = float(r.get('turbo_strength', image_turbo_strength))
                if r.get('video_unet_fl2va') or r.get('video_lora_1'):
                    video_unet_fl2va = r.get('video_unet_fl2va') or video_unet_fl2va
                    video_lora_1 = r.get('video_lora_1') or video_lora_1
                    video_lora_1_strength = float(r.get('video_lora_1_strength', video_lora_1_strength))
                    video_lora_2 = r.get('video_lora_2') or video_lora_2
                    video_lora_2_strength = float(r.get('video_lora_2_strength', video_lora_2_strength))
                    video_lora_3 = r.get('video_lora_3') or video_lora_3
                    video_lora_3_strength = float(r.get('video_lora_3_strength', video_lora_3_strength))
                    video_lora_4 = r.get('video_lora_4') or video_lora_4
                    video_lora_4_strength = float(r.get('video_lora_4_strength', video_lora_4_strength))
                    video_turbo_lora = r.get('video_turbo_lora') or video_turbo_lora
                    video_turbo_strength = float(r.get('video_turbo_strength', video_turbo_strength))
                elif r.get('modality') == 'VIDEO':
                    video_unet_fl2va = r.get('model_name') or video_unet_fl2va
                    video_lora_1 = r.get('lora_1') or video_lora_1
                    video_lora_1_strength = float(r.get('lora_1_strength', video_lora_1_strength))
                    video_lora_2 = r.get('lora_2') or video_lora_2
                    video_lora_2_strength = float(r.get('lora_2_strength', video_lora_2_strength))
                    video_lora_3 = r.get('lora_3') or video_lora_3
                    video_lora_3_strength = float(r.get('lora_3_strength', video_lora_3_strength))
                    video_lora_4 = r.get('lora_4') or video_lora_4
                    video_lora_4_strength = float(r.get('lora_4_strength', video_lora_4_strength))
                    video_turbo_lora = r.get('turbo_lora') or video_turbo_lora
                    video_turbo_strength = float(r.get('turbo_strength', video_turbo_strength))
                if not str(trigger_words or '').strip() and r.get('trigger_words'):
                    trigger_words = str(r['trigger_words'])
                break
    image_unet_name = enforce_modality_lock('IMAGE', image_unet_name, 'diffusion_models', image_architecture)
    image_style_lora_1 = enforce_modality_lock('IMAGE', image_style_lora_1, 'loras', image_architecture)
    image_style_lora_2 = enforce_modality_lock('IMAGE', image_style_lora_2, 'loras', image_architecture)
    image_style_lora_3 = enforce_modality_lock('IMAGE', image_style_lora_3, 'loras', image_architecture)
    image_style_lora_4 = enforce_modality_lock('IMAGE', image_style_lora_4, 'loras', image_architecture)
    image_turbo_lora = enforce_modality_lock('IMAGE', image_turbo_lora, 'loras', image_architecture)
    video_unet_fl2va = enforce_modality_lock('VIDEO', video_unet_fl2va, 'diffusion_models', video_architecture)
    video_lora_1 = enforce_modality_lock('VIDEO', video_lora_1, 'loras', video_architecture)
    video_lora_2 = enforce_modality_lock('VIDEO', video_lora_2, 'loras', video_architecture)
    video_lora_3 = enforce_modality_lock('VIDEO', video_lora_3, 'loras', video_architecture)
    video_lora_4 = enforce_modality_lock('VIDEO', video_lora_4, 'loras', video_architecture)
    video_turbo_lora = enforce_modality_lock('VIDEO', video_turbo_lora, 'loras', video_architecture)
    eff_img_l1 = str(image_style_lora_1 or 'None') if bool(enable_image_lora_1) else 'None'
    eff_img_l2 = str(image_style_lora_2 or 'None') if bool(enable_image_lora_2) else 'None'
    eff_img_l3 = str(image_style_lora_3 or 'None') if bool(enable_image_lora_3) else 'None'
    eff_img_l4 = str(image_style_lora_4 or 'None') if bool(enable_image_lora_4) else 'None'
    eff_img_turbo = str(image_turbo_lora or 'None') if bool(enable_image_turbo_lora) else 'None'
    eff_vid_l1 = str(video_lora_1 or 'None') if bool(enable_video_lora_1) else 'None'
    eff_vid_l2 = str(video_lora_2 or 'None') if bool(enable_video_lora_2) else 'None'
    eff_vid_l3 = str(video_lora_3 or 'None') if bool(enable_video_lora_3) else 'None'
    eff_vid_l4 = str(video_lora_4 or 'None') if bool(enable_video_lora_4) else 'None'
    eff_vid_turbo = str(video_turbo_lora or 'None') if bool(enable_video_turbo_lora) else 'None'
    img_comp = resolve_architecture_companions(
        image_architecture,
        'IMAGE',
        selected_model=image_unet_name,
        selected_loras=[eff_img_l1, eff_img_l2, eff_img_l3, eff_img_l4, eff_img_turbo],
    )
    vid_comp = resolve_architecture_companions(
        video_architecture,
        'VIDEO',
        selected_model=video_unet_fl2va,
        selected_loras=[eff_vid_l1, eff_vid_l2, eff_vid_l3, eff_vid_l4, eff_vid_turbo],
    )
    image_model_spec = {'modality': 'IMAGE', 'architecture': str(image_architecture or 'krea2'), 'unet_name': str(image_unet_name or 'None'), 'clip_type': str(img_comp.get('clip_type', 'krea2')), 'clip_name': str(img_comp.get('clip_name', 'None')), 'vae_name': str(img_comp.get('vae_name', 'None')), 'license_tier': lic['tier']}
    image_lora_spec = {
        'modality': 'IMAGE',
        'architecture': str(image_architecture or 'krea2'),
        'style_loras': [
            (eff_img_l1, float(image_style_strength_1) if bool(enable_image_lora_1) else 0.0),
            (eff_img_l2, float(image_style_strength_2) if bool(enable_image_lora_2) else 0.0),
            (eff_img_l3, float(image_style_strength_3) if bool(enable_image_lora_3) else 0.0),
            (eff_img_l4, float(image_style_strength_4) if bool(enable_image_lora_4) else 0.0),
        ],
        'style_enables': [bool(enable_image_lora_1), bool(enable_image_lora_2), bool(enable_image_lora_3), bool(enable_image_lora_4)],
        'enable_turbo_lora': bool(enable_image_turbo_lora),
        'turbo_lora': eff_img_turbo,
        'turbo_strength': float(image_turbo_strength) if bool(enable_image_turbo_lora) else 0.0,
        'trigger_words': str(trigger_words or '').strip(),
    }
    video_model_spec = {'modality': 'VIDEO', 'architecture': str(video_architecture or 'MiniMax H3'), 'video_unet_fl2va': str(video_unet_fl2va or 'None'), 'clip_type': str(vid_comp.get('clip_type', 'minimax')), 'video_clip_name': str(vid_comp.get('clip_name', 'None')), 'video_vae_name': str(vid_comp.get('vae_name', 'None')), 'audio_vae_name': str(vid_comp.get('audio_vae_name', 'None')), 'license_tier': lic['tier']}
    video_lora_spec = {
        'modality': 'VIDEO',
        'architecture': str(video_architecture or 'MiniMax H3'),
        'video_loras': [
            (eff_vid_l1, float(video_lora_1_strength) if bool(enable_video_lora_1) else 0.0, 0.0, 1.0, 0.0),
            (eff_vid_l2, float(video_lora_2_strength) if bool(enable_video_lora_2) else 0.0, 0.0, 1.0, 0.0),
            (eff_vid_l3, float(video_lora_3_strength) if bool(enable_video_lora_3) else 0.0, 0.0, 1.0, 0.0),
            (eff_vid_l4, float(video_lora_4_strength) if bool(enable_video_lora_4) else 0.0, 0.0, 1.0, 0.0),
        ],
        'video_enables': [bool(enable_video_lora_1), bool(enable_video_lora_2), bool(enable_video_lora_3), bool(enable_video_lora_4)],
        'enable_video_turbo_lora': bool(enable_video_turbo_lora),
        'video_turbo_lora': eff_vid_turbo,
        'turbo_video_strength': float(video_turbo_strength) if bool(enable_video_turbo_lora) else 0.0,
        'turbo_audio_strength': 1.0 if bool(enable_video_turbo_lora) else 0.0,
        'trigger_words': str(trigger_words or '').strip(),
    }
    return (image_model_spec, image_lora_spec, video_model_spec, video_lora_spec, str(trigger_words or '').strip())

def register_civitai_promptserver_routes():
    try:
        import asyncio
        from aiohttp import web
        from server import PromptServer
        ps = getattr(PromptServer, 'instance', None)
        if ps is None or getattr(ps, '_ez_civitai_routes_registered', False):
            return
        ps._ez_civitai_routes_registered = True

        async def _ez_civitai_status(request):
            tier_sel = str(request.rel_url.query.get('tier_selection', '') or '')
            c_rating = str(request.rel_url.query.get('content_rating', 'Uncensored') or 'Uncensored')
            purge_stats = purge_civitai_cache(force_clear_all=False)
            lic = verify_civitai_license_status()
            key_val = load_civitai_api_key()
            masked = f'{key_val[:4]}...{key_val[-4:]}' if len(key_val) >= 8 else 'SET' if key_val else ''
            hf_tok = load_hf_api_token()
            hf_masked = f'{hf_tok[:4]}...{hf_tok[-4:]}' if len(hf_tok) >= 8 else 'SET' if hf_tok else ''
            img_c = resolve_architecture_companions('KREA2', 'IMAGE', tier_selection=tier_sel, content_rating=c_rating)
            vid_c = resolve_architecture_companions('MiniMax H3', 'VIDEO', tier_selection=tier_sel, content_rating=c_rating)
            return web.json_response({'status': 'ok', 'license': lic, 'licensed': bool(lic.get('licensed', False)), 'has_api_key': bool(key_val), 'has_key': bool(key_val), 'masked_api_key': masked, 'has_hf_token': bool(hf_tok), 'masked_hf_token': hf_masked, 'cache': purge_stats, 'cache_files': int(purge_stats.get('remaining_files', 0)), 'cache_mb': float(purge_stats.get('total_mb', 0.0)), 'recipes': load_civitai_recipes(), 'system_tier': img_c.get('system_tier'), 'image_companions': img_c, 'video_companions': vid_c})

        async def _ez_civitai_save_key(request):
            try:
                body = await request.json()
            except Exception:
                body = {}
            if 'hf_token' in body:
                hf_res = save_hf_api_token(str(body.get('hf_token', '') or ''))
                if 'api_key' not in body:
                    return web.json_response(hf_res)
            res = save_civitai_api_key(str(body.get('api_key', '') or ''))
            res['has_key'] = bool(res.get('has_api_key', res.get('has_key', False)))
            return web.json_response(res)

        async def _ez_civitai_clear_cache(request):
            res = purge_civitai_cache(force_clear_all=True)
            res['removed_files'] = int(res.get('removed_files', res.get('removed', 0)))
            return web.json_response(res)

        async def _ez_civitai_search(request):
            try:
                body = await request.json()
            except Exception:
                body = {}
            loop = asyncio.get_running_loop()
            res = await loop.run_in_executor(None, lambda : query_civitai_catalog(modality=str(body.get('modality', 'IMAGE')), asset_type=str(body.get('asset_type', 'LORA')), base_arch=str(body.get('base_arch', 'All')), sort_by=str(body.get('sort_by', 'Most Downloaded')), period=str(body.get('period', 'AllTime')), domain_mode=str(body.get('domain_mode', 'civitai.com')), query_text=str(body.get('query', '')), limit=int(body.get('limit', 12) or 12), force_refresh=bool(body.get('force_refresh', False))))
            return web.json_response(res)

        async def _ez_civitai_hf_search(request):
            try:
                body = await request.json()
            except Exception:
                body = {}
            action = str(body.get('action', 'search') or 'search').lower()
            loop = asyncio.get_running_loop()
            if action == 'inspect':
                res = await loop.run_in_executor(None, lambda: inspect_huggingface_repo_files(str(body.get('repo_id', '') or '')))
            else:
                res = await loop.run_in_executor(None, lambda: query_huggingface_catalog(query_text=str(body.get('query', '') or ''), category_filter=str(body.get('category', 'ALL') or 'ALL'), limit=int(body.get('limit', 16) or 16)))
            return web.json_response(res)

        async def _ez_civitai_hf_download(request):
            try:
                body = await request.json()
            except Exception:
                body = {}
            loop = asyncio.get_running_loop()
            res = await loop.run_in_executor(
                None,
                lambda: download_huggingface_asset_to_comfyui(
                    repo_id=str(body.get('repo_id', '') or ''),
                    filename=str(body.get('filename', '') or ''),
                    target_folder=str(body.get('target_folder', 'LLM/Qwen-VL') or 'LLM/Qwen-VL'),
                    include_mmproj=bool(body.get('include_mmproj', True)),
                ),
            )
            return web.json_response(res)

        async def _ez_civitai_thumb(request):
            fname = os.path.basename(str(request.rel_url.query.get('file', '') or ''))
            fpath = get_civitai_cache_dir() / 'thumbs' / fname
            if not fname or not fpath.exists():
                return web.Response(status=404)
            return web.FileResponse(path=str(fpath))

        async def _ez_civitai_local_catalog(request):
            tier_sel = str(request.rel_url.query.get('tier_selection', '') or '')
            c_rating = str(request.rel_url.query.get('content_rating', 'Uncensored') or 'Uncensored')
            if request.method == 'POST':
                try:
                    body = await request.json()
                    tier_sel = str(body.get('tier_selection', tier_sel) or '')
                    c_rating = str(body.get('content_rating', c_rating) or 'Uncensored')
                except Exception:
                    pass
            loop = asyncio.get_running_loop()
            res = await loop.run_in_executor(None, lambda: scan_local_comfyui_assets(tier_sel, content_rating=c_rating))
            return web.json_response(res)

        async def _ez_civitai_local_preview(request):
            cat = str(request.rel_url.query.get('cat', 'loras') or 'loras')
            rel_name = str(request.rel_url.query.get('name', '') or '')
            if cat not in ('loras', 'diffusion_models', 'unet', 'checkpoints') or not rel_name:
                return web.Response(status=404)
            full_p = folder_paths.get_full_path(cat, rel_name) if cat in folder_paths.folder_names_and_paths else None
            (sidecar_p, _) = _find_sidecar_preview(full_p)
            if not sidecar_p or not os.path.isfile(sidecar_p):
                return web.Response(status=404)
            return web.FileResponse(path=str(sidecar_p))

        async def _ez_civitai_download(request):
            try:
                body = await request.json()
            except Exception:
                body = {}
            loop = asyncio.get_running_loop()
            res = await loop.run_in_executor(
                None,
                lambda: download_civitai_asset_to_comfyui(
                    download_url=str(body.get('download_url', '') or ''),
                    filename=str(body.get('filename', '') or ''),
                    asset_type=str(body.get('asset_type', 'LORA') or 'LORA'),
                    modality=str(body.get('modality', 'IMAGE') or 'IMAGE'),
                    sample_url=str(body.get('sample_url', '') or ''),
                    model_id=str(body.get('model_id', '') or ''),
                    expected_size_kb=float(body.get('size_kb', 0.0) or 0.0),
                    version_id=str(body.get('version_id', '') or ''),
                    file_id=str(body.get('file_id', '') or ''),
                    async_bg=bool(body.get('async_bg', False)),
                ),
            )
            return web.json_response(res)

        async def _ez_civitai_model_details(request):
            try:
                if request.method == 'POST':
                    body = await request.json()
                else:
                    body = dict(request.rel_url.query)
            except Exception:
                body = {}
            loop = asyncio.get_running_loop()
            res = await loop.run_in_executor(
                None,
                lambda: fetch_civitai_model_details(
                    model_id=str(body.get('model_id', '') or ''),
                    domain=str(body.get('domain', 'civitai.com') or 'civitai.com'),
                    modality=str(body.get('modality', 'IMAGE') or 'IMAGE'),
                ),
            )
            return web.json_response(res)

        async def _ez_civitai_downloads_status(request):
            if request.method == 'POST':
                try:
                    body = await request.json()
                except Exception:
                    body = {}
                act = str(body.get('action', '') or '').lower()
                if act in ('clear', 'clear_completed'):
                    return web.json_response(clear_completed_civitai_downloads())
                if act in ('cancel', 'cancel_download', 'stop'):
                    return web.json_response(
                        cancel_civitai_download(
                            dl_id=str(body.get('dl_id', '') or ''),
                            filename=str(body.get('filename', '') or ''),
                            cancel_all=bool(body.get('cancel_all', False)),
                        )
                    )
            return web.json_response(get_civitai_downloads_status())

        async def _ez_civitai_companions(request):
            try:
                body = await request.json()
            except Exception:
                body = {}
            arch = str(body.get('architecture', 'KREA2'))
            mod = str(body.get('modality', 'IMAGE'))
            sel_model = str(body.get('selected_model', '') or '')
            sel_loras = body.get('selected_loras') if isinstance(body.get('selected_loras'), list) else []
            tier_sel = str(body.get('tier_selection', '') or '')
            c_rating = str(body.get('content_rating', 'Uncensored') or 'Uncensored')
            action = str(body.get('action', 'resolve')).lower()
            loop = asyncio.get_running_loop()
            if action == 'download':
                res = await loop.run_in_executor(None, lambda : download_architecture_companions(arch, mod, tier_selection=tier_sel))
            else:
                res = await loop.run_in_executor(None, lambda : resolve_architecture_companions(arch, mod, sel_model, sel_loras, tier_selection=tier_sel, content_rating=c_rating))
            return web.json_response(res)

        async def _ez_civitai_delete_local(request):
            try:
                body = await request.json()
            except Exception:
                body = {}
            cat = str(body.get('category', '') or '')
            rname = str(body.get('name', '') or '')
            loop = asyncio.get_running_loop()
            res = await loop.run_in_executor(None, lambda : delete_local_comfyui_asset(cat, rname))
            return web.json_response(res)

        async def _ez_civitai_recipes(request):
            try:
                body = await request.json()
            except Exception:
                body = {}
            action = str(body.get('action', 'list')).lower()
            if action == 'save':
                return web.json_response(save_civitai_recipe(body.get('recipe') or {}))
            if action == 'delete':
                return web.json_response(delete_civitai_recipe(str(body.get('id', ''))))
            return web.json_response({'status': 'ok', 'recipes': load_civitai_recipes()})

        async def _ez_civitai_locales(request):
            from .engine_ez_locales import load_project_locales_payload, set_project_active_locale, register_project_custom_language
            if request.method == 'GET':
                return web.json_response({'status': 'ok', **load_project_locales_payload()})
            try:
                body = await request.json()
            except Exception:
                body = {}
            action = str(body.get('action', 'set')).lower()
            if action == 'register':
                res = register_project_custom_language(lang_code=str(body.get('lang_code', '')), lang_label=str(body.get('lang_label', '')), custom_translations=body.get('translations') if isinstance(body.get('translations'), dict) else None)
                return web.json_response(res)
            payload = set_project_active_locale(str(body.get('locale', 'EN')))
            return web.json_response({'status': 'ok', **payload})
        for prefix in ('/ez_cinematrix/civitai', '/api/ez_cinematrix/civitai'):
            ps.routes.get(f'{prefix}/status')(_ez_civitai_status)
            ps.routes.post(f'{prefix}/apikey')(_ez_civitai_save_key)
            ps.routes.post(f'{prefix}/cache/clear')(_ez_civitai_clear_cache)
            ps.routes.post(f'{prefix}/search')(_ez_civitai_search)
            ps.routes.get(f'{prefix}/model_details')(_ez_civitai_model_details)
            ps.routes.post(f'{prefix}/model_details')(_ez_civitai_model_details)
            ps.routes.post(f'{prefix}/hf_search')(_ez_civitai_hf_search)
            ps.routes.post(f'{prefix}/hf_download')(_ez_civitai_hf_download)
            ps.routes.get(f'{prefix}/thumb')(_ez_civitai_thumb)
            ps.routes.get(f'{prefix}/local_catalog')(_ez_civitai_local_catalog)
            ps.routes.post(f'{prefix}/local_catalog')(_ez_civitai_local_catalog)
            ps.routes.post(f'{prefix}/delete_local')(_ez_civitai_delete_local)
            ps.routes.get(f'{prefix}/local_preview')(_ez_civitai_local_preview)
            ps.routes.post(f'{prefix}/download')(_ez_civitai_download)
            ps.routes.get(f'{prefix}/downloads_status')(_ez_civitai_downloads_status)
            ps.routes.post(f'{prefix}/downloads_status')(_ez_civitai_downloads_status)
            ps.routes.post(f'{prefix}/cancel_download')(_ez_civitai_downloads_status)
            ps.routes.post(f'{prefix}/companions')(_ez_civitai_companions)
            ps.routes.post(f'{prefix}/recipes')(_ez_civitai_recipes)
            ps.routes.get(f'{prefix}/locales')(_ez_civitai_locales)
            ps.routes.post(f'{prefix}/locales')(_ez_civitai_locales)
    except Exception:
        pass
