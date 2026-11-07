@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_source.ps1" %*
set "result=%ERRORLEVEL%"
if not "%result%"=="0" (
  echo.
  echo AnimeVoiceTutor exited with code %result%. Check data\logs.
  pause
)
exit /b %result%
