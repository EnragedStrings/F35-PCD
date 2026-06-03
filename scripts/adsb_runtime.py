from __future__ import annotations

import json
import math
import os
import time
from typing import Dict, List, Optional, Tuple
from urllib import error as urllib_error
from urllib import request as urllib_request

ADSB_DEFAULT_RADIUS_KM = max(1, int(os.environ.get("ADSB_RADIUS_KM", "100")))
ADSB_DEFAULT_MIN_INTERVAL_S = max(10, int(os.environ.get("ADSB_MIN_INTERVAL_S", "10")))
ADSB_MIL_MIN_INTERVAL_S = max(300, int(os.environ.get("ADSB_MIL_INTERVAL_S", "300")))
ADSB_GEO_REFRESH_S = max(60, int(os.environ.get("ADSB_GEO_REFRESH_S", "3600")))
ADSB_HTTP_TIMEOUT_S = max(1.0, float(os.environ.get("ADSB_HTTP_TIMEOUT_S", "8.0")))

def _http_get_json(url: str, timeout: float = ADSB_HTTP_TIMEOUT_S) -> Optional[Dict[str, object]]:
    req = urllib_request.Request(
        str(url),
        headers={
            "User-Agent": "F35-PCD-Sim/1.0",
            "Accept": "application/json",
        },
    )
    try:
        with urllib_request.urlopen(req, timeout=float(timeout)) as resp:
            payload = resp.read().decode("utf-8", errors="ignore")
        parsed = json.loads(payload)
        if isinstance(parsed, dict):
            return parsed
    except (urllib_error.URLError, urllib_error.HTTPError, TimeoutError, OSError, json.JSONDecodeError):
        return None
    except Exception:
        return None
    return None


def _safe_float_or_none(value: object) -> Optional[float]:
    try:
        out = float(value)
    except Exception:
        return None
    if math.isfinite(out):
        return out
    return None


def get_general_geo_area_from_ip(timeout: float = ADSB_HTTP_TIMEOUT_S) -> Optional[Dict[str, object]]:
    """
    Resolve an approximate user geo area from public IP.

    Returns:
        dict with keys: lat, lon, city, region, country, ip, source
        or None if lookup failed.
    """
    providers: List[Tuple[str, str]] = [
        ("ipapi", "https://ipapi.co/json/"),
        ("ipinfo", "https://ipinfo.io/json"),
        ("ipwhois", "https://ipwho.is/"),
    ]
    for provider, url in providers:
        data = _http_get_json(url, timeout=timeout)
        if not isinstance(data, dict):
            continue
        try:
            if provider == "ipapi":
                if bool(data.get("error", False)):
                    continue
                lat = _safe_float_or_none(data.get("latitude"))
                lon = _safe_float_or_none(data.get("longitude"))
                city = str(data.get("city", "")).strip()
                region = str(data.get("region", "")).strip()
                country = str(data.get("country_name", data.get("country", ""))).strip()
                ip = str(data.get("ip", "")).strip()
            elif provider == "ipinfo":
                loc = str(data.get("loc", "")).strip()
                parts = [p.strip() for p in loc.split(",")]
                if len(parts) != 2:
                    continue
                lat = _safe_float_or_none(parts[0])
                lon = _safe_float_or_none(parts[1])
                city = str(data.get("city", "")).strip()
                region = str(data.get("region", "")).strip()
                country = str(data.get("country", "")).strip()
                ip = str(data.get("ip", "")).strip()
            else:
                if data.get("success") is False:
                    continue
                lat = _safe_float_or_none(data.get("latitude"))
                lon = _safe_float_or_none(data.get("longitude"))
                city = str(data.get("city", "")).strip()
                region = str(data.get("region", "")).strip()
                country = str(data.get("country", "")).strip()
                ip = str(data.get("ip", "")).strip()
            if lat is None or lon is None:
                continue
            return {
                "lat": float(lat),
                "lon": float(lon),
                "city": city,
                "region": region,
                "country": country,
                "ip": ip,
                "source": provider,
            }
        except Exception:
            continue
    return None


def get_adsb_data(lat: float, lon: float, radius: int = 100, min_interval: int = 10):
    """
    Query ADSB.lol around a point with built-in per-process rate limiting.
    If called too soon, returns the last successful cached response.
    """
    if not hasattr(get_adsb_data, "_last_request_time"):
        get_adsb_data._last_request_time = 0.0
    if not hasattr(get_adsb_data, "_last_data"):
        get_adsb_data._last_data = None
    if not hasattr(get_adsb_data, "_last_error_log_time"):
        get_adsb_data._last_error_log_time = 0.0

    now = time.time()
    min_interval_s = max(10, int(min_interval))
    if now - float(get_adsb_data._last_request_time) < float(min_interval_s):
        return get_adsb_data._last_data

    try:
        lat_f = float(lat)
        lon_f = float(lon)
        radius_i = max(1, int(radius))
    except Exception:
        return get_adsb_data._last_data

    url = f"https://api.adsb.lol/v2/point/{lat_f}/{lon_f}/{radius_i}"
    data = _http_get_json(url, timeout=10.0)
    if isinstance(data, dict):
        get_adsb_data._last_request_time = now
        get_adsb_data._last_data = data
        return data
    if (now - float(get_adsb_data._last_error_log_time)) >= 30.0:
        print("ADSB warning: ADSB.lol point request/parse failed (using last cached data)")
        get_adsb_data._last_error_log_time = now
    return get_adsb_data._last_data


def get_adsb_mil_data(min_interval: int = ADSB_MIL_MIN_INTERVAL_S):
    """
    Query ADSB.lol military feed with per-process rate limiting.
    If called too soon, returns the last successful cached response.
    """
    if not hasattr(get_adsb_mil_data, "_last_request_time"):
        get_adsb_mil_data._last_request_time = 0.0
    if not hasattr(get_adsb_mil_data, "_last_data"):
        get_adsb_mil_data._last_data = None
    if not hasattr(get_adsb_mil_data, "_last_error_log_time"):
        get_adsb_mil_data._last_error_log_time = 0.0

    now = time.time()
    min_interval_s = max(1, int(min_interval))
    if now - float(get_adsb_mil_data._last_request_time) < float(min_interval_s):
        return get_adsb_mil_data._last_data

    data = _http_get_json("https://api.adsb.lol/v2/mil", timeout=10.0)
    if isinstance(data, dict):
        get_adsb_mil_data._last_request_time = now
        get_adsb_mil_data._last_data = data
        return data
    if (now - float(get_adsb_mil_data._last_error_log_time)) >= 30.0:
        print("ADSB warning: ADSB.lol /v2/mil request/parse failed (using last cached data)")
        get_adsb_mil_data._last_error_log_time = now
    return get_adsb_mil_data._last_data


def _adsb_aircraft_count(payload: object) -> int:
    if not isinstance(payload, dict):
        return 0
    ac = payload.get("ac")
    if isinstance(ac, list):
        return len(ac)
    nested = payload.get("aircraft")
    if isinstance(nested, list):
        return len(nested)
    return 0


