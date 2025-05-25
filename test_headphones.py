import sounddevice as sd
import numpy as np
import time

print("=== Headphone Audio Test ===\n")

# List devices
devices = sd.query_devices()
print("Your headphone devices:")
print(f"Input (Mic): Device 7 - {devices[7]['name']}")
print(f"Output (Headphones): Device 10 - {devices[10]['name']}")

print("\n1. Testing microphone levels...")
print("Speak into your headphone mic for 3 seconds...")

# Monitor input levels
def print_level(indata, frames, time, status):
    volume_norm = np.linalg.norm(indata) * 10
    print('|' * int(volume_norm))

with sd.InputStream(device=7, callback=print_level):
    sd.sleep(3000)

print("\n2. Recording test audio...")
print("Say something for 3 seconds...")

# Record
duration = 3
recording = sd.rec(int(duration * 44100), samplerate=44100, channels=2, 
                  device=7, dtype='float32')
sd.wait()

# Check if we got any audio
max_amplitude = np.max(np.abs(recording))
print(f"\nMax amplitude recorded: {max_amplitude}")
if max_amplitude < 0.001:
    print("WARNING: No audio detected! The microphone might not be working.")
else:
    print("Good! Audio was detected.")

print("\n3. Playing back through headphones...")
sd.play(recording, samplerate=44100, device=10)
sd.wait()

print("\n4. Testing with amplification...")
amplified = recording * 5  # Amplify by 5x
amplified = np.clip(amplified, -1, 1)  # Prevent clipping
print("Playing amplified version...")
sd.play(amplified, samplerate=44100, device=10)
sd.wait()

print("\n=== Test Complete ===")
print("\nIf you couldn't hear anything:")
print("1. Check Windows Sound Settings - make sure the headphone mic is enabled")
print("2. Right-click speaker icon > Sounds > Recording tab")
print("3. Find 'External Microphone' and check if it shows levels when you speak")
print("4. Make sure it's set as default device")
print("\nAlso check playback devices in the Playback tab")
