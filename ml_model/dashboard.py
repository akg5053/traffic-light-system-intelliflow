"""
IntelliFlow - Real-Time Web Dashboard
Flask backend API for React frontend and WebSocket updates
Includes video streaming for live vehicle detection
"""

from flask import Flask, jsonify, Response
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import json
import os
from datetime import datetime
import base64
import time

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend
socketio = SocketIO(app, cors_allowed_origins="*")

DATA_FILE = "traffic_log.json"

# Global reference to traffic controller for video streaming
traffic_controller = None

def set_traffic_controller(controller):
    """Set the traffic controller instance for video streaming"""
    global traffic_controller
    traffic_controller = controller

def read_data():
    """Read traffic log data from JSON file"""
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = []
    return data[-50:]  # Return last 50 entries

def get_latest_data():
    """Get the latest traffic data entry"""
    logs = read_data()
    return logs[-1] if logs else {}

# ============================================================
# API Endpoints for React Frontend
# ============================================================

@app.route("/api/data")
def api_data():
    """Get current traffic data (for polling) - Uses REAL-TIME data from ML system"""
    logs = read_data()
    latest = get_latest_data()
    
    # Get REAL-TIME data from traffic controller if available
    if traffic_controller:
        # Get real-time vehicle counts from ML system
        real_vehicle_counts = traffic_controller.current_counts if hasattr(traffic_controller, 'current_counts') else {"North": 0, "East": 0}
        
        # Get real-time phase from ML system
        real_current_phase = traffic_controller.current_phase if hasattr(traffic_controller, 'current_phase') else "NorthSouth_Green"
        
        # Get signal timings (calculate from current counts - ALWAYS calculate fresh)
        if hasattr(traffic_controller, 'calculate_green_time'):
            signal_timings = traffic_controller.calculate_green_time(real_vehicle_counts)
        else:
            # Fallback: use latest logged or defaults
            signal_timings = latest.get("signal_timings", {"NorthSouth": 5, "EastWest": 5})
        
        # Use real-time data
        current_phase = real_current_phase
        vehicle_counts = real_vehicle_counts
        total_vehicles = real_vehicle_counts.get("North", 0) + real_vehicle_counts.get("East", 0)
        
        # Get remaining time - calculate from elapsed time (most reliable method)
        remaining = 0
        if hasattr(traffic_controller, 'phase_start_time') and hasattr(traffic_controller, 'current_phase'):
            try:
                elapsed = time.time() - traffic_controller.phase_start_time
                if "Green" in current_phase:
                    if "NorthSouth" in current_phase:
                        # Use calculated signal timing for NorthSouth
                        remaining = max(0, signal_timings.get("NorthSouth", 5) - elapsed)
                    elif "EastWest" in current_phase:
                        # Use calculated signal timing for EastWest
                        remaining = max(0, signal_timings.get("EastWest", 5) - elapsed)
                    else:
                        remaining = 0
                elif "Yellow" in current_phase:
                    yellow_time = traffic_controller.YELLOW_TIME if hasattr(traffic_controller, 'YELLOW_TIME') else 3
                    remaining = max(0, yellow_time - elapsed)
                elif "All_Red" in current_phase:
                    all_red_time = traffic_controller.ALL_RED_TIME if hasattr(traffic_controller, 'ALL_RED_TIME') else 2
                    remaining = max(0, all_red_time - elapsed)
                else:
                    remaining = 0
            except Exception as e:
                # If calculation fails, try to use phase_remaining_time as fallback
                if hasattr(traffic_controller, 'phase_remaining_time'):
                    try:
                        remaining = max(0, float(traffic_controller.phase_remaining_time))
                    except:
                        remaining = 0
                else:
                    remaining = 0
        elif hasattr(traffic_controller, 'phase_remaining_time'):
            # Fallback: use phase_remaining_time if phase_start_time not available
            try:
                remaining = max(0, float(traffic_controller.phase_remaining_time))
            except:
                remaining = 0
    else:
        # Fallback to logged data if controller not available
        current_phase = latest.get("current_phase", "NorthSouth_Green")
        vehicle_counts = latest.get("vehicle_counts", {"North": 0, "East": 0})
        signal_timings = latest.get("signal_timings", {"NorthSouth": 5, "EastWest": 5})
        total_vehicles = latest.get("total_vehicles", 0)
        remaining = 0
    
    # Determine active lane
    active_lane = "North" if "NorthSouth" in current_phase else "East"
    
    # Map North → North/South (same), East → East/West (same)
    # Calculate remaining times for all 4 lanes based on current phase
    remaining_times = {"North": 0, "South": 0, "East": 0, "West": 0}
    
    # Calculate remaining times based on current phase and elapsed time
    if "NorthSouth_Green" in current_phase:
        # North/South have green - show remaining time
        if remaining > 0:
            remaining_times["North"] = max(0, int(remaining))
            remaining_times["South"] = max(0, int(remaining))
        else:
            # If remaining is 0 or negative, use the calculated signal timing
            remaining_times["North"] = signal_timings.get("NorthSouth", 5)
            remaining_times["South"] = signal_timings.get("NorthSouth", 5)
        # East/West have red
        remaining_times["East"] = 0
        remaining_times["West"] = 0
    elif "NorthSouth_Yellow" in current_phase:
        # North/South have yellow
        if remaining > 0:
            remaining_times["North"] = max(0, int(remaining))
            remaining_times["South"] = max(0, int(remaining))
        else:
            remaining_times["North"] = 3
            remaining_times["South"] = 3
        # East/West have red
        remaining_times["East"] = 0
        remaining_times["West"] = 0
    elif "EastWest_Green" in current_phase:
        # East/West have green - show remaining time
        if remaining > 0:
            remaining_times["East"] = max(0, int(remaining))
            remaining_times["West"] = max(0, int(remaining))
        else:
            # If remaining is 0 or negative, use the calculated signal timing
            remaining_times["East"] = signal_timings.get("EastWest", 5)
            remaining_times["West"] = signal_timings.get("EastWest", 5)
        # North/South have red
        remaining_times["North"] = 0
        remaining_times["South"] = 0
    elif "EastWest_Yellow" in current_phase:
        # East/West have yellow
        if remaining > 0:
            remaining_times["East"] = max(0, int(remaining))
            remaining_times["West"] = max(0, int(remaining))
        else:
            remaining_times["East"] = 3
            remaining_times["West"] = 3
        # North/South have red
        remaining_times["North"] = 0
        remaining_times["South"] = 0
    else:
        # All Red or unknown phase
        remaining_times = {"North": 0, "South": 0, "East": 0, "West": 0}
    
    # Calculate efficiency improvement
    avg_wait_traditional = 90
    avg_wait_intelliflow = (signal_timings.get("NorthSouth", 5) + signal_timings.get("EastWest", 5)) / 2
    efficiency_improvement = round(((avg_wait_traditional - avg_wait_intelliflow) / avg_wait_traditional) * 100, 2)
    
    response = {
        "logs": logs,
        "latest": latest,
        "active_lane": active_lane,
        "current_phase": current_phase,
        "vehicle_counts": {
            "North": vehicle_counts.get("North", 0),
            "South": 0,  # South count is 0 (only North has count)
            "East": vehicle_counts.get("East", 0),
            "West": 0     # West count is 0 (only East has count)
        },
        "signal_timings": signal_timings,
        "remaining_times": remaining_times,
        "total_vehicles": total_vehicles,
        "efficiency_improvement": efficiency_improvement,
        "last_updated": datetime.now().strftime("%H:%M:%S"),
    }
    return jsonify(response)

@app.route("/api/stats")
def api_stats():
    """Get aggregated statistics"""
    logs = read_data()
    if not logs:
        return jsonify({
            "total_vehicles": 0,
            "avg_efficiency": 0,
            "total_cycles": 0
        })
    
    total_vehicles = sum(log.get("total_vehicles", 0) for log in logs)
    avg_efficiency = sum(log.get("efficiency_improvement", 0) for log in logs) / len(logs)
    
    return jsonify({
        "total_vehicles": total_vehicles,
        "avg_efficiency": round(avg_efficiency, 2),
        "total_cycles": len(logs)
    })

# ============================================================
# Video Streaming Endpoints
# ============================================================

@app.route("/api/video/north")
def video_north():
    """Stream North lane video with vehicle detections"""
    def generate():
        while True:
            if traffic_controller and traffic_controller.north_frame_encoded:
                with traffic_controller.frame_lock:
                    frame = traffic_controller.north_frame_encoded
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            else:
                # Send placeholder if no frame available
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + b'' + b'\r\n')
            import time
            time.sleep(0.033)  # ~30 FPS
    
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/api/video/east")
def video_east():
    """Stream East lane video with vehicle detections"""
    def generate():
        while True:
            if traffic_controller and traffic_controller.east_frame_encoded:
                with traffic_controller.frame_lock:
                    frame = traffic_controller.east_frame_encoded
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            else:
                # Send placeholder if no frame available
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + b'' + b'\r\n')
            import time
            time.sleep(0.033)  # ~30 FPS
    
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/api/video/frames")
def video_frames():
    """Get latest frames as base64 encoded images"""
    if traffic_controller:
        with traffic_controller.frame_lock:
            north_frame = base64.b64encode(traffic_controller.north_frame_encoded).decode('utf-8') if traffic_controller.north_frame_encoded else None
            east_frame = base64.b64encode(traffic_controller.east_frame_encoded).decode('utf-8') if traffic_controller.east_frame_encoded else None
        
        return jsonify({
            "north": north_frame,
            "east": east_frame,
            "north_count": traffic_controller.current_counts.get("North", 0),
            "east_count": traffic_controller.current_counts.get("East", 0)
        })
    return jsonify({"north": None, "east": None})

# ============================================================
# WebSocket Updates
# ============================================================

def push_live_update():
    """Push newest data to dashboard via WebSocket"""
    logs = read_data()
    latest = get_latest_data()
    
    # Get real-time data if traffic controller is available
    if traffic_controller:
        current_phase = traffic_controller.current_phase if hasattr(traffic_controller, 'current_phase') else latest.get("current_phase", "NorthSouth_Green")
        active_lane = "North" if "NorthSouth" in current_phase else "East"
        
        # Calculate signal timings and remaining times
        real_vehicle_counts = traffic_controller.current_counts if hasattr(traffic_controller, 'current_counts') else {"North": 0, "East": 0}
        if hasattr(traffic_controller, 'calculate_green_time'):
            signal_timings = traffic_controller.calculate_green_time(real_vehicle_counts)
        else:
            signal_timings = latest.get("signal_timings", {"NorthSouth": 5, "EastWest": 5})
        
        # Calculate remaining time
        remaining = 0
        if hasattr(traffic_controller, 'phase_start_time'):
            try:
                elapsed = time.time() - traffic_controller.phase_start_time
                if "Green" in current_phase:
                    if "NorthSouth" in current_phase:
                        remaining = max(0, signal_timings.get("NorthSouth", 5) - elapsed)
                    elif "EastWest" in current_phase:
                        remaining = max(0, signal_timings.get("EastWest", 5) - elapsed)
                elif "Yellow" in current_phase:
                    yellow_time = traffic_controller.YELLOW_TIME if hasattr(traffic_controller, 'YELLOW_TIME') else 3
                    remaining = max(0, yellow_time - elapsed)
                elif "All_Red" in current_phase:
                    all_red_time = traffic_controller.ALL_RED_TIME if hasattr(traffic_controller, 'ALL_RED_TIME') else 2
                    remaining = max(0, all_red_time - elapsed)
            except:
                if hasattr(traffic_controller, 'phase_remaining_time'):
                    remaining = max(0, float(traffic_controller.phase_remaining_time))
        
        # Calculate remaining times for all lanes
        remaining_times = {"North": 0, "South": 0, "East": 0, "West": 0}
        if "NorthSouth_Green" in current_phase:
            remaining_times["North"] = max(0, int(remaining)) if remaining > 0 else signal_timings.get("NorthSouth", 5)
            remaining_times["South"] = max(0, int(remaining)) if remaining > 0 else signal_timings.get("NorthSouth", 5)
        elif "NorthSouth_Yellow" in current_phase:
            remaining_times["North"] = max(0, int(remaining)) if remaining > 0 else 3
            remaining_times["South"] = max(0, int(remaining)) if remaining > 0 else 3
        elif "EastWest_Green" in current_phase:
            remaining_times["East"] = max(0, int(remaining)) if remaining > 0 else signal_timings.get("EastWest", 5)
            remaining_times["West"] = max(0, int(remaining)) if remaining > 0 else signal_timings.get("EastWest", 5)
        elif "EastWest_Yellow" in current_phase:
            remaining_times["East"] = max(0, int(remaining)) if remaining > 0 else 3
            remaining_times["West"] = max(0, int(remaining)) if remaining > 0 else 3
    else:
        current_phase = latest.get("current_phase", "NorthSouth_Green")
        active_lane = "North" if "NorthSouth" in current_phase else "East"
        signal_timings = latest.get("signal_timings", {"NorthSouth": 5, "EastWest": 5})
        remaining_times = {"North": 0, "South": 0, "East": 0, "West": 0}
    
    socketio.emit("update", {
        "logs": logs,
        "latest": latest,
        "active_lane": active_lane,
        "current_phase": current_phase,
        "signal_timings": signal_timings,
        "remaining_times": remaining_times,
        "time": datetime.now().strftime("%H:%M:%S")
    })

# ✅ Exposed for IntelliFlow to call when it logs new cycle data
@app.route("/notify_update")
def notify_update():
    """Notify dashboard of new data"""
    push_live_update()
    return jsonify({"status": "ok"})

@socketio.on("connect")
def handle_connect():
    """Handle WebSocket connection"""
    print("🌐 Client connected")
    push_live_update()  # Send current data on connect

if __name__ == "__main__":
    # This will only run if dashboard.py is started directly
    # If started from intelliflow_ml.py, Flask server runs in a thread there
    print("🚀 IntelliFlow API Server running at http://127.0.0.1:5000")
    print("📡 WebSocket enabled for real-time updates")
    print("🔗 React frontend should connect to: http://127.0.0.1:5000")
    print("\n⚠️  NOTE: If you're running intelliflow_ml.py, Flask server will start automatically.")
    print("⚠️  You don't need to run dashboard.py separately.\n")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
