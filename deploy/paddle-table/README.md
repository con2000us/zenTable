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

## Notes

- This service is independent from existing OCR services (safe A/B testing).
- Output includes `tables[]` with `bbox`, `html`, and raw block data.
- Keep as experimental branch first; promote to main only after stability checks.
