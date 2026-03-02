#!/usr/bin/env python3
"""Cell-level transform helpers."""

from __future__ import annotations


def normalize_cell(cell):
    """將 cell 統一為 dict，支援舊格式（字串/數字）與 CellSpec。含 hl 時一併保留。"""
    if isinstance(cell, dict):
        text = cell.get("text", "")
        try:
            colspan = int(cell.get("colspan", 1))
        except (TypeError, ValueError):
            colspan = 1
        try:
            rowspan = int(cell.get("rowspan", 1))
        except (TypeError, ValueError):
            rowspan = 1
        out = {
            "text": "" if text is None else str(text),
            "colspan": max(1, colspan),
            "rowspan": max(1, rowspan),
        }
        if "hl" in cell and cell["hl"] is not None:
            out["hl"] = str(cell["hl"]).strip() or None
        return out
    return {
        "text": "" if cell is None else str(cell),
        "colspan": 1,
        "rowspan": 1,
    }


def _row_cells(row):
    """從一列取得 cells 串列；支援 list 或 {row_hl, cells}。"""
    if isinstance(row, dict) and "cells" in row:
        return list(row["cells"]) if row["cells"] is not None else []
    if isinstance(row, list):
        return row
    return []


def _try_numeric(s):
    """嘗試將值轉成數字，失敗回傳 None。"""
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def cell_text(cell) -> str:
    return normalize_cell(cell).get("text", "")
