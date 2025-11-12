## Pest & Disease Detection Web Service

Browser-based workflow for uploading crop images from remote locations, running selectable inference models, and visualizing JSON predictions. Backend uses FastAPI with a pluggable model registry, while static assets provide the UI. Requirements are tracked in `specs/pest-detection.openspec.yaml`.

### Quickstart (macOS/Linux)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then open `http://<server-ip>:8000` from any machine on the same network. CORS is open, so the API can be called programmatically as well.

### Quickstart (Windows 10/11)

```powershell
cd C:\Users\<you>\MyCode\pesticide\backend
py -3 -m venv .venv
.venv\Scripts\Activate.ps1   # 若遇到權限問題可先執行：Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
$env:PYTHONPATH = (Get-Location)
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

開啟 `http://127.0.0.1:8000`；若要讓同實驗室網段的其他裝置測試，改成 Windows 桌機的區網 IP。

### Secure Remote Access

1. Generate or provision a TLS certificate (self-signed example shown):
   ```bash
   mkdir -p backend/certs
   openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
     -keyout backend/certs/pesticide.key \
     -out backend/certs/pesticide.crt \
     -subj "/CN=$(hostname)"
   ```
2. Export environment hardening variables before starting the server:
   ```bash
   export APP_ALLOWED_ORIGINS="https://your.domain.com"
   export APP_TRUSTED_HOSTS="your.domain.com"
   export APP_FORCE_HTTPS=true
   export APP_ALLOW_CREDENTIALS=false
   ```
3. Launch the HTTPS server (listens on all interfaces by default):
   ```bash
   cd backend
   source .venv/bin/activate
   SSL_CERTFILE=$PWD/certs/pesticide.crt \
   SSL_KEYFILE=$PWD/certs/pesticide.key \
   bash run_secure.sh
   ```
   Windows (PowerShell)：
   ```powershell
   cd C:\Users\<you>\MyCode\pesticide\backend
   .venv\Scripts\Activate.ps1
   $env:SSL_CERTFILE = "$PWD\certs\pesticide.crt"
   $env:SSL_KEYFILE = "$PWD\certs\pesticide.key"
   bash run_secure.sh
   ```
4. Open firewall/router port `8443` and connect from outside using `https://<public-ip-or-domain>:8443`.

> `APP_ALLOWED_ORIGINS` and `APP_TRUSTED_HOSTS` accept comma-separated lists; set them to `"*"` only for trusted private networks.

### Adding New Models

1. Create a module under `backend/app/models/` that subclasses `BasePestModel` and exposes `metadata` plus an async `predict()` returning `Prediction`.
2. Register it inside `backend/app/models/__init__.py::load_models()`.
3. Restart the FastAPI service – the `/api/v1/models` endpoint and UI dropdown update automatically.

### Agent Handoff Notes

- 所有指令都假設目前工作目錄在 repo root (`MyCode/pesticide`)；Windows 版本沿用相同結構。
- 若在 Windows 實驗室桌機使用新的 agent，先說明 OS、Python 版本與 `.venv` 是否啟用，方便它延續工作。
- Secure 模式需要在 PowerShell 以 `$env:VAR=value` 設定 `APP_ALLOWED_ORIGINS`、`APP_TRUSTED_HOSTS`、`APP_FORCE_HTTPS`、`APP_ALLOW_CREDENTIALS` 以及 `SSL_CERTFILE`/`SSL_KEYFILE`。
