#!/usr/bin/env python3
"""OpenClaw custom-skill renderer shim for ZenbleTable.

This repository contains the full ZenTable project under /var/www/html/zenTable.
The OpenClaw skill docs expect a lightweight renderer at:
  ~/.openclaw/custom-skills/zenbleTable/table_renderer.py

In this deployment, ~/.openclaw/custom-skills/zenbleTable is a symlink to:
  /var/www/html/zenTable/skills/zebleTable

So we provide this shim here.

Interface (kept compatible with the SKILL.md examples):
  echo '{json}' | table_renderer.py - /tmp/out.png --theme mobile_chat

Implementation:
  - CSS themes (mobile_chat, minimal_ios, bubble_card, modern_line, compact_clean)
    render via scripts/zeble_render.py --force-css.
  - default_light/default_dark render via scripts/zeble_render.py --force-pil
    using the bundled theme zip.

Notes:
  - We intentionally depend on the local ZenTable scripts and themes; this is
    host-specific and not meant for upstream OpenClaw repo.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ZEN_ROOT = Path("/var/www/html/zenTable")
ZEBLE_RENDER = ZEN_ROOT / "zenble-renderer.py"
THEMES_CSS = ZEN_ROOT / "themes" / "css"
THEMES_PIL_ZIP = ZEN_ROOT / "themes" / "pil"

CSS_THEMES = {"mobile_chat", "minimal_ios", "bubble_card", "modern_line", "compact_clean"}
PIL_THEMES = {"default_light", "default_dark"}


def _read_json_input(input_path: str) -> str:
    if input_path == "-":
        return sys.stdin.read()
    return Path(input_path).read_text(encoding="utf-8")


def _write_temp_json(data_str: str, tmpdir: Path) -> Path:
    # Validate JSON early for nicer errors.
    try:
        json.loads(data_str)
    except json.JSONDecodeError as e:
        raise SystemExit(f"Invalid JSON input: {e}")

    p = tmpdir / "data.json"
    p.write_text(data_str, encoding="utf-8")
    return p


def _theme_to_args(theme: str, tmpdir: Path) -> list[str]:
    theme = theme.strip()

    if theme in CSS_THEMES:
        theme_file = THEMES_CSS / theme / "template.json"
        if not theme_file.exists():
            raise SystemExit(f"Theme not found: {theme_file}")
        return ["--force-css", "--theme", str(theme_file)]

    if theme in PIL_THEMES:
        zip_path = THEMES_PIL_ZIP / f"{theme}.zip"
        if not zip_path.exists():
            raise SystemExit(f"Theme zip not found: {zip_path}")
        extract_dir = tmpdir / f"theme_{theme}"
        extract_dir.mkdir(parents=True, exist_ok=True)
        shutil.unpack_archive(str(zip_path), str(extract_dir))
        theme_file = extract_dir / "template.json"
        if not theme_file.exists():
            raise SystemExit(f"Theme template.json missing after unzip: {theme_file}")
        return ["--force-pil", "--theme", str(theme_file)]

    # Back-compat aliases (accept 'default' => default_light)
    if theme in {"default", "light"}:
        return _theme_to_args("default_light", tmpdir)
    if theme in {"dark"}:
        return _theme_to_args("default_dark", tmpdir)

    raise SystemExit(
        "Unknown theme. Supported: "
        + ", ".join(sorted(CSS_THEMES | PIL_THEMES))
        + " (plus aliases: default, light, dark)"
    )


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("input", help="JSON file path, or '-' for stdin")
    ap.add_argument("output", help="Output PNG path")
    ap.add_argument("--theme", default="mobile_chat")
    ap.add_argument("--transparent", action="store_true")
    ap.add_argument("--width", type=int, default=None)
    ap.add_argument("--text-scale", default=None)
    ap.add_argument("--text-scale-max", type=float, default=None)
    ap.add_argument("--auto-height", action="store_true")
    ap.add_argument("--auto-height-max", type=int, default=None)
    ap.add_argument("--page", type=int, default=1)
    ap.add_argument("--per-page", type=int, default=None)
    ap.add_argument("--css-api-url", default=None)
    ap.add_argument("--transpose", action="store_true")
    ap.add_argument("--cc", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if not ZEBLE_RENDER.exists():
        raise SystemExit(f"Missing renderer script: {ZEBLE_RENDER}")

    with tempfile.TemporaryDirectory(prefix="zenbleTable_") as td:
        tmpdir = Path(td)

        data_str = _read_json_input(args.input)
        data_json = _write_temp_json(data_str, tmpdir)

        cmd = [sys.executable, str(ZEBLE_RENDER), str(data_json), str(args.output)]
        cmd += _theme_to_args(args.theme, tmpdir)

        if args.transparent:
            cmd += ["--transparent"]
        if args.width is not None:
            cmd += ["--width", str(args.width)]
        if args.text_scale is not None:
            cmd += ["--text-scale", str(args.text_scale)]
        if args.text_scale_max is not None:
            cmd += ["--text-scale-max", str(args.text_scale_max)]

        if args.auto_height:
            cmd += ["--auto-height"]
        if args.auto_height_max is not None:
            cmd += ["--auto-height-max", str(args.auto_height_max)]

        if args.page is not None:
            cmd += ["--page", str(max(1, int(args.page)))]
        if args.per_page is not None:
            cmd += ["--per-page", str(max(1, int(args.per_page)))]

        if args.transpose or args.cc:
            cmd += ["--transpose"]

        if args.verbose:
            print("Running:", " ".join(cmd), file=sys.stderr)

        env = os.environ.copy()
        # Default: prefer CSS render FastAPI (if running). Renderer will fallback to local Chrome on errors.
        # Can be overridden via --css-api-url.
        if args.css_api_url:
            env["ZENTABLE_CSS_API_URL"] = str(args.css_api_url)
        else:
            env.setdefault("ZENTABLE_CSS_API_URL", "http://127.0.0.1:8001")

        proc = subprocess.run(cmd, cwd=str(ZEN_ROOT), env=env)
        return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
