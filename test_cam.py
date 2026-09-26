import cv2

print("Scanning for cameras...")
for i in range(5):
    # Try default backend first
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        print(f"✅ Camera found at index {i} (Default backend)")
        cap.release()
    else:
        print(f"❌ No camera at index {i} (Default)")
        
    # Try DirectShow explicitly
    cap_ds = cv2.VideoCapture(i, cv2.CAP_DSHOW)
    if cap_ds.isOpened():
        print(f"✅ Camera found at index {i} (DirectShow)")
        cap_ds.release()
    else:
        print(f"❌ No camera at index {i} (DirectShow)")
        
print("Scan complete.")