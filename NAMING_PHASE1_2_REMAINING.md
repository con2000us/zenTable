# Naming Phase 1.2 Remaining Checklist

Last updated: 2026-02-27

## Status

Phase 1.2 items are complete, and the deferred Phase 2 cleanup has now been executed.

## Completed Phase 2 items

- [x] Hard rename convergence to canonical runtime renderer:
  - `scripts/zentable_render.py` is the only active renderer file
  - removed legacy `scripts/zeble_render.py`
- [x] Skill runtime pointer updated:
  - `skills/zentable/zentable_renderer.py` points to canonical renderer
- [x] Legacy CLI renderer archived:
  - `scripts/zeble.py` moved to `doc/archive/deprecated_code/zeble.py`
- [x] Removed stale/broken legacy aliases:
  - `zenble-renderer.py`
  - `zentable.py` (old symlink to removed `scripts/zeble.py`)

## Notes

- Deployment folder `/var/www/html/zenTable` remains unchanged for compatibility.
- `/zenTable/...` URL output path remains unchanged for compatibility.
