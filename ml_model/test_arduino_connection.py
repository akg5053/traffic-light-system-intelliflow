import serial
import time

# Change this to your actual port from Arduino IDE (e.g. 'COM3')
arduino = serial.Serial('COM5', 9600, timeout=1)

time.sleep(5)
print("✅ Connected to Arduino!")

# Test sequence for 2-lane signal
commands = ["L1_G", "L1_Y", "L1_R", "L2_G", "L2_Y", "L2_R"]

for cmd in commands:
    arduino.write(f"{cmd}\n".encode())
    print(f"➡️ Sent: {cmd}")
    time.sleep(2)  # wait 2 seconds between each LED change

print("✅ Test completed! Check LED behavior on Arduino.")
arduino.close()
