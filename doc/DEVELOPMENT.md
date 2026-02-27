# ZenTable 開發流程文檔（2026-02 更新）

## 目前有效程式入口

```
/var/www/html/zenTable/
├── scripts/
│   ├── zeble_render.py        # 唯一 CLI 入口（CSS/PIL/ASCII）
│   ├── zentable_render.py     # symlink -> zeble_render.py（相容名）
│   └── zentable/              # 模組化實作（input/transform/output/orchestration）
├── themes/                    # css/pil/text 主題
├── tests/golden/              # golden baseline 與驗證腳本
└── doc/                       # 文件
```

> `scripts/zeble.py` 與 `doc/*.py` 舊稿已封存到 `doc/archive/deprecated_code/`，不再作為開發來源。

## 開發流程

1. 修改 `scripts/` 與 `scripts/zentable/` 內程式碼。
2. 必跑驗證：
   - `python3 -m py_compile scripts/zeble_render.py`
   - `bash tests/golden/run_golden.sh`
3. 如有 auto-width 相關調整，補跑：
   - `python3 scripts/zentable_render.py tests/golden/input.json /tmp/css_auto_check.png --force-css --theme-name minimal_ios --auto-width`

## 主要 API 端點

- `gentable_css.php` → `zeble_render.py --force-css`
- `gentable_pil.php` → `zeble_render.py --force-pil`
- `gentable_ascii.php` → `zeble_render.py --force-ascii`
- `gentable.php` → **deprecated**（僅回傳棄用訊息）

## 備註

- 部署相容路徑維持 `/zenTable/...`。
- Golden 目前已驗證可重現（同 commit/同環境下穩定）。
