@echo off
setlocal
cd /d "%~dp0.."
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\scripts\test_source.ps1" %*
if errorlevel 1 ( echo Live smoke test failed. Check the output above. & pause & exit /b 1 )
echo Live smoke test passed.
pause
