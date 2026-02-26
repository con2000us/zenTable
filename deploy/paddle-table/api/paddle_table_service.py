"""
Paddle Table API (PP-Structure) - experimental

Endpoints
- GET /health
- POST /table-parse (multipart image)
"""

import io
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

_engine: Any = None
_engine_err: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _engine, _engine_err
    _engine = None
    _engine_err = None

    # reduce runtime incompatibility risk in some CPU envs
    os.environ.setdefault("FLAGS_enable_pir_api", "0")
    os.environ.setdefault("FLAGS_enable_new_executor", "0")
    os.environ.setdefault("FLAGS_use_mkldnn", "0")
    os.environ.setdefault("FLAGS_use_onednn", "0")
    os.environ.setdefault("FLAGS_enable_onednn", "0")

    try:
        from paddleocr import PPStructure

        lang = os.environ.get("OCR_LANG", "ch")
        _engine = PPStructure(
            show_log=True,
            lang=lang,
            use_gpu=False,
            table=True,
            ocr=True,
            layout=True,
            recovery=False,
        )
    except Exception as e:
        _engine_err = str(e)
        _engine = None

    yield

    _engine = None


app = FastAPI(title="ZenTable Paddle Table API", lifespan=lifespan)


class TableParseResponse(BaseModel):
    success: bool
    tables: List[Dict[str, Any]]
    elapsed_ms: Optional[int] = None
    error: Optional[str] = None


def _normalize_structure_output(raw: Any) -> List[Dict[str, Any]]:
    """Normalize PPStructure output to a stable table list format."""
    tables: List[Dict[str, Any]] = []
    if not isinstance(raw, list):
        return tables

    for block in raw:
        if not isinstance(block, dict):
            continue
        if block.get("type") != "table":
            continue

        bbox = block.get("bbox")
        html = None
        cell_bbox = None
        if isinstance(block.get("res"), dict):
            html = block["res"].get("html")
            cell_bbox = block["res"].get("boxes")

        tables.append(
            {
                "bbox": bbox,
                "html": html,
                "cell_boxes": cell_bbox,
                "raw": block,
            }
        )

    return tables


@app.get("/health")
async def health():
    if _engine is None:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "table": "not_loaded", "error": _engine_err},
        )
    return {"status": "ok", "table": "ready", "backend": "paddle-ppstructure"}


@app.post("/table-parse", response_model=TableParseResponse)
async def table_parse(image: UploadFile = File(...)):
    if _engine is None:
        return TableParseResponse(success=False, tables=[], error=f"engine_not_loaded: {_engine_err}")

    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="請上傳圖片檔（image/*）")

    try:
        from PIL import Image
        import numpy as np

        raw = await image.read()
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        arr = np.array(img)

        t0 = time.time()
        out = _engine(arr)
        elapsed_ms = int((time.time() - t0) * 1000)

        tables = _normalize_structure_output(out)
        return TableParseResponse(success=True, tables=tables, elapsed_ms=elapsed_ms)
    except Exception as e:
        return TableParseResponse(success=False, tables=[], error=str(e))


def run():
    import uvicorn

    host = os.environ.get("OCR_HOST", "0.0.0.0")
    port = int(os.environ.get("OCR_PORT", "8010"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run()
