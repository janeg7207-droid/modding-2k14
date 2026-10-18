@echo off
cd /d "%~dp0"
py -3 mod_formatter.py --ps3
if errorlevel 1 (
  echo If Python is missing, install Python 3.10+ with Tcl/Tk and the Python launcher.
  pause
)
