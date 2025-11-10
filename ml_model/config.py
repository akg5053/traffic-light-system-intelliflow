"""
IntelliFlow Configuration File
Edit this file to configure your system
"""

# ============================================================
# VIDEO SOURCE CONFIGURATION
# ============================================================
# Choose ONE option below by setting USE_VIDEO_FILES, USE_WEBCAM, or USE_MIXED

# ============================================================
# OPTION 1: Use Laptop Webcam (for both lanes)
# ============================================================
USE_WEBCAM = False
NORTH_WEBCAM_INDEX = 0  # Camera index for North lane (usually 0)
EAST_WEBCAM_INDEX = 1   # Camera index for East lane (usually 1, or same as 0 if only one camera)

# ============================================================
# OPTION 2: Use Video Files (for both lanes)
# ============================================================
USE_VIDEO_FILES = True
NORTH_VIDEO_FILE = "vid1.mp4"
EAST_VIDEO_FILE = "vid2.mp4"

# ============================================================
# OPTION 3: Mixed Sources (IP Webcam for North + ESP32-CAM for East)
# ============================================================
USE_MIXED = False
# North Lane: IP Webcam App (Android phone)
NORTH_IP_WEBCAM_URL = "http://192.168.1.50:8080/video"  # IP Webcam app URL
# East Lane: ESP32-CAM
EAST_ESP32_IP = "192.168.1.101"   # ESP32-CAM IP address
EAST_ESP32_STREAM_URL = "/stream"  # ESP32-CAM stream endpoint

# ============================================================
# Other Options (if needed)
# ============================================================
# Option 4: Both ESP32-CAM
# USE_VIDEO_FILES = False
# USE_WEBCAM = False
# USE_MIXED = False
# NORTH_ESP32_IP = "192.168.1.100"
# EAST_ESP32_IP = "192.168.1.101"
# ESP32_STREAM_URL = "/stream"

# Option 5: Both IP Webcam
# USE_VIDEO_FILES = False
# USE_WEBCAM = False
# USE_MIXED = False
# NORTH_IP_WEBCAM_URL = "http://192.168.1.50:8080/video"
# EAST_IP_WEBCAM_URL = "http://192.168.1.51:8080/video"

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
MAX_GREEN_TIME = 40   # Maximum green light time (seconds)
YELLOW_TIME = 4       # Yellow light time (seconds)
ALL_RED_TIME = 2      # All red safety buffer (seconds)

# ============================================================
# VEHICLE DETECTION
# ============================================================

DETECTION_CONFIDENCE = 0.4  # Lower = detect more vehicles, Higher = detect only confident ones
VEHICLE_CLASSES = [2, 3, 5, 7]  # COCO classes: 2=car, 3=motorcycle, 5=bus, 7=truck

