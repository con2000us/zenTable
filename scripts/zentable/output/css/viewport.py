#!/usr/bin/env python3
"""Viewport/scaling helpers for CSS rendering."""

from __future__ import annotations

import re


MAX_VIEWPORT_DIM = 16384


def _parse_font_size_px(style_str: str, default: int = 14) -> int:
    if not style_str:
        return default
    m = re.search(r'font-size:\s*(\d+)px', style_str, re.I)
    return int(m.group(1)) if m else default


def _parse_width_px(style_str: str):
    if not style_str:
        return None
    for pat in (r'width:\s*(\d+)px', r'min-width:\s*(\d+)px'):
        m = re.search(pat, style_str, re.I)
        if m:
            return int(m.group(1))
    return None


def _scale_css_styles_px(theme: dict, scale: float) -> dict:
    """將 CSS 主題 styles 內所有 px 數值按倍率縮放。"""
    try:
        s = float(scale)
    except Exception:
        return theme
    if abs(s - 1.0) < 1e-6:
        return theme

    styles = (theme or {}).get("styles", {})
    if not isinstance(styles, dict) or not styles:
        return theme

    def scale_px_values(style_str: str) -> str:
        if not isinstance(style_str, str) or "px" not in style_str:
            return style_str

        def repl(m):
            num = float(m.group(1))
            return f"{int(round(num * s))}px"

        return re.sub(r"(-?[0-9]*\.?[0-9]+)px", repl, style_str)

    scaled_styles = {k: scale_px_values(v) for k, v in styles.items()}
    new_theme = dict(theme or {})
    new_theme["styles"] = scaled_styles
    return new_theme


def estimate_css_viewport_width_height(data: dict, theme: dict, measure_text_width, row_cells, cell_text) -> tuple:
    """依表格內容估算 CSS 截圖所需的 viewport 寬高。回傳 (width, height, explicit_width)。"""
    styles = theme.get("styles", {}) or {}
    header_fs = _parse_font_size_px(styles.get("th", ""), 18)
    cell_fs = _parse_font_size_px(styles.get("td", ""), 14)

    headers = data.get("headers", [])
    rows = data.get("rows", [])
    col_count = len(headers) if headers else 1

    col_widths = []
    for i in range(col_count):
        w = measure_text_width(headers[i] if i < len(headers) else "", header_fs)
        for row in rows:
            cells = row_cells(row)
            if i < len(cells):
                w = max(w, measure_text_width(cell_text(cells[i]), cell_fs))
        w = min(400, max(60, w + 28))
        col_widths.append(w)

    table_width = sum(col_widths)
    row_height = max(int(cell_fs * 2), 45)
    header_height = 55
    footer_height = 50

    width = 40 + table_width
    height = 50
    if data.get("title"):
        height += 60
    height += header_height + len(rows) * row_height + footer_height

    margin = 40
    scale_w, scale_h = 1.15, 1.25
    vw = int((width + margin) * scale_w)
    vh = int((height + margin) * scale_h)

    explicit_width = False
    _style_keys = {"body": ("body",), "container": ("container", ".container"), "table": ("table", ".data-table")}
    for _, try_keys in _style_keys.items():
        raw = ""
        for k in try_keys:
            raw = styles.get(k, "")
            if raw:
                break
        w = _parse_width_px(raw)
        if w is not None and w > vw:
            vw = min(w, MAX_VIEWPORT_DIM)
            explicit_width = True
    return (vw, min(vh, MAX_VIEWPORT_DIM), explicit_width)


def _inject_wrap_gap_css(html: str, gap_px: int) -> str:
    try:
        gap_px = max(0, int(gap_px))
    except Exception:
        gap_px = 0
    if gap_px <= 0:
        return html
    css = (
        f"\nhtml, body {{ width: calc(100% - {gap_px}px) !important; margin: 0 {gap_px}px 0 0 !important; box-sizing: border-box; }}"
        f"\ntable {{ width: 100% !important; }}\n"
        f"\nhtml {{ -webkit-text-size-adjust: 100%; text-size-adjust: 100%; }}\n"
    )
    inject = f"\n<style id=\"zentable-wrap-gap\">{css}</style>\n"
    if "</head>" in html:
        return html.replace("</head>", inject + "</head>")
    return html + inject
