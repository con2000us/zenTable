# SkillHub Release Assets (English)

## One-paragraph description
ZenTable is a production-oriented table rendering skill that converts structured JSON data into polished table outputs, with CSS (Chrome) and PIL image pipelines as primary paths and optional ASCII output for compatibility/debug workflows. It supports stable CLI flags, pin/reset defaults, and dual-service deployment (CSS Render API + OCR API) for reliable automation in chat and backend environments.

## Feature highlights
- CSS + PIL dual rendering with consistent JSON contract (`headers` + `rows`)
- Optional OCR pipeline via FastAPI service (`/ocr`, `/ocr/base64`, `/health`)
- Pin/reset workflow for default rendering behaviors (`--pin`, `--pin-reset`)
- Optional dual output mode (`--both`) to produce PNG + TXT in one run
- Skill-oriented Docker deployment for CSS API + OCR API in one compose stack

## Known limitations
- ASCII output is **beta/experimental** and may drift across platforms due to font fallback and whitespace behavior.
- In Discord plain text, repeated regular spaces are collapsed; Unicode spacing characters (e.g., NBSP/Thin/NNBSP/Em/En/Hair) can be used when preserving spacing is required.
- OCR dependency stack is heavy and may take longer on first build.
- Chrome-based rendering requires headless browser dependencies in runtime containers.

## Quickstart (skill-fastapi)
```bash
cd /var/www/html/zenTable/deploy/skill-fastapi
cp .env.example .env
docker compose up -d --build

# health
curl http://127.0.0.1:8002/health
curl http://127.0.0.1:8001/health
```
