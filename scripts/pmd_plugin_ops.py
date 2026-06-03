from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple


def pmd_status_menu_action_from_plugin_result(
    result: object,
    now_ms: int,
    osb_flash_ms: int,
) -> Tuple[bool, Optional[Tuple[str, Optional[str], int]]]:
    if isinstance(result, bool):
        return bool(result), None
    if result is None:
        return True, None
    if isinstance(result, str):
        token = str(result).strip().lower()
        if token == "":
            return True, None
        if token == "back":
            return True, ("back", None, int(now_ms) + int(osb_flash_ms))
        if token == "close":
            return True, ("open", None, int(now_ms) + int(osb_flash_ms))
        return True, ("open", str(result), int(now_ms) + int(osb_flash_ms))
    if isinstance(result, dict):
        if result.get("handled", True) is False:
            return False, None
        action = str(result.get("action", "")).strip().lower()
        if action in {"", "none"}:
            submenu = result.get("submenu", result.get("value", None))
            if submenu is None:
                return True, None
            return True, ("open", str(submenu), int(now_ms) + int(osb_flash_ms))
        if action == "back":
            return True, ("back", None, int(now_ms) + int(osb_flash_ms))
        if action == "close":
            return True, ("open", None, int(now_ms) + int(osb_flash_ms))
        if action == "open":
            submenu = result.get("submenu", result.get("value", None))
            return True, ("open", None if submenu is None else str(submenu), int(now_ms) + int(osb_flash_ms))
        return True, None
    return True, None


def pmd_status_menu_zone_key(plugin_id: str, button_id: str, sanitize_pmd_id: Callable[[object], str]) -> str:
    raw_plugin = sanitize_pmd_id(plugin_id)
    raw_button = "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in str(button_id).strip().upper())
    raw_button = raw_button.strip("_")
    if raw_button == "":
        raw_button = "BTN"
    return f"PMD_EXT_{raw_plugin}_{raw_button}"


def pmd_manifest_for_dir(
    plugin_dir: Path,
    manifest_file: str,
    default_entry_file: str,
    safe_read_json: Callable[[Path, Optional[dict]], dict],
) -> Dict[str, object]:
    manifest_path = plugin_dir / manifest_file
    defaults: Dict[str, object] = {
        "name": plugin_dir.name,
        "description": "",
        "creator": "UNKNOWN",
        "url": "",
        "entry": default_entry_file,
        "code": default_entry_file,
        "autoload": False,
        "session_only": False,
    }
    manifest = safe_read_json(manifest_path, defaults)
    entry_raw = str(manifest.get("entry", manifest.get("code", default_entry_file))).strip()
    if entry_raw == "":
        entry_raw = default_entry_file
    manifest["entry"] = entry_raw
    manifest["code"] = entry_raw
    name = str(manifest.get("name", plugin_dir.name)).strip()
    if name == "":
        name = plugin_dir.name
    manifest["name"] = name
    manifest["description"] = str(manifest.get("description", "")).strip()
    creator = str(manifest.get("creator", manifest.get("author", "UNKNOWN"))).strip()
    manifest["creator"] = creator if creator != "" else "UNKNOWN"
    manifest["url"] = str(
        manifest.get("url", manifest.get("author_url", manifest.get("website", "")))
    ).strip()
    manifest["autoload"] = bool(manifest.get("autoload", manifest.get("persistent", False)))
    manifest["session_only"] = bool(manifest.get("session_only", False))
    return manifest


def pmd_deactivate_plugin(
    plugin_id: str,
    *,
    sanitize_pmd_id: Callable[[object], str],
    pmd_plugins: Dict[str, Any],
    pmd_disabled_plugins: Dict[str, Any],
    pmd_build_api: Callable[[Any], Dict[str, object]],
    pmd_remove_runtime_status_menu_buttons: Callable[[Any], None],
    pmd_update_settings_lists: Callable[[], None],
    sync_pmd_ui_cache: Callable[..., None],
    formats_module: Any,
    traceback_module: Any,
    shutil_module: Any,
    remove_files: bool = False,
) -> bool:
    key = sanitize_pmd_id(plugin_id)
    if key == "":
        return False
    runtime = pmd_plugins.pop(key, None)
    was_loaded = runtime is not None
    if runtime is None:
        runtime = pmd_disabled_plugins.pop(key, None)
        if runtime is None:
            return False
    if was_loaded:
        api_obj = runtime.scope.get("PMD_API")
        if not isinstance(api_obj, dict):
            api_obj = pmd_build_api(runtime)
        try:
            if callable(runtime.on_unload):
                runtime.on_unload(api_obj)
        except Exception:
            traceback_module.print_exc()
        pmd_remove_runtime_status_menu_buttons(runtime)
        try:
            reg = getattr(formats_module, "_FORMAT_REGISTRY", {})
            if isinstance(reg, dict):
                for fmt_name in runtime.added_formats:
                    reg.pop(str(fmt_name), None)
                for fmt_name, factory in runtime.format_overrides.items():
                    reg[str(fmt_name)] = factory
            for fmt_name in runtime.added_formats:
                while str(fmt_name) in formats_module.FORMAT_NAMES:
                    formats_module.FORMAT_NAMES.remove(str(fmt_name))
        except Exception:
            pass
    else:
        pmd_remove_runtime_status_menu_buttons(runtime)
    if remove_files:
        try:
            shutil_module.rmtree(runtime.folder, ignore_errors=True)
        except Exception:
            pass
    pmd_update_settings_lists()
    sync_pmd_ui_cache()
    return True


def pmd_disable_plugin(
    plugin_id: str,
    *,
    sanitize_pmd_id: Callable[[object], str],
    pmd_plugins: Dict[str, Any],
    pmd_disabled_plugins: Dict[str, Any],
    pmd_deactivate_plugin_cb: Callable[[str, bool], bool],
    sync_pmd_ui_cache: Callable[..., None],
) -> Tuple[bool, str]:
    key = sanitize_pmd_id(plugin_id)
    if key == "":
        return False, "Invalid PMD ID."
    runtime = pmd_plugins.get(key)
    if runtime is None:
        return False, "PMD is not active."
    runtime.enabled = False
    pmd_disabled_plugins[key] = runtime
    if not pmd_deactivate_plugin_cb(key, False):
        pmd_disabled_plugins.pop(key, None)
        return False, "Unable to disable PMD."
    sync_pmd_ui_cache()
    return True, f"Disabled PMD: {runtime.display_name}"


def pmd_enable_plugin(
    plugin_id: str,
    *,
    sanitize_pmd_id: Callable[[object], str],
    pmd_disabled_plugins: Dict[str, Any],
    pmd_activate_plugin_cb: Callable[[Any, Optional[Any], Optional[bool]], Tuple[bool, str]],
    sync_pmd_ui_cache: Callable[..., None],
) -> Tuple[bool, str]:
    key = sanitize_pmd_id(plugin_id)
    if key == "":
        return False, "Invalid PMD ID."
    runtime = pmd_disabled_plugins.get(key)
    if runtime is None:
        return False, "PMD is already enabled."
    ok, msg = pmd_activate_plugin_cb(
        runtime.folder,
        runtime.archive_path,
        bool(runtime.session_only),
    )
    if ok:
        pmd_disabled_plugins.pop(key, None)
        sync_pmd_ui_cache()
    else:
        pmd_disabled_plugins[key] = runtime
    return ok, msg
