#!/usr/bin/env python3
"""CSS viewport estimation and style scaling helpers."""

from __future__ import annotations

import copy
import re


def _scale_css_styles_px(theme: dict, scale: float) -> dict:
    """Scale px-based css lengths in theme['styles'] by a factor."""
    if not theme or not isinstance(theme, dict):
        return theme
    out = copy.deepcopy(theme)
    styles = out.get('styles') if isinstance(out, dict) else None
    if not isinstance(styles, dict):
        return out

    px_re = re.compile(r"(?P<num>-?\d+(?:\.\d+)?)px")

    def repl(m):
        try:
            v = float(m.group('num')) * float(scale)
            if abs(v - round(v)) < 1e-6:
                return f"{int(round(v))}px"
            return f"{v:.2f}px"
        except Exception:
            return m.group(0)

    for k, v in list(styles.items()):
        if isinstance(v, str):
            styles[k] = px_re.sub(repl, v)
    return out


def estimate_css_viewport_width_height(data: dict, theme: dict) -> tuple:
    """Heuristic viewport estimator used for css rendering.

    Returns: (width, height, explicit_width)
    """
    try:
        headers = data.get('headers', []) or []
        rows = data.get('rows', []) or []
        ncols = max(1, len(headers))
        nrows = max(1, len(rows))

        styles = (theme or {}).get('styles', {}) if isinstance(theme, dict) else {}

        def _num_px(s, default):
            if not isinstance(s, str):
                return float(default)
            m = re.search(r"(\d+(?:\.\d+)?)px", s)
            if not m:
                return float(default)
            try:
                return float(m.group(1))
            except Exception:
                return float(default)

        fs = _num_px(styles.get('font_size', '16px'), 16)
        px = _num_px(styles.get('padding_x', '12px'), 12)
        py = _num_px(styles.get('padding_y', '8px'), 8)
        border = _num_px(styles.get('border_width', '1px'), 1)
        title_fs = _num_px(styles.get('title_size', '28px'), 28)
        footer_fs = _num_px(styles.get('footer_size', '14px'), 14)

        sample_text = ''
        for r in rows[: min(20, len(rows))]:
            if isinstance(r, dict) and 'cells' in r:
                cells = r['cells']
            else:
                cells = r
            for c in cells[: min(10, len(cells))]:
                if isinstance(c, dict):
                    t = str(c.get('text', ''))
                else:
                    t = str(c)
                if len(t) > len(sample_text):
                    sample_text = t
        avg_chars = max(6, min(26, int((len(sample_text) * 0.6) if sample_text else 12)))

        char_w = fs * 0.58
        col_w = max(90, int(avg_chars * char_w + px * 2 + border * 2))
        width = int(ncols * col_w + border * (ncols + 1))
        width = max(560, min(2400, width))

        explicit_width = False
        params = (theme or {}).get('params', {}) if isinstance(theme, dict) else {}
        if isinstance(params, dict) and params.get('table_width'):
            explicit_width = True

        row_h = int(fs * 1.25 + py * 2 + border * 2)
        header_h = int(row_h * 1.2)
        title_h = int(title_fs * 1.5) if data.get('title') else 0
        footer_h = int(footer_fs * 1.7) if data.get('footer') else 0
        height = int(title_h + header_h + nrows * row_h + footer_h + 24)
        height = max(220, min(6000, height))
        return width, height, explicit_width
    except Exception:
        return 1200, 800, False


def _inject_wrap_gap_css(html: str, gap_px: int) -> str:
    """Inject per-line vertical gap for multi-line cell content in CSS mode."""
    try:
        if not html or gap_px <= 0:
            return html
        marker = "</style>"
        css = (
            "\n/* zentable wrap-gap injection */\n"
            f".wrapline + .wrapline {{ margin-top: {int(gap_px)}px; }}\n"
        )
        idx = html.find(marker)
        if idx >= 0:
            return html[:idx] + css + html[idx:]
        return html + "\n<style>" + css + "</style>\n"
    except Exception:
        return html
