# ERRATA (Refactor Planning Corrections)

Date: 2026-02-27
Scope: `doc/refactor/*`

## 1) api/render_api.py symlink statement correction

Previous planning notes mentioned:
- `api/render_api.py` is a broken symlink.

Current actual state (verified):
- `api/render_api.py` is a **regular file** (not symlink).

Action for agents:
- Do not treat `api/render_api.py` as symlink-repair task.
- Treat naming/path references inside it as regular code refactor.

## 2) Wave 0 prerequisites clarification (golden assets)

Before running wave-gated checks, ensure golden assets exist:

- `tests/golden/input.json`
- `tests/golden/expected_css.png`
- `tests/golden/expected_pil.png`
- `tests/golden/expected_ascii.txt`

If missing, create baseline first, then continue `execution-order.md` Wave 0.

## 3) Package path status clarification

`scripts/zentable/...` package structure in planning docs is the **target architecture**, not guaranteed current-state layout.

Action for agents:
- Create package skeleton in Wave 0/1 as planned.
- Do not assume modules already exist before their corresponding tasks.

## 4) Practical instruction

When in doubt between docs and code reality:
- prioritize actual code and runtime behavior,
- then update docs/checklists accordingly.
