#!/usr/bin/env python3
"""
Audio Output Test Script
Tests if TTS audio is actually playing through your speakers
"""

import pyttsx3
import time
import sounddevice as sd
import numpy as np

print("\n" + "="*60)
print("🔊 AUDIO OUTPUT TEST")
print("="*60 + "\n")

# Test 1: List available audio devices
print("[TEST 1] Available Audio Devices:")
print("-" * 60)
devices = sd.query_devices()
for i, device in enumerate(devices):
    device_type = "🎤" if device['max_input_channels'] > 0 else ""
    device_type += "🔊" if device['max_output_channels'] > 0 else ""
    default = " (DEFAULT)" if i == sd.default.device[1] else ""
    print(f"{i}: {device_type} {device['name']}{default}")
print()

# Test 2: Play a beep sound to test speakers
print("[TEST 2] Testing speaker output with beep sound...")
print("You should hear a beep sound now...")

try:
    # Generate a 1-second beep at 440 Hz (A note)
    duration = 1  # seconds
    sample_rate = 44100
    frequency = 440  # Hz
    
    t = np.linspace(0, duration, int(sample_rate * duration))
    beep = 0.3 * np.sin(2 * np.pi * frequency * t)
    
    sd.play(beep, sample_rate)
    sd.wait()
    
    print("✅ Beep played successfully!")
    response = input("Did you HEAR the beep? (y/n): ").strip().lower()
    
    if response != 'y':
        print("⚠️  WARNING: You didn't hear the beep!")
        print("   Your speakers might be muted or disconnected.")
        print("   Check your system audio settings.")
except Exception as e:
    print(f"❌ Error playing beep: {e}")

print()

# Test 3: Test pyttsx3 TTS engine
print("[TEST 3] Testing pyttsx3 TTS engine...")
print("-" * 60)

try:
    engine = pyttsx3.init()
    
    # Get engine info
    print(f"Engine: {engine.getProperty('name') if hasattr(engine, 'getProperty') else 'Unknown'}")
    
    # List available voices
    voices = engine.getProperty('voices')
    print(f"\nAvailable voices: {len(voices)}")
    for i, voice in enumerate(voices[:5]):  # Show first 5
        print(f"  {i}: {voice.name}")
    
    # Set properties
    engine.setProperty('rate', 150)
    engine.setProperty('volume', 1.0)  # Max volume
    
    print("\n" + "="*60)
    print("🗣️  TTS TEST - You should hear speech now...")
    print("="*60)
    
    test_phrases = [
        "Testing one two three.",
        "Hello, this is a test of the text to speech system.",
        "Can you hear me clearly?",
        "This is your final warning."
    ]
    
    for i, phrase in enumerate(test_phrases, 1):
        print(f"\n[{i}] Speaking: '{phrase}'")
        print("    ⏳ Speaking...", end="", flush=True)
        
        engine.say(phrase)
        engine.runAndWait()
        
        print(" ✅ Done")
        time.sleep(0.5)
    
    print("\n" + "="*60)
    response = input("\nDid you HEAR all 4 phrases clearly? (y/n): ").strip().lower()
    
    if response == 'y':
        print("✅ TTS is working correctly!")
    else:
        print("⚠️  TTS audio issue detected!")
        print("\n🔧 TROUBLESHOOTING:")
        print("   1. Check system volume (increase to 100%)")
        print("   2. Check that correct audio output device is selected")
        print("   3. Try plugging in headphones/external speakers")
        print("   4. On macOS: System Preferences → Sound → Output")
        print("   5. On Linux: Check pulseaudio/alsa settings")
        print("   6. Try: pip install --upgrade pyttsx3")
        
except Exception as e:
    print(f"❌ Error initializing TTS: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("🏁 AUDIO TEST COMPLETE")
print("="*60)

# Test 4: Volume test
print("\n[TEST 4] Volume Level Test")
print("This will play the same phrase at different volumes...")

try:
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)
    
    for volume in [0.3, 0.5, 0.7, 1.0]:
        engine.setProperty('volume', volume)
        print(f"\n🔊 Volume: {int(volume*100)}%")
        engine.say(f"This is at {int(volume*100)} percent volume")
        engine.runAndWait()
        time.sleep(0.5)
        
except Exception as e:
    print(f"❌ Volume test failed: {e}")

print("\n" + "="*60)
print("If you heard all tests clearly, your TTS is working fine!")
print("If not, there's an audio configuration issue on your system.")
print("="*60 + "\n")