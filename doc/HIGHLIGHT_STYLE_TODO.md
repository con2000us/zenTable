# Highlight Style 實作 TODO（給 Cursor 直接執行）

> 目標：在不破壞舊資料格式前提下，新增 Theme-driven highlight 樣式能力。

## Phase 0 — 準備

- [ ] 建分支：`feat/highlight-style-mvp`
- [x] 確認現況可跑：
  - [x] `python3 -m py_compile scripts/zentable_renderer.py skills/zentable/table_renderer.py`
  - [x] 用現有 JSON 渲染 1 張圖（baseline）

---

## Phase 1 — Data schema 相容擴充（MVP）

### 1.1 Cell object 相容

- [x] 在 `scripts/zeble_render.py` 的 normalize 流程支援 cell object：
  - 舊：`"text"`
  - 新：`{"text":"...", "hl":"success"}`
- [x] 保證純字串舊資料不壞

### 1.2 Row-level highlight

- [x] 支援 row object：
  - `{"row_hl":"warning", "cells":[...]} `
- [x] 若 row 是 list，維持原邏輯

---

## Phase 2 — Theme token 載入

### 2.1 Theme schema

- [x] 在 theme json 支援 `highlight_styles` 欄位
- [x] 預設 token 至少包含：
  - [x] `default`
  - [x] `success`
  - [x] `warning`
  - [x] `danger`

### 2.2 Fallback 規則

- [x] 若 data 指定未知 token：fallback `default`
- [x] stderr 輸出 warning（不 crash）

---

## Phase 3 — Renderer 注入 class

### 3.1 解析優先序

- [x] 實作 `cell.hl > row_hl > default`

### 3.2 HTML class

- [x] 每個 cell 可輸出：`hl hl-<token>`
- [x] 例如：`<td class="hl hl-success">...` 

### 3.3 CSS 注入

- [x] 將 `highlight_styles` 轉成 CSS rules（寫入 style block）
- [x] 建議 selector：`td.hl-xxx, th.hl-xxx`（避免被通用 td 覆蓋）

---

## Phase 4 — smart-wrap 相容

- [x] smart-wrap 不可覆蓋 `hl`
- [x] 若 cell 是 object，只改 `cell.text`
- [x] `--nosw` 行為維持

---

## Phase 5 — 文件與範例

### 5.1 文件更新

- [x] `doc/RENDER_PARAMS_REFERENCE.md`：新增 highlight data format
- [x] `skills/zentable/SKILL.md`：新增 highlight 範例

### 5.2 範例檔

- [x] 新增 `doc/examples/highlight_demo.json`
- [x] 內容至少有 success/warning/danger + row_hl

---

## Phase 6 — 測試與驗收

### 6.1 功能測試

- [x] 舊 JSON（純字串）渲染正常
- [x] cell `hl` 正常套用
- [x] row `row_hl` 正常套用
- [x] 未知 token fallback 正常

### 6.2 主題測試

- [x] `minimal_ios` 通過
- [x] `mobile_chat` 通過

### 6.3 smart-wrap 測試

- [x] `smart-wrap` ON：樣式仍在
- [x] `--nosw`：樣式仍在

---

## Phase 7 — 可選增強（第二階段，不阻擋 MVP）

- [ ] `highlight_rules` 自動判斷（依欄位數值）
- [ ] `--hl-debug` 參數（輸出每格 token 來源）
- [ ] `--hl-strict` 參數（未知 token 直接報錯）
- [ ] **Sub-cell segments**：支援 cell `segments: [{ "text", "hl" }, ...]`；renderer 輸出 `<td><span class="hl hl-xxx">...</span>...</td>`，segment 文字做 HTML escape；theme 沿用 `highlight_styles`（selector 涵蓋 `span.hl-xxx`）

---

## 建議 commit 切分

1. `feat(renderer): support cell/row highlight metadata`
2. `feat(theme): add highlight_styles token mapping`
3. `fix(renderer): keep highlight metadata with smart-wrap`
4. `docs: add highlight style schema and examples`

---

## 快速驗收命令（範例）

```bash
python3 /var/www/html/zenTable/skills/zentable/table_renderer.py \
  /var/www/html/zenTable/doc/examples/highlight_demo.json \
  /tmp/highlight_demo.png \
  --theme minimal_ios --width 600 --auto-height
```

```bash
python3 /var/www/html/zenTable/skills/zentable/table_renderer.py \
  /var/www/html/zenTable/doc/examples/highlight_demo.json \
  /tmp/highlight_demo_nosw.png \
  --theme minimal_ios --width 600 --auto-height --nosw
```
