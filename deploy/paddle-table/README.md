# Paddle Table Docker (PP-Structure)

Experimental table-structure parsing service for ZenTable.

## Start

```bash
cd /var/www/html/zenTable/deploy/paddle-table
docker compose up -d --build
```

## Health

```bash
curl http://127.0.0.1:8012/health
```

## Parse table

```bash
curl -s -X POST http://127.0.0.1:8012/table-parse \
  -F "image=@/path/to/table.jpg"
```

Debug mode (include stage timings and diagnostics):

```bash
curl -s -X POST "http://127.0.0.1:8012/table-parse?debug=true" \
  -F "image=@/path/to/table.jpg" | jq '.timing, .debug'
```

## Hybrid extraction (structure + OpenVINO OCR text)

After `table-parse`, you can re-read each table region with OpenVINO OCR:

```bash
python3 table_hybrid_extract.py \
  --image /home/minecraft/.openclaw/media/inbound/a8cd7a76-0074-4ac7-9a8f-eef4e81d0d06.jpg \
  --parse-json /tmp/table_parse_result.json \
  --out /tmp/hybrid_table.json
```

Then normalize rows into stable rectangular arrays:

```bash
python3 normalize_rows.py --in /tmp/hybrid_table.json --out /tmp/hybrid_table_norm.json
jq '.tables[] | {table_index,row_count,col_count}' /tmp/hybrid_table_norm.json
```

Optional merge step (default merge=false):

```bash
python3 merge_tables.py \
  --in /tmp/hybrid_table_norm.json \
  --out /tmp/hybrid_table_merged.json \
  --merge true \
  --merge-mode normalized

jq '{merge_enabled, merge_mode, merged_rows:(.merged_table.rows|length)}' /tmp/hybrid_table_merged.json
```

## Notes

- This service is independent from existing OCR services (safe A/B testing).
- Output includes `tables[]` with `bbox`, `html`, and raw block data.
- Keep as experimental branch first; promote to main only after stability checks.
