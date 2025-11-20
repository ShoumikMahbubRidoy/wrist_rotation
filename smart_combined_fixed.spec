# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Spec File for Smart Combined Detection
FIXED VERSION - No splash screen, proper depthai bundling
"""

block_cipher = None

# List of all data files to include
datas = [
    # Model files
    ('models/*.blob', 'models'),
    
    # Source files
    ('src/gesture_oak/detection/*.py', 'gesture_oak/detection'),
    ('src/gesture_oak/utils/*.py', 'gesture_oak/utils'),
]

# Hidden imports that PyInstaller might miss
hiddenimports = [
    'numpy',
    'cv2',
    'depthai',
    'socket',
    'pathlib',
    'collections',
    'enum',
    'math',
    'time',
    'usb',
    'usb.core',
    'usb.util',
    'usb.backend',
    'usb.backend.libusb1',
    'gesture_oak',
    'gesture_oak.detection',
    'gesture_oak.detection.rgb_hand_detector',
    'gesture_oak.detection.smart_combined_detector',
    'gesture_oak.detection.HandTracker',
    'gesture_oak.detection.HandTrackerRenderer',
    'gesture_oak.utils',
    'gesture_oak.utils.FPS',
    'gesture_oak.utils.mediapipe_utils',
]

a = Analysis(
    ['smart_combined_standalone.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyt = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyt,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SmartCombinedDetection',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Keep console for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
