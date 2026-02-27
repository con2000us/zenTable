#!/usr/bin/env python3
"""PIL blueprint visualizer for ASCII debug layout."""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from . import font as pil_font
from . import draw as pil_draw

def render_ascii_blueprint_pil(blueprint: dict, out_png_path: str, unit_px: int = 10):
    """將 ASCII 版面格式化（blueprint）用 PIL 可視化。

    輸入 blueprint 應為 render_ascii(..., calibration=None, debug_details=...) 的輸出。
    座標系以「字元格」為單位（半形=1、全形=2 的預設模型），每單位用 unit_px 轉換成像素。
    """
    warning = None
    try:
        unit_px = int(unit_px)
    except Exception:
        unit_px = 10
    unit_px = max(5, min(30, unit_px))

    if not isinstance(blueprint, dict) or not blueprint.get("col_h_counts"):
        return None, "blueprint 無效或缺少欄位資訊"

    col_h = blueprint.get("col_h_counts") or []
    ncols = int(blueprint.get("ncols") or len(col_h) or 0)
    col_h = col_h[:ncols]
    row_heights = blueprint.get("row_heights") or []
    header_height = int(blueprint.get("header_height") or 0)
    has_headers = bool(blueprint.get("has_headers"))
    has_title = bool(blueprint.get("has_title"))
    has_footer = bool(blueprint.get("has_footer"))
    # 實際表格內容（用於在藍圖上渲染文字以便核對）
    title_text = str(blueprint.get("title") or "")
    footer_text = str(blueprint.get("footer") or "")
    headers_list = blueprint.get("headers") or []
    rows_list = blueprint.get("rows") or []
    header_lines_list = blueprint.get("header_lines") or []
    row_lines_list = blueprint.get("row_lines") or []

    def _build_fonts(px: int):
        """依 unit_px 建立字體與估計字高。"""
        try:
            base = max(12, min(28, int(px * 0.8) + 8))
            f = ImageFont.truetype(pil_font.FONT_CJK, base)
            f_sm = ImageFont.truetype(FONT_CJK, max(11, base - 4))
        except Exception:
            f = ImageFont.load_default()
            f_sm = ImageFont.load_default()
            base = 14
        try:
            d = ImageDraw.Draw(Image.new("RGB", (10, 10), (255, 255, 255)))
            bb = d.textbbox((0, 0), "Ag字", font=f_sm)
            th = max(0, bb[3] - bb[1])
        except Exception:
            try:
                th = f_sm.getbbox("Ag字")[3]
            except Exception:
                th = 12
        return f, f_sm, th, base

    # 以字高推最小 unit_px（避免文字擠在一起）。若提升 unit_px，需重建字體。
    font, font_sm, text_h, base_font_size = _build_fonts(unit_px)
    min_unit_px = max(10, int(text_h + 8))
    if unit_px < min_unit_px:
        warning = f"unit_px 太小，為避免標註重疊，已自動提升 {unit_px}→{min_unit_px}"
        unit_px = min_unit_px
        font, font_sm, text_h, base_font_size = _build_fonts(unit_px)

    # 字元格座標（含 border/intersection 字元）
    width_chars = 2 + sum(int(x) for x in col_h) + max(0, ncols - 1)

    y = 0
    title_row = None
    footer_row = None
    if has_title:
        title_row = y
        y += 1
    top_border = y
    y += 1
    header_start = None
    header_sep = None
    if has_headers:
        header_start = y
        y += max(1, header_height)
        header_sep = y
        y += 1
    data_start = y
    data_row_starts = []
    for h in row_heights:
        data_row_starts.append(y)
        y += max(1, int(h))
    bottom_border = y
    y += 1
    if has_footer:
        footer_row = y
        y += 1
    height_chars = y

    # 右側 legend 區，避免覆蓋表格。行高加高一倍再 +5px，支援單 cell 多行文字。
    margin = 64
    legend_gap = 24
    legend_w = 360
    unit_px_vertical = unit_px * 2 + 5
    table_w_px = width_chars * unit_px
    table_h_px = height_chars * unit_px_vertical

    # 換行工具：讓底部面板與 legend 文字不會超出框線
    def _text_width(d, fnt, txt: str) -> int:
        txt = "" if txt is None else str(txt)
        try:
            return int(d.textlength(txt, font=fnt))
        except Exception:
            try:
                return int(fnt.getlength(txt))
            except Exception:
                try:
                    bb = d.textbbox((0, 0), txt, font=fnt)
                    return int(bb[2] - bb[0])
                except Exception:
                    return len(txt) * 8

    def _wrap_text(d, fnt, txt: str, max_w: int, subsequent_prefix: str = ""):
        txt = "" if txt is None else str(txt)
        if max_w <= 0:
            return [txt]
        if _text_width(d, fnt, txt) <= max_w:
            return [txt]
        # 先用空白斷詞；無空白則逐字切
        if " " in txt:
            words = txt.split(" ")
            out = []
            cur = ""
            for w0 in words:
                cand = (cur + (" " if cur else "") + w0).strip()
                if cur and _text_width(d, fnt, cand) > max_w:
                    out.append(cur)
                    cur = subsequent_prefix + w0
                else:
                    cur = cand
            if cur:
                out.append(cur)
            return out if out else [txt]
        # 逐字切（CJK 友善）
        out = []
        cur = ""
        for ch in txt:
            cand = cur + ch
            if cur and _text_width(d, fnt, cand) > max_w:
                out.append(cur)
                cur = subsequent_prefix + ch
            else:
                cur = cand
        if cur:
            out.append(cur)
        return out if out else [txt]

    # 下方文字面板（區塊標註、摘要）— 不覆蓋 table
    summary = []
    if title_row is not None:
        summary.append(f"title row: y={title_row}")
    summary.append(f"top border: y={top_border}")
    if has_headers and header_start is not None and header_sep is not None:
        summary.append(f"header: y={header_start}..{header_sep-1}")
        summary.append(f"header sep: y={header_sep}")
    summary.append(f"data: y={data_start}..{bottom_border-1}")
    summary.append(f"bottom border: y={bottom_border}")
    if footer_row is not None:
        summary.append(f"footer row: y={footer_row}")

    # 先用 dummy draw 進行換行與高度估算（避免字體超出框線）
    _dummy = ImageDraw.Draw(Image.new("RGB", (10, 10), (255, 255, 255)))
    bottom_panel_w = (margin * 2 + table_w_px + legend_gap + legend_w) - margin * 2  # 實際會畫在 table_x0..legend_x1
    bottom_inner_w = max(120, int(bottom_panel_w - 24))
    panel_font = font  # 底部面板字體放大
    panel_line_h = max(18, int(text_h + 10))

    bottom_lines = []
    bottom_lines.extend(_wrap_text(_dummy, panel_font, "Regions (y) — blueprint (no calibration):", bottom_inner_w))
    for line in summary:
        wrapped = _wrap_text(_dummy, panel_font, "- " + line, bottom_inner_w, subsequent_prefix="  ")
        bottom_lines.extend(wrapped)

    bottom_panel_h = max(140, 20 + len(bottom_lines) * panel_line_h + 20)
    # 表格下方預留空間給欄位交界座標字（0, 17, 28...），避免 Regions 框蓋住
    gap_below_table = 40
    w = margin * 2 + table_w_px + legend_gap + legend_w
    h = margin * 2 + table_h_px + gap_below_table + bottom_panel_h
    img = Image.new("RGB", (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    ox, oy = margin, margin
    table_x0, table_y0 = ox, oy
    table_x1, table_y1 = ox + table_w_px, oy + table_h_px
    legend_x0 = table_x1 + legend_gap
    legend_x1 = legend_x0 + legend_w
    bottom_y0 = table_y1 + gap_below_table
    bottom_y1 = bottom_y0 + bottom_panel_h

    # 主要區域外框（四邊同樣粗）
    draw.rectangle([table_x0, table_y0, table_x1, table_y1], outline=(0, 0, 0), width=3)

    # x border positions（字元索引）
    x_borders = [0]
    pos = 0
    for i in range(ncols):
        pos += 1 + int(col_h[i])
        x_borders.append(pos)

    # 畫垂直邊界線（含最左/最右與欄分隔），並標出每個 column 交界的 x 座標
    for i, xb in enumerate(x_borders):
        x = ox + xb * unit_px
        draw.line([x, table_y0, x, table_y1], fill=(0, 0, 0), width=2)
        txt = str(xb)
        try:
            bbox = draw.textbbox((0, 0), txt, font=font_sm)
            w = bbox[2] - bbox[0]
        except Exception:
            w = len(txt) * 6
        draw.text((x - w // 2, table_y1 + 4), txt, fill=(0, 70, 100), font=font_sm)

    # 畫水平關鍵線
    def hline(y_idx, color=(0, 0, 0), width=2):
        yy = oy + y_idx * unit_px_vertical
        draw.line([table_x0, yy, table_x1, yy], fill=color, width=width)

    def _shade_band(y0_idx, y1_idx, fill_rgb):
        """用淡色標出區塊範圍。"""
        y0p = oy + y0_idx * unit_px_vertical
        y1p = oy + y1_idx * unit_px_vertical
        draw.rectangle([table_x0, y0p, table_x1, y1p], fill=fill_rgb)

    # 標題/底註行（只畫線框提示）
    if title_row is not None:
        _shade_band(title_row, title_row + 1, (235, 245, 255))
        hline(title_row, (60, 60, 60), 2)
        hline(title_row + 1, (60, 60, 60), 2)
    if footer_row is not None:
        _shade_band(footer_row, footer_row + 1, (235, 245, 255))
        hline(footer_row, (60, 60, 60), 2)
        hline(footer_row + 1, (60, 60, 60), 2)

    hline(top_border, (0, 0, 0), 3)
    if has_headers and header_sep is not None:
        hline(header_sep, (0, 0, 0), 3)
    hline(bottom_border, (0, 0, 0), 3)

    if has_headers and header_start is not None and header_sep is not None:
        _shade_band(header_start, header_sep, (240, 255, 240))

    # 畫資料列邊界（淡色，作為 cell 高度參考）
    for ys in data_row_starts:
        hline(ys, (190, 190, 190), 1)
    hline(data_start, (120, 120, 120), 2)

    # 座標刻度：表格大時降低密度
    tick_step = 10 if max(width_chars, height_chars) >= 80 else 5
    for xi in range(0, width_chars + 1, tick_step):
        x = ox + xi * unit_px
        draw.line([x, oy - 6, x, oy], fill=(0, 0, 0), width=1)
        draw.text((x + 2, oy - 22), str(xi), fill=(0, 0, 0), font=font_sm)
    for yi in range(0, height_chars + 1, tick_step):
        yyy = oy + yi * unit_px_vertical
        draw.line([ox - 6, yyy, ox, yyy], fill=(0, 0, 0), width=1)
        draw.text((ox - 36, yyy + 2), str(yi), fill=(0, 0, 0), font=font_sm)

    # 表格右端：每一行的 y 座標（支援單 cell 多行時對照行高）
    for yi in range(0, height_chars + 1):
        yyy = oy + yi * unit_px_vertical
        txt = str(yi)
        try:
            bbox = draw.textbbox((0, 0), txt, font=font_sm)
            h = bbox[3] - bbox[1]
        except Exception:
            h = 14
        draw.text((table_x1 + 4, yyy - h // 2), txt, fill=(0, 70, 100), font=font_sm)

    def _pick_label_mode(cell_w_px: int, cell_h_px: int):
        # full: 兩行座標；compact: 單行 r,c；none: 不標（高度以 unit_px_vertical 為準）
        if cell_w_px >= 14 * unit_px and cell_h_px >= 3 * unit_px_vertical:
            return "full"
        if cell_w_px >= 6 * unit_px and cell_h_px >= 2 * unit_px_vertical:
            return "compact"
        return "none"

    def _truncate_to_width(d, fnt, txt: str, max_w: int, suffix: str = "…") -> str:
        if max_w <= 0:
            return ""
        txt = "" if txt is None else str(txt)
        if _text_width(d, fnt, txt) <= max_w:
            return txt
        while txt and _text_width(d, fnt, txt + suffix) > max_w:
            txt = txt[:-1]
        return txt + suffix if txt else suffix

    def _truncate_to_width_mixed(txt: str, max_w: int, fs: int, suffix: str = "…") -> str:
        """依混合字體寬度截斷（與 PIL 後端一致，供 emoji 正確顯示時使用）。"""
        if max_w <= 0:
            return ""
        txt = "" if txt is None else str(txt)
        if pil_draw.measure_text_width(txt, fs) <= max_w:
            return txt
        while txt and pil_draw.measure_text_width(txt + suffix, fs) > max_w:
            txt = txt[:-1]
        return txt + suffix if txt else suffix

    def _cell_font(size: int):
        return pil_font.get_font_cjk(size)

    def _draw_cell_content(px0: int, py0: int, px1: int, py1: int, lines: list, color=(0, 0, 0)):
        """在 cell 矩形內繪製多行文字，與 PIL 後端一致：emoji 用 get_font_emoji，CJK 用 get_font_cjk（混合字體）。"""
        if not lines:
            return
        pad = 2
        bottom_margin = 6
        cell_w = max(0, px1 - px0 - 2 * pad)
        cell_h = max(0, py1 - py0 - 2 * pad)
        n_lines = max(1, len(lines))
        inner_h = max(1, cell_h - bottom_margin)
        per_line_max = max(1, inner_h // n_lines)
        max_font = max(14, int(unit_px_vertical * 0.85))
        font_size = min(max_font, per_line_max - 2)
        font_size = max(6, font_size)
        fnt = _cell_font(font_size)
        while font_size >= 6:
            try:
                lh = draw.textbbox((0, 0), "Ag字", font=fnt)[3] - draw.textbbox((0, 0), "Ag字", font=fnt)[1]
            except Exception:
                lh = font_size + 4
            lh_safe = lh + 2
            if n_lines * lh_safe <= inner_h:
                break
            font_size -= 1
            fnt = _cell_font(font_size)
        try:
            lh = draw.textbbox((0, 0), "Ag字", font=fnt)[3] - draw.textbbox((0, 0), "Ag字", font=fnt)[1]
        except Exception:
            lh = font_size + 4
        for i, line in enumerate(lines[:n_lines]):
            if (i + 1) * lh > inner_h:
                break
            truncated = _truncate_to_width_mixed(str(line), cell_w, font_size)
            pil_draw.draw_text_with_mixed_fonts(
                draw, truncated,
                px0 + pad, py0 + pad + i * lh,
                font_size, color, img_mode="RGB"
            )

    # 標註每個 data cell 的區域（以字元座標表示）。格子太小就降級標註，避免擠在一起。
    data_y = data_start
    for r_idx, rh in enumerate(row_heights):
        rh = max(1, int(rh))
        for c_idx in range(ncols):
            # 外框（含框線佔位）— 淡灰，讓線看起來「連實」
            bx0 = x_borders[c_idx]
            bx1 = x_borders[c_idx + 1]
            x0 = x_borders[c_idx] + 1
            x1 = x_borders[c_idx + 1] - 1
            y0 = data_y
            y1 = data_y + rh - 1
            # 轉成像素（橫向 unit_px，縱向 unit_px_vertical）
            bpx0 = ox + bx0 * unit_px
            bpy0 = oy + y0 * unit_px_vertical
            bpx1 = ox + (bx1 + 1) * unit_px
            bpy1 = oy + (y1 + 1) * unit_px_vertical
            draw.rectangle([bpx0, bpy0, bpx1, bpy1], outline=(210, 210, 210), width=1)

            px0 = ox + x0 * unit_px
            py0 = oy + y0 * unit_px_vertical
            px1 = ox + (x1 + 1) * unit_px
            py1 = oy + (y1 + 1) * unit_px_vertical
            draw.rectangle([px0, py0, px1, py1], outline=(230, 120, 40), width=1)
            mode = _pick_label_mode(px1 - px0, py1 - py0)
            if mode == "full":
                label = f"r{r_idx},c{c_idx}\\n({x0},{y0})-({x1},{y1})"
                draw.text((px0 + 2, py0 + 2), label, fill=(120, 60, 0), font=font_sm)
            elif mode == "compact":
                draw.text((px0 + 2, py0 + 2), f"r{r_idx},c{c_idx}", fill=(120, 60, 0), font=font_sm)
            # 渲染該格文字內容（方便核對）
            cell_lines = []
            if r_idx < len(row_lines_list) and c_idx < len(row_lines_list[r_idx]):
                cell_lines = [str(ln) for ln in row_lines_list[r_idx][c_idx]]
            if not cell_lines and r_idx < len(rows_list) and c_idx < len(rows_list[r_idx]):
                cell_lines = [str(rows_list[r_idx][c_idx])]
            if cell_lines:
                _draw_cell_content(px0, py0, px1, py1, cell_lines, color=(80, 50, 20))
        data_y += rh

    # header cell
    if has_headers and header_start is not None:
        hy0 = header_start
        hy1 = header_start + max(1, header_height) - 1
        for c_idx in range(ncols):
            # 外框（含框線佔位）
            bx0 = x_borders[c_idx]
            bx1 = x_borders[c_idx + 1]
            x0 = x_borders[c_idx] + 1
            x1 = x_borders[c_idx + 1] - 1
            bpx0 = ox + bx0 * unit_px
            bpy0 = oy + hy0 * unit_px_vertical
            bpx1 = ox + (bx1 + 1) * unit_px
            bpy1 = oy + (hy1 + 1) * unit_px_vertical
            draw.rectangle([bpx0, bpy0, bpx1, bpy1], outline=(180, 180, 180), width=1)

            px0 = ox + x0 * unit_px
            py0 = oy + hy0 * unit_px_vertical
            px1 = ox + (x1 + 1) * unit_px
            py1 = oy + (hy1 + 1) * unit_px_vertical
            draw.rectangle([px0, py0, px1, py1], outline=(40, 120, 200), width=1)
            mode = _pick_label_mode(px1 - px0, py1 - py0)
            if mode != "none":
                draw.text((px0 + 2, py0 + 2), f"H{c_idx}", fill=(0, 70, 140), font=font_sm)
            # 渲染表頭文字內容
            hdr_lines = []
            if c_idx < len(header_lines_list):
                hdr_lines = [str(ln) for ln in header_lines_list[c_idx]]
            if not hdr_lines and c_idx < len(headers_list):
                hdr_lines = [str(headers_list[c_idx])]
            if hdr_lines:
                _draw_cell_content(px0, py0, px1, py1, hdr_lines, color=(0, 70, 140))

    # 標題列文字
    if has_title and title_row is not None and title_text:
        tx0 = table_x0
        ty0 = oy + title_row * unit_px_vertical
        tx1 = table_x1
        ty1 = oy + (title_row + 1) * unit_px_vertical
        _draw_cell_content(tx0, ty0, tx1, ty1, [title_text], color=(0, 90, 160))

    # 底註列文字
    if has_footer and footer_row is not None and footer_text:
        fx0 = table_x0
        fy0 = oy + footer_row * unit_px_vertical
        fx1 = table_x1
        fy1 = oy + (footer_row + 1) * unit_px_vertical
        _draw_cell_content(fx0, fy0, fx1, fy1, [footer_text], color=(0, 90, 160))

    # legend（固定在右側，不覆蓋表格）
    info = [
        "ASCII blueprint PIL preview",
        f"unit_px={unit_px}",
        f"width_chars={width_chars}, height_chars={height_chars}",
        f"ncols={ncols}, nrows={len(row_heights)}",
        "note: gray=cell incl. border cols; colored=content area",
    ]
    # legend 先計算換行結果，再自動決定框高度，避免文字跑出框線
    legend_inner_w = max(80, int(legend_w - 20))
    legend_box_x0 = legend_x0
    legend_box_x1 = legend_x1
    legend_box_y0 = table_y0  # 固定在右側上方

    # 嘗試用較大的字，但如果高度塞不下就縮小
    legend_font_size = max(10, min(18, base_font_size - 6))
    legend_font = font_sm
    try:
        legend_font = ImageFont.truetype(pil_font.FONT_CJK, legend_font_size)
    except Exception:
        legend_font = font_sm

    def _build_legend_lines(fnt):
        lines = []
        for line in info:
            lines.extend(_wrap_text(draw, fnt, line, legend_inner_w))
        return lines

    def _line_height(fnt):
        try:
            bb = draw.textbbox((0, 0), "Ag字", font=fnt)
            th = max(0, bb[3] - bb[1])
        except Exception:
            th = text_h
        return max(16, int(th + 8))

    legend_lines = _build_legend_lines(legend_font)
    lh = _line_height(legend_font)
    legend_box_h = 12 + len(legend_lines) * lh + 12
    max_h = table_h_px

    # 若太高，逐步縮小字體
    while legend_box_h > max_h and legend_font_size > 9:
        legend_font_size -= 1
        try:
            legend_font = ImageFont.truetype(pil_font.FONT_CJK, legend_font_size)
        except Exception:
            break
        legend_lines = _build_legend_lines(legend_font)
        lh = _line_height(legend_font)
        legend_box_h = 12 + len(legend_lines) * lh + 12

    # 若仍太高，截斷並加省略號
    if legend_box_h > max_h:
        max_lines = max(1, int((max_h - 24) / lh))
        if len(legend_lines) > max_lines:
            legend_lines = legend_lines[:max_lines - 1] + ["..."]
        legend_box_h = max_h

    legend_box_y1 = legend_box_y0 + legend_box_h
    if legend_box_y1 > table_y1:
        legend_box_y1 = table_y1

    draw.rectangle([legend_box_x0, legend_box_y0, legend_box_x1, legend_box_y1], fill=(255, 255, 255), outline=(0, 0, 0), width=1)
    ly = legend_box_y0 + 12
    for wl in legend_lines:
        draw.text((legend_x0 + 10, ly), wl, fill=(0, 0, 0), font=legend_font)
        ly += lh

    # 下方文字面板：Regions/說明（不覆蓋 table）
    draw.rectangle([table_x0, bottom_y0, legend_x1, bottom_y1], fill=(250, 250, 250), outline=(0, 0, 0), width=1)
    bx = table_x0 + 12
    by = bottom_y0 + 10
    for wl in bottom_lines:
        draw.text((bx, by), wl, fill=(0, 0, 0), font=panel_font)
        by += panel_line_h

    try:
        img.save(out_png_path, "PNG")
    except Exception as e:
        return None, f"PIL 儲存失敗: {e}"
    return out_png_path, warning
