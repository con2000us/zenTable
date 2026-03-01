# ZenTable Beta Release — skillhub-zentable-beta-2026-03-01

ZenTable beta focuses on hard table workflows: converting noisy inputs (A4 photo capture, broken ASCII, fragmented crops) into clean, decision-ready visual outputs.

## Highlights

- Direct render flow via `Zx` (default CSS path)
- Stable CSS + PIL rendering
- OCR-ready deployment path (OpenVINO route in `deploy/skill-fastapi`)
- Pagination, sorting, filtering, and threshold-oriented highlighting
- Optional dual output (`--both`) for PNG + TXT

## Release positioning

- Channel: **beta**
- Scope: **integrated beta scope** (broad WIP included)

## Known limitations

- ASCII remains **beta/experimental** and can vary across platforms.
- Font fallback and whitespace behavior may affect cross-platform alignment.
- Discord plain text collapses repeated normal spaces; Unicode spacing characters may be needed.
- Validation in this release is Discord-first; other channels may require agent-side output adaptation.

## Quickstart (portable)

```bash
# from repository root
cd deploy/skill-fastapi
cp .env.example .env

# if host port 8001 is occupied
OCR_API_PORT=8003 docker compose up -d --build

curl http://127.0.0.1:8002/health
curl http://127.0.0.1:${OCR_API_PORT:-8001}/health
```

## Smoke test (portable)

```bash
# from repository root
python3 -m py_compile scripts/zentable_render.py

echo '{"headers":["A","B"],"rows":[["1","2"]]}' \
| python3 skills/zentable/table_renderer.py - /tmp/zt_smoke.png --theme minimal_ios_mobile --width 450

ls -lh /tmp/zt_smoke.png
```

## Demo status

Demo video is coming soon. We prioritized shipping beta first for early real-workflow validation.
