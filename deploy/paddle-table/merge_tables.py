#!/usr/bin/env python3
"""
Merge normalized table outputs with safe defaults.

Input: normalize_rows.py output JSON
Output: merged JSON with original_tables + optional merged_table

Usage:
  python3 merge_tables.py \
    --in /tmp/hybrid_table_norm.json \
    --out /tmp/hybrid_table_merged.json \
    --merge true \
    --merge-mode normalized
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def _as_bool(s: str) -> bool:
    return str(s).strip().lower() in ("1", "true", "yes", "on")


def _clean(x: str) -> str:
    return " ".join((x or "").strip().split())


def _normalized_merge(tables: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Convert tables into long-form rows with schema:
      [來源表, 行索引, 欄索引, 內容]
    This is robust when original table schemas differ.
    """
    rows: List[List[str]] = []
    for t in tables:
        ti = str(t.get("table_index", "?"))
        for r_idx, r in enumerate(t.get("rows", [])):
            for c_idx, cell in enumerate(r):
                txt = _clean(str(cell))
                if not txt:
                    continue
                rows.append([f"table_{ti}", str(r_idx), str(c_idx), txt])

    return {
        "title": "Merged Table (normalized)",
        "headers": ["source_table", "row", "col", "text"],
        "rows": rows,
        "footer": "Auto-merged with normalized mode",
    }


def _append_rows_merge(tables: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Append rows when schemas are similar (best effort)."""
    max_cols = max((t.get("col_count", 0) for t in tables), default=0)
    headers = [f"col_{i+1}" for i in range(max_cols)]
    merged_rows: List[List[str]] = []

    for t in tables:
        ti = t.get("table_index")
        for r in t.get("rows", []):
            rr = [_clean(str(x)) for x in r]
            rr += [""] * (max_cols - len(rr))
            # keep provenance in first column note if available
            if rr:
                rr[0] = f"[T{ti}] {rr[0]}" if rr[0] else f"[T{ti}]"
            merged_rows.append(rr)

    return {
        "title": "Merged Table (append_rows)",
        "headers": headers,
        "rows": merged_rows,
        "footer": "Auto-merged with append_rows mode",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--merge", default="false", help="true/false, default false")
    ap.add_argument("--merge-mode", default="normalized", choices=["normalized", "append_rows"])
    args = ap.parse_args()

    src = json.loads(Path(args.inp).read_text(encoding="utf-8"))
    tables = src.get("tables", [])

    out: Dict[str, Any] = {
        "success": bool(src.get("success", True)),
        "merge_enabled": _as_bool(args.merge),
        "merge_mode": args.merge_mode,
        "original_tables": tables,
        "merged_table": None,
        "warnings": [],
    }

    if not _as_bool(args.merge):
        out["warnings"].append("merge disabled (default). returning original tables only")
    else:
        if args.merge_mode == "normalized":
            out["merged_table"] = _normalized_merge(tables)
        elif args.merge_mode == "append_rows":
            out["merged_table"] = _append_rows_merge(tables)

    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved: {args.out}")


if __name__ == "__main__":
    main()
