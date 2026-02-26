# OCR Backends

Unified OCR API supports multiple inference backends under the same endpoints.

## Endpoint compatibility

All backends return the same JSON schema:

- `GET /health`
- `POST /ocr`
- `POST /ocr/base64`

## Select backend

Set by env var:

```env
OCR_BACKEND=auto|openvino|onnx|paddle
```

### auto mode (recommended)

Startup fallback order:

1. `openvino`
2. `onnx`
3. `paddle`

If one backend is unavailable, startup automatically falls back to the next.

## Direct tuning parameters (kept for paddle)

- `OCR_CPU_THREADS`
- `OCR_ENABLE_MKLDNN`
- `OCR_IR_OPTIM`
- `OCR_LANG`
- `USE_ANGLE_CLS`

## Practical recommendation

- For Intel hosts: prefer `openvino` or `auto`
- For broad compatibility: use `onnx`
- Keep `paddle` as compatibility fallback
