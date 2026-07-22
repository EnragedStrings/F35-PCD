from formats import *  # noqa: F401,F403


class TwdFormat(FormatBase):
    _RWR_SS_OPTIONS: List[str] = ["AA", "AS", "DFLT", "TAC SAM", "TRNG"]

    def __init__(self) -> None:
        self.name = "TWD"

    @classmethod
    def _rwr_ss_options(cls) -> List[str]:
        return list(cls._RWR_SS_OPTIONS)

    @classmethod
    def _rwr_ss_idx(cls) -> int:
        opts = cls._rwr_ss_options()
        idx = int(TWD_STATE.get("rwr_ss_idx", 2) or 2)
        if idx < 0 or idx >= len(opts):
            idx = 2 if len(opts) > 2 else 0
        return idx

    @classmethod
    def _set_rwr_ss_idx(cls, idx: int) -> None:
        opts = cls._rwr_ss_options()
        if len(opts) <= 0:
            TWD_STATE["rwr_ss_idx"] = 0
            return
        clamped = max(0, min(len(opts) - 1, int(idx)))
        TWD_STATE["rwr_ss_idx"] = clamped

    @staticmethod
    def _rwr_ss_popup_open() -> bool:
        return bool(TWD_STATE.get("rwr_ss_popup_open", False))

    @staticmethod
    def _set_rwr_ss_popup_open(value: bool) -> None:
        TWD_STATE["rwr_ss_popup_open"] = bool(value)

    @staticmethod
    def _set_popup_anchor_portal_index(portal_index: Optional[int]) -> None:
        try:
            idx = int(portal_index) if portal_index is not None else int(TWD_STATE.get("_popup_anchor_portal_idx", 0))
        except Exception:
            idx = int(TWD_STATE.get("_popup_anchor_portal_idx", 0) or 0)
        TWD_STATE["_popup_anchor_portal_idx"] = max(0, min(3, idx))

    @staticmethod
    def _set_heading_deg(value: float) -> None:
        try:
            heading = float(value) % 360.0
        except Exception:
            heading = 0.0
        if heading < 0:
            heading += 360.0
        TWD_STATE["heading_deg"] = heading
        try:
            throttle = PANEL_BUTTON_STATES.get("THROTTLE", {})
            if not isinstance(throttle, dict):
                throttle = {}
                PANEL_BUTTON_STATES["THROTTLE"] = throttle
            aircraft = throttle.get("AIRCRAFT", {})
            if not isinstance(aircraft, dict):
                aircraft = {}
                throttle["AIRCRAFT"] = aircraft
            aircraft["HEADING_DEG"] = float(heading)
            aircraft["HDG_DEG"] = float(heading)
            aircraft["HEADING"] = float(heading)
            aircraft["HDG"] = float(heading)
        except Exception:
            pass

    @staticmethod
    def _hdg_selected() -> bool:
        return bool(TWD_STATE.get("hdg_selected", False))

    @staticmethod
    def _set_hdg_selected(selected: bool) -> None:
        TWD_STATE["hdg_selected"] = bool(selected)

    @staticmethod
    def _hdg_input() -> str:
        return str(TWD_STATE.get("hdg_input", ""))

    @staticmethod
    def _set_hdg_input(value: str) -> None:
        TWD_STATE["hdg_input"] = str(value)

    @staticmethod
    def _commit_hdg_entry() -> None:
        raw = "".join(ch for ch in TwdFormat._hdg_input() if ch.isdigit())
        if raw != "":
            try:
                heading = max(0, min(359, int(raw)))
                TwdFormat._set_heading_deg(float(heading))
            except Exception:
                pass
        TwdFormat._set_hdg_input("")
        TwdFormat._set_hdg_selected(False)

    @staticmethod
    def _apply_hdg_key(key: str) -> None:
        current = TwdFormat._hdg_input()
        token = str(key).upper().strip()
        if token in {"BACK", "KP_BACK", "BACKSPACE"}:
            TwdFormat._set_hdg_input(current[:-1])
            return
        if token.startswith("KP_") and len(token) == 4 and token[-1].isdigit():
            digit = token[-1]
        elif len(token) == 1 and token.isdigit():
            digit = token
        else:
            digit = ""
        if digit == "":
            return
        TwdFormat._set_hdg_input((current + digit)[-3:])

    @staticmethod
    def _data_entry_grid_rect(rect: pygame.Rect) -> pygame.Rect:
        # Keep keypad geometry aligned with FUEL popup behavior.
        grid_w = 5 * GRID_CELL_W
        grid_h = 8 * GRID_CELL_H
        grid_x = _anchored_5col_grid_x(rect, grid_w)
        return pygame.Rect(grid_x, rect.y - SIDE_OSB_Y_SHIFT, grid_w, grid_h)

    @staticmethod
    def _draw_data_entry_popup(surface: pygame.Surface, rect: pygame.Rect) -> None:
        if not TwdFormat._hdg_selected():
            return
        grid_rect = TwdFormat._data_entry_grid_rect(rect)
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
        font = get_font(16)
        for cell_name, text in keypad.items():
            box = cell_rect(cell_name)
            s = font.render(text, True, (0, 255, 255))
            s_rect = s.get_rect(center=box.center)
            surface.blit(s, s_rect)

    @staticmethod
    def _read_heading_deg() -> float:
        # Default heading is 035 unless a heading value is provided elsewhere.
        heading = float(TWD_STATE.get("heading_deg", 35.0))
        try:
            throttle = PANEL_BUTTON_STATES.get("THROTTLE", {}) if isinstance(PANEL_BUTTON_STATES, dict) else {}
            if isinstance(throttle, dict):
                aircraft = throttle.get("AIRCRAFT", {})
                if isinstance(aircraft, dict):
                    for key in ("HEADING_DEG", "HDG_DEG", "HEADING", "HDG"):
                        if key in aircraft:
                            heading = float(aircraft.get(key, heading))
                            break
        except Exception:
            pass
        heading = float(heading) % 360.0
        if heading < 0:
            heading += 360.0
        return heading

    @staticmethod
    def _is_5x5_window(rect: pygame.Rect) -> bool:
        return rect.width < int(10 * DPI) and rect.height < int(7 * DPI)

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
    def _hsd_border_rect(rect: pygame.Rect) -> pygame.Rect:
        border_inset_x = int(round(0.85 * DPI))
        border_inset_y = int(round(0.5 * DPI))
        return pygame.Rect(
            rect.left + border_inset_x,
            rect.top + border_inset_y,
            rect.width - (2 * border_inset_x),
            rect.height - (2 * border_inset_y),
        )

    @staticmethod
    def _ownship_altitude_msl_ft() -> float:
        def _read_from(src: object) -> Optional[float]:
            if not isinstance(src, dict):
                return None
            for key in ("ALTITUDE_FT", "ALTITUDE_TARGET_FT", "ALT"):
                try:
                    if key in src:
                        return float(src.get(key, 0.0) or 0.0)
                except Exception:
                    continue
            return None

        try:
            panel = PANEL_BUTTON_STATES if isinstance(PANEL_BUTTON_STATES, dict) else {}
            top_aircraft = panel.get("AIRCRAFT", {}) if isinstance(panel, dict) else {}
            v = _read_from(top_aircraft)
            if v is not None:
                return float(v)
            throttle = panel.get("THROTTLE", {}) if isinstance(panel, dict) else {}
            nested_aircraft = throttle.get("AIRCRAFT", {}) if isinstance(throttle, dict) else {}
            v = _read_from(nested_aircraft)
            if v is not None:
                return float(v)
        except Exception:
            pass
        return 0.0

    @staticmethod
    def _latlon_to_world_px(lat: float, lon: float, zoom: int) -> Tuple[float, float]:
        lat_clamped = max(-85.05112878, min(85.05112878, float(lat)))
        lon_wrapped = ((float(lon) + 180.0) % 360.0) - 180.0
        scale = float(256 * (2 ** int(zoom)))
        x = ((lon_wrapped + 180.0) / 360.0) * scale
        sin_lat = math.sin(math.radians(lat_clamped))
        y = (0.5 - (math.log((1.0 + sin_lat) / max(1e-9, (1.0 - sin_lat))) / (4.0 * math.pi))) * scale
        return float(x), float(y)

    @classmethod
    def _terrain_elevation_m(cls, lat: float, lon: float, zoom: int = 11) -> Optional[float]:
        if Image is None:
            return None
        z = max(0, min(15, int(zoom)))
        wx, wy = cls._latlon_to_world_px(float(lat), float(lon), z)
        tx = int(math.floor(wx / 256.0))
        ty = int(math.floor(wy / 256.0))
        tile = Asr1Format._fetch_terrain_tile(z, tx, ty)
        if tile is None:
            return None
        px = int(wx - (float(tx) * 256.0))
        py = int(wy - (float(ty) * 256.0))
        px = max(0, min(255, int(px)))
        py = max(0, min(255, int(py)))
        try:
            r, g, b = tile.getpixel((px, py))
            elev_m = (float(r) * 256.0) + float(g) + (float(b) / 256.0) - 32768.0
            return float(elev_m)
        except Exception:
            return None

    def _ownship_agl_m(self) -> float:
        state = self._state()
        own = self._own_lat_lon()
        alt_msl_m = max(0.0, float(self._ownship_altitude_msl_ft()) * 0.3048)
        if own is None:
            return alt_msl_m
        lat, lon = own
        key = (int(round(float(lat) * 1000.0)), int(round(float(lon) * 1000.0)))
        now_ms = int(pygame.time.get_ticks())
        last_key = state.get("_ears_terrain_key")
        last_ms = int(state.get("_ears_terrain_ms", 0) or 0)
        cached_ground = Tsd1Format._safe_float(state.get("_ears_ground_m"))
        if (
            isinstance(last_key, tuple)
            and len(last_key) == 2
            and tuple(last_key) == tuple(key)
            and cached_ground is not None
            and (now_ms - last_ms) < 1200
        ):
            return max(0.0, alt_msl_m - float(cached_ground))
        ground_m = self._terrain_elevation_m(float(lat), float(lon), zoom=11)
        if ground_m is None:
            ground_m = float(cached_ground) if cached_ground is not None else 0.0
        state["_ears_terrain_key"] = key
        state["_ears_terrain_ms"] = now_ms
        state["_ears_ground_m"] = float(ground_m)
        return max(0.0, alt_msl_m - float(ground_m))

    @staticmethod
    def _bezier_points(
        p0: Tuple[float, float],
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        p3: Tuple[float, float],
        steps: int = 32,
    ) -> List[Tuple[float, float]]:
        points: List[Tuple[float, float]] = []
        count = max(2, int(steps))
        for i in range(count):
            t = float(i) / float(max(1, count - 1))
            u = 1.0 - t
            x = (
                (u * u * u * float(p0[0]))
                + (3.0 * u * u * t * float(p1[0]))
                + (3.0 * u * t * t * float(p2[0]))
                + (t * t * t * float(p3[0]))
            )
            y = (
                (u * u * u * float(p0[1]))
                + (3.0 * u * u * t * float(p1[1]))
                + (3.0 * u * t * t * float(p2[1]))
                + (t * t * t * float(p3[1]))
            )
            points.append((float(x), float(y)))
        return points

    @classmethod
    def _generate_f35_sar_ears(
        cls,
        altitude_scale: float = 1.0,
        width: float = 95.0,
        height: float = 270.0,
        inner_gap: float = 7.0,
        bottom_y: float = 0.0,
        steps: int = 40,
    ) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
        s = max(0.2, float(altitude_scale))
        w = float(width) * s
        h = float(height) * s
        g = float(inner_gap) * s
        by = float(bottom_y)
        lobes: List[List[Tuple[float, float]]] = []
        for side in (-1.0, 1.0):
            inner_bottom = (side * g, by)
            far_tip = (side * 26.0 * s, by + h)
            outer_bulge = (side * w, by + (h * 0.48))
            outer_bottom = (side * 42.0 * s, by + (h * 0.08))
            inner_edge = cls._bezier_points(
                inner_bottom,
                (side * g, by + (h * 0.35)),
                (side * 18.0 * s, by + (h * 0.78)),
                far_tip,
                steps,
            )
            outer_edge = cls._bezier_points(
                far_tip,
                (side * 72.0 * s, by + (h * 0.92)),
                outer_bulge,
                outer_bottom,
                steps,
            )
            bottom_edge = cls._bezier_points(
                outer_bottom,
                (side * 28.0 * s, by - (h * 0.02)),
                (side * 12.0 * s, by - (h * 0.03)),
                inner_bottom,
                steps,
            )
            lobes.append(inner_edge + outer_edge + bottom_edge)
        if len(lobes) < 2:
            return [], []
        return lobes[0], lobes[1]

    @staticmethod
    def _sar_altitude_scale(agl_m: float) -> float:
        # Matches requested behavior: lower altitude compresses lobes (about 0.55),
        # higher altitude expands toward nominal/full shape.
        agl_ft = max(0.0, float(agl_m) * 3.28084)
        if agl_ft <= 5000.0:
            return 0.55
        if agl_ft >= 12000.0:
            return 1.0
        t = (agl_ft - 5000.0) / 7000.0
        return 0.55 + (0.45 * t)

    def _draw_hsd_sar_ears(
        self,
        surface: pygame.Surface,
        center: Tuple[int, int],
        range_nm: float,
        heading_deg: float,
        zoom_scale: float,
        clamp_rect: Optional[pygame.Rect] = None,
    ) -> None:
        agl_m = self._ownship_agl_m()
        if agl_m <= 0.5:
            return
        altitude_scale = self._sar_altitude_scale(agl_m)
        left_lobe, right_lobe = self._generate_f35_sar_ears(
            altitude_scale=altitude_scale,
            width=95.0,
            height=270.0,
            inner_gap=7.0,
            bottom_y=0.0,
            steps=40,
        )
        if len(left_lobe) < 3 and len(right_lobe) < 3:
            return
        px_scale = max(0.2, float(zoom_scale))

        def _map_lobe_to_screen(points: List[Tuple[float, float]]) -> List[Tuple[int, int]]:
            mapped: List[Tuple[int, int]] = []
            for x_local, y_local in points:
                x_px = float(x_local) * px_scale
                y_px = float(y_local) * px_scale
                radius = math.hypot(x_px, y_px)
                if radius <= 1e-6:
                    mapped.append((int(center[0]), int(center[1])))
                    continue
                # Local frame: +Y is aircraft forward, +X is aircraft right.
                rel_deg = math.degrees(math.atan2(float(x_px), float(y_px)))
                world_deg = (float(heading_deg) + rel_deg) % 360.0
                sx, sy = self._polar_from_north(center, radius, world_deg)
                mapped.append((int(sx), int(sy)))
            return mapped

        left_pts = _map_lobe_to_screen(left_lobe)
        right_pts = _map_lobe_to_screen(right_lobe)
        prev_clip = surface.get_clip()
        if isinstance(clamp_rect, pygame.Rect) and clamp_rect.width > 0 and clamp_rect.height > 0:
            surface.set_clip(prev_clip.clip(clamp_rect))
        ear_color = (0, 255, 80)
        try:
            if len(left_pts) >= 2:
                pygame.draw.lines(surface, ear_color, False, left_pts, 2)
            if len(right_pts) >= 2:
                pygame.draw.lines(surface, ear_color, False, right_pts, 2)
        except Exception:
            pass
        surface.set_clip(prev_clip)

    @staticmethod
    def _ownship_altitude_msl_ft() -> float:
        def _read_from(src: object) -> Optional[float]:
            if not isinstance(src, dict):
                return None
            for key in ("ALTITUDE_FT", "ALTITUDE_TARGET_FT", "ALT"):
                try:
                    if key in src:
                        return float(src.get(key, 0.0) or 0.0)
                except Exception:
                    continue
            return None

        try:
            panel = PANEL_BUTTON_STATES if isinstance(PANEL_BUTTON_STATES, dict) else {}
            top_aircraft = panel.get("AIRCRAFT", {}) if isinstance(panel, dict) else {}
            v = _read_from(top_aircraft)
            if v is not None:
                return float(v)
            throttle = panel.get("THROTTLE", {}) if isinstance(panel, dict) else {}
            nested_aircraft = throttle.get("AIRCRAFT", {}) if isinstance(throttle, dict) else {}
            v = _read_from(nested_aircraft)
            if v is not None:
                return float(v)
        except Exception:
            pass
        return 0.0

    @staticmethod
    def _latlon_to_world_px(lat: float, lon: float, zoom: int) -> Tuple[float, float]:
        lat_clamped = max(-85.05112878, min(85.05112878, float(lat)))
        lon_wrapped = ((float(lon) + 180.0) % 360.0) - 180.0
        scale = float(256 * (2 ** int(zoom)))
        x = ((lon_wrapped + 180.0) / 360.0) * scale
        sin_lat = math.sin(math.radians(lat_clamped))
        y = (0.5 - (math.log((1.0 + sin_lat) / max(1e-9, (1.0 - sin_lat))) / (4.0 * math.pi))) * scale
        return float(x), float(y)

    @classmethod
    def _terrain_elevation_m(cls, lat: float, lon: float, zoom: int = 11) -> Optional[float]:
        if Image is None:
            return None
        z = max(0, min(15, int(zoom)))
        wx, wy = cls._latlon_to_world_px(float(lat), float(lon), z)
        tx = int(math.floor(wx / 256.0))
        ty = int(math.floor(wy / 256.0))
        tile = Asr1Format._fetch_terrain_tile(z, tx, ty)
        if tile is None:
            return None
        px = int(wx - (float(tx) * 256.0))
        py = int(wy - (float(ty) * 256.0))
        px = max(0, min(255, int(px)))
        py = max(0, min(255, int(py)))
        try:
            r, g, b = tile.getpixel((px, py))
            elev_m = (float(r) * 256.0) + float(g) + (float(b) / 256.0) - 32768.0
            return float(elev_m)
        except Exception:
            return None

    def _ownship_agl_m(self) -> float:
        state = self._state()
        own = self._own_lat_lon()
        alt_msl_m = max(0.0, float(self._ownship_altitude_msl_ft()) * 0.3048)
        if own is None:
            return alt_msl_m
        lat, lon = own
        key = (int(round(float(lat) * 1000.0)), int(round(float(lon) * 1000.0)))
        now_ms = int(pygame.time.get_ticks())
        last_key = state.get("_ears_terrain_key")
        last_ms = int(state.get("_ears_terrain_ms", 0) or 0)
        cached_ground = Tsd1Format._safe_float(state.get("_ears_ground_m"))
        if (
            isinstance(last_key, tuple)
            and len(last_key) == 2
            and tuple(last_key) == tuple(key)
            and cached_ground is not None
            and (now_ms - last_ms) < 1200
        ):
            return max(0.0, alt_msl_m - float(cached_ground))
        ground_m = self._terrain_elevation_m(float(lat), float(lon), zoom=11)
        if ground_m is None:
            ground_m = float(cached_ground) if cached_ground is not None else 0.0
        state["_ears_terrain_key"] = key
        state["_ears_terrain_ms"] = now_ms
        state["_ears_ground_m"] = float(ground_m)
        return max(0.0, alt_msl_m - float(ground_m))

    @staticmethod
    def _sar_outline_xy_m(
        h_m: float,
        az_max_deg: float = 35.0,
        el_min_deg: float = 6.0,
        el_max_deg: float = 45.0,
        steps: int = 120,
    ) -> List[Tuple[float, float]]:
        h = max(0.1, float(h_m))
        az_max = math.radians(float(az_max_deg))
        el_min = math.radians(float(el_min_deg))
        el_max = math.radians(float(el_max_deg))
        count = max(24, int(steps))
        outer: List[Tuple[float, float]] = []
        inner: List[Tuple[float, float]] = []
        for i in range(count):
            t = -1.0 + (2.0 * float(i) / float(max(1, count - 1)))
            # Outer edge (lower elevation).
            az_outer = float(t) * float(az_max)
            d_oz = math.sin(el_min)
            if abs(d_oz) <= 1e-6:
                continue
            t_outer = float(h) / d_oz
            x_outer = math.cos(el_min) * math.cos(az_outer) * t_outer
            y_outer = math.cos(el_min) * math.sin(az_outer) * t_outer
            outer.append((float(x_outer), float(y_outer)))
            # Inner edge (higher elevation, narrower az limit).
            az_limit_inner = float(az_max) * (1.0 - 0.45 * (1.0 ** 1.6))
            az_inner = float(t) * az_limit_inner
            d_iz = math.sin(el_max)
            if abs(d_iz) <= 1e-6:
                continue
            t_inner = float(h) / d_iz
            x_inner = math.cos(el_max) * math.cos(az_inner) * t_inner
            y_inner = math.cos(el_max) * math.sin(az_inner) * t_inner
            inner.append((float(x_inner), float(y_inner)))
        return outer + list(reversed(inner))

    def _draw_hsd_sar_ears(
        self,
        surface: pygame.Surface,
        center: Tuple[int, int],
        range_nm: float,
        heading_deg: float,
        zoom_scale: float,
        clamp_rect: Optional[pygame.Rect] = None,
    ) -> None:
        agl_m = self._ownship_agl_m()
        if agl_m <= 0.5:
            return
        outline_xy = self._sar_outline_xy_m(agl_m, az_max_deg=35.0, el_min_deg=6.0, el_max_deg=45.0, steps=120)
        if len(outline_xy) < 3:
            return
        nm_per_px = max(1e-6, float(range_nm) / float(4.0 * DPI * max(0.01, float(zoom_scale))))
        points: List[Tuple[int, int]] = []
        for x_m, y_m in outline_xy:
            dist_nm = math.hypot(float(x_m), float(y_m)) / 1852.0
            rel_deg = math.degrees(math.atan2(float(y_m), float(x_m)))
            display_deg = float(rel_deg) % 360.0
            radius_px = float(dist_nm) / nm_per_px
            sx, sy = self._polar_from_north(center, radius_px, display_deg)
            points.append((int(sx), int(sy)))
        if len(points) < 3:
            return
        prev_clip = surface.get_clip()
        if isinstance(clamp_rect, pygame.Rect) and clamp_rect.width > 0 and clamp_rect.height > 0:
            surface.set_clip(prev_clip.clip(clamp_rect))
        ear_color = (0, 255, 0)
        try:
            pygame.draw.lines(surface, ear_color, True, points, 1)
        except Exception:
            pass
        surface.set_clip(prev_clip)

    def _set_hsd_secondary_cursor_from_click(self, pos: Tuple[int, int], border_rect: pygame.Rect) -> None:
        if border_rect.width <= 1 or border_rect.height <= 1:
            return
        px = max(border_rect.left, min(border_rect.right - 1, int(pos[0])))
        py = max(border_rect.top, min(border_rect.bottom - 1, int(pos[1])))
        nx = float(px - border_rect.left) / float(max(1, border_rect.width - 1))
        ny = float(py - border_rect.top) / float(max(1, border_rect.height - 1))
        state = self._state()
        state["hsd_secondary_cursor_norm"] = (max(0.0, min(1.0, nx)), max(0.0, min(1.0, ny)))
        state["hsd_secondary_track_id"] = None
        state["hsd_secondary_track_active"] = False
        state["hsd_secondary_last_printed_id"] = ""
        state["hsd_secondary_track_data"] = {}
        state["hsd_secondary_fusion_id"] = ""
        state["hsd_secondary_confidence"] = 0.0

    def _hsd_secondary_cursor_screen_pos(self, border_rect: pygame.Rect) -> Optional[Tuple[int, int]]:
        raw = self._state().get("hsd_secondary_cursor_norm")
        if not isinstance(raw, (tuple, list)) or len(raw) != 2:
            return None
        try:
            nx = float(raw[0])
            ny = float(raw[1])
        except Exception:
            return None
        nx = max(0.0, min(1.0, nx))
        ny = max(0.0, min(1.0, ny))
        x = int(round(border_rect.left + nx * float(max(1, border_rect.width - 1))))
        y = int(round(border_rect.top + ny * float(max(1, border_rect.height - 1))))
        x = max(border_rect.left, min(border_rect.right - 1, x))
        y = max(border_rect.top, min(border_rect.bottom - 1, y))
        return x, y

    @staticmethod
    def _secondary_cursor_shape_params() -> Tuple[int, int, int]:
        # Main crosshair in main.py uses size=25px; draw secondary at 0.75x.
        size = max(3, int(round(25.0 * 0.75)))
        half_len = size
        y_off = size
        return size, half_len, y_off

    def _update_hsd_secondary_cursor_tracking(
        self,
        border_rect: pygame.Rect,
        center: Tuple[int, int],
        adsb_items: List[Dict[str, object]],
    ) -> None:
        state = self._state()
        cursor_pos = self._hsd_secondary_cursor_screen_pos(border_rect)
        if cursor_pos is None:
            state["hsd_secondary_track_active"] = False
            return

        track_id = state.get("hsd_secondary_track_id")
        if isinstance(track_id, str) and track_id != "":
            for item in adsb_items:
                if str(item.get("id", "")) == track_id:
                    tx = int(item.get("x", cursor_pos[0]))
                    ty = int(item.get("y", cursor_pos[1]))
                    nx = float(tx - border_rect.left) / float(max(1, border_rect.width - 1))
                    ny = float(ty - border_rect.top) / float(max(1, border_rect.height - 1))
                    state["hsd_secondary_cursor_norm"] = (max(0.0, min(1.0, nx)), max(0.0, min(1.0, ny)))
                    state["hsd_secondary_track_active"] = True
                    return
            # Keep track lock if target is temporarily unavailable.
            state["hsd_secondary_track_active"] = True
            return

        _, half_len, y_off = self._secondary_cursor_shape_params()
        cx, cy = cursor_pos
        x0 = cx - half_len
        x1 = cx + half_len
        y0 = cy - y_off
        y1 = cy + y_off
        in_box: List[Dict[str, object]] = []
        for item in adsb_items:
            try:
                tx = int(item.get("x", -99999))
                ty = int(item.get("y", -99999))
            except Exception:
                continue
            if tx < x0 or tx > x1 or ty < y0 or ty > y1:
                continue
            in_box.append(item)
        if len(in_box) <= 0:
            state["hsd_secondary_track_active"] = False
            return

        center_x, center_y = center
        best = min(
            in_box,
            key=lambda item: (
                (int(item.get("x", center_x)) - center_x) ** 2
                + (int(item.get("y", center_y)) - center_y) ** 2
            ),
        )
        best_id = str(best.get("id", ""))
        if best_id == "":
            state["hsd_secondary_track_active"] = False
            return
        state["hsd_secondary_track_id"] = best_id
        tx = int(best.get("x", cx))
        ty = int(best.get("y", cy))
        nx = float(tx - border_rect.left) / float(max(1, border_rect.width - 1))
        ny = float(ty - border_rect.top) / float(max(1, border_rect.height - 1))
        state["hsd_secondary_cursor_norm"] = (max(0.0, min(1.0, nx)), max(0.0, min(1.0, ny)))
        state["hsd_secondary_track_active"] = True

    def _draw_hsd_secondary_cursor(self, surface: pygame.Surface, border_rect: pygame.Rect) -> None:
        if not bool(self._state().get("hsd_secondary_track_active", False)):
            return
        pos = self._hsd_secondary_cursor_screen_pos(border_rect)
        if pos is None:
            return
        x, y = pos
        green = (0, 255, 0)
        size, half_len, y_off = self._secondary_cursor_shape_params()
        top_y = y - y_off
        bot_y = y + y_off
        pygame.draw.line(surface, green, (x - half_len, top_y), (x + half_len, top_y), 1)
        pygame.draw.line(surface, green, (x - half_len, bot_y), (x + half_len, bot_y), 1)
        pygame.draw.circle(surface, green, (x, y), max(1, int(round(size * 0.12))), 0)

        box_size = max(6, int(round(0.10 * DPI)))
        indicator = pygame.Rect(
            border_rect.right - box_size - 2,
            border_rect.bottom - box_size - 2,
            box_size,
            box_size,
        )
        pygame.draw.rect(surface, (255, 255, 255), indicator, 1)

    @staticmethod
    def _hsd_border_rect(rect: pygame.Rect) -> pygame.Rect:
        border_inset_x = int(round(0.85 * DPI))
        border_inset_y = int(round(0.5 * DPI))
        return pygame.Rect(
            rect.left + border_inset_x,
            rect.top + border_inset_y,
            rect.width - (2 * border_inset_x),
            rect.height - (2 * border_inset_y),
        )

    def _set_hsd_secondary_cursor_from_click(self, pos: Tuple[int, int], border_rect: pygame.Rect) -> None:
        if border_rect.width <= 1 or border_rect.height <= 1:
            return
        px = max(border_rect.left, min(border_rect.right - 1, int(pos[0])))
        py = max(border_rect.top, min(border_rect.bottom - 1, int(pos[1])))
        nx = float(px - border_rect.left) / float(max(1, border_rect.width - 1))
        ny = float(py - border_rect.top) / float(max(1, border_rect.height - 1))
        self._state()["hsd_secondary_cursor_norm"] = (max(0.0, min(1.0, nx)), max(0.0, min(1.0, ny)))

    def _hsd_secondary_cursor_screen_pos(self, border_rect: pygame.Rect) -> Optional[Tuple[int, int]]:
        raw = self._state().get("hsd_secondary_cursor_norm")
        if not isinstance(raw, (tuple, list)) or len(raw) != 2:
            return None
        try:
            nx = float(raw[0])
            ny = float(raw[1])
        except Exception:
            return None
        nx = max(0.0, min(1.0, nx))
        ny = max(0.0, min(1.0, ny))
        x = int(round(border_rect.left + nx * float(max(1, border_rect.width - 1))))
        y = int(round(border_rect.top + ny * float(max(1, border_rect.height - 1))))
        x = max(border_rect.left, min(border_rect.right - 1, x))
        y = max(border_rect.top, min(border_rect.bottom - 1, y))
        return x, y

    def _draw_hsd_secondary_cursor(self, surface: pygame.Surface, border_rect: pygame.Rect) -> None:
        if not bool(self._state().get("hsd_secondary_track_active", False)):
            return
        pos = self._hsd_secondary_cursor_screen_pos(border_rect)
        if pos is None:
            return
        x, y = pos
        green = (0, 255, 0)
        # Main crosshair in main.py uses size=25px; draw this at 0.75x.
        size = max(3, int(round(25.0 * 0.75)))
        half_len = size
        y_off = size
        top_y = y - y_off
        bot_y = y + y_off
        pygame.draw.line(surface, green, (x - half_len, top_y), (x + half_len, top_y), 1)
        pygame.draw.line(surface, green, (x - half_len, bot_y), (x + half_len, bot_y), 1)
        pygame.draw.circle(surface, green, (x, y), max(1, int(round(size * 0.12))), 0)

    @staticmethod
    def _polar_from_north(center: Tuple[int, int], radius_px: float, angle_deg_from_north: float) -> Tuple[int, int]:
        cx, cy = center
        theta = math.radians(float(angle_deg_from_north))
        x = int(round(cx + radius_px * math.sin(theta)))
        y = int(round(cy - radius_px * math.cos(theta)))
        return x, y

    @staticmethod
    def _safe_float(value: object) -> Optional[float]:
        try:
            return float(value)
        except Exception:
            return None

    def _own_lat_lon(self) -> Optional[Tuple[float, float]]:
        snap = TSD_ADSB_STATE if isinstance(TSD_ADSB_STATE, dict) else {}
        lat = self._safe_float(snap.get("lat"))
        lon = self._safe_float(snap.get("lon"))
        if lat is None or lon is None:
            geo = snap.get("geo")
            if isinstance(geo, dict):
                lat = self._safe_float(geo.get("lat"))
                lon = self._safe_float(geo.get("lon"))
        if lat is None or lon is None:
            return None
        return float(lat), float(lon)

    @staticmethod
    def _classification_to_color(classification: str) -> Optional[Tuple[int, int, int]]:
        token = str(classification).upper().strip()
        if token == "FOE":
            return (255, 0, 0)
        if token == "SUSPECT":
            return (255, 255, 0)
        if token == "UNKNOWN":
            return (255, 255, 255)
        return None

    @staticmethod
    def _classify_contact(contact: Dict[str, object]) -> str:
        # Use affiliation first, then optional explicit threat fields.
        aff = str(contact.get("affiliation", "")).upper().strip()
        norm = Tsd1Format._normalize_track_affiliation(aff)
        if norm in {"UNKNOWN", "SUSPECT", "FOE"}:
            return norm
        for key in ("threat", "threat_level", "hostility", "identity", "iff"):
            raw = str(contact.get(key, "")).upper().strip()
            if raw == "":
                continue
            probe = Tsd1Format._normalize_track_affiliation(raw)
            if probe in {"UNKNOWN", "SUSPECT", "FOE"}:
                return probe
            if raw in {"HOSTILE", "ENEMY", "RED", "BANDIT", "FOE"}:
                return "FOE"
            if raw in {"SUSPECT", "YELLOW", "AMBIGUOUS"}:
                return "SUSPECT"
        return "UNKNOWN"

    @staticmethod
    def _adsb_contact_is_suspect_seed(contact: Dict[str, object]) -> bool:
        # Deterministic 5% split for ADS-B UNKNOWN targets on TWD.
        # Uses stable text fields first so the assignment does not flicker.
        parts: List[str] = []
        for key in ("id", "hex", "icao", "callsign", "registration"):
            raw = str(contact.get(key, "")).strip().upper()
            if raw != "":
                parts.append(raw)
        if len(parts) <= 0:
            lat = Tsd1Format._safe_float(contact.get("lat"))
            lon = Tsd1Format._safe_float(contact.get("lon"))
            if lat is not None and lon is not None:
                parts.append(f"{float(lat):.3f}:{float(lon):.3f}")
            else:
                parts.append("UNKNOWN")
        seed = "|".join(parts)
        acc = 0
        for ch in seed:
            acc = ((acc * 131) + ord(ch)) % 1000003
        return (acc % 20) == 0

    def _twd_display_range_nm(self) -> float:
        # Mirror TSD scale options so TWD threat scaling feels consistent.
        opts = Tsd1Format._range_options()
        idx = 4
        try:
            if isinstance(TSD1_STATE, dict):
                idx = int(TSD1_STATE.get("scale_index", 4) or 4)
        except Exception:
            idx = 4
        if idx < 0 or idx >= len(opts):
            idx = max(0, min(len(opts) - 1, idx))
        try:
            return max(0.1, float(opts[idx]))
        except Exception:
            return 120.0

    def _iter_twd_contacts(self) -> List[Dict[str, object]]:
        contacts: List[Dict[str, object]] = []
        snap = TSD_ADSB_STATE if isinstance(TSD_ADSB_STATE, dict) else {}
        adsb_enabled = bool(snap.get("enabled", False))
        adsb_visible = bool(snap.get("show_live_adsb", True))
        if adsb_enabled and adsb_visible:
            raw_payload = snap.get("raw")
            mil_payload = snap.get("mil_raw")
            try:
                parsed_adsb = Tsd1Format._adsb_contacts(raw_payload, mil_payload=mil_payload)
                for src in parsed_adsb:
                    if not isinstance(src, dict):
                        continue
                    c = dict(src)
                    if self._classify_contact(c) == "UNKNOWN" and self._adsb_contact_is_suspect_seed(c):
                        c["affiliation"] = "SUSPECT"
                    contacts.append(c)
            except Exception:
                pass
        link16_raw = TSD_LINK16_CONTACTS if isinstance(TSD_LINK16_CONTACTS, list) else []
        for item in link16_raw:
            if not isinstance(item, dict):
                continue
            try:
                lat_v = float(item.get("lat"))
                lon_v = float(item.get("lon"))
            except Exception:
                continue
            contacts.append(
                {
                    "id": str(item.get("id", "")).strip(),
                    "lat": lat_v,
                    "lon": lon_v,
                    "heading": float(item.get("heading", 0.0) or 0.0),
                    "speed_kts": float(item.get("speed_kts", 0.0) or 0.0),
                    "affiliation": str(item.get("affiliation", "FRIENDLY")).upper().strip() or "FRIENDLY",
                }
            )
        sim_live = TSD_SIM_CONTACTS if isinstance(TSD_SIM_CONTACTS, list) else []
        for item in sim_live:
            if not isinstance(item, dict):
                continue
            try:
                lat_v = float(item.get("lat"))
                lon_v = float(item.get("lon"))
            except Exception:
                continue
            contacts.append(
                {
                    "id": str(item.get("id", "")).strip() or "PMD_SIM",
                    "lat": lat_v,
                    "lon": lon_v,
                    "heading": float(item.get("heading", 0.0) or 0.0),
                    "speed_kts": float(item.get("speed_kts", 0.0) or 0.0),
                    "affiliation": str(item.get("affiliation", "UNKNOWN")).upper().strip() or "UNKNOWN",
                }
            )
        # Deduplicate by id when available.
        if len(contacts) > 1:
            dedup: Dict[str, Dict[str, object]] = {}
            noid: List[Dict[str, object]] = []
            for c in contacts:
                cid = str(c.get("id", "")).strip()
                if cid == "":
                    noid.append(c)
                    continue
                dedup[cid] = c
            contacts = list(dedup.values()) + noid
        return contacts

    def _draw_threat_targets(
        self,
        surface: pygame.Surface,
        center: Tuple[int, int],
        heading_deg: float,
        r_outer: float,
        sep_held: bool = False,
    ) -> None:
        own = self._own_lat_lon()
        if own is None:
            return
        own_lat, own_lon = own
        range_nm = self._twd_display_range_nm()
        if range_nm <= 0.0:
            return
        contacts = self._iter_twd_contacts()
        if len(contacts) <= 0:
            return
        # Keep icon size proportional to the active TWD ring scale.  Full-size
        # TWD uses a 2.1in outer radius; subportals pass a smaller r_outer.
        icon_px = max(4, int(round(float(r_outer) * ((0.45 * 0.75 * 0.5) / 2.1))))
        edge_margin = max(6.0, float(icon_px) * 0.65)
        rank_map = {"FOE": 1, "SUSPECT": 2, "UNKNOWN": 3}
        items: List[Dict[str, object]] = []
        for contact in contacts:
            lat = self._safe_float(contact.get("lat"))
            lon = self._safe_float(contact.get("lon"))
            if lat is None or lon is None:
                continue
            classification = self._classify_contact(contact)
            color = self._classification_to_color(classification)
            if color is None:
                continue
            try:
                bearing_deg, dist_nm = Tsd1Format._bearing_and_distance_nm(float(own_lat), float(own_lon), float(lat), float(lon))
            except Exception:
                continue
            if dist_nm <= 0.0:
                continue
            radial_px = (float(dist_nm) / float(range_nm)) * float(r_outer)
            # Requested TWD behavior: UNKNOWN (white) threats sit midway
            # between the outer ring and the next inner ring.
            if classification == "UNKNOWN":
                r_mid_ratio = (1.25 / 2.1)
                radial_px = float(r_outer) * ((1.0 + r_mid_ratio) * 0.5)
            if radial_px > float(r_outer):
                continue
            rel_bearing_deg = (float(bearing_deg) - float(heading_deg)) % 360.0
            px, py = self._polar_from_north(center, radial_px, rel_bearing_deg)
            domain = str(contact.get("domain", "AIR")).upper().strip() or "AIR"
            moving = bool(Tsd1Format._safe_float(contact.get("speed_kts")) and float(Tsd1Format._safe_float(contact.get("speed_kts")) or 0.0) >= 10.0)
            emitting = bool(contact.get("emitting", False))
            quality_level = Tsd1Format._track_quality_level(contact)
            icon = Tsd1Format._get_adsb_contact_icon(
                classification,  # force Unknown/Suspect/Foe color family for TWD
                domain,
                icon_px,
                0.0,  # no rotation on TWD; always directly up
                quality_level=quality_level,
                moving=moving,
                emitting=emitting,
                build_if_missing=True,
            )
            if icon is None:
                continue
            # Make TWD icon linework visually thinner than baseline TSD symbols.
            try:
                iw, ih = icon.get_size()
                tw = max(1, int(round(float(iw) * 0.78)))
                th = max(1, int(round(float(ih) * 0.78)))
                shrunk = pygame.transform.smoothscale(icon, (tw, th))
                icon = pygame.transform.smoothscale(shrunk, (iw, ih))
            except Exception:
                pass
            items.append(
                {
                    "x": float(px),
                    "y": float(py),
                    "base_radius": float(radial_px),
                    "rel_bearing_deg": float(rel_bearing_deg),
                    "class": classification,
                    "rank": int(rank_map.get(classification, 3)),
                    "dist_nm": float(dist_nm),
                    "icon": icon,
                    "icon_px": int(icon_px),
                }
            )

        if len(items) <= 0:
            return

        if bool(sep_held) and len(items) > 1:
            # Find overlap clusters and spread each cluster by threat priority.
            overlap_thresh = float(icon_px) * 0.95
            used = [False] * len(items)
            clusters: List[List[int]] = []
            for i in range(len(items)):
                if used[i]:
                    continue
                stack = [i]
                used[i] = True
                cluster = [i]
                while len(stack) > 0:
                    idx = stack.pop()
                    xi = float(items[idx]["x"])
                    yi = float(items[idx]["y"])
                    for j in range(len(items)):
                        if used[j]:
                            continue
                        xj = float(items[j]["x"])
                        yj = float(items[j]["y"])
                        if math.hypot(xj - xi, yj - yi) <= overlap_thresh:
                            used[j] = True
                            stack.append(j)
                            cluster.append(j)
                if len(cluster) > 1:
                    clusters.append(cluster)

            sep_step_px = max(8.0, float(icon_px) * 1.05)
            clock_step_deg = 10.0
            edge_radius = max(0.0, float(r_outer) - edge_margin)
            for cluster in clusters:
                ordered = sorted(
                    cluster,
                    key=lambda idx: (
                        int(items[idx]["rank"]),
                        float(items[idx]["dist_nm"]),
                    ),
                )
                anchor_deg = float(items[ordered[0]]["rel_bearing_deg"])
                base_r = max(6.0, min(float(items[ordered[0]]["base_radius"]), edge_radius))
                for order_idx, item_idx in enumerate(ordered):
                    target_r = base_r + (float(order_idx) * sep_step_px)
                    if target_r <= edge_radius:
                        tx, ty = self._polar_from_north(center, target_r, anchor_deg)
                    else:
                        overflow = target_r - edge_radius
                        cw_steps = int(max(1, math.ceil(overflow / sep_step_px)))
                        target_deg = (anchor_deg + (cw_steps * clock_step_deg)) % 360.0
                        tx, ty = self._polar_from_north(center, edge_radius, target_deg)
                    items[item_idx]["x"] = float(tx)
                    items[item_idx]["y"] = float(ty)

        best_idx: Optional[int] = None
        best_key: Optional[Tuple[int, float]] = None
        for idx, item in enumerate(items):
            key = (int(item["rank"]), float(item["dist_nm"]))
            if best_key is None or key < best_key:
                best_key = key
                best_idx = idx

        for idx, item in enumerate(items):
            icon = item.get("icon")
            if not isinstance(icon, pygame.Surface):
                continue
            px = int(round(float(item["x"])))
            py = int(round(float(item["y"])))
            ir = icon.get_rect(center=(px, py))
            surface.blit(icon, ir)
            if best_idx is not None and idx == best_idx:
                half = max(7, int(round(max(ir.width, ir.height) * 0.93)))
                diamond = [
                    (px, py - half),
                    (px + half, py),
                    (px, py + half),
                    (px - half, py),
                ]
                pygame.draw.polygon(surface, (255, 255, 255), diamond, 1)

    @staticmethod
    def _gol_popup_rows(rect: pygame.Rect) -> Tuple[int, int]:
        is_5x7 = rect.height >= int(7 * DPI) - 1
        row_start = 3
        return row_start, row_start + 3

    def _popup_grid_rect(self, base_rect: pygame.Rect) -> pygame.Rect:
        popup_w = 5 * GRID_CELL_W
        popup_h = 8 * GRID_CELL_H
        width = int(base_rect.width)
        if width <= popup_w:
            x = int(base_rect.x)
        elif width >= int((10 * DPI) - 1):
            try:
                idx = int(TWD_STATE.get("_popup_anchor_portal_idx", 0))
            except Exception:
                idx = 0
            x = int(base_rect.x) if (idx % 2 == 0) else int(base_rect.right - popup_w)
        else:
            x = int(base_rect.x + max(0, (width - popup_w) // 2))
        return pygame.Rect(x, base_rect.top - SIDE_OSB_Y_SHIFT, popup_w, popup_h)

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
        grid = self._popup_grid_rect(rect)
        x = grid.x + col * GRID_CELL_W
        y = grid.y + row * GRID_CELL_H
        w = GRID_CELL_W if col < 4 else (grid.right - x)
        h = GRID_CELL_H if row < 7 else (grid.bottom - y)
        return pygame.Rect(x, y, max(1, w), max(1, h))

    def _popup_cell_at_pos(self, pos: Tuple[int, int], rect: pygame.Rect) -> Optional[str]:
        grid = self._popup_grid_rect(rect)
        rel_x = int(pos[0]) - int(grid.x)
        rel_y = int(pos[1]) - int(grid.y)
        if rel_x < 0 or rel_y < 0 or rel_x >= grid.width or rel_y >= grid.height:
            return None
        col = max(0, min(4, rel_x // max(1, GRID_CELL_W)))
        row = max(0, min(7, rel_y // max(1, GRID_CELL_H)))
        return f"{chr(ord('A') + int(col))}{int(row) + 1}"

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

    def _draw_rwr_ss_popup(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        if not self._rwr_ss_popup_open():
            return
        popup = self._gol_popup_rect(rect)
        row_start, row_end = self._gol_popup_rows(rect)
        if popup.width <= 1 or popup.height <= 1:
            return
        cyan = (0, 255, 255)
        white = (255, 255, 255)
        surface.fill((0, 0, 0), popup)
        pygame.draw.rect(surface, cyan, popup, 1)
        grid = self._popup_grid_rect(rect)
        for c in range(1, 3):
            x = grid.x + (c + 1) * GRID_CELL_W
            pygame.draw.line(surface, cyan, (x, popup.top), (x, popup.bottom), 1)
        for r in range(1, (row_end - row_start + 1)):
            y = grid.y + ((row_start - 1 + r) * GRID_CELL_H)
            pygame.draw.line(surface, cyan, (popup.left, y), (popup.right, y), 1)
        opts = self._rwr_ss_options()
        option_cells = self._gol_popup_option_cells(rect, len(opts))
        idx_sel = self._rwr_ss_idx()
        font = get_font(14)
        for i, opt in enumerate(opts):
            if i >= len(option_cells):
                break
            row = self._popup_cell_rect(rect, option_cells[i])
            if row is None:
                continue
            color = white if i == idx_sel else cyan
            txt = font.render(str(opt), True, color)
            tr = txt.get_rect(center=row.center)
            if i == idx_sel:
                pygame.draw.rect(surface, white, tr.inflate(4, 2), 1)
            surface.blit(txt, tr)

    def _sep_is_held(self, rect: pygame.Rect, is_primary: bool) -> bool:
        if not bool(is_primary):
            return False
        return bool(TWD_STATE.get("sep_hold_mouse", False))

    def _draw_hotas_status(self, surface: pygame.Surface, rect: pygame.Rect, top_y: int) -> None:
        flags: List[str] = []
        if bool(TWD_STATE.get("jam_active", False)):
            flags.append("JAM")
        if bool(TWD_STATE.get("case_jamming", False)):
            flags.append("CASE")
        try:
            asr_state = ASR1_STATE if isinstance(ASR1_STATE, dict) else {}
        except Exception:
            asr_state = {}
        if isinstance(asr_state, dict) and bool(asr_state.get("egl_enabled", False)):
            flags.append("EGL")
        if len(flags) <= 0:
            return
        font = get_font(14)
        surf = font.render("  ".join(flags), True, (0, 255, 0))
        tr = surf.get_rect(centerx=rect.centerx, top=int(top_y))
        pygame.draw.rect(surface, (0, 0, 0), tr.inflate(8, 4), 0)
        surface.blit(surf, tr)

    def _draw_osb_labels(self, surface: pygame.Surface, rect: pygame.Rect, context: FormatContext, sep_held: bool = False) -> None:
        items: List[Tuple[str, ButtonState]] = [
            (
                "L1",
                ButtonState(
                    button_id="TWD_L1",
                    button_type=ButtonType.GOL,
                    function_label="RWR SS",
                    options=self._rwr_ss_options(),
                    selected_index=self._rwr_ss_idx(),
                    h_align="left",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("L1") else 0,
                ),
            ),
            (
                "T2",
                ButtonState(
                    button_id="TWD_T2",
                    button_type=ButtonType.PAGE_ACCESS,
                    text="STBY",
                    h_align="center",
                    v_align="top",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("T2") else 0,
                ),
            ),
            (
                "T5",
                ButtonState(
                    button_id="TWD_T5",
                    button_type=ButtonType.PAGE_ACCESS,
                    text="CNTL>",
                    h_align="center",
                    v_align="top",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("T5") else 0,
                ),
            ),
            (
                "L4",
                ButtonState(
                    button_id="TWD_L4",
                    button_type=ButtonType.MOMENTARY_SINGLE,
                    text="SEP",
                    is_single_function=True,
                    is_on=bool(sep_held),
                    h_align="left",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=0,
                ),
            ),
            (
                "R4",
                ButtonState(
                    button_id="TWD_R4",
                    button_type=ButtonType.PAGE_ACCESS,
                    text="DCLT",
                    h_align="right",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("R4") else 0,
                ),
            ),
        ]
        for label, state in items:
            box = self._osb_box(rect, label)
            if box is None:
                continue
            render_button(surface, box, state, get_font, int(pygame.time.get_ticks()))

    def render(self, surface, rect, is_primary: bool, context: FormatContext) -> None:
        prev_clip = surface.get_clip()
        surface.set_clip(rect)
        surface.fill((0, 0, 0), rect)

        if not is_primary:
            heading_deg = self._read_heading_deg()
            sym_color = (255, 255, 255)
            green = (0, 255, 0)
            title_font_size = 10
            title_clearance = max(14, int(round(0.24 * DPI)))

            # Scale 4.2in symbology to fit the upper subportal area.  Keep
            # clear of the bottom title row, which is always visible.
            target_diam = 4.2 * DPI
            fit_w = max(1, rect.width - 8)
            fit_h = max(1, rect.height - title_clearance - 8)
            sub_scale = max(0.16, min(0.82, min(fit_w / float(target_diam), fit_h / float(target_diam))))

            r_outer = 2.1 * DPI * sub_scale
            r_mid = 1.25 * DPI * sub_scale
            r_inner = 0.5 * DPI * sub_scale
            r_center = 0.125 * DPI * sub_scale
            usable_top = rect.top + 4
            usable_bottom = rect.bottom - title_clearance - 4
            center_y = int(round(usable_top + r_outer))
            center_y = max(int(round(usable_top + r_outer)), min(int(round(usable_bottom - r_outer)), center_y))
            center = (rect.centerx, center_y)
            for radius in (r_outer, r_mid, r_inner, r_center):
                pygame.draw.circle(surface, sym_color, center, int(round(radius)), 1)
            sep_held = self._sep_is_held(rect, is_primary=False)
            self._draw_threat_targets(surface, center, heading_deg, r_outer, sep_held=sep_held)

            base_hash_len = 0.2 * DPI * sub_scale
            for world_deg in range(0, 360, 10):
                display_deg = (float(world_deg) - heading_deg) % 360.0
                is_cardinal = (world_deg % 90) == 0
                hash_len = base_hash_len * (1.5 if is_cardinal else 1.0)
                p0 = self._polar_from_north(center, r_outer - 1.0, display_deg)
                p1 = self._polar_from_north(center, (r_outer - 1.0) - hash_len, display_deg)
                pygame.draw.line(surface, sym_color, p0, p1, 1)

            # Stationary crosshair segments from 1.0in circle to 4.2in circle.
            for world_deg in (0, 90, 180, 270):
                p_inner = self._polar_from_north(center, r_inner, float(world_deg))
                p_outer = self._polar_from_north(center, r_outer - 1.0, float(world_deg))
                pygame.draw.line(surface, sym_color, p_inner, p_outer, 1)

            # Inner-circle cardinal marks.
            inner_hash_len = base_hash_len
            for world_deg in (90, 270):  # E/W inside only
                display_deg = (float(world_deg) - heading_deg) % 360.0
                p0 = self._polar_from_north(center, r_inner, display_deg)
                p1 = self._polar_from_north(center, r_inner - inner_hash_len, display_deg)
                pygame.draw.line(surface, sym_color, p0, p1, 1)
            s_deg = (180.0 - heading_deg) % 360.0  # S outboard only
            s0 = self._polar_from_north(center, r_inner, s_deg)
            s1 = self._polar_from_north(center, r_inner + inner_hash_len, s_deg)
            pygame.draw.line(surface, sym_color, s0, s1, 1)
            n_deg = (0.0 - heading_deg) % 360.0  # N both ways
            n0 = self._polar_from_north(center, r_inner - inner_hash_len, n_deg)
            n1 = self._polar_from_north(center, r_inner + inner_hash_len, n_deg)
            pygame.draw.line(surface, sym_color, n0, n1, 1)

            # Subportal mode labels.
            mode_font = get_font(max(10, int(round(12 * sub_scale))))
            oper = mode_font.render("OPER", True, green)
            semi = mode_font.render("SEMI", True, green)
            oper_rect = oper.get_rect(left=rect.left + 4, top=rect.top + 2)
            semi_rect = semi.get_rect(right=rect.right - 4, top=rect.top + 2)
            surface.blit(oper, oper_rect)
            surface.blit(semi, semi_rect)
            self._draw_hotas_status(surface, rect, rect.top + 18)

            # Subportal format label.
            twd_font = get_font(max(9, int(round(title_font_size * max(0.9, sub_scale)))))
            twd_surf = twd_font.render("TWD", True, (0, 255, 255))
            twd_rect = twd_surf.get_rect(centerx=rect.centerx, bottom=rect.bottom - 2)
            surface.blit(twd_surf, twd_rect)

            pygame.draw.rect(surface, (0, 255, 255), rect, 1)
            surface.set_clip(prev_clip)
            return

        # Keep the TWD symbology at a fixed vertical reference (same as 5x5),
        # while centering horizontally for wider windows.
        center = (rect.centerx, rect.top + int(round(2.625 * DPI)))
        white = (255, 255, 255)
        sym_color = white
        heading_deg = self._read_heading_deg()

        r_outer = 2.1 * DPI       # 4.2 in diameter
        r_mid = 1.25 * DPI        # 2.5 in diameter
        r_inner = 0.5 * DPI       # 1.0 in diameter
        r_center = 0.125 * DPI    # 0.25 in diameter
        for radius in (r_outer, r_mid, r_inner, r_center):
            pygame.draw.circle(surface, sym_color, center, int(round(radius)), 1)

        # Threat target overlay: UNKNOWN (white), SUSPECT (yellow), FOE (red).
        sep_held = self._sep_is_held(rect, is_primary=True)
        self._draw_threat_targets(surface, center, heading_deg, r_outer, sep_held=sep_held)

        # Rotating hash marks every 10 deg on inside of outer circle.
        base_hash_len = 0.2 * DPI
        for world_deg in range(0, 360, 10):
            display_deg = (float(world_deg) - heading_deg) % 360.0
            is_cardinal = (world_deg % 90) == 0
            hash_len = base_hash_len * (1.5 if is_cardinal else 1.0)
            p0 = self._polar_from_north(center, r_outer - 1.0, display_deg)
            p1 = self._polar_from_north(center, (r_outer - 1.0) - hash_len, display_deg)
            pygame.draw.line(surface, sym_color, p0, p1, 1)

        # Crosshair segments from 1.0in circle to 4.2in circle (stationary on screen).
        for world_deg in (0, 90, 180, 270):
            display_deg = float(world_deg)
            p_inner = self._polar_from_north(center, r_inner, display_deg)
            p_outer = self._polar_from_north(center, r_outer - 1.0, display_deg)
            pygame.draw.line(surface, sym_color, p_inner, p_outer, 1)

        # Additional inner-circle cardinal marks at the 1.0in circle.
        # E/W: inside-only marks (same length as regular hash).
        inner_hash_len = base_hash_len
        for world_deg in (90, 270):
            display_deg = (float(world_deg) - heading_deg) % 360.0
            p0 = self._polar_from_north(center, r_inner, display_deg)
            p1 = self._polar_from_north(center, r_inner - inner_hash_len, display_deg)
            pygame.draw.line(surface, sym_color, p0, p1, 1)
        # S: outboard-only mark from the 1.0in circle.
        s_deg = (180.0 - heading_deg) % 360.0
        s0 = self._polar_from_north(center, r_inner, s_deg)
        s1 = self._polar_from_north(center, r_inner + inner_hash_len, s_deg)
        pygame.draw.line(surface, sym_color, s0, s1, 1)
        # N: both-way mark crossing the 1.0in circle.
        n_deg = (0.0 - heading_deg) % 360.0
        n0 = self._polar_from_north(center, r_inner - inner_hash_len, n_deg)
        n1 = self._polar_from_north(center, r_inner + inner_hash_len, n_deg)
        pygame.draw.line(surface, sym_color, n0, n1, 1)

        # Rotating N/E/S/W labels at cardinals.
        nsew: List[Tuple[str, int]] = [("N", 0), ("E", 90), ("S", 180), ("W", 270)]
        nsew_font = get_font(14)
        nsew_radius = r_outer - (base_hash_len * 1.5) - (0.10 * DPI)
        for txt, world_deg in nsew:
            display_deg = (float(world_deg) - heading_deg) % 360.0
            tx, ty = self._polar_from_north(center, nsew_radius, display_deg)
            surf = nsew_font.render(txt, True, sym_color)
            # Rotate the glyphs with heading (not just their position).
            rot = pygame.transform.rotate(surf, float(heading_deg))
            tr = rot.get_rect(center=(tx, ty))
            surface.blit(rot, tr)

        # Heading readout between 4.2in and 2.5in circles at top.
        heading_int = int(round(heading_deg)) % 360
        heading_text = f"{heading_int:03d}"
        heading_font = get_font(16)
        heading_surf = heading_font.render(heading_text, True, white)
        heading_radius = (r_outer + r_mid) * 0.5
        hx, hy = self._polar_from_north(center, heading_radius, 0.0)
        heading_rect = heading_surf.get_rect(center=(hx, hy))
        heading_box = heading_rect.inflate(6, 4)
        pygame.draw.rect(surface, (0, 0, 0), heading_box, 0)
        pygame.draw.rect(surface, white, heading_box, 1)
        surface.blit(heading_surf, heading_rect)
        self._draw_hotas_status(surface, rect, rect.top + DISPLAY_OSB_H + 4)

        self._draw_osb_labels(surface, rect, context, sep_held=sep_held)
        self._draw_rwr_ss_popup(surface, rect)
        pygame.draw.rect(surface, (0, 255, 255), rect, 1)
        surface.set_clip(prev_clip)

    def on_osb(self, label: str, context: FormatContext) -> bool:
        self._set_popup_anchor_portal_index(getattr(context, "portal_index", None))
        if label == "T1":
            context.request_vded(context.portal_index, "MENU")
            return True
        if label == "L1":
            self._set_rwr_ss_popup_open(not self._rwr_ss_popup_open())
            return True
        if label == "L4":
            # Actual hold-state is driven directly by mouse down/up in main loop.
            return True
        if label in {"T2", "T5", "L4", "R4"}:
            return True
        return False

    def on_click(self, pos: Tuple[int, int], rect: pygame.Rect, context: FormatContext) -> bool:
        self._set_popup_anchor_portal_index(getattr(context, "portal_index", None))
        if not self._rwr_ss_popup_open():
            return False
        popup = self._gol_popup_rect(rect)
        if not popup.collidepoint(pos):
            self._set_rwr_ss_popup_open(False)
            return False
        cell = self._popup_cell_at_pos(pos, rect)
        if cell is None:
            return True
        opts = self._rwr_ss_options()
        option_cells = self._gol_popup_option_cells(rect, len(opts))
        if cell in option_cells:
            idx = int(option_cells.index(cell))
            self._set_rwr_ss_idx(idx)
            self._set_rwr_ss_popup_open(False)
            return True
        return False

    def on_right_click(self, pos: Tuple[int, int], rect: pygame.Rect, context: FormatContext) -> bool:
        return False

    def on_key(self, key: str) -> bool:
        return False
