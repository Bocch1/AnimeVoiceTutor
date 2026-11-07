@echo off
setlocal
cd /d "%~dp0.."
if "%~1"=="" (
  echo To reuse your current installation, run:
  echo Use Existing Models.cmd "FULL_PATH_TO_EXISTING_PROJECT"
  echo You can specify ASR/TTS Python or model paths using optional parameters.
  pause
  exit /b 2
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\scripts\reuse_existing_installation.ps1" -ExistingProjectRoot "%~1"
if errorlevel 1 ( echo Linking failed. & pause & exit /b 1 )
pause
