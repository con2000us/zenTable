# 校準說明

Skill 設計為**獨立執行**，盡量不依賴額外套件。

## 運作方式

- **輸出校準區塊**：複製後貼至終端顯示、截圖，可手動量測或上傳分析。
- **截圖上傳**：可上傳截圖。若伺服器**未安裝** pytesseract、Pillow、Tesseract OCR，會回傳 wcwidth 預設值（ascii 1、cjk 2 等），請於右側表單**手動輸入**實際量測結果。
- **手動校準**：於右側「校準」區塊直接輸入 ascii、cjk、box、half_space、full_space 等數值。

## 可選：OCR 自動分析

若希望上傳截圖後自動分析，可於該環境另行安裝 Tesseract 與 Python 套件；未安裝時不影響 skill 使用，改採手動校準即可。
