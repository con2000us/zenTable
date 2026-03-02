#!/usr/bin/env python3
"""CLI orchestration entry for zeble_render main()."""

from __future__ import annotations


def run_cli_main(zr):
    # Bind legacy globals/functions from zeble_render into this module scope
    globals().update(zr.__dict__)
    if len(sys.argv) < 3:
        print(__doc__)
        print("\n用法: python3 zentable_renderer.py <data.json> <output.png> [options]")
        print("\n選項:")
        print('  --force-pil     強制使用 PIL')
        print('  --force-css     強制使用 CSS + Chrome')
        print('  --transparent   產出透空背景 PNG')
        print('  --bg MODE      背景：transparent | theme | #RRGGBB')
        print('  --width N      強制 viewport/輸出寬度')
        print('  --text-scale S  （僅 CSS）文字/間距縮放：smallest|small|auto|large|largest 或數值（如 1.4）')
        print('  --text-scale-max M  （僅 CSS, auto）自動縮放上限（預設 2.5）')
        print('  --scale N      輸出尺寸倍數')
        print('  --auto-height  自動高度（用較高 viewport 渲染後，依像素內容裁切高度）')
        print('  --auto-height-max H  auto-height 預渲染高度上限（預設 3600）')
        print('  --auto-width   自動寬度（先量測/渲染後，必要時加寬再重渲）')
        print('  --auto-width-max W  auto-width 起始寬度（預設 2400）')
        print('  --no-auto-width / --no-aw  關閉自動寬度')
        print('  --per-page N / --pp N  每頁列數（預設 %d）' % ROWS_PER_PAGE)
        print('  --fill-width   background|container|scale|no-shrink（搭配 --width）')
        print('  --theme FILE    主題檔案（直接用於測試，不儲存）')
        print('  --theme-name    themes/ 目錄中的主題名稱')
        print('  --tt           透明模式：保留 theme 內 rgba/#RRGGBBAA 的 alpha（非 tt 會強制去除 alpha 變不透明）')
        print('  --no-tt        關閉透明模式（覆蓋 theme defaults 的 tt）')
        print('  --page N|A-B|A-|all / --p ...  頁碼範圍（每頁 %d 列）' % ROWS_PER_PAGE)
        print('  --all          等價 --page all')
        print('  --transpose     轉置表格（header 變第一欄；適合手機閱讀）')
        print('  --cc            --transpose 的別名')
        print('  --debug-auto-width  儲存每次 auto-width 嘗試的右側邊界裁切圖（用於診斷）')
        print('  --debug-auto-width-strip N  右側裁切寬度（預設 40px）')
        print('  --wrap-gap N   固定寬度模式用：viewport 變成 (width+N)，但排版寬度縮成 calc(100%-N) 以強制更早換行（避免右側溢出）')
        print('  --smart-wrap    啟用智慧換行（預設開）')
        print('  --no-smart-wrap / --nosw / nosw  關閉智慧換行，保留原始文字斷行')
        print('  --sort <欄位規格>   排序；支援單鍵或多鍵（例：分數>等級>姓名、分數:desc,姓名:asc）')
        print('  --asc           升序（預設）')
        print('  --desc          降序')
        print('  --f / --filter  過濾（例：col:!備註,附件；row:狀態!=停用；row:分數>=60;等級 in 甲|乙）')
        print('  --both / --bo   除 PNG 外同時輸出 ASCII（同主檔名 .txt）')
        print("\n可用主題 (themes/css/):", ', '.join(list_themes_in_dir('css')) or '(無)')
        print("可用主題 (themes/pil/):", ', '.join(list_themes_in_dir('pil')) or '(無)')
        print("可用主題 (themes/text/):", ', '.join(list_themes_in_dir('text')) or '(無)')
        sys.exit(1)

    data_file = sys.argv[1]
    output_file = sys.argv[2]

    force_pil = False
    force_css = False
    force_ascii = False
    theme_file = None
    theme_name = "default_dark"
    custom_params = {}
    output_ascii = None  # 如果指定則輸出 ASCII 到檔案
    output_both = False  # --both/--bo：除 PNG 外同時輸出 ASCII
    calibration_json = None  # 字元寬度校準數據
    page = 1
    page_spec = None
    all_pages = False
    sort_by = None
    sort_asc = True
    filter_specs = []
    transpose = False
    bg_mode = "theme"  # transparent | theme | #RRGGBB
    force_width = None
    text_scale = None
    text_scale_mode = "auto"
    text_scale_max = 2.5
    scale_factor = 1.0
    per_page = ROWS_PER_PAGE
    fill_width_method = "container"  # background | container | scale | no-shrink

    tt = False
    tt_set = False

    auto_height = False
    auto_height_set = False
    auto_height_max = 3600

    auto_width = False
    auto_width_set = False
    auto_width_max = 2400

    width_set = False
    text_scale_set = False
    text_scale_max_set = False

    # 延遲匯入 CSS renderer（避免循環依賴）
    def _get_css_renderer():
        if not hasattr(_get_css_renderer, '_cached'):
            from zentable.output.css.renderer import generate_css_html
            _get_css_renderer._cached = generate_css_html
        return _get_css_renderer._cached

    debug_auto_width = False
    debug_auto_width_strip = 40

    # 預設啟用智慧換行；可用 --no-smart-wrap/--nosw 關閉
    smart_wrap = True

    wrap_gap = 0  # explicit: shrink effective layout width by gap; viewport becomes (width+gap)

    for i in range(3, len(sys.argv)):
        arg = sys.argv[i]
        if arg == "--force-pil":
            force_pil = True
        elif arg == "--force-css":
            force_css = True
        elif arg == "--force-ascii":
            force_ascii = True
        elif arg == "--theme" and i + 1 < len(sys.argv):
            theme_file = sys.argv[i + 1]
        elif arg == "--theme-name" and i + 1 < len(sys.argv):
            theme_name = sys.argv[i + 1]
        elif arg == "--tt":
            tt = True
            tt_set = True
        elif arg == "--no-tt":
            tt = False
            tt_set = True
        elif arg == "--params" and i + 1 < len(sys.argv):
            try:
                custom_params = json.loads(sys.argv[i + 1])
            except:
                print("⚠️  無效的 params JSON", file=sys.stderr)
        elif arg == "--output-ascii" and i + 1 < len(sys.argv):
            output_ascii = sys.argv[i + 1]
        elif arg == "--both" or arg == "--bo":
            output_both = True
        elif arg == "--transparent":
            pass  # 在下方用 transparent_flag 累加
        elif (arg == "--page" or arg == "--p") and i + 1 < len(sys.argv):
            page_spec = str(sys.argv[i + 1]).strip()
            # 若為數字，維持原有單頁流程；範圍/all 稍後統一處理
            if re.fullmatch(r"\d+", page_spec):
                page = max(1, int(page_spec))
        elif arg == "--all":
            all_pages = True
        elif arg == "--sort" and i + 1 < len(sys.argv):
            sort_by = sys.argv[i + 1]
        elif arg == "--asc":
            sort_asc = True
        elif arg == "--desc":
            sort_asc = False
        elif (arg == "--f" or arg == "--filter") and i + 1 < len(sys.argv):
            filter_specs.append(sys.argv[i + 1])
        elif arg == "--transpose" or arg == "--cc":
            transpose = True
        elif arg == "--debug-auto-width":
            debug_auto_width = True
        elif arg == "--debug-auto-width-strip" and i + 1 < len(sys.argv):
            try:
                debug_auto_width_strip = max(10, int(sys.argv[i + 1]))
                debug_auto_width = True
            except ValueError:
                pass
        elif arg == "--wrap-gap" and i + 1 < len(sys.argv):
            try:
                wrap_gap = max(0, int(sys.argv[i + 1]))
            except ValueError:
                pass
        elif arg == "--smart-wrap":
            smart_wrap = True
        elif arg == "--no-smart-wrap" or arg == "--nosw" or arg == "nosw":
            smart_wrap = False
        elif arg == "--bg" and i + 1 < len(sys.argv):
            bg_mode = sys.argv[i + 1].strip().lower()
        elif arg == "--width" and i + 1 < len(sys.argv):
            try:
                force_width = max(1, int(sys.argv[i + 1]))
                width_set = True
            except ValueError:
                pass
        elif arg == "--text-scale" and i + 1 < len(sys.argv):
            raw = sys.argv[i + 1].strip()
            raw_lower = raw.lower()
            text_scale_set = True
            if raw_lower in ("smallest", "small", "auto", "large", "largest"):
                text_scale = None
                text_scale_mode = raw_lower
            else:
                try:
                    text_scale = float(raw)
                    text_scale_mode = "auto"
                except ValueError:
                    text_scale = None
                    text_scale_mode = "auto"
        elif arg == "--text-scale-max" and i + 1 < len(sys.argv):
            try:
                text_scale_max = float(sys.argv[i + 1])
                text_scale_max_set = True
            except ValueError:
                pass
        elif arg == "--scale" and i + 1 < len(sys.argv):
            try:
                scale_factor = max(0.1, min(5.0, float(sys.argv[i + 1])))
            except ValueError:
                pass
        elif (arg == "--per-page" or arg == "--pp") and i + 1 < len(sys.argv):
            try:
                per_page = max(1, int(sys.argv[i + 1]))
            except ValueError:
                pass
        elif arg == "--calibration" and i + 1 < len(sys.argv):
            try:
                calibration_json = json.loads(sys.argv[i + 1])
            except:
                print("⚠️  無效的 calibration JSON", file=sys.stderr)
        elif arg == "--fill-width" and i + 1 < len(sys.argv):
            m = sys.argv[i + 1].strip().lower()
            if m in ("background", "container", "scale", "no-shrink"):
                fill_width_method = m
        elif arg == "--auto-height":
            auto_height = True
            auto_height_set = True
        elif arg == "--auto-height-max" and i + 1 < len(sys.argv):
            try:
                auto_height_max = max(200, int(sys.argv[i + 1]))
            except ValueError:
                pass
        elif arg == "--auto-width":
            auto_width = True
            auto_width_set = True
        elif arg == "--no-auto-width" or arg == "--no-aw":
            auto_width = False
            auto_width_set = True
        elif arg == "--auto-width-max" and i + 1 < len(sys.argv):
            try:
                auto_width_max = max(200, int(sys.argv[i + 1]))
            except ValueError:
                pass

    # Default behavior: enable auto-height + auto-width unless the user explicitly set them.
    if not auto_height_set:
        auto_height = True
    if not auto_width_set:
        auto_width = True

    # 背景：--transparent 優先，否則 --bg
    transparent_bg = "--transparent" in sys.argv or bg_mode == "transparent"
    if transparent_bg:
        bg_color = None
    elif bg_mode.startswith("#"):
        bg_color = bg_mode
    else:
        bg_color = None

    # --both/--bo：除 PNG 外同時輸出 ASCII，若未指定 --output-ascii 則由主輸出路徑衍生
    if output_both and not output_ascii:
        output_ascii = os.path.splitext(output_file)[0] + '.txt'

    data = load_json(data_file)

    # 從數據中提取自定義參數（gentable_pil.php 傳入）
    if isinstance(data, dict):
        data_params = data.pop('_params', {})
        custom_params = {**custom_params, **data_params}

    # 統一輸入格式（陣列 of 物件 或 headers+rows）
    data = normalise_data(data)
    if filter_specs:
        data, filter_stats = apply_filters(data, filter_specs=filter_specs)
        if filter_stats.get("applied"):
            print(
                f"🔎 filter 已套用: rows {filter_stats.get('rows_before')} -> {filter_stats.get('rows_after')}, "
                f"cols {filter_stats.get('cols_before')} -> {filter_stats.get('cols_after')}",
                file=sys.stderr,
            )
        for e in (filter_stats.get("errors") or []):
            print(f"⚠️  filter warning: {e}", file=sys.stderr)
    if transpose:
        data = transpose_table(data)

    # page range / all：在同一支腳本內展開逐頁渲染（供其他入口直接呼叫）
    if all_pages or (page_spec is not None and not re.fullmatch(r"\d+", page_spec.strip())):
        total_rows = len(data.get("rows", [])) if isinstance(data, dict) else 0
        try:
            pages, total_pages = _resolve_page_list(total_rows, per_page, page_spec=page_spec, use_all=all_pages)
        except ValueError as e:
            print(f"❌ {e}", file=sys.stderr)
            sys.exit(2)

        base_args = sys.argv[3:]  # 去掉 data_file, output_file
        last_rc = 0
        print(f"📚 page spec 展開: pages={pages} / total_pages={total_pages}", file=sys.stderr)
        for p in pages:
            out_p = _page_output_path(output_file, p, pages)
            child_args = []
            i = 0
            while i < len(base_args):
                a = base_args[i]
                # 移除範圍語法，改用單頁
                if a in ("--all",):
                    i += 1
                    continue
                if a in ("--page", "--p"):
                    i += 2
                    continue
                # 支援 ASCII 多頁輸出檔名
                if a == "--output-ascii" and i + 1 < len(base_args):
                    ascii_out = _page_output_path(base_args[i + 1], p, pages)
                    child_args += [a, ascii_out]
                    i += 2
                    continue
                child_args.append(a)
                i += 1

            cmd = [sys.executable, sys.argv[0], data_file, out_p] + child_args + ["--page", str(p)]
            if "--verbose" in base_args:
                print("Running:", " ".join(cmd), file=sys.stderr)
            rc = subprocess.run(cmd).returncode
            last_rc = rc
            if rc != 0:
                sys.exit(rc)
        sys.exit(last_rc)

    # 再套用排序與分頁
    data = apply_sort_and_page(data, sort_by=sort_by, sort_asc=sort_asc, page=page, per_page=per_page)

    # 預設智慧換行：渲染前先在語意斷點插入換行，減少窄寬表格斷句破壞
    smart_wrap_stats = {"applied": False}
    
    # 決定渲染方式（提前檢查，為 DOM 預檢使用）
    chrome_available = check_chrome_available()
    
    # 如果是固定寬度且使用 CSS，先進行 DOM 預檢查以確定最佳寬度
    precheck_width = None
    print(f"🔍 DOM 預檢條件: smart_wrap={smart_wrap}, width_set={width_set}, chrome={chrome_available}, auto_width={auto_width}", file=sys.stderr)
    if smart_wrap and width_set and chrome_available and not auto_width:
        print(f"🔍 進入 DOM 預檢", file=sys.stderr)
        # 暫時套用 smart-wrap 進行測試
        test_data, _ = apply_smart_wrap(data.copy(), width=force_width)
        # 延遲匯入，避免循環依賴
        from zentable.output.css import chrome as css_chrome
        # 生成測試 HTML
        test_html = _get_css_renderer()(test_data, theme, parse_width_px=lambda x: None, transparent=False)
        # DOM 測量
        dom_info = css_chrome.measure_dom_overflow(test_html, "/tmp", viewport_width=force_width, viewport_height=800)
        print(f"🔍 DOM 測量結果: {dom_info}", file=sys.stderr)
        if isinstance(dom_info, dict):
            body = dom_info.get('body') or {}
            scroll_w = int(body.get('scrollWidth') or 0)
            print(f"🔍 scrollWidth={scroll_w}, force_width={force_width}, 溢出={scroll_w > (force_width + 20)}", file=sys.stderr)
            if scroll_w > (force_width + 20):
                # 需要更大的寬度
                precheck_width = min(scroll_w + 60, auto_width_max or 2400)
                print(f"🔍 預檢建議寬度: {precheck_width}px", file=sys.stderr)
                print(f"🔍 DOM 預檢：指定寬度 {force_width}px 不足，建議使用 {precheck_width}px", file=sys.stderr)
    
    if smart_wrap:
        # 使用預檢後的寬度（如果有）
        wrap_width = precheck_width if precheck_width else force_width
        data, smart_wrap_stats = apply_smart_wrap(data, width=wrap_width)
        if smart_wrap_stats.get("applied"):
            print(
                f"🧠 smart-wrap 已介入：changed_cells={smart_wrap_stats.get('changed_cells')}, "
                f"per_col_limit≈{smart_wrap_stats.get('per_col_limit')}",
                file=sys.stderr,
            )
    
    # 更新 force_width 為預檢後的寬度
    if precheck_width and precheck_width > force_width:
        force_width = precheck_width
        vw = precheck_width

    # 決定渲染方式
    if force_ascii:
        mode = "ASCII"
    elif force_pil:
        mode = "PIL (forced)"
    elif force_css:
        mode = "CSS + Chrome (forced)"
        chrome_available = True
    elif chrome_available:
        mode = "CSS + Chrome"
    else:
        mode = "PIL (fallback)"

    # 避免污染 stdout（特別是 ASCII 模式會直接回傳文本）
    print(f"🖥️  渲染模式: {mode}", file=sys.stderr)

    # 三種模式皆從 themes/<mode>/ 載入主題（或 --theme 指定檔案）
    theme_mode = 'text' if mode == "ASCII" else ('pil' if mode.startswith("PIL") else 'css')
    if theme_file:
        theme = load_json(theme_file)
        print(f"🎨 使用主題檔案: {theme_file}", file=sys.stderr)
    else:
        theme = get_theme(theme_name, theme_mode)

    # Apply theme defaults (template.json -> meta.defaults) when CLI did not explicitly set options
    def _get_theme_defaults(th: dict) -> dict:
        if not isinstance(th, dict):
            return {}
        meta = th.get('meta', {}) if isinstance(th.get('meta', {}), dict) else {}
        d = meta.get('defaults', {}) if isinstance(meta.get('defaults', {}), dict) else {}
        if not d and isinstance(th.get('defaults', {}), dict):
            d = th.get('defaults', {})
        return d if isinstance(d, dict) else {}

    defaults = _get_theme_defaults(theme)
    if defaults:
        if (not tt_set) and ('tt' in defaults):
            try: tt = bool(defaults.get('tt'))
            except Exception: pass

        if (not width_set) and ('width' in defaults):
            try:
                force_width = max(1, int(defaults.get('width')))
                width_set = True
            except Exception: pass

        if (not auto_width_set) and ('auto_width' in defaults):
            try: auto_width = bool(defaults.get('auto_width'))
            except Exception: pass

        if (not auto_height_set) and ('auto_height' in defaults):
            try: auto_height = bool(defaults.get('auto_height'))
            except Exception: pass

    # 規則：只要有設定 --width（或由 theme defaults 套入 width），就自動關閉 auto-width。
    # 避免最終輸出寬度被 auto-width 擴張，導致文字看起來變小。
    if width_set:
        auto_width = False

        if (not text_scale_set) and ('text_scale' in defaults):
            raw = str(defaults.get('text_scale')).strip()
            raw_lower = raw.lower()
            if raw_lower in ("smallest", "small", "auto", "large", "largest"):
                text_scale = None
                text_scale_mode = raw_lower
            else:
                try:
                    text_scale = float(raw)
                    text_scale_mode = "auto"
                except Exception: pass

        if (not text_scale_max_set) and ('text_scale_max' in defaults):
            try:
                text_scale_max = float(defaults.get('text_scale_max'))
                text_scale_max_set = True
            except Exception: pass

        if ('auto_width_max' in defaults) and (not width_set):
            try: auto_width_max = max(200, int(defaults.get('auto_width_max')))
            except Exception: pass

        if ('auto_height_max' in defaults):
            try: auto_height_max = max(200, int(defaults.get('auto_height_max')))
            except Exception: pass

    # ASCII 模式
    if mode == "ASCII":
        def _truthy(v):
            if isinstance(v, bool):
                return v
            if isinstance(v, (int, float)):
                return v != 0
            if isinstance(v, str):
                s = v.strip().lower()
                return s not in ("", "0", "false", "no", "off", "null", "none")
            return False

        cal = None
        if calibration_json and isinstance(calibration_json, dict):
            if 'char_widths' in calibration_json:
                cal = {'custom': calibration_json['char_widths']}
            else:
                cal = calibration_json
            cats = [k for k in ('ascii','cjk','box','emoji','half_space','full_space') if k in cal]
            custom_count = len(cal.get('custom', {}))
            print(f"📐 收到校準 JSON: 類別={cats}, 自訂字元數={custom_count}", file=sys.stderr)

        # ASCII style：允許 --params 覆蓋（前端即時調整）
        theme_params = (theme or {}).get("params") or {}
        merged_ascii_params = {**(theme_params or {}), **(custom_params or {})}
        ascii_style = ASCIIStyle(
            border_style=merged_ascii_params.get("style", "double"),
            padding=int(merged_ascii_params.get("padding", 2)),
            align=merged_ascii_params.get("align", "left"),
            header_align=merged_ascii_params.get("header_align", "center"),
        )

        ascii_debug = _truthy(merged_ascii_params.get("ascii_debug"))
        stage1_pil_preview = _truthy(merged_ascii_params.get("stage1_pil_preview"))
        stage1_unit_px = merged_ascii_params.get("stage1_unit_px", 10)

        if ascii_debug:
            # stage1/stage2：不套用校準（預設半形=1、全形=2），先產生版面藍圖與參考輸出
            blueprint = {}
            stage2_text = render_ascii(data, theme, style=ascii_style, calibration=None, debug_details=blueprint)

            # stage3：套用校準後的輸出與細節
            calibrated = {}
            ascii_output = render_ascii(data, theme, style=ascii_style, calibration=cal, debug_details=calibrated)
        else:
            blueprint = None
            calibrated = None
            stage2_text = None
            ascii_output = render_ascii(data, theme, style=ascii_style, calibration=cal, debug_details=None)

        if output_ascii:
            if ascii_debug:
                # stage1: 欄寬/對齊計算摘要；stage2: 參考結果（等寬字型）；text: 校準輸出（stage3）
                stage1_lines = []
                if isinstance(blueprint, dict):
                    stage1_lines.extend([
                        "stage1 (blueprint): 不套用校準（預設半形=1.0、全形=2.0）",
                        f"border_style={blueprint.get('border_style')}, padding={blueprint.get('padding')}, align={blueprint.get('align')}, header_align={blueprint.get('header_align')}",
                        f"space_width(sw)={blueprint.get('space_width')}, h='{blueprint.get('h_char')}' width(hw)={blueprint.get('h_char_width')}",
                        f"raw_widths={blueprint.get('raw_widths')}",
                        f"col_h_counts={blueprint.get('col_h_counts')}",
                        f"col_targets={blueprint.get('col_targets')}",
                        f"row_heights={blueprint.get('row_heights')}",
                        f"rows={blueprint.get('nrows')}, cols={blueprint.get('ncols')}",
                    ])

                stage1_pil_image = None
                stage1_pil_warning = None
                if stage1_pil_preview and isinstance(blueprint, dict):
                    try:
                        base = os.path.splitext(os.path.basename(output_ascii))[0]
                        img_name = base + "_stage1.png"
                        img_path = os.path.join(os.path.dirname(output_ascii), img_name)
                        saved_path, warn = render_ascii_blueprint_pil(blueprint, img_path, stage1_unit_px)
                        if saved_path:
                            stage1_pil_image = "/zenTable/" + os.path.basename(saved_path)
                        if warn:
                            stage1_pil_warning = str(warn)
                    except Exception as e:
                        stage1_pil_warning = f"stage1 PIL 預覽失敗: {e}"

                payload = {
                    "text": ascii_output,
                    "stage1": "\n".join(stage1_lines).strip(),
                    "stage2": stage2_text,
                    "stage3_details": {
                        "blueprint": blueprint,
                        "calibrated": calibrated,
                    },
                    "stage1_pil_image": stage1_pil_image,
                    "stage1_pil_warning": stage1_pil_warning,
                }
                with open(output_ascii, 'w', encoding='utf-8') as f:
                    json.dump(payload, f, ensure_ascii=False)
            else:
                with open(output_ascii, 'w', encoding='utf-8') as f:
                    f.write(ascii_output)
            print(f"✅ 已保存: {output_ascii}")
        else:
            print(ascii_output)

    # 渲染
    elif mode.startswith("CSS") and chrome_available:
        # （僅 CSS）文字/間距縮放：先縮放主題，再估算 viewport 與產生 HTML
        resolved_text_scale = _resolve_text_scale(
            force_width,
            text_scale,
            text_scale_mode=text_scale_mode,
            text_scale_max=text_scale_max
        )
        theme = _scale_css_styles_px(theme, resolved_text_scale)

        vw, vh, explicit_width = estimate_css_viewport_width_height(data, theme)
        # auto-height: 先用足夠高的 viewport 渲染，避免內容因換行而被截斷。
        if auto_height:
            vh = max(vh, auto_height_max)
        # auto-width: 以估算寬度起跑，必要時再放大（避免預設直接放到超寬）
        if auto_width and not explicit_width:
            vw = min(max(560, int(vw)), int(auto_width_max))
        table_width_pct = None
        use_scale_post = False
        scale_no_shrink = False
        if force_width:
            if fill_width_method == "background":
                table_width_pct = None
                vw, vh = force_width, vh
            elif fill_width_method == "container":
                table_width_pct = 96
                vw, vh = force_width, vh
            elif fill_width_method == "scale":
                table_width_pct = None
                use_scale_post = True
                vw, vh = vw, vh  # content-based
            else:  # no-shrink
                table_width_pct = None
                use_scale_post = True
                scale_no_shrink = True
                vw, vh = vw, vh
        # Auto width: 使用 autowidth-wrapper 包裹，wrapper 設為 90%，內部 container 保持 100%
        auto_width_wrapper_pct = None
        if auto_width and not explicit_width and not table_width_pct:
            auto_width_wrapper_pct = 90  # wrapper 寬度 90%，內部保持 100%
        
        html = _get_css_renderer()(data, theme, parse_width_px=_parse_width_px, transparent=transparent_bg, table_width_pct=table_width_pct, tt=tt, auto_width_wrapper_pct=auto_width_wrapper_pct)

        # Explicit, user-controlled wrap gap (only when user passed --width).
        if width_set and force_width and wrap_gap:
            html = _inject_wrap_gap_css(html, gap_px=wrap_gap)
            # viewport becomes width+gap; layout uses calc(100%-gap)
            vw = int(force_width) + int(wrap_gap)

        # (removed: #zentable-fixedwidth-wrap injected table-layout:fixed + max-width:0
        #  which broke cell layout; table-layout: auto is now handled by generate_css_html)

        # Optional debug dump: save full HTML/CSS + resolved render inputs for diffing.
        if os.environ.get("ZENTABLE_DUMP_RENDER_INPUT") == "1":
            try:
                dump_base = output_file
                with open(dump_base + ".input.html", "w", encoding="utf-8") as f:
                    f.write(html)
                # extract combined CSS blocks for convenience
                import re as _re
                css_blocks = _re.findall(r"<style[^>]*>(.*?)</style>", html, flags=_re.S | _re.I)
                with open(dump_base + ".input.css", "w", encoding="utf-8") as f:
                    f.write("\n\n/* ---- style block ---- */\n\n".join([c.strip() for c in css_blocks]))
                input_meta = {
                    "theme_name": theme_name,
                    "theme_mode": theme_mode,
                    "theme_file": theme_file,
                    "transparent": bool(transparent_bg),
                    "tt": bool(tt),
                    "bg_mode": bg_mode,
                    "bg_color": bg_color,
                    "explicit_width": bool(explicit_width),
                    "width_set": bool(width_set) if 'width_set' in locals() else None,
                    "force_width": int(force_width) if force_width else None,
                    "fill_width_method": fill_width_method,
                    "auto_width": bool(auto_width),
                    "auto_height": bool(auto_height),
                    "auto_width_max": int(auto_width_max) if auto_width_max else None,
                    "auto_height_max": int(auto_height_max) if auto_height_max else None,
                    "text_scale_mode": text_scale_mode,
                    "text_scale": float(resolved_text_scale) if resolved_text_scale is not None else None,
                    "scale_factor": float(scale_factor),
                    "wrap_gap": int(wrap_gap) if 'wrap_gap' in locals() else 0,
                }
                import json as _json
                with open(dump_base + ".input.json", "w", encoding="utf-8") as f:
                    f.write(_json.dumps(input_meta, ensure_ascii=False, indent=2))
            except Exception:
                pass
        if scale_factor != 1.0:
            vw = max(1, int(vw * scale_factor))
            vh = max(1, int(vh * scale_factor))
        cache_dir = None
        if not theme_file:
            try:
                cache_dir = ensure_theme_cache(theme_name, theme_mode)
            except ValueError:
                pass
        # auto-height/auto-width: 先用較大 viewport 渲染；若邊界仍有內容，代表可能被截斷，則加倍再重渲。
        # Strategy C: DOM pre-measure (local Chrome only) + pixel edge check.
        if auto_height or auto_width:
            max_hard = MAX_VIEWPORT_DIM
            if auto_width:
                try:
                    max_hard = min(max_hard, int(auto_width_max))
                except Exception:
                    pass
            attempts = 0
            cur_vw = min(vw, max_hard)
            cur_vh = min(vh, max_hard)

            width_steps = []
            render_attempts = []  # [{attempt, vw, vh, css_render_ms}]

            # DOM pre-measure (skip when using remote CSS API)
            # Prefer overflow-based measurement over raw scrollWidth to avoid background/border false positives.
            if auto_width and not os.environ.get("ZENTABLE_CSS_API_URL"):
                try:
                    ov = measure_dom_overflow(html, cache_dir or "/tmp", viewport_width=cur_vw, viewport_height=cur_vh)
                    if ov and (ov.get('body') or ov.get('table')):
                        width_steps.append({"reason": "dom_overflow", "vw": int(cur_vw), **ov})
                        # Prefer BODY overflow for decision (catches elements that spill outside table)
                        src = ov.get('body') or ov.get('table') or {}
                        sw = int(src.get('scrollWidth') or 0)
                        cw = int(src.get('clientWidth') or 0)
                        # Only grow if real overflow exists
                        if sw > (cw + 2) and sw > cur_vw:
                            base_w = int(force_width) if force_width else int(cur_vw)
                            dom_cap = min(max_hard, max(base_w * 2, base_w + 400))
                            need_w = min(int(sw), int(dom_cap))
                            need_w = int(((need_w + 49) // 50) * 50)
                            need_w = min(need_w, max_hard)
                            if need_w > cur_vw:
                                width_steps.append({"reason": "dom", "from": int(cur_vw), "to": int(need_w)})
                                cur_vw = need_w
                    else:
                        need_w = measure_dom_scroll_width(html, cache_dir or "/tmp", viewport_width=cur_vw, viewport_height=cur_vh)
                        if need_w and need_w > cur_vw:
                            base_w = int(force_width) if force_width else int(cur_vw)
                            dom_cap = min(max_hard, max(base_w * 2, base_w + 400))
                            need_w = min(int(need_w), int(dom_cap))
                            need_w = int(((need_w + 49) // 50) * 50)
                            need_w = min(need_w, max_hard)
                            if need_w > cur_vw:
                                width_steps.append({"reason": "dom", "from": int(cur_vw), "to": int(need_w)})
                                cur_vw = need_w
                except Exception:
                    pass

            while True:
                attempts += 1

                # DOM overflow metrics at this viewport (debug/stats)
                attempt_dom = None
                if auto_width and not os.environ.get("ZENTABLE_CSS_API_URL"):
                    try:
                        attempt_dom = measure_dom_overflow(html, cache_dir or "/tmp", viewport_width=cur_vw, viewport_height=cur_vh)
                    except Exception:
                        attempt_dom = None

                success = render_css(
                    html, output_file,
                    transparent=transparent_bg,
                    html_dir=cache_dir,
                    viewport_width=cur_vw,
                    viewport_height=cur_vh,
                    bg_color=bg_color,
                    skip_crop=True,  # 先不裁，才能檢查邊界是否被截
                )
                if success:
                    try:
                        edge_metrics = _right_edge_metrics(output_file, transparent=transparent_bg, x_inset=0)
                        edge_metrics_inset = _right_edge_metrics(output_file, transparent=transparent_bg, x_inset=5)
                        debug_files = None
                        if debug_auto_width:
                            try:
                                from PIL import Image as _Image
                                im = _Image.open(output_file)
                                w, h = im.size
                                dbg_dir = output_file + ".debug"
                                os.makedirs(dbg_dir, exist_ok=True)

                                # full image snapshot for this attempt
                                full_path = os.path.join(dbg_dir, f"attempt_{attempts:02d}_full.png")
                                im.save(full_path, "PNG")

                                # right strip snapshot
                                strip_w = min(int(debug_auto_width_strip), w)
                                strip = im.crop((w - strip_w, 0, w, h))
                                right_path = os.path.join(dbg_dir, f"attempt_{attempts:02d}_right{strip_w}.png")
                                strip.save(right_path, "PNG")

                                debug_files = {"full": full_path, "right_strip": right_path}
                            except Exception:
                                debug_files = None

                        render_attempts.append({
                            "attempt": int(attempts),
                            "vw": int(cur_vw),
                            "vh": int(cur_vh),
                            "css_render_ms": int(LAST_CSS_RENDER_MS) if LAST_CSS_RENDER_MS is not None else None,
                            "dom": attempt_dom,
                            "dom_source": "body" if (attempt_dom and isinstance(attempt_dom, dict) and attempt_dom.get('body')) else "table",
                            "edge": edge_metrics,
                            "edge_inset5": edge_metrics_inset,
                            "debug": debug_files,
                        })
                    except Exception:
                        pass
                else:
                    break

                grew = False
                if auto_height and _bottom_edge_has_content(output_file, transparent=transparent_bg) and cur_vh < max_hard:
                    next_vh = min(cur_vh * 2, max_hard)
                    if next_vh != cur_vh:
                        cur_vh = next_vh
                        grew = True

                # Auto-width edge check:
                # If DOM metrics are available and show no overflow, skip edge-growth
                # (table width:100% can naturally touch right edge without being truncated).
                edge_inset = 50
                dom_overflow_now = None
                if isinstance(attempt_dom, dict):
                    src = attempt_dom.get('body') or attempt_dom.get('table') or {}
                    try:
                        sw_now = int(src.get('scrollWidth') or 0)
                        cw_now = int(src.get('clientWidth') or 0)
                        dom_overflow_now = sw_now > (cw_now + 2)
                    except Exception:
                        dom_overflow_now = None

                allow_edge_growth = True
                if dom_overflow_now is False:
                    allow_edge_growth = False

                if auto_width and allow_edge_growth and _right_edge_has_content(output_file, transparent=transparent_bg, x_inset=edge_inset) and cur_vw < max_hard:
                    next_vw = max(cur_vw + 400, int(cur_vw * 1.25))
                    next_vw = min(next_vw, max_hard)
                    if next_vw != cur_vw:
                        width_steps.append({"reason": "edge", "from": int(cur_vw), "to": int(next_vw), "x_inset": int(edge_inset), "dom_overflow": dom_overflow_now})
                        cur_vw = next_vw
                        grew = True

                if not grew or attempts >= 6:
                    break

            # 最終：
            # - explicit width：不裁左右，只裁高度（避免 width 被改）
            # - 非 explicit：照原本裁切（含左右空白）
            if success:
                if width_set:
                    crop_to_content_height(output_file, transparent=transparent_bg)
                else:
                    crop_to_content_bounds(output_file, padding=2, transparent=transparent_bg)
            print(f"🔍 主循環結束: width_set={width_set}, auto_width={auto_width}", file=sys.stderr)
        else:
            print(f"🔍 進入 else 分支: width_set={width_set}", file=sys.stderr)
            success = render_css(html, output_file, transparent=transparent_bg, html_dir=cache_dir,
                                viewport_width=vw, viewport_height=vh, bg_color=bg_color,
                                skip_crop=width_set)
            
            # 方案 C：當指定寬度但內容溢出時，自動擴大到最小容納寬度
            print(f"🔍 檢查溢出: width_set={width_set}, chrome={chrome_available}", file=sys.stderr)
            if success and width_set and chrome_available:
                # 使用 DOM 測量檢查溢出
                from zentable.output.css import chrome as css_chrome
                from zentable.output.css import crop as css_crop
                max_hard = min(int(auto_width_max), 2400)
                attempts = 0
                cur_vw = int(vw)
                
                while attempts < 3:
                    # 測量 DOM 溢出
                    dom_info = css_chrome.measure_dom_overflow(
                        html, cache_dir or "/tmp", 
                        viewport_width=cur_vw, viewport_height=vh
                    )
                    
                    overflow_detected = False
                    needed_width = cur_vw
                    if isinstance(dom_info, dict):
                        body = dom_info.get('body') or {}
                        table = dom_info.get('table') or {}
                        scroll_w = int(body.get('scrollWidth') or table.get('scrollWidth') or 0)
                        # 關鍵：比較 scrollWidth 與 viewport 寬度，不是 clientWidth
                        if scroll_w > (cur_vw + 10):  # 內容撐開超過 viewport
                            overflow_detected = True
                            needed_width = scroll_w + 60  # 加邊距
                            
                    if not overflow_detected:
                        break
                    
                    # 計算新寬度
                    next_vw = max(cur_vw + 200, int(cur_vw * 1.15), needed_width)
                    next_vw = min(next_vw, max_hard)
                    
                    if next_vw <= cur_vw:
                        break
                    
                    print(f"⚠️ 指定寬度 {cur_vw}px 導致內容溢出 (需要 {scroll_w}px)，自動擴大到 {next_vw}px", file=sys.stderr)
                    cur_vw = next_vw
                    attempts += 1
                    
                    # 用新寬度重新渲染
                    success = render_css(html, output_file, transparent=transparent_bg, html_dir=cache_dir,
                                        viewport_width=cur_vw, viewport_height=vh, bg_color=bg_color,
                                        skip_crop=False)
                    
                    if not success:
                        break
                
                # 最後裁切到內容邊界
                if success:
                    css_crop.crop_to_content_bounds(output_file, padding=2, transparent=transparent_bg)
                
                # 更新 force_width 為實際使用的寬度，避免後製縮放
                if attempts > 0 and cur_vw > force_width:
                    print(f"📏 更新輸出寬度為 {cur_vw}px（原指定 {force_width}px）", file=sys.stderr)
                    force_width = cur_vw

        if success and use_scale_post and force_width:
            try:
                img = Image.open(output_file)
                w, h = img.size
                if scale_no_shrink and w >= force_width:
                    pass  # 不縮小，保持原樣
                else:
                    new_w = force_width
                    new_h = max(1, int(h * force_width / w))
                    try:
                        resample = Image.Resampling.LANCZOS
                    except AttributeError:
                        resample = Image.LANCZOS
                    img = img.resize((new_w, new_h), resample)
                    img.save(output_file, "PNG")
            except Exception as e:
                print(f"⚠️  後製縮放失敗: {e}", file=sys.stderr)
        if success:
            # Write a small sidecar JSON for downstream callers (e.g., zx stats)
            try:
                from PIL import Image as _Image
                out_im = _Image.open(output_file)
                out_w, out_h = out_im.size
                meta = {
                    "render_mode": "CSS",
                    "theme_name": theme_name,
                    "tt": bool(tt),
                    "smart_wrap": bool(smart_wrap),
                    "smart_wrap_stats": smart_wrap_stats if 'smart_wrap_stats' in locals() else None,
                    "text_scale_mode": text_scale_mode,
                    "text_scale": float(resolved_text_scale) if resolved_text_scale is not None else None,
                    "viewport": {"w": int(LAST_CSS_VIEWPORT[0]), "h": int(LAST_CSS_VIEWPORT[1])} if LAST_CSS_VIEWPORT else None,
                    "output": {"w": int(out_w), "h": int(out_h)},
                    "css_render_ms": int(LAST_CSS_RENDER_MS) if LAST_CSS_RENDER_MS is not None else None,
                    "auto_width_steps": width_steps if 'width_steps' in locals() else None,
                    "render_attempts": render_attempts if 'render_attempts' in locals() else None,
                }
                import json as _json
                with open(output_file + ".meta.json", "w", encoding="utf-8") as f:
                    f.write(_json.dumps(meta, ensure_ascii=False, indent=2))
            except Exception:
                pass

            print(f"✅ 已保存: {output_file}")
            if output_ascii:
                try:
                    theme_text = get_theme(theme_name, 'text')
                    theme_params = (theme_text or {}).get("params") or {}
                    merged_ascii = {**(theme_params or {}), **(custom_params or {})}
                    ascii_style_both = ASCIIStyle(
                        border_style=merged_ascii.get("style", "double"),
                        padding=int(merged_ascii.get("padding", 2)),
                        align=merged_ascii.get("align", "left"),
                        header_align=merged_ascii.get("header_align", "center"),
                    )
                    ascii_out = render_ascii(data, theme_text, style=ascii_style_both, calibration=None, debug_details=None)
                    with open(output_ascii, 'w', encoding='utf-8') as f:
                        f.write(ascii_out)
                    print(f"✅ 已保存: {output_ascii}")
                except Exception as e:
                    print(f"⚠️  both 模式寫入 ASCII 失敗: {e}", file=sys.stderr)
        else:
            print("❌ CSS 渲染失敗")
            sys.exit(1)

    else:  # PIL
        if transparent_bg:
            custom_params = {**custom_params, 'bg_color': '#00000000'}
        elif bg_color:
            custom_params = {**custom_params, 'bg_color': bg_color}
        img = render_pil(data, theme, custom_params)
        w, h = img.size
        if force_width:
            if fill_width_method == "background":
                # 背景填滿：canvas = force_width，表格置中
                try:
                    bg_color_pil = (0, 0, 0, 0) if transparent_bg else parse_color(bg_color or "#1a1a2e")
                except Exception:
                    bg_color_pil = (26, 26, 46)
                use_rgba = transparent_bg or (isinstance(bg_color_pil, tuple) and len(bg_color_pil) == 4)
                canvas = Image.new("RGBA" if use_rgba else "RGB", (force_width, h), bg_color_pil)
                x = (force_width - w) // 2
                if img.mode != canvas.mode:
                    img = img.convert(canvas.mode)
                canvas.paste(img, (x, 0))
                img = canvas
            elif fill_width_method == "no-shrink" and w >= force_width:
                pass  # 不縮小
            else:
                new_w = force_width
                new_h = max(1, int(h * force_width / w))
                try:
                    resample = Image.Resampling.LANCZOS
                except AttributeError:
                    resample = Image.LANCZOS
                img = img.resize((new_w, new_h), resample)
        elif scale_factor != 1.0:
            new_w = max(1, int(w * scale_factor))
            new_h = max(1, int(h * scale_factor))
            try:
                resample = Image.Resampling.LANCZOS
            except AttributeError:
                resample = Image.LANCZOS
            img = img.resize((new_w, new_h), resample)
        img.save(output_file, quality=95)

        if os.path.exists(output_file) and auto_height:
            # PIL：可能是純色背景（非透明），所以 transparent 取決於 transparent_bg
            crop_to_content_height(output_file, transparent=transparent_bg)

        if os.path.exists(output_file):
            print(f"✅ 已保存: {output_file}")
            if output_ascii:
                try:
                    theme_text = get_theme(theme_name, 'text')
                    theme_params = (theme_text or {}).get("params") or {}
                    merged_ascii = {**(theme_params or {}), **(custom_params or {})}
                    ascii_style_both = ASCIIStyle(
                        border_style=merged_ascii.get("style", "double"),
                        padding=int(merged_ascii.get("padding", 2)),
                        align=merged_ascii.get("align", "left"),
                        header_align=merged_ascii.get("header_align", "center"),
                    )
                    ascii_out = render_ascii(data, theme_text, style=ascii_style_both, calibration=None, debug_details=None)
                    with open(output_ascii, 'w', encoding='utf-8') as f:
                        f.write(ascii_out)
                    print(f"✅ 已保存: {output_ascii}")
                except Exception as e:
                    print(f"⚠️  both 模式寫入 ASCII 失敗: {e}", file=sys.stderr)
        else:
            print("❌ PIL 渲染失敗")
            sys.exit(1)
