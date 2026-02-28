# 歸檔文件

此目錄存放已不再主動維護、僅供參考的歷史文件。

- 回到主文件入口：[`../README.md`](../README.md)
- 回到分類總表：[`../DOCS_INDEX.md`](../DOCS_INDEX.md)

## 一般歸檔

| 檔案 | 說明 |
|------|------|
| PLAN_COMPLETED_AND_CALL_GRAPH.md | 過往計畫完成清單與調用關係圖；部分路徑與流程可能與現況不同。 |
| ZEBLE_FLOW.md | 舊版流程圖，含已淘汰入口（如 `gentable_*` / 舊路徑命名），僅供歷史參考。 |
| INTEGRATION.md | 早期整合示例草稿，含過時呼叫方式與示意程式碼。 |

## deprecated_code/

| 檔案 | 原位置 | 說明 |
|---|---|---|
| `zeble.py` | `scripts/zeble.py` | legacy PIL 渲染入口（已棄用並封存） |
| `doc_zeble.py` | `doc/zeble.py` | 文件目錄中的舊版副本 |
| `zeble_render.py` | `doc/zeble_render.py` | 舊版 render 主流程快照 |
| `zentable_render.py` | `doc/zentable_render.py` | 早期版本快照 |
| `table_detect.py` | `doc/table_detect.py` | 舊版 table detect 腳本 |
| `smart_table_output.py` | `doc/smart_table_output.py` | 一次性實驗腳本（含過時依賴） |
| `reproduce_issue.py` | `doc/reproduce_issue.py` | 問題重現小工具 |
| `gen_test_data.py` | `doc/gen_test_data.py` | 測試資料產生小工具 |
