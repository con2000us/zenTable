# Naming Migration Plan (Phase 1)

Last updated: 2026-02-26

## Canonical naming

Use **`zentable`** as the single canonical project identifier for code/runtime paths.

- code/module/path: `zentable` (all lowercase)
- product display name: `ZenTable` (UI/branding only)

## Why

The repository currently mixes names such as:

- `zeble`
- `zable`
- `zebleTable`
- `zenTable`
- `zentable`

This causes onboarding friction and path mistakes.

## Phase 1 scope (safe migration)

Phase 1 is intentionally non-breaking:

1. Define canonical naming policy (`zentable`).
2. Keep compatibility aliases (symlinks/wrappers) for old names.
3. Update docs and entry-point references first.
4. Do **not** remove legacy names yet.

## Current canonical entry points

- Renderer script (real implementation):
  - `/var/www/html/zenTable/scripts/zeble_render.py` (legacy filename, kept for compatibility)
- Canonical renderer alias:
  - `/var/www/html/zenTable/scripts/zentable_render.py`
  - `/var/www/html/zenTable/zentable_renderer.py` (added in phase 1)

## Name mapping table

| Legacy | Canonical target | Phase 1 action |
|---|---|---|
| `zeble_render.py` | `zentable_render.py` | Keep legacy file, use canonical alias in docs |
| `zeble.py` | `zentable.py` | Keep legacy file, add canonical alias |
| `zenTable` path spelling | `zentable` naming policy | Keep existing folder for now; normalize references gradually |
| `zenbleTable` skill label | `zentable` | Keep label now (compat), update docs to canonical naming |

## Phase 2 (future)

- Migrate implementation filenames from `zeble*` to `zentable*`.
- Switch all runtime references to canonical names.
- Remove legacy aliases after validation window.

## Validation checklist

- [ ] Existing commands still work (legacy names)
- [ ] Canonical aliases also work
- [ ] Skills/docs point to canonical naming
- [ ] No service interruption during migration
