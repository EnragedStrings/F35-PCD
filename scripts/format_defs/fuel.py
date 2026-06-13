from formats import *  # noqa: F401,F403


class FuelFormat(FormatBase):
    name: str = "FUEL"
    _shared_fuel_qty: Dict[str, float] = {
        "F1": 5100.0,
        "F1I": 1300.0,
        "F2L": 1150.0,
        "F2R": 1150.0,
        "F3L": 2150.0,
        "F3R": 2150.0,
        "F4L": 1100.0,
        "F4R": 1100.0,
        "F5L": 1000.0,
        "F5R": 1000.0,
        "LW": 1150.0,
        "RW": 1150.0,
    }
    _shared_fuel_max: Dict[str, float] = {
        "F1": 5100.0,
        "F1I": 1300.0,
        "F2L": 1150.0,
        "F2R": 1150.0,
        "F3L": 2150.0,
        "F3R": 2150.0,
        "F4L": 1100.0,
        "F4R": 1100.0,
        "F5L": 1000.0,
        "F5R": 1000.0,
        "LW": 1150.0,
        "RW": 1150.0,
    }
    _shared_hazard_cover_closed: Dict[str, bool] = {"L2": True, "L6": True, "R6": True}
    _shared_hazard_on: Dict[str, bool] = {"L2": False, "L6": False, "R6": False}
    _shared_hazard_confirm_pending_by_scope: Dict[object, Optional[str]] = {}
    _shared_refuel_t2_on: bool = False
    _shared_total_lbs: float = 0.0
    _shared_data_values: Dict[str, float] = {"L3": 0.0, "R2": 0.0, "R3": 0.0}
    _shared_data_selected_by_scope: Dict[object, Optional[str]] = {}
    _shared_data_inputs_by_scope: Dict[object, Dict[str, str]] = {}
    _popup_anchor_portal_idx: int = 0
    _popup_anchor_scope_key: object = "portal:0"
    _shared_tank_degrd: Dict[str, bool] = {k: False for k in _shared_fuel_qty.keys()}
    _shared_sensor_degrd: Dict[str, bool] = {k: False for k in _shared_fuel_qty.keys()}
    _shared_stale_data: bool = False
    _shared_valve_state: Dict[str, Dict[str, bool]] = {
        "F1": {"V1": True, "V2": False, "V3": False},
        "F3L": {"V1": False, "V2": False},
        "F3R": {"V1": False, "V2": False},
    }
    _shared_valve_degrd: Dict[str, Dict[str, bool]] = {
        "F1": {"V1": False, "V2": False, "V3": False},
        "F3L": {"V1": False, "V2": False},
        "F3R": {"V1": False, "V2": False},
    }

    def __init__(self) -> None:
        # Shared tank state across all FUEL instances (primary, subportal, popup).
        self.fuel_qty = FuelFormat._shared_fuel_qty
        self.fuel_max = FuelFormat._shared_fuel_max
        # Guarded hazard-bordered OSBs are shared across instances so portal and popup stay synced.
        self._hazard_cover_closed = FuelFormat._shared_hazard_cover_closed
        self._hazard_on = FuelFormat._shared_hazard_on
        self._data_values = FuelFormat._shared_data_values

    @classmethod
    def _scope_key(cls) -> object:
        try:
            key = cls._popup_anchor_scope_key
            if key is not None:
                return key
        except Exception:
            pass
        try:
            idx = int(cls._popup_anchor_portal_idx)
        except Exception:
            idx = 0
        return f"portal:{max(0, min(3, idx))}"

    def _set_popup_anchor_scope_key(self, scope_key: object) -> None:
        FuelFormat._popup_anchor_scope_key = scope_key

    def _set_popup_anchor_portal_index(self, portal_index: Optional[int]) -> None:
        idx: Optional[int] = None
        try:
            if portal_index is not None:
                idx = int(portal_index)
        except Exception:
            idx = None
        if idx is None:
            idx = _active_render_portal_index()
        if idx is None:
            idx = int(FuelFormat._popup_anchor_portal_idx)
        FuelFormat._popup_anchor_portal_idx = max(0, min(3, int(idx)))
        try:
            current_scope = str(FuelFormat._popup_anchor_scope_key)
        except Exception:
            current_scope = ""
        if current_scope.startswith("portal:") or current_scope == "":
            FuelFormat._popup_anchor_scope_key = f"portal:{FuelFormat._popup_anchor_portal_idx}"

    @classmethod
    def _data_inputs_for_scope(cls) -> Dict[str, str]:
        scope = cls._scope_key()
        current = cls._shared_data_inputs_by_scope.get(scope)
        if isinstance(current, dict):
            return current
        fresh = {"L3": "", "R2": "", "R3": ""}
        cls._shared_data_inputs_by_scope[scope] = fresh
        return fresh

    @staticmethod
    def _hazard_labels() -> Set[str]:
        return {"L2", "L6", "R6"}

    def _hazard_confirm_pending(self) -> Optional[str]:
        pending = FuelFormat._shared_hazard_confirm_pending_by_scope.get(FuelFormat._scope_key())
        if pending in self._hazard_labels():
            return str(pending)
        return None

    def _set_hazard_confirm_pending(self, label: Optional[str]) -> None:
        scope = FuelFormat._scope_key()
        if label in self._hazard_labels():
            FuelFormat._shared_hazard_confirm_pending_by_scope[scope] = str(label)
        else:
            FuelFormat._shared_hazard_confirm_pending_by_scope[scope] = None

    @staticmethod
    def _hazard_confirm_line2(label: str) -> str:
        mapping = {
            "L2": "DUMP OPEN",
            "L6": "CLOSE MFSOV",
            "R6": "OPEN REFUEL",
        }
        return str(mapping.get(str(label), ""))

    def _hazard_confirm_popup_rect(self, rect: pygame.Rect) -> pygame.Rect:
        width = max(1, int(round(4.25 * DPI)))
        height = max(1, int(round(1.5 * DPI)))
        top_count = 5 if rect.width < int(10 * DPI) else 10
        top_offset = DISPLAY_OSB_H if top_count > 0 else 0
        row2_center_y = rect.y + top_offset + DISPLAY_OSB_H + (DISPLAY_OSB_H // 2)
        x = rect.centerx - (width // 2)
        y = int(row2_center_y - (height / 2))
        return pygame.Rect(x, y, width, height)

    def _draw_hazard_confirm_popup(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        pending = self._hazard_confirm_pending()
        if pending is None:
            return
        popup = self._hazard_confirm_popup_rect(rect)
        pygame.draw.rect(surface, (0, 255, 255), popup)
        pygame.draw.rect(surface, (255, 255, 255), popup, 1)
        line1 = "CONFIRM"
        line2 = self._hazard_confirm_line2(pending)
        font = get_font(20)
        s1 = font.render(line1, True, (0, 0, 0))
        s2 = font.render(line2, True, (0, 0, 0))
        total_h = s1.get_height() + s2.get_height() + 4
        y = popup.centery - (total_h // 2)
        r1 = s1.get_rect(centerx=popup.centerx)
        r1.y = y
        y = r1.bottom + 4
        r2 = s2.get_rect(centerx=popup.centerx)
        r2.y = y
        surface.blit(s1, r1)
        surface.blit(s2, r2)

    @staticmethod
    def _is_airborne() -> bool:
        try:
            panel = PANEL_BUTTON_STATES if isinstance(PANEL_BUTTON_STATES, dict) else {}
            aircraft = panel.get("AIRCRAFT", {}) if isinstance(panel, dict) else {}
            if not isinstance(aircraft, dict):
                return False
            altitude_ft = float(aircraft.get("ALTITUDE_FT", 0.0))
            return altitude_ft > 0.0
        except Exception:
            return False

    def _tank_ratio(self, tank_id: str) -> float:
        if self._sensor_degraded(tank_id):
            return 0.0
        max_qty = max(1.0, float(self.fuel_max.get(tank_id, 1.0)))
        qty = float(self.fuel_qty.get(tank_id, 0.0))
        return max(0.0, min(1.0, qty / max_qty))

    @staticmethod
    def _effective_tank_key(tank_id: str) -> str:
        key = str(tank_id).upper().strip()
        if key == "F1I":
            return "F1"
        return key

    def _tank_degraded(self, tank_id: str) -> bool:
        key = self._effective_tank_key(tank_id)
        raw = getattr(FuelFormat, "_shared_tank_degrd", {})
        return bool(raw.get(key, False) or raw.get(tank_id, False)) if isinstance(raw, dict) else False

    def _sensor_degraded(self, tank_id: str) -> bool:
        key = self._effective_tank_key(tank_id)
        raw = getattr(FuelFormat, "_shared_sensor_degrd", {})
        return bool(raw.get(key, False) or raw.get(tank_id, False)) if isinstance(raw, dict) else False

    def _valve_state(self, tank_id: str, valve: str, default: bool = False) -> bool:
        raw = getattr(FuelFormat, "_shared_valve_state", {})
        if not isinstance(raw, dict):
            return bool(default)
        local = raw.get(str(tank_id).upper().strip(), {})
        if not isinstance(local, dict):
            return bool(default)
        return bool(local.get(str(valve).upper().strip(), default))

    def _valve_degraded(self, tank_id: str, valve: str) -> bool:
        raw = getattr(FuelFormat, "_shared_valve_degrd", {})
        if not isinstance(raw, dict):
            return False
        local = raw.get(str(tank_id).upper().strip(), {})
        if not isinstance(local, dict):
            return False
        return bool(local.get(str(valve).upper().strip(), False))

    def _draw_rect_tank(self, surface: pygame.Surface, tank_rect: pygame.Rect, tank_id: str) -> None:
        purple = (66, 100, 231)
        white = (255, 255, 255)
        green = (0, 255, 0)
        yellow = (255, 255, 0)
        tank_degrd = self._tank_degraded(tank_id)
        sensor_degrd = self._sensor_degraded(tank_id)
        inner = tank_rect.inflate(-2, -2)
        if inner.width > 0 and inner.height > 0:
            pygame.draw.rect(surface, (0, 0, 0), inner)
            if tank_id == "F1":
                # F1 is split: upper 1/3 is F1, lower 2/3 is F1I.
                split_y = inner.top + int(inner.height / 3.0)
                top_h = max(1, split_y - inner.top)
                bot_h = max(1, inner.bottom - split_y)

                top_ratio = self._tank_ratio("F1")
                bot_ratio = self._tank_ratio("F1I")

                top_fill_h = int(top_h * top_ratio)
                bot_fill_h = int(bot_h * bot_ratio)
                if top_fill_h > 0:
                    top_fill = pygame.Rect(inner.left, inner.top + (top_h - top_fill_h), inner.width, top_fill_h)
                    pygame.draw.rect(surface, purple, top_fill)
                if bot_fill_h > 0:
                    bot_fill = pygame.Rect(inner.left, split_y + (bot_h - bot_fill_h), inner.width, bot_fill_h)
                    pygame.draw.rect(surface, purple, bot_fill)
            else:
                ratio = self._tank_ratio(tank_id)
                fill_h = int(inner.height * ratio)
                if fill_h > 0:
                    fill_rect = pygame.Rect(inner.left, inner.bottom - fill_h, inner.width, fill_h)
                    pygame.draw.rect(surface, purple, fill_rect)
        pygame.draw.rect(surface, yellow if tank_degrd else white, tank_rect, 1)

        if tank_id == "F1":
            split_y = inner.top + int(inner.height / 3.0)
            pygame.draw.line(surface, yellow if tank_degrd else white, (inner.left, split_y), (inner.right, split_y), 1)

        font_small = get_font(14)
        txt_color = yellow if sensor_degrd else green
        label_surface = font_small.render(tank_id, True, txt_color)
        top_value_text = "XXXX" if sensor_degrd else str(int(self.fuel_qty.get("F1" if tank_id == "F1" else tank_id, 0.0)))
        value_surface = font_small.render(top_value_text, True, txt_color)
        label_rect = label_surface.get_rect()
        label_rect.topleft = (tank_rect.left + 4, tank_rect.top + 2)
        surface.blit(label_surface, label_rect)
        if tank_id == "F1":
            # Top quantity (F1) near top.
            top_rect = value_surface.get_rect()
            top_rect.centerx = tank_rect.centerx
            top_rect.y = tank_rect.top + 2
            surface.blit(value_surface, top_rect)
            # Bottom quantity (F1I) centered in lower 2/3.
            f1i_value_text = "XXXX" if sensor_degrd else str(int(self.fuel_qty.get("F1I", 0.0)))
            f1i_surface = font_small.render(f1i_value_text, True, txt_color)
            bottom_area_top = inner.top + int(inner.height / 3.0)
            bottom_area_h = max(1, inner.bottom - bottom_area_top)
            f1i_rect = f1i_surface.get_rect()
            f1i_rect.centerx = tank_rect.centerx
            f1i_rect.centery = bottom_area_top + (bottom_area_h // 2)
            surface.blit(f1i_surface, f1i_rect)
        else:
            value_rect = value_surface.get_rect()
            value_rect.centerx = tank_rect.centerx
            value_rect.y = tank_rect.top + 20
            surface.blit(value_surface, value_rect)

    def _draw_poly_tank(self, surface: pygame.Surface, points: List[Tuple[int, int]], tank_id: str) -> None:
        purple = (66, 100, 231)
        white = (255, 255, 255)
        green = (0, 255, 0)
        yellow = (255, 255, 0)
        tank_degrd = self._tank_degraded(tank_id)
        sensor_degrd = self._sensor_degraded(tank_id)
        ratio = self._tank_ratio(tank_id)

        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        bbox = pygame.Rect(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
        if bbox.width <= 0 or bbox.height <= 0:
            return

        local_points = [(x - bbox.left, y - bbox.top) for x, y in points]
        pygame.draw.polygon(surface, (0, 0, 0), points, 0)

        fill_layer = pygame.Surface((bbox.width, bbox.height), pygame.SRCALPHA)
        pygame.draw.polygon(fill_layer, (*purple, 255), local_points, 0)
        fill_top = int(bbox.height * (1.0 - ratio))
        fill_top = max(0, min(bbox.height, fill_top))
        if fill_top < bbox.height:
            src = pygame.Rect(0, fill_top, bbox.width, bbox.height - fill_top)
            surface.blit(fill_layer, (bbox.left, bbox.top + fill_top), src)

        pygame.draw.polygon(surface, yellow if tank_degrd else white, points, 1)

        font_small = get_font(14)
        txt_color = yellow if sensor_degrd else green
        label_surface = font_small.render(tank_id, True, txt_color)
        value_text = "XXXX" if sensor_degrd else str(int(self.fuel_qty.get(tank_id, 0.0)))
        value_surface = font_small.render(value_text, True, txt_color)

        # Wing tank label sits at the sloped-top depth (top_dy level), centered horizontally.
        label_level_y = points[1][1] if len(points) > 1 else bbox.top
        label_rect = label_surface.get_rect(centerx=bbox.centerx)
        label_rect.centery = label_level_y

        # Fuel quantity text centered vertically within the wing tank bounds.
        value_rect = value_surface.get_rect(center=(bbox.centerx, bbox.centery))
        surface.blit(label_surface, label_rect)
        surface.blit(value_surface, value_rect)

    def _compute_cg(self) -> float:
        # Simple weighted station model so CG changes with tank distribution.
        station = {
            "F1": 25.0,
            "F1I": 25.0,
            "F2L": 27.0, "F2R": 27.0,
            "F3L": 30.0, "F3R": 30.0,
            "F4L": 32.0, "F4R": 32.0,
            "F5L": 34.0, "F5R": 34.0,
            "LW": 33.0, "RW": 33.0,
        }
        total = sum(float(v) for v in self.fuel_qty.values())
        if total <= 0:
            return 0.0
        moment = sum(float(self.fuel_qty[k]) * station.get(k, 30.0) for k in self.fuel_qty.keys())
        return moment / total

    def _draw_primary_tanks(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        # In 10x7 expanded mode, all tank geometry scales to 1.3x.
        tank_scale = 1.3 if rect.width >= int(10 * DPI) - 1 else 1.0
        left_margin = GRID_CELL_W + 8
        right_margin = GRID_CELL_W + 8
        top_margin = GRID_CELL_H + 6
        content = pygame.Rect(
            rect.left + left_margin,
            rect.top + top_margin,
            rect.width - left_margin - right_margin,
            rect.height - top_margin - GRID_CELL_H - 6,
        )
        cx = content.centerx
        gap_x = max(6, int(0.08 * DPI * tank_scale))
        gap_y = max(4, int(0.06 * DPI * tank_scale))
        gap_z = max(4, int(0.15 * DPI * tank_scale))
        gap_w = max(4, int(0.45 * DPI * tank_scale))

        w_big = max(70, int(1.35 * DPI * tank_scale))
        w_med = max(54, int(w_big * 0.65))
        w_mid = max(54, int(w_big * 0.5))
        w_small = max(40, int((1.2 / 3.0) * w_big))
        h_f1 = max(42, int(1 * DPI * tank_scale))
        h_f2 = max(36, int(0.7 * DPI * tank_scale))
        h_f3 = max(50, int(0.78 * DPI * tank_scale))
        h_f4 = max(42, int(0.78 * DPI * tank_scale))
        h_f5 = max(32, int(0.78 * DPI * tank_scale))

        y = content.top - int(44 * tank_scale) + 15
        f1_extra_up = 20
        f1 = pygame.Rect(cx - int(w_big * 0.45), y - f1_extra_up, int(w_big * 0.9), h_f1 + f1_extra_up)
        y = f1.bottom + gap_y

        f2l = pygame.Rect(cx - gap_x // 2 - w_mid, y, w_mid, h_f2)
        f2r = pygame.Rect(cx + gap_x // 2, y, w_mid, h_f2)
        y = f2l.bottom + gap_z

        f3l = pygame.Rect(cx - gap_x // 2 - w_med, y, w_med, h_f3)
        f3r = pygame.Rect(cx + gap_x // 2, y, w_med, h_f3)
        cg_y = f3l.bottom + max(2, int(0.04 * DPI))
        y = cg_y + max(16, int(0.22 * DPI))

        f4l = pygame.Rect(cx - gap_x // 2 - w_med, y, w_med, h_f4)
        f4r = pygame.Rect(cx + gap_x // 2, y, w_med, h_f4)
        y = f4l.bottom + gap_y

        f5l = pygame.Rect(cx - gap_w // 2 - w_small, y, w_small, h_f5)
        f5r = pygame.Rect(cx + gap_w // 2, y, w_small, h_f5)

        # Wing trapezoids: start at top of F3 and end at 1/3 of F5 height.
        y_top = f3r.top + 3
        y_bottom = f5r.top + f5r.height // 3
        inner_gap = max(4, int(0.07 * DPI * tank_scale))
        wing_left_limit = rect.left + GRID_CELL_W + 4
        wing_right_limit = rect.right - GRID_CELL_W - 4
        top_dy = int(0.5 * DPI * tank_scale)
        bottom_dy = int(0.5 * DPI * tank_scale)
        span_top = int(0.5 * DPI * tank_scale)
        span_bottom = int(0.5 * DPI * tank_scale)

        # Right wing: inner edge near fuselage, outer edge points outward.
        rw_inner_top = (f3r.right + inner_gap, y_top)
        rw_inner_bottom = (f3r.right + inner_gap, y_bottom)
        rw_outer_top_x = min(wing_right_limit, rw_inner_top[0] + span_top)
        rw_outer_bottom_x = min(wing_right_limit, rw_inner_bottom[0] + span_bottom)
        rw_points = [
            rw_inner_top,
            (rw_outer_top_x, y_top + top_dy),
            (rw_outer_bottom_x, y_bottom - bottom_dy),
            rw_inner_bottom,
        ]

        # Left wing: mirror of right wing.
        lw_inner_top = (f3l.left - inner_gap, y_top)
        lw_inner_bottom = (f3l.left - inner_gap, y_bottom)
        lw_outer_top_x = max(wing_left_limit, lw_inner_top[0] - span_top)
        lw_outer_bottom_x = max(wing_left_limit, lw_inner_bottom[0] - span_bottom)
        lw_points = [
            lw_inner_top,
            (lw_outer_top_x, y_top + top_dy),
            (lw_outer_bottom_x, y_bottom - bottom_dy),
            lw_inner_bottom,
        ]

        self._draw_rect_tank(surface, f1, "F1")
        self._draw_rect_tank(surface, f2l, "F2L")
        self._draw_rect_tank(surface, f2r, "F2R")
        self._draw_rect_tank(surface, f3l, "F3L")
        self._draw_rect_tank(surface, f3r, "F3R")
        self._draw_rect_tank(surface, f4l, "F4L")
        self._draw_rect_tank(surface, f4r, "F4R")
        self._draw_rect_tank(surface, f5l, "F5L")
        self._draw_rect_tank(surface, f5r, "F5R")
        self._draw_poly_tank(surface, lw_points, "LW")
        self._draw_poly_tank(surface, rw_points, "RW")

        # Bottom markers: F1i gets 3x "B" circles; F3L/F3R get 2x "T" circles each.
        white = (255, 255, 255)
        black = (0, 0, 0)
        green = (0, 255, 0)

        def draw_letter_circle(
            cx: int,
            cy: int,
            radius: int,
            fill_color: Tuple[int, int, int],
            border_color: Tuple[int, int, int],
            letter: str,
            letter_color: Tuple[int, int, int],
            *,
            degraded: bool = False,
        ) -> None:
            r = max(4, int(radius))
            center = (int(cx), int(cy))
            pygame.draw.circle(surface, fill_color, center, r, 0)
            pygame.draw.circle(surface, border_color, center, r, 1)
            if degraded:
                cross = (255, 255, 0)
                inset = max(2, int(r * 0.55))
                pygame.draw.line(surface, cross, (center[0] - inset, center[1] - inset), (center[0] + inset, center[1] + inset), 2)
                pygame.draw.line(surface, cross, (center[0] - inset, center[1] + inset), (center[0] + inset, center[1] - inset), 2)
            else:
                letter_font = get_font(max(10, int(round(r * 1.5))))
                letter_surf = letter_font.render(str(letter), True, letter_color)
                letter_rect = letter_surf.get_rect(center=center)
                surface.blit(letter_surf, letter_rect)

        # F1i marker row (inside lower F1 segment).
        f1_inner = f1.inflate(-2, -2)
        f1_split_y = f1_inner.top + int(f1_inner.height / 3.0)
        f1i_h = max(1, f1_inner.bottom - f1_split_y)
        f1_r = max(5, int(min(f1_inner.width, f1i_h) * 0.13))
        f1_y = f1_inner.bottom - f1_r - max(2, int(0.04 * DPI * tank_scale))
        f1_dx = max(int(f1_r * 1.9), int(f1_inner.width * 0.24))
        f1_cx = f1.centerx
        f1_left_x = max(f1_inner.left + f1_r + 1, f1_cx - f1_dx)
        f1_right_x = min(f1_inner.right - f1_r - 1, f1_cx + f1_dx)
        f1_v1_on = self._valve_state("F1", "V1", True)
        f1_v2_on = self._valve_state("F1", "V2", False)
        f1_v3_on = self._valve_state("F1", "V3", False)
        f1_v1_degrd = self._valve_degraded("F1", "V1")
        f1_v2_degrd = self._valve_degraded("F1", "V2")
        f1_v3_degrd = self._valve_degraded("F1", "V3")
        draw_letter_circle(
            f1_left_x, f1_y, f1_r,
            black if f1_v1_degrd else (green if f1_v1_on else black),
            white if f1_v1_degrd else (green if f1_v1_on else white),
            "B",
            black if f1_v1_on else white,
            degraded=f1_v1_degrd,
        )
        draw_letter_circle(
            f1_cx, f1_y, f1_r,
            black if f1_v2_degrd else (green if f1_v2_on else black),
            white if f1_v2_degrd else (green if f1_v2_on else white),
            "B",
            black if f1_v2_on else white,
            degraded=f1_v2_degrd,
        )
        draw_letter_circle(
            f1_right_x, f1_y, f1_r,
            black if f1_v3_degrd else (green if f1_v3_on else black),
            white if f1_v3_degrd else (green if f1_v3_on else white),
            "B",
            black if f1_v3_on else white,
            degraded=f1_v3_degrd,
        )

        # F3L / F3R marker rows (two per tank).
        def draw_f3_t_markers(tank: pygame.Rect, tank_id: str) -> None:
            inner = tank.inflate(-2, -2)
            r = max(5, int(min(inner.width, inner.height) * 0.12))
            y_mark = inner.bottom - r - max(2, int(0.04 * DPI * tank_scale))
            dx = max(int(r * 1.6), int(inner.width * 0.18))
            cx = inner.centerx
            left_x = max(inner.left + r + 1, cx - dx)
            right_x = min(inner.right - r - 1, cx + dx)
            v1_on = self._valve_state(tank_id, "V1", False)
            v2_on = self._valve_state(tank_id, "V2", False)
            v1_degrd = self._valve_degraded(tank_id, "V1")
            v2_degrd = self._valve_degraded(tank_id, "V2")
            draw_letter_circle(
                left_x, y_mark, r,
                black if v1_degrd else (green if v1_on else black),
                white if v1_degrd else (green if v1_on else white),
                "T",
                black if v1_on else white,
                degraded=v1_degrd,
            )
            draw_letter_circle(
                right_x, y_mark, r,
                black if v2_degrd else (green if v2_on else black),
                white if v2_degrd else (green if v2_on else white),
                "T",
                black if v2_on else white,
                degraded=v2_degrd,
            )

        draw_f3_t_markers(f3l, "F3L")
        draw_f3_t_markers(f3r, "F3R")

        # Fuel summary block to the right of F1.
        total_fuel = sum(float(v) for v in self.fuel_qty.values())
        int_fuel = total_fuel
        ext_fuel = 0.0
        tank_degrd_map = getattr(FuelFormat, "_shared_tank_degrd", {})
        sensor_degrd_map = getattr(FuelFormat, "_shared_sensor_degrd", {})
        any_tank_degrd = False
        any_sensor_degrd = False
        trapped_fuel = 0.0
        if isinstance(tank_degrd_map, dict):
            any_tank_degrd = any(bool(tank_degrd_map.get(k, False)) for k in ("F1", "F2L", "F2R", "F3L", "F3R", "F4L", "F4R", "F5L", "F5R", "LW", "RW"))
            trapped_fuel = sum(float(self.fuel_qty.get(k, 0.0)) for k in self.fuel_qty.keys() if bool(tank_degrd_map.get(k, False)))
        if isinstance(sensor_degrd_map, dict):
            any_sensor_degrd = any(bool(sensor_degrd_map.get(k, False)) for k in ("F1", "F2L", "F2R", "F3L", "F3R", "F4L", "F4R", "F5L", "F5R", "LW", "RW"))
        use_fuel = max(0.0, total_fuel - trapped_fuel)
        summary_lines: List[Tuple[str, Tuple[int, int, int]]] = [
            (f"TOT: {total_fuel / 1000.0:.1f}", (255, 255, 0) if any_sensor_degrd else (0, 255, 0)),
            (f"INT: {int_fuel / 1000.0:.1f}", (255, 255, 0) if any_sensor_degrd else (0, 255, 0)),
            (f"EXT: {ext_fuel:.1f}", (0, 255, 0)),
        ]
        if any_tank_degrd:
            summary_lines.append((f"USE: {use_fuel / 1000.0:.1f}", (255, 255, 0)))
        font = get_font(14)
        rendered = [font.render(line, True, color) for line, color in summary_lines]
        max_w = max(s.get_width() for s in rendered)
        line_spacing = 4
        total_h = sum(s.get_height() for s in rendered) + line_spacing * max(0, len(rendered) - 1)
        summary_rect = pygame.Rect(
            f1.right + max(8, int(0.15 * DPI)),
            f1.top + max(4, int(0.17 * DPI)),
            max_w + 10,
            total_h + 8,
        )
        pygame.draw.rect(surface, (255, 255, 0) if any_tank_degrd else (0, 255, 0), summary_rect, 1)
        y_text = summary_rect.top + 4
        for surf in rendered:
            surface.blit(surf, (summary_rect.left + 5, y_text))
            y_text += surf.get_height() + line_spacing

        # Left-side readout block (left of F1, above OSB L2): GW / INLET / FEED
        readout_font = get_font(14)
        gw_val = 29.0 + (total_fuel / 1000.0)
        readout_rows = [("GW:", f"{gw_val:.1f}"), ("INLET:", "0"), ("FEED:", "0")]
        left_col_w = max(readout_font.size("INLET:")[0], readout_font.size("FEED:")[0])
        right_col_w = max(readout_font.size("999.9")[0], readout_font.size("0")[0])
        readout_w = left_col_w + 8 + right_col_w
        row_h = readout_font.get_height() + 2
        readout_h = row_h * len(readout_rows)
        readout_x = f1.left - readout_w - max(8, int(0.12 * DPI)) - 14
        readout_y = rect.y + GRID_CELL_H - 6
        readout_rect = pygame.Rect(readout_x, readout_y, readout_w, readout_h)
        label_shift_x = max(16, int(0.2 * DPI)) + 10
        for i, (label, value) in enumerate(readout_rows):
            y = readout_rect.y + i * row_h
            row_color = (0, 255, 255) if i == 0 else (0, 255, 0)
            lab = readout_font.render(label, True, row_color)
            val = readout_font.render(value, True, row_color)
            surface.blit(lab, (readout_rect.left + label_shift_x, y))
            surface.blit(val, (readout_rect.right - val.get_width(), y))

        cg = self._compute_cg()
        cg_rect = pygame.Rect(content.left, cg_y, content.width, max(16, int(0.24 * DPI)))
        draw_centered_text(surface, cg_rect, f"CG: {cg:.1f}", "00FF00", 16)

    def _primary_display_rect(self, rect: pygame.Rect) -> pygame.Rect:
        # In 10x5 pair mode, keep FUEL at native 5x5 scale and center it.
        if rect.width >= int(10 * DPI) - 1 and rect.height < int(7 * DPI) - 1:
            target_w = int(5 * DPI)
            x = rect.x + max(0, (rect.width - target_w) // 2)
            return pygame.Rect(x, rect.y, min(target_w, rect.width), rect.height)
        return rect

    def get_osb_rect(self, rect: pygame.Rect) -> pygame.Rect:
        # Keep FUEL side OSBs available down into the subportal row in 5x5/10x5.
        if rect.height < int(7 * DPI) - 1:
            return pygame.Rect(rect.x, rect.y, rect.width, int(7 * DPI))
        return rect

    def _fuel_osb_box(self, rect: pygame.Rect, label: str) -> pygame.Rect:
        txt = str(label).upper().strip()
        top_count = 5 if rect.width < int(10 * DPI) else 10
        side_count = 6 if rect.height >= int(7 * DPI) - 1 else 5
        top_h = DISPLAY_OSB_H
        side_h = DISPLAY_OSB_H
        one_in_h = int(1.0 * DPI)
        if txt.startswith("T"):
            try:
                idx = int(txt[1:])
            except Exception:
                idx = 1
            idx = max(1, min(top_count, idx))
            return pygame.Rect(rect.x + (idx - 1) * GRID_CELL_W, rect.y, GRID_CELL_W, top_h)
        if txt.startswith("L") or txt.startswith("R"):
            try:
                idx = int(txt[1:])
            except Exception:
                idx = 1
            idx = max(1, min(side_count, idx))
            x = rect.x if txt.startswith("L") else rect.right - GRID_CELL_W
            h = one_in_h if txt in {"L2", "L6", "R6"} else side_h
            if txt in {"L6", "R6"}:
                y = rect.y + int(5.0 * DPI)
            elif txt in {"L5", "R5"}:
                y = rect.y + int(5.0 * DPI) - side_h
            else:
                y = rect.y + top_h - SIDE_OSB_Y_SHIFT + (idx - 1) * side_h
            return pygame.Rect(x, y, GRID_CELL_W, h)
        return pygame.Rect(rect.x, rect.y, GRID_CELL_W, top_h)

    def adjust_osb_zones(self, zones: List[object], rect: pygame.Rect, visible_rect: Optional[pygame.Rect] = None) -> List[object]:
        show_bottom_side_osbs = visible_rect is None or visible_rect.height >= int(7 * DPI) - 1
        if not show_bottom_side_osbs:
            zones = [zone for zone in zones if str(getattr(zone, "label", "")).upper() not in {"L6", "R6"}]
        for zone in zones:
            label = str(getattr(zone, "label", "")).upper()
            if label in {"L2", "L5", "L6", "R5", "R6"}:
                try:
                    zone.rect = self._fuel_osb_box(rect, label)
                except Exception:
                    pass
        return zones

    def _data_entry_grid_rect(self, rect: pygame.Rect) -> pygame.Rect:
        # Keep popup keypad on a fixed 5x8 grid centered horizontally for wide portals.
        grid_w = 5 * GRID_CELL_W
        grid_h = 8 * GRID_CELL_H
        grid_x = _anchored_5col_grid_x(rect, grid_w)
        return pygame.Rect(grid_x, rect.y - SIDE_OSB_Y_SHIFT, grid_w, grid_h)

    @staticmethod
    def _data_entry_row_start(rect: pygame.Rect) -> int:
        # 5x7 / 10x7 uses rows 3..6; 5x5 / 10x5 uses rows 2..5.
        return 3

    def render(self, surface, rect, is_primary: bool, context: FormatContext) -> None:
        prev_clip = surface.get_clip()
        osb_rect = self.get_osb_rect(rect)
        surface.set_clip(rect)
        color = parse_hex_color("00FFFF")
        primary_rect = self._primary_display_rect(rect)
        pygame.draw.rect(surface, color, rect, 1)
        if is_primary:
            self._draw_primary_tanks(surface, primary_rect)
            # Keep OSB labels/buttons at full portal geometry in 10x5/10x7.
            surface.set_clip(osb_rect)
            self._draw_osb_labels(surface, osb_rect, context)
            # Keep keypad popup centered to the full portal.
            surface.set_clip(rect)
            self._draw_data_entry_popup(surface, rect)
            surface.set_clip(osb_rect)
            self._draw_hazard_confirm_popup(surface, rect)
        else:
            sub_rect = rect.inflate(-6, -6)
            surface.set_clip(sub_rect)

            total_fuel = sum(float(v) for v in self.fuel_qty.values()) / 1000.0
            int_fuel = total_fuel
            ext_fuel = 0.0
            gw_fuel = 29.0 + total_fuel

            font = get_font(20)
            rows = [
                ("GW:", f"{gw_fuel:.1f}", (0, 255, 255)),
                ("TOT:", f"{total_fuel:.1f}", (0, 255, 0)),
                ("INT:", f"{int_fuel:.1f}", (0, 255, 0)),
                ("EXT:", f"{ext_fuel:.1f}", (0, 255, 0)),
            ]
            label_w = max(font.size(r[0])[0] for r in rows)
            value_w = max(font.size(r[1])[0] for r in rows)
            gap = 10
            block_w = label_w + gap + value_w
            left_x = sub_rect.centerx - block_w // 2
            value_x = left_x + label_w + gap
            row_h = font.get_height() + 2
            y0 = sub_rect.centery - (row_h * len(rows)) // 2 - 8
            for idx, (label, value, color_rgb) in enumerate(rows):
                y = y0 + idx * row_h
                lab = font.render(label, True, color_rgb)
                val = font.render(value, True, color_rgb)
                surface.blit(lab, (left_x, y))
                surface.blit(val, (value_x, y))

            bottom_font = get_font(18)
            bottom = bottom_font.render("FUEL", True, (0, 255, 255))
            bottom_rect = bottom.get_rect(centerx=sub_rect.centerx)
            bottom_rect.bottom = sub_rect.bottom - 2
            surface.blit(bottom, bottom_rect)
        surface.set_clip(prev_clip)

    def _data_selected(self) -> Optional[str]:
        sel = FuelFormat._shared_data_selected_by_scope.get(FuelFormat._scope_key())
        if sel in {"L3", "R2", "R3"}:
            return sel
        return None

    def _set_data_selected(self, label: Optional[str]) -> None:
        scope = FuelFormat._scope_key()
        if label in {"L3", "R2", "R3"}:
            FuelFormat._shared_data_selected_by_scope[scope] = label
        else:
            FuelFormat._shared_data_selected_by_scope[scope] = None

    def _commit_data_entry(self, label: str) -> None:
        data_inputs = self._data_inputs_for_scope()
        raw = "".join(ch for ch in str(data_inputs.get(label, "")) if (ch.isdigit() or ch == "."))
        if raw != "":
            try:
                self._data_values[label] = float(raw)
            except Exception:
                pass
        data_inputs[label] = ""

    def _apply_data_key(self, selected: str, key: str) -> None:
        data_inputs = self._data_inputs_for_scope()
        current = str(data_inputs.get(selected, ""))
        if key == "BACK":
            data_inputs[selected] = current[:-1]
            return
        if key == ".":
            if "." not in current:
                if current == "":
                    data_inputs[selected] = "0."
                else:
                    data_inputs[selected] = current + "."
            return
        if key not in {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}:
            return
        # max 4 digits + optional decimal point
        next_val = current + key
        digits_only = "".join(ch for ch in next_val if ch.isdigit())
        if len(digits_only) > 4:
            # overflow removes oldest numeric digit while preserving decimal placement
            digits_only = digits_only[-4:]
            if "." in next_val:
                left, _, right = next_val.partition(".")
                left_digits = "".join(ch for ch in left if ch.isdigit())
                right_digits = "".join(ch for ch in right if ch.isdigit())
                take_left = min(len(left_digits), len(digits_only))
                left_part = digits_only[:take_left]
                right_part = digits_only[take_left:]
                next_val = left_part + "." + right_part if right_part != "" else left_part
            else:
                next_val = digits_only
        data_inputs[selected] = next_val[:6]

    def _draw_data_entry_popup(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        if self._data_selected() is None:
            return
        grid_rect = self._data_entry_grid_rect(rect)
        row_start = self._data_entry_row_start(rect)
        row_end = row_start + 3
        # Keep keypad geometry tied to the fixed OSB grid so 5x5 and 5x7
        # layouts render the same keypad size/positions.
        cell_w = GRID_CELL_W
        cell_h = GRID_CELL_H

        def cell_rect(name: str) -> pygame.Rect:
            col = ord(name[0].upper()) - ord("A")
            row = int(name[1:]) - 1
            return pygame.Rect(grid_rect.x + col * cell_w, grid_rect.y + row * cell_h, cell_w, cell_h)

        popup_rect = cell_rect(f"B{row_start}").union(cell_rect(f"D{row_end}"))
        surface.fill((0, 0, 0), popup_rect)
        pygame.draw.rect(surface, (0, 255, 255), popup_rect, 1)

        for c in (1, 2):
            x = grid_rect.x + (1 + c) * cell_w
            pygame.draw.line(surface, (0, 255, 255), (x, popup_rect.top), (x, popup_rect.bottom), 1)
        for r in (1, 2, 3):
            y = grid_rect.y + ((row_start - 1) + r) * cell_h
            pygame.draw.line(surface, (0, 255, 255), (popup_rect.left, y), (popup_rect.right, y), 1)

        keypad = {
            f"B{row_start}": "1", f"C{row_start}": "2", f"D{row_start}": "3",
            f"B{row_start + 1}": "4", f"C{row_start + 1}": "5", f"D{row_start + 1}": "6",
            f"B{row_start + 2}": "7", f"C{row_start + 2}": "8", f"D{row_start + 2}": "9",
            f"B{row_start + 3}": ".",
            f"C{row_start + 3}": "0", f"D{row_start + 3}": "BACK",
        }
        now_ms = int(pygame.time.get_ticks())
        for cell_name, text in keypad.items():
            box = cell_rect(cell_name)
            render_button(
                surface,
                box,
                ButtonState(
                    button_id=f"FUEL_KEYPAD_{cell_name}",
                    button_type=ButtonType.MOMENTARY_SINGLE,
                    text=text,
                    flash_until_ms=1 if self._local_flash_active(f"KEYPAD_{cell_name}", now_ms) else 0,
                ),
                get_font,
                now_ms,
            )

    def on_click(self, pos: Tuple[int, int], rect: pygame.Rect, context: FormatContext) -> bool:
        self._set_popup_anchor_portal_index(getattr(context, "portal_index", None))
        pending = self._hazard_confirm_pending()
        if pending is not None:
            popup = self._hazard_confirm_popup_rect(rect)
            if popup.collidepoint(pos):
                self._hazard_cover_closed[pending] = False
                self._hazard_on[pending] = False
            self._set_hazard_confirm_pending(None)
            return True
        if self._data_selected() is None:
            return False
        grid_rect = self._data_entry_grid_rect(rect)
        row_start = self._data_entry_row_start(rect)
        row_end = row_start + 3
        cols = 5
        rows = 8
        # Match keypad hitboxes to the same fixed geometry as rendering.
        cell_w = max(1, GRID_CELL_W)
        cell_h = max(1, GRID_CELL_H)
        rel_x = pos[0] - grid_rect.x
        rel_y = pos[1] - grid_rect.y
        if rel_x < 0 or rel_y < 0 or rel_x >= grid_rect.width or rel_y >= grid_rect.height:
            return False
        col = max(0, min(cols - 1, rel_x // cell_w))
        row = max(0, min(rows - 1, rel_y // cell_h))
        cell = f"{chr(ord('A') + int(col))}{int(row) + 1}"
        if col < 1 or col > 3 or row < (row_start - 1) or row > (row_end - 1):
            return False
        keypad = {
            f"B{row_start}": "1", f"C{row_start}": "2", f"D{row_start}": "3",
            f"B{row_start + 1}": "4", f"C{row_start + 1}": "5", f"D{row_start + 1}": "6",
            f"B{row_start + 2}": "7", f"C{row_start + 2}": "8", f"D{row_start + 2}": "9",
            f"B{row_start + 3}": ".",
            f"C{row_start + 3}": "0", f"D{row_start + 3}": "BACK",
        }
        key = keypad.get(cell)
        if key is None:
            return True
        self._trigger_local_flash(f"KEYPAD_{cell}")
        selected = self._data_selected()
        if selected is None:
            return True
        self._apply_data_key(selected, key)
        return True

    def on_key(self, key: str) -> bool:
        selected = self._data_selected()
        if selected is None:
            return False
        raw = str(key).strip()
        if raw == "":
            return False
        normalized: Optional[str] = None
        upper = raw.upper()
        if upper in {"ENTER", "RETURN", "KP_ENTER"}:
            self._commit_data_entry(selected)
            self._set_data_selected(None)
            return True
        if upper in {"KP_BACK", "BACKSPACE", "BACK"}:
            normalized = "BACK"
        elif upper in {"KP_DECIMAL", "DECIMAL", "DOT", "."}:
            normalized = "."
        elif upper.startswith("KP_") and len(upper) == 4 and upper[3].isdigit():
            normalized = upper[3]
        elif len(raw) == 1 and raw.isdigit():
            normalized = raw
        elif raw == ".":
            normalized = "."
        if normalized is None:
            return False
        self._apply_data_key(selected, normalized)
        return True

    def _draw_osb_labels(self, surface, rect: pygame.Rect, context: FormatContext, only_labels: Optional[Set[str]] = None) -> None:
        color = parse_hex_color("00FFFF")
        top_labels = {1: "", 2: "REFUEL", 3: "", 4: "PRE\\nCONTACT"}
        right_labels = {
            1: "",
            2: f"JOKER\\n{float(self._data_values.get('R2', 0.0)):.1f}",
            3: f"BINGO\\n{float(self._data_values.get('R3', 0.0)):.1f}",
            5: "FUEL\\nXFER\\nRIGHT",
            6: "EMER\\nREFUEL",
        }
        left_labels = {
            1: "LRP>",
            2: "DUMP",
            3: f"DUMP CO\\n{float(self._data_values.get('L3', 0.0)):.1f}",
            5: "FUEL\\nXFER\\nLEFT",
            6: "MF SOV",
        }

        def draw_label(
            box: pygame.Rect,
            text: str,
            side: str,
            flash: bool,
            *,
            single_on: bool = False,
            intermediate_on: bool = False,
            base_color: Optional[Tuple[int, int, int]] = None,
        ) -> None:
            normalized = text.replace("\\n", "\n")
            if side == "right":
                h_align = "right"
            elif side == "left":
                h_align = "left"
            else:
                h_align = "center"
            v_align = "top" if side in ("top", "bottom") else "center"
            lines = normalized.split("\n")
            font = get_font(14)
            text_color = base_color if base_color is not None else color
            rendered = [font.render(line, True, (255, 255, 255) if single_on else text_color) for line in lines]
            total_h = sum(s.get_height() for s in rendered) + max(0, len(rendered) - 1)
            if v_align == "top":
                y = box.top + OSB_PADDING
            else:
                y = box.centery - total_h // 2
            rects: List[pygame.Rect] = []
            for surf in rendered:
                if h_align == "left":
                    r = surf.get_rect()
                    r.left = box.left + OSB_PADDING
                elif h_align == "right":
                    r = surf.get_rect()
                    r.right = box.right - OSB_PADDING
                else:
                    r = surf.get_rect(centerx=box.centerx)
                r.y = y
                rects.append(r)
                y += surf.get_height() + 1
            if flash and rects:
                flash_rect = rects[0].copy()
                for r in rects[1:]:
                    flash_rect.union_ip(r)
                flash_rect.inflate_ip(4, 2)
                pygame.draw.rect(surface, (255, 255, 255), flash_rect)
                rendered = [font.render(line, True, (0, 0, 0)) for line in lines]
            elif intermediate_on and rects:
                inter_rect = rects[0].copy()
                for r in rects[1:]:
                    inter_rect.union_ip(r)
                inter_rect.inflate_ip(4, 2)
                pygame.draw.rect(surface, (0, 255, 255), inter_rect)
                rendered = [font.render(line, True, (0, 0, 0)) for line in lines]
            elif single_on and rects:
                on_rect = rects[0].copy()
                for r in rects[1:]:
                    on_rect.union_ip(r)
                on_rect.inflate_ip(4, 2)
                pygame.draw.rect(surface, (255, 255, 255), on_rect, 1)
            for surf, r in zip(rendered, rects):
                surface.blit(surf, r)

        def draw_label_lines_2_3(box: pygame.Rect, text: str, side: str, flash: bool) -> None:
            normalized = text.replace("\\n", "\n")
            parts = normalized.split("\n")
            l2 = parts[0] if len(parts) > 0 else ""
            l3 = parts[1] if len(parts) > 1 else ""
            font = get_font(14)
            slot_h = box.height / 3.0

            def _line_rect(s: str, line_no: int) -> pygame.Rect:
                surf = font.render(s, True, color)
                rr = surf.get_rect()
                if side == "left":
                    rr.left = box.left + OSB_PADDING
                elif side == "right":
                    rr.right = box.right - OSB_PADDING
                else:
                    rr.centerx = box.centerx
                rr.y = int(box.top + (line_no - 1) * slot_h + (slot_h - surf.get_height()) / 2)
                return rr

            surf2 = font.render(l2, True, (0, 0, 0) if flash else color)
            surf3 = font.render(l3, True, (0, 0, 0) if flash else color)
            r2 = _line_rect(l2, 2)
            r3 = _line_rect(l3, 3)
            if flash:
                fr = r2.union(r3).inflate(4, 2)
                pygame.draw.rect(surface, (255, 255, 255), fr)
            surface.blit(surf2, r2)
            if l3 != "":
                surface.blit(surf3, r3)

        top_count = 5 if rect.width < int(10 * DPI) else 10
        side_count = 6 if rect.height >= int(7 * DPI) - 1 else 5
        show_bottom_side_osbs = rect.height >= int(7 * DPI) - 1
        top_offset = DISPLAY_OSB_H if top_count > 0 else 0
        airborne = self._is_airborne()
        if not airborne:
            # L2 DUMP is unavailable while on the ground.
            self._hazard_on["L2"] = False
            self._hazard_cover_closed["L2"] = True
            if self._hazard_confirm_pending() == "L2":
                self._set_hazard_confirm_pending(None)

        for idx, text in top_labels.items():
            if idx > top_count:
                continue
            osb_label = f"T{idx}"
            if only_labels is not None and osb_label not in only_labels:
                continue
            box = self._fuel_osb_box(rect, osb_label)
            if osb_label in {"L6", "R6"}:
                surface.fill((0, 0, 0), box)
            flashing = context.is_osb_flashing(osb_label)
            draw_label(box, text, "top", flashing, single_on=(osb_label == "T2" and bool(FuelFormat._shared_refuel_t2_on)))

        for idx, text in left_labels.items():
            if idx > side_count:
                continue
            osb_label = f"L{idx}"
            if osb_label == "L6" and not show_bottom_side_osbs:
                continue
            if only_labels is not None and osb_label not in only_labels:
                continue
            box = self._fuel_osb_box(rect, osb_label)
            if osb_label in {"L6", "R6"}:
                surface.fill((0, 0, 0), box)
            flashing = context.is_osb_flashing(osb_label)
            if osb_label == "L3":
                draw_label_lines_2_3(box, text, "left", flashing)
            else:
                is_l2_ground_disabled = (osb_label == "L2" and not airborne)
                draw_label(
                    box,
                    text,
                    "left",
                    flashing,
                    single_on=(False if is_l2_ground_disabled else bool(self._hazard_on.get(osb_label, False))),
                    intermediate_on=(
                        False
                        if is_l2_ground_disabled
                        else (not bool(self._hazard_cover_closed.get(osb_label, True)) and not bool(self._hazard_on.get(osb_label, False)))
                    ),
                    base_color=((128, 128, 128) if is_l2_ground_disabled else None),
                )
            if osb_label in {"L3"} and self._data_selected() == osb_label:
                font = get_font(14)
                raw = str(self._data_inputs_for_scope().get(osb_label, ""))
                scratch = raw[-5:].rjust(5, "_")
                top_text = f"{scratch}\u2190"
                surf = font.render(top_text, True, (255, 255, 255))
                r = surf.get_rect()
                r.left = box.left + OSB_PADDING
                r.y = box.top + OSB_PADDING
                pygame.draw.rect(surface, (255, 255, 255), r.inflate(4, 2), 1)
                surface.blit(surf, r)
            if idx in (2, 6):
                # Ground-disabled L2 has no hazard border/cover.
                if osb_label == "L2" and not airborne:
                    pass
                elif bool(self._hazard_cover_closed.get(osb_label, True)):
                    draw_hazard_stripe_border(
                        surface,
                        box.inflate(-2, -2),
                        border_thickness=HAZARD_BORDER_THICKNESS,
                        stripe_line_width=HAZARD_STRIPE_LINE_WIDTH,
                        stripe_spacing=HAZARD_STRIPE_SPACING,
                    )

        for idx, text in right_labels.items():
            if idx > side_count:
                continue
            osb_label = f"R{idx}"
            if osb_label == "R6" and not show_bottom_side_osbs:
                continue
            if only_labels is not None and osb_label not in only_labels:
                continue
            box = self._fuel_osb_box(rect, osb_label)
            flashing = context.is_osb_flashing(osb_label)
            if osb_label in {"R2", "R3"}:
                draw_label_lines_2_3(box, text, "right", flashing)
            else:
                draw_label(
                    box,
                    text,
                    "right",
                    flashing,
                    single_on=bool(self._hazard_on.get(osb_label, False)),
                    intermediate_on=(not bool(self._hazard_cover_closed.get(osb_label, True)) and not bool(self._hazard_on.get(osb_label, False))),
                )
            if osb_label in {"R2", "R3"} and self._data_selected() == osb_label:
                font = get_font(14)
                raw = str(self._data_inputs_for_scope().get(osb_label, ""))
                scratch = raw[-5:].rjust(5, "_")
                top_text = f"{scratch}\u2190"
                surf = font.render(top_text, True, (255, 255, 255))
                r = surf.get_rect()
                r.right = box.right - OSB_PADDING
                r.y = box.top + OSB_PADDING
                pygame.draw.rect(surface, (255, 255, 255), r.inflate(4, 2), 1)
                surface.blit(surf, r)
            if idx in (6,):
                if bool(self._hazard_cover_closed.get(osb_label, True)):
                    draw_hazard_stripe_border(
                        surface,
                        box.inflate(-2, -2),
                        border_thickness=HAZARD_BORDER_THICKNESS,
                        stripe_line_width=HAZARD_STRIPE_LINE_WIDTH,
                        stripe_spacing=HAZARD_STRIPE_SPACING,
                    )

    def on_osb(self, label: str, context: FormatContext) -> bool:
        self._set_popup_anchor_portal_index(getattr(context, "portal_index", None))
        if self._hazard_confirm_pending() is not None:
            self._set_hazard_confirm_pending(None)
            return True
        if label == "T1":
            context.request_vded(context.portal_index, "MENU")
            return True
        if label == "L1":
            return True
        if label == "L2" and not self._is_airborne():
            # DUMP is intentionally disabled on the ground.
            self._hazard_on["L2"] = False
            self._hazard_cover_closed["L2"] = True
            return True
        if label in {"L3", "R2", "R3"}:
            selected = self._data_selected()
            if selected == label:
                self._commit_data_entry(label)
                self._set_data_selected(None)
            else:
                if selected is not None:
                    self._commit_data_entry(selected)
                self._data_inputs_for_scope()[label] = ""
                self._set_data_selected(label)
            return True
        if label in {"L2", "L6", "R6"}:
            cover_closed = bool(self._hazard_cover_closed.get(label, True))
            is_on = bool(self._hazard_on.get(label, False))
            if cover_closed and not is_on:
                self._set_hazard_confirm_pending(label)
                return True
            if not cover_closed and not is_on:
                self._hazard_on[label] = True
                return True
            if label in {"L2", "R6"} and is_on:
                self._hazard_on[label] = False
                self._hazard_cover_closed[label] = True
            return True
        if label == "T2":
            FuelFormat._shared_refuel_t2_on = not bool(FuelFormat._shared_refuel_t2_on)
            return True
        if label in {"R1"}:
            print(f"FUEL OSB {label} pressed")
            return True
        return False
