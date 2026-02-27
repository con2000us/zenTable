#!/usr/bin/env python3
"""
Hybrid table extraction prototype:
- Structure from Paddle Table API result JSON
- Cell text re-read via OpenVINO OCR API on each cell crop

Usage:
  python3 table_hybrid_extract.py \
    --image /path/to/image.jpg \
    --parse-json /tmp/table_parse_result.json \
    --out /tmp/hybrid_table.json
"""

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests
from PIL import Image


def _norm_box(box: Any) -> Tuple[int, int, int, int]:
    # Supports [x1,y1,x2,y2] or 4-point polygon
    if isinstance(box, (list, tuple)) and len(box) == 4 and all(isinstance(v, (int, float)) for v in box):
        x1, y1, x2, y2 = box
        return int(x1), int(y1), int(x2), int(y2)

    if isinstance(box, (list, tuple)) and len(box) >= 4 and isinstance(box[0], (list, tuple)):
        xs = [p[0] for p in box if isinstance(p, (list, tuple)) and len(p) >= 2]
        ys = [p[1] for p in box if isinstance(p, (list, tuple)) and len(p) >= 2]
        if xs and ys:
            return int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))

    return 0, 0, 0, 0


def _ocr_json(ocr_url: str, crop_img: Image.Image) -> Dict[str, Any]:
    with tempfile.NamedTemporaryFile(suffix=".png") as tf:
        crop_img.save(tf.name)
        with open(tf.name, "rb") as f:
            r = requests.post(ocr_url, files={"image": f}, timeout=30)
        r.raise_for_status()
        return r.json()


def _ocr_crop(ocr_url: str, crop_img: Image.Image) -> str:
    data = _ocr_json(ocr_url, crop_img)
    rows = data.get("rows", [])
    texts = [str(rw.get("text", "")).strip() for rw in rows if str(rw.get("text", "")).strip()]
    return " ".join(texts).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--parse-json", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ocr-url", default="http://127.0.0.1:8011/ocr")
    args = ap.parse_args()

    img = Image.open(args.image).convert("RGB")
    parsed = json.loads(Path(args.parse_json).read_text(encoding="utf-8"))

    out: Dict[str, Any] = {
        "success": True,
        "source": {
            "image": args.image,
            "parse_json": args.parse_json,
            "ocr_url": args.ocr_url,
        },
        "tables": [],
    }

    for ti, t in enumerate(parsed.get("tables", [])):
        bbox = t.get("bbox")
        cell_boxes = t.get("cell_boxes") or []
        table_obj: Dict[str, Any] = {
            "table_index": ti,
            "bbox": bbox,
            "mode": "cell_boxes" if cell_boxes else "bbox_fallback",
            "cells": [],
            "rows": [],
        }

        # Normalize table bbox
        tx1, ty1, tx2, ty2 = _norm_box(bbox)
        tx1 = max(0, min(tx1, img.width - 1))
        tx2 = max(1, min(tx2, img.width))
        ty1 = max(0, min(ty1, img.height - 1))
        ty2 = max(1, min(ty2, img.height))

        if cell_boxes:
            for ci, cb in enumerate(cell_boxes):
                x1, y1, x2, y2 = _norm_box(cb)
                if x2 <= x1 or y2 <= y1:
                    continue

                # clamp
                x1 = max(0, min(x1, img.width - 1))
                x2 = max(1, min(x2, img.width))
                y1 = max(0, min(y1, img.height - 1))
                y2 = max(1, min(y2, img.height))

                crop = img.crop((x1, y1, x2, y2))
                try:
                    text = _ocr_crop(args.ocr_url, crop)
                except Exception as e:
                    text = f"[OCR_ERR] {e}"

                table_obj["cells"].append({
                    "cell_index": ci,
                    "bbox": [x1, y1, x2, y2],
                    "text": text,
                })
        else:
            # Fallback: OCR the whole table region then group text boxes by Y into rows.
            if tx2 > tx1 and ty2 > ty1:
                t_crop = img.crop((tx1, ty1, tx2, ty2))
                try:
                    ocr_data = _ocr_json(args.ocr_url, t_crop)
                    rows = ocr_data.get("rows", []) or []
                except Exception as e:
                    rows = [{"text": f"[OCR_ERR] {e}", "left": 0, "top": 0, "width": 0, "height": 0}]

                # convert to table-global coords and sort
                cells = []
                for i, r in enumerate(rows):
                    left = int(r.get("left", 0)) + tx1
                    top = int(r.get("top", 0)) + ty1
                    width = int(r.get("width", 0))
                    height = int(r.get("height", 0))
                    text = str(r.get("text", "")).strip()
                    if not text:
                        continue
                    cells.append({
                        "cell_index": i,
                        "bbox": [left, top, left + max(1, width), top + max(1, height)],
                        "text": text,
                        "left": left,
                        "top": top,
                        "width": width,
                        "height": height,
                    })

                cells.sort(key=lambda c: (c["top"], c["left"]))
                table_obj["cells"] = cells

                # naive row clustering by top distance
                clustered: List[List[Dict[str, Any]]] = []
                threshold = 18
                for c in cells:
                    if not clustered:
                        clustered.append([c])
                        continue
                    last_row = clustered[-1]
                    last_top = sum(x["top"] for x in last_row) / len(last_row)
                    if abs(c["top"] - last_top) <= threshold:
                        last_row.append(c)
                    else:
                        clustered.append([c])

                table_obj["rows"] = [
                    [x["text"] for x in sorted(row, key=lambda y: y["left"]) ]
                    for row in clustered
                ]

        out["tables"].append(table_obj)

    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved: {args.out}")


if __name__ == "__main__":
    main()
