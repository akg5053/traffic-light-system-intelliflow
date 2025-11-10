# IntelliFlow Troubleshooting Guide

## PyTorch DLL Error (Windows)

If you see this error:
```
OSError: [WinError 1114] A dynamic link library (DLL) initialization routine failed
```

### Solution 1: Install Visual C++ Redistributables

PyTorch requires Visual C++ Redistributables. Download and install:

**For Windows:**
- [Microsoft Visual C++ Redistributable for Visual Studio 2015-2022](https://aka.ms/vs/17/release/vc_redist.x64.exe)

After installing, restart your computer and try again.

### Solution 2: Reinstall PyTorch

```bash
.venv\Scripts\activate
pip uninstall torch torchvision
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### Solution 3: Use CPU-only PyTorch

If GPU is not needed, install CPU-only version:

```bash
.venv\Scripts\activate
pip uninstall torch torchvision
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### Solution 4: Check System Requirements

- Windows 10/11 (64-bit)
- Python 3.8-3.12
- At least 4GB RAM
- Visual C++ Redistributables installed

## Common Issues

### 1. Virtual Environment Not Activating

**Problem:** `'venv' is not recognized as an internal or external command`

**Solution:**
```bash
# Use full path
.venv\Scripts\activate.bat

# Or use Python's venv module
python -m venv .venv
```

### 2. Dependencies Won't Install

**Problem:** `pip install` fails or times out

**Solutions:**
- Check internet connection
- Upgrade pip: `python -m pip install --upgrade pip`
- Use timeout: `pip install --default-timeout=100 -r requirements.txt`
- Try installing individually: `pip install ultralytics`

### 3. Camera Not Working

**Problem:** `Failed to connect to camera`

**Solutions:**
- Check camera permissions in Windows Settings
- Try different camera indices (0, 1, 2, etc.)
- For video files, verify file path is correct
- Test with: `python -c "import cv2; cap = cv2.VideoCapture(0); print('Camera works!' if cap.isOpened() else 'Camera not found')"`

### 4. Arduino Not Connecting

**Problem:** `Arduino not connected` or serial port error

**Solutions:**
- Check COM port in Device Manager (Windows)
- Update COM port in `intelliflow_ml.py`: `serial.Serial('COM11', 9600)`
- Verify Arduino is connected via USB
- Check baud rate matches (9600)
- Install Arduino drivers if needed

### 5. Dashboard Not Loading

**Problem:** React frontend can't connect to backend

**Solutions:**
- Ensure Flask backend is running: `python dashboard.py`
- Check backend is on `http://127.0.0.1:5000`
- Verify CORS is enabled in `dashboard.py`
- Check browser console for errors
- Try accessing API directly: `http://127.0.0.1:5000/api/data`

### 6. Module Not Found Errors

**Problem:** `ModuleNotFoundError: No module named 'X'`

**Solutions:**
- Activate virtual environment: `.venv\Scripts\activate`
- Install missing module: `pip install X`
- Verify installation: `pip list | findstr X`
- Reinstall all: `pip install -r requirements.txt --force-reinstall`

## Testing Installation

### Test 1: Core Dependencies
```bash
.venv\Scripts\activate
python -c "import flask, cv2, numpy, serial; print('✅ Core dependencies OK')"
```

### Test 2: ML Dependencies (may fail due to PyTorch DLL issue)
```bash
.venv\Scripts\activate
python -c "import ultralytics; print('✅ ML dependencies OK')"
```

### Test 3: Flask Backend
```bash
.venv\Scripts\activate
python dashboard.py
# Should see: "🚀 IntelliFlow API Server running at http://127.0.0.1:5000"
```

### Test 4: Camera Access
```bash
.venv\Scripts\activate
python -c "import cv2; cap = cv2.VideoCapture(0); print('Camera works!' if cap.isOpened() else 'Camera issue'); cap.release()"
```

## Getting Help

If issues persist:
1. Check Python version: `python --version` (should be 3.8-3.12)
2. Check pip version: `pip --version`
3. Check installed packages: `pip list`
4. Review error messages carefully
5. Check Windows Event Viewer for system errors

## Alternative: Use Docker (Advanced)

If Windows issues persist, consider using Docker:

```bash
# Create Dockerfile
# Build: docker build -t intelliflow .
# Run: docker run -p 5000:5000 intelliflow
```

## System Requirements Checklist

- [ ] Python 3.8-3.12 installed
- [ ] Virtual environment created (`.venv` folder exists)
- [ ] All dependencies installed (`pip list` shows packages)
- [ ] Visual C++ Redistributables installed (for PyTorch)
- [ ] Camera/webcam connected and working
- [ ] Arduino connected (if using hardware)
- [ ] Port 5000 available (for Flask)
- [ ] Port 8080 available (for React frontend)



