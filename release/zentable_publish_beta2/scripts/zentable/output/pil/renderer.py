#!/usr/bin/env python3
"""PIL table renderer."""

from __future__ import annotations

from dataclasses import dataclass
from PIL import Image, ImageDraw

from ...util.color import parse_color
from ...transform.cell import _row_cells, cell_text
from . import font as pil_font
from . import draw as pil_draw


@dataclass
class PILStyle:
    bg_color: str = "#1a1a2e"
    text_color: str = "#ffffff"
    header_bg: str = "#0f3460"
    header_text: str = "#e94560"
    alt_row_color: str = "#16213e"
    border_color: str = "#4a5568"


def render_pil(data: dict, theme: dict, custom_params: dict = None) -> Image.Image:
    params = theme.get("params") or {}
    base_style = PILStyle(
        params.get("bg_color", "#1a1a2e"),
        params.get("text_color", "#ffffff"),
        params.get("header_bg", "#0f3460"),
        params.get("header_text", "#e94560"),
        params.get("alt_row_color", "#16213e"),
        params.get("border_color", "#4a5568"),
    )

    if custom_params:
        style = PILStyle(
            bg_color=custom_params.get('bg_color', base_style.bg_color),
            text_color=custom_params.get('text_color', base_style.text_color),
            header_bg=custom_params.get('header_bg', base_style.header_bg),
            header_text=custom_params.get('header_text', base_style.header_text),
            alt_row_color=custom_params.get('alt_row_color', base_style.alt_row_color),
            border_color=custom_params.get('border_color', base_style.border_color),
        )
    else:
        style = base_style
    merged_params = {**(params or {}), **(custom_params or {})}
    align = (merged_params.get("align") or merged_params.get("cell_align") or "left").lower().strip()
    if align not in ("left", "center", "right"):
        align = "left"
    header_align = (merged_params.get("header_align") or "center").lower().strip()
    if header_align not in ("left", "center", "right"):
        header_align = "center"

    headers = data.get("headers", [])
    rows = data.get("rows", [])

    col_count = len(headers) if headers else 1
    row_count = len(rows)
    header_font_size = merged_params.get('header_font_size', 18)
    cell_font_size = merged_params.get('font_size', 16)
    cell_padding = 20
    min_col_width, max_col_width = 60, 400
    padding = 20
    header_height = 50

    col_widths = []
    for i in range(col_count):
        w = pil_draw.measure_text_width(headers[i] if i < len(headers) else "", header_font_size)
        for row in rows:
            cells = _row_cells(row)
            if i < len(cells):
                w = max(w, pil_draw.measure_text_width(cell_text(cells[i]), cell_font_size))
        w = min(max_col_width, max(min_col_width, w + cell_padding))
        col_widths.append(w)

    cell_height = max(int(cell_font_size * 1.5), 30)
    title_block_height = 50 if data.get("title") else 0
    footer_block_height = 30
    bottom_extra = 10

    width = padding * 2 + sum(col_widths)
    height = padding * 2 + title_block_height + header_height + row_count * cell_height + footer_block_height + bottom_extra

    def has_alpha(c):
        return c.startswith('rgba(') or (c.startswith('#') and len(c) == 9)

    use_rgba = any(has_alpha(c) for c in [style.bg_color, style.header_bg, style.alt_row_color, style.border_color])
    img_mode_str = 'RGBA' if use_rgba else 'RGB'
    img = Image.new(img_mode_str, (width, height), parse_color(style.bg_color))
    draw = ImageDraw.Draw(img)

    pil_font.get_font_cjk(cell_font_size)
    pil_font.get_font_cjk(header_font_size)
    pil_font.get_font_emoji(cell_font_size)

    y = padding
    title_fill = parse_color(style.header_text)
    header_fill = parse_color(style.header_text)
    cell_fill = parse_color(style.text_color)

    if data.get("title"):
        draw.rectangle([padding, y, width-padding, y+40], fill=parse_color(style.header_bg))
        pil_draw.draw_text_aligned(draw, data["title"], padding, y+10, width - 2*padding, 22, title_fill, "center", img_mode=img_mode_str)
        y += 50

    draw.rectangle([padding, y, width-padding, y+header_height], fill=parse_color(style.header_bg))
    x_offset = padding
    for i, h in enumerate(headers):
        cw = col_widths[i] if i < len(col_widths) else 60
        pil_draw.draw_text_aligned(draw, h, x_offset, y+15, cw, header_font_size, header_fill, header_align, img_mode=img_mode_str)
        x_offset += cw
    y += header_height

    for idx, row in enumerate(rows):
        row_bg = style.alt_row_color if idx % 2 == 0 else style.bg_color
        draw.rectangle([padding, y, width-padding, y+cell_height], fill=parse_color(row_bg))
        draw.line([padding, y+cell_height, width-padding, y+cell_height], fill=parse_color(style.border_color))
        x_offset = padding
        for i, cell in enumerate(_row_cells(row)):
            cw = col_widths[i] if i < len(col_widths) else 60
            pil_draw.draw_text_aligned(draw, cell_text(cell), x_offset, y+10, cw, cell_font_size, cell_fill, align, img_mode=img_mode_str)
            x_offset += cw
        y += cell_height

    draw.rectangle([padding, y, width-padding, y+30], fill=parse_color(style.header_bg))
    footer_text = data.get("footer") or "Generated by ZenTable (PIL fallback)"
    pil_draw.draw_text_aligned(draw, footer_text, padding, y+8, width - 2*padding, 12, header_fill, "center", img_mode=img_mode_str)

    return img
