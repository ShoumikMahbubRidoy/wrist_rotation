# Smart Combined Detection - EXE Build Guide
## Create Standalone Executable for Windows

---

## 📦 What This Creates

A **single executable file** (`SmartCombinedDetection.exe`) that:
- ✅ Runs on any Windows PC without Python installed
- ✅ Includes all dependencies (NumPy, OpenCV, DepthAI)
- ✅ Auto-detects OAK-D camera
- ✅ Smart mode switching (wrist rotation ↔ 3-area pointing)
- ✅ Sends UDP messages to Unity/games
- ✅ No environment configuration needed

---

## 🛠️ Prerequisites

### On Build PC (where you create the EXE)

1. **Python 3.10** (recommended)
2. **Git** (to clone repo)
3. **OAK-D Camera** (for testing)
4. **Working wrist_rotation project**

---

## 📋 Step-by-Step Build Process

### Step 1: Prepare Your Project

```powershell
cd C:\Users\s-ridoy_d1\Desktop\wrist_rotation

# Make sure these files exist:
ls src\gesture_oak\detection\rgb_hand_detector.py
ls src\gesture_oak\detection\smart_combined_detector.py
ls src\gesture_oak\detection\HandTracker.py
ls src\gesture_oak\detection\HandTrackerRenderer.py
ls src\gesture_oak\utils\FPS.py
ls src\gesture_oak\utils\mediapipe_utils.py
ls models\palm_detection_sh4.blob
ls models\hand_landmark_lite_sh4.blob
```

All these files should exist!

---

### Step 2: Install PyInstaller

```powershell
# Activate your virtual environment
.venv\Scripts\activate

# Install PyInstaller
pip install pyinstaller

# Verify installation
pyinstaller --version
```

Should show: `5.x.x` or similar

---

### Step 3: Copy Build Files

Download these files and place them in your project root:

1. **[smart_combined_standalone.py](computer:///mnt/user-data/outputs/smart_combined_standalone.py)** 
   → Project root

2. **[smart_combined.spec](computer:///mnt/user-data/outputs/smart_combined.spec)**
   → Project root

3. **[requirements_exe.txt](computer:///mnt/user-data/outputs/requirements_exe.txt)** (optional)
   → Project root

Your directory should look like:
```
wrist_rotation/
├── smart_combined_standalone.py  ← NEW
├── smart_combined.spec            ← NEW
├── requirements_exe.txt           ← NEW
├── main.py
├── models/
│   ├── palm_detection_sh4.blob
│   └── hand_landmark_lite_sh4.blob
└── src/
    └── gesture_oak/
        ├── detection/
        └── utils/
```

---

### Step 4: Build the EXE (Simple Method)

```powershell
cd C:\Users\s-ridoy_d1\Desktop\wrist_rotation

# Build with PyInstaller (ONE FILE)
pyinstaller --onefile --windowed ^
    --name SmartCombinedDetection ^
    --add-data "models;models" ^
    --add-data "src/gesture_oak;gesture_oak" ^
    --hidden-import numpy ^
    --hidden-import cv2 ^
    --hidden-import depthai ^
    smart_combined_standalone.py
```

**Wait 2-5 minutes** while it builds...

---

### Step 5: Build the EXE (Advanced Method - Using .spec file)

For more control, use the spec file:

```powershell
# Edit smart_combined.spec if needed (icon, console, etc.)

# Build using spec file
pyinstaller smart_combined.spec
```

---

### Step 6: Find Your EXE

After build completes:

```powershell
# EXE will be in dist folder
ls dist\

# You should see:
# SmartCombinedDetection.exe  (~200-400 MB)
```

---

### Step 7: Test the EXE

```powershell
cd dist

# Run it
.\SmartCombinedDetection.exe
```

Should show:
```
=====================================
SMART COMBINED DETECTION - STANDALONE
=====================================

🤚 OPEN HAND  → Wrist Rotation Mode
☝  ONE FINGER → 3-Area Pointing Mode
✊ FIST       → Universal gesture

Initializing RGB hand detector...
✓ All systems ready!
```

---

## 📦 Distribution Package

Create a distributable package:

### Create Package Folder

```powershell
mkdir SmartCombinedDetection_Package
cd SmartCombinedDetection_Package

# Copy the EXE
copy ..\dist\SmartCombinedDetection.exe .

# Create README
echo "Smart Combined Detection" > README.txt
echo "" >> README.txt
echo "Double-click SmartCombinedDetection.exe to run" >> README.txt
echo "" >> README.txt
echo "Requirements:" >> README.txt
echo "- Windows 10/11" >> README.txt
echo "- OAK-D Camera connected" >> README.txt
echo "- USB 3.0 port" >> README.txt
```

---

## 🎯 What Users Need

### To Use the EXE on Another PC:

**Requirements:**
1. ✅ Windows 10/11 (64-bit)
2. ✅ OAK-D Camera
3. ✅ USB 3.0 port
4. ❌ NO Python needed
5. ❌ NO environment setup needed
6. ❌ NO pip install needed

**Just:**
1. Copy `SmartCombinedDetection.exe` to any PC
2. Connect OAK-D camera
3. Double-click the EXE
4. Done!

---

## 🔧 Troubleshooting Build Issues

### Issue 1: "Module not found" during build

**Solution:**
```powershell
# Install missing modules
pip install numpy opencv-python depthai

# Rebuild
pyinstaller smart_combined.spec --clean
```

### Issue 2: EXE is too large (>500 MB)

**Solution:**
```powershell
# Use UPX compression (edit smart_combined.spec)
# Change: upx=True

# Or build without debug info
pyinstaller --onefile --strip smart_combined_standalone.py
```

### Issue 3: "Cannot find models" when running EXE

**Solution:**
Make sure models folder is included in build:
```powershell
# Check spec file has:
datas = [
    ('models/*.blob', 'models'),
]

# Rebuild
pyinstaller smart_combined.spec --clean
```

### Issue 4: Console window shows errors

**Solution:**
Run from command line to see full error:
```powershell
cd dist
.\SmartCombinedDetection.exe
```

Copy error message and fix the issue.

---

## 🎨 Customization

### Add Icon

1. Get an `.ico` file (256x256 recommended)
2. Save as `icon.ico` in project root
3. Edit `smart_combined.spec`:
```python
icon='icon.ico',  # This line
```
4. Rebuild

### Hide Console Window

Edit `smart_combined.spec`:
```python
console=False,  # Change from True to False
```

**Warning:** You won't see error messages!

### Add Splash Screen

1. Create `splash.png` (image shown while loading)
2. Place in project root
3. Already configured in spec file!

---

## 📊 Build Comparison

| Method | File Size | Build Time | Portability |
|--------|-----------|------------|-------------|
| Script (.py) | ~100 KB | Instant | ❌ Needs Python |
| EXE (onefile) | ~300 MB | 3-5 min | ✅ Standalone |
| EXE (onedir) | ~400 MB | 2-3 min | ✅ Standalone |

**Recommended:** Use `--onefile` for easiest distribution

---

## 🚀 Quick Build Script

Save this as `build_exe.bat`:

```batch
@echo off
echo ========================================
echo Building Smart Combined Detection EXE
echo ========================================
echo.

echo Activating virtual environment...
call .venv\Scripts\activate

echo.
echo Installing PyInstaller...
pip install pyinstaller

echo.
echo Building EXE (this may take 3-5 minutes)...
pyinstaller smart_combined.spec --clean

echo.
echo ========================================
echo Build Complete!
echo ========================================
echo.
echo EXE location: dist\SmartCombinedDetection.exe
echo.
pause
```

Then just run:
```powershell
.\build_exe.bat
```

---

## 📝 Build Checklist

Before building:
- [ ] All source files in correct locations
- [ ] Model files (.blob) present in models/
- [ ] Virtual environment activated
- [ ] PyInstaller installed
- [ ] Tested code works as Python script first

After building:
- [ ] EXE file created in dist/
- [ ] Test EXE on build PC
- [ ] Copy to different PC and test
- [ ] Verify camera detection works
- [ ] Check UDP messages sending
- [ ] Create distribution package

---

## 💡 Tips

1. **Test First:** Always test your Python script before building EXE
2. **Clean Builds:** Use `--clean` flag if rebuilding
3. **Size Matters:** EXE will be 200-400 MB (normal for bundled app)
4. **Antivirus:** Some antivirus may flag PyInstaller EXEs as suspicious (false positive)
5. **USB Driver:** OAK-D drivers install automatically on first run

---

## 📤 Sharing Your EXE

### Via USB Drive
```
Copy SmartCombinedDetection.exe to USB
→ Plug into target PC
→ Copy EXE to Desktop
→ Double-click to run
```

### Via Cloud
```
Upload to Google Drive / Dropbox
→ Share link
→ Download on target PC
→ Run
```

### Via Network
```
Place on shared network drive
→ Access from any PC
→ Copy locally
→ Run
```

---

## 🎉 Success!

If you see this when running the EXE:
```
✓ RGB Hand Detector initialized
✓ All systems ready!
```

**Congratulations! Your standalone EXE is working!** 🎯

Users can now run Smart Combined Detection on any Windows PC without any setup!

---

## 📚 Additional Resources

- PyInstaller Docs: https://pyinstaller.org/
- DepthAI Docs: https://docs.luxonis.com/
- Troubleshooting: See console output for errors

---

**Need help? Check the console output for specific error messages!**
