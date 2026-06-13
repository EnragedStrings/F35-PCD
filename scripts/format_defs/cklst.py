from formats import *  # noqa: F401,F403


class CklstFormat(FormatBase):
    name: str = "CKLST"

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

    def _draw_osb_multiline(
        self,
        surface: pygame.Surface,
        box: pygame.Rect,
        lines: List[str],
        color: Tuple[int, int, int],
        *,
        h_align: str,
        flashing: bool,
    ) -> None:
        font = get_font(14)
        rendered = [font.render(str(line), True, (0, 0, 0) if flashing else color) for line in lines]
        total_h = sum(s.get_height() for s in rendered) + max(0, len(rendered) - 1)
        y = box.centery - total_h // 2
        text_rects: List[pygame.Rect] = []
        for surf in rendered:
            if h_align == "left":
                rr = surf.get_rect()
                rr.left = box.left + OSB_PADDING
            elif h_align == "right":
                rr = surf.get_rect()
                rr.right = box.right - OSB_PADDING
            else:
                rr = surf.get_rect(centerx=box.centerx)
            rr.y = y
            text_rects.append(rr)
            y += surf.get_height() + 1
        if flashing and len(text_rects) > 0:
            flash_rect = text_rects[0].copy()
            for rr in text_rects[1:]:
                flash_rect.union_ip(rr)
            pygame.draw.rect(surface, (255, 255, 255), flash_rect.inflate(4, 2))
        for surf, rr in zip(rendered, text_rects):
            surface.blit(surf, rr)

    def render(self, surface, rect, is_primary: bool, context: FormatContext) -> None:
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
        white = (255, 255, 255)
        blue = (0, 0, 255)
        osb_spec: List[Tuple[str, str, Tuple[int, int, int], str]] = [
            ("R1", "EMER>", cyan, "right"),
            ("R2", "SPECL>", white, "right"),
            ("R3", "LIMITS>", white, "right"),
            ("L3", "NORM>", cyan, "left"),
            ("L4", "TACT>", white, "left"),
        ]
        for label, text, color, align in osb_spec:
            box = self._osb_box(rect, label)
            if box is None:
                continue
            self._draw_osb_multiline(
                surface,
                box,
                text.split("\n"),
                color,
                h_align=align,
                flashing=bool(context.is_osb_flashing(label)),
            )

        msg_font = get_font(18)
        msg = msg_font.render("Use paper checklist", True, blue)
        surface.blit(msg, (rect.left + int(1.0 * DPI), rect.top + int(0.5 * DPI)))
        surface.set_clip(prev_clip)

    def on_osb(self, label: str, context: FormatContext) -> bool:
        token = str(label).upper().strip()
        return token in {"R1", "R2", "R3", "L3", "L4"}

    def osb_is_interactive(self, label: str) -> bool:
        token = str(label).upper().strip()
        return token in {"T1", "R1", "R2", "R3", "L3", "L4"}
