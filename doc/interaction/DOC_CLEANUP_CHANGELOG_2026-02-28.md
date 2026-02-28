# Doc 整理完整變更清單（2026-02-28）

> 範圍：本輪 Step B / C / D 與收尾；按 commit 分段。

## e58b0fc — doc viewer: add highlighted quick list and right-click highlight action
- 修改檔案：
  - `doc/md_viewer.php`
  - `doc/README.md`
- 內容重點：
  - 左側新增 **Highlighted files** 區塊
  - 每個高亮項目提供「移除」按鈕
  - 檔案樹右鍵新增「將此檔案高亮」

## 25618f8 — docs focus: clear md highlights outside current discussion
- 修改檔案：
  - `doc/md_focus.json`
- 內容重點：
  - 清空高亮清單，移除不在當前討論範圍的文件

## 6090ec4 — docs focus: highlight DOCS_INDEX during doc discussion
- 修改檔案：
  - `doc/md_focus.json`
- 內容重點：
  - 將 `DOCS_INDEX.md` 設為高亮

## 41e3155 — docs step B: archive legacy ZEBLE_FLOW and refresh index
- 修改檔案：
  - `doc/archive/ZEBLE_FLOW.md`（由 `doc/ZEBLE_FLOW.md` 移入）
  - `doc/DOCS_INDEX.md`
  - `doc/archive/README.md`
- 內容重點：
  - 將舊流程圖歸類為 legacy 並移入 `archive/`
  - 同步索引與 archive 說明

## 23b79fa — docs step B: archive legacy INTEGRATION doc and refresh indexes
- 修改檔案：
  - `doc/archive/INTEGRATION.md`（由 `doc/INTEGRATION.md` 移入）
  - `doc/DOCS_INDEX.md`
  - `doc/README.md`
  - `doc/archive/README.md`
- 內容重點：
  - 將早期整合示例歸類為 legacy
  - 主入口與 archive 索引同步更新

## f02c82a — docs step C: normalize canonical render entry and deprecate legacy refs
- 修改檔案：
  - `doc/RENDERER_USAGE.md`
  - `doc/SKILL_PY_PROGRAMS.md`
  - `doc/MODULE_API_FOR_COMFYUI_N8N.md`
- 內容重點：
  - canonical 入口統一為 `scripts/zentable_render.py`
  - 將舊命名改為 historical note / legacy 說明

## a696887 — docs step C: refresh call-flow and params docs to canonical script path
- 修改檔案：
  - `doc/CSS_MODE_BACKEND_CALL_FLOW.md`
  - `doc/DEVELOPMENT.md`
  - `doc/RENDER_PARAMS_REFERENCE.md`
- 內容重點：
  - 呼叫流程與參數文檔統一至 canonical script path

## 13fe9dc — docs step C: polish OCR/theme/index wording and canonical path notes
- 修改檔案：
  - `doc/OCR_TEST_SPEC.md`
  - `doc/THEME_STRUCTURE.md`
  - `doc/DOCS_INDEX.md`
- 內容重點：
  - 用詞與 canonical 註記收斂（含 legacy 註解）

## bfa42c5 — docs step D: add cross-index navigation and finalize cleanup status
- 修改檔案：
  - `doc/README.md`
  - `doc/DOCS_INDEX.md`
  - `doc/archive/README.md`
- 內容重點：
  - 補齊 README / DOCS_INDEX / archive README 的雙向導覽
  - 將 A→D 狀態明確寫入索引

## 53fe7f2 — docs wrap-up: align dependency/theme-source/spec notes to canonical paths
- 修改檔案：
  - `doc/ENVIRONMENT_DEPENDENCIES.md`
  - `doc/THEME_SOURCES.md`
  - `doc/SPECIFICATION.md`
- 內容重點：
  - 依賴與主題來源描述對齊現況
  - SPEC 補 canonical 參考註記

---

## 本輪總結
- Step B：已完成（legacy 文件歸檔）
- Step C：已完成（active 文件 canonical 路徑與命名收斂）
- Step D：已完成（索引/導覽補齊）
- 收尾：已完成（依賴/主題來源/spec 一致性補強）
