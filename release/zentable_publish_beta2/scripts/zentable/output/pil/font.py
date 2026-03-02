#!/usr/bin/env python3
"""PIL font loading/cache helpers (CJK + emoji)."""

from __future__ import annotations

import glob
import os
from PIL import ImageFont

# 字體路徑（依優先順序，多路徑以支援不同發行版）
FONT_CJK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_CJK_LIST = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
FONT_EMOJI_LIST = [
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/google-noto-emoji/NotoColorEmoji.ttf",
    "/usr/share/fonts/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/noto-color-emoji/NotoColorEmoji.ttf",
    "/usr/share/fonts/opentype/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/truetype/ancient-scripts/Symbola_hint.ttf",
    "/usr/share/fonts/truetype/ancient-scripts/Symbola.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/Symbola.ttf",
]

_font_cache = {}
_emoji_font_available = None


def get_font_cjk(size=16):
    key = f"cjk_{size}"
    if key not in _font_cache:
        for path in FONT_CJK_LIST:
            if os.path.isfile(path):
                try:
                    _font_cache[key] = ImageFont.truetype(path, size)
                    break
                except Exception:
                    continue
        if key not in _font_cache:
            try:
                _font_cache[key] = ImageFont.truetype(FONT_CJK, size)
            except Exception:
                _font_cache[key] = ImageFont.load_default()
    return _font_cache[key]


def _detect_emoji_font():
    global _emoji_font_available
    if _emoji_font_available is not None:
        return _emoji_font_available

    def _try(path):
        try:
            ImageFont.truetype(path, 16)
            return True
        except Exception:
            return False

    for font_path in FONT_EMOJI_LIST:
        if os.path.isfile(font_path) and _try(font_path):
            _emoji_font_available = (font_path, "NotoColor" in font_path or "noto-color" in font_path.lower())
            return _emoji_font_available

    patterns = [
        "*[Nn]oto*[Ee]moji*.ttf", "*[Nn]oto*[Cc]olor*[Ee]moji*.ttf",
        "*[Ss]ymbola*.ttf", "*[Ss]ymbola*.otf",
        "*[Dd]eja[Vv]u*[Ss]ans*.ttf", "*[Dd]eja[Vv]u*.ttf",
        "*[Ll]iberation*[Ss]ans*.ttf",
        "*[Ee]moji*.ttf", "*[Ss]ymbol*.ttf",
    ]
    for base in ["/usr/share/fonts", "/usr/local/share/fonts", "/usr/share/fonts/truetype", "/usr/share/fonts/TTF"]:
        if not os.path.isdir(base):
            continue
        for pattern in patterns:
            for path in glob.glob(os.path.join(base, pattern)) + glob.glob(os.path.join(base, "*", pattern)):
                if os.path.isfile(path) and _try(path):
                    _emoji_font_available = (path, "Color" in path or "color" in path.lower())
                    return _emoji_font_available

    for base in ["/usr/share/fonts", "/usr/local/share/fonts"]:
        if not os.path.isdir(base):
            continue
        for name in ["NotoColorEmoji.ttf", "Symbola_hint.ttf", "Symbola.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"]:
            for path in glob.glob(os.path.join(base, "**", name)):
                if os.path.isfile(path) and _try(path):
                    _emoji_font_available = (path, "Color" in path or "color" in path.lower())
                    return _emoji_font_available

    _emoji_font_available = (None, False)
    return _emoji_font_available


def get_font_emoji(size=16):
    key = f"emoji_{size}"
    if key not in _font_cache:
        font_path, _ = _detect_emoji_font()
        if font_path:
            try:
                _font_cache[key] = ImageFont.truetype(font_path, size)
            except Exception:
                _font_cache[key] = ImageFont.load_default()
        else:
            for path in FONT_EMOJI_LIST:
                if os.path.isfile(path):
                    try:
                        _font_cache[key] = ImageFont.truetype(path, size)
                        break
                    except Exception:
                        continue
            if key not in _font_cache:
                _font_cache[key] = ImageFont.load_default()
    return _font_cache[key]


def is_color_emoji_font():
    _, is_color = _detect_emoji_font()
    return is_color


def get_font(size=16):
    return get_font_cjk(size)
