# ZenTable 主題來源說明

所有模式的 theme **一律從「各自主題資料夾」讀出**，不得使用根目錄扁平 `.json`。完整規則與目錄結構見 **[THEME_STRUCTURE.md](THEME_STRUCTURE.md)**。

路徑格式：

```
themes/
├── css/<theme_id>.zip   # CSS 模式（zip 內含 template.json）
├── pil/<theme_id>.zip   # PIL 模式（zip 內含 template.json）
└── text/<theme_id>.zip  # ASCII 模式（zip 內含 template.json）
```

載入順序：固定使用本專案 `themes/`（`/var/www/html/zenTable/themes/`）。

---

## 已移除的其餘 theme 來源

以下來源已移除，不再使用；主題僅能來自上述目錄。

| 來源 | 位置 | 說明 |
|------|------|------|
| **BUILTIN_THEMES** | zentable_render.py（已刪除） | 內建 CSS 主題字典（default_dark, default_light, cyberpunk, gradient_modern, glass, forest） |
| **render_pil 內建 theme_colors** | scripts/zentable_render.py（舊版） | PIL 的內建主題顏色 dict（default_dark, default_light, cyberpunk, gradient_modern, glass） |
| **render_pil theme_name_map** | scripts/zentable_render.py（舊版） | 前端 theme id 對應內建 key（dark→default_dark, light→default_light 等） |
| **theme_api 靜態 text 主題** | theme_api.php | load 時對 simple/grid/double 回傳的內聯 JSON template |
| **theme_api 靜態 text 列表** | theme_api.php | list 時對 mode=text 回傳的固定 [simple, grid, double] 列表 |

---

## 仍保留的與「主題」無關的常數

| 項目 | 位置 | 說明 |
|------|------|------|
| **ASCII_STYLES** | scripts/zentable_render.py | 框線字元實作（single/double/grid/markdown），由 theme 的 `params.style` 選擇使用哪一種，非主題定義本身 |

**注意**：theme_api 已不再支援扁平 `themes/*.json`，僅讀取 `themes/<mode>/<theme_id>.zip`（zip 內含 `template.json`）。見 [THEME_STRUCTURE.md](THEME_STRUCTURE.md)。

---

## 各模式對 template.json 的依賴

- **CSS**：`theme.styles`（選擇器 → CSS 字串）＋ 必要時 `template` 結構。
- **PIL**：`theme.params`（bg_color, text_color, header_bg, header_text, alt_row_color, border_color，及 font_size, padding 等）；API 傳入的 custom_params 會覆蓋同名字段。
- **ASCII**：`theme.params`（style, padding, align, header_align）對應 ASCIIStyle。

若目錄中沒有對應的 theme，會先嘗試別名（dark→default_dark, light→default_light），再嘗試 default_dark / default_light；若仍找不到則報錯。
