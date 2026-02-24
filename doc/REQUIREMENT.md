# Requirements

This document lists the runtime requirements for ZenTable.

## 1) Headless CSS renderer (Chrome)

Used for CSS-mode table rendering (HTML/CSS → PNG screenshot).

### System packages

- **Google Chrome / Chromium** with headless support
  - binary: `google-chrome` (or `chromium-browser`)
- **Xvfb** (for servers without a real display)
  - used via `xvfb-run`

### Notes

- The renderer may optionally use a warm CSS render FastAPI service (`/render/css`).
- If a proxy is required for outbound requests, Chrome can be started with `--proxy-server=...`.

## 2) PaddleOCR (OCR FastAPI)

Used for extracting text boxes from images (table screenshots).

### Python dependencies

Recommended (CPU) minimal install:

```bash
pip install fastapi uvicorn python-multipart pillow numpy
pip install "paddleocr>=2.0.1"
# Pin PaddlePaddle for CPU stability (avoid PIR/oneDNN runtime issues on some 3.3.x builds)
pip install "paddlepaddle==3.2.2"
```

### Model cache

PaddleOCR v3 / PaddleX pipelines cache models under the user home directory, e.g.:

- `~/.paddlex/official_models/`

The cache is persistent until manually deleted.

## 3) Fonts (recommended)

To render CJK/emoji correctly in screenshots:

- `fonts-noto-cjk`
- `fonts-noto-color-emoji`

## 4) Performance guidance

- OCR latency varies significantly across hosts.
- If OCR is slow or inaccurate, crop the screenshot to the relevant region and/or split it into smaller images.
