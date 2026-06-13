from formats import *  # noqa: F401,F403


class WindFormat(FormatBase):
    name: str = "WIND"
    _FLASH_MS: int = 250

    def _state(self) -> Dict[str, object]:
        _wind_init_state()
        return WIND_STATE

    def _selected_field(self) -> str:
        token = str(self._state().get("selected_field", "")).upper().strip()
        if token in {"TZ", "DATE", "TIME"}:
            return token
        return ""

    def _set_selected_field(self, token: str) -> None:
        t = str(token).upper().strip()
        self._state()["selected_field"] = t if t in {"TZ", "DATE", "TIME"} else ""

    def _entry_buffer(self) -> str:
        return str(self._state().get("entry_buffer", ""))

    def _set_entry_buffer(self, value: str) -> None:
        self._state()["entry_buffer"] = str(value)

    def _display_mode(self) -> str:
        mode = str(self._state().get("display_mode", "LOCAL")).upper().strip()
        return "ZULU" if mode == "ZULU" else "LOCAL"

    def _set_display_mode(self, mode: str) -> None:
        self._state()["display_mode"] = "ZULU" if str(mode).upper().strip() == "ZULU" else "LOCAL"

    def _display_datetime(self) -> datetime:
        local_dt, zulu_dt = _wind_local_and_zulu_datetimes()
        return local_dt if self._display_mode() == "LOCAL" else zulu_dt

    def _format_stopwatch(self) -> str:
        total = int(max(0.0, _wind_stopwatch_elapsed_s()))
        hh = total // 3600
        mm = (total % 3600) // 60
        ss = total % 60
        return f"{hh:02d}:{mm:02d}:{ss:02d}"

    def _trigger_flash(self, key: str) -> None:
        state = self._state()
        flash = state.get("flash_until", {})
        if not isinstance(flash, dict):
            flash = {}
        try:
            flash[str(key).upper().strip()] = int(pygame.time.get_ticks()) + int(self._FLASH_MS)
        except Exception:
            flash[str(key).upper().strip()] = int(self._FLASH_MS)
        state["flash_until"] = flash

    @staticmethod
    def _cell_rect(rect: pygame.Rect, cell_name: str) -> pygame.Rect:
        cols = 5
        rows = 8
        cell_w = max(1, rect.width // cols)
        cell_h = max(1, rect.height // rows)
        col = ord(cell_name[0].upper()) - ord("A")
        row = int(cell_name[1:]) - 1
        return pygame.Rect(rect.x + col * cell_w, rect.y + row * cell_h, cell_w, cell_h)

    def _hit_cell(self, pos: Tuple[int, int], rect: pygame.Rect) -> str:
        cols = 5
        rows = 8
        cell_w = max(1, rect.width // cols)
        cell_h = max(1, rect.height // rows)
        rel_x = pos[0] - rect.x
        rel_y = pos[1] - rect.y
        if rel_x < 0 or rel_y < 0 or rel_x >= rect.width or rel_y >= rect.height:
            return ""
        col = max(0, min(cols - 1, rel_x // cell_w))
        row = max(0, min(rows - 1, rel_y // cell_h))
        if row == 0 and col in {1, 2}:
            return "BC1"
        if row == 0 and col in {3, 4}:
            return "DE1"
        if row == 2 and col in {3, 4}:
            return "DE3"
        return f"{chr(ord('A') + int(col))}{int(row) + 1}"

    def _scratch_date(self, raw: str) -> str:
        digits = "".join(ch for ch in str(raw) if ch.isdigit())[:8]
        slots = list("________")
        for i, ch in enumerate(digits):
            slots[i] = ch
        return f"{slots[0]}{slots[1]}{slots[2]}{slots[3]}/{slots[4]}{slots[5]}/{slots[6]}{slots[7]} \u2190"

    def _scratch_time(self, raw: str) -> str:
        digits = "".join(ch for ch in str(raw) if ch.isdigit())[:6]
        slots = list("______")
        for i, ch in enumerate(digits):
            slots[i] = ch
        return f"{slots[0]}{slots[1]}:{slots[2]}{slots[3]}:{slots[4]}{slots[5]} \u2190"

    def _scratch_tz(self, raw: str) -> str:
        digits = "".join(ch for ch in str(raw) if ch.isdigit())[:4]
        slots = list("____")
        for i, ch in enumerate(digits):
            slots[i] = ch
        sign = "-" if str(raw).strip().startswith("-") else ""
        return f"{sign}{slots[0]}{slots[1]}{slots[2]}.{slots[3]} \u2190"

    def _commit_selected_entry(self) -> None:
        state = self._state()
        selected = self._selected_field()
        raw = self._entry_buffer().strip()
        mode = self._display_mode()
        tz_off = float(state.get("tz_offset_hours", 0.0))
        if selected == "TZ":
            if raw != "":
                explicit_sign = -1 if raw.startswith("-") else (1 if raw.startswith("+") else 0)
                value_abs: Optional[float] = None
                if "." in raw:
                    try:
                        value_abs = abs(float(raw))
                    except Exception:
                        value_abs = None
                else:
                    digits = "".join(ch for ch in raw if ch.isdigit())
                    if digits != "":
                        try:
                            # Left-to-right TZ entry for ___._:
                            # 3 -> 3.0, 35 -> 35.0, 357 -> 357.0, 3574 -> 357.4
                            d = digits[:4]
                            if len(d) >= 4:
                                value_abs = float(int(d[:3])) + (float(int(d[3])) / 10.0)
                            else:
                                value_abs = float(int(d))
                        except Exception:
                            value_abs = None
                if value_abs is not None:
                    sign = -1.0 if tz_off < 0.0 else 1.0
                    if explicit_sign < 0:
                        sign = -1.0
                    elif explicit_sign > 0:
                        sign = 1.0
                    state["tz_offset_hours"] = max(-14.0, min(14.0, sign * float(value_abs)))
        elif selected in {"DATE", "TIME"}:
            display_now = self._display_datetime()
            digits = "".join(ch for ch in raw if ch.isdigit())
            try:
                if selected == "DATE" and len(digits) == 8:
                    year = int(digits[0:4])
                    month = int(digits[4:6])
                    day = int(digits[6:8])
                    new_display = datetime(
                        year,
                        month,
                        day,
                        display_now.hour,
                        display_now.minute,
                        display_now.second,
                        tzinfo=timezone.utc,
                    )
                    utc_ts = float(new_display.timestamp())
                    if mode == "LOCAL":
                        utc_ts -= tz_off * 3600.0
                    _wind_set_utc_ts(utc_ts)
                elif selected == "TIME" and len(digits) == 6:
                    hour = int(digits[0:2])
                    minute = int(digits[2:4])
                    second = int(digits[4:6])
                    new_display = datetime(
                        display_now.year,
                        display_now.month,
                        display_now.day,
                        hour,
                        minute,
                        second,
                        tzinfo=timezone.utc,
                    )
                    utc_ts = float(new_display.timestamp())
                    if mode == "LOCAL":
                        utc_ts -= tz_off * 3600.0
                    _wind_set_utc_ts(utc_ts)
            except Exception:
                pass
        self._set_selected_field("")
        self._set_entry_buffer("")

    def _select_entry_field(self, token: str) -> None:
        selected = self._selected_field()
        target = str(token).upper().strip()
        if target not in {"TZ", "DATE", "TIME"}:
            return
        if selected == target:
            self._commit_selected_entry()
            return
        if selected != "":
            self._commit_selected_entry()
        self._set_selected_field(target)
        self._set_entry_buffer("")

    def _apply_keypad_token(self, token: str) -> None:
        selected = self._selected_field()
        if selected == "":
            return
        tok_raw = str(token).strip()
        tok = tok_raw.upper()
        raw = self._entry_buffer()
        max_len = 8 if selected == "DATE" else (6 if selected == "TIME" else 4)
        if tok in {"BACK", "KP_BACK", "BACKSPACE"}:
            self._set_entry_buffer(raw[:-1])
            return
        if tok in {"NEG0", "-0"}:
            if raw == "":
                self._set_entry_buffer("-")
                return
            tok = "0"
        if len(tok) == 1 and tok.isdigit():
            digits = "".join(ch for ch in raw if ch.isdigit())
            if len(digits) >= max_len:
                return
            self._set_entry_buffer(raw + tok)

    def render(self, surface, rect, is_primary: bool, context: FormatContext) -> None:
        if not is_primary:
            draw_centered_text(surface, rect, "WIND", "00FFFF", 14)
            return

        state = self._state()
        cyan = (0, 255, 255)
        green = (0, 255, 0)
        white = (255, 255, 255)
        gray = (128, 128, 128)
        now_ms = int(pygame.time.get_ticks())
        flash_until = state.get("flash_until", {})
        if not isinstance(flash_until, dict):
            flash_until = {}
        mode = self._display_mode()
        selected = self._selected_field()
        raw = self._entry_buffer()
        display_dt = self._display_datetime()
        date_text = display_dt.strftime("%Y/%m/%d")
        time_text = display_dt.strftime("%H:%M:%S")
        tz_off = float(state.get("tz_offset_hours", 0.0))
        stopwatch_text = self._format_stopwatch()

        cols = 5
        rows = 8
        cell_w = max(1, rect.width // cols)
        cell_h = max(1, rect.height // rows)

        def draw_line_bottom(
            box: pygame.Rect,
            line_no: int,
            text: str,
            color: Tuple[int, int, int],
            *,
            size: int = 16,
            box_selected: bool = False,
            align: str = "center",
            x_pad: int = 4,
            flash_key: Optional[str] = None,
        ) -> pygame.Rect:
            font = get_font(size)
            y3 = box.bottom - font.get_height() - 2
            y2 = y3 - font.get_height() - 1
            y1 = y2 - font.get_height() - 1
            y = y1 if line_no <= 1 else y2 if line_no == 2 else y3
            flashing = False
            if flash_key is not None:
                try:
                    flashing = int(flash_until.get(str(flash_key).upper().strip(), 0)) > int(now_ms)
                except Exception:
                    flashing = False
            draw_color = white if flashing else color
            surf = font.render(str(text), True, draw_color)
            if align == "left":
                srect = surf.get_rect(left=box.left + x_pad)
            elif align == "right":
                srect = surf.get_rect(right=box.right - x_pad)
            else:
                srect = surf.get_rect(centerx=box.centerx)
            srect.y = y
            if box_selected or flashing:
                pygame.draw.rect(surface, white, srect.inflate(4, 2), 1)
            surface.blit(surf, srect)
            return srect

        pygame.draw.rect(surface, cyan, rect, 1)
        x1 = rect.x + cell_w
        x2 = rect.x + 2 * cell_w
        x3 = rect.x + 3 * cell_w
        x4 = rect.x + 4 * cell_w
        pygame.draw.line(surface, cyan, (x1, rect.top), (x1, rect.bottom), 1)
        pygame.draw.line(surface, cyan, (x2, rect.top + cell_h), (x2, rect.bottom), 1)  # skip B/C split on row 1
        pygame.draw.line(surface, cyan, (x3, rect.top), (x3, rect.bottom), 1)
        pygame.draw.line(surface, cyan, (x4, rect.top + cell_h), (x4, rect.top + 2 * cell_h), 1)  # skip D/E row 1
        pygame.draw.line(surface, cyan, (x4, rect.top + 3 * cell_h), (x4, rect.bottom), 1)  # skip D/E row 3
        for j in range(1, rows):
            y = rect.y + j * cell_h
            pygame.draw.line(surface, cyan, (rect.left, y), (rect.right, y), 1)

        a1 = self._cell_rect(rect, "A1")
        bc1 = self._cell_rect(rect, "B1").union(self._cell_rect(rect, "C1"))
        de1 = self._cell_rect(rect, "D1").union(self._cell_rect(rect, "E1"))
        a2 = self._cell_rect(rect, "A2")
        b2 = self._cell_rect(rect, "B2")
        e2 = self._cell_rect(rect, "E2")
        de3 = self._cell_rect(rect, "D3").union(self._cell_rect(rect, "E3"))
        d5 = self._cell_rect(rect, "D5")
        e4 = self._cell_rect(rect, "E4")
        e5 = self._cell_rect(rect, "E5")

        if selected == "TZ":
            draw_line_bottom(a1, 1, self._scratch_tz(raw), white, box_selected=True)
        draw_line_bottom(a1, 2, "TZ", cyan)
        draw_line_bottom(a1, 3, f"{tz_off:.1f}", cyan)

        if selected == "DATE":
            draw_line_bottom(bc1, 1, self._scratch_date(raw), white, box_selected=True)
        draw_line_bottom(bc1, 2, "YYYY/MM/DD", cyan)
        draw_line_bottom(bc1, 3, date_text, cyan)

        if selected == "TIME":
            draw_line_bottom(de1, 1, self._scratch_time(raw), white, box_selected=True)
        draw_line_bottom(de1, 2, "HH:MM:SS", cyan)
        draw_line_bottom(de1, 3, time_text, cyan)

        draw_line_bottom(a2, 2, "USE OTA", cyan)
        draw_line_bottom(a2, 3, "TOD", cyan)

        b2_head = draw_line_bottom(b2, 2, "COM", green)
        pygame.draw.line(surface, green, (b2_head.left, b2_head.bottom + 1), (b2_head.right, b2_head.bottom + 1), 1)

        local_selected = mode == "LOCAL"
        zulu_selected = mode == "ZULU"
        draw_line_bottom(e2, 2, "LOCAL", white if local_selected else cyan, box_selected=local_selected)
        draw_line_bottom(e2, 3, "ZULU", white if zulu_selected else cyan, box_selected=zulu_selected)

        stopwatch_color = green if _wind_stopwatch_is_visible() else gray
        draw_line_bottom(de3, 2, "STOPWATCH", stopwatch_color)
        draw_line_bottom(de3, 3, stopwatch_text, stopwatch_color)

        draw_line_bottom(e4, 2, "START", cyan, flash_key="E4")
        draw_line_bottom(e5, 2, "STOP", cyan, flash_key="E5")
        draw_line_bottom(d5, 2, "RESET", cyan, flash_key="D5")

        keypad_labels = {
            "A4": "1",
            "B4": "2",
            "C4": "3",
            "A5": "4",
            "B5": "5",
            "C5": "6",
            "A6": "7",
            "B6": "8",
            "C6": "9",
            "A7": "",
            "B7": "-0",
            "C7": "BACK",
        }
        font = get_font(16)
        flash_until = state.get("flash_until", {})
        if not isinstance(flash_until, dict):
            flash_until = {}
        now_ms = int(pygame.time.get_ticks())
        for cell_name, text in keypad_labels.items():
            if text == "":
                continue
            box = self._cell_rect(rect, cell_name)
            flashing = int(flash_until.get(f"KP_{cell_name}", 0) or 0) > now_ms
            surf = font.render(text, True, (0, 0, 0) if flashing else cyan)
            srect = surf.get_rect(center=box.center)
            if flashing:
                pygame.draw.rect(surface, white, srect.inflate(6, 3), 0)
            surface.blit(surf, srect)

    def on_click(self, pos: Tuple[int, int], rect: pygame.Rect, context: FormatContext) -> bool:
        if not rect.collidepoint(pos):
            return False
        state = self._state()
        cell = self._hit_cell(pos, rect)
        if cell == "":
            return True

        keypad_map = {
            "A4": "1",
            "B4": "2",
            "C4": "3",
            "A5": "4",
            "B5": "5",
            "C5": "6",
            "A6": "7",
            "B6": "8",
            "C6": "9",
            "B7": "NEG0",
            "C7": "BACK",
        }

        if cell in keypad_map:
            self._trigger_flash(f"KP_{cell}")
            self._apply_keypad_token(keypad_map[cell])
            return True

        if cell == "A1":
            self._select_entry_field("TZ")
            return True
        if cell == "BC1":
            self._select_entry_field("DATE")
            return True
        if cell == "DE1":
            self._select_entry_field("TIME")
            return True

        if self._selected_field() != "":
            self._commit_selected_entry()

        if cell == "A2":
            _wind_sync_ota_time()
            return True
        if cell == "E2":
            self._set_display_mode("LOCAL" if self._display_mode() == "ZULU" else "ZULU")
            return True
        if cell == "E4":
            self._trigger_flash("E4")
            if not bool(state.get("stopwatch_running", False)):
                state["stopwatch_running"] = True
                state["stopwatch_anchor_mono"] = float(time.monotonic())
            return True
        if cell == "E5":
            self._trigger_flash("E5")
            if bool(state.get("stopwatch_running", False)):
                anchor = float(state.get("stopwatch_anchor_mono", time.monotonic()))
                elapsed = float(state.get("stopwatch_elapsed_s", 0.0))
                state["stopwatch_elapsed_s"] = max(0.0, elapsed + (float(time.monotonic()) - anchor))
                state["stopwatch_running"] = False
            return True
        if cell == "D5":
            self._trigger_flash("D5")
            state["stopwatch_elapsed_s"] = 0.0
            state["stopwatch_running"] = False
            state["stopwatch_anchor_mono"] = float(time.monotonic())
            return True
        if cell == "B2":
            # Reserved GOL behavior.
            return True
        return True

    def on_osb(self, label: str, context: FormatContext) -> bool:
        if label == "T1":
            context.request_vded(context.portal_index, "MENU")
            return True
        return False

    def on_key(self, key: str) -> bool:
        selected = self._selected_field()
        if selected == "":
            return False
        raw = str(key).strip()
        if raw == "":
            return False
        upper = raw.upper()
        if upper in {"ENTER", "RETURN", "KP_ENTER"}:
            self._commit_selected_entry()
            return True
        if upper in {"KP_BACK", "BACKSPACE", "BACK"}:
            self._apply_keypad_token("BACK")
            return True
        if upper in {"KP_MINUS", "MINUS"} or raw == "-":
            self._apply_keypad_token("NEG0")
            return True
        if upper.startswith("KP_") and len(upper) == 4 and upper[3].isdigit():
            self._apply_keypad_token(upper[3])
            return True
        if len(raw) == 1 and raw.isdigit():
            self._apply_keypad_token(raw)
            return True
        return False
