from formats import *  # noqa: F401,F403


class IffFormat(FormatBase):
    name: str = "IFF"

    def render(self, surface, rect, is_primary: bool, context: FormatContext) -> None:
        if not is_primary:
            draw_centered_text(surface, rect, "IFF", "00FFFF", 14)
            return
        state = IFF_STATE
        now_ms = int(state.get("now_ms", 0))
        flash_until = state.get("flash_until", {})
        cols = 5
        rows = 8
        cell_w = rect.width // cols
        cell_h = rect.height // rows
        cyan = (0, 255, 255)
        white = (255, 255, 255)
        gray = (128, 128, 128)
        mode_options = state.get("mode_options", ["OFF", "STBY", "MAN", "AUTO"])
        if not isinstance(mode_options, list) or len(mode_options) == 0:
            mode_options = ["OFF", "STBY", "MAN", "AUTO"]
        mode_options = [str(x).upper() for x in mode_options]
        try:
            mode_idx = int(state.get("mode_idx", 0))
        except Exception:
            mode_idx = 0
        mode_idx = max(0, min(len(mode_options) - 1, mode_idx))
        current_mode = str(mode_options[mode_idx])
        if bool(state.get("emergency_on", False)) and bool(state.get("iff_on", False)):
            current_mode = "EMER"
        state["mode_idx"] = mode_idx
        cm_fail_iff_active = bool(state.get("cm_fail_iff_active", False))
        mode_c_degd_active = bool(state.get("mode_c_degd_active", False))
        if cm_fail_iff_active:
            # CM FAIL - IFF forces normal popup interaction paths closed.
            state["a1_menu_open"] = False
            state["a2_menu_open"] = False
            state["e7_subpage_open"] = False
            state["selected_field"] = None

        def cell_rect(cell_name: str) -> pygame.Rect:
            col = ord(cell_name[0]) - ord("A")
            row = int(cell_name[1:]) - 1
            return pygame.Rect(rect.x + col * cell_w, rect.y + row * cell_h, cell_w, cell_h)

        def merged_bc(row_num: int) -> pygame.Rect:
            b = cell_rect(f"B{row_num}")
            c = cell_rect(f"C{row_num}")
            return b.union(c)

        def flashing(key: Optional[str]) -> bool:
            if key is None or not isinstance(flash_until, dict):
                return False
            try:
                return int(flash_until.get(key, 0)) > now_ms
            except Exception:
                return False

        def flash_until_ms_for(*keys: str) -> int:
            out = 0
            if not isinstance(flash_until, dict):
                return out
            for key in keys:
                try:
                    out = max(out, int(flash_until.get(key, 0)))
                except Exception:
                    continue
            return out

        a1_menu_open = bool(state.get("a1_menu_open", False))
        a2_menu_open = bool(state.get("a2_menu_open", False))
        e7_subpage_open = bool(state.get("e7_subpage_open", False))
        merge_top_bc = not (a2_menu_open or e7_subpage_open)

        pygame.draw.rect(surface, cyan, rect, 1)
        for i in range(1, cols):
            x = rect.x + i * cell_w
            if i == 2 or (e7_subpage_open and i == 4):
                for row_idx in range(rows):
                    if i == 2 and row_idx == 7 and not e7_subpage_open:
                        continue
                    if i == 2 and row_idx == 0 and merge_top_bc:
                        continue
                    if e7_subpage_open and i == 2 and row_idx in {1, 2}:
                        continue
                    if e7_subpage_open and i == 4 and row_idx == 1:
                        continue
                    y0 = rect.y + row_idx * cell_h
                    y1 = y0 + cell_h
                    pygame.draw.line(surface, cyan, (x, y0), (x, y1), 1)
            else:
                pygame.draw.line(surface, cyan, (x, rect.top), (x, rect.bottom), 1)
        for j in range(1, rows):
            y = rect.y + j * cell_h
            pygame.draw.line(surface, cyan, (rect.left, y), (rect.right, y), 1)

        def draw_line_bottom(
            box: pygame.Rect,
            line_no: int,
            text: str,
            color: Tuple[int, int, int],
            *,
            size: int = 16,
            box_selected: bool = False,
            flash_key: Optional[str] = None,
            highlight_fill: Optional[Tuple[int, int, int]] = None,
        ) -> pygame.Rect:
            font = get_font(size)
            y3 = box.bottom - font.get_height() - 2
            y2 = y3 - font.get_height() - 1
            y1 = y2 - font.get_height() - 1
            y = y1 if line_no <= 1 else y2 if line_no == 2 else y3
            is_flash = flashing(flash_key)
            draw_color = (0, 0, 0) if is_flash else color
            surf = font.render(text, True, draw_color)
            srect = surf.get_rect(centerx=box.centerx)
            srect.y = y
            if is_flash:
                pygame.draw.rect(surface, white, srect.inflate(4, 2))
            elif highlight_fill is not None:
                pygame.draw.rect(surface, highlight_fill, srect.inflate(4, 2))
            if box_selected:
                pygame.draw.rect(surface, white, srect.inflate(4, 2), 1)
            surface.blit(surf, srect)
            return srect

        def draw_triangle(box: pygame.Rect, direction: str, flash_key: str) -> None:
            f = flashing(flash_key)
            color = (0, 0, 0) if f else cyan
            cx, cy = box.centerx, box.centery
            w = min(16, box.width // 3)
            h = min(12, box.height // 3)
            if direction == "up":
                pts = [(cx, cy - h), (cx - w, cy + h), (cx + w, cy + h)]
            else:
                pts = [(cx, cy + h), (cx - w, cy - h), (cx + w, cy - h)]
            if f:
                pygame.draw.rect(surface, white, box.inflate(-box.width // 3, -box.height // 3))
            pygame.draw.polygon(surface, color, pts, 0)

        def draw_right_triangle(box: pygame.Rect, flash_key: str) -> None:
            f = flashing(flash_key)
            color = (0, 0, 0) if f else cyan
            cx, cy = box.centerx, box.centery
            w = min(16, box.width // 3)
            h = min(12, box.height // 3)
            pts = [
                (cx + w, cy),
                (cx - w, cy - h),
                (cx - w, cy + h),
            ]
            if f:
                pygame.draw.rect(surface, white, box.inflate(-box.width // 3, -box.height // 3))
            pygame.draw.polygon(surface, color, pts, 0)

        def draw_top_center(
            box: pygame.Rect,
            text: str,
            color: Tuple[int, int, int],
            *,
            size: int = 15,
            flash_key: Optional[str] = None,
            box_selected: bool = False,
        ) -> pygame.Rect:
            font = get_font(size)
            is_flash = flashing(flash_key)
            draw_color = (0, 0, 0) if is_flash else color
            surf = font.render(text, True, draw_color)
            srect = surf.get_rect(centerx=box.centerx)
            srect.top = box.top + 2
            if is_flash:
                pygame.draw.rect(surface, white, srect.inflate(4, 2))
            if box_selected:
                pygame.draw.rect(surface, white, srect.inflate(4, 2), 1)
            surface.blit(surf, srect)
            return srect

        def draw_center_lines(
            box: pygame.Rect,
            lines: List[Tuple[str, Tuple[int, int, int]]],
            *,
            size: int = 16,
            flash_key: Optional[str] = None,
        ) -> None:
            font = get_font(size)
            is_flash = flashing(flash_key)
            rendered = []
            for txt, col in lines:
                draw_col = (0, 0, 0) if is_flash else col
                rendered.append(font.render(txt, True, draw_col))
            total_h = sum(s.get_height() for s in rendered) + max(0, len(rendered) - 1)
            y = box.centery - total_h // 2
            rects: List[pygame.Rect] = []
            for surf in rendered:
                r = surf.get_rect(centerx=box.centerx)
                r.y = y
                rects.append(r)
                y += surf.get_height() + 1
            if is_flash and len(rects) > 0:
                flash_r = rects[0].copy()
                for rr in rects[1:]:
                    flash_r.union_ip(rr)
                pygame.draw.rect(surface, white, flash_r.inflate(4, 2))
            for surf, rr in zip(rendered, rects):
                surface.blit(surf, rr)

        def scratch(field: str, width: int) -> str:
            value = "".join(ch for ch in str(state.get(f"{field}_input", "")) if ch.isdigit())[-width:]
            slots = list("_" * width)
            for i, ch in enumerate(value):
                slots[i] = ch
            return f"{''.join(slots)} \u2190"

        def scratch_text(field: str, width: int, *, grouped: bool = False) -> str:
            value = str(state.get(f"{field}_input", "") or "").upper()[-width:]
            slots = list("_" * width)
            for i, ch in enumerate(value):
                slots[i] = ch
            out = "".join(slots)
            if grouped and len(out) == 8:
                out = f"{out[:4]} {out[4:]}"
            return f"{out} \u2190"

        def render_iff_keypad() -> None:
            keypad_specs = [
                ("A4", "KP_1", "1"),
                ("B4", "KP_2", "ABC\n2"),
                ("C4", "KP_3", "DEF\n3"),
                ("A5", "KP_4", "GHI\n4"),
                ("B5", "KP_5", "JKL\n5"),
                ("C5", "KP_6", "MNO\n6"),
                ("A6", "KP_7", "PQRS\n7"),
                ("B6", "KP_8", "TUV"),
                ("C6", "KP_9", "WXYZ"),
                ("A7", "KP_RIGHT", ""),
                ("B7", "KP_0", "0"),
                ("C7", "KP_BACK", "BACK"),
            ]
            for cell, flash_key, text in keypad_specs:
                box = cell_rect(cell)
                if flash_key == "KP_RIGHT":
                    draw_right_triangle(box, flash_key)
                    continue
                btn = ButtonState(
                    button_id=f"IFF_{flash_key}",
                    button_type=ButtonType.MOMENTARY_SINGLE,
                    text=text,
                    h_align="center",
                    v_align="center",
                    font_size=14,
                    flash_until_ms=flash_until_ms_for(flash_key),
                )
                render_button(surface, box, btn, get_font, now_ms)

        if bool(state.get("a2_menu_open", False)) and not e7_subpage_open and (not cm_fail_iff_active):
            options = ["OFF", "ON"]
            selected_idx = 1 if bool(state.get("mode45_enabled", False)) else 0
            slots = ["A1", "B1"]
            for idx, opt in enumerate(options):
                box = cell_rect(slots[idx])
                key = f"IFF_A2_OPT_{idx}"
                selected_opt = idx == selected_idx
                draw_line_bottom(
                    box,
                    2,
                    str(opt),
                    white if selected_opt else cyan,
                    box_selected=selected_opt,
                    flash_key=key,
                )
            return

        def draw_single(
            cell: str,
            text: str,
            on: bool,
            flash_key: Optional[str] = None,
            *,
            enabled: bool = True,
        ) -> None:
            box = cell_rect(cell)
            btn = ButtonState(
                button_id=f"IFF_{cell}",
                button_type=ButtonType.MOMENTARY_SINGLE,
                text=text,
                enabled=enabled,
                is_single_function=True,
                is_on=bool(on),
                h_align="center",
                v_align="center",
                font_size=14,
                flash_until_ms=flash_until_ms_for(flash_key or ""),
            )
            render_button(surface, box, btn, get_font, now_ms)

        def draw_gol(
            cell: str,
            label: str,
            value: str,
            flash_key: Optional[str] = None,
            *,
            enabled: bool = True,
        ) -> None:
            box = cell_rect(cell)
            btn = ButtonState(
                button_id=f"IFF_{cell}",
                button_type=ButtonType.GOL,
                enabled=enabled,
                function_label=label,
                options=[value],
                selected_index=0,
                h_align="center",
                v_align="center",
                font_size=14,
                flash_until_ms=flash_until_ms_for(flash_key or ""),
            )
            render_button(surface, box, btn, get_font, now_ms)

        def draw_double(
            cell: str,
            label: str,
            options: List[str],
            selected_idx: int,
            flash_key: Optional[str] = None,
            *,
            enabled: bool = True,
        ) -> None:
            box = cell_rect(cell)
            btn = ButtonState(
                button_id=f"IFF_{cell}",
                button_type=ButtonType.DOUBLE_FUNCTION,
                enabled=enabled,
                function_label=label,
                options=[str(x) for x in options],
                selected_index=max(0, min(len(options) - 1, int(selected_idx))) if len(options) > 0 else 0,
                h_align="center",
                v_align="center",
                font_size=14,
                flash_until_ms=flash_until_ms_for(flash_key or ""),
            )
            render_button(surface, box, btn, get_font, now_ms)

        def draw_page(
            cell: str,
            text: str,
            flash_key: Optional[str] = None,
            *,
            enabled: bool = True,
        ) -> None:
            box = cell_rect(cell)
            btn = ButtonState(
                button_id=f"IFF_{cell}",
                button_type=ButtonType.PAGE_ACCESS,
                enabled=enabled,
                text=text,
                h_align="center",
                v_align="center",
                font_size=14,
                flash_until_ms=flash_until_ms_for(flash_key or ""),
            )
            render_button(surface, box, btn, get_font, now_ms)

        def draw_data(
            cell: str,
            field: str,
            width: int,
            label: str,
            default_value: str,
            *,
            enabled: bool = True,
        ) -> None:
            box = cell_rect(cell)
            selected = enabled and (str(state.get("selected_field", "") or "") == field)
            if selected:
                draw_line_bottom(box, 1, scratch(field, width), white, box_selected=True, flash_key=cell)
            row_color = cyan if enabled else gray
            draw_line_bottom(box, 2, label, row_color, flash_key=cell)
            value = str(state.get(field, default_value))
            value = "".join(ch for ch in value if ch.isdigit())[-width:].rjust(width, "0")
            draw_line_bottom(box, 3, value, white if enabled else gray, flash_key=cell)

        ant_opts = state.get("antenna_options", ["NORM"])
        if not isinstance(ant_opts, list) or len(ant_opts) == 0:
            ant_opts = ["NORM"]
        ant_opts = [str(x).upper() for x in ant_opts]
        try:
            ant_idx = int(state.get("antenna_idx", 0))
        except Exception:
            ant_idx = 0
        ant_idx = max(0, min(len(ant_opts) - 1, ant_idx))
        ant_text = str(ant_opts[ant_idx])

        mode_s_opts = state.get("mode_s_options", ["ELS", "EHS"])
        if not isinstance(mode_s_opts, list) or len(mode_s_opts) < 2:
            mode_s_opts = ["ELS", "EHS"]
        mode_s_opts = [str(x).upper() for x in mode_s_opts[:2]]
        try:
            mode_s_idx = int(state.get("mode_s_idx", 0))
        except Exception:
            mode_s_idx = 0
        mode_s_idx = max(0, min(len(mode_s_opts) - 1, mode_s_idx))

        mode5_level_opts = state.get("mode5_level_options", ["L2", "L1"])
        if not isinstance(mode5_level_opts, list) or len(mode5_level_opts) < 2:
            mode5_level_opts = ["L2", "L1"]
        mode5_level_opts = [str(x).upper() for x in mode5_level_opts[:2]]
        try:
            mode5_level_idx = int(state.get("mode5_level_idx", 0))
        except Exception:
            mode5_level_idx = 0
        mode5_level_idx = max(0, min(len(mode5_level_opts) - 1, mode5_level_idx))

        addr_fmt_opts = state.get("mode_s_addr_format_options", ["OCTAL", "HEX"])
        if not isinstance(addr_fmt_opts, list) or len(addr_fmt_opts) < 2:
            addr_fmt_opts = ["OCTAL", "HEX"]
        addr_fmt_opts = [str(x).upper() for x in addr_fmt_opts[:2]]
        try:
            addr_fmt_idx = int(state.get("mode_s_addr_format_idx", 0))
        except Exception:
            addr_fmt_idx = 0
        addr_fmt_idx = max(0, min(len(addr_fmt_opts) - 1, addr_fmt_idx))
        addr_fmt = addr_fmt_opts[addr_fmt_idx]

        def mode_s_addr_value() -> str:
            raw = str(state.get("mode_s_addr", "37777777")).upper()
            if addr_fmt == "HEX":
                chars = [ch for ch in raw if ch.isdigit() or ("A" <= ch <= "F")]
                val = "".join(chars)[-8:].rjust(8, "0")
            else:
                chars = [ch for ch in raw if ch in "01234567"]
                val = "".join(chars)[-8:].rjust(8, "0")
            return f"{val[:4]} {val[4:]}"

        if e7_subpage_open and (not cm_fail_iff_active):
            def merged_cells(left_cell: str, right_cell: str) -> pygame.Rect:
                return cell_rect(left_cell).union(cell_rect(right_cell))

            selected_field = str(state.get("selected_field", "") or "")
            draw_center_lines(
                cell_rect("A1"),
                [("M5 PIN", cyan), (str(state.get("m5_pin", "37777")), white)],
                flash_key="A1",
            )
            draw_center_lines(
                cell_rect("B1"),
                [("NATLORG", cyan), (str(state.get("natlorg", "37777")), white)],
                flash_key="B1",
            )

            draw_double("A2", "MODE S", addr_fmt_opts, addr_fmt_idx, "A2")

            mode_s_addr_box = merged_cells("B2", "C2")
            if selected_field == "mode_s_addr":
                draw_line_bottom(mode_s_addr_box, 1, scratch_text("mode_s_addr", 8, grouped=True), white, box_selected=True, flash_key="BC2")
            draw_line_bottom(mode_s_addr_box, 2, "MODE S ADDR", cyan, flash_key="BC2")
            draw_line_bottom(mode_s_addr_box, 3, mode_s_addr_value(), white, flash_key="BC2")

            mode_s_acid_box = merged_cells("D2", "E2")
            if selected_field == "mode_s_acid":
                draw_line_bottom(mode_s_acid_box, 1, scratch_text("mode_s_acid", 7), white, box_selected=True, flash_key="DE2")
            draw_line_bottom(mode_s_acid_box, 2, "MODE S AC ID", cyan, flash_key="DE2")
            draw_line_bottom(mode_s_acid_box, 3, str(state.get("mode_s_acid", "KNIGHT1")).upper(), white, flash_key="DE2")

            mode_s_perm_box = merged_cells("B3", "C3")
            draw_center_lines(
                mode_s_perm_box,
                [
                    ("MODE S PERM", (0, 255, 0)),
                    ("ADDRESS", (0, 255, 0)),
                    (str(state.get("mode_s_perm_address", "12345677")), (0, 255, 0)),
                ],
                flash_key="BC3",
            )

            draw_page("E8", "<IFF", "E8")

            if selected_field in {"mode_s_addr", "mode_s_acid"}:
                render_iff_keypad()
            return

        popup_enabled = not cm_fail_iff_active
        draw_gol("A1", "IFF MODE", current_mode, "A1", enabled=popup_enabled)
        iff_master_mode_off = current_mode == "OFF"
        d1_enabled = (not iff_master_mode_off) and popup_enabled
        d2_enabled = (not iff_master_mode_off) and popup_enabled
        d3_enabled = (not iff_master_mode_off) and (not mode_c_degd_active) and popup_enabled
        d4_enabled = (not iff_master_mode_off) and (not mode_c_degd_active) and popup_enabled
        d5_enabled = (not iff_master_mode_off) and popup_enabled
        d6_enabled = (not iff_master_mode_off) and popup_enabled
        d7_enabled = (not iff_master_mode_off) and popup_enabled
        e1_enabled = d1_enabled and bool(state.get("mode1_enabled", True))
        e2_enabled = d2_enabled and bool(state.get("mode2_enabled", True))
        e3_enabled = d3_enabled and bool(state.get("mode3ac_on", True))
        ident_box = merged_bc(1)
        ident_on = int(state.get("ident_until_ms", 0)) > now_ms
        ident_flash = flash_until_ms_for("B1", "C1")
        ident_btn = ButtonState(
            button_id="IFF_B1C1",
            button_type=ButtonType.MOMENTARY_SINGLE,
            text="IDENT",
            enabled=popup_enabled,
            is_single_function=True,
            is_on=ident_on,
            h_align="center",
            v_align="center",
            font_size=14,
            flash_until_ms=ident_flash,
        )
        render_button(surface, ident_box, ident_btn, get_font, now_ms)
        draw_single("D1", "MODE 1", bool(state.get("mode1_enabled", True)), "D1", enabled=d1_enabled)
        draw_data("E1", "mode1", 2, "MODE 1", "61", enabled=e1_enabled)

        draw_gol("A2", "M45 MON", "ON" if bool(state.get("mode45_enabled", False)) else "OFF", "A2", enabled=popup_enabled)
        draw_gol("B2", "ANTENNA", ant_text, "B2", enabled=popup_enabled)
        draw_single("C2", "MODE 5\nSQUIT", bool(state.get("mode5_squit_on", False)), "C2", enabled=popup_enabled)
        draw_single("D2", "MODE 2", bool(state.get("mode2_enabled", True)), "D2", enabled=d2_enabled)
        draw_data("E2", "mode2", 4, "MODE 2", "2241", enabled=e2_enabled)

        draw_single("A3", "TEST", bool(state.get("test_on", False)), "A3", enabled=popup_enabled)
        draw_single("B3", "MODE S\nEXTEND\nSQUIT", bool(state.get("mode_s_extend_squit_on", False)), "B3", enabled=popup_enabled)
        draw_double("C3", "MODE S", mode_s_opts, mode_s_idx, "C3", enabled=popup_enabled)
        draw_single("D3", "MODE\n3/A-C", bool(state.get("mode3ac_on", True)), "D3", enabled=d3_enabled)
        draw_data("E3", "mode3a", 4, "MODE 3", "1200", enabled=e3_enabled)

        draw_single("D4", "MODE C\nALT\nCONTROL", bool(state.get("modec_enabled", True)), "D4", enabled=d4_enabled)
        draw_single("D5", "MODE 4", bool(state.get("mode4_sf_on", False)), "D5", enabled=d5_enabled)
        draw_single("D6", "MODE 5", bool(state.get("mode5_enabled", False)), "D6", enabled=d6_enabled)
        draw_single("D7", "MODE S", bool(state.get("mode_s_enabled", False)), "D7", enabled=d7_enabled)
        draw_double("E6", "MODE 5", mode5_level_opts, mode5_level_idx, "E6", enabled=popup_enabled)
        draw_page("E7", "M5/MS\nDATA>", "E7", enabled=popup_enabled)
        draw_page("D8", "INTG>", "D8", enabled=popup_enabled)
        draw_page("E8", "AUTO\nTIME>", "E8", enabled=popup_enabled)

        sel_field = str(state.get("selected_field", "") or "")
        if (
            (sel_field == "mode1" and e1_enabled)
            or (sel_field == "mode2" and e2_enabled)
            or (sel_field == "mode3a" and e3_enabled)
        ):
            render_iff_keypad()

        emergency_box = merged_bc(8)
        emergency_on = bool(state.get("emergency_on", False))
        emergency_cover_closed = bool(state.get("emergency_cover_closed", True))
        emergency_intermediate = (not emergency_cover_closed) and (not emergency_on)
        emergency_btn = ButtonState(
            button_id="IFF_B8C8",
            button_type=ButtonType.MOMENTARY_SINGLE,
            text="EMERGENCY",
            enabled=popup_enabled,
            is_single_function=True,
            is_on=emergency_on,
            h_align="center",
            v_align="center",
            font_size=14,
            flash_until_ms=flash_until_ms_for("B8", "C8"),
        )
        render_button(surface, emergency_box, emergency_btn, get_font, now_ms)
        if emergency_intermediate and popup_enabled:
            font = get_font(14)
            txt = font.render("EMERGENCY", True, (0, 0, 0))
            txt_rect = txt.get_rect(center=emergency_box.center)
            pygame.draw.rect(surface, cyan, txt_rect.inflate(4, 2))
            surface.blit(txt, txt_rect)
        if bool(state.get("emergency_cover_closed", True)) and popup_enabled:
            draw_hazard_stripe_border(
                surface,
                emergency_box.inflate(-2, -2),
                border_thickness=HAZARD_BORDER_THICKNESS,
                stripe_line_width=HAZARD_STRIPE_LINE_WIDTH,
                stripe_spacing=HAZARD_STRIPE_SPACING,
            )
        if bool(state.get("emergency_confirm_pending", False)):
            popup_w = max(1, int(round(4.25 * DPI)))
            popup_h = max(1, int(round(1.5 * DPI)))
            row2_center_y = rect.y + cell_h + (cell_h // 2)
            popup_rect = pygame.Rect(
                rect.centerx - (popup_w // 2),
                int(row2_center_y - (popup_h / 2)),
                popup_w,
                popup_h,
            )
            pygame.draw.rect(surface, cyan, popup_rect)
            pygame.draw.rect(surface, white, popup_rect, 1)
            popup_font = get_font(20)
            l1 = popup_font.render("CONFIRM", True, (0, 0, 0))
            l2 = popup_font.render("TX EMER IFF", True, (0, 0, 0))
            total_h = l1.get_height() + l2.get_height() + 4
            y = popup_rect.centery - (total_h // 2)
            r1 = l1.get_rect(centerx=popup_rect.centerx)
            r1.y = y
            y = r1.bottom + 4
            r2 = l2.get_rect(centerx=popup_rect.centerx)
            r2.y = y
            surface.blit(l1, r1)
            surface.blit(l2, r2)

        if a1_menu_open and (not e7_subpage_open) and (not cm_fail_iff_active):
            option_cells = ["B3", "C3", "D3", "B4", "C4", "D4"]
            used_cells = option_cells[: max(0, min(len(mode_options), len(option_cells)))]
            font = get_font(16)
            for idx, cell_name in enumerate(used_cells):
                box = cell_rect(cell_name)
                key = f"IFF_A1_OPT_{idx}"
                selected_opt = idx == mode_idx
                is_flash = flashing(key)
                surface.fill((0, 0, 0), box)
                pygame.draw.rect(surface, cyan, box, 1)
                text_color = (0, 0, 0) if is_flash else (white if selected_opt else cyan)
                txt = font.render(str(mode_options[idx]), True, text_color)
                tr = txt.get_rect(center=box.center)
                if is_flash:
                    pygame.draw.rect(surface, white, tr.inflate(4, 2))
                elif selected_opt:
                    pygame.draw.rect(surface, white, tr.inflate(6, 3), 1)
                surface.blit(txt, tr)

    def on_osb(self, label: str, context: FormatContext) -> bool:
        if label == "T1":
            context.request_vded(context.portal_index, "MENU")
            return True
        return False
