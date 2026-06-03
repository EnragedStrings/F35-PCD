from formats import *  # noqa: F401,F403


class CommFormat(FormatBase):
    name: str = "COMM"

    def render(self, surface, rect, is_primary: bool, context: FormatContext) -> None:
        if not is_primary:
            draw_centered_text(surface, rect, "COMM", "00FFFF", 14)
            return
        state = context.get_comm_state()
        now_ms = int(state.get("now_ms", 0))
        flash_until = state.get("flash_until", {})
        cols = 5
        rows = 8
        cell_w = rect.width // cols
        cell_h = rect.height // rows
        cyan = (0, 255, 255)
        white = (255, 255, 255)
        gray = (128, 128, 128)
        yellow = (255, 255, 0)
        green = (0, 255, 0)

        def cell_rect(cell_name: str) -> pygame.Rect:
            col = ord(cell_name[0]) - ord("A")
            row = int(cell_name[1:]) - 1
            return pygame.Rect(rect.x + col * cell_w, rect.y + row * cell_h, cell_w, cell_h)

        def merged_de(row_num: int) -> pygame.Rect:
            d = cell_rect(f"D{row_num}")
            e = cell_rect(f"E{row_num}")
            return d.union(e)

        # Base COMM grid with D/E row merges.
        pygame.draw.rect(surface, cyan, rect, 1)
        for i in (1, 2, 3):
            x = rect.x + i * cell_w
            pygame.draw.line(surface, cyan, (x, rect.top), (x, rect.bottom), 1)
        de_x = rect.x + 4 * cell_w
        merged_rows = {1, 2, 3, 5, 6}
        for r in range(1, rows + 1):
            if r in merged_rows:
                continue
            y0 = rect.y + (r - 1) * cell_h
            y1 = y0 + cell_h
            pygame.draw.line(surface, cyan, (de_x, y0), (de_x, y1), 1)
        for j in range(1, rows):
            y = rect.y + j * cell_h
            pygame.draw.line(surface, cyan, (rect.left, y), (rect.right, y), 1)

        def draw_line(
            box: pygame.Rect,
            line_no: int,
            text: str,
            color: Tuple[int, int, int],
            *,
            size: int = 17,
            box_selected: bool = False,
            align: str = "center",
            x_pad: int = 4,
            flash_key: Optional[str] = None,
        ) -> pygame.Rect:
            font = get_font(size)
            # Keep lines tighter than default layout.
            y1 = box.top + 2
            y2 = y1 + font.get_height() + 1
            y3 = y2 + font.get_height() + 1
            if y3 + font.get_height() > box.bottom - 1:
                # Fallback for small cells.
                if line_no <= 1:
                    y = box.top + 2
                elif line_no == 2:
                    y = box.centery - font.get_height() // 2
                else:
                    y = box.bottom - font.get_height() - 2
            else:
                y = y1 if line_no <= 1 else y2 if line_no == 2 else y3
            flashing = False
            if flash_key is not None and isinstance(flash_until, dict):
                try:
                    flashing = int(flash_until.get(flash_key, 0)) > now_ms
                except Exception:
                    flashing = False
            draw_color = (0, 0, 0) if flashing else color
            surf = font.render(text, True, draw_color)
            if align == "left":
                srect = surf.get_rect(left=box.left + x_pad)
            elif align == "right":
                srect = surf.get_rect(right=box.right - x_pad)
            else:
                srect = surf.get_rect(centerx=box.centerx)
            srect.y = y
            if flashing:
                pygame.draw.rect(surface, white, srect.inflate(4, 2))
            if box_selected:
                pygame.draw.rect(surface, white, srect.inflate(4, 2), 1)
            surface.blit(surf, srect)
            return srect

        def draw_line_bottom(
            box: pygame.Rect,
            line_no: int,
            text: str,
            color: Tuple[int, int, int],
            *,
            size: int = 17,
            box_selected: bool = False,
            align: str = "center",
            x_pad: int = 4,
            flash_key: Optional[str] = None,
            highlight_fill: Optional[Tuple[int, int, int]] = None,
        ) -> pygame.Rect:
            font = get_font(size)
            y3 = box.bottom - font.get_height() - 2
            y2 = y3 - font.get_height() - 1
            y1 = y2 - font.get_height() - 1
            y = y1 if line_no <= 1 else y2 if line_no == 2 else y3
            flashing = False
            if flash_key is not None and isinstance(flash_until, dict):
                try:
                    flashing = int(flash_until.get(flash_key, 0)) > now_ms
                except Exception:
                    flashing = False
            draw_color = (0, 0, 0) if flashing else color
            surf = font.render(text, True, draw_color)
            if align == "left":
                srect = surf.get_rect(left=box.left + x_pad)
            elif align == "right":
                srect = surf.get_rect(right=box.right - x_pad)
            else:
                srect = surf.get_rect(centerx=box.centerx)
            srect.y = y
            if flashing:
                pygame.draw.rect(surface, white, srect.inflate(4, 2))
            elif highlight_fill is not None:
                pygame.draw.rect(surface, highlight_fill, srect.inflate(4, 2))
            if box_selected:
                pygame.draw.rect(surface, white, srect.inflate(4, 2), 1)
            surface.blit(surf, srect)
            return srect

        def draw_gol_header(box: pygame.Rect, header: str, flash_key: Optional[str] = None) -> None:
            header_rect = draw_line_bottom(box, 1, header, green, flash_key=flash_key)
            pygame.draw.line(
                surface,
                green,
                (header_rect.left, header_rect.bottom + 1),
                (header_rect.right, header_rect.bottom + 1),
                1,
            )

        def vol_scratch(input_text: str) -> str:
            value = "".join(ch for ch in str(input_text) if ch.isdigit())[-2:]
            slots = list("__")
            for i, ch in enumerate(value):
                slots[i] = ch
            return f"{slots[0]} {slots[1]} \u2190"

        def freq_scratch(input_text: str) -> str:
            value = "".join(ch for ch in str(input_text) if ch.isdigit())[-6:]
            if len(value) == 0:
                body = "___.___"
            elif len(value) == 1:
                body = f"{value[0]}__.___"
            elif len(value) == 2:
                body = f"{value[0]}{value[1]}_.___"
            elif len(value) == 3:
                body = f"{value[0]}{value[1]}{value[2]}.___"
            elif len(value) == 4:
                body = f"{value[0]}{value[1]}{value[2]}.{value[3]}__"
            elif len(value) == 5:
                body = f"{value[0]}{value[1]}{value[2]}.{value[3]}{value[4]}_"
            else:
                body = f"{value[0]}{value[1]}{value[2]}.{value[3]}{value[4]}{value[5]}"
            return f"{body} \u2190"

        selected = str(state.get("selected_field", "") or "")
        bur_degd_active = bool(state.get("bur_degd_active", False))
        bur_fail_active = bool(state.get("bur_fail_active", False))
        asgn_radio = str(state.get("asgn_radio", "comb"))
        asgn_com_label = {
            "coma": "COM A",
            "comb": "COM B",
            "comc": "COM C",
            "comd": "COM D",
        }.get(asgn_radio, "COM B")
        curr_radio = str(asgn_radio).strip().lower()
        if curr_radio not in {"coma", "comb", "comc", "comd"}:
            curr_radio = "comb"
        curr_prof = _comm_profile_for_radio(state, curr_radio)
        gol_menu = str(state.get("gol_menu", "")).upper().strip()
        if gol_menu == "" and bool(state.get("asgn_menu_open", False)):
            gol_menu = "D4"

        if bool(state.get("audio_submenu_open", False)):
            # Standard COMM AUDIO grid (no D/E merged rows).
            pygame.draw.rect(surface, cyan, rect, 1)
            for i in range(1, cols):
                x = rect.x + i * cell_w
                pygame.draw.line(surface, cyan, (x, rect.top), (x, rect.bottom), 1)
            for j in range(1, rows):
                y = rect.y + j * cell_h
                pygame.draw.line(surface, cyan, (rect.left, y), (rect.right, y), 1)

            def _audio_scratch(raw_input: object) -> str:
                digits = "".join(ch for ch in str(raw_input) if ch.isdigit())[-2:]
                slots = ["_", "_"]
                for idx, ch in enumerate(digits):
                    slots[idx] = ch
                return f"{slots[0]}{slots[1]} \u2190"

            def _draw_audio_e_line(
                box: pygame.Rect,
                line_no: int,
                text: str,
                color: Tuple[int, int, int],
                flash_key: str,
                *,
                box_selected: bool = False,
            ) -> pygame.Rect:
                font = get_font(15)
                fh = font.get_height()
                total_h = (fh * 3) + 2
                start_y = box.centery - (total_h // 2)
                y = start_y + ((max(1, int(line_no)) - 1) * (fh + 1))
                flashing = False
                if isinstance(flash_until, dict):
                    try:
                        flashing = int(flash_until.get(flash_key, 0)) > now_ms
                    except Exception:
                        flashing = False
                draw_color = (0, 0, 0) if flashing else color
                surf = font.render(text, True, draw_color)
                srect = surf.get_rect(right=box.right - 6)
                srect.y = y
                if flashing:
                    pygame.draw.rect(surface, white, srect.inflate(4, 2))
                if box_selected:
                    pygame.draw.rect(surface, white, srect.inflate(4, 2), 1)
                surface.blit(surf, srect)
                return srect

            # C1/C2 momentary single-function.
            c1 = cell_rect("C1")
            c2 = cell_rect("C2")
            draw_line(c1, 1, "MUTE", cyan, size=15, align="center", flash_key="AUDIO_C1")
            draw_line(c1, 2, "ALL", cyan, size=15, align="center", flash_key="AUDIO_C1")
            draw_line(c2, 1, "UNMUTE", cyan, size=15, align="center", flash_key="AUDIO_C2")
            draw_line(c2, 2, "ALL", cyan, size=15, align="center", flash_key="AUDIO_C2")

            audio_rows: List[Tuple[int, str, str, str, str]] = [
                (1, "THRT", "THRT", "audio_thrt_on", "audio_thrt_vol"),
                (2, "WPN", "WPN", "audio_wpn_on", "audio_wpn_vol"),
                (3, "NAV AIDS", "NAVAID", "audio_navaid_on", "audio_navaid_vol"),
                (4, "ICAWS", "ICAWS", "audio_icaws_on", "audio_icaws_vol"),
                (5, "ICS", "ICS", "audio_ics_on", "audio_ics_vol"),
                (6, "VOX", "VOX", "audio_vox_on", "audio_vox_vol"),
                (7, "CKPT", "CKPT", "audio_ckpt_on", "audio_ckpt_vol"),
            ]
            for row_num, d_label, e_title, toggle_key, vol_key in audio_rows:
                d_box = cell_rect(f"D{row_num}")
                e_box = cell_rect(f"E{row_num}")
                on = bool(state.get(toggle_key, True))
                d_color = white if on else gray
                e_color = cyan if on else gray
                draw_line(
                    d_box,
                    2,
                    d_label,
                    d_color,
                    size=15,
                    align="center",
                    box_selected=on,
                    flash_key=f"AUDIO_D{row_num}",
                )
                vol_value = max(0, min(99, int(state.get(vol_key, 0) or 0)))
                if selected == vol_key and on:
                    _draw_audio_e_line(
                        e_box,
                        1,
                        _audio_scratch(state.get(f"{vol_key}_input", "")),
                        white,
                        flash_key=f"AUDIO_E{row_num}",
                        box_selected=True,
                    )
                _draw_audio_e_line(
                    e_box,
                    2,
                    e_title,
                    e_color,
                    flash_key=f"AUDIO_E{row_num}",
                )
                _draw_audio_e_line(
                    e_box,
                    3,
                    f"VOL {vol_value}",
                    e_color,
                    flash_key=f"AUDIO_E{row_num}",
                )
                if on:
                    font_sz = get_font(15)
                    total_h = (font_sz.get_height() * 3) + 2
                    y1 = e_box.centery - (total_h // 2)
                    y2 = y1 + font_sz.get_height() + 1
                    y3 = y2 + font_sz.get_height() + 1
                    cy2 = y2 + (font_sz.get_height() // 2)
                    cy3 = y3 + (font_sz.get_height() // 2)
                    left_x = e_box.left + 10
                    up = [(left_x, cy2 - 7), (left_x - 6, cy2 + 3), (left_x + 6, cy2 + 3)]
                    down = [(left_x, cy3 + 7), (left_x - 6, cy3 - 3), (left_x + 6, cy3 - 3)]
                    pygame.draw.polygon(surface, cyan, up)
                    pygame.draw.polygon(surface, cyan, down)

            e8 = cell_rect("E8")
            draw_line(e8, 1, "<COM", cyan, size=15, align="center", flash_key="AUDIO_E8")

            # Numeric keypad A4-C7, with A7/A8 INC/DEC symbols.
            keypad_labels = {
                "A4": ("1", "AUDIO_KP_1"),
                "B4": ("2", "AUDIO_KP_2"),
                "C4": ("3", "AUDIO_KP_3"),
                "A5": ("4", "AUDIO_KP_4"),
                "B5": ("5", "AUDIO_KP_5"),
                "C5": ("6", "AUDIO_KP_6"),
                "A6": ("7", "AUDIO_KP_7"),
                "B6": ("8", "AUDIO_KP_8"),
                "C6": ("9", "AUDIO_KP_9"),
                "B7": ("0", "AUDIO_KP_0"),
                "C7": ("BACK", "AUDIO_KP_BACK"),
            }
            kfont = get_font(17)
            for cell, (text, flash_key) in keypad_labels.items():
                krect = cell_rect(cell)
                flashing = isinstance(flash_until, dict) and int(flash_until.get(flash_key, 0)) > now_ms
                surf = kfont.render(text, True, (0, 0, 0) if flashing else cyan)
                srect = surf.get_rect(center=krect.center)
                if flashing:
                    pygame.draw.rect(surface, white, srect.inflate(4, 2))
                surface.blit(surf, srect)

            a7 = cell_rect("A7")
            a8 = cell_rect("A8")
            up_flashing = isinstance(flash_until, dict) and int(flash_until.get("AUDIO_KP_UP", 0)) > now_ms
            down_flashing = isinstance(flash_until, dict) and int(flash_until.get("AUDIO_KP_DOWN", 0)) > now_ms
            up = [
                (a7.centerx, a7.centery - 8),
                (a7.centerx - 7, a7.centery + 5),
                (a7.centerx + 7, a7.centery + 5),
            ]
            down = [
                (a8.centerx, a8.centery + 8),
                (a8.centerx - 7, a8.centery - 5),
                (a8.centerx + 7, a8.centery - 5),
            ]
            if up_flashing:
                pygame.draw.rect(surface, white, a7.inflate(-a7.width // 3, -a7.height // 3))
            if down_flashing:
                pygame.draw.rect(surface, white, a8.inflate(-a8.width // 3, -a8.height // 3))
            pygame.draw.polygon(surface, (0, 0, 0) if up_flashing else cyan, up)
            pygame.draw.polygon(surface, (0, 0, 0) if down_flashing else cyan, down)
            return

        def _safe_int(value: object, default: Optional[int] = None) -> Optional[int]:
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        def _draw_comm_gol_popup(menu_token: str) -> None:
            option_cells = ["B3", "C3", "D3", "B4", "C4", "D4"]
            menu_options: List[str] = []
            selected_idx = 0
            option_prefix = ""
            if menu_token == "D4":
                # Keep ASGN GOL off keypad rows now that keypad stays visible.
                option_cells = ["B1", "C1", "D1", "B2", "C2", "D2"]
                menu_options = ["HIGH VHF", "LOW VHF", "UHF", "AM"]
                selected_idx = {"coma": 0, "comb": 1, "comc": 2, "comd": 3}.get(curr_radio, 1)
                option_prefix = "ASGN_OPT_"
            elif menu_token == "D7":
                menu_options = ["AUTO", "OFF"]
                selected_idx = 0 if bool(state.get("d7_auto", True)) else 1
                option_prefix = "D7_OPT_"
            elif menu_token == "E7":
                menu_options = ["AUTO", "OFF"]
                selected_idx = 0 if bool(state.get("e7_auto", True)) else 1
                option_prefix = "E7_OPT_"
            elif menu_token == "C8":
                menu_options = ["ON", "OFF"]
                selected_idx = 0 if bool(curr_prof.get("aj_on", False)) else 1
                option_prefix = "C8_OPT_"
            elif menu_token == "D8":
                menu_options = ["ON", "OFF"]
                selected_idx = 0 if bool(curr_prof.get("secure_on", False)) else 1
                option_prefix = "D8_OPT_"

            used_cells = option_cells[: max(0, min(len(menu_options), len(option_cells)))]
            for cell_name in used_cells:
                box = cell_rect(cell_name)
                surface.fill((0, 0, 0), box)
                pygame.draw.rect(surface, cyan, box, 1)

            font = get_font(16)
            for idx, opt in enumerate(menu_options):
                if idx >= len(used_cells):
                    break
                box = cell_rect(used_cells[idx])
                is_sel = idx == int(selected_idx)
                flash_key = f"{option_prefix}{idx}" if option_prefix != "" else None
                flashing = False
                if flash_key is not None and isinstance(flash_until, dict):
                    try:
                        flashing = int(flash_until.get(flash_key, 0)) > now_ms
                    except Exception:
                        flashing = False
                color = (0, 0, 0) if flashing else (white if is_sel else cyan)
                txt = font.render(str(opt), True, color)
                tr = txt.get_rect(center=box.center)
                if flashing:
                    pygame.draw.rect(surface, white, tr.inflate(4, 2))
                elif is_sel:
                    pygame.draw.rect(surface, white, tr.inflate(6, 3), 1)
                surface.blit(txt, tr)

        # A-column
        a_cells = [("A1", "tone_on", "TONE"), ("A2", "mute_on", "MUTE"), ("A3", "sqlch_on", "SQLCH")]
        for cell, key, label in a_cells:
            box = cell_rect(cell)
            on = bool(state.get(key, False))
            color = white if on else cyan
            draw_line_bottom(box, 2, label, color, box_selected=on, flash_key=cell)
            draw_line_bottom(box, 3, asgn_com_label, green, flash_key=cell)

        # B-column with selectable off state.
        radios = [
            ("A", "B1", "coma_freq", bool(state.get("coma_on", True))),
            ("B", "B2", "comb_freq", bool(state.get("comb_on", True))),
            ("C", "B3", "comc_freq", bool(state.get("comc_on", True))),
        ]
        for r_name, cell_name, key, on in radios:
            col = cyan if on else gray
            freq = str(state.get(key, "000.000"))
            box = cell_rect(cell_name)
            draw_line_bottom(box, 1, f"COM {r_name}", col, flash_key=cell_name)
            draw_line_bottom(box, 2, "PREV", col, flash_key=cell_name)
            draw_line_bottom(box, 3, freq, col, flash_key=cell_name)

        # C-column data entry labels.
        c_rows = [("C1", "vola", "VOL A"), ("C2", "volb", "VOL B"), ("C3", "volc", "VOL C")]
        for cell, field, label in c_rows:
            box = cell_rect(cell)
            is_selected = selected == field
            if is_selected:
                top = vol_scratch(str(state.get(f"{field}_input", "")))
                draw_line_bottom(box, 1, top, white, box_selected=True, flash_key=cell)
            draw_line_bottom(box, 2, label, cyan, flash_key=cell)
            draw_line_bottom(box, 3, str(int(state.get(field, 5))), cyan, flash_key=cell)

        # D4 GOL and E4 volume data-entry.
        d4 = cell_rect("D4")
        draw_gol_header(d4, "ASGN", flash_key="D4")
        draw_line_bottom(d4, 2, str(state.get("asgn_mode", "LOW VHF")), cyan, flash_key="D4")
        asgn_freq = {
            "coma": state.get("coma_freq", "000.000"),
            "comb": state.get("comb_freq", "000.000"),
            "comc": state.get("comc_freq", "000.000"),
            "comd": state.get("comd_freq", "000.000"),
        }.get(asgn_radio, state.get("comb_freq", "000.000"))
        draw_line_bottom(d4, 3, str(asgn_freq), cyan, flash_key="D4")

        e4 = cell_rect("E4")
        e4_disabled = bool(bur_fail_active)
        if selected == "vold" and (not e4_disabled):
            top = vol_scratch(str(state.get("vold_input", "")))
            draw_line_bottom(e4, 1, top, white, box_selected=True, flash_key="E4")
        e4_color = gray if e4_disabled else cyan
        draw_line_bottom(e4, 2, "VOL D", e4_color, flash_key="E4")
        draw_line_bottom(e4, 3, str(int(state.get("vold", 5))), e4_color, flash_key="E4")

        # D/E merged rows.
        de_rows = [
            (1, "A", "coma", "coma_freq", bool(state.get("coma_on", True)), _safe_int(state.get("preset_a"), None)),
            (2, "B", "comb", "comb_freq", bool(state.get("comb_on", True)), _safe_int(state.get("preset_b"), None)),
            (3, "C", "comc", "comc_freq", bool(state.get("comc_on", True)), _safe_int(state.get("preset_c"), None)),
            (5, "D", "comd", "comd_freq", bool(state.get("comd_on", True)), _safe_int(state.get("preset_d"), None)),
        ]
        for row_num, radio, field, freq_key, on, preset in de_rows:
            m = merged_de(row_num)
            row_key = f"DE{row_num}"
            row_disabled = bool(row_num == 5 and bur_fail_active)
            mode_indicator = _comm_band_indicator_for_mode(_comm_mode_for_radio(state, field))
            if row_num in {1, 2, 3}:
                mode_indicator = _comm_cni_class_for_radio(field, mode_indicator).strip().upper()
            freq_value = str(state.get(freq_key, "000.000"))
            preset_number = _comm_preset_number_for_freq(state, field, freq_value)
            preset_display: Optional[int] = None
            try:
                if preset is not None and int(preset) > 0:
                    preset_display = int(preset)
            except Exception:
                preset_display = None
            if preset_display is not None:
                l2_value = f"{preset_display} {freq_value}"
            else:
                l2_value = freq_value
            left_lbl, mid_lbl, right_lbl = _comm_row_label_parts(state, field, freq_value, preset_number)
            line3_suffix = _comm_compose_row_label(left_lbl, mid_lbl, right_lbl)
            line3_main = f"COM {radio}"
            line3_text = line3_main if line3_suffix == "" else f"{line3_main} {line3_suffix}"
            line3_font = get_font(15)
            line3_text_w = line3_font.size(line3_text)[0]
            line2_x_pad = max(0, (m.width - line3_text_w) // 2)
            if selected == field and (not row_disabled):
                top = freq_scratch(str(state.get(f"{field}_input", "")))
                draw_line_bottom(m, 1, top, white, size=15, box_selected=True, flash_key=row_key)
            if on:
                l2 = l2_value
                line2_color = gray if row_disabled else cyan
                if row_num == 5 and (not row_disabled) and bur_degd_active:
                    line3_color = yellow
                else:
                    line3_color = gray if row_disabled else cyan
            else:
                l2 = f"COM {radio} OFF"
                line2_color = gray if row_disabled else cyan
                line3_color = gray if row_disabled else cyan
            l2_rect = draw_line_bottom(m, 2, l2, line2_color, size=15, align="left", x_pad=line2_x_pad, flash_key=row_key)
            if on and mode_indicator != "":
                s_surf = get_font(15).render(mode_indicator, True, gray if row_disabled else green)
                s_rect = s_surf.get_rect()
                s_rect.left = l2_rect.right + max(1, get_font(15).size(" ")[0])
                s_rect.y = l2_rect.y
                if isinstance(flash_until, dict) and int(flash_until.get(row_key, 0)) > now_ms:
                    pygame.draw.rect(surface, white, s_rect.inflate(3, 2))
                    s_surf = get_font(15).render(mode_indicator, True, (0, 0, 0))
                surface.blit(s_surf, s_rect)
            if on:
                l3_rect = draw_line_bottom(m, 3, line3_text, line3_color, size=15, align="center", flash_key=row_key)
            else:
                l3_rect = l2_rect
            if selected == field and (not row_disabled):
                up_tri = [
                    (m.left + 10, l2_rect.centery - 7),
                    (m.left + 3, l2_rect.centery + 3),
                    (m.left + 17, l2_rect.centery + 3),
                ]
                pygame.draw.polygon(surface, cyan, up_tri)
                if on:
                    down_tri = [
                        (m.left + 10, l3_rect.centery + 7),
                        (m.left + 3, l3_rect.centery - 3),
                        (m.left + 17, l3_rect.centery - 3),
                    ]
                    pygame.draw.polygon(surface, cyan, down_tri)

        # D/E6 guard with hazard border.
        de6 = merged_de(6)
        if bool(state.get("guard_cover_closed", True)):
            draw_hazard_stripe_border(
                surface,
                de6,
                border_thickness=10,
                stripe_line_width=HAZARD_STRIPE_LINE_WIDTH,
                stripe_spacing=HAZARD_STRIPE_SPACING,
                colors=((0, 0, 0), (255, 255, 0)),
            )
        guard_on = bool(state.get("guard_on", False))
        guard_cover_closed = bool(state.get("guard_cover_closed", True))
        guard_intermediate = (not guard_cover_closed) and (not guard_on)
        draw_line_bottom(
            de6,
            2,
            "GUARD",
            (255, 255, 255) if guard_on else ((0, 0, 0) if guard_intermediate else cyan),
            flash_key="DE6",
            box_selected=guard_on,
            highlight_fill=(cyan if guard_intermediate else None),
        )
        if bool(state.get("guard_confirm_pending", False)):
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
            l2 = popup_font.render("SWITCH TO GUARD", True, (0, 0, 0))
            total_h = l1.get_height() + l2.get_height() + 4
            y = popup_rect.centery - (total_h // 2)
            r1 = l1.get_rect(centerx=popup_rect.centerx)
            r1.y = y
            y = r1.bottom + 4
            r2 = l2.get_rect(centerx=popup_rect.centerx)
            r2.y = y
            surface.blit(l1, r1)
            surface.blit(l2, r2)

        # D7/E7/C8/D8 GOLs and page access buttons.
        d7 = cell_rect("D7")
        e7 = cell_rect("E7")
        b8 = cell_rect("B8")
        c8 = cell_rect("C8")
        d8 = cell_rect("D8")
        e8 = cell_rect("E8")
        curr_radio = str(state.get("asgn_radio", "comb")).strip().lower()
        if curr_radio not in {"coma", "comb", "comc", "comd"}:
            curr_radio = "comb"
        curr_prof = _comm_profile_for_radio(state, curr_radio)
        draw_gol_header(d7, "MOD", flash_key="D7")
        draw_line_bottom(d7, 2, "AUTO" if bool(state.get("d7_auto", True)) else "OFF", cyan, flash_key="D7")
        draw_gol_header(e7, "ANTENNA", flash_key="E7")
        draw_line_bottom(e7, 2, "AUTO" if bool(state.get("e7_auto", True)) else "OFF", cyan, flash_key="E7")
        draw_line(b8, 1, "AUDIO>", cyan, size=15, align="center", flash_key="B8")
        draw_gol_header(c8, "AJ", flash_key="C8")
        draw_line_bottom(c8, 2, "ON" if bool(curr_prof.get("aj_on", False)) else "OFF", cyan, flash_key="C8")
        draw_gol_header(d8, "SECURE", flash_key="D8")
        draw_line_bottom(d8, 2, "ON" if bool(curr_prof.get("secure_on", False)) else "OFF", cyan, flash_key="D8")
        draw_line(e8, 1, "COM", cyan, size=15, align="left", x_pad=6, flash_key="E8")
        draw_line(e8, 2, "SETUP>", cyan, size=15, align="left", x_pad=6, flash_key="E8")

        if gol_menu in {"D4", "D7", "E7", "C8", "D8"}:
            _draw_comm_gol_popup(gol_menu)

        # Numeric keypad stays available while COMM GOLs are open.
        keypad_labels = {
            "A4": "1", "B4": "2", "C4": "3",
            "A5": "4", "B5": "5", "C5": "6",
            "A6": "7", "B6": "8", "C6": "9",
            "B7": "0", "C7": "BACK",
        }
        font = get_font(17)
        for cell, text in keypad_labels.items():
            c_rect = cell_rect(cell)
            k = f"KP_{text}" if text.isdigit() else "KP_BACK"
            if cell == "C7":
                k = "KP_BACK"
            if cell == "B7":
                k = "KP_0"
            flashing = isinstance(flash_until, dict) and int(flash_until.get(k, 0)) > now_ms
            surf = font.render(text, True, (0, 0, 0) if flashing else cyan)
            srect = surf.get_rect(center=c_rect.center)
            if flashing:
                pygame.draw.rect(surface, white, srect.inflate(4, 2))
            surface.blit(surf, srect)
        a7 = cell_rect("A7")
        a8 = cell_rect("A8")
        up_flashing = isinstance(flash_until, dict) and int(flash_until.get("KP_UP", 0)) > now_ms
        down_flashing = isinstance(flash_until, dict) and int(flash_until.get("KP_DOWN", 0)) > now_ms
        up = [
            (a7.centerx, a7.centery - 8),
            (a7.centerx - 7, a7.centery + 5),
            (a7.centerx + 7, a7.centery + 5),
        ]
        down = [
            (a8.centerx, a8.centery + 8),
            (a8.centerx - 7, a8.centery - 5),
            (a8.centerx + 7, a8.centery - 5),
        ]
        if up_flashing:
            pygame.draw.rect(surface, white, a7.inflate(-a7.width // 3, -a7.height // 3))
        if down_flashing:
            pygame.draw.rect(surface, white, a8.inflate(-a8.width // 3, -a8.height // 3))
        pygame.draw.polygon(surface, (0, 0, 0) if up_flashing else cyan, up)
        pygame.draw.polygon(surface, (0, 0, 0) if down_flashing else cyan, down)

    def on_osb(self, label: str, context: FormatContext) -> bool:
        if label == "T1":
            context.request_vded(context.portal_index, "MENU")
            return True
        return False
