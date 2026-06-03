from formats import *  # noqa: F401,F403


class OfflineSensorFormat(FormatBase):
    def __init__(self, name: str) -> None:
        self.name = str(name).upper().strip()

    def render(self, surface, rect, is_primary: bool, context: FormatContext) -> None:
        prev_clip = surface.get_clip()
        surface.set_clip(rect)
        surface.fill((0, 0, 0), rect)
        label = f"{self.name} OFFLINE"
        font_size = 42 if is_primary else 18
        draw_centered_text(surface, rect, label, "00FF00", font_size)
        pygame.draw.rect(surface, (0, 255, 255), rect, 1)
        surface.set_clip(prev_clip)

    def on_osb(self, label: str, context: FormatContext) -> bool:
        return False
