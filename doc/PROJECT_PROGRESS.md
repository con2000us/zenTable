# ZenTable 專案進度表

依 doc 與程式現況整理。大項：輸入、JSON 調整、輸出、Theme 編輯、Fast API。

---

## 一、輸入 (Input)

**功能說明**：負責表格資料的來源與前處理。接受標準 JSON（`title` / `headers` / `rows` / `footer`）或「陣列 of 物件」，經正規化後供渲染使用；Table Detect 判斷使用者輸入是否需以表格呈現；前端 Data 面板提供標題/表尾、JSON 編輯、範例載入、分頁與排序欄位；若資料含 URL，可依規格同時輸出 ASCII 供對照。

| 細項 | 說明 | 狀態 | 備註 |
|------|------|------|------|
| JSON 格式 | title, headers, rows, footer 標準格式 | ✅ 完成 | SPECIFICATION §6.1；gentable_*.php 皆接受 |
| 陣列 of 物件正規化 | 物件陣列 → normalise_data → headers/rows | ✅ 完成 | zeble_render normalise_data、apply_sort_and_page |
| Table Detect | 判斷是否需要表格輸出 | ✅ 完成 | table_detect.py + table_detect_api.php；index 有 Table Detect 區塊 |
| 前端 Data 面板 | 標題/表尾、JSON 編輯、範例、分頁/排序 | ✅ 完成 | Data/Records 分頁、Page/每頁筆數/Sort/降序、dataJson、範例選單 |
| URL 偵測 | 資料含 URL 時可同時輸出 ascii | ✅ 規格已定 | SPECIFICATION §6.2、§7 |

---

## 二、JSON 調整

**功能說明**：負責在送入渲染前對「資料範圍」與「即時參數」的調整。包含分頁（每頁筆數、指定頁碼）、排序（依欄位升序/降序）；PIL / ASCII 的 `--params` 覆蓋（對齊、框線樣式、padding、校準等）；ASCII 的 `grid_config`（分隔線顯示與九宮格、儲存格格式）；以及進階 Render 選項（寬度、縮放、填滿方式、背景）的 CLI 與部分 UI。

| 細項 | 說明 | 狀態 | 備註 |
|------|------|------|------|
| 分頁 | --page, --per-page | ✅ 完成 | gentable_*.php 傳入；zeble_render 支援 |
| 排序 | --sort, --asc/--desc | ✅ 完成 | 同上；index 有 Sort by column、降序勾選 |
| PIL 自訂參數 | --params 覆蓋主題 | ✅ 完成 | cell_align, header_align, 顏色、字級等；多數有 UI |
| ASCII 自訂參數 | style, padding, align, header_align, grid_config | ✅ 完成 | gentable_ascii 傳入；zeble_render --params 支援 |
| ASCII 校準 | --calibration JSON | ✅ 完成 | 後端支援；index 有校準 JSON、輸出校準、PIL 藍圖 |
| ASCII grid_config | sep/null/false、九宮格、cells.5 | ✅ 文件與邏輯已定義 | RENDER_PARAMS §二；cells.5 僅 ASCII |
| 進階 Render | --width, --scale, --fill-width, --bg | ⚠️ 部分 | CLI 有；UI 在 Advanced 區 |

---

## 三、輸出 (Output)

**功能說明**：負責依選定模式產出最終檔案。三種模式為 ASCII（純文字 .txt）、PIL（.png）、CSS（Chrome 截圖 .png），並支援自動降級（css → pil → ascii）；可選透空背景。ASCII 模式提供除錯輸出（stage1/stage2/stage3_details）與藍圖 PIL 可視化（格線、座標、Regions、emoji 混合字體）；PIL 模式支援儲存格/表頭對齊與 emoji 用專用字型；進階尺寸（`--width`、`--scale`）可經 CLI 或 Advanced UI 傳入。

| 細項 | 說明 | 狀態 | 備註 |
|------|------|------|------|
| 三模式 | ascii / pil / css | ✅ 完成 | zeble_render 三分支；gentable_ascii/pil/css.php |
| 模式選擇與降級 | auto：css → pil → ascii | ✅ 完成 | SPECIFICATION §2 |
| 輸出格式 | .txt（ASCII）、.png（PIL/CSS） | ✅ 完成 | 依模式寫入 |
| 透空背景 | --transparent / --bg transparent | ✅ 完成 | CSS；index 有透空勾選 |
| ASCII 除錯輸出 | stage1/stage2/stage3_details、ascii_debug | ✅ 完成 | gentable_ascii 回傳；Backend 分頁 |
| ASCII 藍圖 PIL 可視化 | stage1 格線/座標/Regions、emoji 混合字體 | ✅ 完成 | stage1_pil_preview、unit_px；與 PIL 後端同字體 |
| PIL 對齊 | cell_align / header_align | ✅ 完成 | render_pil 已實作；params 與 UI 對應 |
| PIL/ASCII emoji | 混合字體（emoji + CJK） | ✅ 完成 | draw_text_with_mixed_fonts；blueprint 已套用 |
| 進階尺寸 | --width, --scale | ✅ CLI | UI 在 Advanced |

---

## 四、Theme 編輯

**功能說明**：負責主題的儲存、載入與視覺參數編輯。透過 `theme_api.php` 做主題列表、載入、儲存、刪除，每主題以 zip 存放 `template.json`；支援匯入單一 zip、匯出全部或單一主題。三種輸出模式對應不同主題結構（css / pil / text）與編輯方式：CSS 為選擇器或 Theme JSON、PIL 為 params 表、ASCII 為 style/padding/align 等；Quick Theme 可一鍵切換；進階選項（width、scale、fill-width、bg）在 Advanced 區塊中提供。

| 細項 | 說明 | 狀態 | 備註 |
|------|------|------|------|
| 主題列表/載入 | theme_api list, load | ✅ 完成 | 讀取專案 themes/ |
| 主題儲存/刪除 | save, delete（zip） | ✅ 完成 | 每主題一 zip，內含 template.json |
| 主題匯入/匯出 | import 單一 zip、export-all | ✅ 完成 | THEME_STRUCTURE；gentable_export 單一匯出 |
| 主題結構 | css/pil/text、template.json | ✅ 完成 | SPECIFICATION §3–4 |
| Quick Theme | 掃描 themes、一鍵選主題 | ✅ 完成 | index 主題下拉、Quick Theme |
| CSS 主題編輯 | 選擇器或 Theme JSON | ✅ 完成 | body, container, table, th, td 等 |
| PIL 主題編輯 | params 對應 UI | ✅ 完成 | 顏色、字級、padding、對齊、浮水印等 |
| font_family（PIL） | 自訂字型路徑 | ⚠️ 無 UI | whitelist 有；編輯頁無欄位 |
| ASCII 主題編輯 | style, padding, align, header_align | ✅ 完成 | 有欄位並傳後端 |
| 進階選項 UI | width, scale, fill-width, bg | ✅ 有 | 在 Advanced 區 |

---

## 五、Fast API

**功能說明**：負責以 HTTP / API 方式對外提供服務。目前實作為 PaddleOCR 的 FastAPI 服務（`/ocr`、`/health`），供辨識使用；前端可顯示 FastAPI 狀態，並透過 `fastapi_control.php` 啟動/停止、檢查依賴。專案內另有校準與渲染的薄包裝（`api/calibration_api`、`api/render_api`），供 ComfyUI / n8n 等整合；「整站改為單一 FastAPI 取代 PHP 呼叫 CLI」尚未實作，目前渲染仍由 PHP 呼叫 `zeble_render.py`。

| 細項 | 說明 | 狀態 | 備註 |
|------|------|------|------|
| PaddleOCR FastAPI | OCR 服務 /ocr、/health | ✅ 完成 | api/paddleocr_service.py（支援 PaddleOCR v3 輸出；建議 paddlepaddle==3.2.2） |
| 前端 FastAPI 狀態 | 執行中/已停止、Start/Stop | ✅ 完成 | index System、fastapiIndicator、fastapi_control.php |
| fastapi_control.php | 啟動/停止/檢查依賴 | ✅ 完成 | 依賴：fastapi, uvicorn, Pillow, numpy 等 |
| 模組 API（ComfyUI/n8n） | 校準/渲染薄包裝或 HTTP | ⚠️ 建議階段 | api/calibration_api、render_api；MODULE_API 文件 |
| 統一渲染 FastAPI | 整站以 FastAPI 取代 PHP 呼叫 CLI | ❌ 未實作 | 目前仍 PHP + zeble_render.py |

---

## 圖例

| 符號 | 意義 |
|------|------|
| ✅ 完成 | 已實作且與文件/UI 對應 |
| ⚠️ 部分 / 無 UI | 後端有、前端缺或僅部分暴露 |
| ❌ 未實作 | 尚未開發 |
