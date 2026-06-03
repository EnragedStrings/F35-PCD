from formats import *  # noqa: F401,F403


class NavMenuFormat(FormatBase):
    name: str = "NAVMENU"

    def render(self, surface, rect, is_primary: bool, context: FormatContext) -> None:
        if not is_primary:
            draw_centered_text(surface, rect, "NAVMENU", "00FFFF", 14)
            return
        state = NAV_STATE
        now_ms = int(state.get("now_ms", 0))
        flash_until = state.get("flash_until", {})
        cols = 5
        rows = 8
        cell_w = rect.width // cols
        cell_h = rect.height // rows
        cyan = (0, 255, 255)
        white = (255, 255, 255)
        gray = (128, 128, 128)
        green = (0, 255, 0)

        def cell_rect(cell_name: str) -> pygame.Rect:
            col = ord(cell_name[0]) - ord("A")
            row = int(cell_name[1:]) - 1
            return pygame.Rect(rect.x + col * cell_w, rect.y + row * cell_h, cell_w, cell_h)

        def merged_de(row_no: int) -> pygame.Rect:
            d = cell_rect(f"D{row_no}")
            e = cell_rect(f"E{row_no}")
            return d.union(e)

        def is_flash(key: str) -> bool:
            if not isinstance(flash_until, dict):
                return False
            try:
                return int(flash_until.get(key, 0)) > now_ms
            except Exception:
                return False

        def draw_line_bottom(
            box: pygame.Rect,
            line_no: int,
            text: str,
            color: Tuple[int, int, int],
            *,
            size: int = 16,
            box_selected: bool = False,
            flash_key: Optional[str] = None,
            h_align: str = "center",
            v_align: str = "bottom",
        ) -> pygame.Rect:
            font = get_font(size)
            y3 = box.bottom - font.get_height() - 2
            y2 = y3 - font.get_height() - 1
            y1 = y2 - font.get_height() - 1
            y = y1 if line_no <= 1 else y2 if line_no == 2 else y3
            if v_align == "center":
                y = box.centery - font.get_height() // 2
            flashing = is_flash(flash_key or "")
            draw_color = (0, 0, 0) if flashing else color
            surf = font.render(text, True, draw_color)
            if h_align == "left":
                srect = surf.get_rect(left=box.left + 4)
            elif h_align == "right":
                srect = surf.get_rect(right=box.right - 4)
            else:
                srect = surf.get_rect(centerx=box.centerx)
            srect.y = y
            if flashing:
                pygame.draw.rect(surface, white, srect.inflate(4, 2))
            if box_selected:
                pygame.draw.rect(surface, white, srect.inflate(4, 2), 1)
            surface.blit(surf, srect)
            return srect

        def draw_triangle(box: pygame.Rect, direction: str, flash_key: str) -> None:
            flashing = is_flash(flash_key)
            color = (0, 0, 0) if flashing else cyan
            cx, cy = box.centerx, box.centery
            w = min(16, box.width // 3)
            h = min(12, box.height // 3)
            if direction == "up":
                pts = [(cx, cy - h), (cx - w, cy + h), (cx + w, cy + h)]
            else:
                pts = [(cx, cy + h), (cx - w, cy - h), (cx + w, cy - h)]
            if flashing:
                pygame.draw.rect(surface, white, box.inflate(-box.width // 3, -box.height // 3))
            pygame.draw.polygon(surface, color, pts, 0)

        def draw_two_line_center(box: pygame.Rect, t1: str, t2: str, color: Tuple[int, int, int], flash_key: str, *, size: int = 16) -> None:
            font = get_font(size)
            flashing = is_flash(flash_key)
            draw_color = (0, 0, 0) if flashing else color
            s1 = font.render(t1, True, draw_color)
            s2 = font.render(t2, True, draw_color)
            total_h = s1.get_height() + 1 + s2.get_height()
            y = box.centery - total_h // 2
            r1 = s1.get_rect(centerx=box.centerx, y=y)
            r2 = s2.get_rect(centerx=box.centerx, y=y + s1.get_height() + 1)
            if flashing:
                flash_r = r1.union(r2).inflate(4, 2)
                pygame.draw.rect(surface, white, flash_r)
            surface.blit(s1, r1)
            surface.blit(s2, r2)

        def freq_scratch(input_key: str) -> str:
            digits = "".join(ch for ch in str(state.get(input_key, "")) if ch.isdigit())[-6:]
            slots = list("_" * 6)
            for i, ch in enumerate(digits):
                slots[i] = ch
            return f"{''.join(slots[:3])}.{''.join(slots[3:])}"

        def int_scratch(input_key: str, width: int) -> str:
            digits = "".join(ch for ch in str(state.get(input_key, "")) if ch.isdigit())[-width:]
            slots = list("_" * width)
            for i, ch in enumerate(digits):
                slots[i] = ch
            return "".join(slots)

        def geo_scratch(input_key: str) -> str:
            digits = "".join(ch for ch in str(state.get(input_key, "")) if ch.isdigit())[-7:]
            slots = list("_" * 7)
            for i, ch in enumerate(digits):
                slots[i] = ch
            return f"{slots[0]}.{''.join(slots[1:])}"

        def draw_de_block(selected: str) -> None:
            de1 = merged_de(1)
            if selected == "de1":
                draw_line_bottom(de1, 1, int_scratch("de1_input", 3), white, box_selected=True, flash_key="DE1")
            de1_ils_active = bool(state.get("de1_ils_active", False)) and state.get("submenu") is None
            if de1_ils_active:
                try:
                    de1_idx = int(state.get("ils_tacan_index", 1))
                except Exception:
                    de1_idx = 1
                de1_idx = max(1, de1_idx)
                runway_text = str(state.get("de1_ils_runway", "")).strip().upper()
                if runway_text == "":
                    runway_text = "---"
                de1_text = f"{de1_idx:03d} {runway_text}"
            else:
                de1_r_idx = max(1, int(state.get("de1_r_idx", 1)))
                de1_text = f"{str(state.get('de1_value', '000')).rjust(3, '0')} R{de1_r_idx}"
            l2 = draw_line_bottom(de1, 2, de1_text, cyan, flash_key="DE1")
            tri_x = de1.left + 8
            up_pts = [(tri_x, l2.centery - 6), (tri_x - 4, l2.centery + 2), (tri_x + 4, l2.centery + 2)]
            dn_y = l2.centery + 13
            dn_pts = [(tri_x, dn_y + 6), (tri_x - 4, dn_y - 2), (tri_x + 4, dn_y - 2)]
            pygame.draw.polygon(surface, cyan, up_pts, 0)
            pygame.draw.polygon(surface, cyan, dn_pts, 0)

            de2 = merged_de(2)
            line_sel = str(state.get("de2_edit_line", "N")).upper()
            if selected == "de2":
                if line_sel == "N":
                    draw_line_bottom(de2, 1, geo_scratch("de2_n_input"), white, box_selected=True, flash_key="DE2")
                else:
                    draw_line_bottom(de2, 1, geo_scratch("de2_e_input"), white, box_selected=True, flash_key="DE2")
            n_color = white if (selected == "de2" and line_sel == "N") else cyan
            e_color = white if (selected == "de2" and line_sel == "E") else cyan
            draw_line_bottom(de2, 2, f"N {state.get('de2_n', '0.000000')}", n_color, flash_key="DE2")
            draw_line_bottom(de2, 3, f"E {state.get('de2_e', '0.000000')}", e_color, flash_key="DE2")

            de3 = merged_de(3)
            draw_two_line_center(de3, "UTM", "OF", cyan, "DE3")

            de4 = merged_de(4)
            draw_line_bottom(de4, 2, "ELEV", cyan, flash_key="DE4")
            draw_line_bottom(de4, 3, "0 FT MSL", cyan, flash_key="DE4")

            de5 = merged_de(5)
            draw_line_bottom(de5, 2, "TOS", cyan, flash_key="DE5")
            draw_line_bottom(de5, 3, "19:50:10Z", cyan, flash_key="DE5")

        def draw_keypad() -> None:
            keypad_labels = {
                "A4": "1", "B4": "2", "C4": "3",
                "A5": "4", "B5": "5", "C5": "6",
                "A6": "7", "B6": "8", "C6": "9",
                "B7": "0", "C7": "BACK",
            }
            font = get_font(15)
            for cell, text in keypad_labels.items():
                box = cell_rect(cell)
                key = f"NAV_{cell}"
                flashing = is_flash(key)
                surf = font.render(text, True, (0, 0, 0) if flashing else cyan)
                srect = surf.get_rect(center=box.center)
                if flashing:
                    pygame.draw.rect(surface, white, srect.inflate(4, 2))
                surface.blit(surf, srect)
            draw_triangle(cell_rect("A7"), "up", "NAV_A7")
            draw_triangle(cell_rect("A8"), "down", "NAV_A8")

        pygame.draw.rect(surface, cyan, rect, 1)
        for i in range(1, cols):
            x = rect.x + i * cell_w
            pygame.draw.line(surface, cyan, (x, rect.top), (x, rect.bottom), 1)
        for j in range(1, rows):
            y = rect.y + j * cell_h
            pygame.draw.line(surface, cyan, (rect.left, y), (rect.right, y), 1)

        # C3 TACAN mode popup state (drawn as an overlay later so base page stays visible).
        options = state.get("c3_options", ["RECV", "T/R", "A-A RCV", "A-A T/R"])
        if not isinstance(options, list) or len(options) == 0:
            options = ["RECV", "T/R", "A-A RCV", "A-A T/R"]
        c3_idx = max(0, min(len(options) - 1, int(state.get("c3_idx", 0))))
        c3_popup_open = bool(state.get("c3_menu_open", False))

        # Merge D/E rows 1..5 visually.
        de_div_x = rect.x + 4 * cell_w
        for row_no in range(1, 6):
            y1 = rect.y + (row_no - 1) * cell_h + 1
            y2 = rect.y + row_no * cell_h - 1
            pygame.draw.line(surface, (0, 0, 0), (de_div_x, y1), (de_div_x, y2), 1)
            pygame.draw.rect(surface, cyan, merged_de(row_no), 1)

        # WAYPT subpage.
        if str(state.get("submenu", "")) == "WAYPT":
            # B/C1 combined.
            bc1_left = cell_rect("B1")
            bc1_right = cell_rect("C1")
            bc1 = bc1_left.union(bc1_right)
            split_x = bc1_right.left
            pygame.draw.line(surface, (0, 0, 0), (split_x, bc1.top + 1), (split_x, bc1.bottom - 1), 1)
            pygame.draw.rect(surface, cyan, bc1, 1)

            selected = str(state.get("selected_field", "") or "")
            draw_de_block(selected)

            d6 = cell_rect("D6")
            t = draw_line_bottom(d6, 1, "TYPE", cyan, flash_key="D6")
            pygame.draw.line(surface, cyan, (t.left, t.bottom + 1), (t.right, t.bottom + 1), 1)
            draw_line_bottom(d6, 2, "NAV", cyan, flash_key="D6")

            e6 = cell_rect("E6")
            draw_two_line_center(e6, "MLA", "0 FT", cyan, "E6")

            d7 = cell_rect("D7")
            draw_two_line_center(d7, "ADD", "WAYPT", cyan, "D7")
            e7 = cell_rect("E7")
            draw_two_line_center(e7, "DELETE", "WAYPT", cyan, "E7")

            d8 = cell_rect("D8")
            draw_line_bottom(d8, 1, "ADD", cyan, flash_key="D8")
            draw_line_bottom(d8, 2, "PRES GPS", cyan, flash_key="D8")
            draw_line_bottom(d8, 3, "WAYPT", cyan, flash_key="D8")
            e8 = cell_rect("E8")
            draw_line_bottom(e8, 2, "<RFNAV", cyan, flash_key="E8")

            draw_keypad()
            return

        # REFPT subpage.
        if str(state.get("submenu", "")) == "REFPT":
            selected = str(state.get("selected_field", "") or "")

            # Combine A1-C3 and D2-E4 as one large merged button region.
            a1 = cell_rect("A1")
            c3 = cell_rect("C3")
            a1c3 = a1.union(c3)
            for i in range(1, 3):
                x = rect.x + i * cell_w
                pygame.draw.line(surface, (0, 0, 0), (x, a1c3.top + 1), (x, a1c3.bottom - 1), 1)
            for j in range(1, 3):
                y = rect.y + j * cell_h
                pygame.draw.line(surface, (0, 0, 0), (a1c3.left + 1, y), (a1c3.right - 1, y), 1)

            d2 = cell_rect("D2")
            e4 = cell_rect("E4")
            d2e4 = d2.union(e4)
            # Hard-clear this merged block so base grid lines cannot bleed through.
            pygame.draw.rect(surface, (0, 0, 0), d2e4.inflate(-2, -2), 0)
            split_x = cell_rect("E2").left
            pygame.draw.line(surface, (0, 0, 0), (split_x, d2e4.top + 1), (split_x, d2e4.bottom - 1), 1)
            # Remove seam between C and D for rows 2-3 so it appears as one button.
            seam_x = cell_rect("D2").left
            seam_top = cell_rect("D2").top + 1
            seam_bottom = cell_rect("D3").bottom - 1
            pygame.draw.line(surface, (0, 0, 0), (seam_x, seam_top), (seam_x, seam_bottom), 1)
            # Remove internal horizontal row lines inside D2-E4 merged area.
            d2e4_row_sep1 = rect.y + 2 * cell_h
            d2e4_row_sep2 = rect.y + 3 * cell_h
            pygame.draw.line(surface, (0, 0, 0), (d2.left + 1, d2e4_row_sep1), (d2e4.right - 1, d2e4_row_sep1), 1)
            pygame.draw.line(surface, (0, 0, 0), (d2.left + 1, d2e4_row_sep2), (d2e4.right - 1, d2e4_row_sep2), 1)
            # Draw one merged L-shape outline.
            pts = [
                (a1.left, a1.top),
                (a1.right + 2 * cell_w, a1.top),              # C1 right
                (a1.right + 2 * cell_w, d2.top),              # C2 top
                (d2e4.right, d2.top),                         # E2 top
                (d2e4.right, d2e4.bottom),                    # E4 bottom
                (d2.left, d2e4.bottom),                       # D4 bottom
                (d2.left, a1c3.bottom),                       # D3 bottom
                (a1.left, a1c3.bottom),                       # A3 bottom
            ]
            pygame.draw.lines(surface, cyan, True, pts, 1)

            # Merge D/E5, D/E6, D/E7.
            for row_no in (5, 6, 7):
                row_rect = merged_de(row_no)
                split_x = cell_rect(f"E{row_no}").left
                pygame.draw.line(surface, (0, 0, 0), (split_x, row_rect.top + 1), (split_x, row_rect.bottom - 1), 1)
                pygame.draw.rect(surface, cyan, row_rect, 1)

            # D1 status.
            d1 = cell_rect("D1")
            draw_line_bottom(d1, 2, "BULL", cyan, flash_key="D1", v_align="center")

            # E1 data entry WAYPT.
            e1 = cell_rect("E1")
            if selected == "ref_e1":
                draw_line_bottom(e1, 1, int_scratch("ref_e1_input", 3), white, box_selected=True, flash_key="E1")
            draw_line_bottom(e1, 2, "WAYPT", cyan, flash_key="E1")
            l3 = draw_line_bottom(e1, 3, str(state.get("ref_e1_value", "000")).rjust(3, "0"), cyan, flash_key="E1")
            tri_x = e1.left + 8
            up_pts = [(tri_x, l3.centery - 18), (tri_x - 4, l3.centery - 10), (tri_x + 4, l3.centery - 10)]
            dn_pts = [(tri_x, l3.centery + 1), (tri_x - 4, l3.centery - 7), (tri_x + 4, l3.centery - 7)]
            pygame.draw.polygon(surface, cyan, up_pts, 0)
            pygame.draw.polygon(surface, cyan, dn_pts, 0)

            def draw_ref_geo(row_no: int, label: str, value_key: str, input_key: str, flash_key: str) -> None:
                box = merged_de(row_no)
                if selected == input_key:
                    draw_line_bottom(box, 1, int_scratch(f"{input_key}_input", 1), white, box_selected=True, flash_key=flash_key)
                draw_line_bottom(box, 2, label, cyan, flash_key=flash_key)
                draw_line_bottom(box, 3, str(state.get(value_key, "0"))[:1], cyan, flash_key=flash_key)

            draw_ref_geo(5, "TSD1 GEOREF", "ref_de5_value", "ref_de5", "DE5")
            draw_ref_geo(6, "TSD2 GEOREF", "ref_de6_value", "ref_de6", "DE6")
            draw_ref_geo(7, "TSD3 GEOREF", "ref_de7_value", "ref_de7", "DE7")

            e8 = cell_rect("E8")
            draw_line_bottom(e8, 2, "<RFNAV", cyan, flash_key="E8")

            draw_keypad()
            return

        selected = str(state.get("selected_field", "") or "")
        cni_fail_tacan = bool(state.get("cni_fail_tacan_active", False))
        cni_fail_ils = bool(state.get("cni_fail_ils_active", False))

        # A1
        a1 = cell_rect("A1")
        if selected == "a1":
            draw_line_bottom(a1, 1, freq_scratch("a1_input"), white, box_selected=True, flash_key="A1")
        draw_line_bottom(a1, 2, "JPALS", cyan, flash_key="A1")
        draw_line_bottom(a1, 3, str(state.get("a1_value", "XXX.XXX")), cyan, flash_key="A1")

        # A2
        a2 = cell_rect("A2")
        draw_line_bottom(a2, 2, "JPALS", cyan, flash_key="A2")
        draw_line_bottom(a2, 3, "TACAN", cyan, flash_key="A2")

        # B1/B2
        b1 = cell_rect("B1")
        b_col = gray if cni_fail_ils else cyan
        if selected == "b1":
            draw_line_bottom(b1, 1, freq_scratch("b1_input"), white, box_selected=True, flash_key="B1")
        draw_line_bottom(b1, 2, "VOR/ILS", b_col, flash_key="B1")
        draw_line_bottom(b1, 3, str(state.get("b1_value", "110.500")), b_col, flash_key="B1")
        b2 = cell_rect("B2")
        draw_line_bottom(b2, 2, "ILS", b_col, flash_key="B2")
        draw_line_bottom(b2, 3, "DME", b_col, flash_key="B2")

        # C1/C2/C3
        c1 = cell_rect("C1")
        if selected == "c1":
            draw_line_bottom(c1, 1, int_scratch("c1_input", 3), white, box_selected=True, flash_key="C1")
        draw_line_bottom(c1, 2, str(state.get("c1_value", "001")), cyan, flash_key="C1")

        c2 = cell_rect("C2")
        c2_mode = int(state.get("c2_mode", 0))
        draw_line_bottom(c2, 1, "BAND", green, flash_key="C2")
        draw_line_bottom(c2, 2, "X", white if c2_mode == 0 else cyan, box_selected=(c2_mode == 0), flash_key="C2")
        draw_line_bottom(c2, 3, "Y", white if c2_mode == 1 else cyan, box_selected=(c2_mode == 1), flash_key="C2")

        c3 = cell_rect("C3")
        c3_head_color = gray if cni_fail_tacan else green
        c3_opt_color = gray if cni_fail_tacan else white
        h = draw_line_bottom(c3, 1, "TACAN", c3_head_color, flash_key="C3")
        if not cni_fail_tacan:
            pygame.draw.line(surface, green, (h.left, h.bottom + 1), (h.right, h.bottom + 1), 1)
        draw_line_bottom(c3, 2, str(options[c3_idx]), c3_opt_color, box_selected=False, flash_key="C3")

        # D/E1..5
        draw_de_block(selected)

        # E6/E7 and D7
        e6 = cell_rect("E6")
        draw_two_line_center(e6, "MLA", "0 FT", cyan, "E6")
        e7 = cell_rect("E7")
        draw_line_bottom(e7, 2, "UTM", cyan, flash_key="E7", v_align="center")
        d7 = cell_rect("D7")
        d7_mode = int(state.get("d7_mode", 1))
        draw_line_bottom(d7, 1, "MAN", white if d7_mode == 0 else cyan, box_selected=(d7_mode == 0), flash_key="D7")
        draw_line_bottom(d7, 2, "AUTO", white if d7_mode == 1 else cyan, box_selected=(d7_mode == 1), flash_key="D7")

        # Page access
        c8 = cell_rect("C8")
        d8 = cell_rect("D8")
        e8 = cell_rect("E8")
        draw_line_bottom(c8, 2, "JPALS>", cyan, flash_key="C8")
        draw_line_bottom(d8, 2, "REFPT>", cyan, flash_key="D8")
        draw_line_bottom(e8, 2, "WAYPT>", cyan, flash_key="E8")

        if c3_popup_open:
            option_cells = [
                "B3",
                "C3",
                "D3",
                "B4",
                "C4",
                "D4",
            ]
            used_cells = option_cells[: max(0, min(len(options), len(option_cells)))]
            for cell_name in used_cells:
                box = cell_rect(cell_name)
                surface.fill((0, 0, 0), box)
                pygame.draw.rect(surface, cyan, box, 1)
            font = get_font(16)
            for idx, opt in enumerate(options[: len(used_cells)]):
                box = cell_rect(used_cells[idx])
                key = f"NAV_C3_OPT_{idx}"
                is_sel = idx == c3_idx
                flashing = is_flash(key)
                text_color = (0, 0, 0) if flashing else (white if is_sel else cyan)
                surf = font.render(str(opt), True, text_color)
                tr = surf.get_rect(center=box.center)
                if flashing:
                    pygame.draw.rect(surface, white, tr.inflate(4, 2))
                elif is_sel:
                    pygame.draw.rect(surface, white, tr.inflate(6, 3), 1)
                surface.blit(surf, tr)
            draw_line_bottom(cell_rect("E8"), 2, "BACK", cyan, flash_key="NAV_C3_BACK")

        draw_keypad()

    def on_osb(self, label: str, context: FormatContext) -> bool:
        if label == "T1":
            context.request_vded(context.portal_index, "MENU")
            return True
        return False
