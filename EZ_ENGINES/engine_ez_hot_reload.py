# -*- coding: utf-8 -*-
import hashlib
import importlib
import inspect
import os
import sys
import shutil
from pathlib import Path
from typing import Optional

_EZ_MTIME_LEDGER = globals().get("_EZ_MTIME_LEDGER", {})
_EZ_TORCH_HUB_PATH = globals().get("_EZ_TORCH_HUB_PATH", None)


def unlock_and_bind_portable_torch_hub(suite_root: Path = None) -> str:
    global _EZ_TORCH_HUB_PATH
    if _EZ_TORCH_HUB_PATH and os.path.exists(_EZ_TORCH_HUB_PATH):
        return _EZ_TORCH_HUB_PATH
    exe_dir = Path(sys.executable).resolve().parent
    s_root = Path(suite_root).resolve() if suite_root else Path(__file__).resolve().parent.parent
    candidates = [exe_dir]
    for anc in list(s_root.parents)[:5]:
        for py_name in ("python_embeded", "python_embedded"):
            candidates.append(anc / py_name)
            candidates.append(anc / "ComfyUI_windows_portable" / py_name)
    portable_py = next((c for c in candidates if c.exists() and (c / "python.exe").exists()), exe_dir)
    torch_home = portable_py / ".cache" / "torch"
    hub_dir = torch_home / "hub"
    ckpt_dir = hub_dir / "checkpoints"
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    win_ckpt = Path.home() / ".cache" / "torch" / "hub" / "checkpoints"
    for folder in (ckpt_dir, win_ckpt):
        if folder.exists():
            for lock_f in list(folder.glob("*.lock")) + list(folder.glob("*.tmp")) + list(folder.glob("*.part")):
                try:
                    lock_f.unlink()
                except OSError:
                    pass
    if win_ckpt.exists() and win_ckpt.resolve() != ckpt_dir.resolve():
        for pth_f in win_ckpt.glob("*.pth"):
            dst_f = ckpt_dir / pth_f.name
            if not dst_f.exists() or dst_f.stat().st_size < pth_f.stat().st_size:
                try:
                    shutil.copy2(pth_f, dst_f)
                except OSError:
                    pass
    os.environ["TORCH_HOME"] = str(torch_home)
    try:
        import torch.hub
        torch.hub.set_dir(str(hub_dir))
    except Exception:
        pass
    _EZ_TORCH_HUB_PATH = str(hub_dir)
    return _EZ_TORCH_HUB_PATH


def _promote_nested_clean_dir_if_present(suite_root: Path) -> bool:
    clean_sub = suite_root / "CLEAN"
    if not clean_sub.exists() or not clean_sub.is_dir():
        return False
    if not (clean_sub / "EZ_ENGINES").exists() and not (clean_sub / "EZ_NODES").exists():
        return False
    promoted = False
    try:
        for item in list(clean_sub.iterdir()):
            if item.name == "__pycache__":
                continue
            dst = suite_root / item.name
            if item.is_dir():
                shutil.copytree(item, dst, dirs_exist_ok=True)
                promoted = True
            elif item.is_file():
                shutil.copy2(item, dst)
                promoted = True
        shutil.rmtree(clean_sub, ignore_errors=True)
    except Exception as prom_err:
        print(f"[EZ HotReload] Could not promote nested CLEAN folder: {prom_err}")
    return promoted


def _purge_suite_pycache(suite_root: Path) -> None:
    for pyc_dir in list(suite_root.rglob("__pycache__")):
        if "CLEAN" in pyc_dir.parts:
            continue
        shutil.rmtree(pyc_dir, ignore_errors=True)


def _scan_suite_py_mtimes(suite_root: Path) -> dict:
    _promote_nested_clean_dir_if_present(suite_root)
    mtimes = {}
    for sub in ("EZ_ENGINES", "EZ_ADAPTERS", "EZ_NODES"):
        sub_dir = suite_root / sub
        if not sub_dir.exists():
            continue
        for py_f in sorted(sub_dir.glob("*.py")):
            if py_f.name == "__init__.py":
                continue
            try:
                raw_bytes = py_f.read_bytes()
                sha_short = hashlib.sha256(raw_bytes).hexdigest()[:16]
                mtimes[f"{sub}/{py_f.name}"] = (sha_short, len(raw_bytes))
            except OSError:
                continue
    return mtimes


def compute_suite_mtime_digest(suite_root: Path, kwargs: dict = None) -> str:
    mtimes = _scan_suite_py_mtimes(suite_root)
    h = hashlib.sha256()
    for rel_k, sig in sorted(mtimes.items()):
        h.update(f"{rel_k}:{sig[0]}:{sig[1]};".encode("utf-8"))
    if isinstance(kwargs, dict):
        for k in sorted(kwargs.keys()):
            v = kwargs[k]
            if isinstance(v, (int, float, str, bool)) or v is None:
                h.update(f"|{k}={v!r}".encode("utf-8"))
    return h.hexdigest()[:24]


def hot_reload_modified_ez_modules(suite_root: Path, package_root: str, force: bool = False) -> bool:
    if not package_root:
        return False
    current = _scan_suite_py_mtimes(suite_root)
    changed_rel = [k for k, v in current.items() if _EZ_MTIME_LEDGER.get(k) != v]
    if not changed_rel and not force:
        return False
    was_bootstrapped = bool(_EZ_MTIME_LEDGER)
    _EZ_MTIME_LEDGER.update(current)
    if not was_bootstrapped and not force:
        return False
    _purge_suite_pycache(suite_root)
    importlib.invalidate_caches()
    reloaded_any = False
    suite_resolved = suite_root.resolve()
    for layer in ("EZ_ENGINES", "EZ_ADAPTERS", "EZ_NODES"):
        for rel_k in sorted(current.keys()):
            if not rel_k.startswith(f"{layer}/"):
                continue
            stem = Path(rel_k).stem
            if stem == "engine_ez_hot_reload":
                continue
            target_file = (suite_resolved / rel_k).resolve()
            candidates = []
            direct_mod = sys.modules.get(f"{package_root}.{layer}.{stem}")
            if direct_mod is not None:
                candidates.append(direct_mod)
            for m_obj in list(sys.modules.values()):
                if m_obj is None or m_obj in candidates:
                    continue
                m_file = getattr(m_obj, "__file__", None)
                if m_file:
                    try:
                        if Path(m_file).resolve() == target_file:
                            candidates.append(m_obj)
                    except OSError:
                        pass
            if candidates:
                for mod_obj in candidates:
                    try:
                        importlib.reload(mod_obj)
                        reloaded_any = True
                    except Exception as rel_err:
                        print(f"[EZ HotReload] Could not reload {getattr(mod_obj, '__name__', rel_k)}: {rel_err}")
    if reloaded_any:
        print(f"[EZ HotReload] Reloaded {len(changed_rel) or len(current)} module(s) from {suite_root.name} (purged __pycache__).")
    return reloaded_any


def _coerce_single_kwarg_value(val, spec_tuple):
    if not isinstance(spec_tuple, (tuple, list)) or len(spec_tuple) == 0:
        return val
    first = spec_tuple[0]
    opts = spec_tuple[1] if len(spec_tuple) > 1 and isinstance(spec_tuple[1], dict) else {}
    default_val = opts.get("default", None)
    if isinstance(first, (list, tuple)):
        if val not in first:
            if isinstance(val, str) and val.strip():
                v_low = val.strip().lower()
                pref_match = next((item for item in first if isinstance(item, str) and item.lower().startswith(v_low)), None)
                if pref_match is not None:
                    return pref_match
            if default_val in first:
                return default_val
            return first[0] if len(first) > 0 else val
        return val
    if first == "INT":
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            try:
                return int(float(str(val).strip()))
            except (ValueError, TypeError):
                return int(default_val) if default_val is not None else 0
        return int(val)
    if first == "FLOAT":
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            try:
                return float(str(val).strip())
            except (ValueError, TypeError):
                return float(default_val) if default_val is not None else 0.0
        return float(val)
    if first == "BOOLEAN":
        if not isinstance(val, bool):
            if isinstance(val, str):
                return val.strip().lower() in ("true", "1", "yes", "on")
            return bool(default_val) if default_val is not None else False
        return val
    if first == "STRING" and val is None:
        return str(default_val) if default_val is not None else ""
    return val


def sanitize_node_kwargs_against_schema(node_cls, kwargs: dict) -> dict:
    try:
        schema = node_cls.INPUT_TYPES()
    except Exception:
        return kwargs
    req = schema.get("required", {}) if isinstance(schema, dict) else {}
    opt = schema.get("optional", {}) if isinstance(schema, dict) else {}
    combined_spec = {}
    if isinstance(req, dict):
        combined_spec.update(req)
    if isinstance(opt, dict):
        combined_spec.update(opt)
    healed = dict(kwargs)
    for k, spec_t in combined_spec.items():
        if k in healed:
            healed[k] = _coerce_single_kwarg_value(healed[k], spec_t)
        elif isinstance(spec_t, (tuple, list)) and len(spec_t) > 1 and isinstance(spec_t[1], dict) and "default" in spec_t[1]:
            healed[k] = spec_t[1]["default"]
    return healed


_EZ_STARTUP_DIAG_EMITTED = False

_REQUIRED_RUNTIME_PACKAGES = (
    ("numpy", "numpy>=1.24.0"),
    ("PIL", "Pillow>=10.0.0"),
    ("safetensors", "safetensors>=0.4.2"),
    ("psutil", "psutil>=5.9.0"),
    ("cryptography", "cryptography>=41.0.0"),
    ("av", "av>=11.0.0"),
    ("imageio_ffmpeg", "imageio-ffmpeg>=0.4.9"),
    ("spandrel", "spandrel>=0.3.0"),
    ("transformers", "transformers>=4.44.0"),
    ("accelerate", "accelerate>=0.30.0"),
    ("huggingface_hub", "huggingface-hub>=0.23.0"),
    ("scipy", "scipy>=1.10.0"),
    ("faster_whisper", "faster-whisper>=1.0.0"),
)


def _auto_sync_comfy_environment(suite_root: Optional[Path] = None) -> None:
    if os.environ.get("EZ_SKIP_AUTO_INSTALL", "0") == "1":
        return
    import importlib.util
    missing = [spec for mod, spec in _REQUIRED_RUNTIME_PACKAGES if importlib.util.find_spec(mod) is None]
    if not missing:
        return
    root_dir = suite_root if isinstance(suite_root, Path) else Path(__file__).resolve().parent.parent
    is_premium_bundle = (root_dir / "allan_ballan_core.enc").is_file() or (root_dir / "signature.enc").is_file()
    if not is_premium_bundle:
        print(
            f"[EZ Cinematrix Community] Notice: {len(missing)} package(s) not detected ({', '.join(missing)}). "
            f"Install via ComfyUI-Manager or 'pip install -r requirements.txt'."
        )
        return
    import importlib
    import subprocess
    if importlib.util.find_spec("pip") is None:
        return
    print(f"[EZ Cinematrix Pro Auto-Env] Installing {len(missing)} missing package(s) into ComfyUI Python ({sys.executable})...")
    install_script = root_dir / "install.py"
    try:
        if install_script.is_file():
            subprocess.run([sys.executable, str(install_script)], check=False, timeout=300)
        else:
            subprocess.run([sys.executable, "-m", "pip", "install", *missing], check=False, timeout=300)
        importlib.invalidate_caches()
    except Exception as exc:
        print(f"[EZ Cinematrix Pro Auto-Env] Warning during environment auto-update: {exc}")


def emit_cinematrix_startup_diagnostics(node_count: int = 13, suite_root: Optional[Path] = None) -> None:
    global _EZ_STARTUP_DIAG_EMITTED
    if _EZ_STARTUP_DIAG_EMITTED:
        return
    _EZ_STARTUP_DIAG_EMITTED = True
    try:
        _auto_sync_comfy_environment(suite_root)
        import importlib.util
        import torch
        dev_str = "CPU"
        vram_str = "N/A"
        if torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            vram_gb = float(props.total_memory) / (1024.0 ** 3)
            arch_lbl = "ROCm" if getattr(torch.version, "hip", None) else f"SM_{props.major}{props.minor}"
            dev_str = f"{props.name} ({arch_lbl})"
            vram_str = f"{vram_gb:.1f} GB"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            dev_str = "Apple Silicon MPS"
        opt_mods = ("av", "spandrel", "faster_whisper", "transformers")
        ready_mods = [m for m in opt_mods if importlib.util.find_spec(m) is not None]
        print(
            f"[EZ Cinematrix Core v2.6] {node_count} Nodes Active | Device: {dev_str} | "
            f"VRAM: {vram_str} | Backends: {', '.join(ready_mods) or 'core'}"
        )
    except Exception:
        pass


def bind_hot_reload_and_schema_guard(node_mapping: dict, suite_root: Path, package_root: str) -> None:
    unlock_and_bind_portable_torch_hub(suite_root)
    emit_cinematrix_startup_diagnostics(len(node_mapping), suite_root=suite_root)
    _scan_init = _scan_suite_py_mtimes(suite_root)
    _EZ_MTIME_LEDGER.update(_scan_init)
    for class_key, node_cls in list(node_mapping.items()):
        if getattr(node_cls, "_EZ_HOT_RELOAD_BOUND", False):
            continue
        fn_name = getattr(node_cls, "FUNCTION", None)
        if not fn_name or not hasattr(node_cls, fn_name):
            continue
        mod_name = getattr(node_cls, "__module__", "")

        def _make_exec_wrapper(orig_fn_name, cls_name, origin_mod):
            def _wrapped_exec(self, *args, **kwargs):
                hot_reload_modified_ez_modules(suite_root, package_root)
                live_mod = sys.modules.get(origin_mod)
                live_cls = getattr(live_mod, cls_name, self.__class__)
                healed_kw = sanitize_node_kwargs_against_schema(live_cls, kwargs)
                raw_fn = getattr(live_cls, "_EZ_ORIG_FUNCTION_REF", None) or getattr(live_cls, orig_fn_name)
                sig = inspect.signature(raw_fn)
                accepts_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
                if not accepts_var_kw:
                    valid_keys = {p.name for p in sig.parameters.values() if p.name != "self"}
                    healed_kw = {k: v for k, v in healed_kw.items() if k in valid_keys}
                try:
                    return raw_fn(self, *args, **healed_kw)
                except TypeError as type_err:
                    if "unexpected keyword argument" in str(type_err):
                        hot_reload_modified_ez_modules(suite_root, package_root, force=True)
                        live_mod = sys.modules.get(origin_mod)
                        live_cls = getattr(live_mod, cls_name, self.__class__)
                        raw_fn = getattr(live_cls, "_EZ_ORIG_FUNCTION_REF", None) or getattr(live_cls, orig_fn_name)
                        return raw_fn(self, *args, **healed_kw)
                    raise
            return _wrapped_exec

        setattr(node_cls, "_EZ_ORIG_FUNCTION_REF", getattr(node_cls, fn_name))
        setattr(node_cls, fn_name, _make_exec_wrapper(fn_name, node_cls.__name__, mod_name))
        orig_in_fn = getattr(node_cls.__dict__.get("INPUT_TYPES"), "__func__", None)
        if orig_in_fn is not None:
            setattr(node_cls, "_EZ_ORIG_INPUT_TYPES_FN", orig_in_fn)

            def _make_input_types_wrapper(cls_name, origin_mod, fallback_fn):
                @classmethod
                def _wrapped_input_types(cls):
                    hot_reload_modified_ez_modules(suite_root, package_root)
                    live_mod = sys.modules.get(origin_mod)
                    live_cls = getattr(live_mod, cls_name, cls)
                    for attr_k in ("RETURN_TYPES", "RETURN_NAMES", "OUTPUT_NODE"):
                        if hasattr(live_cls, attr_k):
                            setattr(cls, attr_k, getattr(live_cls, attr_k))
                    edition_cat = getattr(cls, "EZ_EDITION_CATEGORY", None)
                    if edition_cat:
                        setattr(cls, "CATEGORY", edition_cat)
                    elif hasattr(live_cls, "CATEGORY"):
                        setattr(cls, "CATEGORY", getattr(live_cls, "CATEGORY"))
                    raw_in = getattr(live_cls, "_EZ_ORIG_INPUT_TYPES_FN", None)
                    if raw_in is not None:
                        return raw_in(live_cls)
                    live_desc = live_cls.__dict__.get("INPUT_TYPES")
                    if live_desc is not None and hasattr(live_desc, "__func__") and live_desc.__func__ is not _wrapped_input_types.__func__:
                        return live_desc.__func__(live_cls)
                    return fallback_fn(cls)
                return _wrapped_input_types

            setattr(node_cls, "INPUT_TYPES", _make_input_types_wrapper(node_cls.__name__, mod_name, orig_in_fn))

        @classmethod
        def _ez_validate_inputs(cls, **kwargs):
            return True

        @classmethod
        def _ez_is_changed(cls, **kwargs):
            hot_reload_modified_ez_modules(suite_root, package_root)
            return compute_suite_mtime_digest(suite_root, kwargs)

        setattr(node_cls, "VALIDATE_INPUTS", _ez_validate_inputs)
        setattr(node_cls, "IS_CHANGED", _ez_is_changed)
        setattr(node_cls, "_EZ_HOT_RELOAD_BOUND", True)
