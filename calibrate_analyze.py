#!/usr/bin/env python3
"""
ASCII 校準截圖分析腳本

從截圖中定位校準區塊，計算各字元類別寬度，輸出 calibration JSON。
用法: python3 calibrate_analyze.py <image_path> [--custom-chars 字詞]
"""

import json
import sys
import os
import re
from typing import Optional, Dict, Any, List, Tuple

# 校準區塊標記
CAL_START = "[ZENT-BLE-MKR]"
CAL_START_LEGACY = "[ZENTABLE-CAL-v1]"  # 向後相容
CAL_END = "[END]"

# █ pattern 錨點參數
BLOCK_CHAR = "\u2588"  # 全方塊 U+2588

# Pattern 參數
BLOCK_PATTERN_DEFAULT = [1, 2, 1, 2, 1, 2, 1, 2]  # █ ██ 重複 4 次
MIN_UNIT_WIDTH = 5  # 最小 1 單位寬度（像素）
UNIT_TOLERANCE = 0.20  # 20% 寬度容差
COLOR_TOL_R = 12  # R 通道顏色容差
COLOR_TOL_G = 8   # G 通道顏色容差
COLOR_TOL_B = 20  # B 通道顏色容差
MIN_VERTICAL_CONTINUOUS = 8  # 垂直方向最少連續像素

CONTENT_MARGIN_RATIO = 0.04  # 排除外緣，避免外框背景影響閾值

# #region agent log
DEBUG_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cursor", "debug-5ac0d2.log")
def _debug_log(location: str, message: str, data: dict, hypothesis_id: str = "", run_id: str = ""):
    try:
        import time
        payload = {"sessionId": "5ac0d2", "location": location, "message": message, "data": data, "timestamp": int(time.time() * 1000)}
        if hypothesis_id: payload["hypothesisId"] = hypothesis_id
        if run_id: payload["runId"] = run_id
        os.makedirs(os.path.dirname(DEBUG_LOG_PATH), exist_ok=True)
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass
# #endregion


def iter_display_tokens(text: str) -> List[str]:
    """
    近似字素切分：
    - RI 旗幟成對（U+1F1E6..U+1F1FF）
    - 吸收 VS15/VS16、ZWJ、emoji modifier、combining
    用於校準字元序列，避免 flag/emoji 被拆成單碼造成對位誤判。
    """
    import unicodedata
    s = str(text or "")
    out = []
    i = 0
    n = len(s)
    while i < n:
        start = i
        cp = ord(s[i])
        i += 1
        if 0x1F1E6 <= cp <= 0x1F1FF and i < n and 0x1F1E6 <= ord(s[i]) <= 0x1F1FF:
            i += 1
        while i < n:
            cp2 = ord(s[i])
            if cp2 in (0xFE0E, 0xFE0F, 0x200D) or (0x1F3FB <= cp2 <= 0x1F3FF):
                i += 1
                continue
            if unicodedata.combining(s[i]) != 0:
                i += 1
                continue
            break
        out.append(s[start:i])
    return out


def parse_uplus_quoted_groups(text: str) -> List[str]:
    """
    解析 `"U+XXXX"` / `"U+AAAA U+BBBB"` 形式的字元群組。
    每個雙引號群組視為唯一字元單位，保留碼序。
    """
    raw = str(text or "").strip()
    if not raw:
        return []
    groups = re.findall(r'"([^"]+)"', raw)
    out = []
    for g in groups:
        parts = [p for p in g.strip().split() if p]
        if not parts:
            continue
        cps: List[int] = []
        ok = True
        for p in parts:
            m = re.match(r"^U\+([0-9A-Fa-f]{4,6})$", p)
            if not m:
                ok = False
                break
            cp = int(m.group(1), 16)
            if cp < 0 or cp > 0x10FFFF:
                ok = False
                break
            cps.append(cp)
        if not ok or not cps:
            continue
        out.append("".join(chr(cp) for cp in cps))
    return out


def _get_content_pixels(img):
    """只取中央內容區域像素，避免右側外框/UI 邊界被誤當文字"""
    w, h = img.size
    m = max(2, int(min(w, h) * CONTENT_MARGIN_RATIO))
    if w <= 2 * m or h <= 2 * m:
        try:
            return list(img.get_flattened_data())
        except AttributeError:
            return list(img.get_flattened_data())
    cropped = img.crop((m, m, w - m, h - m))
    try:
        return list(cropped.get_flattened_data())
    except AttributeError:
        return list(cropped.get_flattened_data())


def preprocess_for_ocr(img):
    """
    預處理截圖供 Tesseract OCR 使用。
    終端背景/字體顏色未知，採用與配色無關的二值化：
    1. 轉灰階
    2. 以中位數為門檻二值化（閾值只用內容區域，排除外框影響）
    3. 確保文字為黑、背景為白（Tesseract 預期）
    """
    from PIL import Image, ImageOps, ImageStat
    if img.mode != "L":
        img = img.convert("L")  # 灰階，避免單一色 channel 偏誤
    pixels = _get_content_pixels(img)
    if not pixels:
        return img
    # 用中位數當門檻，較不受配色影響
    threshold = sorted(pixels)[len(pixels) // 2]
    # 二值化：低於門檻→0（黑），高於→255（白）
    img = img.point(lambda x: 0 if x <= threshold else 255, mode="1").convert("L")
    # 文字通常佔少數像素，若黑色比例 > 50% 表示可能是反的，再反轉
    stat = ImageStat.Stat(img)
    mean_bright = stat.mean[0]
    if mean_bright < 128:
        img = ImageOps.invert(img)
    return img


def load_image(path: str):
    """載入圖片"""
    try:
        from PIL import Image
        img = Image.open(path)
        if img.mode != "RGB":
            img = img.convert("RGB")
        return img
    except Exception as e:
        print(json.dumps({"success": False, "error": f"無法載入圖片: {e}"}))
        sys.exit(1)


def run_ocr_full(image_path: str) -> List[Dict]:
    """對全圖執行 OCR，取得 image_to_data 格式"""
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(image_path)
        img = preprocess_for_ocr(img)
        data = pytesseract.image_to_data(img, lang="chi_tra+eng", output_type=pytesseract.Output.DICT, config="--psm 6")
        n = len(data.get("text", []))
        rows = []
        for i in range(n):
            rows.append({
                "text": data.get("text", [""] * n)[i] or "",
                "left": data.get("left", [0] * n)[i],
                "top": data.get("top", [0] * n)[i],
                "width": data.get("width", [0] * n)[i],
                "height": data.get("height", [0] * n)[i],
            })
        return rows
    except ImportError:
        return []
    except Exception as e:
        return []


def preprocess_for_pixel(img):
    """二值化供像素定位使用。返回 (二值化圖, 是否需要反轉)"""
    from PIL import Image, ImageOps, ImageStat
    if img.mode != "L":
        img = img.convert("L")
    pixels = _get_content_pixels(img)
    if not pixels:
        return img, False
    # 用中位數當門檻
    threshold = sorted(pixels)[len(pixels) // 2]
    bin_img = img.point(lambda x: 0 if x <= threshold else 255, mode="1").convert("L")
    # 檢查是否需要反轉（文字通常佔少數像素）
    stat = ImageStat.Stat(bin_img)
    need_invert = stat.mean[0] < 128
    if need_invert:
        bin_img = ImageOps.invert(bin_img)
    return bin_img, need_invert


def get_pixel_runs_color(img_rgb, is_dark_foreground: bool = True) -> Tuple[List[List[Tuple[int, int, Tuple[int, int, int]]]], int, int]:
    """
    對 RGB 圖像做水平投影，回傳每行的 runs（含顏色）。
    回傳: (runs_by_row, width, height)
    每個 run: (x1, x2, (r,g,b)) - x 範圍與平均顏色
    
    使用顏色連續性偵測：
    - 顏色容忍值：R < 12, G < 10, B < 20 視為同色
    - 從一點開始，檢查下一像素顏色是否連續
    - 直到發現不連續為止，記錄連續長度
    """
    w, h = img_rgb.size
    runs_by_row = []
    
    # 顏色容忍值
    TOL_R = 12
    TOL_G = 10
    TOL_B = 20
    
    for y in range(h):
        row_data = list(img_rgb.crop((0, y, w, y + 1)).convert("RGB").get_flattened_data())
        
        runs = []
        x = 0
        while x < w:
            # 開始新的 run
            run_start = x
            run_color = row_data[x]  # (r, g, b)
            
            # 繼續找連續的同色像素
            x += 1
            while x < w:
                next_color = row_data[x]
                # 檢查顏色是否連續（容忍範圍內）
                if (abs(next_color[0] - run_color[0]) <= TOL_R and
                    abs(next_color[1] - run_color[1]) <= TOL_G and
                    abs(next_color[2] - run_color[2]) <= TOL_B):
                    x += 1  # 顏色連續，繼續
                else:
                    break  # 發現不連續的顏色
            
            # 記錄這個 run
            run_end = x
            if run_end > run_start:
                runs.append((run_start, run_end, run_color))
        
        runs_by_row.append(runs)
    
    return runs_by_row, w, h


def otsu_threshold_from_luma(luma_values: List[int]) -> int:
    """以 Otsu 方法計算 0-255 灰階閾值。"""
    if not luma_values:
        return 127

    hist = [0] * 256
    for v in luma_values:
        iv = 0 if v < 0 else 255 if v > 255 else int(v)
        hist[iv] += 1

    total = len(luma_values)
    sum_all = 0
    for i, c in enumerate(hist):
        sum_all += i * c

    sum_b = 0.0
    w_b = 0.0
    max_var = -1.0
    threshold = 127

    for t in range(256):
        w_b += hist[t]
        if w_b <= 0:
            continue
        w_f = total - w_b
        if w_f <= 0:
            break

        sum_b += t * hist[t]
        m_b = sum_b / w_b
        m_f = (sum_all - sum_b) / w_f
        between = w_b * w_f * (m_b - m_f) * (m_b - m_f)
        if between > max_var:
            max_var = between
            threshold = t

    return int(threshold)


def get_pixel_runs_otsu_luma(img_rgb) -> Tuple[List[List[Tuple[int, int, Tuple[int, int, int]]]], int, int, int, bool, float]:
    """
    以 luma + Otsu 二值化後取得每行「前景 runs」。
    回傳: (runs_by_row, w, h, threshold, fg_is_bright, fg_ratio)

    前景定義：全圖較少數的亮/暗像素類別（通常是文字/方塊）。
    """
    w, h = img_rgb.size

    px = img_rgb.convert("RGB").load()
    all_luma: List[int] = []
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            all_luma.append(int(round(0.299 * r + 0.587 * g + 0.114 * b)))

    thr = otsu_threshold_from_luma(all_luma)
    bright_count = sum(1 for v in all_luma if v >= thr)
    dark_count = len(all_luma) - bright_count

    # 文字通常佔少數像素：以少數類別當前景
    fg_is_bright = bright_count <= dark_count
    fg_count = bright_count if fg_is_bright else dark_count
    fg_ratio = (fg_count / len(all_luma)) if all_luma else 0.0

    runs_by_row: List[List[Tuple[int, int, Tuple[int, int, int]]]] = []
    for y in range(h):
        runs: List[Tuple[int, int, Tuple[int, int, int]]] = []
        x = 0
        while x < w:
            r, g, b = px[x, y]
            lv = int(round(0.299 * r + 0.587 * g + 0.114 * b))
            is_fg = (lv >= thr) if fg_is_bright else (lv < thr)
            if not is_fg:
                x += 1
                continue
            x1 = x
            luma_sum = 0
            n = 0
            while x < w:
                r2, g2, b2 = px[x, y]
                lv2 = int(round(0.299 * r2 + 0.587 * g2 + 0.114 * b2))
                is_fg2 = (lv2 >= thr) if fg_is_bright else (lv2 < thr)
                if not is_fg2:
                    break
                luma_sum += lv2
                n += 1
                x += 1
            x2 = x
            if x2 > x1:
                avg = int(round(luma_sum / n)) if n > 0 else 0
                runs.append((x1, x2, (avg, avg, avg)))
        runs_by_row.append(runs)

    return runs_by_row, w, h, thr, fg_is_bright, fg_ratio


def colors_similar(c1: Tuple[int, int, int], c2: Tuple[int, int, int]) -> bool:
    """檢查兩顏色是否相似（R < 12, G < 10, B < 20）"""
    return (abs(c1[0] - c2[0]) <= 12 and
            abs(c1[1] - c2[1]) <= 10 and
            abs(c1[2] - c2[2]) <= 20)


def find_horizontal_runs(bin_img) -> List[List[Tuple[int, int]]]:
    """對二值化圖像做水平投影，回傳每行的黑色 runs [[(x1,x2), ...], ...]"""
    from PIL import Image
    w, h = bin_img.size
    runs_by_row = []
    for y in range(h):
        row_data = list(bin_img.crop((0, y, w, y + 1)).get_flattened_data())
        runs = []
        x = 0
        while x < w:
            while x < w and row_data[x] > 127:
                x += 1
            if x >= w:
                break
            x1 = x
            while x < w and row_data[x] <= 127:
                x += 1
            x2 = x
            if x2 > x1:
                runs.append((x1, x2))
        runs_by_row.append(runs)
    return runs_by_row


def quantize_runs(runs: List[Tuple], unit_width: float, min_unit: int = MIN_UNIT_WIDTH) -> List[int]:
    """將 run 寬度量化為 1 或 2 個單位（最小單位 >= min_unit）。runs 每項可為 (x1, x2) 或 (x1, x2, color)。"""
    quantized = []
    for run in runs:
        x1, x2 = run[0], run[1]
        w = x2 - x1
        if unit_width <= 0:
            quantized.append(0)
            continue
        # 使用 20% 容差
        ratio = w / unit_width
        # 1 unit: ratio in [0.8, 1.5), 2 units: ratio in [1.5, 2.5), etc.
        if ratio < 0.8:
            quantized.append(0)  # 噪音
        elif ratio < 1.5:
            quantized.append(1)
        elif ratio < 2.5:
            quantized.append(2)
        else:
            quantized.append(int(ratio + 0.5))  # 四捨五入
    return quantized


def estimate_unit_width(runs_by_row: List[List[Tuple]]) -> float:
    """從所有 runs 估計單格寬度，回傳最小有效單位寬度（至少 MIN_UNIT_WIDTH）。
    runs 每項可為 (x1, x2) 或 (x1, x2, color)。
    """
    all_widths = []
    for runs in runs_by_row:
        for run in runs:
            x1, x2 = run[0], run[1]
            w = x2 - x1
            if w >= MIN_UNIT_WIDTH:
                all_widths.append(w)
    if not all_widths:
        return float(MIN_UNIT_WIDTH)
    # 取前 25% 分位數當最小單位（避免把多格當一格）
    sorted_widths = sorted(all_widths)
    idx = len(sorted_widths) // 4
    unit = sorted_widths[idx] if idx < len(sorted_widths) else sorted_widths[0]
    return max(float(unit), float(MIN_UNIT_WIDTH))


def match_pattern_sliding(quantized: List[int], pattern: List[int]) -> int:
    """滑動視窗比對 pattern（量化值完全匹配），回傳匹配起始索引，否則回傳 -1"""
    if len(quantized) < len(pattern):
        return -1
    for start in range(len(quantized) - len(pattern) + 1):
        match = True
        for i, (a, b) in enumerate(zip(quantized[start:start + len(pattern)], pattern)):
            if a != b:
                match = False
                break
        if match:
            return start
    return -1


def match_pattern_by_width(k: List[int], pattern: List[int], debug_logs: List[str], row_idx: int, skip_indices: set = None) -> List[Dict]:
    """
    使用寬度比對 pattern
    - k: run 寬度陣列 [w1, w2, w3, ...]
    - pattern: pattern 值 [1, 2, 1, 2, 1, 2, 1, 2]
    - skip_indices: 要跳過的起始索引集合（避免重複匹配）
    - 回傳: [{'start_idx': 起始索引, 'unit_width': 單位寬度, 'matched': True/False}, ...]
    """
    if skip_indices is None:
        skip_indices = set()

    if len(k) < len(pattern):  # 至少要有 pattern 長度的 run
        return []

    TOLERANCE = 0.20  # 20% 容差
    matches: List[Dict] = []

    # 支援兩種輸入：
    # 1) 緊密前景 runs（Otsu 前景）: [run, run, run, ...]
    # 2) 舊格式（run+gap 交錯）: [run, gap, run, gap, ...]
    dense_mode = len(k) < len(pattern) * 2

    for i in range(len(k)):
        if i in skip_indices:
            continue

        w1 = k[i]
        if w1 < MIN_UNIT_WIDTH:
            continue

        unit = w1 / pattern[0]
        expected_widths = [unit * p for p in pattern]

        match = True
        cursor = i
        last_run_end_idx = i
        actual_widths: List[int] = []

        crack_px = max(1, min(2, int(round(unit * 0.18))))
        max_crack_merges = 3
        step_next = 1 if dense_mode else 2

        for pi in range(len(pattern)):
            if cursor >= len(k):
                match = False
                break

            expected = expected_widths[pi]
            actual = k[cursor]

            if expected * (1 - TOLERANCE) <= actual <= expected * (1 + TOLERANCE):
                actual_widths.append(actual)
                last_run_end_idx = cursor
                cursor += step_next
                continue

            # 小縫合併：run + (小gap + next_run) + ...
            merged = actual
            merge_cursor = cursor
            merged_ok = False
            merge_steps = 0
            while merge_cursor + step_next < len(k) and merge_steps < max_crack_merges:
                gap_width = 0 if dense_mode else k[merge_cursor + 1]
                next_width = k[merge_cursor + step_next]
                if gap_width > crack_px:
                    break
                merged += gap_width + next_width
                merge_cursor += step_next
                merge_steps += 1
                if expected * (1 - TOLERANCE) <= merged <= expected * (1 + TOLERANCE):
                    merged_ok = True
                    actual_widths.append(int(round(merged)))
                    last_run_end_idx = merge_cursor
                    cursor = merge_cursor + step_next
                    break
            if not merged_ok:
                match = False
                break

        if match:
            pattern_start_x = sum(k[:i])
            pattern_end_x = sum(k[:last_run_end_idx + 1])
            debug_logs.append(f"[PIXEL] Row {row_idx}: Found pattern at index {i}, unit_width={unit:.1f}, start_x={pattern_start_x}, end_x={pattern_end_x}")
            matches.append({
                "start_idx": i,
                "end_idx": last_run_end_idx,
                "unit_width": unit,
                "matched": True,
                "start_x": pattern_start_x,
                "end_x": pattern_end_x,
                "actual_widths": actual_widths,
            })

    return matches


def get_actual_pattern_widths(runs: List[Tuple[int, int]], pattern_len: int, start_idx: int) -> List[int]:
    """取得 pattern 實際像素寬度 [w1, w2, ...]"""
    widths = []
    for i in range(pattern_len):
        idx = start_idx + i
        if idx < len(runs):
            w = runs[idx][1] - runs[idx][0]
            widths.append(w)
    return widths


def check_vertical_consistency(img_rgb, runs_by_row: List[List[Tuple[int, int]]], match_row: int,
                               pattern_widths: List[int], unit_width: float, tol: float = UNIT_TOLERANCE) -> Tuple[bool, int, int]:
    """
    檢查垂直方向一致性。
    1. 取得 match_row 處的 pattern x 範圍
    2. 往上、往下檢查是否有相似的 pattern 分布
    3. 回傳: (是否成功, 上界, 下界)
    """
    w, h = img_rgb.size

    # 取得 match_row 的 pattern 位置
    if match_row >= len(runs_by_row):
        return False, 0, 0
    match_runs = runs_by_row[match_row]
    if not match_runs:
        return False, 0, 0

    # 假設 pattern 在行中間位置附近（跳過前面的標籤）
    # 找最接近中間的連續多個 runs
    mid_x = w // 2
    best_start = -1
    best_count = 0
    for i in range(len(match_runs) - len(pattern_widths) + 1):
        # 檢查這段 runs 是否在 mid_x 附近
        first_run = match_runs[i]
        last_run = match_runs[i + len(pattern_widths) - 1]
        run_mid = (first_run[0] + last_run[1]) // 2
        if abs(run_mid - mid_x) < abs(mid_x - (match_runs[best_start][0] + match_runs[best_start + best_count - 1][1]) // 2 if best_start >= 0 else 999999):
            best_start = i
            best_count = len(pattern_widths)

    if best_start < 0:
        return False, 0, 0

    # 取得 pattern 的 x 範圍
    pattern_left = match_runs[best_start][0]
    pattern_right = match_runs[best_start + len(pattern_widths) - 1][1]

    # 往上檢查
    top_bound = match_row
    for y in range(match_row - 1, max(0, match_row - 20), -1):
        runs = runs_by_row[y]
        # 找這個 y 在 pattern_left~pattern_right 範圍內的 runs (現在每個 run 有 3 個元素)
        contained = [(x1, x2) for x1, x2, c in runs if x1 < pattern_right and x2 > pattern_left]
        if not contained:
            break
        # 檢查這些 runs 的總寬度是否與 pattern 總寬接近
        total_w = sum(x2 - x1 for x1, x2 in contained)
        pattern_total = sum(pattern_widths)
        if abs(total_w - pattern_total) / pattern_total > tol * 2:
            break
        top_bound = y

        # 往下檢查
    bottom_bound = match_row
    for y in range(match_row + 1, min(h, match_row + 20)):
        runs = runs_by_row[y]
        contained = [(x1, x2) for x1, x2, c in runs if x1 < pattern_right and x2 > pattern_left]
        if not contained:
            break
        total_w = sum(x2 - x1 for x1, x2 in contained)
        pattern_total = sum(pattern_widths)
        if abs(total_w - pattern_total) / pattern_total > tol * 2:
            break
        bottom_bound = y

    vertical_span = bottom_bound - top_bound
    if vertical_span >= MIN_VERTICAL_CONTINUOUS:
        return True, top_bound, bottom_bound
    return False, top_bound, bottom_bound


def check_vertical_consistency_direct(img_rgb, runs_by_row: List[List[Tuple[int, int]]], match_row: int,
                               pattern_left: int, pattern_right: int, pattern_widths: List[int], 
                               unit_width: float, debug_logs: List[str], row_idx: int) -> Tuple[bool, int, int]:
    """
    直接使用 pattern 位置進行垂直一致性檢查
    """
    w, h = img_rgb.size
    pattern_total = sum(pattern_widths)
    tol = 0.40  # 40% 容差
    
    debug_logs.append(f"[VERTICAL] match_row={match_row}, pattern_left={pattern_left}, pattern_right={pattern_right}, total_width={pattern_total}")
    
    # 往上檢查
    top_bound = match_row
    up_count = 0
    for y in range(match_row - 1, max(0, match_row - 20), -1):
        runs = runs_by_row[y]
        # 找在 pattern_left~pattern_right 範圍內的 runs
        contained = [(x1, x2) for x1, x2, c in runs if x1 < pattern_right and x2 > pattern_left]
        if not contained:
            debug_logs.append(f"[VERTICAL] Row {y} (up): no runs in range [{pattern_left}, {pattern_right}]")
            break
        total_w = sum(x2 - x1 for x1, x2 in contained)
        ratio = total_w / pattern_total if pattern_total > 0 else 0
        debug_logs.append(f"[VERTICAL] Row {y} (up): contained widths={[x2-x1 for x1,x2 in contained]}, total={total_w}, ratio={ratio:.2f}")
        if abs(total_w - pattern_total) / pattern_total > tol:
            debug_logs.append(f"[VERTICAL] Row {y}: ratio {ratio:.2f} > tol {tol}, break")
            break
        top_bound = y
        up_count += 1

    # 往下檢查
    bottom_bound = match_row
    down_count = 0
    for y in range(match_row + 1, min(h, match_row + 20)):
        runs = runs_by_row[y]
        contained = [(x1, x2) for x1, x2, c in runs if x1 < pattern_right and x2 > pattern_left]
        if not contained:
            debug_logs.append(f"[VERTICAL] Row {y} (down): no runs in range [{pattern_left}, {pattern_right}]")
            break
        total_w = sum(x2 - x1 for x1, x2 in contained)
        ratio = total_w / pattern_total if pattern_total > 0 else 0
        debug_logs.append(f"[VERTICAL] Row {y} (down): contained widths={[x2-x1 for x1,x2 in contained]}, total={total_w}, ratio={ratio:.2f}")
        if abs(total_w - pattern_total) / pattern_total > tol:
            debug_logs.append(f"[VERTICAL] Row {y}: ratio {ratio:.2f} > tol {tol}, break")
            break
        bottom_bound = y
        down_count += 1

    vertical_span = bottom_bound - top_bound
    debug_logs.append(f"[VERTICAL] Result: top={top_bound}, bottom={bottom_bound}, span={vertical_span}, min={MIN_VERTICAL_CONTINUOUS}, up_count={up_count}, down_count={down_count}")
    
    if vertical_span >= MIN_VERTICAL_CONTINUOUS:
        return True, top_bound, bottom_bound
    return False, top_bound, bottom_bound


def find_block_bounds_by_pixel(image_path: str) -> Optional[Tuple[int, int, int, int]]:
    """
    用 █ pattern (█ ██ 重複) 定位校準區塊上界，用 [END] 文字偵測下界。
    回傳 (left, top, right, bottom)
    """
    from PIL import Image
    img = Image.open(image_path)
    w, h = img.size
    bin_img, _ = preprocess_for_pixel(img)

    # 取得每行的黑色 runs
    runs_by_row = find_horizontal_runs(bin_img)

    # 估計單格寬度：取所有 run 寬度的中位數
    all_widths = []
    for runs in runs_by_row:
        for x1, x2 in runs:
            all_widths.append(x2 - x1)
    if not all_widths:
        return None
    unit_width = sorted(all_widths)[len(all_widths) // 2]
    if unit_width <= 0:
        unit_width = 1

    # 由上往下掃描，找 first pattern 匹配的行
    block_top = None
    block_left = None
    block_right = None

    for y, runs in enumerate(runs_by_row):
        if len(runs) < 4:  # 至少需要 4 個 runs 才能容納 pattern
            continue
        量化序列 = quantize_runs(runs, unit_width)
        match_idx = match_pattern_sliding(量化序列, BLOCK_PATTERN, BLOCK_PATTERN_TOL)
        if match_idx >= 0:
            # 找到 pattern，記錄為上界
            block_top = y
            # 找 block_left：第 match_idx 個 run 的起點
            block_left = runs[match_idx][0]
            # 找 block_right：倒數幾個 run 的終點（容許前面有標籤如 R:）
            if len(runs) >= match_idx + len(BLOCK_PATTERN):
                last_run_idx = match_idx + len(BLOCK_PATTERN) - 1
                block_right = runs[last_run_idx][1]
            else:
                block_right = runs[-1][1]
            break

    if block_top is None:
        return None

    # 找下界：用 OCR 找 [END] 或保守估計為 block_top + 固定行數
    # 先嘗試用像素找整行 █（結尾標記）
    block_bottom = None
    for y in range(block_top + 5, min(block_top + 20, h)):
        runs = runs_by_row[y] if y < len(runs_by_row) else []
        # 若整行幾乎被黑色填滿，視為結尾標記
        total_black = sum(x2 - x1 for x1, x2 in runs)
        if total_black > w * 0.7:
            block_bottom = y + 1
            break

    # 若找不到結尾標記，用 block_top + 固定行數（約 8 行）
    if block_bottom is None:
        block_bottom = block_top + 8

    if block_right is None:
        block_right = w - 10

    return (block_left, block_top, block_right, block_bottom)


def find_block_bounds_by_pixel(image_path: str, pattern: List[int] = None) -> Optional[Tuple[int, int, int, int]]:
    """
    用 █ pattern 定位校準區塊。
    - pattern: 自訂 pattern，如 [1,2,1,2,1,2,1,2]，預設為 BLOCK_PATTERN_DEFAULT
    - 支援最小單位寬度 >= 5px，20% 容差
    - 支援顏色一致性檢查
    - 垂直方向連續性驗證（>= 8px）
    回傳 (left, top, right, bottom)
    """
    from PIL import Image
    debug_logs = []  # 收集調試日誌

    if pattern is None:
        pattern = BLOCK_PATTERN_DEFAULT

    debug_logs.append(f"[PIXEL] Input pattern: {pattern}")
    debug_logs.append(f"[PIXEL] MIN_UNIT_WIDTH: {MIN_UNIT_WIDTH}, TOLERANCE: {UNIT_TOLERANCE}")

    img = Image.open(image_path)
    w, h = img.size

    debug_logs.append(f"[PIXEL] Image size: {w}x{h}")

    # 載入 RGB 圖像用於顏色分析
    img_rgb = img.convert("RGB")

    # 以 luma+Otsu 取得每行「前景 runs」（避免顏色毛邊造成 run 被切碎/或整行同色）
    runs_by_row, _, _, otsu_thr, fg_is_bright, fg_ratio = get_pixel_runs_otsu_luma(img_rgb)
    debug_logs.append(f"[PIXEL] Otsu threshold (luma): {otsu_thr}")
    debug_logs.append(f"[PIXEL] Foreground class: {'bright' if fg_is_bright else 'dark'} (ratio={fg_ratio:.3f})")

    # 估計單格寬度（最小為 MIN_UNIT_WIDTH=5px）
    unit_width = estimate_unit_width(runs_by_row)
    debug_logs.append(f"[PIXEL] Estimated unit_width: {unit_width}px")

    # 由上往下掃描，找 pattern 匹配的行
    block_top = None
    block_left = None
    block_right = None
    match_info = None
    # 記錄每個已 match 的範圍 (top, bottom, left, right)，測試新點前排除落在這些範圍內的候選
    matched_ranges = []

    rows_checked = 0
    matches_found = 0

    for y, runs in enumerate(runs_by_row):
        rows_checked += 1
        if len(runs) < len(pattern):
            if y < 5:  # 只記錄前5行
                debug_logs.append(f"[PIXEL] Row {y}: runs count {len(runs)} < pattern length {len(pattern)}, widths={[r[1]-r[0] for r in runs][:10]}")
            continue

        # 使用寬度直接比對 pattern（此處 runs 為前景 runs，屬 dense_mode）
        k = [r[1] - r[0] for r in runs]
        
        if y < 5:  # 只記錄前5行
            debug_logs.append(f"[PIXEL] Row {y}: runs widths={k}")

        # 追蹤已匹配的索引，避免重複
        matched_indices = set()
        
        # 使用新的寬度比對演算法 - 迴圈直到沒有新匹配
        while True:
            all_matches = match_pattern_by_width(k, pattern, debug_logs, y, matched_indices)
            
            # 過濾掉已匹配的
            new_matches = [m for m in all_matches if m['start_idx'] not in matched_indices]
            
            if not new_matches:
                break
            
            for match_result in new_matches:
                match_idx = match_result['start_idx']
                end_idx = match_result.get('end_idx', match_idx + len(pattern) - 1)
                # 先取得此候選的 x 範圍（像素）
                first_run = runs[match_idx]
                last_run = runs[end_idx] if end_idx < len(runs) else runs[-1]
                pattern_start_x = first_run[0]
                pattern_end_x = last_run[1]

                # 測試新點前：確認不在「已 match 的範圍」內（有重疊則跳過）
                def in_matched_range(row, x_start, x_end):
                    for (t, b, l, r) in matched_ranges:
                        if t <= row <= b and not (x_end <= l or x_start >= r):
                            return True  # 有重疊
                    return False

                if in_matched_range(y, pattern_start_x, pattern_end_x):
                    matched_indices.add(match_idx)
                    continue

                matched_indices.add(match_idx)
                matches_found += 1
                unit_width = match_result['unit_width']
                actual_widths = match_result.get('actual_widths') or get_actual_pattern_widths(runs, len(pattern), match_idx)
                debug_logs.append(f"[PIXEL] Row {y}: pattern found at idx={match_idx}, unit_width={unit_width:.1f}, actual_widths={actual_widths}")

                debug_logs.append(f"[PIXEL] Row {y}: === Vertical Check Start ===")
                debug_logs.append(f"[PIXEL] Row {y}: match_row={y}, actual_widths={actual_widths}, unit_width={unit_width:.1f}")
                debug_logs.append(f"[PIXEL] Row {y}: pattern x range: {pattern_start_x} to {pattern_end_x}")

                valid, top_bound, bottom_bound = check_vertical_consistency_direct(
                    img_rgb, runs_by_row, y, pattern_start_x, pattern_end_x, actual_widths, unit_width, debug_logs, y
                )

                debug_logs.append(f"[PIXEL] Row {y}: vertical consistency check: valid={valid}, top_bound={top_bound}, bottom_bound={bottom_bound}, span={bottom_bound - top_bound if top_bound and bottom_bound else 0}")
                debug_logs.append(f"[PIXEL] Row {y}: === Vertical Check End ===")

                if valid:
                    block_left_cur = first_run[0]
                    block_right_cur = last_run[1]
                    matched_ranges.append((top_bound, bottom_bound, block_left_cur, block_right_cur))
                    debug_logs.append(f"[PIXEL] SUCCESS: Found valid block #{len(matched_ranges)} at row {y}, bounds=({block_left_cur}, {top_bound}, {block_right_cur}, {bottom_bound}), start_idx={match_idx}")
                    # 第一個有效 match 作為主要回傳結果（向後相容）
                    if match_info is None:
                        block_top = top_bound
                        block_left = block_left_cur
                        block_right = block_right_cur
                        match_info = {
                            "row": y,
                            "left": block_left_cur,
                            "right": block_right_cur,
                            "widths": actual_widths,
                            "unit_width": unit_width,
                            "top": top_bound,
                            "bottom": bottom_bound,
                        }

    debug_logs.append(f"[PIXEL] Scanned {rows_checked} rows, found {matches_found} matches, {len(matched_ranges)} distinct regions")
    if block_top is None:
        debug_logs.append("[PIXEL] No valid pattern found")

    # 輸出調試日誌
    for log in debug_logs:
        print(log, file=sys.stderr)

    if block_top is None:
        return None

    # 找下界：使用 block_bottom（從垂直驗證取得）或往後找黑色填充行
    block_bottom = match_info["bottom"] if match_info else block_top + 8

    # 往後找結尾標記（整行黑色填充）
    for y in range(block_bottom + 2, min(h, block_bottom + 15)):
        runs = runs_by_row[y] if y < len(runs_by_row) else []
        total_black = sum(r[1] - r[0] for r in runs)
        if total_black > w * 0.7:
            block_bottom = y + 1
            break

    # 保守估計
    if block_bottom <= block_top:
        block_bottom = block_top + 8

    return (block_left, block_top, block_right, block_bottom)


# ⚠️ 必須單獨測量的字元（寬度經常與其他字元不一致）
MUST_MEASURE_INDIVIDUALLY = {
    '-',  # 連接符：在許多字型中寬度與其他 ASCII 字元不一致
    '=',  # 等號：寬度變化極大
    '_',  # 底線：在某些字型中會延伸到字元框外
    '*',  # 星號：在某些字型中特別小或特別大
}

# ASCII 字元分類定義（用代表字元減少校準工作量）
# 注意：MUST_MEASURE_INDIVIDUALLY 中的字元會被排除在分類之外
ASCII_CHAR_CATEGORIES = {
    "uppercase": {
        "chars": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "representative": "A",  # 基準字元
        "description": "大寫字母（通常等寬）"
    },
    "lowercase": {
        "chars": "abcdefghijklmnopqrstuvwxyz",
        "representative": "a",
        "description": "小寫字母（通常等寬）"
    },
    "digits": {
        "chars": "0123456789",
        "representative": "0",
        "description": "數字（等寬字型中等寬）"
    },
    "narrow_punct": {
        "chars": ".,;:!'\"`",
        "representative": ".",
        "description": "窄標點符號"
    },
    "brackets": {
        "chars": "()[]{}<>",
        "representative": "(",
        "description": "括號類符號"
    },
    "other_operators": {
        "chars": "+",  # 移除 -_=*（必須單獨測量）
        "representative": "+",
        "description": "其他運算符"
    },
    "slashes": {
        "chars": "/\\|",
        "representative": "/",
        "description": "斜線和豎線"
    },
    "special": {
        "chars": "@#$%^&~?",  # 移除 *（必須單獨測量）
        "representative": "@",
        "description": "特殊符號"
    }
}

# 框線字元分類（單線 vs 雙線）
BOX_CHAR_CATEGORIES = {
    "single_line": {
        "chars": "─│┌┐└┘├┤┬┴┼",
        "representative": "─",
        "description": "單線框線"
    },
    "double_line": {
        "chars": "═║╔╗╚╝╠╣╬",
        "representative": "═",
        "description": "雙線框線"
    },
    "mixed_line": {
        "chars": "╒╓╕╖╘╙╛╜╞╟╡╢╤╥╧╨╪╫",
        "representative": "╒",
        "description": "混合線框線"
    }
}


def get_representative_for_char(char: str) -> Optional[str]:
    """
    取得字元的代表字元（用於分類歸納）
    
    參數：
        char: 要查詢的字元
    
    回傳：
        代表字元，如果找不到則回傳 None
        如果是必須單獨測量的字元，回傳 None（表示不使用代表）
    
    範例：
        get_representative_for_char('B') -> 'A'  # 大寫字母用 A 代表
        get_representative_for_char('b') -> 'a'  # 小寫字母用 a 代表
        get_representative_for_char('5') -> '0'  # 數字用 0 代表
        get_representative_for_char('-') -> None  # 必須單獨測量
        get_representative_for_char('=') -> None  # 必須單獨測量
        get_representative_for_char('字') -> None  # CJK 沒有代表，返回 None
    """
    # ⚠️ 必須單獨測量的字元，不使用代表
    if char in MUST_MEASURE_INDIVIDUALLY:
        return None
    
    # 檢查 ASCII 字元類別
    for cat_name, cat_info in ASCII_CHAR_CATEGORIES.items():
        if char in cat_info["chars"]:
            return cat_info["representative"]
    
    # 檢查框線字元類別
    for cat_name, cat_info in BOX_CHAR_CATEGORIES.items():
        if char in cat_info["chars"]:
            return cat_info["representative"]
    
    # 找不到代表字元（如 CJK、emoji 等）
    return None


def get_representative_chars(include_all_categories: bool = False) -> List[str]:
    """
    取得代表字元列表（涵蓋大部分 ASCII 字元類型）
    
    參數：
        include_all_categories: 是否包含所有類別（False 則只包含常用類別）
    
    回傳：
        代表字元列表，A 永遠在第一位
        包含必須單獨測量的字元 (-, =, 等)
    """
    representatives = []
    
    # 1. 基準字元 A（必須第一個）
    representatives.append('A')
    
    # 2. 其他 ASCII 類別代表
    priority_categories = ["lowercase", "digits", "narrow_punct", "other_operators", "brackets"]
    optional_categories = ["slashes", "special"]
    
    for cat_name in priority_categories:
        if cat_name in ASCII_CHAR_CATEGORIES:
            cat = ASCII_CHAR_CATEGORIES[cat_name]
            rep = cat["representative"]
            if rep != 'A' and rep not in representatives:
                representatives.append(rep)
    
    if include_all_categories:
        for cat_name in optional_categories:
            cat = ASCII_CHAR_CATEGORIES[cat_name]
            rep = cat["representative"]
            if rep not in representatives:
                representatives.append(rep)
    
    # 3. ⚠️ 加入必須單獨測量的字元
    for char in sorted(MUST_MEASURE_INDIVIDUALLY):
        if char not in representatives:
            representatives.append(char)
    
    return representatives


def extract_chars_from_ascii_pattern(table_data: Dict[str, Any], box_chars: Dict[str, str] = None, 
                                     include_defaults: bool = True, use_representatives: bool = True) -> str:
    """
    從 ASCII table 數據和框線設定中提取所有需要校準的字元
    
    參數：
        table_data: 表格數據 {"headers": [...], "rows": [[...], ...]}
        box_chars: 框線字元設定 {"tl": "╔", "tr": "╗", ...}
        include_defaults: 是否包含預設必要字元
        use_representatives: 是否使用代表字元（減少校準數量）
    
    回傳：
        字元字串，第一個字元必為 'A'（基準）
        
    策略：
    - use_representatives=True: 只包含每類的代表字元（如 A 代表所有大寫字母）
    - use_representatives=False: 包含所有實際使用的字元
    """
    unique_chars = set()
    
    # === 預設必要字元（代表字元方式）===
    if include_defaults and use_representatives:
        # 使用代表字元（減少首次校準數量）
        representatives = get_representative_chars(include_all_categories=False)
        unique_chars.update(representatives)
    elif include_defaults:
        # 傳統方式（包含更多字元）
        unique_chars.add('A')
        unique_chars.add('-')
        unique_chars.update('.,:;!?()[]')
        unique_chars.update('0123456789')
    
    # === 從表格數據中提取字元 ===
    table_chars = set()
    if table_data:
        # 提取標題欄字元
        headers = table_data.get("headers", [])
        for header in headers:
            if isinstance(header, str):
                for char in header:
                    if char.strip():
                        table_chars.add(char)
        
        # 提取資料列字元
        rows = table_data.get("rows", [])
        for row in rows:
            if isinstance(row, list):
                for cell in row:
                    if isinstance(cell, str):
                        for char in cell:
                            if char.strip():
                                table_chars.add(char)
                    elif isinstance(cell, (int, float)):
                        for char in str(cell):
                            if char.strip():
                                table_chars.add(char)
    
    # === 處理提取的表格字元 ===
    if use_representatives:
        # 用代表字元替代（減少校準數量）
        for char in table_chars:
            rep = get_representative_for_char(char)
            if rep:
                unique_chars.add(rep)
            else:
                # 找不到代表字元的（如 CJK、emoji），直接加入
                unique_chars.add(char)
    else:
        # 直接加入所有字元
        unique_chars.update(table_chars)
    
    # === 從框線字元中提取 ===
    if box_chars:
        for key, char in box_chars.items():
            if char and char.strip():
                if use_representatives:
                    # 判斷框線類型，使用代表字元
                    if char in BOX_CHAR_CATEGORIES["single_line"]["chars"]:
                        unique_chars.add("─")
                    elif char in BOX_CHAR_CATEGORIES["double_line"]["chars"]:
                        unique_chars.add("═")
                    elif char in BOX_CHAR_CATEGORIES["mixed_line"]["chars"]:
                        unique_chars.add("╒")
                    else:
                        unique_chars.add(char)
                else:
                    unique_chars.add(char)
    
    # 3. 轉換為字串（保持一定順序：A 必須第一 -> 其他 ASCII -> 框線 -> CJK）
    result_chars = []
    
    # ⚠️ 字母 A 必須是第一個（作為基準）
    if 'A' in unique_chars:
        result_chars.append('A')
        unique_chars.remove('A')
    
    # ASCII 數字和字母（排除 A）
    ascii_alnum = sorted([c for c in unique_chars if ord(c) < 128 and c.isalnum()])
    result_chars.extend(ascii_alnum)
    
    # ASCII 標點符號（包含 -）
    ascii_punct = sorted([c for c in unique_chars if ord(c) < 128 and not c.isalnum() and c not in result_chars])
    result_chars.extend(ascii_punct)
    
    # b. 框線字元（theme 用到的）
    box_chars_list = sorted([c for c in unique_chars if c in '─═│║╔╗╚╝┌┐└┘├┤┬┴┼╠╣╬┏┓┗┛┣┫┳┻╋'])
    result_chars.extend(box_chars_list)
    
    # e. CJK 字元（同語言寬度通常一致）
    cjk_chars = sorted([c for c in unique_chars if ord(c) >= 0x4E00 and ord(c) <= 0x9FFF])
    # 限制 CJK 字元數量（取前幾個代表即可）
    result_chars.extend(cjk_chars[:10])
    
    # 其他字元（包含 emoji 等）
    other_chars = sorted([c for c in unique_chars if c not in result_chars])
    result_chars.extend(other_chars[:5])
    
    # 確保 A 在第一位
    final_chars = ''.join(result_chars[:50])  # 限制最多 50 個字元
    if not final_chars.startswith('A') and 'A' in final_chars:
        final_chars = 'A' + final_chars.replace('A', '')
    
    return final_chars


def generate_calibration_pattern(
    start_pattern: List[int] = None,
    end_pattern: List[int] = None,
    test_chars: str = "ABCDE─═│║╔╗╚╝┼字",
    chars_per_line: int = 2,
    mode: str = "pixel"
) -> str:
    """
    生成校正圖案（ASCII 字串）供用戶截圖使用
    
    參數：
        start_pattern: 開始錨點 pattern，如 [1, 2, 1, 3, 1, 2]
        end_pattern: 結束錨點 pattern，如 [2, 1, 3, 1, 2, 1]
        test_chars: 測試字元字串
        chars_per_line: 每行測試字元數（1-7）
        mode: "pixel" 或 "ocr"（目前只支援 pixel）
    
    回傳：
        多行 ASCII 校正圖字串
    """
    if start_pattern is None:
        start_pattern = [1, 2, 1, 3, 1, 2]
    if end_pattern is None:
        end_pattern = [2, 1, 3, 1, 2, 1]
    
    lines = []
    
    if mode == "pixel":
        # === Pixel 模式 ===
        # 開始錨點：根據 pattern 生成
        start_parts = []
        for n in start_pattern:
            start_parts.append(BLOCK_CHAR * n)
            start_parts.append(' ')
        start_line = ''.join(start_parts).rstrip()
        lines.append(start_line)
        
        # 空白校準行: █ + 5半形空白 + █ + 1半形空白 + █ + 5全形空白 + █
        lines.append(f'{BLOCK_CHAR}     {BLOCK_CHAR} {BLOCK_CHAR}\u3000\u3000\u3000\u3000\u3000{BLOCK_CHAR}')
        
        # 測試行：每行 chars_per_line 個字元
        # 格式: █ + 半形空白 + (5個測試字) + 半形空白 + █
        # 如果有兩組，中間加: 半形空白 + █ + 半形空白
        chars = [c for c in test_chars if c.strip()]
        for i in range(0, len(chars), chars_per_line):
            line_chars = chars[i:i + chars_per_line]
            line_parts = []
            for j, char in enumerate(line_chars):
                if j == 0:
                    line_parts.append(f'{BLOCK_CHAR} {char * 5} {BLOCK_CHAR}')
                else:
                    line_parts.append(f' {BLOCK_CHAR} {char * 5} {BLOCK_CHAR}')
            lines.append(''.join(line_parts))
        
        # 結束錨點：根據 pattern 生成
        end_parts = []
        for n in end_pattern:
            end_parts.append(BLOCK_CHAR * n)
            end_parts.append(' ')
        end_line = ''.join(end_parts).rstrip()
        lines.append(end_line)
    
    else:  # OCR 模式
        # 目前不實作，保留擴展性
        lines.append('[ZENT-BLE-MKR]')
        lines.append('// OCR mode not implemented yet')
        lines.append('[END]')
    
    return '\n'.join(lines)


def analyze_vertical_blocks(img_rgb, start_x: int, start_y: int, end_y: int, 
                            test_chars_count: int, chars_per_line: int) -> Dict:
    """
    分析垂直線 (start_x, start_y) 到 (start_x, end_y) 的色塊分布。
    
    步驟：
    1. 垂直掃描，記錄連續色塊的像素長度與顏色
    2. 第一個色塊 = 背景色，第二個色塊 = 文字色
    3. 驗證色塊數量是否符合預期：(行數 * 2 + 1)
    4. 對每行文字掃描第一個 █ 的寬度
    
    回傳：
    {
        "text_color": (R, G, B),
        "bg_color": (R, G, B),
        "vertical_blocks": [長度1, 長度2, ...],
        "block_colors": [(R,G,B), (R,G,B), ...],
        "expected_blocks": N * 2 + 1,
        "is_valid": bool,
        "row_block_widths": [每行第一個█的寬度]
    }
    """
    import math
    
    w, h = img_rgb.size
    
    # 計算預期行數
    content_lines = 1 + math.ceil(test_chars_count / chars_per_line)  # 1(空白) + ceil(字數/每行)
    expected_blocks = content_lines * 2 + 1
    
    # 確保座標在範圍內
    if start_x < 0 or start_x >= w or start_y < 0 or end_y >= h or start_y >= end_y:
        return {
            "text_color": (0, 0, 0),
            "bg_color": (255, 255, 255),
            "vertical_blocks": [],
            "block_colors": [],
            "expected_blocks": expected_blocks,
            "is_valid": False,
            "content_lines": content_lines,
            "row_block_widths": [],
            "error": "Invalid coordinates"
        }
    
    # === 垂直掃描，記錄連續色塊與顏色 ===
    vertical_blocks = []  # 記錄每個色塊的長度
    block_colors = []     # 記錄每個色塊的顏色
    
    current_color = None
    current_length = 0
    
    for y in range(start_y, min(end_y + 1, h)):
        pixel = img_rgb.getpixel((start_x, y))
        
        if current_color is None:
            # 第一個像素
            current_color = pixel
            current_length = 1
        elif current_color == pixel:
            # 同色，累加
            current_length += 1
        else:
            # 顏色變化，記錄前一個色塊
            vertical_blocks.append(current_length)
            block_colors.append(current_color)
            current_color = pixel
            current_length = 1
    
    # 記錄最後一個色塊
    if current_length > 0:
        vertical_blocks.append(current_length)
        block_colors.append(current_color)
    
    # === 確定文字顏色與背景顏色 ===
    # 第一個色塊 = 背景色，第二個色塊 = 文字色
    bg_color = block_colors[0] if len(block_colors) > 0 else (255, 255, 255)
    text_color = block_colors[1] if len(block_colors) > 1 else (0, 0, 0)
    
    # === 驗證 ===
    is_valid = len(vertical_blocks) == expected_blocks
    
    # 舊算法棄用：不再用垂直掃描推算每行第一個 █ 寬度
    # row_block_widths 將在 find_calibration_start_point() 內，
    # 由第一文字行水平分析得到前景色後再重算。
    row_block_widths = []
    
    return {
        "text_color": text_color,
        "bg_color": bg_color,
        "vertical_blocks": vertical_blocks,
        "block_colors": block_colors,
        "expected_blocks": expected_blocks,
        "is_valid": is_valid,
        "content_lines": content_lines,
        "text_height": vertical_blocks[1] if len(vertical_blocks) > 1 else 0,
        "line_spacing": vertical_blocks[2] if len(vertical_blocks) > 2 else 0,
        "row_block_widths": row_block_widths
    }


def analyze_first_row_horizontal(img_rgb, start_x: int, start_y: int, row_height: int, 
                                  debug_logs: List[str] = None) -> Dict:
    """
    分析第一文字行的水平連續色塊，推斷前景色與背景色。
    
    第一文字行只有 █ 和空白，適合做顏色推斷。
    格式: █ + 5半形空白 + █ + 1半形空白 + █ + 5全形空白 + █
    
    步驟：
    1. 從左往右掃描，記錄所有連續色塊（含毛邊）
    2. 記錄每個色塊的 RGB 顏色
    3. 統計顏色出現頻率（容許值內合併）
    4. 找出背景色（最多）和前景色（第二多）
    
    參數：
        img_rgb: PIL Image (RGB)
        start_x: 第一文字行的起始 x 座標
        start_y: 第一文字行的起始 y 座標（左上角）
        row_height: 該行的高度（像素）
        debug_logs: 調試日誌列表
    
    回傳：
        {
            "horizontal_blocks": [長度1, 長度2, ...],
            "block_colors": [(R,G,B), ...],
            "fg_color": (R, G, B),
            "bg_color": (R, G, B),
            "row_width": 總寬度,
            "row_right_x": 右邊界 x 座標
        }
    """
    if debug_logs is None:
        debug_logs = []
    
    w, h = img_rgb.size
    px = img_rgb.load()
    
    # === 步驟 1：水平掃描，記錄連續色塊 ===
    # 掃描該行中間一行（避免上下邊緣毛邊影響顏色判斷）
    scan_y = start_y + row_height // 2
    if scan_y >= h:
        scan_y = start_y
    
    debug_logs.append(f"[HORIZONTAL] 第一文字行水平掃描開始")
    debug_logs.append(f"[HORIZONTAL] start_x={start_x}, start_y={start_y}, row_height={row_height}, scan_y={scan_y}")
    
    # 從 start_x 往右掃描，記錄連續色塊
    # 需求：以 >2px 視為主要色塊（含 3px 毛邊間隔），當主要色塊累計到第 7 塊時即停止。
    horizontal_blocks = []  # 每個色塊的長度
    block_colors = []        # 每個色塊的顏色
    major_block_count = 0

    x = start_x
    while x < w:
        current_color = px[x, scan_y]
        run_start = x
        run_length = 0
        
        # 累積連續同色像素
        while x < w:
            pixel_color = px[x, scan_y]
            # 顏色容差（RGB 各差 15 以內視為同色）
            if colors_similar_strict(pixel_color, current_color, tolerance=15):
                run_length += 1
                x += 1
            else:
                break
        
        if run_length > 0:
            horizontal_blocks.append(run_length)
            block_colors.append(current_color)
            debug_logs.append(f"[HORIZONTAL] 色塊 #{len(horizontal_blocks)}: x={run_start}, 長度={run_length}, 顏色={current_color}")
            if run_length > 2:
                major_block_count += 1
                if major_block_count >= 7:
                    break
    
    debug_logs.append(f"[HORIZONTAL] 第一文字行連續色塊記錄陣列: {horizontal_blocks}")
    
    # === 步驟 2：統計顏色出現頻率（容許值內合併）===
    color_stats = {}  # {(R,G,B): 總像素數}
    COLOR_TOLERANCE = 20  # 顏色容差
    
    for i, color in enumerate(block_colors):
        length = horizontal_blocks[i]
        
        # 尋找是否已有相似顏色
        found_similar = False
        for existing_color in color_stats:
            if colors_similar_strict(color, existing_color, tolerance=COLOR_TOLERANCE):
                # 合併到現有顏色
                color_stats[existing_color] += length
                found_similar = True
                break
        
        if not found_similar:
            # 新顏色
            color_stats[color] = length
    
    debug_logs.append(f"[HORIZONTAL] 顏色統計（容差={COLOR_TOLERANCE}）:")
    
    # 排序：像素數由多到少
    sorted_colors = sorted(color_stats.items(), key=lambda x: x[1], reverse=True)
    for color, count in sorted_colors:
        debug_logs.append(f"[HORIZONTAL]   顏色 {color}: {count} 像素")
    
    # === 步驟 3：決定前景色與背景色 ===
    if len(sorted_colors) >= 2:
        bg_color = sorted_colors[0][0]  # 最多的是背景色
        fg_color = sorted_colors[1][0]  # 第二多的是前景色（█）
    elif len(sorted_colors) == 1:
        bg_color = sorted_colors[0][0]
        fg_color = (0, 0, 0)  # 預設黑色
    else:
        bg_color = (255, 255, 255)
        fg_color = (0, 0, 0)
    
    debug_logs.append(f"[HORIZONTAL] 判定結果: 背景色={bg_color}, 前景色={fg_color}")
    
    # === 步驟 4：由第一行 run 推算單一 block 寬度 ===
    major_runs = [v for v in horizontal_blocks if v > 2]
    first_seven = major_runs[:7]
    odd_block_widths = [first_seven[i] for i in [0, 2, 4, 6] if i < len(first_seven)]
    estimated_block_width = (sum(odd_block_widths) / 4.0) if len(odd_block_widths) == 4 else 0.0
    debug_logs.append(f"[HORIZONTAL] >2px 主要色塊(前7): {first_seven}")
    debug_logs.append(f"[HORIZONTAL] 第1/3/5/7塊(視為█): {odd_block_widths}")
    debug_logs.append(f"[HORIZONTAL] 推算單一█寬度: {estimated_block_width:.3f}")
    # #region agent log
    _debug_log("calibrate_analyze.py:first_row_est", "odd_block_widths and estimated_block_width", {"odd_block_widths": odd_block_widths, "estimated_block_width": estimated_block_width, "min_odd": min(odd_block_widths) if odd_block_widths else 0, "max_odd": max(odd_block_widths) if odd_block_widths else 0}, "H1")
    # #endregion

    # === 步驟 5：計算行的總寬度和右邊界 ===
    row_width = sum(horizontal_blocks)
    row_right_x = start_x + row_width
    
    debug_logs.append(f"[HORIZONTAL] 行總寬度: {row_width}, 右邊界 x: {row_right_x}")
    debug_logs.append(f"[HORIZONTAL] 第一文字行水平掃描結束")
    
    # 將 tuple 轉換為字串格式（JSON 兼容）
    def color_to_str(c):
        return f"rgb({c[0]},{c[1]},{c[2]})"
    
    color_stats_json = {color_to_str(c): count for c, count in sorted_colors}
    block_colors_json = [color_to_str(c) for c in block_colors]
    
    return {
        "horizontal_blocks": horizontal_blocks,
        "block_colors": block_colors_json,
        "fg_color": fg_color,
        "bg_color": bg_color,
        "row_width": row_width,
        "row_right_x": row_right_x,
        "color_stats": color_stats_json,
        "major_blocks_gt3": first_seven,
        "block_widths_1_3_5_7": odd_block_widths,
        "estimated_block_width": round(estimated_block_width, 3)
    }


def colors_similar_strict(c1: Tuple[int, int, int], c2: Tuple[int, int, int], tolerance: int = 15) -> bool:
    """檢查兩顏色是否在容差範圍內相似"""
    return (abs(c1[0] - c2[0]) <= tolerance and
            abs(c1[1] - c2[1]) <= tolerance and
            abs(c1[2] - c2[2]) <= tolerance)


def find_all_blocks_by_projection(img_rgb, vertical_blocks: List[int], start_x: int, start_y: int,
                                   target_width: int, text_color: Tuple[int, int, int], 
                                   size_tolerance: int = 1) -> List[Dict]:
    """
    使用投影陣列找出所有符合尺寸的色塊
    
    步驟：
    1. 對每個文字行建立水平投影陣列
    2. 找出連續完全投影區域（投影值 = 行高）
    3. 判定寬度是否符合目標 ± 容差
    4. 記錄所有符合的區塊座標
    
    參數：
        img_rgb: PIL Image (RGB)
        vertical_blocks: [長度1, 長度2, ...] 垂直色塊長度陣列
        start_x, start_y: 校準起點座標
        target_width: 目標寬度（第一個 █ 的寬度）
        text_color: (R, G, B) 文字顏色
        size_tolerance: 尺寸容差（像素）
    
    回傳：
        [{"row": 行號, "x": x, "y": y, "width": w, "height": h}, ...]
    """
    w, h = img_rgb.size
    
    def is_similar_color(c1, c2, tolerance=30):
        """判斷兩個顏色是否相似"""
        return all(abs(c1[i] - c2[i]) <= tolerance for i in range(3))
    
    def get_column_projection(x, y_top, y_bottom):
        """計算該列的文字像素數（垂直投影）"""
        count = 0
        for y in range(y_top, y_bottom + 1):
            if x >= w or y >= h:
                continue
            pixel = img_rgb.getpixel((x, y))
            if is_similar_color(pixel, text_color):
                count += 1
        return count
    
    all_blocks = []
    
    # 遍歷每個文字行
    cumulative_y = start_y
    row_index = 0
    
    for idx in range(len(vertical_blocks)):
        block_length = vertical_blocks[idx]
        
        # 只處理偶數位（文字行）：索引 1, 3, 5, ...
        if idx % 2 == 1:
            y_top = cumulative_y
            y_bottom = cumulative_y + block_length - 1
            row_height = block_length
            
            # === 建立這一行的投影陣列 ===
            max_scan_width = w - start_x
            projection_array = []
            
            for dx in range(max_scan_width):
                x = start_x + dx
                projection = get_column_projection(x, y_top, y_bottom)
                projection_array.append(projection)
            
            # === 分析投影陣列，找出連續完全投影區域 ===
            # 完全投影 = 投影值 == row_height
            x = 0
            while x < len(projection_array):
                # 如果當前列是完全投影
                if projection_array[x] == row_height:
                    # 計算連續完全投影的長度
                    continuous_width = 0
                    start_offset = x
                    
                    while x < len(projection_array) and projection_array[x] == row_height:
                        continuous_width += 1
                        x += 1
                    
                    # 判定是否符合目標寬度 ± 容差
                    # #region agent log
                    if row_index == 0 and len(all_blocks) < 20:
                        _debug_log("calibrate_analyze.py:projection_run", "continuous_width vs target", {"continuous_width": continuous_width, "target_width": target_width, "size_tolerance": size_tolerance, "match": abs(continuous_width - target_width) <= size_tolerance}, "H2")
                    # #endregion
                    if abs(continuous_width - target_width) <= size_tolerance:
                        all_blocks.append({
                            "row": row_index + 1,
                            "x": start_x + start_offset,
                            "y": y_top,
                            "width": continuous_width,
                            "height": row_height
                        })
                else:
                    x += 1
            
            row_index += 1
        
        cumulative_y += block_length
    
    # #region agent log
    _debug_log("calibrate_analyze.py:find_blocks_result", "find_all_blocks_by_projection result", {"total_blocks": len(all_blocks), "target_width": target_width, "size_tolerance": size_tolerance}, "H2")
    # #endregion
    return all_blocks


def calculate_calibration_from_gaps(gap_widths: List[Dict], test_chars: str, repeat_count: int = 5,
                                    test_char_groups: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    從空隙寬度計算標準 calibration JSON（方案 B：相對寬度 + 像素基準）
    
    參數：
        gap_widths: [{"row": 1, "gaps": [{"gap_width": 30, ...}, ...]}, ...]
        test_chars: 測試字元字串，如 "ABCDE─═│║╔╗╚╝┼字"
    
    回傳：
        {
            "calibration": {
                "half_space": 1.0,
                "full_space": 2.0,
                "ascii": 1.742,
                "cjk": 1.935,
                "box": 1.0,
                "custom": {...}
            },
            "pixel_per_unit": 6.2
        }
    """
    # 收集所有間隙值
    all_gaps = []
    for row_data in gap_widths:
        for gap_info in row_data["gaps"]:
            all_gaps.append(gap_info["gap_width"])
    
    if len(all_gaps) < 2:
        return {"error": "Not enough gaps (需要至少2個間隙)"}
    
    safe_repeat = max(1, int(repeat_count) if isinstance(repeat_count, int) else 5)

    # === 計算像素寬度（保留完整精度）===
    half_space_px = all_gaps[0] / float(safe_repeat)  # 第一個間隙 ÷ repeat_count
    full_space_px = all_gaps[1] / float(safe_repeat)  # 第二個間隙 ÷ repeat_count
    
    # === 先計算所有測試字元的像素寬度，尋找字母 A 作為基準 ===
    ascii_a_px = None
    char_px_map = {}
    
    test_tokens = list(test_char_groups) if test_char_groups else iter_display_tokens(test_chars)
    if len(all_gaps) > 2 and test_tokens:
        for i in range(2, len(all_gaps)):
            char_index = i - 2
            if char_index >= len(test_tokens):
                break
            
            char = test_tokens[char_index]
            gap = all_gaps[i]
            
            # 計算字元像素寬度：(間隙 - 半形空白×2) ÷ repeat_count
            char_px = (gap - half_space_px * 2) / float(safe_repeat)
            char_px_map[char] = char_px
            
            # 尋找字母 A 作為基準（最高優先級）
            if char == 'A' and ascii_a_px is None:
                ascii_a_px = char_px
            # 如果沒有 A，用其他 ASCII 字母/數字
            elif ascii_a_px is None and char in '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz':
                ascii_a_px = char_px
    
    # === 基準值：以字母 A 為 1.0（如果沒有 A，使用半形空白）===
    if ascii_a_px is None or ascii_a_px <= 0:
        ascii_a_px = half_space_px
        print(f"[WARNING] 未找到字母 A 或 ASCII 字元，使用半形空白作為基準: {ascii_a_px:.2f}px", file=sys.stderr)
    
    pixel_per_unit = ascii_a_px
    
    # === 計算相對寬度（所有寬度相對於 A）===
    calibration = {
        "ascii": 1.0,  # 基準固定為 1.0（字母 A）
        "half_space": half_space_px / ascii_a_px,
        "full_space": full_space_px / ascii_a_px
    }
    
    # === 測試字元寬度 ===
    if char_px_map:
        custom = {}
        ascii_widths = []
        cjk_widths = []
        box_widths = []
        
        for char, char_px in char_px_map.items():
            # 計算相對寬度：字元寬度 ÷ 基準寬度（A）
            char_relative = char_px / ascii_a_px
            
            # 分類字元
            if len(char) == 1 and char.isascii() and char.isalnum():
                ascii_widths.append(char_relative)
            elif len(char) == 1 and ord(char) >= 0x4E00 and ord(char) <= 0x9FFF:  # CJK 統一漢字
                cjk_widths.append(char_relative)
            elif len(char) == 1 and char in '─═│║╔╗╚╝┌┐└┘├┤┬┴┼':  # 框線字元
                box_widths.append(char_relative)
            
            custom[char] = char_relative
        
        # 計算各類別平均值
        if ascii_widths:
            calibration["ascii"] = sum(ascii_widths) / len(ascii_widths)
        if cjk_widths:
            calibration["cjk"] = sum(cjk_widths) / len(cjk_widths)
        if box_widths:
            calibration["box"] = sum(box_widths) / len(box_widths)
        
        if custom:
            calibration["custom"] = custom
    
    # === 四捨五入到 3 位小數（只在輸出時）===
    def round_dict(d, precision=3):
        """遞迴四捨五入字典中的數值"""
        result = {}
        for k, v in d.items():
            if isinstance(v, dict):
                result[k] = round_dict(v, precision)
            elif isinstance(v, (int, float)):
                result[k] = round(v, precision)
            else:
                result[k] = v
        return result
    
    return {
        "calibration": round_dict(calibration, 3),
        "pixel_per_unit": round(pixel_per_unit, 3)
    }


def find_calibration_start_point(image_path: str, start_pattern: List[int], end_pattern: List[int], 
                                test_chars_count: int = 0, chars_per_line: int = 2, test_chars_str: str = '',
                                repeat_count: int = 5, test_char_groups: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    找出字元寬度測量的起點座標，並分析垂直色塊。

    步驟：
    1. 使用 start_pattern 找到開始錨點，記錄左下點座標
    2. 使用 end_pattern 找到結束錨點，記錄左上點座標
    3. 比較 X 值是否一致（相同或差1以內），取較大值
    4. 設定校準起點為 (X, start_y + 1)
    5. 分析垂直色塊，驗證行數

    回傳：
    {
        "success": True,
        "start_x": X 座標,
        "start_y": start_y + 1,
        "start_anchor_bottom_left": (x, y),
        "end_anchor_top_left": (x, y),
        "vertical_analysis": { text_color, bg_color, vertical_blocks, ... },
        "debug_logs": [...]
    }
    若失敗回傳 {"success": False, "error": "...", "debug_logs": [...]}
    """
    from PIL import Image

    debug_logs = []

    if not start_pattern or not end_pattern:
        debug_logs.append("[CAL_START] Error: start_pattern or end_pattern is empty")
        return {
            "success": False,
            "error": "start_pattern or end_pattern is empty",
            "start_candidates": [],
            "end_candidates": [],
            "debug_logs": debug_logs
        }

    debug_logs.append(f"[CAL_START] start_pattern: {start_pattern}")
    debug_logs.append(f"[CAL_START] end_pattern: {end_pattern}")

    img = Image.open(image_path)
    w, h = img.size
    img_rgb = img.convert("RGB")

    debug_logs.append(f"[CAL_START] Image size: {w}x{h}")

    # 以 luma+Otsu 取得每行前景 runs（較不受毛邊顏色影響）
    runs_by_row, _, _, otsu_thr, fg_is_bright, fg_ratio = get_pixel_runs_otsu_luma(img_rgb)
    debug_logs.append(f"[CAL_START] Otsu threshold (luma): {otsu_thr}")
    debug_logs.append(f"[CAL_START] Foreground class: {'bright' if fg_is_bright else 'dark'} (ratio={fg_ratio:.3f})")

    # === 第一步：找開始錨點（記錄左下點）===
    start_anchor = None
    start_candidates: List[Dict[str, Any]] = []
    for y, runs in enumerate(runs_by_row):
        if len(runs) < len(start_pattern):
            continue

        k = [r[1] - r[0] for r in runs]
        matched_indices = set()

        while True:
            matches = match_pattern_by_width(k, start_pattern, debug_logs, y, matched_indices)
            new_matches = [m for m in matches if m['start_idx'] not in matched_indices]

            if not new_matches:
                break

            for match_result in new_matches:
                match_idx = match_result['start_idx']
                end_idx = match_result.get('end_idx', match_idx + len(start_pattern) - 1)
                matched_indices.add(match_idx)

                actual_widths = match_result.get('actual_widths') or get_actual_pattern_widths(runs, len(start_pattern), match_idx)
                unit_width = match_result['unit_width']

                # 計算 pattern 的 x 範圍
                first_run = runs[match_idx]
                last_run = runs[end_idx] if end_idx < len(runs) else runs[-1]
                pattern_start_x = first_run[0]
                pattern_end_x = last_run[1]

                # 垂直一致性檢查
                valid, top_bound, bottom_bound = check_vertical_consistency_direct(
                    img_rgb, runs_by_row, y, pattern_start_x, pattern_end_x,
                    actual_widths, unit_width, debug_logs, y
                )

                if valid:
                    ratio_seq = []
                    if unit_width > 0:
                        ratio_seq = [round(w / unit_width, 2) for w in actual_widths]
                    win_l = max(0, match_idx - 4)
                    win_r = min(len(k), end_idx + 5)
                    window_widths = k[win_l:win_r]
                    candidate = {
                        "x": pattern_start_x,
                        "y": bottom_bound,  # 底部y座標
                        "top": top_bound,
                        "bottom": bottom_bound,
                        "row": y,
                        "start_idx": match_idx,
                        "end_idx": end_idx,
                        "unit_width": round(unit_width, 3),
                        "actual_widths": actual_widths,
                        "ratio_seq": ratio_seq,
                        "window_widths": window_widths,
                    }
                    start_candidates.append(candidate)
                    debug_logs.append(
                        f"[CAL_START] Candidate start anchor at row {y}, "
                        f"bottom-left=({pattern_start_x}, {bottom_bound}), idx={match_idx}-{end_idx}, "
                        f"unit={unit_width:.2f}, actual={actual_widths}, ratio={ratio_seq}, "
                        f"k_window[{win_l}:{win_r}]={window_widths}"
                    )

    if start_candidates:
        # 維持舊邏輯傾向：優先最早列，再取較左側
        start_candidates.sort(key=lambda c: (c["row"], c["x"]))
        start_anchor = start_candidates[0]
        top3 = start_candidates[:3]
        top3_brief = [
            {
                "row": c["row"],
                "x": c["x"],
                "idx": [c["start_idx"], c["end_idx"]],
                "ratio": c["ratio_seq"],
            }
            for c in top3
        ]
        debug_logs.append(
            f"[CAL_START] Selected start anchor at row {start_anchor['row']}, "
            f"bottom-left=({start_anchor['x']}, {start_anchor['y']}), "
            f"candidate_count={len(start_candidates)}, top3={top3_brief}"
        )

    if not start_anchor:
        debug_logs.append("[CAL_START] Failed: Cannot find start anchor")
        return {
            "success": False,
            "error": "Cannot find start anchor",
            "start_candidates": [],
            "end_candidates": [],
            "debug_logs": debug_logs
        }

    # === 第二步：找結束錨點（記錄左上點）===
    end_anchor = None
    start_x = start_anchor["x"]
    end_candidates: List[Dict[str, Any]] = []
    for y, runs in enumerate(runs_by_row):
        if len(runs) < len(end_pattern):
            continue

        k = [r[1] - r[0] for r in runs]
        matched_indices = set()

        while True:
            matches = match_pattern_by_width(k, end_pattern, debug_logs, y, matched_indices)
            new_matches = [m for m in matches if m['start_idx'] not in matched_indices]

            if not new_matches:
                break

            for match_result in new_matches:
                match_idx = match_result['start_idx']
                end_idx = match_result.get('end_idx', match_idx + len(end_pattern) - 1)
                matched_indices.add(match_idx)

                actual_widths = match_result.get('actual_widths') or get_actual_pattern_widths(runs, len(end_pattern), match_idx)
                unit_width = match_result['unit_width']

                # 計算 pattern 的 x 範圍
                first_run = runs[match_idx]
                last_run = runs[end_idx] if end_idx < len(runs) else runs[-1]
                pattern_start_x = first_run[0]
                pattern_end_x = last_run[1]

                # 垂直一致性檢查
                valid, top_bound, bottom_bound = check_vertical_consistency_direct(
                    img_rgb, runs_by_row, y, pattern_start_x, pattern_end_x,
                    actual_widths, unit_width, debug_logs, y
                )

                if valid:
                    ratio_seq = []
                    if unit_width > 0:
                        ratio_seq = [round(w / unit_width, 2) for w in actual_widths]
                    win_l = max(0, match_idx - 4)
                    win_r = min(len(k), end_idx + 5)
                    window_widths = k[win_l:win_r]
                    candidate = {
                        "x": pattern_start_x,
                        "y": top_bound,  # 頂部y座標
                        "top": top_bound,
                        "bottom": bottom_bound,
                        "row": y,
                        "x_diff": abs(pattern_start_x - start_x),
                        "start_idx": match_idx,
                        "end_idx": end_idx,
                        "unit_width": round(unit_width, 3),
                        "actual_widths": actual_widths,
                        "ratio_seq": ratio_seq,
                        "window_widths": window_widths,
                    }
                    end_candidates.append(candidate)
                    debug_logs.append(
                        f"[CAL_START] Candidate end anchor at row {y}, "
                        f"top-left=({pattern_start_x}, {top_bound}), x_diff={candidate['x_diff']}, "
                        f"idx={match_idx}-{end_idx}, unit={unit_width:.2f}, "
                        f"actual={actual_widths}, ratio={ratio_seq}, k_window[{win_l}:{win_r}]={window_widths}"
                    )

    if end_candidates:
        # 優先採用 x 最接近 start_anchor 的候選；同 x_diff 時，優先較早出現的列
        end_candidates.sort(key=lambda c: (c["x_diff"], c["row"]))
        end_anchor = end_candidates[0]
        top3 = end_candidates[:3]
        top3_brief = [
            {
                "row": c["row"],
                "x": c["x"],
                "x_diff": c["x_diff"],
                "idx": [c["start_idx"], c["end_idx"]],
                "ratio": c["ratio_seq"],
            }
            for c in top3
        ]
        debug_logs.append(
            f"[CAL_START] Selected end anchor at row {end_anchor['row']}, "
            f"top-left=({end_anchor['x']}, {end_anchor['y']}), x_diff={end_anchor['x_diff']}, "
            f"candidate_count={len(end_candidates)}, top3={top3_brief}"
        )

    if not end_anchor:
        debug_logs.append("[CAL_START] Failed: Cannot find end anchor")
        return {
            "success": False,
            "error": "Cannot find end anchor",
            "start_candidates": start_candidates,
            "end_candidates": end_candidates,
            "debug_logs": debug_logs
        }

    # === 第三步：比較 X 值 ===
    start_x = start_anchor["x"]
    end_x = end_anchor["x"]
    x_diff = abs(start_x - end_x)

    debug_logs.append(f"[CAL_START] start_x={start_x}, end_x={end_x}, diff={x_diff}")

    if x_diff > 1:
        debug_logs.append(f"[CAL_START] Failed: X values differ by more than 1 ({x_diff})")
        return {
            "success": False,
            "error": f"X values differ by more than 1 ({x_diff})",
            "start_candidates": start_candidates,
            "end_candidates": end_candidates,
            "debug_logs": debug_logs
        }

    # 取較大值
    calibration_x = max(start_x, end_x)
    start_y = start_anchor["y"]

    # === 第四步：設定校準起點 ===
    calibration_y = start_y + 1

    debug_logs.append(f"[CAL_START] Calibration start point: ({calibration_x}, {calibration_y})")

    # === 第五步：分析垂直色塊（若有提供字符數） ===
    vertical_analysis = None
    if test_chars_count > 0:
        end_y = end_anchor["y"] - 1
        debug_logs.append(f"[VERTICAL_BLOCKS] Analyzing from ({calibration_x}, {calibration_y}) to ({calibration_x}, {end_y})")
        debug_logs.append(f"[VERTICAL_BLOCKS] test_chars_count={test_chars_count}, chars_per_line={chars_per_line}")
        
        vertical_analysis = analyze_vertical_blocks(
            img_rgb, calibration_x, calibration_y, end_y, 
            test_chars_count, chars_per_line
        )
        
        debug_logs.append(f"[VERTICAL_BLOCKS] Text color: {vertical_analysis['text_color']}")
        debug_logs.append(f"[VERTICAL_BLOCKS] BG color: {vertical_analysis['bg_color']}")
        debug_logs.append(f"[VERTICAL_BLOCKS] Blocks: {vertical_analysis['vertical_blocks']}")
        debug_logs.append(f"[VERTICAL_BLOCKS] Expected: {vertical_analysis['expected_blocks']}, Actual: {len(vertical_analysis['vertical_blocks'])}")
        debug_logs.append(f"[VERTICAL_BLOCKS] Valid: {vertical_analysis['is_valid']}")
    
    # === 第六步：分析第一文字行的水平色塊（推斷前景色與背景色）===
    first_row_horizontal = None
    if vertical_analysis and len(vertical_analysis.get('vertical_blocks', [])) >= 2:
        vertical_blocks = vertical_analysis['vertical_blocks']
        # 第一文字行 = 索引 1（vertical_blocks 的奇數位）
        # y_top = calibration_y + vertical_blocks[0]（第一個背景間距）
        # row_height = vertical_blocks[1]（第一文字行高度）
        
        first_row_y_top = calibration_y + vertical_blocks[0]
        first_row_height = vertical_blocks[1]
        
        debug_logs.append(f"[FIRST_ROW] 第一文字行 y_top={first_row_y_top}, height={first_row_height}")
        
        first_row_horizontal = analyze_first_row_horizontal(
            img_rgb, calibration_x, first_row_y_top, first_row_height, debug_logs
        )
        
        # 用水平掃描結果更新顏色（比垂直掃描更準確）
        if first_row_horizontal:
            debug_logs.append(f"[FIRST_ROW] 水平掃描結果更新顏色判定:")
            debug_logs.append(f"[FIRST_ROW]   新前景色: {first_row_horizontal['fg_color']}")
            debug_logs.append(f"[FIRST_ROW]   新背景色: {first_row_horizontal['bg_color']}")
            if vertical_analysis:
                vertical_analysis['text_color'] = first_row_horizontal['fg_color']
                vertical_analysis['bg_color'] = first_row_horizontal['bg_color']
                # 新算法：由第一文字行 run 推得單一█寬度，套用到每個文字行
                est = first_row_horizontal.get('estimated_block_width', 0.0) if first_row_horizontal else 0.0
                vb = vertical_analysis.get('vertical_blocks', [])
                row_count = len([1 for i in range(len(vb)) if i % 2 == 1])
                if est > 0 and row_count > 0:
                    w_int = int(round(est))
                    vertical_analysis['row_block_widths'] = [w_int for _ in range(row_count)]
                    debug_logs.append(f"[ROW_WIDTH_RECALC] 使用第一文字行推算寬度: {est:.3f} -> 各行={w_int}px, row_count={row_count}")
                else:
                    vertical_analysis['row_block_widths'] = []
                    debug_logs.append("[ROW_WIDTH_RECALC] 失敗：第一文字行推算寬度不足，row_block_widths 保持空陣列")
        else:
            debug_logs.append("[FIRST_ROW] 水平掃描失敗，row_block_widths 將保持空陣列（舊算法已棄用）")
    
    # === 找出所有符合尺寸的色塊 ===
    all_blocks = []
    gap_widths = []
    gap_errors = []
    
    if vertical_analysis and len(vertical_analysis.get('row_block_widths', [])) > 0:
        target_width = vertical_analysis['row_block_widths'][0]  # 第一個 █ 的寬度
        vertical_blocks = vertical_analysis['vertical_blocks']
        
        # 使用水平掃描得到的顏色（更準確）
        if first_row_horizontal:
            text_color = first_row_horizontal['fg_color']
            debug_logs.append(f"[FIND_BLOCKS] 使用水平掃描前景色: {text_color}")
        else:
            text_color = vertical_analysis['text_color']
            debug_logs.append(f"[FIND_BLOCKS] 使用垂直掃描前景色: {text_color}")
        
        debug_logs.append(f"[FIND_BLOCKS] Target width: {target_width}px")
        debug_logs.append(f"[FIND_BLOCKS] Scanning from ({calibration_x}, {calibration_y})")
        # #region agent log
        _debug_log("calibrate_analyze.py:before_find_blocks", "target_width passed to find_all_blocks_by_projection", {"target_width": target_width, "calibration_x": calibration_x, "calibration_y": calibration_y}, "H2")
        # #endregion
        all_blocks = find_all_blocks_by_projection(
            img_rgb=img_rgb,
            vertical_blocks=vertical_blocks,
            start_x=calibration_x,
            start_y=calibration_y,
            target_width=target_width,
            text_color=text_color,
            size_tolerance=1
        )
        
        debug_logs.append(f"[FIND_BLOCKS] Found {len(all_blocks)} matching blocks")
        
        # === 計算空隙寬度 ===
        # 按行分組
        blocks_by_row = {}
        for block in all_blocks:
            row = block['row']
            if row not in blocks_by_row:
                blocks_by_row[row] = []
            blocks_by_row[row].append(block)
        
        # 對每行計算空隙
        for row_num in sorted(blocks_by_row.keys()):
            blocks = blocks_by_row[row_num]
            
            # 檢查區塊數是否為雙數
            if len(blocks) % 2 != 0:
                gap_errors.append({
                    "row": row_num,
                    "block_count": len(blocks),
                    "message": f"第 {row_num} 行的區塊數為 {len(blocks)}（奇數），無法配對"
                })
                debug_logs.append(f"[GAP_ERROR] Row {row_num}: odd number of blocks ({len(blocks)})")
                continue
            
            # 兩個一組計算空隙寬度
            row_gaps = []
            for i in range(0, len(blocks), 2):
                block1 = blocks[i]
                block2 = blocks[i + 1]
                
                # 計算邊界
                block1_right = block1['x'] + block1['width'] - 1
                block2_left = block2['x']
                
                # 計算空隙：後面的起始點 - 前面的結束點 - 1
                gap_width = block2_left - block1_right - 1
                
                row_gaps.append({
                    "pair": i // 2 + 1,
                    "block1_left": block1['x'],
                    "block1_right": block1_right,
                    "block2_left": block2_left,
                    "block2_right": block2_left + block2['width'] - 1,
                    "gap_width": gap_width
                })
                
                debug_logs.append(f"[GAP] Row {row_num}, Pair {i//2 + 1}: "
                                f"{block2_left} - {block1_right} - 1 = {gap_width}")
            
            gap_widths.append({
                "row": row_num,
                "gaps": row_gaps
            })
    elif vertical_analysis:
        debug_logs.append("[FIND_BLOCKS] 略過：row_block_widths 為空（需先完成 FIRST_ROW 顏色重算）")
    
    # === 計算標準 calibration JSON（方案 B）===
    calibration_result = None
    if gap_widths and len(gap_widths) > 0:
        calibration_result = calculate_calibration_from_gaps(
            gap_widths,
            test_chars_str,
            repeat_count=repeat_count,
            test_char_groups=test_char_groups
        )
        
        if "error" not in calibration_result:
            debug_logs.append(f"[CALIBRATION] pixel_per_unit: {calibration_result.get('pixel_per_unit', 0)}")
            debug_logs.append(f"[CALIBRATION] Generated standard calibration JSON")
        else:
            debug_logs.append(f"[CALIBRATION] Error: {calibration_result.get('error', 'unknown')}")

    return {
        "success": True,
        "start_x": calibration_x,
        "start_y": calibration_y,
        "start_anchor_bottom_left": (start_x, start_anchor["y"]),
        "end_anchor_top_left": (end_x, end_anchor["y"]),
        "start_candidates": start_candidates,
        "end_candidates": end_candidates,
        "vertical_analysis": vertical_analysis,
        "first_row_horizontal": first_row_horizontal,
        "all_blocks": all_blocks,
        "gap_widths": gap_widths,
        "gap_errors": gap_errors,
        "test_chars": test_chars_str,
        "repeat_count": repeat_count,
        "calibration": calibration_result.get("calibration") if calibration_result else None,
        "pixel_per_unit": calibration_result.get("pixel_per_unit") if calibration_result else None,
        "debug_logs": debug_logs,
    }


def find_block_bounds(ocr_data: List[Dict]) -> Optional[Tuple[int, int, int, int]]:
    """從 OCR 結果搜尋錨點與 [END]，回傳 (left, top, right, bottom)"""
    start_bbox = None
    end_bbox = None
    full_text = ""

    for i, row in enumerate(ocr_data):
        text = (row.get("text") or "").strip()
        if not text:
            continue
        full_text += text
        left = row.get("left", 0)
        top = row.get("top", 0)
        w = row.get("width", 0)
        h = row.get("height", 0)
        right = left + w
        bottom = top + h

        if (CAL_START in text or CAL_START in full_text or
                CAL_START_LEGACY in text or CAL_START_LEGACY in full_text):
            if start_bbox is None:
                start_bbox = (left, top, right, bottom)
        if CAL_END in text or CAL_END in full_text:
            end_bbox = (left, top, right, bottom)

    if start_bbox and end_bbox:
        return (
            start_bbox[0],
            start_bbox[1],
            end_bbox[2],
            end_bbox[3],
        )
    return None


def crop_to_block(image_path: str, bounds: Tuple[int, int, int, int], output_path: str) -> str:
    """裁切至區塊範圍"""
    from PIL import Image
    img = Image.open(image_path)
    cropped = img.crop(bounds)
    cropped.save(output_path)
    return output_path


def analyze_widths_by_pixel(image_path: str, custom_chars: str = "") -> Dict[str, Any]:
    """
    用像素計數方式分析校準區塊寬度（不依賴 OCR）。
    適用於 █字█ 格式的校準區塊。
    """
    from PIL import Image

    default_cal = {"ascii": 1.0, "cjk": 2.0, "box": 1.0, "half_space": 1.0, "full_space": 2.0, "emoji": 1.5}
    if custom_chars:
        default_cal["custom"] = {c: 2.0 for c in iter_display_tokens(custom_chars)}

    img = Image.open(image_path)
    w, h = img.size

    # 二值化
    bin_img, _ = preprocess_for_pixel(img)

    # 取得每行 runs
    runs_by_row = find_horizontal_runs(bin_img)

    # 估計單格寬度
    unit_width = estimate_unit_width(runs_by_row)

    # 建立行分組
    def group_by_line(items, tol=8):
        if not items:
            return []
        sorted_items = sorted(items, key=lambda x: (-x[1], x[0]))
        lines, current_line, current_y = [], [], None
        for t in sorted_items:
            y = t[1]
            if current_y is None or abs(y - current_y) <= tol:
                current_line.append(t)
                current_y = y if current_y is None else current_y
            else:
                if current_line:
                    lines.append(sorted(current_line, key=lambda x: x[0]))
                current_line, current_y = [t], y
        if current_line:
            lines.append(sorted(current_line, key=lambda x: x[0]))
        return lines

    # 將 runs 轉為 (left, right, y) 格式並分行
    all_runs = []
    for y, runs in enumerate(runs_by_row):
        for x1, x2 in runs:
            all_runs.append((x1, x2, y, x2 - x1))
    lines_boxes = group_by_line(all_runs)

    # 找第一行的 pattern 寬度作為 unit
    pixel_per_unit = None
    unit_chars = ("a", "A", "0", "1")

    # 掃描所有行，找典型半形字元的寬度
    for line_items in lines_boxes:
        for x1, x2, y, wid in line_items:
            if wid >= MIN_UNIT_WIDTH and pixel_per_unit is None:
                pixel_per_unit = wid
                break
        if pixel_per_unit:
            break

    if pixel_per_unit is None or pixel_per_unit <= 0:
        pixel_per_unit = unit_width

    def to_units(pw, force_one=False):
        if force_one:
            return 1.0
        return round(pw / pixel_per_unit, 3) if pixel_per_unit > 0 else 1.0

    # 測量各行█夾字元的寬度
    # 格式: R:██████████, A:█0██1██a█, C:█甲█, B:█║██═██│█, H:█ █, F:口　口
    ascii_w, cjk_w, box_w = 1.0, 2.0, 1.0
    half_space, full_space = 1.0, 2.0
    custom = {}
    char_measurements = []
    ocr_lines = []  # 像素模式沒有 OCR 文字

    # 依行首標籤分類測量
    label_map = {
        "R": "box",      # R: ██████████
        "A": "ascii",   # A: █0██1██a█
        "C": "cjk",     # C: █甲█
        "B": "box",     # B: █║██═██│█
        "H": "half_space",  # H: █ █
        "F": "full_space",  # F: 口　█
    }

    for line_items in lines_boxes:
        if not line_items:
            continue
        # 找這行第一個 run 的位置當作參考
        first_x = line_items[0][0]
        # 計算這行所有 runs 的總寬度
        total_w = sum(x2 - x1 for x1, x2, y, w in line_items)
        # 用第一個有效寬度當作 unit
        if pixel_per_unit is None:
            for x1, x2, y, wid in line_items:
                if wid >= MIN_UNIT_WIDTH:
                    pixel_per_unit = wid
                    break

        # 測量各字元寬度（█與字之間的間隙）
        # 這是簡化版本，直接用 runs 間距估計
        for i in range(len(line_items) - 1):
            x1, x2, y1, w1 = line_items[i]
            x1_next, x2_next, y2_next, w2 = line_items[i + 1]
            gap = x1_next - x2  # 間隙寬度
            if gap > 0 and gap < total_w * 0.5:  # 合理的間隙
                # 這可能是字元的寬度
                char_width = gap
                char_measurements.append({
                    "char": "?",
                    "pixel_width": char_width,
                    "unit_width": to_units(char_width)
                })

    # 沒有 OCR 時，用預設值
    return {
        "calibration": default_cal,
        "pixel_per_unit": round(pixel_per_unit, 2) if pixel_per_unit else 1.0,
        "ocr_lines": [],
        "char_measurements": char_measurements,
    }


def analyze_widths(image_path: str, custom_chars: str = "", use_ocr: bool = True) -> Dict[str, Any]:
    """
    分析校準區塊，計算各類別寬度。
    演算法：以半形 'A'（或 0,1,a）的像素寬度為 1 單位，測量各字元像素後除以單位得浮點數。
    - use_ocr: 是否使用 OCR（預設 True）。False 時使用像素計數方式。
    回傳 dict 含：calibration, pixel_per_unit, ocr_lines, char_measurements
    """
    default_cal = {"ascii": 1.0, "cjk": 2.0, "box": 1.0, "half_space": 1.0, "full_space": 2.0, "emoji": 1.5}
    custom_token_set = set(iter_display_tokens(custom_chars)) if custom_chars else set()
    if custom_chars:
        default_cal["custom"] = {c: 2.0 for c in custom_token_set}
    from PIL import Image

    # 不使用 OCR 時，用像素計數測量寬度
    if not use_ocr:
        return analyze_widths_by_pixel(image_path, custom_chars)

    try:
        import pytesseract
    except ImportError:
        return {"calibration": default_cal, "pixel_per_unit": 1.0, "ocr_lines": [], "char_measurements": []}

    img = Image.open(image_path)
    img = preprocess_for_ocr(img)
    w, h = img.size
    ascii_w, cjk_w, box_w = 1.0, 2.0, 1.0
    half_space, full_space = 1.0, 2.0
    custom = {}

    # OCR 行文字（image_to_data）
    ocr_lines = []
    try:
        data = pytesseract.image_to_data(img, lang="chi_tra+eng", output_type=pytesseract.Output.DICT, config="--psm 6")
        n = len(data.get("text", []))
        lines_dict = {}
        for i in range(n):
            text = (data.get("text", [""] * n)[i] or "").strip()
            ln = data.get("line_num", [0] * n)[i]
            if ln not in lines_dict:
                lines_dict[ln] = []
            lines_dict[ln].append(text)
        for ln in sorted(lines_dict.keys()):
            ocr_lines.append(" ".join(lines_dict[ln]))
    except Exception:
        pass

    try:
        boxes_raw = pytesseract.image_to_boxes(img, lang="chi_tra+eng", config="--psm 6")
    except Exception:
        boxes_raw = ""

    box_list = []
    for line in (boxes_raw or "").strip().splitlines():
        parts = line.strip().split()
        if len(parts) >= 5:
            ch = " " if parts[0] == "~" else parts[0]
            try:
                left, bottom, right, top = int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4])
                box_list.append((ch, left, right, bottom, top, right - left))
            except (ValueError, IndexError):
                pass

    def group_by_line(items, tol=8):
        if not items:
            return []
        sorted_items = sorted(items, key=lambda x: (-x[3], x[1]))
        lines, current_line, current_y = [], [], None
        for t in sorted_items:
            y = t[3]
            if current_y is None or abs(y - current_y) <= tol:
                current_line.append(t)
                current_y = y if current_y is None else current_y
            else:
                if current_line:
                    lines.append(sorted(current_line, key=lambda x: x[1]))
                current_line, current_y = [t], y
        if current_line:
            lines.append(sorted(current_line, key=lambda x: x[1]))
        return lines

    lines_boxes = group_by_line(box_list)
    # 單位基準：A: 行的 a, A, 0, 1 為半形單位 1，取其像素寬為 pixel_per_unit
    # 優先取單一字符（避免多個誤測平均），以 a/A 為首選
    pixel_per_unit = None
    unit_chars = ("a", "A", "0", "1")
    for line_items in lines_boxes:
        chars = "".join(t[0] for t in line_items)
        if any(c in chars for c in "01aA"):
            for preferred in ("a", "A", "0", "1"):
                for t in line_items:
                    if t[0] == preferred and t[5] > 0:
                        pixel_per_unit = t[5]
                        break
                if pixel_per_unit is not None:
                    break
            if pixel_per_unit is not None:
                break
    if pixel_per_unit is None or pixel_per_unit <= 0:
        pixel_per_unit = 1.0

    def to_units(pw, force_one=False):
        if force_one:
            return 1.0
        return round(pw / pixel_per_unit, 3) if pixel_per_unit > 0 else 1.0

    # 每個字元只輸出一筆，單位基準字強制 unit_width=1
    seen = {}
    for t in box_list:
        if t[5] <= 0:
            continue
        ch = t[0]
        if ch in seen:
            continue
        force_one = ch in unit_chars
        seen[ch] = {"char": ch, "pixel_width": t[5], "unit_width": to_units(t[5], force_one)}
    char_measurements = list(seen.values())

    for line_items in lines_boxes:
        chars = "".join(t[0] for t in line_items)
        if "甲" in chars:
            for t in line_items:
                if t[0] == "甲":
                    cjk_w = to_units(t[5])
                    break
        if any(x in chars for x in "║═│"):
            bw = [t[5] for t in line_items if t[0] in "║═│"]
            if bw:
                box_w = to_units(sum(bw) / len(bw))
        if "H" in chars:
            for t in line_items:
                if t[0] == " ":
                    half_space = to_units(t[5])
                    break
        if "F" in chars or "口" in chars or "　" in chars:
            for t in line_items:
                if t[0] == "　":
                    full_space = to_units(t[5])
                    break
        if "U" in chars and custom_token_set:
            for t in line_items:
                if t[0] in custom_token_set:
                    custom[t[0]] = to_units(t[5])

    calibration = {"ascii": ascii_w, "cjk": cjk_w, "box": box_w, "half_space": half_space, "full_space": full_space, "emoji": 1.5}
    if custom:
        calibration["custom"] = custom

    return {
        "calibration": calibration,
        "pixel_per_unit": round(pixel_per_unit, 2),
        "ocr_lines": ocr_lines,
        "char_measurements": char_measurements,
    }


OCR_BACKEND_DEFAULT = "tesseract"


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "用法: calibrate_analyze.py <image_path> [--custom-chars 字詞] [--ocr tesseract|rapidocr|none] [--pixel-pattern '1 2 1 2 ...'] [--pixel-end-pattern '2 1 3 1 2 1'] [--find-start-point] [--use-startpoint-pipeline] [--test-chars-count N] [--test-char-groups '\"U+XXXX\" \"U+AAAA U+BBBB\" ...']"}))
        sys.exit(1)

    image_path = sys.argv[1]
    custom_chars = ""
    ocr_backend = os.environ.get("OCR_BACKEND", OCR_BACKEND_DEFAULT)
    pixel_pattern_str = ""
    pixel_end_pattern_str = ""
    find_start_point_only = False
    use_startpoint_pipeline = False
    test_chars_str = ""
    test_chars_count_override = None
    test_char_groups_raw = ""
    chars_per_line_str = ""
    repeat_count = 5
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--custom-chars" and i + 1 < len(sys.argv):
            custom_chars = sys.argv[i + 1]
            i += 2
            continue
        elif sys.argv[i] == "--ocr" and i + 1 < len(sys.argv):
            ocr_backend = (sys.argv[i + 1] or "").strip().lower() or OCR_BACKEND_DEFAULT
            i += 2
            continue
        elif sys.argv[i] == "--pixel-pattern" and i + 1 < len(sys.argv):
            pixel_pattern_str = sys.argv[i + 1]
            i += 2
            continue
        elif sys.argv[i] == "--pixel-end-pattern" and i + 1 < len(sys.argv):
            pixel_end_pattern_str = sys.argv[i + 1]
            i += 2
            continue
        elif sys.argv[i] == "--find-start-point":
            find_start_point_only = True
            i += 1
            continue
        elif sys.argv[i] == "--use-startpoint-pipeline":
            use_startpoint_pipeline = True
            i += 1
            continue
        elif sys.argv[i] == "--test-chars" and i + 1 < len(sys.argv):
            test_chars_str = sys.argv[i + 1]
            i += 2
            continue
        elif sys.argv[i] == "--test-chars-count" and i + 1 < len(sys.argv):
            try:
                test_chars_count_override = int(sys.argv[i + 1])
            except ValueError:
                test_chars_count_override = None
            i += 2
            continue
        elif sys.argv[i] == "--test-char-groups" and i + 1 < len(sys.argv):
            test_char_groups_raw = sys.argv[i + 1]
            i += 2
            continue
        elif sys.argv[i] == "--chars-per-line" and i + 1 < len(sys.argv):
            chars_per_line_str = sys.argv[i + 1]
            i += 2
            continue
        elif sys.argv[i] == "--repeat-count" and i + 1 < len(sys.argv):
            try:
                repeat_count = int(sys.argv[i + 1])
            except ValueError:
                repeat_count = 5
            i += 2
            continue
        i += 1

    if not os.path.isfile(image_path):
        print(json.dumps({"success": False, "error": f"圖片不存在: {image_path}"}))
        sys.exit(1)

    # 解析 pixel pattern
    pixel_pattern = None
    if pixel_pattern_str:
        try:
            pixel_pattern = [int(x) for x in pixel_pattern_str.split() if int(x) > 0]
        except ValueError:
            pixel_pattern = None
    if not pixel_pattern:
        pixel_pattern = BLOCK_PATTERN_DEFAULT

    # 解析 end pixel pattern
    pixel_end_pattern = None
    if pixel_end_pattern_str:
        try:
            pixel_end_pattern = [int(x) for x in pixel_end_pattern_str.split() if int(x) > 0]
        except ValueError:
            pixel_end_pattern = None
    if not pixel_end_pattern:
        # 預設結束 pattern
        pixel_end_pattern = [2, 1, 3, 1, 2, 1]

    # 如果只找起點模式
    if find_start_point_only:
        import io
        from contextlib import redirect_stderr

        parsed_test_char_groups = parse_uplus_quoted_groups(test_char_groups_raw)
        # 解析測試字符數、每行字數、重複次數
        # 優先使用前端傳入的 test_chars_count（精準反映實際校準字元數）
        if test_chars_count_override is not None and test_chars_count_override >= 0:
            test_chars_count = test_chars_count_override
        else:
            # 後備：優先使用 quoted group，再退回顯示 token 計數
            test_chars_count = len(parsed_test_char_groups) if parsed_test_char_groups else (len(iter_display_tokens(test_chars_str)) if test_chars_str else 0)
        chars_per_line = int(chars_per_line_str) if chars_per_line_str and chars_per_line_str.isdigit() else 2
        repeat_count = max(1, min(20, repeat_count))

        stderr_capture = io.StringIO()
        with redirect_stderr(stderr_capture):
            result = find_calibration_start_point(
                image_path, pixel_pattern, pixel_end_pattern,
                test_chars_count, chars_per_line, test_chars_str, repeat_count, parsed_test_char_groups
            )

        if not isinstance(result, dict):
            result = {"success": False, "error": "Failed to find calibration start point", "debug_logs": []}
        stderr_lines = [ln for ln in stderr_capture.getvalue().strip().split('\n') if ln.strip()]
        result["debug_logs"] = result.get("debug_logs", []) + stderr_lines
        # 輸出單行 JSON（第一行是 JSON，後面是 debug logs）
        print(json.dumps(result, ensure_ascii=False))
        # debug logs 輸出到 stderr
        for log in result.get("debug_logs", []):
            print(log, file=sys.stderr)
        sys.exit(0)

    def _build_calibration_steps_summary(sp):
        """從 start_point 組裝步驟摘要字串（偵測範圍、行高、第一行色塊、顏色）"""
        lines = []
        lines.append("─────── 偵測的校正範圍 ───────")
        lines.append("校準起點: ({}, {})".format(sp.get("start_x", ""), sp.get("start_y", "")))
        start_anchor = sp.get("start_anchor_bottom_left")
        end_anchor = sp.get("end_anchor_top_left")
        if start_anchor is not None:
            lines.append("開始錨點左下: {}".format(start_anchor))
        if end_anchor is not None:
            lines.append("結束錨點左上: {}".format(end_anchor))
        va = sp.get("vertical_analysis")
        if va:
            lines.append("")
            lines.append("─────── 垂直色塊分析 ───────")
            lines.append("背景顏色: {}".format(va.get("bg_color", "")))
            lines.append("文字顏色: {}".format(va.get("text_color", "")))
            vb = va.get("vertical_blocks", [])
            if vb:
                lines.append("色塊高度陣列: {}".format(vb))
            row_widths = va.get("row_block_widths", [])
            if row_widths:
                lines.append("每行第一個 █ 寬度 (行高):")
                for i, w in enumerate(row_widths, 1):
                    lines.append("  第 {} 行: {}px".format(i, w))
        frh = sp.get("first_row_horizontal")
        if frh:
            lines.append("")
            lines.append("─────── 第一文字行連續色塊與顏色 ───────")
            lines.append("第一文字行連續色塊記錄陣列: {}".format(frh.get("horizontal_blocks", [])))
            lines.append("文字顏色(前景): {}".format(frh.get("fg_color", "")))
            lines.append("背景顏色: {}".format(frh.get("bg_color", "")))
            lines.append("推算單一█寬度: {} px".format(frh.get("estimated_block_width", "")))
        return "\n".join(lines)

    # 打包流程：同一次請求內完成「找起點 + 校準輸出」
    if use_startpoint_pipeline:
        import io
        from contextlib import redirect_stderr

        parsed_test_char_groups = parse_uplus_quoted_groups(test_char_groups_raw)
        if test_chars_count_override is not None and test_chars_count_override >= 0:
            test_chars_count = test_chars_count_override
        else:
            test_chars_count = len(parsed_test_char_groups) if parsed_test_char_groups else (len(iter_display_tokens(test_chars_str)) if test_chars_str else 0)
        chars_per_line = int(chars_per_line_str) if chars_per_line_str and chars_per_line_str.isdigit() else 2
        repeat_count = max(1, min(20, repeat_count))

        stderr_capture = io.StringIO()
        with redirect_stderr(stderr_capture):
            sp = find_calibration_start_point(
                image_path, pixel_pattern, pixel_end_pattern,
                test_chars_count, chars_per_line, test_chars_str, repeat_count, parsed_test_char_groups
            )

        if not isinstance(sp, dict) or not sp.get("success"):
            err = "Failed to run startpoint pipeline"
            if isinstance(sp, dict) and sp.get("error"):
                err = str(sp.get("error"))
            out_err = {"success": False, "error": err}
            if isinstance(sp, dict):
                out_err["start_point"] = sp
                out_err["pixel_debug_logs"] = sp.get("debug_logs", [])
            stderr_lines = [ln for ln in stderr_capture.getvalue().strip().split('\n') if ln.strip()]
            if stderr_lines:
                out_err["pixel_debug_logs"] = (out_err.get("pixel_debug_logs") or []) + stderr_lines
            print(json.dumps(out_err, ensure_ascii=False))
            sys.exit(0)

        calibration = sp.get("calibration")
        if not isinstance(calibration, dict):
            _steps = _build_calibration_steps_summary(sp)
            print(json.dumps({
                "success": False,
                "error": "Startpoint pipeline produced no calibration",
                "start_point": sp,
                "pixel_debug_logs": sp.get("debug_logs", []),
                "calibration_steps_summary": _steps,
            }, ensure_ascii=False))
            sys.exit(0)

        out_ok = {
            "success": True,
            "calibration": calibration,
            "pixel_per_unit": sp.get("pixel_per_unit", 1.0),
            "ocr_lines": [],
            "char_measurements": [],
            "ocr_method_used": "startpoint_pipeline",
            "start_point": sp,
            "pixel_debug_logs": sp.get("debug_logs", []),
            "calibration_steps_summary": _build_calibration_steps_summary(sp),
        }
        stderr_lines = [ln for ln in stderr_capture.getvalue().strip().split('\n') if ln.strip()]
        if stderr_lines:
            out_ok["pixel_debug_logs"] = (out_ok.get("pixel_debug_logs") or []) + stderr_lines
        print(json.dumps(out_ok, ensure_ascii=False))
        sys.exit(0)

    # 區塊定位
    bounds = None
    ocr_method_used = None
    pixel_debug_logs = []  # 收集 pixel 調試日誌

    if ocr_backend == "none":
        # 使用 pixel-based 定位（不依賴 OCR）
        import io
        from contextlib import redirect_stderr
        
        # 捕獲 stderr 中的調試日誌
        stderr_capture = io.StringIO()
        with redirect_stderr(stderr_capture):
            bounds = find_block_bounds_by_pixel(image_path, pattern=pixel_pattern)
        pixel_debug_logs = stderr_capture.getvalue().strip().split('\n') if stderr_capture.getvalue() else []
        
        ocr_method_used = "none"
    else:
        # 使用 OCR 定位（Tesseract 或 RapidOCR）
        ocr_data = run_ocr_full(image_path)
        bounds = find_block_bounds(ocr_data) if ocr_data else None
        ocr_method_used = ocr_backend

    work_path = image_path
    if bounds:
        cropped_path = image_path + ".cropped.png"
        try:
            crop_to_block(image_path, bounds, cropped_path)
            work_path = cropped_path
        except Exception:
            pass

    # 寬度分析：統一先走 pixel 路徑（不依賴 OCR）
    out = analyze_widths(work_path, custom_chars, use_ocr=False)
    calibration = out.get("calibration", {})
    output = {
        "success": True,
        "calibration": calibration,
        "pixel_per_unit": out.get("pixel_per_unit", 1.0),
        "ocr_lines": out.get("ocr_lines", []),
        "char_measurements": out.get("char_measurements", []),
        "ocr_method_used": ocr_method_used,
    }
    
    # 加入 pixel 調試日誌
    if pixel_debug_logs:
        output["pixel_debug_logs"] = pixel_debug_logs
    
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
