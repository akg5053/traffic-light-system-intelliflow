# 📹 Video Source Configuration Guide

## Three Main Options

### Option 1: Laptop Webcam (Both Lanes)

Edit `ml_model/config.py`:
```python
USE_WEBCAM = True
USE_VIDEO_FILES = False
USE_MIXED = False

NORTH_WEBCAM_INDEX = 0  # Camera index for North lane (usually 0)
EAST_WEBCAM_INDEX = 1   # Camera index for East lane (usually 1)
# If you only have one camera, use same index for both: 0 and 0
```

**How to find camera index:**
- Try 0, 1, 2, etc. until you find the right cameras
- Test with: `python -c "import cv2; cap = cv2.VideoCapture(0); print('Camera 0 works!' if cap.isOpened() else 'Camera 0 not found'); cap.release()"`

---

### Option 2: Two Video Files (Both Lanes)

Edit `ml_model/config.py`:
```python
USE_WEBCAM = False
USE_VIDEO_FILES = True
USE_MIXED = False

NORTH_VIDEO_FILE = "your_video1.mp4"  # Path to North lane video
EAST_VIDEO_FILE = "your_video2.mp4"    # Path to East lane video
```

**Video file paths:**
- Put video files in `ml_model/` folder
- Use relative paths: `"video1.mp4"`
- Or absolute paths: `"C:/path/to/video1.mp4"`

---

### Option 3: Mixed Sources (IP Webcam + ESP32-CAM)

**North Lane:** IP Webcam App (Android phone)  
**East Lane:** ESP32-CAM

Edit `ml_model/config.py`:
```python
USE_WEBCAM = False
USE_VIDEO_FILES = False
USE_MIXED = True

# North Lane: IP Webcam App
NORTH_IP_WEBCAM_URL = "http://192.168.1.50:8080/video"  # Your phone's IP and port

# East Lane: ESP32-CAM
EAST_ESP32_IP = "192.168.1.101"   # ESP32-CAM IP address
EAST_ESP32_STREAM_URL = "/stream"  # ESP32-CAM stream endpoint
```

**Setup IP Webcam (Android):**
1. Install "IP Webcam" app from Play Store
2. Open app, tap "Start server"
3. Note the IP address shown (e.g., `192.168.1.50:8080`)
4. Use URL: `http://192.168.1.50:8080/video`

**Setup ESP32-CAM:**
1. Upload `ESP32_CAM_CODE.ino` to your ESP32-CAM
2. Connect ESP32-CAM to WiFi
3. Check Serial Monitor for IP address
4. Use IP in config: `EAST_ESP32_IP = "192.168.1.101"`

---

## Quick Reference

| Option | North Source | East Source | Config Setting |
|--------|-------------|-------------|----------------|
| 1 | Webcam | Webcam | `USE_WEBCAM = True` |
| 2 | Video File | Video File | `USE_VIDEO_FILES = True` |
| 3 | IP Webcam | ESP32-CAM | `USE_MIXED = True` |

---

## Testing Video Sources

### Test Webcam:
```python
import cv2
cap = cv2.VideoCapture(0)  # Try 0, 1, 2, etc.
print("Working!" if cap.isOpened() else "Failed!")
cap.release()
```

### Test Video File:
```python
import cv2
cap = cv2.VideoCapture("your_video.mp4")
print("Working!" if cap.isOpened() else "Failed!")
cap.release()
```

### Test IP Webcam:
Open in browser: `http://192.168.1.50:8080/video`

### Test ESP32-CAM:
Open in browser: `http://192.168.1.101/stream`

---

## Troubleshooting

**Webcam not working:**
- Check camera permissions
- Try different indices (0, 1, 2, etc.)
- Make sure no other app is using the camera

**Video file not loading:**
- Check file path is correct
- Make sure file exists in `ml_model/` folder
- Try absolute path instead of relative

**IP Webcam not connecting:**
- Make sure phone and computer are on same WiFi
- Check IP address is correct
- Make sure IP Webcam server is running on phone

**ESP32-CAM not connecting:**
- Make sure ESP32-CAM is on same WiFi network
- Check IP address in Serial Monitor
- Verify stream URL is correct (`/stream`)

---

## Current Configuration

Your system is currently set to use **Option 2** (Video Files):
- North: `WhatsApp Video 2025-11-08 at 00.20.17_02904bca.mp4`
- East: `WhatsApp Video 2025-11-08 at 00.20.17_269fdc46.mp4`

To change, edit `ml_model/config.py` and set the appropriate option to `True`.


