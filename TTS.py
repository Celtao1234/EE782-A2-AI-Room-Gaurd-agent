import pyttsx3
import time
from state import state

# Initialize TTS engine
print("[TTS] Initializing text-to-speech engine...")
try:
    engine = pyttsx3.init()
    
    # Configure voice properties
    voices = engine.getProperty('voices')
    engine.setProperty('rate', 150)  # Speed of speech (default ~200)
    engine.setProperty('volume', 0.9)  # Volume (0.0 to 1.0)
    
    # Try to set a more authoritative voice (if available)
    # This will use the default voice if specific one not found
    for voice in voices:
        if 'male' in voice.name.lower():
            engine.setProperty('voice', voice.id)
            break
    
    print("[TTS] ✅ TTS engine initialized")
except Exception as e:
    print(f"[TTS] ⚠️  Error initializing: {e}")
    engine = None


def speak_safe(text):
    """
    Speak text while pausing STT to prevent echo/feedback.
    
    Args:
        text: Text to speak
    """
    if not engine:
        print("[TTS] ❌ Engine not available")
        print(f"[TTS] Would say: {text}")
        return
    
    # Set TTS playing flag BEFORE speaking
    with state.lock:
        state.tts_playing = True
    
    # Small delay to ensure STT sees the flag
    time.sleep(0.2)
    
    try:
        print(f"\n[GUARD] 🗣️  '{text}'\n")
        engine.say(text)
        engine.runAndWait()
        
        # Longer buffer to ensure TTS fully completes and sound clears
        time.sleep(0.8)  # Increased from 0.5
        
    except Exception as e:
        print(f"[TTS] ⚠️  Error speaking: {e}")
    finally:
        # Always clear the flag, even if there's an error
        with state.lock:
            state.tts_playing = False
        
        # Extra buffer time after flag is cleared
        time.sleep(0.5)  # Increased from 0.3
        print("[TTS] ✅ Finished speaking, STT can resume")


def alarm():
    """
    Play alarm sound and message.
    Called when maximum escalation is reached.
    """
    if not engine:
        print("[TTS] ❌ Engine not available")
        print("[TTS] 🚨 ALARM! ALARM! INTRUDER DETECTED!")
        return
    
    # Set TTS playing flag
    with state.lock:
        state.tts_playing = True
    
    time.sleep(0.2)
    
    try:
        print("\n" + "="*60)
        print("🚨 ALARM TRIGGERED 🚨")
        print("="*60 + "\n")
        
        # Repeat alarm message for emphasis
        alarm_message = "Alarm! Security breach! The owner has been notified. Authorities are being contacted."
        
        for i in range(2):
            engine.say(alarm_message)
            engine.runAndWait()
            time.sleep(0.5)
        
        print("\n" + "="*60 + "\n")
        
        # Longer wait after alarm
        time.sleep(1.0)
        
    except Exception as e:
        print(f"[TTS] ⚠️  Error during alarm: {e}")
    finally:
        with state.lock:
            state.tts_playing = False
        
        time.sleep(0.5)
        print("[TTS] ✅ Alarm finished")


def speak_status(active: bool):
    """
    Announce guard status change.
    
    Args:
        active: True if guard activated, False if deactivated
    """
    if active:
        message = "Guard mode activated. I am now monitoring this room."
    else:
        message = "Guard mode deactivated. Standing by."
    
    speak_safe(message)


def test_tts():
    """Test TTS functionality."""
    print("\n[TEST] Testing TTS...")
    
    test_messages = [
        "Hello, I am your AI room guard.",
        "This room is private. Please leave immediately.",
        "This is your final warning.",
    ]
    
    for msg in test_messages:
        speak_safe(msg)
        time.sleep(1)
    
    print("\n[TEST] Testing alarm...")
    alarm()
    
    print("\n[TEST] TTS test complete!")


if __name__ == "__main__":
    """Test mode - run TTS.py directly to test speech"""
    test_tts()