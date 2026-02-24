@echo off
REM MotorCAD Simulation Framework - GUI Launcher
REM Double-click this file to start the graphical interface

echo ========================================
echo MotorCAD Simulation Framework
echo ========================================
echo.
echo Starting GUI application...
echo.

python scripts\gui_main.py

if errorlevel 1 (
    echo.
    echo ERROR: Failed to launch GUI
    echo Please check that Python is installed and in your PATH
    echo.
    pause
)
