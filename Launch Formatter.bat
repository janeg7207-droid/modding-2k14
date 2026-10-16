@echo off
cd /d "%~dp0"
py -3 mod_formatter.py
if errorlevel 1 (
  echo If Python is missing, install Python 3.10+ from python.org with Tcl/Tk and the Python launcher.
  pause
)
