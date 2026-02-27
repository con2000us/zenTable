# ZenTable 規格文件

## 1. 概述

ZenTable 是一個跨平台表格渲染引擎，支援多種輸出模式和主題。

**設計目標：**
1. 無視 OpenClaw 運行環境（Linux、macOS、Windows、Docker）
2. 根據環境依賴智慧降級
3. 支援 pre-response 自動化處理

---

## 2. 輸出模式

| 模式 | 說明 | 依賴 | 輸出格式 |
|------|------|------|---------|
| `ascii` | 純文字表格 | 無 | .txt |
| `pil` | PIL 圖片 | PIL | .png |
| `css` | HTML+CSS 渲染 | Chrome | .png |
| `auto` | 自動降級 | 依環境 | .png |

**降級順序：**
```
css → pil → ascii
```

---

## 3. 主題結構

### 3.1 目錄結構

```
themes/
├── css/
│   ├── glass/
│   │   ├── template.json    # CSS 模板定義
│   │   └── asset/           # 圖片資源
│   │       ├── background.png
│   │       ├── border.png
│   │       └── logo.png
│   │
│   ├── cyberpunk/
│   │   ├── template.json
│   │   └── asset/
│   │
│   └── gradient/
│       ├── template.json
│       └── asset/
│
├── pil/
│   ├── glass/
│   │   └── template.json    # PIL 參數定義
│   │
│   ├── cyberpunk/
│   │   └── template.json
│   │
│   └── gradient/
│       └── template.json
│
└── text/
    ├── glass/
    │   └── template.json    # ASCII 風格定義
    │
    ├── simple/
    │   └── template.json
    │
    └── grid/
        └── template.json
```

### 3.2 主題命名規則

- **文字 ID**：小寫字母、數字、底線（`glass`, `cyberpunk`, `gradient_modern`）
- **資料夾**：與文字 ID 一致
- **格式**：每個主題資料夾內必須包含 `template.json`

### 3.3 主題參考

| 文字 ID | 名稱 | CSS | PIL | ASCII |
|---------|------|-----|-----|--------|
| `glass` | 毛玻璃 | ✅ | ✅ | ✅ |
| `cyberpunk` | 賽博龐克 | ✅ | ✅ | ✅ |
| `gradient` | 漸層現代 | ✅ | ✅ | ✅ |
| `minimal` | 極簡白 | ✅ | ✅ | ✅ |
| `simple` | 簡易分隔 | ❌ | ❌ | ✅ |
| `grid` | 方格 | ❌ | ❌ | ✅ |

---

## 4. 主題格式

### 4.1 CSS 主題 (template.json)

CSS 主題使用自由模板定義，支援自訂 HTML 結構。

```json
{
  "type": "css",
  "name": "Theme Name",
  "version": "1.0.0",
  "description": "主題說明",
  "author": "Author Name",
  "created": "2026-02-09",
  "updated": "2026-02-09",
  "tags": ["dark", "glass", "modern"],
  "template": {
    "html": "<div class=\"container\"><div class=\"header\">{{title}}</div><div class=\"table-wrapper\">{{table}}</div><div class=\"footer\">{{footer}}</div></div>",
    "table_html": "<table class=\"data-table\"><thead><tr>{{headers}}</tr></thead><tbody>{{rows}}</tbody></table>",
    "row_html": "<tr class=\"row {{row_class}}\">{{cells}}</tr>",
    "cell_html": "<td class=\"cell {{cell_class}}\">{{content}}</td>",
    "header_cell_html": "<th class=\"cell-header\">{{content}}</th>"
  },
  "styles": {
    "body": "margin: 0; padding: 30px; background: linear-gradient(135deg, #1a1a2e, #16213e, #0f3460); min-height: 100vh; display: flex; justify-content: center; align-items: flex-start;",
    ".container": "background: rgba(255,255,255,0.08); backdrop-filter: blur(12px); border-radius: 20px; border: 1px solid rgba(255,255,255,0.15); box-shadow: 0 20px 60px rgba(0,0,0,0.4); width: auto; min-width: 500px;",
    ".header": "padding: 24px 28px; font-size: 22px; font-weight: 700; color: #e94560; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.1);",
    ".data-table": "width: 100%; border-collapse: collapse;",
    ".cell-header": "padding: 16px 20px; font-weight: 600; color: #e94560; background: rgba(233,69,96,0.15);",
    ".row.tr_even": "background: rgba(255,255,255,0.03);",
    ".row.tr_odd": "background: transparent;",
    ".cell": "padding: 14px 20px; color: #ffffff;",
    ".footer": "padding: 14px 20px; font-size: 12px; color: rgba(255,255,255,0.4); text-align: center;"
  },
  "assets": {
    "background": "asset/background.png",
    "border": "asset/border.png",
    "logo": "asset/logo.png"
  }
}
```

**HTML 模板佔位符：**

| 佔位符 | 說明 |
|--------|------|
| `{{title}}` | 表格標題 |
| `{{table}}` | 完整表格 HTML |
| `{{footer}}` | 底部文字 |
| `{{headers}}` | 表頭 `<tr>` |
| `{{rows}}` | 所有資料列 |
| `{{row_class}}` | 奇偶列樣式類別 (`tr_even` / `tr_odd`) |
| `{{cell_class}}` | 儲存格樣式類別 |
| `{{content}}` | 儲存格內容 |

**自定義模板範例：**

```json
// 範例 1：標題在左側
{
  "template": {
    "html": "<div class=\"layout\"><aside class=\"title\">{{title}}</aside><main class=\"table\">{{table}}</main></div>"
  }
}

// 範例 2：標題在表格內
{
  "template": {
    "html": "<div class=\"card\"><table>{{table}}</table></div>",
    "table_html": "<thead><tr><th colspan=\"3\">{{title}}</th></tr></thead><tbody>{{rows}}</tbody>"
  }
}

// 範例 3：卡片式布局
{
  "template": {
    "html": "<div class=\"card\"><div class=\"card-header\">{{title}}</div><div class=\"card-body\">{{table}}</div><div class=\"card-footer\">{{footer}}</div></div>"
  }
}
```

**CSS 資源引用：**
```css
/* 在 styles 中使用 */
body {
    background: url("asset/background.png");
    border: url("asset/border.png") 10px solid;
}
```

### 4.2 PIL 主題 (template.json)

PIL 主題使用參數定義方式，支援豐富的視覺效果。

```json
{
  "type": "pil",
  "name": "Theme Name",
  "version": "1.0.0",
  "description": "主題說明",
  "author": "Author Name",
  "created": "2026-02-09",
  "updated": "2026-02-09",
  "tags": ["dark", "glass"],
  "params": {
    "bg_color": "#0a1929",
    "text_color": "#ffffff",
    "header_bg": "rgba(233,69,96,0.2)",
    "header_text": "#e94560",
    "alt_row_color": "rgba(255,255,255,0.05)",
    "border_color": "rgba(255,255,255,0.15)",
    "font_size": 16,
    "header_font_size": 18,
    "title_font_size": 22,
    "footer_font_size": 14,
    "padding": 20,
    "cell_padding": 12,
    "row_height": 44,
    "header_height": 52,
    "border_radius": 12,
    "border_width": 1,
    "font_family": null,
    "line_spacing": 1.4,
    "shadow_color": "#000000",
    "shadow_offset": 8,
    "shadow_blur": 20,
    "shadow_opacity": 0.3,
    "title_padding": 16,
    "footer_padding": 12,
    "cell_align": "left",
    "header_align": "left"
  },
  "styles": {
    "title": { "color": "#e94560", "bold": true, "underline": false },
    "header": { "bold": true, "italic": false },
    "cell": { "bold": false, "italic": false },
    "footer": { "color": "rgba(255,255,255,0.5)", "size_offset": -2 }
  },
  "assets": {
    "background": "asset/background.png",
    "border": "asset/border.png"
  },
  "watermark": {
    "enabled": true,
    "text": "Generated by ZenTable",
    "position": "bottom-right",
    "opacity": 0.5,
    "size_offset": -4
  }
}
```

**params 參數說明：**

| 參數 | 類型 | 說明 | 預設值 |
|------|------|------|--------|
| `bg_color` | 顏色 | 背景色 | `#0a1929` |
| `text_color` | 顏色 | 文字顏色 | `#ffffff` |
| `header_bg` | 顏色 | 表頭背景 | `rgba(233,69,96,0.2)` |
| `header_text` | 顏色 | 表頭文字 | `#e94560` |
| `alt_row_color` | 顏色 | 偶數列背景 | `rgba(255,255,255,0.05)` |
| `border_color` | 顏色 | 邊框顏色 | `rgba(255,255,255,0.15)` |
| `font_size` | 數字 | 內文字體大小 | 16 |
| `header_font_size` | 數字 | 表頭字體大小 | 18 |
| `title_font_size` | 數字 | 標題字體大小 | 22 |
| `footer_font_size` | 數字 | 底部字體大小 | 14 |
| `padding` | 數字 | 外邊距 | 20 |
| `cell_padding` | 數字 | 儲存格內距 | 12 |
| `row_height` | 數字 | 列高度 | 44 |
| `header_height` | 數字 | 表頭高度 | 52 |
| `border_radius` | 數字 | 圓角半徑 | 12 |
| `border_width` | 數字 | 邊框寬度 | 1 |
| `shadow_color` | 顏色 | 陰影顏色 | `#000000` |
| `shadow_offset` | 數字 | 陰影偏移 | 8 |
| `shadow_blur` | 數字 | 陰影模糊 | 20 |
| `shadow_opacity` | 數字 | 陰影透明度 | 0.3 |
| `title_padding` | 數字 | 標題內距 | 16 |
| `footer_padding` | 數字 | 底部內距 | 12 |
| `font_family` | 路徑 | 自定義字體 | null |
| `line_spacing` | 數字 | 行距 | 1.4 |

**watermark 參數說明：**

| 參數 | 說明 | 預設值 |
|------|------|--------|
| `enabled` | 啟用浮水印 | true |
| `text` | 浮水印文字 | Generated by ZenTable |
| `position` | 位置 | bottom-right |
| `opacity` | 透明度 | 0.5 |
| `size_offset` | 大小偏移 | -4 |

### 4.3 ASCII 主題 (template.json)

```json
{
  "type": "text",
  "name": "Theme Name",
  "version": "1.0.0",
  "description": "主題說明",
  "author": "Author Name",
  "created": "2026-02-09",
  "updated": "2026-02-09",
  "tags": ["dark", "glass"],
  "params": {
    "style": "double",
    "corner_top_left": "╔",
    "corner_top_right": "╗",
    "corner_bottom_left": "╚",
    "corner_bottom_right": "╝",
    "border_horizontal": "═",
    "border_vertical": "║",
    "header_separator": "╠",
    "row_separator": "╠",
    "footer_separator": "╠",
    "intersection": "╬",
    "padding": 2,
    "align": "center",
    "header_align": "center",
    "min_width": 80
  },
  "colors": {
    "header": "glass_pink",
    "text": "white",
    "border": "glass_blue"
  }
}
```

---

## 5. 指令參數

### 5.1 參數定義

| 參數 | 縮寫 | 說明 | 預設值 |
|------|------|------|-------|
| `--theme` | `-t` | 主題文字 ID 或路徑 | `default` |
| `--mode` | `-m` | 輸出模式 | `auto` |
| `--data` | `-d` | 資料檔案或內聯 JSON | 必填 |
| `--output` | `-o` | 輸出檔案 | `output` |
| `--rows-per-page` | `-r` | 每頁筆數 | 10 |
| `--page` | `-p` | 指定輸出頁數 | 全部 |
| `--max-pages` | `-M` | 最大輸出頁數 | 無限制 |
| `--resource-dir` | `-R` | 資源目錄 | 主題目錄 |
| `--env` | `-e` | 環境 | `auto` |
| `--chrome` | `-c` | Chrome 路徑 | auto |
| `--force` | `-f` | 強制模式 | false |
| `--verbose` | `-v` | 詳細輸出 | false |

### 5.2 使用範例

```bash
# 自動偵測環境
python3 zentable_render.py -d data.json -o out.png

# 指定主題
python3 zentable_render.py -t glass -d data.json -o out.png
python3 zentable_render.py -t themes/css/glass -d data.json -o out.png
python3 zentable_render.py -t themes/pil/glass -d data.json -o out.png
python3 zentable_render.py -t themes/text/glass -d data.json -o out.txt

# 指定模式
python3 zentable_render.py -m pil -t glass -d data.json -o out.png
python3 zentable_render.py -m css -t glass -d data.json -o out.png

# 分頁控制
python3 zentable_render.py -t glass -d data.json -o out.png --rows-per-page 15
python3 zentable_render.py -t glass -d data.json -o out.png --page 2
python3 zentable_render.py -t glass -d data.json -o out.png --max-pages 3

# 同時輸出 PNG + ASCII（同主檔名 .txt）
python3 zentable_render.py -t glass -d data.json -o out.png --both

# 自定義資源目錄
python3 zentable_render.py -t glass -d data.json -o out.png -R /path/to/resources
```

---

## 6. 資料格式

### 6.1 輸入格式 (JSON)

```json
{
  "title": "表格標題",
  "headers": ["欄位1", "欄位2", "欄位3"],
  "rows": [
    ["資料1-1", "資料1-2", "資料1-3"],
    ["資料2-1", "資料2-2", "資料2-3"]
  ],
  "footer": "底部文字（可選）"
}
```

### 6.2 URL 偵測

```python
URL_PATTERN = r"https?://[^\s]+"

def contains_url(data: dict) -> bool:
    """檢查是否包含 URL"""
    for row in data.get("rows", []):
        for cell in row:
            if re.search(URL_PATTERN, str(cell)):
                return True
    for header in data.get("headers", []):
        if re.search(URL_PATTERN, str(header)):
            return True
    return False
```

---

## 7. 使用時機 (pre-response)

### 7.1 自動化流程

```
用戶輸入
    ↓
table_detect.py 偵測
    ↓
needs_table = true?
    ├── 是 → 智慧判斷輸出
    │   ├── 包含 URL → 輸出 zentable + ascii
    │   └── 無 URL → 僅輸出 zentable
    └── 否 → 一般文字回覆
```

### 7.2 智慧判斷

```python
def smart_render(data: dict) -> list:
    """智慧渲染"""
    outputs = []
    
    # 1. 輸出 zentable（主要表格）
    if contains_url(data):
        # 2. 包含 URL 時，同時輸出 ascii
        ascii_output = render_ascii(data, theme="glass")
        outputs.append(("ascii", ascii_output))
    
    # 3. 輸出 zentable 圖片
    zentable_output = render_zentable(data, theme="glass")
    outputs.append(("zentable", zentable_output))
    
    return outputs
```

---

## 8. 環境偵測

### 8.1 偵測邏輯

```python
def detect_environment():
    """偵測可用渲染方式"""
    if check_chrome():
        return "css"
    elif check_pil():
        return "pil"
    else:
        return "ascii"
```

### 8.2 各平台路徑

| 平台 | Chrome 路徑 | xvfb 需求 |
|------|-------------|-----------|
| Linux | `/usr/bin/google-chrome` | 伺服器需要 |
| macOS | `/Applications/Google Chrome.app/...` | 不需要 |
| Windows | `C:\Program Files\Google\Chrome\...` | 不需要 |

---

## 9. 檔案結構

```
/var/www/html/zenTable/
├── scripts/                 # Python 入口
│   ├── zentable_renderer.py       # 主腳本（CSS/PIL/ASCII）
│   └── table_detect.py       # 表格偵測
├── themes/                   # 主題目錄
│   ├── css/
│   │   ├── glass/
│   │   │   ├── template.json
│   │   │   └── asset/
│   │   ├── cyberpunk/
│   │   │   ├── template.json
│   │   │   └── asset/
│   │   └── gradient/
│   │       ├── template.json
│   │       └── asset/
│   ├── pil/
│   │   ├── glass/
│   │   │   └── template.json
│   │   ├── cyberpunk/
│   │   │   └── template.json
│   │   └── gradient/
│   │       └── template.json
│   └── text/
│       ├── glass/
│       │   └── template.json
│       ├── simple/
│       │   └── template.json
│       └── grid/
│           └── template.json
├── INTEGRATION.md           # 整合範例
├── SPECIFICATION.md        # 本文件
├── README.md               # 說明文件
└── SKILL.md               # Skill 文件
```

---

## 10. 版本歷史

| 版本 | 日期 | 變更 |
|------|------|------|
| 1.0.0 | 2026-02-09 | 初始版本 |
| 1.1.0 | 2026-02-09 | CSS 主題改用 template.json，自由模板定義 |
| 1.2.0 | 2026-02-09 | PIL 主題參數完整化，新增浮水印、陰影效果 |

---

## 11. 參考

- **zenTable**：表格渲染引擎
- **zentable**：表格渲染後的圖片輸出
- **zentable化**：將表格轉為 zentable 圖片的過程
