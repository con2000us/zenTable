#!/usr/bin/env python3
"""Text/emoji utility helpers for zentable."""

from __future__ import annotations


def is_emoji_modifier_or_joiner(char):
    """判斷是否為 emoji 修飾符或連接符。"""
    code = ord(char)
    if code == 0xFE0F:  # Variation Selector-16 (emoji style)
        return True
    if code == 0x200D:  # ZWJ
        return True
    if 0x1F3FB <= code <= 0x1F3FF:  # 膚色修飾
        return True
    if 0x1F9B0 <= code <= 0x1F9B3:  # 髮色修飾
        return True
    if 0xFE00 <= code <= 0xFE0F:   # 其他 variation selector
        return True
    return False


def is_emoji(char):
    """判斷是否為 Emoji（需用支援 emoji 的字型繪製）。"""
    color_circles = {
        '🟢': '(綠)', '🟡': '(黃)', '🔴': '(紅)', '🟠': '(橙)',
        '🔵': '(藍)', '⚫': '(黑)', '⚪': '(白)', '🟣': '(紫)',
        '🟤': '(棕)', '🟣': '(紫)', '🟡': '(黃)'
    }
    if char in color_circles:
        return 'special'
    code = ord(char)
    if is_emoji_modifier_or_joiner(char):
        return False

    emoji_ranges = [
        (0x2600, 0x26FF), (0x2700, 0x27BF), (0x1F300, 0x1F5FF),
        (0x1F600, 0x1F64F), (0x1F680, 0x1F6FF), (0x1F1E0, 0x1F1FF),
        (0x1F900, 0x1F9FF), (0x1FA00, 0x1FA6F), (0x1FA70, 0x1FAFF),
        (0x203C, 0x203C), (0x2049, 0x2049), (0x2122, 0x2122), (0x2139, 0x2139),
        (0x2194, 0x2199), (0x21A9, 0x21AA), (0x231A, 0x231B), (0x23E9, 0x23F3),
        (0x23F8, 0x23FA), (0x25AA, 0x25AB), (0x25B6, 0x25B6), (0x25C0, 0x25C0),
        (0x25FB, 0x25FE), (0x2614, 0x2615), (0x2648, 0x2653), (0x267F, 0x267F),
        (0x2693, 0x2693), (0x26A1, 0x26A1), (0x26AA, 0x26AB), (0x26BD, 0x26BE),
        (0x26C4, 0x26C5), (0x26CE, 0x26CE), (0x26D4, 0x26D4), (0x26EA, 0x26EA),
        (0x26F2, 0x26F3), (0x26F5, 0x26F5), (0x26FA, 0x26FA), (0x26FD, 0x26FD),
        (0x2702, 0x2702), (0x2705, 0x2705), (0x2708, 0x270D), (0x270F, 0x270F),
        (0x2712, 0x2712), (0x2714, 0x2714), (0x2716, 0x2716), (0x271D, 0x271D),
        (0x2721, 0x2721), (0x2728, 0x2728), (0x2733, 0x2734), (0x2744, 0x2744),
        (0x2747, 0x2747), (0x274C, 0x274C), (0x274E, 0x274E), (0x2753, 0x2755),
        (0x2757, 0x2757), (0x2763, 0x2764), (0x2795, 0x2797), (0x27A1, 0x27A1),
        (0x27B0, 0x27B0), (0x27BF, 0x27BF), (0x2934, 0x2935), (0x2B05, 0x2B07),
        (0x2B1B, 0x2B1C), (0x2B50, 0x2B50), (0x2B55, 0x2B55), (0x3030, 0x3030),
        (0x303D, 0x303D), (0x3297, 0x3297), (0x3299, 0x3299),
    ]
    for start, end in emoji_ranges:
        if start <= code <= end:
            return True
    if char in "🀀🌐🎉✨💯✅❌⚠️📦🖥️💰📊🔄🔗🎨⚡🔧🛠️":
        return True
    return False


def replace_color_circles(text):
    """替換顏色圈為文字（Symbola 不支援彩色圓形）。"""
    color_circles = {
        '🟢': '(綠)', '🟡': '(黃)', '🔴': '(紅)', '🟠': '(橙)',
        '🔵': '(藍)', '⚫': '(黑)', '⚪': '(白)', '🟣': '(紫)',
        '🟤': '(棕)', '🟥': '(紅方)', '🟧': '(橙方)', '🟨': '(黃方)',
        '🟩': '(綠方)', '🟦': '(藍方)', '🟪': '(紫方)', '🟫': '(棕方)',
        '⬛': '(黑方)', '⬜': '(白方)'
    }
    text = str(text)
    for emoji, replacement in color_circles.items():
        text = text.replace(emoji, replacement)
    return text


def split_text_by_font(text):
    """將文字分段，返回 [(文字, 字體類型), ...]。"""
    text = replace_color_circles(str(text))
    segments = []
    current_type = None
    current_text = ""

    for char in text:
        if current_type == "emoji" and is_emoji_modifier_or_joiner(char):
            current_text += char
            continue

        char_type = is_emoji(char)
        if char_type == "special":
            char_type = "cjk"
        elif char_type is True:
            char_type = "emoji"

        if current_type not in (None, char_type):
            if current_text:
                segments.append((current_text, current_type))
            current_type = char_type
            current_text = char
        else:
            if current_type is None:
                current_type = char_type
            current_text += char

    if current_text:
        segments.append((current_text, current_type))
    return segments
