import sounddevice as sd
import numpy as np

print("=== Checking Headphone Device Capabilities ===\n")

# Check all headphone devices
headphone_devices = [
    (4, "MME Headphones"),
    (10, "DirectSound Headphones"),
    (13, "WASAPI Headphones")
]

for device_id, name in headphone_devices:
    print(f"\n{name} (Device {device_id}):")
    try:
        info = sd.query_devices(device_id)
        print(f"  Default sample rate: {info['default_samplerate']}")
        print(f"  Max output channels: {info['max_output_channels']}")
        
        # Try to check supported sample rates
        for sr in [44100, 48000, 96000, 192000]:
            try:
                sd.check_output_settings(device=device_id, samplerate=sr)
                print(f"  ✓ Supports {sr} Hz")
            except:
                print(f"  ✗ Does NOT support {sr} Hz")
    except Exception as e:
        print(f"  Error querying device: {e}")

print("\n\n=== Testing with device default settings ===\n")

# Record audio
print("Recording 2 seconds...")
recording = sd.rec(int(2 * 44100), samplerate=44100, channels=2, device=7, dtype='float32')
sd.wait()

# Try each device with its default sample rate
for device_id, name in headphone_devices:
    try:
        info = sd.query_devices(device_id)
        sr = int(info['default_samplerate'])
        print(f"\nTrying {name} at {sr} Hz...")
        
        # Resample if needed
        if sr != 44100:
            # Simple resampling
            factor = sr / 44100
            new_length = int(len(recording) * factor)
            import scipy.signal
            resampled = scipy.signal.resample(recording, new_length)
        else:
            resampled = recording
        
        # Try different dtypes
        for dtype in ['float32', 'int16', 'int32']:
            try:
                print(f"  Trying dtype {dtype}...")
                if dtype == 'int16':
                    audio = (resampled * 32767).astype(np.int16)
                elif dtype == 'int32':
                    audio = (resampled * 2147483647).astype(np.int32)
                else:
                    audio = resampled
                
                sd.play(audio, samplerate=sr, device=device_id)
                sd.wait()
                print(f"  ✓ SUCCESS with {dtype} at {sr} Hz!")
                break
            except Exception as e:
                print(f"  ✗ Failed with {dtype}: {str(e)[:50]}...")
                
    except Exception as e:
        print(f"Failed to test {name}: {e}")

print("\n\n=== Alternative: Test System Default ===")
print("Unplug headphones and press Enter to test laptop speakers...")
input()

try:
    print("Playing through default device...")
    sd.play(recording, samplerate=44100)
    sd.wait()
    print("SUCCESS with default device!")
except Exception as e:
    print(f"Failed: {e}")
