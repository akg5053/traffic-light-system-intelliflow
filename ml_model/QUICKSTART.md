# IntelliFlow Quick Start Guide

## ✅ Setup Complete!

All Python dependencies have been installed in the virtual environment (`.venv`).

## Current Status

### ✅ Installed and Working:
- Flask & Flask-SocketIO (Backend server)
- OpenCV (Video processing)
- NumPy (Numerical operations)
- PySerial (Arduino communication)
- Flask-CORS (CORS support)

### ⚠️ PyTorch DLL Issue (Windows):
- PyTorch is installed but may have DLL loading issues on Windows
- **Solution:** Run `install_pytorch_cpu.bat` to reinstall CPU-only version
- Or install Visual C++ Redistributables (see TROUBLESHOOTING.md)

## Running the System

### Method 1: Use Batch Scripts (Easiest)

1. **Start Flask Backend:**
   ```
   start_backend.bat
   ```
   This starts the API server on http://127.0.0.1:5000

2. **Start ML System:**
   ```
   start_ml_system.bat
   ```
   This starts the vehicle detection and traffic control system

### Method 2: Manual Commands

1. **Activate virtual environment:**
   ```bash
   .venv\Scripts\activate
   ```

2. **Start Flask backend:**
   ```bash
   python dashboard.py
   ```

3. **Start ML system (in another terminal):**
   ```bash
   .venv\Scripts\activate
   python intelliflow_ml.py
   ```

## Configuration

### 1. Configure Cameras

Edit `intelliflow_ml.py` (line ~470):
```python
controller = TrafficSignalController(
    model_path="yolov8n.pt",
    north_camera_url=0,  # Change to your camera index or video file
    east_camera_url=1    # Change to your camera index or video file
)
```

**Options:**
- Webcam: Use `0`, `1`, `2`, etc.
- Video file: Use `"path/to/video.mp4"`

### 2. Configure Arduino

Edit `intelliflow_ml.py` (line ~75):
```python
self.arduino = serial.Serial('COM11', 9600, timeout=1)  # Change COM11 to your port
```

**To find your COM port:**
- Windows: Device Manager → Ports (COM & LPT)
- Or: `python -m serial.tools.list_ports`

### 3. Start React Frontend

```bash
cd ../eco-traffic-dash
npm install
npm run dev
```

Frontend will run on http://localhost:8080

## Testing

### Test Backend:
```bash
.venv\Scripts\activate
python dashboard.py
# Should see: "🚀 IntelliFlow API Server running at http://127.0.0.1:5000"
# Visit: http://127.0.0.1:5000/api/data
```

### Test Camera:
```bash
.venv\Scripts\activate
python -c "import cv2; cap = cv2.VideoCapture(0); print('✅ Camera works!' if cap.isOpened() else '❌ Camera not found'); cap.release()"
```

### Test ML System (without camera):
The system will try to connect to cameras. If they don't exist, it will show an error but you can still test the logic.

## Troubleshooting

### PyTorch DLL Error:
Run: `install_pytorch_cpu.bat`

### Camera Issues:
- Check Windows camera permissions
- Try different camera indices
- Use video files for testing

### Arduino Issues:
- Check COM port in Device Manager
- Verify baud rate (9600)
- Test connection: `python test_arduino_connection.py`

See `TROUBLESHOOTING.md` for detailed solutions.

## File Structure

```
ml_model/
├── .venv/                 # Virtual environment (created)
├── intelliflow_ml.py      # Main ML system
├── dashboard.py           # Flask backend
├── requirements.txt       # Dependencies
├── setup.bat             # Setup script
├── start_backend.bat     # Start Flask backend
├── start_ml_system.bat   # Start ML system
├── install_pytorch_cpu.bat # Fix PyTorch DLL issues
└── TROUBLESHOOTING.md    # Troubleshooting guide
```

## Next Steps

1. ✅ Dependencies installed
2. ⚙️ Configure cameras in `intelliflow_ml.py`
3. ⚙️ Configure Arduino port (if using hardware)
4. 🚀 Start Flask backend: `start_backend.bat`
5. 🚀 Start ML system: `start_ml_system.bat`
6. 🌐 Start React frontend: `cd ../eco-traffic-dash && npm run dev`

## Need Help?

- Check `TROUBLESHOOTING.md` for common issues
- Check `README_SETUP.md` for detailed setup instructions
- Check main `README.md` for system overview



