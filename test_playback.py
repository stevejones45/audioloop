import sounddevice as sd
import numpy as np
import time

print("=== Testing Different Audio APIs ===\n")

# Record some audio first
print("Recording 2 seconds of audio from your headphone mic...")
recording = sd.rec(int(2 * 44100), samplerate=44100, channels=2, 
                  device=7, dtype='float32')  # DirectSound input works fine
sd.wait()
print(f"Recorded successfully. Max amplitude: {np.max(np.abs(recording))}")

# Try different output devices
print("\nTrying different playback methods:\n")

# Method 1: WASAPI output
try:
    print("1. Trying WASAPI headphones (device 13)...")
    sd.play(recording, samplerate=44100, device=13)
    sd.wait()
    print("   SUCCESS with WASAPI!")
except Exception as e:
    print(f"   Failed: {e}")

# Method 2: Default output
try:
    print("\n2. Trying default output device...")
    sd.default.device = [7, None]  # Keep input as 7, use default output
    sd.play(recording, samplerate=44100)
    sd.wait()
    print("   SUCCESS with default output!")
except Exception as e:
    print(f"   Failed: {e}")

# Method 3: MME output
try:
    print("\n3. Trying MME headphones (device 4)...")
    sd.play(recording, samplerate=44100, device=4)
    sd.wait()
    print("   SUCCESS with MME!")
except Exception as e:
    print(f"   Failed: {e}")

# Method 4: Create a new stream approach
try:
    print("\n4. Trying fresh DirectSound stream...")
    with sd.OutputStream(device=10, samplerate=44100, channels=2, dtype='float32') as stream:
        stream.write(recording)
    print("   SUCCESS with fresh DirectSound stream!")
except Exception as e:
    print(f"   Failed: {e}")

print("\n=== Results ===")
print("Check which method(s) worked above.")
print("We'll use the working method in the main app.")
