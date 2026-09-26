import cv2

# Try index 0, 1, or 2
cap = cv2.VideoCapture(0)

# Force the MJPG format to fix green screen decoding issues
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

print("Attempting to connect to camera...")

if not cap.isOpened():
    print("Error: Could not open camera.")

while True:
    ret, frame = cap.read()
    
    if not ret:
        break

    cv2.imshow("Camera Test", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()