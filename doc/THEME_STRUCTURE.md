# 主題目錄結構與規則

## 規則：每個 theme 以 theme_name.zip 放置

**每個主題以一個 zip 檔案儲存，檔名即為主題 ID。**

- ✅ 正確：`themes/<模式>/<主題_id>.zip`
- 每個 zip 內含 `template.json`（置於根目錄）

過渡期仍支援舊格式 `themes/<模式>/<主題_id>/template.json`（資料夾）。

---

## 目錄結構

```
themes/
├── css/                          # CSS 輸出模式
│   ├── glass.zip
│   ├── gradient_modern.zip
│   ├── neon_cyber.zip
│   └── ...
├── pil/                          # PIL 輸出模式
│   ├── <theme_id>.zip
│   └── ...
└── text/                         # ASCII 輸出模式
    ├── <theme_id>.zip
    └── ...
```

- **模式**：`css`、`pil`、`text` 三種，對應三種輸出方式。
- **主題 ID**：zip 檔名（不含 .zip）即為主題 ID，用於 API 的 `theme` 參數與 Quick Theme 選項。
- **zip 內容**：根目錄必須有 `template.json`。CSS 主題可額外包含 `images/` 等 assets。

---

## CSS 主題 assets 與相對路徑

CSS 主題的 `styles` 中可使用 `url('images/bg.png')` 等相對路徑。zentable_render 會將 zip 解壓至快取目錄，HTML 寫入同目錄，使相對路徑正確解析。

- **zip 結構範例**：`template.json`、`images/logo.png`、`images/bg.png`
- **快取**：解壓至 `/tmp/zentable_themes/{mode}_{theme_name}/`（可透過 `ZENTABLE_CACHE_DIR` 覆寫）
- **快取失效**：依 zip 的 `mtime` 判斷；zip 更新後下次渲染會重新解壓

---

## template.json 必要欄位（依模式）

| 模式 | 必要欄位 | 說明 |
|------|----------|------|
| **css** | `name`, `styles` | `name` 為顯示名稱；`styles` 為選擇器 → CSS 字串的物件 |
| **pil** | `name`, `params` | `params` 含 bg_color, header_bg, text_color 等 |
| **text** | `name`, `params` | `params` 含 style, padding, align 等 |

建議一併填寫：`type`（與模式一致）、`description`、`version`、`theme_color`（Quick Theme 圓點色）、`tags`。

---

## 新增主題步驟

1. 在 index.html 使用「Add」建立新主題，或透過 `theme_api.php` action=save 寫入。
2. 新主題會儲存為 `themes/<模式>/<主題_id>.zip`。
3. Quick Theme 會自動掃描並列出新主題。

---

## ZIP 匯入匯出

### 匯出全部

- **API**：`theme_api.php?action=export-all`（GET）
- **結果**：下載 `themes_full_YYYYMMDDHHMMSS.zip`，內含 `css/*.zip`、`pil/*.zip`、`text/*.zip`（每個 zip 為一個 theme）。
- **用途**：備份、分發、版本控制。

### 匯入 ZIP

- **API**：`theme_api.php`（POST，`action=import`，上傳欄位 `zip_file`，可選 `mode`）
- **格式**：單一 theme 的 zip，內含 `template.json`（根目錄或 `mode/theme_name/template.json`）。
- **行為**：驗證 template.json → 寫入 `themes/<mode>/<theme_name>.zip`（覆蓋同名）。
- **回應**：`{ success, imported, theme, mode }`。

### 單一主題匯出

- `gentable_export.php`：POST 傳入 `theme_json`、`theme_name`、`mode`，回傳單一主題 ZIP 下載連結（legacy 工具；主流程以 `theme_api.php` 為主）。
- 產出 zip 內含根目錄 `template.json`，可匯入或手動放置至 `themes/<mode>/<theme_name>.zip`。

### 儲存位置說明

- `theme_api` 的 `$themesDir` 固定為本專案 `themes/`（`/var/www/html/zenTable/themes/`）
- 匯入/儲存皆寫入專案 `themes/`（需確保 web server 對 `themes/<mode>/` 有寫入權限）

---

## 既有主題遷移

若原本使用資料夾格式（`themes/<mode>/<theme_id>/template.json`），可執行：

```bash
php migrate_themes_to_zip.php
```

加上 `--delete` 可在轉換後刪除原有資料夾。

---

## 相關檔案

- 主題列表與載入：`theme_api.php`（`listThemes`、`loadThemeTemplate`）
- 主題匯入匯出：`theme_api.php`（`export-all`、`import`、`delete`）
- 單一主題匯出：`gentable_export.php`
- 主題遷移：`migrate_themes_to_zip.php`
- 主題來源說明與歷史：`doc/THEME_SOURCES.md`
