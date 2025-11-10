# How to Run IntelliFlow System

## Quick Start - All Systems

### Option 1: Run Everything at Once (Recommended)

1. **Start all systems:**
   ```bash
   start_all.bat
   ```
   This will:
   - Start Flask backend server (Terminal 1)
   - Start ML traffic detection system (Terminal 2)

2. **Start React Frontend:**
   ```bash
   cd ../eco-traffic-dash
   npm install  # First time only
   npm run dev
   ```

3. **Open in browser:**
   - Frontend: http://localhost:8080
   - Backend API: http://127.0.0.1:5000/api/data

### Option 2: Run Manually

1. **Terminal 1 - Start Flask Backend:**
   ```bash
   .venv\Scripts\activate
   python dashboard.py
   ```

2. **Terminal 2 - Start ML System:**
   ```bash
   .venv\Scripts\activate
   python intelliflow_ml.py
   ```

3. **Terminal 3 - Start React Frontend:**
   ```bash
   cd ../eco-traffic-dash
   npm run dev
   ```

## What You'll See

### Web Dashboard (http://localhost:8080)
- **Live Video Feeds**: Both North and East lane videos with vehicle detection boxes
- **Vehicle Counts**: Real-time count of detected vehicles in each lane
- **Traffic Statistics**: Total vehicles, efficiency improvements
- **Charts**: Vehicle counts and efficiency over time
- **Traffic Light Status**: Current phase and active lane

### ML System Console
- Vehicle detection in real-time
- Traffic light cycle information
- Vehicle counts per lane
- Signal timing calculations
- Arduino commands (if connected)

## Video Files

The system uses these video files:
- **North Lane**: `WhatsApp Video 2025-11-08 at 00.20.17_02904bca.mp4`
- **East Lane**: `WhatsApp Video 2025-11-08 at 00.20.17_269fdc46.mp4`

Videos will automatically loop when they reach the end.

## Features

✅ **Full Frame Detection**: Detects ALL vehicles in entire video frame (not just specific regions)
✅ **Live Video Streaming**: See both videos with detection boxes in real-time on web
✅ **Automatic Video Looping**: Videos restart automatically when they end
✅ **Real-time Statistics**: Vehicle counts and traffic data updated live
✅ **Traffic Light Control**: Automatic traffic light cycling based on vehicle density

## Troubleshooting

### Videos not showing in web dashboard
- Make sure Flask backend is running: `python dashboard.py`
- Make sure ML system is running: `python intelliflow_ml.py`
- Check browser console for errors
- Try refreshing the page

### No vehicles detected
- Check video files exist in `ml_model` folder
- Verify video files can be opened
- Check console for detection messages
- Lower confidence threshold in `intelliflow_ml.py` (line 129): `conf=0.4` → `conf=0.3`

### Video streaming slow
- Reduce FPS in `intelliflow_ml.py` (line 366): `time.sleep(0.033)` → `time.sleep(0.05)`
- Reduce JPEG quality in `intelliflow_ml.py` (line 337): `85` → `70`

## Configuration

### Change Video Files
Edit `intelliflow_ml.py` (lines 460-461):
```python
north_camera_url="your_video1.mp4"
east_camera_url="your_video2.mp4"
```

### Change Detection Confidence
Edit `intelliflow_ml.py` (line 129):
```python
results = self.model(frame, conf=0.4, classes=[2, 3, 5, 7], verbose=False)
# Lower conf (e.g., 0.3) = detect more vehicles
# Higher conf (e.g., 0.5) = detect only confident detections
```

## Next Steps

1. ✅ System running
2. ✅ Videos playing with detection
3. ✅ Web dashboard showing live feeds
4. ⚙️ Configure Arduino (if using hardware)
5. ⚙️ Adjust traffic light timings
6. ⚙️ Fine-tune vehicle detection


