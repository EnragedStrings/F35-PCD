from formats import *  # noqa: F401,F403


class StatusBarFormat(FormatBase):
    def __init__(self, labels: List[str]) -> None:
        self.name = "STATUS"
        self.labels = labels
        self._last_cw_keys: set = set()

    def render(self, surface, rect, is_primary: bool, context: FormatContext) -> None:
        if context.portal_index != 0:
            return
        color = parse_hex_color("00FFFF")
        font = get_font(28)
        text = "SWAP"
        full_rect = pygame.Rect(rect.x, rect.y, rect.width * 2, rect.height)
        half_span_w = max(1, full_rect.width // 2)

        # Gray edge bands: left 0.5 in and right 0.5 in of the status bar.
        edge_w = int(0.5 * DPI)
        left_edge = pygame.Rect(full_rect.left, full_rect.top, edge_w, full_rect.height)
        right_edge = pygame.Rect(full_rect.right - edge_w, full_rect.top, edge_w, full_rect.height)
        pygame.draw.rect(surface, (128, 128, 128), left_edge)
        pygame.draw.rect(surface, (128, 128, 128), right_edge)
        if bool(getattr(context, "show_status_fps", False)):
            fps_getter = getattr(context, "get_status_fps", None)
            if not callable(fps_getter):
                fps_getter = lambda: 0.0
            fps_val = max(0.0, float(fps_getter()))
            fps_font = get_font(13)
            fps_line1 = fps_font.render(f"{int(round(fps_val))}", True, (0, 255, 255))
            fps_line2 = fps_font.render("FPS", True, (0, 255, 255))
            fps_l1_rect = fps_line1.get_rect()
            fps_l2_rect = fps_line2.get_rect()
            fps_l1_rect.left = left_edge.left + 4
            fps_l1_rect.top = full_rect.top + 1
            fps_l2_rect.left = left_edge.left + 4
            fps_l2_rect.top = fps_l1_rect.bottom - 1
            surface.blit(fps_line1, fps_l1_rect)
            surface.blit(fps_line2, fps_l2_rect)

        # Arc gauge center tracks the ENG/FUEL side.
        gauge_offset = int((0.5 + (1.125 / 2.0)) * DPI)
        gauge_cx = full_rect.left + gauge_offset
        if context.status_swapped:
            gauge_cx += half_span_w
        gauge_cy = full_rect.centery
        gauge_r = max(10, int(0.33 * DPI))

        def pt(angle_deg: float) -> Tuple[int, int]:
            rad = math.radians(angle_deg)
            return (
                gauge_cx + int(gauge_r * math.cos(rad)),
                gauge_cy - int(gauge_r * math.sin(rad)),
            )

        def arc_points_clockwise(start_deg: float, end_deg: float, steps: int) -> List[Tuple[int, int]]:
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

        green = parse_hex_color("00FF00")
        yellow = (255, 255, 0)
        comm_fail_active = bool(getattr(EngineFormat, "_shared_comm_fail_active", False))
        gauge_color = yellow if comm_fail_active else green
        red = gauge_color
        start_deg = 90.0
        green_end_deg = -180.0
        red_end_deg = -210.0

        red_points = arc_points_clockwise(green_end_deg, red_end_deg, 40)
        if len(red_points) >= 2:
            pygame.draw.lines(surface, red, False, red_points, 2)
        green_points = arc_points_clockwise(start_deg, green_end_deg, 120)
        if len(green_points) >= 2:
            pygame.draw.lines(surface, gauge_color, False, green_points, 2)

        # Outward ticks at green arc ends.
        for a in (start_deg, green_end_deg):
            p = pt(a)
            rad = math.radians(a)
            ux = math.cos(rad)
            uy = -math.sin(rad)
            p2 = (int(round(p[0] + ux * 3)), int(round(p[1] + uy * 3)))
            pygame.draw.line(surface, gauge_color, p, p2, 2)

        thrust = 0.0 if comm_fail_active else max(0.0, min(150.0, float(context.get_status_engine_thrust())))
        # Match main THRUST gauge mapping:
        # 0-100 spans the green 270deg arc, 100-150 spans the final 30deg red segment.
        if thrust <= 100.0:
            needle_deg = start_deg - (270.0 * (thrust / 100.0))
        else:
            needle_deg = green_end_deg - (30.0 * ((thrust - 100.0) / 50.0))
        nrad = math.radians(needle_deg)
        tip_radius = max(4, gauge_r - 4)
        tip = (
            gauge_cx + int(tip_radius * math.cos(nrad)),
            gauge_cy - int(tip_radius * math.sin(nrad)),
        )
        pygame.draw.line(surface, gauge_color, (gauge_cx, gauge_cy), tip, 2)
        ah = 5
        aw = 3
        back = (
            tip[0] - int(ah * math.cos(nrad)),
            tip[1] + int(ah * math.sin(nrad)),
        )
        perp = (math.sin(nrad), math.cos(nrad))
        left = (back[0] - int(aw * perp[0]), back[1] - int(aw * perp[1]))
        right = (back[0] + int(aw * perp[0]), back[1] + int(aw * perp[1]))
        pygame.draw.polygon(surface, gauge_color, [tip, left, right], 0)
        thrust_text = get_font(12).render(f"{int(round(thrust))}", True, gauge_color)
        thrust_rect = thrust_text.get_rect()
        thrust_rect.right = gauge_cx - 4
        thrust_rect.bottom = gauge_cy - gauge_r + 12
        surface.blit(thrust_text, thrust_rect)

        # ENG/FUEL/SMS popup buttons, touching a gray edge band without overlap.
        eng_btn_w = int(1.125 * DPI)
        eng_btn_h = int(1.0 * DPI)
        eng_btn_rect = pygame.Rect(left_edge.right, full_rect.top, eng_btn_w, eng_btn_h)
        fuel_btn_rect = pygame.Rect(eng_btn_rect.right, full_rect.top, eng_btn_w, eng_btn_h)
        sms_btn_rect = pygame.Rect(fuel_btn_rect.right, full_rect.top, eng_btn_w, eng_btn_h)
        aircraft_btn_rect = pygame.Rect(sms_btn_rect.right, full_rect.top, eng_btn_w, eng_btn_h)
        icaws_btn_rect = pygame.Rect(aircraft_btn_rect.right, full_rect.top, int(3.375 * DPI), eng_btn_h)
        autopilot_btn_rect = pygame.Rect(icaws_btn_rect.right, full_rect.top, eng_btn_w, eng_btn_h)
        if context.status_swapped:
            for _r in (eng_btn_rect, fuel_btn_rect, sms_btn_rect, aircraft_btn_rect, icaws_btn_rect, autopilot_btn_rect):
                _r.x += half_span_w
        if bool(getattr(EngineFormat, "_shared_status_engine_hazard", False)):
            draw_hazard_stripe_border(
                surface,
                eng_btn_rect,
                border_thickness=5,
                stripe_line_width=3,
                stripe_spacing=8,
            )
        if context.eng_popup_active:
            pygame.draw.rect(surface, (255, 255, 255), eng_btn_rect, 1)
        context.set_eng_popup_button_rect(eng_btn_rect.copy())

        if context.fuel_popup_active:
            pygame.draw.rect(surface, (255, 255, 255), fuel_btn_rect, 1)
        context.set_fuel_popup_button_rect(fuel_btn_rect.copy())
        if context.sms_popup_active:
            pygame.draw.rect(surface, (255, 255, 255), sms_btn_rect, 1)
        context.set_sms_popup_button_rect(sms_btn_rect.copy())

        # Aircraft status icon button (to the right of SMS in normal layout).
        if context.fcs_popup_active:
            pygame.draw.rect(surface, (255, 255, 255), aircraft_btn_rect, 1)
        context.set_fcs_popup_button_rect(aircraft_btn_rect.copy())
        icon_pad = 6
        icon_size = (
            max(2, aircraft_btn_rect.width - icon_pad * 2),
            max(2, aircraft_btn_rect.height - icon_pad * 2),
        )
        aircraft_icon = get_green_aircraft_icon(icon_size)
        if aircraft_icon is not None:
            icon_rect = aircraft_icon.get_rect(center=aircraft_btn_rect.center)
            surface.blit(aircraft_icon, icon_rect)
        # Mirror the three FCS reference rectangles in the status button at 1/2
        # scale, including the same gear-transition staged behavior.
        gear_rect_state = _get_fcs_gear_rect_render_state()
        top_visible = bool(gear_rect_state.get("top_visible", True))
        bottom_visible = bool(gear_rect_state.get("bottom_visible", True))
        top_color = tuple(gear_rect_state.get("top_color", (0, 255, 0)))
        bottom_color = tuple(gear_rect_state.get("bottom_color", (0, 255, 0)))
        top_hazard = bool(gear_rect_state.get("top_hazard", False))
        bottom_hazard = bool(gear_rect_state.get("bottom_hazard", False))
        fcs_scale = 0.5
        ref_w = max(2, int(round((1.0 / 4.0) * DPI * fcs_scale)))
        ref_h = max(2, int(round((1.0 / 3.0) * DPI * fcs_scale)))
        # Keep the same left bias used by FCS page top block (scaled),
        # then shift all three blocks right by one block width and left 1 px.
        top_cx = aircraft_btn_rect.centerx + int(round(-19.0 * fcs_scale)) + ref_w - 1
        # Vertical placement tuned for the compact status button.
        base_top_y = aircraft_btn_rect.top + icon_pad + 8
        # Move only the top block down, then up by 2/3 its height.
        top_y = base_top_y + ref_h - int(round((2.0 / 3.0) * ref_h))
        top_ref = pygame.Rect(0, 0, ref_w, ref_h)
        top_ref.centerx = top_cx
        top_ref.top = top_y
        lower_ref_y = base_top_y + int(round(0.42 * aircraft_btn_rect.height))
        # Bring the lower pair closer together than the FCS-scaled spacing.
        lr_dx = int(round(18.0 * fcs_scale))
        left_ref = pygame.Rect(0, 0, ref_w, ref_h)
        right_ref = pygame.Rect(0, 0, ref_w, ref_h)
        left_ref.centerx = top_cx - lr_dx
        right_ref.centerx = top_cx + lr_dx
        left_ref.top = lower_ref_y
        right_ref.top = lower_ref_y
        clip_rect = aircraft_btn_rect.inflate(-2, -2)
        if top_visible:
            clipped = top_ref.clip(clip_rect)
            if clipped.width > 0 and clipped.height > 0:
                if top_hazard:
                    draw_hazard_stripe_fill_box(surface, clipped)
                else:
                    pygame.draw.rect(surface, top_color, clipped, 0)
        if bottom_visible:
            for rr in (left_ref, right_ref):
                clipped = rr.clip(clip_rect)
                if clipped.width > 0 and clipped.height > 0:
                    if bottom_hazard:
                        draw_hazard_stripe_fill_box(surface, clipped)
                    else:
                        pygame.draw.rect(surface, bottom_color, clipped, 0)

        context.set_icaws_popup_button_rect(icaws_btn_rect.copy())
        # Keep all ICAWS content inside a 1px inset so it never overlaps button borders.
        icaws_content_rect = icaws_btn_rect.inflate(-2, -2)
        # ICAWS label/selection visual box uses the left half of the ICAWS FAB;
        # click area stays the full FAB.
        icaws_label_rect = pygame.Rect(
            icaws_btn_rect.left,
            icaws_btn_rect.top,
            max(1, icaws_btn_rect.width // 2),
            icaws_btn_rect.height,
        ).inflate(-2, -2)
        all_alerts = get_current_icaws_alerts()
        if len(all_alerts) > 10:
            # Keep second-column bottom slot as overflow cue when >10 alerts exist.
            alerts = all_alerts[:9] + [("__DEC__", "overflow")]
        else:
            alerts = all_alerts[:10]

        cw_keys = {f"{txt}|{sev}" for txt, sev in all_alerts if sev in {"warning", "caution"}}
        unacked_raw = ICAWS_STATE.get("unacked_cw", [])
        if isinstance(unacked_raw, list):
            unacked_cw = set(str(x) for x in unacked_raw)
        else:
            unacked_cw = set()
        # Remove unacknowledged entries that are no longer active.
        unacked_cw = {k for k in unacked_cw if k in cw_keys}
        # New caution/warning entries become unacknowledged.
        for k in cw_keys:
            if k not in self._last_cw_keys and k not in unacked_cw:
                unacked_cw.add(k)
        ICAWS_STATE["unacked_cw"] = sorted(unacked_cw)
        ICAWS_STATE["ack_pending"] = len(unacked_cw) > 0
        self._last_cw_keys = cw_keys

        show_icaws_alert_content = not bool(context.icaws_popup_active)
        if (not show_icaws_alert_content) or len(alerts) == 0:
            icaws_text = get_font(18).render("ICAWS", True, (0, 255, 255))
            icaws_rect = icaws_text.get_rect()
            icaws_rect.center = icaws_label_rect.center
            surface.blit(icaws_text, icaws_rect)
        else:
            slot_w = max(1, icaws_content_rect.width // 2)
            cell_font = get_font(12)
            for idx, (txt, sev) in enumerate(alerts):
                col = 0 if idx < 5 else 1
                row = idx if idx < 5 else idx - 5
                col_left = icaws_content_rect.left + (col * icaws_content_rect.width) // 2
                col_right = icaws_content_rect.left + ((col + 1) * icaws_content_rect.width) // 2
                row_top = icaws_content_rect.top + (row * icaws_content_rect.height) // 5
                row_bottom = icaws_content_rect.top + ((row + 1) * icaws_content_rect.height) // 5
                cell = pygame.Rect(
                    col_left,
                    row_top,
                    max(1, col_right - col_left),
                    max(1, row_bottom - row_top),
                )
                if txt == "__DEC__" and sev == "overflow":
                    tri_w_base = max(8, min(cell.width - 6, int(0.18 * DPI)))
                    tri_w = max(6, int(tri_w_base * (2.0 / 3.0)))
                    tri_h = max(6, min(cell.height - 4, int(0.10 * DPI)))
                    cx = cell.centerx
                    cy = cell.centery
                    points = [
                        (cx, cy + tri_h // 2),
                        (cx - tri_w // 2, cy - tri_h // 2),
                        (cx + tri_w // 2, cy - tri_h // 2),
                    ]
                    pygame.draw.polygon(surface, (0, 255, 0), points, 1)
                    continue
                alert_key = f"{txt}|{sev}"
                if sev == "warning":
                    # Warnings always remain white text on red background.
                    # Acknowledged warning: white text on red background.
                    bg, fg = (255, 0, 0), (255, 255, 255)
                elif sev == "caution":
                    # Unacknowledged caution: black text on yellow background.
                    # Acknowledged caution: yellow text on black background.
                    if alert_key in unacked_cw:
                        bg, fg = (255, 255, 0), (0, 0, 0)
                    else:
                        bg, fg = (0, 0, 0), (255, 255, 0)
                else:
                    bg, fg = (0, 0, 0), (0, 255, 0)
                pygame.draw.rect(surface, bg, cell)
                t = cell_font.render(txt, True, fg)
                tr = t.get_rect(left=cell.left + 2, centery=cell.centery)
                surface.blit(t, tr)

        if show_icaws_alert_content and bool(ICAWS_STATE.get("ack_pending", False)):
            has_unacked_warning = any(str(k).endswith("|warning") for k in unacked_cw)
            has_unacked_caution = any(str(k).endswith("|caution") for k in unacked_cw)
            right_half = pygame.Rect(
                icaws_content_rect.centerx,
                icaws_content_rect.top,
                icaws_content_rect.width // 2,
                icaws_content_rect.height,
            )
            cfont = get_font(18)
            if has_unacked_warning and has_unacked_caution:
                top_half = pygame.Rect(right_half.left, right_half.top, right_half.width, max(1, right_half.height // 2))
                bottom_half = pygame.Rect(
                    right_half.left,
                    top_half.bottom,
                    right_half.width,
                    max(1, right_half.height - top_half.height),
                )
                pygame.draw.rect(surface, (255, 0, 0), top_half)
                pygame.draw.rect(surface, (255, 255, 0), bottom_half)
                wtext = cfont.render("WARNING", True, (0, 0, 0))
                wrect = wtext.get_rect(center=top_half.center)
                surface.blit(wtext, wrect)
                ctext = cfont.render("CAUTION", True, (0, 0, 0))
                crect = ctext.get_rect(center=bottom_half.center)
                surface.blit(ctext, crect)
            elif has_unacked_warning:
                pygame.draw.rect(surface, (255, 0, 0), right_half)
                wtext = cfont.render("WARNING", True, (0, 0, 0))
                wrect = wtext.get_rect(center=right_half.center)
                surface.blit(wtext, wrect)
            else:
                pygame.draw.rect(surface, (255, 255, 0), right_half)
                ctext = cfont.render("CAUTION", True, (0, 0, 0))
                crect = ctext.get_rect(center=right_half.center)
                surface.blit(ctext, crect)

        # Draw selection outline last so it always appears above ICAWS content.
        if context.icaws_popup_active:
            pygame.draw.rect(surface, (255, 255, 255), icaws_label_rect, 1)

        if context.autopilot_popup_active:
            pygame.draw.rect(surface, (255, 255, 255), autopilot_btn_rect, 1)
        context.set_autopilot_popup_button_rect(autopilot_btn_rect.copy())
        ap_state = ButtonState(
            button_id="STATUS_AUTOPILOT",
            button_type=ButtonType.STATUS_LABEL,
            text="AP\nAT",
            flash_until_ms=0,
            h_align="center",
            v_align="center",
            font_size=24,
        )
        render_button(surface, autopilot_btn_rect, ap_state, get_font, 0)

        # Fuel status icon: stacked grouped tank bars at right, green totals at left.
        snapshot = context.get_status_fuel_snapshot()
        groups = snapshot.get("groups", [])
        joker = float(snapshot.get("joker", 0.0))
        bingo = float(snapshot.get("bingo", 0.0))
        max_total = max(0.001, float(snapshot.get("max_total", 1.0)))
        fuel_stale = bool(getattr(FuelFormat, "_shared_stale_data", False))
        sensor_map = getattr(FuelFormat, "_shared_sensor_degrd", {})
        fuel_sensor_degrd = False
        if isinstance(sensor_map, dict):
            fuel_sensor_degrd = any(bool(sensor_map.get(k, False)) for k in ("F1", "F2L", "F2R", "F3L", "F3R", "F4L", "F4R", "F5L", "F5R", "LW", "RW"))

        bar_w = max(2, int(0.15 * DPI))
        bar_gap = 2
        inner_margin = 4
        bars_total_h = fuel_btn_rect.height - inner_margin * 2
        unit_h = max(2, int((bars_total_h - 5 * bar_gap) / 6.5))
        top_h = int(unit_h * 1.5)
        x_bar = fuel_btn_rect.right - inner_margin - bar_w - 5
        y_bar = fuel_btn_rect.top + inner_margin + 0
        bars_top = y_bar
        for idx in range(6):
            h = top_h if idx == 0 else unit_h
            r = pygame.Rect(x_bar, y_bar, bar_w, h)
            pygame.draw.rect(surface, (0, 0, 0), r)
            y_bar += h + bar_gap
        # Shared stacked fuel level: depletes top segment first, then next below.
        total_qty = sum(float(g.get("qty", 0.0)) for g in groups)
        total_max_qty = max(1.0, sum(float(g.get("max", 0.0)) for g in groups))
        stack_ratio = 1.0 if fuel_stale else max(0.0, min(1.0, total_qty / total_max_qty))
        bar_rects: List[pygame.Rect] = []
        y_bar = fuel_btn_rect.top + inner_margin + 0
        for idx in range(6):
            h = top_h if idx == 0 else unit_h
            bar_rects.append(pygame.Rect(x_bar, y_bar, bar_w, h))
            y_bar += h + bar_gap
        total_stack_h = sum(br.height for br in bar_rects)
        remaining_fill = int(total_stack_h * stack_ratio)
        fill_by_index = [0] * len(bar_rects)
        for idx in range(len(bar_rects) - 1, -1, -1):
            h = bar_rects[idx].height
            fill_h = min(h, remaining_fill)
            fill_by_index[idx] = fill_h
            remaining_fill -= fill_h
            if remaining_fill <= 0:
                break
        for idx, br in enumerate(bar_rects):
            fill_h = fill_by_index[idx]
            if fill_h > 0:
                fill = pygame.Rect(br.left, br.bottom - fill_h, br.width, fill_h)
                pygame.draw.rect(surface, (128, 128, 128) if fuel_stale else (66, 100, 231), fill)
        bars_bottom = y_bar - bar_gap
        bars_h = max(1, bars_bottom - bars_top)

        def marker_y(val: float) -> int:
            p = max(0.0, min(1.0, val / max_total))
            return int(bars_bottom - p * bars_h)

        if not fuel_stale:
            jy = marker_y(joker)
            by = marker_y(bingo)
            pygame.draw.line(surface, (255, 255, 255), (x_bar + 3, jy), (x_bar + bar_w + 3, jy), 1)
            pygame.draw.line(surface, (255, 255, 0), (x_bar + 3, by), (x_bar + bar_w + 3, by), 1)

        tot, int_fuel, ext = context.get_status_fuel_values()
        green = parse_hex_color("00FF00")
        yellow = (255, 255, 0)
        gray = (128, 128, 128)
        value_font = get_font(13)
        label_font = get_font(13)
        value_x = fuel_btn_rect.left + 32
        value_line_centers: List[int] = []
        if not fuel_stale:
            value_lines = [f"{tot:.1f}", f"{int_fuel:.1f}", f"{ext:.1f}"]
            value_colors = [
                yellow if fuel_sensor_degrd else green,
                yellow if fuel_sensor_degrd else green,
                green,
            ]
            value_surfs = [value_font.render(v, True, c) for v, c in zip(value_lines, value_colors)]
            value_h = sum(s.get_height() for s in value_surfs) + 2 * 2
            value_y = fuel_btn_rect.centery - value_h // 2
            y = value_y
            for s in value_surfs:
                surface.blit(s, (value_x, y))
                value_line_centers.append(y + s.get_height() // 2)
                y += s.get_height() + 2
        else:
            row_step = max(1, fuel_btn_rect.height // 4)
            value_line_centers = [
                fuel_btn_rect.top + row_step,
                fuel_btn_rect.top + 2 * row_step,
                fuel_btn_rect.top + 3 * row_step,
            ]

        i_surf = label_font.render("I", True, gray if fuel_stale else (yellow if fuel_sensor_degrd else green))
        e_surf = label_font.render("E", True, gray if fuel_stale else green)
        ie_x = fuel_btn_rect.left + 10
        surface.blit(i_surf, (ie_x, value_line_centers[1] - i_surf.get_height() // 2))
        surface.blit(e_surf, (ie_x, value_line_centers[2] - e_surf.get_height() // 2))

        # SMS icon text.
        sms_green = parse_hex_color("00FF00")
        sms_white = (255, 255, 255)
        sms_font = get_font(14)
        mrm_count = int(SMS_STATE.get("mrm_count", 0))
        srm_count = int(SMS_STATE.get("srm_count", 0))
        gun_count = int(SMS_STATE.get("gun_count", 182))
        as_count = int(SMS_STATE.get("as_count", 0))
        left_lines = [f"{mrm_count} MRM", f"{srm_count} SRM", f"{gun_count}GUN", f"{as_count} AS"]
        left_surfs = [sms_font.render(t, True, sms_green) for t in left_lines]
        line_gap = 1
        total_h = sum(s.get_height() for s in left_surfs) + line_gap * (len(left_surfs) - 1)
        y0 = sms_btn_rect.centery - total_h // 2
        lx = sms_btn_rect.left + 7
        line_y = []
        y = y0
        for s in left_surfs:
            surface.blit(s, (lx, y))
            line_y.append(y + s.get_height() // 2)
            y += s.get_height() + line_gap
        wx = sms_btn_rect.right - 25
        chaff = int(SMS_STATE.get("chaff", 10))
        flare = int(SMS_STATE.get("flare", 10))
        w10 = sms_font.render(str(chaff), True, sms_white)
        w20 = sms_font.render(str(flare), True, sms_white)
        surface.blit(w10, w10.get_rect(right=wx, centery=line_y[0]))
        surface.blit(w20, w20.get_rect(right=wx, centery=line_y[1]))

        text_surface = font.render(text, True, color)
        text_rect = text_surface.get_rect(center=full_rect.center)

        left_base_x = text_rect.x + font.size("S")[0]
        right_base_x = text_rect.x + font.size("SWA")[0]

        center_y = full_rect.centery
        tri_half_h = max(10, min(full_rect.height // 2 - 2, text_rect.height // 2 + 10))
        top_y = center_y - tri_half_h
        bottom_y = center_y + tri_half_h
        tip_offset = 22

        left_tip = (left_base_x - tip_offset, center_y)
        right_tip = (right_base_x + tip_offset, center_y)

        pygame.draw.line(surface, color, left_tip, (left_base_x, top_y), 1)
        pygame.draw.line(surface, color, left_tip, (left_base_x, bottom_y), 1)
        pygame.draw.line(surface, color, right_tip, (right_base_x, top_y), 1)
        pygame.draw.line(surface, color, right_tip, (right_base_x, bottom_y), 1)

        gap_top = text_rect.top - 1
        gap_bottom = text_rect.bottom + 1
        if top_y < gap_top:
            pygame.draw.line(surface, color, (left_base_x, top_y), (left_base_x, gap_top), 1)
            pygame.draw.line(surface, color, (right_base_x, top_y), (right_base_x, gap_top), 1)
        if gap_bottom < bottom_y:
            pygame.draw.line(surface, color, (left_base_x, gap_bottom), (left_base_x, bottom_y), 1)
            pygame.draw.line(surface, color, (right_base_x, gap_bottom), (right_base_x, bottom_y), 1)

        surface.blit(text_surface, text_rect)
        swap_hit_rect = pygame.Rect(0, 0, int(1.0 * DPI), full_rect.height)
        swap_hit_rect.centerx = text_rect.centerx
        swap_hit_rect.y = full_rect.y
        context.set_swap_button_rect(swap_hit_rect)

        menu_box_size = max(1, int(STATUS_MENU_BOX_SIZE_IN * DPI))
        grid_cells = max(1, STATUS_MENU_GRID_CELLS)
        menu_grid_color = (128, 128, 128)

        # MENU placement baseline is above Portal 4 T1, then SWAP shifts the
        # entire right-side status half to the left side while preserving order.
        menu_portal_index = 3
        menu_cell_center_x = full_rect.x + int((menu_portal_index * 5.0 + 0.5) * DPI)
        menu_offset = int((0.125 * DPI) / 2)
        menu_rect = pygame.Rect(
            menu_cell_center_x - menu_box_size // 2 + menu_offset,
            rect.y + (rect.height - menu_box_size) // 2,
            menu_box_size,
            menu_box_size,
        )
        nav_btn_w = int(1.125 * DPI)
        nav_btn_rect = pygame.Rect(0, full_rect.top, nav_btn_w, int(1.0 * DPI))
        nav_btn_rect.right = menu_rect.left - 2 - int((0.125 * DPI) + (0.125 * DPI) / 4)

        record_btn_rect = pygame.Rect(0, full_rect.top, nav_btn_w, int(1.0 * DPI))
        comm_btn_rect = pygame.Rect(0, full_rect.top, int(2.25 * DPI), int(1.0 * DPI))
        record_btn_rect.right = nav_btn_rect.left - 2
        comm_btn_rect.right = record_btn_rect.left - 2 + int((0.125 * DPI) / 4)
        if context.status_swapped:
            for _r in (menu_rect, nav_btn_rect, record_btn_rect, comm_btn_rect):
                _r.x -= half_span_w
        context.set_record_button_rect(record_btn_rect.copy())
        if context.comm_popup_active:
            pygame.draw.rect(surface, (255, 255, 255), comm_btn_rect, 1)
        context.set_comm_popup_button_rect(comm_btn_rect.copy())
        # COMM symbology.
        comm_font = get_font(14)
        comm_label_font = get_font(max(5, int(round(14 / 3.0))))
        cyan = (0, 255, 255)
        green = (0, 255, 0)
        white = (255, 255, 255)
        comm_state = context.get_comm_state()
        ptt_radio = str(comm_state.get("ptt_radio", "")).strip().lower()
        rx_until = comm_state.get("rx_until", {})
        if not isinstance(rx_until, dict):
            rx_until = {}
        now_ticks = pygame.time.get_ticks()

        def _draw_radio_letter(x: int, y: int, letter: str, *, tx_active: bool, rx_active: bool, mute_on: bool) -> pygame.Rect:
            letter_surf = comm_font.render(str(letter), True, (0, 0, 0) if tx_active else cyan)
            letter_rect = letter_surf.get_rect(topleft=(x, y))
            if tx_active:
                pygame.draw.rect(surface, cyan, letter_rect.inflate(4, 2))
            if rx_active:
                pygame.draw.rect(surface, white, letter_rect.inflate(6, 4), 1)
            surface.blit(letter_surf, letter_rect)
            if mute_on:
                x0 = letter_rect.left - 1
                y0 = letter_rect.top - 1
                x1 = letter_rect.right + 1
                y1 = letter_rect.bottom + 1
                # Draw a thicker mute X by over-stroking both diagonals.
                for off in (-1, 0, 1):
                    pygame.draw.line(surface, white, (x0 + off, y0), (x1 + off, y1), 1)
                    pygame.draw.line(surface, white, (x0 + off, y1), (x1 + off, y0), 1)
            return letter_rect

        rows: List[Tuple[str, str, bool]] = [
            ("A", "coma", bool(comm_state.get("coma_on", True))),
            ("B", "comb", bool(comm_state.get("comb_on", True))),
            ("C", "comc", bool(comm_state.get("comc_on", True))),
        ]
        row_h = max(1, comm_btn_rect.height // 3)
        y0 = comm_btn_rect.top
        left_x = comm_btn_rect.left + 6
        space_w = max(1, comm_font.size(" ")[0])
        row_centers: List[int] = []
        # (center_label, aj_text, secure_text, is_on)
        row_right_parts: List[Tuple[str, str, str, bool]] = []
        for i, (letter, radio_key, is_on) in enumerate(rows):
            y = y0 + i * row_h + max(0, (row_h - comm_font.get_height()) // 2)
            rx_active = int(rx_until.get(radio_key, 0)) > now_ticks
            tx_active = ptt_radio == radio_key
            prof = _comm_profile_for_radio(comm_state, radio_key)
            mute_on = bool(prof.get("mute_on", False))
            freq_key = _comm_freq_key_for_radio(radio_key)
            freq = str(comm_state.get(freq_key, "000.000")) if freq_key != "" else "000.000"
            mode_indicator = _comm_band_indicator_for_mode(_comm_mode_for_radio(comm_state, radio_key))
            preset_number = _comm_preset_number_for_freq(comm_state, radio_key, freq)
            display_value = str(preset_number) if preset_number is not None else freq
            left_lbl, mid_lbl, right_lbl = _comm_row_label_parts(comm_state, radio_key, freq, preset_number)
            row_right_parts.append((mid_lbl, left_lbl, right_lbl, is_on))
            l_rect = _draw_radio_letter(left_x, y, letter, tx_active=tx_active, rx_active=rx_active, mute_on=mute_on)
            x = l_rect.right + space_w
            if is_on:
                if mode_indicator != "":
                    b_s = comm_font.render(mode_indicator, True, cyan)
                    surface.blit(b_s, (x, y))
                    x += b_s.get_width() + space_w
                else:
                    x += space_w
                value_color = green if tx_active else cyan
                f_s = comm_font.render(display_value, True, value_color)
                surface.blit(f_s, (x, y))
                row_centers.append(y + max(l_rect.height, f_s.get_height()) // 2)
            else:
                row_centers.append(y + l_rect.height // 2)
        right_margin = comm_btn_rect.right - 6
        box_gap = max(1, comm_label_font.size(" ")[0])
        s_box_w = comm_label_font.size("S")[0]
        aj_box_text = "AJ     "
        aj_box_w = comm_label_font.size(aj_box_text)[0]
        for i, (mid_lbl, left_lbl, right_lbl, is_on) in enumerate(row_right_parts):
            if not is_on:
                continue
            cy = row_centers[i]
            cursor_right = right_margin
            if right_lbl != "":
                s_sec = comm_label_font.render("S", True, cyan)
                r_sec = s_sec.get_rect(centery=cy)
                r_sec.x = cursor_right - s_sec.get_width()
                surface.blit(s_sec, r_sec)
                cursor_right -= s_box_w + box_gap
            if left_lbl != "":
                s_aj = comm_label_font.render(aj_box_text, True, cyan)
                r_aj = s_aj.get_rect(centery=cy)
                r_aj.x = cursor_right - s_aj.get_width()
                surface.blit(s_aj, r_aj)
                cursor_right -= aj_box_w + box_gap
            if mid_lbl != "":
                s_mid = comm_label_font.render(mid_lbl, True, cyan)
                r_mid = s_mid.get_rect(centery=cy)
                r_mid.x = cursor_right - s_mid.get_width()
                surface.blit(s_mid, r_mid)
        mode_name = str(getattr(context, "record_mode_name", "RECORD")).strip().upper()
        if mode_name == "PICTURE":
            record_top = "PICTURE"
        else:
            record_top = "RECORD"
        rec_top_surf = get_font(15).render(record_top, True, (0, 255, 0))
        rec_top_rect = rec_top_surf.get_rect(centerx=record_btn_rect.centerx)
        rec_top_rect.y = record_btn_rect.top + 3
        surface.blit(rec_top_surf, rec_top_rect)
        if context.record_started:
            h = max(0, int(context.record_elapsed_seconds)) // 3600
            m = (max(0, int(context.record_elapsed_seconds)) % 3600) // 60
            s = max(0, int(context.record_elapsed_seconds)) % 60
            t = f"{h}:{m:02d}:{s:02d}"
            time_surf = get_font(17).render(t, True, (0, 255, 0))
            time_rect = time_surf.get_rect(center=record_btn_rect.center)
            surface.blit(time_surf, time_rect)
        area_label = str(getattr(context, "record_area_label", "L H R"))
        if area_label.strip() == "":
            area_label = "L H R"
        lhr_surf = get_font(15).render(area_label, True, (0, 255, 255))
        lhr_rect = lhr_surf.get_rect(centerx=record_btn_rect.centerx)
        lhr_rect.bottom = record_btn_rect.bottom - 2
        surface.blit(lhr_surf, lhr_rect)
        if context.nav_popup_active:
            pygame.draw.rect(surface, (255, 255, 255), nav_btn_rect, 1)
        context.set_nav_popup_button_rect(nav_btn_rect.copy())
        # NAV button symbology.
        # 8-point white star at top-left.
        star_cx = nav_btn_rect.left + 12
        star_cy = nav_btn_rect.top + 12
        star_r = 5
        pygame.draw.line(surface, (255, 255, 255), (star_cx - star_r, star_cy), (star_cx + star_r, star_cy), 1)
        pygame.draw.line(surface, (255, 255, 255), (star_cx, star_cy - star_r), (star_cx, star_cy + star_r), 1)
        pygame.draw.line(surface, (255, 255, 255), (star_cx - 4, star_cy - 4), (star_cx + 4, star_cy + 4), 1)
        pygame.draw.line(surface, (255, 255, 255), (star_cx - 4, star_cy + 4), (star_cx + 4, star_cy - 4), 1)
        # To the right of the star write: "2  AUTO" / "R2".
        top_font = get_font(13)
        nav_state = NAV_STATE
        c1_val = str(nav_state.get("c1_value", "001"))
        d7_mode = int(nav_state.get("d7_mode", 1))
        d7_text = "AUTO" if d7_mode == 1 else "MAN"
        try:
            r_idx = int(nav_state.get("de1_r_idx", 1))
        except Exception:
            r_idx = 1
        r_idx = max(1, r_idx)
        txt2 = top_font.render(c1_val, True, (0, 255, 255))
        txt_auto = top_font.render(d7_text, True, (255, 255, 255))
        top_y = nav_btn_rect.top + 6
        x2 = star_cx + 10
        surface.blit(txt2, (x2, top_y))
        surface.blit(txt_auto, (x2 + txt2.get_width() + 7, top_y))
        # "R#" below, aligned with the first line block.
        r2 = get_font(16).render(f"R{r_idx}", True, (0, 255, 255))
        r2_rect = r2.get_rect()
        r2_rect.left = x2 + get_font(16).size(" ")[0]
        r2_rect.top = top_y + txt2.get_height() + 2
        surface.blit(r2, r2_rect)

        pygame.draw.rect(surface, menu_grid_color, menu_rect, 1)
        for i in range(1, grid_cells):
            x = menu_rect.x + (i * menu_rect.width) // grid_cells
            y = menu_rect.y + (i * menu_rect.height) // grid_cells
            pygame.draw.line(surface, menu_grid_color, (x, menu_rect.top), (x, menu_rect.bottom-1), 1)
            pygame.draw.line(surface, menu_grid_color, (menu_rect.left, y), (menu_rect.right-1, y), 1)

        menu_state = ButtonState(
            button_id="STATUS_MENU",
            button_type=ButtonType.MOMENTARY_SINGLE,
            text="MENU",
            flash_until_ms=1 if context.status_menu_button_flashing else 0,
            font_size=23,
        )
        render_button(surface, menu_rect, menu_state, get_font, 0)
        # Make MENU clickable across a 1.125in selection box, not just the
        # inner 0.75in rendered grid.
        menu_hit_rect = menu_rect.inflate(int(0.375 * DPI), int(0.375 * DPI))
        context.set_status_menu_button_rect(menu_hit_rect.copy())

        # IFF / ALTITUDE / WIND buttons (1.125 in each), to the right of MENU.
        aux_w = int(1.125 * DPI)
        aux_h = int(1.0 * DPI)
        aux_gap = 2
        labels = ["IFF", "ALTITUDE", "WIND"]
        start_x = menu_rect.right + aux_gap + int(0.125 * DPI)
        rects: List[pygame.Rect] = []
        for i in range(3):
            r = pygame.Rect(start_x + i * (aux_w + aux_gap), full_rect.top, aux_w, aux_h)
            rects.append(r)
        for i, lbl in enumerate(labels):
            r = rects[i]
            is_active = (
                (lbl == "IFF" and context.iff_popup_active)
                or (lbl == "ALTITUDE" and context.altitude_popup_active)
                or (lbl == "WIND" and context.time_popup_active)
            )
            if is_active:
                pygame.draw.rect(surface, (255, 255, 255), r, 1)
            btn = ButtonState(
                button_id=f"STATUS_{lbl}",
                button_type=ButtonType.STATUS_LABEL,
                text="" if lbl in {"IFF", "ALTITUDE", "WIND"} else lbl,
                font_size=16,
            )
            render_button(surface, r, btn, get_font, 0)
            if lbl == "IFF":
                state = IFF_STATE
                iff_on = bool(state.get("iff_on", False))
                emergency_on = bool(state.get("emergency_on", False))
                mode4_on = bool(state.get("mode4_sf_on", False))
                emcon_flag = bool(state.get("emcon_flag", False))
                cm_fail_iff_active = bool(state.get("cm_fail_iff_active", False))
                mode_c_degd_active = bool(state.get("mode_c_degd_active", False))
                degrade_flag = bool(state.get("degrade_flag", False)) or mode_c_degd_active or cm_fail_iff_active
                degrade_mode = str(state.get("degrade_mode", "")).strip().upper()
                now_ms = int(state.get("now_ms", 0))
                status_flash = state.get("status_flash_until", {})
                if not isinstance(status_flash, dict):
                    status_flash = {}
                mode_flash = int(status_flash.get("mode", 0)) > now_ms
                mode1_flash = int(status_flash.get("mode1", 0)) > now_ms
                mode3_flash = int(status_flash.get("mode3", 0)) > now_ms or int(state.get("mode3_highlight_until_ms", 0)) > now_ms
                try:
                    on_since_ms = int(state.get("on_since_ms", 0))
                except Exception:
                    on_since_ms = 0
                try:
                    mode4_on_since_ms = int(state.get("mode4_on_since_ms", 0))
                except Exception:
                    mode4_on_since_ms = 0
                if iff_on and on_since_ms <= 0:
                    on_since_ms = now_ms
                if mode4_on and mode4_on_since_ms <= 0:
                    mode4_on_since_ms = now_ms
                highlight_cyan = iff_on and (now_ms - on_since_ms < 3000)
                mode4_highlight = iff_on and mode4_on and (now_ms - mode4_on_since_ms < 3000)
                white = (255, 255, 255)
                purple = (255, 0, 255)
                yellow = (255, 255, 0)
                if cm_fail_iff_active:
                    main_color = white
                else:
                    main_color = (0, 255, 255) if (emcon_flag and iff_on) else ((0, 255, 255) if highlight_cyan else (255, 255, 255))

                try:
                    mode_options = state.get("mode_options", ["OFF", "STBY", "MAN", "AUTO"])
                    if not isinstance(mode_options, list) or len(mode_options) == 0:
                        mode_options = ["OFF", "STBY", "MAN", "AUTO"]
                    mode_idx = int(state.get("mode_idx", 0))
                    mode_idx = max(0, min(len(mode_options) - 1, mode_idx))
                    mode_text = str(mode_options[mode_idx]) if iff_on else "OFF"
                except Exception:
                    mode_text = "OFF" if not iff_on else "STBY"
                if iff_on and emergency_on:
                    mode_text = "EMER"

                mode1 = str(state.get("mode1", "00"))
                mode3 = str(state.get("mode3a", "1200"))
                font_iff = get_font(13)
                font_mode = get_font(12)
                font_mid = get_font(13)
                font_code = get_font(12)
                font_idx = get_font(12)

                iff_s = font_iff.render("IFF", True, main_color if iff_on else white)
                iff_rect = iff_s.get_rect()
                iff_rect.left = r.left + 4
                iff_rect.top = r.top + 3
                surface.blit(iff_s, iff_rect)

                mode_label_text = "DEGD" if (cm_fail_iff_active or (iff_on and degrade_flag)) else mode_text
                mode_label_color = yellow if (cm_fail_iff_active or (iff_on and degrade_flag)) else white
                emer_highlight = str(mode_text).upper() == "EMER"
                mode_s = font_mode.render(mode_label_text, True, (0, 0, 0) if emer_highlight else mode_label_color)
                mode_rect = mode_s.get_rect()
                mode_rect.top = r.top + 4
                mode_rect.right = r.right - 4
                if emer_highlight:
                    pygame.draw.rect(surface, (0, 255, 255), mode_rect.inflate(4, 2))
                surface.blit(mode_s, mode_rect)

                # CM FAIL - IFF: status button only shows "IFF" and "DEGD".
                if cm_fail_iff_active:
                    continue

                if iff_on:
                    code_color = main_color
                    y_line3 = r.top + 42
                    y_line4 = r.top + 58

                    m1_s = font_code.render(mode1, True, (0, 0, 0) if mode1_flash else code_color)
                    m1_rect = m1_s.get_rect()
                    m1_rect.left = r.left + 6
                    m1_rect.top = y_line3
                    if mode1_flash:
                        pygame.draw.rect(surface, (0, 255, 255), m1_rect.inflate(4, 2))
                    surface.blit(m1_s, m1_rect)

                    m3_s = font_code.render(mode3, True, (0, 0, 0) if mode3_flash else code_color)
                    m3_rect = m3_s.get_rect()
                    m3_rect.right = r.right - 6
                    m3_rect.top = y_line3
                    if mode3_flash:
                        pygame.draw.rect(surface, (0, 255, 255), m3_rect.inflate(4, 2))
                    surface.blit(m3_s, m3_rect)

                    if (not mode4_on or mode4_highlight) and not emcon_flag:
                        i1_s = font_idx.render("1", True, purple)
                        i1_rect = i1_s.get_rect()
                        i1_rect.centerx = m1_rect.centerx
                        i1_rect.top = y_line4
                        surface.blit(i1_s, i1_rect)

                        i4_s = font_idx.render("4", True, purple)
                        i4_rect = i4_s.get_rect()
                        i4_rect.centerx = m3_rect.centerx
                        i4_rect.top = y_line4
                        surface.blit(i4_s, i4_rect)

                    if not highlight_cyan:
                        if emcon_flag:
                            emcon_s = font_mid.render("EMCON", True, white)
                            emcon_rect = emcon_s.get_rect(centerx=r.centerx)
                            emcon_rect.top = r.top + 24
                            surface.blit(emcon_s, emcon_rect)
                        elif degrade_flag:
                            base_line = "123 C 4"
                            idx_map = {"1": 0, "2": 1, "3": 2, "C": 4, "4": 6}
                            hi_idx = idx_map.get(degrade_mode, -1)
                            x = r.left + 6
                            y = r.top + 24
                            for i, ch in enumerate(base_line):
                                ch_color = yellow if i == hi_idx else white
                                ch_s = font_mid.render(ch, True, ch_color)
                                ch_rect = ch_s.get_rect()
                                ch_rect.left = x
                                ch_rect.top = y
                                surface.blit(ch_s, ch_rect)
                                x += ch_rect.width
                        elif mode4_highlight:
                            mid_left_s = font_mid.render("123 C ", True, white)
                            mid_left_rect = mid_left_s.get_rect()
                            mid_left_rect.left = r.left + 6
                            mid_left_rect.top = r.top + 24
                            surface.blit(mid_left_s, mid_left_rect)

                            mid_4_s = font_mid.render("4", True, (0, 0, 0))
                            mid_4_rect = mid_4_s.get_rect()
                            mid_4_rect.left = mid_left_rect.right
                            mid_4_rect.top = mid_left_rect.top
                            pygame.draw.rect(surface, white, mid_4_rect.inflate(4, 2))
                            surface.blit(mid_4_s, mid_4_rect)
                        else:
                            mid_s = font_mid.render("123 C 4", True, white)
                            mid_rect = mid_s.get_rect()
                            mid_rect.left = r.left + 6
                            mid_rect.top = r.top + 24
                            surface.blit(mid_s, mid_rect)

                    if mode4_on and not mode4_highlight:
                        mode4_s = font_idx.render("MODE 4", True, (0, 0, 0))
                        mode4_rect = mode4_s.get_rect(centerx=r.centerx)
                        mode4_rect.top = y_line4
                        pygame.draw.rect(surface, yellow, mode4_rect.inflate(6, 2))
                        surface.blit(mode4_s, mode4_rect)
            elif lbl == "ALTITUDE":
                state = ALTITUDE_STATE
                cyan = (0, 255, 255)
                line1 = str(state.get("line1_value", state.get("baro_inhg", "29.87")))
                cab = str(state.get("cab", "0000"))
                options = state.get("gcas_options", ["OFF", "AUTO", "LW-LVL", "STBY"])
                try:
                    gidx = int(state.get("gcas_idx", 1))
                except Exception:
                    gidx = 1
                if not isinstance(options, list) or not options:
                    options = ["OFF", "AUTO", "LW-LVL", "STBY"]
                gidx = max(0, min(len(options) - 1, gidx))
                gcas = str(options[gidx])
                alow = str(state.get("alow", "0000"))

                f1 = get_font(12)
                f2 = get_font(11)
                y1 = r.top + 4
                y2 = r.top + 22
                y3 = r.top + 39
                y4 = r.top + 56
                lpad = 6
                rpad = 6

                l1s = f1.render(line1, True, cyan)
                l1r = l1s.get_rect(centerx=r.centerx)
                l1r.top = y1
                surface.blit(l1s, l1r)

                for y, left_txt, right_txt in (
                    (y2, "CAB", cab),
                    (y3, "GCAS", gcas),
                    (y4, "ALOW", alow),
                ):
                    ls = f2.render(left_txt, True, cyan)
                    lr = ls.get_rect()
                    lr.left = r.left + lpad
                    lr.top = y
                    surface.blit(ls, lr)
                    rs = f2.render(right_txt, True, cyan)
                    rr = rs.get_rect()
                    rr.right = r.right - rpad
                    rr.top = y
                    surface.blit(rs, rr)
            elif lbl == "WIND":
                white = (255, 255, 255)
                cyan = (0, 255, 255)
                f = get_font(11)
                x = r.left + 6
                y1 = r.top + 4
                y2 = r.top + 22
                y3 = r.top + 39
                y4 = r.top + 56
                local_time, zulu_time = _wind_status_button_times()
                surface.blit(f.render(local_time, True, white), (x, y1))
                surface.blit(f.render(zulu_time, True, cyan), (x, y2))
                surface.blit(f.render("WIND:", True, cyan), (x, y3))
                surface.blit(f.render("360/    0", True, cyan), (x, y4))
            if lbl == "IFF":
                context.set_iff_popup_button_rect(r.copy())
            elif lbl == "ALTITUDE":
                context.set_altitude_popup_button_rect(r.copy())
            elif lbl == "WIND":
                context.set_time_popup_button_rect(r.copy())

        if context.status_menu_popup_active:
            outline_w = int(1.125 * DPI)
            outline_h = int(1 * DPI)
            outline_rect = pygame.Rect(0, 0, outline_w, outline_h)
            outline_rect.center = menu_rect.center
            pygame.draw.rect(surface, (255, 255, 255), outline_rect, 1)
