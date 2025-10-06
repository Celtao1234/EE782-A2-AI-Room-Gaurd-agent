# camera_module.py
import cv2
import face_recognition
import numpy as np
import os
import time
from state import state

TOLERANCE = 0.6  # Lower = stricter matching

def load_trusted_faces():
    """Load all saved face embeddings from the trusted_faces directory"""
    trusted_embeddings = []
    trusted_names = []
    
    if not os.path.exists("trusted_faces"):
        print("[⚠️] No 'trusted_faces' directory found. Please run capture_face.py first.")
        return [], []
    
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


def recognize_face():
    """Continuously monitor camera feed when guard mode is active."""
    print("[CAMERA] Starting real-time face recognition...")
    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not camera.isOpened():
        print("[❌ CAMERA] Could not open webcam.")
        return

    trusted_embeddings, trusted_names = load_trusted_faces()
    if len(trusted_embeddings) == 0:
        print("[❌ CAMERA] No trusted faces loaded. Exiting camera module.")
        camera.release()
        return

    while True:
        with state.lock:
            if not state.guard_status:
                # Guard is off → pause camera monitoring
                time.sleep(1)
                continue

        ret, frame = camera.read()
        if not ret:
            print("[CAMERA] Failed to grab frame.")
            continue

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame, model="hog")
        
        if face_locations:
            encodings = face_recognition.face_encodings(rgb_frame, face_locations, num_jitters=1)
            for encoding in encodings:
                matches = face_recognition.compare_faces(trusted_embeddings, encoding, tolerance=TOLERANCE)
                face_distances = face_recognition.face_distance(trusted_embeddings, encoding)

                if True in matches:
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        with state.lock:
                            state.intruder = False
                        print(f"[✅ CAMERA] Trusted face: {trusted_names[best_match_index]} ({face_distances[best_match_index]:.2f})")
                    else:
                        with state.lock:
                            state.intruder = True
                        print("[⚠️ CAMERA] Unknown face detected")
                else:
                    with state.lock:
                        state.intruder = True
                    print("[⚠️ CAMERA] Unknown face detected")

        # To avoid CPU overload
        time.sleep(0.2)

    camera.release()
    print("[CAMERA] Stopped face recognition.")
