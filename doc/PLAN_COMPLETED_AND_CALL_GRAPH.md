# 計畫完成列表與調用關係圖

## 一、完成項目清單

| # | 項目 | 說明 |
|---|------|------|
| 1 | zeble_render.py 支援 --page, --sort, --asc, --desc，並可接受陣列輸入 | 在 zeble_render.py 新增 ROWS_PER_PAGE、normalise_data()（陣列 of 物件 → `{headers, rows}`）、apply_sort_and_page()；CLI 解析 --page、--sort、--asc、--desc；load_json 之後先 normalise 再 sort/page，再送入 CSS/PIL/ASCII 三種渲染。 |
| 2 | 主題 cyberpunk 與文件一致 | 新增 `themes/css/cyberpunk/template.json`（skill 與專案皆有），配色對齊 SKILL.md 所述 cyberpunk 風格。 |
| 3 | 更新 SKILL.md 反映 zeble_render.py、themes/、雙入口 | 在 skill 與專案 doc/SKILL.md 中補上：zeble_render.py 為對外主入口（支援 CSS/PIL/ASCII、--theme-name、--transparent、--page、--sort 等）；zeble.py 為 CLI 用；themes/ 來自 themes/css/、themes/pil/、themes/text/；測試頁透過 theme_api + gentable_*.php 呼叫 skill。 |
| 4 | doc/zeble_test*.html 改為呼叫 theme_api 與 gentable_*.php | zeble_test.html、zeble_test_v2.html 皆改為：onload 時從 theme_api.php?action=list 取得主題列表；選主題時（若來自 API）呼叫 loadThemeTemplateFromApi 載入 template；新增「後端渲染」按鈕，將 JSON（陣列 of 物件）轉成 `{headers, rows, title, footer}`，POST 至 gentable_pil/css/ascii.php，並顯示回傳圖片。gentable_*.php 已支援 page、sort、desc 傳遞給 zeble_render.py。 |
| 5 | index.html 暴露分頁／排序欄位 | 在左欄新增 Page、Sort by column、降序 (Desc) 勾選；Render Backend 時一併傳 page、sort、desc 給 gentable_*.php。 |
| 附 | gentable_*.php 改為優先調用 skill 的 zeble_render.py | gentable_css.php、gentable_pil.php、gentable_ascii.php 皆改為：`file_exists($scriptSkill)` 時用 skill 版，否則 fallback `doc/zeble_render.py`。 |
| 附 | theme_api 與 gentable 支援 page/sort/desc | gentable_pil.php、gentable_css.php、gentable_ascii.php 接受 POST 的 page、sort、desc，轉成 --page、--sort、--asc/--desc 傳給 zeble_render.py。 |

---

## 二、測試頁（doc）與 skill 資料夾的調用關係圖

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         zenTable 專案 ( /var/www/html/zenTable/ )                     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────────────┐  │
│  │  doc/             │     │  根目錄 PHP       │     │  themes/                 │  │
│  │  (測試頁資料夾)    │     │  (API 入口)      │     │  (fallback 主題)         │  │
│  │                   │     │                  │     │                          │  │
│  │  zeble_test.html  │     │  theme_api.php   │     │  css/dark/template.json  │  │
│  │  zeble_test_v2.html│     │  gentable_css.php│     │  pil/dark/template.json  │  │
│  │  zeble_render.py     │     │  gentable_pil.php│     │  ...                     │  │
│  │  zeble.py         │     │  gentable_ascii.php│    └──────────────────────────┘  │
│  │  table_detect.py  │     │                  │                                   │
│  └─────────┬─────────┘     └────────┬─────────┘                                   │
│            │                         │                                               │
│            │  ../theme_api.php        │  theme_api.php                                │
│            │  ../gentable_*.php       │  gentable_*.php                              │
│            │  (當頁面在 doc/ 時)       │  (index.html 在根目錄)                       │
│            │                         │                                               │
└────────────┼─────────────────────────┼───────────────────────────────────────────────┘
             │                         │
             │                         │  theme_api.php:
             │                         │    固定讀取專案 themes/
             │                         │
             │                         │  gentable_*.php:
             │                         │    固定執行 scripts/zeble_render.py
             │                         │
             ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    專案資料夾 ( /var/www/html/zenTable/ )                              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────┐ │
│  │  scripts/zeble_render.py  (主渲染程式)                                             │ │
│  │  • 被 gentable_css.php / gentable_pil.php / gentable_ascii.php 呼叫             │ │
│  │  • 讀取 themes/css/、themes/pil/、themes/text/ 的 template.json                  │ │
│  └──────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────┐ │
│  │  themes/                                                                        │ │
│  │    css/  dark, light, cyberpunk, forest, ocean, sunset, rose, midnight, ...     │ │
│  │    pil/  dark, light, forest, ocean, sunset, rose, midnight, glass, ...         │ │
│  │    text/ glass, ...                                                             │ │
│  │  每個主題一資料夾，內含 template.json                                            │ │
│  └──────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                     │
│  ┌────────────────────┐  (table_detect_api.php 呼叫)                               │
│  │  table_detect.py   │                                                             │
│  └────────────────────┘                                                             │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 調用流程（簡化）

```
[doc/zeble_test.html] 或 [index.html]
        │
        ├── GET  theme_api.php?action=list&mode=pil
        │              │
        │              └── theme_api.php 讀取 themes
        │                        │
        │                        ├── 優先：skill/themes/
        │                        └── fallback：專案 themes/
        │
        ├── GET  theme_api.php?action=load&theme=xxx
        │              └── 同上，回傳 template.json 內容
        │
        └── POST gentable_css.php | gentable_pil.php | gentable_ascii.php
                     │
                     │  (data, theme, page?, sort?, desc?)
                     ▼
              執行 Python 腳本
                     │
                     ├── 優先：skill/zeble_render.py
                     └── fallback：doc/zeble_render.py
                            │
                            └── 讀取 theme：優先 skill/themes/ → fallback 專案 themes/
```

### 檔案對照表

| 用途 | 測試頁／專案 | skill |
|------|--------------|-------|
| 主題 CSS | 專案 themes/css/（fallback） | skill themes/css/ |
| 主題 PIL | 專案 themes/pil/（fallback） | skill themes/pil/ |
| 渲染腳本 | doc/zeble_render.py（fallback） | skill zeble_render.py |
| 測試頁面 | doc/zeble_test.html, doc/zeble_test_v2.html | skill 內有副本（可同步） |
| 主測試頁 | index.html（根目錄） | 無，專案獨有 |
| API | theme_api.php, gentable_*.php（根目錄） | 無，專案獨有 |
