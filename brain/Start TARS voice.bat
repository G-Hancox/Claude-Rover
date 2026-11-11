@echo off
rem Double-click for hands-free TARS: say "Hey TARS", then talk. Leave this window open.
cd /d "%~dp0"
title Claude TARS - voice
python tars_voice.py
pause
