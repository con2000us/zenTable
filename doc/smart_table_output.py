#!/usr/bin/env python3
"""
智能表格输出 skill - 适合 OpenClaw 自动化
"""

import json
import os
from pathlib import Path

# 偏好设置文件
SETTINGS_PATH = os.path.expanduser("~/.openclaw/table_output_settings.json")

DEFAULT_SETTINGS = {
    "prefer_image": None,  # None = 询问, True = 总是图片, False = 总是文字
    "theme": "dark",
    "rows_per_page": 10,
    "has_been_asked": False
}

def load_settings():
    """加载偏好设置"""
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, 'r') as f:
                return {**DEFAULT_SETTINGS, **json.load(f)}
        except:
            pass
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    """保存偏好设置"""
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, 'w') as f:
        json.dump(settings, f, indent=2)

def should_use_image(ask_if_first=True, is_first_table=False):
    """
    判断是否应该使用图片输出

    Args:
        ask_if_first: 如果是第一次，是否询问
        is_first_table: 是否是本次会话中第一次输出表格

    Returns:
        bool: True=使用图片, False=使用文字, None=需要询问
    """
    settings = load_settings()

    # 已设置偏好
    if settings["prefer_image"] is not None:
        return settings["prefer_image"]

    # 第一次且需要询问
    if ask_if_first and (is_first_table or not settings["has_been_asked"]):
        settings["has_been_asked"] = True
        save_settings(settings)
        return None  # 表示需要询问

    return False

def ask_user_preference():
    """返回询问消息"""
    return {
        "type": "choice",
        "message": "📊 檢測到表格輸出，您偏好哪種格式？",
        "options": [
            {"label": "🖼️ 圖片輸出（適合手機/Discord）", "value": "image"},
            {"label": "📝 文字表格", "value": "text"},
            {"label": "⚙️ 設置偏好", "value": "settings"}
        ]
    }

def set_preference(prefer_image: bool):
    """设置偏好"""
    settings = load_settings()
    settings["prefer_image"] = prefer_image
    settings["remember_choice"] = True
    save_settings(settings)
    return f"✅ 已設置為: {'總是圖片' if prefer_image else '總是文字'}"

def set_theme(theme: str):
    """设置主题"""
    settings = load_settings()
    settings["theme"] = theme
    save_settings(settings)
    return f"✅ 主題已設置為: {theme}"

def render_as_image(data, output_path, theme="dark"):
    """渲染为图片"""
    from zeble import draw_table, StyleConfig

    if theme == "dark":
        config = StyleConfig(bg_color="#1a1a2e")
    else:
        config = StyleConfig(bg_color="#f8f9fa", text_color="#212529")

    result = draw_table(data, output_path, config=config)
    return result

def render_as_text(data):
    """渲染为文字表格"""
    if not data:
        return "無數據"

    if isinstance(data, list) and len(data) > 0:
        keys = list(data[0].keys())
        col_widths = {k: max(len(str(k)), max(len(str(row.get(k, ""))) for row in data)) + 2 for k in keys}

        lines = []
        header = " | ".join(str(k).ljust(col_widths[k]) for k in keys)
        separator = "-+-".join("-" * col_widths[k] for k in keys)

        lines.append(f"\n{header}")
        lines.append(separator)

        for row in data:
            line = " | ".join(str(row.get(k, "")).ljust(col_widths[k]) for k in keys)
            lines.append(line)

        lines.append(f"\n共 {len(data)} 行")
        return "\n".join(lines)

    return str(data)

# CLI 接口
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 smart_table_output.py --ask <data.json>")
        print("  python3 smart_table_output.py --image <data.json> <output.png>")
        print("  python3 smart_table_output.py --text <data.json>")
        print("  python3 smart_table_output.py --set image|text")
        print("  python3 smart_table_output.py --status")
        sys.exit(1)

    if sys.argv[1] == "--status":
        settings = load_settings()
        pref = settings["prefer_image"]
        print(f"偏好: {'圖片' if pref else '文字' if pref is False else '未設置'}")
        print(f"主題: {settings['theme']}")
        print(f"已詢問過: {'是' if settings['has_been_asked'] else '否'}")
    elif sys.argv[1] == "--set":
        if sys.argv[2] == "image":
            print(set_preference(True))
        elif sys.argv[2] == "text":
            print(set_preference(False))
    elif sys.argv[1] == "--ask":
        result = should_use_image()
        if result is None:
            print("ASK_USER")
        else:
            print(f"USE_IMAGE: {result}")
    elif sys.argv[1] == "--image":
        with open(sys.argv[2], 'r') as f:
            data = json.load(f)
        render_as_image(data, sys.argv[3])
        print(f"✅ 已生成圖片: {sys.argv[3]}")
    elif sys.argv[1] == "--text":
        with open(sys.argv[2], 'r') as f:
            data = json.load(f)
        print(render_as_text(data))
