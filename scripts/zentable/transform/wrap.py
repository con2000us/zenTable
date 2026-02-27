#!/usr/bin/env python3
"""Smart wrapping transform."""

from __future__ import annotations

from typing import Optional, Tuple

from .cell import _row_cells


def _smart_wrap_text(text: str, limit: int) -> str:
    s = "" if text is None else str(text)
    if "\n" in s or len(s) <= limit:
        return s

    s = s.replace("/", "/\n").replace("?", "?\n").replace("&", "&\n").replace("=", "=\n")
    if "\n" in s:
        parts = []
        for seg in s.split("\n"):
            parts.append(_smart_wrap_text(seg, limit))
        return "\n".join(p for p in parts if p != "")

    punct = set("，。；：、,.;: ")
    out, cur = [], ""
    soft_cut = max(1, int(limit * 0.6))
    for ch in s:
        cur += ch
        if ch in punct and len(cur) >= soft_cut:
            out.append(cur.rstrip())
            cur = ""
        elif len(cur) >= limit:
            out.append(cur)
            cur = ""
    if cur:
        out.append(cur)
    return "\n".join(p for p in out if p)


def apply_smart_wrap(data: dict, width: Optional[int] = None) -> Tuple[dict, dict]:
    headers = list(data.get("headers", []) or [])
    rows = data.get("rows", []) or []
    if not headers or not rows:
        return data, {"applied": False, "reason": "no-data"}

    col_count = max(1, len(headers))
    base_width = int(width) if width else 600
    total_chars = max(24, int(base_width / 13))
    per_col = max(8, total_chars // col_count)

    changed_cells = 0
    new_rows = []
    for r in rows:
        cells = _row_cells(r)
        rr = []
        for i, c in enumerate(cells):
            limit = max(6, per_col - 2) if i == 0 else per_col
            if isinstance(c, dict):
                old_t = c.get("text", "")
                new_t = _smart_wrap_text(old_t, limit)
                if new_t != ("" if old_t is None else str(old_t)):
                    changed_cells += 1
                cc = dict(c)
                cc["text"] = new_t
                rr.append(cc)
            else:
                old_t = "" if c is None else str(c)
                new_t = _smart_wrap_text(old_t, limit)
                if new_t != old_t:
                    changed_cells += 1
                rr.append(new_t)
        if isinstance(r, dict) and "cells" in r:
            new_rows.append({"row_hl": r.get("row_hl"), "cells": rr})
        else:
            new_rows.append(rr)

    out = {"headers": headers, "rows": new_rows, "title": data.get("title", ""), "footer": data.get("footer", "")}
    return out, {
        "applied": changed_cells > 0,
        "changed_cells": changed_cells,
        "per_col_limit": per_col,
        "col_count": col_count,
        "base_width": base_width,
    }
