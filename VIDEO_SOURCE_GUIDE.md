# 📹 Video Source Configuration Guide

## Choose a Mode

All lane inputs are controlled from `ml_model/config.py` using the `SYSTEM_MODE` switch. Pick the mode that matches your hardware, then populate the supporting dictionaries.

```python
SYSTEM_MODE = "TWO_VIDEO"  # Options: "FOUR_VIDEO", "TWO_VIDEO", "TWO_ESP32", "TWO_IP", "TWO_MIXED", "FOUR_HYBRID"
```

### Source Dictionaries

```python
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

### Mode Reference

| `SYSTEM_MODE` | North | South | East | West |
|---------------|-------|-------|------|------|
| `FOUR_VIDEO`  | `VIDEO_FILES` | `VIDEO_FILES` | `VIDEO_FILES` | `VIDEO_FILES` |
| `TWO_VIDEO`   | `VIDEO_FILES` | _unused_ | `VIDEO_FILES` | _unused_ |
| `TWO_ESP32`   | `ESP32_CAMERAS` | _unused_ | `ESP32_CAMERAS` | _unused_ |
| `TWO_IP`      | `IP_WEBCAMS` | _unused_ | `IP_WEBCAMS` | _unused_ |
| `TWO_MIXED`   | `IP_WEBCAMS` | _unused_ | `ESP32_CAMERAS` | _unused_ |
| `FOUR_HYBRID` | `IP_WEBCAMS` | `IP_WEBCAMS` | `ESP32_CAMERAS` | `ESP32_CAMERAS` |

> 💡 The React dashboard automatically renders two or four live feeds based on the selected mode.

## Setup Notes

### Laptop Webcams
- Map your webcam indices into the `VIDEO_FILES` dictionary (e.g., use `0` or `1` if you are streaming locally via OpenCV).
- Verify indices with `python -c "import cv2; cap = cv2.VideoCapture(0); print(cap.isOpened()); cap.release()"`.

### Video Files
- Place files inside `ml_model/` or provide absolute paths.
- Update `VIDEO_FILES` entries accordingly.

### ESP32-CAM
1. Flash the ESP32 with `ESP32_CAM_CODE.ino`.
2. Connect to WiFi and note each IP address.
3. Update the `ESP32_CAMERAS` dictionary with IP + stream path (default `/stream`).

### IP Webcam (Android)
1. Install the *IP Webcam* app.
2. Start the server and note the URL.
3. Populate the `IP_WEBCAMS` dictionary with the full `http://<ip>:<port>/video` paths.

## Testing Sources

```python
import cv2

# Webcam index
cap = cv2.VideoCapture(0)
print("Webcam working" if cap.isOpened() else "Webcam failed")
cap.release()

# Video file
cap = cv2.VideoCapture("your_video.mp4")
print("File working" if cap.isOpened() else "File failed")
cap.release()
```

- Test IP webcams or ESP32 streams directly in a browser (`http://<ip>/video` or `http://<ip>/stream`).

## Troubleshooting

- **Stream not opening?** Confirm the URL/IP address and that the device is reachable on the network.
- **No video in dashboard?** Ensure the Flask backend and ML system are running, then reload the frontend.
- **Wrong camera shown?** Double-check `SYSTEM_MODE` and the dictionary entries for each lane.

## Current Configuration

The default repository setup runs `SYSTEM_MODE = "TWO_VIDEO"` with sample clips for the North and East lanes. Switch modes to enable four-lane operation or alternate hardware without changing application code.


