@echo off
setlocal
cd /d "%~dp0.."
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\scripts\doctor_source.ps1"
if errorlevel 1 ( echo Preflight failed. & pause & exit /b 1 )
pause
