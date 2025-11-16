@echo off
echo ========================================
echo IntelliFlow - Cleanup Script
echo ========================================
echo.
echo This will remove unnecessary files before moving to a new system.
echo.
echo Files to be removed:
echo   - Old documentation files
echo   - Runtime log files
echo   - Python cache
echo   - Old batch files
echo.
echo Large files (videos, models) will NOT be removed.
echo You can remove them manually if not needed.
echo.
pause

echo.
echo Removing old documentation files...
del /Q COMPLETE_ANSWER.md 2>nul
del /Q DEPLOYMENT_GUIDE.md 2>nul
del /Q TEST_CHECKLIST.md 2>nul
del /Q START_HERE.md 2>nul
del /Q PHONE_ACCESS_GUIDE.md 2>nul
del /Q MULTIPLE_TUNNELS_SOLUTION.md 2>nul
del /Q ml_model\README_SETUP.md 2>nul
del /Q ml_model\QUICKSTART.md 2>nul
del /Q ml_model\RUN_SYSTEM.md 2>nul

echo Removing runtime files...
del /Q ml_model\traffic_log.json 2>nul
del /Q ml_model\emergency_state.json 2>nul
rmdir /S /Q ml_model\__pycache__ 2>nul

echo Removing old batch files...
del /Q ml_model\activate_venv.bat 2>nul
del /Q ml_model\setup.bat 2>nul
del /Q ml_model\install_pytorch_cpu.bat 2>nul
del /Q ml_model\start_backend.bat 2>nul
del /Q ml_model\start_ml_system.bat 2>nul
del /Q start_ngrok.bat 2>nul

echo.
echo ========================================
echo Cleanup complete!
echo ========================================
echo.
echo Remaining files:
echo   - Essential code files
echo   - Configuration files
echo   - Main documentation (README.md, NEW_DEVICE_SETUP.md, etc.)
echo   - Video files (if present - remove manually if not needed)
echo   - Model files (if present - will auto-download on new system)
echo.
echo Next steps:
echo   1. Review CLEANUP_GUIDE.md for details
echo   2. If using Git: Push to repository
echo   3. If using ZIP: Compress the folder
echo   4. On new system: Follow NEW_DEVICE_SETUP.md
echo.
pause

