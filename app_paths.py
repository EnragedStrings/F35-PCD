import os
import shutil
import sys
from pathlib import Path
from typing import Iterable, List


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_base_dir() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def bundle_base_dir() -> Path:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return app_base_dir()


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
    if not is_frozen():
        return app_base_dir()
    return _app_data_root()


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
