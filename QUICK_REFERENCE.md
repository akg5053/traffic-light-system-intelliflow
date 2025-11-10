# 🚦 IntelliFlow - Quick Reference

## 🎯 How Arduino Works (Simple Explanation)

1. **Upload Arduino code ONCE** using Arduino IDE
2. **Arduino stays connected** to computer via USB
3. **Python script sends commands** to Arduino automatically
4. **Arduino controls LEDs** based on commands
5. **NO need to run Arduino IDE** after initial upload

**Think of it like this:**
- Arduino = Remote control receiver (waiting for commands)
- Python = Remote control sender (sending commands)
- USB cable = Communication channel

## 🚀 Quick Start Order

1. **Arduino** (one-time): Upload code, connect LEDs, note COM port
2. **Flask Backend**: `python dashboard.py`
3. **ML System**: `python intelliflow_ml.py`
4. **React Frontend**: `npm run dev`
5. **Browser**: http://localhost:8080

## 📹 Video Source Options

Edit `ml_model/config.py`:

### Video Files:
```python
USE_VIDEO_FILES = True
NORTH_VIDEO_FILE = "video1.mp4"
EAST_VIDEO_FILE = "video2.mp4"
```

### ESP32-CAM:
```python
USE_VIDEO_FILES = False
NORTH_ESP32_IP = "192.168.1.100"
EAST_ESP32_IP = "192.168.1.101"
```

### IP Webcam (Android):
```python
USE_VIDEO_FILES = False
NORTH_IP_WEBCAM_URL = "http://192.168.1.50:8080/video"
EAST_IP_WEBCAM_URL = "http://192.168.1.51:8080/video"
```

### Webcams:
```python
USE_VIDEO_FILES = False
NORTH_WEBCAM_INDEX = 0
EAST_WEBCAM_INDEX = 1
```

## 🖥️ Moving to New Machine

1. Copy project (except `.venv` and `node_modules`)
2. Recreate virtual environment: `python -m venv .venv`
3. Install dependencies: `pip install -r requirements.txt`
4. Update `config.py`: COM port, video paths, IPs
5. Reinstall Node: `npm install`
6. Done!

See `DEPLOYMENT_GUIDE.md` for details.

## 🔧 Common Commands

```bash
# Python setup
cd ml_model
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Start Flask
python dashboard.py

# Start ML system
python intelliflow_ml.py

# Start React
cd ../eco-traffic-dash
npm install
npm run dev
```

## 📞 Quick Troubleshooting

**Arduino not working?**
- Check COM port in Device Manager
- Update `ARDUINO_PORT` in `config.py`
- Make sure Arduino is connected via USB

**Videos not loading?**
- Check file paths in `config.py`
- For ESP32/IP Webcam: Check IP addresses and network

**Dashboard not showing?**
- Make sure Flask backend is running
- Make sure ML system is running
- Check browser console for errors

## 📚 Full Documentation

- `SETUP_GUIDE.md` - Complete setup instructions
- `DEPLOYMENT_GUIDE.md` - Moving to new machine
- `README.md` - System overview


