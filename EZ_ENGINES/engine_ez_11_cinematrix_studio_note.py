# -*- coding: utf-8 -*-
"""
===============================================================================
📦 MODULE      : engine_ez_11_cinematrix_studio_note.py
🏛️ ARCHITECTURE: EZ Cinematrix Core — Localized Studio Note, How-To & Model Guide
⚡ LANGUAGES   : EN, SV, ZH, JA, ES, DE, FR
===============================================================================
"""

from pathlib import Path
import re
from typing import Dict, Any, Tuple
from .engine_ez_locales import load_project_locales_payload

NOTE_TOPIC_PRESETS = [
    "All Guides & Model Tips (Complete Studio Handbook [01]➔[14])",
    "1. How-To, 1-Click Auto-Wire & Wiring Guide ([01] ➔ [14])",
    "2. Suno [12], Speech Recognition (Whisper ASR), Auto-Prompt & Duration Sync",
    "3. Model, PRISM SVD, Dialect Normalizer & LoRA Tips (Krea 2, Pony, Illustrious, MiniMax H3)",
    "4. Upscale, Edge-Directed Lanczos, 4x➔2x Supersampling, 1x Skin & RIFE IFNet",
    "5. Dynamic VLM Token Scaling (360s/72 Shots), 3D Latent Hysteresis & 3-Axis Director",
    "6. EZ [13] Omni-Reference 5-Slot Studio (Slots [1]–[4] Character + Slot [5] Video Scene) & Switchboard [14]",
    "7. Basics — Beginner's Guide (ComfyUI, Models, LoRA/DoRA, PRISM Foundry & Resources)",
    "8. PRISM Merge Recipes (01–09), 7 EZ [05] LoRA Combos & Local-Priority Shield ([03]/[05]/[10])",
    "9. Custom Studio Notes Only (Custom Markdown)",
    "10. Version & Patch Changelog ([Major].[Minor].[Hotfix]-[Environment])",
]

NOTE_LOCALE_CHOICES = [
    "Auto (Follow Active UI Locale)",
    "EN — English",
    "SV — Svenska",
    "ZH — 中文 (简体)",
    "JA — 日本語",
    "ES — Español",
    "DE — Deutsch",
    "FR — Français",
]
NOTE_LOCALE_PRESETS = NOTE_LOCALE_CHOICES

STUDIO_GUIDE_CHAPTERS: Dict[str, Dict[str, str]] = {
    "SV": {
        "howto": (
            "### 🗺️ 1. HOW-TO, 1-KLICKS AUTO-WIRE, ÖPPEN PROMPT-INSPEKTION & KOPPLINGSGUIDE (`[01]` ➔ `[14]`)\n"
            "* **1-Klicks Auto-Wire (Alla Noder)**: Högerklicka på valfri EZ-nod och välj **`⚡ Auto-Skapa & Koppla hela EZ Cinematrix-flödet (1-Klick)`**. Kopplar automatiskt alla noder i exakt rätt ordning:\n"
            "  * **Buss-kedja (`cinematrix_bus`)**: `[09] Anatomy Dock ➔ [10] Civitai ➔ [11] Studio Note ➔ [12] Suno Studio ➔ [13] Omni-Reference ➔ [01] Canvas Ingest ➔ [02] Qwen3-VL ➔ [03] Image LoRA ➔ [04] Krea 2 Sampler ➔ [05] Video LoRA ➔ [06] Director ➔ [07] Joint AV Sampler ➔ [08] Cinema Vault` (+ `[14] Switchboard`).\n"
            "* **🔍 100 % Öppen Prompt-Inspektion (`krea2_image_prompt` & `h3_video_timeline_prompt` i `EZ [02]`)**:\n"
            "  * Både `krea2_image_prompt` och `h3_video_timeline_prompt` på **`EZ [02]`** är 100 % öppna `STRING`-utgångar som kan kopplas direkt till valfri textnod (`ShowText`, `Preview Any` etc.) samt visas direkt i nodens egen **NEGATIVE PROMPT & TIMELINE OVERRIDE HUD**.\n"
            "* **📐 Viktigt om `base_width`/`base_height` vs `final_width`/`final_height` (`[01]` ➔ `[04]` & `[06]`)**:\n"
            "  * **`base_width` & `base_height` (från `[01]`)**: Kopplas **endast** till **`EZ [03]`** och **`EZ [04]`** (Steg 1 bas-sampling innan 1.5x/2x latent uppskalning). De ska **ALDRIG** kopplas till `EZ [06] Video Director`!\n"
            "  * **`final_width` & `final_height` (från `[01]`)**: Kopplas till `final_width`/`final_height` på **`EZ [04]`** OCH till **`video_width`/`video_height` på `EZ [06] Video Director`** så att videomotorn alltid matchar den färdiga keyframens fulla upplösning.\n"
            "* **Hur `EZ [13] Omni-Reference` kopplas in**:\n"
            "  * **In i `[13]`**: Koppla `cinematrix_bus` från **`[12] Suno`** (eller `[11]` / `[10]`) in i `cinematrix_bus` på **`[13]`**.\n"
            "  * **Ut ur `[13]` (till `[01] Canvas Ingest`)**: Koppla `cinematrix_bus ➔ [01] cinematrix_bus`, samt `master_composite_image ➔ optional_image`, `person_reactor_image ➔ ref_image_2_person`, `clothing_ootd_image ➔ ref_image_3_clothing` och `background_depth_image ➔ ref_image_4_background`.\n"
            "* **Master Duration-Synk (`[12]` / `[02]` ➔ `[06]`)**: `master_duration` i **`EZ [02]`** styr automatiskt **`EZ [06]`** via `cinematrix_bus`, och synkar med **`EZ [12] Suno Studio`** enligt valt `duration_sync_mode`.\n"
            "* **🛡️ Local-First LoRA-Skydd & Live Header-Status (`EZ [03]`, `EZ [05]` & `EZ [10]`, `remote_hub_mode = local_priority`)**:\n"
            "  * Dina lokala modell- och LoRA-val i **`EZ [03]`** och **`EZ [05]`** vinner nu **alltid per slot** som standard (`🛡️ LOKALA VAL VINNER`). Kvarlämnade LoRAs i **`EZ [10]`** (`⚡ HUB SÄNDER` / `💤 HUB PASSIV`) kan aldrig längre skriva över aktiva slots i smyg via bussen; de fyller endast i `None`-platser om du inte själv slår om `remote_hub_mode` till `hub_override` (`⚠️ [10] OVERRIDE AKTIV`).\n"
            "* **Videospelare i `[08]` vs Live-MiniPyAV i `[07]`**: **`EZ [07]`** visar **endast MiniPyAV Live-Sampler-frames** under generering. **`EZ [08] Cinema Vault`** äger den färdiga **`🎬 SLUTPRODUKT // MASTER VIDEO PLAYER`** (nu med `-f ffmetadata` långprompt-skydd & förregistrerad PyAV AAC-ljudström)."
        ),
        "suno": (
            "### 🎵 2. `EZ [12]` SUNO MUSIC VIDEO, TALIGENKÄNNING (`WHISPER ASR`), AUTO-PROMPT & LÄNGD-SYNK\n"
            "* **🔗 Suno-Länk (`suno.com/s/...` / `suno.com/song/...`) & Lokal Ljudfil**:\n"
            "  * Klistra bara in din Suno-länk eller UUID i `suno_song_url_or_id`. **`EZ [12]`** hämtar automatiskt **48 kHz Stereo Master-ljudet** (stödjer både Suno v3/v4 `.mp3` och Suno v4.5/v5/v5.5 `chirp-fenix` `.mp4` AAC-strömmar), låttitel, genre-taggar, BPM och hela låttexten utan copy-paste.\n"
            "* **🗣️ Taligenkänning (Whisper ASR) & Akustisk Röst-/Genre-Analys**:\n"
            "  * **`EZ [12]`** kör lokal Whisper-taligenkänning (`faster_whisper` / `openai-whisper` / `transformers` i `ComfyUI/models/whisper`) + spektral grundtonsanalys ($F_0$ manlig baryton/tenor eller kvinnlig röst, taltempo & percussivitet).\n"
            "  * Klassificerar automatiskt ljudet som **`SPOKEN_WORD`** (prat/intervju/podcast/kändistal), **`VOCAL_SONG`** (sång) eller **`INSTRUMENTAL_MUSIC`**.\n"
            "* **✨ Automatisk Bild- & Videoprompt direkt från Ljudet (`[12]` ➔ `[02]`)**:\n"
            "  * **Lämna `user_input` tom i `EZ [02] Qwen3-VL`!** Då använder `[02]` automatiskt `auto_scene_prompt` och de transkriberade orden/sångtexten från `[12]` för att skapa en matchande Krea 2-keyframe och MiniMax H3-videotidslinje (och respekterar alltid valt `style_target` och referensbilder från `[13]`/`[01]`).\n"
            "* **⏱️ Kort Klipp vs Hela Låten (`duration_sync_mode` i `[12]`)**:\n"
            "  * `Sync Audio Slice to Timeline [02] / Director [06] (Short Clip)` *(Standard)*: Gör ett kortare klipp (t.ex. `5s`–`20s` styrt av `[02]`) och klipper ut rätt del av låten från `start_offset_sec`.\n"
            "  * `Custom Slice Duration in [12] (Start Offset + Seconds)`: Styr klippets exakta längd (`custom_duration_sec`) och starttid (`start_offset_sec`) direkt i `[12]`.\n"
            "  * `Match Full Audio Track Length (Full-Length Music Video)`: Låser `[02]` och `[06]` till hela låtens fulla längd (upp till `360s` / `72 shots`)."
        ),
        "models": (
            "### 🧬 3. PRISM ORTOGONAL SVD, DIALEKT-SANITIZER, TURBO-SHIELD & MINIMAX H3 (`FL2VA` VS `REF2VA`) (`[02]`–`[10]`)\n"
            "* **🧹 Automatisk Krea 2 Prose-Sanitizer & Pony/Illustrious Parentes-Normaliserare (`EZ [02]` & `EZ [03]`)**:\n"
            "  * **I `EZ [02]` & `EZ [03]` för `Krea 2 / Flux`**: Tar automatiskt bort SDXL/Pony-viktklamrar `(tag:1.25) ➔ tag`, eliminerar skenande bisatser (`which is... that is...`) och omvandlar kommasallad till naturlig kameraprosa så att T5/Qwen-textkodaren aldrig tappar semantisk skärpa.\n"
            "  * **I `EZ [03]` för `Pony V6 XL` & `Illustrious XL`**: Bevarar äkta viktuttryck `(tag:1.2)` men skyddar oviktade parenteser `(medium) ➔ \\(medium\\)` så att CLIP-L/G inte feltolkar dem som viktmodifierare.\n"
            "* **💎 PRISM Spektral SVD-Ortogonalisering & Turbo-Shield (`EZ [03]`, `EZ [05]` & `EZ [10]`)**:\n"
            "  * **1) PRISM Multi-LoRA Subspace Orthogonalization (`[03]` & `[05]`)**: När du kombinerar `Slot 1` (Karaktär/Anatomi/NSFW) med `Slot 2..3` (Stil/Ljussättning/Rörelse), projiceras `Slot 2..3` automatiskt **ortogonalt bort** från `Slot 1`:s primära singulära vektorer ($U_1, V_1$ via Reduced QR + Core $r \\times r$ SVD). Det förhindrar att stil- eller rörelse-LoRAs skriver över ansikte, ögon eller intima anatomiska detaljer!\n"
            "  * **2) PRISM Stage-2 & Video Turbo-Shield (`[03]` & `[05]`)**:\n"
            "    * I **`EZ [03]`** projiceras `IMG_krea2_raw_to_turbo_lora` (`0.90` i `stage2_model`) ortogonalt bort från `style_lora_1..3` så att Steg 2-poleringen aldrig tvättar bort hudporer eller NSFW-mikroanatomi.\n"
            "    * I **`EZ [05]`** projiceras `VID_minimax_h3_turbo_v4_step600_pruned_comfyui` (`1.00`) ortogonalt bort från `video_lora_1..3` (på både `FL2VA` och `Ref2VA`) så att en `0.25` detalj-/anatomi-LoRA behåller 100 % styrka utan att dränkas av Turbo-LoRAn.\n"
            "  * **3) PRISM Multi-LoRA Stack Scaling (`EZ [10]`)**: Justerar automatiskt sammanlagd LoRA-energi (`88 %` vid 2 LoRAs, `78 %` vid 3 LoRAs) för att förhindra latent-mättnad.\n"
            "* **🖼️ Kurerade Krea 2 Bildmodeller för `EZ [03]` & `EZ [04]` (16 GB RTX 40/50 Blackwell — med `EZ-03-TURBO-GUARD`)**:\n"
            "  * **🛡️ Automatiskt Dubbel-Turbo-Skydd (`EZ-03-TURBO-GUARD` + `EZ-04-TURBO-GUARD`)**: Om du väljer en Krea 2-modell med **inbakad Turbo** (`*Turbo*`, `NVFP4Turbo`, `Dasiwa...V2Turbo`) kopplar `EZ [03]` automatiskt ur extern Stage-2 Turbo-LoRA (`0.00`), låser `sampling_mode = turbo_fixed` och `EZ [04]` sänker automatiskt `CFG ➔ 1.0` (`max 8 steg`) så du aldrig bränner kontrasten!\n"
            "  * **🏆 RAW-Modeller (EJ inbakad Turbo — körs i `raw_dynamic` MED Stage-2 Turbo-LoRA `ON`, `CFG 3.5–4.5`)**:\n"
            "    * **#1 Ren Referensbas & LoRA-Kung (`~12.5 GB`)**: **`krea-2-raw-int8-convrot.safetensors`** *(100 % neutral Hadamard ConvRot INT8 — maximal LoRA-träffsäkerhet)*.\n"
            "    * **#2 Bästa Filmiska Fotorealism, Hud & Porträtt (`~12.5 GB`)**: **`museByStableYogi_v35Int8Extended.safetensors`** *(ersätter äldre `realismByStableYogi_v30`)*. \n"
            "    * **#3 Bästa Uncensored / NSFW-Anatomi (`~12.5 GB`)**: **`snofsSexNudesAndOther_krea2RawV14_int8.safetensors`** *(ersätter äldre `V13D` och `lustify_v10Krea2`)*.\n"
            "  * **⚡ INBAKAD TURBO-Modeller (`EZ-03-TURBO-GUARD` låser automatiskt `turbo_fixed`, `CFG 1.0` & `4–8 steg`)**:\n"
            "    * **#4 Snabbaste RTX 50-Serie Blackwell-Raket (`~7 GB` äkta FP4!)**: **`museByStableYogi_v25NVFP4Turbo.safetensors`** *(halva VRAM-minnet i 5:e gen Tensor Cores)*.\n"
            "    * **#5 Snabb Karaktärs- & NSFW-Turbo (`~12.5 GB`)**: **`DasiwaKrea2TurboRaw_cutedisasterV2Turbo_full_int8.safetensors`** *(undvik okvantiserade `~24 GB` BF16-dubbletter och `INT8+INT4+FP8`-blandkvantiseringar)*.\n"
            "* **🎨 Äkta Platt 2D Cel-Anime (`style_target = anime / cartoonish`) — Krea 2 vs Illustrious XL (`EZ [02]`–`[04]`)**:\n"
            "  * **1) 2D-Anime på Krea 2 (`EZ-03-ANIME-TURBO-BYPASS` + Negativ Anti-3D Slider)**:\n"
            "    * Välj **`krea-2-raw-int8-convrot.safetensors`** i `EZ [03]` (`EZ [03]` kopplar automatiskt ur fotorealistiska `krea2_raw_to_turbo` vid `anime`/`cartoonish` och mutar positiva 3D/realism-LoRAs!).\n"
            "    * **Negativ Anti-3D Slider (Valfri Boost)**: Sätt `real_3d_krea2_loraholic` eller `snofs_photoSlider` på **`-0.35`** i `style_lora_2` — negativa vikter (`< 0`) bevaras 100 % och drar aktivt bort 3D-skuggning!\n"
            "    * I **`EZ [04]`**: Sätt `i2i_denoise = 0.78 – 0.85` och `enable_frequency_polish = false`. 3D-referensbilder plattas nu automatiskt till diskreta 2-tons cel-ytor + mörka 2D-bläcklinjer innan VAE-encode.\n"
            "    * **2) Plug-and-Play Multi-Arkitektur Autopilot för Illustrious XL, Pony V6 XL, SDXL 1.0, Flux.1 & Qwen-Image i `EZ [03]`, `EZ [04]` & `EZ [10]` (`EZ-04-MULTIARCH-AUTO`)**:\n"
            "      * **Krea 2 förblir vår #1 Huvudmodell** (med 3-stegs Raw➔Turbo➔Polish), men nybörjare kan nu välja valfri **Illustrious XL**, **Pony**, **SDXL 1.0** eller **Flux.1 Dev/Schnell** direkt i `unet_name` i **`EZ [03]`** (eller via **`EZ [10]`**, som även stödjer Civitai-länkar, `#ModelID` som `#827184` för `WAI-illustrious-SDXL v17` och filnamns-alias som `waiNSFWIllustrious` / `CyberRealistic Pony`)!\n"
            "      * **100 % Självläkande i `EZ [03]` & `EZ [04]`**: `EZ [03]` auto-detekterar arkitekturen, laddar rätt CLIP (`Dual CLIP-L/G` + `CLIP Skip -2` på Pony/Illustrious; `Dual CLIP-L + T5-XXL` på Flux; `Qwen3-VL 4B` på Krea 2) och rätt VAE (`4ch SDXL-VAE` / `16ch ae.safetensors` / `qwen_image_vae`), samt filtrerar bort inkompatibla LoRAs. `EZ [04]` stänger automatiskt av Steg 2 (`stage2_steps = 0`, `handoff_percent = 100 %`), skalar ner `>1.35 MP` till optimala `~1.1 MP` på 4ch-modeller och sätter rätt Single-Stage-parametrar (**Illustrious: `28 steg, CFG 4.5, euler_ancestral/karras`** mot neonbränning | **Pony: `28 steg, CFG 5.5, euler_ancestral/karras`** | **SDXL: `28 steg, CFG 5.0, dpmpp_2m_sde/karras`** | **DMD2: `8 steg, CFG 1.2`** | **Flux Dev: `24 steg, CFG 1.0, euler/simple`**, **Schnell: `4 steg`**).\n"
            "  * **3) Dubbla Dark-Fantasy-Profiler (`dark-fantasy-real` vs `dark-fantasy-cgi`) & `EZ-03-ANTI3D-GUARD`**:\n"
            "    * **`dark-fantasy-real`** *(Live-Action ARRI Alexa 65 Grimdark — The Witcher / Nosferatu)*: Anamorfisk `35mm f/1.8` Z-ledsbokeh, äkta hudporer (`0.92x` fotoreal-LoRA i `[03]`, `1.0x` i `[05]`), praktiska Weta-horn/svärtat stål och stenhårt förbud mot både `2d digital painting / book cover` och `3d cgi` (`:1.90`).\n"
            "    * **`dark-fantasy-cgi`** *(Diablo IV / Blur Studio Pre-Rendered 3D Cutscene)*: Offline path-traced 3D-VFX, skulpterade demonhorn/graverad gotisk rustning, volumetrisk dimma/glöd (`0.65x` mikrotextur i `[03]` & `[05]`) och stenhårt förbud mot platt 2D-bokomslagskonst (`:1.88`) utan att strypa 3D-CGI.\n"
            "    * **`EZ-03-ANTI3D-GUARD`**: Om en negativ Anti-3D-slider (t.ex. `-0.35` från `anime`) lämnas kvar i `[03]` när du växlar till `dark-fantasy-real`, `dark-fantasy-cgi` eller `realism`, kopplas den automatiskt ur så 3D-djupet bevaras.\n"
            "* **🎯 Vilken MiniMax H3-modell ska jag välja: `FL2VA` (`produktionsläge = I2VA`) eller `REF2VA` (`produktionsläge = REF2VA`)?**\n"
            "  * **0 MB Extra VRAM (Smart Lazy-Loading i `[05]`)**: Du kan tryggt ha **båda** slottarna ifyllda i **`EZ [05]`** (`video_unet_name` + `video_unet_ref2va`). Motorn läser `produktionsläge` från **`EZ [06]`** och laddar **endast** den aktiva modellen i VRAM (`0 MB VRAM` för den inaktiva slotten).\n"
            "  * **🥇 Val 1 (Standard — 90 % av alla scener): `produktionsläge = I2VA` (`video_unet_name` = `FL2VA` / `Singularity` / `Hybrid`)**: Låser din Krea 2-keyframe från `[04]` som exakt bildruta 0 (`start_image`) + injicerar **`allan_ballan` Multi-Zon Anatomi-Atlas** i `Qwen3-VL 32B`.\n"
            "  * **🥈 Val 2 (Friare kamera / Karaktärs-LoRA-läge): `produktionsläge = REF2VA` (`video_unet_ref2va` = `Ref2VA`)**: Matar automatiskt in **`<Picture 1>`** (Helbild), **`<Picture 2>`** (Ansikte/Hår/Ögon) och **`<Picture 3>`** (Torso/Byst/Bäcken) som permanenta identitets-tokens i varje videorutas DiT Self-Attention.\n"
            "* **📦 Officiellt HuggingFace-Arkiv & Bästa Modeller, VAE, CLIP & LoRAs för `EZ [05]` (16 GB+ RTX 40/50)**:\n"
            "  * **🔗 HuggingFace Basrepo (UNets & VAEs)**: `https://huggingface.co/DeepBeepMeep/MiniMax-H3/tree/main`\n"
            "  * **🔗 HuggingFace LoRA-Arkiv (`loras/`)**: `https://huggingface.co/DeepBeepMeep/MiniMax-H3/tree/main/loras`\n"
            "  * **🏛️ Bästa Video-UNets (`ComfyUI/models/diffusion_models/H3/`)**:\n"
            "    * **#1 Realism/NSFW (Inbakad Turbo — ha extern Turbo-LoRA `OFF`)**: `10Eros_Max_SingularityV2_PRISM2_PikaFlex_0.85_int8HQ.safetensors` *(eller `1.00_int8HQ` för maximal rörelsefrihet)*.\n"
            "    * **#2 100 % VRAM-Resident Blackwell-Raket (`13.8 GB`, Inbakad 8-Stegs QAD Turbo — ha extern Turbo-LoRA `OFF`)**: `FastH3-Omni-NVFP4-QAD-pruned_rank8_nvfp4.safetensors` *(klarar både `I2VA` & `REF2VA` med 0 MB PCIe-swap på 16 GB VRAM)*.\n"
            "    * **#3 Ren Non-Turbo Basmodell (Körs MED extern Turbo-LoRA `ON`)**: `h3ErosMax_beta5_3185154.safetensors` eller `MiniMax-H3-FL2VA-pruned_int8_convrot.safetensors` (`22.1 GB`).\n"
            "    * **#4 Bästa `REF2VA`-Modeller (`video_unet_ref2va`)**: `dasiwa_minimax_h3_ref2va_v5xs_pruned_graviton_int8_row-wise_convrot_runtime_mixed.safetensors`, `10erosMaxInt8Ref2va_v11.safetensors` eller `Minimax-h3_Singularity_ref2va_v2_pruned_int8_convrot.safetensors` (`21 GB`).\n"
            "  * **🧩 Bästa Companion-Modeller (`CLIP`, `Video-VAE` & `Audio-VAE` i `EZ [05]`)**:\n"
            "    * **`video_clip_name` (`models/text_encoders/H3/`, `clip_type = minimax`)**: **`qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors`** — *#1 Guldstandard (32B 5120-dim AWQ/NVFP4 Text Encoder, hårdvaruaccelererad i RTX 50-seriens Tensor Cores)*.\n"
            "    * **`video_vae_name` (`models/vae/H3/`)**: **`MiniMax-H3-video_vae_fp16.safetensors` (`5.21 GB`)** *(eller `minimax_h3_video_vae_bf16.safetensors`)* — *#1 Måste-val! Ren 16-bitars 3D Video-VAE som eliminerar 8-bitars (`int8_convrot`) avrundnings-, kontrast- och bakgrundsdrift vid flerfönster `decode ➔ encode`* *(Lättviktsreserv: `minimax_h3_video_vae_fp8mix.safetensors` `2.79 GB`).*\n"
            "    * **`audio_vae_name` (`models/vae/H3/`)**: **`MiniMax-H3-audio_vae_fp32.safetensors` (`605 MB`)** — *#1 Guldstandard i full FP32 för kristallren 32 kHz sång, läppsynk & SFX utan fasbrus.*\n"
            "  * **⚡ Bästa Video-LoRAs (`ComfyUI/models/loras/H3/`)**:\n"
            "    * **#1 Ny Bästa Turbo-LoRA (Endast på Non-Turbo UNets, `8–10 steg`, `CFG 1.0–1.2`)**: **`minimax_h3_dmad_8step_full_critic_lora_bf16.safetensors` (`1.38 GB`)** — *Adversarial Full-Critic-destillering som utklassar äldre `step600` och `lightx2v` i dansrörelse, läppsynk och naturlig hudkontrast* *(Alternativ 6-stegs: `pika_h3_flex_fl2va_6step_v1_bf16.safetensors` `1.38 GB`).*\n"
            "    * **#2 Skärpa & Mikrodetalj-LoRA (Fungerar på ALLA modeller inkl. PikaFlex/10Eros!)**: **`minimax_h3_lms_v1.0_r64.safetensors` (`1.24 GB`, LMS-Sharp v1.0 Rank 64)** — *Kör i `video_lora_1`/`2` på `0.20 – 0.30` styrka för knivskarpa ögon, glasögon, porer och rumstexturer.*\n"
            "    * **#3 Rörelse & Reasoning**: `H3_VBVR_Pro_attn_only.safetensors` (`0.35 – 0.45` styrka; kumulativ LoRA-energi hålls automatiskt `≤ 0.85` av `EZ [05]`).\n"
            "    * **🚫 Undvik i repot (på 16 GB VRAM)**: `40–66 GB *_bf16` UNets (PCIe-flaskhals), `*_heads_bf16.safetensors` (`44 MB`, endast för WanGP), `MiniMax-H3-Image-*` (använd Krea 2 i `[03]/[04]`) samt `pdmd_2nfe` (2-stegs)."
        ),
        "upscale": (
            "### 🚀 4. KANTSTYRD LANCZOS + MULTI-SCALE DETAIL RESTORER, `4x➔2x SUPERSAMPLING`, `1x HUD` & `RIFE IFNet` (`[04]` & `[08]`)\n"
            "* **🔬 Steg 1 (Första Passet — 0 MB Extra VRAM): Kantstyrd Lanczos + Multi-Scale Unsharp/High-Pass Detail Restorer i `[04]` & `[08]`**:\n"
            "  * Återställer sub-pixel-mikrodetaljer ($\\sigma_1 = 0.85$ för porer/ögonfransar/slemhinnor och $\\sigma_2 = 2.1$ för anatomiska konturer/muskeldefinition) direkt under keyframe- och videouppskalning med automatisk anti-halo-klippning.\n"
            "* **✨ Steg 2 (Efter-Pass): `4x➔2x Supersampling` + `1x Hud-Detalj` + `100% KeypointRCNN` 6-Zons Anatomiskt Skydd (`[04]` & `[08]`)**:\n"
            "  * Delar upp bilden i ett **Lågfrekvent färglager** (`skin_blur_radius`) och ett **Högfrekvent mikrotexturlager** (`skin_texture_strength`), styrt **100 % av KeypointRCNN-skelettzoner** (`face`, `eyes`, `hands`, `torso`, `pelvic`, `feet`) så att fin hudstruktur och NSFW-detaljer aldrig suddas ut.\n"
            "* **🎞️ Äkta RIFE v4.7/v4.9 `IFNet` (`rife49.pth` / `rife47.pth`) + `raft_small` i `[08]`**:\n"
            "  * Laddar äkta PyTorch `IFNet`-arkitektur från `ComfyUI/models/rife` med automatisk fallback till `raft_small`.\n"
            "* **🏆 Bästa 3-Stegs Master-Kedja i `[08]`**:\n"
            "  * `upscale_model_name`: **`4x-ClearRealityV1.pth`** (`4x➔2x` till `1536x1024`) + `detailer_1x_model_name`: **`1x-ITF-SkinDiffDetail-Lite-v1.pth`** (`0.45` blend) + `enable_frequency_polish = true`."
        ),
        "tips": (
            "### 💡 5. DYNAMISK LÅNGFILMS-SKALNING (`360s` / `72 SHOTS` I `[02]`), 3D HYSTERES-PROJEKTION (`[07]`), KREA 2 (`[04]`) & 3-AXLAD REGISSÖR (`[06]`)\n"
            "* **📈 Dynamisk VLM Token- & Kontext-Skalning (`5s` ➔ `360s` / `72 Shots` i `EZ [02]`)**:\n"
            "  * `_compute_dynamic_vlm_token_budget` skalar automatiskt antalet tidslinjeskott upp till **`72 shots`** (för 4–6 minuters musikvideor/kortfilmer), höjer `effective_max_tokens` (`6144 ➔ 8192`) och `llama_cpp` `n_ctx` (`8192 ➔ 12288`) samt beräknar en exakt ordkvot per shot (`per_shot_words = ~38–68 ord/shot`) så att Qwen3-VL aldrig klipper av tidslinjen före `[END_PROMPT]`!\n"
            "* **⚡ GPU-Vektoriserad 3D Dubbeltröskel-Hysteres & 24-Kanals Ortogonal Residual Spike-Projektion (`EZ [07]`)**:\n"
            "  * I `_stabilize_3d_video_latent_outliers` identifieras latenta energiutbrott via 3D-hysteres (`seed_hi > 11.2`, `cand_lo > 6.5` med `F.max_pool3d` + `F.avg_pool3d` mjuk övertoning) och projiceras ortogonalt bort längs `_EZ_H3_24CH_SPIKE_AXIS`, vilket bevarar 92 % av omgivande hudporer och tygstruktur utan färgblixtar.\n"
            "* **🎛️ Finjustering av Krea 2 3-Stegs Sampler (`EZ [04]`): `handoff_percent`, `stage3_handoff_percent` & `i2i_denoise` (Alla med `0.01`-steg)**:\n"
            "  * **`handoff_percent` (`55.00 – 65.00 %`)**, **`stage3_handoff_percent` (`88.00 – 92.00 %` — Anti-Ghosting & 5-Finger-Lås)** och **`i2i_denoise` (`0.70 – 0.78`)**.\n"
            "  * **🛡️ 100 % Nod-Auktoritet för `content_rating_mode` & `subject_1_age` i `EZ [02]` & `EZ [06]`** + **100 % Ras-, Genre- & Prompt-Neutral Kompilator** (inga hårdkodade varelser/vapen läcker in).\n"
            "* **🎬 Universell 3-Axlad Regissörsstyrning, Dynamisk Helkroppskoreografi & Förlustfri 24c Fönster-Handoff (`[02]`, `[06]`, `[07]` & `[08]`)**:\n"
            "  * Placerar alla huvudkaraktärer (`<Subject 1>`, `<Subject 2>`...) på samma främre kameraplan i knivskarp `35mm f/5.6` djupfokus, tillåter dynamisk vertikal koreografi (dans/knäböj/rörelse) vid låst kameraavstånd och förankrar varje 5s-fönster med förlustfri 24-kanals latent tail (`force_tail_replace=True`) samt fönsterspecifik Qwen3-VL `handoff_kf`-konditionering så att kläder och texturer aldrig skiftar mellan tidsfönster."
        ),
        "omniref": (
            "### 🖼️ 6. `EZ [13]` OMNI-REFERENCE 5-SLOT STUDIO (KARAKTÄRSREFERENS `[1]–[4]` + VIDEO-SCENMALL `[5]`) & `EZ [14]` SWITCHBOARD\n"
            "* **🎯 Smart Rollfördelning när BÅDE Bild (`Slot [1]`–`[4]`) och Referensvideo (`Slot [5]`) används tillsammans**:\n"
            "  * **1) Bild-slottarna (`Slot [1]`–`[4]`) = Huvudkaraktärens Identitet & Utseende (`<Subject 1>`)**:\n"
            "    * När en referensvideo är aktiv i `Slot [5]` extraherar `EZ [13]` ett **ansikts-/axlar-utsnitt (`slot1_character_ref_image`)** samt **exakt hudpigmentvektor (`slot1_skin_rgb = [R, G, B]`)** från `Slot [1]`. Stående kroppshållning, vapen och bakgrund från `Slot [1]` skärs bort så att de aldrig krockar med referensvideons scen.\n"
            "  * **2) Referensvideo (`Slot [5]`) = Scen-, Kamera-, Poserings-, Rörelse- & Ljudmall (`slot5_reference_video`)**:\n"
            "    * **Ingen filstorleksgräns (`.mp4`, `.mkv`, `.webm`, `.mov`, `.avi`, `.gif`, `.webp`)**: Läser via strömmande `PyAV`/`OpenCV` seek direkt till `slot5_start_offset_sec` och avkodar endast det valda tidsfönstret i RAM.\n"
            "    * **Scenmall för Krea 2 (`EZ [02]` & `EZ [04]`)**: Första bildrutan vid `slot5_start_offset_sec` blir **`master_composite_image`** och styr **100 % av scenens rumsliga layout, kameravinkel, Depth-Anything 3D och OpenPose 17J-skelett** (med `Slot [1]`-karaktärens hudton låst via **Skin Chromaticity Harmonizer** i `EZ [04]`).\n"
            "    * **Tidslängd i Sekunder (`slot5_duration_mode`)**: Välj **`follow_master_duration (Följ Master-Tidslängd [02] / [06] — Auto)`** *(Standard)*.\n"
            "* **🎛️ `EZ [14]` Cinematrix Pipeline Switchboard & Tier-Kopplat DevOps Värmeskydd (`Tier 1`–`Tier 4`)**:\n"
            "  * Styr hela kedjan i 0 MB VRAM via `pipeline_execution_mode` (`full_studio_image_and_video`, `image_only_krea2_studio`, `video_only_direct_i2v`) och övervakar GPU/CPU-värme via en **Time-Over-Threshold Värmemättnads-Integral**."
        ),
        "basics": (
            "### 🎓 7. BASICS — NYBÖRJARGUIDE TILL COMFYUI, MODELLTYPER, LORA/DORA, PRISM FOUNDRY & RESURSFILER\n"
            "* **🖥️ 1) ComfyUI Basics & Färgkodade Sladdar**:\n"
            "  * **Lila (`MODEL`)** = Basmodell (UNet/DiT), **Gul (`CLIP`)** = Texttolkare, **Orange (`CONDITIONING`)** = Positiv/negativ promptvektor, **Rosa (`LATENT`)** = Komprimerad bild i VRAM, **Röd (`VAE`)** = Avkodare till pixlar, **Blå (`IMAGE`)** = RGB-bild, **Grön (`MINIMAX_GUIDE` / `cinematrix_bus`)** = EZ Cinematrix master-kabel mellan `[01]`–`[14]`.\n"
            "* **🏛️ 2) Modelltyper (Checkpoints vs UNet/DiT)**:\n"
            "  * **Krea 2 (Flux/Qwen-DiT)**, **Flux.1 Dev/Schnell**, **SDXL 1.0**, **Pony Diffusion V6 XL (`clip_type = pony`)**, **Illustrious XL / NoobAI (`clip_type = illustrious`)** och **MiniMax H3 (`FL2VA` vs `Ref2VA`)**.\n"
            "* **🧩 3) LoRA, DoRA & PRISM Orthogonal SVD (`[03]`, `[05]` & `Model Foundry`)**:\n"
            "  * **LoRA (`Low-Rank Adaptation`) & DoRA (`Weight-Decomposed LoRA`)**: Skyddas av **PRISM Orthogonal SVD** och **Turbo-Shield**.\n"
            "  * **🏛️ EZ Model Foundry & LoRA Lab (i DevOps Studio — Station 3 `BF16` / `I64` Alpha / Zero-Up Kaiming Guard / Anti-3D)**: 5 stationer för dataset, LoRA/DoRA-träning, **Gold Epoch** via PRISM Effective Rank Entropy & Condition Number ($\\kappa = \\sigma_1 / \\sigma_k$), inbyggd **`BF16`/`FP16`/`FP32` + `I64` `.alpha` SafeTensors-läsning**, **Zero-`lora_up` Kaiming-brusspärr**, **automatisk rensning av ensidiga H3-ljudvikter på visuella merges**, **Multi-Rank (`r_a != r_b`) PRISM Orthogonal SVD Merge**, **Negativ Anti-3D Slider-Subtraktion (`-1.0 .. +1.0`)** samt **Cross-Architecture Guard (`ARCH_MISMATCH`)**."
        ),
        "prism_recipes": (
            "### 🧬 8. DE 9 PRISM MERGE-RECEPTEN (`ez_h3_01`–`09`), 7 LORA-KOMBOS I `EZ [05]` & GULDREGLER FÖR LJUD/RÖRELSE\n"
            "* **🛡️ 5 Kritiska Produktionsregler för `EZ [03]`, `EZ [05]` & `EZ [10]` (Läs alltid först!)**:\n"
            "  * **0) Local-Priority Skydd (`remote_hub_mode = local_priority` — `🛡️ LOKALA VAL VINNER`)**: Dina lokala modell- och LoRA-val i `EZ [03]` och `EZ [05]` vinner alltid per slot över `EZ [10] Civitai Hub` (`[10]` får endast fylla tomma `None`-slots om du inte manuellt väljer `hub_override`).\n"
            "  * **1) Rå Bas-UNet vs Inbakad PRISM/Turbo-UNet (`SingularityV2_PRISM2` / `FastH3`)**: På rå basmodell (`PinkCherry_v1.8`, `h3ErosMax_beta5`, `FL2VA-pruned`) kör du **full styrka** (`0.70–0.90` i Slot 1) + `ez_h3_06_dmad_pika_turbo_8step_v1` `ON` (`0.95–1.00`). På **inbakad PRISM/Turbo-UNet** (`10Eros_Max_SingularityV2_PRISM2_PikaFlex`) sänker du LoRA-styrkan med **~25–30 %** (`0.50–0.65` i Slot 1), håller `enable_video_turbo_lora = OFF` och kör `shift_video = 5.0`, `shift_audio = 3.0`, `8 steps`, `CFG 1.0`!\n"
            "  * **2) Ljudregeln (`lora_X_audio_strength = 0.00` på visuella LoRAs!)**: Sätt **alltid `Audio = 0.00`** på visuella/fysik/anatomi-merges (`ez_h3_01`–`04`, `07`–`09`, `LMS`, `breastplayjiggle`) — `EZ [05]` strippar då alla `audio_in`/`a_attn`/`a_block`-nycklar så 32 kHz FP32 Audio-VAE förblir 100 % fasren. Sätt `Audio = 0.75–1.00` **endast** på `ez_h3_05_sexgod_vocal_drive_v1`, `Audio\\moawxx_000002000` och `ez_h3_06` Turbo!\n"
            "  * **3) Mer kameradynamik & mindre stelhet i 30s-klipp**: Slå PÅ `allow_camera_movement = true` i `EZ [02]`, lägg `ez_h3_02_kinetic_combat_motion_v1` svagt (`0.25–0.35`) i Slot 2, eller växla `EZ [06]` från `I2VA` till **`REF2VA`** (`motion_transfer_strength = 0.80–0.85`) och sänk `lock_hands_and_fingers` (`0.95`) / `temporal_identity_rigidity` (`0.55`) i `EZ [09]`.\n"
            "  * **4) Slot 1 = Primary Anchor**: Lägg alltid din primära bas-merge i `video_lora_1` — `EZ [05]` projicerar Slot 2–4 ortogonalt bort från Slot 1!\n"
            "* **⚗️ De 9 Kirurgiska PRISM SVD Merge-Recepten (Model Foundry Station 3 — `PRISM_ORTHOGONAL_SVD`, `BF16`)**:\n"
            "  * **🎬 Recept 1 (`ez_h3_01_cinema_physics_core_v1` — SFW Film, Fysik & Skärpa)**: `A = Reasoning\\H3_VBVR_Pro_attn_only` + `B = Reasoning\\minimax_h3_lms_v1.0_r64` | `Anatomy: 0.85 | Style: 0.40 | Alpha: 0.60` ➔ Slot 1: `0.75–0.85` rå (`0.50–0.60` SingularityV2), `Audio: 0.00`.\n"
            "  * **⚡ Recept 2 (`ez_h3_02_kinetic_combat_motion_v1` — Action, Fight & Kamerapuls)**: `A = Motion\\H3_Combat_V2` + `B = Motion\\H3_Motion_BoosterV2` | `Anatomy: 0.80 | Style: 0.45 | Alpha: 0.60` ➔ Slot 2: `0.55–0.75` rå (`0.30–0.50` SingularityV2), `Audio: 0.00`.\n"
            "  * **🔥 Recept 3 (`ez_h3_03_mystic_skin_realism_v1` — Fotorealistisk Hud & NSFW Bas)**: `A = Theme\\MysticXXX_MMH3-V5` + `B = Theme\\HMNSFW-Extreme-Realism` | `Anatomy: 0.85 | Style: 0.40 | Alpha: 0.60` ➔ Slot 1: `0.75–0.90` rå (`0.55–0.65` SingularityV2), `Audio: 0.00`.\n"
            "  * **💎 Recept 4 (`ez_h3_04_intimate_anatomy_jiggle_v1` — Detaljanatomi + Mjukdelsfysik)**: `A = Features\\HMPussyV2` + `B = TnA\\breastplayjiggle_h3_v2` | `Anatomy: 0.80 | Style: 0.45 | Alpha: 0.60` ➔ Slot 2: `0.55–0.70` rå (`0.40–0.52` SingularityV2), `Audio: 0.00`.\n"
            "  * **🎙️ Recept 5 (`ez_h3_05_sexgod_vocal_drive_v1` — Intensitet + Joint-AV Röst/Andning)**: `A = Theme\\SexGod_NaughtyTimes_v3_rank64_unpruned` + `B = Audio\\moawxx_000002000` | `Anatomy: 0.80 | Style: 0.75 | Alpha: 0.60` ➔ Slot 3: `Video: 0.60 (0.45 SingularityV2)` | **`Audio: 0.85`**.\n"
            "  * **🚀 Recept 6 (`ez_h3_06_dmad_pika_turbo_8step_v1` — Hybrid 8-Step DMAD + PikaFlex Turbo)**: `A = Turbo\\minimax_h3_dmad_8step_full_critic_lora_bf16` + `B = Turbo\\pika_h3_flex_turbo_8step_fl2va_v1_bf16` | `Anatomy: 0.80 | Style: 0.35 | Alpha: 0.85` ➔ `video_turbo_lora_LOCKED`: `Video: 0.95–1.00 | Audio: 1.00` på råa UNets (`EZ-05-TURBO-GUARD` stänger av den automatiskt på SingularityV2!).\n"
            "  * **🎌 Recept 7 (`ez_h3_07_sakuga_anime_physics_v1` — SFW 2D Anime & Sakuga)**: `A = Reasoning\\H3_VBVR_Pro_attn_only` + `B = Motion\\H3_Motion_Booster_anime` | `Anatomy: 0.75 | Style: 0.55 | Alpha: 0.55` ➔ Slot 1: `0.75–0.90` rå (`0.55–0.68` SingularityV2), `Audio: 0.00`.\n"
            "  * **🌸 Recept 8 (`ez_h3_08_anime_nsfw_sakuga_v1` — 2D Hentai / Illustrious XL + Sakuga)**: `A = Theme\\NSFW_ANIME_H3_V16-step00002250` + `B = Motion\\H3_Motion_Booster_anime` | `Anatomy: 0.85 | Style: 0.45 | Alpha: 0.55` ➔ Slot 1: `0.80–0.95` rå (`0.60–0.70` SingularityV2), `Audio: 0.00`.\n"
            "  * **✨ Recept 9 (`ez_h3_09_glamour_uncensored_skin_v1` — R-Rated Glamour / Dark-Fantasy utan Hardcore-bias)**: `A = Features\\Minimax_H3_Unlocked_V3` + `B = Theme\\HMNSFW-Extreme-Realism` | `Anatomy: 0.80 | Style: 0.45 | Alpha: 0.55` ➔ Slot 1: `0.65–0.80` rå (`0.50–0.60` SingularityV2), `Audio: 0.00`.\n"
            "* **🎛️ Dina 7 Färdigkalibrerade LoRA-Kombos i `EZ [05]` (`Rå UNet` / `SingularityV2 PRISM`)**:\n"
            "  * **Kombo 1 (Hollywood SFW & Suno MV)**: Slot 1 `ez_h3_01` (`0.80` / `0.55`, `Audio: 0.00`) + valfri Slot 2 `ez_h3_02` (`0.30` / `0.25`, `Audio: 0.00`).\n"
            "  * **Kombo 2 (Blockbuster Action & Dans)**: Slot 1 `ez_h3_01` (`0.65` / `0.48`, `Audio: 0.00`) + Slot 2 `ez_h3_02` (`0.70` / `0.50`, `Audio: 0.00`).\n"
            "  * **Kombo 3 (R-Rated Glamour & Valkyrie Dark-Fantasy)**: Slot 1 `ez_h3_09` (`0.75` / `0.55`) + Slot 2 `ez_h3_01` el. `02` (`0.40` / `0.30`) + valfri Slot 3 `breastplayjiggle_h3_v2` (`0.40` / `0.30`), alla `Audio: 0.00`.\n"
            "  * **Kombo 4 (Flagship Adult Cinema — Par)**: Slot 1 `ez_h3_03` (`0.75` / `0.55`, `Audio: 0.00`) + Slot 2 `ez_h3_04` (`0.55` / `0.42`, `Audio: 0.00`) + Slot 3 `ez_h3_05` (`Video: 0.60/0.45`, **`Audio: 0.85`**) + valfri Slot 4 specialist (`0.50/0.38`).\n"
            "  * **Kombo 5 (NSFW Solo + 100 % Rent Röstspår)**: Slot 1 `ez_h3_03` (`0.75` / `0.55`) + Slot 2 `ez_h3_04` (`0.60` / `0.45`) + Slot 3 `hmmasturbation_v2` (`0.68` / `0.50`, `Audio: 0.00`) + Slot 4 `Audio\\moawxx_000002000` (**`Video: 0.00` | `Audio: 0.80`**).\n"
            "  * **Kombo 6 (2D Anime AMV & Sakuga)**: Slot 1 `ez_h3_07` (`0.85` / `0.62`, `Audio: 0.00`) + valfri Slot 2 `ez_h3_02` (`0.35` / `0.28`, `Audio: 0.00`), `enable_frequency_polish = false` i `[08]`.\n"
            "  * **Kombo 7 (2D Cel-Shaded NSFW / Illustrious XL)**: Slot 1 `ez_h3_08` (`0.85` / `0.65`) + Slot 2 `breastplayjiggle_h3_v2` (`0.45` / `0.35`) + Slot 3 aktions-LoRA (`0.55` / `0.42`) + Slot 4 `moawxx` (`Video: 0.00 | Audio: 0.75`)."
        ),
    },
    "EN": {
        "howto": (
            "### 🗺️ 1. HOW-TO, 1-CLICK AUTO-WIRE, OPEN PROMPT INSPECTION & WIRING GUIDE (`[01]` ➔ `[14]`)\n"
            "* **1-Click Auto-Wire (All Nodes)**: Right-click any EZ node and select **`⚡ Auto-Build & Wire Full EZ Cinematrix Pipeline (1-Click)`**. Automatically wires the complete studio chain:\n"
            "  * **Bus Chain (`cinematrix_bus`)**: `[09] Anatomy Dock ➔ [10] Civitai ➔ [11] Studio Note ➔ [12] Suno Studio ➔ [13] Omni-Reference ➔ [01] Canvas Ingest ➔ [02] Qwen3-VL ➔ [03] Image LoRA ➔ [04] Krea 2 Sampler ➔ [05] Video LoRA ➔ [06] Director ➔ [07] Joint AV Sampler ➔ [08] Cinema Vault` (+ `[14] Switchboard`).\n"
            "* **🔍 100% Open Prompt Inspection (`krea2_image_prompt` & `h3_video_timeline_prompt` on `EZ [02]`)**:\n"
            "  * Both `krea2_image_prompt` and `h3_video_timeline_prompt` on **`EZ [02]`** are 100% open `STRING` outputs ready to wire into any external text preview node (`ShowText`, `Preview Any`, etc.) and are simultaneously displayed live inside `[02]`'s built-in **NEGATIVE PROMPT & TIMELINE OVERRIDE HUD**.\n"
            "* **📐 Important: `base_width`/`base_height` vs `final_width`/`final_height` (`[01]` ➔ `[04]` & `[06]`)**:\n"
            "  * **`base_width` & `base_height` (from `[01]`)**: Wire **only** to **`EZ [03]`** and **`EZ [04]`** (Stage 1 base sampling before 1.5x/2x latent upscale). Never wire `base_width`/`base_height` into `EZ [06]`!\n"
            "  * **`final_width` & `final_height` (from `[01]`)**: Wire to `final_width`/`final_height` on **`EZ [04]`** AND to **`video_width`/`video_height` on `EZ [06] Video Director`** so the video engine matches the full upscaled keyframe resolution.\n"
            "* **How to wire `EZ [13] Omni-Reference`**:\n"
            "  * **Into `[13]`**: Connect `cinematrix_bus` from **`[12] Suno`** (or `[11]` / `[10]`) into `cinematrix_bus` on **`[13]`**.\n"
            "  * **Out of `[13]` (into `[01] Canvas Ingest`)**: Connect `cinematrix_bus ➔ [01] cinematrix_bus`, plus `master_composite_image ➔ optional_image`, `person_reactor_image ➔ ref_image_2_person`, `clothing_ootd_image ➔ ref_image_3_clothing`, and `background_depth_image ➔ ref_image_4_background`.\n"
            "* **Master Duration Sync (`[12]` / `[02]` ➔ `[06]`)**: `master_duration` in **`EZ [02]`** is authoritative when `cinematrix_bus` is connected and syncs with **`EZ [12]`** according to `duration_sync_mode`.\n"
            "* **🛡️ Local-First LoRA Shield & Live Header Pills (`EZ [03]`, `EZ [05]` & `EZ [10]`, `remote_hub_mode = local_priority`)**:\n"
            "  * Selections made directly inside **`EZ [03]`** and **`EZ [05]`** now **always win per slot** by default (`🛡️ LOKALA VAL VINNER`). Leftover LoRAs in **`EZ [10]`** (`⚡ HUB SÄNDER` / `💤 HUB PASSIV`) can never silently overwrite active local slots via the bus, and only fill `None` slots unless `remote_hub_mode` is explicitly set to `hub_override`.\n"
            "* **Master Video Player in `[08]` vs Live MiniPyAV in `[07]`**: **`EZ [07]`** displays live MiniPyAV sampler frames, while **`EZ [08] Cinema Vault`** hosts the final **`🎬 MASTER VIDEO PLAYER`** (with `-f ffmetadata` long-prompt safety & pre-registered PyAV AAC stream)."
        ),
        "suno": (
            "### 🎵 2. `EZ [12]` SUNO MUSIC VIDEO, SPEECH RECOGNITION (`WHISPER ASR`), AUTO-PROMPT & DURATION SYNC\n"
            "* **🔗 Suno URL (`suno.com/s/...` / `suno.com/song/...`) & Local Audio Auto-Fetcher**:\n"
            "  * Paste any Suno shortlink, song URL, or UUID into `suno_song_url_or_id`. **`EZ [12]`** automatically fetches the **48 kHz Stereo Master Audio** (supporting both Suno v3/v4 `.mp3` and Suno v4.5/v5/v5.5 `chirp-fenix` `.mp4` AAC streams), title, genre tags, BPM, and full lyrics.\n"
            "* **🗣️ Local Whisper ASR Speech-to-Text & Acoustic Voice/Genre Classifier**:\n"
            "  * Transcribes spoken dialogue or vocals via local Whisper (`faster_whisper` / `openai-whisper` / `transformers` in `ComfyUI/models/whisper`) and analyzes fundamental pitch $F_0$ (baritone male, mid-tenor, emotive female voice).\n"
            "  * Classifies audio into **`SPOKEN_WORD`** (monologue/interview/celebrity speech), **`VOCAL_SONG`**, or **`INSTRUMENTAL_MUSIC`**.\n"
            "* **✨ Zero-Prompt Audio-to-Scene Generation (`[12]` ➔ `[02]`)**:\n"
            "  * **Leave `user_input` empty in `EZ [02] Qwen3-VL`!** `[02]` automatically uses `auto_scene_prompt` and transcribed speech/lyrics from `[12]` while preserving your `style_target` and reference images from `[13]`/`[01]`.\n"
            "* **⏱️ Short Clip vs Full Song (`duration_sync_mode` in `[12]`)**:\n"
            "  * `Sync Audio Slice to Timeline [02] / Director [06] (Short Clip)` *(Default)*: Render a short clip (`5s`–`20s`) sliced at `start_offset_sec`.\n"
            "  * `Custom Slice Duration in [12]`: Slice `custom_duration_sec` starting at `start_offset_sec`.\n"
            "  * `Match Full Audio Track Length`: Locks `[02]` and `[06]` to the full song duration (scaling up to `360s` / `72 shots`)."
        ),
        "models": (
            "### 🧬 3. PRISM ORTHOGONAL SVD, DIALECT SANITIZER, TURBO-SHIELD & MINIMAX H3 (`FL2VA` VS `REF2VA`) (`[02]`–`[10]`)\n"
            "* **🧹 Automatic Krea 2 Prose Sanitizer & Pony/Illustrious Parenthesis Normalizer (`EZ [02]` & `EZ [03]`)**:\n"
            "  * **In `EZ [02]` & `EZ [03]` for `Krea 2 / Flux`**: Automatically strips SDXL/Pony weight brackets `(tag:1.25) ➔ tag`, prunes runaway relative-pronoun chains (`which is... that is...`), and converts comma-tag salad into cohesive camera prose so the T5/Qwen text encoder never suffers attention dilution.\n"
            "  * **In `EZ [03]` for `Pony V6 XL` & `Illustrious XL`**: Preserves explicit weight syntax `(tag:1.2)` while escaping unweighted parentheses `(medium) ➔ \\(medium\\)` so Dual CLIP-L/G never misinterprets literal tags as weight modifiers.\n"
            "* **💎 PRISM Spectral SVD Orthogonalization & Turbo-Shield (`EZ [03]`, `EZ [05]` & `EZ [10]`)**:\n"
            "  * **1) PRISM Multi-LoRA Subspace Orthogonalization (`[03]` & `[05]`)**: When stacking `Slot 1` (Character/Anatomy/NSFW) with `Slot 2..3` (Style/Lighting/Motion), `Slot 2..3` are automatically projected **orthogonally away** from `Slot 1`'s principal singular vectors ($U_1, V_1$ via Reduced QR + Core $r \\times r$ SVD). Secondary LoRAs never overwrite facial identity or micro-anatomy!\n"
            "  * **2) PRISM Stage-2 & Video Turbo-Shield (`[03]` & `[05]`)**:\n"
            "    * In **`EZ [03]`**, `IMG_krea2_raw_to_turbo_lora` (`0.90` in `stage2_model`) is projected orthogonally away from `style_lora_1..3` so Stage 2 refinement never washes out skin pores or NSFW micro-anatomy.\n"
            "    * In **`EZ [05]`**, `VID_minimax_h3_turbo_v4_step600_pruned_comfyui` (`1.00`) is projected orthogonally away from `video_lora_1..3` (on both `FL2VA` and `Ref2VA`) so a `0.25` detail/anatomy LoRA retains 100% fidelity without being drowned out by the `1.00` Turbo LoRA.\n"
            "  * **3) PRISM Multi-LoRA Stack Scaling (`EZ [10]`)**: Automatically scales combined LoRA energy (`88%` for 2 LoRAs, `78%` for 3 LoRAs) to prevent latent saturation.\n"
            "* **🖼️ Curated Krea 2 Image Models for `EZ [03]` & `EZ [04]` (16 GB RTX 40/50 Blackwell — with `EZ-03-TURBO-GUARD`)**:\n"
            "  * **🛡️ Automatic Double-Turbo Protection (`EZ-03-TURBO-GUARD` + `EZ-04-TURBO-GUARD`)**: Selecting any **baked-in Turbo** Krea 2 checkpoint (`*Turbo*`, `NVFP4Turbo`, `Dasiwa...V2Turbo`) automatically detaches the external Stage-2 Turbo LoRA (`0.00`), locks `sampling_mode = turbo_fixed`, and clamps `EZ [04]` `CFG ➔ 1.0` (`max 8 steps`) to prevent contrast burn!\n"
            "  * **🏆 RAW Checkpoints (Non-Turbo — run in `raw_dynamic` WITH Stage-2 Turbo LoRA `ON`, `CFG 3.5–4.5`)**:\n"
            "    * **#1 Pure Reference Base & Heavy LoRA Stacks (`~12.5 GB`)**: **`krea-2-raw-int8-convrot.safetensors`** *(Hadamard ConvRot INT8 — zero merge bias)*.\n"
            "    * **#2 Best Cinematic Photorealism, Skin & Portraits (`~12.5 GB`)**: **`museByStableYogi_v35Int8Extended.safetensors`** *(supersedes `realismByStableYogi_v30`)*.\n"
            "    * **#3 Best Uncensored / NSFW Anatomy (`~12.5 GB`)**: **`snofsSexNudesAndOther_krea2RawV14_int8.safetensors`** *(supersedes `V13D` & `lustify_v10Krea2`)*.\n"
            "  * **⚡ BAKED-TURBO Checkpoints (`EZ-03-TURBO-GUARD` auto-locks `turbo_fixed`, `CFG 1.0` & `4–8 steps`)**:\n"
            "    * **#4 Fastest RTX 50-Series Blackwell Specialist (`~7 GB` native FP4!)**: **`museByStableYogi_v25NVFP4Turbo.safetensors`** *(5th-gen FP4 Tensor Core acceleration)*.\n"
            "    * **#5 Fast Character & NSFW Turbo (`~12.5 GB`)**: **`DasiwaKrea2TurboRaw_cutedisasterV2Turbo_full_int8.safetensors`** *(skip unquantized `~24 GB` BF16 duplicates and `INT8+INT4+FP8` mixed quants)*.\n"
            "* **🎨 True Flat 2D Cel-Anime (`style_target = anime / cartoonish`) — Krea 2 vs Illustrious XL (`EZ [02]`–`[04]`)**:\n"
            "  * **1) 2D Anime on Krea 2 (`EZ-03-ANIME-TURBO-BYPASS` + Negative Anti-3D Slider)**:\n"
            "    * Select **`krea-2-raw-int8-convrot.safetensors`** in `EZ [03]` (`EZ [03]` automatically bypasses photorealistic `krea2_raw_to_turbo` in `anime`/`cartoonish` and mutes positive 3D/realism LoRAs).\n"
            "    * **Negative Anti-3D Slider**: Set `real_3d_krea2_loraholic` or `snofs_photoSlider` to **`-0.35`** — negative weights (`< 0`) pass through intact to subtract 3D shading! Set `i2i_denoise = 0.78 – 0.85` and `enable_frequency_polish = false` in `EZ [04]`.\n"
            "  * **2) Plug-and-Play Multi-Architecture Autopilot for Illustrious XL, Pony V6 XL, SDXL 1.0, Flux.1 & Qwen-Image (`EZ-04-MULTIARCH-AUTO`)**:\n"
            "    * While **Krea 2 remains our #1 Flagship** (3-stage Raw➔Turbo➔Polish), selecting any **Illustrious XL**, **Pony**, **SDXL 1.0**, or **Flux.1 Dev/Schnell** model in **`EZ [03]`** (or via **`EZ [10]`**, supporting Civitai URLs, `#ModelID` like `#827184` for `WAI-illustrious-SDXL v17`, and filename aliases) automatically pairs the right CLIP (`CLIP Skip -2` Dual CLIP-L/G for Pony/Illustrious; Dual CLIP-L + T5-XXL for Flux) + VAE (`4ch SDXL` / `16ch ae.safetensors`), strips cross-arch LoRAs, clamps `>1.35 MP` 4ch latents to `~1.1 MP`, and switches `EZ [04]` to Single-Stage (`stage2_steps = 0`, `handoff_percent = 100%`: **Illustrious `CFG 4.5`**, **Pony `CFG 5.5`**, **SDXL `CFG 5.0`**, **DMD2 `CFG 1.2`**, **Flux `CFG 1.0`**).\n"
            "  * **3) Dual Dark-Fantasy Engines (`dark-fantasy-real` vs `dark-fantasy-cgi`) & `EZ-03-ANTI3D-GUARD`**:\n"
            "    * **`dark-fantasy-real`** *(Live-Action ARRI Alexa 65 Grimdark — The Witcher / Nosferatu)*: Anamorphic `35mm f/1.8` deep Z-axis bokeh, real biological pores (`0.92x` photoreal LoRAs in `[03]`, `1.0x` in `[05]`), practical Weta-grade horns/forged dark steel, banning both `2d digital painting / book cover` and `3d cgi` (`:1.90`).\n"
            "    * **`dark-fantasy-cgi`** *(Diablo IV / Blur Studio Pre-Rendered 3D Cutscene)*: Offline path-traced 3D VFX, sculpted demonic horns/engraved gothic armor, volumetric multi-plane fog/embers (`0.65x` micro-texture in `[03]` & `[05]`), banning flat 2D book-cover paintings (`:1.88`) while preserving full 3D VFX shaders.\n"
            "    * **`EZ-03-ANTI3D-GUARD`**: Automatically detaches any leftover negative Anti-3D slider (`-0.35`) when switching from `anime` to 3D/photoreal styles.\n"
            "* **🎯 Which MiniMax H3 model should I use: `FL2VA` (`production_mode = I2VA`) or `REF2VA` (`production_mode = REF2VA`)?**\n"
            "  * **0 MB Extra VRAM (Smart Lazy-Loading in `[05]`)**: Keep **both** slots populated in **`EZ [05]`** (`video_unet_name` + `video_unet_ref2va`). Only the active slot selected in **`EZ [06]`** is loaded into VRAM.\n"
            "  * **🥇 Choice 1 (Default — 90% of scenes): `production_mode = I2VA` (`video_unet_name` = `FL2VA` / `Singularity` / `Hybrid`)**: Locks Krea 2 keyframe from `[04]` as exact pixel frame 0 + injects the **`allan_ballan` Multi-Zone Anatomical Atlas** into `Qwen3-VL 32B`.\n"
            "  * **🥈 Choice 2 (Freer Camera / Character-LoRA Mode): `production_mode = REF2VA` (`video_unet_ref2va` = `Ref2VA`)**: Feeds **`<Picture 1>`** (Full Keyframe), **`<Picture 2>`** (Face/Eyes/Hair crop), and **`<Picture 3>`** (Torso/Bust/Pelvis crop) into DiT Self-Attention.\n"
            "* **📦 Curated HuggingFace Repository & Best Models, VAE, CLIP & LoRAs for `EZ [05]` (16 GB+ RTX 40/50)**:\n"
            "  * **🔗 HuggingFace Main Repo (UNets & VAEs)**: `https://huggingface.co/DeepBeepMeep/MiniMax-H3/tree/main`\n"
            "  * **🔗 HuggingFace LoRA Vault (`loras/`)**: `https://huggingface.co/DeepBeepMeep/MiniMax-H3/tree/main/loras`\n"
            "  * **🏛️ Recommended Video UNets (`ComfyUI/models/diffusion_models/H3/`)**:\n"
            "    * **#1 Realism/NSFW (Baked Turbo — keep external Turbo LoRA `OFF`)**: `10Eros_Max_SingularityV2_PRISM2_PikaFlex_0.85_int8HQ.safetensors` *(or `1.00_int8HQ` for maximum motion amplitude)*.\n"
            "    * **#2 100% VRAM-Resident Blackwell Rocket (`13.8 GB`, Baked 8-Step QAD Turbo — keep external Turbo LoRA `OFF`)**: `FastH3-Omni-NVFP4-QAD-pruned_rank8_nvfp4.safetensors` *(supports both `I2VA` & `REF2VA` with 0 MB PCIe swap on 16 GB GPUs)*.\n"
            "    * **#3 Pure Non-Turbo Base UNet (Run WITH external Turbo LoRA `ON`)**: `h3ErosMax_beta5_3185154.safetensors` or `MiniMax-H3-FL2VA-pruned_int8_convrot.safetensors` (`22.1 GB`).\n"
            "    * **#4 Best `REF2VA` Models (`video_unet_ref2va`)**: `dasiwa_minimax_h3_ref2va_v5xs_pruned_graviton_int8_row-wise_convrot_runtime_mixed.safetensors`, `10erosMaxInt8Ref2va_v11.safetensors`, or `Minimax-h3_Singularity_ref2va_v2_pruned_int8_convrot.safetensors` (`21 GB`).\n"
            "  * **🧩 Mandatory Companion Stack (`CLIP`, `Video-VAE` & `Audio-VAE` in `EZ [05]`)**:\n"
            "    * **`video_clip_name` (`models/text_encoders/H3/`, `clip_type = minimax`)**: **`qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors`** — *#1 Gold Standard (32B 5120-dim AWQ/NVFP4 Text Encoder, hardware-accelerated on RTX 50-series Tensor Cores)*.\n"
            "    * **`video_vae_name` (`models/vae/H3/`)**: **`MiniMax-H3-video_vae_fp16.safetensors` (`5.21 GB`)** *(or `minimax_h3_video_vae_bf16.safetensors`)* — *#1 Must-Have! Pure 16-bit 3D Video VAE that eliminates 8-bit (`int8_convrot`) rounding, contrast, and background drift across multi-window `decode ➔ encode` handoffs* *(Lightweight backup: `minimax_h3_video_vae_fp8mix.safetensors` `2.79 GB`).*\n"
            "    * **`audio_vae_name` (`models/vae/H3/`)**: **`MiniMax-H3-audio_vae_fp32.safetensors` (`605 MB`)** — *#1 Gold Standard in full FP32 for phase-pure 32 kHz vocals, lip-sync & foley.*\n"
            "  * **⚡ Top Video LoRAs (`ComfyUI/models/loras/H3/`)**:\n"
            "    * **#1 Best Step-Distilled Turbo LoRA (Non-Turbo UNets ONLY, `8–10 steps`, `CFG 1.0–1.2`)**: **`minimax_h3_dmad_8step_full_critic_lora_bf16.safetensors` (`1.38 GB`)** — *Adversarial Full-Critic distillation outperforming legacy `step600` and `lightx2v` in choreography amplitude, lip-sync, and natural skin contrast* *(6-step option: `pika_h3_flex_fl2va_6step_v1_bf16.safetensors` `1.38 GB`).*\n"
            "    * **#2 Micro-Detail & Sharpness Booster (Safe on ALL UNets incl. PikaFlex/10Eros!)**: **`minimax_h3_lms_v1.0_r64.safetensors` (`1.24 GB`, LMS-Sharp v1.0 Rank 64)** — *Use in `video_lora_1`/`2` at `0.20 – 0.30` strength for crisp eyes, glasses, skin pores, and room textures.*\n"
            "    * **#3 Motion & Reasoning**: `H3_VBVR_Pro_attn_only.safetensors` (`0.35 – 0.45` strength; cumulative LoRA budget auto-guarded `≤ 0.85` by `EZ [05]`).\n"
            "    * **🚫 Skip on 16 GB VRAM**: `40–66 GB *_bf16` UNets, `*_heads_bf16.safetensors` (`44 MB`, WanGP-only), `MiniMax-H3-Image-*` (use Krea 2 in `[03]/[04]`), and `pdmd_2nfe` (2-step)."
        ),
        "upscale": (
            "### 🚀 4. EDGE-DIRECTED LANCZOS + MULTI-SCALE DETAIL RESTORER, `4x➔2x SUPERSAMPLING`, `1x SKIN` & `RIFE IFNet` (`[04]` & `[08]`)\n"
            "* **🔬 Pass 1 (Zero Extra VRAM): Edge-Directed Lanczos + Multi-Scale Unsharp/High-Pass Detail Restorer in `[04]` & `[08]`**:\n"
            "  * Restores sub-pixel micro-details ($\\sigma_1 = 0.85$ for pores/eyelashes/mucosal micro-texture and $\\sigma_2 = 2.1$ for anatomical contours/muscle definition) during keyframe and video upscaling with anti-halo clipping.\n"
            "* **✨ Pass 2 (Post-Process): `4x➔2x Supersampling` + `1x Skin Detailer` + `100% KeypointRCNN` 6-Zone Anatomical Shield (`[04]` & `[08]`)**:\n"
            "  * Tracks up to **12 subjects simultaneously** (`face`, `eyes`, `hands`, `torso`, `pelvic`, `feet`) with reinforced `contour_shield` so skin, crowd characters, and NSFW group micro-textures are preserved without plastic smoothing or limb merging.\n"
            "* **🎞️ Native RIFE v4.7/v4.9 `IFNet` (`rife49.pth` / `rife47.pth`) + `raft_small`**: Loads genuine PyTorch `IFNet` weights from `ComfyUI/models/rife`.\n"
            "* **🏆 Best 3-Stage Master Chain in `[08]`**: **`4x-ClearRealityV1.pth`** (`4x➔2x`) + **`1x-ITF-SkinDiffDetail-Lite-v1.pth`** (`0.45` blend) + `enable_frequency_polish = true`."
        ),
        "tips": (
            "### 💡 5. DYNAMIC LONG-FORM VLM SCALING (`360s` / `72 SHOTS` IN `[02]`), 3D LATENT HYSTERESIS (`[07]`), KREA 2 (`[04]`) & 3-AXIS DIRECTOR (`[06]`)\n"
            "* **📈 Dynamic Long-Form VLM Token & Context Scaling (`5s` ➔ `360s` / `72 Shots` in `EZ [02]`)**:\n"
            "  * `_compute_dynamic_vlm_token_budget` dynamically scales timeline shots up to **`72 shots`** (supporting 4-to-6-minute full-length music videos and short films), elevates `effective_max_tokens` (`6144 ➔ 8192`) and `llama_cpp` `n_ctx` (`8192 ➔ 12288`), and enforces a uniform per-shot word quota (`per_shot_words = ~38–68 words/shot`) so Qwen3-VL never truncates multi-minute timelines before `[END_PROMPT]`.\n"
            "* **⚡ GPU-Vectorized 3D Dual-Threshold Hysteresis & 24-Channel Orthogonal Residual Spike Projection (`EZ [07]`)**:\n"
            "  * `_stabilize_3d_video_latent_outliers` detects connected 3D spatiotemporal energy anomalies via dual-threshold hysteresis (`seed_hi > 11.2`, `cand_lo > 6.5` using `F.max_pool3d` morphological dilation and `F.avg_pool3d` spatial feathering) and projects out only the corruptive 24-channel spike axis (`_EZ_H3_24CH_SPIKE_AXIS`) while preserving 92% of orthogonal high-frequency skin pore and fabric texture energy.\n"
            "* **🎛️ Krea 2 3-Stage Sampler Fine-Tuning (`EZ [04]`): `handoff_percent`, `stage3_handoff_percent` & `i2i_denoise` (All in `0.01` Steps)**:\n"
            "  * **`handoff_percent` (`55.00 – 65.00%`)**, **`stage3_handoff_percent` (`88.00 – 92.00%` — Anti-Ghosting & 5-Finger Lock)**, and **`i2i_denoise` (`0.70 – 0.78`)**.\n"
            "  * **🛡️ 100% Node Authority for `content_rating_mode` & `subject_1_age` in `EZ [02]` & `EZ [06]`** + **100% Species-, Genre- & Prompt-Neutral Compiler** (zero hardcoded creatures or garments injected unless prompted).\n"
            "* **🎬 Universal 3-Axis Director Controls, Dynamic Full-Body Choreography & Lossless 24c Window Handoff (`[02]`, `[06]`, `[07]` & `[08]`)**:\n"
            "  * Locks all foreground main characters (`<Subject 1>`, `<Subject 2>`...) onto the same foreground camera plane in razor-sharp `35mm f/5.6` deep focus, preserves dynamic vertical choreography (squatting/dancing/garment physics) at constant camera distance, and anchors each 5s continuation window with lossless 24-channel native latent tail (`force_tail_replace=True`) plus per-window Qwen3-VL `handoff_kf` conditioning so outfits and textures remain 100% consistent across all windows."
        ),
        "omniref": (
            "### 🖼️ 6. `EZ [13]` OMNI-REFERENCE 5-SLOT STUDIO (CHARACTER REF `[1]–[4]` + VIDEO SCENE TEMPLATE `[5]`) & `EZ [14]` SWITCHBOARD\n"
            "* **🎯 Architectural Role Split when BOTH Image (`Slot [1]`–`[4]`) and Reference Video (`Slot [5]`) are active**:\n"
            "  * **1) Image Slots (`Slot [1]`–`[4]`) = Main Character Identity & Appearance (`<Subject 1>`)**:\n"
            "    * When `Slot [5]` (Reference Video) is active, `EZ [13]` extracts a **head-and-shoulders character identity crop (`slot1_character_ref_image`)** and **exact skin pigment vector (`slot1_skin_rgb = [R, G, B]`)** from `Slot [1]`, excluding `Slot [1]`'s standing pose, weapons, and background.\n"
            "  * **2) Reference Video (`Slot [5]`) = Scene, Camera, Posture, Motion & Audio Template (`slot5_reference_video`)**:\n"
            "    * **No File-Size Cap (`.mp4`, `.mkv`, `.webm`, `.mov`, `.avi`, `.gif`, `.webp`)**: Streams directly to `slot5_start_offset_sec` via `PyAV`/`OpenCV` seek and decodes only the active time window into RAM.\n"
            "    * **Scene Template for Krea 2 (`EZ [02]` & `EZ [04]`)**: The video frame at `slot5_start_offset_sec` becomes **`master_composite_image`**, driving **100% of the spatial scene layout, camera angle, Depth-Anything 3D, and OpenPose 17J skeleton** (with `Slot [1]`'s skin chromaticity locked post-decode in `EZ [04]`).\n"
            "    * **Duration in Seconds (`slot5_duration_mode`)**: Select **`follow_master_duration`** *(Default)* to automatically match `master_duration` (`20s`–`360s`) from `EZ [02]`/`[12]`.\n"
            "* **🎛️ `EZ [14]` Cinematrix Pipeline Switchboard & Tier-Coupled DevOps Thermal Shield (`Tier 1`–`Tier 4`)**:\n"
            "  * Switch between `full_studio_image_and_video`, `image_only_krea2_studio`, `video_only_direct_i2v`, or individual node toggles with 0 MB wasted VRAM, protected by the **Time-Over-Threshold Thermal Soak Integral**."
        ),
        "basics": (
            "### 🎓 7. BASICS — BEGINNER'S GUIDE TO COMFYUI, MODEL TYPES, LORA/DORA, PRISM FOUNDRY & RESOURCE FILES\n"
            "* **🖥️ 1) ComfyUI Basics & Color-Coded Wires**:\n"
            "  * **Purple (`MODEL`)** = UNet/DiT brain, **Yellow (`CLIP`)** = Text Encoder, **Orange (`CONDITIONING`)** = Encoded prompt vectors, **Pink (`LATENT`)** = Compressed latent tensor, **Red (`VAE`)** = Latent-to-Pixel decoder, **Blue (`IMAGE`)** = RGB tensor, **Green (`MINIMAX_GUIDE` / `cinematrix_bus`)** = EZ Cinematrix master bus across `[01]`–`[14]`.\n"
            "* **🏛️ 2) Model Types**: **Krea 2 (Flux/Qwen-DiT)**, **Flux.1 Dev/Schnell**, **SDXL 1.0**, **Pony V6 XL (`clip_type = pony`)**, **Illustrious XL (`clip_type = illustrious`)**, and **MiniMax H3 (`FL2VA` vs `Ref2VA`)**.\n"
            "* **🧩 3) LoRA, DoRA & PRISM Orthogonal SVD (`[03]`, `[05]` & `Model Foundry`)**:\n"
            "  * **LoRA & DoRA**: Load in standard slots in `[03]` and `[05]`, protected by **PRISM Orthogonal SVD** & **Turbo-Shield**.\n"
            "  * **🏛️ EZ Model Foundry & LoRA Lab (in DevOps Studio — Station 3 `BF16` / `I64` Alpha / Zero-Up Kaiming Guard / Anti-3D)**: 5-station laboratory for Dataset Curation, LoRA/DoRA Training, **Gold Epoch Selection** via PRISM Effective Rank Entropy & Condition Number ($\\kappa = \\sigma_1 / \\sigma_k$), native **`BF16`/`FP16`/`FP32` + `I64` `.alpha` SafeTensors I/O**, **Zero-`lora_up` Kaiming Noise Guard**, **automatic single-sided H3 orphan audio-key stripping**, **Multi-Rank (`r_a != r_b`) PRISM Orthogonal SVD Merging**, **Signed Negative Anti-3D Slider Subtraction (`-1.0 .. +1.0`)**, and **Cross-Architecture Guard (`ARCH_MISMATCH`)**."
        ),
        "prism_recipes": (
            "### 🧬 8. THE 9 PRISM MERGE RECIPES (`ez_h3_01`–`09`), 7 `EZ [05]` LORA COMBOS & AUDIO/MOTION RULES\n"
            "* **🛡️ Core Calibration Rules in `EZ [03]`, `EZ [05]` & `EZ [10]`**:\n"
            "  * **Local-Priority Shield (`remote_hub_mode = local_priority` — `🛡️ LOCAL CHOICES WIN`)**: Your local model and LoRA selections in `EZ [03]` and `EZ [05]` always win per slot over `EZ [10] Civitai Hub` (`[10]` may only populate empty `None` slots unless you manually switch `remote_hub_mode` to `hub_override`).\n"
            "  * **Raw Base UNet vs Baked PRISM/Turbo UNet (`SingularityV2_PRISM2` / `FastH3`)**: Use full recipe weights (`0.70–0.90` in Slot 1) + `ez_h3_06_dmad_pika_turbo_8step_v1` `ON` (`0.95–1.00`) on raw UNets (`PinkCherry`, `h3ErosMax`, `FL2VA-pruned`). On baked PRISM/Turbo UNets (`10Eros_Max_SingularityV2_PRISM2_PikaFlex`), reduce LoRA weights by **~25–30%** (`0.50–0.65` in Slot 1), keep `enable_video_turbo_lora = OFF`, and run `shift_video = 5.0`, `shift_audio = 3.0`, `8 steps`, `CFG 1.0`.\n"
            "  * **Audio-Mute Strip (`lora_X_audio_strength = 0.00`)**: Keep `Audio = 0.00` on all visual merges (`ez_h3_01`–`04`, `07`–`09`, `LMS`, `breastplayjiggle`) so `EZ [05]` physically strips `audio_in`/`a_attn`/`a_block` keys before injection. Only set `Audio = 0.75–1.00` on `ez_h3_05_sexgod_vocal_drive_v1`, `Audio\\moawxx_000002000`, and `ez_h3_06` Turbo.\n"
            "* **⚗️ All 9 PRISM Orthogonal SVD Merge Recipes (`PRISM_ORTHOGONAL_SVD`, `BF16`)**:\n"
            "  * **01 `ez_h3_01_cinema_physics_core_v1`**: `H3_VBVR_Pro_attn_only` + `minimax_h3_lms_v1.0_r64` (`0.85 / 0.40 / 0.60`) — SFW Cinema & Suno MV Primary Anchor.\n"
            "  * **02 `ez_h3_02_kinetic_combat_motion_v1`**: `H3_Combat_V2` + `H3_Motion_BoosterV2` (`0.80 / 0.45 / 0.60`) — Action, Dance & Camera Motion.\n"
            "  * **03 `ez_h3_03_mystic_skin_realism_v1`**: `MysticXXX_MMH3-V5` + `HMNSFW-Extreme-Realism` (`0.85 / 0.40 / 0.60`) — Photoreal Skin & NSFW Primary Anchor.\n"
            "  * **04 `ez_h3_04_intimate_anatomy_jiggle_v1`**: `HMPussyV2` + `breastplayjiggle_h3_v2` (`0.80 / 0.45 / 0.60`) — Micro-Anatomy & Soft-Body Physics (Slot 2).\n"
            "  * **05 `ez_h3_05_sexgod_vocal_drive_v1`**: `SexGod_NaughtyTimes_v3` + `moawxx_000002000` (`0.80 / 0.75 / 0.60`) — Joint-AV Motion + Vocal Drive (`Audio: 0.85`).\n"
            "  * **06 `ez_h3_06_dmad_pika_turbo_8step_v1`**: `minimax_h3_dmad_8step_full_critic` + `pika_h3_flex_turbo_8step` (`0.80 / 0.35 / 0.85`) — Locked 8-Step Hybrid Turbo (`EZ-05-TURBO-GUARD` safe).\n"
            "  * **07 `ez_h3_07_sakuga_anime_physics_v1`**: `H3_VBVR_Pro_attn_only` + `H3_Motion_Booster_anime` (`0.75 / 0.55 / 0.55`) — SFW 2D Anime & AMV Sakuga.\n"
            "  * **08 `ez_h3_08_anime_nsfw_sakuga_v1`**: `NSFW_ANIME_H3_V16` + `H3_Motion_Booster_anime` (`0.85 / 0.45 / 0.55`) — Illustrious XL 2D NSFW + Sakuga.\n"
            "  * **09 `ez_h3_09_glamour_uncensored_skin_v1`**: `Minimax_H3_Unlocked_V3` + `HMNSFW-Extreme-Realism` (`0.80 / 0.45 / 0.55`) — R-Rated Glamour & Dark-Fantasy without hardcore bias."
        ),
    },
    "JA": {
        "howto": (
            "### 🗺️ 1. 配線ガイド・ワンクリック自動配線・プロンプト直接確認 & 解像度ルーティング (`[01]` ➔ `[14]`)\n"
            "* **ワンクリック自動配線 (全ノード)**: 任意のEZノードを右クリックし、**`⚡ EZ Cinematrix 全ノードをワンクリック自動構築・配線`** を選択します (`[09] ➔ [10] ➔ [11] ➔ [12] ➔ [13] ➔ [01] ... ➔ [08]` + `[14]`)。\n"
            "* **🔍 オープンプロンプト出力 (`EZ [02]`)**: `krea2_image_prompt` と `h3_video_timeline_prompt` は任意のテキスト表示ノード (`ShowText` 等) に直接接続して確認できます。\n"
            "* **📐 解像度の配線 (`[01]` ➔ `[04]` & `[06]`)**: `[01]` の `final_width` と `final_height` を `[04]` および **`[06] Video Director` の `video_width`/`video_height`** に接続します。"
        ),
        "suno": (
            "### 🎵 2. `EZ [12]` SUNOミュージックビデオ・音声認識 (`WHISPER ASR`) & 自動プロンプト\n"
            "* **Sunoリンク (`suno.com/s/...`) & 48 kHz ステレオマスター**: URLまたはUUIDを貼り付けるだけで、48 kHzステレオ音源 (Suno v5.5 `.mp4` AAC対応)、BPM、歌詞を自動取得し、ローカルWhisper ASRで音声・歌詞を解析して `[02]` のシーンプロンプトを自動生成します。"
        ),
        "models": (
            "### 🧬 3. PRISM 直交SVD・KREA 2散文サニタイザー・TURBO-SHIELD & MINIMAX H3 (`[02]`–`[10]`)\n"
            "* **🧹 Krea 2 散文サニタイザー & Pony/Illustrious 括弧正規化 (`[02]` & `[03]`)**: Krea 2/Fluxでは `(tag:1.2)` の重み括弧と冗長な関係代名詞節を自動除去して自然言語カメラ散文に整形し、Pony/Illustriousでは重みなし括弧 `\\(medium\\)` を自動エスケープします。\n"
            "* **💎 PRISM 直交SVD部分空間アライメント & Turbo-Shield (`[03]`, `[05]`, `[10]`)**: サブLoRA (`Slot 2..3`) や加速Turbo LoRAをメインLoRA (`Slot 1`) の主特異ベクトル空間と直交投影し、肌の毛穴・顔立ち・微細構造を100%保護します。\n"
            "* **🖼️ 推奨 Krea 2 画像モデル (`EZ [03]`/`[04]`, `EZ-03-TURBO-GUARD` 自動二重Turbo防止搭載)**: Raw = `krea-2-raw-int8-convrot.safetensors`、`museByStableYogi_v35Int8Extended.safetensors`、`snofsSexNudesAndOther_krea2RawV14_int8.safetensors` | 内蔵Turbo = `museByStableYogi_v25NVFP4Turbo.safetensors` (RTX 50 NVFP4)、`DasiwaKrea2TurboRaw_cutedisasterV2Turbo_full_int8.safetensors`。\n"
            "* **📦 推奨 MiniMax H3 モデル・VAE・CLIP・LoRA (`https://huggingface.co/DeepBeepMeep/MiniMax-H3/tree/main`)**:\n"
            "  * **UNet**: `10Eros_Max_SingularityV2_PRISM2_PikaFlex_0.85_int8HQ.safetensors` または `FastH3-Omni-NVFP4-QAD-pruned_rank8_nvfp4.safetensors` (`13.8 GB`) | **Ref2VA**: `Minimax-h3_Singularity_ref2va_v2_pruned_int8_convrot.safetensors`。\n"
            "  * **CLIP (`minimax`)**: `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | **Video VAE (16-bit必須)**: `MiniMax-H3-video_vae_fp16.safetensors` (`5.21 GB`, `int8`の色ズレ防止) | **Audio VAE**: `MiniMax-H3-audio_vae_fp32.safetensors` (`605 MB`)。\n"
            "  * **推奨LoRA (`/loras`)**: Turbo (非Turbo UNet専用) = `minimax_h3_dmad_8step_full_critic_lora_bf16.safetensors` (`1.38 GB`) | 精細度強化 = `minimax_h3_lms_v1.0_r64.safetensors` (`0.20–0.30`)。"
        ),
        "upscale": (
            "### 🚀 4. エッジ指向LANCZOS + マルチスケール詳細復元・`4x➔2x 超解像` & `RIFE IFNet` (`[04]` & `[08]`)\n"
            "* **🔬 パス1 (追加VRAM 0 MB): エッジ指向Lanczos + マルチスケール高周波復元 ($\\sigma_1 = 0.85, \\sigma_2 = 2.1$)** (`[04]` & `[08]`)。\n"
            "* **🏆 推奨マスター構成**: **`4x-ClearRealityV1.pth`** (`4x➔2x`) + **`1x-ITF-SkinDiffDetail-Lite-v1.pth`** (`0.45` ブレンド) + `enable_frequency_polish = true` + 6ゾーンKeypointRCNN解剖学シールド (**最大12人同時追跡**)。"
        ),
        "tips": (
            "### 💡 5. 動的長尺VLMトークンスケーリング (`360s`/`72カット`)・3D潜在ヒステリシス投影 (`[07]`) & 3軸ディレクター (`[06]`)\n"
            "* **📈 動的長尺VLMトークン & コンテキストスケーリング (`EZ [02]`)**: 最大 **`360秒` (`72カット`)** まで対応し、`effective_max_tokens` (`6144➔8192`) と `n_ctx` (`8192➔12288`)、および1カットあたりの単語数 (`~38–68語/カット`) を自動配分して長尺動画での途中切れを完全防止します。\n"
            "* **⚡ GPUベクトル化3D二重閾値ヒステリシス & 24チャンネル直交残差スパイク投影 (`EZ [07]`)**: `seed_hi > 11.2` / `cand_lo > 6.5` の3Dヒステリシスと `_EZ_H3_24CH_SPIKE_AXIS` 直交投影により、肌の毛穴と質感を92%維持したまま潜在スパイクのみを除去します。\n"
            "* **🎬 3軸ディレクター制御 & Krea 2 `0.01` 刻み微調整 (`EZ [04]` & `[06]`)**: `Backward Track` および `Outro Track ➔ Follow` により正面後退トラッキングで顔を100%維持します。"
        ),
        "omniref": (
            "### 🖼️ 6. `EZ [13]` OMNI-REFERENCE 5スロット・スタジオ (キャラ参照 `[1]–[4]` + 動画シーンテンプレート `[5]`) & `EZ [14]` スイッチボード\n"
            "* **🎯 画像 (`Slot [1]`–`[4]`) と 参照動画 (`Slot [5]`) の併用時の役割分担**:\n"
            "  * **`Slot [1]`–`[4]` (主人公 `<Subject 1>` の顔・種族・肌色色素 `[R,G,B]`・衣装参照)** と **`Slot [5]` (参照動画 `.mp4`/`.mkv`/`.webp` によるシーン構図・カメラ角度・姿勢・モーション・音声テンプレート)** を自動分離します。\n"
            "  * **秒単位の期間同期 (`slot5_duration_mode = follow_master_duration`)**: `[02]`/`[06]` のマスター秒数に自動追従します。`EZ [14]` スイッチボードで画像のみ/動画のみをワンクリック切替可能です。"
        ),
        "basics": (
            "### 🎓 7. BASICS — 初心者ガイド (ComfyUI基礎・モデル種別・LoRA/DoRA & PRISM MODEL FOUNDRY)\n"
            "* **ComfyUI基礎・2Dセルアニメ自動最適化 (`EZ-03-ANIME-TURBO-BYPASS` + Illustrious XL `EZ-04-ILLUSTRIOUS-AUTO` 28step/CFG 5.5・DMD2 8step)・2系統ダークファンタジー (`dark-fantasy-real` 実写ARRI / `dark-fantasy-cgi` Diablo IV 3Dカットシーン + `EZ-03-ANTI3D-GUARD`) & PRISM Model Foundry (`BF16`/異ランク統合/負重みAnti-3D減算/`ARCH_MISMATCH`保護)**。"
        ),
    },
    "ES": {
        "howto": (
            "### 🗺️ 1. GUÍA HOW-TO, AUTO-CONEXIÓN 1-CLIC, INSPECCIÓN DE PROMPTS Y RESOLUCIÓN (`[01]` ➔ `[14]`)\n"
            "* **Auto-Conexión en 1 Clic**: Clic derecho en cualquier nodo EZ ➔ **`⚡ Auto-Crear y Conectar Flujo EZ Cinematrix (1-Clic)`** (`[09] ➔ [10] ➔ [11] ➔ [12] ➔ [13] ➔ [01] ... ➔ [08]` + `[14]`).\n"
            "* **🔍 Inspección Abierta de Prompts (`EZ [02]`)**: `krea2_image_prompt` y `h3_video_timeline_prompt` son salidas `STRING` 100% abiertas listas para conectar a cualquier nodo de texto (`ShowText`).\n"
            "* **Resolución (`[01]` ➔ `[06]`)**: Conecta `final_width` y `final_height` de `[01]` a `video_width` y `video_height` en `[06]` (`base_width`/`base_height` van solo a `[03]` y `[04]`)."
        ),
        "suno": (
            "### 🎵 2. `EZ [12]` SUNO MUSIC VIDEO, RECONOCIMIENTO DE VOZ (`WHISPER ASR`) Y AUTO-PROMPT\n"
            "* **Enlace Suno (`suno.com/s/...`) y Audio 48 kHz**: Descarga automáticamente el máster estéreo de 48 kHz (incluyendo Suno v5.5 `.mp4` AAC), BPM, etiquetas y letra.\n"
            "* **Reconocimiento de Voz (Whisper ASR) y Auto-Prompt en `[02]`**: Detecta habla/entrevistas (`SPOKEN_WORD`), canto (`VOCAL_SONG`) o instrumental."
        ),
        "models": (
            "### 🧬 3. PRISM ORTOGONAL SVD, SANITIZADOR DE DIALECTO, TURBO-SHIELD Y MINIMAX H3 (`[02]`–`[10]`)\n"
            "* **🧹 Sanitizador de Prosa Krea 2 y Normalizador de Paréntesis Pony/Illustrious (`[02]` y `[03]`)**: Elimina pesos `(tag:1.2)` y cláusulas repetitivas en Krea 2/Flux, y escapa paréntesis sin peso `\\(medium\\)` en Pony/Illustrious.\n"
            "* **💎 PRISM Ortogonal SVD y Turbo-Shield (`[03]`, `[05]`, `[10]`)**: Proyecta los LoRAs secundarios (`Slot 2..3`) y los Turbo-LoRAs ortogonalmente lejos del LoRA principal (`Slot 1`).\n"
            "* **🖼️ Modelos Krea 2 Recomendados (`EZ [03]`/`[04]` con `EZ-03-TURBO-GUARD`)**: Raw = `krea-2-raw-int8-convrot.safetensors`, `museByStableYogi_v35Int8Extended.safetensors`, `snofsSexNudesAndOther_krea2RawV14_int8.safetensors` | Turbo integrado = `museByStableYogi_v25NVFP4Turbo.safetensors` (RTX 50 NVFP4), `DasiwaKrea2TurboRaw_cutedisasterV2Turbo_full_int8.safetensors`.\n"
            "* **📦 Repositorio Oficial HuggingFace y Modelos Recomendados (`https://huggingface.co/DeepBeepMeep/MiniMax-H3/tree/main`)**:\n"
            "  * **UNet**: `10Eros_Max_SingularityV2_PRISM2_PikaFlex_0.85_int8HQ.safetensors` o `FastH3-Omni-NVFP4-QAD-pruned_rank8_nvfp4.safetensors` (`13.8 GB`) | **Ref2VA**: `Minimax-h3_Singularity_ref2va_v2_pruned_int8_convrot.safetensors`.\n"
            "  * **CLIP (`minimax`)**: `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | **Video VAE (16-bit sin deriva)**: `MiniMax-H3-video_vae_fp16.safetensors` (`5.21 GB`) | **Audio VAE**: `MiniMax-H3-audio_vae_fp32.safetensors` (`605 MB`).\n"
            "  * **LoRAs (`/loras`)**: Turbo (solo UNet sin Turbo) = `minimax_h3_dmad_8step_full_critic_lora_bf16.safetensors` (`1.38 GB`) | Nitidez = `minimax_h3_lms_v1.0_r64.safetensors` (`0.20–0.30`)."
        ),
        "upscale": (
            "### 🚀 4. LANCZOS DIRIGIDO POR BORDES + MULTI-SCALE RESTORER, `4x➔2x` Y `RIFE IFNet` (`[04]` & `[08]`)\n"
            "* **🔬 Paso 1 (0 MB VRAM): Lanczos Dirigido por Bordes + Restaurador Multi-Escala ($\\sigma_1 = 0.85, \\sigma_2 = 2.1$)** en `[04]` y `[08]`.\n"
            "* **🏆 Cadena Maestra**: **`4x-ClearRealityV1.pth`** (`4x➔2x`) + **`1x-ITF-SkinDiffDetail-Lite-v1.pth`** + `enable_frequency_polish = true` con protección anatómica KeypointRCNN de 6 zonas para hasta **12 personas simultáneas**."
        ),
        "tips": (
            "### 💡 5. ESCALADO DINÁMICO VLM (`360s`/`72 TOMAS`), HISTÉRESIS LATENTE 3D (`[07]`), KREA 2 (`[04]`) Y DIRECTOR 3 EJES (`[06]`)\n"
            "* **📈 Escalado Dinámico de Tokens y Contexto VLM (`5s` ➔ `360s` / `72 Tomas` en `EZ [02]`)**: Escala automáticamente `effective_max_tokens` (`6144➔8192`), `n_ctx` (`8192➔12288`) y asigna `~38–68 palabras/toma` para vídeos largos de hasta 4–6 minutos sin cortes.\n"
            "* **⚡ Histéresis 3D de Doble Umbral y Proyección Ortogonal de Picos de 24 Canales (`EZ [07]`)**: Detecta anomalías (`seed_hi > 11.2`, `cand_lo > 6.5` vía `F.max_pool3d`) y proyecta solo el eje corruptivo `_EZ_H3_24CH_SPIKE_AXIS` conservando el 92% de los poros y texturas.\n"
            "* **🎬 Controles de Director de 3 Ejes y Ajuste Fino `0.01` en `EZ [04]`/`[06]`**: Mantiene el 100% del rostro en `Backward Track` y `Outro Track ➔ Follow`."
        ),
        "omniref": (
            "### 🖼️ 6. `EZ [13]` OMNI-REFERENCE 5-SLOT STUDIO (PERSONAJE `[1]–[4]` + PLANTILLA DE ESCENA DE VÍDEO `[5]`) Y `EZ [14]` SWITCHBOARD\n"
            "* **🎯 División de Roles cuando Imagen (`Slot [1]`–`[4]`) y Vídeo de Referencia (`Slot [5]`) están activos**:\n"
            "  * **`Slot [1]`–`[4]`** definen la identidad facial, especie y pigmento de piel (`slot1_skin_rgb`) de `<Subject 1>`, mientras que **`Slot [5]` (`.mp4`/`.mkv`/`.webp` en `slot5_start_offset_sec`)** define la **plantilla espacial de escena, escritorio/estudio, cámara, postura, movimiento y audio** (`follow_master_duration` en segundos) + control remoto en `EZ [14]`."
        ),
        "basics": (
            "### 🎓 7. BASICS — GUÍA PARA PRINCIPIANTES, MODELOS, LORA/DORA Y PRISM MODEL FOUNDRY\n"
            "* **ComfyUI, Anime 2D Plano (`EZ-03-ANIME-TURBO-BYPASS` + Illustrious XL `EZ-04-ILLUSTRIOUS-AUTO`), Doble Motor Dark-Fantasy (`dark-fantasy-real` ARRI Live-Action / `dark-fantasy-cgi` Diablo IV 3D VFX + `EZ-03-ANTI3D-GUARD`) y PRISM Model Foundry & LoRA Lab (`BF16`/Multi-Rank/Anti-3D `-1..+1`/`ARCH_MISMATCH`)**."
        ),
    },
    "DE": {
        "howto": (
            "### 🗺️ 1. HOW-TO, 1-KLICK AUTO-WIRE, OFFENE PROMPT-INSPEKTION & AUFLÖSUNG (`[01]` ➔ `[14]`)\n"
            "* **1-Klick Auto-Wire**: Rechtsklick auf einen EZ-Node ➔ **`⚡ EZ Cinematrix Pipeline automatisch erstellen (1-Klick)`** (`[09] ➔ [10] ➔ [11] ➔ [12] ➔ [13] ➔ [01] ... ➔ [08]` + `[14]`).\n"
            "* **🔍 Offene Prompt-Inspektion (`EZ [02]`)**: `krea2_image_prompt` und `h3_video_timeline_prompt` sind 100% offene `STRING`-Ausgänge für beliebige Text-Nodes (`ShowText`).\n"
            "* **Auflösung (`[01]` ➔ `[06]`)**: `final_width` und `final_height` aus `[01]` mit `video_width` und `video_height` in `[06]` verbinden (`base_width`/`base_height` gehören nur an `[03]` und `[04]`)."
        ),
        "suno": (
            "### 🎵 2. `EZ [12]` SUNO MUSIC VIDEO, SPRACHERKENNUNG (`WHISPER ASR`) & AUTO-PROMPT\n"
            "* **Suno-Link (`suno.com/s/...`) & 48 kHz Stereo-Master**: Lädt automatisch 48 kHz Stereo-Audio (inkl. Suno v5.5 `.mp4` AAC), BPM, Stil-Tags und Songtext."
        ),
        "models": (
            "### 🧬 3. PRISM ORTHOGONALE SVD, DIALEKT-SANITIZER, TURBO-SHIELD & MINIMAX H3 (`[02]`–`[10]`)\n"
            "* **🧹 Krea 2 Prosa-Sanitizer & Pony/Illustrious Klammer-Normalisierer (`[02]` & `[03]`)**: Entfernt `(tag:1.2)`-Gewichtsklammern und Endlossätze bei Krea 2/Flux und maskiert ungewichtete Klammern `\\(medium\\)` bei Pony/Illustrious.\n"
            "* **💎 PRISM Orthogonale SVD & Turbo-Shield (`[03]`, `[05]`, `[10]`)**: Projiziert sekundäre LoRAs (`Slot 2..3`) sowie die Turbo-LoRAs orthogonal weg vom Haupt-LoRA (`Slot 1`).\n"
            "* **🖼️ Empfohlene Krea 2 Bildmodelle (`EZ [03]`/`[04]` mit `EZ-03-TURBO-GUARD`)**: Raw = `krea-2-raw-int8-convrot.safetensors`, `museByStableYogi_v35Int8Extended.safetensors`, `snofsSexNudesAndOther_krea2RawV14_int8.safetensors` | Integrierter Turbo = `museByStableYogi_v25NVFP4Turbo.safetensors` (RTX 50 NVFP4), `DasiwaKrea2TurboRaw_cutedisasterV2Turbo_full_int8.safetensors`.\n"
            "* **📦 HuggingFace-Repository & Empfohlene Modelle (`https://huggingface.co/DeepBeepMeep/MiniMax-H3/tree/main`)**:\n"
            "  * **UNet**: `10Eros_Max_SingularityV2_PRISM2_PikaFlex_0.85_int8HQ.safetensors` oder `FastH3-Omni-NVFP4-QAD-pruned_rank8_nvfp4.safetensors` (`13.8 GB`) | **Ref2VA**: `Minimax-h3_Singularity_ref2va_v2_pruned_int8_convrot.safetensors`.\n"
            "  * **CLIP (`minimax`)**: `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | **Video-VAE (16-Bit verlustfrei)**: `MiniMax-H3-video_vae_fp16.safetensors` (`5.21 GB`) | **Audio-VAE**: `MiniMax-H3-audio_vae_fp32.safetensors` (`605 MB`).\n"
            "  * **Top-LoRAs (`/loras`)**: Turbo (nur Non-Turbo UNet) = `minimax_h3_dmad_8step_full_critic_lora_bf16.safetensors` (`1.38 GB`) | Schärfe = `minimax_h3_lms_v1.0_r64.safetensors` (`0.20–0.30`)."
        ),
        "upscale": (
            "### 🚀 4. KANTENGESTEUERTER LANCZOS + MULTI-SCALE RESTORER, `4x➔2x` & `RIFE IFNet` (`[04]` & `[08]`)\n"
            "* **🔬 Pass 1 (0 MB VRAM): Kantengesteuerter Lanczos + Multi-Scale High-Pass Restorer ($\\sigma_1 = 0.85, \\sigma_2 = 2.1$)** in `[04]` und `[08]`.\n"
            "* **🏆 Beste Masterkette**: **`4x-ClearRealityV1.pth`** (`4x➔2x`) + **`1x-ITF-SkinDiffDetail-Lite-v1.pth`** + `enable_frequency_polish = true` mit 6-Zonen KeypointRCNN-Schutz für bis zu **12 Personen gleichzeitig**."
        ),
        "tips": (
            "### 💡 5. DYNAMISCHE VLM-LANGZEITSKALIERUNG (`360s`/`72 SHOTS`), 3D-LATENT-HYSTERESE (`[07]`) & 3-ACHSEN-DIRECTOR (`[06]`)\n"
            "* **📈 Dynamische VLM Token- & Kontext-Skalierung (`5s` ➔ `360s` / `72 Shots` in `EZ [02]`)**: Skaliert `effective_max_tokens` (`6144➔8192`), `n_ctx` (`8192➔12288`) und das Wortbudget pro Shot (`~38–68 Wörter/Shot`) automatisch für 4–6-minütige Videos ohne Abbruch.\n"
            "* **⚡ GPU-Vektorisierte 3D-Doppelschwellen-Hysterese & 24-Kanal Orthogonale Spike-Projektion (`EZ [07]`)**: Filtert latente Ausreißer (`seed_hi > 11.2`, `cand_lo > 6.5` via `F.max_pool3d`) entlang `_EZ_H3_24CH_SPIKE_AXIS` und bewahrt 92% der Hautporen- und Texturdetails.\n"
            "* **🎬 3-Achsen-Regie & `0.01`-Feinabstimmung in `EZ [04]`/`[06]`**: Bewahrt 100% Gesichtsidentität via `Backward Track` & `Outro Track ➔ Follow`."
        ),
        "omniref": (
            "### 🖼️ 6. `EZ [13]` OMNI-REFERENCE 5-SLOT STUDIO (CHARAKTER `[1]–[4]` + VIDEO-SZENENVORLAGE `[5]`) & `EZ [14]` SWITCHBOARD\n"
            "* **🎯 Rollenteilung bei Bild (`Slot [1]`–`[4]`) + Referenzvideo (`Slot [5]`)**:\n"
            "  * **`Slot [1]`–`[4]`** definieren Gesichtsidentität, Spezies und Hautpigment (`slot1_skin_rgb`) von `<Subject 1>`, während **`Slot [5]` (`.mp4`/`.mkv`/`.webp` ab `slot5_start_offset_sec`)** als **Szenen-, Kamera-, Haltungs-, Bewegungs- & Audiovorlage** (`follow_master_duration` in Sekunden) dient + `EZ [14]` Pipeline Switchboard."
        ),
        "basics": (
            "### 🎓 7. BASICS — EINSTEIGERGUIDE, MODELLE, LORA/DORA & PRISM MODEL FOUNDRY\n"
            "* **ComfyUI, 2D-Cel-Anime (`EZ-03-ANIME-TURBO-BYPASS` + Illustrious XL `EZ-04-ILLUSTRIOUS-AUTO`), Duales Dark-Fantasy-System (`dark-fantasy-real` ARRI Live-Action / `dark-fantasy-cgi` Diablo IV 3D-Cutscene + `EZ-03-ANTI3D-GUARD`) & PRISM Model Foundry (`BF16`/Multi-Rank/Anti-3D `-1..+1`/`ARCH_MISMATCH`)**."
        ),
    },
    "FR": {
        "howto": (
            "### 🗺️ 1. GUIDE HOW-TO, AUTO-CÂBLAGE 1-CLIC, INSPECTION DES PROMPTS & RÉSOLUTION (`[01]` ➔ `[14]`)\n"
            "* **Auto-Câblage 1-Clic**: Clic droit sur un nœud EZ ➔ **`⚡ Auto-Créer & Câbler tout le flux EZ Cinematrix (1-Clic)`** (`[09] ➔ [10] ➔ [11] ➔ [12] ➔ [13] ➔ [01] ... ➔ [08]` + `[14]`).\n"
            "* **🔍 Inspection Ouverte des Prompts (`EZ [02]`)**: `krea2_image_prompt` et `h3_video_timeline_prompt` sont des sorties `STRING` 100% ouvertes connectables à tout nœud texte (`ShowText`).\n"
            "* **Résolution (`[01]` ➔ `[06]`)**: Connectez `final_width` et `final_height` de `[01]` à `video_width` et `video_height` sur `[06]` (`base_width`/`base_height` vont uniquement à `[03]` et `[04]`)."
        ),
        "suno": (
            "### 🎵 2. `EZ [12]` SUNO MUSIC VIDEO, RECONNAISSANCE VOCALE (`WHISPER ASR`) & AUTO-PROMPT\n"
            "* **Lien Suno (`suno.com/s/...`) & Audio 48 kHz**: Télécharge automatiquement le master stéréo 48 kHz (y compris Suno v5.5 `.mp4` AAC), BPM, tags et paroles."
        ),
        "models": (
            "### 🧬 3. SVD ORTHOGONALE PRISM, SANITISEUR DE DIALECTE, TURBO-SHIELD & MINIMAX H3 (`[02]`–`[10]`)\n"
            "* **🧹 Sanitiseur de Prose Krea 2 & Normaliseur de Parenthèses Pony/Illustrious (`[02]` & `[03]`)**: Supprime les poids `(tag:1.2)` et clauses répétitives sur Krea 2/Flux, et échappe les parenthèses non pondérées `\\(medium\\)` sur Pony/Illustrious.\n"
            "* **💎 SVD Orthogonale PRISM & Turbo-Shield (`[03]`, `[05]`, `[10]`)**: Projette les LoRAs secondaires (`Slot 2..3`) et les Turbo-LoRAs orthogonalement au LoRA principal (`Slot 1`).\n"
            "* **🖼️ Modèles Image Krea 2 Recommandés (`EZ [03]`/`[04]` avec `EZ-03-TURBO-GUARD`)**: Raw = `krea-2-raw-int8-convrot.safetensors`, `museByStableYogi_v35Int8Extended.safetensors`, `snofsSexNudesAndOther_krea2RawV14_int8.safetensors` | Turbo intégré = `museByStableYogi_v25NVFP4Turbo.safetensors` (RTX 50 NVFP4), `DasiwaKrea2TurboRaw_cutedisasterV2Turbo_full_int8.safetensors`.\n"
            "* **📦 Dépôt HuggingFace & Modèles Recommandés (`https://huggingface.co/DeepBeepMeep/MiniMax-H3/tree/main`)**:\n"
            "  * **UNet**: `10Eros_Max_SingularityV2_PRISM2_PikaFlex_0.85_int8HQ.safetensors` ou `FastH3-Omni-NVFP4-QAD-pruned_rank8_nvfp4.safetensors` (`13.8 GB`) | **Ref2VA**: `Minimax-h3_Singularity_ref2va_v2_pruned_int8_convrot.safetensors`.\n"
            "  * **CLIP (`minimax`)**: `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | **Video-VAE (16-bit sans dérive)**: `MiniMax-H3-video_vae_fp16.safetensors` (`5.21 GB`) | **Audio-VAE**: `MiniMax-H3-audio_vae_fp32.safetensors` (`605 MB`).\n"
            "  * **LoRAs (`/loras`)**: Turbo (UNet non-Turbo uniquement) = `minimax_h3_dmad_8step_full_critic_lora_bf16.safetensors` (`1.38 GB`) | Détails = `minimax_h3_lms_v1.0_r64.safetensors` (`0.20–0.30`)."
        ),
        "upscale": (
            "### 🚀 4. LANCZOS DIRIGÉ PAR LES BORDS + MULTI-SCALE RESTORER, `4x➔2x` & `RIFE IFNet` (`[04]` & `[08]`)\n"
            "* **🔬 Passe 1 (0 Mo VRAM): Lanczos Dirigé par les Bords + Restaurateur Multi-Échelle ($\\sigma_1 = 0.85, \\sigma_2 = 2.1$)** dans `[04]` et `[08]`.\n"
            "* **🏆 Chaîne Maître Recommandée**: **`4x-ClearRealityV1.pth`** (`4x➔2x`) + **`1x-ITF-SkinDiffDetail-Lite-v1.pth`** + `enable_frequency_polish = true` avec bouclier anatomique KeypointRCNN 6 zones jusqu'à **12 personnes simultanées**."
        ),
        "tips": (
            "### 💡 5. MISE À L'ÉCHELLE VLM DYNAMIQUE (`360s`/`72 PLANS`), HYSTÉRÉSIS LATENTE 3D (`[07]`) & RÉALISATEUR 3 AXES (`[06]`)\n"
            "* **📈 Mise à l'Échelle Dynamique des Tokens et du Contexte VLM (`5s` ➔ `360s` / `72 Plans` dans `EZ [02]`)**: Adapte automatiquement `effective_max_tokens` (`6144➔8192`), `n_ctx` (`8192➔12288`) et le quota de mots par plan (`~38–68 mots/plan`) pour les vidéos longues de 4 à 6 minutes sans coupure.\n"
            "* **⚡ Hystérésis 3D à Double Seuil & Projection Orthogonale des Pics 24 Canaux (`EZ [07]`)**: Détecte les anomalies (`seed_hi > 11.2`, `cand_lo > 6.5` via `F.max_pool3d`) et projette uniquement l'axe `_EZ_H3_24CH_SPIKE_AXIS` tout en préservant 92% des pores de la peau et des textures.\n"
            "* **🎬 Contrôles Réalisateur 3 Axes & Réglage Fin `0.01` dans `EZ [04]`/`[06]`**: Préserve 100% du visage via `Backward Track` & `Outro Track ➔ Follow`."
        ),
        "omniref": (
            "### 🖼️ 6. `EZ [13]` OMNI-REFERENCE 5-SLOT STUDIO (PERSONNAGE `[1]–[4]` + MODÈLE DE SCÈNE VIDÉO `[5]`) & `EZ [14]` SWITCHBOARD\n"
            "* **🎯 Répartition des Rôles Image (`Slot [1]`–`[4]`) + Vidéo de Référence (`Slot [5]`)**:\n"
            "  * **`Slot [1]`–`[4]`** définissent l'identité faciale, l'espèce et le pigment cutané (`slot1_skin_rgb`) de `<Subject 1>`, tandis que **`Slot [5]` (`.mp4`/`.mkv`/`.webp` à `slot5_start_offset_sec`)** sert de **modèle spatial de scène, caméra, posture, mouvement et audio** (`follow_master_duration` en secondes) + `EZ [14]` Switchboard."
        ),
        "basics": (
            "### 🎓 7. BASICS — GUIDE DÉBUTANT, MODÈLES, LORA/DORA & PRISM MODEL FOUNDRY\n"
            "* **ComfyUI, Anime 2D Plat (`EZ-03-ANIME-TURBO-BYPASS` + Illustrious XL `EZ-04-ILLUSTRIOUS-AUTO`), Double Moteur Dark-Fantasy (`dark-fantasy-real` ARRI Live-Action / `dark-fantasy-cgi` Cinématique 3D Diablo IV + `EZ-03-ANTI3D-GUARD`) & PRISM Model Foundry (`BF16`/Multi-Rank/Anti-3D `-1..+1`/`ARCH_MISMATCH`)**."
        ),
    },
    "ZH": {
        "howto": (
            "### 🗺️ 1. 操作指南、一键自动连线、开放提示词检查与分辨率路由 (`[01]` ➔ `[14]`)\n"
            "* **一键自动连线**: 右键点击任意 EZ 节点并选择 **`⚡ 一键自动创建并连接完整 EZ Cinematrix 工作流`** (`[09] ➔ [10] ➔ [11] ➔ [12] ➔ [13] ➔ [01] ... ➔ [08]` + `[14]`)。\n"
            "* **🔍 100% 开放提示词检查 (`EZ [02]`)**: `krea2_image_prompt` 与 `h3_video_timeline_prompt` 均为完全开放的 `STRING` 输出，可直接连线至任意文本预览节点 (`ShowText`)。\n"
            "* **分辨率连线 (`[01]` ➔ `[06]`)**: 将 `[01]` 的 `final_width` 与 `final_height` 连接至 `[06]` 的 `video_width` 与 `video_height` (`base_width`/`base_height` 仅连接至 `[03]` 与 `[04]`)。"
        ),
        "suno": (
            "### 🎵 2. `EZ [12]` SUNO 音乐视频、语音识别 (`WHISPER ASR`)、自动提示词与时长同步\n"
            "* **Suno 链接 (`suno.com/s/...`) 与 48 kHz 立体声母带**: 粘贴链接即可自动抓取 48 kHz 立体声音频 (支持 Suno v5.5 `.mp4` AAC 流)、歌名、风格标签、BPM 与完整歌词。"
        ),
        "models": (
            "### 🧬 3. PRISM 正交 SVD、方言净化器、TURBO-SHIELD 与 MINIMAX H3 (`[02]`–`[10]`)\n"
            "* **🧹 Krea 2 自然散文净化器与 Pony/Illustrious 括号规范器 (`[02]` & `[03]`)**: 在 Krea 2/Flux 模式下自动剥离 `(tag:1.2)` 权重括号与冗余从句并转换为自然镜头散文；在 Pony/Illustrious 模式下自动转义无权重括号 `\\(medium\\)`。\n"
            "* **💎 PRISM 正交 SVD 子空间对齐与 Turbo-Shield (`[03]`、`[05]`、`[10]`)**: 将副槽位 LoRA (`Slot 2..3`) 及加速 Turbo LoRA 正交投影至主角色 LoRA (`Slot 1`) 的主奇异向量空间之外，100% 保留皮肤毛孔与面部特征。\n"
            "* **🖼️ 精选 Krea 2 图像底模清单 (`EZ [03]`/`[04]`，内置 `EZ-03-TURBO-GUARD` 防双重加速过曝)**: Raw 底模 = `krea-2-raw-int8-convrot.safetensors`、`museByStableYogi_v35Int8Extended.safetensors`、`snofsSexNudesAndOther_krea2RawV14_int8.safetensors` | 内置 Turbo = `museByStableYogi_v25NVFP4Turbo.safetensors` (RTX 50 NVFP4)、`DasiwaKrea2TurboRaw_cutedisasterV2Turbo_full_int8.safetensors`。\n"
            "* **📦 官方 HuggingFace 仓库与最佳 MiniMax H3 模型清单 (`https://huggingface.co/DeepBeepMeep/MiniMax-H3/tree/main`)**:\n"
            "  * **UNet**: `10Eros_Max_SingularityV2_PRISM2_PikaFlex_0.85_int8HQ.safetensors` 或 `FastH3-Omni-NVFP4-QAD-pruned_rank8_nvfp4.safetensors` (`13.8 GB`) | **Ref2VA**: `Minimax-h3_Singularity_ref2va_v2_pruned_int8_convrot.safetensors`。\n"
            "  * **CLIP (`minimax`)**: `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | **Video VAE (16-bit 零对比度漂移)**: `MiniMax-H3-video_vae_fp16.safetensors` (`5.21 GB`) | **Audio VAE**: `MiniMax-H3-audio_vae_fp32.safetensors` (`605 MB`)。\n"
            "  * **顶级 LoRA (`/loras`)**: Turbo (仅用于无内置Turbo底模) = `minimax_h3_dmad_8step_full_critic_lora_bf16.safetensors` (`1.38 GB`) | 锐度微距增强 = `minimax_h3_lms_v1.0_r64.safetensors` (`0.20–0.30`)。"
        ),
        "upscale": (
            "### 🚀 4. 边缘导向 LANCZOS + 多尺度细节恢复、`4x➔2x 超采样` 与 `原生 RIFE IFNet` (`[04]` & `[08]`)\n"
            "* **🔬 第一遍 (0 MB 显存): 边缘导向 Lanczos + 多尺度高频细节恢复器 ($\\sigma_1 = 0.85, \\sigma_2 = 2.1$)** (`[04]` 与 `[08]`)。\n"
            "* **🏆 最佳写实超分组合**: **`4x-ClearRealityV1.pth`** (`4x➔2x`) + **`1x-ITF-SkinDiffDetail-Lite-v1.pth`** (`0.45` 融合) + `enable_frequency_polish = true` + 6区域 KeypointRCNN 解剖保护 (支持最多 **12 人同框**)。"
        ),
        "tips": (
            "### 💡 5. 动态长视频 VLM 令牌扩展 (`360s`/`72镜头`)、3D 潜空间迟滞投影 (`[07]`) 与三轴导演 (`[06]`)\n"
            "* **📈 动态长视频 VLM 令牌与上下文扩展 (`5s` ➔ `360s` / `72 镜头` 于 `EZ [02]`)**: 自动将 `effective_max_tokens` (`6144➔8192`)、`n_ctx` (`8192➔12288`) 及单镜头词数配额 (`~38–68 词/镜头`) 动态扩展，确保 4–6 分钟长视频绝不在 `[END_PROMPT]` 前截断。\n"
            "* **⚡ GPU 矢量化 3D 双阈值迟滞与 24 通道正交残差尖峰投影 (`EZ [07]`)**: 通过 `seed_hi > 11.2` / `cand_lo > 6.5` 3D 迟滞检测与 `_EZ_H3_24CH_SPIKE_AXIS` 正交残差投影，在消除伪影的同时保留 92% 的皮肤毛孔与织物高频纹理。\n"
            "* **🎬 三轴全能导演控制与 Krea 2 `0.01` 步进精调 (`EZ [04]` & `[06]`)**: `Backward Track` 与 `Outro Track ➔ Follow` 100% 锁定面部特征。"
        ),
        "omniref": (
            "### 🖼️ 6. `EZ [13]` 全能五槽位参考中心 (角色身份 `[1]–[4]` + 视频场景与动作模板 `[5]`) 与 `EZ [14]` 总控台\n"
            "* **🎯 参考图 (`Slot [1]`–`[4]`) 与 参考视频 (`Slot [5]`) 同时启用时的智能分工**:\n"
            "  * **`Slot [1]`–`[4]`** 专用于锁定主角 `<Subject 1>` 的面部特征、种族与皮肤色素 (`slot1_skin_rgb`)；**`Slot [5]` (`.mp4`/`.mkv`/`.webp` 于 `slot5_start_offset_sec`)** 作为 **空间场景构图、演播室/桌面布局、镜头角度、姿态、动作与音频模板** (`follow_master_duration` 按秒自动同步) + `EZ [14]` 一键旁路总控。"
        ),
        "basics": (
            "### 🎓 7. BASICS — 新手入门指南 (ComfyUI 基础、模型类型、LoRA/DoRA、PRISM Foundry 与资源文件)\n"
            "* **ComfyUI 基础、纯平涂 2D 赛璐璐动漫引擎 (`EZ-03-ANIME-TURBO-BYPASS` + Illustrious XL `EZ-04-ILLUSTRIOUS-AUTO`)、双轨暗黑奇幻引擎 (`dark-fantasy-real` ARRI 实拍暗黑电影 / `dark-fantasy-cgi` 暗黑破坏神IV 预渲染 3D 过场动画 + `EZ-03-ANTI3D-GUARD`) 及 PRISM Model Foundry (`BF16`/跨秩SVD融合/负权重Anti-3D减法/`ARCH_MISMATCH`跨架构防护)**。"
        ),
    },
}


def resolve_note_locale_code(note_locale: str = "Auto (Follow Active UI Locale)") -> str:
    raw = str(note_locale or "").strip().upper()
    for code in ("EN", "SV", "ZH", "JA", "ES", "DE", "FR"):
        if raw.startswith(code):
            return code
    try:
        loc_payload = load_project_locales_payload()
        active = str(loc_payload.get("active_locale", "EN")).strip().upper()
        if active in STUDIO_GUIDE_CHAPTERS:
            return active
    except Exception:
        pass
    return "EN"


def _load_runtime_changelog_markdown(lang: str = "SV") -> Tuple[str, str]:
    here = Path(__file__).resolve()
    candidates = [
        here.parent.parent / "CHANGELOG.md",
        here.parent.parent.parent / "CHANGELOG.md",
        here.parent.parent.parent.parent / "RELEASES" / "CHANGELOG.md",
        here.parent / "BLUEPRINTS" / "00_cinematrix_core" / "CHANGELOG.md",
    ]
    for cand in candidates:
        if cand.is_file():
            raw_md = cand.read_text(encoding="utf-8", errors="replace").strip()
            if raw_md:
                m_ver = re.search(r"(\d+\.\d+\.\d+-(?:DEV|STAGING|PRODUCTION))", raw_md)
                ver_tag = m_ver.group(1) if m_ver else "3.6.1-PRODUCTION"
                return (ver_tag, raw_md)
    fallback_tag = "3.6.1-PRODUCTION"
    if str(lang or "SV").upper().startswith("SV"):
        fallback_md = (
            "### 📜 10. VERSIONS- & UPPDATERINGSLOGG (`3.6.1-PRODUCTION` | Freemium `1.1.1-PRODUCTION`)\n"
            "* **Format (`[Major].[Minor].[Hotfix]-[Environment]`)**: `MAJOR` = arkitekturskifte | `MINOR` = nya funktioner/autopiloter | `HOTFIX` = kirurgiska bugg-/tensorfixar.\n"
            "* **`3.6.1-PRODUCTION` / `1.1.1-PRODUCTION` [HOTFIX]**: Ref2VA utsnittslås i `EZ [06]`, `t=0` fönster-handoff + 2D Viseme Jaw Soft-Ceiling (`0.58 * tanh`) i `EZ [07]`, samt `'lust for life'` idiomskydd & negativ stilkollisions-läkning i `EZ [02]`.\n"
            "* **`3.6.0-PRODUCTION` / `1.1.0-PRODUCTION` [MINOR]**: Multi-arkitektur autopilot (`Illustrious`, `Pony`, `SDXL`, `Flux`) med `stage2_steps = 0` och Civitai `#ModelID`/URL-uppslag.\n"
            "* **`3.5.0-PRODUCTION` / `1.0.0-PRODUCTION` [MAJOR]**: 14-noders `CINEMATRIX_BUS`, PRISM SVD, `EZ [12]` Suno/Whisper ASR & MIT Open-Core Unlimited lansering."
        )
    else:
        fallback_md = (
            "### 📜 10. VERSION & PATCH CHANGELOG (`3.6.1-PRODUCTION` | Freemium `1.1.1-PRODUCTION`)\n"
            "* **Scheme (`[Major].[Minor].[Hotfix]-[Environment]`)**: `MAJOR` = architecture shift | `MINOR` = new features/autopilots | `HOTFIX` = surgical bug/tensor fixes.\n"
            "* **`3.6.1-PRODUCTION` / `1.1.1-PRODUCTION` [HOTFIX]**: Single-ref `Ref2VA` framing lock in `EZ [06]`, `t=0` inter-window handoff + 2D Viseme Jaw Soft-Ceiling (`0.58 * tanh`) in `EZ [07]`, plus `'lust for life'` idiom shield & negative style-collision healer in `EZ [02]`.\n"
            "* **`3.6.0-PRODUCTION` / `1.1.0-PRODUCTION` [MINOR]**: Multi-architecture autopilot (`Illustrious`, `Pony`, `SDXL`, `Flux`) with `stage2_steps = 0` and Civitai `#ModelID`/URL resolver.\n"
            "* **`3.5.0-PRODUCTION` / `1.0.0-PRODUCTION` [MAJOR]**: 14-node `CINEMATRIX_BUS`, PRISM SVD, `EZ [12]` Suno/Whisper ASR & MIT Open-Core Unlimited launch."
        )
    return (fallback_tag, fallback_md)


def compile_localized_studio_note_markdown(
    topic_preset: str,
    note_locale: str = "Auto (Follow Active UI Locale)",
    custom_notes: str = "",
    cinematrix_bus: Dict[str, Any] | None = None,
) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
    lang = resolve_note_locale_code(note_locale)
    chapters = STUDIO_GUIDE_CHAPTERS.get(lang, STUDIO_GUIDE_CHAPTERS["EN"])
    preset_str = str(topic_preset or NOTE_TOPIC_PRESETS[0])
    active_ver_tag, changelog_section_md = _load_runtime_changelog_markdown(lang)

    selected_blocks = []
    if preset_str.startswith("1."):
        selected_blocks.append(chapters["howto"])
    elif preset_str.startswith("2.") and "Suno" in preset_str:
        selected_blocks.append(chapters["suno"])
    elif preset_str.startswith("3."):
        selected_blocks.append(chapters["models"])
    elif preset_str.startswith("4."):
        selected_blocks.append(chapters["upscale"])
    elif preset_str.startswith("5."):
        selected_blocks.append(chapters["tips"])
    elif preset_str.startswith("6.") and "Omni-Reference" in preset_str:
        selected_blocks.append(chapters.get("omniref", chapters["howto"]))
    elif preset_str.startswith("7.") and "Basics" in preset_str:
        selected_blocks.append(chapters.get("basics", STUDIO_GUIDE_CHAPTERS["EN"]["basics"]))
    elif preset_str.startswith("8.") and "PRISM Merge" in preset_str:
        selected_blocks.append(chapters.get("prism_recipes", STUDIO_GUIDE_CHAPTERS["SV"]["prism_recipes"] if lang == "SV" else STUDIO_GUIDE_CHAPTERS["EN"]["prism_recipes"]))
    elif "Custom Studio Notes Only" in preset_str or preset_str.startswith("9."):
        selected_blocks.clear()
    elif preset_str.startswith("10.") or "Changelog" in preset_str:
        selected_blocks.append(changelog_section_md)
    else:
        selected_blocks.extend([
            chapters["howto"],
            chapters.get("omniref", ""),
            chapters["suno"],
            chapters["models"],
            chapters.get("prism_recipes", STUDIO_GUIDE_CHAPTERS["EN"].get("prism_recipes", "")),
            chapters["upscale"],
            chapters["tips"],
            chapters.get("basics", STUDIO_GUIDE_CHAPTERS["EN"]["basics"]),
            changelog_section_md,
        ])

    user_note_clean = str(custom_notes or "").strip()
    if user_note_clean:
        selected_blocks.append(f"### 📝 CUSTOM STUDIO NOTES\n{user_note_clean}")

    bus_out: Dict[str, Any] = dict(cinematrix_bus) if isinstance(cinematrix_bus, dict) else {}
    suno_pkg = bus_out.get("suno_music_studio") if not bus_out.get("suno_bypassed") else None
    if not bus_out.get("suno_bypassed") and not (isinstance(suno_pkg, dict) and suno_pkg.get("active")):
        try:
            from .engine_ez_12_cinematrix_suno_music_studio import get_active_suno_session_package
            cached_suno = get_active_suno_session_package()
            if isinstance(cached_suno, dict) and cached_suno.get("active"):
                suno_pkg = cached_suno
        except Exception:
            suno_pkg = None

    live_g: Dict[str, Any] = {}
    try:
        from ..EZ_ADAPTERS.adapter_ez_02_cinematrix_qwenvl_timeline import _ACTIVE_QWENVL_SCENE_STATE
        if isinstance(_ACTIVE_QWENVL_SCENE_STATE, dict):
            live_g.update(_ACTIVE_QWENVL_SCENE_STATE)
    except Exception:
        pass
    try:
        from server import PromptServer
        ps = getattr(PromptServer, "instance", None)
        pq = getattr(ps, "prompt_queue", None) if ps is not None else None
        running = getattr(pq, "currently_running", None) if pq is not None else None
        if isinstance(running, dict) and len(running) > 0:
            active_item = next(iter(running.values()))
            p_graph = active_item[2] if isinstance(active_item, (list, tuple)) and len(active_item) > 2 and isinstance(active_item[2], dict) else None
            if isinstance(p_graph, dict):
                for n_def in p_graph.values():
                    if not isinstance(n_def, dict):
                        continue
                    ct = str(n_def.get("class_type", "") or "")
                    n_in = n_def.get("inputs") if isinstance(n_def.get("inputs"), dict) else {}
                    if "QwenVL" in ct or "EZ_02" in ct:
                        for k_q in ("style_target", "content_rating_mode", "compiler_seed", "subject_stance_posture", "body_choreography_preset", "camera_trajectory_arc"):
                            val_q = n_in.get(k_q)
                            if val_q is not None and not isinstance(val_q, list):
                                live_g[k_q] = val_q
                    elif "ThreeStage" in ct or "Krea2" in ct or "EZ_04" in ct:
                        if n_in.get("seed") is not None and not isinstance(n_in.get("seed"), list):
                            live_g["krea2_seed"] = n_in.get("seed")
                    elif "VideoDirector" in ct or "EZ_06" in ct:
                        if n_in.get("frame_rate") is not None and not isinstance(n_in.get("frame_rate"), list):
                            live_g["frame_rate"] = n_in.get("frame_rate")
                    elif "CinemaVault" in ct or "EZ_08" in ct:
                        for k_v in ("upscale_model_name", "detailer_1x_model_name"):
                            val_v = n_in.get(k_v)
                            if val_v is not None and not isinstance(val_v, list):
                                live_g[k_v] = val_v
    except Exception:
        pass

    telemetry_summary = ""
    if bus_out or live_g or (isinstance(suno_pkg, dict) and suno_pkg.get("active")):
        style_t = str(bus_out.get("style_target") or live_g.get("style_target") or "original").strip()
        raw_rat = str(bus_out.get("content_rating_mode") or live_g.get("content_rating_mode") or "Uncensored").strip()
        rating_t = "SFW" if raw_rat.lower().startswith("sfw") else ("NSFW" if "explicit" in raw_rat.lower() else "Uncensored")
        img_seed = bus_out.get("krea2_seed") or live_g.get("krea2_seed") or bus_out.get("compiler_seed") or live_g.get("compiler_seed") or "auto"
        vid_fps = bus_out.get("final_fps", bus_out.get("frame_rate", live_g.get("frame_rate", 24)))
        up_mod = bus_out.get("upscale_model_name") or live_g.get("upscale_model_name") or "None"
        det_1x = bus_out.get("detailer_1x_model_name") or live_g.get("detailer_1x_model_name") or "None"
        cam_lock = "STATIC_LOCK" if bus_out.get("static_camera_lock") else "DYNAMIC"
        stance_k = str(bus_out.get("resolved_stance_key") or live_g.get("subject_stance_posture") or "auto").split(" ")[0]
        choreo_k = str(bus_out.get("resolved_choreo_key") or live_g.get("body_choreography_preset") or "auto").split(" ")[0]
        arc_k = str(bus_out.get("resolved_arc_key") or live_g.get("camera_trajectory_arc") or "auto").split(" ")[0]
        dir3_tag = f" | 🎬 3Axis=[{stance_k}/{choreo_k}/{arc_k}]"
        prism_img = bus_out.get("prism_image_lora_telemetry") or {}
        prism_vid = bus_out.get("prism_video_lora_telemetry") or {}
        prism_lat = bus_out.get("prism_latent_spectral_telemetry") or {}
        prism_tag = (
            f" | 💎 PRISM=[03:{'ON' if prism_img.get('turbo_shield_active') else 'READY'}"
            f"/05:{'ON' if prism_vid.get('video_turbo_shield_active') else 'READY'}"
            f"/07:{prism_lat.get('spectral_restorations_applied', 0)}]"
        )
        omni_b = bus_out.get("omni_reference_bundle")
        omni_tag = (
            f" | 🖼️ OmniRef={omni_b.get('active_count', 0)}/5"
            + ("+SceneVid" if omni_b.get("has_video_scene_template") else "")
            if isinstance(omni_b, dict) and omni_b.get("active")
            else ""
        )
        suno_tag = ""
        if isinstance(suno_pkg, dict) and suno_pkg.get("active"):
            s_name = suno_pkg.get("source_name") or suno_pkg.get("song_title") or "Suno_Master"
            s_bpm = suno_pkg.get("bpm", 124.0)
            s_mod = suno_pkg.get("audio_modality") or (suno_pkg.get("voice_scene_profile") or {}).get("modality", "AUDIO")
            suno_tag = f" | 🎵 Suno={s_name} ({s_bpm} BPM, {s_mod})"
        telemetry_summary = (
            f"📊 LIVE BUS [{active_ver_tag}]: Style={style_t} | Mode={rating_t} | Cam={cam_lock} | Seed={img_seed} | "
            f"FPS={vid_fps} | Upscale={up_mod} | 1xDetailer={det_1x}{dir3_tag}{prism_tag}{omni_tag}{suno_tag}"
        )
        selected_blocks.append(f"### 📊 LIVE CINEMATRIX BUS TELEMETRY\n`{telemetry_summary}`")

    compiled_text = "\n\n".join([b for b in selected_blocks if b]).strip()
    bus_out["ez_version_tag"] = active_ver_tag
    bus_out["studio_note_locale"] = lang
    bus_out["studio_note_topic"] = preset_str
    bus_out["studio_custom_notes"] = user_note_clean
    bus_out["studio_compiled_guide"] = compiled_text

    ui_payload = {
        "version_tag": active_ver_tag,
        "locale": lang,
        "topic_preset": preset_str,
        "custom_notes": user_note_clean,
        "compiled_markdown": compiled_text,
        "telemetry_summary": telemetry_summary,
        "chapters": {**chapters, "changelog": changelog_section_md},
        "all_locales": STUDIO_GUIDE_CHAPTERS,
    }
    return (compiled_text, bus_out, ui_payload)


def register_studio_note_promptserver_routes() -> None:
    try:
        from aiohttp import web
        from server import PromptServer
        ps = getattr(PromptServer, "instance", None)
        if ps is None or getattr(ps, "_ez_studio_note_routes_bound", False):
            return
        ps._ez_studio_note_routes_bound = True

        async def _ez_note_manuals(request):
            try:
                if request.method == "POST":
                    body = await request.json()
                else:
                    body = dict(request.rel_url.query)
            except Exception:
                body = {}
            loc_in = str(body.get("locale") or body.get("note_locale") or "Auto")
            topic_in = str(body.get("topic_preset") or NOTE_TOPIC_PRESETS[0])
            notes_in = str(body.get("custom_notes") or "")
            compiled_md, _b, ui_pay = compile_localized_studio_note_markdown(
                topic_preset=topic_in,
                note_locale=loc_in,
                custom_notes=notes_in,
                cinematrix_bus=None,
            )
            return web.json_response({
                "status": "ok",
                "locale": ui_pay["locale"],
                "topic_preset": topic_in,
                "topic_presets": NOTE_TOPIC_PRESETS,
                "locale_presets": NOTE_LOCALE_CHOICES,
                "locale_choices": NOTE_LOCALE_CHOICES,
                "compiled_markdown": compiled_md,
                "chapters": ui_pay["chapters"],
                "all_locales": STUDIO_GUIDE_CHAPTERS,
            })

        for prefix in ("/ez_cinematrix/note", "/api/ez_cinematrix/note"):
            ps.routes.get(f"{prefix}/manuals")(_ez_note_manuals)
            ps.routes.post(f"{prefix}/manuals")(_ez_note_manuals)
    except Exception:
        pass


register_studio_note_promptserver_routes()
