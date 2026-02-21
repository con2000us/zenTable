#!/usr/bin/env python3
"""
ZenTable - Smart table renderer（參照用）

本檔案為文件參照副本；本專案實際執行版本為 `scripts/zeble_render.py`，
後端端點會固定呼叫該檔案，不再依賴外部 `/opt/...`。

自動偵測可用渲染方式：
1. CSS + Chrome（效果更好）
2. Pure Python + PIL（無依賴 fallback）

用法: python3 scripts/zeble_render.py <data.json> <output.png> [options]

選項:
  --force-pil        強制使用 PIL 渲染
  --force-css        強制使用 CSS + Chrome 渲染
  --transparent      產出透空背景 PNG（僅 CSS 模式；Chrome --default-background-color=00000000 直接透明）
  --theme FILE       主題檔案路徑
  --theme-name NAME  內建主題名稱
  --bg MODE          背景：transparent | theme | #RRGGBB（指定色）
  --width N          強制 viewport 寬度（CSS）或輸出寬度（PIL）
  --scale N          輸出尺寸倍數（預設 1.0）
  --per-page N       每頁列數（預設 15）
  --fill-width M     搭配 --width 使用：background | container | scale | no-shrink
"""

import json
import sys
import os
import re
import glob
import subprocess
import zipfile
import time
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass

# =============================================================================
# ASCII RENDERER
# =============================================================================

@dataclass
class ASCIIStyle:
    border_style: str = "double"  # single, double, grid, markdown
    padding: int = 2
    align: str = "left"
    header_align: str = "center"

# ASCII 框線樣式
ASCII_STYLES = {
    "single": {
        "tl": "+", "tr": "+", "bl": "+", "br": "+",
        "h": "-", "v": "|",
        "header": "+", "row": "+", "footer": "+"
    },
    "double": {
        "tl": "╔", "tr": "╗", "bl": "╚", "br": "╝",
        "h": "═", "v": "║",
        "header": "╠", "row": "╠", "footer": "╠"
    },
    "grid": {
        "tl": "┌", "tr": "┐", "bl": "└", "br": "┘",
        "h": "─", "v": "│",
        "header": "├", "row": "├", "footer": "├"
    },
    "markdown": {
        "tl": "|", "tr": "|", "bl": "|", "br": "|",
        "h": "-", "v": "|",
        "header": "|", "row": "|", "footer": "|"
    }
}

def calculate_column_widths(headers, rows, padding=2):
    """計算每列最大寬度"""
    widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    return [w + padding * 2 for w in widths]

def align_text(text, width, align="left"):
    """對齊文字"""
    text = str(text)
    if align == "left":
        return text.ljust(width)
    elif align == "right":
        return text.rjust(width)
    else:  # center
        return text.center(width)

def render_ascii(data: dict, theme: dict = None, style: ASCIIStyle = None) -> str:
    """使用 ASCII 渲染表格，主題來自 themes/text/<name>/template.json 的 params"""
    if style is None:
        params = (theme or {}).get("params") or {}
        style = ASCIIStyle(
            border_style=params.get("style", "double"),
            padding=int(params.get("padding", 2)),
            align=params.get("align", "left"),
            header_align=params.get("header_align", "center"),
        )
    
    headers = data.get("headers", [])
    rows = data.get("rows", [])
    title = data.get("title", "")
    footer = data.get("footer", "")
    
    # 計算列寬
    widths = calculate_column_widths(headers, rows, style.padding)
    total_width = sum(widths) + len(widths) + 1
    
    # 獲取框線樣式
    s = ASCII_STYLES.get(style.border_style, ASCII_STYLES["double"])
    
    lines = []
    
    # 標題
    if title:
        title_line = align_text(title, total_width - 4, "center")
        lines.append(f"{s['tl']}{s['h'] * 2} {title_line} {s['h'] * 2}{s['tr']}")
    
    # 頂部框線
    top_line = s['tl'] + s['h'] * (total_width - 2) + s['tr']
    lines.append(top_line)
    
    # 表頭
    if headers:
        header_cells = []
        for i, h in enumerate(headers):
            cell = align_text(h, widths[i], style.header_align)
            header_cells.append(f" {cell} ")
        lines.append(s['v'] + s['v'].join(header_cells) + s['v'])
        
        # 表頭分隔線
        sep_cells = []
        for w in widths:
            sep_cells.append(s['h'] * (w + 2))
        sep_line = s['header'] + s['header'].join(sep_cells) + s['header']
        lines.append(sep_line)
    
    # 資料列
    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            c = align_text(cell, widths[i], style.align)
            cells.append(f" {c} ")
        lines.append(s['v'] + s['v'].join(cells) + s['v'])
    
    # 底部框線
    bottom_line = s['bl'] + s['h'] * (total_width - 2) + s['br']
    lines.append(bottom_line)
    
    # 底部文字
    if footer:
        footer_line = align_text(footer, total_width - 4, "center")
        lines.append(f"{s['bl']}{s['h'] * 2} {footer_line} {s['h'] * 2}{s['br']}")
    
    return "\n".join(lines)

class TemplateEngine:
    """Pure Python lightweight template engine"""
    
    def __init__(self):
        self.helpers: Dict[str, Callable] = {}
        self.register_default_helpers()
    
    def register_helper(self, name: str, func: Callable):
        self.helpers[name] = func
    
    def register_default_helpers(self):
        self.helpers['upper'] = lambda x: str(x).upper()
        self.helpers['lower'] = lambda x: str(x).lower()
        self.helpers['currency'] = lambda x: f"${x}" if isinstance(x, (int, float)) else str(x)
        self.helpers['percent'] = lambda x: f"{x}%" if isinstance(x, (int, float)) else str(x)
        self.helpers['even'] = lambda x: x % 2 == 0
        self.helpers['odd'] = lambda x: x % 2 == 1
    
    def render(self, template: str, context: Dict) -> str:
        result = template
        result = self._render_conditionals(result, context)
        result = self._render_loops(result, context)
        result = self._render_variables(result, context)
        return result
    
    def _render_variables(self, template: str, context: Dict) -> str:
        def replace(match):
            var_path = match.group(1).strip()
            keys = var_path.split('.')
            value = context
            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key, '')
                return str(value) if value is not None else ''
        return re.sub(r'\{\{([^{}][^{}]*?)\}\}', replace, template)
    
    def _render_conditionals(self, template: str, context: Dict) -> str:
        def process_if(match):
            condition = match.group(1).strip()
            content = match.group(2)
            if '&&' in condition:
                return content if all(self._check_condition(c.strip(), context) for c in condition.split('&&')) else ''
            return content if self._check_condition(condition, context) else ''
        pattern = r'\{\{#if\s+([^}]+)\}\}(.*?)\{\{/if\}\}'
        while re.search(pattern, template):
            template = re.sub(pattern, process_if, template, flags=re.DOTALL)
        return template
    
    def _check_condition(self, condition: str, context: Dict) -> bool:
        condition = condition.strip()
        for op in ['==', '!=']:
            if op in condition:
                a, b = condition.split(op)
                return self._eval_value(a.strip(), context) == self._eval_value(b.strip(), context)
        return bool(self._eval_value(condition, context))
    
    def _eval_value(self, value: str, context: Dict) -> Any:
        value = value.strip()
        if value.startswith('"') and value.endswith('"'):
            return value[1:-1]
        try:
            return float(value) if '.' in value else int(value)
        except:
            pass
        if value.lower() == 'true':
            return True
        if value.lower() == 'false':
            return False
        return context.get(value, '')
    
    def _render_loops(self, template: str, context: Dict) -> str:
        pattern = r'\{\{#each\s+([^{}]+)\}\}(.*?)\{\{/each\}\}'
        def process_loop(match):
            list_name = match.group(1).strip()
            content = match.group(2)
            list_value = self._eval_value(list_name, context)
            if not isinstance(list_value, (list, tuple)):
                return ''
            results = []
            for idx, item in enumerate(list_value):
                loop_ctx = context.copy()
                loop_ctx['@index'] = idx
                loop_ctx['@even'] = idx % 2 == 0
                loop_ctx['@odd'] = idx % 2 == 1
                item_html = content
                item_html = self._render_variables(item_html, loop_ctx)
                results.append(item_html)
            return ''.join(results)
        while re.search(pattern, template):
            template = re.sub(pattern, process_loop, template, flags=re.DOTALL)
        return template


# =============================================================================
# CSS RENDERER
# =============================================================================

def check_chrome_available() -> bool:
    """檢查 Chrome headless 是否可用"""
    try:
        result = subprocess.run(
            ['which', 'google-chrome'],
            capture_output=True, timeout=5
        )
        return result.returncode == 0
    except:
        return False

# 透空背景：現代 Chrome 支援 --default-background-color=RRGGBBAA（8 位 hex，Alpha=00 為透明）
# 直接輸出透明 PNG，無需 chroma key 後製，陰影半透明也不會出問題
TRANSPARENT_BG_HEX = "00000000"  # RGBA，Alpha=0 = 透明

def _make_png_background_transparent_chroma(png_path: str, chroma_rgb: tuple = (255, 0, 255), tolerance: int = 8) -> bool:
    """Fallback：以 chroma key 後製透空（僅在 Chrome 不支援 --default-background-color 時使用）。"""
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
    """裁切 PNG 至內容邊界，移除多餘空白。transparent=True 時以 alpha 通道判斷；否則以角落為背景參考。"""
    try:
        from PIL import Image
        img = Image.open(png_path)
        w, h = img.size
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        
        if transparent:
            # 透空：alpha > 0 的像素邊界
            alpha = img.split()[3]
            bbox = alpha.getbbox()
        else:
            # 不透明：以四角採樣作為背景參考，建立遮罩後用 getbbox
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

def _hex_to_chrome_bg(hex_color: str) -> str:
    """將 #RRGGBB 或 #RRGGBBAA 轉為 Chrome --default-background-color 格式（8 位 RRGGBBAA）"""
    h = hex_color.lstrip('#')
    if len(h) == 6:
        return h + 'FF'
    if len(h) == 8:
        return h
    return '000000FF'

def render_css(html: str, output_path: str, transparent: bool = False, html_dir: str = None,
               viewport_width: int = None, viewport_height: int = None, bg_color: str = None,
               skip_crop: bool = False) -> bool:
    """使用 Chrome headless 渲染。transparent=True 時以 --default-background-color=00000000 直接產出透明 PNG。
    html_dir: 若指定，HTML 寫入此目錄（使相對路徑資源可正確解析）；否則與 output 同目錄。
    viewport_width, viewport_height: 若提供則設定 Chrome 視窗尺寸，使截圖依內容大小。
    bg_color: 若指定（#RRGGBB），覆蓋背景色；transparent 優先於 bg_color。"""
    if html_dir:
        ts = str(int(time.time() * 1000))
        html_file = os.path.join(html_dir, f"render_{ts}.html")
    else:
        html_file = output_path.replace('.png', '.html')
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    parts = [
        "xvfb-run -a google-chrome --headless",
        "--proxy-server=http://localhost:8191",
        f"--screenshot={output_path}",
        "--virtual-time-budget=3000",
        "--hide-scrollbars",
        "--disable-gpu",
    ]
    if viewport_width and viewport_height:
        parts.append(f"--window-size={viewport_width},{viewport_height}")
    if transparent:
        parts.append(f"--default-background-color={TRANSPARENT_BG_HEX}")
    elif bg_color and bg_color.startswith('#'):
        parts.append(f"--default-background-color={_hex_to_chrome_bg(bg_color)}")
    parts.append(f"file://{html_file}")
    cmd = " ".join(parts)
    
    result = os.system(cmd)
    
    if os.path.exists(html_file):
        os.remove(html_file)
    
    if result != 0 or not os.path.exists(output_path):
        return False
    # 依內容邊界裁切，移除多餘空白；若 skip_crop（使用者明確指定寬度）則不裁切
    if not skip_crop:
        crop_to_content_bounds(output_path, padding=2, transparent=transparent)
    return True

def _parse_font_size_px(style_str: str, default: int = 14) -> int:
    """從 CSS 字串解析 font-size（px），例：font-size: 14px;"""
    if not style_str:
        return default
    m = re.search(r'font-size:\s*(\d+)px', style_str, re.I)
    return int(m.group(1)) if m else default

def _parse_width_px(style_str: str) -> Optional[int]:
    """從 CSS 字串解析 width/min-width（px），例：width: 2400px; 或 min-width: 1200px;"""
    if not style_str:
        return None
    for pat in (r'width:\s*(\d+)px', r'min-width:\s*(\d+)px'):
        m = re.search(pat, style_str, re.I)
        if m:
            return int(m.group(1))
    return None

# Chrome headless 視窗尺寸上限（高度約 16384px）
MAX_VIEWPORT_DIM = 16384

def estimate_css_viewport_width_height(data: dict, theme: dict) -> tuple:
    """依表格內容估算 CSS 截圖所需的 viewport 寬高。回傳 (width, height)。"""
    styles = theme.get("styles", {}) or {}
    header_fs = _parse_font_size_px(styles.get("th", ""), 18)
    cell_fs = _parse_font_size_px(styles.get("td", ""), 14)
    title_fs = _parse_font_size_px(styles.get("title", ""), 20)
    footer_fs = _parse_font_size_px(styles.get("footer", ""), 12)
    
    headers = data.get("headers", [])
    rows = data.get("rows", [])
    col_count = len(headers) if headers else 1
    
    col_widths = []
    for i in range(col_count):
        w = measure_text_width(headers[i] if i < len(headers) else "", header_fs)
        for row in rows:
            if i < len(row):
                w = max(w, measure_text_width(cell_text(row[i]), cell_fs))
        w = min(400, max(60, w + 28))  # padding
        col_widths.append(w)
    
    table_width = sum(col_widths)
    # CSS 主題 td 有 padding: 12px 14px，每列約 45px；header/footer 也較高
    row_height = max(int(cell_fs * 2), 45)
    header_height = 55
    footer_height = 50
    
    width = 40 + table_width
    height = 50  # body 外層 padding
    if data.get("title"):
        height += 60  # title padding 20px + font
    height += header_height + len(rows) * row_height + footer_height
    
    margin = 40
    scale_w, scale_h = 1.15, 1.25  # 高度預留多些（換行、padding 變異）
    vw = int((width + margin) * scale_w)
    vh = int((height + margin) * scale_h)
    
    # 若主題 body/container/table 有明確 width/min-width，視為最低 viewport 寬度，避免截圖被裁切
    # 主題可能使用 "container" 或 ".container"；table 可能為 "table" 或 ".data-table"
    explicit_width = False
    _style_keys = {"body": ("body",), "container": ("container", ".container"), "table": ("table", ".data-table")}
    for key, try_keys in _style_keys.items():
        raw = ""
        for k in try_keys:
            raw = styles.get(k, "")
            if raw:
                break
        w = _parse_width_px(raw)
        if w is not None and w > vw:
            vw = min(w, MAX_VIEWPORT_DIM)
            explicit_width = True
    return (vw, min(vh, MAX_VIEWPORT_DIM), explicit_width)

def generate_css_html(data: dict, theme: dict, transparent: bool = False, table_width_pct: int = None) -> str:
    """生成 CSS 版本的 HTML。table_width_pct: 若指定（如 96），表格填滿該比例的 viewport 寬度。"""
    engine = TemplateEngine()
    
    headers = data.get("headers", [])
    rows = data.get("rows", [])
    title = data.get("title", "")
    footer = data.get("footer", "Generated by ZenTable")
    
    # 斑馬紋 rows（支援 colspan/rowspan）
    rows_html = build_css_rows_html(rows)
    
    headers_html = ''.join(f'<th>{h}</th>' for h in headers)
    
    styles = theme.get("styles", {})
    # 正確對應 HTML：body/table/th/td 為標籤選擇器，其餘為 class；規格中的 .header/.cell-header/.cell 對應到 .title/th/td
    TAG_SELECTORS = {'body', 'table', 'thead', 'tbody', 'tr', 'th', 'td'}
    def css_selector(key):
        if key in ('.header', 'header'):
            return '.title'
        if key in ('.cell-header', 'cell-header'):
            return 'th'
        if key in ('.cell', 'cell'):
            return 'td'
        if key.startswith('.'):
            return key
        if key in TAG_SELECTORS:
            return key
        if key == 'tbody_tr':
            return 'tbody tr'
        if key == 'tr_even':
            return 'tr.tr_even'
        if key == 'tr_odd':
            return 'tr.tr_odd'
        # 用於指定欄位：th:nth-child(N), td:nth-child(N) 或 col_N（N 為 1-based 欄位編號）
        if ':nth-child' in key or (',' in key and ':' in key):
            return key
        if key.startswith('col_') and key[4:].isdigit():
            n = key[4:]
            return f'th:nth-child({n}), td:nth-child({n})'
        return '.' + key
    css = '\n'.join(f'{css_selector(k)} {{{v}}}' for k, v in styles.items())
    css += "\ntd { white-space: pre-wrap !important; }"
    if transparent:
        # 表格透空：移除外層色塊兜底，body/container 透明，不覆蓋 th/td 列色（保留可讀性）
        css += "\nhtml, body, div.container, .container { background: transparent !important; background-image: none !important; }"
    else:
        # 非透空時：body 背景透明，色塊僅在 .container，避免 body 背景溢出 table 寬度
        css += "\nbody { background: transparent !important; background-image: none !important; }"
    if table_width_pct:
        # 指定 viewport 寬度時，表格填滿該比例
        css += f"\n.container {{ width: {table_width_pct}% !important; max-width: {table_width_pct}% !important; box-sizing: border-box; }}"
        css += "\ntable { width: 100% !important; table-layout: auto; }"
    else:
        # 僅當主題未指定 container 寬度時才加 fit-content，否則尊重使用者設定的 width
        _container_style = styles.get("container", "") or styles.get(".container", "")
        if _parse_width_px(_container_style) is None:
            css += "\n.container { width: fit-content !important; max-width: 100%; }"
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        {css}
    </style>
</head>
<body>
<div class="container">
{ f'<div class="title">{title}</div>' if title else '' }
<table>
{ f'<thead><tr>{headers_html}</tr></thead>' if headers else '' }
<tbody>
{rows_html}
</tbody>
</table>
{ f'<div class="footer">{footer}</div>' if footer else '' }
</div>
</body>
</html>"""
    return html


# =============================================================================
# PIL RENDERER (FALLBACK)
# =============================================================================

from PIL import Image, ImageDraw, ImageFont
import re

@dataclass
class PILStyle:
    bg_color: str = "#1a1a2e"
    text_color: str = "#ffffff"
    header_bg: str = "#0f3460"
    header_text: str = "#e94560"
    alt_row_color: str = "#16213e"
    border_color: str = "#4a5568"

def parse_color(c):
    """解析顏色格式：#RRGGBB、#RRGGBBAA、rgba(r,g,b,a)"""
    c = c.strip()
    
    # rgba(r,g,b,a) 格式
    if c.startswith('rgba('):
        parts = c[5:-1].split(',')
        if len(parts) == 4:
            r = int(parts[0].strip())
            g = int(parts[1].strip())
            b = int(parts[2].strip())
            a = float(parts[3].strip())
            return (r, g, b, int(a * 255))
    
    # #RRGGBBAA 格式
    if c.startswith('#') and len(c) == 9:
        c = c.lstrip('#')
        return tuple(int(c[i:i+2], 16) for i in (0, 2, 4, 6))
    
    # #RRGGBB 格式
    if c.startswith('#') and len(c) == 7:
        c = c.lstrip('#')
        return tuple(int(c[i:i+2], 16) for i in (0, 2, 4))
    
    # #RGB 格式
    if c.startswith('#') and len(c) == 4:
        c = c.lstrip('#')
        return tuple(int(c[i]*2, 16) for i in (0, 1, 2))
    
    raise ValueError(f"Unknown color format: {c}")

def hex_rgb(c):
    """向下相容：返回 RGB 元組"""
    color = parse_color(c)
    return color[:3]  # 忽略 alpha

# =============================================================================
# MIXED FONT RENDERER (中文 + Emoji)
# =============================================================================

# 字體路徑（依優先順序）
FONT_CJK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
# Emoji 字體：優先彩色 Noto Color Emoji，備援 Symbola（多路徑以支援不同發行版）
FONT_EMOJI_LIST = [
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/google-noto-emoji/NotoColorEmoji.ttf",
    "/usr/share/fonts/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/noto-color-emoji/NotoColorEmoji.ttf",
    "/usr/share/fonts/truetype/ancient-scripts/Symbola_hint.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

# 載入字體快取
_font_cache = {}
_emoji_font_available = None  # 快取可用的 emoji 字體

def get_font_cjk(size=16):
    """取得中文字體"""
    key = f"cjk_{size}"
    if key not in _font_cache:
        try:
            _font_cache[key] = ImageFont.truetype(FONT_CJK, size)
        except:
            _font_cache[key] = ImageFont.load_default()
    return _font_cache[key]

def _detect_emoji_font():
    """偵測可用的 emoji 字體，回傳 (字體路徑, 是否為彩色)。先試固定路徑，再掃描系統字型目錄。"""
    global _emoji_font_available
    if _emoji_font_available is not None:
        return _emoji_font_available

    def _try(path):
        try:
            ImageFont.truetype(path, 16)
            return path
        except Exception:
            return None

    for font_path in FONT_EMOJI_LIST:
        if os.path.isfile(font_path) and _try(font_path):
            _emoji_font_available = (font_path, "NotoColor" in font_path or "noto-color" in font_path.lower())
            return _emoji_font_available

    # 掃描系統字型目錄（不同發行版路徑不一）
    for base in ["/usr/share/fonts", "/usr/local/share/fonts"]:
        if not os.path.isdir(base):
            continue
        for pattern in ["*Noto*Emoji*.ttf", "*Noto*Color*Emoji*.ttf", "*Symbola*.ttf", "*Symbola*.otf"]:
            for path in glob.glob(os.path.join(base, pattern)) + glob.glob(os.path.join(base, "*", pattern)):
                if os.path.isfile(path) and _try(path):
                    _emoji_font_available = (path, "Color" in path or "color" in path)
                    return _emoji_font_available

    _emoji_font_available = (None, False)
    return _emoji_font_available

def get_font_emoji(size=16):
    """取得 Emoji 字體（自動選擇最佳可用字體）"""
    key = f"emoji_{size}"
    if key not in _font_cache:
        font_path, is_color = _detect_emoji_font()
        try:
            if font_path:
                _font_cache[key] = ImageFont.truetype(font_path, size)
            else:
                _font_cache[key] = ImageFont.load_default()
        except:
            _font_cache[key] = ImageFont.load_default()
    return _font_cache[key]

def is_color_emoji_font():
    """檢查目前使用的 emoji 字體是否為彩色"""
    _, is_color = _detect_emoji_font()
    return is_color

def get_font(size=16):
    """取得預設字體"""
    return get_font_cjk(size)

def is_emoji(char):
    """判斷是否為 Emoji"""
    # 顏色圈支援度不統一，統一替換為文字
    color_circles = {
        '🟢': '(綠)', '🟡': '(黃)', '🔴': '(紅)', '🟠': '(橙)',
        '🔵': '(藍)', '⚫': '(黑)', '⚪': '(白)', '🟣': '(紫)',
        '🟤': '(棕)', '🟣': '(紫)', '🟡': '(黃)'
    }
    if char in color_circles:
        # 標記為特殊字符（不當 emoji 渲染）
        return 'special'
    
    # Emoji Unicode 範圍
    emoji_ranges = [
        (0x1F300, 0x1F9FF),   # 雜項符號和圖形、擴展
        (0x2600, 0x26FF),     # 符號
        (0x2700, 0x27BF),     # 裝飾字母
        (0x1F600, 0x1F64F),   # 笑臉
        (0x1F300, 0x1F5FF),   # 符號和圖形
        (0x1F680, 0x1F6FF),   # 交通和地圖
        (0x1F1E0, 0x1F1FF),   # 國旗
        (0x1F900, 0x1F9FF),   # 補充符號
        (0x1FA00, 0x1FA6F),   # 象棋符號等
    ]
    code = ord(char)
    for start, end in emoji_ranges:
        if start <= code <= end:
            return True
    # 簡單判斷：如果是 emoji 通常是表情符號
    if char in "🀀🌐🎉✨💯✅❌⚠️📦🖥️💰📊🔄🔗🎨⚡🔧🛠️📦🖥️💰📊🔄":
        return True
    return False

def replace_color_circles(text):
    """替換顏色圈為文字（Symbola 不支援彩色圓形）"""
    color_circles = {
        '🟢': '(綠)', '🟡': '(黃)', '🔴': '(紅)', '🟠': '(橙)',
        '🔵': '(藍)', '⚫': '(黑)', '⚪': '(白)', '🟣': '(紫)',
        '🟤': '(棕)', '🟥': '(紅方)', '🟧': '(橙方)', '🟨': '(黃方)',
        '🟩': '(綠方)', '🟦': '(藍方)', '🟪': '(紫方)', '🟫': '(棕方)',
        '⬛': '(黑方)', '⬜': '(白方)'
    }
    for emoji, replacement in color_circles.items():
        text = text.replace(emoji, replacement)
    return text

def split_text_by_font(text):
    """將文字分段，返回 [(文字, 字體類型), ...]"""
    # 先替換顏色圈
    text = replace_color_circles(str(text))
    
    segments = []
    current_type = None
    current_text = ""
    
    for char in text:
        char_type = is_emoji(char)
        if char_type == 'special':
            char_type = 'cjk'
        elif char_type is True:
            char_type = 'emoji'  # 統一用字串，供 draw_text_with_mixed_fonts 比對
        
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

def measure_text_width(text: str, font_size: int) -> int:
    """使用混合字體測量文字寬度（不繪製）"""
    segments = split_text_by_font(str(text))
    total = 0
    for seg_text, font_type in segments:
        font = get_font_emoji(font_size) if font_type == "emoji" else get_font_cjk(font_size)
        try:
            bbox = font.getbbox(seg_text)
            total += bbox[2] - bbox[0]
        except Exception:
            total += font_size * len(seg_text) * 0.6
    return int(total)

def draw_text_with_mixed_fonts(draw, text, x, y, font_size, fill_color, baseline_offset=0):
    """使用混合字體繪製文字"""
    segments = split_text_by_font(str(text))
    
    current_x = x
    
    for segment_text, font_type in segments:
        if font_type == "emoji":
            # Emoji 用 Symbola，比較小，需要向下微調對齊 CJK
            font = get_font_emoji(font_size)
            # CJK bbox 通常從 y=5 開始，emoji 從 y=3，差約 2px
            emoji_y = y + 2
        else:
            # 中文用 Noto Sans CJK
            font = get_font_cjk(font_size)
            emoji_y = y
        
        draw.text((current_x, emoji_y), segment_text, font=font, fill=fill_color)
        
        # 更新 x 位置
        try:
            bbox = font.getbbox(segment_text)
            width = bbox[2] - bbox[0]
        except:
            width = font_size * len(segment_text) * 0.6
        current_x += width
    
    return current_x

def render_pil(data: dict, theme: dict, custom_params: dict = None) -> Image.Image:
    """使用 PIL 渲染表格，主題來自 themes/pil/<name>/template.json 的 params"""
    params = theme.get("params") or {}
    base_style = PILStyle(
        params.get("bg_color", "#1a1a2e"),
        params.get("text_color", "#ffffff"),
        params.get("header_bg", "#0f3460"),
        params.get("header_text", "#e94560"),
        params.get("alt_row_color", "#16213e"),
        params.get("border_color", "#4a5568"),
    )
    
    # 應用 custom_params 覆蓋（API 傳入）
    if custom_params:
        style = PILStyle(
            bg_color=custom_params.get('bg_color', base_style.bg_color),
            text_color=custom_params.get('text_color', base_style.text_color),
            header_bg=custom_params.get('header_bg', base_style.header_bg),
            header_text=custom_params.get('header_text', base_style.header_text),
            alt_row_color=custom_params.get('alt_row_color', base_style.alt_row_color),
            border_color=custom_params.get('border_color', base_style.border_color),
        )
    else:
        style = base_style
    merged_params = {**(params or {}), **(custom_params or {})}
    
    headers = data.get("headers", [])
    rows = data.get("rows", [])
    
    # 依內容計算尺寸
    col_count = len(headers) if headers else 1
    row_count = len(rows)
    header_font_size = merged_params.get('header_font_size', 18)
    cell_font_size = merged_params.get('font_size', 16)
    cell_padding = 20
    min_col_width, max_col_width = 60, 400
    padding = 20
    header_height = 50
    
    # 每欄最大文字寬度
    col_widths = []
    for i in range(col_count):
        w = measure_text_width(headers[i] if i < len(headers) else "", header_font_size)
        for row in rows:
            if i < len(row):
                w = max(w, measure_text_width(str(row[i]), cell_font_size))
        w = min(max_col_width, max(min_col_width, w + cell_padding))
        col_widths.append(w)
    
    cell_height = max(int(cell_font_size * 1.5), 30)

    # 版面高度需把 title/footer 區塊一併計入，否則 title 存在時 footer 會被裁切
    title_block_height = 50 if data.get("title") else 0
    footer_block_height = 30
    bottom_extra = 10

    width = padding * 2 + sum(col_widths)
    height = padding * 2 + title_block_height + header_height + row_count * cell_height + footer_block_height + bottom_extra
    
    # 檢查是否需要 RGBA 模式
    def has_alpha(c):
        return c.startswith('rgba(') or (c.startswith('#') and len(c) == 9)
    
    use_rgba = any(has_alpha(c) for c in [
        style.bg_color, style.header_bg, style.alt_row_color, style.border_color
    ])
    
    # 建立圖片
    img_mode = 'RGBA' if use_rgba else 'RGB'
    img = Image.new(img_mode, (width, height), parse_color(style.bg_color))
    draw = ImageDraw.Draw(img)
    
    # 載入字體
    try:
        font = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 16)
        header_font = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 18)
    except:
        font = ImageFont.load_default()
        header_font = font
    
    y = padding
    
    # 標題
    if data.get("title"):
        draw.rectangle([padding, y, width-padding, y+40], fill=parse_color(style.header_bg))
        draw_text_with_mixed_fonts(draw, data["title"], padding+10, y+10, 22, parse_color(style.header_text))
        y += 50
    
    # 表頭
    draw.rectangle([padding, y, width-padding, y+header_height], fill=parse_color(style.header_bg))
    x_offset = padding
    for i, h in enumerate(headers):
        draw_text_with_mixed_fonts(draw, h, x_offset + 10, y+15, header_font_size, parse_color(style.header_text))
        x_offset += col_widths[i] if i < len(col_widths) else 60
    y += header_height
    
    # 資料列
    for idx, row in enumerate(rows):
        row_bg = style.alt_row_color if idx % 2 == 0 else style.bg_color
        draw.rectangle([padding, y, width-padding, y+cell_height], fill=parse_color(row_bg))
        draw.line([padding, y+cell_height, width-padding, y+cell_height], fill=parse_color(style.border_color))
        
        x_offset = padding
        for i, cell in enumerate(row):
            draw_text_with_mixed_fonts(draw, str(cell), x_offset + 10, y+10, cell_font_size, parse_color(style.text_color))
            x_offset += col_widths[i] if i < len(col_widths) else 60
        y += cell_height
    
    # 底部（使用混合字體以支援 footer 中的 emoji）
    draw.rectangle([padding, y, width-padding, y+30], fill=parse_color(style.header_bg))
    footer_text = data.get("footer") or "Generated by ZenTable (PIL fallback)"
    draw_text_with_mixed_fonts(draw, footer_text, padding+10, y+8, 12, parse_color(style.text_color))
    
    return img


# =============================================================================
# THEME LOADER
# =============================================================================

# 主題目錄：固定使用本專案 `themes/`（避免依賴外部 /opt skill 目錄）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEMES_DIR = os.path.join(_PROJECT_ROOT, 'themes')

CACHE_BASE = os.environ.get('ZENTABLE_CACHE_DIR', '/tmp/zentable_themes')

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def _read_template_from_zip(zip_path):
    """從 zip 內讀取 template.json（支援根目錄或 mode/theme_name/template.json）"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            candidates = ['template.json'] + [n for n in z.namelist() if n.endswith('template.json')]
            for c in candidates:
                try:
                    content = z.read(c)
                    return json.loads(content.decode('utf-8'))
                except (KeyError, json.JSONDecodeError):
                    continue
    except (zipfile.BadZipFile, OSError):
        pass
    return None

def load_theme_from_themes_dir(theme_name, mode='css'):
    """從 themes 目錄載入 template.json（支援 theme_name.zip 與 theme_name/template.json）"""
    for base in [THEMES_DIR]:
        if not base:
            continue
        zip_path = os.path.join(base, mode, theme_name + '.zip')
        if os.path.isfile(zip_path):
            try:
                data = _read_template_from_zip(zip_path)
                if data:
                    return data
            except Exception as e:
                print(f"⚠️  載入主題失敗 {zip_path}: {e}")
        folder_path = os.path.join(base, mode, theme_name, 'template.json')
        if os.path.exists(folder_path):
            try:
                return load_json(folder_path)
            except Exception as e:
                print(f"⚠️  載入主題失敗 {folder_path}: {e}")
    return None

def list_themes_in_dir(mode='css'):
    """列出 themes/ 目錄中的所有主題（含 .zip 與資料夾）"""
    seen = set()
    for base in [THEMES_DIR]:
        if not base or not os.path.isdir(base):
            continue
        mode_dir = os.path.join(base, mode)
        if not os.path.isdir(mode_dir):
            continue
        for name in os.listdir(mode_dir):
            if name in seen:
                continue
            full = os.path.join(mode_dir, name)
            if name.endswith('.zip') and os.path.isfile(full):
                seen.add(name[:-4])
            elif os.path.isdir(full) and os.path.exists(os.path.join(full, 'template.json')):
                seen.add(name)
    return sorted(seen)

def get_theme_source_path(theme_name, mode='css'):
    """取得 theme 來源路徑。回傳 (path, is_zip) 或 None。支援 alias 與 fallback。"""
    def find_path(name):
        for base in [THEMES_DIR]:
            if not base:
                continue
            zip_path = os.path.join(base, mode, name + '.zip')
            if os.path.isfile(zip_path):
                return (os.path.abspath(zip_path), True)
            folder_path = os.path.join(base, mode, name, 'template.json')
            if os.path.exists(folder_path):
                return (os.path.abspath(os.path.join(base, mode, name)), False)
        return None
    r = find_path(theme_name)
    if r:
        return r
    alias = {"dark": "default_dark", "light": "default_light"}.get(theme_name)
    if alias:
        r = find_path(alias)
        if r:
            return r
    for fallback in ["default_dark", "default_light"]:
        r = find_path(fallback)
        if r:
            return r
    return None

def _rmtree_safe(d):
    """遞迴刪除目錄"""
    if not os.path.isdir(d):
        return
    for name in os.listdir(d):
        p = os.path.join(d, name)
        if os.path.isdir(p):
            _rmtree_safe(p)
        else:
            try:
                os.remove(p)
            except OSError:
                pass
    try:
        os.rmdir(d)
    except OSError:
        pass

def ensure_theme_cache(theme_name, mode='css'):
    """確保 theme 已解壓至快取目錄，回傳渲染用目錄（含 assets）。資料夾來源直接回傳路徑。"""
    src = get_theme_source_path(theme_name, mode)
    if not src:
        raise ValueError(f"主題 '{theme_name}' 不存在於 themes/{mode}/")
    path, is_zip = src
    if not is_zip:
        return path
    cache_dir = os.path.join(CACHE_BASE, f"{mode}_{theme_name}")
    meta_path = os.path.join(cache_dir, '.cache_meta')
    try:
        zip_mtime = os.path.getmtime(path)
    except OSError:
        zip_mtime = 0
    if os.path.isdir(cache_dir) and os.path.isfile(meta_path):
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            if meta.get('source') == path and meta.get('mtime') == zip_mtime:
                return cache_dir
        except (json.JSONDecodeError, OSError):
            pass
    if os.path.isdir(cache_dir):
        _rmtree_safe(cache_dir)
    os.makedirs(cache_dir, exist_ok=True)
    try:
        with zipfile.ZipFile(path, 'r') as z:
            z.extractall(cache_dir)
    except (zipfile.BadZipFile, OSError) as e:
        print(f"⚠️  解壓主題失敗 {path}: {e}", file=sys.stderr)
        raise
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump({"source": path, "mtime": zip_mtime}, f)
    return cache_dir

def get_theme(theme_name, mode='css'):
    """取得主題設定（僅從 themes 目錄載入）"""
    theme = load_theme_from_themes_dir(theme_name, mode)
    if theme:
        print(f"🎨 從 themes 目錄載入: {theme_name} ({mode})")
        return theme
    # 常見別名：前端傳 dark/light 時對應目錄 default_dark/default_light
    alias = {"dark": "default_dark", "light": "default_light"}.get(theme_name)
    if alias:
        theme = load_theme_from_themes_dir(alias, mode)
        if theme:
            print(f"🎨 從 themes 目錄載入: {alias} ({mode}) [別名 {theme_name}]")
            return theme
    if theme_name not in ("default_dark", "default_light"):
        for fallback in ["default_dark", "default_light"]:
            theme = load_theme_from_themes_dir(fallback, mode)
            if theme:
                print(f"⚠️  主題 '{theme_name}' 不存在，使用 {fallback}")
                return theme
    raise ValueError(f"主題 '{theme_name}' 不存在於 themes/{mode}/ 目錄，且無法找到預設主題")

# =============================================================================
# DATA NORMALISATION, SORT, PAGE (SKILL.md: --page, --sort, --asc, --desc)
# =============================================================================

ROWS_PER_PAGE = 15

def normalize_cell(cell):
    """將 cell 統一為 dict，支援舊格式（字串/數字）與 CellSpec。"""
    if isinstance(cell, dict):
        text = cell.get("text", "")
        try:
            colspan = int(cell.get("colspan", 1))
        except (TypeError, ValueError):
            colspan = 1
        try:
            rowspan = int(cell.get("rowspan", 1))
        except (TypeError, ValueError):
            rowspan = 1
        return {
            "text": "" if text is None else str(text),
            "colspan": max(1, colspan),
            "rowspan": max(1, rowspan),
        }
    return {
        "text": "" if cell is None else str(cell),
        "colspan": 1,
        "rowspan": 1,
    }

def cell_text(cell) -> str:
    return normalize_cell(cell).get("text", "")

def build_css_rows_html(rows) -> str:
    """輸出 tbody rows，支援 colspan/rowspan 並跳過被 rowspan 覆蓋的格子。"""
    rows_html = []
    active_rowspans = []
    for idx, row in enumerate(rows if isinstance(rows, list) else []):
        row_class = "tr_even" if idx % 2 == 0 else "tr_odd"
        row_cells = []
        col_cursor = 0
        for raw_cell in (row if isinstance(row, list) else []):
            while col_cursor < len(active_rowspans) and active_rowspans[col_cursor] > 0:
                col_cursor += 1
            cell = normalize_cell(raw_cell)
            attrs = []
            if cell["colspan"] > 1:
                attrs.append(f'colspan="{cell["colspan"]}"')
            if cell["rowspan"] > 1:
                attrs.append(f'rowspan="{cell["rowspan"]}"')
            attr_str = f" {' '.join(attrs)}" if attrs else ""
            row_cells.append(f'<td{attr_str}>{cell["text"]}</td>')
            if cell["rowspan"] > 1:
                for i in range(cell["colspan"]):
                    target_idx = col_cursor + i
                    while target_idx >= len(active_rowspans):
                        active_rowspans.append(0)
                    active_rowspans[target_idx] = max(active_rowspans[target_idx], cell["rowspan"] - 1)
            col_cursor += cell["colspan"]
        for i in range(len(active_rowspans)):
            if active_rowspans[i] > 0:
                active_rowspans[i] -= 1
        rows_html.append(f'<tr class="{row_class}">{"".join(row_cells)}</tr>\n')
    return "".join(rows_html)

def normalise_data(data):
    """將陣列 of 物件或 {headers, rows} 統一為 {headers, rows, title?, footer?}。"""
    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
        headers = list(data[0].keys())
        rows = [[row.get(h, "") for h in headers] for row in data]
        return {"headers": headers, "rows": rows, "title": "", "footer": ""}
    if isinstance(data, dict) and "headers" in data and "rows" in data:
        out = {"headers": list(data["headers"]), "rows": [list(r) for r in data["rows"]], "title": data.get("title", ""), "footer": data.get("footer", "")}
        return out
    if isinstance(data, dict):
        return {"headers": data.get("headers", []), "rows": data.get("rows", []), "title": data.get("title", ""), "footer": data.get("footer", "")}
    return {"headers": [], "rows": [], "title": "", "footer": ""}

def apply_sort_and_page(data, sort_by=None, sort_asc=True, page=1, per_page=ROWS_PER_PAGE):
    """依 sort_by 排序 rows，再取第 page 頁。"""
    headers = data.get("headers", [])
    rows = data.get("rows", [])
    if sort_by and headers and rows:
        try:
            col_idx = headers.index(sort_by)
        except ValueError:
            col_idx = 0
        def sort_key(r):
            v = r[col_idx] if col_idx < len(r) else ""
            return cell_text(v)
        rows = sorted(rows, key=sort_key, reverse=not sort_asc)
    total = len(rows)
    start = (page - 1) * per_page
    end = start + per_page
    rows = rows[start:end]
    return {"headers": headers, "rows": rows, "title": data.get("title", ""), "footer": data.get("footer", "")}

# =============================================================================
# MAIN
# =============================================================================

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        print("\n用法: python3 zeble_render.py <data.json> <output.png> [options]")
        print("\n選項:")
        print('  --force-pil     強制使用 PIL')
        print('  --force-css     強制使用 CSS + Chrome')
        print('  --transparent   產出透空背景 PNG')
        print('  --bg MODE      背景：transparent | theme | #RRGGBB')
        print('  --width N      強制 viewport/輸出寬度')
        print('  --scale N      輸出尺寸倍數')
        print('  --per-page N   每頁列數（預設 %d）' % ROWS_PER_PAGE)
        print('  --fill-width   background|container|scale|no-shrink（搭配 --width）')
        print('  --theme FILE    主題檔案（直接用於測試，不儲存）')
        print('  --theme-name    themes/ 目錄中的主題名稱')
        print('  --page N        第 N 頁（每頁 %d 列）' % ROWS_PER_PAGE)
        print('  --sort <欄位>   依欄位排序')
        print('  --asc           升序（預設）')
        print('  --desc          降序')
        print("\n可用主題 (themes/css/):", ', '.join(list_themes_in_dir('css')) or '(無)')
        print("可用主題 (themes/pil/):", ', '.join(list_themes_in_dir('pil')) or '(無)')
        print("可用主題 (themes/text/):", ', '.join(list_themes_in_dir('text')) or '(無)')
        sys.exit(1)
    
    data_file = sys.argv[1]
    output_file = sys.argv[2]
    
    force_pil = False
    force_css = False
    force_ascii = False
    theme_file = None
    theme_name = "default_dark"
    custom_params = {}
    output_ascii = None  # 如果指定則輸出 ASCII 到檔案
    page = 1
    sort_by = None
    sort_asc = True
    bg_mode = "theme"  # transparent | theme | #RRGGBB
    force_width = None
    scale_factor = 1.0
    per_page = ROWS_PER_PAGE
    fill_width_method = "container"  # background | container | scale | no-shrink
    
    for i in range(3, len(sys.argv)):
        arg = sys.argv[i]
        if arg == "--force-pil":
            force_pil = True
        elif arg == "--force-css":
            force_css = True
        elif arg == "--force-ascii":
            force_ascii = True
        elif arg == "--theme" and i + 1 < len(sys.argv):
            theme_file = sys.argv[i + 1]
        elif arg == "--theme-name" and i + 1 < len(sys.argv):
            theme_name = sys.argv[i + 1]
        elif arg == "--params" and i + 1 < len(sys.argv):
            try:
                custom_params = json.loads(sys.argv[i + 1])
            except:
                print("⚠️  無效的 params JSON")
        elif arg == "--output-ascii" and i + 1 < len(sys.argv):
            output_ascii = sys.argv[i + 1]
        elif arg == "--transparent":
            pass  # 在下方用 transparent_flag 累加
        elif arg == "--page" and i + 1 < len(sys.argv):
            page = max(1, int(sys.argv[i + 1]))
        elif arg == "--sort" and i + 1 < len(sys.argv):
            sort_by = sys.argv[i + 1]
        elif arg == "--asc":
            sort_asc = True
        elif arg == "--desc":
            sort_asc = False
        elif arg == "--bg" and i + 1 < len(sys.argv):
            bg_mode = sys.argv[i + 1].strip().lower()
        elif arg == "--width" and i + 1 < len(sys.argv):
            try:
                force_width = max(1, int(sys.argv[i + 1]))
            except ValueError:
                pass
        elif arg == "--scale" and i + 1 < len(sys.argv):
            try:
                scale_factor = max(0.1, min(5.0, float(sys.argv[i + 1])))
            except ValueError:
                pass
        elif arg == "--per-page" and i + 1 < len(sys.argv):
            try:
                per_page = max(1, int(sys.argv[i + 1]))
            except ValueError:
                pass
        elif arg == "--fill-width" and i + 1 < len(sys.argv):
            m = sys.argv[i + 1].strip().lower()
            if m in ("background", "container", "scale", "no-shrink"):
                fill_width_method = m
    
    # 背景：--transparent 優先，否則 --bg
    transparent_bg = "--transparent" in sys.argv or bg_mode == "transparent"
    if transparent_bg:
        bg_color = None
    elif bg_mode.startswith("#"):
        bg_color = bg_mode
    else:
        bg_color = None
    
    data = load_json(data_file)
    
    # 從數據中提取自定義參數（gentable_pil.php 傳入）
    if isinstance(data, dict):
        data_params = data.pop('_params', {})
        custom_params = {**custom_params, **data_params}
    
    # 統一輸入格式（陣列 of 物件 或 headers+rows），再套用排序與分頁
    data = normalise_data(data)
    data = apply_sort_and_page(data, sort_by=sort_by, sort_asc=sort_asc, page=page, per_page=per_page)
    
    # 決定渲染方式
    chrome_available = check_chrome_available()
    
    if force_ascii:
        mode = "ASCII"
    elif force_pil:
        mode = "PIL (forced)"
    elif force_css:
        mode = "CSS + Chrome (forced)"
        chrome_available = True
    elif chrome_available:
        mode = "CSS + Chrome"
    else:
        mode = "PIL (fallback)"
    
    print(f"🖥️  渲染模式: {mode}")
    
    # 三種模式皆從 themes/<mode>/ 載入主題（或 --theme 指定檔案）
    theme_mode = 'text' if mode == "ASCII" else ('pil' if mode.startswith("PIL") else 'css')
    if theme_file:
        theme = load_json(theme_file)
        print(f"🎨 使用主題檔案: {theme_file}")
    else:
        theme = get_theme(theme_name, theme_mode)
    
    # ASCII 模式
    if mode == "ASCII":
        ascii_output = render_ascii(data, theme)
        if output_ascii:
            with open(output_ascii, 'w', encoding='utf-8') as f:
                f.write(ascii_output)
            print(f"✅ 已保存: {output_ascii}")
        else:
            print(ascii_output)
    
    # 渲染
    elif mode.startswith("CSS") and chrome_available:
        vw, vh, explicit_width = estimate_css_viewport_width_height(data, theme)
        table_width_pct = None
        use_scale_post = False
        scale_no_shrink = False
        if force_width:
            if fill_width_method == "background":
                table_width_pct = None
                vw, vh = force_width, vh
            elif fill_width_method == "container":
                table_width_pct = 96
                vw, vh = force_width, vh
            elif fill_width_method == "scale":
                table_width_pct = None
                use_scale_post = True
                vw, vh = vw, vh  # content-based
            else:  # no-shrink
                table_width_pct = None
                use_scale_post = True
                scale_no_shrink = True
                vw, vh = vw, vh
        html = generate_css_html(data, theme, transparent=transparent_bg, table_width_pct=table_width_pct)
        if scale_factor != 1.0:
            vw = max(1, int(vw * scale_factor))
            vh = max(1, int(vh * scale_factor))
        cache_dir = None
        if not theme_file:
            try:
                cache_dir = ensure_theme_cache(theme_name, theme_mode)
            except ValueError:
                pass
        success = render_css(html, output_file, transparent=transparent_bg, html_dir=cache_dir,
                            viewport_width=vw, viewport_height=vh, bg_color=bg_color,
                            skip_crop=explicit_width)
        if success and use_scale_post and force_width:
            try:
                img = Image.open(output_file)
                w, h = img.size
                if scale_no_shrink and w >= force_width:
                    pass  # 不縮小，保持原樣
                else:
                    new_w = force_width
                    new_h = max(1, int(h * force_width / w))
                    try:
                        resample = Image.Resampling.LANCZOS
                    except AttributeError:
                        resample = Image.LANCZOS
                    img = img.resize((new_w, new_h), resample)
                    img.save(output_file, "PNG")
            except Exception as e:
                print(f"⚠️  後製縮放失敗: {e}", file=sys.stderr)
        if success:
            print(f"✅ 已保存: {output_file}")
        else:
            print("❌ CSS 渲染失敗")
            sys.exit(1)
    
    else:  # PIL
        if transparent_bg:
            custom_params = {**custom_params, 'bg_color': '#00000000'}
        elif bg_color:
            custom_params = {**custom_params, 'bg_color': bg_color}
        img = render_pil(data, theme, custom_params)
        w, h = img.size
        if force_width:
            if fill_width_method == "background":
                # 背景填滿：canvas = force_width，表格置中
                try:
                    bg_color_pil = (0, 0, 0, 0) if transparent_bg else parse_color(bg_color or "#1a1a2e")
                except Exception:
                    bg_color_pil = (26, 26, 46)
                use_rgba = transparent_bg or (isinstance(bg_color_pil, tuple) and len(bg_color_pil) == 4)
                canvas = Image.new("RGBA" if use_rgba else "RGB", (force_width, h), bg_color_pil)
                x = (force_width - w) // 2
                if img.mode != canvas.mode:
                    img = img.convert(canvas.mode)
                canvas.paste(img, (x, 0))
                img = canvas
            elif fill_width_method == "no-shrink" and w >= force_width:
                pass  # 不縮小
            else:
                new_w = force_width
                new_h = max(1, int(h * force_width / w))
                try:
                    resample = Image.Resampling.LANCZOS
                except AttributeError:
                    resample = Image.LANCZOS
                img = img.resize((new_w, new_h), resample)
        elif scale_factor != 1.0:
            new_w = max(1, int(w * scale_factor))
            new_h = max(1, int(h * scale_factor))
            try:
                resample = Image.Resampling.LANCZOS
            except AttributeError:
                resample = Image.LANCZOS
            img = img.resize((new_w, new_h), resample)
        img.save(output_file, quality=95)
        if os.path.exists(output_file):
            print(f"✅ 已保存: {output_file}")
        else:
            print("❌ PIL 渲染失敗")
            sys.exit(1)

if __name__ == "__main__":
    main()
