from formats import *  # noqa: F401,F403


class Tsd1Format(FormatBase):
    name: str = "TSD1"
    _cyan_icon_cache: Dict[Tuple[int, int], pygame.Surface] = {}
    _vsd_bg_raw_cache: Dict[str, Optional[pygame.Surface]] = {}
    _vsd_bg_circle_cache: Dict[Tuple[str, int], Optional[pygame.Surface]] = {}
    _adsb_icon_base_cache: Dict[str, Optional[pygame.Surface]] = {}
    _adsb_icon_rot_cache: Dict[Tuple[object, ...], pygame.Surface] = {}
    _track_symbol_base_cache: Dict[Tuple[object, ...], Optional[pygame.Surface]] = {}
    _tacan_icon_cache: Dict[Tuple[str, int], Optional[pygame.Surface]] = {}
    _tsd_svg_cache: Dict[Tuple[str, int], Optional[pygame.Surface]] = {}
    _map_index_cache: Optional[List[Dict[str, object]]] = None
    _map_image_cache: Dict[str, object] = {}
    _map_patch_cache: Dict[Tuple[str, int, int, int, int], pygame.Surface] = {}
    _navaid_cache_mtime: Optional[float] = None
    _navaid_cache: List[Dict[str, object]] = []
    _airport_cache_mtime: Optional[float] = None
    _airport_cache_by_ident: Dict[str, Dict[str, object]] = {}
    _airport_frequency_cache_mtime: Optional[float] = None
    _airport_frequency_military_idents: Set[str] = set()
    _runway_cache_mtime: Optional[float] = None
    _runway_cache: List[Dict[str, object]] = []
    _runway_spatial_index: Dict[Tuple[int, int], List[Dict[str, object]]] = {}
    _runway_cache_loading: bool = False
    _runway_cache_target_mtime: Optional[float] = None
    _runway_cache_lock = threading.Lock()
    _runway_cache_file_version: int = 2
    _faa_ils_cache_key: Optional[Tuple[float, int, float, int]] = None
    _faa_ils_by_airport: Dict[str, List[Dict[str, object]]] = {}
    _faa_ils_entries: List[Dict[str, object]] = []
    _road_overlay_lock = threading.Lock()
    _road_overlay_segments: List[Tuple[float, float, float, float]] = []
    _road_overlay_center: Optional[Tuple[float, float]] = None
    _road_overlay_radius_m: float = 0.0
    _road_overlay_last_fetch_s: float = 0.0
    _road_overlay_fetch_inflight: bool = False
    _road_overlay_last_error_s: float = 0.0
    # Match main OSB flash cadence so VSD L3 feels the same as other OSBs.
    _VSD_L3_FLASH_DELAY_MS: int = 250

    @staticmethod
    def _normalize_tsd_name(name: str) -> str:
        upper = str(name).upper()
        digits = "".join(ch for ch in upper if ch.isdigit())
        if digits in {"1", "2", "3"}:
            return f"TSD{digits}"
        return "TSD1"

    def _bind_state(self) -> Dict[str, object]:
        global TSD1_STATE
        key = self._normalize_tsd_name(getattr(self, "name", "TSD1"))
        state = TSD_STATES_BY_NAME.get(key)
        if not isinstance(state, dict):
            state = _new_tsd_state()
            TSD_STATES_BY_NAME[key] = state
        TSD1_STATE = state
        return state

    def _subportal_label(self) -> str:
        key = self._normalize_tsd_name(getattr(self, "name", "TSD1"))
        return key

    def _service_vsd_pending_actions(self) -> None:
        state = self._state()
        try:
            due_ms = int(state.get("vsd_l3_pending_toggle_due_ms", 0) or 0)
        except Exception:
            due_ms = 0
        if due_ms <= 0:
            return
        now_ms = int(pygame.time.get_ticks())
        if now_ms < due_ms:
            return
        state["vsd_side_view"] = not bool(state.get("vsd_side_view", False))
        state["vsd_l3_pending_toggle_due_ms"] = 0

    def _debug_print(
        self,
        channel: str,
        message: str,
        min_interval_ms: int = 1000,
        force: bool = False,
    ) -> None:
        state = self._state()
        now_ms = int(pygame.time.get_ticks())
        times = state.get("_debug_print_ms")
        if not isinstance(times, dict):
            times = {}
        key = str(channel).upper().strip() or "GEN"
        last_ms = int(times.get(key, 0) or 0)
        if (not bool(force)) and (now_ms - last_ms) < max(0, int(min_interval_ms)):
            state["_debug_print_ms"] = times
            return
        print(f"[{self._subportal_label()}][{key}] {message}")
        times[key] = now_ms
        state["_debug_print_ms"] = times

    @staticmethod
    def _debug_print_for_state(
        state: Dict[str, object],
        label: str,
        channel: str,
        message: str,
        min_interval_ms: int = 1000,
        force: bool = False,
    ) -> None:
        if not isinstance(state, dict):
            return
        now_ms = int(pygame.time.get_ticks())
        times = state.get("_debug_print_ms")
        if not isinstance(times, dict):
            times = {}
        key = str(channel).upper().strip() or "GEN"
        last_ms = int(times.get(key, 0) or 0)
        if (not bool(force)) and (now_ms - last_ms) < max(0, int(min_interval_ms)):
            state["_debug_print_ms"] = times
            return
        print(f"[{str(label).strip() or 'TSD'}][{key}] {message}")
        times[key] = now_ms
        state["_debug_print_ms"] = times

    @classmethod
    def _fetch_hsd_roads_async(cls, lat: float, lon: float, radius_m: float) -> None:
        with cls._road_overlay_lock:
            if bool(cls._road_overlay_fetch_inflight):
                return
            cls._road_overlay_fetch_inflight = True
        center_lat = float(lat)
        center_lon = float(lon)
        query_radius_m = max(5000.0, min(45000.0, float(radius_m)))

        def _worker() -> None:
            segments: List[Tuple[float, float, float, float]] = []
            ok = False
            try:
                overpass_query = (
                    f"[out:json][timeout:25];"
                    f"(way[\"highway\"](around:{int(round(query_radius_m))},{center_lat:.6f},{center_lon:.6f}););"
                    f"(._;>;);out body;"
                )
                payload = urllib.parse.urlencode({"data": overpass_query}).encode("utf-8")
                req = urllib.request.Request(
                    "https://overpass-api.de/api/interpreter",
                    data=payload,
                    headers={"User-Agent": "F35-PCD-TSD/1.0", "Content-Type": "application/x-www-form-urlencoded"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=12.0) as resp:
                    body = resp.read()
                data = json.loads(body.decode("utf-8", errors="replace"))
                elements = data.get("elements", []) if isinstance(data, dict) else []
                if not isinstance(elements, list):
                    elements = []
                nodes: Dict[int, Tuple[float, float]] = {}
                ways: List[Dict[str, object]] = []
                for el in elements:
                    if not isinstance(el, dict):
                        continue
                    et = str(el.get("type", "")).strip().lower()
                    if et == "node":
                        try:
                            nid = int(el.get("id"))
                            nlat = float(el.get("lat"))
                            nlon = float(el.get("lon"))
                            nodes[nid] = (nlat, nlon)
                        except Exception:
                            continue
                    elif et == "way":
                        ways.append(el)
                for way in ways:
                    nlist = way.get("nodes", [])
                    if not isinstance(nlist, list) or len(nlist) < 2:
                        continue
                    for i in range(len(nlist) - 1):
                        try:
                            a_id = int(nlist[i])
                            b_id = int(nlist[i + 1])
                        except Exception:
                            continue
                        a = nodes.get(a_id)
                        b = nodes.get(b_id)
                        if not isinstance(a, tuple) or not isinstance(b, tuple):
                            continue
                        try:
                            _brg, dist_nm = cls._bearing_and_distance_nm(float(a[0]), float(a[1]), float(b[0]), float(b[1]))
                        except Exception:
                            continue
                        if float(dist_nm) <= 0.003:
                            continue
                        segments.append((float(a[0]), float(a[1]), float(b[0]), float(b[1])))
                ok = len(segments) > 0
            except Exception:
                ok = False
            with cls._road_overlay_lock:
                cls._road_overlay_fetch_inflight = False
                cls._road_overlay_last_fetch_s = time.monotonic()
                if ok:
                    cls._road_overlay_segments = segments
                    cls._road_overlay_center = (float(center_lat), float(center_lon))
                    cls._road_overlay_radius_m = float(query_radius_m)
                else:
                    cls._road_overlay_last_error_s = time.monotonic()

        th = threading.Thread(target=_worker, name="TSDRoadFetch", daemon=True)
        th.start()

    def _maybe_refresh_hsd_road_overlay(self, own_lat: float, own_lon: float, range_nm: float) -> None:
        now_s = time.monotonic()
        requested_radius_m = max(8000.0, min(45000.0, float(range_nm) * 1852.0 * 1.8))
        with self._road_overlay_lock:
            center = self._road_overlay_center
            current_radius_m = float(self._road_overlay_radius_m)
            last_fetch_s = float(self._road_overlay_last_fetch_s)
            inflight = bool(self._road_overlay_fetch_inflight)
            have_data = len(self._road_overlay_segments) > 0
        if inflight:
            return
        need_fetch = not bool(have_data)
        if isinstance(center, tuple) and len(center) == 2:
            try:
                _b, dist_nm = self._bearing_and_distance_nm(float(center[0]), float(center[1]), float(own_lat), float(own_lon))
                dist_m = float(dist_nm) * 1852.0
            except Exception:
                dist_m = float(requested_radius_m)
            if dist_m > max(1800.0, current_radius_m * 0.40):
                need_fetch = True
            if requested_radius_m > (current_radius_m * 1.15):
                need_fetch = True
        if (now_s - last_fetch_s) > 900.0:
            need_fetch = True
        if need_fetch:
            self._fetch_hsd_roads_async(float(own_lat), float(own_lon), float(requested_radius_m))

    def _draw_hsd_road_overlay(
        self,
        surface: pygame.Surface,
        center: Tuple[int, int],
        range_nm: float,
        heading_deg: float,
        clamp_rect: Optional[pygame.Rect] = None,
    ) -> None:
        own = self._own_lat_lon()
        if own is None:
            return
        own_lat, own_lon = own
        self._maybe_refresh_hsd_road_overlay(float(own_lat), float(own_lon), float(range_nm))
        with self._road_overlay_lock:
            segments = list(self._road_overlay_segments)
        if len(segments) <= 0:
            return
        max_range_nm = max(0.2, float(range_nm))
        px_per_nm = (4.0 * float(DPI)) / max_range_nm
        prev_clip = surface.get_clip()
        if isinstance(clamp_rect, pygame.Rect) and clamp_rect.width > 0 and clamp_rect.height > 0:
            surface.set_clip(prev_clip.clip(clamp_rect))
        drawn = 0
        for a_lat, a_lon, b_lat, b_lon in segments:
            try:
                brg_a, dist_a = self._bearing_and_distance_nm(float(own_lat), float(own_lon), float(a_lat), float(a_lon))
                brg_b, dist_b = self._bearing_and_distance_nm(float(own_lat), float(own_lon), float(b_lat), float(b_lon))
            except Exception:
                continue
            if float(dist_a) > (max_range_nm * 1.35) and float(dist_b) > (max_range_nm * 1.35):
                continue
            rel_a = (float(brg_a) - float(heading_deg)) % 360.0
            rel_b = (float(brg_b) - float(heading_deg)) % 360.0
            ra = max(0.0, min(max_range_nm * 1.4, float(dist_a))) * px_per_nm
            rb = max(0.0, min(max_range_nm * 1.4, float(dist_b))) * px_per_nm
            p0 = self._polar_from_north(center, ra, rel_a)
            p1 = self._polar_from_north(center, rb, rel_b)
            pygame.draw.line(surface, (255, 0, 0), p0, p1, 1)
            drawn += 1
            if drawn >= 3000:
                break
        surface.set_clip(prev_clip)

    def opaque_subportal_background(self) -> bool:
        return True

    @staticmethod
    def _vsd_bg_color_key() -> str:
        lt_state = str(SMS_STATE.get("lt_state", "CLOSE")).upper()
        rt_state = str(SMS_STATE.get("rt_state", "CLOSE")).upper()
        if lt_state in {"PARTIAL", "OPEN"} or rt_state in {"PARTIAL", "OPEN"}:
            return "red"
        return "green"

    @classmethod
    def _get_vsd_bg_circle_surface(cls, color_key: str, diameter: int) -> Optional[pygame.Surface]:
        d = max(1, int(diameter))
        key = (str(color_key).lower(), d)
        if key in cls._vsd_bg_circle_cache:
            return cls._vsd_bg_circle_cache[key]

        raw_key = str(color_key).lower()
        if raw_key not in cls._vsd_bg_raw_cache:
            filename = "VSD RED.png" if raw_key == "red" else "VSD GREEN.png"
            img_path = Path(resource_path(Path("icons") / "TSD" / filename))
            raw_surface: Optional[pygame.Surface]
            if not img_path.exists():
                raw_surface = None
            else:
                try:
                    raw_surface = pygame.image.load(str(img_path)).convert_alpha()
                except Exception:
                    raw_surface = None
            cls._vsd_bg_raw_cache[raw_key] = raw_surface
        raw = cls._vsd_bg_raw_cache.get(raw_key)
        if raw is None:
            cls._vsd_bg_circle_cache[key] = None
            return None

        scaled = pygame.transform.smoothscale(raw, (d, d))
        clipped = pygame.Surface((d, d), pygame.SRCALPHA)
        clipped.blit(scaled, (0, 0))
        mask = pygame.Surface((d, d), pygame.SRCALPHA)
        radius = d // 2
        pygame.draw.circle(mask, (255, 255, 255, 255), (radius, radius), radius, 0)
        clipped.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        cls._vsd_bg_circle_cache[key] = clipped
        return clipped

    def _draw_vsd_bg_image(self, surface: pygame.Surface, center: Tuple[int, int], outer_r: int) -> None:
        diameter = max(2, int(outer_r) * 2)
        color_key = self._vsd_bg_color_key()
        bg = self._get_vsd_bg_circle_surface(color_key, diameter)
        if bg is None:
            return
        bg_rect = bg.get_rect(center=center)
        surface.blit(bg, bg_rect)

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
        state = self._state()
        state["hsd_secondary_cursor_norm"] = (max(0.0, min(1.0, nx)), max(0.0, min(1.0, ny)))
        state["hsd_secondary_track_id"] = None
        state["hsd_secondary_track_active"] = False
        state["hsd_secondary_track_data"] = {}
        state["hsd_secondary_lock_pending"] = True

    def _clear_hsd_secondary_cursor(self) -> None:
        state = self._state()
        state["hsd_secondary_cursor_norm"] = None
        state["hsd_secondary_track_id"] = None
        state["hsd_secondary_track_active"] = False
        state["hsd_secondary_track_data"] = {}
        state["hsd_secondary_fusion_id"] = ""
        state["hsd_secondary_confidence"] = 0.0
        state["hsd_secondary_lock_pending"] = False

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
        size = max(3, int(round(25.0 * 0.75)))
        half_len = size
        y_off = size
        return size, half_len, y_off

    @staticmethod
    def _angle_delta_deg(a: float, b: float) -> float:
        return ((float(a) - float(b) + 180.0) % 360.0) - 180.0

    def _fusion_id_for_contact(self, contact_id: str) -> str:
        global TSD_GLOBAL_CONTACT_FUSION_IDS
        mapping = TSD_GLOBAL_CONTACT_FUSION_IDS
        if not isinstance(mapping, dict):
            mapping = {}
            TSD_GLOBAL_CONTACT_FUSION_IDS = mapping
        key = str(contact_id).strip().upper()
        if key == "":
            key = f"UNK_{random.randint(0, 999999):06d}"
        existing = str(mapping.get(key, "")).strip()
        if len(existing) == 3 and existing.isdigit():
            return existing
        used = {str(v) for v in mapping.values() if isinstance(v, str)}
        for _ in range(1200):
            cand = f"{random.randint(0, 999):03d}"
            if cand not in used:
                mapping[key] = cand
                return cand
        fallback = f"{random.randint(0, 999):03d}"
        mapping[key] = fallback
        return fallback

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
            state["hsd_secondary_track_data"] = {}
            state["hsd_secondary_track_id"] = None
            state["hsd_secondary_lock_pending"] = False
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
                    fusion_id = str(item.get("fusion_id", "")).strip()
                    if fusion_id == "":
                        fusion_id = self._fusion_id_for_contact(str(item.get("id", "")))
                    state["hsd_secondary_fusion_id"] = fusion_id
                    try:
                        conf = float(state.get("hsd_secondary_confidence", 0.0))
                    except Exception:
                        conf = 0.0
                    if conf < 0.70 or conf > 0.99:
                        state["hsd_secondary_confidence"] = round(random.uniform(0.70, 0.99), 2)
                    state["hsd_secondary_track_data"] = dict(item)
                    state["hsd_secondary_track_active"] = True
                    return
            state["hsd_secondary_track_active"] = False
            state["hsd_secondary_track_data"] = {}
            state["hsd_secondary_track_id"] = None
            return

        lock_pending = bool(state.get("hsd_secondary_lock_pending", False))
        if not lock_pending:
            state["hsd_secondary_track_active"] = False
            state["hsd_secondary_track_data"] = {}
            return
        state["hsd_secondary_lock_pending"] = False

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
            state["hsd_secondary_track_data"] = {}
            state["hsd_secondary_track_id"] = None
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
            state["hsd_secondary_track_data"] = {}
            return
        state["hsd_secondary_track_id"] = best_id
        best_fusion = str(best.get("fusion_id", "")).strip()
        if best_fusion == "":
            best_fusion = self._fusion_id_for_contact(best_id)
        last_printed_id = str(state.get("hsd_secondary_last_printed_id", ""))
        if best_id != last_printed_id:
            raw_row = best.get("raw_row")
            print(f"[TSD ADSB TARGET] {best_id}")
            if isinstance(raw_row, dict):
                try:
                    print(json.dumps(raw_row, indent=2, sort_keys=True))
                except Exception:
                    print(str(raw_row))
            else:
                print(str(best))
            state["hsd_secondary_last_printed_id"] = best_id
        state["hsd_secondary_fusion_id"] = best_fusion
        state["hsd_secondary_confidence"] = round(random.uniform(0.70, 0.99), 2)
        tx = int(best.get("x", cx))
        ty = int(best.get("y", cy))
        nx = float(tx - border_rect.left) / float(max(1, border_rect.width - 1))
        ny = float(ty - border_rect.top) / float(max(1, border_rect.height - 1))
        state["hsd_secondary_cursor_norm"] = (max(0.0, min(1.0, nx)), max(0.0, min(1.0, ny)))
        state["hsd_secondary_track_data"] = dict(best)
        state["hsd_secondary_track_active"] = True

    def _draw_hsd_tracking_panel(self, surface: pygame.Surface, border_rect: pygame.Rect) -> None:
        state = self._state()
        if not bool(state.get("hsd_secondary_track_active", False)):
            return

        panel_w = max(1, int(round(2.9 * DPI)))
        panel_h = max(1, int(round(1.125 * DPI)))
        right_gap = int(round(0.25 * DPI))
        right_x = border_rect.right - right_gap
        left_x = right_x - panel_w
        bottom_y = border_rect.bottom - 1
        top_y = bottom_y - panel_h
        if left_x < border_rect.left + 1:
            left_x = border_rect.left + 1
            right_x = min(border_rect.right - 1, left_x + panel_w)
        if top_y < border_rect.top + 1:
            top_y = border_rect.top + 1
            bottom_y = min(border_rect.bottom - 1, top_y + panel_h)
        panel = pygame.Rect(left_x, top_y, max(1, right_x - left_x), max(1, bottom_y - top_y))

        white = (255, 255, 255)
        yellow = (255, 255, 0)
        cyan = (0, 255, 255)
        # Opaque black background so HSD symbology/targets do not show through.
        pygame.draw.rect(surface, (0, 0, 0), panel, 0)
        pygame.draw.rect(surface, white, panel, 1)

        h_small = int(round(0.1875 * DPI))
        # Bottom row is 0.375in; top four are 0.1875in each.
        y1 = panel.top + h_small
        y2 = y1 + h_small
        y3 = y2 + h_small
        y4 = y3 + h_small
        for yy in (y1, y2, y3, y4):
            if yy < panel.bottom:
                pygame.draw.line(surface, white, (panel.left, yy), (panel.right, yy), 1)

        fusion_id = str(state.get("hsd_secondary_fusion_id", "")).strip()
        if fusion_id == "":
            fusion_id = f"{random.randint(0, 999):03d}"
            state["hsd_secondary_fusion_id"] = fusion_id
        try:
            conf_val = float(state.get("hsd_secondary_confidence", 0.0))
        except Exception:
            conf_val = 0.0
        if conf_val < 0.70 or conf_val > 0.99:
            conf_val = round(random.uniform(0.70, 0.99), 2)
            state["hsd_secondary_confidence"] = conf_val

        labels = ["FUSION AFF", "FUSION ID", "CONFIDENCE", "ESM"]
        values = ["U 0.0", fusion_id, f"{conf_val:.2f}", fusion_id]
        colors = [yellow, white, white, white]

        font = get_font(13)
        label_x = panel.left + 6
        value_x = panel.left + int(round(1.45 * DPI))
        row_tops = [panel.top, y1, y2, y3]
        row_bottoms = [y1, y2, y3, y4]
        for i in range(4):
            rt = row_tops[i]
            rb = row_bottoms[i]
            cy = rt + max(1, (rb - rt)) // 2
            ls = font.render(labels[i], True, white)
            vs = font.render(values[i], True, colors[i])
            lr = ls.get_rect(left=label_x, centery=cy)
            vr = vs.get_rect(left=value_x, centery=cy)
            surface.blit(ls, lr)
            surface.blit(vs, vr)

        # Bottom row target data (for currently tracked target).
        trk = state.get("hsd_secondary_track_data", {})
        if isinstance(trk, dict) and len(trk) > 0:
            try:
                rel_brg = float(trk.get("rel_bearing_deg", 0.0)) % 360.0
            except Exception:
                rel_brg = 0.0
            try:
                rng_nm = max(0.0, float(trk.get("range_nm", 0.0)))
            except Exception:
                rng_nm = 0.0
            try:
                hdg_deg = float(trk.get("heading_deg", 0.0)) % 360.0
            except Exception:
                hdg_deg = 0.0
            try:
                vc = int(round(float(trk.get("closure_kts", 0.0))))
            except Exception:
                vc = 0
            fusion_id = str(trk.get("fusion_id", state.get("hsd_secondary_fusion_id", ""))).strip()
            if fusion_id == "":
                fusion_id = str(state.get("hsd_secondary_fusion_id", ""))
            line1 = f"{int(round(rel_brg)) % 360:03d}\u00b0/{rng_nm:.1f}/HDG {int(round(hdg_deg)) % 360:03d}\u00b0/Vc{vc}"
            line2 = f"{fusion_id}L"
            btm_top = y4
            btm_bottom = panel.bottom
            btm_h = max(1, btm_bottom - btm_top)
            f2 = get_font(11)
            s1 = f2.render(line1, True, cyan)
            s2 = f2.render(line2, True, cyan)
            y_line1 = btm_top + max(0, int(round(0.22 * btm_h - s1.get_height() * 0.5)))
            y_line2 = btm_top + max(0, int(round(0.72 * btm_h - s2.get_height() * 0.5)))
            surface.blit(s1, s1.get_rect(left=label_x, y=y_line1))
            surface.blit(s2, s2.get_rect(left=label_x, y=y_line2))

        # Extra info boxes above panel (touching top edge): icon box + left info box.
        icon_box_w = max(1, int(round(0.375 * DPI)))
        icon_box_h = max(1, int(round(0.6 * DPI)))
        icon_box = pygame.Rect(panel.right - icon_box_w, panel.top - icon_box_h, icon_box_w, icon_box_h)
        left_box_w = max(1, int(round(0.75 * DPI)))
        left_box_h = max(1, int(round(0.1875 * DPI)))
        left_box = pygame.Rect(icon_box.left - left_box_w, panel.top - left_box_h, left_box_w, left_box_h)

        # Keep these boxes within the grey HSD border while preserving right alignment.
        if icon_box.top < border_rect.top:
            dy = border_rect.top - icon_box.top
            icon_box.y += dy
            left_box.y += dy
        if left_box.left < border_rect.left:
            shift = border_rect.left - left_box.left
            left_box.x += shift
            icon_box.x += shift
            if icon_box.right > panel.right:
                icon_box.right = panel.right
            if left_box.right > icon_box.left:
                left_box.right = icon_box.left

        for box in (left_box, icon_box):
            pygame.draw.rect(surface, (0, 0, 0), box, 0)
            pygame.draw.rect(surface, white, box, 1)

        # Left mini-info box intentionally left empty.

        # Icon box: tracked icon (no rotation) + ID below icon.
        trk_aff = "UNKNOWN"
        trk_dom = "AIR"
        if isinstance(trk, dict):
            trk_aff = str(trk.get("affiliation", "UNKNOWN")).upper().strip() or "UNKNOWN"
            trk_dom = str(trk.get("domain", "AIR")).upper().strip() or "AIR"
        id_text = str(fusion_id).strip() if str(fusion_id).strip() != "" else "---"
        id_font = get_font(11)
        id_surf = id_font.render(id_text, True, white)
        id_h = id_surf.get_height()
        icon_max_w = max(2, icon_box.width - 4)
        icon_max_h = max(2, icon_box.height - id_h - 5)
        icon_size = max(2, min(icon_max_w, icon_max_h))
        ticon = self._get_adsb_contact_icon(trk_aff, trk_dom, icon_size, 0.0)
        if ticon is not None:
            # Force icon in this box to white regardless of tracked affiliation.
            ticon_white = ticon.copy()
            ticon_white.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
            ticon_white.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_ADD)
            trect = ticon_white.get_rect(centerx=icon_box.centerx, top=icon_box.top + 2)
            surface.blit(ticon_white, trect)
        id_rect = id_surf.get_rect(centerx=icon_box.centerx, bottom=icon_box.bottom - 2)
        surface.blit(id_surf, id_rect)

    def _draw_hsd_secondary_cursor(self, surface: pygame.Surface, border_rect: pygame.Rect) -> None:
        if not bool(self._state().get("hsd_secondary_track_active", False)):
            return
        pos = self._hsd_secondary_cursor_screen_pos(border_rect)
        if pos is None:
            return
        x, y = pos
        green = (0, 255, 0)
        size, half_len, y_off = self._secondary_cursor_shape_params()
        left_x = x - y_off
        right_x = x + y_off
        pygame.draw.line(surface, green, (left_x, y - half_len), (left_x, y + half_len), 1)
        pygame.draw.line(surface, green, (right_x, y - half_len), (right_x, y + half_len), 1)
        pygame.draw.circle(surface, green, (x, y), max(1, int(round(size * 0.12))), 0)
        self._draw_hsd_tracking_panel(surface, border_rect)

    def _draw_toi_marker(
        self,
        surface: pygame.Surface,
        border_rect: pygame.Rect,
        center: Tuple[int, int],
        range_nm: float,
        own_heading_deg: float,
    ) -> None:
        toi = TSD_TOI_STATE if isinstance(TSD_TOI_STATE, dict) else {}
        if not bool(toi.get("active", False)):
            return
        try:
            toi_lat = float(toi.get("lat"))
            toi_lon = float(toi.get("lon"))
        except Exception:
            return
        snap = TSD_ADSB_STATE if isinstance(TSD_ADSB_STATE, dict) else {}
        own_lat = self._safe_float(snap.get("lat"))
        own_lon = self._safe_float(snap.get("lon"))
        if own_lat is None or own_lon is None:
            geo = snap.get("geo")
            if isinstance(geo, dict):
                own_lat = self._safe_float(geo.get("lat"))
                own_lon = self._safe_float(geo.get("lon"))
        if own_lat is None or own_lon is None:
            return
        bearing_deg, dist_nm = self._bearing_and_distance_nm(float(own_lat), float(own_lon), float(toi_lat), float(toi_lon))
        rel_bearing_deg = (float(bearing_deg) - float(own_heading_deg)) % 360.0
        max_range_nm = max(0.001, float(range_nm))
        radial_px = (float(dist_nm) / max_range_nm) * float(4.0 * DPI)
        x, y = self._polar_from_north(center, radial_px, rel_bearing_deg)
        if isinstance(border_rect, pygame.Rect) and border_rect.width > 0 and border_rect.height > 0:
            x = max(border_rect.left, min(border_rect.right - 1, int(x)))
            y = max(border_rect.top, min(border_rect.bottom - 1, int(y)))
        green = (0, 255, 0)
        _, half_len, y_off = self._secondary_cursor_shape_params()
        top_y = int(y - half_len)
        bot_y = int(y + half_len)
        base_gap = max(2, int(2 * y_off))
        top_gap = max(2, int(base_gap - 4))
        bot_gap = max(2, int(base_gap + 4))
        lt_x = int(round(float(x) - (float(top_gap) * 0.5)))
        lb_x = int(round(float(x) - (float(bot_gap) * 0.5)))
        rt_x = int(round(float(x) + (float(top_gap) * 0.5)))
        rb_x = int(round(float(x) + (float(bot_gap) * 0.5)))
        pygame.draw.line(surface, green, (lt_x, top_y), (lb_x, bot_y), 1)
        pygame.draw.line(surface, green, (rt_x, top_y), (rb_x, bot_y), 1)

    def _auto_follow_tracked_target_on_zoom(
        self,
        symbol_center: Tuple[int, int],
        border_rect: pygame.Rect,
    ) -> None:
        state = self._state()
        if not bool(state.get("hsd_secondary_track_active", False)):
            return
        zoom_scale = self._kbd_zoom_scale(self._range_nm())
        if zoom_scale <= 1.0005:
            return
        trk = state.get("hsd_secondary_track_data", {})
        if not isinstance(trk, dict) or len(trk) <= 0:
            return
        try:
            trk_range_nm = float(trk.get("range_nm", 0.0))
        except Exception:
            trk_range_nm = 0.0
        max_follow_range_nm = self._effective_range_nm(self._range_nm())
        if trk_range_nm > max_follow_range_nm:
            return
        if bool(trk.get("is_clamped", False)):
            return
        try:
            tx = int(trk.get("x", symbol_center[0]))
            ty = int(trk.get("y", symbol_center[1]))
        except Exception:
            return
        dx = int(symbol_center[0]) - int(tx)
        dy = int(symbol_center[1]) - int(ty)
        if abs(dx) <= 0 and abs(dy) <= 0:
            return
        pan_x, pan_y = self._kbd_pan_offset_px()
        max_pan_px = float(6.0 * DPI)
        pan_x = max(-max_pan_px, min(max_pan_px, float(pan_x) + float(dx)))
        pan_y = max(-max_pan_px, min(max_pan_px, float(pan_y) + float(dy)))
        state["kbd_pan_x_px"] = float(pan_x)
        state["kbd_pan_y_px"] = float(pan_y)

    @staticmethod
    def _polar_from_north(center: Tuple[int, int], radius_px: float, angle_deg_from_north: float) -> Tuple[int, int]:
        cx, cy = center
        theta = math.radians(float(angle_deg_from_north))
        x = int(round(cx + radius_px * math.sin(theta)))
        y = int(round(cy - radius_px * math.cos(theta)))
        return x, y

    @staticmethod
    def _read_heading_deg() -> float:
        try:
            return float(TwdFormat._read_heading_deg())
        except Exception:
            try:
                return float(TWD_STATE.get("heading_deg", 35.0)) % 360.0
            except Exception:
                return 35.0

    def _state(self) -> Dict[str, object]:
        key = self._normalize_tsd_name(getattr(self, "name", "TSD1"))
        state = TSD_STATES_BY_NAME.get(key)
        if not isinstance(state, dict):
            state = _new_tsd_state()
            TSD_STATES_BY_NAME[key] = state
        return state

    def _range_nm(self) -> float:
        state = self._state()
        try:
            value = float(state.get("range_nm", 20.0))
        except Exception:
            value = 20.0
        return self._quantize_range_nm(value)

    def _set_range_nm(self, value: float) -> None:
        state = self._state()
        try:
            raw = float(value)
        except Exception:
            raw = 20.0
        state["range_nm"] = self._quantize_range_nm(raw)

    def _kbd_zoom_scale(self, base_range_nm: Optional[float] = None) -> float:
        state = self._state()
        if base_range_nm is None:
            base = self._range_nm()
        else:
            base = self._quantize_range_nm(base_range_nm)
        try:
            value = float(state.get("kbd_zoom_scale", 1.0))
        except Exception:
            value = 1.0
        max_scale = max(1.0, float(base) / 0.01)
        value = max(1.0, min(max_scale, value))
        if abs(value - 1.0) < 0.0005:
            value = 1.0
        state["kbd_zoom_scale"] = float(value)
        return float(value)

    def _set_kbd_zoom_scale(self, value: float, base_range_nm: Optional[float] = None) -> None:
        state = self._state()
        if base_range_nm is None:
            base = self._range_nm()
        else:
            base = self._quantize_range_nm(base_range_nm)
        try:
            raw = float(value)
        except Exception:
            raw = 1.0
        max_scale = max(1.0, float(base) / 0.01)
        raw = max(1.0, min(max_scale, raw))
        if abs(raw - 1.0) < 0.0005:
            raw = 1.0
        state["kbd_zoom_scale"] = float(raw)

    def _effective_range_nm(self, base_range_nm: Optional[float] = None) -> float:
        if base_range_nm is None:
            base = self._range_nm()
        else:
            base = self._quantize_range_nm(base_range_nm)
        zoom_scale = self._kbd_zoom_scale(base)
        value = float(base) / max(1.0, float(zoom_scale))
        value = max(0.01, min(float(base), value))
        return float(value)

    def _kbd_pan_offset_px(self) -> Tuple[float, float]:
        state = self._state()
        try:
            pan_x = float(state.get("kbd_pan_x_px", 0.0))
        except Exception:
            pan_x = 0.0
        try:
            pan_y = float(state.get("kbd_pan_y_px", 0.0))
        except Exception:
            pan_y = 0.0
        state["kbd_pan_x_px"] = float(pan_x)
        state["kbd_pan_y_px"] = float(pan_y)
        return float(pan_x), float(pan_y)

    @staticmethod
    def _quantize_range_nm(value: float) -> float:
        try:
            v = float(value)
        except Exception:
            v = 15.0
        allowed = Tsd1Format._range_options()
        # Choose nearest allowed range; for ties, choose the lower value.
        return min(allowed, key=lambda x: (abs(x - v), x))

    @staticmethod
    def _range_options() -> List[float]:
        return [7.5, 15.0, 30.0, 60.0, 120.0, 240.0]

    def _adjust_range_nm(self, direction: int) -> None:
        opts = self._range_options()
        curr = self._quantize_range_nm(self._range_nm())
        idx = 0
        for i, v in enumerate(opts):
            if abs(float(v) - float(curr)) < 1e-6:
                idx = i
                break
        idx = max(0, min(len(opts) - 1, idx + (1 if int(direction) > 0 else -1)))
        self._set_range_nm(float(opts[idx]))

    def _view_label(self) -> str:
        state = self._state()
        try:
            idx = int(state.get("view_idx", 0))
        except Exception:
            idx = 0
        idx = 1 if idx == 1 else 0
        state["view_idx"] = idx
        return "VSD" if idx == 1 else "HSD"

    def _is_vsd(self) -> bool:
        state = self._state()
        try:
            return int(state.get("view_idx", 0)) == 1
        except Exception:
            return False

    def _emc_label(self) -> str:
        state = self._state()
        try:
            idx = int(state.get("emc_idx", 3))
        except Exception:
            idx = 3
        idx = max(0, min(3, idx))
        state["emc_idx"] = idx
        return f"EMC{idx + 1}"

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
        ]
        return ordered[: max(0, int(count))]

    def _active_t2_l3_popup_key(self) -> str:
        state = self._state()
        if bool(state.get("t2_menu_open", False)):
            return "T2"
        if bool(state.get("l3_menu_open", False)) and (not self._is_vsd()):
            return "L3"
        return ""

    def _close_t2_l3_popups(self) -> None:
        state = self._state()
        state["t2_menu_open"] = False
        state["l3_menu_open"] = False

    def _set_popup_anchor_portal_index(self, portal_index: Optional[int]) -> None:
        state = self._state()
        try:
            idx = int(portal_index) if portal_index is not None else int(state.get("_popup_anchor_portal_idx", 0))
        except Exception:
            idx = int(state.get("_popup_anchor_portal_idx", 0) or 0)
        state["_popup_anchor_portal_idx"] = max(0, min(3, idx))

    def _popup_grid_rect(self, base_rect: pygame.Rect) -> pygame.Rect:
        popup_w = 5 * GRID_CELL_W
        popup_h = 8 * GRID_CELL_H
        width = int(base_rect.width)
        if width <= popup_w:
            x = int(base_rect.x)
        elif width >= int((10 * DPI) - 1):
            try:
                idx = int(self._state().get("_popup_anchor_portal_idx", 0))
            except Exception:
                idx = 0
            x = int(base_rect.x) if (idx % 2 == 0) else int(base_rect.right - popup_w)
        else:
            x = int(base_rect.x + max(0, (width - popup_w) // 2))
        return pygame.Rect(x, base_rect.top, popup_w, popup_h)

    def _draw_t2_l3_popup(self, surface: pygame.Surface, rect: pygame.Rect, context: FormatContext) -> None:
        popup_key = self._active_t2_l3_popup_key()
        if popup_key == "":
            return
        state = self._state()
        if popup_key == "T2":
            options = ["HSD", "VSD"]
            try:
                selected_idx = int(state.get("view_idx", 0))
            except Exception:
                selected_idx = 0
            selected_idx = 1 if selected_idx == 1 else 0
        else:
            options = ["EMC1", "EMC2", "EMC3", "EMC4"]
            try:
                selected_idx = int(state.get("emc_idx", 3))
            except Exception:
                selected_idx = 3
            selected_idx = max(0, min(len(options) - 1, selected_idx))

        cyan = (0, 255, 255)
        white = (255, 255, 255)
        option_cells = self._gol_popup_option_cells(rect, len(options))
        for cell_name in option_cells:
            box = self._popup_cell_rect(rect, cell_name)
            if box is None:
                continue
            surface.fill((0, 0, 0), box)
            pygame.draw.rect(surface, cyan, box, 1)
        font = get_font(16)
        for idx, opt in enumerate(options):
            if idx >= len(option_cells):
                break
            box = self._popup_cell_rect(rect, option_cells[idx])
            if box is None:
                continue
            is_selected = idx == int(selected_idx)
            key = f"{popup_key}_OPT_{idx}"
            flashing = bool(context.is_osb_flashing(key))
            color = (0, 0, 0) if flashing else (white if is_selected else cyan)
            txt = font.render(str(opt), True, color)
            tr = txt.get_rect(center=box.center)
            if flashing:
                pygame.draw.rect(surface, white, tr.inflate(4, 2))
            elif is_selected:
                pygame.draw.rect(surface, white, tr.inflate(6, 3), 1)
            surface.blit(txt, tr)

    def _handle_t2_l3_popup_click(self, pos: Tuple[int, int], rect: pygame.Rect) -> bool:
        popup_key = self._active_t2_l3_popup_key()
        if popup_key == "":
            return False
        state = self._state()
        popup = self._gol_popup_rect(rect)
        if not popup.collidepoint(pos):
            self._close_t2_l3_popups()
            return True
        # Popup options are defined in portal-grid cells (e.g., B3/C3), so map
        # click position against the full portal rect, not popup-local coords.
        cell = self._popup_cell_at_pos(pos, rect)
        if cell is None:
            return True
        if popup_key == "T2":
            option_cells = self._gol_popup_option_cells(rect, 2)
            if cell in option_cells:
                state["view_idx"] = 1 if option_cells.index(cell) == 1 else 0
                if int(state.get("view_idx", 0)) == 1:
                    dclt_state = self._ensure_dclt_state()
                    dclt_state["dclt_menu_open"] = False
                    dclt_state["dclt_cat_menu_open"] = False
                    dclt_state["dclt_submenu"] = ""
                    dclt_state["dclt_data_selected"] = ""
                    dclt_state["dclt_data_input"] = ""
                self._close_t2_l3_popups()
                return True
            return True
        option_cells = self._gol_popup_option_cells(rect, 4)
        if cell in option_cells:
            state["emc_idx"] = max(0, min(3, int(option_cells.index(cell))))
            self._close_t2_l3_popups()
            return True
        return True

    def _atk_value(self) -> int:
        state = self._state()
        try:
            val = int(state.get("atk_value", 360))
        except Exception:
            val = 360
        val = max(0, min(360, val))
        state["atk_value"] = val
        return val

    def _set_atk_value(self, value: int) -> None:
        state = self._state()
        try:
            val = int(value)
        except Exception:
            val = 360
        state["atk_value"] = max(0, min(360, val))

    def _atk_selected(self) -> bool:
        return bool(self._state().get("atk_selected", False))

    def _set_atk_selected(self, selected: bool) -> None:
        self._state()["atk_selected"] = bool(selected)

    def _atk_input(self) -> str:
        return str(self._state().get("atk_input", ""))

    def _set_atk_input(self, value: str) -> None:
        self._state()["atk_input"] = str(value)

    def _ensure_dclt_state(self) -> Dict[str, object]:
        state = self._state()
        state.setdefault("dclt_menu_open", False)
        state.setdefault("dclt_cat_menu_open", False)
        state.setdefault("dclt_submenu", "")
        state.setdefault("dclt_data_selected", "")
        state.setdefault("dclt_data_input", "")
        state.setdefault("_popup_anchor_portal_idx", 0)
        state.setdefault("t2_menu_open", False)
        state.setdefault("l3_menu_open", False)
        state.setdefault("vsd_side_view", False)
        state.setdefault("vsd_l3_pending_toggle_due_ms", 0)
        state.setdefault("dclt_aa_on", True)
        state.setdefault("dclt_as_on", True)
        state.setdefault("dclt_nav_on", True)
        state.setdefault("dclt_rgn1_on", True)
        state.setdefault("dclt_rgn2_on", True)
        state.setdefault("dclt_rgn3_on", True)
        state.setdefault("dclt_max_air", 95)
        state.setdefault("dclt_max_sur", 86)
        state.setdefault("dclt_max_eob", 86)
        state.setdefault("dclt_ears_on", False)
        state.setdefault("dclt_unrng_on", True)
        state.setdefault("dclt_route_idx", 1)
        state.setdefault("dclt_prop_route_idx", 0)
        state.setdefault("dclt_lar_on", False)
        state.setdefault("dclt_mem_on", False)
        state.setdefault("dclt_show_unknown", True)
        state.setdefault("dclt_show_friendly", True)
        state.setdefault("dclt_show_enemy", True)
        state.setdefault("dclt_show_hdg", True)
        state.setdefault("dclt_show_rng_marks", True)
        state.setdefault("dclt_show_fsn_id", True)
        cat_enabled = state.get("dclt_cat_enabled")
        if not isinstance(cat_enabled, dict):
            cat_enabled = {}
        for prefix in ("A", "B"):
            for idx in range(1, 7):
                key = f"{prefix}{idx}"
                cat_enabled[key] = bool(cat_enabled.get(key, True))
        state["dclt_cat_enabled"] = cat_enabled
        return state

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
        if not grid.collidepoint(pos):
            return None
        rel_x = int(pos[0]) - int(grid.x)
        rel_y = int(pos[1]) - int(grid.y)
        col = max(0, min(4, rel_x // max(1, GRID_CELL_W)))
        row = max(0, min(7, rel_y // max(1, GRID_CELL_H)))
        return f"{chr(ord('A') + col)}{row + 1}"

    @staticmethod
    def _popup_cell_from_osb_label(label: str) -> Optional[str]:
        raw = str(label).upper().strip()
        if len(raw) < 2:
            return None
        side = raw[0]
        try:
            idx = int(raw[1:])
        except Exception:
            return None
        if side == "T" and 1 <= idx <= 5:
            return f"{chr(ord('A') + idx - 1)}1"
        if side == "L" and 1 <= idx <= 6:
            return f"A{idx + 1}"
        if side == "R" and 1 <= idx <= 6:
            return f"E{idx + 1}"
        return None

    def _handle_dclt_popup_cell_click(self, cell: str) -> bool:
        state = self._ensure_dclt_state()
        if not bool(state.get("dclt_menu_open", False)):
            return False
        key = str(cell).upper().strip()
        if len(key) < 2:
            return True

        def _toggle_state(flag_key: str) -> bool:
            new_value = not bool(state.get(flag_key, False))
            state[flag_key] = new_value
            return new_value

        submenu = str(state.get("dclt_submenu", "")).upper().strip()
        if submenu == "RGNS":
            region_map = {
                "B3": ("dclt_rgn1_on", ("A1", "B1")),
                "C3": ("dclt_rgn2_on", ("A2", "B2")),
                "D3": ("dclt_rgn3_on", ("A3", "B3")),
            }
            if key in region_map:
                flag, cat_keys = region_map[key]
                is_on = _toggle_state(flag)
                cat_enabled = state.get("dclt_cat_enabled")
                if not isinstance(cat_enabled, dict):
                    cat_enabled = {}
                    state["dclt_cat_enabled"] = cat_enabled
                for cat_key in cat_keys:
                    cat_enabled[str(cat_key)] = bool(is_on)
                return True
            if key == "D6":
                state["dclt_submenu"] = ""
                return True
            return True

        if submenu == "ROUTE":
            route_cells = {"B3": 1, "B4": 2, "B5": 3, "D3": 0}
            prop_cells = {"C3": 1, "C4": 2, "C5": 3, "D4": 0}
            if key in route_cells:
                state["dclt_route_idx"] = int(route_cells[key])
                return True
            if key in prop_cells:
                state["dclt_prop_route_idx"] = int(prop_cells[key])
                return True
            if key == "D6":
                state["dclt_submenu"] = ""
                return True
            return True

        main_cells = ["B3", "C3", "D3", "B4", "C4", "D4", "B5", "C5", "D5", "B6", "C6", "D6"]
        cell_action = {name: idx for idx, name in enumerate(main_cells[:12])}
        action_idx = cell_action.get(key, -1)
        if action_idx == 0:  # AA
            aa_on = _toggle_state("dclt_aa_on")
            state["dclt_show_unknown"] = bool(aa_on)
            state["dclt_show_friendly"] = bool(aa_on)
            state["dclt_show_enemy"] = bool(aa_on)
            return True
        if action_idx == 1:  # AS
            _toggle_state("dclt_as_on")
            return True
        if action_idx == 2:  # NAV
            nav_on = _toggle_state("dclt_nav_on")
            state["dclt_show_hdg"] = bool(nav_on)
            state["dclt_show_rng_marks"] = bool(nav_on)
            return True
        if action_idx == 3:  # RGNS
            state["dclt_submenu"] = "RGNS"
            state["dclt_data_selected"] = ""
            state["dclt_data_input"] = ""
            return True
        if action_idx in {4, 5, 6}:  # MAX AIR/SUR/EOB
            field = {4: "dclt_max_air", 5: "dclt_max_sur", 6: "dclt_max_eob"}[action_idx]
            if str(state.get("dclt_data_selected", "")) == field:
                self._commit_dclt_data_input(field)
                state["dclt_data_selected"] = ""
                state["dclt_data_input"] = ""
            else:
                state["dclt_data_selected"] = field
                state["dclt_data_input"] = ""
            return True
        if action_idx == 7:  # EARS
            _toggle_state("dclt_ears_on")
            return True
        if action_idx == 8:  # UNRNG
            _toggle_state("dclt_unrng_on")
            return True
        if action_idx == 9:  # ROUTE
            state["dclt_submenu"] = "ROUTE"
            state["dclt_data_selected"] = ""
            state["dclt_data_input"] = ""
            return True
        if action_idx == 10:  # LAR
            _toggle_state("dclt_lar_on")
            return True
        if action_idx == 11:  # MEM
            _toggle_state("dclt_mem_on")
            return True
        return True

    def _dclt_popup_rect(self, base_rect: pygame.Rect) -> pygame.Rect:
        return self._popup_grid_rect(base_rect)

    @staticmethod
    def _dclt_covers_osb_label(label: str) -> bool:
        raw = str(label).upper().strip()
        if len(raw) < 2:
            return False
        side = raw[0]
        try:
            idx = int(raw[1:])
        except Exception:
            return False
        if side == "L":
            return 1 <= idx <= 6
        if side == "T":
            return 1 <= idx <= 5
        return False

    def _draw_dclt_popup(self, surface: pygame.Surface, rect: pygame.Rect, context: FormatContext) -> None:
        state = self._ensure_dclt_state()
        now_ms = int(pygame.time.get_ticks())
        cyan = (0, 255, 255)
        white = (255, 255, 255)
        popup = self._gol_popup_rect(rect)
        if popup.width <= 1 or popup.height <= 1:
            return
        surface.fill((0, 0, 0), popup)
        pygame.draw.rect(surface, cyan, popup, 1)
        grid = self._popup_grid_rect(rect)
        for c in (1, 2):
            x = grid.x + ((1 + c) * GRID_CELL_W)
            pygame.draw.line(surface, cyan, (x, popup.top), (x, popup.bottom), 1)
        for r in (4, 5, 6):
            y = grid.y + ((r - 1) * GRID_CELL_H)
            pygame.draw.line(surface, cyan, (popup.left, y), (popup.right, y), 1)

        def _draw_toggle(cell: str, text: str, is_on: bool, btn_id: str) -> None:
            box = self._popup_cell_rect(rect, cell)
            if box is None:
                return
            bs = ButtonState(
                button_id=btn_id,
                button_type=ButtonType.MOMENTARY_SINGLE,
                text=text,
                is_single_function=True,
                is_on=bool(is_on),
                h_align="center",
                v_align="center",
                padding=OSB_PADDING,
                font_size=14,
                flash_until_ms=1 if context.is_osb_flashing(cell) else 0,
            )
            render_button(surface, box, bs, get_font, now_ms)

        def _draw_page(cell: str, text: str, selected: bool = False) -> None:
            box = self._popup_cell_rect(rect, cell)
            if box is None:
                return
            bs = ButtonState(
                button_id=f"TSD1_DCLT_{cell}",
                button_type=ButtonType.PAGE_ACCESS,
                text=text,
                h_align="center",
                v_align="center",
                padding=OSB_PADDING,
                font_size=14,
                flash_until_ms=1 if context.is_osb_flashing(cell) else 0,
            )
            render_button(surface, box, bs, get_font, now_ms)
            if selected:
                font = get_font(14)
                lines = [font.render(line, True, white) for line in text.split("\n")]
                total_h = sum(s.get_height() for s in lines) + max(0, len(lines) - 1)
                y = box.centery - total_h // 2
                rects: List[pygame.Rect] = []
                for surf in lines:
                    rr = surf.get_rect(centerx=box.centerx, y=y)
                    rects.append(rr)
                    y += surf.get_height() + 1
                if rects:
                    bound = rects[0].copy()
                    for rr in rects[1:]:
                        bound.union_ip(rr)
                    pygame.draw.rect(surface, white, bound.inflate(6, 3), 1)
                    for surf, rr in zip(lines, rects):
                        surface.blit(surf, rr)

        def _draw_data(cell: str, label: str, field_key: str) -> None:
            box = self._popup_cell_rect(rect, cell)
            if box is None:
                return
            try:
                value = int(state.get(field_key, 0))
            except Exception:
                value = 0
            selected = str(state.get("dclt_data_selected", "")) == field_key
            pending = str(state.get("dclt_data_input", ""))
            value_text = pending if (selected and pending != "") else str(value)
            font = get_font(14)
            lines = label.split("\n") + [value_text]
            y = box.centery - (sum(font.render(t, True, cyan).get_height() for t in lines) + max(0, len(lines) - 1)) // 2
            value_rect: Optional[pygame.Rect] = None
            for idx, line in enumerate(lines):
                color = white if (selected and idx == len(lines) - 1) else cyan
                surf = font.render(str(line), True, color)
                rr = surf.get_rect(centerx=box.centerx, y=y)
                surface.blit(surf, rr)
                if idx == len(lines) - 1:
                    value_rect = rr
                y += surf.get_height() + 1
            if selected and value_rect is not None:
                pygame.draw.rect(surface, white, value_rect.inflate(6, 3), 1)

        submenu = str(state.get("dclt_submenu", "")).upper().strip()
        if submenu == "RGNS":
            _draw_toggle("B3", "RGN1", bool(state.get("dclt_rgn1_on", True)), "TSD1_DCLT_RGN1")
            _draw_toggle("C3", "RGN2", bool(state.get("dclt_rgn2_on", True)), "TSD1_DCLT_RGN2")
            _draw_toggle("D3", "RGN3", bool(state.get("dclt_rgn3_on", True)), "TSD1_DCLT_RGN3")
            _draw_page("D6", "<BACK")
            return
        if submenu == "ROUTE":
            for cell, idx in (("B3", 1), ("B4", 2), ("B5", 3)):
                _draw_page(cell, f"RTE{idx}", selected=int(state.get("dclt_route_idx", 1) or 1) == idx)
            _draw_page("D3", "ROUTE\nOFF", selected=int(state.get("dclt_route_idx", 1) or 1) == 0)
            for cell, idx in (("C3", 1), ("C4", 2), ("C5", 3)):
                _draw_page(cell, f"PRP{idx}", selected=int(state.get("dclt_prop_route_idx", 0) or 0) == idx)
            _draw_page("D4", "PROP\nOFF", selected=int(state.get("dclt_prop_route_idx", 0) or 0) == 0)
            _draw_page("D6", "<BACK")
            return

        _draw_toggle("B3", "AA", bool(state.get("dclt_aa_on", True)), "TSD1_DCLT_AA")
        _draw_toggle("C3", "AS", bool(state.get("dclt_as_on", True)), "TSD1_DCLT_AS")
        _draw_toggle("D3", "NAV", bool(state.get("dclt_nav_on", True)), "TSD1_DCLT_NAV")
        _draw_page("B4", "RGNS")
        _draw_data("C4", "MAX\nAIR", "dclt_max_air")
        _draw_data("D4", "MAX\nSUR", "dclt_max_sur")
        _draw_data("B5", "MAX\nEOB", "dclt_max_eob")
        _draw_toggle("C5", "EARS", bool(state.get("dclt_ears_on", False)), "TSD1_DCLT_EARS")
        _draw_toggle("D5", "UNRNG", bool(state.get("dclt_unrng_on", True)), "TSD1_DCLT_UNRNG")
        _draw_page("B6", "ROUTE")
        _draw_toggle("C6", "LAR", bool(state.get("dclt_lar_on", False)), "TSD1_DCLT_LAR")
        _draw_toggle("D6", "MEM", bool(state.get("dclt_mem_on", False)), "TSD1_DCLT_MEM")

    def _dclt_data_limits(self, field_key: str) -> Tuple[int, int]:
        key = str(field_key).strip().lower()
        if key == "dclt_max_air":
            return 10, 95
        if key == "dclt_max_sur":
            return 1, 86
        if key == "dclt_max_eob":
            return 0, 86
        return 0, 999

    def _commit_dclt_data_input(self, field_key: str) -> None:
        state = self._ensure_dclt_state()
        raw = "".join(ch for ch in str(state.get("dclt_data_input", "")) if ch.isdigit())
        if raw != "":
            try:
                value = int(raw)
            except Exception:
                value = int(state.get(field_key, 0) or 0)
            lo, hi = self._dclt_data_limits(field_key)
            state[field_key] = max(int(lo), min(int(hi), int(value)))
        state["dclt_data_input"] = ""

    def _apply_dclt_key(self, key: str) -> bool:
        state = self._ensure_dclt_state()
        selected = str(state.get("dclt_data_selected", ""))
        if selected not in {"dclt_max_air", "dclt_max_sur", "dclt_max_eob"}:
            return False
        token = str(key).upper().strip()
        current = str(state.get("dclt_data_input", ""))
        if token in {"KP_BACK", "BACK", "BACKSPACE"}:
            state["dclt_data_input"] = current[:-1]
            return True
        if token in {"ENTER", "RETURN", "KP_ENTER"}:
            self._commit_dclt_data_input(selected)
            state["dclt_data_selected"] = ""
            return True
        if token.startswith("KP_") and len(token) == 4 and token[-1].isdigit():
            digit = token[-1]
        elif len(token) == 1 and token.isdigit():
            digit = token
        else:
            return False
        if len(current) >= 3:
            return True
        state["dclt_data_input"] = current + digit
        return True

    def _commit_atk_input(self) -> None:
        raw = "".join(ch for ch in self._atk_input() if ch.isdigit())
        if raw != "":
            try:
                self._set_atk_value(int(raw))
            except Exception:
                pass
        self._set_atk_input("")
        self._set_atk_selected(False)

    def _apply_atk_key(self, key: str) -> None:
        token = str(key).upper().strip()
        current = self._atk_input()
        if token in {"KP_BACK", "BACK", "BACKSPACE"}:
            self._set_atk_input(current[:-1])
            return
        if token.startswith("KP_") and len(token) == 4 and token[-1].isdigit():
            digit = token[-1]
        elif len(token) == 1 and token.isdigit():
            digit = token
        else:
            digit = ""
        if digit == "":
            return
        self._set_atk_input((current + digit)[-3:])

    @staticmethod
    def _format_range_label(value: float) -> str:
        if abs(value - round(value)) < 0.001:
            return str(int(round(value)))
        return f"{value:.1f}"

    @staticmethod
    def _format_zoom_value_label(value: float) -> str:
        try:
            v = float(value)
        except Exception:
            v = 20.0
        v = max(0.01, v)
        if abs(v - round(v)) < 0.001:
            return str(int(round(v)))
        if v >= 10.0:
            return f"{v:.1f}".rstrip("0").rstrip(".")
        if v >= 1.0:
            return f"{v:.2f}".rstrip("0").rstrip(".")
        return f"{v:.2f}"

    @classmethod
    def _get_cyan_aircraft_icon(cls, size: Tuple[int, int]) -> Optional[pygame.Surface]:
        key = (max(1, int(size[0])), max(1, int(size[1])))
        cached = cls._cyan_icon_cache.get(key)
        if cached is not None:
            return cached
        base = get_green_aircraft_icon(key)
        if base is None:
            return None
        # Force icon to a single flat cyan shade.
        base_mask = pygame.mask.from_surface(base, 1)
        flat = base_mask.to_surface(setcolor=(0, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
        # Keep a true 1px stroke (no post-thickening).
        cls._cyan_icon_cache[key] = flat
        return flat

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
    def _svg_half_lobe_points(cls, steps: int = 40) -> List[Tuple[float, float]]:
        p0 = (63.45, 338.72)
        c1 = cls._bezier_points(
            p0,
            (63.45, 338.72),
            (148.83, 310.70),
            (151.77, 306.05),
            steps,
        )
        c2 = cls._bezier_points(
            (151.77, 306.05),
            (154.71, 301.40),
            (182.18, 281.60),
            (172.34, 212.89),
            steps,
        )
        c3 = cls._bezier_points(
            (172.34, 212.89),
            (162.50, 144.18),
            (83.54, 22.11),
            (86.44, 8.42),
            steps,
        )
        c4 = cls._bezier_points(
            (86.44, 8.42),
            (89.33, -5.26),
            (56.85, 150.30),
            (63.45, 338.72),
            steps,
        )
        return c1 + c2[1:] + c3[1:] + c4[1:]

    @staticmethod
    def _normalize_half_lobe(points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        if len(points) <= 0:
            return []
        xs = [float(p[0]) for p in points]
        ys = [float(p[1]) for p in points]
        min_x = min(xs)
        max_x = max(xs)
        min_y = min(ys)
        max_y = max(ys)
        span_x = max(1e-6, max_x - min_x)
        span_y = max(1e-6, max_y - min_y)
        out: List[Tuple[float, float]] = []
        for x, y in points:
            nx = (float(x) - min_x) / span_x
            ny = 1.0 - ((float(y) - min_y) / span_y)
            out.append((nx, ny))
        return out

    @classmethod
    def _generate_f35_sar_lobes_from_svg(
        cls,
        altitude_ft: float = 10000.0,
        center: Tuple[float, float] = (0.0, 0.0),
        height: float = 280.0,
        width: float = 90.0,
        inner_gap: float = 8.0,
        side_spread: float = 1.0,
        outer_roundness: float = 1.0,
        aft_rounding: float = 1.0,
        steps: int = 40,
    ) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
        base_half = cls._normalize_half_lobe(cls._svg_half_lobe_points(steps=max(20, int(steps))))
        if len(base_half) <= 0:
            return [], []
        alt_scale = cls._sar_altitude_scale(float(altitude_ft))
        h = float(height) * alt_scale
        w = float(width) * alt_scale * max(0.25, float(side_spread))
        g = float(inner_gap) * alt_scale
        cx, cy = float(center[0]), float(center[1])
        right: List[Tuple[float, float]] = []
        for nx, ny in base_half:
            x_curve = float(nx)
            bulge = math.sin(math.pi * float(ny))
            x_curve *= 1.0 + ((float(outer_roundness) - 1.0) * 0.35 * bulge)
            if float(ny) < 0.18:
                x_curve *= 1.0 + ((float(aft_rounding) - 1.0) * (1.0 - (float(ny) / 0.18)) * 0.5)
            x = cx + g + (x_curve * w)
            y = cy + (float(ny) * h)
            right.append((x, y))
        left = [(-x + (2.0 * cx), y) for x, y in right]
        return left, right

    @staticmethod
    def _sar_altitude_scale(
        altitude_ft: float,
        min_alt_ft: float = 250.0,
        max_alt_ft: float = 15000.0,
        min_scale: float = 0.32,
        max_scale: float = 1.0,
    ) -> float:
        t = (float(altitude_ft) - float(min_alt_ft)) / max(1e-6, float(max_alt_ft) - float(min_alt_ft))
        t = max(0.0, min(1.0, t))
        return float(min_scale) + ((float(max_scale) - float(min_scale)) * math.sqrt(t))

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
        altitude_ft = max(0.0, float(agl_m) * 3.28084)
        alt_scale = self._sar_altitude_scale(altitude_ft)
        t_hi = max(0.0, min(1.0, (alt_scale - 0.32) / max(1e-6, 1.0 - 0.32)))
        side_spread = 0.82 + ((1.0 - 0.82) * t_hi)
        outer_roundness = 0.92 + ((1.08 - 0.92) * t_hi)
        aft_rounding = 0.85 + ((1.15 - 0.85) * t_hi)
        left_lobe, right_lobe = self._generate_f35_sar_lobes_from_svg(
            altitude_ft=altitude_ft,
            center=(0.0, 0.0),
            height=280.0,
            width=92.0,
            inner_gap=6.0,
            side_spread=side_spread,
            outer_roundness=outer_roundness,
            aft_rounding=aft_rounding,
            steps=40,
        )
        if len(left_lobe) < 3 and len(right_lobe) < 3:
            return
        _ = heading_deg
        # Scale ears by displayed TSD range so they grow/shrink with OSB range.
        # Keep 120 NM as the neutral baseline.
        effective_range_nm = max(0.1, float(range_nm))
        range_scale = 120.0 / effective_range_nm
        # `range_nm` already reflects keyboard zoom, so do not multiply full zoom
        # again here (that would double-scale). Keep a sane clamp for readability.
        px_scale = max(0.08, min(6.0, float(range_scale)))
        _ = zoom_scale

        def _map_lobe_to_screen(points: List[Tuple[float, float]]) -> List[Tuple[int, int]]:
            mapped: List[Tuple[int, int]] = []
            for x_local, y_local in points:
                x_px = float(x_local) * px_scale
                y_px = float(y_local) * px_scale
                radius = math.hypot(x_px, y_px)
                if radius <= 1e-6:
                    mapped.append((int(center[0]), int(center[1])))
                    continue
                rel_deg = math.degrees(math.atan2(float(x_px), float(y_px)))
                sx, sy = self._polar_from_north(center, radius, rel_deg)
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
    def _is_tacan_vor_navaid_type(raw_type: object) -> bool:
        nav_type = str(raw_type or "").upper().strip().replace("_", "-").replace(" ", "-")
        if nav_type == "":
            return False
        return nav_type.startswith("VOR") or nav_type == "VORTAC" or "TACAN" in nav_type

    @classmethod
    def _load_tacan_vor_navaids(cls) -> List[Dict[str, object]]:
        path = Path(resource_path(Path("DATA") / "navaids.csv"))
        try:
            mtime = path.stat().st_mtime
        except Exception:
            cls._navaid_cache_mtime = None
            cls._navaid_cache = []
            return cls._navaid_cache
        if cls._navaid_cache_mtime == mtime:
            return cls._navaid_cache

        navaids: List[Dict[str, object]] = []
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    if not cls._is_tacan_vor_navaid_type(row.get("type")):
                        continue
                    lat = cls._safe_float(row.get("latitude_deg"))
                    lon = cls._safe_float(row.get("longitude_deg"))
                    if lat is None or lon is None:
                        continue
                    ident = str(row.get("ident") or "").strip().upper()
                    if ident == "":
                        ident = str(row.get("filename") or "").strip().upper()
                    if ident == "":
                        continue
                    navaids.append(
                        {
                            "ident": ident,
                            "name": str(row.get("name") or "").strip(),
                            "type": str(row.get("type") or "").strip().upper(),
                            "lat": float(lat),
                            "lon": float(lon),
                            "frequency_khz": cls._safe_float(row.get("frequency_khz")),
                            "dme_channel": str(row.get("dme_channel") or "").strip().upper(),
                            "associated_airport": str(row.get("associated_airport") or "").strip().upper(),
                        }
                    )
        except Exception:
            navaids = []
        cls._navaid_cache_mtime = mtime
        cls._navaid_cache = navaids
        print(f"[TSD][NAVAIDS_DATA] loaded DATA/navaids.csv entries={len(navaids)}")
        return cls._navaid_cache

    @classmethod
    def _get_tacan_icon(cls, size_px: int) -> Optional[pygame.Surface]:
        px = max(1, int(size_px))
        cache_key = ("V3", px)
        cached = cls._tacan_icon_cache.get(cache_key)
        if cached is not None or cache_key in cls._tacan_icon_cache:
            return cached
        icon_path = Path(resource_path(Path("icons") / "TSD" / "TACAN.svg"))
        icon: Optional[pygame.Surface] = None
        if icon_path.exists():
            try:
                raw = pygame.image.load(str(icon_path)).convert_alpha()
                icon = pygame.transform.smoothscale(raw, (px, px))
                # Keep TACAN as outline only (no interior fill).
                outline = cls._outline_only_from_alpha(icon, edge_width=1)
                icon = outline
                # SVGs ship with black outlines; tint TACAN symbol cyan for map use.
                icon = cls._tint_surface_color(icon, (0, 255, 255))
            except Exception:
                icon = None
        cls._tacan_icon_cache[cache_key] = icon
        return icon

    @staticmethod
    def _format_tacan_channel(raw_channel: object) -> str:
        text = str(raw_channel or "").strip().upper()
        if text == "":
            return ""
        m = re.match(r"^0*([0-9]+)([XY])$", text)
        if m is not None:
            return f"{m.group(1)}{m.group(2)}"
        return text[:5]

    @classmethod
    def _load_faa_ils_by_airport(cls) -> Dict[str, List[Dict[str, object]]]:
        ils_path = Path(resource_path(Path("DATA") / "FAA" / "ILS_BASE.csv"))
        rwy_end_path = Path(resource_path(Path("DATA") / "FAA" / "APT_RWY_END.csv"))
        try:
            ils_stat = ils_path.stat()
            rwy_stat = rwy_end_path.stat()
            cache_key = (
                float(ils_stat.st_mtime),
                int(ils_stat.st_size),
                float(rwy_stat.st_mtime),
                int(rwy_stat.st_size),
            )
        except Exception:
            cls._faa_ils_cache_key = None
            cls._faa_ils_by_airport = {}
            cls._faa_ils_entries = []
            return cls._faa_ils_by_airport
        if cls._faa_ils_cache_key == cache_key:
            return cls._faa_ils_by_airport

        runway_end_info: Dict[Tuple[str, str], Dict[str, object]] = {}
        try:
            with rwy_end_path.open("r", encoding="utf-8-sig", newline="") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    airport_ident = str(row.get("ARPT_ID") or "").strip().upper()
                    runway_end_id = str(row.get("RWY_END_ID") or "").strip().upper()
                    if airport_ident == "" or runway_end_id == "":
                        continue
                    key = (airport_ident, runway_end_id)
                    if key in runway_end_info:
                        continue
                    runway_end_info[key] = {
                        "runway_id": str(row.get("RWY_ID") or "").strip().upper(),
                        "runway_end_id": runway_end_id,
                        "airport_ident": airport_ident,
                        "true_alignment_deg": cls._safe_float(row.get("TRUE_ALIGNMENT")),
                        "ils_type": str(row.get("ILS_TYPE") or "").strip().upper(),
                    }
        except Exception:
            runway_end_info = {}

        by_airport: Dict[str, List[Dict[str, object]]] = {}
        entries: List[Dict[str, object]] = []
        try:
            with ils_path.open("r", encoding="utf-8-sig", newline="") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    airport_ident = str(row.get("ARPT_ID") or "").strip().upper()
                    runway_end_id = str(row.get("RWY_END_ID") or "").strip().upper()
                    loc_freq = cls._safe_float(row.get("LOC_FREQ"))
                    if airport_ident == "" or runway_end_id == "" or loc_freq is None:
                        continue
                    if float(loc_freq) <= 0.0:
                        continue

                    end_info = runway_end_info.get((airport_ident, runway_end_id), {})
                    apch_bear = cls._safe_float(row.get("APCH_BEAR"))
                    true_alignment = cls._safe_float(end_info.get("true_alignment_deg"))
                    course_deg: Optional[float]
                    if true_alignment is not None:
                        course_deg = float(true_alignment) % 360.0
                    elif apch_bear is not None:
                        course_deg = float(apch_bear) % 360.0
                    else:
                        course_deg = None

                    item: Dict[str, object] = {
                        "airport_ident": airport_ident,
                        "runway_end_id": runway_end_id,
                        "runway_id": str(end_info.get("runway_id") or "").strip().upper(),
                        "loc_freq_mhz": float(loc_freq),
                        "loc_freq_text": f"{float(loc_freq):.2f}",
                        "ils_loc_id": str(row.get("ILS_LOC_ID") or "").strip().upper(),
                        "system_type": str(row.get("SYSTEM_TYPE_CODE") or "").strip().upper(),
                        "category": str(row.get("CATEGORY") or "").strip().upper(),
                        "status": str(row.get("COMPONENT_STATUS") or "").strip().upper(),
                        "bk_course_status": str(row.get("BK_COURSE_STATUS_CODE") or "").strip().upper(),
                        "apch_bear_deg": float(apch_bear) % 360.0 if apch_bear is not None else None,
                        "runway_true_alignment_deg": float(true_alignment) % 360.0 if true_alignment is not None else None,
                        "course_deg": course_deg,
                        "lat": cls._safe_float(row.get("LAT_DECIMAL")),
                        "lon": cls._safe_float(row.get("LONG_DECIMAL")),
                        "city": str(row.get("CITY") or "").strip(),
                        "state_code": str(row.get("STATE_CODE") or "").strip().upper(),
                        "country_code": str(row.get("COUNTRY_CODE") or "").strip().upper(),
                    }
                    by_airport.setdefault(airport_ident, []).append(item)
                    entries.append(item)
        except Exception:
            by_airport = {}
            entries = []

        for airport_ident, vals in by_airport.items():
            vals.sort(key=lambda x: (str(x.get("runway_id", "")), str(x.get("runway_end_id", "")), float(x.get("loc_freq_mhz", 0.0))))
            by_airport[airport_ident] = vals
        entries.sort(key=lambda x: (str(x.get("airport_ident", "")), str(x.get("runway_end_id", "")), float(x.get("loc_freq_mhz", 0.0))))

        cls._faa_ils_cache_key = cache_key
        cls._faa_ils_by_airport = by_airport
        cls._faa_ils_entries = entries
        print(f"[FAA][ILS_DATA] loaded airports={len(by_airport)} entries={len(entries)}")
        return cls._faa_ils_by_airport

    @classmethod
    def _faa_ils_entries_flat(cls) -> List[Dict[str, object]]:
        cls._load_faa_ils_by_airport()
        return cls._faa_ils_entries

    @classmethod
    def _resolve_faa_ils_solution(
        cls,
        freq_mhz: float,
        *,
        own_lat: Optional[float] = None,
        own_lon: Optional[float] = None,
        max_range_nm: float = 220.0,
    ) -> Optional[Dict[str, object]]:
        try:
            target = float(freq_mhz)
        except Exception:
            return None
        entries = cls._faa_ils_entries_flat()
        if len(entries) <= 0:
            return None
        # FAA frequency precision is two decimals; tolerate half-step for float parse noise.
        tol = 0.006
        matches: List[Dict[str, object]] = []
        for item in entries:
            try:
                f = float(item.get("loc_freq_mhz", -1.0))
            except Exception:
                continue
            if abs(f - target) <= tol:
                matches.append(item)
        if len(matches) <= 0:
            return None
        if own_lat is None or own_lon is None:
            return dict(matches[0])

        best: Optional[Dict[str, object]] = None
        best_dist = float("inf")
        for item in matches:
            lat = cls._safe_float(item.get("lat"))
            lon = cls._safe_float(item.get("lon"))
            if lat is None or lon is None:
                continue
            brg, dist_nm = cls._bearing_and_distance_nm(float(own_lat), float(own_lon), float(lat), float(lon))
            if float(dist_nm) < best_dist:
                out = dict(item)
                out["bearing_deg"] = float(brg) % 360.0
                out["distance_nm"] = float(dist_nm)
                best = out
                best_dist = float(dist_nm)
        if best is None:
            return dict(matches[0])
        if best_dist > float(max_range_nm):
            return None
        return best

    @staticmethod
    def _airport_military_text_match(text: object) -> bool:
        raw = f" {str(text or '').upper()} "
        compact = raw.replace(".", " ").replace("-", " ").replace("_", " ")
        terms = (
            " AIR FORCE BASE ",
            " AIR FORCE STATION ",
            " AIR BASE ",
            " AFB ",
            " ANGB ",
            " SPACE FORCE BASE ",
            " SFB ",
            " JOINT BASE ",
            " NAVAL AIR STATION ",
            " NAVAL AIR BASE ",
            " NAS ",
            " NAF ",
            " NAVY ",
            " ARMY AIRFIELD ",
            " ARMY AIR FIELD ",
            " ARMY AVIATION ",
            " MARINE CORPS AIR STATION ",
            " MCAS ",
            " MILITARY ",
            " RCAF ",
            " RAF ",
            " RNAS ",
            " USAF ",
            " USN ",
            " USMC ",
            " BASE AEREA ",
            " AIR NATIONAL GUARD ",
        )
        return any(term in compact for term in terms)

    @classmethod
    def _load_airports_by_ident(cls) -> Dict[str, Dict[str, object]]:
        path = Path(resource_path(Path("DATA") / "airports.csv"))
        try:
            mtime = path.stat().st_mtime
        except Exception:
            cls._airport_cache_mtime = None
            cls._airport_cache_by_ident = {}
            return cls._airport_cache_by_ident
        if cls._airport_cache_mtime == mtime:
            return cls._airport_cache_by_ident

        airports: Dict[str, Dict[str, object]] = {}
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    ident = str(row.get("ident") or "").strip().upper()
                    if ident == "":
                        continue
                    lat = cls._safe_float(row.get("latitude_deg"))
                    lon = cls._safe_float(row.get("longitude_deg"))
                    if lat is None or lon is None:
                        continue
                    name_text = str(row.get("name") or "")
                    text = " ".join(
                        str(row.get(key) or "")
                        for key in ("name", "keywords", "home_link", "wikipedia_link", "municipality")
                    )
                    airports[ident] = {
                        "id": str(row.get("id") or "").strip(),
                        "ident": ident,
                        "type": str(row.get("type") or "").strip(),
                        "name": name_text.strip(),
                        "lat": float(lat),
                        "lon": float(lon),
                        "is_military_name": cls._airport_military_text_match(name_text),
                        "is_military_text": cls._airport_military_text_match(text),
                    }
        except Exception:
            airports = {}
        cls._airport_cache_mtime = mtime
        cls._airport_cache_by_ident = airports
        # Runway military coloring depends on airport metadata.
        cls._runway_cache_mtime = None
        return cls._airport_cache_by_ident

    @classmethod
    def _load_airport_frequency_military_idents(cls) -> Set[str]:
        path = Path(resource_path(Path("DATA") / "airport-frequencies.csv"))
        try:
            mtime = path.stat().st_mtime
        except Exception:
            cls._airport_frequency_cache_mtime = None
            cls._airport_frequency_military_idents = set()
            return cls._airport_frequency_military_idents
        if cls._airport_frequency_cache_mtime == mtime:
            return cls._airport_frequency_military_idents

        idents: Set[str] = set()
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    ident = str(row.get("airport_ident") or "").strip().upper()
                    if ident == "":
                        continue
                    freq_type = str(row.get("type") or "").strip().upper()
                    desc = f" {str(row.get('description') or '').upper()} "
                    desc_norm = desc.replace(".", " ").replace("-", " ").replace("_", " ")
                    freq_military = freq_type == "MIL" or any(
                        term in desc_norm
                        for term in (
                            " MIL ",
                            " MIL OPS ",
                            " MILITARY ",
                            " USAF ",
                            " USN ",
                            " USMC ",
                            " NAVY ",
                            " ARMY OPS ",
                            " ARMY AVIATION ",
                            " ANG ",
                            " AIR NATIONAL GUARD ",
                        )
                    )
                    if freq_military:
                        idents.add(ident)
        except Exception:
            idents = set()
        cls._airport_frequency_cache_mtime = mtime
        cls._airport_frequency_military_idents = idents
        # Runway military coloring depends on frequency hints.
        cls._runway_cache_mtime = None
        return cls._airport_frequency_military_idents

    @classmethod
    def _is_military_airport_ident(cls, ident: object) -> bool:
        key = str(ident or "").strip().upper()
        if key == "":
            return False
        airport = cls._load_airports_by_ident().get(key)
        if isinstance(airport, dict):
            return bool(airport.get("is_military_name", False))
        if key in cls._load_airport_frequency_military_idents():
            return True
        return False

    @staticmethod
    def _runway_heading_from_ident(raw_ident: object) -> Optional[float]:
        text = str(raw_ident or "").strip().upper()
        m = re.match(r"^([0-3]?[0-9])", text)
        if m is None:
            return None
        try:
            number = int(m.group(1))
        except Exception:
            return None
        if number <= 0:
            return 360.0
        if number > 36:
            return None
        return float((number * 10) % 360)

    @classmethod
    def _runway_endpoint_pair(cls, row: Dict[str, object], airport: Optional[Dict[str, object]]) -> Optional[Tuple[float, float, float, float, float]]:
        le_lat = cls._safe_float(row.get("le_latitude_deg"))
        le_lon = cls._safe_float(row.get("le_longitude_deg"))
        he_lat = cls._safe_float(row.get("he_latitude_deg"))
        he_lon = cls._safe_float(row.get("he_longitude_deg"))
        le_hdg = cls._safe_float(row.get("le_heading_degT"))
        he_hdg = cls._safe_float(row.get("he_heading_degT"))
        length_ft = cls._safe_float(row.get("length_ft"))
        if length_ft is None or length_ft <= 0.0:
            return None
        length_nm = float(length_ft) / 6076.12

        if le_hdg is None and he_hdg is not None:
            le_hdg = (float(he_hdg) + 180.0) % 360.0
        if le_hdg is None:
            le_hdg = cls._runway_heading_from_ident(row.get("le_ident"))
        if le_hdg is None and he_hdg is not None:
            le_hdg = (float(he_hdg) + 180.0) % 360.0

        if le_lat is not None and le_lon is not None and he_lat is not None and he_lon is not None:
            if le_hdg is None:
                le_hdg, _dist_nm = cls._bearing_and_distance_nm(float(le_lat), float(le_lon), float(he_lat), float(he_lon))
            le_hdg = float(le_hdg) % 360.0
            return float(le_lat), float(le_lon), float(he_lat), float(he_lon), le_hdg
        if le_hdg is None:
            return None
        le_hdg = float(le_hdg) % 360.0
        if le_lat is not None and le_lon is not None:
            est_he_lat, est_he_lon = cls._project_lat_lon_nm(float(le_lat), float(le_lon), le_hdg, length_nm)
            return float(le_lat), float(le_lon), float(est_he_lat), float(est_he_lon), le_hdg
        if he_lat is not None and he_lon is not None:
            est_le_lat, est_le_lon = cls._project_lat_lon_nm(float(he_lat), float(he_lon), (le_hdg + 180.0) % 360.0, length_nm)
            return float(est_le_lat), float(est_le_lon), float(he_lat), float(he_lon), le_hdg
        if not isinstance(airport, dict):
            return None
        apt_lat = cls._safe_float(airport.get("lat"))
        apt_lon = cls._safe_float(airport.get("lon"))
        if apt_lat is None or apt_lon is None:
            return None
        half_nm = length_nm * 0.5
        est_le_lat, est_le_lon = cls._project_lat_lon_nm(float(apt_lat), float(apt_lon), (le_hdg + 180.0) % 360.0, half_nm)
        est_he_lat, est_he_lon = cls._project_lat_lon_nm(float(apt_lat), float(apt_lon), le_hdg, half_nm)
        return float(est_le_lat), float(est_le_lon), float(est_he_lat), float(est_he_lon), le_hdg

    @classmethod
    def _runway_record_from_row(
        cls,
        row: Dict[str, object],
        airport: Optional[Dict[str, object]],
        is_military: bool,
    ) -> Optional[Dict[str, object]]:
        if str(row.get("closed") or "0").strip() in {"1", "TRUE", "true", "True"}:
            return None
        airport_ident = str(row.get("airport_ident") or "").strip().upper()
        if airport_ident == "":
            return None
        length_ft = cls._safe_float(row.get("length_ft"))
        width_ft = cls._safe_float(row.get("width_ft"))
        if length_ft is None or length_ft <= 0.0:
            return None
        if float(length_ft) < 100.0:
            return None
        pair = cls._runway_endpoint_pair(row, airport)
        if pair is None:
            return None
        le_lat, le_lon, he_lat, he_lon, le_heading = pair
        mid_lat = (float(le_lat) + float(he_lat)) * 0.5
        mid_lon = (float(le_lon) + float(he_lon)) * 0.5
        return {
            "airport_ident": airport_ident,
            "airport_name": str((airport or {}).get("name", "")),
            "is_military": bool(is_military),
            "length_ft": float(length_ft),
            "width_ft": float(width_ft or 0.0),
            "surface": str(row.get("surface") or "").strip(),
            "le_ident": str(row.get("le_ident") or "").strip().upper(),
            "he_ident": str(row.get("he_ident") or "").strip().upper(),
            "le_lat": float(le_lat),
            "le_lon": float(le_lon),
            "he_lat": float(he_lat),
            "he_lon": float(he_lon),
            "mid_lat": float(mid_lat),
            "mid_lon": float(mid_lon),
            "le_heading_deg": float(le_heading) % 360.0,
            "le_displaced_threshold_ft": float(cls._safe_float(row.get("le_displaced_threshold_ft")) or 0.0),
        }

    @classmethod
    def _build_runway_spatial_index(cls, runways: List[Dict[str, object]]) -> Dict[Tuple[int, int], List[Dict[str, object]]]:
        index: Dict[Tuple[int, int], List[Dict[str, object]]] = {}
        for runway in runways:
            try:
                mid_lat = float(runway.get("mid_lat"))
                mid_lon = float(runway.get("mid_lon"))
            except Exception:
                continue
            key = (int(math.floor(mid_lat)), int(math.floor(mid_lon)))
            bucket = index.get(key)
            if bucket is None:
                bucket = []
                index[key] = bucket
            bucket.append(runway)
        return index

    @classmethod
    def _runway_disk_cache_path(cls) -> Path:
        try:
            cache_dir = writable_path("CACHE")
        except Exception:
            cache_dir = Path.cwd() / "CACHE"
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            cache_dir = Path.cwd()
        return cache_dir / f"tsd_runways_cache_v{int(cls._runway_cache_file_version)}.pkl"

    @classmethod
    def _load_runways_from_disk_cache(cls, source_mtime: float, source_size: int) -> Optional[List[Dict[str, object]]]:
        cache_path = cls._runway_disk_cache_path()
        if not cache_path.exists():
            return None
        try:
            with cache_path.open("rb") as fh:
                payload = pickle.load(fh)
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        try:
            version = int(payload.get("version", 0))
            cached_mtime = float(payload.get("source_mtime", -1.0))
            cached_size = int(payload.get("source_size", -1))
        except Exception:
            return None
        if version != int(cls._runway_cache_file_version):
            return None
        if abs(cached_mtime - float(source_mtime)) > 1e-6 or cached_size != int(source_size):
            return None
        runways = payload.get("runways")
        if not isinstance(runways, list):
            return None
        return runways

    @classmethod
    def _save_runways_to_disk_cache(cls, runways: List[Dict[str, object]], source_mtime: float, source_size: int) -> None:
        cache_path = cls._runway_disk_cache_path()
        tmp_path = cache_path.with_suffix(f"{cache_path.suffix}.tmp")
        payload = {
            "version": int(cls._runway_cache_file_version),
            "source_mtime": float(source_mtime),
            "source_size": int(source_size),
            "runways": runways,
        }
        with tmp_path.open("wb") as fh:
            pickle.dump(payload, fh, protocol=pickle.HIGHEST_PROTOCOL)
        tmp_path.replace(cache_path)

    @classmethod
    def _load_runways_worker(cls, path: Path, mtime: float, source_size: int) -> None:
        runways: List[Dict[str, object]] = []
        loaded_from_disk = False
        try:
            cached = cls._load_runways_from_disk_cache(mtime, source_size)
            if isinstance(cached, list):
                runways = cached
                loaded_from_disk = True
            else:
                airports = cls._load_airports_by_ident()
                military_idents: Set[str] = set()
                for ident, airport in airports.items():
                    if isinstance(airport, dict) and bool(airport.get("is_military_name", False)):
                        military_idents.add(str(ident).strip().upper())
                military_idents.update(cls._load_airport_frequency_military_idents())
                with path.open("r", encoding="utf-8-sig", newline="") as fh:
                    reader = csv.DictReader(fh)
                    for row in reader:
                        airport_ident = str(row.get("airport_ident") or "").strip().upper()
                        if airport_ident == "":
                            continue
                        airport = airports.get(airport_ident)
                        runway = cls._runway_record_from_row(row, airport, airport_ident in military_idents)
                        if runway is not None:
                            runways.append(runway)
                try:
                    cls._save_runways_to_disk_cache(runways, mtime, source_size)
                except Exception as exc:
                    print(f"[TSD][RUNWAYS_DATA] failed to save runway cache: {exc}")
        except Exception:
            runways = []

        index = cls._build_runway_spatial_index(runways)
        with cls._runway_cache_lock:
            cls._runway_cache = runways
            cls._runway_spatial_index = index
            cls._runway_cache_mtime = mtime
            cls._runway_cache_loading = False
            cls._runway_cache_target_mtime = None
        src = "disk cache" if loaded_from_disk else "csv parse"
        print(f"[TSD][RUNWAYS_DATA] loaded DATA/runways.csv entries={len(runways)} (async, source={src})")

    @classmethod
    def _load_runways(cls) -> List[Dict[str, object]]:
        path = Path(resource_path(Path("DATA") / "runways.csv"))
        try:
            stat = path.stat()
            mtime = stat.st_mtime
            source_size = int(stat.st_size)
        except Exception:
            with cls._runway_cache_lock:
                cls._runway_cache_mtime = None
                cls._runway_cache = []
                cls._runway_spatial_index = {}
                cls._runway_cache_loading = False
                cls._runway_cache_target_mtime = None
            return []

        start_loader = False
        snapshot: List[Dict[str, object]] = []
        with cls._runway_cache_lock:
            snapshot = cls._runway_cache
            if cls._runway_cache_mtime == mtime:
                return snapshot
            if (not cls._runway_cache_loading) or (cls._runway_cache_target_mtime != mtime):
                cls._runway_cache_loading = True
                cls._runway_cache_target_mtime = mtime
                start_loader = True

        if start_loader:
            try:
                worker = threading.Thread(
                    target=cls._load_runways_worker,
                    args=(path, mtime, source_size),
                    name="TSDRunwayLoader",
                    daemon=True,
                )
                worker.start()
                print("[TSD][RUNWAYS_DATA] async runway load started")
            except Exception:
                with cls._runway_cache_lock:
                    cls._runway_cache_loading = False
                    cls._runway_cache_target_mtime = None
        return snapshot

    @classmethod
    def nearest_military_runway(cls, lat: object, lon: object) -> Optional[Dict[str, object]]:
        own_lat = cls._safe_float(lat)
        own_lon = cls._safe_float(lon)
        if own_lat is None or own_lon is None:
            return None
        airports = cls._load_airports_by_ident()
        military_airports: List[Tuple[float, str, Dict[str, object]]] = []
        for ident, airport in airports.items():
            if not isinstance(airport, dict) or not bool(airport.get("is_military_name", False)):
                continue
            apt_lat = cls._safe_float(airport.get("lat"))
            apt_lon = cls._safe_float(airport.get("lon"))
            if apt_lat is None or apt_lon is None:
                continue
            _bearing, dist_nm = cls._bearing_and_distance_nm(float(own_lat), float(own_lon), float(apt_lat), float(apt_lon))
            military_airports.append((float(dist_nm), str(ident), airport))
        if len(military_airports) <= 0:
            return None
        military_airports.sort(key=lambda item: item[0])

        candidate_airports = military_airports[:80]
        candidate_idents = {ident for _dist, ident, _airport in candidate_airports}
        candidate_runways: Dict[str, List[Dict[str, object]]] = {ident: [] for ident in candidate_idents}
        path = Path(resource_path(Path("DATA") / "runways.csv"))
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    ident = str(row.get("airport_ident") or "").strip().upper()
                    if ident not in candidate_idents:
                        continue
                    runway = cls._runway_record_from_row(row, airports.get(ident), True)
                    if runway is not None:
                        candidate_runways.setdefault(ident, []).append(runway)
        except Exception:
            return None
        for _dist, ident, _airport in candidate_airports:
            runways = candidate_runways.get(ident, [])
            if len(runways) <= 0:
                continue
            return dict(max(runways, key=lambda rw: float(rw.get("length_ft", 0.0) or 0.0)))
        return None

    @classmethod
    def spawn_point_for_runway(cls, runway: Dict[str, object]) -> Optional[Dict[str, float]]:
        try:
            le_lat = float(runway.get("le_lat"))
            le_lon = float(runway.get("le_lon"))
            heading = float(runway.get("le_heading_deg", 0.0)) % 360.0
            length_ft = max(1.0, float(runway.get("length_ft", 0.0) or 0.0))
        except Exception:
            return None
        displaced_ft = max(0.0, float(runway.get("le_displaced_threshold_ft", 0.0) or 0.0))
        offset_ft = max(250.0, displaced_ft)
        offset_ft = min(offset_ft, length_ft * 0.25)
        lat, lon = cls._project_lat_lon_nm(le_lat, le_lon, heading, offset_ft / 6076.12)
        return {"lat": float(lat), "lon": float(lon), "heading_deg": float(heading)}

    def _draw_hsd_navaid_markers(
        self,
        surface: pygame.Surface,
        center: Tuple[int, int],
        range_nm: float,
        own_heading_deg: float,
        clamp_rect: Optional[pygame.Rect] = None,
    ) -> None:
        own = self._own_lat_lon()
        if own is None:
            return
        own_lat, own_lon = own
        navaids = self._load_tacan_vor_navaids()
        if len(navaids) <= 0:
            return

        outer_radius_px = float(4.0 * DPI)
        max_range_nm = max(0.001, float(range_nm))
        max_screen_radius_px = outer_radius_px
        if isinstance(clamp_rect, pygame.Rect) and clamp_rect.width > 0 and clamp_rect.height > 0:
            for sx, sy in (
                (clamp_rect.left, clamp_rect.top),
                (clamp_rect.right, clamp_rect.top),
                (clamp_rect.left, clamp_rect.bottom),
                (clamp_rect.right, clamp_rect.bottom),
            ):
                max_screen_radius_px = max(
                    max_screen_radius_px,
                    math.hypot(float(center[0] - sx), float(center[1] - sy)),
                )
        visible_range_nm = max_range_nm * (max_screen_radius_px / outer_radius_px) * 1.05
        lat_window_deg = max(0.05, visible_range_nm / 60.0)
        cos_lat = max(0.15, abs(math.cos(math.radians(float(own_lat)))))
        lon_window_deg = max(0.05, visible_range_nm / (60.0 * cos_lat))

        candidates: List[Tuple[float, int, int, Dict[str, object]]] = []
        for nav in navaids:
            try:
                lat = float(nav.get("lat"))
                lon = float(nav.get("lon"))
            except Exception:
                continue
            if abs(lat - float(own_lat)) > lat_window_deg or abs(lon - float(own_lon)) > lon_window_deg:
                continue
            bearing_deg, dist_nm = self._bearing_and_distance_nm(float(own_lat), float(own_lon), lat, lon)
            if dist_nm > visible_range_nm:
                continue
            rel_bearing_deg = (float(bearing_deg) - float(own_heading_deg)) % 360.0
            radial_px = (float(dist_nm) / max_range_nm) * outer_radius_px
            px, py = self._polar_from_north(center, radial_px, rel_bearing_deg)
            if isinstance(clamp_rect, pygame.Rect) and clamp_rect.width > 0 and clamp_rect.height > 0:
                pad = max(18, int(round(0.22 * DPI)))
                if px < clamp_rect.left - pad or px > clamp_rect.right + pad or py < clamp_rect.top - pad or py > clamp_rect.bottom + pad:
                    continue
            candidates.append((float(dist_nm), int(px), int(py), nav))

        if len(candidates) <= 0:
            return
        candidates.sort(key=lambda item: item[0])
        candidates = candidates[:120]
        dclt_state = self._ensure_dclt_state()
        now_ms = int(pygame.time.get_ticks())
        last_nav_ms = int(dclt_state.get("_tsd_nav_stage_last_ms", 0) or 0)
        if last_nav_ms <= 0 or (now_ms - last_nav_ms) > 500:
            dclt_state["_tsd_nav_stage_start_ms"] = now_ms
        nav_start_ms = int(dclt_state.get("_tsd_nav_stage_start_ms", now_ms) or now_ms)
        nav_elapsed_ms = max(0, now_ms - nav_start_ms)
        nav_initial_budget = 0
        nav_growth = int(nav_elapsed_ms // 30)  # +33 icons/sec
        nav_budget = max(nav_initial_budget, min(len(candidates), nav_initial_budget + nav_growth))
        dclt_state["_tsd_nav_stage_last_ms"] = now_ms

        cyan = (0, 255, 255)
        black = (0, 0, 0)
        font = get_font(10)
        icon_px = max(1, int(round(0.45 * DPI)))
        tacan_icon: Optional[pygame.Surface] = None
        marker_r = max(5, int(round(0.075 * DPI)))
        drawn_count = 0
        tacan_drawn = 0
        vor_drawn = 0
        for _, px, py, nav in candidates[:nav_budget]:
            if isinstance(clamp_rect, pygame.Rect) and clamp_rect.width > 0 and clamp_rect.height > 0:
                if not clamp_rect.collidepoint((px, py)):
                    continue
            nav_type = str(nav.get("type", "")).upper().strip()
            is_tacan = "TACAN" in nav_type or nav_type == "VORTAC"
            label_gap = marker_r + 3
            if is_tacan and tacan_icon is None:
                tacan_icon = self._get_tacan_icon(icon_px)
            if is_tacan and tacan_icon is not None:
                ir = tacan_icon.get_rect(center=(px, py))
                if isinstance(clamp_rect, pygame.Rect) and clamp_rect.width > 0 and clamp_rect.height > 0:
                    if not ir.colliderect(clamp_rect):
                        continue
                surface.blit(tacan_icon, ir)
                drawn_count += 1
                tacan_drawn += 1
                label_gap = (icon_px // 2) + 3
            elif is_tacan:
                if isinstance(clamp_rect, pygame.Rect) and clamp_rect.width > 0 and clamp_rect.height > 0:
                    fallback_rect = pygame.Rect(px - marker_r, py - marker_r, marker_r * 2 + 1, marker_r * 2 + 1)
                    if not fallback_rect.colliderect(clamp_rect):
                        continue
                points = [(px, py - marker_r), (px + marker_r, py), (px, py + marker_r), (px - marker_r, py)]
                pygame.draw.polygon(surface, cyan, points, 1)
                drawn_count += 1
                tacan_drawn += 1
            if is_tacan:
                channel = self._format_tacan_channel(nav.get("dme_channel"))
                if channel != "":
                    channel_font = get_font(11)
                    ch_surf = channel_font.render(channel, True, (255, 255, 255))
                    ch_rect = ch_surf.get_rect(center=(px, py))
                    pygame.draw.rect(surface, black, ch_rect.inflate(4, 2), 0)
                    surface.blit(ch_surf, ch_rect)
                continue
            else:
                if isinstance(clamp_rect, pygame.Rect) and clamp_rect.width > 0 and clamp_rect.height > 0:
                    vor_rect = pygame.Rect(px - marker_r, py - marker_r, marker_r * 2 + 1, marker_r * 2 + 1)
                    if not vor_rect.colliderect(clamp_rect):
                        continue
                points = []
                for idx in range(6):
                    angle = math.radians(30.0 + idx * 60.0)
                    points.append((int(round(px + marker_r * math.cos(angle))), int(round(py + marker_r * math.sin(angle)))))
                pygame.draw.polygon(surface, cyan, points, 1)
                drawn_count += 1
                vor_drawn += 1

            ident = str(nav.get("ident", "")).strip().upper()
            if ident == "":
                continue
            label = font.render(ident[:5], True, cyan)
            label_rect = label.get_rect(left=px + label_gap, centery=py)
            if isinstance(clamp_rect, pygame.Rect) and clamp_rect.width > 0 and clamp_rect.height > 0:
                if label_rect.right > clamp_rect.right - 1:
                    label_rect.right = px - label_gap
                if label_rect.left < clamp_rect.left + 1:
                    label_rect.left = clamp_rect.left + 1
                if label_rect.top < clamp_rect.top + 1:
                    label_rect.top = clamp_rect.top + 1
                if label_rect.bottom > clamp_rect.bottom - 1:
                    label_rect.bottom = clamp_rect.bottom - 1
            pygame.draw.rect(surface, black, label_rect.inflate(2, 0), 0)
            surface.blit(label, label_rect)
        self._debug_print(
            "NAVAIDS",
            f"loaded={len(navaids)} candidates={len(candidates)} budget={nav_budget} drawn={drawn_count} tacan={tacan_drawn} vor={vor_drawn}",
            min_interval_ms=1200,
        )

    def _draw_hsd_runways(
        self,
        surface: pygame.Surface,
        center: Tuple[int, int],
        range_nm: float,
        own_heading_deg: float,
        clamp_rect: Optional[pygame.Rect] = None,
    ) -> None:
        own = self._own_lat_lon()
        if own is None:
            return
        own_lat, own_lon = own
        runways = self._load_runways()
        if len(runways) <= 0:
            with self.__class__._runway_cache_lock:
                loading = bool(self.__class__._runway_cache_loading)
            self._debug_print(
                "RUNWAYS",
                "runway cache loading..." if loading else "runway cache empty",
                min_interval_ms=1200,
            )
            return

        outer_radius_px = float(4.0 * DPI)
        max_range_nm = max(0.001, float(range_nm))
        max_screen_radius_px = outer_radius_px
        if isinstance(clamp_rect, pygame.Rect) and clamp_rect.width > 0 and clamp_rect.height > 0:
            for sx, sy in (
                (clamp_rect.left, clamp_rect.top),
                (clamp_rect.right, clamp_rect.top),
                (clamp_rect.left, clamp_rect.bottom),
                (clamp_rect.right, clamp_rect.bottom),
            ):
                max_screen_radius_px = max(
                    max_screen_radius_px,
                    math.hypot(float(center[0] - sx), float(center[1] - sy)),
                )
        visible_range_nm = max_range_nm * (max_screen_radius_px / outer_radius_px) * 1.05
        lat_window_deg = max(0.05, visible_range_nm / 60.0)
        cos_lat = max(0.15, abs(math.cos(math.radians(float(own_lat)))))
        lon_window_deg = max(0.05, visible_range_nm / (60.0 * cos_lat))

        with self.__class__._runway_cache_lock:
            runway_index = self.__class__._runway_spatial_index
        candidate_runways: List[Dict[str, object]]
        if isinstance(runway_index, dict) and len(runway_index) > 0:
            lat_min_cell = int(math.floor(float(own_lat) - lat_window_deg)) - 1
            lat_max_cell = int(math.floor(float(own_lat) + lat_window_deg)) + 1
            lon_min_cell = int(math.floor(float(own_lon) - lon_window_deg)) - 1
            lon_max_cell = int(math.floor(float(own_lon) + lon_window_deg)) + 1
            candidate_runways = []
            for lat_cell in range(lat_min_cell, lat_max_cell + 1):
                for lon_cell in range(lon_min_cell, lon_max_cell + 1):
                    bucket = runway_index.get((lat_cell, lon_cell))
                    if isinstance(bucket, list) and len(bucket) > 0:
                        candidate_runways.extend(bucket)
        else:
            candidate_runways = runways

        red = (255, 0, 0)
        blue = (0, 160, 255)
        visible_count = 0
        drawn_count = 0
        prev_clip = surface.get_clip()
        if isinstance(clamp_rect, pygame.Rect) and clamp_rect.width > 0 and clamp_rect.height > 0:
            surface.set_clip(clamp_rect)
        try:
            for runway in candidate_runways:
                try:
                    mid_lat = float(runway.get("mid_lat"))
                    mid_lon = float(runway.get("mid_lon"))
                    length_ft = float(runway.get("length_ft", 0.0) or 0.0)
                except Exception:
                    continue
                if abs(mid_lat - float(own_lat)) > lat_window_deg or abs(mid_lon - float(own_lon)) > lon_window_deg:
                    continue
                _mid_bearing, mid_dist_nm = self._bearing_and_distance_nm(float(own_lat), float(own_lon), mid_lat, mid_lon)
                runway_half_nm = max(0.0, length_ft / 6076.12) * 0.5
                if mid_dist_nm > (visible_range_nm + runway_half_nm):
                    continue
                visible_count += 1

                try:
                    le_lat = float(runway.get("le_lat"))
                    le_lon = float(runway.get("le_lon"))
                    he_lat = float(runway.get("he_lat"))
                    he_lon = float(runway.get("he_lon"))
                except Exception:
                    continue
                le_bearing, le_dist_nm = self._bearing_and_distance_nm(float(own_lat), float(own_lon), le_lat, le_lon)
                he_bearing, he_dist_nm = self._bearing_and_distance_nm(float(own_lat), float(own_lon), he_lat, he_lon)
                le_rel = (float(le_bearing) - float(own_heading_deg)) % 360.0
                he_rel = (float(he_bearing) - float(own_heading_deg)) % 360.0
                le_radial = (float(le_dist_nm) / max_range_nm) * outer_radius_px
                he_radial = (float(he_dist_nm) / max_range_nm) * outer_radius_px
                p0 = self._polar_from_north(center, le_radial, le_rel)
                p1 = self._polar_from_north(center, he_radial, he_rel)
                color = blue if bool(runway.get("is_military", False)) else red
                pygame.draw.line(surface, color, p0, p1, 2)
                drawn_count += 1
        finally:
            surface.set_clip(prev_clip)
        self._debug_print(
            "RUNWAYS",
            f"loaded={len(runways)} candidates={len(candidate_runways)} visible={visible_count} drawn={drawn_count} range_nm={float(range_nm):.1f}",
            min_interval_ms=1200,
        )
    def _map_available_for_own_position(self) -> bool:
        own = self._own_lat_lon()
        if own is None:
            return False
        lat, lon = own
        return self._choose_map_for_point(lat, lon) is not None

    @classmethod
    def _resolve_map_tif_path(cls, maps_root: Path, entry: Dict[str, object]) -> Optional[Path]:
        raw_tif = str(entry.get("tif", "")).strip()
        if raw_tif != "":
            parts = [p for p in raw_tif.replace("\\", "/").split("/") if p.strip() != ""]
            if len(parts) >= 2 and parts[0].lower() == "assets" and parts[1].lower() == "maps":
                parts = parts[2:]
            candidate = maps_root.joinpath(*parts)
            if candidate.exists():
                return candidate

        raw_folder = str(entry.get("folder", "")).strip()
        if raw_folder != "":
            parts = [p for p in raw_folder.replace("\\", "/").split("/") if p.strip() != ""]
            if len(parts) >= 2 and parts[0].lower() == "assets" and parts[1].lower() == "maps":
                parts = parts[2:]
            folder = maps_root.joinpath(*parts)
            if folder.exists() and folder.is_dir():
                hits = sorted(folder.glob("*.tif"))
                if len(hits) > 0:
                    return hits[0]
                hits = sorted(folder.glob("*.tiff"))
                if len(hits) > 0:
                    return hits[0]

        map_name = str(entry.get("name", "")).strip()
        if map_name != "":
            folder = maps_root / map_name
            if folder.exists() and folder.is_dir():
                hits = sorted(folder.glob("*.tif"))
                if len(hits) > 0:
                    return hits[0]
                hits = sorted(folder.glob("*.tiff"))
                if len(hits) > 0:
                    return hits[0]
        return None

    @classmethod
    def _load_map_index(cls) -> List[Dict[str, object]]:
        if isinstance(cls._map_index_cache, list):
            return cls._map_index_cache
        cls._map_index_cache = []
        maps_root = Path(resource_path(Path("icons") / "MAPS"))
        idx_path = maps_root / "maps_index.json"
        if not idx_path.exists():
            return cls._map_index_cache
        try:
            import json
            raw = json.loads(idx_path.read_text(encoding="utf-8"))
        except Exception:
            return cls._map_index_cache
        if not isinstance(raw, list):
            return cls._map_index_cache

        for row in raw:
            if not isinstance(row, dict):
                continue
            bbox_raw = row.get("bbox")
            if not isinstance(bbox_raw, list) or len(bbox_raw) != 4:
                continue
            try:
                min_lon = float(bbox_raw[0])
                min_lat = float(bbox_raw[1])
                max_lon = float(bbox_raw[2])
                max_lat = float(bbox_raw[3])
            except Exception:
                continue
            if max_lon <= min_lon or max_lat <= min_lat:
                continue
            tif_path = cls._resolve_map_tif_path(maps_root, row)
            if tif_path is None:
                continue
            cls._map_index_cache.append(
                {
                    "name": str(row.get("name", "")).strip() or tif_path.stem,
                    "path": str(tif_path),
                    "bbox": (min_lon, min_lat, max_lon, max_lat),
                }
            )
        return cls._map_index_cache

    @classmethod
    def _choose_map_for_point(cls, lat: float, lon: float) -> Optional[Dict[str, object]]:
        entries = cls._load_map_index()
        if len(entries) <= 0:
            return None

        inside_best: Optional[Dict[str, object]] = None
        inside_area = float("inf")
        for entry in entries:
            bbox = entry.get("bbox")
            if not isinstance(bbox, tuple) or len(bbox) != 4:
                continue
            min_lon, min_lat, max_lon, max_lat = bbox
            if not (min_lon <= lon <= max_lon and min_lat <= lat <= max_lat):
                continue
            area = (max_lon - min_lon) * (max_lat - min_lat)
            if area < inside_area:
                inside_area = area
                inside_best = entry
        if inside_best is not None:
            return inside_best

        # Fallback: nearest map center in simple lat/lon space.
        cos_lat = max(0.2, abs(math.cos(math.radians(float(lat)))))
        nearest: Optional[Dict[str, object]] = None
        nearest_d2 = float("inf")
        for entry in entries:
            bbox = entry.get("bbox")
            if not isinstance(bbox, tuple) or len(bbox) != 4:
                continue
            min_lon, min_lat, max_lon, max_lat = bbox
            c_lon = (min_lon + max_lon) * 0.5
            c_lat = (min_lat + max_lat) * 0.5
            dx = (lon - c_lon) * cos_lat
            dy = lat - c_lat
            d2 = dx * dx + dy * dy
            if d2 < nearest_d2:
                nearest_d2 = d2
                nearest = entry
        return nearest

    @classmethod
    def _open_map_image(cls, map_path: str) -> Optional[object]:
        if Image is None:
            return None
        key = str(map_path)
        cached = cls._map_image_cache.get(key)
        if cached is not None:
            return cached
        try:
            img = Image.open(key)
        except Exception:
            return None
        cls._map_image_cache[key] = img
        # Keep only a tiny cache; these TIFFs are very large.
        while len(cls._map_image_cache) > 2:
            old_key = next(iter(cls._map_image_cache.keys()))
            old_img = cls._map_image_cache.pop(old_key, None)
            try:
                if old_img is not None and hasattr(old_img, "close"):
                    old_img.close()
            except Exception:
                pass
        return img

    @staticmethod
    def _latlon_to_map_px(
        lat: float,
        lon: float,
        bbox: Tuple[float, float, float, float],
        width: int,
        height: int,
    ) -> Tuple[float, float]:
        min_lon, min_lat, max_lon, max_lat = bbox
        lon_span = max(1e-9, float(max_lon - min_lon))
        lat_span = max(1e-9, float(max_lat - min_lat))
        u = (float(lon) - min_lon) / lon_span
        v = (max_lat - float(lat)) / lat_span
        x = u * float(max(1, width - 1))
        y = v * float(max(1, height - 1))
        return x, y

    @classmethod
    def _hsd_map_patch(
        cls,
        map_entry: Dict[str, object],
        lat: float,
        lon: float,
        range_nm: float,
        diameter_px: int,
    ) -> Optional[pygame.Surface]:
        if Image is None:
            return None
        path = str(map_entry.get("path", "")).strip()
        bbox = map_entry.get("bbox")
        if path == "" or not isinstance(bbox, tuple) or len(bbox) != 4:
            return None

        key = (
            path,
            int(round(float(lat) * 1000.0)),
            int(round(float(lon) * 1000.0)),
            int(round(float(range_nm) * 5.0)),
            max(2, int(diameter_px)),
        )
        cached = cls._map_patch_cache.get(key)
        if cached is not None:
            return cached

        img = cls._open_map_image(path)
        if img is None:
            return None

        try:
            width, height = img.size
        except Exception:
            return None
        if width <= 1 or height <= 1:
            return None

        center_x, center_y = cls._latlon_to_map_px(float(lat), float(lon), bbox, int(width), int(height))
        min_lon, min_lat, max_lon, max_lat = bbox
        lon_span = max(1e-9, float(max_lon - min_lon))
        lat_span = max(1e-9, float(max_lat - min_lat))
        px_per_deg_x = float(max(1, width - 1)) / lon_span
        px_per_deg_y = float(max(1, height - 1)) / lat_span
        half_lat_deg = max(0.001, float(range_nm) / 60.0)
        cos_lat = max(0.15, abs(math.cos(math.radians(float(lat)))))
        half_lon_deg = max(0.001, float(range_nm) / (60.0 * cos_lat))
        half_w_px = max(2.0, half_lon_deg * px_per_deg_x)
        half_h_px = max(2.0, half_lat_deg * px_per_deg_y)

        left = int(math.floor(center_x - half_w_px))
        right = int(math.ceil(center_x + half_w_px))
        top = int(math.floor(center_y - half_h_px))
        bottom = int(math.ceil(center_y + half_h_px))
        if right <= left:
            right = left + 1
        if bottom <= top:
            bottom = top + 1

        try:
            crop = img.crop((left, top, right, bottom))
            resample = Image.Resampling.BILINEAR if hasattr(Image, "Resampling") else Image.BILINEAR
            crop = crop.resize((max(2, int(diameter_px)), max(2, int(diameter_px))), resample=resample)
            crop = crop.convert("RGB")
            raw = crop.tobytes()
            surf = pygame.image.fromstring(raw, crop.size, "RGB").convert()
        except Exception:
            return None

        # Keep map readable under symbology without losing color.
        # Requested: render map at 50% brightness.
        surf.fill((128, 128, 128), special_flags=pygame.BLEND_RGB_MULT)
        surf = surf.convert_alpha()
        surf.set_alpha(255)

        cls._map_patch_cache[key] = surf
        while len(cls._map_patch_cache) > 48:
            old_key = next(iter(cls._map_patch_cache.keys()))
            cls._map_patch_cache.pop(old_key, None)
        return surf

    def _draw_hsd_map(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        center: Tuple[int, int],
        range_nm: float,
        heading_deg: float,
        zoom_scale: float = 1.0,
    ) -> None:
        if not bool(self._state().get("map_on", False)):
            return
        if rect.width <= 0 or rect.height <= 0:
            return
        own = self._own_lat_lon()
        if own is None:
            return
        own_lat, own_lon = own

        # Sampling must account for panning and heading:
        # derive the sampled center from ownship lat/lon plus current pan offset.
        live_center = (float(center[0]), float(center[1]))
        ref_center = (
            float(rect.centerx),
            float(rect.centery + int(round(0.875 * DPI))),
        )
        pan_dx_px = float(live_center[0] - ref_center[0])
        pan_dy_px = float(live_center[1] - ref_center[1])
        nm_per_px = max(1e-6, float(range_nm) / float(4.0 * DPI))
        pan_dist_nm = math.hypot(pan_dx_px, pan_dy_px) * nm_per_px
        if pan_dist_nm > 1e-6:
            pan_rel_bearing_deg = (math.degrees(math.atan2(pan_dx_px, -pan_dy_px)) + 360.0) % 360.0
            pan_world_bearing_deg = (float(heading_deg) + pan_rel_bearing_deg) % 360.0
            lat, lon = self._project_lat_lon_nm(own_lat, own_lon, pan_world_bearing_deg, pan_dist_nm)
        else:
            lat, lon = own_lat, own_lon

        map_entry = self._choose_map_for_point(lat, lon)
        if map_entry is None:
            map_entry = self._choose_map_for_point(own_lat, own_lon)
            lat, lon = own_lat, own_lon
            if map_entry is None:
                self._debug_print("MAP", "no map entry for ownship position", min_interval_ms=1500)
                return

        # Expand sampled range so the map stays valid across the full visible rect.
        corners = [
            (rect.left, rect.top),
            (rect.right, rect.top),
            (rect.left, rect.bottom),
            (rect.right, rect.bottom),
        ]
        max_corner_dist = 0.0
        for cx, cy in corners:
            d = math.hypot(float(live_center[0] - cx), float(live_center[1] - cy))
            if d > max_corner_dist:
                max_corner_dist = d
        sample_range_nm = max(0.01, float(max_corner_dist) * nm_per_px)

        raw_diameter = max(2, int(math.ceil(max_corner_dist * 2.0)) + 8)
        diameter = int(math.ceil(float(raw_diameter) / 32.0) * 32.0)
        diameter = max(64, min(2048, diameter))

        base = self._hsd_map_patch(map_entry, lat, lon, sample_range_nm, diameter)
        if base is None:
            map_name = str(map_entry.get("name", "UNKNOWN")) if isinstance(map_entry, dict) else "UNKNOWN"
            self._debug_print(
                "MAP",
                f"map={map_name} patch build failed (diameter={diameter}, sample_range_nm={sample_range_nm:.2f})",
                min_interval_ms=1500,
            )
            return

        # Counter-rotate map against own heading for heading-up presentation.
        # Zoom is applied via sampled range_nm to avoid huge runtime scale surfaces.
        rot = pygame.transform.rotozoom(base, float(heading_deg), 1.0)
        map_name = str(map_entry.get("name", "UNKNOWN")) if isinstance(map_entry, dict) else "UNKNOWN"
        self._debug_print(
            "MAP",
            f"map={map_name} center=({lat:.4f},{lon:.4f}) sample_range_nm={sample_range_nm:.2f} diameter={diameter} patch_cache={len(self._map_patch_cache)}",
            min_interval_ms=1500,
        )

        prev_clip = surface.get_clip()
        surface.set_clip(rect)
        dst = rot.get_rect(center=center)
        surface.blit(rot, dst)
        surface.set_clip(prev_clip)

    @staticmethod
    def _normalize_contact_affiliation(raw: object, row: Dict[str, object]) -> str:
        if bool(row.get("enemy")) or bool(row.get("hostile")):
            return "ENEMY"
        if bool(row.get("friendly")) or bool(row.get("friend")):
            return "FRIENDLY"
        text = str(raw).upper().strip()
        if text in {"FRIENDLY", "FRIEND", "ALLY", "OWN", "BLUE"}:
            return "FRIENDLY"
        if text in {"ENEMY", "HOSTILE", "FOE", "RED", "BANDIT"}:
            return "ENEMY"
        if "FRIEND" in text or "ALLY" in text or "BLUE" in text:
            return "FRIENDLY"
        if "ENEMY" in text or "HOSTILE" in text or "FOE" in text or "BANDIT" in text or "RED" in text:
            return "ENEMY"
        return "UNKNOWN"

    @staticmethod
    def _normalize_contact_domain(row: Dict[str, object]) -> str:
        for key in ("on_ground", "gnd", "ground", "is_ground", "grounded"):
            if bool(row.get(key)):
                return "GROUND"
        alt = Tsd1Format._safe_float(row.get("alt_baro"))
        if alt is None:
            alt = Tsd1Format._safe_float(row.get("alt_geom"))
        if alt is None:
            alt = Tsd1Format._safe_float(row.get("altitude"))
        if alt is not None and alt <= 0.0:
            return "GROUND"
        return "AIR"

    @staticmethod
    def _mil_match_sets(mil_payload: object) -> Tuple[set, set]:
        mil_hex: set = set()
        mil_flight: set = set()
        if not isinstance(mil_payload, dict):
            return mil_hex, mil_flight
        rows = mil_payload.get("ac")
        if not isinstance(rows, list):
            rows = mil_payload.get("aircraft")
        if not isinstance(rows, list):
            return mil_hex, mil_flight
        for row in rows:
            if not isinstance(row, dict):
                continue
            hx = ""
            for key in ("hex", "icao", "icao24", "id"):
                candidate = str(row.get(key, "")).strip().upper()
                if candidate != "":
                    hx = candidate
                    break
            if hx != "":
                mil_hex.add(hx)
            flt = ""
            for key in ("flight", "callsign", "r"):
                candidate = str(row.get(key, "")).strip().upper()
                if candidate != "":
                    flt = candidate
                    break
            if flt != "":
                mil_flight.add(flt.replace(" ", ""))
        return mil_hex, mil_flight

    @staticmethod
    def _adsb_contacts(raw_payload: object, mil_payload: object = None) -> List[Dict[str, object]]:
        contacts: List[Dict[str, object]] = []
        if not isinstance(raw_payload, dict):
            return contacts
        mil_hex_set, mil_flight_set = Tsd1Format._mil_match_sets(mil_payload)
        rows = raw_payload.get("ac")
        if not isinstance(rows, list):
            rows = raw_payload.get("aircraft")
        if not isinstance(rows, list):
            return contacts
        for idx, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            lat = Tsd1Format._safe_float(row.get("lat"))
            lon = Tsd1Format._safe_float(row.get("lon"))
            if lat is None or lon is None:
                lat = Tsd1Format._safe_float(row.get("latitude"))
                lon = Tsd1Format._safe_float(row.get("longitude"))
            if lat is None or lon is None:
                continue
            heading = Tsd1Format._safe_float(row.get("track"))
            if heading is None:
                for key in ("true_heading", "heading", "nav_heading", "hdg"):
                    heading = Tsd1Format._safe_float(row.get(key))
                    if heading is not None:
                        break
            speed_kts = Tsd1Format._safe_float(row.get("gs"))
            if speed_kts is None:
                for key in ("groundspeed", "speed", "spd", "velocity"):
                    speed_kts = Tsd1Format._safe_float(row.get(key))
                    if speed_kts is not None:
                        break
            if speed_kts is None:
                speed_kts = 0.0
            speed_kts = max(0.0, float(speed_kts))
            cid = ""
            contact_hex = ""
            for key in ("hex", "icao", "icao24", "id", "flight", "callsign"):
                raw_id = str(row.get(key, "")).strip().upper()
                if raw_id != "":
                    cid = raw_id
                    break
            for key in ("hex", "icao", "icao24", "id"):
                raw_hex = str(row.get(key, "")).strip().upper()
                if raw_hex != "":
                    contact_hex = raw_hex
                    break
            contact_flight = ""
            for key in ("flight", "callsign", "r"):
                raw_flight = str(row.get(key, "")).strip().upper()
                if raw_flight != "":
                    contact_flight = raw_flight
                    break
            contact_flight_key = contact_flight.replace(" ", "")
            if cid == "":
                cid = f"ROW_{idx}"
            domain = Tsd1Format._normalize_contact_domain(row)
            category = ""
            for key in ("category", "cat", "ac_category", "emitter_category"):
                raw_cat = str(row.get(key, "")).strip().upper()
                if raw_cat == "":
                    continue
                raw_cat = raw_cat.replace(" ", "")
                m = re.match(r"^([AB])[ _-]?([1-6])$", raw_cat)
                if m is not None:
                    category = f"{m.group(1)}{m.group(2)}"
                    break
                if re.match(r"^[AB][1-6]$", raw_cat):
                    category = raw_cat
                    break
            # Requested behavior:
            # - <10 kts is always UNKNOWN GROUND.
            # - Otherwise force deterministic 10% ENEMY, 10% FRIENDLY, 80% UNKNOWN.
            if speed_kts < 10.0:
                affiliation = "UNKNOWN"
                domain = "GROUND"
            else:
                is_military_friendly = False
                if contact_hex != "" and contact_hex in mil_hex_set:
                    is_military_friendly = True
                elif contact_flight_key != "" and contact_flight_key in mil_flight_set:
                    is_military_friendly = True
                if is_military_friendly:
                    affiliation = "FRIENDLY"
                else:
                    sig = 0
                    for i, ch in enumerate(cid):
                        sig += (i + 1) * ord(ch)
                    bucket = sig % 10
                    if bucket == 0:
                        affiliation = "ENEMY"
                    elif bucket == 1:
                        affiliation = "FRIENDLY"
                    else:
                        affiliation = "UNKNOWN"
            contacts.append(
                {
                    "id": cid,
                    "hex": contact_hex,
                    "flight": contact_flight,
                    "lat": lat,
                    "lon": lon,
                    "heading": heading,
                    "speed_kts": speed_kts,
                    "affiliation": affiliation,
                    "domain": domain,
                    "category": category,
                    "raw_row": dict(row),
                }
            )
        return contacts

    @staticmethod
    def _bearing_and_distance_nm(
        own_lat_deg: float,
        own_lon_deg: float,
        contact_lat_deg: float,
        contact_lon_deg: float,
    ) -> Tuple[float, float]:
        own_lat = math.radians(float(own_lat_deg))
        own_lon = math.radians(float(own_lon_deg))
        tgt_lat = math.radians(float(contact_lat_deg))
        tgt_lon = math.radians(float(contact_lon_deg))
        d_lat = tgt_lat - own_lat
        d_lon = tgt_lon - own_lon

        sin_dlat = math.sin(d_lat * 0.5)
        sin_dlon = math.sin(d_lon * 0.5)
        a = sin_dlat * sin_dlat + math.cos(own_lat) * math.cos(tgt_lat) * sin_dlon * sin_dlon
        c = 2.0 * math.atan2(math.sqrt(max(0.0, a)), math.sqrt(max(0.0, 1.0 - a)))
        km = 6371.0088 * c
        nm = km * 0.5399568

        y = math.sin(d_lon) * math.cos(tgt_lat)
        x = math.cos(own_lat) * math.sin(tgt_lat) - math.sin(own_lat) * math.cos(tgt_lat) * math.cos(d_lon)
        bearing = (math.degrees(math.atan2(y, x)) + 360.0) % 360.0
        return bearing, nm

    @staticmethod
    def _project_lat_lon_nm(
        lat_deg: float,
        lon_deg: float,
        heading_deg: float,
        distance_nm: float,
    ) -> Tuple[float, float]:
        if distance_nm <= 0.0:
            return float(lat_deg), float(lon_deg)
        radius_km = 6371.0088
        dist_km = float(distance_nm) * 1.852
        angular = dist_km / radius_km
        lat1 = math.radians(float(lat_deg))
        lon1 = math.radians(float(lon_deg))
        brg = math.radians(float(heading_deg) % 360.0)

        sin_lat2 = math.sin(lat1) * math.cos(angular) + math.cos(lat1) * math.sin(angular) * math.cos(brg)
        lat2 = math.asin(max(-1.0, min(1.0, sin_lat2)))
        lon2 = lon1 + math.atan2(
            math.sin(brg) * math.sin(angular) * math.cos(lat1),
            math.cos(angular) - math.sin(lat1) * math.sin(lat2),
        )
        lon2 = (lon2 + math.pi) % (2.0 * math.pi) - math.pi
        return math.degrees(lat2), math.degrees(lon2)

    @classmethod
    def _load_tsd_svg_icon(cls, filename: str, size_px: int) -> Optional[pygame.Surface]:
        name = str(filename).strip()
        if not name.lower().endswith(".svg"):
            name = f"{name}.svg"
        key = (name.upper(), max(1, int(size_px)))
        cached = cls._tsd_svg_cache.get(key)
        if cached is not None or key in cls._tsd_svg_cache:
            return cached
        path = Path(resource_path(Path("icons") / "TSD" / name))
        loaded: Optional[pygame.Surface] = None
        if path.exists():
            try:
                raw = pygame.image.load(str(path)).convert_alpha()
                loaded = pygame.transform.smoothscale(raw, (key[1], key[1]))
            except Exception:
                loaded = None
        cls._tsd_svg_cache[key] = loaded
        return loaded

    @staticmethod
    def _tint_surface_color(src: pygame.Surface, rgb: Tuple[int, int, int]) -> pygame.Surface:
        out = src.copy()
        out.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
        out.fill((int(rgb[0]), int(rgb[1]), int(rgb[2]), 0), special_flags=pygame.BLEND_RGBA_ADD)
        return out

    @staticmethod
    def _outline_only_from_alpha(src: pygame.Surface, edge_width: int = 1) -> pygame.Surface:
        w, h = src.get_size()
        out = pygame.Surface((w, h), pygame.SRCALPHA)
        out.fill((0, 0, 0, 0))
        ew = max(1, int(edge_width))
        try:
            mask = pygame.mask.from_surface(src, 1)
            points = mask.outline()
            if len(points) >= 2:
                pygame.draw.lines(out, (255, 255, 255, 255), True, points, ew)
                return out
        except Exception:
            pass
        return out

    @staticmethod
    def _outer_border_from_alpha(
        src: pygame.Surface,
        color: Tuple[int, int, int],
        thickness: int = 1,
    ) -> pygame.Surface:
        w, h = src.get_size()
        out = pygame.Surface((w, h), pygame.SRCALPHA)
        out.fill((0, 0, 0, 0))
        t = max(1, int(thickness))
        try:
            core = pygame.mask.from_surface(src, 1)
            expanded = core.copy()
            for dy in range(-t, t + 1):
                for dx in range(-t, t + 1):
                    if dx == 0 and dy == 0:
                        continue
                    expanded.draw(core, (dx, dy))
            border = expanded.copy()
            border.erase(core, (0, 0))
            out = border.to_surface(
                setcolor=(int(color[0]), int(color[1]), int(color[2]), 255),
                unsetcolor=(0, 0, 0, 0),
            )
        except Exception:
            pass
        return out

    @staticmethod
    def _cache_set_limited(cache: Dict[Tuple[object, ...], object], key: Tuple[object, ...], value: object, limit: int) -> None:
        if key in cache:
            cache[key] = value
            return
        cache[key] = value
        while len(cache) > max(1, int(limit)):
            try:
                oldest = next(iter(cache))
            except Exception:
                break
            if oldest == key and len(cache) <= 1:
                break
            cache.pop(oldest, None)

    @staticmethod
    def _normalize_track_affiliation(raw: object) -> str:
        text = str(raw or "").upper().strip()
        if text in {"FRIENDLY", "FRIEND", "ALLY", "OWN", "BLUE"}:
            return "FRIEND"
        if text in {"ENEMY", "HOSTILE", "FOE", "RED", "BANDIT"}:
            return "FOE"
        if text in {"SUSPECT", "YELLOW", "AMBIGUOUS"}:
            return "SUSPECT"
        if text in {"NEUTRAL", "MAGENTA", "CIVIL", "CIV"}:
            return "NEUTRAL"
        return "UNKNOWN"

    @staticmethod
    def _track_color_for_affiliation(aff: str) -> Tuple[int, int, int]:
        token = Tsd1Format._normalize_track_affiliation(aff)
        if token == "FRIEND":
            return (0, 255, 0)
        if token == "SUSPECT":
            return (255, 255, 0)
        if token == "FOE":
            return (255, 0, 0)
        if token == "NEUTRAL":
            return (255, 0, 255)
        return (255, 255, 255)

    @staticmethod
    def _track_quality_level(contact: Dict[str, object]) -> int:
        raw_row = contact.get("raw_row")
        row = raw_row if isinstance(raw_row, dict) else {}
        candidates: List[object] = [
            contact.get("track_quality"),
            contact.get("quality"),
            contact.get("quality_level"),
            contact.get("trk_quality"),
            row.get("track_quality"),
            row.get("quality"),
            row.get("quality_level"),
            row.get("trk_quality"),
        ]
        for value in candidates:
            if value is None:
                continue
            if isinstance(value, bool):
                return 2 if bool(value) else 0
            if isinstance(value, (int, float)):
                try:
                    f = float(value)
                except Exception:
                    continue
                if f <= 0.0:
                    return 0
                if f <= 1.0:
                    return 1
                return 2
            text = str(value).upper().strip()
            if text == "":
                continue
            if any(tag in text for tag in ("NONE", "FAIL", "LOW", "BAD", "NOFILL", "NO FILL")):
                return 0
            if any(tag in text for tag in ("HALF", "PART", "MED")):
                return 1
            if any(tag in text for tag in ("FULL", "GOOD", "HIGH", "MEET", "PASS")):
                return 2
            if text in {"0", "1", "2"}:
                return max(0, min(2, int(text)))
        # Default to no fill when track-quality metadata is absent.
        return 0

    @staticmethod
    def _track_is_emitting(contact: Dict[str, object]) -> bool:
        raw_row = contact.get("raw_row")
        row = raw_row if isinstance(raw_row, dict) else {}
        keys = (
            "emitting",
            "is_emitting",
            "radar_on",
            "radar_emitting",
            "jamming",
            "jammer",
            "ew",
            "ew_active",
            "emit",
        )
        for key in keys:
            if bool(contact.get(key)) or bool(row.get(key)):
                return True
        text_fields = (
            str(contact.get("emitter", "")),
            str(contact.get("sensor_state", "")),
            str(row.get("emitter", "")),
            str(row.get("sensor_state", "")),
        )
        blob = " ".join(text_fields).upper()
        return any(tag in blob for tag in ("EMIT", "EW", "JAM", "RADAR"))

    @staticmethod
    def _draw_track_main_fill(
        target: pygame.Surface,
        shape: str,
        color: Tuple[int, int, int],
        fill_level: int,
    ) -> None:
        if fill_level <= 0:
            return
        px = target.get_width()
        clip = pygame.Rect(0, 0, px, px)
        if fill_level == 1:
            clip = pygame.Rect(0, px // 2, px, px - (px // 2))
        prev_clip = target.get_clip()
        target.set_clip(clip)
        if shape == "CIRCLE":
            pygame.draw.circle(target, color, (px // 2, px // 2), int(round(px * 0.262)), 0)
        elif shape == "SQUARE":
            x0 = int(round(px * 0.236))
            y0 = int(round(px * 0.236))
            w = int(round(px * 0.524))
            pygame.draw.rect(target, color, pygame.Rect(x0, y0, w, w), 0)
        elif shape == "DIAMOND":
            pts = [
                (int(round(px * 0.498)), int(round(px * 0.236))),
                (int(round(px * 0.235)), int(round(px * 0.501))),
                (int(round(px * 0.498)), int(round(px * 0.766))),
                (int(round(px * 0.763)), int(round(px * 0.501))),
            ]
            pygame.draw.polygon(target, color, pts, 0)
        else:  # TRIANGLE
            pts = [
                (int(round(px * 0.272)), int(round(px * 0.616))),
                (int(round(px * 0.720)), int(round(px * 0.616))),
                (int(round(px * 0.500)), int(round(px * 0.232))),
            ]
            pygame.draw.polygon(target, color, pts, 0)
        target.set_clip(prev_clip)

    @classmethod
    def _compose_track_symbol(
        cls,
        affiliation: str,
        domain: str,
        size_px: int,
        quality_level: int,
        moving: bool,
        emitting: bool,
    ) -> Optional[pygame.Surface]:
        aff = cls._normalize_track_affiliation(affiliation)
        dom = str(domain).upper().strip()
        if dom not in {"AIR", "GROUND"}:
            dom = "AIR"
        main_shape = "TRIANGLE" if dom == "GROUND" else "SQUARE"
        if dom == "AIR" and aff == "FRIEND":
            main_shape = "CIRCLE"
        elif dom == "AIR" and aff == "FOE":
            main_shape = "DIAMOND"
        color = cls._track_color_for_affiliation(aff)
        px = max(1, int(size_px))

        canvas = pygame.Surface((px, px), pygame.SRCALPHA)
        canvas.fill((0, 0, 0, 0))

        fill_level = max(0, min(2, int(quality_level)))
        cls._draw_track_main_fill(canvas, main_shape, color, fill_level)

        main_outline = cls._load_tsd_svg_icon(f"{main_shape}.svg", px)
        if main_outline is None:
            return None
        outline_only = cls._outline_only_from_alpha(main_outline, edge_width=max(1, int(round(px / 40.0))))
        canvas.blit(cls._tint_surface_color(outline_only, color), (0, 0))

        if bool(emitting):
            half_circle = cls._load_tsd_svg_icon("HALF CIRCLE.svg", px)
            if half_circle is not None:
                half_circle_outline = cls._outline_only_from_alpha(
                    half_circle,
                    edge_width=max(1, int(round(px / 40.0))),
                )
                canvas.blit(cls._tint_surface_color(half_circle_outline, color), (0, 0))

        if bool(moving):
            line = cls._load_tsd_svg_icon("LINE.svg", px)
            if line is not None:
                line_outline = cls._outline_only_from_alpha(
                    line,
                    edge_width=max(1, int(round(px / 40.0))),
                )
                canvas.blit(cls._tint_surface_color(line_outline, color), (0, 0))

        # Add a 1px outer border around the full icon (main shape + extras),
        # using the same affiliation color as the icon.
        full_outline = cls._outer_border_from_alpha(canvas, color, thickness=1)
        canvas.blit(full_outline, (0, 0))

        return canvas

    @classmethod
    def _get_adsb_contact_icon(
        cls,
        affiliation: str,
        domain: str,
        size_px: int,
        heading_deg: float,
        quality_level: int = 0,
        moving: bool = True,
        emitting: bool = False,
        build_if_missing: bool = True,
    ) -> Optional[pygame.Surface]:
        aff = cls._normalize_track_affiliation(affiliation)
        dom = str(domain).upper().strip()
        if dom not in {"AIR", "GROUND"}:
            dom = "AIR"
        px = max(1, int(size_px))
        # Quantize heading to reduce cache churn and frame hitches on TSD open.
        hdg_raw = int(round(float(heading_deg))) % 360
        hdg = int(round(hdg_raw / 15.0) * 15) % 360
        qlvl = max(0, min(2, int(quality_level)))
        base_key: Tuple[object, ...] = ("TRACK_BASE_V4", aff, dom, px, qlvl, int(bool(moving)), int(bool(emitting)))
        base = cls._track_symbol_base_cache.get(base_key)
        if base is None and base_key not in cls._track_symbol_base_cache:
            if not bool(build_if_missing):
                return None
            base = cls._compose_track_symbol(
                aff,
                dom,
                px,
                qlvl,
                bool(moving),
                bool(emitting),
            )
            cls._cache_set_limited(cls._track_symbol_base_cache, base_key, base, 512)
        if base is None:
            return None

        cache_key: Tuple[object, ...] = ("TRACK_ROT_V4", aff, dom, px, hdg, qlvl, int(bool(moving)), int(bool(emitting)))
        cached = cls._adsb_icon_rot_cache.get(cache_key)
        if cached is not None:
            return cached
        if not bool(build_if_missing):
            return None
        icon = pygame.transform.rotozoom(base, -float(hdg), 1.0)
        if icon is None:
            return None
        cls._cache_set_limited(cls._adsb_icon_rot_cache, cache_key, icon, 4096)
        return icon

    @classmethod
    def _enqueue_track_icon_load_job(
        cls,
        state: Dict[str, object],
        affiliation: str,
        domain: str,
        size_px: int,
        heading_deg: float,
        quality_level: int,
        moving: bool,
        emitting: bool,
    ) -> None:
        aff = cls._normalize_track_affiliation(affiliation)
        dom = str(domain).upper().strip()
        if dom not in {"AIR", "GROUND"}:
            dom = "AIR"
        px = max(1, int(size_px))
        qlvl = max(0, min(2, int(quality_level)))
        hdg_raw = int(round(float(heading_deg))) % 360
        hdg = int(round(hdg_raw / 15.0) * 15) % 360
        mov_i = int(bool(moving))
        emit_i = int(bool(emitting))
        cache_key: Tuple[object, ...] = ("TRACK_ROT_V4", aff, dom, px, hdg, qlvl, mov_i, emit_i)
        if cache_key in cls._adsb_icon_rot_cache:
            return

        raw_queue = state.get("_tsd_track_icon_load_queue")
        queue: deque = raw_queue if isinstance(raw_queue, deque) else deque()
        raw_set = state.get("_tsd_track_icon_load_set")
        queued_set: Set[Tuple[object, ...]] = raw_set if isinstance(raw_set, set) else set()

        if cache_key in queued_set:
            state["_tsd_track_icon_load_queue"] = queue
            state["_tsd_track_icon_load_set"] = queued_set
            return

        queue.append((aff, dom, px, hdg, qlvl, mov_i, emit_i))
        queued_set.add(cache_key)
        state["_tsd_track_icon_load_queue"] = queue
        state["_tsd_track_icon_load_set"] = queued_set

    @classmethod
    def _service_track_icon_load_jobs(
        cls,
        state: Dict[str, object],
        max_jobs: int = 2,
        max_ms: float = 2.0,
        debug_label: str = "TSD",
    ) -> None:
        raw_queue = state.get("_tsd_track_icon_load_queue")
        queue: deque = raw_queue if isinstance(raw_queue, deque) else deque()
        raw_set = state.get("_tsd_track_icon_load_set")
        queued_set: Set[Tuple[object, ...]] = raw_set if isinstance(raw_set, set) else set()
        if len(queue) <= 0:
            state["_tsd_track_icon_load_queue"] = queue
            state["_tsd_track_icon_load_set"] = queued_set
            return

        jobs = max(1, int(max_jobs))
        deadline = time.perf_counter() + max(0.0005, float(max_ms) / 1000.0)
        processed = 0
        while jobs > 0 and len(queue) > 0:
            aff, dom, px, hdg, qlvl, mov_i, emit_i = queue.popleft()
            key = ("TRACK_ROT_V4", aff, dom, px, hdg, qlvl, int(bool(mov_i)), int(bool(emit_i)))
            queued_set.discard(key)
            cls._get_adsb_contact_icon(
                str(aff),
                str(dom),
                int(px),
                float(hdg),
                quality_level=int(qlvl),
                moving=bool(mov_i),
                emitting=bool(emit_i),
                build_if_missing=True,
            )
            jobs -= 1
            processed += 1
            if time.perf_counter() >= deadline:
                break

        state["_tsd_track_icon_load_queue"] = queue
        state["_tsd_track_icon_load_set"] = queued_set
        cls._debug_print_for_state(
            state,
            debug_label,
            "ICON_BUILD",
            f"processed={processed} remaining={len(queue)} rot_cache={len(cls._adsb_icon_rot_cache)}",
            min_interval_ms=500,
            force=bool(processed > 0),
        )

    def _draw_hsd_adsb_contacts(
        self,
        surface: pygame.Surface,
        center: Tuple[int, int],
        range_nm: float,
        clamp_rect: Optional[pygame.Rect] = None,
    ) -> List[Dict[str, object]]:
        rendered_items: List[Dict[str, object]] = []
        snap = TSD_ADSB_STATE if isinstance(TSD_ADSB_STATE, dict) else {}
        link16_raw = TSD_LINK16_CONTACTS if isinstance(TSD_LINK16_CONTACTS, list) else []
        sim_live = TSD_SIM_CONTACTS if isinstance(TSD_SIM_CONTACTS, list) else []
        show_link16 = len(link16_raw) > 0
        show_sim_live = len(sim_live) > 0
        adsb_enabled = bool(snap.get("enabled", False))
        adsb_visible = bool(snap.get("show_live_adsb", True))
        if (not adsb_enabled or not adsb_visible) and (not show_link16) and (not show_sim_live):
            return rendered_items

        own_lat = self._safe_float(snap.get("lat"))
        own_lon = self._safe_float(snap.get("lon"))
        if own_lat is None or own_lon is None:
            geo = snap.get("geo")
            if isinstance(geo, dict):
                own_lat = self._safe_float(geo.get("lat"))
                own_lon = self._safe_float(geo.get("lon"))
        if own_lat is None or own_lon is None:
            return rendered_items

        dclt_state = self._ensure_dclt_state()
        contacts: List[Dict[str, object]] = []
        if adsb_enabled and adsb_visible:
            raw_payload = snap.get("raw")
            mil_payload = snap.get("mil_raw")
            last_update_key = self._safe_float(snap.get("last_update_time"))
            sim_tick_key = 0
            try:
                sim_tick_key = int(getattr(sys.modules.get(__name__), "PMD_SIM_TARGETS_TICK", 0) or 0)
            except Exception:
                sim_tick_key = 0
            cache_key = (
                id(raw_payload),
                id(mil_payload),
                float(last_update_key) if last_update_key is not None else 0.0,
                int(sim_tick_key),
            )
            cached_key = dclt_state.get("_tsd_adsb_contacts_cache_key")
            cached_contacts = dclt_state.get("_tsd_adsb_contacts_cache")
            if (
                isinstance(cached_contacts, list)
                and isinstance(cached_key, tuple)
                and cached_key == cache_key
            ):
                contacts.extend(cached_contacts)
            else:
                parsed = self._adsb_contacts(raw_payload, mil_payload=mil_payload)
                dclt_state["_tsd_adsb_contacts_cache_key"] = cache_key
                dclt_state["_tsd_adsb_contacts_cache"] = parsed
                contacts.extend(parsed)
        if isinstance(link16_raw, list):
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
                        "domain": str(item.get("domain", "AIR")).upper().strip() or "AIR",
                        "category": str(item.get("category", "B1")).upper().strip() or "B1",
                        "_link16": True,
                        "_sim": bool(item.get("_sim", False)),
                    }
                )
        # Direct local PMD sim-target feed (live every frame). This bypasses
        # ADS-B fetch cadence so simulated targets are not throttled.
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
                    "domain": str(item.get("domain", "AIR")).upper().strip() or "AIR",
                    "category": str(item.get("category", "B1")).upper().strip() or "B1",
                    "_plugin_sim": True,
                    "_sim": True,
                }
            )
        # Deduplicate by contact id, preferring simulated/local variants.
        if len(contacts) > 1:
            dedup: Dict[str, Dict[str, object]] = {}
            for c in contacts:
                if not isinstance(c, dict):
                    continue
                cid = str(c.get("id", "")).strip()
                if cid == "":
                    continue
                prev = dedup.get(cid)
                if prev is None:
                    dedup[cid] = c
                    continue
                prev_sim = bool(prev.get("_plugin_sim", False) or prev.get("_sim", False))
                cur_sim = bool(c.get("_plugin_sim", False) or c.get("_sim", False))
                if cur_sim and (not prev_sim):
                    dedup[cid] = c
            contacts = list(dedup.values())
        if len(contacts) <= 0:
            self._debug_print(
                "ADSB",
                f"enabled={int(bool(adsb_enabled))} visible={int(bool(adsb_visible))} raw={int(snap.get('aircraft_count', 0) or 0)} mil={int(snap.get('mil_aircraft_count', 0) or 0)} contacts=0",
                min_interval_ms=1200,
            )
            return rendered_items

        show_unknown = bool(dclt_state.get("dclt_show_unknown", True))
        show_friendly = bool(dclt_state.get("dclt_show_friendly", True))
        show_enemy = bool(dclt_state.get("dclt_show_enemy", True))
        show_fsn_id = bool(dclt_state.get("dclt_show_fsn_id", True))
        cat_enabled = dclt_state.get("dclt_cat_enabled")
        if not isinstance(cat_enabled, dict):
            cat_enabled = {}

        own_heading_deg = self._read_heading_deg()
        outer_radius_px = float(4.0 * DPI)
        max_range_nm = max(0.001, float(range_nm))
        icon_px = max(1, int(round(0.45 * DPI * 0.75)))
        id_font = get_font(11)
        white = (255, 255, 255)
        now_s = datetime.now(timezone.utc).timestamp()
        last_update_s = self._safe_float(snap.get("last_update_time"))
        if last_update_s is None:
            last_update_s = now_s
        age_s = max(0.0, now_s - float(last_update_s))
        configured_interval_s = self._safe_float(snap.get("min_interval_s"))
        if configured_interval_s is None:
            configured_interval_s = 5.0
        # Limit dead-reckoning horizon so stale payloads do not drift away forever.
        max_project_s = max(2.0, min(45.0, float(configured_interval_s) * 2.5))
        project_dt_s = min(age_s, max_project_s)

        candidate_items: List[Dict[str, object]] = []
        for contact in contacts:
            lat = contact.get("lat")
            lon = contact.get("lon")
            if lat is None or lon is None:
                continue
            is_sim = bool(contact.get("_plugin_sim", False) or contact.get("_sim", False))
            aff = str(contact.get("affiliation", "UNKNOWN")).upper().strip()
            if aff == "UNKNOWN" and not show_unknown:
                continue
            if aff == "FRIENDLY" and not show_friendly:
                continue
            if aff == "ENEMY" and not show_enemy:
                continue
            category = str(contact.get("category", "")).strip().upper()
            if category in cat_enabled and not bool(cat_enabled.get(category, True)):
                continue
            raw_contact_heading = self._safe_float(contact.get("heading"))
            speed_kts = self._safe_float(contact.get("speed_kts"))
            if speed_kts is None:
                speed_kts = 0.0
            speed_kts = max(0.0, float(speed_kts))

            proj_lat = float(lat)
            proj_lon = float(lon)
            if (not is_sim) and raw_contact_heading is not None and speed_kts > 1.0 and project_dt_s > 0.0:
                travel_nm = speed_kts * (project_dt_s / 3600.0)
                proj_lat, proj_lon = self._project_lat_lon_nm(proj_lat, proj_lon, raw_contact_heading, travel_nm)

            bearing_deg, dist_nm = self._bearing_and_distance_nm(own_lat, own_lon, proj_lat, proj_lon)
            if dist_nm <= 0.01:
                continue

            rel_bearing_deg = (bearing_deg - own_heading_deg) % 360.0
            radial_px = (dist_nm / max_range_nm) * outer_radius_px
            px, py = self._polar_from_north(center, radial_px, rel_bearing_deg)
            was_clamped = False

            contact_heading = raw_contact_heading
            if contact_heading is None:
                contact_heading = bearing_deg
            heading_deg = float(contact_heading) % 360.0
            display_heading = (float(contact_heading) - own_heading_deg) % 360.0
            is_link16 = bool(contact.get("_link16", False))

            # If projected inside screen view but outside the grey HSD box,
            # clamp to the nearest box edge and point directly inward.
            if isinstance(clamp_rect, pygame.Rect) and clamp_rect.width > 0 and clamp_rect.height > 0:
                min_x = int(clamp_rect.left)
                max_x = int(clamp_rect.right - 1)
                min_y = int(clamp_rect.top)
                max_y = int(clamp_rect.bottom - 1)
                if px < min_x or px > max_x or py < min_y or py > max_y:
                    was_clamped = True
                    over_left = float(min_x - px) if px < min_x else 0.0
                    over_right = float(px - max_x) if px > max_x else 0.0
                    over_top = float(min_y - py) if py < min_y else 0.0
                    over_bottom = float(py - max_y) if py > max_y else 0.0
                    side_over = {
                        "LEFT": over_left,
                        "RIGHT": over_right,
                        "TOP": over_top,
                        "BOTTOM": over_bottom,
                    }
                    side = max(side_over, key=side_over.get)
                    px = max(min_x, min(max_x, px))
                    py = max(min_y, min(max_y, py))
                    if side == "LEFT":
                        display_heading = 90.0   # point right
                    elif side == "RIGHT":
                        display_heading = 270.0  # point left
                    elif side == "TOP":
                        display_heading = 180.0  # point down
                    else:
                        display_heading = 0.0    # point up

            contact_id = str(contact.get("id", "")).strip().upper()
            fusion_id = self._fusion_id_for_contact(contact_id)
            own_from_contact_bearing = (bearing_deg + 180.0) % 360.0
            los_delta = self._angle_delta_deg(heading_deg, own_from_contact_bearing)
            closure_kts = float(speed_kts) * math.cos(math.radians(los_delta))
            candidate_items.append(
                {
                    "contact": contact,
                    "aff": aff,
                    "category": category,
                    "dom": str(contact.get("domain", "AIR")).upper().strip(),
                    "is_link16": bool(is_link16),
                    "px": int(px),
                    "py": int(py),
                    "display_heading": float(display_heading),
                    "speed_kts": float(speed_kts),
                    "heading_deg": float(heading_deg),
                    "rel_bearing_deg": float(rel_bearing_deg),
                    "dist_nm": float(dist_nm),
                    "fusion_id": fusion_id,
                    "contact_id": contact_id,
                    "closure_kts": float(closure_kts),
                    "was_clamped": bool(was_clamped),
                }
            )

        if len(candidate_items) <= 0:
            self._debug_print(
                "ADSB",
                f"raw={int(snap.get('aircraft_count', 0) or 0)} contacts={len(contacts)} candidates=0 link16={len(link16_raw)}",
                min_interval_ms=1200,
            )
            return rendered_items

        # Nearest-first ordering so DCLT max-track limits hide farthest tracks first.
        candidate_items.sort(key=lambda item: float(item.get("dist_nm", 1e9)))

        try:
            max_air_tracks = int(dclt_state.get("dclt_max_air", 95))
        except Exception:
            max_air_tracks = 95
        max_air_tracks = max(10, min(95, max_air_tracks))
        if max_air_tracks < len(candidate_items):
            candidate_items = candidate_items[:max_air_tracks]
        budget = len(candidate_items)

        # Queue visible contact icons for deferred loading (separate from draw).
        preload_count = len(candidate_items)
        for item in candidate_items[:preload_count]:
            if bool(item.get("is_link16", False)):
                continue
            dom_q = str(item.get("dom", "AIR")).upper().strip()
            if dom_q not in {"AIR", "GROUND"}:
                dom_q = "AIR"
            speed_kts_q = float(item.get("speed_kts", 0.0))
            contact_q = item.get("contact")
            contact_row_q = contact_q if isinstance(contact_q, dict) else {}
            self._enqueue_track_icon_load_job(
                dclt_state,
                str(item.get("aff", "UNKNOWN")),
                dom_q,
                icon_px,
                float(item.get("display_heading", 0.0)),
                0,
                bool(speed_kts_q > 1.0),
                self._track_is_emitting(contact_row_q),
            )
        q_now = dclt_state.get("_tsd_track_icon_load_queue")
        q_len = len(q_now) if isinstance(q_now, deque) else 0
        self._debug_print(
            "ICON_QUEUE",
            f"preload={preload_count} budget={budget} queued={q_len} rot_cache={len(self._adsb_icon_rot_cache)} base_cache={len(self._track_symbol_base_cache)}",
            min_interval_ms=900,
        )

        for item in candidate_items[:budget]:
            dom = str(item.get("dom", "AIR")).upper().strip()
            if dom not in {"AIR", "GROUND"}:
                dom = "AIR"
            is_link16 = bool(item.get("is_link16", False))
            px_i = int(item.get("px", 0))
            py_i = int(item.get("py", 0))
            if isinstance(clamp_rect, pygame.Rect) and clamp_rect.width > 0 and clamp_rect.height > 0:
                if not clamp_rect.collidepoint((px_i, py_i)):
                    continue
            display_heading_i = float(item.get("display_heading", 0.0))
            speed_kts_i = float(item.get("speed_kts", 0.0))
            contact = item.get("contact")
            contact_row = contact if isinstance(contact, dict) else {}
            is_sim = bool(contact_row.get("_sim", False))
            if is_link16 and (not is_sim):
                ownship_icon = self._get_cyan_aircraft_icon((icon_px, icon_px))
                if ownship_icon is None:
                    continue
                try:
                    icon = pygame.transform.rotozoom(ownship_icon, -float(display_heading_i), 1.0)
                except Exception:
                    try:
                        icon = pygame.transform.rotate(ownship_icon, -float(display_heading_i))
                    except Exception:
                        icon = ownship_icon
            else:
                quality_level = 0
                emitting = self._track_is_emitting(contact_row)
                moving = bool(float(speed_kts_i) > 1.0)
                icon = self._get_adsb_contact_icon(
                    str(item.get("aff", "UNKNOWN")),
                    dom,
                    icon_px,
                    display_heading_i,
                    quality_level=quality_level,
                    moving=moving,
                    emitting=emitting,
                    build_if_missing=False,
                )
            if icon is None:
                continue
            ir = icon.get_rect(center=(px_i, py_i))
            if isinstance(clamp_rect, pygame.Rect) and clamp_rect.width > 0 and clamp_rect.height > 0:
                if not ir.colliderect(clamp_rect):
                    continue
            surface.blit(icon, ir)

            if show_fsn_id and (not is_link16):
                id_surf = id_font.render(str(item.get("fusion_id", "")), True, white)
                id_y = ir.bottom + 1
                if isinstance(clamp_rect, pygame.Rect) and clamp_rect.height > 0:
                    id_y = min(id_y, clamp_rect.bottom - id_surf.get_height() - 1)
                id_rect = id_surf.get_rect(centerx=px_i, y=id_y)
                if isinstance(clamp_rect, pygame.Rect) and clamp_rect.width > 0:
                    if id_rect.left < clamp_rect.left + 1:
                        id_rect.left = clamp_rect.left + 1
                    if id_rect.right > clamp_rect.right - 1:
                        id_rect.right = clamp_rect.right - 1
                surface.blit(id_surf, id_rect)

            rendered_items.append(
                {
                    "id": str(item.get("contact_id", "")),
                    "x": int(px_i),
                    "y": int(py_i),
                    "fusion_id": str(item.get("fusion_id", "")),
                    "affiliation": str(item.get("aff", "UNKNOWN")),
                    "domain": dom,
                    "category": str(item.get("category", "")),
                    "rel_bearing_deg": float(item.get("rel_bearing_deg", 0.0)),
                    "range_nm": float(item.get("dist_nm", 0.0)),
                    "heading_deg": float(item.get("heading_deg", 0.0)),
                    "closure_kts": float(item.get("closure_kts", 0.0)),
                    "raw_row": contact_row.get("raw_row"),
                    "is_clamped": bool(item.get("was_clamped", False)),
                    "in_range": bool(float(item.get("dist_nm", 0.0)) <= max_range_nm),
                }
            )
        # Build a tiny batch after drawing so the page appears immediately and icons
        # progressively populate without blocking the render path.
        self._service_track_icon_load_jobs(
            dclt_state,
            max_jobs=2,
            max_ms=2.0,
            debug_label=self._subportal_label(),
        )
        self._debug_print(
            "ADSB",
            f"raw={int(snap.get('aircraft_count', 0) or 0)} contacts={len(contacts)} candidates={len(candidate_items)} budget={budget} rendered={len(rendered_items)} link16={len(link16_raw)}",
            min_interval_ms=900,
        )
        return rendered_items

    @staticmethod
    def _read_ownship_altitude_ft_for_vsd() -> float:
        try:
            throttle = PANEL_BUTTON_STATES.get("THROTTLE", {})
            if not isinstance(throttle, dict):
                return 0.0
            aircraft = throttle.get("AIRCRAFT", {})
            if not isinstance(aircraft, dict):
                return 0.0
            return float(aircraft.get("ALTITUDE_FT", aircraft.get("ALTITUDE_TARGET_FT", 0.0)) or 0.0)
        except Exception:
            return 0.0

    @staticmethod
    def _read_ownship_pitch_deg_for_vsd() -> float:
        try:
            throttle = PANEL_BUTTON_STATES.get("THROTTLE", {})
            if not isinstance(throttle, dict):
                return 0.0
            aircraft = throttle.get("AIRCRAFT", {})
            if not isinstance(aircraft, dict):
                return 0.0
            return float(
                aircraft.get(
                    "ATT_PITCH_DEG",
                    aircraft.get(
                        "ATTITUDE",
                        aircraft.get("ATT_PITCH_RAW_DEG", aircraft.get("PITCH", 0.0)),
                    ),
                )
                or 0.0
            )
        except Exception:
            return 0.0

    @staticmethod
    def _contact_altitude_ft_for_vsd(contact: Dict[str, object]) -> Optional[float]:
        if not isinstance(contact, dict):
            return None
        for key in ("altitude_ft", "alt_ft", "alt_baro", "alt_geom", "altitude"):
            val = Tsd1Format._safe_float(contact.get(key))
            if val is not None:
                return float(val)
        raw = contact.get("raw_row")
        if isinstance(raw, dict):
            for key in ("alt_baro", "alt_geom", "altitude", "alt_ft", "altitude_ft"):
                val = Tsd1Format._safe_float(raw.get(key))
                if val is not None:
                    return float(val)
        return None

    def _draw_vsd_tracks(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        snap = TSD_ADSB_STATE if isinstance(TSD_ADSB_STATE, dict) else {}
        link16_raw = TSD_LINK16_CONTACTS if isinstance(TSD_LINK16_CONTACTS, list) else []
        sim_live = TSD_SIM_CONTACTS if isinstance(TSD_SIM_CONTACTS, list) else []
        show_link16 = len(link16_raw) > 0
        show_sim_live = len(sim_live) > 0
        adsb_enabled = bool(snap.get("enabled", False))
        adsb_visible = bool(snap.get("show_live_adsb", True))
        if (not adsb_enabled or not adsb_visible) and (not show_link16) and (not show_sim_live):
            return

        own_lat = self._safe_float(snap.get("lat"))
        own_lon = self._safe_float(snap.get("lon"))
        if own_lat is None or own_lon is None:
            geo = snap.get("geo")
            if isinstance(geo, dict):
                own_lat = self._safe_float(geo.get("lat"))
                own_lon = self._safe_float(geo.get("lon"))
        if own_lat is None or own_lon is None:
            return

        dclt_state = self._ensure_dclt_state()
        contacts: List[Dict[str, object]] = []
        if adsb_enabled and adsb_visible:
            raw_payload = snap.get("raw")
            mil_payload = snap.get("mil_raw")
            last_update_key = self._safe_float(snap.get("last_update_time"))
            sim_tick_key = 0
            try:
                sim_tick_key = int(getattr(sys.modules.get(__name__), "PMD_SIM_TARGETS_TICK", 0) or 0)
            except Exception:
                sim_tick_key = 0
            cache_key = (
                id(raw_payload),
                id(mil_payload),
                float(last_update_key) if last_update_key is not None else 0.0,
                int(sim_tick_key),
            )
            cached_key = dclt_state.get("_tsd_adsb_contacts_cache_key")
            cached_contacts = dclt_state.get("_tsd_adsb_contacts_cache")
            if (
                isinstance(cached_contacts, list)
                and isinstance(cached_key, tuple)
                and cached_key == cache_key
            ):
                contacts.extend(cached_contacts)
            else:
                parsed = self._adsb_contacts(raw_payload, mil_payload=mil_payload)
                dclt_state["_tsd_adsb_contacts_cache_key"] = cache_key
                dclt_state["_tsd_adsb_contacts_cache"] = parsed
                contacts.extend(parsed)
        if isinstance(link16_raw, list):
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
                        "domain": str(item.get("domain", "AIR")).upper().strip() or "AIR",
                        "category": str(item.get("category", "B1")).upper().strip() or "B1",
                        "altitude_ft": self._safe_float(item.get("altitude_ft")),
                        "_link16": True,
                        "_sim": bool(item.get("_sim", False)),
                    }
                )
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
                    "domain": str(item.get("domain", "AIR")).upper().strip() or "AIR",
                    "category": str(item.get("category", "B1")).upper().strip() or "B1",
                    "altitude_ft": self._safe_float(item.get("altitude_ft")),
                    "_plugin_sim": True,
                    "_sim": True,
                }
            )
        if len(contacts) > 1:
            dedup: Dict[str, Dict[str, object]] = {}
            for c in contacts:
                if not isinstance(c, dict):
                    continue
                cid = str(c.get("id", "")).strip()
                if cid == "":
                    continue
                prev = dedup.get(cid)
                if prev is None:
                    dedup[cid] = c
                    continue
                prev_sim = bool(prev.get("_plugin_sim", False) or prev.get("_sim", False))
                cur_sim = bool(c.get("_plugin_sim", False) or c.get("_sim", False))
                if cur_sim and (not prev_sim):
                    dedup[cid] = c
            contacts = list(dedup.values())

        show_unknown = bool(dclt_state.get("dclt_show_unknown", True))
        show_friendly = bool(dclt_state.get("dclt_show_friendly", True))
        show_enemy = bool(dclt_state.get("dclt_show_enemy", True))
        show_fsn_id = bool(dclt_state.get("dclt_show_fsn_id", True))
        cat_enabled = dclt_state.get("dclt_cat_enabled")
        if not isinstance(cat_enabled, dict):
            cat_enabled = {}

        own_heading_deg = self._read_heading_deg()
        own_alt_ft = self._read_ownship_altitude_ft_for_vsd()
        own_pitch_deg = self._read_ownship_pitch_deg_for_vsd()
        max_range_nm = max(0.001, float(self._effective_range_nm(self._range_nm())))
        side_view = bool(self._state().get("vsd_side_view", False))

        candidate_items: List[Dict[str, object]] = []
        for contact in contacts:
            if not isinstance(contact, dict):
                continue
            lat = self._safe_float(contact.get("lat"))
            lon = self._safe_float(contact.get("lon"))
            if lat is None or lon is None:
                continue
            dom = str(contact.get("domain", "AIR")).upper().strip()
            if dom != "AIR":
                continue
            aff = str(contact.get("affiliation", "UNKNOWN")).upper().strip()
            if aff == "UNKNOWN" and not show_unknown:
                continue
            if aff == "FRIENDLY" and not show_friendly:
                continue
            if aff == "ENEMY" and not show_enemy:
                continue
            category = str(contact.get("category", "")).strip().upper()
            if category in cat_enabled and not bool(cat_enabled.get(category, True)):
                continue
            bearing_deg, dist_nm = self._bearing_and_distance_nm(float(own_lat), float(own_lon), float(lat), float(lon))
            if dist_nm <= 0.01 or dist_nm > max_range_nm:
                continue
            rel_az_deg = self._angle_delta_deg(float(bearing_deg), float(own_heading_deg))
            rel_az_rad = math.radians(float(rel_az_deg))
            contact_alt_ft = self._contact_altitude_ft_for_vsd(contact)
            if contact_alt_ft is None:
                contact_alt_ft = float(own_alt_ft)
            delta_alt_ft = float(contact_alt_ft) - float(own_alt_ft)
            horiz_ft = max(1.0, float(dist_nm) * 6076.12)
            world_el_deg = math.degrees(math.atan2(float(delta_alt_ft), float(horiz_ft)))
            body_el_deg = float(world_el_deg) - float(own_pitch_deg)
            forward_nm = float(dist_nm) * math.cos(rel_az_rad)
            raw_heading = self._safe_float(contact.get("heading"))
            if raw_heading is None:
                raw_heading = float(bearing_deg)
            display_heading = (float(raw_heading) - float(own_heading_deg)) % 360.0
            contact_id = str(contact.get("id", "")).strip().upper()
            fusion_id = self._fusion_id_for_contact(contact_id)
            candidate_items.append(
                {
                    "contact": contact,
                    "aff": aff,
                    "rel_az_deg": float(rel_az_deg),
                    "body_el_deg": float(body_el_deg),
                    "forward_nm": float(forward_nm),
                    "delta_alt_ft": float(delta_alt_ft),
                    "display_heading": float(display_heading),
                    "dist_nm": float(dist_nm),
                    "fusion_id": fusion_id,
                }
            )

        if len(candidate_items) <= 0:
            return

        candidate_items.sort(key=lambda item: float(item.get("dist_nm", 1e9)))
        try:
            max_air_tracks = int(dclt_state.get("dclt_max_air", 95))
        except Exception:
            max_air_tracks = 95
        max_air_tracks = max(10, min(95, max_air_tracks))
        if max_air_tracks < len(candidate_items):
            candidate_items = candidate_items[:max_air_tracks]

        cx = rect.centerx
        cy = rect.top + int(round(2.5 * DPI))
        outer_r = max(2, int(round((4.5 * DPI) / 2.0)))
        az_limit_deg = 90.0
        el_limit_deg = 60.0
        side_alt_limit_ft = max(
            1.0,
            float(max_range_nm) * 6076.12 * math.tan(math.radians(float(el_limit_deg))),
        )
        icon_px = max(1, int(round(0.45 * DPI * 0.75)))
        id_font = get_font(11)
        for item in candidate_items:
            az = float(item.get("rel_az_deg", 0.0))
            if side_view:
                nx = float(item.get("forward_nm", 0.0)) / float(max_range_nm)
                ny = float(item.get("delta_alt_ft", 0.0)) / float(side_alt_limit_ft)
            else:
                nx = az / az_limit_deg
                el = float(item.get("body_el_deg", 0.0))
                ny = el / el_limit_deg
            px = int(round(float(cx) + nx * float(outer_r)))
            py = int(round(float(cy) - ny * float(outer_r)))
            dx = float(px - cx)
            dy = float(py - cy)
            if (dx * dx + dy * dy) > (float(outer_r) * float(outer_r)):
                continue
            aff = str(item.get("aff", "UNKNOWN")).upper().strip()
            contact = item.get("contact")
            row = contact if isinstance(contact, dict) else {}
            is_link16 = bool(row.get("_link16", False))
            is_sim = bool(row.get("_sim", False))
            display_heading = float(item.get("display_heading", 0.0))
            if is_link16 and (not is_sim):
                ownship_icon = self._get_cyan_aircraft_icon((icon_px, icon_px))
                if ownship_icon is None:
                    continue
                try:
                    icon = pygame.transform.rotozoom(ownship_icon, -float(display_heading), 1.0)
                except Exception:
                    try:
                        icon = pygame.transform.rotate(ownship_icon, -float(display_heading))
                    except Exception:
                        icon = ownship_icon
            else:
                emitting = self._track_is_emitting(row)
                moving = bool(float(row.get("speed_kts", 0.0) or 0.0) > 1.0)
                icon = self._get_adsb_contact_icon(
                    str(aff),
                    "AIR",
                    icon_px,
                    display_heading,
                    quality_level=0,
                    moving=moving,
                    emitting=emitting,
                    build_if_missing=True,
                )
            if icon is None:
                continue
            ir = icon.get_rect(center=(px, py))
            surface.blit(icon, ir)
            if show_fsn_id:
                txt = str(item.get("fusion_id", "")).strip()
                if txt != "":
                    s = id_font.render(txt, True, (255, 255, 255))
                    rr = s.get_rect(centerx=px, top=ir.bottom + 1)
                    surface.blit(s, rr)

    def _draw_header_value_button(
        self,
        surface: pygame.Surface,
        box: pygame.Rect,
        header: str,
        value: str,
        flashing: bool,
        header_color: Tuple[int, int, int] = (0, 255, 0),
        value_color: Tuple[int, int, int] = (0, 255, 255),
        h_align: str = "center",
        v_align: str = "center",
    ) -> None:
        font = get_font(14)
        h_surf = font.render(header, True, (0, 0, 0) if flashing else header_color)
        v_surf = font.render(value, True, (0, 0, 0) if flashing else value_color)
        total_h = h_surf.get_height() + 1 + v_surf.get_height()
        if v_align == "top":
            y = box.top + OSB_PADDING
        else:
            y = box.centery - total_h // 2
        if h_align == "left":
            h_rect = h_surf.get_rect(left=box.left + OSB_PADDING, y=y)
        elif h_align == "right":
            h_rect = h_surf.get_rect(right=box.right - OSB_PADDING, y=y)
        else:
            h_rect = h_surf.get_rect(centerx=box.centerx, y=y)
        y = h_rect.bottom + 1
        if h_align == "left":
            v_rect = v_surf.get_rect(left=box.left + OSB_PADDING, y=y)
        elif h_align == "right":
            v_rect = v_surf.get_rect(right=box.right - OSB_PADDING, y=y)
        else:
            v_rect = v_surf.get_rect(centerx=box.centerx, y=y)
        pygame.draw.rect(surface, (0, 0, 0), h_rect.inflate(6, 2), 0)
        pygame.draw.rect(surface, (0, 0, 0), v_rect.inflate(6, 2), 0)
        if flashing:
            fr = h_rect.union(v_rect).inflate(4, 2)
            pygame.draw.rect(surface, (255, 255, 255), fr)
        surface.blit(h_surf, h_rect)
        underline_color = (0, 0, 0) if flashing else header_color
        pygame.draw.line(
            surface,
            underline_color,
            (h_rect.left, h_rect.bottom + 1),
            (h_rect.right, h_rect.bottom + 1),
            1,
        )
        surface.blit(v_surf, v_rect)

    def _draw_inc_dec_and_range(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        *,
        l1_flash: bool = False,
        l2_flash: bool = False,
    ) -> None:
        cyan = (0, 255, 255)
        white = (255, 255, 255)
        l1 = self._osb_box(rect, "L1")
        l2 = self._osb_box(rect, "L2")
        if l1 is not None:
            tri_w = max(10, l1.width // 3)
            tri_h = max(10, l1.height // 3)
            cx = l1.left + OSB_PADDING + tri_w // 2 + 2
            cy = l1.centery
            up_points = [
                (cx, cy - tri_h // 2),
                (cx - tri_w // 2, cy + tri_h // 2),
                (cx + tri_w // 2, cy + tri_h // 2),
            ]
            pygame.draw.polygon(surface, white if bool(l1_flash) else cyan, up_points, 0)
        if l2 is not None:
            tri_w = max(10, l2.width // 3)
            tri_h = max(10, l2.height // 3)
            cx = l2.left + OSB_PADDING + tri_w // 2 + 2
            cy = l2.centery
            down_points = [
                (cx, cy + tri_h // 2),
                (cx - tri_w // 2, cy - tri_h // 2),
                (cx + tri_w // 2, cy - tri_h // 2),
            ]
            pygame.draw.polygon(surface, white if bool(l2_flash) else cyan, down_points, 0)
        if l1 is not None and l2 is not None:
            font = get_font(14)
            range_text = self._format_range_label(self._range_nm())
            txt = font.render(range_text, True, cyan)
            tx = l1.left + OSB_PADDING + (txt.get_width() // 2)
            ty = int(round((l1.centery + l2.centery) / 2.0))
            tr = txt.get_rect(center=(tx, ty))
            pygame.draw.rect(surface, (0, 0, 0), tr.inflate(6, 2), 0)
            surface.blit(txt, tr)

    @staticmethod
    def _draw_text_line_backdrops(
        surface: pygame.Surface,
        box: pygame.Rect,
        lines: Iterable[str],
        font_size: int,
        h_align: str,
        v_align: str,
        padding: int,
    ) -> None:
        clean_lines = [str(line) for line in lines if str(line) != ""]
        if len(clean_lines) <= 0:
            return
        font = get_font(int(font_size))
        rendered = [font.render(line, True, (255, 255, 255)) for line in clean_lines]
        total_h = sum(s.get_height() for s in rendered) + max(0, len(rendered) - 1)
        if str(v_align).lower() == "top":
            y = box.top + int(padding)
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

    def _draw_osb_labels(self, surface: pygame.Surface, rect: pygame.Rect, context: FormatContext) -> None:
        if self._is_vsd():
            self._draw_vsd_osb_labels(surface, rect, context)
            return

        now_ms = int(pygame.time.get_ticks())
        state = self._state()
        # MAP currently disabled by request.
        map_available = False
        state["map_on"] = False

        standard_items: List[Tuple[str, ButtonState]] = [
            (
                "T4",
                ButtonState(
                    button_id="TSD1_T4",
                    button_type=ButtonType.PAGE_ACCESS,
                    text="DLINK>",
                    h_align="center",
                    v_align="top",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("T4") else 0,
                ),
            ),
            (
                "T5",
                ButtonState(
                    button_id="TSD1_T5",
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
                    button_id="TSD1_L4",
                    button_type=ButtonType.MOMENTARY_SINGLE,
                    text="MAP",
                    is_single_function=True,
                    is_on=False,
                    enabled=False,
                    h_align="left",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("L4") else 0,
                ),
            ),
            (
                "L5",
                ButtonState(
                    button_id="TSD1_L5",
                    button_type=ButtonType.MOMENTARY_SINGLE,
                    text="BLOB",
                    is_single_function=True,
                    is_on=bool(state.get("blob_on", False)),
                    h_align="left",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("L5") else 0,
                ),
            ),
            (
                "R3",
                ButtonState(
                    button_id="TSD1_R3",
                    button_type=ButtonType.MOMENTARY_SINGLE,
                    text="MK",
                    is_single_function=True,
                    is_on=bool(state.get("mk_on", False)),
                    h_align="right",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("R3") else 0,
                ),
            ),
            (
                "R4",
                ButtonState(
                    button_id="TSD1_R4",
                    button_type=ButtonType.PAGE_ACCESS,
                    text="ASGN>",
                    enabled=False,
                    h_align="right",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("R4") else 0,
                ),
            ),
            (
                "R5",
                ButtonState(
                    button_id="TSD1_R5",
                    button_type=ButtonType.MOMENTARY_SINGLE,
                    text="DCLT>",
                    h_align="right",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("R5") else 0,
                ),
            ),
            (
                "R6",
                ButtonState(
                    button_id="TSD1_R6",
                    button_type=ButtonType.MOMENTARY_SINGLE,
                    text="ATK",
                    is_single_function=True,
                    is_on=bool(state.get("atk_on", False)),
                    h_align="right",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("R6") else 0,
                ),
            ),
        ]
        for label, state in standard_items:
            box = self._osb_box(rect, label)
            if box is None:
                continue
            backdrop_lines = state.text.split("\n")
            self._draw_text_line_backdrops(
                surface,
                box,
                backdrop_lines,
                state.font_size,
                state.h_align,
                state.v_align,
                state.padding,
            )
            render_button(surface, box, state, get_font, now_ms)

        # T2/L3: green header + underline with cyan changing value.
        t2_box = self._osb_box(rect, "T2")
        if t2_box is not None:
            self._draw_header_value_button(
                surface,
                t2_box,
                "VIEW",
                self._view_label(),
                bool(context.is_osb_flashing("T2")),
                h_align="center",
                v_align="top",
            )

        l3_box = self._osb_box(rect, "L3")
        if l3_box is not None:
            self._draw_header_value_button(
                surface,
                l3_box,
                "EMC",
                self._emc_label(),
                bool(context.is_osb_flashing("L3")),
                h_align="left",
                v_align="center",
            )

        # R1 / R2 white labels. R1 reflects extra keyboard zoom state.
        white = (255, 255, 255)
        base_range_nm = self._range_nm()
        effective_range_nm = self._effective_range_nm(base_range_nm)
        zoom_active = effective_range_nm < (base_range_nm - 0.0005)
        r1_label = "ZOOM" if zoom_active else "NORM"
        r1_value = self._format_zoom_value_label(effective_range_nm if zoom_active else base_range_nm)
        for label, text in (("R1", f"{r1_label}\n{r1_value}"), ("R2", "DEP")):
            box = self._osb_box(rect, label)
            if box is None:
                continue
            font = get_font(14)
            lines = text.split("\n")
            rendered = [font.render(line, True, white) for line in lines]
            total_h = sum(s.get_height() for s in rendered) + max(0, len(rendered) - 1)
            y = box.centery - total_h // 2
            for surf in rendered:
                rr = surf.get_rect(right=box.right - OSB_PADDING, y=y)
                pygame.draw.rect(surface, (0, 0, 0), rr.inflate(6, 2), 0)
                surface.blit(surf, rr)
                y += surf.get_height() + 1

        # L6: data-entry ATK value.
        l6_box = self._osb_box(rect, "L6")
        if l6_box is not None:
            cyan = (0, 255, 255)
            white = (255, 255, 255)
            font = get_font(14)
            slot_h = l6_box.height / 3.0
            atk_title = font.render("ATK", True, cyan)
            title_rect = atk_title.get_rect(left=l6_box.left + OSB_PADDING)
            title_rect.y = int(l6_box.top + (1 * slot_h) + (slot_h - atk_title.get_height()) / 2)
            pygame.draw.rect(surface, (0, 0, 0), title_rect.inflate(6, 2), 0)
            surface.blit(atk_title, title_rect)

            atk_selected = self._atk_selected()
            raw_input = self._atk_input()
            if atk_selected and raw_input != "":
                value_text = raw_input[-3:].rjust(3, "_") + "\u2190"
            else:
                atk_val = self._atk_value()
                value_text = "360" if atk_val == 360 else f"{atk_val:03d}"
            atk_val_surf = font.render(value_text, True, white if atk_selected else cyan)
            val_rect = atk_val_surf.get_rect(left=l6_box.left + OSB_PADDING)
            val_rect.y = int(l6_box.top + (2 * slot_h) + (slot_h - atk_val_surf.get_height()) / 2)
            pygame.draw.rect(surface, (0, 0, 0), val_rect.inflate(6, 2), 0)
            if atk_selected:
                pygame.draw.rect(surface, white, val_rect.inflate(4, 2), 1)
            surface.blit(atk_val_surf, val_rect)

        self._draw_inc_dec_and_range(
            surface,
            rect,
            l1_flash=bool(context.is_osb_flashing("L1")),
            l2_flash=bool(context.is_osb_flashing("L2")),
        )

    def _draw_vsd_osb_labels(self, surface: pygame.Surface, rect: pygame.Rect, context: FormatContext) -> None:
        now_ms = int(pygame.time.get_ticks())
        white = (255, 255, 255)

        t5_box = self._osb_box(rect, "T5")
        if t5_box is not None:
            t5_state = ButtonState(
                button_id="TSD1_T5",
                button_type=ButtonType.PAGE_ACCESS,
                text="CNTL>",
                h_align="center",
                v_align="top",
                padding=OSB_PADDING,
                font_size=14,
                flash_until_ms=1 if context.is_osb_flashing("T5") else 0,
            )
            self._draw_text_line_backdrops(
                surface,
                t5_box,
                t5_state.text.split("\n"),
                t5_state.font_size,
                t5_state.h_align,
                t5_state.v_align,
                t5_state.padding,
            )
            render_button(
                surface,
                t5_box,
                t5_state,
                get_font,
                now_ms,
            )

        t2_box = self._osb_box(rect, "T2")
        if t2_box is not None:
            self._draw_header_value_button(
                surface,
                t2_box,
                "VIEW",
                self._view_label(),
                bool(context.is_osb_flashing("T2")),
                h_align="center",
                v_align="top",
            )

        state = self._state()
        l3_mode = "SIDE" if bool(state.get("vsd_side_view", False)) else "FWD"
        for label, text in (("L3", l3_mode), ("L4", "RCS")):
            box = self._osb_box(rect, label)
            if box is None:
                continue
            font = get_font(14)
            is_flash = bool(context.is_osb_flashing(label))
            surf = font.render(text, True, (0, 0, 0) if is_flash else white)
            rr = surf.get_rect(left=box.left + OSB_PADDING, centery=box.centery)
            if is_flash:
                pygame.draw.rect(surface, white, rr.inflate(6, 2), 0)
            else:
                pygame.draw.rect(surface, (0, 0, 0), rr.inflate(6, 2), 0)
            surface.blit(surf, rr)

        l5_box = self._osb_box(rect, "L5")
        if l5_box is not None:
            self._draw_header_value_button(
                surface,
                l5_box,
                "RCS",
                "FTR",
                bool(context.is_osb_flashing("L5")),
                h_align="left",
                v_align="center",
            )

    def _draw_vsd_symbology(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        white = (255, 255, 255)
        green = (0, 255, 0)

        # Keep VSD ball geometry fixed for all portal sizes:
        # constant size, constant vertical position from top, centered horizontally.
        scale = 1.0
        cx = rect.centerx
        cy = rect.top + int(round(2.5 * DPI))
        outer_r = max(2, int(round((4.5 * DPI) / 2.0)))
        self._draw_vsd_bg_image(surface, (cx, cy), outer_r)
        pygame.draw.circle(surface, white, (cx, cy), outer_r, 1)

        # Slightly smaller green circle with matching top edge.
        delta_r = max(2, int(round(0.10 * DPI * scale)))
        inner_r = max(1, outer_r - delta_r)
        inner_cy = cy - (outer_r - inner_r)
        pygame.draw.circle(surface, green, (cx, inner_cy), inner_r, 1)

        # White crosshair touching the circle.
        pygame.draw.line(surface, white, (cx - outer_r, cy), (cx + outer_r, cy), 1)
        pygame.draw.line(surface, white, (cx, cy - outer_r), (cx, cy + outer_r), 1)

        # 8 hash marks per side on each axis; spacing compresses outward.
        marks_per_side = 8
        first_from_center = 0.5 * DPI * scale
        edge_gap = 0.0625 * DPI * scale  # 0.125/2 inches.
        max_from_center = max(first_from_center, outer_r - edge_gap)
        half_tick = max(2, int(round(0.05 * DPI * scale)))

        dists: List[float] = []
        if marks_per_side > 0:
            dists.append(first_from_center)
        if marks_per_side > 1:
            remaining = max_from_center - first_from_center
            extra = marks_per_side - 1
            if remaining <= 0.0:
                for _ in range(extra):
                    dists.append(first_from_center)
            else:
                # Gap from center->first is largest (0.5in).
                # From first->second and onward, gaps shrink progressively outward.
                gap_ratio = 0.78
                den = 1.0 - (gap_ratio ** extra)
                if abs(den) < 1e-6:
                    base_gap = remaining / float(extra)
                else:
                    base_gap = remaining * (1.0 - gap_ratio) / den
                if base_gap >= first_from_center:
                    gap_ratio = 0.90
                    den = 1.0 - (gap_ratio ** extra)
                    base_gap = remaining * (1.0 - gap_ratio) / den if abs(den) >= 1e-6 else remaining / float(extra)

                d = first_from_center
                gap = base_gap
                for _ in range(extra):
                    d += gap
                    dists.append(d)
                    gap *= gap_ratio

        for d in dists:
            dx = int(round(d))
            dy = int(round(d))
            # Hashes on horizontal crosshair.
            pygame.draw.line(surface, white, (cx + dx, cy - half_tick), (cx + dx, cy + half_tick), 1)
            pygame.draw.line(surface, white, (cx - dx, cy - half_tick), (cx - dx, cy + half_tick), 1)
            # Hashes on vertical crosshair.
            pygame.draw.line(surface, white, (cx - half_tick, cy + dy), (cx + half_tick, cy + dy), 1)
            pygame.draw.line(surface, white, (cx - half_tick, cy - dy), (cx + half_tick, cy - dy), 1)

        # Two vertical ovals: side extents align to the 3rd and 6th hash marks.
        if len(dists) >= 6:
            for idx in (2, 5):  # 3rd and 6th
                rx = max(1, int(round(dists[idx])))
                oval_rect = pygame.Rect(0, 0, rx * 2, outer_r * 2)
                oval_rect.center = (cx, cy)
                pygame.draw.ellipse(surface, white, oval_rect, 1)

    def _draw_hsd_subportal(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        green = (0, 255, 0)
        cyan = (0, 255, 255)
        font = get_font(14)
        footer_font = get_font(14)

        footer = footer_font.render(self._subportal_label(), True, cyan)
        footer_rect = footer.get_rect(centerx=rect.centerx)
        footer_rect.bottom = rect.bottom - 2

        content_rect = rect.copy()
        content_rect.height = max(4, footer_rect.top - rect.top - 2)

        mid_x = content_rect.centerx
        pygame.draw.line(surface, green, (mid_x, content_rect.top + 2), (mid_x, content_rect.bottom - 2), 1)

        left = font.render("A-A NTS", True, green)
        right = font.render("A-S NTS", True, green)
        left_rect = left.get_rect(centerx=(content_rect.left + mid_x) // 2, centery=content_rect.top + max(10, left.get_height() // 2 + 2))
        right_rect = right.get_rect(centerx=(mid_x + content_rect.right) // 2, centery=left_rect.centery)
        surface.blit(left, left_rect)
        surface.blit(right, right_rect)
        pygame.draw.line(surface, green, (left_rect.left, left_rect.bottom + 1), (left_rect.right, left_rect.bottom + 1), 1)
        pygame.draw.line(surface, green, (right_rect.left, right_rect.bottom + 1), (right_rect.right, right_rect.bottom + 1), 1)
        footer_bg = pygame.Rect(rect.left, max(rect.top, footer_rect.top - 1), rect.width, min(rect.bottom - max(rect.top, footer_rect.top - 1), footer_rect.height + 3))
        pygame.draw.rect(surface, (0, 0, 0), footer_bg, 0)
        surface.blit(footer, footer_rect)

    def _draw_vsd_subportal(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        white = (255, 255, 255)
        green = (0, 255, 0)
        cyan = (0, 255, 255)
        footer_font = get_font(14)

        footer = footer_font.render(self._subportal_label(), True, cyan)
        footer_rect = footer.get_rect(centerx=rect.centerx)
        footer_rect.bottom = rect.bottom - 2

        content_rect = rect.copy()
        content_rect.height = max(4, footer_rect.top - rect.top - 2)

        cx = content_rect.centerx
        cy = content_rect.centery
        outer_r = max(2, min(content_rect.width, content_rect.height) // 2 - 4)
        self._draw_vsd_bg_image(surface, (cx, cy), outer_r)
        pygame.draw.circle(surface, white, (cx, cy), outer_r, 1)
        inner_r = max(1, outer_r - 2)
        inner_cy = cy - (outer_r - inner_r)
        pygame.draw.circle(surface, green, (cx, inner_cy), inner_r, 1)

        # Full VSD subportal symbology: crosshair, compressing hashes, and two ovals.
        pygame.draw.line(surface, white, (cx - outer_r, cy), (cx + outer_r, cy), 1)
        pygame.draw.line(surface, white, (cx, cy - outer_r), (cx, cy + outer_r), 1)

        marks_per_side = 8
        # Scale subportal hash geometry from the full-size VSD proportions.
        # Full-size reference: outer_r=2.25in, first=0.5in, edge_gap=0.0625in.
        ratio_first = 0.5 / 2.25
        ratio_edge = 0.0625 / 2.25
        ratio_tick = 0.04 / 2.25
        first_from_center = max(2.0, float(outer_r) * ratio_first)
        edge_gap = max(1.0, float(outer_r) * ratio_edge)
        if first_from_center >= (float(outer_r) - edge_gap):
            first_from_center = max(1.0, (float(outer_r) - edge_gap) * 0.45)
        max_from_center = max(first_from_center, float(outer_r) - edge_gap)
        half_tick = max(1, int(round(float(outer_r) * ratio_tick)))

        dists: List[float] = []
        if marks_per_side > 0:
            dists.append(first_from_center)
        if marks_per_side > 1:
            remaining = max_from_center - first_from_center
            extra = marks_per_side - 1
            if remaining <= 0.0:
                for _ in range(extra):
                    dists.append(first_from_center)
            else:
                gap_ratio = 0.78
                den = 1.0 - (gap_ratio ** extra)
                base_gap = remaining * (1.0 - gap_ratio) / den if abs(den) >= 1e-6 else remaining / float(extra)
                if base_gap >= first_from_center:
                    gap_ratio = 0.90
                    den = 1.0 - (gap_ratio ** extra)
                    base_gap = remaining * (1.0 - gap_ratio) / den if abs(den) >= 1e-6 else remaining / float(extra)
                d = first_from_center
                gap = base_gap
                for _ in range(extra):
                    d += gap
                    dists.append(d)
                    gap *= gap_ratio

        px_dists: List[int] = []
        for d in dists:
            px = max(1, min(outer_r - 1, int(round(d))))
            if len(px_dists) <= 0 or px != px_dists[-1]:
                px_dists.append(px)

        for px in px_dists:
            # Horizontal axis hash ticks.
            pygame.draw.line(surface, white, (cx + px, cy - half_tick), (cx + px, cy + half_tick), 1)
            pygame.draw.line(surface, white, (cx - px, cy - half_tick), (cx - px, cy + half_tick), 1)
            # Vertical axis hash ticks.
            pygame.draw.line(surface, white, (cx - half_tick, cy + px), (cx + half_tick, cy + px), 1)
            pygame.draw.line(surface, white, (cx - half_tick, cy - px), (cx + half_tick, cy - px), 1)

        if len(px_dists) >= 3:
            idx_a = min(2, len(px_dists) - 1)
            idx_b = min(5, len(px_dists) - 1)
            for idx in sorted({idx_a, idx_b}):
                rx = max(1, px_dists[idx])
                oval_rect = pygame.Rect(0, 0, rx * 2, outer_r * 2)
                oval_rect.center = (cx, cy)
                pygame.draw.ellipse(surface, white, oval_rect, 1)

        footer_bg = pygame.Rect(rect.left, max(rect.top, footer_rect.top - 1), rect.width, min(rect.bottom - max(rect.top, footer_rect.top - 1), footer_rect.height + 3))
        pygame.draw.rect(surface, (0, 0, 0), footer_bg, 0)
        surface.blit(footer, footer_rect)

    def render(self, surface, rect, is_primary: bool, context: FormatContext) -> None:
        self._set_popup_anchor_portal_index(getattr(context, "portal_index", None))
        prev_clip = surface.get_clip()
        surface.set_clip(rect)
        surface.fill((0, 0, 0), rect)
        if is_primary and self._is_vsd():
            self._service_vsd_pending_actions()

        if not is_primary:
            if self._is_vsd():
                self._draw_vsd_subportal(surface, rect)
            else:
                self._draw_hsd_subportal(surface, rect)
            pygame.draw.rect(surface, (0, 255, 255), rect, 1)
            surface.set_clip(prev_clip)
            return

        if self._is_vsd():
            self._draw_vsd_symbology(surface, rect)
            self._draw_vsd_tracks(surface, rect)
            if is_primary:
                self._draw_osb_labels(surface, rect, context)
                self._draw_t2_l3_popup(surface, rect, context)
            pygame.draw.rect(surface, (0, 255, 255), rect, 1)
            surface.set_clip(prev_clip)
            return

        state = self._state()
        dclt_state = self._ensure_dclt_state()
        popup_rect: Optional[pygame.Rect] = None
        if bool(dclt_state.get("dclt_menu_open", False)):
            popup_rect = self._dclt_popup_rect(rect)
        draw_popup_in_primary_pass = popup_rect is not None and rect.height < int(7 * DPI) - 1
        # MAP currently disabled by request.
        state["map_on"] = False

        gray = (128, 128, 128)
        white = (255, 255, 255)
        map_on = bool(state.get("map_on", False))
        basic_sym_color = white if map_on else gray
        border_rect = self._hsd_border_rect(rect)
        if border_rect.width > 0 and border_rect.height > 0:
            pygame.draw.rect(surface, basic_sym_color, border_rect, 1)

        pan_x_px, pan_y_px = self._kbd_pan_offset_px()
        center = (
            rect.centerx + int(round(pan_x_px)),
            rect.centery + int(round(0.875 * DPI + pan_y_px)),
        )
        heading_deg = self._read_heading_deg()
        base_range_nm = self._range_nm()
        zoom_scale = self._kbd_zoom_scale(base_range_nm)
        range_nm = self._effective_range_nm(base_range_nm)
        # Map zoom follows HSD zoom by sampling at effective range.
        self._draw_hsd_map(surface, rect, center, range_nm, heading_deg, zoom_scale)
        if border_rect.width > 0 and border_rect.height > 0:
            pygame.draw.rect(surface, basic_sym_color, border_rect, 1)

        for diameter_in in (8.0, 6.0, 4.0, 2.0):
            radius = max(1, int(round(((diameter_in * DPI) / 2.0) * zoom_scale)))
            pygame.draw.circle(surface, basic_sym_color, center, radius, 1)

        # Draw additional range rings beyond 8in:
        # each ring doubles the previous range (e.g., 20 -> 40 -> 80 ...),
        # and is shown while any part of the page can see beyond that range.
        outer8_radius_px = float(4.0 * DPI) * zoom_scale
        max_visible_radius_px = 0.0
        for cx, cy in (
            (rect.left, rect.top),
            (rect.right, rect.top),
            (rect.left, rect.bottom),
            (rect.right, rect.bottom),
        ):
            d = math.hypot(float(center[0] - cx), float(center[1] - cy))
            if d > max_visible_radius_px:
                max_visible_radius_px = d
        extra_mult = 2.0
        extra_ring_mults: List[float] = []
        # Hard cap prevents pathological draw loops when center is far off-page.
        for _ in range(12):
            r_px = float(outer8_radius_px) * float(extra_mult)
            if r_px >= max_visible_radius_px:
                break
            pygame.draw.circle(surface, basic_sym_color, center, max(1, int(round(r_px))), 1)
            extra_ring_mults.append(float(extra_mult))
            extra_mult *= 2.0

        show_hdg = bool(dclt_state.get("dclt_show_hdg", True))
        show_rng_marks = bool(dclt_state.get("dclt_show_rng_marks", True))
        r_four = (2.0 * DPI) * zoom_scale
        tick_len = (0.25 * DPI) * zoom_scale
        label_font = get_font(14)
        if show_hdg:
            # White rotating 4-inch ring tick marks and heading labels.
            tick_color = basic_sym_color
            for world_deg in range(0, 360, 10):
                display_deg = (float(world_deg) - heading_deg) % 360.0
                if world_deg % 30 == 0:
                    text = "360" if world_deg == 0 else str(world_deg)
                    # Push heading numbers farther outboard.
                    tx, ty = self._polar_from_north(center, r_four - tick_len + 2.0, display_deg)
                    surf = label_font.render(text, True, tick_color)
                    tr = surf.get_rect(center=(tx, ty))
                    surface.blit(surf, tr)
                else:
                    # Contract tick marks from the outside by 4px.
                    p0 = self._polar_from_north(center, r_four - 4.0, display_deg)
                    p1 = self._polar_from_north(center, r_four - tick_len, display_deg)
                    pygame.draw.line(surface, tick_color, p0, p1, 1)

            # White vertical line centered on the top of the 4-inch circle.
            top_x = center[0]
            top_y = int(round(center[1] - r_four))
            vlen = int(round(0.375 * DPI))
            half_vlen = vlen // 2
            pygame.draw.line(surface, white, (top_x, top_y - half_vlen), (top_x, top_y + half_vlen), 1)

        if show_rng_marks:
            # Range labels at 30 deg from top on the 4/6/8-inch circles.
            ring_labels = [
                (4.0, self._format_range_label(base_range_nm * 0.5)),
                (6.0, str(int(math.floor(base_range_nm * 0.75)))),
                (8.0, self._format_range_label(base_range_nm)),
            ]
            for diameter_in, txt in ring_labels:
                radius = ((diameter_in / 2.0) * DPI) * zoom_scale
                lx, ly = self._polar_from_north(center, radius, 30.0)
                surf = label_font.render(txt, True, white)
                lr = surf.get_rect(center=(lx, ly))
                surface.blit(surf, lr)

            for mult in extra_ring_mults:
                radius = float(outer8_radius_px) * float(mult)
                txt = self._format_range_label(float(base_range_nm) * float(mult))
                lx, ly = self._polar_from_north(center, radius, 30.0)
                surf = label_font.render(txt, True, white)
                lr = surf.get_rect(center=(lx, ly))
                surface.blit(surf, lr)

        if bool(dclt_state.get("dclt_ears_on", False)):
            self._draw_hsd_sar_ears(
                surface,
                center,
                range_nm,
                heading_deg,
                zoom_scale,
                border_rect if border_rect.width > 0 and border_rect.height > 0 else None,
            )

        if bool(dclt_state.get("dclt_nav_on", True)):
            # TACAN/VOR navaids from DATA/navaids.csv in HSD space.
            self._draw_hsd_navaid_markers(
                surface,
                center,
                range_nm,
                heading_deg,
                border_rect if border_rect.width > 0 and border_rect.height > 0 else None,
            )
        # Optional live ADS-B contacts (UNKNOWN AIR symbols) in HSD space.
        adsb_items = self._draw_hsd_adsb_contacts(
            surface,
            center,
            range_nm,
            border_rect if border_rect.width > 0 and border_rect.height > 0 else None,
        )

        # Center cyan aircraft icon (STATUS BAR Aircraft.png), 0.6in wide.
        icon_w = max(1, int(round(0.6 * DPI)))
        icon_h = icon_w
        aircraft_icon = self._get_cyan_aircraft_icon((icon_w, icon_h))
        if aircraft_icon is not None:
            ir = aircraft_icon.get_rect(center=center)
            surface.blit(aircraft_icon, ir)

        if border_rect.width > 0 and border_rect.height > 0:
            self._update_hsd_secondary_cursor_tracking(border_rect, center, adsb_items)
            self._draw_hsd_secondary_cursor(surface, border_rect)
            self._draw_toi_marker(surface, border_rect, center, range_nm, heading_deg)

        if is_primary:
            self._draw_osb_labels(surface, rect, context)
            self._draw_t2_l3_popup(surface, rect, context)

        # In 5x5/10x5, draw popup now so bottom is clipped/covered by subportals.
        # In 5x7/10x7, popup is drawn in a post-subportal overlay pass.
        if draw_popup_in_primary_pass and popup_rect is not None:
            surface.set_clip(popup_rect)
            self._draw_dclt_popup(surface, popup_rect, context)

        pygame.draw.rect(surface, (0, 255, 255), rect, 1)
        surface.set_clip(prev_clip)

    def render_post_subportal_overlay(self, surface: pygame.Surface, rect: pygame.Rect, context: FormatContext) -> None:
        self._set_popup_anchor_portal_index(getattr(context, "portal_index", None))
        # Keep subportal tabs visible in layout logic, but ensure DCLT can sit above them.
        if self._is_vsd():
            return
        dclt_state = self._ensure_dclt_state()
        if not bool(dclt_state.get("dclt_menu_open", False)):
            return
        if rect.height < int(7 * DPI) - 1:
            return
        popup_rect = self._dclt_popup_rect(rect)
        prev_clip = surface.get_clip()
        surface.set_clip(popup_rect)
        self._draw_dclt_popup(surface, popup_rect, context)
        surface.set_clip(prev_clip)

    def on_click(self, pos: Tuple[int, int], rect: pygame.Rect, context: FormatContext) -> bool:
        self._set_popup_anchor_portal_index(getattr(context, "portal_index", None))
        if self._handle_t2_l3_popup_click(pos, rect):
            return True
        if self._is_vsd():
            return False
        dclt_state = self._ensure_dclt_state()
        if bool(dclt_state.get("dclt_menu_open", False)):
            popup_rect = self._dclt_popup_rect(rect)
            if not popup_rect.collidepoint(pos):
                return False
            cell = self._popup_cell_at_pos(pos, popup_rect)
            if cell is None:
                return True
            return bool(self._handle_dclt_popup_cell_click(cell))
        border_rect = self._hsd_border_rect(rect)
        state = self._state()
        state["hsd_secondary_track_id"] = None
        state["hsd_secondary_track_active"] = False
        state["hsd_secondary_fusion_id"] = ""
        state["hsd_secondary_confidence"] = 0.0
        state["hsd_secondary_track_data"] = {}
        state["hsd_secondary_last_printed_id"] = ""
        state["hsd_secondary_lock_pending"] = False
        if border_rect.width <= 0 or border_rect.height <= 0:
            return False
        if border_rect.collidepoint(pos):
            self._set_hsd_secondary_cursor_from_click(pos, border_rect)
            return True
        return False

    def on_right_click(self, pos: Tuple[int, int], rect: pygame.Rect, context: FormatContext) -> bool:
        if self._is_vsd():
            return False
        border_rect = self._hsd_border_rect(rect)
        if border_rect.width <= 0 or border_rect.height <= 0:
            return False
        if border_rect.collidepoint(pos):
            self._clear_hsd_secondary_cursor()
            return True
        return False

    def on_osb(self, label: str, context: FormatContext) -> bool:
        self._set_popup_anchor_portal_index(getattr(context, "portal_index", None))
        state = self._state()
        dclt_state = self._ensure_dclt_state()
        if label == "R5":
            self._close_t2_l3_popups()
            is_open = bool(dclt_state.get("dclt_menu_open", False))
            dclt_state["dclt_menu_open"] = not is_open
            if not bool(dclt_state.get("dclt_menu_open", False)):
                dclt_state["dclt_cat_menu_open"] = False
                dclt_state["dclt_submenu"] = ""
                dclt_state["dclt_data_selected"] = ""
                dclt_state["dclt_data_input"] = ""
            return True
        if label == "T1":
            context.request_vded(context.portal_index, "MENU")
            return True
        if label == "T2":
            dclt_state["dclt_menu_open"] = False
            dclt_state["dclt_cat_menu_open"] = False
            dclt_state["dclt_submenu"] = ""
            is_open = bool(state.get("t2_menu_open", False))
            state["t2_menu_open"] = not is_open
            state["l3_menu_open"] = False
            return True
        if self._is_vsd():
            if label == "L3":
                now_ms = int(pygame.time.get_ticks())
                state["vsd_l3_pending_toggle_due_ms"] = int(now_ms + int(self._VSD_L3_FLASH_DELAY_MS))
                return True
            if label in {"T5", "L4", "L5"}:
                return True
            return False
        if bool(dclt_state.get("dclt_menu_open", False)) and self._dclt_covers_osb_label(label):
            # Let popup hit-testing handle this click via on_click.
            return False
        if label == "L1":
            self._adjust_range_nm(+1)
            return True
        if label == "L2":
            self._adjust_range_nm(-1)
            return True
        if label == "L3":
            dclt_state["dclt_menu_open"] = False
            dclt_state["dclt_cat_menu_open"] = False
            dclt_state["dclt_submenu"] = ""
            is_open = bool(state.get("l3_menu_open", False))
            state["l3_menu_open"] = not is_open
            state["t2_menu_open"] = False
            return True
        if label == "L4":
            state["map_on"] = False
            return True
        if label == "L5":
            state["blob_on"] = not bool(state.get("blob_on", False))
            return True
        if label == "L6":
            if self._atk_selected():
                self._commit_atk_input()
            else:
                self._set_atk_selected(True)
                self._set_atk_input("")
            return True
        if label == "R3":
            state["mk_on"] = not bool(state.get("mk_on", False))
            return True
        if label == "R1":
            state["kbd_zoom_scale"] = 1.0
            state["kbd_pan_x_px"] = 0.0
            state["kbd_pan_y_px"] = 0.0
            return True
        if label == "R6":
            state["atk_on"] = not bool(state.get("atk_on", False))
            return True
        if label in {"T4", "T5", "R1", "R2", "R4"}:
            return True
        return False

    def osb_is_interactive(self, label: str) -> bool:
        if self._is_vsd():
            return label in {"T1", "T2", "T5", "L3"}
        if label == "L4":
            return False
        if label in {"R2", "R4"}:
            return False
        return True

    def suppress_subportals(self) -> bool:
        return False

    def get_t1_override(self, system_mode: str) -> Optional[List[Tuple[str, Tuple[int, int, int]]]]:
        if self._is_vsd():
            return None
        return None

    def t1_opens_menu(self) -> bool:
        if self._is_vsd():
            return True
        return not bool(self._ensure_dclt_state().get("dclt_menu_open", False))

    def on_key(self, key: str) -> bool:
        dclt_state = self._ensure_dclt_state()
        if bool(dclt_state.get("dclt_menu_open", False)) and self._apply_dclt_key(key):
            return True
        if self._is_vsd():
            return False
        if not self._atk_selected():
            return False
        token = str(key).upper().strip()
        if token in {"ENTER", "RETURN", "KP_ENTER"}:
            self._commit_atk_input()
            return True
        if token in {"KP_BACK", "BACKSPACE", "BACK"}:
            self._apply_atk_key("BACK")
            return True
        if token in {"KP_0", "KP_1", "KP_2", "KP_3", "KP_4", "KP_5", "KP_6", "KP_7", "KP_8", "KP_9"}:
            self._apply_atk_key(token)
            return True
        if len(token) == 1 and token.isdigit():
            self._apply_atk_key(token)
            return True
        return False
