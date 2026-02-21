# Skill 完整運行評估

## 一、調用鏈是否完整

| 組件 | 專案端 | Skill 端 | 狀態 |
|------|--------|----------|------|
| CSS 渲染 | gentable_css.php | scripts/zeble_render.py | ✅ 固定調用本專案 |
| PIL 渲染 | gentable_pil.php | scripts/zeble_render.py | ✅ 同上 |
| ASCII 渲染 | gentable_ascii.php | scripts/zeble_render.py | ✅ 同上 |
| 主題列表/載入 | theme_api.php | themes/ | ✅ 固定讀取本專案 |
| 主題儲存 | theme_api.php action=save | themes/ | ⚠️ 需寫入權限 |
| 表格偵測 | table_detect_api.php | scripts/table_detect.py | ✅ 固定調用本專案 |

## 二、Skill 程式與資源完整性

| 項目 | 路徑 | 狀態 |
|------|------|------|
| 主渲染程式 | /var/www/html/zenTable/scripts/zeble_render.py | ✅ |
| 表格偵測 | /var/www/html/zenTable/scripts/table_detect.py | ✅ |
| CSS 主題 | themes/css/（dark, light, cyberpunk, glass...） | ✅ |
| PIL 主題 | themes/pil/（dark, light, forest, gradient_modern...） | ✅ |
| Text 主題 | themes/text/glass/ | ✅ |

## 三、環境依賴與潛在阻礙

### 1. 必備（所有模式）

- **Python 3**：執行 zeble_render.py、table_detect.py
- **table_detect.py**：僅用 json/sys/re，無額外依賴 ✅

### 2. CSS 模式

- **Chrome/Chromium**：`google-chrome` 或 `chromium` 需在 PATH
- **xvfb-run**：無 X11 時需安裝
- **代理**：zeble_render.py 內含 `--proxy-server=http://localhost:8191`，若無代理可能導致 Chrome 卡住或失敗

### 3. PIL 模式

- **Pillow**：`pip install Pillow`
- **字體**：Noto Sans CJK、Symbola（或系統 fallback）

### 4. ASCII 模式

- 僅需 Python 3 ✅

## 四、結論與建議

### 可完整運行的條件

1. **本專案檔案齊全**：`scripts/zeble_render.py`、`scripts/table_detect.py`、`themes/` 存在
2. **PHP 能執行**：gentable_*.php、theme_api.php 可被 Apache/nginx 執行
3. **模式對應環境**：
   - ASCII：一定會跑
   - PIL：需 Pillow
   - CSS：需 Chrome + xvfb

### 建議調整（可選）

| 項目 | 說明 |
|------|------|
| Chrome 代理 | zeble_render.py 的 `--proxy-server=...` 若環境無代理，可改為不加或設為空，避免 Chrome 卡住 |
| 主題儲存寫入 | theme_api save 寫入 skill themes 時，需 `themes/<mode>/` 可寫；否則可改為 fallback 寫專案 themes |
| 輸出路徑 | gentable_*.php 寫入 `/var/www/html/zenTable/`，需確保 PHP 有寫入權限 |

### 快速驗證

```bash
# 1. 直接測試 zeble_render.py（ASCII 最輕量）
cd /var/www/html/zenTable
echo '[{"a":1,"b":2}]' > /tmp/test.json
python3 scripts/zeble_render.py /tmp/test.json /tmp/out.png --force-ascii --output-ascii /tmp/out.txt

# 2. 測試 PIL（需 Pillow）
python3 scripts/zeble_render.py /tmp/test.json /tmp/out.png --force-pil --theme-name dark

# 3. 測試 table_detect
echo '列出價格比較表' | python3 scripts/table_detect.py
```
