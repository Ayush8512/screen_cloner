@echo off
title AirScreen - Modular Wireless Display Server
cd /d "%~dp0"

echo ================================================================
echo   AIRSCREEN :: MODULAR WIRELESS DISPLAY AND VIRTUAL MONITOR
echo ================================================================
echo.
echo   [1] Start Wireless Display Server
echo   [2] Install / Enable Virtual Extended Display (Display 2)
echo   [3] Manage Virtual Display Settings (VDD Control GUI)
echo.
set /p opt="Select an option (Press Enter for 1): "

if "%opt%"=="2" (
    call "%~dp0install_driver_admin.bat"
    exit /b
)

if "%opt%"=="3" (
    echo.
    echo [INFO] Launching Virtual Display Driver Control...
    start "" "%~dp0virtual_display_driver\VDD Control.exe"
    exit /b
)

echo.
echo [INFO] Initializing AirScreen Server...
python main.py
pause
