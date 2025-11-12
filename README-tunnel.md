# Cloudflare Tunnel 部署教學（零開孔 HTTPS）

## 前置
1. 申請 Cloudflare 帳號並將你的網域託管至 Cloudflare。
2. 安裝 cloudflared  
   - macOS: `brew install cloudflare/cloudflare/cloudflared`  
   - Windows: 下載官方執行檔或使用 `winget install Cloudflare.cloudflared`

## 建立與啟動 Tunnel
```bash
cloudflared tunnel login
cloudflared tunnel create pest-backend
# 將 cloudflared.config.yml.template 另存為 cloudflared/config.yml 並填入 hostname、credentials
cloudflared tunnel route dns pest-backend api.你的網域.com
cloudflared tunnel run pest-backend
```

## 啟動後端

### macOS/Linux
```bash
python -m pip install -r requirements.txt
./run_uvicorn.sh
```

### Windows（PowerShell）
```powershell
python -m pip install -r requirements.txt
./run_uvicorn.ps1
```

## 備註
- 後端仍在 `http://localhost:8000` 提供服務；Tunnel 會將 `https://api.你的網域.com` 的流量轉進來。
- 若前端位於不同網域，請在 `FRONTEND_ORIGIN` 或 `APP_ALLOWED_ORIGINS` 中加入對應網址，讓 CORS 放行。
- 需要上傳大檔時，可在 FastAPI 設定或 Cloudflare Tunnel 參數自行提高限制。
