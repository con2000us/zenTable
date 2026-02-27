#!/usr/bin/env python3
"""OpenClaw custom-skill renderer shim for ZenTable.

This repository contains the full ZenTable project under /var/www/html/zenTable.
The OpenClaw skill docs expect a lightweight renderer at:
  ~/.openclaw/custom-skills/zentable/table_renderer.py

In this deployment, ~/.openclaw/custom-skills/zentable is a symlink to:
  /var/www/html/zenTable/skills/zentable

So we provide this shim here.

Interface (kept compatible with the SKILL.md examples):
  echo '{json}' | table_renderer.py - /tmp/out.png --theme mobile_chat

Implementation:
  - CSS themes (mobile_chat, minimal_ios, bubble_card, modern_line, compact_clean)
    render via scripts/zentable_render.py --force-css.
  - default_light/default_dark render via scripts/zentable_render.py --force-pil
    using the bundled theme zip.

Notes:
  - We intentionally depend on the local ZenTable scripts and themes; this is
    host-specific and not meant for upstream OpenClaw repo.
"""

from __future__ import annotations

import argparse
import math
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ZEN_ROOT = Path("/var/www/html/zenTable")
# Use a single stable entrypoint under the skill folder for dev/testing/distribution.
ZEBLE_RENDER = ZEN_ROOT / "skills" / "zentable" / "zentable_renderer.py"
THEMES_CSS = ZEN_ROOT / "themes" / "css"
THEMES_PIL_ZIP = ZEN_ROOT / "themes" / "pil"
DEFAULT_ROWS_PER_PAGE = 15

def _discover_css_themes() -> set[str]:
    themes: set[str] = set()
    if THEMES_CSS.exists():
        for p in THEMES_CSS.iterdir():
            if p.is_dir() and (p / "template.json").exists():
                themes.add(p.name)
            elif p.is_file() and p.suffix == ".zip":
                themes.add(p.stem)
    return themes


def _discover_pil_themes() -> set[str]:
    themes: set[str] = set()
    if THEMES_PIL_ZIP.exists():
        for p in THEMES_PIL_ZIP.iterdir():
            if p.is_file() and p.suffix == ".zip":
                themes.add(p.stem)
    return themes


CSS_THEMES = _discover_css_themes()
PIL_THEMES = _discover_pil_themes()


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


def _count_rows(data_obj: object) -> int:
    """Count logical rows for pagination estimation."""
    if isinstance(data_obj, list):
        return len(data_obj)
    if isinstance(data_obj, dict):
        rows = data_obj.get("rows")
        if isinstance(rows, list):
            return len(rows)
    return 0


def _parse_page_spec(spec: str) -> tuple[str, int, int | None]:
    """
    Parse page spec into:
      ("single", n, None)
      ("range", a, b)
      ("from", a, None)
      ("all", 1, None)
    """
    s = (spec or "").strip().lower()
    if not s:
        return ("single", 1, None)
    if s == "all":
        return ("all", 1, None)
    if re.fullmatch(r"\d+", s):
        n = max(1, int(s))
        return ("single", n, None)
    m = re.fullmatch(r"(\d+)-(\d+)", s)
    if m:
        a = max(1, int(m.group(1)))
        b = max(1, int(m.group(2)))
        if a > b:
            raise SystemExit(f"Invalid --page range '{spec}': start must be <= end")
        return ("range", a, b)
    m = re.fullmatch(r"(\d+)-", s)
    if m:
        a = max(1, int(m.group(1)))
        return ("from", a, None)
    raise SystemExit(
        f"Invalid --page '{spec}'. Supported: N, A-B, A-, all"
    )


def _resolve_pages(
    total_pages: int,
    page_spec: str | None,
    use_all: bool,
    default_cap: int = 3,
) -> tuple[list[int], bool]:
    """
    Return (pages, truncated_by_default_cap).
    """
    total_pages = max(1, int(total_pages))
    if use_all:
        return (list(range(1, total_pages + 1)), False)

    if page_spec is None:
        pages = list(range(1, min(default_cap, total_pages) + 1))
        return (pages, total_pages > default_cap)

    kind, a, b = _parse_page_spec(page_spec)
    if kind == "all":
        return (list(range(1, total_pages + 1)), False)
    if kind == "single":
        if a > total_pages:
            raise SystemExit(f"--page {a} exceeds total pages ({total_pages})")
        return ([a], False)
    if kind == "range":
        if a > total_pages:
            raise SystemExit(f"--page {a}-{b} exceeds total pages ({total_pages})")
        return (list(range(a, min(b, total_pages) + 1)), False)
    # kind == "from"
    if a > total_pages:
        raise SystemExit(f"--page {a}- exceeds total pages ({total_pages})")
    return (list(range(a, total_pages + 1)), False)


def _output_for_page(output_path: str, page: int, pages: list[int]) -> str:
    """Keep original path for single page; suffix .pN for multi-page output."""
    if len(pages) == 1:
        return output_path
    p = Path(output_path)
    suffix = p.suffix
    if suffix:
        return str(p.with_name(f"{p.stem}.p{page}{suffix}"))
    return str(p.with_name(f"{p.name}.p{page}"))


def _theme_to_args(theme: str, tmpdir: Path) -> list[str]:
    theme = theme.strip()

    # CSS theme as folder: themes/css/<theme>/template.json
    theme_file = THEMES_CSS / theme / "template.json"
    if theme_file.exists():
        return ["--force-css", "--theme", str(theme_file)]

    # CSS theme distributed as zip under themes/css/*.zip
    zip_path = THEMES_CSS / f"{theme}.zip"
    if zip_path.exists():
        extract_dir = tmpdir / f"theme_css_{theme}"
        extract_dir.mkdir(parents=True, exist_ok=True)
        shutil.unpack_archive(str(zip_path), str(extract_dir))
        theme_file = extract_dir / "template.json"
        if not theme_file.exists():
            raise SystemExit(f"CSS theme template.json missing after unzip: {theme_file}")
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
    ap.add_argument("--theme", "-t", default="mobile_chat")
    ap.add_argument("--transparent", action="store_true")
    ap.add_argument("--width", "-w", type=int, default=None)
    ap.add_argument("--text-scale", "--ts", default=None)
    ap.add_argument("--text-scale-max", type=float, default=None)
    ap.add_argument("--auto-height", action="store_true")
    ap.add_argument("--auto-height-max", type=int, default=None)
    ap.add_argument("--auto-width", action="store_true")
    ap.add_argument("--no-auto-width", action="store_true")
    ap.add_argument("--auto-width-max", type=int, default=None)
    ap.add_argument("--page", "--p", default=None,
                    help="Page spec: N, A-B, A-, or all")
    ap.add_argument("--all", action="store_true",
                    help="Equivalent to --page all")
    ap.add_argument("--per-page", "--pp", type=int, default=None)
    ap.add_argument("--sort", default=None,
                    help="Sort spec, e.g. 欄位A or 欄位A>欄位B or 欄位A:desc,欄位B:asc")
    ap.add_argument("--asc", action="store_true")
    ap.add_argument("--desc", action="store_true")
    ap.add_argument("--f", "--filter", action="append", default=[],
                    help="Filter spec, e.g. col:!備註,附件 or row:狀態!=停用")
    ap.add_argument("--smart-wrap", action="store_true")
    ap.add_argument("--no-smart-wrap", action="store_true")
    ap.add_argument("--nosw", action="store_true")
    ap.add_argument("--css-api-url", default=None)
    ap.add_argument("--tt", action="store_true")
    ap.add_argument("--transpose", action="store_true")
    ap.add_argument("--cc", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if not ZEBLE_RENDER.exists():
        raise SystemExit(f"Missing renderer script: {ZEBLE_RENDER}")

    with tempfile.TemporaryDirectory(prefix="zentable_") as td:
        tmpdir = Path(td)

        data_str = _read_json_input(args.input)
        data_obj = json.loads(data_str)
        data_json = _write_temp_json(data_str, tmpdir)

        per_page = max(1, int(args.per_page)) if args.per_page is not None else DEFAULT_ROWS_PER_PAGE
        total_rows = _count_rows(data_obj)
        total_pages = max(1, int(math.ceil(total_rows / float(per_page)))) if total_rows else 1
        pages, truncated = _resolve_pages(total_pages, args.page, args.all, default_cap=3)

        env = os.environ.copy()
        # Default: prefer CSS render FastAPI (if running). Renderer will fallback to local Chrome on errors.
        # Can be overridden via --css-api-url.
        if args.css_api_url:
            env["ZENTABLE_CSS_API_URL"] = str(args.css_api_url)
        else:
            env.setdefault("ZENTABLE_CSS_API_URL", "http://127.0.0.1:8001")

        if truncated:
            remaining = total_pages - len(pages)
            print(
                f"[zenTable] Default output limited to first {len(pages)} pages. "
                f"{remaining} page(s) not rendered. Use --page 4- or --all.",
                file=sys.stderr,
            )

        last_code = 0
        for page in pages:
            out_path = _output_for_page(args.output, page, pages)
            cmd = [sys.executable, str(ZEBLE_RENDER), str(data_json), str(out_path)]
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

            if args.auto_width:
                cmd += ["--auto-width"]
            if args.no_auto_width:
                cmd += ["--no-auto-width"]
            if args.auto_width_max is not None:
                cmd += ["--auto-width-max", str(args.auto_width_max)]

            cmd += ["--page", str(page), "--per-page", str(per_page)]
            if args.sort:
                cmd += ["--sort", str(args.sort)]
            if args.desc:
                cmd += ["--desc"]
            elif args.asc:
                cmd += ["--asc"]
            for fexpr in (args.f or []):
                cmd += ["--f", str(fexpr)]

            if args.tt:
                cmd += ["--tt"]
            if args.transpose or args.cc:
                cmd += ["--transpose"]

            # Smart-wrap: default is ON in renderer; allow explicit on/off passthrough
            if args.smart_wrap:
                cmd += ["--smart-wrap"]
            if args.no_smart_wrap or args.nosw:
                cmd += ["--no-smart-wrap"]

            if args.verbose:
                print("Running:", " ".join(cmd), file=sys.stderr)

            proc = subprocess.run(cmd, cwd=str(ZEN_ROOT), env=env)
            last_code = proc.returncode
            if last_code != 0:
                return last_code
        return last_code


if __name__ == "__main__":
    raise SystemExit(main())
