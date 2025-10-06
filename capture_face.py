"""
Face Capture Utility
Captures and saves face embeddings for trusted individuals
"""

import cv2
import face_recognition
import numpy as np
import os

def capture_trusted_face():
    """
    Capture face embedding for a trusted person.
    Saves embedding to trusted_faces directory.
    """
    print("\n" + "="*60)
    print("TRUSTED FACE ENROLLMENT")
    print("="*60)
    
    # Get person's name
    name = input("\nEnter person's name (e.g., 'john', 'owner'): ").strip()
    
    if not name:
        print("❌ Name cannot be empty")
        return
    
    # Create directory if it doesn't exist
    os.makedirs("trusted_faces", exist_ok=True)
    
    # Check if already exists
    filename = f"trusted_faces/{name}_embedding.npy"
    if os.path.exists(filename):
        overwrite = input(f"⚠️  '{name}' already exists. Overwrite? (y/n): ").strip().lower()
        if overwrite != 'y':
            print("❌ Cancelled")
            return
    
    print("\n" + "="*60)
    print("INSTRUCTIONS")
    print("="*60)
    print("1. Position your face in the camera frame")
    print("2. Look directly at the camera")
    print("3. Ensure good lighting")
    print("4. Press SPACE to capture when ready")
    print("5. Press 'q' to cancel")
    print("="*60 + "\n")
    
    # Initialize camera
    print("📷 Opening camera...")
    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    if not camera.isOpened():
        print("❌ Could not open webcam")
        return
    
    print("✅ Camera ready!")
    print("\nPosition yourself and press SPACE to capture...")
    
    captured = False
    encoding = None
    
    while not captured:
        ret, frame = camera.read()
        
        if not ret:
            print("❌ Failed to grab frame")
            break
        
        # Convert to RGB for face_recognition
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations = face_recognition.face_locations(rgb_frame, model="hog")
        
        # Draw rectangles around faces
        for (top, right, bottom, left) in face_locations:
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            cv2.putText(
                frame,
                "Face detected - Press SPACE",
                (left, top - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2
            )
        
        # Show instructions on frame
        cv2.putText(
            frame,
            f"Enrolling: {name}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )
        
        cv2.putText(
            frame,
            "SPACE = Capture | Q = Cancel",
            (10, 460),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )
        
        # Display frame
        cv2.imshow("Face Enrollment", frame)
        
        # Check for key press
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord(' '):  # Space bar
            if len(face_locations) == 0:
                print("⚠️  No face detected! Try again...")
                continue
            
            if len(face_locations) > 1:
                print("⚠️  Multiple faces detected! Please ensure only one person is visible...")
                continue
            
            print("\n📸 Capturing face...")
            
            # Get face encoding
            encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            
            if len(encodings) > 0:
                encoding = encodings[0]
                print("✅ Face captured successfully!")
                captured = True
            else:
                print("❌ Failed to extract face encoding. Try again...")
        
        elif key == ord('q'):
            print("\n❌ Cancelled")
            break
    
    # Cleanup camera
    camera.release()
    cv2.destroyAllWindows()
    
    if captured and encoding is not None:
        # Save encoding
        np.save(filename, encoding)
        print(f"\n✅ Face embedding saved: {filename}")
        print(f"✅ {name} is now a trusted face!")
        print("\n" + "="*60)
        print("ENROLLMENT COMPLETE")
        print("="*60)
        return True
    else:
        print("\n❌ Enrollment failed")
        return False


def list_trusted_faces():
    """List all enrolled trusted faces."""
    print("\n" + "="*60)
    print("ENROLLED TRUSTED FACES")
    print("="*60 + "\n")
    
    if not os.path.exists("trusted_faces"):
        print("No trusted faces enrolled yet.")
        print("Run this script to enroll faces.")
        return
    
    files = [f for f in os.listdir("trusted_faces") if f.endswith("_embedding.npy")]
    
    if len(files) == 0:
        print("No trusted faces found.")
    else:
        print(f"Found {len(files)} trusted face(s):\n")
        for i, filename in enumerate(sorted(files), 1):
            name = filename.replace("_embedding.npy", "")
            print(f"  {i}. {name}")
    
    print("\n" + "="*60)


def delete_trusted_face():
    """Delete a trusted face."""
    list_trusted_faces()
    
    if not os.path.exists("trusted_faces"):
        return
    
    files = [f for f in os.listdir("trusted_faces") if f.endswith("_embedding.npy")]
    
    if len(files) == 0:
        return
    
    print("\n" + "="*60)
    name = input("Enter name to delete (or press Enter to cancel): ").strip()
    
    if not name:
        print("Cancelled")
        return
    
    filename = f"trusted_faces/{name}_embedding.npy"
    
    if not os.path.exists(filename):
        print(f"❌ '{name}' not found")
        return
    
    confirm = input(f"⚠️  Delete '{name}'? (y/n): ").strip().lower()
    
    if confirm == 'y':
        os.remove(filename)
        print(f"✅ Deleted: {name}")
    else:
        print("Cancelled")


def main():
    """Main menu for face enrollment."""
    while True:
        print("\n" + "="*60)
        print("FACE ENROLLMENT UTILITY")
        print("="*60)
        print("\nOptions:")
        print("  1. Enroll new trusted face")
        print("  2. List trusted faces")
        print("  3. Delete trusted face")
        print("  4. Exit")
        print("="*60)
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == '1':
            capture_trusted_face()
        elif choice == '2':
            list_trusted_faces()
        elif choice == '3':
            delete_trusted_face()
        elif choice == '4':
            print("\n👋 Goodbye!")
            break
        else:
            print("❌ Invalid option")


if __name__ == "__main__":
    main()