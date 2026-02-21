# ZenTable 渲染 API：供 ComfyUI / n8n 以模組或 subprocess 方式呼叫
# 使用方式一（subprocess，不需改 zeble_render.py）：
#   from api.render_api import render_table
#   result = render_table(data, "/tmp/out.png", mode="css", theme_name="neon_cyber")
#
# 使用方式二（若 zeble_render 已實作 run_render）：
#   from api.render_api import run_render
#   result = run_render(data, "/tmp/out.png", mode="css", theme_name="neon_cyber")

import json
import os
import subprocess
import tempfile
from typing import Any, Dict, Optional


# 預設 zeble_render.py 路徑（與 gentable_*.php 一致）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SCRIPT = os.path.join(_PROJECT_ROOT, "scripts", "zeble_render.py")


def render_table(
    data: Dict[str, Any],
    output_path: str,
    mode: str = "css",
    theme_name: str = "default_dark",
    theme_json: Optional[dict] = None,
    script_path: str = DEFAULT_SCRIPT,
    *,
    page: int = 1,
    per_page: int = 15,
    sort_by: Optional[str] = None,
    sort_asc: bool = True,
    calibration: Optional[dict] = None,
    params_override: Optional[dict] = None,
    transparent: bool = False,
    width: Optional[int] = None,
    scale: float = 1.0,
    fill_width: Optional[str] = None,
    bg: Optional[str] = None,
    output_ascii_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    透過 subprocess 呼叫 zeble_render.py 進行表格渲染。
    不需修改 zeble_render.py 即可供 ComfyUI / n8n 使用。

    Args:
        data: 表格資料 {"headers": [...], "rows": [[...]], "title": "", "footer": ""}
        output_path: 輸出 PNG 路徑（ASCII 時可為文字檔路徑）
        mode: "css" | "pil" | "ascii"
        theme_name: themes/<mode>/ 下的主題名稱
        theme_json: 若給定則寫入暫存檔並用 --theme 傳入（覆蓋 theme_name）
        script_path: zeble_render.py 實際路徑
        page, per_page, sort_by, sort_asc: 分頁與排序
        calibration: ASCII 用校準 dict（來自 analyze_from_image 的 calibration）
        params_override: PIL/ASCII 額外參數
        transparent, width, scale, fill_width, bg: 渲染選項
        output_ascii_path: ASCII 模式時文字輸出檔路徑

    Returns:
        {"success": bool, "path": str, "error": str, "stdout": str}
    """
    if not os.path.isfile(script_path):
        return {"success": False, "path": "", "error": f"zeble_render.py 不存在: {script_path}", "stdout": ""}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        input_file = f.name

    cmd = [
        "python3", script_path,
        input_file,
        output_path if mode != "ascii" or not output_ascii_path else "dummy.png",
    ]
    tfd = None
    if theme_json is not None:
        tfd = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
        json.dump(theme_json, tfd, ensure_ascii=False)
        tfd.close()
        cmd.extend(["--theme", tfd.name])
    else:
        cmd.extend(["--theme-name", theme_name])

    if mode == "css":
        cmd.append("--force-css")
    elif mode == "pil":
        cmd.append("--force-pil")
        if params_override:
            cmd.extend(["--params", json.dumps(params_override)])
    elif mode == "ascii":
        cmd.extend(["--force-ascii"])
        if output_ascii_path:
            cmd.extend(["--output-ascii", output_ascii_path])
        if calibration:
            cmd.extend(["--calibration", json.dumps(calibration)])
        if params_override:
            cmd.extend(["--params", json.dumps(params_override)])

    if page > 1:
        cmd.extend(["--page", str(page)])
    if per_page != 15:
        cmd.extend(["--per-page", str(per_page)])
    if sort_by:
        cmd.extend(["--sort", sort_by, "--desc" if not sort_asc else "--asc"])
    if transparent:
        cmd.append("--transparent")
    if width is not None and width > 0:
        cmd.extend(["--width", str(width)])
    if scale != 1.0:
        cmd.extend(["--scale", str(scale)])
    if fill_width:
        cmd.extend(["--fill-width", fill_width])
    if bg:
        cmd.extend(["--bg", bg])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=os.path.dirname(script_path) or None,
        )
        stdout = (result.stdout or "") + (result.stderr or "")
        if result.returncode != 0:
            return {
                "success": False,
                "path": output_path,
                "error": f"exit code {result.returncode}",
                "stdout": stdout,
            }
        if mode == "ascii" and output_ascii_path and os.path.isfile(output_ascii_path):
            out_path = output_ascii_path
        else:
            out_path = output_path
        return {
            "success": os.path.isfile(out_path),
            "path": out_path,
            "error": "" if os.path.isfile(out_path) else "輸出檔未產生",
            "stdout": stdout,
        }
    except Exception as e:
        return {"success": False, "path": output_path, "error": str(e), "stdout": ""}
    finally:
        try:
            os.unlink(input_file)
        except Exception:
            pass
        if tfd is not None:
            try:
                os.unlink(tfd.name)
            except Exception:
                pass


def run_render(*args, **kwargs) -> Dict[str, Any]:
    """
    若 zeble_render.py 日後實作 run_render(data, output_path, mode=..., **kwargs)，
    可在此改為 import 並呼叫該函數，以同進程執行、避免 subprocess。
    目前直接轉給 render_table（subprocess）。
    """
    return render_table(*args, **kwargs)
