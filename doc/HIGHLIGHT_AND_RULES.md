# Highlight 與規則 — 使用說明

表格可依「語意」套用 theme 的高亮樣式（顏色、字重等），不需在 data 裡寫死 CSS。本頁為**使用摘要**；完整規格與 op 清單見 [HIGHLIGHT_STYLE_PLAN.md](HIGHLIGHT_STYLE_PLAN.md)。

---

## 資料格式速查

| 方式 | 寫法 | 說明 |
|------|------|------|
| **格** | `{"text": "95", "hl": "success"}` | 該格套用 token `success` |
| **列** | `{"row_hl": "warning", "cells": ["A", "B", "C"]}` | 整列套用 `warning` |
| **欄** | `"col_hl": {"分數": "danger"}` | 該欄（依欄位名）套用 `danger` |
| **規則** | `"highlight_rules": [{...}]` | 依欄位值自動套用（見下） |

Token 名稱由各 theme 的 `highlight_styles` 定義（常見：default、success、warning、danger、info、muted）。

---

## highlight_rules（依值自動上色）

在 data 根層加 `highlight_rules` 陣列，每條規則指定：**欄位名** `col`、**運算** `op`、**比較值** `value`、**套用 token** `hl`。Renderer 依陣列順序檢查，**先符合的規則**生效（first match wins）。

**常用 op**：
- 數值：`<`、`<=`、`==`、`!=`、`>=`、`>`
- 多選一：`in`（value **必須為陣列**，如 `["甲","乙"]`）
- 多選排除：`not in`（value 必須為陣列）
- 子字串：`contains`、`not contains`（value 可字串或陣列）
- 空值：`empty`、`not empty`

單一值等於/不等於用 `==` / `!=`；多個候選用 `in` / `not in`。

**範例**：
```json
"highlight_rules": [
  {"col": "分數", "op": ">=", "value": 90, "hl": "success"},
  {"col": "分數", "op": "<", "value": 60, "hl": "danger"},
  {"col": "等級", "op": "in", "value": ["甲", "乙"], "hl": "info"}
]
```

---

## 優先序（衝突時）

1. `cell.hl`（最高）
2. `row_hl`
3. `col_hl`
4. `highlight_rules`（第一條符合者）
5. theme default（最低）

---

## 完整規格

op 完整清單、value 型態、規則衝突細節、Sub-cell segments 等見 **[HIGHLIGHT_STYLE_PLAN.md](HIGHLIGHT_STYLE_PLAN.md)**。
