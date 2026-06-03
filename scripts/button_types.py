from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, List, Optional, Tuple

import pygame

COLOR_GREEN = (0, 255, 0)
COLOR_CYAN = (0, 255, 255)
COLOR_WHITE = (255, 255, 255)
COLOR_GRAY = (128, 128, 128)
COLOR_BLACK = (0, 0, 0)


class ButtonType(str, Enum):
    STATUS_LABEL = "status_label"
    MOMENTARY_SINGLE = "momentary_single"
    BLIND_ROTARY = "blind_rotary"
    DOUBLE_FUNCTION = "double_function"
    TRIPLE_FUNCTION = "triple_function"
    GOL = "gol"
    GROUP_OPTION_LIST = "gol"  # Alias for legacy callsites.
    PAGE_ACCESS = "page_access"
    DATA_ENTRY = "data_entry"
    SLIDER_BAR = "slider_bar"
    INC_DEC = "inc_dec"


@dataclass
class ButtonState:
    button_id: str
    button_type: ButtonType
    text: str = ""
    enabled: bool = True
    flash_until_ms: int = 0

    # Single-function / momentary
    is_single_function: bool = False
    is_on: bool = False

    # Shared option state (rotary / double / triple / GOL)
    options: List[str] = field(default_factory=list)
    selected_index: Optional[int] = None
    off_allowed: bool = False

    # Optional static label for multi-function / GOL
    function_label: Optional[str] = None
    function_label_color: Optional[Tuple[int, int, int]] = None
    h_align: str = "center"  # center | left | right
    v_align: str = "center"  # center | top
    padding: int = 2
    font_size: int = 16
    # Centralized behavior policy: when True, button action should be
    # executed after the flash interval instead of immediately.
    execute_after_flash: Optional[bool] = None


def _draw_text_lines(
    surface: pygame.Surface,
    rect: pygame.Rect,
    lines: List[Tuple[str, Tuple[int, int, int]]],
    get_font: Callable[[int], pygame.font.Font],
    now_ms: int,
    flash_until_ms: int,
    font_size: int = 16,
    h_align: str = "center",
    v_align: str = "center",
    padding: int = 2,
) -> None:
    font = get_font(font_size)
    rendered = [font.render(text, True, color) for text, color in lines]
    total_h = sum(r.get_height() for r in rendered) + max(0, len(rendered) - 1)
    if v_align == "top":
        y = rect.top + padding
    else:
        y = rect.centery - total_h // 2
    text_rects: List[pygame.Rect] = []
    for surf in rendered:
        if h_align == "left":
            r = surf.get_rect()
            r.left = rect.left + padding
        elif h_align == "right":
            r = surf.get_rect()
            r.right = rect.right - padding
        else:
            r = surf.get_rect(centerx=rect.centerx)
        r.y = y
        text_rects.append(r)
        y += surf.get_height() + 1

    flashing = _is_flashing(flash_until_ms, now_ms)
    if flashing and text_rects:
        flash_rect = text_rects[0].copy()
        for r in text_rects[1:]:
            flash_rect.union_ip(r)
        flash_rect.inflate_ip(4, 2)
        pygame.draw.rect(surface, COLOR_WHITE, flash_rect)
        rendered = [font.render(lines[i][0], True, COLOR_BLACK) for i in range(len(lines))]

    for surf, r in zip(rendered, text_rects):
        surface.blit(surf, r)


def _draw_box_around_lines(surface: pygame.Surface, rects: List[pygame.Rect]) -> None:
    if not rects:
        return
    box = rects[0].copy()
    for r in rects[1:]:
        box.union_ip(r)
    box.inflate_ip(4, 2)
    pygame.draw.rect(surface, COLOR_WHITE, box, 1)


def _is_flashing(flash_until_ms: int, now_ms: int) -> bool:
    # Backward compatible flashing semantics:
    # - Absolute timer mode: flash_until_ms is a future tick timestamp.
    # - Boolean mode: legacy callsites pass 1 when already in flashing phase.
    return bool(int(flash_until_ms) == 1 or int(flash_until_ms) > int(now_ms))


def render_button(
    surface: pygame.Surface,
    rect: pygame.Rect,
    state: ButtonState,
    get_font: Callable[[int], pygame.font.Font],
    now_ms: int,
) -> None:
    unavailable = not state.enabled

    if state.button_type == ButtonType.STATUS_LABEL:
        color = COLOR_GRAY if unavailable else COLOR_GREEN
        lines = [(line, color) for line in state.text.split("\n")]
        _draw_text_lines(
            surface,
            rect,
            lines,
            get_font,
            now_ms,
            state.flash_until_ms,
            font_size=state.font_size,
            h_align=state.h_align,
            v_align=state.v_align,
            padding=state.padding,
        )
        return

    if state.button_type == ButtonType.PAGE_ACCESS:
        color = COLOR_GRAY if unavailable else COLOR_CYAN
        lines = [(line, color) for line in state.text.split("\n")]
        _draw_text_lines(
            surface,
            rect,
            lines,
            get_font,
            now_ms,
            state.flash_until_ms,
            font_size=state.font_size,
            h_align=state.h_align,
            v_align=state.v_align,
            padding=state.padding,
        )
        return

    if state.button_type == ButtonType.MOMENTARY_SINGLE:
        if state.is_single_function:
            color = COLOR_GRAY if unavailable else (COLOR_WHITE if state.is_on else COLOR_CYAN)
            lines = [(line, color) for line in state.text.split("\n")]
            _draw_text_lines(
                surface,
                rect,
                lines,
                get_font,
                now_ms,
                state.flash_until_ms,
                font_size=state.font_size,
                h_align=state.h_align,
                v_align=state.v_align,
                padding=state.padding,
            )
            if state.is_on and (not _is_flashing(state.flash_until_ms, now_ms)) and not unavailable:
                font = get_font(state.font_size)
                rendered = [font.render(line, True, color) for line in state.text.split("\n")]
                total_h = sum(r.get_height() for r in rendered) + max(0, len(rendered) - 1)
                if state.v_align == "top":
                    y = rect.top + state.padding
                else:
                    y = rect.centery - total_h // 2
                line_rects: List[pygame.Rect] = []
                for surf in rendered:
                    if state.h_align == "left":
                        rr = surf.get_rect()
                        rr.left = rect.left + state.padding
                    elif state.h_align == "right":
                        rr = surf.get_rect()
                        rr.right = rect.right - state.padding
                    else:
                        rr = surf.get_rect(centerx=rect.centerx)
                    rr.y = y
                    line_rects.append(rr)
                    y += surf.get_height() + 1
                _draw_box_around_lines(surface, line_rects)
        else:
            color = COLOR_GRAY if unavailable else COLOR_CYAN
            lines = [(line, color) for line in state.text.split("\n")]
            _draw_text_lines(
                surface,
                rect,
                lines,
                get_font,
                now_ms,
                state.flash_until_ms,
                font_size=state.font_size,
                h_align=state.h_align,
                v_align=state.v_align,
                padding=state.padding,
            )
        return

    if state.button_type == ButtonType.BLIND_ROTARY:
        text = ""
        if state.options:
            idx = 0 if state.selected_index is None else max(0, min(len(state.options) - 1, state.selected_index))
            text = state.options[idx]
        color = COLOR_GRAY if unavailable else COLOR_WHITE
        _draw_text_lines(
            surface,
            rect,
            [(text, color)],
            get_font,
            now_ms,
            state.flash_until_ms,
            font_size=state.font_size,
            h_align=state.h_align,
            v_align=state.v_align,
            padding=state.padding,
        )
        return

    if state.button_type in (ButtonType.DOUBLE_FUNCTION, ButtonType.TRIPLE_FUNCTION):
        font = get_font(state.font_size)
        display_lines: List[Tuple[str, Tuple[int, int, int], bool]] = []
        if state.function_label:
            label_color = state.function_label_color if state.function_label_color is not None else COLOR_GREEN
            display_lines.append((state.function_label, label_color if not unavailable else COLOR_GRAY, False))
        for idx, option in enumerate(state.options):
            selected = state.selected_index == idx
            color = COLOR_GRAY if unavailable else (COLOR_WHITE if selected else COLOR_CYAN)
            display_lines.append((option, color, selected))
        rendered = [font.render(text, True, color) for text, color, _ in display_lines]
        total_h = sum(r.get_height() for r in rendered) + max(0, len(rendered) - 1)
        if state.v_align == "top":
            y = rect.top + state.padding
        else:
            y = rect.centery - total_h // 2
        flashing = _is_flashing(state.flash_until_ms, now_ms)
        for (text, color, selected), surf in zip(display_lines, rendered):
            if flashing:
                surf = font.render(text, True, COLOR_BLACK)
            if state.h_align == "left":
                text_rect = surf.get_rect()
                text_rect.left = rect.left + state.padding
            elif state.h_align == "right":
                text_rect = surf.get_rect()
                text_rect.right = rect.right - state.padding
            else:
                text_rect = surf.get_rect(centerx=rect.centerx)
            text_rect.y = y
            if flashing:
                flash_rect = text_rect.inflate(4, 2)
                pygame.draw.rect(surface, COLOR_WHITE, flash_rect)
            elif selected and not unavailable:
                pygame.draw.rect(surface, COLOR_WHITE, text_rect.inflate(4, 2), 1)
            surface.blit(surf, text_rect)
            y += surf.get_height() + 1
        return

    if state.button_type == ButtonType.GOL:
        font = get_font(state.font_size)
        label_color = COLOR_GRAY if unavailable else COLOR_GREEN
        option_text = ""
        if state.options and state.selected_index is not None:
            option_text = state.options[max(0, min(len(state.options) - 1, state.selected_index))]
        option_color = COLOR_GRAY if unavailable else COLOR_WHITE
        lines: List[Tuple[str, Tuple[int, int, int]]] = []
        if state.function_label:
            lines.append((state.function_label, label_color))
        lines.append((option_text, option_color))
        rendered = [font.render(text, True, color) for text, color in lines]
        total_h = sum(r.get_height() for r in rendered) + max(0, len(rendered) - 1)
        if state.v_align == "top":
            y = rect.top + state.padding
        else:
            y = rect.centery - total_h // 2

        flashing = _is_flashing(state.flash_until_ms, now_ms)
        text_rects: List[pygame.Rect] = []
        for surf in rendered:
            if state.h_align == "left":
                tr = surf.get_rect()
                tr.left = rect.left + state.padding
            elif state.h_align == "right":
                tr = surf.get_rect()
                tr.right = rect.right - state.padding
            else:
                tr = surf.get_rect(centerx=rect.centerx)
            tr.y = y
            text_rects.append(tr)
            y += surf.get_height() + 1

        if flashing and text_rects:
            flash_rect = text_rects[0].copy()
            for tr in text_rects[1:]:
                flash_rect.union_ip(tr)
            flash_rect.inflate_ip(4, 2)
            pygame.draw.rect(surface, COLOR_WHITE, flash_rect)
            rendered = [font.render(lines[i][0], True, COLOR_BLACK) for i in range(len(lines))]

        for surf, tr in zip(rendered, text_rects):
            surface.blit(surf, tr)

        # Underline the first line exactly where it was rendered.
        if state.function_label and (not unavailable) and (not flashing) and text_rects:
            head = text_rects[0]
            pygame.draw.line(surface, label_color, (head.left, head.bottom + 1), (head.right, head.bottom + 1), 1)
        return


def activate_button(state: ButtonState, now_ms: int, flash_ms: int = 250) -> Optional[str]:
    if not state.enabled:
        return None

    state.flash_until_ms = now_ms + flash_ms

    if state.button_type == ButtonType.MOMENTARY_SINGLE:
        if state.is_single_function:
            state.is_on = not state.is_on
            return "toggle"
        return "momentary"

    if state.button_type == ButtonType.BLIND_ROTARY:
        if state.options:
            idx = state.selected_index or 0
            state.selected_index = (idx + 1) % len(state.options)
        return "rotate"

    if state.button_type in (ButtonType.DOUBLE_FUNCTION, ButtonType.TRIPLE_FUNCTION):
        n = len(state.options)
        if n == 0:
            return None
        if state.selected_index is None:
            state.selected_index = 0
            return "select"
        next_idx = state.selected_index + 1
        if next_idx >= n:
            state.selected_index = None if state.off_allowed else 0
        else:
            state.selected_index = next_idx
        return "cycle"

    if state.button_type == ButtonType.GOL:
        return "open_gol"

    if state.button_type == ButtonType.PAGE_ACCESS:
        return "page_access"

    return "pressed"


def button_executes_after_flash(state: ButtonState) -> bool:
    # Explicit override always wins.
    if state.execute_after_flash is not None:
        return bool(state.execute_after_flash)
    # Labels never execute actions.
    if state.button_type == ButtonType.STATUS_LABEL:
        return False
    # Standardized policy: all actionable buttons execute after flash unless
    # a specific caller overrides with execute_after_flash=False.
    return True


def button_action_due_ms(state: ButtonState, now_ms: int) -> int:
    if not button_executes_after_flash(state):
        return int(now_ms)
    return int(max(int(now_ms), int(state.flash_until_ms)))
