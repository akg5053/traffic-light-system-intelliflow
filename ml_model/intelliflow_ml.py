"""
IntelliFlow - Smart Traffic Management System
AI/ML Module for Vehicle Detection, Dynamic Signal Timing & Arduino LED Control
Updated for 2 video inputs (North and East lanes) with proper traffic light cycling
"""

from ultralytics import YOLO
import cv2
import numpy as np
from collections import deque
import time
import json
import serial
from datetime import datetime
import threading
import os


class TrafficSignalController:
    def __init__(self, model_path="yolov8n.pt", north_camera_url=None, east_camera_url=None):
        """Initialize the traffic signal controller with configurable lane inputs"""
        print("🚀 Starting IntelliFlow System...")
        print("📦 Loading YOLOv8 model (this may take a minute first time)...")
        self.model = YOLO(model_path)
        print("✅ Model loaded successfully!")

        # Load configuration
        try:
            import config
            self.config = config
            print("✅ Configuration loaded from config.py")
        except ImportError:
            print("⚠️ config.py not found, using defaults")
            self.config = None
        
        self.lane_order = ["North", "South", "East", "West"]
        self.system_mode = getattr(self.config, 'SYSTEM_MODE', 'TWO_VIDEO') if self.config else 'TWO_VIDEO'
        self.lane_groups = getattr(self.config, 'LANE_GROUPS', {
            "NorthSouth": ["North", "South"],
            "EastWest": ["East", "West"],
        })
        self.lane_sources = self._initialize_lane_sources(north_camera_url, east_camera_url)
        self.active_lanes = [lane for lane in self.lane_order if lane in self.lane_sources]
        if not self.active_lanes:
            raise ValueError("❌ No lane sources configured. Please review config.py or constructor parameters.")

        # Camera capture storage per lane
        self.captures = {}

        # Signal timing parameters (from config or defaults)
        if self.config:
            self.MIN_GREEN = getattr(self.config, 'MIN_GREEN_TIME', 10)
            self.MAX_GREEN = getattr(self.config, 'MAX_GREEN_TIME', 40)
            self.YELLOW_TIME = getattr(self.config, 'YELLOW_TIME', 3)
            self.ALL_RED_TIME = getattr(self.config, 'ALL_RED_TIME', 2)
        else:
            self.MIN_GREEN = 10
            self.MAX_GREEN = 40
            self.YELLOW_TIME = 3
            self.ALL_RED_TIME = 2

        # Vehicle counting per lane
        self.vehicle_history = {lane: deque(maxlen=10) for lane in self.active_lanes}
        self.current_counts = {lane: 0 for lane in self.lane_order}
        self.group_counts = {"NorthSouth": 0, "EastWest": 0}
        self._update_group_counts()

        # Traffic light state
        self.current_phase = "NorthSouth_Green"  # or "EastWest_Green"
        self.phase_start_time = time.time()
        self.current_green_time = self.MIN_GREEN
        self.phase_remaining_time = 0  # Remaining time for current phase
        self.phase_remaining_times = {"NorthSouth": 0, "EastWest": 0}

        # Emergency detection
        self.emergency_detected = False
        self.emergency_lane = None

        # Statistics
        self.total_vehicles_detected = 0
        self.cycles_completed = 0
        self.log_data = []

        # Threading for dual video processing
        self.running = False
        self.frames = {}
        self.encoded_frames = {}
        self.north_frame = None
        self.south_frame = None
        self.east_frame = None
        self.west_frame = None
        self.north_frame_encoded = None
        self.south_frame_encoded = None
        self.east_frame_encoded = None
        self.west_frame_encoded = None
        self.frame_lock = threading.Lock()

        # Video loop support (restart videos when they end)
        self.video_finished_flags = {lane: False for lane in self.active_lanes}

        # Arduino Connection Setup (from config or defaults)
        if self.config:
            arduino_port = getattr(self.config, 'ARDUINO_PORT', 'COM5')
            arduino_baud = getattr(self.config, 'ARDUINO_BAUD_RATE', 9600)
        else:
            arduino_port = 'COM5'
            arduino_baud = 9600
        
        # Try to connect to Arduino with better error handling
        self.arduino = None
        try:
            print(f"\n🔌 Attempting to connect to Arduino on {arduino_port}...")
            
            # Close port if already open (in case of previous failed connection)
            try:
                test_serial = serial.Serial(arduino_port, arduino_baud, timeout=1)
                test_serial.close()
                time.sleep(0.5)
                print(f"   Closed existing connection on {arduino_port}")
            except:
                pass
            
            # Open serial connection
            self.arduino = serial.Serial(arduino_port, arduino_baud, timeout=1)
            print(f"   Serial port opened, waiting for Arduino to reset...")
            time.sleep(5)  # Increased wait time (like test file) - Arduino needs time to reset
            
            # Flush any existing data
            self.arduino.reset_input_buffer()
            self.arduino.reset_output_buffer()
            print(f"   Buffers flushed")
            
            # Verify connection is still open
            if not self.arduino.is_open:
                raise serial.SerialException("Port closed after opening")
            
            # Test connection by sending commands
            print(f"   Testing connection...")
            self.arduino.write(b"L1_R\n")
            self.arduino.flush()
            time.sleep(0.2)
            self.arduino.write(b"L2_R\n")
            self.arduino.flush()
            time.sleep(0.2)
            
            # Try to read any response from Arduino (optional - Arduino might not send response)
            if self.arduino.in_waiting > 0:
                response = self.arduino.read(self.arduino.in_waiting)
                print(f"   Arduino response: {response.decode('utf-8', errors='ignore')}")
            
            print(f"✅ Connected to Arduino ({arduino_port})")
            print(f"✅ Arduino communication test successful")
            print(f"   Port status: {'OPEN' if self.arduino.is_open else 'CLOSED'}")
        except serial.SerialException as e:
            print(f"\n❌ Arduino Serial Error: {e}")
            print(f"   Expected port: {arduino_port}, baud rate: {arduino_baud}")
            print("   System will run without hardware control")
            print("   💡 Make sure Arduino is connected and check COM port in Device Manager")
            print("   💡 Try running: python test_arduino_connection.py to test connection")
            self.arduino = None
        except Exception as e:
            print(f"\n❌ Arduino connection failed: {e}")
            print(f"   Expected port: {arduino_port}, baud rate: {arduino_baud}")
            print("   System will run without hardware control")
            import traceback
            traceback.print_exc()
            self.arduino = None

        print("\n📊 Configuration:")
        print(f"   Min Green Time: {self.MIN_GREEN}s")
        print(f"   Max Green Time: {self.MAX_GREEN}s")
        print(f"   Yellow Time: {self.YELLOW_TIME}s")
        print(f"   Active System Mode: {self.system_mode}")
        for lane in self.active_lanes:
            lane_source = self.lane_sources[lane]
            print(f"   {lane} Source ({lane_source['type']}): {lane_source['open_arg']}")


    # =============================================================
    # Helper Functions
    # =============================================================
    def _initialize_lane_sources(self, north_camera_url, east_camera_url):
        """Resolve lane sources from config or legacy constructor parameters."""
        lane_sources = {}

        if self.config and hasattr(self.config, 'LANE_SOURCES'):
            for lane, settings in self.config.LANE_SOURCES.items():
                lane_sources[lane] = self._resolve_lane_source(lane, settings)
        else:
            # Legacy fallback: only North/East provided via constructor arguments
            fallback_north = {"type": "direct", "source": north_camera_url if north_camera_url is not None else 0}
            fallback_east = {"type": "direct", "source": east_camera_url if east_camera_url is not None else 1}
            lane_sources["North"] = self._resolve_lane_source("North", fallback_north)
            lane_sources["East"] = self._resolve_lane_source("East", fallback_east)

        return lane_sources

    def _resolve_lane_source(self, lane, settings):
        """Normalize lane source configuration into a common dict."""
        if not isinstance(settings, dict):
            settings = {"source": settings}

        source_type = settings.get("type", "direct")
        resolved = {
            "type": source_type,
            "settings": settings,
            "is_video_file": False,
            "open_arg": None,
        }

        if source_type == "video":
            path = settings.get("path")
            if not path:
                raise ValueError(f"Lane {lane} is missing 'path' for video source.")
            resolved["open_arg"] = path
            resolved["is_video_file"] = True
        elif source_type == "ip":
            url = settings.get("url")
            if not url:
                raise ValueError(f"Lane {lane} is missing 'url' for IP camera source.")
            resolved["open_arg"] = url
        elif source_type == "esp32":
            ip = settings.get("ip")
            if not ip:
                raise ValueError(f"Lane {lane} is missing 'ip' for ESP32-CAM source.")
            stream = settings.get("stream", "/stream")
            resolved["open_arg"] = f"http://{ip}{stream}"
        elif source_type == "webcam":
            resolved["open_arg"] = settings.get("index", 0)
        elif source_type == "direct":
            resolved["open_arg"] = settings.get("source")
            if resolved["open_arg"] is None:
                resolved["open_arg"] = settings.get("path") or settings.get("url")
            if isinstance(resolved["open_arg"], str) and os.path.splitext(str(resolved["open_arg"]))[1].lower() in [".mp4", ".mov", ".avi", ".mkv"]:
                resolved["is_video_file"] = True
        else:
            # Generic fallback
            resolved["open_arg"] = settings.get("source") or settings.get("path") or settings.get("url")
            if resolved["open_arg"] is None:
                raise ValueError(f"Lane {lane} has unsupported configuration: {settings}")

        if resolved["open_arg"] is None:
            raise ValueError(f"Lane {lane} has invalid source configuration: {settings}")

        return resolved

    def _update_group_counts(self):
        """Recompute aggregate counts for North/South and East/West groups."""
        for group, lanes in self.lane_groups.items():
            self.group_counts[group] = sum(self.current_counts.get(lane, 0) for lane in lanes)

    def get_group_vehicle_counts(self):
        """Expose current aggregate counts for API usage."""
        return dict(self.group_counts)

    def _update_phase_remaining_times(self):
        """Update remaining time trackers for current phase."""
        try:
            elapsed = time.time() - self.phase_start_time
            signal_timings = self.calculate_green_time(self.current_counts)

            if "Green" in self.current_phase:
                if "NorthSouth" in self.current_phase:
                    remaining = max(0, signal_timings.get("NorthSouth", self.MIN_GREEN) - elapsed)
                    self.phase_remaining_time = remaining
                    self.phase_remaining_times["NorthSouth"] = remaining
                    self.phase_remaining_times["EastWest"] = signal_timings.get("EastWest", self.MIN_GREEN)
                elif "EastWest" in self.current_phase:
                    remaining = max(0, signal_timings.get("EastWest", self.MIN_GREEN) - elapsed)
                    self.phase_remaining_time = remaining
                    self.phase_remaining_times["EastWest"] = remaining
                    self.phase_remaining_times["NorthSouth"] = signal_timings.get("NorthSouth", self.MIN_GREEN)
                else:
                    self.phase_remaining_time = 0
            elif "Yellow" in self.current_phase:
                remaining = max(0, self.YELLOW_TIME - elapsed)
                self.phase_remaining_time = remaining
                if "NorthSouth" in self.current_phase:
                    self.phase_remaining_times["NorthSouth"] = remaining
                    self.phase_remaining_times["EastWest"] = 0
                else:
                    self.phase_remaining_times["EastWest"] = remaining
                    self.phase_remaining_times["NorthSouth"] = 0
            elif "All_Red" in self.current_phase:
                remaining = max(0, self.ALL_RED_TIME - elapsed)
                self.phase_remaining_time = remaining
                self.phase_remaining_times["NorthSouth"] = remaining
                self.phase_remaining_times["EastWest"] = remaining
            else:
                self.phase_remaining_time = 0
                self.phase_remaining_times = {"NorthSouth": 0, "EastWest": 0}
        except Exception:
            self.phase_remaining_time = 0
            self.phase_remaining_times = {"NorthSouth": 0, "EastWest": 0}

    def _combine_frames_for_display(self, frames):
        """Create a tiled view for local debugging display."""
        if not frames:
            return None
        if len(frames) == 1:
            return frames[0]
        if len(frames) == 2:
            return np.hstack(frames)

        padded_frames = list(frames)
        if len(padded_frames) % 2 != 0:
            padded_frames.append(np.zeros_like(padded_frames[0]))

        rows = []
        for idx in range(0, len(padded_frames), 2):
            rows.append(np.hstack((padded_frames[idx], padded_frames[idx + 1])))

        if len(rows) == 1:
            return rows[0]
        return np.vstack(rows)

    def check_arduino_connection(self):
        """Check if Arduino connection is still valid"""
        if not self.arduino:
            return False
        try:
            return self.arduino.is_open
        except:
            return False
    
    def send_signal_to_arduino(self, lane, color):
        """Send signal command to Arduino (e.g., L1_G, L2_R, etc.)"""
        if not self.arduino:
            # Only print warning once per phase to avoid spam
            if not hasattr(self, '_arduino_warning_printed'):
                print("⚠️ Arduino not connected - commands will not be sent")
                self._arduino_warning_printed = True
            return
        
        try:
            # Check if serial port is still open
            if not self.arduino.is_open:
                print("⚠️ Arduino port closed, attempting to reconnect...")
                try:
                    if self.config:
                        arduino_port = getattr(self.config, 'ARDUINO_PORT', 'COM5')
                        arduino_baud = getattr(self.config, 'ARDUINO_BAUD_RATE', 9600)
                    else:
                        arduino_port = 'COM5'
                        arduino_baud = 9600
                    
                    # Close old connection if it exists
                    try:
                        self.arduino.close()
                    except:
                        pass
                    
                    # Reopen connection
                    self.arduino = serial.Serial(arduino_port, arduino_baud, timeout=1)
                    time.sleep(2)  # Wait for Arduino to reset
                    self.arduino.reset_input_buffer()
                    self.arduino.reset_output_buffer()
                    print(f"✅ Reconnected to Arduino ({arduino_port})")
                except Exception as reconnect_error:
                    print(f"❌ Failed to reconnect: {reconnect_error}")
                    self.arduino = None
                    return
            
            # Flush input buffer (clear any pending data)
            if self.arduino.in_waiting > 0:
                self.arduino.reset_input_buffer()
            
            # Send command (same format as test file)
            cmd = f"{lane}_{color}\n"
            cmd_bytes = cmd.encode('utf-8')
            
            # Write command
            bytes_written = self.arduino.write(cmd_bytes)
            self.arduino.flush()  # Ensure data is sent immediately
            
            # Verify command was written
            if bytes_written != len(cmd_bytes):
                print(f"⚠️ Warning: Only {bytes_written} bytes written, expected {len(cmd_bytes)}")
            
            # Small delay to ensure command is processed by Arduino
            time.sleep(0.1)
            
            # Print confirmation (only for important state changes to reduce spam)
            if color in ['G', 'R']:  # Only log Green and Red (not Yellow to reduce spam)
                print(f"➡️ Arduino: {cmd.strip()} ({bytes_written} bytes sent)")
            
        except serial.SerialException as e:
            print(f"❌ Serial error sending to Arduino: {e}")
            print(f"   Command was: {lane}_{color}")
            try:
                self.arduino.close()
            except:
                pass
            self.arduino = None
        except Exception as e:
            print(f"❌ Failed to send to Arduino: {e}")
            print(f"   Command was: {lane}_{color}")
            import traceback
            traceback.print_exc()
            try:
                if self.arduino:
                    self.arduino.close()
            except:
                pass
            self.arduino = None

    def connect_cameras(self):
        """Connect to configured cameras for all active lanes"""
        print(f"\n📷 Connecting to cameras...")
        for lane in self.active_lanes:
            lane_source = self.lane_sources[lane]
            source_arg = lane_source["open_arg"]
            print(f"   {lane} Lane: {source_arg}")

            cap = cv2.VideoCapture(source_arg)
            if not cap.isOpened():
                raise Exception(f"❌ Failed to connect to {lane} camera: {source_arg}")

            # Standardize frame size for layout consistency
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.captures[lane] = cap
            print(f"✅ {lane} camera connected!")
        return True

    def detect_vehicles(self, frame):
        """Detect vehicles using YOLOv8"""
        if self.config:
            conf = getattr(self.config, 'DETECTION_CONFIDENCE', 0.4)
            classes = getattr(self.config, 'VEHICLE_CLASSES', [2, 3, 5, 7])
        else:
            conf = 0.4
            classes = [2, 3, 5, 7]
        results = self.model(frame, conf=conf, classes=classes, verbose=False)
        return results[0].boxes

    def count_vehicles_in_frame(self, boxes, frame, lane_name):
        """Count vehicles in entire frame (detect ALL vehicles, not just specific regions)"""
        if boxes is None or len(boxes.xyxy) == 0:
            return 0
        
        vehicle_count = len(boxes.xyxy)
        # Draw bounding boxes on ALL detected vehicles in the entire frame
        for i, box in enumerate(boxes.xyxy):
            x1, y1, x2, y2 = map(int, box)
            # Draw green bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            # Add vehicle label with count
            label = f"Vehicle {i+1}"
            cv2.putText(frame, label, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        return vehicle_count

    def smooth_vehicle_counts(self, latest_counts):
        """Apply temporal smoothing to vehicle counts for all active lanes"""
        smoothed = {}
        for lane in self.active_lanes:
            history = self.vehicle_history.setdefault(lane, deque(maxlen=10))
            value = latest_counts.get(lane, 0)
            history.append(value)
            smoothed[lane] = int(np.mean(history)) if history else 0

        # Ensure inactive lanes remain zero
        for lane in self.lane_order:
            if lane not in smoothed:
                smoothed[lane] = 0

        return smoothed

    def calculate_green_time(self, vehicle_counts, current_phase=None, phase_elapsed=0):
        """
        PREDICTIVE Emergency Vehicle Preemption Logic
        NEVER cuts countdowns - only influences FUTURE light changes
        
        Calculate dynamic green time based on vehicle counts and EV state.
        If EV is active, calculates when EV lane MUST be green and plans accordingly.
        """
        # Check for Emergency Vehicle Preemption state
        evp_state = self._load_evp_state()
        
        # Calculate normal green times first (without EV consideration)
        north_group = sum(vehicle_counts.get(lane, 0) for lane in self.lane_groups.get("NorthSouth", []))
        east_group = sum(vehicle_counts.get(lane, 0) for lane in self.lane_groups.get("EastWest", []))
        total_vehicles = north_group + east_group
        
        if total_vehicles == 0:
            base_north = self.MIN_GREEN
            base_east = self.MIN_GREEN
        else:
            if north_group > east_group:
                base_north = min(self.MAX_GREEN, max(self.MIN_GREEN, north_group * 2))
                base_east = min(self.MAX_GREEN, max(self.MIN_GREEN, east_group * 2))
            elif east_group > north_group:
                base_east = min(self.MAX_GREEN, max(self.MIN_GREEN, east_group * 2))
                base_north = min(self.MAX_GREEN, max(self.MIN_GREEN, north_group * 2))
            else:
                green_time = min(self.MAX_GREEN, max(self.MIN_GREEN, total_vehicles))
                base_north = green_time
                base_east = green_time
        
        # If no EV active, return normal times
        if not evp_state.get("active") or not evp_state.get("lane"):
            return {"NorthSouth": int(base_north), "EastWest": int(base_east)}
        
        ev_lane = evp_state["lane"]
        expected_arrival = evp_state.get("expected_arrival_ts", 0)
        ev_remaining = max(0, expected_arrival - time.time())
        
        # Determine which group the EV is coming from
        ev_group = None
        if ev_lane in self.lane_groups.get("NorthSouth", []):
            ev_group = "NorthSouth"
        elif ev_lane in self.lane_groups.get("EastWest", []):
            ev_group = "EastWest"
        
        if not ev_group or ev_remaining <= 0:
            return {"NorthSouth": int(base_north), "EastWest": int(base_east)}
        
        # PREDICTIVE LOGIC: Calculate when EV lane MUST be green
        MANDATORY_GREEN_THRESHOLD = 10  # EV lane must be green when <10s away
        must_be_green_at = ev_remaining - MANDATORY_GREEN_THRESHOLD
        
        # Get current phase info if available
        if current_phase is None:
            current_phase = getattr(self, 'current_phase', 'All_Red')
        
        # Determine which group is currently active
        current_group = None
        if "NorthSouth" in current_phase:
            current_group = "NorthSouth"
        elif "EastWest" in current_phase:
            current_group = "EastWest"
        
        # Calculate how much time current phase has remaining
        # This is CRITICAL - we NEVER cut this time
        if current_phase and hasattr(self, 'phase_start_time'):
            phase_elapsed = time.time() - self.phase_start_time
        
        # If we're in a green phase, estimate remaining time
        current_phase_remaining = 0
        if "Green" in current_phase:
            # Estimate remaining based on signal timings
            if current_group == "NorthSouth":
                current_phase_remaining = max(0, base_north - phase_elapsed)
            elif current_group == "EastWest":
                current_phase_remaining = max(0, base_east - phase_elapsed)
        
        # Add yellow and all-red time to get total time until next phase can start
        time_until_next_phase = current_phase_remaining
        if "Green" in current_phase:
            time_until_next_phase += self.YELLOW_TIME + self.ALL_RED_TIME
        
        # PREDICTIVE CALCULATION
        if ev_group == "NorthSouth":
            # EV coming from North/South
            if current_group == "NorthSouth" and "Green" in current_phase:
                # EV lane is currently green - extend it to cover EV arrival
                # Calculate how long it needs to stay green
                vehicles_in_ev_lane = north_group
                clearing_time = max(20, vehicles_in_ev_lane * 2)  # Time to clear vehicles
                needed_duration = max(
                    int(ev_remaining + 10),  # Stay green until EV passes + buffer
                    clearing_time,  # Or enough to clear vehicles
                    base_north  # Or at least normal time
                )
                return {
                    "NorthSouth": int(min(self.MAX_GREEN, needed_duration)),
                    "EastWest": int(self.MIN_GREEN)  # Non-EV lane gets minimal time next
                }
            elif current_group == "EastWest" and "Green" in current_phase:
                # Non-EV lane is green - let it finish, but limit next green time
                # Check if we have time for East/West to finish + transition
                if time_until_next_phase <= must_be_green_at - 15:
                    # We have time - let East/West finish, then give North/South enough time
                    return {
                        "NorthSouth": int(min(self.MAX_GREEN, max(base_north, int(ev_remaining + 10)))),
                        "EastWest": int(base_east)  # Let current green finish normally
                    }
                else:
                    # Not enough time - limit East/West to minimum after current finishes
                    return {
                        "NorthSouth": int(min(self.MAX_GREEN, max(base_north, int(ev_remaining + 10)))),
                        "EastWest": int(self.MIN_GREEN)
                    }
            else:
                # Not in green phase - can start EV lane green immediately
                vehicles_in_ev_lane = north_group
                clearing_time = max(20, vehicles_in_ev_lane * 2)
                needed_duration = max(
                    int(ev_remaining + 10),
                    clearing_time,
                    base_north
                )
                return {
                    "NorthSouth": int(min(self.MAX_GREEN, needed_duration)),
                    "EastWest": int(self.MIN_GREEN)
                }
        else:
            # EV coming from East/West (same logic, reversed)
            if current_group == "EastWest" and "Green" in current_phase:
                # EV lane is currently green - extend it
                vehicles_in_ev_lane = east_group
                clearing_time = max(20, vehicles_in_ev_lane * 2)
                needed_duration = max(
                    int(ev_remaining + 10),
                    clearing_time,
                    base_east
                )
                return {
                    "NorthSouth": int(self.MIN_GREEN),
                    "EastWest": int(min(self.MAX_GREEN, needed_duration))
                }
            elif current_group == "NorthSouth" and "Green" in current_phase:
                # Non-EV lane is green - let it finish, but limit next green time
                if time_until_next_phase <= must_be_green_at - 15:
                    return {
                        "NorthSouth": int(base_north),  # Let current green finish normally
                        "EastWest": int(min(self.MAX_GREEN, max(base_east, int(ev_remaining + 10))))
                    }
                else:
                    return {
                        "NorthSouth": int(self.MIN_GREEN),
                        "EastWest": int(min(self.MAX_GREEN, max(base_east, int(ev_remaining + 10))))
                    }
            else:
                # Not in green phase - can start EV lane green immediately
                vehicles_in_ev_lane = east_group
                clearing_time = max(20, vehicles_in_ev_lane * 2)
                needed_duration = max(
                    int(ev_remaining + 10),
                    clearing_time,
                    base_east
                )
                return {
                    "NorthSouth": int(self.MIN_GREEN),
                    "EastWest": int(min(self.MAX_GREEN, needed_duration))
                }
    
    def _load_evp_state(self):
        """Load emergency vehicle preemption state from JSON file"""
        ev_state_file = "emergency_state.json"
        if not os.path.exists(ev_state_file):
            return {"active": False, "lane": None}
        try:
            with open(ev_state_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"active": False, "lane": None}

    def handle_emergency_vehicle(self, emergency_lane):
        """Handle emergency vehicle"""
        self.emergency_detected = True
        self.emergency_lane = emergency_lane
        print(f"\n🚨 EMERGENCY VEHICLE DETECTED IN {emergency_lane}")
        # Emergency: give 30s green to emergency lane, 5s to other
        if emergency_lane in ("North", "South"):
            return {"NorthSouth": 30, "EastWest": 5}
        else:
            return {"NorthSouth": 5, "EastWest": 30}

    def log_statistics(self, vehicle_counts, signal_timings, current_phase):
        """Log data + notify dashboard"""
        avg_wait_traditional = 90
        avg_wait_intelliflow = (signal_timings["NorthSouth"] + signal_timings["EastWest"]) / 2

        lane_counts = {lane: vehicle_counts.get(lane, 0) for lane in self.lane_order}
        group_counts = {
            group: sum(lane_counts.get(lane, 0) for lane in lanes)
            for group, lanes in self.lane_groups.items()
        }
        total_vehicles = sum(lane_counts.values())

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "vehicle_counts": lane_counts,
            "group_counts": group_counts,
            "signal_timings": signal_timings,
            "current_phase": current_phase,
            "total_vehicles": total_vehicles,
            "emergency": self.emergency_detected,
            "avg_wait_time_traditional": avg_wait_traditional,
            "avg_wait_time_intelliflow": avg_wait_intelliflow,
            "time_saved": avg_wait_traditional - avg_wait_intelliflow,
            "efficiency_improvement": round(((avg_wait_traditional - avg_wait_intelliflow)
                                             / avg_wait_traditional) * 100, 2)
        }

        self.log_data.append(log_entry)
        self.total_vehicles_detected = total_vehicles

        with open('traffic_log.json', 'w') as f:
            json.dump(self.log_data, f, indent=2)

        try:
            import requests
            requests.get("http://127.0.0.1:5000/notify_update", timeout=1)
            print("🌐 Dashboard notified for live update.")
        except Exception as e:
            print(f"⚠️ Dashboard update failed: {e}")

        print(f"\n📈 Statistics Updated:")
        print(f"   Time Saved: {log_entry['time_saved']:.1f}s per cycle")
        print(f"   Efficiency: {log_entry['efficiency_improvement']}% better")

    def draw_info_panel(self, frame, lane_name, vehicle_count, phase_info=""):
        """Draw info panel on frame"""
        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, h - 150), (400, h - 10), (0, 0, 0), -1)
        frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)
        y_offset = h - 130
        
        cv2.putText(frame, f"{lane_name} LANE", (20, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        y_offset += 30
        
        cv2.putText(frame, f"Vehicles: {vehicle_count}", (20, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        y_offset += 25
        
        if phase_info:
            cv2.putText(frame, phase_info, (20, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        
        cv2.putText(frame, f"Total: {self.total_vehicles_detected}",
                    (20, h - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
        
        if self.emergency_detected:
            cv2.rectangle(frame, (w - 200, 10), (w - 10, 60), (0, 0, 255), -1)
            cv2.putText(frame, "EMERGENCY", (w - 190, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        return frame

    # =============================================================
    # Main Loop
    # =============================================================
    def process_video_feeds(self):
        """Process configured video feeds - detect vehicles and stream to web"""
        self.running = True
        frame_count = 0
        
        while self.running:
            lane_frames = {}
            latest_counts = {}

            for lane in self.active_lanes:
                cap = self.captures.get(lane)
                if not cap:
                    continue

                ret, frame = cap.read()
                if not ret:
                    lane_source = self.lane_sources[lane]
                    if lane_source.get("is_video_file"):
                        if not self.video_finished_flags.get(lane, False):
                            print(f"🔄 {lane} video ended, restarting...")
                            self.video_finished_flags[lane] = True
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, frame = cap.read()
                        if ret:
                            self.video_finished_flags[lane] = False

                if not ret:
                    continue

                boxes = self.detect_vehicles(frame)
                latest_counts[lane] = self.count_vehicles_in_frame(boxes, frame, lane)
                lane_frames[lane] = frame

            if not lane_frames:
                time.sleep(0.1)
                continue

            self.current_counts.update(self.smooth_vehicle_counts(latest_counts))
            self._update_group_counts()
            self.total_vehicles_detected = sum(self.group_counts.values())
            self._update_phase_remaining_times()

            phase_info = f"Phase: {self.current_phase}"

            with self.frame_lock:
                for lane, frame in lane_frames.items():
                    label = f"{lane.upper()}"
                    vehicle_count = self.current_counts.get(lane, 0)
                    frame = self.draw_info_panel(frame, label, vehicle_count, phase_info)
                    cv2.putText(frame, f"{lane} Lane - Vehicles: {vehicle_count}", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

                    self.frames[lane] = frame.copy()
                    success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    if success:
                        encoded = buffer.tobytes()
                        self.encoded_frames[lane] = encoded

                        if lane == "North":
                            self.north_frame = frame.copy()
                            self.north_frame_encoded = encoded
                        elif lane == "South":
                            self.south_frame = frame.copy()
                            self.south_frame_encoded = encoded
                        elif lane == "East":
                            self.east_frame = frame.copy()
                            self.east_frame_encoded = encoded
                        elif lane == "West":
                            self.west_frame = frame.copy()
                            self.west_frame_encoded = encoded

            # Display frames locally (optional - can be disabled for headless server)
            try:
                display_frames = [self.frames[lane] for lane in self.lane_order if lane in self.frames]
                combined_frame = self._combine_frames_for_display(display_frames)
                if combined_frame is not None:
                    cv2.imshow('IntelliFlow - Traffic Video System', combined_frame)

                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        self.running = False
                        break
                    elif key == ord('e'):
                        self.emergency_detected = True
                        self.emergency_lane = "North"
                        print("\n🚨 EMERGENCY MODE ACTIVATED!")
                    elif key == ord('r'):
                        self.total_vehicles_detected = 0
                        self.cycles_completed = 0
                        self.log_data = []
                        print("\n🔄 Statistics reset!")
            except cv2.error:
                # No display available (headless server) - continue without showing
                pass

            frame_count += 1
            time.sleep(0.033)  # ~30 FPS
    
    def run_traffic_control(self):
        """Main traffic light control loop with proper cycling"""
        print("\n" + "=" * 60)
        print("🚦 IntelliFlow Traffic Management System Started")
        print("=" * 60)
        print("\n📋 Controls:")
        print("   Press 'q' to quit")
        print("   Press 'e' to simulate emergency vehicle")
        print("   Press 'r' to reset statistics")
        print("\n⏳ Traffic lights will cycle based on vehicle counts...")
        print("=" * 60 + "\n")
        
        try:
            while self.running:
                # Check EV state at the start of each cycle
                evp_state = self._load_evp_state()
                ev_active = evp_state.get("active", False)
                ev_lane = evp_state.get("lane")
                ev_remaining = 0
                ev_group = None
                
                if ev_active and ev_lane:
                    expected_arrival = evp_state.get("expected_arrival_ts", 0)
                    ev_remaining = max(0, expected_arrival - time.time())
                    if ev_lane in self.lane_groups.get("NorthSouth", []):
                        ev_group = "NorthSouth"
                    elif ev_lane in self.lane_groups.get("EastWest", []):
                        ev_group = "EastWest"
                
                # Calculate green times based on current vehicle counts
                # Pass current phase info so calculate_green_time can plan ahead
                current_phase_for_calc = getattr(self, 'current_phase', 'All_Red')
                phase_elapsed = 0
                if hasattr(self, 'phase_start_time'):
                    phase_elapsed = time.time() - self.phase_start_time
                
                if self.emergency_detected:
                    signal_timings = self.handle_emergency_vehicle(self.emergency_lane)
                    self.emergency_detected = False
                else:
                    signal_timings = self.calculate_green_time(
                        self.current_counts, 
                        current_phase=current_phase_for_calc,
                        phase_elapsed=phase_elapsed
                    )
                self._update_group_counts()
                
                print(f"\n{'=' * 60}")
                print(f"⏱️  Cycle #{self.cycles_completed + 1}")
                if ev_active:
                    print(f"🚑 EMERGENCY VEHICLE ACTIVE: {ev_lane} lane, {int(ev_remaining)}s remaining")
                print(f"{'=' * 60}")
                print(f"\n📊 Vehicle Counts:")
                for lane in self.active_lanes:
                    print(f"   {lane} Lane: {self.current_counts.get(lane, 0)} vehicles")
                print(f"\n📊 Group Totals:")
                print(f"   North/South Total: {self.group_counts.get('NorthSouth', 0)} vehicles")
                print(f"   East/West Total: {self.group_counts.get('EastWest', 0)} vehicles")
                print(f"\n⏱️  Calculated Signal Timings:")
                print(f"   North/South: {signal_timings['NorthSouth']}s GREEN")
                print(f"   East/West: {signal_timings['EastWest']}s GREEN")
                
                # =====================================
                # 🔴🟡🟢 Traffic Light Cycle
                # =====================================
                # Phase 1: North/South GREEN, East/West RED
                # Check EV state RIGHT BEFORE starting phase
                evp_state_check = self._load_evp_state()
                ev_check_active = evp_state_check.get("active", False)
                ev_check_lane = evp_state_check.get("lane")
                ev_check_remaining = 0
                ev_check_group = None
                
                if ev_check_active and ev_check_lane:
                    ev_check_arrival = evp_state_check.get("expected_arrival_ts", 0)
                    ev_check_remaining = max(0, ev_check_arrival - time.time())
                    if ev_check_lane in self.lane_groups.get("NorthSouth", []):
                        ev_check_group = "NorthSouth"
                    elif ev_check_lane in self.lane_groups.get("EastWest", []):
                        ev_check_group = "EastWest"
                
                # CRITICAL: If EV is <10s away, EV lane MUST be green
                if ev_check_active and ev_check_remaining <= 10 and ev_check_group == "EastWest":
                    # EV is coming from East/West - skip North/South, go directly to East/West
                    print(f"🚑 EV CRITICAL: {ev_check_lane} lane, {int(ev_check_remaining)}s - Skipping North/South, going to East/West")
                    # Skip to Phase 4 (East/West Green)
                    green_time_ew = signal_timings['EastWest']
                    # Ensure EV lane gets enough time
                    if ev_check_remaining > 0:
                        green_time_ew = max(green_time_ew, int(ev_check_remaining + 15))  # Stay green until EV passes
                    print(f"\n🟢 Phase 4 (EV PRIORITY): East/West GREEN ({green_time_ew}s)")
                    self.current_phase = "EastWest_Green"
                    self.phase_start_time = time.time()
                    self.phase_remaining_time = green_time_ew
                    self.phase_remaining_times = {"NorthSouth": 0, "EastWest": green_time_ew}
                    self.send_signal_to_arduino("L1", "R")  # North/South red
                    time.sleep(0.1)
                    self.send_signal_to_arduino("L2", "G")  # East/West green
                    start_time = time.time()
                    last_push_time = time.time()
                    ev_keep_green_priority_ew = False
                    while time.time() - start_time < green_time_ew or ev_keep_green_priority_ew:
                        # Check EV state - keep green if <10s
                        evp_state_priority = self._load_evp_state()
                        if evp_state_priority.get("active") and evp_state_priority.get("lane"):
                            ev_priority_lane = evp_state_priority["lane"]
                            ev_priority_arrival = evp_state_priority.get("expected_arrival_ts", 0)
                            ev_priority_remaining = max(0, ev_priority_arrival - time.time())
                            if ev_priority_lane in self.lane_groups.get("EastWest", []):
                                if ev_priority_remaining <= 10:
                                    if not ev_keep_green_priority_ew:
                                        print(f"🚑 EV CRITICAL: Keeping East/West green until EV clears")
                                    ev_keep_green_priority_ew = True
                                    self.phase_remaining_time = -1
                                    self.phase_remaining_times["EastWest"] = -1
                                else:
                                    if ev_keep_green_priority_ew:
                                        ev_keep_green_priority_ew = False
                                        break
                            else:
                                if ev_keep_green_priority_ew:
                                    ev_keep_green_priority_ew = False
                                    break
                        else:
                            if ev_keep_green_priority_ew:
                                print(f"✅ EV cleared - resuming normal cycle")
                                ev_keep_green_priority_ew = False
                                break
                        
                        if not ev_keep_green_priority_ew:
                            elapsed = time.time() - self.phase_start_time
                            remaining = max(0, green_time_ew - elapsed)
                            self.phase_remaining_time = remaining
                            self.phase_remaining_times["EastWest"] = remaining
                        if time.time() - last_push_time >= 0.5:
                            try:
                                from dashboard import push_live_update
                                push_live_update()
                                last_push_time = time.time()
                            except:
                                pass
                        time.sleep(0.1)
                    # Skip to end of cycle after EV lane green
                    self.log_statistics(self.current_counts, signal_timings, self.current_phase)
                    self.cycles_completed += 1
                    continue
                
                # Normal North/South phase
                green_time_ns = signal_timings['NorthSouth']
                # If EV is coming from North/South and <10s, extend green time
                if ev_check_active and ev_check_remaining <= 10 and ev_check_group == "NorthSouth":
                    green_time_ns = max(green_time_ns, int(ev_check_remaining + 15))  # Stay green until EV passes
                    print(f"🚑 EV CRITICAL: {ev_check_lane} lane, {int(ev_check_remaining)}s - Extending North/South green to {green_time_ns}s")
                
                print(f"\n🟢 Phase 1: North/South GREEN ({green_time_ns}s)")
                self.current_phase = "NorthSouth_Green"
                self.phase_start_time = time.time()  # Reset phase start time
                self.phase_remaining_time = green_time_ns  # Set initial remaining time
                self.phase_remaining_times = {"NorthSouth": green_time_ns, "EastWest": 0}
                self.send_signal_to_arduino("L1", "G")  # North/South green
                time.sleep(0.1)  # Delay between commands
                self.send_signal_to_arduino("L2", "R")  # East/West red
                start_time = time.time()
                last_push_time = time.time()
                ev_keep_green_ns = False
                while time.time() - start_time < green_time_ns or ev_keep_green_ns:
                    # Check EV state DURING phase
                    evp_state_during = self._load_evp_state()
                    if evp_state_during.get("active") and evp_state_during.get("lane"):
                        ev_during_lane = evp_state_during["lane"]
                        ev_during_arrival = evp_state_during.get("expected_arrival_ts", 0)
                        ev_during_remaining = max(0, ev_during_arrival - time.time())
                        ev_during_group = None
                        if ev_during_lane in self.lane_groups.get("NorthSouth", []):
                            ev_during_group = "NorthSouth"
                        elif ev_during_lane in self.lane_groups.get("EastWest", []):
                            ev_during_group = "EastWest"
                        
                        # CRITICAL: If EV is <10s and we're in EV lane, keep it green indefinitely
                        if ev_during_remaining <= 10 and ev_during_group == "NorthSouth":
                            # EV from North/South and we're in North/South - keep green!
                            if not ev_keep_green_ns:
                                print(f"🚑 EV CRITICAL: {ev_during_lane} lane, {int(ev_during_remaining)}s - Keeping North/South green until EV clears")
                            ev_keep_green_ns = True
                            # Set special value for "--" display
                            self.phase_remaining_time = -1
                            self.phase_remaining_times["NorthSouth"] = -1
                        # CRITICAL: If EV is <10s and we're in wrong phase, transition NOW
                        elif ev_during_remaining <= 10 and ev_during_group == "EastWest":
                            # EV from East/West but we're in North/South - transition immediately
                            print(f"🚑 EV CRITICAL DURING PHASE: {ev_during_lane} lane, {int(ev_during_remaining)}s - Transitioning to East/West NOW")
                            ev_keep_green_ns = False
                            break  # Exit current phase loop
                        else:
                            # EV not critical or cleared
                            if ev_keep_green_ns:
                                print(f"✅ EV cleared or passed - resuming normal cycle")
                                ev_keep_green_ns = False
                                break
                    else:
                        # EV cleared
                        if ev_keep_green_ns:
                            print(f"✅ EV cleared - resuming normal cycle")
                            ev_keep_green_ns = False
                            break
                    
                    # Update remaining time continuously (only if not in EV keep-green mode)
                    if not ev_keep_green_ns:
                        elapsed = time.time() - self.phase_start_time
                        remaining = max(0, green_time_ns - elapsed)
                        self.phase_remaining_time = remaining
                        self.phase_remaining_times["NorthSouth"] = remaining
                    # Push updates to web dashboard every 0.5 seconds
                    if time.time() - last_push_time >= 0.5:
                        try:
                            from dashboard import push_live_update
                            push_live_update()
                            last_push_time = time.time()
                        except:
                            pass
                    time.sleep(0.1)  # Update more frequently
                
                # After North/South green, check if we need to skip to EV lane
                evp_state_after = self._load_evp_state()
                if evp_state_after.get("active") and evp_state_after.get("lane"):
                    ev_after_lane = evp_state_after["lane"]
                    ev_after_arrival = evp_state_after.get("expected_arrival_ts", 0)
                    ev_after_remaining = max(0, ev_after_arrival - time.time())
                    ev_after_group = None
                    if ev_after_lane in self.lane_groups.get("NorthSouth", []):
                        ev_after_group = "NorthSouth"
                    elif ev_after_lane in self.lane_groups.get("EastWest", []):
                        ev_after_group = "EastWest"
                    
                    if ev_after_remaining <= 10 and ev_after_group == "EastWest":
                        # Skip yellow and all-red, go directly to East/West green
                        print(f"🚑 EV CRITICAL: Skipping yellow/all-red, going to East/West green")
                        green_time_ew_emergency = signal_timings['EastWest']
                        if ev_after_remaining > 0:
                            green_time_ew_emergency = max(green_time_ew_emergency, int(ev_after_remaining + 15))
                        print(f"\n🟢 Phase 4 (EV PRIORITY): East/West GREEN ({green_time_ew_emergency}s)")
                        self.current_phase = "EastWest_Green"
                        self.phase_start_time = time.time()
                        self.phase_remaining_time = green_time_ew_emergency
                        self.phase_remaining_times = {"NorthSouth": 0, "EastWest": green_time_ew_emergency}
                        self.send_signal_to_arduino("L1", "R")
                        time.sleep(0.1)
                        self.send_signal_to_arduino("L2", "G")
                        start_time = time.time()
                        last_push_time = time.time()
                        ev_keep_green_emergency_ew = False
                        while time.time() - start_time < green_time_ew_emergency or ev_keep_green_emergency_ew:
                            # Check EV state - keep green if <10s
                            evp_state_emergency = self._load_evp_state()
                            if evp_state_emergency.get("active") and evp_state_emergency.get("lane"):
                                ev_emergency_lane = evp_state_emergency["lane"]
                                ev_emergency_arrival = evp_state_emergency.get("expected_arrival_ts", 0)
                                ev_emergency_remaining = max(0, ev_emergency_arrival - time.time())
                                if ev_emergency_lane in self.lane_groups.get("EastWest", []):
                                    if ev_emergency_remaining <= 10:
                                        if not ev_keep_green_emergency_ew:
                                            print(f"🚑 EV CRITICAL: Keeping East/West green until EV clears")
                                        ev_keep_green_emergency_ew = True
                                        self.phase_remaining_time = -1
                                        self.phase_remaining_times["EastWest"] = -1
                                    else:
                                        if ev_keep_green_emergency_ew:
                                            ev_keep_green_emergency_ew = False
                                            break
                                else:
                                    if ev_keep_green_emergency_ew:
                                        ev_keep_green_emergency_ew = False
                                        break
                            else:
                                if ev_keep_green_emergency_ew:
                                    print(f"✅ EV cleared - resuming normal cycle")
                                    ev_keep_green_emergency_ew = False
                                    break
                            
                            if not ev_keep_green_emergency_ew:
                                elapsed = time.time() - self.phase_start_time
                                remaining = max(0, green_time_ew_emergency - elapsed)
                                self.phase_remaining_time = remaining
                                self.phase_remaining_times["EastWest"] = remaining
                            if time.time() - last_push_time >= 0.5:
                                try:
                                    from dashboard import push_live_update
                                    push_live_update()
                                    last_push_time = time.time()
                                except:
                                    pass
                            time.sleep(0.1)
                        self.log_statistics(self.current_counts, signal_timings, self.current_phase)
                        self.cycles_completed += 1
                        continue
                
                # Phase 2: North/South YELLOW, East/West RED
                # GOLDEN RULE: Always complete the full countdown
                print(f"🟡 Phase 2: North/South YELLOW ({self.YELLOW_TIME}s)")
                self.current_phase = "NorthSouth_Yellow"
                self.phase_start_time = time.time()  # Reset phase start time
                self.phase_remaining_time = self.YELLOW_TIME  # Set initial remaining time
                self.phase_remaining_times = {"NorthSouth": self.YELLOW_TIME, "EastWest": 0}
                self.send_signal_to_arduino("L1", "Y")
                time.sleep(0.1)
                self.send_signal_to_arduino("L2", "R")
                start_time = time.time()
                last_push_time = time.time()
                while time.time() - start_time < self.YELLOW_TIME:
                    # Update remaining time continuously
                    elapsed = time.time() - self.phase_start_time
                    remaining = max(0, self.YELLOW_TIME - elapsed)
                    self.phase_remaining_time = remaining
                    self.phase_remaining_times["NorthSouth"] = remaining
                    self.phase_remaining_times["EastWest"] = 0
                    # Push updates to web dashboard every 0.5 seconds
                    if time.time() - last_push_time >= 0.5:
                        try:
                            from dashboard import push_live_update
                            push_live_update()
                            last_push_time = time.time()
                        except:
                            pass
                    time.sleep(0.1)
                
                # Phase 3: ALL RED (safety buffer)
                # GOLDEN RULE: Always complete the full countdown
                print(f"🔴 Phase 3: ALL RED ({self.ALL_RED_TIME}s)")
                self.current_phase = "All_Red"
                self.phase_start_time = time.time()  # Reset phase start time
                self.phase_remaining_time = self.ALL_RED_TIME  # Set initial remaining time
                self.phase_remaining_times = {"NorthSouth": self.ALL_RED_TIME, "EastWest": self.ALL_RED_TIME}
                self.send_signal_to_arduino("L1", "R")
                time.sleep(0.1)
                self.send_signal_to_arduino("L2", "R")
                start_time = time.time()
                last_push_time = time.time()
                while time.time() - start_time < self.ALL_RED_TIME:
                    # Update remaining time continuously
                    elapsed = time.time() - self.phase_start_time
                    remaining = max(0, self.ALL_RED_TIME - elapsed)
                    self.phase_remaining_time = remaining
                    self.phase_remaining_times["NorthSouth"] = remaining
                    self.phase_remaining_times["EastWest"] = remaining
                    # Push updates to web dashboard every 0.5 seconds
                    if time.time() - last_push_time >= 0.5:
                        try:
                            from dashboard import push_live_update
                            push_live_update()
                            last_push_time = time.time()
                        except:
                            pass
                    time.sleep(0.1)
                
                # Phase 4: East/West GREEN, North/South RED
                # Check EV state RIGHT BEFORE starting phase
                evp_state_check2 = self._load_evp_state()
                ev_check_active2 = evp_state_check2.get("active", False)
                ev_check_lane2 = evp_state_check2.get("lane")
                ev_check_remaining2 = 0
                ev_check_group2 = None
                
                if ev_check_active2 and ev_check_lane2:
                    ev_check_arrival2 = evp_state_check2.get("expected_arrival_ts", 0)
                    ev_check_remaining2 = max(0, ev_check_arrival2 - time.time())
                    if ev_check_lane2 in self.lane_groups.get("NorthSouth", []):
                        ev_check_group2 = "NorthSouth"
                    elif ev_check_lane2 in self.lane_groups.get("EastWest", []):
                        ev_check_group2 = "EastWest"
                
                # CRITICAL: If EV is <10s away from North/South, skip East/West
                if ev_check_active2 and ev_check_remaining2 <= 10 and ev_check_group2 == "NorthSouth":
                    # EV is coming from North/South - skip East/West, go back to North/South
                    print(f"🚑 EV CRITICAL: {ev_check_lane2} lane, {int(ev_check_remaining2)}s - Skipping East/West, going to North/South")
                    green_time_ns_ev = signal_timings['NorthSouth']
                    # Ensure EV lane gets enough time
                    if ev_check_remaining2 > 0:
                        green_time_ns_ev = max(green_time_ns_ev, int(ev_check_remaining2 + 15))  # Stay green until EV passes
                    print(f"\n🟢 Phase 1 (EV PRIORITY): North/South GREEN ({green_time_ns_ev}s)")
                    self.current_phase = "NorthSouth_Green"
                    self.phase_start_time = time.time()
                    self.phase_remaining_time = green_time_ns_ev
                    self.phase_remaining_times = {"NorthSouth": green_time_ns_ev, "EastWest": 0}
                    self.send_signal_to_arduino("L1", "G")  # North/South green
                    time.sleep(0.1)
                    self.send_signal_to_arduino("L2", "R")  # East/West red
                    start_time = time.time()
                    last_push_time = time.time()
                    ev_keep_green_priority_ns = False
                    while time.time() - start_time < green_time_ns_ev or ev_keep_green_priority_ns:
                        # Check EV state - keep green if <10s
                        evp_state_priority_ns = self._load_evp_state()
                        if evp_state_priority_ns.get("active") and evp_state_priority_ns.get("lane"):
                            ev_priority_lane_ns = evp_state_priority_ns["lane"]
                            ev_priority_arrival_ns = evp_state_priority_ns.get("expected_arrival_ts", 0)
                            ev_priority_remaining_ns = max(0, ev_priority_arrival_ns - time.time())
                            if ev_priority_lane_ns in self.lane_groups.get("NorthSouth", []):
                                if ev_priority_remaining_ns <= 10:
                                    if not ev_keep_green_priority_ns:
                                        print(f"🚑 EV CRITICAL: Keeping North/South green until EV clears")
                                    ev_keep_green_priority_ns = True
                                    self.phase_remaining_time = -1
                                    self.phase_remaining_times["NorthSouth"] = -1
                                else:
                                    if ev_keep_green_priority_ns:
                                        ev_keep_green_priority_ns = False
                                        break
                            else:
                                if ev_keep_green_priority_ns:
                                    ev_keep_green_priority_ns = False
                                    break
                        else:
                            if ev_keep_green_priority_ns:
                                print(f"✅ EV cleared - resuming normal cycle")
                                ev_keep_green_priority_ns = False
                                break
                        
                        if not ev_keep_green_priority_ns:
                            elapsed = time.time() - self.phase_start_time
                            remaining = max(0, green_time_ns_ev - elapsed)
                            self.phase_remaining_time = remaining
                            self.phase_remaining_times["NorthSouth"] = remaining
                        if time.time() - last_push_time >= 0.5:
                            try:
                                from dashboard import push_live_update
                                push_live_update()
                                last_push_time = time.time()
                            except:
                                pass
                        time.sleep(0.1)
                    # Skip to end of cycle after EV lane green
                    self.log_statistics(self.current_counts, signal_timings, self.current_phase)
                    self.cycles_completed += 1
                    continue
                
                # Normal East/West phase
                green_time_ew = signal_timings['EastWest']
                # If EV is coming from East/West and <10s, extend green time
                if ev_check_active2 and ev_check_remaining2 <= 10 and ev_check_group2 == "EastWest":
                    green_time_ew = max(green_time_ew, int(ev_check_remaining2 + 15))  # Stay green until EV passes
                    print(f"🚑 EV CRITICAL: {ev_check_lane2} lane, {int(ev_check_remaining2)}s - Extending East/West green to {green_time_ew}s")
                
                print(f"\n🟢 Phase 4: East/West GREEN ({green_time_ew}s)")
                self.current_phase = "EastWest_Green"
                self.phase_start_time = time.time()  # Reset phase start time
                self.phase_remaining_time = green_time_ew  # Set initial remaining time
                self.phase_remaining_times = {"NorthSouth": 0, "EastWest": green_time_ew}
                self.send_signal_to_arduino("L1", "R")  # North/South red
                time.sleep(0.1)
                self.send_signal_to_arduino("L2", "G")  # East/West green
                start_time = time.time()
                last_push_time = time.time()
                ev_keep_green_ew = False
                while time.time() - start_time < green_time_ew or ev_keep_green_ew:
                    # Check EV state DURING phase
                    evp_state_during_ew = self._load_evp_state()
                    if evp_state_during_ew.get("active") and evp_state_during_ew.get("lane"):
                        ev_during_lane_ew = evp_state_during_ew["lane"]
                        ev_during_arrival_ew = evp_state_during_ew.get("expected_arrival_ts", 0)
                        ev_during_remaining_ew = max(0, ev_during_arrival_ew - time.time())
                        ev_during_group_ew = None
                        if ev_during_lane_ew in self.lane_groups.get("NorthSouth", []):
                            ev_during_group_ew = "NorthSouth"
                        elif ev_during_lane_ew in self.lane_groups.get("EastWest", []):
                            ev_during_group_ew = "EastWest"
                        
                        # CRITICAL: If EV is <10s and we're in EV lane, keep it green indefinitely
                        if ev_during_remaining_ew <= 10 and ev_during_group_ew == "EastWest":
                            # EV from East/West and we're in East/West - keep green!
                            if not ev_keep_green_ew:
                                print(f"🚑 EV CRITICAL: {ev_during_lane_ew} lane, {int(ev_during_remaining_ew)}s - Keeping East/West green until EV clears")
                            ev_keep_green_ew = True
                            # Set special value for "--" display
                            self.phase_remaining_time = -1
                            self.phase_remaining_times["EastWest"] = -1
                        # CRITICAL: If EV is <10s and we're in wrong phase, transition NOW
                        elif ev_during_remaining_ew <= 10 and ev_during_group_ew == "NorthSouth":
                            # EV from North/South but we're in East/West - transition immediately
                            print(f"🚑 EV CRITICAL DURING PHASE: {ev_during_lane_ew} lane, {int(ev_during_remaining_ew)}s - Transitioning to North/South NOW")
                            ev_keep_green_ew = False
                            break  # Exit current phase loop
                        else:
                            # EV not critical or cleared
                            if ev_keep_green_ew:
                                print(f"✅ EV cleared or passed - resuming normal cycle")
                                ev_keep_green_ew = False
                                break
                    else:
                        # EV cleared
                        if ev_keep_green_ew:
                            print(f"✅ EV cleared - resuming normal cycle")
                            ev_keep_green_ew = False
                            break
                    
                    # Update remaining time continuously (only if not in EV keep-green mode)
                    if not ev_keep_green_ew:
                        elapsed = time.time() - self.phase_start_time
                        remaining = max(0, green_time_ew - elapsed)
                        self.phase_remaining_time = remaining
                        self.phase_remaining_times["EastWest"] = remaining
                    # Push updates to web dashboard every 0.5 seconds
                    if time.time() - last_push_time >= 0.5:
                        try:
                            from dashboard import push_live_update
                            push_live_update()
                            last_push_time = time.time()
                        except:
                            pass
                    time.sleep(0.1)
                
                # After East/West green, check if we need to skip to EV lane (North/South)
                evp_state_after_ew = self._load_evp_state()
                if evp_state_after_ew.get("active") and evp_state_after_ew.get("lane"):
                    ev_after_lane_ew = evp_state_after_ew["lane"]
                    ev_after_arrival_ew = evp_state_after_ew.get("expected_arrival_ts", 0)
                    ev_after_remaining_ew = max(0, ev_after_arrival_ew - time.time())
                    ev_after_group_ew = None
                    if ev_after_lane_ew in self.lane_groups.get("NorthSouth", []):
                        ev_after_group_ew = "NorthSouth"
                    elif ev_after_lane_ew in self.lane_groups.get("EastWest", []):
                        ev_after_group_ew = "EastWest"
                    
                    if ev_after_remaining_ew <= 10 and ev_after_group_ew == "NorthSouth":
                        # Skip yellow and all-red, go directly to North/South green
                        print(f"🚑 EV CRITICAL: Skipping yellow/all-red, going to North/South green")
                        green_time_ns_emergency = signal_timings['NorthSouth']
                        if ev_after_remaining_ew > 0:
                            green_time_ns_emergency = max(green_time_ns_emergency, int(ev_after_remaining_ew + 15))
                        print(f"\n🟢 Phase 1 (EV PRIORITY): North/South GREEN ({green_time_ns_emergency}s)")
                        self.current_phase = "NorthSouth_Green"
                        self.phase_start_time = time.time()
                        self.phase_remaining_time = green_time_ns_emergency
                        self.phase_remaining_times = {"NorthSouth": green_time_ns_emergency, "EastWest": 0}
                        self.send_signal_to_arduino("L1", "G")
                        time.sleep(0.1)
                        self.send_signal_to_arduino("L2", "R")
                        start_time = time.time()
                        last_push_time = time.time()
                        ev_keep_green_emergency_ns = False
                        while time.time() - start_time < green_time_ns_emergency or ev_keep_green_emergency_ns:
                            # Check EV state - keep green if <10s
                            evp_state_emergency_ns = self._load_evp_state()
                            if evp_state_emergency_ns.get("active") and evp_state_emergency_ns.get("lane"):
                                ev_emergency_lane_ns = evp_state_emergency_ns["lane"]
                                ev_emergency_arrival_ns = evp_state_emergency_ns.get("expected_arrival_ts", 0)
                                ev_emergency_remaining_ns = max(0, ev_emergency_arrival_ns - time.time())
                                if ev_emergency_lane_ns in self.lane_groups.get("NorthSouth", []):
                                    if ev_emergency_remaining_ns <= 10:
                                        if not ev_keep_green_emergency_ns:
                                            print(f"🚑 EV CRITICAL: Keeping North/South green until EV clears")
                                        ev_keep_green_emergency_ns = True
                                        self.phase_remaining_time = -1
                                        self.phase_remaining_times["NorthSouth"] = -1
                                    else:
                                        if ev_keep_green_emergency_ns:
                                            ev_keep_green_emergency_ns = False
                                            break
                                else:
                                    if ev_keep_green_emergency_ns:
                                        ev_keep_green_emergency_ns = False
                                        break
                            else:
                                if ev_keep_green_emergency_ns:
                                    print(f"✅ EV cleared - resuming normal cycle")
                                    ev_keep_green_emergency_ns = False
                                    break
                            
                            if not ev_keep_green_emergency_ns:
                                elapsed = time.time() - self.phase_start_time
                                remaining = max(0, green_time_ns_emergency - elapsed)
                                self.phase_remaining_time = remaining
                                self.phase_remaining_times["NorthSouth"] = remaining
                            if time.time() - last_push_time >= 0.5:
                                try:
                                    from dashboard import push_live_update
                                    push_live_update()
                                    last_push_time = time.time()
                                except:
                                    pass
                            time.sleep(0.1)
                        self.log_statistics(self.current_counts, signal_timings, self.current_phase)
                        self.cycles_completed += 1
                        continue
                
                # Phase 5: East/West YELLOW, North/South RED
                # GOLDEN RULE: Always complete the full countdown
                print(f"🟡 Phase 5: East/West YELLOW ({self.YELLOW_TIME}s)")
                self.current_phase = "EastWest_Yellow"
                self.phase_start_time = time.time()  # Reset phase start time
                self.phase_remaining_time = self.YELLOW_TIME  # Set initial remaining time
                self.phase_remaining_times = {"NorthSouth": 0, "EastWest": self.YELLOW_TIME}
                self.send_signal_to_arduino("L2", "Y")
                time.sleep(0.1)
                self.send_signal_to_arduino("L1", "R")
                start_time = time.time()
                last_push_time = time.time()
                while time.time() - start_time < self.YELLOW_TIME:
                    # Update remaining time continuously
                    elapsed = time.time() - self.phase_start_time
                    remaining = max(0, self.YELLOW_TIME - elapsed)
                    self.phase_remaining_time = remaining
                    self.phase_remaining_times["EastWest"] = remaining
                    self.phase_remaining_times["NorthSouth"] = 0
                    # Push updates to web dashboard every 0.5 seconds
                    if time.time() - last_push_time >= 0.5:
                        try:
                            from dashboard import push_live_update
                            push_live_update()
                            last_push_time = time.time()
                        except:
                            pass
                    time.sleep(0.1)
                
                # Phase 6: ALL RED (safety buffer)
                # GOLDEN RULE: Always complete the full countdown
                print(f"🔴 Phase 6: ALL RED ({self.ALL_RED_TIME}s)")
                self.current_phase = "All_Red"
                self.phase_start_time = time.time()  # Reset phase start time
                self.phase_remaining_time = self.ALL_RED_TIME  # Set initial remaining time
                self.phase_remaining_times = {"NorthSouth": self.ALL_RED_TIME, "EastWest": self.ALL_RED_TIME}
                self.send_signal_to_arduino("L1", "R")
                time.sleep(0.1)
                self.send_signal_to_arduino("L2", "R")
                start_time = time.time()
                last_push_time = time.time()
                while time.time() - start_time < self.ALL_RED_TIME:
                    # Update remaining time continuously
                    elapsed = time.time() - self.phase_start_time
                    remaining = max(0, self.ALL_RED_TIME - elapsed)
                    self.phase_remaining_time = remaining
                    self.phase_remaining_times["NorthSouth"] = remaining
                    self.phase_remaining_times["EastWest"] = remaining
                    # Push updates to web dashboard every 0.5 seconds
                    if time.time() - last_push_time >= 0.5:
                        try:
                            from dashboard import push_live_update
                            push_live_update()
                            last_push_time = time.time()
                        except:
                            pass
                    time.sleep(0.1)
                
                # Log statistics
                self.log_statistics(self.current_counts, signal_timings, self.current_phase)
                self.cycles_completed += 1
                
                # Push live update to web dashboard via WebSocket
                try:
                    from dashboard import push_live_update
                    push_live_update()
                except Exception as e:
                    pass  # Silently fail if dashboard not available
                
                print(f"\n{'=' * 60}\n")
                
        except KeyboardInterrupt:
            self.running = False
    
    def run(self, register_with_dashboard=True, start_flask_server=True):
        """Main execution loop - starts video processing and traffic control"""
        self.connect_cameras()
        
        # Register with Flask dashboard for video streaming
        if register_with_dashboard:
            try:
                from dashboard import set_traffic_controller, app, socketio
                set_traffic_controller(self)
                print("✅ Registered with web dashboard for video streaming")
                
                # Start Flask server in a separate thread (if requested)
                if start_flask_server:
                    def run_flask():
                        print("\n" + "=" * 60)
                        print("🚀 Starting IntelliFlow Flask Server...")
                        print("📡 WebSocket enabled for real-time updates")
                        print("🔗 React frontend should connect to: http://127.0.0.1:5000")
                        print("=" * 60 + "\n")
                        socketio.run(app, host="0.0.0.0", port=5000, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)
                    
                    flask_thread = threading.Thread(target=run_flask, daemon=True)
                    flask_thread.start()
                    print("✅ Flask server started in background thread")
                    # Give Flask a moment to start
                    time.sleep(2)
            except Exception as e:
                print(f"⚠️ Could not register with dashboard: {e}")
                print("⚠️ Web dashboard will not be available")
        
        # Start video processing in a separate thread
        video_thread = threading.Thread(target=self.process_video_feeds, daemon=True)
        video_thread.start()
        
        # Run traffic control in main thread
        try:
            self.run_traffic_control()
        finally:
            self.running = False
            for cap in self.captures.values():
                try:
                    cap.release()
                except Exception:
                    pass
            cv2.destroyAllWindows()
            
            if self.arduino:
                # Set both lanes to red on shutdown
                self.send_signal_to_arduino("L1", "R")
                self.send_signal_to_arduino("L2", "R")
                self.arduino.close()
            
            print("\n" + "=" * 60)
            print("✅ IntelliFlow System Stopped")
            print("=" * 60)
            print(f"\n📊 Final Statistics:")
            print(f"   Total Vehicles Detected: {self.total_vehicles_detected}")
            print(f"   Cycles Completed: {self.cycles_completed}")
            print(f"   Log Entries: {len(self.log_data)}")
            print(f"   Data saved to: traffic_log.json")
            print("\n" + "=" * 60 + "\n")


# =============================================================
# Run IntelliFlow
# =============================================================
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("     IntelliFlow - Smart Traffic Management System")
    print("        Dual Video Input System (North & East)")
    print("              InnoTech 2025 Project")
    print("=" * 60 + "\n")

    # Initialize with TWO video inputs
    # Video 1 (north_camera_url): All vehicles are in NORTH lane
    # Video 2 (east_camera_url): All vehicles are in EAST lane
    # Initialize controller
    # Configuration is loaded from config.py if it exists
    # Otherwise, you can specify video sources here:
    controller = TrafficSignalController(
        model_path="yolov8n.pt",
        # north_camera_url and east_camera_url will be loaded from config.py
        # Or specify here: north_camera_url="video1.mp4", east_camera_url="video2.mp4"
    )

    controller.run()
