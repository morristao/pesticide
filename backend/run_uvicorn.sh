#!/usr/bin/env bash
set -euo pipefail

MODULE_PATH=${MODULE_PATH:-app.main:app}
HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8000}

export PYTHONPATH=${PYTHONPATH:-$PWD}

uvicorn "$MODULE_PATH" \
  --host "$HOST" \
  --port "$PORT" \
  --proxy-headers \
  --forwarded-allow-ips="*"
