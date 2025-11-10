# IntelliFlow Setup Guide

## Quick Start

### Option 1: Automated Setup (Windows)

1. **Run the setup script:**
   ```bash
   setup.bat
   ```
   This will:
   - Create a virtual environment (if it doesn't exist)
   - Install all required dependencies
   - Set up everything automatically

2. **Start the Flask backend:**
   ```bash
   start_backend.bat
   ```

3. **Start the ML system:**
   ```bash
   start_ml_system.bat
   ```

### Option 2: Manual Setup

1. **Create virtual environment:**
   ```bash
   python -m venv .venv
   ```

2. **Activate virtual environment:**
   ```bash
   # Windows
   .venv\Scripts\activate
   
   # Linux/Mac
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the system:**
   ```bash
   # Terminal 1: Start Flask backend
   python dashboard.py
   
   # Terminal 2: Start ML system
   python intelliflow_ml.py
   ```

## Dependencies Installed

- **ultralytics** - YOLOv8 for vehicle detection
- **opencv-python** - Video processing
- **numpy** - Numerical operations
- **pyserial** - Arduino communication
- **flask** - Web backend
- **flask-socketio** - WebSocket support
- **flask-cors** - CORS support for React frontend
- **requests** - HTTP requests
- **python-socketio** - Socket.IO client
- **eventlet** - Async networking

## Verification

To verify installation, run:
```bash
.venv\Scripts\activate
python -c "import ultralytics, cv2, flask, flask_socketio; print('✅ All dependencies installed!')"
```

## Troubleshooting

### Virtual environment not activating
- Make sure you're in the `ml_model` directory
- Check that `.venv` folder exists
- Try: `python -m venv .venv --clear` to recreate

### Dependencies not installing
- Make sure you have internet connection
- Try: `pip install --upgrade pip` first
- Check Python version: `python --version` (should be 3.8+)

### Import errors
- Make sure virtual environment is activated
- Verify installation: `pip list`
- Reinstall: `pip install -r requirements.txt --force-reinstall`

## Next Steps

1. **Configure cameras** in `intelliflow_ml.py`:
   - Update `north_camera_url` and `east_camera_url`
   - Use webcam indices (0, 1) or video file paths

2. **Configure Arduino** in `intelliflow_ml.py`:
   - Update COM port (e.g., `COM11` → your port)

3. **Start the React frontend:**
   ```bash
   cd ../eco-traffic-dash
   npm install
   npm run dev
   ```



