# ZenTable (Beta) - Runnable Bundle

This bundle includes runnable renderer code (not docs-only).

## Included runtime files

- `skills/zentable/table_renderer.py`
- `scripts/zentable_render.py`
- `scripts/zentable/` (render helpers)
- `themes/` (CSS/PIL/text themes)

## Prerequisites

- Python 3.10+
- Google Chrome (for CSS rendering path)
- Optional OCR stack for image extraction workflows

## Quick install

From this bundle root:

```bash
python3 -m pip install -r requirements-css-api.txt
```

## Smoke test

```bash
echo '{"headers":["A","B"],"rows":[["1","2"]]}' \
| python3 skills/zentable/table_renderer.py - /tmp/zt_smoke.png --theme minimal_ios_mobile --width 450

ls -lh /tmp/zt_smoke.png
```

## Optional OCR/OpenVINO dependencies

```bash
python3 -m pip install -r requirements-openvino.txt
```

## Support / Contact

- GitHub Issues: https://github.com/con2000us/zenTable/issues
- Maintainer: @con2000us (Discord)
