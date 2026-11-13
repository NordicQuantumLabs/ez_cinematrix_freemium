# -*- coding: utf-8 -*-
# 👑 EMPIRE CONSOLE - AST VERIFIED CLEAN VAULT INITIALIZER
import re as _ez_re
import sys as _ez_sys
from pathlib import Path as _EzPath

NODE_SUITE_VERSION = 'v1.0 Freemium'
NODE_SUITE_TIER = 'FREEMIUM'

from .EZ_NODES.ez_master_ez_01_cinematrix_canvas_ingest import NODE_CLASS_MAPPINGS as mappings_ez_01_cinematrix_canvas_ingest
try:
    from .EZ_NODES.ez_master_ez_01_cinematrix_canvas_ingest import NODE_DISPLAY_NAME_MAPPINGS as display_ez_01_cinematrix_canvas_ingest
except ImportError:
    display_ez_01_cinematrix_canvas_ingest = {}
from .EZ_NODES.ez_master_ez_02_cinematrix_qwenvl_timeline import NODE_CLASS_MAPPINGS as mappings_ez_02_cinematrix_qwenvl_timeline
try:
    from .EZ_NODES.ez_master_ez_02_cinematrix_qwenvl_timeline import NODE_DISPLAY_NAME_MAPPINGS as display_ez_02_cinematrix_qwenvl_timeline
except ImportError:
    display_ez_02_cinematrix_qwenvl_timeline = {}
from .EZ_NODES.ez_master_ez_03_cinematrix_image_lora_splitter import NODE_CLASS_MAPPINGS as mappings_ez_03_cinematrix_image_lora_splitter
try:
    from .EZ_NODES.ez_master_ez_03_cinematrix_image_lora_splitter import NODE_DISPLAY_NAME_MAPPINGS as display_ez_03_cinematrix_image_lora_splitter
except ImportError:
    display_ez_03_cinematrix_image_lora_splitter = {}
from .EZ_NODES.ez_master_ez_04_cinematrix_krea2_sampler import NODE_CLASS_MAPPINGS as mappings_ez_04_cinematrix_krea2_sampler
try:
    from .EZ_NODES.ez_master_ez_04_cinematrix_krea2_sampler import NODE_DISPLAY_NAME_MAPPINGS as display_ez_04_cinematrix_krea2_sampler
except ImportError:
    display_ez_04_cinematrix_krea2_sampler = {}
from .EZ_NODES.ez_master_ez_05_cinematrix_video_lora_stack import NODE_CLASS_MAPPINGS as mappings_ez_05_cinematrix_video_lora_stack
try:
    from .EZ_NODES.ez_master_ez_05_cinematrix_video_lora_stack import NODE_DISPLAY_NAME_MAPPINGS as display_ez_05_cinematrix_video_lora_stack
except ImportError:
    display_ez_05_cinematrix_video_lora_stack = {}
from .EZ_NODES.ez_master_ez_06_cinematrix_video_director import NODE_CLASS_MAPPINGS as mappings_ez_06_cinematrix_video_director
try:
    from .EZ_NODES.ez_master_ez_06_cinematrix_video_director import NODE_DISPLAY_NAME_MAPPINGS as display_ez_06_cinematrix_video_director
except ImportError:
    display_ez_06_cinematrix_video_director = {}
from .EZ_NODES.ez_master_ez_07_cinematrix_joint_av_sampler import NODE_CLASS_MAPPINGS as mappings_ez_07_cinematrix_joint_av_sampler
try:
    from .EZ_NODES.ez_master_ez_07_cinematrix_joint_av_sampler import NODE_DISPLAY_NAME_MAPPINGS as display_ez_07_cinematrix_joint_av_sampler
except ImportError:
    display_ez_07_cinematrix_joint_av_sampler = {}
from .EZ_NODES.ez_master_ez_08_cinematrix_cinema_vault import NODE_CLASS_MAPPINGS as mappings_ez_08_cinematrix_cinema_vault
try:
    from .EZ_NODES.ez_master_ez_08_cinematrix_cinema_vault import NODE_DISPLAY_NAME_MAPPINGS as display_ez_08_cinematrix_cinema_vault
except ImportError:
    display_ez_08_cinematrix_cinema_vault = {}
from .EZ_NODES.ez_master_ez_09_cinematrix_anatomy_dock import NODE_CLASS_MAPPINGS as mappings_ez_09_cinematrix_anatomy_dock
try:
    from .EZ_NODES.ez_master_ez_09_cinematrix_anatomy_dock import NODE_DISPLAY_NAME_MAPPINGS as display_ez_09_cinematrix_anatomy_dock
except ImportError:
    display_ez_09_cinematrix_anatomy_dock = {}
from .EZ_NODES.ez_master_ez_10_cinematrix_civitai_controller import NODE_CLASS_MAPPINGS as mappings_ez_10_cinematrix_civitai_controller
try:
    from .EZ_NODES.ez_master_ez_10_cinematrix_civitai_controller import NODE_DISPLAY_NAME_MAPPINGS as display_ez_10_cinematrix_civitai_controller
except ImportError:
    display_ez_10_cinematrix_civitai_controller = {}
from .EZ_NODES.ez_master_ez_11_cinematrix_studio_note import NODE_CLASS_MAPPINGS as mappings_ez_11_cinematrix_studio_note
try:
    from .EZ_NODES.ez_master_ez_11_cinematrix_studio_note import NODE_DISPLAY_NAME_MAPPINGS as display_ez_11_cinematrix_studio_note
except ImportError:
    display_ez_11_cinematrix_studio_note = {}
from .EZ_NODES.ez_master_ez_12_cinematrix_suno_music_studio import NODE_CLASS_MAPPINGS as mappings_ez_12_cinematrix_suno_music_studio
try:
    from .EZ_NODES.ez_master_ez_12_cinematrix_suno_music_studio import NODE_DISPLAY_NAME_MAPPINGS as display_ez_12_cinematrix_suno_music_studio
except ImportError:
    display_ez_12_cinematrix_suno_music_studio = {}
from .EZ_NODES.ez_master_ez_13_cinematrix_omni_reference_loader import NODE_CLASS_MAPPINGS as mappings_ez_13_cinematrix_omni_reference_loader
try:
    from .EZ_NODES.ez_master_ez_13_cinematrix_omni_reference_loader import NODE_DISPLAY_NAME_MAPPINGS as display_ez_13_cinematrix_omni_reference_loader
except ImportError:
    display_ez_13_cinematrix_omni_reference_loader = {}
from .EZ_NODES.ez_master_ez_14_cinematrix_pipeline_switchboard import NODE_CLASS_MAPPINGS as mappings_ez_14_cinematrix_pipeline_switchboard
try:
    from .EZ_NODES.ez_master_ez_14_cinematrix_pipeline_switchboard import NODE_DISPLAY_NAME_MAPPINGS as display_ez_14_cinematrix_pipeline_switchboard
except ImportError:
    display_ez_14_cinematrix_pipeline_switchboard = {}

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

NODE_CLASS_MAPPINGS.update(mappings_ez_01_cinematrix_canvas_ingest)
for k in mappings_ez_01_cinematrix_canvas_ingest.keys(): NODE_DISPLAY_NAME_MAPPINGS[k] = str(display_ez_01_cinematrix_canvas_ingest.get(k, k))
NODE_CLASS_MAPPINGS.update(mappings_ez_02_cinematrix_qwenvl_timeline)
for k in mappings_ez_02_cinematrix_qwenvl_timeline.keys(): NODE_DISPLAY_NAME_MAPPINGS[k] = str(display_ez_02_cinematrix_qwenvl_timeline.get(k, k))
NODE_CLASS_MAPPINGS.update(mappings_ez_03_cinematrix_image_lora_splitter)
for k in mappings_ez_03_cinematrix_image_lora_splitter.keys(): NODE_DISPLAY_NAME_MAPPINGS[k] = str(display_ez_03_cinematrix_image_lora_splitter.get(k, k))
NODE_CLASS_MAPPINGS.update(mappings_ez_04_cinematrix_krea2_sampler)
for k in mappings_ez_04_cinematrix_krea2_sampler.keys(): NODE_DISPLAY_NAME_MAPPINGS[k] = str(display_ez_04_cinematrix_krea2_sampler.get(k, k))
NODE_CLASS_MAPPINGS.update(mappings_ez_05_cinematrix_video_lora_stack)
for k in mappings_ez_05_cinematrix_video_lora_stack.keys(): NODE_DISPLAY_NAME_MAPPINGS[k] = str(display_ez_05_cinematrix_video_lora_stack.get(k, k))
NODE_CLASS_MAPPINGS.update(mappings_ez_06_cinematrix_video_director)
for k in mappings_ez_06_cinematrix_video_director.keys(): NODE_DISPLAY_NAME_MAPPINGS[k] = str(display_ez_06_cinematrix_video_director.get(k, k))
NODE_CLASS_MAPPINGS.update(mappings_ez_07_cinematrix_joint_av_sampler)
for k in mappings_ez_07_cinematrix_joint_av_sampler.keys(): NODE_DISPLAY_NAME_MAPPINGS[k] = str(display_ez_07_cinematrix_joint_av_sampler.get(k, k))
NODE_CLASS_MAPPINGS.update(mappings_ez_08_cinematrix_cinema_vault)
for k in mappings_ez_08_cinematrix_cinema_vault.keys(): NODE_DISPLAY_NAME_MAPPINGS[k] = str(display_ez_08_cinematrix_cinema_vault.get(k, k))
NODE_CLASS_MAPPINGS.update(mappings_ez_09_cinematrix_anatomy_dock)
for k in mappings_ez_09_cinematrix_anatomy_dock.keys(): NODE_DISPLAY_NAME_MAPPINGS[k] = str(display_ez_09_cinematrix_anatomy_dock.get(k, k))
NODE_CLASS_MAPPINGS.update(mappings_ez_10_cinematrix_civitai_controller)
for k in mappings_ez_10_cinematrix_civitai_controller.keys(): NODE_DISPLAY_NAME_MAPPINGS[k] = str(display_ez_10_cinematrix_civitai_controller.get(k, k))
NODE_CLASS_MAPPINGS.update(mappings_ez_11_cinematrix_studio_note)
for k in mappings_ez_11_cinematrix_studio_note.keys(): NODE_DISPLAY_NAME_MAPPINGS[k] = str(display_ez_11_cinematrix_studio_note.get(k, k))
NODE_CLASS_MAPPINGS.update(mappings_ez_12_cinematrix_suno_music_studio)
for k in mappings_ez_12_cinematrix_suno_music_studio.keys(): NODE_DISPLAY_NAME_MAPPINGS[k] = str(display_ez_12_cinematrix_suno_music_studio.get(k, k))
NODE_CLASS_MAPPINGS.update(mappings_ez_13_cinematrix_omni_reference_loader)
for k in mappings_ez_13_cinematrix_omni_reference_loader.keys(): NODE_DISPLAY_NAME_MAPPINGS[k] = str(display_ez_13_cinematrix_omni_reference_loader.get(k, k))
NODE_CLASS_MAPPINGS.update(mappings_ez_14_cinematrix_pipeline_switchboard)
for k in mappings_ez_14_cinematrix_pipeline_switchboard.keys(): NODE_DISPLAY_NAME_MAPPINGS[k] = str(display_ez_14_cinematrix_pipeline_switchboard.get(k, k))

_LOADED_TIERS = getattr(_ez_sys, '_EZ_CINEMATRIX_LOADED_TIERS', set())
setattr(_ez_sys, '_EZ_CINEMATRIX_LOADED_TIERS', _LOADED_TIERS)
_SUITE_DIR_KEY = str(_EzPath(__file__).resolve().parent).lower()
_TIER_OWNER_MAP = getattr(_ez_sys, '_EZ_CINEMATRIX_TIER_OWNERS', {})
setattr(_ez_sys, '_EZ_CINEMATRIX_TIER_OWNERS', _TIER_OWNER_MAP)
if 'FREEMIUM' in _LOADED_TIERS and _TIER_OWNER_MAP.get('FREEMIUM') != _SUITE_DIR_KEY:
    NODE_CLASS_MAPPINGS.clear()
    NODE_DISPLAY_NAME_MAPPINGS.clear()
else:
    _LOADED_TIERS.add('FREEMIUM')
    _TIER_OWNER_MAP['FREEMIUM'] = _SUITE_DIR_KEY
    for _base_k, _base_cls in list(NODE_CLASS_MAPPINGS.items()):
        _clean_k = _ez_re.sub(r'_(?:PRO|Freemium)$', '', str(_base_k))
        _raw_d = _ez_re.sub(r'\s*\(v\d+\.\d+\)\s*$', '', str(NODE_DISPLAY_NAME_MAPPINGS.get(_base_k, _clean_k))).strip()
        _raw_d = _ez_re.sub(r'\s*—\s*(?:PRO|Freemium)\s+v\d+\.\d+\s*$', '', _raw_d).strip()
        _free_d = f'{_raw_d} — Freemium v1.0'
        _orig_cat = str(getattr(_base_cls, 'CATEGORY', 'EZ_Cinematrix'))
        _sub_cat = _orig_cat.split('/', 1)[1] if '/' in _orig_cat else _orig_cat
        _free_cat = f'EZ_Cinematrix_Freemium_v1.0/{_sub_cat}'
        _free_cls = type(f'{_base_cls.__name__}_Freemium', (_base_cls,), {'__module__': _base_cls.__module__, '_EZ_BASE_CLS_NAME': _base_cls.__name__, 'CATEGORY': _free_cat, 'EZ_EDITION_CATEGORY': _free_cat, 'EZ_SUITE_TIER': 'FREEMIUM', 'EZ_SUITE_VERSION': 'v1.0 Freemium'})
        NODE_CLASS_MAPPINGS.pop(_base_k, None)
        NODE_DISPLAY_NAME_MAPPINGS.pop(_base_k, None)
        NODE_CLASS_MAPPINGS[f'{_clean_k}_Freemium'] = _free_cls
        NODE_DISPLAY_NAME_MAPPINGS[f'{_clean_k}_Freemium'] = _free_d

try:
    from .EZ_ENGINES.engine_ez_hot_reload import bind_hot_reload_and_schema_guard as _bind_ez_hot_reload
    if NODE_CLASS_MAPPINGS:
        _bind_ez_hot_reload(NODE_CLASS_MAPPINGS, _EzPath(__file__).resolve().parent, __package__ or __name__)
except Exception:
    pass

WEB_DIRECTORY = './web/js'
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'NODE_SUITE_VERSION', 'NODE_SUITE_TIER', 'WEB_DIRECTORY']
