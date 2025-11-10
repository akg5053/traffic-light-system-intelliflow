"""
Helper tool to find lane coordinates
Click on your camera feed to get coordinates
"""
import cv2

clicks = []

def click_event(event, x, y, flags, params):
    if event == cv2.EVENT_LBUTTONDOWN:
        print(f"✅ Clicked at: ({x}, {y})")
        clicks.append((x, y))
        
        # Draw point
        cv2.circle(frame_copy, (x, y), 5, (0, 0, 255), -1)
        cv2.putText(frame_copy, f"({x},{y})", (x+10, y-10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        cv2.imshow('Click to get coordinates', frame_copy)
        
        if len(clicks) % 2 == 0:
            idx = len(clicks) // 2
            print(f"📍 Lane {idx}: ({clicks[-2][0]}, {clicks[-2][1]}, {clicks[-1][0]}, {clicks[-1][1]})")

print("🎯 Coordinate Finder Tool")
print("Instructions:")
print("1. Click TOP-LEFT corner of Lane 1")
print("2. Click BOTTOM-RIGHT corner of Lane 1")
print("3. Repeat for all 4 lanes")
print("4. Press 'q' when done\n")

cap = cv2.VideoCapture(0)  # Change to your camera
ret, frame = cap.read()

if not ret:
    print("❌ Cannot open camera")
    exit()

frame_copy = frame.copy()
cv2.imshow('Click to get coordinates', frame)
cv2.setMouseCallback('Click to get coordinates', click_event)

print("👆 Click on the image window (not here!)\n")

cv2.waitKey(0)
cap.release()
cv2.destroyAllWindows()

print("\n✅ Done! Copy these coordinates to intelliflow_ml.py")


## ✅ **Step 5: Your Folder Should Look Like This**
