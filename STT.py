import sounddevice as sd
import numpy as np
import whisper
import datetime
from state import state
import time

# -------------------------
# Configuration
# -------------------------
SAMPLE_RATE = 16000
VAD_THRESHOLD = 0.015  # Voice activity detection (increased from 0.01)
LISTEN_DURATION = 5  # seconds for listen_once
CHUNK_DURATION = 5  # seconds for continuous listening
TTS_BUFFER_TIME = 2.0  # Extra wait time after TTS finishes (increased from 1.0)

print("[STT] Loading Whisper model...")
try:
    whisper_model = whisper.load_model("base")  # 'tiny' for speed, 'base' for accuracy
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


def wait_for_tts():
    """Wait until TTS is completely finished."""
    while state.tts_playing:
        time.sleep(0.1)
    # Extra buffer time after TTS finishes
    time.sleep(TTS_BUFFER_TIME)


def listen_once(duration=LISTEN_DURATION):
    """
    Record for specified duration and return transcription.
    Used during guard interactions with visitor.
    
    Returns:
        str: Transcribed text or empty string
    """
    # CRITICAL: Wait for TTS to completely finish
    wait_for_tts()
    
    if not whisper_model:
        print("[STT] ❌ Whisper not loaded!")
        return ""
    
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
        
        # Double check TTS isn't still playing somehow
        if state.tts_playing:
            print("[STT] ⚠️  TTS still playing, skipping this recording")
            return ""
        
        # Process audio
        audio_flat = audio_data.flatten()
        max_vol = np.max(np.abs(audio_flat))
        
        # Check if audio was captured
        if max_vol < 0.001:
            print("[STT] ⚠️  No audio detected")
            return ""
        
        # Normalize audio
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
        
        if text:
            # Filter out common TTS phrases that might leak through
            tts_phrases = [
                "hello this is a private room",
                "you must leave",
                "this room is off-limits",
                "alarm",
                "security",
                "final warning"
            ]
            
            text_lower = text.lower()
            is_tts_echo = any(phrase in text_lower for phrase in tts_phrases)
            
            if is_tts_echo and max_vol < 0.02:
                print(f"[STT] 🔇 Filtered TTS echo: '{text}'")
                return ""
            
            print(f"[STT] ✅ Heard: '{text}'")
            transcribe_speech(text)
            return text
        else:
            print("[STT] ⚠️  No speech detected")
            return ""
            
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
    
    print("[STT] 🎙️ Continuous listener started")
    print(f"[STT] 🔑 Hotword: '{hotword}' (activates guard)")
    print(f"[STT] 🔑 Coldword: '{coldword}' (deactivates guard)")
    print(f"[STT] 🎚️  VAD Threshold: {VAD_THRESHOLD}")
    print()
    
    while True:
        # Pause if intruder mode is active
        if state.intruder:
            time.sleep(1)
            continue
        
        # CRITICAL: Wait for TTS to finish completely
        if state.tts_playing:
            time.sleep(0.1)
            continue
        
        # Extra safety: wait a bit after TTS stops
        wait_for_tts()
        
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
                print("[STT] ⏭️  Skipping chunk (TTS started)")
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
            
            text = result["text"].strip().lower()
            
            if not text:
                continue
            
            # Filter out TTS echoes
            tts_phrases = [
                "alarm",
                "security breach",
                "private room",
                "you must leave",
                "final warning",
                "authorities"
            ]
            
            is_tts_echo = any(phrase in text for phrase in tts_phrases)
            
            if is_tts_echo and max_vol < 0.03:
                print(f"[STT] 🔇 Filtered TTS echo: '{text}'")
                continue
            
            print(f"[STT] 💬 You said: '{text}'")
            
            # Update state
            with state.lock:
                state.current_text = text
            
            # Log transcription
            transcribe_speech(text)
            
            # Check for hotwords
            if hotword.lower() in text:
                with state.lock:
                    state.guard_status = True
                print("[STT] 🔒 ═══════════════════════════════════")
                print("[STT] 🔒 GUARD MODE ACTIVATED!")
                print("[STT] 🔒 ═══════════════════════════════════")
                
            elif coldword.lower() in text:
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
    
    if max_vol < 0.001:
        print("[TEST] ❌ No audio detected - check microphone!")
        return False
    elif max_vol < 0.01:
        print("[TEST] ⚠️  Audio quiet - consider lowering VAD_THRESHOLD")
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