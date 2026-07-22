import base64
import csv
import importlib
import math
import random
import re
import json
import io
import pickle
import time
import threading
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from pathlib import Path
from collections import deque
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple
import sys

import pygame
from app_paths import resource_path, writable_path
from format_defs.hrcs_catalog import HRC_ALERT_DEFS, hrc_text
from button_types import ButtonState, ButtonType, activate_button, render_button
from format_bootstrap import (
    DEFAULT_FORMAT_NAMES,
    DEFAULT_STATUS_FORMATS,
    bootstrap_default_formats,
)
try:
    import numpy as np  # type: ignore
except Exception:
    np = None  # type: ignore
try:
    from PIL import Image  # type: ignore
    Image.MAX_IMAGE_PIXELS = None
except Exception:
    Image = None  # type: ignore

# Keep DPI aligned with main layout (20in logical width at 1920 px).
DPI = 1920 // 20
GRID_CELL_W = int(1 * DPI)
GRID_CELL_H = int((7 / 8) * DPI)
DISPLAY_OSB_H = int(0.875 * DPI)
SIDE_OSB_Y_SHIFT = int(0.25 * DPI)
OSB_PADDING = 10
HAZARD_BORDER_THICKNESS = 7
HAZARD_STRIPE_LINE_WIDTH = 5
HAZARD_STRIPE_SPACING = 12
STATUS_MENU_BOX_SIZE_IN = 0.75
STATUS_MENU_GRID_CELLS = 5

_THREEDWORLD_MODULE: Optional[object] = None
_THREEDWORLD_TRIED_IMPORT = False
_DASWORLD_MODULE: Optional[object] = None
_DASWORLD_TRIED_IMPORT = False


def _get_3dworld_module() -> Optional[object]:
    global _THREEDWORLD_MODULE, _THREEDWORLD_TRIED_IMPORT
    if _THREEDWORLD_MODULE is not None:
        return _THREEDWORLD_MODULE
    if _THREEDWORLD_TRIED_IMPORT:
        return None
    _THREEDWORLD_TRIED_IMPORT = True
    try:
        _THREEDWORLD_MODULE = importlib.import_module("3DWorld")
    except Exception as exc:
        _THREEDWORLD_MODULE = None
        try:
            print(f"[3DWORLD][IMPORT] failed in formats: {exc}")
        except Exception:
            pass
    return _THREEDWORLD_MODULE


def _get_dasworld_module() -> Optional[object]:
    global _DASWORLD_MODULE, _DASWORLD_TRIED_IMPORT
    if _DASWORLD_MODULE is not None:
        return _DASWORLD_MODULE
    if _DASWORLD_TRIED_IMPORT:
        return None
    _DASWORLD_TRIED_IMPORT = True
    try:
        _DASWORLD_MODULE = importlib.import_module("DASWorld")
    except Exception as exc:
        _DASWORLD_MODULE = None
        try:
            print(f"[DASWORLD][IMPORT] failed in formats: {exc}")
        except Exception:
            pass
    return _DASWORLD_MODULE


def _active_render_portal_index() -> Optional[int]:
    try:
        raw = globals().get("_ACTIVE_RENDER_PORTAL_INDEX")
        if raw is None:
            return None
        idx = int(raw)
        if 0 <= idx <= 3:
            return idx
    except Exception:
        return None
    return None


def _anchored_5col_grid_x(rect: pygame.Rect, grid_w: int) -> int:
    # Keep 5-column popup grids on their originating 5x7 side when a portal is
    # rendered as a 10x7 owner rect.
    width = int(rect.width)
    if width <= int(grid_w):
        return int(rect.x)
    if width >= int((10 * DPI) - 1):
        idx = _active_render_portal_index()
        if idx is not None:
            return int(rect.x) if (idx % 2 == 0) else int(rect.right - grid_w)
    return int(rect.x + max(0, (width - int(grid_w)) // 2))

PHM_SYSTEM_SUBSYSTEMS: Dict[str, List[str]] = {
    "AIR_FRM": ["DATA", "SENSOR", "STRCTR"],
    "EPS": ["BAT_28", "BAT_270", "BUS_28", "BUS_AC", "BUS_270", "EDU_1", "EDU_2", "ESGPMG", "ICC"],
    "FCS": ["AIRDAT", "EHAS", "LEFAS", "EU", "STICK", "TACNAV", "THROTL", "ICU", "RPA"],
    "FPS": ["DET_DB", "DET_EB", "DET_ENG", "DET_IBL", "DET_IPP", "SUP_DB", "SUP_IPP"],
    "FUEL": ["DEFUEL", "DUMP", "FEED", "FPRESS", "INERT", "MEASUR", "REFUEL", "THRMAL", "TRNSFR"],
    "GEAR": ["BRAKES", "GEAR_L", "GEAR_N", "GEAR_R", "NWS", "HOOK"],
    "HYD": ["HYD_A", "HYD_B", "HYD_C", "HDOORS", "WBDD"],
    "LIF_SUP": ["BOS", "CAS", "EJSEAT", "OBOGS", "SCP"],
    "PROP": ["AFTBNR", "ANTICE", "ENGOIL", "FADEC", "PERF"],
    "PTMS": ["AFTAVS", "BAY", "BLEED", "CABIN", "COLDLL", "FANS", "FWAVS", "HOTLL", "IPPELC", "RAM", "ICEDET"],
    "VSP": ["RIO", "VMC", "VSN", "CSMU"],
    "COM_NAV": ["CNI", "GPS", "INS", "PSCTS"],
    "DAS": ["DAS"],
    "DISPL": ["HMDS", "PCD_L", "PCD_R", "SFD", "MSIM"],
    "EOTS": ["EOTS"],
    "EW": ["ESM", "CM"],
    "GUN": ["GUN"],
    "LIGHTG": ["LTGFWD", "LTGWNG"],
    "MSP": ["AMD", "ICP", "PMD", "FC NET", "1394NET"],
    "RADAR": ["RADAR"],
    "SMS": ["CMDCTL", "FRIU"],
    "SRES": ["SRES_1", "SRES_2", "SRES_3", "SRES_4", "SRES_5", "SRES_6", "SRES_7", "SRES_8", "SRES_9", "SRES_10", "SRES_11"],
    "RIUS": ["RIU"],
}

IFF_STATE: Dict[str, object] = {
    "iff_on": False,
    "mode4_sf_on": False,
    "mode_options": ["OFF", "STBY", "MAN", "AUTO"],
    "mode_idx": 0,
    "mode_menu_open": False,
    "a1_menu_open": False,
    "a2_menu_open": False,
    "e7_subpage_open": False,
    "mode1": "73",
    "mode2": "0000",
    "mode3a": "1200",
    "mode4": "0000",
    "mode_s_addr": "37777777",
    "mode_s_acid": "KNIGHT1",
    "mode_s_addr_format_options": ["OCTAL", "HEX"],
    "mode_s_addr_format_idx": 0,
    "m5_pin": "37777",
    "natlorg": "37777",
    "mode_s_perm_address": "12345677",
    "selected_field": None,
    "mode1_input": "",
    "mode2_input": "",
    "mode3a_input": "",
    "mode4_input": "",
    "mode_s_addr_input": "",
    "mode_s_acid_input": "",
    "input_cursor": 0,
    "input_comp_key": None,
    "input_comp_idx": -1,
    "input_comp_cycle": 0,
    "flash_until": {},
    "now_ms": 0,
    "on_since_ms": 0,
    "mode4_on_since_ms": 0,
    "ident_until_ms": 0,
    "advisory_text": "",
    "advisory_sev": "advisory",
    "mode1_enabled": True,
    "mode2_enabled": True,
    "mode3_enabled": True,
    "modec_enabled": True,
    "mode45_enabled": False,
    "crypto_options": ["HOLD", "NORM", "ZERO"],
    "crypto_idx": 1,
    "antenna_options": ["NORM"],
    "antenna_idx": 0,
    "mode_s_options": ["ELS", "EHS"],
    "mode_s_idx": 0,
    "mode5_level_options": ["L2", "L1"],
    "mode5_level_idx": 0,
    "mode5_squit_on": False,
    "test_on": False,
    "mode_s_extend_squit_on": False,
    "mode3ac_on": True,
    "mode5_enabled": False,
    "mode_s_enabled": False,
    "emergency_on": False,
    "emergency_cover_closed": True,
    "emcon_flag": False,
    "degrade_flag": False,
    "degrade_mode": "",
}

ALTITUDE_STATE: Dict[str, object] = {
    "baro_inhg": "29.87",
    "hpa": "1013",
    "line1_value": "29.87",
    "line1_source": "E1",
    "cab": "0000",
    "gcas_options": ["OFF", "AUTO", "LW-LVL", "STBY"],
    "gcas_idx": 1,
    "alow": "0000",
    "selected_field": None,
    "e1_input": "",
    "e2_input": "",
    "e4_input": "",
    "gcas_menu_open": False,
    "flash_until": {},
    "now_ms": 0,
}

NAV_STATE: Dict[str, object] = {
    "a1_value": "XXX.XXX",
    "b1_value": "110.500",
    "c1_value": "001",
    "c2_mode": 0,  # 0=X, 1=Y
    "c3_options": ["RECV", "T/R", "A-A RCV", "A-A T/R"],
    "c3_idx": 0,
    "c3_menu_open": False,
    "de1_value": "000",
    "de1_r_idx": 1,
    "de2_n": "0.000000",
    "de2_e": "0.000000",
    "de2_edit_line": "N",
    "d7_mode": 1,  # 0=MAN, 1=AUTO
    "submenu": None,  # None | "WAYPT" | "REFPT"
    "selected_field": None,
    "a1_input": "",
    "b1_input": "",
    "c1_input": "",
    "de1_input": "",
    "de2_n_input": "",
    "de2_e_input": "",
    "ref_e1_value": "000",
    "ref_e1_input": "",
    "ref_de5_value": "0",
    "ref_de6_value": "0",
    "ref_de7_value": "0",
    "ref_de5_input": "",
    "ref_de6_input": "",
    "ref_de7_input": "",
    "de1_ils_active": False,
    "de1_ils_runway": "",
    "ils_tacan_airport": "",
    "ils_tacan_entries": [],
    "ils_tacan_index": 1,
    "ils_tacan_signature": "",
    "flash_until": {},
    "now_ms": 0,
}

AUTOPILOT_STATE: Dict[str, object] = {
    "att_hold": False,
    "hdg_sel": False,
    "hdg_value": "000",
    "hdg_input": "",
    "alt_hold": False,
    "alt_sel": False,
    "alt_value": "00000",
    "alt_input": "",
    "speed_hold": False,
    "speed_mode_options": ["IAS", "FLCH", "SPEED"],
    "speed_mode_idx": 0,
    "speed_menu_open": False,
    "speed_sel": False,
    "speed_value": "000",
    "speed_input": "",
    "rte_hold": False,
    "att_target_pitch_deg": None,
    "alt_hold_target_ft": None,
    "speed_hold_target_kts": None,
    "selected_field": None,
    "flash_until": {},
    "now_ms": 0,
}

FCS_STATE: Dict[str, object] = {
    "nose_door": False,
    "ap": False,
    "alt_pa": False,
    "integ_fcs_fadec": False,
    "trim_reset": False,
    "gear_reset": False,
    # Per-side flight-control position values (signed; rendered as abs + sign arrow).
    "l_lef": 0.0,
    "r_lef": 0.0,
    "l_aileron": 0.0,
    "r_aileron": 0.0,
    "l_rudder": 0.0,
    "r_rudder": 0.0,
    "l_elevator": 0.0,
    "r_elevator": 0.0,
    "top_cyan_x_in": 0.0,
    "top_cyan_y_in": 0.0,
    "bottom_cyan_x_in": 0.0,
    "rudder_trim_in": 0.0,
    "_ctrl_last_ms": 0.0,
}

PANEL_BUTTON_STATES: Dict[str, Dict[str, object]] = {}
DISPLAY_CURSOR_LOGICAL: Tuple[int, int] = (0, 0)


def set_display_cursor_logical(pos: Tuple[int, int]) -> None:
    global DISPLAY_CURSOR_LOGICAL
    try:
        DISPLAY_CURSOR_LOGICAL = (int(pos[0]), int(pos[1]))
    except Exception:
        DISPLAY_CURSOR_LOGICAL = (0, 0)

SMS_STATE: Dict[str, int] = {
    "chaff": 10,
    "flare": 10,
    "excm_armed": 0,
    "excm_program": 0,
    "last_cm_program": 0,
    "last_cm_dispense_ms": 0,
    "doors_open": 0,
    "mrm_count": 0,
    "srm_count": 0,
    "as_count": 0,
    "gun_count": 182,
    "live_train_idx": 0,
    "store_loads": {},
    "training_store_loads": {},
    "stores_thought_initialized": 0,
    "training_stores_thought_initialized": 1,
    "cntl_submenu_open": 0,
    "cntl_inv_prog_open": 0,
    "cntl_inv_load_open": 0,
    "cntl_inv_load_type_menu_open": 0,
    "cntl_inv_load_type_page": 0,
    "cntl_inv_load_selected_field": "",
    "cntl_inv_load_type_value": "",
    "cntl_inv_load_rack_value": "",
    "cntl_inv_load_wpn_value": "",
    "cntl_inv_load_fuze_value": "",
    "cntl_inv_load_fuze_mode_value": "",
    "cntl_inv_load_fuze_mode_open": 0,
    "cntl_inv_load_qty_value": 0,
    "cntl_inv_load_qty_max": 0,
    "cntl_inv_load_qty_input": "",
    "cntl_inv_load_request": {},
    "cntl_live_train_idx": 0,
    "excm_arm_confirm_pending": 0,
    "cntl_inv_selected_stations": [],
    "cntl_inv_clear_request": [],
}

ASR1_STATE: Dict[str, object] = {
    "radar_status": "OK",
    "radar_fail": False,
    "spnt_tgt": False,
    "nts_designated": False,
    "nts_kind": "",
    "tflir_slew_control": False,
}

TWD_STATE: Dict[str, object] = {
    "heading_deg": 35.0,
    "rwr_ss_idx": 2,
    "rwr_ss_popup_open": False,
    "_popup_anchor_portal_idx": 0,
}

WIND_STATE: Dict[str, object] = {
    "initialized": False,
    "base_utc_ts": 0.0,
    "anchor_monotonic": 0.0,
    "tz_offset_hours": 0.0,
    "display_mode": "LOCAL",  # LOCAL | ZULU
    "selected_field": "",     # TZ | DATE | TIME
    "entry_buffer": "",
    "stopwatch_running": False,
    "stopwatch_elapsed_s": 0.0,
    "stopwatch_anchor_mono": 0.0,
    "flash_until": {},
}


def _wind_system_tz_offset_hours() -> float:
    try:
        now_local = datetime.now().astimezone()
        off = now_local.utcoffset()
        if off is None:
            return 0.0
        return float(off.total_seconds()) / 3600.0
    except Exception:
        return 0.0


def _wind_init_state() -> None:
    if bool(WIND_STATE.get("initialized", False)):
        return
    now_utc = datetime.now(timezone.utc).timestamp()
    now_mono = time.monotonic()
    WIND_STATE["base_utc_ts"] = float(now_utc)
    WIND_STATE["anchor_monotonic"] = float(now_mono)
    WIND_STATE["tz_offset_hours"] = float(_wind_system_tz_offset_hours())
    WIND_STATE["display_mode"] = "LOCAL"
    WIND_STATE["selected_field"] = ""
    WIND_STATE["entry_buffer"] = ""
    WIND_STATE["stopwatch_running"] = False
    WIND_STATE["stopwatch_elapsed_s"] = 0.0
    WIND_STATE["stopwatch_anchor_mono"] = float(now_mono)
    WIND_STATE["flash_until"] = {}
    WIND_STATE["initialized"] = True


def _wind_now_utc_ts() -> float:
    _wind_init_state()
    base = float(WIND_STATE.get("base_utc_ts", 0.0))
    anchor = float(WIND_STATE.get("anchor_monotonic", 0.0))
    return base + max(0.0, float(time.monotonic()) - anchor)


def _wind_set_utc_ts(new_utc_ts: float) -> None:
    _wind_init_state()
    WIND_STATE["base_utc_ts"] = float(new_utc_ts)
    WIND_STATE["anchor_monotonic"] = float(time.monotonic())


def _wind_sync_ota_time() -> None:
    _wind_set_utc_ts(datetime.now(timezone.utc).timestamp())


def _wind_local_and_zulu_datetimes() -> Tuple[datetime, datetime]:
    _wind_init_state()
    utc_dt = datetime.fromtimestamp(_wind_now_utc_ts(), timezone.utc)
    tz_off = float(WIND_STATE.get("tz_offset_hours", 0.0))
    local_dt = utc_dt + timedelta(hours=tz_off)
    return local_dt, utc_dt


def _wind_status_button_times() -> Tuple[str, str]:
    local_dt, zulu_dt = _wind_local_and_zulu_datetimes()
    return local_dt.strftime("%H:%M:%S"), zulu_dt.strftime("%H:%M:%S Z")


def _wind_stopwatch_elapsed_s() -> float:
    _wind_init_state()
    elapsed = max(0.0, float(WIND_STATE.get("stopwatch_elapsed_s", 0.0)))
    if bool(WIND_STATE.get("stopwatch_running", False)):
        anchor = float(WIND_STATE.get("stopwatch_anchor_mono", time.monotonic()))
        elapsed += max(0.0, float(time.monotonic()) - anchor)
    return elapsed


def _wind_stopwatch_is_visible() -> bool:
    _wind_init_state()
    if bool(WIND_STATE.get("stopwatch_running", False)):
        return True
    return _wind_stopwatch_elapsed_s() > 0.0


def _wind_stopwatch_status_text() -> str:
    total = int(max(0.0, _wind_stopwatch_elapsed_s()))
    hh = total // 3600
    mm = (total % 3600) // 60
    ss = total % 60
    if hh > 0:
        return f"{hh:02d}:{mm:02d}:{ss:02d}"
    if mm > 0:
        return f":{mm:02d}:{ss:02d}"
    return f":{ss:02d}"


def _wind_display_mode_label() -> str:
    _wind_init_state()
    mode = str(WIND_STATE.get("display_mode", "LOCAL")).upper().strip()
    return "ZULU" if mode == "ZULU" else "LOCAL"

def _new_tsd_state() -> Dict[str, object]:
    return {
        "view_idx": 0,  # 0=HSD, 1=VSD
        "vsd_side_view": False,  # False=FWD, True=SIDE
        "vsd_l3_pending_toggle_due_ms": 0,
        "emc_idx": 3,   # EMC4 default
        "range_nm": 15.0,
        "kbd_pan_x_px": 0.0,
        "kbd_pan_y_px": 0.0,
        "kbd_zoom_scale": 1.0,
        "map_on": False,
        "blob_on": False,
        "mk_on": False,
        "atk_on": False,
        "atk_value": 360,
        "atk_selected": False,
        "atk_input": "",
        "hsd_secondary_cursor_norm": None,
        "hsd_secondary_track_id": None,
        "hsd_secondary_track_active": False,
        "hsd_secondary_fusion_id": "",
        "hsd_secondary_confidence": 0.0,
        "hsd_contact_fusion_ids": {},
        "hsd_secondary_track_data": {},
        "hsd_secondary_last_printed_id": "",
        "hsd_secondary_lock_pending": False,
        "dclt_menu_open": False,
        "dclt_cat_menu_open": False,
        "dclt_submenu": "",
        "dclt_data_selected": "",
        "dclt_data_input": "",
        "dclt_data_dirty": False,
        "dclt_data_error": "",
        "dclt_defaults_version": 2,
        "_popup_anchor_portal_idx": 0,
        "dclt_aa_on": True,
        "dclt_as_on": True,
        "dclt_nav_on": True,
        "dclt_rgn1_on": True,
        "dclt_rgn2_on": True,
        "dclt_rgn3_on": True,
        "dclt_max_air": 16,
        "dclt_max_sur": 32,
        "dclt_max_eob": 16,
        "dclt_ears_on": False,
        "dclt_unrng_on": True,
        "dclt_route_idx": 1,
        "dclt_prop_route_idx": 0,
        "dclt_lar_on": False,
        "dclt_mem_on": False,
        "dclt_show_unknown": True,
        "dclt_show_friendly": True,
        "dclt_show_enemy": True,
        "dclt_show_hdg": True,
        "dclt_show_rng_marks": True,
        "dclt_show_fsn_id": True,
        "dclt_cat_enabled": {f"{p}{n}": True for p in ("A", "B") for n in range(1, 7)},
        "_debug_print_ms": {},
        "_debug_last_values": {},
    }


TSD_STATES_BY_NAME: Dict[str, Dict[str, object]] = {
    "TSD1": _new_tsd_state(),
    "TSD2": _new_tsd_state(),
    "TSD3": _new_tsd_state(),
}
# Backward-compatible aliases for legacy hyphenated names.
TSD_STATES_BY_NAME["TSD-1"] = TSD_STATES_BY_NAME["TSD1"]
TSD_STATES_BY_NAME["TSD-2"] = TSD_STATES_BY_NAME["TSD2"]
TSD_STATES_BY_NAME["TSD-3"] = TSD_STATES_BY_NAME["TSD3"]
# Runtime ADS-B/geo snapshot published by main.py (shared read-only display state).
TSD_ADSB_STATE: Dict[str, object] = {
    "enabled": False,
    "geo": None,
    "lat": None,
    "lon": None,
    "show_live_adsb": True,
    "radius_km": 100,
    "min_interval_s": 10,
    "status": "idle",
    "last_error": "",
    "last_update_time": 0.0,
    "aircraft_count": 0,
    "raw": None,
    "mil_raw": None,
    "mil_aircraft_count": 0,
}
TSD_LINK16_CONTACTS: List[Dict[str, object]] = []
TSD_SIM_CONTACTS: List[Dict[str, object]] = []
TSD_GLOBAL_CONTACT_FUSION_IDS: Dict[str, str] = {}
TSD_TOI_STATE: Dict[str, object] = {
    "active": False,
    "tsd_name": "",
    "lat": None,
    "lon": None,
    "screen_pos": None,
    "set_at_ms": 0,
}
TFLIR3D_STATE: Dict[str, object] = {
    "look_az_deg": 90.0,
    "look_el_deg": 0.0,
    "norm_look_az_deg": 90.0,
    "norm_look_el_deg": 0.0,
    "zoom_fov_deg": 45.0,
    "cam_rel_forward_m": 0.0,
    "cam_rel_right_m": 0.0,
    "cam_rel_up_m": 0.0,
    "cam_default_forward_m": 0.0,
    "cam_default_right_m": 2.79,
    "cam_default_up_m": -0.59,
    "cam_default_cube_size_m": 1.0,
    "cam_cube_forward_m": 0.0,
    "cam_cube_right_m": 2.79,
    "cam_cube_up_m": -0.59,
    "cam_move_speed_mps": 35.0,
    "cube_move_speed_mps": 10.0,
    "look_slew_active": False,
    "hold_point_enabled": True,
    "whot": True,
    "bhot": False,
}
DAS3D_STATE: Dict[str, object] = {
    "camera_keys": ["DAS-BA", "DAS-BF", "DAS-L", "DAS-R", "DAS-TA", "DAS-TF"],
    "camera_index": 0,
    "active_camera_key": "DAS-BA",
    # Positions and directions are aircraft-body-relative and come from DAS calibration.
    "camera_offsets_m": {
        "DAS-BA": {"forward": 4.25, "right": 0.00, "up": -2.75},
        "DAS-BF": {"forward": 5.25, "right": 0.00, "up": -2.75},
        "DAS-L": {"forward": 11.00, "right": -1.05, "up": -1.50},
        "DAS-R": {"forward": 11.00, "right": 1.05, "up": -1.50},
        "DAS-TA": {"forward": 3.20, "right": 0.00, "up": 0.95},
        "DAS-TF": {"forward": 11.45, "right": 0.00, "up": -0.30},
    },
    "camera_rot_deg": {
        "DAS-BA": {"yaw": 180.0, "pitch": -15.0},
        "DAS-BF": {"yaw": 0.0, "pitch": -15.0},
        "DAS-L": {"yaw": -75.0, "pitch": -15.0},
        "DAS-R": {"yaw": 75.0, "pitch": -15.0},
        "DAS-TA": {"yaw": 180.0, "pitch": 10.0},
        "DAS-TF": {"yaw": 0.0, "pitch": -5.0},
    },
    "zoom_ratio": 2.9,
    "fov_v_deg": 29.0,
    "fov_h_deg": 29.0,
    "whot": True,
}
# Backward-compatible alias; bound per-instance at runtime.
TSD1_STATE: Dict[str, object] = TSD_STATES_BY_NAME["TSD1"]


def _get_fcs_gear_rect_render_state() -> Dict[str, object]:
    """
    Shared staged visibility/color behavior for the three filled FCS gear
    reference rectangles used in both the FCS format and status bar FCS button.
    """
    green = (0, 255, 0)
    yellow = (255, 255, 0)
    state: Dict[str, object] = {
        "top_visible": True,
        "bottom_visible": True,
        "top_color": green,
        "bottom_color": green,
        "top_hazard": False,
        "bottom_hazard": False,
    }

    panel = PANEL_BUTTON_STATES if isinstance(PANEL_BUTTON_STATES, dict) else {}
    console_left = panel.get("CONSOLE LEFT", {})
    if not isinstance(console_left, dict):
        return state

    mode = str(console_left.get("GEAR", "DOWN_OFF")).upper()
    try:
        due_ms = int(console_left.get("GEAR_TRANSITION_DUE_MS", 0))
    except Exception:
        due_ms = 0
    try:
        start_ms = int(console_left.get("GEAR_TRANSITION_START_MS", 0))
    except Exception:
        start_ms = 0
    try:
        transition_ms = int(console_left.get("GEAR_TRANSITION_DURATION_MS", 0))
    except Exception:
        transition_ms = 0
    direction = str(console_left.get("GEAR_TRANSITION_DIR", "")).upper()
    if direction not in {"UP", "DOWN"}:
        if mode.startswith("UP"):
            direction = "UP"
        elif mode.startswith("DOWN"):
            direction = "DOWN"

    try:
        now_ms = int(pygame.time.get_ticks())
    except Exception:
        now_ms = 0

    in_transition = bool(mode.endswith("_ON") and due_ms > now_ms and start_ms > 0 and direction in {"UP", "DOWN"})
    if not in_transition:
        # Steady-state behavior only after transition is complete.
        if mode.startswith("UP"):
            state["top_visible"] = False
            state["bottom_visible"] = False
        else:
            state["top_visible"] = True
            state["bottom_visible"] = True
        return state

    elapsed_ms = max(0, now_ms - start_ms)
    if transition_ms <= 0 and due_ms > start_ms:
        transition_ms = int(due_ms - start_ms)
    transition_ms = max(2000, transition_ms)
    stage_ms = max(1000, int(round(float(transition_ms) / 2.0)))

    if direction == "UP":
        # Raising order: nose (top) first, then mains (bottom).
        # 0-2s: both yellow (moving together at start cue).
        # 2-4s: top hidden (nose up), bottom yellow (mains still moving).
        # 4s+:  bottom hidden (up).
        if elapsed_ms < stage_ms:
            state["top_visible"] = True
            state["bottom_visible"] = True
            state["top_color"] = yellow
            state["bottom_color"] = yellow
            state["top_hazard"] = True
            state["bottom_hazard"] = True
        elif elapsed_ms < (stage_ms * 2):
            state["top_visible"] = False
            state["bottom_visible"] = True
            state["bottom_color"] = yellow
            state["bottom_hazard"] = True
        else:
            state["top_visible"] = False
            state["bottom_visible"] = False
    else:
        # Lowering order: mains (bottom) first, then nose (top).
        # 0-2s: both yellow (transition start), then
        # 2-4s: bottom green, top yellow. 4s+: top green.
        state["top_visible"] = True
        state["bottom_visible"] = True
        if elapsed_ms < stage_ms:
            state["top_color"] = yellow
            state["bottom_color"] = yellow
            state["top_hazard"] = True
            state["bottom_hazard"] = True
        elif elapsed_ms < (stage_ms * 2):
            state["top_color"] = yellow
            state["bottom_color"] = green
            state["top_hazard"] = True
        else:
            state["top_color"] = green
            state["bottom_color"] = green

    return state

def _norm_phm_token(value: str) -> str:
    return re.sub(r"[\s_]+", "_", str(value).upper().strip())


_PHM_SUBSYSTEMS_BY_SYSTEM_NORM: Dict[str, Dict[str, str]] = {}
_PHM_SUBSYSTEM_KEY_TO_CANONICAL: Dict[str, str] = {}
_PHM_SUBSYSTEM_KEY_TO_SYSTEM: Dict[str, str] = {}
for _sys_name, _subs in PHM_SYSTEM_SUBSYSTEMS.items():
    _sys_key = _norm_phm_token(_sys_name)
    _lut: Dict[str, str] = {}
    for _sub in _subs:
        _sub_key = _norm_phm_token(_sub)
        _lut[_sub_key] = str(_sub)
        _PHM_SUBSYSTEM_KEY_TO_CANONICAL[_sub_key] = str(_sub)
        _PHM_SUBSYSTEM_KEY_TO_SYSTEM[_sub_key] = str(_sys_name)
    _PHM_SUBSYSTEMS_BY_SYSTEM_NORM[_sys_key] = _lut

_PHM_SYSTEM_ALIASES: Dict[str, str] = {
    "CNI": "COM_NAV",
}
_PHM_SUBSYSTEM_ALIASES: Dict[str, str] = {
    "IPPELEC": "IPPELC",
}
_ICAWS_HRC_SINGLE_RE = re.compile(r"^\d+$")
_ICAWS_HRC_RANGE_RE = re.compile(r"^(?P<a>\d+)\s*-\s*(?P<b>\d+)$")


def _icaw_alert_key(text: str, severity: str) -> str:
    return f"{str(text).strip().upper()}|{str(severity).strip().lower()}"


def _resolve_phm_system_key(raw_system: str) -> str:
    sys_key = _norm_phm_token(raw_system)
    if sys_key == "":
        return ""
    sys_key = _PHM_SYSTEM_ALIASES.get(sys_key, sys_key)
    if sys_key in PHM_SYSTEM_SUBSYSTEMS:
        return sys_key
    if sys_key in _PHM_SUBSYSTEM_KEY_TO_SYSTEM:
        return _PHM_SUBSYSTEM_KEY_TO_SYSTEM[sys_key]
    return ""


def _resolve_phm_subsystem_key(raw_subsystem: str, system_hint: str = "") -> str:
    raw_key = _norm_phm_token(raw_subsystem)
    if raw_key == "":
        return ""
    sub_key = _PHM_SUBSYSTEM_ALIASES.get(raw_key, raw_key)
    sys_hint_key = _resolve_phm_system_key(system_hint)
    if sys_hint_key != "":
        lut = _PHM_SUBSYSTEMS_BY_SYSTEM_NORM.get(sys_hint_key, {})
        if sub_key in lut:
            return str(lut[sub_key])
    canonical = _PHM_SUBSYSTEM_KEY_TO_CANONICAL.get(sub_key, "")
    if canonical != "":
        return str(canonical)
    return ""


def _parse_icaw_target_spec(system_raw: str, subsystem_raw: str) -> Tuple[str, str, List[str]]:
    system_key = _resolve_phm_system_key(system_raw)
    sub_spec = str(subsystem_raw).strip()
    if sub_spec == "":
        if system_key != "":
            return system_key, "system", [system_key]
        return "", "none", []

    mode = "single"
    body = sub_spec
    if re.match(r"^\s*RANDOM\s*:", body, flags=re.IGNORECASE):
        mode = "random"
        body = re.split(r":", body, maxsplit=1)[1]
    elif re.match(r"^\s*ALL\s*:", body, flags=re.IGNORECASE):
        mode = "all"
        body = re.split(r":", body, maxsplit=1)[1]
    elif re.search(r"\(\s*RANDOM\s*\)", body, flags=re.IGNORECASE):
        mode = "random"
        body = re.sub(r"\(\s*RANDOM\s*\)", "", body, flags=re.IGNORECASE)

    parts = [p.strip() for p in re.split(r"\s*,\s*|\s+OR\s+", body, flags=re.IGNORECASE) if p.strip() != ""]
    resolved_subs: List[str] = []
    for part in parts:
        sub = _resolve_phm_subsystem_key(part, system_key)
        if sub != "" and sub not in resolved_subs:
            resolved_subs.append(sub)
    if len(resolved_subs) <= 0:
        sys_from_sub = _resolve_phm_system_key(sub_spec)
        if system_key == "" and sys_from_sub != "":
            system_key = sys_from_sub
        if system_key != "":
            return system_key, "system", [system_key]
        return "", "none", []
    if system_key == "":
        inferred = _PHM_SUBSYSTEM_KEY_TO_SYSTEM.get(_norm_phm_token(resolved_subs[0]), "")
        if inferred != "":
            system_key = inferred
    if mode == "single" and len(resolved_subs) > 1:
        mode = "all"
    return system_key, mode, resolved_subs


def _parse_icaw_hrc_rules(detail_lines: List[str]) -> List[Dict[str, object]]:
    if any("NO HRC" in str(line).upper() for line in detail_lines):
        return []
    rules: List[Dict[str, object]] = []
    for raw_line in detail_lines:
        for segment in [seg.strip() for seg in str(raw_line).split(",") if seg.strip() != ""]:
            m_range = _ICAWS_HRC_RANGE_RE.match(segment)
            if m_range is not None:
                a = str(m_range.group("a"))
                b = str(m_range.group("b"))
                if len(a) < 7 or len(b) < 7:
                    continue
                a_i = int(a)
                b_i = int(b)
                lo = min(a_i, b_i)
                hi = max(a_i, b_i)
                rules.append({"kind": "range", "start": lo, "end": hi, "width": max(len(a), len(b))})
                continue
            if _ICAWS_HRC_SINGLE_RE.match(segment):
                if len(segment) < 7:
                    continue
                rules.append({"kind": "single", "value": str(segment)})
    return rules


def _choose_random_icaw_hrc(rules: List[Dict[str, object]]) -> str:
    if len(rules) <= 0:
        return ""
    weighted: List[Tuple[Dict[str, object], int]] = []
    total = 0
    for rule in rules:
        if str(rule.get("kind", "")) == "range":
            try:
                lo = int(rule.get("start", 0))
                hi = int(rule.get("end", 0))
            except Exception:
                continue
            span = max(1, hi - lo + 1)
            total += span
            weighted.append((rule, span))
        elif str(rule.get("kind", "")) == "single":
            total += 1
            weighted.append((rule, 1))
    if total <= 0 or len(weighted) <= 0:
        return ""
    pick = random.randint(1, total)
    acc = 0
    for rule, weight in weighted:
        acc += weight
        if pick > acc:
            continue
        if str(rule.get("kind", "")) == "single":
            return str(rule.get("value", ""))
        try:
            lo = int(rule.get("start", 0))
            hi = int(rule.get("end", 0))
            width = int(rule.get("width", max(len(str(lo)), len(str(hi)))))
        except Exception:
            return ""
        value = random.randint(lo, hi)
        return str(value).zfill(max(1, width))
    return ""


def _load_icaws_catalog_from_hrcs() -> Tuple[Dict[str, Dict[str, object]], List[str], List[str], List[str], Dict[str, str]]:
    catalog: Dict[str, Dict[str, object]] = {}
    warnings: List[str] = []
    cautions: List[str] = []
    advisories: List[str] = []
    name_default_severity: Dict[str, str] = {}
    warnings_seen: set = set()
    cautions_seen: set = set()
    advisories_seen: set = set()

    if len(HRC_ALERT_DEFS) <= 0:
        return catalog, warnings, cautions, advisories, name_default_severity

    def _finalize_entry(entry: Dict[str, object]) -> None:
        name = str(entry.get("name", "")).strip()
        if name == "":
            return
        severities = entry.get("severities", [])
        if not isinstance(severities, list) or len(severities) <= 0:
            severities = ["advisory"]
        system_key = str(entry.get("system", "")).strip()
        sub_spec = str(entry.get("subsystem", "")).strip()
        detail_lines = entry.get("detail_lines", [])
        if not isinstance(detail_lines, list):
            detail_lines = []
        target_system, target_mode, target_keys = _parse_icaw_target_spec(system_key, sub_spec)
        hrc_rules = _parse_icaw_hrc_rules([str(x) for x in detail_lines])

        for sev in severities:
            sev_key = str(sev).strip().lower()
            if sev_key not in {"warning", "caution", "advisory"}:
                continue
            full_key = _icaw_alert_key(name, sev_key)
            catalog[full_key] = {
                "name": name,
                "severity": sev_key,
                "system": target_system,
                "target_mode": target_mode,
                "target_keys": list(target_keys),
                "hrc_rules": list(hrc_rules),
            }
            name_up = str(name).strip().upper()
            if name_up not in name_default_severity:
                name_default_severity[name_up] = sev_key
            if sev_key == "warning":
                if name not in warnings_seen:
                    warnings_seen.add(name)
                    warnings.append(name)
            elif sev_key == "caution":
                if name not in cautions_seen:
                    cautions_seen.add(name)
                    cautions.append(name)
            else:
                if name not in advisories_seen:
                    advisories_seen.add(name)
                    advisories.append(name)

    for entry_raw in HRC_ALERT_DEFS:
        if not isinstance(entry_raw, dict):
            continue
        _finalize_entry(entry_raw)
    return catalog, warnings, cautions, advisories, name_default_severity


ICAWS_ALERT_CATALOG, ICAWS_WARNING_ALERTS, ICAWS_CAUTION_ALERTS, ICAWS_ADVISORY_ALERTS, ICAWS_ALERT_DEFAULT_SEVERITY = _load_icaws_catalog_from_hrcs()


def get_hrcs_text() -> str:
    return str(hrc_text())
ICAWS_ALERT_CANONICAL_NAME: Dict[str, str] = {}
for _catalog_entry in ICAWS_ALERT_CATALOG.values():
    _name = str(_catalog_entry.get("name", "")).strip()
    if _name == "":
        continue
    ICAWS_ALERT_CANONICAL_NAME[str(_name).upper()] = _name

# Active ICAWS list format:
# [{"text": "BINGO", "severity": "caution"}, ...]
ICAWS_STATE: Dict[str, object] = {
    "active": [],
    "ack_pending": False,
    "unacked_cw": [],
    "test_active_until_ms": 0,
    "hrc_bindings": {},
    "hrc_applied": {},
}


def _icaw_catalog_entry(text: str, severity: str) -> Optional[Dict[str, object]]:
    key = _icaw_alert_key(text, severity)
    entry = ICAWS_ALERT_CATALOG.get(key)
    if isinstance(entry, dict):
        return entry
    name = str(text).strip().upper()
    if name == "":
        return None
    default_sev = str(ICAWS_ALERT_DEFAULT_SEVERITY.get(name, "")).lower()
    if default_sev in {"warning", "caution", "advisory"}:
        fallback = ICAWS_ALERT_CATALOG.get(_icaw_alert_key(name, default_sev))
        if isinstance(fallback, dict):
            return fallback
    return None


def _icaw_normalize_alert(text: str, severity: str) -> Optional[Tuple[str, str]]:
    raw_name = str(text).strip()
    if raw_name == "":
        return None
    sev = str(severity).strip().lower()
    if sev not in {"warning", "caution", "advisory"}:
        sev = "advisory"
    entry = _icaw_catalog_entry(raw_name, sev)
    if not isinstance(entry, dict):
        return None
    name = str(entry.get("name", raw_name)).strip()
    sev_out = str(entry.get("severity", sev)).strip().lower()
    if name == "" or sev_out not in {"warning", "caution", "advisory"}:
        return None
    return (name, sev_out)


def _icaw_add_alert(alerts: List[Tuple[str, str]], name: str, severity: str) -> bool:
    normalized = _icaw_normalize_alert(name, severity)
    if normalized is None:
        return False
    if normalized not in alerts:
        alerts.append(normalized)
    return True


def _icaw_set_alert(alerts: List[Tuple[str, str]], name: str, severity: str) -> bool:
    normalized = _icaw_normalize_alert(name, severity)
    if normalized is None:
        return False
    target_name = normalized[0]
    alerts[:] = [a for a in alerts if a[0] != target_name]
    alerts.append(normalized)
    return True


def _icaw_set_alert_runtime(alerts: List[Tuple[str, str]], name: str, severity: str) -> bool:
    """
    Runtime variant of _icaw_set_alert that allows severity overrides even when
    the catalog only defines a different default severity for the alert text.
    """
    raw_name = str(name).strip()
    if raw_name == "":
        return False
    sev = str(severity).strip().lower()
    if sev not in {"warning", "caution", "advisory"}:
        sev = "advisory"

    canon = str(ICAWS_ALERT_CANONICAL_NAME.get(raw_name.upper(), raw_name)).strip()
    if canon == "":
        return False

    alerts[:] = [a for a in alerts if str(a[0]) != canon]
    alerts.append((canon, sev))
    return True


def _icaw_has_text(alerts: List[Tuple[str, str]], name: str) -> bool:
    return any(txt == str(name) for txt, _ in alerts)


def _icaw_phm_status_state() -> Dict[str, object]:
    panel = PANEL_BUTTON_STATES if isinstance(PANEL_BUTTON_STATES, dict) else {}
    existing = panel.get("PHM STATUS", None)
    if not isinstance(existing, dict):
        raw = {}
        panel["PHM STATUS"] = raw
    else:
        raw = existing
    if not isinstance(raw.get("hrc_events"), dict):
        raw["hrc_events"] = {}
    if not isinstance(raw.get("fna_events"), dict):
        raw["fna_events"] = {}
    if not isinstance(raw.get("status_overrides"), dict):
        raw["status_overrides"] = {}
    return raw


def _icaw_recompute_phm_status_overrides() -> None:
    state = _icaw_phm_status_state()
    hrc_map = state.get("hrc_events", {})
    fna_map = state.get("fna_events", {})
    overrides = state.get("status_overrides", {})
    if not isinstance(hrc_map, dict) or not isinstance(fna_map, dict) or not isinstance(overrides, dict):
        return

    systems: List[str] = list(PHM_SYSTEM_SUBSYSTEMS.keys())
    for key in list(overrides.keys()):
        sys_key = _resolve_phm_system_key(str(key))
        if sys_key != "" and sys_key not in systems:
            systems.append(sys_key)

    for system in systems:
        event_keys: List[str] = [system] + list(PHM_SYSTEM_SUBSYSTEMS.get(system, []))
        has_fna = False
        has_hrc = False
        for event_key in event_keys:
            f_vals = fna_map.get(event_key, [])
            if isinstance(f_vals, list) and any(str(x).strip() != "" for x in f_vals):
                has_fna = True
                break
        if not has_fna:
            for event_key in event_keys:
                h_vals = hrc_map.get(event_key, [])
                if isinstance(h_vals, list) and any(str(x).strip() != "" for x in h_vals):
                    has_hrc = True
                    break
        if has_fna:
            overrides[system] = "OT"
        elif has_hrc:
            overrides[system] = "HR"
        else:
            overrides.pop(system, None)


def _icaw_sync_hrc_bindings(alerts: List[Tuple[str, str]]) -> None:
    state = _icaw_phm_status_state()
    hrc_map = state.get("hrc_events", {})
    if not isinstance(hrc_map, dict):
        return

    prior_bindings = ICAWS_STATE.get("hrc_bindings", {})
    if not isinstance(prior_bindings, dict):
        prior_bindings = {}
    prior_applied = ICAWS_STATE.get("hrc_applied", {})
    if not isinstance(prior_applied, dict):
        prior_applied = {}

    # Remove previously applied ICAWS HRC entries before rebuilding active bindings.
    for applied in prior_applied.values():
        if not isinstance(applied, list):
            continue
        for row in applied:
            if not isinstance(row, (list, tuple)) or len(row) < 2:
                continue
            target_key = str(row[0]).strip()
            hrc_text = str(row[1]).strip()
            if target_key == "" or hrc_text == "":
                continue
            vals = hrc_map.get(target_key, [])
            if not isinstance(vals, list):
                continue
            norm = hrc_text.upper()
            new_vals = [str(x) for x in vals if str(x).strip() != "" and str(x).strip().upper() != norm]
            if len(new_vals) > 0:
                hrc_map[target_key] = new_vals
            else:
                hrc_map.pop(target_key, None)

    hidden_raw = ICAWS_STATE.get("_hidden_binding_alerts", [])
    hidden_alerts: List[Tuple[str, str]] = []
    if isinstance(hidden_raw, list):
        for item in hidden_raw:
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue
            norm = _icaw_normalize_alert(str(item[0]), str(item[1]))
            if norm is None:
                continue
            hidden_alerts.append(norm)

    new_bindings: Dict[str, Dict[str, object]] = {}
    all_binding_alerts = list(alerts) + [a for a in hidden_alerts if a not in alerts]
    for text, sev in all_binding_alerts:
        # SMS GROUND SAFE should only bind HRCs when presented as a caution.
        if str(text).strip().upper() == "SMS GROUND SAFE" and str(sev).strip().lower() != "caution":
            continue
        key = _icaw_alert_key(text, sev)
        entry = ICAWS_ALERT_CATALOG.get(key)
        if not isinstance(entry, dict):
            continue
        rules = entry.get("hrc_rules", [])
        if not isinstance(rules, list) or len(rules) <= 0:
            continue

        old = prior_bindings.get(key, {})
        if not isinstance(old, dict):
            old = {}
        old_hrc = str(old.get("hrc", "")).strip()
        old_targets_raw = old.get("targets", [])
        old_targets = [str(x) for x in old_targets_raw] if isinstance(old_targets_raw, list) else []
        if old_hrc != "":
            new_bindings[key] = {"hrc": old_hrc, "targets": old_targets}
            continue

        hrc_value = _choose_random_icaw_hrc(rules)
        if hrc_value == "":
            continue
        raw_targets = entry.get("target_keys", [])
        target_mode = str(entry.get("target_mode", "none")).lower()
        targets = [str(x) for x in raw_targets] if isinstance(raw_targets, list) else []
        if target_mode == "random" and len(targets) > 0:
            targets = [str(random.choice(targets))]
        elif target_mode in {"single", "system"} and len(targets) > 0:
            targets = [targets[0]]
        elif target_mode == "none":
            targets = []
        else:
            # "all" keeps all targets.
            targets = list(dict.fromkeys([t for t in targets if str(t).strip() != ""]))
        new_bindings[key] = {"hrc": hrc_value, "targets": targets}

    new_applied: Dict[str, List[Tuple[str, str]]] = {}
    for key, binding in new_bindings.items():
        if not isinstance(binding, dict):
            continue
        hrc_value = str(binding.get("hrc", "")).strip()
        targets_raw = binding.get("targets", [])
        targets = [str(x).strip() for x in targets_raw] if isinstance(targets_raw, list) else []
        if hrc_value == "":
            continue
        applied_rows: List[Tuple[str, str]] = []
        for target in targets:
            if target == "":
                continue
            vals = hrc_map.get(target, [])
            if not isinstance(vals, list):
                vals = []
            if hrc_value not in vals:
                vals.append(hrc_value)
            vals = [str(x) for x in vals if str(x).strip() != ""]
            if len(vals) > 0:
                hrc_map[target] = vals
            else:
                hrc_map.pop(target, None)
            applied_rows.append((target, hrc_value))
        new_applied[key] = applied_rows

    ICAWS_STATE["hrc_bindings"] = new_bindings
    ICAWS_STATE["hrc_applied"] = new_applied
    _icaw_recompute_phm_status_overrides()


def get_current_icaws_alerts() -> List[Tuple[str, str]]:
    active_alerts_raw = ICAWS_STATE.get("active", [])
    alerts: List[Tuple[str, str]] = []
    sms_ground_safe_active = False
    wpn_doors_not_closed = False
    if isinstance(active_alerts_raw, list):
        for item in active_alerts_raw:
            if isinstance(item, dict):
                text = str(item.get("text", "")).strip()
                sev = str(item.get("severity", "advisory")).strip().lower()
            else:
                text = str(item).strip()
                sev = "advisory"
            normalized = _icaw_normalize_alert(text, sev)
            if normalized is None:
                continue
            if normalized not in alerts:
                alerts.append(normalized)

    # Momentary ICAWS TEST injection window (set by ICAWS T3 hold handling).
    try:
        now_ms = int(pygame.time.get_ticks())
    except Exception:
        now_ms = 0
    try:
        test_until_ms = int(ICAWS_STATE.get("test_active_until_ms", 0))
    except Exception:
        test_until_ms = 0
    if test_until_ms > 0 and now_ms <= test_until_ms:
        for sev in ("warning", "caution", "advisory"):
            _icaw_add_alert(alerts, "TEST", sev)

    # Auto ICAWS condition: Fuel L2 DUMP ON => FUEL DUMP OPEN.
    try:
        if bool(FuelFormat._shared_hazard_on.get("L2", False)):
            _icaw_set_alert(alerts, "FUEL DUMP OPEN", "caution")
    except Exception:
        pass

    # Auto fuel ICAWS conditions.
    try:
        shared_qty = getattr(FuelFormat, "_shared_fuel_qty", None)
        if isinstance(shared_qty, dict) and len(shared_qty) > 0:
            total_lbs = float(sum(max(0.0, float(v)) for v in shared_qty.values()))
        else:
            total_lbs = float(getattr(FuelFormat, "_shared_total_lbs", 0.0))
        joker_lbs = max(0.0, float(FuelFormat._shared_data_values.get("R2", 0.0)) * 1000.0)
        bingo_lbs = max(0.0, float(FuelFormat._shared_data_values.get("R3", 0.0)) * 1000.0)
        refuel_doors_open = bool(getattr(FuelFormat, "_shared_refuel_t2_on", False)) or bool(FuelFormat._shared_hazard_on.get("R6", False))
        lt_state = str(SMS_STATE.get("lt_state", "CLOSE")).upper()
        rt_state = str(SMS_STATE.get("rt_state", "CLOSE")).upper()
        wpn_doors_not_closed = bool(lt_state != "CLOSE" or rt_state != "CLOSE")

        if bingo_lbs > 0.0 and total_lbs < bingo_lbs:
            _icaw_set_alert(alerts, "BINGO", "advisory")
        if joker_lbs > 0.0 and total_lbs < joker_lbs:
            _icaw_set_alert(alerts, "JOKER", "caution")
        if refuel_doors_open:
            _icaw_set_alert(alerts, "REFUEL DOOR", "caution")
    except Exception:
        pass

    # Auto panel/runtime related ICAWS conditions.
    try:
        panel = PANEL_BUTTON_STATES if isinstance(PANEL_BUTTON_STATES, dict) else {}
        power = panel.get("POWER PANEL", {})
        throttle = panel.get("THROTTLE", {})
        console_left = panel.get("CONSOLE LEFT", {})
        aircraft = panel.get("AIRCRAFT", {})
        if isinstance(power, dict) and isinstance(throttle, dict):
            bat_on = bool(power.get("BAT_ACTIVE", str(power.get("BAT", "OFF")).upper() == "ON"))
            ipp_on = bool(power.get("IPP_ON", False))
            engine_mode = str(throttle.get("ENGINE", "OFF")).upper()
            engine_on = engine_mode != "OFF"
            icc1_on = str(power.get("ICC1", "OFF")).upper() == "ON"
            icc2_on = str(power.get("ICC2", "OFF")).upper() == "ON"
            icc3_on = str(power.get("ICC3", "OFF")).upper() == "ON"
            try:
                thrust_pct = float(getattr(EngineFormat, "_shared_gauge_values", {}).get("THRUST", 0.0))
            except Exception:
                thrust_pct = 0.0
            if isinstance(aircraft, dict):
                try:
                    airspeed_kts = float(aircraft.get("AIRSPEED_KTS", 0.0))
                except Exception:
                    airspeed_kts = 0.0
                try:
                    total_speed_kts = float(aircraft.get("TOTAL_SPEED_KTS", airspeed_kts))
                except Exception:
                    total_speed_kts = airspeed_kts
                try:
                    altitude_ft = float(aircraft.get("ALTITUDE_FT", 0.0))
                except Exception:
                    altitude_ft = 0.0
                try:
                    vertical_speed_fpm = float(aircraft.get("VERTICAL_SPEED_FPM", 0.0))
                except Exception:
                    vertical_speed_fpm = 0.0
            else:
                if thrust_pct <= 15.0:
                    airspeed_kts = 0.0
                elif thrust_pct >= 150.0:
                    airspeed_kts = 710.0
                else:
                    airspeed_kts = ((thrust_pct - 15.0) / 135.0) * 710.0
                total_speed_kts = airspeed_kts
                altitude_ft = 0.0
                vertical_speed_fpm = 0.0
            gear_mode = str(console_left.get("GEAR", "DOWN_OFF")).upper() if isinstance(console_left, dict) else "DOWN_OFF"
            parking_brake_mode = str(console_left.get("PARKING_BRAKE", "ON")).upper() if isinstance(console_left, dict) else "ON"
            gear_handle_up = gear_mode.startswith("UP")
            gear_handle_down = gear_mode.startswith("DOWN")
            on_ground = altitude_ft <= 0.0
            in_flight = not bool(on_ground)
            descent_rate_fpm = max(0.0, -vertical_speed_fpm)
            auto_runtime = ICAWS_STATE.get("_auto_runtime", {})
            if not isinstance(auto_runtime, dict):
                auto_runtime = {}
                ICAWS_STATE["_auto_runtime"] = auto_runtime
            try:
                prev_on_ground = bool(auto_runtime.get("prev_on_ground", on_ground))
            except Exception:
                prev_on_ground = bool(on_ground)
            try:
                prev_descent_rate_fpm = max(0.0, float(auto_runtime.get("prev_descent_rate_fpm", descent_rate_fpm)))
            except Exception:
                prev_descent_rate_fpm = float(descent_rate_fpm)
            try:
                prev_airspeed_kts = max(0.0, float(auto_runtime.get("prev_airspeed_kts", airspeed_kts)))
            except Exception:
                prev_airspeed_kts = max(0.0, float(airspeed_kts))
            touchdown_this_frame = bool((not prev_on_ground) and on_ground)
            try:
                engine_spool = float(throttle.get("ENGINE_SPOOL", 0.0))
            except Exception:
                engine_spool = 0.0
            engine_spool_mode = str(throttle.get("ENGINE_SPOOL_MODE", "OFF")).upper()

            if bat_on and ipp_on and engine_on:
                if (not icc1_on) and (not icc2_on):
                    _icaw_set_alert(alerts, "GEN FAIL 1&2", "warning")
                else:
                    if not icc1_on:
                        _icaw_set_alert(alerts, "GEN FAIL 1", "caution")
                    if not icc2_on:
                        _icaw_set_alert(alerts, "GEN FAIL 2", "caution")
                if not icc3_on:
                    _icaw_set_alert(alerts, "GEN FAIL 3", "caution")

            cab_press = str(power.get("CAB_PRESS", "NORM")).upper()
            if cab_press in {"DUMP", "RAM"}:
                _icaw_set_alert(alerts, "CABIN PRESS", "caution")

            try:
                batt_28v = float(power.get("BATT_28V", 0.0))
            except Exception:
                batt_28v = 0.0
            if bat_on and bool(power.get("BATT_28V_SBIT_COMPLETE", False)):
                if batt_28v <= 5.0:
                    _icaw_set_alert(alerts, "BATT LO 28V", "warning")
                elif batt_28v < 10.0:
                    _icaw_set_alert(alerts, "BATT LO 28V", "caution")
            if bool(power.get("BATT_270V_LOW_LIGHT", False)):
                _icaw_set_alert(alerts, "BATT LO 270V", "warning")

            canopy_pos = float(throttle.get("CANOPY_POS", 0.0))
            if canopy_pos < 0.999:
                # Ground: advisory only. In flight: caution.
                _icaw_set_alert_runtime(alerts, "CANOPY UNLOCKED", "caution" if in_flight else "advisory")

            # Keep SMS GROUND SAFE active until a VS BIT run completes successfully.
            try:
                vs_bit_status = str(throttle.get("VS_BIT_STATUS", "OK")).upper()
            except Exception:
                vs_bit_status = "OK"
            try:
                vs_bit_last_result_ms = int(throttle.get("VS_BIT_LAST_RESULT_MS", 0))
            except Exception:
                vs_bit_last_result_ms = 0
            vs_bit_has_pass = bool(vs_bit_status == "OK" and vs_bit_last_result_ms > 0)
            sms_ground_safe_active = not bool(vs_bit_has_pass)
            if sms_ground_safe_active:
                # Advisory on ground, caution in flight.
                _icaw_set_alert_runtime(alerts, "SMS GROUND SAFE", "caution" if in_flight else "advisory")
                # WPN DOOR is suppressed while SMS GROUND SAFE is active.
                alerts[:] = [a for a in alerts if str(a[0]).strip().upper() != "WPN DOOR"]

            if parking_brake_mode == "ON":
                _icaw_set_alert_runtime(alerts, "PARKING BRAKE ON", "advisory")

            if engine_mode == "RUN" and (engine_spool_mode != "RUN" or engine_spool < 0.999):
                _icaw_set_alert(alerts, "ENG START ASSIST", "advisory")
            if gear_handle_down and airspeed_kts > 300.0:
                _icaw_set_alert(alerts, "OVERSPEED GEAR", "caution")
            # Suppress ENG THRUST LO during active V/S BIT and while on ground.
            if in_flight and gear_handle_up and thrust_pct < 47.0 and (not bool(throttle.get("VS_BIT_RUNNING", False))):
                _icaw_set_alert(alerts, "ENG THRUST LO", "caution")
            if in_flight and total_speed_kts < 150.0 and (altitude_ft > 500.0 or gear_handle_up):
                _icaw_set_alert(alerts, "ENG STALL", "caution")
            gear_fail_ground_up = bool(on_ground and gear_handle_up)
            touchdown_descent_rate_fpm = prev_descent_rate_fpm if touchdown_this_frame else descent_rate_fpm
            touchdown_airspeed_kts = prev_airspeed_kts if touchdown_this_frame else airspeed_kts
            hard_descent_limit_fpm = max(300.0, 5.0 * max(0.0, touchdown_airspeed_kts))
            gear_fail_ground_hard_descent = bool(
                touchdown_this_frame
                and gear_handle_down
                and (touchdown_descent_rate_fpm > hard_descent_limit_fpm)
            )
            if gear_fail_ground_up or gear_fail_ground_hard_descent:
                _icaw_set_alert(alerts, "GEAR FAIL", "caution")

            auto_runtime["prev_on_ground"] = bool(on_ground)
            auto_runtime["prev_descent_rate_fpm"] = float(descent_rate_fpm)
            auto_runtime["prev_airspeed_kts"] = float(max(0.0, airspeed_kts))

            if bool(throttle.get("VS_BIT_RUNNING", False)):
                _icaw_set_alert_runtime(alerts, "VS BIT RUNNING", "advisory")
            if bool(throttle.get("VS_BIT_NO_GO", False)):
                _icaw_set_alert(alerts, "VS BIT NO GO", "caution")
    except Exception:
        pass

    if wpn_doors_not_closed and (not sms_ground_safe_active):
        _icaw_set_alert(alerts, "WPN DOOR", "caution")

    # Auto SVC DEBUG related ICAWS conditions.
    try:
        bos_qty = float(SVC_DEBUG_STATE.get("bos_qty", 330.0))
        eng_oil_qts = float(SVC_DEBUG_STATE.get("eng_oil_qts", 12.0))
        hyd_a_cuin = float(SVC_DEBUG_STATE.get("hyd_a_cuin", 436.0))
        hyd_b_cuin = float(SVC_DEBUG_STATE.get("hyd_b_cuin", 540.0))

        if bos_qty < 250.0:
            _icaw_set_alert(alerts, "BOS LO", "caution")
        if bos_qty < 280.0:
            _icaw_set_alert(alerts, "BOS SERVICE", "advisory")
        if eng_oil_qts < 6.0:
            _icaw_set_alert(alerts, "ENG OIL", "caution")
        if hyd_a_cuin < 400.0 or hyd_a_cuin > 450.0:
            _icaw_set_alert(alerts, "HYD FLUID A", "caution")
        if hyd_b_cuin < 505.0 or hyd_b_cuin > 555.0:
            _icaw_set_alert(alerts, "HYD FLUID B", "caution")
    except Exception:
        pass

    # If both single-hydraulic fails are present, collapse to HYD FAIL DUAL.
    if _icaw_has_text(alerts, "HYD FAIL A") and _icaw_has_text(alerts, "HYD FAIL B"):
        _icaw_set_alert(alerts, "HYD FAIL DUAL", "warning")
        alerts[:] = [a for a in alerts if str(a[0]).strip().upper() not in {"HYD FAIL A", "HYD FAIL B"}]

    if _icaw_has_text(alerts, "GEN FAIL 1") and _icaw_has_text(alerts, "GEN FAIL 2"):
        _icaw_set_alert(alerts, "GEN FAIL 1&2", "warning")

    hidden_binding_alerts: List[Tuple[str, str]] = []
    # GEN FAIL 1&2 displays as the warning, but it inherits the HRC behavior
    # from the two underlying single-generator caution alerts.
    if _icaw_has_text(alerts, "GEN FAIL 1&2"):
        for name in ("GEN FAIL 1", "GEN FAIL 2"):
            norm = _icaw_normalize_alert(name, "caution")
            if norm is not None:
                hidden_binding_alerts.append(norm)
        alerts[:] = [a for a in alerts if str(a[0]).strip().upper() not in {"GEN FAIL 1", "GEN FAIL 2"}]
    ICAWS_STATE["_hidden_binding_alerts"] = hidden_binding_alerts

    _icaw_sync_hrc_bindings(alerts)

    sev_rank = {"warning": 0, "caution": 1, "advisory": 2}
    alerts.sort(key=lambda t: sev_rank.get(t[1], 2))
    return alerts

ENGINE_MID_VALUES: Dict[str, int] = {
    "HYDA": 5,
    "HYDB": 7,
}

SVC_DEBUG_STATE: Dict[str, float] = {
    "bos_qty": 330.0,
    "bos_psi": 2545.0 * (330.0 / 400.0),
    "eng_oil_qts": 12.0,
    "hyd_a_cuin": 436.0,
    "hyd_b_cuin": 540.0,
    "hyd_a_qts": 436.0 * 0.017316,
    "hyd_b_qts": 540.0 * 0.017316,
    "pao_cuin": 5.3,
    "batt_28v": 95.0,
}


class FormatContext:
    def __init__(
        self,
        portal_index: int,
        request_vded: Callable[[int, str], None],
        set_format: Callable[[int, str], None],
        close_vded: Callable[[int], None],
        is_osb_flashing: Optional[Callable[[str], bool]] = None,
        set_status_menu_button_rect: Optional[Callable[[pygame.Rect], None]] = None,
        set_eng_popup_button_rect: Optional[Callable[[pygame.Rect], None]] = None,
        set_fuel_popup_button_rect: Optional[Callable[[pygame.Rect], None]] = None,
        set_sms_popup_button_rect: Optional[Callable[[pygame.Rect], None]] = None,
        set_fcs_popup_button_rect: Optional[Callable[[pygame.Rect], None]] = None,
        set_icaws_popup_button_rect: Optional[Callable[[pygame.Rect], None]] = None,
        set_autopilot_popup_button_rect: Optional[Callable[[pygame.Rect], None]] = None,
        set_nav_popup_button_rect: Optional[Callable[[pygame.Rect], None]] = None,
        set_iff_popup_button_rect: Optional[Callable[[pygame.Rect], None]] = None,
        set_altitude_popup_button_rect: Optional[Callable[[pygame.Rect], None]] = None,
        set_time_popup_button_rect: Optional[Callable[[pygame.Rect], None]] = None,
        set_record_button_rect: Optional[Callable[[pygame.Rect], None]] = None,
        set_comm_popup_button_rect: Optional[Callable[[pygame.Rect], None]] = None,
        set_swap_button_rect: Optional[Callable[[pygame.Rect], None]] = None,
        get_status_fuel_values: Optional[Callable[[], Tuple[float, float, float]]] = None,
        get_status_fuel_snapshot: Optional[Callable[[], Dict[str, object]]] = None,
        get_status_engine_thrust: Optional[Callable[[], float]] = None,
        get_status_fps: Optional[Callable[[], float]] = None,
        show_status_fps: bool = False,
        get_comm_state: Optional[Callable[[], Dict[str, object]]] = None,
        status_menu_popup_active: bool = False,
        status_menu_button_flashing: bool = False,
        eng_popup_active: bool = False,
        fuel_popup_active: bool = False,
        sms_popup_active: bool = False,
        fcs_popup_active: bool = False,
        icaws_popup_active: bool = False,
        autopilot_popup_active: bool = False,
        nav_popup_active: bool = False,
        iff_popup_active: bool = False,
        altitude_popup_active: bool = False,
        time_popup_active: bool = False,
        record_active: bool = False,
        record_started: bool = False,
        record_elapsed_seconds: int = 0,
        record_mode_name: str = "RECORD",
        record_area_label: str = "L H R",
        comm_popup_active: bool = False,
        status_swapped: bool = False,
    ) -> None:
        self.portal_index = portal_index
        self.request_vded = request_vded
        self.set_format = set_format
        self.close_vded = close_vded
        self.is_osb_flashing = is_osb_flashing or (lambda _label: False)
        self.set_status_menu_button_rect = set_status_menu_button_rect or (lambda _rect: None)
        self.set_eng_popup_button_rect = set_eng_popup_button_rect or (lambda _rect: None)
        self.set_fuel_popup_button_rect = set_fuel_popup_button_rect or (lambda _rect: None)
        self.set_sms_popup_button_rect = set_sms_popup_button_rect or (lambda _rect: None)
        self.set_fcs_popup_button_rect = set_fcs_popup_button_rect or (lambda _rect: None)
        self.set_icaws_popup_button_rect = set_icaws_popup_button_rect or (lambda _rect: None)
        self.set_autopilot_popup_button_rect = set_autopilot_popup_button_rect or (lambda _rect: None)
        self.set_nav_popup_button_rect = set_nav_popup_button_rect or (lambda _rect: None)
        self.set_iff_popup_button_rect = set_iff_popup_button_rect or (lambda _rect: None)
        self.set_altitude_popup_button_rect = set_altitude_popup_button_rect or (lambda _rect: None)
        self.set_time_popup_button_rect = set_time_popup_button_rect or (lambda _rect: None)
        self.set_record_button_rect = set_record_button_rect or (lambda _rect: None)
        self.set_comm_popup_button_rect = set_comm_popup_button_rect or (lambda _rect: None)
        self.set_swap_button_rect = set_swap_button_rect or (lambda _rect: None)
        self.get_status_fuel_values = get_status_fuel_values or (lambda: (0.0, 0.0, 0.0))
        self.get_status_fuel_snapshot = get_status_fuel_snapshot or (lambda: {})
        self.get_status_engine_thrust = get_status_engine_thrust or (lambda: 0.0)
        self.get_status_fps = get_status_fps or (lambda: 0.0)
        self.show_status_fps = bool(show_status_fps)
        self.get_comm_state = get_comm_state or (lambda: {})
        self.status_menu_popup_active = status_menu_popup_active
        self.status_menu_button_flashing = status_menu_button_flashing
        self.eng_popup_active = eng_popup_active
        self.fuel_popup_active = fuel_popup_active
        self.sms_popup_active = sms_popup_active
        self.fcs_popup_active = fcs_popup_active
        self.icaws_popup_active = icaws_popup_active
        self.autopilot_popup_active = autopilot_popup_active
        self.nav_popup_active = nav_popup_active
        self.iff_popup_active = iff_popup_active
        self.altitude_popup_active = altitude_popup_active
        self.time_popup_active = time_popup_active
        self.record_active = record_active
        self.record_started = record_started
        self.record_elapsed_seconds = record_elapsed_seconds
        self.record_mode_name = str(record_mode_name)
        self.record_area_label = str(record_area_label)
        self.comm_popup_active = comm_popup_active
        self.status_swapped = status_swapped


class FormatBase:
    name: str = "UNKNOWN"
    _LOCAL_FLASH_MS = 250

    def render(self, surface, rect, is_primary: bool, context: FormatContext) -> None:
        pass

    def on_osb(self, label: str, context: FormatContext) -> bool:
        return False

    def osb_is_interactive(self, label: str) -> bool:
        return True

    def get_t1_override(self, system_mode: str) -> Optional[List[Tuple[str, Tuple[int, int, int]]]]:
        return None

    def _trigger_local_flash(self, key: str, ms: Optional[int] = None) -> None:
        try:
            flash = getattr(self, "_local_flash_until", None)
            if not isinstance(flash, dict):
                flash = {}
                setattr(self, "_local_flash_until", flash)
            duration = int(self._LOCAL_FLASH_MS if ms is None else ms)
            flash[str(key).upper().strip()] = int(pygame.time.get_ticks()) + max(1, duration)
        except Exception:
            pass

    def _local_flash_active(self, key: str, now_ms: Optional[int] = None) -> bool:
        try:
            flash = getattr(self, "_local_flash_until", None)
            if not isinstance(flash, dict):
                return False
            now = int(pygame.time.get_ticks()) if now_ms is None else int(now_ms)
            return int(flash.get(str(key).upper().strip(), 0) or 0) > now
        except Exception:
            return False

    def t1_opens_menu(self) -> bool:
        if self._is_vsd():
            return True
        return not bool(self._ensure_dclt_state().get("dclt_menu_open", False))


class VdedBase:
    name: str = "UNKNOWN"

    def render(self, surface, rect, context: FormatContext) -> None:
        pass

    def on_zone(self, label: str, context: FormatContext) -> bool:
        return False


_FONT_CACHE: Dict[int, pygame.font.Font] = {}
_AIRCRAFT_ICON_CACHE: Dict[Tuple[int, int], pygame.Surface] = {}
_SMS_LAYER_LOAD_QUEUE = deque()
_SMS_LAYER_LOAD_PENDING: set = set()
_SMS_TINT_COLOR = (0x65, 0x67, 0x66)
FONT_SIZE_BOOST = 5


def get_font(size: int) -> pygame.font.Font:
    adjusted_size = max(1, int(size) + FONT_SIZE_BOOST)
    font = _FONT_CACHE.get(adjusted_size)
    if font is None:
        font = pygame.font.SysFont("consolas", adjusted_size)
        _FONT_CACHE[adjusted_size] = font
    return font


def get_green_aircraft_icon(size: Tuple[int, int]) -> Optional[pygame.Surface]:
    cached = _AIRCRAFT_ICON_CACHE.get(size)
    if cached is not None:
        return cached
    icon_path = resource_path("icons", "STATUS BAR", "Aircraft.png")
    if not icon_path.exists():
        return None
    try:
        src = pygame.image.load(str(icon_path)).convert_alpha()
    except Exception:
        return None
    sw = max(1, src.get_width())
    sh = max(1, src.get_height())
    tw = max(1, size[0])
    th = max(1, size[1])
    scale = min(tw / sw, th / sh)
    nw = max(1, int(sw * scale))
    nh = max(1, int(sh * scale))
    scaled = pygame.transform.smoothscale(src, (nw, nh))
    canvas = pygame.Surface((tw, th), pygame.SRCALPHA)
    dst = scaled.get_rect(center=(tw // 2, th // 2))
    canvas.blit(scaled, dst)
    tinted = canvas.copy()
    tint_layer = pygame.Surface(size, pygame.SRCALPHA)
    tint_layer.fill((0, 255, 0, 255))
    tinted.blit(tint_layer, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    _AIRCRAFT_ICON_CACHE[size] = tinted
    return tinted


def preload_graphics_assets() -> None:
    # Queue image-based assets so they can be loaded incrementally per frame.
    try:
        get_green_aircraft_icon((max(1, int(1.125 * DPI) - 12), max(1, int(1.0 * DPI) - 12)))
    except Exception:
        pass
    try:
        sms = SmsFormat()
        sms._get_layer_image("SMS AIRCRAFT.png", tinted=False)
        sms._get_layer_image("SMS AIRCRAFT.png", tinted=True)
        for side in ("LT", "RT"):
            for state in ("CLOSE", "PARTIAL", "OPEN"):
                name = sms._door_overlay_name(side, state)
                sms._get_layer_image(name, tinted=False)
                sms._get_layer_image(name, tinted=True)
    except Exception:
        pass


def pump_graphics_asset_loading(max_items: int = 2) -> int:
    # Perform a bounded number of queued asset decodes each frame.
    loaded = 0
    budget = max(1, int(max_items))
    while loaded < budget and _SMS_LAYER_LOAD_QUEUE:
        key = _SMS_LAYER_LOAD_QUEUE.popleft()
        _SMS_LAYER_LOAD_PENDING.discard(key)
        if key in SmsFormat._cached_layers:
            continue
        SmsFormat._load_layer_now(key)
        loaded += 1
    return loaded


def parse_hex_color(hex_value: str) -> Tuple[int, int, int]:
    value = hex_value.strip().lstrip("#")
    if len(value) != 6:
        return (0, 255, 0)
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def draw_multiline_text(
    surface,
    rect,
    lines: List[Tuple[str, str]],
    font_size: int = 16,
    line_spacing: int = 2,
) -> None:
    font = get_font(font_size)
    y = rect.y + 2
    for text, color_hex in lines:
        color = parse_hex_color(color_hex)
        rendered = font.render(text, True, color)
        surface.blit(rendered, (rect.x + 2, y))
        y += rendered.get_height() + line_spacing


def draw_centered_text(
    surface,
    rect,
    text: str,
    color_hex: str,
    font_size: int = 16,
) -> None:
    font = get_font(font_size)
    color = parse_hex_color(color_hex)
    rendered = font.render(text, True, color)
    text_rect = rendered.get_rect(center=rect.center)
    surface.blit(rendered, text_rect)


def draw_multiline_centered_text(
    surface,
    rect,
    lines: List[Tuple[str, str]],
    font_size: int = 16,
    line_spacing: int = 2,
) -> None:
    font = get_font(font_size)
    rendered_lines = [(font.render(text, True, parse_hex_color(color)), text)
                      for text, color in lines]
    total_height = sum(line.get_height() for line, _ in rendered_lines)
    total_height += line_spacing * max(0, len(rendered_lines) - 1)
    y = rect.centery - total_height / 2
    for rendered, _ in rendered_lines:
        text_rect = rendered.get_rect(center=(rect.centerx, int(y + rendered.get_height() / 2)))
        surface.blit(rendered, text_rect)
        y += rendered.get_height() + line_spacing


def draw_hazard_stripe_border(
    surface: pygame.Surface,
    rect: pygame.Rect,
    border_thickness: int = HAZARD_BORDER_THICKNESS,
    stripe_line_width: int = HAZARD_STRIPE_LINE_WIDTH,
    stripe_spacing: int = HAZARD_STRIPE_SPACING,
    colors: Tuple[Tuple[int, int, int], Tuple[int, int, int]] = ((0, 0, 0), (255, 255, 0)),
) -> None:
    if rect.width <= 0 or rect.height <= 0:
        return
    border_thickness = max(1, border_thickness)
    stripe_line_width = max(1, stripe_line_width)
    stripe_color = colors[1]
    overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    for offset in range(-rect.height, rect.width + rect.height, stripe_spacing):
        start = (offset, rect.height)
        end = (offset + rect.height, 0)
        pygame.draw.line(overlay, (*stripe_color, 255), start, end, stripe_line_width)

    hole = pygame.Rect(
        border_thickness,
        border_thickness,
        rect.width - border_thickness * 2,
        rect.height - border_thickness * 2,
    )
    if hole.width > 0 and hole.height > 0:
        pygame.draw.rect(overlay, (0, 0, 0, 0), hole)

    surface.blit(overlay, rect.topleft)


def draw_hazard_stripe_fill_box(
    surface: pygame.Surface,
    rect: pygame.Rect,
    stripe_line_width: int = HAZARD_STRIPE_LINE_WIDTH,
    stripe_spacing: int = HAZARD_STRIPE_SPACING,
    colors: Tuple[Tuple[int, int, int], Tuple[int, int, int]] = ((0, 0, 0), (255, 255, 0)),
) -> None:
    if rect.width <= 0 or rect.height <= 0:
        return
    stripe_line_width = max(1, stripe_line_width)
    base_color = colors[0]
    stripe_color = colors[1]
    pygame.draw.rect(surface, base_color, rect, 0)
    overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    for offset in range(-rect.height, rect.width + rect.height, stripe_spacing):
        start = (offset, rect.height)
        end = (offset + rect.height, 0)
        pygame.draw.line(overlay, (*stripe_color, 255), start, end, stripe_line_width)
    surface.blit(overlay, rect.topleft)
    pygame.draw.rect(surface, stripe_color, rect, 1)


def draw_arc_gauge(
    surface: pygame.Surface,
    center: Tuple[int, int],
    radius: int,
    start_angle_deg: float,
    sweep_deg: float,
    percent: float,
    color: Tuple[int, int, int] = (0, 255, 255),
    red_start_percent: float = 0.8,
) -> None:
    percent = max(0.0, min(1.0, percent))
    rect = pygame.Rect(0, 0, radius * 2, radius * 2)
    rect.center = center
    start_rad = math.radians(start_angle_deg)
    end_rad = math.radians(start_angle_deg + sweep_deg)
    pygame.draw.arc(surface, color, rect, start_rad, end_rad, 2)

    red_start = start_angle_deg + sweep_deg * red_start_percent
    red_start_rad = math.radians(red_start)
    pygame.draw.arc(surface, (255, 0, 0), rect, red_start_rad, end_rad, 2)

    needle_angle = start_angle_deg + sweep_deg * percent
    needle_rad = math.radians(needle_angle)
    end_x = center[0] + int(radius * math.cos(needle_rad))
    end_y = center[1] - int(radius * math.sin(needle_rad))
    pygame.draw.line(surface, color, center, (end_x, end_y), 2)

    pct_text = f"{int(percent * 100)}%"
    text_rect = pygame.Rect(center[0] - radius, center[1] - radius - 20, radius * 2, 20)
    draw_centered_text(surface, text_rect, pct_text, "00FFFF", 16)

@dataclass
class GridCell:
    label: str
    rect: pygame.Rect
    center: Tuple[int, int]
    merged: bool = False
    split_axis: Optional[str] = None


def build_portal_grid() -> Dict[str, GridCell]:
    grid: Dict[str, GridCell] = {}
    rows = "ABCDEFGH"
    for row_index, row_label in enumerate(rows):
        for col in range(1, 6):
            x = int((col - 1) * GRID_CELL_W)
            y = int(row_index * GRID_CELL_H)
            rect = pygame.Rect(x, y, GRID_CELL_W, GRID_CELL_H)
            label = f"{row_label}{col}"
            center = (rect.centerx, rect.centery)
            grid[label] = GridCell(label=label, rect=rect, center=center)
    return grid


def merge_grid_cells(
    grid: Dict[str, GridCell],
    labels: Iterable[str],
    merged_label: Optional[str] = None,
) -> GridCell:
    cells = [grid[label] for label in labels if label in grid]
    if not cells:
        raise ValueError("No grid cells provided for merge.")
    left = min(cell.rect.left for cell in cells)
    top = min(cell.rect.top for cell in cells)
    right = max(cell.rect.right for cell in cells)
    bottom = max(cell.rect.bottom for cell in cells)
    rect = pygame.Rect(left, top, right - left, bottom - top)
    if merged_label is None:
        merged_label = "+".join(label for label in labels)
    split_axis = "vertical" if rect.height > rect.width else "horizontal"
    center = (rect.centerx, rect.centery)
    merged = GridCell(label=merged_label, rect=rect, center=center, merged=True, split_axis=split_axis)
    return merged


def merged_hit_half(cell: GridCell, local_pos: Tuple[int, int]) -> int:
    if not cell.merged or cell.split_axis is None:
        return 1
    if cell.split_axis == "vertical":
        return 1 if local_pos[1] < cell.rect.top + cell.rect.height / 2 else 2
    return 1 if local_pos[0] < cell.rect.left + cell.rect.width / 2 else 2




def _comm_freq_key_for_radio(radio_key: str) -> str:
    mapping = {"coma": "coma_freq", "comb": "comb_freq", "comc": "comc_freq", "comd": "comd_freq"}
    return str(mapping.get(str(radio_key).strip().lower(), ""))


def _comm_preset_key_for_radio(radio_key: str) -> str:
    mapping = {"coma": "preset_a", "comb": "preset_b", "comc": "preset_c", "comd": "preset_d"}
    return str(mapping.get(str(radio_key).strip().lower(), ""))


def _comm_presets_key_for_radio(radio_key: str) -> str:
    mapping = {"coma": "coma_presets", "comb": "comb_presets", "comc": "comc_presets", "comd": "comd_presets"}
    return str(mapping.get(str(radio_key).strip().lower(), ""))


def _comm_preset_labels_key_for_radio(radio_key: str) -> str:
    mapping = {
        "coma": "coma_preset_labels",
        "comb": "comb_preset_labels",
        "comc": "comc_preset_labels",
        "comd": "comd_preset_labels",
    }
    return str(mapping.get(str(radio_key).strip().lower(), ""))


def _comm_mode_for_radio(state: Dict[str, object], radio_key: str) -> str:
    key = str(radio_key).strip().lower()
    mode_map = state.get("radio_modes", {})
    if isinstance(mode_map, dict):
        mode = str(mode_map.get(key, "")).strip()
        if mode != "":
            return mode
    fallback = {
        "coma": "HIGH VHF",
        "comb": "LOW VHF",
        "comc": "UHF",
        "comd": "AM",
    }
    return str(fallback.get(key, ""))


def _comm_band_indicator_for_mode(mode_text: str) -> str:
    mode = str(mode_text).strip().upper()
    has_uhf = "UHF" in mode
    has_vhf = ("VHF" in mode) or ("SINCGARS" in mode)
    if has_uhf and has_vhf:
        return ""
    if has_uhf:
        return "U"
    if has_vhf:
        return "V"
    return ""


def _comm_profile_for_radio(state: Dict[str, object], radio_key: str) -> Dict[str, bool]:
    defaults = {"tone_on": False, "mute_on": False, "sqlch_on": False, "aj_on": False, "secure_on": False}
    profiles = state.get("radio_profiles", {})
    if not isinstance(profiles, dict):
        return dict(defaults)
    prof = profiles.get(str(radio_key).strip().lower(), {})
    if not isinstance(prof, dict):
        return dict(defaults)
    out = dict(defaults)
    for k in out.keys():
        out[k] = bool(prof.get(k, out[k]))
    return out


def _comm_preset_number_for_freq(state: Dict[str, object], radio_key: str, freq_text: str) -> Optional[int]:
    presets_key = _comm_presets_key_for_radio(radio_key)
    preset_key = _comm_preset_key_for_radio(radio_key)
    if presets_key == "" or preset_key == "":
        return None
    presets = state.get(presets_key, [])
    if not isinstance(presets, list) or len(presets) <= 0:
        return None
    freq = str(freq_text).strip()
    preset_val = state.get(preset_key, None)
    try:
        idx = int(preset_val)
    except Exception:
        idx = 0
    if 1 <= idx <= len(presets):
        try:
            preset_freq = str(presets[idx - 1]).strip()
        except Exception:
            preset_freq = ""
        if preset_freq == freq:
            return int(idx)
    for i, value in enumerate(presets):
        if str(value).strip() == freq:
            return int(i + 1)
    return None


def _comm_preset_label_for_number(state: Dict[str, object], radio_key: str, preset_number: Optional[int]) -> str:
    if preset_number is None or int(preset_number) <= 0:
        return ""
    labels_key = _comm_preset_labels_key_for_radio(radio_key)
    if labels_key == "":
        return ""
    labels = state.get(labels_key, [])
    if not isinstance(labels, list) or len(labels) <= 0:
        return ""
    idx = int(preset_number) - 1
    if idx < 0 or idx >= len(labels):
        return ""
    return str(labels[idx]).strip().upper()


def _comm_row_label_parts(
    state: Dict[str, object],
    radio_key: str,
    freq_text: str,
    preset_number: Optional[int],
) -> Tuple[str, str, str]:
    prof = _comm_profile_for_radio(state, radio_key)
    left = "AJ" if bool(prof.get("aj_on", False)) else ""
    right = "S" if bool(prof.get("secure_on", False)) else ""
    # AJ/SECURE overlays replace the normal preset/guard center label.
    if left != "" or right != "":
        return left, "", right
    freq = str(freq_text).strip().upper()
    if freq == "243.000":
        center = "GUARD"
    else:
        center = _comm_preset_label_for_number(state, radio_key, preset_number)
    return left, center, right


def _comm_compose_row_label(left: str, center: str, right: str) -> str:
    pieces = [str(left).strip(), str(center).strip(), str(right).strip()]
    return " ".join([p for p in pieces if p != ""]).strip()


def _comm_cni_class_for_radio(radio_key: str, fallback: str = "U/V") -> str:
    radio_norm = str(radio_key).strip().lower()
    com_letter = {"coma": "A", "comb": "B", "comc": "C", "comd": "D"}.get(radio_norm, "")
    if com_letter == "":
        return str(fallback)
    try:
        rows = getattr(CniFormat, "_table_rows", [])
    except Exception:
        rows = []
    if not isinstance(rows, list):
        return str(fallback)
    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) < 5:
            continue
        row_com = str(row[4]).upper().strip()
        if row_com != com_letter:
            continue
        class_value = str(row[1]).upper().strip()
        if class_value != "":
            return class_value
        return str(fallback)
    return str(fallback)



from format_defs.basic import BasicFormat
from format_defs.fcs import FcsFormat
from format_defs.sms import SmsFormat, update_sms_door_transitions
from format_defs.statusbar import StatusBarFormat
from format_defs.eng import EngineFormat
from format_defs.autopilot import AutopilotFormat
from format_defs.navmenu import NavMenuFormat
from format_defs.iff import IffFormat
from format_defs.altitude import AltitudeFormat
from format_defs.wind import WindFormat
from format_defs.comm import CommFormat
from format_defs.cni import CniFormat
from format_defs.cklst_legacy import CklstLegacyFormat
from format_defs.cklst import CklstFormat
from format_defs.wpn_a import WpnAFormat
from format_defs.wpn_s import WpnSFormat
from format_defs.icaws import IcawsFormat
from format_defs.fuel import FuelFormat
from format_defs.phm import PhmFormat
from format_defs.efi import EfiFormat
from format_defs.hud import HudFormat
from format_defs.search import SearchFormat
from format_defs.asr1 import Asr1Format
from format_defs.twd import TwdFormat
from format_defs.tsd import Tsd1Format
from format_defs.dim import DimFormat, DimV2Format
from format_defs.offline_sensor import OfflineSensorFormat
from format_defs.tflir3d import Tflir3DFormat
from format_defs.das3d import Das3DFormat
from format_defs.runtime_registry import (
    StubFormat,
    StubVded,
    create_format,
    create_vded,
    register_format,
    register_vded,
)
from format_defs.menu_vded import MenuVded

# Export all currently known symbols (including single-underscore helpers) so
# split format modules importing `from formats import *` get shared internals.
__all__ = [name for name in globals().keys() if not name.startswith("__")]

# Backfill all imported split modules with the fully-populated formats globals
# so cross-format references (e.g. EngineFormat from statusbar) resolve.
for _mod_name, _mod in list(sys.modules.items()):
    if not isinstance(_mod_name, str):
        continue
    if not _mod_name.startswith("format_defs."):
        continue
    try:
        _mod.__dict__.update(globals())
    except Exception:
        pass

def prewarm_tsd_background_loads() -> None:
    """
    Kick off long-running TSD background loaders at application startup.
    Safe to call multiple times.
    """
    try:
        Tsd1Format._load_runways()
    except Exception as exc:
        print(f"[TSD][RUNWAYS_DATA] startup prewarm failed: {exc}")


FORMAT_NAMES = list(DEFAULT_FORMAT_NAMES)
STATUS_FORMATS = list(DEFAULT_STATUS_FORMATS)

bootstrap_default_formats(
    register_format,
    register_vded,
    format_names=FORMAT_NAMES,
    status_formats=STATUS_FORMATS,
    BasicFormat=BasicFormat,
    MenuVded=MenuVded,
)

# Final export pass so modules using `from formats import *` can see late-bound
# globals populated during bootstrap/refactor wiring.
__all__ = [name for name in globals().keys() if not name.startswith("__")]
