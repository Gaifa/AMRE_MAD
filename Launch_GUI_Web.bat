@echo off
REM MotorCAD Simulation Framework - Web GUI Launcher
REM Double-click this file to start the web interface

echo ========================================
echo MotorCAD Simulation Framework
echo Web Interface (No tkinter required)
echo ========================================
echo.
echo Starting web server...
echo Your browser will open automatically.
echo.
echo Press Ctrl+C to stop the server
echo.

python scripts\gui_web.py

if errorlevel 1 (
    echo.
    echo ERROR: Failed to launch web GUI
    echo Install Flask with: pip install flask
    echo.
    pause
)
