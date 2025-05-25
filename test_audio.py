import sounddevice as sd
import numpy as np

print("Testing audio devices...\n")

# Get host APIs info
hostapis = sd.query_hostapis()
print("Available host APIs:")
for i, api in enumerate(hostapis):
    print(f"  {i}: {api['name']}")

print("\n" + "="*50 + "\n")

# Find all DirectSound and WASAPI devices
devices = sd.query_devices()
ds_inputs = []
ds_outputs = []
wasapi_inputs = []
wasapi_outputs = []

for i, device in enumerate(devices):
    # Get the host API name for this device
    hostapi_idx = device['hostapi']
    hostapi_name = hostapis[hostapi_idx]['name']
    
    if 'DirectSound' in hostapi_name:
        if device['max_input_channels'] > 0:
            ds_inputs.append((i, device['name']))
        if device['max_output_channels'] > 0:
            ds_outputs.append((i, device['name']))
    elif 'WASAPI' in hostapi_name:
        if device['max_input_channels'] > 0:
            wasapi_inputs.append((i, device['name']))
        if device['max_output_channels'] > 0:
            wasapi_outputs.append((i, device['name']))

print("DirectSound Input Devices:")
for idx, name in ds_inputs:
    print(f"  {idx}: {name}")

print("\nDirectSound Output Devices:")
for idx, name in ds_outputs:
    print(f"  {idx}: {name}")

print("\nWASAPI Input Devices:")
for idx, name in wasapi_inputs:
    print(f"  {idx}: {name}")

print("\nWASAPI Output Devices:")
for idx, name in wasapi_outputs:
    print(f"  {idx}: {name}")

# Test recording with DirectSound
print("\n\nTesting DirectSound recording...")
try:
    # Find External Microphone in DirectSound
    ext_mic_ds = None
    headphones_ds = None
    
    for idx, name in ds_inputs:
        if 'External Microphone' in name:
            ext_mic_ds = idx
            break
    
    for idx, name in ds_outputs:
        if 'Headphones' in name:
            headphones_ds = idx
            break
    
    if ext_mic_ds and headphones_ds:
        print(f"Using input device {ext_mic_ds} and output device {headphones_ds}")
        
        # Test recording
        duration = 2  # seconds
        recording = sd.rec(int(duration * 44100), samplerate=44100, channels=2, 
                          device=ext_mic_ds, dtype='float32')
        sd.wait()
        print("Recording successful!")
        
        # Test playback
        sd.play(recording, samplerate=44100, device=headphones_ds)
        sd.wait()
        print("Playback successful!")
    else:
        print("Could not find suitable DirectSound devices")
        
except Exception as e:
    print(f"DirectSound test failed: {e}")
    
# Test with WASAPI if DirectSound failed
print("\n\nTesting WASAPI...")
try:
    # Find devices in WASAPI
    ext_mic_wasapi = None
    headphones_wasapi = None
    
    for idx, name in wasapi_inputs:
        if 'External Microphone' in name or 'Microphone' in name:
            ext_mic_wasapi = idx
            break
    
    for idx, name in wasapi_outputs:
        if 'Headphones' in name:
            headphones_wasapi = idx
            break
    
    if ext_mic_wasapi and headphones_wasapi:
        print(f"Using input device {ext_mic_wasapi} and output device {headphones_wasapi}")
        
        # Test recording
        duration = 2  # seconds
        recording = sd.rec(int(duration * 44100), samplerate=44100, channels=2, 
                          device=ext_mic_wasapi, dtype='float32')
        sd.wait()
        print("Recording successful!")
        
        # Test playback
        sd.play(recording, samplerate=44100, device=headphones_wasapi)
        sd.wait()
        print("Playback successful!")
    else:
        print("Could not find suitable WASAPI devices")
        
except Exception as e:
    print(f"WASAPI test failed: {e}")

print("\n\nRecommended device IDs for your setup:")
if ext_mic_ds and headphones_ds:
    print(f"DirectSound: Input={ext_mic_ds}, Output={headphones_ds}")
elif ext_mic_wasapi and headphones_wasapi:
    print(f"WASAPI: Input={ext_mic_wasapi}, Output={headphones_wasapi}")
else:
    print("No suitable device combination found")
