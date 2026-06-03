from formats import *  # noqa: F401,F403


class IcawsFormat(FormatBase):
    name: str = "ICAWS"
    _popup_anchor_portal_idx: int = 0
    _popup_anchor_scope_key: object = "portal:0"

    @classmethod
    def _scope_idx(cls) -> object:
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
        IcawsFormat._popup_anchor_scope_key = scope_key

    @classmethod
    def _scoped_keys(cls) -> Set[str]:
        return {"selected_idx", "selected_scroll", "reason_page_idx", "selected_alert_key"}

    @classmethod
    def _scoped_state(cls) -> Dict[str, object]:
        by_portal = ICAWS_STATE.get("_ui_by_portal")
        if not isinstance(by_portal, dict):
            by_portal = {}
            ICAWS_STATE["_ui_by_portal"] = by_portal
        key = cls._scope_idx()
        state = by_portal.get(key)
        if not isinstance(state, dict):
            state = {}
            by_portal[key] = state
        state.setdefault("selected_idx", 0)
        state.setdefault("selected_scroll", 0)
        state.setdefault("reason_page_idx", 0)
        state.setdefault("selected_alert_key", "")
        return state

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
            idx = int(IcawsFormat._popup_anchor_portal_idx)
        IcawsFormat._popup_anchor_portal_idx = max(0, min(3, int(idx)))
        try:
            current_scope = str(IcawsFormat._popup_anchor_scope_key)
        except Exception:
            current_scope = ""
        if current_scope.startswith("portal:") or current_scope == "":
            IcawsFormat._popup_anchor_scope_key = f"portal:{IcawsFormat._popup_anchor_portal_idx}"
        scoped = self._scoped_state()
        for key in self._scoped_keys():
            ICAWS_STATE[key] = scoped.get(key)

    @staticmethod
    def _state_int(key: str, default: int = 0) -> int:
        if key in IcawsFormat._scoped_keys():
            try:
                return int(IcawsFormat._scoped_state().get(key, default))
            except Exception:
                return int(default)
        try:
            return int(ICAWS_STATE.get(key, default))
        except Exception:
            return int(default)

    @staticmethod
    def _set_state_int(key: str, value: int) -> None:
        if key in IcawsFormat._scoped_keys():
            IcawsFormat._scoped_state()[key] = int(value)
        ICAWS_STATE[key] = int(value)

    @staticmethod
    def _state_str(key: str, default: str = "") -> str:
        if key in IcawsFormat._scoped_keys():
            try:
                return str(IcawsFormat._scoped_state().get(key, default))
            except Exception:
                return str(default)
        try:
            return str(ICAWS_STATE.get(key, default))
        except Exception:
            return str(default)

    @staticmethod
    def _linked_reasons_for_alert(text: str, severity: str) -> List[str]:
        alert_text = str(text).strip()
        alert_sev = str(severity).strip().lower()
        alert_upper = alert_text.upper()
        reasons: List[str] = []
        alert_key = _icaw_alert_key(alert_text, alert_sev)
        bindings = ICAWS_STATE.get("hrc_bindings", {})
        if isinstance(bindings, dict):
            bound = bindings.get(alert_key, {})
            if isinstance(bound, dict):
                hrc_value = str(bound.get("hrc", "")).strip()
                if hrc_value != "":
                    reasons.append(hrc_value)
        # Preserve V/S BIT linkage from ICAWS into PHM VSP reasons.
        if alert_upper.replace("/", "") == "VS BIT NO GO":
            try:
                status, vs_reasons = PhmFormat._vs_bit_runtime_state()
                if str(status).upper() == "FN":
                    reasons.extend(vs_reasons)
            except Exception:
                pass
            try:
                reasons.extend(PhmFormat._phm_debug_reasons_for_keys(["VSP"] + list(PHM_SYSTEM_SUBSYSTEMS.get("VSP", []))))
            except Exception:
                pass
        # Fuel degrade cautions are runtime-generated and should explicitly
        # show the associated PHM HRC/FnA entries they triggered.
        if alert_upper == "TANK DEGRD":
            try:
                reasons.extend(PhmFormat._phm_debug_reasons_for_keys(["FEED"]))
            except Exception:
                pass
        elif alert_upper == "SENSOR DEGRD":
            try:
                reasons.extend(PhmFormat._phm_debug_reasons_for_keys(["MEASUR"]))
            except Exception:
                pass
        formatted: List[str] = []
        for reason in reasons:
            try:
                text_reason = PhmFormat._format_fna_reason(str(reason))
            except Exception:
                text_reason = str(reason).strip()
            if text_reason == "":
                continue
            if text_reason not in formatted:
                formatted.append(text_reason)
        return formatted

    def _osb_box(self, rect: pygame.Rect, label: str) -> Optional[pygame.Rect]:
        if len(label) < 2:
            return None
        side = label[0]
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

    def _draw_inc_dec_symbols(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        cyan = (0, 255, 255)
        # Vertical INC/DEC at L1/L2.
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
            pygame.draw.polygon(surface, cyan, up_points, 0)
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
            pygame.draw.polygon(surface, cyan, down_points, 0)

    def _set_selected_index(self, idx: int, count: int) -> int:
        if count <= 0:
            self._set_state_int("selected_idx", 0)
            self._set_state_int("selected_scroll", 0)
            self._set_state_int("reason_page_idx", 0)
            self._scoped_state()["selected_alert_key"] = ""
            ICAWS_STATE["selected_alert_key"] = ""
            return 0
        clamped = max(0, min(count - 1, int(idx)))
        self._set_state_int("selected_idx", clamped)
        return clamped

    def _update_test_hold(self, rect: pygame.Rect, is_primary: bool) -> bool:
        if not is_primary:
            return False
        t3 = self._osb_box(rect, "T3")
        if t3 is None:
            return False
        try:
            left_held = bool(pygame.mouse.get_pressed(3)[0])
            mouse_pos = pygame.mouse.get_pos()
            now_ms = int(pygame.time.get_ticks())
        except Exception:
            return False
        if left_held and t3.collidepoint(mouse_pos):
            ICAWS_STATE["test_active_until_ms"] = now_ms + 150
            return True
        return now_ms <= int(ICAWS_STATE.get("test_active_until_ms", 0))

    def _draw_primary_buttons(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        context: FormatContext,
        prev_enabled: bool,
        next_enabled: bool,
        test_held: bool,
        page_text: str,
    ) -> None:
        osbs: List[Tuple[str, ButtonState]] = [
            (
                "L5",
                ButtonState(
                    button_id="ICAWS_L5",
                    button_type=ButtonType.PAGE_ACCESS,
                    text="PREV",
                    enabled=prev_enabled,
                    h_align="left",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=16,
                    flash_until_ms=1 if context.is_osb_flashing("L5") else 0,
                ),
            ),
            (
                "R5",
                ButtonState(
                    button_id="ICAWS_R5",
                    button_type=ButtonType.PAGE_ACCESS,
                    text="NEXT",
                    enabled=next_enabled,
                    h_align="right",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=16,
                    flash_until_ms=1 if context.is_osb_flashing("R5") else 0,
                ),
            ),
            (
                "T3",
                ButtonState(
                    button_id="ICAWS_T3",
                    button_type=ButtonType.MOMENTARY_SINGLE,
                    text="TEST\nICAWS",
                    is_single_function=True,
                    is_on=test_held,
                    h_align="center",
                    v_align="center",
                    padding=OSB_PADDING,
                    font_size=14,
                    flash_until_ms=1 if context.is_osb_flashing("T3") else 0,
                ),
            ),
        ]
        now_ms = int(pygame.time.get_ticks())
        for label, state in osbs:
            box = self._osb_box(rect, label)
            if box is None:
                continue
            render_button(surface, box, state, get_font, now_ms)

        # Standalone page indicator directly above PREV (not bound to L4 cell rendering).
        l5_box = self._osb_box(rect, "L5")
        if l5_box is not None:
            pfont = get_font(16)
            page_surf = pfont.render(page_text, True, (0, 255, 0))
            prev_ref = pfont.render("PREV", True, (0, 255, 255))
            prev_rect = prev_ref.get_rect()
            prev_rect.left = l5_box.left + OSB_PADDING
            prev_rect.centery = l5_box.centery
            page_rect = page_surf.get_rect()
            page_rect.left = prev_rect.left
            # One text line above PREV.
            page_rect.bottom = prev_rect.top - 1
            surface.blit(page_surf, page_rect)

    def render(self, surface, rect, is_primary: bool, context: FormatContext) -> None:
        prev_clip = surface.get_clip()
        surface.set_clip(rect)
        pygame.draw.rect(surface, (0, 255, 255), rect, 1)
        test_held = self._update_test_hold(rect, is_primary)
        if is_primary:
            self._draw_inc_dec_symbols(surface, rect)

        if not is_primary:
            all_alerts = get_current_icaws_alerts()
            unacked_raw = ICAWS_STATE.get("unacked_cw", [])
            if isinstance(unacked_raw, list):
                unacked_cw = {str(x) for x in unacked_raw}
            else:
                unacked_cw = set()

            indexed_alerts = list(enumerate(all_alerts))

            def _sev_rank(sev: str) -> int:
                if sev == "warning":
                    return 0
                if sev == "caution":
                    return 1
                return 2

            def _priority(item: Tuple[int, Tuple[str, str]]) -> Tuple[int, int, int]:
                idx, (txt, sev) = item
                alert_key = f"{txt}|{sev}"
                needs_ack = sev in {"warning", "caution"}
                unacked_rank = 0 if (needs_ack and alert_key in unacked_cw) else 1
                return (_sev_rank(sev), unacked_rank, idx)

            # 7-row single-column layout: top 6 alerts + bottom "ICAWS" label row.
            prioritized = [a for _, a in sorted(indexed_alerts, key=_priority)[:6]]

            content = rect.inflate(-2, -2)
            if content.width > 0 and content.height > 0:
                rows = 7
                font = get_font(12)
                for row_idx in range(rows - 1):
                    row_top = content.top + (row_idx * content.height) // rows
                    row_bottom = content.top + ((row_idx + 1) * content.height) // rows
                    row_rect = pygame.Rect(
                        content.left,
                        row_top,
                        max(1, content.width),
                        max(1, row_bottom - row_top),
                    )
                    if row_idx >= len(prioritized):
                        continue
                    txt, sev = prioritized[row_idx]
                    alert_key = f"{txt}|{sev}"
                    if sev == "warning":
                        bg, fg = (255, 0, 0), (255, 255, 255)
                    elif sev == "caution":
                        if alert_key in unacked_cw:
                            bg, fg = (255, 255, 0), (0, 0, 0)
                        else:
                            bg, fg = (0, 0, 0), (255, 255, 0)
                    else:
                        bg, fg = (0, 0, 0), (0, 255, 0)
                    pygame.draw.rect(surface, bg, row_rect)
                    t = font.render(txt, True, fg)
                    tr = t.get_rect(centerx=row_rect.centerx, centery=row_rect.centery)
                    surface.blit(t, tr)

                # Bottom label row.
                label_top = content.top + ((rows - 1) * content.height) // rows
                label_bottom = content.top + (rows * content.height) // rows
                label_rect = pygame.Rect(
                    content.left,
                    label_top,
                    max(1, content.width),
                    max(1, label_bottom - label_top),
                )
                pygame.draw.rect(surface, (0, 0, 0), label_rect)
                label = font.render("ICAWS", True, (0, 255, 255))
                lr = label.get_rect(centerx=label_rect.centerx, centery=label_rect.centery)
                surface.blit(label, lr)
            surface.set_clip(prev_clip)
            return

        alerts = get_current_icaws_alerts()
        unacked_raw = ICAWS_STATE.get("unacked_cw", [])
        if isinstance(unacked_raw, list):
            unacked_cw = {str(x) for x in unacked_raw}
        else:
            unacked_cw = set()
        content_left = rect.left + GRID_CELL_W + 2
        content_top = rect.top + GRID_CELL_H + 2
        content_right = rect.right - GRID_CELL_W - 2
        content_bottom = rect.bottom - GRID_CELL_H - 2
        content_rect = pygame.Rect(content_left, content_top, max(1, content_right - content_left), max(1, content_bottom - content_top))
        surface.set_clip(content_rect)

        font = get_font(16)
        row_h = font.get_height() + 2
        max_rows = max(1, content_rect.height // row_h)
        selected_idx = self._set_selected_index(self._state_int("selected_idx", 0), len(alerts))
        scroll_idx = self._state_int("selected_scroll", 0)
        if len(alerts) <= max_rows:
            scroll_idx = 0
        else:
            max_scroll = max(0, len(alerts) - max_rows)
            scroll_idx = max(0, min(max_scroll, scroll_idx))
            if selected_idx < scroll_idx:
                scroll_idx = selected_idx
            elif selected_idx >= scroll_idx + max_rows:
                scroll_idx = selected_idx - max_rows + 1
            scroll_idx = max(0, min(max_scroll, scroll_idx))
        self._set_state_int("selected_scroll", scroll_idx)

        selected_key = ""
        linked_reasons: List[str] = []
        if len(alerts) > 0:
            sel_text, sel_sev = alerts[selected_idx]
            selected_key = f"{sel_text}|{sel_sev}"
            linked_reasons = self._linked_reasons_for_alert(sel_text, sel_sev)
        if selected_key != self._state_str("selected_alert_key", ""):
            self._scoped_state()["selected_alert_key"] = selected_key
            ICAWS_STATE["selected_alert_key"] = selected_key
            self._set_state_int("reason_page_idx", 0)

        reason_page_size = 10
        reason_total_pages = (
            max(1, int(math.ceil(len(linked_reasons) / float(reason_page_size))))
            if len(linked_reasons) > 0
            else 1
        )
        reason_page_idx = self._state_int("reason_page_idx", 0)
        reason_page_idx = max(0, min(reason_total_pages - 1, reason_page_idx))
        self._set_state_int("reason_page_idx", reason_page_idx)

        reason_font = get_font(14)
        reason_line_h = reason_font.get_height() + 1
        desired_reason_h = (reason_line_h * reason_page_size) + 6
        alerts_rect = content_rect.copy()
        reasons_rect: Optional[pygame.Rect] = None
        if len(linked_reasons) > 0:
            # Keep linked HRC/FnA text in the lower area (near L5/R5), like before.
            l5_box = self._osb_box(rect, "L5")
            preferred_reason_top = content_rect.top
            if l5_box is not None:
                preferred_reason_top = max(content_rect.top, min(content_rect.bottom - 1, l5_box.top))
            reason_max_h = max(0, content_rect.bottom - preferred_reason_top)
            reason_h = max(0, min(desired_reason_h, reason_max_h))
            if reason_h > 0:
                reasons_rect = pygame.Rect(content_rect.left, preferred_reason_top, content_rect.width, reason_h)
                alerts_bottom = max(content_rect.top + 1, reasons_rect.top - 4)
                alerts_rect = pygame.Rect(
                    content_rect.left,
                    content_rect.top,
                    content_rect.width,
                    max(1, alerts_bottom - content_rect.top),
                )

        max_rows = max(1, alerts_rect.height // row_h)
        if len(alerts) <= max_rows:
            scroll_idx = 0
        else:
            max_scroll = max(0, len(alerts) - max_rows)
            scroll_idx = max(0, min(max_scroll, scroll_idx))
            if selected_idx < scroll_idx:
                scroll_idx = selected_idx
            elif selected_idx >= scroll_idx + max_rows:
                scroll_idx = selected_idx - max_rows + 1
            scroll_idx = max(0, min(max_scroll, scroll_idx))
        self._set_state_int("selected_scroll", scroll_idx)

        reason_start = reason_page_idx * reason_page_size
        reason_end = reason_start + reason_page_size
        reason_items = linked_reasons[reason_start:reason_end]

        y = alerts_rect.top
        for draw_idx in range(scroll_idx, min(len(alerts), scroll_idx + max_rows)):
            text, sev = alerts[draw_idx]
            if y + row_h > alerts_rect.bottom:
                break
            alert_key = f"{text}|{sev}"
            if sev == "warning":
                color = (255, 0, 0)
            elif sev == "caution":
                color = (255, 255, 0)
            else:
                color = (0, 255, 0)
            highlighted_unacked = (sev == "warning") or (alert_key in unacked_cw and sev == "caution")
            text_color = (255, 255, 255) if sev == "warning" else ((0, 0, 0) if highlighted_unacked else color)
            s = font.render(text, True, text_color)
            text_x = alerts_rect.left + 14
            s_rect = s.get_rect(x=text_x, y=y)
            if highlighted_unacked:
                pygame.draw.rect(surface, color, s_rect.inflate(4, 2))
            surface.blit(s, s_rect)
            if draw_idx == selected_idx:
                star = font.render("*", True, (255, 255, 255))
                star_rect = star.get_rect()
                star_rect.left = alerts_rect.left + 1
                star_rect.centery = s_rect.centery
                surface.blit(star, star_rect)
            y += row_h

        if reasons_rect is not None:
            old_clip = surface.get_clip()
            surface.set_clip(reasons_rect)
            ry = reasons_rect.top + 2
            for reason in reason_items:
                if ry + reason_line_h > reasons_rect.bottom:
                    break
                line_s = reason_font.render(str(reason), True, (255, 255, 0))
                line_r = line_s.get_rect(x=reasons_rect.left + 4, y=ry)
                surface.blit(line_s, line_r)
                ry += reason_line_h
            surface.set_clip(old_clip)

        surface.set_clip(prev_clip)

        page_text = f"{reason_page_idx + 1:02d}/{reason_total_pages:02d}"
        prev_enabled = len(linked_reasons) > 0 and reason_page_idx > 0
        next_enabled = len(linked_reasons) > 0 and reason_page_idx < (reason_total_pages - 1)
        self._draw_primary_buttons(surface, rect, context, prev_enabled, next_enabled, test_held, page_text)

    def on_osb(self, label: str, context: FormatContext) -> bool:
        if label == "T1":
            context.request_vded(context.portal_index, "MENU")
            return True
        alerts = get_current_icaws_alerts()
        alert_count = len(alerts)
        selected_idx = self._set_selected_index(self._state_int("selected_idx", 0), alert_count)
        if label == "L1":
            self._set_selected_index(selected_idx - 1, alert_count)
            self._set_state_int("reason_page_idx", 0)
            return True
        if label == "L2":
            self._set_selected_index(selected_idx + 1, alert_count)
            self._set_state_int("reason_page_idx", 0)
            return True
        if label == "T3":
            try:
                ICAWS_STATE["test_active_until_ms"] = int(pygame.time.get_ticks()) + 250
            except Exception:
                ICAWS_STATE["test_active_until_ms"] = 250
            return True
        linked_reasons: List[str] = []
        if alert_count > 0:
            sel_text, sel_sev = alerts[selected_idx]
            linked_reasons = self._linked_reasons_for_alert(sel_text, sel_sev)
        reason_page_size = 10
        total_pages = (
            max(1, int(math.ceil(len(linked_reasons) / float(reason_page_size))))
            if len(linked_reasons) > 0
            else 1
        )
        max_idx = max(0, total_pages - 1)
        page_idx = max(0, min(max_idx, self._state_int("reason_page_idx", 0)))
        if label == "L5":
            if len(linked_reasons) <= 0 or page_idx <= 0:
                return True
            self._set_state_int("reason_page_idx", page_idx - 1)
            return True
        if label == "R5":
            if len(linked_reasons) <= 0 or page_idx >= max_idx:
                return True
            self._set_state_int("reason_page_idx", page_idx + 1)
            return True
        return False
