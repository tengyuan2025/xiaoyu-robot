# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains tools and utilities for working with the RK3328 noise reduction board (环形六麦阵列) and the AIUI documentation system. It consists of two main components:

1. **RK3328 Hardware Control**: Python and C programs for controlling the RK3328 noise reduction board via serial communication and capturing audio from the 6-microphone array
2. **Documentation Crawler**: Web scraper for archiving AIUI documentation from https://aiui-doc.xf-yun.com/

## Key Commands

### Python Environment Setup

```bash
# Install dependencies
pip3 install -r xfmic/requirements.txt

# On Ubuntu/Debian (for audio support)
sudo apt-get install -y portaudio19-dev alsa-utils libasound2-dev python3-dev

# On macOS (for audio support)
brew install portaudio
```

### RK3328 Hardware Control

```bash
# Run the complete demo (serial control + audio recording)
python3 xfmic/rk3328_demo.py /dev/ttyUSB0 1
# Arguments: <serial_port> <audio_device_index>

# Run serial controller only
python3 xfmic/rk3328_controller.py /dev/ttyUSB0

# Run audio recorder only
python3 xfmic/audio_recorder.py

# Compile and run C program for DOA (Direction of Arrival) reading
cd xfmic
make
./rk3328_doa_reader /dev/ttyUSB0
```

### Documentation Crawler

```bash
# Crawl navigation links only (recommended, faster)
cd xfmic
python3 crawl_docs.py

# For recursive crawling, edit crawl_docs.py main() function
# Replace spider.crawl() with spider.crawl_recursive(max_depth=3)

# Clean and re-crawl
rm -rf xfmic/docs && python3 xfmic/crawl_docs.py
```

### macOS Specific Commands

On macOS, serial devices have different paths:

```bash
# Find serial devices on Mac
ls /dev/tty.usbserial*

# Run demo with macOS serial path
python3 xfmic/mac_demo.py
# Or specify manually:
python3 xfmic/rk3328_demo.py /dev/tty.usbserial-1410 0
```

## Architecture

### RK3328 Serial Communication Protocol

The RK3328 board uses a custom serial protocol at 115200 baud:
- **Sync header**: 0xA5
- **Message types**: Handshake (0x01), Device (0x02), Confirm (0x03), Master (0x04)
- **Communication flow**: Initial handshake → command/response exchange
- **Key features**: Manual wakeup, beam control (0-5 for 0°-300°), wakeup word switching

Files: `xfmic/rk3328_controller.py` (Python), `xfmic/rk3328_doa_reader.c` (C)

### Audio Capture System

The RK3328 outputs processed audio through a 3.5mm jack:
- **Sample rate**: 16000 Hz
- **Channels**: 1 (mono)
- **Format**: 16-bit PCM, little-endian
- **Capture methods**: PyAudio (cross-platform), ALSA (Linux), CoreAudio (macOS)

Files: `xfmic/audio_recorder.py`

### Beam Direction Mapping

The 6-microphone circular array provides 6 beam directions:

| Beam | Angle | Direction |
|------|-------|-----------|
| 0    | 0°    | Front     |
| 1    | 60°   | Right-front |
| 2    | 120°  | Right-rear |
| 3    | 180°  | Rear |
| 4    | 240°  | Left-rear |
| 5    | 300°  | Left-front |

### Documentation Crawler Architecture

**crawl_docs.py** - Main crawler with `DocsSpider` class:
- `parse_navigation()`: Extracts links from sidebar using `nav ul.summary` selector
- `get_file_path()`: Converts URLs to local paths (`/project-1/doc-123/` → `docs/project-1/doc-123.html`)
- `crawl()`: Navigation-only mode (154 pages, fast)
- `crawl_recursive()`: Deep crawl with configurable depth

**Key implementation details**:
- Disables SSL verification for target site: `verify=False`
- 0.5s delay between requests to avoid overwhelming server
- Generates `_navigation.json` with complete navigation metadata
- Preserves URL structure in local file paths

## Hardware Configuration

### Serial Port Setup

```bash
# Linux: Add user to dialout group for serial port access
sudo usermod -a -G dialout $USER
# Then logout/login or run:
newgrp dialout

# Temporary permission fix
sudo chmod 666 /dev/ttyUSB0

# macOS: Install CH340 driver first
# Download from: http://www.wch.cn/downloads/CH341SER_MAC_ZIP.html
# Device will appear as /dev/tty.usbserial-*
```

### Audio Device Configuration

```bash
# Linux: List audio devices
arecord -l                # ALSA devices
pactl list sources        # PulseAudio sources

# Test audio input
arecord -D hw:1,0 -f S16_LE -r 16000 -c 1 -d 5 test.wav
aplay test.wav

# macOS: Check system preferences
# System Preferences > Sound > Input
# Then use Python to list devices:
python3 -c "import pyaudio; p = pyaudio.PyAudio(); [print(f'[{i}] {p.get_device_info_by_index(i)[\"name\"]}') for i in range(p.get_device_count()) if p.get_device_info_by_index(i)['maxInputChannels'] > 0]"
```

## Platform Compatibility

### Linux (Primary Platform)
- Serial: `/dev/ttyUSB0`, `/dev/ttyS0`, `/dev/ttyAMA0`
- Audio: ALSA/PulseAudio
- Fully supported with native drivers

### macOS (Supported)
- Serial: `/dev/tty.usbserial-*` or `/dev/cu.usbserial-*`
- Audio: CoreAudio (may need USB audio adapter for newer Macs)
- Requires CH340/CP2102 driver installation
- M1/M2: Ensure ARM-compatible drivers or use Rosetta

### Windows (Via Documentation Only)
- Serial: COM ports
- Requires official Windows tools (not included in this repo)

## Common Workflows

### Voice Wake-up + ASR Integration

```python
from xfmic.rk3328_controller import RK3328Controller
from xfmic.audio_recorder import AudioRecorder

controller = RK3328Controller('/dev/ttyUSB0')
recorder = AudioRecorder(device_index=1)

if controller.connect():
    # Wait for wake event
    msg = controller.read_device_message(timeout=60)
    if msg and msg.get('type') == 'wakeup':
        # Record command
        recorder.record(duration=5, output_file='command.wav')
        # Send to ASR service...
```

### Beam Tracking Based on DOA

```python
def angle_to_beam(angle):
    """Convert angle to nearest beam index"""
    beams = [0, 60, 120, 180, 240, 300]
    distances = [abs(angle - b) for b in beams]
    return distances.index(min(distances))

while True:
    msg = controller.read_device_message()
    if msg and msg.get('type') == 'wakeup':
        angle = msg['content']['angle']
        beam = angle_to_beam(angle)
        controller.manual_wakeup(beam=beam)
```

## Important Notes

### Serial Communication
- Always wait for handshake before sending commands
- Use MSG_TYPE_CONFIRM to acknowledge device messages
- Device sends periodic heartbeat/status messages

### Audio Recording
- RK3328 only outputs audio after wakeup (unless manually triggered)
- Use exception_on_overflow=False in PyAudio to handle buffer overruns
- For real-time processing, use stream mode rather than file recording

### Documentation Crawler
- Target site has SSL certificate issues - SSL verification is disabled
- Adjust `time.sleep(0.5)` if you need different crawl speeds
- Navigation mode only crawls `/project-1/doc-*` pattern links
- Output directory is `xfmic/docs/` by default

## File Structure

```
xiaoyu-robot/
├── xfmic/                          # Main working directory
│   ├── rk3328_controller.py        # Serial control (Python)
│   ├── audio_recorder.py           # Audio capture (Python)
│   ├── rk3328_demo.py              # Complete integration demo
│   ├── mac_demo.py                 # macOS-specific demo
│   ├── rk3328_doa_reader.c         # DOA reader (C)
│   ├── crawl_docs.py               # Documentation crawler
│   ├── Makefile                    # Build C programs
│   ├── requirements.txt            # Python dependencies
│   ├── docs/                       # Crawled documentation
│   └── README*.md                  # Various guides
└── CLAUDE.md                       # This file
```

## Troubleshooting

### Serial connection fails
- Check device exists: `ls -l /dev/ttyUSB*` (Linux) or `ls /dev/tty.usbserial*` (Mac)
- Verify permissions: `sudo chmod 666 /dev/ttyUSB0`
- Check driver: `lsmod | grep ch341` or `lsmod | grep cp210x`
- Ensure TX/RX are not swapped

### No audio output
- Verify 3.5mm cable connected to correct port
- Check RK3328 is awake (manual wakeup: `controller.manual_wakeup(beam=0)`)
- Test audio input: `arecord -D hw:1,0 -f S16_LE -r 16000 -c 1 | aplay`
- Select correct input device in system settings

### PyAudio installation fails
```bash
# Ubuntu/Debian
sudo apt-get install portaudio19-dev python3-dev
pip3 install --upgrade pyaudio

# macOS
brew install portaudio
pip3 install pyaudio

# Or use system package
sudo apt-get install python3-pyaudio  # Linux
```

### Handshake timeout
- Check serial connections (TX→RX, RX→TX)
- Verify baud rate is 115200
- Ensure RK3328 board is powered (DC 12V)
- Try different serial port or cable
