from formats import *  # noqa: F401,F403


class HudFormat(EfiFormat):
    name: str = "HUD"
    _HUD_SPACING_SCALE_BASE: float = 3.0
    _HUD_HEADING_WINDOW_IN: float = 2.0

    def _draw_heading_indicator(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        heading_deg: float,
        *,
        y_offset_px: float = 0.0,
    ) -> None:
        green = (0, 255, 0)
        black = (0, 0, 0)
        window_w = max(1, int(round(self._HUD_HEADING_WINDOW_IN * DPI)))
        window_h = max(1, int(round(1.05 * DPI)))
        window = pygame.Rect(0, 0, window_w, window_h)
        window.centerx = rect.centerx
        base_top_offset = int(round(0.75 * DPI))
        is_5x7 = rect.height >= int(7 * DPI) - 1
        if not is_5x7:
            base_top_offset -= int(round(0.75 * DPI))
        window.top = rect.top + max(0, int(base_top_offset + float(y_offset_px)))

        clip_prev = surface.get_clip()
        surface.set_clip(clip_prev.clip(window))

        heading_text = f"{int(round(float(heading_deg))) % 360:03d}"
        center_font = get_font(14)
        center_surf = center_font.render(heading_text, True, green)
        text_row_y = int(window.top + max(1, int(round(0.06 * DPI))) + 10)
        marker_text_y = text_row_y
        line_len_px = 15
        center_text_rect = center_surf.get_rect(centerx=window.centerx, y=text_row_y)
        center_box = center_text_rect.inflate(10, 6)

        px_per_deg = max(0.1, (float(window.width) / 80.0) * 2.5)
        half_span_deg = int(math.ceil((float(window.width) * 0.5) / px_per_deg)) + 10
        start_mark = int(math.floor((float(heading_deg) - float(half_span_deg)) / 5.0) * 5)
        end_mark = int(math.ceil((float(heading_deg) + float(half_span_deg)) / 5.0) * 5)
        major_font = center_font
        tick_base_y = center_box.bottom
        major_tick_h = max(8, int(round(0.10 * DPI)))
        minor_tick_h = max(4, int(round(0.06 * DPI)))

        for mark in range(start_mark, end_mark + 1, 5):
            delta = ((float(mark) - float(heading_deg) + 180.0) % 360.0) - 180.0
            x = int(round(float(window.centerx) + (delta * px_per_deg)))
            if x < window.left - 2 or x > window.right + 2:
                continue
            is_major = (mark % 10) == 0
            if is_major:
                tick_y0 = tick_base_y
                tick_y1 = tick_base_y + major_tick_h
            else:
                # Keep minor tick bottoms aligned with major tick bottoms.
                tick_y0 = tick_base_y + max(0, major_tick_h - minor_tick_h)
                tick_y1 = tick_base_y + major_tick_h
            pygame.draw.line(surface, green, (x, tick_y0), (x, tick_y1), 1)
            if is_major:
                h_norm = int(mark) % 360
                label = f"{h_norm:03d}"[1:]
                lbl_surf = major_font.render(label, True, green)
                lbl_rect = lbl_surf.get_rect(centerx=x, y=marker_text_y)
                surface.blit(lbl_surf, lbl_rect)

        # Draw current heading box/text last so it masks marker labels behind it.
        inner_box = center_box.inflate(-2, -2)
        if inner_box.width > 0 and inner_box.height > 0:
            pygame.draw.rect(surface, black, inner_box, 0)
        pygame.draw.rect(surface, green, center_box, 1)
        surface.blit(center_surf, center_text_rect)

        line_start = (center_box.centerx, center_box.bottom)
        line_end = (center_box.centerx, center_box.bottom + line_len_px)
        pygame.draw.line(surface, green, line_start, line_end, 1)

        surface.set_clip(clip_prev)

    def _draw_side_speed_altitude(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        green = (0, 255, 0)
        speed_kts = max(0.0, self._read_aircraft_scalar(("TOTAL_SPEED_KTS", "AIRSPEED_KTS"), 0.0))
        altitude_ft = max(0.0, self._read_aircraft_scalar(("ALTITUDE_FT", "ALTITUDE_TARGET_FT"), 0.0))

        font = get_font(16)
        speed_surf = font.render(str(int(round(speed_kts))), True, green)
        alt_surf = font.render(str(int(round(altitude_ft))), True, green)

        side_margin = max(2, int(round(0.8 * DPI)))
        cy = int(rect.centery)
        speed_rect = speed_surf.get_rect(midleft=(int(rect.left + side_margin), cy))
        alt_rect = alt_surf.get_rect(midright=(int(rect.right - side_margin), cy))

        surface.blit(speed_surf, speed_rect)
        surface.blit(alt_surf, alt_rect)

        dot_radius_px = 40.0
        for center in (speed_rect.center, alt_rect.center):
            for angle_deg in range(0, 360, 36):
                dot_x, dot_y = self._polar_from_north(center, dot_radius_px, float(angle_deg))
                pygame.draw.circle(surface, green, (int(dot_x), int(dot_y)), 2, 0)

    def _draw_bottom_left_status(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        green = (0, 255, 0)
        airspeed_kts = max(0.0, self._read_aircraft_scalar(("AIRSPEED_KTS",), 0.0))
        total_speed_kts = max(airspeed_kts, self._read_aircraft_scalar(("TOTAL_SPEED_KTS",), airspeed_kts))
        altitude_ft = max(0.0, self._read_aircraft_scalar(("ALTITUDE_FT", "ALTITUDE_TARGET_FT"), 0.0))

        alt_m = max(0.0, float(altitude_ft)) * 0.3048
        if alt_m <= 11000.0:
            temp_k = 288.15 - (0.0065 * alt_m)
        else:
            temp_k = 216.65
        a_mps = math.sqrt(1.4 * 287.05 * max(1.0, temp_k))
        sound_kts = max(1e-6, a_mps * 1.9438444924406)
        mach = max(0.0, float(total_speed_kts) / sound_kts)

        lines = [f"M {mach:.2f}", "G43", "#-4.5", "ASTO"]
        font = get_font(14)
        rendered = [font.render(txt, True, green) for txt in lines]
        total_h = sum(s.get_height() for s in rendered) + max(0, len(rendered) - 1)
        anchor_x = int(round(rect.left + (0.8 * DPI)))
        anchor_y = int(round(rect.bottom - (1.5 * DPI)))
        y = anchor_y - total_h
        for surf in rendered:
            rr = surf.get_rect()
            rr.right = anchor_x
            rr.y = y
            surface.blit(surf, rr)
            y += surf.get_height() + 1

    def _draw_hud_core(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        *,
        draw_border: bool = True,
        draw_side_speed_altitude: bool = True,
        draw_bottom_left_status: bool = True,
        heading_y_offset_px: float = 0.0,
        roll_indicator_offset_override_px: Optional[float] = None,
        ladder_spacing_scale: Optional[float] = None,
    ) -> None:
        green = (0, 255, 0)
        # Drive HUD symbology from current aircraft attitude.
        pitch_deg = self._normalize_signed_angle_deg(self._read_global_attitude_deg())
        heading_deg = float(self._read_heading_deg()) % 360.0
        roll_deg = self._normalize_signed_angle_deg(self._read_global_bank_deg())

        adi_rect = rect.inflate(-2, -2)
        spacing_scale = float(self._HUD_SPACING_SCALE_BASE if ladder_spacing_scale is None else ladder_spacing_scale)
        self._draw_adi(
            surface,
            adi_rect,
            sym_color=green,
            draw_background=False,
            draw_nose_symbol=False,
            draw_horizon_gap_arrow=False,
            line_width=2,
            nose_y_override=float(adi_rect.centery),
            ladder_spacing_scale=spacing_scale,
            pitch_deg_override=pitch_deg,
            bank_deg_override=roll_deg,
            ladder_numbers_left_only=True,
            w_vertical_offset_px=(0.5 * DPI),
            ladder_width_scale=0.7,
        )
        is_5x7 = rect.height >= int(7 * DPI) - 1
        roll_indicator_offset_px = (0.25 * DPI) if is_5x7 else 0.0
        if roll_indicator_offset_override_px is not None:
            roll_indicator_offset_px = float(roll_indicator_offset_override_px)
        self._draw_bottom_roll_indicator(
            surface,
            adi_rect,
            -roll_deg,
            sym_color=green,
            vertical_offset_px=roll_indicator_offset_px,
        )
        if bool(draw_side_speed_altitude):
            self._draw_side_speed_altitude(surface, rect)
        if bool(draw_bottom_left_status):
            self._draw_bottom_left_status(surface, rect)
        self._draw_heading_indicator(surface, rect, heading_deg, y_offset_px=float(heading_y_offset_px))

        if bool(draw_border):
            pygame.draw.rect(surface, (0, 255, 255), rect, 1)

    def render(self, surface, rect, is_primary: bool, context: FormatContext) -> None:
        _ = context
        prev_clip = surface.get_clip()
        surface.set_clip(rect)
        surface.fill((0, 0, 0), rect)
        if not is_primary:
            # Render full-size HUD symbology first, then scale to subportal.
            base_w = max(1, int(round(5.0 * DPI)))
            base_h = max(1, int(round(7.0 * DPI)))
            virtual = pygame.Surface((base_w, base_h), pygame.SRCALPHA)
            virtual.fill((0, 0, 0, 255))
            self._draw_hud_core(
                virtual,
                virtual.get_rect(),
                draw_border=False,
                draw_side_speed_altitude=False,
                draw_bottom_left_status=False,
                heading_y_offset_px=(1.10 * DPI),
                roll_indicator_offset_override_px=(-1.35 * DPI),
                ladder_spacing_scale=2.2,
            )
            target_w = max(1, rect.width)
            scale = float(target_w) / float(base_w)
            target_h = max(1, int(round(float(base_h) * scale)))
            scaled = pygame.transform.smoothscale(virtual, (target_w, target_h))
            dst = scaled.get_rect()
            dst.centery = rect.centery
            dst.centerx = rect.centerx
            surface.blit(scaled, dst.topleft)
            # Keep cyan border thickness constant regardless of content scaling.
            pygame.draw.rect(surface, (0, 255, 255), rect, 1)
            surface.set_clip(prev_clip)
            return

        # Main portal HUD: keep the original direct-render behavior.
        green = (0, 255, 0)
        pitch_deg = self._normalize_signed_angle_deg(self._read_global_attitude_deg())
        heading_deg = float(self._read_heading_deg()) % 360.0
        roll_deg = self._normalize_signed_angle_deg(self._read_global_bank_deg())
        adi_rect = rect.inflate(-2, -2)
        self._draw_adi(
            surface,
            adi_rect,
            sym_color=green,
            draw_background=False,
            draw_nose_symbol=False,
            draw_horizon_gap_arrow=False,
            line_width=2,
            nose_y_override=float(adi_rect.centery),
            ladder_spacing_scale=self._HUD_SPACING_SCALE_BASE,
            pitch_deg_override=pitch_deg,
            bank_deg_override=roll_deg,
            ladder_numbers_left_only=True,
            w_vertical_offset_px=(0.5 * DPI),
            ladder_width_scale=0.7,
        )
        is_5x7 = rect.height >= int(7 * DPI) - 1
        roll_indicator_offset_px = (0.25 * DPI) if is_5x7 else 0.0
        self._draw_bottom_roll_indicator(
            surface,
            adi_rect,
            -roll_deg,
            sym_color=green,
            vertical_offset_px=roll_indicator_offset_px,
        )
        self._draw_side_speed_altitude(surface, rect)
        self._draw_bottom_left_status(surface, rect)
        self._draw_heading_indicator(surface, rect, heading_deg)
        pygame.draw.rect(surface, (0, 255, 255), rect, 1)
        surface.set_clip(prev_clip)

    def on_osb(self, label: str, context: FormatContext) -> bool:
        if str(label).upper() == "T1":
            context.request_vded(context.portal_index, "MENU")
            return True
        return False

    def osb_is_interactive(self, label: str) -> bool:
        return str(label).upper() == "T1"
