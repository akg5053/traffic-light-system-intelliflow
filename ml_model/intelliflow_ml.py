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
            # Close port if already open
            try:
                test_serial = serial.Serial(arduino_port, arduino_baud, timeout=1)
                test_serial.close()
                time.sleep(0.5)
            except:
                pass
            
            # Open serial connection
            self.arduino = serial.Serial(arduino_port, arduino_baud, timeout=1)
            time.sleep(2)  # Wait for Arduino to reset
            
            # Flush any existing data
            self.arduino.reset_input_buffer()
            self.arduino.reset_output_buffer()
            
            # Test connection by sending a command
            self.arduino.write(b"L1_R\n")
            time.sleep(0.1)
            self.arduino.write(b"L2_R\n")
            time.sleep(0.1)
            
            print(f"✅ Connected to Arduino ({arduino_port})")
            print(f"✅ Arduino communication test successful")
        except serial.SerialException as e:
            print(f"⚠️ Arduino Serial Error: {e}")
            print(f"⚠️ Expected port: {arduino_port}, baud rate: {arduino_baud}")
            print("⚠️ System will run without hardware control")
            print("💡 Make sure Arduino is connected and check COM port in Device Manager")
            self.arduino = None
        except Exception as e:
            print(f"⚠️ Arduino connection failed: {e}")
            print(f"⚠️ Expected port: {arduino_port}, baud rate: {arduino_baud}")
            print("⚠️ System will run without hardware control")
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

    def send_signal_to_arduino(self, lane, color):
        """Send signal command to Arduino (e.g., L1_G, L2_R, etc.)"""
        if not self.arduino:
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
                    self.arduino = serial.Serial(arduino_port, arduino_baud, timeout=1)
                    time.sleep(1)
                    self.arduino.reset_input_buffer()
                    self.arduino.reset_output_buffer()
                    print(f"✅ Reconnected to Arduino ({arduino_port})")
                except Exception as reconnect_error:
                    print(f"⚠️ Failed to reconnect: {reconnect_error}")
                    self.arduino = None
                    return
            
            # Flush buffers before sending
            self.arduino.reset_output_buffer()
            
            # Send command
            cmd = f"{lane}_{color}\n".encode('utf-8')
            self.arduino.write(cmd)
            self.arduino.flush()  # Ensure data is sent
            
            # Small delay to ensure command is processed
            time.sleep(0.05)
            
            print(f"➡️ Sent to Arduino: {cmd.decode('utf-8').strip()}")
        except serial.SerialException as e:
            print(f"⚠️ Serial error sending to Arduino: {e}")
            self.arduino = None
        except Exception as e:
            print(f"⚠️ Failed to send to Arduino: {e}")

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

    def calculate_green_time(self, vehicle_counts):
        """
        Calculate dynamic green time based on vehicle counts
        More vehicles = more green time, less vehicles = less time
        """
        north_group = sum(vehicle_counts.get(lane, 0) for lane in self.lane_groups.get("NorthSouth", []))
        east_group = sum(vehicle_counts.get(lane, 0) for lane in self.lane_groups.get("EastWest", []))
        total_vehicles = north_group + east_group
        
        if total_vehicles == 0:
            # No vehicles detected - use minimum time
            return {"NorthSouth": self.MIN_GREEN, "EastWest": self.MIN_GREEN}
        
        # Calculate proportional green time based on vehicle density
        # More vehicles need more green time
        if north_group > east_group:
            north_green = min(self.MAX_GREEN, max(self.MIN_GREEN, north_group * 2))
            east_green = min(self.MAX_GREEN, max(self.MIN_GREEN, east_group * 2))
        elif east_group > north_group:
            east_green = min(self.MAX_GREEN, max(self.MIN_GREEN, east_group * 2))
            north_green = min(self.MAX_GREEN, max(self.MIN_GREEN, north_group * 2))
        else:
            # Equal vehicles - equal time
            green_time = min(self.MAX_GREEN, max(self.MIN_GREEN, total_vehicles))
            north_green = green_time
            east_green = green_time
        
        return {"NorthSouth": int(north_green), "EastWest": int(east_green)}

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
                # Calculate green times based on current vehicle counts
                if self.emergency_detected:
                    signal_timings = self.handle_emergency_vehicle(self.emergency_lane)
                    self.emergency_detected = False
                else:
                    signal_timings = self.calculate_green_time(self.current_counts)
                self._update_group_counts()
                
                print(f"\n{'=' * 60}")
                print(f"⏱️  Cycle #{self.cycles_completed + 1}")
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
                green_time_ns = signal_timings['NorthSouth']
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
                while time.time() - start_time < green_time_ns:
                    # Update remaining time continuously
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
                
                # Phase 2: North/South YELLOW, East/West RED
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
                green_time_ew = signal_timings['EastWest']
                print(f"🟢 Phase 4: East/West GREEN ({green_time_ew}s)")
                self.current_phase = "EastWest_Green"
                self.phase_start_time = time.time()  # Reset phase start time
                self.phase_remaining_time = green_time_ew  # Set initial remaining time
                self.phase_remaining_times = {"NorthSouth": 0, "EastWest": green_time_ew}
                self.send_signal_to_arduino("L1", "R")  # North/South red
                time.sleep(0.1)
                self.send_signal_to_arduino("L2", "G")  # East/West green
                start_time = time.time()
                last_push_time = time.time()
                while time.time() - start_time < green_time_ew:
                    # Update remaining time continuously
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
                
                # Phase 5: East/West YELLOW, North/South RED
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
