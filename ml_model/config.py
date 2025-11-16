"""
IntelliFlow Configuration File

Edit this file to configure your video sources and hardware.
Choose a SYSTEM_MODE from the list below and update the related
source dictionaries for your environment.
"""

# ============================================================
# CORE MODE SELECTION
# ============================================================
# Available options:
#   "FOUR_VIDEO"  -> Four independent video files (North/South/East/West)
#   "TWO_VIDEO"   -> Original two-video setup (North + East feeds)
#   "TWO_ESP32"   -> Two ESP32-CAM devices (North + East)
#   "TWO_IP"      -> Two IP Webcam streams (North + East)
#   "TWO_MIXED"   -> Hybrid: North IP Webcam + East ESP32-CAM
#   "FOUR_HYBRID" -> Four lanes (North/South IP Webcam, East/West ESP32-CAM)
SYSTEM_MODE = "TWO_VIDEO"

# ============================================================
# SOURCE DEFINITIONS
# ============================================================

# Video files for each lane (used by TWO_VIDEO and FOUR_VIDEO)
VIDEO_FILES = {
    "North": "vid1.mp4",
    "South": "WhatsApp Video 2025-11-08 at 00.20.17_269fdc46.mp4",
    "East": "vid2.mp4",
    "West": "WhatsApp Video 2025-11-08 at 00.20.17_02904bca.mp4",
}

# ESP32-CAM definitions for each lane (IP + optional stream endpoint)
ESP32_CAMERAS = {
    "North": {"ip": "192.168.1.100", "stream": "/stream"},
    "South": {"ip": "192.168.1.101", "stream": "/stream"},
    "East": {"ip": "192.168.1.102", "stream": "/stream"},
    "West": {"ip": "192.168.1.103", "stream": "/stream"},
}

# IP Webcam URLs (Android IP Webcam app or similar)
IP_WEBCAMS = {
    "North": "http://10.142.4.81:8080/video",
    "South": "http://10.142.4.79:8080/video",
    "East": "http://10.142.4.79:8080/video",
    "West": "http://192.168.1.53:8080/video",
}

# Optional laptops webcams (leave unused unless you wire them in custom mode)
LOCAL_WEBCAMS = {
    "North": 0,
    "South": 1,
    "East": 2,
    "West": 3,
}

# ============================================================
# MODE → LANE SOURCE MAPPING
# ============================================================

LANE_SOURCES_BY_MODE = {
    "FOUR_VIDEO": {
        "North": {"type": "video", "path": VIDEO_FILES["North"]},
        "South": {"type": "video", "path": VIDEO_FILES["South"]},
        "East": {"type": "video", "path": VIDEO_FILES["East"]},
        "West": {"type": "video", "path": VIDEO_FILES["West"]},
    },
    "TWO_VIDEO": {
        "North": {"type": "video", "path": VIDEO_FILES["North"]},
        "East": {"type": "video", "path": VIDEO_FILES["East"]},
    },
    "TWO_ESP32": {
        "North": {"type": "esp32", **ESP32_CAMERAS["North"]},
        "East": {"type": "esp32", **ESP32_CAMERAS["East"]},
    },
    "TWO_IP": {
        "North": {"type": "ip", "url": IP_WEBCAMS["North"]},
        "East": {"type": "ip", "url": IP_WEBCAMS["East"]},
    },
    "TWO_MIXED": {
        "North": {"type": "ip", "url": IP_WEBCAMS["North"]},
        "East": {"type": "esp32", **ESP32_CAMERAS["East"]},
    },
    "FOUR_HYBRID": {
        "North": {"type": "ip", "url": IP_WEBCAMS["North"]},
        "South": {"type": "ip", "url": IP_WEBCAMS["South"]},
        "East": {"type": "esp32", **ESP32_CAMERAS["East"]},
        "West": {"type": "esp32", **ESP32_CAMERAS["West"]},
    },
}

# Final lane source configuration consumed by IntelliFlow.
# You can also override this dictionary manually if you ever need
# a custom combination that is not covered above.
LANE_SOURCES = LANE_SOURCES_BY_MODE.get(SYSTEM_MODE, LANE_SOURCES_BY_MODE["TWO_VIDEO"])

# Groups map keeps lane associations for North/South and East/West
LANE_GROUPS = {
    "NorthSouth": ["North", "South"],
    "EastWest": ["East", "West"],
}

# ============================================================
# ARDUINO CONFIGURATION
# ============================================================

# Arduino COM Port (Windows) or /dev/ttyUSB0 (Linux) or /dev/tty.usbserial (Mac)
ARDUINO_PORT = "COM5"  # Change this to your Arduino port
ARDUINO_BAUD_RATE = 9600

# ============================================================
# TRAFFIC LIGHT TIMING
# ============================================================

MIN_GREEN_TIME = 10    # Minimum green light time (seconds)
MAX_GREEN_TIME = 40    # Maximum green light time (seconds)
YELLOW_TIME = 4        # Yellow light time (seconds)
ALL_RED_TIME = 2       # All red safety buffer (seconds)

# ============================================================
# VEHICLE DETECTION
# ============================================================

DETECTION_CONFIDENCE = 0.4  # Lower = detect more vehicles, Higher = detect only confident ones
VEHICLE_CLASSES = [2, 3, 5, 7]  # COCO classes: 2=car, 3=motorcycle, 5=bus, 7=truck

