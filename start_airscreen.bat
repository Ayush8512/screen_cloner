@echo off
title AirScreen - Modular Wireless Display & Control Center
cd /d "%~dp0"

if exist "%~dp0AirScreen.exe" (
    start "" "%~dp0AirScreen.exe"
    exit /b
)

echo ================================================================
echo   AIRSCREEN :: WIRELESS DISPLAY & VIRTUAL MONITOR SUITE
echo ================================================================
echo.
echo   [1] Start AirScreen (Modern Desktop GUI + System Tray)
echo   [2] Start AirScreen (Console / Headless Mode)
echo   [3] Install / Enable Virtual Extended Display (Display 2)
echo   [4] Manage Virtual Display Settings (VDD Control GUI)
echo   [5] Build Standalone Windows Executable (.exe)
echo.
set /p opt="Select an option (Press Enter for 1): "

if "%opt%"=="2" (
    echo.
    echo [INFO] Starting AirScreen in Headless / Console Mode...
    python main.py --headless
    exit /b
)

if "%opt%"=="3" (
    call "%~dp0install_driver_admin.bat"
    exit /b
)

if "%opt%"=="4" (
    echo.
    echo [INFO] Launching Virtual Display Driver Control...
    start "" "%~dp0virtual_display_driver\VDD Control.exe"
    exit /b
)

if "%opt%"=="5" (
    echo.
    echo [INFO] Building Standalone Executable with PyInstaller...
    python build_app.py
    pause
    exit /b
)

echo.
echo [INFO] Initializing AirScreen Desktop Control Center...
python main.py
