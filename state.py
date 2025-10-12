import threading

class GuardState:
    """
    Shared state for the AI Room Guard system.
    Thread-safe using locks.
    """
    
    def __init__(self):
        self.lock = threading.Lock()
        
        # Core states
        self.guard_status = False  # True = guard mode active
        self.intruder = False  # True = intruder detected by camera
        self.camera_active = True  # True = camera should keep monitoring
        self.tts_playing = False  # True = TTS is speaking
        
        # Audio/text states
        self.current_text = ""  # Last transcribed text
        self.last_tts_text = ""  # Last TTS output (for echo detection)
        
        # Speaker recognition states
        self.current_speaker = None  # Name of current speaker
        self.speaker_is_trusted = False  # Is current speaker trusted?
        self.last_speaker_check = 0  # Timestamp of last speaker check
        
        # System stats
        self.total_intrusions = 0
        self.total_activations = 0
        self.intruder_confirmed = False  # True = intruder confirmed, stop camera
    
    def set_guard_active(self, active: bool):
        """Thread-safe guard status setter."""
        with self.lock:
            self.guard_status = active
            if active:
                self.total_activations += 1
                self.camera_active = True  # Resume camera when guard activates
    
    def set_intruder(self, detected: bool):
        """Thread-safe intruder status setter."""
        with self.lock:
            self.intruder = detected
            if detected:
                self.total_intrusions += 1
    
    def confirm_intruder(self):
        """Mark intruder as confirmed and stop camera."""
        with self.lock:
            self.intruder_confirmed = True
            self.camera_active = False  # Stop camera
            print("[STATE] 🚨 Intruder confirmed - Camera paused")
    
    def resume_camera(self):
        """Resume camera monitoring after alarm."""
        with self.lock:
            self.camera_active = True
            self.intruder_confirmed = False
            print("[STATE] 🎥 Camera monitoring resumed")
    
    def set_speaker(self, name: str, is_trusted: bool):
        """Thread-safe speaker info setter."""
        with self.lock:
            self.current_speaker = name
            self.speaker_is_trusted = is_trusted
            import time
            self.last_speaker_check = time.time()
    
    def get_status(self):
        """Get current system status (thread-safe)."""
        with self.lock:
            return {
                'guard_active': self.guard_status,
                'intruder_detected': self.intruder,
                'intruder_confirmed': self.intruder_confirmed,
                'camera_active': self.camera_active,
                'tts_playing': self.tts_playing,
                'current_speaker': self.current_speaker,
                'speaker_trusted': self.speaker_is_trusted,
                'total_intrusions': self.total_intrusions,
                'total_activations': self.total_activations
            }
    
    def reset(self):
        """Reset state to initial values."""
        with self.lock:
            self.guard_status = False
            self.intruder = False
            self.intruder_confirmed = False
            self.camera_active = True
            self.tts_playing = False
            self.current_text = ""
            self.current_speaker = None
            self.speaker_is_trusted = False


# Single shared instance
state = GuardState()