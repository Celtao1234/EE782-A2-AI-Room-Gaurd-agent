import cv2                    # for accessing webcam and frames
import face_recognition        # for detecting faces and extracting embeddings
import numpy as np             # for handling numerical data
import os
from state import state
# --- Load all trusted face embeddings ---
def load_trusted_faces():
    """Load all saved face embeddings from the trusted_faces directory"""
    trusted_embeddings = []
    trusted_names = []
    
    if not os.path.exists("trusted_faces"):
        print("[⚠️] No 'trusted_faces' directory found. Please run capture_face.py first.")
        return [], []
    
    # Load all .npy embedding files
    for filename in os.listdir("trusted_faces"):
        if filename.endswith("_embedding.npy"):
            name = filename.replace("_embedding.npy", "")
            embedding = np.load(f"trusted_faces/{filename}")
            trusted_embeddings.append(embedding)
            trusted_names.append(name)
            print(f"[✅] Loaded trusted face: {name}")
    
    if len(trusted_embeddings) == 0:
        print("[⚠️] No trusted face embeddings found in 'trusted_faces' directory.")
    
    return trusted_embeddings, trusted_names


# --- Initialize camera ---
def recognize_face():
    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not camera.isOpened():
        raise Exception("Error: Could not open webcam")

    # Load trusted faces
    trusted_embeddings, trusted_names = load_trusted_faces()

    if len(trusted_embeddings) == 0:
        print("[❌] No trusted faces to compare against. Exiting.")
        camera.release()
        exit()

    print("\n[🎥] Starting face recognition...")
    print("Press 'q' to quit.")

    # Recognition parameters
    TOLERANCE = 0.6  # Lower = stricter matching 

    # --- Main recognition loop ---
    while state.guard_status:
        ret, frame = camera.read()
        if not ret:
            print("Failed to grab frame")
            break

        # Convert from BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Detect face locations
        face_locations = face_recognition.face_locations(rgb_frame, model="hog")

        # If faces detected, get their encodings
        if face_locations:
            encodings = face_recognition.face_encodings(rgb_frame, face_locations, num_jitters=1)

            for (top, right, bottom, left), encoding in zip(face_locations, encodings):
                # Compare with all trusted faces
                matches = face_recognition.compare_faces(trusted_embeddings, encoding, tolerance=TOLERANCE)
                face_distances = face_recognition.face_distance(trusted_embeddings, encoding)

                # Initialize as untrusted
                #trusted = 0
                with state.lock:
                    state.intruder = True
                name = "Unknown"
                color = (0, 0, 255)  # Red for unknown

                # If any match found
                if True in matches:
                    # Get the best match
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        with state.lock:
                            state.intruder = False
                        name = trusted_names[best_match_index]
                        color = (0, 255, 0)  # Green for trusted
                        print(f"[✅] safe | Recognized: {name} (distance: {face_distances[best_match_index]:.2f})")
                    else:
                        print(f"[⚠️] intrusion | Unknown face detected")
                else:
                    print(f"[⚠️] intrusion | Unknown face detected")

                # Draw rectangle and label
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
                cv2.putText(frame, f"{name}", (left + 6, bottom - 6), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # Display the frame
        cv2.imshow("Face Recognition", frame)

        # Check for quit
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("\n[👋] Quitting...")
            break

    # Cleanup
    camera.release()
    cv2.destroyAllWindows()
# recognize_face()