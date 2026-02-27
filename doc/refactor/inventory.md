# ZenTable Refactoring Inventory

> Generated: 2026-02-27 | Source of truth: **actual code**, not documentation.

---

## 1. Symlink Map (Critical for Compatibility)

All PHP/Skill entry points rely on these symlinks. **Must be preserved or replaced with equivalent aliases.**

| Symlink Path | Target | Used By |
|---|---|---|
| `scripts/zentable_render.py` | `scripts/zeble_render.py` | `gentable_css.php`, `gentable_pil.php`, `gentable_ascii.php` |
| `skills/zentable/zentable_renderer.py` | `scripts/zeble_render.py` | `skills/zentable/table_renderer.py` |
| `skills/zentable/themes` | `/var/www/html/zenTable/themes` | `table_renderer.py` theme discovery |
| `skills/zentable/paddleocr_service.py` | `api/paddleocr_service.py` | Skill OCR access |
| `skills/zentable/zentable_api_ctl.sh` | `scripts/zentable_api_ctl.sh` | Skill API control |
| `skills/zentable/zentable_service.py` | `api/zentable_service.py` | Skill service access |

### Broken Reference (No Symlink)

| Reference Path | Referenced By | Status |
|---|---|---|
| `scripts/zentable_renderer.py` | `api/render_api.py` L19 | **BROKEN** — file does not exist |

---

## 2. Entry Points (External → Internal)

### 2.1 PHP → Python (shell_exec)

| PHP File | Python Script | CLI Pattern | Mode |
|---|---|---|---|
| `gentable_css.php` | `scripts/zentable_render.py` (symlink) | `xvfb-run -a python <script> <json> <png> [opts]` | CSS+Chrome |
| `gentable_pil.php` | `scripts/zentable_render.py` (symlink) | `python <script> <json> <png> --force-pil [opts]` | PIL |
| `gentable_ascii.php` | `scripts/zentable_render.py` (symlink) | `python <script> <json> dummy.png --force-ascii --output-ascii <txt> [opts]` | ASCII |
| `gentable.php` | (deprecated endpoint) | returns deprecation JSON | Deprecated |
| `table_detect_api.php` | `scripts/table_detect.py` | `python <script> '<json_payload>'` | Detect |
| `calibrate_upload.php` | `calibrate_analyze.py` (root) | `python calibrate_analyze.py <image> [opts]` | Calibrate |
| `ocr_test_upload.php` | `scripts/ocr_test_analyze.py` | `python <script> <image> [opts]` | **BROKEN** (script missing) |
| `fastapi_control.php` | `api.render_api:app` | `python -m uvicorn api.render_api:app` | FastAPI |

### 2.2 Python API (import)

| API Module | Entry Function | Calls |
|---|---|---|
| `api/render_api.py` | `render_table()`, `run_render()` | subprocess → `scripts/zentable_renderer.py` (**BROKEN**) |
| `api/calibration_api.py` | `analyze_from_image()` | import → `calibrate_analyze` |
| `api/__init__.py` | re-exports above | — |

### 2.3 FastAPI Services (HTTP)

| Service File | Port | Endpoints | Status |
|---|---|---|---|
| `api/zentable_service.py` | 8011 | `/health`, `/ocr`, `/ocr/base64`, `/ocr/det`, `/render/css` | Active |
| `api/paddleocr_service.py` | 8010 | `/health`, `/ocr`, `/ocr/base64` | Active (unified OCR) |
| `api/ocr_openvino_service.py` | 8010 | `/health`, `/ocr`, `/ocr/base64` | Active (redundant — covered by paddleocr_service) |
| `deploy/paddle-table/api/paddle_table_service.py` | 8012 | `/health`, `/table-parse` | Active (separate container) |

### 2.4 Skill Entry (OpenClaw)

| File | Entry | Calls |
|---|---|---|
| `skills/zentable/table_renderer.py` | `main()` CLI | subprocess → `skills/zentable/zentable_renderer.py` (symlink → `zeble_render.py`) |

### 2.5 Frontend (JS → PHP)

| JS Function | PHP Endpoint | Method |
|---|---|---|
| `renderBackend()` css | `gentable_css.php` | POST |
| `renderBackend()` pil | `gentable_pil.php` | POST |
| `renderBackend()` ascii | `gentable_ascii.php` | POST |
| `runTableDetect()` | `table_detect_api.php` | POST |
| `loadThemesFromApi()` | `theme_api.php?action=list` | GET |
| `loadThemeTemplate()` | `theme_api.php?action=load` | GET |
| `doSaveTheme()` / `doAddTheme()` / `doCopyTheme()` | `theme_api.php` action=save | POST |
| `confirmDeleteTheme()` | `theme_api.php` action=delete | POST |
| `exportAllThemes()` | `theme_api.php?action=export-all` | GET |
| `importZipFile()` | `theme_api.php` action=import | POST |
| `exportTheme()` | `gentable_export.php` | POST |
| `runWidthTest()` / `runFullTest()` etc. | `calibrate_upload.php` | POST |
| `loadCalibrationRecords()` etc. | `calibrate_records.php` | GET/POST |
| `startFastapi()` / `stopFastapi()` | `fastapi_control.php` | POST |
| `checkFastapiStatus()` | `http://<host>:<port>/health` | GET (direct) |

---

## 3. Module Inventory

### 3.1 Core Rendering Engine — `scripts/zeble_render.py` (4,176 lines)

**The monolith.** Contains 88 functions/classes across 6 categories:

| Category | Functions | Lines (approx) | Description |
|---|---|---|---|
| UTIL | 20 | ~300 | Text width, emoji detection, color circles, CSV split |
| INPUT | 7 | ~160 | JSON loading, theme loading/caching/listing |
| TRANSFORM | 16 | ~760 | normalise_data, transpose, filter, sort, page, smart-wrap, highlight |
| RENDER_ASCII | 3 + ASCIIStyle | ~230 | ASCII table rendering with calibration |
| RENDER_CSS | 18 + TemplateEngine | ~1,100 | HTML generation, Chrome rendering, viewport, cropping |
| RENDER_PIL | 14 + PILStyle | ~1,020 | PIL image rendering, font management, mixed-font drawing |
| ORCHESTRATION | main() | ~880 | CLI parsing, mode dispatch, auto-width/height loop, post-processing |

**Global mutable state** (shared across functions):

| Variable | Line | Written By | Read By |
|---|---|---|---|
| `LAST_CSS_RENDER_MS` | 808 | `render_css` | `main` |
| `LAST_CSS_VIEWPORT` | 809 | `render_css` | `main` |
| `_font_cache` | 1480 | `get_font_cjk`, `get_font_emoji` | same |
| `_emoji_font_available` | 1481 | `_detect_emoji_font` | same |

### 3.2 Table Detect — `scripts/table_detect.py` (283 lines)

Standalone module. Clean boundaries. No coupling to renderer.

| Function | Line | Category |
|---|---|---|
| `_parse_input_payload` | 57 | Detector |
| `_is_zx_trigger` | 113 | Detector |
| `_resolve_zx_source` | 126 | Detector |
| `contains_table_data` | 153 | Detector |
| `detect_table_intent` | 164 | Detector |
| `analyze_message` | 181 | Detector |
| `analyze_payload` | 216 | Detector |

### 3.3 Calibration — `calibrate_analyze.py` (2,821 lines)

Root-level monolith for ASCII calibration. Contains two `find_block_bounds_by_pixel` definitions (L684 and L755 — later one shadows former).

### 3.4 OpenClaw Skill Shim — `skills/zentable/table_renderer.py` (350 lines)

Subprocess wrapper with duplicated page logic:
- `_parse_page_spec` — duplicates `zeble_render.py` L2574
- `_resolve_pages` — duplicates `zeble_render.py` L2606

### 3.5 API Layer — `api/` (4 files, ~700 lines active)

| File | Lines | Purpose | Duplications |
|---|---|---|---|
| `render_api.py` | 162 | Subprocess wrapper | Reference to nonexistent `zentable_renderer.py` |
| `zentable_service.py` | 494 | Combined OCR + CSS render FastAPI | `_paddle_result_to_rows` duplicates `paddleocr_service._normalize_rows` |
| `paddleocr_service.py` | 316 | Unified OCR FastAPI | Supersedes `ocr_openvino_service.py` |
| `ocr_openvino_service.py` | 178 | OpenVINO OCR FastAPI | **Redundant** — fully covered by `paddleocr_service.py` auto mode |
| `calibration_api.py` | 48 | Thin wrapper | OK |
| `__init__.py` | 7 | Re-export | OK |

### 3.6 Paddle Table Pipeline — `deploy/paddle-table/` (3 files, ~370 lines)

Standalone pipeline. Clean boundaries. No coupling to renderer.

| File | Lines | Step |
|---|---|---|
| `table_hybrid_extract.py` | 180 | Step 1: Structure + OCR |
| `normalize_rows.py` | 76 | Step 2: Row normalization |
| `merge_tables.py` | 111 | Step 3: Table merging |

### 3.7 Legacy / Dead Python Files

| File | Lines | Status | Reason |
|---|---|---|---|
| `scripts/zeble.py` | moved | **ARCHIVED** | moved to `doc/archive/deprecated_code/zeble.py` |
| `doc/zeble.py` | moved | **ARCHIVED** | moved to `doc/archive/deprecated_code/doc_zeble.py` |
| `doc/zeble_render.py` | 1,446 | **DEAD** | Marked as "document reference copy" |
| `doc/zentable_render.py` | 966 | **DEAD** | Early class-based version, superseded |
| `doc/table_detect.py` | 129 | **DEAD** | Old version missing Zx features |
| `doc/smart_table_output.py` | 163 | **DEAD** | References removed `zeble` module |
| `doc/reproduce_issue.py` | 17 | **DEAD** | One-off debug script |
| `doc/gen_test_data.py` | 55 | **DEAD** | One-off test data generator |
| **Total dead code** | **4,043 lines** | | |

---

## 4. Coupling Analysis

### 4.1 Cross-Category Dependencies in `zeble_render.py`

Functions shared by 3+ categories (cannot be trivially extracted):

| Function | Used By Categories |
|---|---|
| `_row_cells(row)` L2667 | TRANSFORM, RENDER_ASCII, RENDER_CSS, RENDER_PIL |
| `cell_text(cell)` L2836 | TRANSFORM, RENDER_ASCII, RENDER_CSS, RENDER_PIL |
| `normalize_cell(cell)` L2640 | TRANSFORM, RENDER_CSS (via `build_css_rows_html`) |
| `display_width()` L164 | RENDER_ASCII, CSS (`estimate_css_viewport_width_height` via `measure_text_width`) |
| `measure_text_width()` L2201 | RENDER_PIL, RENDER_CSS |
| `parse_color()` L1413 | RENDER_PIL |
| `resolve_cell_highlight()` L2780 | RENDER_CSS (via `build_css_rows_html`) |

### 4.2 Dependency Flow

```
index.html + js/app.js
    │
    ├──► gentable_css.php  ──► zentable_render.py (symlink) ──► zeble_render.py::main()
    ├──► gentable_pil.php  ──► zentable_render.py (symlink) ──► zeble_render.py::main()
    ├──► gentable_ascii.php ─► zentable_render.py (symlink) ──► zeble_render.py::main()
    ├──► gentable.php (deprecated) ► returns warning JSON (no renderer call)
    ├──► table_detect_api.php ──► table_detect.py
    ├──► calibrate_upload.php ──► calibrate_analyze.py
    ├──► theme_api.php (pure PHP, no Python)
    ├──► calibrate_records.php (pure PHP)
    ├──► gentable_export.php (pure PHP)
    └──► fastapi_control.php ──► api.render_api:app (uvicorn)

zeble_render.py::main()
    ├── Phase 1 (Input):  load_json → normalise_data
    ├── Phase 2 (Transform): apply_filters → transpose_table → apply_sort_and_page → apply_smart_wrap
    └── Phase 3 (Output):  render_ascii / render_css / render_pil
```

---

## 5. Documentation Map

### Fresh (Accurate)

| File | Purpose |
|---|---|
| `doc/HIGHLIGHT_AND_RULES.md` | Highlight usage guide |
| `doc/HIGHLIGHT_STYLE_PLAN.md` | Highlight style spec (acceptance unchecked) |
| `doc/RENDER_PARAMS_REFERENCE.md` | CLI param reference (naming inconsistent) |
| `doc/RENDERER_USAGE.md` | Usage guide (naming inconsistent) |
| `skills/zentable/SKILL.md` | OpenClaw skill definition |
| `doc/THEME_SOURCES.md` | Theme source explanation |
| `doc/THEME_STRUCTURE.md` | Theme directory structure |
| `doc/REQUIREMENT.md` | Runtime requirements |
| `doc/PADDLEOCR_SERVICE.md` | PaddleOCR service setup |
| `doc/ENVIRONMENT_DEPENDENCIES.md` | Dependency matrix |
| `doc/CALIBRATE_SETUP.md` | Calibration setup guide |
| `doc/CSS_MODE_BACKEND_CALL_FLOW.md` | CSS call flow (line numbers fragile) |
| `OCR_BACKENDS.md` | OCR backend selection |
| `DEPLOYMENT.md` | Docker deployment |
| `NAMING_MIGRATION.md` | Canonical naming policy |
| `deploy/paddle-table/README.md` | Paddle Table quickstart |
| `deploy/ocr-fastapi/README.md` | OCR FastAPI deployment |

### Stale (Partially Outdated)

| File | Issue |
|---|---|
| `doc/SKILL_PY_PROGRAMS.md` | 4 naming variants mixed; workflow diagram outdated |
| `doc/SPECIFICATION.md` | §9 file structure outdated; CLI references wrong script name |
| `doc/ZEBLE_FLOW.md` | References removed `/opt/` paths; title uses "Zeble" |
| `doc/MODULE_API_FOR_COMFYUI_N8N.md` | Proposal doc; `run_render()` may not work |
| `WORKFLOW_VALIDATION.md` | Script name inconsistencies |
| `THEME_EDIT.md` | Too generic, doesn't reference actual structure |

### Obsolete (Should Archive or Delete)

| File | Issue |
|---|---|
| `doc/DEVELOPMENT.md` | Architecture description severely outdated; hardcoded IPs |
| `doc/INTEGRATION.md` | **Python file with .md extension**; references nonexistent scripts |
| `doc/archive/PLAN_COMPLETED_AND_CALL_GRAPH.md` | Already archived |

---

## 6. Naming Inconsistency Summary

| Variant | Where | Actual |
|---|---|---|
| `zeble_render.py` | Actual filename in `scripts/` | **The real file** |
| `zentable_render.py` | Symlink in `scripts/` | → `zeble_render.py` |
| `zentable_renderer.py` | Symlink in `skills/zentable/` | → `zeble_render.py` |
| `zentable_renderer.py` | `api/render_api.py` L19 | **BROKEN** (no such file in `scripts/`) |
| `zentable.py` | (none) | legacy alias, no active caller |
| `zeble.py` | `doc/archive/deprecated_code/zeble.py` | archived legacy PIL renderer |
