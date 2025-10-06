import threading

class GuardState:
    def __init__(self):
        self.lock = threading.Lock()
        self.guard_status = False # from STT
        self.intruder = False # from camera output
        self.tts_playing = False #
        self.current_text = ""

# single shared instance
state = GuardState()
