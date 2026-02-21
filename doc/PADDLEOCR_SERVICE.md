# PaddleOCR FastAPI 服務

將 PaddleOCR 以單例常駐方式跑成 HTTP API，供 ZenTable 校準、LangFlow、n8n 等呼叫，無需每次載入模型。

## 安裝

在專案根目錄（zenTable）下：

```bash
pip install -r requirements-ocr.txt
```

或僅安裝必要套件：

```bash
pip install fastapi uvicorn "paddleocr>=2.0.1" "paddlepaddle" python-multipart
```

- **CPU**：上述即可。
- **GPU**：請依 [PaddlePaddle 官方](https://www.paddlepaddle.org.cn/install/quick) 安裝對應 CUDA 版 `paddlepaddle-gpu`，並設 `USE_GPU=true`。

## 啟動

```bash
# 專案根目錄
python -m api.paddleocr_service
```

或指定 host/port：

```bash
OCR_HOST=0.0.0.0 OCR_PORT=8000 python -m api.paddleocr_service
```

或使用 uvicorn：

```bash
uvicorn api.paddleocr_service:app --host 0.0.0.0 --port 8000
```

預設監聽 `http://0.0.0.0:8000`。

## 環境變數

| 變數 | 說明 | 預設 |
|------|------|------|
| `OCR_LANG` | 語言（ch / en 等） | `ch` |
| `USE_GPU` | 是否使用 GPU（true/false） | `false` |
| `USE_ANGLE_CLS` | 是否啟用方向分類 | `true` |
| `OCR_HOST` | 綁定 host | `0.0.0.0` |
| `OCR_PORT` | 綁定 port | `8000` |

## API 端點

### GET /health

健康檢查。回傳 `{"status":"ok","ocr":"ready"}` 表示模型已載入。

### POST /ocr

上傳一張圖片（`multipart/form-data`，欄位名 `image`），回傳辨識結果。

- **Content-Type**：`multipart/form-data`，欄位：`image`（檔案）
- **回傳**：`{ "success": true, "rows": [ { "text", "left", "top", "width", "height" }, ... ] }`  
  格式與 `calibrate_analyze.run_ocr_full()` 相容，可供 `find_block_bounds`、校準流程使用。

### POST /ocr/base64

以 JSON body 傳入 base64 圖片。

- **Body**：`{ "image_base64": "..." }`
- **回傳**：同上。

## 與 ZenTable 校準整合

- 校準流程目前使用 `calibrate_analyze.run_ocr_full()`（Tesseract）。若改為「呼叫 OCR 服務」，可：
  - 在 `calibrate_analyze` 中新增後端選項（例如 `--ocr paddleocr-api`），對圖片呼叫 `POST /ocr`，將回傳的 `rows` 當成 `run_ocr_full` 的結果繼續跑 `find_block_bounds`、`analyze_widths`。
  - 或由 LangFlow / n8n 先呼叫本服務取得 `rows`，再呼叫 ZenTable 校準 API（傳入已有 OCR 結果或圖片路徑，依你現有 API 設計而定）。

## 依賴與 Skill

- 本服務**只依賴**：FastAPI、PaddleOCR、PaddlePaddle、Pillow、numpy。
- 呼叫端（LangFlow 節點、n8n、自訂 skill）只需依賴 **HTTP 客戶端**（如 `requests`），依賴清單短、易於封裝成 skill。

## PaddleOCR-VL（可選）

若需文件解析、表格結構等進階能力，可改用 PaddleOCR-VL（需 GPU、安裝 `paddleocr[doc-parser]`）。目前本服務使用標準 PaddleOCR；若要改為 VL 版，需替換 lifespan 內的模型載入與 `ocr()` 呼叫邏輯，並依 [PaddleOCR-VL 文件](https://paddlepaddle.github.io/PaddleOCR/latest/en/version3.x/pipeline_usage/PaddleOCR-VL.html) 調整回傳格式對應。
