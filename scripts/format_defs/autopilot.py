from formats import *  # noqa: F401,F403


class AutopilotFormat(FormatBase):
    name: str = "AUTOPILOT"

    def render(self, surface, rect, is_primary: bool, context: FormatContext) -> None:
        if not is_primary:
            draw_centered_text(surface, rect, "AUTOPILOT", "00FFFF", 14)
            return
        state = AUTOPILOT_STATE
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

        def is_flash(key: str) -> bool:
            flash = state.get("flash_until", {})
            if not isinstance(flash, dict):
                return False
            try:
                return int(flash.get(key, 0)) > int(state.get("now_ms", 0))
            except Exception:
                return False

        def draw_line_bottom(
            box: pygame.Rect,
            line_no: int,
            text: str,
            color: Tuple[int, int, int],
            *,
            size: int = 15,
            flash_key: Optional[str] = None,
            box_selected: bool = False,
        ) -> pygame.Rect:
            font = get_font(size)
            y3 = box.bottom - font.get_height() - 2
            y2 = y3 - font.get_height() - 1
            y1 = y2 - font.get_height() - 1
            y = y1 if line_no <= 1 else y2 if line_no == 2 else y3
            flashing = is_flash(flash_key or "")
            draw_color = (0, 0, 0) if flashing else color
            surf = font.render(text, True, draw_color)
            srect = surf.get_rect(centerx=box.centerx, y=y)
            if flashing:
                pygame.draw.rect(surface, white, srect.inflate(4, 2))
            if box_selected:
                pygame.draw.rect(surface, white, srect.inflate(4, 2), 1)
            surface.blit(surf, srect)
            return srect

        def draw_single_func(box: pygame.Rect, l2: str, l3: str, selected_on: bool, flash_key: str) -> None:
            color = white if selected_on else cyan
            font = get_font(15)
            flashing = is_flash(flash_key)
            draw_color = (0, 0, 0) if flashing else color
            s2 = font.render(l2, True, draw_color)
            s3 = font.render(l3, True, draw_color)
            total_h = s2.get_height() + 1 + s3.get_height()
            y = box.centery - total_h // 2
            r2 = s2.get_rect(centerx=box.centerx, y=y)
            r3 = s3.get_rect(centerx=box.centerx, y=y + s2.get_height() + 1)
            if flashing:
                flash_rect = r2.union(r3).inflate(4, 2)
                pygame.draw.rect(surface, white, flash_rect)
            surface.blit(s2, r2)
            surface.blit(s3, r3)
            if selected_on:
                sel = r2.union(r3).inflate(4, 2)
                pygame.draw.rect(surface, white, sel, 1)

        def draw_data_entry_cell(
            box: pygame.Rect,
            scratch: str,
            label: str,
            current_value: str,
            *,
            selected_on: bool,
            flash_key: str,
        ) -> None:
            scratch_font = get_font(15)
            label_font = get_font(15)
            value_font = get_font(15)
            flashing = is_flash(flash_key)
            label_color = (0, 0, 0) if flashing else cyan
            value_color = (0, 0, 0) if flashing else cyan
            label_surf = label_font.render(label, True, label_color)
            value_surf = value_font.render(current_value, True, value_color)
            if selected_on:
                scratch_surf = scratch_font.render(scratch, True, (0, 0, 0) if flashing else white)
                total_h = scratch_surf.get_height() + 1 + label_surf.get_height() + 1 + value_surf.get_height()
                y = box.centery - total_h // 2
                scratch_rect = scratch_surf.get_rect(centerx=box.centerx, y=y)
                label_rect = label_surf.get_rect(centerx=box.centerx, y=y + scratch_surf.get_height() + 1)
                value_rect = value_surf.get_rect(centerx=box.centerx, y=label_rect.bottom + 1)
                dew_rect = scratch_rect.inflate(6, 4)
                if flashing:
                    pygame.draw.rect(surface, white, dew_rect)
                pygame.draw.rect(surface, white, dew_rect, 1)
                surface.blit(scratch_surf, scratch_rect)
                surface.blit(label_surf, label_rect)
                surface.blit(value_surf, value_rect)
            else:
                total_h = label_surf.get_height() + 1 + value_surf.get_height()
                y = box.centery - total_h // 2
                label_rect = label_surf.get_rect(centerx=box.centerx, y=y)
                value_rect = value_surf.get_rect(centerx=box.centerx, y=y + label_surf.get_height() + 1)
                if flashing:
                    flash_rect = label_rect.union(value_rect).inflate(4, 2)
                    pygame.draw.rect(surface, white, flash_rect)
                surface.blit(label_surf, label_rect)
                surface.blit(value_surf, value_rect)

        def scratch_3(raw: str) -> str:
            digits = "".join(ch for ch in str(raw) if ch.isdigit())[-3:]
            slots = list("___")
            for i, ch in enumerate(digits):
                slots[i] = ch
            return "".join(slots)

        def scratch_alt(raw: str) -> str:
            digits = "".join(ch for ch in str(raw) if ch.isdigit())[-5:]
            slots = list("_____")
            for i, ch in enumerate(digits):
                slots[i] = ch
            return "".join(slots)

        for i in range(1, cols):
            x = rect.x + i * cell_w
            pygame.draw.line(surface, cyan, (x, rect.top), (x, rect.bottom), 1)
        for j in range(1, rows):
            y = rect.y + j * cell_h
            pygame.draw.line(surface, cyan, (rect.left, y), (rect.right, y), 1)
        pygame.draw.rect(surface, cyan, rect, 1)

        options = state.get("speed_mode_options", ["IAS", "FLCH", "SPEED"])
        if not isinstance(options, list) or len(options) == 0:
            options = ["IAS", "FLCH", "SPEED"]
        options = [("SPEED" if str(o).upper() == "SPD" else str(o)) for o in options[:3]]
        mode_idx = max(0, min(len(options) - 1, int(state.get("speed_mode_idx", 0))))

        # SPEED GOL page.
        if bool(state.get("speed_menu_open", False)):
            for i, opt in enumerate(options[:3]):
                box = cell_rect(f"{chr(ord('A') + i)}1")
                r = draw_line_bottom(
                    box,
                    2,
                    str(opt),
                    white if i == mode_idx else cyan,
                    flash_key=f"AP_SPEED_OPT_{i}",
                    box_selected=(i == mode_idx),
                    size=16,
                )
                if i == mode_idx:
                    pygame.draw.rect(surface, white, r.inflate(4, 2), 1)
            return

        selected = str(state.get("selected_field", "") or "")
        hdg_scratch = scratch_3(state.get("hdg_input", "")) if selected == "hdg" else "___"
        alt_scratch = scratch_alt(state.get("alt_input", "")) if selected == "alt" else "_____"
        spd_scratch = scratch_3(state.get("speed_input", "")) if selected == "speed" else "___"
        hdg_current = str(state.get("hdg_value", "000"))
        alt_current = str(state.get("alt_value", "00000"))
        spd_current = str(state.get("speed_value", "000"))

        draw_single_func(cell_rect("D1"), "ATT", "HOLD", bool(state.get("att_hold", False)), "AP_D1")
        draw_single_func(cell_rect("D2"), "HDG", "SEL", bool(state.get("hdg_sel", False)), "AP_D2")
        draw_data_entry_cell(cell_rect("E2"), hdg_scratch, "HDG", hdg_current, selected_on=(selected == "hdg"), flash_key="AP_E2")
        draw_single_func(cell_rect("D3"), "ALT", "HOLD", bool(state.get("alt_hold", False)), "AP_D3")
        draw_single_func(cell_rect("D4"), "ALT", "SEL", bool(state.get("alt_sel", False)), "AP_D4")
        draw_data_entry_cell(cell_rect("E4"), alt_scratch, "ALT", alt_current, selected_on=(selected == "alt"), flash_key="AP_E4")
        draw_single_func(cell_rect("D5"), "SPEED", "HOLD", bool(state.get("speed_hold", False)), "AP_D5")
        e5 = cell_rect("E5")
        gol_font = get_font(15)
        flashing_e5 = is_flash("AP_E5")
        top_color = (0, 0, 0) if flashing_e5 else green
        bot_color = (0, 0, 0) if flashing_e5 else white
        top = gol_font.render("SPEED", True, top_color)
        bot = gol_font.render(str(options[mode_idx]), True, bot_color)
        total_h = top.get_height() + 1 + bot.get_height()
        y = e5.centery - total_h // 2
        top_rect = top.get_rect(centerx=e5.centerx, y=y)
        bot_rect = bot.get_rect(centerx=e5.centerx, y=y + top.get_height() + 1)
        if flashing_e5:
            flash_rect = top_rect.union(bot_rect).inflate(4, 2)
            pygame.draw.rect(surface, white, flash_rect)
        surface.blit(top, top_rect)
        pygame.draw.line(surface, green if not flashing_e5 else (0, 0, 0), (top_rect.left, top_rect.bottom + 1), (top_rect.right, top_rect.bottom + 1), 1)
        surface.blit(bot, bot_rect)
        draw_single_func(cell_rect("D6"), "SPEED", "SEL", bool(state.get("speed_sel", False)), "AP_D6")
        draw_data_entry_cell(cell_rect("E6"), spd_scratch, "SPEED", spd_current, selected_on=(selected == "speed"), flash_key="AP_E6")
        draw_single_func(cell_rect("D7"), "RTE", "HOLD", bool(state.get("rte_hold", False)), "AP_D7")

        # Keypad (A7/A8 removed).
        keypad_labels = {
            "A4": "1", "B4": "2", "C4": "3",
            "A5": "4", "B5": "5", "C5": "6",
            "A6": "7", "B6": "8", "C6": "9",
            "B7": "0", "C7": "BACK",
        }
        font = get_font(15)
        for cell, text in keypad_labels.items():
            box = cell_rect(cell)
            k = f"AP_{cell}"
            flashing = is_flash(k)
            surf = font.render(text, True, (0, 0, 0) if flashing else cyan)
            srect = surf.get_rect(center=box.center)
            if flashing:
                pygame.draw.rect(surface, white, srect.inflate(4, 2))
            surface.blit(surf, srect)

    def on_osb(self, label: str, context: FormatContext) -> bool:
        if label == "T1":
            context.request_vded(context.portal_index, "MENU")
            return True
        return False
