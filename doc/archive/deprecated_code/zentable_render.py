#!/usr/bin/env python3
"""
ZenTable Renderer - Flexible HTML/CSS rendering engine

支援兩種渲染模式:
1. CSS + Chrome - 效果最好，支援完整 CSS
2. PIL - 零依賴 fallback，支援 CSS 子集

使用方式:
    python3 zentable_render.py [OPTIONS]

選項:
    -e, --env ENVIRONMENT     環境: linux, macos, windows, auto (預設: auto)
    -c, --chrome PATH         Chrome 路徑 (預設: auto-detect)
    -t, --template TEMPLATE   CSS 範本檔案或內聯 CSS
    -d, --data DATA           JSON 資料檔案或內聯 JSON
    -o, --output OUTPUT       輸出 PNG 檔案
    -f, --force-pil           強制使用 PIL fallback
    -v, --verbose             詳細輸出
    --help                    顯示說明

PIL 支援的 CSS 屬性:
    background, background-color → 背景色
    color → 文字顏色
    font-size → 字型大小
    padding → 內距

範例:
    # CSS 模式 (完整 CSS)
    python3 zentable_render.py -t theme.css -d data.json -o out.png

    # PIL 模式 (CSS 子集)
    python3 zentable_render.py -f -t pil_theme.css -d data.json -o out.png

    # 內聯 CSS 和資料
    python3 zentable_render.py -t "body { background: red; }" -d '{"title":"Test"}' -o out.png

PIL 範本範例 (pil_theme.css):
    body { background: #1a1a2e; padding: 20px; }
    container { background: #1a1a2e; border-radius: 12px; }
    title { background: #0f3460; color: #e94560; font-size: 20px; }
    th { background: #0f3460; color: #e94560; padding: 12px; }
    tr_even { background: #16213e; }
    tr_odd { background: #1a1a2e; }
    td { color: #ffffff; padding: 10px; font-size: 14px; }
"""

import json
import sys
import os
import re
import subprocess
import platform
import argparse
from dataclasses import dataclass
from typing import Optional, Dict, Any, Callable
from pathlib import Path

# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class RenderConfig:
    """渲染配置"""
    env: str = "auto"                    # 環境: linux, macos, windows, auto
    chrome_path: Optional[str] = None   # Chrome 路徑
    template: str = ""                   # 範本 (檔案路徑或內聯 CSS)
    data: str = ""                       # 資料 (JSON 檔案或內聯 JSON)
    output: str = "output.png"           # 輸出檔案
    force_pil: bool = False              # 強制 PIL
    resource_dir: str = None             # 資源目錄 (圖片等)
    verbose: bool = False                # 詳細輸出

# =============================================================================
# TEMPLATE ENGINE (Lightweight)
# =============================================================================

class TemplateEngine:
    """輕量範本引擎"""
    
    def __init__(self):
        self.helpers: Dict[str, Callable] = {}
        self.register_default_helpers()
    
    def register_helper(self, name: str, func: Callable):
        self.helpers[name] = func
    
    def register_default_helpers(self):
        self.helpers['upper'] = lambda x: str(x).upper()
        self.helpers['lower'] = lambda x: str(x).lower()
        self.helpers['currency'] = lambda x: f"${x}"
        self.helpers['percent'] = lambda x: f"{x}%"
        self.helpers['even'] = lambda x: x % 2 == 0
        self.helpers['odd'] = lambda x: x % 2 == 1
    
    def render(self, template: str, context: Dict) -> str:
        """渲染範本"""
        result = template
        result = self._render_conditionals(result, context)
        result = self._render_loops(result, context)
        result = self._render_variables(result, context)
        return result
    
    def _render_variables(self, template: str, context: Dict) -> str:
        def replace(match):
            var = match.group(1).strip()
            keys = var.split('.')
            value = context
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k, '')
            return str(value) if value else ''
        return re.sub(r'\{\{([^{}][^{}]*?)\}\}', replace, template)
    
    def _render_conditionals(self, template: str, context: Dict) -> str:
        def process(match):
            cond = match.group(1).strip()
            content = match.group(2)
            if '&&' in cond:
                return content if all(self._check(c.strip(), context) for c in cond.split('&&')) else ''
            return content if self._check(cond, context) else ''
        pattern = r'\{\{#if\s+([^}]+)\}\}(.*?)\{\{/if\}\}'
        while re.search(pattern, template):
            template = re.sub(pattern, process, template, flags=re.DOTALL)
        return template
    
    def _check(self, cond: str, context: Dict) -> bool:
        for op in ['==', '!=']:
            if op in cond:
                a, b = cond.split(op)
                return self._eval(a.strip(), context) == self._eval(b.strip(), context)
        return bool(self._eval(cond, context))
    
    def _eval(self, val: str, context: Dict) -> Any:
        val = val.strip()
        if val.startswith('"') and val.endswith('"'):
            return val[1:-1]
        try:
            return float(val) if '.' in val else int(val)
        except:
            pass
        return context.get(val, '')
    
    def _render_loops(self, template: str, context: Dict) -> str:
        def process(match):
            list_name = match.group(1).strip()
            content = match.group(2)
            lst = self._eval(list_name, context)
            if not isinstance(lst, (list, tuple)):
                return ''
            results = []
            for idx, item in enumerate(lst):
                ctx = context.copy()
                ctx['@index'] = idx
                ctx['@even'] = idx % 2 == 0
                ctx['@odd'] = idx % 2 == 1
                if isinstance(item, dict):
                    for k, v in item.items():
                        ctx[f'$row.{k}'] = v
                ctx['$row'] = item
                item_html = self._render_variables(content, ctx)
                results.append(item_html)
            return ''.join(results)
        pattern = r'\{\{#each\s+([^{}]+)\}\}(.*?)\{\{/each\}\}'
        while re.search(pattern, template):
            template = re.sub(pattern, process, template, flags=re.DOTALL)
        return template

# =============================================================================
# ENVIRONMENT DETECTION
# =============================================================================

class EnvironmentDetector:
    """環境偵測"""
    
    @staticmethod
    def detect() -> str:
        """偵測當前環境"""
        system = platform.system().lower()
        if system in ['darwin', 'linux', 'windows']:
            return system
        return 'linux'  # 預設
    
    @staticmethod
    def find_chrome(env: str = "auto") -> Optional[str]:
        """尋找 Chrome"""
        if env == "auto":
            env = EnvironmentDetector.detect()
        
        chrome_paths = {
            'darwin': [
                '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                '/usr/bin/google-chrome',
            ],
            'linux': [
                '/usr/bin/google-chrome',
                '/usr/bin/chromium',
                '/usr/bin/chromium-browser',
            ],
            'windows': [
                'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
                'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
            ]
        }
        
        paths = chrome_paths.get(env, [])
        for path in paths:
            if os.path.exists(path):
                return path
        
        # 嘗試 which
        try:
            result = subprocess.run(['which', 'google-chrome'], capture_output=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        
        return None
    
    @staticmethod
    def need_xvfb(env: str = "auto") -> bool:
        """是否需要 xvfb (無顯示環境)"""
        if env == "auto":
            env = EnvironmentDetector.detect()
        
        if env == 'linux':
            # 檢查是否有 DISPLAY
            return not os.environ.get('DISPLAY')
        return False

# =============================================================================
# RENDERERS
# =============================================================================

class CSSRenderer:
    """CSS + Chrome 渲染器"""
    
    # 專案根目錄（本專案不再依賴外部 /opt skill 目錄）
    SKILL_DIR = "/var/www/html/zenTable"
    
    def __init__(self, config: RenderConfig):
        self.config = config
        self.engine = TemplateEngine()
    
    def render(self, html: str, output_path: str) -> bool:
        """使用 Chrome 渲染"""
        # 確定資源目錄
        resource_dir = None
        
        # 如果範本是檔案，相對於該檔案所在目錄
        if self.config.template and os.path.exists(self.config.template):
            resource_dir = os.path.dirname(self.config.template)
        else:
            # 預設使用 skill 目錄
            resource_dir = self.SKILL_DIR
        
        # 處理 HTML 中的資源路徑
        html = resolve_resource_path_in_html(html, resource_dir)
        
        # 寫入暫存 HTML
        html_file = output_path.replace('.png', '_temp.html')
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        # 構建命令
        env = self.config.env if self.config.env != 'auto' else EnvironmentDetector.detect()
        chrome_path = self.config.chrome_path or EnvironmentDetector.find_chrome(env)
        
        if not chrome_path:
            raise RuntimeError("未找到 Chrome")
        
        # 基礎指令
        cmd = [chrome_path, '--headless']
        
        # xvfb (Linux 無顯示時)
        if EnvironmentDetector.need_xvfb(env):
            cmd = ['xvfb-run', '-a'] + cmd
        
        # 參數
        cmd.extend([
            f'--screenshot={output_path}',
            '--hide-scrollbars',
            '--disable-gpu',
            '--virtual-time-budget=3000',
            f'file://{html_file}'
        ])
        
        # 執行
        if self.config.verbose:
            print(f"執行指令: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True)
        
        # 清理
        if os.path.exists(html_file):
            os.remove(html_file)
        
        return result.returncode == 0 and os.path.exists(output_path)


class PILRenderer:
    """PIL 純 Python 渲染器 (Fallback)"""
    
    # 支援的 CSS 屬性映射
    CSS_TO_PIL = {
        'background': 'bg_color',
        'background-color': 'bg_color',
        'color': 'text_color',
        'font-size': 'font_size',
        'padding': 'padding',
        'font-weight': 'font_weight',
    }
    
    # 預設值
    DEFAULTS = {
        'bg_color': '#1a1a2e',
        'text_color': '#ffffff',
        'header_bg': '#0f3460',
        'header_text': '#e94560',
        'alt_row_color': '#16213e',
        'border_color': '#4a5568',
        'font_size': 16,
        'header_font_size': 18,
        'title_font_size': 22,
        'padding': 10,
        'cell_padding': 10,
        'row_height': 40,
        'header_height': 50,
        'border_radius': 8,
        'font_family': None,
        'line_spacing': 1.4,
        'header_padding': 14,
        'border_width': 1,
        'shadow_color': '#000000',
        'shadow_offset': 8,
        'shadow_blur': 20,
        'shadow_opacity': 0.3,
        'title_padding': 16,
        'footer_padding': 12,
        'cell_align': 'left',
        'header_align': 'left',
    }
    
    def __init__(self, config: RenderConfig):
        self.config = config
    
    def parse_css_template(self, css: str) -> dict:
        """解析 CSS 範本為 PIL 參數"""
        styles = {}
        
        # 解析各元素的 CSS
        element_pattern = r'(\w+)\s*\{([^}]+)\}'
        for match in re.finditer(element_pattern, css):
            element = match.group(1).strip()
            properties = match.group(2)
            
            element_styles = {}
            for prop_match in re.finditer(r'([^:]+):\s*([^;]+);', properties):
                prop = prop_match.group(1).strip()
                value = prop_match.group(2).strip()
                element_styles[prop] = value
            
            # 映射到 PIL 參數
            pil_params = {}
            for css_prop, pil_prop in self.CSS_TO_PIL.items():
                if css_prop in element_styles:
                    pil_params[pil_prop] = element_styles[css_prop]
            
            styles[element] = pil_params
        
        # 合併預設值
        result = self.DEFAULTS.copy()
        for element, params in styles.items():
            result.update({f'{element}_{k}': v for k, v in params.items()})
        
        return result
    
    def load_template_params(self, template_path: str = None) -> dict:
        """從 template.json 載入參數"""
        template = template_path or self.config.template
        
        if not template:
            return self.DEFAULTS.copy()
        
        # 檢查是否為 template.json 格式
        if template.endswith('.json') or os.path.isdir(template):
            if os.path.isdir(template):
                template = os.path.join(template, 'template.json')
            
            if os.path.exists(template):
                try:
                    with open(template, 'r', encoding='utf-8') as f:
                        template_data = json.load(f)
                    
                    params = template_data.get('params', {})
                    
                    # 合併預設值
                    result = self.DEFAULTS.copy()
                    result.update(params)
                    
                    return result
                except Exception as e:
                    print(f"⚠️  載入模板失敗: {e}")
                    return self.DEFAULTS.copy()
        
        # 舊格式：CSS 範本
        return self.parse_css_template(template)
    
    def render(self, data: dict, output_path: str) -> bool:
        """使用 PIL 渲染"""
        from PIL import Image, ImageDraw, ImageFont
        
        headers = data.get("headers", [])
        rows = data.get("rows", [])
        title = data.get("title", "")
        footer = data.get("footer", "")
        
        # 載入參數
        params = self.load_template_params()
        
        # 提取參數
        bg_color = params.get('bg_color', '#1a1a2e')
        text_color = params.get('text_color', '#ffffff')
        header_bg = params.get('header_bg', '#0f3460')
        header_text = params.get('header_text', '#e94560')
        alt_row_color = params.get('alt_row_color', '#16213e')
        border_color = params.get('border_color', '#4a5568')
        font_size = int(params.get('font_size', 16))
        header_font_size = int(params.get('header_font_size', 18))
        title_font_size = int(params.get('title_font_size', 22))
        padding = int(params.get('padding', 10))
        cell_padding = int(params.get('cell_padding', 10))
        row_height = int(params.get('row_height', 40))
        header_height = int(params.get('header_height', 50))
        border_radius = int(params.get('border_radius', 8))
        font_family = params.get('font_family')
        shadow_color = params.get('shadow_color', '#000000')
        shadow_offset = int(params.get('shadow_offset', 8))
        shadow_blur = int(params.get('shadow_blur', 20))
        shadow_opacity = float(params.get('shadow_opacity', 0.3))
        title_padding = int(params.get('title_padding', 16))
        footer_padding = int(params.get('footer_padding', 12))
        footer_font_size = int(params.get('footer_font_size', font_size))
        
        # 計算尺寸
        col_count = len(headers) if headers else 1
        row_count = len(rows)
        
        cell_width = max(100, max(len(str(h)) for h in headers) * 12 if headers else 100)
        for row in rows:
            for i, cell in enumerate(row):
                if i < col_count:
                    cell_width = max(cell_width, len(str(cell)) * 12)
        cell_width += cell_padding * 2
        
        width = padding * 2 + col_count * cell_width
        title_height = title_font_size + title_padding * 2 if title else 0
        footer_height = footer_font_size if footer else 0
        height = padding * 2 + title_height + header_height + row_count * row_height + footer_height + padding
        
        # 建立圖片
        img = Image.new('RGB', (width, height), self._hex_rgb(bg_color))
        draw = ImageDraw.Draw(img)
        
        # 嘗試載入中文字體
        try:
            font_paths = [
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/noto/NotoSansCJK-Regular.ttc",
            ]
            font = None
            for fp in font_paths:
                if os.path.exists(fp):
                    font = ImageFont.truetype(fp, font_size)
                    break
            
            if font is None:
                font = ImageFont.load_default()
            
            header_font = ImageFont.truetype(fp, header_font_size) if font != ImageFont.load_default() else font
            title_font = ImageFont.truetype(fp, title_font_size) if font != ImageFont.load_default() else font
        except Exception:
            font = ImageFont.load_default()
            header_font = font
            title_font = font
        
        y = padding
        
        # 陰影
        if shadow_offset > 0:
            shadow_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow_img)
            shadow_draw.rounded_rectangle(
                [padding, y, width-padding, height-padding],
                radius=border_radius,
                fill=self._hex_rgba(shadow_color, shadow_opacity)
            )
            # 簡化陰影
            draw.rectangle(
                [padding + shadow_offset, y + shadow_offset, width - padding + shadow_offset, height - padding + shadow_offset],
                fill=self._hex_rgb(shadow_color)
            )
        
        # 背景圓角
        draw.rounded_rectangle(
            [padding, y, width-padding, height-padding],
            radius=border_radius,
            fill=self._hex_rgb(bg_color),
            outline=self._hex_rgb(border_color),
            width=1
        )
        
        # 標題
        if title:
            title_y = y + padding
            title_text = self._replace_emoji(str(title))
            draw.text((padding + cell_padding, title_y + title_padding), title_text, font=title_font, fill=self._hex_rgb(header_text))
            y += title_height + padding
        
        # 表頭背景
        header_y = y
        draw.rounded_rectangle(
            [padding, header_y, width-padding, header_y + header_height],
            radius=border_radius if row_count == 0 else 0,
            fill=self._hex_rgb(header_bg)
        )
        
        for i, h in enumerate(headers):
            x = padding + i * cell_width + cell_padding
            header_text = self._replace_emoji(str(h))
            draw.text((x, header_y + (header_height - header_font_size) // 2), header_text, font=header_font, fill=self._hex_rgb(header_text))
        y += header_height
        
        # 資料列
        for idx, row in enumerate(rows):
            bg = alt_row_color if idx % 2 == 0 else bg_color
            draw.rectangle([padding, y, width-padding, y+row_height], fill=self._hex_rgb(bg))
            
            for i, cell in enumerate(row):
                if i < col_count:
                    x = padding + i * cell_width + cell_padding
                    cell_text = self._replace_emoji(str(cell))
                    draw.text((x, y + (row_height - font_size) // 2), cell_text, font=font, fill=self._hex_rgb(text_color))
            y += row_height
        
        # 底部
        if footer:
            footer_y = height - padding - footer_padding - footer_font_size
            footer_text = self._replace_emoji(str(footer))
            draw.text((padding + cell_padding, footer_y), footer_text, font=font, fill=self._hex_rgb(text_color))
        
        img.save(output_path, quality=95)
        return os.path.exists(output_path)
    
    def _hex_rgb(self, hex_color: str):
        """轉換顏色"""
        if not hex_color:
            return (30, 30, 60)
        hex_color = hex_color.strip()
        if hex_color.startswith('rgba'):
            return (30, 30, 60)
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join(c*2 for c in hex_color)
        try:
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        except:
            return (30, 30, 60)
    
    def _hex_rgba(self, hex_color: str, alpha: float):
        """轉換 RGBA"""
        rgb = self._hex_rgb(hex_color)
        return (rgb[0], rgb[1], rgb[2], int(255 * alpha))

    def _replace_emoji(self, text: str) -> str:
        """替換 Emoji 為文字（因為 PIL 預設字體不支援）"""
        emoji_map = {
            '✅': '[OK]',
            '❌': '[X]',
            '⚠️': '[!]',
            '⚡': '[!]',
            '🔥': '[HOT]',
            '💀': '[DEAD]',
            '⭐': '[*]',
            '📌': '[PIN]',
            '🔒': '[LOCK]',
            '🔓': '[UNLOCK]',
            '➜': '->',
            '→': '->',
            '✔': '[OK]',
            '✖': '[X]',
            '✓': '[OK]',
        }
        for emoji, replacement in emoji_map.items():
            text = text.replace(emoji, replacement)
        return text

# =============================================================================
# MAIN
# =============================================================================

def parse_args():
    """解析參數"""
    parser = argparse.ArgumentParser(
        description="ZenTable Renderer - Flexible HTML/CSS rendering",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  %(prog)s -t template.html -d data.json -o out.png
  %(prog)s -t "body { bg: red }" -d '{"title":"Hi"}' -o out.png
  %(prog)s -f -d data.json -o out.png  # 強制 PIL
        """
    )
    
    parser.add_argument('-e', '--env', default='auto', 
                        choices=['auto', 'linux', 'macos', 'windows'],
                        help='環境 (預設: auto)')
    parser.add_argument('-c', '--chrome', default=None,
                        help='Chrome 路徑 (預設: auto)')
    parser.add_argument('-t', '--template', default='',
                        help='範本檔案或 CSS 內容')
    parser.add_argument('-d', '--data', default='',
                        help='資料 JSON 檔案或 JSON 字串')
    parser.add_argument('-o', '--output', default='output.png',
                        help='輸出 PNG 檔案 (預設: output.png)')
    parser.add_argument('-f', '--force-pil', action='store_true',
                        help='強制使用 PIL fallback')
    parser.add_argument('-r', '--resource-dir', default=None,
                        help='資源目錄 (相對路徑的基準) (預設: 範本所在目錄)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='詳細輸出')
    
    return parser.parse_args()

def load_template(path_or_content: str) -> str:
    """載入範本"""
    if os.path.exists(path_or_content):
        with open(path_or_content, 'r', encoding='utf-8') as f:
            return f.read()
    return path_or_content

def load_data(path_or_json: str) -> dict:
    """載入資料"""
    if os.path.exists(path_or_json):
        with open(path_or_json, 'r', encoding='utf-8') as f:
            return json.load(f)
    return json.loads(path_or_json)

def resolve_resource_path(css: str, resource_dir: str = None) -> str:
    """
    解析 CSS 中的資源路徑
    
    支援:
    - 相對路徑 (images/bg.png) → 轉為絕對路徑
    - 絕對路徑 (/opt/...) → 保持不變
    - URL (http://...) → 保持不變
    - data:URI → 保持不變
    """
    if not resource_dir:
        return css
    
    def replace_url(match):
        url_content = match.group(1)
        url_content = url_content.strip()
        
        # 跳过已完成的 URL（可能有嵌套）
        if url_content.startswith('data:') or url_content.startswith('http://') or url_content.startswith('https://'):
            return match.group(0)
        
        # 去除引號
        if url_content.startswith('"') and url_content.endswith('"'):
            url_content = url_content[1:-1]
        elif url_content.startswith("'") and url_content.endswith("'"):
            url_content = url_content[1:-1]
        
        # 只處理相對路徑
        if not url_content.startswith('/') and not url_content.startswith('http'):
            abs_path = os.path.join(resource_dir, url_content)
            if os.path.exists(abs_path):
                return f'url("file://{abs_path}")'
        
        return match.group(0)
    
    # 處理 url() 語法
    result = re.sub(r'url\s*\(\s*([^)]+)\s*\)', replace_url, css)
    return result

def resolve_resource_path_in_html(html: str, resource_dir: str) -> str:
    """
    解析 HTML 中的資源路徑
    
    處理:
    - <img src="...">
    - <div style="background: url(...)">
    """
    def replace_img_src(match):
        tag = match.group(0)
        # 提取 src 屬性
        src_match = re.search(r'src\s*=\s*["\']([^"\']+)["\']', tag)
        if src_match:
            src = src_match.group(1)
            # 只處理相對路徑
            if not src.startswith('/') and not src.startswith('http') and not src.startswith('data:'):
                abs_path = os.path.join(resource_dir, src)
                if os.path.exists(abs_path):
                    tag = tag.replace(f'src="{src}"', f'src="file://{abs_path}"')
                    tag = tag.replace(f"src='{src}'", f"src='file://{abs_path}'")
        return tag
    
    def replace_style_url(match):
        style = match.group(1)
        # 處理 style 中的 url()
        def replace_url_in_style(url_match):
            url = url_match.group(1).strip()
            if url.startswith('"') and url.endswith('"'):
                url = url[1:-1]
            elif url.startswith("'") and url.endswith("'"):
                url = url[1:-1]
            
            if not url.startswith('/') and not url.startswith('http') and not url.startswith('data:'):
                abs_path = os.path.join(resource_dir, url)
                if os.path.exists(abs_path):
                    return f'url("file://{abs_path}")'
            return url_match.group(0)
        
        return 'style="' + re.sub(r'url\s*\(\s*([^)]+)\s*\)', replace_url_in_style, style) + '"'
    
    # 處理 <img> 標籤
    html = re.sub(r'<img[^>]*>', replace_img_src, html)
    
    # 處理 style 属性中的 url()
    html = re.sub(r'style="([^"]*)"', replace_style_url, html)
    html = re.sub(r"style='([^']*)'", replace_style_url, html)
    
    return html

def load_template_json(template_path: str) -> dict:
    """載入 template.json 格式的範本"""
    with open(template_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def build_html_from_template(template_data: dict, data: dict, resource_dir: str = None) -> str:
    """從 template.json 格式構建 HTML"""
    
    # 提取模板結構
    html_template = template_data.get('template', {}).get('html', DEFAULT_HTML)
    table_html = template_data.get('template', {}).get('table_html', DEFAULT_TABLE_HTML)
    row_html = template_data.get('template', {}).get('row_html', DEFAULT_ROW_HTML)
    cell_html = template_data.get('template', {}).get('cell_html', DEFAULT_CELL_HTML)
    header_cell_html = template_data.get('template', {}).get('header_cell_html', DEFAULT_HEADER_CELL_HTML)
    
    # 提取樣式
    styles_raw = template_data.get('styles', {})
    
    # 解析資源路徑
    if resource_dir:
        for key, value in styles_raw.items():
            styles_raw[key] = resolve_resource_path(value, resource_dir)
    
    # 生成各部分 HTML
    headers = data.get('headers', [])
    rows = data.get('rows', [])
    title = data.get('title', '')
    footer = data.get('footer', '')
    
    # 生成 header cells
    headers_html = ''.join(header_cell_html.replace('{{content}}', str(h)) for h in headers)
    
    # 生成 data rows
    rows_html = ""
    for idx, row in enumerate(rows):
        row_class = "tr_even" if idx % 2 == 0 else "tr_odd"
        cells = ''.join(cell_html.replace('{{content}}', str(cell)).replace('{{cell_class}}', '') for cell in row)
        rows_html += row_html.replace('{{cells}}', cells).replace('{{row_class}}', row_class) + '\n'
    
    # 生成 table HTML
    table = table_html.replace('{{headers}}', headers_html).replace('{{rows}}', rows_html)
    
    # 生成完整 HTML
    html = html_template.replace('{{title}}', str(title)).replace('{{table}}', table).replace('{{footer}}', str(footer))
    
    # 生成 CSS
    css = '\n'.join(f'{k} {{ {v} }}' for k, v in styles_raw.items())
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>{css}</style>
</head>
<body>
{html}
</body>
</html>"""

# 預設 CSS（向後兼容）
DEFAULT_CSS = """
body { background: #1a1a2e; padding: 20px; }
container { background: #1a1a2e; border-radius: 12px; }
title { background: #0f3460; color: #e94560; padding: 16px; }
th { background: #0f3460; color: #e94560; padding: 12px; }
tr_even { background: #16213e; }
tr_odd { background: #1a1a2e; }
td { padding: 10px; color: #fff; }
"""

# 預設模板結構（向後兼容）
DEFAULT_HTML = '<div class="container"><div class="title">{{title}}</div><table>{{table}}</table></div>'
DEFAULT_TABLE_HTML = '<table class="data-table"><thead><tr>{{headers}}</tr></thead><tbody>{{rows}}</tbody></table>'
DEFAULT_ROW_HTML = '<tr class="row {{row_class}}">{{cells}}</tr>'
DEFAULT_CELL_HTML = '<td class="cell">{{content}}</td>'
DEFAULT_HEADER_CELL_HTML = '<th class="cell-header">{{content}}</th>'

def build_html(template: str, data: dict, resource_dir: str = None) -> str:
    """從 CSS 範本和資料構建 HTML"""
    engine = TemplateEngine()
    
    # 解析 CSS（並處理資源路徑）
    styles = {}
    for match in re.finditer(r'(\w+)\s*\{([^}]+)\}', template):
        key, value = match.groups()
        key = key.strip()
        value = value.strip()
        
        # 解析資源路徑
        if resource_dir:
            value = resolve_resource_path(value, resource_dir)
        
        styles[key] = value
    
    # 生成 HTML
    headers = data.get('headers', [])
    rows = data.get('rows', [])
    title = data.get('title', '')
    
    rows_html = ""
    for idx, row in enumerate(rows):
        row_class = "tr_even" if idx % 2 == 0 else "tr_odd"
        cells = ''.join(f'<td>{cell}</td>' for cell in row)
        rows_html += f'<tr class="{row_class}">{cells}</tr>\n'
    
    headers_html = ''.join(f'<th>{h}</th>' for h in headers)
    
    css = '\n'.join(f'.{k} {{ {v} }}' for k, v in styles.items())
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>{css}</style>
</head>
<body>
<div class="container">
{ f'<div class="title">{title}</div>' if title else '' }
<table>
{ f'<thead><tr>{headers_html}</tr></thead>' if headers else '' }
<tbody>{rows_html}</tbody>
</table>
</div>
</body>
</html>"""

def main():
    args = parse_args()
    
    config = RenderConfig(
        env=args.env,
        chrome_path=args.chrome,
        template=args.template,
        data=args.data,
        output=args.output,
        force_pil=args.force_pil,
        resource_dir=args.resource_dir,
        verbose=args.verbose
    )
    
    if args.verbose:
        print(f"環境: {config.env}")
        print(f"資源目錄: {config.resource_dir or '預設 (skill目錄)'}")
        print(f"輸出: {config.output}")
        print(f"PIL fallback: {config.force_pil}")
    
    # 載入資料
    try:
        data = load_data(config.data)
        if args.verbose:
            print(f"資料: {len(data.get('rows', []))} 列")
    except Exception as e:
        print(f"❌ 載入資料失敗: {e}")
        sys.exit(1)
    
    # 決定渲染方式
    use_pil = config.force_pil
    
    if not use_pil:
        # 檢查 Chrome
        env = config.env if config.env != 'auto' else EnvironmentDetector.detect()
        chrome = config.chrome_path or EnvironmentDetector.find_chrome(env)
        if not chrome:
            print("⚠️  未找到 Chrome，使用 PIL fallback")
            use_pil = True
        elif args.verbose:
            print(f"Chrome: {chrome}")
    
    # 渲染
    try:
        if use_pil:
            print("🖼️  使用 PIL 渲染...")
            renderer = PILRenderer(config)
            
            # 顯示載入的模板資訊
            if args.verbose and config.template:
                params = renderer.load_template_params()
                print(f"模板: {config.template}")
                print(f"背景: {params.get('bg_color')}")
                print(f"標題字體: {params.get('title_font_size')}px")
                print(f"圓角: {params.get('border_radius')}px")
            
            success = renderer.render(data, config.output)
        else:
            print("🖥️  使用 CSS + Chrome 渲染...")
            template_data = None
            
            # 檢查是否為 template.json 格式
            if config.template and os.path.exists(config.template):
                if config.template.endswith('.json') or os.path.isdir(config.template):
                    # template.json 或主題目錄
                    template_path = config.template
                    if os.path.isdir(template_path):
                        template_path = os.path.join(template_path, 'template.json')
                    
                    if os.path.exists(template_path):
                        template_data = load_template_json(template_path)
                        if args.verbose:
                            print(f"載入範本: {template_path}")
            
            if template_data:
                # 新格式 template.json
                resource_dir = config.resource_dir or os.path.dirname(template_path) if 'template_path' in dir() else None
                html = build_html_from_template(template_data, data, resource_dir)
            else:
                # 舊格式：直接 CSS
                template = load_template(config.template) if config.template else ""
                if not template:
                    template = DEFAULT_CSS
                html = build_html(template, data)
            
            renderer = CSSRenderer(config)
            success = renderer.render(html, config.output)
        
        if success:
            size = os.path.getsize(config.output)
            print(f"✅ 已保存: {config.output} ({size:,} bytes)")
        else:
            print("❌ 渲染失敗")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
