# ZenTable 校準 API：供 ComfyUI / n8n 以模組方式呼叫
# 使用方式：將 zenTable 目錄加入 sys.path 後
#   from api.calibration_api import analyze_from_image
#   result = analyze_from_image("/path/to/screenshot.png", custom_chars="", use_ocr=True)

import os
import sys
from typing import Any, Dict


def _add_project_path():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root not in sys.path:
        sys.path.insert(0, root)


def analyze_from_image(
    image_path: str,
    custom_chars: str = "",
    use_ocr: bool = True,
) -> Dict[str, Any]:
    """
    從校準截圖分析字元寬度，回傳 calibration 等結果。
    供 ComfyUI / n8n 等以 import 方式呼叫，無需執行 CLI。

    Args:
        image_path: 校準區塊截圖路徑（含 [ZENT-BLE-MKR] ... [END] 的畫面）
        custom_chars: 要個別測量的自訂字元序列
        use_ocr: True=用 OCR 測量（預設），False=純像素計數

    Returns:
        {
            "calibration": { "ascii", "cjk", "box", "half_space", "full_space", "emoji", "custom"? },
            "pixel_per_unit": float,
            "ocr_lines": [...],
            "char_measurements": [...]
        }
    """
    _add_project_path()
    from calibrate_analyze import analyze_widths
    return analyze_widths(image_path, custom_chars=custom_chars, use_ocr=use_ocr)


def analyze_from_image_pixel(image_path: str, custom_chars: str = "") -> Dict[str, Any]:
    """僅用像素計數分析（不依賴 OCR）。回傳格式同 analyze_from_image。"""
    _add_project_path()
    from calibrate_analyze import analyze_widths_by_pixel
    return analyze_widths_by_pixel(image_path, custom_chars=custom_chars)
