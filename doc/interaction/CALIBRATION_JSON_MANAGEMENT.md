# Calibration JSON Management（校準檔管理層）

> 本文件整理需求背景與管理規則，來源為近期討論結論。

## 為什麼需要管理層

校準 JSON 不能只靠單檔覆蓋，原因：

1. **跨平台字體差異**
   - 使用者可能在不同平台交錯使用 agent（手機/桌面/不同終端）
   - 各平台字型與渲染行為不同，校準結果通常不可互用

2. **同平台需多次補測**
   - 手機寬度有限，一次校準能覆蓋的字元數有限
   - 需要多次校準把 `custom` 字元逐步補齊

---

## 設計目標

1. **平台隔離**：不同平台可使用不同校準檔
2. **增量更新**：同平台可分次補測、合併到同一 profile
3. **可重測**：支援清零重測（reset）
4. **可辨識**：檔名/索引可追蹤 profile 與用途

---

## Profile 模型（最終決議）

### 主鍵

- 以 **`profile_name`（自訂名稱）** 為主鍵
- 平台不是唯一鍵，僅作 metadata

### 預設命名

- 若使用者未填 `profile_name`，自動命名：
  - `"<agent_name>-<platform>"`

### Metadata（建議）

- `profile_name`（唯一）
- `platform`（如 discord-mobile / terminal-macos）
- `agent_name`
- `note`（可選）
- `created_at`
- `updated_at`

---

## 操作語義

1. **Create profile**
   - 建立新 profile 與 JSON

2. **Update profile（增量合併）**
   - 同平台分次補測時使用
   - 合併規則：
     - 基礎鍵（`ascii/cjk/box/half_space/full_space/emoji`）以「本次值覆蓋」
     - `custom` 以 key merge（同 key 覆蓋，不同 key 保留）

3. **Reset profile**
   - 清空該 profile 校準資料並重新量測

4. **Switch active profile**
   - 每次渲染依 active profile 讀取校準 JSON

---

## 路徑與檔案（建議）

- `calibrate_data/records/<profile_name>.json`
- `calibrate_data/records/index.json`（profile 索引與 metadata）
- `calibrate_data/records/active.json`（當前 profile 指向）

---

## 待實作（TODO）

- [ ] 定義 profile CRUD API（list/get/create/update/reset/set-active）
- [ ] 定義 merge 行為與衝突策略（含 custom）
- [ ] 前端加 profile 選擇/建立/重設 UI
- [ ] 渲染路徑接入 active profile
- [ ] 補文件與驗收案例（跨平台切換、多次補測）
- [ ] 新增 `space_collapse` 環境欄位（true/false）並接入渲染策略
- [ ] 對接兩套模型（受限模型 / 精細模型）選擇機制

> 註：目前精細模型已有已知 bug，不能視為最終可用基線；需與測量圖重設、雙模型方案一起重構。

---

## 驗收重點

1. 同一使用者可建立多個 profile（同平台也可）
2. 不同 profile 互不覆蓋
3. 同 profile 多次補測後 `custom` 可累積
4. reset 後資料清零但 profile metadata 仍可保留
5. 未指定 profile 時可用預設命名策略建立
