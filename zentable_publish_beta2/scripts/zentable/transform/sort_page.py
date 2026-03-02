#!/usr/bin/env python3
"""Sorting and pagination transforms."""

from __future__ import annotations

import functools
import os
import re

from .cell import _row_cells, cell_text

ROWS_PER_PAGE = 15


def _parse_page_spec(spec: str):
    s = (spec or "").strip().lower()
    if not s:
        return ("single", 1, None)
    if s == "all":
        return ("all", 1, None)
    if re.fullmatch(r"\d+", s):
        return ("single", max(1, int(s)), None)

    m = re.fullmatch(r"(\d+)-(\d+)", s)
    if m:
        a = max(1, int(m.group(1)))
        b = max(1, int(m.group(2)))
        if a > b:
            raise ValueError(f"Invalid page range '{spec}': start must be <= end")
        return ("range", a, b)

    m = re.fullmatch(r"(\d+)-", s)
    if m:
        a = max(1, int(m.group(1)))
        return ("from", a, None)

    raise ValueError(f"Invalid --page '{spec}'. Supported: N, A-B, A-, all")


def _resolve_page_list(total_rows: int, per_page: int, page_spec: str = None, use_all: bool = False):
    total_rows = max(0, int(total_rows))
    per_page = max(1, int(per_page))
    total_pages = max(1, (total_rows + per_page - 1) // per_page)

    if use_all:
        return list(range(1, total_pages + 1)), total_pages

    kind, a, b = _parse_page_spec(page_spec or "1")
    if kind == "all":
        return list(range(1, total_pages + 1)), total_pages
    if kind == "single":
        if a > total_pages:
            raise ValueError(f"--page {a} exceeds total pages ({total_pages})")
        return [a], total_pages
    if kind == "range":
        if a > total_pages:
            raise ValueError(f"--page {a}-{b} exceeds total pages ({total_pages})")
        return list(range(a, min(b, total_pages) + 1)), total_pages

    if a > total_pages:
        raise ValueError(f"--page {a}- exceeds total pages ({total_pages})")
    return list(range(a, total_pages + 1)), total_pages


def _page_output_path(path: str, page: int, pages: list) -> str:
    if len(pages) <= 1:
        return path
    root, ext = os.path.splitext(path)
    if ext:
        return f"{root}.p{page}{ext}"
    return f"{path}.p{page}"


def _try_sort_numeric(value):
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    if s.endswith("%"):
        s = s[:-1].strip()
    s = s.replace(",", "")
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _parse_sort_specs(sort_by, sort_asc=True):
    if not sort_by:
        return []
    raw = str(sort_by).strip()
    if not raw:
        return []
    tokens = [t.strip() for t in re.split(r"[>,]", raw) if t.strip()]
    specs = []
    for tok in tokens:
        if ":" in tok:
            col, dir_token = tok.rsplit(":", 1)
            col = col.strip()
            d = dir_token.strip().lower()
            direction = "desc" if d in ("desc", "d", "-") else "asc"
        else:
            col = tok
            direction = "asc" if sort_asc else "desc"
        if col:
            specs.append((col, direction))
    return specs


def apply_sort_and_page(data, sort_by=None, sort_asc=True, page=1, per_page=ROWS_PER_PAGE):
    headers = data.get("headers", [])
    rows = data.get("rows", [])
    if sort_by and headers and rows:
        specs = _parse_sort_specs(sort_by, sort_asc=sort_asc)
        idx_specs = []
        for col_name, direction in specs:
            try:
                idx = headers.index(col_name)
                idx_specs.append((idx, direction))
            except ValueError:
                continue
        if not idx_specs:
            idx_specs = [(0, "asc" if sort_asc else "desc")]

        def cmp_rows(a, b):
            cells_a = _row_cells(a)
            cells_b = _row_cells(b)
            for idx, direction in idx_specs:
                va = cell_text(cells_a[idx]) if idx < len(cells_a) else ""
                vb = cell_text(cells_b[idx]) if idx < len(cells_b) else ""
                na = _try_sort_numeric(va)
                nb = _try_sort_numeric(vb)

                ka = 0 if na is not None else 1
                kb = 0 if nb is not None else 1
                if ka != kb:
                    return -1 if ka < kb else 1

                if ka == 0:
                    if na < nb:
                        c = -1
                    elif na > nb:
                        c = 1
                    else:
                        c = 0
                else:
                    sa = str(va).casefold()
                    sb = str(vb).casefold()
                    if sa < sb:
                        c = -1
                    elif sa > sb:
                        c = 1
                    else:
                        c = 0

                if c != 0:
                    return -c if direction == "desc" else c
            return 0

        rows = sorted(rows, key=functools.cmp_to_key(cmp_rows))

    start = (page - 1) * per_page
    end = start + per_page
    rows = rows[start:end]
    return {"headers": headers, "rows": rows, "title": data.get("title", ""), "footer": data.get("footer", "")}
