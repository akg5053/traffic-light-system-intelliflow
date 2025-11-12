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

def build_dashboard_state():
    """Compose the dashboard payload with the latest realtime information."""
    logs = read_data()
    latest = get_latest_data()
    lane_order = ["North", "South", "East", "West"]
    
    # Get REAL-TIME data from traffic controller if available
    if traffic_controller:
        # Get real-time vehicle counts from ML system
        real_vehicle_counts = traffic_controller.current_counts if hasattr(traffic_controller, 'current_counts') else {}
        lane_order = getattr(traffic_controller, 'lane_order', lane_order)
        lane_groups = getattr(traffic_controller, 'lane_groups', {"NorthSouth": ["North", "South"], "EastWest": ["East", "West"]})
        lanes_available = getattr(traffic_controller, 'active_lanes', lane_order)
        lane_counts = {lane: real_vehicle_counts.get(lane, 0) for lane in lane_order}
        group_counts = traffic_controller.get_group_vehicle_counts() if hasattr(traffic_controller, 'get_group_vehicle_counts') else {
            "NorthSouth": lane_counts.get("North", 0) + lane_counts.get("South", 0),
            "EastWest": lane_counts.get("East", 0) + lane_counts.get("West", 0),
        }
        
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
        vehicle_counts = lane_counts
        total_vehicles = sum(vehicle_counts.get(lane, 0) for lane in lane_order if lane in lanes_available)
        
        # Derive remaining time from phase start + durations
        remaining_times_group = {"NorthSouth": 0.0, "EastWest": 0.0}
        elapsed = 0.0
        if hasattr(traffic_controller, "phase_start_time"):
            elapsed = time.time() - traffic_controller.phase_start_time

        yellow_time = getattr(traffic_controller, "YELLOW_TIME", 3)
        all_red_time = getattr(traffic_controller, "ALL_RED_TIME", 2)

        if "NorthSouth_Green" in current_phase:
            remaining_times_group["NorthSouth"] = max(0.0, signal_timings.get("NorthSouth", 0) - elapsed)
        elif "NorthSouth_Yellow" in current_phase:
            remaining_times_group["NorthSouth"] = max(0.0, yellow_time - elapsed)
        elif "EastWest_Green" in current_phase:
            remaining_times_group["EastWest"] = max(0.0, signal_timings.get("EastWest", 0) - elapsed)
        elif "EastWest_Yellow" in current_phase:
            remaining_times_group["EastWest"] = max(0.0, yellow_time - elapsed)
        elif "All_Red" in current_phase:
            remaining_times_group["NorthSouth"] = max(0.0, all_red_time - elapsed)
            remaining_times_group["EastWest"] = max(0.0, all_red_time - elapsed)

        remaining_times = {}
        for group, lanes in lane_groups.items():
            group_remaining_int = max(0, int(round(remaining_times_group.get(group, 0.0))))
            for lane in lanes:
                remaining_times[lane] = group_remaining_int
        for lane in lane_order:
            remaining_times.setdefault(lane, 0)
    else:
        # Fallback to logged data if controller not available
        current_phase = latest.get("current_phase", "NorthSouth_Green")
        vehicle_counts = latest.get("vehicle_counts", {lane: 0 for lane in lane_order})
        lanes_available = [lane for lane, count in vehicle_counts.items() if count is not None]
        lane_groups = {"NorthSouth": ["North", "South"], "EastWest": ["East", "West"]}
        signal_timings = latest.get("signal_timings", {"NorthSouth": 5, "EastWest": 5})
        group_counts = latest.get("group_counts", {
            "NorthSouth": vehicle_counts.get("North", 0) + vehicle_counts.get("South", 0),
            "EastWest": vehicle_counts.get("East", 0) + vehicle_counts.get("West", 0),
        })
        signal_timings = latest.get("signal_timings", {"NorthSouth": 5, "EastWest": 5})
        total_vehicles = latest.get("total_vehicles", 0)
        remaining_times = {lane: 0 for lane in lane_order}
    
    # Determine active lane
    active_group = "NorthSouth" if "NorthSouth" in current_phase else "EastWest" if "EastWest" in current_phase else "All_Red"
    active_lane = lane_groups.get(active_group, ["North"])[0]
    
    # Map North → North/South (same), East → East/West (same)
    # Calculate remaining times for all 4 lanes based on current phase
    remaining_times = {lane: remaining_times.get(lane, 0) for lane in lane_order}
    
    # Calculate efficiency improvement
    avg_wait_traditional = 90
    avg_wait_intelliflow = (signal_timings.get("NorthSouth", 5) + signal_timings.get("EastWest", 5)) / 2
    efficiency_improvement = round(((avg_wait_traditional - avg_wait_intelliflow) / avg_wait_traditional) * 100, 2)
    
    return {
        "logs": logs,
        "latest": latest,
        "active_lane": active_lane,
        "active_group": active_group,
        "current_phase": current_phase,
        "vehicle_counts": {lane: vehicle_counts.get(lane, 0) for lane in lane_order},
        "group_counts": group_counts,
        "signal_timings": signal_timings,
        "remaining_times": remaining_times,
        "total_vehicles": total_vehicles,
        "efficiency_improvement": efficiency_improvement,
        "last_updated": datetime.now().strftime("%H:%M:%S"),
        "lanes_available": list(lanes_available),
        "lane_groups": lane_groups,
        "system_mode": getattr(traffic_controller, 'system_mode', 'TWO_VIDEO') if traffic_controller else "TWO_VIDEO",
    }


@app.route("/api/data")
def api_data():
    """Get current traffic data (for polling) - Uses REAL-TIME data from ML system"""
    return jsonify(build_dashboard_state())

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

@app.route("/api/video/south")
def video_south():
    """Stream South lane video with vehicle detections"""
    def generate():
        while True:
            if traffic_controller and traffic_controller.south_frame_encoded:
                with traffic_controller.frame_lock:
                    frame = traffic_controller.south_frame_encoded
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            else:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + b'' + b'\r\n')
            import time
            time.sleep(0.033)  # ~30 FPS
    
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/api/video/west")
def video_west():
    """Stream West lane video with vehicle detections"""
    def generate():
        while True:
            if traffic_controller and traffic_controller.west_frame_encoded:
                with traffic_controller.frame_lock:
                    frame = traffic_controller.west_frame_encoded
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            else:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + b'' + b'\r\n')
            import time
            time.sleep(0.033)  # ~30 FPS
    
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/api/video/frames")
def video_frames():
    """Get latest frames as base64 encoded images"""
    if traffic_controller:
        lane_order = getattr(traffic_controller, 'lane_order', ["North", "South", "East", "West"])
        frames_payload = {}
        counts_payload = {}
        with traffic_controller.frame_lock:
            for lane in lane_order:
                encoded = traffic_controller.encoded_frames.get(lane)
                frames_payload[lane.lower()] = base64.b64encode(encoded).decode('utf-8') if encoded else None
                counts_payload[lane.lower()] = traffic_controller.current_counts.get(lane, 0)

        return jsonify({
            "frames": frames_payload,
            "counts": counts_payload,
            "lanes": getattr(traffic_controller, 'active_lanes', lane_order),
        })
    empty_frames = {"north": None, "south": None, "east": None, "west": None}
    empty_counts = {"north": 0, "south": 0, "east": 0, "west": 0}
    return jsonify({"frames": empty_frames, "counts": empty_counts, "lanes": []})

# ============================================================
# WebSocket Updates
# ============================================================

def push_live_update():
    """Push newest data to dashboard via WebSocket"""
    snapshot = build_dashboard_state()
    socketio.emit("update", snapshot)

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
