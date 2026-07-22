from typing import Dict, List, Tuple

STATUS_MENU_ITEMS = {
    "CRUS": (1, 0, "CRUS>"),
    "DATA_LINK": (1, 1, "DATA\nLINK>"),
    "ECS": (1, 2, "ECS>"),
    "HMD": (1, 3, "HMD>"),
    "INS_GPS": (2, 0, "INS\nGPS>"),
    "LITES": (2, 1, "LITES>"),
    "ON_OFF": (2, 2, "ON\nOFF>"),
    "PMD_DR": (2, 3, "PMD/DR>"),
    "SECLVL": (2, 4, "SECLVL>"),
}
ON_OFF_CELL_BUTTONS: List[Tuple[str, str]] = [
    ("A2", "ACE"),
    ("B2", "BUR"),
    ("C2", "CNI-A"),
    ("D2", "CNI-B"),
    ("E2", "CM-L"),
    ("A3", "CM-R"),
    ("B3", "DAS-BA"),
    ("C3", "DAS-BF"),
    ("D3", "DAS-L"),
    ("E3", "DAS-R"),
    ("A4", "DAS-TA"),
    ("B4", "DAS-TF"),
    ("C4", "DMC-L"),
    ("D4", "DMC-R"),
    ("E4", "DMC-H"),
    ("A5", "EW-SYS"),
    ("B5", "EW-B"),
    ("C5", "EW-AFT"),
    ("D5", "ICP-A"),
    ("E5", "ICP-B"),
    ("A6", "ICP-C"),
    ("B6", "GPS"),
    ("C6", "INS"),
    ("D6", "LADC"),
    ("B7", "PMD"),
    ("C7", "RADAR"),
    ("D7", "EOTS"),
]
ON_OFF_BUTTON_ZONE_KEYS = {f"ON_OFF_{cell_name}" for cell_name, _label in ON_OFF_CELL_BUTTONS}
ON_OFF_BUTTON_KEY_TO_LABEL: Dict[str, str] = {
    f"ON_OFF_{cell_name}": str(label).upper().strip()
    for cell_name, label in ON_OFF_CELL_BUTTONS
}
ON_OFF_LABEL_TO_BUTTON_KEY: Dict[str, str] = {
    str(label).upper().strip(): f"ON_OFF_{cell_name}"
    for cell_name, label in ON_OFF_CELL_BUTTONS
}
ON_OFF_LABELS: List[str] = [str(label).upper().strip() for _cell_name, label in ON_OFF_CELL_BUTTONS]
ON_OFF_BIT_MIN_MS = 35000
ON_OFF_BIT_MAX_MS = 50000
ON_OFF_OFF_TO_GRAY_MS = 5000


def _default_on_off_states() -> Dict[str, bool]:
    return {key: True for key in ON_OFF_BUTTON_ZONE_KEYS}
PMD_DR_TANK_LIMITS: Dict[str, int] = {
    "F1": 5100,
    "F1I": 1300,
    "F2L": 1150,
    "F2R": 1150,
    "F3L": 2150,
    "F3R": 2150,
    "F4L": 1100,
    "F4R": 1100,
    "F5L": 1000,
    "F5R": 1000,
    "LW": 1150,
    "RW": 1150,
}
PMD_FUEL_DEGRD_TANK_ORDER: List[str] = [
    "F1",
    "F2L",
    "F2R",
    "F3L",
    "F3R",
    "F4L",
    "F4R",
    "F5L",
    "F5R",
    "LW",
    "RW",
]
PMD_FUEL_DEGRD_VALVE_LAYOUT: Dict[str, List[str]] = {
    "F1": ["V1", "V2", "V3"],
    "F3L": ["V1", "V2"],
    "F3R": ["V1", "V2"],
}
PMD_FUEL_DEGRD_VALVE_DEFAULTS: Dict[str, Dict[str, bool]] = {
    "F1": {"V1": True, "V2": False, "V3": False},
    "F3L": {"V1": False, "V2": False},
    "F3R": {"V1": False, "V2": False},
}

INS_GPS_MODE_OPTIONS: List[str] = ["ALIGN", "NAV", "STBY", "COMP", "SEC"]
INS_GPS_ALIGN_PROFILE_OPTIONS: List[str] = ["NORM", "FINE", "FAST", "STOR"]
INS_GPS_GPS_AIDING_OPTIONS: List[str] = ["AUTO", "ON", "OFF"]
INS_GPS_FIX_SOURCE_OPTIONS: List[str] = ["WYPT", "SENS", "MAN", "TACN"]
INS_GPS_NAV_FILTER_OPTIONS: List[str] = ["NORM", "TIGHT", "SMTH", "HI-DYN"]
INS_GPS_MAGVAR_MODE_OPTIONS: List[str] = ["AUTO", "MAN"]
INS_GPS_WYPT_SOURCE_OPTIONS: List[str] = ["PRES GPS", "WYPT", "TACN"]
_VS_BIT_FCS_SEQUENCE: List[Dict[str, object]] = [
    {"targets": {"l_elevator": -20.0, "r_elevator": -20.0}, "delay_s": 11.0},
    {"targets": {"l_elevator": -25.0, "r_elevator": -25.0, "l_rudder": -5.0, "r_rudder": 5.0, "l_aileron": -5.0, "r_aileron": -5.0}, "delay_s": 0.25},
    {"targets": {"l_elevator": -20.0, "r_elevator": -20.0, "l_rudder": 0.0, "r_rudder": 0.0, "l_aileron": 0.0, "r_aileron": 0.0}, "delay_s": 0.5},
    {"targets": {"l_elevator": -55.0, "r_elevator": -55.0, "l_rudder": -20.0, "r_rudder": 20.0, "l_aileron": -15.0, "r_aileron": -15.0}, "delay_s": 0.25},
    {"targets": {"l_elevator": 0.0, "r_elevator": 0.0, "l_rudder": 5.0, "r_rudder": -5.0, "l_aileron": 10.0, "r_aileron": 10.0}, "delay_s": 0.5},
    {"targets": {"l_elevator": -55.0, "r_elevator": -55.0, "l_rudder": -20.0, "r_rudder": 20.0, "l_aileron": -10.0, "r_aileron": -10.0}, "delay_s": 0.5},
    {"targets": {"l_elevator": 0.0, "r_elevator": 0.0, "l_rudder": -20.0, "r_rudder": 20.0, "l_aileron": 10.0, "r_aileron": 10.0}, "delay_s": 0.5},
    {"targets": {"l_elevator": -55.0, "r_elevator": -55.0, "l_rudder": -20.0, "r_rudder": 20.0, "l_aileron": -10.0, "r_aileron": -10.0}, "delay_s": 0.5},
    {"targets": {"l_elevator": -5.0, "r_elevator": -5.0, "l_rudder": -20.0, "r_rudder": 20.0, "l_aileron": 10.0, "r_aileron": 10.0}, "delay_s": 1.0},
    {"targets": {"l_elevator": -5.0, "r_elevator": -5.0, "l_rudder": 20.0, "r_rudder": -20.0, "l_aileron": 10.0, "r_aileron": 10.0}, "delay_s": 0.75},
    {"targets": {"l_elevator": -15.0, "r_elevator": -15.0, "l_rudder": 20.0, "r_rudder": -20.0, "l_aileron": 0.0, "r_aileron": 0.0}, "refuel_open": True, "delay_s": 0.5},
    {"targets": {"l_elevator": -25.0, "r_elevator": -25.0, "l_rudder": 20.0, "r_rudder": -20.0, "l_aileron": -10.0, "r_aileron": -10.0}, "delay_s": 0.25},
    {"targets": {"l_elevator": -20.0, "r_elevator": -20.0, "l_rudder": 0.0, "r_rudder": 0.0, "l_aileron": -10.0, "r_aileron": -10.0, "l_lef": 5.0, "r_lef": 5.0}, "delay_s": 1.0},
    {"targets": {"l_elevator": 20.0, "r_elevator": 20.0, "l_rudder": 0.0, "r_rudder": 0.0, "l_aileron": -10.0, "r_aileron": -10.0, "l_lef": 15.0, "r_lef": 15.0}, "delay_s": 0.25},
    {"targets": {"l_elevator": -20.0, "r_elevator": -20.0, "l_rudder": 0.0, "r_rudder": 0.0, "l_aileron": 0.0, "r_aileron": 0.0, "l_lef": 0.0, "r_lef": 0.0}, "refuel_open": False, "delay_s": 6.0},
    {"targets": {"l_elevator": 5.0, "r_elevator": 5.0}, "delay_s": 0.1},
    {"targets": {"l_elevator": 0.0, "r_elevator": 0.0}, "delay_s": 0.25},
    {"targets": {"l_elevator": -25.0, "r_elevator": -25.0}, "delay_s": 3.0},
    {"targets": {"l_elevator": -5.0, "r_elevator": -5.0, "l_rudder": 0.0, "r_rudder": 0.0, "l_aileron": -25.0, "r_aileron": -25.0}},
]
VS_BIT_FAILURE_CATALOG: List[Tuple[str, str]] = [
    ("VS BIT: ABORT-Pilot", "Pilot aborted Vehicle System (VS) Built-in Test (BIT) with the VS BIT Switch."),
    ("VS BIT: ABORT-HOTAS", "Pilot aborted VS BIT with stick/throttle/grip interference."),
    ("VS BIT: ABORT-Engine Off", "Pilot aborted VS BIT with engine cutoff."),
    ("VS BIT: FAIL-FLCS", "VS BIT failed for the Flight Controls System. Maintenance actionable HRCs should be found on the FCS or VSP page."),
    ("VS BIT: FAIL-Fuel", "VS BIT failed for the Fuel Management System. Maintenance actionable HRCs should be found on the FUEL page."),
    ("VS BIT: FAIL-FPS", "VS BIT failed for the Fire Protection System. Maintenance actionable HRCs should be found on the FPS page."),
    ("VS BIT: FAIL-HUA", "VS BIT failed for the hydraulics system. Maintenance actionable HRCs should be found on the HYD page."),
    ("VS BIT: FAIL-LGS", "VS BIT failed for the Landing and Arresting Gear System. Maintenance actionable HRCs should be found on the GEAR page."),
    ("VS BIT: FAIL-Prop", "VS BIT failed for the Propulsion System. Maintenance actionable HRCs should be found on the PROP page."),
    ("VS BIT: FAIL-PTMS", "VS BIT failed for the power & Thermal Management System. Maintenance actionable HRCs should be found on the PTMS page."),
    ("VS BIT: Ground Interlock", "Ground Interlocks were not met or exceeded during VS BIT (W-ON-W, Throttle more than Idle, Aircraft Not Stationary, etc.)."),
    ("VS BIT: Parking Brake", "Hydraulics test not complete due to parking brake off."),
    ("VS BIT: NWS Out of Range", "Nose Wheel Steering (NWS) not in correct forward facing orientation."),
    ("VS BIT: EHA Temp-HOT", "Electro Hydraulic Actuator (EHA) not tested due to hot actuators."),
    ("VS BIT: EHA Temp-COLD", "EHA not tested due to cold actuators."),
    ("VS BIT: Stick Passive", "VS BIT failed due to stick in passive mode."),
    ("VS BIT: Throttle Passive", "VS BIT failed due to throttle in passive mode."),
    ("VS BIT: No EHA 270V", "270Vdc not available to Electro Static Actuation System (EHAS) during VS BIT."),
    ("VS BIT: Fuel-Def Vlv Open", "Refuel/Defuel valve is in incorrect position."),
    ("VS BIT: No HYD A-HTCA", "Hydraulics-System A not available during VS BIT-Horizontal Tail Centering Actuator (HTCA)."),
    ("VS BIT: No HYD B-NWS", "Hydraulics-system B not available during VS BIT-NWS."),
    ("VS BIT: HUA-Timeout", "VS BIT time out-HUA-doors not restored to pre-VS BIT state in time."),
    ("VS BIT: Timeout", "VS BIT time out."),
    ("VS BIT: HUA Terminate", "HUA had a safety protocol violated and terminated the BIT."),
    ("VS BIT: Pilot Delay", "This indicates that the pilot is to wait at a minimum 15 secs before attempting to run VS BIT. Either the engine has not reached Idle yet or some other action is still in progress that prevents VS BIT entry. This FnA will clear when the timers have cleared."),
    ("VS BIT: Convert to CTOL", "VS BIT cannot be performed if the aircraft is not in CTOL mode. Pilot needs to ensure that the aircraft is in the proper configuration to run VS BIT. FnA will clear once in CTOL mode."),
    ("VS BIT: ETR to Idle", "VS BIT will fail if the Engine is not at idle. Ensure the Throttle is set to Idle and delay 15 secs before requesting VS BIT. FnA will clear once ETR has reached steady state for 15 seconds."),
    ("VS BIT: In Motion", "VS BIT cannot be performed while the aircraft is moving. Stop the aircraft and ensure the Parking Brake is set prior to requesting VS BIT."),
    ("VS BIT: Parking Brake", "VS BIT cannot be performed if the Parking Brake is not set. Set the Parking Brake before requesting VS BIT."),
    ("VS BIT: Not Available", "VS BIT is not available. No pilot action will return the capability of VS BIT."),
]
VS_BIT_FAILURE_TITLES: List[str] = [title for title, _desc in VS_BIT_FAILURE_CATALOG]
IPP_LIGHT_FLASH_INTERVAL_MS = 250
IPP_START_SUCCESS_FLASH_MS = 10000
IPP_START_FAIL_FLASH_MS = 5000
IPP_OFF_HOLD_REQUIRED_MS = 5000
IPP_SHUTDOWN_FLASH_MS = 60000
CONSOLE_LEFT_GEAR_TRANSITION_MIN_MS = 8000
CONSOLE_LEFT_GEAR_TRANSITION_MAX_MS = 11000
CONSOLE_LEFT_GEAR_TRANSITION_DEFAULT_MS = 9500
BATT_28V_SBIT_START_DELAY_MS = 2000
BATT_28V_SBIT_COMPLETE_MS = 15000
BATT_28V_SBIT_FLASH_MS = 1000
BATT_28V_DIS_BATT_OFF_CLEAR_MS = 5000
BATT_28V_DIS_IPP_READY_CLEAR_MS = 7000
BATT_28V_LOW_FLASH_INTERVAL_MS = 250
BATT_270V_BIT_FLASH_MS = 250
ENGINE_MOTOR_SPOOL_MS = 30000
ENGINE_RUN_SPOOL_MS = 60000
ENGINE_OFF_FROM_MOTOR_SPOOL_MS = 30000
ENGINE_OFF_FROM_RUN_SPOOL_MS = 30000
THROTTLE_HANDLE_MAX_DX_PX = 550
THROTTLE_HANDLE_MAX_DY_PX = -50
AIRSPEED_MIN_THRUST_PCT = 15.0
AIRSPEED_AB_START_THRUST_PCT = 100.0
AIRSPEED_MAX_THRUST_PCT = 150.0
AIRSPEED_MAX_KTS = 710.0
AIRSPEED_AT_AB_START_KTS = 420.0
AIRSPEED_PRE_AB_EXP = 1.1
AIRSPEED_AB_EXP = 0.4
AIRSPEED_MAX_ACCEL_KTS_PER_SEC = 25.0
AIRSPEED_DECEL_GAP_COEFF = 0.1
AIRSPEED_MIN_DECEL_KTS_PER_SEC = 0.5
AIRSPEED_MAX_DECEL_KTS_PER_SEC = 15.0
KTS_PER_FPS = 0.592483801295896
G_ACCEL_FTPS2 = 32.174
F35_EMPTY_WEIGHT_LBS = 29000.0
ENGINE_THRUST_LBF_IDLE_CUTOFF_PCT = 15.0
ENGINE_THRUST_LBF_MIL_PCT = 99.0
ENGINE_THRUST_LBF_AB_START_PCT = 100.0
ENGINE_THRUST_LBF_MAX_PCT = 150.0
ENGINE_THRUST_LBF_MIL = 28000.0
ENGINE_THRUST_LBF_MAX = 43000.0
LIFT_COEFF_MAX = 1.0
AERO_LIFT_CEILING_FT = 50000.0
AERO_LIFT_CEILING_MIN_FACTOR = 0.05
AERO_LIFT_ALTITUDE_EXP = 1.6
AERO_DRAG_BASE_LBF = 1500.0
AERO_DRAG_QUAD_COEFF = 0.028
AERO_DRAG_HIGH_SPEED_BREAK_FPS = 950.0
AERO_DRAG_HIGH_SPEED_COEFF = 0.05
CLIMB_ENERGY_EXCHANGE_FACTOR = 1.0
VERTICAL_LIFT_ALIGN_RATE_MIN = 1.0
VERTICAL_LIFT_ALIGN_RATE_MAX = 7.0
LOW_SPEED_DESCENT_NO_CLIMB_STALL_FACTOR = 1.2
STALL_NOSE_DROP_DPS_MAX = 14.0
BANK_NOSE_DIP_DPS_MAX = 10.0
PITCH_STABILITY_DPS = 4.0
GROUND_ROLLING_RESIST_KTS_PER_SEC = 8.0
GROUND_IDLE_BRAKING_KTS_PER_SEC = 130.0
GROUND_DECEL_DISABLE_THRUST_PCT = 30.0
GUN_FIRE_RATE_RPS = 55.0
ALTITUDE_MIN_SPEED_KTS = 150.0
ALTITUDE_KNEE_SPEED_KTS = 300.0
ALTITUDE_MAX_SPEED_KTS = 710.0
ALTITUDE_KNEE_FT = 25000.0
ALTITUDE_MAX_FT = 50000.0
ALTITUDE_PRE_KNEE_EXP = 1.2
ALTITUDE_POST_KNEE_EXP = 1.0
ALTITUDE_RATE_COEFF = 1.0
ALTITUDE_MAX_CLIMB_FPM = 45000.0
ALTITUDE_MAX_DESCENT_FPM = 15000.0
ALTITUDE_STALL_SPEED_KTS = 150.0
ALTITUDE_CLIMB_AT_STALL_FPM = 800.0
ALTITUDE_CLIMB_AT_MAX_SPEED_FPM = 14000.0
ALTITUDE_DESCENT_AT_STALL_FPM = 2000.0
ALTITUDE_DESCENT_AT_MAX_SPEED_FPM = 18000.0
ALTITUDE_STALL_SINK_BASE_FPM = 6000.0
ALTITUDE_STALL_SINK_PER_KT_FPM = 40.0
ATTITUDE_PITCH_RATE_MIN_DPS = 6.0
ATTITUDE_PITCH_RATE_MAX_DPS = 28.0
ATTITUDE_ROLL_RATE_MIN_DPS = 20.0
ATTITUDE_ROLL_RATE_MAX_DPS = 120.0
ATTITUDE_RUDDER_YAW_RATE_MAX_DPS = 18.0
ATTITUDE_PITCH_TO_YAW_COUPLE = 1.0
ATTITUDE_YAW_TO_PITCH_COUPLE = 1.0
ATTITUDE_BANK_TURN_RATE_SCALE = 1.0
ATTITUDE_BANK_TURN_RATE_MAX_DPS = 26.0
# Invert pitch/yaw inputs only when truly near inverted flight.
# This prevents relationship flips just from crossing +/-90 deg bank.
ATTITUDE_INPUT_INVERT_ROLL_ENTER_DEG = 170.0
ATTITUDE_INPUT_INVERT_ROLL_EXIT_DEG = 165.0
VERTICAL_RATE_FULL_SCALE_PITCH_DEG = 25.0
ATT_PITCH_FLIP_START_DEG = 87.0
ATT_PITCH_FLIP_END_DEG = 93.0
GEAR_UP_MIN_AIRSPEED_KTS = 150.0


# Export all config symbols (including underscore-prefixed helpers) so
# `from main_config import *` preserves existing references in main.py.
__all__ = [name for name in globals().keys() if not name.startswith("__")]

_POWER_PANEL_BUTTON_RULES: Dict[str, Dict[str, object]] = {
    "BAT": {"type": "toggle", "off": "BAT OFF.png", "on": "BAT ON.png"},
    "ICC3": {"type": "toggle", "off": "ICC3 OFF.png", "on": "ICC3 ON.png"},
    "ICC2": {"type": "toggle", "off": "ICC2 OFF.png", "on": "ICC2 ON.png"},
    "ICC1": {"type": "toggle", "off": "ICC1 OFF.png", "on": "ICC1 ON.png"},
    "CAB_PRESS": {
        "type": "tri",
        "norm": "CAB PRES NORM.png",
        "dump": "CAB PRES DUMP.png",
        "ram": "CAB PRES RAM.png",
    },
    "IPP": {
        "type": "hold_lr",
        "auto": "IPP AUTO.png",
        "left": "IPP OFF.png",
        "right": "IPP START.png",
    },
    "EMER": {"type": "press", "image": "EMER BUTTON.png"},
}
_THROTTLE_PANEL_BUTTON_RULES: Dict[str, Dict[str, object]] = {
    "CANOPY": {
        "type": "hold_lr_tri",
        "up": "CANOPY UP.png",
        "center": "CANOPY CENTER.png",
        "down": "CANOPY DOWN.png",
    },
    "ENGINE": {
        "type": "tri_lr",
        "left": "ENGINE RUN.png",
        "center": "ENGINE OFF.png",
        "right": "ENGINE MOTOR.png",
    },
    "FCS_RESET": {"type": "toggle", "up": "FCS RESET UP.png", "down": "FCS RESET DOWN.png"},
    "RUDDER": {
        "type": "tri_lr",
        "left": "RUDDER LEFT.png",
        "center": "RUDDER CENTER.png",
        "right": "RUDDER RIGHT.png",
    },
    "VS_BIT": {"type": "press", "image": "VS BIT BUTTON.png"},
}
_DISPLAY_CONTROL_BUTTON_RULES: Dict[str, Dict[str, object]] = {
    "BRT_DOWN": {"type": "button", "image": "BRT DOWN.png"},
    "BRT_UP": {"type": "button", "image": "BRT UP.png"},
    "MFD": {
        "type": "tri_lr",
        "right": "MFD DAY.png",
        "center": "MFD NIGHT.png",
        "left": "MFD OFF.png",
    },
}
_MASTER_ARM_BUTTON_RULES: Dict[str, Dict[str, object]] = {
    "DIAL_A": {"type": "dial", "image": "DIAL A.png"},
    "DIAL_B": {"type": "dial", "image": "DIAL B.png"},
    "DIAL_C": {"type": "dial", "image": "DIAL C.png"},
    "MASTER_ARM": {"type": "toggle", "off": "MASTER ARM OFF.png", "on": "MASTER ARM ON.png"},
}
_CONSOLE_LEFT_BUTTON_RULES: Dict[str, Dict[str, object]] = {
    "JETT": {
        "type": "tri_lr",
        "ext": "JETT EXT.png",
        "sel": "JETT SEL.png",
        "all": "JETT ALL.png",
    },
    "PARKING_BRAKE": {
        "type": "toggle",
        "on": "PARKING BRAKE ON.png",
        "off": "PARKING BRAKE OFF.png",
    },
    "GEAR": {
        "type": "quad",
        "down_off": "GEAR DOWN OFF.png",
        "down_on": "GEAR DOWN ON.png",
        "up_off": "GEAR UP OFF.png",
        "up_on": "GEAR UP ON.png",
    },
}

PMD_STORES_STATION_ORDER: List[str] = [
    "STA1",
    "STA2",
    "STA3",
    "STA4",
    "STA5",
    "STA7",
    "STA8",
    "STA9",
    "STA10",
    "STA11",
]
PMD_STORES_EXTERNAL_STATIONS = {"STA1", "STA2", "STA3", "STA9", "STA10", "STA11"}
PMD_STORES_INTERNAL_STATIONS = {"STA4", "STA5", "STA7", "STA8"}
# These stations support only air-to-air stores (no AS weapons).
PMD_STORES_AA_ONLY_STATIONS = {"STA1", "STA5", "STA7", "STA11"}
PMD_STORES_DEFAULT_LOADOUT: Dict[str, str] = {
    "STA4": "GBU-38",
    "STA5": "AIM-120",
    # Internal stations only, mirrored.
    "STA8": "GBU-38",
    "STA7": "AIM-120",
}
PHM_SYSTEM_LCN_PREFIX: Dict[str, str] = {
    "AIR_FRM": "20",
    "PROP": "45",
    "EPS": "24",
    "FCS": "27",
    "FPS": "26",
    "FUEL": "28",
    "GEAR": "32",
    "HYD": "29",
    "LIF_SUP": "60",
    "PTMS": "21",
    "VSP": "31",
    "COM_NAV": "23",
    "DAS": "97",
    "DISPL": "46",
    "EW": "94",
    "GUN": "94",
    "EOTS": "97",
    "MSP": "96",
    "RADAR": "96",
    "RIUS": "93",
    "SRES": "94",
    "LIGHTG": "33",
}

# Keep this at end of module so underscore-prefixed constants declared below
# early sections are included in wildcard imports.
__all__ = [name for name in globals().keys() if not name.startswith("__")]
