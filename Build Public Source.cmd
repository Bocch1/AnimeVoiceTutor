@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build_public_source.ps1" %*
if errorlevel 1 ( echo Public source build failed. & pause & exit /b 1 )
echo Public source build complete.
pause
