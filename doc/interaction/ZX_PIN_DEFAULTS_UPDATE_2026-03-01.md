# Zx pin 預設機制更新（2026-03-01）

## 變更摘要

### 1) `table_renderer.py` 預設值對齊
- 預設主題：`minimal_ios_mobile`
- 預設寬度：`450`

### 2) 新增可持久化預設（pin）
- 新增參數：`--pin`
- 預設寫入檔案：`skills/zentable/zx_defaults.json`

### 3) 新增 `--pin-reset`
- `--pin-reset` 會將 pinned defaults 回復到基線：
  - `theme=minimal_ios_mobile`
  - `width=450`
  - `smart_wrap=true`
  - `per_page=15`

## `--pin` 兩種用法

### A. 指定鍵 pin（既有）
```bash
--pin width,nosw,theme
```
代表只固定 `width`、`smart_wrap`（nosw）、`theme`。

### B. 全量 pin（新增）
```bash
--pin
```
代表把「本次有效參數」整批固定為未來預設（all-current params）。

## 可 pin 的預設鍵
- `theme`
- `width`
- `smart_wrap`（`nosw`）
- `per_page`
- `text_scale`
- `text_scale_max`
- `transparent`
- `auto_height`
- `auto_height_max`
- `auto_width`
- `auto_width_max`

## 4) 修正 `--both` 的 ASCII fallback bug
- 問題：當主題是 CSS/PIL 專用（例如 `minimal_ios_mobile`、`default_dark`）時，`--both` 會在 ASCII 輸出失敗。
- 修正：`table_renderer.py` 改為 **分兩段執行**：
  1. 先輸出 PNG（原主題）
  2. 再以可用 text theme（優先同名，否則 fallback `default`）輸出 `.txt`
- 結果：`--both` 現在可穩定產出 PNG + ASCII。

## 文件同步
- `skills/zentable/SKILL.md` 已更新
- `doc/skills/zentable/SKILL.md`（mirror）已同步
