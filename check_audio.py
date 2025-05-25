import sounddevice as sd

# List all audio devices
print("Available audio devices:")
print(sd.query_devices())

# Show default input device
default_input = sd.query_devices(kind='input')
print(f"\nDefault input device: {default_input['name']}")
print(f"Max input channels: {default_input['max_input_channels']}")
