import threading
import time
from multiprocessing import Process
from llm_module import gemini_response, GuardEscalationFSM, analyze_visitor_intent
from TTS import speak_safe, alarm
from STT import listen_once, audio_listener
from state import state

# Try to import face recognition module
try:
    from face_recognition_module import recognize_face, load_trusted_faces
    FACE_RECOGNITION_AVAILABLE = True
    print("[SYSTEM] ✅ Face recognition module loaded")
except ImportError as e:
    print(f"[SYSTEM] ⚠️ Face recognition not available: {e}")
    print("[SYSTEM] Running in simulation mode")
    FACE_RECOGNITION_AVAILABLE = False

# -------------------------
# Configuration
# -------------------------
USE_REAL_CAMERA = True  # Set to False to use simulation
SIMULATION_DELAY = 15  # seconds before simulating intruder (if camera disabled)


def main_guard_loop():
    """
    Main guard interaction loop.
    Handles conversation with visitor using escalating responses.
    """
    print("\n" + "="*60)
    print("🤖 AI ROOM GUARD - INTRUDER DETECTED")
    print("="*60 + "\n")
    
    fsm = GuardEscalationFSM()
    
    print(f"[GUARD] Starting at escalation level {fsm.get_level()}")
    initial_response = gemini_response("A visitor has entered the room.", fsm.get_level())
    speak_safe(initial_response)
    fsm.escalate()
    
    while not fsm.should_trigger_alarm():
        visitor_text = listen_once()
        if not visitor_text:
            time.sleep(1)
            continue
        
        print(f"\n[VISITOR] {visitor_text}")
        intent = analyze_visitor_intent(visitor_text)
        print(f"[ANALYSIS] Intent: {intent}")
        
        if intent['leaving']:
            farewell = gemini_response(visitor_text, fsm.get_level())
            speak_safe(farewell)
            print("\n[GUARD] ✅ Visitor is leaving. Returning to standby mode.")
            break
        
        response = gemini_response(visitor_text, fsm.get_level())
        speak_safe(response)
        
        if intent['compliant']:
            print("[GUARD] Visitor seems compliant, maintaining level")
        elif intent['aggressive']:
            print("[GUARD] Aggressive behavior detected, escalating faster")
            fsm.escalate()
            fsm.escalate()
        else:
            print("[GUARD] No cooperation, escalating")
            fsm.escalate()
        
        print(f"[GUARD] Current escalation level: {fsm.get_level()}/{fsm.max_level}")
        time.sleep(0.5)
    
    if fsm.should_trigger_alarm():
        print("\n[GUARD] ⚠️ MAXIMUM ESCALATION REACHED")
        print("[GUARD] 🚨 TRIGGERING ALARM")
        alarm()
    
    with state.lock:
        state.intruder = False
    
    print("\n[GUARD] Returning to monitoring mode...\n")


def fsm_controller():
    """
    Finite State Machine controller.
    Manages transitions between listening and guard modes.
    """
    print("[FSM] Controller started")
    
    while True:
        try:
            if state.guard_status:
                if state.intruder:
                    print("\n[FSM] 🚨 Intruder detected, starting guard protocol")
                    main_guard_loop()
                else:
                    time.sleep(0.5)
            else:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n[FSM] Shutting down...")
            break
        except Exception as e:
            print(f"[FSM] Error: {e}")
            time.sleep(1)


def camera_monitor():
    """
    Monitor camera for face recognition.
    Runs continuously when guard mode is active.
    """
    if not FACE_RECOGNITION_AVAILABLE:
        print("[CAMERA] Face recognition not available, using simulation")
        camera_simulator()
        return
    
    print("[CAMERA] Starting real face recognition monitor...")
    try:
        trusted_embeddings, trusted_names = load_trusted_faces()
        if len(trusted_embeddings) == 0:
            print("[CAMERA] ⚠️ No trusted faces found! Please run: python capture_face.py")
            print("[CAMERA] Falling back to simulation mode")
            camera_simulator()
            return
        
        print(f"[CAMERA] Loaded {len(trusted_names)} trusted face(s): {', '.join(trusted_names)}")
    except Exception as e:
        print(f"[CAMERA] Error loading trusted faces: {e}")
        camera_simulator()
        return
    
    while not state.guard_status:
        time.sleep(0.5)
    
    print("[CAMERA] 🎥 Guard mode active - starting face recognition")
    try:
        recognize_face()
    except Exception as e:
        print(f"[CAMERA] ❌ Face recognition error: {e}")
        print("[CAMERA] Camera monitoring stopped")
    
    print("[CAMERA] Face recognition monitor stopped")


def camera_simulator():
    """
    Simulates camera motion detection for testing.
    Used when real camera is not available.
    """
    print(f"[CAMERA] Simulation mode - will trigger in {SIMULATION_DELAY} seconds")
    
    while not state.guard_status:
        time.sleep(0.5)
    
    time.sleep(SIMULATION_DELAY)
    
    if state.guard_status:
        print("\n[CAMERA] 🎥 ═══════════════════════════════════")
        print("[CAMERA] 🎥 MOTION DETECTED (SIMULATED)!")
        print("[CAMERA] 🎥 ═══════════════════════════════════\n")
        with state.lock:
            state.intruder = True
    else:
        print("[CAMERA] Motion detected but guard is OFF - ignoring")


def status_monitor():
    """
    Background thread to monitor and display system status.
    """
    while True:
        time.sleep(10)
        status = state.get_status()
        guard = "🔒 ACTIVE" if status['guard_active'] else "🛑 INACTIVE"
        intruder = "⚠️ YES" if status['intruder_detected'] else "✅ NO"
        speaker = status['current_speaker'] if status['current_speaker'] else "None"
        print(f"\n[STATUS] Guard: {guard} | Intruder: {intruder} | Speaker: {speaker}")


def main():
    """
    Main entry point for the AI Room Guard system.
    """
    print("\n" + "="*60)
    print("🤖 AI ROOM GUARD SYSTEM")
    print("="*60)
    print("\n[SYSTEM] Initializing...")
    
    camera_mode = "Real Camera" if (USE_REAL_CAMERA and FACE_RECOGNITION_AVAILABLE) else "Simulation"
    print(f"[SYSTEM] Camera Mode: {camera_mode}")
    
    # Audio listener thread
    print("[SYSTEM] Starting audio listener...")
    listener_thread = threading.Thread(target=audio_listener, daemon=True)
    listener_thread.start()
    time.sleep(2)
    
    # FSM controller
    print("[SYSTEM] Starting FSM controller...")
    fsm_thread = threading.Thread(target=fsm_controller, daemon=True)
    fsm_thread.start()
    
    # Camera monitor (now in a separate process!)
    print("[SYSTEM] Starting camera monitor...")
    if camera_mode == "Real Camera":
        camera_thread = threading.Thread(target=camera_monitor, daemon=True)
        camera_thread.start()

    else:
        camera_thread = threading.Thread(target=camera_simulator, daemon=True)
        camera_thread.start()
    
    # Optional: status monitor
    # status_thread = threading.Thread(target=status_monitor, daemon=True)
    # status_thread.start()
    
    print("\n" + "="*60)
    print("✅ SYSTEM READY")
    print("="*60)
    print("\n📢 INSTRUCTIONS:")
    print("   1. Say 'watch my room' to ACTIVATE guard mode")
    print("   2. Say 'stop watching' to DEACTIVATE guard mode")
    if camera_mode == "Real Camera":
        print("   3. Camera will monitor for faces automatically")
        print("   4. Trusted faces: No alarm | Unknown faces: Guard activates")
        print("\n   💡 TIP: Press 'q' in camera window to stop monitoring")
    else:
        print(f"   3. Camera will simulate intruder in {SIMULATION_DELAY}s after activation")
    
    print("\n   Press Ctrl+C to exit\n")
    print("="*60 + "\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("👋 SHUTTING DOWN AI ROOM GUARD")
        print("="*60)
        with state.lock:
            state.guard_status = False
            state.intruder = False
        time.sleep(1)
        print("\n[SYSTEM] Goodbye!\n")


if __name__ == "__main__":
    main()
import threading
import time
from llm_module import gemini_response, GuardEscalationFSM, analyze_visitor_intent
from TTS import speak_safe, alarm
from STT import listen_once, audio_listener
from state import state

# Try to import face recognition module
try:
    from face_recognition_module import recognize_face, load_trusted_faces
    FACE_RECOGNITION_AVAILABLE = True
    print("[SYSTEM] ✅ Face recognition module loaded")
except ImportError as e:
    print(f"[SYSTEM] ⚠️  Face recognition not available: {e}")
    print("[SYSTEM] Running in simulation mode")
    FACE_RECOGNITION_AVAILABLE = False

# -------------------------
# Configuration
# -------------------------
USE_REAL_CAMERA = True  # Set to False to use simulation
SIMULATION_DELAY = 15  # seconds before simulating intruder (if camera disabled)


def main_guard_loop():
    """
    Main guard interaction loop.
    Handles conversation with visitor using escalating responses.
    Camera is paused during this interaction.
    """
    print("\n" + "="*60)
    print("🤖 AI ROOM GUARD - INTRUDER DETECTED")
    print("="*60 + "\n")
    
    fsm = GuardEscalationFSM()
    
    # Initial greeting
    print(f"[GUARD] Starting at escalation level {fsm.get_level()}")
    initial_response = gemini_response("A visitor has entered the room.", fsm.get_level())
    speak_safe(initial_response)
    fsm.escalate()
    
    # Main interaction loop
    while not fsm.should_trigger_alarm():
        # Listen for visitor response
        visitor_text = listen_once()
        
        if not visitor_text:
            # No response, wait a bit and try again
            time.sleep(1)
            continue
        
        print(f"\n[VISITOR] {visitor_text}")
        
        # Analyze visitor's intent
        intent = analyze_visitor_intent(visitor_text)
        print(f"[ANALYSIS] Intent: {intent}")
        
        # Check if visitor is leaving
        if intent['leaving']:
            farewell = gemini_response(visitor_text, fsm.get_level())
            speak_safe(farewell)
            print("\n[GUARD] ✅ Visitor is leaving. Returning to standby mode.")
            break
        
        # Generate contextual response
        response = gemini_response(visitor_text, fsm.get_level())
        speak_safe(response)
        
        # Adjust escalation based on visitor behavior
        if intent['compliant']:
            print("[GUARD] Visitor seems compliant, maintaining level")
            # Don't escalate if they're being cooperative
        elif intent['aggressive']:
            print("[GUARD] Aggressive behavior detected, escalating faster")
            fsm.escalate()
            fsm.escalate()  # Double escalate for aggression
        else:
            print("[GUARD] No cooperation, escalating")
            fsm.escalate()
        
        print(f"[GUARD] Current escalation level: {fsm.get_level()}/{fsm.max_level}")
        
        # Small pause between interactions
        time.sleep(0.5)
    
    # Maximum escalation reached - trigger alarm
    if fsm.should_trigger_alarm():
        print("\n[GUARD] ⚠️  MAXIMUM ESCALATION REACHED")
        print("[GUARD] 🚨 TRIGGERING ALARM")
        alarm()
        
        # Resume camera after alarm
        print("\n[GUARD] 📷 Resuming camera monitoring...")
        state.resume_camera()
    
    # Reset intruder flag
    with state.lock:
        state.intruder = False
    
    print("\n[GUARD] Returning to monitoring mode...\n")


def fsm_controller():
    """
    Finite State Machine controller.
    Manages transitions between listening and guard modes.
    """
    print("[FSM] Controller started")
    
    while True:
        try:
            # Check current state
            if state.guard_status:
                # Guard mode is active
                if state.intruder and state.intruder_confirmed:
                    # Intruder confirmed - start guard loop
                    print("\n[FSM] 🚨 Intruder confirmed, starting conversation protocol")
                    main_guard_loop()
                else:
                    # Guard active but no confirmed intruder - just wait
                    time.sleep(0.5)
            else:
                # Guard mode inactive - just wait
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print("\n[FSM] Shutting down...")
            break
        except Exception as e:
            print(f"[FSM] Error: {e}")
            time.sleep(1)


def camera_monitor():
    """
    Monitor camera for face recognition.
    Runs continuously when guard mode is active.
    Automatically pauses when intruder is confirmed.
    Resumes after alarm is triggered.
    """
    if not USE_REAL_CAMERA or not FACE_RECOGNITION_AVAILABLE:
        print("[CAMERA] Face recognition not available, using simulation")
        camera_simulator()
        return
    
    print("[CAMERA] Starting real face recognition monitor...")
    
    # Check if trusted faces exist
    try:
        trusted_embeddings, trusted_names = load_trusted_faces()
        
        if len(trusted_embeddings) == 0:
            print("[CAMERA] ⚠️  No trusted faces found!")
            print("[CAMERA] Please run: python capture_face.py")
            print("[CAMERA] Falling back to simulation mode")
            camera_simulator()
            return
        
        print(f"[CAMERA] Loaded {len(trusted_names)} trusted face(s): {', '.join(trusted_names)}")
        
    except Exception as e:
        print(f"[CAMERA] Error loading trusted faces: {e}")
        print("[CAMERA] Falling back to simulation mode")
        camera_simulator()
        return
    
    # Main camera loop - restarts after each alarm cycle
    while True:
        # Wait for guard mode to be activated
        while not state.guard_status:
            time.sleep(0.5)
        
        print("[CAMERA] 🎥 Guard mode active - starting face recognition")
        
        try:
            # Run face recognition (will pause when intruder confirmed)
            recognize_face()
            
        except Exception as e:
            print(f"[CAMERA] ❌ Face recognition error: {e}")
            print("[CAMERA] Camera monitoring stopped")
        
        # Wait a bit before potentially restarting
        time.sleep(1)
        
        # If guard is still active, camera will restart automatically
        if state.guard_status:
            print("[CAMERA] 🔄 Restarting camera monitoring...")


def camera_simulator():
    """
    Simulates camera motion detection for testing.
    Used when real camera is not available.
    """
    print(f"[CAMERA] Simulation mode - will trigger in {SIMULATION_DELAY} seconds")
    
    while True:
        # Wait for guard mode to be activated
        while not state.guard_status:
            time.sleep(0.5)
        
        time.sleep(SIMULATION_DELAY)
        
        # Only trigger if guard mode is still active
        if state.guard_status:
            print("\n[CAMERA] 🎥 ═══════════════════════════════════")
            print("[CAMERA] 🎥 MOTION DETECTED (SIMULATED)!")
            print("[CAMERA] 🎥 ═══════════════════════════════════\n")
            
            with state.lock:
                state.intruder = True
            
            # Confirm intruder after detection
            state.confirm_intruder()
            
            # Wait for guard loop to complete
            while state.intruder_confirmed and state.guard_status:
                time.sleep(1)
            
            print("[CAMERA] 🔄 Simulation cycle complete, monitoring resumed")


def status_monitor():
    """
    Background thread to monitor and display system status.
    Optional - helps with debugging.
    """
    while True:
        time.sleep(10)  # Update every 10 seconds
        
        status = state.get_status()
        
        guard = "🔒 ACTIVE" if status['guard_active'] else "🛑 INACTIVE"
        intruder = "⚠️  YES" if status['intruder_detected'] else "✅ NO"
        camera = "🎥 ON" if status['camera_active'] else "📷 PAUSED"
        speaker = status['current_speaker'] if status['current_speaker'] else "None"
        
        print(f"\n[STATUS] Guard: {guard} | Intruder: {intruder} | Camera: {camera} | Speaker: {speaker}")


def main():
    """
    Main entry point for the AI Room Guard system.
    """
    print("\n" + "="*60)
    print("🤖 AI ROOM GUARD SYSTEM")
    print("="*60)
    print("\n[SYSTEM] Initializing...")
    
    # Check camera mode
    camera_mode = "Real Camera" if (USE_REAL_CAMERA and FACE_RECOGNITION_AVAILABLE) else "Simulation"
    print(f"[SYSTEM] Camera Mode: {camera_mode}")
    
    # Start audio listener thread
    print("[SYSTEM] Starting audio listener...")
    listener_thread = threading.Thread(target=audio_listener, daemon=True)
    listener_thread.start()
    
    # Wait a moment for listener to initialize
    time.sleep(2)
    
    # Start FSM controller thread
    print("[SYSTEM] Starting FSM controller...")
    fsm_thread = threading.Thread(target=fsm_controller, daemon=True)
    fsm_thread.start()
    
    # Start camera monitor thread
    print("[SYSTEM] Starting camera monitor...")
    camera_thread = threading.Thread(target=camera_monitor, daemon=True)
    camera_thread.start()
    
    # Optional: Start status monitor
    status_thread = threading.Thread(target=status_monitor, daemon=True)
    status_thread.start()
    
    print("\n" + "="*60)
    print("✅ SYSTEM READY")
    print("="*60)
    print("\n📢 INSTRUCTIONS:")
    print("   1. Say 'watch my room' to ACTIVATE guard mode")
    print("   2. Say 'stop watching' to DEACTIVATE guard mode")
    
    if camera_mode == "Real Camera":
        print("\n🎥 CAMERA BEHAVIOR:")
        print("   • Camera monitors continuously while guard is active")
        print("   • When intruder detected → Camera PAUSES")
        print("   • AI guard talks to intruder (escalating responses)")
        print("   • If escalation reaches maximum → ALARM triggers")
        print("   • After alarm → Camera RESUMES monitoring")
    else:
        print(f"   3. Camera will simulate intruder in {SIMULATION_DELAY}s after activation")
    
    print("\n   Press Ctrl+C to exit\n")
    print("="*60 + "\n")
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("👋 SHUTTING DOWN AI ROOM GUARD")
        print("="*60)
        
        # Clean shutdown
        with state.lock:
            state.guard_status = False
            state.intruder = False
            state.camera_active = False
        
        time.sleep(1)  # Give threads time to exit
        
        print("\n[SYSTEM] Goodbye!\n")


if __name__ == "__main__":
    main()