@echo off
rem Double-click to talk to TARS through Claude Code.
cd /d "%~dp0"
title Claude TARS
python tars_mcp.py --check
if errorlevel 1 (
  echo.
  echo Can't reach TARS. Is it switched on and on the same Wi-Fi?
  pause
  exit /b 1
)
echo.
where claude >nul 2>nul
if errorlevel 1 (
  "%USERPROFILE%\.local\bin\claude.exe"
) else (
  claude
)
