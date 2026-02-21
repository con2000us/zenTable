# Zeble - Zen Table Output

**讓表格文字有禪意的風格輸出**

## 功能特性

- 🎨 **混合字體渲染**
  - 中文 → Noto Sans CJK
  - Emoji → Symbola（彩色符號）
  - 自動垂直對齊

- 🔧 **狀態指示器**
  - 自動狀態欄渲染
  - 狀態點（綠/黃/紅）
  - 狀態文字顏色

- 📊 **主題系統**
  - 深色、淺色、賽博龐克、森林、海洋、日落、玫瑰、午夜

- 🖼️ **背景與邊框**
  - 自訂背景圖片
  - 自訂邊框圖片
  - 圓角矩形

## 字體策略

### Emoji 替換規則

| 原始 | 替換為 | 原因 |
|------|--------|------|
| 🟢 | (綠) | Symbola 不支援 |
| 🟡 | (黃) | Symbola 不支援 |
| 其他 | 原樣 | Symbola 正常顯示 |

### Unicode 區塊支援

- ✅ 狀態類：U+2700-U+27BF, U+2600-U+26FF
- ✅ 表情類：U+1F600-U+1F64F  
- ✅ 雜項類：U+1F300-U+1F9FF
- ✅ 交通類：U+1F680-U+1F6FF
- ✅ 國旗類：U+1F1E6-U+1F1FF
- ✅ 箭頭類：U+2194-U+2199, U+21A9-U+21AA
- ✅ 其他：U+231A-U+231B, U+2139

## 使用方式

```bash
python3 zeble.py <input.json> <output.png> [options]
```

## 參數

### 主題
```bash
--dark    # 深色 (預設)
--light   # 淺色
--cyberpunk  # 賽博龐克
--forest  # 森林
--ocean   # 海洋
--sunset  # 日落
--rose    # 玫瑰
--midnight # 午夜
```

### 分頁
```bash
--page N  # 第 N 頁
```

### 排序
```bash
--sort <欄位名>  # 排序欄位
--asc            # 升序
--desc           # 降序
```

## 輸入格式

### 格式 1：JSON 陣列
```json
[
  {"名稱": "伺服器 A", "狀態": "運行中", "延遲": "15ms"},
  {"名稱": "伺服器 B", "狀態": "維護", "延遲": "--"}
]
```

### 格式 2：表頭+資料
```json
{
  "headers": ["名稱", "狀態", "延遲"],
  "rows": [["伺服器 A", "運行中", "15ms"]]
}
```

### 格式 3：含圖片設定
```json
{
  "bg_image": "/path/to/bg.png",
  "border_image": "/path/to/border.png",
  "data": [...]
}
```

## 主題配置

### 深色 (dark)
```python
{
  "bg_color": "#1a1a2e",
  "text_color": "#ffffff",
  "header_bg": "#0f3460",
  "header_text": "#e94560",
  "alt_row_color": "#16213e",
  "border_color": "#4a5568",
  "highlight_color": "#e94560"
}
```

### 淺色 (light)
```python
{
  "bg_color": "#f8f9fa",
  "text_color": "#212529",
  "header_bg": "#e9ecef",
  "header_text": "#495057",
  "alt_row_color": "#ffffff",
  "border_color": "#dee2e6",
  "highlight_color": "#0d6efd"
}
```

### 賽博龐克 (cyberpunk)
```python
{
  "bg_color": "#0d0221",
  "text_color": "#00ff9f",
  "header_bg": "#ff00ff",
  "header_text": "#000000",
  "alt_row_color": "#1a1a3e",
  "border_color": "#00ff9f",
  "highlight_color": "#ffff00"
}
```

## 狀態欄自動偵測

自動偵測以下關鍵字：
- ✅ 運行：運行、active、online、success、ok
- ⚠️ 維護：維護、warning、warn、pending
- ❌ 離線：離線、error、fail、offline

## 字體路徑

```python
CHINESE_FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
EMOJI_FONT_PATH = "/usr/share/fonts/truetype/ancient-scripts/Symbola_hint.ttf"
```

## 檔案結構

```
skills/zeble/
├── SKILL.md          # 技能說明
├── zeble.py          # 主程式
├── zeble_test.html   # 測試網頁
├── README.md         # 本文件
└── test_*.json       # 測試數據
```

## 版本歷史

### v2.0 (2026-02-09)
- ✅ 混合字體渲染
- ✅ Emoji Unicode 區塊支援
- ✅ 垂直對齊調整
- ✅ 彩色圓圈替換
- ✅ 變體選擇符處理

### v1.0 (初始版本)
- 基礎表格渲染
- 主題系統
- 狀態指示器
