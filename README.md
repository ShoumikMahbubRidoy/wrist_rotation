# Wrist Rotation Detection System

A real-time hand gesture and wrist rotation detection system using OAK-D camera with MediaPipe hand tracking and UDP communication.

## 🎯 Overview

This system detects:
- **Hand State**: FISTED or OPEN
- **Wrist Rotation Position**: 4 zones (1-4) based on rotation angle (0-180°)
- **Real-time UDP Communication**: Sends gesture and position data over network

## 🚀 Features

### Core Functionality
- ✅ **Independent Detection**: Hand state and position are detected independently
- ✅ **Real-time Position Tracking**: Position updates instantly as you rotate your wrist
- ✅ **Visual Feedback**: Interactive UI with position zones drawn on screen
- ✅ **UDP Broadcasting**: Sends gesture and position data to remote systems
- ✅ **Smart NO HAND Detection**: 3-second delay before sending "no hand" signal (prevents false triggers)
- ✅ **Auto-Calibration**: Automatically calibrates neutral position at startup
- ✅ **Mirrored Display**: Natural hand movement (frame and landmarks mirrored)

### Position Zones

The wrist rotation is divided into 4 positions:

```
        2 | 3
    1   \|/   4
    ----hand----
```

- **Position 1** (LEFT): 0° to 60° - Yellow zone
- **Position 2** (LEFT-CENTER): 60° to 90° - Green zone
- **Position 3** (RIGHT-CENTER): 90° to 120° - Orange zone
- **Position 4** (RIGHT): 120° to 180° - Red zone

### Visual Display

The application shows:
- 4 colored fan-shaped zones emanating from wrist
- Current zone highlighted with transparent overlay
- Hand skeleton with landmark points
- Real-time angle indicator
- Hand state (FISTED/OPEN)
- Finger detection status (debug info)

## 📡 UDP Communication

### Messages Sent

The system sends UTF-8 encoded strings to `192.168.0.10:9000`:

| Event | UDP Message | Description |
|-------|-------------|-------------|
| Hand OPEN | `gesture/five` | All or most fingers extended |
| Hand FISTED | `gesture/zero` | All fingers curled |
| Position 1 | `area/menu/1` | Wrist angle 0-60° |
| Position 2 | `area/menu/2` | Wrist angle 60-90° |
| Position 3 | `area/menu/3` | Wrist angle 90-120° |
| Position 4 | `area/menu/4` | Wrist angle 120-180° |
| No Hand | `area/menu/0` | No hand detected (after 3s delay) |

### Message Timing
- **Hand state & Position**: Sent immediately (real-time)
- **No Hand**: Sent after 3-second delay (prevents false triggers when hand temporarily leaves frame)
- **Smart Sending**: Only sends when values change (no spam)

### UDP Configuration

Default settings:
```python
UDP_IP = "192.168.0.10"
UDP_PORT = 9000
NO_HAND_DELAY = 3.0  # seconds
```

To change UDP settings, edit in `wrist_rotation_detector.py`:
```python
detector = WristRotationDetector(udp_ip="YOUR_IP", udp_port=YOUR_PORT)
```

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- OAK-D or OAK-D Lite camera
- Windows/Linux/Mac

### Dependencies
```bash
pip install depthai opencv-python numpy
```

### Setup
```bash
# Clone or download the project
cd wrist_rotation

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## 📖 Usage

### Quick Start

1. **Connect OAK-D Camera**
2. **Run Application**:
   ```bash
   python main.py
   # Select option 5: "Run wrist rotation detection"
   ```
3. **Position Your Hand**: 
   - Place hand 40-100cm from camera
   - Palm facing camera
   - Hand visible in frame

4. **Interact**:
   - Rotate wrist left/right → Position changes (1→2→3→4)
   - Open/close fist → Hand state changes
   - Move hand → Zones follow your wrist

### Controls

| Key | Action |
|-----|--------|
| `q` | Quit application |
| `r` | Reset calibration |
| `s` | Save current frame |

## 🔧 Technical Details

### Detection Algorithm

#### Hand State Detection
Uses multi-method approach:
1. **Distance Ratio Method**: Compares fingertip-to-wrist vs MCP-to-wrist distances
2. **Finger Spread Analysis**: Measures distance between fingertips
3. **Palm Distance Check**: Detects if fingertips are bunched near palm center

Threshold: `ratio > 1.2` (fingertip must be 20% farther than MCP)

**Decision Logic**:
- 3+ fingertips near palm center → FISTED
- 2+ fingers extended OR good spread → OPEN
- Otherwise → FISTED

#### Wrist Rotation Detection
- Calculates angle of wrist→middle-MCP vector
- Range: 0° (left) to 180° (right), with 90° as center
- Smoothing: 5-frame median filter
- Auto-calibration: Centers neutral position to 90°

#### Position Mapping
Direct angle-to-position mapping:
```python
if angle < 60°:   Position 1
if angle < 90°:   Position 2  
if angle < 120°:  Position 3
else:             Position 4
```

### Performance
- **FPS**: ~30 FPS (depends on hardware)
- **Latency**: <50ms for position updates
- **Detection Distance**: 40-100cm optimal

## 📁 Project Structure

```
wrist_rotation/
├── main.py                          # Main entry point
├── src/
│   └── gesture_oak/
│       ├── detection/
│       │   ├── hand_detector.py                 # OAK-D hand detection
│       │   └── wrist_rotation_detector.py       # Wrist rotation + UDP
│       └── apps/
│           └── wrist_rotation_app.py            # Main application UI
├── result.txt                       # Output file (state, position, angle)
└── README.md                        # This file
```

## 🐛 Troubleshooting

### Hand Not Detected
- **Solution**: Ensure hand is 40-100cm from camera
- Check lighting conditions (IR cameras work in dark)
- Make sure palm faces camera

### Fist Detection Not Working
- **Solution**: Make a tight fist with all fingers curled
- Ensure fingertips are close to palm
- Try pressing 'r' to reset calibration

### Position Not Updating
- **Solution**: Open your hand (position only updates when hand is OPEN)
- Check that hand state shows "HAND OPEN = 1"
- Rotate wrist more dramatically

### UDP Messages Not Received
- **Solution**: Check UDP IP/Port settings
- Verify network connection
- Use Wireshark or `nc -ul 9000` to monitor UDP traffic
- Check firewall settings

### Zones Not Visible
- **Solution**: Ensure hand is detected (skeleton should be visible)
- Zones appear only when hand is in frame
- Check that wrist landmark is detected

## 📊 Output Files

### result.txt
Updated in real-time with current state:
```
State: OPEN
Position: 3
Angle: 105.2°
```

### Saved Frames
Press 's' to save current frame:
- Filename: `wrist_0001.jpg`, `wrist_0002.jpg`, etc.
- Includes all visual overlays (zones, skeleton, text)

## 🔬 Advanced Configuration

### Adjust Sensitivity

Edit `wrist_rotation_detector.py`:

```python
# Fist detection threshold (higher = stricter)
ratio > 1.2  # Default, change to 1.1 (looser) or 1.3 (stricter)

# NO HAND delay
self._no_hand_delay_seconds = 3.0  # Change to 2.0 or 5.0

# Angle smoothing (frames)
self.angle_buffer = deque(maxlen=5)  # Change to 3 (faster) or 10 (smoother)
```

### Custom Position Ranges

Edit position boundaries:
```python
def _angle_to_position(self, angle: float) -> RotationPosition:
    if angle < 60.0:    # Change these thresholds
        return RotationPosition.LEFT_FAR
    elif angle < 90.0:
        return RotationPosition.LEFT_NEAR
    # ... etc
```

## 🎨 Customization

### Change Zone Colors

In `wrist_rotation_app.py`:
```python
zone_colors = {
    1: (0, 255, 255),    # Yellow (BGR format)
    2: (0, 255, 0),      # Green
    3: (255, 128, 0),    # Orange
    4: (0, 0, 255)       # Red
}
```

### Modify UDP Protocol

Change message format in `_send_udp()` method:
```python
state_msg = "gesture/five"  # Customize these strings
pos_msg = f"area/menu/{pos}"
```

## 🧪 Testing

### Test UDP Reception (Linux/Mac)
```bash
# Listen on UDP port
nc -ul 9000
```

### Test UDP Reception (Windows PowerShell)
```powershell
# Use Python to listen
python -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.bind(('0.0.0.0', 9000)); print('Listening...'); [print(s.recvfrom(1024)[0].decode()) for _ in iter(int, 1)]"
```

### Test Workflow
1. Start UDP listener
2. Run wrist rotation app
3. Verify messages received:
   - Open hand → `gesture/five`
   - Close fist → `gesture/zero`
   - Rotate wrist → `area/menu/1-4`
   - Remove hand (wait 3s) → `area/menu/0`

## 📝 Version History

### v3.0.0 (Current)
- ✅ Added UDP communication
- ✅ Visual position zones
- ✅ 3-second NO HAND delay
- ✅ Improved fist detection (triple method)
- ✅ Independent position/state detection
- ✅ Mirrored display
- ✅ Auto-calibration

### v2.0.0
- ✅ Simplified detection algorithm
- ✅ Direct angle-to-position mapping

### v1.0.0
- ✅ Initial release
- ✅ Basic wrist rotation detection

## 🤝 Contributing

Issues and pull requests welcome!

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- Built with [DepthAI](https://github.com/luxonis/depthai)
- Uses MediaPipe hand tracking models
- Inspired by hand gesture control systems

## 📧 Support

For issues or questions:
- Check Troubleshooting section
- Review code comments in `wrist_rotation_detector.py`
- Test with simplified UDP listener

## 🎯 Use Cases

- **Gaming Control**: Map positions to game actions
- **Smart Home**: Control lights, devices with hand gestures
- **Presentation Control**: Navigate slides with wrist rotation
- **Accessibility**: Hands-free computer control
- **VR/AR Input**: Natural hand-based interaction
- **Robotics**: Control robot movements with gestures

---

**Made with ❤️ using OAK-D Camera**
