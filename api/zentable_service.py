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

from api.ocr_normalize import normalize_ocr_rows


# -----------------------------------------------------------------------------
# PaddleOCR singleton
# -----------------------------------------------------------------------------

_ocr_engine: Any = None


def _get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        raise RuntimeError("OCR engine not initialized")
    return _ocr_engine


def _paddle_result_to_rows(result: Any) -> List[Dict[str, Any]]:
    return normalize_ocr_rows(result)


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

        # Workarounds for some PaddlePaddle runtime issues on certain CPU builds.
        # Must be set BEFORE importing paddle/paddleocr.
        os.environ.setdefault("FLAGS_enable_pir_api", "0")
        os.environ.setdefault("FLAGS_enable_new_executor", "0")
        os.environ.setdefault("FLAGS_use_mkldnn", "0")
        os.environ.setdefault("FLAGS_use_onednn", "0")
        os.environ.setdefault("FLAGS_enable_onednn", "0")

        lang = os.environ.get("OCR_LANG", "ch")
        # PaddleOCR v3 uses `use_textline_orientation` (angle classifier).
        use_textline_orientation = os.environ.get("USE_ANGLE_CLS", "true").lower() in ("1", "true", "yes")

        # PaddleX model source check can block startup in some environments.
        # Allow disabling via env (recommended for offline / restricted envs).
        if os.environ.get("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK") is None:
            os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

        _ocr_engine = PaddleOCR(use_textline_orientation=use_textline_orientation, lang=lang)
        print("[zentable_service] OCR engine loaded")
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

# --- lightweight usage tracking (for heartbeat monitoring) ---
USAGE_PATH = os.environ.get("ZENTABLE_USAGE_PATH", "/home/minecraft/.openclaw/zentable_api_usage.json")


def _usage_touch(request_path: str, method: str) -> None:
    try:
        now = int(time.time())
        os.makedirs(os.path.dirname(USAGE_PATH), exist_ok=True)
        data = {}
        if os.path.exists(USAGE_PATH):
            try:
                import json as _json
                data = _json.loads(open(USAGE_PATH, "r", encoding="utf-8").read() or "{}")
            except Exception:
                data = {}
        last = data.get("last_used_unix")
        data["last_used_unix"] = now
        data.setdefault("counts", {})
        key = f"{method.upper()} {request_path}"
        data["counts"][key] = int(data["counts"].get(key, 0)) + 1
        if last is None:
            data["first_seen_unix"] = now
        import json as _json
        open(USAGE_PATH, "w", encoding="utf-8").write(_json.dumps(data, ensure_ascii=False, indent=2))
    except Exception:
        pass


@app.middleware("http")
async def usage_middleware(request, call_next):
    _usage_touch(request.url.path, request.method)
    return await call_next(request)


class OCRResponse(BaseModel):
    success: bool
    rows: List[Dict[str, Any]]
    elapsed_ms: Optional[int] = None
    error: Optional[str] = None


class OCRBase64Body(BaseModel):
    image_base64: str


class OCRDetResponse(BaseModel):
    success: bool
    boxes: List[Dict[str, Any]]
    elapsed_ms: Optional[int] = None
    error: Optional[str] = None


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
        # PaddleOCR v3: `cls` kwarg is not supported; orientation is configured by pipeline.
        t0 = time.time()
        result = _get_ocr_engine().ocr(img_np)
        elapsed_ms = int((time.time() - t0) * 1000)
        rows = _paddle_result_to_rows(result)
        return OCRResponse(success=True, rows=rows, elapsed_ms=elapsed_ms)
    except Exception as e:
        return OCRResponse(success=False, rows=[], error=str(e))


@app.post("/ocr/det", response_model=OCRDetResponse)
async def ocr_det(image: UploadFile = File(...), timeout_ms: int = 15000):
    """Detection-only: return text region boxes (no recognition).

    Designed for quick complexity estimation.

    timeout_ms:
      - If >0, hard-timeout the det job by running it in a forked subprocess and terminating it.
      - Default 15000ms.
    """
    if _ocr_engine is None:
        return OCRDetResponse(success=False, boxes=[], error="OCR engine not loaded (missing deps?)")
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

        # PaddleOCR v3 (PaddleX pipeline): use the internal text_det_model
        pipe = getattr(_get_ocr_engine(), "paddlex_pipeline", None)
        det_model = None
        if pipe is not None:
            inner = getattr(pipe, "_pipeline", None)
            det_model = getattr(inner, "text_det_model", None) if inner is not None else None

        if det_model is None or not hasattr(det_model, "predict"):
            return OCRDetResponse(success=False, boxes=[], error="det-only not supported by current OCR engine")

        def run_det_job() -> OCRDetResponse:
            t0 = time.time()
            det_res = list(det_model.predict(img_np))
            elapsed_ms = int((time.time() - t0) * 1000)

            boxes: List[Dict[str, Any]] = []
            if det_res:
                r0 = det_res[0]
                polys = None
                try:
                    polys = r0.get("dt_polys")
                except Exception:
                    polys = getattr(r0, "dt_polys", None)
                if polys is not None:
                    for poly in polys:
                        try:
                            xs = [float(p[0]) for p in poly]
                            ys = [float(p[1]) for p in poly]
                            l = int(min(xs)); t = int(min(ys)); r = int(max(xs)); b = int(max(ys))
                            boxes.append({"left": l, "top": t, "width": max(0, r - l), "height": max(0, b - t)})
                        except Exception:
                            continue

            return OCRDetResponse(success=True, boxes=boxes, elapsed_ms=elapsed_ms)

        # Hard timeout via forked subprocess (Linux). This avoids leaving a long-running det job.
        try:
            import multiprocessing as mp
            if timeout_ms is None:
                timeout_ms = 0
            timeout_s = max(0.0, float(timeout_ms) / 1000.0)

            if timeout_s <= 0:
                return run_det_job()

            ctx = mp.get_context("fork")
            q = ctx.Queue(maxsize=1)

            def _worker():
                try:
                    r = run_det_job().model_dump()
                    q.put({"ok": True, "data": r})
                except Exception as e:
                    q.put({"ok": False, "error": str(e)})

            p = ctx.Process(target=_worker)
            p.daemon = True
            p.start()
            p.join(timeout_s)

            if p.is_alive():
                p.terminate()
                p.join(1)
                return OCRDetResponse(success=False, boxes=[], elapsed_ms=int(timeout_ms), error=f"det timeout > {int(timeout_ms)}ms")

            if not q.empty():
                msg = q.get_nowait()
                if msg.get("ok"):
                    d = msg.get("data") or {}
                    return OCRDetResponse(**d)
                return OCRDetResponse(success=False, boxes=[], error=msg.get("error") or "det failed")

            return OCRDetResponse(success=False, boxes=[], error="det failed (no result)")
        except Exception:
            # Fallback: no hard-timeout available
            return run_det_job()

    except Exception as e:
        return OCRDetResponse(success=False, boxes=[], error=str(e))


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
        # PaddleOCR v3: `cls` kwarg is not supported; orientation is configured by pipeline.
        t0 = time.time()
        result = _get_ocr_engine().ocr(img_np)
        elapsed_ms = int((time.time() - t0) * 1000)
        rows = _paddle_result_to_rows(result)
        return OCRResponse(success=True, rows=rows, elapsed_ms=elapsed_ms)
    except Exception as e:
        return OCRResponse(success=False, rows=[], error=str(e))


@app.post("/render/css")
async def render_css(body: CSSRenderBody):
    if not _check_chrome_available():
        return JSONResponse(status_code=503, content={"success": False, "error": "chrome missing"})

    t0 = time.time()
    try:
        png = _render_html_to_png(
            html=body.html,
            viewport_width=body.viewport_width,
            viewport_height=body.viewport_height,
            transparent=body.transparent,
            timeout_ms=body.timeout_ms,
        )
        elapsed_ms = int((time.time() - t0) * 1000)
        headers = {
            "X-Render-Ms": str(elapsed_ms),
            "X-Viewport-W": str(int(body.viewport_width)),
            "X-Viewport-H": str(int(body.viewport_height)),
        }
        return Response(content=png, media_type="image/png", headers=headers)
    except Exception as e:
        elapsed_ms = int((time.time() - t0) * 1000)
        return JSONResponse(status_code=500, content={"success": False, "error": str(e), "elapsed_ms": elapsed_ms})


def run():
    import uvicorn

    host = os.environ.get("ZENTABLE_HOST", "0.0.0.0")
    port = int(os.environ.get("ZENTABLE_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run()
