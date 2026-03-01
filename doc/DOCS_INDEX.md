# DOCS_INDEX.md

Generated: 2026-02-27 18:27 UTC

本文件為 ZenTable 文件總目錄（第一版），用於後續逐檔清理、搬移與修編。

> 入口建議：日常先看 `doc/README.md`；需要追歷史內容時看 `doc/archive/README.md`。

## 分類總覽

| 分類 | 說明 |
| :--- | :--- |
| Runtime/Renderer/API | 執行流程、渲染、OCR、API 相關文件 |
| Skill/Workflow | OpenClaw skill 與工作流說明 |
| Refactor/重構紀錄 | refactor wave 記錄、風險與驗收 |
| General | 一般說明與綜合文檔 |
| Archive/歷史 | 已封存舊文檔（不作為現行真相） |

## Runtime/Renderer/API

| 檔案 | 狀態 | 建議 |
| :--- | :--- | :--- |
| `doc/CALIBRATE_SETUP.md` | active | 保留並更新路徑/命名 |
| `doc/DEVELOPMENT.md` | active | 保持與實際入口一致（scripts/zentable_render.py） |
| `doc/HIGHLIGHT_AND_RULES.md` | active | 保留並更新路徑/命名 |
| `doc/HIGHLIGHT_STYLE_PLAN.md` | active | 保留並更新路徑/命名 |
| `doc/MODULE_API_FOR_COMFYUI_N8N.md` | active | 保留並更新路徑/命名 |
| `doc/OCR_TABLE_SEGMENT_STRATEGY.md` | active | 保留並更新路徑/命名 |
| `doc/OCR_TEST_SPEC.md` | active | 保留並更新路徑/命名 |
| `doc/PADDLEOCR_SERVICE.md` | active | 保留並更新路徑/命名 |
| `doc/PADDLE_TABLE_OCR_HANDOFF.md` | active | 保留並更新路徑/命名 |
| `doc/RENDERER_USAGE.md` | active | 保留並更新路徑/命名 |
| `doc/RENDER_PARAMS_REFERENCE.md` | active | 保留並更新路徑/命名 |
| `doc/SPECIFICATION.md` | active | 保留並更新路徑/命名 |
| `doc/THEME_SOURCES.md` | active | 保留並更新路徑/命名 |
| `doc/THEME_STRUCTURE.md` | active | 保留並更新路徑/命名 |

## Skill/Workflow

| 檔案 | 狀態 | 建議 |
| :--- | :--- | :--- |
| `doc/SKILL_PY_PROGRAMS.md` | active | 保留並更新路徑/命名 |

## Refactor/重構紀錄

| 檔案 | 狀態 | 建議 |
| :--- | :--- | :--- |
| `doc/refactor/ERRATA.md` | active | 保留並更新路徑/命名 |
| `doc/refactor/acceptance-checklist.md` | active | 驗收結果同步，避免過時勾選 |
| `doc/refactor/execution-order.md` | active | 保留並更新路徑/命名 |
| `doc/refactor/inventory.md` | active | 保留並更新路徑/命名 |
| `doc/refactor/risk-register.md` | active | 保留並更新路徑/命名 |
| `doc/refactor/todo.md` | active | 作為重構真相來源，持續同步 |

## General/General

| 檔案 | 狀態 | 建議 |
| :--- | :--- | :--- |
| `doc/CSS_MODE_BACKEND_CALL_FLOW.md` | active | 保留並更新路徑/命名 |
| `doc/ENVIRONMENT_DEPENDENCIES.md` | active | 保留並更新路徑/命名 |
| `doc/README.md` | active | 保留並更新路徑/命名 |
| `doc/REQUIREMENT.md` | active | 保留並更新路徑/命名 |
| `doc/architecture/THREE_LAYER_ARCHITECTURE.md` | active | 三層架構導讀（自 refactor todo 摘要） |
| `doc/interaction/CALIBRATION_JSON_MANAGEMENT.md` | active | 校準檔管理層需求（profile/merge/reset） |
| `doc/interaction/ASCII_CALIBRATION_REDESIGN_TODO.md` | active | ASCII 重設 TODO（雙模型+測量圖+管理層+進度清單） |
| `doc/interaction/SKILLHUB_RELEASE_CHECKLIST.md` | active | SkillHub 發布檢查清單（含英文文檔要求） |
| `doc/interaction/SKILLHUB_RELEASE_ASSETS_EN.md` | active | SkillHub 發布英文素材（description/highlights/limitations/quickstart） |
| `doc/interaction/SKILLHUB_RELEASE_NOTES_BETA.md` | active | SkillHub beta release notes + blockers |
| `doc/interaction/SKILLHUB_BETA_INTEGRATED_SCOPE.md` | active | SkillHub beta 整包 WIP 納入範圍聲明 |
| `doc/architecture/CALIBRATION_PIXEL_PIPELINE.md` | active | 校準區塊像素解析步驟（動態 pattern / gap -> calibration） |

## Archive/歷史

| 檔案 | 狀態 | 建議 |
| :--- | :--- | :--- |
| `doc/archive/CSS_FRONTEND_BACKEND_DIFF.md` | legacy | 僅保留歷史，避免當前流程引用 |
| `doc/archive/HIGHLIGHT_STYLE_TODO.md` | legacy | 僅保留歷史，避免當前流程引用 |
| `doc/archive/PLAN_COMPLETED_AND_CALL_GRAPH.md` | legacy | 僅保留歷史，避免當前流程引用 |
| `doc/archive/PROJECT_PROGRESS.md` | legacy | 僅保留歷史，避免當前流程引用 |
| `doc/archive/README.md` | legacy | 僅保留歷史，避免當前流程引用 |
| `doc/archive/SKILL_RUNNABLE_ASSESSMENT.md` | legacy | 僅保留歷史，避免當前流程引用 |
| `doc/archive/TEST_PAGE.md` | legacy | 僅保留歷史，避免當前流程引用 |
| `doc/archive/ZEBLE_FLOW.md` | legacy | 舊流程圖（含已淘汰入口），僅保留歷史參考 |
| `doc/archive/INTEGRATION.md` | legacy | 早期整合示例草稿（含過時呼叫方式），僅供歷史參考 |

## 文件清理進度（Step A→D）

1. ✅ Step A：文件盤點與總表建立（本檔）。
2. ✅ Step B：純歷史文件移入 `doc/archive/`（例如 `ZEBLE_FLOW.md`、`INTEGRATION.md`）。
3. ✅ Step C：active 文件 canonical 路徑/命名修正（`scripts/zentable_render.py`、deprecated `gentable.php` 註記）。
4. ✅ Step D：active/legacy 索引連結補齊（`doc/README.md`、`doc/archive/README.md`、本檔互相導覽）。

## 維護規則（後續持續）

- 每次內容變更時，同步更新對應 md。
- 每批修編後跑一次 smoke / golden 再 commit。
- 新增文件時先判定 active 或 legacy，避免主目錄再混雜歷史稿。
