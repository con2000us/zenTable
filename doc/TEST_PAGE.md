# Zeble Test Page Specification

## 🌐 測試頁面固定網址

**測試頁面位置**: `http://YOUR_HOST/zenTable/`

**本地開發位置**: `/var/www/html/zenTable/index.html`

---

## 📌 創建此頁面的理解

測試頁的存在，是為了**在與 skill 上線相同條件下**驗證渲染與主題行為，而不是用自帶資料模擬。

- **為何不能全是自帶：** 若主題、程式、資源都寫死在頁面或專案內，就無法驗證「實際 skill 目錄」在線上的表現（themes、zeble_render.py、字型、asset 等）。因此測試頁應**盡量調用 skill 目錄的資源**（程式、themes、必要 asset），僅在 fallback 時才用專案自帶，並在文件中註明。這樣才能測到 skill 上線的實際狀況。
- **測試頁不得自帶與 skill 重複的程序：** 凡 skill 會有的程式（渲染腳本、table_detect、主題檔等），測試頁**不得**以自帶為優先，否則會混淆「測到的是 skill 還是專案」。**例外**：僅限「skill 不會有的」邏輯可自帶，例如**前端即時預渲染**（瀏覽器內用 JS + 載入的 theme 樣式畫出預覽），因為 skill 端沒有網頁與 JS 執行環境。
- **未來擴充：** 此頁將具備：
  - **調試功能**：例如錯誤重現、請求/回應檢視、各模式除錯開關。
  - **輸出 theme 包功能**：將目前選用/編輯的主題打包成符合 skill 目錄結構的 ZIP（或目錄），解壓到 `skills/zeble/themes/` 即可使用，以利「測試完就反饋回 skill」。

測試頁開發進度已超前現有 skill 的程序與資源；整合與反更新規劃見下方「整合與反更新規劃」及「相關檔案與資源清單」。

- **skill 與 test page 重合部分，以 test page 為準已反更新回 skill：** 目前 skill 與測試頁的重疊部分（程式、主題、規則）已將**測試頁較完整的版本**反更新回 skill，以 skill 為單一來源；測試頁改為**調用 skill** 的程式與資源，不再以自帶為優先。
- **後續 bug 或新需求：直接改 skill。** 若有 bug 或要新增功能，**一律在 skill 目錄內修改程式或資源**（如 `zeble_render.py`、`themes/`），不要先在測試頁或專案 `doc/` 改完再同步。改完後測試頁因已調用 skill，自然會測到變更；必要時再將 skill 的變更同步回專案文件或 fallback 用副本，以利本機無 skill 時仍可開發。

---

## 🎯 測試頁面目的 (Purpose)

本測試頁面 (`index.html` 為主；`doc/zeble_test.html`、`doc/zeble_test_v2.html` 為舊版) 旨在提供一個**跨環境渲染驗證平台**，用於確保 Zeble 在不同運行環境下都能產出預期的結果。

由於 Zeble 支援多種渲染後端（CSS/Chrome, PIL/Python, ASCII），且各環境對字體、Emoji 和排版的支援度不同，因此需要一個統一的測試基準；測試時應以 **skill 目錄的程式與 themes** 為主要調用來源，才能反映上線狀況。

---

## 🧪 驗證目標 (Validation Goals)

### 1. 跨環境渲染一致性
- **CSS Mode (Chrome Headless)**：
  - 驗證 **彩色 Emoji** 顯示是否正確（不應出現豆腐塊或黑白符號）。
  - 驗證複雜 CSS 特效（如毛玻璃 `backdrop-filter`、漸層背景）是否如預期渲染。
  - 檢查 Web Font（如 Noto Sans CJK）載入是否正常。
  
- **PIL Mode (Python Fallback)**：
  - 驗證在 **無 Chrome 環境** 下的降級效果。
  - 確保 Emoji 即使退化為單色（Symbola 字體），仍能保持可辨識度與對齊。
  - 檢查基本排版（表格線條、背景色）是否與 CSS 版本維持視覺一致性。

- **ASCII Mode (Text Only)**：
  - 驗證在 **純文字環境**（Logs, CLI）的可讀性。
  - 確保表格對齊與寬度計算正確。

### 2. 主題與對比度 (Theme & Contrast)
- **深色模式 (Dark Theme)**：
  - 嚴格檢查 **文字/背景對比度**（WCAG AA 標準），確保在深色背景下文字清晰可讀。
  - 驗證 Highlight 顏色（如狀態燈、強調文字）的視覺效果。
  
- **淺色模式 (Light Theme)**：
  - 檢查邊框與分隔線的清晰度。

### 3. 資料多樣性 (Data Diversity)
- **混合內容**：測試中英文混排、特殊符號、長字串自動換行的處理。
- **邊界情況**：測試空值、極長欄位、大量的 Emoji 連續排列。
- **格式化**：驗證數值、百分比、狀態標籤（Status Badge）的自動格式化邏輯。

---

## 📐 Layout & Feature Requirements (v2)

### 1. 輸出模式選擇 (Output Mode Selection)
- **優先選擇**：介面首要步驟需先選擇輸出模式。
- **支援模式**：CSS (Chrome), PIL (Python), ASCII (Text)。
- **連動顯示**：選擇模式後，下方的樣式編輯區應自動切換為該模式專屬的編輯介面。

### 2. 預設資源 (Default Resources)
- **預設主題**：應從 `theme_api.php` 取得主題列表（即 skill/專案 `themes/` 目錄），**不得僅依賴頁內自帶 defaultThemes**，否則無法測試 skill 上線狀況。Quick Theme 顯示的即為該目錄下之主題。
- **範例數據**：提供多種場景的範例表格：
  - 🖥️ Servers (6 筆資料)
  - 📊 Project Status (5 筆資料)
  - 💰 Pricing Plans (4 筆資料)
  - 📦 Inventory (5 筆資料)
  - ⚡ DevOps Services (5 筆資料)
  - 😀 Emoji Test (6 個分類)

### 3. 數據編輯 (Data Editor)
- **JSON 編輯器**：選擇範例後，顯示表格資料的 JSON 內容。
- **自由編輯**：使用者可直接修改 JSON 結構與數值。

### 4. 樣式編輯器 (Style Editors by Mode)
根據選擇的輸出模式，顯示不同的編輯介面：

- **CSS Mode**：
  - **JSON 編輯**：提供完整 Theme JSON 編輯器（結構同 `template.json`）。
  - **高度自訂**：支援自定義 CSS 樣式、HTML 模板結構。
  - **從 themes/css/ 載入**：即時從 `theme_api.php` 載入 template.json

- **PIL Mode**：
  - **參數列表**：列出所有 `zeble.py` 實作的可調參數（如 `font_size`, `bg_color`, `padding`, `row_height` 等）。
  - **數值調整**：提供輸入框或滑桿直接修改數值。
  - **從 themes/pil/ 載入**：載入對應的 PIL template.json

- **ASCII Mode**：
  - **參數列表**：列出 ASCII 相關參數（如 `border_style`, `padding`, `align`）。

### 5. 雙重預覽 (Dual Preview)
- **前端模擬**：瀏覽器端即時渲染的預覽效果（使用從 API 載入的 theme template）。
- **後端實測**：呼叫實際後端腳本（PHP -> Python）產生的真實圖片/文字。
- **對照驗證**：方便比對前後端渲染差異，確保一致性。

### 6. 主題打包與匯出 (Theme Export)
- **ZIP 打包**：將使用者當前設定好的 Theme JSON 及相關資源（如背景圖、字型等）打包成 ZIP 檔。
- **標準結構**：ZIP 內容結構需符合 Skill 的 `themes/` 目錄規範。
- **即刻使用**：使用者下載後，解壓至 `skills/zeble/themes/` 目錄下即可直接被 `zeble.py` 調用。

---

## 🛠️ 使用方式

### 1. 部署測試頁面
測試頁面已部署至 `/var/www/html/zenTable/`。

### 2. 後端 API 清單

| API | 網址 | 說明 |
|-----|------|------|
| 主題列表 | `/zenTable/theme_api.php?action=list&mode=css` | 列出所有 CSS 主題 |
| 載入主題 | `/zenTable/theme_api.php?action=load&mode=css&theme=dark` | 載入指定主題的 template.json |
| CSS 渲染 | `/zenTable/gentable_css.php` | POST data, theme, mode |
| PIL 渲染 | `/zenTable/gentable_pil.php` | POST data, theme, mode + 參數 |
| ASCII 渲染 | `/zenTable/gentable_ascii.php` | POST data, theme, mode |

### 3. 執行渲染測試
- **PIL 測試**：
  ```bash
  python3 zentable.py rich_test_data.json output_pil.png --dark
  ```
- **CSS 測試**：
  ```bash
  python3 zentable_renderer.py rich_test_data.json output_css.png --force-css --theme-name dark
  ```

### 4. 視覺比對
在網頁上切換不同模式的輸出圖，確認：
- [ ] CSS 版 Emoji 是否為彩色？
- [ ] PIL 版文字是否清晰？
- [ ] 森林主題顏色是否正確（綠色背景）？
- [ ] 前端預覽和後端渲染是否一致？

---

## 📁 檔案結構

```
/var/www/html/zenTable/
├── index.html              # 測試頁面主檔案
├── theme_api.php           # 主題 API（載入 themes/ 目錄）
├── gentable_css.php        # CSS 渲染 API
├── gentable_pil.php        # PIL 渲染 API
├── gentable_ascii.php      # ASCII 渲染 API
├── gentable_export.php     # 主題匯出 API
├── table_detect_api.php      # 表格偵測 API
├── themes/                   # 主題（css/pil/text）
└── scripts/                  # Python 入口（zeble_render.py、table_detect.py）
```

---

## ✅ 開發進度 (2026-02-11)

### 已完成
- [x] 建立 theme_api.php 從 themes/ 目錄動態載入 template.json
- [x] 建立 CSS 主題：dark, light, forest, ocean, sunset, rose, midnight
- [x] 建立 PIL 主題：dark, light, forest, ocean, sunset, rose, midnight
- [x] 更新前端從 theme_api.php 動態載入 theme 列表
- [x] 更新前端預覽使用實際載入的 template styles
- [x] 更新後端 zentable_renderer.py 支援從 themes/ 目錄載入
- [x] 擴充範例資料至 6 個場景
- [x] 修復 PIL emoji 彩色圓形替換（(綠), (紅) 等）
- [x] 新增 PIL emoji 字體自動選擇（NotoColorEmoji 優先）
- [x] 修復 CSS backend 主題映射（forest 等）

### 已完成（本輪）
- [x] 實現 theme 編輯後儲存到 themes/ 目錄（theme_api.php action=save）
- [x] 實現 theme ZIP 匯出功能（多模式、結構為 mode/themeName/template.json）
- [x] 新增更多 ASCII 主題（text 模式靜態 simple / grid / double）
- [x] 實現 table_detect.py 整合展示（table_detect_api.php + 測試頁 Table Detect 區塊）

---

## 🔧 技術細節

### Theme 載入流程
```
前端網頁
    ↓
AJAX 請求 theme_api.php?action=list
    ↓
PHP 讀取 /var/www/html/zenTable/themes/css/
    ↓
回傳 JSON: {id, name, description, version, tags}
    ↓
前端選擇 theme
    ↓
AJAX 請求 theme_api.php?action=load&theme=dark
    ↓
回傳完整的 template.json + frontend 格式
    ↓
前端預覽使用 template.styles 渲染
    ↓
後端渲染時也從相同路徑載入 template
```

### CSS 與 PIL Theme 對應
- 前端切換 mode 時，會自動載入對應的 theme 類型
- CSS Mode → themes/css/{theme}/template.json
- PIL Mode → themes/pil/{theme}/template.json
- 確保前後端使用相同的配色設定

### 程序工作流與調用關係

下圖為測試頁從使用者操作到後端執行的流程，以及**各步驟實際調用的程式／資源**。凡與 skill 重複的程式必須以「調用 skill」為優先，僅 skill 不會有的（如前端預渲染）才允許測試頁自帶。

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  使用者                                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  測試頁 (index.html)                                                          │
│  • 範例資料：頁內自帶 JSON（僅供輸入，不影響「誰來渲染」）                        │
│  • 前端預覽：自帶 OK（skill 沒有瀏覽器，無法做即時預渲染）                        │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ├── GET theme_api.php?action=list&mode=css|pil|text
         │         │
         │         ▼
         │   theme_api.php 讀取 themes 目錄
         │         │
│         └── 固定：專案 themes/（本專案不再依賴 /opt skill）
         │
         ├── GET theme_api.php?action=load&theme=xxx
         │         └── 同上，template 來自 skill（或 fallback）
         │
         ├── POST gentable_css.php | gentable_pil.php | gentable_ascii.php
         │         │
         │         ▼
         │   渲染 API 執行 Python 腳本
         │         │
│         └── 固定：scripts/zeble_render.py
         │         │
         │         ▼
         │   zentable_renderer.py 執行時讀取 theme
│         └── 固定讀取專案 themes/
         │
         ├── POST table_detect_api.php
         │         │
         │         ▼
         │   目前：優先 doc/table_detect.py → 再 skill table_detect.py
         │   應改：優先 skill table_detect.py → fallback doc（若 skill 有則調用 skill）
         │
         ├── POST gentable_export.php
         │         └── 純 PHP 組 ZIP，不執行 skill 程式 → 自帶 OK（測試頁專用工具）
         │
         └── POST theme_api.php?action=save
                   └── 寫入 themes 目錄（應寫入 skill 目錄或明定寫入位置，避免與 skill 不同步）
```

**總結：**
- **主題列表／載入**：調用 skill（theme_api 讀 skill themes，fallback 專案）。
- **前端預覽**：測試頁自帶（skill 沒有前端）。
- **CSS/PIL/ASCII 渲染**：應調用 skill 的 zeble_render.py，不應優先自帶 doc 版。
- **Table Detect**：應調用 skill 的 table_detect.py（若 skill 有）；無則 fallback 專案。
- **Theme 匯出 ZIP**：測試頁自帶（PHP 打包，skill 不需此程式）。

---

### 依序檢視：調用 skill vs 測試頁自帶

以下依流程逐項標註**應為「調用 skill」**或**可「給測試網頁自帶」**，避免混淆。

| # | 項目 | 目前行為 | 應為 | 說明 |
|---|------|----------|------|------|
| 1 | 主題列表 (Quick Theme) | theme_api 讀 skill → fallback 專案 themes | **調用 skill** | 列表來源必須是 skill 的 themes/，才能測到上線有哪些主題。 |
| 2 | 主題內容 (template.json) | theme_api 讀 skill → fallback 專案 | **調用 skill** | 同上，載入的 template 應來自 skill。 |
| 3 | 前端即時預覽 (Frontend Sim) | 頁面 JS 用載入的 styles 渲染 HTML | **測試頁自帶** | skill 沒有瀏覽器與 JS，此為測試頁獨有，自帶合理。 |
| 4 | 範例資料 (Example Data) | 頁內 JSON 寫死 | **測試頁自帶** | 僅供輸入用，不影響「誰來渲染」；skill 不需這批範例。 |
| 5 | CSS 渲染 (gentable_css.php → py) | 優先 doc/zeble_render.py，再 skill | **調用 skill** | 應改為優先 skill 的 zeble_render.py，doc 僅 fallback。 |
| 6 | PIL 渲染 (gentable_pil.php → py) | 同上，doc 優先 | **調用 skill** | 同上，執行 skill 的腳本。 |
| 7 | ASCII 渲染 (gentable_ascii.php → py) | 同上，doc 優先 | **調用 skill** | 同上，執行 skill 的腳本。 |
| 8 | Table Detect (table_detect_api → py) | 優先 doc/table_detect.py，再 skill | **調用 skill**（若 skill 有） | 若 skill 有 table_detect.py 則優先調用；無則 fallback 專案。 |
| 9 | Theme 匯出 ZIP (gentable_export.php) | 純 PHP 打包 | **測試頁自帶** | 測試頁工具，產出給 skill 用；skill 端不需此程式。 |
| 10 | Theme 儲存 (theme_api save) | 寫入 theme_api 使用的 themesDir | **依 themesDir 而定** | 若 themesDir 為 skill，則寫入 skill；避免寫入專案而 skill 看不到。 |

**原則重申：** 測試頁不能有自帶的、與 skill 重複的**程序**（如 zeble_render.py、table_detect.py）。除非是 skill 不會有的（如前端預渲染、匯出 ZIP 的 PHP），否則一律以**調用 skill** 為準，才不會混淆。

---

## 🔄 整合與反更新規劃

測試頁開發進度已超前現有 skill 的程序與資源。**目前重合部分已以 test page 較完整版本反更新回 skill，測試頁改為以調用 skill 為主。** 以下為當時的整合要點；後續維護請依「後續維護原則」操作。

### 後續維護原則（請遵守）

- **單一真相來源為 skill：** 與 skill 重疊的程式與資源，以 skill 目錄為準；測試頁只負責調用，不保留一份「較新」的自帶版。
- **bug 或新需求：直接改 skill。** 修 bug 或加功能時，**直接修改 skill 目錄內的程式或資源**（如 `zeble_render.py`、`themes/css/xxx/template.json`、`table_detect.py` 等），不要先在測試頁或專案 `doc/` 改。改完後測試頁因會調用 skill，重新操作即可驗證。
- 若本機沒有 skill 目錄、僅能改專案時：可在專案內修改，但**完成後須將變更同步回 skill**，並確保測試環境改為優先調用 skill，避免長期兩邊不一致。

### 該整合的（單一來源）
- **主題**：所有測試頁（含 `doc/zeble_test.html`、`doc/zeble_test_v2.html`）改為經 `theme_api.php` 取得主題，不再以頁內 `defaultThemes` 為主要來源。
- **渲染**：一律經 `gentable_css.php` / `gentable_pil.php` / `gentable_ascii.php`，由 API 決定執行哪支腳本、讀哪個 themes 目錄。

### 該重新調用 skill 的（以 skill 為真）
- **Py 程式**：後端 API 改為**優先執行 skill 目錄**的 `zeble_render.py`（及 pil/ascii 對應腳本），專案 `doc/zeble_render.py` 僅作 fallback（本機無 skill 時才用），這樣測試頁跑出來的就是 skill 上線時會用的程式。
- **Themes / Asset**：`theme_api.php` 與渲染流程已優先讀 skill 的 themes；維持此邏輯。若 skill 目錄有指定字型或圖檔，渲染時應優先使用 skill 路徑，文件註明 fallback 順序。

### 該反更新回 skill 的（專案較新）
- **主題規則與結構**：`doc/THEME_STRUCTURE.md` 的「全部 theme 放各自資料夾」規則與目錄結構，同步至 skill 端說明或 README；若 skill 仍有扁平 theme，改為資料夾結構並遷移。
- **新主題**：專案內 7 個 CSS 主題（neon_cyber, sunset_layers, card_3d, minimal_ink, forest_soft, glass, gradient_modern）複製到 skill 的 `themes/css/`，供線上與測試頁一致。
- **zeble_render.py**：`doc/zeble_render.py` 的修正（選擇器、theme 載入、多模式等）合併回 skill 的 `zeble_render.py`，之後測試頁改為優先調用 skill 版即可測到上線狀況。
- **Theme 包輸出**：測試頁未來「輸出 theme 包」產物，結構對齊 skill 的 `themes/`，解壓至 skill 即完成反更新。

---

## 📂 相關檔案與資源清單

以下列出與測試頁、skill 上線相關的檔案與資源，並標註**建議處理方式**（整合 / 重新調用 skill / 反更新回 skill）。實際執行時依「整合與反更新規劃」一節操作。

### 測試頁與入口
| 檔案 | 說明 | 建議處理 |
|------|------|----------|
| `index.html` | 主測試頁，已有 theme_api、三模式、後端 Render | 維持；確保主題與渲染皆調用 skill/API，勿依賴自帶 |
| `doc/zeble_test.html` | 舊版測試頁，主題為頁內 defaultThemes | **整合**：改為呼叫 theme_api 取得主題；後端渲染改為呼叫 gentable_*.php |
| `doc/zeble_test_v2.html` | 舊版測試面板，主題為頁內 defaultThemes | **整合**：同上 |
| `index_v2.html` | 根目錄另一版入口 | 視是否保留；若保留則同 doc 測試頁改為調用 API |

### 後端 API（PHP）
| 檔案 | 說明 | 建議處理 |
|------|------|----------|
| `theme_api.php` | 主題列表/載入/儲存；優先讀 skill themes | 維持；已符合「調用 skill」 |
| `gentable_css.php` | CSS 渲染；目前優先用 doc/zentable_renderer.py | **重新調用 skill**：改為優先執行 skill 目錄的 zeble_render.py，doc 版 fallback |
| `gentable_pil.php` | PIL 渲染 | 改為優先執行 skill 目錄對應腳本，doc 版 fallback |
| `gentable_ascii.php` | ASCII 渲染 | 同上 |
| `gentable_export.php` | 主題 ZIP 匯出 | 維持；產物結構對齊 skill themes/，即反更新用 |
| `table_detect_api.php` | 表格偵測 | 視 skill 是否含 table_detect；若無則保留專案版 |

### Python 程式
| 檔案 | 說明 | 建議處理 |
|------|------|----------|
| `doc/zeble_render.py` | 專案版 CSS/PIL/ASCII 主腳本，已含選擇器與 theme 載入修正 | **反更新回 skill**：將變更合併至 skill 的 zeble_render.py；之後 API 改為優先調用 skill 版 |
| `doc/zeble.py` | 專案版（若與 skill 不同） | 若有修正，合併回 skill 對應腳本 |
| `doc/table_detect.py` | 表格偵測 | 若 skill 需此功能，複製至 skill 並由 table_detect_api 調用 skill 版 |
| `doc/zentable_render.py` | 其他渲染輔助 | 視 skill 是否使用；必要時反更新 |

### 主題資源（themes/）
| 路徑 | 說明 | 建議處理 |
|------|------|----------|
| `themes/css/*/template.json` | 專案內 7 個 CSS 主題（glass, gradient_modern, neon_cyber, sunset_layers, card_3d, minimal_ink, forest_soft） | **反更新回 skill**：複製至 skill 的 `themes/css/`，使 Quick Theme 與後端從 skill 讀到同一批 |
| `themes/pil/` | 專案若有 PIL 主題 | 同步至 skill 的 themes/pil/ |
| `themes/text/` | 專案若有 ASCII 主題 | 同步至 skill 的 themes/text/ |

### 文件
| 檔案 | 說明 | 建議處理 |
|------|------|----------|
| `doc/TEST_PAGE.md` | 本文件 | 已更新創建理解、整合與反更新規劃、檔案清單 |
| `doc/THEME_STRUCTURE.md` | 主題目錄規則 | **反更新回 skill**：規則與結構同步至 skill 端文件 |
| `doc/THEME_SOURCES.md` | 主題來源說明 | 可複製或連結至 skill 端 |

### 其他資源（範例資料、產物）
| 檔案 | 說明 | 建議處理 |
|------|------|----------|
| `doc/rich_test_data.json`、`example_table*.json` | 範例/測試資料 | 保留於專案；skill 若有需要可複製一份 |
| `gentable_export.php` 產出的 ZIP | theme 包 | 解壓至 skill 的 themes/ 即完成反更新，無需額外檔案列表 |
