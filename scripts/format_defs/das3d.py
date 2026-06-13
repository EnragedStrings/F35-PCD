from formats import *  # noqa: F401,F403
import formats as formats_mod


def _shared_get(name: str, default=None):
    try:
        return getattr(formats_mod, name)
    except Exception:
        return globals().get(name, default)


def _shared_set(name: str, value) -> None:
    try:
        setattr(formats_mod, name, value)
    except Exception:
        pass
    try:
        globals()[name] = value
    except Exception:
        pass


class Das3DFormat(FormatBase):
    def __init__(self) -> None:
        self.name = "DAS"
        self._cached_surface: Optional[pygame.Surface] = None
        self._cached_frame_path: str = ""
        self._cached_frame_mtime_ns: int = 0
        self._last_pose_push_ms: int = 0
        self._cam_menu_open: bool = False

    @staticmethod
    def _startup_overlay_active() -> bool:
        state_raw = _shared_get("DAS3D_STATE", {})
        if not isinstance(state_raw, dict):
            return False
        now_ms = int(pygame.time.get_ticks())
        if not bool(state_raw.get("startup_overlay_initialized", False)):
            state_raw["startup_overlay_initialized"] = True
            state_raw["startup_overlay_shown_once"] = False
            state_raw["startup_overlay_until_ms"] = int(now_ms + 4000)
        if bool(state_raw.get("startup_overlay_shown_once", False)):
            return False
        until_ms = int(state_raw.get("startup_overlay_until_ms", 0) or 0)
        if now_ms < until_ms:
            return True
        state_raw["startup_overlay_shown_once"] = True
        return False

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

    @staticmethod
    def _draw_osb_multiline(
        surface: pygame.Surface,
        box: pygame.Rect,
        lines: List[str],
        color: Tuple[int, int, int],
        *,
        h_align: str,
        v_align: str,
        flashing: bool = False,
    ) -> None:
        font = get_font(14)
        rendered = [font.render(str(line), True, (0, 0, 0) if flashing else color) for line in lines]
        total_h = sum(s.get_height() for s in rendered) + max(0, len(rendered) - 1)
        if v_align == "top":
            y = box.top + 2
        elif v_align == "bottom":
            y = box.bottom - total_h - 2
        else:
            y = box.centery - (total_h // 2)
        text_rects: List[pygame.Rect] = []
        for surf in rendered:
            if h_align == "left":
                rr = surf.get_rect()
                rr.left = box.left + OSB_PADDING
            elif h_align == "right":
                rr = surf.get_rect()
                rr.right = box.right - OSB_PADDING
            else:
                rr = surf.get_rect(centerx=box.centerx)
            rr.y = y
            text_rects.append(rr)
            y += surf.get_height() + 1
        if flashing and len(text_rects) > 0:
            flash_rect = text_rects[0].copy()
            for rr in text_rects[1:]:
                flash_rect.union_ip(rr)
            pygame.draw.rect(surface, (255, 255, 255), flash_rect.inflate(4, 2))
        for surf, rr in zip(rendered, text_rects):
            surface.blit(surf, rr)

    @staticmethod
    def _draw_text_line_backdrops(
        surface: pygame.Surface,
        box: pygame.Rect,
        lines: Iterable[str],
        *,
        h_align: str,
        v_align: str,
        padding: int = OSB_PADDING,
        font_size: int = 14,
    ) -> None:
        clean_lines = [str(line) for line in lines if str(line) != ""]
        if len(clean_lines) <= 0:
            return
        font = get_font(int(font_size))
        rendered = [font.render(line, True, (255, 255, 255)) for line in clean_lines]
        total_h = sum(s.get_height() for s in rendered) + max(0, len(rendered) - 1)
        if str(v_align).lower() == "top":
            y = box.top + 2
        elif str(v_align).lower() == "bottom":
            y = box.bottom - total_h - 2
        else:
            y = box.centery - total_h // 2
        for surf in rendered:
            if str(h_align).lower() == "left":
                rr = surf.get_rect(left=box.left + int(padding), y=y)
            elif str(h_align).lower() == "right":
                rr = surf.get_rect(right=box.right - int(padding), y=y)
            else:
                rr = surf.get_rect(centerx=box.centerx, y=y)
            pygame.draw.rect(surface, (0, 0, 0), rr.inflate(6, 2), 0)
            y += surf.get_height() + 1

    @staticmethod
    def _data_entry_grid_rect(rect: pygame.Rect) -> pygame.Rect:
        grid_w = 5 * GRID_CELL_W
        grid_h = 8 * GRID_CELL_H
        grid_x = _anchored_5col_grid_x(rect, grid_w)
        return pygame.Rect(grid_x, rect.y - SIDE_OSB_Y_SHIFT, grid_w, grid_h)

    @staticmethod
    def _gol_popup_rows(rect: pygame.Rect) -> Tuple[int, int]:
        is_5x7 = rect.height >= int(7 * DPI) - 1
        row_start = 3
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

    def _popup_cell_rect(self, rect: pygame.Rect, cell: str) -> Optional[pygame.Rect]:
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
        grid = self._data_entry_grid_rect(rect)
        x = grid.x + col * GRID_CELL_W
        y = grid.y + row * GRID_CELL_H
        w = GRID_CELL_W if col < 4 else (grid.right - x)
        h = GRID_CELL_H if row < 7 else (grid.bottom - y)
        return pygame.Rect(x, y, max(1, w), max(1, h))

    def _popup_cell_at_pos(self, pos: Tuple[int, int], rect: pygame.Rect) -> Optional[str]:
        grid = self._data_entry_grid_rect(rect)
        rel_x = int(pos[0]) - int(grid.x)
        rel_y = int(pos[1]) - int(grid.y)
        if rel_x < 0 or rel_y < 0 or rel_x >= grid.width or rel_y >= grid.height:
            return None
        col = max(0, min(4, rel_x // max(1, GRID_CELL_W)))
        row = max(0, min(7, rel_y // max(1, GRID_CELL_H)))
        return f"{chr(ord('A') + int(col))}{int(row) + 1}"

    @staticmethod
    def _resolve_view_profile(rect: pygame.Rect) -> Tuple[str, float, float]:
        w_in = float(rect.width) / float(DPI)
        h_in = float(rect.height) / float(DPI)
        if w_in >= 9.5 and h_in >= 6.5:
            # 7x10 portal
            return ("7x10", 44.0, 50.0)
        if w_in >= 9.5:
            # 5x10 portal
            return ("5x10", 15.0, 29.0)
        if h_in >= 6.5:
            # 7x5 portal
            return ("7x5", 41.0, 29.0)
        # 5x5 portal
        return ("5x5", 29.0, 29.0)

    @staticmethod
    def _active_das_camera_state() -> Tuple[str, Dict[str, float], Dict[str, float], float]:
        state_raw = _shared_get("DAS3D_STATE", {})
        state = state_raw if isinstance(state_raw, dict) else {}
        camera_keys = state.get("camera_keys", [])
        if not isinstance(camera_keys, list):
            camera_keys = []
        idx = 0
        try:
            idx = int(state.get("camera_index", 0) or 0)
        except Exception:
            idx = 0
        if len(camera_keys) == 0:
            camera_keys = ["DAS-BA", "DAS-BF", "DAS-L", "DAS-R", "DAS-TA", "DAS-TF"]
            state["camera_keys"] = list(camera_keys)
        idx = idx % max(1, len(camera_keys))
        key = str(state.get("active_camera_key", camera_keys[idx]) or camera_keys[idx]).upper().strip()
        if key not in camera_keys:
            key = str(camera_keys[idx]).upper().strip()
        offsets_raw = state.get("camera_offsets_m", {})
        rots_raw = state.get("camera_rot_deg", {})
        zoom_ratio = 2.9
        try:
            zoom_ratio = float(state.get("zoom_ratio", 2.9) or 2.9)
        except Exception:
            zoom_ratio = 2.9
        default_off = {"forward": 0.0, "right": 0.0, "up": 0.0}
        default_rot = {"yaw": 0.0, "pitch": 0.0}
        off_src = offsets_raw.get(key, default_off) if isinstance(offsets_raw, dict) else default_off
        rot_src = rots_raw.get(key, default_rot) if isinstance(rots_raw, dict) else default_rot
        off = {
            "forward": float(off_src.get("forward", 0.0) if isinstance(off_src, dict) else 0.0),
            "right": float(off_src.get("right", 0.0) if isinstance(off_src, dict) else 0.0),
            "up": float(off_src.get("up", 0.0) if isinstance(off_src, dict) else 0.0),
        }
        rot = {
            "yaw": float(rot_src.get("yaw", 0.0) if isinstance(rot_src, dict) else 0.0),
            "pitch": float(rot_src.get("pitch", 0.0) if isinstance(rot_src, dict) else 0.0),
        }
        return (key, off, rot, max(0.1, zoom_ratio))

    @staticmethod
    def _camera_keys_state() -> Tuple[List[str], int]:
        state_raw = _shared_get("DAS3D_STATE", {})
        state = state_raw if isinstance(state_raw, dict) else {}
        camera_keys = state.get("camera_keys", [])
        if not isinstance(camera_keys, list) or len(camera_keys) == 0:
            camera_keys = ["DAS-BA", "DAS-BF", "DAS-L", "DAS-R", "DAS-TA", "DAS-TF"]
            if isinstance(state, dict):
                state["camera_keys"] = list(camera_keys)
        try:
            idx = int(state.get("camera_index", 0) or 0)
        except Exception:
            idx = 0
        idx = idx % max(1, len(camera_keys))
        return ([str(k).upper().strip() for k in camera_keys], int(idx))

    def _push_pose(self, rect: pygame.Rect) -> None:
        mod = _get_dasworld_module()
        if mod is None:
            return
        now_ms = int(pygame.time.get_ticks())
        if (now_ms - int(self._last_pose_push_ms)) < 80:
            return
        self._last_pose_push_ms = now_ms
        base = Tflir3DFormat._extract_pose()
        if not isinstance(base, dict):
            return
        _profile, fov_v_deg, fov_h_deg = self._resolve_view_profile(rect)
        cam_key, cam_off, cam_rot, zoom_ratio = self._active_das_camera_state()
        das_state_raw = _shared_get("DAS3D_STATE", {})
        if isinstance(das_state_raw, dict):
            das_state_raw["fov_v_deg"] = float(fov_v_deg)
            das_state_raw["fov_h_deg"] = float(fov_h_deg)
        try:
            update_fn = getattr(mod, "update_pose", None)
            if callable(update_fn):
                try:
                    _shared_set("_3DWORLD_DIRECT_POSE_PUSH_MS", int(time.time() * 1000))
                except Exception:
                    pass
                update_fn(
                    float(base.get("lat", 0.0)),
                    float(base.get("lon", 0.0)),
                    float(base.get("altitude_ft", 0.0)),
                    float(base.get("heading_deg", 0.0)),
                    base.get("quat_wxyz"),
                    float(base.get("pitch_deg", 0.0)),
                    float(base.get("roll_deg", 0.0)),
                    float(base.get("look_az_deg", 90.0)),
                    float(base.get("look_el_deg", 0.0)),
                    float(base.get("zoom_fov_deg", 45.0)),
                    float(base.get("cam_rel_forward_m", 0.0)),
                    float(base.get("cam_rel_right_m", 0.0)),
                    float(base.get("cam_rel_up_m", 0.0)),
                    float(base.get("cam_default_forward_m", 0.0)),
                    float(base.get("cam_default_right_m", 2.79)),
                    float(base.get("cam_default_up_m", -0.59)),
                    float(base.get("cam_default_cube_size_m", 1.0)),
                    float(base.get("cam_cube_forward_m", base.get("cam_default_forward_m", 0.0))),
                    float(base.get("cam_cube_right_m", base.get("cam_default_right_m", 2.79))),
                    float(base.get("cam_cube_up_m", base.get("cam_default_up_m", -0.59))),
                    bool(base.get("look_slew_active", False)),
                    str(cam_key),
                    float(zoom_ratio),
                    float(fov_v_deg),
                    float(fov_h_deg),
                    float(cam_off.get("forward", 0.0)),
                    float(cam_off.get("right", 0.0)),
                    float(cam_off.get("up", 0.0)),
                    float(cam_rot.get("yaw", 0.0)),
                    float(cam_rot.get("pitch", 0.0)),
                    bool(base.get("hold_point_enabled", True)),
                    bool(das_state_raw.get("whot", True) if isinstance(das_state_raw, dict) else True),
                    False,
                )
        except Exception:
            pass

    def _pull_latest_frame(self) -> None:
        mod = _get_dasworld_module()
        if mod is None:
            return
        try:
            path_fn = getattr(mod, "latest_frame_path", None)
            if not callable(path_fn):
                return
            frame_path = path_fn(3000)
            if not isinstance(frame_path, str) or frame_path.strip() == "":
                return
            p = Path(frame_path)
            if not p.exists():
                return
            mtime_ns = int(p.stat().st_mtime_ns)
            if frame_path == self._cached_frame_path and mtime_ns == int(self._cached_frame_mtime_ns):
                return
            surf = pygame.image.load(str(p))
            self._cached_surface = surf.convert()
            self._cached_frame_path = frame_path
            self._cached_frame_mtime_ns = mtime_ns
        except Exception:
            return

    def _draw_osb_labels(self, surface: pygame.Surface, rect: pygame.Rect, context: FormatContext) -> None:
        now_ms = int(pygame.time.get_ticks())
        whot_enabled = True
        try:
            st = _shared_get("DAS3D_STATE", {})
            if isinstance(st, dict):
                whot_enabled = bool(st.get("whot", True))
        except Exception:
            whot_enabled = True
        t2 = self._osb_box(rect, "T2")
        t3 = self._osb_box(rect, "T3")
        t5 = self._osb_box(rect, "T5")
        r1 = self._osb_box(rect, "R1")
        r2 = self._osb_box(rect, "R2")
        l3 = self._osb_box(rect, "L3")
        if t2 is not None:
            render_button(
                surface,
                t2,
                ButtonState(
                    button_id="DAS_T2",
                    button_type=ButtonType.MOMENTARY_SINGLE,
                    text="OPER",
                    is_single_function=True,
                    is_on=False,
                    h_align="center",
                    v_align="top",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("T2") else 0,
                ),
                get_font,
                now_ms,
            )
        if t3 is not None:
            cam_key, _off, _rot, _zr = self._active_das_camera_state()
            render_button(
                surface,
                t3,
                ButtonState(
                    button_id="DAS_T3",
                    button_type=ButtonType.GOL,
                    function_label="CAM",
                    options=[str(cam_key)],
                    selected_index=0,
                    h_align="center",
                    v_align="top",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("T3") else 0,
                ),
                get_font,
                now_ms,
            )
        if t5 is not None:
            render_button(
                surface,
                t5,
                ButtonState(
                    button_id="DAS_T5",
                    button_type=ButtonType.PAGE_ACCESS,
                    text="CNTL>",
                    h_align="center",
                    v_align="top",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("T5") else 0,
                ),
                get_font,
                now_ms,
            )
        if r1 is not None:
            render_button(
                surface,
                r1,
                ButtonState(
                    button_id="DAS_R1",
                    button_type=ButtonType.MOMENTARY_SINGLE,
                    text="NORM",
                    is_single_function=True,
                    is_on=False,
                    h_align="right",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("R1") else 0,
                ),
                get_font,
                now_ms,
            )
        if r2 is not None:
            render_button(
                surface,
                r2,
                ButtonState(
                    button_id="DAS_R2",
                    button_type=ButtonType.MOMENTARY_SINGLE,
                    text="WHOT" if whot_enabled else "BHOT",
                    h_align="right",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("R2") else 0,
                ),
                get_font,
                now_ms,
            )
        if l3 is not None:
            render_button(
                surface,
                l3,
                ButtonState(
                    button_id="DAS_L3",
                    button_type=ButtonType.GOL,
                    function_label="VIEW",
                    options=["A-S"],
                    selected_index=0,
                    h_align="left",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("L3") else 0,
                ),
                get_font,
                now_ms,
            )

    def _draw_cam_gol_popup(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        popup = self._gol_popup_rect(rect)
        if popup.width <= 1 or popup.height <= 1:
            return
        cyan = (0, 255, 255)
        white = (255, 255, 255)
        grid = self._data_entry_grid_rect(rect)
        row_start, row_end = self._gol_popup_rows(rect)
        surface.fill((0, 0, 0), popup)
        pygame.draw.rect(surface, cyan, popup, 1)
        for c in (1, 2):
            x = grid.x + ((1 + c) * GRID_CELL_W)
            pygame.draw.line(surface, cyan, (x, popup.top), (x, popup.bottom), 1)
        for r in range(row_start + 1, row_end + 1):
            y = grid.y + ((r - 1) * GRID_CELL_H)
            pygame.draw.line(surface, cyan, (popup.left, y), (popup.right, y), 1)
        camera_keys, selected_idx = self._camera_keys_state()
        option_cells = self._gol_popup_option_cells(rect, len(camera_keys))
        font = get_font(14)
        for idx, cam in enumerate(camera_keys):
            if idx >= len(option_cells):
                break
            box = self._popup_cell_rect(rect, option_cells[idx])
            if box is None:
                continue
            is_selected = idx == selected_idx
            surf = font.render(str(cam), True, white if is_selected else cyan)
            rr = surf.get_rect(center=box.center)
            if is_selected:
                pygame.draw.rect(surface, white, rr.inflate(6, 3), 1)
            surface.blit(surf, rr)

    def render(self, surface, rect, is_primary: bool, context: FormatContext) -> None:
        prev_clip = surface.get_clip()
        surface.set_clip(rect)
        surface.fill((0, 0, 0), rect)
        self._push_pose(rect)
        self._pull_latest_frame()
        show_startup_overlay = self._startup_overlay_active()
        if (not show_startup_overlay) and isinstance(self._cached_surface, pygame.Surface):
            try:
                view_profile, _v, _h = self._resolve_view_profile(rect)
                draw_rect = rect.copy()
                if view_profile == "7x10":
                    desired_w = max(2, int(round(9.14 * DPI)))
                    desired_w = min(desired_w, rect.width)
                    draw_rect = pygame.Rect(rect.centerx - (desired_w // 2), rect.top, desired_w, rect.height)
                frame = pygame.transform.smoothscale(self._cached_surface, (int(draw_rect.width), int(draw_rect.height)))
                surface.blit(frame, draw_rect)
            except Exception:
                pass
        else:
            draw_centered_text(surface, rect, "DAS NOT COOLED", "00FF00", 24)
        if is_primary:
            self._draw_osb_labels(surface, rect, context)
        if is_primary and self._cam_menu_open:
            self._draw_cam_gol_popup(surface, rect)
        pygame.draw.rect(surface, (0, 255, 255), rect, 1)
        surface.set_clip(prev_clip)

    def _set_camera_index(self, idx: int) -> None:
        state_raw = _shared_get("DAS3D_STATE", {})
        if not isinstance(state_raw, dict):
            return
        camera_keys, _sel = self._camera_keys_state()
        if len(camera_keys) <= 0:
            return
        idx = int(idx) % len(camera_keys)
        state_raw["camera_index"] = int(idx)
        state_raw["active_camera_key"] = str(camera_keys[idx]).upper().strip()

    def on_click(self, pos: Tuple[int, int], rect: pygame.Rect, context: FormatContext) -> bool:
        del context
        if not self._cam_menu_open:
            return False
        popup = self._gol_popup_rect(rect)
        if not popup.collidepoint(pos):
            self._cam_menu_open = False
            return False
        cell = self._popup_cell_at_pos(pos, rect)
        if cell is None:
            return True
        camera_keys, _selected_idx = self._camera_keys_state()
        option_cells = self._gol_popup_option_cells(rect, len(camera_keys))
        if cell in option_cells:
            self._set_camera_index(option_cells.index(cell))
            self._cam_menu_open = False
        return True

    def on_osb(self, label: str, context: FormatContext) -> bool:
        token = str(label or "").upper().strip()
        if token == "T1":
            context.request_vded(context.portal_index, "MENU")
            return True
        if token == "T3":
            self._cam_menu_open = not bool(self._cam_menu_open)
            return True
        if token == "R2":
            state_raw = _shared_get("DAS3D_STATE", {})
            if isinstance(state_raw, dict):
                state_raw["whot"] = not bool(state_raw.get("whot", True))
                _shared_set("DAS3D_STATE", state_raw)
            return True
        return False

    def osb_is_interactive(self, label: str) -> bool:
        return str(label or "").upper().strip() in {"T1", "T3", "R2"}
