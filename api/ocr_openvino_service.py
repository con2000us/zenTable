"""
OpenVINO-based OCR FastAPI service (via ONNX Runtime OpenVINO EP).
Compatible with ZenTable OCR API format.
"""

import base64
import io
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from api.ocr_normalize import normalize_ocr_rows

_engine: Any = None
_engine_err: Optional[str] = None


def _to_rows(result: Any) -> List[Dict[str, Any]]:
    return normalize_ocr_rows(result)


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
    timing: Optional[Dict[str, Any]] = None
    debug: Optional[Dict[str, Any]] = None
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
async def ocr(image: UploadFile = File(...), debug: bool = Query(False)):
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
        timing = {"total_ms": elapsed_ms}
        resp = OCRResponse(success=True, rows=rows, elapsed_ms=elapsed_ms, timing=timing)
        if debug:
            resp.debug = {
                "backend": "openvino_onnx",
                "stages": {"ocr_ms": elapsed_ms},
                "row_count": len(rows),
            }
        return resp
    except Exception as e:
        return OCRResponse(success=False, rows=[], error=str(e))


@app.post("/ocr/base64", response_model=OCRResponse)
async def ocr_base64(body: OCRBase64Body, debug: bool = Query(False)):
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
        timing = {"total_ms": elapsed_ms}
        resp = OCRResponse(success=True, rows=rows, elapsed_ms=elapsed_ms, timing=timing)
        if debug:
            resp.debug = {
                "backend": "openvino_onnx",
                "stages": {"ocr_ms": elapsed_ms},
                "row_count": len(rows),
            }
        return resp
    except Exception as e:
        return OCRResponse(success=False, rows=[], error=str(e))


def run():
    import uvicorn
    host = os.environ.get("OCR_HOST", "0.0.0.0")
    port = int(os.environ.get("OCR_PORT", "8010"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run()
