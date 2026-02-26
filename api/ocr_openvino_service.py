"""
OpenVINO-based OCR FastAPI service (via ONNX Runtime OpenVINO EP).
Compatible with ZenTable OCR API format.
"""

import base64
import io
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

_engine: Any = None
_engine_err: Optional[str] = None


def _to_rows(result: Any) -> List[Dict[str, Any]]:
    """Convert RapidOCR result to ZenTable OCR rows."""
    rows: List[Dict[str, Any]] = []
    if not result:
        return rows

    for item in result:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        box = item[0]
        text = item[1] if len(item) >= 2 else ""

        left = top = width = height = 0
        if isinstance(box, (list, tuple)) and len(box) >= 4 and isinstance(box[0], (list, tuple)):
            try:
                xs = [int(p[0]) for p in box]
                ys = [int(p[1]) for p in box]
                left = min(xs)
                top = min(ys)
                width = max(xs) - left
                height = max(ys) - top
            except Exception:
                pass

        rows.append({
            "text": "" if text is None else str(text),
            "left": int(left),
            "top": int(top),
            "width": int(max(0, width)),
            "height": int(max(0, height)),
        })
    return rows


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _engine, _engine_err
    _engine = None
    _engine_err = None
    try:
        # rapidocr_onnxruntime with OpenVINO EP
        from rapidocr_onnxruntime import RapidOCR

        # Use OpenVINO Execution Provider if available
        ep_params = {"providers": ["OpenVINOExecutionProvider", "CPUExecutionProvider"]}
        _engine = RapidOCR(**ep_params)
    except Exception as e:
        _engine_err = str(e)
        _engine = None
    yield
    _engine = None


app = FastAPI(
    title="ZenTable OCR OpenVINO API",
    description="OpenVINO-based OCR service via ONNX Runtime.",
    lifespan=lifespan,
)


class OCRResponse(BaseModel):
    success: bool
    rows: List[Dict[str, Any]]
    elapsed_ms: Optional[int] = None
    error: Optional[str] = None


class OCRBase64Body(BaseModel):
    image_base64: str


@app.get("/health")
async def health():
    if _engine is None:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "ocr": "not_loaded", "error": _engine_err},
        )
    return {"status": "ok", "ocr": "ready", "backend": "openvino_onnx"}


@app.post("/ocr", response_model=OCRResponse)
async def ocr(image: UploadFile = File(...)):
    if _engine is None:
        return OCRResponse(success=False, rows=[], error=f"engine_not_loaded: {_engine_err}")

    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="請上傳圖片檔（image/*）")

    try:
        raw = await image.read()
        from PIL import Image
        import numpy as np
        import time

        img = Image.open(io.BytesIO(raw)).convert("RGB")
        arr = np.array(img)

        t0 = time.time()
        result, _ = _engine(arr)
        elapsed_ms = int((time.time() - t0) * 1000)

        rows = _to_rows(result)
        return OCRResponse(success=True, rows=rows, elapsed_ms=elapsed_ms)
    except Exception as e:
        return OCRResponse(success=False, rows=[], error=str(e))


@app.post("/ocr/base64", response_model=OCRResponse)
async def ocr_base64(body: OCRBase64Body):
    if _engine is None:
        return OCRResponse(success=False, rows=[], error=f"engine_not_loaded: {_engine_err}")

    try:
        raw = base64.b64decode(body.image_base64)
        from PIL import Image
        import numpy as np
        import time

        img = Image.open(io.BytesIO(raw)).convert("RGB")
        arr = np.array(img)

        t0 = time.time()
        result, _ = _engine(arr)
        elapsed_ms = int((time.time() - t0) * 1000)

        rows = _to_rows(result)
        return OCRResponse(success=True, rows=rows, elapsed_ms=elapsed_ms)
    except Exception as e:
        return OCRResponse(success=False, rows=[], error=str(e))


def run():
    import uvicorn
    host = os.environ.get("OCR_HOST", "0.0.0.0")
    port = int(os.environ.get("OCR_PORT", "8010"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run()
