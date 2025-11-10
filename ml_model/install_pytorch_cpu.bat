@echo off
REM IntelliFlow - Install CPU-only PyTorch (fixes DLL issues)
echo ========================================
echo Installing CPU-only PyTorch
echo This fixes common DLL errors on Windows
echo ========================================
echo.

call .venv\Scripts\activate.bat

echo Uninstalling existing PyTorch...
pip uninstall torch torchvision -y

echo.
echo Installing CPU-only PyTorch...
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

echo.
echo Testing installation...
python -c "import torch; print(f'✅ PyTorch {torch.__version__} installed successfully!')"

echo.
echo ========================================
echo ✅ Installation complete!
echo ========================================
pause



