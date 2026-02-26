# Theme Editing with Docker

When using Docker, keep themes outside image layers using volume mounts.

## Why

- Edit themes without rebuilding image
- Keep theme files persistent across container updates
- Easier sharing/export/import

## Example compose mount

```yaml
services:
  renderer:
    volumes:
      - ./themes:/app/themes
```

## Workflow

1. Edit files in host `./themes`
2. Renderer reads `/app/themes`
3. If cached, trigger reload endpoint or restart renderer container

## Suggested APIs (optional)

- `GET /theme/list`
- `POST /theme/save`
- `POST /theme/load`

Store all theme data in mounted volume to avoid data loss after image rebuild.
