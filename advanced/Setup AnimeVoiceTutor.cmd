@echo off
setlocal
cd /d "%~dp0.."
if "%~1"=="" (
  call "%~dp0..\First Run Setup.cmd"
  exit /b %ERRORLEVEL%
)
set "role=web"
if /I "%~1"=="all" set "role=all"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\scripts\setup_source.ps1" -Role %role%
if errorlevel 1 ( echo Setup failed. Check messages above. & pause & exit /b 1 )
echo Runtime setup complete. Voice models, licensed reference audio and FFmpeg require separate configuration.
pause
