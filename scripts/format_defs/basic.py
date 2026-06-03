from formats import *  # noqa: F401,F403


class BasicFormat(FormatBase):
    def __init__(self, name: str) -> None:
        self.name = name

    def render(self, surface, rect, is_primary: bool, context: FormatContext) -> None:
        if is_primary:
            draw_centered_text(surface, rect, self.name, "00FFFF", 18)
        else:
            draw_centered_text(surface, rect, f"{self.name} (SUB)", "00FFFF", 14)

    def on_osb(self, label: str, context: FormatContext) -> bool:
        if label == "T1":
            context.request_vded(context.portal_index, "MENU")
            return True
        return False
