#!/usr/bin/env python3
"""Input loading and normalization for zentable."""

from __future__ import annotations

import json
from typing import Any, Dict


def load_json(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def normalise_data(data: Any) -> Dict[str, Any]:
    """將資料統一為 {headers, rows, title, footer}。

    支援：
    - list[dict]
    - {headers, rows}
    - row 為 list 或 {row_hl, cells}
    """
    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
        headers = list(data[0].keys())
        rows = [[row.get(h, "") for h in headers] for row in data]
        return {"headers": headers, "rows": rows, "title": "", "footer": ""}

    if isinstance(data, dict) and "headers" in data and "rows" in data:
        rows = []
        for r in data["rows"]:
            if isinstance(r, dict) and "cells" in r:
                rows.append({"row_hl": r.get("row_hl"), "cells": list(r["cells"])})
            else:
                rows.append(list(r) if isinstance(r, (list, tuple)) else [])
        return {
            "headers": list(data["headers"]),
            "rows": rows,
            "title": data.get("title", ""),
            "footer": data.get("footer", ""),
        }

    if isinstance(data, dict):
        rows = data.get("rows", [])
        out_rows = []
        for r in rows:
            if isinstance(r, dict) and "cells" in r:
                out_rows.append({"row_hl": r.get("row_hl"), "cells": list(r["cells"])})
            else:
                out_rows.append(list(r) if isinstance(r, (list, tuple)) else [])
        return {
            "headers": data.get("headers", []),
            "rows": out_rows,
            "title": data.get("title", ""),
            "footer": data.get("footer", ""),
        }

    return {"headers": [], "rows": [], "title": "", "footer": ""}
