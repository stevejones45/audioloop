# 4-Track Looper

A minimal 4-track audio looper application built with Python and Dear PyGui.

## Features
- **4 independent tracks** for layering audio
- **First track sets the loop length** - all subsequent tracks automatically loop to match
- **Per-track controls**:
  - Record button
  - Mute/unmute
  - Clear track
  - Volume slider
- **Visual waveforms** for each track
- **Master playback** control
- **Save mix** - exports all tracks mixed together as WAV

## Installation

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Optional: Install ASIO4ALL for better audio performance on Windows:
   - Download from: https://www.asio4all.org/

## Usage

1. Run the application:
   ```
   python audioloop.py
   ```

2. **Record your first track** (this sets the loop length):
   - Click "Record Track 1"
   - Play/sing/make sounds
   - Click "Stop Recording"

3. **Layer additional tracks**:
   - Click "Record Track 2/3/4"
   - The new recording will automatically loop to match Track 1's length

4. **Mix and control**:
   - Use "Mute" buttons to toggle tracks on/off
   - Adjust volume sliders for each track
   - Click "Play All" to hear your loop

5. **Save your creation**:
   - Enter a filename and click "Save Mix"

## Notes
- Stereo recording (2 channels)
- 44.1kHz sample rate, 16-bit depth
- First recorded track determines the loop length for all tracks
- Recordings longer than the loop length are truncated
- Recordings shorter than the loop length are automatically looped
