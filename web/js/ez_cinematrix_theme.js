// -*- coding: utf-8 -*-
// FILENAME: ez_cinematrix_theme.js
// DESCRIPTION: Official ComfyUI Frontend Theme Extension for EZ Cinematrix Core Suite.
// Applies Timeline Compiler Obsidian (#0c0d12 / #13151a) & Cyan Neon (#00f0ff) styling,
// Sampler-Exclusive MiniPyAV Preview, and Civitai Controller & 30d Cache Hub.

import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const EZ_SUITE_VERSION = "v2.6";
const EZ_THEME_PALETTE = {
    default: { color: "#0c0d12", bgcolor: "#13151a", boxcolor: "#00f0ff", badge: "EZ CORE v2.6", badgeColor: "#00f0ff" },
    civitai: { color: "#0c0d12", bgcolor: "#13151a", boxcolor: "#eab308", badge: "ZONE 0 // CIVITAI HUB v2.6", badgeColor: "#facc15" },
    omni:    { color: "#0c0d12", bgcolor: "#13151a", boxcolor: "#06b6d4", badge: "ZONE 13 // OMNI-REF STUDIO v2.6", badgeColor: "#22d3ee" },
    ingest:  { color: "#0c0d12", bgcolor: "#13151a", boxcolor: "#00f0ff", badge: "ZONE 1 // INGEST v2.6", badgeColor: "#00f0ff" },
    qwenvl:  { color: "#0c0d12", bgcolor: "#13151a", boxcolor: "#a855f7", badge: "ZONE 2 // QWEN3-VL v2.6", badgeColor: "#c084fc" },
    krea2:   { color: "#0c0d12", bgcolor: "#13151a", boxcolor: "#f59e0b", badge: "ZONE 3 // KREA 2 v2.6", badgeColor: "#fbbf24" },
    h3:      { color: "#0c0d12", bgcolor: "#13151a", boxcolor: "#10b981", badge: "ZONE 4 // MINIMAX H3 v2.6", badgeColor: "#34d399" },
    vault:   { color: "#0c0d12", bgcolor: "#13151a", boxcolor: "#ec4899", badge: "ZONE 5 // CINEMA VAULT v2.6", badgeColor: "#f472b6" },
    dock:    { color: "#0c0d12", bgcolor: "#13151a", boxcolor: "#38bdf8", badge: "OPT // ANATOMY DOCK v2.6", badgeColor: "#38bdf8" },
    note:        { color: "#0c0d12", bgcolor: "#13151a", boxcolor: "#22d3ee", badge: "ZONE 11 // STUDIO NOTE v2.6", badgeColor: "#22d3ee" },
    suno:        { color: "#0c0d12", bgcolor: "#13151a", boxcolor: "#e879f9", badge: "ZONE 12 // SUNO MUSIC v2.6", badgeColor: "#f0abfc" },
    switchboard: { color: "#0c0d12", bgcolor: "#13151a", boxcolor: "#a855f7", badge: "ZONE 14 // REMOTE v2.6", badgeColor: "#c084fc" }
};

function stripEzEditionSuffix(typeName) {
    return String(typeName || "").replace(/_(?:PRO|Freemium)$/i, "");
}

function detectEzNodeEdition(nodeOrType) {
    let rawType = "";
    let rawTitle = "";
    let rawCat = "";
    if (typeof nodeOrType === "string") {
        rawType = nodeOrType;
    } else if (nodeOrType && typeof nodeOrType === "object") {
        rawType = String(nodeOrType.type || nodeOrType.comfyClass || nodeOrType.name || "");
        rawTitle = String(nodeOrType.title || nodeOrType.display_name || (nodeOrType.constructor && nodeOrType.constructor.title) || "");
        rawCat = String(nodeOrType.category || (nodeOrType.constructor && nodeOrType.constructor.category) || "");
    }
    if (/_Freemium$/i.test(rawType) || /freemium/i.test(rawType)) return "FREEMIUM";
    if (/_PRO$/i.test(rawType)) return "PRO";
    const regDef = (typeof EZ_NODE_DATA_REGISTRY !== "undefined" && rawType) ? EZ_NODE_DATA_REGISTRY[rawType] : null;
    const catStr = `${rawCat} ${(regDef && regDef.category) || ""}`;
    const dispStr = `${rawTitle} ${(regDef && regDef.display_name) || ""}`;
    if (/freemium/i.test(catStr) || /freemium/i.test(dispStr)) return "FREEMIUM";
    if (/\bpro\b|_pro/i.test(catStr) || /—\s*PRO\b/i.test(dispStr)) return "PRO";
    return "PRO";
}

function resolveEditionNodeType(baseCls, targetEdition) {
    const cleanBase = stripEzEditionSuffix(baseCls);
    const wantEdition = String(targetEdition || "PRO").toUpperCase() === "FREEMIUM" ? "FREEMIUM" : "PRO";
    const lgTypes = (typeof LiteGraph !== "undefined" && LiteGraph.registered_node_types) ? LiteGraph.registered_node_types : {};
    const regMap = (typeof EZ_NODE_DATA_REGISTRY !== "undefined" && EZ_NODE_DATA_REGISTRY) ? EZ_NODE_DATA_REGISTRY : {};
    const isRegistered = (k) => Boolean(lgTypes[k] || regMap[k]);
    const preferredCandidates = wantEdition === "FREEMIUM"
        ? [`${cleanBase}_Freemium`, cleanBase]
        : [cleanBase, `${cleanBase}_PRO`];
    for (const cand of preferredCandidates) {
        if (isRegistered(cand) && detectEzNodeEdition(cand) === wantEdition) {
            return cand;
        }
    }
    const allKeys = new Set([...Object.keys(regMap), ...Object.keys(lgTypes)]);
    for (const k of allKeys) {
        if (stripEzEditionSuffix(k) === cleanBase && detectEzNodeEdition(k) === wantEdition) {
            return k;
        }
    }
    return null;
}

function resolveEzPalette(nodeName) {
    const low = stripEzEditionSuffix(nodeName).toLowerCase();
    if (low.includes("switchboard") || low.includes("14")) return EZ_THEME_PALETTE.switchboard;
    if (low.includes("omni") || low.includes("13")) return EZ_THEME_PALETTE.omni;
    if (low.includes("suno") || low.includes("music")) return EZ_THEME_PALETTE.suno;
    if (low.includes("note") || low.includes("handbook")) return EZ_THEME_PALETTE.note;
    if (low.includes("civitai") || low.includes("controller")) return EZ_THEME_PALETTE.civitai;
    if (low.includes("ingest") || low.includes("canvas")) return EZ_THEME_PALETTE.ingest;
    if (low.includes("qwen") || low.includes("timeline") || low.includes("prompt")) return EZ_THEME_PALETTE.qwenvl;
    if (low.includes("krea") || low.includes("image_model")) return EZ_THEME_PALETTE.krea2;
    if (low.includes("h3") || low.includes("video") || low.includes("director") || low.includes("joint_av")) return EZ_THEME_PALETTE.h3;
    if (low.includes("vault") || low.includes("combine") || low.includes("rtx")) return EZ_THEME_PALETTE.vault;
    if (low.includes("anatomy") || low.includes("dock")) return EZ_THEME_PALETTE.dock;
    return EZ_THEME_PALETTE.default;
}

const EZ_WIRING_GUIDE = {
    "EZCinematrixCivitaiController":             { step: "CTRL NODE [10]", next: "➔ Wire image_model/lora_spec to [03] | video_model/lora_spec to [05] | bus ➔ [11]" },
    "EZCinematrixOmniReferenceLoader":           { step: "OMNI-REF [13]", next: "➔ Wire master_composite_image, person/clothing/background & cinematrix_bus to [01] Canvas Ingest" },
    "EZCinematrixCanvasIngest":                  { step: "STEP 1/8 [01]", next: "➔ Wire image to [02] & [04] | width/height ➔ [03] & [06] | bus ➔ [02]" },
    "EZCinematrixQwenVLTimelineCompiler":        { step: "STEP 2/8 [02]", next: "➔ Wire krea2_image_prompt & adaptive_negative to [04] | timeline/neg ➔ [06] | bus ➔ [03]" },
    "EZCinematrixImageModelAndLoraSplitter":     { step: "STEP 3/8 [03]", next: "➔ Wire stage1_model, stage2_model, image_clip, image_vae & bus to [04] (No orange fallback needed)" },
    "EZCinematrixKrea2ThreeStageSampler":        { step: "STEP 4/8 [04]", next: "➔ Wire keyframe_image to [06] | cinematrix_bus ➔ [14] Switchboard ➔ [05] | (3-Stage T2I & I2I Sampler)" },
    "EZCinematrixVideoEngineAndLoraStack":       { step: "STEP 5/8 [05]", next: "➔ Wire video_model, yellow video_clip, video_vae & audio_vae to [06] & [08] | bus ➔ [06]" },
    "EZCinematrixVideoDirectorAndGuide":         { step: "STEP 6/8 [06]", next: "➔ Wire active_video_model, positive, negative, latent & bus to [07]" },
    "EZCinematrixJointAVTemporalSampler":        { step: "STEP 7/8 [07]", next: "➔ MiniPyAV Live-Sampler! Wire sampled_video_latent & bus to [08] Vault" },
    "EZCinematrixCinemaVaultPostAndCombine":     { step: "STEP 8/8 [08]", next: "➔ MASTER VIDEO PLAYER (Final MP4/MKV + Suno/32kHz Audio + 4x➔2x + 1x Skin + RIFE)" },
    "EZCinematrixNeuralAnatomyContinuityDock":   { step: "ANATOMY [09]", next: "➔ VIDEO DOCK: Wire anatomy_dock to [07] & [08]" },
    "EZCinematrixStudioNoteAndGuide":            { step: "HANDBOOK [11]", next: "➔ Interactive Studio Handbook & Note Node (wire cinematrix_bus [10]➔[11]➔[12])" },
    "EZCinematrixSunoMusicVideoStudio":          { step: "SUNO [12]", next: "➔ Suno API & Audio Beat-Sync Studio (wire cinematrix_bus [11]➔[12]➔[13]➔[01])" },
    "EZCinematrixPipelineSwitchboard":           { step: "SWITCHBOARD [14]", next: "➔ Fast Bypass Remote: 1-Click Image Only [03-04] / Full Studio / Video Only [05-08] + Suno/VLM Toggles" }
};

function showEzFlowchartModal() {
    const old = document.getElementById("ez-cinematrix-flowchart-modal");
    if (old) old.remove();
    const modal = document.createElement("div");
    modal.id = "ez-cinematrix-flowchart-modal";
    modal.style.cssText = "position:fixed;inset:0;background:rgba(5,6,10,0.86);z-index:99999;display:flex;align-items:center;justify-content:center;font-family:monospace;color:#e2e8f0;";
    modal.innerHTML = `<div style="background:#0c0d12;border:2px solid #00f0ff;border-radius:10px;padding:20px;max-width:960px;width:95%;box-shadow:0 0 35px rgba(0,240,255,0.25);">
      <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #1e293b;padding-bottom:10px;margin-bottom:12px;">
        <span style="color:#00f0ff;font-size:15px;font-weight:bold;">🗺️ EZ CINEMATRIX CORE — WIRING GUIDE & FLOWCHART ([01] ➔ [13])</span>
        <button id="ez-close-flow-btn" style="background:#ef4444;color:#fff;border:none;border-radius:4px;padding:4px 10px;cursor:pointer;font-weight:bold;">CLOSE ✕</button>
      </div>
      <div style="font-size:12px;line-height:1.65;background:#13151a;padding:12px;border-radius:6px;border:1px solid #334155;">
        <div><b style="color:#facc15;">[10] Civitai Controller, Download Manager & Recipe Hub</b> ➔ Wire <code>image_model_spec</code> & <code>image_lora_spec</code> to <b>[03]</b> | <code>video_model_spec</code> & <code>video_lora_spec</code> to <b>[05]</b> | <code>cinematrix_bus</code> ➔ <b>[11]</b></div>
        <div><b style="color:#22d3ee;">[11] Studio Note, How-To & Model Guide</b> ➔ Interactive Studio Handbook (6 languages + Full Web Window) | <code>cinematrix_bus</code> ➔ <b>[12]</b></div>
        <div><b style="color:#f0abfc;">[12] Suno Music Video, Beat-Sync & Whisper ASR Studio</b> ➔ Fetches 48 kHz Stereo Master, runs Whisper ASR & auto-prompts if <b>[02]</b> is empty! Wire <code>cinematrix_bus</code> ➔ <b>[13]</b> (or directly to <b>[01]</b>)</div>
        <div><b style="color:#22d3ee;">[13] Omni-Reference Load Image & Control Studio</b> ➔ Unified 4-Slot Reference Loader (Master/Pose/Inpaint, Face-ID/ReActor, Clothing/OOTDiffusion, Background/DepthAnything). Wire <code>master_composite_image</code>, <code>person_reactor_image</code>, <code>clothing_ootd_image</code>, <code>background_depth_image</code> & <code>cinematrix_bus</code> ➔ <b>[01]</b></div>
        <hr style="border-color:#1e293b;margin:8px 0;"/>
        <div><b style="color:#00f0ff;">[01] Canvas & Ingest</b> ➔ <code>image</code> to <b>[02]</b> (<code>reference_image</code>) & <b>[04]</b> (<code>source_image</code>) | <code>base_width/height</code> to <b>[03]</b> & <b>[06]</b> | <code>cinematrix_bus</code> ➔ <b>[02]</b></div>
        <div><b style="color:#c084fc;">[02] Qwen3-VL Timeline (Auto-Load in LM Studio + Strict SFW Guard)</b> ➔ <code>krea2_image_prompt</code> & <code>adaptive_negative_prompt</code> to <b>[04]</b> | <code>video_timeline_prompt</code> & <code>adaptive_negative_prompt</code> to <b>[06]</b> | <code>cinematrix_bus</code> ➔ <b>[03]</b></div>
        <div><b style="color:#fbbf24;">[03] Image Model & LoRA (KREA2 / Flux.1 / SDXL)</b> ➔ Wire <code>stage1_model</code>, <code>stage2_model</code>, <code>image_clip</code>, <code>image_vae</code> & <code>cinematrix_bus</code> to <b>[04]</b> (orange <code>positive</code>/<code>negative</code> fallback ports stay unconnected!)</div>
        <div><b style="color:#fbbf24;">[04] Krea 2 3-Stage Sampler (T2I & I2I/Multi-Ref)</b> ➔ Owns Keyframe Preview! Wire <code>keyframe_image</code> to <b>[06]</b> | <code>cinematrix_bus</code> ➔ <b>[05]</b></div>
        <div><b style="color:#38bdf8;">[09] Neural Anatomy Dock (Video Continuity Dock)</b> ➔ Wire <code>anatomy_dock</code> to <b>[07]</b> & <b>[08]</b></div>
        <hr style="border-color:#1e293b;margin:8px 0;"/>
        <div><b style="color:#34d399;">[05] Video Engine & LoRA (MiniMax H3 / Wan 2.2 / LTXV)</b> ➔ <code>video_model_fl2va/ref2va</code>, <b>yellow <code>video_clip</code></b>, <code>video_vae</code>, <code>audio_vae</code> & <code>cinematrix_bus</code> to <b>[06]</b> (and <code>video_vae/audio_vae</code> to <b>[08]</b>)</div>
        <div><b style="color:#34d399;">[06] Video Director Guide</b> ➔ Syncs <code>master_duration</code> from <b>[02] / [12]</b>! Wire <code>active_video_model</code>, <code>positive</code>, <code>negative</code>, <code>latent_video_audio</code> & <code>cinematrix_bus</code> to <b>[07]</b></div>
        <div><b style="color:#34d399;">[07] Joint AV Temporal Sampler</b> ➔ Owns <b>MiniPyAV Live-Sampler-Preview</b>! Wire <code>sampled_video_latent</code> & <code>cinematrix_bus</code> to <b>[08]</b></div>
        <div><b style="color:#f472b6;">[08] Cinema Vault</b> ➔ Owns <b>🎬 FINAL PRODUCT // MASTER VIDEO PLAYER</b> (muxes 48 kHz Stereo Suno or 32 kHz H3 audio + 4x➔2x Supersampling + 1x Skin Detailer & RIFE IFNet)!</div>
      </div>
    </div>`;
    document.body.appendChild(modal);
    document.getElementById("ez-close-flow-btn").onclick = () => modal.remove();
    modal.onclick = (e) => { if (e.target === modal) modal.remove(); };
}

function autoBuildAndWireCinematrixSuite(triggerNode = null) {
    const graph = app.graph;
    if (!graph) return;
    let targetEdition = "PRO";
    if (triggerNode && typeof triggerNode === "object") {
        targetEdition = detectEzNodeEdition(triggerNode);
    } else if (app.canvas && app.canvas.selected_nodes && typeof app.canvas.selected_nodes === "object") {
        const selList = Object.values(app.canvas.selected_nodes).filter(Boolean);
        const selEz = selList.find(n => String(n.type || "").startsWith("EZ"));
        if (selEz) targetEdition = detectEzNodeEdition(selEz);
    } else if (Array.isArray(graph._nodes)) {
        const firstEz = graph._nodes.find(n => n && String(n.type || "").startsWith("EZ"));
        if (firstEz) targetEdition = detectEzNodeEdition(firstEz);
    }
    const order = [
        ["EZCinematrixCivitaiController", 60, -20],
        ["EZCinematrixStudioNoteAndGuide", 1560, -20],
        ["EZCinematrixSunoMusicVideoStudio", 2620, -20],
        ["EZCinematrixOmniReferenceLoader", -480, 740],
        ["EZCinematrixCanvasIngest", 60, 740],
        ["EZCinematrixQwenVLTimelineCompiler", 540, 740],
        ["EZCinematrixImageModelAndLoraSplitter", 1040, 740],
        ["EZCinematrixKrea2ThreeStageSampler", 1560, 740],
        ["EZCinematrixPipelineSwitchboard", 1560, 1480],
        ["EZCinematrixNeuralAnatomyContinuityDock", 1560, 2040],
        ["EZCinematrixVideoEngineAndLoraStack", 2100, 740],
        ["EZCinematrixVideoDirectorAndGuide", 2620, 740],
        ["EZCinematrixJointAVTemporalSampler", 3160, 740],
        ["EZCinematrixCinemaVaultPostAndCombine", 3720, 740]
    ];
    const map = {};
    for (const [cls, x, y] of order) {
        let node = null;
        if (triggerNode && stripEzEditionSuffix(triggerNode.type) === cls && detectEzNodeEdition(triggerNode) === targetEdition) {
            node = triggerNode;
        }
        if (!node && Array.isArray(graph._nodes)) {
            node = graph._nodes.find(
                n => n && stripEzEditionSuffix(n.type) === cls && detectEzNodeEdition(n) === targetEdition
            );
        }
        if (!node) {
            const targetType = resolveEditionNodeType(cls, targetEdition);
            if (targetType) {
                node = LiteGraph.createNode(targetType);
                if (node) {
                    node.pos = [x, y];
                    graph.add(node);
                }
            }
        }
        if (node) map[cls] = node;
    }
    const ensureInputSlot = (node, inName, fallbackType = "*") => {
        if (!node) return -1;
        let idx = node.findInputSlot(inName);
        if (idx !== -1) return idx;
        if (Array.isArray(node.widgets)) {
            const w = node.widgets.find(x => x && x.name === inName);
            if (w && typeof node.addInput === "function") {
                node.addInput(inName, fallbackType, { widget: { name: inName } });
                idx = node.findInputSlot(inName);
            }
        }
        return idx;
    };
    const disconnectInputSlotIfWired = (dstCls, inName) => {
        const d = map[dstCls];
        if (!d) return;
        const iIdx = d.findInputSlot(inName);
        if (iIdx !== -1 && typeof d.disconnectInput === "function") {
            try { d.disconnectInput(iIdx); } catch (e) {}
        }
    };
    const wire = (srcCls, outName, dstCls, inName) => {
        const s = map[srcCls], d = map[dstCls];
        if (!s || !d) return;
        const oIdx = s.findOutputSlot(outName);
        if (oIdx === -1) return;
        const outType = (s.outputs && s.outputs[oIdx] && s.outputs[oIdx].type) ? s.outputs[oIdx].type : "*";
        const iIdx = ensureInputSlot(d, inName, outType);
        if (iIdx !== -1) s.connect(oIdx, d, iIdx);
    };
    wire("EZCinematrixCivitaiController", "image_model_spec", "EZCinematrixImageModelAndLoraSplitter", "image_model_spec");
    wire("EZCinematrixCivitaiController", "image_lora_spec", "EZCinematrixImageModelAndLoraSplitter", "image_lora_spec");
    wire("EZCinematrixCivitaiController", "video_model_spec", "EZCinematrixVideoEngineAndLoraStack", "video_model_spec");
    wire("EZCinematrixCivitaiController", "video_lora_spec", "EZCinematrixVideoEngineAndLoraStack", "video_lora_spec");
    wire("EZCinematrixCivitaiController", "cinematrix_bus", "EZCinematrixStudioNoteAndGuide", "cinematrix_bus");
    wire("EZCinematrixStudioNoteAndGuide", "cinematrix_bus", "EZCinematrixSunoMusicVideoStudio", "cinematrix_bus");
    wire("EZCinematrixSunoMusicVideoStudio", "cinematrix_bus", "EZCinematrixOmniReferenceLoader", "cinematrix_bus");
    wire("EZCinematrixOmniReferenceLoader", "cinematrix_bus", "EZCinematrixCanvasIngest", "cinematrix_bus");
    wire("EZCinematrixOmniReferenceLoader", "master_composite_image", "EZCinematrixCanvasIngest", "optional_image");
    wire("EZCinematrixOmniReferenceLoader", "person_reactor_image", "EZCinematrixCanvasIngest", "ref_image_2_person");
    wire("EZCinematrixOmniReferenceLoader", "clothing_ootd_image", "EZCinematrixCanvasIngest", "ref_image_3_clothing");
    wire("EZCinematrixOmniReferenceLoader", "background_depth_image", "EZCinematrixCanvasIngest", "ref_image_4_background");
    wire("EZCinematrixCanvasIngest", "image", "EZCinematrixQwenVLTimelineCompiler", "reference_image");
    wire("EZCinematrixCanvasIngest", "image", "EZCinematrixKrea2ThreeStageSampler", "source_image");
    wire("EZCinematrixCanvasIngest", "base_width", "EZCinematrixImageModelAndLoraSplitter", "final_width");
    wire("EZCinematrixCanvasIngest", "base_height", "EZCinematrixImageModelAndLoraSplitter", "final_height");
    wire("EZCinematrixCanvasIngest", "base_width", "EZCinematrixVideoDirectorAndGuide", "video_width");
    wire("EZCinematrixCanvasIngest", "base_height", "EZCinematrixVideoDirectorAndGuide", "video_height");
    wire("EZCinematrixCanvasIngest", "cinematrix_bus", "EZCinematrixQwenVLTimelineCompiler", "cinematrix_bus");
    wire("EZCinematrixQwenVLTimelineCompiler", "krea2_image_prompt", "EZCinematrixKrea2ThreeStageSampler", "krea2_image_prompt");
    wire("EZCinematrixQwenVLTimelineCompiler", "adaptive_negative_prompt", "EZCinematrixKrea2ThreeStageSampler", "adaptive_negative_prompt");
    wire("EZCinematrixQwenVLTimelineCompiler", "video_timeline_prompt", "EZCinematrixVideoDirectorAndGuide", "timeline_prompt");
    wire("EZCinematrixQwenVLTimelineCompiler", "adaptive_negative_prompt", "EZCinematrixVideoDirectorAndGuide", "negative_prompt");
    wire("EZCinematrixQwenVLTimelineCompiler", "cinematrix_bus", "EZCinematrixImageModelAndLoraSplitter", "cinematrix_bus");
    wire("EZCinematrixImageModelAndLoraSplitter", "stage1_model", "EZCinematrixKrea2ThreeStageSampler", "stage1_model");
    wire("EZCinematrixImageModelAndLoraSplitter", "stage2_model", "EZCinematrixKrea2ThreeStageSampler", "stage2_model");
    wire("EZCinematrixImageModelAndLoraSplitter", "image_clip", "EZCinematrixKrea2ThreeStageSampler", "image_clip");
    wire("EZCinematrixImageModelAndLoraSplitter", "image_vae", "EZCinematrixKrea2ThreeStageSampler", "image_vae");
    // Do NOT wire the orange fallback CONDITIONING ports (positive/negative) from [03] to [04]
    disconnectInputSlotIfWired("EZCinematrixKrea2ThreeStageSampler", "positive");
    disconnectInputSlotIfWired("EZCinematrixKrea2ThreeStageSampler", "negative");
    wire("EZCinematrixImageModelAndLoraSplitter", "cinematrix_bus", "EZCinematrixKrea2ThreeStageSampler", "cinematrix_bus");
    wire("EZCinematrixNeuralAnatomyContinuityDock", "anatomy_dock", "EZCinematrixJointAVTemporalSampler", "anatomy_dock");
    wire("EZCinematrixNeuralAnatomyContinuityDock", "anatomy_dock", "EZCinematrixCinemaVaultPostAndCombine", "anatomy_dock");
    wire("EZCinematrixKrea2ThreeStageSampler", "keyframe_image", "EZCinematrixVideoDirectorAndGuide", "keyframe_image");
    if (map["EZCinematrixPipelineSwitchboard"]) {
        wire("EZCinematrixKrea2ThreeStageSampler", "cinematrix_bus", "EZCinematrixPipelineSwitchboard", "cinematrix_bus");
        wire("EZCinematrixPipelineSwitchboard", "cinematrix_bus", "EZCinematrixVideoEngineAndLoraStack", "cinematrix_bus");
    } else {
        wire("EZCinematrixKrea2ThreeStageSampler", "cinematrix_bus", "EZCinematrixVideoEngineAndLoraStack", "cinematrix_bus");
    }
    wire("EZCinematrixVideoEngineAndLoraStack", "video_model_fl2va", "EZCinematrixVideoDirectorAndGuide", "video_model_fl2va");
    wire("EZCinematrixVideoEngineAndLoraStack", "video_model_ref2va", "EZCinematrixVideoDirectorAndGuide", "video_model_ref2va");
    wire("EZCinematrixVideoEngineAndLoraStack", "video_clip", "EZCinematrixVideoDirectorAndGuide", "video_clip");
    wire("EZCinematrixVideoEngineAndLoraStack", "video_vae", "EZCinematrixVideoDirectorAndGuide", "video_vae");
    wire("EZCinematrixVideoEngineAndLoraStack", "audio_vae", "EZCinematrixVideoDirectorAndGuide", "audio_vae");
    wire("EZCinematrixVideoEngineAndLoraStack", "video_vae", "EZCinematrixCinemaVaultPostAndCombine", "video_vae");
    wire("EZCinematrixVideoEngineAndLoraStack", "audio_vae", "EZCinematrixCinemaVaultPostAndCombine", "audio_vae");
    wire("EZCinematrixVideoEngineAndLoraStack", "cinematrix_bus", "EZCinematrixVideoDirectorAndGuide", "cinematrix_bus");
    wire("EZCinematrixVideoDirectorAndGuide", "active_video_model", "EZCinematrixJointAVTemporalSampler", "active_video_model");
    wire("EZCinematrixVideoDirectorAndGuide", "positive", "EZCinematrixJointAVTemporalSampler", "positive");
    wire("EZCinematrixVideoDirectorAndGuide", "negative", "EZCinematrixJointAVTemporalSampler", "negative");
    wire("EZCinematrixVideoDirectorAndGuide", "latent_video_audio", "EZCinematrixJointAVTemporalSampler", "latent_video_audio");
    wire("EZCinematrixVideoDirectorAndGuide", "cinematrix_bus", "EZCinematrixJointAVTemporalSampler", "cinematrix_bus");
    wire("EZCinematrixJointAVTemporalSampler", "sampled_video_latent", "EZCinematrixCinemaVaultPostAndCombine", "sampled_video_latent");
    wire("EZCinematrixJointAVTemporalSampler", "cinematrix_bus", "EZCinematrixCinemaVaultPostAndCombine", "cinematrix_bus");
    graph.setDirtyCanvas(true, true);
}

function buildViewUrl(filename, subfolder, type) {
    const p = new URLSearchParams({ filename: String(filename || ""), subfolder: String(subfolder || ""), type: String(type || "output") });
    return api.apiURL(`/view?${p.toString()}&t=${Date.now()}`);
}

function forwardWheelEventToCanvas(e) {
    if (!e || e._ezWheelForwarded) return;
    const lgCanvas = (app && app.canvas && app.canvas.canvas)
        ? app.canvas.canvas
        : document.querySelector("canvas#graph-canvas, canvas.lgraphcanvas");
    if (!lgCanvas || e.target === lgCanvas) return;
    const tgt = e.target;
    if (tgt && typeof tgt.closest === "function") {
        if (tgt.closest("#ez-cinematrix-flowchart-modal, .comfy-modal, .p-dialog, .litegraph.litesearchbox, .litemenu")) {
            return;
        }
        const activeScrollBox = tgt.closest("textarea, [data-ez-scrollable='1'], .ez-civitai-results-grid, .ez-note-body");
        if (activeScrollBox && (document.activeElement === activeScrollBox || activeScrollBox.classList.contains("ez-civitai-results-grid") || activeScrollBox.classList.contains("ez-note-body"))) {
            if (activeScrollBox.scrollHeight > activeScrollBox.clientHeight + 4 && !e.ctrlKey) {
                return;
            }
        }
    }
    e.preventDefault();
    e.stopPropagation();
    try {
        const synth = new WheelEvent("wheel", {
            bubbles: true,
            cancelable: true,
            clientX: e.clientX,
            clientY: e.clientY,
            screenX: e.screenX,
            screenY: e.screenY,
            deltaX: e.deltaX,
            deltaY: e.deltaY,
            deltaZ: e.deltaZ,
            deltaMode: e.deltaMode,
            ctrlKey: e.ctrlKey,
            shiftKey: e.shiftKey,
            altKey: e.altKey,
            metaKey: e.metaKey,
        });
        synth._ezWheelForwarded = true;
        lgCanvas.dispatchEvent(synth);
    } catch (err) {
        if (app && app.canvas && typeof app.canvas.processMouseWheel === "function") {
            app.canvas.processMouseWheel(e);
        }
    }
}

if (typeof window !== "undefined" && !window._ezGlobalCanvasWheelBridgeInstalled) {
    window._ezGlobalCanvasWheelBridgeInstalled = true;
    window.addEventListener("wheel", (e) => {
        const t = e && e.target;
        if (!t || typeof t.closest !== "function") return;
        if (t.tagName === "IMG" || t.tagName === "VIDEO" || t.closest(".dom-widget, .comfy-multiline-input, [class*='ez-']")) {
            forwardWheelEventToCanvas(e);
        }
    }, { capture: true, passive: false });
}

function forwardRightClickToNode(domEl, node) {
    if (!domEl || !node) return;
    domEl.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (app && app.canvas && typeof app.canvas.processContextMenu === "function") {
            app.canvas.processContextMenu(node, e);
        }
    });
    domEl.addEventListener("wheel", (e) => {
        forwardWheelEventToCanvas(e);
    }, { passive: false });
}

// SAMPLER-EXCLUSIVE MINIPYAV LIVE PREVIEW (Mounted ONLY on EZ [07] Joint AV Sampler during sampling)
function mountEzLiveStreamWidget(node, meta) {
    if (!node || !meta || !meta.filename || meta.is_final_master) return;
    if (!node._ezLiveDom) {
        const wrap = document.createElement("div");
        wrap.style.cssText = "background:#090a0f;border:1px solid #10b981;border-radius:6px;padding:6px;margin-top:4px;font-family:monospace;color:#e2e8f0;display:flex;flex-direction:column;gap:4px;box-sizing:border-box;";
        wrap.innerHTML = `
          <div style="display:flex;justify-content:space-between;align-items:center;gap:4px;">
            <div class="ez-live-hud" style="font-size:10px;color:#34d399;font-weight:bold;">⚡ MINIPYAV LIVE SAMPLER MONITOR</div>
          </div>
          <video class="ez-live-vid" controls autoplay loop muted playsinline style="width:100%;max-height:260px;background:#000;border-radius:4px;display:none;"></video>
          <img class="ez-live-img" style="width:100%;max-height:260px;object-fit:contain;background:#000;border-radius:4px;display:none;" />
        `;
        forwardRightClickToNode(wrap, node);
        node._ezLiveDom = wrap;
        if (typeof node.addDOMWidget === "function") {
            node.addDOMWidget("ez_live_stream_monitor", "div", wrap, { serialize: false, hideOnZoom: false });
        }
    }
    const wrap = node._ezLiveDom;
    const hud = wrap.querySelector(".ez-live-hud");
    const vid = wrap.querySelector(".ez-live-vid");
    const img = wrap.querySelector(".ez-live-img");
    const url = buildViewUrl(meta.filename, meta.subfolder || "", meta.type || "temp");
    hud.style.color = "#34d399";
    hud.textContent = `⚡ MINIPYAV LIVE // FÖNSTER ${meta.window || 1}/${meta.total_windows || 1} // STEG ${meta.step || 1}/${meta.total_steps || 1} (${meta.frames || 1}f)`;
    const isVid = meta.format === "mp4" || /\.(mp4|webm|mov|mkv)$/i.test(String(meta.filename || ""));
    if (isVid) {
        img.style.display = "none";
        vid.style.display = "block";
        if (vid.src !== url) {
            vid.src = url;
            vid.play().catch(() => {});
        }
    } else {
        vid.pause();
        vid.style.display = "none";
        img.style.display = "block";
        img.src = meta.preview_webp ? buildViewUrl(meta.preview_webp, "", "temp") : url;
    }
    if (node.size[1] < 560) node.setSize([Math.max(node.size[0], 400), 560]);
    if (app.graph) app.graph.setDirtyCanvas(true, true);
}

// SAVE NODE MASTER VIDEO PLAYER & ARCHIVE HUD (Mounted on EZ [08] Cinema Vault for Final Product Playback)
function mountEzVaultArchiveHudWidget(node, meta) {
    if (!node || !meta || !meta.filename) return;
    if (!node._ezVaultHudDom) {
        const wrap = document.createElement("div");
        wrap.style.cssText = "background:#090a0f;border:1px solid #f472b6;border-radius:6px;padding:6px;margin-top:4px;font-family:monospace;color:#f8fafc;display:flex;flex-direction:column;gap:5px;box-sizing:border-box;";
        wrap.innerHTML = `
          <div style="display:flex;justify-content:space-between;align-items:center;gap:4px;">
            <span class="ez-vault-status" style="font-size:10px;color:#f472b6;font-weight:bold;">🎬 SLUTPRODUKT // MASTER VIDEO PLAYER</span>
            <div style="display:flex;gap:4px;">
              <button class="ez-vault-anat-btn" style="background:#1e293b;color:#38bdf8;border:1px solid #334155;border-radius:3px;padding:2px 6px;font-size:9px;cursor:pointer;font-weight:bold;">🧬 VISA ANATOMI-MASK</button>
              <a class="ez-dl-link" target="_blank" style="background:#0f172a;color:#38bdf8;border:1px solid #38bdf8;border-radius:3px;padding:2px 6px;font-size:9px;text-decoration:none;font-weight:bold;">⬇ SPARA / ÖPPNA MASTER</a>
            </div>
          </div>
          <div class="ez-vault-hud" style="font-size:10px;color:#cbd5e1;padding:3px 5px;background:#0c0d12;border-radius:3px;"></div>
          <video class="ez-vault-master-vid" controls autoplay loop playsinline style="width:100%;max-height:320px;background:#000;border-radius:4px;display:block;"></video>
          <img class="ez-vault-anat-img" style="width:100%;max-height:220px;object-fit:contain;background:#000;border-radius:4px;display:none;" />
        `;
        forwardRightClickToNode(wrap, node);
        node._ezVaultHudDom = wrap;
        if (typeof node.addDOMWidget === "function") {
            node.addDOMWidget("ez_cinema_vault_hud", "div", wrap, { serialize: false, hideOnZoom: false });
        }
    }
    const wrap = node._ezVaultHudDom;
    const hudEl = wrap.querySelector(".ez-vault-hud");
    const dlLink = wrap.querySelector(".ez-dl-link");
    const masterVid = wrap.querySelector(".ez-vault-master-vid");
    const anatBtn = wrap.querySelector(".ez-vault-anat-btn");
    const anatImg = wrap.querySelector(".ez-vault-anat-img");
    const videoUrl = buildViewUrl(meta.filename, meta.subfolder || "", meta.type || "output");
    dlLink.href = videoUrl;
    hudEl.textContent = `Master: ${meta.filename} // ${meta.codec || "H.264"} ${meta.container || "MP4"} (CRF ${meta.quality ?? 18}) // ${meta.size_mb ?? 0} MB // ${meta.fps ?? 24} FPS (${meta.frames ?? 0}f)`;
    if (masterVid && masterVid.src !== videoUrl) {
        masterVid.src = videoUrl;
        masterVid.play().catch(() => {});
    }
    if (meta.anatomy_png) {
        const anatUrl = buildViewUrl(meta.anatomy_png, "", "temp");
        anatBtn.onclick = () => {
            const vis = anatImg.style.display === "block";
            anatImg.style.display = vis ? "none" : "block";
            if (!vis) anatImg.src = anatUrl;
        };
    }
    if (node.size[1] < 680) node.setSize([Math.max(node.size[0], 430), 680]);
    if (app.graph) app.graph.setDirtyCanvas(true, true);
}

function mountEzKrea2PreviewWidget(node, meta) {
    if (!node || !meta || !meta.filename) return;
    if (!node._ezKreaDom) {
        const wrap = document.createElement("div");
        wrap.style.cssText = "background:#090a0f;border:1px solid #f59e0b;border-radius:6px;padding:6px;margin-top:4px;font-family:monospace;color:#f8fafc;display:flex;flex-direction:column;gap:4px;box-sizing:border-box;";
        wrap.innerHTML = `
          <div style="display:flex;gap:4px;">
            <button class="ez-k-img-btn" style="background:#f59e0b;color:#000;border:none;border-radius:3px;padding:3px 7px;font-size:10px;cursor:pointer;font-weight:bold;">🖼️ KEYFRAME</button>
            <button class="ez-k-ana-btn" style="background:#1e293b;color:#cbd5e1;border:1px solid #334155;border-radius:3px;padding:3px 7px;font-size:10px;cursor:pointer;font-weight:bold;">🧬 ANATOMI-MASK</button>
          </div>
          <img class="ez-k-view" style="width:100%;max-height:520px;object-fit:contain;background:#000;border-radius:4px;display:block;" />
        `;
        forwardRightClickToNode(wrap, node);
        node._ezKreaDom = wrap;
        if (typeof node.addDOMWidget === "function") {
            node.addDOMWidget("ez_krea2_viewer", "div", wrap, { serialize: false, hideOnZoom: false });
        }
    }
    const wrap = node._ezKreaDom;
    const imgEl = wrap.querySelector(".ez-k-view");
    const btnI = wrap.querySelector(".ez-k-img-btn");
    const btnA = wrap.querySelector(".ez-k-ana-btn");
    const mainUrl = buildViewUrl(meta.filename, meta.subfolder || "", meta.type || "temp");
    const anatUrl = meta.anatomy_png ? buildViewUrl(meta.anatomy_png, "", "temp") : mainUrl;
    btnI.onclick = () => { btnI.style.background = "#f59e0b"; btnI.style.color = "#000"; btnA.style.background = "#1e293b"; btnA.style.color = "#cbd5e1"; imgEl.src = mainUrl; };
    btnA.onclick = () => { btnA.style.background = "#0284c7"; btnA.style.color = "#fff"; btnI.style.background = "#1e293b"; btnI.style.color = "#cbd5e1"; imgEl.src = anatUrl; };
    imgEl.src = mainUrl;
    if (node.size[1] < 640) node.setSize([Math.max(node.size[0], 400), 640]);
    if (app.graph) app.graph.setDirtyCanvas(true, true);
}

function buildEzInputImageUrl(rawVal) {
    let s = String(rawVal || "").trim();
    if (!s || s === "None") return "";
    let type = "input";
    const typeMatch = s.match(/\s+\[(input|output|temp)\]$/i);
    if (typeMatch) {
        type = typeMatch[1].toLowerCase();
        s = s.slice(0, s.length - typeMatch[0].length).trim();
    }
    const norm = s.replace(/\\/g, "/");
    const slashIdx = norm.lastIndexOf("/");
    const subfolder = slashIdx !== -1 ? norm.slice(0, slashIdx) : "";
    const filename = slashIdx !== -1 ? norm.slice(slashIdx + 1) : norm;
    const p = new URLSearchParams({ filename, subfolder, type });
    return api.apiURL(`/view?${p.toString()}`);
}

const EZ_LIVE_UPLOADED_IMAGES = new Set();
const EZ_LIVE_UPLOADED_VIDEOS = new Set();
const EZ_THUMB_IMG_CACHE = new Map();
const EZ_MEDIA_DIM_CACHE = new Map();
let EZ_LAST_MEDIA_SYNC_TS = 0;
let EZ_ACTIVE_MEDIA_PICKER_CTX = { node: null, widget: null, slotName: "", ts: 0 };

const EZ_OMNI_IMAGE_SLOT_NAMES = [
    "slot1_master_image",
    "slot2_person_image",
    "slot3_clothing_image",
    "slot4_background_image"
];
const EZ_OMNI_ALL_SLOT_NAMES = [
    ...EZ_OMNI_IMAGE_SLOT_NAMES,
    "slot5_reference_video"
];
const EZ_OMNI_UPLOAD_BTN_SPECS = [
    { slot: "slot1_master_image", btnName: "ez_slot1_upload_btn", label: "📂 choose file to upload ([1] Huvudbild)" },
    { slot: "slot2_person_image", btnName: "ez_slot2_upload_btn", label: "📂 choose file to upload ([2] Person)" },
    { slot: "slot3_clothing_image", btnName: "ez_slot3_upload_btn", label: "📂 choose file to upload ([3] Kläder)" },
    { slot: "slot4_background_image", btnName: "ez_slot4_upload_btn", label: "📂 choose file to upload ([4] Bakgrund)" },
    { slot: "slot5_reference_video", btnName: "ez_slot5_video_upload_btn", label: "🎬 choose file to upload ([5] Video)" }
];

function isEzImageFilename(val) {
    const clean = String(val || "").trim().replace(/\s+\[(input|output|temp)\]$/i, "");
    return /\.(png|jpg|jpeg|webp|bmp|gif)$/i.test(clean);
}

function isEzVideoFilename(val) {
    const clean = String(val || "").trim().replace(/\s+\[(input|output|temp)\]$/i, "");
    return /\.(mp4|mkv|webp|mov|webm|avi|gif)$/i.test(clean);
}

function getCachedEzThumbImage(rawVal) {
    const url = buildEzInputImageUrl(rawVal);
    if (!url || !isEzImageFilename(rawVal)) return null;
    if (EZ_THUMB_IMG_CACHE.has(url)) return EZ_THUMB_IMG_CACHE.get(url);
    const im = new Image();
    im.decoding = "async";
    im.onload = () => {
        if (im.naturalWidth > 0 && im.naturalHeight > 0) {
            EZ_MEDIA_DIM_CACHE.set(String(rawVal), `${im.naturalWidth}×${im.naturalHeight}`);
        }
        if (app && app.graph) app.graph.setDirtyCanvas(true, true);
    };
    im.src = url;
    EZ_THUMB_IMG_CACHE.set(url, im);
    return im;
}

function appendUniqueMediaValues(targetArr, incomingValues) {
    if (!Array.isArray(targetArr) || !Array.isArray(incomingValues)) return false;
    let changed = false;
    for (const v of incomingValues) {
        if (v && typeof v === "string" && !targetArr.includes(v)) {
            targetArr.push(v);
            changed = true;
        }
    }
    return changed;
}

function mergeEzMediaIntoRegistryDef(defObj, imgList, vidList) {
    if (!defObj || !defObj.input || !defObj.input.required) return;
    const req = defObj.input.required;
    for (const k of ["source_image", ...EZ_OMNI_IMAGE_SLOT_NAMES]) {
        if (Array.isArray(req[k]) && Array.isArray(req[k][0])) {
            appendUniqueMediaValues(req[k][0], imgList);
        }
    }
    if (Array.isArray(req.slot5_reference_video) && Array.isArray(req.slot5_reference_video[0])) {
        appendUniqueMediaValues(req.slot5_reference_video[0], vidList);
    }
}

function broadcastEzMediaListsToAllGraphNodes(imgList, vidList) {
    for (const v of imgList) if (v && v !== "None") EZ_LIVE_UPLOADED_IMAGES.add(v);
    for (const v of vidList) if (v && v !== "None") EZ_LIVE_UPLOADED_VIDEOS.add(v);
    const allImgs = Array.from(EZ_LIVE_UPLOADED_IMAGES);
    const allVids = Array.from(EZ_LIVE_UPLOADED_VIDEOS);
    for (const defObj of Object.values(EZ_NODE_DATA_REGISTRY)) {
        mergeEzMediaIntoRegistryDef(defObj, allImgs, allVids);
    }
    if (!app || !app.graph || !Array.isArray(app.graph._nodes)) return;
    let anyChanged = false;
    for (const n of app.graph._nodes) {
        if (!n || !Array.isArray(n.widgets)) continue;
        const bType = stripEzEditionSuffix(n.type);
        if (bType === "EZCinematrixOmniReferenceLoader" || bType === "EZ_13_Cinematrix_Omni_Reference_Loader") {
            for (const sName of EZ_OMNI_IMAGE_SLOT_NAMES) {
                const w = n.widgets.find(x => x && x.name === sName);
                if (w && w.options && Array.isArray(w.options.values)) {
                    if (appendUniqueMediaValues(w.options.values, allImgs)) anyChanged = true;
                }
            }
            const wVid = n.widgets.find(x => x && x.name === "slot5_reference_video");
            if (wVid && wVid.options && Array.isArray(wVid.options.values)) {
                if (appendUniqueMediaValues(wVid.options.values, allVids)) anyChanged = true;
            }
        } else if (bType === "EZCinematrixCanvasIngest") {
            const wSrc = n.widgets.find(x => x && x.name === "source_image");
            if (wSrc && wSrc.options && Array.isArray(wSrc.options.values)) {
                if (appendUniqueMediaValues(wSrc.options.values, allImgs)) anyChanged = true;
            }
        }
    }
    if (anyChanged && app.graph) app.graph.setDirtyCanvas(true, true);
}

function broadcastEzUploadedMediaToGraph(uploadedPath) {
    const p = String(uploadedPath || "").trim();
    if (!p || p === "None") return;
    const imgs = isEzImageFilename(p) ? [p] : [];
    const vids = isEzVideoFilename(p) ? [p] : [];
    if (!imgs.length && !vids.length) imgs.push(p);
    broadcastEzMediaListsToAllGraphNodes(imgs, vids);
}

async function syncEzLiveInputMediaFromServer(force = false) {
    const now = Date.now();
    if (!force && now - EZ_LAST_MEDIA_SYNC_TS < 1200) return;
    EZ_LAST_MEDIA_SYNC_TS = now;
    try {
        const resp = await api.fetchApi("/ez_cinematrix/omni_ref/media_list");
        if (resp && resp.status === 200) {
            const data = await resp.json();
            const imgs = Array.isArray(data.images) ? data.images : [];
            const vids = Array.isArray(data.videos) ? data.videos : [];
            broadcastEzMediaListsToAllGraphNodes(imgs, vids);
            return;
        }
    } catch (e) {}
    try {
        const respInfo = await api.fetchApi("/object_info/EZCinematrixOmniReferenceLoader");
        if (respInfo && respInfo.status === 200) {
            const infoJson = await respInfo.json();
            const defObj = infoJson && infoJson.EZCinematrixOmniReferenceLoader;
            const req = defObj && defObj.input && defObj.input.required;
            if (req) {
                const imgs = Array.isArray(req.slot1_master_image && req.slot1_master_image[0]) ? req.slot1_master_image[0] : [];
                const vids = Array.isArray(req.slot5_reference_video && req.slot5_reference_video[0]) ? req.slot5_reference_video[0] : [];
                broadcastEzMediaListsToAllGraphNodes(imgs, vids);
            }
        }
    } catch (e) {}
}

async function uploadFileToEzNodeSlot(file, targetNode, targetSlot) {
    if (!file) return null;
    const body = new FormData();
    body.append("image", file);
    body.append("overwrite", "true");
    try {
        const resp = await api.fetchApi("/upload/image", { method: "POST", body });
        if (resp && resp.status === 200) {
            const data = await resp.json();
            const uploadedPath = data.subfolder ? `${data.subfolder}/${data.name}` : data.name;
            broadcastEzUploadedMediaToGraph(uploadedPath);
            if (targetNode) {
                if (typeof targetNode._ezSetOmniSlotValue === "function" && EZ_OMNI_ALL_SLOT_NAMES.includes(targetSlot)) {
                    targetNode._ezSetOmniSlotValue(targetSlot, uploadedPath);
                } else if (Array.isArray(targetNode.widgets)) {
                    const w = targetNode.widgets.find(x => x && x.name === targetSlot);
                    if (w) {
                        if (w.options && Array.isArray(w.options.values) && !w.options.values.includes(uploadedPath)) {
                            w.options.values.push(uploadedPath);
                        }
                        w.value = uploadedPath;
                        if (typeof w.callback === "function") {
                            try { w.callback(uploadedPath); } catch (e) {}
                        }
                    }
                    if (app && app.graph) app.graph.setDirtyCanvas(true, true);
                }
            }
            return uploadedPath;
        }
    } catch (err) {
        console.error("[EZ Media Upload Error]", err);
    }
    return null;
}

function getOrCreateEzMenuHoverLoupe() {
    let loupe = document.getElementById("ez-omni-menu-hover-loupe");
    if (loupe) return loupe;
    loupe = document.createElement("div");
    loupe.id = "ez-omni-menu-hover-loupe";
    loupe.style.cssText = "position:fixed;z-index:100050;width:236px;background:#07090f;border:1.5px solid #22d3ee;border-radius:8px;padding:6px;box-shadow:0 14px 36px rgba(0,0,0,0.85);pointer-events:none;display:none;flex-direction:column;gap:5px;font-family:monospace;";
    loupe.innerHTML = `
      <img class="ez-loupe-img" style="width:100%;height:200px;object-fit:contain;background:#020305;border-radius:5px;display:none;" />
      <video class="ez-loupe-vid" muted loop autoplay playsinline style="width:100%;height:200px;object-fit:contain;background:#020305;border-radius:5px;display:none;"></video>
      <div class="ez-loupe-caption" style="font-size:10px;color:#e2e8f0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-align:center;"></div>
    `;
    document.body.appendChild(loupe);
    return loupe;
}

function hideEzMenuHoverLoupe() {
    const loupe = document.getElementById("ez-omni-menu-hover-loupe");
    if (!loupe) return;
    loupe.style.display = "none";
    const vid = loupe.querySelector(".ez-loupe-vid");
    if (vid) {
        try { vid.pause(); } catch (e) {}
        vid.removeAttribute("src");
    }
}

function showEzMenuHoverLoupe(rawVal, anchorRect) {
    const url = buildEzInputImageUrl(rawVal);
    if (!url || !anchorRect) {
        hideEzMenuHoverLoupe();
        return;
    }
    const loupe = getOrCreateEzMenuHoverLoupe();
    const imgEl = loupe.querySelector(".ez-loupe-img");
    const vidEl = loupe.querySelector(".ez-loupe-vid");
    const capEl = loupe.querySelector(".ez-loupe-caption");
    const cleanName = String(rawVal).replace(/\s+\[(input|output|temp)\]$/i, "").split(/[\\/]/).pop();
    const isVid = isEzVideoFilename(rawVal) && !isEzImageFilename(rawVal);
    if (isVid) {
        imgEl.style.display = "none";
        vidEl.style.display = "block";
        if (vidEl.dataset.rawVal !== rawVal) {
            vidEl.dataset.rawVal = rawVal;
            vidEl.src = url;
            try {
                const p = vidEl.play();
                if (p && typeof p.catch === "function") p.catch(() => {});
            } catch (e) {}
        }
    } else {
        vidEl.style.display = "none";
        imgEl.style.display = "block";
        if (imgEl.dataset.rawVal !== rawVal) {
            imgEl.dataset.rawVal = rawVal;
            imgEl.src = url;
        }
    }
    const dimTxt = EZ_MEDIA_DIM_CACHE.get(String(rawVal));
    capEl.textContent = dimTxt ? `${dimTxt} · ${cleanName}` : cleanName;
    loupe.style.display = "flex";
    const loupeW = 248;
    const loupeH = 236;
    let leftPos = anchorRect.right + 10;
    if (leftPos + loupeW > window.innerWidth - 8) {
        leftPos = Math.max(8, anchorRect.left - loupeW - 10);
    }
    const topPos = Math.max(8, Math.min(window.innerHeight - loupeH - 8, anchorRect.top - 24));
    loupe.style.left = `${Math.round(leftPos)}px`;
    loupe.style.top = `${Math.round(topPos)}px`;
}

function decorateEzMediaContextMenu(menuEl) {
    if (!menuEl || !(menuEl instanceof HTMLElement)) return;
    const entries = Array.from(menuEl.querySelectorAll(".litemenu-entry"));
    if (!entries.length) return;
    const activeCtx = (Date.now() - EZ_ACTIVE_MEDIA_PICKER_CTX.ts < 8000) ? EZ_ACTIVE_MEDIA_PICKER_CTX : null;
    const hasMediaItems = Boolean(activeCtx) || entries.some(el => {
        const v = String(el.getAttribute("data-value") || el.textContent || "").trim();
        return isEzImageFilename(v) || isEzVideoFilename(v);
    });
    if (!hasMediaItems) return;

    menuEl.style.minWidth = "340px";
    menuEl.style.maxWidth = "520px";

    if (activeCtx && activeCtx.node && activeCtx.slotName && !menuEl.querySelector(".ez-menu-upload-bar")) {
        const upBar = document.createElement("div");
        upBar.className = "ez-menu-upload-bar";
        upBar.style.cssText = "display:flex;align-items:center;justify-content:space-between;gap:6px;padding:5px 7px;margin-bottom:3px;background:#0b1120;border-bottom:1px solid #1e293b;position:sticky;top:0;z-index:3;";
        const upBtn = document.createElement("button");
        upBtn.type = "button";
        upBtn.textContent = "📂 choose file to upload";
        upBtn.style.cssText = "width:100%;background:linear-gradient(90deg,#0284c7,#0ea5e9);color:#fff;font-family:monospace;font-weight:bold;font-size:11px;border:1px solid #38bdf8;border-radius:4px;padding:5px 8px;cursor:pointer;text-align:center;";
        const hiddenPicker = document.createElement("input");
        hiddenPicker.type = "file";
        hiddenPicker.style.display = "none";
        hiddenPicker.accept = activeCtx.slotName === "slot5_reference_video"
            ? ".mp4,.mkv,.webp,.mov,.webm,.avi,.gif,video/*"
            : ".png,.jpg,.jpeg,.webp,.bmp,.gif,image/png,image/jpeg,image/webp,image/bmp";
        upBtn.onclick = (ev) => {
            ev.preventDefault();
            ev.stopPropagation();
            hiddenPicker.value = "";
            hiddenPicker.click();
        };
        hiddenPicker.onchange = async (ev) => {
            ev.stopPropagation();
            const f = hiddenPicker.files && hiddenPicker.files[0];
            if (!f) return;
            await uploadFileToEzNodeSlot(f, activeCtx.node, activeCtx.slotName);
            hideEzMenuHoverLoupe();
            try { menuEl.remove(); } catch (e) {}
        };
        upBar.appendChild(upBtn);
        upBar.appendChild(hiddenPicker);
        const filterInput = menuEl.querySelector("input");
        if (filterInput && filterInput.nextSibling) {
            menuEl.insertBefore(upBar, filterInput.nextSibling);
        } else if (filterInput) {
            menuEl.appendChild(upBar);
        } else {
            menuEl.insertBefore(upBar, menuEl.firstChild);
        }
    }

    const curSelected = activeCtx && activeCtx.widget ? String(activeCtx.widget.value || "") : "";
    for (const entry of entries) {
        if (entry.dataset.ezThumbDecorated === "1") continue;
        const rawVal = String(entry.getAttribute("data-value") || entry.textContent || "").trim();
        if (!rawVal) continue;
        const isNone = rawVal === "None";
        const isImg = !isNone && isEzImageFilename(rawVal);
        const isVid = !isNone && !isImg && isEzVideoFilename(rawVal);
        if (!isNone && !isImg && !isVid) continue;

        entry.dataset.ezThumbDecorated = "1";
        entry.textContent = "";
        entry.style.cssText += ";display:flex !important;align-items:center !important;gap:9px !important;padding:4px 8px !important;min-height:46px !important;box-sizing:border-box !important;";
        if (curSelected && rawVal === curSelected) {
            entry.style.background = "rgba(14, 165, 233, 0.22)";
            entry.style.borderLeft = "3px solid #22d3ee";
        }

        const thumbBox = document.createElement("div");
        thumbBox.style.cssText = "width:42px;height:42px;min-width:42px;border-radius:4px;background:#050608;border:1px solid #334155;overflow:hidden;display:flex;align-items:center;justify-content:center;flex-shrink:0;";
        const labelWrap = document.createElement("div");
        labelWrap.style.cssText = "display:flex;flex-direction:column;min-width:0;flex:1;overflow:hidden;line-height:1.25;";
        const nameSpan = document.createElement("span");
        nameSpan.style.cssText = "font-size:11.5px;color:#f1f5f9;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-family:monospace;";
        nameSpan.textContent = rawVal;
        const subSpan = document.createElement("span");
        subSpan.style.cssText = "font-size:9.5px;color:#94a3b8;font-family:monospace;";

        if (isNone) {
            thumbBox.innerHTML = `<span style="font-size:14px;color:#64748b;">∅</span>`;
            subSpan.textContent = "Ingen fil vald (Tom slot)";
        } else if (isImg) {
            const tImg = document.createElement("img");
            tImg.loading = "lazy";
            tImg.decoding = "async";
            tImg.src = buildEzInputImageUrl(rawVal);
            tImg.style.cssText = "width:42px;height:42px;object-fit:cover;display:block;";
            const cachedDim = EZ_MEDIA_DIM_CACHE.get(rawVal);
            subSpan.textContent = cachedDim ? `🖼️ ${cachedDim}` : "🖼️ Bildreferens";
            tImg.onload = () => {
                if (tImg.naturalWidth > 0 && tImg.naturalHeight > 0) {
                    const dStr = `${tImg.naturalWidth}×${tImg.naturalHeight}`;
                    EZ_MEDIA_DIM_CACHE.set(rawVal, dStr);
                    subSpan.textContent = `🖼️ ${dStr}`;
                }
            };
            thumbBox.appendChild(tImg);
        } else if (isVid) {
            const tVid = document.createElement("video");
            tVid.preload = "metadata";
            tVid.muted = true;
            tVid.playsInline = true;
            tVid.src = `${buildEzInputImageUrl(rawVal)}#t=0.1`;
            tVid.style.cssText = "width:42px;height:42px;object-fit:cover;display:block;";
            subSpan.textContent = "🎬 Videoreferens";
            tVid.onloadedmetadata = () => {
                if (tVid.videoWidth > 0 && tVid.videoHeight > 0) {
                    const dStr = `${tVid.videoWidth}×${tVid.videoHeight}`;
                    EZ_MEDIA_DIM_CACHE.set(rawVal, dStr);
                    subSpan.textContent = `🎬 ${dStr}`;
                }
            };
            thumbBox.appendChild(tVid);
        }

        labelWrap.appendChild(nameSpan);
        labelWrap.appendChild(subSpan);
        entry.appendChild(thumbBox);
        entry.appendChild(labelWrap);

        if (!isNone) {
            entry.addEventListener("mouseenter", () => {
                showEzMenuHoverLoupe(rawVal, menuEl.getBoundingClientRect());
            });
            entry.addEventListener("mouseleave", () => {
                hideEzMenuHoverLoupe();
            });
        } else {
            entry.addEventListener("mouseenter", hideEzMenuHoverLoupe);
        }
    }
}

function installEzGlobalMediaSyncAndThumbnailMenu() {
    if (window._ezGlobalMediaSyncInstalled) return;
    window._ezGlobalMediaSyncInstalled = true;

    if (api && typeof api.fetchApi === "function" && !api._ezUploadSyncWrapped) {
        api._ezUploadSyncWrapped = true;
        const origFetchApi = api.fetchApi.bind(api);
        api.fetchApi = async function (route, options) {
            const resp = await origFetchApi(route, options);
            try {
                if (resp && resp.status === 200 && /\/upload\/image\b/i.test(String(route || ""))) {
                    resp.clone().json().then(data => {
                        if (data && data.name) {
                            const uploadedPath = data.subfolder ? `${data.subfolder}/${data.name}` : data.name;
                            broadcastEzUploadedMediaToGraph(uploadedPath);
                        }
                    }).catch(() => {});
                }
            } catch (e) {}
            return resp;
        };
    }

    window.addEventListener("focus", () => {
        syncEzLiveInputMediaFromServer(false);
    });

    document.addEventListener("pointerdown", (ev) => {
        try {
            if (!ev.target || !(ev.target instanceof HTMLElement) || !ev.target.closest(".litecontextmenu")) {
                hideEzMenuHoverLoupe();
            }
            const cv = app && app.canvas;
            const n = cv && cv.node_over;
            if (!n || !Array.isArray(n.widgets)) return;
            const bType = stripEzEditionSuffix(n.type);
            const is13 = (bType === "EZCinematrixOmniReferenceLoader" || bType === "EZ_13_Cinematrix_Omni_Reference_Loader");
            const is01 = (bType === "EZCinematrixCanvasIngest");
            if (!is13 && !is01) return;
            syncEzLiveInputMediaFromServer(false);
            if (cv.graph_mouse && Array.isArray(n.pos)) {
                const localY = cv.graph_mouse[1] - n.pos[1];
                const slotCandidates = is13 ? EZ_OMNI_ALL_SLOT_NAMES : ["source_image"];
                for (const sName of slotCandidates) {
                    const w = n.widgets.find(x => x && x.name === sName);
                    if (w && typeof w.last_y === "number" && localY >= w.last_y - 2 && localY <= w.last_y + 24) {
                        EZ_ACTIVE_MEDIA_PICKER_CTX = { node: n, widget: w, slotName: sName, ts: Date.now() };
                        break;
                    }
                }
            }
        } catch (e) {}
    }, true);

    const obs = new MutationObserver((mutations) => {
        let checkClose = false;
        for (const m of mutations) {
            for (const added of m.addedNodes) {
                if (!(added instanceof HTMLElement)) continue;
                const menu = added.classList.contains("litecontextmenu")
                    ? added
                    : (added.closest && added.closest(".litecontextmenu")) || (added.querySelector && added.querySelector(".litecontextmenu"));
                if (menu) {
                    decorateEzMediaContextMenu(menu);
                }
            }
            if (m.removedNodes && m.removedNodes.length > 0) checkClose = true;
        }
        if (checkClose && !document.querySelector(".litecontextmenu")) {
            hideEzMenuHoverLoupe();
        }
    });
    obs.observe(document.body, { childList: true, subtree: true });
    setTimeout(() => syncEzLiveInputMediaFromServer(true), 450);
}

// OMNI-REFERENCE [13] 5-SLOT VISUAL PREVIEW STUDIO (Main Figure [1] + 4 Secondary Thumbnails [2][3][4][5] Lined Up Underneath)
function mountEzOmniReferencePreviewStrip(node) {
    if (!node) return;
    if (node._ezOmniPreviewDom) {
        if (typeof node._ezOrderOmniSlotWidgets === "function") node._ezOrderOmniSlotWidgets();
        if (typeof node._ezRefreshOmniPreviews === "function") node._ezRefreshOmniPreviews();
        return;
    }
    const wrap = document.createElement("div");
    wrap.style.cssText = "background:#08090d;border:1px solid rgba(34,211,238,0.35);border-radius:6px;padding:6px;margin-top:4px;font-family:monospace;color:#e2e8f0;display:flex;flex-direction:column;gap:6px;box-sizing:border-box;width:100%;";
    wrap.innerHTML = `
      <div class="ez-omni-s1-card" style="display:flex;flex-direction:column;align-items:center;background:#050608;border:1px solid #1e293b;border-radius:5px;padding:4px;position:relative;">
        <div style="width:100%;display:flex;justify-content:space-between;align-items:center;margin-bottom:3px;padding:0 2px;gap:4px;">
          <span style="font-size:9.5px;color:#22d3ee;font-weight:bold;">🎯 [1] HUVUDBILD / MASTER COMPOSITE</span>
          <div style="display:flex;align-items:center;gap:4px;">
            <span class="ez-omni-s1-dim" style="font-size:9px;color:#94a3b8;">—</span>
            <button class="ez-omni-up-btn" data-slot="slot1_master_image" title="choose file to upload — [1] Huvudbild" style="background:#0369a1;color:#f8fafc;border:1px solid #38bdf8;border-radius:3px;padding:1px 5px;font-size:8.5px;cursor:pointer;font-family:monospace;">📂 Upload</button>
            <button class="ez-omni-clr-btn" data-slot="slot1_master_image" title="Rensa [1] Huvudbild (None)" style="background:#1e293b;color:#f87171;border:1px solid #334155;border-radius:3px;padding:1px 4px;font-size:8.5px;cursor:pointer;">✕</button>
          </div>
        </div>
        <img class="ez-omni-s1-img" style="width:100%;max-height:220px;object-fit:contain;background:#000;border-radius:4px;display:none;cursor:pointer;" title="Klicka för att välja / ladda upp ny bild till [1] Huvudbild" />
        <div class="ez-omni-s1-empty" style="height:110px;width:100%;display:flex;align-items:center;justify-content:center;background:#090a10;border:1px dashed #1e293b;border-radius:4px;color:#64748b;font-size:10px;cursor:pointer;text-align:center;">+ Klicka här eller på choose file to upload ([1] Huvudbild)</div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:5px;width:100%;">
        <div class="ez-omni-subcard" data-slot="slot2_person_image" style="background:#050608;border:1px solid #1e293b;border-radius:5px;padding:4px;display:flex;flex-direction:column;align-items:center;gap:3px;">
          <div style="width:100%;display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:8px;color:#c084fc;font-weight:bold;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">👤 [2] PERSON</span>
            <div style="display:flex;gap:2px;">
              <button class="ez-omni-up-btn" data-slot="slot2_person_image" title="Ladda upp bild till [2] Person" style="background:#1e293b;color:#38bdf8;border:1px solid #334155;border-radius:3px;padding:0 3px;font-size:8px;cursor:pointer;">📂</button>
              <button class="ez-omni-clr-btn" data-slot="slot2_person_image" title="Rensa [2] Person (None)" style="background:#1e293b;color:#f87171;border:1px solid #334155;border-radius:3px;padding:0 3px;font-size:8px;cursor:pointer;">✕</button>
            </div>
          </div>
          <img class="ez-omni-sub-img" style="width:100%;height:86px;object-fit:contain;background:#000;border-radius:3px;display:none;cursor:pointer;" title="Klicka för att ladda upp ny bild till [2] Person" />
          <div class="ez-omni-sub-empty" style="width:100%;height:86px;display:flex;align-items:center;justify-content:center;background:#090a10;border:1px dashed #1e293b;border-radius:3px;color:#475569;font-size:8px;text-align:center;cursor:pointer;">+ Välj / Ladda<br/>Person</div>
          <div class="ez-omni-sub-meta" style="font-size:7.5px;color:#94a3b8;width:100%;text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">None</div>
        </div>
        <div class="ez-omni-subcard" data-slot="slot3_clothing_image" style="background:#050608;border:1px solid #1e293b;border-radius:5px;padding:4px;display:flex;flex-direction:column;align-items:center;gap:3px;">
          <div style="width:100%;display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:8px;color:#38bdf8;font-weight:bold;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">👗 [3] KLÄDER</span>
            <div style="display:flex;gap:2px;">
              <button class="ez-omni-up-btn" data-slot="slot3_clothing_image" title="Ladda upp bild till [3] Kläder" style="background:#1e293b;color:#38bdf8;border:1px solid #334155;border-radius:3px;padding:0 3px;font-size:8px;cursor:pointer;">📂</button>
              <button class="ez-omni-clr-btn" data-slot="slot3_clothing_image" title="Rensa [3] Kläder (None)" style="background:#1e293b;color:#f87171;border:1px solid #334155;border-radius:3px;padding:0 3px;font-size:8px;cursor:pointer;">✕</button>
            </div>
          </div>
          <img class="ez-omni-sub-img" style="width:100%;height:86px;object-fit:contain;background:#000;border-radius:3px;display:none;cursor:pointer;" title="Klicka för att ladda upp ny bild till [3] Kläder" />
          <div class="ez-omni-sub-empty" style="width:100%;height:86px;display:flex;align-items:center;justify-content:center;background:#090a10;border:1px dashed #1e293b;border-radius:3px;color:#475569;font-size:8px;text-align:center;cursor:pointer;">+ Välj / Ladda<br/>Kläder</div>
          <div class="ez-omni-sub-meta" style="font-size:7.5px;color:#94a3b8;width:100%;text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">None</div>
        </div>
        <div class="ez-omni-subcard" data-slot="slot4_background_image" style="background:#050608;border:1px solid #1e293b;border-radius:5px;padding:4px;display:flex;flex-direction:column;align-items:center;gap:3px;">
          <div style="width:100%;display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:8px;color:#34d399;font-weight:bold;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">🌆 [4] BAKGRUND</span>
            <div style="display:flex;gap:2px;">
              <button class="ez-omni-up-btn" data-slot="slot4_background_image" title="Ladda upp bild till [4] Bakgrund" style="background:#1e293b;color:#38bdf8;border:1px solid #334155;border-radius:3px;padding:0 3px;font-size:8px;cursor:pointer;">📂</button>
              <button class="ez-omni-clr-btn" data-slot="slot4_background_image" title="Rensa [4] Bakgrund (None)" style="background:#1e293b;color:#f87171;border:1px solid #334155;border-radius:3px;padding:0 3px;font-size:8px;cursor:pointer;">✕</button>
            </div>
          </div>
          <img class="ez-omni-sub-img" style="width:100%;height:86px;object-fit:contain;background:#000;border-radius:3px;display:none;cursor:pointer;" title="Klicka för att ladda upp ny bild till [4] Bakgrund" />
          <div class="ez-omni-sub-empty" style="width:100%;height:86px;display:flex;align-items:center;justify-content:center;background:#090a10;border:1px dashed #1e293b;border-radius:3px;color:#475569;font-size:8px;text-align:center;cursor:pointer;">+ Välj / Ladda<br/>Bakgrund</div>
          <div class="ez-omni-sub-meta" style="font-size:7.5px;color:#94a3b8;width:100%;text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">None</div>
        </div>
        <div class="ez-omni-subcard" data-slot="slot5_reference_video" data-kind="video" style="background:#050608;border:1px solid #1e293b;border-radius:5px;padding:4px;display:flex;flex-direction:column;align-items:center;gap:3px;">
          <div style="width:100%;display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:8px;color:#fbbf24;font-weight:bold;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">🎬 [5] VIDEO</span>
            <div style="display:flex;gap:2px;">
              <button class="ez-omni-up-btn" data-slot="slot5_reference_video" title="Ladda upp video till [5] Referensvideo" style="background:#1e293b;color:#fbbf24;border:1px solid #334155;border-radius:3px;padding:0 3px;font-size:8px;cursor:pointer;">📂</button>
              <button class="ez-omni-clr-btn" data-slot="slot5_reference_video" title="Rensa [5] Referensvideo (None)" style="background:#1e293b;color:#f87171;border:1px solid #334155;border-radius:3px;padding:0 3px;font-size:8px;cursor:pointer;">✕</button>
            </div>
          </div>
          <video class="ez-omni-sub-vid" muted loop autoplay playsinline style="width:100%;height:86px;object-fit:contain;background:#000;border-radius:3px;display:none;cursor:pointer;" title="Klicka för att ladda upp ny video (.mp4, .mkv, .webp) till [5] Referensvideo"></video>
          <img class="ez-omni-sub-img" style="width:100%;height:86px;object-fit:contain;background:#000;border-radius:3px;display:none;cursor:pointer;" title="Klicka för att ladda upp ny video/WebP/GIF till [5] Referensvideo" />
          <div class="ez-omni-sub-empty" style="width:100%;height:86px;display:flex;align-items:center;justify-content:center;background:#090a10;border:1px dashed #1e293b;border-radius:3px;color:#475569;font-size:8px;text-align:center;cursor:pointer;">+ Välj / Ladda<br/>MP4 · MKV · WEBP</div>
          <div class="ez-omni-sub-meta" style="font-size:7.5px;color:#94a3b8;width:100%;text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">None</div>
        </div>
      </div>
      <input type="file" class="ez-omni-hidden-file" accept=".mp4,.mkv,.webp,.mov,.webm,.avi,.gif,image/png,image/jpeg,image/webp,video/mp4,video/x-matroska,video/webm,video/quicktime" style="display:none;" />
    `;
    forwardRightClickToNode(wrap, node);
    node._ezOmniPreviewDom = wrap;

    const s1Img = wrap.querySelector(".ez-omni-s1-img");
    const s1Empty = wrap.querySelector(".ez-omni-s1-empty");
    const s1Dim = wrap.querySelector(".ez-omni-s1-dim");
    const fileInput = wrap.querySelector(".ez-omni-hidden-file");
    let pendingUploadSlot = "slot1_master_image";

    s1Img.onload = () => {
        s1Dim.textContent = `${s1Img.naturalWidth} × ${s1Img.naturalHeight}`;
    };

    const getSlotVal = (slotName) => {
        if (!Array.isArray(node.widgets)) return "None";
        const w = node.widgets.find(x => x && x.name === slotName);
        return w ? String(w.value || "None") : "None";
    };

    const setSlotVal = (slotName, newVal) => {
        if (!Array.isArray(node.widgets)) return;
        if (newVal && newVal !== "None") {
            broadcastEzUploadedMediaToGraph(newVal);
        }
        const targetSlots = slotName === "slot5_reference_video"
            ? ["slot5_reference_video"]
            : EZ_OMNI_IMAGE_SLOT_NAMES;
        for (const sName of targetSlots) {
            const sw = node.widgets.find(x => x && x.name === sName);
            if (sw && sw.options && Array.isArray(sw.options.values) && newVal && !sw.options.values.includes(newVal)) {
                sw.options.values.push(newVal);
            }
        }
        const w = node.widgets.find(x => x && x.name === slotName);
        if (w) {
            w.value = newVal;
            if (typeof w.callback === "function") {
                try { w.callback(newVal); } catch (e) {}
            }
        }
        refreshOmniPreviews();
    };
    node._ezSetOmniSlotValue = setSlotVal;

    const triggerUploadForSlot = (slotKey) => {
        pendingUploadSlot = slotKey || "slot1_master_image";
        if (pendingUploadSlot === "slot5_reference_video") {
            fileInput.accept = ".mp4,.mkv,.webp,.mov,.webm,.avi,.gif,video/mp4,video/x-matroska,image/webp,video/webm,video/quicktime,video/x-msvideo,video/*,image/gif";
        } else {
            fileInput.accept = ".png,.jpg,.jpeg,.webp,.bmp,.gif,image/png,image/jpeg,image/webp,image/bmp,image/gif";
        }
        fileInput.value = "";
        fileInput.click();
    };
    node._ezTriggerOmniSlotUpload = triggerUploadForSlot;

    const ensureAndOrderOmniSlotWidgets = () => {
        if (!Array.isArray(node.widgets) || typeof node.addWidget !== "function") return;
        for (const spec of EZ_OMNI_UPLOAD_BTN_SPECS) {
            let btnW = node.widgets.find(x => x && x.name === spec.btnName);
            if (!btnW) {
                btnW = node.addWidget("button", spec.label, null, () => {
                    triggerUploadForSlot(spec.slot);
                });
                if (btnW) {
                    btnW.name = spec.btnName;
                    btnW.label = spec.label;
                }
            }
            if (btnW) {
                btnW.serialize = false;
                btnW.options = Object.assign({}, btnW.options || {}, { serialize: false });
            }
        }
        for (const w of node.widgets) {
            if (w && w.name === "upload" && w.type === "button") {
                w.serialize = false;
                w.options = Object.assign({}, w.options || {}, { serialize: false });
                w.callback = () => triggerUploadForSlot("slot1_master_image");
            }
        }
        const btnBySlot = new Map();
        for (const spec of EZ_OMNI_UPLOAD_BTN_SPECS) {
            const bw = node.widgets.find(x => x && x.name === spec.btnName);
            if (bw) btnBySlot.set(spec.slot, bw);
        }
        const btnSet = new Set(btnBySlot.values());
        let dockW = node.widgets.find(x => x && x.name === "ez_omni_ref_preview_dock");
        if (!dockW && typeof node.addDOMWidget === "function") {
            dockW = node.addDOMWidget("ez_omni_ref_preview_dock", "div", wrap, { serialize: false, hideOnZoom: false });
            if (dockW) {
                dockW.serialize = false;
                dockW.options = Object.assign({}, dockW.options || {}, { serialize: false, hideOnZoom: false });
                dockW.computeSize = (w) => [w, 368];
            }
        }
        const reordered = [];
        for (const w of node.widgets) {
            if (!w || btnSet.has(w) || w === dockW || (w.name === "upload" && w.type === "button")) continue;
            reordered.push(w);
            if (btnBySlot.has(w.name)) {
                reordered.push(btnBySlot.get(w.name));
            }
        }
        if (dockW) reordered.push(dockW);
        node.widgets = reordered;
    };
    node._ezOrderOmniSlotWidgets = ensureAndOrderOmniSlotWidgets;
    ensureAndOrderOmniSlotWidgets();

    const refreshOmniPreviews = () => {
        node.imgs = null;
        node.imageIndex = null;
        const v1 = getSlotVal("slot1_master_image");
        const u1 = buildEzInputImageUrl(v1);
        if (u1) {
            s1Img.style.display = "block";
            s1Empty.style.display = "none";
            if (s1Img.dataset.rawVal !== v1) {
                s1Img.dataset.rawVal = v1;
                s1Img.src = u1;
            }
            getCachedEzThumbImage(v1);
        } else {
            s1Img.style.display = "none";
            s1Empty.style.display = "flex";
            s1Dim.textContent = "None";
            s1Img.dataset.rawVal = "";
        }

        const subCards = wrap.querySelectorAll(".ez-omni-subcard");
        subCards.forEach(card => {
            const slotKey = card.getAttribute("data-slot");
            const isVideoSlot = card.getAttribute("data-kind") === "video" || slotKey === "slot5_reference_video";
            const val = getSlotVal(slotKey);
            const url = buildEzInputImageUrl(val);
            const vidEl = card.querySelector(".ez-omni-sub-vid");
            const imgEl = card.querySelector(".ez-omni-sub-img");
            const emptyEl = card.querySelector(".ez-omni-sub-empty");
            const metaEl = card.querySelector(".ez-omni-sub-meta");
            if (url) {
                const cleanVal = String(val).replace(/\s+\[(input|output|temp)\]$/i, "");
                const shortName = cleanVal.split(/[\\/]/).pop();
                const isAnimImg = /\.(gif|webp|png|jpg|jpeg|bmp)$/i.test(shortName);
                if (isVideoSlot && vidEl && !isAnimImg) {
                    if (imgEl) imgEl.style.display = "none";
                    emptyEl.style.display = "none";
                    vidEl.style.display = "block";
                    if (vidEl.dataset.rawVal !== val) {
                        vidEl.dataset.rawVal = val;
                        metaEl.textContent = shortName;
                        vidEl.onloadedmetadata = () => {
                            metaEl.textContent = `${vidEl.videoWidth}×${vidEl.videoHeight} · ${shortName}`;
                        };
                        vidEl.src = url;
                        try {
                            vidEl.load();
                            const p = vidEl.play();
                            if (p && typeof p.catch === "function") p.catch(() => {});
                        } catch (e) {}
                    }
                } else {
                    if (vidEl) {
                        vidEl.style.display = "none";
                        vidEl.dataset.rawVal = "";
                    }
                    imgEl.style.display = "block";
                    emptyEl.style.display = "none";
                    getCachedEzThumbImage(val);
                    if (imgEl.dataset.rawVal !== val) {
                        imgEl.dataset.rawVal = val;
                        metaEl.textContent = shortName;
                        imgEl.onload = () => {
                            metaEl.textContent = `${imgEl.naturalWidth}×${imgEl.naturalHeight} · ${shortName}`;
                        };
                        imgEl.src = url;
                    }
                }
            } else {
                if (vidEl) {
                    try { vidEl.pause(); } catch (e) {}
                    vidEl.removeAttribute("src");
                    vidEl.style.display = "none";
                    vidEl.dataset.rawVal = "";
                }
                if (imgEl) {
                    imgEl.style.display = "none";
                    imgEl.dataset.rawVal = "";
                }
                emptyEl.style.display = "flex";
                metaEl.textContent = "None";
            }
        });
        if (node.size[1] < 1090) {
            node.setSize([Math.max(node.size[0], 460), 1090]);
        }
        if (app.graph) app.graph.setDirtyCanvas(true, true);
    };

    node._ezRefreshOmniPreviews = refreshOmniPreviews;

    if (s1Img) s1Img.onclick = () => triggerUploadForSlot("slot1_master_image");
    if (s1Empty) s1Empty.onclick = () => triggerUploadForSlot("slot1_master_image");

    wrap.querySelectorAll(".ez-omni-up-btn").forEach(btn => {
        btn.onclick = (e) => {
            e.stopPropagation();
            triggerUploadForSlot(btn.getAttribute("data-slot"));
        };
    });
    wrap.querySelectorAll(".ez-omni-clr-btn").forEach(btn => {
        btn.onclick = (e) => {
            e.stopPropagation();
            setSlotVal(btn.getAttribute("data-slot"), "None");
        };
    });
    wrap.querySelectorAll(".ez-omni-subcard").forEach(card => {
        const slotKey = card.getAttribute("data-slot");
        const vidEl = card.querySelector(".ez-omni-sub-vid");
        const imgEl = card.querySelector(".ez-omni-sub-img");
        const emptyEl = card.querySelector(".ez-omni-sub-empty");
        if (vidEl) vidEl.onclick = () => triggerUploadForSlot(slotKey);
        if (imgEl) imgEl.onclick = () => triggerUploadForSlot(slotKey);
        if (emptyEl) emptyEl.onclick = () => triggerUploadForSlot(slotKey);
    });

    fileInput.onchange = async () => {
        if (!fileInput.files || !fileInput.files.length) return;
        const file = fileInput.files[0];
        const isVidFile = /\.(mp4|mkv|mov|webm|avi)$/i.test(file.name || "");
        const targetSlot = isVidFile ? "slot5_reference_video" : pendingUploadSlot;
        await uploadFileToEzNodeSlot(file, node, targetSlot);
    };

    if (Array.isArray(node.widgets)) {
        for (const sName of EZ_OMNI_ALL_SLOT_NAMES) {
            const w = node.widgets.find(x => x && x.name === sName);
            if (w && !w._ezOmniPreviewHooked) {
                w._ezOmniPreviewHooked = true;
                const origCb = w.callback;
                w.callback = function () {
                    const r = origCb ? origCb.apply(this, arguments) : undefined;
                    setTimeout(() => refreshOmniPreviews(), 10);
                    return r;
                };
            }
        }
    }
    const origDrawBg = node.onDrawBackground;
    node.onDrawBackground = function () {
        this.imgs = null;
        this.imageIndex = null;
        return origDrawBg ? origDrawBg.apply(this, arguments) : undefined;
    };
    syncEzLiveInputMediaFromServer(false);
    refreshOmniPreviews();
}

function inferEzImageArchFromUnetName(filename) {
    const raw = String(filename || "").replace(/\\/g, "/").toLowerCase();
    if (!raw || raw === "none") {
        return { clipType: "krea2", clipSkip: -1, civitaiArch: "KREA2" };
    }
    const isKrea = /(krea[\s_\-]?2|krea2|flux1[\s_\-]?krea|musebystableyogi|cutedisaster.*krea|snofs.*krea)/.test(raw);
    if (!isKrea) {
        if (/(illustrious|ilxl|noobai|wainsfw|wai[\s_\-]?illustrious|wai[\s_\-]?nsfw|inanime|arblend|hassaku)/.test(raw)) {
            return { clipType: "illustrious", clipSkip: -2, civitaiArch: "Illustrious" };
        }
        if (/(pony|pdxl|autismmix|cyberrealistic[\s_\-]?pony|ponydiffusion)/.test(raw)) {
            return { clipType: "pony", clipSkip: -2, civitaiArch: "Pony" };
        }
        if (/(sdxl|juggernaut|realvis|lustify|bigasp|epicrealismxl|dreamshaperxl)/.test(raw)) {
            return { clipType: "sdxl", clipSkip: -1, civitaiArch: "SDXL 1.0" };
        }
        if (/(qwen[\s_\-]?image|qwenimage)/.test(raw)) {
            return { clipType: "krea2", clipSkip: -1, civitaiArch: "Qwen-Image" };
        }
        if (/(flux1[\s_\-]?schnell|flux\.1[\s_\-]?schnell|schnell)/.test(raw)) {
            return { clipType: "flux", clipSkip: -1, civitaiArch: "Flux.1 S" };
        }
        if (/(flux|chroma|shuttle|pixelwave)/.test(raw)) {
            return { clipType: "flux", clipSkip: -1, civitaiArch: "Flux.1 D" };
        }
    }
    return { clipType: "krea2", clipSkip: -1, civitaiArch: "KREA2" };
}

// CIVITAI CONTROLLER & LORA MANAGER WEB-WINDOW STUDIO (Mounted on EZ [10])
function collapseEzCivitaiNativeWidgets(node, hideRaw = true) {
    if (!node || !Array.isArray(node.widgets)) return;
    node.widgets.forEach(w => {
        if (!w || w.name === "ez_civitai_browser_hub") return;
        if (!w._ezOrigType) {
            w._ezOrigType = w.type;
            w._ezOrigComputeSize = w.computeSize;
            w._ezOrigDraw = w.draw;
        }
        if (hideRaw) {
            w.type = "converted-widget";
            w.computeSize = () => [0, -4];
            w.draw = () => {};
        } else {
            w.type = w._ezOrigType;
            if (w._ezOrigComputeSize) w.computeSize = w._ezOrigComputeSize;
            else delete w.computeSize;
            if (w._ezOrigDraw) w.draw = w._ezOrigDraw;
            else delete w.draw;
        }
    });
    if (app.graph) app.graph.setDirtyCanvas(true, true);
}

function mountEzCivitaiControllerWidget(node) {
    if (!node || node._ezCivitaiDom) return;
    collapseEzCivitaiNativeWidgets(node, true);

    const state = {
        activeTab: "stack",
        stackModality: "IMAGE",
        localFilterMod: "ALL",
        localFilterType: "LORA",
        localQuery: "",
        localLoras: [],
        localModels: [],
        localResources: [],
        civModality: "IMAGE",
        civType: "LORA",
        civArch: "KREA2",
        civSort: "Most Downloaded",
        civPeriod: "AllTime",
        civDomain: "civitai.com",
        civQuery: "",
        civItems: [],
        civInspectedItem: null,
        hfQuery: "",
        hfCategory: "ALL",
        hfTargetFolder: "LLM/Qwen-VL",
        hfItems: [],
        hfCurated: [],
        hfInspectedRepo: "",
        hfInspectedFiles: [],
        hasHfToken: false,
        maskedHfToken: "",
        recipes: [],
        downloadsQueue: [],
        downloadsSummary: { total_files: 0, total_count: 0, active_count: 0, completed_count: 0, failed_count: 0, total_mb: 0, total_size_mb: 0, downloaded_mb: 0, total_downloaded_mb: 0, overall_percent: 0, total_speed_mbps: 0, total_eta_sec: 0 },
        dlPollTimer: null,
        lastCompletedCount: 0,
        licensed: false,
        hasKey: false,
        maskedKey: "",
        cacheFiles: 0,
        lastThumbFile: "",
        showRawWidgets: false,
        imageCompanions: null,
        videoCompanions: null,
        statusMsg: "Ready in Civitai & HuggingFace Model Hub"
    };

    const getWidgetVal = (wName, fallback) => {
        if (!Array.isArray(node.widgets)) return fallback;
        const w = node.widgets.find(x => x.name === wName);
        return (w && w.value !== undefined && w.value !== null) ? w.value : fallback;
    };
    const setWidgetVal = (wName, val) => {
        if (!Array.isArray(node.widgets)) return;
        const w = node.widgets.find(x => x.name === wName);
        if (w) {
            if (w.options && Array.isArray(w.options.values) && val && !w.options.values.includes(val)) {
                w.options.values.push(val);
            }
            w.value = val;
            if (typeof w.callback === "function") {
                try { w.callback(val); } catch (e) {}
            }
        }
        if (app.graph) app.graph.setDirtyCanvas(true, true);
    };

    const shortLabel = (val) => {
        const s = String(val || "None");
        if (!s || s === "None") return "— None selected (Click to select) —";
        const base = s.split(/[\\/]/).pop();
        return base.replace(/\.(safetensors|ckpt|pt|bin|gguf)$/i, "");
    };

    const SLOT_STRENGTH_MAP = {
        video_lora_1: "video_lora_1_strength",
        video_lora_2: "video_lora_2_strength",
        video_lora_3: "video_lora_3_strength",
        video_lora_4: "video_lora_4_strength",
        video_turbo_lora: "video_turbo_strength",
        image_style_lora_1: "image_style_strength_1",
        image_style_lora_2: "image_style_strength_2",
        image_style_lora_3: "image_style_strength_3",
        image_style_lora_4: "image_style_strength_4",
        image_turbo_lora: "image_turbo_strength"
    };

    const STRENGTH_TO_SLOT_MAP = {
        video_lora_1_strength: "video_lora_1",
        video_lora_2_strength: "video_lora_2",
        video_lora_3_strength: "video_lora_3",
        video_lora_4_strength: "video_lora_4",
        video_turbo_strength: "video_turbo_lora",
        image_style_strength_1: "image_style_lora_1",
        image_style_strength_2: "image_style_lora_2",
        image_style_strength_3: "image_style_lora_3",
        image_style_strength_4: "image_style_lora_4",
        image_turbo_strength: "image_turbo_lora"
    };

    const SLOT_ENABLE_MAP = {
        video_lora_1: "enable_video_lora_1",
        video_lora_2: "enable_video_lora_2",
        video_lora_3: "enable_video_lora_3",
        video_lora_4: "enable_video_lora_4",
        video_turbo_lora: "enable_video_turbo_lora",
        image_style_lora_1: "enable_image_lora_1",
        image_style_lora_2: "enable_image_lora_2",
        image_style_lora_3: "enable_image_lora_3",
        image_style_lora_4: "enable_image_lora_4",
        image_turbo_lora: "enable_image_turbo_lora"
    };

    const setNodeDownstreamWidget = (targetNode, wName, val) => {
        if (!targetNode || !Array.isArray(targetNode.widgets)) return false;
        const wIdx = targetNode.widgets.findIndex(x => x && x.name === wName);
        if (wIdx < 0) return false;
        const w = targetNode.widgets[wIdx];
        let canonicalVal = val;
        if (w.options && Array.isArray(w.options.values) && typeof val === "string" && val !== "") {
            const opts = w.options.values;
            const vNorm = val.replace(/\\/g, "/").toLowerCase();
            const vBase = vNorm.split("/").pop();
            const exact = opts.find(o => o === val);
            const slashMatch = exact === undefined
                ? opts.find(o => String(o || "").replace(/\\/g, "/").toLowerCase() === vNorm)
                : undefined;
            const baseMatch = (exact === undefined && slashMatch === undefined && vBase && vBase !== "none")
                ? opts.find(o => String(o || "").replace(/\\/g, "/").toLowerCase().split("/").pop() === vBase)
                : undefined;
            canonicalVal = exact !== undefined
                ? exact
                : (slashMatch !== undefined ? slashMatch : (baseMatch !== undefined ? baseMatch : val));
            if (!opts.includes(canonicalVal)) {
                opts.push(canonicalVal);
            }
        }
        w.value = canonicalVal;
        if (Array.isArray(targetNode.widgets_values) && wIdx < targetNode.widgets_values.length) {
            targetNode.widgets_values[wIdx] = canonicalVal;
        }
        if (targetNode.properties && targetNode.properties._ez_widget_map && typeof targetNode.properties._ez_widget_map === "object") {
            targetNode.properties._ez_widget_map[wName] = canonicalVal;
        }
        if (typeof w.callback === "function") {
            try { w.callback(canonicalVal, app.canvas, targetNode, [0, 0], null); } catch (e) {}
        }
        if (typeof targetNode.setDirtyCanvas === "function") {
            targetNode.setDirtyCanvas(true, true);
        }
        return true;
    };

    const isImageLoaderNode = (gn) => {
        if (!gn || detectEzNodeEdition(gn) !== detectEzNodeEdition(node)) return false;
        const ct = stripEzEditionSuffix(String((gn && (gn.comfyClass || gn.type)) || ""));
        return ct === "EZCinematrixImageModelAndLoraSplitter" || ct.includes("03_Cinematrix");
    };

    const isVideoLoaderNode = (gn) => {
        if (!gn || detectEzNodeEdition(gn) !== detectEzNodeEdition(node)) return false;
        const ct = stripEzEditionSuffix(String((gn && (gn.comfyClass || gn.type)) || ""));
        return ct === "EZCinematrixVideoEngineAndLoraStack" || ct.includes("05_Cinematrix") || ct.includes("EZCinematrixVideoLoRAStack");
    };

    const syncSlotToDownstreamGraphNodes = (slotKey, filename, strengthVal = null, enableVal = null) => {
        if (!app || !app.graph || !Array.isArray(app.graph._nodes)) return;
        const DOWNSTREAM_MAP = {
            image_unet_name:    { isVid: false, w: "unet_name" },
            image_style_lora_1: { isVid: false, w: "style_lora_1", sW: "style_strength_1", eW: "enable_style_lora_1" },
            image_style_lora_2: { isVid: false, w: "style_lora_2", sW: "style_strength_2", eW: "enable_style_lora_2" },
            image_style_lora_3: { isVid: false, w: "style_lora_3", sW: "style_strength_3", eW: "enable_style_lora_3" },
            image_style_lora_4: { isVid: false, w: "style_lora_4", sW: "style_strength_4", eW: "enable_style_lora_4" },
            image_turbo_lora:   { isVid: false, w: "turbo_acceleration_lora_LOCKED", sW: "turbo_strength", eW: "enable_turbo_lora" },
            video_unet_fl2va:   { isVid: true,  w: "video_unet_fl2va" },
            video_lora_1:       { isVid: true,  w: "video_lora_1", sW: "lora_1_video_strength", eW: "enable_video_lora_1" },
            video_lora_2:       { isVid: true,  w: "video_lora_2", sW: "lora_2_video_strength", eW: "enable_video_lora_2" },
            video_lora_3:       { isVid: true,  w: "video_lora_3", sW: "lora_3_video_strength", eW: "enable_video_lora_3" },
            video_lora_4:       { isVid: true,  w: "video_lora_4", sW: "lora_4_video_strength", eW: "enable_video_lora_4" },
            video_turbo_lora:   { isVid: true,  w: "video_turbo_lora_LOCKED", sW: "turbo_video_strength", eW: "enable_video_turbo_lora" }
        };
        const spec = DOWNSTREAM_MAP[slotKey];
        if (!spec) return;
        for (const gn of app.graph._nodes) {
            if (spec.isVid ? isVideoLoaderNode(gn) : isImageLoaderNode(gn)) {
                if (filename !== null && filename !== undefined) {
                    setNodeDownstreamWidget(gn, spec.w, filename);
                    if (slotKey === "image_unet_name" && filename && filename !== "None") {
                        const infArch = inferEzImageArchFromUnetName(filename);
                        setNodeDownstreamWidget(gn, "clip_type", infArch.clipType);
                        setNodeDownstreamWidget(gn, "stop_at_clip_layer", infArch.clipSkip);
                    }
                }
                if (spec.sW && typeof strengthVal === "number" && !Number.isNaN(strengthVal)) {
                    setNodeDownstreamWidget(gn, spec.sW, strengthVal);
                }
                if (spec.eW && typeof enableVal === "boolean") {
                    setNodeDownstreamWidget(gn, spec.eW, enableVal);
                }
            }
        }
        app.graph.setDirtyCanvas(true, true);
    };

    const syncResourceToDownstreamGraphNodes = (role, filename, modality = "IMAGE") => {
        if (!filename || filename === "None" || !app || !app.graph || !Array.isArray(app.graph._nodes)) return false;
        const rUp = String(role || "").toUpperCase();
        const isVid = String(modality || "").toUpperCase() === "VIDEO";
        if (rUp === "VLM") {
            return assignVlmToTimelineCompiler(filename);
        }
        if (rUp === "UNET") {
            return assignAssetToSlot(isVid ? "video_unet_fl2va" : "image_unet_name", filename, isVid ? "VIDEO" : "IMAGE");
        }
        if (rUp === "TURBO_LORA") {
            return assignAssetToSlot(isVid ? "video_turbo_lora" : "image_turbo_lora", filename, isVid ? "VIDEO" : "IMAGE");
        }
        let updated = false;
        for (const gn of app.graph._nodes) {
            if (!isVid && isImageLoaderNode(gn)) {
                if (rUp === "CLIP" && setNodeDownstreamWidget(gn, "clip_name", filename)) {
                    if (/qwen3vl|qwen3-vl|krea/i.test(filename)) setNodeDownstreamWidget(gn, "clip_type", "krea2");
                    updated = true;
                }
                if (rUp === "VAE" && setNodeDownstreamWidget(gn, "vae_name", filename)) updated = true;
            }
            if (isVid && isVideoLoaderNode(gn)) {
                if (rUp === "CLIP" && setNodeDownstreamWidget(gn, "video_clip_name", filename)) {
                    if (/qwen3vl|qwen3-vl|krea|minimax|h3/i.test(filename)) setNodeDownstreamWidget(gn, "clip_type", "minimax");
                    updated = true;
                }
                if (rUp === "VAE" && setNodeDownstreamWidget(gn, "video_vae_name", filename)) updated = true;
                if (rUp === "AUDIO_VAE" && setNodeDownstreamWidget(gn, "audio_vae_name", filename)) updated = true;
            }
        }
        if (updated && app.graph) app.graph.setDirtyCanvas(true, true);
        return updated;
    };

    const isTrueTurboLoraName = (nameStr) => {
        const bLow = String(nameStr || "").split(/[\\/]/).pop().toLowerCase();
        if (!bLow) return false;
        const hasAccelToken = /(?:^|[\s_\-.])(dmd2|pcm|lcm|hyper[\s_\-]?sd|sdxl[\s_\-]?lightning|flux[\s_\-]?hyper|qwen[\s_\-]?image[\s_\-]?lightning|wan[\s_\-]?lightning|4[\s_\-]?steps?|8[\s_\-]?steps?|step600|step[\s_\-]?\d{3,4}|causvid|fast[\s_\-]?lora|turbo[\s_\-]?lora|lora[\s_\-]?turbo|lightning)(?:$|[\s_\-.])/i.test(bLow);
        if (hasAccelToken) return true;
        if (/(?:^|[\s_\-.])turbo(?:$|[\s_\-.])/i.test(bLow)) {
            if (/realism|realistic|style|detail|skin|face|portrait|anime|character|outfit|clothing|lighting|slider|concept|nsfw|beauty|girl|woman|photo|cinematic|enhancer|aesthetic/i.test(bLow) && !/4step|8step|lcm|dmd2|lightning|fast|accel/i.test(bLow)) {
                return false;
            }
            return true;
        }
        return false;
    };

    const detectFrontendAssetTrueRole = (nameStr, assetTypeHint = "") => {
        const raw = String(nameStr || "").trim();
        if (!raw || raw === "None") return "NONE";
        let baseLow = raw.split(/[\\/]/).pop().toLowerCase();
        if (baseLow.startsWith("img_")) baseLow = baseLow.slice(4);
        if (baseLow.startsWith("vid_")) baseLow = baseLow.slice(4);
        if (baseLow.includes("mmproj") && baseLow.endsWith(".gguf")) return "MMPROJ";
        const isVlmName = /qwen3vl|qwen3-vl|qwen3_vl|qwen2\.5-vl|qwen2_5_vl|qwen-vl|qwen_vl|huihui|llava|florence|minicpm|internvl/i.test(baseLow);
        if (isVlmName && baseLow.endsWith(".gguf")) return "VLM";
        if (isVlmName && /instruct|chat|8b|7b|32b/i.test(baseLow) && !/comfyui|4b_fp8_scaled|minimax_h3|nvfp4|awq|text_encoder/i.test(baseLow)) return "VLM";
        if (/qwen3vl|qwen3-vl|qwen3_vl|qwen2\.5-vl|qwen-vl|qwen_vl|t5xxl|umt5|clip_l|clip_g|text_encoder|te_fp8|llava_llama3/i.test(baseLow)) return "CLIP";
        if (baseLow.includes("audio_vae")) return "AUDIO_VAE";
        if (["ae.safetensors", "ae.sft", "qwen_image_vae.safetensors", "wan_2.1_vae.safetensors", "wan_2.2_vae.safetensors", "sdxl_vae.safetensors"].includes(baseLow) || /_vae|video_vae|flux_vae|vae_fp16|vae_bf16|vae_int8/i.test(baseLow)) return "VAE";
        const hintUp = String(assetTypeHint || "").toUpperCase();
        if (hintUp === "LORA" || /(?:^|[\s_\-.])(lora|lycoris|locon|loha|dora)(?:$|[\s_\-.])/i.test(baseLow)) return "LORA";
        return "UNET";
    };

    const hydrateSlotsFromGraphNodes = (forceHydrate = false) => {
        if (!app || !app.graph || !Array.isArray(app.graph._nodes) || app.graph._nodes.length === 0) return;
        const allowInitialHydrate = forceHydrate || !state._hydratedFromGraphOnce;
        let sawLoaderNode = false;
        for (const gn of app.graph._nodes) {
            if (isImageLoaderNode(gn) && Array.isArray(gn.widgets)) {
                sawLoaderNode = true;
                const map03 = [
                    ["image_unet_name", "unet_name"],
                    ["image_style_lora_1", "style_lora_1"],
                    ["image_style_lora_2", "style_lora_2"],
                    ["image_style_lora_3", "style_lora_3"],
                    ["image_style_lora_4", "style_lora_4"],
                    ["image_turbo_lora", "turbo_acceleration_lora_LOCKED"]
                ];
                for (const [sKey, wName] of map03) {
                    const curV = String(getWidgetVal(sKey, "None"));
                    if (sKey === "image_unet_name" && curV !== "None" && detectFrontendAssetTrueRole(curV) !== "UNET") {
                        setWidgetVal(sKey, "None");
                    }
                    if (allowInitialHydrate && String(getWidgetVal(sKey, "None")) === "None") {
                        const w = gn.widgets.find(x => x && x.name === wName);
                        if (w && w.value && String(w.value) !== "None") {
                            if (sKey === "image_unet_name" && detectFrontendAssetTrueRole(w.value) !== "UNET") continue;
                            setWidgetVal(sKey, String(w.value));
                        }
                    }
                }
            } else if (isVideoLoaderNode(gn) && Array.isArray(gn.widgets)) {
                sawLoaderNode = true;
                const map05 = [
                    ["video_unet_fl2va", "video_unet_fl2va"],
                    ["video_lora_1", "video_lora_1"],
                    ["video_lora_2", "video_lora_2"],
                    ["video_lora_3", "video_lora_3"],
                    ["video_lora_4", "video_lora_4"],
                    ["video_turbo_lora", "video_turbo_lora_LOCKED"]
                ];
                for (const [sKey, wName] of map05) {
                    const curV = String(getWidgetVal(sKey, "None"));
                    if (sKey === "video_unet_fl2va" && curV !== "None" && detectFrontendAssetTrueRole(curV) !== "UNET") {
                        setWidgetVal(sKey, "None");
                    }
                    if (allowInitialHydrate && String(getWidgetVal(sKey, "None")) === "None") {
                        const w = gn.widgets.find(x => x && x.name === wName);
                        if (w && w.value && String(w.value) !== "None") {
                            if (sKey === "video_unet_fl2va" && detectFrontendAssetTrueRole(w.value) !== "UNET") continue;
                            setWidgetVal(sKey, String(w.value));
                        }
                    }
                }
            }
        }
        if (sawLoaderNode) {
            state._hydratedFromGraphOnce = true;
        }
    };

    const getAvailableSlotOptions = (slotKey, isLora, isVid) => {
        const modTarget = isVid ? "VIDEO" : "IMAGE";
        const isValidCandidateForSlot = (nameVal) => {
            if (!nameVal || nameVal === "None") return false;
            if (!isLora) {
                if (detectFrontendAssetTrueRole(nameVal, "Checkpoint") !== "UNET") return false;
                const bLow = String(nameVal).split(/[\\/]/).pop().toLowerCase();
                const isVidUnet = /(?:^|[\s_\-.])(minimax|h3|fl2va|ref2va|hailuo|wan2\.1|wan2\.2|wan2|wan_video|ltxv|ltx[\s_\-]?video|hunyuan[\s_\-]?video|mochi|cogvideox)(?:$|[\s_\-.])|^vid_/i.test(bLow);
                const isImgUnet = /(?:^|[\s_\-.])(krea2?|flux|chroma|sdxl|pony|pdxl|autismmix|illustrious|ilxl|noobai|wainsfw|inanime|arblend|juggernaut|realvis|lustify|qwen[\s_\-]?image|sd1\.?5|sd3\.?5|playground|pixart|auraflow|kolors)(?:$|[\s_\-.])|^img_/i.test(bLow);
                if (!isVid && isVidUnet && !isImgUnet) return false;
                if (isVid && isImgUnet && !isVidUnet) return false;
            }
            return true;
        };
        const fromCatalog = (isLora ? state.localLoras : state.localModels)
            .filter(it => (!it.modality || it.modality === modTarget || it.modality === "UNKNOWN") && isValidCandidateForSlot(it.name))
            .map(it => ({
                name: it.name,
                badge: it.is_optimal_for_tier ? "🏆 " : (it.optimal_tier_level === "SUBOPTIMAL" ? "⚠️ " : ""),
                size_mb: it.size_mb || 0
            }));
        const seen = new Set(fromCatalog.map(x => x.name));
        if (Array.isArray(node.widgets)) {
            const nw = node.widgets.find(x => x && x.name === slotKey);
            const vals = (nw && nw.options && Array.isArray(nw.options.values)) ? nw.options.values : [];
            for (const v of vals) {
                if (v && v !== "None" && !seen.has(v) && isValidCandidateForSlot(v)) {
                    seen.add(v);
                    fromCatalog.push({ name: v, badge: "", size_mb: 0 });
                }
            }
        }
        return fromCatalog;
    };

    const assignAssetToSlot = (slotKey, filename, itemModality, triggerWords = [], thumbFile = "", optSettings = null) => {
        const isVideoSlot = slotKey.startsWith("video_");
        const isUnetSlot = slotKey === "image_unet_name" || slotKey === "video_unet_fl2va";
        if (isUnetSlot && filename && filename !== "None") {
            const trueRole = detectFrontendAssetTrueRole(filename, "Checkpoint");
            if (trueRole === "VLM" || trueRole === "MMPROJ") {
                assignVlmToTimelineCompiler(filename);
                state.statusMsg = `🧠 Auto-dirigerade Qwen3-VL (${shortLabel(filename)}) till [02] Qwen3-VL Timeline (ej till UNet-loader)!`;
                syncAllViews();
                return true;
            }
            if (trueRole === "CLIP") {
                const targetMod = isVideoSlot ? "VIDEO" : "IMAGE";
                syncResourceToDownstreamGraphNodes("CLIP", filename, targetMod);
                state.statusMsg = `🔤 Auto-dirigerade Text Encoder (${shortLabel(filename)}) till ${isVideoSlot ? "[05] video_clip_name" : "[03] clip_name"} (ej till UNet-loader)!`;
                syncAllViews();
                return true;
            }
            if (trueRole === "VAE" || trueRole === "AUDIO_VAE") {
                const targetMod = trueRole === "AUDIO_VAE" || isVideoSlot ? "VIDEO" : "IMAGE";
                syncResourceToDownstreamGraphNodes(trueRole, filename, targetMod);
                state.statusMsg = `🎨 Auto-dirigerade ${trueRole} (${shortLabel(filename)}) till ${targetMod === "VIDEO" ? "[05]" : "[03]"} VAE-slot!`;
                syncAllViews();
                return true;
            }
        }
        const normMod = String(itemModality || "").toUpperCase();
        if (isVideoSlot && normMod === "IMAGE") {
            state.statusMsg = "⛔ MODALITY LOCK: Image asset cannot be sent to a VIDEO slot!";
            syncAllViews();
            return false;
        }
        if (!isVideoSlot && normMod === "VIDEO") {
            state.statusMsg = "⛔ MODALITY LOCK: Video asset cannot be sent to an IMAGE slot!";
            syncAllViews();
            return false;
        }
        setWidgetVal(slotKey, filename);
        if (slotKey === "image_unet_name" && filename && filename !== "None") {
            const infArch = inferEzImageArchFromUnetName(filename);
            setWidgetVal("image_architecture", infArch.civitaiArch);
        }
        const sKey = SLOT_STRENGTH_MAP[slotKey];
        let appliedStrength = null;
        if (sKey && optSettings && typeof optSettings.rec_strength === "number") {
            appliedStrength = optSettings.rec_strength;
            setWidgetVal(sKey, appliedStrength);
        } else if (sKey) {
            appliedStrength = parseFloat(getWidgetVal(sKey, 0.75));
        }
        syncSlotToDownstreamGraphNodes(slotKey, filename, appliedStrength);
        if (Array.isArray(triggerWords) && triggerWords.length > 0) {
            const curTw = String(getWidgetVal("trigger_words", "") || "").trim();
            const merged = Array.from(new Set(
                (curTw ? curTw.split(",").map(x => x.trim()) : []).concat(triggerWords.map(x => String(x).trim()))
            )).filter(Boolean).join(", ");
            setWidgetVal("trigger_words", merged);
        }
        if (thumbFile) state.lastThumbFile = thumbFile;
        const activeArchNow = getWidgetVal(isVideoSlot ? "video_architecture" : "image_architecture", isVideoSlot ? "MiniMax H3" : "KREA2");
        fetchArchitectureCompanions(activeArchNow, isVideoSlot ? "VIDEO" : "IMAGE", "resolve");
        state.statusMsg = `📤 Sent ${shortLabel(filename)} -> ${slotKey} (& synced to ${isVideoSlot ? "[05]" : "[03]"})${optSettings && optSettings.rec_strength ? ` [Rec: ${optSettings.rec_strength}]` : ""}`;
        syncAllViews();
        return true;
    };

    const autoAssignNextSlot = (filename, assetType, modality, isTurbo = false, triggerWords = [], thumbFile = "", optSettings = null) => {
        const isVid = String(modality || "").toUpperCase() === "VIDEO";
        const isCheck = String(assetType || "").toUpperCase() !== "LORA";
        if (isCheck) {
            const trueRole = detectFrontendAssetTrueRole(filename, assetType);
            if (trueRole === "VLM" || trueRole === "MMPROJ") {
                assignVlmToTimelineCompiler(filename);
                state.statusMsg = `🧠 Kopplade ${shortLabel(filename)} till [02] Qwen3-VL Timeline!`;
                syncAllViews();
                return true;
            }
            if (trueRole === "CLIP" || trueRole === "VAE" || trueRole === "AUDIO_VAE") {
                syncResourceToDownstreamGraphNodes(trueRole, filename, trueRole === "AUDIO_VAE" || isVid ? "VIDEO" : "IMAGE");
                state.statusMsg = `✅ Kopplade ${shortLabel(filename)} (${trueRole}) till ${isVid ? "[05]" : "[03]"}!`;
                syncAllViews();
                return true;
            }
            return assignAssetToSlot(isVid ? "video_unet_fl2va" : "image_unet_name", filename, isVid ? "VIDEO" : "IMAGE", triggerWords, thumbFile, optSettings);
        }
        if (isTurbo || isTrueTurboLoraName(filename)) {
            return assignAssetToSlot(isVid ? "video_turbo_lora" : "image_turbo_lora", filename, isVid ? "VIDEO" : "IMAGE", triggerWords, thumbFile, optSettings);
        }
        const slots = isVid
            ? ["video_lora_1", "video_lora_2", "video_lora_3", "video_lora_4"]
            : ["image_style_lora_1", "image_style_lora_2", "image_style_lora_3", "image_style_lora_4"];
        const target = slots.find(s => String(getWidgetVal(s, "None")) === "None") || slots[0];
        return assignAssetToSlot(target, filename, isVid ? "VIDEO" : "IMAGE", triggerWords, thumbFile, optSettings);
    };

    const applyOptimalSettingsToConnectedGraph = (isVid) => {
        const comp = isVid ? state.videoCompanions : state.imageCompanions;
        const opt = (comp && comp.optimal_settings) || (isVid
            ? { sampler: "res_multistep", scheduler: "simple", steps: 8, cfg: 1.0, denoise: 1.0, shift_video: 5.0, shift_audio: 3.0 }
            : { sampler: "euler", scheduler: "beta / simple", steps: 52, cfg: 3.0, denoise: 0.75, stage1_steps: 52, stage1_cfg: 3.0, stage1_sampler: "euler", stage1_scheduler: "beta", stage2_steps: 14, stage2_cfg: 1.0, stage2_sampler: "euler", stage2_scheduler: "simple", handoff_percent: 16.0, stage3_handoff_percent: 90.0 });
        const isDistilled = Boolean(opt.is_distilled_checkpoint);
        const recTurboStr = typeof opt.turbo_strength === "number" ? opt.turbo_strength : (isDistilled ? 0.0 : (isVid ? 1.0 : 0.9));
        const loraProfiles = Array.isArray(opt.selected_lora_profiles) ? opt.selected_lora_profiles : [];
        const resolveSlotProfile = (slotIdx, lName) => {
            const bName = String(lName || "").split(/[\\/]/).pop().toLowerCase();
            return loraProfiles.find(lp => lp && (
                lp.slot_index === slotIdx ||
                (lp.lora_name && bName && (
                    bName === String(lp.lora_name).split(/[\\/]/).pop().toLowerCase() ||
                    bName.includes(String(lp.lora_name).toLowerCase())
                ))
            )) || null;
        };
        const resolveSlotBalancedWeight = (slotIdx, lName, fallbackVal) => {
            const profMatch = resolveSlotProfile(slotIdx, lName);
            if (profMatch && typeof profMatch.stack_balanced_strength === "number") {
                return profMatch.stack_balanced_strength;
            }
            if (profMatch && typeof profMatch.rec_strength === "number") {
                return profMatch.rec_strength;
            }
            return fallbackVal;
        };
        let activeUnet = String(getWidgetVal(isVid ? "video_unet_fl2va" : "image_unet_name", "None") || "None");
        if ((activeUnet === "None" || !activeUnet) && comp && comp.unet_name && comp.unet_name !== "None") {
            activeUnet = String(comp.unet_name);
            setWidgetVal(isVid ? "video_unet_fl2va" : "image_unet_name", activeUnet);
        }
        let activeTurbo = String(getWidgetVal(isVid ? "video_turbo_lora" : "image_turbo_lora", "None") || "None");
        if ((activeTurbo === "None" || !activeTurbo) && !isDistilled && comp && comp.turbo_lora_name && comp.turbo_lora_name !== "None") {
            activeTurbo = String(comp.turbo_lora_name);
            setWidgetVal(isVid ? "video_turbo_lora" : "image_turbo_lora", activeTurbo);
        }
        const activeLoraSlots = [];
        if (isVid) {
            for (const idx of [1, 2, 3, 4]) {
                const vVal = String(getWidgetVal(`video_lora_${idx}`, "None") || "None");
                const defW = /motion/i.test(vVal) ? 0.16 : (idx === 1 ? 0.25 : 0.20);
                const wStr = (vVal !== "None" && vVal !== "")
                    ? resolveSlotBalancedWeight(idx, vVal, defW)
                    : parseFloat(getWidgetVal(`video_lora_${idx}_strength`, defW));
                if (vVal !== "None" && vVal !== "") {
                    setWidgetVal(`video_lora_${idx}_strength`, wStr);
                }
                activeLoraSlots.push({ idx, name: vVal, strength: wStr, prof: resolveSlotProfile(idx, vVal) });
            }
            setWidgetVal("video_turbo_strength", recTurboStr);
        } else {
            for (const idx of [1, 2, 3, 4]) {
                const iVal = String(getWidgetVal(`image_style_lora_${idx}`, "None") || "None");
                const wStr = (iVal !== "None" && iVal !== "")
                    ? resolveSlotBalancedWeight(idx, iVal, 0.72)
                    : parseFloat(getWidgetVal(`image_style_strength_${idx}`, 0.72));
                if (iVal !== "None" && iVal !== "") {
                    setWidgetVal(`image_style_strength_${idx}`, wStr);
                }
                activeLoraSlots.push({ idx, name: iVal, strength: wStr, prof: resolveSlotProfile(idx, iVal) });
            }
            setWidgetVal("image_turbo_strength", recTurboStr);
        }
        const graphNodes = (app.graph && app.graph._nodes) || [];
        let updatedCount = 0;
        const syncedModelsSummary = [];
        for (const gn of graphNodes) {
            const ct = String(gn.comfyClass || gn.type || "");
            if (isVid && isVideoLoaderNode(gn)) {
                if (activeUnet && activeUnet !== "None") {
                    setNodeDownstreamWidget(gn, "video_unet_fl2va", activeUnet);
                    syncedModelsSummary.push(`UNet: ${shortLabel(activeUnet)}`);
                }
                if (comp && comp.clip_name && comp.clip_name !== "None") {
                    setNodeDownstreamWidget(gn, "video_clip_name", comp.clip_name);
                }
                if (comp && comp.clip_type) {
                    setNodeDownstreamWidget(gn, "clip_type", comp.clip_type);
                }
                if (comp && comp.vae_name && comp.vae_name !== "None") {
                    setNodeDownstreamWidget(gn, "video_vae_name", comp.vae_name);
                }
                if (comp && comp.audio_vae_name && comp.audio_vae_name !== "None") {
                    setNodeDownstreamWidget(gn, "audio_vae_name", comp.audio_vae_name);
                }
                for (const slotObj of activeLoraSlots) {
                    const idx = slotObj.idx;
                    const lName = slotObj.name || "None";
                    const lp = slotObj.prof;
                    const isAud = /audio|sound|voice|vocal|sfx|moaw|moan|whisper/i.test(lName) && !/turbo/i.test(lName);
                    setNodeDownstreamWidget(gn, `video_lora_${idx}`, lName);
                    setNodeDownstreamWidget(gn, `lora_${idx}_video_strength`, slotObj.strength);
                    setNodeDownstreamWidget(gn, `lora_${idx}_vis_strength`, (lp && typeof lp.vis_strength === "number") ? lp.vis_strength : 1.0);
                    setNodeDownstreamWidget(gn, `lora_${idx}_audio_strength`, (lp && typeof lp.audio_strength === "number") ? lp.audio_strength : (isAud ? 1.0 : 0.0));
                    setNodeDownstreamWidget(gn, `lora_${idx}_clip_strength`, (lp && typeof lp.clip_strength === "number") ? lp.clip_strength : 0.0);
                    if (lName !== "None") {
                        syncedModelsSummary.push(`LoRA ${idx}: ${shortLabel(lName)} (${ Number(slotObj.strength).toFixed(2) })`);
                    }
                }
                if (activeTurbo && activeTurbo !== "None") {
                    setNodeDownstreamWidget(gn, "video_turbo_lora_LOCKED", activeTurbo);
                    syncedModelsSummary.push(`Turbo: ${shortLabel(activeTurbo)} (${Number(recTurboStr).toFixed(2)})`);
                }
                const turboProf = resolveSlotProfile(4, activeTurbo);
                setNodeDownstreamWidget(gn, "turbo_video_strength", recTurboStr);
                setNodeDownstreamWidget(gn, "turbo_vis_strength", (turboProf && typeof turboProf.vis_strength === "number") ? turboProf.vis_strength : 1.0);
                setNodeDownstreamWidget(gn, "turbo_audio_strength", (turboProf && typeof turboProf.audio_strength === "number") ? turboProf.audio_strength : 1.0);
                setNodeDownstreamWidget(gn, "shift_video", opt.shift_video ?? 5.0);
                setNodeDownstreamWidget(gn, "shift_audio", opt.shift_audio ?? 3.0);
                updatedCount++;
            } else if (isVid && (ct.includes("07_Cinematrix_Joint_AV_Sampler") || ct.includes("EZCinematrixJointAVSampler") || ct.includes("EZCinematrixJointAVTemporalSampler"))) {
                setNodeDownstreamWidget(gn, "sampler_name", opt.sampler || "res_multistep");
                setNodeDownstreamWidget(gn, "scheduler", opt.scheduler || "simple");
                setNodeDownstreamWidget(gn, "steps", opt.steps || 8);
                setNodeDownstreamWidget(gn, "cfg", opt.cfg ?? 1.0);
                setNodeDownstreamWidget(gn, "denoise", opt.denoise ?? 1.0);
                updatedCount++;
            } else if (!isVid && isImageLoaderNode(gn)) {
                if (activeUnet && activeUnet !== "None") {
                    setNodeDownstreamWidget(gn, "unet_name", activeUnet);
                    syncedModelsSummary.push(`UNet: ${shortLabel(activeUnet)}`);
                }
                if (comp && comp.clip_name && comp.clip_name !== "None") setNodeDownstreamWidget(gn, "clip_name", comp.clip_name);
                if (comp && comp.clip_type) setNodeDownstreamWidget(gn, "clip_type", comp.clip_type);
                if (comp && comp.vae_name && comp.vae_name !== "None") setNodeDownstreamWidget(gn, "vae_name", comp.vae_name);
                if (opt.clip_skip) {
                    setNodeDownstreamWidget(gn, "stop_at_clip_layer", -Math.abs(Number(opt.clip_skip) || 1));
                }
                for (const slotObj of activeLoraSlots) {
                    const idx = slotObj.idx;
                    const lName = slotObj.name || "None";
                    const lp = slotObj.prof;
                    setNodeDownstreamWidget(gn, `style_lora_${idx}`, lName);
                    setNodeDownstreamWidget(gn, `style_strength_${idx}`, slotObj.strength);
                    setNodeDownstreamWidget(gn, `style_clip_strength_${idx}`, (lp && typeof lp.clip_strength === "number") ? lp.clip_strength : 1.0);
                    if (lName !== "None") {
                        syncedModelsSummary.push(`LoRA ${idx}: ${shortLabel(lName)} (${Number(slotObj.strength).toFixed(2)})`);
                    }
                }
                if (activeTurbo && activeTurbo !== "None") {
                    setNodeDownstreamWidget(gn, "turbo_acceleration_lora_LOCKED", activeTurbo);
                    syncedModelsSummary.push(`Turbo: ${shortLabel(activeTurbo)} (${Number(recTurboStr).toFixed(2)})`);
                }
                setNodeDownstreamWidget(gn, "turbo_strength", recTurboStr);
                updatedCount++;
            } else if (!isVid && (ct.includes("EZCinematrixKrea2ThreeStageSampler") || ct.includes("04_Cinematrix"))) {
                setNodeDownstreamWidget(gn, "handoff_percent", opt.handoff_percent ?? 58.0);
                setNodeDownstreamWidget(gn, "stage3_handoff_percent", opt.stage3_handoff_percent ?? 90.0);
                setNodeDownstreamWidget(gn, "stage1_steps", opt.stage1_steps ?? 52);
                setNodeDownstreamWidget(gn, "stage1_cfg", opt.stage1_cfg ?? 3.0);
                setNodeDownstreamWidget(gn, "stage1_sampler_name", opt.stage1_sampler || "euler");
                setNodeDownstreamWidget(gn, "stage1_scheduler", opt.stage1_scheduler || "beta");
                setNodeDownstreamWidget(gn, "stage2_steps", opt.stage2_steps ?? 14);
                setNodeDownstreamWidget(gn, "stage2_cfg", opt.stage2_cfg ?? 1.0);
                setNodeDownstreamWidget(gn, "stage2_sampler_name", opt.stage2_sampler || "euler");
                setNodeDownstreamWidget(gn, "stage2_scheduler", opt.stage2_scheduler || "simple");
                updatedCount++;
            }
        }
        if (app.graph) app.graph.setDirtyCanvas(true, true);
        const syncedStr = syncedModelsSummary.length > 0 ? ` [${syncedModelsSummary.join(" · ")}]` : "";
        state.statusMsg = `⚡ Applicerade Modell, LoRAs & Optimala inställningar (${opt.sampler}/${opt.scheduler}, Steps ${opt.steps}, CFG ${opt.cfg}) på ${updatedCount} noder (${isVid ? "[05] & [07]" : "[03] & [04]"})${syncedStr}!`;
        syncAllViews();
    };

    const pollDownloadsStatus = async () => {
        try {
            const r = await api.fetchApi("/ez_cinematrix/civitai/downloads_status");
            const d = await r.json();
            if (d && d.status === "ok") {
                const qList = Array.isArray(d.downloads) ? d.downloads : (Array.isArray(d.files) ? d.files : []);
                state.downloadsQueue = qList;
                if (d.summary) state.downloadsSummary = d.summary;
                const activeCnt = (state.downloadsSummary && state.downloadsSummary.active_count) || 0;
                const compCnt = (state.downloadsSummary && state.downloadsSummary.completed_count) || 0;
                if (compCnt > (state.lastCompletedCount || 0)) {
                    state.lastCompletedCount = compCnt;
                    fetchLocalCatalog();
                    const newestDone = qList.find(x => x.status === "completed");
                    if (newestDone && activeCnt === 0) {
                        state.statusMsg = `✅ Nedladdning klar (${newestDone.total_mb || newestDone.downloaded_mb || 0} MB): ${newestDone.filename}`;
                    }
                }
                const newestErr = qList.find(x => x.status === "failed" || x.status === "error");
                if (newestErr && activeCnt === 0 && newestErr.error) {
                    state.statusMsg = `❌ Nedladdningsfel (${newestErr.filename}): ${newestErr.error}`;
                }
                if (activeCnt > 0) {
                    const topAct = state.downloadsQueue.find(x => x.status === "downloading");
                    if (topAct) {
                        state.statusMsg = `⬇️ Laddar ner ${topAct.filename}: ${Number(topAct.percent || 0).toFixed(1)}% (${topAct.downloaded_mb}/${topAct.total_mb} MB @ ${topAct.speed_mbps} MB/s, ETA ${Math.round(topAct.eta_sec || 0)}s)`;
                    }
                    ensureDownloadPolling(true);
                } else if (state.dlPollTimer) {
                    clearInterval(state.dlPollTimer);
                    state.dlPollTimer = null;
                }
                syncAllViews();
            }
        } catch (e) {}
    };

    const ensureDownloadPolling = (start = true) => {
        if (!start) {
            if (state.dlPollTimer) {
                clearInterval(state.dlPollTimer);
                state.dlPollTimer = null;
            }
            return;
        }
        if (!state.dlPollTimer) {
            state.dlPollTimer = setInterval(() => {
                pollDownloadsStatus();
            }, 900);
        }
    };

    const getActiveGraphHardwareTier = () => {
        try {
            const gNodes = (app.graph && app.graph._nodes) || [];
            for (const gn of gNodes) {
                const ct = String(gn.comfyClass || gn.type || "");
                if (ct.includes("EZCinematrixCanvasIngest") || ct.includes("01_Cinematrix")) {
                    const w = Array.isArray(gn.widgets) ? gn.widgets.find(x => x.name === "hardware_tier") : null;
                    if (w && w.value) return String(w.value);
                }
            }
        } catch (e) {}
        return "auto_from_devops_tier";
    };

    const getActiveGraphContentRating = () => {
        try {
            const gNodes = (app.graph && app.graph._nodes) || [];
            for (const gn of gNodes) {
                const ct = String(gn.comfyClass || gn.type || "");
                if (ct.includes("EZCinematrix") || ct.includes("01_Cinematrix") || ct.includes("02_Cinematrix")) {
                    const w = Array.isArray(gn.widgets) ? gn.widgets.find(x => x.name === "content_rating" || x.name === "rating_tier") : null;
                    if (w && w.value) return String(w.value);
                }
            }
        } catch (e) {}
        return "Uncensored";
    };

    const fetchStatusAndRecipes = async () => {
        try {
            const tierSel = encodeURIComponent(getActiveGraphHardwareTier());
            const cRating = encodeURIComponent(getActiveGraphContentRating());
            const r = await api.fetchApi(`/ez_cinematrix/civitai/status?tier_selection=${tierSel}&content_rating=${cRating}`);
            const d = await r.json();
            if (d) {
                state.licensed = Boolean(d.licensed || (d.license && d.license.licensed));
                state.hasKey = Boolean(d.has_key || d.has_api_key);
                state.maskedKey = d.masked_api_key || "";
                state.hasHfToken = Boolean(d.has_hf_token);
                state.maskedHfToken = d.masked_hf_token || "";
                state.cacheFiles = (d.cache && d.cache.remaining_files) || d.cache_files || 0;
                if (Array.isArray(d.recipes)) state.recipes = d.recipes;
                if (d.system_tier) state.systemTier = d.system_tier;
                if (d.image_companions) state.imageCompanions = d.image_companions;
                if (d.video_companions) state.videoCompanions = d.video_companions;
            }
        } catch (e) {}
        pollDownloadsStatus();
        syncAllViews();
    };

    const fetchArchitectureCompanions = async (arch, modality, action = "resolve") => {
        const isV = String(modality || "").toUpperCase() === "VIDEO";
        const selModel = String(getWidgetVal(isV ? "video_unet_fl2va" : "image_unet_name", "None"));
        const selLoras = isV
            ? [getWidgetVal("video_lora_1", "None"), getWidgetVal("video_lora_2", "None"), getWidgetVal("video_lora_3", "None"), getWidgetVal("video_lora_4", "None"), getWidgetVal("video_turbo_lora", "None")]
            : [getWidgetVal("image_style_lora_1", "None"), getWidgetVal("image_style_lora_2", "None"), getWidgetVal("image_style_lora_3", "None"), getWidgetVal("image_style_lora_4", "None"), getWidgetVal("image_turbo_lora", "None")];
        const tierSelection = getActiveGraphHardwareTier();
        const contentRating = getActiveGraphContentRating();
        if (action === "download") {
            state.statusMsg = `⬇️ Laddar ner saknad VAE & CLIP för ${arch} från HuggingFace...`;
            syncAllViews();
        }
        try {
            const r = await api.fetchApi("/ez_cinematrix/civitai/companions", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ architecture: arch, modality, selected_model: selModel, selected_loras: selLoras, tier_selection: tierSelection, content_rating: contentRating, action })
            });
            const d = await r.json();
            if (d && d.status === "ok") {
                if (d.system_tier) state.systemTier = d.system_tier;
                if (isV) state.videoCompanions = d;
                else state.imageCompanions = d;
                if (action === "download") {
                    const dlCount = Array.isArray(d.downloaded) ? d.downloaded.length : 0;
                    state.statusMsg = dlCount > 0
                        ? `✓ Laddade ner ${dlCount} matchande VAE/CLIP-resursfiler för ${arch}!`
                        : `✓ Alla VAE/CLIP-resursfiler för ${arch} finns redan lokalt på disken.`;
                }
            }
        } catch (e) {}
        syncAllViews();
    };

    const fetchLocalCatalog = async () => {
        try {
            hydrateSlotsFromGraphNodes();
            const tierSel = encodeURIComponent(getActiveGraphHardwareTier());
            const cRating = encodeURIComponent(getActiveGraphContentRating());
            const r = await api.fetchApi(`/ez_cinematrix/civitai/local_catalog?tier_selection=${tierSel}&content_rating=${cRating}`);
            const d = await r.json();
            if (d && d.status === "ok") {
                state.localLoras = Array.isArray(d.loras) ? d.loras : [];
                state.localModels = Array.isArray(d.models) ? d.models : [];
                state.localResources = Array.isArray(d.resources) ? d.resources : [];
                if (d.system_tier) state.systemTier = d.system_tier;
                state.duplicateSummary = d.duplicate_summary || { total_groups: 0, total_duplicate_files: 0, reclaimable_mb: 0 };
            }
        } catch (e) {}
        syncAllViews();
    };

    const deleteLocalAsset = async (category, relName) => {
        if (!category || !relName) return;
        state.statusMsg = `🗑️ Raderar ${shortLabel(relName)} från models/${category}...`;
        state.pendingDeleteKey = "";
        syncAllViews();
        try {
            const r = await api.fetchApi("/ez_cinematrix/civitai/delete_local", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ category, name: relName })
            });
            const d = await r.json();
            if (d && d.status === "ok") {
                if (d.catalog) {
                    state.localLoras = Array.isArray(d.catalog.loras) ? d.catalog.loras : [];
                    state.localModels = Array.isArray(d.catalog.models) ? d.catalog.models : [];
                    state.localResources = Array.isArray(d.catalog.resources) ? d.catalog.resources : [];
                    state.duplicateSummary = d.catalog.duplicate_summary || { total_groups: 0, total_duplicate_files: 0, reclaimable_mb: 0 };
                } else {
                    await fetchLocalCatalog();
                }
                const allSlotKeys = [
                    "image_unet_name", "image_style_lora_1", "image_style_lora_2", "image_style_lora_3", "image_style_lora_4", "image_turbo_lora",
                    "video_unet_fl2va", "video_lora_1", "video_lora_2", "video_lora_3", "video_lora_4", "video_turbo_lora"
                ];
                for (const sk of allSlotKeys) {
                    if (String(getWidgetVal(sk, "None")) === relName) {
                        setWidgetVal(sk, "None");
                    }
                }
                state.statusMsg = `✅ Raderade ${shortLabel(relName)} (Frigjorde ${d.freed_mb || 0} MB på disken)!`;
            } else {
                state.statusMsg = `⚠️ ${(d && d.message) || "Kunde inte radera filen."}`;
            }
        } catch (e) {
            state.statusMsg = `⚠️ Raderingsfel: ${String(e)}`;
        }
        syncAllViews();
    };

    const runCivitaiSearch = async (forceRefresh = false) => {
        state.statusMsg = forceRefresh ? "⏳ Clearing 30d cache & fetching from Civitai..." : "⏳ Searching Civitai catalog...";
        syncAllViews();
        try {
            const r = await api.fetchApi("/ez_cinematrix/civitai/search", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    modality: state.civModality,
                    asset_type: state.civType,
                    base_arch: state.civArch,
                    sort_by: state.civSort,
                    period: state.civPeriod,
                    domain_mode: state.civDomain,
                    query: state.civQuery,
                    limit: 16,
                    force_refresh: Boolean(forceRefresh)
                })
            });
            const d = await r.json();
            state.civItems = (d && Array.isArray(d.items)) ? d.items : [];
            state.statusMsg = d && d.domain_notice
                ? d.domain_notice
                : `✓ Found ${state.civItems.length} ${state.civModality} assets (${state.civArch})`;
            fetchStatusAndRecipes();
        } catch (e) {
            state.statusMsg = `Civitai search error: ${String(e)}`;
            syncAllViews();
        }
    };

    const resolveSelectedVersionAndFile = (item, explicitVerIdx = null, explicitFileIdx = null) => {
        if (!item) return null;
        const versions = Array.isArray(item.versions) && item.versions.length > 0 ? item.versions : [{
            version_id: item.version_id || "",
            version_name: item.version_name || "v1.0",
            base_model: item.base_model || "All",
            created_at: item.updated_at || "",
            download_url: item.download_url || "",
            filename: item.filename || `${item.name || "model"}.safetensors`,
            size_kb: item.size_kb || 0,
            size_mb: item.size_mb || 0,
            size_label: item.size_label || "Auto",
            fp: item.fp || "Auto",
            format: item.format || "SafeTensor",
            trigger_words: item.trigger_words || [],
            description_text: item.description_text || "",
            files: Array.isArray(item.files) && item.files.length > 0 ? item.files : [{
                file_id: item.file_id || "",
                version_id: item.version_id || "",
                name: item.filename || `${item.name || "model"}.safetensors`,
                size_kb: item.size_kb || 0,
                size_mb: item.size_mb || 0,
                size_label: item.size_label || "Auto",
                fp: item.fp || "Auto",
                quantization: item.fp || "Auto",
                size_variant: "standard",
                format: item.format || "SafeTensor",
                download_url: item.download_url || "",
                display_label: item.filename || `${item.name || "model"}.safetensors`
            }],
            samples: item.samples || [],
            optimal_settings: item.optimal_settings || {}
        }];
        const vIdx = explicitVerIdx !== null ? Math.max(0, Math.min(versions.length - 1, Number(explicitVerIdx) || 0)) : Math.max(0, Math.min(versions.length - 1, Number(item._selectedVerIdx) || 0));
        const ver = versions[vIdx] || versions[0];
        const files = Array.isArray(ver.files) && ver.files.length > 0 ? ver.files : [{
            file_id: "",
            version_id: ver.version_id || "",
            name: ver.filename || item.filename || `${item.name || "model"}.safetensors`,
            size_kb: ver.size_kb || 0,
            size_mb: ver.size_mb || 0,
            size_label: ver.size_label || "Auto",
            fp: ver.fp || "Auto",
            quantization: ver.fp || "Auto",
            size_variant: "standard",
            format: ver.format || "SafeTensor",
            download_url: ver.download_url || item.download_url || "",
            display_label: ver.filename || item.filename || `${item.name || "model"}.safetensors`
        }];
        const defaultSafetensorsIdx = Math.max(0, files.findIndex(f => /\.safetensors|\.sft$/i.test(String(f.name || f.filename || ""))));
        const fallbackIdx = ver._selectedFileIdx !== undefined ? Number(ver._selectedFileIdx) : defaultSafetensorsIdx;
        const fIdx = explicitFileIdx !== null ? Math.max(0, Math.min(files.length - 1, Number(explicitFileIdx) || 0)) : Math.max(0, Math.min(files.length - 1, fallbackIdx || 0));
        const file = files[fIdx] || files[0];
        return {
            ver,
            file,
            versions,
            files,
            verIdx: vIdx,
            fileIdx: fIdx,
            version_id: String(ver.version_id || item.version_id || ""),
            version_name: String(ver.version_name || item.version_name || "v1.0"),
            base_model: String(ver.base_model || item.base_model || ""),
            file_id: String(file.file_id || ""),
            filename: String(file.name || ver.filename || item.filename || `${item.name}.safetensors`),
            download_url: String(file.download_url || ver.download_url || item.download_url || ""),
            size_kb: Number(file.size_kb || ver.size_kb || item.size_kb || 0),
            size_mb: Number(file.size_mb || ver.size_mb || item.size_mb || 0),
            size_label: String(file.size_label || ver.size_label || item.size_label || "Auto"),
            fp: String(file.fp || ver.fp || "Auto"),
            size_variant: String(file.size_variant || "standard"),
            format: String(file.format || ver.format || "SafeTensor"),
            trigger_words: Array.isArray(ver.trigger_words) && ver.trigger_words.length ? ver.trigger_words : (item.trigger_words || []),
            samples: Array.isArray(ver.samples) && ver.samples.length ? ver.samples : (item.samples || []),
            optimal_settings: ver.optimal_settings || item.optimal_settings || null
        };
    };

    const inspectCivitaiModelDetails = async (item) => {
        if (!item) return;
        state.civInspectedItem = item;
        syncAllViews();
        if (!item.id) return;
        try {
            const r = await api.fetchApi("/ez_cinematrix/civitai/model_details", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    model_id: item.id,
                    domain: item.source_domain || state.civDomain || "civitai.com",
                    modality: item.modality || state.civModality || "IMAGE"
                })
            });
            const d = await r.json();
            if (d && d.status === "ok" && d.item) {
                const curVerIdx = item._selectedVerIdx || 0;
                d.item._selectedVerIdx = curVerIdx;
                const idxInList = state.civItems.findIndex(x => String(x.id) === String(item.id));
                if (idxInList >= 0) state.civItems[idxInList] = d.item;
                state.civInspectedItem = d.item;
                syncAllViews();
            }
        } catch (e) {}
    };

    // Dedicated Download-Only Function (Supports specific version/file & async background download with live telemetry)
    const downloadOnlyCivitaiItem = async (item, explicitVerIdx = null, explicitFileIdx = null, waitForCompletion = false) => {
        const sel = resolveSelectedVersionAndFile(item, explicitVerIdx, explicitFileIdx);
        if (!sel || (!sel.download_url && !item.id && !sel.version_id)) {
            state.statusMsg = "⚠️ Ingen nedladdnings-URL eller Model ID tillgänglig för denna fil.";
            syncAllViews();
            return null;
        }
        state.statusMsg = `⬇️ Startar nedladdning av ${sel.filename} (${sel.fp} · ${sel.size_label}) till ComfyUI...`;
        ensureDownloadPolling(true);
        syncAllViews();
        const sample = (Array.isArray(sel.samples) && sel.samples[0]) || null;
        try {
            const r = await api.fetchApi("/ez_cinematrix/civitai/download", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    download_url: sel.download_url || "",
                    model_id: item.id || "",
                    version_id: sel.version_id || "",
                    file_id: sel.file_id || "",
                    size_kb: sel.size_kb || 0,
                    source_domain: item.source_domain || "civitai.com",
                    filename: sel.filename,
                    asset_type: item.type || state.civType,
                    modality: item.modality || state.civModality,
                    sample_url: sample ? (sample.remote_url || sample.url || "") : "",
                    async_bg: !waitForCompletion
                })
            });
            const d = await r.json();
            await pollDownloadsStatus();
            if (d && (d.status === "started" || d.status === "downloading")) {
                ensureDownloadPolling(true);
                state.statusMsg = `⬇️ Laddar ner ${d.filename || sel.filename} i bakgrunden — följ realtids-status under fliken ⬇️ Downloads!`;
                syncAllViews();
                return d;
            }
            if (d && d.status === "ok" && d.filename) {
                await fetchLocalCatalog();
                state.statusMsg = `✓ Nedladdad till disk (${d.size_mb} MB): ${d.filename}`;
                syncAllViews();
                return d;
            } else {
                state.statusMsg = `⚠️ ${(d && d.message) || "Kunde inte ladda ner filen (kontrollera Civitai API-nyckel i 🔑 API)."}`;
            }
        } catch (e) {
            state.statusMsg = `⚠️ Nedladdningsfel: ${String(e)}`;
        }
        syncAllViews();
        return null;
    };

    // Dedicated Send-to-Slot Function (Assigns selected version/file to slot, or downloads first if not on disk)
    const sendCivitaiItemToSlot = async (item, targetSlot = "", explicitVerIdx = null, explicitFileIdx = null) => {
        if (!item) return;
        const sel = resolveSelectedVersionAndFile(item, explicitVerIdx, explicitFileIdx);
        if (!sel) return;
        const rawFname = String(sel.filename || `${item.name}.safetensors`);
        const targetLower = rawFname.toLowerCase();
        const allLoc = state.localLoras.concat(state.localModels);
        const matchedLoc = allLoc.find(loc => {
            const base = String(loc.name || "").split(/[\\/]/).pop().toLowerCase();
            return base === targetLower || base === `img_${targetLower}` || base === `vid_${targetLower}`;
        });
        state.stackModality = item.modality === "VIDEO" ? "VIDEO" : "IMAGE";
        const sample = (Array.isArray(sel.samples) && sel.samples[0]) || null;
        const cThumb = sample ? (sample.cached_thumb || sample.cached_file || "") : "";
        if (matchedLoc) {
            if (targetSlot) {
                assignAssetToSlot(targetSlot, matchedLoc.name, item.modality, sel.trigger_words || [], cThumb, sel.optimal_settings || null);
            } else {
                autoAssignNextSlot(matchedLoc.name, item.type, item.modality, false, sel.trigger_words || [], cThumb, sel.optimal_settings || null);
            }
            return;
        }
        const dlRes = await downloadOnlyCivitaiItem(item, sel.verIdx, sel.fileIdx, true);
        if (dlRes && dlRes.filename) {
            if (targetSlot) {
                assignAssetToSlot(targetSlot, dlRes.filename, item.modality, sel.trigger_words || [], cThumb, sel.optimal_settings || null);
            } else {
                autoAssignNextSlot(dlRes.filename, dlRes.asset_type || item.type, item.modality, false, sel.trigger_words || [], cThumb, sel.optimal_settings || null);
            }
        }
    };

    const saveCurrentRecipe = async (customName) => {
        const name = String(customName || "").trim() || `Rig_${new Date().toISOString().slice(11, 19).replace(/:/g, "")}`;
        const recipe = {
            name,
            modality: state.stackModality,
            image_architecture: getWidgetVal("image_architecture", "KREA2"),
            image_unet_name: getWidgetVal("image_unet_name", "None"),
            enable_image_lora_1: Boolean(getWidgetVal("enable_image_lora_1", true)),
            image_style_lora_1: getWidgetVal("image_style_lora_1", "None"),
            image_style_strength_1: parseFloat(getWidgetVal("image_style_strength_1", 0.8)),
            enable_image_lora_2: Boolean(getWidgetVal("enable_image_lora_2", true)),
            image_style_lora_2: getWidgetVal("image_style_lora_2", "None"),
            image_style_strength_2: parseFloat(getWidgetVal("image_style_strength_2", 0.65)),
            enable_image_lora_3: Boolean(getWidgetVal("enable_image_lora_3", true)),
            image_style_lora_3: getWidgetVal("image_style_lora_3", "None"),
            image_style_strength_3: parseFloat(getWidgetVal("image_style_strength_3", 0.45)),
            enable_image_lora_4: Boolean(getWidgetVal("enable_image_lora_4", true)),
            image_style_lora_4: getWidgetVal("image_style_lora_4", "None"),
            image_style_strength_4: parseFloat(getWidgetVal("image_style_strength_4", 0.35)),
            enable_image_turbo_lora: Boolean(getWidgetVal("enable_image_turbo_lora", true)),
            image_turbo_lora: getWidgetVal("image_turbo_lora", "None"),
            image_turbo_strength: parseFloat(getWidgetVal("image_turbo_strength", 0.9)),
            video_architecture: getWidgetVal("video_architecture", "MiniMax H3"),
            video_unet_fl2va: getWidgetVal("video_unet_fl2va", "None"),
            enable_video_lora_1: Boolean(getWidgetVal("enable_video_lora_1", true)),
            video_lora_1: getWidgetVal("video_lora_1", "None"),
            video_lora_1_strength: parseFloat(getWidgetVal("video_lora_1_strength", 0.6)),
            enable_video_lora_2: Boolean(getWidgetVal("enable_video_lora_2", true)),
            video_lora_2: getWidgetVal("video_lora_2", "None"),
            video_lora_2_strength: parseFloat(getWidgetVal("video_lora_2_strength", 0.5)),
            enable_video_lora_3: Boolean(getWidgetVal("enable_video_lora_3", true)),
            video_lora_3: getWidgetVal("video_lora_3", "None"),
            video_lora_3_strength: parseFloat(getWidgetVal("video_lora_3_strength", 0.4)),
            enable_video_lora_4: Boolean(getWidgetVal("enable_video_lora_4", true)),
            video_lora_4: getWidgetVal("video_lora_4", "None"),
            video_lora_4_strength: parseFloat(getWidgetVal("video_lora_4_strength", 0.35)),
            enable_video_turbo_lora: Boolean(getWidgetVal("enable_video_turbo_lora", true)),
            video_turbo_lora: getWidgetVal("video_turbo_lora", "None"),
            video_turbo_strength: parseFloat(getWidgetVal("video_turbo_strength", 1.0)),
            trigger_words: getWidgetVal("trigger_words", ""),
            thumbnail_file: state.lastThumbFile
        };
        try {
            const r = await api.fetchApi("/ez_cinematrix/civitai/recipes", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: "save", recipe })
            });
            const d = await r.json();
            if (d && Array.isArray(d.recipes)) state.recipes = d.recipes;
            setWidgetVal("active_recipe_name", name);
            state.statusMsg = `💾 Recipe sparat: ${name}`;
        } catch (e) {}
        syncAllViews();
    };

    const applySavedRecipe = (rec) => {
        if (!rec) return;
        const fields = [
            "image_architecture", "image_unet_name",
            "enable_image_lora_1", "image_style_lora_1", "image_style_strength_1",
            "enable_image_lora_2", "image_style_lora_2", "image_style_strength_2",
            "enable_image_lora_3", "image_style_lora_3", "image_style_strength_3",
            "enable_image_lora_4", "image_style_lora_4", "image_style_strength_4",
            "enable_image_turbo_lora", "image_turbo_lora", "image_turbo_strength",
            "video_architecture", "video_unet_fl2va",
            "enable_video_lora_1", "video_lora_1", "video_lora_1_strength",
            "enable_video_lora_2", "video_lora_2", "video_lora_2_strength",
            "enable_video_lora_3", "video_lora_3", "video_lora_3_strength",
            "enable_video_lora_4", "video_lora_4", "video_lora_4_strength",
            "enable_video_turbo_lora", "video_turbo_lora", "video_turbo_strength",
            "trigger_words"
        ];
        fields.forEach(f => {
            if (rec[f] !== undefined && rec[f] !== null) setWidgetVal(f, rec[f]);
        });
        if (rec.modality === "IMAGE" && rec.model_name && !rec.image_unet_name) {
            setWidgetVal("image_unet_name", rec.model_name);
            setWidgetVal("image_style_lora_1", rec.lora_1 || "None");
            setWidgetVal("image_style_strength_1", rec.lora_1_strength ?? 0.8);
            setWidgetVal("image_style_lora_2", rec.lora_2 || "None");
            setWidgetVal("image_style_strength_2", rec.lora_2_strength ?? 0.65);
            setWidgetVal("image_style_lora_3", rec.lora_3 || "None");
            setWidgetVal("image_style_strength_3", rec.lora_3_strength ?? 0.45);
            setWidgetVal("image_style_lora_4", rec.lora_4 || "None");
            setWidgetVal("image_style_strength_4", rec.lora_4_strength ?? 0.35);
            setWidgetVal("image_turbo_lora", rec.turbo_lora || "None");
            setWidgetVal("image_turbo_strength", rec.turbo_strength ?? 0.9);
        } else if (rec.modality === "VIDEO" && rec.model_name && !rec.video_unet_fl2va) {
            setWidgetVal("video_unet_fl2va", rec.model_name);
            setWidgetVal("video_lora_1", rec.lora_1 || "None");
            setWidgetVal("video_lora_1_strength", rec.lora_1_strength ?? 0.6);
            setWidgetVal("video_lora_2", rec.lora_2 || "None");
            setWidgetVal("video_lora_2_strength", rec.lora_2_strength ?? 0.5);
            setWidgetVal("video_lora_3", rec.lora_3 || "None");
            setWidgetVal("video_lora_3_strength", rec.lora_3_strength ?? 0.4);
            setWidgetVal("video_lora_4", rec.lora_4 || "None");
            setWidgetVal("video_lora_4_strength", rec.lora_4_strength ?? 0.35);
            setWidgetVal("video_turbo_lora", rec.turbo_lora || "None");
            setWidgetVal("video_turbo_strength", rec.turbo_strength ?? 1.0);
        }
        if (rec.name) setWidgetVal("active_recipe_name", rec.name);
        state.statusMsg = `⚡ Laddade Recipe: ${rec.name}`;
        syncAllViews();
    };

    const renderPillBtn = (label, active, colorHex = "#eab308", extraStyle = "") => {
        const bg = active ? colorHex : "#13161f";
        const fg = active ? "#090a0f" : "#cbd5e1";
        const border = active ? colorHex : "#334155";
        return `<button style="background:${bg};color:${fg};border:1px solid ${border};border-radius:4px;padding:3px 7px;font-size:9.5px;font-weight:bold;cursor:pointer;transition:all 0.12s;${extraStyle}">${label}</button>`;
    };

    const buildStackPanelHtml = (isCompact = true) => {
        hydrateSlotsFromGraphNodes();
        const isVid = state.stackModality === "VIDEO";
        const accent = isVid ? "#34d399" : "#fbbf24";
        const archKey = isVid ? "video_architecture" : "image_architecture";
        const curArch = String(getWidgetVal(archKey, isVid ? "MiniMax H3" : "KREA2"));
        const archOptions = isVid
            ? ["MiniMax H3", "Wan 2.1", "LTXV", "Hunyuan Video"]
            : ["KREA2", "Flux.1 D", "Flux.1 S", "Illustrious", "Pony", "SDXL 1.0", "Qwen-Image"];
        const baseKey = isVid ? "video_unet_fl2va" : "image_unet_name";
        const baseVal = String(getWidgetVal(baseKey, "None"));
        const modelOpts = getAvailableSlotOptions(baseKey, false, isVid);
        const modelSelectOptionsHtml = `<option value="None" ${baseVal === "None" ? "selected" : ""}>— Ingen modell vald (Välj här eller via 🗂️ Lokal / 🌐 Civitai) —</option>` +
            modelOpts.map(m => `<option value="${String(m.name).replace(/"/g, "&quot;")}" ${m.name === baseVal ? "selected" : ""}>${m.badge}${shortLabel(m.name)}${m.size_mb ? ` (${m.size_mb} MB)` : ""}</option>`).join("");
        const rows = isVid
            ? [
                { label: "🎬 Video LoRA 1", key: "video_lora_1", sKey: "video_lora_1_strength", eKey: "enable_video_lora_1", min: -4, max: 4 },
                { label: "🎬 Video LoRA 2", key: "video_lora_2", sKey: "video_lora_2_strength", eKey: "enable_video_lora_2", min: -4, max: 4 },
                { label: "🎬 Video LoRA 3", key: "video_lora_3", sKey: "video_lora_3_strength", eKey: "enable_video_lora_3", min: -4, max: 4 },
                { label: "🎬 Video LoRA 4", key: "video_lora_4", sKey: "video_lora_4_strength", eKey: "enable_video_lora_4", min: -4, max: 4 },
                { label: "⚡ Video Turbo", key: "video_turbo_lora", sKey: "video_turbo_strength", eKey: "enable_video_turbo_lora", min: 0, max: 2.5 }
            ]
            : [
                { label: "🖼️ Style LoRA 1", key: "image_style_lora_1", sKey: "image_style_strength_1", eKey: "enable_image_lora_1", min: -4, max: 4 },
                { label: "🖼️ Style LoRA 2", key: "image_style_lora_2", sKey: "image_style_strength_2", eKey: "enable_image_lora_2", min: -4, max: 4 },
                { label: "🖼️ Style LoRA 3", key: "image_style_lora_3", sKey: "image_style_strength_3", eKey: "enable_image_lora_3", min: -4, max: 4 },
                { label: "🖼️ Style LoRA 4", key: "image_style_lora_4", sKey: "image_style_strength_4", eKey: "enable_image_lora_4", min: -4, max: 4 },
                { label: "⚡ Image Turbo", key: "image_turbo_lora", sKey: "image_turbo_strength", eKey: "enable_image_turbo_lora", min: 0, max: 2.5 }
            ];
        const archPills = archOptions.map(a =>
            `<button data-arch="${a}" style="background:${curArch === a ? accent : "#151821"};color:${curArch === a ? "#000" : "#94a3b8"};border:1px solid ${curArch === a ? accent : "#262b38"};border-radius:3px;padding:2px 6px;font-size:9px;font-weight:bold;cursor:pointer;">${a}</button>`
        ).join("");
        const loraOptsAll = getAvailableSlotOptions(rows[0].key, true, isVid);
        const slotsHtml = rows.map(r => {
            const val = String(getWidgetVal(r.key, "None"));
            const strVal = Number(getWidgetVal(r.sKey, 0.75)).toFixed(2);
            const isEnabled = Boolean(getWidgetVal(r.eKey, true));
            const hasSelection = val !== "None" && val !== "";
            const active = hasSelection && isEnabled;
            const locMatch = state.localLoras.find(l => l.name === val || shortLabel(l.name) === shortLabel(val));
            const optHint = locMatch && locMatch.optimal_settings
                ? locMatch.optimal_settings.summary_badge
                : (isVid
                    ? (r.key.includes("turbo") ? "⚡ Optimal: 1.00 (VIS 1.0 / Aud 1.0 / CLIP 0.0)" : "⚡ Optimal: 0.16–0.25 (VIS 1.0 / Aud 0.0 / CLIP 0.0)")
                    : (r.key.includes("turbo") ? "⚡ Optimal: 0.90 (Stage 2+3 @ CFG 1.0)" : "⚡ Optimal: 0.65–0.80 (VIS 1.0 / CLIP 1.0)"));
            const loraSelHtml = `<option value="None" ${!hasSelection ? "selected" : ""}>— Ingen LoRA vald (Klicka för att välja lokal LoRA) —</option>` +
                loraOptsAll.map(l => `<option value="${String(l.name).replace(/"/g, "&quot;")}" ${l.name === val ? "selected" : ""}>${l.badge}${shortLabel(l.name)}${l.size_mb ? ` (${l.size_mb} MB)` : ""}</option>`).join("");
            const borderCol = !isEnabled ? "#ef4444" : (active ? accent : "#1e293b");
            return `
              <div style="background:${!isEnabled ? "#140c10" : "#11131a"};border:1px solid ${borderCol};border-radius:5px;padding:5px 7px;display:flex;flex-direction:column;gap:4px;opacity:${!isEnabled ? "0.78" : "1"};">
                <div style="display:flex;justify-content:space-between;align-items:center;gap:4px;">
                  <div style="display:flex;align-items:center;gap:5px;">
                    <button data-toggle-enable="${r.eKey}" data-toggle-slot="${r.key}" title="Klicka för 1-klicks ON / BYPASS utan att ta bort LoRA från menyn" style="background:${isEnabled ? "#065f46" : "#7f1d1d"};color:${isEnabled ? "#34d399" : "#fca5a5"};border:1px solid ${isEnabled ? "#10b981" : "#ef4444"};border-radius:3px;padding:1px 6px;font-size:8.5px;font-weight:bold;cursor:pointer;">${isEnabled ? "🟢 ON" : "🔇 BYPASS"}</button>
                    <span style="font-size:9.5px;color:${!isEnabled ? "#f87171" : (active ? accent : "#94a3b8")};font-weight:bold;">${r.label}${!isEnabled && hasSelection ? " (BYPASSED)" : ""}</span>
                  </div>
                  <div style="display:flex;gap:3px;">
                    <button data-pick-local="${r.key}" data-pick-mod="${isVid ? "VIDEO" : "IMAGE"}" style="background:#1e293b;color:#e2e8f0;border:1px solid #334155;border-radius:3px;padding:1px 5px;font-size:8.5px;cursor:pointer;">🗂️ Lokal</button>
                    <button data-pick-civ="${r.key}" data-pick-mod="${isVid ? "VIDEO" : "IMAGE"}" style="background:#1e293b;color:#facc15;border:1px solid #334155;border-radius:3px;padding:1px 5px;font-size:8.5px;cursor:pointer;">🌐 Civitai</button>
                    ${hasSelection ? `<button data-clear-slot="${r.key}" style="background:#7f1d1d;color:#fecaca;border:none;border-radius:3px;padding:1px 5px;font-size:8.5px;cursor:pointer;font-weight:bold;" title="Rensa slot">✕</button>` : ""}
                  </div>
                </div>
                <select data-slot-select="${r.key}" data-slot-mod="${isVid ? "VIDEO" : "IMAGE"}" style="width:100%;background:#090a0f;color:${hasSelection ? (isEnabled ? "#f8fafc" : "#fca5a5") : "#94a3b8"};border:1px solid ${active ? accent : "#334155"};border-radius:3px;padding:2px 4px;font-size:9px;font-weight:bold;cursor:pointer;">
                  ${loraSelHtml}
                </select>
                <div style="font-size:8px;color:#38bdf8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="${optHint}">${optHint}</div>
                <div style="display:flex;align-items:center;gap:6px;">
                  <span style="font-size:8.5px;color:#94a3b8;min-width:42px;">Styrka:</span>
                  <input type="range" data-slider-key="${r.sKey}" min="${r.min}" max="${r.max}" step="0.05" value="${strVal}" style="flex:1;accent-color:${isEnabled ? accent : "#ef4444"};height:4px;cursor:pointer;" />
                  <span class="ez-sl-val" style="font-size:9.5px;color:${isEnabled ? accent : "#f87171"};font-weight:bold;min-width:30px;text-align:right;">${strVal}</span>
                </div>
              </div>
            `;
        }).join("");

        return `
          <div style="display:flex;flex-direction:column;gap:6px;flex:1;min-height:0;overflow-y:auto;padding-right:2px;">
            <div style="display:flex;gap:4px;flex-shrink:0;">
              <button data-stack-mod="IMAGE" style="flex:1;background:${!isVid ? "#fbbf24" : "#13161f"};color:${!isVid ? "#000" : "#94a3b8"};border:1px solid ${!isVid ? "#fbbf24" : "#334155"};border-radius:4px;padding:5px;font-size:10px;font-weight:bold;cursor:pointer;">🖼️ [03] IMAGE RIG (KREA2 / Flux)</button>
              <button data-stack-mod="VIDEO" style="flex:1;background:${isVid ? "#34d399" : "#13161f"};color:${isVid ? "#000" : "#94a3b8"};border:1px solid ${isVid ? "#34d399" : "#334155"};border-radius:4px;padding:5px;font-size:10px;font-weight:bold;cursor:pointer;">🎬 [05] VIDEO RIG (MiniMax H3 / Wan)</button>
            </div>
            <div style="display:flex;gap:3px;flex-wrap:wrap;align-items:center;flex-shrink:0;">
              <span style="font-size:8.5px;color:#94a3b8;margin-right:2px;">Arkitektur:</span>
              ${archPills}
            </div>
            <div style="background:#11131a;border:1px solid ${baseVal !== "None" ? accent : "#334155"};border-radius:5px;padding:6px 7px;display:flex;flex-direction:column;gap:4px;flex-shrink:0;">
              <div style="display:flex;justify-content:space-between;align-items:center;gap:4px;">
                <span style="font-size:9.5px;color:${accent};font-weight:bold;">🏛️ ${isVid ? "Video UNet / Diffusion (fl2va)" : "Image UNet / Checkpoint"} (${modelOpts.length} på disk)</span>
                <div style="display:flex;gap:3px;">
                  <button data-pick-local-model="${baseKey}" data-pick-mod="${isVid ? "VIDEO" : "IMAGE"}" style="background:#1e293b;color:#e2e8f0;border:1px solid #334155;border-radius:3px;padding:1px 6px;font-size:8.5px;cursor:pointer;">🗂️ Lokal Bank</button>
                  <button data-pick-civ-model="${baseKey}" data-pick-mod="${isVid ? "VIDEO" : "IMAGE"}" style="background:#1e293b;color:#facc15;border:1px solid #334155;border-radius:3px;padding:1px 6px;font-size:8.5px;cursor:pointer;">🌐 Civitai</button>
                  ${baseVal !== "None" ? `<button data-clear-slot="${baseKey}" style="background:#7f1d1d;color:#fecaca;border:none;border-radius:3px;padding:1px 5px;font-size:8.5px;cursor:pointer;">✕</button>` : ""}
                </div>
              </div>
              <select data-slot-select="${baseKey}" data-slot-mod="${isVid ? "VIDEO" : "IMAGE"}" style="width:100%;background:#090a0f;color:${baseVal !== "None" ? "#f8fafc" : "#94a3b8"};border:1px solid ${baseVal !== "None" ? accent : "#334155"};border-radius:3px;padding:3px 5px;font-size:9.5px;font-weight:bold;cursor:pointer;">
                ${modelSelectOptionsHtml}
              </select>
            </div>
            ${(() => {
                const imgComp = state.imageCompanions || {};
                const vidComp = state.videoCompanions || {};
                const comp = isVid ? vidComp : imgComp;
                const sysTier = (comp && comp.system_tier) || (imgComp && imgComp.system_tier) || (vidComp && vidComp.system_tier) || state.systemTier || {
                    gpu_name: "Detekterar GPU...",
                    actual_vram_gb: 16.0,
                    system_ram_gb: 32.0,
                    tier_short: "Tier 1 (Auto)",
                    optimal_precision_label: "FP8 Scaled + GGUF Q8_0"
                };
                const vlmComp = (comp && comp.vlm_companions) || (imgComp && imgComp.vlm_companions) || (vidComp && vidComp.vlm_companions) || {};
                const hasVlm = Boolean(vlmComp.has_vlm);
                const hasMmproj = Boolean(vlmComp.has_mmproj);
                const vlmList = Array.isArray(vlmComp.installed_vlms) ? vlmComp.installed_vlms : [];
                const activeVlmRaw = vlmComp.active_vlm_name && vlmComp.active_vlm_name !== "None" ? vlmComp.active_vlm_name : "";
                const vlmOptsHtml = vlmList.length
                    ? vlmList.map(v => `<option value="${String(v.name).replace(/"/g, "&quot;")}" ${v.name === activeVlmRaw ? "selected" : ""}>${v.is_qwen_vl ? "🏆 " : "⚠️ "}${shortLabel(v.name)} (${v.type} · ${v.size_gb} GB)</option>`).join("")
                    : `<option value="">— Ingen Qwen-VL på disk —</option>`;

                const imgClipOk = Boolean(imgComp.has_clip && imgComp.clip_name && imgComp.clip_name !== "None");
                const imgVaeOk = Boolean(imgComp.has_vae && imgComp.vae_name && imgComp.vae_name !== "None");
                const imgUnetOk = Boolean(imgComp.has_unet && imgComp.unet_name && imgComp.unet_name !== "None");
                const imgClipList = Array.isArray(imgComp.installed_clips) ? imgComp.installed_clips : [];
                const imgVaeList = Array.isArray(imgComp.installed_vaes) ? imgComp.installed_vaes : [];
                const imgBp = (imgComp && imgComp.optimal_blueprint) || {
                    unet: "krea2_fp8_e4m3fn_scaled.safetensors (FP8 / ConvRot)",
                    clip: "qwen3vl_4b_fp8_scaled.safetensors",
                    vae: "ae.safetensors / qwen_image_vae.safetensors"
                };

                const vidClipOk = Boolean(vidComp.has_clip && vidComp.clip_name && vidComp.clip_name !== "None");
                const vidVaeOk = Boolean(vidComp.has_vae && vidComp.vae_name && vidComp.vae_name !== "None");
                const vidAudOk = Boolean(vidComp.has_audio_vae);
                const vidUnetOk = Boolean(vidComp.has_unet && vidComp.unet_name && vidComp.unet_name !== "None");
                const vidClipList = Array.isArray(vidComp.installed_clips) ? vidComp.installed_clips : [];
                const vidVaeList = Array.isArray(vidComp.installed_vaes) ? vidComp.installed_vaes : [];
                const vidAudList = Array.isArray(vidComp.installed_audio_vaes) ? vidComp.installed_audio_vaes : [];
                const vidBp = (vidComp && vidComp.optimal_blueprint) || {
                    unet: "10Eros_Max_SingularityV2_PRISM2_PikaFlex_0.85_int8HQ.safetensors",
                    clip: "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors (32B 5120-dim NVFP4/AWQ)",
                    vae: "MiniMax-H3-video_vae_fp16.safetensors (5.21 GB 16-bit FP16)",
                    audio_vae: "MiniMax-H3-audio_vae_fp32.safetensors (605 MB FP32)"
                };

                const canDlImg = Boolean(imgComp.can_auto_download);
                const canDlVid = Boolean(vidComp.can_auto_download);
                const subNotices = Array.from(new Set([].concat(imgComp.suboptimal_notices || [], vidComp.suboptimal_notices || [])));
                const allOk = hasVlm && hasMmproj && imgClipOk && imgVaeOk && vidClipOk && vidVaeOk && vidAudOk;
                const healthState = !allOk ? "MISSING" : (subNotices.length > 0 ? "SUBOPTIMAL" : "OPTIMAL");
                const healthBorder = healthState === "OPTIMAL" ? "#10b981" : (healthState === "SUBOPTIMAL" ? "#f59e0b" : "#ef4444");
                const healthBg = healthState === "OPTIMAL" ? "#064e3b" : (healthState === "SUBOPTIMAL" ? "#451a03" : "#450a0a");
                const healthFg = healthState === "OPTIMAL" ? "#34d399" : (healthState === "SUBOPTIMAL" ? "#fbbf24" : "#fca5a5");
                const healthText = (comp && comp.health_label) || (healthState === "OPTIMAL"
                    ? `🟢 Grön (Optimal): Alla obligatoriska resursfiler (VAE, CLIP, Audio VAE, Qwen3-VL + mmproj) finns på disken och matchar ditt faktiska system (${sysTier.gpu_name}, ${sysTier.actual_vram_gb} GB VRAM / ${sysTier.system_ram_gb} GB RAM) och projektets tier (${sysTier.tier_short}).`
                    : (healthState === "SUBOPTIMAL"
                        ? `🟡 Gul (Suboptimal): Resursfiler finns lokalt men kontrollera huvudmodell/precision mot ${sysTier.gpu_name} (${sysTier.actual_vram_gb} GB VRAM) & ${sysTier.tier_short}.`
                        : `🔴 Röd (Saknas på disk): En eller flera obligatoriska resursfiler saknas lokalt och behöver tas hem för ${sysTier.gpu_name} (${sysTier.actual_vram_gb} GB VRAM / ${sysTier.tier_short}).`));
                const dupSum = state.duplicateSummary || { total_groups: 0, total_duplicate_files: 0, reclaimable_mb: 0 };
                const opt = (comp && comp.optimal_settings) || (isVid
                    ? { sampler: "res_multistep", scheduler: "simple", steps: 8, cfg: 1.0, denoise: 1.0, shift_video: 5.0, shift_audio: 3.0, arch_note: "8-Step Turbo: res_multistep + simple, Steps 8, CFG 1.0, Denoise 1.00, Shift V:5.0 / A:3.0. Turbo Audio=1.0, Visuella LoRAs=0.15-0.30 (Audio=0.0, CLIP=0.0)." }
                    : { sampler: "euler", scheduler: "beta / simple", steps: 52, cfg: 3.0, denoise: 0.75, stage1_steps: 52, stage1_cfg: 3.0, stage1_sampler: "euler", stage1_scheduler: "beta", stage2_steps: 14, stage2_cfg: 1.0, stage2_sampler: "euler", stage2_scheduler: "simple", handoff_percent: 58.0, stage3_handoff_percent: 90.0, skin_blur_radius: 1.5, skin_polish_opacity: 0.25, arch_note: "Krea2 3-Stegs Fotorealism: Steg 1 (Raw 0->58% av 52 stp): euler + beta @ CFG 3.0 | Steg 2 (Turbo 58->90% på 14-grid): euler + simple @ CFG 1.0 | Steg 3 (Polish 90->100%)." });
                const imgArchNow = String(getWidgetVal("image_architecture", "KREA2"));
                const vidArchNow = String(getWidgetVal("video_architecture", "MiniMax H3"));
                const totResCount = state.localResources.length || (vlmList.length + imgClipList.length + imgVaeList.length);
                return `
                  <div style="background:#0c111d;border:1px solid #38bdf8;border-radius:6px;padding:6px 8px;display:flex;flex-direction:column;gap:5px;flex-shrink:0;">
                    <div style="display:flex;justify-content:space-between;align-items:center;gap:4px;flex-wrap:wrap;">
                      <span style="font-size:9px;color:#38bdf8;font-weight:bold;">🧭 OPTIMAL RESURS- & KOMPANJONSKONTROLL (VAD ÄR OPTIMALT vs VAD DU HAR PÅ DISK)</span>
                      <div style="display:flex;gap:3px;">
                        <button class="ez-equip-all-optimal" style="background:linear-gradient(90deg,#10b981,#34d399);color:#000;border:none;border-radius:3px;padding:2px 7px;font-size:8px;font-weight:bold;cursor:pointer;" title="Sätter bästa lokala Qwen3-VL, UNet, Turbo-LoRA, CLIP, VAE & Audio-VAE direkt i [02], [03], [05] och [10]">⚡ 1-Klick: Utrusta Alla Optimala Filer</button>
                        <button class="ez-comp-check-all" style="background:#1e293b;color:#38bdf8;border:1px solid #334155;border-radius:3px;padding:2px 6px;font-size:8px;font-weight:bold;cursor:pointer;">🔄 Skanna System & Disk</button>
                      </div>
                    </div>
                    <div style="background:#090d16;border:1px solid #1e293b;border-radius:4px;padding:3px 6px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:4px;font-size:8px;color:#cbd5e1;">
                      <span>🖥️ <b>Faktiskt System:</b> <span style="color:#f8fafc;">${sysTier.gpu_name}</span> (<b style="color:#38bdf8;">${sysTier.actual_vram_gb} GB VRAM</b> / ${sysTier.system_ram_gb} GB RAM)</span>
                      <span>🎯 <b>Projekt-Tier:</b> <span style="color:#facc15;font-weight:bold;">${sysTier.tier_short}</span> · <span style="color:#a7f3d0;">Optimal precision: ${sysTier.optimal_precision_label}</span></span>
                    </div>
                    <div style="background:${healthBg};border:1px solid ${healthBorder};border-radius:4px;padding:3px 6px;font-size:8px;color:${healthFg};font-weight:bold;line-height:1.25;">
                      ${healthText}
                    </div>

                    <!-- [02] QWEN-VL -->
                    <div style="background:#111624;border:1px solid ${hasVlm && hasMmproj ? "#10b981" : "#ef4444"};border-radius:4px;padding:5px 6px;display:flex;flex-direction:column;gap:3px;">
                      <div style="display:flex;justify-content:space-between;align-items:center;gap:4px;">
                        <span style="font-size:8.5px;font-weight:bold;color:${hasVlm && hasMmproj ? "#34d399" : "#f87171"};">🧠 [02] QWEN-VL COMPILER (${vlmList.length} modeller på disk)</span>
                        ${(!hasVlm || !hasMmproj)
                            ? `<button class="ez-vlm-auto-hf" style="background:#eab308;color:#000;border:none;border-radius:3px;padding:1px 6px;font-size:8px;font-weight:bold;cursor:pointer;">⬇️ Ta hem Qwen3-VL Safetensors (HF)</button>`
                            : `<button class="ez-vlm-sync-02" data-vlm-name="${activeVlmRaw}" style="background:#065f46;color:#a7f3d0;border:none;border-radius:3px;padding:1px 6px;font-size:8px;font-weight:bold;cursor:pointer;">⚡ Koppla vald till [02]</button>`}
                      </div>
                      <div style="font-size:7.8px;color:#fde68a;">🎯 <b>Optimalt för ${sysTier.actual_vram_gb} GB VRAM:</b> ${vlmComp.optimal_recommended_vlm || "Huihui-Qwen3-VL-4B / 8B-Instruct-abliterated (Native Safetensors + EZ Q8 Cache)"}</div>
                      <div style="display:flex;align-items:center;gap:4px;">
                        <span style="font-size:7.8px;color:${hasVlm ? "#34d399" : "#f87171"};font-weight:bold;white-space:nowrap;">${hasVlm ? "🟢 PÅ DISK:" : "🔴 BEHÖVER TAS HEM:"}</span>
                        <select class="ez-vlm-select-02" style="flex:1;background:#090a0f;color:#f8fafc;border:1px solid #334155;border-radius:3px;padding:1px 4px;font-size:8px;">${vlmOptsHtml}</select>
                        <span style="font-size:7.8px;color:${hasMmproj ? "#34d399" : "#f87171"};font-weight:bold;white-space:nowrap;">Vision: ${hasMmproj ? `🟢 ${shortLabel(vlmComp.active_mmproj_name)}` : "🔴 mmproj saknas"}</span>
                      </div>
                    </div>

                    <!-- [03/04] BILD-RESURSER -->
                    <div style="background:#111624;border:1px solid ${imgClipOk && imgVaeOk ? "#10b981" : "#ef4444"};border-radius:4px;padding:5px 6px;display:flex;flex-direction:column;gap:3px;">
                      <div style="display:flex;justify-content:space-between;align-items:center;gap:4px;">
                        <span style="font-size:8.5px;font-weight:bold;color:${imgClipOk && imgVaeOk ? "#34d399" : "#fbbf24"};">🖼️ [03/04] BILD-RESURSER (${imgArchNow})</span>
                        <div style="display:flex;gap:3px;">
                          ${canDlImg ? `<button class="ez-comp-dl" data-comp-arch="${imgArchNow}" data-comp-mod="IMAGE" style="background:#0284c7;color:#fff;border:none;border-radius:3px;padding:1px 6px;font-size:8px;font-weight:bold;cursor:pointer;">⬇️ Ta hem saknad Bild-VAE/CLIP (HF)</button>` : ""}
                          <button class="ez-equip-rig-res" data-res-mod="IMAGE" style="background:#065f46;color:#a7f3d0;border:none;border-radius:3px;padding:1px 6px;font-size:8px;font-weight:bold;cursor:pointer;">⚡ Koppla Optimala till [03]</button>
                        </div>
                      </div>
                      <div style="font-size:7.8px;color:#fde68a;">🎯 <b>Optimalt (${imgArchNow}):</b> UNet: <b>${imgBp.unet}</b> | CLIP: <b>${imgBp.clip}</b> | VAE: <b>${imgBp.vae}</b></div>
                      <div style="font-size:7.8px;color:#cbd5e1;display:flex;flex-wrap:wrap;gap:6px;">
                        <span>🏛️ UNet: <b style="color:${imgUnetOk ? "#34d399" : "#fbbf24"};">${imgUnetOk ? `🟢 På disk (${shortLabel(imgComp.unet_name)})` : "🟡 Välj i UNet-listan ovan"}</b></span>
                        <span>🔤 CLIP (${imgClipList.length} på disk): <b style="color:${imgClipOk ? "#34d399" : "#f87171"};">${imgClipOk ? `🟢 ${shortLabel(imgComp.clip_name)}` : "🔴 SAKNAS — Ta hem"}</b></span>
                        <span>🎨 VAE (${imgVaeList.length} på disk): <b style="color:${imgVaeOk ? "#34d399" : "#f87171"};">${imgVaeOk ? `🟢 ${shortLabel(imgComp.vae_name)}` : "🔴 SAKNAS — Ta hem"}</b></span>
                      </div>
                    </div>

                    <!-- [05/07] VIDEO-RESURSER -->
                    <div style="background:#111624;border:1px solid ${vidClipOk && vidVaeOk && vidAudOk ? "#10b981" : "#ef4444"};border-radius:4px;padding:5px 6px;display:flex;flex-direction:column;gap:3px;">
                      <div style="display:flex;justify-content:space-between;align-items:center;gap:4px;">
                        <span style="font-size:8.5px;font-weight:bold;color:${vidClipOk && vidVaeOk && vidAudOk ? "#34d399" : "#fbbf24"};">🎬 [05/07] VIDEO-RESURSER (${vidArchNow})</span>
                        <div style="display:flex;gap:3px;">
                          ${canDlVid ? `<button class="ez-comp-dl" data-comp-arch="${vidArchNow}" data-comp-mod="VIDEO" style="background:#0284c7;color:#fff;border:none;border-radius:3px;padding:1px 6px;font-size:8px;font-weight:bold;cursor:pointer;">⬇️ Ta hem saknad Video-VAE/CLIP (HF)</button>` : ""}
                          <button class="ez-equip-rig-res" data-res-mod="VIDEO" style="background:#065f46;color:#a7f3d0;border:none;border-radius:3px;padding:1px 6px;font-size:8px;font-weight:bold;cursor:pointer;">⚡ Koppla Optimala till [05]</button>
                        </div>
                      </div>
                      <div style="font-size:7.8px;color:#fde68a;">🎯 <b>Optimalt (${vidArchNow}):</b> UNet: <b>${vidBp.unet}</b> | CLIP: <b>${vidBp.clip}</b> | V-VAE: <b>${vidBp.vae}</b>${vidBp.audio_vae ? ` | A-VAE: <b>${vidBp.audio_vae}</b>` : ""}</div>
                      <div style="font-size:7.8px;color:#cbd5e1;display:flex;flex-wrap:wrap;gap:6px;">
                        <span>🏛️ UNet: <b style="color:${vidUnetOk ? "#34d399" : "#fbbf24"};">${vidUnetOk ? `🟢 På disk (${shortLabel(vidComp.unet_name)})` : "🟡 Välj i UNet-listan ovan"}</b></span>
                        <span>🔤 CLIP (${vidClipList.length}): <b style="color:${vidClipOk ? "#34d399" : "#f87171"};">${vidClipOk ? `🟢 ${shortLabel(vidComp.clip_name)}` : "🔴 SAKNAS"}</b></span>
                        <span>🎞️ V-VAE (${vidVaeList.length}): <b style="color:${vidVaeOk ? "#34d399" : "#f87171"};">${vidVaeOk ? `🟢 ${shortLabel(vidComp.vae_name)}` : "🔴 SAKNAS"}</b></span>
                        ${vidComp && vidComp.audio_vae_name ? `<span>🔊 A-VAE (${vidAudList.length || 1}): <b style="color:${vidAudOk ? "#34d399" : "#f87171"};">${vidAudOk ? `🟢 ${shortLabel(vidComp.audio_vae_name)}` : "🔴 SAKNAS"}</b></span>` : ""}
                      </div>
                    </div>

                    ${subNotices.length ? `<div style="font-size:7.5px;color:#fbbf24;background:#1c1917;border:1px solid #78350f;border-radius:3px;padding:2px 5px;">⚠️ ${subNotices.join(" | ")}</div>` : ""}
                    <div style="display:flex;justify-content:space-between;align-items:center;background:#13161f;border:1px solid ${dupSum.total_duplicate_files > 0 ? "#f59e0b" : "#1e293b"};border-radius:4px;padding:3px 6px;flex-wrap:wrap;gap:4px;">
                      <span style="font-size:8px;color:${dupSum.total_duplicate_files > 0 ? "#fbbf24" : "#94a3b8"};font-weight:bold;">
                        💿 Lokalt på disk: <b>${state.localModels.length} Modeller</b> · <b>${state.localLoras.length} LoRAs</b> · <b>${totResCount} Resursfiler</b> | 🧬 Dubbletter: <b>${dupSum.total_duplicate_files > 0 ? `${dupSum.total_duplicate_files} st (${dupSum.reclaimable_mb} MB)` : "0 st"}</b>
                      </span>
                      <div style="display:flex;gap:3px;">
                        <button class="ez-open-res-view" style="background:#0284c7;color:#fff;border:none;border-radius:3px;padding:2px 6px;font-size:8px;font-weight:bold;cursor:pointer;">🧬 Se Alla Resursfiler (${totResCount})</button>
                        <button class="ez-open-dup-view" style="background:${dupSum.total_duplicate_files > 0 ? "#eab308" : "#1e293b"};color:${dupSum.total_duplicate_files > 0 ? "#000" : "#cbd5e1"};border:none;border-radius:3px;padding:2px 6px;font-size:8px;font-weight:bold;cursor:pointer;">🗂️ Lokal Filbank & Radera</button>
                      </div>
                    </div>
                  </div>
                  <div style="background:#0d1512;border:1px solid #10b981;border-radius:5px;padding:6px 8px;display:flex;flex-direction:column;gap:4px;flex-shrink:0;">
                    <div style="display:flex;justify-content:space-between;align-items:center;gap:4px;flex-wrap:wrap;">
                      <span style="font-size:8.5px;color:#34d399;font-weight:bold;">⚡ DYNAMISKA OPTIMALA INSTÄLLNINGAR (${opt.selected_model_name ? shortLabel(opt.selected_model_name) : curArch} · ${sysTier.tier_short}):</span>
                      <button class="ez-apply-opt-graph" data-opt-mod="${isVid ? "VIDEO" : "IMAGE"}" style="background:linear-gradient(90deg,#10b981,#34d399);color:#000;border:none;border-radius:3px;padding:2px 7px;font-size:8px;font-weight:bold;cursor:pointer;" title="Sätter Author- & Tier-anpassad Sampler, Scheduler, Steps, CFG, Denoise, Shift & Stack-balanserade LoRA-styrkor direkt på [03]/[04] eller [05]/[07]">⚡ Applicera på ${isVid ? "[05] & [07]" : "[03] & [04]"}</button>
                    </div>
                    <div style="font-size:8.5px;color:#e2e8f0;">🎯 Sampler: <b style="color:#facc15;">${opt.sampler}</b> | Scheduler: <b style="color:#facc15;">${opt.scheduler}</b> | Steps: <b>${opt.steps}</b>${opt.author_steps_range && opt.author_steps_range !== String(opt.steps) ? ` <span style="color:#94a3b8;">(Author: ${opt.author_steps_range})</span>` : ""} | CFG: <b>${opt.cfg}</b>${opt.author_cfg_range && opt.author_cfg_range !== String(opt.cfg) ? ` <span style="color:#94a3b8;">(Author: ${opt.author_cfg_range})</span>` : ""}${!isVid && opt.clip_skip ? ` | Clip Skip: <b style="color:#38bdf8;">${opt.clip_skip}</b>` : ""} | Denoise: <b style="color:#34d399;">${Number(opt.denoise ?? 1.0).toFixed(2)}</b>${isVid ? ` | Shift V/A: <b>${opt.shift_video ?? 5.0}/${opt.shift_audio ?? 3.0}</b>` : ""}</div>
                    ${opt.author_summary_line ? `<div style="font-size:8px;color:#fde68a;background:#090d14;border:1px solid #1e293b;border-radius:3px;padding:2px 5px;line-height:1.25;">${opt.author_summary_line}</div>` : `<div style="font-size:8px;color:#94a3b8;line-height:1.25;">💡 ${opt.arch_note || ""}</div>`}
                    ${opt.quant_tech_note ? `<div style="font-size:7.8px;color:#a7f3d0;background:#06281e;border:1px solid #047857;border-radius:3px;padding:2px 5px;line-height:1.25;">${opt.quant_tech_note}</div>` : ""}
                    ${Array.isArray(opt.selected_lora_profiles) && opt.selected_lora_profiles.length > 0 ? `
                      <div style="display:flex;flex-direction:column;gap:2px;background:#090c12;border:1px solid #1e293b;border-radius:3px;padding:3px 5px;">
                        <div style="font-size:7.8px;color:#38bdf8;font-weight:bold;">${opt.stack_harmony_note || "🧩 Aktiva LoRA-profiler (Relativt till ditt val):"}</div>
                        ${opt.selected_lora_profiles.map(lp => `<div style="font-size:7.6px;color:#cbd5e1;display:flex;justify-content:space-between;gap:4px;flex-wrap:wrap;"><span>• <b>Slot ${lp.slot_index} (${shortLabel(lp.lora_name)}):</b> Author <b>${lp.author_weight_range || lp.rec_strength}</b>${lp.network_dim ? ` · Rank ${lp.network_dim}/Alpha ${lp.network_alpha}` : ""}</span><span style="color:#34d399;font-weight:bold;">⚡ Stack-Optimal: ${Number(lp.stack_balanced_strength ?? lp.rec_strength).toFixed(2)} (VIS ${Number(lp.vis_strength ?? 1.0).toFixed(1)}/Aud ${Number(lp.audio_strength ?? 0.0).toFixed(1)}/CLIP ${Number(lp.clip_strength ?? 0.0).toFixed(1)})</span></div>`).join("")}
                      </div>
                    ` : ""}
                  </div>
                `;
            })()}
            <div style="display:grid;grid-template-columns:${isCompact ? "repeat(auto-fill,minmax(240px,1fr))" : "1fr"};gap:5px;">
              ${slotsHtml}
            </div>
            <div style="background:#11131a;border:1px solid #1e293b;border-radius:5px;padding:5px 7px;display:flex;flex-direction:column;gap:3px;flex-shrink:0;">
              <span style="font-size:8.5px;color:#94a3b8;font-weight:bold;">⚡ Trigger Words (injiceras i [02] / [06]):</span>
              <input type="text" class="ez-trig-input" value="${String(getWidgetVal("trigger_words", "")).replace(/"/g, "&quot;")}" placeholder="Inga trigger words aktiva..." style="background:#090a0f;color:#facc15;border:1px solid #334155;border-radius:3px;padding:4px 6px;font-size:9.5px;" />
            </div>
          </div>
        `;
    };

    const bindStackEvents = (container, refreshFn) => {
        container.querySelectorAll("[data-stack-mod]").forEach(btn => {
            btn.onclick = () => {
                state.stackModality = btn.getAttribute("data-stack-mod");
                setWidgetVal("controller_modality", state.stackModality === "VIDEO" ? "VIDEO — Video (MiniMax H3 / Wan 2.1 / LTXV / Hunyuan)" : "IMAGE — Bild (KREA2 / Flux.1 / SDXL / Qwen-Image)");
                const arch = getWidgetVal(state.stackModality === "VIDEO" ? "video_architecture" : "image_architecture", state.stackModality === "VIDEO" ? "MiniMax H3" : "KREA2");
                fetchArchitectureCompanions(arch, state.stackModality, "resolve");
            };
        });
        container.querySelectorAll("[data-arch]").forEach(btn => {
            btn.onclick = () => {
                const a = btn.getAttribute("data-arch");
                setWidgetVal(state.stackModality === "VIDEO" ? "video_architecture" : "image_architecture", a);
                state.civArch = a;
                fetchArchitectureCompanions(a, state.stackModality, "resolve");
            };
        });
        container.querySelectorAll("[data-slot-select]").forEach(sel => {
            sel.onchange = () => {
                const slotKey = sel.getAttribute("data-slot-select");
                const mod = sel.getAttribute("data-slot-mod") || "IMAGE";
                const val = sel.value || "None";
                if (val === "None") {
                    setWidgetVal(slotKey, "None");
                    syncSlotToDownstreamGraphNodes(slotKey, "None", null);
                    const activeArchNow = getWidgetVal(mod === "VIDEO" ? "video_architecture" : "image_architecture", mod === "VIDEO" ? "MiniMax H3" : "KREA2");
                    fetchArchitectureCompanions(activeArchNow, mod, "resolve");
                    state.statusMsg = `🧹 Rensade ${slotKey}`;
                    syncAllViews();
                } else {
                    const locItem = state.localLoras.concat(state.localModels).find(x => x.name === val);
                    assignAssetToSlot(slotKey, val, mod, [], "", (locItem && locItem.optimal_settings) || null);
                }
            };
        });
        const equipAllOptBtn = container.querySelector(".ez-equip-all-optimal");
        if (equipAllOptBtn) {
            equipAllOptBtn.onclick = () => {
                const imgComp = state.imageCompanions || {};
                const vidComp = state.videoCompanions || {};
                const vlmComp = (imgComp && imgComp.vlm_companions) || (vidComp && vidComp.vlm_companions) || {};
                let equipped = [];
                if (vlmComp.active_vlm_name && vlmComp.active_vlm_name !== "None") {
                    assignVlmToTimelineCompiler(vlmComp.active_vlm_name);
                    equipped.push(`[02] ${shortLabel(vlmComp.active_vlm_name)}`);
                }
                if (imgComp.unet_name && imgComp.unet_name !== "None") {
                    assignAssetToSlot("image_unet_name", imgComp.unet_name, "IMAGE");
                    equipped.push(`[03 UNet] ${shortLabel(imgComp.unet_name)}`);
                }
                if (imgComp.turbo_lora_name && imgComp.turbo_lora_name !== "None") {
                    assignAssetToSlot("image_turbo_lora", imgComp.turbo_lora_name, "IMAGE");
                }
                if (imgComp.clip_name && imgComp.clip_name !== "None") syncResourceToDownstreamGraphNodes("CLIP", imgComp.clip_name, "IMAGE");
                if (imgComp.vae_name && imgComp.vae_name !== "None") syncResourceToDownstreamGraphNodes("VAE", imgComp.vae_name, "IMAGE");
                if (vidComp.unet_name && vidComp.unet_name !== "None") {
                    assignAssetToSlot("video_unet_fl2va", vidComp.unet_name, "VIDEO");
                    equipped.push(`[05 UNet] ${shortLabel(vidComp.unet_name)}`);
                }
                if (vidComp.turbo_lora_name && vidComp.turbo_lora_name !== "None") {
                    assignAssetToSlot("video_turbo_lora", vidComp.turbo_lora_name, "VIDEO");
                }
                if (vidComp.clip_name && vidComp.clip_name !== "None") syncResourceToDownstreamGraphNodes("CLIP", vidComp.clip_name, "VIDEO");
                if (vidComp.vae_name && vidComp.vae_name !== "None") syncResourceToDownstreamGraphNodes("VAE", vidComp.vae_name, "VIDEO");
                if (vidComp.audio_vae_name && vidComp.audio_vae_name !== "None") syncResourceToDownstreamGraphNodes("AUDIO_VAE", vidComp.audio_vae_name, "VIDEO");
                state.statusMsg = `⚡ Utrustade optimala filer i riggen: ${equipped.join(" · ") || "CLIP/VAE synkade"}!`;
                syncAllViews();
            };
        }
        container.querySelectorAll(".ez-equip-rig-res").forEach(btn => {
            btn.onclick = () => {
                const mod = btn.getAttribute("data-res-mod") || "IMAGE";
                const isV = mod === "VIDEO";
                const c = isV ? (state.videoCompanions || {}) : (state.imageCompanions || {});
                if (c.unet_name && c.unet_name !== "None") assignAssetToSlot(isV ? "video_unet_fl2va" : "image_unet_name", c.unet_name, mod);
                if (c.turbo_lora_name && c.turbo_lora_name !== "None") assignAssetToSlot(isV ? "video_turbo_lora" : "image_turbo_lora", c.turbo_lora_name, mod);
                if (c.clip_name && c.clip_name !== "None") syncResourceToDownstreamGraphNodes("CLIP", c.clip_name, mod);
                if (c.vae_name && c.vae_name !== "None") syncResourceToDownstreamGraphNodes("VAE", c.vae_name, mod);
                if (isV && c.audio_vae_name && c.audio_vae_name !== "None") syncResourceToDownstreamGraphNodes("AUDIO_VAE", c.audio_vae_name, "VIDEO");
                state.statusMsg = `✅ Kopplade optimala ${isV ? "Video ([05])" : "Bild ([03])"}-resurser (UNet, CLIP, VAE)!`;
                syncAllViews();
            };
        });
        const vlmSel02 = container.querySelector(".ez-vlm-select-02");
        if (vlmSel02) {
            vlmSel02.onchange = () => {
                const vn = vlmSel02.value || "";
                if (vn) {
                    const ok = assignVlmToTimelineCompiler(vn);
                    if (state.imageCompanions && state.imageCompanions.vlm_companions) state.imageCompanions.vlm_companions.active_vlm_name = vn;
                    if (state.videoCompanions && state.videoCompanions.vlm_companions) state.videoCompanions.vlm_companions.active_vlm_name = vn;
                    state.statusMsg = ok ? `✅ Satte [02] vlm_model_name = ${vn}!` : `ℹ️ Valde VLM: ${vn}`;
                    syncAllViews();
                }
            };
        }
        const compCheckAllBtn = container.querySelector(".ez-comp-check-all");
        if (compCheckAllBtn) {
            compCheckAllBtn.onclick = async () => {
                const iArch = getWidgetVal("image_architecture", "KREA2");
                const vArch = getWidgetVal("video_architecture", "MiniMax H3");
                await fetchLocalCatalog();
                await fetchArchitectureCompanions(iArch, "IMAGE", "resolve");
                await fetchArchitectureCompanions(vArch, "VIDEO", "resolve");
                state.statusMsg = `✓ Skannade disk: ${state.localModels.length} modeller, ${state.localLoras.length} LoRAs, ${state.localResources.length} resursfiler!`;
                syncAllViews();
            };
        }
        container.querySelectorAll(".ez-comp-dl").forEach(btn => {
            btn.onclick = () => {
                fetchArchitectureCompanions(btn.getAttribute("data-comp-arch"), btn.getAttribute("data-comp-mod"), "download");
            };
        });
        const vlmAutoBtn = container.querySelector(".ez-vlm-auto-hf");
        if (vlmAutoBtn) {
            vlmAutoBtn.onclick = () => {
                triggerHuggingFaceDownload(
                    "huihui-ai/Huihui-Qwen3-VL-4B-Instruct-abliterated",
                    "__FULL_HF_REPO__",
                    "LLM/Qwen-VL",
                    true
                );
            };
        }
        const vlmSyncBtn = container.querySelector(".ez-vlm-sync-02");
        if (vlmSyncBtn) {
            vlmSyncBtn.onclick = () => {
                const vn = (vlmSel02 && vlmSel02.value) || vlmSyncBtn.getAttribute("data-vlm-name") || "";
                if (vn) {
                    const ok = assignVlmToTimelineCompiler(vn);
                    state.statusMsg = ok ? `✅ Satte [02] vlm_model_name = ${vn}!` : `ℹ️ ${vn} är redo (öppna [02] Timeline för att välja).`;
                    syncAllViews();
                }
            };
        }
        const openResBtn = container.querySelector(".ez-open-res-view");
        if (openResBtn) {
            openResBtn.onclick = () => {
                state.localFilterType = "RESOURCES";
                state.localFilterMod = "ALL";
                state.activeTab = "local";
                syncAllViews();
            };
        }
        const openDupBtn = container.querySelector(".ez-open-dup-view");
        if (openDupBtn) {
            openDupBtn.onclick = () => {
                const dSum = state.duplicateSummary || {};
                state.localFilterType = dSum.total_duplicate_files > 0 ? "DUPLICATES" : "Checkpoint";
                state.localFilterMod = "ALL";
                state.activeTab = "local";
                syncAllViews();
            };
        }
        const applyOptBtn = container.querySelector(".ez-apply-opt-graph");
        if (applyOptBtn) {
            applyOptBtn.onclick = () => {
                applyOptimalSettingsToConnectedGraph(applyOptBtn.getAttribute("data-opt-mod") === "VIDEO");
            };
        }
        container.querySelectorAll("[data-toggle-enable]").forEach(btn => {
            btn.onclick = () => {
                const eKey = btn.getAttribute("data-toggle-enable");
                const sKey = btn.getAttribute("data-toggle-slot");
                const curState = Boolean(getWidgetVal(eKey, true));
                const nextState = !curState;
                setWidgetVal(eKey, nextState);
                if (sKey) {
                    syncSlotToDownstreamGraphNodes(sKey, null, null, nextState);
                }
                const lName = sKey ? shortLabel(getWidgetVal(sKey, "None")) : eKey;
                state.statusMsg = nextState
                    ? `🟢 Aktiverade ${sKey} (${lName})`
                    : `🔇 Bypass aktiv på ${sKey} (${lName} ligger kvar i menyn men hoppas över vid körning)`;
                syncAllViews();
            };
        });
        container.querySelectorAll("[data-clear-slot]").forEach(btn => {
            btn.onclick = () => {
                const sk = btn.getAttribute("data-clear-slot");
                const isV = String(sk || "").startsWith("video_");
                setWidgetVal(sk, "None");
                syncSlotToDownstreamGraphNodes(sk, "None", null);
                const activeArchNow = getWidgetVal(isV ? "video_architecture" : "image_architecture", isV ? "MiniMax H3" : "KREA2");
                fetchArchitectureCompanions(activeArchNow, isV ? "VIDEO" : "IMAGE", "resolve");
                syncAllViews();
            };
        });
        container.querySelectorAll("[data-pick-local]").forEach(btn => {
            btn.onclick = () => {
                state.localFilterMod = btn.getAttribute("data-pick-mod") || "ALL";
                state.localFilterType = "LORA";
                state.activeTab = "local";
                syncAllViews();
            };
        });
        container.querySelectorAll("[data-pick-local-model]").forEach(btn => {
            btn.onclick = () => {
                state.localFilterMod = btn.getAttribute("data-pick-mod") || "ALL";
                state.localFilterType = "Checkpoint";
                state.activeTab = "local";
                syncAllViews();
            };
        });
        container.querySelectorAll("[data-pick-civ]").forEach(btn => {
            btn.onclick = () => {
                state.civModality = btn.getAttribute("data-pick-mod") || "IMAGE";
                state.civType = "LORA";
                state.activeTab = "civitai";
                syncAllViews();
                if (!state.civItems.length) runCivitaiSearch(false);
            };
        });
        container.querySelectorAll("[data-pick-civ-model]").forEach(btn => {
            btn.onclick = () => {
                state.civModality = btn.getAttribute("data-pick-mod") || "IMAGE";
                state.civType = "Checkpoint";
                state.activeTab = "civitai";
                syncAllViews();
                if (!state.civItems.length) runCivitaiSearch(false);
            };
        });
        container.querySelectorAll("[data-slider-key]").forEach(sl => {
            sl.oninput = (ev) => {
                const k = sl.getAttribute("data-slider-key");
                const v = parseFloat(ev.target.value);
                setWidgetVal(k, v);
                const mappedSlot = STRENGTH_TO_SLOT_MAP[k];
                if (mappedSlot) {
                    syncSlotToDownstreamGraphNodes(mappedSlot, null, v);
                }
                const lbl = sl.parentElement && sl.parentElement.querySelector(".ez-sl-val");
                if (lbl) lbl.textContent = v.toFixed(2);
            };
            sl.onchange = () => syncAllViews();
        });
        const trigIn = container.querySelector(".ez-trig-input");
        if (trigIn) {
            trigIn.onchange = () => {
                setWidgetVal("trigger_words", trigIn.value || "");
                syncAllViews();
            };
        }
    };

    const buildLocalBankHtml = (cols = 2) => {
        const allCombined = state.localLoras.concat(state.localModels, state.localResources);
        const dupItems = allCombined.filter(x => x && x.is_duplicate);
        dupItems.sort((a, b) => String(a.dup_group_id || "").localeCompare(String(b.dup_group_id || "")) || (b.keep_recommended ? 1 : -1));
        const sourceList = state.localFilterType === "DUPLICATES"
            ? dupItems
            : (state.localFilterType === "RESOURCES"
                ? state.localResources
                : (state.localFilterType === "LORA" ? state.localLoras : state.localModels));
        const q = state.localQuery.trim().toLowerCase();
        const filtered = sourceList.filter(item => {
            if (state.localFilterMod !== "ALL" && item.modality !== state.localFilterMod && item.modality !== "VLM") return false;
            if (q && !item.name.toLowerCase().includes(q) && !String(item.resource_role || "").toLowerCase().includes(q)) return false;
            return true;
        });
        const cardsHtml = filtered.length
            ? filtered.map((item, idx) => {
                const isVid = item.modality === "VIDEO";
                const isVlm = item.modality === "VLM";
                const isLoraItem = item.asset_type === "LORA";
                const isResourceItem = item.asset_type === "Resource";
                const modColor = isVlm ? "#a855f7" : (isVid ? "#34d399" : "#fbbf24");
                const pUrl = item.preview_url ? api.apiURL(item.preview_url) : "";
                const delKey = `${item.category || (isLoraItem ? "loras" : "diffusion_models")}:${item.name}`;
                const isConfirmingDel = state.pendingDeleteKey === delKey;
                const roleIcon = isResourceItem
                    ? (item.resource_role === "VLM" || item.resource_role === "MMPROJ" ? "🧠" : (item.resource_role === "AUDIO_VAE" ? "🔊" : (item.resource_role === "CLIP" ? "🔤" : "🎨")))
                    : (isVid ? "🎬" : "🖼️");
                const mediaBox = pUrl
                    ? (item.is_video
                        ? `<video src="${pUrl}" autoplay loop muted playsinline style="width:100%;aspect-ratio:16/10;min-height:115px;object-fit:cover;background:#07080c;border-radius:3px;"></video>`
                        : `<img src="${pUrl}" style="width:100%;aspect-ratio:16/10;min-height:115px;object-fit:cover;background:#07080c;border-radius:3px;" />`)
                    : `<div style="width:100%;aspect-ratio:16/10;min-height:${isResourceItem ? "68px" : "95px"};background:linear-gradient(135deg,#111420,#191e2e);border-radius:3px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;">
                         <span style="font-size:20px;">${roleIcon}</span>
                         <span style="font-size:8px;color:#94a3b8;font-weight:bold;">models/${item.subfolder || item.category}</span>
                       </div>`;

                let slotBtns = "";
                if (isResourceItem) {
                    if (item.resource_role === "VLM") {
                        slotBtns = `<button data-loc-res-idx="${idx}" data-res-role="VLM" data-res-mod="VLM" style="flex:1;background:#a855f7;color:#fff;border:none;border-radius:2px;padding:3px 6px;font-size:8.5px;cursor:pointer;font-weight:bold;">🧠 KOPPLA TILL [02] QWEN-VL</button>`;
                    } else if (item.resource_role === "MMPROJ") {
                        slotBtns = `<span style="font-size:8px;color:#34d399;font-weight:bold;">👁️ Auto-laddas med Qwen-VL GGUF i [02]</span>`;
                    } else if (item.resource_role === "AUDIO_VAE") {
                        slotBtns = `<button data-loc-res-idx="${idx}" data-res-role="AUDIO_VAE" data-res-mod="VIDEO" style="flex:1;background:#10b981;color:#000;border:none;border-radius:2px;padding:3px 6px;font-size:8.5px;cursor:pointer;font-weight:bold;">🔊 SÄTT SOM [05] AUDIO-VAE</button>`;
                    } else if (item.resource_role === "VAE") {
                        slotBtns = `<button data-loc-res-idx="${idx}" data-res-role="VAE" data-res-mod="IMAGE" style="flex:1;background:#fbbf24;color:#000;border:none;border-radius:2px;padding:3px 5px;font-size:8px;cursor:pointer;font-weight:bold;">🎨 [03] Bild-VAE</button>
                                    <button data-loc-res-idx="${idx}" data-res-role="VAE" data-res-mod="VIDEO" style="flex:1;background:#34d399;color:#000;border:none;border-radius:2px;padding:3px 5px;font-size:8px;cursor:pointer;font-weight:bold;">🎞️ [05] Video-VAE</button>`;
                    } else if (item.resource_role === "CLIP") {
                        slotBtns = `<button data-loc-res-idx="${idx}" data-res-role="CLIP" data-res-mod="IMAGE" style="flex:1;background:#fbbf24;color:#000;border:none;border-radius:2px;padding:3px 5px;font-size:8px;cursor:pointer;font-weight:bold;">🔤 [03] Bild-CLIP</button>
                                    <button data-loc-res-idx="${idx}" data-res-role="CLIP" data-res-mod="VIDEO" style="flex:1;background:#34d399;color:#000;border:none;border-radius:2px;padding:3px 5px;font-size:8px;cursor:pointer;font-weight:bold;">🔤 [05] Video-CLIP</button>`;
                    }
                } else if (isLoraItem) {
                    slotBtns = isVid
                        ? `<button data-loc-idx="${idx}" data-slot="video_lora_1" style="background:#065f46;color:#fff;border:none;border-radius:2px;padding:2px 4px;font-size:8.5px;cursor:pointer;font-weight:bold;">+V1</button>
                           <button data-loc-idx="${idx}" data-slot="video_lora_2" style="background:#065f46;color:#fff;border:none;border-radius:2px;padding:2px 4px;font-size:8.5px;cursor:pointer;font-weight:bold;">+V2</button>
                           <button data-loc-idx="${idx}" data-slot="video_lora_3" style="background:#065f46;color:#fff;border:none;border-radius:2px;padding:2px 4px;font-size:8.5px;cursor:pointer;font-weight:bold;">+V3</button>
                           <button data-loc-idx="${idx}" data-slot="video_lora_4" style="background:#065f46;color:#fff;border:none;border-radius:2px;padding:2px 4px;font-size:8.5px;cursor:pointer;font-weight:bold;">+V4</button>
                           <button data-loc-idx="${idx}" data-slot="video_turbo_lora" style="background:#047857;color:#a7f3d0;border:none;border-radius:2px;padding:2px 4px;font-size:8.5px;cursor:pointer;font-weight:bold;">⚡Turbo</button>`
                        : `<button data-loc-idx="${idx}" data-slot="image_style_lora_1" style="background:#92400e;color:#fff;border:none;border-radius:2px;padding:2px 4px;font-size:8.5px;cursor:pointer;font-weight:bold;">+B1</button>
                           <button data-loc-idx="${idx}" data-slot="image_style_lora_2" style="background:#92400e;color:#fff;border:none;border-radius:2px;padding:2px 4px;font-size:8.5px;cursor:pointer;font-weight:bold;">+B2</button>
                           <button data-loc-idx="${idx}" data-slot="image_style_lora_3" style="background:#92400e;color:#fff;border:none;border-radius:2px;padding:2px 4px;font-size:8.5px;cursor:pointer;font-weight:bold;">+B3</button>
                           <button data-loc-idx="${idx}" data-slot="image_style_lora_4" style="background:#92400e;color:#fff;border:none;border-radius:2px;padding:2px 4px;font-size:8.5px;cursor:pointer;font-weight:bold;">+B4</button>
                           <button data-loc-idx="${idx}" data-slot="image_turbo_lora" style="background:#b45309;color:#fde68a;border:none;border-radius:2px;padding:2px 4px;font-size:8.5px;cursor:pointer;font-weight:bold;">⚡Turbo</button>`;
                } else {
                    slotBtns = `<button data-loc-idx="${idx}" data-slot="image_unet_name" data-force-mod="IMAGE" style="flex:1;background:${!isVid ? "#fbbf24" : "#1e293b"};color:${!isVid ? "#000" : "#e2e8f0"};border:none;border-radius:2px;padding:3px 5px;font-size:8.5px;cursor:pointer;font-weight:bold;">🖼️ [03] Bild UNet</button>
                                <button data-loc-idx="${idx}" data-slot="video_unet_fl2va" data-force-mod="VIDEO" style="flex:1;background:${isVid ? "#34d399" : "#1e293b"};color:${isVid ? "#000" : "#e2e8f0"};border:none;border-radius:2px;padding:3px 5px;font-size:8.5px;cursor:pointer;font-weight:bold;">🎬 [05] Video UNet</button>`;
                }

                const delBtnHtml = isConfirmingDel
                    ? `<button data-loc-del-confirm="${idx}" style="background:#dc2626;color:#fff;border:1px solid #fca5a5;border-radius:2px;padding:2px 6px;font-size:8.5px;cursor:pointer;font-weight:bold;">⚠️ Radera nu?</button>
                       <button data-loc-del-cancel="${idx}" style="background:#334155;color:#e2e8f0;border:none;border-radius:2px;padding:2px 5px;font-size:8px;cursor:pointer;">✕</button>`
                    : `<button data-loc-del-ask="${idx}" style="background:#450a0a;color:#fca5a5;border:1px solid #7f1d1d;border-radius:2px;padding:2px 5px;font-size:8.5px;cursor:pointer;margin-left:auto;" title="Radera ${item.name} från disken">🗑️</button>`;

                const tierBadge = item.optimal_tier_badge
                    ? `<div style="font-size:7.8px;font-weight:bold;padding:2px 5px;border-radius:3px;background:${item.optimal_tier_level === "OPTIMAL" ? "#064e3b" : (item.optimal_tier_level === "SUBOPTIMAL" ? "#451a03" : "#0f172a")};color:${item.optimal_tier_level === "OPTIMAL" ? "#34d399" : (item.optimal_tier_level === "SUBOPTIMAL" ? "#fbbf24" : "#38bdf8")};border:1px solid ${item.optimal_tier_level === "OPTIMAL" ? "#10b981" : (item.optimal_tier_level === "SUBOPTIMAL" ? "#f59e0b" : "#1e293b")};" title="${item.optimal_tier_reason || ""}">${item.optimal_tier_badge}</div>`
                    : "";

                const dupBanner = item.is_duplicate
                    ? `<div style="font-size:8px;font-weight:bold;padding:2px 5px;border-radius:3px;background:${item.keep_recommended ? "#064e3b" : "#450a0a"};color:${item.keep_recommended ? "#34d399" : "#fca5a5"};border:1px solid ${item.keep_recommended ? "#10b981" : "#ef4444"};display:flex;justify-content:space-between;align-items:center;" title="${item.keep_reason || ""} — Dubblett till: ${(item.dup_peers || []).join(", ")}">
                         <span>${item.keep_recommended ? `⭐ BEHÅLL (${item.keep_reason || "Optimal"})` : "🗑️ DUBBLETT (Kan raderas)"}</span>
                         <span>${item.dup_type === "EXACT_BINARY" ? "100% Binär" : "Variant"}</span>
                       </div>`
                    : "";

                const optBadge = (item.optimal_settings && item.optimal_settings.summary_badge) || item.optimal_tier_reason || "";
                const cardBorder = item.is_duplicate
                    ? (item.keep_recommended ? "#10b981" : "#ef4444")
                    : (item.optimal_tier_level === "OPTIMAL" ? "#10b981" : "#262b38");
                const dispRole = isLoraItem
                    ? (isTrueTurboLoraName(item.name) ? "TURBO_LORA" : "STYLE_LORA")
                    : (item.resource_role || item.asset_type);
                return `
                  <div style="background:#13161f;border:1px solid ${cardBorder};border-radius:5px;padding:5px;display:flex;flex-direction:column;gap:4px;">
                    <div style="position:relative;">
                      ${mediaBox}
                      <span style="position:absolute;top:3px;left:3px;background:rgba(9,10,15,0.9);color:${modColor};border:1px solid ${modColor};font-size:8px;padding:1px 4px;border-radius:2px;font-weight:bold;">${item.modality} • ${dispRole}</span>
                      <span style="position:absolute;top:3px;right:3px;background:rgba(9,10,15,0.9);color:#94a3b8;font-size:8px;padding:1px 4px;border-radius:2px;">${item.size_mb >= 1024 ? `${(item.size_mb / 1024).toFixed(2)} GB` : `${item.size_mb} MB`}</span>
                    </div>
                    ${tierBadge}
                    ${dupBanner}
                    <div style="font-size:9.5px;font-weight:bold;color:#f8fafc;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="${item.name} (${item.subfolder || item.category})">${item.short_name}</div>
                    ${item.is_duplicate && item.dup_peers && item.dup_peers.length ? `<div style="font-size:7.5px;color:#fbbf24;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="Dubblett med: ${item.dup_peers.join(", ")}">🔗 Dubblett med: ${shortLabel(item.dup_peers[0])}</div>` : ""}
                    ${optBadge ? `<div style="font-size:7.8px;color:#94a3b8;background:#0b111e;border:1px solid #1e293b;border-radius:3px;padding:2px 4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="${optBadge}">${optBadge}</div>` : ""}
                    <div style="display:flex;gap:3px;flex-wrap:wrap;align-items:center;margin-top:auto;">${slotBtns}${delBtnHtml}</div>
                  </div>
                `;
            }).join("")
            : `<div style="grid-column:1/-1;padding:18px;text-align:center;color:#94a3b8;font-size:10px;">${state.localFilterType === "DUPLICATES" ? "✅ Inga dubbletter hittades bland dina lokalt nedladdade modeller, LoRAs och resursfiler!" : `Inga lokala filer matchade filtret (${state.localFilterType}). Klicka på 🔄 Skanna för att uppdatera.`}</div>`;

        const dupSum = state.duplicateSummary || { total_groups: 0, total_duplicate_files: 0, reclaimable_mb: 0 };
        return {
            filtered,
            cardsHtml,
            html: `
              <div style="display:flex;flex-direction:column;gap:6px;flex:1;min-height:0;height:100%;">
                <div style="display:flex;gap:4px;flex-wrap:wrap;justify-content:space-between;flex-shrink:0;">
                  <div style="display:flex;gap:3px;flex-wrap:wrap;">
                    <button data-loc-type="LORA" style="background:${state.localFilterType === "LORA" ? "#eab308" : "#13161f"};color:${state.localFilterType === "LORA" ? "#000" : "#cbd5e1"};border:1px solid #334155;border-radius:3px;padding:3px 7px;font-size:9.5px;font-weight:bold;cursor:pointer;">🧩 LoRAs (${state.localLoras.length})</button>
                    <button data-loc-type="Checkpoint" style="background:${state.localFilterType === "Checkpoint" ? "#eab308" : "#13161f"};color:${state.localFilterType === "Checkpoint" ? "#000" : "#cbd5e1"};border:1px solid #334155;border-radius:3px;padding:3px 7px;font-size:9.5px;font-weight:bold;cursor:pointer;">🏛️ Modeller (${state.localModels.length})</button>
                    <button data-loc-type="RESOURCES" style="background:${state.localFilterType === "RESOURCES" ? "#38bdf8" : "#13161f"};color:${state.localFilterType === "RESOURCES" ? "#000" : "#cbd5e1"};border:1px solid #38bdf8;border-radius:3px;padding:3px 7px;font-size:9.5px;font-weight:bold;cursor:pointer;">🧬 Resursfiler: VAE/CLIP/VLM (${state.localResources.length})</button>
                    <button data-loc-type="DUPLICATES" style="background:${state.localFilterType === "DUPLICATES" ? "#ef4444" : "#13161f"};color:${state.localFilterType === "DUPLICATES" ? "#fff" : (dupItems.length ? "#fca5a5" : "#cbd5e1")};border:1px solid ${dupItems.length ? "#ef4444" : "#334155"};border-radius:3px;padding:3px 7px;font-size:9.5px;font-weight:bold;cursor:pointer;">⚖️ Dubbletter (${dupItems.length})</button>
                  </div>
                  <div style="display:flex;gap:3px;">
                    <button data-loc-mod="ALL" style="background:${state.localFilterMod === "ALL" ? "#38bdf8" : "#13161f"};color:${state.localFilterMod === "ALL" ? "#000" : "#cbd5e1"};border:1px solid #334155;border-radius:3px;padding:3px 6px;font-size:9px;font-weight:bold;cursor:pointer;">ALLA</button>
                    <button data-loc-mod="IMAGE" style="background:${state.localFilterMod === "IMAGE" ? "#fbbf24" : "#13161f"};color:${state.localFilterMod === "IMAGE" ? "#000" : "#cbd5e1"};border:1px solid #334155;border-radius:3px;padding:3px 6px;font-size:9px;font-weight:bold;cursor:pointer;">🖼️ IMAGE</button>
                    <button data-loc-mod="VIDEO" style="background:${state.localFilterMod === "VIDEO" ? "#34d399" : "#13161f"};color:${state.localFilterMod === "VIDEO" ? "#000" : "#cbd5e1"};border:1px solid #334155;border-radius:3px;padding:3px 6px;font-size:9px;font-weight:bold;cursor:pointer;">🎬 VIDEO</button>
                  </div>
                </div>
                ${state.localFilterType === "DUPLICATES" && dupSum.total_duplicate_files > 0 ? `
                  <div style="background:#1c1917;border:1px solid #f59e0b;border-radius:4px;padding:4px 7px;font-size:8.5px;color:#fde68a;display:flex;justify-content:space-between;align-items:center;flex-shrink:0;">
                    <span>🧬 <b>${dupSum.total_groups} dubblettgrupper</b> hittade (${dupSum.total_duplicate_files} överflödiga filer = <b>${dupSum.reclaimable_mb} MB</b>). Grön = Rekommenderad att behålla, Röd = Dubblett.</span>
                  </div>
                ` : ""}
                <div style="display:flex;gap:4px;flex-shrink:0;">
                  <input type="text" class="ez-loc-search" value="${state.localQuery.replace(/"/g, "&quot;")}" placeholder="Filtrera installerade modeller, LoRAs, VAE, CLIP, Qwen-VL eller dubbletter..." style="flex:1;background:#11131a;color:#f8fafc;border:1px solid #334155;border-radius:4px;padding:4px 7px;font-size:10px;" />
                  <button class="ez-loc-rescan" style="background:#1e293b;color:#38bdf8;border:1px solid #334155;border-radius:4px;padding:4px 8px;font-size:9.5px;font-weight:bold;cursor:pointer;">🔄 Skanna Disk</button>
                </div>
                <div class="ez-civ-scroll-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(${cols > 2 ? "220px" : "200px"},1fr));align-content:start;gap:6px;flex:1;min-height:180px;overflow-y:auto;padding:3px;">
                  ${cardsHtml}
                </div>
              </div>
            `
        };
    };

    const bindLocalGridCardButtons = (scopeEl, filtered) => {
        if (!scopeEl) return;
        scopeEl.querySelectorAll("[data-loc-idx]").forEach(btn => {
            btn.onclick = () => {
                const idx = parseInt(btn.getAttribute("data-loc-idx"), 10);
                const slot = btn.getAttribute("data-slot");
                const forceMod = btn.getAttribute("data-force-mod");
                const item = filtered[idx];
                if (item && slot) {
                    const effMod = forceMod || (slot.startsWith("video_") ? "VIDEO" : "IMAGE");
                    assignAssetToSlot(slot, item.name, effMod, [], "", item.optimal_settings || null);
                    state.stackModality = effMod;
                    const arch = getWidgetVal(effMod === "VIDEO" ? "video_architecture" : "image_architecture", effMod === "VIDEO" ? "MiniMax H3" : "KREA2");
                    fetchArchitectureCompanions(arch, effMod, "resolve");
                }
            };
        });
        scopeEl.querySelectorAll("[data-loc-res-idx]").forEach(btn => {
            btn.onclick = () => {
                const idx = parseInt(btn.getAttribute("data-loc-res-idx"), 10);
                const role = btn.getAttribute("data-res-role");
                const mod = btn.getAttribute("data-res-mod") || "IMAGE";
                const item = filtered[idx];
                if (item && role) {
                    const ok = syncResourceToDownstreamGraphNodes(role, item.name, mod);
                    state.statusMsg = ok
                        ? `✅ Kopplade ${shortLabel(item.name)} -> ${role} i ${mod === "VLM" ? "[02]" : (mod === "VIDEO" ? "[05]" : "[03]")}!`
                        : `ℹ️ Valde ${shortLabel(item.name)} (${role}).`;
                    syncAllViews();
                }
            };
        });
        scopeEl.querySelectorAll("[data-loc-del-ask]").forEach(btn => {
            btn.onclick = () => {
                const idx = parseInt(btn.getAttribute("data-loc-del-ask"), 10);
                const item = filtered[idx];
                if (item) {
                    const cat = item.category || (item.asset_type === "LORA" ? "loras" : "diffusion_models");
                    state.pendingDeleteKey = `${cat}:${item.name}`;
                    syncAllViews();
                }
            };
        });
        scopeEl.querySelectorAll("[data-loc-del-cancel]").forEach(btn => {
            btn.onclick = () => {
                state.pendingDeleteKey = "";
                syncAllViews();
            };
        });
        scopeEl.querySelectorAll("[data-loc-del-confirm]").forEach(btn => {
            btn.onclick = () => {
                const idx = parseInt(btn.getAttribute("data-loc-del-confirm"), 10);
                const item = filtered[idx];
                if (item) {
                    const cat = item.category || (item.asset_type === "LORA" ? "loras" : "diffusion_models");
                    deleteLocalAsset(cat, item.name);
                }
            };
        });
    };

    const bindLocalBankEvents = (container, filtered) => {
        container.querySelectorAll("[data-loc-type]").forEach(b => {
            b.onclick = () => {
                state.localFilterType = b.getAttribute("data-loc-type");
                state.pendingDeleteKey = "";
                syncAllViews();
            };
        });
        container.querySelectorAll("[data-loc-mod]").forEach(b => {
            b.onclick = () => {
                state.localFilterMod = b.getAttribute("data-loc-mod");
                state.pendingDeleteKey = "";
                syncAllViews();
            };
        });
        const sIn = container.querySelector(".ez-loc-search");
        if (sIn) {
            sIn.oninput = () => {
                state.localQuery = sIn.value || "";
                const inlineGrid = wrap && wrap.querySelector(".ez-inline-body .ez-civ-scroll-grid");
                if (inlineGrid && state.activeTab === "local") {
                    const bObj = buildLocalBankHtml(2);
                    inlineGrid.innerHTML = bObj.cardsHtml;
                    bindLocalGridCardButtons(inlineGrid, bObj.filtered);
                }
                const modalGrid = modalOverlay && modalOverlay.querySelector(".ez-modal-left .ez-civ-scroll-grid");
                if (modalGrid && (state.activeTab === "local" || state.activeTab === "stack")) {
                    const mObj = buildLocalBankHtml(3);
                    modalGrid.innerHTML = mObj.cardsHtml;
                    bindLocalGridCardButtons(modalGrid, mObj.filtered);
                }
                const otherRoot = container.classList.contains("ez-modal-left") ? wrap : modalOverlay;
                const otherInput = otherRoot ? otherRoot.querySelector(".ez-loc-search") : null;
                if (otherInput && otherInput !== sIn) {
                    otherInput.value = state.localQuery;
                }
            };
        }
        const rescanBtn = container.querySelector(".ez-loc-rescan");
        if (rescanBtn) rescanBtn.onclick = () => fetchLocalCatalog();
        bindLocalGridCardButtons(container, filtered);
    };

    const buildCivitaiWebHtml = (cols = 2) => {
        const isVid = state.civModality === "VIDEO";
        const archList = isVid
            ? ["All", "MiniMax H3", "Wan Video", "LTXV", "Hunyuan Video"]
            : ["All", "KREA2", "Flux.1 D", "Illustrious", "Pony", "SDXL 1.0", "Qwen-Image"];
        const archBtns = archList.map(a =>
            `<button data-civ-arch="${a}" style="background:${state.civArch === a ? "#eab308" : "#13161f"};color:${state.civArch === a ? "#000" : "#94a3b8"};border:1px solid #334155;border-radius:3px;padding:2px 6px;font-size:8.5px;font-weight:bold;cursor:pointer;">${a}</button>`
        ).join("");
        const sortList = [
            { id: "Most Downloaded", lbl: "🔥 Most Downloaded" },
            { id: "Highest Rated", lbl: "⭐ Highest Rated" },
            { id: "Newest", lbl: "🆕 Newest" }
        ];
        const sortBtns = sortList.map(s =>
            `<button data-civ-sort="${s.id}" style="background:${state.civSort === s.id ? "#38bdf8" : "#13161f"};color:${state.civSort === s.id ? "#000" : "#94a3b8"};border:1px solid #334155;border-radius:3px;padding:2px 6px;font-size:8.5px;font-weight:bold;cursor:pointer;">${s.lbl}</button>`
        ).join("");
        const domList = [
            { id: "civitai.com", lbl: "💙 .com" },
            { id: "civitai.red", lbl: "❤️ .red (Pro)" },
            { id: "both", lbl: "⚡ Both" }
        ];
        const domBtns = domList.map(d =>
            `<button data-civ-dom="${d.id}" style="background:${state.civDomain === d.id ? "#a855f7" : "#13161f"};color:${state.civDomain === d.id ? "#fff" : "#94a3b8"};border:1px solid #334155;border-radius:3px;padding:2px 6px;font-size:8.5px;font-weight:bold;cursor:pointer;">${d.lbl}</button>`
        ).join("");

        const buildInspectedCivitaiModalHtml = () => {
            const insp = state.civInspectedItem;
            if (!insp) return "";
            const sel = resolveSelectedVersionAndFile(insp);
            if (!sel) return "";
            const itemIsVid = insp.modality === "VIDEO";
            const modColor = itemIsVid ? "#34d399" : "#fbbf24";
            const authorName = insp.author || insp.creator || "Unknown Creator";
            const verBtns = sel.versions.map((v, vIdx) => {
                const act = vIdx === sel.verIdx;
                const fCnt = Array.isArray(v.files) ? v.files.length : 1;
                return `<button data-civ-insp-ver="${vIdx}" style="background:${act ? modColor : "#13161f"};color:${act ? "#000" : "#e2e8f0"};border:1px solid ${act ? modColor : "#334155"};border-radius:4px;padding:3px 8px;font-size:8.5px;font-weight:bold;cursor:pointer;">📦 ${v.version_name} (${v.base_model || insp.base_model} · ${fCnt} fil${fCnt > 1 ? "er" : ""})</button>`;
            }).join("");
            const filesRows = sel.files.map((f, fIdx) => {
                const isSel = fIdx === sel.fileIdx;
                const fpBadge = f.fp && f.fp !== "Auto" ? `<span style="background:#0284c7;color:#fff;padding:1px 4px;border-radius:2px;font-size:7.5px;font-weight:bold;">${f.fp}</span>` : "";
                const szVarBadge = f.size_variant && f.size_variant !== "standard" ? `<span style="background:#475569;color:#e2e8f0;padding:1px 4px;border-radius:2px;font-size:7.5px;">${f.size_variant}</span>` : "";
                const fmtBadge = `<span style="background:#1e293b;color:#38bdf8;padding:1px 4px;border-radius:2px;font-size:7.5px;">${f.format || "SafeTensor"}</span>`;
                return `
                  <div style="display:flex;justify-content:space-between;align-items:center;background:${isSel ? "#172033" : "#11131a"};border:1px solid ${isSel ? modColor : "#262b38"};border-radius:4px;padding:4px 7px;gap:6px;flex-wrap:wrap;">
                    <div style="display:flex;align-items:center;gap:5px;min-width:0;flex:1;">
                      <span style="font-size:8.5px;font-weight:bold;color:#f8fafc;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${f.name}">${f.primary ? "⭐ " : ""}${f.name}</span>
                      ${fpBadge} ${szVarBadge} ${fmtBadge}
                      <span style="font-size:8.5px;color:#facc15;font-weight:bold;">${f.size_label || `${f.size_mb} MB`}</span>
                    </div>
                    <div style="display:flex;gap:4px;flex-shrink:0;">
                      <button data-civ-insp-dl-file="${fIdx}" style="background:#0284c7;color:#fff;border:none;border-radius:3px;padding:2px 7px;font-size:8px;font-weight:bold;cursor:pointer;">⬇️ Ladda ner (${f.size_label || "Fil"})</button>
                      <button data-civ-insp-eq-file="${fIdx}" style="background:${modColor};color:#000;border:none;border-radius:3px;padding:2px 7px;font-size:8px;font-weight:bold;cursor:pointer;">📤 Ladda ner & Utrusta</button>
                    </div>
                  </div>
                `;
            }).join("");
            const trigStr = (sel.trigger_words || []).join(", ");
            const descStr = String(sel.ver.description_text || insp.description_text || "Ingen beskrivning angiven av skaparen.").slice(0, 700);
            const tagsStr = Array.isArray(insp.tags) && insp.tags.length ? insp.tags.slice(0, 10).map(t => `<span style="background:#1e293b;color:#94a3b8;padding:1px 5px;border-radius:3px;font-size:7.5px;">#${t}</span>`).join(" ") : "";
            return `
              <div style="background:#0d1322;border:1.5px solid ${modColor};border-radius:6px;padding:8px;display:flex;flex-direction:column;gap:6px;flex-shrink:0;box-shadow:0 6px 20px rgba(0,0,0,0.6);">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;flex-wrap:wrap;">
                  <div style="display:flex;flex-direction:column;gap:2px;">
                    <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                      <span style="font-size:10.5px;font-weight:bold;color:#f8fafc;">🔍 ${insp.name}</span>
                      <span style="font-size:8.5px;background:#1e293b;color:#38bdf8;padding:1px 6px;border-radius:3px;font-weight:bold;">👤 Skapare / Author: ${authorName}</span>
                      <span style="font-size:8px;background:#1e293b;color:${modColor};padding:1px 6px;border-radius:3px;font-weight:bold;">${insp.type} · ${sel.base_model}</span>
                      <span style="font-size:8px;color:#94a3b8;">ID #${insp.id} · 📅 ${sel.ver.created_at || insp.updated_at || ""} · ⬇ ${insp.downloads || 0} · ★ ${Number(insp.rating || 0).toFixed(1)} · ❤️ ${insp.thumbs_up || insp.favorites || 0}</span>
                    </div>
                    ${tagsStr ? `<div style="display:flex;gap:3px;flex-wrap:wrap;margin-top:2px;">${tagsStr}</div>` : ""}
                  </div>
                  <button class="ez-civ-close-inspect" style="background:#dc2626;color:#fff;border:none;border-radius:4px;padding:2px 8px;font-size:8.5px;font-weight:bold;cursor:pointer;">✕ Stäng Detaljvy</button>
                </div>
                <div style="display:flex;flex-direction:column;gap:3px;">
                  <span style="font-size:8.5px;color:#cbd5e1;font-weight:bold;">📚 Välj Modellversion (${sel.versions.length} tillgängliga):</span>
                  <div style="display:flex;gap:4px;flex-wrap:wrap;">${verBtns}</div>
                </div>
                <div style="display:flex;flex-direction:column;gap:3px;">
                  <span style="font-size:8.5px;color:#facc15;font-weight:bold;">💾 Filer, Kvantisering (FP8/FP16/BF16/GGUF) & Storlekar i version "${sel.version_name}":</span>
                  <div style="display:flex;flex-direction:column;gap:3px;max-height:130px;overflow-y:auto;">${filesRows}</div>
                </div>
                ${trigStr ? `<div style="font-size:8.5px;color:#a7f3d0;background:#064e3b;border:1px solid #059669;border-radius:4px;padding:3px 6px;">🔑 <b>Trigger-ord:</b> ${trigStr}</div>` : ""}
                ${sel.optimal_settings ? `
                  <div style="font-size:8px;color:#fde68a;background:#09111e;border:1px solid #0284c7;border-radius:4px;padding:4px 6px;display:flex;flex-direction:column;gap:2px;">
                    <div><b>⚡ Optimala Inställningar (Author & System-Tier):</b> ${sel.optimal_settings.summary_badge || ""}</div>
                    ${sel.optimal_settings.author_summary_line ? `<div style="color:#e2e8f0;">${sel.optimal_settings.author_summary_line}</div>` : ""}
                    ${sel.optimal_settings.quant_tech_note ? `<div style="color:#34d399;">${sel.optimal_settings.quant_tech_note}</div>` : ""}
                  </div>
                ` : ""}
                <div style="font-size:8.5px;color:#cbd5e1;background:#090a0f;border:1px solid #1e293b;border-radius:4px;padding:5px 7px;max-height:85px;overflow-y:auto;white-space:pre-wrap;line-height:1.35;">${descStr.replace(/</g, "&lt;")}</div>
              </div>
            `;
        };

        const cardsHtml = state.civItems.length
            ? state.civItems.map((item, idx) => {
                const sel = resolveSelectedVersionAndFile(item);
                const sample = (Array.isArray(sel.samples) && sel.samples[0]) || (Array.isArray(item.samples) && item.samples[0]) || null;
                const cThumb = sample ? (sample.cached_thumb || sample.cached_file || "") : "";
                const thumbUrl = cThumb
                    ? api.apiURL(`/ez_cinematrix/civitai/thumb?file=${encodeURIComponent(cThumb)}`)
                    : (sample ? sample.url : "");
                const isVidSample = sample && (sample.is_video || sample.media_type === "video");
                const mediaHtml = thumbUrl
                    ? (isVidSample
                        ? `<video src="${thumbUrl}" autoplay loop muted playsinline style="width:100%;aspect-ratio:16/10;min-height:135px;object-fit:cover;background:#000;border-radius:3px;"></video>`
                        : `<img src="${thumbUrl}" style="width:100%;aspect-ratio:16/10;min-height:135px;object-fit:cover;background:#000;border-radius:3px;" />`)
                    : `<div style="width:100%;aspect-ratio:16/10;min-height:135px;background:#090a0f;display:flex;align-items:center;justify-content:center;color:#64748b;font-size:10px;">No Preview</div>`;
                const itemIsVid = item.modality === "VIDEO";
                const modColor = itemIsVid ? "#34d399" : "#fbbf24";
                const opt = sel.optimal_settings || item.optimal_settings || {};
                const optBadge = opt.summary_badge || "";
                const authorName = item.author || item.creator || "Unknown Creator";
                const verCount = Array.isArray(item.versions) ? item.versions.length : (item.version_count || 1);
                const verOptionsHtml = sel.versions.map((v, vIdx) =>
                    `<option value="${vIdx}" ${vIdx === sel.verIdx ? "selected" : ""}>v: ${v.version_name} (${v.base_model || item.base_model})</option>`
                ).join("");
                const fileOptionsHtml = sel.files.map((f, fIdx) =>
                    `<option value="${fIdx}" ${fIdx === sel.fileIdx ? "selected" : ""}>${f.fp && f.fp !== "Auto" ? `[${f.fp}] ` : ""}${f.size_label || `${f.size_mb}MB`} — ${f.name}</option>`
                ).join("");
                const isLoraCard = String(item.type || state.civType).toUpperCase() === "LORA";
                const cardTrueRole = isLoraCard ? "LORA" : (item.resource_role || detectFrontendAssetTrueRole(`${sel.filename} ${item.name}`, item.type));
                const sendSlotsHtml = isLoraCard
                    ? (itemIsVid
                        ? `<button data-civ-send="${idx}" data-slot="video_lora_1" style="background:#065f46;color:#fff;border:none;border-radius:2px;padding:2px 4px;font-size:8px;cursor:pointer;font-weight:bold;" title="Send to Video LoRA 1 on [10] & [05]">📤+V1</button>
                           <button data-civ-send="${idx}" data-slot="video_lora_2" style="background:#065f46;color:#fff;border:none;border-radius:2px;padding:2px 4px;font-size:8px;cursor:pointer;font-weight:bold;" title="Send to Video LoRA 2 on [10] & [05]">+V2</button>
                           <button data-civ-send="${idx}" data-slot="video_lora_3" style="background:#065f46;color:#fff;border:none;border-radius:2px;padding:2px 4px;font-size:8px;cursor:pointer;font-weight:bold;" title="Send to Video LoRA 3 on [10] & [05]">+V3</button>
                           <button data-civ-send="${idx}" data-slot="video_lora_4" style="background:#065f46;color:#fff;border:none;border-radius:2px;padding:2px 4px;font-size:8px;cursor:pointer;font-weight:bold;" title="Send to Video LoRA 4 on [10] & [05]">+V4</button>
                           <button data-civ-send="${idx}" data-slot="video_turbo_lora" style="background:#047857;color:#a7f3d0;border:none;border-radius:2px;padding:2px 4px;font-size:8px;cursor:pointer;font-weight:bold;" title="Send to Video Turbo LoRA on [10] & [05]">⚡T</button>`
                        : `<button data-civ-send="${idx}" data-slot="image_style_lora_1" style="background:#92400e;color:#fff;border:none;border-radius:2px;padding:2px 4px;font-size:8px;cursor:pointer;font-weight:bold;" title="Send to Image Style LoRA 1 on [10] & [03]">📤+B1</button>
                           <button data-civ-send="${idx}" data-slot="image_style_lora_2" style="background:#92400e;color:#fff;border:none;border-radius:2px;padding:2px 4px;font-size:8px;cursor:pointer;font-weight:bold;" title="Send to Image Style LoRA 2 on [10] & [03]">+B2</button>
                           <button data-civ-send="${idx}" data-slot="image_style_lora_3" style="background:#92400e;color:#fff;border:none;border-radius:2px;padding:2px 4px;font-size:8px;cursor:pointer;font-weight:bold;" title="Send to Image Style LoRA 3 on [10] & [03]">+B3</button>
                           <button data-civ-send="${idx}" data-slot="image_style_lora_4" style="background:#92400e;color:#fff;border:none;border-radius:2px;padding:2px 4px;font-size:8px;cursor:pointer;font-weight:bold;" title="Send to Image Style LoRA 4 on [10] & [03]">+B4</button>
                           <button data-civ-send="${idx}" data-slot="image_turbo_lora" style="background:#b45309;color:#fde68a;border:none;border-radius:2px;padding:2px 4px;font-size:8px;cursor:pointer;font-weight:bold;" title="Send to Image Turbo LoRA on [10] & [03]">⚡T</button>`)
                    : (cardTrueRole === "VLM" || cardTrueRole === "MMPROJ"
                        ? `<button data-civ-send="${idx}" data-slot="image_unet_name" style="flex:1;background:#a855f7;color:#fff;border:none;border-radius:2px;padding:2px 5px;font-size:8px;cursor:pointer;font-weight:bold;" title="Send Qwen-VL directly to [02] Timeline Compiler">🧠 Send to Qwen3-VL [02]</button>`
                        : (cardTrueRole === "CLIP"
                            ? `<button data-civ-send="${idx}" data-slot="${itemIsVid ? "video_unet_fl2va" : "image_unet_name"}" style="flex:1;background:#38bdf8;color:#000;border:none;border-radius:2px;padding:2px 5px;font-size:8px;cursor:pointer;font-weight:bold;" title="Send Text Encoder (CLIP) to ${itemIsVid ? "[05]" : "[03]"}">🔤 Send to CLIP ${itemIsVid ? "[05]" : "[03]"}</button>`
                            : `<button data-civ-send="${idx}" data-slot="${itemIsVid ? "video_unet_fl2va" : "image_unet_name"}" style="flex:1;background:${modColor};color:#000;border:none;border-radius:2px;padding:2px 5px;font-size:8px;cursor:pointer;font-weight:bold;" title="Send to Model Slot on [10] & ${itemIsVid ? "[05]" : "[03]"}">📤 Send to ${itemIsVid ? "Video Model [05]" : "Image Model [03]"}</button>`));
                return `
                  <div style="background:#13161f;border:1px solid #262b38;border-radius:5px;padding:5px;display:flex;flex-direction:column;gap:4px;">
                    <div style="position:relative;">
                      ${mediaHtml}
                      <span style="position:absolute;top:3px;left:3px;background:rgba(9,10,15,0.92);color:${modColor};border:1px solid ${modColor};font-size:7.5px;padding:1px 4px;border-radius:2px;font-weight:bold;">${item.modality} // ${sel.base_model}</span>
                      <span style="position:absolute;top:3px;right:3px;background:rgba(9,10,15,0.92);color:#facc15;font-size:7.5px;padding:1px 4px;border-radius:2px;font-weight:bold;">${sel.fp !== "Auto" ? `${sel.fp} · ` : ""}${sel.size_label}</span>
                      <span style="position:absolute;bottom:3px;left:3px;background:rgba(9,10,15,0.92);color:#38bdf8;font-size:7.5px;padding:1px 5px;border-radius:2px;font-weight:bold;">👤 ${authorName}</span>
                      <span style="position:absolute;bottom:3px;right:3px;background:rgba(9,10,15,0.92);color:#cbd5e1;font-size:7.5px;padding:1px 4px;border-radius:2px;">${verCount} ver</span>
                    </div>
                    <div style="font-size:9.5px;font-weight:bold;color:#f8fafc;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="${item.name} (by ${authorName})">${item.name}</div>
                    <div style="display:flex;justify-content:space-between;align-items:center;font-size:8px;color:#94a3b8;">
                      <span style="color:#38bdf8;font-weight:bold;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:58%;" title="Author: ${authorName}">👤 ${authorName}</span>
                      <span>⬇ ${item.downloads || 0} · ★ ${Number(item.rating || 0).toFixed(1)}</span>
                    </div>
                    <div style="display:flex;flex-direction:column;gap:2px;background:#0b0d14;border:1px solid #1e293b;border-radius:4px;padding:3px;">
                      <select data-civ-ver-sel="${idx}" title="Välj Modellversion" style="width:100%;background:#11131a;color:#e2e8f0;border:1px solid #334155;border-radius:3px;padding:2px 4px;font-size:8px;font-family:monospace;">
                        ${verOptionsHtml}
                      </select>
                      <select data-civ-file-sel="${idx}" title="Välj Fil / Kvantisering (FP8/FP16/GGUF) / Storlek" style="width:100%;background:#11131a;color:#facc15;border:1px solid #334155;border-radius:3px;padding:2px 4px;font-size:8px;font-family:monospace;">
                        ${fileOptionsHtml}
                      </select>
                    </div>
                    ${optBadge ? `<div style="font-size:7.5px;color:#38bdf8;background:#0b111e;border:1px solid #1e293b;border-radius:3px;padding:2px 4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="${optBadge}">${optBadge}</div>` : ""}
                    <div style="display:flex;gap:3px;">
                      <button data-civ-dl="${idx}" style="flex:1;background:#0284c7;color:#fff;border:none;border-radius:3px;padding:3px 4px;font-size:8px;font-weight:bold;cursor:pointer;" title="Ladda ner vald version & fil (${sel.filename})">⬇️ DL (${sel.size_label})</button>
                      <button data-civ-inspect="${idx}" style="background:#1e293b;color:#38bdf8;border:1px solid #38bdf8;border-radius:3px;padding:3px 5px;font-size:8px;font-weight:bold;cursor:pointer;" title="Visa fullständig modellinfo, author, alla versioner och alla filer/kvantiseringar">🔍 Info</button>
                      <button data-civ-equip="${idx}" style="background:#334155;color:#f8fafc;border:1px solid ${modColor};border-radius:3px;padding:3px 5px;font-size:8px;font-weight:bold;cursor:pointer;" title="Ladda ner & skicka till nästa lediga slot på [10] & [03]/[05]">📤 Slot</button>
                    </div>
                    <div style="display:flex;gap:2px;flex-wrap:wrap;">${sendSlotsHtml}</div>
                  </div>
                `;
            }).join("")
            : `<div style="grid-column:1/-1;padding:20px;text-align:center;color:#94a3b8;font-size:10px;">Click <b>🔍 SEARCH</b> to browse Civitai models and LoRAs with version/quantization selector & author metadata.</div>`;

        return `
          <div style="display:flex;flex-direction:column;gap:5px;flex:1;min-height:0;height:100%;">
            <div style="display:flex;gap:3px;flex-wrap:wrap;justify-content:space-between;flex-shrink:0;">
              <div style="display:flex;gap:3px;">
                <button data-civ-mod="IMAGE" style="background:${!isVid ? "#fbbf24" : "#13161f"};color:${!isVid ? "#000" : "#cbd5e1"};border:1px solid #334155;border-radius:3px;padding:3px 7px;font-size:9px;font-weight:bold;cursor:pointer;">🖼️ IMAGE</button>
                <button data-civ-mod="VIDEO" style="background:${isVid ? "#34d399" : "#13161f"};color:${isVid ? "#000" : "#cbd5e1"};border:1px solid #334155;border-radius:3px;padding:3px 7px;font-size:9px;font-weight:bold;cursor:pointer;">🎬 VIDEO</button>
                <button data-civ-type="LORA" style="background:${state.civType === "LORA" ? "#eab308" : "#13161f"};color:${state.civType === "LORA" ? "#000" : "#cbd5e1"};border:1px solid #334155;border-radius:3px;padding:3px 7px;font-size:9px;font-weight:bold;cursor:pointer;">🧩 LoRA</button>
                <button data-civ-type="Checkpoint" style="background:${state.civType === "Checkpoint" ? "#eab308" : "#13161f"};color:${state.civType === "Checkpoint" ? "#000" : "#cbd5e1"};border:1px solid #334155;border-radius:3px;padding:3px 7px;font-size:9px;font-weight:bold;cursor:pointer;">🏛️ Model</button>
              </div>
              <div style="display:flex;gap:3px;">${domBtns}</div>
            </div>
            <div style="display:flex;gap:3px;flex-wrap:wrap;flex-shrink:0;">${archBtns}</div>
            <div style="display:flex;gap:3px;flex-wrap:wrap;justify-content:space-between;flex-shrink:0;">
              <div style="display:flex;gap:3px;">${sortBtns}</div>
              <div style="display:flex;gap:2px;">
                ${["AllTime", "Month", "Week", "Day"].map(p => `<button data-civ-per="${p}" style="background:${state.civPeriod === p ? "#475569" : "#13161f"};color:#e2e8f0;border:1px solid #334155;border-radius:3px;padding:2px 5px;font-size:8px;cursor:pointer;">${p}</button>`).join("")}
              </div>
            </div>
            <div style="display:flex;gap:4px;flex-shrink:0;">
              <input type="text" class="ez-civ-q-in" value="${state.civQuery.replace(/"/g, "&quot;")}" placeholder="Search Civitai models & LoRAs..." style="flex:1;background:#11131a;color:#f8fafc;border:1px solid #334155;border-radius:4px;padding:4px 7px;font-size:10px;" />
              <button class="ez-civ-go" style="background:#eab308;color:#000;border:none;border-radius:4px;padding:4px 9px;font-size:9.5px;font-weight:bold;cursor:pointer;">🔍 SEARCH</button>
              <button class="ez-civ-force" title="Clear 30d cache & refresh" style="background:#10b981;color:#000;border:none;border-radius:4px;padding:4px 7px;font-size:9.5px;font-weight:bold;cursor:pointer;">🔄</button>
            </div>
            ${buildInspectedCivitaiModalHtml()}
            <div class="ez-civ-scroll-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(${cols > 2 ? "235px" : "210px"},1fr));align-content:start;gap:6px;flex:1;min-height:180px;overflow-y:auto;padding:3px;">
              ${cardsHtml}
            </div>
          </div>
        `;
    };

    const bindCivitaiWebEvents = (container) => {
        container.querySelectorAll("[data-civ-mod]").forEach(b => {
            b.onclick = () => {
                state.civModality = b.getAttribute("data-civ-mod");
                state.civArch = state.civModality === "VIDEO" ? "MiniMax H3" : "KREA2";
                runCivitaiSearch(false);
            };
        });
        container.querySelectorAll("[data-civ-type]").forEach(b => {
            b.onclick = () => { state.civType = b.getAttribute("data-civ-type"); runCivitaiSearch(false); };
        });
        container.querySelectorAll("[data-civ-arch]").forEach(b => {
            b.onclick = () => { state.civArch = b.getAttribute("data-civ-arch"); runCivitaiSearch(false); };
        });
        container.querySelectorAll("[data-civ-sort]").forEach(b => {
            b.onclick = () => { state.civSort = b.getAttribute("data-civ-sort"); runCivitaiSearch(false); };
        });
        container.querySelectorAll("[data-civ-per]").forEach(b => {
            b.onclick = () => { state.civPeriod = b.getAttribute("data-civ-per"); runCivitaiSearch(false); };
        });
        container.querySelectorAll("[data-civ-dom]").forEach(b => {
            b.onclick = () => { state.civDomain = b.getAttribute("data-civ-dom"); runCivitaiSearch(false); };
        });
        const qIn = container.querySelector(".ez-civ-q-in");
        if (qIn) {
            qIn.onkeydown = (e) => {
                if (e.key === "Enter") { state.civQuery = qIn.value || ""; runCivitaiSearch(false); }
            };
        }
        const goBtn = container.querySelector(".ez-civ-go");
        if (goBtn) goBtn.onclick = () => { if (qIn) state.civQuery = qIn.value || ""; runCivitaiSearch(false); };
        const forceBtn = container.querySelector(".ez-civ-force");
        if (forceBtn) forceBtn.onclick = () => { if (qIn) state.civQuery = qIn.value || ""; runCivitaiSearch(true); };

        container.querySelectorAll("[data-civ-ver-sel]").forEach(selEl => {
            selEl.onchange = () => {
                const idx = parseInt(selEl.getAttribute("data-civ-ver-sel"), 10);
                const item = state.civItems[idx];
                if (item) {
                    item._selectedVerIdx = parseInt(selEl.value, 10) || 0;
                    if (Array.isArray(item.versions) && item.versions[item._selectedVerIdx]) {
                        item.versions[item._selectedVerIdx]._selectedFileIdx = 0;
                    }
                    syncAllViews();
                }
            };
        });
        container.querySelectorAll("[data-civ-file-sel]").forEach(selEl => {
            selEl.onchange = () => {
                const idx = parseInt(selEl.getAttribute("data-civ-file-sel"), 10);
                const item = state.civItems[idx];
                if (item) {
                    const vIdx = item._selectedVerIdx || 0;
                    if (Array.isArray(item.versions) && item.versions[vIdx]) {
                        item.versions[vIdx]._selectedFileIdx = parseInt(selEl.value, 10) || 0;
                    }
                    syncAllViews();
                }
            };
        });
        container.querySelectorAll("[data-civ-inspect]").forEach(btn => {
            btn.onclick = () => {
                const item = state.civItems[parseInt(btn.getAttribute("data-civ-inspect"), 10)];
                if (item) inspectCivitaiModelDetails(item);
            };
        });
        const closeInspBtn = container.querySelector(".ez-civ-close-inspect");
        if (closeInspBtn) {
            closeInspBtn.onclick = () => {
                state.civInspectedItem = null;
                syncAllViews();
            };
        }
        container.querySelectorAll("[data-civ-insp-ver]").forEach(btn => {
            btn.onclick = () => {
                if (state.civInspectedItem) {
                    state.civInspectedItem._selectedVerIdx = parseInt(btn.getAttribute("data-civ-insp-ver"), 10) || 0;
                    syncAllViews();
                }
            };
        });
        container.querySelectorAll("[data-civ-insp-dl-file]").forEach(btn => {
            btn.onclick = () => {
                if (state.civInspectedItem) {
                    const fIdx = parseInt(btn.getAttribute("data-civ-insp-dl-file"), 10) || 0;
                    const vIdx = state.civInspectedItem._selectedVerIdx || 0;
                    downloadOnlyCivitaiItem(state.civInspectedItem, vIdx, fIdx, false);
                }
            };
        });
        container.querySelectorAll("[data-civ-insp-eq-file]").forEach(btn => {
            btn.onclick = () => {
                if (state.civInspectedItem) {
                    const fIdx = parseInt(btn.getAttribute("data-civ-insp-eq-file"), 10) || 0;
                    const vIdx = state.civInspectedItem._selectedVerIdx || 0;
                    sendCivitaiItemToSlot(state.civInspectedItem, "", vIdx, fIdx);
                }
            };
        });

        container.querySelectorAll("[data-civ-dl]").forEach(btn => {
            btn.onclick = () => {
                const item = state.civItems[parseInt(btn.getAttribute("data-civ-dl"), 10)];
                if (item) downloadOnlyCivitaiItem(item);
            };
        });
        container.querySelectorAll("[data-civ-equip]").forEach(btn => {
            btn.onclick = () => {
                const item = state.civItems[parseInt(btn.getAttribute("data-civ-equip"), 10)];
                if (item) sendCivitaiItemToSlot(item, "");
            };
        });
        container.querySelectorAll("[data-civ-send]").forEach(btn => {
            btn.onclick = () => {
                const item = state.civItems[parseInt(btn.getAttribute("data-civ-send"), 10)];
                const slot = btn.getAttribute("data-slot") || "";
                if (item && slot) sendCivitaiItemToSlot(item, slot);
            };
        });
    };

    const formatEtaString = (sec) => {
        const s = Math.max(0, Math.round(Number(sec) || 0));
        if (s <= 0) return "0s";
        const m = Math.floor(s / 60);
        const rem = s % 60;
        return m > 0 ? `${m}m ${rem}s` : `${rem}s`;
    };

    const buildDownloadsHtml = () => {
        const sum = state.downloadsSummary || {};
        const items = Array.isArray(state.downloadsQueue) ? state.downloadsQueue : [];
        const overallPct = Number(sum.overall_percent || 0).toFixed(1);
        const dlMb = Number(sum.downloaded_mb ?? sum.total_downloaded_mb ?? 0).toFixed(2);
        const totMb = Number(sum.total_mb ?? sum.total_size_mb ?? 0).toFixed(2);
        const spd = Number(sum.total_speed_mbps || 0).toFixed(2);
        const etaStr = formatEtaString(sum.total_eta_sec || 0);
        const totFilesCount = sum.total_files ?? sum.total_count ?? items.length;

        const rowsHtml = items.length
            ? items.map((d, idx) => {
                const pct = Math.min(100, Math.max(0, Number(d.percent || 0)));
                const isDone = d.status === "completed";
                const isCancelled = d.status === "cancelled";
                const isErr = d.status === "error" || d.status === "failed";
                const isDownloading = d.status === "downloading" || d.status === "started";
                const isVid = String(d.modality || "").toUpperCase() === "VIDEO";
                const isLora = String(d.asset_type || "LORA").toUpperCase() === "LORA";
                const barColor = isCancelled ? "#f59e0b" : (isErr ? "#ef4444" : (isDone ? "#10b981" : "#38bdf8"));
                const dlKey = String(d.dl_id || d.id || `dl_${d.filename || idx}`);
                const statusBadge = isCancelled
                    ? `<span style="color:#fbbf24;font-weight:bold;">🛑 AVBRUTEN (.part raderad)</span>`
                    : (isErr
                        ? `<span style="color:#f87171;font-weight:bold;">❌ FAILED</span>`
                        : (isDone
                            ? `<span style="color:#34d399;font-weight:bold;">✅ COMPLETED (100%)</span>`
                            : `<span style="color:#38bdf8;font-weight:bold;">⬇️ DOWNLOADING (${pct.toFixed(1)}%)</span>`));
                const cancelBtn = isDownloading
                    ? `<button data-dl-cancel="${dlKey.replace(/"/g, "&quot;")}" data-dl-fname="${String(d.filename || "").replace(/"/g, "&quot;")}" style="background:#dc2626;color:#fff;border:1px solid #f87171;border-radius:3px;padding:2px 7px;font-size:8px;cursor:pointer;font-weight:bold;" title="Avbryt pågående nedladdning och radera halvfärdig .part-fil från disk">🛑 Avbryt & Radera .part</button>`
                    : "";
                const sendBtns = isDone
                    ? (isLora
                        ? (isVid
                            ? `<button data-dl-send="${idx}" data-slot="video_lora_1" style="background:#065f46;color:#fff;border:none;border-radius:3px;padding:2px 5px;font-size:8px;cursor:pointer;font-weight:bold;">📤+V1</button>
                               <button data-dl-send="${idx}" data-slot="video_lora_2" style="background:#065f46;color:#fff;border:none;border-radius:3px;padding:2px 5px;font-size:8px;cursor:pointer;font-weight:bold;">+V2</button>
                               <button data-dl-send="${idx}" data-slot="video_lora_3" style="background:#065f46;color:#fff;border:none;border-radius:3px;padding:2px 5px;font-size:8px;cursor:pointer;font-weight:bold;">+V3</button>
                               <button data-dl-send="${idx}" data-slot="video_lora_4" style="background:#065f46;color:#fff;border:none;border-radius:3px;padding:2px 5px;font-size:8px;cursor:pointer;font-weight:bold;">+V4</button>
                               <button data-dl-send="${idx}" data-slot="video_turbo_lora" style="background:#047857;color:#a7f3d0;border:none;border-radius:3px;padding:2px 5px;font-size:8px;cursor:pointer;font-weight:bold;">⚡T</button>`
                            : `<button data-dl-send="${idx}" data-slot="image_style_lora_1" style="background:#92400e;color:#fff;border:none;border-radius:3px;padding:2px 5px;font-size:8px;cursor:pointer;font-weight:bold;">📤+B1</button>
                               <button data-dl-send="${idx}" data-slot="image_style_lora_2" style="background:#92400e;color:#fff;border:none;border-radius:3px;padding:2px 5px;font-size:8px;cursor:pointer;font-weight:bold;">+B2</button>
                               <button data-dl-send="${idx}" data-slot="image_style_lora_3" style="background:#92400e;color:#fff;border:none;border-radius:3px;padding:2px 5px;font-size:8px;cursor:pointer;font-weight:bold;">+B3</button>
                               <button data-dl-send="${idx}" data-slot="image_style_lora_4" style="background:#92400e;color:#fff;border:none;border-radius:3px;padding:2px 5px;font-size:8px;cursor:pointer;font-weight:bold;">+B4</button>
                               <button data-dl-send="${idx}" data-slot="image_turbo_lora" style="background:#b45309;color:#fde68a;border:none;border-radius:3px;padding:2px 5px;font-size:8px;cursor:pointer;font-weight:bold;">⚡T</button>`)
                        : `<button data-dl-send="${idx}" data-slot="${isVid ? "video_unet_fl2va" : "image_unet_name"}" style="background:#eab308;color:#000;border:none;border-radius:3px;padding:2px 6px;font-size:8.5px;cursor:pointer;font-weight:bold;">📤 Send to ${isVid ? "[05] Video Model" : "[03] Image Model"}</button>`)
                    : "";
                return `
                  <div style="background:#13161f;border:1px solid ${barColor};border-radius:5px;padding:7px;display:flex;flex-direction:column;gap:5px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;">
                      <span style="font-size:9.5px;font-weight:bold;color:#f8fafc;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="${d.filename}">${d.filename}</span>
                      <div style="display:flex;align-items:center;gap:5px;flex-shrink:0;">
                        ${statusBadge}
                        ${cancelBtn}
                      </div>
                    </div>
                    <div style="width:100%;height:7px;background:#090a0f;border-radius:4px;overflow:hidden;border:1px solid #1e293b;">
                      <div style="width:${pct.toFixed(1)}%;height:100%;background:${barColor};transition:width 0.25s;"></div>
                    </div>
                    <div style="display:flex;justify-content:space-between;align-items:center;font-size:8.5px;color:#cbd5e1;flex-wrap:wrap;gap:4px;">
                      <span>📦 <b>${Number(d.downloaded_mb || 0).toFixed(2)} MB</b> / ${Number(d.total_mb || 0).toFixed(2)} MB (<b>${pct.toFixed(1)}%</b>)</span>
                      <span>⚡ Speed: <b style="color:#facc15;">${Number(d.speed_mbps || 0).toFixed(2)} MB/s</b> | ⏱️ ETA: <b style="color:#38bdf8;">${formatEtaString(d.eta_sec || 0)}</b></span>
                    </div>
                    ${d.error ? `<div style="font-size:8.5px;color:#fca5a5;">${d.error}</div>` : ""}
                    ${sendBtns ? `<div style="display:flex;gap:3px;align-items:center;justify-content:flex-end;">${sendBtns}</div>` : ""}
                  </div>
                `;
            }).join("")
            : `<div style="padding:20px;text-align:center;color:#94a3b8;font-size:10px;">No downloads in queue yet. Click <b>⬇️ DL</b> on any Civitai asset or missing VAE/CLIP to track real-time progress, speed (MB/s), and ETA here.</div>`;

        return `
          <div style="display:flex;flex-direction:column;gap:6px;flex:1;min-height:0;height:100%;">
            <div style="background:#11131a;border:1px solid #38bdf8;border-radius:6px;padding:7px 9px;display:flex;flex-direction:column;gap:4px;flex-shrink:0;">
              <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:4px;">
                <span style="font-size:10px;font-weight:bold;color:#38bdf8;">⬇️ DOWNLOAD MANAGER // QUEUE TELEMETRY</span>
                <div style="display:flex;gap:4px;flex-wrap:wrap;">
                  ${(sum.active_count || 0) > 0 ? `<button class="ez-dl-cancel-all" style="background:#dc2626;color:#fff;border:1px solid #f87171;border-radius:3px;padding:2px 7px;font-size:8.5px;font-weight:bold;cursor:pointer;" title="Avbryt alla pågående nedladdningar och radera alla halvfärdiga .part-filer">🛑 Stop All (${sum.active_count}) & Delete .part</button>` : ""}
                  <button class="ez-dl-refresh" style="background:#1e293b;color:#38bdf8;border:1px solid #334155;border-radius:3px;padding:2px 7px;font-size:8.5px;font-weight:bold;cursor:pointer;">🔄 Refresh</button>
                  <button class="ez-dl-clear" style="background:#334155;color:#e2e8f0;border:none;border-radius:3px;padding:2px 7px;font-size:8.5px;font-weight:bold;cursor:pointer;">🧹 Clear Finished</button>
                </div>
              </div>
              <div style="width:100%;height:8px;background:#090a0f;border-radius:4px;overflow:hidden;border:1px solid #1e293b;">
                <div style="width:${Math.min(100, Number(overallPct))}%;height:100%;background:linear-gradient(90deg,#0284c7,#34d399);transition:width 0.25s;"></div>
              </div>
              <div style="display:flex;justify-content:space-between;font-size:9px;color:#e2e8f0;flex-wrap:wrap;gap:6px;">
                <span>📊 Files: <b>${sum.completed_count || 0}/${totFilesCount}</b> (${sum.active_count || 0} active)</span>
                <span>💾 Total: <b>${dlMb} MB / ${totMb} MB (${overallPct}%)</b></span>
                <span>⚡ Speed: <b style="color:#facc15;">${spd} MB/s</b></span>
                <span>⏱️ Total ETA: <b style="color:#34d399;">${etaStr}</b></span>
              </div>
            </div>
            <div style="display:flex;flex-direction:column;gap:5px;flex:1;min-height:160px;overflow-y:auto;padding-right:2px;">
              ${rowsHtml}
            </div>
          </div>
        `;
    };

    const bindDownloadsEvents = (container) => {
        const refBtn = container.querySelector(".ez-dl-refresh");
        if (refBtn) refBtn.onclick = () => pollDownloadsStatus();
        const clrBtn = container.querySelector(".ez-dl-clear");
        if (clrBtn) {
            clrBtn.onclick = async () => {
                await api.fetchApi("/ez_cinematrix/civitai/downloads_status", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ action: "clear_completed" })
                });
                pollDownloadsStatus();
            };
        }
        const cancelAllBtn = container.querySelector(".ez-dl-cancel-all");
        if (cancelAllBtn) {
            cancelAllBtn.onclick = async () => {
                state.statusMsg = "🛑 Avbryter alla aktiva nedladdningar och raderar .part-filer...";
                syncAllViews();
                await api.fetchApi("/ez_cinematrix/civitai/downloads_status", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ action: "cancel", cancel_all: true })
                });
                await pollDownloadsStatus();
                await fetchLocalCatalog();
                state.statusMsg = "🛑 Alla pågående nedladdningar avbröts och halvfärdiga .part-filer raderades.";
                syncAllViews();
            };
        }
        container.querySelectorAll("[data-dl-cancel]").forEach(btn => {
            btn.onclick = async () => {
                const dlId = btn.getAttribute("data-dl-cancel") || "";
                const fn = btn.getAttribute("data-dl-fname") || "";
                state.statusMsg = `🛑 Avbryter nedladdning av ${fn || dlId} och raderar .part-fil...`;
                syncAllViews();
                await api.fetchApi("/ez_cinematrix/civitai/downloads_status", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ action: "cancel", dl_id: dlId, filename: fn })
                });
                await pollDownloadsStatus();
                await fetchLocalCatalog();
                state.statusMsg = `🛑 Avbröt ${fn || dlId} och raderade halvfärdig .part-fil från disk.`;
                syncAllViews();
            };
        });
        container.querySelectorAll("[data-dl-send]").forEach(btn => {
            btn.onclick = () => {
                const idx = parseInt(btn.getAttribute("data-dl-send"), 10);
                const slot = btn.getAttribute("data-slot");
                const dItem = state.downloadsQueue[idx];
                if (dItem && dItem.filename && slot) {
                    assignAssetToSlot(slot, dItem.filename, dItem.modality || "IMAGE", [], "", null);
                }
            };
        });
    };

    const buildRecipesHtml = (cols = 2) => {
        const cards = state.recipes.length
            ? state.recipes.map((r, idx) => {
                const tUrl = r.thumbnail_url
                    ? (r.thumbnail_url.startsWith("/") ? api.apiURL(r.thumbnail_url) : api.apiURL(`/ez_cinematrix/civitai/thumb?file=${encodeURIComponent(r.thumbnail_url)}`))
                    : "";
                return `
                  <div style="background:#13161f;border:1px solid #334155;border-radius:5px;padding:6px;display:flex;flex-direction:column;gap:4px;">
                    ${tUrl ? `<img src="${tUrl}" style="width:100%;aspect-ratio:16/10;min-height:110px;object-fit:cover;border-radius:3px;background:#000;" />` : ""}
                    <div style="font-size:10px;font-weight:bold;color:#facc15;">${r.name}</div>
                    <div style="font-size:8.5px;color:#94a3b8;">🖼️ ${shortLabel(r.image_unet_name || r.model_name)} | 🎬 ${shortLabel(r.video_unet_fl2va || "None")}</div>
                    <div style="display:flex;gap:3px;">
                      <button data-rec-load="${idx}" style="flex:1;background:#10b981;color:#000;border:none;border-radius:3px;padding:3px;font-size:9px;font-weight:bold;cursor:pointer;">⚡ Load Recipe</button>
                      <button data-rec-del="${r.id}" style="background:#7f1d1d;color:#fecaca;border:none;border-radius:3px;padding:3px 6px;font-size:9px;cursor:pointer;">🗑️</button>
                    </div>
                  </div>
                `;
            }).join("")
            : `<div style="grid-column:1/-1;padding:16px;text-align:center;color:#94a3b8;font-size:10px;">No saved Recipes yet. Configure your rig and click <b>💾 Save Rig</b>!</div>`;

        return `
          <div style="display:flex;flex-direction:column;gap:6px;flex:1;min-height:0;height:100%;">
            <div style="display:flex;gap:4px;flex-shrink:0;">
              <input type="text" class="ez-rec-new-name" placeholder="Name current Image+Video Rig..." style="flex:1;background:#11131a;color:#f8fafc;border:1px solid #334155;border-radius:4px;padding:4px 7px;font-size:10px;" />
              <button class="ez-rec-save-now" style="background:#a855f7;color:#fff;border:none;border-radius:4px;padding:4px 9px;font-size:9.5px;font-weight:bold;cursor:pointer;">💾 Save Rig</button>
            </div>
            <div class="ez-civ-scroll-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(${cols > 2 ? "220px" : "200px"},1fr));align-content:start;gap:6px;flex:1;min-height:180px;overflow-y:auto;">
              ${cards}
            </div>
          </div>
        `;
    };

    const bindRecipesEvents = (container) => {
        const nameIn = container.querySelector(".ez-rec-new-name");
        const saveBtn = container.querySelector(".ez-rec-save-now");
        if (saveBtn) saveBtn.onclick = () => saveCurrentRecipe(nameIn ? nameIn.value : "");
        container.querySelectorAll("[data-rec-load]").forEach(btn => {
            btn.onclick = () => applySavedRecipe(state.recipes[parseInt(btn.getAttribute("data-rec-load"), 10)]);
        });
        container.querySelectorAll("[data-rec-del]").forEach(btn => {
            btn.onclick = async () => {
                const id = btn.getAttribute("data-rec-del");
                await api.fetchApi("/ez_cinematrix/civitai/recipes", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ action: "delete", id })
                });
                fetchStatusAndRecipes();
            };
        });
    };

    const assignVlmToTimelineCompiler = (vlmValue) => {
        if (!vlmValue || !app || !app.graph || !Array.isArray(app.graph._nodes)) return false;
        const cleanVal = String(vlmValue).replace(/\//g, "\\");
        let applied = false;
        for (const gn of app.graph._nodes) {
            if (!gn || detectEzNodeEdition(gn) !== detectEzNodeEdition(node)) continue;
            const ct = stripEzEditionSuffix(String(gn && (gn.comfyClass || gn.type || "")));
            if ((ct === "EZCinematrixQwen3VLTimelineCompiler" || ct === "EZCinematrixQwenVLTimelineCompiler" || ct.includes("02_Cinematrix")) && Array.isArray(gn.widgets)) {
                const wVlm = gn.widgets.find(w => w && w.name === "vlm_model_name");
                if (wVlm) {
                    if (wVlm.options && Array.isArray(wVlm.options.values) && !wVlm.options.values.includes(cleanVal)) {
                        wVlm.options.values.push(cleanVal);
                    }
                    wVlm.value = cleanVal;
                    if (typeof wVlm.callback === "function") {
                        try { wVlm.callback(cleanVal); } catch (e) {}
                    }
                    gn.properties = gn.properties || {};
                    gn.properties._ez_widget_map = gn.properties._ez_widget_map || {};
                    gn.properties._ez_widget_map.vlm_model_name = cleanVal;
                    applied = true;
                }
            }
        }
        if (applied && app.graph) app.graph.setDirtyCanvas(true, true);
        return applied;
    };

    const runHuggingFaceSearch = async () => {
        state.statusMsg = "⏳ Searching HuggingFace Hub models & GGUFs...";
        syncAllViews();
        try {
            const r = await api.fetchApi("/ez_cinematrix/civitai/hf_search", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    action: "search",
                    query: state.hfQuery,
                    category: state.hfCategory,
                    limit: 16
                })
            });
            const d = await r.json();
            if (d) {
                state.hfItems = Array.isArray(d.items) ? d.items : [];
                if (Array.isArray(d.curated)) state.hfCurated = d.curated;
                state.statusMsg = d.notice || `🤗 Found ${state.hfItems.length} HuggingFace repositories.`;
            }
        } catch (e) {
            state.statusMsg = `HuggingFace search error: ${String(e)}`;
        }
        syncAllViews();
    };

    const inspectHuggingFaceRepo = async (repoId, recTarget = "") => {
        if (!repoId) return;
        state.hfInspectedRepo = repoId;
        state.hfInspectedFiles = [];
        if (recTarget) state.hfTargetFolder = recTarget;
        state.statusMsg = `🔍 Inspecting files in ${repoId}...`;
        syncAllViews();
        try {
            const r = await api.fetchApi("/ez_cinematrix/civitai/hf_search", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: "inspect", repo_id: repoId })
            });
            const d = await r.json();
            if (d && d.status === "ok") {
                state.hfInspectedRepo = d.repo_id || repoId;
                state.hfInspectedFiles = Array.isArray(d.files) ? d.files : [];
                state.statusMsg = `📂 Found ${state.hfInspectedFiles.length} downloadable weight options in ${state.hfInspectedRepo}.`;
            } else {
                state.statusMsg = `⚠️ ${(d && d.message) || "Could not inspect repository."}`;
            }
        } catch (e) {
            state.statusMsg = `⚠️ Inspect error: ${String(e)}`;
        }
        syncAllViews();
    };

    const triggerHuggingFaceDownload = async (repoId, filename, targetFolder, autoAssignVlm = true) => {
        const tf = targetFolder || state.hfTargetFolder || "LLM/Qwen-VL";
        state.statusMsg = `⬇️ Downloading from HuggingFace (${repoId}) -> models/${tf}...`;
        ensureDownloadPolling(true);
        syncAllViews();
        try {
            const r = await api.fetchApi("/ez_cinematrix/civitai/hf_download", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    repo_id: repoId,
                    filename: filename || "__FULL_HF_REPO__",
                    target_folder: tf,
                    include_mmproj: true
                })
            });
            const d = await r.json();
            await pollDownloadsStatus();
            if (d && d.status === "ok") {
                await fetchLocalCatalog();
                if (autoAssignVlm && d.vlm_dropdown_value && tf.startsWith("LLM")) {
                    const sent = assignVlmToTimelineCompiler(d.vlm_dropdown_value);
                    state.statusMsg = `✅ Downloaded ${d.filename} (${d.size_mb} MB)${sent ? ` & set [02] vlm_model_name = ${d.vlm_dropdown_value}` : ""}!`;
                } else {
                    state.statusMsg = `✅ Downloaded ${d.filename} (${d.size_mb} MB) to models/${tf}!`;
                }
            } else {
                state.statusMsg = `⚠️ ${(d && d.message) || "HuggingFace download failed."}`;
            }
        } catch (e) {
            state.statusMsg = `⚠️ HuggingFace download error: ${String(e)}`;
        }
        syncAllViews();
    };

    const buildHuggingFaceHtml = (cols = 2) => {
        const curList = (Array.isArray(state.hfCurated) && state.hfCurated.length) ? state.hfCurated : [
            {
                repo_id: "huihui-ai/Huihui-Qwen3-VL-4B-Instruct-abliterated",
                title: "Huihui Qwen3-VL 4B Instruct Abliterated (Native Safetensors Repo)",
                category: "VLM_REPO",
                target_folder: "LLM/Qwen-VL",
                recommended_file: "__FULL_HF_REPO__",
                size_gb: 8.4,
                note: "Fastest native BF16/SDPA Safetensors Vision-Language Compiler for 16 GB GPUs (zero GGUF dequantization overhead)."
            },
            {
                repo_id: "huihui-ai/Huihui-Qwen3-VL-8B-Instruct-abliterated",
                title: "Huihui Qwen3-VL 8B Instruct Abliterated (Native Safetensors + EZ Q8 Cache)",
                category: "VLM_REPO",
                target_folder: "LLM/Qwen-VL",
                recommended_file: "__FULL_HF_REPO__",
                size_gb: 16.5,
                note: "Full 8B Safetensors Vision-Language Repo (auto-caches persistent Q8 Safetensors + SDPA on 16 GB VRAM)."
            },
            {
                repo_id: "mradermacher/Huihui-Qwen3-VL-8B-Instruct-abliterated-GGUF",
                title: "Huihui Qwen3-VL 8B Instruct Abliterated (Q8_0 GGUF Legacy Fallback)",
                category: "VLM_GGUF",
                target_folder: "LLM/Qwen-VL",
                recommended_file: "Huihui-Qwen3-VL-8B-Instruct-abliterated.Q8_0.gguf",
                size_gb: 8.7,
                note: "Legacy GGUF Q8_0 fallback with mmproj vision projector."
            },
            {
                repo_id: "Mungert/Qwen3-VL-8B-Instruct-Unredacted-MAX-GGUF",
                title: "Qwen3-VL 8B Instruct Unredacted MAX (Q8_0 GGUF Legacy Fallback)",
                category: "VLM_GGUF",
                target_folder: "LLM/GGUF",
                recommended_file: "Qwen3-VL-8B-Instruct-Unredacted-MAX-q8_0.gguf",
                size_gb: 8.7,
                note: "Uncensored Q8_0 GGUF fallback for [02] Timeline Compiler."
            }
        ];
        const targetFolders = [
            { id: "LLM/Qwen-VL", lbl: "🧠 models/LLM/Qwen-VL ([02] VLM)" },
            { id: "LLM/GGUF", lbl: "📦 models/LLM/GGUF ([02] Q8 GGUF)" },
            { id: "text_encoders", lbl: "🔤 models/text_encoders (CLIP/T5)" },
            { id: "diffusion_models", lbl: "🏛️ models/diffusion_models (UNet)" },
            { id: "loras", lbl: "🧩 models/loras (LoRA)" },
            { id: "vae", lbl: "🎨 models/vae (VAE)" }
        ];
        const folderOpts = targetFolders.map(f =>
            `<option value="${f.id}" ${state.hfTargetFolder === f.id ? "selected" : ""}>${f.lbl}</option>`
        ).join("");
        const catBtns = [
            { id: "ALL", lbl: "🌟 Alla" },
            { id: "VLM_GGUF", lbl: "⚡ Q8 / GGUF ([02])" },
            { id: "VLM_REPO", lbl: "📁 Full VLM Repo ([02])" }
        ].map(c =>
            `<button data-hf-cat="${c.id}" style="background:${state.hfCategory === c.id ? "#eab308" : "#13161f"};color:${state.hfCategory === c.id ? "#000" : "#cbd5e1"};border:1px solid #334155;border-radius:3px;padding:3px 7px;font-size:8.5px;font-weight:bold;cursor:pointer;">${c.lbl}</button>`
        ).join("");

        const curatedHtml = curList.map((c, idx) => `
          <div style="background:#111522;border:1px solid #38bdf8;border-radius:5px;padding:6px;display:flex;flex-direction:column;gap:4px;">
            <div style="display:flex;justify-content:space-between;align-items:center;gap:4px;">
              <span style="font-size:9px;font-weight:bold;color:#38bdf8;">⭐ RECOMMENDED FOR [02] (${c.size_gb} GB)</span>
              <span style="font-size:8px;background:#090a0f;color:#facc15;padding:1px 5px;border-radius:3px;">${c.target_folder}</span>
            </div>
            <div style="font-size:9.5px;font-weight:bold;color:#f8fafc;" title="${c.repo_id}">${c.title}</div>
            <div style="font-size:8px;color:#94a3b8;line-height:1.25;">${c.note}</div>
            <div style="display:flex;gap:4px;margin-top:2px;">
              <button data-hf-cur-dl="${idx}" style="flex:1;background:linear-gradient(90deg,#0284c7,#38bdf8);color:#000;border:none;border-radius:3px;padding:4px 6px;font-size:8.5px;font-weight:bold;cursor:pointer;">⬇️ 1-Click Download & Set in [02]</button>
              <button data-hf-inspect="${c.repo_id}" data-hf-rec-folder="${c.target_folder}" style="background:#1e293b;color:#e2e8f0;border:1px solid #334155;border-radius:3px;padding:4px 6px;font-size:8.5px;cursor:pointer;">📂 Files</button>
            </div>
          </div>
        `).join("");

        const inspectedHtml = state.hfInspectedRepo ? `
          <div style="background:#0f172a;border:1px solid #eab308;border-radius:5px;padding:6px;display:flex;flex-direction:column;gap:4px;flex-shrink:0;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span style="font-size:9.5px;font-weight:bold;color:#facc15;">📂 Files in ${state.hfInspectedRepo} (Target: models/${state.hfTargetFolder})</span>
              <button class="ez-hf-close-inspect" style="background:#334155;color:#fff;border:none;border-radius:3px;padding:1px 6px;font-size:8px;cursor:pointer;">✕</button>
            </div>
            <div style="max-height:135px;overflow-y:auto;display:flex;flex-direction:column;gap:3px;">
              ${state.hfInspectedFiles.length ? state.hfInspectedFiles.map((f, fIdx) => `
                <div style="display:flex;justify-content:space-between;align-items:center;background:#13161f;border:1px solid ${f.is_q8 ? "#34d399" : "#262b38"};border-radius:3px;padding:3px 6px;gap:6px;">
                  <span style="font-size:8.5px;color:${f.is_q8 ? "#34d399" : "#f8fafc"};font-weight:${f.is_q8 ? "bold" : "normal"};overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${f.path}">
                    ${f.is_q8 ? "🔥 [Q8] " : ""}${f.label || f.path} (${f.size_gb >= 1 ? `${f.size_gb} GB` : `${f.size_mb} MB`})
                  </span>
                  <button data-hf-file-dl="${fIdx}" style="background:${f.is_q8 ? "#10b981" : "#eab308"};color:#000;border:none;border-radius:3px;padding:2px 7px;font-size:8px;font-weight:bold;cursor:pointer;flex-shrink:0;">⬇️ Download</button>
                </div>
              `).join("") : `<div style="font-size:8.5px;color:#94a3b8;padding:4px;">Loading file list...</div>`}
            </div>
          </div>
        ` : "";

        const searchCardsHtml = state.hfItems.map(item => `
          <div style="background:#13161f;border:1px solid #262b38;border-radius:5px;padding:6px;display:flex;flex-direction:column;gap:4px;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span style="font-size:8px;background:#1e293b;color:${item.is_gguf ? "#34d399" : "#facc15"};padding:1px 5px;border-radius:3px;font-weight:bold;">${item.pipeline_tag}</span>
              <span style="font-size:8px;color:#94a3b8;">⬇ ${item.downloads} | ❤️ ${item.likes}</span>
            </div>
            <div style="font-size:9.5px;font-weight:bold;color:#f8fafc;word-break:break-all;" title="${item.repo_id}">${item.repo_id}</div>
            <div style="display:flex;gap:3px;margin-top:auto;">
              <button data-hf-inspect="${item.repo_id}" data-hf-rec-folder="${item.recommended_target}" style="flex:1;background:#eab308;color:#000;border:none;border-radius:3px;padding:3px 6px;font-size:8.5px;font-weight:bold;cursor:pointer;">📂 Choose File / Q8 GGUF</button>
              <button data-hf-full-dl="${item.repo_id}" data-hf-rec-folder="${item.recommended_target}" style="background:#0284c7;color:#fff;border:none;border-radius:3px;padding:3px 6px;font-size:8.5px;font-weight:bold;cursor:pointer;" title="Download entire HuggingFace repository folder">📦 Full Repo</button>
            </div>
          </div>
        `).join("");

        return `
          <div style="display:flex;flex-direction:column;gap:6px;flex:1;min-height:0;height:100%;">
            <div style="display:flex;gap:4px;flex-wrap:wrap;justify-content:space-between;align-items:center;flex-shrink:0;">
              <div style="display:flex;gap:3px;">${catBtns}</div>
              <div style="display:flex;align-items:center;gap:4px;">
                <span style="font-size:8.5px;color:#94a3b8;">Target:</span>
                <select class="ez-hf-target-sel" style="background:#11131a;color:#38bdf8;border:1px solid #334155;border-radius:3px;padding:2px 5px;font-size:8.5px;font-weight:bold;">${folderOpts}</select>
              </div>
            </div>
            <div style="display:flex;gap:4px;flex-shrink:0;">
              <input type="text" class="ez-hf-q-in" value="${state.hfQuery.replace(/"/g, "&quot;")}" placeholder="Search HuggingFace or paste repo/URL (e.g. mradermacher/Huihui-Qwen3-VL-8B-Instruct-abliterated-GGUF)..." style="flex:1;background:#11131a;color:#f8fafc;border:1px solid #334155;border-radius:4px;padding:4px 7px;font-size:9.5px;" />
              <button class="ez-hf-go" style="background:#eab308;color:#000;border:none;border-radius:4px;padding:4px 9px;font-size:9.5px;font-weight:bold;cursor:pointer;">🔍 SEARCH HF</button>
              <button class="ez-hf-inspect-input" style="background:#38bdf8;color:#000;border:none;border-radius:4px;padding:4px 8px;font-size:9px;font-weight:bold;cursor:pointer;" title="Inspect files inside the pasted repo/URL">📂 Inspect Repo</button>
            </div>
            ${inspectedHtml}
            <div class="ez-civ-scroll-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(${cols > 2 ? "250px" : "215px"},1fr));align-content:start;gap:6px;flex:1;min-height:170px;overflow-y:auto;padding:2px;">
              ${curatedHtml}
              ${searchCardsHtml}
            </div>
          </div>
        `;
    };

    const bindHuggingFaceEvents = (container) => {
        const curList = (Array.isArray(state.hfCurated) && state.hfCurated.length) ? state.hfCurated : [
            { repo_id: "huihui-ai/Huihui-Qwen3-VL-4B-Instruct-abliterated", target_folder: "LLM/Qwen-VL", recommended_file: "__FULL_HF_REPO__" },
            { repo_id: "huihui-ai/Huihui-Qwen3-VL-8B-Instruct-abliterated", target_folder: "LLM/Qwen-VL", recommended_file: "__FULL_HF_REPO__" },
            { repo_id: "mradermacher/Huihui-Qwen3-VL-8B-Instruct-abliterated-GGUF", target_folder: "LLM/Qwen-VL", recommended_file: "Huihui-Qwen3-VL-8B-Instruct-abliterated.Q8_0.gguf" },
            { repo_id: "Mungert/Qwen3-VL-8B-Instruct-Unredacted-MAX-GGUF", target_folder: "LLM/GGUF", recommended_file: "Qwen3-VL-8B-Instruct-Unredacted-MAX-q8_0.gguf" }
        ];
        container.querySelectorAll("[data-hf-cat]").forEach(b => {
            b.onclick = () => {
                state.hfCategory = b.getAttribute("data-hf-cat");
                runHuggingFaceSearch();
            };
        });
        const sel = container.querySelector(".ez-hf-target-sel");
        if (sel) {
            sel.onchange = () => { state.hfTargetFolder = sel.value; };
        }
        const qIn = container.querySelector(".ez-hf-q-in");
        if (qIn) {
            qIn.onkeydown = (e) => {
                if (e.key === "Enter") {
                    state.hfQuery = qIn.value || "";
                    if (state.hfQuery.includes("/") && !state.hfQuery.includes(" ")) {
                        inspectHuggingFaceRepo(state.hfQuery, state.hfTargetFolder);
                    } else {
                        runHuggingFaceSearch();
                    }
                }
            };
        }
        const goBtn = container.querySelector(".ez-hf-go");
        if (goBtn) {
            goBtn.onclick = () => {
                if (qIn) state.hfQuery = qIn.value || "";
                runHuggingFaceSearch();
            };
        }
        const inspBtn = container.querySelector(".ez-hf-inspect-input");
        if (inspBtn) {
            inspBtn.onclick = () => {
                if (qIn) state.hfQuery = qIn.value || "";
                inspectHuggingFaceRepo(state.hfQuery, state.hfTargetFolder);
            };
        }
        const closeInsp = container.querySelector(".ez-hf-close-inspect");
        if (closeInsp) {
            closeInsp.onclick = () => {
                state.hfInspectedRepo = "";
                state.hfInspectedFiles = [];
                syncAllViews();
            };
        }
        container.querySelectorAll("[data-hf-cur-dl]").forEach(btn => {
            btn.onclick = () => {
                const c = curList[parseInt(btn.getAttribute("data-hf-cur-dl"), 10)];
                if (c) triggerHuggingFaceDownload(c.repo_id, c.recommended_file, c.target_folder, true);
            };
        });
        container.querySelectorAll("[data-hf-inspect]").forEach(btn => {
            btn.onclick = () => {
                const rid = btn.getAttribute("data-hf-inspect");
                const rf = btn.getAttribute("data-hf-rec-folder") || "";
                inspectHuggingFaceRepo(rid, rf);
            };
        });
        container.querySelectorAll("[data-hf-full-dl]").forEach(btn => {
            btn.onclick = () => {
                const rid = btn.getAttribute("data-hf-full-dl");
                const rf = btn.getAttribute("data-hf-rec-folder") || state.hfTargetFolder;
                triggerHuggingFaceDownload(rid, "__FULL_HF_REPO__", rf, true);
            };
        });
        container.querySelectorAll("[data-hf-file-dl]").forEach(btn => {
            btn.onclick = () => {
                const f = state.hfInspectedFiles[parseInt(btn.getAttribute("data-hf-file-dl"), 10)];
                if (f && state.hfInspectedRepo) {
                    triggerHuggingFaceDownload(state.hfInspectedRepo, f.path, state.hfTargetFolder, true);
                }
            };
        });
    };

    const buildSettingsHtml = () => `
      <div style="display:flex;flex-direction:column;gap:8px;padding:4px;flex:1;min-height:0;overflow-y:auto;">
        <div style="background:#11131a;border:1px solid #334155;border-radius:5px;padding:8px;display:flex;flex-direction:column;gap:5px;">
          <div style="font-size:10px;font-weight:bold;color:#facc15;">🔑 Civitai API Key (Saved locally in CONFIG/civitai_credentials.json)</div>
          <div style="font-size:9px;color:#94a3b8;">Status: ${state.hasKey ? `<span style="color:#34d399;font-weight:bold;">Active (${state.maskedKey})</span>` : `<span style="color:#f87171;">No key saved</span>`}</div>
          <div style="display:flex;gap:4px;">
            <input type="password" class="ez-api-in" placeholder="Paste Civitai API Token..." style="flex:1;background:#090a0f;color:#f8fafc;border:1px solid #334155;border-radius:4px;padding:4px 7px;font-size:10px;" />
            <button class="ez-api-save" style="background:#0284c7;color:#fff;border:none;border-radius:4px;padding:4px 10px;font-size:9.5px;font-weight:bold;cursor:pointer;">💾 Save Key</button>
          </div>
        </div>
        <div style="background:#11131a;border:1px solid #334155;border-radius:5px;padding:8px;display:flex;flex-direction:column;gap:5px;">
          <div style="font-size:10px;font-weight:bold;color:#38bdf8;">🤗 HuggingFace Access Token (Optional — for gated/private HF repos)</div>
          <div style="font-size:9px;color:#94a3b8;">Status: ${state.hasHfToken ? `<span style="color:#34d399;font-weight:bold;">Active (${state.maskedHfToken})</span>` : `<span style="color:#94a3b8;">Public Mode (No token required for public Qwen3-VL / GGUF repos)</span>`}</div>
          <div style="display:flex;gap:4px;">
            <input type="password" class="ez-hf-api-in" placeholder="Paste hf_... token (optional)..." style="flex:1;background:#090a0f;color:#f8fafc;border:1px solid #334155;border-radius:4px;padding:4px 7px;font-size:10px;" />
            <button class="ez-hf-api-save" style="background:#eab308;color:#000;border:none;border-radius:4px;padding:4px 10px;font-size:9.5px;font-weight:bold;cursor:pointer;">💾 Save HF Token</button>
          </div>
        </div>
        <div style="background:#11131a;border:1px solid #334155;border-radius:5px;padding:8px;display:flex;justify-content:space-between;align-items:center;">
          <div>
            <div style="font-size:10px;font-weight:bold;color:#38bdf8;">🗄️ 30-Day Thumbnail & Catalog Cache</div>
            <div style="font-size:9px;color:#94a3b8;">Cached files: ${state.cacheFiles} (Auto-purged after 30 days)</div>
          </div>
          <button class="ez-cache-purge" style="background:#ef4444;color:#fff;border:none;border-radius:4px;padding:5px 9px;font-size:9.5px;font-weight:bold;cursor:pointer;">🧹 Purge Cache Now</button>
        </div>
        <div style="background:#11131a;border:1px solid #334155;border-radius:5px;padding:8px;display:flex;justify-content:space-between;align-items:center;">
          <span style="font-size:9.5px;color:#94a3b8;">Show raw ComfyUI dropdown widgets on node:</span>
          <button class="ez-toggle-raw" style="background:#1e293b;color:#e2e8f0;border:1px solid #475569;border-radius:4px;padding:4px 8px;font-size:9px;cursor:pointer;">${state.showRawWidgets ? "🙈 Hide Raw Dropdowns" : "⚙️ Show Raw Dropdowns"}</button>
        </div>
      </div>
    `;

    const bindSettingsEvents = (container) => {
        const apiIn = container.querySelector(".ez-api-in");
        const apiBtn = container.querySelector(".ez-api-save");
        if (apiBtn) {
            apiBtn.onclick = async () => {
                await api.fetchApi("/ez_cinematrix/civitai/apikey", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ api_key: apiIn ? apiIn.value : "" })
                });
                state.statusMsg = "🔑 Civitai API key updated!";
                fetchStatusAndRecipes();
            };
        }
        const hfIn = container.querySelector(".ez-hf-api-in");
        const hfBtn = container.querySelector(".ez-hf-api-save");
        if (hfBtn) {
            hfBtn.onclick = async () => {
                await api.fetchApi("/ez_cinematrix/civitai/apikey", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ hf_token: hfIn ? hfIn.value : "" })
                });
                state.statusMsg = "🤗 HuggingFace token updated!";
                fetchStatusAndRecipes();
            };
        }
        const purgeBtn = container.querySelector(".ez-cache-purge");
        if (purgeBtn) {
            purgeBtn.onclick = async () => {
                const r = await api.fetchApi("/ez_cinematrix/civitai/cache/clear", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({})
                });
                const d = await r.json();
                state.statusMsg = `🧹 Purged ${d.removed_files || 0} cached files.`;
                fetchStatusAndRecipes();
            };
        }
        const rawBtn = container.querySelector(".ez-toggle-raw");
        if (rawBtn) {
            rawBtn.onclick = () => {
                state.showRawWidgets = !state.showRawWidgets;
                collapseEzCivitaiNativeWidgets(node, !state.showRawWidgets);
                syncAllViews();
            };
        }
    };

    const stopCanvasKeyHijack = (rootEl) => {
        if (!rootEl || rootEl._ezKeyGuardBound) return;
        rootEl._ezKeyGuardBound = true;
        ["keydown", "keyup", "keypress"].forEach(evName => {
            rootEl.addEventListener(evName, (ev) => {
                const t = ev.target;
                if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable)) {
                    ev.stopPropagation();
                }
            });
        });
    };

    const wrap = document.createElement("div");
    wrap.style.cssText = "width:100%;height:100%;background:#090a0f;border:1px solid #eab308;border-radius:7px;padding:7px;margin-top:2px;font-family:monospace;color:#f8fafc;display:flex;flex-direction:column;gap:6px;box-sizing:border-box;overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,0.65);";
    forwardRightClickToNode(wrap, node);
    stopCanvasKeyHijack(wrap);
    node._ezCivitaiDom = wrap;
    if (typeof node.addDOMWidget === "function") {
        node.addDOMWidget("ez_civitai_browser_hub", "div", wrap, { serialize: false, hideOnZoom: false });
    }

    const syncSurfWindowGeometry = () => {
        if (!node || !Array.isArray(node.size)) return;
        const availH = Math.max(330, Math.round(node.size[1] - 185));
        wrap.style.height = "100%";
        wrap.style.minHeight = `${availH}px`;
    };
    const origNodeOnResize = node.onResize;
    node.onResize = function (size) {
        if (origNodeOnResize) origNodeOnResize.apply(this, arguments);
        syncSurfWindowGeometry();
    };

    let modalOverlay = null;
    let modalFullscreen = false;

    const openWebWindowModal = () => {
        if (modalOverlay) { modalOverlay.remove(); modalOverlay = null; }
        modalOverlay = document.createElement("div");
        modalOverlay.style.cssText = "position:fixed;inset:0;background:rgba(4,5,9,0.86);backdrop-filter:blur(5px);z-index:100000;display:flex;align-items:center;justify-content:center;font-family:monospace;color:#f8fafc;";
        modalOverlay.onclick = (e) => { if (e.target === modalOverlay) { modalOverlay.remove(); modalOverlay = null; } };
        stopCanvasKeyHijack(modalOverlay);
        document.body.appendChild(modalOverlay);
        if (state.activeTab === "stack") state.activeTab = "local";
        syncAllViews();
    };

    const renderInlineNode = () => {
        const actDl = (state.downloadsSummary && state.downloadsSummary.active_count) || 0;
        const dlBadge = actDl > 0 ? `⬇️ DL (${actDl})` : `⬇️ DL`;
        const tabs = [
            { id: "stack", lbl: "🎛️ Active Rig" },
            { id: "local", lbl: "🗂️ Local" },
            { id: "civitai", lbl: "🌐 Civitai" },
            { id: "hf", lbl: "🤗 HF Hub" },
            { id: "downloads", lbl: dlBadge },
            { id: "recipes", lbl: "💾 Recipes" },
            { id: "settings", lbl: "🔑 API" }
        ];
        const tabBar = tabs.map(t =>
            renderPillBtn(t.lbl, state.activeTab === t.id, "#eab308", `flex:1;text-align:center;`)
                .replace("<button ", `<button data-tab="${t.id}" `)
        ).join("");

        let bodyObj = { html: "", filtered: [] };
        if (state.activeTab === "stack") bodyObj.html = buildStackPanelHtml(true);
        else if (state.activeTab === "local") bodyObj = buildLocalBankHtml(2);
        else if (state.activeTab === "civitai") bodyObj.html = buildCivitaiWebHtml(2);
        else if (state.activeTab === "hf") bodyObj.html = buildHuggingFaceHtml(2);
        else if (state.activeTab === "downloads") bodyObj.html = buildDownloadsHtml();
        else if (state.activeTab === "recipes") bodyObj.html = buildRecipesHtml(2);
        else bodyObj.html = buildSettingsHtml();

        wrap.innerHTML = `
          <div style="display:flex;justify-content:space-between;align-items:center;background:#11131a;border:1px solid #1e293b;border-radius:5px;padding:4px 7px;flex-shrink:0;">
            <span style="font-size:9.5px;color:${state.licensed ? "#34d399" : "#38bdf8"};font-weight:bold;">
              ${state.licensed ? "🟢 PRO STUDIO (.com + .red + HF)" : "🛡️ FREEMIUM (.com + HF)"}
            </span>
            <button class="ez-open-webwin" style="background:linear-gradient(90deg,#eab308,#f59e0b);color:#000;border:none;border-radius:4px;padding:3px 8px;font-size:9.5px;font-weight:bold;cursor:pointer;">🗖 OPEN WEB WINDOW</button>
          </div>
          <div style="display:flex;gap:3px;flex-wrap:wrap;flex-shrink:0;">${tabBar}</div>
          <div class="ez-inline-body" style="background:#0c0e14;border:1px solid #1e293b;border-radius:5px;padding:6px;flex:1;min-height:0;display:flex;flex-direction:column;overflow:hidden;">
            ${bodyObj.html}
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;font-size:8.5px;color:#94a3b8;padding:0 2px;flex-shrink:0;">
            <span style="color:#facc15;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:75%;">${state.statusMsg}</span>
            <span>Cache: ${state.cacheFiles}</span>
          </div>
        `;
        syncSurfWindowGeometry();

        wrap.querySelector(".ez-open-webwin").onclick = () => openWebWindowModal();
        wrap.querySelectorAll("[data-tab]").forEach(b => {
            b.onclick = () => {
                state.activeTab = b.getAttribute("data-tab");
                if (state.activeTab === "local" && !state.localLoras.length) fetchLocalCatalog();
                if (state.activeTab === "civitai" && !state.civItems.length) runCivitaiSearch(false);
                if (state.activeTab === "hf" && !state.hfItems.length) runHuggingFaceSearch();
                if (state.activeTab === "downloads") pollDownloadsStatus();
                syncAllViews();
            };
        });
        const bodyEl = wrap.querySelector(".ez-inline-body");
        if (state.activeTab === "stack") bindStackEvents(bodyEl);
        else if (state.activeTab === "local") bindLocalBankEvents(bodyEl, bodyObj.filtered);
        else if (state.activeTab === "civitai") bindCivitaiWebEvents(bodyEl);
        else if (state.activeTab === "hf") bindHuggingFaceEvents(bodyEl);
        else if (state.activeTab === "downloads") bindDownloadsEvents(bodyEl);
        else if (state.activeTab === "recipes") bindRecipesEvents(bodyEl);
        else bindSettingsEvents(bodyEl);
    };

    const renderModalWindow = () => {
        if (!modalOverlay) return;
        const mTab = state.activeTab === "stack" ? "local" : state.activeTab;
        const actDl = (state.downloadsSummary && state.downloadsSummary.active_count) || 0;
        let leftObj = { html: "", filtered: [] };
        if (mTab === "local") leftObj = buildLocalBankHtml(3);
        else if (mTab === "civitai") leftObj.html = buildCivitaiWebHtml(3);
        else if (mTab === "hf") leftObj.html = buildHuggingFaceHtml(3);
        else if (mTab === "downloads") leftObj.html = buildDownloadsHtml();
        else if (mTab === "recipes") leftObj.html = buildRecipesHtml(3);
        else leftObj.html = buildSettingsHtml();

        const boxSizeStyle = modalFullscreen
            ? "width:99vw;height:98vh;max-width:none;max-height:none;"
            : "width:94vw;height:88vh;min-width:680px;min-height:480px;resize:both;";

        modalOverlay.innerHTML = `
          <div style="${boxSizeStyle}background:#090a0f;border:2px solid #eab308;border-radius:10px;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 24px 64px rgba(0,0,0,0.9);">
            <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 16px;background:#11131a;border-bottom:1px solid #1e293b;flex-shrink:0;">
              <div style="display:flex;align-items:center;gap:12px;">
                <span style="font-size:13px;font-weight:bold;color:#facc15;">🌐 EZ [10] CIVITAI & HUGGINGFACE MODEL HUB WEB-STUDIO</span>
                <span style="font-size:10px;background:#1e293b;color:${state.licensed ? "#34d399" : "#38bdf8"};padding:2px 8px;border-radius:4px;font-weight:bold;">
                  ${state.licensed ? "🔓 LICENSED PRO (.com + .red + HuggingFace)" : "🛡️ FREEMIUM (.com + HuggingFace)"}
                </span>
              </div>
              <div style="display:flex;gap:6px;align-items:center;">
                <button data-mtab="local" style="background:${mTab === "local" ? "#eab308" : "#1e293b"};color:${mTab === "local" ? "#000" : "#e2e8f0"};border:none;border-radius:4px;padding:5px 11px;font-size:10.5px;font-weight:bold;cursor:pointer;">🗂️ Local Bank</button>
                <button data-mtab="civitai" style="background:${mTab === "civitai" ? "#eab308" : "#1e293b"};color:${mTab === "civitai" ? "#000" : "#e2e8f0"};border:none;border-radius:4px;padding:5px 11px;font-size:10.5px;font-weight:bold;cursor:pointer;">🌐 Civitai Catalog</button>
                <button data-mtab="hf" style="background:${mTab === "hf" ? "#eab308" : "#1e293b"};color:${mTab === "hf" ? "#000" : "#e2e8f0"};border:none;border-radius:4px;padding:5px 11px;font-size:10.5px;font-weight:bold;cursor:pointer;">🤗 HuggingFace Hub (Qwen3-VL / GGUF)</button>
                <button data-mtab="downloads" style="background:${mTab === "downloads" ? "#eab308" : "#1e293b"};color:${mTab === "downloads" ? "#000" : "#e2e8f0"};border:none;border-radius:4px;padding:5px 11px;font-size:10.5px;font-weight:bold;cursor:pointer;">⬇️ Downloads (${actDl > 0 ? `${actDl} active` : state.downloadsQueue.length})</button>
                <button data-mtab="recipes" style="background:${mTab === "recipes" ? "#eab308" : "#1e293b"};color:${mTab === "recipes" ? "#000" : "#e2e8f0"};border:none;border-radius:4px;padding:5px 11px;font-size:10.5px;font-weight:bold;cursor:pointer;">💾 Recipes (${state.recipes.length})</button>
                <button data-mtab="settings" style="background:${mTab === "settings" ? "#eab308" : "#1e293b"};color:${mTab === "settings" ? "#000" : "#e2e8f0"};border:none;border-radius:4px;padding:5px 11px;font-size:10.5px;font-weight:bold;cursor:pointer;">🔑 API & Cache</button>
                <button class="ez-max-modal" style="background:#334155;color:#f8fafc;border:none;border-radius:4px;padding:5px 10px;font-size:10.5px;font-weight:bold;cursor:pointer;margin-left:4px;">${modalFullscreen ? "🗗 RESTORE" : "⛶ FULLSCREEN"}</button>
                <button class="ez-close-modal" style="background:#dc2626;color:#fff;border:none;border-radius:4px;padding:5px 12px;font-size:10.5px;font-weight:bold;cursor:pointer;">✕ CLOSE</button>
              </div>
            </div>
            <div style="flex:1;min-height:0;display:grid;grid-template-columns:1fr 370px;overflow:hidden;">
              <div class="ez-modal-left" style="padding:12px;display:flex;flex-direction:column;min-height:0;overflow:hidden;border-right:1px solid #1e293b;">
                ${leftObj.html}
              </div>
              <div class="ez-modal-right" style="padding:12px;display:flex;flex-direction:column;min-height:0;overflow-y:auto;background:#0c0e14;">
                <div style="font-size:11px;font-weight:bold;color:#facc15;margin-bottom:8px;border-bottom:1px solid #1e293b;padding-bottom:4px;flex-shrink:0;">🎛️ ACTIVE RIG & LORA STACK (LIVE)</div>
                ${buildStackPanelHtml(false)}
              </div>
            </div>
            <div style="padding:7px 16px;background:#11131a;border-top:1px solid #1e293b;display:flex;justify-content:space-between;font-size:10px;color:#94a3b8;flex-shrink:0;">
              <span style="color:#facc15;font-weight:bold;">${state.statusMsg}</span>
              <span>🔒 Modality-Lock Active: IMAGE (KREA2/Flux) ⇄ VIDEO (MiniMax H3/Wan) ⇄ VLM (Qwen3-VL Q8/GGUF)</span>
            </div>
          </div>
        `;
        modalOverlay.querySelector(".ez-max-modal").onclick = () => { modalFullscreen = !modalFullscreen; renderModalWindow(); };
        modalOverlay.querySelector(".ez-close-modal").onclick = () => { modalOverlay.remove(); modalOverlay = null; };
        modalOverlay.querySelectorAll("[data-mtab]").forEach(b => {
            b.onclick = () => {
                state.activeTab = b.getAttribute("data-mtab");
                if (state.activeTab === "civitai" && !state.civItems.length) runCivitaiSearch(false);
                if (state.activeTab === "hf" && !state.hfItems.length) runHuggingFaceSearch();
                if (state.activeTab === "downloads") pollDownloadsStatus();
                syncAllViews();
            };
        });
        const leftEl = modalOverlay.querySelector(".ez-modal-left");
        const rightEl = modalOverlay.querySelector(".ez-modal-right");
        bindStackEvents(rightEl);
        if (mTab === "local") bindLocalBankEvents(leftEl, leftObj.filtered);
        else if (mTab === "civitai") bindCivitaiWebEvents(leftEl);
        else if (mTab === "hf") bindHuggingFaceEvents(leftEl);
        else if (mTab === "downloads") bindDownloadsEvents(leftEl);
        else if (mTab === "recipes") bindRecipesEvents(leftEl);
        else bindSettingsEvents(leftEl);
    };

    function syncAllViews() {
        const activeEl = document.activeElement;
        let focusRestore = null;
        if (activeEl && (activeEl.tagName === "INPUT" || activeEl.tagName === "TEXTAREA")) {
            const inModal = Boolean(modalOverlay && modalOverlay.contains(activeEl));
            const inWrap = Boolean(wrap && wrap.contains(activeEl));
            if (inModal || inWrap) {
                const trackedClasses = [
                    "ez-loc-search",
                    "ez-civ-q-in",
                    "ez-hf-q-in",
                    "ez-rec-new-name",
                    "ez-api-in",
                    "ez-hf-api-in",
                    "ez-trig-input"
                ];
                const matchedCls = trackedClasses.find(c => activeEl.classList.contains(c));
                if (matchedCls) {
                    const val = activeEl.value || "";
                    if (matchedCls === "ez-loc-search") state.localQuery = val;
                    else if (matchedCls === "ez-civ-q-in") state.civQuery = val;
                    else if (matchedCls === "ez-hf-q-in") state.hfQuery = val;
                    focusRestore = {
                        inModal,
                        cls: matchedCls,
                        val,
                        selStart: typeof activeEl.selectionStart === "number" ? activeEl.selectionStart : val.length,
                        selEnd: typeof activeEl.selectionEnd === "number" ? activeEl.selectionEnd : val.length
                    };
                }
            }
        }
        renderInlineNode();
        if (modalOverlay) renderModalWindow();
        if (focusRestore) {
            const targetRoot = focusRestore.inModal && modalOverlay ? modalOverlay : wrap;
            const restoredInput = targetRoot ? targetRoot.querySelector(`.${focusRestore.cls}`) : null;
            if (restoredInput) {
                if (restoredInput.value !== focusRestore.val) restoredInput.value = focusRestore.val;
                try {
                    restoredInput.focus({ preventScroll: true });
                    if (typeof restoredInput.setSelectionRange === "function" && restoredInput.type !== "password") {
                        restoredInput.setSelectionRange(focusRestore.selStart, focusRestore.selEnd);
                    }
                } catch (e) {}
            }
        }
    }

    syncAllViews();
    fetchStatusAndRecipes();
    fetchLocalCatalog();
    node.setSize([Math.max(node.size[0], 460), Math.max(node.size[1], 560)]);
}

const EZ_SUPPORTED_LOCALES = ["EN", "SV", "ZH", "JA", "ES", "DE", "FR"];
let EZ_ACTIVE_LOCALE = (typeof localStorage !== "undefined" && localStorage.getItem("ez_cinematrix_locale")) || "EN";
if (!EZ_SUPPORTED_LOCALES.includes(EZ_ACTIVE_LOCALE)) EZ_ACTIVE_LOCALE = "EN";

const EZ_WIDGET_LOCALE_MAP = {
    content_rating_mode: { EN: "content_rating_mode (SFW/Uncensored/NSFW)", SV: "innehållsläge (SFW/Uncensored/NSFW)", ZH: "内容分级 (SFW/无审查/NSFW)", JA: "コンテンツモード (SFW/無検閲/NSFW)", ES: "modo_contenido (SFW/SinCensura/NSFW)", DE: "Inhaltsmodus (SFW/Unzensiert/NSFW)", FR: "mode_contenu (SFW/SansCensure/NSFW)" },
    generation_mode: { EN: "generation_mode", SV: "genereringsläge", ZH: "生成模式", JA: "生成モード", ES: "modo_generación", DE: "Generierungsmodus", FR: "mode_génération" },
    production_mode: { EN: "production_mode", SV: "produktionsläge", ZH: "制作模式", JA: "制作モード (I2VA/REF2VA)", ES: "modo_producción", DE: "Produktionsmodus", FR: "mode_production" },
    i2i_denoise: { EN: "i2i_denoise (Image Fidelity 0.01)", SV: "i2i_denoise (Bildtrohet 0.01)", ZH: "图生图重绘幅度 (i2i_denoise 0.01)", JA: "i2i_denoise (元画像維持度 0.01)", ES: "i2i_denoise (Fidelidad 0.01)", DE: "i2i_denoise (Bildtreue 0.01)", FR: "i2i_denoise (Fidélité 0.01)" },
    handoff_percent: { EN: "handoff_percent (Stage 1➔2 % 0.01)", SV: "handoff_percent (Steg 1➔2 % 0.01)", ZH: "阶段1➔2交接% (handoff_percent 0.01)", JA: "Stage 1➔2 移行% (handoff 0.01)", ES: "handoff_percent (Etapa 1➔2 % 0.01)", DE: "handoff_percent (Stufe 1➔2 % 0.01)", FR: "handoff_percent (Étape 1➔2 % 0.01)" },
    stage3_handoff_percent: { EN: "stage3_handoff_percent (Stage 2➔3 % 0.01)", SV: "stage3_handoff_percent (Steg 2➔3 % 0.01)", ZH: "阶段2➔3交接% (stage3_handoff 0.01)", JA: "Stage 2➔3 移行% (stage3 0.01)", ES: "stage3_handoff_percent (Etapa 2➔3 % 0.01)", DE: "stage3_handoff_percent (Stufe 2➔3 % 0.01)", FR: "stage3_handoff_percent (Étape 2➔3 % 0.01)" },
    subject_stance_posture: { EN: "subject_stance_posture (Posture)", SV: "subject_stance_posture (Kroppshållning)", ZH: "角色姿态与场景 (stance_posture)", JA: "姿勢 & シーン構成 (stance_posture)", ES: "postura_sujeto", DE: "Körperhaltung", FR: "posture_sujet" },
    body_choreography_preset: { EN: "body_choreography_preset (Choreo)", SV: "body_choreography_preset (Rörelseschema)", ZH: "动作与舞蹈编排 (choreography)", JA: "モーション & 振付 (choreography)", ES: "coreografía_cuerpo", DE: "Körper-Choreografie", FR: "chorégraphie_corps" },
    camera_trajectory_arc: { EN: "camera_trajectory_arc (Camera Arc)", SV: "camera_trajectory_arc (Kamerabana)", ZH: "镜头轨迹与升降 (camera_arc)", JA: "カメラ軌道 & アーク (camera_arc)", ES: "trayectoria_cámara", DE: "Kamera-Flugbahn", FR: "trajectoire_caméra" },
    scene_continuity_mode: { EN: "scene_continuity_mode (Stage / One-Shot / Multi-Cut)", SV: "scene_continuity_mode (Låst Scen / One-Shot / Scenklipp)", ZH: "场景连续性模式 (锁定 / 一镜到底 / 多场景剪辑)", JA: "シーン連続性モード (固定 / ワンカット / マルチシーン)", ES: "modo_continuidad_escena (Fijo / One-Shot / Cortes)", DE: "Szenen-Kontinuität (Fixiert / One-Shot / Schnitte)", FR: "mode_continuité_scène (Fixe / Plan-Séquence / Coupes)" },
    temporal_window_horizon: { EN: "temporal_window_horizon (PRO Focus Seam / 5s / 10s)", SV: "temporal_window_horizon (PRO Fokus-Skarv / 5s / 10s)", ZH: "时间窗口跨度 (PRO焦点接缝 / 5s / 10s)", JA: "時間ウィンドウ幅 (PROフォーカス継目 / 5s / 10s)", ES: "horizonte_ventana_temporal (PRO / 5s / 10s)", DE: "Zeitfenster-Horizont (PRO Fokus / 5s / 10s)", FR: "horizon_fenêtre_temporelle (PRO / 5s / 10s)" },
    rife_model: { EN: "rife_model", SV: "rife_modell", ZH: "RIFE补帧模型", JA: "RIFE補間モデル", ES: "modelo_rife", DE: "RIFE-Modell", FR: "modèle_rife" },
    rife_multiplier: { EN: "rife_multiplier", SV: "rife_multiplikator", ZH: "RIFE补帧倍率", JA: "RIFE補間倍率", ES: "multiplicador_rife", DE: "RIFE-Multiplikator", FR: "multiplicateur_rife" },
    rife_strength: { EN: "rife_strength", SV: "rife_styrka", ZH: "RIFE运动强度", JA: "RIFE補間強度", ES: "fuerza_rife", DE: "RIFE-Stärke", FR: "force_rife" },
    style_clip_strength_1: { EN: "style_clip_strength_1 (CLIP)", SV: "style_clip_strength_1 (CLIP)", ZH: "CLIP强度 1", JA: "CLIP強度 1", ES: "fuerza_clip_1", DE: "CLIP-Stärke 1", FR: "force_clip_1" },
    style_clip_strength_2: { EN: "style_clip_strength_2 (CLIP)", SV: "style_clip_strength_2 (CLIP)", ZH: "CLIP强度 2", JA: "CLIP強度 2", ES: "fuerza_clip_2", DE: "CLIP-Stärke 2", FR: "force_clip_2" },
    style_clip_strength_3: { EN: "style_clip_strength_3 (CLIP)", SV: "style_clip_strength_3 (CLIP)", ZH: "CLIP强度 3", JA: "CLIP強度 3", ES: "fuerza_clip_3", DE: "CLIP-Stärke 3", FR: "force_clip_3" },
    style_clip_strength_4: { EN: "style_clip_strength_4 (CLIP)", SV: "style_clip_strength_4 (CLIP)", ZH: "CLIP强度 4", JA: "CLIP強度 4", ES: "fuerza_clip_4", DE: "CLIP-Stärke 4", FR: "force_clip_4" },
    lora_1_vis_strength: { EN: "lora_1_vis_strength (VIS)", SV: "lora_1_vis_strength (VIS)", ZH: "LoRA 1 视觉强度 (VIS)", JA: "LoRA 1 視覚強度 (VIS)", ES: "lora_1_vis (VIS)", DE: "LoRA 1 VIS-Stärke", FR: "lora_1_vis (VIS)" },
    lora_2_vis_strength: { EN: "lora_2_vis_strength (VIS)", SV: "lora_2_vis_strength (VIS)", ZH: "LoRA 2 视觉强度 (VIS)", JA: "LoRA 2 視覚強度 (VIS)", ES: "lora_2_vis (VIS)", DE: "LoRA 2 VIS-Stärke", FR: "lora_2_vis (VIS)" },
    lora_3_vis_strength: { EN: "lora_3_vis_strength (VIS)", SV: "lora_3_vis_strength (VIS)", ZH: "LoRA 3 视觉强度 (VIS)", JA: "LoRA 3 視覚強度 (VIS)", ES: "lora_3_vis (VIS)", DE: "LoRA 3 VIS-Stärke", FR: "lora_3_vis (VIS)" },
    lora_4_vis_strength: { EN: "lora_4_vis_strength (VIS)", SV: "lora_4_vis_strength (VIS)", ZH: "LoRA 4 视觉强度 (VIS)", JA: "LoRA 4 視覚強度 (VIS)", ES: "lora_4_vis (VIS)", DE: "LoRA 4 VIS-Stärke", FR: "lora_4_vis (VIS)" },
    detailer_1x_model_name: { EN: "detailer_1x_model_name (1x Skin/Detail)", SV: "detailer_1x_model_name (1x Hud/Detalj)", ZH: "1x皮肤细节模型", JA: "1x肌ディテールモデル", ES: "modelo_detalle_1x", DE: "1x-Detailer-Modell", FR: "modèle_détail_1x" }
};

function applyEzLocaleToNode(node) {
    if (!node || !Array.isArray(node.widgets)) return;
    for (const w of node.widgets) {
        const entry = EZ_WIDGET_LOCALE_MAP[w.name];
        if (entry && entry[EZ_ACTIVE_LOCALE]) {
            w.label = entry[EZ_ACTIVE_LOCALE];
        } else if (entry) {
            w.label = w.name;
        }
    }
}

const EZ_STUDIO_NOTE_I18N = {
    SV: {
        title: "📝 EZ [11] STUDIO ANTECKNINGAR, HOW-TO & MODELL-HANDBOK ([01]➔[13])",
        openWindowBtn: "🗖 ÖPPNA HANDBOKSFÖNSTER",
        tabs: { all: "📚 Alla", howto: "🗺️ How-To & [13]", suno: "🎵 Suno & Tal [12]", models: "💎 PRISM & Modeller", upscale: "🚀 Lanczos & 4x/1x", tips: "🎥 Kamera & Spektral", basics: "🎓 Basics & Foundry", custom: "📝 Anteckningar" },
        howto: `<div style="display:flex;flex-direction:column;gap:6px;">
          <div><b style="color:#22d3ee;">🗺️ 1. KRONOLOGISK KOPPLINGSGUIDE ([01] ➔ [13]) & UPPLÖSNING I [06]</b></div>
          <div>• <b>1-Klicks Auto-Wire (Alla 13 Noder)</b>: Högerklicka på valfri EZ-nod ➔ <code>⚡ Auto-Skapa & Koppla hela EZ Cinematrix-flödet (1-Klick)</code>. Kopplar <code>[09] ➔ [10] ➔ [11] ➔ [12] ➔ [13] ➔ [01] ➔ [02] ➔ [03] ➔ [04] ➔ [05] ➔ [06] ➔ [07] ➔ [08]</code>.</div>
          <div>• <b style="color:#34d399;">📐 Upplösning i [06] Video Director</b>: Koppla <code>final_width ➔ video_width</code> och <code>final_height ➔ video_height</code> från <b>[01]</b> till <b>[06]</b>! (<code>base_width</code>/<code>base_height</code> ska <b>endast</b> kopplas till <b>[03]</b> och <b>[04]</b>).</div>
          <div>• <b style="color:#fbbf24;">🖼️ EZ [13] Omni-Reference Load Image & Control Studio (4 Bilder i Samma Nod)</b>:<br/>
            — <b>Slot 1 (Master Composition)</b>: Inpainting + ControlNet (OpenPose 17-leds skelett / Canny / Lineart / TemporalNet) + LayerDiffusion.<br/>
            — <b>Slot 2 (Person / Face-ID)</b>: ReActor Face-Swap + ADetailer Face/Eye + AdvancedLivePortrait + IP-Adapter FaceID PlusV2.<br/>
            — <b>Slot 3 (Clothing / Garment)</b>: OOTDiffusion (Open-Outfitting torsoklädsel) + LayerDiffusion Alpha.<br/>
            — <b>Slot 4 (Background / Environment)</b>: DepthAnything / MiDaS 3D-djupkarta + ControlNet Tile & Relighting.</div>
        </div>`,
        suno: `<div style="display:flex;flex-direction:column;gap:6px;">
          <div><b style="color:#f0abfc;">🎵 2. EZ [12] SUNO MUSIC VIDEO, BYPASS, WHISPER ASR & VISUELL STIL-PRIORITET</b></div>
          <div>• <b>🔇 Äkta Bypass i [12]</b>: Välj <code>Bypass / Off (Standard Video)</code> (eller <code>Ctrl+B</code>) för att stänga av Suno 100% även om en länk ligger kvar i fältet.</div>
          <div>• <b>🎨 Referensbild & style_target har 100% Prioritet</b>: <code>song_style_tags</code> i <b>[12]</b> styr endast lyrisk rytm/stämning och skriver ALDRIG över dina referensbilder i <b>[13]/[01]</b> eller <code>style_target</code> i <b>[02]</b>!</div>
          <div>• <b>🔗 Suno-Länk (v3–v5.5) & Whisper ASR</b>: Klistra in <code>suno.com/s/...</code> för 48 kHz Stereo Master + lokal Whisper-transkribering. Lämna <code>user_input</code> tom i <b>[02]</b> (utan referensbild) för Auto-Prompt från ljudet.</div>
        </div>`,
        models: `<div style="display:flex;flex-direction:column;gap:6px;">
          <div><b style="color:#fbbf24;">💎 3. PRISM ORTOGONAL SVD, MODELLER, VAE, CLIP, LORAS &amp; HUGGINGFACE ([03]–[10])</b></div>
          <div>• <b style="color:#34d399;">📦 Officiellt HuggingFace-Arkiv (MiniMax H3)</b>: <a href="https://huggingface.co/DeepBeepMeep/MiniMax-H3/tree/main" target="_blank" rel="noopener noreferrer" style="color:#38bdf8;text-decoration:underline;">https://huggingface.co/DeepBeepMeep/MiniMax-H3/tree/main</a> (LoRAs: <a href="https://huggingface.co/DeepBeepMeep/MiniMax-H3/tree/main/loras" target="_blank" rel="noopener noreferrer" style="color:#38bdf8;text-decoration:underline;">/loras</a>).</div>
          <div>• <b style="color:#22d3ee;">🏛️ Bästa Video-UNets (16 GB+)</b>: <b>#1 Realism/NSFW (Inbakad Turbo=OFF)</b>: <code>10Eros_Max_SingularityV2_PRISM2_PikaFlex_0.85_int8HQ.safetensors</code> | <b>#2 Blackwell NVFP4 (13.8 GB, Inbakad Turbo=OFF)</b>: <code>FastH3-Omni-NVFP4-QAD-pruned_rank8_nvfp4.safetensors</code> | <b>#3 Non-Turbo (Turbo-LoRA=ON)</b>: <code>h3ErosMax_beta5_3185154.safetensors</code> | <b>Ref2VA</b>: <code>dasiwa_ref2va_v5xs</code> / <code>Minimax-h3_Singularity_ref2va_v2_pruned_int8_convrot.safetensors</code>.</div>
          <div>• <b style="color:#facc15;">🧩 Bästa CLIP, Video-VAE &amp; Audio-VAE i [05]</b>: <b>CLIP (<code>minimax</code>)</b> = <code>qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors</code> | <b>Video-VAE (16-bitars, noll kontrastdrift!)</b> = <code>MiniMax-H3-video_vae_fp16.safetensors</code> (<code>5.21 GB</code>, ersätter <code>int8_convrot</code>!) | <b>Audio-VAE</b> = <code>MiniMax-H3-audio_vae_fp32.safetensors</code> (<code>605 MB</code>).</div>
          <div>• <b style="color:#f0abfc;">⚡ Bästa Video-LoRAs (<code>/loras</code>)</b>: <b>#1 Ny Turbo-LoRA (endast på Non-Turbo UNet)</b> = <code>minimax_h3_dmad_8step_full_critic_lora_bf16.safetensors</code> (<code>1.38 GB</code>) | <b>#2 Skärpa/Mikrodetalj (alla UNets @ 0.20–0.30)</b> = <code>minimax_h3_lms_v1.0_r64.safetensors</code> | <b>#3 Rörelse</b> = <code>H3_VBVR_Pro_attn_only.safetensors</code> (<code>0.35–0.45</code>).</div>
          <div>• <b style="color:#38bdf8;">💎 PRISM Multi-LoRA Orthogonalization &amp; Turbo-Shield ([03], [05], [10])</b>: Projicerar sekundära LoRAs och Turbo-LoRAs ortogonalt bort från <code>Slot 1</code> + Smart Lazy-Loading (<code>0 MB extra VRAM</code> för inaktiv <code>FL2VA/REF2VA</code>-slot).</div>
        </div>`,
        upscale: `<div style="display:flex;flex-direction:column;gap:6px;">
          <div><b style="color:#f472b6;">🚀 4. KANTSTYRD LANCZOS + MULTI-SCALE RESTORER, 4x➔2x SUPERSAMPLING & RIFE IFNet ([04] & [08])</b></div>
          <div>• <b>🔬 Steg 1 (0 MB VRAM): Kantstyrd Lanczos + Multi-Scale High-Pass Restorer</b> i <b>[04]</b> &amp; <b>[08]</b> återställer sub-pixel-mikrodetaljer (<code>sigma=0.85/2.1</code>) med anti-halo-klippning.</div>
          <div>• <b>✨ Steg 2: 100% KeypointRCNN 6-Zons Skelett-Skydd + Äkta RIFE v4.7/v4.9 IFNet (rife49.pth / rife47.pth)</b>.</div>
          <div>• <b style="color:#34d399;">🏆 Bästa 3-Stegs Master-Kedja i [08]</b>: <b>4x-ClearRealityV1.pth</b> (supersamplas 4x➔2x) + <b>1x-ITF-SkinDiffDetail-Lite-v1.pth</b> (45% blend) + <code>enable_frequency_polish = true</code>.</div>
        </div>`,
        tips: `<div style="display:flex;flex-direction:column;gap:6px;">
          <div><b style="color:#34d399;">💡 5. KREA 2 FINJUSTERING ([02]–[04]), 100% INNEHÅLLS-/ÅLDERSAUKTORITET, ANTI-GHOSTING &amp; PRISM ([07])</b></div>
          <div>• <b style="color:#fbbf24;">🎛️ Finjustering i EZ [04] (handoff_percent, stage3_handoff &amp; i2i_denoise med 0.01-steg)</b>: Håll <code>handoff_percent = 56.00–62.00%</code> och <code>stage3_handoff_percent = 88.00–92.00%</code> (med automatiskt 16-kanals anti-ghosting &amp; 5-finger-lås). <code>i2i_denoise</code> stegar med <b>0.01</b> (<code>0.70–0.78</code> = balanserad fotorealism &amp; dubbelriktat rem-/glip-lås).</div>
          <div>• <b style="color:#38bdf8;">🛡️ 100% Nod-Auktoritet för content_rating_mode &amp; subject_1_age i [02] &amp; [06]</b>: <code>Uncensored Artistic / Action</code> bevarar mörk fantasy, stridsaction, rustningsklyfta och höftskynke med glipor men blockerar automatiskt oönskade explicita NSFW-ord.</div>
          <div>• <b style="color:#22d3ee;">🎥 3-Axlad Regissör (Backward Track &amp; Outro Track ➔ Follow) ([02], [06], [07])</b> &amp; <b style="color:#f0abfc;">💎 PRISM Latent Spectral Lock i [07]</b>.</div>
        </div>`,
        basics: `<div style="display:flex;flex-direction:column;gap:6px;">
          <div><b style="color:#38bdf8;">🎓 7. BASICS — COMFYUI, MODELLTYPER, LORA/DORA & PRISM MODEL FOUNDRY</b></div>
          <div>• <b>🏛️ EZ Model Foundry & LoRA Lab (i DevOps Studio)</b>: 5 stationer för Dataset-kureringsflöde, LoRA/DoRA-träning, <b>Gold Epoch</b> via PRISM Effective Rank Entropy &amp; Condition Number, <b>PRISM SVD Tail Denoising</b> samt <b>PRISM Orthogonal SVD Merge</b> och <code>Int8 ConvRot</code> / <code>NVFP4</code>-kvantisering.</div>
          <div>• <b>📦 python_embedded &amp; requirements.txt</b>: 3-stegs hårdvaruacceleration (<code>PyTorch cuSOLVER</code> ➔ <code>SciPy/NumPy LAPACK gesdd</code> ➔ <code>Pure-Python Gram-Schmidt</code>) med automatisk synk av <code>scipy>=1.11.0</code>, <code>numpy>=1.26.0</code>, <code>safetensors>=0.4.3</code> och <code>Pillow>=10.3.0</code>.</div>
        </div>`,
        customLabel: "📝 Egna Projekt-Anteckningar (Synkas direkt med nodens custom_notes):"
    },
    EN: {
        title: "📝 EZ [11] STUDIO NOTES, HOW-TO & MODEL HANDBOOK ([01]➔[13])",
        openWindowBtn: "🗖 OPEN HANDBOOK WINDOW",
        tabs: { all: "📚 All", howto: "🗺️ How-To & [13]", suno: "🎵 Suno & ASR [12]", models: "💎 PRISM & Models", upscale: "🚀 Lanczos & 4x/1x", tips: "🎥 Tuning & Camera", basics: "🎓 Basics & Foundry", custom: "📝 Scratchpad" },
        howto: `<div style="display:flex;flex-direction:column;gap:6px;">
          <div><b style="color:#22d3ee;">🗺️ 1. CHRONOLOGICAL WIRING GUIDE ([01] ➔ [13]) & RESOLUTION ROUTING IN [06]</b></div>
          <div>• <b>1-Click Auto-Wire (All 13 Nodes)</b>: Right-click any EZ node ➔ <code>⚡ Auto-Build & Wire Full EZ Cinematrix Pipeline (1-Click)</code> (wires <code>[09] ➔ [10] ➔ [11] ➔ [12] ➔ [13] ➔ [01] ... ➔ [08]</code>).</div>
          <div>• <b style="color:#34d399;">📐 Resolution Wiring in [06] Video Director</b>: Wire <code>final_width ➔ video_width</code> and <code>final_height ➔ video_height</code> from <b>[01]</b> to <b>[06]</b>! (<code>base_width</code>/<code>base_height</code> go <b>only</b> to <b>[03]</b> and <b>[04]</b>).</div>
          <div>• <b style="color:#fbbf24;">🖼️ EZ [13] Omni-Reference Load Image & Control Studio (4 Images in 1 Node)</b>:<br/>
            — <b>Slot 1 (Master Composition)</b>, <b>Slot 2 (Person / Face-ID)</b>, <b>Slot 3 (Clothing / Garment)</b>, <b>Slot 4 (Background / Environment)</b>.</div>
        </div>`,
        suno: `<div style="display:flex;flex-direction:column;gap:6px;">
          <div><b style="color:#f0abfc;">🎵 2. EZ [12] SUNO MUSIC VIDEO, BYPASS, WHISPER ASR & VISUAL STYLE PRIORITY</b></div>
          <div>• <b>🔇 True Bypass in [12]</b>: Select <code>Bypass / Off (Standard Video)</code> (or press <code>Ctrl+B</code>) to unconditionally disable Suno even if a URL remains in the text field.</div>
          <div>• <b>🎨 Reference Images & style_target Have 100% Priority</b>: <code>song_style_tags</code> in <b>[12]</b> never overrides your reference images from <b>[13]/[01]</b> or <code>style_target</code> in <b>[02] Timeline Compiler</b>.</div>
          <div>• <b>🔗 Suno Link (v3–v5.5) & Whisper ASR</b>: Paste any <code>suno.com/s/...</code> link for 48 kHz Stereo Master download + local Whisper speech transcription.</div>
        </div>`,
        models: `<div style="display:flex;flex-direction:column;gap:6px;">
          <div><b style="color:#fbbf24;">💎 3. PRISM ORTHOGONAL SVD, MODELS, VAE, CLIP, LORAS &amp; HUGGINGFACE ([03]–[10])</b></div>
          <div>• <b style="color:#34d399;">📦 Official HuggingFace Vault (MiniMax H3)</b>: <a href="https://huggingface.co/DeepBeepMeep/MiniMax-H3/tree/main" target="_blank" rel="noopener noreferrer" style="color:#38bdf8;text-decoration:underline;">https://huggingface.co/DeepBeepMeep/MiniMax-H3/tree/main</a> (LoRAs: <a href="https://huggingface.co/DeepBeepMeep/MiniMax-H3/tree/main/loras" target="_blank" rel="noopener noreferrer" style="color:#38bdf8;text-decoration:underline;">/loras</a>).</div>
          <div>• <b style="color:#22d3ee;">🏛️ Top Video UNets (16 GB+)</b>: <b>#1 Realism/NSFW (Baked Turbo=OFF)</b>: <code>10Eros_Max_SingularityV2_PRISM2_PikaFlex_0.85_int8HQ.safetensors</code> | <b>#2 Blackwell NVFP4 (13.8 GB, Baked Turbo=OFF)</b>: <code>FastH3-Omni-NVFP4-QAD-pruned_rank8_nvfp4.safetensors</code> | <b>#3 Non-Turbo (Turbo LoRA=ON)</b>: <code>h3ErosMax_beta5_3185154.safetensors</code> | <b>Ref2VA</b>: <code>dasiwa_ref2va_v5xs</code> / <code>Minimax-h3_Singularity_ref2va_v2_pruned_int8_convrot.safetensors</code>.</div>
          <div>• <b style="color:#facc15;">🧩 Best CLIP, Video VAE &amp; Audio VAE in [05]</b>: <b>CLIP (<code>minimax</code>)</b> = <code>qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors</code> | <b>Video VAE (16-bit, zero contrast drift!)</b> = <code>MiniMax-H3-video_vae_fp16.safetensors</code> (<code>5.21 GB</code>, replaces <code>int8_convrot</code>!) | <b>Audio VAE</b> = <code>MiniMax-H3-audio_vae_fp32.safetensors</code> (<code>605 MB</code>).</div>
          <div>• <b style="color:#f0abfc;">⚡ Top Video LoRAs (<code>/loras</code>)</b>: <b>#1 Best Turbo LoRA (Non-Turbo UNets only)</b> = <code>minimax_h3_dmad_8step_full_critic_lora_bf16.safetensors</code> (<code>1.38 GB</code>) | <b>#2 Sharpness/Micro-Detail (all UNets @ 0.20–0.30)</b> = <code>minimax_h3_lms_v1.0_r64.safetensors</code> | <b>#3 Motion</b> = <code>H3_VBVR_Pro_attn_only.safetensors</code> (<code>0.35–0.45</code>).</div>
          <div>• <b style="color:#38bdf8;">💎 PRISM Multi-LoRA Orthogonalization &amp; Turbo-Shield ([03], [05], [10])</b>: Projects secondary &amp; Turbo LoRAs orthogonally away from <code>Slot 1</code> + Smart Lazy-Loading (<code>0 MB extra VRAM</code> for inactive <code>FL2VA/REF2VA</code> slot).</div>
        </div>`,
        upscale: `<div style="display:flex;flex-direction:column;gap:6px;">
          <div><b style="color:#f472b6;">🚀 4. EDGE-DIRECTED LANCZOS + MULTI-SCALE RESTORER, 4x➔2x SUPERSAMPLING & RIFE IFNet ([04] & [08])</b></div>
          <div>• <b>🔬 Pass 1 (0 MB VRAM): Edge-Directed Lanczos + Multi-Scale High-Pass Restorer</b> in <b>[04]</b> &amp; <b>[08]</b> restores sub-pixel micro-details (<code>sigma=0.85/2.1</code>) with anti-halo clipping.</div>
          <div>• <b>✨ Pass 2: 100% KeypointRCNN 6-Zone Skeletal Shield + Native RIFE v4.7/v4.9 IFNet (rife49.pth / rife47.pth)</b>.</div>
          <div>• <b style="color:#34d399;">🏆 Best 3-Stage Master Chain in [08]</b>: <b>4x-ClearRealityV1.pth</b> (4x➔2x) + <b>1x-ITF-SkinDiffDetail-Lite-v1.pth</b> (45% blend) + <code>enable_frequency_polish = true</code>.</div>
        </div>`,
        tips: `<div style="display:flex;flex-direction:column;gap:6px;">
          <div><b style="color:#34d399;">💡 5. KREA 2 FINE-TUNING ([02]–[04]), 100% RATING &amp; AGE AUTHORITY, ANTI-GHOSTING &amp; PRISM ([07])</b></div>
          <div>• <b style="color:#fbbf24;">🎛️ Fine-Tuning in EZ [04] (handoff_percent, stage3_handoff &amp; i2i_denoise in 0.01 steps)</b>: Set <code>handoff_percent = 56.00–62.00%</code> and <code>stage3_handoff_percent = 88.00–92.00%</code> (with 16-channel spatial alignment &amp; 5-finger anti-ghosting lock). <code>i2i_denoise</code> steps in <b>0.01</b> increments (<code>0.70–0.78</code> = balanced photorealism &amp; bidirectional strap/gap lock).</div>
          <div>• <b style="color:#38bdf8;">🛡️ 100% Node Authority for content_rating_mode &amp; subject_1_age in [02] &amp; [06]</b>: Selecting <code>Uncensored Artistic / Action</code> preserves dark-fantasy action, cleavage, and separated loincloth straps while scrubbing unrequested explicit exposure clauses.</div>
          <div>• <b style="color:#22d3ee;">🎥 3-Axis Director (Backward Track &amp; Outro Track ➔ Follow) ([02], [06], [07])</b> &amp; <b style="color:#f0abfc;">💎 PRISM Latent Spectral Lock in [07]</b>.</div>
        </div>`,
        basics: `<div style="display:flex;flex-direction:column;gap:6px;">
          <div><b style="color:#38bdf8;">🎓 7. BASICS — COMFYUI, MODEL TYPES, LORA/DORA & PRISM MODEL FOUNDRY</b></div>
          <div>• <b>🏛️ EZ Model Foundry & LoRA Lab (in DevOps Studio)</b>: 5 stations for Dataset Curation, LoRA/DoRA Training, <b>Gold Epoch</b> selection via PRISM Effective Rank Entropy &amp; Condition Number, <b>PRISM SVD Tail Denoising</b>, and <b>PRISM Orthogonal SVD Merge</b> + <code>Int8 ConvRot</code> / <code>NVFP4</code> quantization.</div>
          <div>• <b>📦 python_embedded &amp; requirements.txt</b>: 3-tier hardware acceleration (<code>PyTorch cuSOLVER</code> ➔ <code>SciPy/NumPy LAPACK gesdd</code> ➔ <code>Pure-Python Gram-Schmidt</code>) synced with <code>scipy>=1.11.0</code>, <code>numpy>=1.26.0</code>, <code>safetensors>=0.4.3</code>, and <code>Pillow>=10.3.0</code>.</div>
        </div>`,
        customLabel: "📝 Custom Project Scratchpad (Synced live with custom_notes widget):"
    },
    JA: {
        title: "📝 EZ [11] スタジオノート・操作ガイド & モデルハンドブック ([01]➔[13])",
        openWindowBtn: "🗖 ハンドブックウィンドウを開く",
        tabs: { all: "📚 すべて", howto: "🗺️ 配線 & [13]", suno: "🎵 Suno & 音声 [12]", models: "💎 PRISM & LoRA", upscale: "🚀 Lanczos & 超解像", tips: "🎥 Krea2微調整 & カメラ", basics: "🎓 基礎 & Foundry", custom: "📝 メモ" },
        howto: `<div><b style="color:#22d3ee;">🗺️ 1. 配線ガイド & 解像度ルーティング ([01] ➔ [13])</b><br/>• <b>[01]</b> の <code>final_width/final_height</code> を <b>[06]</b> の <code>video_width/video_height</code> に接続してください (<code>base_width/base_height</code> は <b>[03]</b> と <b>[04]</b> のみ)。</div>`,
        suno: `<div><b style="color:#f0abfc;">🎵 2. EZ [12] SUNOミュージックビデオ・BYPASS & WHISPER音声認識</b><br/>• <code>Bypass / Off</code> を選択するとSunoを完全にバイパスします。</div>`,
        models: `<div><b style="color:#fbbf24;">💎 3. PRISM 直交SVD・TURBO-SHIELD & MINIMAX H3</b><br/>• <b>[03]</b> と <b>[05]</b> でサブLoRAおよびTurbo LoRAをメインLoRAと直交投影し、肌の毛穴と顔立ちを100%保護します。</div>`,
        upscale: `<div><b style="color:#f472b6;">🚀 4. エッジ指向LANCZOS・4x➔2x超解像 & RIFE IFNet ([04] & [08])</b><br/>• <b>推奨構成</b>: <code>4x-ClearRealityV1.pth</code> + <code>1x-ITF-SkinDiffDetail-Lite-v1.pth</code> + <code>enable_frequency_polish = true</code>。</div>`,
        tips: `<div><b style="color:#34d399;">💡 5. KREA 2 微調整 ([02]–[04])・100%モード/年齢権限・ゴースト防止 &amp; PRISM ([07])</b><br/>• <b>[04]</b> の <code>handoff_percent</code> (<code>56.00〜62.00%</code>)、<code>stage3_handoff_percent</code> (<code>88.00〜92.00%</code>)、<code>i2i_denoise</code> (<code>0.70〜0.78</code>) はすべて <b>0.01刻み</b> で微調整可能。16チャンネル空間アライメントにより二重輪郭のゴーストや6本指の破綻を防止します。</div>`,
        basics: `<div><b style="color:#38bdf8;">🎓 7. BASICS & PRISM MODEL FOUNDRY</b><br/>• DevOps Studio内のPRISM SVD Model Foundry &amp; LoRA Lab (<code>python_embedded</code> 自動同期)。</div>`,
        customLabel: "📝 カスタムプロジェクトメモ (custom_notes とリアルタイム同期):"
    },
    ES: {
        title: "📝 EZ [11] NOTAS DE ESTUDIO, GUÍA HOW-TO Y MODELOS ([01]➔[13])",
        openWindowBtn: "🗖 ABRIR MANUAL",
        tabs: { all: "📚 Todo", howto: "🗺️ How-To", suno: "🎵 Suno y Voz [12]", models: "💎 PRISM y LoRA", upscale: "🚀 Lanczos y 4x/1x", tips: "🎥 Ajuste y Cámara", basics: "🎓 Basics y Foundry", custom: "📝 Notas" },
        howto: `<div><b style="color:#22d3ee;">🗺️ 1. GUÍA DE CONEXIÓN Y RESOLUCIÓN ([01] ➔ [13])</b><br/>• Conecta <code>final_width/final_height</code> de <b>[01]</b> a <code>video_width/video_height</code> en <b>[06]</b> (<code>base_width/base_height</code> solo van a <b>[03]</b> y <b>[04]</b>).</div>`,
        suno: `<div><b style="color:#f0abfc;">🎵 2. EZ [12] SUNO MUSIC VIDEO, BYPASS Y WHISPER ASR</b><br/>• Selecciona <code>Bypass / Off</code> para desactivar Suno por completo.</div>`,
        models: `<div><b style="color:#fbbf24;">💎 3. PRISM ORTOGONAL SVD, TURBO-SHIELD Y MINIMAX H3</b><br/>• Proyecta los LoRAs secundarios y los Turbo-LoRAs ortogonalmente lejos del LoRA principal en <b>[03]</b> y <b>[05]</b>.</div>`,
        upscale: `<div><b style="color:#f472b6;">🚀 4. LANCZOS DIRIGIDO POR BORDES, 4x➔2x, 1x PIEL Y RIFE IFNet ([04] & [08])</b><br/>• <b>Recomendado</b>: <code>4x-ClearRealityV1.pth</code> + <code>1x-ITF-SkinDiffDetail-Lite-v1.pth</code> + <code>enable_frequency_polish = true</code>.</div>`,
        tips: `<div><b style="color:#34d399;">💡 5. AJUSTE FINO KREA 2 ([02]–[04]), EDAD, CÁMARA Y PRISM ([07])</b><br/>• En <b>[04]</b> usa <code>handoff_percent = 58.0–65.0%</code> y ajusta <code>i2i_denoise</code> en pasos de <b>0.01</b> (<code>0.70–0.78</code> equilibra fotorrealismo y bloqueo de 5 dedos).</div>`,
        basics: `<div><b style="color:#38bdf8;">🎓 7. BASICS Y PRISM MODEL FOUNDRY</b><br/>• Laboratorio PRISM SVD en DevOps Studio con sincronización en <code>python_embedded</code> (<code>scipy</code>, <code>numpy</code>, <code>safetensors</code>).</div>`,
        customLabel: "📝 Notas del Proyecto (Sincronizadas con custom_notes):"
    },
    DE: {
        title: "📝 EZ [11] STUDIO-NOTIZEN, HOW-TO & MODELL-HANDBUCH ([01]➔[13])",
        openWindowBtn: "🗖 HANDBUCH ÖFFNEN",
        tabs: { all: "📚 Alle", howto: "🗺️ How-To", suno: "🎵 Suno & Sprache [12]", models: "💎 PRISM & LoRA", upscale: "🚀 Lanczos & 4x/1x", tips: "🎥 Tuning & Kamera", basics: "🎓 Basics & Foundry", custom: "📝 Notizen" },
        howto: `<div><b style="color:#22d3ee;">🗺️ 1. VERKABELUNGSGUIDE & AUFLÖSUNG ([01] ➔ [13])</b><br/>• <code>final_width/final_height</code> aus <b>[01]</b> mit <code>video_width/video_height</code> in <b>[06]</b> verbinden (<code>base_width/base_height</code> nur an <b>[03]</b> und <b>[04]</b>).</div>`,
        suno: `<div><b style="color:#f0abfc;">🎵 2. EZ [12] SUNO MUSIC VIDEO, BYPASS & WHISPER ASR</b><br/>• <code>Bypass / Off</code> deaktiviert Suno vollständig.</div>`,
        models: `<div><b style="color:#fbbf24;">💎 3. PRISM ORTHOGONALE SVD, TURBO-SHIELD & MINIMAX H3</b><br/>• Projiziert sekundäre LoRAs und Turbo-LoRAs orthogonal weg vom Haupt-LoRA in <b>[03]</b> und <b>[05]</b>.</div>`,
        upscale: `<div><b style="color:#f472b6;">🚀 4. KANTENGESTEUERTER LANCZOS, 4x➔2x, 1x HAUT & ECHTES RIFE IFNet ([04] & [08])</b><br/>• <b>Empfohlen</b>: <code>4x-ClearRealityV1.pth</code> + <code>1x-ITF-SkinDiffDetail-Lite-v1.pth</code> + <code>enable_frequency_polish = true</code>.</div>`,
        tips: `<div><b style="color:#34d399;">💡 5. KREA 2 FEINABSTIMMUNG ([02]–[04]), ALTER, KAMERA &amp; PRISM ([07])</b><br/>• Nutze in <b>[04]</b> <code>handoff_percent = 58.0–65.0%</code> und <code>i2i_denoise</code> in <b>0.01-Schritten</b> (<code>0.70–0.78</code> für Fotorealismus &amp; 5-Finger-Schutz).</div>`,
        basics: `<div><b style="color:#38bdf8;">🎓 7. BASICS & PRISM MODEL FOUNDRY</b><br/>• PRISM SVD Model Foundry &amp; LoRA Lab mit automatischer <code>python_embedded</code> Synchronisierung (<code>scipy</code>, <code>numpy</code>, <code>safetensors</code>).</div>`,
        customLabel: "📝 Eigene Projektnotizen (Live synchronisiert mit custom_notes):"
    },
    FR: {
        title: "📝 EZ [11] NOTES STUDIO, GUIDE HOW-TO & MODÈLES ([01]➔[13])",
        openWindowBtn: "🗖 OUVRIR LE MANUEL",
        tabs: { all: "📚 Tout", howto: "🗺️ How-To", suno: "🎵 Suno & Voix [12]", models: "💎 PRISM & LoRA", upscale: "🚀 Lanczos & 4x/1x", tips: "🎥 Réglage & Caméra", basics: "🎓 Basics & Foundry", custom: "📝 Notes" },
        howto: `<div><b style="color:#22d3ee;">🗺️ 1. GUIDE DE CÂBLAGE & RÉSOLUTION ([01] ➔ [13])</b><br/>• Connectez <code>final_width/final_height</code> de <b>[01]</b> à <code>video_width/video_height</code> sur <b>[06]</b> (<code>base_width/base_height</code> uniquement sur <b>[03]</b> et <b>[04]</b>).</div>`,
        suno: `<div><b style="color:#f0abfc;">🎵 2. EZ [12] SUNO MUSIC VIDEO, BYPASS & WHISPER ASR</b><br/>• <code>Bypass / Off</code> désactive Suno.</div>`,
        models: `<div><b style="color:#fbbf24;">💎 3. SVD ORTHOGONALE PRISM, TURBO-SHIELD & MINIMAX H3</b><br/>• Projette les LoRAs secondaires et les Turbo-LoRAs orthogonalement au LoRA principal dans <b>[03]</b> et <b>[05]</b>.</div>`,
        upscale: `<div><b style="color:#f472b6;">🚀 4. LANCZOS DIRIGÉ PAR LES BORDS, 4x➔2x, 1x PEAU & RIFE IFNet ([04] & [08])</b><br/>• <b>Recommandé</b>: <code>4x-ClearRealityV1.pth</code> + <code>1x-ITF-SkinDiffDetail-Lite-v1.pth</code> + <code>enable_frequency_polish = true</code>.</div>`,
        tips: `<div><b style="color:#34d399;">💡 5. RÉGLAGE FIN KREA 2 ([02]–[04]), ÂGE, CAMÉRA &amp; PRISM ([07])</b><br/>• Dans <b>[04]</b>, réglez <code>handoff_percent = 58.0–65.0%</code> et <code>i2i_denoise</code> par pas de <b>0.01</b> (<code>0.70–0.78</code> pour photoréalisme et protection à 5 doigts).</div>`,
        basics: `<div><b style="color:#38bdf8;">🎓 7. BASICS & PRISM MODEL FOUNDRY</b><br/>• Laboratoire PRISM SVD dans DevOps Studio avec synchronisation <code>python_embedded</code> (<code>scipy</code>, <code>numpy</code>, <code>safetensors</code>).</div>`,
        customLabel: "📝 Notes du Projet (Synchronisées avec custom_notes) :"
    },
    ZH: {
        title: "📝 EZ [11] 工作室笔记、操作指南与模型手册 ([01]➔[13])",
        openWindowBtn: "🗖 打开完整手册窗口",
        tabs: { all: "📚 全部", howto: "🗺️ 连线指南", suno: "🎵 Suno与语音 [12]", models: "💎 PRISM与LoRA", upscale: "🚀 边缘Lanczos与超分", tips: "🎥 Krea2精调与镜头", basics: "🎓 新手与Foundry", custom: "📝 笔记" },
        howto: `<div><b style="color:#22d3ee;">🗺️ 1. 节点连线与分辨率指南 ([01] ➔ [13])</b><br/>• 将 <b>[01]</b> 的 <code>final_width/final_height</code> 连接至 <b>[06]</b> 的 <code>video_width/video_height</code> (<code>base_width/base_height</code> 仅连接至 <b>[03]</b> 与 <b>[04]</b>)。</div>`,
        suno: `<div><b style="color:#f0abfc;">🎵 2. EZ [12] SUNO 音乐视频、BYPASS 与 WHISPER 语音识别</b><br/>• 选择 <code>Bypass / Off</code> 可完全旁路 Suno。</div>`,
        models: `<div><b style="color:#fbbf24;">💎 3. PRISM 正交 SVD、TURBO-SHIELD 与 MINIMAX H3</b><br/>• 在 <b>[03]</b> 与 <b>[05]</b> 中将副槽位 LoRA 与 Turbo LoRA 正交投影至主角色/解剖 LoRA 子空间之外。</div>`,
        upscale: `<div><b style="color:#f472b6;">🚀 4. 边缘导向 LANCZOS、4x➔2x 超采样与原生 RIFE IFNet ([04] & [08])</b><br/>• <b>最佳写实组合</b>: <code>4x-ClearRealityV1.pth</code> + <code>1x-ITF-SkinDiffDetail-Lite-v1.pth</code> + <code>enable_frequency_polish = true</code>。</div>`,
        tips: `<div><b style="color:#34d399;">💡 5. KREA 2 三阶段精调 ([02]–[04])、100%分级与年龄权威、防重影五指锁与 PRISM ([07])</b><br/>• 在 <b>[04]</b> 中 <code>handoff_percent</code> (<code>56.00–62.00%</code>)、<code>stage3_handoff_percent</code> (<code>88.00–92.00%</code>) 与 <code>i2i_denoise</code> (<code>0.70–0.78</code>) 均支持 <b>0.01 步进</b>，配合 16 通道空间对齐彻底消除重影与多指畸变。</div>`,
        basics: `<div><b style="color:#38bdf8;">🎓 7. 新手指南与 PRISM MODEL FOUNDRY</b><br/>• DevOps Studio 内置 PRISM 模型与 LoRA 实验室，自动同步 <code>python_embedded</code> (<code>scipy</code>, <code>numpy</code>, <code>safetensors</code>)。</div>`,
        customLabel: "📝 自定义项目笔记 (与 custom_notes 实时同步):"
    }
};

function collapseEzStudioNoteNativeWidgets(node, hideRaw = true) {
    if (!node || !Array.isArray(node.widgets)) return;
    node.widgets.forEach(w => {
        if (!w || w.name === "ez_studio_note_handbook") return;
        if (!w._ezOrigType) {
            w._ezOrigType = w.type;
            w._ezOrigComputeSize = w.computeSize;
            w._ezOrigDraw = w.draw;
        }
        if (hideRaw) {
            w.type = "converted-widget";
            w.computeSize = () => [0, -4];
            w.draw = () => {};
        } else {
            w.type = w._ezOrigType;
            if (w._ezOrigComputeSize) w.computeSize = w._ezOrigComputeSize;
            else delete w.computeSize;
            if (w._ezOrigDraw) w.draw = w._ezOrigDraw;
            else delete w.draw;
        }
    });
    if (app.graph) app.graph.setDirtyCanvas(true, true);
}

function _mapTopicPresetToTab(presetVal) {
    const v = String(presetVal || "").toLowerCase();
    if (v.startsWith("0.") || v.startsWith("alla") || v.includes("komplett") || v.includes("all_chapters")) return "all";
    if (v.startsWith("1.") || v.includes("auto-wire") || v.includes("wiring")) return "howto";
    if (v.startsWith("2.") || v.includes("suno")) return "suno";
    if (v.startsWith("3.") || v.includes("prism svd") || v.includes("multi-model") || v.includes("multi_model")) return "models";
    if (v.startsWith("4.") || v.includes("upscale")) return "upscale";
    if (v.startsWith("5.") || v.includes("spektral") || v.includes("sfw")) return "tips";
    if (v.startsWith("6.") && v.includes("omni")) return "omniref";
    if (v.startsWith("7.") && v.includes("basics")) return "basics";
    if (v.startsWith("7.") || v.startsWith("8.") || v.includes("anteckningar")) return "custom";
    return "all";
}

function _mapTabToTopicPreset(tabKey) {
    const map = {
        all: "Alla Guider & Modell-Tips (Komplett Studio-Handbok [01]➔[13])",
        howto: "1. How-To, 1-Klicks Auto-Wire & Kopplingsguide ([01] ➔ [13])",
        suno: "2. Suno [12], Taligenkänning (Whisper ASR), Auto-Prompt & Längd-Synk",
        models: "3. Modell-, PRISM SVD- & LoRA-Tips (Krea 2, Pony, Illustrious, MiniMax H3, Turbo-Shield)",
        upscale: "4. Upscale, Kantstyrd Lanczos, 4x➔2x Supersampling, 1x Hud & RIFE IFNet",
        tips: "5. PRISM Spektrallås, Statisk/Dynamisk Kamera, 20s/30s+ Kontinuitet & SFW-Lås",
        omniref: "6. EZ [13] Omni-Reference Load Image & Control Studio (4-Slots, Inpaint, ReActor, OOTD)",
        basics: "7. Basics — Nybörjarguide (ComfyUI, Modeller, LoRA/DoRA, PRISM Foundry & Resursfiler)",
        custom: "8. Endast Egna Anteckningar (Custom Markdown)",
        compiled: "Alla Guider & Modell-Tips (Komplett Studio-Handbok [01]➔[13])"
    };
    return map[tabKey] || null;
}

function _formatNoteMarkdownToHtml(mdText, searchQuery = "", isModal = false) {
    const raw = String(mdText || "").trim();
    if (!raw) return `<div style="color:#94a3b8;">Ingen manualtext tillgänglig.</div>`;
    let safe = raw
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
    safe = safe
        .replace(/^###\s+(.+)$/gm, `<div style="font-size:${isModal ? "14px" : "11px"};font-weight:bold;color:#22d3ee;margin:8px 0 4px 0;border-bottom:1px solid #1e293b;padding-bottom:3px;">$1</div>`)
        .replace(/^##\s+(.+)$/gm, `<div style="font-size:${isModal ? "15px" : "11.5px"};font-weight:bold;color:#facc15;margin:10px 0 5px 0;">$1</div>`)
        .replace(/\*\*([^*]+)\*\*/g, `<b style="color:#f8fafc;">$1</b>`)
        .replace(/`([^`]+)`/g, (m, codeTxt) => {
            if (/^https?:\/\//i.test(codeTxt.trim())) {
                const url = codeTxt.trim();
                return `<a href="${url}" target="_blank" rel="noopener noreferrer" style="background:#0c1424;color:#38bdf8;border:1px solid #1e293b;border-radius:3px;padding:1px 5px;font-family:monospace;text-decoration:underline;">${url}</a>`;
            }
            return `<code style="background:#0c1424;color:#38bdf8;border:1px solid #1e293b;border-radius:3px;padding:1px 4px;font-family:monospace;">${codeTxt}</code>`;
        })
        .replace(/^\s*•\s+(.+)$/gm, `<div style="padding-left:10px;margin:2px 0;">• $1</div>`)
        .replace(/^\s*-\s+(.+)$/gm, `<div style="padding-left:10px;margin:2px 0;">• $1</div>`)
        .replace(/^\s*\*\s+(.+)$/gm, `<div style="padding-left:10px;margin:2px 0;">• $1</div>`)
        .replace(/\n/g, "<br/>");
    const q = String(searchQuery || "").trim();
    if (q.length >= 2) {
        try {
            const escQ = q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
            const re = new RegExp(`(${escQ})`, "gi");
            safe = safe.replace(re, `<mark style="background:#facc15;color:#000;padding:0 2px;border-radius:2px;font-weight:bold;">$1</mark>`);
        } catch (e) {}
    }
    return safe;
}

const EZ_SWITCHBOARD_GROUPS = {
    enable_qwenvl_compiler_02: ["EZCinematrixQwenVLTimelineCompiler"],
    enable_krea2_image_03_04: [
        "EZCinematrixImageModelAndLoraSplitter",
        "EZCinematrixKrea2ThreeStageSampler",
        "EZCinematrixKrea2DualStageSampler"
    ],
    enable_minimax_video_05_08: [
        "EZCinematrixVideoEngineAndLoraStack",
        "EZCinematrixVideoDirectorAndGuide",
        "EZCinematrixJointAVTemporalSampler",
        "EZCinematrixCinemaVaultPostAndCombine"
    ],
    enable_suno_music_12: ["EZCinematrixSunoMusicVideoStudio"],
    enable_omni_reference_13: ["EZCinematrixOmniReferenceLoader"],
    enable_anatomy_dock_09: ["EZCinematrixNeuralAnatomyContinuityDock"]
};

function syncEzSwitchboardToGraph(node) {
    if (!node || !app.graph || !Array.isArray(app.graph._nodes)) return { active: 0, bypassed: 0 };
    const getW = (name) => Array.isArray(node.widgets) ? node.widgets.find(w => w && w.name === name) : null;
    const wMode = getW("pipeline_execution_mode");
    const wKrea = getW("enable_krea2_image_03_04");
    const wVid = getW("enable_minimax_video_05_08");
    const wBehav = getW("bypass_behavior");

    const modeStr = String(wMode ? wMode.value : "").toLowerCase();
    if (modeStr.startsWith("image_only") || modeStr.includes("endast bild")) {
        if (wKrea) wKrea.value = true;
        if (wVid) wVid.value = false;
    } else if (modeStr.startsWith("video_only") || modeStr.includes("endast video")) {
        if (wKrea) wKrea.value = false;
        if (wVid) wVid.value = true;
    } else if (modeStr.startsWith("full_studio") || modeStr.includes("full studio")) {
        if (wKrea) wKrea.value = true;
        if (wVid) wVid.value = true;
    }

    const useMute = String(wBehav ? wBehav.value : "").toLowerCase().startsWith("mute_mode_2");
    const offMode = useMute ? 2 : 4;
    let activeCount = 0;
    let bypassedCount = 0;

    const swEdition = detectEzNodeEdition(node);
    for (const [wName, clsList] of Object.entries(EZ_SWITCHBOARD_GROUPS)) {
        const wToggle = getW(wName);
        const isEnabled = wToggle ? Boolean(wToggle.value) : true;
        const targetMode = isEnabled ? 0 : offMode;
        for (const gNode of app.graph._nodes) {
            if (!gNode || gNode === node) continue;
            if (detectEzNodeEdition(gNode) !== swEdition) continue;
            if (clsList.includes(stripEzEditionSuffix(gNode.type))) {
                gNode.mode = targetMode;
                if (isEnabled) activeCount++;
                else bypassedCount++;
            }
        }
    }
    app.graph.setDirtyCanvas(true, true);
    if (typeof node._ezRefreshSwitchboardDom === "function") {
        node._ezRefreshSwitchboardDom(activeCount, bypassedCount, offMode);
    }
    return { active: activeCount, bypassed: bypassedCount };
}

function mountEzPipelineSwitchboardWidget(node) {
    if (!node || node._ezSwitchboardMounted) return;
    node._ezSwitchboardMounted = true;

    const getW = (name) => Array.isArray(node.widgets) ? node.widgets.find(w => w && w.name === name) : null;
    const setPresetChoice = (prefix) => {
        const wMode = getW("pipeline_execution_mode");
        if (!wMode) return;
        const vals = (wMode.options && Array.isArray(wMode.options.values)) ? wMode.options.values : [];
        const match = vals.find(v => String(v).toLowerCase().startsWith(prefix));
        wMode.value = match || prefix;
    };

    if (Array.isArray(node.widgets)) {
        for (const w of node.widgets) {
            if (!w || w._ezSwBound) continue;
            w._ezSwBound = true;
            const origCb = w.callback;
            w.callback = function () {
                if (w.name === "enable_krea2_image_03_04" || w.name === "enable_minimax_video_05_08") {
                    setPresetChoice("custom_manual_switches");
                }
                if (origCb) origCb.apply(this, arguments);
                syncEzSwitchboardToGraph(node);
            };
        }
    }

    const wrap = document.createElement("div");
    wrap.style.cssText = "background:transparent;border:none;padding:0;margin:0;overflow:visible;box-sizing:border-box;user-select:none;width:100%;";
    forwardRightClickToNode(wrap, node);

    const innerBox = document.createElement("div");
    innerBox.style.cssText = "background:#0b0d14;border:1.5px solid #a855f7;border-radius:8px;padding:10px 10px 12px 10px;font-family:monospace;color:#e2e8f0;display:flex;flex-direction:column;gap:7px;box-sizing:border-box;width:100%;height:max-content;box-shadow:0 4px 14px rgba(0,0,0,0.45);";
    wrap.appendChild(innerBox);

    const titleRow = document.createElement("div");
    titleRow.style.cssText = "display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #1e293b;padding-bottom:5px;";
    const titleSpan = document.createElement("span");
    titleSpan.style.cssText = "color:#c084fc;font-weight:bold;font-size:11px;";
    titleSpan.textContent = "🎛️ PIPELINE REMOTE SWITCHBOARD";
    const statusBadge = document.createElement("span");
    statusBadge.style.cssText = "font-size:10px;padding:1px 6px;border-radius:4px;background:#1e1b4b;color:#e9d5ff;border:1px solid #7e22ce;";
    statusBadge.textContent = "READY";
    titleRow.appendChild(titleSpan);
    titleRow.appendChild(statusBadge);
    innerBox.appendChild(titleRow);

    const presetRow = document.createElement("div");
    presetRow.style.cssText = "display:grid;grid-template-columns:repeat(3,1fr);gap:6px;";
    const presets = [
        { key: "image_only", label: "🖼️ IMAGE ONLY", sub: "[03-04] ON | Video OFF", krea: true, vid: false },
        { key: "full_studio", label: "🎬 FULL STUDIO", sub: "Image + Video + Audio", krea: true, vid: true },
        { key: "video_only", label: "🎞️ VIDEO ONLY", sub: "Direct I2V | Skip [03-04]", krea: false, vid: true }
    ];
    const presetBtns = {};
    for (const p of presets) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.style.cssText = "background:#131722;border:1px solid #334155;border-radius:6px;padding:6px 4px;cursor:pointer;color:#e2e8f0;display:flex;flex-direction:column;align-items:center;gap:2px;font-family:monospace;";
        btn.innerHTML = `<span style="font-size:10.5px;font-weight:bold;">${p.label}</span><span style="font-size:8.5px;color:#94a3b8;">${p.sub}</span>`;
        btn.onclick = () => {
            setPresetChoice(p.key);
            const wKrea = getW("enable_krea2_image_03_04");
            const wVid = getW("enable_minimax_video_05_08");
            if (wKrea) wKrea.value = p.krea;
            if (wVid) wVid.value = p.vid;
            syncEzSwitchboardToGraph(node);
        };
        presetBtns[p.key] = btn;
        presetRow.appendChild(btn);
    }
    innerBox.appendChild(presetRow);

    const modGrid = document.createElement("div");
    modGrid.style.cssText = "display:grid;grid-template-columns:repeat(3,1fr);gap:6px;";
    const modSpecs = [
        { wName: "enable_qwenvl_compiler_02", label: "🧠 [02] Qwen3-VL" },
        { wName: "enable_krea2_image_03_04", label: "🎨 [03-04] Krea 2" },
        { wName: "enable_minimax_video_05_08", label: "🎬 [05-08] Video" },
        { wName: "enable_suno_music_12", label: "🎵 [12] Suno Music" },
        { wName: "enable_omni_reference_13", label: "🖼️ [13] Omni-Ref" },
        { wName: "enable_anatomy_dock_09", label: "🦴 [09] Anatomy" }
    ];
    const modBtns = {};
    for (const m of modSpecs) {
        const b = document.createElement("button");
        b.type = "button";
        b.style.cssText = "border-radius:5px;padding:6px 7px;cursor:pointer;font-family:monospace;font-size:10px;font-weight:bold;display:flex;justify-content:space-between;align-items:center;border:1px solid #334155;";
        b.onclick = () => {
            const w = getW(m.wName);
            if (w) {
                w.value = !Boolean(w.value);
                if (m.wName === "enable_krea2_image_03_04" || m.wName === "enable_minimax_video_05_08") {
                    setPresetChoice("custom_manual_switches");
                }
                syncEzSwitchboardToGraph(node);
            }
        };
        modBtns[m.wName] = { btn: b, label: m.label };
        modGrid.appendChild(b);
    }
    innerBox.appendChild(modGrid);

    node._ezRefreshSwitchboardDom = (activeCnt, bypassedCnt, offMode) => {
        const wK = getW("enable_krea2_image_03_04");
        const wV = getW("enable_minimax_video_05_08");
        const kOn = wK ? Boolean(wK.value) : true;
        const vOn = wV ? Boolean(wV.value) : true;
        const activePreset = (kOn && !vOn) ? "image_only" : ((!kOn && vOn) ? "video_only" : ((kOn && vOn) ? "full_studio" : "custom"));
        for (const [k, btn] of Object.entries(presetBtns)) {
            const isSel = k === activePreset;
            btn.style.background = isSel ? "linear-gradient(135deg,#581c87,#1e1b4b)" : "#131722";
            btn.style.borderColor = isSel ? "#c084fc" : "#334155";
            btn.style.boxShadow = isSel ? "0 0 10px rgba(192,132,252,0.35)" : "none";
        }
        const offLbl = offMode === 2 ? "MUTE" : "BYPASS";
        for (const [wName, info] of Object.entries(modBtns)) {
            const w = getW(wName);
            const isOn = w ? Boolean(w.value) : true;
            info.btn.style.background = isOn ? "rgba(16,185,129,0.16)" : "rgba(168,85,247,0.16)";
            info.btn.style.borderColor = isOn ? "#10b981" : "#a855f7";
            info.btn.style.color = isOn ? "#6ee7b7" : "#d8b4fe";
            info.btn.innerHTML = `<span>${info.label}</span><span style="font-size:9px;padding:1px 4px;border-radius:3px;background:${isOn ? "#065f46" : "#581c87"};color:#fff;">${isOn ? "ON" : offLbl}</span>`;
        }
        statusBadge.textContent = `ACTIVE: ${activeCnt} | ${offLbl}: ${bypassedCnt}`;
    };

    if (typeof node.addDOMWidget === "function") {
        const domW = node.addDOMWidget("ez_switchboard_remote_ui", "div", wrap, {
            serialize: false,
            hideOnZoom: false
        });
        domW.computeSize = (width) => [Math.max(420, width - 20), 192];
    }
    if (Array.isArray(node.size)) {
        node.size[0] = Math.max(node.size[0] || 520, 520);
        node.size[1] = Math.max(node.size[1] || 470, 470);
    }
    setTimeout(() => syncEzSwitchboardToGraph(node), 120);
}

function mountEzStudioNoteWidget(node, execMeta = null) {
    if (!node) return;
    if (!node._ezStudioNoteState) {
        const wTopic = Array.isArray(node.widgets) ? node.widgets.find(w => w.name === "topic_preset") : null;
        node._ezStudioNoteState = {
            activeTab: wTopic ? _mapTopicPresetToTab(wTopic.value) : "all",
            telemetry: "",
            compiledGuideText: "",
            serverChapters: null,
            allLocalesChapters: null,
            searchQuery: "",
            showRawWidgets: false,
            modalFullscreen: false,
            copyNotice: ""
        };
        collapseEzStudioNoteNativeWidgets(node, true);
    }
    const st = node._ezStudioNoteState;
    if (execMeta) {
        if (execMeta.telemetry_summary) st.telemetry = execMeta.telemetry_summary;
        if (execMeta.compiled_markdown || execMeta.compiled_guide_text) {
            st.compiledGuideText = execMeta.compiled_markdown || execMeta.compiled_guide_text;
        }
        if (execMeta.chapters) st.serverChapters = execMeta.chapters;
        if (execMeta.all_locales) st.allLocalesChapters = execMeta.all_locales;
    }

    const fetchServerManuals = async () => {
        try {
            const wTopic = Array.isArray(node.widgets) ? node.widgets.find(w => w.name === "topic_preset") : null;
            const wNotes = Array.isArray(node.widgets) ? node.widgets.find(w => w.name === "custom_notes") : null;
            const r = await api.fetchApi("/ez_cinematrix/note/manuals", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    locale: EZ_ACTIVE_LOCALE,
                    topic_preset: wTopic ? wTopic.value : "Alla Guider & Modell-Tips (Komplett Studio-Handbok [01]➔[13])",
                    custom_notes: wNotes ? wNotes.value : ""
                })
            });
            const d = await r.json();
            if (d && d.status === "ok") {
                if (d.chapters) st.serverChapters = d.chapters;
                if (d.all_locales) st.allLocalesChapters = d.all_locales;
                if (d.compiled_markdown) st.compiledGuideText = d.compiled_markdown;
                if (typeof node._ezRenderStudioNote === "function") node._ezRenderStudioNote();
            }
        } catch (e) {}
    };

    if (!st._initialFetchDone) {
        st._initialFetchDone = true;
        fetchServerManuals();
    }

    if (Array.isArray(node.widgets)) {
        const wTopic = node.widgets.find(w => w.name === "topic_preset");
        if (wTopic && !wTopic._ezNoteTopicBound) {
            wTopic._ezNoteTopicBound = true;
            const origTopicCb = wTopic.callback;
            wTopic.callback = function (val) {
                st.activeTab = _mapTopicPresetToTab(val);
                fetchServerManuals();
                if (typeof node._ezRenderStudioNote === "function") node._ezRenderStudioNote();
                if (origTopicCb) origTopicCb.apply(this, arguments);
            };
        }
        const wLoc = node.widgets.find(w => w.name === "note_locale");
        if (wLoc && !wLoc._ezNoteLocBound) {
            wLoc._ezNoteLocBound = true;
            const origLocCb = wLoc.callback;
            wLoc.callback = function (val) {
                const rawV = String(val || "EN").trim().toUpperCase();
                for (const code of EZ_SUPPORTED_LOCALES) {
                    if (rawV.startsWith(code)) {
                        setEzActiveLocale(code);
                        break;
                    }
                }
                fetchServerManuals();
                if (origLocCb) origLocCb.apply(this, arguments);
            };
        }
    }
    if (!node._ezStudioNoteDom) {
        const wrap = document.createElement("div");
        wrap.style.cssText = "width:100%;height:100%;background:#090a0f;border:1px solid #22d3ee;border-radius:7px;padding:7px;margin-top:2px;font-family:monospace;color:#f8fafc;display:flex;flex-direction:column;gap:5px;box-sizing:border-box;overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,0.65);";
        forwardRightClickToNode(wrap, node);
        node._ezStudioNoteDom = wrap;
        if (typeof node.addDOMWidget === "function") {
            const domW = node.addDOMWidget("ez_studio_note_handbook", "div", wrap, { serialize: false, hideOnZoom: false });
            if (domW) {
                domW.computeSize = (w) => [w, Math.max(360, (node.size && node.size[1] ? node.size[1] - 60 : 420))];
            }
        }
        if (node.size[0] < 540 || node.size[1] < 480) {
            node.setSize([Math.max(node.size[0], 560), Math.max(node.size[1], 500)]);
        }
    }

    const resolveActiveChapters = (dict) => {
        const locChapters = (st.allLocalesChapters && st.allLocalesChapters[EZ_ACTIVE_LOCALE]) || st.serverChapters || null;
        return {
            howto: (locChapters && locChapters.howto) || dict.howto || "",
            suno: (locChapters && locChapters.suno) || dict.suno || "",
            models: (locChapters && locChapters.models) || dict.models || "",
            upscale: (locChapters && locChapters.upscale) || dict.upscale || "",
            tips: (locChapters && locChapters.tips) || dict.tips || "",
            omniref: (locChapters && locChapters.omniref) || "### 6. OMNI-REFERENCE [13]\n• Ladda upp Karaktär, Kläder och Bakgrund separat och styr Qwen3-VL [02] och MiniMax H3 [06].",
            basics: (locChapters && locChapters.basics) || dict.basics || ""
        };
    };

    const getTabLabelMap = (dict) => ({
        all: (dict.tabs && dict.tabs.all) || "📚 Alla",
        howto: (dict.tabs && dict.tabs.howto) || "1. Flöde",
        suno: (dict.tabs && dict.tabs.suno) || "2. Suno [12]",
        models: (dict.tabs && dict.tabs.models) || "3. PRISM & Modeller",
        upscale: (dict.tabs && dict.tabs.upscale) || "4. Upscale [08]",
        tips: (dict.tabs && dict.tabs.tips) || "5. Kamera & Spektral",
        omniref: "6. Omni [13]",
        basics: (dict.tabs && dict.tabs.basics) || "7. Basics & Foundry",
        compiled: "📄 Text-Utgång",
        custom: (dict.tabs && dict.tabs.custom) || "📝 Anteckning"
    });

    const buildBodyHtml = (dict, wNotes, isModal = false) => {
        const ch = resolveActiveChapters(dict);
        const fSize = isModal ? "12.5px" : "10.5px";
        if (st.activeTab === "custom") {
            const curVal = wNotes ? String(wNotes.value || "") : "";
            return `<div style="display:flex;flex-direction:column;gap:6px;flex:1;min-height:${isModal ? "380px" : "180px"};">
              <div style="font-size:${isModal ? "12px" : "9.5px"};color:#22d3ee;font-weight:bold;">${dict.customLabel || "📝 Egna produktionsanteckningar:"}</div>
              <textarea class="ez-note-scratch" style="flex:1;width:100%;min-height:${isModal ? "360px" : "160px"};background:#0c0d12;color:#f8fafc;border:1px solid #334155;border-radius:6px;padding:8px;font-family:monospace;font-size:${isModal ? "12px" : "10.5px"};resize:vertical;box-sizing:border-box;">${curVal.replace(/</g, "&lt;")}</textarea>
            </div>`;
        }
        if (st.activeTab === "compiled") {
            const compRaw = st.compiledGuideText || [ch.howto, ch.omniref, ch.suno, ch.models, ch.upscale, ch.tips, ch.basics].filter(Boolean).join("\n\n");
            return `<div style="display:flex;flex-direction:column;gap:6px;flex:1;min-height:0;">
              <div style="font-size:${isModal ? "11.5px" : "9.5px"};color:#facc15;font-weight:bold;">📄 Direkt förhandsvisning av nodens <code>note_and_guide_text</code>-utgång (ingen "Preview as Text"-nod behövs):</div>
              <pre style="flex:1;margin:0;background:#07090e;color:#e2e8f0;border:1px solid #1e293b;border-radius:6px;padding:10px;font-family:monospace;font-size:${isModal ? "11.5px" : "10px"};white-space:pre-wrap;overflow-y:auto;line-height:1.5;">${compRaw.replace(/</g, "&lt;")}</pre>
            </div>`;
        }
        if (st.activeTab === "all") {
            const allParts = [ch.howto, ch.omniref, ch.suno, ch.models, ch.upscale, ch.tips, ch.basics]
                .filter(Boolean)
                .map(part => _formatNoteMarkdownToHtml(part, st.searchQuery, isModal))
                .join(`<hr style="border:none;border-top:1px solid #1e293b;margin:10px 0;"/>`);
            return `<div style="font-size:${fSize};line-height:1.6;color:#e2e8f0;overflow-y:auto;padding:4px;">${allParts}</div>`;
        }
        const singleMd = ch[st.activeTab] || ch.howto;
        return `<div style="font-size:${fSize};line-height:1.6;color:#e2e8f0;overflow-y:auto;padding:4px;">${_formatNoteMarkdownToHtml(singleMd, st.searchQuery, isModal)}</div>`;
    };

    const syncTabSelection = (nextTab) => {
        st.activeTab = nextTab;
        const wTopic = Array.isArray(node.widgets) ? node.widgets.find(w => w.name === "topic_preset") : null;
        const mappedPreset = _mapTabToTopicPreset(nextTab);
        if (wTopic && mappedPreset && wTopic.options && Array.isArray(wTopic.options.values) && wTopic.options.values.includes(mappedPreset)) {
            wTopic.value = mappedPreset;
        }
        fetchServerManuals();
        renderNote();
        if (node._ezStudioNoteModalOverlay) renderStudioNoteModal();
    };

    const copyActiveManualText = async () => {
        const dict = EZ_STUDIO_NOTE_I18N[EZ_ACTIVE_LOCALE] || EZ_STUDIO_NOTE_I18N.EN;
        const ch = resolveActiveChapters(dict);
        const txt = st.activeTab === "compiled" || st.activeTab === "all"
            ? (st.compiledGuideText || [ch.howto, ch.omniref, ch.suno, ch.models, ch.upscale, ch.tips, ch.basics].filter(Boolean).join("\n\n"))
            : (ch[st.activeTab] || st.compiledGuideText || "");
        try {
            await navigator.clipboard.writeText(String(txt || ""));
            st.copyNotice = "✓ Kopierad!";
            renderNote();
            if (node._ezStudioNoteModalOverlay) renderStudioNoteModal();
            setTimeout(() => {
                st.copyNotice = "";
                renderNote();
                if (node._ezStudioNoteModalOverlay) renderStudioNoteModal();
            }, 1800);
        } catch (e) {}
    };

    const openStudioNoteModal = () => {
        if (node._ezStudioNoteModalOverlay) {
            renderStudioNoteModal();
            return;
        }
        const ov = document.createElement("div");
        ov.style.cssText = "position:fixed;inset:0;background:rgba(4,6,12,0.88);backdrop-filter:blur(6px);z-index:100000;display:flex;align-items:center;justify-content:center;padding:16px;box-sizing:border-box;font-family:monospace;color:#f8fafc;";
        ov.onclick = (e) => { if (e.target === ov) closeStudioNoteModal(); };
        document.body.appendChild(ov);
        node._ezStudioNoteModalOverlay = ov;
        renderStudioNoteModal();
    };

    const closeStudioNoteModal = () => {
        if (node._ezStudioNoteModalOverlay) {
            node._ezStudioNoteModalOverlay.remove();
            node._ezStudioNoteModalOverlay = null;
        }
    };

    const renderStudioNoteModal = () => {
        const ov = node._ezStudioNoteModalOverlay;
        if (!ov) return;
        const dict = EZ_STUDIO_NOTE_I18N[EZ_ACTIVE_LOCALE] || EZ_STUDIO_NOTE_I18N.EN;
        const tabLabels = getTabLabelMap(dict);
        const wNotes = Array.isArray(node.widgets) ? node.widgets.find(w => w.name === "custom_notes") : null;
        const tabKeys = ["all", "howto", "suno", "models", "upscale", "tips", "omniref", "basics", "compiled", "custom"];
        const sidebarBtns = tabKeys.map(k => {
            const act = st.activeTab === k;
            return `<button data-mntab="${k}" style="width:100%;text-align:left;background:${act ? "#22d3ee" : "#13161f"};color:${act ? "#000" : "#e2e8f0"};border:1px solid ${act ? "#22d3ee" : "#334155"};border-radius:6px;padding:8px 10px;font-size:11px;font-weight:bold;cursor:pointer;">${tabLabels[k]}</button>`;
        }).join("");
        const langBtns = EZ_SUPPORTED_LOCALES.map(loc => {
            const act = loc === EZ_ACTIVE_LOCALE;
            return `<button data-mnloc="${loc}" style="background:${act ? "#38bdf8" : "#1e293b"};color:${act ? "#000" : "#cbd5e1"};border:none;border-radius:4px;padding:4px 8px;font-size:10.5px;font-weight:bold;cursor:pointer;">${loc}</button>`;
        }).join("");
        const bodyHtml = buildBodyHtml(dict, wNotes, true);
        const telemHtml = st.telemetry ? `<div style="font-size:11px;color:#34d399;background:#0c0d12;border:1px solid #1e293b;border-radius:6px;padding:6px 10px;">${st.telemetry}</div>` : "";
        const boxSize = st.modalFullscreen
            ? "width:99vw;height:98vh;"
            : "width:min(1180px, 95vw);height:min(820px, 90vh);resize:both;";
        ov.innerHTML = `
          <div style="${boxSize}background:#090a0f;border:2px solid #22d3ee;border-radius:12px;padding:14px;display:flex;flex-direction:column;gap:10px;box-shadow:0 24px 64px rgba(0,0,0,0.9);overflow:hidden;">
            <div style="display:flex;justify-content:space-between;align-items:center;background:#11131a;border:1px solid #1e293b;border-radius:8px;padding:8px 12px;gap:10px;flex-wrap:wrap;flex-shrink:0;">
              <div style="display:flex;align-items:center;gap:10px;">
                <span style="font-size:13px;font-weight:bold;color:#22d3ee;">${dict.title} // INTERACTIVE STUDIO MANUAL HUB</span>
                <span style="font-size:10px;background:#0e293b;color:#38bdf8;padding:2px 7px;border-radius:4px;">Ersätter "Preview as Text"</span>
              </div>
              <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                <input type="text" class="ez-note-modal-search" value="${st.searchQuery.replace(/"/g, "&quot;")}" placeholder="🔍 Sök i manualer..." style="background:#090a0f;color:#f8fafc;border:1px solid #334155;border-radius:5px;padding:4px 8px;font-size:11px;width:180px;" />
                <button class="ez-note-modal-copy" style="background:#10b981;color:#000;border:none;border-radius:5px;padding:5px 10px;font-size:10.5px;font-weight:bold;cursor:pointer;">${st.copyNotice || "📋 Kopiera Kapitel"}</button>
                ${langBtns}
                <button class="ez-note-modal-max" style="background:#334155;color:#f8fafc;border:none;border-radius:5px;padding:5px 10px;font-size:10.5px;font-weight:bold;cursor:pointer;">${st.modalFullscreen ? "🗗 Återställ" : "⛶ Fullskärm"}</button>
                <button class="ez-note-modal-close" style="background:#ef4444;color:#fff;border:none;border-radius:5px;padding:5px 12px;font-size:11px;font-weight:bold;cursor:pointer;">✕ STÄNG</button>
              </div>
            </div>
            <div style="flex:1;min-height:0;display:grid;grid-template-columns:220px 1fr;gap:10px;overflow:hidden;">
              <div style="background:#11131a;border:1px solid #1e293b;border-radius:8px;padding:8px;display:flex;flex-direction:column;gap:5px;overflow-y:auto;">
                <div style="font-size:10px;color:#94a3b8;font-weight:bold;padding:2px 4px;">KAPITEL & VYER</div>
                ${sidebarBtns}
              </div>
              <div class="ez-note-modal-body" style="background:#11131a;border:1px solid #1e293b;border-radius:8px;padding:14px;display:flex;flex-direction:column;overflow-y:auto;min-height:0;">
                ${bodyHtml}
              </div>
            </div>
            ${telemHtml}
          </div>
        `;
        if (!ov._ezKeyGuardBound) {
            ov._ezKeyGuardBound = true;
            ["keydown", "keyup", "keypress"].forEach(evName => {
                ov.addEventListener(evName, (ev) => {
                    const t = ev.target;
                    if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT")) {
                        ev.stopPropagation();
                    }
                });
            });
        }
        const closeBtn = ov.querySelector(".ez-note-modal-close");
        if (closeBtn) closeBtn.onclick = () => closeStudioNoteModal();
        const maxBtn = ov.querySelector(".ez-note-modal-max");
        if (maxBtn) maxBtn.onclick = () => { st.modalFullscreen = !st.modalFullscreen; renderStudioNoteModal(); };
        const copyBtn = ov.querySelector(".ez-note-modal-copy");
        if (copyBtn) copyBtn.onclick = () => copyActiveManualText();
        const bindModalScratchInput = (scopeEl) => {
            const ta = scopeEl ? scopeEl.querySelector(".ez-note-scratch") : null;
            if (ta && wNotes) {
                ta.oninput = () => { wNotes.value = ta.value; renderNote(); };
            }
        };
        const sIn = ov.querySelector(".ez-note-modal-search");
        if (sIn) {
            sIn.oninput = () => {
                st.searchQuery = sIn.value || "";
                renderNote();
                const mBody = ov.querySelector(".ez-note-modal-body");
                if (mBody) {
                    mBody.innerHTML = buildBodyHtml(dict, wNotes, true);
                    bindModalScratchInput(mBody);
                }
            };
        }
        ov.querySelectorAll("[data-mntab]").forEach(b => {
            b.onclick = () => syncTabSelection(b.getAttribute("data-mntab"));
        });
        ov.querySelectorAll("[data-mnloc]").forEach(b => {
            b.onclick = () => {
                setEzActiveLocale(b.getAttribute("data-mnloc"));
                fetchServerManuals();
            };
        });
        bindModalScratchInput(ov);
    };

    const renderNote = () => {
        const wrap = node._ezStudioNoteDom;
        if (!wrap) return;
        const dict = EZ_STUDIO_NOTE_I18N[EZ_ACTIVE_LOCALE] || EZ_STUDIO_NOTE_I18N.EN;
        const tabLabels = getTabLabelMap(dict);
        const wNotes = Array.isArray(node.widgets) ? node.widgets.find(w => w.name === "custom_notes") : null;
        const tabKeys = ["all", "howto", "suno", "models", "upscale", "tips", "omniref", "basics", "compiled", "custom"];
        const tabBtns = tabKeys.map(k => {
            const act = st.activeTab === k;
            return `<button data-ntab="${k}" style="background:${act ? "#22d3ee" : "#11131a"};color:${act ? "#000" : "#e2e8f0"};border:1px solid ${act ? "#22d3ee" : "#334155"};border-radius:4px;padding:3px 6px;font-size:8.5px;font-weight:bold;cursor:pointer;">${tabLabels[k]}</button>`;
        }).join("");
        const langBtns = EZ_SUPPORTED_LOCALES.map(loc => {
            const act = loc === EZ_ACTIVE_LOCALE;
            return `<button data-nloc="${loc}" style="background:${act ? "#38bdf8" : "#1e293b"};color:${act ? "#000" : "#cbd5e1"};border:none;border-radius:3px;padding:2px 5px;font-size:8px;font-weight:bold;cursor:pointer;">${loc}</button>`;
        }).join("");
        const bodyHtml = buildBodyHtml(dict, wNotes, false);
        const telemHtml = st.telemetry ? `<div style="font-size:8.5px;color:#34d399;background:#0c0d12;border:1px solid #1e293b;border-radius:4px;padding:3px 6px;flex-shrink:0;">${st.telemetry}</div>` : "";
        wrap.innerHTML = `
          <div style="display:flex;justify-content:space-between;align-items:center;background:#11131a;border:1px solid #1e293b;border-radius:5px;padding:4px 7px;gap:5px;flex-wrap:wrap;flex-shrink:0;">
            <span style="font-size:9.5px;font-weight:bold;color:#22d3ee;">${dict.title}</span>
            <div style="display:flex;align-items:center;gap:4px;flex-wrap:wrap;">
              <button class="ez-note-open-win" style="background:linear-gradient(90deg,#22d3ee,#38bdf8);color:#000;border:none;border-radius:4px;padding:3px 8px;font-size:9px;font-weight:bold;cursor:pointer;">${dict.openWindowBtn || "🗖 ÖPPNA MANUALER I EXTRA RUTA"}</button>
              <button class="ez-note-copy-btn" style="background:#10b981;color:#000;border:none;border-radius:3px;padding:2px 6px;font-size:8px;font-weight:bold;cursor:pointer;" title="Kopiera manualtext">${st.copyNotice || "📋"}</button>
              <button class="ez-note-raw-toggle" style="background:#1e293b;color:#cbd5e1;border:1px solid #334155;border-radius:3px;padding:2px 5px;font-size:8px;cursor:pointer;" title="Visa/Dölj råa ComfyUI-widgets">⚙️</button>
              <div style="display:flex;gap:2px;">${langBtns}</div>
            </div>
          </div>
          <div style="display:flex;gap:3px;flex-wrap:wrap;flex-shrink:0;">${tabBtns}</div>
          <div style="flex:1;min-height:220px;background:#11131a;border:1px solid #1e293b;border-radius:5px;padding:7px;display:flex;flex-direction:column;overflow-y:auto;">${bodyHtml}</div>
          ${telemHtml}
        `;
        if (!wrap._ezKeyGuardBound) {
            wrap._ezKeyGuardBound = true;
            ["keydown", "keyup", "keypress"].forEach(evName => {
                wrap.addEventListener(evName, (ev) => {
                    const t = ev.target;
                    if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT")) {
                        ev.stopPropagation();
                    }
                });
            });
        }
        const openWinBtn = wrap.querySelector(".ez-note-open-win");
        if (openWinBtn) openWinBtn.onclick = () => openStudioNoteModal();
        const copyBtn = wrap.querySelector(".ez-note-copy-btn");
        if (copyBtn) copyBtn.onclick = () => copyActiveManualText();
        const rawBtn = wrap.querySelector(".ez-note-raw-toggle");
        if (rawBtn) {
            rawBtn.onclick = () => {
                st.showRawWidgets = !st.showRawWidgets;
                collapseEzStudioNoteNativeWidgets(node, !st.showRawWidgets);
                renderNote();
            };
        }
        wrap.querySelectorAll("[data-ntab]").forEach(b => {
            b.onclick = () => syncTabSelection(b.getAttribute("data-ntab"));
        });
        wrap.querySelectorAll("[data-nloc]").forEach(b => {
            b.onclick = () => {
                setEzActiveLocale(b.getAttribute("data-nloc"));
                fetchServerManuals();
            };
        });
        const ta = wrap.querySelector(".ez-note-scratch");
        if (ta && wNotes) {
            ta.oninput = () => { wNotes.value = ta.value; };
        }
    };
    node._ezRenderStudioNote = () => {
        renderNote();
        if (node._ezStudioNoteModalOverlay) renderStudioNoteModal();
    };
    renderNote();
}

function mountEzSunoStudioHudWidget(node, sm = null) {
    if (!node) return;
    if (sm && typeof sm === "object") {
        node._ezLastSunoMeta = sm;
    }
    const meta = sm || node._ezLastSunoMeta || null;
    if (typeof node._ezSunoSplitRatio !== "number") {
        const savedRatio = parseFloat(localStorage.getItem("ez_suno_split_ratio") || "0.42");
        node._ezSunoSplitRatio = (!isNaN(savedRatio) && savedRatio >= 0.20 && savedRatio <= 0.78) ? savedRatio : 0.42;
    }
    const computeSunoHudHeight = () => {
        const nodeH = Array.isArray(node.size) ? Number(node.size[1] || 680) : 680;
        const fixedOverhead = 340;
        const flexArea = Math.max(300, nodeH - fixedOverhead);
        const ratio = Math.max(0.20, Math.min(0.78, Number(node._ezSunoSplitRatio || 0.42)));
        return Math.round(Math.max(195, Math.min(flexArea - 85, flexArea * ratio)));
    };
    if (!node._ezSunoHudDom) {
        const wrap = document.createElement("div");
        wrap.style.cssText = "width:100%;height:100%;background:#090a0f;border:1px solid #e879f9;border-radius:8px;padding:0 12px 10px 12px;margin:0;font-family:monospace;color:#f8fafc;display:flex;flex-direction:column;gap:6px;box-sizing:border-box;overflow:hidden;box-shadow:inset 0 0 18px rgba(232,121,249,0.08);";
        wrap.innerHTML = `
          <div class="ez-suno-splitter" title="Dra upp eller ner för att justera höjden mellan Låttext och Suno Studio" style="display:flex;justify-content:center;align-items:center;gap:8px;height:18px;min-height:18px;margin:0 -12px 2px -12px;background:linear-gradient(180deg,#1e1b4b 0%,#11131a 100%);border-bottom:1px solid #701a75;cursor:ns-resize;user-select:none;flex-shrink:0;">
            <span style="width:28px;height:3px;border-radius:2px;background:#e879f9;opacity:0.8;"></span>
            <span style="font-size:8.5px;color:#f0abfc;font-weight:bold;letter-spacing:0.5px;">↕ DRA FÖR ATT JUSTERA LÅTTEXT / SUNO-BOX</span>
            <span style="width:28px;height:3px;border-radius:2px;background:#e879f9;opacity:0.8;"></span>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;border-bottom:1px solid #1e293b;padding-bottom:5px;flex-shrink:0;">
            <span class="ez-suno-title" style="font-size:11px;color:#f0abfc;font-weight:bold;letter-spacing:0.3px;">🎵 SUNO MASTER AUDIO PLAYER (48 kHz STEREO)</span>
            <span class="ez-suno-badge" style="font-size:9.5px;background:#1e1b4b;color:#e879f9;border:1px solid #701a75;border-radius:4px;padding:2px 7px;font-weight:bold;">REDO</span>
          </div>
          <audio class="ez-suno-aud" controls preload="metadata" style="width:100%;height:38px;min-height:38px;border-radius:6px;background:#11131a;flex-shrink:0;display:block;"></audio>
          <div class="ez-suno-meta-bar" style="display:flex;gap:8px;flex-wrap:wrap;font-size:9.5px;color:#cbd5e1;background:#11131a;border:1px solid #1e293b;border-radius:5px;padding:4px 8px;flex-shrink:0;"></div>
          <div class="ez-suno-lyr-box" style="flex:1;min-height:48px;overflow-y:auto;overflow-x:hidden;background:#0c0d12;border:1px solid #1e293b;border-radius:5px;padding:6px 8px;font-size:9.5px;line-height:1.45;color:#94a3b8;white-space:pre-wrap;word-break:break-word;"></div>
        `;
        forwardRightClickToNode(wrap, node);
        node._ezSunoHudDom = wrap;
        const splitterEl = wrap.querySelector(".ez-suno-splitter");
        if (splitterEl) {
            splitterEl.addEventListener("pointerdown", (ev) => {
                if (ev.button !== 0) return;
                ev.preventDefault();
                ev.stopPropagation();
                const startY = ev.clientY;
                const startHudH = computeSunoHudHeight();
                const nodeH = Array.isArray(node.size) ? Number(node.size[1] || 680) : 680;
                const flexArea = Math.max(300, nodeH - 340);
                const scale = (app && app.canvas && app.canvas.ds && Number(app.canvas.ds.scale) > 0) ? Number(app.canvas.ds.scale) : 1.0;
                const onMove = (mEv) => {
                    const dy = (mEv.clientY - startY) / scale;
                    const nextH = Math.max(195, Math.min(flexArea - 85, startHudH - dy));
                    node._ezSunoSplitRatio = Math.max(0.20, Math.min(0.78, nextH / flexArea));
                    try { localStorage.setItem("ez_suno_split_ratio", String(node._ezSunoSplitRatio)); } catch (e) {}
                    node.setSize([node.size[0], node.size[1]]);
                    if (app && app.graph) app.graph.setDirtyCanvas(true, true);
                };
                const onUp = () => {
                    window.removeEventListener("pointermove", onMove, true);
                    window.removeEventListener("pointerup", onUp, true);
                };
                window.addEventListener("pointermove", onMove, true);
                window.addEventListener("pointerup", onUp, true);
            });
        }
        if (typeof node.addDOMWidget === "function") {
            const domW = node.addDOMWidget("ez_suno_audio_hud", "div", wrap, {
                serialize: false,
                hideOnZoom: false,
                getMinHeight: () => computeSunoHudHeight(),
                getMaxHeight: () => computeSunoHudHeight(),
            });
            if (domW) {
                domW.computeSize = (w) => [w, computeSunoHudHeight()];
                node._ezSunoHudWidget = domW;
            }
        }
    }
    if (Array.isArray(node.widgets)) {
        const lyrIdx = node.widgets.findIndex(w => w && w.name === "lyrics_or_prompt");
        const hudIdx = node.widgets.findIndex(w => w && w.name === "ez_suno_audio_hud");
        if (lyrIdx !== -1 && hudIdx !== -1 && lyrIdx < hudIdx - 1) {
            const [lyrW] = node.widgets.splice(lyrIdx, 1);
            const newHudIdx = node.widgets.findIndex(w => w && w.name === "ez_suno_audio_hud");
            node.widgets.splice(newHudIdx, 0, lyrW);
        }
    }
    const wrap = node._ezSunoHudDom;
    const titleEl = wrap.querySelector(".ez-suno-title");
    const badgeEl = wrap.querySelector(".ez-suno-badge");
    const audEl = wrap.querySelector(".ez-suno-aud");
    const metaBar = wrap.querySelector(".ez-suno-meta-bar");
    const lyrBox = wrap.querySelector(".ez-suno-lyr-box");

    const wMode = Array.isArray(node.widgets) ? node.widgets.find(w => w && w.name === "source_mode") : null;
    const wUrl = Array.isArray(node.widgets) ? node.widgets.find(w => w && w.name === "suno_song_url_or_id") : null;
    const wLoc = Array.isArray(node.widgets) ? node.widgets.find(w => w && w.name === "local_audio_file") : null;
    const wCus = Array.isArray(node.widgets) ? node.widgets.find(w => w && w.name === "custom_audio_path") : null;
    const wLyr = Array.isArray(node.widgets) ? node.widgets.find(w => w && w.name === "lyrics_or_prompt") : null;
    const wTag = Array.isArray(node.widgets) ? node.widgets.find(w => w && w.name === "song_style_tags") : null;

    const modeStr = wMode ? String(wMode.value || "") : "";
    const isBypassWidget = modeStr.toLowerCase().startsWith("bypass");
    const urlStr = wUrl ? String(wUrl.value || "").trim() : "";
    const locStr = wLoc ? String(wLoc.value || "").trim() : "";
    const cusStr = wCus ? String(wCus.value || "").trim() : "";
    const hasLocalFile = (locStr && !locStr.startsWith("(") && locStr.toLowerCase() !== "none") || Boolean(cusStr);
    const hasSunoUrl = Boolean(urlStr);

    const isBypassed = isBypassWidget || (meta && meta.suno_bypassed === true) || (!hasSunoUrl && !hasLocalFile && !(meta && meta.active && meta.filename));

    if (isBypassed) {
        wrap.style.borderColor = "#475569";
        if (titleEl) {
            titleEl.style.color = "#94a3b8";
            titleEl.textContent = "🔇 SUNO STUDIO // BYPASS / AVSTÄNGD (H3 32 kHz INBYGGT LJUD AKTIVT)";
        }
        if (badgeEl) {
            badgeEl.style.background = "#1e293b";
            badgeEl.style.color = "#cbd5e1";
            badgeEl.style.borderColor = "#334155";
            badgeEl.textContent = isBypassWidget ? "BYPASS PÅ" : "INGEN LÄNK -> AUTO-BYPASS";
        }
        if (audEl) {
            try { audEl.pause(); } catch (e) {}
            audEl.removeAttribute("src");
            audEl.style.opacity = "0.45";
        }
        if (metaBar) {
            metaBar.innerHTML = `<span>🔈 <b>Ljudkälla:</b> MiniMax H3 / Wan Inbyggt Ljud (32 kHz)</span><span>•</span><span>Suno-ljud spelas inte in i videon när Bypass är aktivt eller länken är tom.</span>`;
        }
        if (lyrBox) {
            lyrBox.textContent = "Suno [12] är i Bypass-läge. Nedströms noder ([02] Timeline, [06] Director, [07] Joint AV Sampler & [08] Cinema Vault) använder videomodellens eget ljud utan tyst WAV-överskrivning.";
        }
    } else {
        wrap.style.borderColor = "#e879f9";
        const srcTitle = (meta && meta.source_name) || urlStr || cusStr || locStr || "Suno / Lokal Ljudkälla";
        if (titleEl) {
            titleEl.style.color = "#f0abfc";
            titleEl.textContent = `🎵 SUNO MASTER: ${String(srcTitle).slice(0, 54)}`;
        }
        if (badgeEl) {
            badgeEl.style.background = "#3b0764";
            badgeEl.style.color = "#f0abfc";
            badgeEl.style.borderColor = "#a855f7";
            badgeEl.textContent = (meta && meta.filename) ? `${meta.bpm || 120} BPM // ${meta.duration_sec || 0}s` : "REDO ATT SYNKAS";
        }
        if (audEl) {
            audEl.style.opacity = "1";
            if (meta && meta.filename) {
                const nextUrl = buildViewUrl(meta.filename, meta.subfolder || "", meta.type || "temp");
                if (audEl.dataset.ezSrc !== meta.filename) {
                    audEl.dataset.ezSrc = meta.filename;
                    audEl.src = nextUrl;
                }
            }
        }
        if (metaBar) {
            const tagsTxt = (meta && meta.tags) || (wTag ? String(wTag.value || "").trim() : "") || "Ingen stiltagg";
            metaBar.innerHTML = `<span>🎼 <b>Stil:</b> ${tagsTxt.slice(0, 68).replace(/</g, "&lt;")}</span><span>•</span><span>🔊 <b>Format:</b> 48 kHz Stereo WAV</span>`;
        }
        if (lyrBox) {
            const lyrTxt = (meta && meta.lyrics) || (wLyr ? String(wLyr.value || "").trim() : "");
            lyrBox.textContent = lyrTxt || "Klistra in en Suno-länk eller välj en lokal ljudfil och kör flödet för att spela upp 48 kHz-mastern och synka lyrics/beats här.";
        }
    }
    if (node.size[0] < 460 || node.size[1] < 650) {
        node.setSize([Math.max(node.size[0], 460), Math.max(node.size[1], 650)]);
    }
    if (app.graph) app.graph.setDirtyCanvas(true, true);
}

function setEzActiveLocale(nextLoc) {
    if (!EZ_SUPPORTED_LOCALES.includes(nextLoc)) return;
    EZ_ACTIVE_LOCALE = nextLoc;
    try { localStorage.setItem("ez_cinematrix_locale", EZ_ACTIVE_LOCALE); } catch (e) {}
    if (app && app.graph && Array.isArray(app.graph._nodes)) {
        for (const n of app.graph._nodes) {
            applyEzLocaleToNode(n);
            if (typeof n._ezRenderStudioNote === "function") n._ezRenderStudioNote();
        }
        app.graph.setDirtyCanvas(true, true);
    }
}

const EZ_NODE_DATA_REGISTRY = {};

function extractEzWidgetSpecs(nodeData) {
    const specs = {};
    if (!nodeData || !nodeData.input) return specs;
    let orderIdx = 0;
    for (const group of ["required", "optional"]) {
        const grpObj = nodeData.input[group];
        if (!grpObj || typeof grpObj !== "object") continue;
        for (const [k, v] of Object.entries(grpObj)) {
            if (!Array.isArray(v) || v.length === 0) continue;
            const first = v[0];
            const opts = (v.length > 1 && v[1] && typeof v[1] === "object" && !Array.isArray(v[1])) ? v[1] : {};
            const kindStr = Array.isArray(first) ? "COMBO" : String(first);
            const isWidgetCapable = Array.isArray(first) || ["INT", "FLOAT", "BOOLEAN", "STRING"].includes(kindStr);
            specs[k] = {
                name: k,
                group,
                orderIndex: orderIdx++,
                kind: kindStr,
                isWidgetCapable,
                choices: Array.isArray(first) ? first : null,
                defaultVal: opts.default !== undefined ? opts.default : (Array.isArray(first) && first.length > 0 ? first[0] : undefined),
                min: opts.min,
                max: opts.max,
                step: opts.step,
                multiline: Boolean(opts.multiline)
            };
            if (opts && opts.control_after_generate) {
                specs.control_after_generate = {
                    name: "control_after_generate",
                    group,
                    orderIndex: orderIdx++,
                    kind: "COMBO",
                    isWidgetCapable: true,
                    choices: ["fixed", "increment", "decrement", "randomize"],
                    defaultVal: "randomize"
                };
            }
        }
    }
    return specs;
}

function styleEzSectionHeaderWidget(node, w) {
    if (!w || typeof w.name !== "string") return;
    if (!(w.name.startsWith("SECTION_HEADER_") || w.name.startsWith("rubrik_slot_")) || w._ezHeaderStyled) return;
    w._ezHeaderStyled = true;
    const initDefs = (node && node._ezInitialWidgetDefaults) || {};
    const headerTitle = String(initDefs[w.name] || w.value || w.name);
    w.draw = function (ctx, _n, widgetWidth, y, H) {
        ctx.save();
        ctx.fillStyle = "rgba(18, 22, 34, 0.96)";
        ctx.strokeStyle = "#f59e0b";
        ctx.lineWidth = 1.2;
        const bx = 12;
        const bw = Math.max(120, widgetWidth - 24);
        ctx.fillRect(bx, y + 1, bw, H - 2);
        ctx.strokeRect(bx, y + 1, bw, H - 2);
        ctx.font = "bold 9.5px monospace";
        ctx.fillStyle = "#fbbf24";
        ctx.fillText(headerTitle.slice(0, 74), bx + 8, y + H * 0.68);
        ctx.restore();
    };
    w.mouse = function () { return false; };
}

const EZ_NEW_LORA4_AND_BYPASS_WIDGETS = new Set([
    "enable_style_lora_1",
    "enable_style_lora_2",
    "enable_style_lora_3",
    "enable_style_lora_4",
    "style_lora_4",
    "style_strength_4",
    "style_clip_strength_4",
    "enable_turbo_lora",
    "enable_video_lora_1",
    "enable_video_lora_2",
    "enable_video_lora_3",
    "enable_video_lora_4",
    "video_lora_4",
    "lora_4_video_strength",
    "lora_4_vis_strength",
    "lora_4_audio_strength",
    "lora_4_clip_strength",
    "enable_video_turbo_lora",
    "enable_image_lora_1",
    "enable_image_lora_2",
    "enable_image_lora_3",
    "enable_image_lora_4",
    "image_style_lora_4",
    "image_style_strength_4",
    "enable_image_turbo_lora",
    "video_lora_4_strength",
    "custom_negative_prompt"
]);

const EZ_INSERTED_WIDGET_NAMES = new Set([
    ...EZ_NEW_LORA4_AND_BYPASS_WIDGETS,
    "control_after_generate",
    "content_rating_mode",
    "audio_soundtrack_mode",
    "seed_mode",
    "i2i_denoise",
    "style_clip_strength_1",
    "style_clip_strength_2",
    "style_clip_strength_3",
    "lora_1_vis_strength",
    "lora_1_clip_strength",
    "lora_2_vis_strength",
    "lora_2_clip_strength",
    "lora_3_vis_strength",
    "lora_3_clip_strength",
    "turbo_vis_strength",
    "rife_model",
    "rife_multiplier",
    "rife_strength",
    "detailer_1x_model_name",
    "custom_frame_rate",
    "custom_quality_crf",
    "subject_stance_posture",
    "body_choreography_preset",
    "camera_trajectory_arc",
    "scene_continuity_mode",
    "temporal_window_horizon",
    "rubrik_slot_5",
    "slot5_reference_video",
    "slot5_start_offset_sec",
    "slot5_duration_mode",
    "slot5_duration_seconds",
    "slot5_focus_mode",
    "slot5_motion_strength",
    "slot5_max_frames",
    "custom_negative_prompt"
]);

function hideRawCustomNegativeWidget(node) {
    if (!node || !Array.isArray(node.widgets)) return null;
    const wNeg = node.widgets.find(w => w && w.name === "custom_negative_prompt");
    if (wNeg && !wNeg._ezHiddenRaw) {
        wNeg._ezHiddenRaw = true;
        wNeg.computeSize = () => [0, -4];
        wNeg.draw = () => {};
        wNeg.mouse = () => false;
        if (wNeg.inputEl && wNeg.inputEl.style) {
            wNeg.inputEl.style.display = "none";
        }
    }
    return wNeg;
}

function mountEzQwenNegativePromptToggleWidget(node, promptData = null) {
    if (!node) return;
    const wCustomNeg = hideRawCustomNegativeWidget(node);
    if (promptData && typeof promptData === "object") {
        if (promptData.auto_neg) node._ezLastAutoNegPrompt = String(promptData.auto_neg);
        if (promptData.neg) node._ezLastCompiledNegPrompt = String(promptData.neg);
    }
    if (!node._ezNegDrawerDom) {
        const wrap = document.createElement("div");
        wrap.style.cssText = "background:#090a0f;border:1px solid rgba(168,85,247,0.45);border-radius:6px;padding:5px 6px;margin-top:4px;font-family:monospace;color:#e2e8f0;display:flex;flex-direction:column;gap:5px;box-sizing:border-box;width:100%;";
        wrap.innerHTML = `
          <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;">
            <button type="button" class="ez-neg-toggle-btn" style="flex:1;background:linear-gradient(90deg,#131622,#1e1b2e);color:#e9d5ff;border:1px solid #a855f7;border-radius:4px;padding:4px 8px;font-size:10px;font-weight:bold;cursor:pointer;text-align:left;display:flex;justify-content:space-between;align-items:center;">
              <span class="ez-neg-toggle-label">🛡️ NEGATIVE PROMPT [DOLD — KLICKA FÖR ATT VISA / REDIGERA]</span>
              <span class="ez-neg-mode-badge" style="background:#064e3b;color:#34d399;border:1px solid #10b981;border-radius:3px;padding:1px 5px;font-size:8.5px;">⚡ AUTO</span>
            </button>
          </div>
          <div class="ez-neg-drawer-body" style="display:none;flex-direction:column;gap:5px;padding-top:3px;border-top:1px solid #1e293b;">
            <div style="display:flex;justify-content:space-between;align-items:center;gap:4px;flex-wrap:wrap;">
              <span class="ez-neg-hint" style="font-size:8.5px;color:#94a3b8;">Visar aktiv Negative Prompt för [04] Krea 2 & [06] Video Director. Skriv i rutan för manuell override:</span>
              <div style="display:flex;gap:4px;">
                <button type="button" class="ez-neg-lock-btn" title="Kopiera auto-genererad negative prompt till redigerbar override" style="background:#1e293b;color:#38bdf8;border:1px solid #334155;border-radius:3px;padding:2px 6px;font-size:8.5px;cursor:pointer;font-weight:bold;">🔒 Lås för Redigering</button>
                <button type="button" class="ez-neg-reset-btn" title="Rensa manuell override och återgå till dynamisk Auto-Negative Prompt" style="background:#1e293b;color:#f87171;border:1px solid #334155;border-radius:3px;padding:2px 6px;font-size:8.5px;cursor:pointer;font-weight:bold;">🔄 Återställ till Auto</button>
              </div>
            </div>
            <textarea class="ez-neg-textarea" data-ez-scrollable="1" rows="5" placeholder="Auto-Negative Prompt genereras dynamiskt vid körning (eller skriv din egen negative prompt här för att överstyra)..." style="width:100%;min-height:92px;max-height:220px;resize:vertical;background:#05060a;color:#f8fafc;border:1px solid #334155;border-radius:4px;padding:6px;font-family:monospace;font-size:10px;line-height:1.4;box-sizing:border-box;"></textarea>
          </div>
        `;
        forwardRightClickToNode(wrap, node);
        node._ezNegDrawerDom = wrap;
        node._ezNegDrawerOpen = false;
        let domW = null;
        if (typeof node.addDOMWidget === "function") {
            domW = node.addDOMWidget("ez_qwen_negative_prompt_drawer", "div", wrap, { serialize: false, hideOnZoom: false });
            if (domW) {
                domW.computeSize = (w) => [w, node._ezNegDrawerOpen ? 168 : 34];
            }
        }
        node._ezNegDrawerWidget = domW;
        const toggleBtn = wrap.querySelector(".ez-neg-toggle-btn");
        const toggleLbl = wrap.querySelector(".ez-neg-toggle-label");
        const modeBadge = wrap.querySelector(".ez-neg-mode-badge");
        const bodyEl = wrap.querySelector(".ez-neg-drawer-body");
        const lockBtn = wrap.querySelector(".ez-neg-lock-btn");
        const resetBtn = wrap.querySelector(".ez-neg-reset-btn");
        const txtArea = wrap.querySelector(".ez-neg-textarea");

        const syncNegStateToWidget = (newVal) => {
            const wN = hideRawCustomNegativeWidget(node);
            const cleanV = String(newVal || "");
            if (wN) {
                wN.value = cleanV;
                if (typeof wN.callback === "function") {
                    try { wN.callback(cleanV); } catch (e) {}
                }
            }
            node.properties = node.properties || {};
            node.properties._ez_widget_map = node.properties._ez_widget_map || {};
            node.properties._ez_widget_map.custom_negative_prompt = cleanV;
            if (Array.isArray(node.widgets)) {
                const serW = node.widgets.filter(x => !(x.options && x.options.serialize === false));
                node.widgets_values = serW.map(x => x.value);
            }
            refreshDrawerUi();
        };

        const refreshDrawerUi = () => {
            const wN = hideRawCustomNegativeWidget(node);
            const customVal = wN ? String(wN.value || "").trim() : "";
            const isManual = customVal.length > 0;
            const isOpen = Boolean(node._ezNegDrawerOpen);
            bodyEl.style.display = isOpen ? "flex" : "none";
            toggleLbl.textContent = isOpen
                ? "🛡️ NEGATIVE PROMPT [ÖPPEN — KLICKA FÖR ATT DÖLJA]"
                : "🛡️ NEGATIVE PROMPT [DOLD — KLICKA FÖR ATT VISA / REDIGERA]";
            if (isManual) {
                modeBadge.textContent = "✍️ MANUELL OVERRIDE";
                modeBadge.style.background = "#451a03";
                modeBadge.style.color = "#fbbf24";
                modeBadge.style.borderColor = "#f59e0b";
                txtArea.style.borderColor = "#f59e0b";
                if (document.activeElement !== txtArea && txtArea.value !== customVal) {
                    txtArea.value = customVal;
                }
            } else {
                modeBadge.textContent = "⚡ AUTO";
                modeBadge.style.background = "#064e3b";
                modeBadge.style.color = "#34d399";
                modeBadge.style.borderColor = "#10b981";
                txtArea.style.borderColor = "#334155";
                const autoTxt = node._ezLastAutoNegPrompt || node._ezLastCompiledNegPrompt || "(Auto-genereras vid körning: anti-twin guard, åldersskydd, stil-negativ, ljud-/läppsynk-filter, chroma-skydd & Wan 2.2 kvalitetsankare)";
                if (document.activeElement !== txtArea) {
                    txtArea.value = autoTxt;
                }
            }
            if (app && app.graph) app.graph.setDirtyCanvas(true, true);
        };

        toggleBtn.onclick = () => {
            node._ezNegDrawerOpen = !node._ezNegDrawerOpen;
            const deltaH = node._ezNegDrawerOpen ? 134 : -134;
            if (Array.isArray(node.size)) {
                node.setSize([node.size[0], Math.max(420, node.size[1] + deltaH)]);
            }
            refreshDrawerUi();
        };

        lockBtn.onclick = () => {
            const seedTxt = node._ezLastAutoNegPrompt || node._ezLastCompiledNegPrompt || txtArea.value || "";
            if (seedTxt && !seedTxt.startsWith("(Auto-genereras")) {
                txtArea.value = seedTxt;
                syncNegStateToWidget(seedTxt);
            }
            txtArea.focus();
        };

        resetBtn.onclick = () => {
            syncNegStateToWidget("");
        };

        txtArea.addEventListener("input", () => {
            syncNegStateToWidget(txtArea.value);
        });

        node._ezRefreshNegDrawer = refreshDrawerUi;
    }
    if (typeof node._ezRefreshNegDrawer === "function") {
        node._ezRefreshNegDrawer();
    }
}

function isValueValidForEzWidget(val, w, spec) {
    if (val === undefined || val === null) return false;
    const choices = (w && w.options && Array.isArray(w.options.values)) ? w.options.values : (spec && spec.choices);
    if (Array.isArray(choices) && choices.length > 0) {
        if (choices.includes(val)) return true;
        if (typeof val === "string" && val.trim().length > 0) {
            const normVal = val.replace(/\//g, "\\");
            if (choices.some(c => String(c).replace(/\//g, "\\") === normVal)) return true;
            if (w && (w.name === "vlm_model_name" || w.name === "source_image" || w.name.startsWith("slot"))) {
                if (w.options && Array.isArray(w.options.values) && !w.options.values.includes(val)) {
                    w.options.values.push(val);
                }
                return true;
            }
        }
        return false;
    }
    const kind = spec ? spec.kind : "";
    if (kind === "INT" || kind === "FLOAT" || (w && w.type === "number")) {
        if (typeof val !== "number" || Number.isNaN(val)) return false;
        if (spec && typeof spec.min === "number" && val < spec.min) return false;
        if (spec && typeof spec.max === "number" && val > spec.max) return false;
        return true;
    }
    if (kind === "BOOLEAN" || (w && w.type === "toggle")) {
        return typeof val === "boolean";
    }
    if (kind === "STRING" || (w && (w.type === "text" || w.type === "customtext"))) {
        return typeof val === "string";
    }
    return true;
}

function resolveDefaultForEzWidget(w, spec, fallbackMap) {
    if (w && typeof w.name === "string") {
        if (w.name.startsWith("enable_")) return true;
        if (w.name === "style_lora_4" || w.name === "video_lora_4" || w.name === "image_style_lora_4") return "None";
    }
    if (spec && spec.defaultVal !== undefined) return spec.defaultVal;
    if (fallbackMap && w && fallbackMap[w.name] !== undefined) return fallbackMap[w.name];
    if (w && w.options && Array.isArray(w.options.values) && w.options.values.length > 0) return w.options.values[0];
    if (w && w.type === "number") return 0;
    if (w && w.type === "toggle") return false;
    return "";
}

function healAndSyncEzNodeWidgets(node, nodeData, savedInfo, resetToDefaults = false) {
    if (!node || !Array.isArray(node.widgets)) return;
    const specs = extractEzWidgetSpecs(nodeData || EZ_NODE_DATA_REGISTRY[node.type]);
    const initDefaults = node._ezInitialWidgetDefaults || {};
    const convertedInputNames = new Set(
        Array.isArray(node.inputs) ? node.inputs.map(inp => inp && inp.name).filter(Boolean) : []
    );

    // 1. Update combo options & numeric bounds on existing widgets, and inject any missing schema widgets in-place
    let createdAnyMissingWidget = false;
    for (const [specName, spec] of Object.entries(specs)) {
        if (!spec || !spec.isWidgetCapable) continue;
        let existingW = node.widgets.find(x => x && x.name === specName);
        if (existingW) {
            if (spec.kind === "COMBO" && Array.isArray(spec.choices)) {
                existingW.options = existingW.options || {};
                const curVal = existingW.value;
                const nextChoices = [...spec.choices];
                if (specName === "source_image" || EZ_OMNI_IMAGE_SLOT_NAMES.includes(specName)) {
                    appendUniqueMediaValues(nextChoices, Array.from(EZ_LIVE_UPLOADED_IMAGES));
                } else if (specName === "slot5_reference_video") {
                    appendUniqueMediaValues(nextChoices, Array.from(EZ_LIVE_UPLOADED_VIDEOS));
                }
                if (curVal && typeof curVal === "string" && (specName === "vlm_model_name" || specName === "source_image" || specName.startsWith("slot")) && !nextChoices.includes(curVal)) {
                    nextChoices.push(curVal);
                }
                existingW.options.values = nextChoices;
            } else if ((spec.kind === "INT" || spec.kind === "FLOAT") && existingW.options) {
                if (typeof spec.min === "number") existingW.options.min = spec.min;
                if (typeof spec.max === "number") existingW.options.max = spec.max;
            }
            if (spec.defaultVal !== undefined && initDefaults[specName] === undefined) {
                initDefaults[specName] = spec.defaultVal;
            }
            styleEzSectionHeaderWidget(node, existingW);
        } else if (!convertedInputNames.has(specName) && typeof node.addWidget === "function") {
            const defVal = spec.defaultVal !== undefined ? spec.defaultVal : "";
            initDefaults[specName] = defVal;
            let newW = null;
            if (spec.kind === "COMBO" && Array.isArray(spec.choices)) {
                newW = node.addWidget("combo", specName, defVal, () => {}, { values: [...spec.choices] });
            } else if (spec.kind === "INT" || spec.kind === "FLOAT") {
                const numOpts = {
                    min: typeof spec.min === "number" ? spec.min : 0,
                    max: typeof spec.max === "number" ? spec.max : 999999,
                    step: typeof spec.step === "number" ? spec.step : (spec.kind === "INT" ? 10 : 0.1),
                    precision: spec.kind === "INT" ? 0 : 2
                };
                newW = node.addWidget("number", specName, Number(defVal) || 0, () => {}, numOpts);
            } else if (spec.kind === "BOOLEAN") {
                newW = node.addWidget("toggle", specName, Boolean(defVal), () => {}, {});
            } else if (spec.kind === "STRING") {
                newW = node.addWidget("text", specName, String(defVal || ""), () => {}, {});
            }
            if (newW) {
                styleEzSectionHeaderWidget(node, newW);
                createdAnyMissingWidget = true;
            }
        }
    }

    if (createdAnyMissingWidget) {
        const domWidgets = node.widgets.filter(w => w && w.options && w.options.serialize === false);
        const stdWidgets = node.widgets.filter(w => !(w && w.options && w.options.serialize === false));
        stdWidgets.sort((a, b) => {
            const oa = specs[a.name] ? specs[a.name].orderIndex : 9999;
            const ob = specs[b.name] ? specs[b.name].orderIndex : 9999;
            return oa - ob;
        });
        node.widgets = [...stdWidgets, ...domWidgets];
    }

    const serWidgets = node.widgets.filter(w => !(w.options && w.options.serialize === false));
    if (savedInfo && savedInfo.properties && savedInfo.properties._ez_widget_map && savedInfo.properties._ez_widget_map.style_target === "dark-fantasy") {
        savedInfo.properties._ez_widget_map.style_target = "dark-fantasy-real";
    }
    if (savedInfo && Array.isArray(savedInfo.widgets_values)) {
        for (let vi = 0; vi < savedInfo.widgets_values.length; vi++) {
            if (savedInfo.widgets_values[vi] === "dark-fantasy") savedInfo.widgets_values[vi] = "dark-fantasy-real";
        }
    }
    for (const w of serWidgets) {
        if (w && w.name === "style_target" && w.value === "dark-fantasy") w.value = "dark-fantasy-real";
    }
    if (resetToDefaults) {
        for (const w of serWidgets) {
            w.value = resolveDefaultForEzWidget(w, specs[w.name], initDefaults);
        }
    } else if (savedInfo && savedInfo.properties && savedInfo.properties._ez_widget_map && typeof savedInfo.properties._ez_widget_map === "object") {
        const wMap = savedInfo.properties._ez_widget_map;
        for (const w of serWidgets) {
            const spec = specs[w.name];
            if (Object.prototype.hasOwnProperty.call(wMap, w.name) && isValueValidForEzWidget(wMap[w.name], w, spec)) {
                w.value = wMap[w.name];
            } else {
                w.value = resolveDefaultForEzWidget(w, spec, initDefaults);
            }
        }
    } else if (savedInfo && Array.isArray(savedInfo.widgets_values) && savedInfo.widgets_values.length !== serWidgets.length) {
        const oldVals = savedInfo.widgets_values;
        let vIdx = 0;
        const missingCount = serWidgets.length - oldVals.length;
        const newWidgetCountInNode = serWidgets.filter(sw => EZ_NEW_LORA4_AND_BYPASS_WIDGETS.has(sw.name)).length;
        const useStrictNewSet = missingCount > 0 && missingCount <= newWidgetCountInNode;
        for (let wIdx = 0; wIdx < serWidgets.length; wIdx++) {
            const w = serWidgets[wIdx];
            const spec = specs[w.name];
            const cand = vIdx < oldVals.length ? oldVals[vIdx] : undefined;
            const remWidgets = serWidgets.length - wIdx;
            const remVals = oldVals.length - vIdx;
            if (remWidgets > remVals && vIdx < oldVals.length) {
                const isInserted = useStrictNewSet
                    ? EZ_NEW_LORA4_AND_BYPASS_WIDGETS.has(w.name)
                    : EZ_INSERTED_WIDGET_NAMES.has(w.name);
                if (isInserted) {
                    w.value = resolveDefaultForEzWidget(w, spec, initDefaults);
                    continue;
                }
                const nextW = serWidgets[wIdx + 1];
                const nextSpec = nextW ? specs[nextW.name] : null;
                if (!isValueValidForEzWidget(cand, w, spec) && nextW && isValueValidForEzWidget(cand, nextW, nextSpec)) {
                    w.value = resolveDefaultForEzWidget(w, spec, initDefaults);
                    continue;
                }
            }
            if (isValueValidForEzWidget(cand, w, spec)) {
                w.value = cand;
                vIdx++;
            } else {
                w.value = resolveDefaultForEzWidget(w, spec, initDefaults);
                if (remWidgets <= remVals) vIdx++;
            }
        }
    } else {
        for (const w of serWidgets) {
            const spec = specs[w.name];
            if (!isValueValidForEzWidget(w.value, w, spec)) {
                w.value = resolveDefaultForEzWidget(w, spec, initDefaults);
            }
        }
    }
    const byName = {};
    for (const w of serWidgets) {
        byName[w.name] = w;
        if (w && (w.name === "seed" || w.name === "random_seed" || w.name === "compiler_seed")) {
            if (w.options && typeof w.options === "object") {
                if (!w.options.max || w.options.max > 9007199254740991) w.options.max = 9007199254740991;
                w.options.step = 10;
                w.options.precision = 0;
            }
            const numSeed = Number(w.value);
            if (!Number.isFinite(numSeed) || numSeed > 9007199254740991 || numSeed < 0) {
                w.value = 860481191328700;
            } else {
                w.value = Math.round(numSeed);
            }
        } else if (w && (w.name === "i2i_denoise" || w.name === "handoff_percent" || w.name === "stage3_handoff_percent" || w.name === "skin_polish_opacity" || w.name === "skin_texture_strength")) {
            if (w.options && typeof w.options === "object") {
                w.options.step = 0.01;
                w.options.precision = 2;
                w.options.round = 0.01;
            }
        }
    }
    const baseNodeType = stripEzEditionSuffix(node.type);
    if (baseNodeType === "EZCinematrixQwenVLTimelineCompiler") {
        hideRawCustomNegativeWidget(node);
    }
    if (baseNodeType === "EZCinematrixJointAVTemporalSampler") {
        const wSteps = byName.steps;
        const wCfg = byName.cfg;
        const wDenoise = byName.denoise;
        if (wSteps && wCfg && Number(wSteps.value) <= 12 && Number(wCfg.value) >= 2.5) {
            wCfg.value = 1.0;
        }
        if (wDenoise && Number(wDenoise.value) < 0.999) {
            wDenoise.value = 1.0;
        }
    } else if (baseNodeType === "EZCinematrixVideoEngineAndLoraStack") {
        for (const idx of [1, 2, 3, 4]) {
            const wLora = byName[`video_lora_${idx}`];
            const wStr = byName[`lora_${idx}_video_strength`];
            const wVis = byName[`lora_${idx}_vis_strength`];
            const wAud = byName[`lora_${idx}_audio_strength`];
            const wClip = byName[`lora_${idx}_clip_strength`];
            const lName = String((wLora && wLora.value) || "").toLowerCase();
            const isAudioLora = /audio|voice|vocal|sound|sfx|music|speech|moan|moaw/.test(lName);
            if (wStr && wVis && Math.abs(Number(wVis.value) - Number(wStr.value)) < 0.001 && Number(wStr.value) < 0.95) {
                wVis.value = 1.0;
            }
            if (wAud && !isAudioLora && Math.abs(Number(wAud.value) - 1.0) < 0.001) {
                wAud.value = 0.0;
            }
            if (wClip && Math.abs(Number(wClip.value) - Number(wStr ? wStr.value : 1.0)) < 0.001) {
                wClip.value = 0.0;
            }
        }
        if (byName.turbo_video_strength && Math.abs(Number(byName.turbo_video_strength.value) - 0.9) < 0.01) {
            byName.turbo_video_strength.value = 1.0;
        }
        if (byName.turbo_vis_strength && Math.abs(Number(byName.turbo_vis_strength.value) - 0.9) < 0.01) {
            byName.turbo_vis_strength.value = 1.0;
        }
        if (byName.turbo_audio_strength && Math.abs(Number(byName.turbo_audio_strength.value)) < 0.01) {
            byName.turbo_audio_strength.value = 1.0;
        }
        const wTurbo = byName.video_turbo_lora_LOCKED;
        if (wTurbo && String(wTurbo.value || "None") !== "None") {
            if (byName.shift_video && Math.abs(Number(byName.shift_video.value) - 11.0) < 0.01) byName.shift_video.value = 5.0;
            if (byName.shift_audio && Math.abs(Number(byName.shift_audio.value) - 4.0) < 0.01) byName.shift_audio.value = 3.0;
        }
    } else if (baseNodeType === "EZCinematrixSunoMusicVideoStudio") {
        if (byName.lyrics_or_prompt) {
            const curLyr = String(byName.lyrics_or_prompt.value || "").trim();
            if (/listen and make your own on suno/i.test(curLyr) || /^\$[0-9a-f]{1,8}$/i.test(curLyr)) {
                byName.lyrics_or_prompt.value = "";
            }
        }
        if (byName.song_style_tags && typeof byName.song_style_tags.value === "string" && byName.song_style_tags.value.includes("\\u")) {
            byName.song_style_tags.value = byName.song_style_tags.value.replace(/\\u([0-9a-fA-F]{4})/g, (_, h) => String.fromCharCode(parseInt(h, 16)));
        }
    }
    if (typeof node._ezOrderOmniSlotWidgets === "function") {
        node._ezOrderOmniSlotWidgets();
    }
    node.widgets_values = serWidgets.map(w => w.value);
    node.properties = node.properties || {};
    const nextMap = {};
    for (const w of serWidgets) nextMap[w.name] = w.value;
    node.properties._ez_widget_map = nextMap;
    node.properties._ez_schema_sig = serWidgets.map(w => w.name).join("|");
}

async function syncAllEzNodesWidgetsWithSchema(resetDefaults = false) {
    if (!app || !app.graph || !Array.isArray(app.graph._nodes)) return;
    try {
        let freshDefs = null;
        if (api && typeof api.getNodeDefs === "function") {
            freshDefs = await api.getNodeDefs();
        } else if (api && typeof api.fetchApi === "function") {
            const resp = await api.fetchApi("/object_info");
            if (resp && resp.status === 200) freshDefs = await resp.json();
        }
        if (freshDefs && typeof freshDefs === "object") {
            for (const [k, defObj] of Object.entries(freshDefs)) {
                if (k.startsWith("EZ") || (defObj && String(defObj.category || "").startsWith("EZ_Cinematrix"))) {
                    EZ_NODE_DATA_REGISTRY[k] = defObj;
                }
            }
        }
    } catch (e) {
        console.warn("[EZ Schema Sync] Could not fetch live /object_info, using cached registry:", e);
    }
    for (const n of app.graph._nodes) {
        if (n && EZ_NODE_DATA_REGISTRY[n.type]) {
            const curMap = {};
            if (Array.isArray(n.widgets)) {
                for (const w of n.widgets) {
                    if (w && w.name && !(w.options && w.options.serialize === false)) {
                        curMap[w.name] = w.value;
                    }
                }
            }
            const syntheticSaved = {
                properties: { _ez_widget_map: Object.assign({}, (n.properties && n.properties._ez_widget_map) || {}, curMap) },
                widgets_values: n.widgets_values
            };
            healAndSyncEzNodeWidgets(n, EZ_NODE_DATA_REGISTRY[n.type], syntheticSaved, resetDefaults);
            applyEzLocaleToNode(n);
            if (typeof n._ezRefreshOmniPreviews === "function") {
                n._ezRefreshOmniPreviews();
            }
            if (typeof n._ezRefreshNegDrawer === "function") {
                n._ezRefreshNegDrawer();
            }
        }
    }
    app.graph.setDirtyCanvas(true, true);
}

app.registerExtension({
    name: "EZStudio.CinematrixCore.Theme",
    async setup() {
        installEzGlobalMediaSyncAndThumbnailMenu();
        api.addEventListener("ez_cinematrix_live_preview", (ev) => {
            const d = ev && ev.detail;
            if (!d || !app.graph) return;
            const n = app.graph._nodes.find(x => stripEzEditionSuffix(x.type) === "EZCinematrixJointAVTemporalSampler")
                || app.graph._nodes.find(x => /joint_av|temporal_sampler|minipyav|video.*sampler/i.test(String(x.type || "")));
            if (n) mountEzLiveStreamWidget(n, d);
        });
        api.addEventListener("ez_cinematrix_vault_ready", (ev) => {
            const d = ev && ev.detail;
            if (!d || !app.graph) return;
            const n = app.graph._nodes.find(x => stripEzEditionSuffix(x.type) === "EZCinematrixCinemaVaultPostAndCombine")
                || app.graph._nodes.find(x => /vault|combine/i.test(String(x.type || "")));
            if (n) mountEzVaultArchiveHudWidget(n, d);
        });
        api.addEventListener("ez_cinematrix_krea2_ready", (ev) => {
            const d = ev && ev.detail;
            if (!d || !app.graph) return;
            const n = app.graph._nodes.find(x => stripEzEditionSuffix(x.type) === "EZCinematrixKrea2ThreeStageSampler")
                || app.graph._nodes.find(x => /krea2|three_stage/i.test(String(x.type || "")));
            if (n) mountEzKrea2PreviewWidget(n, d);
        });
    },
    async beforeRegisterNodeDef(nodeType, nodeData) {
        const typeName = String((nodeData && nodeData.name) || "");
        const baseTypeName = stripEzEditionSuffix(typeName);
        const category = String((nodeData && nodeData.category) || "");
        if (!typeName.startsWith("EZ") && !category.startsWith("EZ_Cinematrix")) {
            return;
        }
        EZ_NODE_DATA_REGISTRY[typeName] = nodeData;
        const origOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const res = origOnNodeCreated ? origOnNodeCreated.apply(this, arguments) : undefined;
            const pal = resolveEzPalette(typeName);
            this.color = pal.color;
            this.bgcolor = pal.bgcolor;
            this.boxcolor = pal.boxcolor;
            this.shape = LiteGraph.ROUND_SHAPE;
            this._ezInitialWidgetDefaults = {};
            if (Array.isArray(this.widgets)) {
                for (const w of this.widgets) {
                    if (w && w.name) this._ezInitialWidgetDefaults[w.name] = w.value;
                }
            }
            const selfNode = this;
            setTimeout(() => {
                if (baseTypeName === "EZCinematrixCivitaiController") {
                    mountEzCivitaiControllerWidget(selfNode);
                }
                if (baseTypeName === "EZCinematrixStudioNoteAndGuide") {
                    mountEzStudioNoteWidget(selfNode);
                }
                if (baseTypeName === "EZCinematrixPipelineSwitchboard" || baseTypeName === "EZ_14_Cinematrix_Pipeline_Switchboard") {
                    mountEzPipelineSwitchboardWidget(selfNode);
                }
                if (baseTypeName === "EZCinematrixOmniReferenceLoader" || baseTypeName === "EZ_13_Cinematrix_Omni_Reference_Loader") {
                    mountEzOmniReferencePreviewStrip(selfNode);
                }
                healAndSyncEzNodeWidgets(selfNode, nodeData, null, false);
                if (baseTypeName === "EZCinematrixQwenVLTimelineCompiler") {
                    mountEzQwenNegativePromptToggleWidget(selfNode, null);
                }
                applyEzLocaleToNode(selfNode);
                if (typeof selfNode._ezRefreshOmniPreviews === "function") {
                    selfNode._ezRefreshOmniPreviews();
                }
                if (Array.isArray(selfNode.widgets)) {
                    for (const w of selfNode.widgets) {
                        if (w && typeof w.name === "string" && (w.name.startsWith("SECTION_HEADER_") || w.name.startsWith("rubrik_slot_")) && !w._ezHeaderStyled) {
                            w._ezHeaderStyled = true;
                            const headerTitle = String(selfNode._ezInitialWidgetDefaults[w.name] || w.value || w.name);
                            w.draw = function (ctx, node, widgetWidth, y, H) {
                                ctx.save();
                                ctx.fillStyle = "rgba(18, 22, 34, 0.96)";
                                ctx.strokeStyle = "#f59e0b";
                                ctx.lineWidth = 1.2;
                                const bx = 12;
                                const bw = Math.max(120, widgetWidth - 24);
                                ctx.fillRect(bx, y + 1, bw, H - 2);
                                ctx.strokeRect(bx, y + 1, bw, H - 2);
                                ctx.font = "bold 9.5px monospace";
                                ctx.fillStyle = "#fbbf24";
                                ctx.fillText(headerTitle.slice(0, 74), bx + 8, y + H * 0.68);
                                ctx.restore();
                            };
                            w.mouse = function () { return false; };
                        }
                    }
                    const wFps = selfNode.widgets.find(w => w.name === "frame_rate");
                    const wCustomFps = selfNode.widgets.find(w => w.name === "custom_frame_rate");
                    if (wFps && wCustomFps && !wFps._ezBound) {
                        wFps._ezBound = true;
                        const origFpsCb = wFps.callback;
                        wFps.callback = function (val) {
                            const m = String(val || "").match(/^\s*([0-9]+(?:\.[0-9]+)?)/);
                            if (m && !/custom/i.test(String(val))) {
                                wCustomFps.value = parseFloat(m[1]);
                            }
                            if (origFpsCb) origFpsCb.apply(this, arguments);
                        };
                        const origCustFpsCb = wCustomFps.callback;
                        wCustomFps.callback = function (val) {
                            if (wFps.options && Array.isArray(wFps.options.values)) {
                                const custOpt = wFps.options.values.find(v => /custom/i.test(String(v)));
                                if (custOpt) wFps.value = custOpt;
                            }
                            if (origCustFpsCb) origCustFpsCb.apply(this, arguments);
                        };
                    }
                    const wQual = selfNode.widgets.find(w => w.name === "quality");
                    const wCustomQual = selfNode.widgets.find(w => w.name === "custom_quality_crf");
                    if (wQual && wCustomQual && !wQual._ezBound) {
                        wQual._ezBound = true;
                        const origQualCb = wQual.callback;
                        wQual.callback = function (val) {
                            const m = String(val || "").match(/CRF\s*([0-9]+)/i);
                            if (m && !/custom/i.test(String(val))) {
                                wCustomQual.value = parseInt(m[1], 10);
                            }
                            if (origQualCb) origQualCb.apply(this, arguments);
                        };
                        const origCustQualCb = wCustomQual.callback;
                        wCustomQual.callback = function (val) {
                            if (wQual.options && Array.isArray(wQual.options.values)) {
                                const custOpt = wQual.options.values.find(v => /custom/i.test(String(v)));
                                if (custOpt) wQual.value = custOpt;
                            }
                            if (origCustQualCb) origCustQualCb.apply(this, arguments);
                        };
                    }
                    const wMasterDur = selfNode.widgets.find(w => w.name === "master_duration");
                    const wDurSec = selfNode.widgets.find(w => w.name === "duration_seconds" || w.name === "custom_duration_seconds");
                    if (wMasterDur && !wMasterDur._ezDurBound) {
                        wMasterDur._ezDurBound = true;
                        const syncTimelineToDirector = (durLabel, numSec) => {
                            if (!app.graph || !Array.isArray(app.graph._nodes)) return;
                            const myEdition = detectEzNodeEdition(selfNode);
                            const dirNode = app.graph._nodes.find(n => n && stripEzEditionSuffix(n.type) === "EZCinematrixVideoDirectorAndGuide" && detectEzNodeEdition(n) === myEdition);
                            if (dirNode && Array.isArray(dirNode.widgets)) {
                                const dDrop = dirNode.widgets.find(w => w.name === "master_duration");
                                const dSec = dirNode.widgets.find(w => w.name === "duration_seconds");
                                if (dDrop && durLabel) dDrop.value = durLabel;
                                if (dSec && typeof numSec === "number" && numSec > 0) dSec.value = numSec;
                            }
                            const sunoNode = app.graph._nodes.find(n => n && stripEzEditionSuffix(n.type) === "EZCinematrixSunoMusicVideoStudio" && detectEzNodeEdition(n) === myEdition);
                            if (sunoNode && Array.isArray(sunoNode.widgets) && typeof numSec === "number" && numSec > 0) {
                                const sMode = sunoNode.widgets.find(w => w.name === "duration_sync_mode");
                                const sSec = sunoNode.widgets.find(w => w.name === "custom_duration_sec");
                                if (sSec && (!sMode || String(sMode.value || "").startsWith("Sync Audio Slice"))) {
                                    sSec.value = numSec;
                                }
                            }
                            app.graph.setDirtyCanvas(true, true);
                        };
                        const origMdCb = wMasterDur.callback;
                        wMasterDur.callback = function (val) {
                            const m = String(val || "").match(/([0-9]+(?:\.[0-9]+)?)/);
                            const parsedSec = m ? parseFloat(m[1]) : 0;
                            if (wDurSec && wDurSec.name === "duration_seconds" && parsedSec > 0 && !/custom/i.test(String(val))) {
                                wDurSec.value = parsedSec;
                            }
                            if (baseTypeName === "EZCinematrixQwenVLTimelineCompiler") {
                                syncTimelineToDirector(val, parsedSec || (wDurSec ? parseFloat(wDurSec.value) : 20.0));
                            }
                            if (origMdCb) origMdCb.apply(this, arguments);
                        };
                        if (wDurSec && !wDurSec._ezDurSecBound) {
                            wDurSec._ezDurSecBound = true;
                            const origSecCb = wDurSec.callback;
                            wDurSec.callback = function (val) {
                                const numV = parseFloat(val) || 0.0;
                                if (numV > 0) {
                                    const matchPreset = `${Math.round(numV)}-second`;
                                    if (wMasterDur.options && Array.isArray(wMasterDur.options.values)) {
                                        if (wMasterDur.options.values.includes(matchPreset)) {
                                            wMasterDur.value = matchPreset;
                                        } else {
                                            wMasterDur.value = "custom";
                                        }
                                    }
                                    if (baseTypeName === "EZCinematrixQwenVLTimelineCompiler") {
                                        syncTimelineToDirector(wMasterDur.value, numV);
                                    }
                                }
                                if (origSecCb) origSecCb.apply(this, arguments);
                            };
                        }
                    }
                    for (const w of selfNode.widgets) {
                        if (w && w.name && !(w.options && w.options.serialize === false) && !w._ezLiveMapBound) {
                            w._ezLiveMapBound = true;
                            const origWCb = w.callback;
                            w.callback = function (val) {
                                selfNode.properties = selfNode.properties || {};
                                selfNode.properties._ez_widget_map = selfNode.properties._ez_widget_map || {};
                                selfNode.properties._ez_widget_map[w.name] = val;
                                const serList = selfNode.widgets.filter(x => !(x.options && x.options.serialize === false));
                                selfNode.widgets_values = serList.map(x => x.value);
                                if (origWCb) return origWCb.apply(this, arguments);
                            };
                        }
                    }
                    if (baseTypeName === "EZCinematrixImageModelAndLoraSplitter" || baseTypeName.includes("03_Cinematrix")) {
                        const wUnet03 = selfNode.widgets.find(w => w && w.name === "unet_name");
                        const wClipType03 = selfNode.widgets.find(w => w && w.name === "clip_type");
                        const wClipSkip03 = selfNode.widgets.find(w => w && w.name === "stop_at_clip_layer");
                        if (wUnet03 && !wUnet03._ezMultiArchSyncBound) {
                            wUnet03._ezMultiArchSyncBound = true;
                            const origUnetCb03 = wUnet03.callback;
                            wUnet03.callback = function (val) {
                                if (val && val !== "None") {
                                    const inf03 = inferEzImageArchFromUnetName(val);
                                    if (wClipType03 && (!wClipType03.options || !Array.isArray(wClipType03.options.values) || wClipType03.options.values.includes(inf03.clipType))) {
                                        wClipType03.value = inf03.clipType;
                                    }
                                    if (wClipSkip03) {
                                        wClipSkip03.value = inf03.clipSkip;
                                    }
                                    if (app && app.graph) app.graph.setDirtyCanvas(true, true);
                                }
                                if (origUnetCb03) return origUnetCb03.apply(this, arguments);
                            };
                        }
                    }
                    if (baseTypeName === "EZCinematrixQwenVLTimelineCompiler") {
                        const wAudMode = selfNode.widgets.find(w => w && w.name === "audio_soundtrack_mode");
                        if (wAudMode && !wAudMode._ezSunoSyncBound) {
                            wAudMode._ezSunoSyncBound = true;
                            const origAudCb = wAudMode.callback;
                            const syncSunoNodeFromAudioDropdown = (rawAudVal) => {
                                if (!app || !app.graph || !Array.isArray(app.graph._nodes)) return;
                                const audLow = String(rawAudVal || "").trim().toLowerCase();
                                const isNoMusic = audLow.startsWith("sfx_only") || audLow.startsWith("sfx_and_speech") || audLow.includes("no_music");
                                const myEdition = detectEzNodeEdition(selfNode);
                                for (const gn of app.graph._nodes) {
                                    if (!gn || detectEzNodeEdition(gn) !== myEdition || !Array.isArray(gn.widgets)) continue;
                                    const gBase = stripEzEditionSuffix(gn.type);
                                    if (gBase === "EZCinematrixSunoMusicVideoStudio") {
                                        const wSunoMode = gn.widgets.find(x => x && x.name === "source_mode");
                                        if (wSunoMode) {
                                            const targetMode = isNoMusic
                                                ? "Bypass / Off (Standard Video)"
                                                : "Suno Song URL or ID (Auto-Fetch Audio + Lyrics)";
                                            wSunoMode.value = targetMode;
                                            gn.properties = gn.properties || {};
                                            gn.properties._ez_widget_map = gn.properties._ez_widget_map || {};
                                            gn.properties._ez_widget_map.source_mode = targetMode;
                                            const serSuno = gn.widgets.filter(x => !(x.options && x.options.serialize === false));
                                            gn.widgets_values = serSuno.map(x => x.value);
                                        }
                                        gn.mode = isNoMusic ? 4 : 0;
                                        mountEzSunoStudioHudWidget(gn, null);
                                        if (typeof gn.setDirtyCanvas === "function") gn.setDirtyCanvas(true, true);
                                    } else if (gBase === "EZCinematrixPipelineSwitchboard") {
                                        const wSwSuno = gn.widgets.find(x => x && x.name === "enable_suno_music_12");
                                        if (wSwSuno && Boolean(wSwSuno.value) !== !isNoMusic) {
                                            wSwSuno.value = !isNoMusic;
                                            gn.properties = gn.properties || {};
                                            gn.properties._ez_widget_map = gn.properties._ez_widget_map || {};
                                            gn.properties._ez_widget_map.enable_suno_music_12 = !isNoMusic;
                                            syncEzSwitchboardToGraph(gn);
                                        }
                                    }
                                }
                            };
                            wAudMode.callback = function (val) {
                                syncSunoNodeFromAudioDropdown(val);
                                if (origAudCb) return origAudCb.apply(this, arguments);
                            };
                        }
                    }
                    if (baseTypeName === "EZCinematrixSunoMusicVideoStudio") {
                        mountEzSunoStudioHudWidget(selfNode, null);
                        const wMode = selfNode.widgets.find(w => w.name === "source_mode");
                        const wSunoUrl = selfNode.widgets.find(w => w.name === "suno_song_url_or_id");
                        const wLocalAud = selfNode.widgets.find(w => w.name === "local_audio_file");
                        const wCustomAud = selfNode.widgets.find(w => w.name === "custom_audio_path");
                        const wTag = selfNode.widgets.find(w => w.name === "song_style_tags");
                        const wLyr = selfNode.widgets.find(w => w.name === "lyrics_or_prompt");
                        const syncTimelineAudioModeForSuno = () => {
                            if (!app || !app.graph || !Array.isArray(app.graph._nodes)) return;
                            const isBypassed = wMode && String(wMode.value || "").toLowerCase().startsWith("bypass");
                            if (isBypassed) return;
                            const myEdition = detectEzNodeEdition(selfNode);
                            for (const gn of app.graph._nodes) {
                                if (!gn || stripEzEditionSuffix(gn.type) !== "EZCinematrixQwenVLTimelineCompiler" || detectEzNodeEdition(gn) !== myEdition || !Array.isArray(gn.widgets)) continue;
                                const wAud = gn.widgets.find(w => w && w.name === "audio_soundtrack_mode");
                                if (wAud && (String(wAud.value || "").toLowerCase().startsWith("sfx_only") || String(wAud.value || "").toLowerCase().startsWith("sfx_and_speech"))) {
                                    const autoOpt = (wAud.options && Array.isArray(wAud.options.values))
                                        ? wAud.options.values.find(x => String(x).toLowerCase().startsWith("auto_from_prompt_or_suno"))
                                        : null;
                                    wAud.value = autoOpt || "auto_from_prompt_or_suno (Auto: Följ Prompt / Suno [12])";
                                    if (gn.properties && gn.properties._ez_widget_map) {
                                        gn.properties._ez_widget_map.audio_soundtrack_mode = wAud.value;
                                    }
                                }
                            }
                        };
                        if (wMode && !wMode._ezSunoModeBound) {
                            wMode._ezSunoModeBound = true;
                            const origModeCb = wMode.callback;
                            wMode.callback = function (val) {
                                mountEzSunoStudioHudWidget(selfNode, null);
                                if (origModeCb) origModeCb.apply(this, arguments);
                            };
                        }
                        if (wSunoUrl && !wSunoUrl._ezSunoFetchBound) {
                            wSunoUrl._ezSunoFetchBound = true;
                            const origSunoCb = wSunoUrl.callback;
                            const triggerLiveSunoMetaFetch = async (rawVal) => {
                                const v = String(rawVal || "").trim();
                                if (!v) {
                                    mountEzSunoStudioHudWidget(selfNode, null);
                                    return;
                                }
                                if (wMode && String(wMode.value || "").toLowerCase().startsWith("bypass")) {
                                    mountEzSunoStudioHudWidget(selfNode, null);
                                    return;
                                }
                                syncTimelineAudioModeForSuno();
                                if (v === selfNode._lastFetchedSunoUrl) return;
                                selfNode._lastFetchedSunoUrl = v;
                                try {
                                    const r = await api.fetchApi("/ez_cinematrix/suno/fetch_meta", {
                                        method: "POST",
                                        headers: { "Content-Type": "application/json" },
                                        body: JSON.stringify({ suno_song_url_or_id: v })
                                    });
                                    const d = await r.json();
                                    if (d && d.status === "ok") {
                                        if (wTag && d.tags) wTag.value = d.tags;
                                        if (wLyr) wLyr.value = d.lyrics || "";
                                        mountEzSunoStudioHudWidget(selfNode, {
                                            active: true,
                                            source_name: d.title || d.cached_file || v,
                                            filename: "",
                                            bpm: 124,
                                            duration_sec: 20,
                                            lyrics: d.lyrics || "",
                                            tags: d.tags || ""
                                        });
                                        if (app.graph) app.graph.setDirtyCanvas(true, true);
                                    }
                                } catch (e) {}
                            };
                            wSunoUrl.callback = function (val) {
                                triggerLiveSunoMetaFetch(val);
                                if (origSunoCb) origSunoCb.apply(this, arguments);
                            };
                            const curLyr = wLyr ? String(wLyr.value || "").trim() : "";
                            const curTag = wTag ? String(wTag.value || "") : "";
                            const isBypassNow = wMode && String(wMode.value || "").toLowerCase().startsWith("bypass");
                            if (!isBypassNow && wSunoUrl.value && (!curLyr || /^\$[0-9a-f]{1,8}$/i.test(curLyr) || curTag.includes("\\u"))) {
                                triggerLiveSunoMetaFetch(wSunoUrl.value);
                            }
                        }
                        for (const wLoc of [wLocalAud, wCustomAud]) {
                            if (wLoc && !wLoc._ezLocalAudBound) {
                                wLoc._ezLocalAudBound = true;
                                const origLocCb = wLoc.callback;
                                wLoc.callback = function (val) {
                                    mountEzSunoStudioHudWidget(selfNode, null);
                                    if (origLocCb) origLocCb.apply(this, arguments);
                                };
                            }
                        }
                    }
                }
                const boundMenu = selfNode.getExtraMenuOptions || nodeType.prototype.getExtraMenuOptions;
                selfNode.getExtraMenuOptions = function (canvas, options) {
                    try {
                        if (Array.isArray(this.imgs) && this.imgs.length > 0 && (this.imageIndex == null || this.imageIndex >= this.imgs.length)) {
                            this.imageIndex = 0;
                        }
                        if (boundMenu) boundMenu.call(this, canvas, options);
                    } catch (e) {}
                    if (Array.isArray(options)) {
                        for (let i = options.length - 1; i >= 0; i--) {
                            if (options[i] === undefined) options.splice(i, 1);
                        }
                        const MENU_I18N = {
                            EN: {
                                flow: "🗺️ Show EZ Cinematrix Flowchart & Wiring Guide",
                                wire: "⚡ Auto-Build & Wire Full EZ Cinematrix Pipeline (1-Click)",
                                heal: "🔄 Sync & Self-Heal All EZ Widgets (Zero Recreate)",
                                lang: `🌐 Language / Locale (${EZ_ACTIVE_LOCALE})`
                            },
                            SV: {
                                flow: "🗺️ Visa EZ Cinematrix Flödesschema & Kopplingsguide",
                                wire: "⚡ Auto-Skapa & Koppla hela EZ Cinematrix-flödet (1-Klick)",
                                heal: "🔄 Synka & Självläk Alla EZ-Widgets (Utan Recreate)",
                                lang: `🌐 Språk / Locale (${EZ_ACTIVE_LOCALE})`
                            },
                            ZH: {
                                flow: "🗺️ 显示 EZ Cinematrix 流程图与连线指南",
                                wire: "⚡ 一键自动创建并连接完整 EZ Cinematrix 工作流",
                                heal: "🔄 同步并自愈所有 EZ 节点组件 (免重建)",
                                lang: `🌐 界面语言 / Locale (${EZ_ACTIVE_LOCALE})`
                            },
                            JA: {
                                flow: "🗺️ EZ Cinematrix 配線ガイド & フローチャートを表示",
                                wire: "⚡ EZ Cinematrix 全13ノードをワンクリック自動構築・配線",
                                heal: "🔄 全EZウィジェットを同期・自己修復 (再作成不要)",
                                lang: `🌐 言語設定 / Locale (${EZ_ACTIVE_LOCALE})`
                            },
                            ES: {
                                flow: "🗺️ Mostrar Guía de Conexión EZ Cinematrix",
                                wire: "⚡ Auto-Crear y Conectar Flujo EZ Cinematrix (1-Clic)",
                                heal: "🔄 Sincronizar y Auto-Reparar Widgets EZ",
                                lang: `🌐 Idioma / Locale (${EZ_ACTIVE_LOCALE})`
                            },
                            DE: {
                                flow: "🗺️ EZ Cinematrix Ablaufplan & Guide anzeigen",
                                wire: "⚡ EZ Cinematrix Pipeline automatisch erstellen (1-Klick)",
                                heal: "🔄 Alle EZ-Widgets synchronisieren & reparieren",
                                lang: `🌐 Sprache / Locale (${EZ_ACTIVE_LOCALE})`
                            },
                            FR: {
                                flow: "🗺️ Afficher le Schéma de Câblage EZ Cinematrix",
                                wire: "⚡ Auto-Créer & Câbler tout le flux EZ Cinematrix (1-Clic)",
                                heal: "🔄 Synchroniser & Réparer tous les Widgets EZ",
                                lang: `🌐 Langue / Locale (${EZ_ACTIVE_LOCALE})`
                            }
                        };
                        const mLoc = MENU_I18N[EZ_ACTIVE_LOCALE] || MENU_I18N.EN;
                        const clickedEdition = detectEzNodeEdition(this);
                        const editionTag = clickedEdition === "FREEMIUM" ? " [Freemium v1.0]" : " [PRO v3.5]";
                        const hasEzFlow = options.some(o => o && typeof o.content === "string" && (o.content.includes("EZ Cinematrix") && o.content.includes("🗺️")));
                        if (!hasEzFlow) {
                            options.push(
                                { content: mLoc.flow, callback: () => showEzFlowchartModal() },
                                { content: `${mLoc.wire}${editionTag}`, callback: () => autoBuildAndWireCinematrixSuite(this) },
                                { content: mLoc.heal, callback: () => syncAllEzNodesWidgetsWithSchema(false) },
                                {
                                    content: mLoc.lang,
                                    submenu: {
                                        options: EZ_SUPPORTED_LOCALES.map(loc => ({
                                            content: `${loc === EZ_ACTIVE_LOCALE ? "✓ " : ""}${loc}`,
                                            callback: () => setEzActiveLocale(loc)
                                        }))
                                    }
                                }
                            );
                        }
                    }
                };
            }, 0);
            return res;
        };

        const origOnConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (info) {
            const res = origOnConfigure ? origOnConfigure.apply(this, arguments) : undefined;
            try {
                healAndSyncEzNodeWidgets(this, nodeData, info, false);
                if (baseTypeName === "EZCinematrixQwenVLTimelineCompiler") {
                    mountEzQwenNegativePromptToggleWidget(this, null);
                }
                applyEzLocaleToNode(this);
                if (typeof this._ezRefreshOmniPreviews === "function") {
                    setTimeout(() => this._ezRefreshOmniPreviews(), 20);
                }
            } catch (e) {}
            return res;
        };

        const origOnSerialize = nodeType.prototype.onSerialize;
        nodeType.prototype.onSerialize = function (o) {
            if (origOnSerialize) origOnSerialize.apply(this, arguments);
            if (o && Array.isArray(this.widgets)) {
                o.properties = o.properties || {};
                const wMap = {};
                const serW = this.widgets.filter(w => !(w.options && w.options.serialize === false));
                for (const w of serW) {
                    if (w && w.name) wMap[w.name] = w.value;
                }
                o.properties._ez_widget_map = wMap;
                o.properties._ez_schema_sig = serW.map(w => w.name).join("|");
            }
        };

        const origOnMouseDown = nodeType.prototype.onMouseDown;
        nodeType.prototype.onMouseDown = function (e, localPos) {
            if (localPos && this._ezLocalePillBounds) {
                const b = this._ezLocalePillBounds;
                if (localPos[0] >= b.x && localPos[0] <= b.x + b.w && localPos[1] >= b.y && localPos[1] <= b.y + b.h) {
                    const idx = (EZ_SUPPORTED_LOCALES.indexOf(EZ_ACTIVE_LOCALE) + 1) % EZ_SUPPORTED_LOCALES.length;
                    setEzActiveLocale(EZ_SUPPORTED_LOCALES[idx]);
                    return true;
                }
            }
            return origOnMouseDown ? origOnMouseDown.apply(this, arguments) : false;
        };

        const origOnExecuted = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function (output) {
            try {
                if (origOnExecuted) origOnExecuted.apply(this, arguments);
            } catch (e) {}
            if (output && Array.isArray(output.ez_qwen_prompts) && output.ez_qwen_prompts.length > 0) {
                mountEzQwenNegativePromptToggleWidget(this, output.ez_qwen_prompts[0]);
            }
            if (output && Array.isArray(output.ez_video) && output.ez_video.length > 0) {
                mountEzVaultArchiveHudWidget(this, output.ez_video[0]);
            }
            if (output && Array.isArray(output.ez_images) && output.ez_images.length > 0) {
                mountEzKrea2PreviewWidget(this, output.ez_images[0]);
            }
            if (output && Array.isArray(output.ez_studio_note) && output.ez_studio_note.length > 0) {
                mountEzStudioNoteWidget(this, output.ez_studio_note[0]);
            }
            if (output && Array.isArray(output.ez_suno_studio) && output.ez_suno_studio.length > 0) {
                const sm = output.ez_suno_studio[0];
                if (sm && sm.active && sm.filename && Array.isArray(this.widgets)) {
                    const wMode = this.widgets.find(w => w && w.name === "source_mode");
                    const isSunoUrlMode = !wMode || String(wMode.value || "").startsWith("Suno Song URL");
                    const wLyr = this.widgets.find(w => w && w.name === "lyrics_or_prompt");
                    const curLyrVal = wLyr ? String(wLyr.value || "").trim() : "";
                    if (wLyr && (/listen and make your own on suno/i.test(curLyrVal) || /^\$[0-9a-f]{1,8}$/i.test(curLyrVal))) {
                        wLyr.value = "";
                    }
                    if (sm.lyrics && !/listen and make your own on suno/i.test(String(sm.lyrics)) && !/^\$[0-9a-f]{1,8}$/i.test(String(sm.lyrics).trim())) {
                        if (wLyr && (isSunoUrlMode || !String(wLyr.value || "").trim())) wLyr.value = sm.lyrics;
                    }
                    if (sm.tags) {
                        const wTag = this.widgets.find(w => w && w.name === "song_style_tags");
                        if (wTag && (isSunoUrlMode || !String(wTag.value || "").trim() || String(wTag.value).startsWith("dark cyberpunk"))) {
                            wTag.value = sm.tags;
                        }
                    }
                }
                mountEzSunoStudioHudWidget(this, sm);
            }
        };

        const computeEzHubStatusPill = (nd, bType) => {
            if (!nd) return null;
            const getW = ( target, nm ) => (Array.isArray(target && target.widgets) ? target.widgets.find(w => w && w.name === nm) : null);
            const isSet = (v) => Boolean(v && String(v).trim() && String(v).trim() !== "None");
            const countHubActive = (hubNode) => {
                if (!hubNode || !Array.isArray(hubNode.widgets)) return { img: 0, vid: 0, recipe: false };
                let imgC = isSet((getW(hubNode, "image_unet_name") || {}).value) ? 1 : 0;
                for (let i = 1; i <= 4; i++) {
                    const en = getW(hubNode, `enable_image_lora_${i}`);
                    const lw = getW(hubNode, `image_style_lora_${i}`);
                    if ((!en || en.value !== false) && lw && isSet(lw.value)) imgC++;
                }
                const itEn = getW(hubNode, "enable_image_turbo_lora");
                const itLw = getW(hubNode, "image_turbo_lora");
                if ((!itEn || itEn.value !== false) && itLw && isSet(itLw.value)) imgC++;
                let vidC = isSet((getW(hubNode, "video_unet_fl2va") || {}).value) ? 1 : 0;
                for (let i = 1; i <= 4; i++) {
                    const en = getW(hubNode, `enable_video_lora_${i}`);
                    const lw = getW(hubNode, `video_lora_${i}`);
                    if ((!en || en.value !== false) && lw && isSet(lw.value)) vidC++;
                }
                const vtEn = getW(hubNode, "enable_video_turbo_lora");
                const vtLw = getW(hubNode, "video_turbo_lora");
                if ((!vtEn || vtEn.value !== false) && vtLw && isSet(vtLw.value)) vidC++;
                const rec = isSet((getW(hubNode, "active_recipe_name") || {}).value);
                return { img: imgC, vid: vidC, recipe: rec };
            };
            if (bType === "EZCinematrixCivitaiController") {
                const st = countHubActive(nd);
                if (st.img > 0 || st.vid > 0 || st.recipe) {
                    return { text: `⚡ HUB SÄNDER (IMG:${st.img} | VID:${st.vid}${st.recipe ? " | RECEPT" : ""})`, color: "#facc15", bg: "rgba(66, 32, 6, 0.95)" };
                }
                return { text: "💤 HUB PASSIV (0 LORAS)", color: "#94a3b8", bg: "rgba(15, 23, 42, 0.92)" };
            }
            if (bType === "EZCinematrixImageModelAndLoraSplitter" || bType === "EZCinematrixVideoEngineAndLoraStack") {
                const isVid = bType === "EZCinematrixVideoEngineAndLoraStack";
                const specPorts = isVid ? ["video_model_spec", "video_lora_spec"] : ["image_model_spec", "image_lora_spec"];
                let upstreamHub = null;
                if (Array.isArray(nd.inputs) && app && app.graph) {
                    for (const pName of specPorts) {
                        const inp = nd.inputs.find(x => x && x.name === pName && x.link != null);
                        if (inp && app.graph.links && app.graph.links[inp.link]) {
                            const lnk = app.graph.links[inp.link];
                            const srcN = app.graph.getNodeById ? app.graph.getNodeById(lnk.origin_id) : null;
                            if (srcN) { upstreamHub = srcN; break; }
                        }
                    }
                }
                if (!upstreamHub) return null;
                const st = countHubActive(upstreamHub);
                const activeCnt = isVid ? st.vid : st.img;
                const modeW = getW(nd, "remote_hub_mode");
                const isOverride = modeW && String(modeW.value || "").toLowerCase().startsWith("hub_override");
                if (isOverride && (activeCnt > 0 || st.recipe)) {
                    return { text: `⚠️ [10] OVERRIDE AKTIV (${activeCnt})`, color: "#fbbf24", bg: "rgba(120, 53, 15, 0.96)" };
                }
                return { text: "🛡️ LOKALA VAL VINNER", color: "#34d399", bg: "rgba(6, 78, 59, 0.92)" };
            }
            return null;
        };

        const origDrawForeground = nodeType.prototype.onDrawForeground;
        nodeType.prototype.onDrawForeground = function (ctx) {
            if (origDrawForeground) {
                origDrawForeground.apply(this, arguments);
            }
            if (this.flags && this.flags.collapsed) return;
            const pal = resolveEzPalette(typeName);
            const guide = EZ_WIRING_GUIDE[baseTypeName] || EZ_WIRING_GUIDE[typeName];
            ctx.save();
            ctx.font = "bold 9px monospace";
            const tagText = guide ? `${guide.step} // ${pal.badge}` : pal.badge;
            const textWidth = ctx.measureText(tagText).width;
            const pillW = textWidth + 12;
            const pillH = 15;
            const pillX = this.size[0] - pillW - 8;
            const pillY = -22;
            ctx.fillStyle = "rgba(12, 13, 18, 0.92)";
            ctx.strokeStyle = pal.badgeColor;
            ctx.lineWidth = 1;
            ctx.beginPath();
            if (ctx.roundRect) {
                ctx.roundRect(pillX, pillY, pillW, pillH, 4);
            } else {
                ctx.rect(pillX, pillY, pillW, pillH);
            }
            ctx.fill();
            ctx.stroke();
            ctx.fillStyle = pal.badgeColor;
            ctx.fillText(tagText, pillX + 6, pillY + 10.5);

            const locText = `🌐 ${EZ_ACTIVE_LOCALE}`;
            const locW = ctx.measureText(locText).width + 10;
            const locX = pillX - locW - 6;
            this._ezLocalePillBounds = { x: locX, y: pillY, w: locW, h: pillH };
            ctx.fillStyle = "rgba(15, 23, 42, 0.94)";
            ctx.strokeStyle = "#38bdf8";
            ctx.beginPath();
            if (ctx.roundRect) {
                ctx.roundRect(locX, pillY, locW, pillH, 4);
            } else {
                ctx.rect(locX, pillY, locW, pillH);
            }
            ctx.fill();
            ctx.stroke();
            ctx.fillStyle = "#38bdf8";
            ctx.fillText(locText, locX + 5, pillY + 10.5);

            const hubPill = computeEzHubStatusPill(this, baseTypeName);
            if (hubPill && this.size[0] > 320) {
                const hpW = ctx.measureText(hubPill.text).width + 12;
                const hpX = locX - hpW - 6;
                if (hpX > 110) {
                    ctx.fillStyle = hubPill.bg;
                    ctx.strokeStyle = hubPill.color;
                    ctx.beginPath();
                    if (ctx.roundRect) {
                        ctx.roundRect(hpX, pillY, hpW, pillH, 4);
                    } else {
                        ctx.rect(hpX, pillY, hpW, pillH);
                    }
                    ctx.fill();
                    ctx.stroke();
                    ctx.fillStyle = hubPill.color;
                    ctx.fillText(hubPill.text, hpX + 6, pillY + 10.5);
                }
            }

            if (guide && this.size[0] > 180) {
                ctx.font = "bold 9.5px monospace";
                ctx.fillStyle = "rgba(12, 13, 18, 0.94)";
                ctx.strokeStyle = pal.badgeColor;
                ctx.fillRect(6, this.size[1] + 2, this.size[0] - 12, 16);
                ctx.strokeRect(6, this.size[1] + 2, this.size[0] - 12, 16);
                ctx.fillStyle = "#e2e8f0";
                ctx.fillText(guide.next.slice(0, 68), 12, this.size[1] + 13);
            }
            if ((baseTypeName === "EZCinematrixOmniReferenceLoader" || baseTypeName === "EZ_13_Cinematrix_Omni_Reference_Loader" || baseTypeName === "EZCinematrixCanvasIngest") && Array.isArray(this.widgets)) {
                const thumbSlots = baseTypeName === "EZCinematrixCanvasIngest" ? ["source_image"] : EZ_OMNI_IMAGE_SLOT_NAMES;
                for (const sName of thumbSlots) {
                    const sw = this.widgets.find(x => x && x.name === sName);
                    if (!sw || typeof sw.last_y !== "number") continue;
                    const sVal = String(sw.value || "None").trim();
                    if (!sVal || sVal === "None" || !isEzImageFilename(sVal)) continue;
                    const tIm = getCachedEzThumbImage(sVal);
                    if (tIm && tIm.complete && tIm.naturalWidth > 0) {
                        const tx = Math.max(80, this.size[0] - 46);
                        const ty = sw.last_y + 1;
                        ctx.fillStyle = "#050608";
                        ctx.strokeStyle = "#22d3ee";
                        ctx.lineWidth = 1;
                        ctx.fillRect(tx - 1, ty - 1, 20, 20);
                        ctx.drawImage(tIm, tx, ty, 18, 18);
                        ctx.strokeRect(tx - 1, ty - 1, 20, 20);
                    }
                }
            }
            ctx.restore();
        };
    }
});

