from formats import *  # noqa: F401,F403
from format_bootstrap import DEFAULT_FORMAT_NAMES


class MenuVded(VdedBase):
    name: str = "MENU"

    def __init__(self) -> None:
        self.current_format = "UNKNOWN"

    def set_current_format(self, name: str) -> None:
        self.current_format = name

    def _build_layout(self) -> Dict[str, str]:
        cells: Dict[str, str] = {}
        labels: List[str] = []
        for row in "BCDEFGH":
            for col in range(1, 6):
                labels.append(f"{row}{col}")
        try:
            names = list(getattr(sys.modules.get("formats"), "FORMAT_NAMES", []))
        except Exception:
            names = []
        if len(names) <= 0:
            names = list(DEFAULT_FORMAT_NAMES)
        for label, name in zip(labels, names):
            cells[label] = name
        return cells

    def get_format_for_zone(self, label: str) -> Optional[str]:
        return self._build_layout().get(label)

    def render(self, surface, rect, context: FormatContext) -> None:
        grid = build_portal_grid()
        for cell in grid.values():
            cell_rect = pygame.Rect(
                rect.x + cell.rect.x,
                rect.y + cell.rect.y,
                cell.rect.width,
                cell.rect.height,
            )
            pygame.draw.rect(surface, (0, 255, 255), cell_rect, 1)

        a1 = grid["A1"]
        a1_rect = pygame.Rect(
            rect.x + a1.rect.x,
            rect.y + a1.rect.y,
            a1.rect.width,
            a1.rect.height,
        )
        a1_flashing = context.is_osb_flashing("A1")
        a1_font = get_font(16)
        a1_l1 = a1_font.render(self.current_format, True, (0, 0, 0) if a1_flashing else parse_hex_color("00FF00"))
        a1_l2 = a1_font.render("MENU", True, (0, 0, 0) if a1_flashing else parse_hex_color("FF00FF"))
        a1_r1 = a1_l1.get_rect(centerx=a1_rect.centerx, centery=a1_rect.centery - a1_l1.get_height() // 2)
        a1_r2 = a1_l2.get_rect(centerx=a1_rect.centerx, y=a1_r1.bottom + 1)
        if a1_flashing:
            pygame.draw.rect(surface, (255, 255, 255), a1_r1.union(a1_r2).inflate(4, 2))
        surface.blit(a1_l1, a1_r1)
        surface.blit(a1_l2, a1_r2)

        layout = self._build_layout()
        cell_font = get_font(16)
        for label, name in layout.items():
            cell = grid[label]
            cell_rect = pygame.Rect(
                rect.x + cell.rect.x,
                rect.y + cell.rect.y,
                cell.rect.width,
                cell.rect.height,
            )
            flashing = context.is_osb_flashing(label)
            lines = str(name).split("\n")
            rendered = [cell_font.render(line, True, (0, 0, 0) if flashing else parse_hex_color("00FFFF")) for line in lines]
            total_h = sum(s.get_height() for s in rendered) + max(0, len(rendered) - 1)
            y = int(cell_rect.centery - (total_h // 2))
            rects: List[pygame.Rect] = []
            for surf in rendered:
                text_rect = surf.get_rect(centerx=cell_rect.centerx)
                text_rect.y = y
                rects.append(text_rect)
                y += surf.get_height() + 1
            if flashing and len(rects) > 0:
                flash_rect = rects[0].copy()
                for r in rects[1:]:
                    flash_rect.union_ip(r)
                pygame.draw.rect(surface, (255, 255, 255), flash_rect.inflate(4, 2))
            for surf, text_rect in zip(rendered, rects):
                surface.blit(surf, text_rect)

    def on_zone(self, label: str, context: FormatContext) -> bool:
        if label == "A1":
            context.close_vded(context.portal_index)
            return True
        layout = self._build_layout()
        new_format = layout.get(label)
        if new_format is None:
            return False
        context.set_format(context.portal_index, new_format)
        context.close_vded(context.portal_index)
        return True
