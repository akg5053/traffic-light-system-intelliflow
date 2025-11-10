# 🚀 IntelliFlow - Quick Start Guide

## ✅ Everything is Ready!

**📖 IMPORTANT:** Read `SETUP_GUIDE.md` first for complete understanding of:
- How Arduino communication works
- System architecture
- Setup order
- Video source options (Files/ESP32-CAM/IP Webcam/Webcams)
- Moving to another machine

## Current Configuration:

Your system is configured via `ml_model/config.py`:
- **Video Source**: Video files (can be changed to ESP32-CAM, IP Webcam, or webcams)
- **North Lane Video**: `WhatsApp Video 2025-11-08 at 00.20.17_02904bca.mp4`
- **East Lane Video**: `WhatsApp Video 2025-11-08 at 00.20.17_269fdc46.mp4`
- **Arduino Port**: `COM11` (update in config.py)

## 🎬 How to Run

### Step 1: Start Flask Backend
```bash
cd ml_model
start_backend.bat
```
Wait for: `🚀 IntelliFlow API Server running at http://127.0.0.1:5000`

### Step 2: Start ML Detection System
```bash
# In a NEW terminal window
cd ml_model
start_ml_system.bat
```
Wait for: `✅ Registered with web dashboard for video streaming`

### Step 3: Start React Frontend
```bash
# In a NEW terminal window
cd eco-traffic-dash
npm install  # First time only
npm run dev
```

### Step 4: Open Browser
Go to: **http://localhost:8080**

## 🎥 What You'll See

### Web Dashboard Features:
- ✅ **Live Video Feeds**: Both North and East lane videos
- ✅ **Vehicle Detection Boxes**: Green boxes around ALL detected vehicles
- ✅ **Real-time Counts**: Vehicle count displayed on each video
- ✅ **Traffic Statistics**: Total vehicles, efficiency metrics
- ✅ **Charts**: Vehicle counts and efficiency over time
- ✅ **Traffic Light Status**: Current phase and active lane

### Key Features:
- 🎯 **Full Frame Detection**: Detects ALL vehicles in entire video (not just regions)
- 🔄 **Auto Video Loop**: Videos restart automatically when they end
- 📊 **Live Updates**: Real-time vehicle counts and statistics
- 🚦 **Smart Traffic Control**: Dynamic green light timing based on vehicle density

## 🛠️ Troubleshooting

### Videos Not Showing?
1. Check Flask backend is running
2. Check ML system is running
3. Refresh browser page
4. Check browser console for errors

### No Vehicles Detected?
- Videos are processing - wait a few seconds
- Check console for detection messages
- Verify video files exist in `ml_model` folder

### System Slow?
- Reduce FPS: Edit `intelliflow_ml.py` line 366: `time.sleep(0.033)` → `time.sleep(0.05)`
- Reduce quality: Edit `intelliflow_ml.py` line 337: `85` → `70`

## 📝 Configuration

**All configuration is in `ml_model/config.py`**

### Change Video Sources
Edit `ml_model/config.py`:
```python
# Video Files
USE_VIDEO_FILES = True
NORTH_VIDEO_FILE = "your_video1.mp4"
EAST_VIDEO_FILE = "your_video2.mp4"

# ESP32-CAM
USE_VIDEO_FILES = False
NORTH_ESP32_IP = "192.168.1.100"
EAST_ESP32_IP = "192.168.1.101"

# IP Webcam
USE_VIDEO_FILES = False
NORTH_IP_WEBCAM_URL = "http://192.168.1.50:8080/video"
EAST_IP_WEBCAM_URL = "http://192.168.1.51:8080/video"

# Webcams
USE_VIDEO_FILES = False
NORTH_WEBCAM_INDEX = 0
EAST_WEBCAM_INDEX = 1
```

### Change Detection Sensitivity
Edit `ml_model/config.py`:
```python
DETECTION_CONFIDENCE = 0.4  # Lower = detect more, Higher = detect less
```

### Change Arduino Port
Edit `ml_model/config.py`:
```python
ARDUINO_PORT = "COM11"  # Update to your COM port
```

## 🎯 Next Steps

1. ✅ System running
2. ✅ Videos showing with detection boxes
3. ✅ Web dashboard displaying live feeds
4. ⚙️ Configure Arduino (if using hardware)
5. ⚙️ Adjust traffic light timings
6. ⚙️ Fine-tune detection settings

## 📚 More Info

- See `ml_model/RUN_SYSTEM.md` for detailed instructions
- See `ml_model/TROUBLESHOOTING.md` for common issues
- See `README.md` for system overview

---

**Ready to go!** Start the three components and watch your traffic system in action! 🚦

