"""
Face Recognition Module for AI Room Guard
Detects faces and identifies trusted vs untrusted individuals
macOS-compatible version (no GUI in thread)
"""

import cv2
import face_recognition
import numpy as np
import os
from state import state
import time

# Configuration
TOLERANCE = 0.6  # Lower = stricter matching (0.4-0.6 recommended)
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
CHECK_INTERVAL = 0.5  # seconds between face checks
SHOW_WINDOW = False  # Set to False on macOS to avoid threading issues


def load_trusted_faces():
    """
    Load all saved face embeddings from the trusted_faces directory.
    
    Returns:
        tuple: (list of embeddings, list of names)
    """
    trusted_embeddings = []
    trusted_names = []
    
    if not os.path.exists("trusted_faces"):
        print("[FACE] ⚠️  No 'trusted_faces' directory found.")
        print("[FACE] Please run: python capture_face.py")
        return [], []
    
    # Load all .npy embedding files
    for filename in sorted(os.listdir("trusted_faces")):
        if filename.endswith("_embedding.npy"):
            name = filename.replace("_embedding.npy", "")
            try:
                embedding = np.load(f"trusted_faces/{filename}")
                trusted_embeddings.append(embedding)
                trusted_names.append(name)
                print(f"[FACE] ✅ Loaded trusted face: {name}")
            except Exception as e:
                print(f"[FACE] ⚠️  Failed to load {filename}: {e}")
    
    if len(trusted_embeddings) == 0:
        print("[FACE] ⚠️  No trusted face embeddings found.")
    
    return trusted_embeddings, trusted_names


def recognize_face_headless():
    """
    Face recognition without GUI (safe for background threads on macOS).
    Monitors camera while guard_status is True.
    Sets state.intruder flag when unknown face detected.
    """
    print("[FACE] 🎥 Initializing camera (headless mode)...")
    
    # Initialize camera
    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    
    if not camera.isOpened():
        raise Exception("[FACE] ❌ Could not open webcam")
    
    print("[FACE] ✅ Camera initialized")
    
    # Load trusted faces
    trusted_embeddings, trusted_names = load_trusted_faces()
    
    if len(trusted_embeddings) == 0:
        print("[FACE] ❌ No trusted faces to compare against.")
        camera.release()
        return
    
    print(f"[FACE] 🎥 Monitoring for faces (headless mode)...")
    print(f"[FACE] Trusted faces: {', '.join(trusted_names)}")
    print("[FACE] Press Ctrl+C to stop")
    
    last_detection_time = 0
    consecutive_unknowns = 0
    UNKNOWN_THRESHOLD = 3  # Number of consecutive unknown detections before triggering
    
    # Main recognition loop - runs while guard is active
    try:
        while state.guard_status:
            ret, frame = camera.read()
            
            if not ret:
                print("[FACE] ⚠️  Failed to grab frame")
                time.sleep(0.1)
                continue
            
            current_time = time.time()
            
            # Only check faces every CHECK_INTERVAL seconds
            if current_time - last_detection_time < CHECK_INTERVAL:
                continue
            
            last_detection_time = current_time
            
            # Convert from BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Detect face locations
            face_locations = face_recognition.face_locations(rgb_frame, model="hog")
            
            # Process detected faces
            if face_locations:
                # Get face encodings
                encodings = face_recognition.face_encodings(
                    rgb_frame, 
                    face_locations, 
                    num_jitters=1
                )
                
                for encoding in encodings:
                    # Compare with all trusted faces
                    matches = face_recognition.compare_faces(
                        trusted_embeddings, 
                        encoding, 
                        tolerance=TOLERANCE
                    )
                    face_distances = face_recognition.face_distance(
                        trusted_embeddings, 
                        encoding
                    )
                    
                    # Check if any match found
                    is_trusted = False
                    name = "Unknown"
                    
                    if True in matches:
                        # Get the best match
                        best_match_index = np.argmin(face_distances)
                        
                        if matches[best_match_index]:
                            name = trusted_names[best_match_index]
                            is_trusted = True
                            distance = face_distances[best_match_index]
                            
                            print(f"[FACE] ✅ Recognized: {name} (confidence: {1-distance:.2%})")
                            consecutive_unknowns = 0
                            
                            # Clear intruder flag for trusted person
                            with state.lock:
                                state.intruder = False
                                state.current_speaker = name
                                state.speaker_is_trusted = True
                    
                    if not is_trusted:
                        consecutive_unknowns += 1
                        print(f"[FACE] ⚠️  Unknown face detected ({consecutive_unknowns}/{UNKNOWN_THRESHOLD})")
                        
                        # Only trigger intruder after multiple detections
                        if consecutive_unknowns >= UNKNOWN_THRESHOLD:
                            with state.lock:
                                if not state.intruder:
                                    print("[FACE] 🚨 INTRUDER CONFIRMED!")
                                state.intruder = True
                                state.current_speaker = "Unknown"
                                state.speaker_is_trusted = False
            else:
                # No faces detected - reset counter
                consecutive_unknowns = 0
    
    except KeyboardInterrupt:
        print("\n[FACE] 👋 Stopping face recognition...")
    
    finally:
        # Cleanup
        print("[FACE] Releasing camera...")
        camera.release()
        print("[FACE] ✅ Camera released")


def recognize_face():
    """
    Main entry point for face recognition.
    Uses headless mode (no GUI window).
    """
    recognize_face_headless()


# Testing function
def test_face_recognition():
    """Test face recognition without guard system."""
    print("\n" + "="*60)
    print("FACE RECOGNITION TEST MODE")
    print("="*60)
    
    # Temporarily enable guard status for testing
    state.guard_status = True
    
    try:
        recognize_face()
    except KeyboardInterrupt:
        print("\n[TEST] Interrupted")
    finally:
        state.guard_status = False
    
    print("[TEST] Test complete")


if __name__ == "__main__":
    test_face_recognition()