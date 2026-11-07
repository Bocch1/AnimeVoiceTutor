@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\quick_setup.ps1" %*
if errorlevel 1 (
    echo.
    echo Quick setup failed. See the messages above.
    pause
    exit /b 1
)
if "%~1"=="" pause
exit /b 0
