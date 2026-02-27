# CSS Mode：Frontend 預覽 vs Backend 渲染差異說明

## 結論：有差異，且部分來自 CSS/HTML 不一致

兩邊**主題來源**在傳送 `theme_json` 時是同一份（前端 `getCssThemeJson()` 傳給 `gentable_css.php`），但後端會對 theme 做**額外處理**，且 **HTML 結構與選擇器** 與前端不盡相同，導致視覺差異。

---

## 1. 主題內容與選擇器對應（一致處）

- **選擇器對應**：前端的 `cssSelectorPreview()` 與後端的 `css_selector()` 對 `.header`/`.cell-header`/`.cell`、`body`→`.zt-body`、`tr_even`/`tr_odd`、`col_N` 等對應邏輯一致。
- **Theme 來源**：有送 `theme_json` 時，後端與前端使用同一份 template；未送時後端用 `--theme-name` 從 `themes/css/` 載入。

---

## 2. 造成差異的原因

### 2.1 後端對 theme 的「再處理」（Frontend 沒有）

| 項目 | 後端 | 前端 |
|------|------|------|
| **text-scale** | 會依 `--width`/`--text-scale` 呼叫 `_scale_css_styles_px(theme, scale)`，把 theme 裡所有 `Npx` 依倍率縮放 | 不做縮放，直接使用 template.styles |
| **透空關閉時** | 呼叫 `_strip_alpha_from_css()`，把 `rgba()`/`hsla()`/8 位 hex 轉成不透明 | 不處理，保留原始透明度 |

因此：同一 theme 下，有設 width/text-scale 或未勾透空時，**後端字級與背景會與前端預覽不同**。

### 2.2 HTML 結構不一致（會導致選擇器只在一邊生效）

| 元素 | 後端 `generate_css_html` | 前端 `updatePreview` (CSS mode) |
|------|---------------------------|----------------------------------|
| 外層 | `<body><div class="container">` | `<div class="zt-body"><div class="container">`（包在 `.zt-scope` 內） |
| 表格外層 | 無 | 可選 `<div class="table-wrapper">`（依 theme 是否有 `.table-wrapper` / `table-wrapper`） |
| 表格 | `<table>`（無 class） | `<table class="data-table">` |
| 列 | `<tr class="tr_even">` 或 `<tr class="tr_odd">` | `<tr class="row tr_even">` 或 `<tr class="row tr_odd">` |

影響：

- Theme 若有 **`.data-table`** 或 **`.table-wrapper`** 的樣式：**僅在前端生效**，後端 HTML 沒有對應元素/class。
- Theme 若有 **`tr.row`** 或 **`.row`**：**僅在前端生效**，後端 `<tr>` 沒有 `row` class。

### 2.3 額外注入的 CSS 差異

- **後端**：  
  - `td { white-space: pre-wrap !important; overflow-wrap: anywhere !important; word-break: break-word !important; }`  
  - 透空時加 `tt_css`（container/table 背景透明）。  
  - 有 `--width` 時可能加 fixed-width 用 wrap CSS（`table-layout: fixed` 等）。
- **前端**：  
  - `td { white-space: pre-wrap !important; }`（無 overflow-wrap/word-break）。  
  - 另有 `.zt-scope` 內 box-sizing、border-collapse、font-weight、table-layout 等。

### 2.4 字體

- **前端**：會用 `getFontsFromTheme()` + `getPreviewFontFaceCss()` 注入 `@font-face`，主題自訂字體可在預覽中顯示。
- **後端**：`generate_css_html` 未注入 theme 的 `@font-face`，自訂字體在後端圖中可能 fallback 成系統字體。

---

## 3. 已實作修正

1. **對齊 HTML 結構（後端已向 frontend 靠攏）**  
   - 後端改為產生 `<table class="data-table">`。  
   - 後端 `<tr>` 改為 `<tr class="row tr_even">` / `<tr class="row tr_odd">`（與前端一致）。  
   - 若 theme 的 `styles` 有 `table-wrapper` 或 `.table-wrapper`，後端會包一層 `<div class="table-wrapper">`。  
   → theme 的 `.data-table`、`.table-wrapper`、`.row` 在兩邊都會生效，**結構與選擇器一致**。

2. **text-scale / 去透明**  
   - 可維持現狀，但在 UI 或文件中說明：  
     - 後端會依 width/text-scale 縮放 px、未透空時會去除透明，所以與前端預覽可能不同。  
   - 若希望「所見即所得」，可考慮後端在「預覽模式」下不 scale、不 strip alpha（需額外參數與實作）。

3. **字體**  
   - 若 theme 內有 `fonts` / 自訂字型，後端可在產生 HTML 時一併注入對應的 `@font-face`（或共用同一套注入邏輯），減少前後端字體差異。

---

## 4. 總結

- **CSS 內容**：選擇器對應與 theme 鍵名在兩邊是對齊的；差異主要來自：  
  (1) 後端對 theme 的 **text-scale 縮放** 與 **alpha 去除**，  
  (2) **HTML 結構**（table/tr/table-wrapper 的 class 與包層）不一致，導致部分選擇器只在前端生效。  
- 透過讓後端 HTML 與前端一致（`data-table`、`row`、可選 `table-wrapper`），可讓**同一份 theme 的 CSS 在兩邊都套用到相同結構**，減少「CSS 內容不一致」造成的差異；其餘差異則來自後端刻意行為（縮放、去透明）與字體注入，可依需求再調整或加說明。
