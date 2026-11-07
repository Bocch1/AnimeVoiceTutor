@echo off
setlocal
cd /d "%~dp0.."
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\scripts\verify_source_tests.ps1"
if errorlevel 1 ( echo Source verification failed. & pause & exit /b 1 )
echo Source verification complete.
pause
