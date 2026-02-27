# ZenTable Modularization TODO

> Generated: 2026-02-27
> Architecture: 3-Layer (Detector → Engine → Renderer)
> Source of truth: `scripts/zeble_render.py` (4,176 lines, 88 functions)
>
> Progress status:
> - ✅ Wave 0 done (T-000, T-001, T-002)
> - ✅ Wave 1 done (T-100, T-101)
> - ✅ Wave 2 done (T-200, T-201)
> - ✅ Wave 3 done (T-300 ~ T-305)
> - ✅ Wave 4 complete (T-400, T-401, T-410~T-413, T-420~T-423)
> - ✅ Wave 5 complete (T-500)
> - ✅ Wave 6 complete (T-600~T-604)

---

## Three-Layer Architecture Mapping

```
┌────────────────────────────────────────────────────────────────────┐
│  Detector Layer (感知/解析層)                                       │
│  zentable/input/                                                   │
│  ► JSON parsing, format normalization, error recovery              │
│  ► Theme loading, caching, listing                                 │
│  ► Intent detection (table_detect.py — already separate)           │
└────────────────────────┬───────────────────────────────────────────┘
                         │ normalised dict: {headers, rows, title, footer}
                         ▼
┌────────────────────────────────────────────────────────────────────┐
│  Engine Layer (核心演算層)                                          │
│  zentable/transform/                                               │
│  ► Table transpose, filter, sort, pagination                       │
│  ► Smart-wrap, highlight rule matching                             │
│  ► CJK character width calculation                                 │
│  ► Cell normalization, text extraction                             │
└────────────────────────┬───────────────────────────────────────────┘
                         │ transformed dict + highlight metadata
                         ▼
┌────────────────────────────────────────────────────────────────────┐
│  Renderer Layer (渲染/輸出層)                                       │
│  zentable/output/{ascii,css,pil}/                                  │
│  ► ASCII: border styles, alignment, calibrated output              │
│  ► CSS: HTML generation, Chrome headless, viewport, cropping       │
│  ► PIL: image drawing, font management, blueprint visualization    │
│  ► Shared: color parsing, emoji/CJK text segmentation              │
└────────────────────────────────────────────────────────────────────┘
```

---

## Target Directory Structure

```
scripts/
├── zeble_render.py              ← keeps CLI entry (main), becomes thin dispatcher
├── zentable_render.py           ← symlink (preserved)
│
├── zentable/                    ← NEW package
│   ├── __init__.py
│   │
│   ├── input/                   ← Detector Layer
│   │   ├── __init__.py
│   │   ├── loader.py            ← load_json, normalise_data
│   │   └── theme.py             ← theme load/cache/list/zip
│   │
│   ├── transform/               ← Engine Layer
│   │   ├── __init__.py
│   │   ├── cell.py              ← normalize_cell, cell_text, _row_cells
│   │   ├── transpose.py         ← transpose_table
│   │   ├── filter.py            ← apply_filters + helpers
│   │   ├── sort_page.py         ← apply_sort_and_page + page spec
│   │   ├── wrap.py              ← apply_smart_wrap
│   │   └── highlight.py         ← resolve_cell_highlight, rule matching
│   │
│   ├── output/                  ← Renderer Layer
│   │   ├── __init__.py
│   │   ├── ascii/
│   │   │   ├── __init__.py
│   │   │   ├── renderer.py      ← render_ascii, ASCIIStyle, align_text
│   │   │   └── charwidth.py     ← char_display_width, display_width, column widths
│   │   ├── css/
│   │   │   ├── __init__.py
│   │   │   ├── renderer.py      ← generate_css_html, build_css_rows_html
│   │   │   ├── chrome.py        ← render_css, check_chrome, TemplateEngine, DOM measure
│   │   │   ├── viewport.py      ← estimate viewport, text_scale, scale CSS
│   │   │   └── crop.py          ← crop_to_content_bounds/height, edge detection
│   │   └── pil/
│   │       ├── __init__.py
│   │       ├── renderer.py      ← render_pil, PILStyle
│   │       ├── font.py          ← get_font_cjk, get_font_emoji, detection
│   │       ├── draw.py          ← draw_text_with_mixed_fonts, draw_text_aligned
│   │       └── blueprint.py     ← render_ascii_blueprint_pil
│   │
│   └── util/                    ← Shared utilities (no layer imports)
│       ├── __init__.py
│       ├── text.py              ← is_emoji, split_text_by_font, replace_color_circles
│       └── color.py             ← parse_color, hex_rgb, _hex_to_chrome_bg
```

---

## Tasks

### Phase 0: Preparation (P0)

---

#### T-000: Create golden test baseline

- **[ID]** T-000
- **[Category]** Infrastructure
- **[Priority]** P0
- **[Risk]** Low
- **[Source]** N/A
- **[Target]** `tests/golden/` (new directory)
- **[Action]**
  1. Create `tests/golden/input.json` with representative data (CJK, emoji, highlight, multi-page)
  2. Run `python scripts/zeble_render.py tests/golden/input.json tests/golden/expected_css.png --theme-name default_dark`
  3. Run `python scripts/zeble_render.py tests/golden/input.json tests/golden/expected_pil.png --force-pil --theme-name default_dark`
  4. Run `python scripts/zeble_render.py tests/golden/input.json /dev/null --force-ascii --output-ascii tests/golden/expected_ascii.txt --theme-name default_dark`
  5. Store outputs as golden references
  6. Create `tests/golden/run_golden.sh` that re-renders and diffs
- **[Compatibility]** N/A
- **[Rollback]** Delete `tests/golden/`
- **[Test]**
  - syntax: `bash -n tests/golden/run_golden.sh`
  - smoke: `bash tests/golden/run_golden.sh` exits 0
  - golden: Outputs match pixel-for-pixel (CSS/PIL) or byte-for-byte (ASCII)
- **[DoD]** Three golden outputs exist; `run_golden.sh` passes

---

#### T-001: Fix broken `api/render_api.py` script reference

- **[ID]** T-001
- **[Category]** Detector (Input path fix)
- **[Priority]** P0
- **[Risk]** Low
- **[Source]** `api/render_api.py` L19: `DEFAULT_SCRIPT = ...scripts/zentable_renderer.py`
- **[Target]** `api/render_api.py` L19
- **[Action]**
  1. Change `"zentable_renderer.py"` → `"zentable_render.py"` (the existing symlink)
  2. Verify symlink resolves: `ls -la scripts/zentable_render.py`
- **[Compatibility]** `api/__init__.py` re-exports unchanged
- **[Rollback]** `git checkout api/render_api.py`
- **[Test]**
  - syntax: `python3 -m py_compile api/render_api.py`
  - smoke: `python3 -c "from api import render_table; print('OK')"`
  - golden: N/A
- **[DoD]** `render_table()` can locate the script; import succeeds

---

#### T-002: Create `scripts/zentable/` package skeleton

- **[ID]** T-002
- **[Category]** Infrastructure
- **[Priority]** P0
- **[Risk]** Low
- **[Source]** N/A
- **[Target]** `scripts/zentable/__init__.py`, all subdirectory `__init__.py` files
- **[Action]**
  1. `mkdir -p scripts/zentable/{input,transform,output/{ascii,css,pil},util}`
  2. Create empty `__init__.py` in each directory
  3. Verify: `python3 -c "import sys; sys.path.insert(0,'scripts'); import zentable; print('OK')"`
- **[Compatibility]** No existing code changes
- **[Rollback]** `rm -rf scripts/zentable`
- **[Test]**
  - syntax: `python3 -m py_compile scripts/zentable/__init__.py`
  - smoke: `python3 -c "import sys; sys.path.insert(0,'scripts'); from zentable.util import text"`
  - golden: `bash tests/golden/run_golden.sh` still passes (no behavior change)
- **[DoD]** All `__init__.py` exist; package imports without error

---

### Phase 1: Extract Utilities (P0)

---

#### T-100: Extract `zentable/util/text.py`

- **[ID]** T-100
- **[Category]** Engine (shared utility)
- **[Priority]** P0
- **[Risk]** Low
- **[Source]** `scripts/zeble_render.py`:
  - `is_emoji_modifier_or_joiner(char)` L2093-2106
  - `is_emoji(char)` L2109-2155
  - `replace_color_circles(text)` L2157-2168
  - `split_text_by_font(text)` L2170-2199
- **[Target]** `scripts/zentable/util/text.py`
- **[Action]**
  1. Copy 4 functions to `util/text.py`
  2. In `zeble_render.py`, replace function bodies with:
     ```python
     from zentable.util.text import is_emoji, is_emoji_modifier_or_joiner, replace_color_circles, split_text_by_font
     ```
  3. Remove original function definitions
  4. Verify no circular imports
- **[Compatibility]** All callers use internal imports; no external interface change
- **[Rollback]** `git checkout scripts/zeble_render.py && rm scripts/zentable/util/text.py`
- **[Test]**
  - syntax: `python3 -m py_compile scripts/zentable/util/text.py`
  - smoke: `python3 -c "from zentable.util.text import is_emoji; print(is_emoji('😀'))"`
  - golden: `bash tests/golden/run_golden.sh`
- **[DoD]** Functions extracted; golden test passes; `zeble_render.py` imports from new module

---

#### T-101: Extract `zentable/util/color.py`

- **[ID]** T-101
- **[Category]** Renderer (shared utility)
- **[Priority]** P0
- **[Risk]** Low
- **[Source]** `scripts/zeble_render.py`:
  - `parse_color(c)` L1413-1442
  - `hex_rgb(c)` L1444-1447 (depends on `parse_color`)
  - `_hex_to_chrome_bg(hex_color)` L799-806
- **[Target]** `scripts/zentable/util/color.py`
- **[Action]**
  1. Copy 3 functions to `util/color.py`
  2. In `zeble_render.py`, replace with import
  3. Remove original definitions
- **[Compatibility]** Internal only
- **[Rollback]** `git checkout scripts/zeble_render.py && rm scripts/zentable/util/color.py`
- **[Test]**
  - syntax: `python3 -m py_compile scripts/zentable/util/color.py`
  - smoke: `python3 -c "from zentable.util.color import parse_color; print(parse_color('#ff0000'))"`
  - golden: `bash tests/golden/run_golden.sh`
- **[DoD]** Functions extracted; golden test passes

---

### Phase 2: Extract Detector Layer — `zentable/input/` (P0)

---

#### T-200: Extract `zentable/input/loader.py`

- **[ID]** T-200
- **[Category]** Detector
- **[Priority]** P0
- **[Risk]** Low
- **[Source]** `scripts/zeble_render.py`:
  - `load_json(path)` L2407-2409
  - `normalise_data(data)` L2897-2922
- **[Target]** `scripts/zentable/input/loader.py`
- **[Action]**
  1. Copy 2 functions to `input/loader.py`
  2. `normalise_data` has no dependencies on other zeble_render functions
  3. `load_json` uses only `json` stdlib
  4. Replace in `zeble_render.py` with import
- **[Compatibility]** Internal only
- **[Rollback]** `git checkout scripts/zeble_render.py && rm scripts/zentable/input/loader.py`
- **[Test]**
  - syntax: `python3 -m py_compile scripts/zentable/input/loader.py`
  - smoke: `python3 -c "from zentable.input.loader import load_json, normalise_data; print('OK')"`
  - golden: `bash tests/golden/run_golden.sh`
- **[DoD]** Functions extracted; golden test passes

---

#### T-201: Extract `zentable/input/theme.py`

- **[ID]** T-201
- **[Category]** Detector
- **[Priority]** P0
- **[Risk]** Medium (path calculation)
- **[Source]** `scripts/zeble_render.py`:
  - `_PROJECT_ROOT` L2402, `THEMES_DIR` L2403, `CACHE_BASE` L2405
  - `_read_template_from_zip(zip_path)` L2411-2424
  - `load_theme_from_themes_dir(name, mode)` L2426-2445
  - `list_themes_in_dir(mode)` L2447-2464
  - `get_theme_source_path(name, mode)` L2466-2491
  - `_rmtree_safe(d)` L2493-2509
  - `ensure_theme_cache(name, mode)` L2511-2544
  - `get_theme(name, mode)` L2546-2565
- **[Target]** `scripts/zentable/input/theme.py`
- **[Action]**
  1. Copy all 8 functions + 3 constants to `input/theme.py`
  2. **Critical:** Recalculate `_PROJECT_ROOT` — file moves from `scripts/zeble_render.py` (depth 1) to `scripts/zentable/input/theme.py` (depth 3). Must use:
     ```python
     _PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
     ```
     Or better: find root by looking for `themes/` directory marker.
  3. `load_json` dependency: import from `zentable.input.loader`
  4. Replace in `zeble_render.py` with imports
- **[Compatibility]** `THEMES_DIR` and `CACHE_BASE` paths must resolve identically
- **[Rollback]** `git checkout scripts/zeble_render.py && rm scripts/zentable/input/theme.py`
- **[Test]**
  - syntax: `python3 -m py_compile scripts/zentable/input/theme.py`
  - smoke: `python3 -c "from zentable.input.theme import list_themes_in_dir; print(list_themes_in_dir('css'))"`
  - golden: `bash tests/golden/run_golden.sh`
- **[DoD]** Theme loading works from all entry points; golden test passes

---

### Phase 3: Extract Engine Layer — `zentable/transform/` (P1)

---

#### T-300: Extract `zentable/transform/cell.py`

- **[ID]** T-300
- **[Category]** Engine
- **[Priority]** P1
- **[Risk]** Low
- **[Source]** `scripts/zeble_render.py`:
  - `normalize_cell(cell)` L2640-2664
  - `_row_cells(row)` L2667-2673
  - `cell_text(cell)` L2836-2837
  - `_try_numeric(s)` L2676-2686
- **[Target]** `scripts/zentable/transform/cell.py`
- **[Action]**
  1. Copy 4 functions; `cell_text` depends on `normalize_cell` (same file, OK)
  2. These are the most cross-referenced functions (used by ASCII, CSS, PIL, Transform)
  3. All other modules import from here
- **[Compatibility]** Internal only
- **[Rollback]** `git checkout scripts/zeble_render.py && rm scripts/zentable/transform/cell.py`
- **[Test]**
  - syntax: `python3 -m py_compile scripts/zentable/transform/cell.py`
  - smoke: `python3 -c "from zentable.transform.cell import normalize_cell, cell_text; print(cell_text('hello'))"`
  - golden: `bash tests/golden/run_golden.sh`
- **[DoD]** Functions extracted; all importers updated; golden test passes

---

#### T-301: Extract `zentable/transform/highlight.py`

- **[ID]** T-301
- **[Category]** Engine
- **[Priority]** P1
- **[Risk]** Low
- **[Source]** `scripts/zeble_render.py`:
  - `_highlight_rule_matches(rule, cell_value)` L2689-2777
  - `resolve_cell_highlight(cell, ...)` L2780-2815
  - `_highlight_styles_to_css(theme)` L2818-2833
- **[Target]** `scripts/zentable/transform/highlight.py`
- **[Action]**
  1. Copy 3 functions
  2. `_highlight_rule_matches` depends on `_try_numeric` → import from `cell.py`
  3. `_highlight_styles_to_css` is CSS-specific but logically belongs with highlight data
- **[Compatibility]** Internal only
- **[Rollback]** `git checkout scripts/zeble_render.py && rm scripts/zentable/transform/highlight.py`
- **[Test]**
  - syntax: `python3 -m py_compile scripts/zentable/transform/highlight.py`
  - smoke: `python3 -c "from zentable.transform.highlight import resolve_cell_highlight; print('OK')"`
  - golden: `bash tests/golden/run_golden.sh`
- **[DoD]** Functions extracted; golden test passes

---

#### T-302: Extract `zentable/transform/transpose.py`

- **[ID]** T-302
- **[Category]** Engine
- **[Priority]** P1
- **[Risk]** Low
- **[Source]** `scripts/zeble_render.py`:
  - `transpose_table(data)` L2924-2959
- **[Target]** `scripts/zentable/transform/transpose.py`
- **[Action]**
  1. Copy function; depends on `cell_text` → import from `cell.py`
- **[Compatibility]** Internal only
- **[Rollback]** `git checkout scripts/zeble_render.py && rm scripts/zentable/transform/transpose.py`
- **[Test]**
  - syntax: `python3 -m py_compile scripts/zentable/transform/transpose.py`
  - smoke: `python3 -c "from zentable.transform.transpose import transpose_table; print('OK')"`
  - golden: `bash tests/golden/run_golden.sh`
- **[DoD]** Function extracted; golden test passes

---

#### T-303: Extract `zentable/transform/filter.py`

- **[ID]** T-303
- **[Category]** Engine
- **[Priority]** P1
- **[Risk]** Low
- **[Source]** `scripts/zeble_render.py`:
  - `_split_csv(text)` L2962-2963
  - `_header_index_map(headers)` L2966-2972
  - `_find_header_idx(headers, name)` L2975-2982
  - `_parse_row_filter_condition(expr)` L2985-3018
  - `_parse_filter_specs(filter_specs)` L3021-3069
  - `apply_filters(data, filter_specs)` L3072-3142
- **[Target]** `scripts/zentable/transform/filter.py`
- **[Action]**
  1. Copy 6 functions
  2. Dependencies: `_row_cells`, `cell_text` → import from `cell.py`
  3. `_highlight_rule_matches` → import from `highlight.py`
- **[Compatibility]** Internal only
- **[Rollback]** `git checkout scripts/zeble_render.py && rm scripts/zentable/transform/filter.py`
- **[Test]**
  - syntax: `python3 -m py_compile scripts/zentable/transform/filter.py`
  - smoke: `python3 -c "from zentable.transform.filter import apply_filters; print('OK')"`
  - golden: `bash tests/golden/run_golden.sh`
- **[DoD]** Functions extracted; golden test passes

---

#### T-304: Extract `zentable/transform/sort_page.py`

- **[ID]** T-304
- **[Category]** Engine
- **[Priority]** P1
- **[Risk]** Low
- **[Source]** `scripts/zeble_render.py`:
  - `_parse_page_spec(spec)` L2574-2603
  - `_resolve_page_list(total_rows, ...)` L2606-2629
  - `_page_output_path(path, page, pages)` L2632-2638
  - `_try_sort_numeric(value)` L3145-3162
  - `_parse_sort_specs(sort_by, sort_asc)` L3165-3190
  - `apply_sort_and_page(data, ...)` L3193-3252
  - `ROWS_PER_PAGE` L2571
- **[Target]** `scripts/zentable/transform/sort_page.py`
- **[Action]**
  1. Copy 6 functions + 1 constant
  2. Dependencies: `_row_cells`, `cell_text` → import from `cell.py`
- **[Compatibility]** Internal only
- **[Rollback]** `git checkout scripts/zeble_render.py && rm scripts/zentable/transform/sort_page.py`
- **[Test]**
  - syntax: `python3 -m py_compile scripts/zentable/transform/sort_page.py`
  - smoke: `python3 -c "from zentable.transform.sort_page import apply_sort_and_page; print('OK')"`
  - golden: `bash tests/golden/run_golden.sh`
- **[DoD]** Functions extracted; golden test passes

---

#### T-305: Extract `zentable/transform/wrap.py`

- **[ID]** T-305
- **[Category]** Engine
- **[Priority]** P1
- **[Risk]** Low
- **[Source]** `scripts/zeble_render.py`:
  - `_smart_wrap_text(text, limit)` L3255-3282
  - `apply_smart_wrap(data, width)` L3285-3330
- **[Target]** `scripts/zentable/transform/wrap.py`
- **[Action]**
  1. Copy 2 functions
  2. Dependencies: `_row_cells` → import from `cell.py`
- **[Compatibility]** Internal only
- **[Rollback]** `git checkout scripts/zeble_render.py && rm scripts/zentable/transform/wrap.py`
- **[Test]**
  - syntax: `python3 -m py_compile scripts/zentable/transform/wrap.py`
  - smoke: `python3 -c "from zentable.transform.wrap import apply_smart_wrap; print('OK')"`
  - golden: `bash tests/golden/run_golden.sh`
- **[DoD]** Functions extracted; golden test passes

---

### Phase 4: Extract Renderer Layer — `zentable/output/` (P1)

---

#### T-400: Extract `zentable/output/ascii/charwidth.py`

- **[ID]** T-400
- **[Category]** Renderer
- **[Priority]** P1
- **[Risk]** Low
- **[Source]** `scripts/zeble_render.py`:
  - `_is_zero_width(ch)` L92-104
  - `_classify_char(ch)` L106-122
  - `_clamp_width(w)` L124-130
  - `char_display_width(ch, calibration)` L132-162
  - `display_width(text, calibration)` L164-173
  - `_space_width(calibration)` L175-195
  - `calculate_column_widths(headers, rows, ...)` L197-205
- **[Target]** `scripts/zentable/output/ascii/charwidth.py`
- **[Action]**
  1. Copy 7 functions
  2. Dependencies: `_row_cells`, `cell_text` → import from `transform/cell.py`
  3. External: `unicodedata` (stdlib)
- **[Compatibility]** Internal only
- **[Rollback]** `git checkout scripts/zeble_render.py && rm scripts/zentable/output/ascii/charwidth.py`
- **[Test]**
  - syntax: `python3 -m py_compile scripts/zentable/output/ascii/charwidth.py`
  - smoke: `python3 -c "from zentable.output.ascii.charwidth import display_width; print(display_width('你好'))"`
  - golden: `bash tests/golden/run_golden.sh`
- **[DoD]** Functions extracted; golden test passes

---

#### T-401: Extract `zentable/output/ascii/renderer.py`

- **[ID]** T-401
- **[Category]** Renderer
- **[Priority]** P1
- **[Risk]** Medium
- **[Source]** `scripts/zeble_render.py`:
  - `ASCIIStyle` L45-50
  - `ASCII_STYLES` L53-90
  - `align_text(text, target_width, ...)` L207-222
  - `render_ascii(data, theme, ...)` L224-416
- **[Target]** `scripts/zentable/output/ascii/renderer.py`
- **[Action]**
  1. Copy class + constant + 2 functions (~230 lines)
  2. Dependencies:
     - `charwidth.py`: `display_width`, `_space_width`, `char_display_width`, `calculate_column_widths`
     - `transform/cell.py`: `_row_cells`, `cell_text`
- **[Compatibility]** Internal only
- **[Rollback]** `git checkout scripts/zeble_render.py && rm scripts/zentable/output/ascii/renderer.py`
- **[Test]**
  - syntax: `python3 -m py_compile scripts/zentable/output/ascii/renderer.py`
  - smoke: `python3 -c "from zentable.output.ascii.renderer import render_ascii; print('OK')"`
  - golden: `bash tests/golden/run_golden.sh` (ASCII output must match)
- **[DoD]** ASCII rendering produces identical output; golden test passes

---

#### T-410: Extract `zentable/output/css/crop.py`

- **[ID]** T-410
- **[Category]** Renderer
- **[Priority]** P1
- **[Risk]** Medium (PIL lazy imports)
- **[Source]** `scripts/zeble_render.py`:
  - `_make_png_background_transparent_chroma(...)` L530-555
  - `crop_to_content_bounds(png_path, ...)` L557-598
  - `_bottom_edge_has_content(png_path, ...)` L601-637
  - `_right_edge_metrics(png_path, ...)` L640-689
  - `_right_edge_has_content(png_path, ...)` L692-748
  - `crop_to_content_height(png_path, ...)` L751-796
- **[Target]** `scripts/zentable/output/css/crop.py`
- **[Action]**
  1. Copy 6 functions (~270 lines)
  2. **Keep local `from PIL import Image` inside each function** (preserves ASCII-only mode compatibility)
  3. No dependency on other zeble_render functions
- **[Compatibility]** Must work in environments without PIL (functions never called in ASCII mode)
- **[Rollback]** `git checkout scripts/zeble_render.py && rm scripts/zentable/output/css/crop.py`
- **[Test]**
  - syntax: `python3 -m py_compile scripts/zentable/output/css/crop.py`
  - smoke: Create test PNG, run `crop_to_content_bounds` on it
  - golden: `bash tests/golden/run_golden.sh` (CSS output must match)
- **[DoD]** Crop functions work identically; golden test passes

---

#### T-411: Extract `zentable/output/css/chrome.py`

- **[ID]** T-411
- **[Category]** Renderer
- **[Priority]** P1
- **[Risk]** High (global state, subprocess, file I/O)
- **[Source]** `scripts/zeble_render.py`:
  - `TRANSPARENT_BG_HEX` L528
  - `check_chrome_available()` L515-524
  - `render_css(html, output_path, ...)` L812-904
  - `measure_dom_scroll_width(html, ...)` L906-912 (+ dead code L982-1031)
  - `measure_dom_overflow(html, ...)` L914-981
  - `TemplateEngine` L418-508
- **[Target]** `scripts/zentable/output/css/chrome.py`
- **[Action]**
  1. Copy class + 5 functions + constant (~500 lines)
  2. **Refactor `render_css()`**: Return `{"render_ms": int, "viewport": (w,h)}` instead of writing globals `LAST_CSS_RENDER_MS`, `LAST_CSS_VIEWPORT`
  3. Dependencies:
     - `crop.py`: `crop_to_content_bounds` (for non-skip_crop path)
  4. Clean up dead code in `measure_dom_scroll_width` (lines after return)
- **[Compatibility]** `main()` must be updated to receive return dict instead of reading globals
- **[Rollback]** `git checkout scripts/zeble_render.py && rm scripts/zentable/output/css/chrome.py`
- **[Test]**
  - syntax: `python3 -m py_compile scripts/zentable/output/css/chrome.py`
  - smoke: `python3 -c "from zentable.output.css.chrome import check_chrome_available; print(check_chrome_available())"`
  - golden: `bash tests/golden/run_golden.sh` (CSS output must match)
- **[DoD]** Chrome rendering works; globals eliminated; golden test passes

---

#### T-412: Extract `zentable/output/css/viewport.py`

- **[ID]** T-412
- **[Category]** Renderer
- **[Priority]** P1
- **[Risk]** Low
- **[Source]** `scripts/zeble_render.py`:
  - `MAX_VIEWPORT_DIM` L1142
  - `_parse_font_size_px(style_str, default)` L1035-1040
  - `_parse_width_px(style_str)` L1042-1050
  - `_resolve_text_scale(width, ...)` L1056-1106
  - `_scale_css_styles_px(theme, scale)` L1109-1138
  - `estimate_css_viewport_width_height(data, theme)` L1144-1197
- **[Target]** `scripts/zentable/output/css/viewport.py`
- **[Action]**
  1. Copy constant + 5 functions (~160 lines)
  2. Dependencies:
     - `transform/cell.py`: `_row_cells`, `cell_text`
     - `output/pil/draw.py`: `measure_text_width` (cross-renderer dependency)
- **[Compatibility]** Internal only
- **[Rollback]** `git checkout scripts/zeble_render.py && rm scripts/zentable/output/css/viewport.py`
- **[Test]**
  - syntax: `python3 -m py_compile scripts/zentable/output/css/viewport.py`
  - smoke: `python3 -c "from zentable.output.css.viewport import estimate_css_viewport_width_height; print('OK')"`
  - golden: `bash tests/golden/run_golden.sh`
- **[DoD]** Viewport calculation works; golden test passes

---

#### T-413: Extract `zentable/output/css/renderer.py`

- **[ID]** T-413
- **[Category]** Renderer
- **[Priority]** P1
- **[Risk]** Medium
- **[Source]** `scripts/zeble_render.py`:
  - `_strip_alpha_from_css(css_text)` L1199-1249
  - `generate_css_html(data, theme, ...)` L1252-1363
  - `_inject_wrap_gap_css(html, gap_px)` L1366-1394
  - `build_css_rows_html(rows, theme, ...)` L2839-2895
- **[Target]** `scripts/zentable/output/css/renderer.py`
- **[Action]**
  1. Copy 4 functions (~300 lines)
  2. Dependencies:
     - `chrome.py`: `TemplateEngine`
     - `viewport.py`: `_parse_width_px`
     - `transform/cell.py`: `_row_cells`, `normalize_cell`
     - `transform/highlight.py`: `resolve_cell_highlight`, `_highlight_styles_to_css`
  3. External: `html` module (stdlib)
- **[Compatibility]** Internal only
- **[Rollback]** `git checkout scripts/zeble_render.py && rm scripts/zentable/output/css/renderer.py`
- **[Test]**
  - syntax: `python3 -m py_compile scripts/zentable/output/css/renderer.py`
  - smoke: `python3 -c "from zentable.output.css.renderer import generate_css_html; print('OK')"`
  - golden: `bash tests/golden/run_golden.sh`
- **[DoD]** CSS HTML generation identical; golden test passes

---

#### T-420: Extract `zentable/output/pil/font.py`

- **[ID]** T-420
- **[Category]** Renderer
- **[Priority]** P1
- **[Risk]** Medium (font cache globals)
- **[Source]** `scripts/zeble_render.py`:
  - `FONT_CJK` L1454, `FONT_CJK_LIST` L1455-1462, `FONT_EMOJI_LIST` L1464-1477
  - `_font_cache` L1480, `_emoji_font_available` L1481
  - `get_font_cjk(size)` L1483-1499
  - `_detect_emoji_font()` L1501-1547
  - `get_font_emoji(size)` L1549-1570
  - `is_color_emoji_font()` L1572-1575
  - `get_font(size)` L1577-1579
- **[Target]** `scripts/zentable/output/pil/font.py`
- **[Action]**
  1. Copy 5 functions + constants + 2 cache globals (~100 lines)
  2. Module-level `_font_cache` and `_emoji_font_available` become the singletons
  3. External: `PIL.ImageFont`, `os`, `glob`
- **[Compatibility]** Internal only
- **[Rollback]** `git checkout scripts/zeble_render.py && rm scripts/zentable/output/pil/font.py`
- **[Test]**
  - syntax: `python3 -m py_compile scripts/zentable/output/pil/font.py`
  - smoke: `python3 -c "from zentable.output.pil.font import get_font_cjk; f=get_font_cjk(14); print(f)"`
  - golden: `bash tests/golden/run_golden.sh`
- **[DoD]** Font loading works; cache functional; golden test passes

---

#### T-421: Extract `zentable/output/pil/draw.py`

- **[ID]** T-421
- **[Category]** Renderer
- **[Priority]** P1
- **[Risk]** Low
- **[Source]** `scripts/zeble_render.py`:
  - `measure_text_width(text, font_size)` L2201-2212
  - `_fill_for_draw(fill_color, img_mode)` L2214-2220
  - `draw_text_with_mixed_fonts(draw, ...)` L2223-2252
  - `_align_x(cell_left, cell_width, text_width, align, padding)` L2255-2261
  - `draw_text_aligned(draw, text, ...)` L2264-2271
- **[Target]** `scripts/zentable/output/pil/draw.py`
- **[Action]**
  1. Copy 5 functions (~80 lines)
  2. Dependencies:
     - `font.py`: `get_font_cjk`, `get_font_emoji`
     - `util/text.py`: `split_text_by_font`
     - `util/color.py`: `parse_color`
- **[Compatibility]** Internal only; `measure_text_width` also used by CSS viewport
- **[Rollback]** `git checkout scripts/zeble_render.py && rm scripts/zentable/output/pil/draw.py`
- **[Test]**
  - syntax: `python3 -m py_compile scripts/zentable/output/pil/draw.py`
  - smoke: `python3 -c "from zentable.output.pil.draw import measure_text_width; print(measure_text_width('hello', 14))"`
  - golden: `bash tests/golden/run_golden.sh`
- **[DoD]** Drawing functions work; golden test passes

---

#### T-422: Extract `zentable/output/pil/renderer.py`

- **[ID]** T-422
- **[Category]** Renderer
- **[Priority]** P1
- **[Risk]** Medium
- **[Source]** `scripts/zeble_render.py`:
  - `PILStyle` L1404-1411
  - `render_pil(data, theme, custom_params)` L2273-2394
- **[Target]** `scripts/zentable/output/pil/renderer.py`
- **[Action]**
  1. Copy class + function (~130 lines)
  2. Dependencies:
     - `draw.py`: `measure_text_width`, `draw_text_aligned`
     - `font.py`: `get_font_cjk`, `get_font_emoji`
     - `util/color.py`: `parse_color`
     - `transform/cell.py`: `_row_cells`, `cell_text`
- **[Compatibility]** Internal only
- **[Rollback]** `git checkout scripts/zeble_render.py && rm scripts/zentable/output/pil/renderer.py`
- **[Test]**
  - syntax: `python3 -m py_compile scripts/zentable/output/pil/renderer.py`
  - smoke: `python3 -c "from zentable.output.pil.renderer import render_pil; print('OK')"`
  - golden: `bash tests/golden/run_golden.sh` (PIL output must match)
- **[DoD]** PIL rendering identical; golden test passes

---

#### T-423: Extract `zentable/output/pil/blueprint.py`

- **[ID]** T-423
- **[Category]** Renderer
- **[Priority]** P2
- **[Risk]** Medium
- **[Source]** `scripts/zeble_render.py`:
  - `render_ascii_blueprint_pil(blueprint, img_path, unit_px)` L1581-2091
- **[Target]** `scripts/zentable/output/pil/blueprint.py`
- **[Action]**
  1. Copy function (~510 lines) — the largest single function
  2. Dependencies:
     - `draw.py`: `draw_text_with_mixed_fonts`, `measure_text_width`
     - `font.py`: `get_font_cjk`
  3. External: `PIL.Image`, `PIL.ImageDraw`, `PIL.ImageFont`
- **[Compatibility]** Internal only (called from ASCII debug flow in main)
- **[Rollback]** `git checkout scripts/zeble_render.py && rm scripts/zentable/output/pil/blueprint.py`
- **[Test]**
  - syntax: `python3 -m py_compile scripts/zentable/output/pil/blueprint.py`
  - smoke: ASCII debug mode with `stage1_pil_preview=1` must produce blueprint image
  - golden: `bash tests/golden/run_golden.sh`
- **[DoD]** Blueprint PIL visualization works; golden test passes

---

### Phase 5: Refactor Orchestration (P2)

---

#### T-500: Slim down `main()` — import from modules

- **[ID]** T-500
- **[Category]** Orchestration
- **[Priority]** P2
- **[Risk]** Medium
- **[Source]** `scripts/zeble_render.py` `main()` L3336-4176
- **[Target]** `scripts/zeble_render.py` (same file, slimmed)
- **[Action]**
  1. Replace all inline function calls with imports from `zentable.*` modules
  2. `main()` remains in `zeble_render.py` (CLI contract preserved)
  3. Remove all extracted function definitions from the file
  4. Expected result: `zeble_render.py` shrinks from ~4,176 lines to ~900 lines (main + imports)
- **[Compatibility]** CLI interface 100% unchanged
- **[Rollback]** `git checkout scripts/zeble_render.py`
- **[Test]**
  - syntax: `python3 -m py_compile scripts/zeble_render.py`
  - smoke: All three PHP endpoints render successfully
  - golden: `bash tests/golden/run_golden.sh`
- **[DoD]** `zeble_render.py` is ≤1,000 lines; all golden tests pass

---

### Phase 6: Cleanup (P2)

---

#### T-600: Remove dead Python files

- **[ID]** T-600
- **[Category]** Infrastructure
- **[Priority]** P2
- **[Risk]** Low
- **[Source]** Dead files:
  - `doc/zeble.py` (633 lines — clone of `scripts/zeble.py`)
  - `doc/zeble_render.py` (1,446 lines — old snapshot)
  - `doc/zentable_render.py` (966 lines — early version)
  - `doc/table_detect.py` (129 lines — old version)
  - `doc/smart_table_output.py` (163 lines — broken imports)
  - `doc/reproduce_issue.py` (17 lines — one-off)
  - `doc/gen_test_data.py` (55 lines — one-off)
- **[Target]** `doc/archive/deprecated_code/` (move, don't delete)
- **[Action]**
  1. `mkdir -p doc/archive/deprecated_code`
  2. Move all 7 files to `doc/archive/deprecated_code/`
  3. Update `doc/archive/README.md` to list them
- **[Compatibility]** No external callers; safe to move
- **[Rollback]** `git checkout doc/`
- **[Test]**
  - syntax: N/A
  - smoke: All PHP endpoints still work
  - golden: `bash tests/golden/run_golden.sh`
- **[DoD]** Dead files archived; no broken imports anywhere

---

#### T-601: Deprecate `scripts/zeble.py`

- **[ID]** T-601
- **[Category]** Infrastructure
- **[Priority]** P2
- **[Risk]** Low
- **[Source]** `scripts/zeble.py` (634 lines — legacy PIL renderer)
- **[Target]** `doc/archive/deprecated_code/zeble.py`
- **[Action]**
  1. Verify `gentable.php` is the only caller (legacy, no frontend caller)
  2. Add deprecation notice to top of `scripts/zeble.py`
  3. Move to archive
  4. Update `gentable.php` to return deprecation warning in JSON
- **[Compatibility]** `gentable.php` still responds (with warning); no frontend caller exists
- **[Rollback]** `git checkout scripts/zeble.py gentable.php`
- **[Test]**
  - syntax: `php -l gentable.php`
  - smoke: `curl -s -X POST localhost/zenTable/gentable.php` returns JSON
  - golden: N/A (legacy endpoint)
- **[DoD]** `zeble.py` archived; `gentable.php` warns about deprecation

---

#### T-602: Update stale documentation

- **[ID]** T-602
- **[Category]** Infrastructure
- **[Priority]** P2
- **[Risk]** Low
- **[Source]** Stale docs:
  - `doc/DEVELOPMENT.md` — obsolete architecture
  - `doc/INTEGRATION.md` — Python file with .md extension
  - `doc/SKILL_PY_PROGRAMS.md` — 4 naming variants mixed
  - `doc/ZEBLE_FLOW.md` — references removed paths
  - `doc/SPECIFICATION.md` — file structure outdated
- **[Target]** Same files (update in-place) or archive
- **[Action]**
  1. Archive `doc/DEVELOPMENT.md` and `doc/INTEGRATION.md` (obsolete)
  2. Update remaining docs to use canonical `zentable` naming
  3. Update file structure references to match new module layout
- **[Compatibility]** Documentation only; no code impact
- **[Rollback]** `git checkout doc/`
- **[Test]**
  - syntax: N/A
  - smoke: N/A
  - golden: N/A
- **[DoD]** All active docs reference correct file paths and canonical names

---

#### T-603: Deduplicate `table_renderer.py` page logic

- **[ID]** T-603
- **[Category]** Engine
- **[Priority]** P2
- **[Risk]** Medium
- **[Source]** `skills/zentable/table_renderer.py`:
  - `_parse_page_spec()` L100 — duplicates `zeble_render.py` L2574
  - `_resolve_pages()` L132 — duplicates `zeble_render.py` L2606
- **[Target]** `skills/zentable/table_renderer.py`
- **[Action]**
  1. Add `scripts/` to `sys.path` in `table_renderer.py`
  2. Replace duplicated functions with: `from zentable.transform.sort_page import _parse_page_spec, _resolve_page_list`
  3. Adapt calling code for any signature differences
- **[Compatibility]** `table_renderer.py` CLI interface unchanged
- **[Rollback]** `git checkout skills/zentable/table_renderer.py`
- **[Test]**
  - syntax: `python3 -m py_compile skills/zentable/table_renderer.py`
  - smoke: `python3 skills/zentable/table_renderer.py --help`
  - golden: Run skill with multi-page input
- **[DoD]** No duplicated page logic; skill produces identical output

---

#### T-604: Deduplicate OCR row normalization

- **[ID]** T-604
- **[Category]** Detector
- **[Priority]** P2
- **[Risk]** Medium
- **[Source]**
  - `api/zentable_service.py`: `_paddle_result_to_rows()` L55
  - `api/paddleocr_service.py`: `_normalize_rows()` L45
  - `api/ocr_openvino_service.py`: `_to_rows()` L20
- **[Target]** `api/ocr_normalize.py` (new shared module)
- **[Action]**
  1. Create `api/ocr_normalize.py` with unified normalization function
  2. Update all 3 service files to import from shared module
  3. Consider deprecating `ocr_openvino_service.py` (covered by `paddleocr_service.py`)
- **[Compatibility]** All FastAPI endpoints unchanged
- **[Rollback]** `git checkout api/`
- **[Test]**
  - syntax: `python3 -m py_compile api/ocr_normalize.py`
  - smoke: `/health` endpoint on each service
  - golden: OCR output format unchanged
- **[DoD]** Single normalization function; all services produce identical output
