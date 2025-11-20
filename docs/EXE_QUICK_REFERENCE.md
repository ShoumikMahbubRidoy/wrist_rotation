# EXE Build - Quick Reference Card

## 🎯 One-Command Build

```powershell
# Just run this!
.\build_exe.bat
```

Wait 3-5 minutes → Done! ✅

---

## 📋 Manual Build (if script fails)

```powershell
# 1. Activate environment
.venv\Scripts\activate

# 2. Install PyInstaller
pip install pyinstaller

# 3. Build
pyinstaller --onefile --name SmartCombinedDetection --add-data "models;models" --add-data "src\gesture_oak;gesture_oak" smart_combined_standalone.py

# 4. Find EXE
cd dist
```

---

## 📦 What You Get

**File:** `SmartCombinedDetection.exe` (~300 MB)

**Location:** `dist\SmartCombinedDetection.exe`

**Runs on:** Any Windows 10/11 PC (no Python needed!)

---

## ✅ Testing Your EXE

```powershell
cd dist
.\SmartCombinedDetection.exe
```

Should see:
```
✓ RGB Hand Detector initialized
✓ All systems ready!
```

---

## 🚀 Distribution

### Method 1: USB Drive
```
Copy SmartCombinedDetection.exe
→ Give to user
→ They copy to PC
→ Double-click to run
```

### Method 2: Cloud
```
Upload to Google Drive
→ Share link
→ User downloads
→ Run
```

### Method 3: Network Share
```
Place on shared drive
→ Anyone can access
→ Copy and run
```

---

## 💡 What Users Need

**Required:**
- ✅ Windows 10/11
- ✅ OAK-D camera
- ✅ USB 3.0 port

**NOT Required:**
- ❌ Python
- ❌ pip
- ❌ Virtual environment
- ❌ Any installation

**Just:** Connect camera → Run EXE → Done!

---

## 🔧 Troubleshooting

### Build fails?
```powershell
# Clean and retry
pyinstaller smart_combined.spec --clean
```

### "Module not found"?
```powershell
pip install numpy opencv-python depthai
```

### EXE won't run?
```
Run from command line to see errors:
dist\SmartCombinedDetection.exe
```

---

## 📊 File Sizes

| Component | Size |
|-----------|------|
| Python script | ~14 KB |
| Built EXE | ~300 MB |
| Model files | ~10 MB |
| **Total package** | ~310 MB |

The large size is normal - it includes Python + all libraries!

---

## 🎨 Customization

### Add Icon
```python
# In smart_combined.spec:
icon='icon.ico',
```

### Hide Console
```python
# In smart_combined.spec:
console=False,
```

### Change Name
```powershell
pyinstaller --name MyCustomName ...
```

---

## ⚡ Quick Commands

```powershell
# Build
.\build_exe.bat

# Test
dist\SmartCombinedDetection.exe

# Clean
rmdir /s dist build

# Rebuild
pyinstaller smart_combined.spec --clean
```

---

## 📞 Support Checklist

If user reports issue:
1. Check Windows version (needs 10/11)
2. Check camera connection (USB 3.0)
3. Try running from command line (see full error)
4. Check antivirus (might block EXE)
5. Re-download fresh copy

---

## 🎉 Success Indicators

✅ Build completes without errors  
✅ EXE file created in `dist/`  
✅ EXE runs and shows detection window  
✅ Camera initializes successfully  
✅ Hand detection works  
✅ UDP messages send  

**All green? You're ready to distribute!** 🚀

---

**Questions? Check EXE_BUILD_GUIDE.md for detailed instructions!**
