#!/usr/bin/env python3
"""
Table Detection Hook for OpenClaw

This hook analyzes user messages to detect when table output is needed
and signals the main agent to use zeble skill for table rendering.
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


def main():
    """Main hook entry point"""
    # Read message from stdin or args
    if len(sys.argv) > 1:
        message = sys.argv[1]
    else:
        # Read from stdin
        message = sys.stdin.read().strip()
    
    if not message:
        print(json.dumps({"needs_table": False, "reason": "Empty message"}))
        return
    
    result = analyze_message(message)
    
    # Output as JSON
    print(json.dumps(result))


if __name__ == "__main__":
    main()
