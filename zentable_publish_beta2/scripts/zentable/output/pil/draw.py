#!/usr/bin/env python3
"""PIL text measurement/drawing helpers (mixed CJK + emoji)."""

from __future__ import annotations

from ...util.text import split_text_by_font
from ...util.color import parse_color
from . import font as pil_font


def measure_text_width(text: str, font_size: int) -> int:
    segments = split_text_by_font(str(text))
    total = 0
    for seg_text, font_type in segments:
        font = pil_font.get_font_emoji(font_size) if font_type == "emoji" else pil_font.get_font_cjk(font_size)
        try:
            bbox = font.getbbox(seg_text)
            total += bbox[2] - bbox[0]
        except Exception:
            total += font_size * len(seg_text) * 0.6
    return int(total)


def _fill_for_draw(fill_color, img_mode="RGB"):
    if isinstance(fill_color, (list, tuple)) and len(fill_color) >= 3:
        part = fill_color[:4] if len(fill_color) > 3 else fill_color[:3]
        out = tuple(int(x) for x in part)
        return out[:3] if img_mode == "RGB" and len(out) == 4 else out
    return (0, 0, 0)


def draw_text_with_mixed_fonts(draw, text, x, y, font_size, fill_color, baseline_offset=0, img_mode=None):
    if img_mode is None:
        img_mode = "RGB"
    fill = _fill_for_draw(fill_color, img_mode) if isinstance(fill_color, (list, tuple)) else _fill_for_draw(parse_color(str(fill_color)), img_mode)
    segments = split_text_by_font(str(text))
    current_x = x

    for segment_text, font_type in segments:
        if font_type == "emoji":
            font = pil_font.get_font_emoji(font_size)
            draw_y = y + 2
        else:
            font = pil_font.get_font_cjk(font_size)
            draw_y = y
        try:
            draw.text((current_x, draw_y), segment_text, font=font, fill=fill)
        except Exception:
            if font_type == "emoji":
                font = pil_font.get_font_cjk(font_size)
                draw.text((current_x, y), segment_text, font=font, fill=fill)
            else:
                raise
        try:
            width = font.getbbox(segment_text)[2] - font.getbbox(segment_text)[0]
        except Exception:
            width = int(font_size * len(segment_text) * 0.6)
        current_x += width

    return current_x


def _align_x(cell_left, cell_width, text_width, align, padding=10):
    if align == "right":
        return max(cell_left, cell_left + cell_width - padding - text_width)
    if align == "center":
        return cell_left + max(0, (cell_width - text_width) // 2)
    return cell_left + padding


def draw_text_aligned(draw, text, cell_left, y, cell_width, font_size, fill_color, align, img_mode=None):
    if img_mode is None:
        img_mode = "RGB"
    text_str = str(text)
    tw = measure_text_width(text_str, font_size)
    x = _align_x(cell_left, cell_width, tw, align)
    draw_text_with_mixed_fonts(draw, text_str, x, y, font_size, fill_color, img_mode=img_mode)
