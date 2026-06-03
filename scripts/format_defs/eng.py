from formats import *  # noqa: F401,F403


class EngineFormat(FormatBase):
    name: str = "ENG"
    _shared_gauge_values: Dict[str, float] = {
        "THRUST": 0.0,
        "EGT": 40.0,
        "NOZZLE": 106.0,
        "N1 RPM": 0.0,
        "N2 RPM": 0.0,
        "OIL": 0.0,
    }
    _shared_mid_values: Dict[str, int] = {"FF": 0, "HYDA": 5, "HYDB": 7}
    _shared_colors: Dict[str, Tuple[int, int, int]] = {
        "THRUST": (0, 255, 0),
        "EGT": (0, 255, 0),
        "NOZZLE": (0, 255, 0),
        "N1 RPM": (0, 255, 0),
        "N2 RPM": (0, 255, 0),
        "OIL": (0, 255, 0),
        "FF": (0, 255, 0),
        "HYDA": (0, 255, 0),
        "HYDB": (0, 255, 0),
    }
    _shared_status_engine_hazard: bool = False
    _shared_comm_fail_active: bool = False

    def __init__(self) -> None:
        self.gauge_values = EngineFormat._shared_gauge_values
        self.gauge_ranges: Dict[str, Tuple[float, float]] = {
            "THRUST": (0.0, 150.0),
            "EGT": (0.0, 2000.0),
            "NOZZLE": (0.0, 106.0),
            "N1 RPM": (0.0, 105.0),
            "N2 RPM": (0.0, 105.0),
            "OIL": (0.0, 105.0),
        }
        self.redline_starts: Dict[str, float] = {
            "THRUST": 100.0,
            "EGT": 850.0,
            "N1 RPM": 100.0,
            "N2 RPM": 100.0,
            "OIL": 100.0,
        }
        self.mid_values = EngineFormat._shared_mid_values
        self.colors = EngineFormat._shared_colors

    def _draw_gauge(
        self,
        surface: pygame.Surface,
        center: Tuple[int, int],
        radius: int,
        value: float,
        value_min: float,
        value_max: float,
        label: str,
        draw_red_segment: bool,
        value_text: str,
        gauge_color: Tuple[int, int, int] = (0, 255, 0),
        redline_start: Optional[float] = None,
    ) -> None:
        red = (255, 0, 0)
        span = max(0.001, value_max - value_min)
        percent = max(0.0, min(1.0, (value - value_min) / span))

        def pt(angle_deg: float) -> Tuple[int, int]:
            rad = math.radians(angle_deg)
            return (
                center[0] + int(radius * math.cos(rad)),
                center[1] - int(radius * math.sin(rad)),
            )

        def arc_points_clockwise(start_deg: float, end_deg: float, steps: int) -> List[Tuple[int, int]]:
            # Build points on the exact gauge radius for smooth curved segments.
            s = start_deg
            e = end_deg
            if e > s:
                e -= 360.0
            out: List[Tuple[int, int]] = []
            for i in range(steps + 1):
                t = i / steps
                a = s + (e - s) * t
                out.append(pt(a))
            return out

        start_deg = 90.0
        total_sweep = 270.0
        green_sweep = 270.0
        red_sweep = 0.0
        if draw_red_segment:
            total_sweep = 300.0
            # Redline always starts at left side (270 deg sweep point).
            green_sweep = 270.0
            red_sweep = 30.0
        green_end_deg = start_deg - green_sweep
        red_end_deg = start_deg - total_sweep

        # Red caution segment on the left side of the arc.
        if draw_red_segment and red_sweep > 0.0:
            red_points = arc_points_clockwise(green_end_deg, red_end_deg, 60)
            if len(red_points) >= 2:
                pygame.draw.lines(surface, red, False, red_points, 2)

        # Draw green arc on top of red for cleaner overlap.
        arc_points = arc_points_clockwise(start_deg, green_end_deg, 180 if green_sweep >= 270.0 else 120)
        if len(arc_points) >= 2:
            pygame.draw.lines(surface, gauge_color, False, arc_points, 2)

        # Outward radial tick marks at start/end of green arc, extending 3 px.
        def draw_outward_tick(angle_deg: float) -> None:
            p = pt(angle_deg)
            rad = math.radians(angle_deg)
            ux = math.cos(rad)
            uy = -math.sin(rad)
            p2 = (int(round(p[0] + ux * 3)), int(round(p[1] + uy * 3)))
            pygame.draw.line(surface, gauge_color, p, p2, 2)

        draw_outward_tick(start_deg)
        draw_outward_tick(green_end_deg)

        # Needle mapping:
        # - Non-redline gauges: span full sweep.
        # - Redline gauges: map min->redline over green (270deg), then
        #   redline->max only over red segment (30deg).
        if (
            draw_red_segment
            and redline_start is not None
            and value_max > value_min
            and value_min < redline_start < value_max
        ):
            if value <= redline_start:
                green_span = max(0.001, redline_start - value_min)
                green_pct = max(0.0, min(1.0, (value - value_min) / green_span))
                needle_deg = start_deg - (green_sweep * green_pct)
            else:
                red_span = max(0.001, value_max - redline_start)
                red_pct = max(0.0, min(1.0, (value - redline_start) / red_span))
                needle_deg = green_end_deg - (red_sweep * red_pct)
        else:
            needle_deg = start_deg - total_sweep * percent
        tip_radius = max(4, radius - 6)
        nrad = math.radians(needle_deg)
        tip = (
            center[0] + int(tip_radius * math.cos(nrad)),
            center[1] - int(tip_radius * math.sin(nrad)),
        )
        pygame.draw.line(surface, gauge_color, center, tip, 2)
        # Arrowhead marker at end of pointer.
        ah = 6
        aw = 4
        back = (
            tip[0] - int(ah * math.cos(nrad)),
            tip[1] + int(ah * math.sin(nrad)),
        )
        perp = (math.sin(nrad), math.cos(nrad))
        left = (back[0] - int(aw * perp[0]), back[1] - int(aw * perp[1]))
        right = (back[0] + int(aw * perp[0]), back[1] + int(aw * perp[1]))
        pygame.draw.polygon(surface, gauge_color, [tip, left, right], 0)

        label_font = get_font(18)
        label_surf = label_font.render(label, True, gauge_color)
        label_rect = label_surf.get_rect(center=(center[0], center[1] + radius + 14))
        surface.blit(label_surf, label_rect)

        # Current value at top-left of each gauge.
        value_font = get_font(18)
        value_surf = value_font.render(value_text, True, gauge_color)
        value_rect = value_surf.get_rect()
        value_rect.right = center[0] - 6
        value_rect.bottom = center[1] - radius + 16
        surface.blit(value_surf, value_rect)

    def _draw_osb_labels(self, surface: pygame.Surface, rect: pygame.Rect, context: FormatContext) -> None:
        top_items = {2: "A-ICE\nOFF", 4: "ADS HT\nOFF"}
        for idx, text in top_items.items():
            box = pygame.Rect(rect.x + (idx - 1) * GRID_CELL_W, rect.y, GRID_CELL_W, DISPLAY_OSB_H)
            state = ButtonState(
                button_id=f"ENG_T{idx}",
                button_type=ButtonType.MOMENTARY_SINGLE,
                text=text,
                flash_until_ms=1 if context.is_osb_flashing(f"T{idx}") else 0,
                h_align="center",
                v_align="top",
                padding=OSB_PADDING,
                font_size=14,
            )
            render_button(surface, box, state, get_font, 0)

            # Cyan underline under first line ("A-ICE" / "ADS HT").
            first_line = text.split("\n", 1)[0]
            fnt = get_font(14)
            surf = fnt.render(first_line, True, (0, 255, 255))
            tx = box.centerx - surf.get_width() // 2
            ty = box.top + OSB_PADDING
            y_line = ty + surf.get_height() + 1
            pygame.draw.line(surface, (0, 255, 255), (tx, y_line), (tx + surf.get_width(), y_line), 1)

    def render(self, surface, rect, is_primary: bool, context: FormatContext) -> None:
        hyd_a_qts = float(SVC_DEBUG_STATE.get("hyd_a_qts", float(self.mid_values.get("HYDA", ENGINE_MID_VALUES.get("HYDA", 5)))))
        hyd_b_qts = float(SVC_DEBUG_STATE.get("hyd_b_qts", float(self.mid_values.get("HYDB", ENGINE_MID_VALUES.get("HYDB", 7)))))
        comm_fail_active = bool(EngineFormat._shared_comm_fail_active)
        try:
            active_names = {str(t).strip().upper() for t, _ in get_current_icaws_alerts()}
        except Exception:
            active_names = set()
        if "HYD FAIL A" in active_names:
            hyd_a_qts = 0.0
        if "HYD FAIL B" in active_names:
            hyd_b_qts = 0.0
        ENGINE_MID_VALUES["HYDA"] = int(round(hyd_a_qts))
        ENGINE_MID_VALUES["HYDB"] = int(round(hyd_b_qts))
        if not is_primary:
            draw_centered_text(surface, rect, "ENG (SUB)", "00FFFF", 14)
            return

        # Layout area avoids OSBs around portal edges.
        content = pygame.Rect(
            rect.left + GRID_CELL_W + 4,
            rect.top + GRID_CELL_H + 2,
            rect.width - 2 * (GRID_CELL_W + 4),
            rect.height - GRID_CELL_H - 20,
        )
        cols = 3
        rows = 2
        cell_w = content.width // cols
        cell_h = content.height // rows
        radius = max(28, min(cell_w, cell_h) // 2.2)
        # In 10x7 expanded mode, keep gauge sizing comparable to 5x5/5x7.
        if rect.width >= int(10 * DPI) - 1:
            radius = max(24, int(radius * 0.45))

        gauge_order = ["THRUST", "EGT", "NOZZLE", "N1 RPM", "N2 RPM", "OIL"]
        red_segment_labels = {"THRUST", "EGT", "N1 RPM", "N2 RPM", "OIL"}
        col_centers = [
            content.left + 0 * cell_w + cell_w // 2 - 40,
            content.left + 1 * cell_w + cell_w // 2,
            content.left + 2 * cell_w + cell_w // 2 + 40,
        ]
        row_centers = [
            content.top + 0 * cell_h + cell_h // 2 - 16,
            content.top + 1 * cell_h + cell_h // 2 - 4,
        ]
        # In 5x7 only, shift gauge cluster up by 30 px.
        is_5x7 = rect.width < int(10 * DPI) - 1 and rect.height >= int(7 * DPI) - 1
        if is_5x7:
            row_centers = [row_centers[0] - 35, row_centers[1] - 35]
        for i, label in enumerate(gauge_order):
            c = i % cols
            r = i // cols
            cx = col_centers[c]
            cy = row_centers[r]
            value_now = 0.0 if comm_fail_active else float(self.gauge_values.get(label, 0.0))
            rng = self.gauge_ranges.get(label, (0.0, 100.0))
            value_text = f"{int(round(value_now)):>4}"
            gauge_color = self.colors.get(label, (0, 255, 0))
            redline_start = self.redline_starts.get(label) if label in red_segment_labels else None
            self._draw_gauge(
                surface,
                (cx, cy),
                radius,
                value_now,
                float(rng[0]),
                float(rng[1]),
                label,
                label in red_segment_labels,
                value_text,
                gauge_color,
                redline_start,
            )

        # FF / HYDA / HYDB between rows, horizontally aligned to gauge columns.
        mid_y = (row_centers[0] + row_centers[1]) // 2
        mid_labels = [
            ("FF", "0" if comm_fail_active else f"{int(self.mid_values.get('FF', 3))}"),
            ("HYDA", f"{hyd_a_qts:.1f}"),
            ("HYDB", f"{hyd_b_qts:.1f}"),
        ]
        label_font = get_font(20)
        value_font = get_font(20)
        for c, (name, value_text) in enumerate(mid_labels):
            col_center_x = col_centers[c]
            mid_color = self.colors.get(name, (0, 255, 0))
            name_surf = label_font.render(name, True, mid_color)

            # Numeric box sized to value text (HYD values include decimal).
            box_w = max(value_font.size("000")[0] + 8, value_font.size(value_text)[0] + 8)
            box_h = value_font.get_height() + 4
            if name == "FF":
                # Keep the FF label + value group centered on the left gauge center,
                # regardless of value digit count.
                group_gap = 8
                group_w = name_surf.get_width() + group_gap + box_w
                group_left = col_center_x - group_w // 2
                name_rect = name_surf.get_rect(midleft=(group_left, mid_y))
                box = pygame.Rect(name_rect.right + group_gap, mid_y - box_h // 2, box_w, box_h)
            else:
                name_rect = name_surf.get_rect(midright=(col_center_x - 6, mid_y))
                box = pygame.Rect(col_center_x + 2, mid_y - box_h // 2, box_w, box_h)
            surface.blit(name_surf, name_rect)
            pygame.draw.rect(surface, mid_color, box, 1)
            val_surf = value_font.render(value_text, True, mid_color)
            val_rect = val_surf.get_rect(right=box.right - 3, centery=box.centery)
            surface.blit(val_surf, val_rect)

        self._draw_osb_labels(surface, rect, context)

    def on_osb(self, label: str, context: FormatContext) -> bool:
        if label == "T1":
            context.request_vded(context.portal_index, "MENU")
            return True
        if label in {"T2", "T4"}:
            return True
        return False


def set_engine_cold_start(cold: bool) -> None:
    if cold:
        EngineFormat._shared_gauge_values.update(
            {
                "THRUST": 0.0,
                "EGT": 40.0,
                "NOZZLE": 106.0,
                "N1 RPM": 0.0,
                "N2 RPM": 0.0,
                "OIL": 0.0,
            }
        )
        EngineFormat._shared_mid_values["FF"] = 0
    else:
        # Hot start baseline uses nominal RUN values near 80% throttle.
        EngineFormat._shared_gauge_values.update(
            {
                "THRUST": 82.0,
                "EGT": 715.0,
                "NOZZLE": 45.0,
                "N1 RPM": 88.0,
                "N2 RPM": 93.0,
                "OIL": 78.0,
            }
        )
        EngineFormat._shared_mid_values["FF"] = 14800
    EngineFormat._shared_colors.update(
        {
            "THRUST": (0, 255, 0),
            "EGT": (0, 255, 0),
            "NOZZLE": (0, 255, 0),
            "N1 RPM": (0, 255, 0),
            "N2 RPM": (0, 255, 0),
            "OIL": (0, 255, 0),
            "FF": (0, 255, 0),
            "HYDA": (0, 255, 0),
            "HYDB": (0, 255, 0),
        }
    )
    EngineFormat._shared_status_engine_hazard = False
