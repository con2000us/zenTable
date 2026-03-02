# Naming Migration Plan (Completed through Phase 2)

Last updated: 2026-02-27

## Canonical naming

Use **`zentable`** as the single canonical project identifier for code/runtime names.

- code/module/file: `zentable`
- product display: `ZenTable`

## Phase status

- ✅ Phase 1: compatibility-first normalization
- ✅ Phase 1.2: runtime/docs consistency updates
- ✅ Phase 2: legacy runtime alias cleanup + hard rename completion

## Phase 2 completed actions

1. Runtime renderer filename converged to canonical:
   - active entry: `scripts/zentable_render.py`
   - legacy `scripts/zeble_render.py` removed
2. Skill symlink updated:
   - `skills/zentable/zentable_renderer.py -> scripts/zentable_render.py`
3. Legacy `zeble.py` pipeline retired/archived:
   - `scripts/zeble.py` moved to `doc/archive/deprecated_code/zeble.py`
   - `gentable.php` now returns explicit deprecation JSON
4. Broken legacy aliases removed:
   - removed stale `zenble-renderer.py`
   - removed stale `zentable.py` symlink to old `scripts/zeble.py`

## Compatibility kept intentionally

- Deployment root path remains `/var/www/html/zenTable`
- URL response path remains `/zenTable/...` (deployment compatibility)

## Validation checklist (Phase 2)

- [x] `python3 -m py_compile scripts/zentable_render.py`
- [x] `bash tests/golden/run_golden.sh`
- [x] skill wrapper path resolves to canonical renderer
- [x] no active runtime caller depends on `scripts/zeble_render.py`
