---
name: zenbleTable
description: "Render structured table data as high-quality PNG images using Headless Chrome. Use when: need to visualize tabular data for chat interfaces, reports, or social media. NOT for: simple text tables that don't need visualization."
homepage: ~/.openclaw/custom-skills/zentable/SKILL.md
metadata: 
  openclaw: 
    emoji: "📊"
    requires: 
      bins: ["python3", "google-chrome"]
allowed-tools: ["exec", "read", "write"]
---

# zenbleTable Skill

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

- 使用者輸入 `Zx` 時，預設視為「使用 zenTable 輸出表格圖片（而非純文字精簡回覆）」。
- `Zx` 的來源優先序：**本則附圖 OCR** → **本則文字整理表格** → **上一則附圖 OCR** → **上一則文字整理表格**。
- 若 `Zx` 觸發但上下文沒有可用圖文資料，先回問一次補充（避免輸出空表）。
- 渲染預設啟用 smart-wrap（代理可在渲染前對長字串做語意斷行）。
- 若要保留原始文字斷句，可加 `--no-smart-wrap`（或 `--nosw`）。
- 若上下文已有表格主題（例如 skills 清單、參數清單、比較表），直接進行渲染並回傳圖片。


### 基礎呼叫

```bash
echo '{JSON資料}' | python3 ~/.openclaw/custom-skills/zentable/table_renderer.py - 輸出路徑.png --theme 主題名稱
```

### 參數說明

| 參數 | 說明 | 選項 |
|------|------|------|
| `--theme` | 視覺主題 | `default_light`, `default_dark`, `mobile_chat`, `minimal_ios`, `bubble_card`, `modern_line`, `compact_clean` |
| `--transparent` | 透明背景 | 加上此參數 |
| `--width` | 固定寬度 | 例如 `--width 800` |
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
| 手機聊天介面 | `mobile_chat` ⭐ 最常用 |
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

Agent 思考：這需要 zenbleTable skill 來渲染表格

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
