# ZenTable OCR FastAPI Docker 部署

此目錄提供把 `api/paddleocr_service.py` 打包成 Docker 的最小方案。

## 檔案

- `Dockerfile`
- `docker-compose.yml`
- `.env.example`

## 快速啟動

```bash
cd /var/www/html/zenTable/deploy/ocr-fastapi
cp .env.example .env

docker compose up -d --build
```

預設對外：`http://<host>:8001`

## 測試

```bash
curl http://127.0.0.1:8001/health
```

## API

- `POST /ocr`（multipart/form-data, 欄位 `image`）
- `POST /ocr/base64`

## iGPU 注意事項（Unraid）

1. 主機需有 `/dev/dri`。
2. compose 已掛 `devices: /dev/dri:/dev/dri`。
3. 若啟動失敗可先移除 `devices/group_add`，先跑 CPU 版本確認服務可用。

## 與既有 Nginx 整合

建議反代到 `127.0.0.1:8001`，例如 `/ocr-api/ -> http://127.0.0.1:8001/`。

## 備註

目前此包裝先以「可運行」為主（CPU 路線）。
若要進一步用 Intel iGPU/OpenVINO 加速，建議另做 `Dockerfile.openvino`。