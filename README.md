# 🎬 ComfyUI — EZ Cinematrix Studio Suite (v1.0 Free Unlimited / PRO v3.5)

![Version](https://img.shields.io/badge/EZ_Cinematrix-v1.0_Open_Core_%7C_PRO_v3.5-00f0ff?style=for-the-badge)
![Publisher](https://img.shields.io/badge/Publisher-Nordic_Quantum_Labs-6366f1?style=for-the-badge)
![ComfyUI Registry](https://img.shields.io/badge/ComfyUI_Manager-MIT_Open_Source-10b981?style=for-the-badge)
![Languages](https://img.shields.io/badge/Locales-EN_%7C_SV_%7C_%E4%B8%AD%E6%96%87_%7C_%E6%97%A5%E6%9C%AC%E8%AA%9E_%7C_ES_%7C_DE_%7C_FR-a855f7?style=for-the-badge)

**EZ Cinematrix** (by **Nordic Quantum Labs**) is an end-to-end **14-Node Audio-Reactive Virtual Production, Keyframe Image & Unlimited Multi-Window Joint Audio-Video VFX Suite** for ComfyUI. Engineered for zero-spaghetti orchestration across **Krea 2**, **Flux.1**, **Illustrious XL / Pony / SDXL**, **MiniMax H3**, **Wan 2.2**, **LTX-2.3**, **Suno v5**, and **Qwen3-VL**.

---

## ⚡ Key Highlights

- **🎛️ Native `EZ [14] Pipeline Switchboard & Fast Bypass Remote`**: Switch your entire studio rig between **`🖼️ IMAGE ONLY`**, **`🎬 FULL STUDIO`**, and **`🎞️ VIDEO ONLY (Direct I2V)`** in a single click — plus individual LED toggles for `[02] Qwen3-VL`, `[03-04] Krea 2`, `[05-08] Video`, `[12] Suno Music`, `[13] Omni-Ref`, and `[09] Anatomy Dock`. Zero `rgthree` dependency required.
- **🎨 3-Stage Krea 2 & Plug-and-Play Illustrious XL Keyframe Studio (`[03]`, `[04]`)**: Precision `0.01`-increment sliders, True Flat 2D Cel-Anime stylized rendering, Dual Dark-Fantasy modes (`dark-fantasy-real` live-action 35mm & `dark-fantasy-cgi` pre-rendered VFX cutscene), and automatic Illustrious/SDXL + DMD2 detection.
- **🧠 3-Axis Universal Director — Unbroken One-Shot & Hollywood Multi-Scene Cuts (`[02]` & `[06]`)**: Direct seamless 60s+ single-take steadicam sequences OR frame-accurate multi-scene editorial cuts (`Establishing Wide -> Subject A Dialogue -> Subject B Reaction -> Climax Cut`) across unlimited multi-act storylines with Multi-Band Laplacian Contrast Stabilization (zero HDR/sepia burn).
- **💎 PRISM Orthogonal SVD & `EZ-05-TURBO-GUARD` (`[03]`, `[05]`, `[07]`)**: Automatically detects baked-in step-distilled checkpoints (`PikaFlex`, `10Eros`, `DaSiWa`, `DMAD`) so external Turbo LoRAs never double-stack and burn skin tones, while projecting secondary LoRAs orthogonally away from your primary identity slot.
- **📝 Interactive `EZ [11]` MiniMax H3 Model, VAE, CLIP & LoRA Handbook**: Built-in 7-language model guide curated for **16GB RTX 5070 Ti / 24GB GPUs** with 1-click links to `https://huggingface.co/DeepBeepMeep/MiniMax-H3/tree/main`.
- **🌍 7 Built-In Studio Languages & Self-Healing `.zip` Installer**: Instant live UI switching (`EN | SV | 中文 | 日本語 | ES | DE | FR`) plus a self-healing root `__init__.py` shim that protects against nested double-folder extraction in `ComfyUI/custom_nodes/`.

---

## 🗂️ The 14-Node Sovereign Architecture

| Node ID | Node Name | Core Function |
| :--- | :--- | :--- |
| **`EZ [01]`** | **Canvas & Aspect Ingest** | Master resolution, aspect ratio, hardware tier profile & reference image ingest |
| **`EZ [02]`** | **Qwen3-VL Story & Timeline Compiler** | Multimodal VLM compiler for One-Shot & Multi-Scene Cuts with 100% node authority on Age, Zoom & Style |
| **`EZ [03]`** | **Image Model & Dual-Stage LoRA Splitter** | Loads Krea 2 / Flux.1 / Illustrious XL + 4-Slot PRISM Orthogonal LoRA stack & Stage-2 Turbo |
| **`EZ [04]`** | **Krea 2 Three-Stage Keyframe Sampler** | 3-Stage T2I/I2I sampler with `0.01`-step handoff, Frequency Skin Polish & 12-Person Anatomy Lock |
| **`EZ [05]`** | **Video Engine & Motion LoRA Stack** | Loads MiniMax H3 / Wan 2.2 / LTXV + 4-Slot Video/Audio/CLIP LoRA stack |
| **`EZ [06]`** | **Video Director & Keyframe Bridge** | Synthesizes Start/Mid/End keyframes, 3-Axis camera/choreography & multi-scene cut timeline |
| **`EZ [07]`** | **Joint AV Temporal Sampler** | Audio-reactive 5D video + 4D audio latent sampler with live MiniPyAV preview |
| **`EZ [08]`** | **Cinema Vault & 4x➔2x + RIFE Master** | Decodes & muxes 48kHz Stereo Suno / 32kHz H3 audio with 4x➔2x supersampling, 1x Skin Detailer & RIFE |
| **`EZ [09]`** | **Neural Anatomy & Motion Physics Dock** | 6-Zone anatomical protection & optical-flow motion continuity lock |
| **`EZ [10]`** | **Civitai & Model Hub Controller** | Built-in Web-Studio for local model management, Civitai live search, downloads & saved recipes |
| **`EZ [11]`** | **Studio Note, How-To & Model Guide** | Interactive 7-language Studio Handbook & live pipeline telemetry |
| **`EZ [12]`** | **Suno Music Video & Whisper ASR Studio** | Imports Suno v4/v5 tracks, extracts BPM/stem envelopes & runs Whisper ASR lyric lip-sync |
| **`EZ [13]`** | **Omni-Reference 4-Slot Image Studio** | 4-Slot reference loader (Pose/Master, Face-ID, Clothing/Armor, Background) + Slot 5 Motion Video |
| **`EZ [14]`** | **Pipeline Switchboard & Fast Bypass** | 1-Click Remote Control (`Image Only` / `Full Studio` / `Video Only`) + 6 live module bypass switches |

---

## 🚀 1-Click Installation & Quick Start

1. **Install via ComfyUI-Manager / Comfy Registry**: Search for **`EZ Cinematrix Studio Suite`** (`ez_cinematrix_freemium`) and click **Install** — or clone directly into `ComfyUI/custom_nodes/`:
   ```bash
   cd ComfyUI/custom_nodes
   git clone https://github.com/NordicQuantumLabs/ez_cinematrix_freemium.git
   pip install -r ez_cinematrix_freemium/requirements.txt
   ```
2. **1-Click Auto-Build**: Right-click anywhere on the ComfyUI canvas and select **`⚡ Auto-Build & Wire Full EZ Cinematrix Pipeline (1-Click)`** — or drag any of the 3 ready-made workflows from **`examples/`** directly onto ComfyUI!

---

## 🔓 Two-Track Architecture: Freemium Open-Core vs. 🔒 Standalone PRO Studio

| Feature | Freemium Open-Core (MIT / Free) | PRO Bas (Perpetual v3.x + 12m Updates) | PRO Gold VIP (Lifetime All Versions) |
| :--- | :---: | :---: | :---: |
| **All 14 Studio Nodes (`[01]`–`[14]`) & Switchboard** | ✅ Included | ✅ Compiled `.ezbin` PRO | ✅ Compiled `.ezbin` PRO |
| **Max Video Timeline Duration** | **✅ Unlimited Multi-Window** | **✅ Unlimited Multi-Window** | **✅ Unlimited Multi-Window** |
| **One-Shot & Multi-Scene Cut Routing** | Standard Manual Timeline | **✅ Automated Multi-Scene Cut Compiler** | **✅ Automated Multi-Scene Cut + 2-Speaker Routing** |
| **VLM System Matrix (`EZ [02]`)** | Editable `system_prompt_light.txt` | **✅ Encrypted `allan_ballan_core.enc`** | **✅ Encrypted `allan_ballan_core.enc`** |
| **Distribution & Update Channel** | GitHub & ComfyUI Manager | **Private Signed R2 Auto-Updater (12m + v3 Hotfixes)** | **Private Signed R2 Auto-Updater (Lifetime v3/v4/v5+)** |

### ⚡ Official Website, Commercial PRO & Support
- **Official Portal & Editions:** [https://nordicquantumlabs.com](https://nordicquantumlabs.com)
- **Global Storefront:** [https://nordicquantumlabs.lemonsqueezy.com](https://nordicquantumlabs.lemonsqueezy.com)
- **Support & Creator VIP Desk:** `support@nordicquantumlabs.com` · `vip@nordicquantumlabs.com`
