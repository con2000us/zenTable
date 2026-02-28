# Render 參數完整對照表

## 參數格式與選項速查

### PIL 模式
| 參數 | 格式 | 說明 |
|------|------|------|
| bg_color, text_color, header_bg... | #RRGGBB | 六位 hex 色碼 |
| cell_align, header_align | left \| center \| right | 對齊方式 |
| font_family | 字型名稱 | 如 Noto Sans TC，留空用預設 |
| font_size, header_font_size... | 8–48 | px 整數 |
| padding, cell_padding... | 0–80 | px 整數 |
| row_height, header_height | 20–120 | px 整數 |
| shadow_opacity, watermark_opacity | 0–1 | 小數 |

### ASCII 模式
| 參數 | 格式／選項 | 說明 |
|------|------------|------|
| style | single \| double \| grid \| markdown | 框線樣式 |
| padding | 0–6 | 儲存格內縮空格數 |
| align, header_align | left \| center \| right | 對齊方式 |

### 進階 Render（--width, --scale, --fill-width, --bg）
| 參數 | 格式 | 說明 |
|------|------|------|
| --width | 正整數 | viewport/輸出寬度 px |
| --text-scale | smallest \| small \| auto \| large \| largest \| 浮點數 | （僅 CSS）文字/間距縮放倍率；預設 auto（依 --width 自動放大） |
| --text-scale-max | 浮點數 | （僅 CSS, auto）自動縮放上限；預設 2.5 |
| --scale | 0.1–5.0 | 輸出尺寸倍數 |
| --fill-width | background \| container \| scale \| no-shrink | 搭配 --width |
| --bg | transparent \| theme \| #RRGGBB | 背景（僅 CSS） |

### OpenClaw Custom Skill：table_renderer.py（額外參數）

下列參數同時適用於 `table_renderer.py`（純 CSS + Chrome headless 截圖）與 `scripts/zentable_render.py` 的 CSS 模式（`--force-css` / Chrome 可用時）：

| 參數 | 格式 | 說明 |
|------|------|------|
| `--text-scale` | `smallest` \| `small` \| `auto` \| `large` \| `largest` \| 浮點數 | 文字與間距縮放倍率；預設 `auto`（依 `--width` 自動放大） |
| `--text-scale-max` | 浮點數 | 自動縮放最大倍率（僅 auto 模式生效；預設 `2.5`） |

---

## 一、scripts/zentable_render.py CLI 參數（全部）

| 參數 | 說明 | 適用模式 | Theme 編輯頁有？ |
|------|------|----------|-----------------|
| `--force-pil` | 強制 PIL 渲染 | 全域 | 有（模式選擇） |
| `--force-css` | 強制 CSS+Chrome | 全域 | 有（模式選擇） |
| `--force-ascii` | 強制 ASCII | 全域 | 有（模式選擇） |
| `--theme FILE` | 主題檔案路徑 | 全域 | 有（theme_json 時用） |
| `--theme-name NAME` | 內建主題名稱 | 全域 | 有（主題下拉） |
| `--params JSON` | 自訂參數覆蓋 | PIL / ASCII | 見下方 |
| `--output-ascii FILE` | ASCII 輸出檔 | ASCII | 後端內部 |
| `--transparent` | 透空背景 PNG | CSS | 有（透空勾選） |
| `--bg MODE` | 背景：transparent \| theme \| #RRGGBB | CSS | **無** |
| `--width N` | 強制 viewport/輸出寬度 | CSS / PIL | **無** |
| `--scale N` | 輸出尺寸倍數（0.1–5.0） | 全域 | **無** |
| `--per-page N` / `--pp N` | 每頁列數 | 全域 | 有（每頁筆數） |
| `--fill-width M` | 搭配 --width：background \| container \| scale \| no-shrink | CSS | **無** |
| `--page N\|A-B\|A-\|all` / `--p ...` | 第 N 頁或頁碼範圍 | 全域 | 有（頁碼） |
| `--all` | 等價 `--page all` | 全域 | **無** |
| `--sort <欄位規格>` | 依欄位排序（支援多鍵，例：`分數>等級`、`分數:desc,姓名:asc`） | 全域 | 有（排序欄位） |
| `--asc` / `--desc` | 升序 / 降序 | 全域 | 有（排序方向） |
| `--f <過濾規格>` / `--filter <過濾規格>` | 欄位/列過濾（可重複），例：`col:!備註,附件`、`row:狀態!=停用;分數>=60` | 全域 | **無** |
| `--both` / `--bo` | 除 PNG 外同時輸出 ASCII（同主檔名 .txt） | 全域 | **無** |

註：ASCII 的 `--params` 已支援，`gentable_ascii.php` 也會傳入（含 `style/padding/align/header_align`、框線字元覆蓋、以及 `ascii_debug`）。

---

## 二、各模式 Theme 編輯頁參數

### CSS 模式

- **主題**：從 themes/css/ 載入，或即時 theme_json
- **編輯方式**：選擇器列表（body, container, table, th, td...）或 Theme JSON (Advanced)
- **額外**：透空背景（cssTransparent）

**CLI 對應**：`--theme` / `--theme-name`、`--transparent`

### Highlight 資料格式（CSS 模式）

Theme 的 `highlight_styles` 定義語意 token（如 success、warning、danger），data 以 `hl` 標註即可套用樣式。

- **Cell-level**：`{"text": "95", "hl": "success"}`
- **Row-level**：`{"row_hl": "warning", "cells": ["項目A", "72", "注意"]}`
- 優先序：`cell.hl` > `row_hl` > theme default；未知 token 會 fallback 至 `default` 並在 stderr 輸出 warning。

---

### PIL 模式

| 參數 | UI 元素 | 備註 |
|------|---------|------|
| bg_color | p_bg_color | ✓ |
| text_color | p_text_color | ✓ |
| header_bg | p_header_bg | ✓ |
| header_text | p_header_text | ✓ |
| alt_row_color | p_alt_row_color | ✓ |
| border_color | p_border_color | ✓ |
| cell_align | p_cell_align | ✓ |
| header_align | p_header_align | ✓ |
| font_size | p_font_size | ✓ |
| header_font_size | p_header_font_size | ✓ |
| title_font_size | p_title_font_size | ✓ |
| footer_font_size | p_footer_font_size | ✓ |
| padding | p_padding | ✓ |
| cell_padding | p_cell_padding | ✓ |
| row_height | p_row_height | ✓ |
| header_height | p_header_height | ✓ |
| border_radius | p_border_radius | ✓ |
| border_width | p_border_width | ✓ |
| shadow_color | p_shadow_color | ✓ |
| shadow_offset | p_shadow_offset | ✓ |
| shadow_blur | p_shadow_blur | ✓ |
| shadow_opacity | p_shadow_opacity | ✓ |
| title_padding | p_title_padding | ✓ |
| footer_padding | p_footer_padding | ✓ |
| line_spacing | p_line_spacing | ✓ |
| watermark_enabled | p_watermark_enabled | ✓ |
| watermark_text | p_watermark_text | ✓ |
| watermark_opacity | p_watermark_opacity | ✓ |
| **font_family** | — | **無 UI**（gentable_pil 有 whitelist） |

---

### ASCII 模式

| 參數 | UI 元素 | 後端有接收？ |
|------|---------|--------------|
| style | a_style | ✓ |
| padding | a_padding | ✓ |
| align | a_align | ✓ |
| header_align | a_header_align | ✓ |
| ascii_debug | （無，後端自動） | ✓（輸出 debug JSON：stage1/stage2/stage3_details） |

**說明**：gentable_ascii 已接收 style、padding、align、header_align、border_mode、row_interval、col_interval、grid_config 等，scripts/zentable_render.py 支援 `--params` 覆蓋。

#### ASCII grid_config 套用規則

| 區塊 | null | false | 自訂物件 | 備註 |
|------|------|-------|----------|------|
| title_sep | 用 style 預設 | 不畫該線 | 4,5,6,0 字元 | 僅 sep 支援 null/false |
| header_sep | 用 style 預設 | 不畫該線 | 4,5,6,0 字元 | 同上 |
| title, top, bottom, footer | — | — | 九宮格 7–9,4–6,1–3 | 未定義列跳過；缺鍵用預設 |

**sep 位置**：4=最左、6=最右、5=橫線、0=交叉。只設 4,5,6 未設 0 → 交叉處為空（├───┤）。

**為何其他區塊邏輯不同？** title、top、bottom、footer 屬於表格「結構」（必備框線或由 data 決定顯示），sep 為「裝飾性」分隔線。sep 可選不畫（false）或還原預設（null），結構區塊則依九宮格定義繪製、未定義列跳過。

#### padding 實現邏輯

- 每欄寬度 = `max(內容 display width) + padding×2`
- `align_text` 將內容對齊至此寬度
- 輸出時外加 `cell_pad_left`、`cell_pad_right` 個空格（預設各 1）
- **左靠齊且最左先空 2 格**：`align: "left"`、`cell_pad_left: 2`，或使用 `cells.5` 格式

#### grid_config cells.5（儲存格格式，僅 ASCII；CSS/PIL 未來實作）

- `"cells": {"5": "  {}"}` → 左空 2 格後接值
- 支援 Python format spec，`:` 後為格式規格

| 格式 | 效果 |
|------|------|
| `"  {:.2f}"` | 小數兩位 |
| `"  {:>10}"` | 右對齊寬 10 |
| `"{:,.2f}"` | 千分位、小數兩位 |
| `"{:.1%}"` | 百分比一位 |
| `"{}"` | 預設 |

非數值使用 `{:.2f}` 等會 fallback 成字串。

---

## 三、進階 Render 選項（Advanced）

點擊預覽列「⚙️ Advanced」展開：

| 參數 | UI | 適用模式 |
|------|-----|----------|
| `--width` | renderWidth | CSS, PIL |
| `--scale` | renderScale | 全域 |
| `--fill-width` | renderFillWidth | CSS |
| `--bg` | renderBg | CSS |

## 四、Table Detect 區塊

**用途**：分析使用者輸入的文字訊息，判斷是否需以表格形式呈現。供 AI Agent（如 OpenClaw）在對話流程中決定是否呼叫 ZenTable 渲染表格。

- 輸入範例：「列出產品價格比較表」→ 回傳 `needs_table: true`
- 呼叫 `table_detect_api.php` → 執行 `table_detect.py`
- 回傳：`needs_table`、`reason`、`confidence`

## 五、總結

- **scripts/zentable_render.py CLI**：約 17 個參數
- **Theme 編輯頁已涵蓋**：模式、主題、透空、分頁、排序、PIL 全部參數（含 font_family）、ASCII 全部參數（含 header_align）、進階選項（width、scale、fill-width、bg）
- **ASCII 即時參數**：style、padding、align、header_align 已由 gentable_ascii 傳入，scripts/zentable_render.py 支援 `--params` 覆蓋
