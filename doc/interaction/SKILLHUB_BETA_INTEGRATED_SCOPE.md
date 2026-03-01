# SkillHub Beta Integrated Scope (Accepted)

This release uses an **integrated beta scope** strategy:
- Include current WIP changes as part of the beta package.
- Do not enforce minimal-diff release isolation for this cycle.
- Treat this release as a broad integration checkpoint before stable hardening.

## Included WIP areas

1. **Doc script migration/cleanup in `doc/`**
   - Legacy doc-side helper/render scripts removed from `doc/` where canonical runtime paths now exist elsewhere.

2. **API enhancements**
   - `table_detect_api.php`: richer payload and response fields for Zx source selection context.
   - `theme_api.php`: `source_type` metadata in theme listing.

3. **Theme updates**
   - Multiple CSS themes updated with `highlight_styles` blocks.
   - Additional theme directories introduced (beta scope).

4. **New utility/docs assets**
   - Added docs/planning notes and example assets under `doc/`.
   - Additional utility PHP/CSS files introduced for workflow support.

## Release positioning

- Channel: **beta**
- Goal: functional integration and user validation
- Non-goal: strict minimal-diff release hygiene

## Next cycle recommendations (toward stable)

- Split broad WIP into smaller traceable change groups.
- Re-run strict repository hygiene gates.
- Lock final API/theme schemas and remove deprecated paths.
