# -*- coding: utf-8 -*-
import hashlib
import html
import json
import math
import os
import re
import shutil
import subprocess
import time
import urllib.request
import wave
from pathlib import Path
import numpy as np
import torch
import folder_paths

SUNO_SOURCE_MODES = [
    'Suno Song URL or ID (Auto-Fetch Audio + Lyrics)',
    'Local Audio File (.mp3 / .wav / .flac)',
    'Suno API Generate (v4 / v4.5 / v3.5)',
    'Bypass / Off (Standard Video)',
]

SUNO_PERFORMANCE_MODES = [
    'Auto_Detect_Audio_And_Generate_Scene (Speech / Song / Genre Auto-Prompt)',
    'Lead_Vocal_LipSync (Character Sings Lyrics)',
    'Spoken_Word_Or_Interview_LipSync (Speech / Celebrity / Monologue)',
    'Rhythm_And_Dance (Beat-Driven Motion Only)',
    'Cinematic_Story_Soundtrack (Mood & Pacing Only)',
]

SUNO_DURATION_SYNC_MODES = [
    'Sync Audio Slice to Timeline [02] / Director [06] (Short Clip)',
    'Custom Slice Duration in [12] (Start Offset + Seconds)',
    'Match Full Audio Track Length (Full-Length Music Video)',
]

SUNO_MODEL_PRESETS = [
    'chirp-v4 (Suno v4 Studio)',
    'chirp-v3-5 (Suno v3.5)',
    'chirp-v3-0 (Suno v3.0)',
]

_UUID_PATTERN = re.compile(
    r'([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})'
)

_ACTIVE_SUNO_SESSION_CACHE = {'packet': None}


def get_active_suno_session_packet() -> dict:
    pkt = _ACTIVE_SUNO_SESSION_CACHE.get('packet')
    return dict(pkt) if isinstance(pkt, dict) and pkt.get('active') else {}


def _resolve_ffmpeg_binary() -> str:
    found = shutil.which('ffmpeg')
    if found:
        return found
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.exists(exe):
            return exe
    except Exception:
        pass
    here = Path(__file__).resolve()
    for parent in here.parents:
        for cand in (
            parent / 'ffmpeg' / 'bin' / 'ffmpeg.exe',
            parent / 'ffmpeg.exe',
            parent / 'python_embeded' / 'Scripts' / 'ffmpeg.exe',
        ):
            if cand.exists():
                return str(cand)
    return 'ffmpeg'


def discover_local_audio_files() -> list:
    discovered = ['None (Use Suno URL, Custom Path or API)']
    audio_exts = ('.mp3', '.wav', '.flac', '.ogg', '.m4a')
    search_roots = []
    try:
        in_dir = Path(folder_paths.get_input_directory())
        search_roots.extend([in_dir, in_dir / 'music', in_dir / 'suno_cache'])
    except Exception:
        pass
    try:
        out_dir = Path(folder_paths.get_output_directory())
        search_roots.append(out_dir)
    except Exception:
        pass
    try:
        models_dir = Path(folder_paths.models_dir)
        search_roots.append(models_dir / 'music')
    except Exception:
        pass
    seen = set(discovered)
    for root in search_roots:
        if not root or not root.exists():
            continue
        try:
            for f in sorted(root.rglob('*')):
                if f.is_file() and f.suffix.lower() in audio_exts:
                    try:
                        rel = str(
                            f.relative_to(root.parent if root.name in ('music', 'suno_cache') else root)
                        ).replace('\\', '/')
                    except Exception:
                        rel = f.name
                    if rel not in seen:
                        seen.add(rel)
                        discovered.append(rel)
        except Exception:
            continue
    return discovered


def _resolve_suno_credentials_file() -> Path:
    here = Path(__file__).resolve().parent
    pkg_root = here.parent
    for cand_dir in (
        pkg_root.parent.parent / 'CONFIG',
        Path('D:/ComfyUI_windows_portable/EZ_Studio_DevTools/CONFIG'),
        Path('D:/EZ_Studio_DevTools/CONFIG'),
        pkg_root,
    ):
        if cand_dir.exists():
            return cand_dir / 'suno_credentials.json'
    return pkg_root / 'suno_credentials.json'


def _load_or_save_suno_credentials(api_endpoint: str, api_key: str) -> tuple:
    cfg_path = _resolve_suno_credentials_file()
    saved = {}
    if cfg_path.exists():
        try:
            saved = json.loads(cfg_path.read_text(encoding='utf-8', errors='ignore'))
        except Exception:
            saved = {}
    clean_ep = str(api_endpoint or '').strip()
    clean_key = str(api_key or '').strip()
    updated = False
    if clean_ep and clean_ep != saved.get('suno_api_endpoint', ''):
        saved['suno_api_endpoint'] = clean_ep
        updated = True
    elif not clean_ep:
        clean_ep = str(saved.get('suno_api_endpoint', 'https://api.sunoapi.org/api/v1/generate')).strip()
    if clean_key and not clean_key.startswith('***') and clean_key != saved.get('suno_api_key', ''):
        saved['suno_api_key'] = clean_key
        updated = True
    elif not clean_key or clean_key.startswith('***'):
        clean_key = str(saved.get('suno_api_key', os.environ.get('SUNO_API_KEY', ''))).strip()
    if updated:
        try:
            cfg_path.parent.mkdir(parents=True, exist_ok=True)
            cfg_path.write_text(json.dumps(saved, indent=2), encoding='utf-8')
        except Exception:
            pass
    return (clean_ep, clean_key)


def _save_sidecar_metadata(audio_path: Path, lyrics: str, tags: str, title: str = '') -> None:
    if not audio_path or not audio_path.parent.exists():
        return
    try:
        meta_path = audio_path.with_suffix('.suno.json')
        payload = {
            'title': str(title or audio_path.stem),
            'lyrics': str(lyrics or '').strip(),
            'tags': str(tags or '').strip(),
            'audio_file': audio_path.name,
        }
        meta_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    except Exception:
        pass


def _decode_unicode_escapes(raw_str: str) -> str:
    txt = str(raw_str or '').strip()
    if '\\u' in txt:
        txt = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), txt)
    return html.unescape(txt).strip()


def _clean_suno_lyrics_str(raw_str: str) -> str:
    txt = _decode_unicode_escapes(raw_str)
    if not txt or 'listen and make your own on suno' in txt.lower():
        return ''
    if re.match(r'^\$[0-9a-fA-F]{1,8}$', txt):
        return ''
    return txt


def _resolve_rsc_flight_pointer(pointer_str: str, flight_stream: str) -> str:
    val = str(pointer_str or '').strip()
    if not re.match(r'^\$[0-9a-fA-F]{1,8}$', val) or not flight_stream:
        return val
    ref_id = val[1:]
    m_t = re.search(rf'(?:^|\n){re.escape(ref_id)}:T([0-9a-fA-F]+),', flight_stream)
    if m_t:
        byte_len = int(m_t.group(1), 16)
        raw_slice = flight_stream[m_t.end():].encode('utf-8')[:byte_len]
        return raw_slice.decode('utf-8', errors='ignore').strip()
    m_q = re.search(rf'(?:^|\n){re.escape(ref_id)}:"((?:[^"\\]|\\.)*)"', flight_stream)
    if m_q:
        return _decode_unicode_escapes(m_q.group(1).replace('\\n', '\n').replace('\\"', '"'))
    return ''


def _load_sidecar_or_embedded_lyrics(audio_path: Path) -> tuple:
    if not audio_path or not audio_path.exists():
        return ('', '', '')
    for ext in ('.suno.json', '.json', '.txt', '.lrc'):
        cand = audio_path.with_suffix(ext)
        if cand.exists():
            try:
                raw = cand.read_text(encoding='utf-8', errors='ignore').strip()
                if ext.endswith('.json'):
                    data = json.loads(raw)
                    return (
                        _clean_suno_lyrics_str(data.get('lyrics') or data.get('prompt') or ''),
                        _decode_unicode_escapes(data.get('tags') or ''),
                        _decode_unicode_escapes(data.get('title') or audio_path.stem),
                    )
                if raw:
                    return (_clean_suno_lyrics_str(raw), '', audio_path.stem)
            except Exception:
                pass
    ffmpeg_bin = _resolve_ffmpeg_binary()
    ffprobe_bin = ffmpeg_bin.replace('ffmpeg.exe', 'ffprobe.exe') if ffmpeg_bin.endswith('ffmpeg.exe') else (shutil.which('ffprobe') or '')
    if ffprobe_bin and os.path.exists(ffprobe_bin):
        try:
            cmd = [ffprobe_bin, '-v', 'quiet', '-print_format', 'json', '-show_format', str(audio_path)]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)
            if proc.stdout:
                fmt_tags = json.loads(proc.stdout).get('format', {}).get('tags', {})
                if isinstance(fmt_tags, dict):
                    lyr = ''
                    genre = ''
                    title = ''
                    for k, v in fmt_tags.items():
                        kl = str(k).lower()
                        if 'lyric' in kl or 'unsynced' in kl or kl == 'comment':
                            lyr = str(v).strip()
                        elif kl in ('genre', 'style'):
                            genre = str(v).strip()
                        elif kl == 'title':
                            title = str(v).strip()
                    if lyr:
                        return (lyr, genre, title)
        except Exception:
            pass
    return ('', '', audio_path.stem)


def _is_valid_media_magic_bytes(raw_bytes: bytes) -> bool:
    if not raw_bytes or len(raw_bytes) < 4096:
        return False
    head = raw_bytes[:16]
    if head.startswith(b'ID3') or head.startswith(b'RIFF') or head.startswith(b'fLaC') or head.startswith(b'OggS'):
        return True
    if len(head) >= 8 and head[4:8] in (b'ftyp', b'moov', b'mdat'):
        return True
    if head[0] == 0xFF and (head[1] & 0xE0) == 0xE0:
        return True
    return False


def _fetch_suno_song_by_url_or_id(
    suno_url_or_id: str,
    api_endpoint: str = '',
    api_key: str = '',
) -> tuple:
    raw_in = str(suno_url_or_id or '').strip()
    if not raw_in:
        return (Path(''), '', '', '')
    in_dir = Path(folder_paths.get_input_directory())
    cache_dir = in_dir / 'suno_cache'
    cache_dir.mkdir(parents=True, exist_ok=True)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8',
        'Referer': 'https://suno.com/',
    }
    page_html = ''
    resolved_url = raw_in
    uuid_match = _UUID_PATTERN.search(raw_in)
    song_uuid = uuid_match.group(1).lower() if uuid_match else ''
    if raw_in.startswith('http') and not song_uuid:
        try:
            req = urllib.request.Request(raw_in, headers=headers)
            with urllib.request.urlopen(req, timeout=25) as resp:
                resolved_url = resp.geturl()
                page_html = resp.read().decode('utf-8', errors='ignore')
            m2 = _UUID_PATTERN.search(resolved_url) or _UUID_PATTERN.search(page_html)
            if m2:
                song_uuid = m2.group(1).lower()
        except Exception as url_err:
            print(f'[EZ-SUNO-12] Shortlink resolve notice: {url_err}')
    if not song_uuid:
        return (Path(''), '', '', '')
    cached_mp3 = cache_dir / f'suno_{song_uuid}.mp3'
    cached_mp4 = cache_dir / f'suno_{song_uuid}.mp4'
    for cand_cached in (cached_mp3, cached_mp4):
        if cand_cached.exists() and cand_cached.stat().st_size > 16384:
            c_lyr, c_tags, c_title = _load_sidecar_or_embedded_lyrics(cand_cached)
            c_lyr = _clean_suno_lyrics_str(c_lyr)
            c_tags = _decode_unicode_escapes(c_tags)
            if c_lyr:
                print(f'[EZ-SUNO-12] ⚡ Loaded cached Suno track & metadata for {song_uuid} ({c_title})')
                return (cand_cached, c_lyr, c_tags, c_title)
    lyrics_found = ''
    tags_found = ''
    title_found = ''
    audio_url_found = f'https://cdn1.suno.ai/{song_uuid}.mp3'
    video_url_found = f'https://cdn1.suno.ai/{song_uuid}.mp4'
    if not page_html:
        for page_cand in (
            f'https://suno.com/song/{song_uuid}',
            f'https://suno.com/embed/{song_uuid}',
        ):
            try:
                req = urllib.request.Request(page_cand, headers=headers)
                with urllib.request.urlopen(req, timeout=25) as resp:
                    page_html = resp.read().decode('utf-8', errors='ignore')
                if page_html and len(page_html) > 500:
                    break
            except Exception:
                continue
    if page_html:
        flight_parts = []
        for m_fl in re.finditer(r'self\.__next_f\.push\(\[\s*1\s*,\s*"((?:[^"\\]|\\.)*)"\s*\]\)', page_html):
            try:
                flight_parts.append(json.loads('"' + m_fl.group(1) + '"'))
            except Exception:
                pass
        flight_stream = ''.join(flight_parts)
        unescaped = (
            flight_stream
            if len(flight_stream) > 500
            else _decode_unicode_escapes(page_html.replace('\\"', '"').replace('\\n', '\n'))
        )
        schema_idx = unescaped.find('"entity_type":"song_schema"')
        schema_win = (
            unescaped[max(0, schema_idx - 350):min(len(unescaped), schema_idx + 5000)]
            if schema_idx != -1
            else unescaped
        )
        m_vurl = re.search(r'"video_url"\s*:\s*"(https://[^"]+\.mp4)"', schema_win)
        if m_vurl:
            video_url_found = m_vurl.group(1).strip()
        m_aurl = re.search(r'"audio_url"\s*:\s*"(https://[^"]+\.mp3)"', schema_win)
        if m_aurl and 'forbidden' not in m_aurl.group(1).lower():
            audio_url_found = m_aurl.group(1).strip()
        m_ti = re.search(r'"title"\s*:\s*"([^"]{1,200})"', schema_win)
        if m_ti:
            title_found = _decode_unicode_escapes(m_ti.group(1))
        m_tg = re.search(r'"tags"\s*:\s*"([^"]{2,600})"', schema_win)
        if m_tg:
            tags_found = _decode_unicode_escapes(m_tg.group(1)).rstrip('\\').strip()
        m_pr = re.search(r'"prompt"\s*:\s*"([^"]{1,4000})"', schema_win, re.DOTALL)
        m_gpt = re.search(r'"gpt_description_prompt"\s*:\s*"([^"]{1,2000})"', schema_win, re.DOTALL)
        if m_pr:
            raw_pr = _decode_unicode_escapes(m_pr.group(1)).rstrip('\\').strip()
            lyrics_found = _clean_suno_lyrics_str(_resolve_rsc_flight_pointer(raw_pr, unescaped))
        if m_gpt:
            raw_gpt = _decode_unicode_escapes(m_gpt.group(1)).replace('\\[', '[').rstrip('\\').strip()
            gpt_txt = _resolve_rsc_flight_pointer(raw_gpt, unescaped)
            if not lyrics_found or lyrics_found.lower() == '[instrumental]':
                lyrics_found = f'[Instrumental]\n{gpt_txt}'.strip() if gpt_txt else '[Instrumental]'
        if not title_found:
            m_og_t = re.search(
                r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
                page_html,
                re.IGNORECASE,
            )
            if m_og_t:
                title_found = html.unescape(m_og_t.group(1)).replace(' | Suno', '').strip()
        if not lyrics_found:
            m_og_d = re.search(
                r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']',
                page_html,
                re.IGNORECASE,
            )
            if m_og_d:
                desc_txt = html.unescape(m_og_d.group(1)).strip()
                if len(desc_txt) > 20 and 'listen and make your own on suno' not in desc_txt.lower():
                    lyrics_found = desc_txt
        if 'vocal' in title_found.lower() and 'no vocal' not in title_found.lower():
            tags_found = re.sub(r'(?i),?\s*\bno\s+vocals?\b', '', tags_found).strip(', ')
            if lyrics_found.lower().startswith('[instrumental]'):
                lyrics_found = re.sub(r'(?i)^\[instrumental\]\s*', '', lyrics_found).strip()
    active_cached = None
    for cand_c in (cached_mp3, cached_mp4):
        if cand_c.exists() and cand_c.stat().st_size > 16384:
            active_cached = cand_c
            break
    if active_cached is None:
        download_candidates = [
            (audio_url_found, cached_mp3),
            (f'https://cdn1.suno.ai/{song_uuid}.mp3', cached_mp3),
            (f'https://cdn2.suno.ai/{song_uuid}.mp3', cached_mp3),
            (video_url_found, cached_mp4),
            (f'https://cdn1.suno.ai/{song_uuid}.mp4', cached_mp4),
            (f'https://cdn2.suno.ai/{song_uuid}.mp4', cached_mp4),
        ]
        seen_urls = set()
        for cdn_url, target_file in download_candidates:
            if not cdn_url or cdn_url in seen_urls or 'forbidden' in cdn_url.lower():
                continue
            seen_urls.add(cdn_url)
            try:
                dl_req = urllib.request.Request(cdn_url, headers=headers)
                with urllib.request.urlopen(dl_req, timeout=60) as dl_resp:
                    raw_bytes = dl_resp.read()
                if _is_valid_media_magic_bytes(raw_bytes):
                    target_file.write_bytes(raw_bytes)
                    active_cached = target_file
                    break
            except Exception:
                continue
    if active_cached is not None and active_cached.exists() and active_cached.stat().st_size > 16384:
        _save_sidecar_metadata(active_cached, lyrics_found, tags_found, title_found or song_uuid)
        print(
            f'[EZ-SUNO-12] 🎵 Fetched Suno Song ({title_found or song_uuid}) [{active_cached.name}] — Lyrics: {len(lyrics_found)} chars, Tags: {tags_found}'
        )
        return (active_cached, lyrics_found, tags_found, title_found or song_uuid)
    return (Path(''), lyrics_found, tags_found, title_found)


def _write_silent_pcm_wav(out_wav: Path, duration_sec: float, sr: int = 48000) -> Path:
    dur = max(5.0, min(120.0, float(duration_sec or 20.0)))
    n_samples = int(dur * sr)
    pcm = np.zeros((n_samples, 2), dtype=np.int16)
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_wav), 'wb') as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return out_wav


def _generate_or_fetch_suno_api_track(
    api_endpoint: str,
    api_key: str,
    suno_model: str,
    song_style_tags: str,
    lyrics_or_prompt: str,
    instrumental_only: bool,
    target_duration_sec: float,
) -> tuple:
    in_dir = Path(folder_paths.get_input_directory())
    cache_dir = in_dir / 'suno_cache'
    cache_dir.mkdir(parents=True, exist_ok=True)
    model_id = str(suno_model or 'chirp-v4').split(' ')[0].strip()
    sig_raw = f'{model_id}|{song_style_tags}|{lyrics_or_prompt}|{bool(instrumental_only)}'
    sig_hash = hashlib.sha256(sig_raw.encode('utf-8')).hexdigest()[:12]
    cached_mp3 = cache_dir / f'suno_{model_id}_{sig_hash}.mp3'
    cached_wav = cache_dir / f'suno_{model_id}_{sig_hash}.wav'
    for cand in (cached_mp3, cached_wav):
        if cand.exists() and cand.stat().st_size > 4096:
            c_lyr, c_tags, c_title = _load_sidecar_or_embedded_lyrics(cand)
            return (cand, c_lyr or lyrics_or_prompt, c_tags or song_style_tags, c_title)
    api_lyrics = str(lyrics_or_prompt or '').strip()
    api_tags = str(song_style_tags or '').strip()
    api_title = f'EZ_Cinematrix_{sig_hash}'
    if api_endpoint.startswith('http') and api_key:
        try:
            payload = {
                'prompt': api_lyrics,
                'tags': api_tags or 'cinematic synthwave, 124 bpm',
                'mv': model_id,
                'model': model_id,
                'make_instrumental': bool(instrumental_only),
                'customMode': True,
                'instrumental': bool(instrumental_only),
                'title': api_title,
            }
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}',
                'api-key': api_key,
            }
            req = urllib.request.Request(
                api_endpoint,
                data=json.dumps(payload).encode('utf-8'),
                headers=headers,
                method='POST',
            )
            with urllib.request.urlopen(req, timeout=90) as resp:
                body = json.loads(resp.read().decode('utf-8', errors='ignore'))
            audio_url = ''
            clip_obj = {}
            if isinstance(body, dict):
                clip_obj = body
                audio_url = str(body.get('audio_url') or body.get('song_path') or '')
                if isinstance(body.get('data'), list) and body['data'] and isinstance(body['data'][0], dict):
                    clip_obj = body['data'][0]
                    audio_url = str(clip_obj.get('audio_url') or clip_obj.get('stream_audio_url') or audio_url)
                elif isinstance(body.get('clips'), list) and body['clips'] and isinstance(body['clips'][0], dict):
                    clip_obj = body['clips'][0]
                    audio_url = str(clip_obj.get('audio_url') or audio_url)
            meta_sub = clip_obj.get('metadata', {}) if isinstance(clip_obj.get('metadata'), dict) else {}
            returned_lyrics = str(
                clip_obj.get('lyric')
                or clip_obj.get('lyrics')
                or meta_sub.get('prompt')
                or clip_obj.get('prompt')
                or api_lyrics
            ).strip()
            returned_tags = str(
                clip_obj.get('tags')
                or meta_sub.get('tags')
                or api_tags
            ).strip()
            returned_title = str(clip_obj.get('title') or api_title).strip()
            if returned_lyrics:
                api_lyrics = returned_lyrics
            if returned_tags:
                api_tags = returned_tags
            if audio_url.startswith('http'):
                dl_req = urllib.request.Request(audio_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(dl_req, timeout=90) as dl_resp:
                    raw_bytes = dl_resp.read()
                if len(raw_bytes) > 4096:
                    target_f = cached_wav if audio_url.lower().endswith('.wav') else cached_mp3
                    target_f.write_bytes(raw_bytes)
                    _save_sidecar_metadata(target_f, api_lyrics, api_tags, returned_title)
                    return (target_f, api_lyrics, api_tags, returned_title)
        except Exception as api_err:
            print(f'[EZ-SUNO-12] Suno API notice: {api_err}')
    return (Path(''), api_lyrics, api_tags, api_title)


def _resolve_local_audio_path(local_audio_file: str, custom_audio_path: str) -> Path:
    cust = str(custom_audio_path or '').strip().strip('"').strip("'")
    if cust:
        cp = Path(cust)
        if cp.exists() and cp.is_file():
            return cp
    sel = str(local_audio_file or '').strip()
    if sel and not sel.startswith('None'):
        for base in (
            Path(folder_paths.get_input_directory()),
            Path(folder_paths.get_output_directory()),
            Path(folder_paths.models_dir) / 'music',
        ):
            cand = base / sel
            if cand.exists() and cand.is_file():
                return cand
            cand_direct = base / Path(sel).name
            if cand_direct.exists() and cand_direct.is_file():
                return cand_direct
    return Path('')


def _decode_audio_with_pyav_fallback(
    source_path: Path,
    out_wav: Path,
    offset_sec: float,
    req_dur_sec: float,
    target_sr: int = 48000,
) -> bool:
    if not source_path or not source_path.exists():
        return False
    try:
        import av
        container = av.open(str(source_path), mode='r')
        if not container.streams.audio:
            container.close()
            return False
        a_stream = container.streams.audio[0]
        resampler = av.AudioResampler(format='s16', layout='stereo', rate=int(target_sr))
        max_samples = int(req_dur_sec * target_sr)
        skip_samples = int(offset_sec * target_sr)
        collected = []
        total_collected = 0
        seen_samples = 0
        for frame in container.decode(a_stream):
            out_frames = resampler.resample(frame)
            if not isinstance(out_frames, list):
                out_frames = [out_frames] if out_frames is not None else []
            for of in out_frames:
                arr = of.to_ndarray()
                if arr.ndim == 2 and arr.shape[0] == 2 and arr.shape[1] > 2:
                    arr = arr.T
                elif arr.ndim == 1:
                    arr = arr.reshape(-1, 2)
                n_s = int(arr.shape[0])
                if seen_samples + n_s <= skip_samples:
                    seen_samples += n_s
                    continue
                if seen_samples < skip_samples:
                    cut = skip_samples - seen_samples
                    arr = arr[cut:]
                    seen_samples = skip_samples
                need = max_samples - total_collected
                if arr.shape[0] > need:
                    arr = arr[:need]
                collected.append(arr.astype(np.int16))
                total_collected += int(arr.shape[0])
                if total_collected >= max_samples:
                    break
            if total_collected >= max_samples:
                break
        container.close()
        if not collected or total_collected < 256:
            return False
        pcm = np.concatenate(collected, axis=0)
        out_wav.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(out_wav), 'wb') as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(int(target_sr))
            wf.writeframes(pcm.tobytes())
        return out_wav.exists() and out_wav.stat().st_size > 1024
    except Exception:
        return False


def _decode_and_slice_audio_to_wav(
    source_path: Path,
    start_offset_sec: float,
    target_duration_sec: float,
) -> tuple:
    temp_dir = Path(folder_paths.get_temp_directory())
    temp_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = _resolve_ffmpeg_binary()
    offset = max(0.0, float(start_offset_sec or 0.0))
    req_dur = max(2.0, float(target_duration_sec or 20.0))
    sig = hashlib.md5(
        f'{source_path}|{offset:.2f}|{req_dur:.2f}|{time.time_ns() // 1000000000}'.encode('utf-8')
    ).hexdigest()[:10]
    master_wav = temp_dir / f'ez_suno_master_{sig}.wav'
    vae_wav = temp_dir / f'ez_suno_32k_{sig}.wav'
    if source_path and source_path.exists() and source_path.is_file():
        try:
            cmd_master = [
                ffmpeg_bin, '-y', '-i', str(source_path),
                '-ss', f'{offset:.3f}', '-t', f'{req_dur:.3f}',
                '-vn', '-ac', '2', '-ar', '48000',
                '-c:a', 'pcm_s16le', str(master_wav),
            ]
            subprocess.run(cmd_master, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            cmd_32k = [
                ffmpeg_bin, '-y', '-i', str(source_path),
                '-ss', f'{offset:.3f}', '-t', f'{req_dur:.3f}',
                '-vn', '-ac', '2', '-ar', '32000',
                '-c:a', 'pcm_s16le', str(vae_wav),
            ]
            subprocess.run(cmd_32k, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        except Exception:
            pass
        if not master_wav.exists() or master_wav.stat().st_size < 1024:
            _decode_audio_with_pyav_fallback(source_path, master_wav, offset, req_dur, target_sr=48000)
        if not vae_wav.exists() or vae_wav.stat().st_size < 1024:
            _decode_audio_with_pyav_fallback(source_path, vae_wav, offset, req_dur, target_sr=32000)
    if not master_wav.exists() or master_wav.stat().st_size < 1024:
        _write_silent_pcm_wav(master_wav, req_dur, sr=48000)
    if not vae_wav.exists() or vae_wav.stat().st_size < 1024:
        _write_silent_pcm_wav(vae_wav, req_dur, sr=32000)
    with wave.open(str(vae_wav), 'rb') as wf:
        n_ch = wf.getnchannels()
        sr = wf.getframerate()
        n_frames = wf.getnframes()
        raw_pcm = wf.readframes(n_frames)
    arr = np.frombuffer(raw_pcm, dtype=np.int16).astype(np.float32) / 32768.0
    if n_ch >= 2:
        arr = arr.reshape(-1, n_ch)[:, :2].T
    else:
        arr = np.stack([arr, arr], axis=0)
    actual_dur = float(arr.shape[1]) / float(max(1, sr))
    waveform_32k = torch.from_numpy(arr).unsqueeze(0).contiguous()
    try:
        vae_wav.unlink()
    except Exception:
        pass
    return (master_wav, waveform_32k, actual_dur, sr)


def _transcribe_audio_speech_to_text(audio_wav_path: Path) -> str:
    if not audio_wav_path or not audio_wav_path.exists():
        return ''
    try:
        from faster_whisper import WhisperModel
        m_dir = Path(folder_paths.models_dir) / 'whisper'
        model_id = str(m_dir) if m_dir.exists() and any(m_dir.iterdir()) else 'base'
        wm = WhisperModel(model_id, device='cpu', compute_type='int8')
        segments, _ = wm.transcribe(str(audio_wav_path), beam_size=3, vad_filter=True)
        lines = [seg.text.strip() for seg in segments if seg.text and seg.text.strip()]
        if lines:
            return '\n'.join(lines)
    except Exception:
        pass
    try:
        import whisper
        w_model = whisper.load_model('base', device='cpu')
        res = w_model.transcribe(str(audio_wav_path), fp16=False)
        txt = str(res.get('text', '') or '').strip()
        if txt:
            return txt
    except Exception:
        pass
    try:
        from transformers import pipeline
        m_dir = Path(folder_paths.models_dir) / 'whisper'
        local_ckpts = [p for p in (m_dir.glob('*') if m_dir.exists() else []) if p.is_dir()]
        if local_ckpts:
            asr = pipeline('automatic-speech-recognition', model=str(local_ckpts[0]), device='cpu')
            out = asr(str(audio_wav_path))
            if isinstance(out, dict) and out.get('text'):
                return str(out['text']).strip()
    except Exception:
        pass
    return ''


def _classify_acoustic_voice_and_scene_blueprint(
    waveform_32k: torch.Tensor,
    sr: int,
    bpm_est: float,
    song_style_tags: str,
    lyrics_or_prompt: str,
    performance_mode: str,
    song_title: str = '',
) -> dict:
    mono = waveform_32k[0].mean(dim=0).detach().cpu().numpy()
    n_s = min(len(mono), int(sr * 12))
    seg = mono[:max(1024, n_s)]
    spec = np.abs(np.fft.rfft(seg))
    freqs = np.fft.rfftfreq(len(seg), d=1.0 / float(max(1, sr)))
    total_e = float(np.sum(spec ** 2) + 1e-9)
    voice_mask = (freqs >= 250.0) & (freqs <= 3400.0)
    sub_mask = (freqs >= 35.0) & (freqs < 180.0)
    voice_ratio = float(np.sum(spec[voice_mask] ** 2)) / total_e
    bass_ratio = float(np.sum(spec[sub_mask] ** 2)) / total_e
    f0_mask = (freqs >= 85.0) & (freqs <= 310.0)
    f0_hz = float(freqs[f0_mask][np.argmax(spec[f0_mask])]) if np.any(f0_mask) else 165.0
    if f0_hz < 145.0:
        voice_desc = 'performer with a deep, resonant baritone vocal timbre'
    elif f0_hz < 180.0:
        voice_desc = 'performer with a warm, natural mid-tenor vocal timbre'
    else:
        voice_desc = 'performer with a clear, emotive alto/soprano vocal timbre'
    perf_str = str(performance_mode or '')
    tags_low = str(song_style_tags or '').lower()
    lyr_low = str(lyrics_or_prompt or '').lower()
    is_inst = ('[instrumental]' in lyr_low) or ('no vocals' in tags_low)
    is_spoken = (
        perf_str.startswith('Spoken_Word')
        or any(k in tags_low for k in ('spoken', 'podcast', 'interview', 'monologue', 'speech', 'talk', 'narration'))
        or (not is_inst and voice_ratio > 0.58 and bass_ratio < 0.16)
    )
    modality = 'SPOKEN_WORD' if is_spoken else ('INSTRUMENTAL_MUSIC' if is_inst else 'VOCAL_SONG')
    clean_dialogue = ' '.join(
        [ln.strip() for ln in str(lyrics_or_prompt or '').splitlines() if ln.strip() and not ln.strip().startswith('[')]
    )[:260]
    vocal_framing = (
        f'preserving the exact camera framing and character anatomy of <Picture 1> with <Subject 1> ({voice_desc}) facing the camera directly, '
        f'direct eye contact, and expressive parted lips actively singing on-camera from 0.0s'
        if modality == 'VOCAL_SONG' and not perf_str.startswith('Rhythm_And_Dance')
        else f'featuring <Subject 1> ({voice_desc})'
    )
    if modality == 'SPOKEN_WORD':
        scene_env = (
            f'Cinematic 35mm sequence of <Subject 1> ({voice_desc}) speaking directly and naturally on camera '
            f'with authentic facial micro-expressions, subtle head nods, and accurate phoneme-level lip-sync'
        )
        if clean_dialogue:
            scene_env += f' delivering the spoken lines: "{clean_dialogue}"'
    elif any(g in tags_low for g in ('cyber', 'synthwave', 'industrial', 'dark synth', 'electro', 'techno')):
        scene_env = (
            f'Cinematic neon-drenched cyberpunk metropolis at night ({bpm_est} BPM {song_style_tags}), '
            f'rain-slicked reflections, volumetric cyan and magenta lighting, {vocal_framing}'
        )
    elif any(g in tags_low for g in ('rock', 'metal', 'punk', 'grunge', 'guitar')):
        scene_env = (
            f'High-energy concert stage with dramatic volumetric spotlights, atmospheric haze, and intense '
            f'{bpm_est} BPM rock performance aesthetics ({song_style_tags}), {vocal_framing}'
        )
    elif any(g in tags_low for g in ('hip hop', 'hip-hop', 'rap', 'trap', 'boom bap', 'drill')):
        scene_env = (
            f'Stylized urban night cinematography with moody anamorphic street lighting, steady framing, '
            f'and rhythmic {bpm_est} BPM hip-hop performance energy ({song_style_tags}), {vocal_framing}'
        )
    elif any(g in tags_low for g in ('pop', 'dance', 'disco', 'house', 'edm', 'club')):
        scene_env = (
            f'Vibrant high-fashion music video studio set with dynamic synchronized LED light walls and '
            f'{bpm_est} BPM performance energy ({song_style_tags}), {vocal_framing}'
        )
    else:
        scene_env = (
            f'Cinematic 35mm music video sequence matching the {bpm_est} BPM mood and genre ({song_style_tags or song_title}), '
            f'dramatic atmospheric lighting and steady framing, {vocal_framing}'
        )
    return {
        'modality': modality,
        'f0_hz': round(f0_hz, 1),
        'voice_profile': voice_desc,
        'auto_scene_prompt': scene_env,
        'is_spoken_word': bool(is_spoken),
    }


def extract_4band_viseme_and_beat_envelope(waveform_32k: torch.Tensor, sr: int = 32000, fps: float = 24.0) -> torch.Tensor:
    if not isinstance(waveform_32k, torch.Tensor) or waveform_32k.numel() < 256:
        return torch.zeros((4, 24), dtype=torch.float32)
    mono = waveform_32k[0].mean(dim=0).detach().cpu().float().numpy()
    eff_sr = max(8000, int(sr or 32000))
    eff_fps = max(8.0, float(fps or 24.0))
    win_len = max(256, int(round(eff_sr / eff_fps)))
    n_frames = max(1, len(mono) // win_len)
    trimmed = mono[:n_frames * win_len].reshape(n_frames, win_len)
    hann = np.hanning(win_len).reshape(1, win_len)
    specs = np.abs(np.fft.rfft(trimmed * hann, axis=1))
    freqs = np.fft.rfftfreq(win_len, d=1.0 / float(eff_sr))
    m_jaw = (freqs >= 300.0) & (freqs <= 1000.0)
    m_lip = (freqs > 1000.0) & (freqs <= 3000.0)
    m_sib = (freqs > 3000.0) & (freqs <= 7500.0)
    m_beat = (freqs >= 40.0) & (freqs < 180.0)
    e_jaw = np.sqrt(np.mean(specs[:, m_jaw] ** 2, axis=1) + 1e-10) if np.any(m_jaw) else np.zeros(n_frames, dtype=np.float32)
    e_lip = np.sqrt(np.mean(specs[:, m_lip] ** 2, axis=1) + 1e-10) if np.any(m_lip) else np.zeros(n_frames, dtype=np.float32)
    e_sib = np.sqrt(np.mean(specs[:, m_sib] ** 2, axis=1) + 1e-10) if np.any(m_sib) else np.zeros(n_frames, dtype=np.float32)
    e_beat_raw = np.sqrt(np.mean(specs[:, m_beat] ** 2, axis=1) + 1e-10) if np.any(m_beat) else np.zeros(n_frames, dtype=np.float32)
    e_beat = np.maximum(0.0, np.diff(e_beat_raw, prepend=e_beat_raw[0])) * 1.65 + 0.35 * e_beat_raw
    channels = []
    for arr in (e_jaw, e_lip, e_sib, e_beat):
        p95 = float(np.percentile(arr, 95)) if len(arr) > 2 else float(np.max(arr))
        denom = max(1e-05, p95)
        norm_c = np.clip(arr / denom, 0.0, 1.0).astype(np.float32)
        channels.append(norm_c)
    return torch.from_numpy(np.stack(channels, axis=0)).contiguous()


def _analyze_waveform_bpm_and_acts(
    waveform_32k: torch.Tensor,
    duration_sec: float,
    lyrics_or_prompt: str,
    performance_mode: str,
    song_style_tags: str,
    song_title: str = '',
) -> dict:
    w = waveform_32k[0].detach().cpu().numpy() if (isinstance(waveform_32k, torch.Tensor) and waveform_32k.ndim >= 3) else np.zeros((2, 32000), dtype=np.float32)
    mono = waveform_32k[0].mean(dim=0).detach().cpu().numpy()
    sr = 32000
    hop = 512
    n_frames = max(1, len(mono) // hop)
    trimmed = mono[:n_frames * hop].reshape(n_frames, hop)
    rms_env = np.sqrt(np.mean(trimmed ** 2, axis=1) + 1e-8)
    onset_env = np.maximum(0.0, np.diff(rms_env, prepend=rms_env[0]))
    env_fps = float(sr) / float(hop)
    min_lag = max(1, int(round(env_fps * 60.0 / 175.0)))
    max_lag = min(len(onset_env) - 1, int(round(env_fps * 60.0 / 72.0)))
    bpm_est = 124.0
    if max_lag > min_lag + 2:
        centered = onset_env - np.mean(onset_env)
        best_lag = min_lag
        best_corr = -1e9
        for lag in range(min_lag, max_lag + 1):
            c = float(np.dot(centered[:-lag], centered[lag:]))
            if c > best_corr:
                best_corr = c
                best_lag = lag
        bpm_est = round(float(env_fps * 60.0 / float(best_lag)), 1)
    bpm_tag = re.search(r'(\d{2,3})\s*bpm', str(song_style_tags or ''), re.IGNORECASE)
    if bpm_tag:
        bpm_est = float(bpm_tag.group(1))
    voice_scene = _classify_acoustic_voice_and_scene_blueprint(
        waveform_32k=waveform_32k,
        sr=sr,
        bpm_est=bpm_est,
        song_style_tags=song_style_tags,
        lyrics_or_prompt=lyrics_or_prompt,
        performance_mode=performance_mode,
        song_title=song_title,
    )
    thresh = float(np.mean(onset_env) + 1.15 * np.std(onset_env))
    beat_times = []
    last_beat_t = -1.0
    min_beat_gap = 60.0 / max(80.0, min(180.0, bpm_est)) * 0.75
    for idx, val in enumerate(onset_env):
        t_sec = float(idx) / env_fps
        if val >= thresh and (t_sec - last_beat_t) >= min_beat_gap:
            beat_times.append(round(t_sec, 2))
            last_beat_t = t_sec
    raw_lines = [
        ln.strip()
        for ln in str(lyrics_or_prompt or '').splitlines()
        if ln.strip() and not ln.strip().startswith('[')
    ]
    n_acts = max(1, int(math.ceil(max(5.0, duration_sec) / 5.0)))
    global_rms_mean = float(np.mean(rms_env) + 1e-6)
    acts = []
    perf_str = str(performance_mode or '')
    is_spoken = voice_scene['is_spoken_word'] or perf_str.startswith('Spoken_Word')
    is_auto = perf_str.startswith('Auto_Detect')
    is_lipsync = (
        perf_str.startswith('Lead_Vocal_LipSync')
        or is_spoken
        or (is_auto and voice_scene['modality'] in ('SPOKEN_WORD', 'VOCAL_SONG'))
    )
    is_dance = perf_str.startswith('Rhythm_And_Dance') or (is_auto and voice_scene['modality'] == 'INSTRUMENTAL_MUSIC')
    center_w = 0.5 * (w[0] + w[1]) if (w.ndim == 2 and w.shape[0] >= 2) else mono
    for act_i in range(n_acts):
        s_t = round(act_i * 5.0, 1)
        e_t = round(min(duration_sec, (act_i + 1) * 5.0), 1)
        i0 = int(s_t * env_fps)
        i1 = max(i0 + 1, int(e_t * env_fps))
        seg_rms = float(np.mean(rms_env[i0:min(len(rms_env), i1)])) if i0 < len(rms_env) else global_rms_mean
        ratio = seg_rms / global_rms_mean
        w_s0 = min(len(center_w), int(s_t * sr))
        w_s1 = min(len(center_w), max(w_s0 + 1, int(e_t * sr)))
        act_slice = center_w[w_s0:w_s1]
        sub_cues = []
        act_voc_active = 0
        n_secs = max(1, int(round(e_t - s_t)))
        for sec_k in range(n_secs):
            k0 = min(len(act_slice), int(sec_k * sr))
            k1 = min(len(act_slice), int((sec_k + 1) * sr))
            sec_w = act_slice[k0:k1]
            if len(sec_w) >= 256:
                spec_s = np.abs(np.fft.rfft(sec_w * np.hanning(len(sec_w))))
                f_s = np.fft.rfftfreq(len(sec_w), d=1.0 / float(sr))
                tot_e = float(np.sum(spec_s ** 2)) + 1e-09
                voc_e = float(np.sum(spec_s[(f_s >= 280.0) & (f_s <= 3400.0)] ** 2))
                sec_rms = float(np.sqrt(np.mean(sec_w ** 2)))
                is_v_sec = (voc_e / tot_e >= 0.34) and (sec_rms >= global_rms_mean * 0.48)
            else:
                is_v_sec = ratio >= 0.85
            if is_v_sec:
                act_voc_active += 1
            sub_cues.append(f'{s_t + sec_k:.0f}s-{min(e_t, s_t + sec_k + 1):.0f}s:{"VOCAL_SYLLABLES" if is_v_sec else "INSTRUMENTAL_BREATH"}')
        voc_density = float(act_voc_active) / float(max(1, n_secs))
        if is_spoken:
            energy_tag = 'EMPHATIC_SPEECH' if ratio >= 1.12 else 'CALM_DIALOGUE'
            cam_cue = 'Continuous static camera framing locked to <Picture 1> maintaining constant medium-wide shot distance'
        elif is_lipsync:
            energy_tag = 'HIGH_DROP_CHORUS' if ratio >= 1.15 else ('LOW_INTRO_BRIDGE' if ratio <= 0.85 else 'MID_VERSE_VOCAL')
            cam_cue = f'Continuous static tripod master camera framing ({bpm_est} BPM) preserving the exact constant wide-to-medium camera distance, full posture scale, character anatomy, and outfit of <Picture 1>'
        elif ratio >= 1.18:
            energy_tag = 'HIGH_DROP_CHORUS'
            cam_cue = f'High-energy {bpm_est} BPM chorus groove with vibrant lighting reactivity while preserving the exact framing of <Picture 1>'
        elif ratio <= 0.85:
            energy_tag = 'LOW_INTRO_BRIDGE'
            cam_cue = f'Atmospheric {bpm_est} BPM melodic intro/bridge preserving the continuous camera framing of <Picture 1>'
        else:
            energy_tag = 'MID_VERSE_GROOVE'
            cam_cue = f'Steady {bpm_est} BPM verse groove with beat-locked subject movement in the exact framing of <Picture 1>'
        lyric_slice = ''
        if raw_lines:
            l_start = int(act_i * len(raw_lines) / max(1, n_acts))
            l_end = max(l_start + 1, int((act_i + 1) * len(raw_lines) / max(1, n_acts)))
            lyric_slice = ' / '.join(raw_lines[l_start:min(len(raw_lines), max(l_start + 1, min(l_end, l_start + 2)))])
        env_window_str = ', '.join(sub_cues)
        if is_spoken:
            perf_cue = '<Subject 1> remains in the exact posture and shot distance of <Picture 1> with natural vocal phrasing synchronized to the 32kHz audio waveform without synthetic text-to-speech narration'
        elif is_lipsync:
            perf_cue = '<Subject 1> remains in the exact posture, full-body scale, and camera distance of <Picture 1>, singing naturally in frame-accurate synchronization with the conditioned 32kHz vocal waveform (never zooming in, never cutting to a face close-up, never turning back, and never reading raw text strings aloud)'
        elif is_dance:
            perf_cue = f'<Subject 1> moves in tight physical synchronization with the {bpm_est} BPM beat transients'
        else:
            perf_cue = f'Cinematic visual pacing synchronized to the {bpm_est} BPM soundtrack ({energy_tag})'
        acts.append({
            'act': act_i + 1,
            'start_s': s_t,
            'end_s': e_t,
            'energy': energy_tag,
            'vocal_density': round(voc_density, 2),
            'envelope_cues': env_window_str,
            'lyric': lyric_slice,
            'directive': f'{cam_cue}; {perf_cue}.',
        })
    shot_lyrics = []
    shot_vocal_cues = []
    for s_idx in range(3):
        shot_vocal_cues.append('')
        shot_lyrics.append('')
    lipsync_rule = (
        '\nCRITICAL AUDIO-WAVEFORM VOCAL SYNC & CONSTANT SHOT DISTANCE LOCK: Synchronize <Subject 1>\'s natural singing expression strictly to the conditioned 32kHz audio latent waveform while keeping the camera 100% locked at the exact medium-wide shot distance and posture scale of <Picture 1> from start to finish (strictly zero zoom-in and zero close-up cuts).'
        if is_lipsync else ''
    )
    prompt_injection = (
        f"[SUNO RHYTHMIC & VOCAL TIMING SYNC — {voice_scene['modality']} // {bpm_est} BPM // Timbre: {voice_scene['voice_profile']}]\n"
        f"STRICT VISUAL STYLE & CAMERA DISTANCE LOCK: Visual style, constant medium-wide camera distance, environment, and subject anatomy/species are governed strictly by <Picture 1> in one continuous unbroken shot.{lipsync_rule}"
    )
    return {
        'bpm': bpm_est,
        'beat_count': len(beat_times),
        'beat_times': beat_times[:64],
        'acts': acts,
        'shot_lyrics': shot_lyrics,
        'shot_vocal_cues': shot_vocal_cues,
        'prompt_injection': prompt_injection,
        'auto_scene_prompt': voice_scene['auto_scene_prompt'],
        'audio_modality': voice_scene['modality'],
        'voice_profile': voice_scene['voice_profile'],
        'wants_lipsync': bool(is_lipsync),
    }


def reslice_suno_packet_to_duration(suno_cfg: dict, target_duration_sec: float) -> dict:
    if not isinstance(suno_cfg, dict) or not suno_cfg.get('active'):
        return suno_cfg
    tgt_dur = max(1.0, float(target_duration_sec or 0.0))
    cur_dur = float(suno_cfg.get('duration_sec', 0.0) or 0.0)
    if abs(cur_dur - tgt_dur) <= 0.12:
        return suno_cfg
    src_str = str(suno_cfg.get('source_audio_path') or suno_cfg.get('master_wav_path') or '').strip()
    src_path = Path(src_str) if src_str else Path('')
    if not src_path or not src_path.exists() or not src_path.is_file():
        return suno_cfg
    start_off = float(suno_cfg.get('start_offset_sec', 0.0) or 0.0)
    master_wav, waveform_32k, actual_dur, sr_32k = _decode_and_slice_audio_to_wav(
        source_path=src_path,
        start_offset_sec=start_off,
        target_duration_sec=tgt_dur,
    )
    updated = dict(suno_cfg)
    updated['master_wav_path'] = str(master_wav)
    updated['waveform_32k'] = waveform_32k
    updated['viseme_envelope_4d'] = extract_4band_viseme_and_beat_envelope(waveform_32k, sr=int(sr_32k), fps=24.0)
    updated['sample_rate_32k'] = int(sr_32k)
    updated['duration_sec'] = round(float(actual_dur), 2)
    _ACTIVE_SUNO_SESSION_CACHE['packet'] = dict(updated)
    return updated


def get_active_suno_session_package() -> dict:
    return get_active_suno_session_packet()


def resolve_or_preexecute_active_suno_packet(bus: dict = None, target_duration_sec: float = 0.0) -> dict:
    if isinstance(bus, dict) and isinstance(bus.get('suno_music_studio'), dict) and bus['suno_music_studio'].get('active'):
        pkt = dict(bus['suno_music_studio'])
        if target_duration_sec > 0.0 and not bool(pkt.get('lock_video_duration')):
            pkt = reslice_suno_packet_to_duration(pkt, target_duration_sec)
        return pkt
    try:
        from server import PromptServer
        ps = getattr(PromptServer, 'instance', None)
        pq = getattr(ps, 'prompt_queue', None) if ps is not None else None
        running = getattr(pq, 'currently_running', None) if pq is not None else None
        if isinstance(running, dict) and len(running) > 0:
            active_item = next(iter(running.values()))
            prompt_graph = active_item[2] if isinstance(active_item, (list, tuple)) and len(active_item) > 2 and isinstance(active_item[2], dict) else None
            if isinstance(prompt_graph, dict):
                suno_node_inputs = None
                for node_def in prompt_graph.values():
                    if not isinstance(node_def, dict):
                        continue
                    ct = str(node_def.get('class_type', '') or '')
                    if 'SunoMusic' in ct or 'EZ_12' in ct or 'Suno_Music' in ct:
                        suno_node_inputs = node_def.get('inputs') if isinstance(node_def.get('inputs'), dict) else {}
                        break
                if suno_node_inputs is None:
                    _ACTIVE_SUNO_SESSION_CACHE['packet'] = None
                    if isinstance(bus, dict):
                        bus['suno_bypassed'] = True
                    return {}
                src_m = str(suno_node_inputs.get('source_mode', '') or '').strip()
                if src_m.lower().startswith('bypass'):
                    _ACTIVE_SUNO_SESSION_CACHE['packet'] = None
                    if isinstance(bus, dict):
                        bus['suno_bypassed'] = True
                    return {}
                eff_dur = float(target_duration_sec or (bus.get('duration_seconds', 0.0) if isinstance(bus, dict) else 0.0) or suno_node_inputs.get('custom_duration_sec', 20.0) or 20.0)
                cached_p = get_active_suno_session_packet()
                url_val = str(suno_node_inputs.get('suno_song_url_or_id', '') or '').strip()
                loc_val = str(suno_node_inputs.get('local_audio_file', '') or '').strip()
                cpath_val = str(suno_node_inputs.get('custom_audio_path', '') or '').strip()
                off_val = float(suno_node_inputs.get('start_offset_sec', 0.0) or 0.0)
                if cached_p.get('active') and abs(float(cached_p.get('start_offset_sec', 0.0)) - off_val) < 0.05:
                    if target_duration_sec > 0.0 and not bool(cached_p.get('lock_video_duration')):
                        return reslice_suno_packet_to_duration(cached_p, target_duration_sec)
                    return cached_p
                sim_bus = dict(bus) if isinstance(bus, dict) else {}
                if eff_dur > 0.0:
                    sim_bus['duration_seconds'] = eff_dur
                _, _, _, _, out_bus, _ = execute_suno_music_video_studio(
                    source_mode=src_m or SUNO_SOURCE_MODES[0],
                    performance_mode=str(suno_node_inputs.get('performance_mode', SUNO_PERFORMANCE_MODES[0]) or SUNO_PERFORMANCE_MODES[0]),
                    duration_sync_mode=str(suno_node_inputs.get('duration_sync_mode', SUNO_DURATION_SYNC_MODES[0]) or SUNO_DURATION_SYNC_MODES[0]),
                    local_audio_file=loc_val if not isinstance(suno_node_inputs.get('local_audio_file'), list) else '',
                    suno_song_url_or_id=url_val if not isinstance(suno_node_inputs.get('suno_song_url_or_id'), list) else '',
                    custom_audio_path=cpath_val if not isinstance(suno_node_inputs.get('custom_audio_path'), list) else '',
                    start_offset_sec=off_val if not isinstance(suno_node_inputs.get('start_offset_sec'), list) else 0.0,
                    custom_duration_sec=float(suno_node_inputs.get('custom_duration_sec', 20.0) or 20.0) if not isinstance(suno_node_inputs.get('custom_duration_sec'), list) else 20.0,
                    suno_model=str(suno_node_inputs.get('suno_model', SUNO_MODEL_PRESETS[0]) or SUNO_MODEL_PRESETS[0]),
                    song_style_tags=str(suno_node_inputs.get('song_style_tags', '') or '') if not isinstance(suno_node_inputs.get('song_style_tags'), list) else '',
                    lyrics_or_prompt=str(suno_node_inputs.get('lyrics_or_prompt', '') or '') if not isinstance(suno_node_inputs.get('lyrics_or_prompt'), list) else '',
                    instrumental_only=bool(suno_node_inputs.get('instrumental_only', False)) if not isinstance(suno_node_inputs.get('instrumental_only'), list) else False,
                    suno_api_endpoint=str(suno_node_inputs.get('suno_api_endpoint', 'https://api.sunoapi.org/api/v1/generate') or ''),
                    suno_api_key=str(suno_node_inputs.get('suno_api_key', '') or ''),
                    cinematrix_bus=sim_bus,
                )
                if isinstance(out_bus, dict) and isinstance(out_bus.get('suno_music_studio'), dict) and out_bus['suno_music_studio'].get('active'):
                    return dict(out_bus['suno_music_studio'])
    except Exception:
        pass
    if isinstance(bus, dict) and bool(bus.get('suno_bypassed', False)):
        return {}
    return get_active_suno_session_packet()


def execute_suno_music_video_studio(
    source_mode: str,
    performance_mode: str,
    duration_sync_mode: str,
    local_audio_file: str,
    suno_song_url_or_id: str = '',
    custom_audio_path: str = '',
    start_offset_sec: float = 0.0,
    custom_duration_sec: float = 20.0,
    suno_model: str = 'chirp-v4 (Suno v4 Studio)',
    song_style_tags: str = 'dark cyberpunk synthwave, powerful female vocals, heavy sub-bass, 124 bpm',
    lyrics_or_prompt: str = '',
    instrumental_only: bool = False,
    suno_api_endpoint: str = 'https://api.sunoapi.org/api/v1/generate',
    suno_api_key: str = '',
    cinematrix_bus: dict = None,
) -> tuple:
    bus = dict(cinematrix_bus) if isinstance(cinematrix_bus, dict) else {}
    has_suno_link = bool(str(suno_song_url_or_id or '').strip())
    loc_file_str = str(local_audio_file or '').strip()
    has_local_override = bool(
        str(custom_audio_path or '').strip()
        or (loc_file_str and not loc_file_str.startswith('None') and not loc_file_str.startswith('('))
    )
    eff_source_mode = str(source_mode or '').strip()
    timeline_aud_mode = str(bus.get('audio_soundtrack_mode', '') or '').strip().lower()
    if not timeline_aud_mode:
        try:
            import server
            p_srv = getattr(server, 'PromptServer', None)
            inst = getattr(p_srv, 'instance', None) if p_srv else None
            q_obj = getattr(inst, 'prompt_queue', None) if inst else None
            curr = getattr(q_obj, 'currently_running', None) if q_obj else None
            if isinstance(curr, dict):
                for _, item in curr.items():
                    prompt_graph = item[2] if isinstance(item, (list, tuple)) and len(item) > 2 else None
                    if isinstance(prompt_graph, dict):
                        for _, n_def in prompt_graph.items():
                            c_type = str(n_def.get('class_type', '')) if isinstance(n_def, dict) else ''
                            if c_type.startswith('EZCinematrixQwenVLTimelineCompiler'):
                                n_in = n_def.get('inputs', {}) if isinstance(n_def.get('inputs'), dict) else {}
                                cand_aud = str(n_in.get('audio_soundtrack_mode', '') or '').strip().lower()
                                if cand_aud:
                                    timeline_aud_mode = cand_aud
                                    break
                    if timeline_aud_mode:
                        break
        except Exception:
            pass
    if timeline_aud_mode.startswith(('sfx_only', 'sfx_and_speech')) or 'no_music' in timeline_aud_mode:
        eff_source_mode = 'Bypass / Off (Standard Video)'
    elif timeline_aud_mode.startswith(('instrumental_bgm', 'bgm_with_vocals', 'auto_from_prompt_or_suno')) and eff_source_mode.lower().startswith('bypass'):
        eff_source_mode = 'Suno Song URL or ID (Auto-Fetch Audio + Lyrics)'

    def _return_clean_bypass(status_msg: str):
        bus.pop('suno_music_studio', None)
        bus['suno_bypassed'] = True
        _ACTIVE_SUNO_SESSION_CACHE['packet'] = None
        empty_audio = {'waveform': torch.zeros((1, 2, 32000), dtype=torch.float32), 'sample_rate': 32000}
        ui_meta = {
            'active': False,
            'suno_bypassed': True,
            'status': status_msg,
            'bpm': 0.0,
            'beat_count': 0,
            'duration_sec': 0.0,
            'filename': '',
            'subfolder': '',
            'type': 'temp',
            'performance_mode': status_msg,
            'source_name': '',
            'lyrics': '',
            'tags': '',
        }
        return (empty_audio, '', '', 0.0, bus, ui_meta)

    if eff_source_mode.lower().startswith('bypass'):
        print('[EZ-SUNO-12] 🔇 Bypass / Off är valt — Suno [12] är helt urkopplad och standard H3-ljud används.')
        return _return_clean_bypass('BYPASSED // Standard Video Audio Mode')

    source_mode = eff_source_mode
    clean_ep, clean_key = _load_or_save_suno_credentials(suno_api_endpoint, suno_api_key)
    bus_dur = float(bus.get('duration_seconds', 0.0) or 0.0)
    sync_mode_str = str(duration_sync_mode or '')
    if sync_mode_str.startswith('Sync Audio Slice') or sync_mode_str.startswith('Sync to Timeline'):
        target_dur = bus_dur if bus_dur > 0.0 else max(5.0, float(custom_duration_sec or 20.0))
        lock_video_dur = False
    elif sync_mode_str.startswith('Match Full Audio') or sync_mode_str.startswith('Use Audio Track'):
        target_dur = 600.0
        lock_video_dur = True
    else:
        target_dur = max(5.0, float(custom_duration_sec or 20.0))
        lock_video_dur = True
    eff_lyrics = _clean_suno_lyrics_str(lyrics_or_prompt)
    eff_tags = _decode_unicode_escapes(song_style_tags)
    song_title = ''
    src_path = Path('')
    if str(source_mode or '').startswith('Suno Song URL') or (has_suno_link and not str(source_mode or '').startswith('Local Audio')):
        if not has_suno_link:
            if has_local_override:
                src_path = _resolve_local_audio_path(local_audio_file, custom_audio_path)
            else:
                print('[EZ-SUNO-12] ℹ️ Ingen Suno-länk angiven — auto-bypass aktiveras så att inbyggt H3-ljud bevaras.')
                return _return_clean_bypass('IDLE // Ingen Suno-länk (Inbyggt H3-ljud aktivt)')
        else:
            src_path, fetched_lyr, fetched_tags, song_title = _fetch_suno_song_by_url_or_id(
                suno_url_or_id=suno_song_url_or_id,
                api_endpoint=clean_ep,
                api_key=clean_key,
            )
            if fetched_lyr:
                eff_lyrics = _clean_suno_lyrics_str(fetched_lyr)
            if fetched_tags:
                eff_tags = _decode_unicode_escapes(fetched_tags)
    elif str(source_mode or '').startswith('Suno API') and not has_local_override:
        if not clean_key and not has_suno_link:
            print('[EZ-SUNO-12] ℹ️ Ingen Suno API-nyckel eller länk angiven — auto-bypass aktiveras så att inbyggt H3-ljud bevaras.')
            return _return_clean_bypass('IDLE // Ingen Suno API-nyckel (Inbyggt H3-ljud aktivt)')
        src_path, api_lyr, api_tags, song_title = _generate_or_fetch_suno_api_track(
            api_endpoint=clean_ep,
            api_key=clean_key,
            suno_model=suno_model,
            song_style_tags=eff_tags,
            lyrics_or_prompt=eff_lyrics,
            instrumental_only=instrumental_only,
            target_duration_sec=target_dur if target_dur <= 120.0 else float(custom_duration_sec or 20.0),
        )
        if api_lyr:
            eff_lyrics = api_lyr
        if api_tags:
            eff_tags = api_tags
    else:
        src_path = _resolve_local_audio_path(local_audio_file, custom_audio_path)
        emb_lyr, emb_tags, emb_title = _load_sidecar_or_embedded_lyrics(src_path)
        if emb_lyr and not eff_lyrics:
            eff_lyrics = emb_lyr
        if emb_tags and not eff_tags:
            eff_tags = emb_tags
        song_title = emb_title
    if not src_path or not str(src_path).strip() or not src_path.exists() or not src_path.is_file() or src_path.stat().st_size < 128:
        print('[EZ-SUNO-12] ⚠️ Ingen giltig ljudfil hittades för Suno [12] — auto-bypass aktiveras för att inte tysta H3-ljudet!')
        return _return_clean_bypass('IDLE // Ingen giltig ljudkälla (Inbyggt H3-ljud aktivt)')
    bus['suno_bypassed'] = False
    master_wav, waveform_32k, actual_dur, sr_32k = _decode_and_slice_audio_to_wav(
        source_path=src_path,
        start_offset_sec=start_offset_sec,
        target_duration_sec=target_dur,
    )
    has_vocal_title = 'vocal' in str(song_title or '').lower() and 'no vocal' not in str(song_title or '').lower()
    if has_vocal_title:
        eff_tags = re.sub(r'(?i),?\s*\bno\s+vocals?\b', '', eff_tags).strip(', ')
        if eff_lyrics.lower().startswith('[instrumental]'):
            eff_lyrics = ''
    if not eff_lyrics and not bool(instrumental_only):
        transcribed_txt = _transcribe_audio_speech_to_text(master_wav)
        if transcribed_txt:
            eff_lyrics = transcribed_txt
            print(f'[EZ-SUNO-12] 🎙️ ASR Taligenkänning extraherade text: {eff_lyrics[:120]}...')
    is_inst_track = (
        bool(instrumental_only)
        or (not has_vocal_title and (('[instrumental]' in eff_lyrics.lower()) or ('no vocals' in eff_tags.lower())))
    )
    eff_perf_mode = (
        'Rhythm_And_Dance (Beat-Driven Motion Only)'
        if (is_inst_track and str(performance_mode or '').startswith('Lead_Vocal_LipSync'))
        else performance_mode
    )
    analysis = _analyze_waveform_bpm_and_acts(
        waveform_32k=waveform_32k,
        duration_sec=actual_dur,
        lyrics_or_prompt=eff_lyrics,
        performance_mode=eff_perf_mode,
        song_style_tags=eff_tags,
        song_title=song_title,
    )
    viseme_env_4d = extract_4band_viseme_and_beat_envelope(waveform_32k, sr=int(sr_32k), fps=24.0)
    suno_packet = {
        'active': True,
        'source_mode': str(source_mode),
        'performance_mode': str(eff_perf_mode),
        'duration_sync_mode': sync_mode_str,
        'lock_video_duration': bool(lock_video_dur),
        'wants_lipsync': bool(analysis['wants_lipsync']) and not is_inst_track,
        'instrumental_only': bool(is_inst_track),
        'song_title': str(song_title or (src_path.stem if src_path and src_path.name else 'Suno_Track')),
        'song_style_tags': str(eff_tags),
        'lyrics_or_prompt': str(eff_lyrics),
        'bpm': float(analysis['bpm']),
        'beat_times': list(analysis['beat_times']),
        'acts': list(analysis['acts']),
        'shot_lyrics': list(analysis.get('shot_lyrics', [])),
        'shot_vocal_cues': list(analysis.get('shot_vocal_cues', [])),
        'prompt_injection': str(analysis['prompt_injection']),
        'auto_scene_prompt': str(analysis['auto_scene_prompt']),
        'audio_modality': str(analysis['audio_modality']),
        'voice_profile': str(analysis['voice_profile']),
        'master_wav_path': str(master_wav),
        'source_audio_path': str(src_path) if src_path else '',
        'waveform_32k': waveform_32k,
        'viseme_envelope_4d': viseme_env_4d,
        'sample_rate_32k': int(sr_32k),
        'duration_sec': round(float(actual_dur), 2),
        'start_offset_sec': float(start_offset_sec or 0.0),
    }
    _ACTIVE_SUNO_SESSION_CACHE['packet'] = dict(suno_packet)
    bus['suno_music_studio'] = suno_packet
    if lock_video_dur:
        bus['duration_seconds'] = round(float(actual_dur), 2)
        bus['master_duration'] = f'{int(round(actual_dur))}-second'
    comfy_audio = {'waveform': waveform_32k, 'sample_rate': int(sr_32k)}
    ui_meta = {
        'active': True,
        'filename': master_wav.name,
        'subfolder': '',
        'type': 'temp',
        'bpm': float(analysis['bpm']),
        'beat_count': int(analysis['beat_count']),
        'duration_sec': round(float(actual_dur), 2),
        'performance_mode': f"{analysis['audio_modality']} // {eff_perf_mode}",
        'source_name': str(song_title or (src_path.name if src_path and src_path.name else master_wav.name)),
        'lyrics': str(eff_lyrics or analysis['auto_scene_prompt']),
        'tags': str(eff_tags),
    }
    return (comfy_audio, str(analysis['prompt_injection']), str(eff_lyrics or analysis['auto_scene_prompt']), float(analysis['bpm']), bus, ui_meta)


def register_suno_promptserver_routes() -> None:
    try:
        import asyncio
        from aiohttp import web
        from server import PromptServer
        if getattr(PromptServer.instance, '_ez_suno_routes_bound', False):
            return
        PromptServer.instance._ez_suno_routes_bound = True

        @PromptServer.instance.routes.post('/ez_cinematrix/suno/fetch_meta')
        async def _ez_suno_fetch_meta(request):
            try:
                body = await request.json()
                url_or_id = str(body.get('suno_song_url_or_id') or '').strip()
                if not url_or_id:
                    return web.json_response({'status': 'empty', 'tags': '', 'lyrics': '', 'title': ''})
                src_p, lyr, tags, title = await asyncio.to_thread(_fetch_suno_song_by_url_or_id, url_or_id)
                return web.json_response({
                    'status': 'ok',
                    'title': str(title or ''),
                    'tags': str(tags or ''),
                    'lyrics': _clean_suno_lyrics_str(lyr),
                    'cached_file': str(src_p.name) if src_p and src_p.name else '',
                })
            except Exception as exc:
                return web.json_response({'status': 'error', 'message': str(exc)}, status=500)
    except Exception:
        pass


register_suno_promptserver_routes()

