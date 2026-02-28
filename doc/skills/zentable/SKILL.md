> ⚠️ 此檔為鏡像副本（供 doc viewer / 網站掃描範圍內閱讀）。
>
> Canonical 原檔：`/var/www/html/zenTable/skills/zentable/SKILL.md`
> 若有內容調整，請優先修改 canonical，再同步本檔。

---
name: zentable
description: "Render structured table data as high-quality PNG images using Headless Chrome. Use when: need to visualize tabular data for chat interfaces, reports, or social media. NOT for: simple text tables that don't need visualization."
homepage: ~/.openclaw/custom-skills/zentable/SKILL.md
metadata: 
  openclaw: 
    emoji: "📊"
    requires: 
      bins: ["python3", "google-chrome"]
allowed-tools: ["exec", "read", "write"]
---

# ZenTable Skill

將結構化表格資料渲染為高品質 PNG 圖片。

> 命名規範（Phase 1）
> - Canonical code 名稱：`zentable`（全小寫）
> - UI/品牌顯示：`ZenTable`
> - `zeble*` / `zenble*` 為歷史相容別名，暫時保留
> - 詳見：`/var/www/html/zenTable/NAMING_MIGRATION.md`

## 何時使用

✅ **USE this skill when:**

- 需要視覺化呈現表格資料
- 產生專業報告/數據圖表
- 分享給 WhatsApp/Telegram/Discord 等聊天介面
- 表格資料量大，純文字難以閱讀
- 需要特定主題風格（iOS、Line、暗色模式等）

❌ **DON'T use when:**

- 簡單的 2-3 行表格（純文字即可）
- 用戶明確要求「不要圖片」
- 需要可編輯的表格（改用 CSV/Excel）

## 使用方法

### Shorthand（本專案約定）

- **MUST 規則**：使用者輸入 `Zx` 時，必須直接執行出圖流程（預設不反問、不先做解釋型回覆）。
- 使用者輸入 `Zx` 時，**視為直接執行指令**：立即進入 zenTable 出圖流程（預設不反問）。
- `Zx` 代表使用者對「出圖」有強烈意願；除非有**高度不確定性**才回問。
- 僅在以下情況允許先問：
  - 無法判定資料來源（本則/上則都無可用圖文）
  - 語氣明顯不像要輸出圖表（例如純閒聊、無表格意圖）
  - 關鍵欄位缺失導致輸出高度可能錯誤
- 其餘情況一律直接用預設設定出圖（預設 CSS + `minimal_ios_mobile` + `width=450`）。\n- `table_renderer.py` 已跟隨此預設（未指定時自動套用 `minimal_ios_mobile + width=450`）。
- **MUST 規則**：出圖回覆時，不要只給連結；只要平台支援圖片附件/內嵌，就必須直接回傳圖片本體。
- `Zx` 預設視為「使用 zenTable 輸出表格圖片（而非純文字精簡回覆）」。
- `Zx` 的來源優先序：**本則附圖 OCR** → **本則文字整理表格** → **上一則附圖 OCR** → **上一則文字整理表格**。
- 若 `Zx` 觸發但上下文沒有可用圖文資料，先回問一次補充（避免輸出空表）。
- **`Zx` 預設渲染模式為 CSS**（優先走 `gentable_css.php` / `table_renderer.py` 的 CSS 路徑）。
- 渲染預設啟用 smart-wrap（代理可在渲染前對長字串做語意斷行）。
- 若要保留原始文字斷句，可加 `--no-smart-wrap`（或 `--nosw`）。
- 若上下文已有表格主題（例如 skills 清單、參數清單、比較表），直接進行渲染並回傳圖片。

### 語法糖 -> Canonical 參數映射（Agent 規格）

原則：`Zx` 參數可視為 **Agent 語法糖**；同時 `table_renderer.py` 也已支援常用 alias 與 `page_spec` 展開，便於直接呼叫。

| 語法糖（Agent 可讀） | Canonical key（Agent 內部） | 正規化規則 | Renderer 最終參數 |
|------|------|------|------|
| `--width N` / `--w N` | `width` | 正整數 | `--width N` |
| `--transpose` / `--cc` | `transpose` | 布林；任一出現即 `true` | `--transpose` |
| `--tt` | `keep_theme_alpha` | 布林；保留 theme alpha | `--tt` |
| `--per-page N` / `--pp N` | `per_page` | 正整數 | `--per-page N` |
| `--page ...` / `--p ...` | `page_spec` | 接受 `N` / `A-B` / `A-` / `all` | `table_renderer.py` 會展開為頁碼範圍並逐頁呼叫 |
| `--all` | `page_spec` | 等價 `all` | `table_renderer.py` 會展開全部頁 |
| `--text-scale V` / `--ts V` | `text_scale` | `smallest/small/auto/large/largest` 或倍率數值 | `--text-scale V` |
| `--sort SPEC` | `sort_spec` | 單鍵或多鍵：`欄位A`、`欄位A>欄位B`、`欄位A:desc,欄位B:asc` | `--sort SPEC` |
| `--asc` / `--desc` | `sort_default_dir` | 多鍵未指定方向時的預設排序方向 | `--asc` / `--desc` |
| `--f SPEC` / `--filter SPEC` | `filters` | 欄位/列過濾；可重複多次 | `--f SPEC` |
| `--smart-wrap` | `smart_wrap` | 明確設為 `true` | `--smart-wrap`（可省略；renderer 預設開） |
| `--no-smart-wrap` / `--nosw` | `smart_wrap` | 設為 `false` | `--no-smart-wrap` |
| `--theme NAME` / `-t NAME` | `theme` | 主題名稱字串 | `--theme NAME` |
| `--both` / `--bo` | `output_both` | 布林；除 PNG 外同時輸出 ASCII（同主檔名 .txt） | `--both` |
| `--pin KEYS` | `pin_keys` | 將本次有效參數寫成未來預設；`KEYS` 以逗號分隔，支援 `theme,width,nosw,per_page` | `--pin width,nosw,theme` |\n
`page_spec` 展開規則（Agent 端）：

- `N` -> 只輸出第 `N` 頁。
- `A-B` -> 輸出第 `A` 到 `B` 頁（含 `B`）。
- `A-` -> 從第 `A` 頁輸出到最後一頁。
- `all` 或 `--all` -> 輸出全部頁面。
- 未指定 `page_spec` 時，預設輸出前 3 頁（`1-3`）；若仍有頁面未輸出，會提示可用 `--page 4-` 或 `--all`。

Canonical 結構建議（Agent 內部）：

```json
{
  "theme": "minimal_ios_mobile",
  "width": 900,
  "transpose": false,
  "keep_theme_alpha": false,
  "per_page": 15,
  "page_spec": "2-",
  "sort_spec": "分數:desc,姓名:asc",
  "sort_default_dir": "asc",
  "filters": ["col:!備註,附件", "row:狀態!=停用;分數>=60"],
  "text_scale": "auto",
  "smart_wrap": true,
  "output_both": false
}
```

轉譯責任邊界（建議）：

- Agent：可先做語法正規化，確保呼叫一致。
- `table_renderer.py`：可直接接受常見語法糖並轉成合法呼叫。
- 核心 `zentable_render.py`：仍以 canonical 參數為主。

### 實際轉譯範例（語法糖 -> canonical -> renderer）

範例 1：常見單頁輸出

- 使用者語法糖：`Zx --theme minimal_ios_mobile --w 900 --ts large`
- canonical：

```json
{
  "theme": "mobile_chat",
  "width": 900,
  "text_scale": "large",
  "smart_wrap": true,
  "page_spec": "1"
}
```

- renderer 呼叫：

```bash
python3 ~/.openclaw/custom-skills/zentable/table_renderer.py - /tmp/out.png --theme minimal_ios_mobile --width 900 --text-scale large --page 1
```

範例 2：關閉智慧換行 + 轉置

- 使用者語法糖：`Zx --cc --nosw -t compact_clean`
- canonical：

```json
{
  "theme": "compact_clean",
  "transpose": true,
  "smart_wrap": false,
  "page_spec": "1"
}
```

- renderer 呼叫：

```bash
python3 ~/.openclaw/custom-skills/zentable/table_renderer.py - /tmp/out.png --theme compact_clean --transpose --no-smart-wrap --page 1
```

範例 3：頁面範圍（A-B）展開

- 使用者語法糖：`Zx --p 2-4 --pp 12`
- canonical：

```json
{
  "per_page": 12,
  "page_spec": "2-4"
}
```

- Agent 展開頁碼：`[2, 3, 4]`
- renderer 呼叫（逐頁）：

```bash
python3 ~/.openclaw/custom-skills/zentable/table_renderer.py - /tmp/out.p2.png --per-page 12 --page 2
python3 ~/.openclaw/custom-skills/zentable/table_renderer.py - /tmp/out.p3.png --per-page 12 --page 3
python3 ~/.openclaw/custom-skills/zentable/table_renderer.py - /tmp/out.p4.png --per-page 12 --page 4
```

範例 4：全部頁面（all）

- 使用者語法糖：`Zx --all --pp 20 --tt`
- canonical：

```json
{
  "page_spec": "all",
  "per_page": 20,
  "keep_theme_alpha": true
}
```

- `table_renderer.py` 會先計算總頁數 `total_pages`，再展開為 `1..total_pages` 逐頁呼叫。
- 若未指定 `--page` / `--all`，會先輸出 3 張並提示剩餘頁數與續印指令（如 `--p 4-`）。

範例 5：多鍵排序（數值優先）

- 使用者語法糖：`Zx --sort 分數:desc,等級:asc,姓名:asc`
- canonical：

```json
{
  "sort_spec": "分數:desc,等級:asc,姓名:asc",
  "sort_default_dir": "asc"
}
```

- renderer 呼叫：

```bash
python3 ~/.openclaw/custom-skills/zentable/table_renderer.py - /tmp/out.png --sort "分數:desc,等級:asc,姓名:asc"
```

- 規則：同欄位值相同時依下一鍵排序；可解析成數值的內容會優先以數值比較。

範例 6：欄位/列過濾（f）

- 使用者語法糖：`Zx --f "col:!備註,附件" --f "row:狀態!=停用;分數>=60"`
- canonical：

```json
{
  "filters": [
    "col:!備註,附件",
    "row:狀態!=停用;分數>=60"
  ]
}
```

- renderer 呼叫：

```bash
python3 ~/.openclaw/custom-skills/zentable/table_renderer.py - /tmp/out.png --f "col:!備註,附件" --f "row:狀態!=停用;分數>=60"
```

範例 7：同時輸出 PNG 與 ASCII（both）

- 使用者語法糖：`Zx --both` 或 `Zx --bo -t mobile_chat`
- canonical：`"output_both": true`
- renderer 呼叫：主輸出為 PNG，另產出同檔名副檔名 `.txt` 的 ASCII 表格。

```bash
python3 ~/.openclaw/custom-skills/zentable/table_renderer.py - /tmp/out.png --theme mobile_chat --both
# 產出 /tmp/out.png 與 /tmp/out.txt
```


### 基礎呼叫

### 固定預設（pin）

可用 `--pin` 把本次參數記成往後預設（寫入 `skills/zentable/zx_defaults.json`）。

1) **選擇性 pin（指定鍵）**

```bash
# 只固定 theme/width/smart-wrap(=nosw)
echo '{"headers":["A"],"rows":[["1"]]}' \
| python3 ~/.openclaw/custom-skills/zentable/table_renderer.py - /tmp/pin.png \
  --theme compact_clean --width 700 --nosw --pin width,nosw,theme
```

2) **全量 pin（只打 `--pin`）**

```bash
# 代表把「這次有效參數」整批設為之後預設
echo '{"headers":["A"],"rows":[["1"]]}' \
| python3 ~/.openclaw/custom-skills/zentable/table_renderer.py - /tmp/pin_all.png \
  --theme compact_clean --width 700 --nosw --text-scale small --auto-width --pin
```

> `--pin`（不帶值）= pin all-current params

支援固定的預設鍵：`theme`, `width`, `smart_wrap`(`nosw`), `per_page`, `text_scale`, `text_scale_max`, `transparent`, `auto_height`, `auto_height_max`, `auto_width`, `auto_width_max`。

之後若不帶這些參數，會自動沿用 pinned 預設。


```bash
echo '{JSON資料}' | python3 ~/.openclaw/custom-skills/zentable/table_renderer.py - 輸出路徑.png --theme 主題名稱
```

### 參數說明

| 參數 | 說明 | 選項 |
|------|------|------|
| `--theme` | 視覺主題 | `default_light`, `default_dark`, `mobile_chat`, `minimal_ios`, `minimal_ios_mobile`, `bubble_card`, `modern_line`, `compact_clean` |
| `--transparent` | 透明背景 | 加上此參數 |
| `--width` | 固定寬度 | 例如 `--width 800` |
| `--sort` | 排序欄位規格 | 單鍵：`欄位`；多鍵：`欄位A>欄位B` 或 `欄位A:desc,欄位B:asc` |
| `--asc` / `--desc` | 排序方向 | 作為未指定方向欄位的預設方向 |
| `--f` / `--filter` | 欄位/列過濾 | 例：`col:!備註,附件`、`row:狀態!=停用;分數>=60` |
| `--both` / `--bo` | 同時輸出 ASCII | 除 PNG 外另產出同主檔名之 `.txt` |
| `--no-smart-wrap` / `--nosw` | 關閉智慧換行（保留原始文字斷句） | 二選一即可 |

### JSON 資料格式

```json
{
  "title": "表格標題",
  "headers": ["欄位A", "欄位B", "欄位C"],
  "rows": [
    ["資料1", "資料2", "資料3"],
    ["資料4", "資料5", "資料6"]
  ],
  "footer": "頁尾說明（可選）"
}
```

**Highlight（可選）**：格／列／欄可套用 theme 語意樣式；另可依欄位值用 `highlight_rules` 自動上色。格式與 op 見專案 **[doc/HIGHLIGHT_AND_RULES.md](../../doc/HIGHLIGHT_AND_RULES.md)**，完整規格見 [doc/HIGHLIGHT_STYLE_PLAN.md](../../doc/HIGHLIGHT_STYLE_PLAN.md)。

## 主題選擇指南

| 場景 | 推薦主題 |
|------|---------|
| 一般文件/報告 | `default_light` |
| 暗色模式展示 | `default_dark` |
| 手機聊天介面（預設） | `minimal_ios_mobile` ⭐ |
| Apple 生態內容 | `minimal_ios` |
| 視覺強調/卡片 | `bubble_card` |
| Line 社群相關 | `modern_line` |
| 資料量大/小螢幕 | `compact_clean` |

## 完整範例

### 範例 1：銷售報表

```bash
echo '{
  "title": "月度銷售報表",
  "headers": ["產品", "數量", "單價", "總額"],
  "rows": [
    ["iPhone 15", 120, 29900, 3588000],
    ["MacBook Pro", 45, 59900, 2695500],
    ["AirPods Pro", 200, 7990, 1598000]
  ],
  "footer": "2024年1月統計"
}' | python3 ~/.openclaw/custom-skills/zentable/table_renderer.py - /tmp/sales.png --theme mobile_chat
```

### 範例 2：透明背景（適合疊加）

```bash
echo '{
  "title": "即時數據",
  "headers": ["指標", "數值"],
  "rows": [["溫度", "25°C"], ["濕度", "60%"]]
}' | python3 ~/.openclaw/custom-skills/zentable/table_renderer.py - /tmp/overlay.png --theme minimal_ios --transparent
```

### 範例 3：固定寬度

```bash
echo '{
  "title": "寬幅表格",
  "headers": ["A", "B", "C", "D", "E"],
  "rows": [[1,2,3,4,5], [6,7,8,9,10]]
}' | python3 ~/.openclaw/custom-skills/zentable/table_renderer.py - /tmp/wide.png --theme compact_clean --width 1000
```

## Agent 使用流程

當用戶需要表格視覺化時：

1. **準備資料**：若觸發 `Zx`，先依「本則圖 → 本則文 → 上一則圖 → 上一則文」決定資料來源，再整理成 JSON
2. **選擇主題**：根據場景選擇最適合的主題
3. **執行渲染**：使用 exec 工具執行命令
4. **回傳圖片**：使用適合的 channel 工具發送 PNG

### 完整對話範例

用戶：「請把這個成績表做成圖片」

Agent 思考：這需要 ZenTable skill 來渲染表格

Agent 行動：
```bash
echo '{"title":"期末成績","headers":["姓名","國文","數學","英文"],"rows":[["小明",85,92,78],["小華",90,88,95]]}' | python3 ~/.openclaw/custom-skills/zentable/table_renderer.py - /tmp/grades.png --theme mobile_chat
```

然後發送圖片給用戶。

## 錯誤處理

- Chrome 未安裝：會顯示 `RuntimeError: Chrome headless 不可用`
- 中文字型問題：建議安裝 `fonts-noto-cjk`
- JSON 格式錯誤：檢查引號、逗號是否正確

## 注意事項

- 輸出路徑建議使用 `/tmp/` 避免權限問題
- 大表格（>20 行）建議用 `compact_clean` 主題
- 單張圖片建議不要超過 50 行資料

## 進一步說明（文件）

細節與規格拆出至專案 `doc/`，SKILL 僅保留要點；需要時可查：

| 主題 | 文件 |
|------|------|
| Highlight 與規則（cell/row/col、highlight_rules、op） | [doc/HIGHLIGHT_AND_RULES.md](../../doc/HIGHLIGHT_AND_RULES.md) |
| Highlight 完整規格（op 清單、衝突、sub-cell） | [doc/HIGHLIGHT_STYLE_PLAN.md](../../doc/HIGHLIGHT_STYLE_PLAN.md) |
| Render 參數完整對照（CLI、theme 參數） | [doc/RENDER_PARAMS_REFERENCE.md](../../doc/RENDER_PARAMS_REFERENCE.md) |
| 渲染器用法（zeble_render、table_renderer） | [doc/RENDERER_USAGE.md](../../doc/RENDERER_USAGE.md) |
| 多表格分割策略（OCR 錨點 + 幾何混合） | [/workflow-hub/agent-share/OCR_TABLE_SEGMENT_STRATEGY.md](/workflow-hub/agent-share/OCR_TABLE_SEGMENT_STRATEGY.md) |

## OCR 多表格處理（後續實作註記）

為避免一張圖含多表格時誤判，後續流程預計優先新增 **OpenCV 分割判斷程式**：

- `table_segment.py`：先找多個表格 ROI（OpenCV 輪廓，主流程）
- `table_segment_rules.py`：用幾何/線條規則做多表判斷與信心分數
- `ocr_by_regions.py`：各 ROI 分區 OCR（可選輔助）
- `reconstruct_table.py`：用文字框分布重建行列

策略重點：
- 可用 OCR 時：先 OCR + 錨點文字估框，再幾何修正
- OCR 不可用或低信心時：允許人工/半自動整理
- 交付優先：先正確結果，再追求全自動
