@echo off
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [INFO] Requesting Administrator privileges to remove Virtual Display Driver...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

title Remove Virtual Display Driver
cd /d "%~dp0virtual_display_driver"

echo ================================================================
echo   AIRSCREEN :: REMOVING VIRTUAL DISPLAY
echo ================================================================
echo.
"%~dp0virtual_display_driver\Dependencies\devcon.exe" remove Root\MttVDD
echo.
echo [INFO] Virtual display removed successfully.
echo.
pause
