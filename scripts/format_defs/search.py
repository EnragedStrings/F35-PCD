from formats import *  # noqa: F401,F403


class SearchFormat(FormatBase):
    name: str = "SRCH"

    def __init__(self) -> None:
        self._label_buttons: Dict[str, Tuple[str, Tuple[int, int, int]]] = {
            "C1": ("AAVOL2", (255, 0, 255)),
            "D1": ("ASVOL", (0, 255, 0)),
        }
        self._label_flash_until: Dict[str, int] = {}
        self._active_gol_button: Optional[str] = None
        self._buttons: Dict[str, ButtonState] = {
            "B1": ButtonState(
                button_id="SRCH_B1",
                button_type=ButtonType.MOMENTARY_SINGLE,
                text="AAVOL1",
                is_single_function=True,
                is_on=False,
                h_align="center",
                v_align="center",
                font_size=14,
            ),
            "E1": ButtonState(
                button_id="SRCH_E1",
                button_type=ButtonType.PAGE_ACCESS,
                text="CNTL>\nE 4",
                h_align="center",
                v_align="center",
                font_size=14,
            ),
            "A2": ButtonState(
                button_id="SRCH_A2",
                button_type=ButtonType.GOL,
                function_label="RDR",
                options=["NOSLP"],
                selected_index=0,
                h_align="center",
                v_align="center",
                font_size=14,
            ),
            "B2": ButtonState(
                button_id="SRCH_B2",
                button_type=ButtonType.DOUBLE_FUNCTION,
                options=["AAS", "HAS"],
                selected_index=1,
                h_align="center",
                v_align="center",
                font_size=14,
            ),
            "C2": ButtonState(
                button_id="SRCH_C2",
                button_type=ButtonType.DOUBLE_FUNCTION,
                options=["AAS", "HAS"],
                selected_index=1,
                h_align="center",
                v_align="center",
                font_size=14,
            ),
            "A3": ButtonState(
                button_id="SRCH_A3",
                button_type=ButtonType.GOL,
                function_label="WB-AA",
                options=["DFLT"],
                selected_index=0,
                h_align="center",
                v_align="center",
                font_size=14,
            ),
            "B3": ButtonState(
                button_id="SRCH_B3",
                button_type=ButtonType.MOMENTARY_SINGLE,
                text="WB-AA1",
                is_single_function=True,
                is_on=False,
                h_align="center",
                v_align="center",
                font_size=14,
            ),
            "C3": ButtonState(
                button_id="SRCH_C3",
                button_type=ButtonType.MOMENTARY_SINGLE,
                text="WB-AA2",
                is_single_function=True,
                is_on=False,
                h_align="center",
                v_align="center",
                font_size=14,
            ),
            "D3": ButtonState(
                button_id="SRCH_D3",
                button_type=ButtonType.MOMENTARY_SINGLE,
                text="WB-AS",
                is_single_function=True,
                is_on=False,
                h_align="center",
                v_align="center",
                font_size=14,
            ),
            "E3": ButtonState(
                button_id="SRCH_E3",
                button_type=ButtonType.GOL,
                function_label="WB-AS",
                options=["DFLT"],
                selected_index=0,
                h_align="center",
                v_align="center",
                font_size=14,
            ),
            "B4": ButtonState(
                button_id="SRCH_B4",
                button_type=ButtonType.MOMENTARY_SINGLE,
                text="IRST",
                is_single_function=True,
                is_on=False,
                h_align="center",
                v_align="center",
                font_size=14,
            ),
            "C4": ButtonState(
                button_id="SRCH_C4",
                button_type=ButtonType.MOMENTARY_SINGLE,
                text="IRST",
                is_single_function=True,
                is_on=False,
                h_align="center",
                v_align="center",
                font_size=14,
            ),
            "B6": ButtonState(
                button_id="SRCH_B6",
                button_type=ButtonType.GOL,
                function_label="AA1-AZ",
                options=["+70"],
                selected_index=0,
                h_align="center",
                v_align="center",
                font_size=14,
            ),
            "C6": ButtonState(
                button_id="SRCH_C6",
                button_type=ButtonType.GOL,
                function_label="AA2-AZ",
                options=["+30"],
                selected_index=0,
                h_align="center",
                v_align="center",
                font_size=14,
            ),
            "D6": ButtonState(
                button_id="SRCH_D6",
                button_type=ButtonType.GOL,
                function_label="AS-AZ",
                options=["+60"],
                selected_index=0,
                h_align="center",
                v_align="center",
                font_size=14,
            ),
        }

    @staticmethod
    def _gol_option_cells() -> List[str]:
        # Keep options on non-OSB-intercepted cells so clicks reach format on_click.
        cells: List[str] = []
        for row in range(2, 8):
            for col in "BCD":
                cells.append(f"{col}{row}")
        for col in "ABCDE":
            cells.append(f"{col}8")
        return cells

    @staticmethod
    def _grid_rect(rect: pygame.Rect) -> pygame.Rect:
        # Keep a fixed 5x7 grid footprint and center it only when width exceeds 5 in.
        grid_w = 5 * GRID_CELL_W
        grid_h = 8 * GRID_CELL_H
        grid_x = _anchored_5col_grid_x(rect, grid_w)
        return pygame.Rect(grid_x, rect.y, grid_w, grid_h)

    @staticmethod
    def _cell_rect(grid_rect: pygame.Rect, label: str) -> Optional[pygame.Rect]:
        if len(label) < 2:
            return None
        col_char = label[0].upper()
        if col_char < "A" or col_char > "E":
            return None
        try:
            row_idx = int(label[1:]) - 1
        except Exception:
            return None
        if row_idx < 0 or row_idx > 7:
            return None
        col_idx = ord(col_char) - ord("A")
        return pygame.Rect(
            grid_rect.x + col_idx * GRID_CELL_W,
            grid_rect.y + row_idx * GRID_CELL_H,
            GRID_CELL_W,
            GRID_CELL_H,
        )

    @staticmethod
    def _cell_label_at_pos(grid_rect: pygame.Rect, pos: Tuple[int, int]) -> Optional[str]:
        if not grid_rect.collidepoint(pos):
            return None
        rel_x = pos[0] - grid_rect.x
        rel_y = pos[1] - grid_rect.y
        col = int(rel_x // GRID_CELL_W)
        row = int(rel_y // GRID_CELL_H)
        if col < 0 or col > 4 or row < 0 or row > 7:
            return None
        return f"{chr(ord('A') + col)}{row + 1}"

    def _set_popup_anchor_portal_index(self, portal_index: Optional[int]) -> None:
        # SRCH has no per-portal popup persistence yet; keep API compatibility
        # with other formats that are called through shared popup routing.
        _ = portal_index

    def render(self, surface, rect, is_primary: bool, context: FormatContext) -> None:
        self._set_popup_anchor_portal_index(getattr(context, "portal_index", None))
        prev_clip = surface.get_clip()
        surface.set_clip(rect)
        surface.fill((0, 0, 0), rect)

        if not is_primary:
            bottom_font = get_font(18)
            bottom = bottom_font.render("SRCH", True, (0, 255, 255))
            bottom_rect = bottom.get_rect(centerx=rect.centerx)
            bottom_rect.bottom = rect.bottom - 2
            surface.blit(bottom, bottom_rect)
            pygame.draw.rect(surface, (0, 255, 255), rect, 1)
            surface.set_clip(prev_clip)
            return

        grid_rect = self._grid_rect(rect)
        cyan = (0, 255, 255)
        green = (0, 255, 0)
        purple = (255, 0, 255)

        # Render full 8-row grid including row 8.
        vert_bottom = grid_rect.bottom

        for col in range(6):
            x = grid_rect.x + col * GRID_CELL_W
            pygame.draw.line(surface, cyan, (x, grid_rect.top), (x, vert_bottom), 1)
        # Keep full horizontal grid lines including bottom line.
        for row in range(9):
            y = grid_rect.y + row * GRID_CELL_H
            pygame.draw.line(surface, cyan, (grid_rect.left, y), (grid_rect.right, y), 1)

        now_ms = int(pygame.time.get_ticks())

        self._label_flash_until = {
            key: until for key, until in self._label_flash_until.items() if int(until) > now_ms
        }

        if self._active_gol_button is not None:
            active_state = self._buttons.get(self._active_gol_button)
            if active_state is None or active_state.button_type != ButtonType.GOL:
                self._active_gol_button = None
            else:
                surface.fill((0, 0, 0), grid_rect)
                vert_bottom = grid_rect.bottom
                for col in range(6):
                    x = grid_rect.x + col * GRID_CELL_W
                    pygame.draw.line(surface, cyan, (x, grid_rect.top), (x, vert_bottom), 1)
                for row in range(9):
                    y = grid_rect.y + row * GRID_CELL_H
                    pygame.draw.line(surface, cyan, (grid_rect.left, y), (grid_rect.right, y), 1)

                selected_idx = int(active_state.selected_index or 0)
                option_font = get_font(14)
                option_cells = self._gol_option_cells()
                for idx, option in enumerate(active_state.options):
                    if idx >= len(option_cells):
                        break
                    option_label = option_cells[idx]
                    box = self._cell_rect(grid_rect, option_label)
                    if box is None:
                        continue
                    is_selected = idx == selected_idx
                    color = (255, 255, 255) if is_selected else cyan
                    opt_surf = option_font.render(str(option), True, color)
                    opt_rect = opt_surf.get_rect(center=box.center)
                    if is_selected:
                        pygame.draw.rect(surface, (255, 255, 255), opt_rect.inflate(4, 2), 1)
                    surface.blit(opt_surf, opt_rect)

                pygame.draw.rect(surface, (0, 255, 255), rect, 1)
                surface.set_clip(prev_clip)
                return

        def draw_center_multiline(cell_label: str, text: str, color: Tuple[int, int, int], font_size: int = 14) -> None:
            box = self._cell_rect(grid_rect, cell_label)
            if box is None:
                return
            lines = text.split("\n")
            font = get_font(font_size)
            flashing = int(self._label_flash_until.get(cell_label, 0)) > now_ms
            rendered = [font.render(line, True, (0, 0, 0) if flashing else color) for line in lines]
            total_h = sum(s.get_height() for s in rendered) + max(0, len(rendered) - 1)
            y = box.centery - total_h // 2
            text_rects: List[pygame.Rect] = []
            for surf in rendered:
                r = surf.get_rect(centerx=box.centerx, y=y)
                text_rects.append(r)
                surface.blit(surf, r)
                y += surf.get_height() + 1
            if flashing and text_rects:
                fr = text_rects[0].copy()
                for rr in text_rects[1:]:
                    fr.union_ip(rr)
                fr.inflate_ip(4, 2)
                pygame.draw.rect(surface, (255, 255, 255), fr)
                for surf, r in zip(rendered, text_rects):
                    surface.blit(surf, r)

        # Row 1 labels.
        for cell_label, (text, color) in self._label_buttons.items():
            draw_center_multiline(cell_label, text, color)

        for cell_label, btn_state in self._buttons.items():
            box = self._cell_rect(grid_rect, cell_label)
            if box is None:
                continue
            render_button(surface, box, btn_state, get_font, now_ms)

        pygame.draw.rect(surface, (0, 255, 255), rect, 1)
        surface.set_clip(prev_clip)

    def on_click(self, pos: Tuple[int, int], rect: pygame.Rect, context: FormatContext) -> bool:
        grid_rect = self._grid_rect(rect)
        label = self._cell_label_at_pos(grid_rect, pos)
        if label is None:
            return False
        now_ms = int(pygame.time.get_ticks())
        if self._active_gol_button is not None:
            active_state = self._buttons.get(self._active_gol_button)
            if active_state is None or active_state.button_type != ButtonType.GOL:
                self._active_gol_button = None
                return True
            option_cells = self._gol_option_cells()
            if label in option_cells:
                idx = option_cells.index(label)
                if idx < len(active_state.options):
                    active_state.selected_index = idx
                    active_state.flash_until_ms = now_ms + 250
                    self._active_gol_button = None
                    return True
            return True
        if label in self._label_buttons:
            self._label_flash_until[label] = now_ms + 250
            return True
        state = self._buttons.get(label)
        if state is None:
            return False
        action = activate_button(state, now_ms, 250)
        if state.button_type == ButtonType.GOL and action == "open_gol":
            self._active_gol_button = label
        return True

    def on_osb(self, label: str, context: FormatContext) -> bool:
        return False

    def osb_is_interactive(self, label: str) -> bool:
        if self._active_gol_button is not None and label == "T1":
            return False
        return True

    def get_t1_override(self, system_mode: str) -> Optional[List[Tuple[str, Tuple[int, int, int]]]]:
        if self._active_gol_button is not None:
            hidden = (0, 0, 0)
            return [("", hidden), ("", hidden), ("", hidden)]
        return None

    def t1_opens_menu(self) -> bool:
        return self._active_gol_button is None
