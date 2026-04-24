# Cloudflare Tunnel Quickstart (Windows)

Expose your local FastAPI backend to the internet quickly via Cloudflare Tunnel.

Prereqs
- A Cloudflare account and a domain managed by Cloudflare (for the DNS option)
- Windows 10/11 with PowerShell

Install Cloudflared
- `winget install Cloudflare.cloudflared`

Run the Backend
- `cd backend`
- `py -3 -m venv .venv`
- `..venv\Scripts\Activate.ps1` (if blocked, run: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`)
- `pip install -r requirements.txt`
- `.\u005crun_uvicorn.ps1` (serves http://localhost:8000)

Option A: Instant demo (no DNS)
- Open a new terminal: `cloudflared tunnel --url http://localhost:8000`
- Use the printed `https://<random>.trycloudflare.com` URL to access the app.

Option B: Named tunnel + DNS (recommended)
- Login: `cloudflared tunnel login`
- Create: `cloudflared tunnel create pest-backend`
- Map DNS: `cloudflared tunnel route dns pest-backend api.your-domain.com`
- Create config: `C:\Users\<you>\.cloudflared\config.yml`
  - Copy from `cloudflared.config.yml.template` and set:
    - `tunnel: pest-backend`
    - `credentials-file: C:\\Users\\<you>\\.cloudflared\\pest-backend.json`
    - `ingress: [{ hostname: api.your-domain.com, service: http://localhost:8000 }, { service: http_status:404 }]`
- Run: `cloudflared tunnel run pest-backend`
- Visit: `https://api.your-domain.com`

Notes
- When you open the backend via the Tunnel URL or your DNS hostname, no extra CORS settings are needed (same-origin).
- If a separate frontend domain is used, set `APP_ALLOWED_ORIGINS` accordingly before launching Uvicorn.
- Avoid forcing HTTPS (`APP_FORCE_HTTPS=true`) for quick demos; Cloudflared already terminates TLS.

---

# Cloudflare Tunnel 部署教學（Windows）

安裝
- 安裝 Cloudflared：`winget install Cloudflare.cloudflared`

啟動後端
- `cd backend`
- `py -3 -m venv .venv`
- `..venv\Scripts\Activate.ps1`（若被阻擋，執行：`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`）
- `pip install -r requirements.txt`
- `.run_uvicorn.ps1`（本機服務 http://localhost:8000）

快速公開（無需 DNS）
- 新開一個終端：`cloudflared tunnel --url http://localhost:8000`
- 使用顯示的 `https://<random>.trycloudflare.com` 連結存取

命名 Tunnel + DNS（建議）
- 登入：`cloudflared tunnel login`
- 建立：`cloudflared tunnel create pest-backend`
- 路由：`cloudflared tunnel route dns pest-backend api.你的網域.com`
- 設定檔：建立 `C:\Users\<you>\.cloudflared\config.yml`，內容可由 `cloudflared.config.yml.template` 複製並調整
- 執行：`cloudflared tunnel run pest-backend`
- 造訪：`https://api.你的網域.com`

備註
- 直接透過 Tunnel URL / DNS 主機名開啟後端頁面，無須額外 CORS 設定。
- 若前端不同網域，請在啟動前設定 `APP_ALLOWED_ORIGINS`。
