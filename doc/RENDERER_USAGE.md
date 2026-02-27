# zentable_renderer.py 用法說明

ZenTable 表格渲染腳本，支援 CSS、PIL、ASCII 三種輸出模式。

**實際執行**：`scripts/zeble_render.py`  
**參照副本**：`doc/zeble_render.py`（文件用，不參與後端呼叫）

---

## 補充：OpenClaw Custom Skill（CSS/Chrome）`table_renderer.py`

若你是在 OpenClaw / 個別 skill 內直接用 headless Chrome 產 PNG（不走 `scripts/zeble_render.py`），會用到另一支較輕量的 renderer：

- **檔案**：`~/.openclaw/custom-skills/zentable/table_renderer.py`
- **定位**：純 CSS + Chrome headless 截圖（單張表格），參數與 `zeble_render.py` **不同**

### 基本用法

```bash
python3 ~/.openclaw/custom-skills/zentable/table_renderer.py <data.json> <output.png> [options]
```

### 選項參數（table_renderer.py）

| 參數 | 格式 | 說明 |
|------|------|------|
| `--theme` | 主題名稱 | 如 `mobile_chat`、`minimal_ios`（預設 `default`） |
| `--transparent` | 旗標 | 透空背景 |
| `--width` | 正整數 | 強制輸出/viewport 寬度（px） |
| `--text-scale` | `smallest` \| `small` \| `auto` \| `large` \| `largest` \| 浮點數 | 文字與間距縮放倍率；預設 `auto`（依 `--width` 自動放大，避免寬圖字太小） |
| `--text-scale-max` | 浮點數 | 自動縮放最大倍率（僅 auto 模式生效；預設 `2.5`） |

### 使用範例

```bash
# 寬圖：文字自動放大（不需要手動指定 text-scale）
python3 ~/.openclaw/custom-skills/zentable/table_renderer.py data.json out.png --theme mobile_chat --width 900

# 寬圖：較保守的自動放大（字會比 auto 小）
python3 ~/.openclaw/custom-skills/zentable/table_renderer.py data.json out.png --theme mobile_chat --width 900 --text-scale small

# 寬圖：較積極的自動放大（字會比 auto 大，常搭配提高 max）
python3 ~/.openclaw/custom-skills/zentable/table_renderer.py data.json out.png --theme mobile_chat --width 900 --text-scale large --text-scale-max 2.5

# 想更大：調高 auto 上限
python3 ~/.openclaw/custom-skills/zentable/table_renderer.py data.json out.png --theme mobile_chat --width 900 --text-scale-max 2.0

# 手動指定：直接覆寫倍率（不走 auto）
python3 ~/.openclaw/custom-skills/zentable/table_renderer.py data.json out.png --theme mobile_chat --width 900 --text-scale 1.4
```

---

## 基本用法

```bash
python3 zentable_renderer.py <data.json> <output> [options]
```

| 參數 | 格式 | 說明 |
|------|------|------|
| **data.json** | 檔案路徑 | 表格資料的 JSON 檔路徑 |
| **output** | 檔案路徑 | 輸出檔路徑（PNG 或 TXT） |

---

## 選項參數

### 渲染模式

| 參數 | 格式 | 說明 |
|------|------|------|
| `--force-pil` | 旗標（無值） | 強制使用 PIL 渲染 |
| `--force-css` | 旗標（無值） | 強制使用 CSS + Chrome 渲染 |
| `--force-ascii` | 旗標（無值） | 強制使用 ASCII 純文字渲染 |

### 背景

| 參數 | 格式 | 說明 |
|------|------|------|
| `--transparent` | 旗標（無值） | 產出透空背景 PNG（優先於 `--bg`） |
| `--bg` | `transparent` \| `theme` \| `#RRGGBB` | 背景模式：透空、主題預設、或指定色 |

### 尺寸

| 參數 | 格式 | 說明 |
|------|------|------|
| `--width` | 正整數 | 強制 viewport 寬度（CSS）或輸出寬度（PIL） |
| `--text-scale` | `smallest` \| `small` \| `auto` \| `large` \| `largest` \| 浮點數 | （僅 CSS）文字/間距縮放倍率；預設 `auto`（依 `--width` 自動放大） |
| `--text-scale-max` | 浮點數 | （僅 CSS, auto）自動縮放上限；預設 `2.5` |
| `--scale` | 浮點數 0.1～5.0 | 輸出尺寸倍數，預設 1.0 |
| `--fill-width` | `background` \| `container` \| `scale` \| `no-shrink` | 搭配 `--width` 使用，控制超出寬度的處理方式 |

### 主題

| 參數 | 格式 | 說明 |
|------|------|------|
| `--theme` | 檔案路徑 | 主題 template.json 路徑 |
| `--theme-name` | 字串 | 內建主題名稱（如 `glass`、`dark`） |

### 自訂參數

| 參數 | 格式 | 說明 |
|------|------|------|
| `--params` | JSON 字串 | 自訂參數，覆蓋主題設定（PIL / ASCII 用） |

### ASCII 校準

| 參數 | 格式 | 說明 |
|------|------|------|
| `--calibration` | JSON 字串 | ASCII 字元寬度校準資料（支援 `ascii/cjk/box/half_space/full_space/emoji/custom`） |

### 分頁與排序

| 參數 | 格式 | 說明 |
|------|------|------|
| `--page` | `N` \| `A-B` \| `A-` \| `all` | 分頁頁碼/範圍（從 1 開始） |
| `--p` | 同 `--page` | `--page` 的別名 |
| `--all` | 旗標（無值） | 等價 `--page all` |
| `--per-page` | 正整數 | 每頁列數，預設 15 |
| `--pp` | 同 `--per-page` | `--per-page` 的別名 |
| `--sort` | 欄位規格 | 單鍵或多鍵（例：`分數`、`分數>等級>姓名`、`分數:desc,姓名:asc`） |
| `--asc` | 旗標 | 升序（預設） |
| `--desc` | 旗標 | 降序 |
| `--f` / `--filter` | 過濾規格 | 欄位/列過濾；可重複傳入（例：`col:!備註,附件`、`row:狀態!=停用;分數>=60`） |
| `--both` / `--bo` | 旗標 | 除 PNG 外同時輸出 ASCII（同主檔名 .txt） |

### ASCII 輸出

| 參數 | 格式 | 說明 |
|------|------|------|
| `--output-ascii` | 檔案路徑 | ASCII 模式輸出路徑 |

---

## ASCII Debug：版面格式化（計算各 cell 寬高）

測試頁「Render Backend」在 ASCII 模式會啟用 debug，目的是讓你能看到：

- **stage1（blueprint）**：在「不套用校準」的前提下（預設半形=1.0、全形=2.0）先算出表格每一欄/每列的 **寬高與座標藍圖**（支援多行內容的高度計算），用來當作後續套用字元寬度校準時的對應基準。
- **stage3（calibrated）**：套用校準後的輸出與細節，並可和 blueprint 對照，定位「哪個字元寬度/哪個框線字元」導致偏移。

### 如何啟用

- **測試頁**：ASCII 模式下會送出 `--params {"ascii_debug": true, ...}`。
- **CLI**：自行加上 `--params '{"ascii_debug": true}'` 並搭配 `--output-ascii`。

### debug 檔案內容（JSON）

當 `ascii_debug=true` 且有 `--output-ascii` 時，輸出檔內容會是 JSON，主要欄位：

- **text**：校準輸出（最終表格）
- **stage1**：版面格式化摘要（blueprint，不套用校準；包含欄寬/列高、每欄框線字元重複次數等）
- **stage2**：ASCII 參考結果（不套用校準的渲染結果）
- **stage3_details**：結構化細節（`blueprint` 與 `calibrated` 兩份對照資料；包含 `raw_widths`、`col_h_counts`、`col_targets`、`row_heights`、`space_width`、`h_char_width`…）

---

## --fill-width 說明（搭配 --width）

當指定 `--width` 時，可透過 `--fill-width` 選擇不同的寬度處理方式：

| 值 | 說明 | 行為 |
|------|------|------|
| **background** | 背景填滿 | viewport 固定，表格維持內容寬度並置中，背景填滿空白 |
| **container** | 表格填滿 96% | viewport 固定，表格佔 96% 寬度（預設） |
| **scale** | 輸出縮放 | 先依內容渲染，再將整體圖片縮放到目標寬度（可放大或縮小） |
| **no-shrink** | 僅放大不縮小 | 同 scale，但若實際寬度已大於目標則不縮小，避免文字太小 |

---

## 資料檔格式（data.json）

### 格式 A：陣列物件

```json
[
  {"名稱":"OpenClaw","版本":"v2.1.0","狀態":"✅ 運行中"},
  {"名稱":"FlareSolverr","版本":"v3.0","狀態":"⚠️ 維護中"}
]
```

### 格式 B：headers + rows

```json
{
  "headers": ["名稱", "版本", "狀態"],
  "rows": [
    ["OpenClaw", "v2.1.0", "✅ 運行中"],
    ["FlareSolverr", "v3.0", "⚠️ 維護中"]
  ],
  "title": "伺服器狀態",
  "footer": "Generated by ZenTable",
  "_params": {}
}
```

- `_params`：會被讀取並與 `--params` 合併後覆蓋主題設定。

---

## 使用範例

```bash
# 基本
python3 zentable_renderer.py data.json out.png

# 指定主題、透空背景
python3 zentable_renderer.py data.json out.png --theme-name glass --transparent

# 背景色、縮放
python3 zentable_renderer.py data.json out.png --bg "#1a1a2e" --scale 1.5

# 固定寬度、分頁、排序
python3 zentable_renderer.py data.json out.png --width 800 --page 2 --sort "名稱" --desc

# 每頁 10 列
python3 zentable_renderer.py data.json out.png --per-page 10

# 固定寬度 800，表格填滿 96%
python3 zentable_renderer.py data.json out.png --width 800 --fill-width container

# 固定寬度 800，背景填滿（表格置中）
python3 zentable_renderer.py data.json out.png --width 800 --fill-width background

# 固定寬度，輸出縮放（可放大或縮小）
python3 zentable_renderer.py data.json out.png --width 800 --fill-width scale

# 固定寬度，僅放大不縮小
python3 zentable_renderer.py data.json out.png --width 800 --fill-width no-shrink

# PIL 模式 + 自訂參數
python3 zentable_renderer.py data.json out.png --force-pil --theme-name glass --params '{"bg_color":"#0f3460"}'

# ASCII 模式
python3 zentable_renderer.py data.json dummy.png --force-ascii --output-ascii out.txt
```

---

## 補充說明

- **資料傳入方式**：目前透過 PHP 將 JSON 寫入臨時檔後傳入檔路徑，避免命令列長度與跳脫問題。
- **每頁列數**：由 `--per-page` 決定，預設 15。
- **viewport**：Chrome 截圖的視窗大小；未傳 `--width` 時，依表格內容估算並裁切多餘空白。
- **字體縮放**：使用 `--fill-width container` 時， table 僅填滿 96% 寬度，字體大小不變。
