@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0scripts\quick_setup.ps1" (
  echo ERROR: Incomplete Core directory. The patch payload is not an installation folder.
  echo Extract the complete AnimeVoiceTutor Core ZIP and run First Run Setup.cmd from its root.
  pause
  exit /b 2
)
if not exist "%~dp0release\public_source_files.txt" (
  echo ERROR: Missing source manifest. Extract the complete Core ZIP.
  pause
  exit /b 2
)
if not exist "%~dp0packages\updates" mkdir "%~dp0packages\updates"
if not exist "%~dp0packages\characters" mkdir "%~dp0packages\characters"
powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0scripts\first_run_gui.ps1"
if errorlevel 1 (
  echo.
  echo First-run setup did not complete. Check the messages above.
  pause
)
exit /b %ERRORLEVEL%
