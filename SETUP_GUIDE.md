# 🚦 IntelliFlow - Complete Setup Guide

## 📋 Table of Contents
1. [How Arduino Communication Works](#arduino-communication)
2. [System Architecture](#system-architecture)
3. [Setup Order](#setup-order)
4. [Video Source Options](#video-sources)
5. [Moving to Another Machine](#moving-to-another-machine)

## 🔌 Arduino Communication Explained

### How It Works:

1. **Arduino Code Runs ONCE:**
   - Upload the Arduino code to your Arduino board using Arduino IDE
   - This code makes Arduino wait for commands via Serial (USB)
   - Arduino stays connected to computer via USB cable
   - Arduino code runs continuously, waiting for commands

2. **Python System Controls Arduino:**
   - Python script (`intelliflow_ml.py`) sends commands to Arduino via Serial port
   - Commands like `L1_G` (Lane 1 Green), `L2_R` (Lane 2 Red), etc.
   - Arduino receives commands and controls the LEDs
   - This happens automatically - no need to run Arduino IDE again

### Arduino Setup Steps:

1. **Upload Code to Arduino:**
   ```
   - Open Arduino IDE
   - Copy the Arduino code (provided)
   - Select your board (Arduino Mega/Uno)
   - Select COM port (e.g., COM11)
   - Click Upload
   - Arduino is now ready and waiting for commands
   ```

2. **Connect Hardware:**
   - Connect LEDs to Arduino pins:
     - Lane 1: Pins 22 (Red), 24 (Yellow), 26 (Green)
     - Lane 2: Pins 31 (Red), 33 (Yellow), 35 (Green)

3. **Configure Python:**
   - Edit `ml_model/config.py`:
     ```python
     ARDUINO_PORT = "COM11"  # Change to your COM port
     ARDUINO_BAUD_RATE = 9600
     ```

4. **Run Python System:**
   - Python automatically connects to Arduino
   - Sends traffic light commands automatically
   - Arduino controls LEDs based on commands

### Important Notes:
- ✅ Arduino code runs ONCE when uploaded
- ✅ Python script sends commands automatically
- ✅ Arduino and Python must stay connected via USB
- ✅ No need to run Arduino IDE after initial upload

---

## 🏗️ System Architecture

```
┌─────────────────┐
│  Video Sources  │
│  (Files/ESP32/  │
│   IP Webcam)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Python ML      │
│  System         │
│  (Vehicle       │
│   Detection)    │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌─────────┐ ┌──────────┐
│ Flask   │ │ Arduino  │
│ Backend │ │ Hardware │
│ (API)   │ │ (LEDs)   │
└────┬────┘ └──────────┘
     │
     ▼
┌──────────────┐
│ React        │
│ Frontend     │
│ (Dashboard)  │
└──────────────┘
```

---

## 🚀 Setup Order

### Step 1: Arduino Setup (One-time)
1. Upload Arduino code using Arduino IDE
2. Connect LEDs to Arduino pins
3. Keep Arduino connected to computer via USB
4. Note the COM port (e.g., COM11)

### Step 2: Python Backend Setup
1. Create virtual environment:
   ```bash
   cd ml_model
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure system:
   - Edit `ml_model/config.py`
   - Set video sources
   - Set Arduino COM port

### Step 3: Start Flask Backend
```bash
cd ml_model
.venv\Scripts\activate
python dashboard.py
```
Wait for: `🚀 IntelliFlow API Server running at http://127.0.0.1:5000`

### Step 4: Start ML System
```bash
# New terminal
cd ml_model
.venv\Scripts\activate
python intelliflow_ml.py
```
Wait for: `✅ Registered with web dashboard for video streaming`

### Step 5: Start React Frontend
```bash
# New terminal
cd eco-traffic-dash
npm install  # First time only
npm run dev
```

### Step 6: Open Browser
Go to: http://localhost:8080

---

## 📹 Video Source Options

All lane inputs are configured via `SYSTEM_MODE` in `ml_model/config.py`. Choose the mode that matches your hardware setup and update the supporting dictionaries.

```python
# Pick one
SYSTEM_MODE = "TWO_VIDEO"   # Other choices: "FOUR_VIDEO", "TWO_ESP32", "TWO_IP", "TWO_MIXED", "FOUR_HYBRID"

VIDEO_FILES = {
    "North": "vid1.mp4",
    "South": "vid3.mp4",
    "East": "vid2.mp4",
    "West": "vid4.mp4",
}

ESP32_CAMERAS = {
    "North": {"ip": "192.168.1.100", "stream": "/stream"},
    "South": {"ip": "192.168.1.101", "stream": "/stream"},
    "East": {"ip": "192.168.1.102", "stream": "/stream"},
    "West": {"ip": "192.168.1.103", "stream": "/stream"},
}

IP_WEBCAMS = {
    "North": "http://192.168.1.50:8080/video",
    "South": "http://192.168.1.51:8080/video",
    "East": "http://192.168.1.52:8080/video",
    "West": "http://192.168.1.53:8080/video",
}
```

- `FOUR_VIDEO`: four independent files (`VIDEO_FILES` North/South/East/West)
- `TWO_VIDEO`: legacy two-video workflow (`VIDEO_FILES` North + East)
- `TWO_ESP32`: two ESP32-CAM streams (`ESP32_CAMERAS` North + East)
- `TWO_IP`: two IP webcam URLs (`IP_WEBCAMS` North + East)
- `TWO_MIXED`: North IP webcam + East ESP32-CAM
- `FOUR_HYBRID`: IP webcams for North/South and ESP32-CAM for East/West

Update the relevant dictionary entries before switching `SYSTEM_MODE`. The React dashboard automatically adjusts to display two or four feeds based on the selected mode.

---

## 🖥️ Moving to Another Machine

### What to Change:

#### 1. Python Virtual Environment
**MUST recreate:**
```bash
cd ml_model
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```
**Why?** Virtual environments are machine-specific.

#### 2. Configuration File
**MUST update `ml_model/config.py`:**
- Video file paths (if using files)
- ESP32-CAM IP addresses (if using ESP32)
- IP Webcam URLs (if using IP Webcam)
- Arduino COM port (varies by machine)
- Webcam indices (if using webcams)

#### 3. Video Files
**Copy video files to new machine:**
- Copy video files to `ml_model/` folder
- Update paths in `config.py` if needed

#### 4. Arduino
**Reconnect:**
- Connect Arduino to new machine via USB
- Find new COM port in Device Manager
- Update `ARDUINO_PORT` in `config.py`
- **NO need to re-upload Arduino code** (unless changing pins)

#### 5. Node.js Dependencies
**Reinstall:**
```bash
cd eco-traffic-dash
npm install
```
**Why?** `node_modules` can be machine-specific.

#### 6. Paths
**Check these paths:**
- Video file paths in `config.py`
- Model file path (`yolov8n.pt` - will download automatically if missing)

### Checklist for New Machine:
- [ ] Install Python 3.8+
- [ ] Install Node.js 16+
- [ ] Create new virtual environment
- [ ] Install Python dependencies
- [ ] Install Node.js dependencies
- [ ] Update `config.py` with new settings
- [ ] Copy video files (if using)
- [ ] Connect Arduino and update COM port
- [ ] Test ESP32-CAM/IP Webcam connectivity (if using)

### What You DON'T Need to Change:
- ✅ Arduino code (unless changing hardware)
- ✅ Python source code
- ✅ React source code
- ✅ Project structure

---

## 🔧 Quick Reference

### Find Arduino COM Port:
- **Windows:** Device Manager → Ports (COM & LPT)
- **Linux:** `ls /dev/ttyUSB*` or `ls /dev/ttyACM*`
- **Mac:** `ls /dev/tty.usbserial*` or `ls /dev/tty.usbmodem*`

### Test Arduino Connection:
```bash
python ml_model/test_arduino_connection.py
```

### Test Video Sources:
```python
import cv2
cap = cv2.VideoCapture("your_source")  # File path, IP, or camera index
print("Working!" if cap.isOpened() else "Failed!")
cap.release()
```

---

## 📞 Troubleshooting

### Arduino Not Responding:
1. Check COM port in Device Manager
2. Update `ARDUINO_PORT` in `config.py`
3. Make sure Arduino is connected via USB
4. Check baud rate matches (9600)

### Videos Not Loading:
1. Check file paths in `config.py`
2. Verify files exist in `ml_model/` folder
3. For ESP32/IP Webcam: Check IP addresses and network connectivity
4. For webcams: Try different camera indices (0, 1, 2, etc.)

### Dashboard Not Showing:
1. Make sure Flask backend is running
2. Make sure ML system is running
3. Check browser console for errors
4. Verify API is accessible: http://127.0.0.1:5000/api/data

---

## ✅ Summary

**Arduino:**
- Upload code ONCE using Arduino IDE
- Python sends commands automatically via Serial
- Arduino controls LEDs based on commands

**Setup Order:**
1. Arduino (one-time setup)
2. Python backend
3. Flask server
4. ML system
5. React frontend

**Moving to New Machine:**
- Recreate virtual environment
- Update `config.py`
- Reinstall Node.js dependencies
- Update COM port and paths

**That's it!** 🎉


