@echo off
REM IntelliFlow - Start All Systems
echo ========================================
echo Starting IntelliFlow - All Systems
echo ========================================
echo.
echo NOTE: Flask server will start automatically within intelliflow_ml.py
echo You do NOT need to run dashboard.py separately anymore!
echo.
echo ========================================
echo.

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Start ML system (which will start Flask server internally)
echo Starting ML traffic detection system with integrated Flask server...
echo.
python intelliflow_ml.py

pause
