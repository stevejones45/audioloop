import sounddevice as sd
import numpy as np
import time

print("=== ASIO4ALL Test ===\n")
print("ASIO4ALL (device 8) supports both input and output!")
print("This might be the solution for using headphones with mic.\n")

# First, let's test ASIO4ALL
try:
    print("1. Testing ASIO4ALL recording and playback...")
    
    # Test with ASIO - it's device 8 and supports both in/out
    asio_device = 8
    
    print(f"Recording 2 seconds with ASIO4ALL...")
    recording = sd.rec(int(2 * 44100), samplerate=44100, channels=2, 
                      device=asio_device, dtype='float32')
    sd.wait()
    print(f"Recorded! Max amplitude: {np.max(np.abs(recording))}")
    
    print("Playing back with ASIO4ALL...")
    sd.play(recording, samplerate=44100, device=asio_device)
    sd.wait()
    print("SUCCESS with ASIO4ALL!")
    
except Exception as e:
    print(f"ASIO4ALL failed: {e}")
    print("\nASIO4ALL might need configuration:")
    print("1. Make sure ASIO4ALL is installed")
    print("2. You might need to open ASIO4ALL control panel")
    print("3. Enable your headphone input/output in ASIO4ALL")

print("\n\n=== Dynamic Device Selection Test ===")
print("This will find the best available devices...\n")

def find_best_devices():
    """Find the best input and output devices currently available"""
    devices = sd.query_devices()
    
    # Look for external mic first, then any mic
    input_device = None
    for i, dev in enumerate(devices):
        if dev['max_input_channels'] > 0:
            if 'External' in dev['name']:
                input_device = i
                break
    
    if input_device is None:
        # Fallback to any available input
        for i, dev in enumerate(devices):
            if dev['max_input_channels'] > 0 and 'Microphone' in dev['name']:
                input_device = i
                break
    
    # Look for headphones first, then speakers
    output_device = None
    for i, dev in enumerate(devices):
        if dev['max_output_channels'] > 0:
            if 'Headphones' in dev['name'] and 'DirectSound' in str(devices[i]):
                output_device = i
                break
    
    if output_device is None:
        # Fallback to speakers
        for i, dev in enumerate(devices):
            if dev['max_output_channels'] > 0 and 'Speakers' in dev['name']:
                output_device = i
                break
    
    return input_device, output_device

# Test dynamic selection
input_dev, output_dev = find_best_devices()
print(f"Found input device: {input_dev} - {sd.query_devices(input_dev)['name'] if input_dev else 'None'}")
print(f"Found output device: {output_dev} - {sd.query_devices(output_dev)['name'] if output_dev else 'None'}")

if input_dev and output_dev:
    try:
        print("\nTesting dynamic devices...")
        recording = sd.rec(int(2 * 44100), samplerate=44100, channels=2, 
                          device=input_dev, dtype='float32')
        sd.wait()
        print(f"Recorded! Max amplitude: {np.max(np.abs(recording))}")
        
        # Try speakers instead of headphones
        sd.play(recording, samplerate=44100, device=output_dev)
        sd.wait()
        print("Playback complete!")
    except Exception as e:
        print(f"Dynamic device test failed: {e}")

print("\n\n=== Recommendation ===")
print("Based on the tests:")
print("1. ASIO4ALL might be your best option for headphone+mic")
print("2. Or use speakers for output while recording with headphone mic")
print("3. The app needs to dynamically detect available devices")
