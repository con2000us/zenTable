# Naming Phase 1.2 Remaining Checklist

Last updated: 2026-02-27
Goal: Continue canonical naming convergence to `zentable` while keeping compatibility aliases.

## Must-fix (runtime-facing)

- [x] `index_v2.html`
  - migrated to `zentable_custom_theme` / `zentable_data.json` / `zentable_theme_*`
- [x] `js/app.js`
  - migrated cookie/local keys to `zentable_*`
  - remaining comment-level wording cleanup can continue in docs sweep
- [x] `gentable_export.php`, `gentable.php`, `gentable_*`
  - Decision: keep legacy `/zenTable/` URL path for deployment compatibility in Phase 1.x.
- [x] `api/render_api.py`
  - comment naming cleanup applied to canonical `zentable` wording.
- [x] `skills/zentable/SKILL.md`
  - metadata name migrated to `name: zentable`
  - alias policy kept in documentation

## Should-fix (docs / consistency)

- [x] `WORKFLOW_VALIDATION.md`
- [x] `doc/ENVIRONMENT_DEPENDENCIES.md`
- [x] `doc/THEME_STRUCTURE.md`
- [x] `doc/INTEGRATION.md`
- [x] `doc/ZEBLE_FLOW.md` (content updated to canonical naming; filename kept for compatibility)
- [x] `doc/SPECIFICATION.md` legacy terms normalized

## Decide-and-document items

- [x] Path policy: keep `/var/www/html/zenTable` as deployed folder for now.
  - Decision: keep path for compatibility, document canonical code naming only.
- [x] Frontend key migration strategy.
  - Decision: migrate to `zentable_*` keys.
  - No long-term retention for old keys is required.
  - Keep local storage mechanism itself for future features.
- [x] Skill display name policy.
  - Decision: migrate to `zentable` and keep alias metadata.

## Phase 1.2 completion criteria

- [x] Runtime commands and scripts use canonical `zentable` names.
- [x] Docs reflect canonical naming (legacy names marked as aliases).
- [ ] No broken calls in PHP/JS/API flows. *(pending one final smoke test pass)*
- [x] Compatibility aliases still function.

## Suggested next action order

1. Frontend keys + filenames (`index_v2.html`, `js/app.js`) with fallback compatibility.
2. `skills/zentable/SKILL.md` metadata naming decision.
3. Runtime/API comments cleanup (`api/render_api.py`, `gentable*`).
4. Docs sweep.
