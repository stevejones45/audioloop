import dearpygui.dearpygui as dpg
import sounddevice as sd
import numpy as np
import threading
import queue
import wave
import os

class MultiTrackLooper:
    def __init__(self):
        self.sample_rate = 44100
        self.channels = 2  # Stereo
        self.dtype = np.int16
        self.recording = False
        self.playing = False
        self.current_track = 0
        self.master_length = None  # Length of first recorded track
        
        # 4 tracks, each can hold audio data
        self.tracks = [None, None, None, None]
        self.track_enabled = [True, True, True, True]
        self.track_volumes = [1.0, 1.0, 1.0, 1.0]
        
        # Recording
        self.audio_queue = queue.Queue()
        self.audio_buffer = []
        self.playback_position = 0
        
        # Audio streams
        self.input_stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=self.dtype,
            callback=self.audio_input_callback
        )
        
        self.output_stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=self.dtype,
            callback=self.audio_output_callback
        )
        
    def audio_input_callback(self, indata, frames, time, status):
        """Callback for audio input"""
        if self.recording:
            self.audio_queue.put(indata.copy())
    
    def audio_output_callback(self, outdata, frames, time, status):
        """Mix and play all enabled tracks"""
        if not self.playing or self.master_length is None:
            outdata.fill(0)
            return
        
        # Create mix buffer
        mix = np.zeros_like(outdata, dtype=np.float32)
        
        # Mix all enabled tracks
        for i, track in enumerate(self.tracks):
            if track is not None and self.track_enabled[i]:
                # Calculate position in loop
                start_pos = self.playback_position % self.master_length
                end_pos = min(start_pos + frames, self.master_length)
                samples_to_copy = end_pos - start_pos
                
                # Add track to mix with volume
                track_float = track[start_pos:end_pos].astype(np.float32) / 32768.0
                mix[:samples_to_copy] += track_float * self.track_volumes[i]
                
                # Handle loop wrap
                if samples_to_copy < frames:
                    remaining = frames - samples_to_copy
                    track_float = track[:remaining].astype(np.float32) / 32768.0
                    mix[samples_to_copy:] += track_float * self.track_volumes[i]
        
        # Clip and convert back to int16
        mix = np.clip(mix, -1.0, 1.0)
        outdata[:] = (mix * 32768).astype(self.dtype)
        
        self.playback_position += frames
    
    def start_recording(self, track_num):
        """Start recording to specified track"""
        if self.recording:
            return
        
        self.current_track = track_num
        self.recording = True
        self.audio_buffer = []
        self.input_stream.start()
        
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
        self.input_stream.stop()
        
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
        self.playing = not self.playing
        if self.playing:
            self.playback_position = 0
            self.output_stream.start()
        else:
            self.output_stream.stop()
    
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
        normalized = display_data.astype(np.float32) / 32768.0
        
        # Create time axis
        time_axis = np.arange(len(normalized)) * downsample / self.sample_rate
        
        # Update plot
        dpg.set_value(f"track_{track_num}_series", [time_axis.tolist(), normalized.tolist()])
    
    def save_mix(self, filename):
        """Save the current mix to a WAV file"""
        if self.master_length is None:
            return None
        
        # Create mix
        mix = np.zeros((self.master_length, self.channels), dtype=np.float32)
        
        for i, track in enumerate(self.tracks):
            if track is not None and self.track_enabled[i]:
                track_float = track.astype(np.float32) / 32768.0
                mix += track_float * self.track_volumes[i]
        
        # Clip and convert
        mix = np.clip(mix, -1.0, 1.0)
        mix_int16 = (mix * 32768).astype(self.dtype)
        
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
app = MultiTrackLooper()

# GUI callbacks
def record_button_callback(sender, app_data, user_data):
    track_num = user_data
    if app.recording and app.current_track == track_num:
        app.stop_recording()
        dpg.set_item_label(f"record_btn_{track_num}", f"Record Track {track_num + 1}")
        dpg.configure_item(f"record_btn_{track_num}", button_color=(51, 51, 55))
    elif not app.recording:
        app.start_recording(track_num)
        dpg.set_item_label(f"record_btn_{track_num}", "Stop Recording")
        dpg.configure_item(f"record_btn_{track_num}", button_color=(150, 0, 0))

def play_button_callback():
    app.toggle_playback()
    if app.playing:
        dpg.set_item_label("play_btn", "Stop All")
        dpg.configure_item("play_btn", button_color=(0, 150, 0))
    else:
        dpg.set_item_label("play_btn", "Play All")
        dpg.configure_item("play_btn", button_color=(51, 51, 55))

def mute_callback(sender, app_data, user_data):
    track_num = user_data
    app.toggle_track(track_num)
    if app.track_enabled[track_num]:
        dpg.set_item_label(f"mute_btn_{track_num}", "Mute")
        dpg.configure_item(f"mute_btn_{track_num}", button_color=(51, 51, 55))
    else:
        dpg.set_item_label(f"mute_btn_{track_num}", "Muted")
        dpg.configure_item(f"mute_btn_{track_num}", button_color=(150, 150, 0))

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
app.input_stream.close()
app.output_stream.close()
dpg.destroy_context()
