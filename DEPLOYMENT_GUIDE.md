# 🚚 IntelliFlow - Deployment Guide

## Moving Project to Another Machine

### Quick Checklist:
1. ✅ Copy entire project folder
2. ✅ Recreate Python virtual environment
3. ✅ Reinstall Python dependencies
4. ✅ Reinstall Node.js dependencies
5. ✅ Update `config.py` with new settings
6. ✅ Connect Arduino and update COM port

---

## Step-by-Step Instructions

### 1. Copy Project Files
Copy the entire `IntelliFlow` folder to the new machine:
```
IntelliFlow/
├── ml_model/
│   ├── .venv/          ← DELETE THIS (will recreate)
│   ├── config.py       ← UPDATE THIS
│   ├── *.py files
│   └── video files
└── eco-traffic-dash/
    ├── node_modules/   ← DELETE THIS (will reinstall)
    └── src/
```

### 2. Python Setup (New Machine)

#### A. Create Virtual Environment
```bash
cd ml_model
python -m venv .venv

# Windows:
.venv\Scripts\activate

# Linux/Mac:
source .venv/bin/activate
```

#### B. Install Dependencies
```bash
pip install -r requirements.txt
```

#### C. Verify Installation
```bash
python -c "import ultralytics, cv2, flask; print('✅ All dependencies installed!')"
```

### 3. Update Configuration

Edit `ml_model/config.py`:

#### Video Sources:
```python
# Option 1: Video Files
USE_VIDEO_FILES = True
NORTH_VIDEO_FILE = "path/to/video1.mp4"  # Update path
EAST_VIDEO_FILE = "path/to/video2.mp4"   # Update path

# Option 2: ESP32-CAM
USE_VIDEO_FILES = False
NORTH_ESP32_IP = "192.168.1.100"  # Update IP
EAST_ESP32_IP = "192.168.1.101"   # Update IP

# Option 3: IP Webcam
USE_VIDEO_FILES = False
NORTH_IP_WEBCAM_URL = "http://192.168.1.50:8080/video"  # Update URL
EAST_IP_WEBCAM_URL = "http://192.168.1.51:8080/video"   # Update URL

# Option 4: Webcams
USE_VIDEO_FILES = False
NORTH_WEBCAM_INDEX = 0  # Update index
EAST_WEBCAM_INDEX = 1   # Update index
```

#### Arduino:
```python
# Find COM port on new machine:
# Windows: Device Manager → Ports (COM & LPT)
# Linux: ls /dev/ttyUSB* or ls /dev/ttyACM*
# Mac: ls /dev/tty.usbserial* or ls /dev/tty.usbmodem*

ARDUINO_PORT = "COM11"  # UPDATE THIS
ARDUINO_BAUD_RATE = 9600
```

### 4. Node.js Setup (New Machine)

```bash
cd eco-traffic-dash

# Delete old node_modules (if exists)
rm -rf node_modules  # Linux/Mac
# or
rmdir /s node_modules  # Windows

# Install dependencies
npm install
```

### 5. Copy Video Files (If Using)

Copy video files to `ml_model/` folder and update paths in `config.py`.

### 6. Arduino Setup (New Machine)

#### A. Connect Arduino
- Connect Arduino to new machine via USB
- Find COM port in Device Manager

#### B. Upload Code (If Needed)
- Open Arduino IDE
- Upload the Arduino code
- **Note:** You only need to upload if changing hardware pins

#### C. Update Config
- Update `ARDUINO_PORT` in `config.py`

### 7. Test Everything

#### Test Python:
```bash
cd ml_model
.venv\Scripts\activate
python -c "import intelliflow_ml; print('✅ Python OK')"
```

#### Test Flask:
```bash
python dashboard.py
# Should see: "🚀 IntelliFlow API Server running"
```

#### Test React:
```bash
cd eco-traffic-dash
npm run dev
# Should see: "Local: http://localhost:8080"
```

---

## What Changes vs What Stays

### ✅ Must Change:
- Virtual environment (recreate)
- Node modules (reinstall)
- `config.py` (update paths, COM port, IPs)
- Video file paths (if using files)
- ESP32-CAM IPs (if using ESP32)
- IP Webcam URLs (if using IP Webcam)
- Arduino COM port

### ❌ Don't Change:
- Python source code
- React source code
- Arduino code (unless changing hardware)
- Project structure

---

## Common Issues

### Issue: "Module not found"
**Solution:** Recreate virtual environment and reinstall dependencies

### Issue: "COM port not found"
**Solution:** 
- Check Device Manager for COM port
- Update `ARDUINO_PORT` in `config.py`
- Make sure Arduino is connected

### Issue: "Video file not found"
**Solution:**
- Copy video files to `ml_model/` folder
- Update paths in `config.py`
- Use absolute paths if needed

### Issue: "ESP32-CAM not connecting"
**Solution:**
- Check ESP32-CAM is on same network
- Verify IP address is correct
- Test in browser: `http://ESP32_IP/stream`

### Issue: "Node modules errors"
**Solution:**
- Delete `node_modules` folder
- Delete `package-lock.json`
- Run `npm install` again

---

## Quick Start on New Machine

```bash
# 1. Python setup
cd ml_model
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 2. Update config.py
# Edit ARDUINO_PORT, video sources, etc.

# 3. Node.js setup
cd ../eco-traffic-dash
npm install

# 4. Start system
# Terminal 1:
cd ml_model
.venv\Scripts\activate
python dashboard.py

# Terminal 2:
cd ml_model
.venv\Scripts\activate
python intelliflow_ml.py

# Terminal 3:
cd eco-traffic-dash
npm run dev
```

---

## File Structure (What to Copy)

```
IntelliFlow/
├── ml_model/
│   ├── *.py              ← Copy
│   ├── config.py         ← Copy (then update)
│   ├── requirements.txt  ← Copy
│   ├── yolov8n.pt       ← Copy (or will download)
│   ├── *.mp4            ← Copy (if using videos)
│   └── .venv/           ← DON'T COPY (recreate)
├── eco-traffic-dash/
│   ├── src/             ← Copy
│   ├── package.json     ← Copy
│   └── node_modules/    ← DON'T COPY (reinstall)
└── README.md            ← Copy
```

---

## Summary

**On New Machine:**
1. Copy project (except `.venv` and `node_modules`)
2. Recreate virtual environment
3. Reinstall dependencies
4. Update `config.py`
5. Connect Arduino and update COM port
6. Test and run!

**That's it!** 🎉


