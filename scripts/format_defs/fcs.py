from formats import *  # noqa: F401,F403


class FcsFormat(FormatBase):
    name: str = "FCS"
    _cached_aircraft_gray: Optional[pygame.Surface] = None
    _aircraft_missing: bool = False
    _scaled_aircraft_cache: Dict[int, pygame.Surface] = {}
    _CTRL_KEYS: Tuple[str, ...] = (
        "l_lef",
        "r_lef",
        "l_aileron",
        "r_aileron",
        "l_rudder",
        "r_rudder",
        "l_elevator",
        "r_elevator",
    )

    _OSB_MAP: Dict[str, Tuple[str, str]] = {
        "T2": ("nose_door", "NOSE\nDOOR"),
        "L3": ("ap", "A/P"),
        "L4": ("alt_pa", "ALT\nPA"),
        "L5": ("integ_fcs_fadec", "INTEG\nFCS\nFADEC"),
        "R4": ("gear_reset", "GEAR\nRESET"),
        "R5": ("trim_reset", "TRIM\nRESET"),
    }

    @staticmethod
    def _tint_to_gray(src: pygame.Surface) -> pygame.Surface:
        # Gray tint with preserved alpha.
        out = src.copy()
        tint = pygame.Surface(out.get_size(), pygame.SRCALPHA)
        tint.fill((165, 165, 165, 255))
        out.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return out

    @classmethod
    def _get_aircraft_image(cls) -> Optional[pygame.Surface]:
        if cls._cached_aircraft_gray is not None:
            return cls._cached_aircraft_gray
        if cls._aircraft_missing:
            return None
        path = resource_path("icons", "FCS", "FCS AIRCRAFT.png")
        try:
            raw = pygame.image.load(str(path)).convert_alpha()
            cls._cached_aircraft_gray = cls._tint_to_gray(raw)
            return cls._cached_aircraft_gray
        except Exception:
            cls._aircraft_missing = True
            return None

    @classmethod
    def _get_scaled_aircraft(cls, target_width: int) -> Optional[pygame.Surface]:
        img = cls._get_aircraft_image()
        if img is None:
            return None
        tw = max(1, int(target_width))
        cached = cls._scaled_aircraft_cache.get(tw)
        if cached is not None:
            return cached
        iw, ih = img.get_size()
        if iw <= 0 or ih <= 0:
            return None
        th = max(1, int(round(tw * (ih / float(iw)))))
        scaled = pygame.transform.smoothscale(img, (tw, th))
        cls._scaled_aircraft_cache[tw] = scaled
        return scaled

    @staticmethod
    def _clamp(v: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, float(v)))

    @staticmethod
    def _safe_float(v: object, default: float = 0.0) -> float:
        try:
            return float(v)
        except Exception:
            return float(default)

    @classmethod
    def _read_control_override(cls, aircraft: Dict[str, object], key: str) -> Optional[float]:
        aliases: Dict[str, Tuple[str, ...]] = {
            "l_lef": ("l_lef", "L_LEF", "lef_l", "LEF_L"),
            "r_lef": ("r_lef", "R_LEF", "lef_r", "LEF_R"),
            "l_aileron": ("l_aileron", "L_AILERON", "aileron_l", "AILERON_L"),
            "r_aileron": ("r_aileron", "R_AILERON", "aileron_r", "AILERON_R"),
            "l_rudder": ("l_rudder", "L_RUDDER", "rudder_l", "RUDDER_L"),
            "r_rudder": ("r_rudder", "R_RUDDER", "rudder_r", "RUDDER_R"),
            "l_elevator": ("l_elevator", "L_ELEVATOR", "elevator_l", "ELEVATOR_L"),
            "r_elevator": ("r_elevator", "R_ELEVATOR", "elevator_r", "ELEVATOR_R"),
        }
        for alias in aliases.get(key, (key,)):
            if alias in aircraft:
                return cls._safe_float(aircraft.get(alias, 0.0), 0.0)
        return None

    @classmethod
    def _update_control_positions(cls) -> None:
        FCS_STATE["_ctrl_last_ms"] = float(int(pygame.time.get_ticks()))
        panel = PANEL_BUTTON_STATES if isinstance(PANEL_BUTTON_STATES, dict) else {}
        aircraft = panel.get("AIRCRAFT", {})
        if not isinstance(aircraft, dict):
            aircraft = {}
        for key in cls._CTRL_KEYS:
            override = cls._read_control_override(aircraft, key)
            if override is not None:
                FCS_STATE[key] = cls._clamp(float(override), -45.0, 45.0)

    def _osb_box(self, rect: pygame.Rect, label: str) -> Optional[pygame.Rect]:
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

    def render(self, surface, rect, is_primary: bool, context: FormatContext) -> None:
        if not is_primary:
            draw_centered_text(surface, rect, "FCS", "00FFFF", 14)
            return

        prev_clip = surface.get_clip()
        surface.set_clip(rect)
        # Keep image scale consistent across 5x5 / 5x7 / 10x7 using the 5x7 width baseline.
        target_w = max(1, int(round((5 * DPI) * 0.8)))
        aircraft = self._get_scaled_aircraft(target_w)
        if aircraft is not None:
            # Anchor to a virtual 5x7 center so 5x5 keeps the same placement.
            ref_center_y = rect.top + int(round(3.5 * DPI)) - 10
            image_rect = aircraft.get_rect(center=(rect.centerx + 20, ref_center_y - 70))
            surface.blit(aircraft, image_rect)

            def draw_horizontal_hashes(y: int, x0: int, x1: int, color: Tuple[int, int, int], count: int = 10, half_len: int = 1) -> None:
                if count <= 1:
                    xs = [int(round((x0 + x1) / 2.0))]
                else:
                    xs = [int(round(x0 + (x1 - x0) * (i / float(count - 1)))) for i in range(count)]
                for x in xs:
                    pygame.draw.line(surface, color, (x, y - half_len), (x, y + half_len), 1)

            def draw_vertical_hashes(x: int, y0: int, y1: int, color: Tuple[int, int, int], count: int = 10, half_len: int = 1) -> None:
                if count <= 1:
                    ys = [int(round((y0 + y1) / 2.0))]
                else:
                    ys = [int(round(y0 + (y1 - y0) * (i / float(count - 1)))) for i in range(count)]
                for y in ys:
                    pygame.draw.line(surface, color, (x - half_len, y), (x + half_len, y), 1)

            def draw_plus(cx: int, cy: int, size: int, color: Tuple[int, int, int]) -> None:
                half = max(1, size // 2)
                pygame.draw.line(surface, color, (cx - half, cy), (cx + half, cy), 1)
                pygame.draw.line(surface, color, (cx, cy - half), (cx, cy + half), 1)

            def draw_inc(cx: int, cy: int, size: int, color: Tuple[int, int, int]) -> None:
                half = max(2, size // 2)
                points = [(cx, cy - half), (cx - half, cy + half), (cx + half, cy + half)]
                pygame.draw.polygon(surface, color, points, 0)

            gray = (128, 128, 128)

            # 1x1 inch gray reference box centered horizontally and positioned below image.
            box_size = int(1 * DPI)
            ref_box = pygame.Rect(0, 0, box_size, box_size)
            ref_box.centerx = rect.centerx
            desired_top = image_rect.bottom + int(round(0.12 * DPI))
            min_top = rect.top + GRID_CELL_H + 4
            # Anchor vertical clamp to a virtual 5x7 portal so 5x5 does not
            # shift the lower trim/stick square upward with subportal collapse.
            virtual_5x7_bottom = rect.top + int(round(7 * DPI))
            max_top = virtual_5x7_bottom - box_size - int(round(0.45 * DPI))
            if max_top < min_top:
                max_top = min_top
            ref_box.top = max(min_top, min(desired_top, max_top))
            v_x = ref_box.centerx
            h_y = ref_box.centery
            left_x = ref_box.left
            right_x = ref_box.right - 1  # shift both horizontal lines left by 1 px from right edge
            underline_y = ref_box.bottom + 11  # keep lower horizontal line fixed after box shift

            # Smaller half-sized gray box (under black cross).
            inner_size = max(2, box_size // 2)
            inner_box = pygame.Rect(0, 0, inner_size, inner_size)
            inner_box.center = ref_box.center
            pygame.draw.rect(surface, gray, inner_box, 1)
            # Smaller half-size gray cross.
            small_half = max(1, box_size // 4)
            pygame.draw.line(surface, gray, (v_x - small_half, h_y), (v_x + small_half, h_y), 1)
            pygame.draw.line(surface, gray, (v_x, h_y - small_half), (v_x, h_y + small_half), 1)

            # Large black cross (under gray/cyan/green overlays).
            pygame.draw.line(surface, (0, 0, 0), (v_x, ref_box.top), (v_x, ref_box.bottom - 1), 9)
            pygame.draw.line(surface, (0, 0, 0), (left_x, h_y), (right_x, h_y), 9)

            # Large gray box and gray linework (over black cross).
            pygame.draw.rect(surface, gray, ref_box, 1)
            pygame.draw.line(surface, gray, (v_x, ref_box.top), (v_x, ref_box.bottom - 1), 1)  # stop 1 px above box bottom
            pygame.draw.line(surface, gray, (left_x, h_y), (right_x, h_y), 1)
            pygame.draw.line(surface, gray, (left_x, underline_y), (right_x, underline_y), 1)
            # Small caps at both ends of the lower horizontal line.
            cap_half = 3
            pygame.draw.line(surface, gray, (left_x, underline_y - cap_half), (left_x, underline_y + cap_half), 1)
            pygame.draw.line(surface, gray, (right_x, underline_y - cap_half), (right_x, underline_y + cap_half), 1)
            # 10 evenly spaced, slightly smaller hash marks.
            draw_horizontal_hashes(h_y, left_x, right_x, gray, count=10, half_len=1)
            draw_horizontal_hashes(underline_y, left_x, right_x, gray, count=10, half_len=1)
            draw_vertical_hashes(v_x, ref_box.top, ref_box.bottom - 1, gray, count=10, half_len=1)
            top_cyan_x_in = self._clamp(self._safe_float(FCS_STATE.get("top_cyan_x_in", 0.0), 0.0), -0.5, 0.5)
            top_cyan_y_in = self._clamp(self._safe_float(FCS_STATE.get("top_cyan_y_in", 0.0), 0.0), -0.5, 0.5)
            bottom_cyan_x_in = self._clamp(self._safe_float(FCS_STATE.get("bottom_cyan_x_in", 0.0), 0.0), -0.5, 0.5)
            rudder_trim_in = self._clamp(self._safe_float(FCS_STATE.get("rudder_trim_in", 0.0), 0.0), -0.5, 0.5)
            top_dx = int(round(top_cyan_x_in * DPI))
            top_dy = int(round(top_cyan_y_in * DPI))
            lower_dx = int(round(bottom_cyan_x_in * DPI))
            trim_dx = int(round(rudder_trim_in * DPI))
            # Cyan squares show trim reference (top currently fixed, bottom uses rudder trim).
            cyan = (0, 255, 255)
            sq = 14
            # Expand +1 px to the right and down.
            cross_sq = pygame.Rect(v_x - sq // 2, h_y - sq // 2, sq + 1, sq + 1)
            lower_sq = pygame.Rect(v_x + trim_dx - sq // 2, underline_y - sq // 2, sq + 1, sq + 1)
            pygame.draw.rect(surface, cyan, cross_sq, 1)
            pygame.draw.rect(surface, cyan, lower_sq, 1)
            # Green stick/rudder indicators: top is stick position; lower is INC symbol for rudder command.
            green = (0, 255, 0)
            draw_plus(v_x + top_dx, h_y + top_dy, sq + 1, green)
            draw_inc(v_x + lower_dx, underline_y + (sq // 2) + 8, max(8, sq - 4), green)

            label_font = get_font(14)
            label_surf = label_font.render("TRIM 00.0\u00B0", True, (0, 255, 0))
            label_rect = label_surf.get_rect(centerx=ref_box.centerx)
            label_rect.bottom = ref_box.top - 2
            surface.blit(label_surf, label_rect)

            # Keep the lower FCS blocks anchored to their original location.
            legacy_ref_box = pygame.Rect(0, 0, box_size, box_size)
            legacy_ref_box.right = image_rect.right
            legacy_ref_box.centery = image_rect.centery
            legacy_ref_box.y -= 10
            legacy_anchor_top = int(legacy_ref_box.top - 2 - label_surf.get_height())

            # Green reference rectangle centered on image X; top aligned to legacy anchor.
            ref_w = max(1, int(round((1.0 / 4.0) * DPI)))
            ref_h = max(1, int(round((1.0 / 3.0) * DPI)))
            man_ref = pygame.Rect(0, 0, ref_w, ref_h)
            man_ref.centerx = image_rect.centerx - 19
            man_ref.top = legacy_anchor_top
            gear_rect_state = _get_fcs_gear_rect_render_state()
            top_visible = bool(gear_rect_state.get("top_visible", True))
            bottom_visible = bool(gear_rect_state.get("bottom_visible", True))
            top_color = tuple(gear_rect_state.get("top_color", (0, 255, 0)))
            bottom_color = tuple(gear_rect_state.get("bottom_color", (0, 255, 0)))
            top_hazard = bool(gear_rect_state.get("top_hazard", False))
            bottom_hazard = bool(gear_rect_state.get("bottom_hazard", False))
            if top_visible:
                if top_hazard:
                    draw_hazard_stripe_fill_box(surface, man_ref)
                else:
                    pygame.draw.rect(surface, top_color, man_ref, 0)

            # Two additional filled rectangles 1.35in below, 45px to either side.
            lower_y = man_ref.top + int(round(1.35 * DPI))
            left_ref = pygame.Rect(0, 0, ref_w, ref_h)
            right_ref = pygame.Rect(0, 0, ref_w, ref_h)
            left_ref.centerx = man_ref.centerx - 45
            right_ref.centerx = man_ref.centerx + 45
            left_ref.top = lower_y
            right_ref.top = lower_y
            if bottom_visible:
                if bottom_hazard:
                    draw_hazard_stripe_fill_box(surface, left_ref)
                    draw_hazard_stripe_fill_box(surface, right_ref)
                else:
                    pygame.draw.rect(surface, bottom_color, left_ref, 0)
                    pygame.draw.rect(surface, bottom_color, right_ref, 0)

            # GWT / G-LIM pair and current weight, aligned to lower-left box edge.
            try:
                shared_qty = getattr(FuelFormat, "_shared_fuel_qty", None)
                if isinstance(shared_qty, dict) and len(shared_qty) > 0:
                    total_fuel_lbs = float(sum(max(0.0, float(v)) for v in shared_qty.values()))
                else:
                    total_fuel_lbs = float(getattr(FuelFormat, "_shared_total_lbs", 0.0))
            except Exception:
                total_fuel_lbs = 0.0
            gw_val = 29.0 + (max(0.0, total_fuel_lbs) / 1000.0)
            left_lines = ["GWT", "G-LIM"]
            right_lines = [f"{gw_val:.1f}", "9"]
            gwt_font = get_font(14)
            gwt_line_gap = 3
            left_surfs = [gwt_font.render(t, True, (0, 255, 0)) for t in left_lines]
            right_surfs = [gwt_font.render(t, True, (0, 255, 0)) for t in right_lines]
            left_h = sum(s.get_height() for s in left_surfs) + max(0, len(left_surfs) - 1) * gwt_line_gap
            right_h = sum(s.get_height() for s in right_surfs) + max(0, len(right_surfs) - 1) * gwt_line_gap
            block_h = max(left_h, right_h)
            center_y = man_ref.bottom
            top_y = int(round(center_y - (block_h / 2.0)))
            right_edge_x = left_ref.left
            right_max_w = max((s.get_width() for s in right_surfs), default=0)
            left_max_w = max((s.get_width() for s in left_surfs), default=0)
            pair_gap = 10
            left_x = right_edge_x - right_max_w - pair_gap - left_max_w

            y = top_y
            for surf in left_surfs:
                lr = surf.get_rect()
                lr.x = left_x
                lr.y = y
                surface.blit(surf, lr)
                y += surf.get_height() + gwt_line_gap

            y = top_y
            for surf in right_surfs:
                rr = surf.get_rect()
                rr.right = right_edge_x
                rr.y = y
                surface.blit(surf, rr)
                y += surf.get_height() + gwt_line_gap

            # CG text centered to the top rectangle, with text bottom touching
            # the top edge of the lower rectangles.
            cg_font = get_font(14)
            cg_line_gap = 3
            cg_lines = ["CG 16", "10 C"]
            cg_surfs = [cg_font.render(t, True, (0, 255, 0)) for t in cg_lines]
            cg_total_h = sum(s.get_height() for s in cg_surfs) + max(0, len(cg_surfs) - 1) * cg_line_gap
            cg_y = lower_y - cg_total_h
            cg16_rect: Optional[pygame.Rect] = None
            for idx, surf in enumerate(cg_surfs):
                cg_rect = surf.get_rect(centerx=man_ref.centerx)
                cg_rect.y = cg_y
                surface.blit(surf, cg_rect)
                if idx == 0:
                    cg16_rect = cg_rect.copy()
                cg_y += surf.get_height() + cg_line_gap

            if cg16_rect is not None:
                self._update_control_positions()
                num_font = get_font(16)

                def draw_arrow_glyph(glyph: str, cx: int, cy: int, color: Tuple[int, int, int]) -> None:
                    arrow_surf = num_font.render(glyph, True, color)
                    arrow_rect = arrow_surf.get_rect(center=(cx, cy))
                    surface.blit(arrow_surf, arrow_rect)

                def fmt_abs(v: float) -> str:
                    return str(int(round(abs(float(v)))))

                def sign_arrow_ud(v: float) -> str:
                    return "\u2191" if float(v) >= 0.0 else "\u2193"

                def sign_arrow_lr(v: float) -> str:
                    return "\u2192" if float(v) >= 0.0 else "\u2190"

                def show_arrow(v: float) -> bool:
                    # Hide arrow when floor(abs(position)) is 0.
                    return int(abs(float(v))) > 0

                l_lef = self._safe_float(FCS_STATE.get("l_lef", 0.0), 0.0)
                r_lef = self._safe_float(FCS_STATE.get("r_lef", 0.0), 0.0)
                l_ail = self._safe_float(FCS_STATE.get("l_aileron", 0.0), 0.0)
                r_ail = self._safe_float(FCS_STATE.get("r_aileron", 0.0), 0.0)
                l_rud = self._safe_float(FCS_STATE.get("l_rudder", 0.0), 0.0)
                r_rud = self._safe_float(FCS_STATE.get("r_rudder", 0.0), 0.0)
                l_elev = self._safe_float(FCS_STATE.get("l_elevator", 0.0), 0.0)
                r_elev = self._safe_float(FCS_STATE.get("r_elevator", 0.0), 0.0)

                # 0=LEF, 1=AILERON, 2=RUDDER, 3=ELEVATOR
                zero_left = num_font.render(fmt_abs(l_lef), True, green)
                zero_right = num_font.render(fmt_abs(r_lef), True, green)
                one_left = num_font.render(fmt_abs(l_ail), True, green)
                one_right = num_font.render(fmt_abs(r_ail), True, green)
                two_left = num_font.render(fmt_abs(l_rud), True, green)
                two_right = num_font.render(fmt_abs(r_rud), True, green)
                three_left = num_font.render(fmt_abs(l_elev), True, green)
                three_right = num_font.render(fmt_abs(r_elev), True, green)

                marker_w = max(1, num_font.render("00", True, green).get_width())
                z_left_cx = int(round(cg16_rect.left - 20 - (marker_w / 2.0) - 22))
                z_right_cx = int(round(cg16_rect.right + 20 + (marker_w / 2.0) + 22))
                z_cy = int(round(cg16_rect.centery + 5))

                # Preserve current tuned geometry.
                one_left_cx_current = z_left_cx - 15
                one_right_cx_current = z_right_cx + 15
                one_cy_current = z_cy + 70 + 15
                two_left_cx_current = one_left_cx_current + 40
                two_right_cx_current = one_right_cx_current - 40
                two_cy_current = z_cy + 90
                three_left_cx_current = two_left_cx_current - 35
                three_right_cx_current = two_right_cx_current + 35
                three_cy_current = z_cy + 160

                one_left_cx = one_left_cx_current + 5
                one_right_cx = one_right_cx_current - 5
                one_cy = one_cy_current - 5
                two_left_cx = two_left_cx_current + 9
                two_right_cx = two_right_cx_current - 9
                two_cy = two_cy_current + 10
                three_left_cx = three_left_cx_current + 10
                three_right_cx = three_right_cx_current - 10
                three_cy = three_cy_current - 5

                z_left_rect = zero_left.get_rect(center=(z_left_cx, z_cy))
                z_right_rect = zero_right.get_rect(center=(z_right_cx, z_cy))
                one_left_rect = one_left.get_rect(center=(one_left_cx, one_cy))
                one_right_rect = one_right.get_rect(center=(one_right_cx, one_cy))
                two_left_rect = two_left.get_rect(center=(two_left_cx, two_cy))
                two_right_rect = two_right.get_rect(center=(two_right_cx, two_cy))
                three_left_rect = three_left.get_rect(center=(three_left_cx, three_cy))
                three_right_rect = three_right.get_rect(center=(three_right_cx, three_cy))

                surface.blit(zero_left, z_left_rect)
                surface.blit(zero_right, z_right_rect)
                surface.blit(one_left, one_left_rect)
                surface.blit(one_right, one_right_rect)
                surface.blit(two_left, two_left_rect)
                surface.blit(two_right, two_right_rect)
                surface.blit(three_left, three_left_rect)
                surface.blit(three_right, three_right_rect)

                arrow_gap = 10
                # Arrows indicate sign (up/down) for each independent surface value.
                if show_arrow(l_ail):
                    draw_arrow_glyph(sign_arrow_ud(l_ail), one_left_rect.left - arrow_gap, one_left_rect.centery, green)
                if show_arrow(r_ail):
                    draw_arrow_glyph(sign_arrow_ud(r_ail), one_right_rect.right + arrow_gap, one_right_rect.centery, green)
                if show_arrow(l_lef):
                    draw_arrow_glyph(sign_arrow_ud(l_lef), z_left_rect.left - arrow_gap, z_left_rect.centery, green)
                if show_arrow(r_lef):
                    draw_arrow_glyph(sign_arrow_ud(r_lef), z_right_rect.right + arrow_gap, z_right_rect.centery, green)
                if show_arrow(l_elev):
                    draw_arrow_glyph(sign_arrow_ud(l_elev), three_left_rect.right + arrow_gap, three_left_rect.centery, green)
                if show_arrow(r_elev):
                    draw_arrow_glyph(sign_arrow_ud(r_elev), three_right_rect.left - arrow_gap, three_right_rect.centery, green)
                if show_arrow(l_rud):
                    draw_arrow_glyph(sign_arrow_lr(l_rud), two_left_rect.left - arrow_gap, two_left_rect.bottom + 10, green)
                if show_arrow(r_rud):
                    draw_arrow_glyph(sign_arrow_lr(r_rud), two_right_rect.right + arrow_gap, two_right_rect.bottom + 10, green)
        else:
            draw_centered_text(surface, rect, "FCS", "00FFFF", 18)

        for osb_label, (state_key, text) in self._OSB_MAP.items():
            box = self._osb_box(rect, osb_label)
            if box is None:
                continue
            side = osb_label[0].upper()
            if side == "L":
                h_align = "left"
                v_align = "center"
            elif side == "R":
                h_align = "right"
                v_align = "center"
            else:
                h_align = "center"
                v_align = "top"
            btn = ButtonState(
                button_id=f"FCS_{osb_label}",
                button_type=ButtonType.MOMENTARY_SINGLE,
                text=text,
                flash_until_ms=1 if context.is_osb_flashing(osb_label) else 0,
                is_single_function=False if osb_label in {"R4", "R5"} else True,
                is_on=False if osb_label in {"R4", "R5"} else bool(FCS_STATE.get(state_key, False)),
                h_align=h_align,
                v_align=v_align,
                font_size=14,
                padding=OSB_PADDING,
            )
            render_button(surface, box, btn, get_font, 0)

        t3_box = self._osb_box(rect, "T3")
        if t3_box is not None:
            t3_font = get_font(14)
            t3_y = t3_box.top + OSB_PADDING
            for line in ("EXER", "MODE"):
                t3_surf = t3_font.render(line, True, (0, 255, 255))
                t3_rect = t3_surf.get_rect(centerx=t3_box.centerx)
                t3_rect.y = t3_y
                surface.blit(t3_surf, t3_rect)
                t3_y += t3_surf.get_height() + 1

        surface.set_clip(prev_clip)

    def on_osb(self, label: str, context: FormatContext) -> bool:
        if label == "T1":
            context.request_vded(context.portal_index, "MENU")
            return True
        spec = self._OSB_MAP.get(label)
        if spec is None:
            return False
        state_key, _ = spec
        if label in {"R4", "R5"}:
            FCS_STATE[state_key] = False
            if label == "R5":
                FCS_STATE["top_cyan_x_in"] = 0.0
                FCS_STATE["top_cyan_y_in"] = 0.0
                FCS_STATE["bottom_cyan_x_in"] = 0.0
                FCS_STATE["rudder_trim_in"] = 0.0
            return True
        FCS_STATE[state_key] = not bool(FCS_STATE.get(state_key, False))
        if label == "L3" and bool(FCS_STATE.get(state_key, False)):
            # FCS A/P quick-enable: HDG SEL + ALT HOLD + SPEED HOLD.
            ap_state = AUTOPILOT_STATE if isinstance(AUTOPILOT_STATE, dict) else {}
            ap_state["att_hold"] = False
            ap_state["hdg_sel"] = True
            ap_state["alt_hold"] = True
            ap_state["alt_sel"] = False
            ap_state["speed_hold"] = True
            ap_state["speed_sel"] = False
            panel = PANEL_BUTTON_STATES if isinstance(PANEL_BUTTON_STATES, dict) else {}
            aircraft = panel.get("AIRCRAFT", {}) if isinstance(panel, dict) else {}
            if isinstance(aircraft, dict):
                heading_val: Optional[float] = None
                for key in ("HEADING_DEG", "HDG_DEG", "HEADING", "HDG", "ATT_HEADING_BASE_DEG"):
                    if key in aircraft:
                        try:
                            heading_val = float(aircraft.get(key, 0.0))
                            break
                        except Exception:
                            continue
                if heading_val is not None:
                    ap_state["hdg_value"] = str(int(round(heading_val)) % 360).rjust(3, "0")
                try:
                    ap_state["alt_hold_target_ft"] = max(0.0, float(aircraft.get("ALTITUDE_FT", 0.0)))
                except Exception:
                    pass
                try:
                    ap_state["speed_hold_target_kts"] = max(
                        0.0,
                        float(aircraft.get("TOTAL_SPEED_KTS", aircraft.get("AIRSPEED_KTS", 0.0))),
                    )
                except Exception:
                    pass
            AUTOPILOT_STATE.update(ap_state)
        elif label == "L3":
            # Turning A/P off from FCS clears all autopilot mode buttons.
            ap_state = AUTOPILOT_STATE if isinstance(AUTOPILOT_STATE, dict) else {}
            ap_state["att_hold"] = False
            ap_state["hdg_sel"] = False
            ap_state["alt_hold"] = False
            ap_state["alt_sel"] = False
            ap_state["speed_hold"] = False
            ap_state["speed_sel"] = False
            ap_state["rte_hold"] = False
            ap_state["speed_menu_open"] = False
            ap_state["selected_field"] = None
            AUTOPILOT_STATE.update(ap_state)
        return True
