import sounddevice as sd
import numpy as np
import whisper
import datetime
from state import state
import time
import os
# Suppress PortAudio warnings on macOS
os.environ['PYTHONWARNINGS'] = 'ignore::UserWarning'

# Set specific audio device if needed (optional)
# Uncomment and adjust if you have multiple audio devices:
# sd.default.device = 0  # Use device ID from sd.query_devices()

# -------------------------
# Configuration
# -------------------------
SAMPLE_RATE = 16000
VAD_THRESHOLD = 0.012  # Balanced threshold
LISTEN_DURATION = 5  # seconds for listen_once
CHUNK_DURATION = 5  # seconds for continuous listening
POST_TTS_WAIT = 2.0  # INCREASED: Wait after TTS finishes to let audio finish playing

print("[STT] Loading Whisper model...")
try:
    whisper_model = whisper.load_model("base")
    print("[STT] ✅ Whisper model loaded!")
except Exception as e:
    print(f"[STT] ❌ Failed to load Whisper: {e}")
    whisper_model = None


def transcribe_speech(text):
    """Log transcriptions to file with timestamp."""
    if not text:
        return
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open("transcriptions.txt", "a", encoding="utf-8") as f:
            f.write(f"{timestamp} | {text}\n")
        print(f"[STT] 📝 Logged: {text}")
    except Exception as e:
        print(f"[STT] Failed to log: {e}")


def is_tts_echo(text, audio_level):
    """
    Detect if transcribed text is likely TTS echo/feedback.
    Uses both content analysis and audio characteristics.
    
    Args:
        text: Transcribed text (lowercase)
        audio_level: Maximum audio amplitude
    
    Returns:
        bool: True if likely TTS echo
    """
    # Common phrases from guard responses
    tts_keywords = [
        "private room", "must leave", "off-limits", "not authorized",
        "alarm", "security", "warning", "authorities", "owner",
        "notified", "breach", "immediately", "final", "leave now",
        "unauthorized", "restricted", "trespassing"
    ]
    
    # Check for keyword matches
    keyword_count = sum(1 for keyword in tts_keywords if keyword in text)
    
    # If multiple keywords AND low audio level, likely echo
    if keyword_count >= 2 and audio_level < 0.025:
        return True
    
    # If very similar to common guard phrases
    guard_phrases = [
        "hello this is a private room",
        "you must leave immediately",
        "this room is off-limits",
        "this is your final warning",
        "security breach",
        "authorities are being contacted"
    ]
    
    for phrase in guard_phrases:
        # Check similarity (if text contains most of the phrase)
        words_in_phrase = phrase.split()
        matching_words = sum(1 for word in words_in_phrase if word in text)
        if matching_words >= len(words_in_phrase) * 0.7:  # 70% match
            return True
    
    return False


def wait_for_tts():
    """Wait until TTS is completely finished with smart timing."""
    # Wait while TTS is actively playing
    tts_was_playing = False
    while state.tts_playing:
        tts_was_playing = True
        time.sleep(0.1)
    
    # Only add buffer if TTS was actually playing
    if tts_was_playing:
        time.sleep(POST_TTS_WAIT)
        print("[STT] ⏰ Post-TTS wait complete")


def listen_once(duration=LISTEN_DURATION, skip_tts_check=False):
    """
    Record for specified duration and return transcription.
    Used during guard interactions with visitor.
    
    Args:
        duration: Recording duration in seconds
        skip_tts_check: If True, skip the initial TTS wait (emergency use)
    
    Returns:
        str: Transcribed text or empty string
    """
    if not whisper_model:
        print("[STT] ❌ Whisper not loaded!")
        return ""
    
    # Wait for TTS unless explicitly skipped
    if not skip_tts_check:
        wait_for_tts()
    
    print(f"[STT] 🎤 Listening... (speak now)")
    
    try:
        # Record audio
        audio_data = sd.rec(
            int(duration * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype='float32'
        )
        sd.wait()
        
        # Emergency check: if TTS started during recording, abort
        if state.tts_playing:
            print("[STT] ⚠️  TTS interference detected, discarding recording")
            return ""
        
        # Process audio
        audio_flat = audio_data.flatten()
        max_vol = np.max(np.abs(audio_flat))
        rms = np.sqrt(np.mean(audio_flat**2))
        
        print(f"[STT] 📊 Audio stats - Max: {max_vol:.4f}, RMS: {rms:.4f}")
        
        # Check if audio was captured
        if max_vol < 0.001:
            print("[STT] ⚠️  No audio detected (too quiet)")
            return ""
        
        # Normalize audio for better Whisper performance
        if max_vol > 0:
            audio_flat = audio_flat / max_vol
        
        # Transcribe with Whisper
        print("[STT] 🔄 Transcribing...")
        result = whisper_model.transcribe(
            audio_flat,
            fp16=False,
            language="en"
        )
        
        text = result["text"].strip()
        
        if not text:
            print("[STT] ⚠️  No speech detected")
            return ""
        
        # Check for TTS echo using smart detection
        text_lower = text.lower()
        if is_tts_echo(text_lower, max_vol):
            print(f"[STT] 🔇 Filtered TTS echo: '{text}' (level: {max_vol:.4f})")
            return ""
        
        # Valid speech detected
        print(f"[STT] ✅ Heard: '{text}' (level: {max_vol:.4f})")
        transcribe_speech(text)
        return text
            
    except Exception as e:
        print(f"[STT] ❌ Error: {e}")
        return ""


def audio_listener(hotword="watch my room", coldword="stop watching"):
    """
    Continuous background listener for hotword detection.
    Listens for activation/deactivation commands.
    
    Args:
        hotword: Phrase to activate guard mode
        coldword: Phrase to deactivate guard mode
    """
    if not whisper_model:
        print("[STT] ❌ Whisper not loaded!")
        return
    
    print("[STT] 🎙️  Continuous listener started")
    print(f"[STT] 🔑 Hotword: '{hotword}' (activates guard)")
    print(f"[STT] 🔑 Coldword: '{coldword}' (deactivates guard)")
    print(f"[STT] 🎚️  VAD Threshold: {VAD_THRESHOLD}")
    print()
    
    while True:
        # Pause if intruder mode is active
        if state.intruder:
            time.sleep(1)
            continue
        
        # Wait if TTS is playing
        if state.tts_playing:
            time.sleep(0.1)
            continue
        
        try:
            # Record a chunk
            audio_data = sd.rec(
                int(CHUNK_DURATION * SAMPLE_RATE),
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype='float32'
            )
            sd.wait()
            
            # Check if TTS started during recording
            if state.tts_playing:
                print("[STT] ⏭️  Skipping chunk (TTS interference)")
                continue
            
            # Check audio level
            audio_flat = audio_data.flatten()
            max_vol = np.max(np.abs(audio_flat))
            
            # Skip if too quiet
            if max_vol < VAD_THRESHOLD:
                continue
            
            print(f"[STT] 🎧 Audio detected (level: {max_vol:.4f}), processing...")
            
            # Normalize
            if max_vol > 0:
                audio_flat = audio_flat / max_vol
            
            # Transcribe
            result = whisper_model.transcribe(
                audio_flat,
                fp16=False,
                language="en"
            )
            
            text = result["text"].strip()
            
            if not text:
                continue
            
            text_lower = text.lower()
            
            # Filter TTS echoes using smart detection
            if is_tts_echo(text_lower, max_vol):
                print(f"[STT] 🔇 Filtered TTS echo: '{text}'")
                continue
            
            print(f"[STT] 💬 You said: '{text}'")
            
            # Update state
            with state.lock:
                state.current_text = text
            
            # Log transcription
            transcribe_speech(text)
            
            # Check for hotwords
            if hotword.lower() in text_lower:
                with state.lock:
                    state.guard_status = True
                print("[STT] 🔒 ═══════════════════════════════════")
                print("[STT] 🔒 GUARD MODE ACTIVATED!")
                print("[STT] 🔒 ═══════════════════════════════════")
                
            elif coldword.lower() in text_lower:
                with state.lock:
                    state.guard_status = False
                print("[STT] 🛑 ═══════════════════════════════════")
                print("[STT] 🛑 GUARD MODE DEACTIVATED")
                print("[STT] 🛑 ═══════════════════════════════════")
                
        except KeyboardInterrupt:
            print("\n[STT] 👋 Stopping listener...")
            break
        except Exception as e:
            print(f"[STT] ⚠️  Error in listener: {e}")
            time.sleep(1)


def test_microphone():
    """Quick microphone test for debugging."""
    print("\n[TEST] 🎤 Microphone Test (3 seconds)")
    print("[TEST] Speak now...")
    
    audio = sd.rec(
        int(3 * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype='float32'
    )
    sd.wait()
    
    max_vol = np.max(np.abs(audio))
    rms = np.sqrt(np.mean(audio**2))
    
    print(f"[TEST] Max volume: {max_vol:.6f}")
    print(f"[TEST] RMS level: {rms:.6f}")
    print(f"[TEST] Current VAD threshold: {VAD_THRESHOLD:.6f}")
    
    if max_vol < 0.001:
        print("[TEST] ❌ No audio detected - check microphone!")
        return False
    elif max_vol < VAD_THRESHOLD:
        print(f"[TEST] ⚠️  Audio below threshold - you may have issues")
        print(f"[TEST] 💡 Consider lowering VAD_THRESHOLD to {max_vol * 0.8:.4f}")
        return True
    else:
        print("[TEST] ✅ Microphone working well!")
        return True


if __name__ == "__main__":
    """Test mode - run STT.py directly to test functionality"""
    print("\n" + "="*60)
    print("STT MODULE - TEST MODE")
    print("="*60)
    
    # Test microphone
    if test_microphone():
        print("\n" + "="*60)
        input("Press Enter to test listen_once()...")
        
        # Test listen_once
        print("\n[TEST] Testing listen_once (5 seconds)...")
        result = listen_once(5)
        print(f"\n[TEST] Result: '{result}'")
        
        print("\n" + "="*60)
        choice = input("Test continuous listener? (y/n): ")
        
        if choice.lower() == 'y':
            print("\n[TEST] Starting continuous listener...")
            print("[TEST] Say 'watch my room' or 'stop watching'")
            print("[TEST] Press Ctrl+C to stop")
            audio_listener()
    
    print("\n[TEST] Tests complete!")