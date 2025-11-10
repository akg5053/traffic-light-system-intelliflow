# IntelliFlow - Smart Traffic Management System

A comprehensive AI-powered traffic management system that uses dual video inputs to count vehicles and dynamically adjust traffic light timings based on real-time traffic conditions.

## Features

- 🎥 **Dual Video Input**: Processes two video feeds simultaneously (North and East lanes)
- 🤖 **AI Vehicle Detection**: Uses YOLOv8 for real-time vehicle detection
- 🚦 **Dynamic Traffic Light Control**: Adjusts green light duration based on vehicle density
- 📊 **Real-time Dashboard**: React-based web dashboard with live updates via WebSocket
- 🔌 **IoT Integration**: Arduino-based hardware control for physical traffic lights
- 📈 **Analytics**: Tracks efficiency improvements and traffic statistics

## System Architecture

### Components

1. **ML Model System** (`ml_model/intelliflow_ml.py`)
   - Processes two video inputs (North and East lanes)
   - Counts vehicles in real-time using YOLOv8
   - Calculates dynamic green light timings
   - Controls Arduino hardware via serial communication

2. **Flask Backend** (`ml_model/dashboard.py`)
   - RESTful API endpoints for data access
   - WebSocket server for real-time updates
   - Data logging and statistics

3. **React Frontend** (`eco-traffic-dash/`)
   - Real-time traffic dashboard
   - Vehicle count visualization
   - Efficiency metrics and charts
   - Live updates via WebSocket

4. **Arduino Hardware**
   - Controls 2 lanes (L1 and L2) with Red/Yellow/Green LEDs
   - Receives commands via serial communication

## Setup Instructions

### Prerequisites

- Python 3.8+
- Node.js 16+
- Arduino IDE (for hardware)
- Webcam(s) or video files for testing

### 1. Python Backend Setup

```bash
# Navigate to ML model directory
cd ml_model

# Create virtual environment (if not already created)
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Download YOLOv8 model (will be downloaded automatically on first run)
# Or manually download yolov8n.pt to ml_model directory
```

### 2. React Frontend Setup

```bash
# Navigate to frontend directory
cd eco-traffic-dash

# Install dependencies
npm install

# The frontend will run on http://localhost:8080
```

### 3. Arduino Setup

1. Upload the provided Arduino code to your Arduino board
2. Connect LEDs:
   - **Lane 1 (L1)**: Pins 22 (Red), 24 (Yellow), 26 (Green)
   - **Lane 2 (L2)**: Pins 31 (Red), 33 (Yellow), 35 (Green)
3. Connect Arduino to computer via USB
4. Note the COM port (e.g., COM11 on Windows, /dev/ttyUSB0 on Linux)

### 4. Configuration

Edit `ml_model/intelliflow_ml.py`:

```python
# Update Arduino COM port
self.arduino = serial.Serial('COM11', 9600, timeout=1)  # Change COM11 to your port

# Update camera URLs
controller = TrafficSignalController(
    model_path="yolov8n.pt",
    north_camera_url=0,  # Video 1: North lane (webcam index or file path)
    east_camera_url=1    # Video 2: East lane (webcam index or file path)
)
```

**Camera Options:**
- Webcam: Use `0`, `1`, etc. for camera indices
- Video files: Use file path like `"path/to/video1.mp4"`

## Running the System

### Step 1: Start Flask Backend

```bash
cd ml_model
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # Linux/Mac

python dashboard.py
```

The backend will run on `http://127.0.0.1:5000`

### Step 2: Start React Frontend

```bash
cd eco-traffic-dash
npm run dev
```

The frontend will run on `http://localhost:8080`

### Step 3: Start ML Model System

```bash
cd ml_model
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # Linux/Mac

python intelliflow_ml.py
```

## Traffic Light Logic

The system implements a 6-phase traffic light cycle:

1. **North/South GREEN** - East/West RED
2. **North/South YELLOW** - East/West RED
3. **ALL RED** (safety buffer)
4. **East/West GREEN** - North/South RED
5. **East/West YELLOW** - North/South RED
6. **ALL RED** (safety buffer)

### Dynamic Timing

- **Minimum Green Time**: 5 seconds
- **Maximum Green Time**: 30 seconds
- **Yellow Time**: 3 seconds
- **All Red Time**: 2 seconds

Green time is calculated based on vehicle counts:
- More vehicles = Longer green time (up to maximum)
- Fewer vehicles = Shorter green time (minimum enforced)

## API Endpoints

### REST API

- `GET /api/data` - Get current traffic data
- `GET /api/stats` - Get aggregated statistics
- `GET /notify_update` - Trigger dashboard update

### WebSocket

- `connect` - Connect to WebSocket server
- `update` - Receive real-time traffic updates

## Project Structure

```
IntelliFlow/
├── ml_model/
│   ├── intelliflow_ml.py      # Main ML system
│   ├── dashboard.py            # Flask backend
│   ├── requirements.txt        # Python dependencies
│   ├── yolov8n.pt             # YOLOv8 model (auto-downloaded)
│   └── traffic_log.json       # Traffic data log
├── eco-traffic-dash/
│   ├── src/
│   │   ├── pages/
│   │   │   └── Index.tsx      # Main dashboard
│   │   ├── components/
│   │   │   └── ui/            # UI components
│   │   └── App.tsx
│   └── package.json
└── README.md
```

## Troubleshooting

### Camera Not Working
- Check camera permissions
- Verify camera indices (try 0, 1, 2, etc.)
- For video files, ensure path is correct

### Arduino Not Connecting
- Check COM port in code matches your system
- Verify Arduino is connected via USB
- Check baud rate (9600) matches on both ends

### Dashboard Not Updating
- Ensure Flask backend is running
- Check CORS settings
- Verify WebSocket connection in browser console

## License

This project is part of the InnoTech 2025 Project.

## Authors

- IntelliFlow Development Team



