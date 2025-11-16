# 🚀 IntelliFlow - New Device Setup Guide

Complete step-by-step instructions to set up the IntelliFlow traffic management system on a new computer.

## 📋 Prerequisites

- **Python 3.8+** (Download from [python.org](https://www.python.org/downloads/))
- **Node.js 18+** (Download from [nodejs.org](https://nodejs.org/))
- **Git** (Optional, for cloning from repository)
- **Arduino IDE** (If using physical Arduino hardware)
- **Video files** (if using video file mode)

---

## 📦 Method 1: Using Git (Recommended)

### Step 1: Clone the Repository

```bash
git clone <your-repository-url>
cd traffic-light-system-intelliflow
```

### Step 2: Skip to "Python Setup" below

---

## 📦 Method 2: Using ZIP File

### Step 1: Extract Project

1. Copy the entire project folder to the new computer
2. Extract/unzip if compressed
3. Navigate to the project folder in terminal/command prompt

### Step 2: Continue with Python Setup below

---

## 🐍 Python Setup (Backend)

### Step 1: Navigate to ML Model Directory

```bash
cd ml_model
```

### Step 2: Create Virtual Environment

**Windows:**
```bash
python -m venv .venv
```

**Linux/Mac:**
```bash
python3 -m venv .venv
```

### Step 3: Activate Virtual Environment

**Windows:**
```bash
.venv\Scripts\activate
```

**Linux/Mac:**
```bash
source .venv/bin/activate
```

You should see `(.venv)` in your terminal prompt.

### Step 4: Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Expected packages:**
- ultralytics (YOLOv8)
- opencv-python
- numpy
- pyserial
- flask
- flask-socketio
- flask-cors
- requests
- python-socketio
- eventlet

### Step 5: Download YOLOv8 Model (if not present)

The model `yolov8n.pt` should be in `ml_model/` directory. If missing, it will be downloaded automatically on first run, or download manually:

```bash
# The model will auto-download on first run, or download from:
# https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.pt
# Place it in ml_model/ directory
```

---

## ⚙️ Configuration

### Step 1: Edit `ml_model/config.py`

Open `ml_model/config.py` and update:

1. **Arduino Port** (if using Arduino):
   ```python
   ARDUINO_PORT = "COM5"  # Change to your Arduino port (Windows: COM#, Linux: /dev/ttyUSB#)
   ```

2. **System Mode**:
   ```python
   SYSTEM_MODE = "TWO_VIDEO"  # or "FOUR_VIDEO"
   ```

3. **Video Sources** (choose one):
   - **Video Files**: Update `VIDEO_FILES` dictionary with your video file paths
   - **ESP32-CAM**: Update `ESP32_CAMERAS` dictionary with IP addresses
   - **IP Webcams**: Update `IP_WEBCAMS` dictionary with URLs
   - **Webcams**: Update `LOCAL_WEBCAMS` dictionary with camera indices

4. **Traffic Light Timings** (optional):
   ```python
   MIN_GREEN_TIME = 10
   MAX_GREEN_TIME = 40
   YELLOW_TIME = 4
   ALL_RED_TIME = 2
   ```

### Step 2: Place Video Files (if using video file mode)

Place your video files in `ml_model/` directory and update paths in `config.py`:
```python
VIDEO_FILES = {
    "North": "vid1.mp4",
    "South": "vid3.mp4",
    "East": "vid2.mp4",
    "West": "vid4.mp4"
}
```

---

## 📦 Node.js Setup (Frontend)

### Step 1: React Dashboard Setup

```bash
# From project root
cd eco-traffic-dash
npm install
```

### Step 2: Next.js EVP Remote App Setup

```bash
# From project root
cd evp-remote
npm install
```

### Step 3: Environment Variables (Optional)

**For React Dashboard** (`eco-traffic-dash/.env.local`):
```env
VITE_API_URL=http://127.0.0.1:5000
```

**For Next.js App** (`evp-remote/.env.local`):
```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:5000
NEXT_PUBLIC_EVP_SECRET=your-secret-key-here  # Optional
```

**Note:** These are optional - defaults work for local development.

---

## 🚀 Running the System

### Option 1: Using start_all.bat (Windows - Easiest)

```bash
cd ml_model
start_all.bat
```

This starts:
- Flask backend (port 5000)
- ML detection system
- All in one command

### Option 2: Manual Start (All Platforms)

**Terminal 1 - Flask Backend:**
```bash
cd ml_model
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # Linux/Mac

python dashboard.py
```

Wait for: `🚀 IntelliFlow API Server running at http://127.0.0.1:5000`

**Terminal 2 - ML Detection System:**
```bash
cd ml_model
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # Linux/Mac

python intelliflow_ml.py
```

**Terminal 3 - React Dashboard:**
```bash
cd eco-traffic-dash
npm run dev
```

Access at: `http://localhost:8080` (or port shown in terminal)

**Terminal 4 - Next.js EVP Remote (Optional):**
```bash
cd evp-remote
npm run dev
```

Access at: `http://localhost:3000`

---

## 🔧 Troubleshooting

### Python Issues

**"python: command not found"**
- Use `python3` instead of `python` on Linux/Mac
- Ensure Python is in your PATH

**"pip: command not found"**
- Use `python -m pip` instead
- Or install pip: `python -m ensurepip --upgrade`

**"Module not found" errors**
- Ensure virtual environment is activated
- Reinstall: `pip install -r requirements.txt`

**YOLOv8 model download fails**
- Download manually from: https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.pt
- Place in `ml_model/` directory

### Node.js Issues

**"npm: command not found"**
- Install Node.js from [nodejs.org](https://nodejs.org/)
- Restart terminal after installation

**Port already in use**
- Change ports in:
  - Flask: `ml_model/dashboard.py` (default: 5000)
  - React: `eco-traffic-dash/vite.config.ts` (default: 8080)
  - Next.js: `evp-remote/package.json` (default: 3000)

**"Cannot find module" errors**
- Delete `node_modules` and reinstall:
  ```bash
  rm -rf node_modules package-lock.json
  npm install
  ```

### Arduino Issues

**"Serial port not found"**
- Check Arduino port in `ml_model/config.py`
- Windows: Use Device Manager to find COM port
- Linux: Use `ls /dev/ttyUSB*` or `ls /dev/ttyACM*`
- Mac: Use `ls /dev/cu.usbmodem*`

**"Permission denied" (Linux/Mac)**
- Add user to dialout group:
  ```bash
  sudo usermod -a -G dialout $USER
  # Log out and back in
  ```

### Video Source Issues

**Video files not found**
- Check file paths in `ml_model/config.py`
- Ensure video files are in `ml_model/` directory
- Use absolute paths if relative paths don't work

**ESP32-CAM not connecting**
- Verify ESP32 IP address in `config.py`
- Ensure ESP32 and computer are on same network
- Check ESP32 stream URL (usually `/stream`)

**IP Webcam not working**
- Verify URL format: `http://IP_ADDRESS:PORT/video`
- Ensure phone/device and computer are on same network
- Check firewall settings

---

## 📁 Important File Locations

```
traffic-light-system-intelliflow/
├── ml_model/
│   ├── config.py              # ⚙️ MAIN CONFIGURATION FILE
│   ├── intelliflow_ml.py      # ML detection system
│   ├── dashboard.py           # Flask backend
│   ├── requirements.txt       # Python dependencies
│   ├── .venv/                 # Virtual environment (created)
│   └── yolov8n.pt             # YOLOv8 model (auto-downloaded)
│
├── eco-traffic-dash/          # React dashboard
│   ├── package.json
│   └── src/pages/Index.tsx
│
├── evp-remote/                # Next.js EVP remote app
│   ├── package.json
│   └── app/page.tsx
│
└── NEW_DEVICE_SETUP.md        # This file
```

---

## ✅ Verification Checklist

After setup, verify:

- [ ] Python virtual environment created and activated
- [ ] All Python packages installed (`pip list` shows required packages)
- [ ] YOLOv8 model present in `ml_model/` directory
- [ ] `config.py` updated with correct Arduino port (if using)
- [ ] `config.py` updated with correct video sources
- [ ] Node.js dependencies installed for both frontends
- [ ] Flask backend starts without errors
- [ ] ML system starts and detects vehicles
- [ ] React dashboard accessible at `http://localhost:8080`
- [ ] Next.js app accessible at `http://localhost:3000` (if using)

---

## 🔄 Updating Configuration

After initial setup, you can change:

1. **System Mode**: Edit `ml_model/config.py` → `SYSTEM_MODE`
2. **Video Sources**: Edit `ml_model/config.py` → Video source dictionaries
3. **Arduino Port**: Edit `ml_model/config.py` → `ARDUINO_PORT`
4. **Timings**: Edit `ml_model/config.py` → Timing constants

**No reinstallation needed** - just restart the system after changes.

---

## 📞 Need Help?

- Check `SETUP_GUIDE.md` for detailed architecture info
- Check `VIDEO_SOURCE_GUIDE.md` for video source configuration
- Check `QUICK_REFERENCE.md` for quick commands
- Check `ml_model/TROUBLESHOOTING.md` for common issues

---

## 🎯 Quick Start (TL;DR)

```bash
# 1. Python setup
cd ml_model
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 2. Edit config.py (Arduino port, video sources)

# 3. Node.js setup
cd ../eco-traffic-dash
npm install
cd ../evp-remote
npm install

# 4. Run
cd ../ml_model
start_all.bat  # Windows
# Or manually start each component
```

---

**Last Updated:** 2025-11-12
**Version:** 2.0 (Four-Lane Support + EVP)

