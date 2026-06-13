import os
import shutil
import sys
from pathlib import Path
from typing import Iterable, List

_APP_BASE_DIR_CACHE: Path | None = None
_BUNDLE_BASE_DIR_CACHE: Path | None = None
_WRITABLE_BASE_DIR_CACHE: Path | None = None


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_base_dir() -> Path:
    global _APP_BASE_DIR_CACHE
    if _APP_BASE_DIR_CACHE is not None:
        return _APP_BASE_DIR_CACHE
    if is_frozen():
        _APP_BASE_DIR_CACHE = Path(sys.executable).resolve().parent
        return _APP_BASE_DIR_CACHE
    module_dir = Path(__file__).resolve().parent
    if module_dir.name.lower() == "scripts":
        _APP_BASE_DIR_CACHE = module_dir.parent
    else:
        _APP_BASE_DIR_CACHE = module_dir
    return _APP_BASE_DIR_CACHE


def bundle_base_dir() -> Path:
    global _BUNDLE_BASE_DIR_CACHE
    if _BUNDLE_BASE_DIR_CACHE is not None:
        return _BUNDLE_BASE_DIR_CACHE
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        _BUNDLE_BASE_DIR_CACHE = Path(meipass)
    else:
        _BUNDLE_BASE_DIR_CACHE = app_base_dir()
    return _BUNDLE_BASE_DIR_CACHE


def _app_data_root() -> Path:
    """
    Cross-platform writable root for runtime data when running packaged binaries.
    """
    app_name = "F35-PCD"
    if os.name == "nt":
        local = str(os.environ.get("LOCALAPPDATA", "")).strip()
        if local != "":
            return Path(local) / app_name
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / app_name
    xdg_data = str(os.environ.get("XDG_DATA_HOME", "")).strip()
    if xdg_data != "":
        return Path(xdg_data) / app_name
    return Path.home() / ".local" / "share" / app_name


def writable_base_dir() -> Path:
    """
    Base path for runtime-writable files.
    - Development (not frozen): project/app directory (current behavior).
    - Frozen binaries: user data directory (Linux/macOS/Windows friendly).
    """
    global _WRITABLE_BASE_DIR_CACHE
    if _WRITABLE_BASE_DIR_CACHE is not None:
        return _WRITABLE_BASE_DIR_CACHE
    if not is_frozen():
        _WRITABLE_BASE_DIR_CACHE = app_base_dir()
    else:
        _WRITABLE_BASE_DIR_CACHE = _app_data_root()
    return _WRITABLE_BASE_DIR_CACHE


def resource_path(*parts: str) -> Path:
    rel = Path(*parts)
    app_candidate = app_base_dir() / rel
    if app_candidate.exists():
        return app_candidate
    bundle_candidate = bundle_base_dir() / rel
    if bundle_candidate.exists():
        return bundle_candidate
    return app_candidate


def writable_path(*parts: str) -> Path:
    return writable_base_dir() / Path(*parts)


def migrate_legacy_writable_entries(entries: Iterable[str]) -> List[str]:
    """
    For frozen builds, copy old writable data that previously lived beside the EXE
    into the new user-writable base directory.
    Returns a list of relative entry names that were migrated.
    """
    migrated: List[str] = []
    if not is_frozen():
        return migrated
    src_root = app_base_dir()
    dst_root = writable_base_dir()
    try:
        if src_root.resolve() == dst_root.resolve():
            return migrated
    except Exception:
        pass
    for entry in entries:
        name = str(entry or "").strip().replace("\\", "/")
        if name == "":
            continue
        src = src_root / Path(name)
        dst = dst_root / Path(name)
        try:
            if (not src.exists()) or dst.exists():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
            migrated.append(name)
        except Exception:
            continue
    return migrated


def resolve_runtime_path(path_text: str) -> Path:
    p = Path(path_text)
    if p.is_absolute():
        return p
    cwd_candidate = Path.cwd() / p
    if cwd_candidate.exists():
        return cwd_candidate
    app_candidate = app_base_dir() / p
    if app_candidate.exists():
        return app_candidate
    bundle_candidate = bundle_base_dir() / p
    if bundle_candidate.exists():
        return bundle_candidate
    return app_candidate

