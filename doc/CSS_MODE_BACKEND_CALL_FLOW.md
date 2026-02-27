# ZenTable Python 檔案與 CSS Mode 後端渲染呼叫流程

## 一、專案內 Python 檔案一覽（不含 venv）

| 檔案 | 說明 |
|------|------|
| **calibrate_analyze.py** | 校準分析：上傳截圖後分析校準區塊、產生 calibration JSON。**不參與 CSS 後端渲染**。 |
| **doc/zentable_render.py** | 文件用參考腳本，不參與執行。 |
| **scripts/zentable_render.py**（實際執行） | 表格渲染主程式：支援 CSS + Chrome、PIL、ASCII 三種模式。**CSS 後端渲染由此腳本完成。** |

> 後端實際呼叫的是本專案 `scripts/zentable_render.py`，由 `gentable_css.php` 以 CLI 呼叫。

---

## 二、CSS Mode 後端渲染呼叫流程（由上而下）

### 2.1 進入點（PHP → Python）

```
gentable_css.php
  └─ shell_exec: python3 zentable_renderer.py <input.json> <output.png> [--theme <file>|--theme-name <name>] [--page N] [--per-page N] [--sort X] [--asc|--desc] [--transparent] [--width N] [--scale N] [--fill-width M] [--bg ...]
       └─ zentable_renderer.py 被執行，從 sys.argv 讀取參數
```

### 2.2 zentable_renderer.py 主流程（CSS 路徑）

```
main()                                    # 行 2307 入口
  │
  ├─ 解析 CLI 參數 (for i in range(3, len(sys.argv)) ...)
  │     data_file, output_file, theme_file / theme_name, page, per_page, sort_by, sort_asc,
  │     force_width, scale_factor, fill_width_method, bg_mode, transparent_bg, ...
  │
  ├─ data = load_json(data_file)          # 行 2382，讀取表格 JSON
  │     └─ load_json(path)                # 行 2098，open + json.load
  │
  ├─ data = normalise_data(data)          # 行 2430，統一為 {headers, rows, title?, footer?}
  │     └─ normalise_data(data)           # 行 2271
  │
  ├─ data = apply_sort_and_page(data, ...) # 行 2431，排序與分頁
  │     └─ apply_sort_and_page()          # 行 2284
  │
  ├─ chrome_available = check_chrome_available()  # 行 2434
  │     └─ check_chrome_available()       # 行 1297，檢查 google-chrome 是否可用
  │
  ├─ theme = get_theme(theme_name, 'css') # 行 2456（無 theme_file 時）
  │     └─ get_theme(theme_name, mode)    # 行 2171
  │           ├─ load_theme_from_themes_dir(theme_name, mode)  # 行 2102，.zip 或 template.json
  │           │     └─ load_json(path)    # 行 2098
  │           └─ （無主題時）list_themes_in_dir(mode) → 取第一個或回傳 None
  │
  └─ 【CSS 分支】mode.startswith("CSS") and chrome_available  # 行 2516
        │
        ├─ vw, vh, explicit_width = estimate_css_viewport_width_height(data, theme)  # 行 2517
        │     └─ estimate_css_viewport_width_height(data, theme)   # 行 1494
        │           ├─ _parse_font_size_px(th_style, 18)             # 行 1436
        │           ├─ _parse_font_size_px(td_style, 14)
        │           ├─ _parse_padding_vertical_px(td_style)        # 行 1460
        │           ├─ _parse_padding_vertical_px(th_style)
        │           ├─ measure_text_width(text, font_size)        # 行 1923（每欄標題與儲存格）
        │           │     └─ split_text_by_font(text)               # 行 1892，get_font_cjk / get_font_emoji
        │           ├─ cell_text(row[i])                           # 行 2236 → normalize_cell() 行 2213
        │           ├─ _parse_padding_px(body_style)              # 行 1453
        │           ├─ _parse_width_px(raw)                        # 行 1443（body/container/table 明確寬度）
        │           └─ 回傳 (vw, vh, explicit_width)
        │
        ├─ （若 --width）依 fill_width_method 調整 vw/vh、table_width_pct、use_scale_post、scale_no_shrink
        │
        ├─ html = generate_css_html(data, theme, transparent=..., table_width_pct=...)  # 行 2546
        │     └─ generate_css_html(data, theme, transparent, table_width_pct)  # 行 1573
        │           ├─ rows_html = build_css_rows_html(rows)        # 行 1583
        │           │     └─ build_css_rows_html(rows)             # 行 2239
        │           │           └─ normalize_cell(raw_cell)        # 行 2213（每個儲存格）
        │           ├─ styles = theme.get("styles", {})
        │           ├─ _inject_font_fallbacks(style_str)           # 行 1616（對每個 style 值，注入 Liberation Sans / Noto Sans CJK TC）
        │           ├─ css_selector(k)                              # 行 1590（.header→.title, .cell-header→th, tr_even→tr.tr_even, col_N→nth-child…）
        │           ├─ _parse_body_bg_hex(styles)                   # 行 1476（非透空時）
        │           ├─ _parse_width_px(_container_style)           # 行 1443
        │           └─ 回傳完整 HTML 字串（含 <style> 與 <body> 內 table 結構）
        │
        ├─ （若 scale_factor != 1.0）vw, vh 乘上 scale_factor
        │
        ├─ use_bg = _parse_body_bg_hex(theme["styles"])  # 行 2562（未指定 --bg 時用主題 body 背景）
        │
        ├─ success = render_css(html, output_file, transparent=..., viewport_width=vw, viewport_height=vh, bg_color=use_bg, skip_crop=explicit_width)  # 行 2564
        │     └─ render_css(html, output_path, transparent, html_dir, viewport_width, viewport_height, bg_color, skip_crop)  # 行 1391
        │           ├─ 寫入暫存 .html 檔
        │           ├─ _hex_to_chrome_bg(bg_color)                  # 行 1382（若指定 bg_color）
        │           ├─ 組出 Chrome CLI：xvfb-run google-chrome --headless --screenshot=... --window-size=vw,vh [--default-background-color=...] file:///...
        │           ├─ os.system(cmd) 執行 Chrome 截圖
        │           ├─ 刪除暫存 .html
        │           └─ 若 not skip_crop: crop_to_content_bounds(output_path, padding=2, transparent=...)  # 行 1339
        │                 └─ crop_to_content_bounds()               # 行 1339，PIL Image 開檔 → 依 alpha 或角落背景 getbbox → crop → 存檔
        │
        └─ （若 success 且 use_scale_post 且 force_width）PIL 讀 output_file → resize → 存檔
```

### 2.3 依「被誰呼叫」整理的函式依賴（僅 CSS 路徑會用到的）

| 函式 | 行號 | 呼叫者（CSS 路徑） |
|------|------|---------------------|
| `main` | 2307 | 程式入口 |
| `load_json` | 2098 | main, get_theme → load_theme_from_themes_dir |
| `normalise_data` | 2271 | main |
| `apply_sort_and_page` | 2284 | main |
| `check_chrome_available` | 1297 | main |
| `get_theme` | 2171 | main |
| `load_theme_from_themes_dir` | 2102 | get_theme |
| `list_themes_in_dir` | 2126 | get_theme（fallback） |
| `estimate_css_viewport_width_height` | 1494 | main |
| `_parse_font_size_px` | 1436 | estimate_css_viewport_width_height |
| `_parse_padding_vertical_px` | 1460 | estimate_css_viewport_width_height |
| `_parse_padding_px` | 1453 | estimate_css_viewport_width_height |
| `_parse_width_px` | 1443 | estimate_css_viewport_width_height |
| `measure_text_width` | 1923 | estimate_css_viewport_width_height |
| `split_text_by_font` | 1892 | measure_text_width |
| `get_font_cjk` / `get_font_emoji` | 1771 / 1812 | measure_text_width（透過 split_text_by_font 使用） |
| `cell_text` | 2236 | estimate_css_viewport_width_height |
| `normalize_cell` | 2213 | cell_text, build_css_rows_html |
| `generate_css_html` | 1573 | main |
| `build_css_rows_html` | 2239 | generate_css_html |
| `_inject_font_fallbacks` | 1616 | generate_css_html（內部對 styles 做 patch） |
| `_parse_body_bg_hex` | 1476 | main（取 use_bg）, generate_css_html |
| `render_css` | 1391 | main |
| `_hex_to_chrome_bg` | 1382 | render_css |
| `crop_to_content_bounds` | 1339 | render_css |

---

## 三、簡化流程圖（CSS 後端渲染）

```
gentable_css.php
    │
    ▼
python3 zentable_renderer.py <data.json> <out.png> [--theme-name NAME] [--width N] ...
    │
    ▼
main()
    │
    ├─ load_json(data_file)           → 讀表格 JSON
    ├─ normalise_data(data)           → 統一 {headers, rows, title?, footer?}
    ├─ apply_sort_and_page(data)      → 排序、分頁
    ├─ check_chrome_available()       → 是否可用 Chrome
    ├─ get_theme(theme_name, 'css')   → load_theme_from_themes_dir / load_json
    │
    ├─ estimate_css_viewport_width_height(data, theme)
    │     ├─ _parse_font_size_px, _parse_padding_vertical_px, _parse_width_px
    │     ├─ measure_text_width()     → split_text_by_font, get_font_cjk/emoji
    │     └─ cell_text()              → normalize_cell
    │
    ├─ generate_css_html(data, theme, transparent, table_width_pct)
    │     ├─ build_css_rows_html(rows) → normalize_cell 每格
    │     ├─ _inject_font_fallbacks(style_str) 對 theme.styles
    │     ├─ css_selector(k) 組出 CSS 選擇器
    │     └─ _parse_body_bg_hex, _parse_width_px
    │
    ├─ render_css(html, output_file, viewport_width=vw, viewport_height=vh, bg_color=use_bg)
    │     ├─ 寫入 .html
    │     ├─ _hex_to_chrome_bg(bg_color) 若需要
    │     ├─ os.system(Chrome --headless --screenshot ...)
    │     └─ crop_to_content_bounds(output_path)
    │
    └─ （可選）PIL resize 後製 → 存檔
```

---

## 四、其他 Python 檔案（不參與 CSS 渲染）

- **calibrate_analyze.py**：由 `calibrate_upload.php` 等上傳流程呼叫，負責解析校準截圖、輸出 calibration 與步驟摘要，與表格「渲染」無關。
- **doc/zentable_render.py**：僅供文件對照，執行時不會被呼叫。

以上即為「現在所有 Python 檔案」與「以 CSS mode 後端渲染為例的 function 呼叫流程」整理。
