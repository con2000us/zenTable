# Zx pin 預設機制更新（2026-03-01）

## 變更摘要

### 1) `table_renderer.py` 預設值對齊
- 預設主題：`minimal_ios_mobile`
- 預設寬度：`450`

### 2) 新增可持久化預設（pin）
- 新增參數：`--pin`
- 預設寫入檔案：`skills/zentable/zx_defaults.json`

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

## 文件同步
- `skills/zentable/SKILL.md` 已更新
- `doc/skills/zentable/SKILL.md`（mirror）已同步
