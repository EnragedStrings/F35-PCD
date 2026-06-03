from formats import *  # noqa: F401,F403


class WpnAFormat(FormatBase):
    name: str = "WPN-A"

    def __init__(self) -> None:
        self._chan_options: List[str] = [str(i) for i in range(1, 10)]
        self._id_options: List[str] = [str(i) for i in range(1, 10)]
        self._store_options: List[str] = ["1", "2", "3", "4", "5", "7", "8", "9", "10", "11"]
        self._tgt_size_options: List[str] = ["UNKN", "SMALL", "MED", "LARGE"]
        self._chan_idx: int = 0
        self._id_idx: int = 0
        self._store_idx: int = 0
        self._tgt_size_idx: int = 0
        self._active_gol: Optional[str] = None

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
            return pygame.Rect(rect.x, rect.y + top_offset + (idx - 1) * DISPLAY_OSB_H, GRID_CELL_W, DISPLAY_OSB_H)
        if side == "R":
            if idx < 1 or idx > side_count:
                return None
            return pygame.Rect(rect.right - GRID_CELL_W, rect.y + top_offset + (idx - 1) * DISPLAY_OSB_H, GRID_CELL_W, DISPLAY_OSB_H)
        return None

    @staticmethod
    def _popup_grid_rect(rect: pygame.Rect) -> pygame.Rect:
        grid_w = 5 * GRID_CELL_W
        grid_h = 8 * GRID_CELL_H
        grid_x = _anchored_5col_grid_x(rect, grid_w)
        return pygame.Rect(grid_x, rect.y, grid_w, grid_h)

    @staticmethod
    def _popup_cell_rect(rect: pygame.Rect, cell: str) -> Optional[pygame.Rect]:
        txt = str(cell).upper().strip()
        if len(txt) < 2:
            return None
        col_ch = txt[0]
        if col_ch < "A" or col_ch > "E":
            return None
        try:
            row_idx = int(txt[1:])
        except Exception:
            return None
        if row_idx < 1 or row_idx > 8:
            return None
        col = ord(col_ch) - ord("A")
        row = row_idx - 1
        grid = WpnAFormat._popup_grid_rect(rect)
        x = grid.x + col * GRID_CELL_W
        y = grid.y + row * GRID_CELL_H
        w = GRID_CELL_W if col < 4 else (grid.right - x)
        h = GRID_CELL_H if row < 7 else (grid.bottom - y)
        return pygame.Rect(x, y, max(1, w), max(1, h))

    @staticmethod
    def _popup_cell_at_pos(pos: Tuple[int, int], rect: pygame.Rect) -> Optional[str]:
        grid = WpnAFormat._popup_grid_rect(rect)
        rel_x = int(pos[0]) - int(grid.x)
        rel_y = int(pos[1]) - int(grid.y)
        if rel_x < 0 or rel_y < 0 or rel_x >= grid.width or rel_y >= grid.height:
            return None
        col = max(0, min(4, rel_x // max(1, GRID_CELL_W)))
        row = max(0, min(7, rel_y // max(1, GRID_CELL_H)))
        return f"{chr(ord('A') + int(col))}{int(row) + 1}"

    @staticmethod
    def _gol_popup_rows(rect: pygame.Rect) -> Tuple[int, int]:
        is_5x7 = rect.height >= int(7 * DPI) - 1
        row_start = 3 if is_5x7 else 2
        return row_start, row_start + 3

    def _gol_popup_rect(self, rect: pygame.Rect) -> pygame.Rect:
        row_start, row_end = self._gol_popup_rows(rect)
        top = self._popup_cell_rect(rect, f"B{row_start}")
        bottom = self._popup_cell_rect(rect, f"D{row_end}")
        if top is None or bottom is None:
            return pygame.Rect(rect.x, rect.y, 1, 1)
        return top.union(bottom)

    def _gol_popup_option_cells(self, rect: pygame.Rect, count: int) -> List[str]:
        row_start, _row_end = self._gol_popup_rows(rect)
        ordered = [
            f"B{row_start}",
            f"C{row_start}",
            f"D{row_start}",
            f"B{row_start + 1}",
            f"C{row_start + 1}",
            f"D{row_start + 1}",
            f"B{row_start + 2}",
            f"C{row_start + 2}",
            f"D{row_start + 2}",
            f"B{row_start + 3}",
            f"C{row_start + 3}",
            f"D{row_start + 3}",
        ]
        return ordered[: max(0, int(count))]

    def _active_gol_options(self) -> List[str]:
        key = str(self._active_gol or "").upper().strip()
        if key == "L2":
            return list(self._chan_options)
        if key == "L3":
            return list(self._id_options)
        if key == "R1":
            return list(self._store_options)
        if key == "R3":
            return list(self._tgt_size_options)
        return []

    def _active_gol_selected_index(self) -> int:
        key = str(self._active_gol or "").upper().strip()
        if key == "L2":
            return max(0, min(len(self._chan_options) - 1, int(self._chan_idx)))
        if key == "L3":
            return max(0, min(len(self._id_options) - 1, int(self._id_idx)))
        if key == "R1":
            return max(0, min(len(self._store_options) - 1, int(self._store_idx)))
        if key == "R3":
            return max(0, min(len(self._tgt_size_options) - 1, int(self._tgt_size_idx)))
        return 0

    def _set_active_gol_selected_index(self, idx: int) -> None:
        key = str(self._active_gol or "").upper().strip()
        if key == "L2" and len(self._chan_options) > 0:
            self._chan_idx = max(0, min(len(self._chan_options) - 1, int(idx)))
        elif key == "L3" and len(self._id_options) > 0:
            self._id_idx = max(0, min(len(self._id_options) - 1, int(idx)))
        elif key == "R1" and len(self._store_options) > 0:
            self._store_idx = max(0, min(len(self._store_options) - 1, int(idx)))
        elif key == "R3" and len(self._tgt_size_options) > 0:
            self._tgt_size_idx = max(0, min(len(self._tgt_size_options) - 1, int(idx)))

    def _draw_gol_popup(self, surface: pygame.Surface, rect: pygame.Rect, context: FormatContext) -> None:
        if self._active_gol is None:
            return
        options = self._active_gol_options()
        if len(options) <= 0:
            self._active_gol = None
            return
        selected_idx = self._active_gol_selected_index()
        popup = self._gol_popup_rect(rect)
        row_start, row_end = self._gol_popup_rows(rect)
        grid = self._popup_grid_rect(rect)
        cyan = (0, 255, 255)
        white = (255, 255, 255)
        surface.fill((0, 0, 0), popup)
        pygame.draw.rect(surface, cyan, popup, 1)

        # Three columns (B, C, D).
        for c in (1, 2):
            x = grid.x + ((1 + c) * GRID_CELL_W)
            pygame.draw.line(surface, cyan, (x, popup.top), (x, popup.bottom), 1)
        # Four rows (3, 4, 5, 6).
        for r in range(row_start + 1, row_end + 1):
            y = grid.y + ((r - 1) * GRID_CELL_H)
            pygame.draw.line(surface, cyan, (popup.left, y), (popup.right, y), 1)

        option_cells = self._gol_popup_option_cells(rect, len(options))
        font = get_font(15)
        popup_key = str(self._active_gol).upper()
        for idx, text in enumerate(options):
            if idx >= len(option_cells):
                break
            box = self._popup_cell_rect(rect, option_cells[idx])
            if box is None:
                continue
            is_selected = idx == int(selected_idx)
            flash_key = f"{popup_key}_OPT_{idx}"
            flashing = bool(context.is_osb_flashing(flash_key))
            color = (0, 0, 0) if flashing else (white if is_selected else cyan)
            surf = font.render(str(text), True, color)
            rr = surf.get_rect(center=box.center)
            if flashing:
                pygame.draw.rect(surface, white, rr.inflate(4, 2))
            elif is_selected:
                pygame.draw.rect(surface, white, rr.inflate(6, 3), 1)
            surface.blit(surf, rr)

    def render(self, surface, rect, is_primary: bool, context: FormatContext) -> None:
        prev_clip = surface.get_clip()
        surface.set_clip(rect)
        pygame.draw.rect(surface, (0, 255, 255), rect, 1)
        if not is_primary:
            bottom_font = get_font(18)
            bottom = bottom_font.render("WPN-A", True, (0, 255, 255))
            br = bottom.get_rect(centerx=rect.centerx)
            br.bottom = rect.bottom - 2
            surface.blit(bottom, br)
            surface.set_clip(prev_clip)
            return

        now_ms = int(pygame.time.get_ticks())

        def _draw(label: str, state: ButtonState) -> None:
            box = self._osb_box(rect, label)
            if box is None:
                return
            render_button(surface, box, state, get_font, now_ms)

        _draw(
            "L1",
            ButtonState(
                button_id="WPNA_L1_STEP",
                button_type=ButtonType.MOMENTARY_SINGLE,
                text="STEP",
                h_align="left",
                v_align="center",
                padding=OSB_PADDING,
                flash_until_ms=1 if context.is_osb_flashing("L1") else 0,
            ),
        )
        _draw(
            "L2",
            ButtonState(
                button_id="WPNA_L2_CHAN",
                button_type=ButtonType.GOL,
                function_label="CHAN",
                options=list(self._chan_options),
                selected_index=int(self._chan_idx),
                h_align="left",
                v_align="center",
                padding=OSB_PADDING,
                flash_until_ms=1 if context.is_osb_flashing("L2") else 0,
            ),
        )
        _draw(
            "L3",
            ButtonState(
                button_id="WPNA_L3_ID",
                button_type=ButtonType.GOL,
                function_label="ID",
                options=list(self._id_options),
                selected_index=int(self._id_idx),
                h_align="left",
                v_align="center",
                padding=OSB_PADDING,
                flash_until_ms=1 if context.is_osb_flashing("L3") else 0,
            ),
        )
        _draw(
            "R1",
            ButtonState(
                button_id="WPNA_R1_STORE",
                button_type=ButtonType.GOL,
                function_label="STORE",
                options=list(self._store_options),
                selected_index=int(self._store_idx),
                h_align="right",
                v_align="center",
                padding=OSB_PADDING,
                flash_until_ms=1 if context.is_osb_flashing("R1") else 0,
            ),
        )
        _draw(
            "R3",
            ButtonState(
                button_id="WPNA_R3_TGT_SIZE",
                button_type=ButtonType.GOL,
                function_label="TGT SIZE",
                options=list(self._tgt_size_options),
                selected_index=int(self._tgt_size_idx),
                h_align="right",
                v_align="center",
                padding=OSB_PADDING,
                flash_until_ms=1 if context.is_osb_flashing("R3") else 0,
            ),
        )
        _draw(
            "T5",
            ButtonState(
                button_id="WPNA_T5_CNTL",
                button_type=ButtonType.PAGE_ACCESS,
                text="CNTL>",
                h_align="center",
                v_align="top",
                padding=OSB_PADDING,
                flash_until_ms=1 if context.is_osb_flashing("T5") else 0,
            ),
        )

        self._draw_gol_popup(surface, rect, context)
        surface.set_clip(prev_clip)

    def on_click(self, pos: Tuple[int, int], rect: pygame.Rect, context: FormatContext) -> bool:
        _ = context
        if self._active_gol is None:
            return False
        popup = self._gol_popup_rect(rect)
        if not popup.collidepoint(pos):
            self._active_gol = None
            return False
        cell = self._popup_cell_at_pos(pos, rect)
        if cell is None:
            return True
        options = self._active_gol_options()
        option_cells = self._gol_popup_option_cells(rect, len(options))
        if cell in option_cells:
            self._set_active_gol_selected_index(option_cells.index(cell))
            self._active_gol = None
        return True

    def on_osb(self, label: str, context: FormatContext) -> bool:
        token = str(label).upper().strip()
        if token == "T1":
            self._active_gol = None
            context.request_vded(context.portal_index, "MENU")
            return True
        if token == "L1":
            self._active_gol = None
            return True
        if token in {"L2", "L3", "R1", "R3"}:
            self._active_gol = None if self._active_gol == token else token
            return True
        if token == "T5":
            self._active_gol = None
            return True
        return False

    def osb_is_interactive(self, label: str) -> bool:
        token = str(label).upper().strip()
        return token in {"T1", "T5", "L1", "L2", "L3", "R1", "R3"}
