# Quick Start Guide - Wrist Rotation Detection

## ⚡ 5-Minute Setup

### 1. Install Dependencies
```bash
pip install depthai opencv-python numpy
```

### 2. Run Application
```bash
python main.py
# Select option 5
```

### 3. Test Hand Detection
- ✋ Show your hand to camera (40-100cm away)
- 🔄 Rotate your wrist left/right
- ✊ Open and close fist
- 📡 Watch UDP messages in console

## 🎮 Quick Controls

| Action | Result |
|--------|--------|
| Rotate wrist LEFT | Position 1 (0-60°) |
| Rotate wrist UP | Position 2 (60-90°) |
| Rotate wrist slightly RIGHT | Position 3 (90-120°) |
| Rotate wrist FAR RIGHT | Position 4 (120-180°) |
| Make fist | `gesture/zero` |
| Open hand | `gesture/five` |
| Remove hand (3s) | `area/menu/0` |

## 📡 UDP Messages

Messages sent to **192.168.0.10:9000**:

```
gesture/five    → Hand open
gesture/zero    → Hand fisted
area/menu/1     → Position 1
area/menu/2     → Position 2
area/menu/3     → Position 3
area/menu/4     → Position 4
area/menu/0     → No hand (after 3 seconds)
```

## 🧪 Test UDP (Terminal)

**Linux/Mac:**
```bash
nc -ul 9000
```

**Windows (PowerShell):**
```powershell
python -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.bind(('0.0.0.0', 9000)); print('Listening on UDP 9000...'); [print(f'Received: {s.recvfrom(1024)[0].decode()}') for _ in iter(int, 1)]"
```

## 🎨 Visual Guide

```
        POSITION ZONES
        
        2 | 3
    1   \|/   4
    ----WRIST----
    
Zone 1: Yellow (LEFT)
Zone 2: Green (CENTER-LEFT)
Zone 3: Orange (CENTER-RIGHT)
Zone 4: Red (RIGHT)
```

## 🔧 Common Issues

### Hand not detected?
- Move hand closer (40-100cm)
- Ensure palm faces camera
- Check lighting

### Fist not working?
- Make tight fist
- Press 'r' to reset
- Try again

### Position not updating?
- **IMPORTANT**: Position only updates when hand is OPEN
- Make sure "HAND OPEN = 1" shows on screen
- Close fist to lock position

### No UDP messages?
- Check IP: 192.168.0.10
- Check Port: 9000
- Test with UDP listener above

## 💡 Pro Tips

1. **Calibration**: App auto-calibrates on startup. Keep hand steady for 3 seconds at start.

2. **Smooth Transitions**: Open your hand for position tracking, close fist to "lock" current position.

3. **NO HAND Delay**: System waits 3 seconds before sending `area/menu/0` to avoid false triggers.

4. **Visual Zones**: Colored zones follow your hand! They show valid rotation areas.

5. **Keyboard Shortcuts**:
   - `q` - Quit
   - `r` - Reset calibration  
   - `s` - Save screenshot

## 📊 Expected Output

**Console:**
```
✓ UDP enabled: 192.168.0.10:9000
✓ Calibrated to 87.3°
✓ Ready!
📡 UDP: gesture/five
📡 UDP: area/menu/2
📡 UDP: area/menu/3
📡 UDP: gesture/zero
⏳ Hand lost, waiting 3 seconds...
📡 UDP: area/menu/0
```

**Screen Display:**
- Hand skeleton (green lines)
- 4 colored position zones
- Current position highlighted
- Hand state (FISTED/OPEN)
- Real-time angle

**result.txt:**
```
State: OPEN
Position: 3
Angle: 105.2°
```

## 🚀 Next Steps

1. ✅ Verify UDP messages received
2. ✅ Test all 4 positions
3. ✅ Test fist/open detection
4. ✅ Test NO HAND delay (3 seconds)
5. ✅ Integrate with your application!

## 🎯 Integration Example

**Python UDP Receiver:**
```python
import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", 9000))

while True:
    data, addr = sock.recvfrom(1024)
    message = data.decode()
    
    if message == "gesture/five":
        print("Hand is OPEN!")
    elif message == "gesture/zero":
        print("Hand is FISTED!")
    elif message.startswith("area/menu/"):
        position = message.split("/")[-1]
        print(f"Position: {position}")
```

**Node.js UDP Receiver:**
```javascript
const dgram = require('dgram');
const server = dgram.createSocket('udp4');

server.on('message', (msg, rinfo) => {
    const message = msg.toString();
    console.log(`Received: ${message}`);
    
    if (message === 'gesture/five') {
        console.log('Hand OPEN!');
    } else if (message === 'gesture/zero') {
        console.log('Hand FISTED!');
    } else if (message.startsWith('area/menu/')) {
        const position = message.split('/')[2];
        console.log(`Position: ${position}`);
    }
});

server.bind(9000);
console.log('Listening on UDP port 9000...');
```

## 📱 Mobile/IoT Integration

Send UDP to your ESP32/Arduino/Raspberry Pi:

**Example: Control LED based on position**
```
area/menu/1 → LED Blue
area/menu/2 → LED Green
area/menu/3 → LED Yellow
area/menu/4 → LED Red
gesture/zero → LED OFF
```

---

**Ready to go! 🚀**

See full README.md for advanced configuration and troubleshooting.
