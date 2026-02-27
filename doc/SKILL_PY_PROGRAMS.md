# Skill Python 程式總覽

## 一、工作流中的主程式（被 API 呼叫）

### 1. zeble_render.py

| 項目 | 說明 |
|------|------|
| **呼叫者** | gentable_css.php、gentable_pil.php、gentable_ascii.php |
| **角色** | 主渲染程式，支援 CSS/PIL/ASCII 三種模式 |
| **輸入** | 1) `<input.json>` 路徑，2) `<output.png>` 路徑（ASCII 時可為 dummy.png） |
| **輸入格式** | 陣列 of 物件 `[{...},{...}]` 或 `{ headers, rows, title?, footer? }`；gentable 會寫入 `_theme`、自訂 `_params` |

| 參數 | 說明 | 由誰傳入 |
|------|------|----------|
| `--theme-name <名稱>` | 主題（dark, light, cyberpunk, glass...） | gentable_*.php |
| `--theme <路徑>` | 主題 JSON 檔案（覆蓋 theme-name） | CLI 手動 |
| `--force-css` | 強制 CSS + Chrome | gentable_css.php |
| `--force-pil` | 強制 PIL | gentable_pil.php |
| `--force-ascii` | 強制 ASCII | gentable_ascii.php |
| `--output-ascii <路徑>` | ASCII 輸出檔（搭配 --force-ascii） | gentable_ascii.php |
| `--transparent` | 透空背景 PNG（僅 CSS） | gentable_css.php（勾選時） |
| `--params <JSON>` | 自訂參數覆蓋 | gentable_pil.php（PIL 樣式欄位） |
| `--page N` | 第 N 頁 | gentable_*.php |
| `--sort <欄位>` | 排序欄位 | gentable_*.php |
| `--asc` | 升序 | gentable_*.php（預設） |
| `--desc` | 降序 | gentable_*.php（勾選時） |

| 輸出 | 說明 |
|------|------|
| **CSS/PIL 模式** | PNG 檔案（寫入 output 路徑） |
| **ASCII 模式** | .txt 檔案 或 stdout |
| **stdout** | 狀態訊息（✅ 已保存 / 錯誤） |

---

### 2. table_detect.py

| 項目 | 說明 |
|------|------|
| **呼叫者** | table_detect_api.php |
| **角色** | 分析使用者訊息，判斷是否需要表格輸出 |
| **輸入** | 訊息字串（stdin 或 `argv[1]`） |

| 參數 | 說明 |
|------|------|
| 無（純文字） | 訊息由 `sys.argv[1]` 或 stdin 讀入 |
| JSON payload（新） | 可傳 `{message, previous_message, has_image, previous_has_image}`，支援 `Zx` 優先序判斷 |

| 輸出 | 格式 | 說明 |
|------|------|------|
| **stdout** | JSON | 基本：`{ "needs_table": bool, "reason": str, "confidence": float }`；`Zx` 模式另含 `zx_mode/source_priority/selected_source/action` |

---

## 二、CLI / 輔助程式（非 API 呼叫）

### 3. zeble.py

| 項目 | 說明 |
|------|------|
| **呼叫者** | gentable.php（舊 API）、本機 CLI |
| **角色** | PIL 渲染，內建 8 主題，不讀 themes/ 目錄 |
| **輸入** | `<input.json>`、`<output.png>` |

| 參數 | 說明 |
|------|------|
| `--dark` | 深色主題 |
| `--light` | 淺色主題 |
| `--cyberpunk` | 賽博龐克 |
| `--forest` | 森林 |
| `--ocean` | 海洋 |
| `--sunset` | 日落 |
| `--rose` | 玫瑰 |
| `--midnight` | 午夜 |
| `--page N` | 第 N 頁 |
| `--sort <欄位>` | 排序 |
| `--asc` / `--desc` | 升序 / 降序 |

| 輸出 | 說明 |
|------|------|
| PNG 檔案 | 表格圖片 |
| JSON 內 `bg_image`、`border_image` | 可指定背景圖、邊框圖 |

---

### 4. zentable_render.py

| 項目 | 說明 |
|------|------|
| **呼叫者** | 無（獨立工具） |
| **角色** | 另套渲染引擎，argparse、CSS 子集、PIL fallback |
| **輸入** | `-t` 範本、`-d` 資料、`-o` 輸出 |

| 參數 | 說明 |
|------|------|
| `-t, --template` | 範本檔案或內聯 CSS |
| `-d, --data` | 資料 JSON 檔案或內聯 |
| `-o, --output` | 輸出 PNG |
| `-f, --force-pil` | 強制 PIL |
| `-e, --env` | 環境 linux/macos/windows/auto |
| `-c, --chrome` | Chrome 路徑 |
| `-v, --verbose` | 詳細輸出 |

| 輸出 | 說明 |
|------|------|
| PNG 檔案 | 表格圖片 |

---

### 5. zeble_interactive.py

| 項目 | 說明 |
|------|------|
| **呼叫者** | 無（測試工具） |
| **角色** | 互動式測試各主題、呼叫 zeble.py |
| **輸入** | 無（內建範例） |
| **輸出** | 產出 test_*.json、test_*.png |

---

### 6. smart_table_output.py

| 項目 | 說明 |
|------|------|
| **呼叫者** | OpenClaw / Agent（若整合） |
| **角色** | 判斷輸出圖片或文字、載入偏好設定 |
| **輸入** | 無 CLI，函式 `should_use_image()` 等 |
| **輸出** | 布林或偏好設定 |

---

## 三、工具腳本（非工作流核心）

| 程式 | 用途 |
|------|------|
| gen_test_data.py | 產生 rich_test_data.json 測試資料 |
| reproduce_issue.py | 重現特定 bug 的測試腳本 |
| update_discord_agents.py | Discord Agent 更新（非表格） |

---

## 四、工作流總覽

```
[使用者] → index.html / zeble_test.html
              │
              ├─ theme_api.php ────────────→ themes/ 目錄（讀取，非 Python）
              │
              ├─ table_detect_api.php ─────→ table_detect.py
              │                                  │
              │                                  └→ stdout: JSON { needs_table, reason, confidence }
              │
              ├─ gentable_css.php ──────────→ zentable_renderer.py --force-css --theme-name X [--transparent]
              │                                  └→ PNG
              │
              ├─ gentable_pil.php ───────────→ zentable_renderer.py --force-pil --theme-name X [--params {...}] [--page] [--sort] [--asc|--desc]
              │                                  └→ PNG
              │
              └─ gentable_ascii.php ────────→ zentable_renderer.py --force-ascii --output-ascii <path> [--page] [--sort]
                                                 └→ TXT

[舊 API]  gentable.php ───────────────────→ zeble.py --dark 等
                                              └→ PNG
```
