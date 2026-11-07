@echo off
setlocal
cd /d "%~dp0"
rem Normal double-click usage is quiet and opens the desktop-style Web window.
rem Advanced command-line switches retain the existing console diagnostic path.
if not "%~1"=="" goto console
if not exist "%~dp0scripts\desktop_start.vbs" goto missing
where wscript.exe >nul 2>nul
if errorlevel 1 goto no_wscript
start "" wscript.exe "%~dp0scripts\desktop_start.vbs"
exit /b 0
:no_wscript
rem Windows Script Host can be disabled on managed PCs. Use hidden PowerShell instead.
start "" powershell.exe -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "%~dp0scripts\desktop_start.ps1"
exit /b 0
:console
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_source.ps1" %*
set "result=%ERRORLEVEL%"
if not "%result%"=="0" (
  echo AnimeVoiceTutor startup returned code %result%. See data\logs.
  pause
)
exit /b %result%
:missing
echo ERROR: Desktop launcher missing. Check the installed Core files.
pause
exit /b 2
