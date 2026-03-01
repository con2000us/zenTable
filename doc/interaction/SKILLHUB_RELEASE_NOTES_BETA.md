# ZenTable SkillHub Release Notes (Beta)

## Version channel
- **beta**

## Highlights
- Stable CSS/PIL rendering paths for production-style table images.
- Zx shorthand policy documented (direct render by default).
- Dual FastAPI deployment path added (`deploy/skill-fastapi`).
- OCR route switched to OpenVINO stack in skill-fastapi compose.
- EN-only SkillHub-facing SKILL docs completed.

## Known limitations
- ASCII output remains **beta/experimental**.
- Cross-platform text alignment may vary due to font fallback and whitespace behavior.
- Discord plain text collapses repeated normal spaces; Unicode spacing characters may be needed.
- Current `zentable-css-api` health is green, but `/render/html` still returns 500 in this environment (`xvfb-run: xauth command not found`) until rebuilt with updated CSS Dockerfile.

## Verification snapshot
- Local renderer end-to-end image demo: PASS (`/tmp/zentable_signoff/e2e_demo.png`)
- CSS API health (`:8002/health`): PASS
- OCR API health (`:8003/health`): PASS

## Pre-stable blockers
- Rebuild and verify CSS API `/render/html` endpoint in container runtime.
- Repo hygiene (clean working tree / artifact cleanup) pending.
- Final checklist approval pending.
