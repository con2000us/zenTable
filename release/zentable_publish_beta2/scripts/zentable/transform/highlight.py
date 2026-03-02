#!/usr/bin/env python3
"""Highlight rule evaluation and css emission."""

from __future__ import annotations

import sys
from typing import Optional

from .cell import _try_numeric


def _highlight_rule_matches(rule: dict, cell_value: str) -> bool:
    op = (rule.get("op") or "").strip().lower()
    value = rule.get("value")
    cell_str = (cell_value or "").strip() if cell_value is not None else ""
    cell_num = _try_numeric(cell_value)

    if op in ("empty", "is empty"):
        return cell_str == ""
    if op in ("not empty", "is not empty"):
        return cell_str != ""

    if op == "in":
        if not isinstance(value, list):
            return False
        vals = [str(v).strip() for v in value]
        if cell_num is not None:
            for v in value:
                n = _try_numeric(v)
                if n is not None and cell_num == n:
                    return True
        return cell_str in vals

    if op == "not in":
        if not isinstance(value, list):
            return False
        vals = [str(v).strip() for v in value]
        if cell_num is not None:
            for v in value:
                n = _try_numeric(v)
                if n is not None and cell_num == n:
                    return False
            return True
        return cell_str not in vals

    if op == "contains":
        if value is None:
            return False
        if isinstance(value, list):
            return any(cell_str.find(str(v)) >= 0 for v in value)
        return cell_str.find(str(value)) >= 0

    if op in ("not contains", "excludes"):
        if value is None:
            return True
        if isinstance(value, list):
            return not any(cell_str.find(str(v)) >= 0 for v in value)
        return cell_str.find(str(value)) < 0

    if op in ("starts with", "startswith"):
        if value is None:
            return False
        if isinstance(value, list):
            return any(cell_str.startswith(str(v)) for v in value)
        return cell_str.startswith(str(value))

    if op in ("ends with", "endswith"):
        if value is None:
            return False
        if isinstance(value, list):
            return any(cell_str.endswith(str(v)) for v in value)
        return cell_str.endswith(str(value))

    compare_val = value
    compare_num = _try_numeric(compare_val) if compare_val is not None else None
    if cell_num is not None and compare_num is not None:
        a, b = cell_num, compare_num
        if op == "==":
            return a == b
        if op == "!=":
            return a != b
        if op == "<":
            return a < b
        if op == "<=":
            return a <= b
        if op == ">":
            return a > b
        if op == ">=":
            return a >= b

    compare_str = str(compare_val).strip() if compare_val is not None else ""
    if op == "==":
        return cell_str == compare_str
    if op == "!=":
        return cell_str != compare_str
    if op in ("<", "<=", ">", ">="):
        return (cell_str < compare_str) if op == "<" else (cell_str <= compare_str) if op == "<=" else (cell_str > compare_str) if op == ">" else (cell_str >= compare_str)
    return False


def resolve_cell_highlight(
    cell: dict,
    row_hl: Optional[str],
    theme: Optional[dict],
    col_name: Optional[str] = None,
    highlight_rules: Optional[list] = None,
    col_hl: Optional[dict] = None,
) -> str:
    token = None
    if cell.get("hl"):
        token = str(cell["hl"]).strip()
    if not token and row_hl:
        token = str(row_hl).strip() if row_hl else None
    if not token and col_hl and col_name and isinstance(col_hl, dict) and col_name in col_hl:
        token = str(col_hl[col_name]).strip()
    if not token and highlight_rules and col_name:
        cell_val = cell.get("text") or ""
        for r in highlight_rules:
            if not isinstance(r, dict):
                continue
            if r.get("col") != col_name:
                continue
            if _highlight_rule_matches(r, cell_val):
                token = (r.get("hl") or "").strip()
                break
    if not token:
        token = "default"
    highlight_styles = (theme or {}).get("highlight_styles") or {}
    if not isinstance(highlight_styles, dict):
        return "default"
    if token not in highlight_styles:
        if token != "default":
            print(f"⚠️  highlight token '{token}' 未定義於 theme，fallback 至 default", file=sys.stderr)
        return "default"
    return token


def _highlight_styles_to_css(theme: dict) -> str:
    highlight_styles = (theme or {}).get("highlight_styles") or {}
    if not isinstance(highlight_styles, dict):
        return ""
    lines = []
    for token, val in highlight_styles.items():
        if not token or not isinstance(val, (str, dict)):
            continue
        css_val = val.get("style", val) if isinstance(val, dict) else val
        if not css_val or not isinstance(css_val, str):
            continue
        css_val = css_val.strip().rstrip(";")
        if css_val:
            lines.append(f"td.hl-{token}, th.hl-{token} {{ {css_val}; }}")
    return "\n".join(lines)
