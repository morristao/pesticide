#!/usr/bin/env bash
set -euo pipefail

HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8443}
APP_PATH=${APP_PATH:-app.main:app}

if [[ -z "${SSL_CERTFILE:-}" || -z "${SSL_KEYFILE:-}" ]]; then
  echo "SSL_CERTFILE and SSL_KEYFILE environment variables must point to your certificate and key." >&2
  exit 1
fi

export PYTHONPATH=${PYTHONPATH:-$PWD}

exec uvicorn "${APP_PATH}" \
  --host "${HOST}" \
  --port "${PORT}" \
  --ssl-certfile "${SSL_CERTFILE}" \
  --ssl-keyfile "${SSL_KEYFILE}"
