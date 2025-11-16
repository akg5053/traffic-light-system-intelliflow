@echo off
echo ========================================
echo IntelliFlow - Git LFS Setup
echo ========================================
echo.
echo This will set up Git LFS to handle large files.
echo.
echo Prerequisites:
echo   1. Git LFS installed (download from https://git-lfs.github.com/)
echo   2. Git repository initialized
echo.
pause

echo.
echo Checking Git LFS installation...
git lfs version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Git LFS is not installed!
    echo.
    echo Please install Git LFS from: https://git-lfs.github.com/
    echo Or run: winget install Git.GitLFS
    echo.
    pause
    exit /b 1
)

echo Git LFS is installed!
echo.

echo Initializing Git LFS...
git lfs install

echo.
echo Tracking large files with Git LFS...
git lfs track "*.mp4"
git lfs track "*.avi"
git lfs track "*.mov"
git lfs track "*.mkv"
git lfs track "*.pt"
git lfs track "*.onnx"
git lfs track "*.exe"
git lfs track "cloudflared"
git lfs track "ngrok"
git lfs track "node_modules/**"
git lfs track ".venv/**"
git lfs track "venv/**"

echo.
echo Adding .gitattributes...
git add .gitattributes

echo.
echo ========================================
echo Git LFS setup complete!
echo ========================================
echo.
echo Next steps:
echo   1. Add your files: git add .
echo   2. Commit: git commit -m "Initial commit with LFS"
echo   3. Push: git push
echo.
echo Note: First push may take a while due to large files.
echo.
pause

