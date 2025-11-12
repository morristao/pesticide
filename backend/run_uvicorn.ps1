$MODULE_PATH = if ($env:MODULE_PATH) { $env:MODULE_PATH } else { "app.main:app" }
$PORT = if ($env:PORT) { $env:PORT } else { 8000 }

if (-not $env:PYTHONPATH) {
    $env:PYTHONPATH = (Get-Location)
}

python -m uvicorn $MODULE_PATH `
    --host 0.0.0.0 `
    --port $PORT `
    --proxy-headers `
    --forwarded-allow-ips="*"
