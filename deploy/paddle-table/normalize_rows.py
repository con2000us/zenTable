#!/usr/bin/env python3
"""
Normalize hybrid table rows into stable rectangular arrays.

Input: hybrid_table_v01.json (from table_hybrid_extract.py)
Output: cleaned JSON with normalized rows per table.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def _clean_text(s: str) -> str:
    s = (s or "").strip()
    # common OCR artifacts cleanup
    s = s.replace("\u3000", " ")
    s = " ".join(s.split())
    return s


def _drop_noise_rows(rows: List[List[str]]) -> List[List[str]]:
    out = []
    for r in rows:
        rr = [_clean_text(x) for x in r]
        # drop fully empty rows
        if not any(rr):
            continue
        out.append(rr)
    return out


def _normalize_width(rows: List[List[str]]) -> List[List[str]]:
    if not rows:
        return rows
    width = max(len(r) for r in rows)
    return [r + [""] * (width - len(r)) for r in rows]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="input hybrid json")
    ap.add_argument("--out", required=True, help="output normalized json")
    args = ap.parse_args()

    src = json.loads(Path(args.inp).read_text(encoding="utf-8"))

    out: Dict[str, Any] = {
        "success": bool(src.get("success", True)),
        "source": src.get("source", {}),
        "tables": [],
    }

    for t in src.get("tables", []):
        rows = t.get("rows") or []
        rows = _drop_noise_rows(rows)
        rows = _normalize_width(rows)

        out["tables"].append(
            {
                "table_index": t.get("table_index"),
                "mode": t.get("mode"),
                "bbox": t.get("bbox"),
                "row_count": len(rows),
                "col_count": max((len(r) for r in rows), default=0),
                "rows": rows,
            }
        )

    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved: {args.out}")


if __name__ == "__main__":
    main()
