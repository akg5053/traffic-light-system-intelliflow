@echo off
echo ========================================
echo IntelliFlow - Cloudflare Tunnel Starter
echo ========================================
echo.
echo This will start Cloudflare tunnels for:
echo   - Flask Backend (port 5000)
echo   - Next.js EVP Remote App (port 3000)
echo.
echo Checking for cloudflared...
if exist "cloudflared.exe" (
    set CLOUDFLARED_CMD=cloudflared.exe
    echo Found cloudflared.exe in current directory!
) else (
    where cloudflared >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        set CLOUDFLARED_CMD=cloudflared
        echo Found cloudflared in PATH!
    ) else (
        echo.
        echo cloudflared not found!
        echo.
        echo Please either:
        echo   1. Download cloudflared-windows-amd64.exe from:
        echo      https://github.com/cloudflare/cloudflared/releases
        echo   2. Rename it to cloudflared.exe
        echo   3. Place it in this folder
        echo.
        pause
        exit /b 1
    )
)
echo.
echo Starting tunnels...
echo.
pause

REM Change localhost (127.0.0.1) to 0.0.0.0 (all interfaces)

echo.
echo Starting Flask Backend tunnel (port 5000)...
start "Flask Cloudflare" cmd /k "title Flask Cloudflare (port 5000) && cd /d %~dp0 && %CLOUDFLARED_CMD% tunnel --url http://0.0.0.0:5000"
timeout /t 3

echo.
echo Starting Next.js App tunnel (port 3000)...
start "Next.js Cloudflare" cmd /k "title Next.js Cloudflare (port 3000) && cd /d %~dp0 && %CLOUDFLARED_CMD% tunnel --url http://0.0.0.0:3000"
timeout /t 2

echo.
echo ========================================
echo Cloudflare tunnels started!
echo ========================================
echo.
echo IMPORTANT: Copy the URLs from the Cloudflare windows:
echo   - Flask: https://xxxx.trycloudflare.com (port 5000)
echo   - Next.js: https://yyyy.trycloudflare.com (port 3000)
echo.
echo Then update:
echo   1. evp-remote/.env.local: NEXT_PUBLIC_API_URL=https://xxxx.trycloudflare.com
echo   2. eco-traffic-dash/.env.local: VITE_API_URL=https://xxxx.trycloudflare.com
echo   3. Restart apps after updating .env files
echo.
echo Press any key to exit...
pause >nul

