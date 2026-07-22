from formats import *  # noqa: F401,F403


class Asr1Format(FormatBase):
    name: str = "ASR1"
    _terrain_tile_cache: Dict[Tuple[int, int, int], Any] = {}
    _terrain_tile_cache_lock = threading.Lock()
    _terrain_tile_cache_max = 512
    _capture_history_bounds: List[object] = []
    _capture_history_max: int = 64
    _wx_api_url: str = "https://api.rainviewer.com/public/weather-maps.json"
    _wx_tile_size: int = 512
    _wx_color: int = 0
    _wx_options: str = "1_1"
    _wx_meta_lock = threading.Lock()
    _wx_meta_last_fetch_s: float = 0.0
    _wx_meta_retry_after_s: float = 0.0
    _wx_frame_base_url: str = ""
    _wx_tile_lock = threading.Lock()
    _wx_tile_bytes_cache: Dict[Tuple[str, int, int, int], Optional[bytes]] = {}
    _wx_tile_surface_cache: Dict[Tuple[str, int, int, int], pygame.Surface] = {}
    _wx_tile_pending: Set[Tuple[str, int, int, int]] = set()
    _wx_tile_queue: deque = deque()
    _wx_workers_started: bool = False
    _wx_tile_cache_max: int = 768

    def __init__(self) -> None:
        self._res_value: str = "1"
        self._show_res_popup: bool = False
        self._mode_value: str = "NONE"
        self._show_mode_popup: bool = False
        self._show_cntl_popup: bool = False
        self._xmit_phase: str = "idle"
        self._xmit_start_ms: int = 0
        self._xmit_acquire_ms: int = 0
        self._xmit_process_ms: int = 0
        self._overlay_on: bool = False
        self._show_overlay_popup: bool = False
        self._none_range_nm: float = 15.0
        self._none_gmti_center_deg: float = 0.0
        self._none_gmti_top_ratio: float = 1.0
        self._capture_surface: Optional[pygame.Surface] = None
        self._capture_base_surface: Optional[pygame.Surface] = None
        self._capture_bounds: Optional[Tuple[float, float, float, float]] = None  # min_lon, min_lat, max_lon, max_lat
        self._capture_center_latlon: Optional[Tuple[float, float]] = None
        self._capture_mpp: float = 1.0
        self._capture_rotation_deg: float = 0.0
        self._capture_draw_zoom: float = 1.0
        self._capture_draw_pan_x: float = 0.0
        self._capture_draw_pan_y: float = 0.0
        self._capture_auto_gain: float = 6.0
        self._capture_auto_gamma: float = 0.85
        self._capture_auto_shadow: float = 0.12
        self._view_zoom: float = 1.0
        self._view_pan_x_px: float = 0.0
        self._view_pan_y_px: float = 0.0
        self._gain_value: float = 6.0
        self._gamma_value: float = 0.85
        self._shadow_value: float = 0.12
        self._captured_portal_surface: Optional[pygame.Surface] = None
        self._last_primary_rect: Optional[pygame.Rect] = None
        self._cntl_selected_field: str = ""
        self._cntl_input_by_field: Dict[str, str] = {"gain": "", "gamma": "", "shadow": ""}
        self._fetch_lock = threading.Lock()
        self._fetch_request_id: int = 0
        self._fetch_ready_payload: Optional[Dict[str, object]] = None
        self._fetch_worker_error: str = ""
        self._wx_overlay_cache_surface: Optional[pygame.Surface] = None
        self._wx_overlay_cache_key: Optional[Tuple[object, ...]] = None
        self._wx_overlay_cache_ms: int = 0
        self._road_lock = threading.Lock()
        self._road_segments: List[Dict[str, object]] = []
        self._road_adjacency: Dict[int, List[Tuple[int, int]]] = {}
        self._road_center: Optional[Tuple[float, float]] = None
        self._road_radius_m: float = 0.0
        self._road_last_fetch_s: float = 0.0
        self._road_fetch_inflight: bool = False
        self._road_generation: int = 0
        self._road_last_error_s: float = 0.0
        self._sim_rng = random.Random(35051)
        self._sim_vehicles: List[Dict[str, object]] = []
        self._sim_last_ms: int = 0
        self._sim_network_generation: int = -1

    @staticmethod
    def _asr_runtime_state() -> Dict[str, object]:
        raw = ASR1_STATE if isinstance(ASR1_STATE, dict) else {}
        return raw

    def _radar_fail_active(self) -> bool:
        state = self._asr_runtime_state()
        if bool(state.get("radar_fail", False)):
            return True
        status = str(state.get("radar_status", "")).upper().strip()
        return status in {"FAIL", "FN", "DEGD", "OT", "INOP"}

    def _draw_radar_fail_overlay(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        white = (255, 255, 255)
        red = (255, 0, 0)
        cyan = (0, 255, 255)
        cx, cy = rect.center
        arm = max(14, int(round(min(rect.width, rect.height) * 0.16)))
        inner = max(5, int(round(arm * 0.32)))
        width = max(2, int(round(arm * 0.10)))
        points = [
            (cx, cy - arm),
            (cx + inner, cy - inner),
            (cx + arm, cy),
            (cx + inner, cy + inner),
            (cx, cy + arm),
            (cx - inner, cy + inner),
            (cx - arm, cy),
            (cx - inner, cy - inner),
        ]
        pygame.draw.polygon(surface, red, points, width)
        pygame.draw.line(surface, white, (cx - arm, cy - arm), (cx + arm, cy + arm), width)
        pygame.draw.line(surface, white, (cx + arm, cy - arm), (cx - arm, cy + arm), width)
        font = get_font(24)
        status = str(self._asr_runtime_state().get("radar_status", "FAIL")).upper().strip() or "FAIL"
        label = "RADAR FAIL" if status in {"FAIL", "FN", "DEGD", "OT", "INOP"} else f"RADAR {status}"
        surf = font.render(label, True, white)
        r = surf.get_rect(centerx=cx, top=cy + arm + 12)
        pygame.draw.rect(surface, (0, 0, 0), r.inflate(8, 4), 0)
        surface.blit(surf, r)
        sub_font = get_font(14)
        sub = sub_font.render("ASR MALTESE CROSS", True, cyan)
        sr = sub.get_rect(centerx=cx, top=r.bottom + 4)
        pygame.draw.rect(surface, (0, 0, 0), sr.inflate(8, 4), 0)
        surface.blit(sub, sr)

    def _draw_asr_hotas_status(self, surface: pygame.Surface, image_rect: pygame.Rect) -> None:
        state = self._asr_runtime_state()
        flags: List[str] = []
        nts_blank = bool(state.get("nts_symbology_blank", False))
        if not nts_blank:
            if bool(state.get("spnt_tgt", False)):
                flags.append("SPNT TGT")
            if bool(state.get("nts_designated", False)):
                kind = str(state.get("nts_kind", "")).upper().strip()
                flags.append(f"{kind} NTS" if kind in {"AA", "AS"} else "NTS")
        if bool(state.get("expand_mode", False)):
            flags.append("EXP")
        if nts_blank:
            flags.append("NTS BLANK")
        if bool(state.get("tflir_slew_control", False)):
            flags.append("TFLIR SLEW")
        if len(flags) <= 0:
            return
        font = get_font(15)
        text = "  ".join(flags[:4])
        surf = font.render(text, True, (0, 255, 0))
        r = surf.get_rect(centerx=image_rect.centerx, top=image_rect.top + 8)
        pygame.draw.rect(surface, (0, 0, 0), r.inflate(8, 4), 0)
        surface.blit(surf, r)

    def _resolution_mpp(self) -> float:
        try:
            val = int(str(self._res_value).strip())
        except Exception:
            val = 1
        val = max(1, min(6, val))
        # Resolution controls requested horizontal capture width in NM.
        # RES1 ~= 0.2 NM and RES6 ~= 20.0 NM across the ASR capture width.
        width_nm_by_res = {
            1: 0.2,
            2: 0.5,
            3: 1.2,
            4: 2.8,
            5: 5.5,
            6: 20.0,
        }
        width_nm = float(width_nm_by_res.get(int(val), 0.2))
        sample_w_px = max(1.0, float(int(round(3.0 * DPI))))
        return float(width_nm * 1852.0 / sample_w_px)

    @staticmethod
    def _read_ownship_lat_lon() -> Optional[Tuple[float, float]]:
        snap = TSD_ADSB_STATE if isinstance(TSD_ADSB_STATE, dict) else {}
        lat = Tsd1Format._safe_float(snap.get("lat"))
        lon = Tsd1Format._safe_float(snap.get("lon"))
        if lat is None or lon is None:
            geo = snap.get("geo")
            if isinstance(geo, dict):
                lat = Tsd1Format._safe_float(geo.get("lat"))
                lon = Tsd1Format._safe_float(geo.get("lon"))
        if lat is None or lon is None:
            return None
        return float(lat), float(lon)

    def _center_for_capture(self) -> Optional[Tuple[float, float, float]]:
        own = self._read_ownship_lat_lon()
        own_heading = 0.0
        try:
            own_heading = float(TWD_STATE.get("heading_deg", 0.0)) % 360.0
        except Exception:
            own_heading = 0.0
        toi = TSD_TOI_STATE if isinstance(TSD_TOI_STATE, dict) else {}
        if bool(toi.get("active", False)):
            try:
                lat = float(toi.get("lat"))
                lon = float(toi.get("lon"))
                rel = 0.0
                if own is not None:
                    brg, _ = Tsd1Format._bearing_and_distance_nm(float(own[0]), float(own[1]), float(lat), float(lon))
                    rel = (float(brg) - float(own_heading)) % 360.0
                return float(lat), float(lon), float(rel)
            except Exception:
                pass
        if own is None:
            return None
        return float(own[0]), float(own[1]), 0.0

    @staticmethod
    def _latlon_to_world_px(lat: float, lon: float, zoom: int) -> Tuple[float, float]:
        lat_clamped = max(-85.05112878, min(85.05112878, float(lat)))
        lon_wrapped = ((float(lon) + 180.0) % 360.0) - 180.0
        scale = float(256 * (2 ** int(zoom)))
        x = ((lon_wrapped + 180.0) / 360.0) * scale
        sin_lat = math.sin(math.radians(lat_clamped))
        y = (0.5 - (math.log((1.0 + sin_lat) / max(1e-9, (1.0 - sin_lat))) / (4.0 * math.pi))) * scale
        return float(x), float(y)

    @staticmethod
    def _world_px_to_latlon(x: float, y: float, zoom: int) -> Tuple[float, float]:
        scale = float(256 * (2 ** int(zoom)))
        lon = (float(x) / scale) * 360.0 - 180.0
        n = math.pi - (2.0 * math.pi * float(y) / scale)
        lat = math.degrees(math.atan(math.sinh(n)))
        return float(lat), float(lon)

    @classmethod
    def _fetch_terrain_tile(cls, z: int, x: int, y: int) -> Optional[Any]:
        if Image is None:
            return None
        key = (int(z), int(x), int(y))
        with cls._terrain_tile_cache_lock:
            cached = cls._terrain_tile_cache.get(key)
            if cached is not None:
                return cached.copy()
        url = f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{int(z)}/{int(x)}/{int(y)}.png"
        req = urllib.request.Request(url, headers={"User-Agent": "F35-PCD-ASR/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=12.0) as resp:
                data = resp.read()
            img = Image.open(io.BytesIO(data)).convert("RGB")
        except Exception:
            return None
        with cls._terrain_tile_cache_lock:
            cls._terrain_tile_cache[key] = img.copy()
            if len(cls._terrain_tile_cache) > int(cls._terrain_tile_cache_max):
                try:
                    oldest = next(iter(cls._terrain_tile_cache.keys()))
                    cls._terrain_tile_cache.pop(oldest, None)
                except Exception:
                    pass
        return img

    @classmethod
    def _wx_zoom_for_range(cls, range_nm: float) -> int:
        try:
            v = float(range_nm)
        except Exception:
            v = 20.0
        if v <= 20.0:
            return 7
        if v <= 60.0:
            return 6
        return 5

    @classmethod
    def _wx_frame_url(cls) -> Optional[str]:
        now_s = time.monotonic()
        with cls._wx_meta_lock:
            cached = str(cls._wx_frame_base_url).strip()
            last_fetch = float(cls._wx_meta_last_fetch_s)
            retry_after = float(cls._wx_meta_retry_after_s)
            if cached != "" and (now_s - last_fetch) < 120.0:
                return cached
            if now_s < retry_after:
                return cached if cached != "" else None
            cls._wx_meta_last_fetch_s = now_s
        new_url = ""
        try:
            req = urllib.request.Request(cls._wx_api_url, headers={"User-Agent": "F35-PCD-ASR/1.0"})
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                payload = resp.read()
            data = json.loads(payload.decode("utf-8", errors="replace"))
            host = str(data.get("host", "")).strip().rstrip("/")
            radar = data.get("radar", {})
            past = radar.get("past", []) if isinstance(radar, dict) else []
            if host != "" and isinstance(past, list) and len(past) > 0 and isinstance(past[-1], dict):
                frame_path = str(past[-1].get("path", "")).strip()
                if frame_path != "":
                    if frame_path.startswith("/"):
                        new_url = f"{host}{frame_path}"
                    else:
                        new_url = f"{host}/{frame_path}"
        except Exception:
            new_url = ""
        with cls._wx_meta_lock:
            if new_url != "":
                changed = str(cls._wx_frame_base_url).strip() != str(new_url).strip()
                cls._wx_frame_base_url = new_url
                cls._wx_meta_retry_after_s = 0.0
                if changed:
                    with cls._wx_tile_lock:
                        cls._wx_tile_bytes_cache.clear()
                        cls._wx_tile_surface_cache.clear()
                        cls._wx_tile_pending.clear()
                        cls._wx_tile_queue.clear()
            else:
                cls._wx_meta_retry_after_s = now_s + 8.0
            return str(cls._wx_frame_base_url).strip() or None

    @classmethod
    def _wx_start_workers(cls) -> None:
        with cls._wx_tile_lock:
            if bool(cls._wx_workers_started):
                return
            cls._wx_workers_started = True
        for idx in range(2):
            th = threading.Thread(target=cls._wx_worker_loop, name=f"ASR1WXTile-{idx + 1}", daemon=True)
            th.start()

    @classmethod
    def _wx_worker_loop(cls) -> None:
        while True:
            key: Optional[Tuple[str, int, int, int]] = None
            with cls._wx_tile_lock:
                if len(cls._wx_tile_queue) > 0:
                    raw = cls._wx_tile_queue.popleft()
                    if isinstance(raw, tuple) and len(raw) == 4:
                        key = (str(raw[0]), int(raw[1]), int(raw[2]), int(raw[3]))
            if key is None:
                time.sleep(0.02)
                continue
            frame_base, z, x, y = key
            raw_data: Optional[bytes] = None
            try:
                tile_url = f"{frame_base}/{int(cls._wx_tile_size)}/{int(z)}/{int(x)}/{int(y)}/{int(cls._wx_color)}/{cls._wx_options}.png"
                req = urllib.request.Request(tile_url, headers={"User-Agent": "F35-PCD-ASR/1.0"})
                with urllib.request.urlopen(req, timeout=4.0) as resp:
                    body = resp.read()
                if len(body) > 0:
                    raw_data = bytes(body)
            except Exception:
                raw_data = None
            with cls._wx_tile_lock:
                cls._wx_tile_pending.discard(key)
                cls._wx_tile_bytes_cache[key] = raw_data
                if raw_data is None:
                    cls._wx_tile_surface_cache.pop(key, None)
                while len(cls._wx_tile_bytes_cache) > int(cls._wx_tile_cache_max):
                    try:
                        old = next(iter(cls._wx_tile_bytes_cache.keys()))
                    except Exception:
                        break
                    cls._wx_tile_bytes_cache.pop(old, None)
                    cls._wx_tile_surface_cache.pop(old, None)
                    cls._wx_tile_pending.discard(old)

    @classmethod
    def _wx_queue_tile(cls, frame_base: str, z: int, x: int, y: int) -> None:
        key = (str(frame_base), int(z), int(x), int(y))
        with cls._wx_tile_lock:
            if key in cls._wx_tile_bytes_cache or key in cls._wx_tile_pending:
                return
            cls._wx_tile_pending.add(key)
            cls._wx_tile_queue.append(key)
        cls._wx_start_workers()

    @classmethod
    def _wx_tile_surface(cls, frame_base: str, z: int, x: int, y: int) -> Optional[pygame.Surface]:
        key = (str(frame_base), int(z), int(x), int(y))
        raw_data: Optional[bytes]
        with cls._wx_tile_lock:
            cached = cls._wx_tile_surface_cache.get(key)
            if isinstance(cached, pygame.Surface):
                return cached
            if key not in cls._wx_tile_bytes_cache:
                raw_data = None
            else:
                raw_data = cls._wx_tile_bytes_cache.get(key)
        if raw_data is None:
            cls._wx_queue_tile(str(frame_base), int(z), int(x), int(y))
            return None
        try:
            surf = pygame.image.load(io.BytesIO(raw_data)).convert_alpha()
        except Exception:
            return None
        if surf.get_width() != int(cls._wx_tile_size) or surf.get_height() != int(cls._wx_tile_size):
            try:
                surf = pygame.transform.smoothscale(surf, (int(cls._wx_tile_size), int(cls._wx_tile_size)))
            except Exception:
                pass
        with cls._wx_tile_lock:
            cls._wx_tile_surface_cache[key] = surf
            while len(cls._wx_tile_surface_cache) > 320:
                try:
                    old = next(iter(cls._wx_tile_surface_cache.keys()))
                except Exception:
                    break
                cls._wx_tile_surface_cache.pop(old, None)
        return surf

    @classmethod
    def _wx_sample_rgba(cls, frame_base: str, z: int, lat: float, lon: float) -> Optional[Tuple[int, int, int, int]]:
        lat_clamped = max(-85.05112878, min(85.05112878, float(lat)))
        lon_wrapped = ((float(lon) + 180.0) % 360.0) - 180.0
        tile_size = float(cls._wx_tile_size)
        scale = tile_size * float(2 ** int(z))
        wx = ((lon_wrapped + 180.0) / 360.0) * scale
        sin_lat = math.sin(math.radians(lat_clamped))
        wy = (0.5 - (math.log((1.0 + sin_lat) / max(1e-9, (1.0 - sin_lat))) / (4.0 * math.pi))) * scale
        tx = int(math.floor(wx / tile_size))
        ty = int(math.floor(wy / tile_size))
        max_tile = (2 ** int(z)) - 1
        if ty < 0 or ty > max_tile:
            return None
        tx_wrapped = tx % (2 ** int(z))
        surf = cls._wx_tile_surface(str(frame_base), int(z), int(tx_wrapped), int(ty))
        if surf is None:
            return None
        px = int(wx - (float(tx) * tile_size))
        py = int(wy - (float(ty) * tile_size))
        px = max(0, min(surf.get_width() - 1, int(px)))
        py = max(0, min(surf.get_height() - 1, int(py)))
        try:
            c = surf.get_at((px, py))
            return int(c.r), int(c.g), int(c.b), int(c.a)
        except Exception:
            return None

    @staticmethod
    def _wx_quantize_color(r: int, g: int, b: int, a: int) -> Optional[Tuple[int, int, int, int]]:
        if int(a) <= 6:
            return None
        rr = int(max(0, min(255, int(r))))
        gg = int(max(0, min(255, int(g))))
        bb = int(max(0, min(255, int(b))))
        aa = int(max(0, min(255, int(a))))
        if rr < 8 and gg < 8 and bb < 8:
            return None
        if aa < 16:
            return None
        # Convert tile color into a simple 0..1 intensity score.
        brightness = max(rr, gg, bb) / 255.0
        alpha_term = aa / 255.0
        warm_term = max(0.0, float(rr - gg)) / 255.0
        cool_term = max(0.0, float(bb - gg)) / 255.0
        score = (0.60 * brightness * alpha_term) + (0.30 * warm_term) + (0.10 * cool_term)
        score = max(0.0, min(1.0, float(score)))
        # Requested palette, low->high: cyan, green, yellow, red, pink, purple.
        palette: List[Tuple[int, int, int]] = [
            (0, 255, 255),   # cyan
            (0, 255, 0),     # green
            (255, 255, 0),   # yellow
            (255, 0, 0),     # red
            (255, 105, 180), # pink
            (180, 0, 255),   # purple
        ]
        idx = int(max(0, min(len(palette) - 1, math.floor(score * float(len(palette))))))
        col = palette[idx]
        return (int(col[0]), int(col[1]), int(col[2]), min(225, aa + 28))

    @staticmethod
    def _road_speed_kts(tags: Dict[str, object]) -> float:
        highway = str(tags.get("highway", "")).strip().lower()
        default_mph = {
            "motorway": 70.0,
            "trunk": 60.0,
            "primary": 45.0,
            "secondary": 40.0,
            "tertiary": 35.0,
            "unclassified": 30.0,
            "residential": 25.0,
            "service": 15.0,
            "living_street": 10.0,
        }.get(highway, 25.0)
        raw = str(tags.get("maxspeed", "")).strip().lower()
        if raw != "":
            m = re.search(r"([0-9]+(?:\.[0-9]+)?)", raw)
            if m is not None:
                try:
                    v = float(m.group(1))
                    if "knot" in raw or "kt" in raw:
                        return max(5.0, min(95.0, v))
                    if "mph" in raw:
                        return max(5.0, min(95.0, v * 0.868976))
                    # Assume km/h when units are absent.
                    return max(5.0, min(95.0, v * 0.539957))
                except Exception:
                    pass
        return max(5.0, min(95.0, default_mph * 0.868976))

    def _overpass_fetch_roads_async(self, lat: float, lon: float, radius_m: float) -> None:
        with self._road_lock:
            if bool(self._road_fetch_inflight):
                return
            self._road_fetch_inflight = True
        center_lat = float(lat)
        center_lon = float(lon)
        query_radius_m = max(3000.0, min(30000.0, float(radius_m)))

        def _worker() -> None:
            segments: List[Dict[str, object]] = []
            adjacency: Dict[int, List[Tuple[int, int]]] = {}
            ok = False
            try:
                overpass_query = (
                    f"[out:json][timeout:25];"
                    f"(way[\"highway\"~\"motorway|trunk|primary|motorway_link|trunk_link|primary_link\"]"
                    f"(around:{int(round(query_radius_m))},{center_lat:.6f},{center_lon:.6f}););"
                    f"(._;>;);out body;"
                )
                payload = urllib.parse.urlencode({"data": overpass_query}).encode("utf-8")
                req = urllib.request.Request(
                    "https://overpass-api.de/api/interpreter",
                    data=payload,
                    headers={"User-Agent": "F35-PCD-ASR/1.0", "Content-Type": "application/x-www-form-urlencoded"},
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
                    tags = way.get("tags", {})
                    if not isinstance(tags, dict):
                        tags = {}
                    nlist = way.get("nodes", [])
                    if not isinstance(nlist, list) or len(nlist) < 2:
                        continue
                    one_way = str(tags.get("oneway", "")).strip().lower() in {"yes", "1", "true"}
                    speed_kts = float(self._road_speed_kts(tags))
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
                        a_lat, a_lon = float(a[0]), float(a[1])
                        b_lat, b_lon = float(b[0]), float(b[1])
                        _brg, dist_nm = Tsd1Format._bearing_and_distance_nm(a_lat, a_lon, b_lat, b_lon)
                        if dist_nm <= 0.003:
                            continue
                        seg_idx = len(segments)
                        segments.append(
                            {
                                "a_id": a_id,
                                "b_id": b_id,
                                "a_lat": a_lat,
                                "a_lon": a_lon,
                                "b_lat": b_lat,
                                "b_lon": b_lon,
                                "len_nm": float(dist_nm),
                                "speed_kts": float(speed_kts),
                                "oneway": bool(one_way),
                            }
                        )
                        # dir=+1 means u:0->1 (a->b), dir=-1 means u:1->0 (b->a)
                        adjacency.setdefault(a_id, []).append((seg_idx, 1))
                        if not bool(one_way):
                            adjacency.setdefault(b_id, []).append((seg_idx, -1))
                ok = len(segments) > 0
            except Exception:
                ok = False
            with self._road_lock:
                self._road_fetch_inflight = False
                self._road_last_fetch_s = time.monotonic()
                if ok:
                    self._road_segments = segments
                    self._road_adjacency = adjacency
                    self._road_center = (float(center_lat), float(center_lon))
                    self._road_radius_m = float(query_radius_m)
                    self._road_generation += 1
                else:
                    self._road_last_error_s = time.monotonic()

        th = threading.Thread(target=_worker, name="ASR1RoadFetch", daemon=True)
        th.start()

    def _maybe_refresh_road_network(self, own_lat: float, own_lon: float, range_nm: float) -> None:
        now_s = time.monotonic()
        requested_radius_m = max(6000.0, min(30000.0, float(range_nm) * 1852.0 * 1.6))
        with self._road_lock:
            center = self._road_center
            current_radius_m = float(self._road_radius_m)
            last_fetch_s = float(self._road_last_fetch_s)
            inflight = bool(self._road_fetch_inflight)
            have_data = len(self._road_segments) > 0
        if inflight:
            return
        need_fetch = not bool(have_data)
        if isinstance(center, tuple) and len(center) == 2:
            try:
                _b, dist_nm = Tsd1Format._bearing_and_distance_nm(float(center[0]), float(center[1]), float(own_lat), float(own_lon))
                dist_m = float(dist_nm) * 1852.0
            except Exception:
                dist_m = float(requested_radius_m)
            if dist_m > max(1500.0, current_radius_m * 0.45):
                need_fetch = True
        if (now_s - last_fetch_s) > 600.0:
            need_fetch = True
        if requested_radius_m > (current_radius_m + 3000.0):
            need_fetch = True
        if need_fetch:
            self._overpass_fetch_roads_async(float(own_lat), float(own_lon), float(requested_radius_m))

    def _step_sim_vehicles(self, dt_s: float) -> None:
        if dt_s <= 0.0:
            return
        with self._road_lock:
            segments = list(self._road_segments)
            adjacency = dict(self._road_adjacency)
            generation = int(self._road_generation)
        if len(segments) <= 0:
            self._sim_vehicles = []
            self._sim_network_generation = generation
            return
        if self._sim_network_generation != generation:
            self._sim_vehicles = []
            self._sim_network_generation = generation
        target_count = max(30, min(240, int(len(segments) * 0.35)))
        while len(self._sim_vehicles) < target_count:
            seg_idx = self._sim_rng.randrange(0, len(segments))
            seg = segments[seg_idx]
            speed = float(seg.get("speed_kts", 20.0)) * self._sim_rng.uniform(0.55, 1.25)
            speed = max(4.0, min(95.0, speed))
            oneway = bool(seg.get("oneway", False))
            if oneway:
                direction = 1
            else:
                direction = 1 if self._sim_rng.random() >= 0.5 else -1
            self._sim_vehicles.append(
                {
                    "seg_idx": int(seg_idx),
                    "u": float(self._sim_rng.random()),
                    "dir": int(direction),
                    "speed_kts": float(speed),
                }
            )
        if len(self._sim_vehicles) > target_count:
            self._sim_vehicles = self._sim_vehicles[:target_count]

        for v in self._sim_vehicles:
            try:
                idx = int(v.get("seg_idx", 0))
                direction = int(v.get("dir", 1))
                u = float(v.get("u", 0.5))
                speed_kts = max(2.0, min(120.0, float(v.get("speed_kts", 20.0))))
            except Exception:
                continue
            hops = 0
            remain_nm = float(speed_kts) * max(0.0, float(dt_s)) / 3600.0
            while remain_nm > 1e-6 and hops < 6 and 0 <= idx < len(segments):
                seg = segments[idx]
                seg_len = max(1e-6, float(seg.get("len_nm", 0.0)))
                if direction >= 0:
                    avail_nm = max(0.0, (1.0 - u) * seg_len)
                    if remain_nm < avail_nm:
                        u += remain_nm / seg_len
                        remain_nm = 0.0
                        break
                    remain_nm -= avail_nm
                    exit_node = int(seg.get("b_id", 0))
                else:
                    avail_nm = max(0.0, u * seg_len)
                    if remain_nm < avail_nm:
                        u -= remain_nm / seg_len
                        remain_nm = 0.0
                        break
                    remain_nm -= avail_nm
                    exit_node = int(seg.get("a_id", 0))
                opts = list(adjacency.get(exit_node, []))
                if len(opts) <= 0:
                    direction *= -1
                    u = max(0.0, min(1.0, 1.0 if direction < 0 else 0.0))
                    hops += 1
                    continue
                if len(opts) > 1:
                    opts = [o for o in opts if int(o[0]) != int(idx)] or opts
                next_idx, next_dir = opts[self._sim_rng.randrange(0, len(opts))]
                idx = int(next_idx)
                direction = int(next_dir)
                u = 0.0 if direction >= 0 else 1.0
                hops += 1
            v["seg_idx"] = int(max(0, min(len(segments) - 1, idx)))
            v["dir"] = int(1 if direction >= 0 else -1)
            v["u"] = float(max(0.0, min(1.0, u)))

    def _sim_vehicle_positions(self, own_lat: float, own_lon: float, own_heading: float, range_nm: float, half_fov_deg: float) -> List[Tuple[float, float]]:
        now_ms = int(pygame.time.get_ticks())
        prev_ms = int(self._sim_last_ms)
        self._sim_last_ms = now_ms
        dt_s = 0.0 if prev_ms <= 0 else max(0.0, min(0.4, (float(now_ms - prev_ms) / 1000.0)))
        self._maybe_refresh_road_network(float(own_lat), float(own_lon), float(range_nm))
        self._step_sim_vehicles(float(dt_s))
        with self._road_lock:
            segments = list(self._road_segments)
        out: List[Tuple[float, float]] = []
        max_range_nm = max(0.1, float(range_nm))
        for v in self._sim_vehicles:
            try:
                idx = int(v.get("seg_idx", -1))
                if idx < 0 or idx >= len(segments):
                    continue
                seg = segments[idx]
                u = float(v.get("u", 0.0))
                lat = float(seg.get("a_lat", 0.0)) + (float(seg.get("b_lat", 0.0)) - float(seg.get("a_lat", 0.0))) * float(u)
                lon = float(seg.get("a_lon", 0.0)) + (float(seg.get("b_lon", 0.0)) - float(seg.get("a_lon", 0.0))) * float(u)
                bearing_deg, dist_nm = Tsd1Format._bearing_and_distance_nm(float(own_lat), float(own_lon), float(lat), float(lon))
                if dist_nm > max_range_nm:
                    continue
                rel_deg = ((float(bearing_deg) - float(own_heading) + 540.0) % 360.0) - 180.0
                if abs(rel_deg) > float(half_fov_deg):
                    continue
                out.append((float(rel_deg), float(dist_nm)))
            except Exception:
                continue
        return out

    def _draw_wx_mode_overlay(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        apex_x: int,
        apex_y: int,
        outer_r: float,
        half_fov_deg: float,
    ) -> None:
        own = self._read_ownship_lat_lon()
        if own is None:
            return
        frame_base = self._wx_frame_url()
        if frame_base is None or str(frame_base).strip() == "":
            return
        try:
            own_heading = float(TWD_STATE.get("heading_deg", 0.0)) % 360.0
        except Exception:
            own_heading = 0.0
        own_lat = float(own[0])
        own_lon = float(own[1])
        max_range_nm = max(0.1, float(self._none_range_nm))
        zoom = int(self._wx_zoom_for_range(max_range_nm))
        if zoom < 0:
            zoom = 0
        if zoom > 7:
            zoom = 7
        now_ms = int(pygame.time.get_ticks())
        cache_key: Tuple[object, ...] = (
            int(rect.width),
            int(rect.height),
            int(apex_x - rect.left),
            int(apex_y - rect.top),
            round(float(outer_r), 2),
            round(float(half_fov_deg), 2),
            round(float(own_lat), 3),
            round(float(own_lon), 3),
            round(float(own_heading), 1),
            round(float(max_range_nm), 2),
            int(zoom),
            str(frame_base),
        )
        if (
            isinstance(self._wx_overlay_cache_surface, pygame.Surface)
            and isinstance(self._wx_overlay_cache_key, tuple)
            and self._wx_overlay_cache_key == cache_key
            and (now_ms - int(self._wx_overlay_cache_ms)) <= 260
        ):
            surface.blit(self._wx_overlay_cache_surface, rect.topleft)
            return
        overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        dot_spacing_px = max(4.0, float(0.055 * DPI))
        ring_step_px = max(3.0, float(0.040 * DPI))
        dot_radius = max(2, int(round(0.012 * DPI)))
        ring_idx = 0
        rr = 3.0
        while rr <= float(outer_r):
            # Stagger each ring so echoes render as dots/areas instead of straight radial lines.
            if rr <= 1.0:
                ang_step_deg = float(half_fov_deg) * 2.0
            else:
                ang_step_deg = math.degrees(dot_spacing_px / max(1.0, rr))
            ang_step_deg = max(1.4, min(10.0, float(ang_step_deg)))
            phase = 0.5 * ang_step_deg if (ring_idx % 2) else 0.0
            rel = -float(half_fov_deg) + phase
            while rel <= float(half_fov_deg) + 0.001:
                frac = max(0.0, min(1.0, float(rr) / max(1.0, float(outer_r))))
                dist_nm = frac * max_range_nm
                bearing = (float(own_heading) + float(rel)) % 360.0
                lat, lon = Tsd1Format._project_lat_lon_nm(own_lat, own_lon, bearing, dist_nm)
                rgba = self._wx_sample_rgba(str(frame_base), int(zoom), float(lat), float(lon))
                if rgba is not None:
                    mapped = self._wx_quantize_color(int(rgba[0]), int(rgba[1]), int(rgba[2]), int(rgba[3]))
                    if mapped is not None:
                        rel_rad = math.radians(rel)
                        sx = int(round(float(apex_x) + (float(rr) * math.sin(rel_rad)))) - rect.left
                        sy = int(round(float(apex_y) - (float(rr) * math.cos(rel_rad)))) - rect.top
                        if 0 <= sx < rect.width and 0 <= sy < rect.height:
                            pygame.draw.circle(overlay, mapped, (int(sx), int(sy)), int(dot_radius), 0)
                rel += float(ang_step_deg)
            rr += float(ring_step_px)
            ring_idx += 1
        self._wx_overlay_cache_surface = overlay
        self._wx_overlay_cache_key = cache_key
        self._wx_overlay_cache_ms = int(now_ms)
        surface.blit(overlay, rect.topleft)

    @classmethod
    def _build_heightmap_capture(
        cls,
        center_lat: float,
        center_lon: float,
        meters_per_px: float,
        out_w: int,
        out_h: int,
    ) -> Optional[Dict[str, object]]:
        if Image is None:
            return None
        out_w = max(64, int(out_w))
        out_h = max(64, int(out_h))
        req_mpp = max(1.0, float(meters_per_px))
        auto_gain = 6.0
        auto_gamma = 0.85
        auto_shadow = 0.12
        lat_for_zoom = max(-85.0, min(85.0, float(center_lat)))
        cos_lat = max(0.15, abs(math.cos(math.radians(lat_for_zoom))))
        equator_mpp = 156543.03392804097
        zoom_f = math.log2((equator_mpp * cos_lat) / req_mpp)
        zoom = max(0, min(15, int(round(zoom_f))))
        actual_mpp = (equator_mpp * cos_lat) / float(2 ** zoom)
        sample_span_px_x = max(1.0, float(out_w) * (req_mpp / max(1e-9, actual_mpp)))
        sample_span_px_y = max(1.0, float(out_h) * (req_mpp / max(1e-9, actual_mpp)))
        cx, cy = cls._latlon_to_world_px(float(center_lat), float(center_lon), zoom)
        left = float(cx) - (sample_span_px_x * 0.5)
        right = float(cx) + (sample_span_px_x * 0.5)
        top = float(cy) - (sample_span_px_y * 0.5)
        bottom = float(cy) + (sample_span_px_y * 0.5)
        tile_size = 256
        max_tile = (2 ** zoom) - 1
        tx0 = int(math.floor(left / tile_size))
        tx1 = int(math.floor((right - 1.0) / tile_size))
        ty0 = int(math.floor(top / tile_size))
        ty1 = int(math.floor((bottom - 1.0) / tile_size))
        if tx1 < tx0 or ty1 < ty0:
            return None
        src_w = (tx1 - tx0 + 1) * tile_size
        src_h = (ty1 - ty0 + 1) * tile_size
        stitched = Image.new("RGB", (int(src_w), int(src_h)))
        for tx in range(tx0, tx1 + 1):
            wrap_x = tx % (2 ** zoom)
            for ty in range(ty0, ty1 + 1):
                if ty < 0 or ty > max_tile:
                    continue
                tile = cls._fetch_terrain_tile(zoom, wrap_x, ty)
                if tile is None:
                    continue
                px = (tx - tx0) * tile_size
                py = (ty - ty0) * tile_size
                stitched.paste(tile, (int(px), int(py)))
        crop_l = int(round(left - (tx0 * tile_size)))
        crop_t = int(round(top - (ty0 * tile_size)))
        crop_r = int(round(right - (tx0 * tile_size)))
        crop_b = int(round(bottom - (ty0 * tile_size)))
        crop_l = max(0, min(stitched.width - 1, crop_l))
        crop_t = max(0, min(stitched.height - 1, crop_t))
        crop_r = max(crop_l + 1, min(stitched.width, crop_r))
        crop_b = max(crop_t + 1, min(stitched.height, crop_b))
        cropped = stitched.crop((crop_l, crop_t, crop_r, crop_b))
        sampled = cropped.resize((out_w, out_h), Image.Resampling.BILINEAR if hasattr(Image, "Resampling") else Image.BILINEAR)
        if np is not None:
            rgb = np.asarray(sampled, dtype=np.uint8)
            heights = (rgb[:, :, 0].astype(np.float32) * 256.0 + rgb[:, :, 1].astype(np.float32) + (rgb[:, :, 2].astype(np.float32) / 256.0)) - 32768.0
            dy, dx = np.gradient(heights.astype(np.float32))
            nx = -dx
            ny = -dy
            nz = np.ones_like(heights, dtype=np.float32)
            norm = np.sqrt(nx * nx + ny * ny + nz * nz) + 1e-8
            nx /= norm
            ny /= norm
            nz /= norm
            span = max(1.0, float(np.max(heights) - np.min(heights)))
            relief = max(0.0, min(1.0, float(np.std(heights) / span) * 6.0))
            gain = max(3.0, min(16.0, 4.0 + (10.0 * relief)))
            gamma = max(0.55, min(1.3, 0.95 - (0.25 * relief)))
            shadow_floor = max(0.06, min(0.30, 0.10 + (0.15 * relief)))
            auto_gain = float(gain)
            auto_gamma = float(gamma)
            auto_shadow = float(shadow_floor)
            speckle_strength = max(0.08, min(0.55, 0.32 - (0.14 * relief)))
            multilook_blend = max(0.18, min(0.55, 0.26 + (0.20 * relief)))
            az = math.radians(90.0)
            inc = math.radians(max(8.0, min(70.0, 35.0 + (8.0 * relief))))
            lx = math.sin(az) * math.sin(inc)
            ly = math.cos(az) * math.sin(inc)
            lz = math.cos(inc)
            facing = -(nx * lx + ny * ly - nz * lz)
            facing = np.clip(facing, 0.0, 1.0)
            slope_mag = np.sqrt(dx * dx + dy * dy)
            slope_min = float(np.min(slope_mag))
            slope_span = max(1e-6, float(np.max(slope_mag) - slope_min))
            slope_term = (slope_mag - slope_min) / slope_span
            img = (0.72 * facing) + (0.28 * slope_term)
            ridge = np.abs(dx) + np.abs(dy)
            ridge_min = float(np.min(ridge))
            ridge_span = max(1e-6, float(np.max(ridge) - ridge_min))
            ridge = (ridge - ridge_min) / ridge_span
            img = (0.82 * img) + (0.18 * ridge)
            hgt, wdt = heights.shape
            mask = np.ones((hgt, wdt), dtype=np.float32)
            proj = math.tan(inc) * 1.6
            for y in range(hgt):
                horizon = -1e30
                for x in range(wdt):
                    apparent = float(heights[y, x]) - (float(x) * proj)
                    if apparent < horizon:
                        mask[y, x] = float(shadow_floor)
                    else:
                        horizon = apparent
            img *= mask
            seed = int((abs(center_lat) * 1000.0) + (abs(center_lon) * 1000.0) + (req_mpp * 101.0)) & 0xFFFFFFFF
            rng = np.random.default_rng(seed)
            noise = rng.gamma(shape=1.6, scale=1.0 / 1.6, size=img.shape).astype(np.float32)
            img = img * ((1.0 - speckle_strength) + (speckle_strength * noise))
            p = np.pad(img, 1, mode="edge")
            smooth = (
                p[:-2, :-2] + p[:-2, 1:-1] + p[:-2, 2:]
                + p[1:-1, :-2] + p[1:-1, 1:-1] + p[1:-1, 2:]
                + p[2:, :-2] + p[2:, 1:-1] + p[2:, 2:]
            ) / 9.0
            img = ((1.0 - multilook_blend) * img) + (multilook_blend * smooth.astype(np.float32))
            img = np.log1p(np.clip(img, 0.0, None) * gain)
            img_min = float(np.min(img))
            img_span = max(1e-6, float(np.max(img) - img_min))
            img = (img - img_min) / img_span
            img = np.power(np.clip(img, 0.0, 1.0), gamma)
            gray_u8 = (img * 255.0).clip(0, 255).astype(np.uint8)
            gray = Image.fromarray(gray_u8, mode="L").convert("RGB")
        else:
            pix = list(sampled.getdata())
            if len(pix) <= 0:
                return None
            heights: List[float] = []
            min_h = None
            max_h = None
            for r, g, b in pix:
                h = (float(r) * 256.0 + float(g) + (float(b) / 256.0)) - 32768.0
                heights.append(h)
                min_h = h if min_h is None else min(min_h, h)
                max_h = h if max_h is None else max(max_h, h)
            lo = float(min_h if min_h is not None else 0.0)
            hi = float(max_h if max_h is not None else 0.0)
            span = max(1.0, hi - lo)
            gray = Image.new("RGB", (out_w, out_h))
            out_pixels: List[Tuple[int, int, int]] = []
            for h in heights:
                v = int(max(0, min(255, round(((float(h) - lo) / span) * 255.0))))
                out_pixels.append((v, v, v))
            gray.putdata(out_pixels)
        top_lat, left_lon = cls._world_px_to_latlon(float(left), float(top), zoom)
        bottom_lat, right_lon = cls._world_px_to_latlon(float(right), float(bottom), zoom)
        bounds = (float(left_lon), float(bottom_lat), float(right_lon), float(top_lat))
        return {
            "image": gray,
            "bounds": bounds,
            "center": (float(center_lat), float(center_lon)),
            "mpp": float(req_mpp),
            "auto_gain": float(auto_gain),
            "auto_gamma": float(auto_gamma),
            "auto_shadow": float(auto_shadow),
        }

    def _request_capture_async(self, image_w: int, image_h: int) -> None:
        center = self._center_for_capture()
        if center is None:
            return
        center_lat, center_lon, rel_bearing_deg = center
        req_id = int(self._fetch_request_id) + 1
        self._fetch_request_id = int(req_id)
        self._fetch_ready_payload = None
        self._fetch_worker_error = ""
        req_mpp = self._resolution_mpp()

        def _worker() -> None:
            payload = self._build_heightmap_capture(center_lat, center_lon, req_mpp, int(image_w), int(image_h))
            with self._fetch_lock:
                if int(self._fetch_request_id) != int(req_id):
                    return
                if payload is None:
                    self._fetch_worker_error = "HEIGHTMAP DOWNLOAD FAILED"
                    return
                payload["rotation_deg"] = float(rel_bearing_deg)
                self._fetch_ready_payload = payload
                self._fetch_worker_error = ""

        th = threading.Thread(target=_worker, name=f"ASR1Capture-{req_id}", daemon=True)
        th.start()

    def _consume_capture_payload(self) -> None:
        with self._fetch_lock:
            payload = self._fetch_ready_payload
            self._fetch_ready_payload = None
        if not isinstance(payload, dict):
            return
        surf = payload.get("surface")
        pil_image = payload.get("image")
        bounds = payload.get("bounds")
        center = payload.get("center")
        rotation_deg = payload.get("rotation_deg")
        auto_gain = payload.get("auto_gain")
        auto_gamma = payload.get("auto_gamma")
        auto_shadow = payload.get("auto_shadow")
        if isinstance(surf, pygame.Surface):
            self._capture_surface = surf.copy()
        elif Image is not None and pil_image is not None and hasattr(pil_image, "tobytes") and hasattr(pil_image, "size") and hasattr(pil_image, "mode"):
            try:
                mode = str(pil_image.mode)
                data = pil_image.tobytes()
                self._capture_surface = pygame.image.fromstring(data, pil_image.size, mode).convert()
            except Exception:
                pass
        if isinstance(bounds, tuple) and len(bounds) == 4:
            try:
                self._capture_bounds = (float(bounds[0]), float(bounds[1]), float(bounds[2]), float(bounds[3]))
            except Exception:
                self._capture_bounds = None
        if isinstance(center, tuple) and len(center) == 2:
            try:
                self._capture_center_latlon = (float(center[0]), float(center[1]))
            except Exception:
                self._capture_center_latlon = None
        try:
            self._capture_rotation_deg = float(rotation_deg if rotation_deg is not None else 0.0) % 360.0
        except Exception:
            self._capture_rotation_deg = 0.0
        try:
            self._capture_mpp = float(payload.get("mpp", self._capture_mpp))
        except Exception:
            pass
        if isinstance(self._capture_surface, pygame.Surface):
            self._capture_base_surface = self._capture_surface.copy()
        try:
            self._capture_auto_gain = self._clamp_float(float(auto_gain), 0.5, 20.0)
        except Exception:
            self._capture_auto_gain = 6.0
        try:
            self._capture_auto_gamma = self._clamp_float(float(auto_gamma), 0.2, 2.5)
        except Exception:
            self._capture_auto_gamma = 0.85
        try:
            self._capture_auto_shadow = self._clamp_float(float(auto_shadow), 0.0, 1.0)
        except Exception:
            self._capture_auto_shadow = 0.12
        self._gain_value = float(self._capture_auto_gain)
        self._gamma_value = float(self._capture_auto_gamma)
        self._shadow_value = float(self._capture_auto_shadow)
        self._cntl_input_by_field = {"gain": "", "gamma": "", "shadow": ""}
        self._apply_capture_controls()
        self.reset_view()
        self._append_capture_history_bounds()

    def _resolution_seconds(self) -> int:
        mapping = {
            "1": 30,
            "2": 20,
            "3": 15,
            "4": 10,
            "5": 7,
            "6": 4,
        }
        return int(mapping.get(str(self._res_value), 30))

    def _start_xmit(self, now_ms: int) -> None:
        acq_ms = max(1000, int(self._resolution_seconds() * 1000))
        self._xmit_phase = "acquiring"
        self._xmit_start_ms = int(now_ms)
        self._xmit_acquire_ms = int(acq_ms)
        self._xmit_process_ms = max(500, int(acq_ms // 2))
        # Start downloading terrain during acquisition so it is ready by completion.
        self._request_capture_async(max(160, int(3.0 * DPI)), max(240, int(6.125 * DPI)))

    def _update_xmit(self, now_ms: int) -> None:
        self._consume_capture_payload()
        phase = str(self._xmit_phase)
        if phase == "acquiring":
            elapsed = int(now_ms) - int(self._xmit_start_ms)
            if elapsed >= int(self._xmit_acquire_ms):
                self._xmit_phase = "processing"
                self._xmit_start_ms = int(now_ms)
        elif phase == "processing":
            elapsed = int(now_ms) - int(self._xmit_start_ms)
            if elapsed >= int(self._xmit_process_ms):
                self._xmit_phase = "idle"
                self._xmit_start_ms = 0

    def _xmit_status_text(self, now_ms: int) -> Optional[str]:
        phase = str(self._xmit_phase)
        if phase == "acquiring":
            remaining_ms = max(0, int(self._xmit_acquire_ms) - (int(now_ms) - int(self._xmit_start_ms)))
            seconds = int(math.ceil(float(remaining_ms) / 1000.0))
            return f"ACQUIRING DATA: {seconds}"
        if phase == "processing":
            return "PROCESSING IMAGE"
        return None

    @staticmethod
    def _clamp_float(value: float, lo: float, hi: float) -> float:
        try:
            val = float(value)
        except Exception:
            val = float(lo)
        return max(float(lo), min(float(hi), float(val)))

    def _control_limits(self, field: str) -> Tuple[float, float, int]:
        key = str(field).strip().lower()
        if key == "gain":
            return 0.5, 20.0, 2
        if key == "gamma":
            return 0.2, 2.5, 2
        return 0.0, 1.0, 2

    def _control_value(self, field: str) -> float:
        key = str(field).strip().lower()
        if key == "gain":
            return float(self._gain_value)
        if key == "gamma":
            return float(self._gamma_value)
        return float(self._shadow_value)

    def _set_control_value(self, field: str, value: float) -> None:
        key = str(field).strip().lower()
        lo, hi, _ = self._control_limits(key)
        val = self._clamp_float(value, lo, hi)
        if key == "gain":
            self._gain_value = float(val)
        elif key == "gamma":
            self._gamma_value = float(val)
        else:
            self._shadow_value = float(val)

    def _apply_capture_controls(self) -> None:
        base = self._capture_base_surface
        if not isinstance(base, pygame.Surface):
            return
        gain_auto = max(0.001, float(self._capture_auto_gain))
        gamma_auto = max(0.001, float(self._capture_auto_gamma))
        shadow_auto = float(self._capture_auto_shadow)
        gain_ratio = float(self._gain_value) / gain_auto
        gamma_ratio = float(self._gamma_value) / gamma_auto
        shadow_delta = float(self._shadow_value) - shadow_auto
        if abs(gain_ratio - 1.0) < 0.001 and abs(gamma_ratio - 1.0) < 0.001 and abs(shadow_delta) < 0.001:
            self._capture_surface = base.copy()
            return
        if np is None:
            self._capture_surface = base.copy()
            return
        try:
            rgb = pygame.surfarray.array3d(base).astype(np.float32)
            gray = np.clip(rgb[:, :, 0] / 255.0, 0.0, 1.0)
            if gain_ratio >= 1.0:
                gray = 1.0 - np.power(np.clip(1.0 - gray, 0.0, 1.0), 1.0 / max(1e-6, gain_ratio))
            else:
                gray = np.power(np.clip(gray, 0.0, 1.0), 1.0 / max(1e-6, gain_ratio))
            gray = np.power(np.clip(gray, 0.0, 1.0), max(0.2, min(4.0, gamma_ratio)))
            if shadow_delta > 0.0:
                gray = np.clip(gray - (shadow_delta * 0.5 * (1.0 - gray)), 0.0, 1.0)
            elif shadow_delta < 0.0:
                gray = np.clip(gray + ((-shadow_delta) * 0.25 * (1.0 - gray)), 0.0, 1.0)
            out_u8 = (gray * 255.0).clip(0, 255).astype(np.uint8)
            out_rgb = np.repeat(out_u8[:, :, None], 3, axis=2)
            self._capture_surface = pygame.surfarray.make_surface(out_rgb).convert()
        except Exception:
            self._capture_surface = base.copy()

    def _control_popup_rect(self, rect: pygame.Rect) -> pygame.Rect:
        grid_rect = self._data_entry_grid_rect(rect)
        return pygame.Rect(
            grid_rect.x + (1 * GRID_CELL_W),
            grid_rect.y + (1 * GRID_CELL_H),
            3 * GRID_CELL_W,
            5 * GRID_CELL_H,
        )

    def _draw_control_popup(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        if not self._show_cntl_popup:
            return
        cyan = (0, 255, 255)
        white = (255, 255, 255)
        green = (0, 255, 0)
        popup_rect = self._control_popup_rect(rect)
        grid_rect = self._data_entry_grid_rect(rect)
        surface.fill((0, 0, 0), popup_rect)
        pygame.draw.rect(surface, cyan, popup_rect, 1)
        for c in (1, 2):
            x = popup_rect.left + (c * GRID_CELL_W)
            pygame.draw.line(surface, cyan, (x, popup_rect.top), (x, popup_rect.bottom), 1)
        for r in range(1, 5):
            y = popup_rect.top + (r * GRID_CELL_H)
            pygame.draw.line(surface, cyan, (popup_rect.left, y), (popup_rect.right, y), 1)

        field_cells = [
            ("gain", "GAIN", 1),
            ("gamma", "GAMMA", 2),
            ("shadow", "SHADOW", 3),
        ]
        font = get_font(14)
        for field, label, col in field_cells:
            box = pygame.Rect(grid_rect.x + (col * GRID_CELL_W), grid_rect.y + (1 * GRID_CELL_H), GRID_CELL_W, GRID_CELL_H)
            _, _, prec = self._control_limits(field)
            value_txt = f"{self._control_value(field):.{prec}f}"
            slot_h = box.height / 3.0

            # L2: field name.
            label_surf = font.render(label, True, green)
            label_rect = label_surf.get_rect(centerx=box.centerx)
            label_rect.y = int(box.top + slot_h + (slot_h - label_surf.get_height()) / 2)
            pygame.draw.rect(surface, (0, 0, 0), label_rect.inflate(6, 2), 0)
            surface.blit(label_surf, label_rect)

            # L3: current committed value.
            value_surf = font.render(value_txt, True, cyan)
            value_rect = value_surf.get_rect(centerx=box.centerx)
            value_rect.y = int(box.top + (2.0 * slot_h) + (slot_h - value_surf.get_height()) / 2)
            pygame.draw.rect(surface, (0, 0, 0), value_rect.inflate(6, 2), 0)
            surface.blit(value_surf, value_rect)

            # L1: scratchpad shown only for the active field.
            if self._cntl_selected_field == field:
                raw = str(self._cntl_input_by_field.get(field, ""))
                scratch = raw[-7:].rjust(7, "_")
                scratch_text = f"{scratch}\u2190"
                scratch_surf = font.render(scratch_text, True, white)
                scratch_rect = scratch_surf.get_rect(centerx=box.centerx)
                scratch_rect.y = int(box.top + (slot_h - scratch_surf.get_height()) / 2)
                pygame.draw.rect(surface, white, scratch_rect.inflate(4, 2), 1)
                surface.blit(scratch_surf, scratch_rect)

        keypad_labels = {
            "B3": "1",
            "C3": "2",
            "D3": "3",
            "B4": "4",
            "C4": "5",
            "D4": "6",
            "B5": "7",
            "C5": "8",
            "D5": "9",
            "B6": ".",
            "C6": "0",
            "D6": "BS",
        }
        for cell_name, text in keypad_labels.items():
            col = ord(cell_name[0]) - ord("A")
            row = int(cell_name[1:]) - 1
            box = pygame.Rect(grid_rect.x + col * GRID_CELL_W, grid_rect.y + row * GRID_CELL_H, GRID_CELL_W, GRID_CELL_H)
            surf = font.render(str(text), True, cyan)
            rr = surf.get_rect(center=box.center)
            pygame.draw.rect(surface, (0, 0, 0), rr.inflate(6, 2), 0)
            surface.blit(surf, rr)

    def _commit_control_entry(self, field: str) -> None:
        key = str(field).strip().lower()
        if key not in {"gain", "gamma", "shadow"}:
            return
        raw = str(self._cntl_input_by_field.get(key, "")).strip()
        if raw not in {"", ".", "-", "-."}:
            try:
                self._set_control_value(key, float(raw))
                self._apply_capture_controls()
            except Exception:
                pass
        self._cntl_input_by_field[key] = ""

    def _control_popup_handle_key(self, token: str) -> None:
        field = str(self._cntl_selected_field).strip().lower()
        if field not in {"gain", "gamma", "shadow"}:
            return
        raw = str(self._cntl_input_by_field.get(field, ""))
        tok = str(token).strip()
        if tok == "BS":
            raw = raw[:-1]
        elif tok == ".":
            if "." not in raw:
                raw = ("0" if raw == "" else raw) + "."
        elif tok.isdigit():
            if len(raw) < 8:
                raw = raw + tok
        self._cntl_input_by_field[field] = raw

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
        grid_w = 5 * GRID_CELL_W
        grid_h = 8 * GRID_CELL_H
        grid_x = _anchored_5col_grid_x(rect, grid_w)
        return pygame.Rect(grid_x, rect.y - SIDE_OSB_Y_SHIFT, grid_w, grid_h)

    def _draw_header_value_button(
        self,
        surface: pygame.Surface,
        box: pygame.Rect,
        header: str,
        value: str,
        flashing: bool,
        *,
        h_align: str = "center",
        v_align: str = "center",
    ) -> None:
        font = get_font(14)
        header_color = (0, 255, 0)
        value_color = (0, 255, 255)
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
        pygame.draw.line(surface, underline_color, (h_rect.left, h_rect.bottom + 1), (h_rect.right, h_rect.bottom + 1), 1)
        surface.blit(v_surf, v_rect)

    def _draw_osb_multiline(
        self,
        surface: pygame.Surface,
        box: pygame.Rect,
        lines: List[str],
        color: Tuple[int, int, int],
        *,
        h_align: str = "center",
        v_align: str = "center",
        flashing: bool = False,
    ) -> None:
        font = get_font(14)
        rendered = [font.render(str(line), True, (0, 0, 0) if flashing else color) for line in lines if str(line) != ""]
        if len(rendered) <= 0:
            return
        total_h = sum(s.get_height() for s in rendered) + max(0, len(rendered) - 1)
        if v_align == "top":
            y = box.top + OSB_PADDING
        else:
            y = box.centery - total_h // 2
        rects: List[pygame.Rect] = []
        for surf in rendered:
            if h_align == "left":
                rr = surf.get_rect(left=box.left + OSB_PADDING, y=y)
            elif h_align == "right":
                rr = surf.get_rect(right=box.right - OSB_PADDING, y=y)
            else:
                rr = surf.get_rect(centerx=box.centerx, y=y)
            rects.append(rr)
            y += surf.get_height() + 1
        if flashing and len(rects) > 0:
            fr = rects[0].copy()
            for rr in rects[1:]:
                fr.union_ip(rr)
            pygame.draw.rect(surface, (255, 255, 255), fr.inflate(4, 2))
        for rr in rects:
            pygame.draw.rect(surface, (0, 0, 0), rr.inflate(6, 2), 0)
        for surf, rr in zip(rendered, rects):
            surface.blit(surf, rr)

    def _res_popup_rows(self, rect: pygame.Rect) -> Tuple[int, int]:
        is_5x7 = rect.height >= int(7 * DPI) - 1
        row_start = 3
        row_end = row_start + 3
        return row_start, row_end

    def _res_popup_rect(self, rect: pygame.Rect) -> pygame.Rect:
        grid = self._data_entry_grid_rect(rect)
        row_start, row_end = self._res_popup_rows(rect)
        top = pygame.Rect(
            grid.x + (1 * GRID_CELL_W),
            grid.y + ((row_start - 1) * GRID_CELL_H),
            GRID_CELL_W,
            GRID_CELL_H,
        )
        bottom = pygame.Rect(
            grid.x + (3 * GRID_CELL_W),
            grid.y + ((row_end - 1) * GRID_CELL_H),
            GRID_CELL_W,
            GRID_CELL_H,
        )
        return top.union(bottom)

    def _res_popup_option_cells(self, rect: pygame.Rect) -> List[str]:
        row_start, _row_end = self._res_popup_rows(rect)
        return [
            f"B{row_start}",
            f"C{row_start}",
            f"D{row_start}",
            f"B{row_start + 1}",
            f"C{row_start + 1}",
            f"D{row_start + 1}",
        ]

    def _grid_cell_at_pos(self, pos: Tuple[int, int], rect: pygame.Rect) -> str:
        grid = self._data_entry_grid_rect(rect)
        rel_x = max(0, min((5 * GRID_CELL_W) - 1, int(pos[0]) - grid.x))
        rel_y = max(0, min((8 * GRID_CELL_H) - 1, int(pos[1]) - grid.y))
        col = max(0, min(4, int(rel_x // GRID_CELL_W)))
        row = max(0, min(7, int(rel_y // GRID_CELL_H)))
        return f"{chr(ord('A') + col)}{row + 1}"

    @staticmethod
    def _mode_options() -> List[str]:
        return ["NONE", "SAR", "WX"]

    def _mode_popup_rect(self, rect: pygame.Rect) -> pygame.Rect:
        grid = self._data_entry_grid_rect(rect)
        top = pygame.Rect(grid.x + (1 * GRID_CELL_W), grid.y + (2 * GRID_CELL_H), GRID_CELL_W, GRID_CELL_H)
        bot = pygame.Rect(grid.x + (3 * GRID_CELL_W), grid.y + (3 * GRID_CELL_H), GRID_CELL_W, GRID_CELL_H)
        return top.union(bot)

    def _mode_popup_option_cells(self) -> List[str]:
        return ["B3", "C3", "D3"]

    def _draw_mode_popup(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        if not self._show_mode_popup:
            return
        grid_rect = self._data_entry_grid_rect(rect)
        popup_rect = self._mode_popup_rect(rect)
        cyan = (0, 255, 255)
        white = (255, 255, 255)
        surface.fill((0, 0, 0), popup_rect)
        pygame.draw.rect(surface, cyan, popup_rect, 1)
        for c in (1, 2):
            x = grid_rect.x + ((1 + c) * GRID_CELL_W)
            pygame.draw.line(surface, cyan, (x, popup_rect.top), (x, popup_rect.bottom), 1)
        y = grid_rect.y + (3 * GRID_CELL_H)
        pygame.draw.line(surface, cyan, (popup_rect.left, y), (popup_rect.right, y), 1)
        labels = {
            "B3": "NONE",
            "C3": "SAR",
            "D3": "WX",
        }
        font = get_font(14)
        mode_text = str(self._mode_value).strip().upper()
        for cell_name, text in labels.items():
            col = ord(cell_name[0]) - ord("A")
            row = int(cell_name[1:]) - 1
            box = pygame.Rect(grid_rect.x + col * GRID_CELL_W, grid_rect.y + row * GRID_CELL_H, GRID_CELL_W, GRID_CELL_H)
            is_selected = mode_text == str(text).upper()
            surf = font.render(str(text), True, white if is_selected else cyan)
            rr = surf.get_rect(center=box.center)
            surface.blit(surf, rr)
            if is_selected:
                pygame.draw.rect(surface, white, rr.inflate(6, 3), 1)

    def _is_sar_mode(self) -> bool:
        return str(self._mode_value).strip().upper() == "SAR"

    def _is_wx_mode(self) -> bool:
        return str(self._mode_value).strip().upper() == "WX"

    def _is_none_mode(self) -> bool:
        return str(self._mode_value).strip().upper() == "NONE"

    def _is_none_like_mode(self) -> bool:
        mode = str(self._mode_value).strip().upper()
        return mode in {"NONE", "WX"}

    @staticmethod
    def _none_range_options() -> List[float]:
        return [7.5, 15.0, 30.0, 60.0, 120.0, 240.0]

    def _quantize_none_range(self, value: object) -> float:
        try:
            v = float(value)
        except Exception:
            v = 20.0
        opts = self._none_range_options()
        return float(min(opts, key=lambda x: (abs(x - v), x)))

    def _set_none_range(self, value: object) -> None:
        self._none_range_nm = float(self._quantize_none_range(value))

    def _adjust_none_range(self, direction: int) -> None:
        opts = self._none_range_options()
        curr = self._quantize_none_range(self._none_range_nm)
        idx = 0
        for i, v in enumerate(opts):
            if abs(float(v) - float(curr)) < 1e-6:
                idx = i
                break
        idx = max(0, min(len(opts) - 1, idx + (1 if int(direction) > 0 else -1)))
        self._none_range_nm = float(opts[idx])

    @staticmethod
    def _format_none_range_label(value: float) -> str:
        try:
            v = float(value)
        except Exception:
            v = 20.0
        if abs(v - round(v)) < 0.001:
            return str(int(round(v)))
        return f"{v:.1f}".rstrip("0").rstrip(".")

    def _overlay_popup_rect(self, rect: pygame.Rect) -> pygame.Rect:
        grid = self._data_entry_grid_rect(rect)
        top = pygame.Rect(grid.x + (1 * GRID_CELL_W), grid.y + (2 * GRID_CELL_H), GRID_CELL_W, GRID_CELL_H)
        bot = pygame.Rect(grid.x + (2 * GRID_CELL_W), grid.y + (2 * GRID_CELL_H), GRID_CELL_W, GRID_CELL_H)
        return top.union(bot)

    def _overlay_popup_option_cells(self) -> List[str]:
        return ["B3", "C3"]

    def _draw_overlay_popup(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        if not self._show_overlay_popup:
            return
        grid_rect = self._data_entry_grid_rect(rect)
        popup_rect = self._overlay_popup_rect(rect)
        cyan = (0, 255, 255)
        white = (255, 255, 255)
        surface.fill((0, 0, 0), popup_rect)
        pygame.draw.rect(surface, cyan, popup_rect, 1)
        x = grid_rect.x + (2 * GRID_CELL_W)
        pygame.draw.line(surface, cyan, (x, popup_rect.top), (x, popup_rect.bottom), 1)
        labels = {"B3": "OFF", "C3": "GMTI"}
        font = get_font(14)
        selected = "GMTI" if bool(self._overlay_on) else "OFF"
        for cell_name, text in labels.items():
            col = ord(cell_name[0]) - ord("A")
            row = int(cell_name[1:]) - 1
            box = pygame.Rect(grid_rect.x + col * GRID_CELL_W, grid_rect.y + row * GRID_CELL_H, GRID_CELL_W, GRID_CELL_H)
            is_selected = selected == text
            surf = font.render(text, True, white if is_selected else cyan)
            rr = surf.get_rect(center=box.center)
            surface.blit(surf, rr)
            if is_selected:
                pygame.draw.rect(surface, white, rr.inflate(6, 3), 1)

    def _draw_none_mode_inc_dec_and_range(
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
            range_text = self._format_none_range_label(self._none_range_nm)
            txt = font.render(range_text, True, cyan)
            tx = l1.left + OSB_PADDING + (txt.get_width() // 2)
            ty = int(round((l1.centery + l2.centery) / 2.0))
            tr = txt.get_rect(center=(tx, ty))
            pygame.draw.rect(surface, (0, 0, 0), tr.inflate(6, 2), 0)
            surface.blit(txt, tr)

    def _draw_none_mode_radar(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        *,
        align_apex_to_bottom: bool = False,
    ) -> None:
        white = (255, 255, 255)
        blue = (0, 128, 255)
        yellow = (255, 255, 0)
        green = (0, 255, 0)
        apex_x = int(rect.centerx)
        if bool(align_apex_to_bottom):
            apex_y = int(rect.bottom - 1)
        else:
            apex_y = int(round(float(rect.top) + (5.25 * DPI)))
        # 120-degree cone (total FOV), 4.75-inch cone height.
        half_fov_deg = 60.0
        target_height_px = max(10.0, float(4.75 * DPI))
        if bool(align_apex_to_bottom):
            # Keep original cone scale in subportals; allow clipping at top if needed.
            outer_r = float(target_height_px)
        else:
            max_r_from_top = max(10.0, float(apex_y - float(rect.top)))
            outer_r = max(10.0, min(target_height_px, max_r_from_top))
        radii = [outer_r * 0.33, outer_r * 0.66, outer_r]

        def _arc_points(radius: float) -> List[Tuple[int, int]]:
            pts: List[Tuple[int, int]] = []
            sweep = int(round(half_fov_deg))
            for ang in range(-sweep, sweep + 1, 2):
                x = int(round(float(apex_x) + (float(radius) * math.sin(math.radians(float(ang))))))
                y = int(round(float(apex_y) - (float(radius) * math.cos(math.radians(float(ang))))))
                pts.append((x, y))
            return pts

        # Boundary lines.
        left_end = (
            int(round(float(apex_x) + outer_r * math.sin(math.radians(-half_fov_deg)))),
            int(round(float(apex_y) - outer_r * math.cos(math.radians(-half_fov_deg)))),
        )
        right_end = (
            int(round(float(apex_x) + outer_r * math.sin(math.radians(half_fov_deg)))),
            int(round(float(apex_y) - outer_r * math.cos(math.radians(half_fov_deg)))),
        )
        pygame.draw.line(surface, white, (apex_x, apex_y), left_end, 1)
        pygame.draw.line(surface, white, (apex_x, apex_y), right_end, 1)

        # Centerline (bottom point to top point).
        top_center = (apex_x, int(round(float(apex_y) - outer_r)))
        pygame.draw.line(surface, white, (apex_x, apex_y), top_center, 1)

        # Two intermediate guide lines between centerline and cone edges.
        mid_ang = half_fov_deg * 0.5
        left_mid_end = (
            int(round(float(apex_x) + outer_r * math.sin(math.radians(-mid_ang)))),
            int(round(float(apex_y) - outer_r * math.cos(math.radians(-mid_ang)))),
        )
        right_mid_end = (
            int(round(float(apex_x) + outer_r * math.sin(math.radians(mid_ang)))),
            int(round(float(apex_y) - outer_r * math.cos(math.radians(mid_ang)))),
        )
        pygame.draw.line(surface, white, (apex_x, apex_y), left_mid_end, 1)
        pygame.draw.line(surface, white, (apex_x, apex_y), right_mid_end, 1)

        # Two inner arcs + top arc.
        for r in radii:
            pts = _arc_points(r)
            if len(pts) >= 2:
                pygame.draw.lines(surface, white, False, pts, 1)

        # GMTI overlay sector box: curved top/bottom with angled sides.
        if bool(self._overlay_on):
            half_box_deg = 15.0  # Top width = 30 degrees.
            thickness_ratio = 1.0 - 0.66  # Match top-arc to 2nd-top arc spacing.
            center_deg = max(-(half_fov_deg - half_box_deg), min((half_fov_deg - half_box_deg), float(self._none_gmti_center_deg)))
            top_ratio = max(thickness_ratio, min(1.0, float(self._none_gmti_top_ratio)))
            self._none_gmti_center_deg = float(center_deg)
            self._none_gmti_top_ratio = float(top_ratio)
            top_r = float(outer_r) * float(top_ratio)
            bot_r = max(1.0, float(outer_r) * float(top_ratio - thickness_ratio))
            left_ang = float(center_deg) - half_box_deg
            right_ang = float(center_deg) + half_box_deg

            def _arc_segment(radius: float, a0: float, a1: float, step_deg: float = 1.5) -> List[Tuple[int, int]]:
                pts: List[Tuple[int, int]] = []
                if a1 < a0:
                    a0, a1 = a1, a0
                a = float(a0)
                while a <= float(a1) + 0.001:
                    x = int(round(float(apex_x) + (float(radius) * math.sin(math.radians(a)))))
                    y = int(round(float(apex_y) - (float(radius) * math.cos(math.radians(a)))))
                    pts.append((x, y))
                    a += float(step_deg)
                return pts

            top_pts = _arc_segment(top_r, left_ang, right_ang)
            bot_pts = _arc_segment(bot_r, left_ang, right_ang)
            if len(top_pts) >= 2:
                pygame.draw.lines(surface, green, False, top_pts, 1)
            if len(bot_pts) >= 2:
                pygame.draw.lines(surface, green, False, bot_pts, 1)
            left_top = (
                int(round(float(apex_x) + (top_r * math.sin(math.radians(left_ang))))),
                int(round(float(apex_y) - (top_r * math.cos(math.radians(left_ang))))),
            )
            left_bot = (
                int(round(float(apex_x) + (bot_r * math.sin(math.radians(left_ang))))),
                int(round(float(apex_y) - (bot_r * math.cos(math.radians(left_ang))))),
            )
            right_top = (
                int(round(float(apex_x) + (top_r * math.sin(math.radians(right_ang))))),
                int(round(float(apex_y) - (top_r * math.cos(math.radians(right_ang))))),
            )
            right_bot = (
                int(round(float(apex_x) + (bot_r * math.sin(math.radians(right_ang))))),
                int(round(float(apex_y) - (bot_r * math.cos(math.radians(right_ang))))),
            )
            pygame.draw.line(surface, green, left_bot, left_top, 1)
            pygame.draw.line(surface, green, right_bot, right_top, 1)

        if self._is_wx_mode():
            self._draw_wx_mode_overlay(
                surface,
                rect,
                int(apex_x),
                int(apex_y),
                float(outer_r),
                float(half_fov_deg),
            )

        # ADS-B tracks: only contacts within selected range and forward 120° FOV.
        own = self._read_ownship_lat_lon()
        if isinstance(own, tuple) and len(own) == 2:
            own_lat = float(own[0])
            own_lon = float(own[1])
            try:
                own_heading = float(TWD_STATE.get("heading_deg", 0.0)) % 360.0
            except Exception:
                own_heading = 0.0
            max_range_nm = max(0.1, float(self._none_range_nm))
            snap = TSD_ADSB_STATE if isinstance(TSD_ADSB_STATE, dict) else {}
            contacts = Tsd1Format._adsb_contacts(snap.get("raw"), mil_payload=snap.get("mil_raw"))
            now_s = datetime.now(timezone.utc).timestamp()
            last_update_s = Tsd1Format._safe_float(snap.get("last_update_time"))
            if last_update_s is None:
                last_update_s = now_s
            age_s = max(0.0, now_s - float(last_update_s))
            configured_interval_s = Tsd1Format._safe_float(snap.get("min_interval_s"))
            if configured_interval_s is None:
                configured_interval_s = 5.0
            max_project_s = max(2.0, min(45.0, float(configured_interval_s) * 2.5))
            project_dt_s = min(age_s, max_project_s)
            for contact in contacts:
                # ASR NONE/WX shows airborne ADS-B returns as blue squares.
                # Ground movers are represented separately by the yellow GMTI simulation below.
                if str(contact.get("domain", "AIR")).upper().strip() == "GROUND":
                    continue
                lat = Tsd1Format._safe_float(contact.get("lat"))
                lon = Tsd1Format._safe_float(contact.get("lon"))
                if lat is None or lon is None:
                    continue
                is_sim = bool(contact.get("_plugin_sim", False) or contact.get("_sim", False))
                speed_kts = Tsd1Format._safe_float(contact.get("speed_kts"))
                trk_heading = Tsd1Format._safe_float(contact.get("heading"))
                if (not is_sim) and trk_heading is not None and speed_kts is not None and speed_kts > 1.0 and project_dt_s > 0.0:
                    travel_nm = float(speed_kts) * (float(project_dt_s) / 3600.0)
                    lat, lon = Tsd1Format._project_lat_lon_nm(float(lat), float(lon), float(trk_heading), float(travel_nm))
                try:
                    bearing_deg, dist_nm = Tsd1Format._bearing_and_distance_nm(own_lat, own_lon, float(lat), float(lon))
                except Exception:
                    continue
                if dist_nm > max_range_nm:
                    continue
                rel_deg = ((float(bearing_deg) - float(own_heading) + 540.0) % 360.0) - 180.0
                if abs(rel_deg) > float(half_fov_deg):
                    continue
                rr = float(outer_r) * (max(0.0, min(1.0, float(dist_nm) / float(max_range_nm))))
                sx = int(round(float(apex_x) + (rr * math.sin(math.radians(float(rel_deg))))))
                sy = int(round(float(apex_y) - (rr * math.cos(math.radians(float(rel_deg))))))
                if not rect.collidepoint(sx, sy):
                    continue
                sq = max(3, int(round(0.06 * DPI)))
                sr = pygame.Rect(0, 0, sq, sq)
                sr.center = (sx, sy)
                pygame.draw.rect(surface, blue, sr, 0)

            # Simulated road vehicles: yellow GMTI squares.
            sim_items = self._sim_vehicle_positions(
                float(own_lat),
                float(own_lon),
                float(own_heading),
                float(max_range_nm),
                float(half_fov_deg),
            )
            for rel_deg, dist_nm in sim_items:
                rr = float(outer_r) * (max(0.0, min(1.0, float(dist_nm) / float(max_range_nm))))
                sx = int(round(float(apex_x) + (rr * math.sin(math.radians(float(rel_deg))))))
                sy = int(round(float(apex_y) - (rr * math.cos(math.radians(float(rel_deg))))))
                if not rect.collidepoint(sx, sy):
                    continue
                sq = max(3, int(round(0.06 * DPI)))
                sr = pygame.Rect(0, 0, sq, sq)
                sr.center = (sx, sy)
                pygame.draw.rect(surface, yellow, sr, 0)

        # Range labels at each curve: left of right boundary line and below each arc.
        try:
            full_range = float(self._none_range_nm)
        except Exception:
            full_range = 0.0
        label_font = get_font(14)
        # Place labels just left of the right quarter line (between center and boundary).
        label_ang = max(0.0, float(mid_ang) - 6.0)
        for r in radii:
            frac = float(r) / max(1e-6, float(outer_r))
            value = max(0, int(round(full_range * frac)))
            lx = int(round(float(apex_x) + (float(r) * math.sin(math.radians(label_ang)))))
            ly = int(round(float(apex_y) - (float(r) * math.cos(math.radians(label_ang)))))
            txt = label_font.render(str(value), True, white)
            tr = txt.get_rect()
            tr.right = lx - 4
            tr.top = ly + 2
            pygame.draw.rect(surface, (0, 0, 0), tr.inflate(4, 2), 0)
            surface.blit(txt, tr)

    def _view_is_default(self) -> bool:
        return (
            abs(float(self._view_zoom) - 1.0) < 0.001
            and abs(float(self._view_pan_x_px)) < 0.5
            and abs(float(self._view_pan_y_px)) < 0.5
        )

    def reset_view(self) -> None:
        self._view_zoom = 1.0
        self._view_pan_x_px = 0.0
        self._view_pan_y_px = 0.0

    def apply_keyboard_pan_zoom(
        self,
        dt_s: float,
        *,
        zoom_in: bool,
        zoom_out: bool,
        pan_left: bool,
        pan_right: bool,
        pan_up: bool,
        pan_down: bool,
    ) -> None:
        if dt_s <= 0.0:
            return
        if self._is_none_like_mode():
            # In NONE/WX modes, SLEW controls the GMTI overlay box.
            if bool(self._overlay_on):
                half_fov_deg = 60.0
                half_box_deg = 15.0  # 30-degree top width.
                max_center = max(0.0, float(half_fov_deg - half_box_deg))
                thickness_ratio = 1.0 - 0.66
                center_rate_deg_s = 55.0
                radial_rate_ratio_s = 0.35
                if pan_left and (not pan_right):
                    self._none_gmti_center_deg = max(
                        -max_center,
                        float(self._none_gmti_center_deg) - (center_rate_deg_s * float(dt_s)),
                    )
                elif pan_right and (not pan_left):
                    self._none_gmti_center_deg = min(
                        max_center,
                        float(self._none_gmti_center_deg) + (center_rate_deg_s * float(dt_s)),
                    )
                if pan_up and (not pan_down):
                    self._none_gmti_top_ratio = min(
                        1.0,
                        float(self._none_gmti_top_ratio) + (radial_rate_ratio_s * float(dt_s)),
                    )
                elif pan_down and (not pan_up):
                    self._none_gmti_top_ratio = max(
                        thickness_ratio,
                        float(self._none_gmti_top_ratio) - (radial_rate_ratio_s * float(dt_s)),
                    )
            return
        if not self._has_renderable_map():
            return
        old_zoom = max(1.0, float(self._view_zoom))
        new_zoom = float(old_zoom)
        if zoom_in and (not zoom_out):
            new_zoom *= math.exp(2.4 * float(dt_s))
        elif zoom_out and (not zoom_in):
            new_zoom *= math.exp(-2.4 * float(dt_s))
        new_zoom = max(1.0, min(6.0, float(new_zoom)))
        if abs(new_zoom - old_zoom) > 1e-9:
            ratio = float(new_zoom) / float(old_zoom)
            self._view_pan_x_px *= ratio
            self._view_pan_y_px *= ratio
        self._view_zoom = float(new_zoom)
        pan_rate_px_s = 220.0
        if pan_left and (not pan_right):
            self._view_pan_x_px += pan_rate_px_s * float(dt_s)
        elif pan_right and (not pan_left):
            self._view_pan_x_px -= pan_rate_px_s * float(dt_s)
        if pan_up and (not pan_down):
            self._view_pan_y_px += pan_rate_px_s * float(dt_s)
        elif pan_down and (not pan_up):
            self._view_pan_y_px -= pan_rate_px_s * float(dt_s)
        self._view_pan_x_px = max(-4096.0, min(4096.0, float(self._view_pan_x_px)))
        self._view_pan_y_px = max(-4096.0, min(4096.0, float(self._view_pan_y_px)))

    @staticmethod
    def _normalize_lon_deg(lon: float) -> float:
        return ((float(lon) + 180.0) % 360.0) - 180.0

    @classmethod
    def _wrap_lon_delta(cls, lon: float, ref_lon: float) -> float:
        return cls._normalize_lon_deg(float(lon) - float(ref_lon))

    @classmethod
    def _bounds_lon_in(cls, lon: float, min_lon: float, max_lon: float) -> bool:
        span = cls._wrap_lon_delta(float(max_lon), float(min_lon))
        if span < 0.0:
            span += 360.0
        d = cls._wrap_lon_delta(float(lon), float(min_lon))
        if d < 0.0:
            d += 360.0
        return d <= span

    @classmethod
    def _bounds_overlap(cls, a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]) -> bool:
        a_min_lon, a_min_lat, a_max_lon, a_max_lat = a
        b_min_lon, b_min_lat, b_max_lon, b_max_lat = b
        if float(a_max_lat) < float(b_min_lat) or float(b_max_lat) < float(a_min_lat):
            return False
        a_pts = [a_min_lon, a_max_lon, (a_min_lon + cls._wrap_lon_delta(a_max_lon, a_min_lon) * 0.5)]
        b_pts = [b_min_lon, b_max_lon, (b_min_lon + cls._wrap_lon_delta(b_max_lon, b_min_lon) * 0.5)]
        for lon in b_pts:
            if cls._bounds_lon_in(lon, a_min_lon, a_max_lon):
                return True
        for lon in a_pts:
            if cls._bounds_lon_in(lon, b_min_lon, b_max_lon):
                return True
        return False

    def _screen_to_capture_latlon(
        self,
        sx: float,
        sy: float,
        image_rect: pygame.Rect,
    ) -> Optional[Tuple[float, float]]:
        if self._capture_bounds is None or image_rect.width <= 1 or image_rect.height <= 1:
            return None
        min_lon, min_lat, max_lon, max_lat = self._capture_bounds
        cx = float(image_rect.centerx)
        cy = float(image_rect.centery)
        x = float(sx) - float(self._capture_draw_pan_x)
        y = float(sy) - float(self._capture_draw_pan_y)
        rot = float(self._capture_rotation_deg) % 360.0
        if abs(rot) > 0.001:
            theta = math.radians(-rot)
            cos_t = math.cos(theta)
            sin_t = math.sin(theta)
            dx = x - cx
            dy = y - cy
            x = cx + (dx * cos_t) - (dy * sin_t)
            y = cy + (dx * sin_t) + (dy * cos_t)
        zoom = max(1.0, float(self._capture_draw_zoom))
        x = cx + ((x - cx) / zoom)
        y = cy + ((y - cy) / zoom)
        if x < image_rect.left or x > image_rect.right or y < image_rect.top or y > image_rect.bottom:
            return None
        u = (float(x) - float(image_rect.left)) / float(max(1, image_rect.width - 1))
        v = (float(y) - float(image_rect.top)) / float(max(1, image_rect.height - 1))
        u = max(0.0, min(1.0, u))
        v = max(0.0, min(1.0, v))
        lon_span = self._wrap_lon_delta(float(max_lon), float(min_lon))
        if lon_span < 0.0:
            lon_span += 360.0
        lon = self._normalize_lon_deg(float(min_lon) + (u * lon_span))
        lat = float(max_lat) - (v * float(max_lat - min_lat))
        return float(lat), float(lon)

    def _capture_latlon_to_image_xy(
        self,
        lat: float,
        lon: float,
        image_rect: pygame.Rect,
        *,
        allow_outside: bool = False,
    ) -> Optional[Tuple[int, int]]:
        if self._capture_bounds is None or image_rect.width <= 1 or image_rect.height <= 1:
            return None
        min_lon, min_lat, max_lon, max_lat = self._capture_bounds
        lon_span = self._wrap_lon_delta(float(max_lon), float(min_lon))
        if lon_span < 0.0:
            lon_span += 360.0
        lat_span = max(1e-9, float(max_lat - min_lat))
        dlon = self._wrap_lon_delta(float(lon), float(min_lon))
        if dlon < 0.0:
            dlon += 360.0
        u = dlon / max(1e-9, lon_span)
        v = (float(max_lat) - float(lat)) / lat_span
        if not allow_outside:
            if u < 0.0 or u > 1.0 or v < 0.0 or v > 1.0:
                return None
        else:
            if u < -2.0 or u > 3.0 or v < -2.0 or v > 3.0:
                return None
        px = int(round(float(image_rect.left) + (u * float(image_rect.width - 1))))
        py = int(round(float(image_rect.top) + (v * float(image_rect.height - 1))))
        return self._transform_overlay_xy(px, py, image_rect)

    def _draw_asr_runways_and_tacan(self, surface: pygame.Surface, image_rect: pygame.Rect) -> None:
        if str(self._xmit_phase) != "idle":
            return
        if self._capture_bounds is None or (not isinstance(self._capture_surface, pygame.Surface)):
            return
        min_lon, min_lat, max_lon, max_lat = self._capture_bounds
        runways = Tsd1Format._load_runways()
        with Tsd1Format._runway_cache_lock:
            runway_index = Tsd1Format._runway_spatial_index
        candidate_runways: List[Dict[str, object]]
        if isinstance(runway_index, dict) and len(runway_index) > 0:
            lat_min_cell = int(math.floor(float(min_lat))) - 1
            lat_max_cell = int(math.floor(float(max_lat))) + 1
            lon_min_cell = int(math.floor(float(min_lon))) - 2
            lon_max_cell = int(math.floor(float(max_lon))) + 2
            candidate_runways = []
            for lat_cell in range(lat_min_cell, lat_max_cell + 1):
                for lon_cell in range(lon_min_cell, lon_max_cell + 1):
                    bucket = runway_index.get((lat_cell, lon_cell))
                    if isinstance(bucket, list) and len(bucket) > 0:
                        candidate_runways.extend(bucket)
        else:
            candidate_runways = runways
        black = (0, 0, 0)
        for runway in candidate_runways:
            try:
                le_lat = float(runway.get("le_lat"))
                le_lon = float(runway.get("le_lon"))
                he_lat = float(runway.get("he_lat"))
                he_lon = float(runway.get("he_lon"))
            except Exception:
                continue
            # Cull clearly outside capture.
            if (
                max(le_lat, he_lat) < (float(min_lat) - 0.05)
                or min(le_lat, he_lat) > (float(max_lat) + 0.05)
            ):
                continue
            if (
                (not self._bounds_lon_in(le_lon, float(min_lon), float(max_lon)))
                and (not self._bounds_lon_in(he_lon, float(min_lon), float(max_lon)))
            ):
                mid_lon = self._normalize_lon_deg((float(le_lon) + float(he_lon)) * 0.5)
                if not self._bounds_lon_in(mid_lon, float(min_lon), float(max_lon)):
                    continue
            try:
                hdg = float(runway.get("le_heading_deg", 0.0)) % 360.0
            except Exception:
                hdg = 0.0
            if abs(hdg) < 1e-6:
                try:
                    hdg = float(Tsd1Format._bearing_and_distance_nm(le_lat, le_lon, he_lat, he_lon)[0]) % 360.0
                except Exception:
                    hdg = 0.0
            try:
                width_ft = float(runway.get("width_ft", 0.0) or 0.0)
            except Exception:
                width_ft = 0.0
            if width_ft <= 0.0:
                width_ft = 25.0
            half_width_nm = max(0.0, float(width_ft) / 6076.12) * 0.5
            le_l_lat, le_l_lon = Tsd1Format._project_lat_lon_nm(le_lat, le_lon, (hdg - 90.0) % 360.0, half_width_nm)
            le_r_lat, le_r_lon = Tsd1Format._project_lat_lon_nm(le_lat, le_lon, (hdg + 90.0) % 360.0, half_width_nm)
            he_l_lat, he_l_lon = Tsd1Format._project_lat_lon_nm(he_lat, he_lon, (hdg - 90.0) % 360.0, half_width_nm)
            he_r_lat, he_r_lon = Tsd1Format._project_lat_lon_nm(he_lat, he_lon, (hdg + 90.0) % 360.0, half_width_nm)
            poly_pts: List[Tuple[int, int]] = []
            for plat, plon in (
                (le_l_lat, le_l_lon),
                (he_l_lat, he_l_lon),
                (he_r_lat, he_r_lon),
                (le_r_lat, le_r_lon),
            ):
                p = self._capture_latlon_to_image_xy(plat, plon, image_rect, allow_outside=True)
                if p is None:
                    poly_pts = []
                    break
                poly_pts.append(p)
            if len(poly_pts) == 4:
                pygame.draw.polygon(surface, black, poly_pts)
                pygame.draw.polygon(surface, black, poly_pts, 1)

        navaids = Tsd1Format._load_tacan_vor_navaids()
        tacan_icon = Tsd1Format._get_tacan_icon(max(8, int(round(0.22 * DPI))))
        if tacan_icon is None:
            return
        for nav in navaids:
            nav_type = str(nav.get("type") or "").upper().strip()
            # TACAN-only request: include TACAN and VORTAC.
            if ("TACAN" not in nav_type) and (nav_type != "VORTAC"):
                continue
            try:
                lat = float(nav.get("lat"))
                lon = float(nav.get("lon"))
            except Exception:
                continue
            if lat < (float(min_lat) - 0.5) or lat > (float(max_lat) + 0.5):
                continue
            if (not self._bounds_lon_in(lon, float(min_lon), float(max_lon))):
                continue
            pos = self._capture_latlon_to_image_xy(lat, lon, image_rect, allow_outside=False)
            if pos is None:
                continue
            rr = tacan_icon.get_rect(center=pos)
            surface.blit(tacan_icon, rr)

    @staticmethod
    def _format_dmm(value: float, is_lat: bool) -> str:
        v = float(value)
        hemi = "N" if is_lat else "E"
        if is_lat and v < 0.0:
            hemi = "S"
        if (not is_lat) and v < 0.0:
            hemi = "W"
        av = abs(v)
        deg = int(math.floor(av))
        minutes = (av - float(deg)) * 60.0
        if is_lat:
            return f"{hemi} {deg:02d} {minutes:05.2f}"
        return f"{hemi}{deg:03d} {minutes:05.2f}"

    @staticmethod
    def _read_ownship_altitude_ft() -> float:
        try:
            throttle = PANEL_BUTTON_STATES.get("THROTTLE", {})
            if not isinstance(throttle, dict):
                return 0.0
            aircraft = throttle.get("AIRCRAFT", {})
            if not isinstance(aircraft, dict):
                return 0.0
            return float(aircraft.get("ALTITUDE_FT", 0.0))
        except Exception:
            return 0.0

    def _append_capture_history_bounds(self) -> None:
        bounds = self._capture_bounds
        if not (isinstance(bounds, tuple) and len(bounds) == 4):
            return
        try:
            min_lon = float(bounds[0])
            min_lat = float(bounds[1])
            max_lon = float(bounds[2])
            max_lat = float(bounds[3])
        except Exception:
            return
        lon_span = self._wrap_lon_delta(float(max_lon), float(min_lon))
        if lon_span < 0.0:
            lon_span += 360.0
        mid_lon = self._normalize_lon_deg(float(min_lon) + (lon_span * 0.5))
        mid_lat = (float(min_lat) + float(max_lat)) * 0.5
        width_nm = 0.0
        height_nm = 0.0
        try:
            _b, width_nm = Tsd1Format._bearing_and_distance_nm(mid_lat, float(min_lon), mid_lat, float(max_lon))
        except Exception:
            width_nm = 0.0
        try:
            _b, height_nm = Tsd1Format._bearing_and_distance_nm(float(min_lat), mid_lon, float(max_lat), mid_lon)
        except Exception:
            height_nm = 0.0
        rec_obj = {
            "bounds": (float(min_lon), float(min_lat), float(max_lon), float(max_lat)),
            "center_lat": float(mid_lat),
            "center_lon": float(mid_lon),
            "rotation_deg": float(self._capture_rotation_deg) % 360.0,
            "width_nm": float(max(0.0, width_nm)),
            "height_nm": float(max(0.0, height_nm)),
        }
        cls = self.__class__
        for old in list(cls._capture_history_bounds):
            try:
                if isinstance(old, dict):
                    ob = old.get("bounds")
                else:
                    ob = old
                if not (isinstance(ob, (tuple, list)) and len(ob) == 4):
                    continue
                if (
                    abs(float(ob[0]) - float(min_lon)) < 1e-6
                    and abs(float(ob[1]) - float(min_lat)) < 1e-6
                    and abs(float(ob[2]) - float(max_lon)) < 1e-6
                    and abs(float(ob[3]) - float(max_lat)) < 1e-6
                ):
                    return
            except Exception:
                continue
        cls._capture_history_bounds.append(rec_obj)
        if len(cls._capture_history_bounds) > int(cls._capture_history_max):
            cls._capture_history_bounds = cls._capture_history_bounds[-int(cls._capture_history_max):]

    def _draw_capture_history_boxes(self, surface: pygame.Surface, image_rect: pygame.Rect) -> None:
        if (not self._is_sar_mode()) or self._capture_bounds is None:
            return
        if str(self._xmit_phase) != "idle" or (not isinstance(self._capture_surface, pygame.Surface)):
            return
        current = self._capture_bounds
        green = (0, 255, 0)
        min_lon, min_lat, max_lon, max_lat = current
        lon_span = self._wrap_lon_delta(float(max_lon), float(min_lon))
        if lon_span < 0.0:
            lon_span += 360.0
        lat_span = max(1e-9, float(max_lat - min_lat))

        def _project(lat: float, lon: float) -> Tuple[int, int]:
            dlon = self._wrap_lon_delta(float(lon), float(min_lon))
            if dlon < 0.0:
                dlon += 360.0
            u = dlon / max(1e-9, lon_span)
            v = (float(max_lat) - float(lat)) / lat_span
            px = int(round(float(image_rect.left) + (u * float(image_rect.width - 1))))
            py = int(round(float(image_rect.top) + (v * float(image_rect.height - 1))))
            return self._transform_overlay_xy(px, py, image_rect)

        def _hist_extract(
            entry: object,
        ) -> Optional[Tuple[Tuple[float, float, float, float], Optional[float], float, float]]:
            try:
                if isinstance(entry, dict):
                    raw_bounds = entry.get("bounds")
                    raw_rot = entry.get("rotation_deg")
                    raw_clat = entry.get("center_lat")
                    raw_clon = entry.get("center_lon")
                else:
                    raw_bounds = entry
                    raw_rot = None
                    raw_clat = None
                    raw_clon = None
                if not (isinstance(raw_bounds, (tuple, list)) and len(raw_bounds) == 4):
                    return None
                b = (
                    float(raw_bounds[0]),
                    float(raw_bounds[1]),
                    float(raw_bounds[2]),
                    float(raw_bounds[3]),
                )
                if raw_rot is None:
                    rot: Optional[float] = None
                else:
                    rot = float(raw_rot) % 360.0
                if raw_clat is None:
                    clat = (float(b[1]) + float(b[3])) * 0.5
                else:
                    clat = float(raw_clat)
                if raw_clon is None:
                    b_span = self._wrap_lon_delta(float(b[2]), float(b[0]))
                    if b_span < 0.0:
                        b_span += 360.0
                    clon = self._normalize_lon_deg(float(b[0]) + (b_span * 0.5))
                else:
                    clon = float(raw_clon)
                return b, rot, float(clat), float(clon)
            except Exception:
                return None

        curr_rot = float(self._capture_rotation_deg) % 360.0
        for hist in list(self.__class__._capture_history_bounds):
            parsed = _hist_extract(hist)
            if parsed is None:
                continue
            h_bounds, h_rot, h_center_lat, h_center_lon = parsed
            if not self._bounds_overlap(current, h_bounds):
                continue
            if (
                abs(float(h_bounds[0]) - float(current[0])) < 1e-6
                and abs(float(h_bounds[1]) - float(current[1])) < 1e-6
                and abs(float(h_bounds[2]) - float(current[2])) < 1e-6
                and abs(float(h_bounds[3]) - float(current[3])) < 1e-6
            ):
                continue
            h_min_lon, h_min_lat, h_max_lon, h_max_lat = h_bounds
            p0 = _project(h_min_lat, h_min_lon)
            p1 = _project(h_min_lat, h_max_lon)
            p2 = _project(h_max_lat, h_max_lon)
            p3 = _project(h_max_lat, h_min_lon)
            pts = [p0, p1, p2, p3]
            if h_rot is not None:
                delta = ((float(h_rot) - float(curr_rot) + 180.0) % 360.0) - 180.0
                if abs(delta) > 0.001:
                    cpt = _project(float(h_center_lat), float(h_center_lon))
                    cx = float(cpt[0])
                    cy = float(cpt[1])
                    pts = [self._rotate_xy(int(pt[0]), int(pt[1]), cx, cy, delta) for pt in pts]
            pygame.draw.lines(surface, green, True, pts, 1)

    def _draw_sar_reference_and_cursor(self, surface: pygame.Surface, rect: pygame.Rect, image_rect: pygame.Rect) -> None:
        if (not self._is_sar_mode()) or (not self._has_renderable_map()):
            return
        green = (0, 255, 0)
        cyan = (0, 255, 255)
        white = (255, 255, 255)
        ref_y = int(round(float(rect.top) + (1.5 * DPI)))
        ref_x0 = int(round(float(rect.left) + (0.75 * DPI) - (0.125 * DPI)))
        ref_len_px = int(round(0.75 * DPI))
        ref_x1 = ref_x0 + ref_len_px
        pygame.draw.line(surface, white, (ref_x0, ref_y), (ref_x1, ref_y), 1)
        pygame.draw.circle(surface, white, (ref_x0, ref_y), max(2, int(round(0.03 * DPI))), 0)
        pygame.draw.circle(surface, white, (ref_x1, ref_y), max(2, int(round(0.03 * DPI))), 0)
        ref_ft = 0.0
        ll0 = self._screen_to_capture_latlon(ref_x0, ref_y, image_rect)
        ll1 = self._screen_to_capture_latlon(ref_x1, ref_y, image_rect)
        if ll0 is not None and ll1 is not None:
            try:
                _brg, dist_nm = Tsd1Format._bearing_and_distance_nm(float(ll0[0]), float(ll0[1]), float(ll1[0]), float(ll1[1]))
                ref_ft = max(0.0, float(dist_nm) * 6076.12)
            except Exception:
                ref_ft = 0.0
        font = get_font(14)
        ref_text = font.render(f"{int(round(ref_ft))} FT", True, green)
        ref_rect = ref_text.get_rect(centerx=(ref_x0 + ref_x1) // 2, y=ref_y + 4)
        pygame.draw.rect(surface, (0, 0, 0), ref_rect.inflate(6, 2), 0)
        surface.blit(ref_text, ref_rect)

        total_nm = 0.0
        if isinstance(self._capture_bounds, tuple) and len(self._capture_bounds) == 4:
            min_lon, min_lat, max_lon, max_lat = self._capture_bounds
            mid_lat = (float(min_lat) + float(max_lat)) * 0.5
            try:
                _brg, total_nm = Tsd1Format._bearing_and_distance_nm(mid_lat, float(min_lon), mid_lat, float(max_lon))
            except Exception:
                total_nm = 0.0
        total_text = font.render(f"{total_nm:.1f} NM", True, green)
        total_rect = total_text.get_rect(centerx=rect.centerx, centery=int(round(float(rect.top) + (0.5 * DPI))))
        pygame.draw.rect(surface, (0, 0, 0), total_rect.inflate(6, 2), 0)
        surface.blit(total_text, total_rect)

        cursor_x = int(DISPLAY_CURSOR_LOGICAL[0])
        cursor_y = int(DISPLAY_CURSOR_LOGICAL[1])
        cursor_x = max(rect.left, min(rect.right - 1, cursor_x))
        cursor_y = max(rect.top, min(rect.bottom - 1, cursor_y))
        ll = self._screen_to_capture_latlon(cursor_x, cursor_y, image_rect)
        lat_txt = "N 00 00.00"
        lon_txt = "W000 00.00"
        dist_m = 0.0
        if ll is not None:
            lat_val, lon_val = ll
            lat_txt = self._format_dmm(lat_val, True)
            lon_txt = self._format_dmm(lon_val, False)
            own = self._read_ownship_lat_lon()
            if own is not None:
                try:
                    _brg, d_nm = Tsd1Format._bearing_and_distance_nm(float(own[0]), float(own[1]), float(lat_val), float(lon_val))
                    dist_m = max(0.0, float(d_nm) * 1852.0)
                except Exception:
                    dist_m = 0.0
        alt_ft = max(0.0, self._read_ownship_altitude_ft())
        third_txt = f"{int(round(dist_m))}M/{int(round(alt_ft))}H"
        t2 = self._osb_box(rect, "T2")
        if t2 is not None:
            box_x = int(round(float(t2.centerx)))
            box_y = t2.bottom + int(round(0.08 * DPI) - (0.25 * DPI))
        else:
            box_x = rect.left + int(round(1.55 * DPI))
            box_y = rect.top + int(round(0.90 * DPI) - (0.25 * DPI))
        txt_font = get_font(13)
        lines = [lat_txt, lon_txt, third_txt]
        text_w = 0
        text_h = 0
        rendered_lines: List[pygame.Surface] = []
        for line in lines:
            surf_line = txt_font.render(line, True, cyan)
            rendered_lines.append(surf_line)
            text_w = max(text_w, int(surf_line.get_width()))
            text_h += int(surf_line.get_height())
        line_gap = 1
        text_h += line_gap * max(0, len(rendered_lines) - 1)
        pad_x = 6
        pad_y = 4
        coord_box = pygame.Rect(
            int(round(float(box_x) - ((text_w + (2 * pad_x)) * 0.5))),
            int(round(float(box_y))),
            max(20, text_w + (2 * pad_x)),
            max(20, text_h + (2 * pad_y)),
        )
        pygame.draw.rect(surface, cyan, coord_box, 1)
        y = coord_box.top + pad_y
        for surf_line in rendered_lines:
            rr = surf_line.get_rect(centerx=coord_box.centerx, y=y)
            pygame.draw.rect(surface, (0, 0, 0), rr.inflate(4, 1), 0)
            surface.blit(surf_line, rr)
            y += int(surf_line.get_height()) + line_gap

        r5 = self._osb_box(rect, "R5")
        if r5 is None:
            return
        arrow_cx = int(round(float(rect.right) - (1.5 * DPI)))
        arrow_cy = int(r5.centery)
        arrow_len = max(12, int(round(0.28 * DPI)))
        north_deg = float(self._capture_rotation_deg) % 360.0
        theta = math.radians(north_deg)
        half_len = float(arrow_len) * 0.5
        tip_x = int(round(float(arrow_cx) + (half_len * math.sin(theta))))
        tip_y = int(round(float(arrow_cy) - (half_len * math.cos(theta))))
        tail_x = int(round(float(arrow_cx) - (half_len * math.sin(theta))))
        tail_y = int(round(float(arrow_cy) + (half_len * math.cos(theta))))
        pygame.draw.line(surface, cyan, (tail_x, tail_y), (tip_x, tip_y), 2)
        left_theta = theta + math.radians(155.0)
        right_theta = theta - math.radians(155.0)
        ah = max(5, int(round(0.07 * DPI)))
        p2 = (int(round(tip_x + ah * math.sin(left_theta))), int(round(tip_y - ah * math.cos(left_theta))))
        p3 = (int(round(tip_x + ah * math.sin(right_theta))), int(round(tip_y - ah * math.cos(right_theta))))
        pygame.draw.polygon(surface, cyan, [(tip_x, tip_y), p2, p3])

    def _draw_res_popup(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        if not self._show_res_popup:
            return
        grid_rect = self._data_entry_grid_rect(rect)
        row_start, row_end = self._res_popup_rows(rect)
        popup_rect = self._res_popup_rect(rect)
        cyan = (0, 255, 255)
        white = (255, 255, 255)
        surface.fill((0, 0, 0), popup_rect)
        pygame.draw.rect(surface, cyan, popup_rect, 1)
        for c in (1, 2):
            x = grid_rect.x + ((1 + c) * GRID_CELL_W)
            pygame.draw.line(surface, cyan, (x, popup_rect.top), (x, popup_rect.bottom), 1)
        for r in range(row_start + 1, row_end + 1):
            y = grid_rect.y + ((r - 1) * GRID_CELL_H)
            pygame.draw.line(surface, cyan, (popup_rect.left, y), (popup_rect.right, y), 1)
        labels = {
            self._res_popup_option_cells(rect)[0]: "1",
            self._res_popup_option_cells(rect)[1]: "2",
            self._res_popup_option_cells(rect)[2]: "3",
            self._res_popup_option_cells(rect)[3]: "4",
            self._res_popup_option_cells(rect)[4]: "5",
            self._res_popup_option_cells(rect)[5]: "6",
        }
        font = get_font(14)
        selected_text = str(self._res_value).strip()
        for cell_name, text in labels.items():
            col = ord(cell_name[0]) - ord("A")
            row = int(cell_name[1:]) - 1
            box = pygame.Rect(grid_rect.x + col * GRID_CELL_W, grid_rect.y + row * GRID_CELL_H, GRID_CELL_W, GRID_CELL_H)
            lines = str(text).split("\n")
            selected = selected_text == str(text)
            rendered = [font.render(line, True, white if selected else cyan) for line in lines]
            total_h = sum(s.get_height() for s in rendered) + max(0, len(rendered) - 1)
            y = box.centery - total_h // 2
            merged_rect: Optional[pygame.Rect] = None
            for surf in rendered:
                rr = surf.get_rect(centerx=box.centerx, y=y)
                surface.blit(surf, rr)
                merged_rect = rr if merged_rect is None else merged_rect.union(rr)
                y += surf.get_height() + 1
            if selected and merged_rect is not None:
                pygame.draw.rect(surface, white, merged_rect.inflate(6, 3), 1)

    def _asr_image_rect(self, rect: pygame.Rect) -> pygame.Rect:
        # Render imagery behind OSBs across the full ASR portal.
        return pygame.Rect(rect.left, rect.top, max(1, rect.width), max(1, rect.height))

    def _draw_capture_image(self, surface: pygame.Surface, rect: pygame.Rect) -> pygame.Rect:
        image_rect = self._asr_image_rect(rect)
        pygame.draw.rect(surface, (0, 0, 0), image_rect, 0)
        self._capture_draw_zoom = 1.0
        self._capture_draw_pan_x = 0.0
        self._capture_draw_pan_y = 0.0
        capture = self._capture_surface
        if str(self._xmit_phase) == "idle" and isinstance(capture, pygame.Surface):
            rot = float(self._capture_rotation_deg) % 360.0
            src_w = max(1, int(capture.get_width()))
            src_h = max(1, int(capture.get_height()))
            dst_w = max(1, int(image_rect.width))
            dst_h = max(1, int(image_rect.height))
            theta = math.radians(rot)
            cos_t = math.cos(theta)
            sin_t = math.sin(theta)
            hx = float(dst_w) * 0.5
            hy = float(dst_h) * 0.5
            sx = float(src_w) * 0.5
            sy = float(src_h) * 0.5
            cover_zoom = 1.0
            for x, y in ((hx, hy), (hx, -hy), (-hx, hy), (-hx, -hy)):
                rx = (x * cos_t) + (y * sin_t)
                ry = (-x * sin_t) + (y * cos_t)
                zx = abs(rx) / max(1e-6, sx)
                zy = abs(ry) / max(1e-6, sy)
                cover_zoom = max(cover_zoom, zx, zy)
            cover_zoom = max(1.0, min(3.5, float(cover_zoom) * 1.02))
            user_zoom = max(1.0, min(6.0, float(self._view_zoom)))
            total_zoom = max(1.0, min(8.5, float(cover_zoom) * float(user_zoom)))
            self._capture_draw_zoom = float(total_zoom)
            if abs(total_zoom - 1.0) > 0.001:
                try:
                    draw_src = pygame.transform.smoothscale(
                        capture,
                        (
                            max(1, int(round(float(src_w) * total_zoom))),
                            max(1, int(round(float(src_h) * total_zoom))),
                        ),
                    )
                except Exception:
                    draw_src = pygame.transform.scale(
                        capture,
                        (
                            max(1, int(round(float(src_w) * total_zoom))),
                            max(1, int(round(float(src_h) * total_zoom))),
                        ),
                    )
            else:
                draw_src = capture
            if abs(rot) > 0.001:
                try:
                    draw_src = pygame.transform.rotozoom(draw_src, rot, 1.0)
                except Exception:
                    try:
                        draw_src = pygame.transform.rotate(draw_src, rot)
                    except Exception:
                        pass
            draw_w = max(1, int(draw_src.get_width()))
            draw_h = max(1, int(draw_src.get_height()))
            max_pan_x = max(0.0, (float(draw_w) - float(dst_w)) * 0.5)
            max_pan_y = max(0.0, (float(draw_h) - float(dst_h)) * 0.5)
            pan_x = max(-max_pan_x, min(max_pan_x, float(self._view_pan_x_px)))
            pan_y = max(-max_pan_y, min(max_pan_y, float(self._view_pan_y_px)))
            crop = pygame.Rect(
                max(0, int(round(((draw_w - dst_w) * 0.5) - pan_x))),
                max(0, int(round(((draw_h - dst_h) * 0.5) - pan_y))),
                min(dst_w, draw_w),
                min(dst_h, draw_h),
            )
            if crop.left + crop.width > draw_w:
                crop.left = max(0, draw_w - crop.width)
            if crop.top + crop.height > draw_h:
                crop.top = max(0, draw_h - crop.height)
            # Use effective clamped pan so overlay/capture-area geometry always
            # matches the displayed cropped image, including at pan edges.
            center_crop_x = (float(draw_w) - float(dst_w)) * 0.5
            center_crop_y = (float(draw_h) - float(dst_h)) * 0.5
            effective_pan_x = float(center_crop_x - float(crop.left))
            effective_pan_y = float(center_crop_y - float(crop.top))
            self._capture_draw_pan_x = float(effective_pan_x)
            self._capture_draw_pan_y = float(effective_pan_y)
            self._view_pan_x_px = float(effective_pan_x)
            self._view_pan_y_px = float(effective_pan_y)
            if crop.width == dst_w and crop.height == dst_h:
                surface.blit(draw_src, image_rect, area=crop)
            else:
                self._capture_draw_pan_x = 0.0
                self._capture_draw_pan_y = 0.0
                self._view_pan_x_px = 0.0
                self._view_pan_y_px = 0.0
                try:
                    scaled = pygame.transform.smoothscale(draw_src, (dst_w, dst_h))
                except Exception:
                    scaled = pygame.transform.scale(draw_src, (dst_w, dst_h))
                surface.blit(scaled, image_rect)
        return image_rect

    def _has_renderable_map(self) -> bool:
        return str(self._xmit_phase) == "idle" and isinstance(self._capture_surface, pygame.Surface)

    def _clear_map(self) -> None:
        self._capture_surface = None
        self._capture_base_surface = None
        self._capture_bounds = None
        self._capture_center_latlon = None
        self._captured_portal_surface = None
        self._capture_draw_zoom = 1.0

    def _capture_current_image_only(self, portal_rect: pygame.Rect) -> bool:
        try:
            w = max(1, int(portal_rect.width))
            h = max(1, int(portal_rect.height))
            shot = pygame.Surface((w, h)).convert()
            shot.fill((0, 0, 0))
            self._draw_capture_image(shot, pygame.Rect(0, 0, w, h))
            self._captured_portal_surface = shot.copy()
            return True
        except Exception as exc:
            print(f"ASR1: CAPTR failed: {exc}")
            return False

    def _store_latest_capture(self) -> bool:
        if not isinstance(self._captured_portal_surface, pygame.Surface):
            print("ASR1: STOR skipped (no CAPTR image available).")
            return False
        try:
            recordings_dir = writable_path("Recordings")
            recordings_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = recordings_dir / f"Capture_ASR1_{ts}.png"
            pygame.image.save(self._captured_portal_surface, str(out_path))
            print(f"ASR1: capture saved to {out_path}")
            return True
        except Exception as exc:
            print(f"ASR1: STOR failed: {exc}")
            return False

    @staticmethod
    def _rotate_xy(px: int, py: int, cx: float, cy: float, deg: float) -> Tuple[int, int]:
        theta = math.radians(float(deg) % 360.0)
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)
        dx = float(px) - float(cx)
        dy = float(py) - float(cy)
        rx = float(cx) + (dx * cos_t) - (dy * sin_t)
        ry = float(cy) + (dx * sin_t) + (dy * cos_t)
        return int(round(rx)), int(round(ry))

    def _transform_overlay_xy(self, px: int, py: int, image_rect: pygame.Rect) -> Tuple[int, int]:
        cx = float(image_rect.centerx)
        cy = float(image_rect.centery)
        zoom = max(1.0, float(self._capture_draw_zoom))
        dx = (float(px) - cx) * zoom
        dy = (float(py) - cy) * zoom
        zx = int(round(cx + dx))
        zy = int(round(cy + dy))
        rot = float(self._capture_rotation_deg) % 360.0
        if abs(rot) > 0.001:
            zx, zy = self._rotate_xy(zx, zy, cx, cy, rot)
        zx += int(round(float(self._capture_draw_pan_x)))
        zy += int(round(float(self._capture_draw_pan_y)))
        return zx, zy

    def _draw_overlay_icons(self, surface: pygame.Surface, image_rect: pygame.Rect) -> None:
        if str(self._xmit_phase) != "idle":
            return
        if (not bool(self._overlay_on)) or self._capture_bounds is None or (not isinstance(self._capture_surface, pygame.Surface)):
            return
        bounds = self._capture_bounds
        min_lon, min_lat, max_lon, max_lat = bounds
        lon_span = max(1e-9, float(max_lon - min_lon))
        lat_span = max(1e-9, float(max_lat - min_lat))
        snap = TSD_ADSB_STATE if isinstance(TSD_ADSB_STATE, dict) else {}
        own = self._read_ownship_lat_lon()
        contacts = Tsd1Format._adsb_contacts(snap.get("raw"), mil_payload=snap.get("mil_raw"))
        now_s = datetime.now(timezone.utc).timestamp()
        last_update_s = Tsd1Format._safe_float(snap.get("last_update_time"))
        if last_update_s is None:
            last_update_s = now_s
        age_s = max(0.0, now_s - float(last_update_s))
        configured_interval_s = Tsd1Format._safe_float(snap.get("min_interval_s"))
        if configured_interval_s is None:
            configured_interval_s = 5.0
        max_project_s = max(2.0, min(45.0, float(configured_interval_s) * 2.5))
        project_dt_s = min(age_s, max_project_s)
        map_rot = float(self._capture_rotation_deg) % 360.0
        for contact in contacts:
            lat = Tsd1Format._safe_float(contact.get("lat"))
            lon = Tsd1Format._safe_float(contact.get("lon"))
            if lat is None or lon is None:
                continue
            is_sim = bool(contact.get("_plugin_sim", False) or contact.get("_sim", False))
            speed_kts = Tsd1Format._safe_float(contact.get("speed_kts"))
            heading = Tsd1Format._safe_float(contact.get("heading"))
            if (not is_sim) and heading is not None and speed_kts is not None and speed_kts > 1.0 and project_dt_s > 0.0:
                travel_nm = float(speed_kts) * (float(project_dt_s) / 3600.0)
                lat, lon = Tsd1Format._project_lat_lon_nm(float(lat), float(lon), float(heading), float(travel_nm))
            u = (float(lon) - float(min_lon)) / lon_span
            v = (float(max_lat) - float(lat)) / lat_span
            if u < -0.02 or u > 1.02 or v < -0.02 or v > 1.02:
                continue
            px = int(round(float(image_rect.left) + (u * float(image_rect.width - 1))))
            py = int(round(float(image_rect.top) + (v * float(image_rect.height - 1))))
            px, py = self._transform_overlay_xy(px, py, image_rect)
            if not image_rect.collidepoint(px, py):
                continue
            aff = str(contact.get("affiliation", "UNKNOWN")).upper().strip()
            dom = str(contact.get("domain", "AIR")).upper().strip()
            icon_size = max(10, int(round(0.22 * DPI)))
            if heading is None and isinstance(own, tuple) and len(own) == 2:
                try:
                    heading = float(Tsd1Format._bearing_and_distance_nm(float(own[0]), float(own[1]), float(lat), float(lon))[0])
                except Exception:
                    heading = 0.0
            icon_heading = (float(heading if heading is not None else 0.0) + map_rot) % 360.0
            icon = Tsd1Format._get_adsb_contact_icon(aff, dom, icon_size, icon_heading)
            if icon is None:
                continue
            ir = icon.get_rect(center=(px, py))
            surface.blit(icon, ir)
        if isinstance(own, tuple) and len(own) == 2:
            own_lat = float(own[0])
            own_lon = float(own[1])
            u = (own_lon - float(min_lon)) / lon_span
            v = (float(max_lat) - own_lat) / lat_span
            if 0.0 <= u <= 1.0 and 0.0 <= v <= 1.0:
                px = int(round(float(image_rect.left) + (u * float(image_rect.width - 1))))
                py = int(round(float(image_rect.top) + (v * float(image_rect.height - 1))))
                px, py = self._transform_overlay_xy(px, py, image_rect)
                if not image_rect.collidepoint(px, py):
                    return
                own_icon = Tsd1Format._get_cyan_aircraft_icon((max(8, int(round(0.30 * DPI))),) * 2)
                if own_icon is not None:
                    orc = own_icon.get_rect(center=(px, py))
                    surface.blit(own_icon, orc)

    def _draw_osb_black_backdrops(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        for label in ("T2", "T3", "T4", "T5", "L3", "L5", "R1", "R2", "R3", "R4"):
            box = self._osb_box(rect, label)
            if box is None:
                continue
            bg = box.inflate(-2, -2)
            if bg.width > 0 and bg.height > 0:
                pygame.draw.rect(surface, (0, 0, 0), bg, 0)

    def render(self, surface, rect, is_primary: bool, context: FormatContext) -> None:
        prev_clip = surface.get_clip()
        surface.set_clip(rect)
        surface.fill((0, 0, 0), rect)
        cyan = (0, 255, 255)
        gray = (128, 128, 128)
        white = (255, 255, 255)

        if self._radar_fail_active():
            self._draw_radar_fail_overlay(surface, rect)
            pygame.draw.rect(surface, cyan, rect, 1)
            surface.set_clip(prev_clip)
            return

        if self._is_none_like_mode():
            self._show_res_popup = False
            if is_primary:
                self._last_primary_rect = rect.copy()
            self._draw_none_mode_radar(surface, rect, align_apex_to_bottom=(not is_primary))
            if not is_primary:
                pygame.draw.rect(surface, cyan, rect, 1)
                surface.set_clip(prev_clip)
                return
            now_ms = int(pygame.time.get_ticks())

            t5 = self._osb_box(rect, "T5")
            if t5 is not None:
                render_button(
                    surface,
                    t5,
                    ButtonState(
                        button_id="ASR1_T5_NONE",
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

            t2 = self._osb_box(rect, "T2")
            if t2 is not None:
                self._draw_header_value_button(
                    surface,
                    t2,
                    "MODE",
                    str(self._mode_value),
                    bool(context.is_osb_flashing("T2")),
                    h_align="center",
                    v_align="top",
                )

            r1 = self._osb_box(rect, "R1")
            if r1 is not None:
                render_button(
                    surface,
                    r1,
                    ButtonState(
                        button_id="ASR1_R1_NONE",
                        button_type=ButtonType.MOMENTARY_SINGLE,
                        text="NORM",
                        is_single_function=True,
                        is_on=bool(not self._view_is_default()),
                        h_align="right",
                        v_align="center",
                        padding=OSB_PADDING,
                        font_size=14,
                        flash_until_ms=1 if context.is_osb_flashing("R1") else 0,
                    ),
                    get_font,
                    now_ms,
                )

            r2 = self._osb_box(rect, "R2")
            if r2 is not None:
                self._draw_header_value_button(
                    surface,
                    r2,
                    "OVERLAY",
                    "GMTI" if bool(self._overlay_on) else "OFF",
                    bool(context.is_osb_flashing("R2")),
                    h_align="right",
                    v_align="center",
                )

            self._draw_none_mode_inc_dec_and_range(
                surface,
                rect,
                l1_flash=bool(context.is_osb_flashing("L1")),
                l2_flash=bool(context.is_osb_flashing("L2")),
            )
            self._draw_overlay_popup(surface, rect)
            self._draw_mode_popup(surface, rect)
            self._draw_control_popup(surface, rect)
            pygame.draw.rect(surface, cyan, rect, 1)
            surface.set_clip(prev_clip)
            return
        self._show_overlay_popup = False

        if not is_primary:
            image_rect = self._draw_capture_image(surface, rect)
            label_font = get_font(14)
            label = label_font.render("ASR1", True, cyan)
            label_rect = label.get_rect(centerx=image_rect.centerx, bottom=image_rect.bottom - 2)
            pygame.draw.rect(surface, (0, 0, 0), label_rect.inflate(6, 2), 0)
            surface.blit(label, label_rect)
            pygame.draw.rect(surface, cyan, rect, 1)
            surface.set_clip(prev_clip)
            return
        self._last_primary_rect = rect.copy()

        now_ms = int(pygame.time.get_ticks())
        self._update_xmit(now_ms)
        image_rect = self._draw_capture_image(surface, rect)
        self._draw_capture_history_boxes(surface, image_rect)
        self._draw_asr_runways_and_tacan(surface, image_rect)
        self._draw_overlay_icons(surface, image_rect)
        self._draw_asr_hotas_status(surface, image_rect)
        t1 = self._osb_box(rect, "T1")
        if t1 is not None:
            render_button(
                surface,
                t1,
                ButtonState(
                    button_id="ASR1_T1",
                    button_type=ButtonType.MOMENTARY_SINGLE,
                    text="ASR1",
                    is_single_function=True,
                    is_on=False,
                    h_align="center",
                    v_align="top",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("T1") else 0,
                ),
                get_font,
                now_ms,
            )
            # Keep a second-line black backdrop under T1 so ASR1 matches two-line top OSB styling.
            t1_font = get_font(14)
            t1_line = t1_font.render("ASR1", True, cyan)
            t1_r1 = t1_line.get_rect(centerx=t1.centerx, y=t1.top + OSB_PADDING)
            t1_r2 = t1_r1.copy()
            t1_r2.y = t1_r1.bottom + 1
            pygame.draw.rect(surface, (0, 0, 0), t1_r2.inflate(6, 2), 0)
        t3 = self._osb_box(rect, "T3")
        if t3 is not None:
            render_button(
                surface,
                t3,
                ButtonState(
                    button_id="ASR1_T3",
                    button_type=ButtonType.MOMENTARY_SINGLE,
                    text="XMIT",
                    is_single_function=True,
                    is_on=False,
                    h_align="center",
                    v_align="top",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("T3") else 0,
                ),
                get_font,
                now_ms,
            )
        t4 = self._osb_box(rect, "T4")
        if t4 is not None:
            render_button(
                surface,
                t4,
                ButtonState(
                    button_id="ASR1_T4",
                    button_type=ButtonType.PAGE_ACCESS,
                    text="BLANK\nMAP",
                    h_align="center",
                    v_align="top",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("T4") else 0,
                ),
                get_font,
                now_ms,
            )
        t5 = self._osb_box(rect, "T5")
        if t5 is not None:
            render_button(
                surface,
                t5,
                ButtonState(
                    button_id="ASR1_T5",
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

        t2 = self._osb_box(rect, "T2")
        if t2 is not None:
            self._draw_header_value_button(
                surface,
                t2,
                "MODE",
                str(self._mode_value),
                bool(context.is_osb_flashing("T2")),
                h_align="center",
                v_align="top",
            )

        r1 = self._osb_box(rect, "R1")
        if r1 is not None:
            render_button(
                surface,
                r1,
                ButtonState(
                    button_id="ASR1_R1",
                    button_type=ButtonType.MOMENTARY_SINGLE,
                    text="NORM",
                    is_single_function=True,
                    is_on=bool(self._has_renderable_map() and (not self._view_is_default())),
                    enabled=bool(self._has_renderable_map()),
                    h_align="right",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("R1") else 0,
                ),
                get_font,
                now_ms,
            )
        r2 = self._osb_box(rect, "R2")
        if r2 is not None:
            self._draw_header_value_button(
                surface,
                r2,
                "OVRLAY",
                "ON" if bool(self._overlay_on) else "OFF",
                bool(context.is_osb_flashing("R2")),
                h_align="right",
                v_align="center",
            )
        action_color = cyan if self._has_renderable_map() else gray
        r3 = self._osb_box(rect, "R3")
        if r3 is not None:
            render_button(
                surface,
                r3,
                ButtonState(
                    button_id="ASR1_R3",
                    button_type=ButtonType.MOMENTARY_SINGLE,
                    text="CAPTR",
                    is_single_function=True,
                    is_on=False,
                    enabled=bool(self._has_renderable_map()),
                    h_align="right",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("R3") else 0,
                ),
                get_font,
                now_ms,
            )
        r4 = self._osb_box(rect, "R4")
        if r4 is not None:
            render_button(
                surface,
                r4,
                ButtonState(
                    button_id="ASR1_R4",
                    button_type=ButtonType.MOMENTARY_SINGLE,
                    text="STOR",
                    is_single_function=True,
                    is_on=False,
                    enabled=bool(self._has_renderable_map()),
                    h_align="right",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("R4") else 0,
                ),
                get_font,
                now_ms,
            )

        l3 = self._osb_box(rect, "L3")
        if l3 is not None:
            asr_state = self._asr_runtime_state()
            render_button(
                surface,
                l3,
                ButtonState(
                    button_id="ASR1_L3",
                    button_type=ButtonType.GOL,
                    function_label="SPNT",
                    options=["TGT"],
                    selected_index=0,
                    enabled=True,
                    is_on=bool(asr_state.get("spnt_tgt", False)),
                    h_align="left",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("L3") else 0,
                ),
                get_font,
                now_ms,
            )
        l5 = self._osb_box(rect, "L5")
        if l5 is not None:
            self._draw_header_value_button(
                surface,
                l5,
                "RES",
                str(self._res_value),
                bool(context.is_osb_flashing("L5")),
                h_align="left",
                v_align="center",
            )

        status_text = self._xmit_status_text(now_ms)
        if status_text:
            status_font = get_font(22)
            status_surf = status_font.render(status_text, True, (255, 255, 255))
            status_rect = status_surf.get_rect(center=image_rect.center)
            pygame.draw.rect(surface, (0, 0, 0), status_rect.inflate(8, 4), 0)
            surface.blit(status_surf, status_rect)

        self._draw_sar_reference_and_cursor(surface, rect, image_rect)
        self._draw_mode_popup(surface, rect)
        self._draw_res_popup(surface, rect)
        self._draw_control_popup(surface, rect)
        pygame.draw.rect(surface, cyan, rect, 1)
        surface.set_clip(prev_clip)

    def on_click(self, pos: Tuple[int, int], rect: pygame.Rect, context: FormatContext) -> bool:
        _ = context
        if self._show_overlay_popup:
            popup_rect = self._overlay_popup_rect(rect)
            if not popup_rect.collidepoint(pos):
                self._show_overlay_popup = False
                return False
            cell = self._grid_cell_at_pos(pos, rect)
            if cell == "B3":
                self._overlay_on = False
                self._show_overlay_popup = False
            elif cell == "C3":
                self._overlay_on = True
                self._show_overlay_popup = False
            return True
        if self._show_mode_popup:
            popup_rect = self._mode_popup_rect(rect)
            if not popup_rect.collidepoint(pos):
                self._show_mode_popup = False
                return False
            cell = self._grid_cell_at_pos(pos, rect)
            option_cells = self._mode_popup_option_cells()
            if cell in option_cells:
                idx = int(option_cells.index(cell))
                opts = self._mode_options()
                if 0 <= idx < len(opts):
                    self._mode_value = str(opts[idx]).upper()
                self._show_mode_popup = False
            return True
        if self._show_cntl_popup:
            popup_rect = self._control_popup_rect(rect)
            if not popup_rect.collidepoint(pos):
                self._show_cntl_popup = False
                self._cntl_selected_field = ""
                return False
            grid_rect = self._data_entry_grid_rect(rect)
            rel_x = pos[0] - grid_rect.x
            rel_y = pos[1] - grid_rect.y
            col = max(0, min(4, int(rel_x // GRID_CELL_W)))
            row = max(0, min(7, int(rel_y // GRID_CELL_H)))
            cell = f"{chr(ord('A') + col)}{row + 1}"
            field_map = {
                "B2": "gain",
                "C2": "gamma",
                "D2": "shadow",
            }
            keypad_map = {
                "B3": "1", "C3": "2", "D3": "3",
                "B4": "4", "C4": "5", "D4": "6",
                "B5": "7", "C5": "8", "D5": "9",
                "B6": ".", "C6": "0", "D6": "BS",
            }
            if cell in field_map:
                clicked = str(field_map[cell]).strip().lower()
                if self._cntl_selected_field == clicked:
                    self._commit_control_entry(clicked)
                    self._cntl_selected_field = ""
                else:
                    prev = str(self._cntl_selected_field).strip().lower()
                    if prev in {"gain", "gamma", "shadow"}:
                        self._commit_control_entry(prev)
                    self._cntl_input_by_field[clicked] = ""
                    self._cntl_selected_field = clicked
                return True
            token = keypad_map.get(cell)
            if token is not None:
                self._control_popup_handle_key(str(token))
                return True
            return True
        if not self._show_res_popup:
            return False
        popup_rect = self._res_popup_rect(rect)
        if not popup_rect.collidepoint(pos):
            self._show_res_popup = False
            return False
        cell = self._grid_cell_at_pos(pos, rect)
        option_cells = self._res_popup_option_cells(rect)
        if cell in option_cells:
            self._res_value = str(option_cells.index(cell) + 1)
            self._show_res_popup = False
        return True

    def on_osb(self, label: str, context: FormatContext) -> bool:
        if label == "T1":
            context.request_vded(context.portal_index, "MENU")
            return True
        if self._is_none_like_mode():
            self._show_res_popup = False
            if label == "T2":
                self._show_overlay_popup = False
                self._show_cntl_popup = False
                self._show_mode_popup = not self._show_mode_popup
                return True
            if label == "T5":
                self._show_overlay_popup = False
                self._show_mode_popup = False
                self._show_cntl_popup = not self._show_cntl_popup
                if not self._show_cntl_popup:
                    self._cntl_selected_field = ""
                return True
            if label == "R1":
                self.reset_view()
                return True
            if label == "R2":
                self._show_cntl_popup = False
                self._show_mode_popup = False
                self._show_overlay_popup = not self._show_overlay_popup
                return True
            if label == "L1":
                self._show_cntl_popup = False
                self._show_mode_popup = False
                self._show_overlay_popup = False
                self._adjust_none_range(+1)
                return True
            if label == "L2":
                self._show_cntl_popup = False
                self._show_mode_popup = False
                self._show_overlay_popup = False
                self._adjust_none_range(-1)
                return True
            return False
        if label == "T3":
            self._start_xmit(int(pygame.time.get_ticks()))
            return True
        if label == "T4":
            self._clear_map()
            return True
        if label == "R3":
            if not self._has_renderable_map():
                return True
            target = self._last_primary_rect
            if not isinstance(target, pygame.Rect):
                target = pygame.Rect(0, 0, max(1, 5 * GRID_CELL_W), max(1, 8 * GRID_CELL_H))
            self._capture_current_image_only(target)
            return True
        if label == "R4":
            if not self._has_renderable_map():
                return True
            self._store_latest_capture()
            return True
        if label == "R1":
            self.reset_view()
            return True
        if label == "R2":
            self._overlay_on = not bool(self._overlay_on)
            return True
        if label == "L5":
            self._show_mode_popup = False
            self._show_cntl_popup = False
            self._show_res_popup = not self._show_res_popup
            return True
        if label == "L3":
            state = self._asr_runtime_state()
            state["spnt_tgt"] = not bool(state.get("spnt_tgt", False))
            state["nts_designated"] = bool(state.get("spnt_tgt", False))
            state["nts_kind"] = "AS"
            state["spnt_last_ms"] = int(pygame.time.get_ticks())
            return True
        if label == "T5":
            self._show_mode_popup = False
            self._show_res_popup = False
            self._show_cntl_popup = not self._show_cntl_popup
            if not self._show_cntl_popup:
                self._cntl_selected_field = ""
            return True
        if label == "T2":
            self._show_res_popup = False
            self._show_cntl_popup = False
            self._show_mode_popup = not self._show_mode_popup
            return True
        if label in {"T5"}:
            return True
        return False

    def osb_is_interactive(self, label: str) -> bool:
        if self._is_none_like_mode():
            return label in {"T1", "T2", "T5", "R1", "R2", "L1", "L2"}
        return label in {"T1", "T2", "T3", "T4", "T5", "L3", "L5", "R1", "R2", "R3", "R4"}
