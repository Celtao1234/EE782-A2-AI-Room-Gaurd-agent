import pyttsx3
import time
from state import state

# ==========================================
# TTS INITIALIZATION
# ==========================================

print("[TTS] Initializing text-to-speech engine...")
try:
    engine = pyttsx3.init()

    # Configure voice properties
    voices = engine.getProperty('voices')
    engine.setProperty('rate', 150)    # Speed of speech
    engine.setProperty('volume', 0.9)  # Volume (0.0 to 1.0)

    # Try to pick a male voice if available
    for voice in voices:
        if 'male' in voice.name.lower():
            engine.setProperty('voice', voice.id)
            break

    print("[TTS] ✅ TTS engine initialized")

except Exception as e:
    print(f"[TTS] ⚠️ Error initializing TTS: {e}")
    engine = None


# ==========================================
# SAFE SPEAK FUNCTION
# ==========================================

def speak_safe(text):
    """
    Speak text while pausing STT to prevent feedback.
    """
    if not engine:
        print("[TTS] ❌ Engine not available")
        print(f"[TTS] Would say: {text}")
        return

    # Set TTS flag so STT pauses
    with state.lock:
        state.tts_playing = True

    # Give STT time to notice flag
    time.sleep(0.2)

    try:
        print(f"\n[GUARD] 🗣️ '{text}'\n")
        engine.say(text)
        engine.runAndWait()
        time.sleep(1)  # Allow sound to clear

    except Exception as e:
        print(f"[TTS] ⚠️ Error speaking: {e}")

    finally:
        with state.lock:
            state.tts_playing = False
        time.sleep(0.3)
        print("[TTS] ✅ Finished speaking, STT can resume")


# ==========================================
# ALARM FUNCTION
# ==========================================

def alarm():
    """
    Speak an alarm warning using TTS.
    Called when maximum escalation is reached.
    """
    if not engine:
        print("[TTS] ❌ Engine not available")
        print("[TTS] 🚨 ALARM! INTRUDER DETECTED!")
        return

    with state.lock:
        state.tts_playing = True

    time.sleep(0.2)

    try:
        print("\n" + "="*60)
        print("🚨 ALARM TRIGGERED 🚨")
        print("="*60 + "\n")

        # Speak the alarm message
        engine.say("Alarm! Security breach detected. The owner has been notified.")
        engine.runAndWait()

        print("\n" + "="*60 + "\n")

        time.sleep(1.0)

    except Exception as e:
        print(f"[TTS] ⚠️ Error during alarm: {e}")

    finally:
        with state.lock:
            state.tts_playing = False
        time.sleep(0.5)
        print("[TTS] ✅ Alarm finished")


# ==========================================
# STATUS ANNOUNCEMENT
# ==========================================

def speak_status(active: bool):
    """
    Announce guard status change.
    """
    if active:
        message = "Guard mode activated. I am now monitoring this room."
    else:
        message = "Guard mode deactivated. Standing by."

    speak_safe(message)


# ==========================================
# TEST FUNCTION
# ==========================================

def test_tts():
    """
    Test TTS functionality standalone.
    """
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
    engine.stop()


# ==========================================
# MAIN TEST ENTRY POINT
# ==========================================

if __name__ == "__main__":
    test_tts()
