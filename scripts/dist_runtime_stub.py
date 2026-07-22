"""
Fallback no-op DIST runtime.

Used when dist_runtime.py is intentionally absent (e.g. open-source/unlocked
builds). Exports the same helper names expected by main.py.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def _dist_default_metadata() -> Dict[str, object]:
    return {
        "version": 1,
        "sealed": False,
        "require_user_key": False,
        "distributor": "",
        "target_user_file": "",
        "allowed_public_keys": [],
        "users_removed": False,
    }


def _dist_normalize_metadata(value: object) -> Dict[str, object]:
    if isinstance(value, dict):
        out = dict(_dist_default_metadata())
        out.update(value)
        return out
    return _dist_default_metadata()


def _dist_load_effective_metadata(_exe_path: Path) -> Dict[str, object]:
    return _dist_default_metadata()


def _dist_seed_embedded_users_from_packaged(_exe_path: Path, metadata: Dict[str, object]) -> Dict[str, object]:
    return _dist_normalize_metadata(metadata)


def _dist_has_embedded_users(_exe_path: Path) -> bool:
    return False


def _dist_try_remove_users_folder() -> None:
    return None


def _dist_consume_restart_auth_bypass(_exe_path: Path) -> bool:
    return False


def _dist_authorize_launch(_metadata: Dict[str, object]) -> Tuple[bool, str, str]:
    return True, "DIST disabled", ""


def _dist_notify_auth_failure(_distributor: object, _reason: object) -> None:
    return None


def _dist_apply_restart_auth_bypass_env(base_env: Dict[str, str], _exe_path: Path) -> Dict[str, str]:
    return dict(base_env)


def _dist_normalize_user_filename(value: object) -> str:
    raw = str(value or "").strip()
    if raw == "":
        return ""
    return Path(raw).name


def _dist_normalize_public_key(value: object) -> str:
    text = str(value or "").strip().lower()
    if len(text) == 64 and all(ch in "0123456789abcdef" for ch in text):
        return text
    return ""


def _dist_sanitize_distributor(value: object, max_len: int = 40) -> str:
    raw = str(value or "")
    filtered = "".join(ch for ch in raw if 32 <= ord(ch) <= 126)
    return filtered.strip()[: max(1, int(max_len))]


def _dist_collect_user_files() -> Dict[str, Path]:
    return {}


def _dist_collect_user_public_keys(_metadata: Optional[Dict[str, object]] = None) -> Dict[str, str]:
    return {}


def _dist_write_embedded_metadata(_exe_path: Path, _metadata: Dict[str, object]) -> bool:
    return False


def _dist_sidecar_path(exe_path: Path) -> Path:
    return exe_path.with_suffix(exe_path.suffix + ".distmeta.json")


def _3dworld_worker_mode_from_argv(_argv: Optional[List[str]] = None) -> Optional[int]:
    args = list(sys.argv[1:] if _argv is None else _argv)
    if "--3dworld-worker" not in args:
        return None
    session_id = ""
    role = "tflir"
    i = 0
    while i < len(args):
        tok = str(args[i]).strip().lower()
        if tok == "--session" and i + 1 < len(args):
            session_id = str(args[i + 1]).strip()
            i += 2
            continue
        if tok == "--role" and i + 1 < len(args):
            role = str(args[i + 1]).strip().lower() or "tflir"
            i += 2
            continue
        i += 1
    try:
        mod = importlib.import_module("3DWorld")
    except Exception as exc:
        try:
            print(f"[3DWORLD][WORKER_DISPATCH] import failed: {exc}")
        except Exception:
            pass
        return 1
    try:
        base_cache = Path(getattr(mod, "_BASE_CACHE_DIR"))
    except Exception:
        base_cache = Path(__file__).resolve().parent.parent / "CACHE" / "3dworld"
    try:
        if role == "das":
            mod._WORKER_PID_PATH = base_cache / "worker_das_pid.txt"
            mod._WORKER_LOG_PATH = base_cache / "worker_das.log"
        else:
            mod._WORKER_PID_PATH = base_cache / "worker_pid.txt"
            mod._WORKER_LOG_PATH = base_cache / "worker.log"
    except Exception:
        pass
    if session_id != "":
        try:
            session_cache = base_cache / str(session_id)
            mod._SESSION_ID = session_id
            mod._CACHE_DIR = session_cache
            mod._POSE_PATH = session_cache / "pose.json"
            mod._FRAME_PATH = session_cache / "tflir_frame.png"
            mod._META_PATH = session_cache / "frame_meta.json"
            mod._DAS_FRAME_PATH = session_cache / "das_frame.png"
            mod._DAS_META_PATH = session_cache / "das_frame_meta.json"
        except Exception:
            pass
    try:
        return int(mod._run_worker())
    except Exception as exc:
        try:
            print(f"[3DWORLD][WORKER_DISPATCH] run failed: {exc}")
        except Exception:
            pass
        return 1


def _firewall_helper_mode_from_argv(_argv: Optional[List[str]] = None) -> Optional[int]:
    return None


def _firewall_helper_apply_rules(_exe_path: str, _relay_ip: str, _relay_port: int) -> Tuple[bool, str]:
    return False, "DIST runtime disabled"


def _dist_collect_machine_identity() -> Dict[str, str]:
    return {}


def _dist_generate_machine_keys() -> Dict[str, str]:
    return {}


def _dist_send_unauthorized_webhook(_distributor: object, _reason: object) -> bool:
    return False


def _dist_read_user_public_key(_path: Path) -> str:
    return ""


def _dist_candidate_users_dirs(_include_legacy_paths: bool = False) -> List[Path]:
    return []


def _dist_collect_packaged_user_public_keys() -> Dict[str, str]:
    return {}


def _dist_allowed_public_keys_from_users(
    _user_keys: Dict[str, str],
    _metadata: Optional[Dict[str, object]] = None,
) -> List[str]:
    return []


__all__ = [name for name in globals().keys() if not name.startswith("__")]
