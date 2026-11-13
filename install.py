# -*- coding: utf-8 -*-
import importlib.util
import platform
import subprocess
import sys
from pathlib import Path

REQUIRED_PACKAGES = (
    ("numpy", "numpy>=1.24.0"),
    ("scipy", "scipy>=1.11.0"),
    ("PIL", "Pillow>=10.0.0"),
    ("safetensors", "safetensors>=0.4.2"),
    ("psutil", "psutil>=5.9.0"),
    ("cryptography", "cryptography>=41.0.0"),
    ("av", "av>=11.0.0"),
    ("imageio_ffmpeg", "imageio-ffmpeg>=0.4.9"),
    ("spandrel", "spandrel>=0.3.0"),
    ("transformers", "transformers>=4.44.0"),
    ("accelerate", "accelerate>=0.30.0"),
)

OPTIONAL_PACKAGES = (
    ("faster_whisper", "faster-whisper>=1.0.0"),
)


def _is_module_installed(mod_name: str) -> bool:
    try:
        return importlib.util.find_spec(mod_name) is not None
    except Exception:
        return False


def _pip_install_single(pkg_spec: str, optional: bool = False) -> bool:
    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--quiet",
        "--disable-pip-version-check",
        "--no-warn-script-location",
        pkg_spec,
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=300, check=False)
        if res.returncode == 0:
            print(f"[EZ Cinematrix Installer] + Installed {pkg_spec}")
            return True
        level = "OPTIONAL NOTICE" if optional else "WARNING"
        err_tail = (res.stderr or res.stdout or "").strip().splitlines()[-1:]
        print(f"[EZ Cinematrix Installer] [{level}] Could not install {pkg_spec}: {err_tail}")
        return False
    except Exception as exc:
        print(f"[EZ Cinematrix Installer] Notice while installing {pkg_spec}: {exc}")
        return False


def run_cross_platform_install() -> int:
    os_name = platform.system()
    arch = platform.machine()
    print(f"[EZ Cinematrix Installer] Checking environment on {os_name} ({arch}) via {sys.executable}...")
    if not _is_module_installed("torch"):
        print("[EZ Cinematrix Installer] WARNING: PyTorch is not detected in this Python environment. Install CUDA/ROCm/MPS PyTorch first.")
    missing_req = [spec for (mod, spec) in REQUIRED_PACKAGES if not _is_module_installed(mod)]
    missing_opt = [spec for (mod, spec) in OPTIONAL_PACKAGES if not _is_module_installed(mod)]
    if not missing_req and not missing_opt:
        print("[EZ Cinematrix Installer] All required & optional dependencies are already satisfied.")
        return 0
    for spec in missing_req:
        _pip_install_single(spec, optional=False)
    for spec in missing_opt:
        _pip_install_single(spec, optional=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cross_platform_install())
