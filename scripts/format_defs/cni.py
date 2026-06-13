from formats import *  # noqa: F401,F403


class CniFormat(FormatBase):
    name: str = "CNI"

    _start_options: List[str] = ["BASIC", "AUTON", "CNTD", "ILS", "ICLS"]
    _mode_options: List[str] = ["STD", "ALT", "EMCON"]
    _shared_mode: str = "STD"
    _shared_start: str = "AUTON"
    _shared_t2_popup_open: bool = False
    _shared_l1_class_popup_open: bool = False
    _shared_confirm_action: Optional[str] = None
    _shared_immed_selected: bool = True
    _shared_selected_row_idx: int = 0
    _table_break_after: int = 6
    _shared_cntd_prompt_active: bool = False
    _shared_cntd_prompt_step_idx: int = 0
    _table_default_rows: List[Tuple[str, str, str, str, str]] = [
        ("U/V", "U", "", "", "A"),
        ("U/V", "U", "Y", "", "B"),
        ("MADL", "S", "Y", "", "C"),
        ("LINK16", "S", "", "", ""),
        ("IFFT", "S", "", "", ""),
        ("INTG", "S", "", "", ""),
        ("RALT", "U", "", "", ""),
        ("UHF", "U", "", "", ""),
        ("VHF", "U", "", "", ""),
        ("TACAN", "", "", "", ""),
    ]
    _table_rows: List[Tuple[str, str, str, str, str]] = list(_table_default_rows)
    _table_row_order: Dict[Tuple[str, str, str], int] = {
        (str(row[0]), str(row[2]), str(row[4])): idx for idx, row in enumerate(_table_default_rows)
    }
    _shared_restart_until_by_key: Dict[Tuple[str, str, str], int] = {}
    _class_options: List[str] = ["U", "S", "SS", "TS"]

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
            return pygame.Rect(rect.x, rect.y + top_offset - SIDE_OSB_Y_SHIFT + (idx - 1) * DISPLAY_OSB_H, GRID_CELL_W, DISPLAY_OSB_H)
        if side == "R":
            if idx < 1 or idx > side_count:
                return None
            return pygame.Rect(rect.right - GRID_CELL_W, rect.y + top_offset - SIDE_OSB_Y_SHIFT + (idx - 1) * DISPLAY_OSB_H, GRID_CELL_W, DISPLAY_OSB_H)
        return None

    @staticmethod
    def _cell_rect(rect: pygame.Rect, cell: str) -> pygame.Rect:
        col = ord(cell[0].upper()) - ord("A")
        row = int(cell[1:]) - 1
        return pygame.Rect(rect.x + col * GRID_CELL_W, rect.y + row * GRID_CELL_H, GRID_CELL_W, GRID_CELL_H)

    @staticmethod
    def _popup_cell_rect(rect: pygame.Rect, cell: str) -> pygame.Rect:
        col = ord(cell[0].upper()) - ord("A")
        row = int(cell[1:]) - 1
        return pygame.Rect(rect.x + col * GRID_CELL_W, rect.y - SIDE_OSB_Y_SHIFT + row * GRID_CELL_H, GRID_CELL_W, GRID_CELL_H)

    def _start_popup_rows(self, rect: pygame.Rect) -> Tuple[int, int]:
        return 3, 6

    def _start_popup_rect(self, rect: pygame.Rect) -> pygame.Rect:
        row_start, row_end = self._start_popup_rows(rect)
        return self._popup_cell_rect(rect, f"B{row_start}").union(self._popup_cell_rect(rect, f"D{row_end}"))

    def _confirm_popup_rect(self, rect: pygame.Rect) -> pygame.Rect:
        width = max(1, int(round(4.25 * DPI)))
        height = max(1, int(round(2.25 * DPI)))
        top_count = 5 if rect.width < int(10 * DPI) else 10
        top_offset = DISPLAY_OSB_H if top_count > 0 else 0
        row2_center_y = rect.y + top_offset + DISPLAY_OSB_H + (DISPLAY_OSB_H // 2)
        x = rect.centerx - (width // 2)
        y = int(row2_center_y - (height / 2))
        return pygame.Rect(x, y, width, height)

    def _confirm_lines(self) -> List[str]:
        action = str(self._shared_confirm_action or "").upper().strip()
        if action == "T4_RECALL":
            return ["CONFIRM", "RECALL CURRENT", "CONFIG?"]
        if action == "T5_RESET":
            return ["CONFIRM", "RESET", "CURRENT", "CONFIG?"]
        return []

    def _draw_confirm_popup(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        if str(self._shared_confirm_action or "").strip() == "":
            return
        lines = self._confirm_lines()
        if len(lines) <= 0:
            return
        popup = self._confirm_popup_rect(rect)
        pygame.draw.rect(surface, (0, 255, 255), popup)
        pygame.draw.rect(surface, (255, 255, 255), popup, 1)
        font = get_font(18)
        rendered = [font.render(line, True, (0, 0, 0)) for line in lines]
        total_h = sum(s.get_height() for s in rendered) + max(0, len(rendered) - 1) * 2
        y = popup.centery - (total_h // 2)
        for surf in rendered:
            rr = surf.get_rect(centerx=popup.centerx, y=y)
            surface.blit(surf, rr)
            y = rr.bottom + 2

    def _class_popup_rect(self, rect: pygame.Rect) -> pygame.Rect:
        return self._start_popup_rect(rect)

    def _draw_class_popup(self, surface: pygame.Surface, rect: pygame.Rect, selected_class: str) -> None:
        if not bool(self._shared_l1_class_popup_open):
            return
        cyan = (0, 255, 255)
        option_cells = ["B3", "C3", "D3", "B4"]
        for cell in option_cells:
            box = self._popup_cell_rect(rect, cell)
            surface.fill((0, 0, 0), box)
            pygame.draw.rect(surface, cyan, box, 1)
        font = get_font(16)
        selected_norm = str(selected_class).upper().strip()
        for idx, opt in enumerate(self._class_options):
            if idx >= len(option_cells):
                break
            cell = option_cells[idx]
            box = self._popup_cell_rect(rect, cell)
            selected = selected_norm == str(opt).upper().strip()
            txt = font.render(str(opt), True, (255, 255, 255) if selected else cyan)
            tr = txt.get_rect(center=box.center)
            if selected:
                pygame.draw.rect(surface, (255, 255, 255), tr.inflate(6, 3), 1)
            surface.blit(txt, tr)

    def _selected_row_is_active(self) -> bool:
        row_count = len(self._table_rows)
        if row_count <= 0:
            return False
        idx = max(0, min(row_count - 1, int(self._shared_selected_row_idx)))
        break_after = int(getattr(type(self), "_table_break_after", self._table_break_after))
        return idx <= break_after

    def _is_t3_std(self) -> bool:
        phase = self._cni_page_phase_from_phm()
        mode = str(self._shared_mode).upper().strip()
        return phase == "STD" and mode == "STD"

    def _selected_has_unacked_caution(self) -> bool:
        # Placeholder for future caution wiring.
        return False

    def _ack_selected_caution(self) -> None:
        # Placeholder for future caution wiring.
        return

    def _config_mode(self) -> str:
        return str(self._shared_start).upper().strip()

    def _is_cntd_mode(self) -> bool:
        return self._config_mode() == "CNTD"

    def _is_auton_mode(self) -> bool:
        # Keep typo tolerance for AUTON mode labels.
        return self._config_mode() in {"AUTON", "AUTION"}

    def _selected_is_inactive_cntd(self) -> bool:
        return self._is_cntd_mode() and (not self._selected_row_is_active())

    def _sync_cntd_prompt_state(self) -> None:
        if (not self._selected_is_inactive_cntd()) or bool(self._shared_immed_selected):
            self._shared_cntd_prompt_active = False
            self._shared_cntd_prompt_step_idx = 0

    @staticmethod
    def _row_key(row: Tuple[str, str, str, str, str]) -> Tuple[str, str, str]:
        # Stable row identity: ACTIVITY, DATA, COM (CLASS/NOTE are mutable).
        return (str(row[0]), str(row[2]), str(row[4]))

    def _row_order_index(self, row: Tuple[str, str, str, str, str]) -> int:
        return int(self._table_row_order.get(self._row_key(row), 10**6))

    def _cleanup_restart_notes(self, now_ms: int) -> None:
        cls = type(self)
        src = getattr(cls, "_shared_restart_until_by_key", {})
        if not isinstance(src, dict):
            src = {}
        cls._shared_restart_until_by_key = {
            k: int(until)
            for k, until in src.items()
            if int(until) > int(now_ms)
        }

    def _row_display_note(self, row: Tuple[str, str, str, str, str], now_ms: int) -> str:
        key = self._row_key(row)
        shared = getattr(type(self), "_shared_restart_until_by_key", {})
        if not isinstance(shared, dict):
            shared = {}
        until = int(shared.get(key, 0))
        if until > int(now_ms):
            return "RESTARTING"
        return str(row[3]).strip()

    def _trigger_selected_restart(self) -> None:
        row_count = len(self._table_rows)
        if row_count <= 0:
            return
        idx = max(0, min(row_count - 1, int(self._shared_selected_row_idx)))
        row = self._table_rows[idx]
        now_ms = int(pygame.time.get_ticks())
        cls = type(self)
        shared = getattr(cls, "_shared_restart_until_by_key", {})
        if not isinstance(shared, dict):
            shared = {}
            cls._shared_restart_until_by_key = shared
        shared[self._row_key(row)] = now_ms + 5000

    def _start_selected_item(self) -> None:
        row_count = len(self._table_rows)
        if row_count <= 0:
            return
        idx = max(0, min(row_count - 1, int(self._shared_selected_row_idx)))
        if idx <= int(self._table_break_after):
            return
        row = self._table_rows.pop(idx)
        cls = type(self)
        old_break = int(getattr(cls, "_table_break_after", self._table_break_after))
        insert_at = max(0, min(len(self._table_rows), old_break + 1))
        moved_order = self._row_order_index(row)
        for j in range(0, max(0, old_break + 1)):
            if self._row_order_index(self._table_rows[j]) > moved_order:
                insert_at = j
                break
        self._table_rows.insert(insert_at, row)
        cls._table_break_after = min(len(self._table_rows) - 1, old_break + 1)
        cls._shared_selected_row_idx = insert_at
        self._table_break_after = cls._table_break_after
        self._shared_selected_row_idx = cls._shared_selected_row_idx

    def _stop_selected_item(self) -> None:
        row_count = len(self._table_rows)
        if row_count <= 0:
            return
        idx = max(0, min(row_count - 1, int(self._shared_selected_row_idx)))
        if idx > int(self._table_break_after):
            return
        row = self._table_rows.pop(idx)
        cls = type(self)
        old_break = int(getattr(cls, "_table_break_after", self._table_break_after))
        cls._table_break_after = max(-1, old_break - 1)
        self._table_break_after = cls._table_break_after
        moved_order = self._row_order_index(row)
        insert_at = len(self._table_rows)
        inactive_start = max(0, min(len(self._table_rows), old_break))
        for j in range(inactive_start, len(self._table_rows)):
            if self._row_order_index(self._table_rows[j]) > moved_order:
                insert_at = j
                break
        self._table_rows.insert(insert_at, row)
        cls._shared_selected_row_idx = insert_at
        self._shared_selected_row_idx = cls._shared_selected_row_idx

    def _selected_class_value(self) -> str:
        row_count = len(self._table_rows)
        if row_count <= 0:
            return ""
        idx = max(0, min(row_count - 1, int(self._shared_selected_row_idx)))
        return str(self._table_rows[idx][1]).strip()

    def _set_selected_class_value(self, class_value: str) -> None:
        row_count = len(self._table_rows)
        if row_count <= 0:
            return
        idx = max(0, min(row_count - 1, int(self._shared_selected_row_idx)))
        row = self._table_rows[idx]
        self._table_rows[idx] = (str(row[0]), str(class_value).strip(), str(row[2]), str(row[3]), str(row[4]))

    @staticmethod
    def _cni_page_phase_from_phm() -> str:
        panel = PANEL_BUTTON_STATES if isinstance(PANEL_BUTTON_STATES, dict) else {}
        phm = panel.get("PHM STATUS", {}) if isinstance(panel, dict) else {}
        if isinstance(phm, dict):
            phase = str(phm.get("cni_page_phase", "")).upper().strip()
            if phase in {"STD", "STARTUP", "INOP", "BIT", "SHUTDOWN"}:
                return phase
            sub_status = phm.get("runtime_subsystem_status", {})
            if isinstance(sub_status, dict):
                st = str(sub_status.get("CNI", "")).upper().strip()
                if st == "BIT":
                    return "BIT"
                if st == "INIT":
                    return "STARTUP"
                if st in {"INOP", "OFF", "OF"}:
                    return "INOP"
                if st == "DEGD":
                    return "SHUTDOWN"
        return "STD"

    @staticmethod
    def _clear_cni_bit_request() -> None:
        panel = PANEL_BUTTON_STATES if isinstance(PANEL_BUTTON_STATES, dict) else {}
        phm = panel.get("PHM STATUS", {}) if isinstance(panel, dict) else {}
        if not isinstance(phm, dict):
            return
        bit_map = phm.get("bit_until_ms", {})
        if not isinstance(bit_map, dict):
            return
        bit_map.pop("CNI", None)
        bit_map.pop("COM_NAV", None)

    def _perform_l3_restart_action(self) -> None:
        # Mirror current L3 RESTART behavior.
        if self._is_cntd_mode() and self._selected_row_is_active():
            self._trigger_selected_restart()
            return
        if self._is_auton_mode():
            # Placeholder only for now; no AUTON restart behavior implemented.
            return

    def _apply_confirm_action(self) -> None:
        action = str(self._shared_confirm_action or "").upper().strip()
        self._shared_confirm_action = None
        if action == "T4_RECALL":
            # Placeholder only for now; reset/recall behavior intentionally no-op.
            return
        if action == "T5_RESET":
            self._perform_l3_restart_action()

    def _draw_text_lines(
        self,
        surface: pygame.Surface,
        box: pygame.Rect,
        lines: List[Tuple[str, Tuple[int, int, int], bool]],
        *,
        align: str = "center",
        v_align: str = "center",
        size: int = 16,
        selected: bool = False,
        flash: bool = False,
    ) -> None:
        font = get_font(size)
        y = box.top + 2
        total_h = 0
        rendered: List[Tuple[pygame.Surface, pygame.Rect, Tuple[int, int, int], bool]] = []
        for text, color, underlined in lines:
            surf = font.render(str(text), True, (0, 0, 0) if flash else color)
            if align == "left":
                r = surf.get_rect(left=box.left + OSB_PADDING)
            elif align == "right":
                r = surf.get_rect(right=box.right - OSB_PADDING)
            else:
                r = surf.get_rect(centerx=box.centerx)
            rendered.append((surf, r, color, bool(underlined)))
            total_h += surf.get_height()
        total_h += max(0, len(rendered) - 1) * 1
        if str(v_align).lower() == "top":
            y = box.top + 2
        else:
            y = box.centery - (total_h // 2)
        if selected:
            pygame.draw.rect(surface, (255, 255, 255), box.inflate(-6, -4), 1)
        for surf, r, color, underlined in rendered:
            r.y = y
            if flash:
                pygame.draw.rect(surface, (255, 255, 255), r.inflate(4, 2))
            surface.blit(surf, r)
            if underlined:
                pygame.draw.line(surface, (0, 0, 0) if flash else color, (r.left, r.bottom + 1), (r.right, r.bottom + 1), 1)
            y = r.bottom + 1

    def _draw_inc_dec_symbol(self, surface: pygame.Surface, box: pygame.Rect, is_inc: bool, flash: bool = False) -> None:
        cyan = (0, 255, 255)
        white = (255, 255, 255)
        tri_w = max(10, box.width // 3)
        tri_h = max(10, box.height // 3)
        cx = box.left + OSB_PADDING + tri_w // 2 + 2
        cy = box.centery
        if is_inc:
            points = [
                (cx, cy - tri_h // 2),
                (cx - tri_w // 2, cy + tri_h // 2),
                (cx + tri_w // 2, cy + tri_h // 2),
            ]
        else:
            points = [
                (cx, cy + tri_h // 2),
                (cx - tri_w // 2, cy - tri_h // 2),
                (cx + tri_w // 2, cy - tri_h // 2),
            ]
        pygame.draw.polygon(surface, white if bool(flash) else cyan, points, 0)

    def _draw_start_popup(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        if not bool(self._shared_t2_popup_open):
            return
        cyan = (0, 255, 255)
        option_cells = ["B3", "C3", "D3", "B4", "C4"]
        for cell in option_cells:
            box = self._popup_cell_rect(rect, cell)
            surface.fill((0, 0, 0), box)
            pygame.draw.rect(surface, cyan, box, 1)
        font = get_font(16)
        for idx, opt in enumerate(self._start_options):
            if idx >= len(option_cells):
                break
            cell = option_cells[idx]
            box = self._popup_cell_rect(rect, cell)
            selected = str(self._shared_start).upper().strip() == str(opt).upper().strip()
            txt = font.render(str(opt), True, (255, 255, 255) if selected else cyan)
            tr = txt.get_rect(center=box.center)
            if selected:
                pygame.draw.rect(surface, (255, 255, 255), tr.inflate(6, 3), 1)
            surface.blit(txt, tr)

    def render(self, surface, rect, is_primary: bool, context: FormatContext) -> None:
        if not is_primary:
            draw_centered_text(surface, rect, "CNI", "00FFFF", 14)
            return
        prev_clip = surface.get_clip()
        surface.set_clip(rect)
        surface.fill((0, 0, 0), rect)
        cyan = (0, 255, 255)
        green = (0, 255, 0)
        gray = (128, 128, 128)

        def flash(label: str) -> bool:
            try:
                return bool(context.is_osb_flashing(label))
            except Exception:
                return False

        # T2-T5, L1-L5 layout.
        t2 = self._osb_box(rect, "T2")
        t3 = self._osb_box(rect, "T3")
        t4 = self._osb_box(rect, "T4")
        t5 = self._osb_box(rect, "T5")
        l1 = self._osb_box(rect, "L1")
        l2 = self._osb_box(rect, "L2")
        l3 = self._osb_box(rect, "L3")
        l4 = self._osb_box(rect, "L4")
        l5 = self._osb_box(rect, "L5")
        r5 = self._osb_box(rect, "R5")

        row_count = len(self._table_rows)
        if row_count > 0:
            self._shared_selected_row_idx = max(0, min(row_count - 1, int(self._shared_selected_row_idx)))
            selected_class = self._selected_class_value()
        else:
            selected_class = ""
        now_ms = int(pygame.time.get_ticks())
        self._cleanup_restart_notes(now_ms)
        self._sync_cntd_prompt_state()
        row_is_active = self._selected_row_is_active()
        cntd_inactive_selected = self._selected_is_inactive_cntd()
        cntd_prompt_active = bool(self._shared_cntd_prompt_active and cntd_inactive_selected)
        cni_phase = self._cni_page_phase_from_phm()
        cni_t3_lines: List[Tuple[str, Tuple[int, int, int], bool]] = [(str(self._shared_mode), green, False)]
        cni_restricted = False
        cni_bit_mode = False
        if cni_phase == "STARTUP":
            cni_t3_lines = [("STARTUP", green, False)]
            cni_restricted = True
        elif cni_phase == "INOP":
            cni_t3_lines = [("INOP", (255, 255, 0), False)]
            cni_restricted = True
        elif cni_phase == "BIT":
            cni_t3_lines = [("BIT", (255, 255, 0), False)]
            cni_restricted = True
            cni_bit_mode = True
        elif cni_phase == "SHUTDOWN":
            cni_t3_lines = [("SHUT", (255, 255, 0), False), ("DOWN", (255, 255, 0), False)]
            cni_restricted = True

        # CNI column headers (ACTIVITY/CLASS/DATA/NOTE/COM) across T2..T5.
        if (not cni_restricted) and t2 is not None and t5 is not None and l1 is not None:
            labels = ["ACTIVITY", "CLASS", "DATA", "NOTE", "COM"]
            x_left = float(t2.centerx)
            x_right = float(t5.centerx)
            span = max(1.0, x_right - x_left)
            # Tuned column geometry:
            # - CLASS moved further right.
            # - NOTE moved further left.
            # - DATA centered between CLASS and NOTE.
            class_x = x_left + (span * 0.28)
            note_x = x_left + (span * 0.67)
            data_x = (class_x + note_x) * 0.5
            x_positions = [
                x_left,
                class_x,
                data_x,
                note_x,
                x_right,
            ]
            col_bounds = [
                x_positions[0] - ((x_positions[1] - x_positions[0]) * 0.5),
                (x_positions[0] + x_positions[1]) * 0.5,
                (x_positions[1] + x_positions[2]) * 0.5,
                (x_positions[2] + x_positions[3]) * 0.5,
                (x_positions[3] + x_positions[4]) * 0.5,
                x_positions[4] + ((x_positions[4] - x_positions[3]) * 0.5),
            ]
            l1_font = get_font(15)
            l1_class_probe = l1_font.render("CLASS", True, cyan)
            l1_value_probe = l1_font.render((selected_class if selected_class != "" else " "), True, cyan)
            l1_total_h = l1_class_probe.get_height() + l1_value_probe.get_height() + 1
            y_top = l1.centery - (l1_total_h // 2)
            l1_class_underline_y = y_top + l1_class_probe.get_height() + 1

            header_font = get_font(15)
            header_rects: List[pygame.Rect] = []
            for txt, xpos in zip(labels, x_positions):
                surf = header_font.render(txt, True, green)
                tr = surf.get_rect(centerx=int(round(xpos)), y=y_top)
                surface.blit(surf, tr)
                header_rects.append(tr)
            if header_rects:
                pygame.draw.line(surface, green, (header_rects[0].left, l1_class_underline_y), (header_rects[-1].right, l1_class_underline_y), 1)

                row_font = get_font(12)
                row_text_h = row_font.get_height()
                row_step = row_text_h + 4
                row_y = l1_class_underline_y + max(4, row_step // 3)
                sep_after = int(self._table_break_after)
                draw_sep = 0 <= sep_after < (len(self._table_rows) - 1)
                for row_idx, row_vals in enumerate(self._table_rows):
                    if row_idx == int(self._shared_selected_row_idx):
                        star = row_font.render("*", True, (255, 255, 255))
                        sr = star.get_rect(right=header_rects[0].left - 2, centery=row_y + (row_text_h // 2))
                        surface.blit(star, sr)

                    row_active = row_idx <= sep_after
                    for col_idx, cell in enumerate(row_vals):
                        if (not row_active) and col_idx in {2, 3, 4}:
                            continue
                        if col_idx == 3:
                            value = self._row_display_note(row_vals, now_ms)
                        else:
                            value = str(cell).strip()
                        if value == "":
                            continue
                        col_color = green if col_idx in {3, 4} else cyan
                        surf = row_font.render(value, True, col_color)
                        if col_idx in {0, 3}:
                            tr = surf.get_rect(left=int(round(col_bounds[col_idx])) + 3, y=row_y)
                        else:
                            tr = surf.get_rect(centerx=int(round(x_positions[col_idx])), y=row_y)
                        surface.blit(surf, tr)

                    if draw_sep and row_idx == sep_after:
                        sep_extra_gap = 20
                        next_row_y = row_y + row_step + sep_extra_gap
                        prev_bottom = row_y + row_text_h
                        sep_y = prev_bottom + max(1, (next_row_y - prev_bottom) // 2)
                        pygame.draw.line(surface, cyan, (header_rects[0].left, sep_y), (header_rects[-1].right, sep_y), 1)
                        row_y = next_row_y
                    else:
                        row_y += row_step

        if (not cni_restricted) and t2 is not None:
            self._draw_text_lines(
                surface,
                t2,
                [("CONFIG", green, True), (str(self._shared_start), cyan, False)],
                align="center",
                v_align="top",
                size=15,
                flash=flash("T2"),
            )
        if t3 is not None:
            self._draw_text_lines(
                surface,
                t3,
                cni_t3_lines,
                align="center",
                v_align="top",
                size=17,
                flash=flash("T3"),
            )
        if (not cni_restricted) and t4 is not None:
            t4_state = ButtonState(
                button_id="CNI_T4",
                button_type=ButtonType.MOMENTARY_SINGLE,
                text="RECALL",
                h_align="center",
                v_align="top",
                padding=OSB_PADDING,
                font_size=15,
                flash_until_ms=1 if flash("T4") else 0,
            )
            render_button(surface, t4, t4_state, get_font, 0)
        if t5 is not None and ((not cni_restricted) or cni_bit_mode):
            t5_state = ButtonState(
                button_id="CNI_T5",
                button_type=ButtonType.MOMENTARY_SINGLE,
                text="RESET",
                h_align="center",
                v_align="top",
                padding=OSB_PADDING,
                font_size=15,
                flash_until_ms=1 if flash("T5") else 0,
            )
            render_button(surface, t5, t5_state, get_font, 0)
        if (not cni_restricted) and l1 is not None:
            if cntd_prompt_active:
                step_text = "1 OF 2" if int(self._shared_cntd_prompt_step_idx) == 0 else "2 OF 2"
                self._draw_text_lines(
                    surface,
                    l1,
                    [(step_text, green, False), ("NEXT", cyan, False)],
                    align="left",
                    size=15,
                    flash=flash("L1"),
                )
            elif self._is_auton_mode():
                self._draw_text_lines(
                    surface,
                    l1,
                    [("DATA", cyan, False)],
                    align="left",
                    size=15,
                    flash=flash("L1"),
                )
            else:
                self._draw_text_lines(
                    surface,
                    l1,
                    [("CLASS", cyan, True), ((selected_class if selected_class != "" else " "), cyan, False)],
                    align="left",
                    size=15,
                    flash=flash("L1"),
                )
        if (not cni_restricted) and l2 is not None:
            if cntd_prompt_active:
                l2_text = "ACCEPT" if int(self._shared_cntd_prompt_step_idx) == 0 else "START"
            elif cntd_inactive_selected:
                l2_text = "START" if bool(self._shared_immed_selected) else "START\nACCEPT"
            elif row_is_active:
                l2_text = "STOP"
            else:
                l2_text = "START"
            l2_state = ButtonState(
                button_id="CNI_L2",
                button_type=ButtonType.MOMENTARY_SINGLE,
                text=l2_text,
                h_align="left",
                v_align="center",
                padding=OSB_PADDING,
                font_size=15,
                flash_until_ms=1 if flash("L2") else 0,
            )
            render_button(surface, l2, l2_state, get_font, 0)
        if (not cni_restricted) and l3 is not None:
            if cntd_prompt_active:
                l3_state = ButtonState(
                    button_id="CNI_L3",
                    button_type=ButtonType.MOMENTARY_SINGLE,
                    text="REJECT",
                    h_align="left",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=15,
                    flash_until_ms=1 if flash("L3") else 0,
                )
            elif self._is_cntd_mode() and row_is_active:
                l3_state = ButtonState(
                    button_id="CNI_L3",
                    button_type=ButtonType.MOMENTARY_SINGLE,
                    text="RESTART",
                    h_align="left",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=15,
                    flash_until_ms=1 if flash("L3") else 0,
                )
            elif self._is_auton_mode():
                l3_state = ButtonState(
                    button_id="CNI_L3",
                    button_type=ButtonType.MOMENTARY_SINGLE,
                    text="RESTART",
                    h_align="left",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=15,
                    flash_until_ms=1 if flash("L3") else 0,
                )
            else:
                l3_state = ButtonState(
                    button_id="CNI_L3",
                    button_type=ButtonType.DOUBLE_FUNCTION,
                    options=["IMMED", "SELECT"],
                    selected_index=0 if bool(self._shared_immed_selected) else 1,
                    h_align="left",
                    v_align="top",
                    padding=OSB_PADDING,
                    font_size=15,
                    flash_until_ms=1 if flash("L3") else 0,
                )
            render_button(surface, l3, l3_state, get_font, 0)
        if (not cni_restricted) and l4 is not None:
            self._draw_inc_dec_symbol(surface, l4, True, flash=flash("L4"))
        if (not cni_restricted) and l5 is not None:
            self._draw_inc_dec_symbol(surface, l5, False, flash=flash("L5"))
        if r5 is not None and self._is_t3_std():
            ack_has_caution = bool(self._selected_has_unacked_caution())
            ack_color = cyan if ack_has_caution else gray
            self._draw_text_lines(
                surface,
                r5,
                [("ACK", ack_color, False)],
                align="right",
                v_align="center",
                size=15,
                flash=flash("R5"),
            )

        if cni_restricted:
            self._shared_t2_popup_open = False
            self._shared_l1_class_popup_open = False
        self._draw_start_popup(surface, rect)
        if not cni_restricted:
            self._draw_class_popup(surface, rect, selected_class)
        self._draw_confirm_popup(surface, rect)
        pygame.draw.rect(surface, cyan, rect, 1)
        surface.set_clip(prev_clip)

    def on_click(self, pos: Tuple[int, int], rect: pygame.Rect, context: FormatContext) -> bool:
        _ = context
        if str(self._shared_confirm_action or "").strip() != "":
            popup = self._confirm_popup_rect(rect)
            if popup.collidepoint(pos):
                self._apply_confirm_action()
            else:
                self._shared_confirm_action = None
            return True
        if (not bool(self._shared_t2_popup_open)) and (not bool(self._shared_l1_class_popup_open)):
            return False
        rel_x = max(0, pos[0] - rect.x)
        rel_y = max(0, pos[1] - (rect.y - SIDE_OSB_Y_SHIFT))
        col = max(0, min(4, int(rel_x // GRID_CELL_W)))
        row = max(0, min(7, int(rel_y // GRID_CELL_H)))
        cell = f"{chr(ord('A') + col)}{row + 1}"

        if bool(self._shared_t2_popup_open):
            popup = self._start_popup_rect(rect)
            if popup.collidepoint(pos):
                row_start, _row_end = self._start_popup_rows(rect)
                option_cells = [f"B{row_start}", f"C{row_start}", f"D{row_start}", f"B{row_start + 1}", f"C{row_start + 1}"]
                if cell in option_cells:
                    idx = option_cells.index(cell)
                    if 0 <= idx < len(self._start_options):
                        self._shared_start = str(self._start_options[idx])
                        self._shared_t2_popup_open = False
                        self._sync_cntd_prompt_state()
                        return True
                return True
            self._shared_t2_popup_open = False
            return False

        if bool(self._shared_l1_class_popup_open):
            popup = self._class_popup_rect(rect)
            if popup.collidepoint(pos):
                row_start, _row_end = self._start_popup_rows(rect)
                option_cells = [f"B{row_start}", f"C{row_start}", f"D{row_start}", f"B{row_start + 1}"]
                if cell in option_cells:
                    idx = option_cells.index(cell)
                    if 0 <= idx < len(self._class_options):
                        self._set_selected_class_value(str(self._class_options[idx]))
                        self._shared_l1_class_popup_open = False
                        return True
                return True
            self._shared_l1_class_popup_open = False
            return False
        return False

    def on_osb(self, label: str, context: FormatContext) -> bool:
        token = str(label).upper().strip()
        cni_phase = self._cni_page_phase_from_phm()
        cni_restricted = cni_phase in {"STARTUP", "INOP", "BIT", "SHUTDOWN"}
        if token == "T1":
            context.request_vded(context.portal_index, "MENU")
            return True
        if token in {"T4", "T5"}:
            self._shared_t2_popup_open = False
            self._shared_l1_class_popup_open = False
            self._shared_confirm_action = "T4_RECALL" if token == "T4" else "T5_RESET"
            return True
        if cni_restricted:
            return token in {"T2", "T4", "T5", "L1", "L2", "L3", "L4", "L5"}
        if token == "T2":
            self._shared_t2_popup_open = not bool(self._shared_t2_popup_open)
            self._shared_l1_class_popup_open = False
            self._sync_cntd_prompt_state()
            return True
        if token == "L4":
            self._shared_l1_class_popup_open = False
            row_count = len(self._table_rows)
            if row_count > 0:
                self._shared_selected_row_idx = (int(self._shared_selected_row_idx) - 1) % row_count
            self._sync_cntd_prompt_state()
            return True
        if token == "L5":
            self._shared_l1_class_popup_open = False
            row_count = len(self._table_rows)
            if row_count > 0:
                self._shared_selected_row_idx = (int(self._shared_selected_row_idx) + 1) % row_count
            self._sync_cntd_prompt_state()
            return True
        self._sync_cntd_prompt_state()
        if token == "L1":
            if bool(self._shared_cntd_prompt_active) and self._selected_is_inactive_cntd():
                self._shared_cntd_prompt_step_idx = 1 if int(self._shared_cntd_prompt_step_idx) == 0 else 0
                self._shared_l1_class_popup_open = False
                return True
            if self._is_auton_mode():
                self._shared_l1_class_popup_open = False
                return True
            selected_class = self._selected_class_value()
            if selected_class != "":
                self._shared_l1_class_popup_open = not bool(self._shared_l1_class_popup_open)
                self._shared_t2_popup_open = False
            else:
                self._shared_l1_class_popup_open = False
            return True
        if token == "L2":
            self._shared_l1_class_popup_open = False
            if bool(self._shared_cntd_prompt_active) and self._selected_is_inactive_cntd():
                if int(self._shared_cntd_prompt_step_idx) == 1:
                    self._start_selected_item()
                self._shared_cntd_prompt_active = False
                self._shared_cntd_prompt_step_idx = 0
                self._sync_cntd_prompt_state()
                return True
            if self._selected_is_inactive_cntd():
                if bool(self._shared_immed_selected):
                    self._start_selected_item()
                    self._sync_cntd_prompt_state()
                    return True
                self._shared_cntd_prompt_active = True
                self._shared_cntd_prompt_step_idx = 0
                return True
            if self._selected_row_is_active():
                self._stop_selected_item()
            else:
                self._start_selected_item()
            self._sync_cntd_prompt_state()
            return True
        if token == "L3":
            self._shared_l1_class_popup_open = False
            if bool(self._shared_cntd_prompt_active) and self._selected_is_inactive_cntd():
                self._shared_cntd_prompt_active = False
                self._shared_cntd_prompt_step_idx = 0
                return True
            if self._is_cntd_mode() and self._selected_row_is_active():
                self._perform_l3_restart_action()
                return True
            if self._is_auton_mode():
                self._perform_l3_restart_action()
                return True
            self._shared_immed_selected = not bool(self._shared_immed_selected)
            return True
        if token == "R5":
            if not self._is_t3_std():
                return False
            if self._selected_has_unacked_caution():
                self._ack_selected_caution()
                return True
            return True
        return token in {"L1", "L2", "L3"}

    def osb_is_interactive(self, label: str) -> bool:
        token = str(label).upper().strip()
        phase = self._cni_page_phase_from_phm()
        if phase in {"STARTUP", "INOP", "SHUTDOWN"}:
            return token == "T1"
        if phase == "BIT":
            return token in {"T1", "T5"}
        if token == "R5":
            return self._is_t3_std() and bool(self._selected_has_unacked_caution())
        return token in {"T1", "T2", "T4", "T5", "L1", "L2", "L3", "L4", "L5"}
