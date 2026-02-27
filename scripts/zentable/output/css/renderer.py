#!/usr/bin/env python3
"""CSS HTML generation helpers."""

from __future__ import annotations

import json
import re
import html as html_module

from ...transform.cell import _row_cells, normalize_cell
from ...transform.highlight import resolve_cell_highlight


def _strip_alpha_from_css(css_text: str) -> str:
    """Convert #RRGGBBAA to #RRGGBB for border colors where needed."""
    if not css_text:
        return css_text
    return re.sub(r"#([0-9a-fA-F]{6})([0-9a-fA-F]{2})", r"#\1", css_text)


def build_css_rows_html(
    rows,
    theme: dict = None,
    headers: list = None,
    highlight_rules: list = None,
    col_hl: dict = None,
) -> str:
    """輸出 tbody rows，支援 colspan/rowspan、row_hl、cell.hl、col_hl、highlight_rules。"""
    rows_list = rows if isinstance(rows, list) else []
    use_hl = bool(theme and isinstance(theme.get("highlight_styles"), dict))
    rules = highlight_rules if isinstance(highlight_rules, list) else []
    col_hl_map = col_hl if isinstance(col_hl, dict) else None
    header_list = headers if isinstance(headers, list) else []
    rows_html = []
    active_rowspans = []
    for idx, row in enumerate(rows_list):
        row_class = "row tr_even" if idx % 2 == 0 else "row tr_odd"
        row_hl = row.get("row_hl") if isinstance(row, dict) and "cells" in row else None
        raw_cells = _row_cells(row)
        row_cells = []
        col_cursor = 0
        col_idx = 0
        for raw_cell in raw_cells:
            while col_cursor < len(active_rowspans) and active_rowspans[col_cursor] > 0:
                col_cursor += 1
            cell = normalize_cell(raw_cell)
            attrs = []
            if cell["colspan"] > 1:
                attrs.append(f'colspan="{cell["colspan"]}"')
            if cell["rowspan"] > 1:
                attrs.append(f'rowspan="{cell["rowspan"]}"')
            if use_hl:
                col_name = header_list[col_idx] if col_idx < len(header_list) else None
                hl_token = resolve_cell_highlight(
                    cell, row_hl, theme,
                    col_name=col_name,
                    highlight_rules=rules,
                    col_hl=col_hl_map,
                )
                cls = f"hl hl-{hl_token}"
                attrs.append(f'class="{cls}"')
            col_idx += 1
            attr_str = f" {' '.join(attrs)}" if attrs else ""
            text_escaped = html_module.escape(cell["text"])
            row_cells.append(f'<td{attr_str}>{text_escaped}</td>')
            if cell["rowspan"] > 1:
                for i in range(cell["colspan"]):
                    target_idx = col_cursor + i
                    while target_idx >= len(active_rowspans):
                        active_rowspans.append(0)
                    active_rowspans[target_idx] = max(active_rowspans[target_idx], cell["rowspan"] - 1)
            col_cursor += cell["colspan"]
        for i in range(len(active_rowspans)):
            if active_rowspans[i] > 0:
                active_rowspans[i] -= 1
        rows_html.append(f'<tr class="{row_class}">{"".join(row_cells)}</tr>\n')
    return "".join(rows_html)


def generate_css_html(data: dict, theme: dict, transparent: bool = False, table_width_pct: int = None, tt: bool = False) -> str:
    template = theme.get("template", "")
    styles = theme.get("styles", {})
    css_background = styles.get("background", "transparent" if transparent else "#111")
    if transparent:
        css_background = "transparent"

    border_color = styles.get("border_color") or "#999"
    if isinstance(border_color, str) and len(border_color) == 9 and border_color.startswith("#"):
        border_color = border_color[:7]

    html_css = f"""
:root {{
  --tbl-border-color: {border_color};
}}
body {{
  margin: 0;
  background: {css_background};
  color: {styles.get('text_color', '#fff')};
  font-family: {styles.get('font_family', 'sans-serif')};
}}
.table-wrap {{
  padding: {styles.get('padding_y', '8px')} {styles.get('padding_x', '12px')};
  width: {str(table_width_pct) + '%' if table_width_pct else styles.get('table_width', 'auto')};
  margin: 0 auto;
}}
table {{
  width: 100%;
  border-collapse: collapse;
  border: {styles.get('border_width', '1px')} solid var(--tbl-border-color);
  table-layout: auto;
}}
th, td {{
  border: {styles.get('border_width', '1px')} solid var(--tbl-border-color);
  padding: {styles.get('cell_padding', '6px 10px')};
  font-size: {styles.get('font_size', '16px')};
  line-height: {styles.get('line_height', '1.4')};
  text-align: {styles.get('align', 'left')};
  vertical-align: middle;
  white-space: pre-wrap;
}}
thead th {{
  background: {styles.get('header_bg', '#1f2937')};
  color: {styles.get('header_color', '#fff')};
}}
"""

    title_html = f"<h1 style='font-size:{styles.get('title_size','28px')};margin:0 0 10px 0;'>{data.get('title','')}</h1>" if data.get('title') else ""
    footer_html = f"<div style='font-size:{styles.get('footer_size','14px')};margin-top:10px;'>{data.get('footer','')}</div>" if data.get('footer') else ""

    headers = data.get("headers", [])
    rows = data.get("rows", [])

    thead = "<thead><tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr></thead>" if headers else ""

    tbody_rows_html = build_css_rows_html(
        rows,
        theme=theme,
        headers=headers,
        highlight_rules=data.get("highlight_rules"),
        col_hl=data.get("col_hl"),
    )
    tbody = "<tbody>" + tbody_rows_html + "</tbody>"

    if template:
        html = template
        html = html.replace("{{CSS}}", html_css)
        html = html.replace("{{TITLE}}", title_html)
        html = html.replace("{{THEAD}}", thead)
        html = html.replace("{{TBODY}}", tbody)
        html = html.replace("{{FOOTER}}", footer_html)
        html = html.replace("{{DATA_JSON}}", json.dumps(data, ensure_ascii=False))
        return html

    return f"""<!doctype html>
<html><head><meta charset='utf-8'><style>{html_css}</style></head>
<body>
<div class='table-wrap'>
  {title_html}
  <table>{thead}{tbody}</table>
  {footer_html}
</div>
</body></html>"""
