#!/usr/bin/env python3
"""CSS screenshot crop and edge-detection helpers."""

from __future__ import annotations

import sys
from typing import Optional


def make_png_background_transparent_chroma(png_path: str, chroma_rgb: tuple = (255, 0, 255), tolerance: int = 8) -> bool:
    try:
        from PIL import Image
        img = Image.open(png_path)
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        data = list(img.getdata())
        r0, g0, b0 = chroma_rgb
        new_data = []
        for item in data:
            if len(item) == 4:
                r, g, b, a = item
            else:
                r, g, b = item[:3]
                a = 255
            if abs(r - r0) <= tolerance and abs(g - g0) <= tolerance and abs(b - b0) <= tolerance:
                new_data.append((0, 0, 0, 0))
            else:
                new_data.append((r, g, b, a))
        img.putdata(new_data)
        img.save(png_path, "PNG")
        return True
    except Exception as e:
        print(f"⚠️  透空後製失敗: {e}", file=sys.stderr)
        return False


def crop_to_content_bounds(png_path: str, padding: int = 2, transparent: bool = False, tolerance: int = 20) -> bool:
    try:
        from PIL import Image
        img = Image.open(png_path)
        w, h = img.size
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        if transparent:
            alpha = img.split()[3]
            bbox = alpha.getbbox()
        else:
            corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
            refs = [img.getpixel(c) for c in corners if 0 <= c[0] < w and 0 <= c[1] < h]
            if not refs:
                return False
            bg = tuple(sum(r[i] for r in refs) // len(refs) for i in range(3))

            def is_content(p):
                return max(abs(p[0] - bg[0]), abs(p[1] - bg[1]), abs(p[2] - bg[2])) > tolerance

            data = list(img.getdata())
            mask_data = [(255 if is_content(p[:3]) else 0) for p in data]
            mask = Image.new("L", (w, h))
            mask.putdata(mask_data)
            bbox = mask.getbbox()

        if bbox:
            left, top, right, bottom = bbox
            left = max(0, left - padding)
            top = max(0, top - padding)
            right = min(w, right + padding)
            bottom = min(h, bottom + padding)
            img = img.crop((left, top, right, bottom))
            img.save(png_path, "PNG")
        return True
    except Exception as e:
        print(f"⚠️  裁切失敗: {e}", file=sys.stderr)
        return False


def bottom_edge_has_content(png_path: str, transparent: bool = False, tolerance: int = 20, alpha_threshold: int = 1) -> bool:
    try:
        from PIL import Image
        img = Image.open(png_path)
        w, h = img.size
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        y = h - 1
        if y < 0:
            return False
        if transparent:
            alpha = img.split()[3]
            row = alpha.crop((0, y, w, y + 1))
            return row.getextrema()[1] >= alpha_threshold

        corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
        refs = [img.getpixel(c) for c in corners if 0 <= c[0] < w and 0 <= c[1] < h]
        if not refs:
            return False
        bg = tuple(sum(r[i] for r in refs) // len(refs) for i in range(3))

        row = img.crop((0, y, w, y + 1))
        for p in list(row.getdata()):
            rgb = p[:3]
            if max(abs(rgb[0] - bg[0]), abs(rgb[1] - bg[1]), abs(rgb[2] - bg[2])) > tolerance:
                return True
        return False
    except Exception:
        return False


def right_edge_metrics(png_path: str, transparent: bool = False, tolerance: int = 20, alpha_threshold: int = 1, x_inset: int = 0) -> Optional[dict]:
    try:
        from PIL import Image
        img = Image.open(png_path)
        w, h = img.size
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        x = max(0, min(w - 1, (w - 1) - int(x_inset)))
        if w <= 0 or h <= 0:
            return None

        bg = (0, 0, 0)
        if not transparent:
            corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
            refs = [img.getpixel(c) for c in corners if 0 <= c[0] < w and 0 <= c[1] < h]
            if not refs:
                return None
            bg = tuple(sum(r[i] for r in refs) // len(refs) for i in range(3))

        def is_nonempty(px):
            if transparent:
                return px[3] >= alpha_threshold
            rgb = px[:3]
            return max(abs(rgb[0] - bg[0]), abs(rgb[1] - bg[1]), abs(rgb[2] - bg[2])) > tolerance

        col = img.crop((x, 0, x + 1, h))
        data = list(col.getdata())
        nonempty = 0
        run = 0
        best_run = 0
        for p in data:
            if is_nonempty(p):
                nonempty += 1
                run += 1
                if run > best_run:
                    best_run = run
            else:
                run = 0

        ratio = (nonempty / float(h)) if h else 0.0
        return {"x": int(x), "h": int(h), "nonempty": int(nonempty), "ratio": float(ratio), "best_run": int(best_run)}
    except Exception:
        return None


def right_edge_has_content(png_path: str, transparent: bool = False, tolerance: int = 20, alpha_threshold: int = 1,
                           min_run: int = 12, min_ratio: float = 0.03, x_inset: int = 0) -> bool:
    m = right_edge_metrics(png_path, transparent=transparent, tolerance=tolerance, alpha_threshold=alpha_threshold, x_inset=x_inset)
    if not m:
        return False
    h = max(1, int(m.get("h", 1)))
    ratio = float(m.get("ratio", 0.0))
    best_run = int(m.get("best_run", 0))
    if ratio >= float(min_ratio):
        return True
    if best_run >= int(min_run):
        return True
    return False


def crop_to_content_height(png_path: str, transparent: bool = False, tolerance: int = 20) -> bool:
    try:
        from PIL import Image
        img = Image.open(png_path)
        w, h = img.size
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        if transparent:
            alpha = img.split()[3]
            bbox = alpha.getbbox()
        else:
            corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
            refs = [img.getpixel(c) for c in corners if 0 <= c[0] < w and 0 <= c[1] < h]
            if not refs:
                return False
            bg = tuple(sum(r[i] for r in refs) // len(refs) for i in range(3))

            def is_content(p):
                return max(abs(p[0] - bg[0]), abs(p[1] - bg[1]), abs(p[2] - bg[2])) > tolerance

            data = list(img.getdata())
            mask_data = [(255 if is_content(p[:3]) else 0) for p in data]
            mask = Image.new("L", (w, h))
            mask.putdata(mask_data)
            bbox = mask.getbbox()

        if not bbox:
            return True

        _, _, _, bottom = bbox
        bottom = max(1, min(h, bottom))
        img = img.crop((0, 0, w, bottom))
        img.save(png_path, "PNG")
        return True
    except Exception as e:
        print(f"⚠️  高度裁切失敗: {e}", file=sys.stderr)
        return False
