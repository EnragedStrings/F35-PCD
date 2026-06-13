from formats import *  # noqa: F401,F403


class DimFormat(FormatBase):
    name: str = "DIM"

    _OWN_ROWS: List[Tuple[str, str, str, str, str]] = [
        ("1120Z", "L", "DS01", "ATK", "DSTRY"),
        ("1040Z", "V", "SLAP", "CAS", "HAVCO"),
        ("1030Z", "V", "SLAP", "CAS", "PARTL"),
        ("1015Z", "V", "SLAP", "CAS", "DSTRY"),
    ]
    _FLT_ROWS: List[Tuple[str, str, str, str, str]] = [
        ("1132Z", "L", "DS01", "ATK", "REPLY"),
        ("1130Z", "V", "DS01", "ATK", "ACTIV"),
        ("1128Z", "L", "DS01", "ATK", "CANTCO"),
        ("1125Z", "L", "DS01", "ATK", "ACTIV"),
        ("1120Z", "L", "DS01", "ATK", "DSTRY"),
        ("1108Z", "L", "DS01", "ATK", "PARTL"),
        ("1106Z", "L", "DS01", "ATK", "CNTCO"),
        ("1101Z", "L", "DS01", "ATK", "DSTRY"),
        ("1013Z", "L", "", "RTB", "CNTCO"),
        ("0942Z", "L", "", "ORBIT", "CNX"),
    ]
    _BDA_ROWS: List[Tuple[str, str, str, str, str]] = [
        ("1132Z", "V", "SLAP", "", "DSTRY"),
        ("1128Z", "V", "SLAP", "", "UNKWN"),
    ]

    def __init__(self) -> None:
        self._t2_idx: int = 0  # 0=INBOX, 1=OUTBOX
        self._selected_row_idx: int = 0

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

    def _entry_count(self) -> int:
        return len(self._OWN_ROWS) + len(self._FLT_ROWS) + len(self._BDA_ROWS)

    def _clamp_selected(self) -> None:
        total = self._entry_count()
        if total <= 0:
            self._selected_row_idx = 0
            return
        self._selected_row_idx = max(0, min(total - 1, int(self._selected_row_idx)))

    def _draw_inc_dec_symbols(self, surface: pygame.Surface, rect: pygame.Rect, context: FormatContext) -> None:
        cyan = (0, 255, 255)
        white = (255, 255, 255)
        l1 = self._osb_box(rect, "L1")
        l2 = self._osb_box(rect, "L2")
        if l1 is not None:
            tri_w = max(10, l1.width // 3)
            tri_h = max(10, l1.height // 3)
            cx = l1.left + OSB_PADDING + tri_w // 2 + 2
            cy = l1.centery
            up = [(cx, cy - tri_h // 2), (cx - tri_w // 2, cy + tri_h // 2), (cx + tri_w // 2, cy + tri_h // 2)]
            flashing = bool(context.is_osb_flashing("L1"))
            if flashing:
                # Keep highlight constrained to the symbol area only.
                pygame.draw.polygon(surface, white, up, 0)
            pygame.draw.polygon(surface, (0, 0, 0) if flashing else cyan, up, 1 if flashing else 0)
        if l2 is not None:
            tri_w = max(10, l2.width // 3)
            tri_h = max(10, l2.height // 3)
            cx = l2.left + OSB_PADDING + tri_w // 2 + 2
            cy = l2.centery
            down = [(cx, cy + tri_h // 2), (cx - tri_w // 2, cy - tri_h // 2), (cx + tri_w // 2, cy - tri_h // 2)]
            flashing = bool(context.is_osb_flashing("L2"))
            if flashing:
                # Keep highlight constrained to the symbol area only.
                pygame.draw.polygon(surface, white, down, 0)
            pygame.draw.polygon(surface, (0, 0, 0) if flashing else cyan, down, 1 if flashing else 0)

    def _draw_osbs(self, surface: pygame.Surface, rect: pygame.Rect, context: FormatContext) -> None:
        now_ms = int(pygame.time.get_ticks())
        t2 = self._osb_box(rect, "T2")
        if t2 is not None:
            t2_state = ButtonState(
                button_id="DIM_T2",
                button_type=ButtonType.DOUBLE_FUNCTION,
                options=["INBOX", "OUTBOX"],
                selected_index=max(0, min(1, int(self._t2_idx))),
                h_align="center",
                v_align="top",
                padding=OSB_PADDING,
                font_size=14,
                flash_until_ms=1 if context.is_osb_flashing("T2") else 0,
            )
            render_button(surface, t2, t2_state, get_font, now_ms)

        self._draw_inc_dec_symbols(surface, rect, context)

        page_access_labels: List[Tuple[str, str, str, str]] = [
            ("L3", "VIEW>", "left", "center"),
            ("L4", "DELETE", "left", "center"),
            ("L5", "<PREV\nPAGE", "left", "center"),
            ("R1", "ASGN\nSELF", "right", "center"),
            ("R3", "REPORT>", "right", "center"),
            ("R4", "L16", "right", "center"),
            ("R5", "NEXT\nPAGE>", "right", "center"),
        ]
        for label, text, h_align, v_align in page_access_labels:
            box = self._osb_box(rect, label)
            if box is None:
                continue
            bs = ButtonState(
                button_id=f"DIM_{label}",
                button_type=ButtonType.PAGE_ACCESS,
                text=text,
                h_align=h_align,
                v_align=v_align,
                padding=OSB_PADDING,
                font_size=14,
                flash_until_ms=1 if context.is_osb_flashing(label) else 0,
            )
            render_button(surface, box, bs, get_font, now_ms)

    def render(self, surface, rect, is_primary: bool, context: FormatContext) -> None:
        prev_clip = surface.get_clip()
        surface.set_clip(rect)
        surface.fill((0, 0, 0), rect)

        if not is_primary:
            dim_font = get_font(14)
            dim_surf = dim_font.render("DIM", True, (0, 255, 255))
            dim_rect = dim_surf.get_rect(centerx=rect.centerx, bottom=rect.bottom - 2)
            surface.blit(dim_surf, dim_rect)
            pygame.draw.rect(surface, (0, 255, 255), rect, 1)
            surface.set_clip(prev_clip)
            return

        self._clamp_selected()
        self._draw_osbs(surface, rect, context)

        content_left = rect.left + GRID_CELL_W + 8
        content_top = rect.top + GRID_CELL_H + 4
        content_right = rect.right - GRID_CELL_W - 8
        content_bottom = rect.bottom - GRID_CELL_H - 4
        content_rect = pygame.Rect(content_left, content_top, max(1, content_right - content_left), max(1, content_bottom - content_top))
        surface.set_clip(content_rect)

        green = (0, 255, 0)
        cyan = (0, 255, 255)
        white = (255, 255, 255)
        header_font = get_font(14)
        row_font = get_font(13)
        page_font = get_font(14)
        row_h = row_font.get_height() + 2
        sec_gap = 5
        extra_flt_to_bda_gap = row_h * 2
        page_text = "1/1"
        page_h = page_font.get_height()
        content_bottom_limit = content_rect.bottom - page_h - 4

        cw = row_font.size("0")[0]
        x_time = content_rect.left + max(6, cw)
        x_lv = x_time + (6 * cw)
        x_unit = x_time + (8 * cw)
        x_task = x_time + (13 * cw)
        x_res = x_time + (20 * cw)

        selectable_idx = 0
        y = content_rect.top + 2
        sections: List[Tuple[str, List[Tuple[str, str, str, str, str]]]] = [
            ("MSN ASSIGN - OWN - CTOTAL", self._OWN_ROWS),
            ("MSN ASSIGN - FLT - CTOTAL", self._FLT_ROWS),
            ("BDA - /DL", self._BDA_ROWS),
        ]

        for sec_idx, (header, rows) in enumerate(sections):
            hs = header_font.render(header, True, green)
            hr = hs.get_rect(left=x_time, y=y)
            surface.blit(hs, hr)
            pygame.draw.line(surface, green, (hr.left, hr.bottom + 1), (hr.right, hr.bottom + 1), 1)
            y = hr.bottom + 4

            for time_txt, lv_txt, unit_txt, task_txt, res_txt in rows:
                selected = selectable_idx == self._selected_row_idx
                col = white if selected else cyan
                if selected:
                    dot_x = x_time - max(5, cw // 2)
                    dot_y = y + row_font.get_height() // 2
                    pygame.draw.circle(surface, white, (dot_x, dot_y), max(2, cw // 4), 0)

                if time_txt != "":
                    surface.blit(row_font.render(time_txt, True, col), (x_time, y))
                if lv_txt != "":
                    surface.blit(row_font.render(lv_txt, True, col), (x_lv, y))
                if unit_txt != "":
                    surface.blit(row_font.render(unit_txt, True, col), (x_unit, y))
                if task_txt != "":
                    surface.blit(row_font.render(task_txt, True, col), (x_task, y))
                if res_txt != "":
                    surface.blit(row_font.render(res_txt, True, col), (x_res, y))

                selectable_idx += 1
                y += row_h
                if y + row_h > content_bottom_limit:
                    break
            y += sec_gap
            if sec_idx == 1:
                y += extra_flt_to_bda_gap
            if y + row_h > content_bottom_limit:
                break

        page_surface = page_font.render(page_text, True, green)
        page_rect = page_surface.get_rect(centerx=content_rect.centerx, bottom=content_rect.bottom - 1)
        surface.blit(page_surface, page_rect)

        surface.set_clip(prev_clip)
        pygame.draw.rect(surface, (0, 255, 255), rect, 1)

    def on_osb(self, label: str, context: FormatContext) -> bool:
        if label == "T1":
            context.request_vded(context.portal_index, "MENU")
            return True
        if label == "T2":
            self._t2_idx = 1 if int(self._t2_idx) == 0 else 0
            return True
        if label == "L1":
            self._selected_row_idx -= 1
            self._clamp_selected()
            return True
        if label == "L2":
            self._selected_row_idx += 1
            self._clamp_selected()
            return True
        if label in {"L3", "L4", "L5", "R1", "R3", "R4", "R5"}:
            return True
        return False

    def osb_is_interactive(self, label: str) -> bool:
        return label in {"T1", "T2", "L1", "L2", "L3", "L4", "L5", "R1", "R3", "R4", "R5"}


class DimV2Format(DimFormat):
    _MODE_INBOX = 0
    _MODE_OUTBOX = 1
    _shared_inbox_image_count: int = 0
    _shared_mission_store: Dict[str, Dict[str, object]] = {}
    _shared_inbox_own_ids: List[str] = []
    _shared_inbox_flt_ids: List[str] = []
    _shared_outbox_ids: List[str] = []
    _shared_mission_seq: int = 0
    _shared_image_data: Dict[str, Dict[str, object]] = {}

    def __init__(self) -> None:
        super().__init__()
        self._t2_idx = self._MODE_INBOX
        self._outbox_new_open = False
        self._header_selected_field = ""
        self._header_input_by_field: Dict[str, str] = {"time": "", "target": "", "msn_type": ""}
        self._header_value_by_field: Dict[str, str] = {"time": self._zulu_hhmmz(), "target": "", "msn_type": ""}
        self._slot_order: List[str] = [
            "msn", "acft", "tac", "tac_sub", "el", "wpn", "knwn_last",
            "ip_lat_h", "ip_lat_deg", "ip_lat_min", "ip_lat_frac",
            "ip_lon_h", "ip_lon_deg", "ip_lon_min", "ip_lon_frac",
            "hdg", "rng_whole", "rng_frac", "elev", "desc", "stat",
            "tgt_lat_h", "tgt_lat_deg", "tgt_lat_min", "tgt_lat_frac",
            "tgt_lon_h", "tgt_lon_deg", "tgt_lon_min", "tgt_lon_frac",
            "lsr", "card", "frnd_num", "frnd_code", "frnd_alpha", "egrs_a", "egrs_b",
        ]
        self._slot_specs: Dict[str, Tuple[str, int, Optional[List[str]]]] = {
            "msn": ("alnum", 4, None),
            "acft": ("alnum", 16, None),
            "tac": ("alnum", 16, None),
            "tac_sub": ("alpha", 16, None),
            "el": ("numeric", 4, None),
            "wpn": ("alpha", 16, None),
            "knwn_last": ("alpha", 16, None),
            "ip_lat_h": ("alpha", 1, ["N", "S"]),
            "ip_lat_deg": ("numeric", 3, None),
            "ip_lat_min": ("numeric", 2, None),
            "ip_lat_frac": ("numeric", 4, None),
            "ip_lon_h": ("alpha", 1, ["E", "W"]),
            "ip_lon_deg": ("numeric", 3, None),
            "ip_lon_min": ("numeric", 2, None),
            "ip_lon_frac": ("numeric", 4, None),
            "hdg": ("numeric", 3, None),
            "rng_whole": ("numeric", 1, None),
            "rng_frac": ("numeric", 1, None),
            "elev": ("numeric", 4, None),
            "desc": ("alnum", 20, None),
            "stat": ("alpha", 20, None),
            "tgt_lat_h": ("alpha", 1, ["N", "S"]),
            "tgt_lat_deg": ("numeric", 3, None),
            "tgt_lat_min": ("numeric", 2, None),
            "tgt_lat_frac": ("numeric", 4, None),
            "tgt_lon_h": ("alpha", 1, ["E", "W"]),
            "tgt_lon_deg": ("numeric", 3, None),
            "tgt_lon_min": ("numeric", 2, None),
            "tgt_lon_frac": ("numeric", 4, None),
            "lsr": ("numeric", 4, None),
            "card": ("numeric", 4, None),
            "frnd_num": ("numeric", 1, None),
            "frnd_code": ("alnum", 4, None),
            "frnd_alpha": ("alpha", 1, None),
            "egrs_a": ("alpha", 1, None),
            "egrs_b": ("alpha", 1, None),
        }
        self._slot_values: Dict[str, str] = {k: "" for k in self._slot_order}
        self._selected_slot_idx = 0
        self._slot_edit_active = False
        self._slot_edit_field = ""
        self._slot_edit_prev_value = ""
        self._slot_edit_buffer = ""
        self._keypad_visible = False
        self._keypad_target = ""
        self._keypad_field = ""
        self._keypad_mode = "numeric"
        self._cycle_cell = ""
        self._cycle_idx = 0
        self._cycle_until_ms = 0
        self._new_image_paths: List[str] = []
        self._new_image_page_idx: int = 0
        self._new_image_cache: Dict[str, pygame.Surface] = {}
        self._inbox_view_open: bool = False
        self._inbox_view_kind: str = ""
        self._inbox_view_mission_id: str = ""
        self._inbox_view_image_path: str = ""
        self._pending_nav_action: Optional[Tuple[str, int]] = None

    @staticmethod
    def _zulu_hhmmz() -> str:
        try:
            return datetime.now(timezone.utc).strftime("%H%M") + "Z"
        except Exception:
            return "0000Z"

    @staticmethod
    def _parse_zulu_to_minutes(time_token: str) -> int:
        token = str(time_token).strip().upper()
        if token.endswith("Z"):
            token = token[:-1]
        if len(token) != 4 or (not token.isdigit()):
            return -1
        try:
            hh = int(token[:2])
            mm = int(token[2:])
        except Exception:
            return -1
        if hh < 0 or hh > 23 or mm < 0 or mm > 59:
            return -1
        return hh * 60 + mm

    @classmethod
    def _next_mission_id(cls) -> str:
        max_seq = 0
        try:
            max_seq = int(cls._shared_mission_seq)
        except Exception:
            max_seq = 0
        try:
            if isinstance(cls._shared_mission_store, dict):
                for raw in cls._shared_mission_store.values():
                    if not isinstance(raw, dict):
                        continue
                    try:
                        seq = int(raw.get("seq", 0))
                    except Exception:
                        seq = 0
                    if seq > max_seq:
                        max_seq = seq
        except Exception:
            pass
        cls._shared_mission_seq = int(max_seq) + 1
        uniq = str(uuid.uuid4().hex[:6]).upper()
        return f"M{int(cls._shared_mission_seq):06d}_{uniq}"

    @classmethod
    def _mission_sort_key(cls, mission: Dict[str, object]) -> Tuple[int, int]:
        mins = cls._parse_zulu_to_minutes(str(mission.get("time", "")))
        try:
            seq = int(mission.get("seq", 0))
        except Exception:
            seq = 0
        return (mins, seq)

    @staticmethod
    def _mission_is_deleted(mission: object) -> bool:
        if not isinstance(mission, dict):
            return False
        raw = mission.get("deleted", False)
        if isinstance(raw, bool):
            return raw
        txt = str(raw).strip().lower()
        return txt in {"1", "true", "yes", "y", "on"}

    @staticmethod
    def _mission_mark_updated(mission: object) -> int:
        if not isinstance(mission, dict):
            return int(time.time() * 1000)
        now_ms = int(time.time() * 1000)
        prev_ms = 0
        try:
            prev_ms = int(mission.get("updated_unix_ms", 0) or 0)
        except Exception:
            prev_ms = 0
        if now_ms <= prev_ms:
            now_ms = prev_ms + 1
        mission["updated_unix_ms"] = int(now_ms)
        return int(now_ms)

    @classmethod
    def _refresh_shared_image_count(cls) -> None:
        count = 0
        for mission in cls._shared_mission_store.values():
            if cls._mission_is_deleted(mission):
                continue
            imgs = mission.get("images", [])
            if isinstance(imgs, list):
                for raw in imgs:
                    if str(raw).strip() != "":
                        count += 1
        cls._shared_inbox_image_count = max(0, int(count))

    @classmethod
    def _sorted_missions_for_ids(cls, mission_ids: List[str]) -> List[Dict[str, object]]:
        rows: List[Dict[str, object]] = []
        seen: set = set()
        for raw_mid in mission_ids:
            mid = str(raw_mid).strip()
            if mid == "" or mid in seen:
                continue
            seen.add(mid)
            mission = cls._shared_mission_store.get(mid)
            if isinstance(mission, dict) and (not cls._mission_is_deleted(mission)):
                rows.append(mission)
        rows.sort(key=cls._mission_sort_key, reverse=True)
        return rows

    def _inbox_own_rows(self) -> List[Dict[str, object]]:
        return self._sorted_missions_for_ids(type(self)._shared_inbox_own_ids)

    def _inbox_flt_rows(self) -> List[Dict[str, object]]:
        return self._sorted_missions_for_ids(type(self)._shared_inbox_flt_ids)

    def _outbox_rows(self) -> List[Dict[str, object]]:
        return self._sorted_missions_for_ids(type(self)._shared_outbox_ids)

    def _entry_count(self) -> int:
        if int(self._t2_idx) != self._MODE_INBOX:
            return 0
        return len(self._inbox_own_rows()) + len(self._inbox_flt_rows()) + len(self._inbox_image_rows())

    def _inbox_image_rows(self) -> List[Dict[str, object]]:
        rows: List[Dict[str, object]] = []
        seen: set = set()
        all_missions: List[Dict[str, object]] = []
        for mission in type(self)._shared_mission_store.values():
            if isinstance(mission, dict):
                if type(self)._mission_is_deleted(mission):
                    continue
                all_missions.append(mission)
        all_missions.sort(key=self._mission_sort_key, reverse=True)
        for mission in all_missions:
            imgs = mission.get("images", [])
            if not isinstance(imgs, list):
                continue
            for idx, raw_path in enumerate(imgs):
                img_path = str(raw_path).strip()
                if img_path == "":
                    continue
                key = (str(mission.get("id", "")), img_path)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(
                    {
                        "mission_id": str(mission.get("id", "")).strip(),
                        "time": str(mission.get("time", "")).strip().upper(),
                        "msn_type": str(mission.get("msn_type", "")).strip().upper(),
                        "image_path": img_path,
                        "img_idx": int(idx),
                    }
                )
        rows.sort(
            key=lambda entry: (
                self._parse_zulu_to_minutes(str(entry.get("time", ""))),
                int(entry.get("img_idx", 0)),
            ),
            reverse=True,
        )
        return rows

    def _selected_inbox_mission_ref(self) -> Tuple[str, Optional[Dict[str, object]]]:
        own_rows = self._inbox_own_rows()
        flt_rows = self._inbox_flt_rows()
        idx = int(self._selected_row_idx)
        if idx < 0:
            return ("", None)
        if idx < len(own_rows):
            return ("OWN", own_rows[idx])
        idx -= len(own_rows)
        if idx < len(flt_rows):
            return ("FLT", flt_rows[idx])
        return ("", None)

    def _selected_inbox_entry(self) -> Tuple[str, Optional[Dict[str, object]]]:
        own_rows = self._inbox_own_rows()
        flt_rows = self._inbox_flt_rows()
        image_rows = self._inbox_image_rows()
        idx = int(self._selected_row_idx)
        if idx < 0:
            return ("", None)
        if idx < len(own_rows):
            return ("OWN", own_rows[idx])
        idx -= len(own_rows)
        if idx < len(flt_rows):
            return ("FLT", flt_rows[idx])
        idx -= len(flt_rows)
        if idx < len(image_rows):
            return ("IMAGE", image_rows[idx])
        return ("", None)

    def _send_ready(self) -> bool:
        time_val = str(self._header_value_by_field.get("time", "")).strip().upper()
        target_val = str(self._header_value_by_field.get("target", "")).strip().upper()
        msn_type_val = str(self._header_value_by_field.get("msn_type", "")).strip().upper()
        return (
            self._parse_zulu_to_minutes(time_val) >= 0
            and target_val != ""
            and msn_type_val != ""
        )

    def _new_total_pages(self) -> int:
        return 1 + len(self._new_image_paths)

    def _new_page_can_prev(self) -> bool:
        return int(self._new_image_page_idx) > 0

    def _new_page_can_next(self) -> bool:
        return int(self._new_image_page_idx) < (self._new_total_pages() - 1)

    def _new_page_is_image(self) -> bool:
        return int(self._new_image_page_idx) > 0

    def _current_new_image_path(self) -> str:
        if not self._new_page_is_image():
            return ""
        idx = int(self._new_image_page_idx) - 1
        if idx < 0 or idx >= len(self._new_image_paths):
            return ""
        return str(self._new_image_paths[idx])

    @classmethod
    def _shared_image_entry(cls, token: str) -> Optional[Dict[str, object]]:
        key = str(token).strip()
        if key == "":
            return None
        raw = cls._shared_image_data.get(key)
        if isinstance(raw, dict):
            return raw
        return None

    def _surface_from_image_token(self, token: str) -> Optional[pygame.Surface]:
        key = str(token).strip()
        if key == "":
            return None
        cached = self._new_image_cache.get(key)
        if cached is not None:
            return cached
        entry = type(self)._shared_image_entry(key)
        if isinstance(entry, dict):
            b64 = str(entry.get("data_b64", "")).strip()
            if b64 == "":
                b64 = str(entry.get("data", entry.get("b64", ""))).strip()
            if b64 != "":
                if "," in b64 and b64.lower().startswith("data:"):
                    b64 = b64.split(",", 1)[1].strip()
                try:
                    raw = base64.b64decode(b64, validate=False)
                    surf = pygame.image.load(io.BytesIO(raw)).convert_alpha()
                    self._new_image_cache[key] = surf
                    return surf
                except Exception:
                    pass
            else:
                try:
                    print(f"[DIM][IMG_VIEW_WAIT] token={key} has_manifest_no_data")
                except Exception:
                    pass
        try:
            surf = pygame.image.load(key).convert_alpha()
            self._new_image_cache[key] = surf
            return surf
        except Exception:
            return None

    def _current_new_image_surface(self) -> Optional[pygame.Surface]:
        img_path = self._current_new_image_path()
        if img_path == "":
            return None
        return self._surface_from_image_token(img_path)

    def _attach_image_file_dialog(self) -> Optional[str]:
        try:
            import tkinter as tk  # type: ignore
            from tkinter import filedialog  # type: ignore
        except Exception:
            return None
        recordings_dir = writable_path("Recordings")
        try:
            recordings_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        chosen = ""
        root = None
        try:
            root = tk.Tk()
            root.withdraw()
            try:
                root.attributes("-topmost", True)
            except Exception:
                pass
            chosen = str(
                filedialog.askopenfilename(
                    title="Attach Mission Image",
                    initialdir=str(recordings_dir),
                    filetypes=[("PNG Image", "*.png"), ("All Files", "*.*")],
                )
            ).strip()
        except Exception:
            chosen = ""
        finally:
            try:
                if root is not None:
                    root.destroy()
            except Exception:
                pass
        if chosen == "":
            return None
        path = Path(chosen)
        if (not path.exists()) or path.suffix.lower() != ".png":
            return None
        try:
            return str(path.resolve())
        except Exception:
            return str(path)

    def _attach_new_image(self) -> None:
        chosen = self._attach_image_file_dialog()
        if chosen is None or chosen == "":
            return
        raw_bytes: bytes = b""
        try:
            raw_bytes = Path(chosen).read_bytes()
        except Exception:
            raw_bytes = b""
        if len(raw_bytes) <= 0:
            return
        try:
            img = pygame.image.load(io.BytesIO(raw_bytes)).convert_alpha()
        except Exception:
            return
        token = f"DLIMG_{uuid.uuid4().hex[:12].upper()}"
        type(self)._shared_image_data[token] = {
            "mime": "image/png",
            "data_b64": base64.b64encode(raw_bytes).decode("ascii"),
            "bytes": int(len(raw_bytes)),
            "name": str(Path(chosen).name),
        }
        self._new_image_cache[token] = img
        self._new_image_paths.append(token)
        self._new_image_page_idx = len(self._new_image_paths)

    def _delete_current_new_image(self) -> None:
        if not self._new_page_is_image():
            return
        idx = int(self._new_image_page_idx) - 1
        if idx < 0 or idx >= len(self._new_image_paths):
            return
        removed = str(self._new_image_paths.pop(idx))
        self._new_image_cache.pop(removed, None)
        if len(self._new_image_paths) <= 0:
            self._new_image_page_idx = 0
            return
        self._new_image_page_idx = max(1, min(int(self._new_image_page_idx), len(self._new_image_paths)))

    def _normalize_header_values(self) -> None:
        for field in ("time", "target", "msn_type"):
            if self._header_selected_field == field:
                self._header_commit(field)
        self._header_selected_field = ""
        self._keypad_close()

    def _create_and_send_mission(self) -> bool:
        self._normalize_header_values()
        if not self._send_ready():
            return False
        mission_id = self._next_mission_id()
        now_ms = int(time.time() * 1000)
        time_val = str(self._header_value_by_field.get("time", "")).strip().upper()
        if self._parse_zulu_to_minutes(time_val) < 0:
            time_val = self._zulu_hhmmz()
        target_val = str(self._header_value_by_field.get("target", "")).strip().upper()
        msn_type_val = str(self._header_value_by_field.get("msn_type", "")).strip().upper()
        mission: Dict[str, object] = {
            "id": mission_id,
            "seq": int(type(self)._shared_mission_seq),
            "time": time_val,
            "local": "V",
            "target": target_val,
            "msn_type": msn_type_val,
            "status": "REPLY",
            "images": [str(p) for p in self._new_image_paths if str(p).strip() != ""],
            "slots": {k: str(v) for k, v in self._slot_values.items()},
            "deleted": False,
            "created_unix_ms": int(now_ms),
            "updated_unix_ms": int(now_ms),
        }
        type(self)._shared_mission_store[mission_id] = mission
        if mission_id not in type(self)._shared_inbox_flt_ids:
            type(self)._shared_inbox_flt_ids.append(mission_id)
        if mission_id not in type(self)._shared_outbox_ids:
            type(self)._shared_outbox_ids.append(mission_id)
        type(self)._refresh_shared_image_count()
        self._outbox_new_open = False
        self._reset_outbox_new_entry()
        self._clamp_selected()
        return True

    def _toggle_inbox_assign(self) -> None:
        section, mission = self._selected_inbox_mission_ref()
        if mission is None:
            return
        mission_id = str(mission.get("id", "")).strip()
        if mission_id == "":
            return
        if section == "OWN":
            type(self)._shared_inbox_own_ids = [mid for mid in type(self)._shared_inbox_own_ids if str(mid) != mission_id]
        elif section == "FLT":
            if mission_id not in type(self)._shared_inbox_own_ids:
                type(self)._shared_inbox_own_ids.append(mission_id)
        self._clamp_selected()

    def _delete_selected_inbox_entry(self) -> None:
        entry_kind, payload = self._selected_inbox_entry()
        if payload is None:
            return
        if entry_kind in {"OWN", "FLT"}:
            mission_id = str(payload.get("id", "")).strip()
            if mission_id == "":
                return
            mission = type(self)._shared_mission_store.get(mission_id)
            if isinstance(mission, dict):
                mission["deleted"] = True
                mark_ms = type(self)._mission_mark_updated(mission)
                mission["deleted_unix_ms"] = int(mark_ms)
            type(self)._shared_inbox_own_ids = [mid for mid in type(self)._shared_inbox_own_ids if str(mid) != mission_id]
            type(self)._shared_inbox_flt_ids = [mid for mid in type(self)._shared_inbox_flt_ids if str(mid) != mission_id]
            type(self)._shared_outbox_ids = [mid for mid in type(self)._shared_outbox_ids if str(mid) != mission_id]
            type(self)._refresh_shared_image_count()
            if self._inbox_view_open and self._inbox_view_kind == "MISSION" and self._inbox_view_mission_id == mission_id:
                self._close_inbox_view()
            self._clamp_selected()
            return
        if entry_kind == "IMAGE":
            mission_id = str(payload.get("mission_id", "")).strip()
            image_path = str(payload.get("image_path", "")).strip()
            if mission_id == "" or image_path == "":
                return
            mission = type(self)._shared_mission_store.get(mission_id)
            if not isinstance(mission, dict):
                return
            imgs = mission.get("images", [])
            if not isinstance(imgs, list):
                return
            removed = False
            new_imgs: List[str] = []
            for raw in imgs:
                token = str(raw).strip()
                if (not removed) and token == image_path:
                    removed = True
                    continue
                new_imgs.append(token)
            mission["images"] = new_imgs
            type(self)._mission_mark_updated(mission)
            type(self)._refresh_shared_image_count()
            if self._inbox_view_open and self._inbox_view_kind == "IMAGE" and self._inbox_view_image_path == image_path:
                self._close_inbox_view()
            self._clamp_selected()

    def _report_enabled_for_selected(self) -> bool:
        entry_kind, payload = self._selected_inbox_entry()
        if payload is None or entry_kind == "IMAGE":
            return False
        status = str(payload.get("status", "")).strip().upper()
        return status != "REPLY"

    def _inbox_view_mission(self) -> Optional[Dict[str, object]]:
        if (not self._inbox_view_open) or self._inbox_view_kind != "MISSION":
            return None
        mission = type(self)._shared_mission_store.get(self._inbox_view_mission_id)
        if isinstance(mission, dict):
            return mission
        return None

    @staticmethod
    def _mission_response_blocked(status: str) -> set:
        state = str(status).strip().upper()
        if state == "REPLY":
            return set()
        if state == "WILCO":
            return {"WILCO", "CANTCO"}
        if state == "CANTCO":
            return {"WILCO", "CANTCO", "HAVECO"}
        if state == "HAVECO":
            return {"WILCO", "CANTCO", "HAVECO"}
        return set()

    def _response_button_enabled(self, response: str) -> bool:
        mission = self._inbox_view_mission()
        if mission is None:
            return False
        status = str(mission.get("status", "REPLY")).strip().upper()
        blocked = self._mission_response_blocked(status)
        return str(response).strip().upper() not in blocked

    def _set_mission_response(self, response: str) -> bool:
        mission = self._inbox_view_mission()
        if mission is None:
            return False
        if type(self)._mission_is_deleted(mission):
            return False
        resp = str(response).strip().upper()
        if resp not in {"WILCO", "CANTCO", "HAVECO"}:
            return False
        if not self._response_button_enabled(resp):
            return True
        mission["status"] = resp
        type(self)._mission_mark_updated(mission)
        return True

    @staticmethod
    def _header_next_field(field: str) -> str:
        token = str(field).strip().lower()
        if token == "time":
            return "target"
        if token == "target":
            return "msn_type"
        return ""

    def _slot_maybe_auto_advance(self, slot: str) -> None:
        if (not self._slot_edit_active) or str(slot) != str(self._slot_edit_field):
            return
        spec = self._slot_specs.get(slot)
        if spec is None:
            return
        _mode, width, _choices = spec
        width = max(1, int(width))
        # Unlimited/free-form fields use Enter to advance; bounded fields auto-advance.
        if width > 4:
            return
        current = str(self._slot_edit_buffer)
        if len(current) < width:
            return
        self._slot_set(slot, current)
        self._slot_move(1)

    def _close_inbox_view(self) -> None:
        self._inbox_view_open = False
        self._inbox_view_kind = ""
        self._inbox_view_mission_id = ""
        self._inbox_view_image_path = ""

    def _open_selected_inbox_view(self) -> None:
        entry_kind, payload = self._selected_inbox_entry()
        if payload is None:
            self._close_inbox_view()
            return
        if entry_kind in {"OWN", "FLT"}:
            mission_id = str(payload.get("id", "")).strip()
            if mission_id == "":
                self._close_inbox_view()
                return
            self._inbox_view_open = True
            self._inbox_view_kind = "MISSION"
            self._inbox_view_mission_id = mission_id
            self._inbox_view_image_path = ""
            return
        if entry_kind == "IMAGE":
            image_path = str(payload.get("image_path", "")).strip()
            if image_path == "":
                self._close_inbox_view()
                return
            self._inbox_view_open = True
            self._inbox_view_kind = "IMAGE"
            self._inbox_view_mission_id = str(payload.get("mission_id", "")).strip()
            self._inbox_view_image_path = image_path
            return
        self._close_inbox_view()

    def _mission_image_tokens(self, mission_id: str) -> List[str]:
        mid = str(mission_id).strip()
        if mid == "":
            return []
        mission = type(self)._shared_mission_store.get(mid)
        if not isinstance(mission, dict):
            return []
        imgs = mission.get("images", [])
        if not isinstance(imgs, list):
            return []
        out: List[str] = []
        for raw in imgs:
            token = str(raw).strip()
            if token == "":
                continue
            out.append(token)
        return out

    def _inbox_view_next_page(self) -> bool:
        if (not self._inbox_view_open) or int(self._t2_idx) != self._MODE_INBOX:
            return False
        if self._inbox_view_kind == "MISSION":
            imgs = self._mission_image_tokens(self._inbox_view_mission_id)
            if len(imgs) <= 0:
                return False
            self._inbox_view_kind = "IMAGE"
            self._inbox_view_image_path = str(imgs[0])
            return True
        if self._inbox_view_kind == "IMAGE":
            imgs = self._mission_image_tokens(self._inbox_view_mission_id)
            if len(imgs) <= 0:
                return False
            cur = str(self._inbox_view_image_path).strip()
            try:
                idx = imgs.index(cur)
            except Exception:
                idx = -1
            if idx < 0:
                self._inbox_view_image_path = str(imgs[0])
                return True
            if idx < (len(imgs) - 1):
                self._inbox_view_image_path = str(imgs[idx + 1])
                return True
            return False
        return False

    def _inbox_view_prev_page(self) -> bool:
        if (not self._inbox_view_open) or int(self._t2_idx) != self._MODE_INBOX:
            return False
        if self._inbox_view_kind == "IMAGE":
            imgs = self._mission_image_tokens(self._inbox_view_mission_id)
            if len(imgs) <= 0:
                return False
            cur = str(self._inbox_view_image_path).strip()
            try:
                idx = imgs.index(cur)
            except Exception:
                idx = -1
            if idx > 0:
                self._inbox_view_image_path = str(imgs[idx - 1])
                return True
            self._inbox_view_kind = "MISSION"
            self._inbox_view_image_path = ""
            return True
        return False

    def _queue_nav_action(self, token: str, delay_ms: int = 220) -> None:
        try:
            now_ms = int(pygame.time.get_ticks())
        except Exception:
            now_ms = 0
        self._pending_nav_action = (str(token).upper().strip(), int(now_ms) + max(1, int(delay_ms)))

    def _run_pending_nav_action(self) -> None:
        pending = self._pending_nav_action
        if not isinstance(pending, tuple) or len(pending) != 2:
            return
        token = str(pending[0]).upper().strip()
        try:
            due_ms = int(pending[1])
        except Exception:
            due_ms = 0
        try:
            now_ms = int(pygame.time.get_ticks())
        except Exception:
            now_ms = 0
        if now_ms < due_ms:
            return
        self._pending_nav_action = None
        if self._outbox_new_open or int(self._t2_idx) != self._MODE_INBOX:
            return
        if token == "L3":
            if self._inbox_view_open:
                self._close_inbox_view()
            else:
                self._open_selected_inbox_view()
            return
        if token == "L5":
            if self._inbox_view_open:
                self._inbox_view_prev_page()
            return
        if token == "R5":
            if self._inbox_view_open:
                self._inbox_view_next_page()
            return

    def _render_mission_view(self, surface: pygame.Surface, content_rect: pygame.Rect, mission: Dict[str, object]) -> None:
        header_font = get_font(13)
        green = (0, 255, 0)
        cyan = (0, 255, 255)
        hdr = header_font.render(
            f"{str(mission.get('time', '')).strip().upper()} {str(mission.get('target', '')).strip().upper()} {str(mission.get('msn_type', '')).strip().upper()}",
            True,
            green,
        )
        hrect = hdr.get_rect(left=content_rect.left + 8, y=content_rect.top + 2)
        surface.blit(hdr, hrect)
        pygame.draw.line(surface, green, (hrect.left, hrect.bottom + 1), (hrect.right, hrect.bottom + 1), 1)

        slots_raw = mission.get("slots", {})
        slot_values: Dict[str, str] = {}
        if isinstance(slots_raw, dict):
            for slot_id in self._slot_order:
                slot_values[slot_id] = str(slots_raw.get(slot_id, ""))
        else:
            for slot_id in self._slot_order:
                slot_values[slot_id] = ""

        font = get_font(10)
        row_h = font.get_height() + 1
        x0 = content_rect.left + 8
        y = hrect.bottom + 4

        def slot_fmt(slot: str, width: int) -> str:
            raw = str(slot_values.get(slot, ""))
            return (raw + ("_" * width))[:width]

        def slot_var(slot: str) -> str:
            raw = str(slot_values.get(slot, ""))
            return raw if raw != "" else "_"

        def draw_text(x: int, yy: int, text: str, color: Tuple[int, int, int]) -> int:
            surf = font.render(text, True, color)
            rr = surf.get_rect(x=x, y=yy)
            surface.blit(surf, rr)
            return int(rr.right)

        def line(parts: List[Tuple[str, str, Tuple[int, int, int]]]) -> None:
            nonlocal y
            x = x0
            for kind, text, color in parts:
                if kind == "text":
                    x = draw_text(x, y, text, color)
                else:
                    x = draw_text(x, y, text, cyan)
            y += row_h

        line([("text", "MSN ", green), ("slot", slot_fmt("msn", 4), cyan), ("text", "  MC ", green), ("text", "/2N", cyan)])
        line([("text", "ACFT ", green), ("slot", slot_var("acft"), cyan)])
        line([("text", "TAC ", green), ("slot", slot_var("tac"), cyan)])
        line([("text", "    ", green), ("slot", slot_var("tac_sub"), cyan), ("text", " EL ", green), ("slot", slot_fmt("el", 4), cyan)])
        line([("text", "WPN ", green), ("slot", slot_var("wpn"), cyan)])
        line([("text", "KNWN LAST ", green), ("slot", slot_var("knwn_last"), cyan)])
        y += row_h
        line([("text", "1 IP", green)])
        line([("text", "  LAT ", green), ("slot", slot_fmt("ip_lat_h", 1), cyan), ("text", " ", cyan), ("slot", slot_fmt("ip_lat_deg", 3), cyan), ("text", "\u00b0", cyan), ("slot", slot_fmt("ip_lat_min", 2), cyan), ("text", ".", cyan), ("slot", slot_fmt("ip_lat_frac", 4), cyan)])
        line([("text", "  LONG ", green), ("slot", slot_fmt("ip_lon_h", 1), cyan), ("text", " ", cyan), ("slot", slot_fmt("ip_lon_deg", 3), cyan), ("text", "\u00b0", cyan), ("slot", slot_fmt("ip_lon_min", 2), cyan), ("text", ".", cyan), ("slot", slot_fmt("ip_lon_frac", 4), cyan)])
        line([("text", "2 HDG ", green), ("slot", slot_fmt("hdg", 3), cyan), ("text", "\u00b0  OFFSET", green)])
        line([("text", "3 RNG ", green), ("slot", slot_fmt("rng_whole", 1), cyan), ("text", ".", cyan), ("slot", slot_fmt("rng_frac", 1), cyan), ("text", " NM", green)])
        line([("text", "4 ELEV ", green), ("slot", slot_fmt("elev", 4), cyan), ("text", " FT", green)])
        line([("text", "5 DESC ", green), ("slot", slot_var("desc"), cyan)])
        y += row_h
        line([("text", "  FREQ/IAS SETTING", green)])
        y += row_h
        line([("text", "  STAT ", green), ("slot", slot_var("stat"), cyan)])
        line([("text", "6 TGT INFO", green)])
        line([("text", "  C/B SN", green)])
        line([("text", "  LAT ", green), ("slot", slot_fmt("tgt_lat_h", 1), cyan), ("text", " ", cyan), ("slot", slot_fmt("tgt_lat_deg", 3), cyan), ("text", "\u00b0", cyan), ("slot", slot_fmt("tgt_lat_min", 2), cyan), ("text", ".", cyan), ("slot", slot_fmt("tgt_lat_frac", 4), cyan)])
        line([("text", "  LONG ", green), ("slot", slot_fmt("tgt_lon_h", 1), cyan), ("text", " ", cyan), ("slot", slot_fmt("tgt_lon_deg", 3), cyan), ("text", "\u00b0", cyan), ("slot", slot_fmt("tgt_lon_min", 2), cyan), ("text", ".", cyan), ("slot", slot_fmt("tgt_lon_frac", 4), cyan)])
        line([("text", "  LSR ", green), ("slot", slot_fmt("lsr", 4), cyan)])
        line([("text", "  MAPNG", green)])
        line([("text", "7 MARK", green)])
        y += row_h
        line([("text", "  CARD ", green), ("slot", slot_fmt("card", 4), cyan), ("text", " SN-279", green)])
        line([("text", "8 FRND ", green), ("slot", slot_fmt("frnd_num", 1), cyan), ("text", " ", cyan), ("slot", slot_fmt("frnd_code", 4), cyan), ("text", " ", cyan), ("slot", slot_fmt("frnd_alpha", 1), cyan)])
        line([("text", "9 EGRS ", green), ("slot", slot_fmt("egrs_a", 1), cyan), ("text", " ", cyan), ("slot", slot_fmt("egrs_b", 1), cyan)])

    def _render_inbox_view(self, surface: pygame.Surface, content_rect: pygame.Rect) -> None:
        if self._inbox_view_kind == "IMAGE":
            img_path = str(self._inbox_view_image_path).strip()
            if img_path == "":
                font = get_font(14)
                msg = font.render("NO IMAGE TOKEN", True, (255, 255, 255))
                surface.blit(msg, msg.get_rect(center=content_rect.center))
                return
            img = self._surface_from_image_token(img_path)
            if img is None:
                font = get_font(14)
                msg = font.render("IMAGE DATA PENDING", True, (255, 255, 255))
                tok = get_font(12).render(img_path[:28], True, (0, 255, 255))
                r1 = msg.get_rect(center=content_rect.center)
                r2 = tok.get_rect(centerx=content_rect.centerx, top=r1.bottom + 4)
                surface.blit(msg, r1)
                surface.blit(tok, r2)
                return
            iw = max(1, int(img.get_width()))
            ih = max(1, int(img.get_height()))
            scale = min(content_rect.width / float(iw), content_rect.height / float(ih))
            scale = max(0.01, scale)
            tw = max(1, int(iw * scale))
            th = max(1, int(ih * scale))
            try:
                scaled = pygame.transform.smoothscale(img, (tw, th))
            except Exception:
                scaled = pygame.transform.scale(img, (tw, th))
            dst = scaled.get_rect(center=content_rect.center)
            surface.blit(scaled, dst)
            return
        if self._inbox_view_kind == "MISSION":
            mission = type(self)._shared_mission_store.get(self._inbox_view_mission_id)
            if isinstance(mission, dict):
                self._render_mission_view(surface, content_rect, mission)

    def _reset_outbox_new_entry(self) -> None:
        self._header_selected_field = ""
        self._header_input_by_field["time"] = ""
        self._header_input_by_field["target"] = ""
        self._header_input_by_field["msn_type"] = ""
        self._header_value_by_field["time"] = self._zulu_hhmmz()
        self._header_value_by_field["target"] = ""
        self._header_value_by_field["msn_type"] = ""
        for slot_id in self._slot_order:
            self._slot_values[slot_id] = ""
        self._selected_slot_idx = 0
        self._slot_edit_active = False
        self._slot_edit_field = ""
        self._slot_edit_prev_value = ""
        self._slot_edit_buffer = ""
        self._new_image_paths = []
        self._new_image_page_idx = 0
        self._new_image_cache = {}
        self._keypad_close()

    @staticmethod
    def _grid_rect(rect: pygame.Rect) -> pygame.Rect:
        grid_w = 5 * GRID_CELL_W
        grid_h = 8 * GRID_CELL_H
        grid_x = _anchored_5col_grid_x(rect, grid_w)
        return pygame.Rect(grid_x, rect.y - SIDE_OSB_Y_SHIFT, grid_w, grid_h)

    def _popup_rect(self, rect: pygame.Rect) -> pygame.Rect:
        grid = self._grid_rect(rect)
        return pygame.Rect(grid.x + GRID_CELL_W, grid.y + GRID_CELL_H, 3 * GRID_CELL_W, 5 * GRID_CELL_H)

    def _slot_selected(self) -> str:
        if len(self._slot_order) <= 0:
            return ""
        self._selected_slot_idx = max(0, min(len(self._slot_order) - 1, int(self._selected_slot_idx)))
        return self._slot_order[self._selected_slot_idx]

    def _slot_move(self, delta: int) -> None:
        if len(self._slot_order) <= 0:
            return
        self._selected_slot_idx = (int(self._selected_slot_idx) + int(delta)) % len(self._slot_order)
        if self._slot_edit_active:
            slot = self._slot_selected()
            self._slot_edit_field = slot
            self._slot_edit_prev_value = self._slot_get(slot)
            self._slot_edit_buffer = self._slot_get(slot)
        if self._keypad_visible and self._keypad_target == "slot":
            slot = self._slot_selected()
            self._keypad_field = slot
            self._keypad_mode = self._slot_specs.get(slot, ("alnum", 4, None))[0]

    def _slot_get(self, slot: str) -> str:
        return str(self._slot_values.get(slot, ""))

    def _slot_fmt(self, slot: str, width: int) -> str:
        raw = self._slot_get(slot)
        return (raw + ("_" * width))[:width]

    def _slot_var(self, slot: str) -> str:
        raw = self._slot_get(slot)
        return raw if raw != "" else "_"

    def _sanitize(self, mode: str, value: str, width: int, choices: Optional[List[str]]) -> str:
        token = str(value).upper()
        if mode == "numeric":
            token = "".join(ch for ch in token if ch.isdigit())
        elif mode == "alpha":
            token = "".join(ch for ch in token if ch.isalpha())
        else:
            token = "".join(ch for ch in token if ch.isalpha() or ch.isdigit())
        token = token[: max(1, int(width))]
        opts = choices or []
        if len(opts) > 0:
            if token == "":
                return ""
            if token[0] not in opts:
                return ""
            token = token[0]
        return token

    def _slot_set(self, slot: str, value: str) -> None:
        if slot not in self._slot_specs:
            return
        mode, width, choices = self._slot_specs[slot]
        val = self._sanitize(mode, value, width, choices)
        if slot == "hdg" and val != "":
            try:
                val = str(max(0, min(360, int(val))))[:width]
            except Exception:
                pass
        self._slot_values[slot] = val

    def _slot_append(self, slot: str, ch: str) -> None:
        self._slot_set(slot, self._slot_get(slot) + str(ch))

    def _slot_backspace(self, slot: str) -> None:
        self._slot_set(slot, self._slot_get(slot)[:-1])

    def _header_mode(self, field: str) -> str:
        if field == "time":
            return "numeric"
        if field == "msn_type":
            return "alpha"
        return "alnum"

    def _header_width(self, field: str) -> int:
        if field == "time":
            return 4
        if field == "target":
            return 4
        if field == "msn_type":
            return 6
        return 8

    def _header_display(self, field: str) -> str:
        val = str(self._header_value_by_field.get(field, ""))
        if field == "time":
            return (val.rstrip("Z") + "____")[:4] + "Z"
        if field == "target":
            return (val + "____")[:4]
        if field == "msn_type":
            return (val + "______")[:6]
        return val

    def _header_commit(self, field: str) -> None:
        raw = str(self._header_input_by_field.get(field, "")).upper()
        if field == "time":
            raw = "".join(ch for ch in raw if ch.isdigit())[:4]
            if len(raw) == 4:
                try:
                    hh = int(raw[:2]); mm = int(raw[2:])
                    if 0 <= hh <= 23 and 0 <= mm <= 59:
                        self._header_value_by_field[field] = raw + "Z"
                except Exception:
                    pass
            return
        self._header_value_by_field[field] = self._sanitize(self._header_mode(field), raw, self._header_width(field), None)

    def _keypad_open(self, target: str, field: str, mode: str) -> None:
        self._keypad_visible = True
        self._keypad_target = target
        self._keypad_field = field
        self._keypad_mode = mode if mode in {"numeric", "alpha", "alnum"} else "alnum"
        self._cycle_cell = ""
        self._cycle_idx = 0
        self._cycle_until_ms = 0

    def _keypad_close(self) -> None:
        self._keypad_visible = False
        self._keypad_target = ""
        self._keypad_field = ""
        self._keypad_mode = "numeric"

    def _keypad_map(self) -> Dict[str, str]:
        field = str(self._keypad_field).strip().lower()
        if self._keypad_target == "slot" and field in {"ip_lat_h", "tgt_lat_h"}:
            return {
                "C2": "N",
                "C4": "S",
                "D5": "BACK",
                "B6": "LEFT",
                "C6": "RIGHT",
                "D6": ">",
            }
        if self._keypad_target == "slot" and field in {"ip_lon_h", "tgt_lon_h"}:
            return {
                "B3": "E",
                "D3": "W",
                "D5": "BACK",
                "B6": "LEFT",
                "C6": "RIGHT",
                "D6": ">",
            }
        if self._keypad_mode == "numeric":
            return {"B2": "1", "C2": "2", "D2": "3", "B3": "4", "C3": "5", "D3": "6", "B4": "7", "C4": "8", "D4": "9", "B5": "", "C5": "0", "D5": "BACK", "B6": "LEFT", "C6": "RIGHT", "D6": ">"}
        if self._keypad_mode == "alpha":
            return {"B2": "ABC", "C2": "DEF", "D2": "GHI", "B3": "JKL", "C3": "MNO", "D3": "PQR", "B4": "STU", "C4": "VWX", "D4": "YZ", "B5": "SP", "C5": "", "D5": "BACK", "B6": "LEFT", "C6": "RIGHT", "D6": ">"}
        return {"B2": "1", "C2": "2ABC", "D2": "3DEF", "B3": "4GHI", "C3": "5JKL", "D3": "6MNO", "B4": "7PQRS", "C4": "8TUV", "D4": "9WXYZ", "B5": "", "C5": "0", "D5": "BACK", "B6": "LEFT", "C6": "RIGHT", "D6": ">"}

    def _keypad_pick_char(self, cell: str, group: str) -> str:
        token = str(group)
        if token == "":
            return ""
        # Alphanumeric key groups cycle digit first, then letters.
        digits = "".join(ch for ch in token if ch.isdigit())
        letters = "".join(ch for ch in token if ch.isalpha())
        if digits != "" and letters != "":
            token = digits + letters
        now_ms = int(pygame.time.get_ticks())
        if str(cell) == str(self._cycle_cell) and now_ms <= int(self._cycle_until_ms) and len(token) > 1:
            self._cycle_idx = (int(self._cycle_idx) + 1) % len(token)
        else:
            self._cycle_cell = str(cell)
            self._cycle_idx = 0
        self._cycle_until_ms = now_ms + 1200
        return token[self._cycle_idx]

    def _keypad_apply_group_char(self, target: str, field: str, cell: str, group_token: str) -> None:
        token = str(group_token)
        if token == "":
            return
        # Build deterministic cycle order: digit first, then letters.
        digits = "".join(ch for ch in token if ch.isdigit())
        letters = "".join(ch for ch in token if ch.isalpha())
        if digits != "" and letters != "":
            token = digits + letters
        chars = list(token)
        if len(chars) <= 0:
            return
        now_ms = int(pygame.time.get_ticks())
        can_cycle_same = bool(
            str(cell) == str(self._cycle_cell)
            and now_ms <= int(self._cycle_until_ms)
            and len(chars) > 1
        )
        if can_cycle_same:
            self._cycle_idx = (int(self._cycle_idx) + 1) % len(chars)
        else:
            self._cycle_cell = str(cell)
            self._cycle_idx = 0
        self._cycle_until_ms = now_ms + 1200
        ch = chars[self._cycle_idx]
        replace_last = can_cycle_same

        if target == "header":
            if field not in {"time", "target", "msn_type"}:
                return
            mode = self._header_mode(field)
            width = self._header_width(field)
            raw = str(self._header_input_by_field.get(field, ""))
            if replace_last and len(raw) > 0:
                raw = raw[:-1] + ch
            else:
                raw = raw + ch
            self._header_input_by_field[field] = self._sanitize(mode, raw, width, None)
            return

        if target == "slot":
            if field not in self._slot_specs:
                return
            mode, width, choices = self._slot_specs[field]
            if self._slot_edit_active and field == self._slot_edit_field:
                raw = str(self._slot_edit_buffer)
                if replace_last and len(raw) > 0:
                    raw = raw[:-1] + ch
                else:
                    raw = raw + ch
                self._slot_edit_buffer = self._sanitize(mode, raw, width, choices)
                self._slot_maybe_auto_advance(field)
            else:
                raw = str(self._slot_get(field))
                if replace_last and len(raw) > 0:
                    raw = raw[:-1] + ch
                else:
                    raw = raw + ch
                self._slot_set(field, raw)
            return

    def _keypad_apply(self, cell: str, token: str) -> None:
        tok = str(token)
        target = str(self._keypad_target)
        field = str(self._keypad_field)
        if tok in {"ENT", "ENTER", "RETURN"}:
            if target == "header" and field in {"time", "target", "msn_type"}:
                self._header_commit(field)
                nxt = self._header_next_field(field)
                if nxt != "":
                    self._header_selected_field = nxt
                    self._header_input_by_field[nxt] = str(self._header_value_by_field.get(nxt, "")).rstrip("Z")
                    self._keypad_open("header", nxt, self._header_mode(nxt))
                else:
                    self._header_selected_field = ""
                    self._keypad_close()
            elif target == "slot" and field in self._slot_specs:
                if self._slot_edit_active and field == self._slot_edit_field:
                    self._slot_set(field, str(self._slot_edit_buffer))
                self._slot_move(1)
                next_slot = self._slot_selected()
                self._slot_edit_active = True
                self._slot_edit_field = next_slot
                self._slot_edit_prev_value = self._slot_get(next_slot)
                self._slot_edit_buffer = self._slot_get(next_slot)
                mode = self._slot_specs.get(next_slot, ("alnum", 4, None))[0]
                self._keypad_open("slot", next_slot, mode)
            else:
                self._keypad_close()
            return
        if tok in {"<", "LEFT"}:
            if target == "slot":
                self._slot_move(-1)
            return
        if tok == "RIGHT":
            if target == "slot":
                self._slot_move(1)
            return
        if tok == ">":
            # Advance to the next character position by resetting group-cycle state.
            self._cycle_cell = ""
            self._cycle_idx = 0
            self._cycle_until_ms = 0
            return
        if tok == "ENT":
            if target == "header" and field in {"time", "target", "msn_type"}:
                self._header_commit(field)
                self._header_selected_field = ""
            self._keypad_close()
            return
        if tok in {"BS", "BACK"}:
            if target == "header":
                self._header_input_by_field[field] = str(self._header_input_by_field.get(field, ""))[:-1]
            elif target == "slot":
                if self._slot_edit_active and field == self._slot_edit_field:
                    self._slot_edit_buffer = str(self._slot_edit_buffer)[:-1]
                else:
                    self._slot_backspace(field)
            self._cycle_cell = ""
            self._cycle_idx = 0
            self._cycle_until_ms = 0
            return
        if target == "header":
            if field not in {"time", "target", "msn_type"}:
                return
            if tok == "00":
                append = "00"
            elif tok == "SP":
                append = " "
            elif len(tok) > 1 and any(ch.isalpha() for ch in tok):
                self._keypad_apply_group_char(target, field, cell, tok)
                return
            else:
                append = tok[0]
            mode = self._header_mode(field)
            width = self._header_width(field)
            raw = str(self._header_input_by_field.get(field, "")) + append
            self._header_input_by_field[field] = self._sanitize(mode, raw, width, None)
            return
        if target == "slot":
            if field not in self._slot_specs:
                return
            mode, width, choices = self._slot_specs[field]
            if tok == "00":
                append = "00"
            elif tok == "SP":
                append = " "
            elif len(tok) > 1 and any(ch.isalpha() for ch in tok):
                self._keypad_apply_group_char(target, field, cell, tok)
                return
            else:
                append = tok[0]
            if self._slot_edit_active and field == self._slot_edit_field:
                raw = str(self._slot_edit_buffer) + str(append)
                self._slot_edit_buffer = self._sanitize(mode, raw, width, choices)
                self._slot_maybe_auto_advance(field)
            else:
                for ch in append:
                    if mode == "numeric" and (not ch.isdigit()):
                        continue
                    if mode == "alpha" and (not ch.isalpha()):
                        continue
                    if mode == "alnum" and (not (ch.isalpha() or ch.isdigit())):
                        continue
                    self._slot_append(field, ch)

    def _draw_header_btn(self, surface: pygame.Surface, box: pygame.Rect, header: str, value: str, selected: bool, flashing: bool) -> None:
        font = get_font(14)
        hdr = font.render(str(header), True, (0, 0, 0) if flashing else (0, 255, 0))
        val = font.render(str(value), True, (0, 0, 0) if flashing else (0, 255, 255))
        h_rect = hdr.get_rect(centerx=box.centerx, y=box.top + OSB_PADDING)
        v_rect = val.get_rect(centerx=box.centerx, y=h_rect.bottom + 1)
        pygame.draw.rect(surface, (0, 0, 0), h_rect.inflate(6, 2), 0)
        pygame.draw.rect(surface, (0, 0, 0), v_rect.inflate(6, 2), 0)
        if flashing:
            flash_rect = h_rect.union(v_rect).inflate(8, 4)
            pygame.draw.rect(surface, (255, 255, 255), flash_rect, 0)
        surface.blit(hdr, h_rect)
        pygame.draw.line(surface, (0, 0, 0) if flashing else (0, 255, 0), (h_rect.left, h_rect.bottom + 1), (h_rect.right, h_rect.bottom + 1), 1)
        surface.blit(val, v_rect)
        if selected:
            pygame.draw.rect(surface, (255, 255, 255), h_rect.union(v_rect).inflate(8, 4), 1)

    def _slot_display_label(self, slot: str) -> str:
        key = str(slot).strip().lower()
        labels = {
            "msn": "MSN",
            "acft": "ACFT",
            "tac": "TAC",
            "tac_sub": "TAC",
            "el": "EL",
            "wpn": "WPN",
            "knwn_last": "KNWN LAST",
            "ip_lat_h": "LAT",
            "ip_lat_deg": "LAT",
            "ip_lat_min": "LAT",
            "ip_lat_frac": "LAT",
            "ip_lon_h": "LONG",
            "ip_lon_deg": "LONG",
            "ip_lon_min": "LONG",
            "ip_lon_frac": "LONG",
            "hdg": "HDG",
            "rng_whole": "RNG",
            "rng_frac": "RNG",
            "elev": "ELEV",
            "desc": "DESC",
            "stat": "STAT",
            "tgt_lat_h": "LAT",
            "tgt_lat_deg": "LAT",
            "tgt_lat_min": "LAT",
            "tgt_lat_frac": "LAT",
            "tgt_lon_h": "LONG",
            "tgt_lon_deg": "LONG",
            "tgt_lon_min": "LONG",
            "tgt_lon_frac": "LONG",
            "lsr": "LSR",
            "card": "CARD",
            "frnd_num": "FRND",
            "frnd_code": "FRND",
            "frnd_alpha": "FRND",
            "egrs_a": "EGRS",
            "egrs_b": "EGRS",
        }
        return str(labels.get(key, key.upper()))

    def _draw_lr_inc_dec_symbols_in_cell(self, surface: pygame.Surface, box: pygame.Rect) -> None:
        cyan = (0, 255, 255)
        tri_w = max(10, box.width // 3)
        tri_h = max(8, box.height // 3)
        lx = box.left + max(8, box.width // 4)
        rx = box.right - max(8, box.width // 4)
        cy = box.centery
        left_tri = [(lx, cy), (lx + tri_w, cy - tri_h // 2), (lx + tri_w, cy + tri_h // 2)]
        right_tri = [(rx, cy), (rx - tri_w, cy - tri_h // 2), (rx - tri_w, cy + tri_h // 2)]
        pygame.draw.polygon(surface, cyan, left_tri, 0)
        pygame.draw.polygon(surface, cyan, right_tri, 0)

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

    def _draw_text(self, surface: pygame.Surface, font: pygame.font.Font, x: int, y: int, text: str, color: Tuple[int, int, int]) -> int:
        surf = font.render(str(text), True, color)
        rr = surf.get_rect(x=x, y=y)
        surface.blit(surf, rr)
        return int(rr.right)

    def _draw_slot(self, surface: pygame.Surface, font: pygame.font.Font, x: int, y: int, slot: str, text: str) -> int:
        selected = self._outbox_new_open and (slot == self._slot_selected())
        color = (255, 255, 255) if selected else (0, 255, 255)
        surf = font.render(str(text), True, color)
        rr = surf.get_rect(x=x, y=y)
        if selected:
            pygame.draw.rect(surface, (255, 255, 255), rr.inflate(4, 2), 1)
        surface.blit(surf, rr)
        return int(rr.right)

    def _render_outbox_new(self, surface: pygame.Surface, content_rect: pygame.Rect) -> None:
        green = (0, 255, 0); cyan = (0, 255, 255); font = get_font(10); row_h = font.get_height() + 1
        x0 = content_rect.left + 8; y = content_rect.top + 6

        def line(parts: List[Tuple[str, str, Tuple[int, int, int]]]) -> None:
            nonlocal y
            x = x0
            for kind, text, color in parts:
                x = self._draw_text(surface, font, x, y, text, color) if kind == "text" else self._draw_slot(surface, font, x, y, kind, text)
            y += row_h

        line([("text", "MSN ", green), ("msn", self._slot_fmt("msn", 4), cyan), ("text", "  MC ", green), ("text", "/2N", cyan)])
        line([("text", "ACFT ", green), ("acft", self._slot_var("acft"), cyan)])
        line([("text", "TAC ", green), ("tac", self._slot_var("tac"), cyan)])
        line([("text", "    ", green), ("tac_sub", self._slot_var("tac_sub"), cyan), ("text", " EL ", green), ("el", self._slot_fmt("el", 4), cyan)])
        line([("text", "WPN ", green), ("wpn", self._slot_var("wpn"), cyan)])
        line([("text", "KNWN LAST ", green), ("knwn_last", self._slot_var("knwn_last"), cyan)])
        y += row_h
        line([("text", "1 IP", green)])
        line([("text", "  LAT ", green), ("ip_lat_h", self._slot_fmt("ip_lat_h", 1), cyan), ("text", " ", cyan), ("ip_lat_deg", self._slot_fmt("ip_lat_deg", 3), cyan), ("text", "\u00b0", cyan), ("ip_lat_min", self._slot_fmt("ip_lat_min", 2), cyan), ("text", ".", cyan), ("ip_lat_frac", self._slot_fmt("ip_lat_frac", 4), cyan)])
        line([("text", "  LONG ", green), ("ip_lon_h", self._slot_fmt("ip_lon_h", 1), cyan), ("text", " ", cyan), ("ip_lon_deg", self._slot_fmt("ip_lon_deg", 3), cyan), ("text", "\u00b0", cyan), ("ip_lon_min", self._slot_fmt("ip_lon_min", 2), cyan), ("text", ".", cyan), ("ip_lon_frac", self._slot_fmt("ip_lon_frac", 4), cyan)])
        line([("text", "2 HDG ", green), ("hdg", self._slot_fmt("hdg", 3), cyan), ("text", "\u00b0  OFFSET", green)])
        line([("text", "3 RNG ", green), ("rng_whole", self._slot_fmt("rng_whole", 1), cyan), ("text", ".", cyan), ("rng_frac", self._slot_fmt("rng_frac", 1), cyan), ("text", " NM", green)])
        line([("text", "4 ELEV ", green), ("elev", self._slot_fmt("elev", 4), cyan), ("text", " FT", green)])
        line([("text", "5 DESC ", green), ("desc", self._slot_var("desc"), cyan)])
        y += row_h
        line([("text", "  FREQ/IAS SETTING", green)])
        y += row_h
        line([("text", "  STAT ", green), ("stat", self._slot_var("stat"), cyan)])
        line([("text", "6 TGT INFO", green)])
        line([("text", "  C/B SN", green)])
        line([("text", "  LAT ", green), ("tgt_lat_h", self._slot_fmt("tgt_lat_h", 1), cyan), ("text", " ", cyan), ("tgt_lat_deg", self._slot_fmt("tgt_lat_deg", 3), cyan), ("text", "\u00b0", cyan), ("tgt_lat_min", self._slot_fmt("tgt_lat_min", 2), cyan), ("text", ".", cyan), ("tgt_lat_frac", self._slot_fmt("tgt_lat_frac", 4), cyan)])
        line([("text", "  LONG ", green), ("tgt_lon_h", self._slot_fmt("tgt_lon_h", 1), cyan), ("text", " ", cyan), ("tgt_lon_deg", self._slot_fmt("tgt_lon_deg", 3), cyan), ("text", "\u00b0", cyan), ("tgt_lon_min", self._slot_fmt("tgt_lon_min", 2), cyan), ("text", ".", cyan), ("tgt_lon_frac", self._slot_fmt("tgt_lon_frac", 4), cyan)])
        line([("text", "  LSR ", green), ("lsr", self._slot_fmt("lsr", 4), cyan)])
        line([("text", "  MAPNG", green)])
        line([("text", "7 MARK", green)])
        y += row_h
        line([("text", "  CARD ", green), ("card", self._slot_fmt("card", 4), cyan), ("text", " SN-279", green)])
        line([("text", "8 FRND ", green), ("frnd_num", self._slot_fmt("frnd_num", 1), cyan), ("text", " ", cyan), ("frnd_code", self._slot_fmt("frnd_code", 4), cyan), ("text", " ", cyan), ("frnd_alpha", self._slot_fmt("frnd_alpha", 1), cyan)])
        line([("text", "9 EGRS ", green), ("egrs_a", self._slot_fmt("egrs_a", 1), cyan), ("text", " ", cyan), ("egrs_b", self._slot_fmt("egrs_b", 1), cyan)])

    def _inbox_section_headers(self) -> List[str]:
        type(self)._refresh_shared_image_count()
        headers: List[str] = [
            "MSN ASSIGN - OWN - CTOTAL",
            "MSN ASSIGN - FLT - CTOTAL",
        ]
        try:
            image_count = int(getattr(self, "_shared_inbox_image_count", 0))
        except Exception:
            image_count = 0
        if image_count > 0:
            headers.append("IMAGES")
        headers.extend(
            [
                "BDA - /DL",
                "MISC REPORT - /DL/TYPE",
            ]
        )
        return headers

    @staticmethod
    def _mission_row_text(mission: Dict[str, object]) -> Tuple[str, str, str, str, str]:
        time_txt = str(mission.get("time", "")).strip().upper()
        local_txt = str(mission.get("local", "")).strip().upper()
        target_txt = str(mission.get("target", "")).strip().upper()
        msn_type_txt = str(mission.get("msn_type", "")).strip().upper()
        status_txt = str(mission.get("status", "REPLY")).strip().upper()
        if status_txt == "":
            status_txt = "REPLY"
        return (time_txt, local_txt, target_txt, msn_type_txt, status_txt)

    def _draw_mission_row(
        self,
        surface: pygame.Surface,
        row_font: pygame.font.Font,
        x_time: int,
        x_lv: int,
        x_unit: int,
        x_task: int,
        x_res: int,
        y: int,
        mission: Dict[str, object],
        selected: bool,
    ) -> None:
        cyan = (0, 255, 255)
        white = (255, 255, 255)
        col = white if selected else cyan
        time_txt, local_txt, target_txt, msn_type_txt, status_txt = self._mission_row_text(mission)
        cw = row_font.size("0")[0]
        if selected:
            dot_x = x_time - max(5, cw // 2)
            dot_y = y + row_font.get_height() // 2
            pygame.draw.circle(surface, white, (dot_x, dot_y), max(2, cw // 4), 0)
        if time_txt != "":
            surface.blit(row_font.render(time_txt, True, col), (x_time, y))
        if local_txt != "":
            surface.blit(row_font.render(local_txt, True, col), (x_lv, y))
        if target_txt != "":
            surface.blit(row_font.render(target_txt, True, col), (x_unit, y))
        if msn_type_txt != "":
            surface.blit(row_font.render(msn_type_txt, True, col), (x_task, y))
        if status_txt != "":
            surface.blit(row_font.render(status_txt, True, col), (x_res, y))

    def _render_outbox_rows(self, surface: pygame.Surface, content_rect: pygame.Rect) -> None:
        green = (0, 255, 0)
        row_font = get_font(13)
        header_font = get_font(14)
        row_h = row_font.get_height() + 2
        cw = row_font.size("0")[0]
        x_time = content_rect.left + max(6, cw)
        x_lv = x_time + (6 * cw)
        x_unit = x_time + (8 * cw)
        x_task = x_time + (13 * cw)
        x_res = x_time + (20 * cw)
        y = content_rect.top + 8
        hs = header_font.render("MSN TASKED - OWN - CTOTAL", True, green)
        hr = hs.get_rect(left=x_time, y=y)
        surface.blit(hs, hr)
        pygame.draw.line(surface, green, (hr.left, hr.bottom + 1), (hr.right, hr.bottom + 1), 1)
        y = hr.bottom + 5
        for mission in self._outbox_rows():
            if y + row_h > content_rect.bottom:
                break
            self._draw_mission_row(surface, row_font, x_time, x_lv, x_unit, x_task, x_res, y, mission, False)
            y += row_h

    def _render_inbox_rows(self, surface: pygame.Surface, content_rect: pygame.Rect) -> None:
        green = (0, 255, 0)
        cyan = (0, 255, 255)
        white = (255, 255, 255)
        header_font = get_font(14)
        row_font = get_font(13)
        row_h = row_font.get_height() + 2
        sec_gap = 6
        cw = row_font.size("0")[0]
        x_time = content_rect.left + max(6, cw)
        x_lv = x_time + (6 * cw)
        x_unit = x_time + (8 * cw)
        x_task = x_time + (13 * cw)
        x_res = x_time + (20 * cw)
        own_rows = self._inbox_own_rows()
        flt_rows = self._inbox_flt_rows()
        image_rows = self._inbox_image_rows()
        self._clamp_selected()
        selected_global = max(0, int(self._selected_row_idx))
        selectable_idx = 0
        y = content_rect.top + 8
        section_rows: List[Tuple[str, List[Dict[str, object]]]] = [
            ("MSN ASSIGN - OWN - CTOTAL", own_rows),
            ("MSN ASSIGN - FLT - CTOTAL", flt_rows),
        ]
        if len(image_rows) > 0:
            section_rows.append(("IMAGES", image_rows))
        section_rows.append(("BDA - /DL", []))
        section_rows.append(("MISC REPORT - /DL/TYPE", []))
        for sec_idx, (header, rows) in enumerate(section_rows):
            hs = header_font.render(header, True, green)
            hr = hs.get_rect(left=x_time, y=y)
            surface.blit(hs, hr)
            pygame.draw.line(surface, green, (hr.left, hr.bottom + 1), (hr.right, hr.bottom + 1), 1)
            y = hr.bottom + 4
            for mission in rows:
                if y + row_h > content_rect.bottom:
                    return
                if header == "IMAGES":
                    selected = selectable_idx == selected_global
                    col = white if selected else cyan
                    if selected:
                        dot_x = x_time - max(5, cw // 2)
                        dot_y = y + row_font.get_height() // 2
                        pygame.draw.circle(surface, white, (dot_x, dot_y), max(2, cw // 4), 0)
                    row_label = f"{str(mission.get('time', '')).strip().upper()}-M-{str(mission.get('msn_type', '')).strip().upper()}"
                    surface.blit(row_font.render(row_label, True, col), (x_time, y))
                else:
                    selected = selectable_idx == selected_global
                    self._draw_mission_row(surface, row_font, x_time, x_lv, x_unit, x_task, x_res, y, mission, selected)
                selectable_idx += 1
                y += row_h
            y += sec_gap
            if sec_idx == 1:
                y += row_h

    def _render_new_image_page(self, surface: pygame.Surface, content_rect: pygame.Rect) -> None:
        image_surface = self._current_new_image_surface()
        if image_surface is None:
            return
        iw = max(1, int(image_surface.get_width()))
        ih = max(1, int(image_surface.get_height()))
        scale = min(content_rect.width / float(iw), content_rect.height / float(ih))
        scale = max(0.01, scale)
        tw = max(1, int(iw * scale))
        th = max(1, int(ih * scale))
        try:
            scaled = pygame.transform.smoothscale(image_surface, (tw, th))
        except Exception:
            scaled = pygame.transform.scale(image_surface, (tw, th))
        dst = scaled.get_rect(center=content_rect.center)
        surface.blit(scaled, dst)

    def _draw_keypad(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        if not self._keypad_visible:
            return
        prev_clip = surface.get_clip()
        surface.set_clip(rect)
        cyan = (0, 255, 255)
        popup = self._popup_rect(rect)
        grid = self._grid_rect(rect)
        mapping = self._keypad_map()
        surface.fill((0, 0, 0), popup)
        pygame.draw.rect(surface, cyan, popup, 1)
        for c in (1, 2):
            x = popup.left + (c * GRID_CELL_W)
            pygame.draw.line(surface, cyan, (x, popup.top), (x, popup.bottom), 1)
        for r in (1, 2, 3, 4):
            y = popup.top + (r * GRID_CELL_H)
            pygame.draw.line(surface, cyan, (popup.left, y), (popup.right, y), 1)
        font = get_font(13)
        now_ms = int(pygame.time.get_ticks())
        for row in range(2, 7):
            for col in range(1, 4):
                cell = f"{chr(ord('A') + col)}{row}"
                label = str(mapping.get(cell, ""))
                box = pygame.Rect(grid.x + (col * GRID_CELL_W), grid.y + ((row - 1) * GRID_CELL_H), GRID_CELL_W, GRID_CELL_H)
                if label == "":
                    continue
                flashing = bool(self._local_flash_active(f"KEYPAD_{cell}", now_ms))
                if label in {"LEFT", "RIGHT"}:
                    tri_w = max(10, box.width // 3)
                    tri_h = max(8, box.height // 3)
                    cy = box.centery
                    if label == "LEFT":
                        cx = box.centerx - max(4, box.width // 10)
                        pts = [(cx - tri_w // 2, cy), (cx + tri_w // 2, cy - tri_h // 2), (cx + tri_w // 2, cy + tri_h // 2)]
                    else:
                        cx = box.centerx + max(4, box.width // 10)
                        pts = [(cx + tri_w // 2, cy), (cx - tri_w // 2, cy - tri_h // 2), (cx - tri_w // 2, cy + tri_h // 2)]
                    if flashing:
                        pygame.draw.rect(surface, (255, 255, 255), box.inflate(-max(4, box.width // 3), -max(4, box.height // 3)), 0)
                    pygame.draw.polygon(surface, (0, 0, 0) if flashing else cyan, pts, 0)
                    continue
                alpha_part = "".join(ch for ch in label if ch.isalpha())
                digit_part = "".join(ch for ch in label if ch.isdigit())
                if alpha_part != "" and digit_part != "":
                    top = font.render(alpha_part, True, (0, 0, 0) if flashing else cyan)
                    bot = font.render(digit_part, True, (0, 0, 0) if flashing else cyan)
                    total_h = top.get_height() + 1 + bot.get_height()
                    ty = box.centery - total_h // 2
                    tr = top.get_rect(centerx=box.centerx, y=ty)
                    br = bot.get_rect(centerx=box.centerx, y=tr.bottom + 1)
                    if flashing:
                        pygame.draw.rect(surface, (255, 255, 255), tr.union(br).inflate(6, 3), 0)
                    surface.blit(top, tr)
                    surface.blit(bot, br)
                else:
                    surf = font.render(label, True, (0, 0, 0) if flashing else cyan)
                    rr = surf.get_rect(center=box.center)
                    if flashing:
                        pygame.draw.rect(surface, (255, 255, 255), rr.inflate(6, 3), 0)
                    surface.blit(surf, rr)
        surface.set_clip(prev_clip)

    def render(self, surface, rect, is_primary: bool, context: FormatContext) -> None:
        self._run_pending_nav_action()
        prev_clip = surface.get_clip()
        surface.set_clip(rect)
        surface.fill((0, 0, 0), rect)
        if not is_primary:
            font = get_font(14)
            surf = font.render("DIM", True, (0, 255, 255))
            rr = surf.get_rect(centerx=rect.centerx, bottom=rect.bottom - 2)
            surface.blit(surf, rr)
            pygame.draw.rect(surface, (0, 255, 255), rect, 1)
            surface.set_clip(prev_clip)
            return
        gray = (130, 130, 130)
        cyan = (0, 255, 255)
        self._clamp_selected()
        if self._outbox_new_open:
            t2 = self._osb_box(rect, "T2")
            t3 = self._osb_box(rect, "T3")
            t4 = self._osb_box(rect, "T4")
            if not self._new_page_is_image():
                if t2 is not None:
                    v = self._header_display("time") if self._header_selected_field != "time" else ((str(self._header_input_by_field.get("time", "")) + "____")[:4] + "Z")
                    self._draw_header_btn(surface, t2, "TIME", v, self._header_selected_field == "time", bool(context.is_osb_flashing("T2")))
                if t3 is not None:
                    v = self._header_display("target") if self._header_selected_field != "target" else (str(self._header_input_by_field.get("target", "")) + "____")[:4]
                    self._draw_header_btn(surface, t3, "TARGET", v, self._header_selected_field == "target", bool(context.is_osb_flashing("T3")))
                if t4 is not None:
                    v = self._header_display("msn_type") if self._header_selected_field != "msn_type" else (str(self._header_input_by_field.get("msn_type", "")) + "______")[:6]
                    self._draw_header_btn(surface, t4, "MSN TYPE", v, self._header_selected_field == "msn_type", bool(context.is_osb_flashing("T4")))
            else:
                if t3 is not None:
                    render_button(
                        surface,
                        t3,
                        ButtonState(
                            button_id="DIM_T3_DELETE",
                            button_type=ButtonType.MOMENTARY_SINGLE,
                            text="DELETE",
                            is_single_function=True,
                            is_on=False,
                            h_align="center",
                            v_align="top",
                            padding=OSB_PADDING,
                            font_size=14,
                            flash_until_ms=1 if context.is_osb_flashing("T3") else 0,
                        ),
                        get_font,
                        int(pygame.time.get_ticks()),
                    )
            self._draw_inc_dec_symbols(surface, rect, context)
            r1 = self._osb_box(rect, "R1")
            r2 = self._osb_box(rect, "R2")
            r3 = self._osb_box(rect, "R3")
            r4 = self._osb_box(rect, "R4")
            l5 = self._osb_box(rect, "L5")
            r5 = self._osb_box(rect, "R5")
            if r1 is not None:
                render_button(
                    surface,
                    r1,
                    ButtonState(
                        button_id="DIM_R1_BACK",
                        button_type=ButtonType.PAGE_ACCESS,
                        text="<BACK",
                        h_align="right",
                        v_align="center",
                        padding=OSB_PADDING,
                        font_size=14,
                        flash_until_ms=1 if context.is_osb_flashing("R1") else 0,
                    ),
                    get_font,
                    int(pygame.time.get_ticks()),
                )
            if r2 is not None:
                if self._slot_edit_active and self._slot_edit_field != "":
                    mode, width, _ = self._slot_specs.get(self._slot_edit_field, ("alnum", 6, None))
                    disp_w = max(4, min(8, int(width)))
                    cur = self._sanitize(mode, str(self._slot_edit_buffer), disp_w, None)
                    prev = self._sanitize(mode, str(self._slot_edit_prev_value), disp_w, None)
                    l1_text = f"{cur[-disp_w:].rjust(disp_w, '_')}\u2190"
                    l2_text = self._slot_display_label(self._slot_edit_field)
                    l3_text = prev[-disp_w:].rjust(disp_w, "_")
                    f = get_font(14)
                    l1 = f.render(l1_text, True, (255, 255, 255))
                    l2 = f.render(l2_text, True, (0, 255, 255))
                    l3 = f.render(l3_text, True, (0, 255, 255))
                    total_h = l1.get_height() + 1 + l2.get_height() + 1 + l3.get_height()
                    y0 = r2.centery - total_h // 2
                    r1t = l1.get_rect(right=r2.right - OSB_PADDING, y=y0)
                    r2t = l2.get_rect(right=r2.right - OSB_PADDING, y=r1t.bottom + 1)
                    r3t = l3.get_rect(right=r2.right - OSB_PADDING, y=r2t.bottom + 1)
                    for rr in (r1t, r2t, r3t):
                        pygame.draw.rect(surface, (0, 0, 0), rr.inflate(6, 2), 0)
                    pygame.draw.rect(surface, (255, 255, 255), r1t.inflate(6, 4), 1)
                    surface.blit(l1, r1t)
                    surface.blit(l2, r2t)
                    surface.blit(l3, r3t)
                else:
                    label = self._slot_display_label(self._slot_selected())
                    render_button(
                        surface,
                        r2,
                        ButtonState(
                            button_id="DIM_R2_EDIT",
                            button_type=ButtonType.PAGE_ACCESS,
                            text=f"EDIT>\n{label}",
                            h_align="right",
                            v_align="center",
                            padding=OSB_PADDING,
                            font_size=14,
                            flash_until_ms=1 if context.is_osb_flashing("R2") else 0,
                        ),
                        get_font,
                        int(pygame.time.get_ticks()),
                    )
            if r3 is not None:
                render_button(
                    surface,
                    r3,
                    ButtonState(
                        button_id="DIM_R3_ATCH",
                        button_type=ButtonType.PAGE_ACCESS,
                        text="ATCH\nIMAGE",
                        h_align="right",
                        v_align="center",
                        padding=OSB_PADDING,
                        font_size=14,
                        flash_until_ms=1 if context.is_osb_flashing("R3") else 0,
                    ),
                    get_font,
                    int(pygame.time.get_ticks()),
                )
            if r4 is not None:
                render_button(
                    surface,
                    r4,
                    ButtonState(
                        button_id="DIM_R4_SEND",
                        button_type=ButtonType.MOMENTARY_SINGLE,
                        text="SEND",
                        is_single_function=True,
                        is_on=False,
                        enabled=bool(self._send_ready()),
                        h_align="right",
                        v_align="center",
                        padding=OSB_PADDING,
                        font_size=14,
                        flash_until_ms=1 if context.is_osb_flashing("R4") else 0,
                    ),
                    get_font,
                    int(pygame.time.get_ticks()),
                )
            if l5 is not None:
                render_button(
                    surface,
                    l5,
                    ButtonState(
                        button_id="DIM_L5_PREV",
                        button_type=ButtonType.PAGE_ACCESS,
                        text="<PREV\nPAGE",
                        enabled=bool(self._new_page_can_prev()),
                        h_align="left",
                        v_align="center",
                        padding=OSB_PADDING,
                        font_size=14,
                        flash_until_ms=1 if context.is_osb_flashing("L5") else 0,
                    ),
                    get_font,
                    int(pygame.time.get_ticks()),
                )
            if r5 is not None:
                render_button(
                    surface,
                    r5,
                    ButtonState(
                        button_id="DIM_R5_NEXT",
                        button_type=ButtonType.PAGE_ACCESS,
                        text="NEXT\nPAGE>",
                        enabled=bool(self._new_page_can_next()),
                        h_align="right",
                        v_align="center",
                        padding=OSB_PADDING,
                        font_size=14,
                        flash_until_ms=1 if context.is_osb_flashing("R5") else 0,
                    ),
                    get_font,
                    int(pygame.time.get_ticks()),
                )
        else:
            t2 = self._osb_box(rect, "T2")
            if self._t2_idx == self._MODE_INBOX and self._inbox_view_open and self._inbox_view_kind == "MISSION":
                t3 = self._osb_box(rect, "T3")
                t4 = self._osb_box(rect, "T4")
                if t2 is not None:
                    render_button(
                        surface,
                        t2,
                        ButtonState(
                            button_id="DIM_T2_WILCO",
                            button_type=ButtonType.MOMENTARY_SINGLE,
                            text="WILCO",
                            is_single_function=True,
                            is_on=False,
                            enabled=bool(self._response_button_enabled("WILCO")),
                            h_align="center",
                            v_align="top",
                            padding=OSB_PADDING,
                            font_size=14,
                            flash_until_ms=1 if context.is_osb_flashing("T2") else 0,
                        ),
                        get_font,
                        int(pygame.time.get_ticks()),
                    )
                if t3 is not None:
                    render_button(
                        surface,
                        t3,
                        ButtonState(
                            button_id="DIM_T3_CANTCO",
                            button_type=ButtonType.MOMENTARY_SINGLE,
                            text="CANTCO",
                            is_single_function=True,
                            is_on=False,
                            enabled=bool(self._response_button_enabled("CANTCO")),
                            h_align="center",
                            v_align="top",
                            padding=OSB_PADDING,
                            font_size=14,
                            flash_until_ms=1 if context.is_osb_flashing("T3") else 0,
                        ),
                        get_font,
                        int(pygame.time.get_ticks()),
                    )
                if t4 is not None:
                    render_button(
                        surface,
                        t4,
                        ButtonState(
                            button_id="DIM_T4_HAVECO",
                            button_type=ButtonType.MOMENTARY_SINGLE,
                            text="HAVECO",
                            is_single_function=True,
                            is_on=False,
                            enabled=bool(self._response_button_enabled("HAVECO")),
                            h_align="center",
                            v_align="top",
                            padding=OSB_PADDING,
                            font_size=14,
                            flash_until_ms=1 if context.is_osb_flashing("T4") else 0,
                        ),
                        get_font,
                        int(pygame.time.get_ticks()),
                    )
            else:
                if t2 is not None:
                    t2_state = ButtonState(button_id="DIM_T2", button_type=ButtonType.DOUBLE_FUNCTION, options=["INBOX", "OUTBOX"], selected_index=max(0, min(1, int(self._t2_idx))), h_align="center", v_align="top", padding=OSB_PADDING, font_size=14, flash_until_ms=1 if context.is_osb_flashing("T2") else 0)
                    render_button(surface, t2, t2_state, get_font, int(pygame.time.get_ticks()))
            self._draw_inc_dec_symbols(surface, rect, context)
            r1 = self._osb_box(rect, "R1")
            if r1 is not None:
                if self._t2_idx == self._MODE_OUTBOX:
                    render_button(
                        surface,
                        r1,
                        ButtonState(
                            button_id="DIM_R1_NEW",
                            button_type=ButtonType.PAGE_ACCESS,
                            text="NEW>",
                            h_align="right",
                            v_align="center",
                            padding=OSB_PADDING,
                            font_size=14,
                            flash_until_ms=1 if context.is_osb_flashing("R1") else 0,
                        ),
                        get_font,
                        int(pygame.time.get_ticks()),
                    )
                else:
                    section, mission = self._selected_inbox_entry()
                    if mission is not None and section == "OWN":
                        r1_lines = ["ASGN", "FLT"]
                    elif mission is None or section == "IMAGE":
                        r1_lines = ["ASGN", "SELF"]
                    else:
                        r1_lines = ["ASGN", "SELF"]
                    render_button(
                        surface,
                        r1,
                        ButtonState(
                            button_id="DIM_R1_ASGN",
                            button_type=ButtonType.PAGE_ACCESS,
                            text="\n".join(r1_lines),
                            h_align="right",
                            v_align="center",
                            padding=OSB_PADDING,
                            font_size=14,
                            flash_until_ms=1 if context.is_osb_flashing("R1") else 0,
                        ),
                        get_font,
                        int(pygame.time.get_ticks()),
                    )
            if self._t2_idx == self._MODE_INBOX:
                report_enabled = self._report_enabled_for_selected()
                for label, text, h_align in (("L3", "VIEW>", "left"), ("L4", "DELETE", "left"), ("L5", "<PREV\nPAGE", "left"), ("R3", "REPORT>", "right"), ("R4", "L16", "right"), ("R5", "NEXT\nPAGE>", "right")):
                    box = self._osb_box(rect, label)
                    if box is None:
                        continue
                    if label == "R3":
                        render_button(
                            surface,
                            box,
                            ButtonState(
                                button_id="DIM_R3_REPORT",
                                button_type=ButtonType.PAGE_ACCESS,
                                text="REPORT>",
                                enabled=bool(report_enabled),
                                h_align="right",
                                v_align="center",
                                padding=OSB_PADDING,
                                font_size=14,
                                flash_until_ms=1 if context.is_osb_flashing("R3") else 0,
                            ),
                            get_font,
                            int(pygame.time.get_ticks()),
                        )
                    else:
                        bs = ButtonState(button_id=f"DIM_{label}", button_type=ButtonType.PAGE_ACCESS, text=text, h_align=h_align, v_align="center", padding=OSB_PADDING, font_size=14, flash_until_ms=1 if context.is_osb_flashing(label) else 0)
                        render_button(surface, box, bs, get_font, int(pygame.time.get_ticks()))

        content_left = rect.left + GRID_CELL_W + 8
        content_top = rect.top + GRID_CELL_H + 4
        content_right = rect.right - GRID_CELL_W - 8
        if rect.height < int(7 * DPI) - 1:
            # In 5x5/10x5, allow content to extend under subportals so it is not prematurely clipped.
            content_bottom = rect.bottom - 4
        else:
            content_bottom = rect.bottom - GRID_CELL_H - 4
        content_rect = pygame.Rect(content_left, content_top, max(1, content_right - content_left), max(1, content_bottom - content_top))
        surface.set_clip(content_rect)
        if self._outbox_new_open:
            if self._new_page_is_image():
                self._render_new_image_page(surface, content_rect)
            else:
                self._render_outbox_new(surface, content_rect)
        elif self._t2_idx == self._MODE_OUTBOX:
            self._render_outbox_rows(surface, content_rect)
        else:
            if self._inbox_view_open:
                self._render_inbox_view(surface, content_rect)
            else:
                self._render_inbox_rows(surface, content_rect)
        surface.set_clip(prev_clip)
        self._draw_keypad(surface, rect)
        pygame.draw.rect(surface, (0, 255, 255), rect, 1)

    def on_click(self, pos: Tuple[int, int], rect: pygame.Rect, context: FormatContext) -> bool:
        _ = context
        if not self._keypad_visible:
            return False
        popup = self._popup_rect(rect)
        if not popup.collidepoint(pos):
            self._keypad_close()
            return False
        grid = self._grid_rect(rect)
        col = max(0, min(4, int((pos[0] - grid.x) // GRID_CELL_W)))
        row = max(0, min(7, int((pos[1] - grid.y) // GRID_CELL_H)))
        cell = f"{chr(ord('A') + col)}{row + 1}"
        tok = str(self._keypad_map().get(cell, ""))
        if tok != "":
            self._trigger_local_flash(f"KEYPAD_{cell}")
            self._keypad_apply(cell, tok)
        return True

    def on_key(self, key: str) -> bool:
        if not self._keypad_visible:
            return False
        raw = str(key)
        if raw == "":
            return False
        token = raw.strip().upper()
        if token in {"KP_BACK", "BACKSPACE", "BACK"}:
            self._keypad_apply("D5", "BACK")
            return True
        if token in {"LEFT", "KP_LEFT"}:
            self._keypad_apply("B6", "LEFT")
            return True
        if token in {"RIGHT", "KP_RIGHT"}:
            self._keypad_apply("C6", "RIGHT")
            return True
        if token in {"ENTER", "RETURN", "KP_ENTER"}:
            self._keypad_apply("KB", "ENT")
            return True
        if raw == ">" or token in {"TAB", "KP_TAB"}:
            self._keypad_apply("D6", ">")
            return True
        ch = ""
        if token.startswith("KP_") and len(token) == 4 and token[3].isdigit():
            ch = token[3]
        elif len(raw) == 1 and raw.isdigit():
            ch = raw
        elif len(raw) == 1 and raw.isalpha():
            ch = raw.upper()
        elif raw == " ":
            ch = " "
        if ch != "":
            # Physical keyboard inputs append directly as new chars.
            self._cycle_cell = ""
            self._cycle_idx = 0
            self._cycle_until_ms = 0
            if ch == " ":
                self._keypad_apply("KB", "SP")
            else:
                self._keypad_apply("KB", ch)
            return True
        return False

    def on_osb(self, label: str, context: FormatContext) -> bool:
        token = str(label).upper().strip()
        if token == "T1":
            context.request_vded(context.portal_index, "MENU")
            return True
        if (not self._outbox_new_open) and self._t2_idx == self._MODE_INBOX and self._inbox_view_open and self._inbox_view_kind == "MISSION":
            if token == "T2":
                return self._set_mission_response("WILCO")
            if token == "T3":
                return self._set_mission_response("CANTCO")
            if token == "T4":
                return self._set_mission_response("HAVECO")
        if token == "T2":
            if self._outbox_new_open:
                if self._new_page_is_image():
                    return True
                if self._header_selected_field == "time":
                    self._header_commit("time")
                    self._header_selected_field = ""
                    self._keypad_close()
                else:
                    self._header_selected_field = "time"
                    self._header_input_by_field["time"] = str(self._header_value_by_field.get("time", "0000Z")).rstrip("Z")
                    self._keypad_open("header", "time", "numeric")
                return True
            self._t2_idx = self._MODE_OUTBOX if int(self._t2_idx) == self._MODE_INBOX else self._MODE_INBOX
            self._outbox_new_open = False
            self._close_inbox_view()
            self._keypad_close()
            return True
        if token == "T3":
            if self._outbox_new_open:
                if self._new_page_is_image():
                    self._delete_current_new_image()
                    return True
                if self._header_selected_field == "target":
                    self._header_commit("target")
                    self._header_selected_field = ""
                    self._keypad_close()
                else:
                    self._header_selected_field = "target"
                    self._header_input_by_field["target"] = str(self._header_value_by_field.get("target", ""))
                    self._keypad_open("header", "target", "alnum")
                return True
            return False
        if token == "T4":
            if self._outbox_new_open:
                if self._new_page_is_image():
                    return True
                if self._header_selected_field == "msn_type":
                    self._header_commit("msn_type")
                    self._header_selected_field = ""
                    self._keypad_close()
                else:
                    self._header_selected_field = "msn_type"
                    self._header_input_by_field["msn_type"] = str(self._header_value_by_field.get("msn_type", ""))
                    self._keypad_open("header", "msn_type", "alpha")
                return True
            return False
        if token == "L1":
            if self._outbox_new_open:
                self._slot_move(-1)
            else:
                self._selected_row_idx -= 1
                self._clamp_selected()
            return True
        if token == "L2":
            if self._outbox_new_open:
                self._slot_move(1)
            else:
                self._selected_row_idx += 1
                self._clamp_selected()
            return True
        if token == "R1":
            if self._t2_idx == self._MODE_OUTBOX:
                if self._outbox_new_open:
                    self._outbox_new_open = False
                    self._header_selected_field = ""
                    self._slot_edit_active = False
                    self._slot_edit_field = ""
                    self._slot_edit_prev_value = ""
                    self._slot_edit_buffer = ""
                    self._new_image_page_idx = 0
                    self._keypad_close()
                else:
                    self._outbox_new_open = True
                    self._reset_outbox_new_entry()
                return True
            if self._t2_idx == self._MODE_INBOX:
                self._toggle_inbox_assign()
                return True
            return True
        if token == "R2":
            if self._outbox_new_open:
                if self._new_page_is_image():
                    return True
                slot = self._slot_selected()
                mode = self._slot_specs.get(slot, ("alnum", 4, None))[0]
                if self._slot_edit_active and self._slot_edit_field == slot:
                    self._slot_set(slot, str(self._slot_edit_buffer))
                    self._slot_edit_active = False
                    self._slot_edit_field = ""
                    self._slot_edit_prev_value = ""
                    self._slot_edit_buffer = ""
                    self._keypad_close()
                else:
                    self._header_selected_field = ""
                    self._slot_edit_active = True
                    self._slot_edit_field = slot
                    self._slot_edit_prev_value = self._slot_get(slot)
                    self._slot_edit_buffer = self._slot_get(slot)
                    self._keypad_open("slot", slot, mode)
                return True
            return False
        if token == "L3":
            if (not self._outbox_new_open) and self._t2_idx == self._MODE_INBOX:
                self._queue_nav_action("L3")
                return True
            return True
        if token == "L5":
            if (not self._outbox_new_open) and self._t2_idx == self._MODE_INBOX:
                self._queue_nav_action("L5")
                return True
            if (not self._outbox_new_open) and self._t2_idx == self._MODE_INBOX and self._inbox_view_open:
                if self._inbox_view_prev_page():
                    return True
                return True
            if self._outbox_new_open and self._new_page_can_prev():
                self._new_image_page_idx = max(0, int(self._new_image_page_idx) - 1)
                return True
            return True
        if token == "R5":
            if (not self._outbox_new_open) and self._t2_idx == self._MODE_INBOX:
                self._queue_nav_action("R5")
                return True
            if (not self._outbox_new_open) and self._t2_idx == self._MODE_INBOX and self._inbox_view_open:
                if self._inbox_view_next_page():
                    return True
                return True
            if self._outbox_new_open and self._new_page_can_next():
                self._new_image_page_idx = min(self._new_total_pages() - 1, int(self._new_image_page_idx) + 1)
                return True
            return True
        if token == "R3":
            if self._outbox_new_open:
                self._attach_new_image()
                return True
            if self._t2_idx == self._MODE_INBOX:
                if not self._report_enabled_for_selected():
                    return True
                return True
            return True
        if token == "R4":
            if self._outbox_new_open:
                self._create_and_send_mission()
                return True
            return True
        if token == "L4":
            if (not self._outbox_new_open) and self._t2_idx == self._MODE_INBOX:
                self._delete_selected_inbox_entry()
                return True
            return True
        return False

    def osb_is_interactive(self, label: str) -> bool:
        token = str(label).upper().strip()
        if (not self._outbox_new_open) and self._t2_idx == self._MODE_INBOX and self._inbox_view_open and self._inbox_view_kind == "MISSION":
            return token in {"T1", "T2", "T3", "T4", "L1", "L2", "L3", "L4", "L5", "R1", "R3", "R4", "R5"}
        if self._outbox_new_open:
            return token in {"T1", "T2", "T3", "T4", "L1", "L2", "L5", "R1", "R2", "R3", "R4", "R5"}
        if self._t2_idx == self._MODE_OUTBOX:
            return token in {"T1", "T2", "L1", "L2", "R1"}
        return token in {"T1", "T2", "L1", "L2", "L3", "L4", "L5", "R1", "R3", "R4", "R5"}
