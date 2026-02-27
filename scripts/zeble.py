#!/usr/bin/env python3
"""
Zeble - Zen Table Output
Elegant table rendering with style

Zen + Table - 讓表格文字有禪意的風格輸出

用法: python3 zentable.py <input.json> <output.png> [options]
"""

import json
import sys
import os
import re
from PIL import Image, ImageDraw, ImageFont
from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class StyleConfig:
    """样式配置"""
    bg_color: str = "#1a1a2e"
    bg_image: str = ""  # 背景圖片路徑
    text_color: str = "#ffffff"
    header_bg: str = "#0f3460"
    header_text: str = "#e94560"
    alt_row_color: str = "#16213e"
    border_color: str = "#4a5568"
    border_image: str = ""  # 邊框圖片路徑
    border_radius: int = 8
    border_width: int = 2
    highlight_color: str = "#e94560"
    font_size: int = 18
    header_font_size: int = 22
    padding: int = 12
    cell_padding: int = 8
    row_height: int = 32
    header_height: int = 40
    rows_per_page: int = 15
    show_page_info: bool = True
    mobile_max_width: int = 600

STYLE = StyleConfig()

# 字体路径
CHINESE_FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
EMOJI_FONT_PATH = "/usr/share/fonts/truetype/ancient-scripts/Symbola_hint.ttf"

# CJK 字符检测
CJK_PATTERN = None

def is_cjk(char: str) -> bool:
    """检测单个字符是否为 CJK"""
    global CJK_PATTERN
    if CJK_PATTERN is None:
        CJK_PATTERN = re.compile(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]')
    return bool(CJK_PATTERN.match(char))

def has_cjk(text: str) -> bool:
    """检测文本是否包含 CJK 字符"""
    return any(is_cjk(c) for c in text)

def is_emoji(char: str) -> bool:
    """检测是否为 Emoji"""
    cp = ord(char)
    # Emoji 區塊
    if (0x1F300 <= cp <= 0x1F9FF): return True  # 雜項符號和擴充
    if (0x2600 <= cp <= 0x26FF): return True     # 雜項符號
    if (0x2700 <= cp <= 0x27BF): return True     # 裝飾符號
    if (0x1F600 <= cp <= 0x1F64F): return True    # 表情符號
    if (0x1F680 <= cp <= 0x1F6FF): return True    # 交通和地圖符號
    if (0x1F1E6 <= cp <= 0x1F1FF): return True    # 國旗
    if (0x2139 <= cp <= 0x2139): return True     # ℹ️ - Information Source
    if (0x2194 <= cp <= 0x2199): return True     # 箭頭
    if (0x21A9 <= cp <= 0x21AA): return True     # 回溯箭頭
    if (0x231A <= cp <= 0x231B): return True     # 鐘和時間
    if (0xFE0F <= cp <= 0xFE0F): return True     # 變體選擇符（彩色 Emoji）
    return False

def split_mixed_text(text: str) -> List[tuple]:
    """分割混合文字，返回 [(字元, 字體類型), ...]"""
    result = []
    i = 0
    while i < len(text):
        char = text[i]
        cp = ord(char)
        
        # 跳過變體選擇符 U+FE0F（小圈圈）
        if cp == 0xFE0F:
            i += 1
            continue
        
        if is_emoji(char):
            result.append((char, 'emoji'))
        elif is_cjk(char):
            result.append((char, 'chinese'))
        else:
            j = i
            while j < len(text):
                next_cp = ord(text[j]) if j < len(text) else 0
                if is_emoji(text[j]) or next_cp == 0xFE0F or is_cjk(text[j]):
                    break
                j += 1
            result.append((text[i:j], 'ascii'))
            i = j - 1
        i += 1
    return result

def clean_text(text: str) -> str:
    """清理文字，保留 Emoji"""
    if not text:
        return text
    return text

def hex_to_rgb(hex_color: str) -> tuple:
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def load_font(size: int, chinese: bool = False, emoji: bool = False):
    """加载字体"""
    if chinese and os.path.exists(CHINESE_FONT_PATH):
        try:
            return ImageFont.truetype(CHINESE_FONT_PATH, size)
        except:
            pass
    
    if emoji and os.path.exists(EMOJI_FONT_PATH):
        try:
            return ImageFont.truetype(EMOJI_FONT_PATH, size)
        except:
            pass

    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        None
    ]
    for path in font_paths:
        if path and os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except:
                continue
    return ImageFont.load_default()

def get_mixed_text_size(draw, text: str, chinese_font: ImageFont.FreeTypeFont, emoji_font: ImageFont.FreeTypeFont) -> tuple:
    """計算混合文字的尺寸"""
    chunks = split_mixed_text(text)
    total_width = 0
    max_height = 0
    
    for chunk, chunk_type in chunks:
        if chunk_type == 'emoji':
            try:
                bbox = draw.textbbox((0, 0), chunk, font=emoji_font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
            except:
                w, h = len(chunk) * emoji_font.size * 0.4, emoji_font.size
        elif chunk_type == 'chinese':
            try:
                bbox = draw.textbbox((0, 0), chunk, font=chinese_font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
            except:
                w, h = len(chunk) * chinese_font.size * 1.2, chinese_font.size
        else:  # ascii
            try:
                bbox = draw.textbbox((0, 0), chunk, font=chinese_font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
            except:
                w, h = len(chunk) * chinese_font.size * 0.4, chinese_font.size
        
        total_width += w
        max_height = max(max_height, h)
    
    return total_width, max_height

def draw_mixed_text(draw, text: str, x: int, y: int, chinese_font: ImageFont.FreeTypeFont, emoji_font: ImageFont.FreeTypeFont, color: tuple) -> int:
    """繪製混合文字，返回總寬度"""
    chunks = split_mixed_text(text)
    current_x = x
    
    for chunk, chunk_type in chunks:
        if chunk_type == 'emoji':
            font = emoji_font
            # Emoji 向下偏移以對齊中文基線
            baseline_offset = chinese_font.size - font.size + 4
            emoji_y = y + baseline_offset
        elif chunk_type == 'chinese':
            font = chinese_font
            emoji_y = y
        else:
            font = chinese_font
            emoji_y = y
        
        try:
            draw.text((current_x, emoji_y), chunk, font=font, fill=color)
            bbox = draw.textbbox((current_x, emoji_y), chunk, font=font)
            width = bbox[2] - bbox[0]
        except:
            width = len(chunk) * font.size * 0.4
        
        current_x += width
    
    return current_x - x

def get_text_size(draw, text: str, font) -> tuple:
    """获取文字尺寸（考虑 CJK 字符）"""
    text = clean_text(text)
    if not text:
        return 0, font.size

    if has_cjk(text):
        cjk_count = sum(1 for c in text if is_cjk(c))
        ascii_count = len(text) - cjk_count
        estimated_width = ascii_count * font.size * 0.4 + cjk_count * font.size * 1.2
        return estimated_width, font.size

    if draw:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    else:
        return len(text) * font.size * 0.6, font.size

def get_text_lines(text: str, max_width: int, font, draw) -> List[str]:
    """获取文字行数（自动换行，不裁剪）"""
    text = clean_text(text)
    if not text:
        return [""]

    cjk_mode = has_cjk(text)

    def char_width(char: str) -> float:
        if cjk_mode and is_cjk(char):
            return font.size * 1.2
        return font.size * 0.4

    def text_width(s: str) -> float:
        return sum(char_width(c) for c in s)

    if text_width(text) <= max_width:
        return [text]

    lines = []
    current_line = ""

    for char in text:
        test_line = current_line + char
        if text_width(test_line) <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = char

    if current_line:
        lines.append(current_line)

    return lines if lines else [""]

def get_status_color(status_str: str) -> str:
    """根据状态返回颜色"""
    s = str(status_str).lower()
    if any(x in s for x in ["運行", "active", "online", "success", "ok"]):
        return "#22c55e"
    elif any(x in s for x in ["維護", "warning", "warn", "pending"]):
        return "#eab308"
    elif any(x in s for x in ["離線", "error", "fail", "offline"]):
        return "#ef4444"
    return "#6b7280"

def calculate_column_widths(page_data, font, header_font, draw):
    """计算列宽（使用真实 draw 对象）"""
    if not page_data:
        return {}

    headers = list(page_data[0].keys())
    col_widths = {}

    for header in headers:
        h_width, _ = get_text_size(draw, header, header_font)
        max_width = h_width

        for row in page_data:
            val = str(row.get(header, ""))
            w, _ = get_text_size(draw, val, font)
            max_width = max(max_width, w)

        col_widths[header] = max_width + STYLE.cell_padding * 2

    return col_widths

def draw_rounded_rectangle(draw, xy, radius: int, fill=None, outline=None, width: int = 1):
    """画圆角矩形"""
    x1, y1, x2, y2 = xy
    draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill, outline=outline, width=width)
    draw.arc([x1, y1, x1 + radius * 2, y1 + radius * 2], 180, 270, fill=fill)
    draw.arc([x2 - radius * 2, y1, x2, y1 + radius * 2], 270, 360, fill=fill)
    draw.arc([x1, y2 - radius * 2, x1 + radius * 2, y2], 90, 180, fill=fill)
    draw.arc([x2 - radius * 2, y2 - radius * 2, x2, y2], 0, 90, fill=fill)
    draw.rectangle([x1, y1 + radius, x1 + radius, y2 - radius], fill=fill)
    draw.rectangle([x2 - radius, y1 + radius, x2, y2 - radius], fill=fill)

def draw_table(data: List[Dict], output_path: str, page: int = 1,
               sort_by: str = None, sort_asc: bool = True, config: StyleConfig = STYLE):
    """绘制表格（支持自动换行）"""
    global STYLE
    STYLE = config

    # 排序
    if sort_by and data:
        data = sorted(data, key=lambda x: str(x.get(sort_by, "")), reverse=not sort_asc)

    # 分页
    total_rows = len(data)
    rows_per_page = config.rows_per_page
    total_pages = (total_rows + rows_per_page - 1) // rows_per_page if rows_per_page > 0 else 1
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * rows_per_page
    end_idx = min(start_idx + rows_per_page, total_rows)
    page_data = data[start_idx:end_idx]

    if not page_data:
        print("❌ 没有数据")
        return

    headers = list(page_data[0].keys())

    # 临时 draw 对象
    temp_img = Image.new('RGB', (100, 100), config.bg_color)
    temp_draw = ImageDraw.Draw(temp_img)

    # 分離載入中文字體和 Emoji 字體
    chinese_font = load_font(config.font_size, chinese=True)
    emoji_font = load_font(config.font_size, emoji=True)
    header_chinese_font = load_font(config.header_font_size, chinese=True)
    header_emoji_font = load_font(config.header_font_size, emoji=True)
    
    # 預設字體（使用中文字體）
    font = chinese_font
    header_font = header_chinese_font
    
    col_widths = calculate_column_widths(page_data, font, header_font, temp_draw)

    # 计算每行需要的最大行数
    def get_cell_lines(header: str, value: str, max_width: int) -> int:
        if "狀態" in header.lower() or "status" in header.lower():
            return 1
        lines = get_text_lines(value, max_width - config.cell_padding * 2, font, temp_draw)
        return len(lines)

    row_max_lines = []
    for row in page_data:
        max_lines = 1
        for h in headers:
            lines = get_cell_lines(h, str(row.get(h, "")), col_widths[h])
            max_lines = max(max_lines, lines)
        row_max_lines.append(max_lines)

    max_row_lines = max(row_max_lines) if row_max_lines else 1
    dynamic_row_height = config.row_height * max_row_lines

    # 计算总宽度和高度
    total_width = sum(col_widths.values()) + config.padding * 2
    total_height = config.header_height + dynamic_row_height * len(page_data) + config.padding * 2 + 60

    total_width = int(total_width)
    total_height = int(total_height)

    img = Image.new('RGB', (total_width, total_height), hex_to_rgb(config.bg_color))
    draw = ImageDraw.Draw(img)

    # 背景圖片
    if config.bg_image and os.path.exists(config.bg_image):
        try:
            bg_img = Image.open(config.bg_image).convert('RGBA')
            bg_img = bg_img.resize((total_width, total_height), Image.Resampling.LANCZOS)
            img.paste(bg_img, (0, 0), bg_img)
        except Exception as e:
            print(f"⚠️ 無法載入背景圖片: {e}")

    # 邊框圖片
    border_img = None
    if config.border_image and os.path.exists(config.border_image):
        try:
            border_img = Image.open(config.border_image).convert('RGBA')
        except Exception as e:
            print(f"⚠️ 無法載入邊框圖片: {e}")

    # 畫邊框
    if border_img:
        # 將邊框圖片縮放並貼上
        border_resized = border_img.resize((total_width, total_height), Image.Resampling.LANCZOS)
        img.paste(border_resized, (0, 0), border_resized)
    else:
        draw_rounded_rectangle(draw, [5, 5, total_width - 5, total_height - 5],
                          config.border_radius, fill=None,
                          outline=hex_to_rgb(config.border_color),
                          width=config.border_width)

    y = config.padding

    # 表头
    header_bg_rgb = hex_to_rgb(config.header_bg)
    draw_rounded_rectangle(draw, [config.padding, y,
                                  total_width - config.padding,
                                  y + config.header_height],
                          config.border_radius, fill=header_bg_rgb)

    x = config.padding + config.cell_padding
    for h in headers:
        clean_h = clean_text(h)
        draw.text((x, y + (config.header_height - config.header_font_size) // 2),
                 clean_h, font=header_font, fill=hex_to_rgb(config.header_text))
        x += col_widths[h]

    y += config.header_height

    # 数据行
    for row_idx, row in enumerate(page_data):
        row_bg = config.alt_row_color if row_idx % 2 == 0 else config.bg_color
        row_start_y = y + dynamic_row_height * row_idx
        row_end_y = row_start_y + dynamic_row_height

        draw.rectangle([config.padding, row_start_y,
                       total_width - config.padding, row_end_y],
                      fill=hex_to_rgb(row_bg))

        if row_idx < len(page_data) - 1:
            draw.line([config.padding, row_end_y,
                      total_width - config.padding, row_end_y],
                     fill=hex_to_rgb(config.border_color), width=1)

        x = config.padding + config.cell_padding
        for h in headers:
            val = str(row.get(h, ""))

            is_status = "狀態" in h.lower() or "status" in h.lower()
            is_status_val = any(x in val.lower() for x in ["運行", "active", "online", "success", "維護", "warning", "warn", "離線", "error", "fail", "offline", "pending"])

            cell_y_start = row_start_y
            cell_content_height = dynamic_row_height

            if is_status or is_status_val:
                status_color = get_status_color(val)
                draw.ellipse([x, cell_y_start + 14, x + 12, cell_y_start + 26],
                           fill=hex_to_rgb(status_color), outline=None)
                clean_val = clean_text(val)
                text_y = cell_y_start + (cell_content_height - config.font_size) // 2
                draw.text((x + 18, text_y), clean_val, font=font, fill=hex_to_rgb(config.text_color))
            else:
                max_width = col_widths[h] - config.cell_padding * 2
                lines = get_text_lines(val, max_width, font, draw)

                total_text_height = len(lines) * font.size
                text_y = cell_y_start + (cell_content_height - total_text_height) // 2

                for line_idx, line in enumerate(lines):
                    line_y = text_y + line_idx * font.size
                    # 使用混合字體繪圖
                    draw_mixed_text(draw, line, x, line_y, chinese_font, emoji_font, hex_to_rgb(config.text_color))

            x += col_widths[h]

    # 底部信息
    footer_y = total_height - 50
    draw.rectangle([config.padding, footer_y,
                   total_width - config.padding, total_height - 10],
                  fill=hex_to_rgb("#0f3460"), width=0)

    if config.show_page_info and total_pages > 1:
        page_text = f"第 {page} 頁 / 共 {total_pages} 頁  |  共 {total_rows} 筆資料"
        text_w = len(page_text) * config.font_size * 0.6
        draw.text(((total_width - text_w) // 2, footer_y + 12),
                 page_text, font=font, fill=hex_to_rgb(config.text_color))

    # 滚动标记
    if page < total_pages:
        draw.text((total_width - config.padding - 100, footer_y + 12), "↓ 向下滾動",
                 font=font, fill=hex_to_rgb(config.highlight_color))
    if page > 1:
        draw.text((total_width - config.padding - 60, footer_y + 12), "↑ 向上滾動",
                 font=font, fill=hex_to_rgb(config.highlight_color))

    img.save(output_path, quality=95)
    print(f"✅ 图片已保存: {output_path}")
    print(f"   尺寸: {total_width}x{total_height} | 页码: {page}/{total_pages} | 行数: {len(page_data)} | 每行最多 {max_row_lines} 行")

def load_data(json_file: str) -> List[Dict]:
    """加载数据（支持多种格式）"""
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 格式 1: [{"列名": 值}, ...]
    if isinstance(data, list):
        return data
    
    # 格式 2: {"headers": [...], "rows": [[...], ...]}
    if isinstance(data, dict):
        if 'headers' in data and 'rows' in data:
            headers = data['headers']
            result = []
            for row in data['rows']:
                row_dict = {}
                for i, h in enumerate(headers):
                    row_dict[h] = row[i] if i < len(row) else ""
                result.append(row_dict)
            return result
        elif 'data' in data:
            return data['data']
    
    return [data]

def load_images(json_file: str) -> Dict:
    """從 JSON 載入圖片設定"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
            return {
                'bg_image': data.get('bg_image', ''),
                'border_image': data.get('border_image', '')
            }
    except:
        pass
    return {'bg_image': '', 'border_image': ''}

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        print("\n用法: python3 zentable.py <input.json> <output.png> [options]")
        print("\n示例:")
        print('  python3 zentable.py data.json output.png')
        print('  python3 zentable.py data.json out.png --dark --page 2')
        sys.exit(1)

    input_json = sys.argv[1]
    output_png = sys.argv[2]

    page = 1
    sort_by = None
    sort_asc = True
    theme = "dark"

    # 預先定義主題
    themes = {
        "dark": StyleConfig(
            bg_color="#1a1a2e", text_color="#ffffff",
            header_bg="#0f3460", header_text="#ffffff",  # Changed header_text to white for contrast
            alt_row_color="#16213e", border_color="#4a5568",
            highlight_color="#e94560"
        ),
        "light": StyleConfig(
            bg_color="#f8f9fa", text_color="#212529",
            header_bg="#e9ecef", header_text="#495057",
            alt_row_color="#ffffff", border_color="#dee2e6",
            highlight_color="#0d6efd"
        ),
        "cyberpunk": StyleConfig(
            bg_color="#0d0221", text_color="#00ff9f",
            header_bg="#ff00ff", header_text="#000000",
            alt_row_color="#1a1a3e", border_color="#00ff9f",
            highlight_color="#ffff00"
        ),
        "forest": StyleConfig(
            bg_color="#1a2f1a", text_color="#90ee90",
            header_bg="#2d5a2d", header_text="#ffffff",
            alt_row_color="#243424", border_color="#4a7a4a",
            highlight_color="#7fff00"
        ),
        "ocean": StyleConfig(
            bg_color="#0a1929", text_color="#64b5f6",
            header_bg="#1565c0", header_text="#ffffff",
            alt_row_color="#0d2137", border_color="#2196f3",
            highlight_color="#00bcd4"
        ),
        "sunset": StyleConfig(
            bg_color="#2d1f1f", text_color="#ffcc80",
            header_bg="#bf360c", header_text="#ffffff",
            alt_row_color="#3d2f2f", border_color="#ff7043",
            highlight_color="#ffab40"
        ),
        "rose": StyleConfig(
            bg_color="#2f1a1a", text_color="#f8bbd9",
            header_bg="#c2185b", header_text="#ffffff",
            alt_row_color="#3f2a2a", border_color="#ec407a",
            highlight_color="#f48fb1"
        ),
        "midnight": StyleConfig(
            bg_color="#0f0f23", text_color="#b0a0ff",
            header_bg="#2a2a4a", header_text="#e0e0ff",
            alt_row_color="#1a1a33", border_color="#5a5a8a",
            highlight_color="#8070ff"
        )
    }
    
    for i in range(3, len(sys.argv)):
        arg = sys.argv[i]
        if arg == "--page" and i + 1 < len(sys.argv):
            page = int(sys.argv[i + 1])
        elif arg == "--sort" and i + 1 < len(sys.argv):
            sort_by = sys.argv[i + 1]
        elif arg == "--asc":
            sort_asc = True
        elif arg == "--desc":
            sort_asc = False
        elif arg.startswith("--") and arg[2:] in themes:
            theme = arg[2:]

    try:
        data = load_data(input_json)
    except Exception as e:
        print(f"❌ 加载失败: {e}")
        sys.exit(1)

    # 取得基礎配置
    config = themes.get(theme, themes["dark"])

    # 從 JSON 載入圖片設定並覆蓋
    images = load_images(input_json)
    if images['bg_image']:
        config.bg_image = images['bg_image']
    if images['border_image']:
        config.border_image = images['border_image']

    draw_table(data, output_png, page=page, sort_by=sort_by, sort_asc=sort_asc, config=config)
    total_pages = (len(data) + config.rows_per_page - 1) // config.rows_per_page
    print(f"\n📊 统计: {len(data)} 行数据，分 {total_pages} 页")

if __name__ == "__main__":
    main()
