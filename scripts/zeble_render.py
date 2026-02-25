#!/usr/bin/env python3
"""
ZenTable / Zeble 表格渲染程式（專案內版本）

本檔案為專案內唯一可執行版本，供 `gentable_css.php` / `gentable_pil.php` /
`gentable_ascii.php` 以 CLI 方式呼叫（位於 `scripts/`）。

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
import unicodedata
from typing import Dict, Any, List, Callable, Optional, Tuple
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
        "tm": "+", "bm": "+", "mm": "+",
        "header_l": "+", "header_m": "+", "header_r": "+",
        "row_l": "+", "row_m": "+", "row_r": "+",
        "footer_l": "+", "footer_m": "+", "footer_r": "+",
        "header": "+", "row": "+", "footer": "+"
    },
    "double": {
        "tl": "╔", "tr": "╗", "bl": "╚", "br": "╝",
        "h": "═", "v": "║",
        "tm": "╦", "bm": "╩", "mm": "╬",
        "header_l": "╠", "header_m": "╬", "header_r": "╣",
        "row_l": "╠", "row_m": "╬", "row_r": "╣",
        "footer_l": "╠", "footer_m": "╬", "footer_r": "╣",
        "header": "╠", "row": "╠", "footer": "╠"
    },
    "grid": {
        "tl": "┌", "tr": "┐", "bl": "└", "br": "┘",
        "h": "─", "v": "│",
        "tm": "┬", "bm": "┴", "mm": "┼",
        "header_l": "├", "header_m": "┼", "header_r": "┤",
        "row_l": "├", "row_m": "┼", "row_r": "┤",
        "footer_l": "├", "footer_m": "┼", "footer_r": "┤",
        "header": "├", "row": "├", "footer": "├"
    },
    "markdown": {
        "tl": "|", "tr": "|", "bl": "|", "br": "|",
        "h": "-", "v": "|",
        "tm": "|", "bm": "|", "mm": "|",
        "header_l": "|", "header_m": "|", "header_r": "|",
        "row_l": "|", "row_m": "|", "row_r": "|",
        "footer_l": "|", "footer_m": "|", "footer_r": "|",
        "header": "|", "row": "|", "footer": "|"
    }
}

def _is_zero_width(ch):
    """判斷字元是否為零寬度（不佔顯示空間）。"""
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
    """將字元分類為 ascii/cjk/box/half_space/full_space/emoji 之一。"""
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
    """校準寬度的安全處理：轉成 float，並把負值夾成 0。"""
    try:
        fw = float(w)
    except Exception:
        return None
    return 0.0 if fw < 0 else fw

def char_display_width(ch, calibration=None):
    """取得單一字元的顯示寬度（浮點數）。
    有校準時回傳浮點值（如 1.742），無校準時回傳整數（1 或 2）。
    calibration 格式: {ascii:1, cjk:2, box:1, emoji:2, custom:{char:width}, ...}
    """
    if _is_zero_width(ch):
        # 零寬字元（如 VS16 / ZWJ / combining marks）一律視為 0，
        # 校準資料若出現負值或微幅修正，這裡也不要讓它影響排版。
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
    """計算字串的顯示寬度（有校準時為浮點數）。

    若字串包含換行，採用「最寬那一行」作為 cell 寬度（符合表格排版邏輯）。
    """
    s = str(text)
    if "\n" in s:
        lines = s.splitlines() or [""]
        return max(sum(char_display_width(ch, calibration) for ch in line) for line in lines)
    return sum(char_display_width(ch, calibration) for ch in s)

def _space_width(calibration=None):
    """取得空格字元（U+0020）的校準寬度。

    注意：前端/校準輸出的 `half_space` 通常代表「一般空白」的寬度，
    因此這裡優先使用 `half_space`，其次才是 `ascii`。
    """
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

def calculate_column_widths(headers, rows, padding=2, calibration=None):
    """計算每列最大顯示寬度（浮點數）。padding 以空格字元寬度為單位累加。"""
    sw = _space_width(calibration)
    widths = [display_width(str(h), calibration) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], display_width(str(cell), calibration))
    return [w + padding * 2 * sw for w in widths]

def align_text(text, target_width, align="left", calibration=None):
    """對齊文字：用浮點寬度計算需要多少個空格來補齊。"""
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
    else:  # left
        return text + ' ' * pad_count

def render_ascii(data: dict, theme: dict = None, style: ASCIIStyle = None,
                  calibration: dict = None, debug_details: dict = None) -> str:
    """使用 ASCII 渲染表格，主題來自 themes/text/<name>/template.json 的 params。
    calibration: 字元寬度校準字典 {char: width}，用於精確計算顯示寬度。
    """
    if style is None:
        params = (theme or {}).get("params") or {}
        style = ASCIIStyle(
            border_style=params.get("style", "double"),
            padding=int(params.get("padding", 2)),
            align=params.get("align", "left"),
            header_align=params.get("header_align", "center"),
        )
    
    cal = calibration
    if cal:
        cats = [k for k in ('ascii','cjk','box','emoji') if k in cal]
        custom_n = len(cal.get('custom', {}))
        # 避免污染 ASCII 輸出（stdout），僅寫到 stderr。
        print(
            f"📐 套用校準: 類別寬度={{{', '.join(f'{k}={cal[k]}' for k in cats)}}}"
            + (f", 自訂={custom_n}字元" if custom_n else ""),
            file=sys.stderr
        )
    
    headers = data.get("headers", [])
    rows = data.get("rows", [])
    title = data.get("title", "")
    footer = data.get("footer", "")
    
    # 計算每欄最小內容寬度（浮點值）
    raw_widths = calculate_column_widths(headers, rows, style.padding, cal)
    
    # 獲取框線樣式
    s = ASCII_STYLES.get(style.border_style, ASCII_STYLES["double"])
    
    sw = _space_width(cal)
    if sw <= 0:
        sw = 1.0

    hch = s.get('h', '─')
    vch = s.get('v', '|')
    tm = s.get('tm', s.get('header', '+'))
    bm = s.get('bm', s.get('footer', '+'))
    header_l = s.get('header_l', s.get('header', '+'))
    header_m = s.get('header_m', s.get('header', '+'))
    header_r = s.get('header_r', s.get('header', '+'))

    hw = char_display_width(hch, cal)
    if hw <= 0:
        hw = 1.0

    # 以「校準寬度」決定每欄 h 的重複次數，並反推出內容目標寬度（確保框線與內容共用同一套目標）
    col_h_counts = []
    col_targets = []
    for w in raw_widths:
        full_w = w + 2 * sw  # cell 會包成 " {aligned} "
        n = max(1, round(full_w / hw))
        col_h_counts.append(n)
        col_targets.append(max(0.0, n * hw - 2 * sw))

    # 多行：先拆行，計算每一列高度（最大行數）
    def _cell_lines(v):
        s = "" if v is None else str(v)
        ls = s.splitlines()
        return ls if ls else [""]

    header_lines = [_cell_lines(h) for h in headers] if headers else []
    header_height = 0
    for i in range(min(len(col_targets), len(header_lines))):
        header_height = max(header_height, len(header_lines[i]))
    row_lines = [[_cell_lines(c) for c in (row if isinstance(row, list) else [])] for row in rows]
    row_heights = []
    for r in row_lines:
        h = 1
        for i in range(min(len(col_targets), len(r))):
            h = max(h, len(r[i]))
        row_heights.append(h)

    if isinstance(debug_details, dict):
        debug_details.clear()
        debug_details.update({
            "border_style": style.border_style,
            "padding": style.padding,
            "align": style.align,
            "header_align": style.header_align,
            "h_char": hch,
            "v_char": vch,
            "space_width": sw,
            "h_char_width": hw,
            "raw_widths": raw_widths,
            "col_h_counts": col_h_counts,
            "col_targets": col_targets,
            "ncols": len(col_h_counts),
            "nrows": len(rows),
            "row_heights": row_heights,
            "header_height": header_height,
            "has_headers": bool(headers),
            "has_title": bool(title),
            "has_footer": bool(footer),
            "title": title,
            "footer": footer,
            "headers": list(headers) if headers else [],
            "rows": [[str(c) for c in row] for row in rows] if rows else [],
            "header_lines": header_lines,
            "row_lines": row_lines,
        })

    def _hseg(i: int) -> str:
        return hch * col_h_counts[i]

    def _build_top_line() -> str:
        parts = [_hseg(i) for i in range(len(col_h_counts))]
        return s['tl'] + tm.join(parts) + s['tr']

    def _build_bottom_line() -> str:
        parts = [_hseg(i) for i in range(len(col_h_counts))]
        return s['bl'] + bm.join(parts) + s['br']

    def _build_header_sep() -> str:
        parts = [_hseg(i) for i in range(len(col_h_counts))]
        return header_l + header_m.join(parts) + header_r

    def _align_chars(text: str, width: int, align: str) -> str:
        """用「字元數」對齊（不走校準寬度）。用於 title/footer 這種裝飾列，確保與框線同寬。"""
        text = "" if text is None else str(text)
        if width <= 0:
            return ""
        if len(text) > width:
            return text[:width]
        pad = width - len(text)
        if align == "right":
            return (" " * pad) + text
        if align == "center":
            left = pad // 2
            return (" " * left) + text + (" " * (pad - left))
        return text + (" " * pad)

    lines = []

    # 標題：用 top line 的「實際字元數」對齊（避免 title 行寬度跑掉）
    if title:
        top_probe = _build_top_line()
        inner_chars = max(0, len(top_probe) - 2)
        title_w_chars = max(0, inner_chars - 6)  # 2*h + spaces around title
        title_line = _align_chars(title, title_w_chars, "center")
        lines.append(f"{s['tl']}{hch * 2} {title_line} {hch * 2}{s['tr']}")

    # 頂部框線（含欄位交界）
    lines.append(_build_top_line())

    # 表頭
    if headers:
        header_cells = []
        for i, h in enumerate(headers):
            cell = align_text(h, col_targets[i], style.header_align, cal)
            header_cells.append(f" {cell} ")
        # 表頭也支援多行（若 header 本身含換行）
        header_height = 1
        for i in range(min(len(col_targets), len(header_lines))):
            header_height = max(header_height, len(header_lines[i]))
        for li in range(header_height):
            line_cells = []
            for i in range(min(len(col_targets), len(headers))):
                txt = header_lines[i][li] if i < len(header_lines) and li < len(header_lines[i]) else ""
                line_cells.append(f" {align_text(txt, col_targets[i], style.header_align, cal)} ")
            lines.append(vch + vch.join(line_cells) + vch)
        lines.append(_build_header_sep())

    # 資料列
    for r_idx, row in enumerate(rows):
        row_cells_lines = row_lines[r_idx] if r_idx < len(row_lines) else []
        height = row_heights[r_idx] if r_idx < len(row_heights) else 1
        for li in range(height):
            cells = []
            for i in range(min(len(col_targets), len(row_cells_lines))):
                txt = row_cells_lines[i][li] if li < len(row_cells_lines[i]) else ""
                c = align_text(txt, col_targets[i], style.align, cal)
                cells.append(f" {c} ")
            lines.append(vch + vch.join(cells) + vch)

    # 底部框線（含欄位交界）
    lines.append(_build_bottom_line())

    # 底部文字（同上，用字元數對齊）
    if footer:
        bottom_probe = _build_bottom_line()
        inner_chars = max(0, len(bottom_probe) - 2)
        footer_w_chars = max(0, inner_chars - 6)
        footer_line = _align_chars(footer, footer_w_chars, "center")
        lines.append(f"{s['bl']}{hch * 2} {footer_line} {hch * 2}{s['br']}")

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


def _bottom_edge_has_content(png_path: str, transparent: bool = False, tolerance: int = 20, alpha_threshold: int = 1) -> bool:
    """檢查 PNG 最底邊（y=h-1）是否有內容。

    用於 auto-height：若最底邊仍有非透明/非背景像素，通常代表內容被截斷，需加高 viewport 再渲染。
    """
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

        # 不透明：以四角採樣作背景參考
        corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
        refs = [img.getpixel(c) for c in corners if 0 <= c[0] < w and 0 <= c[1] < h]
        if not refs:
            return False
        bg = tuple(sum(r[i] for r in refs) // len(refs) for i in range(3))

        row = img.crop((0, y, w, y + 1))
        data = list(row.getdata())
        for p in data:
            rgb = p[:3]
            if max(abs(rgb[0] - bg[0]), abs(rgb[1] - bg[1]), abs(rgb[2] - bg[2])) > tolerance:
                return True
        return False
    except Exception:
        return False


def _right_edge_metrics(png_path: str, transparent: bool = False, tolerance: int = 20, alpha_threshold: int = 1,
                        x_inset: int = 0) -> Optional[dict]:
    """Return metrics for a vertical edge line.

    Returns:
      {x, h, nonempty, ratio, best_run}
    """
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


def _right_edge_has_content(png_path: str, transparent: bool = False, tolerance: int = 20, alpha_threshold: int = 1,
                            min_run: int = 12, min_ratio: float = 0.03, x_inset: int = 0) -> bool:
    """檢查 PNG 最右邊（x=w-1）是否有內容（更嚴格）。

    用於 auto-width：避免 1px 抗鋸齒/陰影造成誤判。

    判定規則（任一成立即 True）：
    - 右邊界非空像素數量比例 >= min_ratio
    - 或存在連續 min_run 個非空像素（垂直方向）
    """
    try:
        from PIL import Image
        img = Image.open(png_path)
        w, h = img.size
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        x = max(0, (w - 1) - int(x_inset))
        if x < 0:
            return False

        def is_nonempty_rgba(px, bg_rgb=None):
            if transparent:
                return px[3] >= alpha_threshold
            rgb = px[:3]
            return max(abs(rgb[0] - bg_rgb[0]), abs(rgb[1] - bg_rgb[1]), abs(rgb[2] - bg_rgb[2])) > tolerance

        bg = (0, 0, 0)
        if not transparent:
            corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
            refs = [img.getpixel(c) for c in corners if 0 <= c[0] < w and 0 <= c[1] < h]
            if not refs:
                return False
            bg = tuple(sum(r[i] for r in refs) // len(refs) for i in range(3))

        col = img.crop((x, 0, x + 1, h))
        data = list(col.getdata())

        nonempty = 0
        run = 0
        best_run = 0
        for p in data:
            if is_nonempty_rgba(p, bg):
                nonempty += 1
                run += 1
                if run > best_run:
                    best_run = run
            else:
                run = 0

        if h > 0 and (nonempty / float(h)) >= float(min_ratio):
            return True
        if best_run >= int(min_run):
            return True
        return False
    except Exception:
        return False


def crop_to_content_height(png_path: str, transparent: bool = False, tolerance: int = 20) -> bool:
    """只裁切高度（保留完整寬度），避免 explicit width 時因 skip_crop 而留下超高空白。

    - transparent=True：用 alpha 通道判斷內容。
    - transparent=False：以四角取樣推定背景色，做差異遮罩判斷內容。

    不加 padding（呼應 smallest/auto-height 需求）。
    """
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

        # 只取 bottom
        _, _, _, bottom = bbox
        bottom = max(1, min(h, bottom))
        img = img.crop((0, 0, w, bottom))
        img.save(png_path, "PNG")
        return True
    except Exception as e:
        print(f"⚠️  高度裁切失敗: {e}", file=sys.stderr)
        return False


def _hex_to_chrome_bg(hex_color: str) -> str:
    """將 #RRGGBB 或 #RRGGBBAA 轉為 Chrome --default-background-color 格式（8 位 RRGGBBAA）"""
    h = hex_color.lstrip('#')
    if len(h) == 6:
        return h + 'FF'
    if len(h) == 8:
        return h
    return '000000FF'

LAST_CSS_RENDER_MS = None
LAST_CSS_VIEWPORT = None


def render_css(html: str, output_path: str, transparent: bool = False, html_dir: str = None,
               viewport_width: int = None, viewport_height: int = None, bg_color: str = None,
               skip_crop: bool = False) -> bool:
    """使用 Chrome headless 渲染。

    New: if env var `ZENTABLE_CSS_API_URL` is set, POST to that service instead of
    spawning Chrome locally. This is useful for a warm headless renderer process.

    transparent=True 時以 --default-background-color=00000000 直接產出透明 PNG。
    html_dir: 若指定，HTML 寫入此目錄（使相對路徑資源可正確解析）；否則與 output 同目錄。
    viewport_width, viewport_height: 若提供則設定 Chrome 視窗尺寸，使截圖依內容大小。
    bg_color: 若指定（#RRGGBB），覆蓋背景色；transparent 優先於 bg_color。"""
    global LAST_CSS_RENDER_MS, LAST_CSS_VIEWPORT

    # If a remote CSS render API is configured, use it.
    css_api = os.environ.get("ZENTABLE_CSS_API_URL")
    if css_api:
        try:
            import json as _json
            import urllib.request as _url

            vw = int(viewport_width or 1200)
            vh = int(viewport_height or 800)
            payload = _json.dumps({
                "html": html,
                "viewport_width": vw,
                "viewport_height": vh,
                "transparent": bool(transparent),
                "timeout_ms": 3000,
            }).encode("utf-8")
            req = _url.Request(css_api.rstrip("/") + "/render/css", data=payload, headers={"Content-Type": "application/json"})
            t0 = time.time()
            resp = _url.urlopen(req, timeout=60)
            png = resp.read()
            LAST_CSS_RENDER_MS = int((time.time() - t0) * 1000)
            # Prefer server-provided header if present
            try:
                h = resp.headers
                if h.get('X-Render-Ms'):
                    LAST_CSS_RENDER_MS = int(h.get('X-Render-Ms'))
            except Exception:
                pass
            LAST_CSS_VIEWPORT = (vw, vh)
            with open(output_path, "wb") as f:
                f.write(png)
        except Exception as e:
            print(f"⚠️  CSS API 渲染失敗，改用本機 Chrome: {e}", file=sys.stderr)
        else:
            if not skip_crop:
                crop_to_content_bounds(output_path, padding=2, transparent=transparent)
            return True

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
    # 所有模式都使用透明背景參數，讓 viewport/body 透明
    parts.append(f"--default-background-color={TRANSPARENT_BG_HEX}")
    parts.append(f"file://{html_file}")
    cmd = " ".join(parts)

    t0 = time.time()
    result = os.system(cmd)
    LAST_CSS_RENDER_MS = int((time.time() - t0) * 1000)
    if viewport_width and viewport_height:
        try:
            LAST_CSS_VIEWPORT = (int(viewport_width), int(viewport_height))
        except Exception:
            pass
    
    if os.path.exists(html_file):
        os.remove(html_file)
    
    if result != 0 or not os.path.exists(output_path):
        return False
    # 依內容邊界裁切，移除多餘空白；若 skip_crop（使用者明確指定寬度）則不裁切
    if not skip_crop:
        crop_to_content_bounds(output_path, padding=2, transparent=transparent)
    return True

def measure_dom_scroll_width(html: str, html_dir: str, viewport_width: int, viewport_height: int) -> Optional[int]:
    """Measure content scrollWidth from DOM using headless Chrome + --dump-dom.

    Returns the needed width (scrollWidth) if measurable, else None.
    Only works for local Chrome spawning (not remote CSS API).
    """


def measure_dom_overflow(html: str, html_dir: str, viewport_width: int, viewport_height: int) -> Optional[dict]:
    """Measure DOM overflow for the table element.

    Returns dict: {scrollWidth, clientWidth, rectWidth}
    """
    try:
        ts = str(int(time.time() * 1000))
        html_file = os.path.join(html_dir, f"overflow_{ts}.html")

        inject = """
<script>
(function(){
  function pick(){ return document.querySelector('table') || document.querySelector('.table') || null; }
  function measure(){
    var el = pick();
    var sw = 0, cw = 0, rw = 0;
    if(el){
      try { sw = el.scrollWidth||0; cw = el.clientWidth||0; rw = el.getBoundingClientRect().width||0; } catch(e) {}
    }
    var bsw = 0, bcw = 0, brw = 0;
    try {
      var b = document.body;
      if(b){ bsw = b.scrollWidth||0; bcw = b.clientWidth||0; brw = b.getBoundingClientRect().width||0; }
    } catch(e) {}
    document.title = 'ZENTABLE_OVERFLOW=' + Math.ceil(sw) + ',' + Math.ceil(cw) + ',' + Math.ceil(rw)
      + '|BODY=' + Math.ceil(bsw) + ',' + Math.ceil(bcw) + ',' + Math.ceil(brw);
  }
  window.addEventListener('load', function(){ setTimeout(measure, 50); });
  setTimeout(measure, 200);
})();
</script>
"""

        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html + inject)

        parts = [
            "xvfb-run", "-a", "google-chrome", "--headless",
            "--disable-gpu",
            "--virtual-time-budget=1000",
            f"--window-size={int(viewport_width)},{int(viewport_height)}",
            f"--default-background-color={TRANSPARENT_BG_HEX}",
            "--dump-dom",
            f"file://{html_file}",
        ]
        import subprocess
        p = subprocess.run(parts, capture_output=True, text=True, timeout=30)
        out = (p.stdout or "")
        m = re.search(r"ZENTABLE_OVERFLOW=(\d+),(\d+),(\d+)\|BODY=(\d+),(\d+),(\d+)", out)
        if m:
            return {
                "table": {"scrollWidth": int(m.group(1)), "clientWidth": int(m.group(2)), "rectWidth": int(m.group(3))},
                "body": {"scrollWidth": int(m.group(4)), "clientWidth": int(m.group(5)), "rectWidth": int(m.group(6))},
            }
        # backward compat
        m2 = re.search(r"ZENTABLE_OVERFLOW=(\d+),(\d+),(\d+)", out)
        if m2:
            return {"table": {"scrollWidth": int(m2.group(1)), "clientWidth": int(m2.group(2)), "rectWidth": int(m2.group(3))}}
        return None
    except Exception:
        return None
    finally:
        try:
            if 'html_file' in locals() and os.path.exists(html_file):
                os.remove(html_file)
        except Exception:
            pass

    try:
        ts = str(int(time.time() * 1000))
        html_file = os.path.join(html_dir, f"measure_{ts}.html")

        inject = """
<script>
(function(){
  function pick(){
    return document.querySelector('table') || document.querySelector('.table') || null;
  }
  function measure(){
    var el = pick();
    var w = 0;
    if(!el){ document.title = 'ZENTABLE_SCROLLWIDTH=0'; return; }
    try { w = Math.max(el.scrollWidth||0, el.getBoundingClientRect().width||0); } catch(e) {}
    document.title = 'ZENTABLE_SCROLLWIDTH=' + Math.ceil(w);
  }
  window.addEventListener('load', function(){ setTimeout(measure, 50); });
  setTimeout(measure, 200);
})();
</script>
"""

        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html + inject)

        parts = [
            "xvfb-run", "-a", "google-chrome", "--headless",
            "--disable-gpu",
            "--virtual-time-budget=1000",
            f"--window-size={int(viewport_width)},{int(viewport_height)}",
            f"--default-background-color={TRANSPARENT_BG_HEX}",
            "--dump-dom",
            f"file://{html_file}",
        ]
        import subprocess
        p = subprocess.run(parts, capture_output=True, text=True, timeout=30)
        out = (p.stdout or "")
        m = re.search(r"ZENTABLE_SCROLLWIDTH=(\d+)", out)
        if m:
            return int(m.group(1))
        return None
    except Exception:
        return None
    finally:
        try:
            if 'html_file' in locals() and os.path.exists(html_file):
                os.remove(html_file)
        except Exception:
            pass



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

# =============================================================================
# CSS TEXT SCALE (CSS mode only)
# =============================================================================

def _resolve_text_scale(
    width: Optional[int],
    text_scale: Optional[float],
    text_scale_mode: str = "auto",
    text_scale_max: float = 2.5
) -> float:
    """
    決定最終文字縮放倍率（僅供 CSS 模式使用）。
    - 若提供 text_scale（數值），視為手動指定（允許到 5.0）
    - 否則依 width 自動推算（寬圖自動放大），並受 text_scale_max 上限控制（最大 2.5）
    """
    def clamp(v: float, lo: float, hi: float) -> float:
        return max(lo, min(v, hi))

    # 手動覆寫
    if text_scale is not None:
        try:
            v = float(text_scale)
        except Exception:
            return 1.0
        if v <= 0:
            return 1.0
        return clamp(v, 0.5, 5.0)

    # 自動：只在明顯寬圖時放大
    if not width:
        return 1.0

    # 自動模式基準寬度（越小 → 放大越多），與 skills/zentable/table_renderer.py 對齊
    mode = (text_scale_mode or "auto").strip().lower()
    mode_to_base = {
        "smallest": 500.0,
        "small": 460.0,
        "auto": 400.0,
        "large": 330.0,
        "largest": 280.0,
    }
    base_w = mode_to_base.get(mode, 400.0)

    math = __import__("math")
    v = math.sqrt(float(width) / base_w)

    try:
        max_v = float(text_scale_max)
    except Exception:
        max_v = 2.5
    if max_v < 1.0:
        max_v = 1.0
    if max_v > 2.5:
        max_v = 2.5
    return clamp(v, 1.0, max_v)


def _scale_css_styles_px(theme: dict, scale: float) -> dict:
    """
    將 CSS 主題 styles 內所有 px 數值按倍率縮放（四捨五入到整數 px）。
    回傳新 theme，避免污染 cache 中的原主題。
    """
    try:
        s = float(scale)
    except Exception:
        return theme
    if abs(s - 1.0) < 1e-6:
        return theme

    styles = (theme or {}).get("styles", {})
    if not isinstance(styles, dict) or not styles:
        return theme

    def scale_px_values(style_str: str) -> str:
        if not isinstance(style_str, str) or "px" not in style_str:
            return style_str

        def repl(m):
            num = float(m.group(1))
            return f"{int(round(num * s))}px"

        return re.sub(r"(-?[0-9]*\.?[0-9]+)px", repl, style_str)

    scaled_styles = {k: scale_px_values(v) for k, v in styles.items()}
    new_theme = dict(theme or {})
    new_theme["styles"] = scaled_styles
    return new_theme


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

def _strip_alpha_from_css(css_text: str) -> str:
    """Best-effort: strip alpha from rgba()/hsla()/8-digit hex colors.

    Used for non-tt mode to make backgrounds fully opaque.
    """
    if not isinstance(css_text, str) or not css_text:
        return css_text

    # rgba(r,g,b,a) -> rgb(r,g,b)
    css_text = re.sub(r'rgba\(\s*([0-9]+)\s*,\s*([0-9]+)\s*,\s*([0-9]+)\s*,\s*([0-9.]+)\s*\)', r'rgb(\1,\2,\3)', css_text, flags=re.I)
    # hsla(h,s,l,a) -> hsl(h,s,l)
    css_text = re.sub(r'hsla\(([^,]+),([^,]+),([^,]+),([^\)]+)\)', r'hsl(\1,\2,\3)', css_text, flags=re.I)

    # #RRGGBBAA -> #RRGGBB
    css_text = re.sub(r'#([0-9a-fA-F]{6})([0-9a-fA-F]{2})\b', r'#\1', css_text)
    return css_text


def generate_css_html(data: dict, theme: dict, transparent: bool = False, table_width_pct: int = None, tt: bool = False) -> str:
    """生成 CSS 版本的 HTML。table_width_pct: 若指定（如 96），表格填滿該比例的 viewport 寬度。

    tt=True:
      - container/table background forced transparent (but cell backgrounds keep their original alpha)
    tt=False:
      - backgrounds are forced opaque by stripping alpha from theme CSS.
    """
    engine = TemplateEngine()
    
    headers = data.get("headers", [])
    rows = data.get("rows", [])
    title = data.get("title", "")
    footer = data.get("footer", "Generated by ZenTable")
    
    # 斑馬紋 rows（支援 colspan/rowspan）
    rows_html = build_css_rows_html(rows)
    
    headers_html = ''.join(f'<th>{h}</th>' for h in headers)
    
    styles = theme.get("styles", {})

    # Non-tt: force opaque backgrounds by stripping alpha from all style blocks.
    if not tt and isinstance(styles, dict):
        styles = {k: _strip_alpha_from_css(v) if isinstance(v, str) else v for k, v in styles.items()}

    # tt: container/table background transparent (keep cell bg alpha as-is)
    tt_css = ""
    if tt:
        tt_css += "\n.container, table { background: transparent !important; background-image: none !important; }"

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
        # 進階選擇器：包含 pseudo-class/複合選擇器時直接視為原生 selector
        # 例如：th:first-child、td:last-child、tbody tr:last-child td、th:nth-child(2)
        if ':' in key or ' ' in key or '>' in key or '+' in key or '~' in key or '[' in key:
            return key
        if key.startswith('col_') and key[4:].isdigit():
            n = key[4:]
            return f'th:nth-child({n}), td:nth-child({n})'
        return '.' + key
    css = '\n'.join(f'{css_selector(k)} {{{v}}}' for k, v in styles.items())
    css += "\ntd { white-space: pre-wrap !important; overflow-wrap: anywhere !important; word-break: break-word !important; }"
    css += tt_css
    # 所有模式都讓 viewport/body 透明，使用 --default-background-color 控制實際輸出
    css += "\nhtml, body { background: transparent !important; background-image: none !important; }"
    if table_width_pct:
        # 指定 viewport 寬度時，container 為 95% 寬度並置中
        css += f"\n.container {{ width: 95% !important; max-width: {table_width_pct}% !important; margin: 0 auto; box-sizing: border-box; }}"
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


def _inject_wrap_gap_css(html: str, gap_px: int) -> str:
    """Inject wrap-gap CSS.

    Purpose: when rendering with a fixed width (e.g. mobile w450), force the layout engine
    to wrap earlier so text doesn't spill past the right edge.

    This is an explicit user-controlled behavior via --wrap-gap.

    Implementation:
      - viewport width = (forced_width + gap)
      - effective layout width = calc(100% - gap)
      - keep a right margin gap for safety
      - force table to 100% so columns are constrained by the layout width
    """
    try:
        gap_px = max(0, int(gap_px))
    except Exception:
        gap_px = 0
    if gap_px <= 0:
        return html
    css = (
        f"\nhtml, body {{ width: calc(100% - {gap_px}px) !important; margin: 0 {gap_px}px 0 0 !important; box-sizing: border-box; }}"
        f"\ntable {{ width: 100% !important; }}\n"
        f"\nhtml {{ -webkit-text-size-adjust: 100%; text-size-adjust: 100%; }}\n"
    )
    inject = f"\n<style id=\"zentable-wrap-gap\">{css}</style>\n"
    if "</head>" in html:
        return html.replace("</head>", inject + "</head>")
    return html + inject


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
# Emoji 字體：優先彩色 Noto Color Emoji，備援 Symbola / DejaVu / Liberation（多路徑以支援不同發行版）
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

# 載入字體快取
_font_cache = {}
_emoji_font_available = None  # 快取可用的 emoji 字體

def get_font_cjk(size=16):
    """取得中文字體（多路徑嘗試，避免單一路徑不存在導致文字不顯示）"""
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
    """偵測可用的 emoji 字體，回傳 (字體路徑, 是否為彩色)。先試固定路徑，再掃描系統字型目錄。"""
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

    # 掃描系統字型目錄（多種 pattern 以適應不同發行版）
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

    # 最後手段：遞迴搜尋常見檔名（適用於非標準目錄結構）
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
    """取得 Emoji 字體（自動選擇支援 emoji 顯示的字型，避免用 default 導致方塊）"""
    key = f"emoji_{size}"
    if key not in _font_cache:
        font_path, _ = _detect_emoji_font()
        if font_path:
            try:
                _font_cache[key] = ImageFont.truetype(font_path, size)
            except Exception:
                _font_cache[key] = ImageFont.load_default()
        else:
            # 無快取結果時再試一次逐路徑載入（避免漏掉執行時才存在的路徑）
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
    """檢查目前使用的 emoji 字體是否為彩色"""
    _, is_color = _detect_emoji_font()
    return is_color

def get_font(size=16):
    """取得預設字體"""
    return get_font_cjk(size)

def render_ascii_blueprint_pil(blueprint: dict, out_png_path: str, unit_px: int = 10):
    """將 ASCII 版面格式化（blueprint）用 PIL 可視化。

    輸入 blueprint 應為 render_ascii(..., calibration=None, debug_details=...) 的輸出。
    座標系以「字元格」為單位（半形=1、全形=2 的預設模型），每單位用 unit_px 轉換成像素。
    """
    warning = None
    try:
        unit_px = int(unit_px)
    except Exception:
        unit_px = 10
    unit_px = max(5, min(30, unit_px))

    if not isinstance(blueprint, dict) or not blueprint.get("col_h_counts"):
        return None, "blueprint 無效或缺少欄位資訊"

    col_h = blueprint.get("col_h_counts") or []
    ncols = int(blueprint.get("ncols") or len(col_h) or 0)
    col_h = col_h[:ncols]
    row_heights = blueprint.get("row_heights") or []
    header_height = int(blueprint.get("header_height") or 0)
    has_headers = bool(blueprint.get("has_headers"))
    has_title = bool(blueprint.get("has_title"))
    has_footer = bool(blueprint.get("has_footer"))
    # 實際表格內容（用於在藍圖上渲染文字以便核對）
    title_text = str(blueprint.get("title") or "")
    footer_text = str(blueprint.get("footer") or "")
    headers_list = blueprint.get("headers") or []
    rows_list = blueprint.get("rows") or []
    header_lines_list = blueprint.get("header_lines") or []
    row_lines_list = blueprint.get("row_lines") or []

    def _build_fonts(px: int):
        """依 unit_px 建立字體與估計字高。"""
        try:
            base = max(12, min(28, int(px * 0.8) + 8))
            f = ImageFont.truetype(FONT_CJK, base)
            f_sm = ImageFont.truetype(FONT_CJK, max(11, base - 4))
        except Exception:
            f = ImageFont.load_default()
            f_sm = ImageFont.load_default()
            base = 14
        try:
            d = ImageDraw.Draw(Image.new("RGB", (10, 10), (255, 255, 255)))
            bb = d.textbbox((0, 0), "Ag字", font=f_sm)
            th = max(0, bb[3] - bb[1])
        except Exception:
            try:
                th = f_sm.getbbox("Ag字")[3]
            except Exception:
                th = 12
        return f, f_sm, th, base

    # 以字高推最小 unit_px（避免文字擠在一起）。若提升 unit_px，需重建字體。
    font, font_sm, text_h, base_font_size = _build_fonts(unit_px)
    min_unit_px = max(10, int(text_h + 8))
    if unit_px < min_unit_px:
        warning = f"unit_px 太小，為避免標註重疊，已自動提升 {unit_px}→{min_unit_px}"
        unit_px = min_unit_px
        font, font_sm, text_h, base_font_size = _build_fonts(unit_px)

    # 字元格座標（含 border/intersection 字元）
    width_chars = 2 + sum(int(x) for x in col_h) + max(0, ncols - 1)

    y = 0
    title_row = None
    footer_row = None
    if has_title:
        title_row = y
        y += 1
    top_border = y
    y += 1
    header_start = None
    header_sep = None
    if has_headers:
        header_start = y
        y += max(1, header_height)
        header_sep = y
        y += 1
    data_start = y
    data_row_starts = []
    for h in row_heights:
        data_row_starts.append(y)
        y += max(1, int(h))
    bottom_border = y
    y += 1
    if has_footer:
        footer_row = y
        y += 1
    height_chars = y

    # 右側 legend 區，避免覆蓋表格。行高加高一倍再 +5px，支援單 cell 多行文字。
    margin = 64
    legend_gap = 24
    legend_w = 360
    unit_px_vertical = unit_px * 2 + 5
    table_w_px = width_chars * unit_px
    table_h_px = height_chars * unit_px_vertical

    # 換行工具：讓底部面板與 legend 文字不會超出框線
    def _text_width(d, fnt, txt: str) -> int:
        txt = "" if txt is None else str(txt)
        try:
            return int(d.textlength(txt, font=fnt))
        except Exception:
            try:
                return int(fnt.getlength(txt))
            except Exception:
                try:
                    bb = d.textbbox((0, 0), txt, font=fnt)
                    return int(bb[2] - bb[0])
                except Exception:
                    return len(txt) * 8

    def _wrap_text(d, fnt, txt: str, max_w: int, subsequent_prefix: str = ""):
        txt = "" if txt is None else str(txt)
        if max_w <= 0:
            return [txt]
        if _text_width(d, fnt, txt) <= max_w:
            return [txt]
        # 先用空白斷詞；無空白則逐字切
        if " " in txt:
            words = txt.split(" ")
            out = []
            cur = ""
            for w0 in words:
                cand = (cur + (" " if cur else "") + w0).strip()
                if cur and _text_width(d, fnt, cand) > max_w:
                    out.append(cur)
                    cur = subsequent_prefix + w0
                else:
                    cur = cand
            if cur:
                out.append(cur)
            return out if out else [txt]
        # 逐字切（CJK 友善）
        out = []
        cur = ""
        for ch in txt:
            cand = cur + ch
            if cur and _text_width(d, fnt, cand) > max_w:
                out.append(cur)
                cur = subsequent_prefix + ch
            else:
                cur = cand
        if cur:
            out.append(cur)
        return out if out else [txt]

    # 下方文字面板（區塊標註、摘要）— 不覆蓋 table
    summary = []
    if title_row is not None:
        summary.append(f"title row: y={title_row}")
    summary.append(f"top border: y={top_border}")
    if has_headers and header_start is not None and header_sep is not None:
        summary.append(f"header: y={header_start}..{header_sep-1}")
        summary.append(f"header sep: y={header_sep}")
    summary.append(f"data: y={data_start}..{bottom_border-1}")
    summary.append(f"bottom border: y={bottom_border}")
    if footer_row is not None:
        summary.append(f"footer row: y={footer_row}")

    # 先用 dummy draw 進行換行與高度估算（避免字體超出框線）
    _dummy = ImageDraw.Draw(Image.new("RGB", (10, 10), (255, 255, 255)))
    bottom_panel_w = (margin * 2 + table_w_px + legend_gap + legend_w) - margin * 2  # 實際會畫在 table_x0..legend_x1
    bottom_inner_w = max(120, int(bottom_panel_w - 24))
    panel_font = font  # 底部面板字體放大
    panel_line_h = max(18, int(text_h + 10))

    bottom_lines = []
    bottom_lines.extend(_wrap_text(_dummy, panel_font, "Regions (y) — blueprint (no calibration):", bottom_inner_w))
    for line in summary:
        wrapped = _wrap_text(_dummy, panel_font, "- " + line, bottom_inner_w, subsequent_prefix="  ")
        bottom_lines.extend(wrapped)

    bottom_panel_h = max(140, 20 + len(bottom_lines) * panel_line_h + 20)
    # 表格下方預留空間給欄位交界座標字（0, 17, 28...），避免 Regions 框蓋住
    gap_below_table = 40
    w = margin * 2 + table_w_px + legend_gap + legend_w
    h = margin * 2 + table_h_px + gap_below_table + bottom_panel_h
    img = Image.new("RGB", (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    ox, oy = margin, margin
    table_x0, table_y0 = ox, oy
    table_x1, table_y1 = ox + table_w_px, oy + table_h_px
    legend_x0 = table_x1 + legend_gap
    legend_x1 = legend_x0 + legend_w
    bottom_y0 = table_y1 + gap_below_table
    bottom_y1 = bottom_y0 + bottom_panel_h

    # 主要區域外框（四邊同樣粗）
    draw.rectangle([table_x0, table_y0, table_x1, table_y1], outline=(0, 0, 0), width=3)

    # x border positions（字元索引）
    x_borders = [0]
    pos = 0
    for i in range(ncols):
        pos += 1 + int(col_h[i])
        x_borders.append(pos)

    # 畫垂直邊界線（含最左/最右與欄分隔），並標出每個 column 交界的 x 座標
    for i, xb in enumerate(x_borders):
        x = ox + xb * unit_px
        draw.line([x, table_y0, x, table_y1], fill=(0, 0, 0), width=2)
        txt = str(xb)
        try:
            bbox = draw.textbbox((0, 0), txt, font=font_sm)
            w = bbox[2] - bbox[0]
        except Exception:
            w = len(txt) * 6
        draw.text((x - w // 2, table_y1 + 4), txt, fill=(0, 70, 100), font=font_sm)

    # 畫水平關鍵線
    def hline(y_idx, color=(0, 0, 0), width=2):
        yy = oy + y_idx * unit_px_vertical
        draw.line([table_x0, yy, table_x1, yy], fill=color, width=width)

    def _shade_band(y0_idx, y1_idx, fill_rgb):
        """用淡色標出區塊範圍。"""
        y0p = oy + y0_idx * unit_px_vertical
        y1p = oy + y1_idx * unit_px_vertical
        draw.rectangle([table_x0, y0p, table_x1, y1p], fill=fill_rgb)

    # 標題/底註行（只畫線框提示）
    if title_row is not None:
        _shade_band(title_row, title_row + 1, (235, 245, 255))
        hline(title_row, (60, 60, 60), 2)
        hline(title_row + 1, (60, 60, 60), 2)
    if footer_row is not None:
        _shade_band(footer_row, footer_row + 1, (235, 245, 255))
        hline(footer_row, (60, 60, 60), 2)
        hline(footer_row + 1, (60, 60, 60), 2)

    hline(top_border, (0, 0, 0), 3)
    if has_headers and header_sep is not None:
        hline(header_sep, (0, 0, 0), 3)
    hline(bottom_border, (0, 0, 0), 3)

    if has_headers and header_start is not None and header_sep is not None:
        _shade_band(header_start, header_sep, (240, 255, 240))

    # 畫資料列邊界（淡色，作為 cell 高度參考）
    for ys in data_row_starts:
        hline(ys, (190, 190, 190), 1)
    hline(data_start, (120, 120, 120), 2)

    # 座標刻度：表格大時降低密度
    tick_step = 10 if max(width_chars, height_chars) >= 80 else 5
    for xi in range(0, width_chars + 1, tick_step):
        x = ox + xi * unit_px
        draw.line([x, oy - 6, x, oy], fill=(0, 0, 0), width=1)
        draw.text((x + 2, oy - 22), str(xi), fill=(0, 0, 0), font=font_sm)
    for yi in range(0, height_chars + 1, tick_step):
        yyy = oy + yi * unit_px_vertical
        draw.line([ox - 6, yyy, ox, yyy], fill=(0, 0, 0), width=1)
        draw.text((ox - 36, yyy + 2), str(yi), fill=(0, 0, 0), font=font_sm)

    # 表格右端：每一行的 y 座標（支援單 cell 多行時對照行高）
    for yi in range(0, height_chars + 1):
        yyy = oy + yi * unit_px_vertical
        txt = str(yi)
        try:
            bbox = draw.textbbox((0, 0), txt, font=font_sm)
            h = bbox[3] - bbox[1]
        except Exception:
            h = 14
        draw.text((table_x1 + 4, yyy - h // 2), txt, fill=(0, 70, 100), font=font_sm)

    def _pick_label_mode(cell_w_px: int, cell_h_px: int):
        # full: 兩行座標；compact: 單行 r,c；none: 不標（高度以 unit_px_vertical 為準）
        if cell_w_px >= 14 * unit_px and cell_h_px >= 3 * unit_px_vertical:
            return "full"
        if cell_w_px >= 6 * unit_px and cell_h_px >= 2 * unit_px_vertical:
            return "compact"
        return "none"

    def _truncate_to_width(d, fnt, txt: str, max_w: int, suffix: str = "…") -> str:
        if max_w <= 0:
            return ""
        txt = "" if txt is None else str(txt)
        if _text_width(d, fnt, txt) <= max_w:
            return txt
        while txt and _text_width(d, fnt, txt + suffix) > max_w:
            txt = txt[:-1]
        return txt + suffix if txt else suffix

    def _truncate_to_width_mixed(txt: str, max_w: int, fs: int, suffix: str = "…") -> str:
        """依混合字體寬度截斷（與 PIL 後端一致，供 emoji 正確顯示時使用）。"""
        if max_w <= 0:
            return ""
        txt = "" if txt is None else str(txt)
        if measure_text_width(txt, fs) <= max_w:
            return txt
        while txt and measure_text_width(txt + suffix, fs) > max_w:
            txt = txt[:-1]
        return txt + suffix if txt else suffix

    def _cell_font(size: int):
        return get_font_cjk(size)

    def _draw_cell_content(px0: int, py0: int, px1: int, py1: int, lines: list, color=(0, 0, 0)):
        """在 cell 矩形內繪製多行文字，與 PIL 後端一致：emoji 用 get_font_emoji，CJK 用 get_font_cjk（混合字體）。"""
        if not lines:
            return
        pad = 2
        bottom_margin = 6
        cell_w = max(0, px1 - px0 - 2 * pad)
        cell_h = max(0, py1 - py0 - 2 * pad)
        n_lines = max(1, len(lines))
        inner_h = max(1, cell_h - bottom_margin)
        per_line_max = max(1, inner_h // n_lines)
        max_font = max(14, int(unit_px_vertical * 0.85))
        font_size = min(max_font, per_line_max - 2)
        font_size = max(6, font_size)
        fnt = _cell_font(font_size)
        while font_size >= 6:
            try:
                lh = draw.textbbox((0, 0), "Ag字", font=fnt)[3] - draw.textbbox((0, 0), "Ag字", font=fnt)[1]
            except Exception:
                lh = font_size + 4
            lh_safe = lh + 2
            if n_lines * lh_safe <= inner_h:
                break
            font_size -= 1
            fnt = _cell_font(font_size)
        try:
            lh = draw.textbbox((0, 0), "Ag字", font=fnt)[3] - draw.textbbox((0, 0), "Ag字", font=fnt)[1]
        except Exception:
            lh = font_size + 4
        for i, line in enumerate(lines[:n_lines]):
            if (i + 1) * lh > inner_h:
                break
            truncated = _truncate_to_width_mixed(str(line), cell_w, font_size)
            draw_text_with_mixed_fonts(
                draw, truncated,
                px0 + pad, py0 + pad + i * lh,
                font_size, color, img_mode="RGB"
            )

    # 標註每個 data cell 的區域（以字元座標表示）。格子太小就降級標註，避免擠在一起。
    data_y = data_start
    for r_idx, rh in enumerate(row_heights):
        rh = max(1, int(rh))
        for c_idx in range(ncols):
            # 外框（含框線佔位）— 淡灰，讓線看起來「連實」
            bx0 = x_borders[c_idx]
            bx1 = x_borders[c_idx + 1]
            x0 = x_borders[c_idx] + 1
            x1 = x_borders[c_idx + 1] - 1
            y0 = data_y
            y1 = data_y + rh - 1
            # 轉成像素（橫向 unit_px，縱向 unit_px_vertical）
            bpx0 = ox + bx0 * unit_px
            bpy0 = oy + y0 * unit_px_vertical
            bpx1 = ox + (bx1 + 1) * unit_px
            bpy1 = oy + (y1 + 1) * unit_px_vertical
            draw.rectangle([bpx0, bpy0, bpx1, bpy1], outline=(210, 210, 210), width=1)

            px0 = ox + x0 * unit_px
            py0 = oy + y0 * unit_px_vertical
            px1 = ox + (x1 + 1) * unit_px
            py1 = oy + (y1 + 1) * unit_px_vertical
            draw.rectangle([px0, py0, px1, py1], outline=(230, 120, 40), width=1)
            mode = _pick_label_mode(px1 - px0, py1 - py0)
            if mode == "full":
                label = f"r{r_idx},c{c_idx}\\n({x0},{y0})-({x1},{y1})"
                draw.text((px0 + 2, py0 + 2), label, fill=(120, 60, 0), font=font_sm)
            elif mode == "compact":
                draw.text((px0 + 2, py0 + 2), f"r{r_idx},c{c_idx}", fill=(120, 60, 0), font=font_sm)
            # 渲染該格文字內容（方便核對）
            cell_lines = []
            if r_idx < len(row_lines_list) and c_idx < len(row_lines_list[r_idx]):
                cell_lines = [str(ln) for ln in row_lines_list[r_idx][c_idx]]
            if not cell_lines and r_idx < len(rows_list) and c_idx < len(rows_list[r_idx]):
                cell_lines = [str(rows_list[r_idx][c_idx])]
            if cell_lines:
                _draw_cell_content(px0, py0, px1, py1, cell_lines, color=(80, 50, 20))
        data_y += rh

    # header cell
    if has_headers and header_start is not None:
        hy0 = header_start
        hy1 = header_start + max(1, header_height) - 1
        for c_idx in range(ncols):
            # 外框（含框線佔位）
            bx0 = x_borders[c_idx]
            bx1 = x_borders[c_idx + 1]
            x0 = x_borders[c_idx] + 1
            x1 = x_borders[c_idx + 1] - 1
            bpx0 = ox + bx0 * unit_px
            bpy0 = oy + hy0 * unit_px_vertical
            bpx1 = ox + (bx1 + 1) * unit_px
            bpy1 = oy + (hy1 + 1) * unit_px_vertical
            draw.rectangle([bpx0, bpy0, bpx1, bpy1], outline=(180, 180, 180), width=1)

            px0 = ox + x0 * unit_px
            py0 = oy + hy0 * unit_px_vertical
            px1 = ox + (x1 + 1) * unit_px
            py1 = oy + (hy1 + 1) * unit_px_vertical
            draw.rectangle([px0, py0, px1, py1], outline=(40, 120, 200), width=1)
            mode = _pick_label_mode(px1 - px0, py1 - py0)
            if mode != "none":
                draw.text((px0 + 2, py0 + 2), f"H{c_idx}", fill=(0, 70, 140), font=font_sm)
            # 渲染表頭文字內容
            hdr_lines = []
            if c_idx < len(header_lines_list):
                hdr_lines = [str(ln) for ln in header_lines_list[c_idx]]
            if not hdr_lines and c_idx < len(headers_list):
                hdr_lines = [str(headers_list[c_idx])]
            if hdr_lines:
                _draw_cell_content(px0, py0, px1, py1, hdr_lines, color=(0, 70, 140))

    # 標題列文字
    if has_title and title_row is not None and title_text:
        tx0 = table_x0
        ty0 = oy + title_row * unit_px_vertical
        tx1 = table_x1
        ty1 = oy + (title_row + 1) * unit_px_vertical
        _draw_cell_content(tx0, ty0, tx1, ty1, [title_text], color=(0, 90, 160))

    # 底註列文字
    if has_footer and footer_row is not None and footer_text:
        fx0 = table_x0
        fy0 = oy + footer_row * unit_px_vertical
        fx1 = table_x1
        fy1 = oy + (footer_row + 1) * unit_px_vertical
        _draw_cell_content(fx0, fy0, fx1, fy1, [footer_text], color=(0, 90, 160))

    # legend（固定在右側，不覆蓋表格）
    info = [
        "ASCII blueprint PIL preview",
        f"unit_px={unit_px}",
        f"width_chars={width_chars}, height_chars={height_chars}",
        f"ncols={ncols}, nrows={len(row_heights)}",
        "note: gray=cell incl. border cols; colored=content area",
    ]
    # legend 先計算換行結果，再自動決定框高度，避免文字跑出框線
    legend_inner_w = max(80, int(legend_w - 20))
    legend_box_x0 = legend_x0
    legend_box_x1 = legend_x1
    legend_box_y0 = table_y0  # 固定在右側上方

    # 嘗試用較大的字，但如果高度塞不下就縮小
    legend_font_size = max(10, min(18, base_font_size - 6))
    legend_font = font_sm
    try:
        legend_font = ImageFont.truetype(FONT_CJK, legend_font_size)
    except Exception:
        legend_font = font_sm

    def _build_legend_lines(fnt):
        lines = []
        for line in info:
            lines.extend(_wrap_text(draw, fnt, line, legend_inner_w))
        return lines

    def _line_height(fnt):
        try:
            bb = draw.textbbox((0, 0), "Ag字", font=fnt)
            th = max(0, bb[3] - bb[1])
        except Exception:
            th = text_h
        return max(16, int(th + 8))

    legend_lines = _build_legend_lines(legend_font)
    lh = _line_height(legend_font)
    legend_box_h = 12 + len(legend_lines) * lh + 12
    max_h = table_h_px

    # 若太高，逐步縮小字體
    while legend_box_h > max_h and legend_font_size > 9:
        legend_font_size -= 1
        try:
            legend_font = ImageFont.truetype(FONT_CJK, legend_font_size)
        except Exception:
            break
        legend_lines = _build_legend_lines(legend_font)
        lh = _line_height(legend_font)
        legend_box_h = 12 + len(legend_lines) * lh + 12

    # 若仍太高，截斷並加省略號
    if legend_box_h > max_h:
        max_lines = max(1, int((max_h - 24) / lh))
        if len(legend_lines) > max_lines:
            legend_lines = legend_lines[:max_lines - 1] + ["..."]
        legend_box_h = max_h

    legend_box_y1 = legend_box_y0 + legend_box_h
    if legend_box_y1 > table_y1:
        legend_box_y1 = table_y1

    draw.rectangle([legend_box_x0, legend_box_y0, legend_box_x1, legend_box_y1], fill=(255, 255, 255), outline=(0, 0, 0), width=1)
    ly = legend_box_y0 + 12
    for wl in legend_lines:
        draw.text((legend_x0 + 10, ly), wl, fill=(0, 0, 0), font=legend_font)
        ly += lh

    # 下方文字面板：Regions/說明（不覆蓋 table）
    draw.rectangle([table_x0, bottom_y0, legend_x1, bottom_y1], fill=(250, 250, 250), outline=(0, 0, 0), width=1)
    bx = table_x0 + 12
    by = bottom_y0 + 10
    for wl in bottom_lines:
        draw.text((bx, by), wl, fill=(0, 0, 0), font=panel_font)
        by += panel_line_h

    try:
        img.save(out_png_path, "PNG")
    except Exception as e:
        return None, f"PIL 儲存失敗: {e}"
    return out_png_path, warning

def is_emoji_modifier_or_joiner(char):
    """判斷是否為 emoji 修飾符或連接符（應與前一個 emoji 同一區段、用同一字型繪製）"""
    code = ord(char)
    if code == 0xFE0F:  # Variation Selector-16 (emoji style)
        return True
    if code == 0x200D:  # ZWJ (Zero Width Joiner)，用於組合 emoji
        return True
    if 0x1F3FB <= code <= 0x1F3FF:  # 膚色修飾
        return True
    if 0x1F9B0 <= code <= 0x1F9B3:   # 髮色修飾
        return True
    if 0xFE00 <= code <= 0xFE0F:     # 其他 variation selector
        return True
    return False


def is_emoji(char):
    """判斷是否為 Emoji（需用支援 emoji 的字型繪製）"""
    # 顏色圈支援度不統一，統一替換為文字
    color_circles = {
        '🟢': '(綠)', '🟡': '(黃)', '🔴': '(紅)', '🟠': '(橙)',
        '🔵': '(藍)', '⚫': '(黑)', '⚪': '(白)', '🟣': '(紫)',
        '🟤': '(棕)', '🟣': '(紫)', '🟡': '(黃)'
    }
    if char in color_circles:
        return 'special'
    code = ord(char)
    # 修飾/連接符單獨出現時不當作 emoji 起點，由 split_text_by_font 併入前段
    if is_emoji_modifier_or_joiner(char):
        return False
    # Emoji Unicode 範圍（涵蓋常見符號與圖形）
    emoji_ranges = [
        (0x2600, 0x26FF),     # 雜項符號
        (0x2700, 0x27BF),     # 裝飾字母
        (0x1F300, 0x1F5FF),   # 符號和圖形
        (0x1F600, 0x1F64F),   # 笑臉與情感
        (0x1F680, 0x1F6FF),   # 交通和地圖
        (0x1F1E0, 0x1F1FF),   # 國旗
        (0x1F900, 0x1F9FF),   # 補充符號與圖形
        (0x1FA00, 0x1FA6F),   # 象棋等
        (0x1FA70, 0x1FAFF),   # 擴展 A
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
    """將文字分段，返回 [(文字, 字體類型), ...]。Emoji 修飾符/ZWJ 會併入前一個 emoji 區段，整段用 emoji 字型繪製。"""
    text = replace_color_circles(str(text))
    segments = []
    current_type = None
    current_text = ""

    for char in text:
        # 若目前是 emoji 區段，且此字為修飾符/連接符，一律併入同一區段（用 emoji 字型畫整段）
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

def _fill_for_draw(fill_color, img_mode="RGB"):
    """PIL 繪製用顏色：確保為 (r,g,b) 或 (r,g,b,a) 的 tuple。"""
    if isinstance(fill_color, (list, tuple)) and len(fill_color) >= 3:
        part = fill_color[:4] if len(fill_color) > 3 else fill_color[:3]
        out = tuple(int(x) for x in part)
        return out[:3] if img_mode == "RGB" and len(out) == 4 else out
    return (0, 0, 0)


def draw_text_with_mixed_fonts(draw, text, x, y, font_size, fill_color, baseline_offset=0, img_mode=None):
    """使用混合字體繪製文字：CJK 用 Noto Sans CJK，Emoji 用支援 emoji 的字型（Noto Color Emoji / Symbola 等）。"""
    if img_mode is None:
        img_mode = "RGB"
    fill = _fill_for_draw(fill_color, img_mode) if isinstance(fill_color, (list, tuple)) else _fill_for_draw(parse_color(str(fill_color)), img_mode)
    segments = split_text_by_font(str(text))
    current_x = x

    for segment_text, font_type in segments:
        if font_type == "emoji":
            font = get_font_emoji(font_size)
            draw_y = y + 2  # emoji 字型與 CJK 對齊微調
        else:
            font = get_font_cjk(font_size)
            draw_y = y
        try:
            draw.text((current_x, draw_y), segment_text, font=font, fill=fill)
        except Exception:
            if font_type == "emoji":
                font = get_font_cjk(font_size)
                draw.text((current_x, y), segment_text, font=font, fill=fill)
            else:
                raise
        try:
            width = font.getbbox(segment_text)[2] - font.getbbox(segment_text)[0]
        except Exception:
            width = int(font_size * len(segment_text) * 0.6)
        current_x += width

    return current_x


def _align_x(cell_left, cell_width, text_width, align, padding=10):
    """依對齊方式計算文字起始 x。align: left | center | right。"""
    if align == "right":
        return max(cell_left, cell_left + cell_width - padding - text_width)
    if align == "center":
        return cell_left + max(0, (cell_width - text_width) // 2)
    return cell_left + padding


def draw_text_aligned(draw, text, cell_left, y, cell_width, font_size, fill_color, align, img_mode=None):
    """在欄位內依 align（left/center/right）繪製文字與 emoji（混合字體）。"""
    if img_mode is None:
        img_mode = "RGB"
    text_str = str(text)
    tw = measure_text_width(text_str, font_size)
    x = _align_x(cell_left, cell_width, tw, align)
    draw_text_with_mixed_fonts(draw, text_str, x, y, font_size, fill_color, img_mode=img_mode)

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
    align = (merged_params.get("align") or merged_params.get("cell_align") or "left").lower().strip()
    if align not in ("left", "center", "right"):
        align = "left"
    header_align = (merged_params.get("header_align") or "center").lower().strip()
    if header_align not in ("left", "center", "right"):
        header_align = "center"

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
    img_mode_str = 'RGBA' if use_rgba else 'RGB'
    img = Image.new(img_mode_str, (width, height), parse_color(style.bg_color))
    draw = ImageDraw.Draw(img)

    # 預先載入 CJK/Emoji 字體（供 measure_text_width / draw_text_with_mixed_fonts 使用）
    get_font_cjk(cell_font_size)
    get_font_cjk(header_font_size)
    get_font_emoji(cell_font_size)

    y = padding
    title_fill = parse_color(style.header_text)
    header_fill = parse_color(style.header_text)
    cell_fill = parse_color(style.text_color)

    # 標題（置中）
    if data.get("title"):
        draw.rectangle([padding, y, width-padding, y+40], fill=parse_color(style.header_bg))
        draw_text_aligned(draw, data["title"], padding, y+10, width - 2*padding, 22, title_fill, "center", img_mode=img_mode_str)
        y += 50

    # 表頭（依 header_align）
    draw.rectangle([padding, y, width-padding, y+header_height], fill=parse_color(style.header_bg))
    x_offset = padding
    for i, h in enumerate(headers):
        cw = col_widths[i] if i < len(col_widths) else 60
        draw_text_aligned(draw, h, x_offset, y+15, cw, header_font_size, header_fill, header_align, img_mode=img_mode_str)
        x_offset += cw
    y += header_height

    # 資料列（依 align）
    for idx, row in enumerate(rows):
        row_bg = style.alt_row_color if idx % 2 == 0 else style.bg_color
        draw.rectangle([padding, y, width-padding, y+cell_height], fill=parse_color(row_bg))
        draw.line([padding, y+cell_height, width-padding, y+cell_height], fill=parse_color(style.border_color))
        x_offset = padding
        for i, cell in enumerate(row):
            cw = col_widths[i] if i < len(col_widths) else 60
            draw_text_aligned(draw, str(cell), x_offset, y+10, cw, cell_font_size, cell_fill, align, img_mode=img_mode_str)
            x_offset += cw
        y += cell_height

    # 底部（置中，混合字體以支援 emoji）
    draw.rectangle([padding, y, width-padding, y+30], fill=parse_color(style.header_bg))
    footer_text = data.get("footer") or "Generated by ZenTable (PIL fallback)"
    draw_text_aligned(draw, footer_text, padding, y+8, width - 2*padding, 12, header_fill, "center", img_mode=img_mode_str)
    
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
                print(f"⚠️  載入主題失敗 {zip_path}: {e}", file=sys.stderr)
        folder_path = os.path.join(base, mode, theme_name, 'template.json')
        if os.path.exists(folder_path):
            try:
                return load_json(folder_path)
            except Exception as e:
                print(f"⚠️  載入主題失敗 {folder_path}: {e}", file=sys.stderr)
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
        print(f"🎨 從 themes 目錄載入: {theme_name} ({mode})", file=sys.stderr)
        return theme
    # 常見別名：前端傳 dark/light 時對應目錄 default_dark/default_light
    alias = {"dark": "default_dark", "light": "default_light"}.get(theme_name)
    if alias:
        theme = load_theme_from_themes_dir(alias, mode)
        if theme:
            print(f"🎨 從 themes 目錄載入: {alias} ({mode}) [別名 {theme_name}]", file=sys.stderr)
            return theme
    if theme_name not in ("default_dark", "default_light"):
        for fallback in ["default_dark", "default_light"]:
            theme = load_theme_from_themes_dir(fallback, mode)
            if theme:
                print(f"⚠️  主題 '{theme_name}' 不存在，使用 {fallback}", file=sys.stderr)
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

def transpose_table(data):
    """Transpose a {headers, rows} table so that the header becomes the first column.

    Typical use: wide tables on mobile → transpose to a key/value style table.

    Output headers:
      ["Field", <row0_key>, <row1_key>, ...]
    where row keys are taken from the first cell of each original row (if present).

    Output rows:
      Each original column becomes a row:
        [<original header>, <cell(row0,col)>, <cell(row1,col)>, ...]

    This is intentionally simple and robust (pads missing cells with "").
    """
    headers = list(data.get("headers", []) or [])
    rows = [list(r) for r in (data.get("rows", []) or [])]

    if not headers:
        return {"headers": [], "rows": [], "title": data.get("title", ""), "footer": data.get("footer", "")}

    # Column headers after transpose come from the first cell of each row (if available)
    row_keys = []
    for r in rows:
        row_keys.append(cell_text(r[0]) if len(r) > 0 else "")

    out_headers = ["Field"] + row_keys

    out_rows = []
    for j, h in enumerate(headers):
        new_row = ["" if h is None else str(h)]
        for i, r in enumerate(rows):
            new_row.append(cell_text(r[j]) if j < len(r) else "")
        out_rows.append(new_row)

    return {"headers": out_headers, "rows": out_rows, "title": data.get("title", ""), "footer": data.get("footer", "")}


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


def _smart_wrap_text(text: str, limit: int) -> str:
    """簡易智慧換行：優先在語意斷點切，否則固定長度切。"""
    s = "" if text is None else str(text)
    if "\n" in s or len(s) <= limit:
        return s

    # URL 友善斷點
    s = s.replace("/", "/\n").replace("?", "?\n").replace("&", "&\n").replace("=", "=\n")
    if "\n" in s:
        parts = []
        for seg in s.split("\n"):
            parts.append(_smart_wrap_text(seg, limit))
        return "\n".join(p for p in parts if p != "")

    punct = set("，。；：、,.;: ")
    out, cur = [], ""
    soft_cut = max(1, int(limit * 0.6))
    for ch in s:
        cur += ch
        if ch in punct and len(cur) >= soft_cut:
            out.append(cur.rstrip())
            cur = ""
        elif len(cur) >= limit:
            out.append(cur)
            cur = ""
    if cur:
        out.append(cur)
    return "\n".join(p for p in out if p)


def apply_smart_wrap(data: dict, width: Optional[int] = None) -> Tuple[dict, dict]:
    """依寬度/欄數預估每欄可容字數，對過長文字插入軟換行。"""
    headers = list(data.get("headers", []) or [])
    rows = [list(r) for r in (data.get("rows", []) or [])]
    if not headers or not rows:
        return data, {"applied": False, "reason": "no-data"}

    col_count = max(1, len(headers))
    base_width = int(width) if width else 600
    total_chars = max(24, int(base_width / 13))
    per_col = max(8, total_chars // col_count)

    changed_cells = 0
    new_rows = []
    for r in rows:
        rr = []
        for i, c in enumerate(r):
            limit = max(6, per_col - 2) if i == 0 else per_col
            if isinstance(c, dict):
                old_t = c.get("text", "")
                new_t = _smart_wrap_text(old_t, limit)
                if new_t != ("" if old_t is None else str(old_t)):
                    changed_cells += 1
                cc = dict(c)
                cc["text"] = new_t
                rr.append(cc)
            else:
                old_t = "" if c is None else str(c)
                new_t = _smart_wrap_text(old_t, limit)
                if new_t != old_t:
                    changed_cells += 1
                rr.append(new_t)
        new_rows.append(rr)

    out = {"headers": headers, "rows": new_rows, "title": data.get("title", ""), "footer": data.get("footer", "")}
    return out, {
        "applied": changed_cells > 0,
        "changed_cells": changed_cells,
        "per_col_limit": per_col,
        "col_count": col_count,
        "base_width": base_width,
    }

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
        print('  --text-scale S  （僅 CSS）文字/間距縮放：smallest|small|auto|large|largest 或數值（如 1.4）')
        print('  --text-scale-max M  （僅 CSS, auto）自動縮放上限（預設 2.5）')
        print('  --scale N      輸出尺寸倍數')
        print('  --auto-height  自動高度（用較高 viewport 渲染後，依像素內容裁切高度）')
        print('  --auto-height-max H  auto-height 預渲染高度上限（預設 3600）')
        print('  --auto-width   自動寬度（先量測/渲染後，必要時加寬再重渲）')
        print('  --auto-width-max W  auto-width 起始寬度（預設 2400）')
        print('  --no-auto-width / --no-aw  關閉自動寬度')
        print('  --per-page N   每頁列數（預設 %d）' % ROWS_PER_PAGE)
        print('  --fill-width   background|container|scale|no-shrink（搭配 --width）')
        print('  --theme FILE    主題檔案（直接用於測試，不儲存）')
        print('  --theme-name    themes/ 目錄中的主題名稱')
        print('  --tt           透明模式：保留 theme 內 rgba/#RRGGBBAA 的 alpha（非 tt 會強制去除 alpha 變不透明）')
        print('  --page N        第 N 頁（每頁 %d 列）' % ROWS_PER_PAGE)
        print('  --transpose     轉置表格（header 變第一欄；適合手機閱讀）')
        print('  --cc            --transpose 的別名')
        print('  --debug-auto-width  儲存每次 auto-width 嘗試的右側邊界裁切圖（用於診斷）')
        print('  --debug-auto-width-strip N  右側裁切寬度（預設 40px）')
        print('  --wrap-gap N   固定寬度模式用：viewport 變成 (width+N)，但排版寬度縮成 calc(100%-N) 以強制更早換行（避免右側溢出）')
        print('  --smart-wrap    啟用智慧換行（預設開）')
        print('  --no-smart-wrap / --nosw / nosw  關閉智慧換行，保留原始文字斷行')
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
    calibration_json = None  # 字元寬度校準數據
    page = 1
    sort_by = None
    sort_asc = True
    transpose = False
    bg_mode = "theme"  # transparent | theme | #RRGGBB
    force_width = None
    text_scale = None
    text_scale_mode = "auto"
    text_scale_max = 2.5
    scale_factor = 1.0
    per_page = ROWS_PER_PAGE
    fill_width_method = "container"  # background | container | scale | no-shrink

    tt = False
    tt_set = False

    auto_height = False
    auto_height_set = False
    auto_height_max = 3600

    auto_width = False
    auto_width_set = False
    auto_width_max = 2400

    width_set = False
    text_scale_set = False
    text_scale_max_set = False

    debug_auto_width = False
    debug_auto_width_strip = 40

    # 預設啟用智慧換行；可用 --no-smart-wrap/--nosw 關閉
    smart_wrap = True

    wrap_gap = 0  # explicit: shrink effective layout width by gap; viewport becomes (width+gap)
    
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
        elif arg == "--tt":
            tt = True
            tt_set = True
        elif arg == "--params" and i + 1 < len(sys.argv):
            try:
                custom_params = json.loads(sys.argv[i + 1])
            except:
                print("⚠️  無效的 params JSON", file=sys.stderr)
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
        elif arg == "--transpose" or arg == "--cc":
            transpose = True
        elif arg == "--debug-auto-width":
            debug_auto_width = True
        elif arg == "--debug-auto-width-strip" and i + 1 < len(sys.argv):
            try:
                debug_auto_width_strip = max(10, int(sys.argv[i + 1]))
                debug_auto_width = True
            except ValueError:
                pass
        elif arg == "--wrap-gap" and i + 1 < len(sys.argv):
            try:
                wrap_gap = max(0, int(sys.argv[i + 1]))
            except ValueError:
                pass
        elif arg == "--smart-wrap":
            smart_wrap = True
        elif arg == "--no-smart-wrap" or arg == "--nosw" or arg == "nosw":
            smart_wrap = False
        elif arg == "--bg" and i + 1 < len(sys.argv):
            bg_mode = sys.argv[i + 1].strip().lower()
        elif arg == "--width" and i + 1 < len(sys.argv):
            try:
                force_width = max(1, int(sys.argv[i + 1]))
                width_set = True
            except ValueError:
                pass
        elif arg == "--text-scale" and i + 1 < len(sys.argv):
            raw = sys.argv[i + 1].strip()
            raw_lower = raw.lower()
            text_scale_set = True
            if raw_lower in ("smallest", "small", "auto", "large", "largest"):
                text_scale = None
                text_scale_mode = raw_lower
            else:
                try:
                    text_scale = float(raw)
                    text_scale_mode = "auto"
                except ValueError:
                    text_scale = None
                    text_scale_mode = "auto"
        elif arg == "--text-scale-max" and i + 1 < len(sys.argv):
            try:
                text_scale_max = float(sys.argv[i + 1])
                text_scale_max_set = True
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
        elif arg == "--calibration" and i + 1 < len(sys.argv):
            try:
                calibration_json = json.loads(sys.argv[i + 1])
            except:
                print("⚠️  無效的 calibration JSON", file=sys.stderr)
        elif arg == "--fill-width" and i + 1 < len(sys.argv):
            m = sys.argv[i + 1].strip().lower()
            if m in ("background", "container", "scale", "no-shrink"):
                fill_width_method = m
        elif arg == "--auto-height":
            auto_height = True
            auto_height_set = True
        elif arg == "--auto-height-max" and i + 1 < len(sys.argv):
            try:
                auto_height_max = max(200, int(sys.argv[i + 1]))
            except ValueError:
                pass
        elif arg == "--auto-width":
            auto_width = True
            auto_width_set = True
        elif arg == "--no-auto-width" or arg == "--no-aw":
            auto_width = False
            auto_width_set = True
        elif arg == "--auto-width-max" and i + 1 < len(sys.argv):
            try:
                auto_width_max = max(200, int(sys.argv[i + 1]))
            except ValueError:
                pass
    
    # Default behavior: enable auto-height + auto-width unless the user explicitly set them.
    if not auto_height_set:
        auto_height = True
    if not auto_width_set:
        auto_width = True

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

    # 統一輸入格式（陣列 of 物件 或 headers+rows）
    data = normalise_data(data)
    if transpose:
        data = transpose_table(data)
    # 再套用排序與分頁
    data = apply_sort_and_page(data, sort_by=sort_by, sort_asc=sort_asc, page=page, per_page=per_page)

    # 預設智慧換行：渲染前先在語意斷點插入換行，減少窄寬表格斷句破壞
    smart_wrap_stats = {"applied": False}
    if smart_wrap:
        data, smart_wrap_stats = apply_smart_wrap(data, width=force_width)
        if smart_wrap_stats.get("applied"):
            print(
                f"🧠 smart-wrap 已介入：changed_cells={smart_wrap_stats.get('changed_cells')}, "
                f"per_col_limit≈{smart_wrap_stats.get('per_col_limit')}",
                file=sys.stderr,
            )
    
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
    
    # 避免污染 stdout（特別是 ASCII 模式會直接回傳文本）
    print(f"🖥️  渲染模式: {mode}", file=sys.stderr)
    
    # 三種模式皆從 themes/<mode>/ 載入主題（或 --theme 指定檔案）
    theme_mode = 'text' if mode == "ASCII" else ('pil' if mode.startswith("PIL") else 'css')
    if theme_file:
        theme = load_json(theme_file)
        print(f"🎨 使用主題檔案: {theme_file}", file=sys.stderr)
    else:
        theme = get_theme(theme_name, theme_mode)

    # Apply theme defaults (template.json -> meta.defaults) when CLI did not explicitly set options
    def _get_theme_defaults(th: dict) -> dict:
        if not isinstance(th, dict):
            return {}
        meta = th.get('meta', {}) if isinstance(th.get('meta', {}), dict) else {}
        d = meta.get('defaults', {}) if isinstance(meta.get('defaults', {}), dict) else {}
        if not d and isinstance(th.get('defaults', {}), dict):
            d = th.get('defaults', {})
        return d if isinstance(d, dict) else {}

    defaults = _get_theme_defaults(theme)
    if defaults:
        if (not tt_set) and ('tt' in defaults):
            try: tt = bool(defaults.get('tt'))
            except Exception: pass

        if (not width_set) and ('width' in defaults):
            try:
                force_width = max(1, int(defaults.get('width')))
                width_set = True
            except Exception: pass

        if (not auto_width_set) and ('auto_width' in defaults):
            try: auto_width = bool(defaults.get('auto_width'))
            except Exception: pass

        if (not auto_height_set) and ('auto_height' in defaults):
            try: auto_height = bool(defaults.get('auto_height'))
            except Exception: pass

    # 規則：只要有設定 --width（或由 theme defaults 套入 width），就自動關閉 auto-width。
    # 避免最終輸出寬度被 auto-width 擴張，導致文字看起來變小。
    if width_set:
        auto_width = False

        if (not text_scale_set) and ('text_scale' in defaults):
            raw = str(defaults.get('text_scale')).strip()
            raw_lower = raw.lower()
            if raw_lower in ("smallest", "small", "auto", "large", "largest"):
                text_scale = None
                text_scale_mode = raw_lower
            else:
                try:
                    text_scale = float(raw)
                    text_scale_mode = "auto"
                except Exception: pass

        if (not text_scale_max_set) and ('text_scale_max' in defaults):
            try:
                text_scale_max = float(defaults.get('text_scale_max'))
                text_scale_max_set = True
            except Exception: pass

        if ('auto_width_max' in defaults) and (not width_set):
            try: auto_width_max = max(200, int(defaults.get('auto_width_max')))
            except Exception: pass

        if ('auto_height_max' in defaults):
            try: auto_height_max = max(200, int(defaults.get('auto_height_max')))
            except Exception: pass
    
    # ASCII 模式
    if mode == "ASCII":
        def _truthy(v):
            if isinstance(v, bool):
                return v
            if isinstance(v, (int, float)):
                return v != 0
            if isinstance(v, str):
                s = v.strip().lower()
                return s not in ("", "0", "false", "no", "off", "null", "none")
            return False

        cal = None
        if calibration_json and isinstance(calibration_json, dict):
            if 'char_widths' in calibration_json:
                cal = {'custom': calibration_json['char_widths']}
            else:
                cal = calibration_json
            cats = [k for k in ('ascii','cjk','box','emoji','half_space','full_space') if k in cal]
            custom_count = len(cal.get('custom', {}))
            print(f"📐 收到校準 JSON: 類別={cats}, 自訂字元數={custom_count}", file=sys.stderr)

        # ASCII style：允許 --params 覆蓋（前端即時調整）
        theme_params = (theme or {}).get("params") or {}
        merged_ascii_params = {**(theme_params or {}), **(custom_params or {})}
        ascii_style = ASCIIStyle(
            border_style=merged_ascii_params.get("style", "double"),
            padding=int(merged_ascii_params.get("padding", 2)),
            align=merged_ascii_params.get("align", "left"),
            header_align=merged_ascii_params.get("header_align", "center"),
        )

        ascii_debug = _truthy(merged_ascii_params.get("ascii_debug"))
        stage1_pil_preview = _truthy(merged_ascii_params.get("stage1_pil_preview"))
        stage1_unit_px = merged_ascii_params.get("stage1_unit_px", 10)

        if ascii_debug:
            # stage1/stage2：不套用校準（預設半形=1、全形=2），先產生版面藍圖與參考輸出
            blueprint = {}
            stage2_text = render_ascii(data, theme, style=ascii_style, calibration=None, debug_details=blueprint)

            # stage3：套用校準後的輸出與細節
            calibrated = {}
            ascii_output = render_ascii(data, theme, style=ascii_style, calibration=cal, debug_details=calibrated)
        else:
            blueprint = None
            calibrated = None
            stage2_text = None
            ascii_output = render_ascii(data, theme, style=ascii_style, calibration=cal, debug_details=None)

        if output_ascii:
            if ascii_debug:
                # stage1: 欄寬/對齊計算摘要；stage2: 參考結果（等寬字型）；text: 校準輸出（stage3）
                stage1_lines = []
                if isinstance(blueprint, dict):
                    stage1_lines.extend([
                        "stage1 (blueprint): 不套用校準（預設半形=1.0、全形=2.0）",
                        f"border_style={blueprint.get('border_style')}, padding={blueprint.get('padding')}, align={blueprint.get('align')}, header_align={blueprint.get('header_align')}",
                        f"space_width(sw)={blueprint.get('space_width')}, h='{blueprint.get('h_char')}' width(hw)={blueprint.get('h_char_width')}",
                        f"raw_widths={blueprint.get('raw_widths')}",
                        f"col_h_counts={blueprint.get('col_h_counts')}",
                        f"col_targets={blueprint.get('col_targets')}",
                        f"row_heights={blueprint.get('row_heights')}",
                        f"rows={blueprint.get('nrows')}, cols={blueprint.get('ncols')}",
                    ])

                stage1_pil_image = None
                stage1_pil_warning = None
                if stage1_pil_preview and isinstance(blueprint, dict):
                    try:
                        base = os.path.splitext(os.path.basename(output_ascii))[0]
                        img_name = base + "_stage1.png"
                        img_path = os.path.join(os.path.dirname(output_ascii), img_name)
                        saved_path, warn = render_ascii_blueprint_pil(blueprint, img_path, stage1_unit_px)
                        if saved_path:
                            stage1_pil_image = "/zenTable/" + os.path.basename(saved_path)
                        if warn:
                            stage1_pil_warning = str(warn)
                    except Exception as e:
                        stage1_pil_warning = f"stage1 PIL 預覽失敗: {e}"

                payload = {
                    "text": ascii_output,
                    "stage1": "\n".join(stage1_lines).strip(),
                    "stage2": stage2_text,
                    "stage3_details": {
                        "blueprint": blueprint,
                        "calibrated": calibrated,
                    },
                    "stage1_pil_image": stage1_pil_image,
                    "stage1_pil_warning": stage1_pil_warning,
                }
                with open(output_ascii, 'w', encoding='utf-8') as f:
                    json.dump(payload, f, ensure_ascii=False)
            else:
                with open(output_ascii, 'w', encoding='utf-8') as f:
                    f.write(ascii_output)
            print(f"✅ 已保存: {output_ascii}")
        else:
            print(ascii_output)
    
    # 渲染
    elif mode.startswith("CSS") and chrome_available:
        # （僅 CSS）文字/間距縮放：先縮放主題，再估算 viewport 與產生 HTML
        resolved_text_scale = _resolve_text_scale(
            force_width,
            text_scale,
            text_scale_mode=text_scale_mode,
            text_scale_max=text_scale_max
        )
        theme = _scale_css_styles_px(theme, resolved_text_scale)

        vw, vh, explicit_width = estimate_css_viewport_width_height(data, theme)
        # auto-height: 先用足夠高的 viewport 渲染，避免內容因換行而被截斷。
        if auto_height:
            vh = max(vh, auto_height_max)
        # auto-width: 先用較寬 viewport（或後面量測後再調整）
        if auto_width and not explicit_width:
            vw = max(vw, auto_width_max)
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
        html = generate_css_html(data, theme, transparent=transparent_bg, table_width_pct=table_width_pct, tt=tt)

        # Explicit, user-controlled wrap gap (only when user passed --width).
        if width_set and force_width and wrap_gap:
            html = _inject_wrap_gap_css(html, gap_px=wrap_gap)
            # viewport becomes width+gap; layout uses calc(100%-gap)
            vw = int(force_width) + int(wrap_gap)

        # Fixed-width wrapping helpers:
        # When user forces width, ensure table is constrained to viewport and cells can shrink for wrapping.
        if explicit_width and force_width and force_width > 0:
            try:
                wrap_css = """
<style id="zentable-fixedwidth-wrap">
  /* Fixed width mode: prevent content-driven table expansion */
  table { width: 100% !important; table-layout: fixed !important; }
  th, td {
    min-width: 0 !important;
    max-width: 0 !important;
    overflow: hidden !important;
  }
</style>
"""
                if "</head>" in html:
                    html = html.replace("</head>", wrap_css + "</head>")
                else:
                    html = wrap_css + html
            except Exception:
                pass

        # Optional debug dump: save full HTML/CSS + resolved render inputs for diffing.
        if os.environ.get("ZENTABLE_DUMP_RENDER_INPUT") == "1":
            try:
                dump_base = output_file
                with open(dump_base + ".input.html", "w", encoding="utf-8") as f:
                    f.write(html)
                # extract combined CSS blocks for convenience
                import re as _re
                css_blocks = _re.findall(r"<style[^>]*>(.*?)</style>", html, flags=_re.S | _re.I)
                with open(dump_base + ".input.css", "w", encoding="utf-8") as f:
                    f.write("\n\n/* ---- style block ---- */\n\n".join([c.strip() for c in css_blocks]))
                input_meta = {
                    "theme_name": theme_name,
                    "theme_mode": theme_mode,
                    "theme_file": theme_file,
                    "transparent": bool(transparent_bg),
                    "tt": bool(tt),
                    "bg_mode": bg_mode,
                    "bg_color": bg_color,
                    "explicit_width": bool(explicit_width),
                    "width_set": bool(width_set) if 'width_set' in locals() else None,
                    "force_width": int(force_width) if force_width else None,
                    "fill_width_method": fill_width_method,
                    "auto_width": bool(auto_width),
                    "auto_height": bool(auto_height),
                    "auto_width_max": int(auto_width_max) if auto_width_max else None,
                    "auto_height_max": int(auto_height_max) if auto_height_max else None,
                    "text_scale_mode": text_scale_mode,
                    "text_scale": float(resolved_text_scale) if resolved_text_scale is not None else None,
                    "scale_factor": float(scale_factor),
                    "wrap_gap": int(wrap_gap) if 'wrap_gap' in locals() else 0,
                }
                import json as _json
                with open(dump_base + ".input.json", "w", encoding="utf-8") as f:
                    f.write(_json.dumps(input_meta, ensure_ascii=False, indent=2))
            except Exception:
                pass
        if scale_factor != 1.0:
            vw = max(1, int(vw * scale_factor))
            vh = max(1, int(vh * scale_factor))
        cache_dir = None
        if not theme_file:
            try:
                cache_dir = ensure_theme_cache(theme_name, theme_mode)
            except ValueError:
                pass
        # auto-height/auto-width: 先用較大 viewport 渲染；若邊界仍有內容，代表可能被截斷，則加倍再重渲。
        # Strategy C: DOM pre-measure (local Chrome only) + pixel edge check.
        if auto_height or auto_width:
            max_hard = MAX_VIEWPORT_DIM
            attempts = 0
            cur_vw = min(vw, max_hard)
            cur_vh = min(vh, max_hard)

            width_steps = []
            render_attempts = []  # [{attempt, vw, vh, css_render_ms}]

            # DOM pre-measure (skip when using remote CSS API)
            # Prefer overflow-based measurement over raw scrollWidth to avoid background/border false positives.
            if auto_width and not os.environ.get("ZENTABLE_CSS_API_URL"):
                try:
                    ov = measure_dom_overflow(html, cache_dir or "/tmp", viewport_width=cur_vw, viewport_height=cur_vh)
                    if ov and (ov.get('body') or ov.get('table')):
                        width_steps.append({"reason": "dom_overflow", "vw": int(cur_vw), **ov})
                        # Prefer BODY overflow for decision (catches elements that spill outside table)
                        src = ov.get('body') or ov.get('table') or {}
                        sw = int(src.get('scrollWidth') or 0)
                        cw = int(src.get('clientWidth') or 0)
                        # Only grow if real overflow exists
                        if sw > (cw + 2) and sw > cur_vw:
                            base_w = int(force_width) if force_width else int(cur_vw)
                            dom_cap = min(max_hard, max(base_w * 2, base_w + 400))
                            need_w = min(int(sw), int(dom_cap))
                            need_w = int(((need_w + 49) // 50) * 50)
                            need_w = min(need_w, max_hard)
                            if need_w > cur_vw:
                                width_steps.append({"reason": "dom", "from": int(cur_vw), "to": int(need_w)})
                                cur_vw = need_w
                    else:
                        need_w = measure_dom_scroll_width(html, cache_dir or "/tmp", viewport_width=cur_vw, viewport_height=cur_vh)
                        if need_w and need_w > cur_vw:
                            base_w = int(force_width) if force_width else int(cur_vw)
                            dom_cap = min(max_hard, max(base_w * 2, base_w + 400))
                            need_w = min(int(need_w), int(dom_cap))
                            need_w = int(((need_w + 49) // 50) * 50)
                            need_w = min(need_w, max_hard)
                            if need_w > cur_vw:
                                width_steps.append({"reason": "dom", "from": int(cur_vw), "to": int(need_w)})
                                cur_vw = need_w
                except Exception:
                    pass

            while True:
                attempts += 1

                # DOM overflow metrics at this viewport (debug/stats)
                attempt_dom = None
                if auto_width and not os.environ.get("ZENTABLE_CSS_API_URL"):
                    try:
                        attempt_dom = measure_dom_overflow(html, cache_dir or "/tmp", viewport_width=cur_vw, viewport_height=cur_vh)
                    except Exception:
                        attempt_dom = None

                success = render_css(
                    html, output_file,
                    transparent=transparent_bg,
                    html_dir=cache_dir,
                    viewport_width=cur_vw,
                    viewport_height=cur_vh,
                    bg_color=bg_color,
                    skip_crop=True,  # 先不裁，才能檢查邊界是否被截
                )
                if success:
                    try:
                        edge_metrics = _right_edge_metrics(output_file, transparent=transparent_bg, x_inset=0)
                        edge_metrics_inset = _right_edge_metrics(output_file, transparent=transparent_bg, x_inset=5)
                        debug_files = None
                        if debug_auto_width:
                            try:
                                from PIL import Image as _Image
                                im = _Image.open(output_file)
                                w, h = im.size
                                dbg_dir = output_file + ".debug"
                                os.makedirs(dbg_dir, exist_ok=True)

                                # full image snapshot for this attempt
                                full_path = os.path.join(dbg_dir, f"attempt_{attempts:02d}_full.png")
                                im.save(full_path, "PNG")

                                # right strip snapshot
                                strip_w = min(int(debug_auto_width_strip), w)
                                strip = im.crop((w - strip_w, 0, w, h))
                                right_path = os.path.join(dbg_dir, f"attempt_{attempts:02d}_right{strip_w}.png")
                                strip.save(right_path, "PNG")

                                debug_files = {"full": full_path, "right_strip": right_path}
                            except Exception:
                                debug_files = None

                        render_attempts.append({
                            "attempt": int(attempts),
                            "vw": int(cur_vw),
                            "vh": int(cur_vh),
                            "css_render_ms": int(LAST_CSS_RENDER_MS) if LAST_CSS_RENDER_MS is not None else None,
                            "dom": attempt_dom,
                            "dom_source": "body" if (attempt_dom and isinstance(attempt_dom, dict) and attempt_dom.get('body')) else "table",
                            "edge": edge_metrics,
                            "edge_inset5": edge_metrics_inset,
                            "debug": debug_files,
                        })
                    except Exception:
                        pass
                else:
                    break

                grew = False
                if auto_height and _bottom_edge_has_content(output_file, transparent=transparent_bg) and cur_vh < max_hard:
                    next_vh = min(cur_vh * 2, max_hard)
                    if next_vh != cur_vh:
                        cur_vh = next_vh
                        grew = True

                # Auto-width edge check (no layout-modifying probe by default):
                # We only look at an inset line to reduce false positives from outer shadows.
                edge_inset = 50
                if auto_width and _right_edge_has_content(output_file, transparent=transparent_bg, x_inset=edge_inset) and cur_vw < max_hard:
                    next_vw = max(cur_vw + 400, int(cur_vw * 1.25))
                    next_vw = min(next_vw, max_hard)
                    if next_vw != cur_vw:
                        width_steps.append({"reason": "edge", "from": int(cur_vw), "to": int(next_vw), "x_inset": int(edge_inset)})
                        cur_vw = next_vw
                        grew = True

                if not grew or attempts >= 6:
                    break

            # 最終：
            # - explicit width：不裁左右，只裁高度（避免 width 被改）
            # - 非 explicit：照原本裁切（含左右空白）
            if success:
                if width_set:
                    crop_to_content_height(output_file, transparent=transparent_bg)
                else:
                    crop_to_content_bounds(output_file, padding=2, transparent=transparent_bg)
        else:
            success = render_css(html, output_file, transparent=transparent_bg, html_dir=cache_dir,
                                viewport_width=vw, viewport_height=vh, bg_color=bg_color,
                                skip_crop=width_set)

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
            # Write a small sidecar JSON for downstream callers (e.g., zx stats)
            try:
                from PIL import Image as _Image
                out_im = _Image.open(output_file)
                out_w, out_h = out_im.size
                meta = {
                    "render_mode": "CSS",
                    "theme_name": theme_name,
                    "tt": bool(tt),
                    "smart_wrap": bool(smart_wrap),
                    "smart_wrap_stats": smart_wrap_stats if 'smart_wrap_stats' in locals() else None,
                    "text_scale_mode": text_scale_mode,
                    "text_scale": float(resolved_text_scale) if resolved_text_scale is not None else None,
                    "viewport": {"w": int(LAST_CSS_VIEWPORT[0]), "h": int(LAST_CSS_VIEWPORT[1])} if LAST_CSS_VIEWPORT else None,
                    "output": {"w": int(out_w), "h": int(out_h)},
                    "css_render_ms": int(LAST_CSS_RENDER_MS) if LAST_CSS_RENDER_MS is not None else None,
                    "auto_width_steps": width_steps if 'width_steps' in locals() else None,
                    "render_attempts": render_attempts if 'render_attempts' in locals() else None,
                }
                import json as _json
                with open(output_file + ".meta.json", "w", encoding="utf-8") as f:
                    f.write(_json.dumps(meta, ensure_ascii=False, indent=2))
            except Exception:
                pass

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

        if os.path.exists(output_file) and auto_height:
            # PIL：可能是純色背景（非透明），所以 transparent 取決於 transparent_bg
            crop_to_content_height(output_file, transparent=transparent_bg)

        if os.path.exists(output_file):
            print(f"✅ 已保存: {output_file}")
        else:
            print("❌ PIL 渲染失敗")
            sys.exit(1)

if __name__ == "__main__":
    main()
