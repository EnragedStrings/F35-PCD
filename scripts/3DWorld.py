#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Dict, Optional
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request


try:
    from app_paths import app_base_dir, writable_path  # type: ignore
except Exception:
    app_base_dir = None  # type: ignore
    writable_path = None  # type: ignore

_SCRIPT_DIR = Path(__file__).resolve().parent
if callable(app_base_dir):
    try:
        _ROOT = Path(app_base_dir())
    except Exception:
        _ROOT = _SCRIPT_DIR.parent if _SCRIPT_DIR.name.lower() == "scripts" else _SCRIPT_DIR
else:
    _ROOT = _SCRIPT_DIR.parent if _SCRIPT_DIR.name.lower() == "scripts" else _SCRIPT_DIR

if callable(writable_path):
    try:
        _BASE_CACHE_DIR = Path(writable_path("CACHE", "3dworld"))
    except Exception:
        _BASE_CACHE_DIR = _ROOT / "CACHE" / "3dworld"
else:
    _BASE_CACHE_DIR = _ROOT / "CACHE" / "3dworld"
_SESSION_ID = f"{os.getpid()}_{int(time.time() * 1000)}"
_CACHE_DIR = _BASE_CACHE_DIR / _SESSION_ID
_POSE_PATH = _CACHE_DIR / "pose.json"
_FRAME_PATH = _CACHE_DIR / "tflir_frame.png"
_META_PATH = _CACHE_DIR / "frame_meta.json"
_DAS_FRAME_PATH = _CACHE_DIR / "das_frame.png"
_DAS_META_PATH = _CACHE_DIR / "das_frame_meta.json"
_WORKER_PID_PATH = _BASE_CACHE_DIR / "worker_pid.txt"
_WORKER_LOG_PATH = _BASE_CACHE_DIR / "worker.log"
_WORKER_PROC: Optional[subprocess.Popen] = None
_AIRCRAFT_STL_B64_CACHE: Optional[str] = None
_TOKEN_CHECK_PRINTED = False
_LAST_SCENE_DIAG_TS = {"tflir": 0, "das": 0}
_LAST_SCENE_DIAG_KEY = {"tflir": "", "das": ""}
_LAST_NOFRAME_WARN_MS = {"tflir": 0, "das": 0}
_LAST_WORKER_RETRY_MS = 0


def _worker_hide_window_enabled() -> bool:
    """
    Offscreen WebEngine updates can stall on Linux when hidden/minimized.
    Keep hidden only on Windows by default, but allow override.
    """
    env = str(os.environ.get("F35_3DWORLD_HIDE_WINDOW", "") or "").strip().lower()
    if env in {"1", "true", "yes", "on"}:
        return True
    if env in {"0", "false", "no", "off"}:
        return False
    return os.name == "nt"


def _is_wsl_runtime() -> bool:
    if os.name != "posix":
        return False
    try:
        rel = str(os.environ.get("WSL_DISTRO_NAME", "") or "").strip()
        if rel != "":
            return True
    except Exception:
        pass
    try:
        p = Path("/proc/version")
        if p.exists():
            txt = p.read_text(encoding="utf-8", errors="ignore").lower()
            if ("microsoft" in txt) or ("wsl" in txt):
                return True
    except Exception:
        pass
    return False


def _ensure_cache_dir() -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _BASE_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _read_token_from_settings() -> str:
    """
    Load Cesium token directly from pcd_settings.json:
      {
        "cesium_ion_token": "..."
      }
    """
    settings_candidates = []
    if callable(writable_path):
        try:
            settings_candidates.append(Path(writable_path("pcd_settings.json")))
        except Exception:
            pass
    settings_candidates.append(_ROOT / "pcd_settings.json")
    try:
        for settings_path in settings_candidates:
            if not settings_path.exists():
                continue
            raw = json.loads(settings_path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                continue
            token = str(raw.get("cesium_ion_token", "") or "").strip()
            if token != "":
                return token
        return ""
    except Exception:
        return ""


def _resolve_cesium_token() -> str:
    # Env override remains highest priority for compatibility.
    env_token = str(os.environ.get("CESIUM_ION_TOKEN", "") or "").strip()
    if env_token != "":
        return env_token
    return _read_token_from_settings()


def _verify_cesium_token(token: str, timeout_s: float = 3.0) -> tuple[bool, str]:
    tok = str(token or "").strip()
    if tok == "":
        return (False, "missing token")
    try:
        q = urllib_parse.urlencode({"access_token": tok})
        url = f"https://api.cesium.com/v1/assets/1/endpoint?{q}"
        req = urllib_request.Request(url, headers={"User-Agent": "F35-PCD/3DWorld"})
        with urllib_request.urlopen(req, timeout=max(1.0, float(timeout_s))) as resp:
            code = int(getattr(resp, "status", 200) or 200)
            if 200 <= code < 300:
                return (True, f"http {code}")
            return (False, f"http {code}")
    except urllib_error.HTTPError as exc:
        msg = ""
        try:
            body = exc.read()
            if isinstance(body, (bytes, bytearray)):
                msg = body.decode("utf-8", errors="ignore").strip()
        except Exception:
            msg = ""
        if msg != "":
            return (False, f"http {int(exc.code)} {msg}")
        return (False, f"http {int(exc.code)}")
    except Exception as exc:
        return (False, str(exc))


def _atomic_write_json(path: Path, payload: Dict) -> None:
    _ensure_cache_dir()
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    tmp.replace(path)


def _is_proc_alive(proc: Optional[subprocess.Popen]) -> bool:
    try:
        return proc is not None and proc.poll() is None
    except Exception:
        return False


def _tail_worker_log_lines(max_lines: int = 12) -> str:
    try:
        if not _WORKER_LOG_PATH.exists():
            return ""
        data = _WORKER_LOG_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()
        if not data:
            return ""
        tail = data[-max(1, int(max_lines)) :]
        return "\n".join(tail)
    except Exception:
        return ""


def _load_aircraft_stl_b64() -> str:
    global _AIRCRAFT_STL_B64_CACHE
    if _AIRCRAFT_STL_B64_CACHE is not None:
        return str(_AIRCRAFT_STL_B64_CACHE)
    stl_path = _ROOT / "models" / "F-35.stl"
    try:
        raw = stl_path.read_bytes()
        _AIRCRAFT_STL_B64_CACHE = base64.b64encode(raw).decode("ascii")
    except Exception:
        _AIRCRAFT_STL_B64_CACHE = ""
    return str(_AIRCRAFT_STL_B64_CACHE)


def _read_existing_worker_pid() -> Optional[int]:
    try:
        if not _WORKER_PID_PATH.exists():
            return None
        raw = str(_WORKER_PID_PATH.read_text(encoding="utf-8")).strip()
        if raw == "":
            return None
        return int(raw)
    except Exception:
        return None


def _terminate_pid(pid: int) -> None:
    if int(pid) <= 0:
        return
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(int(pid)), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            try:
                os.kill(int(pid), 15)
            except Exception:
                pass
    except Exception:
        pass


def ensure_worker_running() -> bool:
    global _WORKER_PROC, _TOKEN_CHECK_PRINTED
    if _is_proc_alive(_WORKER_PROC):
        return True
    # Surface why a previously-started worker died before we respawn.
    try:
        if _WORKER_PROC is not None:
            rc_prev = _WORKER_PROC.poll()
            if rc_prev is not None:
                print(f"[3DWORLD] previous worker exited rc={int(rc_prev)}; respawning")
                tail_prev = _tail_worker_log_lines()
                if tail_prev:
                    print("[3DWORLD] worker log tail (previous-exit):")
                    print(tail_prev)
    except Exception:
        pass
    _ensure_cache_dir()
    # Ensure stale worker from previous run doesn't keep writing frames.
    old_pid = _read_existing_worker_pid()
    if old_pid is not None:
        _terminate_pid(int(old_pid))
        try:
            time.sleep(0.08)
        except Exception:
            pass
    pid_tag = str(_WORKER_PID_PATH.name).lower()
    role_tag = "das" if "das" in pid_tag else "tflir"
    if bool(getattr(sys, "frozen", False)):
        cmd = [
            sys.executable,
            "--3dworld-worker",
            "--session",
            str(_SESSION_ID),
            "--role",
            str(role_tag),
        ]
    else:
        cmd = [sys.executable, str(Path(__file__).resolve()), "--worker", "--session", str(_SESSION_ID)]
    if not _TOKEN_CHECK_PRINTED:
        _TOKEN_CHECK_PRINTED = True
        token = _resolve_cesium_token()
        ok, detail = _verify_cesium_token(token)
        if ok:
            print(f"[3DWORLD] Cesium token check: OK ({detail})")
        else:
            print(f"[3DWORLD] Cesium token check: FAIL ({detail})")
    creation_flags = 0
    try:
        if os.name == "nt":
            creation_flags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    except Exception:
        creation_flags = 0

    def _spawn_worker(single_process: bool) -> Optional[subprocess.Popen]:
        env = os.environ.copy()
        mode_tag = "sp" if single_process else "mp"
        chromium_profile = _BASE_CACHE_DIR / f"chromium_profile_{role_tag}_{mode_tag}_{_SESSION_ID}"
        try:
            chromium_profile.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        flags = str(env.get("QTWEBENGINE_CHROMIUM_FLAGS", "") or "").strip()
        extra = [
            f"--user-data-dir={chromium_profile}",
            "--ignore-gpu-blocklist",
        ]
        if os.name != "nt":
            wsl_force_soft = _is_wsl_runtime() or (
                str(env.get("F35_3DWORLD_FORCE_SOFTWARE", "") or "").strip().lower() in {"1", "true", "yes", "on"}
            )
            if wsl_force_soft:
                # WSL often cannot present Chromium GPU textures into Qt reliably.
                # Force software paths on both Chromium and Qt scene graph.
                extra.extend(
                    [
                        "--disable-gpu",
                        "--disable-gpu-compositing",
                        "--disable-features=Vulkan,DefaultPassthroughCommandDecoder",
                    ]
                )
                env["QT_QUICK_BACKEND"] = "software"
                env["QT_XCB_FORCE_SOFTWARE_OPENGL"] = "1"
                env["LIBGL_ALWAYS_SOFTWARE"] = "1"
            else:
                extra.extend(
                    [
                        "--use-gl=angle",
                        "--use-angle=default",
                        "--disable-features=Vulkan,DefaultPassthroughCommandDecoder",
                    ]
                )
            # Do not force ozone platform; many distro/Qt builds do not include
            # all ozone backends (e.g. x11), and forcing an unsupported one
            # crashes Chromium at startup.
            ozone_env = str(env.get("F35_3DWORLD_OZONE_PLATFORM", "") or "").strip().lower()
            if ozone_env in {"x11", "wayland", "headless"}:
                extra.append(f"--ozone-platform={ozone_env}")
            env["QTWEBENGINE_DISABLE_DMABUF_RENDERER"] = "1"
            if not wsl_force_soft:
                env.pop("QT_QUICK_BACKEND", None)
                env.pop("LIBGL_ALWAYS_SOFTWARE", None)
        if single_process:
            extra.extend(
                [
                    "--no-sandbox",
                    "--single-process",
                    "--no-proxy-server",
                    "--enable-features=NetworkServiceInProcess",
                ]
            )
            env["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
        if flags != "":
            flags = f"{flags} {' '.join(extra)}"
        else:
            flags = " ".join(extra)
        env["QTWEBENGINE_CHROMIUM_FLAGS"] = flags
        log_file = None
        try:
            log_file = open(_WORKER_LOG_PATH, "a", encoding="utf-8")
            log_file.write(
                f"[{int(time.time()*1000)}] spawn session={_SESSION_ID} single_process={int(single_process)} "
                f"flags={flags} "
                f"dmabuf={env.get('QTWEBENGINE_DISABLE_DMABUF_RENDERER','')} "
                f"qquick={env.get('QT_QUICK_BACKEND','')} "
                f"libgl_sw={env.get('LIBGL_ALWAYS_SOFTWARE','')}\n"
            )
            log_file.flush()
        except Exception:
            log_file = None
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(_ROOT),
                stdin=subprocess.DEVNULL,
                stdout=(log_file if log_file is not None else subprocess.DEVNULL),
                stderr=(log_file if log_file is not None else subprocess.DEVNULL),
                creationflags=creation_flags,
                env=env,
            )
            return proc
        except Exception:
            try:
                if log_file is not None:
                    log_file.close()
            except Exception:
                pass
            return None
        finally:
            try:
                if log_file is not None:
                    log_file.close()
            except Exception:
                pass

    prefer_single_process = os.name == "nt"
    print(
        f"[3DWORLD] worker spawn requested role={role_tag} session={_SESSION_ID} "
        f"single_process_pref={int(bool(prefer_single_process))} log={_WORKER_LOG_PATH}"
    )
    _WORKER_PROC = _spawn_worker(single_process=prefer_single_process)
    if _WORKER_PROC is None:
        print(f"[3DWORLD] worker spawn failed role={role_tag} (Popen returned None)")
        return False
    # If worker crashes shortly after startup, retry once with a
    # single-process Chromium fallback.
    crashed_early = False
    for _ in range(12):
        try:
            time.sleep(0.2)
        except Exception:
            pass
        if _WORKER_PROC.poll() is not None:
            crashed_early = True
            break
    if crashed_early:
        code0 = None
        try:
            code0 = int(_WORKER_PROC.poll()) if _WORKER_PROC is not None else None
        except Exception:
            code0 = None
        print(
            f"[3DWORLD] worker crashed early role={role_tag} rc={code0} "
            f"retrying single-process fallback"
        )
        tail = _tail_worker_log_lines()
        if tail:
            print("[3DWORLD] worker log tail (pre-fallback):")
            print(tail)
        _WORKER_PROC = _spawn_worker(single_process=True)
        if _WORKER_PROC is None:
            print(f"[3DWORLD] worker fallback spawn failed role={role_tag}")
            return False
        crashed_again = False
        for _ in range(12):
            try:
                time.sleep(0.2)
            except Exception:
                pass
            if _WORKER_PROC.poll() is not None:
                crashed_again = True
                break
        if crashed_again:
            code1 = None
            try:
                code1 = int(_WORKER_PROC.poll()) if _WORKER_PROC is not None else None
            except Exception:
                code1 = None
            print(
                f"[3DWORLD] worker fallback crashed role={role_tag} rc={code1} "
                f"log={_WORKER_LOG_PATH}"
            )
            tail = _tail_worker_log_lines()
            if tail:
                print("[3DWORLD] worker log tail (fallback):")
                print(tail)
            return False
    try:
        _WORKER_PID_PATH.write_text(str(int(_WORKER_PROC.pid)), encoding="utf-8")
    except Exception:
        pass
    try:
        print(
            f"[3DWORLD] worker started role={role_tag} pid={int(_WORKER_PROC.pid)} "
            f"log={_WORKER_LOG_PATH}"
        )
    except Exception:
        pass
    return True


def stop_worker() -> None:
    global _WORKER_PROC
    proc = _WORKER_PROC
    _WORKER_PROC = None
    if proc is None:
        return
    try:
        proc.terminate()
    except Exception:
        pass


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
    show_aircraft_model: bool = True,
    hold_point_enabled: bool = True,
    whot: bool = True,
    level_roll_to_horizon: bool = False,
) -> bool:
    if not ensure_worker_running():
        return False
    payload = {
        "ts_ms": int(time.time() * 1000),
        "lat": float(lat),
        "lon": float(lon),
        "altitude_ft": float(max(0.0, altitude_ft)),
        "heading_deg": float(heading_deg) % 360.0,
        "pitch_deg": float(pitch_deg),
        "roll_deg": float(roll_deg),
        "look_az_deg": float(look_az_deg),
        "look_el_deg": float(look_el_deg),
        "zoom_fov_deg": float(zoom_fov_deg),
        "cam_rel_forward_m": float(cam_rel_forward_m),
        "cam_rel_right_m": float(cam_rel_right_m),
        "cam_rel_up_m": float(cam_rel_up_m),
        "cam_default_forward_m": float(cam_default_forward_m),
        "cam_default_right_m": float(cam_default_right_m),
        "cam_default_up_m": float(cam_default_up_m),
        "cam_default_cube_size_m": float(cam_default_cube_size_m),
        "cam_cube_forward_m": float(cam_cube_forward_m),
        "cam_cube_right_m": float(cam_cube_right_m),
        "cam_cube_up_m": float(cam_cube_up_m),
        "look_slew_active": bool(look_slew_active),
        "das_camera_key": str(das_camera_key or "DAS-BA"),
        "das_zoom_ratio": float(max(0.1, das_zoom_ratio)),
        "das_fov_v_deg": float(max(0.1, das_fov_v_deg)),
        "das_fov_h_deg": float(max(0.1, das_fov_h_deg)),
        "das_cam_forward_m": float(das_cam_forward_m),
        "das_cam_right_m": float(das_cam_right_m),
        "das_cam_up_m": float(das_cam_up_m),
        "das_yaw_deg": float(das_yaw_deg),
        "das_pitch_deg": float(das_pitch_deg),
        "show_aircraft_model": bool(show_aircraft_model),
        "hold_point_enabled": bool(hold_point_enabled),
        "whot": bool(whot),
        "level_roll_to_horizon": bool(level_roll_to_horizon),
    }
    if isinstance(quat_wxyz, dict):
        payload["quat_wxyz"] = {
            "w": float(quat_wxyz.get("w", 1.0)),
            "x": float(quat_wxyz.get("x", 0.0)),
            "y": float(quat_wxyz.get("y", 0.0)),
            "z": float(quat_wxyz.get("z", 0.0)),
        }
    try:
        _atomic_write_json(_POSE_PATH, payload)
        return True
    except Exception:
        return False


def latest_frame_path(max_age_ms: int = 3000) -> Optional[str]:
    try:
        _ensure_worker_retry()
        if not _FRAME_PATH.exists() or not _META_PATH.exists():
            _maybe_log_no_frame("tflir", "missing_frame_or_meta")
            return None
        meta = json.loads(_META_PATH.read_text(encoding="utf-8"))
        ts_ms = int(meta.get("ts_ms", 0) or 0)
        age_ms = int(time.time() * 1000) - ts_ms
        if age_ms > int(max_age_ms):
            _maybe_log_no_frame("tflir", f"stale age_ms={age_ms}")
            return None
        _maybe_log_scene_diag("tflir", meta, age_ms)
        return str(_FRAME_PATH)
    except Exception:
        return None


def latest_das_frame_path(max_age_ms: int = 3000) -> Optional[str]:
    try:
        _ensure_worker_retry()
        if not _DAS_FRAME_PATH.exists() or not _DAS_META_PATH.exists():
            _maybe_log_no_frame("das", "missing_frame_or_meta")
            return None
        meta = json.loads(_DAS_META_PATH.read_text(encoding="utf-8"))
        ts_ms = int(meta.get("ts_ms", 0) or 0)
        age_ms = int(time.time() * 1000) - ts_ms
        if age_ms > int(max_age_ms):
            _maybe_log_no_frame("das", f"stale age_ms={age_ms}")
            return None
        _maybe_log_scene_diag("das", meta, age_ms)
        return str(_DAS_FRAME_PATH)
    except Exception:
        return None


def _maybe_log_scene_diag(mode: str, meta: Dict, age_ms: int) -> None:
    try:
        m = "das" if str(mode).lower().strip() == "das" else "tflir"
        status = str(meta.get("scene_status", "") or "").strip()
        source = str(meta.get("source", "") or "").strip()
        err = str(meta.get("scene_error", "") or "").strip()
        key = f"{status}|{source}|{err[:120]}"
        now_ms = int(time.time() * 1000)
        changed = key != _LAST_SCENE_DIAG_KEY.get(m, "")
        quiet_period_ok = (now_ms - int(_LAST_SCENE_DIAG_TS.get(m, 0) or 0)) >= 3000
        if changed or quiet_period_ok:
            _LAST_SCENE_DIAG_KEY[m] = key
            _LAST_SCENE_DIAG_TS[m] = now_ms
            if status not in {"ready", ""} or source in {"none", "python_fallback", "js_fallback"}:
                print(
                    f"[3DWORLD][{m.upper()}] status={status or '-'} source={source or '-'} "
                    f"age_ms={int(age_ms)} err={(err[:160] if err else '-')} "
                    f"log={_WORKER_LOG_PATH}"
                )
    except Exception:
        return


def _maybe_log_no_frame(mode: str, reason: str) -> None:
    try:
        m = "das" if str(mode).lower().strip() == "das" else "tflir"
        now_ms = int(time.time() * 1000)
        last_ms = int(_LAST_NOFRAME_WARN_MS.get(m, 0) or 0)
        if (now_ms - last_ms) < 3000:
            return
        _LAST_NOFRAME_WARN_MS[m] = now_ms
        proc_alive = _is_proc_alive(_WORKER_PROC)
        pid_txt = "-"
        try:
            if _WORKER_PROC is not None and _WORKER_PROC.pid:
                pid_txt = str(int(_WORKER_PROC.pid))
        except Exception:
            pid_txt = "-"
        print(
            f"[3DWORLD][{m.upper()}] no_frame reason={reason} worker_alive={int(bool(proc_alive))} "
            f"pid={pid_txt} log={_WORKER_LOG_PATH}"
        )
    except Exception:
        return


def _ensure_worker_retry() -> None:
    """
    If frame readers are called before update_pose, make sure the worker still
    gets a chance to spawn. This prevents sticky no-frame states where the
    worker never starts because pose extraction temporarily returns None.
    """
    global _LAST_WORKER_RETRY_MS
    try:
        if _is_proc_alive(_WORKER_PROC):
            return
        now_ms = int(time.time() * 1000)
        if (now_ms - int(_LAST_WORKER_RETRY_MS)) < 1200:
            return
        _LAST_WORKER_RETRY_MS = now_ms
        ensure_worker_running()
    except Exception:
        return


def _run_worker() -> int:
    try:
        from PySide6.QtCore import QCoreApplication, QTimer, Qt, QUrl
        from PySide6.QtWidgets import QApplication, QMainWindow
        from PySide6.QtWebEngineWidgets import QWebEngineView
    except Exception as exc:
        try:
            _ensure_cache_dir()
            with open(_WORKER_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"[{int(time.time()*1000)}] [3DWORLD][WORKER][IMPORT_FAIL] {exc}\n")
                f.write(traceback.format_exc() + "\n")
        except Exception:
            pass
        return 1
    try:
        from PySide6.QtWebEngineCore import QWebEngineSettings  # type: ignore
    except Exception:
        QWebEngineSettings = None  # type: ignore

    token = _resolve_cesium_token()
    html = _worker_html(token, _load_aircraft_stl_b64())

    session_id = None
    if "--session" in sys.argv:
        try:
            i = sys.argv.index("--session")
            if i + 1 < len(sys.argv):
                session_id = str(sys.argv[i + 1]).strip()
        except Exception:
            session_id = None
    if not session_id:
        session_id = "default"
    session_cache = _BASE_CACHE_DIR / str(session_id)
    pose_path = session_cache / "pose.json"
    frame_path = session_cache / "tflir_frame.png"
    meta_path = session_cache / "frame_meta.json"
    das_frame_path = session_cache / "das_frame.png"
    das_meta_path = session_cache / "das_frame_meta.json"
    session_cache.mkdir(parents=True, exist_ok=True)

    class _Win(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            _ensure_cache_dir()
            self.setWindowTitle("3DWorld Worker")
            self.resize(960, 540)
            hide_window = _worker_hide_window_enabled()
            try:
                if hide_window:
                    self.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
            except Exception:
                pass
            self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
            self.web = QWebEngineView(self)
            self.setCentralWidget(self.web)
            self.web.setHtml(html, QUrl("https://localhost/"))
            try:
                self.web.loadStarted.connect(lambda: self._log("[3DWORLD][WEB] loadStarted"))
                self.web.loadFinished.connect(lambda ok: self._log(f"[3DWORLD][WEB] loadFinished ok={int(bool(ok))}"))
                self.web.urlChanged.connect(lambda u: self._log(f"[3DWORLD][WEB] url={str(u.toString())}"))
                self.web.renderProcessTerminated.connect(
                    lambda term, code: self._log(f"[3DWORLD][WEB] renderProcessTerminated term={int(term)} code={int(code)}")
                )
            except Exception:
                pass

            self._last_pose_ms = -1
            self._capture_busy = False
            self._capture_mode = "tflir"
            self._diag_last_print_ms = 0
            self._diag_last_status = ""
            self._diag_last_source = ""

            self.pose_timer = QTimer(self)
            self.pose_timer.timeout.connect(self._tick_pose)
            self.pose_timer.start(20)

            self.frame_timer = QTimer(self)
            self.frame_timer.timeout.connect(self._tick_capture)
            self.frame_timer.start(33)
            self._log(
                f"[3DWORLD][WORKER] init session={session_id} hide_window={int(bool(hide_window))} "
                f"platform={sys.platform} pid={os.getpid()}"
            )

        def _log(self, text: str) -> None:
            try:
                ts = int(time.time() * 1000)
                with open(_WORKER_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(f"[{ts}] {text}\n")
            except Exception:
                pass

        def _tick_pose(self) -> None:
            if not pose_path.exists():
                return
            try:
                pose = json.loads(pose_path.read_text(encoding="utf-8"))
            except Exception:
                return
            ts_ms = int(pose.get("ts_ms", 0) or 0)
            if ts_ms <= self._last_pose_ms:
                return
            self._last_pose_ms = ts_ms
            try:
                show_model = bool(pose.get("show_aircraft_model", True))
                self._capture_mode = "tflir" if show_model else "das"
            except Exception:
                self._capture_mode = "tflir"
            js = "window.__setPose && window.__setPose(%s);" % json.dumps(pose)
            try:
                self.web.page().runJavaScript(js)
            except Exception:
                pass

        def _tick_capture(self) -> None:
            if self._capture_busy:
                return
            self._capture_busy = True
            js = """
            (function() {
              const mode = %MODE%;
              let source = "none";
              let status = "";
              let lastError = "";
              let camHeadingWorldDeg = null;
              let camLookAzDeg = null;
              try {
                if (window.__captureFrame) {
                  const d = window.__captureFrame(mode);
                  if (typeof d === "string" && d.indexOf("data:image/png;base64,") === 0) {
                    source = String(window.__lastCaptureSource || "capture");
                    status = String(window.__sceneStatus || "");
                    lastError = String(window.__sceneLastError || "");
                    if (typeof window.__tflir_cam_heading_world_deg === "number") {
                      camHeadingWorldDeg = Number(window.__tflir_cam_heading_world_deg);
                    }
                    if (typeof window.__tflir_final_look_az_deg === "number") {
                      camLookAzDeg = Number(window.__tflir_final_look_az_deg);
                    }
                    return {
                      png: d,
                      source: source,
                      status: status,
                      lastError: lastError,
                      camHeadingWorldDeg: camHeadingWorldDeg,
                      camLookAzDeg: camLookAzDeg
                    };
                  }
                }
              } catch (_e) {}
              try {
                let c = document.getElementById("codex_fb_capture");
                if (!c) {
                  c = document.createElement("canvas");
                  c.id = "codex_fb_capture";
                  c.style.position = "fixed";
                  c.style.left = "0";
                  c.style.top = "0";
                  c.style.width = "100vw";
                  c.style.height = "100vh";
                  c.style.zIndex = "99999";
                  c.style.pointerEvents = "none";
                  document.body.appendChild(c);
                }
                c.width = Math.max(2, Math.floor(window.innerWidth || 2));
                c.height = Math.max(2, Math.floor(window.innerHeight || 2));
                const g = c.getContext("2d");
                const w = c.width;
                const h = c.height;
                g.fillStyle = "#0d0d0d";
                g.fillRect(0, 0, w, h);
                g.fillStyle = "#2a2a2a";
                g.fillRect(0, 0, w, Math.floor(h * 0.48));
                g.strokeStyle = "#666666";
                g.lineWidth = 2;
                g.beginPath();
                g.moveTo(0, Math.floor(h * 0.48));
                g.lineTo(w, Math.floor(h * 0.48));
                g.stroke();
                g.strokeStyle = "#d0d0d0";
                g.lineWidth = 2;
                g.beginPath();
                g.moveTo((w * 0.5) - 20, h * 0.5);
                g.lineTo((w * 0.5) + 20, h * 0.5);
                g.moveTo(w * 0.5, (h * 0.5) - 20);
                g.lineTo(w * 0.5, (h * 0.5) + 20);
                g.stroke();
                g.fillStyle = "#8a8a8a";
                g.font = "18px monospace";
                g.fillText((mode === "das") ? "DAS FALLBACK" : "TFLIR FALLBACK", 18, 28);
                source = "python_fallback";
                status = String(window.__sceneStatus || "");
                lastError = String(window.__sceneLastError || "");
                if (typeof window.__tflir_cam_heading_world_deg === "number") {
                  camHeadingWorldDeg = Number(window.__tflir_cam_heading_world_deg);
                }
                if (typeof window.__tflir_final_look_az_deg === "number") {
                  camLookAzDeg = Number(window.__tflir_final_look_az_deg);
                }
                return {
                  png: c.toDataURL("image/png"),
                  source: source,
                  status: status,
                  lastError: lastError,
                  camHeadingWorldDeg: camHeadingWorldDeg,
                  camLookAzDeg: camLookAzDeg
                };
              } catch (_e) {
                source = "none";
                status = String(window.__sceneStatus || "");
                lastError = String(window.__sceneLastError || "");
                if (typeof window.__tflir_cam_heading_world_deg === "number") {
                  camHeadingWorldDeg = Number(window.__tflir_cam_heading_world_deg);
                }
                if (typeof window.__tflir_final_look_az_deg === "number") {
                  camLookAzDeg = Number(window.__tflir_final_look_az_deg);
                }
                return {
                  png: "",
                  source: source,
                  status: status,
                  lastError: lastError,
                  camHeadingWorldDeg: camHeadingWorldDeg,
                  camLookAzDeg: camLookAzDeg
                };
              }
            })();
            """
            mode = str(self._capture_mode or "tflir").lower().strip()
            js_mode = js.replace("%MODE%", json.dumps(mode))

            def _cb(result):
                wrote_frame = False
                frame_size = 0
                source = ""
                status = ""
                last_error = ""
                cam_heading_world_deg = None
                cam_look_az_deg = None
                try:
                    try:
                        payload = ""
                        if isinstance(result, dict):
                            payload = str(result.get("png", "") or "")
                            source = str(result.get("source", "") or "")
                            status = str(result.get("status", "") or "")
                            last_error = str(result.get("lastError", "") or "")
                            try:
                                raw_cam_hdg = result.get("camHeadingWorldDeg", None)
                                if raw_cam_hdg is not None:
                                    cam_heading_world_deg = float(raw_cam_hdg)
                            except Exception:
                                cam_heading_world_deg = None
                            try:
                                raw_cam_az = result.get("camLookAzDeg", None)
                                if raw_cam_az is not None:
                                    cam_look_az_deg = float(raw_cam_az)
                            except Exception:
                                cam_look_az_deg = None
                        else:
                            payload = str(result or "")
                        if not payload.startswith("data:image/png;base64,"):
                            payload = ""
                        if payload.startswith("data:image/png;base64,"):
                            b64 = payload.split(",", 1)[1]
                            raw = base64.b64decode(b64, validate=False)
                            tmp_frame = frame_path.with_suffix(frame_path.suffix + ".tmp")
                            tmp_frame.write_bytes(raw)
                            tmp_frame.replace(frame_path)
                            wrote_frame = True
                            frame_size = int(len(raw))
                    except Exception:
                        pass
                    # On some Linux/WSL stacks, WebGL canvas readback returns
                    # empty due compositor/dma-buf issues. Fall back to Qt
                    # widget capture so we still get pixels.
                    if not wrote_frame:
                        try:
                            pix = None
                            src_tag = ""
                            try:
                                p0 = self.web.grab()
                                if p0 is not None and (not p0.isNull()):
                                    pix = p0
                                    src_tag = "qt_web_grab"
                            except Exception:
                                pix = None
                            if pix is None:
                                try:
                                    p1 = self.grab()
                                    if p1 is not None and (not p1.isNull()):
                                        pix = p1
                                        src_tag = "qt_win_grab"
                                except Exception:
                                    pix = None
                            if pix is None:
                                try:
                                    scr = QApplication.primaryScreen()
                                    if scr is not None:
                                        p2 = scr.grabWindow(int(self.winId()))
                                        if p2 is not None and (not p2.isNull()):
                                            pix = p2
                                            src_tag = "qt_screen_grab"
                                except Exception:
                                    pix = None
                            if pix is not None and (not pix.isNull()):
                                tmp_frame = frame_path.with_suffix(frame_path.suffix + ".tmp")
                                ok = bool(pix.save(str(tmp_frame), "PNG"))
                                if ok and tmp_frame.exists():
                                    frame_size = int(tmp_frame.stat().st_size)
                                    if frame_size > 0:
                                        tmp_frame.replace(frame_path)
                                        wrote_frame = True
                                        if not source:
                                            source = src_tag if src_tag else "qt_grab"
                                        if not status:
                                            status = "qt_grab_only"
                        except Exception:
                            pass
                    if wrote_frame:
                        try:
                            _atomic_write_json(
                                meta_path,
                                {
                                    "ts_ms": int(time.time() * 1000),
                                    "size": int(frame_size),
                                    "session_id": str(session_id),
                                    "mode": str(mode),
                                    "source": str(source),
                                    "scene_status": str(status),
                                    "scene_error": str(last_error),
                                    "cam_heading_world_deg": (
                                        float(cam_heading_world_deg) if isinstance(cam_heading_world_deg, (int, float)) else None
                                    ),
                                    "cam_look_az_deg": (
                                        float(cam_look_az_deg) if isinstance(cam_look_az_deg, (int, float)) else None
                                    ),
                                },
                            )
                        except Exception:
                            pass
                    now_ms = int(time.time() * 1000)
                    should_log = False
                    if source != self._diag_last_source or status != self._diag_last_status:
                        should_log = True
                    if (now_ms - int(self._diag_last_print_ms)) >= 2000:
                        should_log = True
                    if should_log:
                        self._diag_last_print_ms = now_ms
                        self._diag_last_source = str(source)
                        self._diag_last_status = str(status)
                        self._log(
                            f"[3DWORLD][CAPTURE] mode={mode} ok={int(bool(wrote_frame))} "
                            f"source={source or '-'} status={status or '-'} "
                            f"err={(last_error[:160] if last_error else '-')}"
                        )
                finally:
                    self._capture_busy = False

            try:
                self.web.page().runJavaScript(js_mode, _cb)
            except Exception:
                self._capture_busy = False

    try:
        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
    except Exception:
        pass
    app = QApplication(sys.argv)
    w = _Win()
    if QWebEngineSettings is not None:
        try:
            s = w.web.settings()
            s.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
            s.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        except Exception:
            pass
    # Must show() for webengine rendering.
    w.show()
    return app.exec()


def _worker_html(token: str, aircraft_stl_b64: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    html, body, #c, #fb {{
      width:100%; height:100%; margin:0; padding:0; overflow:hidden; background:#000;
    }}
    #c, #fb {{
      position:absolute; left:0; top:0;
    }}
    #fb {{
      z-index:0;
    }}
    #c {{
      z-index:1;
    }}
    .cesium-viewer-bottom {{
      display:none !important;
    }}
  </style>
</head>
<body>
  <canvas id="fb"></canvas>
  <div id="c"></div>
  <script>
    const token = {json.dumps(token)};
    async function _loadScript(url) {{
      return await new Promise((resolve, reject) => {{
        try {{
          const s = document.createElement("script");
          s.src = String(url || "");
          s.async = true;
          s.crossOrigin = "anonymous";
          s.onload = () => resolve(true);
          s.onerror = () => reject(new Error("script_load_failed"));
          document.head.appendChild(s);
        }} catch (_e) {{
          reject(_e);
        }}
      }});
    }}
    async function _loadCss(url) {{
      return await new Promise((resolve, reject) => {{
        try {{
          const l = document.createElement("link");
          l.rel = "stylesheet";
          l.href = String(url || "");
          l.onload = () => resolve(true);
          l.onerror = () => reject(new Error("css_load_failed"));
          document.head.appendChild(l);
        }} catch (_e) {{
          reject(_e);
        }}
      }});
    }}
    async function _ensureCesiumLoaded() {{
      if (typeof Cesium !== "undefined") return true;
      const cssUrls = [
        "https://cesium.com/downloads/cesiumjs/releases/1.126/Build/Cesium/Widgets/widgets.css",
        "https://cdn.jsdelivr.net/npm/cesium@1.126.0/Build/Cesium/Widgets/widgets.css",
        "https://unpkg.com/cesium@1.126.0/Build/Cesium/Widgets/widgets.css"
      ];
      const jsUrls = [
        "https://cesium.com/downloads/cesiumjs/releases/1.126/Build/Cesium/Cesium.js",
        "https://cdn.jsdelivr.net/npm/cesium@1.126.0/Build/Cesium/Cesium.js",
        "https://unpkg.com/cesium@1.126.0/Build/Cesium/Cesium.js"
      ];
      for (let i = 0; i < cssUrls.length; i += 1) {{
        try {{
          await _loadCss(cssUrls[i]);
          break;
        }} catch (_e) {{}}
      }}
      for (let i = 0; i < jsUrls.length; i += 1) {{
        try {{
          await _loadScript(jsUrls[i]);
          if (typeof Cesium !== "undefined") return true;
        }} catch (_e) {{}}
      }}
      return (typeof Cesium !== "undefined");
    }}
    const aircraftStlB64 = {json.dumps(aircraft_stl_b64)};
    let viewer = null;
    let aircraftPrimitive = null;
    let aircraftLoadAttempted = false;
    let sceneStatus = "boot";
    let sceneLastError = "";
    let lastCaptureSource = "";
    window.__sceneStatus = "boot";
    window.__sceneLastError = "";
    window.__lastCaptureSource = "";
    try {{
      window.addEventListener("error", (ev) => {{
        try {{
          sceneLastError = String((ev && ev.message) ? ev.message : "js_error");
          window.__sceneLastError = sceneLastError;
        }} catch (_e) {{}}
      }});
      window.addEventListener("unhandledrejection", (ev) => {{
        try {{
          sceneLastError = String((ev && ev.reason) ? ev.reason : "js_rejection");
          window.__sceneLastError = sceneLastError;
        }} catch (_e) {{}}
      }});
    }} catch (_e) {{}}
    let pose = {{
      lat: 33.535,
      lon: -112.383,
      altitude_ft: 0.0,
      heading_deg: 0.0,
      pitch_deg: 0.0,
      roll_deg: 0.0,
      look_az_deg: 90.0,
      look_el_deg: 0.0,
      zoom_fov_deg: 45.0,
      cam_rel_forward_m: 0.0,
      cam_rel_right_m: 0.0,
      cam_rel_up_m: 0.0,
      cam_default_forward_m: 0.0,
      cam_default_right_m: 2.79,
      cam_default_up_m: -0.59,
      cam_default_cube_size_m: 1.0,
      cam_cube_forward_m: 0.0,
      cam_cube_right_m: 2.79,
      cam_cube_up_m: -0.59,
      look_slew_active: false,
      hold_point_enabled: true,
      whot: true,
      level_roll_to_horizon: false,
      das_camera_key: "DAS-BA",
      das_zoom_ratio: 2.9,
      das_fov_v_deg: 29.0,
      das_fov_h_deg: 29.0,
      das_cam_forward_m: 0.0,
      das_cam_right_m: 0.0,
      das_cam_up_m: 0.0,
      das_yaw_deg: 0.0,
      das_pitch_deg: 0.0,
      show_aircraft_model: true
    }};
    let smoothPose = Object.assign({{}}, pose);
    let poseInitialized = false;
    let lookTargetPoint = null;
    let lastCmdLookAz = 90.0;
    let lastCmdLookEl = 0.0;
    let lastStabPrintMs = 0;
    const fbCanvas = document.getElementById("fb");
    const fbCtx = fbCanvas ? fbCanvas.getContext("2d") : null;

    function _resizeFallback() {{
      try {{
        if (!fbCanvas) return;
        const w = Math.max(2, Math.floor(window.innerWidth || 2));
        const h = Math.max(2, Math.floor(window.innerHeight || 2));
        if (fbCanvas.width !== w) fbCanvas.width = w;
        if (fbCanvas.height !== h) fbCanvas.height = h;
      }} catch (_e) {{}}
    }}

    function _drawFallback() {{
      _resizeFallback();
      if (!fbCanvas || !fbCtx) return;
      const w = fbCanvas.width;
      const h = fbCanvas.height;
      const cx = w * 0.5;
      const cy = h * 0.5;
      const rollRad = (Number(smoothPose.roll_deg || 0.0) * Math.PI) / 180.0;
      const pitchPx = Math.max(-h * 0.45, Math.min(h * 0.45, Number(smoothPose.pitch_deg || 0.0) * (h / 80.0)));

      fbCtx.fillStyle = "#101010";
      fbCtx.fillRect(0, 0, w, h);
      fbCtx.save();
      fbCtx.translate(cx, cy);
      fbCtx.rotate(-rollRad);
      const horizonY = pitchPx;
      fbCtx.fillStyle = "#3a3a3a";
      fbCtx.fillRect(-w, -h * 2, w * 2, h * 2 + horizonY);
      fbCtx.fillStyle = "#101010";
      fbCtx.fillRect(-w, horizonY, w * 2, h * 2);
      // Soft transition band near horizon (avoid a hard divider).
      const band = fbCtx.createLinearGradient(0, horizonY - 24, 0, horizonY + 24);
      band.addColorStop(0.0, "rgba(120,120,120,0.00)");
      band.addColorStop(0.5, "rgba(120,120,120,0.35)");
      band.addColorStop(1.0, "rgba(120,120,120,0.00)");
      fbCtx.fillStyle = band;
      fbCtx.fillRect(-w, horizonY - 24, w * 2, 48);

      fbCtx.strokeStyle = "#2f2f2f";
      fbCtx.lineWidth = 1;
      const azShift = Math.max(-0.6, Math.min(0.6, Number(smoothPose.look_az_deg || 0.0) / 120.0)) * (w * 0.35);
      const vanishX = azShift;
      const vanishY = horizonY + 6;
      for (let i = 1; i <= 10; i += 1) {{
        const t = i / 10.0;
        const y = horizonY + (t * t) * (h * 0.9);
        fbCtx.beginPath();
        fbCtx.moveTo(-w, y);
        fbCtx.lineTo(w, y);
        fbCtx.stroke();
      }}
      for (let k = -8; k <= 8; k += 1) {{
        const x0 = (k / 8.0) * (w * 0.95);
        fbCtx.beginPath();
        fbCtx.moveTo(x0, h * 0.95);
        fbCtx.lineTo(vanishX + (x0 * 0.08), vanishY);
        fbCtx.stroke();
      }}
      fbCtx.restore();

      fbCtx.strokeStyle = "#d0d0d0";
      fbCtx.lineWidth = 2;
      fbCtx.beginPath();
      fbCtx.moveTo(cx - 20, cy);
      fbCtx.lineTo(cx + 20, cy);
      fbCtx.moveTo(cx, cy - 20);
      fbCtx.lineTo(cx, cy + 20);
      fbCtx.stroke();
    }}
    try {{
      window.addEventListener("resize", _resizeFallback);
    }} catch (_e) {{}}
    _resizeFallback();
    _drawFallback();

    function applyDay(v) {{
      v.scene.globe.show = true;
      v.scene.globe.enableLighting = false;
      // Keep subtle atmospheric fade so the horizon is not a hard seam.
      v.scene.globe.showGroundAtmosphere = true;
      v.scene.skyAtmosphere.show = true;
      v.scene.fog.enabled = true;
      v.scene.requestRenderMode = false;
      v.shadows = false;
      v.scene.highDynamicRange = false;
      try {{ v.scene.skyBox.show = false; }} catch (_e) {{}}
      try {{ v.scene.sun.show = false; }} catch (_e) {{}}
      try {{ v.scene.moon.show = false; }} catch (_e) {{}}
      try {{ v.scene.backgroundColor = Cesium.Color.BLACK; }} catch (_e) {{}}
      const noon = Cesium.JulianDate.fromDate(new Date(Date.UTC(2026,0,1,12,0,0)));
      v.clock.currentTime = noon;
      v.clock.startTime = noon;
      v.clock.stopTime = noon;
      v.clock.multiplier = 0.0;
      v.clock.shouldAnimate = false;
      // Bias toward stable parent tiles vs aggressive deep-zoom refinement.
      try {{ v.scene.globe.maximumScreenSpaceError = 1.5; }} catch (_e) {{}}
      try {{ v.scene.globe.tileCacheSize = 4096; }} catch (_e) {{}}
      try {{ v.scene.globe.preloadAncestors = true; }} catch (_e) {{}}
      try {{ v.scene.globe.preloadSiblings = true; }} catch (_e) {{}}
    }}

    async function setupWorld(v) {{
      while (v.imageryLayers.length > 0) {{
        v.imageryLayers.remove(v.imageryLayers.get(0), true);
      }}
      // Always add a local/offline base so the globe is visible even if
      // remote imagery is blocked or unavailable.
      try {{
        const grid = new Cesium.GridImageryProvider({{
          cells: 12,
          color: Cesium.Color.fromBytes(90, 90, 90, 180),
          glowColor: Cesium.Color.fromBytes(0, 0, 0, 0),
          backgroundColor: Cesium.Color.fromBytes(18, 18, 18, 255),
        }});
        v.imageryLayers.addImageryProvider(grid);
      }} catch (_e) {{}}
      const esri = new Cesium.UrlTemplateImageryProvider({{
        url: "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}",
        maximumLevel: 22
      }});
      if (token && token.length > 0) {{
        try {{
          const esriLayer = v.imageryLayers.addImageryProvider(esri);
          try {{
            esriLayer.maximumTerrainLevel = 17;
          }} catch (_e) {{}}
        }} catch (_e) {{}}
        if (token && token.length > 0) {{
          try {{
            const terrain = await Cesium.createWorldTerrainAsync({{
              requestVertexNormals: true,
              requestWaterMask: true
            }});
            v.terrainProvider = terrain;
          }} catch (_e) {{}}
        }}
      }}
      // Intentionally DO NOT add OSM buildings per requirement.
    }}

    function addBwFilter(v) {{
      const fs = `
        uniform sampler2D colorTexture;
        uniform sampler2D depthTexture;
        uniform bool u_whot;
        in vec2 v_textureCoordinates;
        void main() {{
          vec4 c = texture(colorTexture, v_textureCoordinates);
          float lum = dot(c.rgb, vec3(0.299, 0.587, 0.114));
          // Sky/background uses grayscale luminance too and follows polarity.
          float d = texture(depthTexture, v_textureCoordinates).r;
          if (d >= 0.999999) {{
            float skyMono = clamp(lum, 0.0, 1.0);
            if (!u_whot) {{
              skyMono = 1.0 - skyMono;
            }}
            out_FragColor = vec4(vec3(skyMono), 1.0);
            return;
          }}
          float mono = clamp(lum, 0.0, 1.0);
          if (!u_whot) {{
            mono = 1.0 - mono;
          }}
          out_FragColor = vec4(vec3(mono), 1.0);
        }}
      `;
      const stage = v.scene.postProcessStages.add(new Cesium.PostProcessStage({{
        fragmentShader: fs,
        uniforms: {{
          u_whot: function() {{
            return !!pose.whot;
          }}
        }}
      }}));
      stage.enabled = true;
    }}

    function _unwrapDeg(curr, target) {{
      let c = Number(curr || 0.0);
      let t = Number(target || 0.0);
      while ((t - c) > 180.0) t -= 360.0;
      while ((t - c) < -180.0) t += 360.0;
      return t;
    }}

    function _blend(curr, target, a) {{
      return (Number(curr || 0.0) * (1.0 - a)) + (Number(target || 0.0) * a);
    }}

    function _vecNorm(v) {{
      const x = Number(v[0] || 0.0);
      const y = Number(v[1] || 0.0);
      const z = Number(v[2] || 0.0);
      const n = Math.sqrt((x * x) + (y * y) + (z * z));
      if (!(n > 1e-9)) return [0.0, 0.0, 0.0];
      return [x / n, y / n, z / n];
    }}

    function _vecCross(a, b) {{
      return [
        (Number(a[1] || 0.0) * Number(b[2] || 0.0)) - (Number(a[2] || 0.0) * Number(b[1] || 0.0)),
        (Number(a[2] || 0.0) * Number(b[0] || 0.0)) - (Number(a[0] || 0.0) * Number(b[2] || 0.0)),
        (Number(a[0] || 0.0) * Number(b[1] || 0.0)) - (Number(a[1] || 0.0) * Number(b[0] || 0.0)),
      ];
    }}

    function _vecDot(a, b) {{
      return (
        (Number(a[0] || 0.0) * Number(b[0] || 0.0)) +
        (Number(a[1] || 0.0) * Number(b[1] || 0.0)) +
        (Number(a[2] || 0.0) * Number(b[2] || 0.0))
      );
    }}

    function _vecScale(v, s) {{
      const sv = Number(s || 0.0);
      return [
        Number(v[0] || 0.0) * sv,
        Number(v[1] || 0.0) * sv,
        Number(v[2] || 0.0) * sv,
      ];
    }}

    function _vecAdd(a, b) {{
      return [
        Number(a[0] || 0.0) + Number(b[0] || 0.0),
        Number(a[1] || 0.0) + Number(b[1] || 0.0),
        Number(a[2] || 0.0) + Number(b[2] || 0.0),
      ];
    }}

    function _quatNorm(q) {{
      const w = Number(q.w || 1.0);
      const x = Number(q.x || 0.0);
      const y = Number(q.y || 0.0);
      const z = Number(q.z || 0.0);
      const n = Math.sqrt((w * w) + (x * x) + (y * y) + (z * z));
      if (!(n > 1e-12)) return {{ w: 1.0, x: 0.0, y: 0.0, z: 0.0 }};
      return {{ w: w / n, x: x / n, y: y / n, z: z / n }};
    }}

    function _quatRotateVec(q, v) {{
      // v' = v + w*t + cross(q_vec, t), t = 2*cross(q_vec, v)
      const w = Number(q.w || 1.0);
      const x = Number(q.x || 0.0);
      const y = Number(q.y || 0.0);
      const z = Number(q.z || 0.0);
      const vx = Number(v[0] || 0.0);
      const vy = Number(v[1] || 0.0);
      const vz = Number(v[2] || 0.0);
      const tx = 2.0 * ((y * vz) - (z * vy));
      const ty = 2.0 * ((z * vx) - (x * vz));
      const tz = 2.0 * ((x * vy) - (y * vx));
      return [
        vx + (w * tx) + ((y * tz) - (z * ty)),
        vy + (w * ty) + ((z * tx) - (x * tz)),
        vz + (w * tz) + ((x * ty) - (y * tx)),
      ];
    }}

    function _quatPoseValid(q) {{
      if (!q || typeof q !== "object") return false;
      const w = Number(q.w);
      const x = Number(q.x);
      const y = Number(q.y);
      const z = Number(q.z);
      return Number.isFinite(w) && Number.isFinite(x) && Number.isFinite(y) && Number.isFinite(z);
    }}

    function _vecLen(v) {{
      const x = Number(v[0] || 0.0);
      const y = Number(v[1] || 0.0);
      const z = Number(v[2] || 0.0);
      return Math.sqrt((x * x) + (y * y) + (z * z));
    }}

    function _rotateAroundAxis(v, axisUnit, angRad) {{
      const vv = _vecNorm(v);
      const aa = _vecNorm(axisUnit);
      if (_vecLen(vv) < 1e-8 || _vecLen(aa) < 1e-8) return vv;
      const c = Math.cos(Number(angRad || 0.0));
      const s = Math.sin(Number(angRad || 0.0));
      const term1 = _vecScale(vv, c);
      const term2 = _vecScale(_vecCross(aa, vv), s);
      const term3 = _vecScale(aa, (1.0 - c) * _vecDot(aa, vv));
      return _vecNorm(_vecAdd(_vecAdd(term1, term2), term3));
    }}

    function _clampElDeg(v) {{
      return Math.max(-85.0, Math.min(2.0, Number(v || 0.0)));
    }}

    function _bodyAzElToWorldDir(basis, azDeg, elDeg) {{
      if (!basis || !basis.right || !basis.forward || !basis.up) return null;
      const az = Cesium.Math.toRadians(Number(azDeg || 0.0));
      const el = Cesium.Math.toRadians(_clampElDeg(elDeg));
      const cEl = Math.cos(el);
      const sEl = Math.sin(el);
      const sAz = Math.sin(az);
      const cAz = Math.cos(az);
      const wr = Cesium.Cartesian3.multiplyByScalar(basis.right, sAz * cEl, new Cesium.Cartesian3());
      const wf = Cesium.Cartesian3.multiplyByScalar(basis.forward, cAz * cEl, new Cesium.Cartesian3());
      const wu = Cesium.Cartesian3.multiplyByScalar(basis.up, sEl, new Cesium.Cartesian3());
      const dir = Cesium.Cartesian3.add(wr, wf, new Cesium.Cartesian3());
      Cesium.Cartesian3.add(dir, wu, dir);
      if (Cesium.Cartesian3.magnitudeSquared(dir) <= 1e-14) return null;
      return Cesium.Cartesian3.normalize(dir, dir);
    }}

    function _worldDirToBodyAzEl(basis, worldDir) {{
      if (!basis || !basis.right || !basis.forward || !basis.up || !worldDir) return null;
      const wd = Cesium.Cartesian3.normalize(worldDir, new Cesium.Cartesian3());
      const r = Cesium.Cartesian3.dot(wd, basis.right);
      const f = Cesium.Cartesian3.dot(wd, basis.forward);
      const u = Cesium.Cartesian3.dot(wd, basis.up);
      const az = Cesium.Math.toDegrees(Math.atan2(r, f));
      const el = Cesium.Math.toDegrees(Math.asin(Math.max(-1.0, Math.min(1.0, u))));
      return {{ az: az, el: el }};
    }}

    function _rayToWorldPoint(origin, worldDir) {{
      try {{
        const ray = new Cesium.Ray(origin, worldDir);
        try {{
          const gp = viewer && viewer.scene && viewer.scene.globe ? viewer.scene.globe.pick(ray, viewer.scene) : null;
          if (gp) return gp;
        }} catch (_e) {{}}
        try {{
          const hit = Cesium.IntersectionTests.rayEllipsoid(ray, Cesium.Ellipsoid.WGS84);
          if (hit && Number.isFinite(hit.start)) {{
            return Cesium.Ray.getPoint(ray, Math.max(0.0, Number(hit.start)), new Cesium.Cartesian3());
          }}
        }} catch (_e) {{}}
        return Cesium.Ray.getPoint(ray, 200000.0, new Cesium.Cartesian3());
      }} catch (_e) {{
        return null;
      }}
    }}

    function _orientationFromQuat(destination, quatObj, lookAzDeg, lookElDeg) {{
      if (!destination || !_quatPoseValid(quatObj)) return null;
      const qn = _quatNorm(quatObj);
      // Sim attitude quaternion axes:
      //   +X right (east), +Y forward (north), +Z up (up).
      let fEnu = _vecNorm(_quatRotateVec(qn, [0.0, 1.0, 0.0]));
      let uEnu = _vecNorm(_quatRotateVec(qn, [0.0, 0.0, 1.0]));
      if (_vecLen(fEnu) < 1e-8 || _vecLen(uEnu) < 1e-8) return null;
      let rEnu = _vecNorm(_vecCross(fEnu, uEnu));
      if (_vecLen(rEnu) < 1e-8) return null;

      // Apply TFLIR line-of-sight slew in aircraft body frame.
      const azDeg = Number(lookAzDeg || 0.0);
      const elDeg = _clampElDeg(lookElDeg);
      if (Math.abs(azDeg) > 1e-6) {{
        const azRad = Cesium.Math.toRadians(-azDeg);
        fEnu = _rotateAroundAxis(fEnu, uEnu, azRad);
        rEnu = _rotateAroundAxis(rEnu, uEnu, azRad);
      }}
      if (Math.abs(elDeg) > 1e-6) {{
        const elRad = Cesium.Math.toRadians(elDeg);
        fEnu = _rotateAroundAxis(fEnu, rEnu, elRad);
        uEnu = _rotateAroundAxis(uEnu, rEnu, elRad);
      }}
      fEnu = _vecNorm(fEnu);
      rEnu = _vecNorm(_vecCross(fEnu, uEnu));
      uEnu = _vecNorm(_vecCross(rEnu, fEnu));

      let m3 = null;
      try {{
        const m4 = Cesium.Transforms.eastNorthUpToFixedFrame(destination);
        m3 = Cesium.Matrix4.getMatrix3(m4, new Cesium.Matrix3());
      }} catch (_e) {{
        return null;
      }}
      let dir = Cesium.Matrix3.multiplyByVector(
        m3,
        new Cesium.Cartesian3(fEnu[0], fEnu[1], fEnu[2]),
        new Cesium.Cartesian3()
      );
      let up = Cesium.Matrix3.multiplyByVector(
        m3,
        new Cesium.Cartesian3(uEnu[0], uEnu[1], uEnu[2]),
        new Cesium.Cartesian3()
      );
      if (!Cesium.defined(dir) || !Cesium.defined(up)) return null;
      if (Cesium.Cartesian3.magnitudeSquared(dir) <= 1e-14 || Cesium.Cartesian3.magnitudeSquared(up) <= 1e-14) return null;
      dir = Cesium.Cartesian3.normalize(dir, dir);
      up = Cesium.Cartesian3.normalize(up, up);
      let right = Cesium.Cartesian3.cross(dir, up, new Cesium.Cartesian3());
      if (Cesium.Cartesian3.magnitudeSquared(right) <= 1e-14) return null;
      right = Cesium.Cartesian3.normalize(right, right);
      up = Cesium.Cartesian3.cross(right, dir, up);
      if (Cesium.Cartesian3.magnitudeSquared(up) <= 1e-14) return null;
      up = Cesium.Cartesian3.normalize(up, up);
      return {{ direction: dir, up: up }};
    }}

    function _orientationFromHprBodyLook(destination, headingDeg, pitchDeg, rollDeg, lookAzDeg, lookElDeg) {{
      if (!destination) return null;
      try {{
        const hpr = Cesium.HeadingPitchRoll.fromDegrees(
          Number(headingDeg || 0.0),
          Number(pitchDeg || 0.0),
          Number(rollDeg || 0.0)
        );
        const m4 = Cesium.Transforms.headingPitchRollToFixedFrame(
          destination,
          hpr,
          Cesium.Ellipsoid.WGS84,
          Cesium.Transforms.eastNorthUpToFixedFrame
        );
        const m3 = Cesium.Matrix4.getMatrix3(m4, new Cesium.Matrix3());
        let r = Cesium.Matrix3.multiplyByVector(m3, Cesium.Cartesian3.UNIT_X, new Cesium.Cartesian3());
        let f = Cesium.Matrix3.multiplyByVector(m3, Cesium.Cartesian3.UNIT_Y, new Cesium.Cartesian3());
        let u = Cesium.Matrix3.multiplyByVector(m3, Cesium.Cartesian3.UNIT_Z, new Cesium.Cartesian3());
        if (
          Cesium.Cartesian3.magnitudeSquared(r) <= 1e-14 ||
          Cesium.Cartesian3.magnitudeSquared(f) <= 1e-14 ||
          Cesium.Cartesian3.magnitudeSquared(u) <= 1e-14
        ) {{
          return null;
        }}
        r = Cesium.Cartesian3.normalize(r, r);
        f = Cesium.Cartesian3.normalize(f, f);
        u = Cesium.Cartesian3.normalize(u, u);

        let rA = [r.x, r.y, r.z];
        let fA = [f.x, f.y, f.z];
        let uA = [u.x, u.y, u.z];

        const azDeg = Number(lookAzDeg || 0.0);
        const elDeg = _clampElDeg(lookElDeg);
        if (Math.abs(azDeg) > 1e-6) {{
          const azRad = Cesium.Math.toRadians(-azDeg);
          fA = _rotateAroundAxis(fA, uA, azRad);
          rA = _rotateAroundAxis(rA, uA, azRad);
        }}
        if (Math.abs(elDeg) > 1e-6) {{
          const elRad = Cesium.Math.toRadians(elDeg);
          fA = _rotateAroundAxis(fA, rA, elRad);
          uA = _rotateAroundAxis(uA, rA, elRad);
        }}
        fA = _vecNorm(fA);
        rA = _vecNorm(_vecCross(fA, uA));
        uA = _vecNorm(_vecCross(rA, fA));
        if (_vecLen(fA) < 1e-8 || _vecLen(uA) < 1e-8) return null;

        let dir = new Cesium.Cartesian3(fA[0], fA[1], fA[2]);
        let up = new Cesium.Cartesian3(uA[0], uA[1], uA[2]);
        dir = Cesium.Cartesian3.normalize(dir, dir);
        up = Cesium.Cartesian3.normalize(up, up);
        let right = Cesium.Cartesian3.cross(dir, up, new Cesium.Cartesian3());
        if (Cesium.Cartesian3.magnitudeSquared(right) <= 1e-14) return null;
        right = Cesium.Cartesian3.normalize(right, right);
        up = Cesium.Cartesian3.cross(right, dir, up);
        if (Cesium.Cartesian3.magnitudeSquared(up) <= 1e-14) return null;
        up = Cesium.Cartesian3.normalize(up, up);
        return {{ direction: dir, up: up }};
      }} catch (_e) {{
        return null;
      }}
    }}

    function _levelOrientationToHorizon(destination, orient) {{
      if (!destination || !orient || !orient.direction || !orient.up) return orient;
      try {{
        let dir = Cesium.Cartesian3.normalize(orient.direction, new Cesium.Cartesian3());
        let geoUp = Cesium.Ellipsoid.WGS84.geodeticSurfaceNormal(destination, new Cesium.Cartesian3());
        if (Cesium.Cartesian3.magnitudeSquared(geoUp) <= 1e-14) return orient;
        geoUp = Cesium.Cartesian3.normalize(geoUp, geoUp);
        const proj = Cesium.Cartesian3.multiplyByScalar(
          dir,
          Cesium.Cartesian3.dot(geoUp, dir),
          new Cesium.Cartesian3()
        );
        let up = Cesium.Cartesian3.subtract(geoUp, proj, new Cesium.Cartesian3());
        if (Cesium.Cartesian3.magnitudeSquared(up) <= 1e-10) return orient;
        up = Cesium.Cartesian3.normalize(up, up);
        let right = Cesium.Cartesian3.cross(dir, up, new Cesium.Cartesian3());
        if (Cesium.Cartesian3.magnitudeSquared(right) <= 1e-10) return orient;
        right = Cesium.Cartesian3.normalize(right, right);
        up = Cesium.Cartesian3.cross(right, dir, up);
        if (Cesium.Cartesian3.magnitudeSquared(up) <= 1e-10) return orient;
        up = Cesium.Cartesian3.normalize(up, up);
        return {{ direction: dir, up: up }};
      }} catch (_e) {{
        return orient;
      }}
    }}

    function _basisFromHpr(destination, headingDeg, pitchDeg, rollDeg) {{
      if (!destination) return null;
      try {{
        const hpr = Cesium.HeadingPitchRoll.fromDegrees(
          Number(headingDeg || 0.0),
          Number(pitchDeg || 0.0),
          Number(rollDeg || 0.0)
        );
        const m4 = Cesium.Transforms.headingPitchRollToFixedFrame(
          destination,
          hpr,
          Cesium.Ellipsoid.WGS84,
          Cesium.Transforms.eastNorthUpToFixedFrame
        );
        const m3 = Cesium.Matrix4.getMatrix3(m4, new Cesium.Matrix3());
        let r = Cesium.Matrix3.multiplyByVector(m3, Cesium.Cartesian3.UNIT_X, new Cesium.Cartesian3());
        let f = Cesium.Matrix3.multiplyByVector(m3, Cesium.Cartesian3.UNIT_Y, new Cesium.Cartesian3());
        let u = Cesium.Matrix3.multiplyByVector(m3, Cesium.Cartesian3.UNIT_Z, new Cesium.Cartesian3());
        if (
          Cesium.Cartesian3.magnitudeSquared(r) <= 1e-14 ||
          Cesium.Cartesian3.magnitudeSquared(f) <= 1e-14 ||
          Cesium.Cartesian3.magnitudeSquared(u) <= 1e-14
        ) return null;
        r = Cesium.Cartesian3.normalize(r, r);
        f = Cesium.Cartesian3.normalize(f, f);
        u = Cesium.Cartesian3.normalize(u, u);
        return {{ right: r, forward: f, up: u, modelMatrix: m4 }};
      }} catch (_e) {{
        return null;
      }}
    }}

    function _decodeBase64ToArrayBuffer(b64) {{
      const raw = atob(String(b64 || ""));
      const len = raw.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i += 1) bytes[i] = raw.charCodeAt(i) & 255;
      return bytes.buffer;
    }}

    function _buildStlGeometryFromBinary(buffer) {{
      const dv = new DataView(buffer);
      if (dv.byteLength < 84) return null;
      const triCount = Number(dv.getUint32(80, true) || 0);
      if (!(triCount > 0) || triCount > 2000000) return null;
      if (!(triCount > 0)) return null;
      const needed = 84 + (triCount * 50);
      if (dv.byteLength < needed) return null;

      const pos = new Float64Array(triCount * 9);
      const nrm = new Float32Array(triCount * 9);
      const idx = new Uint32Array(triCount * 3);
      let off = 84;
      let p = 0;
      let i = 0;
      let minX = Number.POSITIVE_INFINITY;
      let minY = Number.POSITIVE_INFINITY;
      let minZ = Number.POSITIVE_INFINITY;
      let maxX = Number.NEGATIVE_INFINITY;
      let maxY = Number.NEGATIVE_INFINITY;
      let maxZ = Number.NEGATIVE_INFINITY;

      for (let t = 0; t < triCount; t += 1) {{
        const nx = Number(dv.getFloat32(off + 0, true));
        const ny = Number(dv.getFloat32(off + 4, true));
        const nz = Number(dv.getFloat32(off + 8, true));
        off += 12;
        for (let v = 0; v < 3; v += 1) {{
          const x = Number(dv.getFloat32(off + 0, true));
          const y = Number(dv.getFloat32(off + 4, true));
          const z = Number(dv.getFloat32(off + 8, true));
          off += 12;
          pos[p + 0] = x;
          pos[p + 1] = y;
          pos[p + 2] = z;
          nrm[p + 0] = nx;
          nrm[p + 1] = ny;
          nrm[p + 2] = nz;
          idx[i] = i;
          p += 3;
          i += 1;
          if (x < minX) minX = x;
          if (y < minY) minY = y;
          if (z < minZ) minZ = z;
          if (x > maxX) maxX = x;
          if (y > maxY) maxY = y;
          if (z > maxZ) maxZ = z;
        }}
        off += 2;
      }}
      const spanX = maxX - minX;
      const spanY = maxY - minY;
      const spanZ = maxZ - minZ;
      const longest = Math.max(spanX, spanY, spanZ, 1e-6);
      const targetLenM = 7.0;
      const scale = targetLenM / longest;
      const cx = (minX + maxX) * 0.5;
      const cy = (minY + maxY) * 0.5;
      const cz = (minZ + maxZ) * 0.5;
      for (let k = 0; k < pos.length; k += 3) {{
        pos[k + 0] = (pos[k + 0] - cx) * scale;
        pos[k + 1] = (pos[k + 1] - cy) * scale;
        pos[k + 2] = (pos[k + 2] - cz) * scale;
      }}
      return new Cesium.Geometry({{
        attributes: {{
          position: new Cesium.GeometryAttribute({{
            componentDatatype: Cesium.ComponentDatatype.DOUBLE,
            componentsPerAttribute: 3,
            values: pos
          }}),
          normal: new Cesium.GeometryAttribute({{
            componentDatatype: Cesium.ComponentDatatype.FLOAT,
            componentsPerAttribute: 3,
            values: nrm
          }})
        }},
        indices: idx,
        primitiveType: Cesium.PrimitiveType.TRIANGLES,
        boundingSphere: Cesium.BoundingSphere.fromVertices(pos),
      }});
    }}

    function _buildStlGeometryFromText(text) {{
      const src = String(text || "");
      if (src.length <= 0) return null;
      const re = /vertex\\s+([-+]?\\d*\\.?\\d+(?:[eE][-+]?\\d+)?)\\s+([-+]?\\d*\\.?\\d+(?:[eE][-+]?\\d+)?)\\s+([-+]?\\d*\\.?\\d+(?:[eE][-+]?\\d+)?)/ig;
      const verts = [];
      let m = null;
      while ((m = re.exec(src)) !== null) {{
        verts.push([Number(m[1] || 0.0), Number(m[2] || 0.0), Number(m[3] || 0.0)]);
      }}
      if (verts.length < 3) return null;
      const triCount = Math.floor(verts.length / 3);
      if (!(triCount > 0) || triCount > 2000000) return null;
      const pos = new Float64Array(triCount * 9);
      const nrm = new Float32Array(triCount * 9);
      const idx = new Uint32Array(triCount * 3);
      let p = 0;
      let i = 0;
      let minX = Number.POSITIVE_INFINITY;
      let minY = Number.POSITIVE_INFINITY;
      let minZ = Number.POSITIVE_INFINITY;
      let maxX = Number.NEGATIVE_INFINITY;
      let maxY = Number.NEGATIVE_INFINITY;
      let maxZ = Number.NEGATIVE_INFINITY;
      for (let t = 0; t < triCount; t += 1) {{
        const a = verts[t * 3 + 0];
        const b = verts[t * 3 + 1];
        const c = verts[t * 3 + 2];
        const abx = b[0] - a[0];
        const aby = b[1] - a[1];
        const abz = b[2] - a[2];
        const acx = c[0] - a[0];
        const acy = c[1] - a[1];
        const acz = c[2] - a[2];
        let nx = (aby * acz) - (abz * acy);
        let ny = (abz * acx) - (abx * acz);
        let nz = (abx * acy) - (aby * acx);
        const nn = Math.sqrt((nx * nx) + (ny * ny) + (nz * nz));
        if (nn > 1e-12) {{
          nx /= nn;
          ny /= nn;
          nz /= nn;
        }} else {{
          nx = 0.0; ny = 0.0; nz = 1.0;
        }}
        const tri = [a, b, c];
        for (let v = 0; v < 3; v += 1) {{
          const x = Number(tri[v][0] || 0.0);
          const y = Number(tri[v][1] || 0.0);
          const z = Number(tri[v][2] || 0.0);
          pos[p + 0] = x;
          pos[p + 1] = y;
          pos[p + 2] = z;
          nrm[p + 0] = nx;
          nrm[p + 1] = ny;
          nrm[p + 2] = nz;
          idx[i] = i;
          p += 3;
          i += 1;
          if (x < minX) minX = x;
          if (y < minY) minY = y;
          if (z < minZ) minZ = z;
          if (x > maxX) maxX = x;
          if (y > maxY) maxY = y;
          if (z > maxZ) maxZ = z;
        }}
      }}
      const spanX = maxX - minX;
      const spanY = maxY - minY;
      const spanZ = maxZ - minZ;
      const longest = Math.max(spanX, spanY, spanZ, 1e-6);
      const targetLenM = 7.0;
      const scale = targetLenM / longest;
      const cx = (minX + maxX) * 0.5;
      const cy = (minY + maxY) * 0.5;
      const cz = (minZ + maxZ) * 0.5;
      for (let k = 0; k < pos.length; k += 3) {{
        pos[k + 0] = (pos[k + 0] - cx) * scale;
        pos[k + 1] = (pos[k + 1] - cy) * scale;
        pos[k + 2] = (pos[k + 2] - cz) * scale;
      }}
      return new Cesium.Geometry({{
        attributes: {{
          position: new Cesium.GeometryAttribute({{
            componentDatatype: Cesium.ComponentDatatype.DOUBLE,
            componentsPerAttribute: 3,
            values: pos
          }}),
          normal: new Cesium.GeometryAttribute({{
            componentDatatype: Cesium.ComponentDatatype.FLOAT,
            componentsPerAttribute: 3,
            values: nrm
          }})
        }},
        indices: idx,
        primitiveType: Cesium.PrimitiveType.TRIANGLES,
        boundingSphere: Cesium.BoundingSphere.fromVertices(pos),
      }});
    }}

    function _ensureAircraftVisuals(v) {{
      if (!v) return;
      if (aircraftPrimitive || aircraftLoadAttempted || !aircraftStlB64 || aircraftStlB64.length <= 0) return;
      aircraftLoadAttempted = true;
      try {{
        const buf = _decodeBase64ToArrayBuffer(aircraftStlB64);
        const bytes = new Uint8Array(buf);
        let geom = null;
        let stlTxt = "";
        try {{
          stlTxt = new TextDecoder("utf-8", {{ fatal: false }}).decode(bytes);
        }} catch (_e) {{
          stlTxt = "";
        }}
        const stlHead = String(stlTxt || "").slice(0, 512).toLowerCase();
        if (stlHead.indexOf("facet") >= 0 && stlHead.indexOf("vertex") >= 0) {{
          geom = _buildStlGeometryFromText(stlTxt);
        }} else {{
          geom = _buildStlGeometryFromBinary(buf);
        }}
        if (!geom) return;
        aircraftPrimitive = v.scene.primitives.add(new Cesium.Primitive({{
          geometryInstances: new Cesium.GeometryInstance({{
            geometry: geom,
            id: "f35_stl_aircraft",
            attributes: {{
              color: Cesium.ColorGeometryInstanceAttribute.fromColor(Cesium.Color.fromBytes(170, 170, 170, 255))
            }}
          }}),
          appearance: new Cesium.PerInstanceColorAppearance({{
            flat: false,
            translucent: false,
            closed: true
          }}),
          asynchronous: false
        }}));
      }} catch (_e) {{
        aircraftPrimitive = null;
      }}
    }}

    const USE_QUAT_ORIENTATION = false;

    function updateCam() {{
      const alphaAng = 0.4;
      // Keep camera hard-locked to ownship center so rotation never orbits/warps.
      smoothPose.lat = Number(pose.lat || smoothPose.lat || 33.535);
      smoothPose.lon = Number(pose.lon || smoothPose.lon || -112.383);
      smoothPose.altitude_ft = Number(pose.altitude_ft || smoothPose.altitude_ft || 0.0);

      const hdgTarget = _unwrapDeg(smoothPose.heading_deg, pose.heading_deg);
      const pitTarget = _unwrapDeg(smoothPose.pitch_deg, pose.pitch_deg);
      const rolTarget = _unwrapDeg(smoothPose.roll_deg, pose.roll_deg);
      const lookAzTarget = _unwrapDeg(smoothPose.look_az_deg, pose.look_az_deg);
      const lookElTarget = _unwrapDeg(smoothPose.look_el_deg, pose.look_el_deg);
      const camFwdTarget = Number(pose.cam_rel_forward_m || 0.0);
      const camRightTarget = Number(pose.cam_rel_right_m || 0.0);
      const camUpTarget = Number(pose.cam_rel_up_m || 0.0);
      const camDefFwdTarget = Number(pose.cam_default_forward_m || 0.0);
      const camDefRightTarget = Number(pose.cam_default_right_m || 2.79);
      const camDefUpTarget = Number(pose.cam_default_up_m || -0.59);
      const camDefCubeTarget = Number(pose.cam_default_cube_size_m || 1.0);
      const camCubeFwdTarget = Number(pose.cam_cube_forward_m || camDefFwdTarget);
      const camCubeRightTarget = Number(pose.cam_cube_right_m || camDefRightTarget);
      const camCubeUpTarget = Number(pose.cam_cube_up_m || camDefUpTarget);
      const zoomTarget = Number(pose.zoom_fov_deg || smoothPose.zoom_fov_deg || 45.0);
      smoothPose.heading_deg = _blend(smoothPose.heading_deg, hdgTarget, alphaAng);
      smoothPose.pitch_deg = _blend(smoothPose.pitch_deg, pitTarget, alphaAng);
      smoothPose.roll_deg = _blend(smoothPose.roll_deg, rolTarget, alphaAng);
      smoothPose.look_az_deg = _blend(smoothPose.look_az_deg, lookAzTarget, 0.35);
      smoothPose.look_el_deg = _blend(smoothPose.look_el_deg, lookElTarget, 0.35);
      smoothPose.cam_rel_forward_m = _blend(Number(smoothPose.cam_rel_forward_m || 0.0), camFwdTarget, 0.55);
      smoothPose.cam_rel_right_m = _blend(Number(smoothPose.cam_rel_right_m || 0.0), camRightTarget, 0.55);
      smoothPose.cam_rel_up_m = _blend(Number(smoothPose.cam_rel_up_m || 0.0), camUpTarget, 0.55);
      smoothPose.cam_default_forward_m = _blend(Number(smoothPose.cam_default_forward_m || 0.0), camDefFwdTarget, 0.45);
      smoothPose.cam_default_right_m = _blend(Number(smoothPose.cam_default_right_m || 2.79), camDefRightTarget, 0.45);
      smoothPose.cam_default_up_m = _blend(Number(smoothPose.cam_default_up_m || -0.59), camDefUpTarget, 0.45);
      smoothPose.cam_default_cube_size_m = _blend(Number(smoothPose.cam_default_cube_size_m || 1.0), camDefCubeTarget, 0.55);
      smoothPose.cam_cube_forward_m = _blend(Number(smoothPose.cam_cube_forward_m || camDefFwdTarget), camCubeFwdTarget, 0.55);
      smoothPose.cam_cube_right_m = _blend(Number(smoothPose.cam_cube_right_m || camDefRightTarget), camCubeRightTarget, 0.55);
      smoothPose.cam_cube_up_m = _blend(Number(smoothPose.cam_cube_up_m || camDefUpTarget), camCubeUpTarget, 0.55);
      smoothPose.zoom_fov_deg = _blend(Number(smoothPose.zoom_fov_deg || 45.0), zoomTarget, 0.25);
      _drawFallback();
      if (!viewer || (typeof Cesium === "undefined")) return;

      const lat = Number(smoothPose.lat || 33.535);
      const lon = Number(smoothPose.lon || -112.383);
      // altitude_ft is MSL from simulator; do not terrain-offset.
      const alt_m = Math.max(2.0, Number(smoothPose.altitude_ft || 0.0) * 0.3048);
      const ownshipPos = Cesium.Cartesian3.fromDegrees(lon, lat, alt_m);
      const camRelFwdM = Number(smoothPose.cam_rel_forward_m || 0.0);
      const camRelRightM = Number(smoothPose.cam_rel_right_m || 0.0);
      const camRelUpM = Number(smoothPose.cam_rel_up_m || 0.0);
      const camBaseForwardM = Number(smoothPose.cam_default_forward_m || 0.0);
      const camBaseRightM = Number(smoothPose.cam_default_right_m || 2.79);
      const camBaseUpM = Number(smoothPose.cam_default_up_m || -0.59);
      const hDegAligned = Number(smoothPose.heading_deg || 0.0) - 90.0;
      const pDeg = Number(smoothPose.pitch_deg || 0.0);
      const rDeg = Number(smoothPose.roll_deg || 0.0);

      const basis = _basisFromHpr(ownshipPos, hDegAligned, pDeg, rDeg);
      let destination = ownshipPos;
      if (basis && basis.forward && basis.right) {{
        const offBaseF = Cesium.Cartesian3.multiplyByScalar(basis.forward, camBaseForwardM, new Cesium.Cartesian3());
        const offBaseR = Cesium.Cartesian3.multiplyByScalar(basis.right, camBaseRightM, new Cesium.Cartesian3());
        const offBaseU = Cesium.Cartesian3.multiplyByScalar(basis.up, camBaseUpM, new Cesium.Cartesian3());
        const offF = Cesium.Cartesian3.multiplyByScalar(basis.forward, camRelFwdM, new Cesium.Cartesian3());
        const offR = Cesium.Cartesian3.multiplyByScalar(basis.right, camRelRightM, new Cesium.Cartesian3());
        const offU = Cesium.Cartesian3.multiplyByScalar(basis.up, camRelUpM, new Cesium.Cartesian3());
        destination = Cesium.Cartesian3.add(ownshipPos, offBaseF, new Cesium.Cartesian3());
        destination = Cesium.Cartesian3.add(destination, offBaseR, destination);
        destination = Cesium.Cartesian3.add(destination, offBaseU, destination);
        destination = Cesium.Cartesian3.add(destination, offF, destination);
        destination = Cesium.Cartesian3.add(destination, offR, destination);
        destination = Cesium.Cartesian3.add(destination, offU, destination);
      }}

      let finalAzDeg = Number(smoothPose.look_az_deg || 90.0);
      let finalElDeg = _clampElDeg(Number(smoothPose.look_el_deg || 0.0));
      const cmdAzNow = Number(pose.look_az_deg || 90.0);
      const cmdElNow = _clampElDeg(Number(pose.look_el_deg || 0.0));
      const slewActive = !!pose.look_slew_active;
      const holdPointEnabled = !!pose.hold_point_enabled;
      const cmdChanged = (!Number.isFinite(lastCmdLookAz)) ||
        (!Number.isFinite(lastCmdLookEl)) ||
        (Math.abs(cmdAzNow - lastCmdLookAz) > 1e-6) ||
        (Math.abs(cmdElNow - lastCmdLookEl) > 1e-6);
      if (cmdChanged) {{
        lastCmdLookAz = cmdAzNow;
        lastCmdLookEl = cmdElNow;
      }}
      if (basis && basis.forward && basis.right && basis.up) {{
        if (slewActive) {{
          // During active slew, do not point-stabilize/follow any prior target.
          lookTargetPoint = null;
        }} else if (!holdPointEnabled) {{
          lookTargetPoint = null;
        }} else if (cmdChanged || !lookTargetPoint) {{
          const cmdDir = _bodyAzElToWorldDir(basis, finalAzDeg, finalElDeg);
          if (cmdDir) {{
            const tgt = _rayToWorldPoint(destination, cmdDir);
            if (tgt) lookTargetPoint = tgt;
          }}
        }} else if (lookTargetPoint) {{
          const toTarget = Cesium.Cartesian3.subtract(lookTargetPoint, destination, new Cesium.Cartesian3());
          if (Cesium.Cartesian3.magnitudeSquared(toTarget) > 1e-6) {{
            const body = _worldDirToBodyAzEl(basis, toTarget);
            if (body && Number.isFinite(body.az) && Number.isFinite(body.el)) {{
              finalAzDeg = _unwrapDeg(finalAzDeg, body.az);
              finalElDeg = _clampElDeg(body.el);
            }}
          }}
        }}
      }}
      smoothPose.look_az_deg = finalAzDeg;
      smoothPose.look_el_deg = finalElDeg;
      try {{
        // Expose resolved TFLIR camera orientation (including hold-point stabilization)
        // so the host can draw a true north arrow.
        const hdg = Number(smoothPose.heading_deg || 0.0);
        const camWorld = (((hdg + (Number(finalAzDeg || 0.0) - 90.0)) % 360.0) + 360.0) % 360.0;
        window.__tflir_cam_heading_world_deg = Number(camWorld);
        window.__tflir_final_look_az_deg = Number(finalAzDeg || 0.0);
      }} catch (_e) {{}}

      const showAircraftModel = !!pose.show_aircraft_model;
      if (showAircraftModel) {{
        _ensureAircraftVisuals(viewer);
        try {{
          if (aircraftPrimitive && basis && basis.modelMatrix) {{
            aircraftPrimitive.modelMatrix = basis.modelMatrix;
          }}
        }} catch (_e) {{}}
      }} else {{
        try {{
          if (aircraftPrimitive && viewer && viewer.scene && viewer.scene.primitives) {{
            viewer.scene.primitives.remove(aircraftPrimitive);
            aircraftPrimitive = null;
          }}
        }} catch (_e) {{}}
      }}
      let usedQuat = false;
      if (USE_QUAT_ORIENTATION) {{
        try {{
          const quatObj = (pose && typeof pose.quat_wxyz === "object") ? pose.quat_wxyz : null;
          let orient = _orientationFromQuat(
            ownshipPos,
            quatObj,
            Number(smoothPose.look_az_deg || 0.0),
            Number(smoothPose.look_el_deg || 0.0),
          );
          if (orient && orient.direction && orient.up) {{
            if (!!pose.level_roll_to_horizon) {{
              orient = _levelOrientationToHorizon(destination, orient);
            }}
            viewer.camera.setView({{
              destination: destination,
              orientation: {{
                direction: orient.direction,
                up: orient.up
              }}
            }});
            usedQuat = true;
          }}
        }} catch (_e) {{
          usedQuat = false;
        }}
      }}
      if (!usedQuat) {{
        // Compose aircraft rotation first, then sensor az/el in aircraft body frame.
        // Rotate aircraft attitude frame 90 deg left to align pitch axis with
        // the true aircraft forward vector used by this TFLIR view.
        const hDeg = hDegAligned;
        const azDeg = Number(finalAzDeg || 0.0);
        const elDeg = Number(finalElDeg || 0.0);
        let orient = _orientationFromHprBodyLook(ownshipPos, hDeg, pDeg, rDeg, azDeg, elDeg);
        if (orient && orient.direction && orient.up) {{
          if (!!pose.level_roll_to_horizon) {{
            orient = _levelOrientationToHorizon(destination, orient);
          }}
          viewer.camera.setView({{
            destination: destination,
            orientation: {{
              direction: orient.direction,
              up: orient.up
            }}
          }});
        }} else {{
          const heading = Cesium.Math.toRadians(hDeg);
          const pitch = Cesium.Math.toRadians(pDeg);
          const roll = Cesium.Math.toRadians(!!pose.level_roll_to_horizon ? 0.0 : rDeg);
          viewer.camera.setView({{
            destination: destination,
            orientation: {{ heading: heading, pitch: pitch, roll: roll }}
          }});
        }}
      }}
      try {{
        const zoomFovDeg = Math.max(0.00001, Math.min(45.0, Number(smoothPose.zoom_fov_deg || 45.0)));
        if (viewer && viewer.camera && viewer.camera.frustum && typeof viewer.camera.frustum.fov === "number") {{
          viewer.camera.frustum.fov = Cesium.Math.toRadians(zoomFovDeg);
        }}
        // Lower near clip for close-in stability; keep far reasonable.
        viewer.camera.frustum.near = 0.05;
        viewer.camera.frustum.far = Math.max(1500000.0, alt_m * 2500.0);
      }} catch (_e) {{}}
      viewer.scene.requestRender();
    }}

    window.__setPose = function(p) {{
      if (p && typeof p === "object") {{
        pose = Object.assign(pose, p);
        if (!poseInitialized) {{
          smoothPose = Object.assign({{}}, pose);
          poseInitialized = true;
        }}
      }}
      if (!!pose.show_aircraft_model) {{
        updateCam();
      }} else {{
        // Keep DAS worker independent from the TFLIR camera path.
        smoothPose.lat = Number(pose.lat || smoothPose.lat || 33.535);
        smoothPose.lon = Number(pose.lon || smoothPose.lon || -112.383);
        smoothPose.altitude_ft = Number(pose.altitude_ft || smoothPose.altitude_ft || 0.0);
        smoothPose.heading_deg = Number(pose.heading_deg || smoothPose.heading_deg || 0.0);
        smoothPose.pitch_deg = Number(pose.pitch_deg || smoothPose.pitch_deg || 0.0);
        smoothPose.roll_deg = Number(pose.roll_deg || smoothPose.roll_deg || 0.0);
        _setCameraForDas();
      }}
      return true;
    }};

    function _captureSetFov(vFovDeg, hFovDeg) {{
      try {{
        if (!viewer || !viewer.camera || !viewer.camera.frustum) return;
        const w = Math.max(2.0, Number(window.innerWidth || 2.0));
        const h = Math.max(2.0, Number(window.innerHeight || 2.0));
        const aspect = Math.max(0.05, w / h);
        const v = Math.max(0.05, Number(vFovDeg || 29.0));
        const hh = Math.max(0.05, Number(hFovDeg || 29.0));
        const vFromH = Cesium.Math.toDegrees(2.0 * Math.atan(Math.tan(Cesium.Math.toRadians(hh) * 0.5) / Math.max(0.05, aspect)));
        let useDeg = v;
        // Cesium frustum.fov is horizontal for wide-aspect and vertical for tall-aspect.
        if (aspect >= 1.0) {{
          useDeg = hh;
        }} else {{
          useDeg = v;
        }}
        if (Number.isFinite(vFromH) && vFromH > 0.01 && aspect < 1.0) {{
          useDeg = vFromH;
        }}
        viewer.camera.frustum.fov = Cesium.Math.toRadians(Math.max(0.01, Math.min(140.0, useDeg)));
      }} catch (_e) {{}}
    }}

    function _setCameraForDas() {{
      if (!viewer || (typeof Cesium === "undefined")) return false;
      const lat = Number(smoothPose.lat || 33.535);
      const lon = Number(smoothPose.lon || -112.383);
      // altitude_ft is MSL from simulator; do not terrain-offset.
      const alt_m = Math.max(2.0, Number(smoothPose.altitude_ft || 0.0) * 0.3048);
      const ownshipPos = Cesium.Cartesian3.fromDegrees(lon, lat, alt_m);
      const hDegAligned = Number(smoothPose.heading_deg || 0.0) - 90.0;
      const pDeg = Number(smoothPose.pitch_deg || 0.0);
      const rDeg = Number(smoothPose.roll_deg || 0.0);
      const basis = _basisFromHpr(ownshipPos, hDegAligned, pDeg, rDeg);
      if (!basis || !basis.forward || !basis.right || !basis.up) return false;

      const offF = Number(pose.das_cam_forward_m || 0.0);
      const offR = Number(pose.das_cam_right_m || 0.0);
      const offU = Number(pose.das_cam_up_m || 0.0);
      let destination = ownshipPos;
      destination = Cesium.Cartesian3.add(destination, Cesium.Cartesian3.multiplyByScalar(basis.forward, offF, new Cesium.Cartesian3()), destination);
      destination = Cesium.Cartesian3.add(destination, Cesium.Cartesian3.multiplyByScalar(basis.right, offR, new Cesium.Cartesian3()), destination);
      destination = Cesium.Cartesian3.add(destination, Cesium.Cartesian3.multiplyByScalar(basis.up, offU, new Cesium.Cartesian3()), destination);

      const dasYaw = Number(pose.das_yaw_deg || 0.0);
      const dasPitch = Number(pose.das_pitch_deg || 0.0);
      const azDeg = 90.0 + dasYaw;
      const elDeg = dasPitch;
      const orient = _orientationFromHprBodyLook(ownshipPos, hDegAligned, pDeg, rDeg, azDeg, elDeg);
      if (orient && orient.direction && orient.up) {{
        viewer.camera.setView({{
          destination: destination,
          orientation: {{
            direction: orient.direction,
            up: orient.up
          }}
        }});
      }} else {{
        return false;
      }}
      const zoomRatio = Math.max(0.1, Number(pose.das_zoom_ratio || 2.9));
      const vfov = Math.max(0.05, Number(pose.das_fov_v_deg || 29.0)) / zoomRatio;
      const hfov = Math.max(0.05, Number(pose.das_fov_h_deg || 29.0)) / zoomRatio;
      _captureSetFov(vfov, hfov);
      try {{
        viewer.camera.frustum.near = 0.05;
        viewer.camera.frustum.far = Math.max(1500000.0, alt_m * 2500.0);
      }} catch (_e) {{}}
      viewer.scene.requestRender();
      return true;
    }}

    window.__captureFrame = function(mode) {{
      try {{
        if (viewer && viewer.scene && viewer.canvas) {{
          if (String(mode || "tflir").toLowerCase() === "das") {{
            if (!_setCameraForDas()) {{
              return "";
            }}
          }} else {{
            updateCam();
          }}
          viewer.scene.requestRender();
          const d = viewer.canvas.toDataURL("image/png");
          if (typeof d === "string" && d.startsWith("data:image/png;base64,")) {{
            lastCaptureSource = "viewer";
            window.__lastCaptureSource = lastCaptureSource;
            return d;
          }}
        }}
      }} catch (_e) {{}}
      try {{
        _drawFallback();
        if (fbCanvas) {{
          lastCaptureSource = "js_fallback";
          window.__lastCaptureSource = lastCaptureSource;
          return fbCanvas.toDataURL("image/png");
        }}
      }} catch (_e) {{}}
      lastCaptureSource = "none";
      window.__lastCaptureSource = lastCaptureSource;
      return "";
    }};

    (async function() {{
      sceneStatus = "loading_cesium";
      window.__sceneStatus = sceneStatus;
      const cesiumOk = await _ensureCesiumLoaded();
      if (!cesiumOk || (typeof Cesium === "undefined")) {{
        sceneStatus = "cesium_missing";
        sceneLastError = "failed_to_load_cesium_js";
        window.__sceneStatus = sceneStatus;
        window.__sceneLastError = sceneLastError;
        return;
      }}
      if (token && token.length > 0) {{
        try {{
          Cesium.Ion.defaultAccessToken = token;
        }} catch (_e) {{}}
      }}
      if (typeof Cesium === "undefined") {{
        sceneStatus = "cesium_missing";
        sceneLastError = "cesium_undefined_after_load";
        window.__sceneStatus = sceneStatus;
        window.__sceneLastError = sceneLastError;
        return;
      }}
      sceneStatus = "viewer_init";
      window.__sceneStatus = sceneStatus;
      viewer = new Cesium.Viewer("c", {{
        terrainProvider: new Cesium.EllipsoidTerrainProvider(),
        animation: false,
        timeline: false,
        geocoder: false,
        homeButton: false,
        sceneModePicker: false,
        baseLayerPicker: false,
        navigationHelpButton: false,
        infoBox: false,
        selectionIndicator: false,
        fullscreenButton: false,
        vrButton: false,
        shouldAnimate: false,
        contextOptions: {{
          webgl: {{
            preserveDrawingBuffer: true,
            // On WSL / software GL paths, Cesium can fail initialization when
            // major performance caveat is detected. Allow fallback so we can
            // still render frames.
            failIfMajorPerformanceCaveat: false
          }}
        }}
      }});
      sceneStatus = "viewer_created";
      window.__sceneStatus = sceneStatus;
      try {{
        if (viewer && viewer.camera && viewer.camera.frustum && typeof viewer.camera.frustum.fov === "number") {{
          // Narrower FOV makes ground scale feel less miniature.
          viewer.camera.frustum.fov = Cesium.Math.toRadians(45.0);
        }}
      }} catch (_e) {{}}
      try {{ viewer.cesiumWidget.creditContainer.style.display = "none"; }} catch (_e) {{}}
      sceneStatus = "world_setup";
      window.__sceneStatus = sceneStatus;
      await setupWorld(viewer);
      applyDay(viewer);
      addBwFilter(viewer);
      sceneStatus = "ready";
      window.__sceneStatus = sceneStatus;
      if (poseInitialized) {{
        if (!!pose.show_aircraft_model) {{
          updateCam();
        }} else {{
          _setCameraForDas();
        }}
      }}
    }})().catch(function(_e) {{
      sceneStatus = "init_error";
      try {{
        sceneLastError = String(_e || "init_error");
      }} catch (_e2) {{
        sceneLastError = "init_error";
      }}
      window.__sceneStatus = sceneStatus;
      window.__sceneLastError = sceneLastError;
    }});
  </script>
</body>
</html>"""


if __name__ == "__main__":
    if "--worker" in sys.argv:
        raise SystemExit(_run_worker())
    print("3DWorld module loaded. This file is used by main/formats and can also run worker with --worker.")
