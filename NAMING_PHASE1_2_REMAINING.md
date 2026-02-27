# Naming Phase 1.2 Remaining Checklist

Last updated: 2026-02-27
Goal: Continue canonical naming convergence to `zentable` while keeping compatibility aliases.

## Must-fix (runtime-facing)

- [ ] `index_v2.html`
  - `zeble_custom_theme` / `zeble_data.json` / `zeble_theme_*` keys + filenames
- [ ] `js/app.js`
  - cookie keys still `zenTable_*` (decide: keep as compatibility or migrate with fallback read)
  - comments mention `zeble_render`
- [ ] `gentable_export.php`, `gentable.php`, `gentable_*`
  - legacy `/zenTable/` URL path usage (keep or alias route?)
- [ ] `api/render_api.py`
  - comments and error text still mention zeble naming in places
- [ ] `skills/zentable/SKILL.md`
  - metadata `name: zenbleTable` (decide migration policy with skill compatibility)

## Should-fix (docs / consistency)

- [ ] `WORKFLOW_VALIDATION.md`
- [ ] `doc/ENVIRONMENT_DEPENDENCIES.md`
- [ ] `doc/THEME_STRUCTURE.md`
- [ ] `doc/INTEGRATION.md`
- [ ] `doc/ZEBLE_FLOW.md` (could keep file name, but content should describe canonical `zentable`)
- [ ] `doc/SPECIFICATION.md` legacy zeble terms

## Decide-and-document items

- [ ] Path policy: keep `/var/www/html/zenTable` as deployed folder for now?
  - recommended: keep path for compatibility, document canonical code naming only.
- [ ] Frontend key migration strategy:
  - Option A: keep old localStorage/cookie keys forever.
  - Option B: migrate to `zentable_*` with fallback read from old keys.
- [ ] Skill display name policy:
  - keep `zenbleTable` for external compatibility?
  - or migrate to `zentable` and keep alias metadata.

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
