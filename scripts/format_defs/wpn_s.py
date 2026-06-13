from formats import *  # noqa: F401,F403


class WpnSFormat(FormatBase):
    name: str = "WPN-S"

    def __init__(self) -> None:
        self._data_selected: Optional[str] = None
        self._data_inputs: Dict[str, str] = {
            "L1": "",
            "T5": "",
            "R1": "",
            "R3": "",
            "R5": "",
        }
        self._data_values: Dict[str, int] = {
            "L1": 1,
            "T5": 45,
            "R1": 0,
            "R3": 850,
            "R5": 500,
        }
        self._field_meta: Dict[str, Dict[str, object]] = {
            "L1": {"title": "QUANT", "suffix": "", "digits": 2},
            "T5": {"title": "IMP ANG", "suffix": "\u00b0", "digits": 3},
            "R1": {"title": "IMG AZ", "suffix": "\u00b0", "digits": 3},
            "R3": {"title": "IMP VEL", "suffix": "FPS", "digits": 4},
            "R5": {"title": "RLSINT", "suffix": "MSEC", "digits": 4},
        }

    @staticmethod
    def _osb_box(rect: pygame.Rect, label: str) -> Optional[pygame.Rect]:
        if len(label) < 2:
            return None
        side = label[0].upper()
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

    def _data_entry_grid_rect(self, rect: pygame.Rect) -> pygame.Rect:
        grid_w = 5 * GRID_CELL_W
        grid_h = 8 * GRID_CELL_H
        grid_x = _anchored_5col_grid_x(rect, grid_w)
        return pygame.Rect(grid_x, rect.y - SIDE_OSB_Y_SHIFT, grid_w, grid_h)

    def _format_field_value(self, label: str) -> str:
        meta = self._field_meta.get(label, {})
        suffix = str(meta.get("suffix", ""))
        value = int(self._data_values.get(label, 0))
        return f"{value}{suffix}"

    def _commit_data_entry(self, label: str) -> None:
        meta = self._field_meta.get(label, {})
        digits = int(meta.get("digits", 3))
        raw = "".join(ch for ch in str(self._data_inputs.get(label, "")) if ch.isdigit())
        if raw != "":
            try:
                value = int(raw)
            except Exception:
                value = int(self._data_values.get(label, 0))
            cap = (10 ** max(1, digits)) - 1
            floor = 1 if label == "L1" else 0
            self._data_values[label] = max(floor, min(cap, value))
        self._data_inputs[label] = ""

    def _apply_data_key(self, label: str, key: str) -> None:
        meta = self._field_meta.get(label, {})
        digits = int(meta.get("digits", 3))
        current = str(self._data_inputs.get(label, ""))
        if key == "BACK":
            self._data_inputs[label] = current[:-1]
            return
        if key not in {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}:
            return
        next_val = "".join(ch for ch in (current + key) if ch.isdigit())
        self._data_inputs[label] = next_val[-digits:]

    def _draw_selected_scratch(self, surface: pygame.Surface, box: pygame.Rect, label: str, *, h_align: str) -> None:
        if self._data_selected != label:
            return
        meta = self._field_meta.get(label, {})
        digits = int(meta.get("digits", 3))
        raw = "".join(ch for ch in str(self._data_inputs.get(label, "")) if ch.isdigit())
        scratch = raw[-digits:].rjust(digits, "_")
        top_text = f"{scratch}\u2190"
        font = get_font(14)
        surf = font.render(top_text, True, (255, 255, 255))
        rr = surf.get_rect()
        if h_align == "right":
            rr.right = box.right - OSB_PADDING
        elif h_align == "left":
            rr.left = box.left + OSB_PADDING
        else:
            rr.centerx = box.centerx
        rr.y = box.top + OSB_PADDING
        pygame.draw.rect(surface, (255, 255, 255), rr.inflate(4, 2), 1)
        surface.blit(surf, rr)

    def _draw_data_entry_popup(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        if self._data_selected is None:
            return
        grid_rect = self._data_entry_grid_rect(rect)
        cell_w = GRID_CELL_W
        cell_h = GRID_CELL_H

        def cell_rect(name: str) -> pygame.Rect:
            col = ord(name[0].upper()) - ord("A")
            row = int(name[1:]) - 1
            return pygame.Rect(grid_rect.x + col * cell_w, grid_rect.y + row * cell_h, cell_w, cell_h)

        popup_rect = cell_rect("B3").union(cell_rect("D6"))
        surface.fill((0, 0, 0), popup_rect)
        pygame.draw.rect(surface, (0, 255, 255), popup_rect, 1)
        for c in (1, 2):
            x = grid_rect.x + (1 + c) * cell_w
            pygame.draw.line(surface, (0, 255, 255), (x, popup_rect.top), (x, popup_rect.bottom), 1)
        for r in (1, 2, 3):
            y = grid_rect.y + (2 + r) * cell_h
            pygame.draw.line(surface, (0, 255, 255), (popup_rect.left, y), (popup_rect.right, y), 1)

        keypad = {
            "B3": "1", "C3": "2", "D3": "3",
            "B4": "4", "C4": "5", "D4": "6",
            "B5": "7", "C5": "8", "D5": "9",
            "B6": ".",
            "C6": "0", "D6": "BACK",
        }
        now_ms = int(pygame.time.get_ticks())
        for cell_name, text in keypad.items():
            box = cell_rect(cell_name)
            render_button(
                surface,
                box,
                ButtonState(
                    button_id=f"WPNS_KEYPAD_{cell_name}",
                    button_type=ButtonType.MOMENTARY_SINGLE,
                    text=text,
                    flash_until_ms=1 if self._local_flash_active(f"KEYPAD_{cell_name}", now_ms) else 0,
                ),
                get_font,
                now_ms,
            )

    def render(self, surface, rect, is_primary: bool, context: FormatContext) -> None:
        prev_clip = surface.get_clip()
        surface.set_clip(rect)
        pygame.draw.rect(surface, (0, 255, 255), rect, 1)
        if not is_primary:
            bottom_font = get_font(18)
            bottom = bottom_font.render("WPN-S", True, (0, 255, 255))
            br = bottom.get_rect(centerx=rect.centerx)
            br.bottom = rect.bottom - 2
            surface.blit(bottom, br)
            surface.set_clip(prev_clip)
            return

        now_ms = int(pygame.time.get_ticks())

        def _draw(label: str, state: ButtonState) -> Optional[pygame.Rect]:
            box = self._osb_box(rect, label)
            if box is None:
                return None
            render_button(surface, box, state, get_font, now_ms)
            return box

        l1_box = _draw(
            "L1",
            ButtonState(
                button_id="WPNS_L1_QUANT",
                button_type=ButtonType.MOMENTARY_SINGLE,
                text=f"\nQUANT\n{self._format_field_value('L1')}",
                h_align="left",
                v_align="center",
                padding=OSB_PADDING,
                flash_until_ms=1 if context.is_osb_flashing("L1") else 0,
            ),
        )
        _draw(
            "T3",
            ButtonState(
                button_id="WPNS_T3_PROF",
                button_type=ButtonType.STATUS_LABEL,
                text="PROF 1",
                h_align="center",
                v_align="top",
                padding=OSB_PADDING,
                flash_until_ms=1 if context.is_osb_flashing("T3") else 0,
            ),
        )

        t5_box = _draw(
            "T5",
            ButtonState(
                button_id="WPNS_T5_IMP_ANG",
                button_type=ButtonType.MOMENTARY_SINGLE,
                text=f"\nIMP ANG\n{self._format_field_value('T5')}",
                h_align="right",
                v_align="center",
                padding=OSB_PADDING,
                flash_until_ms=1 if context.is_osb_flashing("T5") else 0,
            ),
        )
        r1_box = _draw(
            "R1",
            ButtonState(
                button_id="WPNS_R1_IMG_AZ",
                button_type=ButtonType.MOMENTARY_SINGLE,
                text=f"\nIMG AZ\n{self._format_field_value('R1')}",
                h_align="right",
                v_align="center",
                padding=OSB_PADDING,
                flash_until_ms=1 if context.is_osb_flashing("R1") else 0,
            ),
        )
        r3_box = _draw(
            "R3",
            ButtonState(
                button_id="WPNS_R3_IMP_VEL",
                button_type=ButtonType.MOMENTARY_SINGLE,
                text=f"\nIMP VEL\n{self._format_field_value('R3')}",
                h_align="right",
                v_align="center",
                padding=OSB_PADDING,
                flash_until_ms=1 if context.is_osb_flashing("R3") else 0,
            ),
        )
        r5_box = _draw(
            "R5",
            ButtonState(
                button_id="WPNS_R5_RLSINT",
                button_type=ButtonType.MOMENTARY_SINGLE,
                text=f"\nRLSINT\n{self._format_field_value('R5')}",
                h_align="right",
                v_align="center",
                padding=OSB_PADDING,
                flash_until_ms=1 if context.is_osb_flashing("R5") else 0,
            ),
        )

        if isinstance(l1_box, pygame.Rect):
            self._draw_selected_scratch(surface, l1_box, "L1", h_align="left")
        if isinstance(t5_box, pygame.Rect):
            self._draw_selected_scratch(surface, t5_box, "T5", h_align="right")
        if isinstance(r1_box, pygame.Rect):
            self._draw_selected_scratch(surface, r1_box, "R1", h_align="right")
        if isinstance(r3_box, pygame.Rect):
            self._draw_selected_scratch(surface, r3_box, "R3", h_align="right")
        if isinstance(r5_box, pygame.Rect):
            self._draw_selected_scratch(surface, r5_box, "R5", h_align="right")

        self._draw_data_entry_popup(surface, rect)
        surface.set_clip(prev_clip)

    def on_click(self, pos: Tuple[int, int], rect: pygame.Rect, context: FormatContext) -> bool:
        selected = self._data_selected
        if selected is None:
            return False
        grid_rect = self._data_entry_grid_rect(rect)
        rel_x = int(pos[0]) - int(grid_rect.x)
        rel_y = int(pos[1]) - int(grid_rect.y)
        if rel_x < 0 or rel_y < 0 or rel_x >= grid_rect.width or rel_y >= grid_rect.height:
            return False
        col = max(0, min(4, rel_x // max(1, GRID_CELL_W)))
        row = max(0, min(7, rel_y // max(1, GRID_CELL_H)))
        if col < 1 or col > 3 or row < 2 or row > 5:
            return False
        cell = f"{chr(ord('A') + int(col))}{int(row) + 1}"
        keypad = {
            "B3": "1", "C3": "2", "D3": "3",
            "B4": "4", "C4": "5", "D4": "6",
            "B5": "7", "C5": "8", "D5": "9",
            "B6": ".",
            "C6": "0", "D6": "BACK",
        }
        key = keypad.get(cell)
        if key is None:
            return True
        self._trigger_local_flash(f"KEYPAD_{cell}")
        self._apply_data_key(selected, key)
        return True

    def on_key(self, key: str) -> bool:
        selected = self._data_selected
        if selected is None:
            return False
        raw = str(key).strip()
        if raw == "":
            return False
        upper = raw.upper()
        if upper in {"ENTER", "RETURN", "KP_ENTER"}:
            self._commit_data_entry(selected)
            self._data_selected = None
            return True
        normalized: Optional[str] = None
        if upper in {"KP_BACK", "BACKSPACE", "BACK"}:
            normalized = "BACK"
        elif upper.startswith("KP_") and len(upper) == 4 and upper[3].isdigit():
            normalized = upper[3]
        elif len(raw) == 1 and raw.isdigit():
            normalized = raw
        if normalized is None:
            return False
        self._apply_data_key(selected, normalized)
        return True

    def on_osb(self, label: str, context: FormatContext) -> bool:
        token = str(label).upper().strip()
        if token == "T1":
            context.request_vded(context.portal_index, "MENU")
            return True
        if token in {"L1", "T5", "R1", "R3", "R5"}:
            if self._data_selected == token:
                self._commit_data_entry(token)
                self._data_selected = None
            else:
                if self._data_selected is not None:
                    self._commit_data_entry(self._data_selected)
                self._data_selected = token
                self._data_inputs[token] = ""
            return True
        return token == "T3"

    def osb_is_interactive(self, label: str) -> bool:
        token = str(label).upper().strip()
        return token in {"T1", "L1", "T5", "R1", "R3", "R5"}
