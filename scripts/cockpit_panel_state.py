from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Tuple

import pygame

import formats
from app_paths import resource_path
from main_config import *  # noqa: F401,F403

_play_sound_effect_cb = None
_get_sound_length_or_default_ms_cb = None


def configure_runtime_hooks(play_sound_effect_cb=None, get_sound_length_or_default_ms_cb=None) -> None:
    global _play_sound_effect_cb, _get_sound_length_or_default_ms_cb
    if play_sound_effect_cb is not None:
        _play_sound_effect_cb = play_sound_effect_cb
    if get_sound_length_or_default_ms_cb is not None:
        _get_sound_length_or_default_ms_cb = get_sound_length_or_default_ms_cb


def set_panel_text_lites_tint(consl_on: bool, brightness: int) -> None:
    global _PANEL_TEXT_LITES_A1_ON, _PANEL_TEXT_LITES_B1_BRT
    _PANEL_TEXT_LITES_A1_ON = bool(consl_on)
    try:
        brt = int(brightness)
    except Exception:
        brt = 0
    _PANEL_TEXT_LITES_B1_BRT = max(0, min(100, brt))


def play_sound_effect(name: str) -> None:
    cb = _play_sound_effect_cb
    if callable(cb):
        try:
            cb(name)
        except Exception:
            pass


def get_sound_length_or_default_ms(name: str, default_ms: int) -> int:
    cb = _get_sound_length_or_default_ms_cb
    if callable(cb):
        try:
            return int(cb(name, default_ms))
        except Exception:
            return int(default_ms)
    return int(default_ms)

_PANEL_IMAGE_CACHE: Dict[str, Optional[pygame.Surface]] = {}
_PANEL_PAGE_CACHE: Optional[List[List[str]]] = None
_PANEL_BUTTON_IMAGE_CACHE: Dict[str, Optional[pygame.Surface]] = {}
_PANEL_BUTTON_BBOX_CACHE: Dict[str, Optional[pygame.Rect]] = {}
_PANEL_BUTTON_ROT_CW90_CACHE: Dict[str, pygame.Surface] = {}
_PANEL_RUNTIME_BUTTON_HITS: List[Dict[str, object]] = []
_PANEL_ACTIVE_HOLDS: Dict[int, Optional[Tuple[str, str]]] = {1: None, 3: None}
_PANEL_ACTIVE_DIAL_DRAG: Optional[Dict[str, object]] = None
_PANEL_TEXT_LITES_A1_ON: bool = False
_PANEL_TEXT_LITES_B1_BRT: int = 0
_PANEL_TEXT_CACHE_SIG: Optional[Tuple[bool, int]] = None
CANOPY_ACTUATOR_TRAVEL_MS = 10000
IPP_START_HOLD_REQUIRED_MS = 3000
VS_BIT_DURATION_MS = 20000
VS_BIT_THROTTLE_UP_MS = 1000
VS_BIT_THROTTLE_DOWN_MS = 1000
FLIGHT_CONTROL_MAX_DEG = 20.0
# Editable default user flight-control movement speed.
FLIGHT_CONTROL_MOVE_RATE_DPS = 40.0
VS_BIT_FLIGHT_CONTROL_RATE_SCALE = 0.50
VS_BIT_FCS_STEP_DELAY_MS = 1000
VS_BIT_IDLE_STABLE_REQUIRED_MS = 15000
VS_BIT_FCS_TIMEOUT_GRACE_MS = 5000
VS_BIT_CONTROL_ABORT_DEADZONE = 0.18
VS_BIT_THROTTLE_ABORT_DELTA = 1.50
FCS_SYMBOL_MAX_OFFSET_IN = 0.5
RUDDER_TRIM_RATE_IN_PER_SEC = 0.25
_FLIGHT_CTRL_MANUAL_KEYS = {
    "elev_up": (pygame.K_w,),
    "elev_down": (pygame.K_s,),
    "ail_left": (pygame.K_a,),
    "ail_right": (pygame.K_d,),
    "rud_left": (pygame.K_q,),
    "rud_right": (pygame.K_e,),
}
FLIGHT_KEYBINDS_SETTINGS_KEY = "flight_keybinds"
HOTAS_BINDINGS_SETTINGS_KEY = "hotas_bindings"
PMD_KEYBIND_ACTION_ORDER: List[str] = [
    "rec_cap",
    "strt_rec",
    "cap_area",
    "restart",
    "ful_scrn",
    "com_mute",
    "com_a",
    "com_b",
    "com_c",
    "rud_left",
    "elev_up",
    "rud_right",
    "ail_left",
    "elev_down",
    "ail_right",
    "throt_minus",
    "throt_plus",
    "brake",
    "ldg_gear",
    "ipp_run",
    "engine_run",
    "tx",
    "pickle",
    "wpn_sel",
    "gun_trigger",
    "disconnect",
    "nws",
    "tms_up",
    "tms_down",
    "tms_left",
    "tms_right",
    "dms_up",
    "dms_down",
    "dms_left",
    "dms_right",
    "fov_up",
    "fov_down",
    "fov_left",
    "fov_right",
    "cms_up",
    "cms_down",
    "cms_left",
    "cms_right",
    "mngmt_z",
    "mngmt_up",
    "mngmt_down",
    "wms_z",
    "wms_fwd",
    "wms_aft",
    "wms_left",
    "wms_right",
    "slew_z",
    "slew_fwd",
    "slew_aft",
    "slew_left",
    "slew_right",
    "comm_ctl_z",
    "comm_ctl_fwd",
    "comm_ctl_aft",
    "comm_ctl_left",
    "comm_ctl_right",
    "cage_uncage",
    "mpo",
    "pol_ctrl",
    "aprch_pwr_comp",
    "cffl_z",
    "cffl_fwd",
    "cffl_aft",
    "spd_brk_fwd",
    "spd_brk_aft",
    "spd_hold_z",
    "spd_hold_up",
    "spd_hold_down",
]
PMD_KEYBIND_ACTION_LABELS: Dict[str, str] = {
    "rec_cap": "RECORD/CAPTURE",
    "strt_rec": "START RECORDING",
    "cap_area": "CAPTURE AREA",
    "restart": "RESTART",
    "ful_scrn": "FULL SCREEN",
    "com_mute": "COM MUTE",
    "com_a": "COM A",
    "com_b": "COM B",
    "com_c": "COM C",
    "rud_left": "RUDDER LEFT",
    "elev_up": "PITCH DOWN",
    "rud_right": "RUDDER RIGHT",
    "ail_left": "ROLL LEFT",
    "elev_down": "PITCH UP",
    "ail_right": "ROLL RIGHT",
    "throt_minus": "THROTTLE DOWN",
    "throt_plus": "THROTTLE UP",
    "brake": "BRAKE",
    "ldg_gear": "LANDING GEAR",
    "ipp_run": "IPP RUN",
    "engine_run": "ENGINE RUN",
    "tx": "TX",
    "pickle": "WEAPON RELEASE",
    "wpn_sel": "WPN REL MODE",
    "gun_trigger": "GUN ENABLE",
    "disconnect": "DISCONNECT",
    "nws": "NWS",
    "tms_up": "TMS UP",
    "tms_down": "TMS DOWN",
    "tms_left": "TMS LEFT",
    "tms_right": "TMS RIGHT",
    "dms_up": "DMS UP",
    "dms_down": "DMS DOWN",
    "dms_left": "DMS LEFT",
    "dms_right": "DMS RIGHT",
    "fov_up": "FOV UP",
    "fov_down": "FOV DOWN",
    "fov_left": "FOV LEFT",
    "fov_right": "FOV RIGHT",
    "cms_up": "CMS UP",
    "cms_down": "CMS DOWN",
    "cms_left": "CMS LEFT",
    "cms_right": "CMS Z",
    "mngmt_z": "MNGMT Z",
    "mngmt_up": "MNGMT UP",
    "mngmt_down": "MNGMT DOWN",
    "wms_z": "WMS Z",
    "wms_fwd": "WMS FWD",
    "wms_aft": "WMS AFT",
    "wms_left": "WMS LEFT",
    "wms_right": "WMS RIGHT",
    "slew_z": "SLEW Z",
    "slew_fwd": "SLEW FWD",
    "slew_aft": "SLEW AFT",
    "slew_left": "SLEW LEFT",
    "slew_right": "SLEW RIGHT",
    "comm_ctl_z": "COMM CTL Z",
    "comm_ctl_fwd": "COMM CTL FWD",
    "comm_ctl_aft": "COMM CTL AFT",
    "comm_ctl_left": "COMM CTL LEFT",
    "comm_ctl_right": "COMM CTL RIGHT",
    "cage_uncage": "CAGE UNCAGE",
    "mpo": "MPO",
    "pol_ctrl": "POL CTRL",
    "aprch_pwr_comp": "APRCH PWR COMP",
    "cffl_z": "CFFL Z",
    "cffl_fwd": "CFFL FWD",
    "cffl_aft": "CFFL AFT",
    "spd_brk_fwd": "SPD BRK FWD",
    "spd_brk_aft": "SPD BRK AFT",
    "spd_hold_z": "SPD HOLD Z",
    "spd_hold_up": "SPD HOLD UP",
    "spd_hold_down": "SPD HOLD DOWN",
}
PMD_KEYBIND_DEFAULT_NAMES: Dict[str, str] = {
    "elev_up": "w",
    "elev_down": "s",
    "ail_left": "a",
    "ail_right": "d",
    "rud_left": "q",
    "rud_right": "e",
    "rec_cap": "f1",
    "strt_rec": "f2",
    "cap_area": "f3",
    "restart": "f5",
    "ful_scrn": "f11",
    "throt_plus": "left shift",
    "throt_minus": "left ctrl",
    "com_a": "1",
    "com_b": "2",
    "com_c": "3",
    "tx": "t",
    "ipp_run": "",
    "engine_run": "home",
    "gun_trigger": "space",
    "pickle": "right alt",
    "com_mute": "m",
    "brake": "b",
    "ldg_gear": "g",
    "wpn_sel": "",
    "disconnect": "",
    "nws": "",
    "tms_up": "",
    "tms_down": "",
    "tms_left": "",
    "tms_right": "",
    "dms_up": "",
    "dms_down": "",
    "dms_left": "",
    "dms_right": "",
    "fov_up": "",
    "fov_down": "",
    "fov_left": "",
    "fov_right": "",
    "cms_up": "",
    "cms_down": "",
    "cms_left": "",
    "cms_right": "",
    "mngmt_z": "",
    "mngmt_up": "",
    "mngmt_down": "",
    "wms_z": "",
    "wms_fwd": "",
    "wms_aft": "",
    "wms_left": "",
    "wms_right": "",
    "slew_z": "",
    "slew_fwd": "",
    "slew_aft": "",
    "slew_left": "",
    "slew_right": "",
    "comm_ctl_z": "",
    "comm_ctl_fwd": "",
    "comm_ctl_aft": "",
    "comm_ctl_left": "",
    "comm_ctl_right": "",
    "cage_uncage": "",
    "mpo": "",
    "pol_ctrl": "",
    "aprch_pwr_comp": "",
    "cffl_z": "",
    "cffl_fwd": "",
    "cffl_aft": "",
    "spd_brk_fwd": "",
    "spd_brk_aft": "",
    "spd_hold_z": "",
    "spd_hold_up": "",
    "spd_hold_down": "",
}

PMD_KEYBIND_DISPLAY_ALIASES: Dict[str, str] = {
    "LEFT SHIFT": "L SHIFT",
    "RIGHT SHIFT": "R SHIFT",
    "LEFT CTRL": "L CTRL",
    "RIGHT CTRL": "R CTRL",
}


def _format_keybind_display_text(raw_text: object) -> str:
    upper = str(raw_text).strip().upper()
    if upper == "":
        return ""
    return str(PMD_KEYBIND_DISPLAY_ALIASES.get(upper, upper))


HOTAS_ACTION_ORDER: List[str] = [
    "pitch",
    "yaw",
    "roll",
    "brake_left",
    "throttle",
    "brake_right",
    "ldg_gear",
    "ipp_run",
    "engine_run",
    "mngmt",
    "mngmt_z",
    "mngmt_up",
    "mngmt_down",
    "wms_z",
    "wms_fwd",
    "wms_aft",
    "wms_left",
    "wms_right",
    "slew_z",
    "slew_lr",
    "slew_ud",
    "comm_ctl_z",
    "comm_ctl_fwd",
    "comm_ctl_aft",
    "comm_ctl_left",
    "comm_ctl_right",
    "pickle",
    "wpn_sel",
    "gun_trigger",
    "disconnect",
    "nws",
    "tms_up",
    "tms_down",
    "tms_left",
    "tms_right",
    "dms_up",
    "dms_down",
    "dms_left",
    "dms_right",
    "fov_up",
    "fov_down",
    "fov_left",
    "fov_right",
    "cms_up",
    "cms_down",
    "cms_left",
    "cms_right",
    "cage_uncage",
    "mpo",
    "pol_ctrl",
    "aprch_pwr_comp",
    "cffl_z",
    "cffl_fwd",
    "cffl_aft",
    "spd_brk_fwd",
    "spd_brk_aft",
    "spd_hold_z",
    "spd_hold_up",
    "spd_hold_down",
]

HOTAS_ACTION_TITLES: Dict[str, str] = {
    "pitch": "PITCH",
    "yaw": "YAW",
    "roll": "ROLL",
    "brake_left": "BRAKE LEFT",
    "throttle": "THROTTLE",
    "brake_right": "BRAKE RIGHT",
    "ldg_gear": "LANDING GEAR",
    "ipp_run": "IPP RUN",
    "engine_run": "ENGINE RUN",
    "mngmt": "MNGMT",
    "mngmt_z": "MNGMT Z",
    "mngmt_up": "MNGMT UP",
    "mngmt_down": "MNGMT DOWN",
    "wms_z": "WMS Z",
    "wms_fwd": "WMS FWD",
    "wms_aft": "WMS AFT",
    "wms_left": "WMS LEFT",
    "wms_right": "WMS RIGHT",
    "slew_z": "SLEW Z",
    "slew_lr": "SLEW X",
    "slew_ud": "SLEW Y",
    "comm_ctl_z": "COMM CTL Z",
    "comm_ctl_fwd": "COMM CTL FWD",
    "comm_ctl_aft": "COMM CTL AFT",
    "comm_ctl_left": "COMM CTL LEFT",
    "comm_ctl_right": "COMM CTL RIGHT",
    "pickle": "WEAPON RELEASE",
    "wpn_sel": "WPN REL MODE",
    "gun_trigger": "GUN ENABLE",
    "disconnect": "DISCONNECT",
    "nws": "NWS",
    "tms_up": "TMS UP",
    "tms_down": "TMS DOWN",
    "tms_left": "TMS LEFT",
    "tms_right": "TMS RIGHT",
    "dms_up": "DMS UP",
    "dms_down": "DMS DOWN",
    "dms_left": "DMS LEFT",
    "dms_right": "DMS RIGHT",
    "fov_up": "FOV UP",
    "fov_down": "FOV DOWN",
    "fov_left": "FOV LEFT",
    "fov_right": "FOV RIGHT",
    "cms_up": "CMS UP",
    "cms_down": "CMS DOWN",
    "cms_left": "CMS LEFT",
    "cms_right": "CMS Z",
    "cage_uncage": "CAGE UNCAGE",
    "mpo": "MPO",
    "pol_ctrl": "POL CTRL",
    "aprch_pwr_comp": "APRCH PWR COMP",
    "cffl_z": "CFFL Z",
    "cffl_fwd": "CFFL FWD",
    "cffl_aft": "CFFL AFT",
    "spd_brk_fwd": "SPD BRK FWD",
    "spd_brk_aft": "SPD BRK AFT",
    "spd_hold_z": "SPD HOLD Z",
    "spd_hold_up": "SPD HOLD UP",
    "spd_hold_down": "SPD HOLD DOWN",
}

HOTAS_ALLOWED_INPUTS: Dict[str, Tuple[str, ...]] = {
    "pitch": ('axis',),
    "yaw": ('axis',),
    "roll": ('axis',),
    "brake_left": ('axis',),
    "throttle": ('axis',),
    "brake_right": ('axis',),
    "ldg_gear": ('hat', 'button'),
    "ipp_run": ('hat', 'button'),
    "engine_run": ('hat', 'button'),
    "mngmt": ('axis',),
    "mngmt_z": ('hat', 'button'),
    "mngmt_up": ('hat', 'button'),
    "mngmt_down": ('hat', 'button'),
    "wms_z": ('hat', 'button'),
    "wms_fwd": ('hat', 'button'),
    "wms_aft": ('hat', 'button'),
    "wms_left": ('hat', 'button'),
    "wms_right": ('hat', 'button'),
    "slew_z": ('hat', 'button'),
    "slew_lr": ('axis',),
    "slew_ud": ('axis',),
    "comm_ctl_z": ('hat', 'button'),
    "comm_ctl_fwd": ('hat', 'button'),
    "comm_ctl_aft": ('hat', 'button'),
    "comm_ctl_left": ('hat', 'button'),
    "comm_ctl_right": ('hat', 'button'),
    "pickle": ('button',),
    "wpn_sel": ('button',),
    "gun_trigger": ('button',),
    "disconnect": ('hat', 'button'),
    "nws": ('hat', 'button'),
    "tms_up": ('hat', 'button'),
    "tms_down": ('hat', 'button'),
    "tms_left": ('hat', 'button'),
    "tms_right": ('hat', 'button'),
    "dms_up": ('hat', 'button'),
    "dms_down": ('hat', 'button'),
    "dms_left": ('hat', 'button'),
    "dms_right": ('hat', 'button'),
    "fov_up": ('hat', 'button'),
    "fov_down": ('hat', 'button'),
    "fov_left": ('hat', 'button'),
    "fov_right": ('hat', 'button'),
    "cms_up": ('hat', 'button'),
    "cms_down": ('hat', 'button'),
    "cms_left": ('hat', 'button'),
    "cms_right": ('hat', 'button'),
    "cage_uncage": ('hat', 'button'),
    "mpo": ('hat', 'button'),
    "pol_ctrl": ('hat', 'button'),
    "aprch_pwr_comp": ('hat', 'button'),
    "cffl_z": ('hat', 'button'),
    "cffl_fwd": ('hat', 'button'),
    "cffl_aft": ('hat', 'button'),
    "spd_brk_fwd": ('hat', 'button'),
    "spd_brk_aft": ('hat', 'button'),
    "spd_hold_z": ('hat', 'button'),
    "spd_hold_up": ('hat', 'button'),
    "spd_hold_down": ('hat', 'button'),
}
def _airspeed_kts_from_thrust_pct(thrust_pct: float) -> float:
    t = max(0.0, min(AIRSPEED_MAX_THRUST_PCT, float(thrust_pct)))
    if t <= AIRSPEED_MIN_THRUST_PCT:
        return 0.0
    if t <= AIRSPEED_AB_START_THRUST_PCT:
        span_pre_ab = max(1e-6, AIRSPEED_AB_START_THRUST_PCT - AIRSPEED_MIN_THRUST_PCT)
        frac_pre_ab = max(0.0, min(1.0, (t - AIRSPEED_MIN_THRUST_PCT) / span_pre_ab))
        v = AIRSPEED_AT_AB_START_KTS * (frac_pre_ab ** AIRSPEED_PRE_AB_EXP)
        return max(0.0, min(AIRSPEED_MAX_KTS, float(v)))
    span_ab = max(1e-6, AIRSPEED_MAX_THRUST_PCT - AIRSPEED_AB_START_THRUST_PCT)
    frac_ab = max(0.0, min(1.0, (t - AIRSPEED_AB_START_THRUST_PCT) / span_ab))
    v = AIRSPEED_AT_AB_START_KTS + (AIRSPEED_MAX_KTS - AIRSPEED_AT_AB_START_KTS) * (frac_ab ** AIRSPEED_AB_EXP)
    return max(0.0, min(AIRSPEED_MAX_KTS, float(v)))


def _thrust_pct_from_airspeed_kts(airspeed_kts: float) -> float:
    v = max(0.0, min(float(AIRSPEED_MAX_KTS), float(airspeed_kts)))
    if v <= 0.0:
        return 0.0
    if v <= float(AIRSPEED_AT_AB_START_KTS):
        frac = max(0.0, min(1.0, v / max(1e-6, float(AIRSPEED_AT_AB_START_KTS))))
        frac_pre_ab = frac ** (1.0 / max(1e-6, float(AIRSPEED_PRE_AB_EXP)))
        thrust = float(AIRSPEED_MIN_THRUST_PCT) + (
            float(AIRSPEED_AB_START_THRUST_PCT) - float(AIRSPEED_MIN_THRUST_PCT)
        ) * frac_pre_ab
        return max(0.0, min(float(AIRSPEED_MAX_THRUST_PCT), float(thrust)))
    frac_ab = max(
        0.0,
        min(
            1.0,
            (v - float(AIRSPEED_AT_AB_START_KTS))
            / max(1e-6, float(AIRSPEED_MAX_KTS) - float(AIRSPEED_AT_AB_START_KTS)),
        ),
    )
    frac_thrust_ab = frac_ab ** (1.0 / max(1e-6, float(AIRSPEED_AB_EXP)))
    thrust = float(AIRSPEED_AB_START_THRUST_PCT) + (
        float(AIRSPEED_MAX_THRUST_PCT) - float(AIRSPEED_AB_START_THRUST_PCT)
    ) * frac_thrust_ab
    return max(0.0, min(float(AIRSPEED_MAX_THRUST_PCT), float(thrust)))


def _engine_thrust_lbf_from_percent(thrust_pct: float) -> float:
    pct = max(0.0, min(float(ENGINE_THRUST_LBF_MAX_PCT), float(thrust_pct)))
    if pct <= float(ENGINE_THRUST_LBF_IDLE_CUTOFF_PCT):
        return 0.0
    if pct <= float(ENGINE_THRUST_LBF_MIL_PCT):
        span = max(1e-6, float(ENGINE_THRUST_LBF_MIL_PCT) - float(ENGINE_THRUST_LBF_IDLE_CUTOFF_PCT))
        frac = (pct - float(ENGINE_THRUST_LBF_IDLE_CUTOFF_PCT)) / span
        return max(0.0, float(ENGINE_THRUST_LBF_MIL) * max(0.0, min(1.0, frac)))
    if pct < float(ENGINE_THRUST_LBF_AB_START_PCT):
        return float(ENGINE_THRUST_LBF_MIL)
    span_ab = max(1e-6, float(ENGINE_THRUST_LBF_MAX_PCT) - float(ENGINE_THRUST_LBF_AB_START_PCT))
    frac_ab = (pct - float(ENGINE_THRUST_LBF_AB_START_PCT)) / span_ab
    return float(ENGINE_THRUST_LBF_MIL) + (float(ENGINE_THRUST_LBF_MAX) - float(ENGINE_THRUST_LBF_MIL)) * max(0.0, min(1.0, frac_ab))


def _gross_weight_lbf_from_fuel() -> float:
    try:
        fuel_lbs = max(0.0, float(getattr(formats.FuelFormat, "_shared_total_lbs", 0.0)))
    except Exception:
        fuel_lbs = 0.0
    # Match FUEL GW readout: GW = 29.0 + (fuel_lbs / 1000.0).
    return float(F35_EMPTY_WEIGHT_LBS) + float(fuel_lbs)


def _total_fuel_lbs_runtime() -> float:
    try:
        shared_qty = getattr(formats.FuelFormat, "_shared_fuel_qty", None)
        if isinstance(shared_qty, dict) and len(shared_qty) > 0:
            total = float(sum(max(0.0, float(v)) for v in shared_qty.values()))
            if total > 0.0:
                return total
    except Exception:
        pass
    try:
        return max(0.0, float(getattr(formats.FuelFormat, "_shared_total_lbs", 0.0)))
    except Exception:
        return 0.0


def _fuel_feed_available(min_total_lbs: float = 1.0) -> bool:
    return _total_fuel_lbs_runtime() > max(0.0, float(min_total_lbs))


def _lift_coeff_from_airspeed_kts(airspeed_kts: float, altitude_ft: float, _bank_deg: float) -> float:
    stall = max(1e-6, float(ALTITUDE_STALL_SPEED_KTS))
    ratio = max(0.0, float(airspeed_kts) / stall)
    coeff = ratio * ratio
    ceiling = max(1.0, float(AERO_LIFT_CEILING_FT))
    alt_norm = max(0.0, min(1.0, float(altitude_ft) / ceiling))
    alt_factor = 1.0 - (alt_norm ** float(AERO_LIFT_ALTITUDE_EXP))
    alt_factor = max(float(AERO_LIFT_CEILING_MIN_FACTOR), min(1.0, alt_factor))
    coeff *= alt_factor
    return max(0.0, min(float(LIFT_COEFF_MAX), coeff))


def _aero_drag_lbf(speed_fps: float) -> float:
    v = max(0.0, float(speed_fps))
    high = max(0.0, v - float(AERO_DRAG_HIGH_SPEED_BREAK_FPS))
    drag = float(AERO_DRAG_BASE_LBF) + (float(AERO_DRAG_QUAD_COEFF) * v * v) + (float(AERO_DRAG_HIGH_SPEED_COEFF) * high * high)
    return max(0.0, drag)


def _altitude_target_ft_from_airspeed_kts(airspeed_kts: float) -> float:
    s = max(0.0, min(ALTITUDE_MAX_SPEED_KTS, float(airspeed_kts)))
    if s <= ALTITUDE_MIN_SPEED_KTS:
        return 0.0
    if s <= ALTITUDE_KNEE_SPEED_KTS:
        span_pre = max(1e-6, ALTITUDE_KNEE_SPEED_KTS - ALTITUDE_MIN_SPEED_KTS)
        frac_pre = max(0.0, min(1.0, (s - ALTITUDE_MIN_SPEED_KTS) / span_pre))
        return max(0.0, min(ALTITUDE_MAX_FT, ALTITUDE_KNEE_FT * (frac_pre ** ALTITUDE_PRE_KNEE_EXP)))
    span_post = max(1e-6, ALTITUDE_MAX_SPEED_KTS - ALTITUDE_KNEE_SPEED_KTS)
    frac_post = max(0.0, min(1.0, (s - ALTITUDE_KNEE_SPEED_KTS) / span_post))
    v = ALTITUDE_KNEE_FT + (ALTITUDE_MAX_FT - ALTITUDE_KNEE_FT) * (frac_post ** ALTITUDE_POST_KNEE_EXP)
    return max(0.0, min(ALTITUDE_MAX_FT, float(v)))


def _ensure_panel_button_states() -> Dict[str, Dict[str, object]]:
    state = getattr(formats, "PANEL_BUTTON_STATES", None)
    if not isinstance(state, dict):
        state = {}
        setattr(formats, "PANEL_BUTTON_STATES", state)
    power = state.get("POWER PANEL")
    if not isinstance(power, dict):
        power = {}
        state["POWER PANEL"] = power
    power.setdefault("BAT", "OFF")
    power.setdefault("ICC3", "OFF")
    power.setdefault("ICC2", "OFF")
    power.setdefault("ICC1", "OFF")
    power.setdefault("CAB_PRESS", "NORM")
    power.setdefault("IPP", "AUTO")
    power.setdefault("IPP_ON", False)
    power.setdefault("IPP_ON_SINCE_MS", 0)
    power.setdefault("IPP_START_HOLD_MS", 0)
    power.setdefault("IPP_OFF_HOLD_MS", 0)
    power.setdefault("IPP_START_SEQ_END_MS", 0)
    power.setdefault("IPP_START_SEQ_SUCCESS", False)
    power.setdefault("IPP_START_BLOCKED", False)
    power.setdefault("IPP_SHUTDOWN_SEQ_END_MS", 0)
    power.setdefault("BAT_ON_SINCE_MS", 0)
    power.setdefault("BAT_OFF_SINCE_MS", 0)
    power.setdefault("BATT_28V", 95.0)
    power.setdefault("BAT_ACTIVE", False)
    power.setdefault("BATT_28V_SBIT_STARTED", False)
    power.setdefault("BATT_28V_SBIT_COMPLETE", False)
    power.setdefault("BATT_28V_SBIT_FLASH_UNTIL_MS", 0)
    power.setdefault("BATT_28V_DIS_ON", False)
    power.setdefault("BATT_28V_DIS_CLEAR_DUE_MS", 0)
    power.setdefault("BATT_28V_LOW_LIGHT", False)
    power.setdefault("BATT_28V_DIS_LIGHT", False)
    power.setdefault("BATT_270V_BIT_FLASH_UNTIL_MS", 0)
    power.setdefault("BATT_270V_DIS_ON", False)
    power.setdefault("BATT_270V_LOW_LIGHT", False)
    power.setdefault("BATT_270V_DIS_LIGHT", False)
    power.setdefault("EMER_PRESSED", False)
    throttle = state.get("THROTTLE")
    if not isinstance(throttle, dict):
        throttle = {}
        state["THROTTLE"] = throttle
    throttle.setdefault("CANOPY", "CENTER")
    throttle.setdefault("CANOPY_POS", 0.0)
    throttle.setdefault("ENGINE", "OFF")
    throttle.setdefault("THROTTLE_POS", 0.0)
    throttle.setdefault("ENGINE_SPOOL", 0.0)
    throttle.setdefault("ENGINE_SPOOL_MODE", "OFF")
    throttle.setdefault("ENGINE_LAST_NON_OFF", "OFF")
    throttle.setdefault("ENGINE_PREV_CMD", "OFF")
    throttle.setdefault("ENGINE_SWITCH_PREV", "OFF")
    throttle.setdefault("ENGINE_RUN_TRANSITION_ACTIVE", False)
    throttle.setdefault("ENGINE_RUN_TRANSITION_MS", 0.0)
    throttle.setdefault("ENGINE_RUN_TRANSITION_FROM", {})
    throttle.setdefault("ENGINE_OFF_EGT_BASE", float(random.uniform(20.0, 60.0)))
    throttle.setdefault("FCS_RESET", "DOWN")
    throttle.setdefault("RUDDER", "CENTER")
    throttle.setdefault("RUDDER_TRIM_IN", 0.0)
    throttle.setdefault("VS_BIT_PRESSED", False)
    throttle.setdefault("VS_BIT_RUNNING", False)
    throttle.setdefault("VS_BIT_END_MS", 0)
    throttle.setdefault("VS_BIT_START_MS", 0)
    throttle.setdefault("VS_BIT_HOLD_THROTTLE_POS", 0.0)
    throttle.setdefault("VS_BIT_MANUAL_OVERRIDE", False)
    throttle.setdefault("VS_BIT_REFUEL_SEEN", False)
    throttle.setdefault("VS_BIT_NO_GO", False)
    throttle.setdefault("VS_BIT_DOOR_MOVED", False)
    throttle.setdefault("VS_BIT_THROTTLE_MOVED", False)
    throttle.setdefault("VS_BIT_CTRL_MOVED", False)
    throttle.setdefault("VS_BIT_DOOR_SIG", "")
    throttle.setdefault("VS_BIT_EXPECT_REFUEL_OPEN", None)
    throttle.setdefault("VS_BIT_FCS_ACTIVE", False)
    throttle.setdefault("VS_BIT_FCS_STEP_IDX", 0)
    throttle.setdefault("VS_BIT_FCS_ACTION_DONE", False)
    throttle.setdefault("VS_BIT_FCS_NEXT_STEP_MS", 0)
    throttle.setdefault("VS_BIT_STATUS", "OK")  # OK | TS | FN
    throttle.setdefault("VS_BIT_FAIL_REASONS", [])
    throttle.setdefault("VS_BIT_REASON_CATALOG", [])
    throttle.setdefault("VS_BIT_LAST_RESULT_MS", 0)
    throttle.setdefault("VS_BIT_IDLE_SINCE_MS", 0)
    throttle.setdefault("VS_BIT_HOTAS_LAST_CMD", None)
    throttle.setdefault("VS_BIT_ABORT_INPUT_SOURCE", "")
    throttle.setdefault("VS_BIT_ABORT_INPUT_DETAIL", "")
    display = state.get("DISPLAY CONTROL")
    if not isinstance(display, dict):
        display = {}
        state["DISPLAY CONTROL"] = display
    display.setdefault("MFD_MODE", "DAY")
    display.setdefault("BRIGHTNESS_LEVEL", 10)
    master_arm = state.get("MASTER ARM")
    if not isinstance(master_arm, dict):
        master_arm = {}
        state["MASTER ARM"] = master_arm
    master_arm.setdefault("MASTER_ARM", "OFF")
    master_arm.setdefault("DIAL_A", 5)
    master_arm.setdefault("DIAL_B", 5)
    master_arm.setdefault("DIAL_C", 5)
    console_left = state.get("CONSOLE LEFT")
    if not isinstance(console_left, dict):
        console_left = {}
        state["CONSOLE LEFT"] = console_left
    console_left.setdefault("JETT", "EXT")
    console_left.setdefault("PARKING_BRAKE", "ON")
    console_left.setdefault("GEAR", "DOWN_OFF")
    console_left.setdefault("GEAR_TRANSITION_DUE_MS", 0)
    console_left.setdefault("GEAR_TRANSITION_START_MS", 0)
    console_left.setdefault("GEAR_TRANSITION_DIR", "")
    console_left.setdefault("GEAR_TRANSITION_DURATION_MS", 0)
    console_left.setdefault("JETT_ACTIVATE_COUNT", 0)
    console_left.setdefault("JETT_LAST_ACTIVATE_MS", 0)
    aircraft = state.get("AIRCRAFT")
    if not isinstance(aircraft, dict):
        aircraft = {}
        state["AIRCRAFT"] = aircraft
    aircraft.setdefault("AIRSPEED_KTS", 0.0)
    aircraft.setdefault("TOTAL_SPEED_KTS", 0.0)
    aircraft.setdefault("ALTITUDE_FT", 0.0)
    aircraft.setdefault("ALTITUDE_TARGET_FT", 0.0)
    aircraft.setdefault("VERTICAL_SPEED_FPM", 0.0)
    aircraft.setdefault("PITCH_CMD", 0.0)
    aircraft.setdefault("ATT_PITCH_DEG", 0.0)
    aircraft.setdefault("ATT_ROLL_DEG", 0.0)
    aircraft.setdefault("ATT_YAW_RATE_DPS", 0.0)
    aircraft.setdefault("PITCH", 0.0)
    aircraft.setdefault("YAW", 0.0)
    aircraft.setdefault("ROLL", 0.0)
    aircraft.setdefault("ATTITUDE", 0.0)
    aircraft.setdefault("BANK", 0.0)
    aircraft.setdefault("ATT_DEBUG_LAST_PRINT_MS", 0.0)
    aircraft.setdefault("ATT_PITCH_RAW_DEG", 0.0)
    aircraft.setdefault("ATT_ROLL_RAW_DEG", 0.0)
    aircraft.setdefault("ATT_HEADING_BASE_DEG", 35.0)
    aircraft.setdefault("ATT_Q_W", 1.0)
    aircraft.setdefault("ATT_Q_X", 0.0)
    aircraft.setdefault("ATT_Q_Y", 0.0)
    aircraft.setdefault("ATT_Q_Z", 0.0)
    aircraft.setdefault("ATT_PITCH_INVERTED", False)
    aircraft.setdefault("ATT_PITCH_FLIP_BLEND", 0.0)
    aircraft.setdefault("ATT_PITCH_FLIP_LATCH", False)
    aircraft.setdefault("ATT_INPUT_INVERTED", False)
    aircraft.setdefault("G_LOAD", 1.0)
    aircraft.setdefault("VEL_X_FPS", 0.0)
    aircraft.setdefault("VEL_Y_FPS", 0.0)
    aircraft.setdefault("VEL_Z_FPS", 0.0)
    aircraft.setdefault("HEADING_DEG", 35.0)
    aircraft.setdefault("HDG_DEG", 35.0)
    aircraft.setdefault("HEADING", 35.0)
    aircraft.setdefault("HDG", 35.0)
    aircraft.setdefault("l_lef", 0.0)
    aircraft.setdefault("r_lef", 0.0)
    aircraft.setdefault("l_aileron", 0.0)
    aircraft.setdefault("r_aileron", 0.0)
    aircraft.setdefault("l_rudder", 0.0)
    aircraft.setdefault("r_rudder", 0.0)
    aircraft.setdefault("l_elevator", 0.0)
    aircraft.setdefault("r_elevator", 0.0)
    aircraft.setdefault("fcs_top_cyan_x_in", 0.0)
    aircraft.setdefault("fcs_top_cyan_y_in", 0.0)
    aircraft.setdefault("fcs_bottom_cyan_x_in", 0.0)
    aircraft.setdefault("fcs_rudder_trim_in", 0.0)
    phm_status = state.get("PHM STATUS")
    if not isinstance(phm_status, dict):
        phm_status = {}
        state["PHM STATUS"] = phm_status
    phm_status.setdefault("status_overrides", {})
    phm_status.setdefault("hrc_events", {})
    phm_status.setdefault("fna_events", {})
    phm_status.setdefault("remove_default_cni_migrated", False)
    if not bool(phm_status.get("defaults_initialized", False)):
        hrc_events = phm_status.get("hrc_events", {})
        fna_events = phm_status.get("fna_events", {})
        status_overrides = phm_status.get("status_overrides", {})
        if not isinstance(hrc_events, dict):
            hrc_events = {}
            phm_status["hrc_events"] = hrc_events
        if not isinstance(fna_events, dict):
            fna_events = {}
            phm_status["fna_events"] = fna_events
        if not isinstance(status_overrides, dict):
            status_overrides = {}
            phm_status["status_overrides"] = status_overrides
        phm_status["defaults_initialized"] = True
    if not bool(phm_status.get("remove_default_cni_migrated", False)):
        hrc_events = phm_status.get("hrc_events", {})
        fna_events = phm_status.get("fna_events", {})
        status_overrides = phm_status.get("status_overrides", {})
        if isinstance(hrc_events, dict):
            cni_vals = hrc_events.get("CNI", [])
            if isinstance(cni_vals, list):
                filtered_cni = [str(x).strip() for x in cni_vals if str(x).strip() != ""]
                if len(filtered_cni) == 1 and filtered_cni[0] == "2336130 15 2829":
                    hrc_events.pop("CNI", None)
        if isinstance(status_overrides, dict):
            if str(status_overrides.get("COM_NAV", "")).upper().strip() == "HR":
                has_cni_hrc = False
                has_com_nav_hrc = False
                has_com_nav_fna = False
                if isinstance(hrc_events, dict):
                    cni_hrc = hrc_events.get("CNI", [])
                    com_nav_hrc = hrc_events.get("COM_NAV", [])
                    has_cni_hrc = isinstance(cni_hrc, list) and any(str(x).strip() != "" for x in cni_hrc)
                    has_com_nav_hrc = isinstance(com_nav_hrc, list) and any(str(x).strip() != "" for x in com_nav_hrc)
                if isinstance(fna_events, dict):
                    com_nav_fna = fna_events.get("COM_NAV", [])
                    has_com_nav_fna = isinstance(com_nav_fna, list) and any(str(x).strip() != "" for x in com_nav_fna)
                if not has_cni_hrc and not has_com_nav_hrc and not has_com_nav_fna:
                    status_overrides.pop("COM_NAV", None)
        phm_status["remove_default_cni_migrated"] = True
    return state


def _load_panel_button_image(panel_name: str, filename: str) -> Optional[pygame.Surface]:
    key = f"{panel_name}/{filename}"
    if key in _PANEL_BUTTON_IMAGE_CACHE:
        return _PANEL_BUTTON_IMAGE_CACHE[key]
    path = resource_path("icons", "PANELS", panel_name, "BUTTONS", filename)
    if not path.exists():
        _PANEL_BUTTON_IMAGE_CACHE[key] = None
        return None
    try:
        surf = pygame.image.load(str(path)).convert_alpha()
        _PANEL_BUTTON_IMAGE_CACHE[key] = surf
        return surf
    except Exception:
        _PANEL_BUTTON_IMAGE_CACHE[key] = None
        return None


def _button_alpha_bbox(panel_name: str, filename: str, image: pygame.Surface) -> Optional[pygame.Rect]:
    key = f"{panel_name}/{filename}"
    if key in _PANEL_BUTTON_BBOX_CACHE:
        return _PANEL_BUTTON_BBOX_CACHE[key]
    try:
        bbox = image.get_bounding_rect(min_alpha=1)
        if bbox.width <= 0 or bbox.height <= 0:
            _PANEL_BUTTON_BBOX_CACHE[key] = None
            return None
        _PANEL_BUTTON_BBOX_CACHE[key] = bbox
        return bbox
    except Exception:
        _PANEL_BUTTON_BBOX_CACHE[key] = None
        return None


def _power_panel_button_image_filename(control: str, states: Dict[str, object]) -> str:
    rule = _POWER_PANEL_BUTTON_RULES.get(control, {})
    rtype = str(rule.get("type", ""))
    if rtype == "toggle":
        current = str(states.get(control, "OFF")).upper()
        return str(rule.get("on" if current == "ON" else "off", ""))
    if rtype == "tri":
        mode = str(states.get("CAB_PRESS", "NORM")).upper()
        if mode == "DUMP":
            return str(rule.get("dump", ""))
        if mode == "RAM":
            return str(rule.get("ram", ""))
        return str(rule.get("norm", ""))
    if rtype == "hold_lr":
        mode = str(states.get("IPP", "AUTO")).upper()
        if mode == "OFF":
            return str(rule.get("left", ""))
        if mode == "START":
            return str(rule.get("right", ""))
        return str(rule.get("auto", ""))
    return str(rule.get("image", ""))


def _ipp_light_visible(power: Dict[str, object], now_ms: int) -> bool:
    start_seq_end = int(power.get("IPP_START_SEQ_END_MS", 0))
    shutdown_seq_end = int(power.get("IPP_SHUTDOWN_SEQ_END_MS", 0))
    ipp_on = bool(power.get("IPP_ON", False))
    batt_on = bool(power.get("BAT_ACTIVE", str(power.get("BAT", "OFF")).upper() == "ON"))
    try:
        batt_28v = float(power.get("BATT_28V", 0.0))
    except Exception:
        batt_28v = 0.0
    if batt_28v <= 0.0:
        return False
    flashing = (start_seq_end > now_ms) or (shutdown_seq_end > now_ms)
    if flashing:
        if not batt_on and not ipp_on:
            return False
        return ((int(now_ms) // IPP_LIGHT_FLASH_INTERVAL_MS) % 2) == 0
    return ipp_on


def _button_image_rotated_cw_90(panel_name: str, filename: str, src: pygame.Surface) -> pygame.Surface:
    key = f"{panel_name}/{filename}"
    cached = _PANEL_BUTTON_ROT_CW90_CACHE.get(key)
    if cached is not None:
        return cached
    rotated = pygame.transform.rotate(src, -90)
    _PANEL_BUTTON_ROT_CW90_CACHE[key] = rotated
    return rotated


def _throttle_panel_button_image_filename(control: str, states: Dict[str, object]) -> str:
    rule = _THROTTLE_PANEL_BUTTON_RULES.get(control, {})
    rtype = str(rule.get("type", ""))
    if control == "FCS_RESET" and rtype == "toggle":
        current = str(states.get(control, "DOWN")).upper()
        return str(rule.get("down" if current == "DOWN" else "up", ""))
    if control == "CANOPY" and rtype == "hold_lr_tri":
        current = str(states.get("CANOPY", "CENTER")).upper()
        if current == "UP":
            return str(rule.get("up", ""))
        if current == "DOWN":
            return str(rule.get("down", ""))
        return str(rule.get("center", ""))
    if control in {"ENGINE", "RUDDER"} and rtype == "tri_lr":
        current = str(states.get(control, "CENTER")).upper()
        if current == "LEFT":
            return str(rule.get("left", ""))
        if current == "RIGHT":
            return str(rule.get("right", ""))
        if control == "ENGINE" and current == "RUN":
            return str(rule.get("left", ""))
        if control == "ENGINE" and current == "MOTOR":
            return str(rule.get("right", ""))
        if control == "ENGINE":
            return str(rule.get("center", ""))
        return str(rule.get("center", ""))
    return str(rule.get("image", ""))


def _display_control_button_image_filename(control: str, states: Dict[str, object]) -> str:
    rule = _DISPLAY_CONTROL_BUTTON_RULES.get(control, {})
    if control == "MFD":
        mode = str(states.get("MFD_MODE", "DAY")).upper()
        if mode == "OFF":
            return str(rule.get("left", ""))
        if mode == "NIGHT":
            return str(rule.get("center", ""))
        return str(rule.get("right", ""))
    return str(rule.get("image", ""))


def _master_arm_button_image_filename(control: str, states: Dict[str, object]) -> str:
    rule = _MASTER_ARM_BUTTON_RULES.get(control, {})
    if control == "MASTER_ARM":
        current = str(states.get("MASTER_ARM", "OFF")).upper()
        return str(rule.get("on" if current == "ON" else "off", ""))
    return str(rule.get("image", ""))


def _console_left_button_image_filename(control: str, states: Dict[str, object]) -> str:
    rule = _CONSOLE_LEFT_BUTTON_RULES.get(control, {})
    if control == "JETT":
        mode = str(states.get("JETT", "EXT")).upper()
        if mode == "SEL":
            return str(rule.get("sel", ""))
        if mode == "ALL":
            return str(rule.get("all", ""))
        return str(rule.get("ext", ""))
    if control == "PARKING_BRAKE":
        current = str(states.get("PARKING_BRAKE", "ON")).upper()
        return str(rule.get("off" if current == "OFF" else "on", ""))
    if control == "GEAR":
        mode = str(states.get("GEAR", "DOWN_OFF")).upper()
        if mode == "DOWN_ON":
            return str(rule.get("down_on", ""))
        if mode == "UP_OFF":
            return str(rule.get("up_off", ""))
        if mode == "UP_ON":
            return str(rule.get("up_on", ""))
        return str(rule.get("down_off", ""))
    return str(rule.get("image", ""))


def _draw_console_left_panel_buttons(screen: pygame.Surface, image_rect: pygame.Rect) -> None:
    state = _ensure_panel_button_states()
    console_left = state.get("CONSOLE LEFT", {})
    if not isinstance(console_left, dict):
        return
    for control in _CONSOLE_LEFT_BUTTON_RULES.keys():
        filename = _console_left_button_image_filename(control, console_left)
        if filename == "":
            continue
        src = _load_panel_button_image("CONSOLE LEFT", filename)
        if src is None:
            continue
        sw = max(1, image_rect.width)
        sh = max(1, image_rect.height)
        scaled = pygame.transform.smoothscale(src, (sw, sh))
        screen.blit(scaled, image_rect.topleft)
        bbox = _button_alpha_bbox("CONSOLE LEFT", filename, src)
        if bbox is None:
            continue
        sx = sw / float(max(1, src.get_width()))
        sy = sh / float(max(1, src.get_height()))
        hx = image_rect.left + int(round(bbox.x * sx))
        hy = image_rect.top + int(round(bbox.y * sy))
        hw = max(1, int(round(bbox.width * sx)))
        hh = max(1, int(round(bbox.height * sy)))
        _PANEL_RUNTIME_BUTTON_HITS.append(
            {
                "panel": "CONSOLE LEFT",
                "control": control,
                "rect": pygame.Rect(hx, hy, hw, hh),
            }
        )


def _draw_display_control_panel_buttons(screen: pygame.Surface, image_rect: pygame.Rect) -> None:
    state = _ensure_panel_button_states()
    display = state.get("DISPLAY CONTROL", {})
    if not isinstance(display, dict):
        return
    for control in _DISPLAY_CONTROL_BUTTON_RULES.keys():
        filename = _display_control_button_image_filename(control, display)
        if filename == "":
            continue
        src = _load_panel_button_image("DISPLAY CONTROL", filename)
        if src is None:
            continue
        sw = max(1, image_rect.width)
        sh = max(1, image_rect.height)
        scaled = pygame.transform.smoothscale(src, (sw, sh))
        screen.blit(scaled, image_rect.topleft)
        bbox = _button_alpha_bbox("DISPLAY CONTROL", filename, src)
        if bbox is None:
            continue
        sx = sw / float(max(1, src.get_width()))
        sy = sh / float(max(1, src.get_height()))
        hx = image_rect.left + int(round(bbox.x * sx))
        hy = image_rect.top + int(round(bbox.y * sy))
        hw = max(1, int(round(bbox.width * sx)))
        hh = max(1, int(round(bbox.height * sy)))
        _PANEL_RUNTIME_BUTTON_HITS.append(
            {
                "panel": "DISPLAY CONTROL",
                "control": control,
                "rect": pygame.Rect(hx, hy, hw, hh),
            }
        )


def _draw_master_arm_panel_buttons(screen: pygame.Surface, image_rect: pygame.Rect) -> None:
    state = _ensure_panel_button_states()
    master_arm = state.get("MASTER ARM", {})
    if not isinstance(master_arm, dict):
        return
    for control in _MASTER_ARM_BUTTON_RULES.keys():
        filename = _master_arm_button_image_filename(control, master_arm)
        if filename == "":
            continue
        src = _load_panel_button_image("MASTER ARM", filename)
        if src is None:
            continue
        sw = max(1, image_rect.width)
        sh = max(1, image_rect.height)
        scaled = pygame.transform.smoothscale(src, (sw, sh))
        screen.blit(scaled, image_rect.topleft)
        bbox = _button_alpha_bbox("MASTER ARM", filename, src)
        if bbox is None:
            continue
        sx = sw / float(max(1, src.get_width()))
        sy = sh / float(max(1, src.get_height()))
        hx = image_rect.left + int(round(bbox.x * sx))
        hy = image_rect.top + int(round(bbox.y * sy))
        hw = max(1, int(round(bbox.width * sx)))
        hh = max(1, int(round(bbox.height * sy)))
        _PANEL_RUNTIME_BUTTON_HITS.append(
            {
                "panel": "MASTER ARM",
                "control": control,
                "rect": pygame.Rect(hx, hy, hw, hh),
            }
        )


def _draw_power_panel_buttons(screen: pygame.Surface, image_rect: pygame.Rect) -> None:
    state = _ensure_panel_button_states()
    power = state.get("POWER PANEL", {})
    if not isinstance(power, dict):
        return
    for control in _POWER_PANEL_BUTTON_RULES.keys():
        filename = _power_panel_button_image_filename(control, power)
        if filename == "":
            continue
        src = _load_panel_button_image("POWER PANEL", filename)
        if src is None:
            continue
        sw = max(1, image_rect.width)
        sh = max(1, image_rect.height)
        scaled = pygame.transform.smoothscale(src, (sw, sh))
        screen.blit(scaled, image_rect.topleft)
        bbox = _button_alpha_bbox("POWER PANEL", filename, src)
        if bbox is None:
            continue
        sx = sw / float(max(1, src.get_width()))
        sy = sh / float(max(1, src.get_height()))
        hx = image_rect.left + int(round(bbox.x * sx))
        hy = image_rect.top + int(round(bbox.y * sy))
        hw = max(1, int(round(bbox.width * sx)))
        hh = max(1, int(round(bbox.height * sy)))
        _PANEL_RUNTIME_BUTTON_HITS.append(
            {
                "panel": "POWER PANEL",
                "control": control,
                "rect": pygame.Rect(hx, hy, hw, hh),
            }
        )
    if _ipp_light_visible(power, int(pygame.time.get_ticks())):
        src = _load_panel_button_image("POWER PANEL", "IPP LIGHT.png")
        if src is not None:
            sw = max(1, image_rect.width)
            sh = max(1, image_rect.height)
            scaled = pygame.transform.smoothscale(src, (sw, sh))
            screen.blit(scaled, image_rect.topleft)
    indicator_specs = [
        ("BATT_28V_LOW_LIGHT", "28V LOW LIGHT.png"),
        ("BATT_28V_DIS_LIGHT", "28V DIS LIGHT.png"),
        ("BATT_270V_LOW_LIGHT", "270V LOW LIGHT.png"),
        ("BATT_270V_DIS_LIGHT", "270V DIS LIGHT.png"),
    ]
    for state_key, filename in indicator_specs:
        if not bool(power.get(state_key, False)):
            continue
        src = _load_panel_button_image("POWER PANEL", filename)
        if src is None:
            continue
        sw = max(1, image_rect.width)
        sh = max(1, image_rect.height)
        scaled = pygame.transform.smoothscale(src, (sw, sh))
        screen.blit(scaled, image_rect.topleft)
    if _active_icaw_has("FIRE IPP"):
        src = _load_panel_overlay_image("POWER PANEL", "FIRE.png")
        if src is not None:
            sw = max(1, image_rect.width)
            sh = max(1, image_rect.height)
            scaled = pygame.transform.smoothscale(src, (sw, sh))
            screen.blit(scaled, image_rect.topleft)


def _draw_throttle_panel_buttons(screen: pygame.Surface, image_rect: pygame.Rect) -> None:
    state = _ensure_panel_button_states()
    throttle = state.get("THROTTLE", {})
    if not isinstance(throttle, dict):
        return
    for control in _THROTTLE_PANEL_BUTTON_RULES.keys():
        filename = _throttle_panel_button_image_filename(control, throttle)
        if filename == "":
            continue
        src = _load_panel_button_image("THROTTLE", filename)
        if src is None:
            continue
        draw_src = _button_image_rotated_cw_90("THROTTLE", filename, src)
        sw = max(1, image_rect.width)
        sh = max(1, image_rect.height)
        scaled = pygame.transform.smoothscale(draw_src, (sw, sh))
        screen.blit(scaled, image_rect.topleft)
        bbox = _button_alpha_bbox("THROTTLE", f"ROT_CW90::{filename}", draw_src)
        if bbox is None:
            continue
        sx = sw / float(max(1, draw_src.get_width()))
        sy = sh / float(max(1, draw_src.get_height()))
        hx = image_rect.left + int(round(bbox.x * sx))
        hy = image_rect.top + int(round(bbox.y * sy))
        hw = max(1, int(round(bbox.width * sx)))
        hh = max(1, int(round(bbox.height * sy)))
        _PANEL_RUNTIME_BUTTON_HITS.append(
            {
                "panel": "THROTTLE",
                "control": control,
                "rect": pygame.Rect(hx, hy, hw, hh),
            }
        )
    # Animated throttle handle overlay (non-clickable).
    handle_src = _load_panel_button_image("THROTTLE", "THROTTLE HANDLE.png")
    if handle_src is not None:
        draw_src = _button_image_rotated_cw_90("THROTTLE", "THROTTLE HANDLE.png", handle_src)
        sw = max(1, image_rect.width)
        sh = max(1, image_rect.height)
        scaled = pygame.transform.smoothscale(draw_src, (sw, sh))
        try:
            thrust = float(throttle.get("THROTTLE_POS", 0.0))
        except Exception:
            thrust = 0.0
        frac = max(0.0, min(1.0, thrust / 150.0))
        dx = int(round(THROTTLE_HANDLE_MAX_DX_PX * frac))
        dy = int(round(THROTTLE_HANDLE_MAX_DY_PX * frac))
        screen.blit(scaled, (image_rect.left + dx, image_rect.top + dy))


def _set_manual_icaw_active(name: str, enabled: bool, severity_hint: Optional[str] = None) -> None:
    alert_name = str(name).strip()
    if alert_name == "":
        return
    alert_name_up = alert_name.upper()
    state = getattr(formats, "ICAWS_STATE", {})
    if not isinstance(state, dict):
        return
    active = state.get("active", [])
    if not isinstance(active, list):
        active = []
    if not enabled:
        active = [
            item for item in active
            if not (
                (isinstance(item, dict) and str(item.get("text", "")).strip().upper() == alert_name_up)
                or ((not isinstance(item, dict)) and str(item).strip().upper() == alert_name_up)
            )
        ]
        state["active"] = active
        return
    for item in active:
        if isinstance(item, dict) and str(item.get("text", "")).strip().upper() == alert_name_up:
            state["active"] = active
            return
    sev = str(severity_hint or "").strip().lower()
    if sev not in {"warning", "caution", "advisory"}:
        try:
            sev = str(getattr(formats, "ICAWS_ALERT_DEFAULT_SEVERITY", {}).get(alert_name_up, "")).strip().lower()
        except Exception:
            sev = ""
    if sev not in {"warning", "caution", "advisory"}:
        sev = "caution"
    active.append({"text": alert_name, "severity": sev})
    state["active"] = active


def _set_power_panel_control(control: str, mouse_button: int, pressed: bool) -> None:
    state = _ensure_panel_button_states()
    power = state.get("POWER PANEL", {})
    if not isinstance(power, dict):
        return
    if control in {"BAT", "ICC1", "ICC2", "ICC3"} and pressed:
        current = str(power.get(control, "OFF")).upper()
        next_state = "ON" if current != "ON" else "OFF"
        power[control] = next_state
        if next_state != current:
            play_sound_effect("SWITCH")
        return
    if control == "CAB_PRESS" and pressed:
        current = str(power.get("CAB_PRESS", "NORM")).upper()
        next_mode = current
        if mouse_button == 1:
            # Left-click steps toward DUMP side: RAM -> NORM -> DUMP.
            if current == "RAM":
                next_mode = "NORM"
            elif current == "NORM":
                next_mode = "DUMP"
            else:
                next_mode = "DUMP"
        elif mouse_button == 3:
            # Right-click steps toward RAM side: DUMP -> NORM -> RAM.
            if current == "DUMP":
                next_mode = "NORM"
            elif current == "NORM":
                next_mode = "RAM"
            else:
                next_mode = "RAM"
        power["CAB_PRESS"] = next_mode
        if next_mode != current:
            play_sound_effect("SWITCH")
        return
    if control == "IPP":
        current_mode = str(power.get("IPP", "AUTO")).upper()
        next_mode = current_mode
        if pressed:
            if mouse_button == 1:
                next_mode = "OFF"
                _PANEL_ACTIVE_HOLDS[1] = ("POWER PANEL", "IPP")
            elif mouse_button == 3:
                next_mode = "START"
                _PANEL_ACTIVE_HOLDS[3] = ("POWER PANEL", "IPP")
        else:
            next_mode = "AUTO"
        power["IPP"] = next_mode
        if next_mode != current_mode:
            play_sound_effect("SWITCH")
        return
    if control == "EMER":
        power["EMER_PRESSED"] = bool(pressed)
        if pressed:
            power["IPP_ON"] = False
            power["IPP_ON_SINCE_MS"] = 0
            power["IPP_START_HOLD_MS"] = 0
            power["IPP_OFF_HOLD_MS"] = 0
            power["IPP_START_SEQ_END_MS"] = 0
            power["IPP_START_SEQ_SUCCESS"] = False
            power["IPP_START_BLOCKED"] = False
            power["IPP_SHUTDOWN_SEQ_END_MS"] = 0
            power["BATT_270V_DIS_ON"] = False
            _set_manual_icaw_active("FIRE IPP", False)
            _set_manual_icaw_active("FPS DISCHARGE", True)
            _PANEL_ACTIVE_HOLDS[mouse_button] = ("POWER PANEL", "EMER")
        return


def _set_throttle_panel_control(control: str, mouse_button: int, pressed: bool) -> None:
    state = _ensure_panel_button_states()
    throttle = state.get("THROTTLE", {})
    if not isinstance(throttle, dict):
        return
    if control == "CANOPY":
        if not pressed:
            return
        # Latched 3-position behavior (not momentary):
        # left click steps toward DOWN, right click steps toward UP.
        order = ["UP", "CENTER", "DOWN"]
        current = str(throttle.get("CANOPY", "CENTER")).upper()
        try:
            idx = order.index(current)
        except ValueError:
            idx = 1
        if mouse_button == 1:
            idx = min(len(order) - 1, idx + 1)
        elif mouse_button == 3:
            idx = max(0, idx - 1)
        next_mode = order[idx]
        throttle["CANOPY"] = next_mode
        if next_mode != current:
            play_sound_effect("SWITCH")
        return
    if control == "FCS_RESET":
        current = str(throttle.get("FCS_RESET", "DOWN")).upper()
        if pressed:
            if mouse_button == 3:
                next_mode = "UP"
            else:
                next_mode = "DOWN"
            throttle["FCS_RESET"] = next_mode
            _PANEL_ACTIVE_HOLDS[mouse_button] = ("THROTTLE", "FCS_RESET")
            if next_mode == "UP":
                throttle["RUDDER_TRIM_IN"] = 0.0
        else:
            next_mode = "DOWN"
            throttle["FCS_RESET"] = next_mode
        if next_mode != current:
            play_sound_effect("SWITCH")
        return
    if control == "ENGINE" and pressed:
        current = str(throttle.get("ENGINE", "OFF")).upper()
        order = ["RUN", "OFF", "MOTOR"]
        try:
            idx = order.index(current)
        except ValueError:
            idx = 1
        if mouse_button == 1:
            # Left click steps toward MOTOR side: RUN -> OFF -> MOTOR.
            idx = min(len(order) - 1, idx + 1)
        elif mouse_button == 3:
            # Right click steps toward RUN side: MOTOR -> OFF -> RUN.
            idx = max(0, idx - 1)
        next_mode = order[idx]
        throttle["ENGINE"] = next_mode
        if next_mode != current:
            play_sound_effect("SWITCH")
        return
    if control == "RUDDER":
        current = str(throttle.get("RUDDER", "CENTER")).upper()
        if pressed:
            if mouse_button == 3:
                next_mode = "RIGHT"
            else:
                next_mode = "LEFT"
            throttle["RUDDER"] = next_mode
            _PANEL_ACTIVE_HOLDS[mouse_button] = ("THROTTLE", "RUDDER")
        else:
            next_mode = "CENTER"
            throttle["RUDDER"] = next_mode
        if next_mode != current:
            play_sound_effect("SWITCH")
        return
    if control == "VS_BIT":
        if pressed:
            if bool(throttle.get("VS_BIT_RUNNING", False)):
                _vs_bit_reset_runtime(throttle)
                _vs_bit_set_result(throttle, "FN", ["VS BIT: ABORT-Pilot"])
                return
            power = state.get("POWER PANEL", {})
            console_left = state.get("CONSOLE LEFT", {})
            aircraft = state.get("AIRCRAFT", {})
            if not isinstance(power, dict) or not isinstance(console_left, dict) or not isinstance(aircraft, dict):
                _vs_bit_set_result(throttle, "FN", ["VS BIT: Not Available"])
                return
            start_ms = int(pygame.time.get_ticks())
            block_reasons = _vs_bit_start_block_reasons(throttle, power, console_left, aircraft, start_ms)
            if len(block_reasons) > 0:
                _vs_bit_set_result(throttle, "FN", block_reasons)
                return
            # Allow re-run to clear previous NO GO immediately.
            _vs_bit_set_result(throttle, "TS", [])
            throttle["VS_BIT_PRESSED"] = True
            throttle["VS_BIT_RUNNING"] = True
            throttle["VS_BIT_START_MS"] = start_ms
            throttle["VS_BIT_END_MS"] = start_ms + VS_BIT_DURATION_MS
            throttle["VS_BIT_HOLD_THROTTLE_POS"] = float(throttle.get("THROTTLE_POS", 0.0))
            throttle["VS_BIT_MANUAL_OVERRIDE"] = False
            throttle["VS_BIT_REFUEL_SEEN"] = False
            throttle["VS_BIT_THROTTLE_MOVED"] = False
            throttle["VS_BIT_CTRL_MOVED"] = False
            throttle["VS_BIT_ABORT_INPUT_SOURCE"] = ""
            throttle["VS_BIT_ABORT_INPUT_DETAIL"] = ""
            throttle["VS_BIT_HOTAS_LAST_CMD"] = None
            throttle["VS_BIT_EXPECT_REFUEL_OPEN"] = None
            throttle["VS_BIT_FCS_ACTIVE"] = True
            throttle["VS_BIT_FCS_STEP_IDX"] = 0
            throttle["VS_BIT_FCS_ACTION_DONE"] = False
            throttle["VS_BIT_FCS_NEXT_STEP_MS"] = 0
            # Start the automated V/S BIT throttle sweep from IDLE.
            throttle["THROTTLE_POS"] = 0.0
            door_sig = _weapon_door_signature(int(pygame.time.get_ticks()))
            throttle["VS_BIT_DOOR_SIG"] = door_sig
            throttle["VS_BIT_DOOR_MOVED"] = _vs_bit_weapon_door_no_go(door_sig)
            _PANEL_ACTIVE_HOLDS[mouse_button] = ("THROTTLE", "VS_BIT")
        else:
            throttle["VS_BIT_PRESSED"] = False
        return


def _set_display_control_panel_control(control: str, mouse_button: int, pressed: bool) -> None:
    if not pressed:
        return
    state = _ensure_panel_button_states()
    display = state.get("DISPLAY CONTROL", {})
    if not isinstance(display, dict):
        return
    if control == "BRT_DOWN":
        level = max(1, min(10, int(display.get("BRIGHTNESS_LEVEL", 10))))
        new_level = max(1, level - 1)
        display["BRIGHTNESS_LEVEL"] = int(new_level)
        if new_level != level:
            play_sound_effect("SWITCH")
        return
    if control == "BRT_UP":
        level = max(1, min(10, int(display.get("BRIGHTNESS_LEVEL", 10))))
        new_level = min(10, level + 1)
        display["BRIGHTNESS_LEVEL"] = int(new_level)
        if new_level != level:
            play_sound_effect("SWITCH")
        return
    if control == "MFD":
        order = ["OFF", "NIGHT", "DAY"]
        current = str(display.get("MFD_MODE", "DAY")).upper()
        try:
            idx = order.index(current)
        except ValueError:
            idx = 2
        if mouse_button == 1:
            idx = max(0, idx - 1)  # DAY -> NIGHT -> OFF
        elif mouse_button == 3:
            idx = min(len(order) - 1, idx + 1)  # OFF -> NIGHT -> DAY
        next_mode = order[idx]
        display["MFD_MODE"] = next_mode
        if next_mode != current:
            play_sound_effect("SWITCH")
        return


def _set_master_arm_panel_control(control: str, mouse_button: int, pressed: bool, pos: Optional[Tuple[int, int]] = None) -> None:
    global _PANEL_ACTIVE_DIAL_DRAG
    state = _ensure_panel_button_states()
    master_arm = state.get("MASTER ARM", {})
    if not isinstance(master_arm, dict):
        return
    if control == "MASTER_ARM":
        if not pressed:
            return
        current = str(master_arm.get("MASTER_ARM", "OFF")).upper()
        next_state = "ON" if current != "ON" else "OFF"
        master_arm["MASTER_ARM"] = next_state
        if next_state != current:
            play_sound_effect("SWITCH")
        return
    if control in {"DIAL_A", "DIAL_B", "DIAL_C"}:
        if pressed and pos is not None:
            _PANEL_ACTIVE_DIAL_DRAG = {
                "control": control,
                "button": int(mouse_button),
                "start_x": int(pos[0]),
                "start_y": int(pos[1]),
                "start_value": int(max(0, min(10, int(master_arm.get(control, 5))))),
                "last_value": int(max(0, min(10, int(master_arm.get(control, 5))))),
            }
        else:
            if _PANEL_ACTIVE_DIAL_DRAG is not None and str(_PANEL_ACTIVE_DIAL_DRAG.get("control", "")) == control:
                _PANEL_ACTIVE_DIAL_DRAG = None
        return


def _set_console_left_panel_control(control: str, mouse_button: int, pressed: bool) -> None:
    if not pressed:
        return
    state = _ensure_panel_button_states()
    console_left = state.get("CONSOLE LEFT", {})
    if not isinstance(console_left, dict):
        return
    if control == "PARKING_BRAKE":
        if mouse_button not in {1, 3}:
            return
        current = str(console_left.get("PARKING_BRAKE", "ON")).upper()
        next_state = "OFF" if current == "ON" else "ON"
        console_left["PARKING_BRAKE"] = next_state
        play_sound_effect("SWITCH")
        return
    if control == "GEAR":
        if mouse_button not in {1, 3}:
            return
        aircraft = state.get("AIRCRAFT", {})
        try:
            altitude_ft = float(aircraft.get("ALTITUDE_FT", aircraft.get("ALTITUDE_TARGET_FT", 0.0))) if isinstance(aircraft, dict) else 0.0
        except Exception:
            altitude_ft = 0.0
        # Weight-on-wheels / on-ground state mechanically blocks gear handle movement.
        if altitude_ft <= 0.0:
            print(f"[GEAR][BLOCK] on_ground altitude_ft={altitude_ft:.1f}")
            return
        current = str(console_left.get("GEAR", "DOWN_OFF")).upper()
        if current.startswith("UP"):
            next_state = "DOWN_ON"
        else:
            next_state = "UP_ON"
        print(f"[GEAR][CMD] {current}->{next_state} altitude_ft={altitude_ft:.1f}")
        console_left["GEAR"] = next_state
        now_ms = int(pygame.time.get_ticks())
        transition_dir = "UP" if next_state.startswith("UP") else "DOWN"
        # FIRE GEAR keeps handle in ON state while active.
        if _active_icaw_has("FIRE GEAR"):
            console_left["GEAR_TRANSITION_DUE_MS"] = 0
            console_left["GEAR_TRANSITION_START_MS"] = 0
            console_left["GEAR_TRANSITION_DIR"] = ""
            console_left["GEAR_TRANSITION_DURATION_MS"] = 0
        else:
            transition_ms = int(random.randint(CONSOLE_LEFT_GEAR_TRANSITION_MIN_MS, CONSOLE_LEFT_GEAR_TRANSITION_MAX_MS))
            console_left["GEAR_TRANSITION_DUE_MS"] = now_ms + transition_ms
            console_left["GEAR_TRANSITION_START_MS"] = now_ms
            console_left["GEAR_TRANSITION_DIR"] = transition_dir
            console_left["GEAR_TRANSITION_DURATION_MS"] = transition_ms
        play_sound_effect("SWITCH")
        return
    if control == "JETT":
        order = ["EXT", "SEL", "ALL"]
        current = str(console_left.get("JETT", "EXT")).upper()
        try:
            idx = order.index(current)
        except ValueError:
            idx = 0
        if mouse_button == 3:
            idx = min(len(order) - 1, idx + 1)
            next_mode = order[idx]
            console_left["JETT"] = next_mode
            if next_mode != current:
                play_sound_effect("SWITCH")
            return
        if mouse_button == 1:
            idx = max(0, idx - 1)
            next_mode = order[idx]
            console_left["JETT"] = next_mode
            if next_mode != current:
                play_sound_effect("SWITCH")
            return
        if mouse_button == 2:
            try:
                console_left["JETT_ACTIVATE_COUNT"] = int(console_left.get("JETT_ACTIVATE_COUNT", 0)) + 1
            except Exception:
                console_left["JETT_ACTIVATE_COUNT"] = 1
            console_left["JETT_LAST_ACTIVATE_MS"] = int(pygame.time.get_ticks())
            play_sound_effect("SWITCH")
            return


def _handle_panel_popup_mouse_drag(pos: Tuple[int, int], buttons: int) -> None:
    global _PANEL_ACTIVE_DIAL_DRAG
    drag = _PANEL_ACTIVE_DIAL_DRAG
    if not isinstance(drag, dict):
        return
    try:
        button = int(drag.get("button", 1))
    except Exception:
        button = 1
    if button == 1 and not (buttons & 1):
        _PANEL_ACTIVE_DIAL_DRAG = None
        return
    if button == 3 and not (buttons & 2):
        _PANEL_ACTIVE_DIAL_DRAG = None
        return
    control = str(drag.get("control", ""))
    if control not in {"DIAL_A", "DIAL_B", "DIAL_C"}:
        _PANEL_ACTIVE_DIAL_DRAG = None
        return
    try:
        sx = int(drag.get("start_x", int(pos[0])))
        sy = int(drag.get("start_y", int(pos[1])))
        base = int(drag.get("start_value", 5))
    except Exception:
        sx, sy, base = int(pos[0]), int(pos[1]), 5
    dx = int(pos[0]) - sx
    dy = int(pos[1]) - sy
    travel = dx if abs(dx) >= abs(dy) else -dy
    # Inverted drag polarity per panel request.
    delta = -int(round(travel / 22.0))
    new_val = max(0, min(10, base + delta))
    state = _ensure_panel_button_states()
    master_arm = state.get("MASTER ARM", {})
    if not isinstance(master_arm, dict):
        return
    prev_val = int(max(0, min(10, int(master_arm.get(control, base)))))
    master_arm[control] = int(new_val)
    if new_val != prev_val:
        play_sound_effect("SWITCH")
    drag["last_value"] = int(new_val)


def _display_control_brightness_multiplier() -> float:
    state = _ensure_panel_button_states()
    display = state.get("DISPLAY CONTROL", {})
    if not isinstance(display, dict):
        return 1.0
    mode = str(display.get("MFD_MODE", "DAY")).upper()
    if mode == "OFF":
        return 0.0
    try:
        level = int(display.get("BRIGHTNESS_LEVEL", 10))
    except Exception:
        level = 10
    level = max(1, min(10, level))
    mult = float(level) / 10.0
    if mode == "NIGHT":
        mult *= 0.75
    return max(0.0, min(1.0, mult))


def _is_refuel_door_open() -> bool:
    try:
        return bool(getattr(formats.FuelFormat, "_shared_refuel_t2_on", False)) or bool(getattr(formats.FuelFormat, "_shared_hazard_on", {}).get("R6", False))
    except Exception:
        return False


def _is_mf_sov_on() -> bool:
    try:
        return bool(getattr(formats.FuelFormat, "_shared_hazard_on", {}).get("L6", False))
    except Exception:
        return False


def _active_icaw_alerts() -> List[Tuple[str, str]]:
    try:
        raw = getattr(formats, "get_current_icaws_alerts", lambda: [])()
    except Exception:
        raw = []
    out: List[Tuple[str, str]] = []
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue
            name = str(item[0]).strip().upper()
            sev = str(item[1]).strip().lower()
            if name == "" or sev == "":
                continue
            out.append((name, sev))
    return out


def _active_icaw_names() -> set[str]:
    return {name for name, _ in _active_icaw_alerts()}


def _active_icaw_name_to_severity() -> Dict[str, str]:
    out: Dict[str, str] = {}
    rank = {"warning": 0, "caution": 1, "advisory": 2}
    for name, sev in _active_icaw_alerts():
        prev = out.get(name, "")
        if prev == "":
            out[name] = sev
            continue
        if rank.get(sev, 99) < rank.get(prev, 99):
            out[name] = sev
    return out


def _active_icaw_has(name: str) -> bool:
    target = str(name).strip().upper()
    if target == "":
        return False
    return target in _active_icaw_names()


def _active_icaw_display_degd_side() -> str:
    """
    Returns "LEFT", "RIGHT", "BOTH", or "" based on active DISPLAY DEGD
    bindings (PCD_L / PCD_R) emitted by formats ICAWS runtime.
    """
    key_candidates = (
        "DISPLAY DEGD|caution",
        "DISPLAY DEGD|warning",
        "DISPLAY DEGD|advisory",
    )
    try:
        bindings = getattr(formats, "ICAWS_STATE", {}).get("hrc_bindings", {})
    except Exception:
        bindings = {}
    if not isinstance(bindings, dict):
        bindings = {}

    left = False
    right = False
    for key in key_candidates:
        bind = bindings.get(key, {})
        if not isinstance(bind, dict):
            continue
        targets = bind.get("targets", [])
        if not isinstance(targets, list):
            continue
        for tgt in targets:
            name = str(tgt).strip().upper()
            if name == "PCD_L":
                left = True
            elif name == "PCD_R":
                right = True
    if left and right:
        return "BOTH"
    if left:
        return "LEFT"
    if right:
        return "RIGHT"
    return ""


def _weapon_door_signature(now_ms: int) -> str:
    try:
        sms = getattr(formats, "SMS_STATE", {})
        if not isinstance(sms, dict):
            return "CLOSE|CLOSE|CLOSE|CLOSE|0|0"
        lt_state = str(sms.get("lt_state", "CLOSE")).upper()
        rt_state = str(sms.get("rt_state", "CLOSE")).upper()
        lt_target = str(sms.get("lt_target", "CLOSE")).upper()
        rt_target = str(sms.get("rt_target", "CLOSE")).upper()
        lt_due = int(sms.get("lt_transition_due_ms", 0))
        rt_due = int(sms.get("rt_transition_due_ms", 0))
        lt_moving = 1 if lt_state == "PARTIAL" or lt_target != lt_state or lt_due > int(now_ms) else 0
        rt_moving = 1 if rt_state == "PARTIAL" or rt_target != rt_state or rt_due > int(now_ms) else 0
        return f"{lt_state}|{rt_state}|{lt_target}|{rt_target}|{lt_moving}|{rt_moving}"
    except Exception:
        return "CLOSE|CLOSE|CLOSE|CLOSE|0|0"


def _vs_bit_weapon_door_no_go(sig: str) -> bool:
    parts = [str(p).strip().upper() for p in str(sig).split("|")]
    if len(parts) < 6:
        return False
    lt_state, rt_state, lt_target, rt_target, lt_moving, rt_moving = parts[:6]
    closed = any(x.startswith("CLOSE") for x in (lt_state, rt_state, lt_target, rt_target))
    moving = (lt_moving == "1") or (rt_moving == "1")
    return bool(closed or moving)


def _clamp_fcs(v: float, lo: float, hi: float) -> float:
    return max(float(lo), min(float(hi), float(v)))


def _step_toward(current: float, target: float, max_step: float) -> float:
    cur = float(current)
    tgt = float(target)
    step = max(0.0, float(max_step))
    if cur < tgt:
        return min(cur + step, tgt)
    if cur > tgt:
        return max(cur - step, tgt)
    return cur


def _vec_dot3(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    return (float(a[0]) * float(b[0])) + (float(a[1]) * float(b[1])) + (float(a[2]) * float(b[2]))


def _vec_cross3(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (
        (float(a[1]) * float(b[2])) - (float(a[2]) * float(b[1])),
        (float(a[2]) * float(b[0])) - (float(a[0]) * float(b[2])),
        (float(a[0]) * float(b[1])) - (float(a[1]) * float(b[0])),
    )


def _vec_norm3(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
    x = float(v[0])
    y = float(v[1])
    z = float(v[2])
    n = math.sqrt((x * x) + (y * y) + (z * z))
    if n <= 1e-12:
        return (0.0, 0.0, 0.0)
    inv = 1.0 / n
    return (x * inv, y * inv, z * inv)


def _quat_normalize(q: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    w = float(q[0])
    x = float(q[1])
    y = float(q[2])
    z = float(q[3])
    n = math.sqrt((w * w) + (x * x) + (y * y) + (z * z))
    if n <= 1e-12:
        return (1.0, 0.0, 0.0, 0.0)
    inv = 1.0 / n
    return (w * inv, x * inv, y * inv, z * inv)


def _quat_mul(
    q1: Tuple[float, float, float, float],
    q2: Tuple[float, float, float, float],
) -> Tuple[float, float, float, float]:
    w1, x1, y1, z1 = float(q1[0]), float(q1[1]), float(q1[2]), float(q1[3])
    w2, x2, y2, z2 = float(q2[0]), float(q2[1]), float(q2[2]), float(q2[3])
    return (
        (w1 * w2) - (x1 * x2) - (y1 * y2) - (z1 * z2),
        (w1 * x2) + (x1 * w2) + (y1 * z2) - (z1 * y2),
        (w1 * y2) - (x1 * z2) + (y1 * w2) + (z1 * x2),
        (w1 * z2) + (x1 * y2) - (y1 * x2) + (z1 * w2),
    )


def _quat_conjugate(q: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    return (float(q[0]), -float(q[1]), -float(q[2]), -float(q[3]))


def _quat_from_axis_angle(axis: Tuple[float, float, float], angle_rad: float) -> Tuple[float, float, float, float]:
    ax, ay, az = float(axis[0]), float(axis[1]), float(axis[2])
    n = math.sqrt((ax * ax) + (ay * ay) + (az * az))
    if n <= 1e-12 or abs(float(angle_rad)) <= 1e-12:
        return (1.0, 0.0, 0.0, 0.0)
    half = 0.5 * float(angle_rad)
    s = math.sin(half) / n
    return _quat_normalize((math.cos(half), ax * s, ay * s, az * s))


def _quat_rotate_vec(
    q: Tuple[float, float, float, float],
    v: Tuple[float, float, float],
) -> Tuple[float, float, float]:
    # Fast quaternion-vector rotation: v' = v + w*t + cross(q_vec, t), t=2*cross(q_vec,v)
    w, x, y, z = float(q[0]), float(q[1]), float(q[2]), float(q[3])
    vx, vy, vz = float(v[0]), float(v[1]), float(v[2])
    tx = 2.0 * ((y * vz) - (z * vy))
    ty = 2.0 * ((z * vx) - (x * vz))
    tz = 2.0 * ((x * vy) - (y * vx))
    return (
        vx + (w * tx) + ((y * tz) - (z * ty)),
        vy + (w * ty) + ((z * tx) - (x * tz)),
        vz + (w * tz) + ((x * ty) - (y * tx)),
    )


def _quat_from_basis(
    right: Tuple[float, float, float],
    forward: Tuple[float, float, float],
    up: Tuple[float, float, float],
) -> Tuple[float, float, float, float]:
    # Rotation matrix columns are body axes expressed in world space:
    # X/right, Y/forward, Z/up.
    m00, m10, m20 = float(right[0]), float(right[1]), float(right[2])
    m01, m11, m21 = float(forward[0]), float(forward[1]), float(forward[2])
    m02, m12, m22 = float(up[0]), float(up[1]), float(up[2])
    trace = m00 + m11 + m22
    if trace > 0.0:
        s = math.sqrt(trace + 1.0) * 2.0
        w = 0.25 * s
        x = (m21 - m12) / s
        y = (m02 - m20) / s
        z = (m10 - m01) / s
    elif m00 > m11 and m00 > m22:
        s = math.sqrt(max(1e-12, 1.0 + m00 - m11 - m22)) * 2.0
        w = (m21 - m12) / s
        x = 0.25 * s
        y = (m01 + m10) / s
        z = (m02 + m20) / s
    elif m11 > m22:
        s = math.sqrt(max(1e-12, 1.0 + m11 - m00 - m22)) * 2.0
        w = (m02 - m20) / s
        x = (m01 + m10) / s
        y = 0.25 * s
        z = (m12 + m21) / s
    else:
        s = math.sqrt(max(1e-12, 1.0 + m22 - m00 - m11)) * 2.0
        w = (m10 - m01) / s
        x = (m02 + m20) / s
        y = (m12 + m21) / s
        z = 0.25 * s
    return _quat_normalize((w, x, y, z))


def _quat_body_rates_dps(
    q_prev: Tuple[float, float, float, float],
    q_curr: Tuple[float, float, float, float],
    dt_sec: float,
) -> Tuple[float, float, float]:
    dt = float(dt_sec)
    if dt <= 1e-9:
        return (0.0, 0.0, 0.0)
    # q_curr = q_prev * dq_body -> dq_body = conj(q_prev) * q_curr
    dq = _quat_mul(_quat_conjugate(_quat_normalize(q_prev)), _quat_normalize(q_curr))
    dq = _quat_normalize(dq)
    w, x, y, z = float(dq[0]), float(dq[1]), float(dq[2]), float(dq[3])
    if w < 0.0:
        w, x, y, z = -w, -x, -y, -z
    v_norm = math.sqrt((x * x) + (y * y) + (z * z))
    if v_norm <= 1e-12:
        return (0.0, 0.0, 0.0)
    angle = 2.0 * math.atan2(v_norm, max(-1.0, min(1.0, w)))
    if angle > math.pi:
        angle -= (2.0 * math.pi)
    inv_v = 1.0 / v_norm
    ax, ay, az = x * inv_v, y * inv_v, z * inv_v
    scale = (180.0 / math.pi) * (angle / dt)
    # Body axes mapping in this sim:
    #   X = pitch, Y = roll, Z = yaw
    return (ax * scale, az * scale, ay * scale)


def _sync_fcs_control_overlay_state(throttle: Dict[str, object], aircraft: Dict[str, object]) -> None:
    max_defl = max(1e-6, float(FLIGHT_CONTROL_MAX_DEG))

    def _norm(key: str) -> float:
        return _clamp_fcs(float(aircraft.get(key, 0.0)) / max_defl, -1.0, 1.0)

    try:
        trim_in = float(throttle.get("RUDDER_TRIM_IN", 0.0))
    except Exception:
        trim_in = 0.0
    trim_in = _clamp_fcs(trim_in, -FCS_SYMBOL_MAX_OFFSET_IN, FCS_SYMBOL_MAX_OFFSET_IN)

    top_x_in = _clamp_fcs(_norm("r_aileron") * FCS_SYMBOL_MAX_OFFSET_IN, -FCS_SYMBOL_MAX_OFFSET_IN, FCS_SYMBOL_MAX_OFFSET_IN)
    top_y_in = _clamp_fcs(-_norm("l_elevator") * FCS_SYMBOL_MAX_OFFSET_IN, -FCS_SYMBOL_MAX_OFFSET_IN, FCS_SYMBOL_MAX_OFFSET_IN)
    rud_cmd_norm = (_norm("l_rudder") + _norm("r_rudder")) * 0.5
    rud_cmd_in = _clamp_fcs(rud_cmd_norm * FCS_SYMBOL_MAX_OFFSET_IN, -FCS_SYMBOL_MAX_OFFSET_IN, FCS_SYMBOL_MAX_OFFSET_IN)
    bottom_cyan_x_in = _clamp_fcs(trim_in + rud_cmd_in, -FCS_SYMBOL_MAX_OFFSET_IN, FCS_SYMBOL_MAX_OFFSET_IN)

    throttle["RUDDER_TRIM_IN"] = float(trim_in)
    aircraft["fcs_top_cyan_x_in"] = float(top_x_in)
    aircraft["fcs_top_cyan_y_in"] = float(top_y_in)
    aircraft["fcs_bottom_cyan_x_in"] = float(bottom_cyan_x_in)
    aircraft["fcs_rudder_trim_in"] = float(trim_in)
    try:
        formats.FCS_STATE["top_cyan_x_in"] = float(top_x_in)
        formats.FCS_STATE["top_cyan_y_in"] = float(top_y_in)
        formats.FCS_STATE["bottom_cyan_x_in"] = float(bottom_cyan_x_in)
        formats.FCS_STATE["rudder_trim_in"] = float(trim_in)
    except Exception:
        pass


def _set_vs_bit_refuel_doors_open(target_open: bool) -> None:
    try:
        # VS BIT drives the refuel doors via R6; keep T2 path disabled here.
        setattr(formats.FuelFormat, "_shared_refuel_t2_on", False)
        hazard_on = getattr(formats.FuelFormat, "_shared_hazard_on", None)
        if isinstance(hazard_on, dict):
            hazard_on["R6"] = bool(target_open)
        cover_closed = getattr(formats.FuelFormat, "_shared_hazard_cover_closed", None)
        if isinstance(cover_closed, dict):
            cover_closed["R6"] = not bool(target_open)
    except Exception:
        pass


def _force_refuel_doors_closed() -> None:
    try:
        setattr(formats.FuelFormat, "_shared_refuel_t2_on", False)
        hazard_on = getattr(formats.FuelFormat, "_shared_hazard_on", None)
        if isinstance(hazard_on, dict):
            hazard_on["R6"] = False
        cover_closed = getattr(formats.FuelFormat, "_shared_hazard_cover_closed", None)
        if isinstance(cover_closed, dict):
            cover_closed["R6"] = True
    except Exception:
        pass


def _vs_bit_reset_runtime(throttle: Dict[str, object]) -> None:
    throttle["VS_BIT_RUNNING"] = False
    throttle["VS_BIT_PRESSED"] = False
    throttle["VS_BIT_START_MS"] = 0
    throttle["VS_BIT_END_MS"] = 0
    throttle["VS_BIT_HOLD_THROTTLE_POS"] = 0.0
    throttle["VS_BIT_MANUAL_OVERRIDE"] = False
    throttle["VS_BIT_REFUEL_SEEN"] = False
    throttle["VS_BIT_DOOR_MOVED"] = False
    throttle["VS_BIT_THROTTLE_MOVED"] = False
    throttle["VS_BIT_CTRL_MOVED"] = False
    throttle["VS_BIT_DOOR_SIG"] = ""
    throttle["VS_BIT_EXPECT_REFUEL_OPEN"] = None
    throttle["VS_BIT_FCS_ACTIVE"] = False
    throttle["VS_BIT_FCS_STEP_IDX"] = 0
    throttle["VS_BIT_FCS_ACTION_DONE"] = False
    throttle["VS_BIT_FCS_NEXT_STEP_MS"] = 0
    throttle["VS_BIT_HOTAS_LAST_CMD"] = None
    throttle["VS_BIT_ABORT_INPUT_SOURCE"] = ""
    throttle["VS_BIT_ABORT_INPUT_DETAIL"] = ""
    _force_refuel_doors_closed()


def _vs_bit_reason_detail_text(reason: str, throttle: Dict[str, object]) -> str:
    raw = str(reason).strip()
    panel = _ensure_panel_button_states()
    power = panel.get("POWER PANEL", {}) if isinstance(panel, dict) else {}
    console_left = panel.get("CONSOLE LEFT", {}) if isinstance(panel, dict) else {}
    aircraft = panel.get("AIRCRAFT", {}) if isinstance(panel, dict) else {}

    try:
        now_ms = int(pygame.time.get_ticks())
    except Exception:
        now_ms = 0

    if raw == "VS BIT: ABORT-Pilot":
        return "_set_throttle_panel_control(VS_BIT): pilot pressed VS BIT while it was already running."
    if raw == "VS BIT: ABORT-HOTAS":
        throttle_moved = bool(throttle.get("VS_BIT_THROTTLE_MOVED", False))
        ctrl_moved = bool(throttle.get("VS_BIT_CTRL_MOVED", False))
        source = str(throttle.get("VS_BIT_ABORT_INPUT_SOURCE", "")).strip()
        detail = str(throttle.get("VS_BIT_ABORT_INPUT_DETAIL", "")).strip()
        if detail == "":
            detail = "no captured input detail"
        return (
            "_update_user_flight_controls(): manual input detected during VS BIT "
            f"(THROTTLE_MOVED={throttle_moved}, CTRL_MOVED={ctrl_moved}, SOURCE={source or 'UNKNOWN'}, DETAIL={detail})."
        )
    if raw == "VS BIT: ABORT-Engine Off":
        engine_mode = str(throttle.get("ENGINE", "OFF")).upper()
        return f"VS BIT runtime loop: engine mode is {engine_mode} (expected RUN)."
    if raw == "VS BIT: In Motion":
        try:
            speed = float(aircraft.get("AIRSPEED_KTS", 0.0)) if isinstance(aircraft, dict) else 0.0
        except Exception:
            speed = 0.0
        return f"_vs_bit_start_block_reasons(): abs(AIRSPEED_KTS)={abs(speed):.2f} > 0.1."
    if raw == "VS BIT: Parking Brake":
        parking_brake = str(console_left.get("PARKING_BRAKE", "ON")).upper() if isinstance(console_left, dict) else "ON"
        return f"_vs_bit_start_block_reasons(): PARKING_BRAKE={parking_brake} (expected ON)."
    if raw == "VS BIT: Fuel-Def Vlv Open":
        return f"_vs_bit_start_block_reasons(): _is_refuel_door_open()={bool(_is_refuel_door_open())}."
    if raw == "VS BIT: ETR to Idle":
        try:
            throttle_pos = float(throttle.get("THROTTLE_POS", 0.0))
        except Exception:
            throttle_pos = 0.0
        return f"_vs_bit_start_block_reasons(): THROTTLE_POS={throttle_pos:.2f} > 1.0 while engine ready."
    if raw == "VS BIT: Pilot Delay":
        engine_mode = str(throttle.get("ENGINE", "OFF")).upper()
        spool_mode = str(throttle.get("ENGINE_SPOOL_MODE", "OFF")).upper()
        try:
            spool = float(throttle.get("ENGINE_SPOOL", 0.0))
        except Exception:
            spool = 0.0
        idle_since = int(throttle.get("VS_BIT_IDLE_SINCE_MS", 0))
        idle_elapsed = max(0, now_ms - idle_since) if idle_since > 0 else 0
        engine_ready = bool(engine_mode == "RUN" and spool_mode == "RUN" and spool >= 0.99)
        if not engine_ready:
            return (
                "_vs_bit_start_block_reasons(): engine not ready "
                f"(ENGINE={engine_mode}, ENGINE_SPOOL_MODE={spool_mode}, ENGINE_SPOOL={spool:.3f})."
            )
        return (
            "_vs_bit_start_block_reasons(): idle stability timer not met "
            f"(idle_elapsed_ms={idle_elapsed}, required_ms={VS_BIT_IDLE_STABLE_REQUIRED_MS})."
        )
    if raw == "VS BIT: FAIL-FLCS":
        refuel_seen = bool(throttle.get("VS_BIT_REFUEL_SEEN", False))
        door_moved = bool(throttle.get("VS_BIT_DOOR_MOVED", False))
        return (
            "VS BIT finalization: refuel/weapon-door condition triggered "
            f"(VS_BIT_REFUEL_SEEN={refuel_seen}, VS_BIT_DOOR_MOVED={door_moved})."
        )
    if raw == "VS BIT: Not Available":
        bat_active = bool(power.get("BAT_ACTIVE", False)) if isinstance(power, dict) else False
        return f"_vs_bit_start_block_reasons(): BAT_ACTIVE={bat_active}."

    reason_to_system = {
        "VS BIT: FAIL-FLCS": "FCS",
        "VS BIT: FAIL-Fuel": "FUEL",
        "VS BIT: FAIL-FPS": "FPS",
        "VS BIT: FAIL-HUA": "HYD",
        "VS BIT: FAIL-LGS": "GEAR",
        "VS BIT: FAIL-Prop": "PROP",
        "VS BIT: FAIL-PTMS": "PTMS",
    }
    if raw in reason_to_system:
        system_name = reason_to_system[raw]
        status_map = _vs_bit_vehicle_status_map()
        status = str(status_map.get(system_name, "")).upper()
        phm_status = panel.get("PHM STATUS", {}) if isinstance(panel, dict) else {}
        hrc_events = phm_status.get("hrc_events", {}) if isinstance(phm_status, dict) else {}
        fna_events = phm_status.get("fna_events", {}) if isinstance(phm_status, dict) else {}
        subsystem_keys = []
        try:
            subsystem_keys = list(getattr(formats, "PHM_SYSTEM_SUBSYSTEMS", {}).get(system_name, []))
        except Exception:
            subsystem_keys = []
        event_keys = [system_name] + [str(x) for x in subsystem_keys]
        active_hrc: Dict[str, List[str]] = {}
        active_fna: Dict[str, List[str]] = {}
        if isinstance(hrc_events, dict):
            for key in event_keys:
                vals = hrc_events.get(key, [])
                if isinstance(vals, list):
                    clean_vals = [str(v).strip() for v in vals if str(v).strip() != ""]
                    if len(clean_vals) > 0:
                        active_hrc[str(key)] = clean_vals
        if isinstance(fna_events, dict):
            for key in event_keys:
                vals = fna_events.get(key, [])
                if isinstance(vals, list):
                    clean_vals = [str(v).strip() for v in vals if str(v).strip() != ""]
                    if len(clean_vals) > 0:
                        active_fna[str(key)] = clean_vals
        return (
            "_vs_bit_collect_system_fail_reasons(): "
            f"{system_name} status is '{status}' (bad statuses: HR, ??, NC, OF); "
            f"active_hrc={active_hrc}; active_fna={active_fna}."
        )
    reason_icaw_sources: Dict[str, List[str]] = {
        "VS BIT: No EHA 270V": ["BATT FAIL 270V", "EPS FAIL 270V"],
        "VS BIT: FAIL-PTMS": ["BLD LEAK ENG", "BLD LEAK IPP"],
        "VS BIT: FAIL-Prop": ["ENG COMM FAIL", "ENG FADEC FAIL", "FLAMEOUT"],
        "VS BIT: EHA Temp-HOT": ["FCS CH HOT A", "FCS CH HOT B", "FCS CH HOT C"],
        "VS BIT: FAIL-FPS": ["FIRE CM BAY", "FIRE ENG", "FIRE GEAR", "FIRE IPP", "FIRE WPN BAY L", "FIRE WPN BAY R", "FPS DETECT DEGD"],
        "VS BIT: FAIL-Fuel": ["FUEL DEGD", "FUEL DUMP OPEN", "REFUEL DOOR"],
        "VS BIT: No HYD A-HTCA": ["HYD FAIL A", "HYD FLUID A"],
        "VS BIT: No HYD B-NWS": ["HYD FAIL B", "HYD FLUID B"],
        "VS BIT: NWS Out of Range": ["NWS FAIL"],
        "VS BIT: Stick Passive": ["STICK JAMMED"],
        "VS BIT: Throttle Passive": ["THROTTLE JAMMED"],
    }
    if raw in reason_icaw_sources:
        active = _active_icaw_names()
        src = [name for name in reason_icaw_sources[raw] if name in active]
        return f"_vs_bit_collect_system_fail_reasons(): active ICAW triggers={src}."
    return "No additional detail available."


def _vs_bit_log_no_go_reasons(throttle: Dict[str, object], reasons: List[str]) -> None:
    clean_reasons = [str(r).strip() for r in reasons if str(r).strip() != ""]
    if len(clean_reasons) <= 0:
        return
    stamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{stamp}] [VS BIT][ERROR] NO GO ({len(clean_reasons)} reason(s))")
    for idx, reason in enumerate(clean_reasons, start=1):
        detail = _vs_bit_reason_detail_text(reason, throttle)
        print(f"[{stamp}] [VS BIT][ERROR] {idx}. {reason} :: {detail}")


def _vs_bit_set_result(throttle: Dict[str, object], status: str, reasons: Optional[List[str]] = None) -> None:
    s = str(status).upper()
    if s not in {"OK", "TS", "FN"}:
        s = "FN"
    clean_reasons = [str(r) for r in (reasons or []) if str(r).strip() != ""]
    clean_reasons = list(dict.fromkeys(clean_reasons))
    throttle["VS_BIT_STATUS"] = s
    throttle["VS_BIT_FAIL_REASONS"] = clean_reasons
    throttle["VS_BIT_NO_GO"] = bool(s == "FN")
    throttle["VS_BIT_LAST_RESULT_MS"] = int(pygame.time.get_ticks())
    throttle["VS_BIT_REASON_CATALOG"] = list(clean_reasons)
    if s == "FN":
        _vs_bit_log_no_go_reasons(throttle, clean_reasons)


def _vs_bit_vehicle_status_map() -> Dict[str, str]:
    try:
        rows = formats.PhmFormat._vehicle_systems()
    except Exception:
        rows = []
    out: Dict[str, str] = {}
    if isinstance(rows, list):
        for item in rows:
            if not isinstance(item, tuple) or len(item) < 2:
                continue
            out[str(item[0]).upper()] = str(item[1]).upper()
    return out


def _vs_bit_collect_system_fail_reasons() -> List[str]:
    bad_status = {"HR", "??", "NC", "OF"}
    system_reason_map = {
        "FCS": "VS BIT: FAIL-FLCS",
        "FUEL": "VS BIT: FAIL-Fuel",
        "FPS": "VS BIT: FAIL-FPS",
        "HYD": "VS BIT: FAIL-HUA",
        "GEAR": "VS BIT: FAIL-LGS",
        "PROP": "VS BIT: FAIL-Prop",
        "PTMS": "VS BIT: FAIL-PTMS",
    }
    status_map = _vs_bit_vehicle_status_map()
    reasons: List[str] = []
    for sys_name, reason in system_reason_map.items():
        status = str(status_map.get(sys_name, "")).upper()
        if status in bad_status:
            reasons.append(reason)

    # Explicit ICAW-driven NO GO mappings.
    icaw_reason_map = {
        "BATT FAIL 270V": "VS BIT: No EHA 270V",
        "BLD LEAK ENG": "VS BIT: FAIL-PTMS",
        "BLD LEAK IPP": "VS BIT: FAIL-PTMS",
        "ENG COMM FAIL": "VS BIT: FAIL-Prop",
        "ENG FADEC FAIL": "VS BIT: FAIL-Prop",
        "EPS FAIL 270V": "VS BIT: No EHA 270V",
        "FCS CG DEGD": "VS BIT: FAIL-FLCS",
        "FCS CH FAIL A": "VS BIT: FAIL-FLCS",
        "FCS CH FAIL B": "VS BIT: FAIL-FLCS",
        "FCS CH FAIL C": "VS BIT: FAIL-FLCS",
        "FCS CH HOT A": "VS BIT: EHA Temp-HOT",
        "FCS CH HOT B": "VS BIT: EHA Temp-HOT",
        "FCS CH HOT C": "VS BIT: EHA Temp-HOT",
        "FCS DATA FAIL": "VS BIT: FAIL-FLCS",
        "FCS SURFACE FAIL": "VS BIT: FAIL-FLCS",
        "FIRE CM BAY": "VS BIT: FAIL-FPS",
        "FIRE ENG": "VS BIT: FAIL-FPS",
        "FIRE GEAR": "VS BIT: FAIL-FPS",
        "FIRE IPP": "VS BIT: FAIL-FPS",
        "FIRE WPN BAY L": "VS BIT: FAIL-FPS",
        "FIRE WPN BAY R": "VS BIT: FAIL-FPS",
        "FLAMEOUT": "VS BIT: FAIL-Prop",
        "FPS DETECT DEGD": "VS BIT: FAIL-FPS",
        "FUEL DEGD": "VS BIT: FAIL-Fuel",
        "FUEL DUMP OPEN": "VS BIT: FAIL-Fuel",
        "HYD FAIL A": "VS BIT: No HYD A-HTCA",
        "HYD FAIL B": "VS BIT: No HYD B-NWS",
        "HYD FLUID A": "VS BIT: No HYD A-HTCA",
        "HYD FLUID B": "VS BIT: No HYD B-NWS",
        "NWS FAIL": "VS BIT: NWS Out of Range",
        "REFUEL DOOR": "VS BIT: FAIL-Fuel",
        "RUDDER FAIL DUAL": "VS BIT: FAIL-FLCS",
        "RUDDER FAIL FUAL": "VS BIT: FAIL-FLCS",
        "STAB FAIL": "VS BIT: FAIL-FLCS",
        "STICK JAMMED": "VS BIT: Stick Passive",
        "THROTTLE JAMMED": "VS BIT: Throttle Passive",
    }
    active = _active_icaw_names()
    for icaw_name, reason in icaw_reason_map.items():
        if icaw_name in active:
            reasons.append(reason)
    return reasons


def _vs_bit_start_block_reasons(
    throttle: Dict[str, object],
    power: Dict[str, object],
    console_left: Dict[str, object],
    aircraft: Dict[str, object],
    now_ms: int,
) -> List[str]:
    if not bool(power.get("BAT_ACTIVE", False)):
        return ["VS BIT: Not Available"]
    engine_mode = str(throttle.get("ENGINE", "OFF")).upper()
    spool_mode = str(throttle.get("ENGINE_SPOOL_MODE", "OFF")).upper()
    try:
        spool = float(throttle.get("ENGINE_SPOOL", 0.0))
    except Exception:
        spool = 0.0
    try:
        throttle_pos = float(throttle.get("THROTTLE_POS", 0.0))
    except Exception:
        throttle_pos = 0.0
    try:
        speed = float(aircraft.get("AIRSPEED_KTS", 0.0))
    except Exception:
        speed = 0.0
    parking_brake = str(console_left.get("PARKING_BRAKE", "ON")).upper()
    reasons: List[str] = []
    if abs(speed) > 0.1:
        reasons.append("VS BIT: In Motion")
    if parking_brake != "ON":
        reasons.append("VS BIT: Parking Brake")
    if bool(_is_refuel_door_open()):
        reasons.append("VS BIT: Fuel-Def Vlv Open")

    engine_ready = bool(engine_mode == "RUN" and spool_mode == "RUN" and spool >= 0.99)
    if not engine_ready:
        reasons.append("VS BIT: Pilot Delay")
    elif throttle_pos > 1.0:
        reasons.append("VS BIT: ETR to Idle")
    else:
        idle_since = int(throttle.get("VS_BIT_IDLE_SINCE_MS", 0))
        if idle_since <= 0 or (now_ms - idle_since) < VS_BIT_IDLE_STABLE_REQUIRED_MS:
            reasons.append("VS BIT: Pilot Delay")
    return list(dict.fromkeys(reasons))


def _update_user_flight_controls(
    throttle: Dict[str, object],
    aircraft: Dict[str, object],
    held_keys: Optional[set[int]],
    dt_sec: float,
    hotas_axes: Optional[Dict[str, float]] = None,
) -> None:
    keys = held_keys if isinstance(held_keys, set) else set()
    rate_step = max(0.0, float(FLIGHT_CONTROL_MOVE_RATE_DPS) * max(0.0, float(dt_sec)))
    vs_bit_running = bool(throttle.get("VS_BIT_RUNNING", False))

    def _held(name: str) -> bool:
        return any(int(k) in keys for k in _FLIGHT_CTRL_MANUAL_KEYS.get(name, ()))

    elev_up = _held("elev_up")
    elev_down = _held("elev_down")
    ail_left = _held("ail_left")
    ail_right = _held("ail_right")
    rud_left = _held("rud_left")
    rud_right = _held("rud_right")
    axes = hotas_axes if isinstance(hotas_axes, dict) else {}
    try:
        axis_pitch = float(axes.get("pitch", 0.0))
    except Exception:
        axis_pitch = 0.0
    try:
        axis_yaw = float(axes.get("yaw", 0.0))
    except Exception:
        axis_yaw = 0.0
    try:
        axis_roll = float(axes.get("roll", 0.0))
    except Exception:
        axis_roll = 0.0
    axis_pitch = max(-1.0, min(1.0, axis_pitch))
    axis_yaw = max(-1.0, min(1.0, axis_yaw))
    axis_roll = max(-1.0, min(1.0, axis_roll))
    axis_dead = float(VS_BIT_CONTROL_ABORT_DEADZONE if vs_bit_running else 0.08)
    pitch_axis_active = abs(axis_pitch) > axis_dead
    yaw_axis_active = abs(axis_yaw) > axis_dead
    roll_axis_active = abs(axis_roll) > axis_dead
    stick_jammed = _active_icaw_has("STICK JAMMED")
    stab_fail = _active_icaw_has("STAB FAIL")
    rudder_fail_dual = _active_icaw_has("RUDDER FAIL DUAL") or _active_icaw_has("RUDDER FAIL FUAL")
    block_elev = bool(stick_jammed or stab_fail)
    block_ail = bool(stick_jammed)
    block_rud = bool(rudder_fail_dual)
    if stick_jammed:
        elev_up = False
        elev_down = False
        ail_left = False
        ail_right = False
    elif stab_fail:
        elev_up = False
        elev_down = False
    if rudder_fail_dual:
        rud_left = False
        rud_right = False
    any_manual = bool(elev_up or elev_down or ail_left or ail_right or rud_left or rud_right)
    if pitch_axis_active or yaw_axis_active or roll_axis_active:
        any_manual = True
    max_defl = float(FLIGHT_CONTROL_MAX_DEG)
    if vs_bit_running and any_manual:
        keys_down: List[str] = []
        if elev_up:
            keys_down.append("ELEV_UP")
        if elev_down:
            keys_down.append("ELEV_DOWN")
        if ail_left:
            keys_down.append("AIL_LEFT")
        if ail_right:
            keys_down.append("AIL_RIGHT")
        if rud_left:
            keys_down.append("RUD_LEFT")
        if rud_right:
            keys_down.append("RUD_RIGHT")
        ctrl_pos = (
            f"LE={float(aircraft.get('l_elevator', 0.0)):.2f},RE={float(aircraft.get('r_elevator', 0.0)):.2f},"
            f"LA={float(aircraft.get('l_aileron', 0.0)):.2f},RA={float(aircraft.get('r_aileron', 0.0)):.2f},"
            f"LR={float(aircraft.get('l_rudder', 0.0)):.2f},RR={float(aircraft.get('r_rudder', 0.0)):.2f}"
        )
        detail = (
            f"keys={keys_down if len(keys_down) > 0 else ['none']}; "
            f"axis(p={axis_pitch:.3f},y={axis_yaw:.3f},r={axis_roll:.3f},dead={axis_dead:.3f}); "
            f"axis_active(p={pitch_axis_active},y={yaw_axis_active},r={roll_axis_active}); "
            f"ctrl_pos[{ctrl_pos}]"
        )
        throttle["VS_BIT_CTRL_MOVED"] = True
        throttle["VS_BIT_ABORT_INPUT_SOURCE"] = "FLIGHT_CTRL"
        throttle["VS_BIT_ABORT_INPUT_DETAIL"] = detail
        _vs_bit_reset_runtime(throttle)
        # Preserve captured abort detail after runtime reset for error logging.
        throttle["VS_BIT_CTRL_MOVED"] = True
        throttle["VS_BIT_ABORT_INPUT_SOURCE"] = "FLIGHT_CTRL"
        throttle["VS_BIT_ABORT_INPUT_DETAIL"] = detail
        _vs_bit_set_result(throttle, "FN", ["VS BIT: ABORT-HOTAS"])
        vs_bit_running = False

    # When VS BIT is running:
    # - manual keys can still drive controls (and trigger failure),
    # - no-key state must not auto-center, so BIT sequence remains authoritative.
    skip_manual_update = bool(vs_bit_running and (not any_manual))

    elev_target = 0.0
    elev_active = False
    if pitch_axis_active:
        elev_target = max_defl * axis_pitch
        elev_active = True
    elif elev_up and (not elev_down):
        elev_target = max_defl
        elev_active = True
    elif elev_down and (not elev_up):
        elev_target = -max_defl
        elev_active = True

    # A: left up, right down. D: left down, right up.
    ail_l_target = 0.0
    ail_r_target = 0.0
    ail_active = False
    if roll_axis_active:
        ail_l_target = -max_defl * axis_roll
        ail_r_target = max_defl * axis_roll
        ail_active = True
    elif ail_left and (not ail_right):
        ail_l_target = max_defl
        ail_r_target = -max_defl
        ail_active = True
    elif ail_right and (not ail_left):
        ail_l_target = -max_defl
        ail_r_target = max_defl
        ail_active = True

    # Q: left rudder command. E: right rudder command.
    rud_l_target = 0.0
    rud_r_target = 0.0
    rud_active = False
    if yaw_axis_active:
        rud_l_target = max_defl * axis_yaw
        rud_r_target = max_defl * axis_yaw
        rud_active = True
    elif rud_left and (not rud_right):
        rud_l_target = -max_defl
        rud_r_target = -max_defl
        rud_active = True
    elif rud_right and (not rud_left):
        rud_l_target = max_defl
        rud_r_target = max_defl
        rud_active = True

    def _apply_target(key: str, target: float) -> None:
        cur = float(aircraft.get(key, 0.0))
        nxt = _step_toward(cur, target, rate_step)
        aircraft[key] = _clamp_fcs(nxt, -max_defl, max_defl)

    def _apply_instant(key: str, target: float) -> None:
        aircraft[key] = _clamp_fcs(target, -max_defl, max_defl)

    if skip_manual_update:
        _sync_fcs_control_overlay_state(throttle, aircraft)
        return

    if rate_step <= 0.0:
        # If time delta is unavailable, still honor pressed commands instantly.
        if elev_active:
            _apply_instant("l_elevator", elev_target)
            _apply_instant("r_elevator", elev_target)
        if ail_active:
            _apply_instant("l_aileron", ail_l_target)
            _apply_instant("r_aileron", ail_r_target)
        if rud_active:
            _apply_instant("l_rudder", rud_l_target)
            _apply_instant("r_rudder", rud_r_target)
        _sync_fcs_control_overlay_state(throttle, aircraft)
        return

    if ((not vs_bit_running) or elev_active) and (not block_elev):
        _apply_target("l_elevator", elev_target)
        _apply_target("r_elevator", elev_target)
    if ((not vs_bit_running) or ail_active) and (not block_ail):
        _apply_target("l_aileron", ail_l_target)
        _apply_target("r_aileron", ail_r_target)
    if ((not vs_bit_running) or rud_active) and (not block_rud):
        _apply_target("l_rudder", rud_l_target)
        _apply_target("r_rudder", rud_r_target)
    _sync_fcs_control_overlay_state(throttle, aircraft)


def _update_vs_bit_flight_controls(throttle: Dict[str, object], aircraft: Dict[str, object], dt_sec: float) -> None:
    if (not bool(throttle.get("VS_BIT_RUNNING", False))) or (not bool(throttle.get("VS_BIT_FCS_ACTIVE", False))):
        return
    lef_lock = _active_icaw_has("LEF LOCK")
    stick_jammed = _active_icaw_has("STICK JAMMED")
    stab_fail = _active_icaw_has("STAB FAIL")
    rudder_fail_dual = _active_icaw_has("RUDDER FAIL DUAL") or _active_icaw_has("RUDDER FAIL FUAL")
    block_elev = bool(stick_jammed or stab_fail)
    block_ail = bool(stick_jammed)
    block_rud = bool(rudder_fail_dual)
    now_ms = int(pygame.time.get_ticks())
    next_step_due = int(throttle.get("VS_BIT_FCS_NEXT_STEP_MS", 0))
    if next_step_due > now_ms:
        return
    step_idx = int(throttle.get("VS_BIT_FCS_STEP_IDX", 0))
    if step_idx >= len(_VS_BIT_FCS_SEQUENCE):
        throttle["VS_BIT_FCS_ACTIVE"] = False
        throttle["VS_BIT_FCS_NEXT_STEP_MS"] = 0
        return
    rate_step = max(0.0, float(FLIGHT_CONTROL_MOVE_RATE_DPS) * float(VS_BIT_FLIGHT_CONTROL_RATE_SCALE) * max(0.0, float(dt_sec)))
    step_data = _VS_BIT_FCS_SEQUENCE[step_idx]
    action_done = bool(throttle.get("VS_BIT_FCS_ACTION_DONE", False))

    refuel_cmd = step_data.get("refuel_open", None)
    if isinstance(refuel_cmd, bool) and (not action_done):
        _set_vs_bit_refuel_doors_open(bool(refuel_cmd))
        throttle["VS_BIT_EXPECT_REFUEL_OPEN"] = bool(refuel_cmd)
        action_done = True

    complete = True
    targets = step_data.get("targets", {})
    if isinstance(targets, dict) and len(targets) > 0:
        max_defl = float(FLIGHT_CONTROL_MAX_DEG)
        for k, v in targets.items():
            key = str(k)
            if key not in {
                "l_lef", "r_lef", "l_aileron", "r_aileron",
                "l_rudder", "r_rudder", "l_elevator", "r_elevator",
            }:
                continue
            if key in {"l_lef", "r_lef"} and lef_lock:
                continue
            if key in {"l_elevator", "r_elevator"} and block_elev:
                continue
            if key in {"l_aileron", "r_aileron"} and block_ail:
                continue
            if key in {"l_rudder", "r_rudder"} and block_rud:
                continue
            cur = float(aircraft.get(key, 0.0))
            tgt = _clamp_fcs(float(v), -max_defl, max_defl)
            nxt = _step_toward(cur, tgt, rate_step)
            aircraft[key] = float(nxt)
            if abs(nxt - tgt) > 1e-4:
                complete = False
    if isinstance(refuel_cmd, bool) and (not action_done):
        complete = False

    if complete:
        step_delay_ms = int(VS_BIT_FCS_STEP_DELAY_MS)
        try:
            if "delay_s" in step_data:
                step_delay_ms = int(round(max(0.0, float(step_data.get("delay_s", 0.0))) * 1000.0))
            elif "delay_ms" in step_data:
                step_delay_ms = int(round(max(0.0, float(step_data.get("delay_ms", 0.0)))))
        except Exception:
            step_delay_ms = int(VS_BIT_FCS_STEP_DELAY_MS)
        step_idx += 1
        throttle["VS_BIT_FCS_STEP_IDX"] = int(step_idx)
        throttle["VS_BIT_FCS_ACTION_DONE"] = False
        if step_idx >= len(_VS_BIT_FCS_SEQUENCE):
            throttle["VS_BIT_FCS_ACTIVE"] = False
            throttle["VS_BIT_FCS_NEXT_STEP_MS"] = 0
        else:
            throttle["VS_BIT_FCS_NEXT_STEP_MS"] = int(now_ms + max(0, step_delay_ms))
    else:
        throttle["VS_BIT_FCS_STEP_IDX"] = int(step_idx)
        throttle["VS_BIT_FCS_ACTION_DONE"] = bool(action_done)


def _update_panel_runtime(
    now_ms: int,
    dt_sec: float,
    held_keys: Optional[set[int]] = None,
    pmd_dr_state: Optional[Dict[str, object]] = None,
) -> None:
    state = _ensure_panel_button_states()
    power = state.get("POWER PANEL", {})
    throttle = state.get("THROTTLE", {})
    console_left = state.get("CONSOLE LEFT", {})
    aircraft = state.get("AIRCRAFT", {})
    if not isinstance(power, dict) or not isinstance(throttle, dict) or not isinstance(console_left, dict):
        return
    if not isinstance(aircraft, dict):
        aircraft = {}
        state["AIRCRAFT"] = aircraft
    for k in (
        "l_lef", "r_lef", "l_aileron", "r_aileron",
        "l_rudder", "r_rudder", "l_elevator", "r_elevator",
    ):
        aircraft.setdefault(k, 0.0)

    active_icaws = _active_icaw_names()
    fuel_available = bool(_fuel_feed_available())
    fire_eng_active = "FIRE ENG" in active_icaws
    flameout_active = "FLAMEOUT" in active_icaws
    ipp_fail_active = "IPP FAIL" in active_icaws
    lef_lock_active = "LEF LOCK" in active_icaws
    if fire_eng_active or flameout_active:
        throttle["ENGINE"] = "OFF"
    if ipp_fail_active:
        power["IPP"] = "OFF"
        power["IPP_ON"] = False
        power["IPP_ON_SINCE_MS"] = 0
        power["IPP_START_HOLD_MS"] = 0
        power["IPP_OFF_HOLD_MS"] = 0
        power["IPP_START_SEQ_END_MS"] = 0
        power["IPP_START_SEQ_SUCCESS"] = False
        power["IPP_START_BLOCKED"] = False
        power["IPP_SHUTDOWN_SEQ_END_MS"] = 0
        power["BATT_270V_DIS_ON"] = False
        power["BATT_270V_BIT_FLASH_UNTIL_MS"] = 0
    if not fuel_available:
        # No fuel feed available: IPP/engine cannot sustain operation.
        throttle["ENGINE"] = "OFF"
        power["IPP_ON"] = False
        power["IPP_ON_SINCE_MS"] = 0
        power["IPP_START_HOLD_MS"] = 0
        power["IPP_OFF_HOLD_MS"] = 0
        power["IPP_START_SEQ_END_MS"] = 0
        power["IPP_START_SEQ_SUCCESS"] = False
        power["IPP_START_BLOCKED"] = False
        power["IPP_SHUTDOWN_SEQ_END_MS"] = 0
        power["BATT_270V_DIS_ON"] = False
        power["BATT_270V_BIT_FLASH_UNTIL_MS"] = 0

    if lef_lock_active:
        if "LEF_LOCK_L" not in throttle:
            throttle["LEF_LOCK_L"] = float(aircraft.get("l_lef", 0.0))
        if "LEF_LOCK_R" not in throttle:
            throttle["LEF_LOCK_R"] = float(aircraft.get("r_lef", 0.0))
        aircraft["l_lef"] = float(throttle.get("LEF_LOCK_L", aircraft.get("l_lef", 0.0)))
        aircraft["r_lef"] = float(throttle.get("LEF_LOCK_R", aircraft.get("r_lef", 0.0)))
    else:
        throttle.pop("LEF_LOCK_L", None)
        throttle.pop("LEF_LOCK_R", None)

    gear_mode = str(console_left.get("GEAR", "DOWN_OFF")).upper()
    gear_due = int(console_left.get("GEAR_TRANSITION_DUE_MS", 0))
    gear_start = int(console_left.get("GEAR_TRANSITION_START_MS", 0))
    gear_dir = str(console_left.get("GEAR_TRANSITION_DIR", "")).upper()
    fire_gear_active = _active_icaw_has("FIRE GEAR")
    gear_fail_active = _active_icaw_has("GEAR FAIL")
    if gear_due > 0 and now_ms >= gear_due and (not fire_gear_active) and (not gear_fail_active):
        if gear_mode == "UP_ON":
            gear_mode = "UP_OFF"
        elif gear_mode == "DOWN_ON":
            gear_mode = "DOWN_OFF"
        gear_due = 0
        console_left["GEAR"] = gear_mode
        console_left["GEAR_TRANSITION_DUE_MS"] = gear_due
        console_left["GEAR_TRANSITION_START_MS"] = 0
        console_left["GEAR_TRANSITION_DIR"] = ""
        console_left["GEAR_TRANSITION_DURATION_MS"] = 0
    if fire_gear_active or gear_fail_active:
        if gear_mode.startswith("UP"):
            console_left["GEAR"] = "UP_ON"
        else:
            console_left["GEAR"] = "DOWN_ON"
        console_left["GEAR_TRANSITION_DUE_MS"] = 0
        console_left["GEAR_TRANSITION_START_MS"] = 0
        console_left["GEAR_TRANSITION_DIR"] = ""
        console_left["GEAR_TRANSITION_DURATION_MS"] = 0
    else:
        try:
            gear_transition_ms = int(console_left.get("GEAR_TRANSITION_DURATION_MS", 0))
        except Exception:
            gear_transition_ms = 0
        if gear_transition_ms <= 0:
            gear_transition_ms = CONSOLE_LEFT_GEAR_TRANSITION_DEFAULT_MS
            if gear_due > now_ms:
                gear_transition_ms = max(1, int(gear_due - now_ms))
            console_left["GEAR_TRANSITION_DURATION_MS"] = int(gear_transition_ms)
        if gear_due > 0 and gear_start <= 0:
            console_left["GEAR_TRANSITION_START_MS"] = max(0, now_ms - int(gear_transition_ms))
        if gear_due > 0 and gear_dir not in {"UP", "DOWN"}:
            console_left["GEAR_TRANSITION_DIR"] = "UP" if gear_mode.startswith("UP") else "DOWN"
        if gear_due <= 0:
            console_left["GEAR_TRANSITION_START_MS"] = 0
            console_left["GEAR_TRANSITION_DIR"] = ""
            console_left["GEAR_TRANSITION_DURATION_MS"] = 0

    dt_ms = int(max(0.0, dt_sec) * 1000.0)
    batt_switch_on = str(power.get("BAT", "OFF")).upper() == "ON"
    icc3_on = str(power.get("ICC3", "OFF")).upper() == "ON"
    mf_sov_on = _is_mf_sov_on()
    engine_mode_switch = str(throttle.get("ENGINE", "OFF")).upper()
    prev_engine_mode_switch = str(throttle.get("ENGINE_SWITCH_PREV", "OFF")).upper()
    if prev_engine_mode_switch not in {"OFF", "MOTOR", "RUN"}:
        prev_engine_mode_switch = "OFF"
    engine_switch_turned_off = bool(engine_mode_switch == "OFF" and prev_engine_mode_switch != "OFF")
    engine_on_switch = (engine_mode_switch != "OFF") and (not mf_sov_on)
    svc_vals = {}
    hotas_axes: Dict[str, float] = {}
    if isinstance(pmd_dr_state, dict):
        maybe_vals = pmd_dr_state.get("svc_values", {})
        if isinstance(maybe_vals, dict):
            svc_vals = maybe_vals
        maybe_hotas_axes = pmd_dr_state.get("hotas_axis", {})
        if isinstance(maybe_hotas_axes, dict):
            for action_name in ("pitch", "yaw", "roll"):
                try:
                    hotas_axes[action_name] = float(maybe_hotas_axes.get(action_name, 0.0))
                except Exception:
                    hotas_axes[action_name] = 0.0

    try:
        batt_28v = float(svc_vals.get("28V_BAT", power.get("BATT_28V", 95.0)))
    except Exception:
        batt_28v = 95.0
    batt_28v = max(0.0, min(100.0, batt_28v))
    batt_power_on = bool(batt_switch_on and batt_28v > 0.0)

    bat_on_since_ms = int(power.get("BAT_ON_SINCE_MS", 0))
    bat_off_since_ms = int(power.get("BAT_OFF_SINCE_MS", 0))
    if batt_power_on:
        if bat_on_since_ms <= 0:
            if bool(power.get("BATT_28V_SBIT_COMPLETE", False)):
                # Preserve hot-start completed SBIT even when early tick values
                # make BAT_ON_SINCE_MS non-positive.
                bat_on_since_ms = now_ms - BATT_28V_SBIT_COMPLETE_MS
                bat_off_since_ms = 0
            else:
                bat_on_since_ms = now_ms
                bat_off_since_ms = 0
                power["BATT_28V_SBIT_STARTED"] = False
                power["BATT_28V_SBIT_COMPLETE"] = False
                power["BATT_28V_SBIT_FLASH_UNTIL_MS"] = 0
                power["BATT_28V_DIS_ON"] = False
                power["BATT_28V_DIS_CLEAR_DUE_MS"] = 0
    else:
        if bat_off_since_ms <= 0:
            bat_off_since_ms = now_ms
            bat_on_since_ms = 0
            power["BATT_28V_SBIT_STARTED"] = False
            power["BATT_28V_SBIT_COMPLETE"] = False
            power["BATT_28V_SBIT_FLASH_UNTIL_MS"] = 0
            power["BATT_28V_DIS_CLEAR_DUE_MS"] = 0

    sbit_started = bool(power.get("BATT_28V_SBIT_STARTED", False))
    sbit_complete = bool(power.get("BATT_28V_SBIT_COMPLETE", False))
    sbit_flash_until = int(power.get("BATT_28V_SBIT_FLASH_UNTIL_MS", 0))
    dis28_on = bool(power.get("BATT_28V_DIS_ON", False))
    dis28_clear_due = int(power.get("BATT_28V_DIS_CLEAR_DUE_MS", 0))
    if batt_power_on and bat_on_since_ms > 0:
        elapsed = now_ms - bat_on_since_ms
        if elapsed >= BATT_28V_SBIT_START_DELAY_MS and not sbit_started:
            sbit_started = True
            sbit_flash_until = now_ms + BATT_28V_SBIT_FLASH_MS
        if elapsed >= BATT_28V_SBIT_COMPLETE_MS and not sbit_complete:
            sbit_complete = True
            dis28_on = True
    else:
        if bat_off_since_ms > 0 and (now_ms - bat_off_since_ms) >= BATT_28V_DIS_BATT_OFF_CLEAR_MS:
            dis28_on = False

    if dis28_clear_due > 0 and now_ms >= dis28_clear_due:
        dis28_on = False
        dis28_clear_due = 0

    # 28V battery charge/discharge model driven by switch and powered sources.
    if batt_power_on:
        batt_rate = 0.1 if (bool(power.get("IPP_ON", False)) or engine_on_switch) else -0.1
        batt_28v = max(0.0, min(100.0, batt_28v + batt_rate * max(0.0, dt_sec)))
    if batt_28v <= 0.0:
        batt_28v = 0.0
        batt_power_on = False
        dis28_on = False

    # Push back into SVC debug state so field E6 always reflects runtime.
    power["BATT_28V"] = float(batt_28v)
    if isinstance(svc_vals, dict):
        svc_vals["28V_BAT"] = float(batt_28v)

    # IPP runtime model:
    # - START requires completed 28V SBIT, BAT+ICC3 ON, and 3s hold.
    # - Holding OFF for 5s starts a 60s flashing shutdown sequence.
    ipp_mode = str(power.get("IPP", "AUTO")).upper()
    ipp_mode_logic = str(ipp_mode)
    ipp_on = bool(power.get("IPP_ON", False))
    ipp_on_since_ms = int(power.get("IPP_ON_SINCE_MS", 0))
    start_hold_ms = int(power.get("IPP_START_HOLD_MS", 0))
    start_seq_end = int(power.get("IPP_START_SEQ_END_MS", 0))
    start_seq_success = bool(power.get("IPP_START_SEQ_SUCCESS", False))
    start_blocked = bool(power.get("IPP_START_BLOCKED", False))
    shutdown_seq_end = int(power.get("IPP_SHUTDOWN_SEQ_END_MS", 0))
    off_hold_ms = int(power.get("IPP_OFF_HOLD_MS", 0))
    bit270_flash_until = int(power.get("BATT_270V_BIT_FLASH_UNTIL_MS", 0))
    dis270_on = bool(power.get("BATT_270V_DIS_ON", False))
    can_start_ipp = bool(batt_power_on and icc3_on and sbit_complete and fuel_available)
    startup_active = bool(start_seq_success and start_seq_end > now_ms)
    if ipp_mode_logic == "OFF" and startup_active and (not bool(power.get("EMER_PRESSED", False))):
        # Keep switch visually in OFF while held, but ignore OFF logic during startup.
        ipp_mode_logic = "AUTO"
        off_hold_ms = 0

    if start_seq_end > 0 and now_ms >= start_seq_end:
        if start_seq_success and can_start_ipp:
            ipp_on = True
            ipp_on_since_ms = now_ms
            dis28_clear_due = now_ms + BATT_28V_DIS_IPP_READY_CLEAR_MS
        start_seq_end = 0
        start_seq_success = False
        start_blocked = False
        dis270_on = False

    if shutdown_seq_end > 0 and now_ms >= shutdown_seq_end:
        ipp_on = False
        ipp_on_since_ms = 0
        shutdown_seq_end = 0

    if bool(power.get("EMER_PRESSED", False)):
        dis270_on = False

    if not batt_power_on and not ipp_on:
        start_seq_end = 0
        start_seq_success = False
        start_blocked = False
        start_hold_ms = 0
        bit270_flash_until = 0
        dis270_on = False

    if ipp_mode_logic != "START":
        start_hold_ms = 0
        start_blocked = False
    elif sbit_complete:
        prev_hold = start_hold_ms
        start_hold_ms += dt_ms
        if prev_hold <= 0:
            bit270_flash_until = now_ms + BATT_270V_BIT_FLASH_MS
        if (not ipp_on) and start_seq_end <= now_ms and shutdown_seq_end <= now_ms and start_hold_ms >= IPP_START_HOLD_REQUIRED_MS:
            if can_start_ipp:
                ipp_start_ms = get_sound_length_or_default_ms("IPP START", IPP_START_SUCCESS_FLASH_MS)
                start_seq_end = now_ms + ipp_start_ms
                start_seq_success = True
                dis270_on = True
                start_blocked = False
            elif batt_power_on and (not icc3_on):
                start_seq_end = now_ms + IPP_START_FAIL_FLASH_MS
                start_seq_success = False
                start_blocked = True
            else:
                start_blocked = True
            start_hold_ms = 0

    if ipp_mode_logic == "OFF":
        off_hold_ms += dt_ms
        if ipp_on and shutdown_seq_end <= now_ms and off_hold_ms >= IPP_OFF_HOLD_REQUIRED_MS:
            shutdown_seq_end = now_ms + IPP_SHUTDOWN_FLASH_MS
            off_hold_ms = 0
            start_seq_end = 0
            start_seq_success = False
            start_blocked = False
            start_hold_ms = 0
            dis270_on = False
    else:
        off_hold_ms = 0

    # Engine switch OFF always initiates IPP shutdown once (without resetting
    # an already-running shutdown timer).
    if engine_switch_turned_off and ipp_on and shutdown_seq_end <= now_ms:
        shutdown_seq_end = now_ms + IPP_SHUTDOWN_FLASH_MS
        off_hold_ms = 0
        start_seq_end = 0
        start_seq_success = False
        start_blocked = False
        start_hold_ms = 0
        dis270_on = False

    # Electrical light states.
    if batt_28v <= 0.0:
        low28 = False
        dis28 = False
        low270 = False
        dis270 = False
    else:
        in_28v_flash = bool(batt_power_on and sbit_started and now_ms < sbit_flash_until)
        low28 = bool(in_28v_flash or (batt_power_on and sbit_complete and batt_28v < 8.0 and ((now_ms // BATT_28V_LOW_FLASH_INTERVAL_MS) % 2 == 0)))
        dis28 = bool(in_28v_flash or dis28_on)
        in_270v_flash = now_ms < bit270_flash_until
        low270 = bool(in_270v_flash)
        dis270 = bool(in_270v_flash or dis270_on)

    power["BAT_ACTIVE"] = bool(batt_power_on)
    power["BAT_ON_SINCE_MS"] = int(bat_on_since_ms)
    power["BAT_OFF_SINCE_MS"] = int(bat_off_since_ms)
    power["BATT_28V_SBIT_STARTED"] = bool(sbit_started)
    power["BATT_28V_SBIT_COMPLETE"] = bool(sbit_complete)
    power["BATT_28V_SBIT_FLASH_UNTIL_MS"] = int(sbit_flash_until)
    power["BATT_28V_DIS_ON"] = bool(dis28_on)
    power["BATT_28V_DIS_CLEAR_DUE_MS"] = int(dis28_clear_due)
    power["BATT_28V_LOW_LIGHT"] = bool(low28)
    power["BATT_28V_DIS_LIGHT"] = bool(dis28)
    power["BATT_270V_BIT_FLASH_UNTIL_MS"] = int(bit270_flash_until)
    power["BATT_270V_DIS_ON"] = bool(dis270_on)
    power["BATT_270V_LOW_LIGHT"] = bool(low270)
    power["BATT_270V_DIS_LIGHT"] = bool(dis270)

    power["IPP_ON"] = bool(ipp_on)
    power["IPP"] = str(ipp_mode)
    power["IPP_ON_SINCE_MS"] = int(ipp_on_since_ms)
    power["IPP_START_HOLD_MS"] = int(start_hold_ms)
    power["IPP_OFF_HOLD_MS"] = int(off_hold_ms)
    power["IPP_START_SEQ_END_MS"] = int(start_seq_end)
    power["IPP_START_SEQ_SUCCESS"] = bool(start_seq_success)
    power["IPP_START_BLOCKED"] = bool(start_blocked)
    power["IPP_SHUTDOWN_SEQ_END_MS"] = int(shutdown_seq_end)
    throttle["ENGINE_SWITCH_PREV"] = str(engine_mode_switch)

    # Canopy actuator: 10s full travel, stops/resumes from current position.
    canopy_pos = float(throttle.get("CANOPY_POS", 0.0))
    canopy_switch = str(throttle.get("CANOPY", "CENTER")).upper()
    rate = (max(0.0, dt_sec) * 1000.0) / float(max(1, CANOPY_ACTUATOR_TRAVEL_MS))
    if canopy_switch == "UP":
        canopy_pos -= rate
    elif canopy_switch == "DOWN":
        canopy_pos += rate
    throttle["CANOPY_POS"] = max(0.0, min(1.0, canopy_pos))

    try:
        curr_spool = float(throttle.get("ENGINE_SPOOL", 0.0))
    except Exception:
        curr_spool = 0.0
    try:
        curr_thr_pos = float(throttle.get("THROTTLE_POS", 0.0))
    except Exception:
        curr_thr_pos = 0.0
    if (
        str(engine_mode_switch).upper() == "RUN"
        and str(throttle.get("ENGINE_SPOOL_MODE", "OFF")).upper() == "RUN"
        and curr_spool >= 0.99
        and curr_thr_pos <= 1.0
    ):
        if int(throttle.get("VS_BIT_IDLE_SINCE_MS", 0)) <= 0:
            throttle["VS_BIT_IDLE_SINCE_MS"] = int(now_ms)
    else:
        throttle["VS_BIT_IDLE_SINCE_MS"] = 0

    rudder_switch_mode = str(throttle.get("RUDDER", "CENTER")).upper()
    try:
        rudder_trim_in = float(throttle.get("RUDDER_TRIM_IN", 0.0))
    except Exception:
        rudder_trim_in = 0.0
    trim_delta = float(max(0.0, dt_sec)) * float(RUDDER_TRIM_RATE_IN_PER_SEC)
    if rudder_switch_mode == "LEFT":
        rudder_trim_in -= trim_delta
    elif rudder_switch_mode == "RIGHT":
        rudder_trim_in += trim_delta
    throttle["RUDDER_TRIM_IN"] = _clamp_fcs(rudder_trim_in, -FCS_SYMBOL_MAX_OFFSET_IN, FCS_SYMBOL_MAX_OFFSET_IN)

    # Flight controls are static unless user input moves them, or VS BIT sequence drives them.
    # Run VS BIT first; manual input can still override and will mark VS BIT failure.
    _update_vs_bit_flight_controls(throttle, aircraft, dt_sec)
    _update_user_flight_controls(throttle, aircraft, held_keys, dt_sec, hotas_axes=hotas_axes)

    # Heading is now driven by coupled attitude dynamics in update_engine_runtime().

    # VS BIT run timer and NO GO latch.
    if bool(throttle.get("VS_BIT_RUNNING", False)):
        if str(engine_mode_switch).upper() == "OFF":
            _vs_bit_reset_runtime(throttle)
            _vs_bit_set_result(throttle, "FN", ["VS BIT: ABORT-Engine Off"])
            return
        start_ms = int(throttle.get("VS_BIT_START_MS", 0))
        end_ms = int(throttle.get("VS_BIT_END_MS", 0))
        manual_override = bool(throttle.get("VS_BIT_MANUAL_OVERRIDE", False))
        throttle_jammed = _active_icaw_has("THROTTLE JAMMED")
        # During V/S BIT, throttle is auto-driven IDLE -> MAX in 1s, then
        # MAX -> IDLE in 1s, then remains at IDLE for the rest of the BIT.
        if (not throttle_jammed) and (not manual_override) and end_ms > start_ms and now_ms <= end_ms:
            elapsed_ms = max(0, now_ms - start_ms)
            if elapsed_ms < VS_BIT_THROTTLE_UP_MS:
                auto_frac = elapsed_ms / float(max(1, VS_BIT_THROTTLE_UP_MS))
            elif elapsed_ms < (VS_BIT_THROTTLE_UP_MS + VS_BIT_THROTTLE_DOWN_MS):
                down_elapsed = elapsed_ms - VS_BIT_THROTTLE_UP_MS
                auto_frac = 1.0 - (down_elapsed / float(max(1, VS_BIT_THROTTLE_DOWN_MS)))
            else:
                auto_frac = 0.0
            auto_frac = max(0.0, min(1.0, auto_frac))
            throttle["THROTTLE_POS"] = 150.0 * auto_frac
        expected_refuel_open = throttle.get("VS_BIT_EXPECT_REFUEL_OPEN", None)
        actual_refuel_open = bool(_is_refuel_door_open())
        if isinstance(expected_refuel_open, bool):
            # VS BIT-commanded refuel door open/close is allowed.
            if actual_refuel_open != bool(expected_refuel_open):
                throttle["VS_BIT_REFUEL_SEEN"] = True
        else:
            # Any refuel-door opening not commanded by VS BIT is a NO GO condition.
            if actual_refuel_open:
                throttle["VS_BIT_REFUEL_SEEN"] = True
        prev_sig = str(throttle.get("VS_BIT_DOOR_SIG", ""))
        now_sig = _weapon_door_signature(int(now_ms))
        if _vs_bit_weapon_door_no_go(now_sig):
            throttle["VS_BIT_DOOR_MOVED"] = True
        elif prev_sig != "" and now_sig != prev_sig:
            throttle["VS_BIT_DOOR_MOVED"] = True
        throttle["VS_BIT_DOOR_SIG"] = now_sig
        # Finalize only after timer expiry AND scripted flight-control sequence completion.
        # Timeout FnA is intentionally disabled; VS BIT waits for sequence completion.
        fcs_seq_done = not bool(throttle.get("VS_BIT_FCS_ACTIVE", False))
        if end_ms > 0 and int(now_ms) >= end_ms and fcs_seq_done:
            refuel_seen = bool(throttle.get("VS_BIT_REFUEL_SEEN", False))
            door_moved = bool(throttle.get("VS_BIT_DOOR_MOVED", False))
            throttle_moved = bool(throttle.get("VS_BIT_THROTTLE_MOVED", False))
            ctrl_moved = bool(throttle.get("VS_BIT_CTRL_MOVED", False))
            reasons: List[str] = []
            if throttle_moved or ctrl_moved:
                reasons.append("VS BIT: ABORT-HOTAS")
            if refuel_seen or door_moved:
                reasons.append("VS BIT: FAIL-FLCS")
            reasons.extend(_vs_bit_collect_system_fail_reasons())
            # Remove duplicates while preserving order.
            uniq_reasons = list(dict.fromkeys([r for r in reasons if str(r).strip() != ""]))
            _vs_bit_reset_runtime(throttle)
            if len(uniq_reasons) > 0:
                _vs_bit_set_result(throttle, "FN", uniq_reasons)
            else:
                _vs_bit_set_result(throttle, "OK", [])


def _handle_panel_popup_mouse_down(pos: Tuple[int, int], mouse_button: int) -> bool:
    if mouse_button not in {1, 2, 3}:
        return False
    for hit in reversed(_PANEL_RUNTIME_BUTTON_HITS):
        rect = hit.get("rect")
        if not isinstance(rect, pygame.Rect):
            continue
        if rect.collidepoint(pos):
            panel = str(hit.get("panel", ""))
            control = str(hit.get("control", ""))
            if panel == "POWER PANEL":
                if mouse_button in {1, 3}:
                    _set_power_panel_control(control, mouse_button, True)
                    return True
                continue
            if panel == "THROTTLE":
                if mouse_button in {1, 3}:
                    _set_throttle_panel_control(control, mouse_button, True)
                    return True
                continue
            if panel == "DISPLAY CONTROL":
                if mouse_button in {1, 3}:
                    _set_display_control_panel_control(control, mouse_button, True)
                    return True
                continue
            if panel == "MASTER ARM":
                if mouse_button in {1, 3}:
                    _set_master_arm_panel_control(control, mouse_button, True, pos=pos)
                    return True
                continue
            if panel == "CONSOLE LEFT":
                _set_console_left_panel_control(control, mouse_button, True)
                return True
    return False


def _handle_panel_popup_mouse_up(mouse_button: int) -> None:
    global _PANEL_ACTIVE_DIAL_DRAG
    if isinstance(_PANEL_ACTIVE_DIAL_DRAG, dict):
        try:
            if int(_PANEL_ACTIVE_DIAL_DRAG.get("button", 1)) == int(mouse_button):
                _PANEL_ACTIVE_DIAL_DRAG = None
        except Exception:
            _PANEL_ACTIVE_DIAL_DRAG = None
    hold = _PANEL_ACTIVE_HOLDS.get(mouse_button)
    if hold is None:
        return
    panel, control = hold
    if panel == "POWER PANEL":
        _set_power_panel_control(control, mouse_button, False)
    elif panel == "THROTTLE":
        _set_throttle_panel_control(control, mouse_button, False)
    _PANEL_ACTIVE_HOLDS[mouse_button] = None


def _release_panel_popup_holds() -> None:
    global _PANEL_ACTIVE_DIAL_DRAG
    _PANEL_ACTIVE_DIAL_DRAG = None
    for b in (1, 3):
        _handle_panel_popup_mouse_up(b)


def _discover_panel_pages() -> List[List[str]]:
    global _PANEL_PAGE_CACHE
    if _PANEL_PAGE_CACHE is not None:
        return _PANEL_PAGE_CACHE
    root = resource_path("icons", "PANELS")
    available: List[str] = []
    try:
        if root.exists():
            for p in root.iterdir():
                if not p.is_dir():
                    continue
                if (p / "DRAWING.png").exists() and (p / "TEXT.png").exists():
                    available.append(p.name)
    except Exception:
        available = []
    available_set = set(available)
    pages: List[List[str]] = []
    preferred_pages = [
        ["POWER PANEL", "THROTTLE"],
        ["DISPLAY CONTROL", "MASTER ARM", "CONSOLE LEFT", "CONSOLE RIGHT"],
    ]
    used: set = set()
    for page in preferred_pages:
        filtered = [name for name in page if name in available_set]
        if filtered:
            pages.append(filtered)
            used.update(filtered)
    remaining = [name for name in sorted(available) if name not in used]
    for i in range(0, len(remaining), 2):
        pages.append(remaining[i:i + 2])
    if not pages:
        pages = [[]]
    _PANEL_PAGE_CACHE = pages
    return pages


def _panel_text_tint_rgb() -> Tuple[int, int, int]:
    # LITES A1(CONSL) gates panel text tint; B1 controls white->green interpolation.
    if not bool(_PANEL_TEXT_LITES_A1_ON):
        return (255, 255, 255)
    brt = max(0, min(100, int(_PANEL_TEXT_LITES_B1_BRT)))
    t = float(brt) / 100.0
    red_blue = int(round(255.0 * (1.0 - t)))
    return (red_blue, 255, red_blue)


def _refresh_panel_text_cache_sig() -> None:
    global _PANEL_TEXT_CACHE_SIG
    sig = (bool(_PANEL_TEXT_LITES_A1_ON), max(0, min(100, int(_PANEL_TEXT_LITES_B1_BRT))))
    if _PANEL_TEXT_CACHE_SIG != sig:
        _PANEL_IMAGE_CACHE.clear()
        _PANEL_TEXT_CACHE_SIG = sig


def _load_panel_composite(panel_name: str) -> Optional[pygame.Surface]:
    _refresh_panel_text_cache_sig()
    cached = _PANEL_IMAGE_CACHE.get(panel_name)
    if cached is not None or panel_name in _PANEL_IMAGE_CACHE:
        return cached
    panel_dir = resource_path("icons", "PANELS", panel_name)
    drawing_path = panel_dir / "DRAWING.png"
    text_path = panel_dir / "TEXT.png"
    if not drawing_path.exists() or not text_path.exists():
        _PANEL_IMAGE_CACHE[panel_name] = None
        return None
    try:
        drawing = pygame.image.load(str(drawing_path)).convert_alpha()
        overlay = pygame.image.load(str(text_path)).convert_alpha()
        tint_rgb = _panel_text_tint_rgb()
        if tint_rgb != (255, 255, 255):
            overlay = overlay.copy()
            tint_layer = pygame.Surface(overlay.get_size(), pygame.SRCALPHA)
            tint_layer.fill((int(tint_rgb[0]), int(tint_rgb[1]), int(tint_rgb[2]), 255))
            overlay.blit(tint_layer, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        w = max(drawing.get_width(), overlay.get_width())
        h = max(drawing.get_height(), overlay.get_height())
        composite = pygame.Surface((w, h), pygame.SRCALPHA)
        composite.blit(drawing, drawing.get_rect(center=(w // 2, h // 2)))
        composite.blit(overlay, overlay.get_rect(center=(w // 2, h // 2)))
        if str(panel_name).strip().upper() == "THROTTLE":
            composite = pygame.transform.rotate(composite, -90)
        _PANEL_IMAGE_CACHE[panel_name] = composite
        return composite
    except Exception:
        _PANEL_IMAGE_CACHE[panel_name] = None
        return None


def _load_panel_overlay_image(panel_name: str, filename: str) -> Optional[pygame.Surface]:
    key = f"{panel_name}::__OVERLAY__::{filename}"
    cached = _PANEL_IMAGE_CACHE.get(key)
    if cached is not None or key in _PANEL_IMAGE_CACHE:
        return cached
    path = resource_path("icons", "PANELS", panel_name, filename)
    if not path.exists():
        _PANEL_IMAGE_CACHE[key] = None
        return None
    try:
        surf = pygame.image.load(str(path)).convert_alpha()
        _PANEL_IMAGE_CACHE[key] = surf
        return surf
    except Exception:
        _PANEL_IMAGE_CACHE[key] = None
        return None


# Export extracted internals so `from cockpit_panel_state import *` preserves
# underscore-prefixed names expected by main.py.
_COCKPIT_EXPORT_SKIP = {
    "math",
    "random",
    "pygame",
    "formats",
    "resource_path",
    "Dict",
    "List",
    "Optional",
    "Tuple",
}
__all__ = [
    name
    for name in globals().keys()
    if (not name.startswith("__")) and (name not in _COCKPIT_EXPORT_SKIP)
]
