from formats import *  # noqa: F401,F403


class AltitudeFormat(FormatBase):
    name: str = "ALTITUDE"

    def render(self, surface, rect, is_primary: bool, context: FormatContext) -> None:
        if not is_primary:
            draw_centered_text(surface, rect, "ALTITUDE", "00FFFF", 14)
            return
        state = ALTITUDE_STATE
        now_ms = int(state.get("now_ms", 0))
        flash_until = state.get("flash_until", {})
        cols = 5
        rows = 8
        cell_w = rect.width // cols
        cell_h = rect.height // rows
        cyan = (0, 255, 255)
        white = (255, 255, 255)

        def cell_rect(cell_name: str) -> pygame.Rect:
            col = ord(cell_name[0]) - ord("A")
            row = int(cell_name[1:]) - 1
            return pygame.Rect(rect.x + col * cell_w, rect.y + row * cell_h, cell_w, cell_h)

        def flashing(key: str) -> bool:
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
        ) -> pygame.Rect:
            font = get_font(size)
            y3 = box.bottom - font.get_height() - 2
            y2 = y3 - font.get_height() - 1
            y1 = y2 - font.get_height() - 1
            y = y1 if line_no <= 1 else y2 if line_no == 2 else y3
            is_flash = flashing(flash_key or "")
            draw_color = (0, 0, 0) if is_flash else color
            surf = font.render(text, True, draw_color)
            srect = surf.get_rect(centerx=box.centerx)
            srect.y = y
            if is_flash:
                pygame.draw.rect(surface, white, srect.inflate(4, 2))
            if box_selected:
                pygame.draw.rect(surface, white, srect.inflate(4, 2), 1)
            surface.blit(surf, srect)
            return srect

        def scratch_inhg() -> str:
            digits = "".join(ch for ch in str(state.get("e1_input", "")) if ch.isdigit())[-4:]
            slots = list("_" * 4)
            for i, ch in enumerate(digits):
                slots[i] = ch
            return f"{slots[0]}{slots[1]}.{slots[2]}{slots[3]} \u2190"

        def scratch_int(key: str, width: int) -> str:
            digits = "".join(ch for ch in str(state.get(key, "")) if ch.isdigit())[-width:]
            slots = list("_" * width)
            for i, ch in enumerate(digits):
                slots[i] = ch
            return f"{''.join(slots)} \u2190"

        pygame.draw.rect(surface, cyan, rect, 1)
        for i in range(1, cols):
            x = rect.x + i * cell_w
            pygame.draw.line(surface, cyan, (x, rect.top), (x, rect.bottom), 1)
        for j in range(1, rows):
            y = rect.y + j * cell_h
            pygame.draw.line(surface, cyan, (rect.left, y), (rect.right, y), 1)

        if bool(state.get("gcas_menu_open", False)):
            options = state.get("gcas_options", ["OFF", "AUTO", "LW-LVL", "STBY"])
            if not isinstance(options, list) or len(options) == 0:
                options = ["OFF", "AUTO", "LW-LVL", "STBY"]
            try:
                selected_idx = int(state.get("gcas_idx", 1))
            except Exception:
                selected_idx = 1
            selected_idx = max(0, min(len(options) - 1, selected_idx))
            slots = ["A1", "B1", "C1", "D1"]
            for idx, opt in enumerate(options[:4]):
                box = cell_rect(slots[idx])
                key = f"ALT_GCAS_OPT_{idx}"
                is_sel = idx == selected_idx
                draw_line_bottom(
                    box,
                    2,
                    str(opt),
                    white if is_sel else cyan,
                    box_selected=is_sel,
                    flash_key=key,
                )
            back = cell_rect("E8")
            draw_line_bottom(back, 2, "BACK", cyan, flash_key="ALT_GCAS_BACK")
            return

        selected_field = str(state.get("selected_field", "") or "")
        e1 = cell_rect("E1")
        e2 = cell_rect("E2")
        e4 = cell_rect("E4")
        e5 = cell_rect("E5")
        if selected_field == "e1":
            draw_line_bottom(e1, 1, scratch_inhg(), white, box_selected=True, flash_key="E1")
        draw_line_bottom(e1, 2, "INHG", cyan, flash_key="E1")
        draw_line_bottom(e1, 3, str(state.get("baro_inhg", "29.87")), cyan, flash_key="E1")

        if selected_field == "e2":
            draw_line_bottom(e2, 1, scratch_int("e2_input", 4), white, box_selected=True, flash_key="E2")
        draw_line_bottom(e2, 2, "HPA", cyan, flash_key="E2")
        draw_line_bottom(e2, 3, str(state.get("hpa", "1013")), cyan, flash_key="E2")

        if selected_field == "e4":
            draw_line_bottom(e4, 1, scratch_int("e4_input", 4), white, box_selected=True, flash_key="E4")
        draw_line_bottom(e4, 2, "ALOW", cyan, flash_key="E4")
        draw_line_bottom(e4, 3, str(state.get("alow", "0000")), cyan, flash_key="E4")

        options = state.get("gcas_options", ["OFF", "AUTO", "LW-LVL", "STBY"])
        if not isinstance(options, list) or len(options) == 0:
            options = ["OFF", "AUTO", "LW-LVL", "STBY"]
        try:
            gidx = int(state.get("gcas_idx", 1))
        except Exception:
            gidx = 1
        gidx = max(0, min(len(options) - 1, gidx))
        head = draw_line_bottom(e5, 2, "GCAS", (0, 255, 0), flash_key="E5")
        pygame.draw.line(surface, (0, 255, 0), (head.left, head.bottom + 1), (head.right, head.bottom + 1), 1)
        draw_line_bottom(e5, 3, str(options[gidx]), white, box_selected=True, flash_key="E5")

        keypad_labels = {
            "A4": "1", "B4": "2", "C4": "3",
            "A5": "4", "B5": "5", "C5": "6",
            "A6": "7", "B6": "8", "C6": "9",
            "A7": "^", "B7": "0", "C7": "BACK",
            "A8": "v",
        }
        font = get_font(16)
        for cell, text in keypad_labels.items():
            box = cell_rect(cell)
            key = f"ALT_{cell}"
            is_flash = flashing(key)
            if cell in {"A7", "A8"}:
                tri_w = max(10, box.width // 3)
                tri_h = max(10, box.height // 3)
                cx, cy = box.centerx, box.centery
                if cell == "A7":
                    pts = [(cx, cy - tri_h // 2), (cx - tri_w // 2, cy + tri_h // 2), (cx + tri_w // 2, cy + tri_h // 2)]
                else:
                    pts = [(cx, cy + tri_h // 2), (cx - tri_w // 2, cy - tri_h // 2), (cx + tri_w // 2, cy - tri_h // 2)]
                if is_flash:
                    flash_rect = pygame.Rect(cx - tri_w // 2 - 3, cy - tri_h // 2 - 3, tri_w + 6, tri_h + 6)
                    pygame.draw.rect(surface, white, flash_rect)
                    pygame.draw.polygon(surface, (0, 0, 0), pts, 0)
                else:
                    pygame.draw.polygon(surface, cyan, pts, 0)
                continue
            surf = font.render(text, True, (0, 0, 0) if is_flash else cyan)
            srect = surf.get_rect(center=box.center)
            if is_flash:
                pygame.draw.rect(surface, white, srect.inflate(4, 2))
            surface.blit(surf, srect)

    def on_osb(self, label: str, context: FormatContext) -> bool:
        if label == "T1":
            context.request_vded(context.portal_index, "MENU")
            return True
        return False
