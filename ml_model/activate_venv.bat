@echo off
REM IntelliFlow - Activate Virtual Environment
echo Activating Python virtual environment...
call .venv\Scripts\activate.bat
echo ✅ Virtual environment activated!
echo.
echo You can now run:
echo   python dashboard.py      - Start the Flask backend server
echo   python intelliflow_ml.py - Start the ML traffic system
echo.
cmd /k



