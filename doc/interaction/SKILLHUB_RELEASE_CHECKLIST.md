# SkillHub Release Checklist (ZenTable)

## A. Release positioning
- [ ] Decide release channel: `beta` (recommended) or `stable`
- [ ] Mark ASCII as `beta/experimental` in all public docs

## B. Functional readiness
- [ ] CSS rendering smoke test passes
- [ ] PIL rendering smoke test passes
- [ ] OCR API health check passes
- [ ] CSS API health check passes
- [ ] `--pin`, `--pin-reset`, `--both` paths verified

## C. Docker/runtime readiness
- [ ] `deploy/skill-fastapi/docker-compose.yml` boots both services
- [ ] Ports and env vars documented and validated
- [ ] Clean rollback path documented

## D. Documentation gate (EN-only for SkillHub)
- [ ] `skills/zentable/SKILL.md` is fully English
- [ ] `doc/skills/zentable/SKILL.md` mirror synced in English
- [ ] Public release summary/highlights/known issues are English
- [ ] Remove mixed Chinese content from publish-facing docs

## E. Publish assets
- [ ] One-paragraph SkillHub description (EN)
- [ ] Feature bullets (EN)
- [ ] Known limitations section (EN)
- [ ] Quickstart command block (EN)

## F. Repository hygiene
- [ ] Remove temporary artifacts (png/tmp/debug outputs)
- [ ] Verify `.gitignore` coverage
- [ ] Final `git status` clean for intended release files

## G. Final sign-off
- [ ] End-to-end demo run recorded (input -> output image)
- [ ] Checklist reviewed and approved
- [ ] Tag/release note prepared
