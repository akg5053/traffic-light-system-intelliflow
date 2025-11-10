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


class TrafficSignalController:
    def __init__(self, model_path="yolov8n.pt", north_camera_url=None, east_camera_url=None):
        """Initialize the traffic signal controller with TWO video inputs"""
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
        
        # TWO Camera setup - North and East lanes
        # Priority: config.py > function parameters > defaults
        if self.config:
            # Check for mixed sources (IP Webcam + ESP32-CAM)
            if hasattr(self.config, 'USE_MIXED') and self.config.USE_MIXED:
                # North: IP Webcam, East: ESP32-CAM
                self.north_camera_url = getattr(self.config, 'NORTH_IP_WEBCAM_URL', None)
                east_esp32_ip = getattr(self.config, 'EAST_ESP32_IP', None)
                east_stream_url = getattr(self.config, 'EAST_ESP32_STREAM_URL', '/stream')
                self.east_camera_url = f"http://{east_esp32_ip}{east_stream_url}" if east_esp32_ip else None
                print(f"📹 Mixed sources: North=IP Webcam ({self.north_camera_url}), East=ESP32-CAM ({self.east_camera_url})")
            # Check for webcam option
            elif hasattr(self.config, 'USE_WEBCAM') and self.config.USE_WEBCAM:
                self.north_camera_url = getattr(self.config, 'NORTH_WEBCAM_INDEX', 0)
                self.east_camera_url = getattr(self.config, 'EAST_WEBCAM_INDEX', 1)
                print(f"📹 Using laptop webcams: North=Index {self.north_camera_url}, East=Index {self.east_camera_url}")
            # Check for video files
            elif hasattr(self.config, 'USE_VIDEO_FILES') and self.config.USE_VIDEO_FILES:
                self.north_camera_url = getattr(self.config, 'NORTH_VIDEO_FILE', None)
                self.east_camera_url = getattr(self.config, 'EAST_VIDEO_FILE', None)
                print(f"📹 Using video files: {self.north_camera_url}, {self.east_camera_url}")
            # Check for ESP32-CAM (both)
            elif hasattr(self.config, 'NORTH_ESP32_IP'):
                self.north_camera_url = f"http://{self.config.NORTH_ESP32_IP}{getattr(self.config, 'ESP32_STREAM_URL', '/stream')}"
                self.east_camera_url = f"http://{self.config.EAST_ESP32_IP}{getattr(self.config, 'ESP32_STREAM_URL', '/stream')}"
                print(f"📹 Using ESP32-CAM: {self.north_camera_url}, {self.east_camera_url}")
            # Check for IP Webcam (both)
            elif hasattr(self.config, 'NORTH_IP_WEBCAM_URL'):
                self.north_camera_url = getattr(self.config, 'NORTH_IP_WEBCAM_URL', None)
                self.east_camera_url = getattr(self.config, 'EAST_IP_WEBCAM_URL', None)
                print(f"📹 Using IP Webcam: {self.north_camera_url}, {self.east_camera_url}")
            # Check for webcams (fallback)
            elif hasattr(self.config, 'NORTH_WEBCAM_INDEX'):
                self.north_camera_url = self.config.NORTH_WEBCAM_INDEX
                self.east_camera_url = self.config.EAST_WEBCAM_INDEX
                print(f"📹 Using webcams: Index {self.north_camera_url}, {self.east_camera_url}")
            else:
                # Default to function parameters
                self.north_camera_url = north_camera_url if north_camera_url is not None else 0
                self.east_camera_url = east_camera_url if east_camera_url is not None else 1
        else:
            # Use function parameters or defaults
            self.north_camera_url = north_camera_url if north_camera_url is not None else 0
            self.east_camera_url = east_camera_url if east_camera_url is not None else 1
        
        self.north_cap = None
        self.east_cap = None

        # Lane definitions - now using two separate videos
        # Video 1 (North) -> L1 (North/South group)
        # Video 2 (East) -> L2 (East/West group)
        self.lanes = {
            "North": "L1",  # North/South lanes (from video 1)
            "East": "L2"    # East/West lanes (from video 2)
        }

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

        # Vehicle counting - separate for North and East
        self.vehicle_history = {
            "North": deque(maxlen=10),
            "East": deque(maxlen=10)
        }
        self.current_counts = {"North": 0, "East": 0}

        # Traffic light state
        self.current_phase = "NorthSouth_Green"  # or "EastWest_Green"
        self.phase_start_time = time.time()
        self.current_green_time = self.MIN_GREEN
        self.phase_remaining_time = 0  # Remaining time for current phase

        # Emergency detection
        self.emergency_detected = False
        self.emergency_lane = None

        # Statistics
        self.total_vehicles_detected = 0
        self.cycles_completed = 0
        self.log_data = []

        # Threading for dual video processing
        self.running = False
        self.north_frame = None
        self.east_frame = None
        self.north_frame_encoded = None
        self.east_frame_encoded = None
        self.frame_lock = threading.Lock()
        
        # Video loop support (restart videos when they end)
        self.north_video_finished = False
        self.east_video_finished = False

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
        print(f"   North Camera: {self.north_camera_url}")
        print(f"   East Camera: {self.east_camera_url}")

    # =============================================================
    # Helper Functions
    # =============================================================
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
        """Connect to both cameras (North and East)"""
        print(f"\n📷 Connecting to cameras...")
        print(f"   North Camera (Video 1): {self.north_camera_url}")
        print(f"   East Camera (Video 2): {self.east_camera_url}")
        
        # Connect to North camera (Video 1)
        self.north_cap = cv2.VideoCapture(self.north_camera_url)
        if not self.north_cap.isOpened():
            raise Exception(f"❌ Failed to connect to North camera: {self.north_camera_url}")
        self.north_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.north_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        print("✅ North camera connected!")
        
        # Connect to East camera (Video 2)
        self.east_cap = cv2.VideoCapture(self.east_camera_url)
        if not self.east_cap.isOpened():
            raise Exception(f"❌ Failed to connect to East camera: {self.east_camera_url}")
        self.east_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.east_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        print("✅ East camera connected!")
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

    def smooth_vehicle_counts(self, north_count, east_count):
        """Apply temporal smoothing to vehicle counts"""
        self.vehicle_history["North"].append(north_count)
        self.vehicle_history["East"].append(east_count)
        
        smooth_north = int(np.mean(self.vehicle_history["North"])) if self.vehicle_history["North"] else 0
        smooth_east = int(np.mean(self.vehicle_history["East"])) if self.vehicle_history["East"] else 0
        
        return {"North": smooth_north, "East": smooth_east}

    def calculate_green_time(self, vehicle_counts):
        """
        Calculate dynamic green time based on vehicle counts
        More vehicles = more green time, less vehicles = less time
        """
        north_count = vehicle_counts.get("North", 0)
        east_count = vehicle_counts.get("East", 0)
        total_vehicles = north_count + east_count
        
        if total_vehicles == 0:
            # No vehicles detected - use minimum time
            return {"NorthSouth": self.MIN_GREEN, "EastWest": self.MIN_GREEN}
        
        # Calculate proportional green time based on vehicle density
        # More vehicles need more green time
        if north_count > east_count:
            # North has more vehicles
            north_green = min(self.MAX_GREEN, max(self.MIN_GREEN, north_count * 2))
            east_green = min(self.MAX_GREEN, max(self.MIN_GREEN, east_count * 2))
        elif east_count > north_count:
            # East has more vehicles
            east_green = min(self.MAX_GREEN, max(self.MIN_GREEN, east_count * 2))
            north_green = min(self.MAX_GREEN, max(self.MIN_GREEN, north_count * 2))
        else:
            # Equal vehicles - equal time
            green_time = min(self.MAX_GREEN, max(self.MIN_GREEN, (north_count + east_count)))
            north_green = green_time
            east_green = green_time
        
        return {"NorthSouth": int(north_green), "EastWest": int(east_green)}

    def handle_emergency_vehicle(self, emergency_lane):
        """Handle emergency vehicle"""
        self.emergency_detected = True
        self.emergency_lane = emergency_lane
        print(f"\n🚨 EMERGENCY VEHICLE DETECTED IN {emergency_lane}")
        # Emergency: give 30s green to emergency lane, 5s to other
        if emergency_lane == "North":
            return {"NorthSouth": 30, "EastWest": 5}
        else:
            return {"NorthSouth": 5, "EastWest": 30}

    def log_statistics(self, vehicle_counts, signal_timings, current_phase):
        """Log data + notify dashboard"""
        avg_wait_traditional = 90
        avg_wait_intelliflow = (signal_timings["NorthSouth"] + signal_timings["EastWest"]) / 2

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "vehicle_counts": {
                "North": vehicle_counts.get("North", 0),
                "East": vehicle_counts.get("East", 0)
            },
            "signal_timings": signal_timings,
            "current_phase": current_phase,
            "total_vehicles": vehicle_counts.get("North", 0) + vehicle_counts.get("East", 0),
            "emergency": self.emergency_detected,
            "avg_wait_time_traditional": avg_wait_traditional,
            "avg_wait_time_intelliflow": avg_wait_intelliflow,
            "time_saved": avg_wait_traditional - avg_wait_intelliflow,
            "efficiency_improvement": round(((avg_wait_traditional - avg_wait_intelliflow)
                                             / avg_wait_traditional) * 100, 2)
        }

        self.log_data.append(log_entry)

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
        """Process both video feeds - detect vehicles in entire frame and stream to web"""
        self.running = True
        frame_count = 0
        
        while self.running:
            # Read frames from both videos
            ret_north, frame_north = self.north_cap.read()
            ret_east, frame_east = self.east_cap.read()
            
            # Handle video end - restart from beginning
            if not ret_north:
                if not self.north_video_finished:
                    print("🔄 North video ended, restarting...")
                    self.north_video_finished = True
                self.north_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret_north, frame_north = self.north_cap.read()
                if ret_north:
                    self.north_video_finished = False
            
            if not ret_east:
                if not self.east_video_finished:
                    print("🔄 East video ended, restarting...")
                    self.east_video_finished = True
                self.east_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret_east, frame_east = self.east_cap.read()
                if ret_east:
                    self.east_video_finished = False
            
            if not ret_north or not ret_east:
                time.sleep(0.1)
                continue
            
            # Detect vehicles in North video (detect ALL vehicles in entire frame)
            boxes_north = self.detect_vehicles(frame_north)
            north_count = self.count_vehicles_in_frame(boxes_north, frame_north, "North")
            
            # Detect vehicles in East video (detect ALL vehicles in entire frame)
            boxes_east = self.detect_vehicles(frame_east)
            east_count = self.count_vehicles_in_frame(boxes_east, frame_east, "East")
            
            # Smooth the counts
            self.current_counts = self.smooth_vehicle_counts(north_count, east_count)
            
            # Update phase_remaining_time based on current phase (for real-time updates)
            # This runs in video loop, so we need to calculate from phase_start_time
            if hasattr(self, 'phase_start_time') and hasattr(self, 'current_phase') and hasattr(self, 'phase_start_time'):
                try:
                    elapsed = time.time() - self.phase_start_time
                    if "Green" in self.current_phase:
                        # Calculate current signal timings based on current vehicle counts
                        signal_timings = self.calculate_green_time(self.current_counts)
                        if "NorthSouth" in self.current_phase:
                            total_time = signal_timings.get("NorthSouth", self.MIN_GREEN)
                            self.phase_remaining_time = max(0, total_time - elapsed)
                        elif "EastWest" in self.current_phase:
                            total_time = signal_timings.get("EastWest", self.MIN_GREEN)
                            self.phase_remaining_time = max(0, total_time - elapsed)
                        else:
                            self.phase_remaining_time = 0
                    elif "Yellow" in self.current_phase:
                        self.phase_remaining_time = max(0, self.YELLOW_TIME - elapsed)
                    elif "All_Red" in self.current_phase:
                        self.phase_remaining_time = max(0, self.ALL_RED_TIME - elapsed)
                    else:
                        self.phase_remaining_time = 0
                except Exception as e:
                    # If calculation fails, set to 0
                    self.phase_remaining_time = 0
            
            # Draw info on frames
            phase_info = f"Phase: {self.current_phase}"
            frame_north = self.draw_info_panel(frame_north, "NORTH", self.current_counts["North"], phase_info)
            frame_east = self.draw_info_panel(frame_east, "EAST", self.current_counts["East"], phase_info)
            
            # Add title and vehicle count overlay
            cv2.putText(frame_north, f"North Lane - Vehicles: {self.current_counts['North']}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            cv2.putText(frame_east, f"East Lane - Vehicles: {self.current_counts['East']}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            
            # Store frames for web streaming (with lock for thread safety)
            with self.frame_lock:
                self.north_frame = frame_north.copy()
                self.east_frame = frame_east.copy()
                # Encode frames as JPEG for web streaming
                _, buffer_north = cv2.imencode('.jpg', frame_north, [cv2.IMWRITE_JPEG_QUALITY, 85])
                _, buffer_east = cv2.imencode('.jpg', frame_east, [cv2.IMWRITE_JPEG_QUALITY, 85])
                self.north_frame_encoded = buffer_north.tobytes()
                self.east_frame_encoded = buffer_east.tobytes()
            
            # Display frames locally (optional - can be disabled for headless server)
            try:
                combined_frame = np.hstack((frame_north, frame_east))
                cv2.imshow('IntelliFlow - Dual Video System', combined_frame)
                
                # Check for user input
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
                
                print(f"\n{'=' * 60}")
                print(f"⏱️  Cycle #{self.cycles_completed + 1}")
                print(f"{'=' * 60}")
                print(f"\n📊 Vehicle Counts:")
                print(f"   North Lane: {self.current_counts['North']} vehicles")
                print(f"   East Lane: {self.current_counts['East']} vehicles")
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
                self.send_signal_to_arduino("L1", "G")  # North/South green
                time.sleep(0.1)  # Delay between commands
                self.send_signal_to_arduino("L2", "R")  # East/West red
                start_time = time.time()
                last_push_time = time.time()
                while time.time() - start_time < green_time_ns:
                    # Update remaining time continuously
                    elapsed = time.time() - self.phase_start_time
                    self.phase_remaining_time = max(0, green_time_ns - elapsed)
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
                self.send_signal_to_arduino("L1", "Y")
                time.sleep(0.1)
                self.send_signal_to_arduino("L2", "R")
                start_time = time.time()
                last_push_time = time.time()
                while time.time() - start_time < self.YELLOW_TIME:
                    # Update remaining time continuously
                    elapsed = time.time() - self.phase_start_time
                    self.phase_remaining_time = max(0, self.YELLOW_TIME - elapsed)
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
                self.send_signal_to_arduino("L1", "R")
                time.sleep(0.1)
                self.send_signal_to_arduino("L2", "R")
                start_time = time.time()
                last_push_time = time.time()
                while time.time() - start_time < self.ALL_RED_TIME:
                    # Update remaining time continuously
                    elapsed = time.time() - self.phase_start_time
                    self.phase_remaining_time = max(0, self.ALL_RED_TIME - elapsed)
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
                self.send_signal_to_arduino("L1", "R")  # North/South red
                time.sleep(0.1)
                self.send_signal_to_arduino("L2", "G")  # East/West green
                start_time = time.time()
                last_push_time = time.time()
                while time.time() - start_time < green_time_ew:
                    # Update remaining time continuously
                    elapsed = time.time() - self.phase_start_time
                    self.phase_remaining_time = max(0, green_time_ew - elapsed)
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
                self.send_signal_to_arduino("L2", "Y")
                time.sleep(0.1)
                self.send_signal_to_arduino("L1", "R")
                start_time = time.time()
                last_push_time = time.time()
                while time.time() - start_time < self.YELLOW_TIME:
                    # Update remaining time continuously
                    elapsed = time.time() - self.phase_start_time
                    self.phase_remaining_time = max(0, self.YELLOW_TIME - elapsed)
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
                self.send_signal_to_arduino("L1", "R")
                time.sleep(0.1)
                self.send_signal_to_arduino("L2", "R")
                start_time = time.time()
                last_push_time = time.time()
                while time.time() - start_time < self.ALL_RED_TIME:
                    # Update remaining time continuously
                    elapsed = time.time() - self.phase_start_time
                    self.phase_remaining_time = max(0, self.ALL_RED_TIME - elapsed)
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
            if self.north_cap:
                self.north_cap.release()
            if self.east_cap:
                self.east_cap.release()
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
