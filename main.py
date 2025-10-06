# main.py
import threading
import time
from llm_module import gemini_response, GuardEscalationFSM, analyze_visitor_intent
from TTS import speak_safe, alarm
from STT import listen_once, audio_listener
from state import state
from camera_module import recognize_face  # Your real camera module

# -------------------------
# Configuration
# -------------------------
SIMULATION_MODE = False  # Use real camera
CAMERA_THREAD_DELAY = 2  # Seconds before starting camera thread


def main_guard_loop():
    """
    Main guard interaction loop.
    Handles conversation with visitor using escalating responses.
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
        elif intent['aggressive']:
            print("[GUARD] Aggressive behavior detected, escalating faster")
            fsm.escalate()
            fsm.escalate()  # Double escalate for aggression
        else:
            print("[GUARD] No cooperation, escalating")
            fsm.escalate()
        
        print(f"[GUARD] Current escalation level: {fsm.get_level()}/{fsm.max_level}")
        time.sleep(0.5)
    
    # Maximum escalation reached - trigger alarm
    if fsm.should_trigger_alarm():
        print("\n[GUARD] ⚠️  MAXIMUM ESCALATION REACHED")
        print("[GUARD] 🚨 TRIGGERING ALARM")
        alarm()
    
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
            with state.lock:
                guard_active = state.guard_status
                intruder_detected = state.intruder

            if guard_active:
                if intruder_detected:
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


def status_monitor():
    """
    Background thread to monitor and display system status.
    Optional - helps with debugging.
    """
    while True:
        time.sleep(10)  # Update every 10 seconds
        with state.lock:
            status = "🔒 ACTIVE" if state.guard_status else "🛑 INACTIVE"
            intruder = "⚠️  YES" if state.intruder else "✅ NO"
        print(f"\n[STATUS] Guard: {status} | Intruder: {intruder}")


def main():
    """
    Main entry point for the AI Room Guard system.
    """
    print("\n" + "="*60)
    print("🤖 AI ROOM GUARD SYSTEM")
    print("="*60)
    print("\n[SYSTEM] Initializing...")
    
    # Start audio listener thread
    print("[SYSTEM] Starting audio listener...")
    listener_thread = threading.Thread(target=audio_listener, daemon=True)
    listener_thread.start()
    
    time.sleep(2)  # Allow listener to initialize
    
    # Start FSM controller thread
    print("[SYSTEM] Starting FSM controller...")
    fsm_thread = threading.Thread(target=fsm_controller, daemon=True)
    fsm_thread.start()
    
    # Start camera thread for face recognition
    print("[SYSTEM] Starting camera monitoring...")
    camera_thread = threading.Thread(target=recognize_face, daemon=True)
    camera_thread.start()
    
    # Optional: start status monitor
    # status_thread = threading.Thread(target=status_monitor, daemon=True)
    # status_thread.start()
    
    print("\n" + "="*60)
    print("✅ SYSTEM READY")
    print("="*60)
    print("\n📢 INSTRUCTIONS:")
    print("   1. Say 'watch my room' to ACTIVATE guard mode")
    print("   2. Say 'stop watching' to DEACTIVATE guard mode")
    print("   3. Real camera face recognition active")
    print("   Press Ctrl+C to exit\n")
    print("="*60 + "\n")
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("👋 SHUTTING DOWN AI ROOM GUARD")
        print("="*60)
        print("\n[SYSTEM] Goodbye!\n")


if __name__ == "__main__":
    main()
