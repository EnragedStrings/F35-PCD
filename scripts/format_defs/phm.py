from formats import *  # noqa: F401,F403


class PhmFormat(FormatBase):
    def __init__(self) -> None:
        self.name = "PHM"
        self._selected_flat_index: Optional[int] = 0
        self._submenu: Optional[str] = None
        self._pending_submenu_action: Optional[Tuple[str, int]] = None
        self._status_page_idx: int = 0
        self._status_prev_rect: Optional[pygame.Rect] = None
        self._status_next_rect: Optional[pygame.Rect] = None
        self._status_selected_sub_idx: int = 0
        self._status_system_name: Optional[str] = None

    @staticmethod
    def _vs_bit_reason_titles() -> List[str]:
        return [
            "VS BIT: ABORT-Pilot",
            "VS BIT: ABORT-HOTAS",
            "VS BIT: ABORT-Engine Off",
            "VS BIT: FAIL-FLCS",
            "VS BIT: FAIL-Fuel",
            "VS BIT: FAIL-FPS",
            "VS BIT: FAIL-HUA",
            "VS BIT: FAIL-LGS",
            "VS BIT: FAIL-Prop",
            "VS BIT: FAIL-PTMS",
            "VS BIT: Ground Interlock",
            "VS BIT: Parking Brake",
            "VS BIT: NWS Out of Range",
            "VS BIT: EHA Temp-HOT",
            "VS BIT: EHA Temp-COLD",
            "VS BIT: Stick Passive",
            "VS BIT: Throttle Passive",
            "VS BIT: No EHA 270V",
            "VS BIT: Fuel-Def Vlv Open",
            "VS BIT: No HYD A-HTCA",
            "VS BIT: No HYD B-NWS",
            "VS BIT: HUA-Timeout",
            "VS BIT: Timeout",
            "VS BIT: HUA Terminate",
            "VS BIT: Pilot Delay",
            "VS BIT: Convert to CTOL",
            "VS BIT: ETR to Idle",
            "VS BIT: In Motion",
            "VS BIT: Parking Brake",
            "VS BIT: Not Available",
        ]

    @staticmethod
    def _is_yellow_status(status: str) -> bool:
        return str(status).upper() in {"HR", "OT", "??", "NC", "OFF", "DEGD", "INOP", "BIT", "SHUTDOWN"}

    @staticmethod
    def _status_color(status: str) -> Tuple[int, int, int]:
        st = str(status).upper().strip()
        if st in {"FAIL", "FN"}:
            return (255, 0, 0)
        if st == "PIN":
            return (0, 255, 255)
        if st == "OF":
            return (128, 128, 128)
        if st == "INIT" or st == "????":
            return (255, 128, 0)
        if st in {"OFF", "DEGD", "HR", "OT", "??", "NC", "INOP", "BIT", "SHUTDOWN"}:
            return (255, 255, 0)
        return (0, 255, 0)

    def _selected_system_name(self) -> str:
        vehicle = self._vehicle_systems()
        mission = self._mission_systems()
        all_rows = vehicle + mission
        if len(all_rows) <= 0:
            return "VSP"
        idx = 0 if self._selected_flat_index is None else int(self._selected_flat_index) % len(all_rows)
        return str(all_rows[idx][0])

    def _status_active_system_name(self) -> str:
        if self._submenu == "STATUS":
            locked = str(self._status_system_name or "").strip()
            if locked != "":
                return locked
        return self._selected_system_name()

    def _status_selected_subsystem_name(self) -> str:
        system_name = self._status_active_system_name()
        vs_bit_status, _catalog = self._vs_bit_runtime_state()
        subsystems = self._subsystems_for_system(system_name, vs_bit_status)
        if len(subsystems) <= 0:
            return ""
        idx = max(0, min(int(self._status_selected_sub_idx), len(subsystems) - 1))
        return str(subsystems[idx][0]).upper().strip()

    @staticmethod
    def _request_phm_status_bit(keys: Iterable[str], duration_ms: int = 10000) -> None:
        panel = PANEL_BUTTON_STATES if isinstance(PANEL_BUTTON_STATES, dict) else {}
        phm = panel.get("PHM STATUS", {}) if isinstance(panel, dict) else {}
        if not isinstance(phm, dict):
            return
        now_ms = int(pygame.time.get_ticks())
        until = now_ms + max(0, int(duration_ms))
        bit_map = phm.get("bit_until_ms", {})
        if not isinstance(bit_map, dict):
            bit_map = {}
            phm["bit_until_ms"] = bit_map
        for key in keys:
            norm = str(key).upper().strip()
            if norm == "":
                continue
            bit_map[norm] = until

    @staticmethod
    def _vs_bit_runtime_state() -> Tuple[str, List[str]]:
        panel = PANEL_BUTTON_STATES.get("THROTTLE", {}) if isinstance(PANEL_BUTTON_STATES, dict) else {}
        if not isinstance(panel, dict):
            return ("OK", [])
        status = str(panel.get("VS_BIT_STATUS", "OK")).upper()
        if status not in {"OK", "TS", "FN"}:
            status = "OK"
        reasons_raw = panel.get("VS_BIT_FAIL_REASONS", panel.get("VS_BIT_REASON_CATALOG", []))
        reasons: List[str] = []
        if isinstance(reasons_raw, list):
            reasons = [str(x) for x in reasons_raw if str(x).strip() != ""]
        if status != "FN":
            reasons = []
        return (status, reasons)

    @staticmethod
    def _phm_debug_panel() -> Dict[str, object]:
        panel = PANEL_BUTTON_STATES if isinstance(PANEL_BUTTON_STATES, dict) else {}
        raw = panel.get("PHM STATUS", {})
        if not isinstance(raw, dict):
            return {}
        return raw

    @staticmethod
    def _phm_debug_status_overrides() -> Dict[str, str]:
        raw = PhmFormat._phm_debug_panel().get("status_overrides", {})
        out: Dict[str, str] = {}
        if isinstance(raw, dict):
            for k, v in raw.items():
                key = str(k).upper().strip()
                val = str(v).upper().strip()
                if key == "" or val == "":
                    continue
                out[key] = val
        return out

    @staticmethod
    def _phm_runtime_system_overrides() -> Dict[str, str]:
        raw = PhmFormat._phm_debug_panel().get("runtime_system_status", {})
        out: Dict[str, str] = {}
        if isinstance(raw, dict):
            for k, v in raw.items():
                key = str(k).upper().strip()
                val = str(v).upper().strip()
                if key == "" or val == "":
                    continue
                out[key] = val
        return out

    @staticmethod
    def _phm_runtime_subsystem_status() -> Dict[str, str]:
        raw = PhmFormat._phm_debug_panel().get("runtime_subsystem_status", {})
        out: Dict[str, str] = {}
        if isinstance(raw, dict):
            for k, v in raw.items():
                key = str(k).upper().strip()
                val = str(v).upper().strip()
                if key == "" or val == "":
                    continue
                out[key] = val
        return out

    @staticmethod
    def _phm_runtime_msstat_blocks() -> Dict[str, List[Tuple[str, str]]]:
        raw = PhmFormat._phm_debug_panel().get("msstat_blocks", {})
        out: Dict[str, List[Tuple[str, str]]] = {}
        if not isinstance(raw, dict):
            return out
        for block_name, rows_raw in raw.items():
            block_key = str(block_name).upper().strip()
            if block_key == "" or not isinstance(rows_raw, list):
                continue
            rows: List[Tuple[str, str]] = []
            for row in rows_raw:
                if not isinstance(row, (tuple, list)) or len(row) < 2:
                    continue
                left = str(row[0]).strip()
                right = str(row[1]).strip().upper()
                if left == "":
                    continue
                rows.append((left, right))
            out[block_key] = rows
        return out

    @staticmethod
    def _phm_debug_reasons_for_keys(keys: Iterable[str]) -> List[str]:
        ordered_keys: List[str] = []
        for key in keys:
            norm = str(key).upper().strip()
            if norm == "" or norm in ordered_keys:
                continue
            ordered_keys.append(norm)
        if len(ordered_keys) <= 0:
            return []
        panel = PhmFormat._phm_debug_panel()
        hrc_map = panel.get("hrc_events", {})
        fna_map = panel.get("fna_events", {})
        reasons: List[str] = []
        for key in ordered_keys:
            if isinstance(hrc_map, dict):
                vals = hrc_map.get(key, [])
                if isinstance(vals, list):
                    reasons.extend(str(x) for x in vals if str(x).strip() != "")
            if isinstance(fna_map, dict):
                vals = fna_map.get(key, [])
                if isinstance(vals, list):
                    reasons.extend(str(x) for x in vals if str(x).strip() != "")
        return list(dict.fromkeys(reasons))

    @staticmethod
    def _phm_debug_reasons_for_system(system_name: str) -> List[str]:
        return PhmFormat._phm_debug_reasons_for_keys([system_name])

    @staticmethod
    def _phm_debug_status_for_key(key: str) -> str:
        norm = str(key).upper().strip()
        if norm == "":
            return "OK"
        panel = PhmFormat._phm_debug_panel()
        hrc_map = panel.get("hrc_events", {})
        fna_map = panel.get("fna_events", {})
        has_fna = False
        has_hrc = False
        if isinstance(fna_map, dict):
            vals = fna_map.get(norm, [])
            if isinstance(vals, list):
                has_fna = any(str(x).strip() != "" for x in vals)
        if isinstance(hrc_map, dict):
            vals = hrc_map.get(norm, [])
            if isinstance(vals, list):
                has_hrc = any(str(x).strip() != "" for x in vals)
        if has_fna:
            return "OT"
        if has_hrc:
            return "HR"
        return "OK"

    def _status_reason_catalog_for_selected(
        self,
        system_name: Optional[str] = None,
        subsystem_name: Optional[str] = None,
    ) -> List[str]:
        selected = str(system_name or self._status_active_system_name()).upper()
        selected_subsystem = str(subsystem_name or "").upper().strip()
        reason_keys: List[str] = []
        if selected_subsystem != "" and selected_subsystem != selected:
            reason_keys.append(selected_subsystem)
        reason_keys.append(selected)
        reasons = self._phm_debug_reasons_for_keys(reason_keys)
        if selected == "VSP" and selected_subsystem in {"", "VMC"}:
            _status, catalog = self._vs_bit_runtime_state()
            reasons = list(catalog) + reasons
        return list(dict.fromkeys(reasons))

    @staticmethod
    def _format_fna_reason(reason: str) -> str:
        text = str(reason).strip()
        if text.upper().startswith("VS BIT:"):
            return text.split(":", 1)[1].strip()
        return text

    @staticmethod
    def _vehicle_systems() -> List[Tuple[str, str]]:
        throttle = PANEL_BUTTON_STATES.get("THROTTLE", {}) if isinstance(PANEL_BUTTON_STATES, dict) else {}
        vsp_status = "OK"
        if isinstance(throttle, dict):
            vs_bit_status = str(throttle.get("VS_BIT_STATUS", "OK")).upper()
            if vs_bit_status == "TS" or bool(throttle.get("VS_BIT_RUNNING", False)):
                vsp_status = "TS"
            elif vs_bit_status == "FN" or bool(throttle.get("VS_BIT_NO_GO", False)):
                vsp_status = "OT"
        rows = [
            ("AIR_FRM", "OK"),
            ("PROP", "OK"),
            ("EPS", "OK"),
            ("FCS", "OK"),
            ("FPS", "OK"),
            ("FUEL", "OK"),
            ("GEAR", "OK"),
            ("HYD", "OK"),
            ("LIF_SUP", "OK"),
            ("PTMS", "OK"),
            ("VSP", vsp_status),
        ]
        runtime = PhmFormat._phm_runtime_system_overrides()
        debug_overrides = PhmFormat._phm_debug_status_overrides()
        out: List[Tuple[str, str]] = []
        for name, status in rows:
            key = str(name).upper()
            merged = str(runtime.get(key, status)).upper().strip() or str(status).upper().strip()
            merged = str(debug_overrides.get(key, merged)).upper().strip() or merged
            out.append((name, merged))
        return out

    @staticmethod
    def _mission_systems() -> List[Tuple[str, str]]:
        rows = [
            ("COM_NAV", "OK"),
            ("DAS", "OK"),
            ("DISPL", "OK"),
            ("EW", "OK"),
            ("GUN", "OK"),
            ("EOTS", "OK"),
            ("MSP", "OK"),
            ("RADAR", "OK"),
            ("RIUs", "OK"),
            ("SRES", "OK"),
            ("LIGHTG", "OK"),
        ]
        runtime = PhmFormat._phm_runtime_system_overrides()
        debug_overrides = PhmFormat._phm_debug_status_overrides()
        out: List[Tuple[str, str]] = []
        for name, status in rows:
            key = str(name).upper()
            merged = str(runtime.get(key, status)).upper().strip() or str(status).upper().strip()
            merged = str(debug_overrides.get(key, merged)).upper().strip() or merged
            out.append((name, merged))
        return out

    @staticmethod
    def _subsystems_for_system(system_name: str, vs_bit_status: str) -> List[Tuple[str, str]]:
        key = str(system_name).upper().strip()
        default_status = "OK"
        subs = PHM_SYSTEM_SUBSYSTEMS.get(key, [])
        runtime_sub_status = PhmFormat._phm_runtime_subsystem_status()
        system_debug_status = PhmFormat._phm_debug_status_for_key(key)
        if key == "VSP":
            target_subsystem = "VMC"
            has_target = any(str(sub).upper().strip() == target_subsystem for sub in subs)
            rows: List[Tuple[str, str]] = []
            for idx, sub in enumerate(subs):
                sub_key = str(sub).upper().strip()
                row_status = str(runtime_sub_status.get(sub_key, default_status)).upper().strip() or default_status
                sub_debug_status = PhmFormat._phm_debug_status_for_key(sub)
                if sub_debug_status != "OK":
                    row_status = sub_debug_status
                elif system_debug_status != "OK":
                    row_status = system_debug_status
                apply_vs_bit_status = sub_key == target_subsystem
                if not has_target and idx == 0:
                    apply_vs_bit_status = True
                if apply_vs_bit_status:
                    if row_status == "OK":
                        row_status = str(vs_bit_status).upper().strip() or default_status
                    rows.append((sub, row_status))
                else:
                    rows.append((sub, row_status))
            return rows
        rows = []
        for sub in subs:
            sub_key = str(sub).upper().strip()
            row_status = str(runtime_sub_status.get(sub_key, default_status)).upper().strip() or default_status
            sub_debug_status = PhmFormat._phm_debug_status_for_key(sub)
            if sub_debug_status != "OK":
                row_status = sub_debug_status
            elif system_debug_status != "OK":
                row_status = system_debug_status
            rows.append((sub, row_status))
        return rows

    def _osb_box(self, rect: pygame.Rect, label: str) -> Optional[pygame.Rect]:
        if len(label) < 2:
            return None
        side = label[0]
        try:
            idx = int(label[1:])
        except Exception:
            return None
        top_count = 5 if rect.width < int(10 * DPI) else 10
        side_count = 6 if rect.height >= int(7 * DPI) - 1 else 5
        top_offset = DISPLAY_OSB_H if top_count > 0 else 0
        if side == "T":
            if idx < 1 or idx > top_count:
                return None
            return pygame.Rect(rect.x + (idx - 1) * GRID_CELL_W, rect.y, GRID_CELL_W, DISPLAY_OSB_H)
        if side == "L":
            if idx < 1 or idx > side_count:
                return None
            return pygame.Rect(rect.x, rect.y + top_offset + (idx - 1) * DISPLAY_OSB_H, GRID_CELL_W, DISPLAY_OSB_H)
        if side == "R":
            if idx < 1 or idx > side_count:
                return None
            return pygame.Rect(rect.right - GRID_CELL_W, rect.y + top_offset + (idx - 1) * DISPLAY_OSB_H, GRID_CELL_W, DISPLAY_OSB_H)
        return None

    def _draw_osbs(self, surface: pygame.Surface, rect: pygame.Rect, context: FormatContext) -> None:
        cyan = (0, 255, 255)
        white = (255, 255, 255)
        gray = (128, 128, 128)
        top_count = 5 if rect.width < int(10 * DPI) else 10
        side_count = 6 if rect.height >= int(7 * DPI) - 1 else 5
        top_offset = DISPLAY_OSB_H if top_count > 0 else 0

        # L1/L2 INC/DEC triangles.
        if side_count >= 2:
            l1_box = pygame.Rect(rect.x, rect.y + top_offset + (1 - 1) * DISPLAY_OSB_H, GRID_CELL_W, DISPLAY_OSB_H)
            l2_box = pygame.Rect(rect.x, rect.y + top_offset + (2 - 1) * DISPLAY_OSB_H, GRID_CELL_W, DISPLAY_OSB_H)
            tri_w = max(10, l1_box.width // 3)
            tri_h = max(10, l1_box.height // 3)
            l1_flash = bool(context.is_osb_flashing("L1"))
            l2_flash = bool(context.is_osb_flashing("L2"))
            tri_col_l1 = white if l1_flash else cyan
            tri_col_l2 = white if l2_flash else cyan
            # INC (up)
            cx = l1_box.left + OSB_PADDING + tri_w // 2 + 2
            cy = l1_box.centery
            up_points = [(cx, cy - tri_h // 2), (cx - tri_w // 2, cy + tri_h // 2), (cx + tri_w // 2, cy + tri_h // 2)]
            pygame.draw.polygon(surface, tri_col_l1, up_points, 0)
            # DEC (down)
            cx = l2_box.left + OSB_PADDING + tri_w // 2 + 2
            cy = l2_box.centery
            dn_points = [(cx, cy + tri_h // 2), (cx - tri_w // 2, cy - tri_h // 2), (cx + tri_w // 2, cy - tri_h // 2)]
            pygame.draw.polygon(surface, tri_col_l2, dn_points, 0)

        osbs: List[Tuple[str, ButtonState]] = [
            (
                "T2",
                ButtonState(
                    button_id="PHM_T2",
                    button_type=ButtonType.PAGE_ACCESS,
                    text="STATUS>",
                    h_align="center",
                    v_align="top",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("T2") else 0,
                ),
            ),
            (
                "R3",
                ButtonState(
                    button_id="PHM_R3",
                    button_type=ButtonType.PAGE_ACCESS,
                    text="SVC>",
                    h_align="right",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("R3") else 0,
                ),
            ),
            (
                "R4",
                ButtonState(
                    button_id="PHM_R4",
                    button_type=ButtonType.PAGE_ACCESS,
                    text="NTWRK>",
                    h_align="right",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("R4") else 0,
                ),
            ),
            (
                "R5",
                ButtonState(
                    button_id="PHM_R5",
                    button_type=ButtonType.PAGE_ACCESS,
                    text="MSSTAT>",
                    h_align="right",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("R5") else 0,
                ),
            ),
        ]
        for label, state in osbs:
            box = self._osb_box(rect, label)
            if box is None:
                continue
            render_button(surface, box, state, get_font, 0)

        l3_box = self._osb_box(rect, "L3")
        if l3_box is not None:
            render_button(
                surface,
                l3_box,
                ButtonState(
                    button_id="PHM_L3_DLVHF",
                    button_type=ButtonType.GOL,
                    function_label="DL",
                    options=["VHF U"],
                    selected_index=0,
                    h_align="left",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("L3") else 0,
                ),
                get_font,
                0,
            )
        t3_box = self._osb_box(rect, "T3")
        if t3_box is not None:
            render_button(
                surface,
                t3_box,
                ButtonState(
                    button_id="PHM_T3_HIST",
                    button_type=ButtonType.MOMENTARY_SINGLE,
                    text="HIST",
                    is_single_function=True,
                    is_on=True,
                    h_align="center",
                    v_align="top",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("T3") else 0,
                ),
                get_font,
                0,
            )
        l5_box = self._osb_box(rect, "L5")
        if l5_box is not None:
            render_button(
                surface,
                l5_box,
                ButtonState(
                    button_id="PHM_L5_XMIT_REPORT",
                    button_type=ButtonType.PAGE_ACCESS,
                    text="XMIT\nREPORT",
                    enabled=False,
                    h_align="left",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("L5") else 0,
                ),
                get_font,
                0,
            )

    def _draw_status_osbs(self, surface: pygame.Surface, rect: pygame.Rect, context: FormatContext) -> None:
        cyan = (0, 255, 255)
        white = (255, 255, 255)
        top_count = 5 if rect.width < int(10 * DPI) else 10
        side_count = 6 if rect.height >= int(7 * DPI) - 1 else 5
        top_offset = DISPLAY_OSB_H if top_count > 0 else 0

        # L1/L2 INC/DEC.
        if side_count >= 2:
            l1_box = pygame.Rect(rect.x, rect.y + top_offset + (1 - 1) * DISPLAY_OSB_H, GRID_CELL_W, DISPLAY_OSB_H)
            l2_box = pygame.Rect(rect.x, rect.y + top_offset + (2 - 1) * DISPLAY_OSB_H, GRID_CELL_W, DISPLAY_OSB_H)
            tri_w = max(10, l1_box.width // 3)
            tri_h = max(10, l1_box.height // 3)
            l1_flash = bool(context.is_osb_flashing("L1"))
            l2_flash = bool(context.is_osb_flashing("L2"))
            tri_col_l1 = white if l1_flash else cyan
            tri_col_l2 = white if l2_flash else cyan
            cx = l1_box.left + OSB_PADDING + tri_w // 2 + 2
            cy = l1_box.centery
            up_points = [(cx, cy - tri_h // 2), (cx - tri_w // 2, cy + tri_h // 2), (cx + tri_w // 2, cy + tri_h // 2)]
            pygame.draw.polygon(surface, tri_col_l1, up_points, 0)
            cx = l2_box.left + OSB_PADDING + tri_w // 2 + 2
            cy = l2_box.centery
            dn_points = [(cx, cy + tri_h // 2), (cx - tri_w // 2, cy - tri_h // 2), (cx + tri_w // 2, cy - tri_h // 2)]
            pygame.draw.polygon(surface, tri_col_l2, dn_points, 0)

        def draw_btn(label: str, state: ButtonState) -> None:
            box = self._osb_box(rect, label)
            if box is None:
                return
            render_button(surface, box, state, get_font, 0)

        draw_btn(
            "T3",
            ButtonState(
                button_id="PHM_STATUS_T3",
                button_type=ButtonType.MOMENTARY_SINGLE,
                text="HIST",
                is_single_function=True,
                is_on=True,
                h_align="center",
                v_align="top",
                padding=OSB_PADDING,
                font_size=14,
                flash_until_ms=1 if context.is_osb_flashing("T3") else 0,
            ),
        )
        draw_btn(
            "R1",
            ButtonState(
                button_id="PHM_STATUS_R1",
                button_type=ButtonType.PAGE_ACCESS,
                text="SVC>",
                h_align="right",
                v_align="center",
                padding=OSB_PADDING,
                font_size=14,
                flash_until_ms=1 if context.is_osb_flashing("R1") else 0,
            ),
        )
        draw_btn(
            "R2",
            ButtonState(
                button_id="PHM_STATUS_R2",
                button_type=ButtonType.MOMENTARY_SINGLE,
                text="BIT",
                h_align="right",
                v_align="center",
                padding=OSB_PADDING,
                font_size=14,
                flash_until_ms=1 if context.is_osb_flashing("R2") else 0,
            ),
        )

    def _draw_msstat_osbs(self, surface: pygame.Surface, rect: pygame.Rect, context: FormatContext) -> None:
        # Intentionally no L1/L2, T3, R1, R2 labels on MSSTAT per spec.
        return

    def _draw_status_body(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        self._status_prev_rect = None
        self._status_next_rect = None

        green = (0, 255, 0)
        cyan = (0, 255, 255)
        yellow = (255, 255, 0)
        gray = (128, 128, 128)
        white = (255, 255, 255)

        top_count = 5 if rect.width < int(10 * DPI) else 10
        top_offset = DISPLAY_OSB_H if top_count > 0 else 0
        y_top = rect.y + top_offset
        header_y = y_top + 4
        center_x = rect.centerx

        left_x = rect.x + GRID_CELL_W + 16
        right_x = rect.right - GRID_CELL_W - 16

        selected_system = self._status_active_system_name()
        vs_bit_status, _catalog = self._vs_bit_runtime_state()

        header_font = get_font(15)
        body_font = get_font(14)
        fna_font = get_font(13)

        system_hdr = header_font.render(selected_system, True, green)
        system_hdr_rect = system_hdr.get_rect(centerx=center_x, y=header_y)
        surface.blit(system_hdr, system_hdr_rect)
        pygame.draw.line(
            surface,
            green,
            (system_hdr_rect.left, system_hdr_rect.bottom + 1),
            (system_hdr_rect.right, system_hdr_rect.bottom + 1),
            1,
        )

        cols_y = system_hdr_rect.bottom + 10
        col_system = body_font.render("SYSTEM", True, green)
        col_stat = body_font.render("STAT", True, green)
        col_offset = max(70, rect.width // 8)
        system_col_center = center_x - col_offset
        stat_col_center = center_x + col_offset
        system_col_rect = col_system.get_rect(centerx=system_col_center, y=cols_y)
        stat_col_rect = col_stat.get_rect(centerx=stat_col_center, y=cols_y)
        surface.blit(col_system, system_col_rect)
        surface.blit(col_stat, stat_col_rect)
        pygame.draw.line(
            surface,
            green,
            (system_col_rect.left, system_col_rect.bottom + 1),
            (system_col_rect.right, system_col_rect.bottom + 1),
            1,
        )
        pygame.draw.line(
            surface,
            green,
            (stat_col_rect.left, stat_col_rect.bottom + 1),
            (stat_col_rect.right, stat_col_rect.bottom + 1),
            1,
        )

        row_top = cols_y + col_system.get_height() + 8
        row_bottom = row_top
        subsystems = self._subsystems_for_system(selected_system, vs_bit_status)
        if len(subsystems) <= 0:
            self._status_selected_sub_idx = 0
        else:
            self._status_selected_sub_idx = max(0, min(int(self._status_selected_sub_idx), len(subsystems) - 1))
        max_subsystem_bottom = (rect.y + (8 * GRID_CELL_H)) - int(2 * DPI) - 6
        sub_row_h = body_font.get_height() + 2
        sel_marker_surf = body_font.render("*", True, white)
        y = row_top
        for idx, (subsystem_name, subsystem_status) in enumerate(subsystems):
            if y + body_font.get_height() > max_subsystem_bottom:
                break
            stat_text = str(subsystem_status).upper().strip()
            row_color = self._status_color(stat_text)
            row_sys_s = body_font.render(str(subsystem_name), True, row_color)
            row_sys_r = row_sys_s.get_rect(centerx=system_col_center, y=y)
            surface.blit(row_sys_s, row_sys_r)
            if idx == int(self._status_selected_sub_idx):
                marker_rect = sel_marker_surf.get_rect(right=row_sys_r.left - 6, y=row_sys_r.y)
                surface.blit(sel_marker_surf, marker_rect)
            if stat_text != "":
                row_stat_s = body_font.render(stat_text, True, row_color)
                row_stat_r = row_stat_s.get_rect(centerx=stat_col_center, y=y)
                surface.blit(row_stat_s, row_stat_r)
                row_bottom = max(row_bottom, row_sys_r.bottom, row_stat_r.bottom)
            else:
                row_bottom = max(row_bottom, row_sys_r.bottom)
            y += sub_row_h

        # Anchor FnA window to the 5x7 frame even when current portal is 5x5/10x5.
        full_bottom = rect.y + (8 * GRID_CELL_H)
        fna_top = full_bottom - int(2 * DPI)
        fna_top = max(fna_top, row_bottom + 8)
        # Move the lower status section down by one rendered text line.
        line_h = fna_font.get_height() + 2
        fna_top += line_h
        fna_bottom = full_bottom - 6
        if fna_bottom <= fna_top:
            return
        fna_rect = pygame.Rect(left_x, fna_top, max(1, right_x - left_x), fna_bottom - fna_top)

        selected_subsystem_name = ""
        if len(subsystems) > 0:
            selected_subsystem_name = str(subsystems[int(self._status_selected_sub_idx)][0])
        reasons = [
            self._format_fna_reason(r)
            for r in self._status_reason_catalog_for_selected(selected_system, selected_subsystem_name)
        ]
        page_size = 5
        total_pages = max(1, int(math.ceil(len(reasons) / float(page_size)))) if len(reasons) > 0 else 1
        self._status_page_idx = max(0, min(self._status_page_idx, total_pages - 1))
        page_no = self._status_page_idx + 1
        page_text = f"{page_no:02d}/{total_pages:02d}"
        page_s = body_font.render(page_text, True, green)
        page_r = page_s.get_rect(x=rect.left + 6, y=fna_rect.top + 2)
        surface.blit(page_s, page_r)

        start = self._status_page_idx * page_size
        end = start + page_size
        page_reasons = reasons[start:end]
        lines_top = page_r.bottom + 6
        for idx, reason in enumerate(page_reasons):
            y = lines_top + idx * line_h
            line_s = fna_font.render(str(reason), True, yellow)
            line_r = line_s.get_rect(centerx=center_x, y=y)
            surface.blit(line_s, line_r)

        btn_y = lines_top + line_h
        can_prev = self._status_page_idx > 0
        can_next = self._status_page_idx < (total_pages - 1)
        prev_col = cyan if can_prev else gray
        next_col = cyan if can_next else gray
        prev_s = body_font.render("PREV", True, prev_col)
        next_s = body_font.render("NEXT", True, next_col)
        prev_r = prev_s.get_rect(x=rect.left + 6, centery=btn_y)
        next_r = next_s.get_rect(right=rect.right - 6, centery=btn_y)
        if can_prev:
            self._status_prev_rect = prev_r.inflate(8, 4)
        if can_next:
            self._status_next_rect = next_r.inflate(8, 4)
        surface.blit(prev_s, prev_r)
        surface.blit(next_s, next_r)

    def _draw_msstat_body(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        self._status_prev_rect = None
        self._status_next_rect = None

        green = (0, 255, 0)
        yellow = (255, 255, 0)

        top_count = 5 if rect.width < int(10 * DPI) else 10
        top_offset = DISPLAY_OSB_H if top_count > 0 else 0
        y_top = rect.y + top_offset
        full_bottom = rect.y + (8 * GRID_CELL_H)
        bottom_limit = full_bottom - 6

        header_font = get_font(15)
        body_font = get_font(13)
        row_h = body_font.get_height() + 1

        col1_x = rect.x + (rect.width // 4)
        col2_x = rect.x + ((3 * rect.width) // 4)

        runtime_blocks = self._phm_runtime_msstat_blocks()
        rows_28v: List[Tuple[str, str]] = runtime_blocks.get("28V", [])
        rows_270v: List[Tuple[str, str]] = runtime_blocks.get("270V", [])
        rows_icp_a: List[Tuple[str, str]] = runtime_blocks.get("ICP-A", [])
        rows_icp_b: List[Tuple[str, str]] = runtime_blocks.get("ICP-B", [])

        if len(rows_28v) <= 0:
            rows_28v = [
                ("ACE", "OK"),
                ("AMD", "OK"),
                ("DMCH-DP", "????"),
                ("DMCH-SP", "OK"),
                ("DMCL", "OK"),
                ("DMCR", "OK"),
                ("PMD", "OK"),
            ]
        if len(rows_270v) <= 0:
            rows_270v = [
                ("CNI-A", "OK"),
                ("CNI-B", "OK"),
                ("CM", "INIT"),
                ("DAS", "OK"),
                ("EOTS", "OK"),
                ("EW", "OK"),
                ("P5-CTS", "OK"),
                ("RADAR", "STBY"),
            ]
        if len(rows_icp_a) <= 0:
            rows_icp_a = [
                ("DSA1A", "PIN"),
                ("DSA1B", "PIN"),
                ("GPA1A1", "OK"),
                ("GPA1A2", "OK"),
                ("GPA1B1", "OK"),
                ("GPA1B2", "OK"),
                ("GPA2A1", "OK"),
                ("GPA2A2", "OK"),
                ("GPA2B1", "OK"),
                ("GPA 2B2", "OK"),
                ("GPIOA1", "OK"),
                ("GPIOA2", "OK"),
            ]
        if len(rows_icp_b) <= 0:
            rows_icp_b = [
                ("DSB1A", "PIN"),
                ("DSB1B", "PIN"),
                ("GPA1A1", "OK"),
                ("GPA1A2", "OK"),
                ("GPA1B1", "OK"),
                ("GPA1B2", "OK"),
                ("GPIOB1", "OK"),
                ("GPIOB2", "OK"),
            ]

        def draw_block(center_x: int, label: str, label_y: int, rows: List[Tuple[str, str]]) -> int:
            max_sys_w = max(body_font.size(str(sys_name))[0] for sys_name, _ in rows) if len(rows) > 0 else 0
            max_stat_w = max(body_font.size(str(stat_text))[0] for _, stat_text in rows) if len(rows) > 0 else 0
            gap = max(14, body_font.size("  ")[0] * 2)
            block_w = max_sys_w + gap + max_stat_w if len(rows) > 0 else 0
            sys_x = int(center_x - (block_w / 2.0)) if len(rows) > 0 else center_x
            stat_x = sys_x + max_sys_w + gap if len(rows) > 0 else center_x

            label_s = header_font.render(label, True, green)
            label_r = label_s.get_rect(centerx=center_x, y=label_y)
            surface.blit(label_s, label_r)
            underline_left = sys_x if len(rows) > 0 else label_r.left
            underline_right = (stat_x + max_stat_w) if len(rows) > 0 else label_r.right
            pygame.draw.line(
                surface,
                green,
                (underline_left, label_r.bottom + 1),
                (underline_right, label_r.bottom + 1),
                1,
            )

            if len(rows) <= 0:
                return label_r.bottom
            rows_top = label_r.bottom + 6
            last_bottom = label_r.bottom
            for idx, (sys_name, stat_text) in enumerate(rows):
                y = rows_top + idx * row_h
                if y + body_font.get_height() > bottom_limit:
                    break
                stat = str(stat_text).upper().strip()
                status_colors = {
                    "????": (255, 128, 0),
                    "PIN": (0, 255, 255),
                    "INIT": (255, 128, 0),
                    "STBY": (0, 255, 0),
                    "OK": (0, 255, 0),
                    "OFF": (255, 255, 0),
                    "OF": (128, 128, 128),
                    "DEGD": (255, 255, 0),
                    "INOP": (255, 255, 0),
                    "SHUTDOWN": (255, 255, 0),
                    "BIT": (255, 255, 0),
                    "OT": (255, 255, 0),
                    "FAIL": (255, 0, 0),
                    "FN": (255, 0, 0),
                }
                status_color = status_colors.get(stat, green)
                system_color = status_color
                if label == "ICP-A" and str(sys_name).upper().strip() == "GPA1A1":
                    system_color = (255, 128, 0)
                sys_s = body_font.render(str(sys_name), True, system_color)
                stat_s = body_font.render(stat, True, status_color)
                sys_r = sys_s.get_rect(x=sys_x, y=y)
                stat_r = stat_s.get_rect(x=stat_x, y=y)
                surface.blit(sys_s, sys_r)
                surface.blit(stat_s, stat_r)
                last_bottom = max(last_bottom, sys_r.bottom, stat_r.bottom)
            return last_bottom

        top_label_y = y_top + 2
        top_left_bottom = draw_block(col1_x, "28V", top_label_y, rows_28v)
        top_right_bottom = draw_block(col2_x, "270V", top_label_y, rows_270v)

        # Bottom-align the ICP lists while allowing different row counts.
        top_pair_bottom = max(top_left_bottom, top_right_bottom)
        icp_a_rows_top = bottom_limit - (len(rows_icp_a) * row_h)
        icp_b_rows_top = bottom_limit - (len(rows_icp_b) * row_h)
        min_label_y = top_pair_bottom + 6
        icp_a_label_y = max(min_label_y, icp_a_rows_top - header_font.get_height() - 4) - 100
        icp_b_label_y = max(min_label_y, icp_b_rows_top - header_font.get_height() - 4) - 100

        draw_block(col1_x, "ICP-A", icp_a_label_y, rows_icp_a)
        draw_block(col2_x, "ICP-B", icp_b_label_y, rows_icp_b)

    def render(self, surface, rect, is_primary: bool, context: FormatContext) -> None:
        if self._pending_submenu_action is not None:
            action, due_ms = self._pending_submenu_action
            if pygame.time.get_ticks() >= int(due_ms):
                if action == "open_svc":
                    self._submenu = "SVC"
                elif action == "close_svc":
                    self._submenu = None
                elif action == "open_status":
                    self._submenu = "STATUS"
                    self._status_page_idx = 0
                    self._status_selected_sub_idx = 0
                    self._status_system_name = self._selected_system_name()
                elif action == "open_msstat":
                    self._submenu = "MSSTAT"
                    self._status_page_idx = 0
                    self._status_selected_sub_idx = 0
                    self._status_system_name = self._selected_system_name()
                elif action == "close_status":
                    self._submenu = None
                    self._status_selected_sub_idx = 0
                    self._status_system_name = None
                self._pending_submenu_action = None
        prev_clip = surface.get_clip()
        clip_rect = rect
        if is_primary and self._submenu in {"STATUS", "MSSTAT"}:
            clip_rect = pygame.Rect(rect.x, rect.y, rect.width, max(rect.height, 8 * GRID_CELL_H))
        surface.set_clip(clip_rect)
        pygame.draw.rect(surface, (0, 255, 255), rect, 1)

        if not is_primary:
            bottom_font = get_font(18)
            bottom = bottom_font.render("PHM", True, (0, 255, 255))
            bottom_rect = bottom.get_rect(centerx=rect.centerx)
            bottom_rect.bottom = rect.bottom - 2
            surface.blit(bottom, bottom_rect)
            surface.set_clip(prev_clip)
            return

        if self._submenu == "STATUS":
            self._draw_status_osbs(surface, rect, context)
        elif self._submenu == "MSSTAT":
            self._draw_msstat_osbs(surface, rect, context)
        elif self._submenu != "SVC":
            self._draw_osbs(surface, rect, context)
        else:
            self._status_prev_rect = None
            self._status_next_rect = None

        top_count = 5 if rect.width < int(10 * DPI) else 10
        top_offset = DISPLAY_OSB_H if top_count > 0 else 0
        y_top = rect.y + top_offset
        y_bottom = y_top + int(4.5 * GRID_CELL_H)
        center_x = rect.centerx
        gray = (128, 128, 128)

        green = (0, 255, 0)
        yellow = (255, 255, 0)

        header_font = get_font(15)
        header_y = y_top + 4

        if self._submenu == "SVC":
            level_h = header_font.render("LEVEL", True, green)
            level_rect = level_h.get_rect(centerx=center_x, y=header_y)
            surface.blit(level_h, level_rect)
            pygame.draw.line(surface, green, (level_rect.left, level_rect.bottom + 1), (level_rect.right, level_rect.bottom + 1), 1)
            bos_psi = float(SVC_DEBUG_STATE.get("bos_psi", 2083.0))
            eng_oil_qts = float(SVC_DEBUG_STATE.get("eng_oil_qts", 12.0))
            hyd_a_qts = float(SVC_DEBUG_STATE.get("hyd_a_qts", float(ENGINE_MID_VALUES.get("HYDA", 5))))
            hyd_b_qts = float(SVC_DEBUG_STATE.get("hyd_b_qts", float(ENGINE_MID_VALUES.get("HYDB", 7))))
            svc_rows: List[Tuple[str, str]] = [
                (f"{int(round(bos_psi))} PSI", "BOS PSI"),
                ("79%", "LIQUID COOL"),
                (f"{hyd_a_qts:.1f} QTS", "HYD A"),
                (f"{hyd_b_qts:.1f} QTS", "HYD B"),
                (f"{eng_oil_qts:.1f} QTS", "ENG OIL"),
                ("OK", "GEN OIL"),
                ("OK", "IPP OIL"),
            ]
            body_font = get_font(14)
            row_h = body_font.get_height() + 7
            list_y = header_y + level_h.get_height() + 8
            values_x = center_x
            labels_x = center_x - 140
            for idx, (value, label) in enumerate(svc_rows):
                y = list_y + idx * row_h
                val_s = body_font.render(value, True, green)
                lab_s = body_font.render(label, True, green)
                val_r = val_s.get_rect(centerx=values_x, y=y)
                lab_r = lab_s.get_rect(x=labels_x, y=y)
                surface.blit(val_s, val_r)
                surface.blit(lab_s, lab_r)
        elif self._submenu == "STATUS":
            self._draw_status_body(surface, rect)
        elif self._submenu == "MSSTAT":
            self._draw_msstat_body(surface, rect)
        else:
            left_header = "VEHCL SYSTMS"
            right_header = "MSSN SYSTMS"
            pygame.draw.line(surface, gray, (center_x, y_top), (center_x, y_bottom), 1)
            left_h = header_font.render(left_header, True, green)
            right_h = header_font.render(right_header, True, green)

            # Keep list columns stable across 5x5 / 5x7 / 10x7 by anchoring to center.
            left_pad = center_x - 145
            right_pad = center_x + 25
            surface.blit(left_h, (left_pad, header_y))
            surface.blit(right_h, (right_pad, header_y))
            pygame.draw.line(
                surface,
                green,
                (left_pad, header_y + left_h.get_height() + 1),
                (left_pad + left_h.get_width(), header_y + left_h.get_height() + 1),
                1,
            )
            pygame.draw.line(
                surface,
                green,
                (right_pad, header_y + right_h.get_height() + 1),
                (right_pad + right_h.get_width(), header_y + right_h.get_height() + 1),
                1,
            )

            vehicle = self._vehicle_systems()
            mission = self._mission_systems()
            total_items = len(vehicle) + len(mission)
            if total_items <= 0:
                self._selected_flat_index = None
            elif self._selected_flat_index is None:
                self._selected_flat_index = 0
            else:
                self._selected_flat_index = int(self._selected_flat_index) % total_items

            body_font = get_font(14)
            list_y = header_y + left_h.get_height() + 6
            max_rows = max(len(vehicle), len(mission), 1)
            available_h = max(1, (y_bottom - 4) - list_y)
            row_h = max(1, available_h // max_rows)
            sel_marker_surf = body_font.render("*", True, (255, 255, 255))

            left_label_x = left_pad
            left_status_x = center_x - 60
            for idx, (name, status) in enumerate(vehicle):
                y = list_y + idx * row_h
                status_color = self._status_color(status)
                name_color = status_color
                if str(status).upper().strip() == "INIT":
                    # Base PHM page uses yellow INIT (MSSTAT keeps orange).
                    status_color = (255, 255, 0)
                    name_color = status_color
                name_surf = body_font.render(name, True, name_color)
                status_surf = body_font.render(status, True, status_color)
                surface.blit(name_surf, (left_label_x, y))
                surface.blit(status_surf, (left_status_x, y))
                if self._selected_flat_index == idx:
                    marker_rect = sel_marker_surf.get_rect(
                        right=left_label_x - 6,
                        y=y,
                    )
                    surface.blit(sel_marker_surf, marker_rect)

            right_label_x = right_pad
            right_status_x = center_x + 105
            for idx, (name, status) in enumerate(mission):
                y = list_y + idx * row_h
                status_color = self._status_color(status)
                name_color = status_color
                if str(status).upper().strip() == "INIT":
                    # Base PHM page uses yellow INIT (MSSTAT keeps orange).
                    status_color = (255, 255, 0)
                    name_color = status_color
                name_surf = body_font.render(name, True, name_color)
                status_surf = body_font.render(status, True, status_color)
                surface.blit(name_surf, (right_label_x, y))
                surface.blit(status_surf, (right_status_x, y))
                if self._selected_flat_index == len(vehicle) + idx:
                    marker_rect = sel_marker_surf.get_rect(
                        right=right_label_x - 6,
                        y=y,
                    )
                    surface.blit(sel_marker_surf, marker_rect)

        surface.set_clip(prev_clip)

    def on_click(self, pos: Tuple[int, int], rect: pygame.Rect, context: FormatContext) -> bool:
        if self._submenu != "STATUS":
            return False
        if self._status_prev_rect is not None and self._status_prev_rect.collidepoint(pos):
            self._status_page_idx = max(0, self._status_page_idx - 1)
            return True
        if self._status_next_rect is not None and self._status_next_rect.collidepoint(pos):
            self._status_page_idx += 1
            return True
        return False

    def on_osb(self, label: str, context: FormatContext) -> bool:
        if label == "T1":
            if self._submenu == "SVC":
                self._pending_submenu_action = ("close_svc", pygame.time.get_ticks() + 250)
                return True
            if self._submenu in {"STATUS", "MSSTAT"}:
                self._submenu = None
                self._status_page_idx = 0
                self._status_selected_sub_idx = 0
                self._status_system_name = None
                return True
            context.request_vded(context.portal_index, "MENU")
            return True
        if label in {"L1", "L2"}:
            if self._submenu == "STATUS":
                status_name = self._status_active_system_name()
                vs_bit_status, _catalog = self._vs_bit_runtime_state()
                subsystems = self._subsystems_for_system(status_name, vs_bit_status)
                total_subs = len(subsystems)
                if total_subs <= 0:
                    self._status_selected_sub_idx = 0
                    return True
                idx = int(self._status_selected_sub_idx) % total_subs
                if label == "L1":
                    idx = (idx - 1) % total_subs
                else:
                    idx = (idx + 1) % total_subs
                self._status_selected_sub_idx = idx
                self._status_page_idx = 0
                return True
            if self._submenu == "MSSTAT":
                return False
            total = len(self._vehicle_systems()) + len(self._mission_systems())
            if total <= 0:
                return True
            if self._selected_flat_index is None:
                self._selected_flat_index = total - 1 if label == "L1" else 0
            elif label == "L1":
                self._selected_flat_index = (self._selected_flat_index - 1) % total
            else:
                self._selected_flat_index = (self._selected_flat_index + 1) % total
            if self._submenu == "STATUS":
                self._status_page_idx = 0
            return True
        if self._submenu == "STATUS":
            if label == "R2":
                selected_system = str(self._status_active_system_name()).upper().strip()
                selected_sub = self._status_selected_subsystem_name()
                keys: List[str] = []
                if selected_system != "":
                    keys.append(selected_system)
                if selected_sub != "" and selected_sub not in keys:
                    keys.append(selected_sub)
                self._request_phm_status_bit(keys, 10000)
                return True
            if label == "R1":
                self._pending_submenu_action = ("open_svc", pygame.time.get_ticks() + 250)
                return True
            if label == "T2":
                # STATUS acts as a toggle: selecting T2 again returns to PHM base.
                self._submenu = None
                self._status_page_idx = 0
                self._status_selected_sub_idx = 0
                self._status_system_name = None
                return True
            if label in {"T3"}:
                return True
            return False
        if self._submenu == "MSSTAT":
            return False
        if label in {"T3", "R4"}:
            return True
        if label == "T2":
            self._pending_submenu_action = ("open_status", pygame.time.get_ticks() + 250)
            return True
        if label == "R5":
            self._pending_submenu_action = ("open_msstat", pygame.time.get_ticks() + 250)
            return True
        if label == "R3":
            self._pending_submenu_action = ("open_svc", pygame.time.get_ticks() + 250)
            return True
        return False

    def osb_is_interactive(self, label: str) -> bool:
        if self._submenu == "STATUS":
            return label in {"T1", "L1", "L2", "T3", "R1", "R2"}
        if self._submenu == "MSSTAT":
            return label == "T1"
        if self._submenu == "SVC":
            return label == "T1"
        if label in {"L3", "L5", "T3"}:
            return False
        return True

    def get_t1_override(self, system_mode: str) -> Optional[List[Tuple[str, Tuple[int, int, int]]]]:
        if self._submenu == "SVC":
            return [("PHM", (0, 255, 0)), (system_mode, (0, 255, 0)), ("SVC", (255, 0, 255))]
        if self._submenu == "STATUS":
            return [("PHM", (0, 255, 0)), ("STATUS", (255, 0, 255)), ("", (0, 0, 0))]
        if self._submenu == "MSSTAT":
            return [("PHM", (0, 255, 0)), ("MSSTAT", (255, 0, 255)), ("", (0, 0, 0))]
        return None

    def t1_opens_menu(self) -> bool:
        return self._submenu is None

    def suppress_subportals(self) -> bool:
        return False

    def opaque_subportal_background(self) -> bool:
        return self._submenu in {"STATUS", "MSSTAT"}
