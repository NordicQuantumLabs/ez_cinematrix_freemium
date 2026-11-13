# -*- coding: utf-8 -*-
import importlib
from pathlib import Path

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

for py_file in Path(__file__).parent.glob('*.py'):
    if py_file.name == '__init__.py':
        continue
    mod_name = f'.{py_file.stem}'
    try:
        mod = importlib.import_module(mod_name, package=__package__ or __name__)
        if hasattr(mod, 'NODE_CLASS_MAPPINGS'):
            NODE_CLASS_MAPPINGS.update(mod.NODE_CLASS_MAPPINGS)
        if hasattr(mod, 'NODE_DISPLAY_NAME_MAPPINGS'):
            NODE_DISPLAY_NAME_MAPPINGS.update(mod.NODE_DISPLAY_NAME_MAPPINGS)
    except Exception as mod_err:
        print(f'[-] Fel vid laddning av {mod_name}: {mod_err}')

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
