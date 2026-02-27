#!/usr/bin/env python3
"""CSS HTML generation helpers."""

from __future__ import annotations

import json
import re


def _strip_alpha_from_css(css_text: str) -> str:
    """Convert #RRGGBBAA to #RRGGBB for border colors where needed."""
    if not css_text:
        return css_text
    return re.sub(r"#([0-9a-fA-F]{6})([0-9a-fA-F]{2})", r"#\1", css_text)


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

    body_rows = []
    for r in rows:
        cells = r.get('cells') if isinstance(r, dict) and 'cells' in r else r
        tds = []
        for c in cells:
            if isinstance(c, dict):
                txt = c.get('text', '')
                colspan = int(c.get('colspan', 1) or 1)
                rowspan = int(c.get('rowspan', 1) or 1)
                attrs = []
                if colspan > 1:
                    attrs.append(f"colspan=\"{colspan}\"")
                if rowspan > 1:
                    attrs.append(f"rowspan=\"{rowspan}\"")
                tds.append(f"<td {' '.join(attrs)}>{txt}</td>")
            else:
                tds.append(f"<td>{c}</td>")
        body_rows.append("<tr>" + "".join(tds) + "</tr>")

    tbody = "<tbody>" + "".join(body_rows) + "</tbody>"

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
