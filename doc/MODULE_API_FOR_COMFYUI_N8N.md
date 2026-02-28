# ZenTable 校準與渲染模組 API（供 ComfyUI / n8n 使用）

## 一、現況與目標

- **校準**：`calibrate_analyze.py` 以 CLI 執行，主邏輯在 `analyze_widths(image_path, custom_chars, use_ocr)`。
- **渲染**：`scripts/zentable_render.py` 以 CLI 執行，`main()` 內依參數分支呼叫 `render_ascii` / `generate_css_html` + `render_css` / `render_pil`。

目標：抽出**可 import 的函數 API**，讓 ComfyUI 自訂節點或 n8n 的 Python/HTTP 節點能直接呼叫，而不必組 `sys.argv` 或跑 subprocess。

---

## 二、建議模組結構

```
zenTable/
├── zentable/                    # 可安裝的套件（選用）
│   ├── __init__.py
│   ├── calibration.py          # 校準：從 calibrate_analyze.py 抽出
│   └── render.py                # 渲染：從 scripts/zentable_render.py 抽出
├── calibrate_analyze.py         # CLI 入口，改為 import zentable.calibration 再呼叫
├── scripts/zentable_render.py        # CLI 入口，改為 import zentable.render
└── doc/
    └── MODULE_API_FOR_COMFYUI_N8N.md
```

或**不新增套件**，只在前端專案內提供「薄包裝層」：

```
zenTable/
├── api/
│   ├── __init__.py
│   ├── calibration_api.py      # 薄包裝：呼叫 calibrate_analyze.analyze_widths
│   └── render_api.py            # 薄包裝：呼叫 scripts/zentable_render.py
├── calibrate_analyze.py
└── scripts/zentable_render.py
```

以下以「薄包裝 + scripts/zentable_render.py」為例，不強制改目錄結構。

---

## 三、校準 API（給 ComfyUI / n8n 呼叫）

### 3.1 現有可重用函數（calibrate_analyze.py）

| 函數 | 行號 | 簽名 | 說明 |
|------|------|------|------|
| **analyze_widths** | 2383 | `analyze_widths(image_path: str, custom_chars: str = "", use_ocr: bool = True) -> Dict[str, Any]` | 主入口。回傳 `{ "calibration": {...}, "pixel_per_unit": float, "ocr_lines": [...], "char_measurements": [...] }` |
| **analyze_widths_by_pixel** | 2257 | `analyze_widths_by_pixel(image_path: str, custom_chars: str = "") -> Dict` | 不用 OCR，純像素計數。 |

**回傳的 calibration** 可直接給 `scripts/zentable_render.py` 的 ASCII 模式（`--calibration` JSON）。

### 3.2 模組包裝範例（可放在 api/calibration_api.py）

```python
# api/calibration_api.py
import os
import sys

def add_calibrate_path():
    """讓 ComfyUI/n8n 能找到 calibrate_analyze"""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root not in sys.path:
        sys.path.insert(0, root)

def analyze_from_image(
    image_path: str,
    custom_chars: str = "",
    use_ocr: bool = True,
) -> dict:
    """
    從校準截圖分析寬度。供 ComfyUI / n8n 呼叫。
    - image_path: 截圖路徑（或 PIL Image 可改為接受 path）
    - custom_chars: 自訂字元序列
    - use_ocr: True=OCR 測量，False=像素測量
    回傳: {"calibration": {...}, "pixel_per_unit": float, "ocr_lines": [...], "char_measurements": [...]}
    """
    add_calibrate_path()
    from calibrate_analyze import analyze_widths
    return analyze_widths(image_path, custom_chars=custom_chars, use_ocr=use_ocr)
```

ComfyUI / n8n 只要把 `zenTable` 或 `api` 加入 `sys.path`，即可 `from api.calibration_api import analyze_from_image`。

---

## 四、渲染 API（給 ComfyUI / n8n 呼叫）

### 4.1 scripts/zentable_render.py 需新增「程式入口」

目前只有 `main()` 讀 `sys.argv`。建議新增一個**純參數的入口**，例如：

```python
# 在 scripts/zentable_render.py（或其可 import 模組）新增

def run_render(
    data: dict,
    output_path: str,
    mode: str = "css",  # "css" | "pil" | "ascii"
    theme_name: str = "default_dark",
    theme_json: dict = None,
    *,
    page: int = 1,
    per_page: int = 15,
    sort_by: str = None,
    sort_asc: bool = True,
    calibration: dict = None,
    params_override: dict = None,
    transparent: bool = False,
    width: int = None,
    scale: float = 1.0,
    fill_width: str = None,
    bg: str = None,
    output_ascii_path: str = None,
) -> dict:
    """
    表格渲染程式入口。供 ComfyUI / n8n 呼叫，不依賴 sys.argv。
    - data: { "headers": [...], "rows": [[...]], "title": "", "footer": "" }
    - output_path: 輸出 PNG 路徑（ASCII 模式時若 output_ascii_path 有值則寫文字檔）
    - mode: "css" | "pil" | "ascii"
    - theme_name: themes/<mode>/ 下的主題名
    - theme_json: 若給定則取代從檔案載入的主題（與 theme_name 二擇一或 theme_json 優先）
    - calibration: ASCII 用校準 dict（可來自 analyze_widths 回傳的 calibration）
    - params_override: PIL/ASCII 的額外參數
    回傳: {"success": bool, "path": str, "error": str}
    """
    # 內部依 mode 呼叫 normalise_data, apply_sort_and_page, get_theme/theme_json,
    # 再分支 render_ascii / generate_css_html+render_css / render_pil，寫檔。
    # 實作時把 main() 裡對應邏輯抽成此函數即可。
    ...
```

這樣 ComfyUI 或 n8n 的 Python 節點即可：

```python
from api.render_api import render_table
result = run_render(
    data={"headers": ["A","B"], "rows": [["1","2"]], "title": "Test", "footer": ""},
    output_path="/tmp/out.png",
    mode="css",
    theme_name="neon_cyber",
)
# result["path"] 即輸出檔
```

---

## 五、ComfyUI 整合方式

### 5.1 自訂節點目錄

在 ComfyUI 的 `custom_nodes/` 下新增一個節點包，例如：

```
ComfyUI/custom_nodes/comfyui_zentable/
├── __init__.py
├── zentable_calibrate.py   # 節點：輸入 image → 輸出 calibration dict
└── zentable_table.py       # 節點：輸入 data + theme + mode → 輸出 image path
```

### 5.2 校準節點範例（輸入圖片 → 輸出 calibration）

```python
# 在 NODE_CLASS_MAPPINGS 註冊
from .zentable_calibrate import ZenTableCalibrateNode

class ZenTableCalibrateNode:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE",),  # ComfyUI 的 image tensor
            },
            "optional": {
                "custom_chars": ("STRING", {"default": ""}),
                "use_ocr": ("BOOLEAN", {"default": True}),
            },
        }
    RETURN_TYPES = ("STRING",)  # JSON 字串
    FUNCTION = "run"
    def run(self, image, custom_chars="", use_ocr=True):
        # 把 image 存成暫存檔，呼叫 analyze_from_image(path, custom_chars, use_ocr)
        # 回傳 json.dumps(result)
        ...
```

### 5.3 表格渲染節點範例（輸入 data + 選項 → 輸出圖片）

```python
# 輸入：data (JSON 字串或從上游)、mode、theme_name；輸出：IMAGE 或 path
# 內部呼叫 run_render(data, output_path, mode=mode, theme_name=theme_name)
# 再 load_image(output_path) 轉成 ComfyUI IMAGE
```

關鍵：ComfyUI 需能 **import 到** `calibrate_analyze` 與 `scripts/zentable_render.py`（或其薄包裝）。做法二擇一：

- 把 `zenTable` 目錄（或 `api`）加入 `sys.path`，例如在節點 `__init__.py` 裡 `sys.path.insert(0, "/var/www/html/zenTable")`；或
- 把 `calibrate_analyze.py` / `scripts/zentable_render.py` 複製或 symlink 到 `custom_nodes/comfyui_zentable/`，再在節點內 import。

---

## 六、n8n 整合方式

### 6.1 用現有 PHP API（最簡單）

n8n 用 **HTTP Request** 節點呼叫既有 API，無需改 Python：

- 校準：`POST` 到 `https://your-host/zenTable/calibrate_upload.php`（form-data: image + 參數）
- 渲染：`POST` 到 `https://your-host/zenTable/gentable_css.php` 或 `gentable_pil.php`、`gentable_ascii.php`（form-data: data, theme, ...）

回傳 JSON 內含 `calibration` 或 `image` 路徑，n8n 再往下傳。

### 6.2 用 Python 節點直接呼叫模組

若 n8n 跑在能存取 zenTable 的環境，可在 **Code** 節點或 **Execute Command** 裡：

```javascript
// n8n Code 節點（執行在 n8n 的 Node 環境，若同機可 subprocess）
const { execSync } = require('child_process');
const data = $input.first().json.data;  // 表資料
const out = execSync(`python3 /var/www/html/zenTable/scripts/zentable_render.py /tmp/in.json /tmp/out.png --force-css --theme-name neon_cyber`, {
  input: JSON.stringify(data),
  encoding: 'utf-8'
});
return { json: { path: '/tmp/out.png' } };
```

或若 n8n 支援內嵌 Python（或另開一個小服務）：

```python
# 假設 n8n 能執行 Python 並指定 zenTable 路徑
import sys
sys.path.insert(0, "/var/www/html/zenTable")
from api.render_api import render_table
result = render_table(data, output_path="/tmp/out.png", mode="css", theme_name="neon_cyber")
```

### 6.3 獨立 HTTP 服務（Flask/FastAPI）包一層

若希望 n8n 一律用 HTTP 且不想依賴 PHP：

- 寫一個小型 FastAPI/Flask app，例如：
  - `POST /calibrate`：上傳圖片 → 呼叫 `analyze_from_image` → 回傳 `{ "calibration": ... }`
  - `POST /render`：body `{ "data", "mode", "theme_name", ... }` → 呼叫 `run_render` → 回傳 `{ "path": "/tmp/xxx.png" }` 或 base64 圖
- 部署在同一台或 n8n 能連到的機器，n8n 用 HTTP Request 節點呼叫。

---

## 七、實作檢查清單（摘要）

| 項目 | 說明 |
|------|------|
| 校準 | `calibrate_analyze.analyze_widths` 已是純函數，可直接 import；可加薄包裝 `analyze_from_image` 並處理 `sys.path`。 |
| 渲染 | 優先使用 `api/render_api.py::render_table`；CLI canonical 入口是 `scripts/zentable_render.py`。 |
| ComfyUI | 新增 custom node，內部 import 校準/渲染 API，輸入輸出對應 ComfyUI 的 IMAGE / STRING。 |
| n8n | 選一種：現成 PHP API、Execute Command 呼叫 CLI、或獨立 Flask/FastAPI 包一層再 HTTP 呼叫。 |

---

## 八、已提供的模組（api/）

專案內已新增可 import 的薄包裝，位置：`zenTable/api/`。

### 校準

```python
import sys
sys.path.insert(0, "/var/www/html/zenTable")
from api.calibration_api import analyze_from_image, analyze_from_image_pixel

# 從截圖分析，回傳 calibration 等
result = analyze_from_image("/path/to/cal_screenshot.png", custom_chars="", use_ocr=True)
calibration = result["calibration"]  # 可傳給 ASCII 渲染或存檔
```

### 渲染（subprocess 呼叫 zentable_render.py）

```python
from api.render_api import render_table

out = render_table(
    data={"headers": ["A","B"], "rows": [["1","2"]], "title": "Test", "footer": ""},
    output_path="/tmp/table.png",
    mode="css",
    theme_name="neon_cyber",
    script_path="/var/www/html/zenTable/scripts/zentable_render.py",
)
if out["success"]:
    print("輸出:", out["path"])
else:
    print("錯誤:", out["error"], out["stdout"])
```

- **ComfyUI**：在自訂節點內 `sys.path.insert(0, "/var/www/html/zenTable")` 後 `from api import analyze_from_image, render_table` 即可。
- **n8n**：同上，或在同機用 Execute Command 呼叫 `python3 -c "from api import ..."`，或直接呼叫現有 PHP API（見六、6.1）。
