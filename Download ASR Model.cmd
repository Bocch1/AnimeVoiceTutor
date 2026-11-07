@echo off
setlocal
cd /d "%~dp0"
set "size=0.6B"
if /I "%~1"=="1.7B" set "size=1.7B"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\download_asr_model.ps1" -Model %size%
if errorlevel 1 ( echo ASR model download failed. & pause & exit /b 1 )
echo ASR model is available.
pause
