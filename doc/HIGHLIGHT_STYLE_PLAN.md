# ZenTable Highlight Style 規劃與實作方案

## 目標
讓 **Theme** 能預設多組高亮樣式（highlight styles），並讓 **data JSON** 依資料情境套用對應樣式。

核心原則：
- **Theme 管視覺**（顏色、邊框、字重、背景）
- **Data 管語意**（success/warning/danger...）
- Renderer 只做 mapping，不把顏色硬寫死在程式裡

---

## 設計總覽

### 1) Theme 層：定義 highlight tokens
在 `themes/css/<theme>/template.json` 新增 `highlight_styles`（或 `tokens.highlight`）。

**Token 名稱**：由各 theme 在 `highlight_styles` 的 key 自由定義，系統不限定固定清單。Data 的 `hl` 應使用該 theme 有定義的 token；未定義時 renderer 會 fallback 至 `default`。若由 agent 產出 data，可依 theme 提供的 token 清單（或 description）決定套用哪一個。

**採用做法 A**：每個 token 的 value 可為**字串**（向後相容）或**物件**；物件可含選用的 `description`，供 data 作者或 agent 判斷套用時機，renderer 僅使用樣式部分、不解析 description。

建議結構：

```json
{
  "type": "css",
  "name": "minimal_ios",
  "styles": { ... },
  "highlight_styles": {
    "default": "background:#f8f9fa; color:#212529;",
    "success": "background:#e8f7ee; color:#1f7a3d; font-weight:600;",
    "warning": {
      "style": "background:#fff8e6; color:#8a5b00; font-weight:600;",
      "description": "需注意、接近閾值、待觀察"
    },
    "danger":  "background:#fdecec; color:#b42318; font-weight:600;",
    "info":    "background:#eaf2ff; color:#1d4ed8;",
    "muted":   "background:#f3f4f6; color:#6b7280;"
  }
}
```

- **Renderer 行為**：value 為字串時直接當 CSS；為物件時取 `value.style` 作為 CSS，忽略 `description`。
- 也可拆成 row/cell：`highlight_styles.row.success`, `highlight_styles.cell.success`，MVP 可先共用。

---

### 2) Data 層：語意標註

#### Cell-level（優先）

```json
{"text":"95", "hl":"success"}
```

#### Row-level

```json
{"row_hl":"warning", "cells":["項目A", "72", "注意"]}
```

#### 欄位標註（可選）

```json
{"col_hl": {"分數":"danger"}}
```

#### 規則引擎（可選，第二階段）

```json
"highlight_rules": [
  {"col":"分數", "op":">=", "value":90, "hl":"success"},
  {"col":"分數", "op":"<",  "value":60, "hl":"danger"}
]
```

**op 清單**（renderer 實作時支援）：  
- 數值比較（該格可轉成數字時）：`<`、`<=`、`==`、`!=`、`>=`、`>`，value 為單一數。  
- 單一值等於/不等於：`==`、`!=`，value 為單一值（字串或數）。  
- 多選一／多選排除：`in`、`not in`，**value 必須為陣列**（格內容等於陣列中任一個即 in 成立；單一值情境用 `==`/`!=`）。  
- 子字串：`contains`、`not contains`，value 為字串或陣列（陣列時表示「包含任一個」即成立）。  
- 前綴／後綴（可選）：`starts with`、`ends with`，value 為字串或陣列。  
- 空值（可選）：`empty`、`not empty`，value 可省略或忽略。  
- 比對方式：先嘗試將格內容與 value 轉成數字再比較；無法轉數字則改字串比較。

**規則衝突**：  
- 與其他來源：維持既有優先序（cell.hl > row_hl > col_hl > highlight_rules > default）；只有當該格沒有 cell.hl、row_hl、col_hl 時，才用 highlight_rules 計算。  
- 規則之間：同一格若多條規則都符合，以**陣列順序**為準，**第一條符合的規則**的 `hl` 生效（first match wins）；撰寫時將較重要規則排在前面。

#### Sub-cell / 格內多段（可選，進階）

同一格內可對**多段文字**各自套不同 `hl`，細緻到 cell 之下。

**資料格式**：cell 可選 `segments` 陣列，與 `text`/`hl` 互斥；有 `segments` 時以 segments 為準，忽略 cell 的 `hl`。

```json
{
  "segments": [
    {"text": "Revenue ", "hl": "default"},
    {"text": "+18.2%", "hl": "success"},
    {"text": " (YoY)", "hl": "muted"}
  ]
}
```

**Renderer 輸出**：`<td>` 內多個 `<span class="hl hl-<token>">...</span>`，每段對應一個 token；theme 沿用同一組 `highlight_styles`，selector 需涵蓋 `span.hl-xxx`（或 `.hl-xxx` 同時套在 `td` 與 `span`）。

**注意**：
- 所有 segment 的 `text` 輸出前必須做 HTML escape。
- Smart-wrap 需在保留 span 邊界下對整格內容斷行（可於斷行處切在 segment 之間）。
- 優先序：有 `segments` 時不使用 cell 的 `hl`；每個 segment 的 `hl` 仍可與 `row_hl` 等合併（依 resolve 邏輯）。

> 此為 MVP 之後的進階規格，實作時機可放在 Phase 7 可選增強。

---

## 優先序（重要）

同一格若多來源衝突，建議優先序：

1. `cell.hl`（最高）
2. `row_hl`
3. `col_hl`
4. `highlight_rules`
5. theme default（最低）

---

## Renderer 實作建議

## A. 資料正規化
在 normalize 階段統一 cell schema：

```ts
Cell = {
  text: string,
  hl?: string,
  className?: string,
  style?: string
}
```

- 舊格式（純字串）自動轉 `{text: "..."}`
- 不破壞既有 input

## B. 計算 highlight token
新增函式：

- `resolve_cell_highlight(row, col, cell, context)`
- 回傳 `{ hlToken, source }`

## C. 輸出 class（不要輸出硬編碼 style）
對每個 `<td>/<th>` 增加 class：

- `hl`
- `hl-success` / `hl-warning` / ...

例如：

```html
<td class="cell hl hl-success">95</td>
```

## D. 注入 theme CSS
將 `highlight_styles` 轉成 CSS class（渲染時拼接到 style block）：

```css
.hl-success { background:#e8f7ee; color:#1f7a3d; font-weight:600; }
.hl-warning { background:#fff8e6; color:#8a5b00; font-weight:600; }
```

若 token 不存在：
- fallback `hl-default`
- 並記錄 warning log（不 crash）

---

## Smart-wrap 相容

- `smart-wrap` 僅調整 `text` 斷行
- 不應覆蓋/移除 `hl`
- 若 cell 是 object，smart-wrap 只能改 `cell.text`

---

## API/CLI 參數建議

### 建議新增
- `--hl-strict`：遇到未知 token 直接報錯（預設 false）
- `--hl-debug`：輸出每格 hl 來源與結果（方便調試）

### 保留現況
- 與 `--smart-wrap` / `--nosw` 完全相容

---

## MVP 範圍（建議先做）

1. Theme 支援 `highlight_styles`
2. Cell-level `{"text":"...", "hl":"success"}`
3. Row-level `row_hl`
4. class 注入 + fallback
5. 1 份 demo JSON + before/after 圖

> 先不上規則引擎（`highlight_rules`），避免一次做太大。

---

## 驗收清單

- [ ] 舊 JSON（純字串 rows）渲染完全不壞
- [ ] `hl` 可套用到 cell
- [ ] `row_hl` 可套用整列
- [ ] 未知 token fallback 正常
- [ ] `smart-wrap` 開/關都不破壞 hl
- [ ] 至少 2 個 theme 測試通過（例如 `minimal_ios`, `mobile_chat`）

---

## 範例資料（可直接測）

```json
{
  "title": "KPI Dashboard",
  "headers": ["Metric", "Value", "Status"],
  "rows": [
    ["Revenue", {"text":"+18.2%", "hl":"success"}, "Good"],
    ["Churn",   {"text":"6.3%",   "hl":"warning"}, "Watch"],
    ["Errors",  {"text":"27",     "hl":"danger"},  "Alert"],
    {"row_hl":"info", "cells":["Note", "Model refreshed", "FYI"]}
  ],
  "footer": "Updated 5 min ago"
}
```

---

## 風險與注意事項

1. **樣式衝突**：theme 既有 `td` 規則可能覆蓋 `.hl-*`
   - 解法：`td.hl-success` 或提高 selector specificity
2. **深色主題可讀性**：同 token 在深色/淺色 theme 需分別定義
3. **過度高亮**：若每格都高亮會視覺疲勞
   - 可加建議：預設只高亮關鍵欄位

---

## 檔案改動建議（供 Cursor）

- `scripts/zentable_render.py`
  - normalize cell object
  - resolve highlight
  - emit class
  - inject highlight CSS

- `skills/zentable/table_renderer.py`
  - 如需，透傳 `--hl-*` 參數

- `themes/css/*/template.json`
  - 加入 `highlight_styles`

- `doc/RENDER_PARAMS_REFERENCE.md`
  - 補充資料格式與參數

- `skills/zentable/SKILL.md`
  - 新增 highlight 範例

---

## 建議開發順序

1. 做 `minimal_ios` 單一 theme MVP
2. 驗證後複製到 `mobile_chat`
3. 補 doc + 範例
4. 再考慮 `highlight_rules`（自動判斷）

---

如需，我可以再補一份「最小 patch 任務列表（逐函式）」給 Cursor 直接照著改。