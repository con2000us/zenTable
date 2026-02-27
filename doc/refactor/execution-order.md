# ZenTable Refactoring Execution Order

> ⚠️ Before execution, read `ERRATA.md` for corrections to planning assumptions.

> Generated: 2026-02-27
> Total tasks: 24 | Estimated phases: 7 (0-6)

---

## Execution Status

- [x] Wave 0 completed (T-000, T-001, T-002)
- [x] Wave 1 completed (T-100, T-101)
- [x] Wave 2 completed (T-200, T-201)
- [x] Wave 3 completed (T-300 ~ T-305)
  - rollback: `git revert d06c36c c1355aa 521c526` (or revert latest Wave 3 commit directly)
- [~] Wave 4 in progress (Batch 1-2 done: T-400, T-401; Batch 3 started: T-410 done)
- [ ] Wave 5 pending
- [ ] Wave 6 pending

## Dependency Graph

```
T-000 (golden tests)
  │
  ├──► T-001 (fix broken api ref)
  │
  └──► T-002 (package skeleton)
         │
         ├──► T-100 (util/text.py)  ──┐
         │                            ├──► T-300 (cell.py)
         └──► T-101 (util/color.py) ──┘       │
                                               ├──► T-301 (highlight.py) ────┐
               T-200 (loader.py) ◄─────────────┤                            │
                 │                              ├──► T-302 (transpose.py)    │
                 └──► T-201 (theme.py)          ├──► T-303 (filter.py) ◄────┤
                                                ├──► T-304 (sort_page.py)    │
                                                └──► T-305 (wrap.py)         │
                                                                             │
         ┌───────────────────────────────────────────────────────────────────┘
         │
         ├──► T-400 (ascii/charwidth.py) ──► T-401 (ascii/renderer.py)
         │
         ├──► T-410 (css/crop.py)
         │      │
         │      └──► T-411 (css/chrome.py) ──► T-413 (css/renderer.py)
         │                                        ▲
         ├──► T-412 (css/viewport.py) ────────────┘
         │      ▲
         │      │
         ├──► T-420 (pil/font.py) ──► T-421 (pil/draw.py) ──► T-422 (pil/renderer.py)
         │                                 │
         │                                 └──► T-423 (pil/blueprint.py)
         │
         └──► T-500 (slim main) ──► T-600 (cleanup dead code)
                                      ├──► T-601 (deprecate zeble.py)
                                      ├──► T-602 (update docs)
                                      ├──► T-603 (dedup table_renderer)
                                      └──► T-604 (dedup OCR normalize)
```

---

## Execution Waves

Each wave can be executed in parallel within the wave. Must complete all tasks in a wave before proceeding to the next.

### Wave 0: Foundation (must be first)

| Order | Task | Depends On | Est. Lines Changed |
|---|---|---|---|
| 0.1 | **T-000**: Create golden test baseline | — | +50 (new files) |
| 0.2 | **T-001**: Fix broken `api/render_api.py` | — | 1 line |
| 0.3 | **T-002**: Create package skeleton | — | +10 (empty `__init__.py` files) |

**Wave 0 validation:** `bash tests/golden/run_golden.sh` passes; package importable.

---

### Wave 1: Shared Utilities (no dependencies on other modules)

| Order | Task | Depends On | Est. Lines Moved |
|---|---|---|---|
| 1.1 | **T-100**: Extract `util/text.py` | T-002 | ~110 |
| 1.2 | **T-101**: Extract `util/color.py` | T-002 | ~60 |

**Can run 1.1 and 1.2 in parallel.**

**Wave 1 validation:** `bash tests/golden/run_golden.sh` passes after both.

---

### Wave 2: Detector Layer (Input)

| Order | Task | Depends On | Est. Lines Moved |
|---|---|---|---|
| 2.1 | **T-200**: Extract `input/loader.py` | T-002 | ~30 |
| 2.2 | **T-201**: Extract `input/theme.py` | T-200 | ~170 |

**Must run 2.1 before 2.2** (theme.py imports load_json from loader.py).

**Wave 2 validation:** `bash tests/golden/run_golden.sh` passes; theme loading from PHP works.

---

### Wave 3: Engine Layer (Transform)

| Order | Task | Depends On | Est. Lines Moved |
|---|---|---|---|
| 3.1 | **T-300**: Extract `transform/cell.py` | T-002 | ~50 |
| 3.2 | **T-301**: Extract `transform/highlight.py` | T-300 | ~150 |
| 3.3 | **T-302**: Extract `transform/transpose.py` | T-300 | ~40 |
| 3.4 | **T-303**: Extract `transform/filter.py` | T-300, T-301 | ~200 |
| 3.5 | **T-304**: Extract `transform/sort_page.py` | T-300 | ~120 |
| 3.6 | **T-305**: Extract `transform/wrap.py` | T-300 | ~80 |

**Execution order:**
- First: T-300 (cell.py) — all others depend on it
- Then parallel: T-301, T-302, T-304, T-305
- Then: T-303 (depends on T-300 + T-301)

**Wave 3 validation:** `bash tests/golden/run_golden.sh` passes after all 6 tasks.

---

### Wave 4: Renderer Layer (Output)

| Order | Task | Depends On | Est. Lines Moved |
|---|---|---|---|
| 4.1 | **T-400**: Extract `ascii/charwidth.py` | T-300 | ~120 |
| 4.2 | **T-401**: Extract `ascii/renderer.py` | T-400, T-300 | ~230 |
| 4.3 | **T-410**: Extract `css/crop.py` | T-002 | ~270 |
| 4.4 | **T-420**: Extract `pil/font.py` | T-002 | ~100 |
| 4.5 | **T-421**: Extract `pil/draw.py` | T-420, T-100, T-101 | ~80 |
| 4.6 | **T-412**: Extract `css/viewport.py` | T-300, T-421 | ~160 |
| 4.7 | **T-411**: Extract `css/chrome.py` | T-410 | ~500 |
| 4.8 | **T-413**: Extract `css/renderer.py` | T-411, T-412, T-300, T-301 | ~300 |
| 4.9 | **T-422**: Extract `pil/renderer.py` | T-421, T-420, T-101, T-300 | ~130 |
| 4.10 | **T-423**: Extract `pil/blueprint.py` | T-421, T-420 | ~510 |

**Execution order:**
- Batch A (parallel): T-400, T-410, T-420
- Batch B (parallel after A): T-401, T-421
- Batch C (parallel after B): T-412, T-411
- Batch D (parallel after C): T-413, T-422, T-423

**Wave 4 validation:** `bash tests/golden/run_golden.sh` passes — all three render modes produce identical output.

---

### Wave 5: Orchestration Refactor

| Order | Task | Depends On | Est. Lines Changed |
|---|---|---|---|
| 5.1 | **T-500**: Slim down `main()` | All of waves 1-4 | ~3,200 lines removed |

**Wave 5 validation:** `bash tests/golden/run_golden.sh` passes; `zeble_render.py` ≤ 1,000 lines.

---

### Wave 6: Cleanup & Deduplication

| Order | Task | Depends On | Est. Lines Changed |
|---|---|---|---|
| 6.1 | **T-600**: Archive dead Python files | T-500 | 7 files moved |
| 6.2 | **T-601**: Deprecate `scripts/zeble.py` | T-500 | 1 file moved |
| 6.3 | **T-602**: Update stale documentation | T-500 | ~5 files updated |
| 6.4 | **T-603**: Dedup `table_renderer.py` page logic | T-304 | ~60 lines removed |
| 6.5 | **T-604**: Dedup OCR row normalization | — | ~80 lines consolidated |

**All Wave 6 tasks can run in parallel.**

**Wave 6 validation:** Full acceptance checklist (see `acceptance-checklist.md`).

---

## Summary Timeline

| Wave | Tasks | Parallelizable | Key Risk | Gate |
|---|---|---|---|---|
| **Wave 0** | T-000, T-001, T-002 | Yes (all 3) | None | Golden baseline exists |
| **Wave 1** | T-100, T-101 | Yes (both) | Low | Utilities importable |
| **Wave 2** | T-200, T-201 | Sequential | Medium (path calc) | Themes load correctly |
| **Wave 3** | T-300 → T-301..T-305 | Mostly parallel | Low | Transform pipeline correct |
| **Wave 4** | T-400..T-423 (10 tasks) | 4 batches | High (globals, PIL) | All 3 render modes identical |
| **Wave 5** | T-500 | Single | Medium | main() slim; all tests pass |
| **Wave 6** | T-600..T-604 | Yes (all 5) | Low | Clean codebase |

**Total estimated effort:** ~4,200 lines moved/refactored across 24 tasks.

---

## Rollback Strategy

At any point, if a wave fails validation:

1. `git stash` or `git checkout` to revert wave changes
2. Re-run `bash tests/golden/run_golden.sh` to confirm baseline
3. Debug the failing task in isolation
4. Re-apply passing tasks, fix failing one, re-validate

Each wave is independently rollbackable because:
- `zeble_render.py` retains all functions until T-500 (final slim-down)
- New modules are additive (imports redirect, originals remain until T-500)
- Symlinks and PHP files are never modified (except T-001 fix)
