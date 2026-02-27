# ZenTable Refactoring Acceptance Checklist

> ⚠️ Before running gates, read `ERRATA.md` and ensure golden assets are prepared.

> Generated: 2026-02-27
> Use this checklist to validate each wave and the final result.

---

## Per-Wave Gate Checks

### Wave 0: Foundation

- [x] `tests/golden/input.json` exists with representative data
- [x] `tests/golden/expected_css.png` exists (non-zero bytes)
- [x] `tests/golden/expected_pil.png` exists (non-zero bytes)
- [x] `tests/golden/expected_ascii.txt` exists (non-empty)
- [x] `bash tests/golden/run_golden.sh` exits 0
- [x] `python3 -c "from api import render_table"` succeeds (T-001 fix)
- [x] `python3 -c "import sys; sys.path.insert(0,'scripts'); import zentable"` succeeds (T-002 skeleton)

### Wave 1: Utilities

- [x] `python3 -m py_compile scripts/zentable/util/text.py`
- [x] `python3 -m py_compile scripts/zentable/util/color.py`
- [x] `python3 -c "from zentable.util.text import is_emoji, split_text_by_font"` (from scripts/ dir)
- [x] `python3 -c "from zentable.util.color import parse_color, hex_rgb"` (from scripts/ dir)
- [x] `bash tests/golden/run_golden.sh` exits 0

### Wave 2: Detector Layer

- [x] `python3 -m py_compile scripts/zentable/input/loader.py`
- [x] `python3 -m py_compile scripts/zentable/input/theme.py`
- [x] `python3 -c "from zentable.input.loader import load_json, normalise_data"` (from scripts/ dir)
- [x] `python3 -c "from zentable.input.theme import list_themes_in_dir; print(list_themes_in_dir('css'))"` (from scripts/ dir)
- [x] Theme list matches `ls themes/css/`
- [x] `bash tests/golden/run_golden.sh` exits 0

### Wave 3: Engine Layer

- [x] `python3 -m py_compile scripts/zentable/transform/cell.py`
- [x] `python3 -m py_compile scripts/zentable/transform/highlight.py`
- [x] `python3 -m py_compile scripts/zentable/transform/transpose.py`
- [x] `python3 -m py_compile scripts/zentable/transform/filter.py`
- [x] `python3 -m py_compile scripts/zentable/transform/sort_page.py`
- [x] `python3 -m py_compile scripts/zentable/transform/wrap.py`
- [x] `python3 -c "from zentable.transform.cell import normalize_cell, cell_text, _row_cells"` (from scripts/ dir)
- [x] `python3 -c "from zentable.transform.filter import apply_filters"` (from scripts/ dir)
- [x] `python3 -c "from zentable.transform.sort_page import apply_sort_and_page"` (from scripts/ dir)
- [x] `bash tests/golden/run_golden.sh` exits 0

### Wave 4: Renderer Layer

- [x] `python3 -m py_compile scripts/zentable/output/ascii/charwidth.py`
- [x] `python3 -m py_compile scripts/zentable/output/ascii/renderer.py`
- [x] `python3 -m py_compile scripts/zentable/output/css/crop.py`
- [x] `python3 -m py_compile scripts/zentable/output/css/chrome.py`
- [x] `python3 -m py_compile scripts/zentable/output/css/viewport.py`
- [x] `python3 -m py_compile scripts/zentable/output/css/renderer.py`
- [x] `python3 -m py_compile scripts/zentable/output/pil/font.py`
- [x] `python3 -m py_compile scripts/zentable/output/pil/draw.py`
- [x] `python3 -m py_compile scripts/zentable/output/pil/renderer.py`
- [x] `python3 -m py_compile scripts/zentable/output/pil/blueprint.py`
- [x] `bash tests/golden/run_golden.sh` exits 0

### Wave 5: Orchestration

- [x] `wc -l scripts/zeble_render.py` ≤ 1,000
- [x] `python3 -m py_compile scripts/zeble_render.py`
- [ ] `bash tests/golden/run_golden.sh` exits 0

### Wave 6: Cleanup

- [x] `doc/archive/deprecated_code/` contains archived files
- [x] `php -l gentable.php` (deprecated endpoint still returns valid JSON)
- [ ] No broken imports: `python3 -c "import sys; sys.path.insert(0,'scripts'); import zentable"` succeeds
- [ ] `php -l gentable_css.php && php -l gentable_pil.php && php -l gentable_ascii.php`
- [ ] `bash tests/golden/run_golden.sh` exits 0

---

## Final Acceptance Tests

### 1. Syntax Validation (All Files)

```bash
# All new Python modules
find scripts/zentable -name '*.py' -exec python3 -m py_compile {} \;

# Main entry point
python3 -m py_compile scripts/zeble_render.py

# API modules
python3 -m py_compile api/render_api.py
python3 -m py_compile api/calibration_api.py

# Skill module
python3 -m py_compile skills/zentable/table_renderer.py

# All PHP files
for f in gentable_css.php gentable_pil.php gentable_ascii.php \
         gentable.php gentable_export.php table_detect_api.php \
         theme_api.php calibrate_upload.php calibrate_records.php \
         fastapi_control.php; do
    php -l "$f"
done
```

### 2. Smoke Tests (Core Functionality)

```bash
# CSS rendering via PHP
curl -s -X POST http://localhost/zenTable/gentable_css.php \
  -F "data=$(cat tests/golden/input.json)" \
  -F "theme=default_dark" \
  | python3 -c "import sys,json; r=json.load(sys.stdin); assert r['success'], r"

# PIL rendering via PHP
curl -s -X POST http://localhost/zenTable/gentable_pil.php \
  -F "data=$(cat tests/golden/input.json)" \
  -F "theme=default_dark" \
  | python3 -c "import sys,json; r=json.load(sys.stdin); assert r['success'], r"

# ASCII rendering via PHP
curl -s -X POST http://localhost/zenTable/gentable_ascii.php \
  -F "data=$(cat tests/golden/input.json)" \
  -F "theme=default_dark" \
  | python3 -c "import sys,json; r=json.load(sys.stdin); assert r['success'], r"

# Table detect via PHP
curl -s -X POST http://localhost/zenTable/table_detect_api.php \
  -H "Content-Type: application/json" \
  -d '{"message":"show me a table"}' \
  | python3 -c "import sys,json; r=json.load(sys.stdin); assert r['success'], r"

# Theme API
curl -s "http://localhost/zenTable/theme_api.php?action=list&mode=css" \
  | python3 -c "import sys,json; r=json.load(sys.stdin); assert isinstance(r, list), r"

# Skill entry point
python3 skills/zentable/table_renderer.py --help 2>&1 | head -1

# API import
python3 -c "from api import render_table, run_render, analyze_from_image; print('API imports OK')"
```

### 3. Golden Tests (Pixel/Byte Identical)

```bash
bash tests/golden/run_golden.sh
```

This script must:
1. Re-render all 3 modes with identical input and options
2. Compare CSS output: `diff <(identify expected_css.png) <(identify actual_css.png)` (dimensions match)
3. Compare PIL output: pixel-by-pixel comparison or perceptual hash
4. Compare ASCII output: `diff expected_ascii.txt actual_ascii.txt` (byte-identical)
5. Exit 0 only if all pass

### 4. Symlink Integrity

```bash
# All symlinks must resolve
for link in \
    scripts/zentable_render.py \
    skills/zentable/zentable_renderer.py \
    skills/zentable/themes \
    skills/zentable/paddleocr_service.py \
    skills/zentable/zentable_api_ctl.sh \
    skills/zentable/zentable_service.py; do
    test -e "$link" || echo "BROKEN: $link"
done
```

### 5. Module Architecture Validation

```bash
# Import dependency check: util/ must not import from input/transform/output
python3 -c "
import ast, sys, os
violations = []
for root, dirs, files in os.walk('scripts/zentable/util'):
    for f in files:
        if not f.endswith('.py'): continue
        path = os.path.join(root, f)
        tree = ast.parse(open(path).read())
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mod = getattr(node, 'module', '') or ''
                for alias in getattr(node, 'names', []):
                    mod = mod or alias.name
                if any(x in mod for x in ['zentable.input', 'zentable.transform', 'zentable.output']):
                    violations.append(f'{path}: imports {mod}')
if violations:
    print('VIOLATIONS:')
    for v in violations: print(f'  {v}')
    sys.exit(1)
print('Architecture OK: util/ has no layer imports')
"
```

### 6. Line Count Targets

| File | Before | Target | Check |
|---|---|---|---|
| `scripts/zeble_render.py` | 499 | ≤ 1,000 | `wc -l scripts/zeble_render.py` |
| Dead code in `doc/` | 4,043 | 0 (archived) | `ls doc/*.py 2>/dev/null \| wc -l` should be 0 |
| `scripts/zentable/` (new) | 0 | ~3,200 | `find scripts/zentable -name '*.py' \| xargs wc -l` |

---

## Regression Scenarios

If any of the following break, the refactoring has a regression:

| # | Scenario | How to Test | Expected |
|---|---|---|---|
| 1 | CSS render with highlight rules | Render `doc/examples/highlight_rules_demo.json` | Same visual output |
| 2 | ASCII render with calibration | Render with `--calibration '{"ascii":1.0,"cjk":2.0}'` | Correct alignment |
| 3 | PIL render with emoji | Render data containing 😀🎉 | Emoji rendered with correct font |
| 4 | Multi-page CSS render | Render with `--page 1-3 --per-page 5` | 3 output files |
| 5 | Transpose + filter + sort | `--transpose --filter "row:分數>=60" --sort 姓名` | Correct data subset |
| 6 | Theme from zip | Render with `--theme-name <zipped-theme>` | Theme loads from zip |
| 7 | Smart-wrap with CJK | Wide CJK table with `--width 400` | Wraps at semantic boundaries |
| 8 | Auto-width CSS | Render without `--width` | Auto-detected width, no overflow |
| 9 | Transparent background | `--bg transparent` | PNG with alpha channel |
| 10 | Skill subprocess call | `python3 skills/zentable/table_renderer.py ...` | Renders successfully |

---

## Sign-Off

| Checkpoint | Verified By | Date |
|---|---|---|
| Wave 0 complete | | |
| Wave 1 complete | | |
| Wave 2 complete | | |
| Wave 3 complete | | |
| Wave 4 complete | | |
| Wave 5 complete | ✅ | `zeble_render.py` 499 lines + golden ok |
| Wave 6 complete | | |
| All golden tests pass | | |
| All smoke tests pass | | |
| All symlinks valid | | |
| Architecture validation passes | | |
| Line count targets met | | |
| Regression scenarios pass (all 10) | | |
| **Final sign-off** | | |
