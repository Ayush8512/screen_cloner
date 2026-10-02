@echo off
:: Request Administrator privileges automatically
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [INFO] Requesting Administrator privileges to install Virtual Display Driver...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

title Install Virtual Display Driver (Display 2)
cd /d "%~dp0virtual_display_driver"

echo ================================================================
echo   AIRSCREEN :: INSTALLING VIRTUAL DISPLAY (DISPLAY 2)
echo ================================================================
echo.
echo [1/2] Installing signed driver into Windows Driver Store...
pnputil /add-driver "%~dp0virtual_display_driver\SignedDrivers\x86\VDD\MttVDD.inf" /install

echo.
echo [2/2] Registering Virtual Display Device in Windows...
"%~dp0virtual_display_driver\Dependencies\devcon.exe" install "%~dp0virtual_display_driver\SignedDrivers\x86\VDD\MttVDD.inf" Root\MttVDD

echo.
echo ================================================================
echo   INSTALLATION COMPLETE!
echo   Display 2 is now active in Windows.
echo ================================================================
echo.
echo NEXT STEPS:
echo   1. Press [Windows Key + P] on your keyboard.
echo   2. Select "Extend".
echo   3. Run start_airscreen.bat (Option 1).
echo.
pause
