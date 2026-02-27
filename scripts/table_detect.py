#!/usr/bin/env python3
"""
Table Detection Hook for OpenClaw

This hook analyzes user messages to detect when table output is needed
and signals the main agent to use zentable skill for table rendering.
"""

import json
import sys
import re

# Table detection keywords and patterns
TABLE_KEYWORDS = {
    # Direct table indicators
    "表格", "表", "table", "tables",
    # Comparison keywords
    "比較", "對照", "vs", "versus", "compare", "comparison",
    # Pricing keywords  
    "定價", "價格", "費用", "cost", "pricing", "fee", "price",
    # Model/type keywords
    "model", "型號", "型別", "type",
    # List keywords
    "列表", "清單", "list", "listing",
    # Specs keywords
    "規格", "specs", "specification", "spec",
    # Column/row keywords
    "欄", "列", "行", "column", "row",
}

# Intent patterns for table requests
INTENT_PATTERNS = [
    r"列出[^\n]*",
    r"show\s+me\s+a?\s*table",
    r"display\s+(as\s+)?table",
    r"比較[^\n]*和[^\n]*",
    r"compare[^\n]*with[^\n]*",
    r"what'?s\s+(the\s+)?(difference|diff)",
    r"list\s+(all\s+)?",
]

# Table symbols
TABLE_SYMBOLS = ["|", "│", "｜"]


def _to_bool(value) -> bool:
    """Best-effort boolean parsing for API payload fields."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return False


def _parse_input_payload(raw: str) -> dict:
    """Accept either plain message text or JSON payload."""
    raw = (raw or "").strip()
    if not raw:
        return {
            "message": "",
            "previous_message": "",
            "has_image": False,
            "previous_has_image": False,
        }

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "message": raw,
            "previous_message": "",
            "has_image": False,
            "previous_has_image": False,
        }

    if isinstance(payload, str):
        return {
            "message": payload,
            "previous_message": "",
            "has_image": False,
            "previous_has_image": False,
        }

    if not isinstance(payload, dict):
        return {
            "message": raw,
            "previous_message": "",
            "has_image": False,
            "previous_has_image": False,
        }

    message = str(payload.get("message", "") or "")
    previous_message = str(payload.get("previous_message", "") or "")
    has_image = _to_bool(payload.get("has_image"))
    previous_has_image = _to_bool(payload.get("previous_has_image"))

    # Fallback: infer has_image from image arrays if provided.
    if not has_image and isinstance(payload.get("images"), list):
        has_image = len(payload.get("images")) > 0
    if not previous_has_image and isinstance(payload.get("previous_images"), list):
        previous_has_image = len(payload.get("previous_images")) > 0

    return {
        "message": message,
        "previous_message": previous_message,
        "has_image": has_image,
        "previous_has_image": previous_has_image,
    }


def _is_zx_trigger(text: str) -> bool:
    """
    Zx shorthand trigger.
    Examples: "zx", "Zx 請整理", "zx: ..."
    """
    return re.match(r"^\s*zx(?:\b|[:：]|\s|$)", (text or "").strip(), re.IGNORECASE) is not None


def _strip_zx_prefix(text: str) -> str:
    """Remove leading zx shorthand token and separators."""
    return re.sub(r"^\s*zx(?:\b)?(?:\s*[:：]\s*|\s+)?", "", text or "", flags=re.IGNORECASE).strip()


def _resolve_zx_source(payload: dict) -> tuple[list[str], str]:
    """
    Zx source priority:
      1) current image OCR
      2) current text to table
      3) previous image OCR
      4) previous text to table
    """
    message = _strip_zx_prefix((payload.get("message") or "").strip())
    prev = (payload.get("previous_message") or "").strip()
    has_image = bool(payload.get("has_image"))
    prev_has_image = bool(payload.get("previous_has_image"))

    source_priority: list[str] = []
    if has_image:
        source_priority.append("current_image_ocr")
    if message:
        source_priority.append("current_text_table")
    if prev_has_image:
        source_priority.append("previous_image_ocr")
    if prev:
        source_priority.append("previous_text_table")

    selected = source_priority[0] if source_priority else ""
    return source_priority, selected


def contains_table_data(text: str) -> bool:
    """Check if text contains table data (e.g., | col1 | col2 |)"""
    for symbol in TABLE_SYMBOLS:
        if symbol in text:
            # Check if it looks like a table row
            parts = text.split(symbol)
            if len(parts) >= 3:
                return True
    return False


def detect_table_intent(text: str) -> bool:
    """Detect if user wants table output based on keywords and intent"""
    text_lower = text.lower()
    
    # Check keywords
    for keyword in TABLE_KEYWORDS:
        if keyword.lower() in text_lower:
            return True
    
    # Check intent patterns
    for pattern in INTENT_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    
    return False


def analyze_message(message: str) -> dict:
    """
    Analyze a message and return detection result.
    
    Returns:
        {
            "needs_table": bool,
            "reason": str,
            "confidence": float (0.0-1.0)
        }
    """
    has_table_data = contains_table_data(message)
    has_intent = detect_table_intent(message)
    
    if has_table_data:
        return {
            "needs_table": True,
            "reason": "Table data detected (pipe symbols found)",
            "confidence": 0.95
        }
    
    if has_intent:
        return {
            "needs_table": True,
            "reason": "Table intent detected (keywords/patterns matched)",
            "confidence": 0.85
        }
    
    return {
        "needs_table": False,
        "reason": "No table indicators found",
        "confidence": 0.0
    }


def analyze_payload(payload: dict) -> dict:
    """Analyze payload with Zx fallback logic and table intent detection."""
    message = str(payload.get("message", "") or "")
    previous_message = str(payload.get("previous_message", "") or "")
    has_image = bool(payload.get("has_image"))
    previous_has_image = bool(payload.get("previous_has_image"))

    zx_mode = _is_zx_trigger(message)
    if zx_mode:
        source_priority, selected_source = _resolve_zx_source(payload)
        if selected_source:
            return {
                "needs_table": True,
                "reason": f"Zx mode: selected source={selected_source}",
                "confidence": 1.0,
                "zx_mode": True,
                "source_priority": source_priority,
                "selected_source": selected_source,
                "action": "ocr_then_table" if "image_ocr" in selected_source else "text_to_table",
                "has_image": has_image,
                "previous_has_image": previous_has_image,
            }
        return {
            "needs_table": False,
            "reason": "Zx mode: no usable current/previous image or text context",
            "confidence": 0.2,
            "zx_mode": True,
            "source_priority": [],
            "selected_source": "",
            "action": "ask_for_context",
            "has_image": has_image,
            "previous_has_image": previous_has_image,
        }

    base = analyze_message(message)
    base.update({
        "zx_mode": False,
        "source_priority": [],
        "selected_source": "",
        "action": "table_intent_detect",
        "has_image": has_image,
        "previous_has_image": previous_has_image,
        "previous_message_present": bool(previous_message.strip()),
    })
    return base


def main():
    """Main hook entry point"""
    # Read raw input from args or stdin. Supports plain message or JSON payload.
    if len(sys.argv) > 1:
        raw = sys.argv[1]
    else:
        raw = sys.stdin.read().strip()

    payload = _parse_input_payload(raw)
    if not payload.get("message") and not payload.get("previous_message") and not payload.get("has_image") and not payload.get("previous_has_image"):
        print(json.dumps({"needs_table": False, "reason": "Empty input", "zx_mode": False}))
        return

    result = analyze_payload(payload)

    # Output as JSON
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
