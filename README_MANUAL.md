# 🎬 EZ Cinematrix Core Suite v2.6 — Official Studio Manual & Architecture Guide

**Default Interface Locale:** `EN` (English — switchable live to `SV`, `ES`, `DE`, `FR`, `ZH` via the `🌐 EN` pill on any node header or right-click menu).  
**Target Hardware Profile:** Windows 11 / Linux • NVIDIA RTX 5070 Ti / RTX 4090 / RTX 3090 (12 GB – 24 GB+ VRAM) • AMD Ryzen 7 9800X3D.

---

## ⚡ 1. Quick Start & 1-Click Auto-Wire (`[01]` ➔ `[13]`)

1. **1-Click Full Pipeline Setup:**  
   Right-click any EZ Cinematrix node on the ComfyUI canvas and select:  
   `⚡ Auto-Skapa & Koppla hela EZ Cinematrix-flödet (1-Klick)`  
   This automatically spawns, arranges, and wires all **13 EZ Cinematrix nodes**:
   - **`🌐 EZ [10] Civitai Asset Browser, Recipe Hub & Download Manager`**
   - **`📝 EZ [11] Studio Notes, How-To & Model Handbook`**
   - **`🎵 EZ [12] Suno Music Video, Beat-Cut & Lyrics Studio`**
   - **`🖼️ EZ [13] Omni-Reference Load Image & Control Studio (4-in-1 Multi-Ref)`**
   - **`📐 EZ [01] Canvas Ingest, Multi-Ref & Aspect Ratio Pad`**
   - **`🧠 EZ [02] Qwen3-VL Timeline, Style & Prompt Compiler`**
   - **`🧬 EZ [03] Krea 2 / Flux / SDXL Dual-Stage Image Model & LoRA Splitter`**
   - **`🎨 EZ [04] Krea 2 Three-Stage Keyframe Sampler (T2I & I2I)`**
   - **`🎞️ EZ [05] MiniMax H3 / Wan 2.2 / LTXV Video Engine & LoRA Stack`**
   - **`🎬 EZ [06] Video Director, Timeline Cuts & Multi-Segment Guide`**
   - **`⚡ EZ [07] Joint Audio+Video Temporal Sampler (MiniPyAV Live HUD)`**
   - **`🏛️ EZ [08] Cinema Vault, 4x➔2x Supersampling, 1x Skin Detailer & RIFE IFNet`**
   - **`🦴 EZ [09] Neural Anatomy & Skeletal Rigging Lock Dock`**

2. **Clean Signal & Resolution Routing (`[01]` ➔ `[03]`, `[04]`, `[06]`, `[09]`, and `[10]`):**  
   - **Resolution Routing (`base_width`/`base_height` vs `final_width`/`final_height`):**
     - `base_width` and `base_height` from `EZ [01]` wire **only** to `EZ [03]` and `EZ [04]` (for Stage 1 base sampling prior to 1.5x/2x latent upscaling). They must **never** be wired to `EZ [06] Video Director`.
     - `final_width` and `final_height` from `EZ [01]` wire to `final_width`/`final_height` on `EZ [04]` **AND** to `video_width`/`video_height` on `EZ [06] Video Director` so the video engine always matches the full upscaled keyframe resolution.
   - `EZ [03]` connects `stage1_model`, `stage2_model`, `image_clip`, and `image_vae` to `EZ [04]`, while `EZ [02]` connects `krea2_image_prompt` and `adaptive_negative_prompt` directly to `EZ [04]`. The two orange fallback `CONDITIONING` ports (`positive` / `negative`) between `[03]` and `[04]` are intentionally left disconnected during 1-Click Auto-Wire unless you use custom external conditioning nodes.
   - `EZ [09] Anatomy Dock` is automatically wired to both `EZ [04]` and `EZ [08]`.
   - `EZ [10] Civitai Controller` is automatically wired to `EZ [03]` (`image_model_spec` / `image_lora_spec`) and `EZ [05]` (`video_model_spec` / `video_lora_spec`).

---

## 🖼️ 2. EZ [13] Omni-Reference 5-Slot Studio (Character Ref `[1]–[4]` + Video Scene Template `[5]`) & EZ [14] Switchboard

`EZ [13]` consolidates **4 reference image slots (`[1]–[4]`)** and **1 reference video + audio slot (`[5]`)** into a single studio hub with automatic architectural role splitting when both images and video are active:

### 🎯 Architectural Role Split (`Slot [1]–[4]` Character Identity vs `Slot [5]` Video Scene Template)
- **When `Slot [5]` (Reference Video) is active alongside `Slot [1]`:**
  1. **`Slot [1]`–`[4]` (Main Character Identity & Appearance for `<Subject 1>`):** `EZ [13]` extracts a head-and-shoulders character identity crop (`slot1_character_ref_image`) and exact facial/body skin pigment vector (`slot1_skin_rgb = [R, G, B]`) from `Slot [1]`, discarding `Slot [1]`'s standing posture, weapons, and background so they never conflict with the video scene.
  2. **`Slot [5]` (Reference Video Scene, Camera, Posture, Motion & Audio Template):** The reference video frame at `slot5_start_offset_sec` (e.g., `129.0s`) becomes `master_composite_image`, driving **100% of the spatial scene layout, desk/studio composition, camera angle, Depth-Anything 3D, and OpenPose 17J skeleton** in `EZ [13]`, `EZ [02]` (Image #1 = Character Ref, Image #2 = Video Scene Template), and `EZ [04]` (Krea 2 scene-guided keyframe sampling with pre-sampling and post-decode **Skin Chromaticity Harmonizer**).

### 🟠 SECTION 1–4 — IMAGE REFERENCE SLOTS (`slot1_master_image` .. `slot4_background_image`)
- **Slot 1 (`[1] MASTER / INPAINT / POSE / CANNY / TEMPORALNET`):** Primary composition/pose when used standalone, or Main Character (`<Subject 1>`) species/skin/facial reference when `Slot [5]` is active.
- **Slot 2 (`[2] PERSON / REACTOR FACE-ID / ADETAILER / LIVEPORTRAIT`):** Identity preservation, LAB face transfer, and high-pass iris sharpening.
- **Slot 3 (`[3] CLOTHING / OOTDIFFUSION / LAYERDIFFUSION GARMENT`):** Virtual try-on and garment transfer.
- **Slot 4 (`[4] BACKGROUND / DEPTH-ANYTHING / MIDAS / CONTROLNET TILE`):** 3D depth geometry and horizon relighting.

### 🎬 SECTION 5 — REFERENCE VIDEO, SCENE TEMPLATE, MOTION CAPTURE & AUDIO (`slot5_reference_video`)
- **Supported Formats & Zero File-Size Limit:** `.mp4`, `.mkv`, `.webm`, `.mov`, `.avi`, `.gif`, `.webp` via streaming `PyAV`/`OpenCV` seek directly to `slot5_start_offset_sec` (only the active window is decoded into RAM).
- **Duration in Seconds (`slot5_duration_mode` & `slot5_duration_seconds`):**
  - `follow_master_duration (Följ Master-Tidslängd [02] / [06] — Auto)` *(Default)*: Automatically reads `master_duration` (`20s`, `30s`, `60s`) from `EZ [02]`/`[12]`—no frame counting required.
  - `custom_seconds`: Uses `slot5_duration_seconds` starting at `slot5_start_offset_sec`.
  - `full_video_from_offset`: Extracts the remainder of the video from `slot5_start_offset_sec`.
- **Audio & Motion Routing to `EZ [06]`:** Automatically passes `reference_motion_video` and `reference_video_audio` via `cinematrix_bus` to `EZ [06]` for motion driving and lip-sync.

### 🎛️ EZ [14] Cinematrix Pipeline Switchboard (Remote Control)
- Provides 1-click preset buttons (`full_studio_image_and_video`, `image_only_krea2_studio`, `video_only_minimax_from_source`, `custom_manual_switches`) and per-module toggles to bypass inactive stages with 0 MB wasted VRAM.

---

## 🧠 3. EZ [02] & EZ [06] 3-Axis Universal Director, Multi-Act Story Progression & Camera Trajectories

1. **System Prompt Licensing (`allan_ballan_core.enc` vs `system_prompt_light.txt`):**
   - When a valid license is present (`signature.enc` or `CONFIG/devops_master_license.enc`), `EZ [02]` automatically decrypts `allan_ballan_core.enc` in RAM (`PRO_LICENSED // allan_ballan_core.enc`) in both **NSFW** and **SFW** modes.
   - When no active license is found, `EZ [02]` automatically loads `system_prompt_light.txt` (`FREEMIUM_LIGHT // system_prompt_light.txt`).
2. **3-Axis Universal Director (`subject_stance`, `choreography_style`, `camera_trajectory_arc` in `EZ [02]` & `EZ [06]`):**
   - **Axis 1 — Subject Stance (`subject_stance`):** Controls posture and center-of-gravity anchoring (`Auto`, `Standing / Upright`, `Sitting / Seated`, `Lying / Reclining`, `Kneeling / Crouched`, `Vehicle / Cockpit Seated`, `Multi-Character Mixed (Stand + Sit + Background)`).
   - **Axis 2 — Choreography & Crowd Engine (`choreography_style`):** Controls movement dynamics (`Auto`, `Beat-Synced Dance / Heavy Footwork`, `Forward Sprint / Chase`, `Social / Tavern / Dialogue`, `Epic Melee Battle / Crowd Combat`, `NSFW Solo / Tease`, `NSFW Duo / Coupled`, `NSFW Group / Multi-Partner`, `Vehicle Entry & Takeoff Transition`).
   - **Axis 3 — Camera Trajectory Arcs (`camera_trajectory_arc`):**
     - **Pure Backward Tracking (`Low->High`, `Mid->Low`, `High->Mid`, `Level`):** Keeps the camera facing the character's front while retreating smoothly with natural optical flow parallax (`enable_parallax_flow = True`), maintaining 100% facial identity throughout the shot.
     - **Outro Backward Track ➔ 180° Follow (`Low->High`, `Mid->Mid`, `High->Low`):** Starts facing the character in a backward track and arcs 180° around to follow behind the character during the final 35% (`arc_progress >= 0.65`) — ideal as an epic **closing sequence (outro)** where shifting from face to back-silhouette looks cinematic.
     - **Sci-Fi / Cybernetic Crane Ascent (`Street-Level Walk ➔ Vehicle Entry ➔ Aerial Cityscape Crane Ascent`):** Elevates the camera from street level up into an aerial cityscape reveal.
3. **Multi-Act Story Progression (`->`, `➔`, `then`, `sedan`):**
   - Write multi-stage transitions directly in `user_input` (e.g., *"cyborg walks through neon rain street -> enters flying spinner car -> lifts off into dense Blade Runner aerial traffic"*). `EZ [02]` and `EZ [06]` split the prompt into chronological acts (`Act 1`, `Act 2`, `Act 3`) and bind each act to the corresponding `[MM:SS - MM:SS]` timeline segments and `Start / Mid / End` keyframes (`[04]` ➔ `[06]` ➔ `[07]`).
4. **True Static Camera Lock (`static_camera_lock`) vs. Dynamic Camera Motion (`EZ [02]`, `EZ [06]`, `EZ [07]`):**
   - When a static tripod preset is selected and `camera_trajectory_arc` is static, `static_camera_lock = True` enforces `motion_bucket_id = 0` and locks background/horizon latents in `EZ [07]`. Selecting any dynamic camera preset, trajectory arc, or forward locomotion automatically enables dynamic background optical flow (`static_camera_lock = False`).
5. **100% Priority for Reference Images & `style_target` Over Suno Tags:**
   - Visual medium and aesthetic style are governed **exclusively** by `style_target` in `EZ [02]` and the reference images loaded in `EZ [13]` / `EZ [01]`.

---

## 🎨 4. EZ [04], EZ [07] & EZ [08] 12-Person Keypoint R-CNN, Beat Velocity Gain & Detail Restorer

`EZ [04]`, `EZ [07]`, and `EZ [08]` combine a **3-Stage Keyframe Pipeline**, **Manifold-Preserving Beat Velocity Gain**, and **12-Person Keypoint R-CNN** anatomical shielding:
- **Stage 1 (Base Composition — `stage1_model` Q8) ➔ Latent Bislerp Upscale ➔ Stage 2 (PRISM Turbo-Shielded LoRA) ➔ Stage 3 (High-Resolution Detail Polish — `stage1_model` Q8).**
- **Manifold-Preserving Beat Velocity Gain (`EZ [07]`):** On Suno/audio transient peaks (kick/snare), `EZ [07]` amplifies temporal motion strictly along the model's own predicted frame-to-frame trajectory (`vf_t_local + (vf_cur - vf_t_local) * gain`) within the subject's anatomical mask—zero synthetic sine-wave noise and zero background jitter.
- **Pass 1 (Zero-VRAM Edge-Directed Lanczos + Multi-Scale High-Pass Detail Restorer in `[04]` & `[08]`):** Restores sub-pixel micro-details ($\sigma_1 = 0.85$ for pores/eyelashes/mucosal micro-textures; $\sigma_2 = 2.1$ for anatomical contours) with anti-halo clipping (`±0.065`).
- **Pass 2 (`4x➔2x Supersampling` + `1x Skin Detailer` + `12-Person KeypointRCNN` 6-Zone Anatomical Shield in `[04]`, `[07]` & `[08]`):**
  - Evaluates up to **12 simultaneous characters** (`range(min(12, ...))`, confidence threshold `0.42`) across `face`, `eyes`, `hands`, `torso`, `pelvic`, and `feet` zones (`4x-ClearRealityV1.pth` + `1x-ITF-SkinDiffDetail-Lite-v1.pth` + native PyTorch `IFNet` RIFE), preventing limb fusion in large battles, tavern scenes, and NSFW duo/group scenes.
- **💡 Pro Tips & Tricks:**
  - **In-Place Dance vs. Forward Sprint:** Use `Standing` + `Beat-Synced Dance` + `Locked-Off Tripod` for stationary footwork (`static_camera_lock = True`), or `Forward Sprint` + `Backward Track (Low -> High)` when the background must rush past the character.
  - **Outro Shots:** Reserve `Outro: Backward Track -> 180° Follow` for the final clip of a scene so the 180° turn naturally transitions to the character's back silhouette without mid-sequence face loss.
  - **NSFW Coupled & Group Precision:** Combine `Sitting`, `Lying`, or `Kneeling` with `NSFW Duo / Coupled` or `NSFW Group / Multi-Partner` and put your primary anatomy/NSFW LoRA in `Slot 1` of `[03]` and `[05]` so PRISM SVD shields it from secondary style/turbo LoRAs.

---

## 🌐 5. EZ [10] Civitai Browser, Download Manager & PRISM Slot Sender

- **Separated Download vs. Send Actions:**
  - **`⬇️ Download Only`:** Downloads the selected checkpoint or LoRA directly to your local `ComfyUI/models/...` disk folder in the background without changing any active node slots.
  - **`📤 Auto-Slot` / `📤+B1..B3` / `📤+V1..V3` / `📤 Send to Model`:** Assigns the selected model or LoRA to the corresponding slot in `EZ [10]` **and** immediately updates the matching widget on `EZ [03]` (Image) or `EZ [05]` (Video), queuing a background download automatically if the file is not yet on disk.
- **PRISM Multi-LoRA Stack Scaling:** Automatically normalizes combined multi-LoRA energy (`88%` for 2 active LoRAs, `78%` for 3 active LoRAs) to prevent latent over-saturation.
- **`⬇️ Downloads` Tab (Live Progress HUD):**
  - Displays every active and completed download with **progress bar (`%`)**, **downloaded MB / total MB**, **real-time speed (`MB/s`)**, and **remaining ETA (`mm:ss`)**, plus an **Aggregate Summary Banner** across all files.

---

## 🛡️ 6. Self-Healing Safetensors Guard (`EZ [03]` & `EZ [05]`)

Before loading any checkpoint or LoRA (`.safetensors`), `EZ [03]` and `EZ [05]` perform a binary header and tensor-offset integrity check:
- If an incomplete or truncated file is detected (preventing `SafetensorError: MetadataIncompleteBuffer`), the corrupted file is automatically quarantined to `.corrupt_part` and the loader seamlessly falls back to the intact model on disk.

---

## 📝 7. EZ [11] Studio Note & Interactive Handbook Window

- Click **`🗖 OPEN HANDBOOK WINDOW`** in the header of `EZ [11]` to open a full-screen interactive handbook reader (`1180 × 820`) with live chapter tabs (`All`, `How-To & [13]`, `Suno & ASR [12]`, `PRISM & Models`, `Lanczos & 4x/1x`, `Camera & Spectral`, `Basics & Foundry`, `Text Output`, and `Scratchpad`).
- Changing `topic_preset` or `note_locale` on `EZ [11]` immediately updates the displayed chapter and language in real time—no external `Preview as Text` node is required.

---

## 💎 8. PRISM Spectral SVD Subspace Alignment, Turbo-Shield & Latent Spectral Lock (`EZ [03]`, `EZ [05]`, `EZ [07]`, `EZ [10]`)

1. **PRISM Multi-LoRA Subspace Orthogonalization (`EZ [03]` & `EZ [05]`):**
   - When stacking a primary character/anatomy/NSFW LoRA in `Slot 1` with secondary style/lighting/motion LoRAs in `Slot 2..3`, PRISM extracts the top-$k$ orthonormal basis ($U_1, V_1$) of `Slot 1` via **Reduced QR + Core $r \times r$ SVD** and projects `Slot 2..3` into the orthogonal complement:
     $$\Delta W_{\text{sec}}^{\perp} = \Delta W_{\text{sec}} - \gamma_{\text{orth}} U_1 U_1^T \Delta W_{\text{sec}} V_1 V_1^T$$
   - Secondary LoRAs never overwrite facial identity, eye geometry, or NSFW micro-anatomy.
2. **PRISM Stage-2 & Video Turbo-Shield (`EZ [03]` & `EZ [05]`):**
   - In **`EZ [03]`**, `IMG_krea2_raw_to_turbo_lora` (`0.90` in `stage2_model`) is projected orthogonally away from the combined subspace of `style_lora_1..3` (`orth_gamma = 0.78`), preventing Stage 2 Turbo distillation from washing out skin pores or intimate anatomical details.
   - In **`EZ [05]`**, `VID_minimax_h3_turbo_v4_step600_pruned_comfyui` (`1.00`) is projected orthogonally away from `video_lora_1..3` (`orth_gamma = 0.82`) on both `FL2VA` and `Ref2VA` models so a `0.25` detail/character/NSFW LoRA retains 100% micro-detail.
3. **PRISM Latent Spectral Energy & Principal Subspace Lock (`EZ [07]`):**
   - Extracts the per-channel singular value spectrum ($\Sigma_0$) of `Frame 0` (`master_kf_latent`) and restores high-frequency tail singular values ($S_t[k_{\text{mid}}:] \leftarrow \max(S_t, \alpha \Sigma_0)$) during `post_cfg_function` (`0.20 <= sigma <= 0.72`) and across multi-window handoffs (`Window 1 ➔ 2 ➔ N`), eliminating distant facial/detail blur in `medium-wide` and `wide` shots.

---

## 🏛️ 9. EZ Model Foundry & LoRA Lab (`EZ_BACKEND` & `python_embedded`)

- **5-Station DevOps Model Foundry (`EZ_BACKEND/ez_model_foundry_engine.py` & `EZ_DEV_PORTAL/ez_model_foundry_module.py`):**
  1. **Station 1 — Dataset Curation & Qwen3-VL Auto-Captioning**
  2. **Station 2 — LoRA / DoRA Training (`sd-scripts` / `ai-toolkit` / `musubi-tuner`)**
  3. **Station 3 — PRISM Gold Epoch Selection & SVD Tail Denoising:** Evaluates checkpoints using **Effective Rank Entropy ($H_{\text{eff}}$)** and **Condition Number ($\kappa = \sigma_1 / \sigma_k$)**, and strips the bottom 25% noisy singular value tail from `.safetensors` LoRA files via Reduced QR + Core $r \times r$ SVD.
  4. **Station 4 — PRISM Orthogonal SVD Surgical Model Merge (`PRISM_ORTHOGONAL_SVD`)**
  5. **Station 5 — Blackwell `NVFP4` & `Int8 ConvRot` Hadamard Quantization**
- **3-Tier Hardware Acceleration & `python_embedded` Sync:**
  - Automatically selects `PyTorch cuSOLVER/MKL` (GPU/CPU) ➔ `SciPy/NumPy C-LAPACK gesdd` ➔ `Pure-Python Gram-Schmidt`.
  - Both `D:\EZ_Studio_DevTools\requirements.txt` and `DEV_BEDS/comfyui_node/ez_cinematrix_core/requirements.txt` + `install.py` automatically provision `numpy>=1.26.0`, `scipy>=1.11.0`, `safetensors>=0.4.3`, and `Pillow>=10.3.0` inside `python_embedded\python.exe`.

