# Paddle Table + OCR Integration Handoff (for Cursor)

Last updated: 2026-02-27
Owner: con2000us / OpenClaw session handoff

---

## 1) Current status

Integration is at **PoC usable** stage.

Working pipeline:
1. Paddle Table API detects multi-table regions (`tables[]`, `bbox`)
2. Hybrid extractor re-reads text with OpenVINO OCR
3. Normalize rows into rectangular arrays
4. Optional merge (default OFF)

Verified on sample class schedule image:
- Paddle table detects `2` tables
- BBox example:
  - `[44, 183, 1118, 430]`
  - `[222, 454, 948, 703]`

---

## 2) Key directories / files

Project root:
- `/var/www/html/zenTable`

Paddle table service:
- `/var/www/html/zenTable/deploy/paddle-table/docker-compose.yml`
- `/var/www/html/zenTable/deploy/paddle-table/Dockerfile`
- `/var/www/html/zenTable/deploy/paddle-table/requirements.txt`
- `/var/www/html/zenTable/deploy/paddle-table/api/paddle_table_service.py`
- `/var/www/html/zenTable/deploy/paddle-table/README.md`

Hybrid + post-processing tools:
- `/var/www/html/zenTable/deploy/paddle-table/table_hybrid_extract.py`
- `/var/www/html/zenTable/deploy/paddle-table/normalize_rows.py`
- `/var/www/html/zenTable/deploy/paddle-table/merge_tables.py`

Related OpenVINO OCR API:
- `/var/www/html/zenTable/api/ocr_openvino_service.py`

---

## 3) API endpoints

### Paddle Table API
Service port mapping: `8012 -> 8010`

- `GET /health`
- `POST /table-parse`
- `POST /table-parse?debug=true` (returns timing/debug block)

### OpenVINO OCR API (already exists)
- Typically `http://127.0.0.1:8011/ocr`
- Supports `?debug=true` timing/debug in current implementation

---

## 4) Commands (known good)

### Start Paddle Table service
```bash
cd /var/www/html/zenTable/deploy/paddle-table
docker compose up -d --build
curl http://127.0.0.1:8012/health
```

### Parse table image
```bash
curl -s -X POST http://127.0.0.1:8012/table-parse \
  -F "image=@/home/minecraft/.openclaw/media/inbound/a8cd7a76-0074-4ac7-9a8f-eef4e81d0d06.jpg" \
  > /tmp/table_parse_result.json

jq '.success, .elapsed_ms, (.tables|length)' /tmp/table_parse_result.json
jq '.tables[].bbox' /tmp/table_parse_result.json
```

### Hybrid extraction (Paddle structure + OpenVINO text)
```bash
python3 /var/www/html/zenTable/deploy/paddle-table/table_hybrid_extract.py \
  --image /home/minecraft/.openclaw/media/inbound/a8cd7a76-0074-4ac7-9a8f-eef4e81d0d06.jpg \
  --parse-json /tmp/table_parse_result.json \
  --out /tmp/hybrid_table_v01.json
```

### Normalize rows
```bash
python3 /var/www/html/zenTable/deploy/paddle-table/normalize_rows.py \
  --in /tmp/hybrid_table_v01.json \
  --out /tmp/hybrid_table_norm.json

jq '.tables[] | {table_index,row_count,col_count}' /tmp/hybrid_table_norm.json
```

### Optional merge
```bash
python3 /var/www/html/zenTable/deploy/paddle-table/merge_tables.py \
  --in /tmp/hybrid_table_norm.json \
  --out /tmp/hybrid_table_merged.json \
  --merge true \
  --merge-mode normalized

jq '{merge_enabled, merge_mode, merged_rows:(.merged_table.rows|length)}' /tmp/hybrid_table_merged.json
```

---

## 5) Important implementation notes

## SIGILL mitigation (critical)
Paddle init had CPU illegal-instruction failures before. Current service uses safer params:
- `ir_optim=False`
- `enable_mkldnn=False`
- `cpu_threads=4`
- `ocr_version="PP-OCRv2"`
- `rec_algorithm="CRNN"`

## JSON serialization fix
Paddle raw outputs include numpy types. Service now sanitizes to JSON-safe via `_to_jsonable()`.

## Debug/timing blocks
Both OCR and table parse now support `debug=true` and include timing.

---

## 6) Known limitations

1. `cell_boxes` can be missing even when table HTML exists.
   - This is why hybrid extractor includes `bbox_fallback` mode.

2. Current v0.1 does **not** reliably infer rowspan/colspan semantics.
   - It focuses on usable extraction + normalization.

3. Per-cell OCR mode can be slower; fallback mode is faster but less structurally precise.

4. Merged output currently favors safety:
   - default `--merge false`
   - `normalized` merge mode preferred

---

## 7) Suggested next steps for Cursor

1. **Unify response schema** across css-render / OCR / Paddle-table:
   - `success`, `data`, `timing.total_ms`, `timing.stages`, `debug`

2. Improve hybrid quality:
   - Add confidence scoring per row/cell
   - Better row clustering thresholds (dynamic by font/height)

3. Add span inference module (future):
   - line-gap geometry + structure hints
   - optional `rowspan/colspan` output

4. Add `debug visualization` endpoint/tool:
   - render image with table bboxes + OCR boxes overlay

5. Add benchmark script:
   - compare OpenVINO OCR only vs Paddle table + hybrid pipeline

---

## 8) Recent commits (reference)

- `0443286` feat(deploy): standalone paddle-table docker service
- `428bdaa` fix(paddle-table): safer CPU inference path to avoid SIGILL
- `e5910d7` fix(paddle-table): sanitize numpy outputs for JSON
- `4a2c614` feat: hybrid extractor (Paddle structure + OpenVINO text)
- `251e938` feat(hybrid v0.1): bbox fallback + row clustering
- `c760680` fix(hybrid): explicit image/png multipart to OCR API
- `5221d5f` feat: normalize_rows tool
- `254ba5b` feat: merge_tables tool (safe default)
- `cb5ab2d` feat(debug): timing/debug response blocks

---

## 9) Handoff summary

Current pipeline is good enough for iterative development and practical tests.
Not final-production yet, but architecture direction is correct:
- Paddle for table structure
- OpenVINO for OCR text quality
- normalization/merge as explicit post-processing stages
