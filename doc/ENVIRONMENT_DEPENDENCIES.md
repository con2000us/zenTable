# Skill 環境依賴（依目前 skill 程式）

以下依 **zeble_render.py**、**table_detect.py** 等 skill 程式整理，執行時需要的環境與資源。

---

## 一、依渲染模式區分

| 模式 | 觸發條件 | 依賴 |
|------|----------|------|
| **CSS + Chrome** | 預設（有 Chrome 時） | Chrome/Chromium、xvfb-run、Python 3 |
| **PIL（fallback）** | 無 Chrome 或 `--force-pil` | Python 3、Pillow (PIL)、字體（見下方） |
| **ASCII** | `--force-ascii` | 僅 Python 3（無圖、無字體） |
| **Table Detect** | table_detect_api 呼叫 | 僅 Python 3（無瀏覽器、無字體） |

---

## 二、必要環境資源

### 1. Python

- **版本**：Python 3（建議 3.8+）
- **用途**：執行 `zeble_render.py`、`table_detect.py`
- **標準庫**：`json`, `sys`, `os`, `re`, `glob`, `subprocess`, `typing`, `dataclasses`（皆內建）

### 2. Chrome / Chromium（僅 CSS 模式）

- **程式**：`google-chrome`（或 Chromium）須在 `PATH`，腳本以 `which google-chrome` 偵測
- **模式**：需支援 **headless** 與下列參數：
  - `--headless`
  - `--screenshot=<路徑>`
  - `--virtual-time-budget=3000`
  - `--hide-scrollbars`
  - `--disable-gpu`
  - （透空時）`--default-background-color=00000000`（8 位 hex RGBA）
- **代理**：目前指令含 `--proxy-server=http://localhost:8191`，若環境無代理可改或移除
- **安裝範例（Ubuntu/Debian）**：
  ```bash
  sudo apt-get update
  sudo apt-get install -y google-chrome-stable
  # 或 chromium: sudo apt-get install -y chromium-browser
  ```
- **無顯示環境**：需 **xvfb**，指令為 `xvfb-run -a google-chrome ...`

### 3. xvfb（無顯示器時，CSS 模式）

- **用途**：在無 X11 的環境下跑 Chrome headless
- **指令**：`xvfb-run -a`
- **安裝範例（Ubuntu/Debian）**：
  ```bash
  sudo apt-get install -y xvfb
  ```

### 4. Pillow（PIL）（PIL 模式必備）

- **用途**：PIL 模式畫圖、透空 fallback 後製（chroma key）
- **套件**：`Pillow`（`from PIL import Image, ImageDraw, ImageFont`）
- **安裝**：
  ```bash
  pip install Pillow
  # 或 pip3 install Pillow
  ```

### 5. 字體（僅 PIL 模式）

腳本會依「固定路徑 → 掃描系統字型」順序找字體；無則用 PIL 內建預設字型（中文與 Emoji 效果較差）。

#### 中文（CJK）

| 用途 | 預設路徑 | 說明 |
|------|----------|------|
| 一般中文、標題、儲存格 | `/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc` | Noto Sans CJK |

- **安裝範例（Ubuntu/Debian）**：
  ```bash
  sudo apt-get install -y fonts-noto-cjk
  ```

#### Emoji（優先彩色）

| 優先順序 | 路徑 |
|----------|------|
| 1 | `/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf` |
| 2 | `/usr/share/fonts/google-noto-emoji/NotoColorEmoji.ttf` |
| 3 | `/usr/share/fonts/noto/NotoColorEmoji.ttf` |
| 4 | `/usr/share/fonts/noto-color-emoji/NotoColorEmoji.ttf` |
| 5 | `/usr/share/fonts/truetype/ancient-scripts/Symbola_hint.ttf`（單色備援） |
| 6 | `/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf` |
| 7 | 掃描 `/usr/share/fonts`、`/usr/local/share/fonts` 下 `*Noto*Emoji*`、`*Symbola*` |

- **安裝範例（Ubuntu/Debian）**：
  ```bash
  sudo apt-get install -y fonts-noto-color-emoji
  # 備援：sudo apt-get install -y fonts-symbola 或 ttf-dejavu
  ```

---

## 三、不需額外依賴的部分

- **table_detect.py**：僅用 Python 標準庫（`json`, `sys`, `re`），不需 Chrome、字體、PIL。
- **ASCII 模式**：只輸出文字，不需圖、字體、Chrome。
- **主題（themes/）**：為 JSON 與 HTML/CSS，不需額外執行檔或字體。

---

## 四、依賴總覽表

| 資源 | CSS 模式 | PIL 模式 | ASCII | Table Detect |
|------|----------|----------|-------|--------------|
| Python 3 | ✅ | ✅ | ✅ | ✅ |
| google-chrome (headless) | ✅ | — | — | — |
| xvfb-run | ✅（無顯示時） | — | — | — |
| Pillow (PIL) | 僅透空 fallback 時 | ✅ | — | — |
| Noto Sans CJK | — | ✅ | — | — |
| Noto Color Emoji / Symbola 等 | — | ✅（建議） | — | — |

---

## 五、建議部署檢查清單

在執行 skill 的機器上可依序確認：

1. `python3 --version` ≥ 3.8  
2. `which google-chrome` 或 `which chromium-browser` 有路徑（若要用 CSS 模式）  
3. `xvfb-run -a true` 可執行（無顯示器時）  
4. `python3 -c "from PIL import Image; print('OK')"` 通過（若要用 PIL）  
5. 上述 Noto CJK / Emoji 路徑至少一個存在（若要用 PIL 且要中文與 Emoji 正常）  
6. `themes/css/`、`themes/pil/` 等主題目錄與 `template.json` 已就緒  

若測試頁或 API 呼叫 skill 的 PHP 在另一台機器，該機只需能執行 PHP 並能呼叫到上述環境（同機或遠端執行 Python/Chrome）。
