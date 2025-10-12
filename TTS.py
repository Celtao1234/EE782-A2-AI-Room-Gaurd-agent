import subprocess
import time
import platform
from state import state

# Detect OS
IS_MACOS = platform.system() == 'Darwin'

print("[TTS] Initializing text-to-speech engine...")

if IS_MACOS:
    print("[TTS] 🍎 Detected macOS - using native 'say' command")
    engine_type = "macos_say"
    engine = None
else:
    print("[TTS] Using pyttsx3 engine")
    engine_type = "pyttsx3"
    try:
        import pyttsx3
        engine = pyttsx3.init()
        
        # Configure voice properties
        voices = engine.getProperty('voices')
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 0.9)
        
        # Try to set a more authoritative voice
        for voice in voices:
            if 'male' in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break
        
        print("[TTS] ✅ pyttsx3 engine initialized")
    except Exception as e:
        print(f"[TTS] ⚠️  Error initializing pyttsx3: {e}")
        engine = None


def speak_with_say(text):
    """
    Use macOS native 'say' command for TTS.
    This is more reliable than pyttsx3 on macOS.
    
    Args:
        text: Text to speak
    """
    try:
        print(f"[TTS] 🎵 Speaking with macOS say command...")
        
        # Just use the simplest form - let macOS pick the default voice
        # This is the most reliable approach
        result = subprocess.run(
            ['say', text],
            check=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"[TTS] 🎵 Audio output finished")
        
        # Extra buffer to ensure audio completes
        time.sleep(0.8)
        
        return True
        
    except subprocess.TimeoutExpired:
        print("[TTS] ❌ Say command timed out")
        return False
    except subprocess.CalledProcessError as e:
        print(f"[TTS] ❌ Say command failed: {e}")
        if e.stderr:
            print(f"[TTS] stderr: {e.stderr}")
        if e.stdout:
            print(f"[TTS] stdout: {e.stdout}")
        return False
    except FileNotFoundError:
        print("[TTS] ❌ 'say' command not found (not on macOS?)")
        return False
    except Exception as e:
        print(f"[TTS] ❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def speak_with_pyttsx3(text):
    """
    Use pyttsx3 for TTS (Linux/Windows).
    
    Args:
        text: Text to speak
    """
    global engine
    
    if not engine:
        print("[TTS] ❌ Engine not available, attempting to reinitialize...")
        if not init_engine():
            print(f"[TTS] Would say: {text}")
            return False
    
    try:
        print(f"[TTS] 🎵 Audio output starting...")
        
        engine.say(text)
        engine.runAndWait()
        
        print(f"[TTS] 🎵 Audio output finished by engine")
        
        # Wait for audio to finish playing through speakers
        time.sleep(1.5)
        
        print(f"[TTS] 🎬 Speech completed successfully")
        return True
        
    except Exception as e:
        print(f"[TTS] ⚠️  Error speaking: {e}")
        return False


def init_engine():
    """Initialize or reinitialize the pyttsx3 engine."""
    global engine
    
    if engine_type == "macos_say":
        return True  # No engine needed for 'say' command
    
    try:
        import pyttsx3
        
        if engine is not None:
            try:
                engine.stop()
            except:
                pass
        
        engine = pyttsx3.init()
        
        # Configure voice properties
        voices = engine.getProperty('voices')
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 0.9)
        
        # Try to set a more authoritative voice
        for voice in voices:
            if 'male' in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break
        
        print("[TTS] ✅ TTS engine initialized")
        return True
    except Exception as e:
        print(f"[TTS] ⚠️  Error initializing: {e}")
        engine = None
        return False


def speak_safe(text, retry_count=0):
    """
    Speak text while pausing STT to prevent echo/feedback.
    Automatically uses the best TTS method for the current OS.
    
    Args:
        text: Text to speak
        retry_count: Internal retry counter
    """
    # Check if already speaking (defensive check)
    if state.tts_playing:
        print("[TTS] ⚠️  Already speaking! Waiting...")
        timeout = 0
        while state.tts_playing and timeout < 50:  # 5 second timeout
            time.sleep(0.1)
            timeout += 1
        
        if state.tts_playing:
            print("[TTS] ⚠️  Timeout waiting for TTS! Force clearing flag...")
            with state.lock:
                state.tts_playing = False
    
    print(f"\n[GUARD] 🗣️  '{text}'\n")
    print(f"[TTS] 🎬 Starting speech (flag: {state.tts_playing} -> True)")
    
    # Set TTS playing flag BEFORE speaking
    with state.lock:
        state.tts_playing = True
    
    # Small delay to ensure STT sees the flag
    time.sleep(0.2)
    
    success = False
    
    try:
        # Use appropriate TTS method based on OS
        if engine_type == "macos_say":
            success = speak_with_say(text)
        else:
            success = speak_with_pyttsx3(text)
        
        if not success and retry_count == 0:
            print("[TTS] 🔄 First attempt failed, retrying...")
            with state.lock:
                state.tts_playing = False
            time.sleep(0.5)
            speak_safe(text, retry_count=1)
            return
            
    except Exception as e:
        print(f"[TTS] ⚠️  Error in speak_safe: {e}")
        
    finally:
        # Always clear the flag, even if there's an error
        print(f"[TTS] 🎬 Ending speech (flag: {state.tts_playing} -> False)")
        with state.lock:
            state.tts_playing = False
        
        # CRITICAL: Extra buffer AFTER clearing flag
        time.sleep(1.5)  # Longer wait for macOS
        print("[TTS] ✅ Finished speaking, STT can resume")


def alarm():
    """
    Play alarm sound and message.
    Called when maximum escalation is reached.
    """
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
            if engine_type == "macos_say":
                speak_with_say(alarm_message)
            else:
                if engine:
                    engine.say(alarm_message)
                    engine.runAndWait()
                else:
                    print(f"[TTS] {alarm_message}")
            
            time.sleep(0.5)
        
        print("\n" + "="*60 + "\n")
        
        # Wait after alarm
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
    print(f"[TEST] Engine type: {engine_type}")
    
    if engine_type == "macos_say":
        print("[TEST] Using macOS 'say' command")
        print("\n[TEST] Available voices on your Mac:")
        try:
            result = subprocess.run(['say', '-v', '?'], capture_output=True, text=True)
            print(result.stdout[:500])  # Show first 500 chars
        except:
            pass
    
    test_messages = [
        "Testing one two three.",
        "Hello, this is a test of the text to speech system.",
        "Can you hear me clearly?",
        "This is your final warning.",
        "This is the fifth test message to ensure multiple calls work correctly."
    ]
    
    for i, msg in enumerate(test_messages, 1):
        print(f"\n[TEST {i}/5] About to speak: '{msg}'")
        input("Press Enter to play this message...")
        speak_safe(msg)
        
        response = input(f"Did you hear message {i} COMPLETELY? (y/n): ").strip().lower()
        if response != 'y':
            print(f"❌ TTS failed at message {i}")
            print("   This indicates a persistent audio issue.")
            break
    else:
        print("\n✅ All 5 messages played successfully!")
    
    print("\n[TEST] Testing alarm...")
    input("Press Enter to test alarm...")
    alarm()
    
    print("\n[TEST] TTS test complete!")


if __name__ == "__main__":
    """Test mode - run TTS.py directly to test speech"""
    test_tts()