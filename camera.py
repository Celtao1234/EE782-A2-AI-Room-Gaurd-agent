import cv2

def open_camera():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("❌ Cannot open webcam")
    return cap

def main():
    cap = open_camera()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        cv2.imshow("Camera Feed", frame)

        # Press 'q' to quit
        if cv2.waitKey(10) & 0xFF == ord('q'):
            print("Quitting...")
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
