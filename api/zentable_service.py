"""ZenTable Combined FastAPI Service.

This service intentionally bundles:
- PaddleOCR (singleton, warm model)
- CSS rendering via headless Chrome (HTTP API wrapper)

It does NOT try to be a full replacement for the existing PHP + CLI pipeline.
The CSS render endpoint is meant as an integration point (and a place to later
add Chrome pooling / CDP reuse if desired).

Run:
  ZENTABLE_HOST=0.0.0.0 ZENTABLE_PORT=8000 python -m api.zentable_service

Env:
  # OCR
  OCR_LANG=ch|en
  USE_GPU=true|false
  USE_ANGLE_CLS=true|false

  # Server
  ZENTABLE_HOST=0.0.0.0
  ZENTABLE_PORT=8000

"""

from __future__ import annotations

import base64
import io
import os
import tempfile
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel


# -----------------------------------------------------------------------------
# PaddleOCR singleton
# -----------------------------------------------------------------------------

_ocr_engine: Any = None


def _get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        raise RuntimeError("OCR engine not initialized")
    return _ocr_engine


def _paddle_result_to_rows(result: Optional[List]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not result:
        return rows
    for line in result:
        if line is None or not isinstance(line, (list, tuple)) or len(line) < 2:
            continue
        box = line[0]
        text_info = line[1]
        text = text_info[0] if isinstance(text_info, (list, tuple)) else str(text_info)
        if isinstance(box, (list, tuple)) and len(box) >= 4:
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            left = int(min(xs))
            top = int(min(ys))
            width = int(max(xs) - left)
            height = int(max(ys) - top)
        else:
            left, top, width, height = 0, 0, 0, 0
        rows.append({"text": text or "", "left": left, "top": top, "width": width, "height": height})
    return rows


# -----------------------------------------------------------------------------
# CSS render via headless Chrome
# -----------------------------------------------------------------------------

TRANSPARENT_BG_HEX = "00000000"


def _check_chrome_available() -> bool:
    import subprocess

    try:
        r = subprocess.run(["which", "google-chrome"], capture_output=True, timeout=3)
        return r.returncode == 0
    except Exception:
        return False


def _render_html_to_png(
    *,
    html: str,
    viewport_width: int = 1200,
    viewport_height: int = 800,
    transparent: bool = True,
    timeout_ms: int = 3000,
) -> bytes:
    """Render an HTML string into a PNG via headless Chrome.

    Returns PNG bytes.

    Notes:
    - This currently shells out to Chrome per request.
    - Later optimization point: Chrome pooling / CDP reuse.
    """
    import subprocess

    # Write HTML to a temp file
    with tempfile.TemporaryDirectory(prefix="zentable_css_api_") as td:
        html_path = os.path.join(td, f"render_{int(time.time() * 1000)}.html")
        out_path = os.path.join(td, "out.png")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        cmd = [
            "xvfb-run",
            "-a",
            "google-chrome",
            "--headless",
            f"--screenshot={out_path}",
            f"--virtual-time-budget={int(timeout_ms)}",
            "--hide-scrollbars",
            "--disable-gpu",
            f"--window-size={int(viewport_width)},{int(viewport_height)}",
        ]
        # Keep behavior aligned with current renderer: always set transparent bg
        cmd.append(f"--default-background-color={TRANSPARENT_BG_HEX}")
        cmd.append(f"file://{html_path}")

        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode != 0 or not os.path.isfile(out_path):
            raise RuntimeError(f"Chrome render failed (code={p.returncode}): {p.stderr or p.stdout}")

        with open(out_path, "rb") as f:
            return f.read()


# -----------------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _ocr_engine

    # OCR init (optional)
    try:
        from paddleocr import PaddleOCR

        lang = os.environ.get("OCR_LANG", "ch")
        use_gpu = os.environ.get("USE_GPU", "false").lower() in ("1", "true", "yes")
        use_angle_cls = os.environ.get("USE_ANGLE_CLS", "true").lower() in ("1", "true", "yes")

        # PaddleX model source check can block startup in some environments.
        # Allow disabling via env (recommended for offline / restricted envs).
        if os.environ.get("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK") is None:
            os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

        _ocr_engine = PaddleOCR(use_angle_cls=use_angle_cls, lang=lang, use_gpu=use_gpu, show_log=False)
    except Exception as e:
        # Keep service up even without OCR deps
        _ocr_engine = None
        print(f"[zentable_service] OCR init failed: {e}")

    yield
    _ocr_engine = None


app = FastAPI(
    title="ZenTable Service",
    description="Combined service: PaddleOCR + Headless Chrome CSS renderer.",
    lifespan=lifespan,
)


class OCRResponse(BaseModel):
    success: bool
    rows: List[Dict[str, Any]]
    error: Optional[str] = None


class OCRBase64Body(BaseModel):
    image_base64: str


class CSSRenderBody(BaseModel):
    html: str
    viewport_width: int = 1200
    viewport_height: int = 800
    transparent: bool = True
    timeout_ms: int = 3000


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "chrome": "ready" if _check_chrome_available() else "missing",
        "ocr": "ready" if _ocr_engine is not None else "not_loaded",
    }


@app.post("/ocr", response_model=OCRResponse)
async def ocr(image: UploadFile = File(...)):
    if _ocr_engine is None:
        return OCRResponse(success=False, rows=[], error="OCR engine not loaded (missing deps?)")
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="image/* required")

    raw = await image.read()
    try:
        import numpy as np
        from PIL import Image

        img = Image.open(io.BytesIO(raw))
        if img.mode != "RGB":
            img = img.convert("RGB")
        img_np = np.array(img)
        use_angle = os.environ.get("USE_ANGLE_CLS", "true").lower() in ("1", "true", "yes")
        result = _get_ocr_engine().ocr(img_np, cls=use_angle)
        rows = _paddle_result_to_rows(result)
        return OCRResponse(success=True, rows=rows)
    except Exception as e:
        return OCRResponse(success=False, rows=[], error=str(e))


@app.post("/ocr/base64", response_model=OCRResponse)
async def ocr_base64(body: OCRBase64Body):
    if _ocr_engine is None:
        return OCRResponse(success=False, rows=[], error="OCR engine not loaded (missing deps?)")
    try:
        raw = base64.b64decode(body.image_base64)
    except Exception as e:
        return OCRResponse(success=False, rows=[], error=f"base64 decode failed: {e}")

    try:
        import numpy as np
        from PIL import Image

        img = Image.open(io.BytesIO(raw))
        if img.mode != "RGB":
            img = img.convert("RGB")
        img_np = np.array(img)
        use_angle = os.environ.get("USE_ANGLE_CLS", "true").lower() in ("1", "true", "yes")
        result = _get_ocr_engine().ocr(img_np, cls=use_angle)
        rows = _paddle_result_to_rows(result)
        return OCRResponse(success=True, rows=rows)
    except Exception as e:
        return OCRResponse(success=False, rows=[], error=str(e))


@app.post("/render/css")
async def render_css(body: CSSRenderBody):
    if not _check_chrome_available():
        return JSONResponse(status_code=503, content={"success": False, "error": "chrome missing"})

    try:
        png = _render_html_to_png(
            html=body.html,
            viewport_width=body.viewport_width,
            viewport_height=body.viewport_height,
            transparent=body.transparent,
            timeout_ms=body.timeout_ms,
        )
        return Response(content=png, media_type="image/png")
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


def run():
    import uvicorn

    host = os.environ.get("ZENTABLE_HOST", "0.0.0.0")
    port = int(os.environ.get("ZENTABLE_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run()
