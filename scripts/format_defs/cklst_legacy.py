from formats import *  # noqa: F401,F403


class CklstLegacyFormat(FormatBase):
    name: str = "CKLST"

    _COCKPIT_ITEMS: List[str] = [
        "GEN (ICC) 1, 2, and 3... ON",
        "CABIN PRESSURE... NORM",
        "BATT... OFF",
        "IPP... AUTO",
        "PIC... LOCKED",
        "SSK... CONNECT",
        "HMD... OFF",
        "HMD AND QDC... CONNECT",
        "HARNESS... CONNECT",
        "ARM RESTRAINTS... CONNECT",
        "QRB... CHECK",
        "ENGINE... OFF",
        "DEFOG... AS REQUIRED",
        "THROTTLE FRICTION... 6 O'CLOCK",
        "THROTTLE ACTIVE... ACTIVE",
        "THROTTLE... IDLE",
        "BOS... NORM",
        "LAND/TAXI LIGHTS... OFF",
        "PARKING BRAKE... ON",
        "LG HANDLE... DOWN",
        "JETTISON COLLAR... SEL",
        "PCD... AS REQUIRED",
        "MASTER ARM... OFF",
        "AUTO RECOVERY... NORM",
        "AIRCRAFT ZEROIZE... NORM",
        "STICK... ACTIVE",
        "ARM/HAND REST... ADJUST",
        "PMD... INSTALLED",
    ]
    _ENGINE_START_ITEMS: List[str] = [
        "BATT... ON",
        "BUR... AS REQUIRED",
        "ICAWS... TEST",
        "IPP... START",
        "MONITOR ENG PAGE...",
        "SFD... BIT",
        "THROTTLE... IDLE",
        "SEC/LVL... AUTHENTICATE",
        "ENGINE... RUN",
        "CANOPY... DOWN",
        "MASK... ON",
    ]
    _TAXI_ITEMS: List[str] = [
        "BEFORE TAXI:",
        "",
        "LIGHTS... AS REQUIRED",
        "INS ALIGN MP-24...",
        "SFD ALIGN... AS REQUIRED",
        "SEC/LVL... VERIFY",
        "VS BIT MP-32...",
        "FCS/ENG... RESET",
        "MIP SWITCHES... FLIGHT",
        "WBDS... CLOSE",
        "CM DOORS... CLOSE",
        "SCP... TEST",
        "BOS... NORM",
        "PMD... LOAD ALL",
        "AR SYSTEM... CYCLE",
        "SMS... VERIFY",
        "INS... NAV",
        "HMD... ON",
        "MISSION SYSTEMS... CONFIGURE",
        "JOKER/BINGO/DUMPCO... SET",
        "NAV AIDS/ALTIMETER... SET",
        "",
        "TAXI:",
        "",
        "PARKING BRAKE... OFF",
        "NWS/BRAKES... CHECK",
        "NAV AIDS... CHECK",
    ]
    _TAKEOFF_ITEMS: List[str] = [
        "BEFORE TAKEOFF:",
        "",
        "28V / 270V DIS/LOW... CHECK",
        "WBDS... CLOSE",
        "CG... WITHIN LIMITS",
        "ICAWS... NO ICAWS",
        "TNS... VERIFY HIGH",
        "IFF... SET",
        "RALT... NORM",
        "HARNESS... CONNECTED",
        "ASE... ARMED",
        "LAND/TAXI LIGHTS... AS REQUIRED",
        "FLIGHT CONTROLS... CYCLE",
        "",
        "TAKEOFF:",
        "",
        "NWS... LO",
        "THROTTLE... MIL/MAX",
        "ROTATE... AT ROTATION SPEED",
        "",
        "CLIMB/CRUISE CHK:",
        "",
        "CABIN ALTIMETER... CHECK",
        "ALTIMETER... CHECK",
    ]
    _LANDING_ITEMS: List[str] = [
        "DECENT/BFR LDG CHECK:",
        "",
        "LAND/TAXI LIGHTS... AS REQUIRED",
        "ALTIMETER... SET",
        "NAV AIDS... SET",
        "DEFOG... AS REQUIRED",
        "",
        "LANDING:",
        "",
        "LG... DN",
        "HOOK... DN (AS REQUIRED)",
        "LAND/TAXI LIGHTS... AS REQUIRED",
        "APC... AS DESIRED",
    ]
    _POST_LANDING_ITEMS: List[str] = [
        "ASE... SAFE",
        "LAND/TAXI LIGHTS... AS REQUIRED",
        "",
        "ENGINE SHUTDOWN:",
        "",
        "PARKING BRAKE... ON",
        "HMD... OFF",
        "VS BIT MP-32...",
        "FCS/ENG... RESET",
        "AR DOORS... OPEN IF USED",
        "SMS... CLEAR",
        "WBDS... OPEN",
        "CM DOORS... AS REQUIRED",
        "MIP SWITCHES... SAFE",
        "BUR... SET TO T/R",
        "ENG OIL... CONFIRM > 6 QTS",
        "ENGINE... OFF",
        "CANOPY... OPEN",
        "BATT... OFF",
        "PIC/SSK/HMD... DISCONNECT",
        "THROTTLE... FULL FORWARD",
    ]
    _CHECKLIST_TITLE_BY_LABEL: Dict[str, str] = {
        "L1": "COCKPIT CHECK",
        "L2": "ENGINE START",
        "L3": "TAXI CHECK",
        "L4": "TAKE OFF",
        "L5": "LANDING",
        "L6": "POST LANDING",
    }

    def __init__(self) -> None:
        self._selected_checklist_label: str = "L1"
        self._scroll_by_label: Dict[str, int] = {k: 0 for k in self._CHECKLIST_TITLE_BY_LABEL.keys()}
        self._popup_anchor_portal_idx: int = 0

    def _set_popup_anchor_portal_index(self, portal_index: Optional[int]) -> None:
        try:
            idx = int(portal_index) if portal_index is not None else int(self._popup_anchor_portal_idx)
        except Exception:
            idx = 0
        self._popup_anchor_portal_idx = max(0, min(3, idx))

    @staticmethod
    def _max_visible_lines() -> int:
        return 25

    def _checklist_lines(self, label: str) -> List[str]:
        return {
            "L1": self._COCKPIT_ITEMS,
            "L2": self._ENGINE_START_ITEMS,
            "L3": self._TAXI_ITEMS,
            "L4": self._TAKEOFF_ITEMS,
            "L5": self._LANDING_ITEMS,
            "L6": self._POST_LANDING_ITEMS,
        }.get(label, self._COCKPIT_ITEMS)

    def _max_scroll_for_label(self, label: str) -> int:
        total = len(self._checklist_lines(label))
        return max(0, total - self._max_visible_lines())

    def _scroll_for_label(self, label: str) -> int:
        try:
            raw = int(self._scroll_by_label.get(label, 0))
        except Exception:
            raw = 0
        bounded = max(0, min(self._max_scroll_for_label(label), raw))
        self._scroll_by_label[label] = bounded
        return bounded

    @staticmethod
    def _dot_fill(item: str, setting: str, width: int = 34) -> str:
        if not item:
            return ""
        if not setting:
            return item
        item = str(item).rstrip(". ").strip()
        setting = str(setting).strip()
        if item == "" or setting == "":
            return f"{item}{setting}"
        base_len = len(item) + len(setting)
        dots = max(1, width - base_len - 2)
        return f"{item}{'.' * dots}{setting}"

    def _format_checklist_line(self, line: str) -> str:
        text = str(line or "")
        if text.strip() == "":
            return ""
        if text.strip().endswith(":"):
            return text
        if "..." in text:
            left, right = text.split("...", 1)
            left = left.strip()
            right = right.strip()
            if right == "":
                # Keep raw trailing-dot checklist items as authored.
                return text
            return self._dot_fill(left, right, 34)
        return text

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
            if idx == 7:
                return pygame.Rect(rect.x, rect.bottom - DISPLAY_OSB_H, GRID_CELL_W, DISPLAY_OSB_H)
            if idx < 1 or idx > side_count:
                return None
            return pygame.Rect(rect.x, rect.y + top_offset + (idx - 1) * DISPLAY_OSB_H, GRID_CELL_W, DISPLAY_OSB_H)
        if side == "R":
            if idx == 7:
                return pygame.Rect(rect.right - GRID_CELL_W, rect.bottom - DISPLAY_OSB_H, GRID_CELL_W, DISPLAY_OSB_H)
            if idx < 1 or idx > side_count:
                return None
            return pygame.Rect(rect.right - GRID_CELL_W, rect.y + top_offset + (idx - 1) * DISPLAY_OSB_H, GRID_CELL_W, DISPLAY_OSB_H)
        return None

    def render(self, surface, rect, is_primary: bool, context: FormatContext) -> None:
        self._set_popup_anchor_portal_index(getattr(context, "portal_index", None))
        prev_clip = surface.get_clip()
        surface.set_clip(rect)
        pygame.draw.rect(surface, (0, 255, 255), rect, 1)

        if not is_primary:
            bottom_font = get_font(18)
            bottom = bottom_font.render("CKLST", True, (0, 255, 255))
            br = bottom.get_rect(centerx=rect.centerx)
            br.bottom = rect.bottom - 2
            surface.blit(bottom, br)
            surface.set_clip(prev_clip)
            return

        cyan = (0, 255, 255)
        green = (0, 255, 0)
        gray = (128, 128, 128)

        # Left OSB labels L1-L6.
        osb_labels = {
            "L1": "COCKPIT\nCHECK",
            "L2": "ENGINE\nSTART",
            "L3": "TAXI\nCHECK",
            "L4": "TAKE\nOFF",
            "L5": "LANDING",
            "L6": "POST\nLANDING",
        }
        for label, text in osb_labels.items():
            box = self._osb_box(rect, label)
            if box is None:
                continue
            font = get_font(14)
            lines = text.split("\n")
            flashing = context.is_osb_flashing(label)
            base_color = gray if label == self._selected_checklist_label else cyan
            rendered = [font.render(line, True, (0, 0, 0) if flashing else base_color) for line in lines]
            total_h = sum(s.get_height() for s in rendered) + max(0, len(rendered) - 1)
            y = box.centery - total_h // 2
            rects: List[pygame.Rect] = []
            for surf in rendered:
                r = surf.get_rect()
                r.left = box.left + OSB_PADDING
                r.y = y
                rects.append(r)
                surface.blit(surf, r)
                y += surf.get_height() + 1
            if flashing and rects:
                flash_rect = rects[0].copy()
                for rr in rects[1:]:
                    flash_rect.union_ip(rr)
                pygame.draw.rect(surface, (255, 255, 255), flash_rect.inflate(4, 2))
                for surf, rr in zip(rendered, rects):
                    surface.blit(surf, rr)

        # Heading below T2.
        scroll_idx = self._scroll_for_label(self._selected_checklist_label)
        max_scroll = self._max_scroll_for_label(self._selected_checklist_label)
        dec_enabled = scroll_idx > 0
        inc_enabled = scroll_idx < max_scroll
        t2_box = self._osb_box(rect, "T2")
        t3_box = self._osb_box(rect, "T3")
        def _draw_side_dec_inc_symbol(box: pygame.Rect, *, is_left: bool, enabled: bool, flashing: bool) -> None:
            base_color = cyan if enabled else gray
            draw_color = (0, 0, 0) if flashing else base_color
            tri_w = max(10, box.width // 3)
            tri_h = max(10, box.height // 3)
            cx = box.centerx
            cy = box.top + OSB_PADDING + (tri_h // 2)
            if is_left:
                pts = [(cx - tri_w // 2, cy), (cx + tri_w // 2, cy - tri_h // 2), (cx + tri_w // 2, cy + tri_h // 2)]
            else:
                pts = [(cx + tri_w // 2, cy), (cx - tri_w // 2, cy - tri_h // 2), (cx - tri_w // 2, cy + tri_h // 2)]
            if flashing:
                flash_rect = pygame.Rect(cx - tri_w // 2 - 3, cy - tri_h // 2 - 3, tri_w + 6, tri_h + 6)
                pygame.draw.rect(surface, (255, 255, 255), flash_rect)
            pygame.draw.polygon(surface, draw_color, pts, 0)

        if t2_box is not None:
            _draw_side_dec_inc_symbol(
                t2_box,
                is_left=True,
                enabled=dec_enabled,
                flashing=bool(context.is_osb_flashing("T2")),
            )
        if t3_box is not None:
            _draw_side_dec_inc_symbol(
                t3_box,
                is_left=False,
                enabled=inc_enabled,
                flashing=bool(context.is_osb_flashing("T3")),
            )

        heading_font = get_font(16)
        checklist_title = self._CHECKLIST_TITLE_BY_LABEL.get(self._selected_checklist_label, "COCKPIT CHECK")
        heading = heading_font.render(checklist_title, True, green)
        list_left = rect.left + GRID_CELL_W + 6
        list_right = rect.right - GRID_CELL_W - 6
        _list_center_x = (list_left + list_right) // 2 + 20
        list_block_left_x = rect.left + GRID_CELL_W + 10
        heading_x = list_block_left_x
        heading_y = rect.top + GRID_CELL_H - 1
        surface.blit(heading, (heading_x, heading_y))

        # Gray checklist list, left aligned in content area.
        y = heading_y + heading.get_height() + 8
        # Only reserve bottom OSB row when this portal actually has bottom OSBs (5x7/10x7).
        has_bottom_osbs = rect.height >= int(7 * DPI) - 1
        bottom_limit = rect.bottom - (GRID_CELL_H + 4 if has_bottom_osbs else 4)
        visible_slots = self._max_visible_lines()
        available_h = max(1, bottom_limit - y)
        target_row_h = max(1, available_h // max(1, visible_slots))
        list_font = get_font(max(8, min(15, target_row_h - 1)))
        row_h = target_row_h
        checklist_items = self._checklist_lines(self._selected_checklist_label)
        visible = checklist_items[scroll_idx:scroll_idx + visible_slots]
        for idx, line in enumerate(visible):
            line_y = y + (idx * row_h)
            formatted_line = self._format_checklist_line(line)
            if not formatted_line:
                continue
            surf = list_font.render(formatted_line, True, gray)
            r = surf.get_rect(x=list_block_left_x, y=line_y)
            surface.blit(surf, r)

        surface.set_clip(prev_clip)

    def on_osb(self, label: str, context: FormatContext) -> bool:
        self._set_popup_anchor_portal_index(getattr(context, "portal_index", None))
        if label == "T1":
            context.request_vded(context.portal_index, "MENU")
            return True
        if label == "T2":
            curr = self._scroll_for_label(self._selected_checklist_label)
            self._scroll_by_label[self._selected_checklist_label] = max(0, curr - 1)
            return True
        if label == "T3":
            curr = self._scroll_for_label(self._selected_checklist_label)
            max_scroll = self._max_scroll_for_label(self._selected_checklist_label)
            self._scroll_by_label[self._selected_checklist_label] = min(max_scroll, curr + 1)
            return True
        if label in {"L1", "L2", "L3", "L4", "L5", "L6"}:
            self._selected_checklist_label = label
            return True
        return False
