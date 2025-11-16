"""
IntelliFlow - Real-Time Web Dashboard
Flask backend API for React frontend and WebSocket updates
Includes video streaming for live vehicle detection
"""

from flask import Flask, jsonify, Response, request
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
EV_STATE_FILE = "emergency_state.json"

# Global reference to traffic controller for video streaming
traffic_controller = None

# ============================================================
# Emergency Vehicle Preemption (EVP) State Management
# ============================================================

def load_evp_state():
    """Load emergency vehicle preemption state from JSON file"""
    if not os.path.exists(EV_STATE_FILE):
        default_state = {
            "active": False,
            "lane": None,
            "started_at": None,
            "eta_seconds": None,
            "expected_arrival_ts": None
        }
        save_evp_state(default_state)
        return default_state
    try:
        with open(EV_STATE_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        default_state = {
            "active": False,
            "lane": None,
            "started_at": None,
            "eta_seconds": None,
            "expected_arrival_ts": None
        }
        save_evp_state(default_state)
        return default_state

def save_evp_state(state):
    """Save emergency vehicle preemption state to JSON file"""
    try:
        with open(EV_STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except IOError as e:
        print(f"⚠️ Failed to save EV state: {e}")

def require_secret(request):
    """Check if request has valid shared secret (optional auth)"""
    secret = os.environ.get("EVP_SECRET", None)
    if not secret:
        return True  # No secret configured, allow all
    return request.headers.get("X-Auth") == secret

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
        # Always calculate fallback values, then use controller's if valid
        remaining_times_group = {"NorthSouth": 0.0, "EastWest": 0.0}
        
        # Calculate fallback values from phase_start_time
        elapsed = 0.0
        if hasattr(traffic_controller, "phase_start_time"):
            elapsed = max(0.0, time.time() - traffic_controller.phase_start_time)
            # Safety check: elapsed shouldn't be unreasonably large (max 60s for any phase)
            if elapsed > 60:
                elapsed = 0.0  # Reset if stale

        yellow_time = getattr(traffic_controller, "YELLOW_TIME", 3)
        all_red_time = getattr(traffic_controller, "ALL_RED_TIME", 2)

        # Calculate fallback remaining times
        if "NorthSouth_Green" in current_phase:
            green_duration = signal_timings.get("NorthSouth", 0)
            remaining_times_group["NorthSouth"] = max(0.0, min(green_duration, green_duration - elapsed))
        elif "NorthSouth_Yellow" in current_phase:
            remaining_times_group["NorthSouth"] = max(0.0, min(yellow_time, yellow_time - elapsed))
        elif "EastWest_Green" in current_phase:
            green_duration = signal_timings.get("EastWest", 0)
            remaining_times_group["EastWest"] = max(0.0, min(green_duration, green_duration - elapsed))
        elif "EastWest_Yellow" in current_phase:
            remaining_times_group["EastWest"] = max(0.0, min(yellow_time, yellow_time - elapsed))
        elif "All_Red" in current_phase:
            remaining_times_group["NorthSouth"] = max(0.0, min(all_red_time, all_red_time - elapsed))
            remaining_times_group["EastWest"] = max(0.0, min(all_red_time, all_red_time - elapsed))
        
        # Override with controller's values if available and valid (more accurate)
        if hasattr(traffic_controller, "phase_remaining_times"):
            controller_remaining = getattr(traffic_controller, "phase_remaining_times", {})
            # Use controller values, but validate they're reasonable (not negative except -1 for EV mode)
            if "NorthSouth" in controller_remaining:
                val = controller_remaining["NorthSouth"]
                if val == -1:
                    remaining_times_group["NorthSouth"] = -1  # EV mode
                elif val >= 0 and val <= 60:  # Reasonable range
                    remaining_times_group["NorthSouth"] = val
            if "EastWest" in controller_remaining:
                val = controller_remaining["EastWest"]
                if val == -1:
                    remaining_times_group["EastWest"] = -1  # EV mode
                elif val >= 0 and val <= 60:  # Reasonable range
                    remaining_times_group["EastWest"] = val

        remaining_times = {}
        # Check if controller has phase_remaining_times with EV mode (-1)
        if hasattr(traffic_controller, "phase_remaining_times"):
            controller_remaining = getattr(traffic_controller, "phase_remaining_times", {})
            for group, lanes in lane_groups.items():
                for lane in lanes:
                    # Check if this lane is in EV mode (value is -1)
                    if controller_remaining.get(group) == -1 or controller_remaining.get(lane) == -1:
                        # EV mode - show EV countdown
                        remaining_times[lane] = -1  # Special value for EV mode
                    else:
                        group_remaining_int = max(0, int(round(remaining_times_group.get(group, 0.0))))
                        remaining_times[lane] = group_remaining_int
        else:
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
    
    # Load EVP state
    evp_state = load_evp_state()
    if evp_state.get("active") and evp_state.get("expected_arrival_ts"):
        remaining = max(0, evp_state["expected_arrival_ts"] - time.time())
        evp_state["remaining_seconds"] = round(remaining, 1)
    else:
        evp_state["remaining_seconds"] = 0
    
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
        "evp_state": evp_state,
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
# Emergency Vehicle Preemption (EVP) API Endpoints
# ============================================================

@app.route("/api/evp/start", methods=["POST"])
def evp_start():
    """Start emergency vehicle preemption for a specific lane"""
    if not require_secret(request):
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    
    try:
        data = request.get_json(force=True)
        lane = data.get("lane")  # "N", "E", "S", "W"
        eta_seconds = int(data.get("eta_seconds", 60))
        
        # Validate lane
        lane_map = {"N": "North", "E": "East", "S": "South", "W": "West"}
        if lane not in lane_map:
            return jsonify({"ok": False, "error": "invalid lane. Use N, E, S, or W"}), 400
        
        if eta_seconds < 10 or eta_seconds > 300:
            return jsonify({"ok": False, "error": "eta_seconds must be between 10 and 300"}), 400
        
        now = time.time()
        state = {
            "active": True,
            "lane": lane_map[lane],
            "started_at": now,
            "eta_seconds": eta_seconds,
            "expected_arrival_ts": now + eta_seconds
        }
        
        save_evp_state(state)
        
        # Broadcast to dashboard clients via WebSocket
        try:
            socketio.emit("evp_state", state)
            push_live_update()  # Also trigger regular update
        except Exception as e:
            print(f"⚠️ WebSocket broadcast failed: {e}")
        
        print(f"🚑 Emergency Vehicle Preemption STARTED: Lane {lane_map[lane]}, ETA {eta_seconds}s")
        return jsonify({"ok": True, "state": state})
    
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/evp/clear", methods=["POST"])
def evp_clear():
    """Clear emergency vehicle preemption and return to normal operation"""
    if not require_secret(request):
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    
    try:
        state = {
            "active": False,
            "lane": None,
            "started_at": None,
            "eta_seconds": None,
            "expected_arrival_ts": None
        }
        
        save_evp_state(state)
        
        # Broadcast to dashboard clients via WebSocket
        try:
            socketio.emit("evp_state", state)
            push_live_update()  # Also trigger regular update
        except Exception as e:
            print(f"⚠️ WebSocket broadcast failed: {e}")
        
        print("✅ Emergency Vehicle Preemption CLEARED - Returning to normal operation")
        return jsonify({"ok": True, "state": state})
    
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/evp/state", methods=["GET"])
def evp_state():
    """Get current emergency vehicle preemption state"""
    state = load_evp_state()
    
    # Calculate remaining time if active
    if state.get("active") and state.get("expected_arrival_ts"):
        remaining = max(0, state["expected_arrival_ts"] - time.time())
        state["remaining_seconds"] = round(remaining, 1)
    else:
        state["remaining_seconds"] = 0
    
    return jsonify(state)

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
    if not traffic_controller:
        empty_frames = {"north": None, "south": None, "east": None, "west": None}
        empty_counts = {"north": 0, "south": 0, "east": 0, "west": 0}
        return jsonify({"frames": empty_frames, "counts": empty_counts, "lanes": []})
    
    try:
        lane_order = getattr(traffic_controller, 'lane_order', ["North", "South", "East", "West"])
        frames_payload = {}
        counts_payload = {}
        
        # Safely access encoded_frames with proper locking
        if hasattr(traffic_controller, 'frame_lock') and hasattr(traffic_controller, 'encoded_frames'):
            with traffic_controller.frame_lock:
                encoded_frames = getattr(traffic_controller, 'encoded_frames', {})
                current_counts = getattr(traffic_controller, 'current_counts', {})
                
                for lane in lane_order:
                    encoded = encoded_frames.get(lane)
                    if encoded and isinstance(encoded, bytes):
                        try:
                            frames_payload[lane.lower()] = base64.b64encode(encoded).decode('utf-8')
                        except Exception as e:
                            frames_payload[lane.lower()] = None
                    else:
                        frames_payload[lane.lower()] = None
                    counts_payload[lane.lower()] = current_counts.get(lane, 0)
        else:
            # Fallback if frame_lock or encoded_frames don't exist
            for lane in lane_order:
                frames_payload[lane.lower()] = None
                counts_payload[lane.lower()] = getattr(traffic_controller, 'current_counts', {}).get(lane, 0)

        return jsonify({
            "frames": frames_payload,
            "counts": counts_payload,
            "lanes": getattr(traffic_controller, 'active_lanes', lane_order),
        })
    except Exception as e:
        # Return empty frames on any error to prevent 500 errors
        print(f"⚠️ Error in video_frames endpoint: {e}")
        import traceback
        traceback.print_exc()
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
    print("🚀 IntelliFlow API Server running at http://127.0.0.1:5000")
    print("📡 WebSocket enabled for real-time updates")
    print("🔗 React frontend should connect to: http://127.0.0.1:5000")
    print("\n⚠️  NOTE: If you're running intelliflow_ml.py, Flask server will start automatically.")
    print("⚠️  You don't need to run dashboard.py separately.\n")
    # Change 0.0.0.0 instead of localhost binding
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, allow_unsafe_werkzeug=True)
