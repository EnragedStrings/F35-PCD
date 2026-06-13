from formats import *  # noqa: F401,F403


class EfiFormat(FormatBase):
    name: str = "EFI"
    _cyan_aircraft_cache: Dict[int, Optional[pygame.Surface]] = {}
    _aoa_icon_cache: Dict[Tuple[int, int], Optional[pygame.Surface]] = {}

    def __init__(self) -> None:
        self._data_selected: Optional[str] = None
        self._data_inputs: Dict[str, str] = {"L6": "", "R6": ""}
        self._cdi_options: List[str] = ["LRP", "STPT", "TCN", "LOC"]
        self._cdi_idx: int = 2
        self._cdi_menu_open: bool = False
        self._hdg_value: int = int(round(self._read_heading_deg())) % 360
        self._loc_value: int = 207
        self._loc_user_set: bool = False
        self._tacan_autoset_key: Optional[Tuple[int, str, str]] = None
        self._tacan_solution_cache_key: Optional[Tuple[float, float, int, str, str]] = None
        self._tacan_solution_cache_until_ms: int = 0
        self._tacan_solution_cache_value: Optional[Dict[str, object]] = None
        self._ils_solution_cache_key: Optional[Tuple[float, float, float]] = None
        self._ils_solution_cache_until_ms: int = 0
        self._ils_solution_cache_value: Optional[Dict[str, object]] = None
        self._radar_alt_cache_key: Optional[Tuple[int, int, int]] = None
        self._radar_alt_cache_until_ms: int = 0
        self._radar_alt_cache_value_ft: float = 0.0

    @staticmethod
    def _read_heading_deg() -> float:
        heading = float(TWD_STATE.get("heading_deg", 35.0))
        try:
            panel = PANEL_BUTTON_STATES if isinstance(PANEL_BUTTON_STATES, dict) else {}
            # Prefer live ownship heading if available.
            aircraft_top = panel.get("AIRCRAFT", {}) if isinstance(panel, dict) else {}
            aircraft_nested = {}
            if isinstance(aircraft_top, dict):
                for key in ("HEADING_DEG", "HDG_DEG", "HEADING", "HDG"):
                    if key in aircraft_top:
                        heading = float(aircraft_top.get(key, heading))
                        break
            # Backward compatibility for older nested location.
            throttle = panel.get("THROTTLE", {}) if isinstance(panel, dict) else {}
            if isinstance(throttle, dict):
                aircraft_nested = throttle.get("AIRCRAFT", {})
                if isinstance(aircraft_nested, dict):
                    for key in ("HEADING_DEG", "HDG_DEG", "HEADING", "HDG"):
                        if key in aircraft_nested:
                            heading = float(aircraft_nested.get(key, heading))
                            break
            # No HSI transition spin: use the published heading as-is.
        except Exception:
            pass
        heading = float(heading) % 360.0
        if heading < 0:
            heading += 360.0
        return heading

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
            panel = PANEL_BUTTON_STATES if isinstance(PANEL_BUTTON_STATES, dict) else {}
            aircraft_top = panel.get("AIRCRAFT", {})
            if not isinstance(aircraft_top, dict):
                aircraft_top = {}
                panel["AIRCRAFT"] = aircraft_top
            for key in ("HEADING_DEG", "HDG_DEG", "HEADING", "HDG"):
                aircraft_top[key] = float(heading)
            throttle = panel.get("THROTTLE", {})
            if not isinstance(throttle, dict):
                throttle = {}
                panel["THROTTLE"] = throttle
            aircraft_nested = throttle.get("AIRCRAFT", {})
            if not isinstance(aircraft_nested, dict):
                aircraft_nested = {}
                throttle["AIRCRAFT"] = aircraft_nested
            for key in ("HEADING_DEG", "HDG_DEG", "HEADING", "HDG"):
                aircraft_nested[key] = float(heading)
        except Exception:
            pass

    @staticmethod
    def _safe_float(value: object, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return float(default)

    @staticmethod
    def _safe_float_opt(value: object) -> Optional[float]:
        try:
            return float(value)
        except Exception:
            return None

    @staticmethod
    def _read_own_lat_lon() -> Optional[Tuple[float, float]]:
        snap = TSD_ADSB_STATE if isinstance(TSD_ADSB_STATE, dict) else {}
        lat = EfiFormat._safe_float_opt(snap.get("lat"))
        lon = EfiFormat._safe_float_opt(snap.get("lon"))
        if lat is None or lon is None:
            geo = snap.get("geo")
            if isinstance(geo, dict):
                lat = EfiFormat._safe_float_opt(geo.get("lat"))
                lon = EfiFormat._safe_float_opt(geo.get("lon"))
        if lat is None or lon is None:
            return None
        return float(lat), float(lon)

    @staticmethod
    def _parse_inhg(value: object) -> Optional[float]:
        txt = str(value or "").strip()
        if txt == "":
            return None
        txt = "".join(ch for ch in txt if ch.isdigit() or ch in {".", "-"})
        if txt in {"", ".", "-", "-."}:
            return None
        try:
            v = float(txt)
        except Exception:
            return None
        if not math.isfinite(v):
            return None
        return float(v)

    @staticmethod
    def _parse_hpa(value: object) -> Optional[float]:
        txt = "".join(ch for ch in str(value or "") if ch.isdigit())
        if txt == "":
            return None
        try:
            v = float(txt)
        except Exception:
            return None
        if not math.isfinite(v):
            return None
        return float(v)

    def _selected_baro_inhg(self) -> float:
        state = ALTITUDE_STATE if isinstance(ALTITUDE_STATE, dict) else {}
        source = str(state.get("line1_source", "E1") or "E1").upper()
        inhg_from_e1 = self._parse_inhg(state.get("baro_inhg", "29.92"))
        hpa_from_e2 = self._parse_hpa(state.get("hpa", "1013"))
        inhg_from_e2 = (float(hpa_from_e2) / 33.8638866667) if hpa_from_e2 is not None else None
        selected = inhg_from_e2 if source == "E2" else inhg_from_e1
        if selected is None:
            selected = inhg_from_e1 if inhg_from_e1 is not None else inhg_from_e2
        if selected is None:
            selected = 29.92
        return max(20.0, min(35.0, float(selected)))

    def _baro_display_altitude_ft(self, true_altitude_msl_ft: float) -> float:
        # Display-only pressure baseline offset; does not modify aircraft position.
        setting_inhg = self._selected_baro_inhg()
        offset_ft = (29.92 - float(setting_inhg)) * 1000.0
        return max(0.0, float(true_altitude_msl_ft) + float(offset_ft))

    def _radar_altitude_ft(self, true_altitude_msl_ft: float) -> float:
        own = self._read_own_lat_lon()
        if own is None:
            return max(0.0, float(true_altitude_msl_ft))
        lat, lon = own
        key = (
            int(round(float(lat) * 1000.0)),
            int(round(float(lon) * 1000.0)),
            int(round(max(0.0, float(true_altitude_msl_ft)))),
        )
        now_ms = int(pygame.time.get_ticks())
        if self._radar_alt_cache_key == key and now_ms < int(self._radar_alt_cache_until_ms):
            return max(0.0, float(self._radar_alt_cache_value_ft))
        ground_m: Optional[float] = None
        try:
            terrain_cls = globals().get("Tsd1Format")
            if terrain_cls is not None and hasattr(terrain_cls, "_terrain_elevation_m"):
                ground_m = terrain_cls._terrain_elevation_m(float(lat), float(lon), zoom=11)
        except Exception:
            ground_m = None
        if ground_m is None:
            radar_ft = max(0.0, float(true_altitude_msl_ft))
        else:
            radar_ft = max(0.0, float(true_altitude_msl_ft) - (float(ground_m) * 3.280839895013123))
        self._radar_alt_cache_key = key
        self._radar_alt_cache_until_ms = now_ms + 700
        self._radar_alt_cache_value_ft = float(radar_ft)
        return float(radar_ft)

    @staticmethod
    def _nav_tacan_selector() -> Tuple[int, str, str]:
        nav_state = NAV_STATE if isinstance(NAV_STATE, dict) else {}
        raw_channel = "".join(ch for ch in str(nav_state.get("c1_value", "001")) if ch.isdigit())
        try:
            channel = int(raw_channel) if raw_channel != "" else 1
        except Exception:
            channel = 1
        channel = max(0, min(126, int(channel)))
        band = "Y" if int(nav_state.get("c2_mode", 0)) == 1 else "X"
        options = nav_state.get("c3_options", ["RECV", "T/R", "A-A RCV", "A-A T/R"])
        if not isinstance(options, list) or len(options) <= 0:
            options = ["RECV", "T/R", "A-A RCV", "A-A T/R"]
        try:
            idx = max(0, min(len(options) - 1, int(nav_state.get("c3_idx", 0))))
        except Exception:
            idx = 0
        mode = str(options[idx]).upper().strip()
        return int(channel), str(band), str(mode)

    @staticmethod
    def _mode_allows_ground_tacan(mode: str) -> bool:
        m = str(mode).upper().strip()
        return m in {"RECV", "T/R"}

    @staticmethod
    def _mode_tacan_max_range_nm(mode: str) -> float:
        m = str(mode).upper().strip()
        if m == "T/R":
            return 260.0
        return 220.0

    @staticmethod
    def _nav_ils_frequency_text() -> str:
        nav_state = NAV_STATE if isinstance(NAV_STATE, dict) else {}
        text = str(nav_state.get("b1_value", "110.500")).strip()
        return text if text != "" else "110.500"

    def _find_nav_ils_solution(self) -> Optional[Dict[str, object]]:
        own = self._read_own_lat_lon()
        if own is None:
            return None
        own_lat, own_lon = own
        try:
            freq_mhz = float(self._nav_ils_frequency_text())
        except Exception:
            return None
        cache_key = (
            round(float(own_lat), 3),
            round(float(own_lon), 3),
            round(float(freq_mhz), 3),
        )
        now_ms = int(pygame.time.get_ticks())
        if (
            self._ils_solution_cache_key == cache_key
            and now_ms < int(self._ils_solution_cache_until_ms)
        ):
            return self._ils_solution_cache_value
        solution = Tsd1Format._resolve_faa_ils_solution(
            float(freq_mhz),
            own_lat=float(own_lat),
            own_lon=float(own_lon),
            max_range_nm=220.0,
        )
        self._ils_solution_cache_key = cache_key
        self._ils_solution_cache_until_ms = now_ms + 500
        self._ils_solution_cache_value = solution
        return solution

    @staticmethod
    def _parse_tacan_channel_band(raw_channel: object) -> Optional[Tuple[int, str]]:
        text = str(raw_channel or "").strip().upper()
        if text == "":
            return None
        m = re.match(r"^0*([0-9]{1,3})([XY])$", text)
        if m is None:
            return None
        try:
            ch = int(m.group(1))
        except Exception:
            return None
        if ch < 1 or ch > 126:
            return None
        band = str(m.group(2)).upper()
        if band not in {"X", "Y"}:
            return None
        return int(ch), str(band)

    @staticmethod
    def _angle_delta_deg(a_deg: float, b_deg: float) -> float:
        return ((float(a_deg) - float(b_deg) + 180.0) % 360.0) - 180.0

    def _resolve_tacan_airport_ident(
        self,
        nav: Dict[str, object],
        tacan_lat: float,
        tacan_lon: float,
    ) -> str:
        ident = str(nav.get("associated_airport") or "").strip().upper()
        if ident != "":
            return ident
        runways = Tsd1Format._load_runways()
        if len(runways) <= 0:
            return ""
        best_ident = ""
        best_dist = float("inf")
        for rw in runways:
            try:
                mid_lat = float(rw.get("mid_lat"))
                mid_lon = float(rw.get("mid_lon"))
                rw_ident = str(rw.get("airport_ident") or "").strip().upper()
            except Exception:
                continue
            if rw_ident == "":
                continue
            _brg, dist_nm = Tsd1Format._bearing_and_distance_nm(
                float(tacan_lat),
                float(tacan_lon),
                float(mid_lat),
                float(mid_lon),
            )
            if float(dist_nm) < best_dist:
                best_dist = float(dist_nm)
                best_ident = rw_ident
        if best_ident == "" or best_dist > 30.0:
            return ""
        return best_ident

    def _runway_course_for_airport(
        self,
        airport_ident: str,
        bearing_to_station_deg: float,
        tacan_lat: float,
        tacan_lon: float,
    ) -> Optional[Dict[str, object]]:
        ident = str(airport_ident or "").strip().upper()
        if ident == "":
            return None
        runways = Tsd1Format._load_runways()
        if len(runways) <= 0:
            return None
        candidates: List[Dict[str, object]] = []
        for rw in runways:
            if str(rw.get("airport_ident") or "").strip().upper() != ident:
                continue
            candidates.append(rw)
        if len(candidates) <= 0:
            return None

        def _candidate_key(rw: Dict[str, object]) -> Tuple[float, float]:
            try:
                mid_lat = float(rw.get("mid_lat"))
                mid_lon = float(rw.get("mid_lon"))
                _brg, dist_nm = Tsd1Format._bearing_and_distance_nm(
                    float(tacan_lat),
                    float(tacan_lon),
                    float(mid_lat),
                    float(mid_lon),
                )
            except Exception:
                dist_nm = 99999.0
            try:
                length_ft = float(rw.get("length_ft", 0.0) or 0.0)
            except Exception:
                length_ft = 0.0
            return (float(dist_nm), -float(length_ft))

        runway = min(candidates, key=_candidate_key)
        try:
            le_hdg = float(runway.get("le_heading_deg", 0.0)) % 360.0
        except Exception:
            return None
        le_ident = str(runway.get("le_ident") or "").strip().upper()
        he_ident = str(runway.get("he_ident") or "").strip().upper()
        if le_ident == "":
            le_ident = "RWY"
        if he_ident == "":
            he_ident = le_ident

        options = [
            (float(le_hdg), le_ident),
            ((float(le_hdg) + 180.0) % 360.0, he_ident),
        ]
        chosen_course, chosen_rwy = min(
            options,
            key=lambda item: abs(self._angle_delta_deg(float(item[0]), float(bearing_to_station_deg))),
        )
        return {
            "airport_ident": ident,
            "runway_course_deg": float(chosen_course) % 360.0,
            "runway_ident": str(chosen_rwy),
        }

    def _find_nav_tacan_solution(self) -> Optional[Dict[str, object]]:
        own = self._read_own_lat_lon()
        if own is None:
            return None
        own_lat, own_lon = own
        channel, band, mode = self._nav_tacan_selector()
        if int(channel) < 1:
            return None
        if not self._mode_allows_ground_tacan(mode):
            return None
        cache_key = (
            round(float(own_lat), 3),
            round(float(own_lon), 3),
            int(channel),
            str(band),
            str(mode),
        )
        now_ms = int(pygame.time.get_ticks())
        if (
            self._tacan_solution_cache_key == cache_key
            and now_ms < int(self._tacan_solution_cache_until_ms)
        ):
            return self._tacan_solution_cache_value
        max_range_nm = self._mode_tacan_max_range_nm(mode)
        best: Optional[Dict[str, object]] = None
        best_nav: Optional[Dict[str, object]] = None
        best_lat = 0.0
        best_lon = 0.0
        best_dist = float("inf")
        for nav in Tsd1Format._load_tacan_vor_navaids():
            if not isinstance(nav, dict):
                continue
            nav_type = str(nav.get("type", "")).upper().strip()
            if ("TACAN" not in nav_type) and (nav_type != "VORTAC"):
                continue
            nav_chan = Tsd1Format._format_tacan_channel(nav.get("dme_channel"))
            parsed = self._parse_tacan_channel_band(nav_chan)
            if parsed is None:
                continue
            nav_channel, nav_band = parsed
            if int(nav_channel) != int(channel) or str(nav_band) != str(band):
                continue
            lat = self._safe_float_opt(nav.get("lat"))
            lon = self._safe_float_opt(nav.get("lon"))
            if lat is None or lon is None:
                continue
            bearing_deg, dist_nm = Tsd1Format._bearing_and_distance_nm(
                float(own_lat),
                float(own_lon),
                float(lat),
                float(lon),
            )
            if float(dist_nm) > float(max_range_nm):
                continue
            if float(dist_nm) < best_dist:
                best_dist = float(dist_nm)
                best_nav = nav
                best_lat = float(lat)
                best_lon = float(lon)
                best = {
                    "bearing_deg": float(bearing_deg) % 360.0,
                    "distance_nm": float(dist_nm),
                    "ident": str(nav.get("ident", "")).strip().upper(),
                    "channel": int(channel),
                    "band": str(band),
                    "mode": str(mode),
                }
        if isinstance(best, dict) and isinstance(best_nav, dict):
            airport_ident = self._resolve_tacan_airport_ident(best_nav, float(best_lat), float(best_lon))
            best["airport_ident"] = str(airport_ident)
            best["tacan_lat"] = float(best_lat)
            best["tacan_lon"] = float(best_lon)
            runway_solution = self._runway_course_for_airport(
                str(airport_ident),
                float(best.get("bearing_deg", 0.0)),
                float(best_lat),
                float(best_lon),
            )
            if isinstance(runway_solution, dict):
                best.update(runway_solution)
        self._tacan_solution_cache_key = cache_key
        self._tacan_solution_cache_until_ms = now_ms + 500
        self._tacan_solution_cache_value = best
        return best

    @classmethod
    def _read_aircraft_scalar(cls, keys: Tuple[str, ...], default: float = 0.0) -> float:
        panel = PANEL_BUTTON_STATES if isinstance(PANEL_BUTTON_STATES, dict) else {}
        aircraft_top = panel.get("AIRCRAFT", {}) if isinstance(panel, dict) else {}
        throttle = panel.get("THROTTLE", {}) if isinstance(panel, dict) else {}
        aircraft_nested = throttle.get("AIRCRAFT", {}) if isinstance(throttle, dict) else {}
        for src in (aircraft_top, aircraft_nested):
            if not isinstance(src, dict):
                continue
            for key in keys:
                if key in src:
                    return cls._safe_float(src.get(key, default), default)
        return float(default)

    @classmethod
    def _read_global_attitude_deg(cls) -> float:
        # Prefer explicitly published global attitude keys.
        return float(
            cls._read_aircraft_scalar(
                ("ATTITUDE", "ATT_PITCH_RAW_DEG", "ATT_PITCH_DEG", "PITCH"),
                0.0,
            )
        )

    @classmethod
    def _read_global_bank_deg(cls) -> float:
        # Prefer explicitly published global bank keys.
        return float(
            cls._read_aircraft_scalar(
                ("BANK", "ATT_ROLL_RAW_DEG", "ATT_ROLL_DEG", "ROLL"),
                0.0,
            )
        )

    @staticmethod
    def _normalize_signed_angle_deg(value: float) -> float:
        return ((float(value) + 180.0) % 360.0) - 180.0

    @staticmethod
    def _fold_ladder_label_deg(value_deg: float) -> int:
        v = abs(float(value_deg))
        if v > 90.0:
            v = 180.0 - v
        return max(0, int(round(v)))

    @staticmethod
    def _upright_rotation_deg(value_deg: float) -> float:
        angle = float(value_deg)
        while angle > 90.0:
            angle -= 180.0
        while angle < -90.0:
            angle += 180.0
        return angle

    @staticmethod
    def _rotate_screen_offset(dx: float, dy: float, angle_deg: float) -> Tuple[float, float]:
        # Screen-space rotation (y grows downward), positive angle = CCW visual.
        rad = math.radians(float(angle_deg))
        c = math.cos(rad)
        s = math.sin(rad)
        return (dx * c) + (dy * s), (-dx * s) + (dy * c)

    @staticmethod
    def _draw_dashed_line(
        surface: pygame.Surface,
        color: Tuple[int, int, int],
        start: Tuple[float, float],
        end: Tuple[float, float],
        *,
        dash_px: float,
        gap_px: float,
        width: int = 1,
    ) -> None:
        x1, y1 = float(start[0]), float(start[1])
        x2, y2 = float(end[0]), float(end[1])
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        if length <= 1e-6:
            return
        ux = dx / length
        uy = dy / length
        step_dash = max(1.0, float(dash_px))
        step_gap = max(0.0, float(gap_px))
        pos = 0.0
        while pos < length:
            seg_start = pos
            seg_end = min(length, pos + step_dash)
            p0 = (int(round(x1 + (ux * seg_start))), int(round(y1 + (uy * seg_start))))
            p1 = (int(round(x1 + (ux * seg_end))), int(round(y1 + (uy * seg_end))))
            pygame.draw.line(surface, color, p0, p1, max(1, int(width)))
            pos += step_dash + step_gap

    def _draw_adi(
        self,
        surface: pygame.Surface,
        adi_rect: pygame.Rect,
        *,
        sym_color: Tuple[int, int, int] = (255, 255, 255),
        draw_background: bool = True,
        draw_symbology: bool = True,
        draw_nose_symbol: bool = True,
        draw_horizon_gap_arrow: bool = True,
        line_width: int = 1,
        nose_y_override: Optional[float] = None,
        px_per_deg_override: Optional[float] = None,
        ladder_spacing_scale: float = 1.0,
        pitch_deg_override: Optional[float] = None,
        bank_deg_override: Optional[float] = None,
        ladder_numbers_left_only: bool = False,
        w_vertical_offset_px: float = 0.0,
        ladder_width_scale: float = 1.0,
    ) -> None:
        white = tuple(sym_color)
        pure_blue = (0, 0, 255)
        pure_brown = (165, 42, 42)
        sym_line_w = max(1, int(line_width))

        if pitch_deg_override is None:
            pitch_deg = self._normalize_signed_angle_deg(self._read_global_attitude_deg())
        else:
            pitch_deg = self._normalize_signed_angle_deg(float(pitch_deg_override))
        if bank_deg_override is None:
            bank_deg = self._normalize_signed_angle_deg(self._read_global_bank_deg())
        else:
            bank_deg = self._normalize_signed_angle_deg(float(bank_deg_override))
        world_rotation_deg = float(bank_deg)

        nose_x = int(adi_rect.centerx)
        if nose_y_override is None:
            nose_y = int(round(adi_rect.top + ((4.0 / 3.0) * DPI)))
        else:
            nose_y = int(round(float(nose_y_override)))
        nose_y = max(adi_rect.top + 2, min(adi_rect.bottom - 3, nose_y))
        nose_center = (nose_x, nose_y)

        if px_per_deg_override is None:
            px_per_deg = 0.1 * DPI
        else:
            px_per_deg = max(0.01, float(px_per_deg_override))
        spacing_scale = max(0.1, float(ladder_spacing_scale))
        ladder_px_per_deg = float(px_per_deg) * spacing_scale
        horizon_gap_px = 0.7 * DPI
        nose_radius_px = 0.1 * DPI
        nose_side_len_px = 0.2 * DPI
        nose_top_len_px = 0.1 * DPI
        ladder_outboard_len_px = 0.6 * DPI * max(0.1, float(ladder_width_scale))
        ladder_tick_len_px = 0.1 * DPI
        ladder_gap_center_x = ((horizon_gap_px * 0.5) + (nose_radius_px + nose_side_len_px)) * 0.5

        world_size = int(max(adi_rect.width, adi_rect.height) * 3)
        if world_size % 2 != 0:
            world_size += 1
        world_size = max(world_size, int(6 * DPI))
        world = pygame.Surface((world_size, world_size), pygame.SRCALPHA)
        wcx = world_size // 2
        wcy = world_size // 2

        # Keep pitch mapping aligned with rung spacing so degree labels remain accurate.
        horizon_offset_px = float(pitch_deg) * float(ladder_px_per_deg)
        horizon_world_y = float(wcy) + horizon_offset_px

        if draw_background:
            world.fill((*pure_brown, 255))
            sky_bottom = int(round(max(0.0, min(float(world_size), horizon_world_y))))
            if sky_bottom > 0:
                pygame.draw.rect(world, pure_blue, pygame.Rect(0, 0, world_size, sky_bottom), 0)
        else:
            world.fill((0, 0, 0, 0))

        ladder_font = get_font(12)
        text_entries: List[Tuple[str, float, float, str, float]] = []
        if draw_symbology:
            hy = int(round(horizon_world_y))
            if -2 <= hy <= (world_size + 2):
                half_h_gap = 0.5 * horizon_gap_px
                left_end = int(round(wcx - half_h_gap))
                right_start = int(round(wcx + half_h_gap))
                pygame.draw.line(world, white, (0, hy), (left_end, hy), sym_line_w)
                pygame.draw.line(world, white, (right_start, hy), (world_size - 1, hy), sym_line_w)
                if draw_horizon_gap_arrow:
                    # Left horizon-gap arrow: tip sits at the left edge of the center gap.
                    arrow_len = max(4, int(round(0.09 * DPI)))
                    arrow_half_h = max(3, int(round(0.05 * DPI)))
                    arrow_pts = [
                        (left_end, hy),
                        (left_end - arrow_len, hy - arrow_half_h),
                        (left_end - arrow_len, hy + arrow_half_h),
                    ]
                    pygame.draw.polygon(world, white, arrow_pts, sym_line_w)

            dash_px = 0.08 * DPI
            gap_px = 0.05 * DPI
            text_above_outboard_px = 0.02 * DPI
            text_90_outside_px = 0.03 * DPI
            text_above_inboard_shift_px = 4.0
            text_above_down_shift_px = 2.0
            text_below_outboard_shift_px = 4.0

            for rung_deg in range(-175, 180, 5):
                if rung_deg == 0:
                    continue
                # No -90 symbology. +90 is handled as a special above-horizon rung.
                if rung_deg == -90:
                    continue
                folded_label = self._fold_ladder_label_deg(rung_deg)
                if folded_label <= 0:
                    continue
                rung_world_y = horizon_world_y - (float(rung_deg) * float(ladder_px_per_deg))
                if rung_world_y < (-1.0 * DPI) or rung_world_y > (world_size + (1.0 * DPI)):
                    continue

                # Past +/-90, invert only line geometry by vertical mirroring.
                inverted_marking = abs(int(rung_deg)) > 90
                use_above_style = bool(rung_deg > 0)

                for side in (-1.0, 1.0):
                    x_gap_mid = float(wcx) + (side * float(ladder_gap_center_x))
                    y0 = float(rung_world_y)
                    if use_above_style:
                        x_out = x_gap_mid + (side * float(ladder_outboard_len_px))
                        pygame.draw.line(
                            world,
                            white,
                            (int(round(x_gap_mid)), int(round(y0))),
                            (int(round(x_out)), int(round(y0))),
                            sym_line_w,
                        )
                        # +90 has only horizontal segment + text.
                        if rung_deg != 90:
                            tick_dir = -1.0 if inverted_marking else 1.0
                            y_down = y0 + (tick_dir * float(ladder_tick_len_px))
                            pygame.draw.line(
                                world,
                                white,
                                (int(round(x_out)), int(round(y0))),
                                (int(round(x_out)), int(round(y_down))),
                                sym_line_w,
                            )
                            above_text_x = x_out + (side * (float(text_above_outboard_px) - float(text_above_inboard_shift_px)))
                            if inverted_marking:
                                # Mirror text vertically with the mirrored (>90) line geometry.
                                above_text_y = y0 - float(text_above_down_shift_px)
                                above_anchor_mode = "bottom_outboard"
                            else:
                                above_text_y = y0 + float(text_above_down_shift_px)
                                above_anchor_mode = "top_outboard"
                            if (not ladder_numbers_left_only) or side < 0.0:
                                text_entries.append(
                                    (
                                        str(folded_label),
                                        above_text_x,
                                        above_text_y,
                                        above_anchor_mode,
                                        side,
                                    )
                                )
                        else:
                            if (not ladder_numbers_left_only) or side < 0.0:
                                text_entries.append(
                                    (
                                        str(folded_label),
                                        x_out + (side * float(text_90_outside_px)),
                                        y0,
                                        "inboard_center",
                                        side,
                                    )
                                )
                    else:
                        vert_dir = -1.0 if inverted_marking else 1.0
                        y_vert_end = y0 + (vert_dir * float(ladder_tick_len_px))
                        pygame.draw.line(
                            world,
                            white,
                            (int(round(x_gap_mid)), int(round(y0))),
                            (int(round(x_gap_mid)), int(round(y_vert_end))),
                            sym_line_w,
                        )
                        dash_ang_deg = min(30.0, float(folded_label))
                        dash_rad = math.radians(float(dash_ang_deg))
                        dash_dx = float(ladder_outboard_len_px) * math.cos(dash_rad) * side
                        dash_dy = float(ladder_outboard_len_px) * math.sin(dash_rad) * vert_dir
                        dash_start = (x_gap_mid, y_vert_end)
                        dash_end = (x_gap_mid + dash_dx, y_vert_end + dash_dy)
                        self._draw_dashed_line(
                            world,
                            white,
                            dash_start,
                            dash_end,
                            dash_px=dash_px,
                            gap_px=gap_px,
                            width=sym_line_w,
                        )
                        bottom_of_dash_y = max(float(dash_start[1]), float(dash_end[1]))
                        top_of_dash_y = min(float(dash_start[1]), float(dash_end[1]))
                        if (not ladder_numbers_left_only) or side < 0.0:
                            text_entries.append(
                                (
                                    str(folded_label),
                                    x_gap_mid + (side * (float(ladder_outboard_len_px) + float(text_below_outboard_shift_px))),
                                    (top_of_dash_y if inverted_marking else bottom_of_dash_y),
                                    "center",
                                    side,
                                )
                            )

        rotated_world = pygame.transform.rotozoom(world, float(world_rotation_deg), 1.0)
        rotated_world_rect = rotated_world.get_rect(center=nose_center)

        old_clip = surface.get_clip()
        surface.set_clip(adi_rect)
        surface.blit(rotated_world, rotated_world_rect)

        if draw_symbology:
            text_rotation_deg = self._upright_rotation_deg(world_rotation_deg)
            for text, tx, ty, anchor_mode, side in text_entries:
                base_text_surface = ladder_font.render(text, True, white)
                base_w, base_h = base_text_surface.get_size()
                anchor_x = float(tx)
                anchor_y = float(ty)
                if anchor_mode == "top_outboard":
                    anchor_x += (-float(side) * (float(base_w) * 0.5))
                    anchor_y += float(base_h) * 0.5
                elif anchor_mode == "bottom_outboard":
                    anchor_x += (-float(side) * (float(base_w) * 0.5))
                    anchor_y -= float(base_h) * 0.5
                elif anchor_mode == "inboard_center":
                    anchor_x += (float(side) * (float(base_w) * 0.5))
                dx = float(tx) - float(wcx)
                dy = float(ty) - float(wcy)
                if anchor_mode in {"top_outboard", "bottom_outboard", "inboard_center"}:
                    dx = float(anchor_x) - float(wcx)
                    dy = float(anchor_y) - float(wcy)
                rdx, rdy = self._rotate_screen_offset(dx, dy, world_rotation_deg)
                sx = float(nose_x) + rdx
                sy = float(nose_y) + rdy
                text_surface = base_text_surface
                if abs(text_rotation_deg) > 1e-3:
                    text_surface = pygame.transform.rotozoom(text_surface, float(text_rotation_deg), 1.0)
                text_rect = text_surface.get_rect(center=(int(round(sx)), int(round(sy))))
                surface.blit(text_surface, text_rect)

            if draw_nose_symbol:
                arc_pts: List[Tuple[int, int]] = []
                for deg in range(120, 421, 6):
                    rad = math.radians(float(deg))
                    arc_pts.append(
                        (
                            int(round(float(nose_x) + (float(nose_radius_px) * math.cos(rad)))),
                            int(round(float(nose_y) + (float(nose_radius_px) * math.sin(rad)))),
                        )
                    )
                if len(arc_pts) >= 2:
                    pygame.draw.lines(surface, white, False, arc_pts, sym_line_w)

                left_start = (int(round(nose_x - nose_radius_px)), int(round(nose_y)))
                left_end = (int(round(nose_x - nose_radius_px - nose_side_len_px)), int(round(nose_y)))
                right_start = (int(round(nose_x + nose_radius_px)), int(round(nose_y)))
                right_end = (int(round(nose_x + nose_radius_px + nose_side_len_px)), int(round(nose_y)))
                pygame.draw.line(surface, white, left_start, left_end, sym_line_w)
                pygame.draw.line(surface, white, right_start, right_end, sym_line_w)
                top_start = (int(round(nose_x)), int(round(nose_y - nose_radius_px)))
                top_end = (int(round(nose_x)), int(round(nose_y - nose_radius_px - nose_top_len_px)))
                pygame.draw.line(surface, white, top_start, top_end, sym_line_w)

            w_top_y = int(round(nose_y - nose_radius_px - nose_top_len_px - (0.04 * DPI) - float(w_vertical_offset_px)))
            w_scale = 0.75
            w_half_span = 0.16 * DPI * w_scale
            w_depth = 0.09 * DPI * w_scale
            w_pts = [
                (int(round(nose_x - w_half_span)), int(round(w_top_y))),
                (int(round(nose_x - (w_half_span * 0.5))), int(round(w_top_y + w_depth))),
                (int(round(nose_x)), int(round(w_top_y))),
                (int(round(nose_x + (w_half_span * 0.5))), int(round(w_top_y + w_depth))),
                (int(round(nose_x + w_half_span)), int(round(w_top_y))),
            ]
            pygame.draw.lines(surface, white, False, w_pts, sym_line_w)
            w_ext = 0.12 * DPI * w_scale
            pygame.draw.line(
                surface,
                white,
                (int(round(nose_x - w_half_span - w_ext)), int(round(w_top_y))),
                (int(round(nose_x - w_half_span)), int(round(w_top_y))),
                sym_line_w,
            )
            pygame.draw.line(
                surface,
                white,
                (int(round(nose_x + w_half_span)), int(round(w_top_y))),
                (int(round(nose_x + w_half_span + w_ext)), int(round(w_top_y))),
                sym_line_w,
            )

        surface.set_clip(old_clip)

    def _draw_bottom_roll_indicator(
        self,
        surface: pygame.Surface,
        adi_rect: pygame.Rect,
        bank_deg: float,
        *,
        sym_color: Tuple[int, int, int] = (255, 255, 255),
        vertical_offset_px: float = 0.0,
    ) -> None:
        white = tuple(sym_color)
        old_clip = surface.get_clip()
        surface.set_clip(old_clip.clip(adi_rect))
        center_x = int(adi_rect.centerx)
        center_y = int(round(float(adi_rect.bottom) - (0.12 * DPI) - 35.0 - float(vertical_offset_px)))

        # Stationary center reference.
        ref_w = max(4, int(round(0.10 * DPI)))
        ref_h = max(8, int(round(0.22 * DPI)))
        ref_rect = pygame.Rect(0, 0, ref_w, ref_h)
        ref_rect.center = (center_x, center_y)
        pygame.draw.rect(surface, white, ref_rect, 1)

        # Rotating roll hash marks at +/-10, +/-20, +/-30 deg.
        # Neutral horizontal spacing between -30 and +30 marks is exactly 1.35in.
        roll_span_px = 1.35 * DPI
        arc_radius = float(roll_span_px)
        arc_center_x = float(center_x)
        # Position the (implicit) circle so its bottom edge touches the
        # rectangle top edge, while keeping the original arc curvature.
        arc_center_y = float(ref_rect.top) - arc_radius
        base_arc_deg = 180.0

        hash_len_short_px = 0.12 * DPI
        hash_len_long_px = hash_len_short_px * 1.5
        for abs_deg in (10, 20, 30):
            tick_len = hash_len_long_px if abs_deg == 30 else hash_len_short_px
            for side in (-1.0, 1.0):
                ang = base_arc_deg + float(bank_deg) + (side * float(abs_deg))
                rad = math.radians(ang)
                ux = math.sin(rad)
                uy = -math.cos(rad)
                px = arc_center_x + (arc_radius * ux)
                py = arc_center_y + (arc_radius * uy)
                pygame.draw.line(
                    surface,
                    white,
                    (int(round(px)), int(round(py))),
                    (int(round(px + (ux * tick_len))), int(round(py + (uy * tick_len)))),
                    2,
                )
        surface.set_clip(old_clip)

    def _draw_adi_heading_box(self, surface: pygame.Surface, adi_rect: pygame.Rect, heading_deg: float) -> None:
        white = (255, 255, 255)
        font = get_font(14)
        heading_int = int(round(float(heading_deg))) % 360
        text_surf = font.render(f"{heading_int:03d}", True, white)
        text_rect = text_surf.get_rect()
        box_rect = text_rect.inflate(8, 4)
        box_rect.centerx = int(adi_rect.centerx)
        box_rect.bottom = int(adi_rect.bottom)
        text_rect.center = box_rect.center
        pygame.draw.rect(surface, white, box_rect, 1)
        surface.blit(text_surf, text_rect)

    @classmethod
    def _get_cyan_aircraft_icon(cls, size_px: int) -> Optional[pygame.Surface]:
        size_px = max(1, int(size_px))
        cached = cls._cyan_aircraft_cache.get(size_px)
        if size_px in cls._cyan_aircraft_cache:
            return cached
        icon_path = resource_path("icons", "STATUS BAR", "Aircraft.png")
        if not icon_path.exists():
            cls._cyan_aircraft_cache[size_px] = None
            return None
        try:
            src = pygame.image.load(str(icon_path)).convert_alpha()
            sw = max(1, src.get_width())
            sh = max(1, src.get_height())
            scale = min(size_px / float(sw), size_px / float(sh))
            nw = max(1, int(round(sw * scale)))
            nh = max(1, int(round(sh * scale)))
            scaled = pygame.transform.smoothscale(src, (nw, nh))
            canvas = pygame.Surface((size_px, size_px), pygame.SRCALPHA)
            dst = scaled.get_rect(center=(size_px // 2, size_px // 2))
            canvas.blit(scaled, dst)
            tint = pygame.Surface((size_px, size_px), pygame.SRCALPHA)
            tint.fill((0, 255, 255, 255))
            canvas.blit(tint, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
            cls._cyan_aircraft_cache[size_px] = canvas
            return canvas
        except Exception:
            cls._cyan_aircraft_cache[size_px] = None
            return None

    @classmethod
    def _get_aoa_icon(cls, width_px: int, height_px: int) -> Optional[pygame.Surface]:
        width_px = max(1, int(width_px))
        height_px = max(1, int(height_px))
        key = (width_px, height_px)
        cached = cls._aoa_icon_cache.get(key)
        if cached is not None:
            return cached
        icon_path = resource_path("icons", "EFI", "aoa.png")
        if not icon_path.exists():
            return None
        try:
            loaded = pygame.image.load(str(icon_path))
            if pygame.display.get_surface() is not None:
                src = loaded.convert_alpha()
            else:
                src = loaded
            sw = max(1, src.get_width())
            sh = max(1, src.get_height())
            scale = min(width_px / float(sw), height_px / float(sh))
            nw = max(1, int(round(sw * scale)))
            nh = max(1, int(round(sh * scale)))
            scaled = pygame.transform.smoothscale(src, (nw, nh))
            # Force every non-transparent pixel to solid white for readability.
            icon_mask = pygame.mask.from_surface(scaled, 0)
            white_scaled = pygame.Surface((nw, nh), pygame.SRCALPHA)
            icon_mask.to_surface(
                white_scaled,
                setcolor=(255, 255, 255, 255),
                unsetcolor=(0, 0, 0, 0),
            )
            scaled = white_scaled
            canvas = pygame.Surface((width_px, height_px), pygame.SRCALPHA)
            dst = scaled.get_rect(center=(width_px // 2, height_px // 2))
            canvas.blit(scaled, dst)
            cls._aoa_icon_cache[key] = canvas
            return canvas
        except Exception:
            return None

    @staticmethod
    def _polar_from_north(center: Tuple[int, int], radius_px: float, angle_deg_from_north: float) -> Tuple[int, int]:
        cx, cy = center
        theta = math.radians(float(angle_deg_from_north))
        x = int(round(cx + radius_px * math.sin(theta)))
        y = int(round(cy - radius_px * math.cos(theta)))
        return x, y

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
            if idx == 7:
                return pygame.Rect(rect.x, rect.bottom - DISPLAY_OSB_H - SIDE_OSB_Y_SHIFT, GRID_CELL_W, DISPLAY_OSB_H)
            if idx < 1 or idx > side_count:
                return None
            return pygame.Rect(rect.x, rect.y + top_offset - SIDE_OSB_Y_SHIFT + (idx - 1) * DISPLAY_OSB_H, GRID_CELL_W, DISPLAY_OSB_H)
        if side == "R":
            if idx == 7:
                return pygame.Rect(rect.right - GRID_CELL_W, rect.bottom - DISPLAY_OSB_H - SIDE_OSB_Y_SHIFT, GRID_CELL_W, DISPLAY_OSB_H)
            if idx < 1 or idx > side_count:
                return None
            return pygame.Rect(rect.right - GRID_CELL_W, rect.y + top_offset - SIDE_OSB_Y_SHIFT + (idx - 1) * DISPLAY_OSB_H, GRID_CELL_W, DISPLAY_OSB_H)
        return None

    @staticmethod
    def _data_entry_grid_rect(rect: pygame.Rect) -> pygame.Rect:
        # Match FUEL keypad geometry.
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

    def _cdi_mode(self) -> str:
        if len(self._cdi_options) <= 0:
            return "TCN"
        idx = max(0, min(len(self._cdi_options) - 1, int(self._cdi_idx)))
        self._cdi_idx = idx
        return str(self._cdi_options[idx]).upper().strip()

    def _set_data_selected(self, label: Optional[str]) -> None:
        if label in {"L6", "R6"}:
            self._data_selected = str(label)
        else:
            self._data_selected = None

    def _display_value(self, label: str) -> str:
        if label == "L6":
            return f"{int(self._hdg_value) % 360:03d}"
        return f"{int(self._loc_value) % 1000:03d}"

    def _commit_data_entry(self, label: str) -> None:
        raw = "".join(ch for ch in str(self._data_inputs.get(label, "")) if ch.isdigit())[-3:]
        if raw != "":
            try:
                value = int(raw)
            except Exception:
                value = 0
            if label == "L6":
                value = max(0, min(359, value))
                self._hdg_value = int(value)
            elif label == "R6":
                value = max(0, min(359, value))
                self._loc_value = int(value)
                self._loc_user_set = True
        self._data_inputs[label] = ""

    def _apply_data_key(self, label: str, key: str) -> None:
        current = str(self._data_inputs.get(label, ""))
        token = str(key).upper().strip()
        if token == "BACK":
            self._data_inputs[label] = current[:-1]
            return
        if token not in {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}:
            return
        next_val = (current + token)[-3:]
        self._data_inputs[label] = next_val

    def _draw_osb_multiline(
        self,
        surface: pygame.Surface,
        box: pygame.Rect,
        lines: List[Tuple[str, Tuple[int, int, int], bool]],
        *,
        h_align: str,
        v_align: str = "center",
        flashing: bool = False,
    ) -> None:
        font = get_font(14)
        rendered = [font.render(text, True, (0, 0, 0) if flashing else color) for text, color, _ul in lines]
        total_h = sum(s.get_height() for s in rendered) + max(0, len(rendered) - 1)
        if v_align == "top":
            y = box.top + OSB_PADDING
        else:
            y = box.centery - total_h // 2
        rects: List[pygame.Rect] = []
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
            rects.append(rr)
            y += surf.get_height() + 1

        if flashing and len(rects) > 0:
            flash_rect = rects[0].copy()
            for rr in rects[1:]:
                flash_rect.union_ip(rr)
            flash_rect.inflate_ip(4, 2)
            pygame.draw.rect(surface, (255, 255, 255), flash_rect)

        for surf, rr in zip(rendered, rects):
            surface.blit(surf, rr)

        if not flashing:
            for rr, (_text, color, underline) in zip(rects, lines):
                if underline:
                    pygame.draw.line(surface, color, (rr.left, rr.bottom + 1), (rr.right, rr.bottom + 1), 1)

    def _draw_osb_lines_2_3(
        self,
        surface: pygame.Surface,
        box: pygame.Rect,
        line2: str,
        line3: str,
        *,
        color: Tuple[int, int, int],
        h_align: str,
        flashing: bool = False,
    ) -> None:
        font = get_font(14)
        y3 = box.bottom - font.get_height() - 2
        y2 = y3 - font.get_height() - 1
        draw_color = (0, 0, 0) if flashing else color
        surf2 = font.render(line2, True, draw_color)
        surf3 = font.render(line3, True, draw_color)
        if h_align == "left":
            r2 = surf2.get_rect(left=box.left + OSB_PADDING, y=y2)
            r3 = surf3.get_rect(left=box.left + OSB_PADDING, y=y3)
        elif h_align == "right":
            r2 = surf2.get_rect(right=box.right - OSB_PADDING, y=y2)
            r3 = surf3.get_rect(right=box.right - OSB_PADDING, y=y3)
        else:
            r2 = surf2.get_rect(centerx=box.centerx, y=y2)
            r3 = surf3.get_rect(centerx=box.centerx, y=y3)
        if flashing:
            flash_rect = r2.union(r3).inflate(4, 2)
            pygame.draw.rect(surface, (255, 255, 255), flash_rect)
        surface.blit(surf2, r2)
        surface.blit(surf3, r3)

    def _draw_osb_labels(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        heading_deg: float,
        adi_rect: pygame.Rect,
        context: FormatContext,
    ) -> None:
        def flash(label: str) -> bool:
            try:
                return bool(context.is_osb_flashing(label))
            except Exception:
                return False

        # T5 page-access label.
        t5 = self._osb_box(rect, "T5")
        if t5 is not None:
            t5_state = ButtonState(
                button_id="EFI_T5",
                button_type=ButtonType.PAGE_ACCESS,
                text="CNTL>",
                h_align="center",
                v_align="top",
                padding=OSB_PADDING,
                font_size=14,
                flash_until_ms=1 if flash("T5") else 0,
            )
            render_button(surface, t5, t5_state, get_font, 0)

        cyan = (0, 255, 255)
        white = (255, 255, 255)
        green = (0, 255, 0)
        # T4: ILS box + frequency.
        t4 = self._osb_box(rect, "T4")
        if t4 is not None:
            font = get_font(14)
            y2 = t4.top + OSB_PADDING
            y3 = y2 + font.get_height() + 1
            ils_freq_text = self._nav_ils_frequency_text()
            ils_surf = font.render("ILS", True, (0, 0, 0) if flash("T4") else white)
            freq_surf = font.render(ils_freq_text, True, (0, 0, 0) if flash("T4") else green)
            ils_rect = ils_surf.get_rect(centerx=t4.centerx, y=y2)
            freq_rect = freq_surf.get_rect(centerx=t4.centerx, y=y3)
            if flash("T4"):
                pygame.draw.rect(surface, white, ils_rect.inflate(4, 2))
                pygame.draw.rect(surface, white, freq_rect.inflate(4, 2))
            pygame.draw.rect(surface, white, ils_rect.inflate(4, 2), 1)
            surface.blit(ils_surf, ils_rect)
            surface.blit(freq_surf, freq_rect)

        l1 = self._osb_box(rect, "L1")
        if l1 is not None:
            l1_state = ButtonState(
                button_id="EFI_L1_CDI",
                button_type=ButtonType.GOL,
                function_label="CDI",
                options=list(self._cdi_options),
                selected_index=int(self._cdi_idx),
                h_align="left",
                v_align="center",
                padding=OSB_PADDING,
                font_size=14,
                flash_until_ms=1 if flash("L1") else 0,
            )
            render_button(surface, l1, l1_state, get_font, 0)

        airspeed_kts = max(0.0, self._read_aircraft_scalar(("AIRSPEED_KTS",), 0.0))
        total_speed_kts = max(airspeed_kts, self._read_aircraft_scalar(("TOTAL_SPEED_KTS",), airspeed_kts))
        vertical_fpm = self._read_aircraft_scalar(("VERTICAL_SPEED_FPM",), 0.0)
        vertical_kts = (abs(float(vertical_fpm)) / 60.0) * 0.592483801295896
        ground_speed_kts = math.sqrt(max(0.0, (total_speed_kts * total_speed_kts) - (vertical_kts * vertical_kts)))
        true_altitude_ft = max(0.0, self._read_aircraft_scalar(("ALTITUDE_FT", "ALTITUDE_TARGET_FT"), 0.0))
        baro_altitude_ft = self._baro_display_altitude_ft(true_altitude_ft)
        l2 = self._osb_box(rect, "L2")
        l3 = self._osb_box(rect, "L3")
        r2 = self._osb_box(rect, "R2")
        r3 = self._osb_box(rect, "R3")
        if l2 is not None and l3 is not None:
            speed_center_y = int(round((float(l2.centery) + float(l3.centery)) * 0.5))
        elif l2 is not None:
            speed_center_y = int(l2.centery)
        else:
            speed_center_y = int(rect.centery)
        if r2 is not None and r3 is not None:
            altitude_center_y = int(round((float(r2.centery) + float(r3.centery)) * 0.5))
        elif r2 is not None:
            altitude_center_y = int(r2.centery)
        else:
            altitude_center_y = int(speed_center_y)

        # Keep readouts fixed relative to ADI edges across 5x/10x portal widths.
        readout_gap_from_adi = 0.5 * DPI
        speed_center_x = int(round(float(adi_rect.left) - float(readout_gap_from_adi)))
        altitude_center_x = int(round(float(adi_rect.right) + float(readout_gap_from_adi)))
        speed_center_x = max(rect.left + OSB_PADDING, speed_center_x)
        altitude_center_x = min(rect.right - OSB_PADDING, altitude_center_x)
        readout_font = get_font(16)

        def _draw_gauge_line(
            center_pt: Tuple[int, int],
            angle_deg: float,
            *,
            guide_circles: Optional[List[Tuple[float, float, float]]] = None,
            boundary_points: Optional[List[Tuple[int, int]]] = None,
            fallback_points: Optional[List[Tuple[int, int]]] = None,
        ) -> None:
            cx, cy = int(center_pt[0]), int(center_pt[1])
            rad = math.radians(float(angle_deg))
            dir_x = math.sin(rad)
            dir_y = -math.cos(rad)
            max_reach = 0.0
            if boundary_points and len(boundary_points) >= 3:
                ordered = sorted(
                    boundary_points,
                    key=lambda p: math.atan2(float(p[1] - cy), float(p[0] - cx)),
                )
                min_hit: Optional[float] = None
                for i in range(len(ordered)):
                    ax, ay = float(ordered[i][0]), float(ordered[i][1])
                    bx, by = float(ordered[(i + 1) % len(ordered)][0]), float(ordered[(i + 1) % len(ordered)][1])
                    ex = bx - ax
                    ey = by - ay
                    rx = ax - float(cx)
                    ry = ay - float(cy)
                    den = (dir_x * ey) - (dir_y * ex)
                    if abs(den) <= 1e-6:
                        continue
                    t = ((rx * ey) - (ry * ex)) / den
                    u = ((rx * dir_y) - (ry * dir_x)) / den
                    if t >= 0.0 and 0.0 <= u <= 1.0:
                        if min_hit is None or t < min_hit:
                            min_hit = t
                if min_hit is not None:
                    max_reach = float(min_hit)
            if max_reach <= 0.0 and guide_circles:
                for ccx, ccy, rr in guide_circles:
                    fx = float(cx) - float(ccx)
                    fy = float(cy) - float(ccy)
                    b = 2.0 * ((fx * dir_x) + (fy * dir_y))
                    c = (fx * fx) + (fy * fy) - (float(rr) * float(rr))
                    disc = (b * b) - (4.0 * c)
                    if disc < 0.0:
                        continue
                    root = math.sqrt(disc)
                    t1 = (-b - root) * 0.5
                    t2 = (-b + root) * 0.5
                    if t1 > max_reach:
                        max_reach = t1
                    if t2 > max_reach:
                        max_reach = t2
            if max_reach <= 0.0 and fallback_points:
                for px, py in fallback_points:
                    vx = float(px - cx)
                    vy = float(py - cy)
                    proj = (vx * dir_x) + (vy * dir_y)
                    if proj > max_reach:
                        max_reach = proj
            if max_reach <= 0.0:
                return
            # Keep the tip just short of the dot ring.
            reach = max(0.0, max_reach - 2.0)
            end_x = float(cx) + (dir_x * reach)
            end_y = float(cy) + (dir_y * reach)
            pygame.draw.line(surface, white, (cx, cy), (int(round(end_x)), int(round(end_y))), 1)

        speed_surf = readout_font.render(str(max(0, int(round(total_speed_kts)))), True, white)
        speed_rect = speed_surf.get_rect(center=(speed_center_x, speed_center_y))
        speed_min_x = rect.left + OSB_PADDING
        speed_max_x = adi_rect.left - OSB_PADDING
        if speed_rect.left < speed_min_x:
            speed_rect.left = speed_min_x
        if speed_rect.right > speed_max_x:
            speed_rect.right = speed_max_x
        speed_ref_w, speed_ref_h = readout_font.size("000")
        dot_orbit_radius = max(8.0, (max(float(speed_ref_w), float(speed_ref_h)) * 0.65) + (0.08 * DPI))
        speed_dot_points: List[Tuple[int, int]] = []
        for angle_deg in (0.0, 70.0, 110.0, 250.0, 290.0, 215.0, 325.0):
            dot_x, dot_y = self._polar_from_north(speed_rect.center, dot_orbit_radius, angle_deg)
            speed_dot_points.append((int(dot_x), int(dot_y)))

        speed_angle_deg = float(total_speed_kts) % 360.0
        _draw_gauge_line(
            speed_rect.center,
            speed_angle_deg,
            guide_circles=[(float(speed_rect.centerx), float(speed_rect.centery), float(dot_orbit_radius))],
            fallback_points=speed_dot_points,
        )
        speed_mask_rect = speed_rect.inflate(4, 2)
        pygame.draw.rect(surface, (0, 0, 0), speed_mask_rect)
        surface.blit(speed_surf, speed_rect)
        for dot_x, dot_y in speed_dot_points:
            pygame.draw.circle(surface, white, (int(dot_x), int(dot_y)), 2, 0)

        r1 = self._osb_box(rect, "R1")
        if r1 is not None:
            self._draw_osb_multiline(
                surface,
                r1,
                [("FD", cyan, True), ("OFF", cyan, False)],
                h_align="right",
                v_align="center",
                flashing=flash("R1"),
            )
        altitude_int = max(0, min(99999, int(round(baro_altitude_ft))))
        altitude_surf = readout_font.render(f"{altitude_int:>5d}", True, white)
        altitude_rect = altitude_surf.get_rect(center=(altitude_center_x, altitude_center_y))
        altitude_min_x = adi_rect.right + OSB_PADDING
        altitude_max_x = rect.right - OSB_PADDING
        if altitude_rect.left < altitude_min_x:
            altitude_rect.left = altitude_min_x
        if altitude_rect.right > altitude_max_x:
            altitude_rect.right = altitude_max_x
        alt_dot_orbit_radius = max(4.0, ((max(altitude_rect.width, altitude_rect.height) * 0.65) + (0.08 * DPI)) - 20.0)
        alt_side_center_offset = max(4.0, 0.14 * DPI)
        alt_outboard_offset = alt_side_center_offset + 4.0
        alt_inboard_offset = max(2.0, alt_side_center_offset - 4.0)
        left_alt_outboard_center = (int(round(altitude_rect.centerx - alt_outboard_offset)), int(altitude_rect.centery))
        right_alt_outboard_center = (int(round(altitude_rect.centerx + alt_outboard_offset)), int(altitude_rect.centery))
        left_alt_inboard_center = (int(round(altitude_rect.centerx - alt_inboard_offset)), int(altitude_rect.centery))
        right_alt_inboard_center = (int(round(altitude_rect.centerx + alt_inboard_offset)), int(altitude_rect.centery))
        altitude_dot_points: List[Tuple[int, int]] = []
        for angle_deg in (0.0, 180.0):
            dot_x, dot_y = self._polar_from_north(left_alt_outboard_center, alt_dot_orbit_radius, angle_deg)
            altitude_dot_points.append((int(dot_x), int(dot_y)))
        for angle_deg in (0.0, 180.0):
            dot_x, dot_y = self._polar_from_north(right_alt_outboard_center, alt_dot_orbit_radius, angle_deg)
            altitude_dot_points.append((int(dot_x), int(dot_y)))
        for angle_deg in (250.0, 290.0):
            dot_x, dot_y = self._polar_from_north(left_alt_inboard_center, alt_dot_orbit_radius, angle_deg)
            altitude_dot_points.append((int(dot_x), int(dot_y)))
        for angle_deg in (70.0, 110.0):
            dot_x, dot_y = self._polar_from_north(right_alt_inboard_center, alt_dot_orbit_radius, angle_deg)
            altitude_dot_points.append((int(dot_x), int(dot_y)))

        altitude_angle_deg = float(altitude_int) % 360.0
        _draw_gauge_line(
            altitude_rect.center,
            altitude_angle_deg,
            boundary_points=altitude_dot_points,
            fallback_points=altitude_dot_points,
        )
        altitude_mask_rect = altitude_rect.inflate(4, 2)
        pygame.draw.rect(surface, (0, 0, 0), altitude_mask_rect)
        surface.blit(altitude_surf, altitude_rect)
        for dot_x, dot_y in altitude_dot_points:
            pygame.draw.circle(surface, white, (int(dot_x), int(dot_y)), 2, 0)

        def _speed_of_sound_kts_for_altitude(alt_ft_value: float) -> float:
            alt_m = max(0.0, float(alt_ft_value)) * 0.3048
            if alt_m <= 11000.0:
                temp_k = 288.15 - (0.0065 * alt_m)
            else:
                temp_k = 216.65
            a_mps = math.sqrt(1.4 * 287.05 * max(1.0, temp_k))
            return a_mps * 1.9438444924406

        sound_kts = max(1e-6, _speed_of_sound_kts_for_altitude(true_altitude_ft))
        mach = max(0.0, float(total_speed_kts) / sound_kts)
        g_from_physics = self._read_aircraft_scalar(("G_LOAD",), float("nan"))
        if math.isfinite(float(g_from_physics)):
            current_g = max(0.0, min(9.0, float(g_from_physics)))
        else:
            # Fallback for older state snapshots.
            bank_deg = self._normalize_signed_angle_deg(self._read_global_bank_deg())
            cos_bank = abs(math.cos(math.radians(float(bank_deg))))
            current_g = 1.0 / max(0.2, cos_bank)
            current_g = max(0.0, min(9.0, current_g))
        pitch_deg = self._normalize_signed_angle_deg(self._read_global_attitude_deg())
        kts_per_fps = 0.592483801295896
        speed_fps = max(0.1, float(total_speed_kts) / kts_per_fps)
        vertical_fps = float(vertical_fpm) / 60.0
        flight_path_deg = math.degrees(math.asin(max(-1.0, min(1.0, vertical_fps / speed_fps))))
        aoa_deg = abs(float(pitch_deg) - float(flight_path_deg))
        aoa_deg = max(0.0, min(99.9, aoa_deg))

        detail_start_y = int(round(float(speed_rect.centery) + 50.0))
        detail_font = get_font(14)
        g_line_text = f"G   {current_g:.1f}"
        speed_detail_lines = [
            f"GS  {max(0, int(round(ground_speed_kts)))}",
            f"M  {mach:.2f}",
            g_line_text,
            f"?   {aoa_deg:.1f}",
            "1.0",
        ]
        speed_detail_lines = speed_detail_lines[:3]
        y_cursor = detail_start_y
        for line in speed_detail_lines:
            line_surf = detail_font.render(line, True, white)
            line_rect = line_surf.get_rect(centerx=speed_center_x, y=y_cursor)
            surface.blit(line_surf, line_rect)
            y_cursor += line_surf.get_height() + 1

        aoa_value_surf = detail_font.render(f"{aoa_deg:.1f}", True, white)
        sym_w = max(10, int(round(0.24 * DPI)))
        sym_h = max(8, int(round(0.11 * DPI)))
        aoa_sym = self._get_aoa_icon(sym_w, sym_h)
        if aoa_sym is None:
            # Fallback if the icon is missing/unreadable.
            aoa_sym = pygame.Surface((sym_w, sym_h), pygame.SRCALPHA)
            left_loop = pygame.Rect(0, 0, max(4, sym_w // 2), sym_h)
            right_loop = pygame.Rect(max(1, (sym_w // 2) - 1), 0, max(4, sym_w // 2), sym_h)
            pygame.draw.ellipse(aoa_sym, white, left_loop, 1)
            pygame.draw.arc(
                aoa_sym,
                white,
                right_loop,
                math.radians(30.0),
                math.radians(330.0),
                1,
            )
        line_gap_px = 3
        g_line_width = detail_font.size(g_line_text)[0]
        g_prefix_width = detail_font.size("G   ")[0]
        g_char_width = detail_font.size("G")[0]
        g_line_left = int(round(float(speed_center_x) - (float(g_line_width) * 0.5)))
        aoa_text_x = g_line_left + g_prefix_width
        aoa_line_h = max(aoa_sym.get_height(), aoa_value_surf.get_height())
        aoa_line_top = y_cursor
        aoa_sym_y = aoa_line_top + ((aoa_line_h - aoa_sym.get_height()) // 2)
        aoa_txt_y = aoa_line_top + ((aoa_line_h - aoa_value_surf.get_height()) // 2)
        g_char_center_x = g_line_left + (g_char_width // 2)
        aoa_sym_x = g_char_center_x - (aoa_sym.get_width() // 2)
        surface.blit(aoa_sym, (aoa_sym_x, aoa_sym_y))
        surface.blit(aoa_value_surf, (aoa_text_x, aoa_txt_y))
        y_cursor += aoa_line_h + 1

        line_surf = detail_font.render("1.0", True, white)
        line_rect = line_surf.get_rect(centerx=speed_center_x, y=y_cursor)
        surface.blit(line_surf, line_rect)
        y_cursor += line_surf.get_height() + 1

        radar_alt_ft = self._radar_altitude_ft(true_altitude_ft)
        radar_alt_int = max(0, min(99999, int(round(radar_alt_ft))))
        alt_detail_surf = detail_font.render(f"R  {radar_alt_int}", True, white)
        alt_detail_rect = alt_detail_surf.get_rect(centerx=altitude_center_x, y=detail_start_y)
        surface.blit(alt_detail_surf, alt_detail_rect)

        l5 = self._osb_box(rect, "L5")
        if l5 is not None:
            self._draw_osb_multiline(
                surface,
                l5,
                [("STPT CL", white, False), ("* 360", white, False), ("0.3", green, False)],
                h_align="left",
                v_align="center",
                flashing=flash("L5"),
            )

        l7 = self._osb_box(rect, "L6")
        if l7 is not None:
            self._draw_osb_lines_2_3(
                surface,
                l7,
                "HDG",
                self._display_value("L6"),
                color=cyan,
                h_align="left",
                flashing=flash("L6"),
            )
            if self._data_selected == "L6":
                font = get_font(14)
                raw = str(self._data_inputs.get("L6", ""))
                scratch = raw[-3:].rjust(3, "_")
                top_text = f"{scratch}\u2190"
                surf = font.render(top_text, True, (255, 255, 255))
                r = surf.get_rect()
                r.left = l7.left + OSB_PADDING
                r.y = l7.top + OSB_PADDING
                pygame.draw.rect(surface, (255, 255, 255), r.inflate(4, 2), 1)
                surface.blit(surf, r)

        r5 = self._osb_box(rect, "R5")
        if r5 is not None:
            self._draw_osb_multiline(
                surface,
                r5,
                [("TCN CL", cyan, False), ("207", cyan, False), ("0.1", green, False)],
                h_align="right",
                v_align="center",
                flashing=flash("R5"),
            )

        r7 = self._osb_box(rect, "R6")
        if r7 is not None:
            self._draw_osb_lines_2_3(
                surface,
                r7,
                "LOC",
                self._display_value("R6"),
                color=cyan,
                h_align="right",
                flashing=flash("R6"),
            )
            if self._data_selected == "R6":
                font = get_font(14)
                raw = str(self._data_inputs.get("R6", ""))
                scratch = raw[-3:].rjust(3, "_")
                top_text = f"{scratch}\u2190"
                surf = font.render(top_text, True, (255, 255, 255))
                r = surf.get_rect()
                r.right = r7.right - OSB_PADDING
                r.y = r7.top + OSB_PADDING
                pygame.draw.rect(surface, (255, 255, 255), r.inflate(4, 2), 1)
                surface.blit(surf, r)

    def render(self, surface, rect, is_primary: bool, context: FormatContext) -> None:
        prev_clip = surface.get_clip()
        surface.set_clip(rect)
        surface.fill((0, 0, 0), rect)
        border_cyan = (0, 255, 255)

        if not is_primary:
            # Subportal EFI: render the ADI (orange/blue section + pitch ladder/symbology)
            # with an expanded background mask; symbology remains proportionally scaled.
            heading_deg = self._read_heading_deg()
            src_w = max(1, int(round(3.0 * DPI)))
            src_h = max(1, int(round(3.5 * DPI)))
            adi_local = pygame.Rect(0, 0, src_w, src_h)
            target_w = max(1, rect.width - 2)
            target_h = max(1, rect.height - 2)
            sym_scale = min(float(target_w) / float(src_w), float(target_h) / float(src_h))
            sym_w = max(1, int(round(float(src_w) * sym_scale)))
            sym_h = max(1, int(round(float(src_h) * sym_scale)))
            sym_dst = pygame.Rect(0, 0, sym_w, sym_h)
            sym_dst.center = rect.center

            # Layer 1: background mask expanded to fit subportal area (no bitmap stretch).
            bg_dst = pygame.Rect(0, 0, target_w, target_h)
            bg_dst.center = rect.center
            src_nose_y = max(2.0, min(float(src_h - 3), float(4.0 * DPI / 3.0)))
            nose_y_bg = float(sym_dst.top) + (src_nose_y * float(sym_scale))
            px_per_deg_bg = float(0.1 * DPI) * float(sym_scale)
            self._draw_adi(
                surface,
                bg_dst,
                draw_background=True,
                draw_symbology=False,
                draw_nose_symbol=False,
                nose_y_override=nose_y_bg,
                px_per_deg_override=px_per_deg_bg,
            )

            # Layer 2: symbology keeps aspect ratio (no stretch).
            sym_surface = pygame.Surface((src_w, src_h), pygame.SRCALPHA)
            sym_surface.fill((0, 0, 0, 0))
            self._draw_adi(
                sym_surface,
                adi_local,
                draw_background=False,
                draw_symbology=True,
                line_width=2,
            )
            self._draw_adi_heading_box(sym_surface, adi_local, heading_deg)
            sym_scaled = pygame.transform.smoothscale(sym_surface, (sym_w, sym_h))
            # Symbology mask matches the full subportal content area.
            sym_mask = pygame.Surface((target_w, target_h), pygame.SRCALPHA)
            sym_mask.fill((0, 0, 0, 0))
            sym_in_mask = sym_scaled.get_rect(center=(target_w // 2, target_h // 2))
            sym_mask.blit(sym_scaled, sym_in_mask)
            surface.blit(sym_mask, bg_dst.topleft)
            pygame.draw.rect(surface, border_cyan, rect, 1)
            surface.set_clip(prev_clip)
            return

        heading_deg = self._read_heading_deg()
        cx = rect.centerx
        virtual_bottom = rect.top + int(round(7.0 * DPI))
        hsi_height = int(round(2.75 * DPI))
        divider_y = virtual_bottom - hsi_height

        # ADI: bank-rotated sky/ground + pitch ladder around a fixed nose vector.
        adi_w = int(round(3.0 * DPI))
        adi_h = int(round(3.5 * DPI))
        adi_rect = pygame.Rect(0, 0, adi_w, adi_h)
        adi_rect.centerx = cx
        adi_rect.bottom = divider_y
        self._draw_adi(surface, adi_rect)
        self._draw_adi_heading_box(surface, adi_rect, heading_deg)
        # Divider line between ADI and HSI sections.
        pygame.draw.line(surface, (255, 255, 255), (rect.left, divider_y), (rect.right - 1, divider_y), 1)

        # HSI: smaller circle with fixed top gap from divider.
        hsi_radius = 0.95 * DPI
        hsi_top_gap = 0.25 * DPI
        hsi_center = (cx, int(round(divider_y + hsi_top_gap + hsi_radius)))
        short_len = 0.07 * DPI
        long_len = short_len * 2.0
        cyan = (0, 255, 255)
        for world_deg in range(0, 360, 5):
            display_deg = (float(world_deg) - heading_deg) % 360.0
            mark_len = long_len if (world_deg % 10 == 0) else short_len
            p0 = self._polar_from_north(hsi_center, hsi_radius, display_deg)
            p1 = self._polar_from_north(hsi_center, hsi_radius - mark_len, display_deg)
            pygame.draw.line(surface, cyan, p0, p1, 1)
        # Stationary outer hash marks (left/right cyan, top white).
        outer_hash_inner_r = hsi_radius + 2.0
        outer_hash_outer_r = outer_hash_inner_r + long_len
        for fixed_deg in (90.0, 270.0):
            p0 = self._polar_from_north(hsi_center, outer_hash_inner_r, fixed_deg)
            p1 = self._polar_from_north(hsi_center, outer_hash_outer_r, fixed_deg)
            pygame.draw.line(surface, cyan, p0, p1, 1)
        p0_top = self._polar_from_north(hsi_center, outer_hash_inner_r, 0.0)
        p1_top = self._polar_from_north(hsi_center, outer_hash_outer_r, 0.0)
        pygame.draw.line(surface, (255, 255, 255), p0_top, p1_top, 1)

        white = (255, 255, 255)
        label_font = get_font(13)
        label_radius = hsi_radius - long_len - (0.12 * DPI)
        for world_deg in range(0, 360, 30):
            if world_deg == 0:
                text = "N"
            elif world_deg == 90:
                text = "E"
            elif world_deg == 180:
                text = "S"
            elif world_deg == 270:
                text = "W"
            else:
                text = f"{(world_deg // 10):02d}"
            display_deg = (float(world_deg) - heading_deg) % 360.0
            tx, ty = self._polar_from_north(hsi_center, label_radius, display_deg)
            ts = label_font.render(text, True, white)
            tr = ts.get_rect(center=(tx, ty))
            surface.blit(ts, tr)

        cdi_mode = self._cdi_mode()
        cdi_needle_color = cyan
        cdi_dot_color = cyan
        if cdi_mode == "LRP":
            cdi_needle_color = white
            cdi_dot_color = cyan
        elif cdi_mode == "STPT":
            cdi_needle_color = (0, 255, 0)
            cdi_dot_color = cyan
        elif cdi_mode == "TCN":
            cdi_needle_color = cyan
            cdi_dot_color = cyan
        elif cdi_mode == "LOC":
            cdi_needle_color = (255, 0, 255)
            cdi_dot_color = (255, 0, 255)

        # Course line steering source is selected by CDI mode.
        tacan_solution = self._find_nav_tacan_solution()
        if isinstance(tacan_solution, dict) and (not bool(self._loc_user_set)):
            try:
                _ch = int(tacan_solution.get("channel", -1))
            except Exception:
                _ch = -1
            _band = str(tacan_solution.get("band", "")).upper().strip()
            _ident = str(tacan_solution.get("ident", "")).upper().strip()
            autoset_key = (_ch, _band, _ident)
            if autoset_key != self._tacan_autoset_key:
                try:
                    autoset_course = float(
                        tacan_solution.get(
                            "runway_course_deg",
                            tacan_solution.get("bearing_deg", self._loc_value),
                        )
                    )
                    self._loc_value = int(round(float(autoset_course))) % 360
                except Exception:
                    self._loc_value = int(self._loc_value) % 360
                self._tacan_autoset_key = autoset_key
        ils_solution = self._find_nav_ils_solution()
        if cdi_mode == "TCN":
            if isinstance(tacan_solution, dict):
                loc_heading = float(tacan_solution.get("bearing_deg", float(int(self._loc_value) % 360.0))) % 360.0
            else:
                loc_heading = float(int(self._loc_value) % 360)
        elif cdi_mode == "LOC":
            if isinstance(ils_solution, dict):
                course_val = ils_solution.get("course_deg")
                if course_val is None:
                    course_val = ils_solution.get("apch_bear_deg")
                loc_heading = float(course_val if course_val is not None else int(self._loc_value) % 360.0) % 360.0
            else:
                loc_heading = float(int(self._loc_value) % 360)
        else:
            loc_heading = float(int(self._loc_value) % 360)
        loc_display_deg = (loc_heading - heading_deg) % 360.0
        theta = math.radians(loc_display_deg)
        dir_x = math.sin(theta)
        dir_y = -math.cos(theta)
        perp_x = math.cos(theta)
        perp_y = math.sin(theta)
        line_end_r = max(0.0, label_radius - (0.05 * DPI) - 4.0)  # shorten 4px at both line ends
        half_mid = 0.375 * DPI  # middle segment is 0.75in total
        p_front = (int(round(hsi_center[0] + dir_x * line_end_r)), int(round(hsi_center[1] + dir_y * line_end_r)))
        p_rear = (int(round(hsi_center[0] - dir_x * line_end_r)), int(round(hsi_center[1] - dir_y * line_end_r)))
        p_mid_front = (int(round(hsi_center[0] + dir_x * half_mid)), int(round(hsi_center[1] + dir_y * half_mid)))
        p_mid_rear = (int(round(hsi_center[0] - dir_x * half_mid)), int(round(hsi_center[1] - dir_y * half_mid)))
        pygame.draw.line(surface, cdi_needle_color, p_front, p_mid_front, 1)
        pygame.draw.line(surface, cdi_needle_color, p_rear, p_mid_rear, 1)

        cdi_max_offset = 0.30 * DPI
        if cdi_mode == "TCN" and isinstance(tacan_solution, dict):
            # TACAN CDI: lateral deflection from runway lineup course (fallback: R6 LOC) to station bearing.
            selected_course = float(
                tacan_solution.get(
                    "runway_course_deg",
                    float(int(self._loc_value) % 360),
                )
            ) % 360.0
            bearing_to_station = float(tacan_solution.get("bearing_deg", loc_heading)) % 360.0
            try:
                station_range_nm = max(0.0, float(tacan_solution.get("distance_nm", 0.0)))
            except Exception:
                station_range_nm = 0.0
            course_err_deg = ((bearing_to_station - selected_course + 180.0) % 360.0) - 180.0
            xtrack_nm = math.sin(math.radians(course_err_deg)) * station_range_nm
            # Full-scale deflection (track bar pegged) at +/-5 NM cross-track.
            cdi_full_scale_nm = 5.0
            cdi_norm = max(-1.0, min(1.0, float(xtrack_nm) / cdi_full_scale_nm))
            cdi_offset = cdi_norm * cdi_max_offset
        elif cdi_mode == "LOC" and isinstance(ils_solution, dict):
            selected_course = ils_solution.get("course_deg")
            if selected_course is None:
                selected_course = ils_solution.get("apch_bear_deg")
            selected_course_deg = float(selected_course if selected_course is not None else int(self._loc_value) % 360.0) % 360.0
            bearing_to_loc = float(ils_solution.get("bearing_deg", selected_course_deg)) % 360.0
            try:
                loc_range_nm = max(0.0, float(ils_solution.get("distance_nm", 0.0)))
            except Exception:
                loc_range_nm = 0.0
            loc_err_deg = ((bearing_to_loc - selected_course_deg + 180.0) % 360.0) - 180.0
            xtrack_nm = math.sin(math.radians(loc_err_deg)) * loc_range_nm
            cdi_full_scale_nm = 1.5
            cdi_norm = max(-1.0, min(1.0, float(xtrack_nm) / cdi_full_scale_nm))
            cdi_offset = cdi_norm * cdi_max_offset
        else:
            # LRP/STPT fallback: steer relative to selected course (LOC value).
            cdi_delta = ((loc_heading - heading_deg + 180.0) % 360.0) - 180.0
            cdi_offset = max(-cdi_max_offset, min(cdi_max_offset, (cdi_delta / 45.0) * cdi_max_offset))
        mid_cx = hsi_center[0] + (perp_x * cdi_offset)
        mid_cy = hsi_center[1] + (perp_y * cdi_offset)
        mid_a = (int(round(mid_cx - dir_x * half_mid)), int(round(mid_cy - dir_y * half_mid)))
        mid_b = (int(round(mid_cx + dir_x * half_mid)), int(round(mid_cy + dir_y * half_mid)))
        pygame.draw.line(surface, cdi_needle_color, mid_a, mid_b, 2)

        # TACAN-rotating side dots inside the HSI: two per side, evenly spaced
        # between the aircraft icon and white heading labels.
        icon_outer_r = 0.24 * DPI
        label_inner_r = max(icon_outer_r + 0.02 * DPI, label_radius - 0.05 * DPI)
        span_r = max(0.0, label_inner_r - icon_outer_r)
        dot_radii = [
            icon_outer_r + (0.18 * span_r),  # inner dot moved inward
            icon_outer_r + ((2.0 * span_r) / 3.0),
        ]
        for side_sign in (-1.0, 1.0):  # left, right
            for dot_r in dot_radii:
                dot_pt = (
                    int(round(hsi_center[0] + (perp_x * dot_r * side_sign))),
                    int(round(hsi_center[1] + (perp_y * dot_r * side_sign))),
                )
                pygame.draw.circle(surface, cdi_dot_color, dot_pt, 3, 0)

        # Front-end TACAN arrow on the inboard course line.
        tac_base_cx = p_front[0] - (dir_x * (0.10 * DPI))
        tac_base_cy = p_front[1] - (dir_y * (0.10 * DPI))
        tac_half_w = 0.05 * DPI
        tac_left = (int(round(tac_base_cx + perp_x * tac_half_w)), int(round(tac_base_cy + perp_y * tac_half_w)))
        tac_right = (int(round(tac_base_cx - perp_x * tac_half_w)), int(round(tac_base_cy - perp_y * tac_half_w)))
        pygame.draw.polygon(surface, cdi_needle_color, [p_front, tac_left, tac_right], 0)

        # "TO" moves with the arrow position but stays upright.
        to_font = get_font(12)
        to_surf = to_font.render("TO", True, cdi_needle_color)
        to_cx = tac_base_cx - (perp_x * (0.20 * DPI))
        to_cy = tac_base_cy - (perp_y * (0.20 * DPI))
        to_rect = to_surf.get_rect(center=(int(round(to_cx)), int(round(to_cy))))
        surface.blit(to_surf, to_rect)

        # HDG SELECT notch from L6 value: thick dual yellow marks with 2px center gap.
        yellow = (255, 255, 0)
        hdg_sel = float(int(self._hdg_value) % 360)
        hdg_sel_display = (hdg_sel - heading_deg) % 360.0
        # Keep the same radial band center as before, but shorten to 2/3 height.
        notch_old_len = 0.14 * DPI
        notch_len = notch_old_len * (2.0 / 3.0)
        notch_mid_r = hsi_radius + (0.09 * DPI)
        notch_inner_r = notch_mid_r - (notch_len / 2.0)
        notch_outer_r = notch_mid_r + (notch_len / 2.0)
        notch_thickness = 5.0
        notch_gap_px = 2.0
        # Build each notch as a small wedge (polygon) so ends follow the circle curvature.
        angle_per_px = 1.0 / max(1.0, float(notch_mid_r))
        notch_half_width_ang = (notch_thickness * 0.5) * angle_per_px
        notch_center_sep_ang = ((notch_thickness + notch_gap_px) * 0.5) * angle_per_px
        center_ang = math.radians(hdg_sel_display)
        for sign in (-1.0, 1.0):
            mark_center_ang = center_ang + (sign * notch_center_sep_ang)
            ang_l = mark_center_ang - notch_half_width_ang
            ang_r = mark_center_ang + notch_half_width_ang
            p0 = (int(round(hsi_center[0] + notch_inner_r * math.sin(ang_l))), int(round(hsi_center[1] - notch_inner_r * math.cos(ang_l))))
            p1 = (int(round(hsi_center[0] + notch_outer_r * math.sin(ang_l))), int(round(hsi_center[1] - notch_outer_r * math.cos(ang_l))))
            p2 = (int(round(hsi_center[0] + notch_outer_r * math.sin(ang_r))), int(round(hsi_center[1] - notch_outer_r * math.cos(ang_r))))
            p3 = (int(round(hsi_center[0] + notch_inner_r * math.sin(ang_r))), int(round(hsi_center[1] - notch_inner_r * math.cos(ang_r))))
            pygame.draw.polygon(surface, yellow, [p0, p1, p2, p3], 0)

        # Outward TACAN pointers align with the current TACAN bearing and reciprocal.
        def _draw_tacan_pointer(world_angle: float) -> None:
            arrow_display_deg = (world_angle - heading_deg) % 360.0
            arrow_theta = math.radians(arrow_display_deg)
            a_dir_x = math.sin(arrow_theta)
            a_dir_y = -math.cos(arrow_theta)
            a_perp_x = math.cos(arrow_theta)
            a_perp_y = math.sin(arrow_theta)
            # Slightly shorter pointer.
            tip_r = hsi_radius + (0.12 * DPI)
            base_r = hsi_radius + (0.06 * DPI)
            half_w = 0.05 * DPI
            tip = (
                int(round(hsi_center[0] + a_dir_x * tip_r)),
                int(round(hsi_center[1] + a_dir_y * tip_r)),
            )
            base_cx = hsi_center[0] + a_dir_x * base_r
            base_cy = hsi_center[1] + a_dir_y * base_r
            left = (int(round(base_cx + a_perp_x * half_w)), int(round(base_cy + a_perp_y * half_w)))
            right = (int(round(base_cx - a_perp_x * half_w)), int(round(base_cy - a_perp_y * half_w)))
            pygame.draw.polygon(surface, cdi_needle_color, [tip, left, right], 0)

        _draw_tacan_pointer(float(loc_heading))
        _draw_tacan_pointer((float(loc_heading) + 180.0) % 360.0)

        # Green top arrow outline above the HSI hash marks (arrowhead + shaft/base).
        green = (0, 255, 0)
        arrow_tip_y = int(round(hsi_center[1] - (hsi_radius + 0.18 * DPI)))
        arrow_base_y = int(round(hsi_center[1] - (hsi_radius + 0.02 * DPI)))
        arrow_head_h = int(round(0.09 * DPI))
        arrow_shoulder_y = arrow_tip_y + arrow_head_h
        arrow_head_half_w = int(round(0.09 * DPI))
        arrow_shaft_half_w = int(round(0.035 * DPI))
        arrow_pts = [
            (hsi_center[0], arrow_tip_y),
            (hsi_center[0] + arrow_head_half_w, arrow_shoulder_y),
            (hsi_center[0] + arrow_shaft_half_w, arrow_shoulder_y),
            (hsi_center[0] + arrow_shaft_half_w, arrow_base_y),
            (hsi_center[0] - arrow_shaft_half_w, arrow_base_y),
            (hsi_center[0] - arrow_shaft_half_w, arrow_shoulder_y),
            (hsi_center[0] - arrow_head_half_w, arrow_shoulder_y),
        ]
        pygame.draw.polygon(surface, green, arrow_pts, 1)

        # Side text around HSI.
        def _draw_block(
            x_center: int,
            y_center: int,
            lines: List[str],
            color: Tuple[int, int, int],
            *,
            size: int = 13,
        ) -> None:
            fnt = get_font(size)
            rendered = [fnt.render(str(line), True, color) for line in lines]
            total_h = sum(s.get_height() for s in rendered) + max(0, len(rendered) - 1)
            y = int(round(y_center - (total_h / 2.0)))
            for surf_line in rendered:
                rr = surf_line.get_rect(centerx=int(x_center), y=y)
                surface.blit(surf_line, rr)
                y += surf_line.get_height() + 1

        r5_box = self._osb_box(rect, "R5")
        right_bound = int(r5_box.left - 4) if r5_box is not None else int(rect.right - GRID_CELL_W - 4)
        left_bound = int(round(hsi_center[0] + hsi_radius + 4))
        right_text_x = min(right_bound - 2, max(left_bound + 4, (left_bound + right_bound) // 2) + 20)
        # Place cyan/green block near the top and purple frequency near the bottom,
        # with increased vertical separation.
        right_text_y = int(round(hsi_center[1] - (0.26 * DPI) - 30))
        purple_y = int(round(hsi_center[1] + (0.34 * DPI) + 30))
        left_text_x = int(round((2 * hsi_center[0]) - right_text_x))
        sel_channel, sel_band, _sel_mode = self._nav_tacan_selector()
        ils_solution = self._find_nav_ils_solution()
        tacan_line = f"TCN {int(sel_channel):03d}{sel_band}"
        tacan_ident = "----"
        tacan_range = "8.9"
        if isinstance(tacan_solution, dict):
            ident_text = str(tacan_solution.get("ident", "")).strip().upper()
            if ident_text != "":
                tacan_ident = ident_text[:5]
            try:
                tacan_range = f"{float(tacan_solution.get('distance_nm', 0.0)):.1f}"
            except Exception:
                tacan_range = "8.9"
        ils_text = self._nav_ils_frequency_text()
        _draw_block(right_text_x, right_text_y, [tacan_range, tacan_line, tacan_ident], cyan, size=13)
        _draw_block(right_text_x, purple_y, [ils_text], (255, 0, 255), size=13)
        _draw_block(left_text_x, right_text_y, ["10.3", "STPT 0"], (0, 255, 0), size=13)

        icon_size = int(round(0.4 * DPI))
        aircraft_icon = self._get_cyan_aircraft_icon(icon_size)
        if aircraft_icon is not None:
            air_rect = aircraft_icon.get_rect(center=hsi_center)
            surface.blit(aircraft_icon, air_rect)

        bank_deg = self._normalize_signed_angle_deg(self._read_global_bank_deg())
        self._draw_bottom_roll_indicator(surface, adi_rect, -bank_deg)
        self._draw_osb_labels(surface, rect, heading_deg, adi_rect, context)
        self._draw_data_entry_popup(surface, rect)
        pygame.draw.rect(surface, border_cyan, rect, 1)
        surface.set_clip(prev_clip)

    def _draw_data_entry_popup(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        if self._cdi_menu_open:
            self._draw_cdi_gol_popup(surface, rect)
        if self._data_selected not in {"L6", "R6"}:
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
                    button_id=f"EFI_KEYPAD_{cell_name}",
                    button_type=ButtonType.MOMENTARY_SINGLE,
                    text=text,
                    flash_until_ms=1 if self._local_flash_active(f"KEYPAD_{cell_name}", now_ms) else 0,
                ),
                get_font,
                now_ms,
            )

    def _draw_cdi_gol_popup(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
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
        option_cells = self._gol_popup_option_cells(rect, len(self._cdi_options))
        font = get_font(15)
        selected_idx = max(0, min(len(self._cdi_options) - 1, int(self._cdi_idx)))
        for idx, text in enumerate(self._cdi_options):
            if idx >= len(option_cells):
                break
            box = self._popup_cell_rect(rect, option_cells[idx])
            if box is None:
                continue
            is_selected = idx == selected_idx
            surf = font.render(str(text), True, white if is_selected else cyan)
            rr = surf.get_rect(center=box.center)
            if is_selected:
                pygame.draw.rect(surface, white, rr.inflate(6, 3), 1)
            surface.blit(surf, rr)

    def on_click(self, pos: Tuple[int, int], rect: pygame.Rect, context: FormatContext) -> bool:
        if self._cdi_menu_open:
            popup = self._gol_popup_rect(rect)
            if not popup.collidepoint(pos):
                self._cdi_menu_open = False
                return False
            cell = self._popup_cell_at_pos(pos, rect)
            if cell is None:
                return True
            option_cells = self._gol_popup_option_cells(rect, len(self._cdi_options))
            if cell in option_cells:
                idx = int(option_cells.index(cell))
                self._cdi_idx = max(0, min(len(self._cdi_options) - 1, idx))
                self._cdi_menu_open = False
            return True
        selected = self._data_selected
        if selected not in {"L6", "R6"}:
            return False
        grid_rect = self._data_entry_grid_rect(rect)
        cols = 5
        rows = 8
        cell_w = max(1, GRID_CELL_W)
        cell_h = max(1, GRID_CELL_H)
        rel_x = pos[0] - grid_rect.x
        rel_y = pos[1] - grid_rect.y
        if rel_x < 0 or rel_y < 0 or rel_x >= grid_rect.width or rel_y >= grid_rect.height:
            return False
        col = max(0, min(cols - 1, rel_x // cell_w))
        row = max(0, min(rows - 1, rel_y // cell_h))
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
        if selected not in {"L6", "R6"}:
            return False
        raw = str(key).strip()
        if raw == "":
            return False
        upper = raw.upper()
        if upper in {"ENTER", "RETURN", "KP_ENTER"}:
            self._commit_data_entry(selected)
            self._set_data_selected(None)
            return True
        if upper in {"KP_BACK", "BACKSPACE", "BACK"}:
            self._apply_data_key(selected, "BACK")
            return True
        if upper.startswith("KP_") and len(upper) == 4 and upper[3].isdigit():
            self._apply_data_key(selected, upper[3])
            return True
        if len(raw) == 1 and raw.isdigit():
            self._apply_data_key(selected, raw)
            return True
        if raw == ".":
            self._apply_data_key(selected, ".")
            return True
        return False

    def on_osb(self, label: str, context: FormatContext) -> bool:
        if label == "L1":
            self._cdi_menu_open = not bool(self._cdi_menu_open)
            return True
        if label in {"L6", "R6"}:
            self._cdi_menu_open = False
            if self._data_selected == label:
                self._commit_data_entry(label)
                self._set_data_selected(None)
            else:
                if self._data_selected in {"L6", "R6"}:
                    self._commit_data_entry(str(self._data_selected))
                self._data_inputs[label] = ""
                self._set_data_selected(label)
            return True
        if label in {"T4", "T5", "R1", "L5", "R5"}:
            self._cdi_menu_open = False
            return True
        return False

    def osb_is_interactive(self, label: str) -> bool:
        return label in {"T1", "T4", "T5", "L1", "R1", "L5", "L6", "R5", "R6"}
