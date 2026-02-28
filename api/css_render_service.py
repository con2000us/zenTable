from __future__ import annotations

import base64
import os
import subprocess
import tempfile
import time
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

TRANSPARENT_BG_HEX = "00000000"


class RenderHtmlBody(BaseModel):
    html: str
    viewport_width: int = 1200
    viewport_height: int = 800
    timeout_ms: int = 3000


class RenderBase64Body(BaseModel):
    html_base64: str
    viewport_width: int = 1200
    viewport_height: int = 800
    timeout_ms: int = 3000


def _check_chrome_available() -> bool:
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
    timeout_ms: int = 3000,
) -> bytes:
    with tempfile.TemporaryDirectory(prefix="zentable_css_api_") as td:
        html_path = os.path.join(td, f"render_{int(time.time() * 1000)}.html")
        out_path = os.path.join(td, "out.png")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        cmd = [
            "xvfb-run", "-a", "google-chrome",
            "--headless",
            f"--screenshot={out_path}",
            f"--virtual-time-budget={int(timeout_ms)}",
            "--hide-scrollbars",
            "--disable-gpu",
            f"--window-size={int(viewport_width)},{int(viewport_height)}",
            f"--default-background-color={TRANSPARENT_BG_HEX}",
            f"file://{html_path}",
        ]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode != 0 or not os.path.isfile(out_path):
            raise RuntimeError(f"Chrome render failed (code={p.returncode}): {p.stderr or p.stdout}")

        with open(out_path, "rb") as f:
            return f.read()


app = FastAPI(title="ZenTable CSS Render Service")


@app.get("/health")
def health():
    return {
        "ok": True,
        "chrome": _check_chrome_available(),
    }


@app.post("/render/html")
def render_html(body: RenderHtmlBody):
    if not body.html.strip():
        raise HTTPException(status_code=400, detail="html is empty")
    try:
        png = _render_html_to_png(
            html=body.html,
            viewport_width=body.viewport_width,
            viewport_height=body.viewport_height,
            timeout_ms=body.timeout_ms,
        )
        return Response(content=png, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/render/base64")
def render_base64(body: RenderBase64Body):
    try:
        html = base64.b64decode(body.html_base64).decode("utf-8", errors="ignore")
    except Exception:
        raise HTTPException(status_code=400, detail="invalid html_base64")
    if not html.strip():
        raise HTTPException(status_code=400, detail="decoded html is empty")
    try:
        png = _render_html_to_png(
            html=html,
            viewport_width=body.viewport_width,
            viewport_height=body.viewport_height,
            timeout_ms=body.timeout_ms,
        )
        return Response(content=png, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
