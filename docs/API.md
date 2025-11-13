# API Reference - Wrist Rotation Detection

Complete API documentation for integrating the Wrist Rotation Detection system.

## 📦 Modules

### `WristRotationDetector`

Main detector class for hand state and wrist rotation detection with UDP communication.

#### Import

```python
from gesture_oak.detection.wrist_rotation_detector import (
    WristRotationDetector,
    HandState,
    RotationPosition,
    WRIST
)
```

---

## 🎯 Classes

### `WristRotationDetector`

**Description**: Main detector class combining hand state detection, wrist rotation tracking, and UDP broadcasting.

#### Constructor

```python
WristRotationDetector(udp_ip="192.168.0.10", udp_port=9000)
```

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `udp_ip` | `str` | `"192.168.0.10"` | Destination IP address for UDP messages |
| `udp_port` | `int` | `9000` | Destination port for UDP messages |

**Returns:** `WristRotationDetector` instance

**Example:**
```python
# Default settings
detector = WristRotationDetector()

# Custom UDP settings
detector = WristRotationDetector(udp_ip="192.168.1.100", udp_port=8080)
```

---

#### Methods

### `update(hand)`

**Description**: Main update function. Processes hand landmarks and returns detection results.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `hand` | `object` or `None` | Hand object with landmarks from hand detector |

**Returns:** `Tuple[RotationPosition, Optional[float], HandState]`
- `RotationPosition`: Current position (0-4)
- `float` or `None`: Current angle in degrees (0-180°)
- `HandState`: Current hand state (FISTED/OPEN/UNKNOWN)

**Side Effects:**
- Writes to `result.txt`
- Sends UDP messages (when values change)
- Updates internal state
- Prints to console

**Example:**
```python
# With hand detected
position, angle, state = detector.update(hand)
print(f"Position: {position.value}, Angle: {angle}°, State: {state.name}")

# No hand detected
position, angle, state = detector.update(None)
# Returns: (RotationPosition.NONE, None, HandState.UNKNOWN)
# Sends: "area/menu/0" after 3 seconds
```

**Behavior:**
```
Hand Present:
  1. Detect hand state (FISTED/OPEN)
  2. Calculate wrist angle
  3. Map angle to position (1-4)
  4. Send UDP messages (state + position)
  5. Return (position, angle, state)

No Hand:
  1. Start 3-second timer (if not started)
  2. After 3s: Send "area/menu/0"
  3. Return (NONE, None, UNKNOWN)

Hand Returns:
  1. Reset timer
  2. Resume normal detection
```

---

### `reset()`

**Description**: Resets all detector state to initial values.

**Parameters:** None

**Returns:** `None`

**Example:**
```python
detector.reset()
```

**Resets:**
- Angle buffer
- Hand state (→ UNKNOWN)
- Position (→ NONE)
- Calibration data
- UDP message cache
- NO HAND timer

---

### `get_state_info()`

**Description**: Returns dictionary with current detector state.

**Parameters:** None

**Returns:** `dict` with keys:
```python
{
    "state": str,              # "OPEN", "FISTED", or "UNKNOWN"
    "hand_state": str,         # Same as "state"
    "angle": float or None,    # Current angle in degrees
    "position": int,           # Position value (0-4)
    "position_name": str,      # Human-readable position name
    "calibrated": bool,        # Whether auto-calibration completed
    "finger_states": dict,     # Individual finger states
}
```

**Example:**
```python
info = detector.get_state_info()

print(f"State: {info['state']}")
print(f"Angle: {info['angle']:.1f}°")
print(f"Position: {info['position']} - {info['position_name']}")
print(f"Calibrated: {info['calibrated']}")

# Finger states
fingers = info['finger_states']
print(f"Thumb: {'✓' if fingers['thumb'] else '✗'}")
print(f"Index: {'✓' if fingers['index'] else '✗'}")
```

---

## 🏷️ Enumerations

### `HandState`

**Description**: Enum representing hand state.

**Values:**
```python
class HandState(Enum):
    UNKNOWN = auto()  # Initial state or no hand
    FISTED = auto()   # All fingers curled
    OPEN = auto()     # 2+ fingers extended
```

**Usage:**
```python
if state == HandState.FISTED:
    print("Hand is fisted")
elif state == HandState.OPEN:
    print("Hand is open")
```

---

### `RotationPosition`

**Description**: Enum representing wrist rotation position.

**Values:**
```python
class RotationPosition(Enum):
    NONE = 0        # No hand or invalid state
    LEFT_FAR = 1    # 0° to 60° (far left)
    LEFT_NEAR = 2   # 60° to 90° (center-left)
    RIGHT_NEAR = 3  # 90° to 120° (center-right)
    RIGHT_FAR = 4   # 120° to 180° (far right)
```

**Usage:**
```python
if position == RotationPosition.LEFT_FAR:
    print("Hand rotated far left")

# Get numeric value
pos_value = position.value  # 1, 2, 3, 4, or 0
```

---

## 📡 UDP Messages

### Message Protocol

All UDP messages are UTF-8 encoded strings sent to configured IP:Port.

### Message Types

#### 1. Gesture Messages

**Format:** `gesture/{name}`

| Message | Sent When | Description |
|---------|-----------|-------------|
| `gesture/five` | Hand state → OPEN | Hand is open (2+ fingers extended) |
| `gesture/zero` | Hand state → FISTED | Hand is fisted (all fingers curled) |

**Example:**
```python
# Automatically sent by detector
# When hand opens: "gesture/five"
# When hand closes: "gesture/zero"
```

#### 2. Position Messages

**Format:** `area/menu/{position}`

| Message | Sent When | Description |
|---------|-----------|-------------|
| `area/menu/1` | Position → 1 | Angle: 0-60° (LEFT) |
| `area/menu/2` | Position → 2 | Angle: 60-90° (CENTER-LEFT) |
| `area/menu/3` | Position → 3 | Angle: 90-120° (CENTER-RIGHT) |
| `area/menu/4` | Position → 4 | Angle: 120-180° (RIGHT) |
| `area/menu/0` | No hand (3s delay) | No hand detected |

**Example:**
```python
# Automatically sent by detector
# When position changes: "area/menu/1" through "area/menu/4"
# When hand removed (after 3s): "area/menu/0"
```

---

## 📊 Output Files

### `result.txt`

**Description**: Text file updated in real-time with current detector state.

**Format:**
```
State: {OPEN|FISTED|UNKNOWN|NO_HAND}
Position: {0-4}
Angle: {angle}°
```

**Location:** Same directory as script

**Example Content:**
```
State: OPEN
Position: 3
Angle: 105.2°
```

**Update Frequency:** Every frame (~30 Hz)

---

## 🔧 Configuration

### Constants

```python
# Landmark indices (MediaPipe Hand)
WRIST = 0
THUMB_TIP = 4
INDEX_TIP = 8
MIDDLE_TIP = 12
RING_TIP = 16
PINKY_TIP = 20

# And more... (see source for complete list)
```

### Adjustable Parameters

Can be modified in source code:

```python
class WristRotationDetector:
    def __init__(self):
        # Smoothing
        self.angle_buffer = deque(maxlen=5)  # Change for more/less smoothing
        
        # Detection
        FINGER_RATIO_THRESHOLD = 1.2         # Adjust sensitivity
        
        # Timing
        self._no_hand_delay_seconds = 3.0    # Change delay
```

---

## 💡 Usage Examples

### Basic Usage

```python
from gesture_oak.detection.wrist_rotation_detector import WristRotationDetector
from gesture_oak.detection.hand_detector import HandDetector

# Initialize
hand_detector = HandDetector()
rotation_detector = WristRotationDetector()

# Main loop
while True:
    frame, hands, _ = hand_detector.get_frame_and_hands()
    
    if hands:
        # Update with detected hand
        position, angle, state = rotation_detector.update(hands[0])
        print(f"{state.name} | Position {position.value} | {angle:.1f}°")
    else:
        # Update with no hand (triggers NO HAND after 3s)
        rotation_detector.update(None)
```

### Custom UDP Configuration

```python
# Custom IP and port
detector = WristRotationDetector(
    udp_ip="192.168.1.50",
    udp_port=12345
)
```

### State Monitoring

```python
def on_state_change(old_state, new_state):
    if new_state == HandState.FISTED:
        print("Hand closed - trigger action!")
    elif new_state == HandState.OPEN:
        print("Hand opened - enable tracking!")

# In loop
old_state = HandState.UNKNOWN
while True:
    _, _, state = detector.update(hand)
    
    if state != old_state:
        on_state_change(old_state, state)
        old_state = state
```

### Position Callback

```python
def on_position_change(position):
    actions = {
        1: lambda: print("Action: LEFT"),
        2: lambda: print("Action: CENTER-LEFT"),
        3: lambda: print("Action: CENTER-RIGHT"),
        4: lambda: print("Action: RIGHT"),
    }
    
    if position.value in actions:
        actions[position.value]()

# In loop
old_pos = RotationPosition.NONE
while True:
    position, _, _ = detector.update(hand)
    
    if position != old_pos and position != RotationPosition.NONE:
        on_position_change(position)
        old_pos = position
```

### UDP Receiver (Python)

```python
import socket

def receive_gestures():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 9000))
    
    print("Listening for gestures...")
    
    while True:
        data, addr = sock.recvfrom(1024)
        message = data.decode()
        
        if message == "gesture/five":
            print("✋ Hand OPEN")
        elif message == "gesture/zero":
            print("✊ Hand FISTED")
        elif message.startswith("area/menu/"):
            pos = message.split("/")[-1]
            print(f"📍 Position: {pos}")

# Run receiver
receive_gestures()
```

### Error Handling

```python
import socket

try:
    detector = WristRotationDetector(udp_ip="192.168.0.10")
    
    while True:
        try:
            position, angle, state = detector.update(hand)
            # Process results...
            
        except Exception as e:
            print(f"Detection error: {e}")
            continue
            
except KeyboardInterrupt:
    print("Stopped")
except socket.error as e:
    print(f"UDP socket error: {e}")
finally:
    detector.reset()
```

---

## 🐛 Debugging

### Enable Verbose Logging

```python
# In detector update loop
info = detector.get_state_info()
print(f"Debug: {info}")
```

### Check UDP Transmission

```bash
# Terminal 1: Run detector
python main.py

# Terminal 2: Monitor UDP
nc -ul 9000  # Linux/Mac
```

### Verify Hand Detection

```python
# Check landmarks
if hasattr(hand, 'landmarks'):
    print(f"Landmarks detected: {len(hand.landmarks)}")
    print(f"Wrist position: {hand.landmarks[WRIST]}")
```

---

## 📝 Type Hints

```python
from typing import Optional, Tuple

class WristRotationDetector:
    def update(self, hand) -> Tuple[RotationPosition, Optional[float], HandState]:
        ...
    
    def reset(self) -> None:
        ...
    
    def get_state_info(self) -> dict:
        ...
```

---

## ⚠️ Common Pitfalls

### 1. Calling update() without None check

```python
# ❌ Wrong
if hands:
    detector.update(hands[0])
# No update when hands is empty!

# ✅ Correct
if hands:
    detector.update(hands[0])
else:
    detector.update(None)  # Triggers NO HAND after 3s
```

### 2. Not checking position value

```python
# ❌ Wrong
print(f"Position: {position}")  # Prints enum

# ✅ Correct
print(f"Position: {position.value}")  # Prints 0-4
```

### 3. Expecting immediate NO HAND

```python
# ❌ Wrong expectation
detector.update(None)
# Expects "area/menu/0" sent immediately

# ✅ Correct understanding
detector.update(None)
# "area/menu/0" sent after 3 seconds
```

---

## 📚 See Also

- [README.md](README.md) - Project overview
- [QUICKSTART.md](QUICKSTART.md) - Quick start guide
- [TECHNICAL.md](TECHNICAL.md) - Technical details

---

**Version:** 3.0.0  
**Last Updated:** 2024
