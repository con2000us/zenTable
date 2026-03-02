#!/usr/bin/env python3
"""ASCII rendering character-width utilities."""

from __future__ import annotations

import unicodedata


def _is_zero_width(ch):
    cp = ord(ch)
    if cp in (0x200B, 0x200C, 0x200D, 0xFEFF, 0x00AD):
        return True
    if 0xFE00 <= cp <= 0xFE0F:
        return True
    if 0xE0100 <= cp <= 0xE01EF:
        return True
    cat = unicodedata.category(ch)
    if cat in ('Mn', 'Me'):
        return True
    return False


def _classify_char(ch):
    cp = ord(ch)
    if 0x2500 <= cp <= 0x257F or 0x2580 <= cp <= 0x259F:
        return 'box'
    if cp == 0x3000:
        return 'full_space'
    if cp in (0x2002, 0x2003, 0x2004, 0x2005, 0x2006, 0x2009, 0x200A):
        return 'half_space'
    if (0x1F300 <= cp <= 0x1F9FF or 0x2600 <= cp <= 0x27BF or
        0x2B50 <= cp <= 0x2B55 or 0x23E9 <= cp <= 0x23FA or
        0x1FA00 <= cp <= 0x1FA6F or 0x1FA70 <= cp <= 0x1FAFF):
        return 'emoji'
    eaw = unicodedata.east_asian_width(ch)
    if eaw in ('W', 'F'):
        return 'cjk'
    return 'ascii'


def _clamp_width(w):
    try:
        fw = float(w)
    except Exception:
        return None
    return 0.0 if fw < 0 else fw


def _space_width(calibration=None):
    if calibration:
        custom = calibration.get('custom') if isinstance(calibration, dict) else None
        if custom and ' ' in custom:
            cw = _clamp_width(custom[' '])
            if cw is not None:
                return cw
        if isinstance(calibration, dict) and 'half_space' in calibration:
            hw = _clamp_width(calibration['half_space'])
            if hw is not None:
                return hw
        if isinstance(calibration, dict) and 'ascii' in calibration:
            aw = _clamp_width(calibration['ascii'])
            if aw is not None:
                return aw
    return 1.0


def char_display_width(ch, calibration=None):
    if _is_zero_width(ch):
        return 0.0
    if ch == ' ':
        return _space_width(calibration)
    if calibration:
        custom = calibration.get('custom') if isinstance(calibration, dict) else None
        if custom and ch in custom:
            cw = _clamp_width(custom[ch])
            if cw is not None:
                return cw
        cat = _classify_char(ch)
        if isinstance(calibration, dict) and cat in calibration:
            kw = _clamp_width(calibration[cat])
            if kw is not None:
                return kw
    cat = _classify_char(ch)
    if cat == 'emoji':
        return 2
    if cat == 'full_space':
        return 2
    eaw = unicodedata.east_asian_width(ch)
    if eaw in ('W', 'F'):
        return 2
    return 1


def display_width(text, calibration=None):
    s = str(text)
    if "\n" in s:
        lines = s.splitlines() or [""]
        return max(sum(char_display_width(ch, calibration) for ch in line) for line in lines)
    return sum(char_display_width(ch, calibration) for ch in s)


def calculate_column_widths(headers, rows, padding=2, calibration=None, row_cells_fn=None, cell_text_fn=None):
    if row_cells_fn is None:
        row_cells_fn = lambda r: r if isinstance(r, list) else []
    if cell_text_fn is None:
        cell_text_fn = lambda c: "" if c is None else str(c)
    sw = _space_width(calibration)
    widths = [display_width(str(h), calibration) for h in headers]
    for row in rows:
        for i, cell in enumerate(row_cells_fn(row)):
            if i < len(widths):
                widths[i] = max(widths[i], display_width(cell_text_fn(cell), calibration))
    return [w + padding * 2 * sw for w in widths]


def align_text(text, target_width, align="left", calibration=None):
    text = str(text)
    dw = display_width(text, calibration)
    sw = _space_width(calibration)
    if sw <= 0:
        sw = 1.0
    pad_count = max(0, round((target_width - dw) / sw))
    if align == "right":
        return ' ' * pad_count + text
    elif align == "center":
        left = pad_count // 2
        right = pad_count - left
        return ' ' * left + text + ' ' * right
    else:
        return text + ' ' * pad_count
