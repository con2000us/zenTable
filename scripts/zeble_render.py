#!/usr/bin/env python3
"""
ZenTable / Zeble 表格渲染程式（專案內版本）

本檔案為專案內唯一可執行版本，供 `gentable_css.php` / `gentable_pil.php` /
`gentable_ascii.php` 以 CLI 方式呼叫（位於 `scripts/`）。

自動偵測可用渲染方式：
1. CSS + Chrome（效果更好）
2. Pure Python + PIL（無依賴 fallback）

用法: python3 zentable_renderer.py <data.json> <output.png> [options]

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

import html as html_module
import json
import sys
import os
import re
import glob
import functools
import subprocess
import zipfile
import time
import unicodedata
from typing import Dict, Any, List, Callable, Optional, Tuple
from dataclasses import dataclass
from zentable.util.text import (
    is_emoji,
    is_emoji_modifier_or_joiner,
    replace_color_circles,
    split_text_by_font,
)
from zentable.util.color import parse_color, hex_rgb, _hex_to_chrome_bg
from zentable.input.loader import load_json, normalise_data
from zentable.input.theme import (
    THEMES_DIR,
    CACHE_BASE,
    ensure_theme_cache,
    get_theme,
    get_theme_source_path,
    list_themes_in_dir,
    load_theme_from_themes_dir,
)
from zentable.transform.cell import normalize_cell, _row_cells, _try_numeric, cell_text
from zentable.transform.highlight import _highlight_rule_matches, resolve_cell_highlight, _highlight_styles_to_css
from zentable.transform.transpose import transpose_table
from zentable.transform.filter import _split_csv, _header_index_map, _find_header_idx, _parse_row_filter_condition, _parse_filter_specs, apply_filters
from zentable.transform.sort_page import ROWS_PER_PAGE, _parse_page_spec, _resolve_page_list, _page_output_path, _try_sort_numeric, _parse_sort_specs, apply_sort_and_page
from zentable.transform.wrap import _smart_wrap_text, apply_smart_wrap
from zentable.output.ascii.charwidth import (
    _is_zero_width, _classify_char, _clamp_width,
    char_display_width, display_width, _space_width,
    calculate_column_widths, align_text,
)
from zentable.output.ascii import renderer as ascii_renderer
from zentable.output.css import crop as css_crop
from zentable.output.css import chrome as css_chrome
from zentable.output.css import viewport as css_viewport
from zentable.output.css import renderer as css_renderer
from zentable.output.pil import font as pil_font
from zentable.output.pil import draw as pil_draw
from zentable.output.pil import renderer as pil_renderer
from zentable.output.pil import blueprint as pil_blueprint
from zentable.orchestration.main import run_cli_main
ASCII_STYLES = ascii_renderer.ASCII_STYLES

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
def render_ascii(data: dict, theme: dict = None, style: ASCIIStyle = None,
                  calibration: dict = None, debug_details: dict = None) -> str:
    """ASCII 渲染（委派至 zentable.output.ascii.renderer）。"""
    if style is None:
        params = (theme or {}).get("params") or {}
        style = ASCIIStyle(
            border_style=params.get("style", "double"),
            padding=int(params.get("padding", 2)),
            align=params.get("align", "left"),
            header_align=params.get("header_align", "center"),
        )
    return ascii_renderer.render_ascii(
        data=data, theme=theme, style=style, calibration=calibration, debug_details=debug_details
    )

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
    return css_chrome.check_chrome_available()

# 透空背景：現代 Chrome 支援 --default-background-color=RRGGBBAA（8 位 hex，Alpha=00 為透明）
# 直接輸出透明 PNG，無需 chroma key 後製，陰影半透明也不會出問題
TRANSPARENT_BG_HEX = "00000000"  # RGBA，Alpha=0 = 透明
MAX_VIEWPORT_DIM = css_viewport.MAX_VIEWPORT_DIM

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

# CSS crop helpers delegate to extracted module (wave4-b3)
crop_to_content_bounds = css_crop.crop_to_content_bounds
_bottom_edge_has_content = css_crop._bottom_edge_has_content
_right_edge_metrics = css_crop._right_edge_metrics
_right_edge_has_content = css_crop._right_edge_has_content
crop_to_content_height = css_crop.crop_to_content_height

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
    return css_chrome.measure_dom_scroll_width(
        html, html_dir, viewport_width, viewport_height,
        transparent_bg_hex=TRANSPARENT_BG_HEX,
    )


def measure_dom_overflow(html: str, html_dir: str, viewport_width: int, viewport_height: int) -> Optional[dict]:
    return css_chrome.measure_dom_overflow(
        html, html_dir, viewport_width, viewport_height,
        transparent_bg_hex=TRANSPARENT_BG_HEX,
    )


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


# CSS viewport helpers delegate to extracted module (wave4-b3)
_scale_css_styles_px = css_viewport._scale_css_styles_px

def estimate_css_viewport_width_height(data: dict, theme: dict) -> tuple:
    return css_viewport.estimate_css_viewport_width_height(
        data, theme,
        measure_text_width=measure_text_width,
        row_cells=_row_cells,
        cell_text=cell_text,
    )


def _inject_wrap_gap_css(html: str, gap_px: int) -> str:
    return css_viewport._inject_wrap_gap_css(html, gap_px)

# CSS renderer helpers delegate to extracted module (wave4-b3)
_strip_alpha_from_css = css_renderer._strip_alpha_from_css
build_css_rows_html = css_renderer.build_css_rows_html

def generate_css_html(data: dict, theme: dict, transparent: bool = False, table_width_pct: int = None, tt: bool = False) -> str:
    return css_renderer.generate_css_html(
        data, theme,
        parse_width_px=_parse_width_px,
        transparent=transparent,
        table_width_pct=table_width_pct,
        tt=tt,
    )


# =============================================================================
# PIL RENDERER (FALLBACK)
# =============================================================================

from PIL import Image, ImageDraw, ImageFont
import re


# PIL blueprint helper delegates (wave4-b4)
def render_ascii_blueprint_pil(blueprint: dict, out_png_path: str, unit_px: int = 10):
    return pil_blueprint.render_ascii_blueprint_pil(blueprint, out_png_path, unit_px)

# PIL draw helpers delegate to extracted module (wave4-b4)
measure_text_width = pil_draw.measure_text_width
_fill_for_draw = pil_draw._fill_for_draw
draw_text_with_mixed_fonts = pil_draw.draw_text_with_mixed_fonts
_align_x = pil_draw._align_x
draw_text_aligned = pil_draw.draw_text_aligned

# PIL renderer delegates (wave4-b4)
PILStyle = pil_renderer.PILStyle

def render_pil(data: dict, theme: dict, custom_params: dict = None) -> Image.Image:
    return pil_renderer.render_pil(data, theme, custom_params)

# =============================================================================
# THEME LOADER (moved to zentable.input.theme)
# =============================================================================

# =============================================================================
# DATA NORMALISATION, SORT, PAGE (SKILL.md: --page, --sort, --asc, --desc)
# =============================================================================

# =============================================================================
# MAIN
# =============================================================================

def main():
    return run_cli_main(sys.modules[__name__])


if __name__ == "__main__":
    main()
