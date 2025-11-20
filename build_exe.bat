@echo off
REM ============================================
REM Smart Combined Detection - FIXED EXE Builder
REM Properly includes depthai module
REM ============================================

echo.
echo ╔═══════════════════════════════════════════════════════════╗
echo ║   Smart Combined Detection - Fixed EXE Builder            ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.

REM Check virtual environment
if not exist ".venv\Scripts\activate.bat" (
    echo ❌ Error: Virtual environment not found!
    pause
    exit /b 1
)

echo [1/6] Activating virtual environment...
call .venv\Scripts\activate
echo ✓ Virtual environment activated

echo.
echo [2/6] Installing required packages...
pip install pyinstaller pyusb --quiet
echo ✓ Packages installed

echo.
echo [3/6] Checking files...
if not exist "smart_combined_standalone.py" (
    echo ❌ smart_combined_standalone.py not found!
    pause
    exit /b 1
)
if not exist "models\palm_detection_sh4.blob" (
    echo ❌ Model files not found!
    pause
    exit /b 1
)
echo ✓ Files OK

echo.
echo [4/6] Cleaning previous builds...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
echo ✓ Cleaned

echo.
echo [5/6] Building EXE (3-5 minutes)...
echo.

REM Build with explicit includes for depthai
pyinstaller --onefile ^
    --name SmartCombinedDetection ^
    --add-data "models;models" ^
    --add-data "src\gesture_oak;gesture_oak" ^
    --hidden-import numpy ^
    --hidden-import cv2 ^
    --hidden-import depthai ^
    --hidden-import usb ^
    --hidden-import usb.core ^
    --hidden-import usb.util ^
    --hidden-import usb.backend ^
    --hidden-import usb.backend.libusb1 ^
    --collect-all depthai ^
    --console ^
    smart_combined_standalone.py

if errorlevel 1 (
    echo.
    echo ❌ Build failed!
    pause
    exit /b 1
)

echo.
echo [6/6] Verifying...
if exist "dist\SmartCombinedDetection.exe" (
    echo.
    echo ═══════════════════════════════════════════════════════════
    echo  ✅ BUILD SUCCESSFUL!
    echo ═══════════════════════════════════════════════════════════
    echo.
    echo  📦 Output: dist\SmartCombinedDetection.exe
    for %%A in ("dist\SmartCombinedDetection.exe") do echo  📊 Size: %%~zA bytes (approx %%~zA/1048576 MB)
    echo.
    echo  🎯 To test: cd dist ^&^& SmartCombinedDetection.exe
    echo.
    echo ═══════════════════════════════════════════════════════════
) else (
    echo ❌ EXE not found!
)

echo.
pause
