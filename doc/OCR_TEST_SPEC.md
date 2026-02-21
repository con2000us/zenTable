# OCR 辨識能力測試：邏輯細節與輸出入規格

## 概述

本模組用於從終端截圖中定位錨點字串（如 `[ZENT-BLE-MKR]`），並回傳座標與裁切重辨結果。供 zeble 校準流程與 Skill 使用。

---

## 輸入規格

### CLI（`ocr_test_analyze.py`）

```
python3 ocr_test_analyze.py <image_path> [--anchor <自訂錨點>]
```

| 參數 | 必要 | 說明 |
|------|------|------|
| `image_path` | ✓ | 截圖檔案路徑（png, jpg, gif, webp） |
| `--anchor` |  | 自訂錨點字串，留空則用預設 `[ZENT-BLE-MKR]` |

### HTTP 上傳（`ocr_test_upload.php`）

- **方法**: `POST`
- **Content-Type**: `multipart/form-data`
- **欄位**:
  - `image`: 圖片檔案（必要）
  - `anchor`: 自訂錨點字串（選填）

---

## 輸出規格（JSON）

### 根層欄位

| 欄位 | 型別 | 說明 |
|------|------|------|
| `success` | boolean | 是否成功執行 |
| `target` | string | 實際使用的錨點字串 |
| `found` | boolean | 是否找到錨點 |
| `ocr_text` | string | OCR 辨識字串（前 200 字） |
| `bbox` | object \| null | 最佳候選在原圖的邊界框 |
| `img_size` | object | `{ width, height }` 原圖尺寸 |
| `elapsed_ms` | number | 執行時間（毫秒） |
| `match_stages` | object \| null | 字數存量比對詳情 |
| `candidates` | array | 候選清單（含 score、bbox、ocr_snippet） |
| `refined_run` | object \| null | 裁切重辨結果（見下） |

### `bbox` 格式

```json
{
  "left": 100,
  "top": 50,
  "right": 300,
  "bottom": 80,
  "width": 200,
  "height": 30
}
```

- 座標為**原圖像素**，左上 (0,0)，y 軸向下
- `left` < `right`，`top` < `bottom`

### `refined_run` 格式（裁切重辨成功時）

| 欄位 | 型別 | 說明 |
|------|------|------|
| `score` | number | 裁切後得分 |
| `avg` | number | 字數存量比對平均（%） |
| `ocr_snippet` | string | 裁切區域辨識字串 |
| `crop_bounds` | object | 裁切區塊在原圖邊界 `{ left, top, right, bottom }` |
| `original_bbox` | object | **最終範圍在原圖座標** `{ left, top, right, bottom, width, height }` |
| `annotated_image_base64` | string | 原圖標註圖（白線+文字）的 base64 PNG |
| `original_score` | number | 原第一名得分 |
| `better` | boolean | 裁切後是否較佳 |
| `crop_image_base64` | string | 裁切圖的 base64 PNG |
| `crop_size` | object | `{ width, height }` 裁切圖尺寸 |
| `refined_bbox` | object | 裁切圖內辨識範圍（相對座標） |
| `strategy` | string | 使用的預處理策略名稱 |

---

## OCR 使用邏輯細節

### 1. 預處理策略（二值化）

| 策略名稱 | 說明 |
|----------|------|
| `fixed128_invert` | 固定閾值 128，依內容區域 mean 反轉 |
| `fixed128_no_invert` | 固定閾值 128，不反轉 |
| `otsu_invert` | Otsu 自動閾值，依 mean 反轉 |
| `otsu_no_invert` | Otsu 自動閾值，不反轉 |
| `raw` | 僅灰階，無二值化 |

**內容區域閾值**：為避免外框/UI 邊界影響，閾值與反轉判斷僅使用影像中央約 92% 像素（外緣 4% 不計入）。

### 2. OCR 引擎

- **Tesseract**：`image_to_boxes`，`lang="chi_tra+eng"`，`--psm 6`
- 座標為 Tesseract 格式（bottom-origin），轉換為 top-origin 後使用

### 3. 錨點搜尋：字數存量比對

1. **滑窗**：以錨點長度 n 對 OCR 字串滑動
2. **三個分數**：
   - 全文：`char_count_match_rate(anchor, ocr_sub)`
   - 前半、後半：各取一半分別比對
3. **平均分數**：`(full + half1 + half2) / 3`
4. **門檻**：72%（`MATCH_THRESHOLD`）
5. **OCR 混淆表**：`OCR_ACCEPTABLE` 對應常見誤辨（如 `Z`↔`2`、`E`↔`F`）

### 4. 候選排序與去重

- **排序**：`score = 準確率 / √(width × height)`，愈小範圍且愈準愈佳
- **交集**：與最佳候選 IoU > 0.5 者取 bbox 交集作為精準區塊
- **去重**：IoU > 0.7 視為同一區塊，僅保留一個

### 5. 裁切重辨（Refined Run）

**前提**：已找到錨點且有候選。

1. **固定策略**：取第一名的 `strategy_name` 作為裁切後唯一預處理
2. **初始裁切**：bbox + 20px margin（不超出原圖）
3. **四方向迭代裁切**：
   - 每次從左/右/上/下裁掉 5%
   - 裁切時**反方向向外推 1px**（不超出原圖）
   - 四個方向試算分數，擇最佳繼續，直至無改善（最多 30 輪）
4. **座標回推**：
   - 裁切區塊左上角 `(c_left, c_top)` 對應原圖座標
   - 裁切圖內 bbox 相對座標 → 原圖：`orig_x = c_left + local_x`
5. **標註輸出**：在原圖上畫白框與 OCR 文字，輸出 `annotated_image_base64`

---

## 座標系統

- **原圖**：左上 (0,0)，x 向右、y 向下，單位像素
- **Tesseract**：y 軸向上，需轉換 `img_top = img_h - tesseract_top`
- **裁切圖內**：裁切區塊左上為 (0,0)，僅在裁切重辨階段使用

---

## 相關檔案

| 檔案 | 說明 |
|------|------|
| `/var/www/html/zenTable/scripts/ocr_test_analyze.py` | 主程式（可選；若未提供則 OCR 測試入口會回報「未啟用」） |
| `/var/www/html/zenTable/ocr_test_upload.php` | HTTP 上傳入口 |
| `index.html`（輸出校準 → OCR 辨識能力測試） | 前端上傳與結果顯示 |

---

## 版本紀錄

- 初始規格：多策略預處理、字數存量比對、裁切重辨（5% 迭代四方向）、原圖座標回推、白線標註
