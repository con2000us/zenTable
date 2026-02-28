# ZenTable Skill 三層架構（感知層 / 核心演算層 / 輸出層）

> 摘錄並整理自 `doc/refactor/todo.md` 的 Three-Layer Architecture Mapping，作為可直接閱讀的架構入口。

## 架構總覽

ZenTable 目前以三層分工概念設計：

1. **Detector Layer（感知/解析層）**
2. **Engine Layer（核心演算層）**
3. **Renderer Layer（渲染/輸出層）**

資料流方向：

`Detector → Engine → Renderer`

---

## 1) Detector Layer（感知/解析層）

**對應模組**：`scripts/zentable/input/`

**主要職責**：
- JSON 讀取、格式標準化、錯誤復原
- 主題載入、快取、列舉
- 意圖判斷（如 `table_detect.py`，已是獨立路徑）

**典型輸出**：
- 正規化資料：`{headers, rows, title, footer}`

---

## 2) Engine Layer（核心演算層）

**對應模組**：`scripts/zentable/transform/`

**主要職責**：
- 表格轉置、過濾、排序、分頁
- smart-wrap 與 highlight rule 套用
- CJK 字元寬度計算
- 儲存格正規化與文字抽取

**典型輸出**：
- 轉換後資料 + highlight metadata

---

## 3) Renderer Layer（渲染/輸出層）

**對應模組**：`scripts/zentable/output/{ascii,css,pil}/`

**主要職責**：
- **ASCII**：框線樣式、對齊、校準輸出
- **CSS**：HTML 生成、Chrome headless 截圖、viewport/crop
- **PIL**：繪圖、字體管理、藍圖視覺化
- 共用能力：色彩處理、emoji/CJK 文字分段

---

## 目錄對應（簡版）

```text
scripts/
├── zentable_render.py          # CLI 入口（dispatcher）
└── zentable/
    ├── input/                  # Detector Layer
    ├── transform/              # Engine Layer
    └── output/                 # Renderer Layer
```

---

## 備註

- 此頁是「架構導讀版」，便於快速定位責任邊界。
- 任務拆分與完整重構清單，仍以 `doc/refactor/todo.md` 為準。
