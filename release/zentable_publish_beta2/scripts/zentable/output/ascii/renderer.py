#!/usr/bin/env python3
"""ASCII renderer module."""

from __future__ import annotations

import sys
from typing import Optional

from ...transform.cell import _row_cells, cell_text
from .charwidth import (
    calculate_column_widths,
    align_text,
    char_display_width,
    _space_width,
)

ASCII_STYLES = {
    "double": {
        "tl": "╔", "tr": "╗", "bl": "╚", "br": "╝",
        "h": "═", "v": "║",
        "tm": "╦", "bm": "╩", "mm": "╬",
        "header_l": "╠", "header_m": "╬", "header_r": "╣",
        "row_l": "╠", "row_m": "╬", "row_r": "╣",
        "footer_l": "╠", "footer_m": "╬", "footer_r": "╣",
        "header": "╠", "row": "╠", "footer": "╠"
    },
    "grid": {
        "tl": "┌", "tr": "┐", "bl": "└", "br": "┘",
        "h": "─", "v": "│",
        "tm": "┬", "bm": "┴", "mm": "┼",
        "header_l": "├", "header_m": "┼", "header_r": "┤",
        "row_l": "├", "row_m": "┼", "row_r": "┤",
        "footer_l": "├", "footer_m": "┼", "footer_r": "┤",
        "header": "├", "row": "├", "footer": "├"
    },
    "markdown": {
        "tl": "|", "tr": "|", "bl": "|", "br": "|",
        "h": "-", "v": "|",
        "tm": "|", "bm": "|", "mm": "|",
        "header_l": "|", "header_m": "|", "header_r": "|",
        "row_l": "|", "row_m": "|", "row_r": "|",
        "footer_l": "|", "footer_m": "|", "footer_r": "|",
        "header": "|", "row": "|", "footer": "|"
    }
}


def render_ascii(data: dict, theme: dict = None, style=None, calibration: dict = None, debug_details: dict = None) -> str:
    if style is None:
        raise ValueError("style is required")

    params = (theme or {}).get("params") or {}
    # when style passed in, still allow missing attrs fallback from params
    border_style = getattr(style, "border_style", params.get("style", "double"))
    padding = int(getattr(style, "padding", params.get("padding", 2)))
    align = getattr(style, "align", params.get("align", "left"))
    header_align = getattr(style, "header_align", params.get("header_align", "center"))

    cal = calibration
    if cal:
        cats = [k for k in ('ascii', 'cjk', 'box', 'emoji') if k in cal]
        custom_n = len(cal.get('custom', {}))
        print(
            f"📐 套用校準: 類別寬度={{{', '.join(f'{k}={cal[k]}' for k in cats)}}}"
            + (f", 自訂={custom_n}字元" if custom_n else ""),
            file=sys.stderr
        )

    headers = data.get("headers", [])
    rows = data.get("rows", [])
    title = data.get("title", "")
    footer = data.get("footer", "")

    raw_widths = calculate_column_widths(headers, rows, padding, cal, row_cells_fn=_row_cells, cell_text_fn=cell_text)

    s = ASCII_STYLES.get(border_style, ASCII_STYLES["double"])

    sw = _space_width(cal)
    if sw <= 0:
        sw = 1.0

    hch = s.get('h', '─')
    vch = s.get('v', '|')
    tm = s.get('tm', s.get('header', '+'))
    bm = s.get('bm', s.get('footer', '+'))
    header_l = s.get('header_l', s.get('header', '+'))
    header_m = s.get('header_m', s.get('header', '+'))
    header_r = s.get('header_r', s.get('header', '+'))

    hw = char_display_width(hch, cal)
    if hw <= 0:
        hw = 1.0

    col_h_counts = []
    col_targets = []
    for w in raw_widths:
        full_w = w + 2 * sw
        n = max(1, round(full_w / hw))
        col_h_counts.append(n)
        col_targets.append(max(0.0, n * hw - 2 * sw))

    def _cell_lines(v):
        ss = "" if v is None else str(v)
        ls = ss.splitlines()
        return ls if ls else [""]

    header_lines = [_cell_lines(h) for h in headers] if headers else []
    header_height = 0
    for i in range(min(len(col_targets), len(header_lines))):
        header_height = max(header_height, len(header_lines[i]))
    row_lines = [[_cell_lines(cell_text(c)) for c in _row_cells(row)] for row in rows]
    row_heights = []
    for r in row_lines:
        h = 1
        for i in range(min(len(col_targets), len(r))):
            h = max(h, len(r[i]))
        row_heights.append(h)

    if isinstance(debug_details, dict):
        debug_details.clear()
        debug_details.update({
            "border_style": border_style,
            "padding": padding,
            "align": align,
            "header_align": header_align,
            "h_char": hch,
            "v_char": vch,
            "space_width": sw,
            "h_char_width": hw,
            "raw_widths": raw_widths,
            "col_h_counts": col_h_counts,
            "col_targets": col_targets,
            "ncols": len(col_h_counts),
            "nrows": len(rows),
            "row_heights": row_heights,
            "header_height": header_height,
            "has_headers": bool(headers),
            "has_title": bool(title),
            "has_footer": bool(footer),
        })

    def _hseg(i: int) -> str:
        return hch * col_h_counts[i]

    def _build_top_line() -> str:
        parts = [_hseg(i) for i in range(len(col_h_counts))]
        return s['tl'] + tm.join(parts) + s['tr']

    def _build_bottom_line() -> str:
        parts = [_hseg(i) for i in range(len(col_h_counts))]
        return s['bl'] + bm.join(parts) + s['br']

    def _build_header_sep() -> str:
        parts = [_hseg(i) for i in range(len(col_h_counts))]
        return header_l + header_m.join(parts) + header_r

    def _align_chars(text: str, width: int, align_mode: str) -> str:
        text = "" if text is None else str(text)
        if width <= 0:
            return ""
        if len(text) > width:
            return text[:width]
        pad = width - len(text)
        if align_mode == "right":
            return (" " * pad) + text
        if align_mode == "center":
            left = pad // 2
            return (" " * left) + text + (" " * (pad - left))
        return text + (" " * pad)

    lines = []

    if title:
        top_probe = _build_top_line()
        inner_chars = max(0, len(top_probe) - 2)
        title_w_chars = max(0, inner_chars - 6)
        title_line = _align_chars(title, title_w_chars, "center")
        lines.append(f"{s['tl']}{hch * 2} {title_line} {hch * 2}{s['tr']}")

    lines.append(_build_top_line())

    if headers:
        header_height = 1
        for i in range(min(len(col_targets), len(header_lines))):
            header_height = max(header_height, len(header_lines[i]))
        for li in range(header_height):
            line_cells = []
            for i in range(min(len(col_targets), len(headers))):
                txt = header_lines[i][li] if i < len(header_lines) and li < len(header_lines[i]) else ""
                line_cells.append(f" {align_text(txt, col_targets[i], header_align, cal)} ")
            lines.append(vch + vch.join(line_cells) + vch)
        lines.append(_build_header_sep())

    for r_idx, row in enumerate(rows):
        row_cells_lines = row_lines[r_idx] if r_idx < len(row_lines) else []
        height = row_heights[r_idx] if r_idx < len(row_heights) else 1
        for li in range(height):
            cells = []
            for i in range(min(len(col_targets), len(row_cells_lines))):
                txt = row_cells_lines[i][li] if li < len(row_cells_lines[i]) else ""
                c = align_text(txt, col_targets[i], align, cal)
                cells.append(f" {c} ")
            lines.append(vch + vch.join(cells) + vch)

    lines.append(_build_bottom_line())

    if footer:
        bottom_probe = _build_bottom_line()
        inner_chars = max(0, len(bottom_probe) - 2)
        footer_w_chars = max(0, inner_chars - 6)
        footer_line = _align_chars(footer, footer_w_chars, "center")
        lines.append(f"{s['bl']}{hch * 2} {footer_line} {hch * 2}{s['br']}")

    return "\n".join(lines)
