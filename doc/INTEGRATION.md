#!/usr/bin/env python3
"""
ZenTable 實際使用範例

展示如何整合到 agent 中使用
"""

# ============================================================================
# 方式 1: 在 Agent 中使用 (推薦)
# ============================================================================

class ZenTableAgent:
    """整合 ZenTable 的 Agent"""
    
    def __init__(self):
        self.render_script = "/var/www/html/zenTable/scripts/zeble_render.py"
    
    def handle_request(self, user_input: str):
        """處理用戶請求"""
        
        # Step 1: 偵測是否需要表格
        if self.needs_table(user_input):
            # Step 2: 準備資料
            data = self.prepare_data(user_input)
            
            # Step 3: 渲染表格
            output_path = self.render_table(data)
            
            # Step 4: 傳送到 Discord
            self.send_to_discord(output_path, "表格已生成")
        else:
            # 一般文字回覆
            self.send_text("這是普通回覆")
    
    def needs_table(self, user_input: str) -> bool:
        """偵測是否需要表格"""
        import subprocess
        result = subprocess.run(
            ["python3", "/var/www/html/zenTable/scripts/table_detect.py"],
            input=user_input,
            capture_output=True,
            text=True
        )
        # 解析回傳
        import json
        data = json.loads(result.stdout)
        return data.get("needs_table", False)
    
    def prepare_data(self, user_input: str) -> dict:
        """從用戶輸入準備 JSON 資料"""
        # 這裡根據你的 agent 邏輯實作
        # 可能是從資料庫、API、或解析用戶輸入
        return {
            "title": "查詢結果",
            "headers": ["名稱", "價格", "庫存"],
            "rows": [
                ["商品 A", "$100", "50"],
                ["商品 B", "$200", "30"],
            ]
        }
    
    def render_table(self, data: dict) -> str:
        """渲染表格"""
        import subprocess
        import json
        import tempfile
        
        # 寫入暫存資料
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f, ensure_ascii=False)
            data_path = f.name
        
        output_path = f"/tmp/table_{id(data)}.png"
        
        # 呼叫渲染腳本
        result = subprocess.run(
            ["python3", self.render_script, "-d", data_path, "-o", output_path],
            capture_output=True,
            text=True
        )
        
        # 清理
        import os
        os.unlink(data_path)
        
        if result.returncode != 0:
            raise RuntimeError(f"渲染失敗: {result.stderr}")
        
        return output_path
    
    def send_to_discord(self, image_path: str, caption: str):
        """傳送到 Discord"""
        from openclaw import message
        message(action="send", filePath=image_path, message=caption)
    
    def send_text(self, text: str):
        """傳送文字"""
        from openclaw import message
        message(action="send", message=text)


# ============================================================================
# 方式 2: 直接指令呼叫 (簡單場景)
# ============================================================================

def simple_example():
    """直接用指令渲染"""
    import subprocess
    import json
    
    # 準備資料
    data = {
        "title": "價格比較",
        "headers": ["產品", "價格"],
        "rows": [["A", "$99"], ["B", "$149"]]
    }
    
    # 寫入資料檔案
    with open("/tmp/data.json", "w") as f:
        json.dump(data, f)
    
    # 呼叫渲染
    subprocess.run([
        "python3", "/var/www/html/zenTable/scripts/zeble_render.py",
        "/tmp/data.json",
        "/tmp/table.png",
        "--force-css",
        "--theme-name", "default_dark"
    ])
    
    # 傳送
    from openclaw import message
    message(action="send", filePath="/tmp/table.png", message="這是表格")


# ============================================================================
# 方式 3: API 方式 (HTTP server)
# ============================================================================

def api_example():
    """使用 PHP API"""
    import requests
    import json
    
    data = {
        "title": "API 測試",
        "headers": ["A", "B"],
        "rows": [["1", "2"]]
    }
    
    # POST 到 API
    response = requests.post(
        "http://localhost/zenTable/gentable_css.php",
        data={"data": json.dumps(data), "theme": "cyberpunk"}
    )
    
    result = response.json()
    
    if result["success"]:
        image_url = result["image"]  # /zenTable/table_xxx.png
        # 傳送
        from openclaw import message
        message(action="send", filePath="/var/www/html/zenTable" + image_url)


# ============================================================================
# 方式 4: 在 OpenClaw Hook 中使用
# ============================================================================

"""
在 SOUL.md 中設定：

## 表格處理 Hook

當 agent 準備回覆時：
1. 檢查是否需要表格
2. 如果需要，用 zentable_render.py 渲染
3. 傳送圖片
"""

# 偽代碼
def agent_hook(user_message: str) -> str:
    if needs_table(user_message):
        data = extract_table_data(user_message)
        output = render_zentable(data)
        return send_image_and_caption(output, "表格如下")
    else:
        return normal_response(user_message)


# ============================================================================
# 環境偵測流程
# ============================================================================

def detect_environment():
    """偵測可用渲染方式"""
    import subprocess
    import os
    
    # 檢查 Chrome
    chrome_paths = [
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    ]
    
    chrome = None
    for path in chrome_paths:
        if os.path.exists(path):
            chrome = path
            break
    
    if chrome:
        return {
            "mode": "css_chrome",
            "chrome": chrome,
            "need_xvfb": not os.environ.get("DISPLAY")
        }
    else:
        return {
            "mode": "pil",
            "reason": "No Chrome found, using PIL fallback"
        }


# ============================================================================
# 完整工作流程圖
# ============================================================================

WORKFLOW = """
┌────────────────────────────────────────────────────────────────────┐
│                       用戶請求                                      │
│                       "列出產品價格"                                │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌────────────────────────────────────────────────────────────────────┐
│                    table_detect.py                                 │
│                    偵測結果: needs_table=true                      │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌────────────────────────────────────────────────────────────────────┐
│                    準備 JSON 資料                                  │
│                    {"title":"產品", "headers":["名稱","價格"],...} │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌────────────────────────────────────────────────────────────────────┐
│                    環境偵測                                         │
│                    Chrome 可用? ── 是 ─→ CSS + Chrome             │
│                          ↓ 否                                      │
│                    PIL Fallback                                    │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌────────────────────────────────────────────────────────────────────┐
│                    zentable_render.py                              │
│                    輸出: /tmp/table_xxx.png                        │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌────────────────────────────────────────────────────────────────────┐
│                    Discord 傳送                                    │
│                    message(action="send", filePath=...)            │
└────────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌────────────────────────────────────────────────────────────────────┐
│                       用戶看到圖片                                  │
└────────────────────────────────────────────────────────────────────┘
"""

if __name__ == "__main__":
    print(WORKFLOW)
