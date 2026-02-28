# Calibration Pixel Pipeline（像素解析步驟）

> 依目前程式碼整理：`calibrate_analyze.py`、`calibrate_upload.php`、`index.html`。
> 目標：說清楚校準不是固定字串，而是動態 pattern + 像素量測流程。

## 0. 入口與參數（前端 → PHP → Python）

1. 前端 `index.html` 組裝參數：
   - `pixel_pattern`
   - `pixel_end_pattern`
   - `test_chars` / `test_char_groups` / `test_chars_count`
   - `chars_per_line`
   - `repeat_count`
   - `ocr=none`
2. `calibrate_upload.php` 收到後呼叫 `calibrate_analyze.py`。
3. 若使用 `--use-startpoint-pipeline`，同一條路徑內完成：
   - 起終點錨點定位
   - 垂直/水平像素解析
   - gap 反推 calibration JSON

---

## 1. 圖像前處理（像素路徑）

主要函式：
- `otsu_threshold_from_luma()`
- `get_pixel_runs_otsu_luma()`

步驟：
1. 圖像轉 RGB，計算 luma（`0.299R + 0.587G + 0.114B`）。
2. 用 Otsu 算法自動找二值化閾值。
3. 以「較少數像素類別」視為前景（通常是文字/方塊）。
4. 逐行建立前景 runs（連續前景像素段）。

---

## 2. 單位寬度估計

主要函式：
- `estimate_unit_width(runs_by_row)`

步驟：
1. 收集 run 寬度，過濾小於 `MIN_UNIT_WIDTH`（預設 5px）。
2. 取寬度分布前 25% 分位估「單位寬」。
3. 後續 pattern 比對都以此 unit + 容差做判定。

---

## 3. 起/終錨點 Pattern 比對（動態，不是固定字串）

主要函式：
- `match_pattern_by_width()`
- `find_calibration_start_point()`

步驟：
1. 對每行 run 寬度序列 `k=[w1,w2,...]`。
2. 用 pattern（如 `1 2 1 3 1 2`）比對：
   - 以 unit 換算期望寬度
   - 20% 容差
   - 支援小裂縫合併（抗 anti-aliasing 斷裂）
3. 找到候選後，必須再過垂直一致性檢查。

---

## 4. 垂直一致性檢查

主要函式：
- `check_vertical_consistency_direct()`

步驟：
1. 取候選 pattern 的 `left/right` 範圍。
2. 往上、往下掃描附近行。
3. 比對該範圍前景總寬是否與 pattern 總寬接近（容差 40%）。
4. 連續跨度需達 `MIN_VERTICAL_CONTINUOUS`（預設 8px）才算有效。

---

## 5. 校準起點求解

在 `find_calibration_start_point()` 內：
1. 開始錨點取左下點。
2. 結束錨點取左上點。
3. 要求 X 對齊（差距 ≤ 1）。
4. 校準起點：
   - `calibration_x = max(start_x, end_x)`
   - `calibration_y = start_anchor_bottom + 1`

---

## 6. 垂直色塊解析（行高/間距）

主要函式：
- `analyze_vertical_blocks()`

步驟：
1. 沿 `calibration_x` 從 `start_y` 掃到 `end_y`。
2. 記錄連續同色塊高度陣列 `vertical_blocks`。
3. 驗證色塊數是否符合預期：`內容行數 * 2 + 1`。

---

## 7. 第一文字行水平色塊解析（顏色 + █寬）

主要函式：
- `analyze_first_row_horizontal()`

步驟：
1. 取第一文字行中線做水平掃描。
2. 記錄連續色塊長度 `horizontal_blocks`。
3. 顏色頻率判定：
   - 最多色 = 背景
   - 第二多色 = 前景
4. 取主要色塊前 7 段，使用第 1/3/5/7 段推估 `estimated_block_width`。

---

## 8. 全行 block 偵測與 gap 計算

主要函式：
- `find_all_blocks_by_projection()`

步驟：
1. 對每個文字行做列投影（每個 x 的前景像素數）。
2. 找完整投影連續區（視為 block）。
3. 依 `target_width ± tolerance` 篩選 block。
4. 兩兩配對，計算 gap：
   - `gap = block2_left - block1_right - 1`

---

## 9. 由 gap 反推 calibration JSON

主要函式：
- `calculate_calibration_from_gaps()`

步驟：
1. 用前兩個 gap 反推空白像素寬：
   - `half_space_px = gap1 / repeat_count`
   - `full_space_px = gap2 / repeat_count`
2. 其他 gap 反推字元像素寬：
   - `(gap - 2*half_space_px) / repeat_count`
3. 以 `A`（或 fallback ASCII）作基準 1.0。
4. 轉成相對寬度輸出：
   - `ascii`, `cjk`, `box`, `half_space`, `full_space`, `custom`

---

## 10. 回傳與封裝

- Python 回傳：
  - `calibration`
  - `pixel_per_unit`
  - `pixel_debug_logs`
  - `calibration_steps_summary`
- PHP 解析第一段 JSON，包裝回前端。
- 失敗時回錯誤，不應假成功。

---

## 備註

- 這套校準流程的核心是「動態 pattern + 像素量測」，不是固定校準字串模板。
- 只要 pattern、測試字元、重複次數不同，量測路徑和輸出自然會動態變化。
