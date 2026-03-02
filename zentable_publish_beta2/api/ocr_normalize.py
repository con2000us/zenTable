"""Shared OCR row normalization.

Normalize various OCR backend outputs to:
{ text, left, top, width, height }
"""

from __future__ import annotations

from typing import Any, Dict, List


def normalize_ocr_rows(result: Any) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not result:
        return rows

    # Paddle v3 style: [{rec_texts, rec_boxes, ...}]
    if isinstance(result, list) and result and isinstance(result[0], dict):
        payload = result[0]
        texts = payload.get("rec_texts") or []
        boxes = payload.get("rec_boxes") or []
        n = min(len(texts), len(boxes))
        for i in range(n):
            b = boxes[i]
            if b is None or len(b) < 4:
                continue
            l, t, r, btm = map(int, b[:4])
            rows.append({
                "text": str(texts[i]) if texts[i] is not None else "",
                "left": l,
                "top": t,
                "width": max(0, r - l),
                "height": max(0, btm - t),
            })
        return rows

    # list-style outputs
    if isinstance(result, list):
        for item in result:
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue

            box = item[0]
            second = item[1]

            # Paddle v2 style: [poly, (text, score)]
            if isinstance(second, (list, tuple)) and len(second) >= 1 and not isinstance(second, str):
                text = second[0]
            else:
                # RapidOCR style: [poly, text, score?]
                text = second

            left = top = width = height = 0
            if isinstance(box, (list, tuple)) and len(box) >= 4 and isinstance(box[0], (list, tuple)):
                try:
                    xs = [int(p[0]) for p in box]
                    ys = [int(p[1]) for p in box]
                    left = min(xs)
                    top = min(ys)
                    width = max(xs) - left
                    height = max(ys) - top
                except Exception:
                    left = top = width = height = 0

            rows.append({
                "text": "" if text is None else str(text),
                "left": int(left),
                "top": int(top),
                "width": int(max(0, width)),
                "height": int(max(0, height)),
            })
        return rows

    return rows
