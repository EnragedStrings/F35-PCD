import importlib
from typing import Any, Callable, Iterable, List


DEFAULT_FORMAT_NAMES: List[str] = [
    "ASR1",
    "CKLST",
    "CNI",
    "DAS",
    "DIM",
    "EFI",
    "ENG",
    "FCS",
    "FUEL",
    "HUD",
    "ICAWS",
    "PHM",
    "SMS",
    "SRCH",
    "TFLIR",
    "TSD1",
    "TSD2",
    "TSD3",
    "TWD",
    "WPN-A",
    "WPN-S",
]

DEFAULT_STATUS_FORMATS: List[str] = ["status1", "status2"]


def _cls(module_name: str, class_name: str):
    mod = importlib.import_module(module_name)
    return getattr(mod, class_name)


def _mk_tsd(name: str):
    Tsd1Format = _cls("format_defs.tsd", "Tsd1Format")
    fmt = Tsd1Format()
    fmt.name = str(name)
    return fmt


def bootstrap_default_formats(
    register_format: Callable[[str, Callable[[], Any]], None],
    register_vded: Callable[[str, Callable[[], Any]], None],
    *,
    format_names: Iterable[str],
    status_formats: Iterable[str],
    BasicFormat: Any,
    MenuVded: Any,
) -> None:
    StatusBarFormat = _cls("format_defs.statusbar", "StatusBarFormat")
    EngineFormat = _cls("format_defs.eng", "EngineFormat")
    AutopilotFormat = _cls("format_defs.autopilot", "AutopilotFormat")
    NavMenuFormat = _cls("format_defs.navmenu", "NavMenuFormat")
    IffFormat = _cls("format_defs.iff", "IffFormat")
    AltitudeFormat = _cls("format_defs.altitude", "AltitudeFormat")
    WindFormat = _cls("format_defs.wind", "WindFormat")
    CommFormat = _cls("format_defs.comm", "CommFormat")
    CniFormat = _cls("format_defs.cni", "CniFormat")
    CklstFormat = _cls("format_defs.cklst", "CklstFormat")
    IcawsFormat = _cls("format_defs.icaws", "IcawsFormat")
    FuelFormat = _cls("format_defs.fuel", "FuelFormat")
    SmsFormat = _cls("format_defs.sms", "SmsFormat")
    PhmFormat = _cls("format_defs.phm", "PhmFormat")
    FcsFormat = _cls("format_defs.fcs", "FcsFormat")
    EfiFormat = _cls("format_defs.efi", "EfiFormat")
    HudFormat = _cls("format_defs.hud", "HudFormat")
    DimV2Format = _cls("format_defs.dim", "DimV2Format")
    Das3DFormat = _cls("format_defs.das3d", "Das3DFormat")
    Tflir3DFormat = _cls("format_defs.tflir3d", "Tflir3DFormat")
    Asr1Format = _cls("format_defs.asr1", "Asr1Format")
    SearchFormat = _cls("format_defs.search", "SearchFormat")
    TwdFormat = _cls("format_defs.twd", "TwdFormat")
    WpnAFormat = _cls("format_defs.wpn_a", "WpnAFormat")
    WpnSFormat = _cls("format_defs.wpn_s", "WpnSFormat")

    for name in list(format_names) + list(status_formats):
        register_format(str(name), lambda fmt_name=name: BasicFormat(name=str(fmt_name)))

    register_vded("MENU", MenuVded)

    register_format("status1", lambda: StatusBarFormat(["Engine", "Fuel", "FCS", "ICAWS", "Autopilot", "SWAP"]))
    register_format("status2", lambda: StatusBarFormat(["CNI", "DIM", "MENU2", "IFF", "GCAS", "TIME"]))
    register_format("ENG", EngineFormat)
    register_format("AUTOPILOT", AutopilotFormat)
    register_format("NAVMENU", NavMenuFormat)
    register_format("IFF", IffFormat)
    register_format("ALTITUDE", AltitudeFormat)
    register_format("WIND", WindFormat)
    register_format("COMM", CommFormat)
    register_format("CNI", CniFormat)
    register_format("CKLST", CklstFormat)
    register_format("ICAWS", IcawsFormat)
    register_format("FUEL", FuelFormat)
    register_format("SMS", SmsFormat)
    register_format("PHM", PhmFormat)
    register_format("FCS", FcsFormat)
    register_format("EFI", EfiFormat)
    register_format("HUD", HudFormat)
    register_format("DIM", DimV2Format)
    register_format("DAS", Das3DFormat)
    register_format("TFLIR", Tflir3DFormat)
    register_format("ASR1", Asr1Format)
    register_format("SRCH", SearchFormat)
    register_format("TWD", TwdFormat)
    register_format("WPN-A", WpnAFormat)
    register_format("WPN-S", WpnSFormat)

    register_format("TSD-1", lambda: _mk_tsd("TSD1"))
    register_format("TSD1", lambda: _mk_tsd("TSD1"))
    register_format("TSD-2", lambda: _mk_tsd("TSD2"))
    register_format("TSD2", lambda: _mk_tsd("TSD2"))
    register_format("TSD-3", lambda: _mk_tsd("TSD3"))
    register_format("TSD3", lambda: _mk_tsd("TSD3"))
