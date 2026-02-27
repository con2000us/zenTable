# ZenTable 開發流程文檔

## 專案架構

```
zeble/
├── zeble.py              # 主入口 CLI 工具
├── zentable_render.py    # 表格渲染核心 (PIL)
├── zentable_renderer.py          # CSS 產生器
├── smart_table_output.py # 智能表格輸出
├── table_detect.py       # 表格偵測/分析
├── gen_test_data.py      # 測試資料生成
├── reproduce_issue.py    # 問題重現腳本
├── themes/               # 主題配置
└── doc/                  # 本文檔目錄
```

## 開發流程

### 1. 修改核心程式碼
- **Python 檔案** → 直接修改 `doc/` 目錄下的 `.py` 檔案
- **CSS/主題** → 修改 `themes/` 目錄或 `zeble_render.py`

### 2. 測試方式

#### A. CLI 測試
```bash
python3 zentable.py input.json output.png
```

#### B. 瀏覽器測試
開啟 `doc/zeble_test_v2.html` 或 `doc/zeble_test.html`：
```
http://192.168.68.115/zenTable/doc/zeble_test_v2.html
```

#### C. 問題重現
```bash
python3 doc/reproduce_issue.py
```

### 3.（已移除）同步回 skill 目錄
目前以本專案 `/var/www/html/zenTable/` 為唯一來源，後端端點會固定呼叫 `scripts/` 下的 Python 程式，因此不需要再同步到外部 `/opt/...`。

## 輸入格式

### JSON 結構
```json
{
  "theme": "dark",
  "columns": [
    {"key": "name", "label": "名稱", "width": 150},
    {"key": "value", "label": "數值", "width": 100}
  ],
  "data": [
    {"name": "項目 A", "value": "100"},
    {"name": "項目 B", "value": "200"}
  ]
}
```

### 測試資料
- `example_table.json` - 基礎範例
- `example_table_large.json` - 大型表格
- `rich_test_data.json` - 豐富格式測試

## 常見問題排查

### JavaScript 錯誤
若瀏覽器出現 `Unexpected end of input`：
1. 檢查 JSON 格式是否完整
2. 確認無多餘逗號
3. 查看第 572 行附近缺少的結束符號

### 渲染問題
執行 `python3 doc/reproduce_issue.py` 重現問題

## 注意事項
- 所有修改請在 `doc/` 目錄下進行
- 同步前請先備份原始檔案
- 測試頁面可直接用瀏險器開啟本地檔案或透過 HTTP 伺服器
