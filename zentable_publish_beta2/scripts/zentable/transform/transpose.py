#!/usr/bin/env python3
"""Table transpose operations."""

from __future__ import annotations

from .cell import cell_text


def transpose_table(data):
    headers = list(data.get("headers", []) or [])
    rows = [list(r) for r in (data.get("rows", []) or [])]

    if not headers:
        return {"headers": [], "rows": [], "title": data.get("title", ""), "footer": data.get("footer", "")}

    row_keys = []
    for r in rows:
        row_keys.append(cell_text(r[0]) if len(r) > 0 else "")

    out_headers = ["Field"] + row_keys

    out_rows = []
    for j, h in enumerate(headers):
        new_row = ["" if h is None else str(h)]
        for i, r in enumerate(rows):
            new_row.append(cell_text(r[j]) if j < len(r) else "")
        out_rows.append(new_row)

    return {"headers": out_headers, "rows": out_rows, "title": data.get("title", ""), "footer": data.get("footer", "")}
