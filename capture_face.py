import cv2                    # for accessing webcam and frames
import face_recognition        # for detecting faces and extracting embeddings
import numpy as np             # for handling numerical data
import os  

camera = cv2.VideoCapture(0)
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

if not camera.isOpened():
    raise Exception("Error: Could not open webcam")


# --- Capture frame and detect face ---
print("Press 's' to capture your face for registration, or 'q' to quit.")

while True:
    ret, frame = camera.read()
    if not ret:
        print("Failed to grab frame")
        break

    # Convert from BGR (OpenCV format) to RGB (face_recognition format)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Detect face locations
    face_locations = face_recognition.face_locations(rgb_frame, model="hog")


    # Draw rectangles for user feedback
    for (top, right, bottom, left) in face_locations:
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

    cv2.imshow("Register Face", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('s'):
        print("Saving snapshot...")
        break
    elif key == ord('q'):
        print("Quitting...")
        camera.release()
        cv2.destroyAllWindows()
        exit()

# --- Block 4: Extract embeddings and save ---
if face_locations:
    # Encode (generate embeddings)
    encodings = face_recognition.face_encodings(rgb_frame, face_locations, num_jitters=3)

    # Take first face (assuming single person registering)
    embedding = encodings[0]

    # Ask for name
    name = input("Enter your name for registration: ")

    # Make sure folder exists
    os.makedirs("trusted_faces", exist_ok=True)

    # Save the embedding
    np.save(f"trusted_faces/{name}_embedding.npy", embedding)

    # Save the snapshot of the cropped version
    top, right, bottom, left = face_locations[0]
    face_crop = frame[top:bottom, left:right]
    cv2.imwrite(f"trusted_faces/{name}_face.jpg", face_crop)

    print(f"[✅] Face data for '{name}' saved successfully.")
else:
    print("[⚠️] No face detected — try again.")


camera.release()
cv2.destroyAllWindows()