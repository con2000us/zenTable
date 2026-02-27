#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p tests/golden/tmp

python3 scripts/zentable_render.py tests/golden/input.json tests/golden/tmp/out_css.png --force-css --theme-name minimal_ios >/tmp/golden_css_run.log 2>&1
python3 scripts/zentable_render.py tests/golden/input.json tests/golden/tmp/out_pil.png --force-pil --theme-name default_dark >/tmp/golden_pil_run.log 2>&1
python3 scripts/zentable_render.py tests/golden/input.json tests/golden/tmp/ascii_dummy.txt --force-ascii --output-ascii tests/golden/tmp/out_ascii.txt --theme-name default >/tmp/golden_ascii_run.log 2>&1

cmp -s tests/golden/expected_css.png tests/golden/tmp/out_css.png
cmp -s tests/golden/expected_pil.png tests/golden/tmp/out_pil.png
cmp -s tests/golden/expected_ascii.txt tests/golden/tmp/out_ascii.txt

echo "golden ok"
