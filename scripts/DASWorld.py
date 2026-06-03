from __future__ import annotations

import importlib
import importlib.machinery
import importlib.util
import os
import time
from pathlib import Path
from typing import Dict, Optional


_ROOT = Path(__file__).resolve().parent
_APP_ROOT = _ROOT.parent if _ROOT.name.lower() == "scripts" else _ROOT
_SRC_PATH = _ROOT / "3DWorld.py"
_BACKING = None


def _load_3dworld_module():
    if _SRC_PATH.exists():
        spec = importlib.util.spec_from_file_location("_f35_dasworld_backing", str(_SRC_PATH))
        if spec is None or spec.loader is None:
            msg = "Unable to load 3DWorld backing module for DASWorld"
            try:
                print(f"[DASWORLD] {msg}")
            except Exception:
                pass
            raise RuntimeError(msg)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    # PyInstaller onefile builds usually bundle imported modules into the PYZ
    # archive instead of extracting a loose 3DWorld.py beside DASWorld.py.
    # Fall back to the bundled module so compiled DAS can still run.
    bundled_spec = importlib.util.find_spec("3DWorld")
    bundled_loader = getattr(bundled_spec, "loader", None)
    get_code = getattr(bundled_loader, "get_code", None)
    if callable(get_code):
        code = get_code("3DWorld")
        if code is not None:
            mod = importlib.util.module_from_spec(
                importlib.machinery.ModuleSpec("_f35_dasworld_backing", bundled_loader)
            )
            mod.__dict__["__file__"] = str(_SRC_PATH)
            mod.__dict__["__package__"] = ""
            exec(code, mod.__dict__)
            return mod

    # Last-resort fallback. This may share module globals with TFLIR, but it is
    # still better than failing to render DAS in unusual packager layouts.
    return importlib.import_module("3DWorld")


def _load_backing():
    global _BACKING
    if _BACKING is not None:
        return _BACKING
    try:
        mod = _load_3dworld_module()
    except Exception as exc:
        try:
            print(f"[DASWORLD] backing exec failed: {exc}")
        except Exception:
            pass
        raise
    try:
        base_cache = Path(getattr(mod, "_BASE_CACHE_DIR"))
    except Exception:
        base_cache = _APP_ROOT / "CACHE" / "3dworld"
    sid = f"das_{os.getpid()}_{int(time.time() * 1000)}"
    try:
        mod._SESSION_ID = sid
        mod._CACHE_DIR = base_cache / sid
        mod._POSE_PATH = mod._CACHE_DIR / "pose.json"
        mod._FRAME_PATH = mod._CACHE_DIR / "tflir_frame.png"
        mod._META_PATH = mod._CACHE_DIR / "frame_meta.json"
        mod._DAS_FRAME_PATH = mod._CACHE_DIR / "das_frame.png"
        mod._DAS_META_PATH = mod._CACHE_DIR / "das_frame_meta.json"
        # Keep DAS worker lifecycle isolated from TFLIR worker lifecycle.
        mod._WORKER_PID_PATH = base_cache / "worker_das_pid.txt"
        mod._WORKER_LOG_PATH = base_cache / "worker_das.log"
    except Exception:
        pass
    _BACKING = mod
    return _BACKING


def update_pose(
    lat: float,
    lon: float,
    altitude_ft: float,
    heading_deg: float,
    quat_wxyz: Optional[Dict[str, float]] = None,
    pitch_deg: float = 0.0,
    roll_deg: float = 0.0,
    look_az_deg: float = 90.0,
    look_el_deg: float = 0.0,
    zoom_fov_deg: float = 45.0,
    cam_rel_forward_m: float = 0.0,
    cam_rel_right_m: float = 0.0,
    cam_rel_up_m: float = 0.0,
    cam_default_forward_m: float = 0.0,
    cam_default_right_m: float = 2.79,
    cam_default_up_m: float = -0.59,
    cam_default_cube_size_m: float = 1.0,
    cam_cube_forward_m: float = 0.0,
    cam_cube_right_m: float = 2.79,
    cam_cube_up_m: float = -0.59,
    look_slew_active: bool = False,
    das_camera_key: str = "DAS-BA",
    das_zoom_ratio: float = 2.9,
    das_fov_v_deg: float = 29.0,
    das_fov_h_deg: float = 29.0,
    das_cam_forward_m: float = 0.0,
    das_cam_right_m: float = 0.0,
    das_cam_up_m: float = 0.0,
    das_yaw_deg: float = 0.0,
    das_pitch_deg: float = 0.0,
    hold_point_enabled: bool = True,
    whot: bool = True,
    level_roll_to_horizon: bool = False,
) -> bool:
    mod = _load_backing()
    return bool(
        mod.update_pose(
            lat,
            lon,
            altitude_ft,
            heading_deg,
            quat_wxyz,
            pitch_deg,
            roll_deg,
            look_az_deg,
            look_el_deg,
            zoom_fov_deg,
            cam_rel_forward_m,
            cam_rel_right_m,
            cam_rel_up_m,
            cam_default_forward_m,
            cam_default_right_m,
            cam_default_up_m,
            cam_default_cube_size_m,
            cam_cube_forward_m,
            cam_cube_right_m,
            cam_cube_up_m,
            look_slew_active,
            das_camera_key,
            das_zoom_ratio,
            das_fov_v_deg,
            das_fov_h_deg,
            das_cam_forward_m,
            das_cam_right_m,
            das_cam_up_m,
            das_yaw_deg,
            das_pitch_deg,
            False,
            hold_point_enabled,
            whot,
            level_roll_to_horizon,
        )
    )


def latest_frame_path(max_age_ms: int = 3000) -> Optional[str]:
    mod = _load_backing()
    return mod.latest_frame_path(max_age_ms)


def stop_worker() -> None:
    mod = _load_backing()
    try:
        mod.stop_worker()
    except Exception:
        pass
