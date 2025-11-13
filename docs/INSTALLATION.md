# Installation Guide - Wrist Rotation Detection System

Complete installation instructions for all platforms.

## 📋 System Requirements

### Hardware
- **Camera**: OAK-D or OAK-D Lite (required)
- **USB**: USB 3.0 port (USB 2.0 works but slower)
- **RAM**: 4 GB minimum, 8 GB recommended
- **CPU**: Intel i5 or equivalent (2 GHz+)

### Software
- **OS**: Windows 10/11, macOS 10.14+, or Linux (Ubuntu 20.04+)
- **Python**: 3.8, 3.9, 3.10, or 3.11
- **Network**: For UDP communication (optional)

---

## 🚀 Quick Install

### Windows

```powershell
# 1. Install Python (if not installed)
# Download from https://www.python.org/downloads/

# 2. Clone/Download project
cd C:\Users\YourName\Desktop
# (Extract wrist_rotation folder here)

# 3. Create virtual environment
cd wrist_rotation
python -m venv .venv

# 4. Activate virtual environment
.venv\Scripts\activate

# 5. Install dependencies
pip install -r requirements.txt

# 6. Run application
python main.py
```

### macOS

```bash
# 1. Install Python (if not installed)
brew install python@3.10

# 2. Clone/Download project
cd ~/Desktop
# (Extract wrist_rotation folder here)

# 3. Create virtual environment
cd wrist_rotation
python3 -m venv .venv

# 4. Activate virtual environment
source .venv/bin/activate

# 5. Install dependencies
pip install -r requirements.txt

# 6. Run application
python main.py
```

### Linux (Ubuntu/Debian)

```bash
# 1. Install Python and dependencies
sudo apt update
sudo apt install python3.10 python3-pip python3-venv

# 2. Install USB rules for OAK-D
echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="03e7", MODE="0666"' | sudo tee /etc/udev/rules.d/80-movidius.rules
sudo udevadm control --reload-rules && sudo udevadm trigger

# 3. Clone/Download project
cd ~/Desktop
# (Extract wrist_rotation folder here)

# 4. Create virtual environment
cd wrist_rotation
python3 -m venv .venv

# 5. Activate virtual environment
source .venv/bin/activate

# 6. Install dependencies
pip install -r requirements.txt

# 7. Run application
python main.py
```

---

## 📦 Detailed Installation

### Step 1: Python Installation

#### Windows
1. Download Python from [python.org](https://www.python.org/downloads/)
2. Run installer
3. ✅ Check "Add Python to PATH"
4. Click "Install Now"
5. Verify installation:
   ```powershell
   python --version
   ```

#### macOS
```bash
# Using Homebrew
brew install python@3.10

# Or download from python.org
```

#### Linux
```bash
# Ubuntu/Debian
sudo apt install python3.10 python3-pip

# Fedora
sudo dnf install python3.10 python3-pip

# Arch
sudo pacman -S python python-pip
```

### Step 2: Get the Project

#### Option A: Download ZIP
1. Download project ZIP file
2. Extract to desired location
3. Rename folder to `wrist_rotation`

#### Option B: Git Clone (if available)
```bash
git clone https://github.com/yourrepo/wrist_rotation.git
cd wrist_rotation
```

### Step 3: Virtual Environment

**Why?** Isolates project dependencies from system Python.

#### Windows
```powershell
cd wrist_rotation
python -m venv .venv
.venv\Scripts\activate
```

#### macOS/Linux
```bash
cd wrist_rotation
python3 -m venv .venv
source .venv/bin/activate
```

**Verify activation:**
- Prompt should show `(.venv)` prefix
- Example: `(.venv) PS C:\wrist_rotation>`

### Step 4: Install Dependencies

#### Create requirements.txt (if missing)

```txt
depthai>=2.21.0
opencv-python>=4.8.0
numpy>=1.24.0
```

#### Install
```bash
# Inside virtual environment
pip install -r requirements.txt
```

**Or install individually:**
```bash
pip install depthai opencv-python numpy
```

### Step 5: Connect OAK-D Camera

1. Connect OAK-D to USB 3.0 port (blue port)
2. Wait for driver installation (Windows)
3. Verify connection:
   ```bash
   # Should detect camera
   python -c "import depthai as dai; print(dai.Device.getAllAvailableDevices())"
   ```

### Step 6: Test Installation

```bash
python main.py
# Select option 1: Test camera connection
```

**Expected output:**
```
Camera detected: OAK-D-LITE
USB Speed: SUPER
✅ Connection successful!
```

---

## 🔧 Troubleshooting

### Issue: "python: command not found"

**Windows:**
```powershell
# Use 'py' instead of 'python'
py --version
py -m venv .venv
```

**macOS/Linux:**
```bash
# Use 'python3'
python3 --version
python3 -m venv .venv
```

### Issue: Camera Not Detected

**Windows:**
- Check Device Manager for "Movidius MyriadX" under "Universal Serial Bus devices"
- Try different USB port
- Update USB drivers

**Linux:**
```bash
# Check USB permissions
lsusb | grep 03e7

# Reinstall udev rules
sudo sh -c 'echo "SUBSYSTEM==\"usb\", ATTRS{idVendor}==\"03e7\", MODE=\"0666\"" > /etc/udev/rules.d/80-movidius.rules'
sudo udevadm control --reload-rules
sudo udevadm trigger

# Reboot
sudo reboot
```

**macOS:**
- Try different USB port
- Check System Preferences > Security & Privacy for blocked device

### Issue: ModuleNotFoundError

```bash
# Make sure virtual environment is activated
# Look for (.venv) in prompt

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: Import cv2 error

```bash
# OpenCV not installed correctly
pip uninstall opencv-python
pip install opencv-python --no-cache-dir

# Or try headless version
pip install opencv-python-headless
```

### Issue: Permission Denied (Linux)

```bash
# USB permissions
sudo usermod -a -G plugdev $USER
sudo reboot

# Or run with sudo (not recommended)
sudo python main.py
```

### Issue: Slow Performance

- Use USB 3.0 port (blue port)
- Close other applications
- Check CPU usage (should be <30%)
- Reduce resolution (edit hand_detector.py):
  ```python
  resolution=(640, 480)  # Lower from (1280, 720)
  ```

---

## 🌐 Network Configuration

### For UDP Communication

#### Windows Firewall
```powershell
# Allow UDP port 9000
New-NetFirewallRule -DisplayName "Wrist Rotation UDP" -Direction Outbound -Protocol UDP -LocalPort 9000 -Action Allow
```

#### Linux Firewall (UFW)
```bash
sudo ufw allow 9000/udp
```

#### macOS Firewall
1. System Preferences > Security & Privacy > Firewall
2. Click "Firewall Options"
3. Add Python to allowed apps

### Test UDP Connection

**Receiver (Terminal 1):**
```bash
# Linux/Mac
nc -ul 9000

# Windows (PowerShell)
# Use Python listener script
```

**Sender (Terminal 2):**
```bash
python main.py
# Select option 5
# Move hand to trigger UDP messages
```

---

## 📁 Project Structure

After installation:
```
wrist_rotation/
├── .venv/                  # Virtual environment (created)
├── src/
│   └── gesture_oak/
│       ├── detection/
│       │   ├── hand_detector.py
│       │   └── wrist_rotation_detector.py
│       └── apps/
│           └── wrist_rotation_app.py
├── main.py
├── requirements.txt
├── README.md
└── result.txt             # Created at runtime
```

---

## 🔄 Updating

### Update Dependencies

```bash
# Activate virtual environment
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Update all packages
pip install --upgrade depthai opencv-python numpy
```

### Update Project Files

1. Download new version
2. Replace files (keep .venv folder)
3. Update dependencies if requirements.txt changed:
   ```bash
   pip install -r requirements.txt --upgrade
   ```

---

## 🗑️ Uninstallation

### Remove Virtual Environment

```bash
# Just delete the .venv folder
rm -rf .venv  # Linux/Mac
rmdir /s .venv  # Windows
```

### Complete Removal

```bash
# Delete entire project folder
rm -rf wrist_rotation  # Linux/Mac
rmdir /s wrist_rotation  # Windows
```

---

## 🐳 Docker Installation (Advanced)

### Dockerfile

```dockerfile
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libusb-1.0-0 \
    libgl1-mesa-glx \
    libglib2.0-0

# Copy project
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run
CMD ["python", "main.py"]
```

### Build & Run

```bash
# Build image
docker build -t wrist-rotation .

# Run with USB device access
docker run --rm -it \
  --device=/dev/bus/usb \
  --network host \
  wrist-rotation
```

---

## 📊 Verify Installation

### Complete Checklist

- [ ] Python 3.8+ installed
- [ ] Virtual environment created and activated
- [ ] Dependencies installed (depthai, opencv, numpy)
- [ ] OAK-D camera connected
- [ ] Camera detected by system
- [ ] Application runs without errors
- [ ] Hand detection works
- [ ] Position detection works
- [ ] UDP messages sent (optional)

### Test Script

```bash
# Run this to verify everything
python -c "
import sys
import depthai as dai
import cv2
import numpy as np

print('✓ Python:', sys.version)
print('✓ DepthAI:', dai.__version__)
print('✓ OpenCV:', cv2.__version__)
print('✓ NumPy:', np.__version__)

devices = dai.Device.getAllAvailableDevices()
if devices:
    print('✓ OAK-D camera detected')
else:
    print('✗ No camera detected')
"
```

---

## 🆘 Getting Help

### Common Commands

```bash
# Check Python version
python --version

# Check installed packages
pip list

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Clear pip cache
pip cache purge
```

### Support Resources

- Check README.md for usage guide
- Check TROUBLESHOOTING section above
- Check camera connection
- Verify USB port is USB 3.0

---

## 🎓 Next Steps

After successful installation:

1. ✅ Read [QUICKSTART.md](QUICKSTART.md)
2. ✅ Run `python main.py` and select option 5
3. ✅ Test hand detection and rotation
4. ✅ Configure UDP IP/Port if needed
5. ✅ Integrate with your application!

---

**Installation successful? Great! Now check the [Quick Start Guide](QUICKSTART.md) to start using the system! 🚀**
