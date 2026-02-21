# Zeble - Zen Table Output

讓表格文字有禪意的風格輸出

## 功能特性

- 🎨 **混合字體渲染**
  - 中文 → Noto Sans CJK
  - Emoji → Symbola（彩色符號）
  - 自動垂直對齊

- 🔧 **Emoji 替換與狀態**
  - 圓形/方塊 Emoji（🟢🟡🔴 等）替換為文字（(綠)(黃)(紅)）
  - 狀態指示器（依欄位名自動偵測上色）為可選增強，尚未實作

- 📊 **主題系統**
  - 深色、淺色、賽博龐克、森林、海洋、日落、玫瑰、午夜

## 程式入口與主題來源

- **zeble_render.py**（對外主要入口）：測試頁與 API 透過 `gentable_css.php` / `gentable_pil.php` / `gentable_ascii.php` 呼叫。支援三種模式：**CSS + Chrome**、**PIL**、**ASCII**；主題來自目錄 `themes/css/`、`themes/pil/`、`themes/text/`（每主題一資料夾，內含 `template.json`）。參數詳見下方「zeble_render.py（API / 測試頁用）」；`gentable_pil.php` 會傳 `--params` 覆蓋主題參數。輸入可為「陣列 of 物件」或 `{ "headers": [], "rows": [] }`。
- **zeble.py**（CLI 用）：本機指令列使用，內建 8 主題、`--page`、`--sort`、`--asc`/`--desc`，並支援 JSON 內 `bg_image`、`border_image` 自訂背景與邊框圖。主題為程式內建，不讀取 `themes/` 目錄。

主題目錄與 SKILL.md 表列對應：`themes/css/` 下含 dark、light、cyberpunk、forest、ocean、sunset、rose、midnight、glass、gradient_modern、neon_cyber 等。

## 使用方式

**zeble_render.py（建議，用於 API / 測試頁）：**
```bash
# CSS 模式（預設）
python3 zeble_render.py <input.json> <output.png> --theme-name dark [--transparent]

# PIL 模式
python3 zeble_render.py <input.json> <output.png> --force-pil --theme-name dark [--page 1] [--sort 欄位] [--asc|--desc]

# ASCII 模式（輸出到檔案）
python3 zeble_render.py <input.json> dummy.png --force-ascii --output-ascii output.txt --theme-name glass
```

**zeble.py（CLI，內建主題與背景圖）：**
```bash
python3 zeble.py <input.json> <output.png> [options]
```

## 參數

### zeble_render.py（API / 測試頁用）

| 參數 | 說明 | 預設 |
|------|------|------|
| `--theme-name <名稱>` | 主題名稱（dark, light, cyberpunk, glass...） | default_dark |
| `--theme <路徑>` | 主題 JSON 檔案路徑（覆蓋 --theme-name） | |
| `--force-css` | 強制 CSS + Chrome 渲染 | |
| `--force-pil` | 強制 PIL 渲染 | |
| `--force-ascii` | 強制 ASCII 文字輸出 | |
| `--output-ascii <路徑>` | ASCII 輸出到指定檔案（搭配 --force-ascii） | stdout |
| `--transparent` | 產出透空背景 PNG（僅 CSS 模式） | |
| `--params <JSON>` | 自訂參數覆蓋（gentable_pil 會傳） | |
| `--page N` | 第 N 頁（每頁 15 列） | 1 |
| `--sort <欄位>` | 依欄位排序 | |
| `--asc` | 升序 | |
| `--desc` | 降序 | |

### zeble.py（CLI 用，內建主題）

| 參數 | 說明 | 預設 |
|------|------|------|
| `--dark` | 深色主題 | ✅ |
| `--light` | 淺色主題 | |
| `--cyberpunk` | 賽博龐克 | |
| `--forest` | 森林 | |
| `--ocean` | 海洋 | |
| `--sunset` | 日落 | |
| `--rose` | 玫瑰 | |
| `--midnight` | 午夜 | |
| `--page N` | 第 N 頁 | 1 |
| `--sort <欄位>` | 排序欄位 | |
| `--asc` | 升序 | |
| `--desc` | 降序 | |

## 輸入格式

```json
[
  {"名稱": "伺服器 A", "狀態": "運行中", "延遲": "15ms"},
  {"名稱": "伺服器 B", "狀態": "維護", "延遲": "--"}
]
```

## 範例

```bash
# 基本使用
python3 zeble.py data.json output.png

# 深色主題 + 第 2 頁
python3 zeble.py data.json out.png --dark --page 2

# 按延遲欄位排序（升序）
python3 zeble.py data.json out.png --sort 延遲 --asc
```

## 主題預覽

| 主題 | 背景 | 文字 | 標題背景 |
|------|------|------|----------|
| dark | #1a1a2e | #ffffff | #0f3460 |
| light | #f8f9fa | #212529 | #e9ecef |
| cyberpunk | #0d0221 | #00ff9f | #ff00ff |
| forest | #1a2f1a | #90ee90 | #2d5a2d |
| ocean | #0a1929 | #64b5f6 | #1565c0 |
| sunset | #2d1f1f | #ffcc80 | #bf360c |
| rose | #2f1a1a | #f8bbd9 | #c2185b |
| midnight | #0f0f23 | #b0a0ff | #2a2a4a |

## Emoji 替換

| 原始 | 替換為 | 原因 |
|------|--------|------|
| 🟢 | (綠) | 圓形顏色 |
| 🟡 | (黃) | 圓形顏色 |
| 🔴 | (紅) | 圓形顏色 |
| 🔵 | (藍) | 圓形顏色 |
| 🟤 | (棕) | 圓形顏色 |
| 🟣 | (紫) | 圓形顏色 |
| 🟠 | (橙) | 圓形顏色 |
| ⚫ | (黑) | 圓形顏色 |
| ⚪ | (白) | 圓形顏色 |
| 🟧 | (橘) | 圓形顏色 |
| 🟦 | (天藍) | 圓形顏色 |
| 🟪 | (深紫) | 圓形顏色 |
| 🟫 | (褐) | 圓形顏色 |
| ☒ | (X) | 方框叉號 |

其他 Emoji 正常顯示（✅✓✗✖✔🎉🚀💡🔥🇹🇼🇯🇵🇺🇸 等）。

## 檔案位置

```
/var/www/html/zenTable/
├── scripts/
│   ├── zeble_render.py   # 主渲染程式（CSS/PIL/ASCII，供 API 與測試頁呼叫）
│   ├── zeble.py          # 舊版 CLI（若仍需要）
│   └── table_detect.py   # 表格偵測
├── themes/               # 主題目錄（css/<名稱>/template.json、pil/、text/）
│   ├── css/       # dark, light, cyberpunk, forest, ocean, sunset, rose, midnight, glass, ...
│   ├── pil/
│   └── text/
├── THEME_STRUCTURE.md # 主題目錄規則
├── README.md      # 詳細文件
└── test_*.json   # 測試數據
```

## 測試網頁

主測試頁（如 zenTable 的 `index.html`）透過 **theme_api.php** 取得主題列表與內容，並透過 **gentable_css.php / gentable_pil.php / gentable_ascii.php** 呼叫本 skill 的 `zeble_render.py` 進行渲染，可測試主題、模式（CSS/PIL/ASCII）、分頁與排序（若測試頁有暴露對應欄位）。
