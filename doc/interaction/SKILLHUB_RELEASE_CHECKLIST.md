# SkillHub Release Checklist (ZenTable)

## A. Release positioning
- [x] Decide release channel: `beta` (recommended) or `stable`
- [x] Mark ASCII as `beta/experimental` in all public docs

## B. Functional readiness
- [x] CSS rendering smoke test passes
- [x] PIL rendering smoke test passes
- [x] OCR API health check passes
- [x] CSS API health check passes
- [x] `--pin`, `--pin-reset`, `--both` paths verified

## C. Docker/runtime readiness
- [x] `deploy/skill-fastapi/docker-compose.yml` boots both services
- [x] Ports and env vars documented and validated
- [x] Clean rollback path documented

## D. Documentation gate (EN-only for SkillHub)
- [x] `skills/zentable/SKILL.md` is fully English
- [x] `doc/skills/zentable/SKILL.md` mirror synced in English
- [x] Public release summary/highlights/known issues are English
- [x] Remove mixed Chinese content from publish-facing docs (platform behavior notes can remain if mirrored in EN)

## E. Publish assets
- [x] One-paragraph SkillHub description (EN)
- [x] Feature bullets (EN)
- [x] Known limitations section (EN)
- [x] Quickstart command block (EN)

## F. Repository hygiene
- [ ] Remove temporary artifacts (png/tmp/debug outputs)
- [x] Verify `.gitignore` coverage
- [x] Final `git status` clean for intended release files (beta scope accepted with integrated WIP set)

## G. Final sign-off
- [x] End-to-end demo run recorded (input -> output image)
- [x] Checklist reviewed and approved (beta integrated scope accepted)
- [x] Tag/release note prepared
