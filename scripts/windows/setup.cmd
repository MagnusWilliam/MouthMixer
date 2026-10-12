@echo off
rem Double-click to set up MouthMixer (runs setup.ps1 without changing your PowerShell policy).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1" %*
pause
