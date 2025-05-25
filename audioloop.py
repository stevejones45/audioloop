import dearpygui.dearpygui as dpg
import sounddevice as sd
import numpy as np
import threading
import queue
import wave
import os

class MultiTrackLooper:
    def __init__(self):
        # Get host APIs and devices info
        hostapis = sd.query_hostapis()
        devices = sd.query_devices()
        
        # Look for headphone mic and output in DirectSound or WASAPI
        input_device_id = None
        output_device_id = None
        
        # First try to find DirectSound devices (usually more stable)
        for i, device in enumerate(devices):
            hostapi_idx = device['hostapi']
            hostapi_name = hostapis[hostapi_idx]['name']
            
            if 'DirectSound' in hostapi_name:
                if device['max_input_channels'] > 0 and 'External Microphone' in device['name']:
                    input_device_id = i
                    print(f"Found DirectSound input: {device['name']} (device {i})")
                elif device['max_output_channels'] > 0 and 'Headphones' in device['name']:
                    output_device_id = i
                    print(f"Found DirectSound output: {device['name']} (device {i})")
        
        # If no external mic found, look for any microphone in DirectSound
        if input_device_id is None:
            for i, device in enumerate(devices):
                hostapi_idx = device['hostapi']
                hostapi_name = hostapis[hostapi_idx]['name']
                
                if 'DirectSound' in hostapi_name and device['max_input_channels'] > 0:
                    if 'Microphone' in device['name']:
                        input_device_id = i
                        print(f"Found DirectSound input: {device['name']} (device {i})")
                        break
        
        # If still not found, fall back to defaults
        if input_device_id is None:
            input_device_id = sd.default.device[0]
            print(f"Using default input device: {devices[input_device_id]['name']}")
        if output_device_id is None:
            output_device_id = sd.default.device[1]
            print(f"Using default output device: {devices[output_device_id]['name']}")
            
        self.sample_rate = 44100
        self.channels = 2
        
        self.dtype = 'float32'  # Use float32 which is more universally supported
        self.recording = False
        self.playing = False
        self.current_track = 0
        self.master_length = None
        
        # 4 tracks, each can hold audio data
        self.tracks = [None, None, None, None]
        self.track_enabled = [True, True, True, True]
        self.track_volumes = [1.0, 1.0, 1.0, 1.0]
        
        # Recording
        self.audio_queue = queue.Queue()
        self.audio_buffer = []
        self.playback_position = 0
        
        # Audio streams - don't create them until needed
        self.input_stream = None
        self.output_stream = None
        
        # Store device IDs for later use
        self.input_device_id = input_device_id
        self.output_device_id = output_device_id
        
        print(f"Audio devices ready - Input: {input_device_id}, Output: {output_device_id}")
    
    def audio_input_callback(self, indata, frames, time, status):
        """Callback for audio input"""
        if status:
            print(f"Input status: {status}")
        if self.recording:
            self.audio_queue.put(indata.copy())
    
    def audio_output_callback(self, outdata, frames, time, status):
        """Mix and play all enabled tracks"""
        if status:
            print(f"Output status: {status}")
            
        if not self.playing or self.master_length is None:
            outdata.fill(0)
            return
        
        # Create mix buffer
        mix = np.zeros_like(outdata)
        
        # Mix all enabled tracks
        for i, track in enumerate(self.tracks):
            if track is not None and self.track_enabled[i]:
                # Calculate position in loop
                start_pos = self.playback_position % self.master_length
                end_pos = min(start_pos + frames, self.master_length)
                samples_to_copy = end_pos - start_pos
                
                # Add track to mix with volume
                mix[:samples_to_copy] += track[start_pos:end_pos] * self.track_volumes[i]
                
                # Handle loop wrap
                if samples_to_copy < frames:
                    remaining = frames - samples_to_copy
                    mix[samples_to_copy:] += track[:remaining] * self.track_volumes[i]
        
        # Clip to prevent distortion
        outdata[:] = np.clip(mix, -1.0, 1.0)
        
        self.playback_position += frames
    
    def start_recording(self, track_num):
        """Start recording to specified track"""
        if self.recording:
            return
        
        self.current_track = track_num
        self.recording = True
        self.audio_buffer = []
        
        # Recreate input stream if needed
        try:
            if self.input_stream:
                self.input_stream.close()
            
            self.input_stream = sd.InputStream(
                device=self.input_device_id,
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
                callback=self.audio_input_callback,
                latency='low'
            )
            self.input_stream.start()
            print(f"Recording track {track_num + 1}")
        except Exception as e:
            print(f"Error starting recording: {e}")
            self.recording = False
            return
        
        # Start recording thread
        threading.Thread(target=self._record_thread, daemon=True).start()
    
    def _record_thread(self):
        """Thread for handling recording"""
        while self.recording:
            try:
                data = self.audio_queue.get(timeout=0.1)
                self.audio_buffer.append(data)
            except queue.Empty:
                continue
    
    def stop_recording(self):
        """Stop recording and save to current track"""
        if not self.recording:
            return
        
        self.recording = False
        
        # Stop and close input stream
        try:
            if self.input_stream:
                self.input_stream.stop()
                self.input_stream.close()
                self.input_stream = None
            print("Recording stopped")
        except Exception as e:
            print(f"Error stopping recording: {e}")
        
        # Clear the queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
        
        if self.audio_buffer:
            recorded_audio = np.concatenate(self.audio_buffer, axis=0)
            
            # If this is the first track, set master length
            if self.master_length is None:
                self.master_length = len(recorded_audio)
                self.tracks[self.current_track] = recorded_audio
            else:
                # Trim or loop to match master length
                if len(recorded_audio) > self.master_length:
                    self.tracks[self.current_track] = recorded_audio[:self.master_length]
                else:
                    # Loop the recording to fill master length
                    loops_needed = self.master_length // len(recorded_audio) + 1
                    looped = np.tile(recorded_audio, (loops_needed, 1))
                    self.tracks[self.current_track] = looped[:self.master_length]
            
            self.update_track_display(self.current_track)
    
    def toggle_playback(self):
        """Toggle master playback"""
        if self.master_length is None:
            print("No tracks recorded yet")
            return
            
        self.playing = not self.playing
        if self.playing:
            self.playback_position = 0
            # Recreate output stream if needed
            try:
                if self.output_stream:
                    self.output_stream.close()
                
                self.output_stream = sd.OutputStream(
                    device=self.output_device_id,
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype=self.dtype,
                    callback=self.audio_output_callback,
                    latency='low'
                )
                self.output_stream.start()
                print("Playback started")
            except Exception as e:
                print(f"Error starting playback: {e}")
                self.playing = False
        else:
            # Stop and close stream
            try:
                if self.output_stream:
                    self.output_stream.stop()
                    self.output_stream.close()
                    self.output_stream = None
                print("Playback stopped")
            except Exception as e:
                print(f"Error stopping playback: {e}")
    
    def clear_track(self, track_num):
        """Clear a specific track"""
        self.tracks[track_num] = None
        self.update_track_display(track_num)
        
        # If all tracks cleared, reset master length
        if all(track is None for track in self.tracks):
            self.master_length = None
    
    def toggle_track(self, track_num):
        """Toggle track on/off"""
        self.track_enabled[track_num] = not self.track_enabled[track_num]
    
    def set_track_volume(self, track_num, volume):
        """Set track volume (0.0 to 1.0)"""
        self.track_volumes[track_num] = volume
    
    def update_track_display(self, track_num):
        """Update waveform display for a track"""
        if self.tracks[track_num] is None:
            dpg.set_value(f"track_{track_num}_series", [[], []])
            return
        
        # Downsample for display
        downsample = 500
        display_data = self.tracks[track_num][::downsample, 0]  # Use left channel
        
        # Create time axis
        time_axis = np.arange(len(display_data)) * downsample / self.sample_rate
        
        # Update plot
        dpg.set_value(f"track_{track_num}_series", [time_axis.tolist(), display_data.tolist()])
    
    def save_mix(self, filename):
        """Save the current mix to a WAV file"""
        if self.master_length is None:
            return None
        
        # Create mix
        mix = np.zeros((self.master_length, self.channels), dtype=np.float32)
        
        for i, track in enumerate(self.tracks):
            if track is not None and self.track_enabled[i]:
                mix += track * self.track_volumes[i]
        
        # Clip and convert to int16 for WAV
        mix = np.clip(mix, -1.0, 1.0)
        mix_int16 = (mix * 32767).astype(np.int16)
        
        # Save
        if not filename.endswith('.wav'):
            filename += '.wav'
        
        filepath = os.path.join(os.path.dirname(__file__), filename)
        
        with wave.open(filepath, 'wb') as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(mix_int16.tobytes())
        
        return filepath

# Create app instance 
try:
    app = MultiTrackLooper()
except Exception as e:
    print(f"Failed to initialize audio: {e}")
    print("\nTroubleshooting:")
    print("1. Make sure no other audio applications are using the device")
    print("2. Try closing and reopening the terminal")
    print("3. Check Windows sound settings")
    print("\nAvailable devices:")
    print(sd.query_devices())
    raise

# GUI callbacks
def record_button_callback(sender, app_data, user_data):
    track_num = user_data
    if app.recording and app.current_track == track_num:
        app.stop_recording()
        dpg.set_item_label(f"record_btn_{track_num}", f"Record Track {track_num + 1}")
        dpg.bind_item_theme(f"record_btn_{track_num}", "button_theme_default")
    elif not app.recording:
        app.start_recording(track_num)
        dpg.set_item_label(f"record_btn_{track_num}", "Stop Recording")
        dpg.bind_item_theme(f"record_btn_{track_num}", "button_theme_recording")

def play_button_callback():
    app.toggle_playback()
    if app.playing:
        dpg.set_item_label("play_btn", "Stop All")
        dpg.bind_item_theme("play_btn", "button_theme_playing")
    else:
        dpg.set_item_label("play_btn", "Play All")
        dpg.bind_item_theme("play_btn", "button_theme_default")

def mute_callback(sender, app_data, user_data):
    track_num = user_data
    app.toggle_track(track_num)
    if app.track_enabled[track_num]:
        dpg.set_item_label(f"mute_btn_{track_num}", "Mute")
        dpg.bind_item_theme(f"mute_btn_{track_num}", "button_theme_default")
    else:
        dpg.set_item_label(f"mute_btn_{track_num}", "Muted")
        dpg.bind_item_theme(f"mute_btn_{track_num}", "button_theme_muted")

def clear_callback(sender, app_data, user_data):
    track_num = user_data
    app.clear_track(track_num)

def volume_callback(sender, app_data, user_data):
    track_num = user_data
    volume = app_data / 100.0  # Convert from 0-100 to 0-1
    app.set_track_volume(track_num, volume)

def save_callback():
    filename = dpg.get_value("filename_input")
    if filename:
        filepath = app.save_mix(filename)
        if filepath:
            dpg.set_value("status_text", f"Saved mix to: {filepath}")
        else:
            dpg.set_value("status_text", "No tracks recorded yet!")

# Create GUI
dpg.create_context()

# Create button themes for different states
with dpg.theme(tag="button_theme_default"):
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (51, 51, 55))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (71, 71, 75))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (91, 91, 95))

with dpg.theme(tag="button_theme_recording"):
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (150, 0, 0))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (170, 20, 20))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (190, 40, 40))

with dpg.theme(tag="button_theme_playing"):
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (0, 150, 0))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (20, 170, 20))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (40, 190, 40))

with dpg.theme(tag="button_theme_muted"):
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (150, 150, 0))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (170, 170, 20))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (190, 190, 40))

# Custom theme for track colors
with dpg.theme() as track_theme:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 5)

with dpg.window(label="4-Track Looper", tag="main_window"):
    # Master controls
    dpg.add_text("Master Controls", color=(255, 255, 255))
    with dpg.group(horizontal=True):
        dpg.add_button(label="Play All", tag="play_btn", callback=play_button_callback,
                      width=150, height=40)
        dpg.add_text("   Loop Length: ", tag="loop_length_text")
    
    dpg.add_separator()
    
    # Create 4 tracks
    colors = [(255, 100, 100), (100, 255, 100), (100, 100, 255), (255, 255, 100)]
    
    for i in range(4):
        dpg.add_text(f"Track {i + 1}", color=colors[i])
        
        with dpg.group(horizontal=True):
            # Track controls
            dpg.add_button(label=f"Record Track {i + 1}", tag=f"record_btn_{i}",
                          callback=record_button_callback, user_data=i,
                          width=120, height=30)
            dpg.add_button(label="Mute", tag=f"mute_btn_{i}",
                          callback=mute_callback, user_data=i,
                          width=60, height=30)
            dpg.add_button(label="Clear", tag=f"clear_btn_{i}",
                          callback=clear_callback, user_data=i,
                          width=60, height=30)
            dpg.add_text("Volume:")
            dpg.add_slider_float(tag=f"volume_{i}", min_value=0, max_value=100,
                               default_value=100, callback=volume_callback,
                               user_data=i, width=150)
        
        # Waveform display
        with dpg.plot(height=80, width=-1, no_title=True):
            x_axis = dpg.add_plot_axis(dpg.mvXAxis, no_tick_labels=True)
            y_axis = dpg.add_plot_axis(dpg.mvYAxis, no_tick_labels=True)
            dpg.set_axis_limits(y_axis, -1, 1)
            dpg.add_line_series([], [], parent=y_axis, tag=f"track_{i}_series")
        
        dpg.add_spacer(height=5)
    
    # Save controls
    dpg.add_separator()
    dpg.add_text("Save Mix:")
    with dpg.group(horizontal=True):
        dpg.add_input_text(tag="filename_input", hint="Enter filename", width=300)
        dpg.add_button(label="Save Mix", callback=save_callback, width=100)
    
    dpg.add_text("", tag="status_text")
    
    # Audio info
    dpg.add_text(f"Audio: {app.sample_rate}Hz, {app.channels}ch", color=(128, 128, 128))

# Update loop length display
def update_loop_length():
    if app.master_length:
        length_seconds = app.master_length / app.sample_rate
        dpg.set_value("loop_length_text", f"   Loop Length: {length_seconds:.2f} seconds")
    else:
        dpg.set_value("loop_length_text", "   Loop Length: Not set")

# Setup Dear PyGui
dpg.create_viewport(title="4-Track Looper", width=800, height=600)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_primary_window("main_window", True)

# Update loop timer
def update_timer():
    while dpg.is_dearpygui_running():
        update_loop_length()
        dpg.render_dearpygui_frame()

# Start GUI
dpg.start_dearpygui()

# Cleanup
if app.input_stream:
    app.input_stream.close()
if app.output_stream:
    app.output_stream.close()
dpg.destroy_context()
