@echo off
REM Setup Models for Smart Combined Detection
REM Run this once on each new PC

echo ╔═══════════════════════════════════════════════════════════╗
echo ║   Smart Combined Detection - First Time Setup            ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.

echo Copying model files to temporary folder...
echo.

REM Create temp models folder
set TEMP_MODELS=%TEMP%\models
if not exist "%TEMP_MODELS%" mkdir "%TEMP_MODELS%"

REM Copy models
copy /Y models\*.blob "%TEMP_MODELS%\" >nul 2>&1

if errorlevel 1 (
    echo ❌ Failed to copy models
    echo.
    echo Try running as Administrator
    pause
    exit /b 1
)

echo ✓ Models copied to: %TEMP_MODELS%
echo.
echo ═══════════════════════════════════════════════════════════
echo  Setup Complete!
echo ═══════════════════════════════════════════════════════════
echo.
echo You can now run SmartCombinedDetection.exe
echo.
pause
