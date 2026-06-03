from __future__ import annotations

import threading
import time
import sys
from typing import Callable, Dict, Optional, Tuple


class AdsbWorkerRuntime:
    def __init__(
        self,
        *,
        formats_module: object,
        enabled: bool,
        radius_km: int,
        min_interval_s: int,
        adsb_default_radius_km: int,
        adsb_default_min_interval_s: int,
        adsb_mil_min_interval_s: int,
        adsb_geo_refresh_s: int,
        current_ownship_adsb_center_cb: Callable[[], Optional[Tuple[float, float]]],
        safe_float_or_none_cb: Callable[[object], Optional[float]],
        get_general_geo_area_from_ip_cb: Callable[[], Optional[Dict[str, object]]],
        get_adsb_data_cb: Callable[..., object],
        get_adsb_mil_data_cb: Callable[..., object],
        adsb_aircraft_count_cb: Callable[[object], int],
        log_cb: Callable[[str], None] = print,
    ) -> None:
        self._formats = formats_module
        self._current_ownship_adsb_center = current_ownship_adsb_center_cb
        self._safe_float_or_none = safe_float_or_none_cb
        self._get_general_geo_area_from_ip = get_general_geo_area_from_ip_cb
        self._get_adsb_data = get_adsb_data_cb
        self._get_adsb_mil_data = get_adsb_mil_data_cb
        self._adsb_aircraft_count = adsb_aircraft_count_cb
        self._log = log_cb
        self._adsb_default_radius_km = int(adsb_default_radius_km)
        self._adsb_default_min_interval_s = int(adsb_default_min_interval_s)
        self._adsb_mil_min_interval_s = int(adsb_mil_min_interval_s)
        self._adsb_geo_refresh_s = int(adsb_geo_refresh_s)

        self.runtime_lock = threading.Lock()
        self.runtime: Dict[str, object] = {
            "enabled": bool(enabled),
            "geo": None,
            "lat": None,
            "lon": None,
            "manual_position": False,
            "fetch_active": False,
            "show_live_adsb": True,
            "radius_km": int(radius_km),
            "query_radius_km": int(radius_km),
            "min_interval_s": int(min_interval_s),
            "status": "idle",
            "last_error": "",
            "last_update_time": 0.0,
            "aircraft_count": 0,
            "raw": None,
            "mil_raw": None,
            "mil_aircraft_count": 0,
        }
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None

    def publish_runtime(self) -> None:
        with self.runtime_lock:
            snapshot = {
                "enabled": bool(self.runtime.get("enabled", False)),
                "geo": self.runtime.get("geo"),
                "lat": self.runtime.get("lat"),
                "lon": self.runtime.get("lon"),
                "manual_position": bool(self.runtime.get("manual_position", False)),
                "fetch_active": bool(self.runtime.get("fetch_active", False)),
                "show_live_adsb": bool(self.runtime.get("show_live_adsb", True)),
                "radius_km": int(self.runtime.get("radius_km", self._adsb_default_radius_km)),
                "query_radius_km": int(self.runtime.get("query_radius_km", self.runtime.get("radius_km", self._adsb_default_radius_km))),
                "min_interval_s": int(self.runtime.get("min_interval_s", self._adsb_default_min_interval_s)),
                "status": str(self.runtime.get("status", "idle")),
                "last_error": str(self.runtime.get("last_error", "")),
                "last_update_time": float(self.runtime.get("last_update_time", 0.0)),
                "aircraft_count": int(self.runtime.get("aircraft_count", 0)),
                "raw": self.runtime.get("raw"),
                "mil_raw": self.runtime.get("mil_raw"),
                "mil_aircraft_count": int(self.runtime.get("mil_aircraft_count", 0)),
            }
        try:
            existing = getattr(self._formats, "TSD_ADSB_STATE", None)
            if isinstance(existing, dict):
                existing.clear()
                existing.update(snapshot)
            else:
                setattr(self._formats, "TSD_ADSB_STATE", snapshot)
                existing = snapshot

            # Format modules use `from formats import *`, so they may hold a
            # reference to the original dict. Keep those references live instead
            # of replacing the object in only the formats module.
            for module in list(sys.modules.values()):
                state = getattr(module, "TSD_ADSB_STATE", None)
                if isinstance(state, dict) and state is not existing:
                    state.clear()
                    state.update(snapshot)
        except Exception:
            pass

    def _worker_loop(self) -> None:
        geo_refresh_due_s = 0.0
        while not self.stop_event.is_set():
            now_s = time.time()
            with self.runtime_lock:
                enabled = bool(self.runtime.get("enabled", False))
                fetch_active = bool(self.runtime.get("fetch_active", False))
                lat = self.runtime.get("lat")
                lon = self.runtime.get("lon")
                manual_position = bool(self.runtime.get("manual_position", False))
            if not enabled:
                with self.runtime_lock:
                    self.runtime["status"] = "disabled"
                self.publish_runtime()
                self.stop_event.wait(1.0)
                continue
            if not fetch_active:
                publish_hidden = False
                with self.runtime_lock:
                    if str(self.runtime.get("status", "")) != "idle_hidden" or str(self.runtime.get("last_error", "")) != "":
                        publish_hidden = True
                    self.runtime["status"] = "idle_hidden"
                    self.runtime["last_error"] = ""
                if publish_hidden:
                    self.publish_runtime()
                self.stop_event.wait(1.0)
                continue

            ownship_center = self._current_ownship_adsb_center()
            if isinstance(ownship_center, tuple) and len(ownship_center) == 2:
                own_lat = self._safe_float_or_none(ownship_center[0])
                own_lon = self._safe_float_or_none(ownship_center[1])
                if own_lat is not None and own_lon is not None:
                    with self.runtime_lock:
                        self.runtime["lat"] = float(own_lat)
                        self.runtime["lon"] = float(own_lon)
                        geo_raw = self.runtime.get("geo")
                        geo = dict(geo_raw) if isinstance(geo_raw, dict) else {}
                        geo["lat"] = float(own_lat)
                        geo["lon"] = float(own_lon)
                        geo["source"] = "ownship"
                        self.runtime["geo"] = geo
                        self.runtime["status"] = "geo_ok"
                        self.runtime["last_error"] = ""
                    self.publish_runtime()
            elif (not manual_position) and (lat is None or lon is None or now_s >= geo_refresh_due_s):
                geo = self._get_general_geo_area_from_ip()
                geo_refresh_due_s = now_s + float(self._adsb_geo_refresh_s)
                if isinstance(geo, dict):
                    with self.runtime_lock:
                        self.runtime["geo"] = geo
                        self.runtime["lat"] = geo.get("lat")
                        self.runtime["lon"] = geo.get("lon")
                        self.runtime["status"] = "geo_ok"
                        self.runtime["last_error"] = ""
                    area = ", ".join([str(geo.get("city", "")).strip(), str(geo.get("region", "")).strip(), str(geo.get("country", "")).strip()]).strip(", ")
                    self._log(f"ADSB GEO: {area if area != '' else 'resolved'} @ {geo.get('lat')}, {geo.get('lon')} ({geo.get('source', 'ip')})")
                else:
                    with self.runtime_lock:
                        self.runtime["status"] = "geo_unavailable"
                        self.runtime["last_error"] = "IP geolocation failed"
                self.publish_runtime()

            with self.runtime_lock:
                lat_f = self._safe_float_or_none(self.runtime.get("lat"))
                lon_f = self._safe_float_or_none(self.runtime.get("lon"))
                radius_km = int(self.runtime.get("query_radius_km", self.runtime.get("radius_km", self._adsb_default_radius_km)))
                min_interval_s = int(self.runtime.get("min_interval_s", self._adsb_default_min_interval_s))
            if lat_f is not None and lon_f is not None:
                try:
                    prev_fetch_ts = float(getattr(self._get_adsb_data, "_last_request_time", 0.0))
                except Exception:
                    prev_fetch_ts = 0.0
                data = self._get_adsb_data(lat_f, lon_f, radius=max(1, radius_km), min_interval=max(10, min_interval_s))
                try:
                    fetch_ts = float(getattr(self._get_adsb_data, "_last_request_time", 0.0))
                except Exception:
                    fetch_ts = 0.0
                fetched_fresh = fetch_ts > (prev_fetch_ts + 1e-6)
                count = self._adsb_aircraft_count(data)
                with self.runtime_lock:
                    self.runtime["raw"] = data
                    self.runtime["aircraft_count"] = int(count)
                    if fetched_fresh and fetch_ts > 0.0:
                        self.runtime["last_update_time"] = float(fetch_ts)
                    elif float(self.runtime.get("last_update_time", 0.0)) <= 0.0 and data is not None:
                        self.runtime["last_update_time"] = float(time.time())
                    if data is not None:
                        self.runtime["status"] = "ok"
                        self.runtime["last_error"] = ""
                    elif str(self.runtime.get("status", "")) == "":
                        self.runtime["status"] = "no_data"
                self.publish_runtime()

            mil_data = self._get_adsb_mil_data(min_interval=self._adsb_mil_min_interval_s)
            mil_count = self._adsb_aircraft_count(mil_data)
            with self.runtime_lock:
                self.runtime["mil_raw"] = mil_data
                self.runtime["mil_aircraft_count"] = int(mil_count)
            self.publish_runtime()
            self.stop_event.wait(1.0)

    def start_if_enabled(self) -> Optional[threading.Thread]:
        self.publish_runtime()
        with self.runtime_lock:
            enabled = bool(self.runtime.get("enabled", False))
        if not enabled:
            self.thread = None
            return None
        try:
            self.thread = threading.Thread(target=self._worker_loop, daemon=True, name="adsb_worker")
            self.thread.start()
        except Exception as exc:
            self._log(f"ADSB worker failed to start: {exc}")
            self.thread = None
        return self.thread
