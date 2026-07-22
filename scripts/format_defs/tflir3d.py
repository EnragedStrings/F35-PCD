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


class Tflir3DFormat(FormatBase):
    def __init__(self) -> None:
        self.name = "TFLIR"
        self._cached_surface: Optional[pygame.Surface] = None
        self._cached_frame_path: str = ""
        self._cached_frame_mtime_ns: int = 0
        self._last_pose_push_ms: int = 0
        self._last_heading_deg: float = 0.0
        self._last_look_az_deg: float = 90.0
        self._last_cam_heading_world_deg: Optional[float] = None

    @staticmethod
    def _bind_tflir_worker_paths(mod: object) -> None:
        try:
            base_cache = Path(getattr(mod, "_BASE_CACHE_DIR"))
            mod._WORKER_PID_PATH = base_cache / "worker_pid.txt"
            mod._WORKER_LOG_PATH = base_cache / "worker.log"
        except Exception:
            pass

    @staticmethod
    def _ensure_startup_orientation_ref() -> None:
        st = _shared_get("TFLIR3D_STATE", {})
        if not isinstance(st, dict):
            return
        if bool(st.get("startup_ref_set", False)):
            return
        try:
            az = float(st.get("look_az_deg", 90.0) or 90.0)
        except Exception:
            az = 90.0
        try:
            el = float(st.get("look_el_deg", 0.0) or 0.0)
        except Exception:
            el = 0.0
        st["startup_look_az_deg"] = float(az)
        st["startup_look_el_deg"] = float(el)
        st["startup_ref_set"] = True

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
        underline_line_index: Optional[int] = None,
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
        if underline_line_index is not None and 0 <= int(underline_line_index) < len(text_rects):
            ur = text_rects[int(underline_line_index)]
            uy = ur.bottom + 1
            pygame.draw.line(surface, color, (ur.left, uy), (ur.right, uy), 1)

    @staticmethod
    def _extract_pose() -> Optional[Dict[str, object]]:
        try:
            tsd = _shared_get("TSD_ADSB_STATE", {})
            lat = None
            lon = None
            if isinstance(tsd, dict):
                lat = tsd.get("lat")
                lon = tsd.get("lon")
                if lat is None or lon is None:
                    geo = tsd.get("geo")
                    if isinstance(geo, dict):
                        lat = geo.get("lat")
                        lon = geo.get("lon")
            if lat is None or lon is None:
                try:
                    ins_state = _shared_get("ins_gps_state", {})
                    if isinstance(ins_state, dict):
                        lat = ins_state.get("position_lat", lat)
                        lon = ins_state.get("position_lon", lon)
                except Exception:
                    pass
            if lat is None or lon is None:
                return None
            lat_f = float(lat)
            lon_f = float(lon)
        except Exception:
            return None
        heading_deg = 0.0
        try:
            heading_deg = float(_shared_get("TWD_STATE", {}).get("heading_deg", 0.0)) % 360.0
        except Exception:
            heading_deg = 0.0
        altitude_ft = 0.0
        quat = None
        pitch_deg = 0.0
        roll_deg = 0.0
        look_az_deg = 90.0
        look_el_deg = 0.0
        zoom_fov_deg = 45.0
        cam_rel_forward_m = 0.0
        cam_rel_right_m = 0.0
        cam_rel_up_m = 0.0
        cam_default_forward_m = 0.0
        cam_default_right_m = 2.79
        cam_default_up_m = -0.59
        cam_default_cube_size_m = 1.0
        cam_cube_forward_m = 0.0
        cam_cube_right_m = 2.79
        cam_cube_up_m = -0.59
        look_slew_active = False
        hold_point_enabled = True
        whot = True
        bhot = False
        das_camera_key = "DAS-BA"
        das_zoom_ratio = 2.9
        das_fov_v_deg = 29.0
        das_fov_h_deg = 29.0
        das_cam_forward_m = 0.0
        das_cam_right_m = 0.0
        das_cam_up_m = 0.0
        das_yaw_deg = 0.0
        das_pitch_deg = 0.0
        try:
            panel = _shared_get("PANEL_BUTTON_STATES", {})
            if isinstance(panel, dict):
                aircraft = panel.get("AIRCRAFT", {}) if isinstance(panel.get("AIRCRAFT", {}), dict) else {}
                if isinstance(aircraft, dict):
                    altitude_ft = float(aircraft.get("ALTITUDE_FT", aircraft.get("ALTITUDE_TARGET_FT", 0.0)) or 0.0)
                    pitch_deg = float(aircraft.get("ATT_PITCH_DEG", aircraft.get("PITCH", pitch_deg)) or pitch_deg)
                    roll_deg = float(aircraft.get("ATT_ROLL_DEG", aircraft.get("ROLL", roll_deg)) or roll_deg)
                    qw = aircraft.get("ATT_Q_W", None)
                    qx = aircraft.get("ATT_Q_X", None)
                    qy = aircraft.get("ATT_Q_Y", None)
                    qz = aircraft.get("ATT_Q_Z", None)
                    if (qw is not None) and (qx is not None) and (qy is not None) and (qz is not None):
                        quat = {
                            "w": float(qw),
                            "x": float(qx),
                            "y": float(qy),
                            "z": float(qz),
                        }
            tflir_state = _shared_get("TFLIR3D_STATE", {})
            if isinstance(tflir_state, dict):
                look_az_deg = float(tflir_state.get("look_az_deg", 90.0) or 90.0)
                look_el_deg = float(tflir_state.get("look_el_deg", 0.0) or 0.0)
                zoom_fov_deg = float(tflir_state.get("zoom_fov_deg", 45.0) or 45.0)
                cam_rel_forward_m = float(tflir_state.get("cam_rel_forward_m", 0.0) or 0.0)
                cam_rel_right_m = float(tflir_state.get("cam_rel_right_m", 0.0) or 0.0)
                cam_rel_up_m = float(tflir_state.get("cam_rel_up_m", 0.0) or 0.0)
                cam_default_forward_m = float(tflir_state.get("cam_default_forward_m", 0.0) or 0.0)
                cam_default_right_m = float(tflir_state.get("cam_default_right_m", 2.79) or 2.79)
                cam_default_up_m = float(tflir_state.get("cam_default_up_m", -0.59) or -0.59)
                cam_default_cube_size_m = float(tflir_state.get("cam_default_cube_size_m", 1.0) or 1.0)
                cam_cube_forward_m = float(tflir_state.get("cam_cube_forward_m", cam_default_forward_m) or cam_default_forward_m)
                cam_cube_right_m = float(tflir_state.get("cam_cube_right_m", cam_default_right_m) or cam_default_right_m)
                cam_cube_up_m = float(tflir_state.get("cam_cube_up_m", cam_default_up_m) or cam_default_up_m)
                look_slew_active = bool(tflir_state.get("look_slew_active", False))
                hold_point_enabled = bool(tflir_state.get("hold_point_enabled", True))
                bhot = bool(tflir_state.get("bhot", False))
                if "bhot" in tflir_state:
                    whot = not bool(bhot)
                else:
                    whot = bool(tflir_state.get("whot", True))
            das_state = _shared_get("DAS3D_STATE", {})
            if isinstance(das_state, dict):
                camera_keys = das_state.get("camera_keys", [])
                if not isinstance(camera_keys, list) or len(camera_keys) == 0:
                    camera_keys = ["DAS-BA", "DAS-BF", "DAS-L", "DAS-R", "DAS-TA", "DAS-TF"]
                try:
                    cam_idx = int(das_state.get("camera_index", 0) or 0) % len(camera_keys)
                except Exception:
                    cam_idx = 0
                das_camera_key = str(das_state.get("active_camera_key", camera_keys[cam_idx]) or camera_keys[cam_idx]).upper().strip()
                if das_camera_key not in camera_keys:
                    das_camera_key = str(camera_keys[cam_idx]).upper().strip()
                try:
                    das_zoom_ratio = float(das_state.get("zoom_ratio", 2.9) or 2.9)
                except Exception:
                    das_zoom_ratio = 2.9
                try:
                    das_fov_v_deg = float(das_state.get("fov_v_deg", 29.0) or 29.0)
                except Exception:
                    das_fov_v_deg = 29.0
                try:
                    das_fov_h_deg = float(das_state.get("fov_h_deg", 29.0) or 29.0)
                except Exception:
                    das_fov_h_deg = 29.0
                offsets_raw = das_state.get("camera_offsets_m", {})
                rots_raw = das_state.get("camera_rot_deg", {})
                if isinstance(offsets_raw, dict):
                    off = offsets_raw.get(das_camera_key, {})
                    if isinstance(off, dict):
                        das_cam_forward_m = float(off.get("forward", 0.0) or 0.0)
                        das_cam_right_m = float(off.get("right", 0.0) or 0.0)
                        das_cam_up_m = float(off.get("up", 0.0) or 0.0)
                if isinstance(rots_raw, dict):
                    rot = rots_raw.get(das_camera_key, {})
                    if isinstance(rot, dict):
                        das_yaw_deg = float(rot.get("yaw", 0.0) or 0.0)
                        das_pitch_deg = float(rot.get("pitch", 0.0) or 0.0)
        except Exception:
            pass
        return {
            "lat": lat_f,
            "lon": lon_f,
            "heading_deg": heading_deg,
            "altitude_ft": max(0.0, float(altitude_ft)),
            "pitch_deg": float(pitch_deg),
            "roll_deg": float(roll_deg),
            "quat_wxyz": quat,
            "look_az_deg": float(look_az_deg),
            "look_el_deg": float(look_el_deg),
            "zoom_fov_deg": float(zoom_fov_deg),
            "cam_rel_forward_m": float(cam_rel_forward_m),
            "cam_rel_right_m": float(cam_rel_right_m),
            "cam_rel_up_m": float(cam_rel_up_m),
            "cam_default_forward_m": float(cam_default_forward_m),
            "cam_default_right_m": float(cam_default_right_m),
            "cam_default_up_m": float(cam_default_up_m),
            "cam_default_cube_size_m": float(cam_default_cube_size_m),
            "cam_cube_forward_m": float(cam_cube_forward_m),
            "cam_cube_right_m": float(cam_cube_right_m),
            "cam_cube_up_m": float(cam_cube_up_m),
            "look_slew_active": bool(look_slew_active),
            "hold_point_enabled": bool(hold_point_enabled),
            "whot": bool(whot),
            "das_camera_key": str(das_camera_key),
            "das_zoom_ratio": float(das_zoom_ratio),
            "das_fov_v_deg": float(das_fov_v_deg),
            "das_fov_h_deg": float(das_fov_h_deg),
            "das_cam_forward_m": float(das_cam_forward_m),
            "das_cam_right_m": float(das_cam_right_m),
            "das_cam_up_m": float(das_cam_up_m),
            "das_yaw_deg": float(das_yaw_deg),
            "das_pitch_deg": float(das_pitch_deg),
        }

    def _push_pose(self) -> None:
        mod = _get_3dworld_module()
        if mod is None:
            return
        self._bind_tflir_worker_paths(mod)
        now_ms = int(pygame.time.get_ticks())
        if (now_ms - int(self._last_pose_push_ms)) < 80:
            return
        self._last_pose_push_ms = now_ms
        pose = self._extract_pose()
        if not isinstance(pose, dict):
            return
        try:
            self._last_heading_deg = float(pose.get("heading_deg", 0.0)) % 360.0
            self._last_look_az_deg = float(pose.get("look_az_deg", 90.0))
        except Exception:
            pass
        try:
            update_fn = getattr(mod, "update_pose", None)
            if callable(update_fn):
                try:
                    _shared_set("_3DWORLD_DIRECT_POSE_PUSH_MS", int(time.time() * 1000))
                except Exception:
                    pass
                update_fn(
                    float(pose.get("lat", 0.0)),
                    float(pose.get("lon", 0.0)),
                    float(pose.get("altitude_ft", 0.0)),
                    float(pose.get("heading_deg", 0.0)),
                    pose.get("quat_wxyz"),
                    float(pose.get("pitch_deg", 0.0)),
                    float(pose.get("roll_deg", 0.0)),
                    float(pose.get("look_az_deg", 90.0)),
                    float(pose.get("look_el_deg", 0.0)),
                    float(pose.get("zoom_fov_deg", 45.0)),
                    float(pose.get("cam_rel_forward_m", 0.0)),
                    float(pose.get("cam_rel_right_m", 0.0)),
                    float(pose.get("cam_rel_up_m", 0.0)),
                    float(pose.get("cam_default_forward_m", 0.0)),
                    float(pose.get("cam_default_right_m", 2.79)),
                    float(pose.get("cam_default_up_m", -0.59)),
                    float(pose.get("cam_default_cube_size_m", 1.0)),
                    float(pose.get("cam_cube_forward_m", pose.get("cam_default_forward_m", 0.0))),
                    float(pose.get("cam_cube_right_m", pose.get("cam_default_right_m", 2.79))),
                    float(pose.get("cam_cube_up_m", pose.get("cam_default_up_m", -0.59))),
                    bool(pose.get("look_slew_active", False)),
                    str(pose.get("das_camera_key", "DAS-BA")),
                    float(pose.get("das_zoom_ratio", 2.9)),
                    float(pose.get("das_fov_v_deg", 29.0)),
                    float(pose.get("das_fov_h_deg", 29.0)),
                    float(pose.get("das_cam_forward_m", 0.0)),
                    float(pose.get("das_cam_right_m", 0.0)),
                    float(pose.get("das_cam_up_m", 0.0)),
                    float(pose.get("das_yaw_deg", 0.0)),
                    float(pose.get("das_pitch_deg", 0.0)),
                    show_aircraft_model=True,
                    hold_point_enabled=bool(pose.get("hold_point_enabled", True)),
                    whot=bool(pose.get("whot", True)),
                    level_roll_to_horizon=True,
                )
        except Exception:
            pass

    def _pull_latest_frame(self) -> None:
        mod = _get_3dworld_module()
        if mod is None:
            return
        self._bind_tflir_worker_paths(mod)
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
            # Pull per-frame camera orientation metadata when available.
            try:
                meta_path = p.parent / "frame_meta.json"
                if meta_path.exists():
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    if isinstance(meta, dict):
                        raw_hdg = meta.get("cam_heading_world_deg", None)
                        if isinstance(raw_hdg, (int, float)):
                            self._last_cam_heading_world_deg = float(raw_hdg) % 360.0
            except Exception:
                pass
        except Exception:
            return

    def _draw_osb_labels(self, surface: pygame.Surface, rect: pygame.Rect, context: FormatContext) -> None:
        now_ms = int(pygame.time.get_ticks())
        whot_enabled = True
        state_raw = _shared_get("TFLIR3D_STATE", {})
        if not isinstance(state_raw, dict):
            state_raw = {}
        try:
            if isinstance(state_raw, dict):
                if "bhot" in state_raw:
                    whot_enabled = not bool(state_raw.get("bhot", False))
                else:
                    whot_enabled = bool(state_raw.get("whot", True))
        except Exception:
            whot_enabled = True
        try:
            laser_active = int(state_raw.get("laser_firing_until_ms", 0) or 0) > now_ms
        except Exception:
            laser_active = False
        mtt_enabled = bool(state_raw.get("mtt_enabled", False))
        ht_enabled = bool(state_raw.get("hold_point_enabled", True))
        spnt_tgt = bool(state_raw.get("spnt_tgt", state_raw.get("nts_designated", False)))
        cue_enabled = bool(state_raw.get("cue_enabled", False))
        t2 = self._osb_box(rect, "T2")
        t3 = self._osb_box(rect, "T3")
        t4 = self._osb_box(rect, "T4")
        t5 = self._osb_box(rect, "T5")
        r1 = self._osb_box(rect, "R1")
        r2 = self._osb_box(rect, "R2")
        r3 = self._osb_box(rect, "R3")
        l3 = self._osb_box(rect, "L3")
        l4 = self._osb_box(rect, "L4")
        if t2 is not None:
            render_button(
                surface,
                t2,
                ButtonState(
                    button_id="TFLIR_T2",
                    button_type=ButtonType.GOL,
                    function_label="A-S",
                    options=[""],
                    selected_index=0,
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
            render_button(
                surface,
                t3,
                ButtonState(
                    button_id="TFLIR_T3",
                    button_type=ButtonType.MOMENTARY_SINGLE,
                    text="LASER",
                    is_single_function=True,
                    is_on=laser_active,
                    h_align="center",
                    v_align="top",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("T3") else 0,
                ),
                get_font,
                now_ms,
            )
        if t4 is not None:
            render_button(
                surface,
                t4,
                ButtonState(
                    button_id="TFLIR_T4",
                    button_type=ButtonType.MOMENTARY_SINGLE,
                    text="MTT",
                    is_single_function=True,
                    is_on=mtt_enabled,
                    h_align="center",
                    v_align="top",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("T4") else 0,
                ),
                get_font,
                now_ms,
            )
        if t5 is not None:
            render_button(
                surface,
                t5,
                ButtonState(
                    button_id="TFLIR_T5",
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
            zoom_fov_deg = 45.0
            try:
                st = _shared_get("TFLIR3D_STATE", {})
                if isinstance(st, dict):
                    zoom_fov_deg = float(st.get("zoom_fov_deg", 45.0) or 45.0)
            except Exception:
                zoom_fov_deg = 45.0
            zoom_ratio = max(1.0, 45.0 / max(0.00001, zoom_fov_deg))
            if zoom_ratio <= 1.01:
                r1_lines = ["NORM"]
            else:
                zoom_txt = f"{zoom_ratio:.1f}".rstrip("0").rstrip(".")
                r1_lines = ["NARO", f"{zoom_txt}X"]
            render_button(
                surface,
                r1,
                ButtonState(
                    button_id="TFLIR_R1",
                    button_type=ButtonType.MOMENTARY_SINGLE,
                    text="\n".join(r1_lines),
                    is_single_function=True,
                    is_on=bool(len(r1_lines) > 1),
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
                    button_id="TFLIR_R2",
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
        if r3 is not None:
            render_button(
                surface,
                r3,
                ButtonState(
                    button_id="TFLIR_R3",
                    button_type=ButtonType.MOMENTARY_SINGLE,
                    text="HT",
                    is_single_function=True,
                    is_on=ht_enabled,
                    h_align="right",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("R3") else 0,
                ),
                get_font,
                now_ms,
            )
        if l3 is not None:
            render_button(
                surface,
                l3,
                ButtonState(
                    button_id="TFLIR_L3",
                    button_type=ButtonType.GOL,
                    function_label="SPNT",
                    options=["TGT"],
                    selected_index=0,
                    is_on=spnt_tgt,
                    h_align="left",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("L3") else 0,
                ),
                get_font,
                now_ms,
            )
        if l4 is not None:
            render_button(
                surface,
                l4,
                ButtonState(
                    button_id="TFLIR_L4",
                    button_type=ButtonType.DOUBLE_FUNCTION,
                    options=["CUE", "OFF"],
                    selected_index=0 if cue_enabled else 1,
                    h_align="left",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("L4") else 0,
                ),
                get_font,
                now_ms,
            )

    def _draw_north_arrow(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        cyan = (0, 255, 255)
        # Prefer resolved camera world-heading from the 3D worker. This keeps
        # north correct during hold-point stabilization as aircraft heading changes.
        raw_cam_hdg = self._last_cam_heading_world_deg
        if isinstance(raw_cam_hdg, (int, float)) and math.isfinite(float(raw_cam_hdg)):
            cam_heading_world_deg = float(raw_cam_hdg) % 360.0
        else:
            # Fallback from local pose when worker metadata is unavailable.
            # look_az_deg is aircraft-relative with +90deg aligned to aircraft forward.
            cam_heading_world_deg = (float(self._last_heading_deg) + (float(self._last_look_az_deg) - 90.0)) % 360.0
        north_deg = (-cam_heading_world_deg) % 360.0
        theta = math.radians(north_deg)
        margin = max(12, int(round(0.55 * DPI)))
        arrow_cx = rect.right - margin
        arrow_cy = rect.bottom - margin
        arrow_len = max(12, int(round(0.26 * DPI)))
        half_len = float(arrow_len) * 0.5
        tip_x = int(round(float(arrow_cx) + (half_len * math.sin(theta))))
        tip_y = int(round(float(arrow_cy) - (half_len * math.cos(theta))))
        tail_x = int(round(float(arrow_cx) - (half_len * math.sin(theta))))
        tail_y = int(round(float(arrow_cy) + (half_len * math.cos(theta))))
        pygame.draw.line(surface, cyan, (tail_x, tail_y), (tip_x, tip_y), 2)
        left_theta = theta + math.radians(155.0)
        right_theta = theta - math.radians(155.0)
        head_len = max(5, int(round(0.07 * DPI)))
        p2 = (int(round(tip_x + head_len * math.sin(left_theta))), int(round(tip_y - head_len * math.cos(left_theta))))
        p3 = (int(round(tip_x + head_len * math.sin(right_theta))), int(round(tip_y - head_len * math.cos(right_theta))))
        pygame.draw.polygon(surface, cyan, [(tip_x, tip_y), p2, p3])

    def _draw_hotas_status(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        state = _shared_get("TFLIR3D_STATE", {})
        if not isinstance(state, dict):
            return
        now_ms = int(pygame.time.get_ticks())
        flags: List[str] = []
        if bool(state.get("nts_designated", False)):
            flags.append("NTS")
        track_mode = str(state.get("track_mode", "")).upper().strip()
        if track_mode != "":
            flags.append(track_mode)
        if bool(state.get("laser_spot_track", False)):
            flags.append("LST")
        try:
            laser_until = int(state.get("laser_firing_until_ms", 0) or 0)
        except Exception:
            laser_until = 0
        if laser_until > now_ms:
            flags.append("LASER")
        if bool(state.get("tflir_slew_control", False)):
            flags.append("SLEW")
        if len(flags) <= 0:
            return
        font = get_font(15)
        text = "  ".join(flags[:4])
        surf = font.render(text, True, (0, 255, 0))
        r = surf.get_rect(centerx=rect.centerx, top=rect.top + DISPLAY_OSB_H + 6)
        pygame.draw.rect(surface, (0, 0, 0), r.inflate(8, 4), 0)
        surface.blit(surf, r)

    def render(self, surface, rect, is_primary: bool, context: FormatContext) -> None:
        self._ensure_startup_orientation_ref()
        prev_clip = surface.get_clip()
        surface.set_clip(rect)
        surface.fill((0, 0, 0), rect)
        # Keep a local fallback pose push so the worker can start even when
        # main-loop INS/GPS lat/lon is temporarily unavailable.
        self._push_pose()
        self._pull_latest_frame()
        if isinstance(self._cached_surface, pygame.Surface):
            try:
                frame = pygame.transform.smoothscale(self._cached_surface, (int(rect.width), int(rect.height)))
                surface.blit(frame, rect)
            except Exception:
                pass
        else:
            draw_centered_text(surface, rect, "TFLIR 3D LOADING", "00FF00", 26)
        self._draw_hotas_status(surface, rect)
        if is_primary:
            self._draw_osb_labels(surface, rect, context)
        self._draw_north_arrow(surface, rect)
        pygame.draw.rect(surface, (0, 255, 255), rect, 1)
        surface.set_clip(prev_clip)

    def on_osb(self, label: str, context: FormatContext) -> bool:
        del context
        token = str(label or "").upper().strip()
        state_raw = _shared_get("TFLIR3D_STATE", {})
        if not isinstance(state_raw, dict):
            state_raw = {}
            _shared_set("TFLIR3D_STATE", state_raw)
        if token == "R1":
            # NORM = reset to default forward-facing direction.
            startup_az = 90.0
            startup_el = 0.0
            state_raw["norm_look_az_deg"] = float(startup_az)
            state_raw["norm_look_el_deg"] = float(startup_el)
            state_raw["zoom_fov_deg"] = 45.0
            state_raw["look_az_deg"] = float(startup_az)
            state_raw["look_el_deg"] = float(startup_el)
            state_raw["look_slew_active"] = False
            state_raw["hold_point_enabled"] = False
            # Prevent immediate joystick/key slew from overriding the NORM reset.
            try:
                state_raw["norm_reset_until_ms"] = int(pygame.time.get_ticks()) + 500
            except Exception:
                state_raw["norm_reset_until_ms"] = 0
            _shared_set("TFLIR3D_STATE", state_raw)
            return True
        if token == "R2":
            # Toggle polarity exactly like DAS: WHOT <-> BHOT.
            next_bhot = not bool(state_raw.get("bhot", False))
            state_raw["bhot"] = bool(next_bhot)
            state_raw["whot"] = not bool(next_bhot)
            _shared_set("TFLIR3D_STATE", state_raw)
            return True
        if token == "T2":
            state_raw["sensor_mode"] = "A-S"
            _shared_set("TFLIR3D_STATE", state_raw)
            return True
        if token == "T3":
            state_raw["laser_firing_until_ms"] = int(pygame.time.get_ticks()) + 3000
            state_raw["laser_last_fire_ms"] = int(pygame.time.get_ticks())
            _shared_set("TFLIR3D_STATE", state_raw)
            return True
        if token == "T4":
            state_raw["mtt_enabled"] = not bool(state_raw.get("mtt_enabled", False))
            state_raw["track_mode"] = "MTT" if bool(state_raw.get("mtt_enabled", False)) else str(state_raw.get("track_mode", "")).replace("MTT", "").strip()
            _shared_set("TFLIR3D_STATE", state_raw)
            return True
        if token == "T5":
            state_raw["cntl_page_open"] = not bool(state_raw.get("cntl_page_open", False))
            _shared_set("TFLIR3D_STATE", state_raw)
            return True
        if token == "R3":
            state_raw["hold_point_enabled"] = not bool(state_raw.get("hold_point_enabled", True))
            _shared_set("TFLIR3D_STATE", state_raw)
            return True
        if token == "L3":
            state_raw["spnt_tgt"] = not bool(state_raw.get("spnt_tgt", False))
            state_raw["nts_designated"] = bool(state_raw.get("spnt_tgt", False))
            state_raw["track_mode"] = "AREA TRK" if bool(state_raw.get("spnt_tgt", False)) else ""
            _shared_set("TFLIR3D_STATE", state_raw)
            return True
        if token == "L4":
            state_raw["cue_enabled"] = not bool(state_raw.get("cue_enabled", False))
            _shared_set("TFLIR3D_STATE", state_raw)
            return True
        return False

    def on_click(self, pos: Tuple[int, int], rect: pygame.Rect, context: FormatContext) -> bool:
        # Fallback direct hit-test for R1/R2 in case OSB zoning misses in resized portals.
        r1 = self._osb_box(rect, "R1")
        r2 = self._osb_box(rect, "R2")
        if r1 is not None and r1.collidepoint(pos):
            return self.on_osb("R1", context)
        if r2 is not None and r2.collidepoint(pos):
            return self.on_osb("R2", context)
        return False

    def osb_is_interactive(self, label: str) -> bool:
        token = str(label or "").upper().strip()
        if token in {"T1", "T2", "T3", "T4", "T5", "R1", "R2", "R3", "L3", "L4"}:
            return True
        return super().osb_is_interactive(label)
