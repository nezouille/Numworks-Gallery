@echo off
setlocal
title Nezu Photo Viewer
powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -File "%~dp0build.ps1"
if errorlevel 1 (
  echo.
  echo Build failed. See the error message above.
)
echo.
pause
