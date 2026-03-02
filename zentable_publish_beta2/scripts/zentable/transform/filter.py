#!/usr/bin/env python3
"""Row/column filter utilities."""

from __future__ import annotations

import json
import re

from .cell import _row_cells, cell_text
from .highlight import _highlight_rule_matches


def _split_csv(text: str):
    return [x.strip() for x in str(text or "").split(",") if x.strip()]


def _header_index_map(headers):
    m = {}
    for i, h in enumerate(headers or []):
        key = str(h).strip().casefold()
        if key and key not in m:
            m[key] = i
    return m


def _find_header_idx(headers, name: str):
    if not headers:
        return None
    target = str(name or "").strip()
    if target in headers:
        return headers.index(target)
    m = _header_index_map(headers)
    return m.get(target.casefold())


def _parse_row_filter_condition(expr: str):
    pattern = re.compile(
        r"^\s*(.+?)\s*(not contains|contains|not in|in|starts with|ends with|<=|>=|!=|==|=|<|>)\s*(.*?)\s*$",
        re.IGNORECASE,
    )
    m = pattern.match(expr or "")
    if not m:
        return None
    col = m.group(1).strip()
    op = m.group(2).strip().lower()
    raw_val = m.group(3).strip()
    if op == "=":
        op = "=="

    if op in ("in", "not in"):
        if raw_val.startswith("[") and raw_val.endswith("]"):
            try:
                value = json.loads(raw_val)
            except Exception:
                value = _split_csv(raw_val[1:-1])
        elif "|" in raw_val:
            value = [v.strip() for v in raw_val.split("|") if v.strip()]
        else:
            value = _split_csv(raw_val)
    else:
        value = raw_val
    return {"col": col, "op": op, "value": value}


def _parse_filter_specs(filter_specs):
    include_cols = []
    exclude_cols = []
    row_rules = []
    errors = []

    for raw in (filter_specs or []):
        spec = str(raw or "").strip()
        if not spec:
            continue
        if ":" not in spec:
            errors.append(f"Invalid filter '{spec}' (missing ':'; use col:... or row:...)")
            continue
        kind, body = spec.split(":", 1)
        kind = kind.strip().lower()
        body = body.strip()
        if kind in ("col", "cols", "column", "columns"):
            for tok in _split_csv(body):
                if tok.startswith("!"):
                    name = tok[1:].strip()
                    if name:
                        exclude_cols.append(name)
                else:
                    include_cols.append(tok)
        elif kind in ("row", "rows"):
            conds = [c.strip() for c in body.split(";") if c.strip()]
            if not conds and body.strip():
                conds = [body.strip()]
            for cond in conds:
                parsed = _parse_row_filter_condition(cond)
                if not parsed:
                    errors.append(f"Invalid row filter condition '{cond}'")
                else:
                    row_rules.append(parsed)
        else:
            errors.append(f"Unknown filter kind '{kind}' in '{spec}'")

    return {
        "include_cols": include_cols,
        "exclude_cols": exclude_cols,
        "row_rules": row_rules,
        "errors": errors,
    }


def apply_filters(data, filter_specs=None):
    headers = list(data.get("headers", []) or [])
    rows = list(data.get("rows", []) or [])
    if not headers or not rows or not filter_specs:
        return data, {"applied": False, "reason": "no-filter"}

    parsed = _parse_filter_specs(filter_specs)
    include_cols = parsed["include_cols"]
    exclude_cols = parsed["exclude_cols"]
    row_rules = parsed["row_rules"]
    errors = parsed["errors"]

    def _row_match(row):
        if not row_rules:
            return True
        cells = _row_cells(row)
        for r in row_rules:
            idx = _find_header_idx(headers, r["col"])
            if idx is None:
                return False
            val = cells[idx] if idx < len(cells) else ""
            if not _highlight_rule_matches({"op": r["op"], "value": r["value"]}, cell_text(val)):
                return False
        return True

    filtered_rows = [r for r in rows if _row_match(r)]

    include_set = {c.casefold() for c in include_cols if c}
    exclude_set = {c.casefold() for c in exclude_cols if c}

    keep_indices = list(range(len(headers)))
    if include_set:
        keep_indices = [i for i, h in enumerate(headers) if str(h).strip().casefold() in include_set]
    if exclude_set:
        keep_indices = [i for i in keep_indices if str(headers[i]).strip().casefold() not in exclude_set]

    col_filter_used = bool(include_cols or exclude_cols)
    if col_filter_used:
        new_headers = [headers[i] for i in keep_indices]
        new_rows = []
        for r in filtered_rows:
            src_cells = _row_cells(r)
            dst_cells = [src_cells[i] if i < len(src_cells) else "" for i in keep_indices]
            if isinstance(r, dict) and "cells" in r:
                new_rows.append({"row_hl": r.get("row_hl"), "cells": dst_cells})
            else:
                new_rows.append(dst_cells)
    else:
        new_headers = headers
        new_rows = filtered_rows

    out = {
        "headers": new_headers,
        "rows": new_rows,
        "title": data.get("title", ""),
        "footer": data.get("footer", ""),
    }
    return out, {
        "applied": True,
        "rows_before": len(rows),
        "rows_after": len(new_rows),
        "cols_before": len(headers),
        "cols_after": len(new_headers),
        "errors": errors,
    }
