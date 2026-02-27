# ZenTable Refactoring Risk Register

> Generated: 2026-02-27 | Based on actual code analysis, not documentation.

---

## Risk Matrix

| ID | Risk | Severity | Likelihood | Impact Area | Mitigation |
|---|---|---|---|---|---|
| R01 | Breaking PHP → Python call chain | **Critical** | Medium | All rendering | Preserve symlinks; test all 3 gentable_*.php |
| R02 | Breaking OpenClaw Skill subprocess | **Critical** | Medium | Skill rendering | Preserve `skills/zentable/zentable_renderer.py` symlink |
| R03 | Import path changes break FastAPI | **High** | Medium | API services | Maintain `api/__init__.py` re-exports |
| R04 | Global state (`LAST_CSS_*`) lost during module split | **High** | High | CSS render metadata | Use module-level state or return values |
| R05 | PIL lazy import pattern broken | **Medium** | Medium | PIL/CSS rendering | Keep conditional imports in output modules |
| R06 | Theme cache path (`CACHE_BASE`) miscalculated after move | **High** | Medium | All CSS rendering | Use `_PROJECT_ROOT` relative; test theme loading |
| R07 | `calibrate_analyze.py` root-level position assumed by PHP | **Medium** | Low | Calibration flow | Keep in root or update PHP path |
| R08 | `main()` CLI interface changes | **Critical** | Low | All PHP callers | No CLI interface changes allowed |
| R09 | Circular imports in new module structure | **Medium** | High | All | Careful dependency ordering; shared types in `util/` |
| R10 | `js/app.js` fetch URLs break | **Low** | Low | Frontend | PHP endpoints unchanged = JS safe |

---

## Detailed Risk Analysis

### R01: PHP → Python Call Chain (CRITICAL)

**Current flow:**
```
gentable_css.php → shell_exec("xvfb-run -a python scripts/zentable_render.py ...")
gentable_pil.php → shell_exec("python scripts/zentable_render.py ... --force-pil")
gentable_ascii.php → shell_exec("python scripts/zentable_render.py ... --force-ascii")
```

**What could break:**
- Renaming/moving `scripts/zentable_render.py`
- Breaking the symlink `scripts/zentable_render.py → zentable_render.py`
- Changing `main()` CLI argument interface
- Changing exit codes or stdout/stderr contract

**Mitigation:**
1. Never modify the symlink `scripts/zentable_render.py`
2. Keep `main()` as the entry point with identical CLI interface
3. Internal refactoring only — `main()` calls `pipeline.run()` internally
4. Test: `python scripts/zentable_render.py <test.json> <out.png>` must produce identical output

**Rollback:**
- `git checkout scripts/zentable_render.py` restores original monolith
- Symlinks are not changed, so PHP callers remain intact

---

### R02: Skill Subprocess Call (CRITICAL)

**Current flow:**
```
table_renderer.py → subprocess → skills/zentable/zentable_renderer.py (symlink → scripts/zentable_render.py)
```

**What could break:**
- Removing `zentable_render.py` before updating symlink target
- Module imports that fail when run from `skills/zentable/` directory

**Mitigation:**
1. Symlink `skills/zentable/zentable_renderer.py` must always resolve
2. `scripts/zentable_render.py` must remain a valid standalone CLI script
3. Test: `python skills/zentable/zentable_renderer.py <test.json> <out.png>` from skill directory

**Rollback:** Same as R01.

---

### R03: API Import Paths (HIGH)

**Current state:**
```python
# api/render_api.py L19 — ALREADY BROKEN
DEFAULT_SCRIPT = os.path.join(_PROJECT_ROOT, "scripts", "zentable_renderer.py")
```

**Note:** This reference is currently broken (file does not exist). Should be `zentable_render.py` (without trailing "er").

**Mitigation:**
1. Fix the broken reference as part of Phase 0
2. Ensure `api/__init__.py` re-exports remain stable
3. Test: `from api import render_table, run_render` must work

**Rollback:** Revert `api/render_api.py` single line.

---

### R04: Global Mutable State (HIGH)

**Current globals:**
```python
LAST_CSS_RENDER_MS = None   # L808 — written by render_css(), read by main()
LAST_CSS_VIEWPORT = None    # L809 — written by render_css(), read by main()
_font_cache = {}            # L1480 — PIL font cache
_emoji_font_available = None # L1481 — emoji font detection cache
```

**What could break:**
- Moving `render_css()` to `output/css/chrome.py` while `main()` reads globals from `zentable_render.py`
- Moving PIL font functions to `output/pil/font.py` loses cache singleton

**Mitigation:**
1. `render_css()` should return metadata dict instead of writing globals
2. Font cache should be module-level in `output/pil/font.py`
3. `main()` receives return values instead of reading globals

**Rollback:** Revert module extraction.

---

### R05: PIL Lazy Import Pattern (MEDIUM)

**Current pattern:** 6 functions do `from PIL import Image` locally to avoid import failure when PIL is not installed (ASCII-only mode).

**What could break:**
- Moving these functions to `output/css/crop.py` or `output/pil/` where PIL is imported at module level
- ASCII-only environments would fail on `import zentable.output.css.crop`

**Mitigation:**
1. Keep lazy imports in crop/image functions
2. Or: only import `output.css` and `output.pil` when mode requires it
3. Test: `python scripts/zentable_render.py <json> <out.txt> --force-ascii` must work without PIL installed

**Rollback:** Revert file moves.

---

### R06: Theme Cache Path (HIGH)

**Current:**
```python
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # L2402
THEMES_DIR = os.path.join(_PROJECT_ROOT, "themes")                          # L2403
CACHE_BASE = os.environ.get("ZENTABLE_THEME_CACHE", os.path.join(_PROJECT_ROOT, ".theme_cache"))
```

**What could break:**
- Moving code to `zentable/input/theme.py` changes `__file__` location
- `_PROJECT_ROOT` calculation would point to wrong directory

**Mitigation:**
1. Calculate `_PROJECT_ROOT` from repo root marker (e.g., presence of `themes/` directory)
2. Or: pass project root as parameter / environment variable
3. Test: Theme loading from all 3 PHP entry points

**Rollback:** Revert theme module; restore inline code.

---

### R08: CLI Interface Contract (CRITICAL)

**The CLI interface of `zentable_render.py` is a public API.** PHP files construct command lines with specific arguments. Any change to argument names, positions, or behavior is a breaking change.

**Current contract (must not change):**
```
python zentable_render.py <data.json> <output.png> [options]

Required positional:
  argv[1] = data JSON file path
  argv[2] = output file path

Options: --force-pil, --force-css, --force-ascii, --theme, --theme-name,
         --page, --per-page, --sort, --asc, --desc, --transparent, --tt,
         --no-tt, --bg, --width, --text-scale, --text-scale-max, --scale,
         --fill-width, --output-ascii, --params, --calibration,
         --transpose, --cc, --filter, --f, --smart-wrap, --no-smart-wrap,
         --nosw, --auto-height, --auto-width, --no-auto-width, --no-aw,
         --auto-height-max, --auto-width-max, --wrap-gap, --all,
         --debug-auto-width, --debug-auto-width-strip

Exit codes:
  0 = success
  1 = render failure
  2 = invalid page spec

Stdout: ASCII output (when --force-ascii without --output-ascii)
Stderr: Status messages (🖥️ 渲染模式:, ✅ 已保存:, ❌ 失敗, etc.)
```

**Mitigation:** CLI parsing stays in `zentable_render.py::main()`. Internal refactoring only.

---

### R09: Circular Imports (MEDIUM)

**Likely circular dependency chains after splitting:**

1. `output/css/renderer.py` → `transform/highlight.py` → `transform/normalize.py` (OK, one-way)
2. `output/css/viewport.py` → `output/pil/draw.py` (via `measure_text_width`) → `util/text.py` (OK)
3. `output/ascii/renderer.py` → `output/ascii/charwidth.py` ← `output/pil/blueprint.py` (potential cycle if blueprint imports renderer)

**Mitigation:**
1. `util/` modules must have zero imports from `input/`, `transform/`, `output/`
2. `transform/` may import from `util/` only
3. `output/` may import from `util/` and `transform/`
4. `input/` may import from `util/` only
5. No cross-imports within `output/ascii/`, `output/css/`, `output/pil/` submodules

---

## Summary: Risk-Ordered Action Priorities

| Priority | Action | Mitigates |
|---|---|---|
| **P0** | Fix `api/render_api.py` broken script path | R03 |
| **P0** | Verify all symlinks before any refactoring | R01, R02 |
| **P0** | Create golden-test baseline (render all 3 modes with fixed input) | R01, R08 |
| **P1** | Extract `util/` first (zero-risk, no callers change) | R09 |
| **P1** | Extract `transform/` (no external callers, internal only) | R09 |
| **P1** | Refactor `render_css()` to return metadata instead of globals | R04 |
| **P2** | Extract `input/` (theme path calculation needs care) | R06 |
| **P2** | Extract `output/` submodules (PIL lazy import needs care) | R05 |
| **P3** | Slim down `main()` to use `pipeline.run()` | R08 |
