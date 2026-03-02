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
SCRIPTS_DIR = ZEN_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from zentable.transform.sort_page import _parse_page_spec, _resolve_page_list

# Use a single stable entrypoint under the skill folder for dev/testing/distribution.
ZEBLE_RENDER = ZEN_ROOT / "skills" / "zentable" / "zentable_renderer.py"
THEMES_CSS = ZEN_ROOT / "themes" / "css"
THEMES_PIL_ZIP = ZEN_ROOT / "themes" / "pil"
THEMES_TEXT = ZEN_ROOT / "themes" / "text"
DEFAULT_ROWS_PER_PAGE = 15
DEFAULT_THEME = "minimal_ios_mobile"
DEFAULT_WIDTH = 450
DEFAULTS_FILE = ZEN_ROOT / "skills" / "zentable" / "zx_defaults.json"
BASE_DEFAULTS = {
    "theme": DEFAULT_THEME,
    "width": DEFAULT_WIDTH,
    "smart_wrap": True,
    "per_page": DEFAULT_ROWS_PER_PAGE,
}

def _load_defaults() -> dict:
    try:
        if DEFAULTS_FILE.exists():
            data = json.loads(DEFAULTS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def _save_defaults(data: dict) -> None:
    DEFAULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    DEFAULTS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _parse_pin_keys(pin_args: list[str]) -> tuple[set[str], bool]:
    keys: set[str] = set()
    pin_all = False
    for raw in pin_args or []:
        rv = str(raw).strip()
        if rv == "__ALL__" or rv == "":
            pin_all = True
            continue
        for token in re.split(r"[\s,]+", rv):
            t = token.strip().lower()
            if not t:
                continue
            keys.add(t)
    aliases = {
        "w": "width",
        "t": "theme",
        "nosw": "smart_wrap",
        "no-smart-wrap": "smart_wrap",
        "smart-wrap": "smart_wrap",
        "sw": "smart_wrap",
        "pp": "per_page",
        "ts": "text_scale",
        "text-scale-max": "text_scale_max",
        "aw": "auto_width",
        "ah": "auto_height",
    }
    normalized: set[str] = set()
    for k in keys:
        normalized.add(aliases.get(k, k))
    return normalized, pin_all


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


def _discover_text_themes() -> set[str]:
    themes: set[str] = set()
    if THEMES_TEXT.exists():
        for p in THEMES_TEXT.iterdir():
            if p.is_dir() and (p / "template.json").exists():
                themes.add(p.name)
            elif p.is_file() and p.suffix == ".zip":
                themes.add(p.stem)
    return themes



TEXT_THEMES = _discover_text_themes()


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
        return ["--force-css", "--theme", str(theme_file), "--auto-height"]

    # CSS theme distributed as zip under themes/css/*.zip
    zip_path = THEMES_CSS / f"{theme}.zip"
    if zip_path.exists():
        extract_dir = tmpdir / f"theme_css_{theme}"
        extract_dir.mkdir(parents=True, exist_ok=True)
        shutil.unpack_archive(str(zip_path), str(extract_dir))
        theme_file = extract_dir / "template.json"
        if not theme_file.exists():
            raise SystemExit(f"CSS theme template.json missing after unzip: {theme_file}")
        return ["--force-css", "--theme", str(theme_file), "--auto-height"]

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
        return ["--force-pil", "--theme", str(theme_file), "--auto-height"]

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



def _ascii_theme_fallback(theme: str) -> str:
    t = (theme or "").strip()
    if t in TEXT_THEMES:
        return t
    # map visual themes to text defaults
    aliases = {
        "default_dark": "default",
        "default_light": "default",
        "dark": "default",
        "light": "default",
    }
    t2 = aliases.get(t, t)
    if t2 in TEXT_THEMES:
        return t2
    if "default" in TEXT_THEMES:
        return "default"
    if TEXT_THEMES:
        return sorted(TEXT_THEMES)[0]
    return "default"

def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("input", help="JSON file path, or '-' for stdin")
    ap.add_argument("output", help="Output PNG path")
    ap.add_argument("--theme", "-t", default="minimal_ios_mobile")
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
    ap.add_argument("--both", "--bo", action="store_true",
                    help="Besides PNG, also output ASCII table to same path with .txt extension")
    ap.add_argument("--smart-wrap", action="store_true")
    ap.add_argument("--no-smart-wrap", action="store_true")
    ap.add_argument("--nosw", action="store_true")
    ap.add_argument("--css-api-url", default=None)
    ap.add_argument("--tt", action="store_true")
    ap.add_argument("--transpose", action="store_true")
    ap.add_argument("--cc", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--pin", nargs="?", const="__ALL__", action="append", default=[],
                    help="Persist defaults. Use --pin (all current params) or --pin width,nosw,theme")
    ap.add_argument("--pin-reset", action="store_true",
                    help="Reset persisted defaults to baseline (minimal_ios_mobile + width=450, smart_wrap=true, per_page=15)")
    args = ap.parse_args()

    if args.pin_reset:
        _save_defaults(dict(BASE_DEFAULTS))
        print("[zenTable] defaults reset to baseline", file=sys.stderr)

    defaults = _load_defaults()
    final_theme = args.theme if args.theme else str(defaults.get("theme") or DEFAULT_THEME)

    final_width = args.width
    if final_width is None:
        dwidth = defaults.get("width")
        if isinstance(dwidth, int) and dwidth > 0:
            final_width = dwidth
        else:
            final_width = DEFAULT_WIDTH

    explicit_sw = bool(args.smart_wrap or args.no_smart_wrap or args.nosw)
    if explicit_sw:
        final_smart_wrap = bool(args.smart_wrap) and not bool(args.no_smart_wrap or args.nosw)
    else:
        final_smart_wrap = bool(defaults.get("smart_wrap", True))

    final_per_page = max(1, int(args.per_page)) if args.per_page is not None else int(defaults.get("per_page") or DEFAULT_ROWS_PER_PAGE)

    final_text_scale = args.text_scale if args.text_scale is not None else defaults.get("text_scale")
    final_text_scale_max = args.text_scale_max if args.text_scale_max is not None else defaults.get("text_scale_max")
    final_transparent = bool(args.transparent) if args.transparent else bool(defaults.get("transparent", False))
    final_auto_height = bool(args.auto_height) if args.auto_height else bool(defaults.get("auto_height", False))
    final_auto_height_max = args.auto_height_max if args.auto_height_max is not None else defaults.get("auto_height_max")

    explicit_auto_width = bool(args.auto_width or args.no_auto_width)
    if explicit_auto_width:
        final_auto_width = bool(args.auto_width)
    else:
        final_auto_width = bool(defaults.get("auto_width", False))
    final_auto_width_max = args.auto_width_max if args.auto_width_max is not None else defaults.get("auto_width_max")

    if not ZEBLE_RENDER.exists():
        raise SystemExit(f"Missing renderer script: {ZEBLE_RENDER}")

    with tempfile.TemporaryDirectory(prefix="zentable_") as td:
        tmpdir = Path(td)

        data_str = _read_json_input(args.input)
        data_obj = json.loads(data_str)
        data_json = _write_temp_json(data_str, tmpdir)

        per_page = final_per_page
        total_rows = _count_rows(data_obj)
        total_pages = max(1, int(math.ceil(total_rows / float(per_page)))) if total_rows else 1

        if args.all:
            pages = list(range(1, total_pages + 1))
            truncated = False
        elif args.page is None:
            pages = list(range(1, min(3, total_pages) + 1))
            truncated = total_pages > 3
        else:
            try:
                pages, _ = _resolve_page_list(total_rows=total_rows, per_page=per_page, page_spec=args.page, use_all=False)
            except ValueError as e:
                raise SystemExit(str(e))
            truncated = False

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
            cmd += _theme_to_args(final_theme, tmpdir)

            if final_transparent:
                cmd += ["--transparent"]
            if final_width is not None:
                cmd += ["--width", str(final_width)]
            if final_text_scale is not None:
                cmd += ["--text-scale", str(final_text_scale)]
            if final_text_scale_max is not None:
                cmd += ["--text-scale-max", str(final_text_scale_max)]

            if final_auto_height:
                cmd += ["--auto-height"]
            if final_auto_height_max is not None:
                cmd += ["--auto-height-max", str(final_auto_height_max)]

            if final_auto_width:
                cmd += ["--auto-width"]
            else:
                cmd += ["--no-auto-width"]
            if final_auto_width_max is not None:
                cmd += ["--auto-width-max", str(final_auto_width_max)]

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

            # Smart-wrap default can be pinned; explicit flags still take precedence.
            if final_smart_wrap:
                cmd += ["--smart-wrap"]
            else:
                cmd += ["--no-smart-wrap"]

            if args.verbose:
                print("Running:", " ".join(cmd), file=sys.stderr)

            proc = subprocess.run(cmd, cwd=str(ZEN_ROOT), env=env)
            last_code = proc.returncode
            if last_code != 0:
                return last_code

            if args.both:
                txt_out = str(Path(out_path).with_suffix('.txt'))
                ascii_theme = _ascii_theme_fallback(final_theme)
                cmd_ascii = [
                    sys.executable, str(ZEBLE_RENDER), str(data_json), str(out_path),
                    "--force-ascii", "--output-ascii", txt_out,
                    "--theme-name", ascii_theme,
                    "--page", str(page), "--per-page", str(per_page),
                ]
                if args.sort:
                    cmd_ascii += ["--sort", str(args.sort)]
                if args.desc:
                    cmd_ascii += ["--desc"]
                elif args.asc:
                    cmd_ascii += ["--asc"]
                for fexpr in (args.f or []):
                    cmd_ascii += ["--f", str(fexpr)]
                if args.transpose or args.cc:
                    cmd_ascii += ["--transpose"]
                if final_smart_wrap:
                    cmd_ascii += ["--smart-wrap"]
                else:
                    cmd_ascii += ["--no-smart-wrap"]
                if args.verbose:
                    print("Running:", " ".join(cmd_ascii), file=sys.stderr)
                proc2 = subprocess.run(cmd_ascii, cwd=str(ZEN_ROOT), env=env)
                if proc2.returncode != 0:
                    print(f"⚠️  both 模式寫入 ASCII 失敗: text theme fallback={ascii_theme}", file=sys.stderr)

        pin_keys, pin_all = _parse_pin_keys(args.pin)
        if pin_all:
            pin_keys = pin_keys | {
                "theme", "width", "smart_wrap", "per_page", "text_scale", "text_scale_max",
                "transparent", "auto_height", "auto_height_max", "auto_width", "auto_width_max"
            }

        if pin_keys:
            new_defaults = dict(defaults)
            if "theme" in pin_keys:
                new_defaults["theme"] = final_theme
            if "width" in pin_keys:
                new_defaults["width"] = int(final_width) if final_width is not None else DEFAULT_WIDTH
            if "smart_wrap" in pin_keys:
                new_defaults["smart_wrap"] = bool(final_smart_wrap)
            if "per_page" in pin_keys:
                new_defaults["per_page"] = int(per_page)
            if "text_scale" in pin_keys:
                new_defaults["text_scale"] = final_text_scale
            if "text_scale_max" in pin_keys:
                new_defaults["text_scale_max"] = final_text_scale_max
            if "transparent" in pin_keys:
                new_defaults["transparent"] = bool(final_transparent)
            if "auto_height" in pin_keys:
                new_defaults["auto_height"] = bool(final_auto_height)
            if "auto_height_max" in pin_keys:
                new_defaults["auto_height_max"] = final_auto_height_max
            if "auto_width" in pin_keys:
                new_defaults["auto_width"] = bool(final_auto_width)
            if "auto_width_max" in pin_keys:
                new_defaults["auto_width_max"] = final_auto_width_max
            _save_defaults(new_defaults)
            mode = "all-current" if pin_all else "selected"
            print(f"[zenTable] pinned defaults ({mode}): {', '.join(sorted(pin_keys))}", file=sys.stderr)

        return last_code


if __name__ == "__main__":
    raise SystemExit(main())
