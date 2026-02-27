# Naming Phase 1.2 Remaining Checklist

Last updated: 2026-02-27
Goal: Continue canonical naming convergence to `zentable` while keeping compatibility aliases.

## Must-fix (runtime-facing)

- [x] `index_v2.html`
  - migrated to `zentable_custom_theme` / `zentable_data.json` / `zentable_theme_*`
- [x] `js/app.js`
  - migrated cookie/local keys to `zentable_*`
  - remaining comment-level wording cleanup can continue in docs sweep
- [ ] `gentable_export.php`, `gentable.php`, `gentable_*`
  - legacy `/zenTable/` URL path usage (keep or alias route?)
- [ ] `api/render_api.py`
  - comments and error text still mention zeble naming in places
- [x] `skills/zentable/SKILL.md`
  - metadata name migrated to `name: zentable`
  - alias policy kept in documentation

## Should-fix (docs / consistency)

- [ ] `WORKFLOW_VALIDATION.md`
- [ ] `doc/ENVIRONMENT_DEPENDENCIES.md`
- [ ] `doc/THEME_STRUCTURE.md`
- [ ] `doc/INTEGRATION.md`
- [ ] `doc/ZEBLE_FLOW.md` (could keep file name, but content should describe canonical `zentable`)
- [ ] `doc/SPECIFICATION.md` legacy zeble terms

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

- [ ] Runtime commands and scripts use canonical `zentable` names.
- [ ] Docs reflect canonical naming (legacy names marked as aliases).
- [ ] No broken calls in PHP/JS/API flows.
- [ ] Compatibility aliases still function.

## Suggested next action order

1. Frontend keys + filenames (`index_v2.html`, `js/app.js`) with fallback compatibility.
2. `skills/zentable/SKILL.md` metadata naming decision.
3. Runtime/API comments cleanup (`api/render_api.py`, `gentable*`).
4. Docs sweep.
