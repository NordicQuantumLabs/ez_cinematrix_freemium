# 📜 EZ Cinematrix Studio — Officiell Versions- & Uppdateringslogg (CHANGELOG)

- **Aktiv PRO / Core-Version:** `3.9.0-PRODUCTION`
- **Aktiv Freemium Open-Core-Version:** `1.4.0-PRODUCTION`
- **Byggd med EZ Studio DevOps IDP:** `5.5.0-PRODUCTION`
- **Versionsstandard:** `[Major].[Minor].[Hotfix]-[Environment]`
- **Senast uppdaterad (UTC):** `2026-11-15T14:06:16Z`

---

## 🧭 Regler för Versionsnumrering (`[Major].[Minor].[Hotfix]-[Environment]`)

| Nivå | Mönster | När nivån ökas |
| :--- | :--- | :--- |
| **`MAJOR`** | `[X+1].0.0-[ENV]` | Större arkitekturskifte, ny plattformsgeneration eller brytande API-/workflow-ändring. |
| **`MINOR`** | `[X].[Y+1].0-[ENV]` | Nya funktioner, nya portaler/moduler, nya modell-autopiloter (100 % bakåtkompatibla). |
| **`HOTFIX`** | `[X].[Y].[Z+1]-[ENV]` | Kirurgiska buggfixar, tråd-/VRAM-skydd, AST-/sanitizer-fixar och UI-kalibrering. |
| **`Environment`** | `-DEV` / `-STAGING` / `-PRODUCTION` | Anger om releasen körs i intern utvecklingsbädd (`DEV`), verifieringsbädd (`STAGING`) eller skarp drift (`PRODUCTION`). |

---

## 🗂️ Kronologisk Patch- & Versionshistorik (Nyast Överst)

### 🛰️ DevOps `5.5.0-PRODUCTION` + Cinematrix `3.9.0-PRODUCTION` *(Freemium: `1.4.0-PRODUCTION`)* — [MINOR] (2026-11-15)
**Sammanfattning:** Cloudflare R2 Private Vault (ez-cinematrix-pro-vault), Edge License Gatekeeper & Official nordicquantumlabs.com Verification Suite
**Berörda moduler:** `EZ_BIZ_PORTAL/ez_r2_vault_publisher.py`, `EZ_BIZ_PORTAL/ez_storefront_connector.py`, `CLOUDFLARE_EDGE/ez_r2_license_gatekeeper.js`, `CLOUDFLARE_PAGES_SITE/index.html`, `app.py`

**Genomförda åtgärder:**
- Integrated pure-Python S3 Signature V4 Cloudflare R2 publisher (ez-cinematrix-pro-vault) with zero-secret OS $env vault enforcement.
- Added serverless Cloudflare Edge Worker (releases.nordicquantumlabs.com) with X-EZ-License-Key verification, Dual Entitlements, and WebCrypto Stripe/Lemon Squeezy webhooks.
- Published official nordicquantumlabs.com static landing page + EU Directive 2011/83/EU Article 16(m) Refund, Terms, and GDPR Privacy suite.
- Synchronized One-Shot + Hollywood Multi-Scene Cuts and 2-track MIT Freemium vs closed-source .ezbin PRO architecture across all release playbooks.

---

### 🛰️ DevOps `5.4.0-PRODUCTION` + Cinematrix `3.8.0-PRODUCTION` *(Freemium: `1.3.0-PRODUCTION`)* — [MINOR] (2026-11-15)
**Sammanfattning:** Dual Storefront (Stripe + Lemon Squeezy), PRO Binary Armor (.ezbin) & Bas/Gold Licensmodell
**Berörda moduler:** `EZ_BACKEND/ez_pro_binary_armor.py`, `EZ_LICENSE/ez_client_guardian.py`, `EZ_LICENSE/ez_pro_auto_updater.py`, `EZ_BIZ_PORTAL/ez_storefront_connector.py`, `EZ_BIZ_PORTAL/ez_commerce_engine.py`, `app.py`

**Genomförda åtgärder:**
- Infört asymmetrisk ECDSA-P256 + RSA-2048 V3 klientverifiering i ez_client_guardian.py helt utan MASTER_SALT.
- Kompilerat alla PRO-moduler i ez_cinematrix_pro_v3.5.zip till AST-strippade binära .ezbin kodobjekt (0 läsbara .py-källfiler).
- Stöd för både PRO Bas (Perpetual v3.x + 12 mån uppdateringar + kritiska hotfixar) och PRO Gold/VIP (Livstids alla uppdateringar v3.x/v4.x+) samt signerad PRO Auto-Updater.
- Integrerat både Stripe (/v1/products, /v1/prices, /v1/payment_links) och Lemon Squeezy (/v1/variants, /v1/checkouts) med HMAC-SHA256 webhooks och OS $env nyckelhantering.

---

### 🚀 `3.7.0-PRODUCTION` *(Freemium Open-Core: `1.2.0-PRODUCTION`)* — [MINOR] (2026-11-15)
**Sammanfattning:** Generell One-Shot & Hollywood Multi-Scene Cuts Regi + Fönster 6 Solver-Stabilisering
**Berörda moduler:** `engine_ez_02_cinematrix_qwenvl_timeline.py`, `engine_ez_06_cinematrix_video_director.py`, `engine_ez_07_cinematrix_joint_av_sampler.py`, `ez_cinematrix_theme.js`

**Genomförda åtgärder:**
- Införde 100 % promptstyrd och domänagnostisk scene_continuity_mode (auto_from_prompt, locked_stage_environment, continuous_one_shot, hollywood_multi_scene_cuts) i EZ [02], EZ [06], EZ [07] och 7-språks UI.
- Eliminerade rekursiv (<Subject 1>), <Subject 1>- carryover och avklippta meningsfragment vid 6-fönsters (30 s) kompilering i EZ [02] och EZ [06].
- Införde C1-mjuka cosinus-sigma-ramper, tvingad FP32-ackumulering på fortsättningsfönster (win_idx >= 1), automatisk euler-step-guard vid låga steg samt självläkande HF-kollapsdetektor i EZ [07] mot Fönster 6-flimmer.
- Lade till rullande RGB-handoff för obrutna One-Shot-åkningar samt skarpa filmklipp med bibehållen cosinus-ljudcrossfade och REF2VA karaktärsankare för Hollywood Multi-Scene Cuts.

---

### 🚀 `3.6.1-PRODUCTION` *(Freemium Open-Core: `1.1.1-PRODUCTION`)* — [HOTFIX] (2026-11-14)
**Sammanfattning:** Ref2VA Kompositionslås, Fönster-Handoff, 2D Viseme Jaw Soft-Ceiling & Prompt-Sanitizer Hotfix
**Berörda moduler:** `engine_ez_02_cinematrix_qwenvl_timeline.py`, `engine_ez_06_cinematrix_video_director.py`, `engine_ez_07_cinematrix_joint_av_sampler.py`, `engine_ez_11_cinematrix_studio_note.py`

**Genomförda åtgärder:**
- EZ [06] Ref2VA Utsnittsskydd: Stoppade auto-injektion av full-frame uttänjda ansikts-/torso-klipp vid singelbilds-Ref2VA och kodade in ref2va_w0_kf_latent så att Fönster 0 behåller exakt master-komposition utan halvkropps-inzoomning.
- EZ [07] Ref2VA Fönster-Handoff: Aktiverade t=0 latent tail-lås i Ref2VA (if (not is_h3_24c) or is_ref2va_lock:) och normaliserade (1, H, W, 3) referens-tensorer för sömlösa 5s/10s/15s-övergångar.
- EZ [07] 2D Viseme-Fix & Jaw Soft-Ceiling: Åtgärdade IndexError på 2D vis_cpu (4, T_lat) som tidigare avbröt suno_aud_cpu 0.98 ljud-latentlåsning i steg 1..7, samt införde 0.58 * tanh(jaw / 0.58) mjuk käkkompression mot onaturligt gapande käkar.
- EZ [02] SFW Idiom-Skydd & Stilkollisions-Läkning: Undantog 'lust for life' i _scrub_nsfw_terms_for_sfw, införde _reconcile_custom_negative_style_collision vid byte från realism till semi-real/anime samt frontal ögonkontakt vid sång.

---

### 🚀 `3.6.0-PRODUCTION` *(Freemium Open-Core: `1.1.0-PRODUCTION`)* — [MINOR] (2026-11-13)
**Sammanfattning:** Multi-Arkitektur Autopilot (Illustrious, Pony, SDXL, Flux) & Civitai Direktuppslag i EZ [03]/[04]/[10]
**Berörda moduler:** `engine_ez_03_cinematrix_image_lora_splitter.py`, `engine_ez_04_cinematrix_krea2_sampler.py`, `engine_ez_10_cinematrix_civitai_controller.py`, `ez_cinematrix_theme.js`

**Genomförda åtgärder:**
- Öppnade stage2_steps = 0 (min: 0) och handoff_percent = 100.0 % i EZ [04] för äkta 1-stegs Single-Stage-exekvering utan onödig Steg 2-polering.
- Byggde EZ-04-MULTIARCH-AUTO autopilot för Illustrious XL (28 steg, CFG 4.5, euler_ancestral/karras), Pony V6 XL (CFG 5.5), SDXL 1.0 (CFG 5.0), DMD2 (8 steg, CFG 1.2) och Flux.1 Dev/Schnell (CFG 1.0) medan Krea 2 behålls som 3-stegs huvudfokus.
- Införde automatisk 4-kanals upplösningsbegränsning (>1.35 MP -> ~1.1 MP) i EZ [04], automatisk CLIP/VAE-parning (CLIP Skip -2 Dual CLIP-L/G resp. T5-XXL) och korsarkitektur-LoRA-filter i EZ [03].
- Uppgraderade EZ [10] Civitai Hub med fullständig versionslista (upp till 40 versioner inkl. WAI-illustrious v14–v17), filnamns-alias (waiNSFWIllustrious -> #827184) samt direkt #ModelID- och URL-uppslag.

---

### 🚀 `3.5.0-PRODUCTION` *(Freemium Open-Core: `1.0.0-PRODUCTION`)* — [MAJOR] (2026-11-10)
**Sammanfattning:** Sovereign 14-Node Audio-Reactive Studio, PRISM SVD & Open-Core Unlimited Lansering
**Berörda moduler:** `EZ [01]–[14] Core Suite`, `EZ Model Foundry (Station 1–5)`, `EZ Licensing & Launch Orchestrator`

**Genomförda åtgärder:**
- Lanserade den kompletta 14-noders enkelkabel-arkitekturen (CINEMATRIX_BUS) med EZ [14] 0-VRAM Pipeline Switchboard (Image Only / Full Studio / Direct I2V).
- Införde PRISM Orthogonal SVD LoRA-projektion och EZ-03/EZ-05-TURBO-GUARD som automatiskt kopplar ur externa Turbo-LoRAs på fördestillerade modeller (SingularityV2, PikaFlex, 10Eros, FastH3).
- Integrerade EZ [12] Suno v4/v5 + lokal Whisper ASR läppsynk samt EZ [08] Cinema Vault med kantstyrd Lanczos, 4x->2x Supersampling, 1x Skin Detailer och RIFE IFNet.
- Etablerade MIT Open-Core Freemium (obegränsad flerfönster-videolängd utan .enc-filer) parallellt med krypterad Drop-In PRO Unlocker (allan_ballan_core.enc + signature.enc).

---
