from formats import *  # noqa: F401,F403


class SmsFormat(FormatBase):
    _cached_layers: Dict[Tuple[str, bool], Optional[pygame.Surface]] = {}
    _cached_store_icons: Dict[Tuple[str, Optional[Tuple[int, int, int]]], Optional[pygame.Surface]] = {}
    _inv_prog_bottom_overlay_cache: Dict[Tuple[Tuple[str, ...], str, str], Optional[pygame.Surface]] = {}
    _stores_json_cache: Dict[str, Any] = {}
    _stores_json_cache_path: str = ""
    _stores_json_cache_mtime: Optional[float] = None
    _INV_TYPE_ORDER: List[str] = [
        "SRM",
        "MRM",
        "GP",
        "GBU",
        "AGM",
        "PGM",
        "CBU",
        "PODTK",
        "GUN",
        "OTHER",
        "SRMTT",
        "MRMTT",
        "LRMTT",
    ]
    _INV_GBU_FUZE_PROFILES: Dict[str, List[Tuple[str, List[str]]]] = {
        "GBU31": [
            ("FMU152", ["INST", "DLY1", "DLY2", "DLY3"]),
            ("FMU139", ["INST", "DLY1", "DLY2"]),
            ("DSU33\nFMU152", ["AIR\nBURST", "AIR\nBURST\nIMPACT"]),
            ("DSU33\nFMU139", ["AIR\nBURST", "AIR\nBURST\nIMPACT"]),
            ("M904\nF152", ["INST", "DLY"]),
            ("FMU152\nFMU143", ["INST", "DLY1", "DLY2"]),
            ("FMU139\nFMU143", ["INST", "DLY1", "DLY2"]),
        ],
        "GBU32": [
            ("FMU152", ["INST", "DLY1", "DLY2", "DLY3"]),
            ("FMU139", ["INST", "DLY1", "DLY2"]),
            ("DSU33\nFMU152", ["AIR\nBURST", "AIR\nBURST\nIMPACT"]),
            ("DSU33\nFMU139", ["AIR\nBURST", "AIR\nBURST\nIMPACT"]),
            ("M904\nF152", ["INST", "DLY"]),
        ],
        "GBU38": [
            ("FMU152", ["INST", "DLY1", "DLY2", "DLY3"]),
            ("FMU139", ["INST", "DLY1", "DLY2"]),
            ("DSU33\nFMU152", ["AIR\nBURST", "AIR\nBURST\nIMPACT"]),
            ("DSU33\nFMU139", ["AIR\nBURST", "AIR\nBURST\nIMPACT"]),
            ("M904\nF152", ["INST", "DLY"]),
        ],
        "GBU12": [
            ("FMU152", ["INST", "DLY1", "DLY2", "DLY3"]),
            ("FMU139", ["INST", "DLY1", "DLY2"]),
            ("DSU33\nFMU152", ["AIR\nBURST", "AIR\nBURST\nIMPACT"]),
            ("DSU33\nFMU139", ["AIR\nBURST", "AIR\nBURST\nIMPACT"]),
            ("M904\nF152", ["INST", "DLY"]),
        ],
        "GBU16": [
            ("FMU152", ["INST", "DLY1", "DLY2", "DLY3"]),
            ("FMU139", ["INST", "DLY1", "DLY2"]),
            ("DSU33\nFMU152", ["AIR\nBURST", "AIR\nBURST\nIMPACT"]),
            ("DSU33\nFMU139", ["AIR\nBURST", "AIR\nBURST\nIMPACT"]),
            ("M904\nF152", ["INST", "DLY"]),
        ],
        "GBU10": [
            ("FMU152", ["INST", "DLY1", "DLY2", "DLY3"]),
            ("FMU139", ["INST", "DLY1", "DLY2"]),
            ("DSU33\nFMU152", ["AIR\nBURST", "AIR\nBURST\nIMPACT"]),
            ("DSU33\nFMU139", ["AIR\nBURST", "AIR\nBURST\nIMPACT"]),
            ("M904\nF152", ["INST", "DLY"]),
        ],
        "GBU24": [
            ("FMU152", ["INST", "DLY1", "DLY2", "DLY3"]),
            ("FMU139", ["INST", "DLY1", "DLY2"]),
            ("DSU33\nFMU152", ["AIR\nBURST", "AIR\nBURST\nIMPACT"]),
            ("DSU33\nFMU139", ["AIR\nBURST", "AIR\nBURST\nIMPACT"]),
            ("M904\nF152", ["INST", "DLY"]),
        ],
        "GBU39": [
            ("FMU152", ["INST", "DLY1", "DLY2", "DLY3"]),
            ("FMU139", ["INST", "DLY1", "DLY2"]),
            ("DSU33\nFMU152", ["AIR\nBURST", "AIR\nBURST\nIMPACT"]),
            ("DSU33\nFMU139", ["AIR\nBURST", "AIR\nBURST\nIMPACT"]),
            ("M904\nF152", ["INST", "DLY"]),
        ],
        "GBU53": [
            ("FMU152", ["INST", "DLY1", "DLY2", "DLY3"]),
            ("FMU139", ["INST", "DLY1", "DLY2"]),
            ("DSU33\nFMU152", ["AIR\nBURST", "AIR\nBURST\nIMPACT"]),
            ("DSU33\nFMU139", ["AIR\nBURST", "AIR\nBURST\nIMPACT"]),
            ("M904\nF152", ["INST", "DLY"]),
        ],
    }
    _INV_WPN_TO_STORE_ID: Dict[str, str] = {
        "AIM9X": "AIM-9X",
        "AIM120C": "AIM-120",
        "AIM132": "AIM-132",
        "AGM154A": "AGM-154",
        "AGM154C": "AGM-154",
        "AGM158": "AGM-158",
        "CBU103": "CBU-103",
        "GBU10": "GBU-10",
        "GBU12": "GBU-12",
        "GBU16": "GBU-16",
        "GBU24": "GBU-24",
        "GBU31": "GBU-31",
        "GBU32": "GBU-32",
        "GBU38": "GBU-38",
    }
    _INV_CAP: Dict[str, Dict[str, Dict[str, List[Tuple[str, int]]]]] = {
        "STA1": {
            "SRM": {"LAU151A": [("AIM9X", 1), ("AIM132", 1)]},
            "MRM": {"LAU151A": [("AIM120C", 1)]},
        },
        "STA11": {
            "SRM": {"LAU151A": [("AIM9X", 1), ("AIM132", 1)]},
            "MRM": {"LAU151A": [("AIM120C", 1)]},
        },
        "STA2": {
            "MRM": {"LAU151A": [("AIM120C", 1)]},
            "AGM": {"BRU68": [("AGM154A", 1), ("AGM154C", 1)], "PYLON": [("AGM158", 1)]},
            "GBU": {"BRU68": [("GBU12", 1), ("GBU16", 1), ("GBU31", 1), ("GBU32", 1), ("GBU38", 1), ("GBU10", 1), ("GBU24", 1)]},
            "GP": {"BRU68": [("MK82", 1), ("MK83", 1), ("MK84", 1)]},
            "CBU": {"BRU68": [("CBU103", 1), ("CBU105", 1), ("CBU99", 1), ("CBU100", 1)]},
            "PGM": {"BRU68": [("GBU12", 1), ("GBU16", 1), ("GBU31", 1), ("GBU32", 1), ("GBU38", 1), ("GBU10", 1), ("GBU24", 1), ("AGM154A", 1), ("AGM154C", 1)]},
            "OTHER": {"BRU68": [("BDU57", 1), ("BDU58", 1), ("BDU60", 1)], "PYLON": [("MXU648", 1)]},
        },
        "STA10": {
            "MRM": {"LAU151A": [("AIM120C", 1)]},
            "AGM": {"BRU68": [("AGM154A", 1), ("AGM154C", 1)], "PYLON": [("AGM158", 1)]},
            "GBU": {"BRU68": [("GBU12", 1), ("GBU16", 1), ("GBU31", 1), ("GBU32", 1), ("GBU38", 1), ("GBU10", 1), ("GBU24", 1)]},
            "GP": {"BRU68": [("MK82", 1), ("MK83", 1), ("MK84", 1)]},
            "CBU": {"BRU68": [("CBU103", 1), ("CBU105", 1), ("CBU99", 1), ("CBU100", 1)]},
            "PGM": {"BRU68": [("GBU12", 1), ("GBU16", 1), ("GBU31", 1), ("GBU32", 1), ("GBU38", 1), ("GBU10", 1), ("GBU24", 1), ("AGM154A", 1), ("AGM154C", 1)]},
            "OTHER": {"BRU68": [("BDU57", 1), ("BDU58", 1), ("BDU60", 1)], "PYLON": [("MXU648", 1)]},
        },
        "STA3": {
            "MRM": {"LAU151A": [("AIM120C", 1)]},
            "AGM": {"BRU68": [("AGM154A", 1), ("AGM154C", 1)], "PYLON": [("AGM158", 1)]},
            "GBU": {"BRU68": [("GBU12", 1), ("GBU16", 1), ("GBU31", 1), ("GBU32", 1), ("GBU38", 1), ("GBU10", 1), ("GBU24", 1)]},
            "GP": {"BRU68": [("MK82", 1), ("MK83", 1), ("MK84", 1)]},
            "CBU": {"BRU68": [("CBU103", 1), ("CBU105", 1), ("CBU99", 1), ("CBU100", 1)]},
            "PGM": {"BRU68": [("GBU12", 1), ("GBU16", 1), ("GBU31", 1), ("GBU32", 1), ("GBU38", 1), ("GBU10", 1), ("GBU24", 1), ("AGM154A", 1), ("AGM154C", 1)]},
            "OTHER": {"BRU68": [("BDU57", 1), ("BDU58", 1), ("BDU60", 1)], "PYLON": [("MXU648", 1)]},
        },
        "STA9": {
            "MRM": {"LAU151A": [("AIM120C", 1)]},
            "AGM": {"BRU68": [("AGM154A", 1), ("AGM154C", 1)], "PYLON": [("AGM158", 1)]},
            "GBU": {"BRU68": [("GBU12", 1), ("GBU16", 1), ("GBU31", 1), ("GBU32", 1), ("GBU38", 1), ("GBU10", 1), ("GBU24", 1)]},
            "GP": {"BRU68": [("MK82", 1), ("MK83", 1), ("MK84", 1)]},
            "CBU": {"BRU68": [("CBU103", 1), ("CBU105", 1), ("CBU99", 1), ("CBU100", 1)]},
            "PGM": {"BRU68": [("GBU12", 1), ("GBU16", 1), ("GBU31", 1), ("GBU32", 1), ("GBU38", 1), ("GBU10", 1), ("GBU24", 1), ("AGM154A", 1), ("AGM154C", 1)]},
            "OTHER": {"BRU68": [("BDU57", 1), ("BDU58", 1), ("BDU60", 1)], "PYLON": [("MXU648", 1)]},
        },
        "STA4": {
            "GBU": {"BRU61": [("GBU39", 4), ("GBU53", 4)], "BRU68": [("GBU12", 1), ("GBU31", 1), ("GBU32", 1), ("GBU38", 1), ("GBU10", 1), ("GBU24", 1)]},
            "AGM": {"BRU68": [("AGM154A", 1), ("AGM154C", 1), ("AGM158", 1)]},
            "CBU": {"BRU68": [("CBU103", 1), ("CBU105", 1)]},
            "PGM": {"BRU61": [("GBU39", 4), ("GBU53", 4)], "BRU68": [("GBU12", 1), ("GBU31", 1), ("GBU32", 1), ("GBU38", 1), ("GBU10", 1), ("GBU24", 1), ("AGM154A", 1), ("AGM154C", 1)]},
        },
        "STA8": {
            "GBU": {"BRU61": [("GBU39", 4), ("GBU53", 4)], "BRU68": [("GBU12", 1), ("GBU31", 1), ("GBU32", 1), ("GBU38", 1), ("GBU10", 1), ("GBU24", 1)]},
            "AGM": {"BRU68": [("AGM154A", 1), ("AGM154C", 1), ("AGM158", 1)]},
            "CBU": {"BRU68": [("CBU103", 1), ("CBU105", 1)]},
            "PGM": {"BRU61": [("GBU39", 4), ("GBU53", 4)], "BRU68": [("GBU12", 1), ("GBU31", 1), ("GBU32", 1), ("GBU38", 1), ("GBU10", 1), ("GBU24", 1), ("AGM154A", 1), ("AGM154C", 1)]},
        },
        "STA5": {"MRM": {"LAU147": [("AIM120C", 1)]}},
        "STA7": {"MRM": {"LAU147": [("AIM120C", 1)]}},
        "STA6": {"GUN": {"GUN": [("GAU22A", 1)]}},
    }

    def __init__(self) -> None:
        self.name = "SMS"

    @classmethod
    def _ui_scope_keys(cls) -> Set[str]:
        return {
            "cntl_submenu_open",
            "cntl_inv_prog_open",
            "cntl_inv_load_open",
            "cntl_inv_load_type_menu_open",
            "cntl_inv_load_type_page",
            "cntl_inv_load_selected_field",
            "cntl_inv_load_type_value",
            "cntl_inv_load_rack_value",
            "cntl_inv_load_wpn_value",
            "cntl_inv_load_fuze_value",
            "cntl_inv_load_fuze_mode_value",
            "cntl_inv_load_fuze_mode_open",
            "cntl_inv_load_qty_value",
            "cntl_inv_load_qty_max",
            "cntl_inv_load_qty_input",
            "cntl_inv_selected_stations",
            "excm_arm_confirm_pending",
        }

    @classmethod
    def _scope_idx(cls) -> object:
        key = SMS_STATE.get("_popup_anchor_scope_key", None)
        if key is not None:
            return key
        try:
            idx = int(SMS_STATE.get("_popup_anchor_portal_idx", 0))
        except Exception:
            idx = 0
        return f"portal:{max(0, min(3, idx))}"

    def _set_popup_anchor_scope_key(self, scope_key: object) -> None:
        SMS_STATE["_popup_anchor_scope_key"] = scope_key

    @classmethod
    def _scope_defaults(cls) -> Dict[str, object]:
        return {
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
            "cntl_inv_selected_stations": [],
            "excm_arm_confirm_pending": 0,
        }

    @classmethod
    def _scope_state(cls) -> Dict[str, object]:
        by_portal = SMS_STATE.get("_popup_ui_by_portal")
        if not isinstance(by_portal, dict):
            by_portal = {}
            SMS_STATE["_popup_ui_by_portal"] = by_portal
        key = cls._scope_idx()
        state = by_portal.get(key)
        if not isinstance(state, dict):
            state = {}
            by_portal[key] = state
        defaults = cls._scope_defaults()
        for key, value in defaults.items():
            if key not in state:
                state[key] = list(value) if isinstance(value, list) else value
        return state

    @classmethod
    def _ui_get(cls, key: str, default: object) -> object:
        if key in cls._ui_scope_keys():
            return cls._scope_state().get(key, default)
        return SMS_STATE.get(key, default)

    @classmethod
    def _ui_set(cls, key: str, value: object) -> None:
        if key in cls._ui_scope_keys():
            cls._scope_state()[key] = value
        SMS_STATE[key] = value

    @staticmethod
    def _master_arm_on() -> bool:
        try:
            panel_state = PANEL_BUTTON_STATES.get("MASTER ARM", {})
            if isinstance(panel_state, dict):
                return str(panel_state.get("MASTER_ARM", "OFF")).upper() == "ON"
        except Exception:
            pass
        return False

    @staticmethod
    def _cntl_submenu_open() -> bool:
        try:
            return bool(int(SmsFormat._ui_get("cntl_submenu_open", 0)))
        except Exception:
            return bool(SmsFormat._ui_get("cntl_submenu_open", False))

    @staticmethod
    def _set_cntl_submenu_open(opened: bool) -> None:
        SmsFormat._ui_set("cntl_submenu_open", 1 if opened else 0)
        if not opened:
            SmsFormat._ui_set("cntl_inv_prog_open", 0)
            SmsFormat._ui_set("cntl_inv_load_open", 0)
            SmsFormat._ui_set("cntl_inv_load_type_menu_open", 0)
            SmsFormat._ui_set("cntl_inv_load_type_page", 0)
            SmsFormat._ui_set("cntl_inv_load_fuze_mode_open", 0)

    @staticmethod
    def _cntl_inv_prog_open() -> bool:
        try:
            return bool(int(SmsFormat._ui_get("cntl_inv_prog_open", 0)))
        except Exception:
            return bool(SmsFormat._ui_get("cntl_inv_prog_open", False))

    @staticmethod
    def _set_cntl_inv_prog_open(opened: bool) -> None:
        SmsFormat._ui_set("cntl_inv_prog_open", 1 if opened else 0)
        if not opened:
            SmsFormat._ui_set("cntl_inv_load_open", 0)
            SmsFormat._ui_set("cntl_inv_load_type_menu_open", 0)
            SmsFormat._ui_set("cntl_inv_load_type_page", 0)
            SmsFormat._ui_set("cntl_inv_load_fuze_mode_open", 0)

    @staticmethod
    def _cntl_inv_load_open() -> bool:
        try:
            return bool(int(SmsFormat._ui_get("cntl_inv_load_open", 0)))
        except Exception:
            return bool(SmsFormat._ui_get("cntl_inv_load_open", False))

    @staticmethod
    def _set_cntl_inv_load_open(opened: bool) -> None:
        SmsFormat._ui_set("cntl_inv_load_open", 1 if opened else 0)
        if not opened:
            SmsFormat._ui_set("cntl_inv_load_type_menu_open", 0)
            SmsFormat._ui_set("cntl_inv_load_type_page", 0)
            SmsFormat._ui_set("cntl_inv_load_fuze_mode_open", 0)
            SmsFormat._ui_set("cntl_inv_load_selected_field", "")
            SmsFormat._ui_set("cntl_inv_load_qty_input", "")

    @staticmethod
    def _cntl_inv_load_type_menu_open() -> bool:
        try:
            return bool(int(SmsFormat._ui_get("cntl_inv_load_type_menu_open", 0)))
        except Exception:
            return bool(SmsFormat._ui_get("cntl_inv_load_type_menu_open", False))

    @staticmethod
    def _set_cntl_inv_load_type_menu_open(opened: bool) -> None:
        SmsFormat._ui_set("cntl_inv_load_type_menu_open", 1 if opened else 0)
        if not opened:
            SmsFormat._ui_set("cntl_inv_load_fuze_mode_open", 0)

    @staticmethod
    def _cntl_inv_load_type_page() -> int:
        try:
            idx = int(SmsFormat._ui_get("cntl_inv_load_type_page", 0))
        except Exception:
            idx = 0
        if idx < 0:
            idx = 0
        SmsFormat._ui_set("cntl_inv_load_type_page", idx)
        return idx

    @staticmethod
    def _set_cntl_inv_load_type_page(idx: int) -> None:
        SmsFormat._ui_set("cntl_inv_load_type_page", max(0, int(idx)))

    @staticmethod
    def _cntl_inv_load_selected_field() -> str:
        token = str(SmsFormat._ui_get("cntl_inv_load_selected_field", "")).upper().strip()
        if token in {"TYPE", "RACK", "WPN", "FUZE", "QNTY"}:
            return token
        return ""

    @staticmethod
    def _set_cntl_inv_load_selected_field(field: str) -> None:
        token = str(field).upper().strip()
        SmsFormat._ui_set("cntl_inv_load_selected_field", token if token in {"TYPE", "RACK", "WPN", "FUZE", "QNTY"} else "")
        if token != "FUZE":
            SmsFormat._ui_set("cntl_inv_load_fuze_mode_open", 0)

    @staticmethod
    def _cntl_inv_load_type_value() -> str:
        return str(SmsFormat._ui_get("cntl_inv_load_type_value", "")).upper().strip()

    @staticmethod
    def _set_cntl_inv_load_type_value(value: str) -> None:
        SmsFormat._ui_set("cntl_inv_load_type_value", str(value).upper().strip())

    @staticmethod
    def _inv_type_value() -> str:
        return str(SmsFormat._ui_get("cntl_inv_load_type_value", "")).upper().strip()

    @staticmethod
    def _inv_rack_value() -> str:
        return str(SmsFormat._ui_get("cntl_inv_load_rack_value", "")).upper().strip()

    @staticmethod
    def _inv_wpn_value() -> str:
        return str(SmsFormat._ui_get("cntl_inv_load_wpn_value", "")).upper().strip()

    @staticmethod
    def _set_inv_rack_value(value: str) -> None:
        SmsFormat._ui_set("cntl_inv_load_rack_value", str(value).upper().strip())

    @staticmethod
    def _set_inv_wpn_value(value: str) -> None:
        SmsFormat._ui_set("cntl_inv_load_wpn_value", str(value).upper().strip())

    @staticmethod
    def _inv_fuze_value() -> str:
        return str(SmsFormat._ui_get("cntl_inv_load_fuze_value", "")).upper().strip()

    @staticmethod
    def _set_inv_fuze_value(value: str) -> None:
        SmsFormat._ui_set("cntl_inv_load_fuze_value", str(value).upper().strip())

    @staticmethod
    def _inv_fuze_mode_value() -> str:
        return str(SmsFormat._ui_get("cntl_inv_load_fuze_mode_value", "")).upper().strip()

    @staticmethod
    def _set_inv_fuze_mode_value(value: str) -> None:
        SmsFormat._ui_set("cntl_inv_load_fuze_mode_value", str(value).upper().strip())

    @staticmethod
    def _cntl_inv_load_fuze_mode_open() -> bool:
        try:
            return bool(int(SmsFormat._ui_get("cntl_inv_load_fuze_mode_open", 0)))
        except Exception:
            return bool(SmsFormat._ui_get("cntl_inv_load_fuze_mode_open", False))

    @staticmethod
    def _set_cntl_inv_load_fuze_mode_open(opened: bool) -> None:
        SmsFormat._ui_set("cntl_inv_load_fuze_mode_open", 1 if opened else 0)

    @staticmethod
    def _inv_qty_value() -> int:
        try:
            return max(0, int(SmsFormat._ui_get("cntl_inv_load_qty_value", 0)))
        except Exception:
            return 0

    @staticmethod
    def _set_inv_qty_value(value: int) -> None:
        try:
            iv = int(value)
        except Exception:
            iv = 0
        SmsFormat._ui_set("cntl_inv_load_qty_value", max(0, iv))

    @staticmethod
    def _inv_qty_max() -> int:
        try:
            return max(0, int(SmsFormat._ui_get("cntl_inv_load_qty_max", 0)))
        except Exception:
            return 0

    @staticmethod
    def _set_inv_qty_max(value: int) -> None:
        try:
            iv = int(value)
        except Exception:
            iv = 0
        SmsFormat._ui_set("cntl_inv_load_qty_max", max(0, iv))

    @staticmethod
    def _sms_live_train_idx() -> int:
        try:
            idx = int(SMS_STATE.get("live_train_idx", 0))
        except Exception:
            idx = 0
        if idx not in (0, 1):
            idx = 0
        SMS_STATE["live_train_idx"] = int(idx)
        SMS_STATE["cntl_live_train_idx"] = int(idx)
        return int(idx)

    @staticmethod
    def _set_sms_live_train_idx(idx: int) -> None:
        value = 1 if int(idx) == 1 else 0
        SMS_STATE["live_train_idx"] = value
        SMS_STATE["cntl_live_train_idx"] = value

    @staticmethod
    def _display_uses_training_stores() -> bool:
        return SmsFormat._master_arm_on() and SmsFormat._sms_live_train_idx() == 1

    @staticmethod
    def _active_display_store_loads_key() -> str:
        return "training_store_loads" if SmsFormat._display_uses_training_stores() else "store_loads"

    @staticmethod
    def _active_inv_store_loads_key() -> str:
        if bool(SMS_STATE.get("cntl_inv_actual_request_mode", 0)):
            return "store_loads"
        return "training_store_loads" if SmsFormat._cntl_live_train_idx() == 1 else "store_loads"

    @staticmethod
    def _store_loads_for_key(key: str) -> Dict[str, object]:
        token = "training_store_loads" if str(key) == "training_store_loads" else "store_loads"
        raw = SMS_STATE.get(token, {})
        if not isinstance(raw, dict):
            raw = {}
            SMS_STATE[token] = raw
        return raw

    @staticmethod
    def _active_inv_store_loads() -> Dict[str, object]:
        return SmsFormat._store_loads_for_key(SmsFormat._active_inv_store_loads_key())

    @staticmethod
    def _active_display_store_loads() -> Dict[str, object]:
        return SmsFormat._store_loads_for_key(SmsFormat._active_display_store_loads_key())

    @staticmethod
    def _mark_active_inv_store_loads_initialized() -> None:
        if SmsFormat._active_inv_store_loads_key() == "training_store_loads":
            SMS_STATE["training_stores_thought_initialized"] = 1
        else:
            SMS_STATE["stores_thought_initialized"] = 1

    @staticmethod
    def _store_icon_tint_color(training: bool) -> Tuple[int, int, int]:
        return (0, 128, 255) if bool(training) else (0, 255, 0)

    @staticmethod
    def _active_inv_store_icon_tint_color() -> Tuple[int, int, int]:
        return SmsFormat._store_icon_tint_color(SmsFormat._active_inv_store_loads_key() == "training_store_loads")

    @staticmethod
    def _active_display_store_icon_tint_color() -> Tuple[int, int, int]:
        return SmsFormat._store_icon_tint_color(SmsFormat._active_display_store_loads_key() == "training_store_loads")

    @staticmethod
    def _stores_json_path() -> Path:
        try:
            writable = writable_path("stores.json")
            if writable.exists():
                return writable
        except Exception:
            pass
        return resource_path("stores.json")

    @staticmethod
    def _stores_json() -> Dict[str, Any]:
        path = SmsFormat._stores_json_path()
        path_key = str(path)
        try:
            mtime = path.stat().st_mtime
        except Exception:
            mtime = None
        if (
            SmsFormat._stores_json_cache_path == path_key
            and SmsFormat._stores_json_cache_mtime == mtime
            and isinstance(SmsFormat._stores_json_cache, dict)
            and len(SmsFormat._stores_json_cache) > 0
        ):
            return SmsFormat._stores_json_cache
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            cfg = raw if isinstance(raw, dict) else {}
        except Exception:
            cfg = {}
        SmsFormat._stores_json_cache_path = path_key
        SmsFormat._stores_json_cache_mtime = mtime
        SmsFormat._stores_json_cache = cfg
        return cfg

    @staticmethod
    def _inv_inventory_config() -> Dict[str, Any]:
        raw = SmsFormat._stores_json().get("inventory", {})
        return raw if isinstance(raw, dict) else {}

    @staticmethod
    def _inv_norm_token(value: object) -> str:
        return re.sub(r"[^A-Z0-9]", "", str(value).upper().strip())

    @staticmethod
    def _inv_type_order() -> List[str]:
        inv = SmsFormat._inv_inventory_config()
        raw = inv.get("type_order", [])
        out: List[str] = []
        if isinstance(raw, list):
            for item in raw:
                token = str(item).upper().strip()
                if token != "" and token not in out:
                    out.append(token)
        return out

    @staticmethod
    def _inv_station_caps(station: str) -> Dict[str, Any]:
        inv = SmsFormat._inv_inventory_config()
        stations = inv.get("stations", {})
        if not isinstance(stations, dict):
            return {}
        raw = stations.get(str(station).upper().strip(), {})
        return raw if isinstance(raw, dict) else {}

    @staticmethod
    def _inv_rack_caps(station: str, type_value: str) -> Dict[str, Any]:
        raw = SmsFormat._inv_station_caps(station).get(str(type_value).upper().strip(), {})
        return raw if isinstance(raw, dict) else {}

    @staticmethod
    def _inv_weapon_entries(station: str, type_value: str, rack_value: str) -> List[Tuple[str, int]]:
        racks = SmsFormat._inv_rack_caps(station, type_value)
        raw_entries = racks.get(str(rack_value).upper().strip(), [])
        if not isinstance(raw_entries, list):
            return []
        out: List[Tuple[str, int]] = []
        for entry in raw_entries:
            weapon = ""
            qty = 1
            if isinstance(entry, dict):
                weapon = str(entry.get("weapon", "")).upper().strip()
                try:
                    qty = int(entry.get("qty", 1))
                except Exception:
                    qty = 1
            elif isinstance(entry, (list, tuple)) and len(entry) >= 1:
                weapon = str(entry[0]).upper().strip()
                if len(entry) >= 2:
                    try:
                        qty = int(entry[1])
                    except Exception:
                        qty = 1
            if weapon != "":
                out.append((weapon, max(0, int(qty))))
        return out

    @staticmethod
    def _inv_weapon_aliases() -> Dict[str, str]:
        inv = SmsFormat._inv_inventory_config()
        raw = inv.get("weapon_aliases", {})
        out: Dict[str, str] = {}
        if isinstance(raw, dict):
            for key, value in raw.items():
                token = str(key).upper().strip()
                mapped = str(value).strip()
                if token != "" and mapped != "":
                    out[token] = mapped
        return out

    @staticmethod
    def _inv_fuze_profiles_for_weapon(wpn_value: str) -> List[Tuple[str, List[str]]]:
        inv = SmsFormat._inv_inventory_config()
        raw_profiles = inv.get("fuzes", inv.get("fuze_profiles", {}))
        if not isinstance(raw_profiles, dict):
            raw_profiles = {}
        token = SmsFormat._inv_norm_token(wpn_value)
        raw_match: Any = None
        for key, value in raw_profiles.items():
            if SmsFormat._inv_norm_token(key) == token:
                raw_match = value
                break
        if not isinstance(raw_match, list):
            return []
        out: List[Tuple[str, List[str]]] = []
        for entry in raw_match:
            fuze = ""
            modes_raw: Any = []
            if isinstance(entry, dict):
                fuze = str(entry.get("fuze", "")).upper().strip()
                modes_raw = entry.get("modes", [])
            elif isinstance(entry, (list, tuple)) and len(entry) >= 1:
                fuze = str(entry[0]).upper().strip()
                modes_raw = entry[1] if len(entry) >= 2 else []
            if fuze == "":
                continue
            modes: List[str] = []
            if isinstance(modes_raw, (list, tuple)):
                for mode in modes_raw:
                    mode_token = "\n".join(line.strip() for line in str(mode).upper().split("\n") if line.strip() != "")
                    if mode_token != "" and mode_token not in modes:
                        modes.append(mode_token)
            out.append((fuze, modes))
        return out

    @staticmethod
    def _inv_is_gbu_wpn(wpn_value: str) -> bool:
        if len(SmsFormat._inv_fuze_profiles_for_weapon(wpn_value)) > 0:
            return True
        token = re.sub(r"[^A-Z0-9]", "", str(wpn_value).upper().strip())
        return token.startswith("GBU")

    @staticmethod
    def _inv_available_fuzes(wpn_value: str) -> List[str]:
        out: List[str] = []
        for fuze_name, _mode_list in SmsFormat._inv_fuze_profiles_for_weapon(wpn_value):
            fuze_token = "\n".join(line.strip() for line in str(fuze_name).upper().split("\n") if line.strip() != "")
            if fuze_token != "" and fuze_token not in out:
                out.append(fuze_token)
        return out

    @staticmethod
    def _inv_available_fuze_modes(wpn_value: str, fuze_value: str) -> List[str]:
        fuze_token = "\n".join(line.strip() for line in str(fuze_value).upper().split("\n") if line.strip() != "")
        if SmsFormat._inv_norm_token(wpn_value) == "" or fuze_token == "":
            return []
        for fuze_name, mode_list in SmsFormat._inv_fuze_profiles_for_weapon(wpn_value):
            name_token = "\n".join(line.strip() for line in str(fuze_name).upper().split("\n") if line.strip() != "")
            if name_token != fuze_token:
                continue
            out: List[str] = []
            if isinstance(mode_list, (list, tuple)):
                for mode in mode_list:
                    mode_token = "\n".join(line.strip() for line in str(mode).upper().split("\n") if line.strip() != "")
                    if mode_token != "" and mode_token not in out:
                        out.append(mode_token)
            return out
        return []

    @staticmethod
    def _inv_resolve_store_weapon_id(wpn_value: str) -> str:
        token = str(wpn_value).upper().strip()
        if token == "":
            return ""
        weapons_raw = SmsFormat._stores_json().get("weapons", {})
        weapons = weapons_raw if isinstance(weapons_raw, dict) else {}
        aliases = SmsFormat._inv_weapon_aliases()
        candidates = [
            str(aliases.get(token, "")).strip(),
            str(SmsFormat._INV_WPN_TO_STORE_ID.get(token, "")).strip(),
            token,
        ]
        norm_token = SmsFormat._inv_norm_token(token)
        for candidate in candidates:
            if candidate != "" and candidate in weapons:
                return candidate
        for key in weapons.keys():
            if SmsFormat._inv_norm_token(key) == norm_token:
                return str(key)
        for candidate in candidates:
            if candidate != "":
                return candidate
        return token

    @staticmethod
    def _resolve_store_icon_path(filename: str) -> Optional[Path]:
        name = str(filename).strip().replace("\\", "/")
        if name == "":
            return None
        root = resource_path("icons", "SMS", "STORES")
        direct = root.joinpath(*[part for part in name.split("/") if part != ""])
        try:
            if direct.exists():
                return direct
        except Exception:
            pass
        basename = Path(name).name
        if basename == "":
            return None
        try:
            flat = root / basename
            if flat.exists():
                return flat
        except Exception:
            pass
        try:
            norm_target = SmsFormat._inv_norm_token(Path(basename).stem)
            for candidate in root.rglob("*.png"):
                if candidate.name.upper() == basename.upper():
                    return candidate
                if SmsFormat._inv_norm_token(candidate.stem) == norm_target:
                    return candidate
        except Exception:
            return None
        return None

    @staticmethod
    def _find_store_icon_name_for_weapon(*tokens: str) -> str:
        wanted = [SmsFormat._inv_norm_token(token) for token in tokens if str(token).strip() != ""]
        wanted = [token for token in wanted if token != ""]
        if len(wanted) <= 0:
            return ""
        root = resource_path("icons", "SMS", "STORES")
        try:
            for candidate in root.rglob("*.png"):
                if SmsFormat._inv_norm_token(candidate.stem) in wanted:
                    try:
                        return str(candidate.relative_to(root)).replace("\\", "/")
                    except Exception:
                        return str(candidate)
        except Exception:
            return ""
        return ""

    @staticmethod
    def _inv_store_icon_exists(icon_name: str) -> bool:
        return SmsFormat._resolve_store_icon_path(icon_name) is not None

    @staticmethod
    def _inv_store_load_metadata(wpn_value: str) -> Tuple[str, str, str]:
        token = str(wpn_value).upper().strip()
        store_id = SmsFormat._inv_resolve_store_weapon_id(token) or token
        weapons_raw = SmsFormat._stores_json().get("weapons", {})
        weapons = weapons_raw if isinstance(weapons_raw, dict) else {}
        meta = weapons.get(store_id, {})
        if not isinstance(meta, dict):
            meta = weapons.get(token, {})
        if not isinstance(meta, dict):
            meta = {}
        icon_name = str(meta.get("icon", "")).strip()
        if icon_name != "" and not SmsFormat._inv_store_icon_exists(icon_name):
            icon_name = ""
        if icon_name == "":
            icon_name = SmsFormat._find_store_icon_name_for_weapon(token, store_id)
        store_type = str(meta.get("type", "AS")).upper().strip()
        if store_type not in {"AS", "SRM", "MRM"}:
            store_type = "AS"
        return store_id, icon_name, store_type

    @staticmethod
    def _inv_apply_selected_store_request() -> None:
        selected = SmsFormat._inv_selected_stations()
        if len(selected) <= 0:
            return
        type_value = SmsFormat._inv_type_value()
        rack_value = SmsFormat._inv_rack_value()
        wpn_value = SmsFormat._inv_wpn_value()
        if type_value == "" or rack_value == "" or wpn_value == "":
            return
        qty_max = SmsFormat._inv_qty_max()
        qty_value = SmsFormat._inv_qty_value()
        if qty_max > 0:
            qty_value = max(1, min(qty_max, qty_value if qty_value > 0 else qty_max))
        else:
            qty_value = 0
        SmsFormat._set_inv_qty_value(qty_value)
        if bool(SMS_STATE.get("cntl_inv_actual_request_mode", 0)):
            SMS_STATE["cntl_inv_load_request"] = {
                "stations": list(selected),
                "type": str(type_value).upper().strip(),
                "rack": str(rack_value).upper().strip(),
                "weapon": str(wpn_value).upper().strip(),
                "fuze": str(SmsFormat._inv_fuze_value()).upper().strip(),
                "fuze_mode": str(SmsFormat._inv_fuze_mode_value()).upper().strip(),
                "qty": int(qty_value),
            }
            return
        store_key = SmsFormat._active_inv_store_loads_key()
        store_loads = SmsFormat._store_loads_for_key(store_key)
        store_id, icon_name, store_type = SmsFormat._inv_store_load_metadata(wpn_value)
        for sta in selected:
            station = str(sta).upper().strip()
            if station == "":
                continue
            store_loads[station] = {
                "weapon": store_id,
                "icon": icon_name,
                "type": store_type,
                "qty": int(qty_value),
                "inv_type": str(type_value).upper().strip(),
                "rack": str(rack_value).upper().strip(),
                "fuze": str(SmsFormat._inv_fuze_value()).upper().strip(),
                "fuze_mode": str(SmsFormat._inv_fuze_mode_value()).upper().strip(),
            }
        SMS_STATE[store_key] = store_loads
        SmsFormat._mark_active_inv_store_loads_initialized()
        SMS_STATE["cntl_inv_load_request"] = {}

    @staticmethod
    def _inv_available_types(selected_stations: Optional[List[str]] = None) -> List[str]:
        selected = selected_stations if selected_stations is not None else SmsFormat._inv_selected_stations()
        if len(selected) <= 0:
            return []
        common: Optional[Set[str]] = None
        for sta in selected:
            station_caps = SmsFormat._inv_station_caps(str(sta).upper().strip())
            keys = set(station_caps.keys())
            common = keys if common is None else (common & keys)
        if not common:
            return []
        ordered = [token for token in SmsFormat._inv_type_order() if token in common]
        for token in sorted(common):
            if token not in ordered:
                ordered.append(token)
        return ordered

    @staticmethod
    def _inv_available_racks(type_value: str, selected_stations: Optional[List[str]] = None) -> List[str]:
        tv = str(type_value).upper().strip()
        if tv == "":
            return []
        selected = selected_stations if selected_stations is not None else SmsFormat._inv_selected_stations()
        if len(selected) <= 0:
            return []
        first_station = str(selected[0]).upper().strip()
        first_caps = SmsFormat._inv_rack_caps(first_station, tv)
        out: List[str] = []
        for rack in first_caps.keys():
            keep = True
            for sta in selected[1:]:
                station_caps = SmsFormat._inv_rack_caps(str(sta).upper().strip(), tv)
                if rack not in station_caps:
                    keep = False
                    break
            if keep:
                out.append(str(rack).upper().strip())
        return out

    @staticmethod
    def _inv_available_wpns(type_value: str, rack_value: str, selected_stations: Optional[List[str]] = None) -> List[str]:
        tv = str(type_value).upper().strip()
        rv = str(rack_value).upper().strip()
        if tv == "" or rv == "":
            return []
        selected = selected_stations if selected_stations is not None else SmsFormat._inv_selected_stations()
        if len(selected) <= 0:
            return []
        first_station = str(selected[0]).upper().strip()
        first_entries = SmsFormat._inv_weapon_entries(first_station, tv, rv)
        out: List[str] = []
        for weapon_name, _qty in first_entries:
            wpn = str(weapon_name).upper().strip()
            if wpn == "":
                continue
            keep = True
            for sta in selected[1:]:
                station_entries = SmsFormat._inv_weapon_entries(str(sta).upper().strip(), tv, rv)
                station_names = {str(name).upper().strip() for name, _ in station_entries}
                if wpn not in station_names:
                    keep = False
                    break
            if keep:
                out.append(wpn)
        return out

    @staticmethod
    def _inv_quantity_for_selection(
        type_value: str,
        rack_value: str,
        wpn_value: str,
        selected_stations: Optional[List[str]] = None,
    ) -> int:
        tv = str(type_value).upper().strip()
        rv = str(rack_value).upper().strip()
        wv = str(wpn_value).upper().strip()
        if tv == "" or rv == "" or wv == "":
            return 0
        selected = selected_stations if selected_stations is not None else SmsFormat._inv_selected_stations()
        if len(selected) <= 0:
            return 0
        qty_values: List[int] = []
        for sta in selected:
            entries = SmsFormat._inv_weapon_entries(str(sta).upper().strip(), tv, rv)
            found_qty: Optional[int] = None
            for name, qty in entries:
                if str(name).upper().strip() == wv:
                    try:
                        found_qty = int(qty)
                    except Exception:
                        found_qty = 0
                    break
            if found_qty is None:
                return 0
            qty_values.append(max(0, int(found_qty)))
        if len(qty_values) <= 0:
            return 0
        # Quantity is per station. A mirrored pair should still show the amount
        # one station can carry, not the combined count across both stations.
        return int(min(qty_values))

    @staticmethod
    def _inv_option_pages(options: List[str], page_size: int = 12) -> List[List[str]]:
        if page_size <= 0:
            page_size = 12
        if len(options) <= 0:
            return [[]]
        pages: List[List[str]] = []
        for i in range(0, len(options), page_size):
            pages.append(options[i:i + page_size])
        return pages

    def _sync_inv_load_selection_state(self) -> Tuple[List[str], List[str], List[str], List[str], List[str], int, int]:
        selected = self._inv_selected_stations()
        type_options = self._inv_available_types(selected)
        type_value = self._inv_type_value()
        if type_value not in type_options:
            type_value = ""
            self._set_cntl_inv_load_type_value("")
            self._set_inv_rack_value("")
            self._set_inv_wpn_value("")
            self._set_inv_fuze_value("")
            self._set_inv_fuze_mode_value("")
            self._set_cntl_inv_load_fuze_mode_open(False)
            self._set_inv_qty_value(0)
            self._set_inv_qty_max(0)

        rack_options = self._inv_available_racks(type_value, selected)
        rack_value = self._inv_rack_value()
        if rack_value not in rack_options:
            rack_value = ""
            self._set_inv_rack_value("")
            self._set_inv_wpn_value("")
            self._set_inv_fuze_value("")
            self._set_inv_fuze_mode_value("")
            self._set_cntl_inv_load_fuze_mode_open(False)
            self._set_inv_qty_value(0)
            self._set_inv_qty_max(0)

        wpn_options = self._inv_available_wpns(type_value, rack_value, selected)
        wpn_value = self._inv_wpn_value()
        if wpn_value not in wpn_options:
            wpn_value = ""
            self._set_inv_wpn_value("")
            self._set_inv_fuze_value("")
            self._set_inv_fuze_mode_value("")
            self._set_cntl_inv_load_fuze_mode_open(False)
            self._set_inv_qty_value(0)
            self._set_inv_qty_max(0)

        fuze_options = self._inv_available_fuzes(wpn_value) if self._inv_is_gbu_wpn(wpn_value) else []
        fuze_value = self._inv_fuze_value()
        if fuze_value not in fuze_options:
            fuze_value = ""
            self._set_inv_fuze_value("")
            self._set_inv_fuze_mode_value("")
            self._set_cntl_inv_load_fuze_mode_open(False)

        fuze_mode_options = self._inv_available_fuze_modes(wpn_value, fuze_value) if fuze_value != "" else []
        fuze_mode_value = self._inv_fuze_mode_value()
        if fuze_mode_value not in fuze_mode_options:
            self._set_inv_fuze_mode_value("")
        if len(fuze_mode_options) <= 0:
            self._set_cntl_inv_load_fuze_mode_open(False)

        qty_max = self._inv_quantity_for_selection(type_value, rack_value, wpn_value, selected)
        qty_value = self._inv_qty_value()
        if qty_max <= 0:
            qty_value = 0
        elif qty_value <= 0:
            qty_value = qty_max
        qty_value = max(0, min(qty_max, qty_value))
        self._set_inv_qty_max(qty_max)
        self._set_inv_qty_value(qty_value)
        return type_options, rack_options, wpn_options, fuze_options, fuze_mode_options, qty_max, qty_value

    @staticmethod
    def _inv_load_option_cells() -> List[str]:
        return [
            "A4", "B4", "C4",
            "A5", "B5", "C5",
            "A6", "B6", "C6",
            "A7", "B7", "C7",
        ]

    @staticmethod
    def _inv_load_edge_cell_for_osb(token: str) -> str:
        # Edge popup cells overlap side OSB hit zones, so route those OSBs back
        # to the same logical cells used by direct grid clicks.
        mapping = {
            "L3": "A4",
            "L4": "A5",
            "L5": "A6",
            "L6": "A7",
            "L7": "A8",
            "R3": "C4",
            "R4": "C5",
            "R5": "C6",
            "R6": "C7",
            "R7": "A8",
        }
        return mapping.get(str(token).upper().strip(), "")

    @staticmethod
    def _inv_station_for_edge_osb(token: str) -> str:
        mapping = {
            "L5": "STA3",
            "L6": "STA2",
            "L7": "STA1",
        }
        return mapping.get(str(token).upper().strip(), "")

    def _inv_load_options_for_selection(
        self,
        current_sel: str,
        type_opts: List[str],
        rack_opts: List[str],
        wpn_opts: List[str],
        fuze_opts: List[str],
        fuze_mode_opts: List[str],
    ) -> List[str]:
        if current_sel == "TYPE":
            return list(type_opts)
        if current_sel == "RACK":
            return list(rack_opts)
        if current_sel == "WPN":
            return list(wpn_opts)
        if current_sel == "FUZE":
            return list(fuze_mode_opts if self._cntl_inv_load_fuze_mode_open() else fuze_opts)
        return []

    def _inv_apply_load_option_choice(self, current_sel: str, chosen: str) -> None:
        chosen = str(chosen).upper().strip()
        if current_sel == "TYPE":
            self._set_cntl_inv_load_type_value(chosen)
            self._set_inv_rack_value("")
            self._set_inv_wpn_value("")
            self._set_inv_fuze_value("")
            self._set_inv_fuze_mode_value("")
            self._set_cntl_inv_load_fuze_mode_open(False)
            self._set_inv_qty_value(0)
            self._set_inv_qty_max(0)
            # Auto-advance to RACK and keep options open.
            self._set_cntl_inv_load_selected_field("RACK")
            self._set_cntl_inv_load_type_menu_open(True)
            self._set_cntl_inv_load_type_page(0)
        elif current_sel == "RACK":
            self._set_inv_rack_value(chosen)
            self._set_inv_wpn_value("")
            self._set_inv_fuze_value("")
            self._set_inv_fuze_mode_value("")
            self._set_cntl_inv_load_fuze_mode_open(False)
            self._set_inv_qty_value(0)
            self._set_inv_qty_max(0)
            # Auto-advance to WPN and keep options open.
            self._set_cntl_inv_load_selected_field("WPN")
            self._set_cntl_inv_load_type_menu_open(True)
            self._set_cntl_inv_load_type_page(0)
        elif current_sel == "WPN":
            self._set_inv_wpn_value(chosen)
            self._set_inv_fuze_value("")
            self._set_inv_fuze_mode_value("")
            self._set_cntl_inv_load_fuze_mode_open(False)
            # Default QNTY to max for the chosen weapon.
            _t, _r, _w, _f, _fm, qmax_now, _q = self._sync_inv_load_selection_state()
            if qmax_now > 0:
                self._set_inv_qty_value(qmax_now)
            self._inv_apply_selected_store_request()
            if self._inv_is_gbu_wpn(chosen):
                self._set_cntl_inv_load_selected_field("FUZE")
                self._set_cntl_inv_load_type_menu_open(True)
                self._set_cntl_inv_load_type_page(0)
                self._set_cntl_inv_load_fuze_mode_open(False)
            else:
                self._set_cntl_inv_load_type_menu_open(False)
        elif current_sel == "FUZE":
            if self._cntl_inv_load_fuze_mode_open():
                self._set_inv_fuze_mode_value(chosen)
                self._inv_apply_selected_store_request()
                self._set_cntl_inv_load_fuze_mode_open(False)
                self._set_cntl_inv_load_type_menu_open(False)
            else:
                self._set_inv_fuze_value(chosen)
                self._set_inv_fuze_mode_value("")
                next_modes = self._inv_available_fuze_modes(self._inv_wpn_value(), chosen)
                if len(next_modes) > 0:
                    self._set_cntl_inv_load_fuze_mode_open(True)
                    self._set_cntl_inv_load_type_menu_open(True)
                    self._set_cntl_inv_load_type_page(0)
                else:
                    self._inv_apply_selected_store_request()
                    self._set_cntl_inv_load_fuze_mode_open(False)
                    self._set_cntl_inv_load_type_menu_open(False)

    def _inv_select_load_option_cell(
        self,
        cell: str,
        current_sel: str,
        type_opts: List[str],
        rack_opts: List[str],
        wpn_opts: List[str],
        fuze_opts: List[str],
        fuze_mode_opts: List[str],
    ) -> bool:
        opts = self._inv_load_options_for_selection(current_sel, type_opts, rack_opts, wpn_opts, fuze_opts, fuze_mode_opts)
        pages = self._inv_option_pages(opts, page_size=12)
        cell = str(cell).upper().strip()
        if cell == "A8" and len(pages) > 1:
            page = self._cntl_inv_load_type_page()
            self._set_cntl_inv_load_type_page((page + 1) % len(pages))
            return True
        page = self._cntl_inv_load_type_page()
        if page >= len(pages):
            page = max(0, len(pages) - 1)
            self._set_cntl_inv_load_type_page(page)
        active = pages[page] if len(pages) > 0 else []
        opt_cells = self._inv_load_option_cells()
        if cell not in opt_cells:
            return False
        idx = opt_cells.index(cell)
        if idx < len(active):
            self._inv_apply_load_option_choice(current_sel, str(active[idx]).upper().strip())
        return True

    @staticmethod
    def _inv_qty_key_for_cell(cell: str) -> str:
        key_cells: Dict[str, str] = {
            "A4": "1", "B4": "2", "C4": "3",
            "A5": "4", "B5": "5", "C5": "6",
            "A6": "7", "B6": "8", "C6": "9",
            "B7": "0", "C7": "BACK",
            "A7": "INC", "A8": "DEC",
        }
        return key_cells.get(str(cell).upper().strip(), "")

    def _inv_apply_qty_key_cell(self, cell: str, qty: int, qmax: int) -> bool:
        token = self._inv_qty_key_for_cell(cell)
        if token == "":
            return False
        cell = str(cell).upper().strip()
        self._trigger_local_flash(f"QTY_KEYPAD_{cell}")
        if token == "INC":
            if qmax > 0:
                new_qty = min(qmax, max(1, qty + 1))
                self._set_inv_qty_value(new_qty)
                SmsFormat._ui_set("cntl_inv_load_qty_input", str(max(1, min(9, new_qty))))
                self._inv_apply_selected_store_request()
            return True
        if token == "DEC":
            if qmax > 0:
                new_qty = max(1, min(qmax, qty - 1))
                self._set_inv_qty_value(new_qty)
                SmsFormat._ui_set("cntl_inv_load_qty_input", str(max(1, min(9, new_qty))))
                self._inv_apply_selected_store_request()
            return True
        input_txt = str(SmsFormat._ui_get("cntl_inv_load_qty_input", ""))
        if token == "BACK":
            input_txt = input_txt[:-1]
        else:
            input_txt = str(token)[:1]
        SmsFormat._ui_set("cntl_inv_load_qty_input", input_txt)
        try:
            typed = int(input_txt) if input_txt != "" else qty
        except Exception:
            typed = qty
        if qmax > 0:
            typed = max(1, min(qmax, typed))
        self._set_inv_qty_value(typed)
        self._inv_apply_selected_store_request()
        return True

    @staticmethod
    def _inv_station_order() -> List[str]:
        return ["STA1", "STA2", "STA3", "STA4", "STA5", "STA6", "STA7", "STA8", "STA9", "STA10", "STA11"]

    @staticmethod
    def _inv_opposite_station(station: str) -> Optional[str]:
        mapping = {
            "STA1": "STA11",
            "STA11": "STA1",
            "STA2": "STA10",
            "STA10": "STA2",
            "STA3": "STA9",
            "STA9": "STA3",
            "STA4": "STA8",
            "STA8": "STA4",
            "STA5": "STA7",
            "STA7": "STA5",
        }
        return mapping.get(str(station).upper().strip())

    @staticmethod
    def _inv_selected_stations() -> List[str]:
        raw = SmsFormat._ui_get("cntl_inv_selected_stations", [])
        out: List[str] = []
        if isinstance(raw, (list, tuple)):
            for item in raw:
                token = str(item).upper().strip()
                if token.startswith("STA"):
                    if token not in out:
                        out.append(token)
        order = SmsFormat._inv_station_order()
        out.sort(key=lambda s: order.index(s) if s in order else 999)
        return out[:2]

    @staticmethod
    def _set_inv_selected_stations(stations: Iterable[str]) -> None:
        order = SmsFormat._inv_station_order()
        values: List[str] = []
        for sta in stations:
            token = str(sta).upper().strip()
            if token.startswith("STA") and token in order and token not in values:
                values.append(token)
        values.sort(key=lambda s: order.index(s) if s in order else 999)
        SmsFormat._ui_set("cntl_inv_selected_stations", values[:2])

    @staticmethod
    def _inv_selected_has_loaded_store() -> bool:
        selected = SmsFormat._inv_selected_stations()
        if len(selected) <= 0:
            return False
        store_loads = SmsFormat._active_inv_store_loads()
        for sta in selected:
            entry = store_loads.get(sta, {})
            if not isinstance(entry, dict):
                continue
            weapon = str(entry.get("weapon", "")).strip().upper()
            icon = str(entry.get("icon", "")).strip()
            if (weapon != "" and weapon != "NONE") or icon != "":
                return True
        return False

    @staticmethod
    def _inv_clear_selected_stores() -> None:
        selected = SmsFormat._inv_selected_stations()
        if len(selected) <= 0:
            return
        if bool(SMS_STATE.get("cntl_inv_actual_request_mode", 0)):
            SMS_STATE["cntl_inv_clear_request"] = list(selected)
            return
        store_loads_raw = SmsFormat._active_inv_store_loads()
        for sta in selected:
            entry = store_loads_raw.get(sta, {})
            if not isinstance(entry, dict):
                entry = {}
                store_loads_raw[sta] = entry
            entry["weapon"] = "NONE"
            entry["icon"] = ""
            entry["type"] = ""
            entry["qty"] = 0
        # SMS INV changes only the aircraft's believed inventory. PMD STORES
        # DEBUG owns the actual aircraft loadout.
        SmsFormat._mark_active_inv_store_loads_initialized()
        SMS_STATE["cntl_inv_clear_request"] = []

    @staticmethod
    def _inv_toggle_station_selection(station: str) -> None:
        sta = str(station).upper().strip()
        if sta == "" or not sta.startswith("STA"):
            return
        selected = SmsFormat._inv_selected_stations()
        if sta in selected:
            selected = [s for s in selected if s != sta]
            SmsFormat._set_inv_selected_stations(selected)
            return
        if len(selected) <= 0:
            SmsFormat._set_inv_selected_stations([sta])
            return
        if len(selected) == 1:
            first = selected[0]
            if SmsFormat._inv_opposite_station(first) == sta:
                SmsFormat._set_inv_selected_stations([first, sta])
            else:
                SmsFormat._set_inv_selected_stations([sta])
            return
        # Two selected: any new non-selected station becomes the sole selection.
        SmsFormat._set_inv_selected_stations([sta])

    @staticmethod
    def _cntl_live_train_idx() -> int:
        return SmsFormat._sms_live_train_idx()

    @staticmethod
    def _set_cntl_live_train_idx(idx: int) -> None:
        SmsFormat._set_sms_live_train_idx(idx)

    @staticmethod
    def _excm_arm_confirm_pending() -> bool:
        try:
            return bool(int(SmsFormat._ui_get("excm_arm_confirm_pending", 0)))
        except Exception:
            return bool(SmsFormat._ui_get("excm_arm_confirm_pending", False))

    @staticmethod
    def _set_excm_arm_confirm_pending(pending: bool) -> None:
        SmsFormat._ui_set("excm_arm_confirm_pending", 1 if pending else 0)

    @staticmethod
    def _excm_armed() -> bool:
        try:
            return bool(int(SMS_STATE.get("excm_armed", 0)))
        except Exception:
            return bool(SMS_STATE.get("excm_armed", False))

    @staticmethod
    def _set_excm_armed(armed: bool) -> None:
        SMS_STATE["excm_armed"] = 1 if bool(armed) else 0

    @staticmethod
    def _excm_confirm_popup_rect(rect: pygame.Rect) -> pygame.Rect:
        width = max(1, int(round(3.0 * DPI)))
        height = max(1, int(round(1.6 * DPI)))
        return pygame.Rect(rect.centerx - (width // 2), rect.centery - (height // 2), width, height)

    @staticmethod
    def _popup_grid_rect(rect: pygame.Rect) -> pygame.Rect:
        grid_w = 5 * GRID_CELL_W
        grid_h = 8 * GRID_CELL_H
        grid_x = _anchored_5col_grid_x(rect, grid_w)
        return pygame.Rect(grid_x, rect.y, grid_w, grid_h)

    def _set_popup_anchor_portal_index(self, portal_index: Optional[int]) -> None:
        idx: Optional[int] = None
        try:
            if portal_index is not None:
                idx = int(portal_index)
        except Exception:
            idx = None
        if idx is None:
            idx = _active_render_portal_index()
        if idx is None:
            try:
                idx = int(SMS_STATE.get("_popup_anchor_portal_idx", 0))
            except Exception:
                idx = 0
        SMS_STATE["_popup_anchor_portal_idx"] = max(0, min(3, int(idx)))
        try:
            current_scope = str(SMS_STATE.get("_popup_anchor_scope_key", ""))
        except Exception:
            current_scope = ""
        if current_scope.startswith("portal:") or current_scope == "":
            SMS_STATE["_popup_anchor_scope_key"] = f"portal:{SMS_STATE['_popup_anchor_portal_idx']}"
        scoped = self._scope_state()
        for key in self._ui_scope_keys():
            if key in scoped:
                SMS_STATE[key] = scoped.get(key)

    @staticmethod
    def _inv_cell_rect(grid: pygame.Rect, name: str) -> pygame.Rect:
        col = ord(name[0].upper()) - ord("A")
        row = int(name[1:]) - 1
        return pygame.Rect(grid.x + col * GRID_CELL_W, grid.y + row * GRID_CELL_H, GRID_CELL_W, GRID_CELL_H)

    @staticmethod
    def _inv_station_button_rects(grid: pygame.Rect) -> List[Tuple[str, pygame.Rect, str]]:
        entries: List[Tuple[str, pygame.Rect, str]] = [
            ("STA5", SmsFormat._inv_cell_rect(grid, "B4"), "STA5"),
            ("STA7", SmsFormat._inv_cell_rect(grid, "C4"), "STA7"),
            ("STA4", SmsFormat._inv_cell_rect(grid, "B5"), "STA4"),
            ("STA8", SmsFormat._inv_cell_rect(grid, "C5"), "STA8"),
            ("STA3", SmsFormat._inv_cell_rect(grid, "A6"), "STA3"),
            ("STA9", SmsFormat._inv_cell_rect(grid, "D6"), "STA9"),
            ("STA2", SmsFormat._inv_cell_rect(grid, "A7"), "STA2"),
            ("STA10", SmsFormat._inv_cell_rect(grid, "D7"), "STA10"),
            ("STA1", SmsFormat._inv_cell_rect(grid, "A8"), "STA1"),
            ("STA11", SmsFormat._inv_cell_rect(grid, "D8"), "STA11"),
            ("STA6", SmsFormat._inv_cell_rect(grid, "B8").union(SmsFormat._inv_cell_rect(grid, "C8")), "STA6"),
        ]
        return entries

    @staticmethod
    def _inv_prog_store_signature() -> Tuple[str, ...]:
        store_loads = SmsFormat._active_inv_store_loads()
        station_order = ["STA1", "STA2", "STA3", "STA4", "STA5", "STA7", "STA8", "STA9", "STA10", "STA11"]
        loaded: List[str] = []
        for sta in station_order:
            entry = store_loads.get(sta, {})
            if not isinstance(entry, dict):
                continue
            weapon = str(entry.get("weapon", "")).strip()
            if weapon == "" or weapon.upper() == "NONE":
                continue
            loaded.append(sta)
        return tuple(loaded)

    def _inv_prog_bottom_overlay_surface(self) -> Optional[pygame.Surface]:
        loaded_sig = self._inv_prog_store_signature()
        if len(loaded_sig) <= 0:
            return None
        lt_state = str(SMS_STATE.get("lt_state", "CLOSE")).upper()
        rt_state = str(SMS_STATE.get("rt_state", "CLOSE")).upper()
        cache_key = (loaded_sig, lt_state, rt_state)
        if cache_key in SmsFormat._inv_prog_bottom_overlay_cache:
            return SmsFormat._inv_prog_bottom_overlay_cache[cache_key]

        base = self._get_layer_image("SMS AIRCRAFT.png", tinted=True)
        if not isinstance(base, pygame.Surface):
            return None
        iw, ih = base.get_size()
        if iw <= 0 or ih <= 0:
            return None

        sample_rect = pygame.Rect(0, 0, max(1, 5 * GRID_CELL_W), max(1, 8 * GRID_CELL_H))
        scale = sample_rect.width / float(iw)
        draw_w = max(1, int(iw * scale))
        draw_h = max(1, int(ih * scale))
        draw_top = sample_rect.top + 2
        sample_image_rect = pygame.Rect(0, 0, draw_w, draw_h)
        sample_image_rect.midtop = (sample_rect.centerx, draw_top)

        tmp = pygame.Surface((sample_rect.width, sample_rect.height), pygame.SRCALPHA)
        tmp.fill((0, 0, 0, 0))
        prev_cntl = SmsFormat._ui_get("cntl_submenu_open", 0)
        prev_inv = SmsFormat._ui_get("cntl_inv_prog_open", 0)
        prev_confirm = SmsFormat._ui_get("excm_arm_confirm_pending", 0)
        try:
            SmsFormat._ui_set("cntl_submenu_open", 0)
            SmsFormat._ui_set("cntl_inv_prog_open", 0)
            SmsFormat._ui_set("excm_arm_confirm_pending", 0)
            ctx = FormatContext(0, lambda *_args: None, lambda *_args: None, lambda *_args: None)
            self.render(tmp, sample_rect, True, ctx)
        finally:
            SmsFormat._ui_set("cntl_submenu_open", prev_cntl)
            SmsFormat._ui_set("cntl_inv_prog_open", prev_inv)
            SmsFormat._ui_set("excm_arm_confirm_pending", prev_confirm)

        # Safely capture the aircraft draw region even when it extends outside
        # the sample portal bounds.
        src = pygame.Surface((sample_image_rect.width, sample_image_rect.height), pygame.SRCALPHA)
        src.fill((0, 0, 0, 0))
        src.blit(tmp, (-sample_image_rect.x, -sample_image_rect.y))
        out = pygame.Surface(src.get_size(), pygame.SRCALPHA)
        cutoff_y = int(round(src.get_height() * 0.52))
        for y in range(max(0, cutoff_y), src.get_height()):
            for x in range(src.get_width()):
                r, g, b, a = src.get_at((x, y))
                if a <= 0:
                    continue
                if g >= 120 and g > (r + 35) and g > (b + 35):
                    out.set_at((x, y), (r, g, b, a))

        if out.get_bounding_rect().width <= 0 or out.get_bounding_rect().height <= 0:
            SmsFormat._inv_prog_bottom_overlay_cache[cache_key] = None
            return None
        if len(SmsFormat._inv_prog_bottom_overlay_cache) > 24:
            SmsFormat._inv_prog_bottom_overlay_cache.clear()
        SmsFormat._inv_prog_bottom_overlay_cache[cache_key] = out
        return out

    @staticmethod
    def _store_fb_quantity_offsets(qty_count: int, draw_w: int, draw_h: int) -> List[Tuple[int, int]]:
        count = max(1, min(4, int(qty_count)))
        gap = max(1, int(round(min(draw_w, draw_h) * 0.20)))
        col = int(draw_w + gap)
        row = int(draw_h + gap)
        if count <= 1:
            return [(0, 0)]
        if count == 2:
            return [(-(col // 2), 0), (col - (col // 2), 0)]
        if count == 3:
            return [(0, -(row // 2)), (-(col // 2), row - (row // 2)), (col - (col // 2), row - (row // 2))]
        return [
            (-(col // 2), -(row // 2)),
            (col - (col // 2), -(row // 2)),
            (-(col // 2), row - (row // 2)),
            (col - (col // 2), row - (row // 2)),
        ]

    def _draw_inv_prog_all_station_numbers(
        self,
        surface: pygame.Surface,
        image_rect: pygame.Rect,
        source_overlay: Optional[pygame.Surface] = None,
        selected_stations: Optional[Set[str]] = None,
        source_size: Optional[Tuple[int, int]] = None,
    ) -> None:
        if image_rect.width <= 0 or image_rect.height <= 0:
            return
        green = (0, 255, 0)
        white = (255, 255, 255)
        # Keep original spacing based on full station order, but draw only
        # outer inline labels on this row.
        station_order_all = ["1", "2", "3", "4", "5", "7", "8", "9", "10", "11"]
        inline_labels = {"1", "2", "3", "9", "10", "11"}
        selected = selected_stations if isinstance(selected_stations, set) else set()
        src_w = image_rect.width
        src_h = image_rect.height
        if isinstance(source_size, tuple) and len(source_size) == 2:
            try:
                src_w = int(source_size[0])
                src_h = int(source_size[1])
            except Exception:
                src_w = image_rect.width
                src_h = image_rect.height
        elif isinstance(source_overlay, pygame.Surface):
            ow, oh = source_overlay.get_size()
            if ow > 0 and oh > 0:
                src_w = int(ow)
                src_h = int(oh)
        left_cx = int(round(src_w * 0.10))
        right_cx = int(round(src_w * 0.90))
        if right_cx <= left_cx:
            right_cx = left_cx + 1
        y = int(round(src_h * 0.74))
        scale_x = float(image_rect.width) / float(max(1, src_w))
        scale_y = float(image_rect.height) / float(max(1, src_h))
        font = get_font(11)

        def _is_green(px: Tuple[int, int, int, int]) -> bool:
            r, g, b, a = int(px[0]), int(px[1]), int(px[2]), int(px[3])
            return a > 0 and g >= 45 and g > (r + 25) and g > (b + 25)

        def _is_station_mark(px: Tuple[int, int, int, int]) -> bool:
            r, g, b, a = int(px[0]), int(px[1]), int(px[2]), int(px[3])
            if a <= 0:
                return False
            if _is_green(px):
                return True
            return r >= 180 and g >= 180 and b >= 180

        def _station_center(src_cx: int, src_cy: int) -> Tuple[int, int]:
            sx = image_rect.left + int(round(src_cx * scale_x))
            sy = image_rect.top + int(round(src_cy * scale_y))
            return sx, sy

        def _clear_station_mark_area(cx: int, cy: int, rx: int, ry: int) -> None:
            x0 = max(image_rect.left, cx - rx)
            x1 = min(image_rect.right - 1, cx + rx)
            y0 = max(image_rect.top, cy - ry)
            y1 = min(image_rect.bottom - 1, cy + ry)
            for py in range(y0, y1 + 1):
                for px in range(x0, x1 + 1):
                    p = surface.get_at((px, py))
                    if _is_station_mark(p):
                        surface.set_at((px, py), (0, 0, 0, 0))

        # Preserve original horizontal spacing by indexing across all stations.
        station_pos_src: Dict[str, Tuple[int, int]] = {}
        for idx, label in enumerate(station_order_all):
            t = idx / float(max(1, len(station_order_all) - 1))
            cx_src = int(round(left_cx + ((right_cx - left_cx) * t)))
            cy_src = int(y)
            station_pos_src[label] = (cx_src, cy_src)

        # First scrub copied labels/icons from the loaded-store overlay. The
        # INV PROG bottom aircraft owns these marks so scale and selection color
        # remain stable whether stations are loaded or empty.
        mid_y_shift_outer = int(round(src_h * 0.045))
        mid_y_shift_inner = int(round(src_h * 0.065))
        mid_positions: Dict[str, Tuple[int, int]] = {}
        label_rx = max(12, int(round(18 * scale_x)))
        label_ry = max(8, int(round(12 * scale_y)))
        for label in station_order_all:
            cx_src, cy_src = station_pos_src[label]
            cx, cy = _station_center(cx_src, cy_src)
            _clear_station_mark_area(cx, cy, label_rx, label_ry)
            if label in {"4", "5", "7", "8"}:
                cy_mid_src = cy_src + (mid_y_shift_outer if label in {"4", "8"} else mid_y_shift_inner)
                mid_cx, mid_cy = _station_center(cx_src, cy_mid_src)
                mid_positions[label] = (mid_cx, mid_cy)
                _clear_station_mark_area(mid_cx, mid_cy, label_rx, label_ry)

        if "4" in mid_positions and "5" in mid_positions:
            gun_cx = int(round((mid_positions["4"][0] + mid_positions["5"][0]) / 2.0))
            gun_cy = int(round(min(mid_positions["4"][1], mid_positions["5"][1]) - (0.040 * image_rect.height)))
            gun_rx = max(30, int(round(44 * scale_x)))
            gun_ry = max(22, int(round(36 * scale_y)))
            _clear_station_mark_area(gun_cx, gun_cy, gun_rx, gun_ry)
            # Loaded-store captures can place the old GUN FB slightly lower than
            # the canonical bottom-aircraft position.
            _clear_station_mark_area(gun_cx, gun_cy + int(round(0.035 * image_rect.height)), gun_rx, gun_ry)

        # Draw inline outer station labels (1/2/3/9/10/11).
        for label in station_order_all:
            if label not in inline_labels:
                continue
            station_name = f"STA{label}"
            cx_src, cy_src = station_pos_src[label]
            cx, cy = _station_center(cx_src, cy_src)
            num_color = white if station_name in selected else green
            base = font.render(label, True, num_color)
            if abs(scale_x - 1.0) > 0.05 or abs(scale_y - 1.0) > 0.05:
                tw = max(1, int(round(base.get_width() * scale_x)))
                th = max(1, int(round(base.get_height() * scale_y)))
                txt = pygame.transform.smoothscale(base, (tw, th))
            else:
                txt = base
            tr = txt.get_rect(center=(cx, cy))
            surface.blit(txt, tr)

        # Persistently draw mid-body station labels (4/5/7/8), independent of
        # loaded stores. Place them at the lower row where the copied labels
        # appear, then erase that copied set and render one authoritative set.
        for label in ("4", "5", "7", "8"):
            cx_src, cy_src_base = station_pos_src.get(label, (left_cx, y))
            cy_src = cy_src_base + (mid_y_shift_outer if label in {"4", "8"} else mid_y_shift_inner)
            cx, cy = _station_center(cx_src, cy_src)
            mid_positions[label] = (cx, cy)
            station_name = f"STA{label}"
            num_color = white if station_name in selected else green
            base = font.render(label, True, num_color)
            if abs(scale_x - 1.0) > 0.05 or abs(scale_y - 1.0) > 0.05:
                tw = max(1, int(round(base.get_width() * scale_x)))
                th = max(1, int(round(base.get_height() * scale_y)))
                txt = pygame.transform.smoothscale(base, (tw, th))
            else:
                txt = base
            tr = txt.get_rect(center=(cx, cy))
            surface.blit(txt, tr)

        store_loads = SmsFormat._active_inv_store_loads()
        icon_tint = self._active_inv_store_icon_tint_color()
        fb_img = self._get_store_icon_image("STORE FB.png", green_tint=True, tint_color=icon_tint)
        if fb_img is not None:
            fb_w, fb_h = fb_img.get_size()
            if fb_w > 0 and fb_h > 0:
                for label in station_order_all:
                    station_name = f"STA{label}"
                    entry = store_loads.get(station_name, {})
                    if not isinstance(entry, dict):
                        continue
                    weapon = str(entry.get("weapon", "")).strip()
                    if weapon == "" or weapon.upper() == "NONE":
                        continue
                    try:
                        qty_count = max(1, int(entry.get("qty", 1)))
                    except Exception:
                        qty_count = 1
                    if label in mid_positions:
                        fb_cx, label_cy = mid_positions[label]
                    else:
                        cx_src, cy_src = station_pos_src.get(label, (left_cx, y))
                        fb_cx, label_cy = _station_center(cx_src, cy_src)
                    draw_fb_h = max(3, int(round(0.020 * image_rect.height)))
                    fb_scale = draw_fb_h / float(max(1, fb_h))
                    draw_fb_w = max(1, int(round(fb_w * fb_scale)))
                    scaled_fb = pygame.transform.smoothscale(fb_img, (draw_fb_w, draw_fb_h))
                    base_center_y = int(round(label_cy + (0.034 * image_rect.height) + (draw_fb_h / 2.0)))
                    offsets = self._store_fb_quantity_offsets(qty_count, draw_fb_w, draw_fb_h)
                    xs = [fb_cx + dx for dx, _dy in offsets]
                    ys = [base_center_y + dy for _dx, dy in offsets]
                    clear_cx = int(round((min(xs) + max(xs)) / 2.0))
                    clear_cy = int(round((min(ys) + max(ys)) / 2.0))
                    clear_rx = max(8, int(round(((max(xs) - min(xs)) + draw_fb_w) / 2.0)) + 3)
                    clear_ry = max(8, int(round(((max(ys) - min(ys)) + draw_fb_h) / 2.0)) + 3)
                    _clear_station_mark_area(clear_cx, clear_cy, clear_rx, clear_ry)
                    for dx, dy in offsets:
                        fb_x = int(round(fb_cx + dx - (draw_fb_w / 2.0)))
                        fb_y = int(round(base_center_y + dy - (draw_fb_h / 2.0)))
                        surface.blit(scaled_fb, (fb_x, fb_y))

        # Persistently draw GUN FB only (STA6) so it does not disappear with
        # empty stations.
        if "4" in mid_positions and "5" in mid_positions:
            gun_cx = int(round((mid_positions["4"][0] + mid_positions["5"][0]) / 2.0))
            gun_cy = int(round(min(mid_positions["4"][1], mid_positions["5"][1]) - (0.040 * image_rect.height)))
            gun_img = self._get_store_icon_image("GUN FB.png", green_tint=True, tint_color=icon_tint)
            if gun_img is not None:
                gw, gh = gun_img.get_size()
                if gw > 0 and gh > 0:
                    target_h = max(3, int(round(0.026 * image_rect.height)))
                    scl = target_h / float(max(1, gh))
                    draw_w = max(1, int(round(gw * scl)))
                    draw_h = max(1, int(round(gh * scl)))
                    scaled = pygame.transform.smoothscale(gun_img, (draw_w, draw_h))
                    gr = scaled.get_rect(center=(gun_cx, gun_cy))
                    surface.blit(scaled, gr)

    def _draw_cntl_inv_prog_submenu(self, surface: pygame.Surface, rect: pygame.Rect, is_primary: bool) -> None:
        _ = is_primary
        cyan = (0, 255, 255)
        green = (0, 255, 0)
        white = (255, 255, 255)
        grid = self._popup_grid_rect(rect)

        def _cell_rect(name: str) -> pygame.Rect:
            return self._inv_cell_rect(grid, name)

        def _draw_cell_text(
            box: pygame.Rect,
            text: str,
            *,
            add_empty_lines: bool = True,
            extra_blank_lines: int = 0,
            text_color: Tuple[int, int, int] = cyan,
            underline_first: bool = False,
            selected: bool = False,
        ) -> None:
            inner = box.inflate(-2, -2)
            if inner.width > 0 and inner.height > 0:
                surface.fill((0, 0, 0), inner)
            lines = str(text).split("\n")
            if add_empty_lines:
                lines += ["", ""]
            if int(extra_blank_lines) > 0:
                lines += [""] * int(extra_blank_lines)
            font = get_font(12)
            line_h = font.get_height() + 1
            total_h = max(0, len(lines) * line_h - 1)
            if len(lines) <= 0 or total_h <= 0:
                return
            y = box.centery - (total_h // 2)
            first_line_rect: Optional[pygame.Rect] = None
            for line in lines:
                if str(line) != "":
                    surf = font.render(line, True, text_color)
                    rr = surf.get_rect(centerx=box.centerx, y=y)
                    surface.blit(surf, rr)
                    if first_line_rect is None:
                        first_line_rect = rr.copy()
                y += line_h
            if underline_first and first_line_rect is not None:
                pygame.draw.line(
                    surface,
                    text_color,
                    (first_line_rect.left, first_line_rect.bottom + 1),
                    (first_line_rect.right, first_line_rect.bottom + 1),
                    1,
                )
            if selected:
                hi = box.inflate(-8, -8)
                if hi.width > 0 and hi.height > 0:
                    pygame.draw.rect(surface, white, hi, 1)

        def _draw_a8_arrow(*, right: bool) -> None:
            box = _cell_rect("A8")
            tri_w = max(10, box.width // 3)
            tri_h = max(10, box.height // 3)
            cx = box.centerx
            cy = box.centery
            if right:
                pts = [
                    (cx + tri_w // 2, cy),
                    (cx - tri_w // 2, cy - tri_h // 2),
                    (cx - tri_w // 2, cy + tri_h // 2),
                ]
            else:
                pts = [
                    (cx - tri_w // 2, cy),
                    (cx + tri_w // 2, cy - tri_h // 2),
                    (cx + tri_w // 2, cy + tri_h // 2),
                ]
            pygame.draw.polygon(surface, cyan, pts, 0)

        def _draw_load_field(box: pygame.Rect, header: str, value: str, *, selected_field: bool = False) -> None:
            inner = box.inflate(-2, -2)
            if inner.width > 0 and inner.height > 0:
                surface.fill((0, 0, 0), inner)
            font = get_font(12)
            line_h = font.get_height() + 1
            y0 = box.centery - ((line_h * 3 - 1) // 2)
            head_s = font.render(str(header), True, green)
            head_r = head_s.get_rect(centerx=box.centerx, y=y0)
            surface.blit(head_s, head_r)
            pygame.draw.line(surface, green, (head_r.left, head_r.bottom + 1), (head_r.right, head_r.bottom + 1), 1)
            value_lines = [str(line).strip() for line in str(value).split("\n") if str(line).strip() != ""]
            if len(value_lines) == 1:
                value_s = font.render(value_lines[0], True, cyan)
                value_r = value_s.get_rect(centerx=box.centerx, y=(y0 + (2 * line_h)))
                surface.blit(value_s, value_r)
            elif len(value_lines) >= 2:
                first_s = font.render(value_lines[0], True, cyan)
                second_s = font.render(value_lines[1], True, cyan)
                first_r = first_s.get_rect(centerx=box.centerx, y=(y0 + line_h))
                second_r = second_s.get_rect(centerx=box.centerx, y=(y0 + (2 * line_h)))
                surface.blit(first_s, first_r)
                surface.blit(second_s, second_r)
            if selected_field:
                hi = box.inflate(-8, -8)
                if hi.width > 0 and hi.height > 0:
                    pygame.draw.rect(surface, white, hi, 1)

        def _draw_qty_field(box: pygame.Rect, qty_value: int, *, selected_field: bool = False) -> None:
            inner = box.inflate(-2, -2)
            if inner.width > 0 and inner.height > 0:
                surface.fill((0, 0, 0), inner)
            font = get_font(12)
            line_h = font.get_height() + 1
            y0 = box.centery - ((line_h * 3 - 1) // 2)
            scratch = str(SmsFormat._ui_get("cntl_inv_load_qty_input", "")).strip()[:1]
            if selected_field:
                scratch_box = pygame.Rect(0, 0, max(8, font.size("8")[0] + 4), max(8, font.get_height() + 2))
                scratch_box.centerx = box.centerx
                scratch_box.y = y0
                pygame.draw.rect(surface, white, scratch_box, 1)
                if scratch != "":
                    scratch_s = font.render(scratch, True, white)
                    scratch_r = scratch_s.get_rect(center=scratch_box.center)
                    surface.blit(scratch_s, scratch_r)
            head_s = font.render("QNTY", True, cyan)
            head_r = head_s.get_rect(centerx=box.centerx, y=(y0 + line_h))
            surface.blit(head_s, head_r)
            val_s = font.render(str(max(0, int(qty_value))), True, cyan)
            val_r = val_s.get_rect(centerx=box.centerx, y=(y0 + (2 * line_h)))
            surface.blit(val_s, val_r)

        def _draw_qty_keypad() -> None:
            font = get_font(12)
            now_ms = int(pygame.time.get_ticks())
            key_labels: Dict[str, str] = {
                "A4": "1", "B4": "2", "C4": "3",
                "A5": "4", "B5": "5", "C5": "6",
                "A6": "7", "B6": "8", "C6": "9",
                "B7": "0", "C7": "BACK",
            }
            for cell_name, text in key_labels.items():
                render_button(
                    surface,
                    _cell_rect(cell_name),
                    ButtonState(
                        button_id=f"SMS_QTY_KEYPAD_{cell_name}",
                        button_type=ButtonType.MOMENTARY_SINGLE,
                        text=text,
                        font_size=12,
                        flash_until_ms=1 if self._local_flash_active(f"QTY_KEYPAD_{cell_name}", now_ms) else 0,
                    ),
                    get_font,
                    now_ms,
                )
            # A7 INC up-triangle
            a7 = _cell_rect("A7")
            up_pts = [(a7.centerx, a7.centery - 12), (a7.centerx - 10, a7.centery + 8), (a7.centerx + 10, a7.centery + 8)]
            if self._local_flash_active("QTY_KEYPAD_A7", now_ms):
                pygame.draw.rect(surface, white, a7.inflate(-max(4, a7.width // 3), -max(4, a7.height // 3)), 0)
                pygame.draw.polygon(surface, (0, 0, 0), up_pts, 0)
            else:
                pygame.draw.polygon(surface, cyan, up_pts, 0)
            # A8 DEC down-triangle
            a8 = _cell_rect("A8")
            dn_pts = [(a8.centerx, a8.centery + 12), (a8.centerx - 10, a8.centery - 8), (a8.centerx + 10, a8.centery - 8)]
            if self._local_flash_active("QTY_KEYPAD_A8", now_ms):
                pygame.draw.rect(surface, white, a8.inflate(-max(4, a8.width // 3), -max(4, a8.height // 3)), 0)
                pygame.draw.polygon(surface, (0, 0, 0), dn_pts, 0)
            else:
                pygame.draw.polygon(surface, cyan, dn_pts, 0)

        # Standard popup grid.
        for col in range(6):
            x = grid.x + col * GRID_CELL_W
            pygame.draw.line(surface, cyan, (x, grid.top), (x, grid.bottom), 1)
        for row in range(9):
            y = grid.y + row * GRID_CELL_H
            pygame.draw.line(surface, cyan, (grid.left, y), (grid.right, y), 1)

        # Merge A1..D3 into one drawing region.
        merged = pygame.Rect(grid.x, grid.y, 4 * GRID_CELL_W, 3 * GRID_CELL_H)
        surface.fill((0, 0, 0), merged)
        pygame.draw.rect(surface, cyan, merged, 1)

        selected = set(self._inv_selected_stations())
        aircraft = self._get_layer_image("SMS AIRCRAFT BOTTOM.png", tinted=True)
        if isinstance(aircraft, pygame.Surface):
            iw, ih = aircraft.get_size()
            if iw > 0 and ih > 0:
                draw_w = max(1, merged.width - 4)
                draw_h = max(1, int(round((float(ih) / float(iw)) * draw_w)))
                scaled = pygame.transform.smoothscale(aircraft, (draw_w, draw_h))
                # Bottom aligned half a square above the current position.
                target_bottom = grid.y + ((5 * GRID_CELL_H) // 2)
                icon_rect = scaled.get_rect(centerx=merged.centerx, bottom=target_bottom)
                surface.blit(scaled, icon_rect)
                overlay = None
                self._draw_inv_prog_all_station_numbers(
                    surface,
                    icon_rect,
                    source_overlay=overlay,
                    selected_stations=selected,
                    source_size=(iw, ih),
                )

        load_submenu = self._cntl_inv_load_open()
        if not load_submenu:
            for station, box, label in self._inv_station_button_rects(grid):
                is_selected = station in selected
                display_label = self._sms_inv_station_label(station)
                _draw_cell_text(box, display_label, add_empty_lines=False, text_color=(white if is_selected else cyan), selected=is_selected)
            # Keep B/C8 merged border visual.
            bc8 = _cell_rect("B8").union(_cell_rect("C8"))
            seam_x = _cell_rect("B8").right
            pygame.draw.line(surface, (0, 0, 0), (seam_x, bc8.top + 1), (seam_x, bc8.bottom - 1), 1)
            pygame.draw.rect(surface, cyan, bc8, 1)

            # E1 gun data.
            try:
                ammo = int(SMS_STATE.get("gun_count", 182))
            except Exception:
                ammo = 182
            _draw_cell_text(_cell_rect("E1"), f"GUN\nPG23\n{ammo}", add_empty_lines=False, text_color=cyan)

            if len(selected) > 0:
                _draw_cell_text(_cell_rect("E6"), "LOAD>", add_empty_lines=False, text_color=cyan)
            if self._inv_selected_has_loaded_store():
                _draw_cell_text(_cell_rect("E7"), "CLR", add_empty_lines=False, text_color=cyan)
        else:
            # LOAD submenu controls.
            type_opts, rack_opts, wpn_opts, fuze_opts, fuze_mode_opts, qty_max, qty_value = self._sync_inv_load_selection_state()
            load_sel = self._cntl_inv_load_selected_field()
            type_value = self._inv_type_value()
            rack_value = self._inv_rack_value()
            wpn_value = self._inv_wpn_value()
            fuze_value = self._inv_fuze_value()
            fuze_mode_value = self._inv_fuze_mode_value()
            _draw_load_field(_cell_rect("E1"), "TYPE", type_value, selected_field=(load_sel == "TYPE"))
            _draw_load_field(_cell_rect("D4"), "RACK", rack_value, selected_field=(load_sel == "RACK"))
            _draw_load_field(_cell_rect("D5"), "WPN", wpn_value, selected_field=(load_sel == "WPN"))
            _draw_qty_field(_cell_rect("D6"), qty_value if qty_value > 0 else 0, selected_field=(load_sel == "QNTY"))
            if self._inv_is_gbu_wpn(wpn_value):
                _draw_load_field(_cell_rect("E5"), "FUZE", fuze_value, selected_field=(load_sel == "FUZE"))

            if self._cntl_inv_load_type_menu_open():
                if load_sel == "QNTY":
                    _draw_qty_keypad()
                else:
                    if load_sel == "TYPE":
                        opts = list(type_opts)
                    elif load_sel == "RACK":
                        opts = list(rack_opts)
                    elif load_sel == "WPN":
                        opts = list(wpn_opts)
                    elif load_sel == "FUZE":
                        opts = list(fuze_mode_opts if self._cntl_inv_load_fuze_mode_open() else fuze_opts)
                    else:
                        opts = []
                    pages = self._inv_option_pages(opts, page_size=12)
                    page = self._cntl_inv_load_type_page()
                    if page >= len(pages):
                        page = max(0, len(pages) - 1)
                        self._set_cntl_inv_load_type_page(page)
                    active = pages[page] if len(pages) > 0 else []
                    opt_cells = [
                        "A4", "B4", "C4",
                        "A5", "B5", "C5",
                        "A6", "B6", "C6",
                        "A7", "B7", "C7",
                    ]
                    for idx, cell in enumerate(opt_cells):
                        box = _cell_rect(cell)
                        if idx < len(active):
                            option = str(active[idx]).upper().strip()
                            if (
                                (load_sel == "TYPE" and option == type_value)
                                or (load_sel == "RACK" and option == rack_value)
                                or (load_sel == "WPN" and option == wpn_value)
                                or (
                                    load_sel == "FUZE"
                                    and (
                                        (self._cntl_inv_load_fuze_mode_open() and option == fuze_mode_value)
                                        or ((not self._cntl_inv_load_fuze_mode_open()) and option == fuze_value)
                                    )
                                )
                            ):
                                _draw_cell_text(box, option, add_empty_lines=False, text_color=white, selected=True)
                            else:
                                _draw_cell_text(box, option, add_empty_lines=False, text_color=cyan)
                        else:
                            inner = box.inflate(-2, -2)
                            if inner.width > 0 and inner.height > 0:
                                surface.fill((0, 0, 0), inner)
                    if len(pages) > 1:
                        _draw_a8_arrow(right=(page < (len(pages) - 1)))

        # Explicitly restore bottom border lines for final-row cells.
        for cell in ("A8", "B8", "C8", "D8", "E8"):
            box = _cell_rect(cell)
            pygame.draw.line(surface, cyan, (box.left, box.bottom - 1), (box.right, box.bottom - 1), 1)

    def _draw_excm_confirm_popup(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        if not self._excm_arm_confirm_pending():
            return
        popup = self._excm_confirm_popup_rect(rect)
        pygame.draw.rect(surface, (0, 255, 255), popup, 0)
        pygame.draw.rect(surface, (255, 255, 255), popup, 1)
        font = get_font(20)
        lines = [font.render("CONFIRM", True, (0, 0, 0)), font.render("ARM CM", True, (0, 0, 0))]
        total_h = sum(s.get_height() for s in lines) + 2
        y = popup.centery - (total_h // 2)
        for surf in lines:
            rr = surf.get_rect(centerx=popup.centerx, y=y)
            surface.blit(surf, rr)
            y = rr.bottom + 2

    def _get_layer_image(self, filename: str, tinted: bool = False) -> Optional[pygame.Surface]:
        key = (filename, tinted)
        if key in SmsFormat._cached_layers:
            return SmsFormat._cached_layers[key]
        self._queue_layer_load(key)
        return None

    @staticmethod
    def _queue_layer_load(key: Tuple[str, bool]) -> None:
        if key in SmsFormat._cached_layers:
            return
        if key in _SMS_LAYER_LOAD_PENDING:
            return
        _SMS_LAYER_LOAD_PENDING.add(key)
        _SMS_LAYER_LOAD_QUEUE.append(key)

    @staticmethod
    def _load_layer_now(key: Tuple[str, bool]) -> Optional[pygame.Surface]:
        if key in SmsFormat._cached_layers:
            return SmsFormat._cached_layers[key]
        filename, tinted = key
        image_path = resource_path("icons", "SMS", filename)
        try:
            loaded = pygame.image.load(str(image_path)).convert_alpha()
            if tinted:
                loaded = SmsFormat._tint_to_color(loaded, _SMS_TINT_COLOR)
            SmsFormat._cached_layers[key] = loaded
        except Exception:
            SmsFormat._cached_layers[key] = None
        return SmsFormat._cached_layers[key]

    @staticmethod
    def _door_overlay_name(side: str, state: str) -> str:
        s = "LT" if side.upper() == "LT" else "RT"
        st = state.upper()
        return f"SMS {s} {st}.png"

    @staticmethod
    def _ensure_door_state_defaults() -> None:
        SMS_STATE.setdefault("lt_state", "CLOSE")
        SMS_STATE.setdefault("rt_state", "CLOSE")
        SMS_STATE.setdefault("lt_target", "CLOSE")
        SMS_STATE.setdefault("rt_target", "CLOSE")
        SMS_STATE.setdefault("lt_transition_due_ms", 0)
        SMS_STATE.setdefault("rt_transition_due_ms", 0)

    @staticmethod
    def _update_door_state(side: str, now_ms: int) -> None:
        SmsFormat._ensure_door_state_defaults()
        s = "lt" if side.upper() == "LT" else "rt"
        state_key = f"{s}_state"
        target_key = f"{s}_target"
        due_key = f"{s}_transition_due_ms"
        try:
            due = int(SMS_STATE.get(due_key, 0))
        except Exception:
            due = 0
        state = str(SMS_STATE.get(state_key, "CLOSE")).upper()
        target = str(SMS_STATE.get(target_key, "CLOSE")).upper()
        if state == "PARTIAL" and due > 0 and now_ms >= due:
            SMS_STATE[state_key] = "OPEN" if target == "OPEN" else "CLOSE"
            SMS_STATE[due_key] = 0

    @staticmethod
    def _command_doors(target_open: bool, now_ms: int) -> None:
        SmsFormat._ensure_door_state_defaults()
        target = "OPEN" if target_open else "CLOSE"
        for s in ("lt", "rt"):
            state_key = f"{s}_state"
            target_key = f"{s}_target"
            due_key = f"{s}_transition_due_ms"
            cur_state = str(SMS_STATE.get(state_key, "CLOSE")).upper()
            SMS_STATE[target_key] = target
            if cur_state != target:
                SMS_STATE[state_key] = "PARTIAL"
                SMS_STATE[due_key] = int(now_ms + 3000)

    @staticmethod
    def _tint_to_color(src: pygame.Surface, tint: Tuple[int, int, int]) -> pygame.Surface:
        # Fast tint path; avoids Python per-pixel loops that stall frame rendering.
        out = src.copy()
        tint_layer = pygame.Surface(out.get_size(), pygame.SRCALPHA)
        tint_layer.fill((int(tint[0]), int(tint[1]), int(tint[2]), 255))
        out.blit(tint_layer, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return out

    @staticmethod
    def _get_store_icon_image(
        filename: str,
        green_tint: bool = True,
        tint_color: Optional[Tuple[int, int, int]] = None,
    ) -> Optional[pygame.Surface]:
        color_key: Optional[Tuple[int, int, int]] = None
        if bool(green_tint):
            raw_color = tint_color if isinstance(tint_color, tuple) and len(tint_color) == 3 else (0, 255, 0)
            color_key = (
                max(0, min(255, int(raw_color[0]))),
                max(0, min(255, int(raw_color[1]))),
                max(0, min(255, int(raw_color[2]))),
            )
        icon_path = SmsFormat._resolve_store_icon_path(str(filename))
        if icon_path is None:
            key = (str(filename), color_key)
            SmsFormat._cached_store_icons[key] = None
            return None
        key = (str(icon_path), color_key)
        if key in SmsFormat._cached_store_icons:
            return SmsFormat._cached_store_icons[key]
        try:
            loaded = pygame.image.load(str(icon_path)).convert_alpha()
            if color_key is not None:
                loaded = SmsFormat._tint_to_color(loaded, color_key)
            SmsFormat._cached_store_icons[key] = loaded
        except Exception:
            SmsFormat._cached_store_icons[key] = None
        return SmsFormat._cached_store_icons[key]

    @staticmethod
    def _store_icon_for_entry(entry: Dict[str, Any]) -> str:
        icon_name = str(entry.get("icon", "")).strip()
        if icon_name != "" and SmsFormat._inv_store_icon_exists(icon_name):
            return icon_name
        weapon = str(entry.get("weapon", "")).strip()
        if weapon == "" or weapon.upper() == "NONE":
            return ""
        _store_id, derived_icon, _store_type = SmsFormat._inv_store_load_metadata(weapon)
        return str(derived_icon).strip()

    @staticmethod
    def _station_icon_faces_left(station: str) -> bool:
        return str(station).upper().strip() in {"STA1", "STA2", "STA3", "STA4", "STA5"}

    @staticmethod
    def _sms_store_weapon_short(value: object) -> str:
        token = SmsFormat._inv_norm_token(value)
        if token.startswith("AIM120"):
            suffix = token[6:] if len(token) > 6 else ""
            return f"A120{suffix}"
        if token.startswith("AIM9"):
            return token.replace("AIM", "A", 1)
        if token.startswith("AIM"):
            return token.replace("AIM", "A", 1)
        if token.startswith("GBU"):
            body = token[3:]
            return f"GB{body}C" if body != "" else "GBC"
        if token.startswith("AGM"):
            return token.replace("AGM", "A", 1)
        if token.startswith("CBU"):
            return token.replace("CBU", "C", 1)
        return token[:6]

    @staticmethod
    def _sms_store_rack_short(rack: object, weapon: object) -> str:
        rack_token = SmsFormat._inv_norm_token(rack)
        weapon_token = SmsFormat._inv_norm_token(weapon)
        if rack_token.startswith("BRU"):
            rack_num = rack_token[3:]
            wpn_hint = ""
            if weapon_token.startswith("GBU"):
                wpn_hint = "G" + weapon_token[3:]
            elif weapon_token.startswith("AGM"):
                wpn_hint = "A" + weapon_token[3:]
            elif weapon_token.startswith("CBU"):
                wpn_hint = "C" + weapon_token[3:]
            return f"B{rack_num}{wpn_hint}"[:7]
        if rack_token.startswith("LAU"):
            return rack_token[:7]
        return rack_token[:7]

    @staticmethod
    def _sms_inv_station_label(station: str) -> str:
        sta = str(station).upper().strip()
        store_loads = SmsFormat._active_inv_store_loads()
        entry = store_loads.get(sta, {})
        if not isinstance(entry, dict):
            return sta
        weapon = str(entry.get("weapon", "")).strip()
        if weapon == "" or weapon.upper() == "NONE":
            return sta
        rack = str(entry.get("rack", "")).strip()
        try:
            qty = max(1, int(entry.get("qty", 1)))
        except Exception:
            qty = 1
        rack_line = SmsFormat._sms_store_rack_short(rack, weapon)
        wpn_line = f"{qty}{SmsFormat._sms_store_weapon_short(weapon)}"
        lines = [sta]
        if rack_line != "":
            lines.append(rack_line)
        if wpn_line != "":
            lines.append(wpn_line)
        return "\n".join(lines)

    def render(self, surface, rect, is_primary: bool, context: FormatContext) -> None:
        self._set_popup_anchor_portal_index(getattr(context, "portal_index", None))
        prev_clip = surface.get_clip()
        surface.set_clip(rect)
        if is_primary and self._cntl_inv_prog_open():
            surface.fill((0, 0, 0), rect)
            self._draw_cntl_inv_prog_submenu(surface, rect, is_primary)
            self._draw_osb_labels(surface, rect, context)
            self._draw_excm_confirm_popup(surface, rect)
            surface.set_clip(prev_clip)
            return
        base = self._get_layer_image("SMS AIRCRAFT.png", tinted=is_primary)
        if base is None:
            draw_centered_text(surface, rect, "SMS", "00FFFF", 18 if is_primary else 14)
            surface.set_clip(prev_clip)
            return
        lt_state = str(SMS_STATE.get("lt_state", "CLOSE")).upper()
        rt_state = str(SMS_STATE.get("rt_state", "CLOSE")).upper()
        lt_overlay = self._get_layer_image(self._door_overlay_name("LT", lt_state), tinted=is_primary)
        rt_overlay = self._get_layer_image(self._door_overlay_name("RT", rt_state), tinted=is_primary)
        # In SMS, 10-wide primary windows (10x7 and 10x5) intentionally share
        # identical image size and center-box placement.
        is_10wide = bool(is_primary and rect.width >= int(10 * DPI) - 1)
        iw, ih = base.get_size()
        if iw <= 0 or ih <= 0:
            surface.set_clip(prev_clip)
            return
        if is_primary:
            if is_10wide:
                # 10x7/10x5: keep aircraft image at 5x7-size (same visual size as 5x7).
                scale = (5.0 * DPI) / iw
            else:
                # Standard primary portals: fit by current page width.
                scale = rect.width / iw
        else:
            # Subportal SMS image: 2.0in wide, top aligned.
            target_w = min(rect.width, int(2.0 * DPI))
            scale = target_w / iw
        draw_w = max(1, int(iw * scale))
        draw_h = max(1, int(ih * scale))
        scaled_base = pygame.transform.smoothscale(base, (draw_w, draw_h))
        draw_top = (rect.top + 2) if is_primary else rect.top - 11
        draw_rect = scaled_base.get_rect(midtop=(rect.centerx, draw_top))
        surface.blit(scaled_base, draw_rect.topleft)
        if lt_overlay is not None:
            scaled_lt = pygame.transform.smoothscale(lt_overlay, (draw_w, draw_h))
            surface.blit(scaled_lt, draw_rect.topleft)
        if rt_overlay is not None:
            scaled_rt = pygame.transform.smoothscale(rt_overlay, (draw_w, draw_h))
            surface.blit(scaled_rt, draw_rect.topleft)

        # Center status box that scales with the image.
        box_w = max(60, int(draw_rect.width * 0.24)) + 5
        box_h = max(66, int(max(88, int(draw_rect.height * 0.30)) * 0.75))
        info_box = pygame.Rect(0, 0, box_w, box_h)
        info_box_y = rect.top + int(3.125 * DPI) - 30 + 100
        if is_10wide:
            # Keep same vertical placement as 5x7 while centered on the aircraft image.
            info_box.center = (rect.centerx, info_box_y)
        else:
            # Keep this in the same location as tuned on a 5x7 portal:
            # center at x=2.5in, y=3.125in from portal top-left.
            info_box.center = (rect.left + int(2.5 * DPI), info_box_y)
        pygame.draw.rect(surface, (255, 255, 255), info_box, 1)

        # Loaded stores row above CHAFF/FLARE box.
        if is_primary:
            store_loads = self._active_display_store_loads()
            display_icon_tint = self._active_display_store_icon_tint_color()
            station_order = ["STA1", "STA2", "STA3", "STA4", "STA5", "STA7", "STA8", "STA9", "STA10", "STA11"]
            station_icons: Dict[str, str] = {}
            station_qty: Dict[str, int] = {}
            station_loaded: Set[str] = set()
            for sta in station_order:
                entry = store_loads.get(sta, {})
                if not isinstance(entry, dict):
                    continue
                weapon = str(entry.get("weapon", "")).strip()
                icon_name = self._store_icon_for_entry(entry)
                if weapon == "" or weapon.upper() == "NONE":
                    continue
                station_loaded.add(sta)
                station_icons[sta] = icon_name
                try:
                    station_qty[sta] = max(1, int(entry.get("qty", 1)))
                except Exception:
                    station_qty[sta] = 1

            # This layout also anchors the fixed GUN/GUN FB symbols, so it must
            # run even when every external station is empty.
            if is_primary:
                green = (0, 255, 0)
                number_font = get_font(12 if is_10wide else 11)
                base_icon_h = max(14, int(0.22 * DPI)) + 70
                base_icon_w = max(base_icon_h, int(0.30 * DPI)) + 70
                icon_max_h = int(round(base_icon_h * 1.5))
                icon_max_w = int(round(base_icon_w * 1.5))
                row_gap = 2
                number_h = number_font.get_height()
                total_h = number_h + row_gap + icon_max_h
                max_bottom = info_box.top - 2
                sms_store_vertical_shift_px = 30
                y_num = max(rect.top + 2, max_bottom - total_h) - 125 + sms_store_vertical_shift_px
                y_icon = y_num + number_h + row_gap
                fb_minor_up_set = {"STA4", "STA8"}
                # Baseline top-icon offsets used as FB-anchor reference.
                fb_anchor_offsets: Dict[str, int] = {
                    "STA1": 80,
                    "STA2": 70,
                    "STA3": 50,
                    "STA4": 50,
                    "STA5": 50,
                    "STA7": 50,
                    "STA8": 50,
                    "STA9": 50,
                    "STA10": 70,
                    "STA11": 80,
                }
                # Slope-out rule:
                # use slope between STA2/3 and apply to 1/2, 3/4, 4/5 and mirror right side.
                base_slope_step = int(fb_anchor_offsets.get("STA2", 70) - fb_anchor_offsets.get("STA3", 50))
                slope_step = int(round(base_slope_step * 1.25))
                top_station_offsets: Dict[str, int] = dict(fb_anchor_offsets)
                top_station_offsets["STA1"] = int(top_station_offsets.get("STA2", 70) + slope_step)
                top_station_offsets["STA4"] = int(top_station_offsets.get("STA3", 50) - slope_step)
                top_station_offsets["STA5"] = int(top_station_offsets.get("STA4", 50) - slope_step)
                top_station_offsets["STA10"] = int(top_station_offsets.get("STA9", 50) + slope_step)
                top_station_offsets["STA8"] = int(top_station_offsets.get("STA9", 50) - slope_step)
                top_station_offsets["STA7"] = int(top_station_offsets.get("STA8", 50) - slope_step)
                top_station_offsets["STA11"] = int(top_station_offsets.get("STA10", 70) + slope_step)
                # Move top STA icons/numbers up by 5px.
                top_sta_global_offset = 15
                # Keep STA5/STA7 in the same current vertical position.
                sta57_keep_offset = 18
                slot_count = len(station_order)
                # Keep station slots fixed across the aircraft image, independent
                # of current icon size, so stations do not collapse toward center.
                left_cx = draw_rect.left + int(draw_rect.width * 0.10)
                right_cx = draw_rect.right - int(draw_rect.width * 0.10)
                if right_cx <= left_cx:
                    right_cx = left_cx + 1
                sta4_cx: Optional[int] = None
                sta4_gun_ref_top_y: Optional[int] = None
                bottom_icon_center_by_station: Dict[str, int] = {}
                bottom_label_center_x_by_station: Dict[str, int] = {}
                bottom_outer_label_y_by_station: Dict[str, int] = {}

                for i, sta in enumerate(station_order):
                    if slot_count <= 1:
                        cx = draw_rect.centerx
                    else:
                        t = i / float(slot_count - 1)
                        cx = int(round(left_cx + (right_cx - left_cx) * t))
                    station_y_offset = int(top_station_offsets.get(sta, 0)) + top_sta_global_offset
                    if sta in {"STA5", "STA7"}:
                        station_y_offset += sta57_keep_offset
                    if sta in {"STA4", "STA5", "STA6", "STA7", "STA8"}:
                        station_y_offset += 10
                    if sta == "STA4":
                        sta4_cx = cx
                        sta4_gun_ref_top_y = y_icon + station_y_offset
                    sta_num = sta.replace("STA", "").strip()
                    icon_name = station_icons.get(sta)
                    if sta in station_loaded:
                        # Top STA number is shown only when a store is loaded on the station.
                        num_surf = number_font.render(sta_num, True, green)
                        num_rect = num_surf.get_rect(centerx=cx, y=y_num + station_y_offset)
                        surface.blit(num_surf, num_rect)
                    icon_y = y_icon + station_y_offset
                    if sta in station_loaded and icon_name:
                        icon_img = self._get_store_icon_image(icon_name, green_tint=True, tint_color=display_icon_tint)
                        if icon_img is not None:
                            src_w, src_h = icon_img.get_size()
                            if src_w > 0 and src_h > 0:
                                fit_scale = min(icon_max_w / float(src_w), icon_max_h / float(src_h))
                                draw_icon_w = max(1, int(round(src_w * fit_scale)))
                                draw_icon_h = max(1, int(round(src_h * fit_scale)))
                                scaled_icon = pygame.transform.smoothscale(icon_img, (draw_icon_w, draw_icon_h))
                                if self._station_icon_faces_left(sta):
                                    scaled_icon = pygame.transform.flip(scaled_icon, True, False)
                                icon_x = cx - draw_icon_w // 2
                                icon_y = y_icon + max(0, (icon_max_h - draw_icon_h) // 2) + station_y_offset
                                surface.blit(scaled_icon, (icon_x, icon_y))

                    # Draw STORE FB beneath loaded stations at the same X, but
                    # always render bottom station numbers even when empty.
                    fb_img = self._get_store_icon_image("STORE FB.png", green_tint=True, tint_color=display_icon_tint)
                    if fb_img is not None:
                        fb_w, fb_h = fb_img.get_size()
                        if fb_w > 0 and fb_h > 0:
                            fb_scale = min(icon_max_w / float(fb_w), icon_max_h / float(fb_h))
                            fb_size_factor = 0.1875
                            if sta in {"STA4", "STA5", "STA7", "STA8"}:
                                fb_size_factor *= 0.9
                            qty_count = max(1, int(station_qty.get(sta, 1)))
                            draw_fb_w = max(1, int(round(fb_w * fb_scale * fb_size_factor)))
                            draw_fb_h = max(1, int(round(fb_h * fb_scale * fb_size_factor)))
                            scaled_fb = pygame.transform.smoothscale(fb_img, (draw_fb_w, draw_fb_h))
                            fb_x = cx - draw_fb_w // 2
                            fb_y = icon_y + 445
                            # Keep FB icons anchored to their baseline position so only
                            # top icons/station numbers are affected by slope changes.
                            fb_y += int(fb_anchor_offsets.get(sta, station_y_offset) - station_y_offset)
                            if sta in {"STA1", "STA2", "STA3", "STA9", "STA10", "STA11"}:
                                fb_y -= 45
                            if sta in {"STA3", "STA9"}:
                                fb_y += 32
                            if sta in fb_minor_up_set:
                                fb_y -= 5
                            if sta in {"STA5", "STA7"}:
                                fb_y += 15
                            if sta in {"STA1", "STA11"}:
                                fb_y -= 10
                            fb_y -= 7
                            fb_x_anchor = fb_x
                            fb_y_anchor = fb_y
                            # Door-state coupling for STA5/STA7 FB icons only.
                            # STA5 follows LT door, STA7 follows RT door.
                            if sta == "STA5":
                                door_state = lt_state
                                if door_state == "PARTIAL":
                                    fb_x -= 5  # outboard (left)
                                    fb_y += 15
                                elif door_state == "OPEN":
                                    fb_x -= 5  # outboard (left)
                                    fb_y += 25
                            elif sta == "STA7":
                                door_state = rt_state
                                if door_state == "PARTIAL":
                                    fb_x += 5  # outboard (right)
                                    fb_y += 15
                                elif door_state == "OPEN":
                                    fb_x += 5  # outboard (right)
                                    fb_y += 25
                            base_center_x = int(fb_x + (draw_fb_w // 2))
                            base_center_y = int(fb_y + (draw_fb_h // 2))
                            offsets = self._store_fb_quantity_offsets(qty_count, draw_fb_w, draw_fb_h)
                            fb_positions: List[Tuple[int, int]] = []
                            for dx, dy in offsets:
                                pos_x = int(round(base_center_x + dx - (draw_fb_w / 2.0)))
                                pos_y = int(round(base_center_y + dy - (draw_fb_h / 2.0)))
                                fb_positions.append((pos_x, pos_y))
                                if sta in station_loaded:
                                    surface.blit(scaled_fb, (pos_x, pos_y))
                            fb_top_y = min((pos_y for _pos_x, pos_y in fb_positions), default=fb_y)
                            bottom_icon_center_by_station[sta] = int(round(fb_top_y + (draw_fb_h / 2.0)))
                            bottom_label_center_x_by_station[sta] = int(fb_x_anchor + (draw_fb_w // 2))
                            if sta in {"STA1", "STA2", "STA3", "STA9", "STA10", "STA11"}:
                                bottom_outer_label_y_by_station[sta] = int((fb_top_y + 7) - 42)
                outer_left_y = int(bottom_outer_label_y_by_station.get("STA3", y_num))
                outer_right_y = int(bottom_outer_label_y_by_station.get("STA9", outer_left_y))
                outer_y = int(round((outer_left_y + outer_right_y) / 2.0))
                num_half_h = max(1, number_font.get_height() // 2)
                row_48_center_y = int(round((
                    bottom_icon_center_by_station.get("STA3", outer_y + num_half_h)
                    + bottom_icon_center_by_station.get("STA9", outer_y + num_half_h)
                ) / 2.0))
                row_57_center_y = int(round((
                    bottom_icon_center_by_station.get("STA4", row_48_center_y)
                    + bottom_icon_center_by_station.get("STA8", row_48_center_y)
                ) / 2.0))
                row_57_icon_center_y = int(round((
                    bottom_icon_center_by_station.get("STA5", row_57_center_y)
                    + bottom_icon_center_by_station.get("STA7", row_57_center_y)
                ) / 2.0))
                for sta in station_order:
                    sta_num = sta.replace("STA", "").strip()
                    label_x = bottom_label_center_x_by_station.get(sta)
                    if label_x is None:
                        continue
                    num_surf = number_font.render(sta_num, True, green)
                    if sta in {"STA1", "STA2", "STA3", "STA9", "STA10", "STA11"}:
                        num_y = outer_y
                    elif sta in {"STA4", "STA8"}:
                        num_y = int(row_48_center_y - (num_surf.get_height() // 2) - 10)
                    elif sta in {"STA5", "STA7"}:
                        num_y = int(row_57_center_y - (num_surf.get_height() // 2))
                    else:
                        continue
                    num_rect = num_surf.get_rect(centerx=label_x, y=num_y)
                    surface.blit(num_surf, num_rect)
                # Draw GUN and GUN FB relative to STA4.
                if sta4_cx is not None:
                    gun_cx = int(sta4_cx + 12)
                    gun_ref_top = sta4_gun_ref_top_y if sta4_gun_ref_top_y is not None else (y_icon + 50)
                    gun_img = self._get_store_icon_image("GUN.png", green_tint=True, tint_color=display_icon_tint)
                    if gun_img is not None:
                        gun_w, gun_h = gun_img.get_size()
                        if gun_w > 0 and gun_h > 0:
                            gun_scale = min(icon_max_w / float(gun_w), icon_max_h / float(gun_h))
                            draw_gun_w = max(1, int(round(gun_w * gun_scale * 0.385)))
                            draw_gun_h = max(1, int(round(gun_h * gun_scale * 0.385)))
                            scaled_gun = pygame.transform.smoothscale(gun_img, (draw_gun_w, draw_gun_h))
                            gun_x = gun_cx - draw_gun_w // 2
                            gun_y = int(gun_ref_top - draw_gun_h - 30)
                            surface.blit(scaled_gun, (gun_x, gun_y))

                    gun_fb_ref_top = int(gun_ref_top + 440)
                    gun_fb_img = self._get_store_icon_image("GUN FB.png", green_tint=True, tint_color=display_icon_tint)
                    if gun_fb_img is not None:
                        gun_fb_w, gun_fb_h = gun_fb_img.get_size()
                        if gun_fb_w > 0 and gun_fb_h > 0:
                            gun_fb_scale = min(icon_max_w / float(gun_fb_w), icon_max_h / float(gun_fb_h))
                            draw_gun_fb_w = max(1, int(round(gun_fb_w * gun_fb_scale * 0.12)))
                            draw_gun_fb_h = max(1, int(round(gun_fb_h * gun_fb_scale * 0.12)))
                            scaled_gun_fb = pygame.transform.smoothscale(gun_fb_img, (draw_gun_fb_w, draw_gun_fb_h))
                            gun_fb_x = gun_cx - draw_gun_fb_w // 2
                            gun_fb_y = int(gun_fb_ref_top - draw_gun_fb_h - 29) - 7
                            surface.blit(scaled_gun_fb, (gun_fb_x, gun_fb_y))
                            sta6_surf = number_font.render("6", True, green)
                            ref_center_y = int(row_57_icon_center_y)
                            sta6_num_y = int(ref_center_y - (sta6_surf.get_height() // 2))
                            sta6_rect = sta6_surf.get_rect(centerx=draw_rect.centerx, y=sta6_num_y)
                            surface.blit(sta6_surf, sta6_rect)
        else:
            # Subportal SMS: render only top station numbers/icons and GUN icon.
            store_loads = self._active_display_store_loads()
            display_icon_tint = self._active_display_store_icon_tint_color()
            station_order = ["STA1", "STA2", "STA3", "STA4", "STA5", "STA7", "STA8", "STA9", "STA10", "STA11"]
            station_icons: Dict[str, str] = {}
            for sta in station_order:
                entry = store_loads.get(sta, {})
                if not isinstance(entry, dict):
                    continue
                weapon = str(entry.get("weapon", "")).strip()
                icon_name = self._store_icon_for_entry(entry)
                if weapon == "" or weapon.upper() == "NONE" or icon_name == "":
                    continue
                station_icons[sta] = icon_name

            if len(station_icons) > 0:
                green = (0, 255, 0)
                sub_scale = max(0.30, min(1.0, draw_rect.width / float(5 * DPI)))
                number_font = get_font(max(8, int(round(11 * sub_scale))))
                base_icon_h = max(14, int(0.22 * DPI)) + 70
                base_icon_w = max(base_icon_h, int(0.30 * DPI)) + 70
                icon_max_h = max(8, int(round(int(round(base_icon_h * 1.5)) * sub_scale)))
                icon_max_w = max(8, int(round(int(round(base_icon_w * 1.5)) * sub_scale)))
                row_gap = max(1, int(round(2 * sub_scale)))
                number_h = number_font.get_height()
                y_num = draw_rect.top + max(2, int(round(8 * sub_scale)))
                y_icon = y_num + number_h + row_gap

                fb_anchor_offsets: Dict[str, int] = {
                    "STA1": 80,
                    "STA2": 70,
                    "STA3": 50,
                    "STA4": 50,
                    "STA5": 50,
                    "STA7": 50,
                    "STA8": 50,
                    "STA9": 50,
                    "STA10": 70,
                    "STA11": 80,
                }
                base_slope_step = int(fb_anchor_offsets.get("STA2", 70) - fb_anchor_offsets.get("STA3", 50))
                slope_step = int(round(base_slope_step * 1.25))
                top_station_offsets: Dict[str, int] = dict(fb_anchor_offsets)
                top_station_offsets["STA1"] = int(top_station_offsets.get("STA2", 70) + slope_step)
                top_station_offsets["STA4"] = int(top_station_offsets.get("STA3", 50) - slope_step)
                top_station_offsets["STA5"] = int(top_station_offsets.get("STA4", 50) - slope_step)
                top_station_offsets["STA10"] = int(top_station_offsets.get("STA9", 50) + slope_step)
                top_station_offsets["STA8"] = int(top_station_offsets.get("STA9", 50) - slope_step)
                top_station_offsets["STA7"] = int(top_station_offsets.get("STA8", 50) - slope_step)
                top_station_offsets["STA11"] = int(top_station_offsets.get("STA10", 70) + slope_step)
                top_sta_global_offset = 15
                sta57_keep_offset = 18

                slot_count = len(station_order)
                left_cx = draw_rect.left + int(draw_rect.width * 0.10)
                right_cx = draw_rect.right - int(draw_rect.width * 0.10)
                if right_cx <= left_cx:
                    right_cx = left_cx + 1
                sta4_cx: Optional[int] = None
                sta4_icon_top_y: Optional[int] = None

                for i, sta in enumerate(station_order):
                    if slot_count <= 1:
                        cx = draw_rect.centerx
                    else:
                        t = i / float(slot_count - 1)
                        cx = int(round(left_cx + (right_cx - left_cx) * t))
                    station_y_offset = int(round((int(top_station_offsets.get(sta, 0)) + top_sta_global_offset) * sub_scale))
                    if sta in {"STA5", "STA7"}:
                        station_y_offset += int(round(sta57_keep_offset * sub_scale))
                    if sta in {"STA4", "STA5", "STA6", "STA7", "STA8"}:
                        station_y_offset += int(round(10 * sub_scale))

                    icon_name = station_icons.get(sta)
                    if not icon_name:
                        continue
                    sta_num = sta.replace("STA", "").strip()
                    num_surf = number_font.render(sta_num, True, green)
                    num_rect = num_surf.get_rect(centerx=cx, y=y_num + station_y_offset)
                    surface.blit(num_surf, num_rect)

                    icon_img = self._get_store_icon_image(icon_name, green_tint=True, tint_color=display_icon_tint)
                    if icon_img is None:
                        continue
                    src_w, src_h = icon_img.get_size()
                    if src_w <= 0 or src_h <= 0:
                        continue
                    fit_scale = min(icon_max_w / float(src_w), icon_max_h / float(src_h))
                    draw_icon_w = max(1, int(round(src_w * fit_scale)))
                    draw_icon_h = max(1, int(round(src_h * fit_scale)))
                    scaled_icon = pygame.transform.smoothscale(icon_img, (draw_icon_w, draw_icon_h))
                    if self._station_icon_faces_left(sta):
                        scaled_icon = pygame.transform.flip(scaled_icon, True, False)
                    icon_x = cx - draw_icon_w // 2
                    icon_y = y_icon + max(0, (icon_max_h - draw_icon_h) // 2) + station_y_offset
                    surface.blit(scaled_icon, (icon_x, icon_y))

                    if sta == "STA4":
                        sta4_cx = cx
                        sta4_icon_top_y = icon_y

                # Subportal/submenu intentionally does not render GUN icon.

        chaff = int(SMS_STATE.get("chaff", 10))
        flare = int(SMS_STATE.get("flare", 10))
        font = get_font(15)
        try:
            excm_prog = int(SMS_STATE.get("last_cm_program", SMS_STATE.get("excm_program", 0)) or 0)
        except Exception:
            excm_prog = 0
        prog_text = str(excm_prog) if excm_prog in {1, 2, 3} else "--"
        lines = [
            ("CHAFF", str(chaff)),
            ("FLARE", str(flare)),
            ("EXCM", "ARM" if self._excm_armed() else "STBY"),
            ("PROG", prog_text),
        ]
        y = info_box.top + 6
        for label, value in lines:
            l_surf = font.render(label, True, (255, 255, 255))
            v_surf = font.render(value, True, (255, 255, 255))
            l_rect = l_surf.get_rect(left=info_box.left + 6, y=y)
            v_rect = v_surf.get_rect(right=info_box.right - 6, y=y)
            surface.blit(l_surf, l_rect)
            surface.blit(v_surf, v_rect)
            y += max(l_surf.get_height(), v_surf.get_height()) + 2

        if is_primary:
            self._draw_osb_labels(surface, rect, context)
            self._draw_excm_confirm_popup(surface, rect)
        else:
            bottom_font = get_font(18)
            bottom = bottom_font.render("SMS", True, (0, 255, 255))
            bottom_rect = bottom.get_rect(centerx=rect.centerx)
            bottom_rect.bottom = rect.bottom - 2
            surface.blit(bottom, bottom_rect)
        surface.set_clip(prev_clip)

    def _draw_osb_labels(self, surface, rect: pygame.Rect, context: FormatContext) -> None:
        top_count = 5 if rect.width < int(10 * DPI) else 10
        side_count = 6 if rect.height >= int(7 * DPI) - 1 else 5
        top_offset = DISPLAY_OSB_H if top_count > 0 else 0
        if side_count < 4:
            return
        sms_ground_safe_active = any(str(t).strip().upper() == "SMS GROUND SAFE" for t, _ in get_current_icaws_alerts())
        master_arm_on = self._master_arm_on()
        cntl_submenu_open = self._cntl_submenu_open()

        def _osb_box(label: str) -> Optional[pygame.Rect]:
            token = str(label).upper().strip()
            if len(token) < 2:
                return None
            side = token[0]
            try:
                idx = int(token[1:])
            except Exception:
                return None
            if side == "T":
                if idx < 1 or idx > top_count:
                    return None
                return pygame.Rect(rect.x + (idx - 1) * GRID_CELL_W, rect.y, GRID_CELL_W, DISPLAY_OSB_H)
            if side == "L":
                if idx < 1 or idx > side_count:
                    return None
                return pygame.Rect(rect.x, rect.y + top_offset - SIDE_OSB_Y_SHIFT + (idx - 1) * DISPLAY_OSB_H, GRID_CELL_W, DISPLAY_OSB_H)
            if side == "R":
                if idx < 1 or idx > side_count:
                    return None
                return pygame.Rect(rect.right - GRID_CELL_W, rect.y + top_offset - SIDE_OSB_Y_SHIFT + (idx - 1) * DISPLAY_OSB_H, GRID_CELL_W, DISPLAY_OSB_H)
            return None

        t1_box = _osb_box("T1")
        t3_box = _osb_box("T3")
        t5_box = _osb_box("T5")
        l1_box = _osb_box("L1")
        l2_box = _osb_box("L2")
        l3_box = _osb_box("L3")
        l4_box = _osb_box("L4")
        r3_box = _osb_box("R3")
        r4_box = _osb_box("R4")

        def _draw_text_only_highlight(
            box: pygame.Rect,
            lines: List[str],
            h_align: str,
            font_size: int = 14,
            padding: int = OSB_PADDING,
        ) -> None:
            if not isinstance(lines, list) or len(lines) <= 0:
                return
            font_obj = get_font(font_size)
            rendered = [font_obj.render(str(line), True, (255, 255, 255)) for line in lines]
            if len(rendered) <= 0:
                return
            total_h = sum(s.get_height() for s in rendered) + max(0, len(rendered) - 1)
            y = box.centery - total_h // 2
            text_rects: List[pygame.Rect] = []
            for surf in rendered:
                tr = surf.get_rect()
                if h_align == "left":
                    tr.left = box.left + int(padding)
                elif h_align == "right":
                    tr.right = box.right - int(padding)
                else:
                    tr.centerx = box.centerx
                tr.y = y
                text_rects.append(tr)
                y += surf.get_height() + 1
            if len(text_rects) <= 0:
                return
            hl = text_rects[0].copy()
            for tr in text_rects[1:]:
                hl.union_ip(tr)
            hl.inflate_ip(4, 2)
            if hl.width > 0 and hl.height > 0:
                pygame.draw.rect(surface, (0, 0, 0), hl, 0)

        if cntl_submenu_open:
            if self._cntl_inv_prog_open():
                # INV PROG submenu keeps only T1 (rendered via T1 override).
                return
            if t3_box is not None:
                t3_state = ButtonState(
                    button_id="SMS_CNTL_T3_LIVE_TRAIN",
                    button_type=ButtonType.DOUBLE_FUNCTION,
                    options=["LIVE", "TRAIN"],
                    selected_index=self._cntl_live_train_idx(),
                    h_align="center",
                    v_align="top",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("T3") else 0,
                )
                render_button(surface, t3_box, t3_state, get_font, 0)
            if l1_box is not None:
                _draw_text_only_highlight(l1_box, ["INV", "PROG>"], "left")
                l1_state = ButtonState(
                    button_id="SMS_CNTL_L1_INV_PROG",
                    button_type=ButtonType.PAGE_ACCESS,
                    text="INV\nPROG>",
                    enabled=True,
                    h_align="left",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("L1") else 0,
                )
                render_button(surface, l1_box, l1_state, get_font, 0)
            if l2_box is not None:
                doors_open = bool(int(SMS_STATE.get("doors_open", 0)))
                _draw_text_only_highlight(l2_box, ["DOORS", "OPEN", "CLOSED"], "left")
                l2_state = ButtonState(
                    button_id="SMS_CNTL_L2_DOORS",
                    button_type=ButtonType.DOUBLE_FUNCTION,
                    function_label="DOORS",
                    function_label_color=(0, 255, 255),
                    options=["OPEN", "CLOSED"],
                    selected_index=0 if doors_open else 1,
                    enabled=not sms_ground_safe_active,
                    h_align="left",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("L2") else 0,
                )
                render_button(surface, l2_box, l2_state, get_font, 0)
            if l3_box is not None:
                _draw_text_only_highlight(l3_box, ["EXCM", "PROG>"], "left")
                l3_state = ButtonState(
                    button_id="SMS_CNTL_L3_EXCM_PROG",
                    button_type=ButtonType.PAGE_ACCESS,
                    text="EXCM\nPROG>",
                    enabled=True,
                    h_align="left",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("L3") else 0,
                )
                render_button(surface, l3_box, l3_state, get_font, 0)
            if l4_box is not None:
                _draw_text_only_highlight(l4_box, ["SJ>"], "left")
                l4_state = ButtonState(
                    button_id="SMS_CNTL_L4_SJ",
                    button_type=ButtonType.PAGE_ACCESS,
                    text="SJ>",
                    enabled=True,
                    h_align="left",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("L4") else 0,
                )
                render_button(surface, l4_box, l4_state, get_font, 0)
            return

        # Black contrast highlight behind only the actual text extents.
        if l3_box is not None:
            _draw_text_only_highlight(l3_box, ["DOORS", "OPEN", "CLOSED"], "left")
        if r3_box is not None:
            _draw_text_only_highlight(r3_box, ["ET OPT", "OFF"], "right")

        if t5_box is not None:
            t5_state = ButtonState(
                button_id="SMS_T5_CNTL",
                button_type=ButtonType.PAGE_ACCESS,
                text="CNTL>",
                enabled=True,
                h_align="center",
                v_align="top",
                padding=OSB_PADDING,
                font_size=14,
                flash_until_ms=1 if context.is_osb_flashing("T5") else 0,
            )
            render_button(surface, t5_box, t5_state, get_font, 0)

        # T3: SAFE/ARM (white), driven by cockpit MASTER ARM panel state.
        live_train_idx = self._sms_live_train_idx()
        if t3_box is not None and master_arm_on:
            # MASTER ARM ON -> show LIVE/TRAIN double-function styling.
            live_train_font = get_font(14)
            live_selected = live_train_idx == 0
            train_selected = live_train_idx == 1
            live_surf = live_train_font.render("LIVE", True, (255, 255, 255) if live_selected else (128, 128, 128))
            train_surf = live_train_font.render("TRAIN", True, (255, 255, 255) if train_selected else (128, 128, 128))
            y = t3_box.top + OSB_PADDING
            live_rect = live_surf.get_rect(centerx=t3_box.centerx, y=y)
            train_rect = train_surf.get_rect(centerx=t3_box.centerx, y=live_rect.bottom + 1)
            surface.blit(live_surf, live_rect)
            surface.blit(train_surf, train_rect)
            if live_selected:
                pygame.draw.rect(surface, (255, 255, 255), live_rect.inflate(4, 2), 1)
            else:
                pygame.draw.rect(surface, (255, 255, 255), train_rect.inflate(4, 2), 1)
        elif t3_box is not None:
            safe_font = get_font(14)
            safe_surf = safe_font.render("SAFE", True, (255, 255, 255))
            safe_rect = safe_surf.get_rect(centerx=t3_box.centerx)
            safe_rect.y = t3_box.top + OSB_PADDING
            surface.blit(safe_surf, safe_rect)

        doors_open = bool(int(SMS_STATE.get("doors_open", 0)))
        if l3_box is not None:
            l3_state = ButtonState(
                button_id="SMS_L3_DOORS",
                button_type=ButtonType.DOUBLE_FUNCTION,
                function_label="DOORS",
                function_label_color=(0, 255, 255),
                options=["OPEN", "CLOSED"],
                selected_index=0 if doors_open else 1,
                enabled=not sms_ground_safe_active,
                h_align="left",
                v_align="center",
                padding=OSB_PADDING,
                font_size=14,
                flash_until_ms=1 if context.is_osb_flashing("L3") else 0,
            )
            render_button(surface, l3_box, l3_state, get_font, 0)

        if l4_box is not None:
            l4_state = ButtonState(
                button_id="SMS_L4_EXCM",
                button_type=ButtonType.MOMENTARY_SINGLE,
                text="EXCM\nARM" if self._excm_armed() else "EXCM\nSTBY",
                is_single_function=True,
                is_on=self._excm_armed(),
                enabled=master_arm_on,
                h_align="left",
                v_align="center",
                padding=OSB_PADDING,
                font_size=14,
                flash_until_ms=1 if context.is_osb_flashing("L4") else 0,
            )
            render_button(surface, l4_box, l4_state, get_font, 0)

        if r3_box is not None:
            r3_state = ButtonState(
                button_id="SMS_R3_ETOPT",
                button_type=ButtonType.STATUS_LABEL,
                text="ET OPT\nOFF",
                enabled=master_arm_on,
                h_align="right",
                v_align="center",
                padding=OSB_PADDING,
                font_size=14,
                flash_until_ms=1 if context.is_osb_flashing("R3") else 0,
            )
            render_button(surface, r3_box, r3_state, get_font, 0)
            # Underline ET OPT.
            underline_color = (0, 255, 0) if master_arm_on else (128, 128, 128)
            font = get_font(14)
            line1 = font.render("ET OPT", True, underline_color)
            line2 = font.render("OFF", True, underline_color)
            total_h = line1.get_height() + line2.get_height() + 1
            y0 = r3_box.centery - total_h // 2
            l1_rect = line1.get_rect()
            l1_rect.right = r3_box.right - OSB_PADDING
            l1_rect.y = y0
            pygame.draw.line(surface, underline_color, (l1_rect.left, l1_rect.bottom + 1), (l1_rect.right, l1_rect.bottom + 1), 1)

        if r4_box is not None:
            r4_state = ButtonState(
                button_id="SMS_R4_ETRUN",
                button_type=ButtonType.STATUS_LABEL,
                text="ET RUN",
                enabled=master_arm_on,
                h_align="right",
                v_align="center",
                padding=OSB_PADDING,
                font_size=14,
                flash_until_ms=1 if context.is_osb_flashing("R4") else 0,
            )
            render_button(surface, r4_box, r4_state, get_font, 0)

    def _toggle_doors(self) -> None:
        if any(str(t).strip().upper() == "SMS GROUND SAFE" for t, _ in get_current_icaws_alerts()):
            return
        now_ms = pygame.time.get_ticks()
        target_open = not bool(int(SMS_STATE.get("doors_open", 0)))
        SMS_STATE["doors_open"] = 1 if target_open else 0
        self._command_doors(target_open, now_ms)

    def _inv_hit_station(self, pos: Tuple[int, int], rect: pygame.Rect) -> Optional[str]:
        grid = self._popup_grid_rect(rect)
        if not grid.collidepoint(pos):
            return None
        for station, box, _label in self._inv_station_button_rects(grid):
            if box.collidepoint(pos):
                return station
        return None

    def on_click(self, pos: Tuple[int, int], rect: pygame.Rect, context: FormatContext) -> bool:
        self._set_popup_anchor_portal_index(getattr(context, "portal_index", None))
        if self._excm_arm_confirm_pending():
            self._set_excm_armed(True)
            self._set_excm_arm_confirm_pending(False)
            return True
        if not (self._cntl_submenu_open() and self._cntl_inv_prog_open()):
            return False
        grid = self._popup_grid_rect(rect)
        if not grid.collidepoint(pos):
            return False
        if not self._cntl_inv_load_open():
            hit_station = self._inv_hit_station(pos, rect)
            if hit_station is not None:
                self._inv_toggle_station_selection(hit_station)
                self._sync_inv_load_selection_state()
                return True
            e6 = self._inv_cell_rect(grid, "E6")
            if e6.collidepoint(pos) and len(self._inv_selected_stations()) > 0:
                self._set_cntl_inv_load_open(True)
                self._sync_inv_load_selection_state()
                return True
            e7 = self._inv_cell_rect(grid, "E7")
            if e7.collidepoint(pos) and self._inv_selected_has_loaded_store():
                self._inv_clear_selected_stores()
                return True
            return True
        # LOAD submenu interactions.
        type_opts, rack_opts, wpn_opts, fuze_opts, fuze_mode_opts, qty_max, qty_value = self._sync_inv_load_selection_state()
        current_sel = self._cntl_inv_load_selected_field()
        e1 = self._inv_cell_rect(grid, "E1")
        if e1.collidepoint(pos):
            if current_sel == "TYPE":
                self._set_cntl_inv_load_selected_field("")
                self._set_cntl_inv_load_type_menu_open(False)
                self._set_cntl_inv_load_fuze_mode_open(False)
            else:
                self._set_cntl_inv_load_selected_field("TYPE")
                self._set_cntl_inv_load_type_menu_open(True)
                self._set_cntl_inv_load_type_page(0)
                self._set_cntl_inv_load_fuze_mode_open(False)
            return True

        d4 = self._inv_cell_rect(grid, "D4")
        if d4.collidepoint(pos):
            if current_sel == "RACK":
                self._set_cntl_inv_load_selected_field("")
                self._set_cntl_inv_load_type_menu_open(False)
                self._set_cntl_inv_load_fuze_mode_open(False)
            else:
                self._set_cntl_inv_load_selected_field("RACK")
                self._set_cntl_inv_load_type_menu_open(True)
                self._set_cntl_inv_load_type_page(0)
                self._set_cntl_inv_load_fuze_mode_open(False)
            return True

        d5 = self._inv_cell_rect(grid, "D5")
        if d5.collidepoint(pos):
            if current_sel == "WPN":
                self._set_cntl_inv_load_selected_field("")
                self._set_cntl_inv_load_type_menu_open(False)
                self._set_cntl_inv_load_fuze_mode_open(False)
            else:
                self._set_cntl_inv_load_selected_field("WPN")
                self._set_cntl_inv_load_type_menu_open(True)
                self._set_cntl_inv_load_type_page(0)
                self._set_cntl_inv_load_fuze_mode_open(False)
            return True

        e5 = self._inv_cell_rect(grid, "E5")
        if e5.collidepoint(pos) and self._inv_is_gbu_wpn(self._inv_wpn_value()):
            if current_sel == "FUZE":
                self._set_cntl_inv_load_selected_field("")
                self._set_cntl_inv_load_type_menu_open(False)
                self._set_cntl_inv_load_fuze_mode_open(False)
            else:
                self._set_cntl_inv_load_selected_field("FUZE")
                self._set_cntl_inv_load_type_menu_open(True)
                self._set_cntl_inv_load_type_page(0)
                self._set_cntl_inv_load_fuze_mode_open(False)
            return True

        d6 = self._inv_cell_rect(grid, "D6")
        if d6.collidepoint(pos):
            if current_sel == "QNTY":
                self._set_cntl_inv_load_selected_field("")
                self._set_cntl_inv_load_type_menu_open(False)
                self._set_cntl_inv_load_fuze_mode_open(False)
                SmsFormat._ui_set("cntl_inv_load_qty_input", "")
            else:
                self._set_cntl_inv_load_selected_field("QNTY")
                self._set_cntl_inv_load_type_menu_open(True)
                self._set_cntl_inv_load_type_page(0)
                self._set_cntl_inv_load_fuze_mode_open(False)
                open_qty = max(1, min(9, int(qty_value if qty_value > 0 else 1)))
                SmsFormat._ui_set("cntl_inv_load_qty_input", str(open_qty))
            return True

        if self._cntl_inv_load_type_menu_open():
            if current_sel == "QNTY":
                qty = max(0, int(self._inv_qty_value()))
                qmax = max(0, int(self._inv_qty_max()))
                for cell in [
                    "A4", "B4", "C4",
                    "A5", "B5", "C5",
                    "A6", "B6", "C6",
                    "B7", "C7",
                    "A7", "A8",
                ]:
                    if self._inv_cell_rect(grid, cell).collidepoint(pos):
                        return self._inv_apply_qty_key_cell(cell, qty, qmax)
                return True

            opts = self._inv_load_options_for_selection(current_sel, type_opts, rack_opts, wpn_opts, fuze_opts, fuze_mode_opts)
            pages = self._inv_option_pages(opts, page_size=12)
            a8 = self._inv_cell_rect(grid, "A8")
            if a8.collidepoint(pos) and len(pages) > 1:
                page = self._cntl_inv_load_type_page()
                self._set_cntl_inv_load_type_page((page + 1) % len(pages))
                return True
            page = self._cntl_inv_load_type_page()
            if page >= len(pages):
                page = max(0, len(pages) - 1)
                self._set_cntl_inv_load_type_page(page)
            active = pages[page] if len(pages) > 0 else []
            opt_cells = [
                "A4", "B4", "C4",
                "A5", "B5", "C5",
                "A6", "B6", "C6",
                "A7", "B7", "C7",
            ]
            for idx, cell in enumerate(opt_cells):
                if self._inv_cell_rect(grid, cell).collidepoint(pos):
                    return self._inv_select_load_option_cell(
                        cell,
                        current_sel,
                        type_opts,
                        rack_opts,
                        wpn_opts,
                        fuze_opts,
                        fuze_mode_opts,
                    )
        return True

    def on_osb(self, label: str, context: FormatContext) -> bool:
        self._set_popup_anchor_portal_index(getattr(context, "portal_index", None))
        token = str(label).upper().strip()
        if self._excm_arm_confirm_pending():
            # Keep OSBs inert while confirmation is displayed.
            return True

        if self._cntl_submenu_open():
            if self._cntl_inv_prog_open():
                if not self._cntl_inv_load_open():
                    station = self._inv_station_for_edge_osb(token)
                    if station != "":
                        self._inv_toggle_station_selection(station)
                        self._sync_inv_load_selection_state()
                        return True
                    if token in {"R6", "R7"} and self._inv_selected_has_loaded_store():
                        self._inv_clear_selected_stores()
                        return True
                    if token in {"R5", "R6", "R7"} and len(self._inv_selected_stations()) > 0:
                        self._set_cntl_inv_load_open(True)
                        self._sync_inv_load_selection_state()
                        return True
                if self._cntl_inv_load_open() and self._cntl_inv_load_type_menu_open():
                    type_opts, rack_opts, wpn_opts, fuze_opts, fuze_mode_opts, _qty_max, _qty_value = self._sync_inv_load_selection_state()
                    current_sel = self._cntl_inv_load_selected_field()
                    edge_cell = self._inv_load_edge_cell_for_osb(token)
                    if edge_cell != "" and current_sel == "QNTY":
                        qty = max(0, int(self._inv_qty_value()))
                        qmax = max(0, int(self._inv_qty_max()))
                        return self._inv_apply_qty_key_cell(edge_cell, qty, qmax)
                    if edge_cell != "" and current_sel in {"TYPE", "RACK", "WPN", "FUZE"}:
                        return self._inv_select_load_option_cell(
                            edge_cell,
                            current_sel,
                            type_opts,
                            rack_opts,
                            wpn_opts,
                            fuze_opts,
                            fuze_mode_opts,
                        )
                if token in {"R3", "R4", "R5", "R6", "R7"} and self._cntl_inv_load_open():
                    self._sync_inv_load_selection_state()
                    if not self._inv_is_gbu_wpn(self._inv_wpn_value()):
                        return True
                    if self._cntl_inv_load_selected_field() == "FUZE":
                        self._set_cntl_inv_load_selected_field("")
                        self._set_cntl_inv_load_type_menu_open(False)
                        self._set_cntl_inv_load_fuze_mode_open(False)
                    else:
                        self._set_cntl_inv_load_selected_field("FUZE")
                        self._set_cntl_inv_load_type_menu_open(True)
                        self._set_cntl_inv_load_type_page(0)
                        self._set_cntl_inv_load_fuze_mode_open(False)
                    return True
                if token in {"T5", "R1", "R2"} and self._cntl_inv_load_open():
                    self._sync_inv_load_selection_state()
                    if self._cntl_inv_load_selected_field() == "TYPE":
                        self._set_cntl_inv_load_selected_field("")
                        self._set_cntl_inv_load_type_menu_open(False)
                        self._set_cntl_inv_load_fuze_mode_open(False)
                    else:
                        self._set_cntl_inv_load_selected_field("TYPE")
                        self._set_cntl_inv_load_type_menu_open(True)
                        self._set_cntl_inv_load_type_page(0)
                        self._set_cntl_inv_load_fuze_mode_open(False)
                    return True
                if token == "T1":
                    if self._cntl_inv_load_open():
                        self._set_cntl_inv_load_type_menu_open(False)
                        self._set_cntl_inv_load_type_page(0)
                        self._set_cntl_inv_load_open(False)
                    else:
                        self._set_cntl_inv_prog_open(False)
                    return True
                # While INV PROG is open, grid interactions are handled in on_click.
                return False
            if token == "T1":
                self._set_cntl_submenu_open(False)
                return True
            if token == "T3":
                self._set_cntl_live_train_idx(1 if self._cntl_live_train_idx() == 0 else 0)
                return True
            if token == "L1":
                self._set_cntl_inv_load_open(False)
                self._set_cntl_inv_load_type_menu_open(False)
                self._set_cntl_inv_load_type_page(0)
                self._set_cntl_inv_prog_open(True)
                return True
            if token == "L2":
                self._toggle_doors()
                return True
            if token in {"L3", "L4"}:
                return True
            return False

        if token == "T1":
            self._set_cntl_inv_prog_open(False)
            self._set_cntl_inv_load_type_menu_open(False)
            self._set_cntl_inv_load_type_page(0)
            context.request_vded(context.portal_index, "MENU")
            return True
        if token == "T5":
            self._set_cntl_inv_prog_open(False)
            self._set_cntl_inv_load_type_menu_open(False)
            self._set_cntl_inv_load_type_page(0)
            self._set_cntl_submenu_open(True)
            return True
        if token == "T3":
            if self._master_arm_on():
                self._set_sms_live_train_idx(1 if self._sms_live_train_idx() == 0 else 0)
            return True
        if token == "L3":
            self._toggle_doors()
            return True
        if token == "L4":
            if self._master_arm_on():
                if self._excm_armed():
                    self._set_excm_armed(False)
                    self._set_excm_arm_confirm_pending(False)
                else:
                    self._set_excm_arm_confirm_pending(True)
            return True
        if token in {"R3", "R4"}:
            return True
        return False

    def defer_osb_to_grid_click(self, label: str) -> bool:
        if not (self._cntl_submenu_open() and self._cntl_inv_prog_open()):
            return False
        token = str(label).upper().strip()
        # T1 remains the page/back OSB. Every other overlapping zone belongs to
        # the rendered INV grid, so let on_click use exact grid cell bounds.
        return token != "T1"

    def osb_is_interactive(self, label: str) -> bool:
        token = str(label).upper().strip()
        sms_ground_safe_active = any(str(t).strip().upper() == "SMS GROUND SAFE" for t, _ in get_current_icaws_alerts())
        if self._excm_arm_confirm_pending():
            return False
        if self._cntl_submenu_open():
            if self._cntl_inv_prog_open():
                # Allow A/E side grid cells used by INV PROG/LOAD to pass through
                # OSB handling into on_click.
                # Include full left/right sides so E-field clicks are not blocked.
                return token in {
                    "T1",
                    "T5",
                    "L1",
                    "L2",
                    "L3",
                    "L4",
                    "L5",
                    "L6",
                    "L7",
                    "R1",
                    "R2",
                    "R3",
                    "R4",
                    "R5",
                    "R6",
                    "R7",
                }
            if token == "L2" and sms_ground_safe_active:
                return False
            return token in {"T1", "T3", "L1", "L2", "L3", "L4"}
        if token == "L3" and sms_ground_safe_active:
            return False
        if token in {"L4", "R3", "R4"}:
            return self._master_arm_on()
        if token in {"T1", "T3", "T5", "L3"}:
            return True
        return False

    def t1_opens_menu(self) -> bool:
        # T1 opens MENU on the base SMS page, but returns from CNTL submenu.
        return not self._cntl_submenu_open()

    def get_t1_override(self, system_mode: str) -> Optional[List[Tuple[str, Tuple[int, int, int]]]]:
        _ = system_mode
        if self._cntl_submenu_open():
            if self._cntl_inv_prog_open():
                return [("SMS", (0, 255, 0)), ("INV", (255, 0, 255)), ("", (0, 0, 0))]
            return [("SMS", (0, 255, 0)), ("CNTL", (255, 0, 255)), ("", (0, 0, 0))]
        return None


def update_sms_door_transitions(now_ms: int) -> None:
    SmsFormat._update_door_state("LT", int(now_ms))
    SmsFormat._update_door_state("RT", int(now_ms))
