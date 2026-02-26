"""
Unified OCR FastAPI service with pluggable backend.

Backends:
- paddle      (PaddleOCR)
- openvino    (rapidocr_onnxruntime + OpenVINOExecutionProvider)
- onnx        (rapidocr_onnxruntime + CPUExecutionProvider)
- auto        (default): openvino -> onnx -> paddle

Environment variables:
- OCR_BACKEND=auto|openvino|onnx|paddle
- OCR_LANG=ch
- USE_ANGLE_CLS=true|false
- OCR_HOST=0.0.0.0
- OCR_PORT=8000

Direct-override parameters (preserved):
- OCR_CPU_THREADS=4
- OCR_ENABLE_MKLDNN=false
- OCR_IR_OPTIM=false
"""

import base64
import io
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

_engine: Any = None
_backend: Optional[str] = None
_engine_error: Optional[str] = None


def _as_bool(v: str, default: bool = False) -> bool:
    if v is None:
        return default
    return str(v).lower() in ("1", "true", "yes", "on")


def _normalize_rows(result: Any) -> List[Dict[str, Any]]:
    """Normalize outputs across backends to {text,left,top,width,height}."""
    rows: List[Dict[str, Any]] = []
    if not result:
        return rows

    # Paddle v3 style: [{rec_texts, rec_boxes, ...}]
    if isinstance(result, list) and result and isinstance(result[0], dict):
        payload = result[0]
        texts = payload.get("rec_texts") or []
        boxes = payload.get("rec_boxes") or []
        n = min(len(texts), len(boxes))
        for i in range(n):
            b = boxes[i]
            if b is None or len(b) < 4:
                continue
            l, t, r, btm = map(int, b[:4])
            rows.append({
                "text": str(texts[i]) if texts[i] is not None else "",
                "left": l,
                "top": t,
                "width": max(0, r - l),
                "height": max(0, btm - t),
            })
        return rows

    # Paddle v2 style: [[poly, (text, score)], ...]
    if isinstance(result, list) and result and isinstance(result[0], (list, tuple)) and len(result[0]) >= 2:
        # Could also be RapidOCR style; detect by second element type
        sample = result[0]
        second = sample[1]

        # RapidOCR style: [box, text, score?]
        if isinstance(second, str):
            for item in result:
                if not isinstance(item, (list, tuple)) or len(item) < 2:
                    continue
                box, text = item[0], item[1]
                left = top = width = height = 0
                if isinstance(box, (list, tuple)) and len(box) >= 4 and isinstance(box[0], (list, tuple)):
                    xs = [int(p[0]) for p in box]
                    ys = [int(p[1]) for p in box]
                    left = min(xs)
                    top = min(ys)
                    width = max(xs) - left
                    height = max(ys) - top
                rows.append({
                    "text": "" if text is None else str(text),
                    "left": int(left),
                    "top": int(top),
                    "width": int(max(0, width)),
                    "height": int(max(0, height)),
                })
            return rows

        # Paddle v2 legacy
        for line in result:
            if line is None or not isinstance(line, (list, tuple)) or len(line) < 2:
                continue
            box = line[0]
            text_info = line[1]
            text = text_info[0] if isinstance(text_info, (list, tuple)) else str(text_info)
            left = top = width = height = 0
            if isinstance(box, (list, tuple)) and len(box) >= 4 and isinstance(box[0], (list, tuple)):
                xs = [p[0] for p in box]
                ys = [p[1] for p in box]
                left = int(min(xs))
                top = int(min(ys))
                width = int(max(xs) - left)
                height = int(max(ys) - top)
            rows.append({"text": text or "", "left": left, "top": top, "width": width, "height": height})
        return rows

    return rows


def _load_paddle() -> Any:
    # runtime safety flags before import
    os.environ.setdefault("FLAGS_enable_pir_api", "0")
    os.environ.setdefault("FLAGS_enable_new_executor", "0")
    os.environ.setdefault("FLAGS_use_mkldnn", "0")
    os.environ.setdefault("FLAGS_use_onednn", "0")
    os.environ.setdefault("FLAGS_enable_onednn", "0")

    import paddle
    from paddleocr import PaddleOCR

    try:
        paddle.set_flags({
            "FLAGS_enable_pir_api": False,
            "FLAGS_enable_new_executor": False,
            "FLAGS_use_mkldnn": False,
            "FLAGS_use_onednn": False,
            "FLAGS_enable_onednn": False,
        })
    except Exception:
        pass

    lang = os.environ.get("OCR_LANG", "ch")
    use_angle = _as_bool(os.environ.get("USE_ANGLE_CLS", "true"), True)
    cpu_threads = int(os.environ.get("OCR_CPU_THREADS", "4"))
    enable_mkldnn = _as_bool(os.environ.get("OCR_ENABLE_MKLDNN", "false"), False)
    ir_optim = _as_bool(os.environ.get("OCR_IR_OPTIM", "false"), False)

    # Keep direct parameters overridable by env
    engine = PaddleOCR(
        lang=lang,
        use_angle_cls=use_angle,
        use_gpu=False,
        cpu_threads=cpu_threads,
        enable_mkldnn=enable_mkldnn,
        ir_optim=ir_optim,
    )
    return engine


def _load_rapidocr(openvino: bool) -> Any:
    from rapidocr_onnxruntime import RapidOCR

    if openvino:
        return RapidOCR(providers=["OpenVINOExecutionProvider", "CPUExecutionProvider"])
    return RapidOCR(providers=["CPUExecutionProvider"])


def _init_engine() -> Tuple[Any, str]:
    backend = os.environ.get("OCR_BACKEND", "auto").strip().lower()

    if backend == "paddle":
        return _load_paddle(), "paddle"
    if backend == "openvino":
        return _load_rapidocr(openvino=True), "openvino"
    if backend == "onnx":
        return _load_rapidocr(openvino=False), "onnx"

    # auto fallback chain
    errs: List[str] = []
    for name in ("openvino", "onnx", "paddle"):
        try:
            if name == "openvino":
                return _load_rapidocr(openvino=True), name
            if name == "onnx":
                return _load_rapidocr(openvino=False), name
            return _load_paddle(), name
        except Exception as e:
            errs.append(f"{name}: {e}")

    raise RuntimeError("all backends failed: " + " | ".join(errs))


def _run_ocr(img_np) -> Any:
    if _engine is None:
        raise RuntimeError("OCR engine not initialized")

    if _backend == "paddle":
        return _engine.ocr(img_np)

    # rapidocr_onnxruntime => (result, elapsed)
    result, _ = _engine(img_np)
    return result


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _engine, _backend, _engine_error
    _engine = None
    _backend = None
    _engine_error = None

    try:
        _engine, _backend = _init_engine()
    except Exception as e:
        _engine_error = str(e)
        _engine = None
        _backend = None

    yield

    _engine = None
    _backend = None


app = FastAPI(
    title="ZenTable Unified OCR API",
    description="Single OCR API with pluggable backend (auto/openvino/onnx/paddle).",
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
            content={"status": "unavailable", "ocr": "not_loaded", "error": _engine_error},
        )
    return {"status": "ok", "ocr": "ready", "backend": _backend}


@app.post("/ocr", response_model=OCRResponse)
async def ocr(image: UploadFile = File(...)):
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="請上傳圖片檔（image/*）")

    if _engine is None:
        return OCRResponse(success=False, rows=[], error=f"engine_not_loaded: {_engine_error}")

    try:
        raw = await image.read()
        import numpy as np
        from PIL import Image

        img = Image.open(io.BytesIO(raw))
        if img.mode != "RGB":
            img = img.convert("RGB")
        img_np = np.array(img)

        t0 = time.time()
        result = _run_ocr(img_np)
        elapsed_ms = int((time.time() - t0) * 1000)

        rows = _normalize_rows(result)
        return OCRResponse(success=True, rows=rows, elapsed_ms=elapsed_ms)
    except Exception as e:
        return OCRResponse(success=False, rows=[], error=str(e))


@app.post("/ocr/base64", response_model=OCRResponse)
async def ocr_base64(body: OCRBase64Body):
    if _engine is None:
        return OCRResponse(success=False, rows=[], error=f"engine_not_loaded: {_engine_error}")

    try:
        raw = base64.b64decode(body.image_base64)
        import numpy as np
        from PIL import Image

        img = Image.open(io.BytesIO(raw))
        if img.mode != "RGB":
            img = img.convert("RGB")
        img_np = np.array(img)

        t0 = time.time()
        result = _run_ocr(img_np)
        elapsed_ms = int((time.time() - t0) * 1000)

        rows = _normalize_rows(result)
        return OCRResponse(success=True, rows=rows, elapsed_ms=elapsed_ms)
    except Exception as e:
        return OCRResponse(success=False, rows=[], error=str(e))


def run():
    import uvicorn

    host = os.environ.get("OCR_HOST", "0.0.0.0")
    port = int(os.environ.get("OCR_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run()
