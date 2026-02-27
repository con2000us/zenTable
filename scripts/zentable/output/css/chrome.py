#!/usr/bin/env python3
"""Chrome interaction helpers for CSS renderer."""

from __future__ import annotations

import os
import re
import subprocess
from typing import Optional


def check_chrome_available() -> bool:
    """檢查 Chrome headless 是否可用。"""
    try:
        result = subprocess.run(['which', 'google-chrome'], capture_output=True, timeout=5)
        return result.returncode == 0
    except Exception:
        return False


def measure_dom_scroll_width(html: str, html_dir: str, viewport_width: int, viewport_height: int, transparent_bg_hex: str = "00000000") -> Optional[int]:
    """Measure content scrollWidth from DOM using headless Chrome + --dump-dom."""
    try:
        ts = str(int(__import__('time').time() * 1000))
        html_file = os.path.join(html_dir, f"measure_{ts}.html")

        inject = """
<script>
(function(){
  function pick(){ return document.querySelector('table') || document.querySelector('.table') || null; }
  function measure(){
    var el = pick();
    var sw = 0;
    if(el){ try { sw = el.scrollWidth||0; } catch(e) {} }
    document.title = 'ZENTABLE_SCROLLWIDTH=' + Math.ceil(sw);
  }
  window.addEventListener('load', function(){ setTimeout(measure, 50); });
  setTimeout(measure, 200);
})();
</script>
"""
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html + inject)

        parts = [
            "xvfb-run", "-a", "google-chrome", "--headless",
            "--disable-gpu",
            "--virtual-time-budget=1000",
            f"--window-size={int(viewport_width)},{int(viewport_height)}",
            f"--default-background-color={transparent_bg_hex}",
            "--dump-dom",
            f"file://{html_file}",
        ]
        p = subprocess.run(parts, capture_output=True, text=True, timeout=30)
        out = (p.stdout or "")
        m = re.search(r"ZENTABLE_SCROLLWIDTH=(\d+)", out)
        if m:
            return int(m.group(1))
        return None
    except Exception:
        return None


def measure_dom_overflow(html: str, html_dir: str, viewport_width: int, viewport_height: int, transparent_bg_hex: str = "00000000") -> Optional[dict]:
    """Measure DOM overflow for table/body."""
    try:
        ts = str(int(__import__('time').time() * 1000))
        html_file = os.path.join(html_dir, f"overflow_{ts}.html")

        inject = """
<script>
(function(){
  function pick(){ return document.querySelector('table') || document.querySelector('.table') || null; }
  function measure(){
    var el = pick();
    var sw = 0, cw = 0, rw = 0;
    if(el){ try { sw = el.scrollWidth||0; cw = el.clientWidth||0; rw = el.getBoundingClientRect().width||0; } catch(e) {} }
    var bsw = 0, bcw = 0, brw = 0;
    try {
      var b = document.body;
      if(b){ bsw = b.scrollWidth||0; bcw = b.clientWidth||0; brw = b.getBoundingClientRect().width||0; }
    } catch(e) {}
    document.title = 'ZENTABLE_OVERFLOW=' + Math.ceil(sw) + ',' + Math.ceil(cw) + ',' + Math.ceil(rw)
      + '|BODY=' + Math.ceil(bsw) + ',' + Math.ceil(bcw) + ',' + Math.ceil(brw);
  }
  window.addEventListener('load', function(){ setTimeout(measure, 50); });
  setTimeout(measure, 200);
})();
</script>
"""
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html + inject)

        parts = [
            "xvfb-run", "-a", "google-chrome", "--headless",
            "--disable-gpu",
            "--virtual-time-budget=1000",
            f"--window-size={int(viewport_width)},{int(viewport_height)}",
            f"--default-background-color={transparent_bg_hex}",
            "--dump-dom",
            f"file://{html_file}",
        ]
        p = subprocess.run(parts, capture_output=True, text=True, timeout=30)
        out = (p.stdout or "")
        m = re.search(r"ZENTABLE_OVERFLOW=(\d+),(\d+),(\d+)\|BODY=(\d+),(\d+),(\d+)", out)
        if m:
            return {
                "table": {"scrollWidth": int(m.group(1)), "clientWidth": int(m.group(2)), "rectWidth": int(m.group(3))},
                "body": {"scrollWidth": int(m.group(4)), "clientWidth": int(m.group(5)), "rectWidth": int(m.group(6))},
            }
        m2 = re.search(r"ZENTABLE_OVERFLOW=(\d+),(\d+),(\d+)", out)
        if m2:
            return {"table": {"scrollWidth": int(m2.group(1)), "clientWidth": int(m2.group(2)), "rectWidth": int(m2.group(3))}}
        return None
    except Exception:
        return None
