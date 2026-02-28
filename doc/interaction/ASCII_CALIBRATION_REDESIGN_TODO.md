# ASCII Calibration / Rendering Redesign TODO

> 狀態結論（目前）：ASCII 實作完程度不高，需重設里程碑。

## 背景與問題定義

- 現行「精細模型」已觀察到 bug（對齊漂移、平台差異擴大、空白折疊干擾）。
- 需要同時重設：
  1. 測量圖（校準基準圖）
  2. 模型（至少兩套：`space_collapse=true/false`）
  3. JSON 管理層（profile + merge + reset + active）

---

## A. 測量圖重設（Calibration Pattern Redesign）

- [ ] A1 定義新測量圖規格（不依賴連續半形空白）
- [ ] A2 拆分測量段：ASCII / CJK / box / emoji / full-space / symbols
- [ ] A3 定義 chat-safe 版（可見占位符）與 terminal 版（原生空白）
- [ ] A4 前端產生器支援新規格（參數化：repeat/chars_per_line/pattern）
- [ ] A5 分析器（`calibrate_analyze.py`）對應新測量圖解析邏輯

驗收：
- [ ] 在 Discord 手機可穩定還原測量段，不因空白折疊失效

---

## B. 模型重設（Two-Model Strategy）

- [ ] B1 定義 `space_collapse=false` 模型（精細）
- [ ] B2 定義 `space_collapse=true` 模型（受限）
- [ ] B3 兩模型共同輸入輸出介面（同一套 calibration schema）
- [ ] B4 padding solver（受限模型）加入誤差分配策略
- [ ] B5 文字寬計算拆分：ascii/cjk/box/emoji/custom/full_space

驗收：
- [ ] 同一份資料在兩模型各自環境中可重現對齊

---

## C. JSON 管理層（Profile Management）

- [ ] C1 profile 主鍵：`profile_name`（自訂）
- [ ] C2 預設命名：`<agent_name>-<platform>`
- [ ] C3 CRUD + set-active + reset API
- [ ] C4 merge 規則（base 覆蓋、custom key-merge）
- [ ] C5 metadata：platform / agent / space_collapse / notes / timestamps

驗收：
- [ ] 不同平台 profile 可獨立校準互不污染
- [ ] 同平台多次補測可累積 custom 字元

---

## D. 進度 Checklist（實作完成度追蹤）

### D1 基礎能力
- [ ] ASCII baseline table 在目標環境右框閉合
- [ ] Header/Body 對齊
- [ ] 無 emoji 情境穩定

### D2 擴展能力
- [ ] CJK 對齊可控（含常用 custom）
- [ ] box drawing 對齊穩定
- [ ] emoji 不破壞欄寬（或受控降級）

### D3 系統能力
- [ ] profile 切換可即時生效
- [ ] 匯入/匯出 calibration JSON
- [ ] reset 後可重測

### D4 品質閘門
- [ ] smoke 測試（兩模型）
- [ ] 平台回歸測試（至少 Discord mobile + desktop）
- [ ] 文件一致性（SKILL / doc / todo）

---

## 目前整體判定

- 目前 ASCII 功能 **可用但不穩定**（特定環境可對齊、跨環境容易漂移）
- 專案優先級應調整為：
  1. 測量圖重設
  2. 兩模型落地
  3. JSON 管理層完成
  4. 再做細節優化
