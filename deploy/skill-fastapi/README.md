# ZenTable Skill FastAPI Docker（雙服務）

此部署提供 skill 常用的兩個 FastAPI：

1. `zentable-css-api`：HTML -> PNG（Headless Chrome）
2. `zentable-ocr-api`：OCR（OpenVINO route, unified OCR API）

## 檔案

- `docker-compose.yml`
- `Dockerfile.css-api`
- `.env.example`

## 快速啟動

```bash
cd /var/www/html/zenTable/deploy/skill-fastapi
cp .env.example .env

docker compose up -d --build
```

## 預設 Port

- CSS API: `http://127.0.0.1:8002`
- OCR API: `http://127.0.0.1:8001`

## 健康檢查

```bash
curl http://127.0.0.1:8002/health
curl http://127.0.0.1:8001/health
```

## CSS API 測試

```bash
curl -X POST http://127.0.0.1:8002/render/html \
  -H 'Content-Type: application/json' \
  -d '{"html":"<html><body><h1>Hello</h1></body></html>","viewport_width":800,"viewport_height":300}' \
  --output /tmp/css_api_test.png
```

## Rollback

```bash
cd /var/www/html/zenTable/deploy/skill-fastapi
docker compose down
# optional: remove local images
# docker image rm skill-fastapi-zentable-css-api skill-fastapi-zentable-ocr-api
```

## 依賴拆分（為何不用單一 requirements.txt）

- `requirements-css-api.txt`：只給 CSS Render API
- `requirements-openvino.txt`：OCR OpenVINO API 依賴（由 `Dockerfile.openvino` 使用）

好處：
- 映像體積較小
- 降低相依衝突（尤其 OCR 加速棧）
- 服務可獨立升級/回滾
