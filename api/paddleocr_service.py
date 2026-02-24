"""
PaddleOCR FastAPI 服務：單例載入、常駐記憶體，對外提供 /ocr 與 /health。

啟動方式（專案根目錄）：
  pip install fastapi uvicorn "paddleocr>=2.0.1" "paddlepaddle"
  python -m api.paddleocr_service
  或：uvicorn api.paddleocr_service:app --host 0.0.0.0 --port 8000

環境變數：
  OCR_LANG: 語言，預設 ch（中文），可選 en 等
  USE_GPU: 是否使用 GPU，預設 false
  USE_ANGLE_CLS: 是否啟用方向分類，預設 true
"""

import io
import base64
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel


# 全域單例，在 lifespan 內建立一次
_ocr_engine: Any = None


def _get_ocr_engine():
    """取得已載入的 PaddleOCR 單例。"""
    global _ocr_engine
    if _ocr_engine is None:
        raise RuntimeError("OCR 引擎尚未初始化")
    return _ocr_engine


def _paddle_result_to_rows(result: Any) -> List[Dict[str, Any]]:
    """Normalize PaddleOCR outputs across major versions.

    - PaddleOCR v2 commonly returns: [ [poly, (text, score)], ... ]
    - PaddleOCR v3 (PaddleX pipeline) can return: [ { rec_texts, rec_boxes, ... } ]

    Output rows: {text,left,top,width,height}
    """
    rows: List[Dict[str, Any]] = []
    if result is None:
        return rows

    # v3: list with a dict payload
    if isinstance(result, list) and result and isinstance(result[0], dict):
        payload = result[0]
        texts = payload.get("rec_texts") or []
        boxes = payload.get("rec_boxes") or []
        try:
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
        except Exception:
            pass

    # v2: list of [poly, (text, score)]
    if isinstance(result, list):
        for line in result:
            if line is None or not isinstance(line, (list, tuple)) or len(line) < 2:
                continue
            box = line[0]
            text_info = line[1]
            text = text_info[0] if isinstance(text_info, (list, tuple)) else str(text_info)

            if isinstance(box, (list, tuple)) and len(box) >= 4 and isinstance(box[0], (list, tuple)):
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

    return rows


@asynccontextmanager
async def lifespan(app: FastAPI):
    """啟動時載入 PaddleOCR 一次，關閉時不特別釋放（process 結束即釋放）。"""
    global _ocr_engine

    # Workarounds for some PaddlePaddle runtime issues on certain CPU builds.
    # MUST be set BEFORE importing paddle/paddleocr.
    os.environ.setdefault("FLAGS_enable_pir_api", "0")
    os.environ.setdefault("FLAGS_enable_new_executor", "0")
    # oneDNN / MKLDNN flags (names vary by Paddle version; safe as no-ops if unknown)
    os.environ.setdefault("FLAGS_use_mkldnn", "0")
    os.environ.setdefault("FLAGS_use_onednn", "0")
    os.environ.setdefault("FLAGS_enable_onednn", "0")

    try:
        from paddleocr import PaddleOCR
    except ImportError as e:
        raise RuntimeError(
            "請先安裝 PaddleOCR：pip install \"paddleocr>=2.0.1\" \"paddlepaddle\""
        ) from e

    lang = os.environ.get("OCR_LANG", "ch")
    # PaddleOCR v3 uses `use_textline_orientation` (angle classifier).
    use_textline_orientation = os.environ.get("USE_ANGLE_CLS", "true").lower() in ("1", "true", "yes")

    lang = os.environ.get("OCR_LANG", "ch")
    # PaddleOCR v3 uses `use_textline_orientation` (angle classifier).
    use_textline_orientation = os.environ.get("USE_ANGLE_CLS", "true").lower() in ("1", "true", "yes")

    _ocr_engine = PaddleOCR(
        use_textline_orientation=use_textline_orientation,
        lang=lang,
    )
    yield
    _ocr_engine = None


app = FastAPI(
    title="ZenTable PaddleOCR API",
    description="單例 PaddleOCR 常駐服務，提供 OCR 辨識。",
    lifespan=lifespan,
)


class OCRResponse(BaseModel):
    """OCR 回傳格式，與 calibrate_analyze run_ocr_full 相容。"""
    success: bool
    rows: List[Dict[str, Any]]
    error: Optional[str] = None


@app.get("/health")
async def health():
    """健康檢查，可用於負載均衡或依賴檢查。"""
    try:
        _get_ocr_engine()
        return {"status": "ok", "ocr": "ready"}
    except RuntimeError:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "ocr": "not_loaded"},
        )


@app.post("/ocr", response_model=OCRResponse)
async def ocr(image: UploadFile = File(...)):
    """
    上傳一張圖片，回傳辨識結果。
    每筆含 text, left, top, width, height（與 run_ocr_full 相容）。
    """
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="請上傳圖片檔（image/*）")

    try:
        raw = await image.read()
    except Exception as e:
        return OCRResponse(success=False, rows=[], error=str(e))

    try:
        engine = _get_ocr_engine()
        # PaddleOCR 可接受路徑或 numpy 陣列；這裡用暫存或記憶體
        import numpy as np
        from PIL import Image
        img = Image.open(io.BytesIO(raw))
        if img.mode != "RGB":
            img = img.convert("RGB")
        img_np = np.array(img)
        # PaddleOCR v3: `cls` kwarg is not supported; orientation is configured by pipeline.
        result = engine.ocr(img_np)
        rows = _paddle_result_to_rows(result)
        return OCRResponse(success=True, rows=rows)
    except Exception as e:
        return OCRResponse(success=False, rows=[], error=str(e))


class OCRBase64Body(BaseModel):
    """Base64 圖片 body（可選，方便 JSON 呼叫）。"""
    image_base64: str


@app.post("/ocr/base64", response_model=OCRResponse)
async def ocr_base64(body: OCRBase64Body):
    """以 JSON body 傳入 base64 圖片，回傳辨識結果。"""
    try:
        raw = base64.b64decode(body.image_base64)
    except Exception as e:
        return OCRResponse(success=False, rows=[], error=f"Base64 解碼失敗: {e}")

    try:
        import numpy as np
        from PIL import Image
        img = Image.open(io.BytesIO(raw))
        if img.mode != "RGB":
            img = img.convert("RGB")
        img_np = np.array(img)
        engine = _get_ocr_engine()
        # PaddleOCR v3: `cls` kwarg is not supported; orientation is configured by pipeline.
        result = engine.ocr(img_np)
        rows = _paddle_result_to_rows(result)
        return OCRResponse(success=True, rows=rows)
    except Exception as e:
        return OCRResponse(success=False, rows=[], error=str(e))


def run():
    """供 python -m api.paddleocr_service 直接啟動。"""
    import uvicorn
    host = os.environ.get("OCR_HOST", "0.0.0.0")
    port = int(os.environ.get("OCR_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run()
