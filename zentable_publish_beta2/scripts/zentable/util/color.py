#!/usr/bin/env python3
"""Color utility helpers for zentable."""

from __future__ import annotations


def _hex_to_chrome_bg(hex_color: str) -> str:
    """將 #RRGGBB 或 #RRGGBBAA 轉為 Chrome --default-background-color 的 8 位格式。"""
    h = str(hex_color).lstrip('#')
    if len(h) == 6:
        return h + 'FF'
    if len(h) == 8:
        return h
    return '000000FF'


def parse_color(c):
    """解析顏色格式：#RRGGBB、#RRGGBBAA、rgba(r,g,b,a)。"""
    c = str(c).strip()

    if c.startswith('rgba('):
        parts = c[5:-1].split(',')
        if len(parts) == 4:
            r = int(parts[0].strip())
            g = int(parts[1].strip())
            b = int(parts[2].strip())
            a = float(parts[3].strip())
            return (r, g, b, int(a * 255))

    if c.startswith('#') and len(c) == 9:
        c = c.lstrip('#')
        return tuple(int(c[i:i+2], 16) for i in (0, 2, 4, 6))

    if c.startswith('#') and len(c) == 7:
        c = c.lstrip('#')
        return tuple(int(c[i:i+2], 16) for i in (0, 2, 4))

    if c.startswith('#') and len(c) == 4:
        c = c.lstrip('#')
        return tuple(int(c[i] * 2, 16) for i in (0, 1, 2))

    raise ValueError(f"Unknown color format: {c}")


def hex_rgb(c):
    """向下相容：返回 RGB 元組。"""
    color = parse_color(c)
    return color[:3]
