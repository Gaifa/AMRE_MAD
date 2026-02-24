@echo off
REM ============================================================================
REM  MotorCAD Simulation Framework - Quality Check Mode
REM ============================================================================
REM  This script runs simulations with automatic quality checking enabled.
REM  It validates result smoothness and auto-adjusts IM_InitialSlip_MotorLAB
REM  parameter iteratively until smooth torque/power curves are obtained.
REM
REM  Author: MotorCAD Analysis Team
REM  Date: February 2026
REM ============================================================================

echo.
echo ========================================================================
echo  MotorCAD Simulation Framework - QUALITY CHECK MODE
echo ========================================================================
echo.
echo  This mode enables automatic quality validation:
echo  - Checks smoothness of torque and power curves
echo  - Automatically adjusts IM_InitialSlip_MotorLAB if needed
echo  - Iterates until smooth results are obtained
echo.
echo ========================================================================
echo.

REM Change to script directory
cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH!
    echo Please install Python 3.8+ or add it to your PATH.
    pause
    exit /b 1
)

echo Select simulation mode:
echo.
echo 1. Single motor with quality check
echo 2. Motor directory with quality check
echo 3. Motor list file with quality check
echo 4. Custom configuration
echo.
set /p MODE="Enter choice (1-4): "

if "%MODE%"=="1" goto SINGLE_MOTOR
if "%MODE%"=="2" goto DIRECTORY
if "%MODE%"=="3" goto LIST_FILE
if "%MODE%"=="4" goto CUSTOM
echo Invalid choice!
pause
exit /b 1

:SINGLE_MOTOR
echo.
set /p MOTOR_PATH="Enter motor file path (or drag-and-drop .mot file): "
REM Remove quotes if present
set MOTOR_PATH=%MOTOR_PATH:"=%
echo.
echo Running simulation with quality check for:
echo %MOTOR_PATH%
echo.
python scripts/run_simulations_quality_check.py --motor "%MOTOR_PATH%"
goto END

:DIRECTORY
echo.
set /p DIR_PATH="Enter directory path (or drag-and-drop folder): "
REM Remove quotes if present
set DIR_PATH=%DIR_PATH:"=%
echo.
set /p RECURSIVE="Search recursively in subdirectories? (y/n): "
echo.
echo Running simulations with quality check for all motors in:
echo %DIR_PATH%
echo.
if /i "%RECURSIVE%"=="y" (
    python scripts/run_simulations_quality_check.py --directory "%DIR_PATH%" --recursive
) else (
    python scripts/run_simulations_quality_check.py --directory "%DIR_PATH%"
)
goto END

:LIST_FILE
echo.
set /p LIST_PATH="Enter motor list file path (or drag-and-drop .txt file): "
REM Remove quotes if present
set LIST_PATH=%LIST_PATH:"=%
echo.
echo Running simulations with quality check for motors in list:
echo %LIST_PATH%
echo.
python scripts/run_simulations_quality_check.py --list "%LIST_PATH%"
goto END

:CUSTOM
echo.
echo Custom Configuration Mode
echo.
set /p MOTOR_PATH="Motor file/directory path: "
set MOTOR_PATH=%MOTOR_PATH:"=%
set /p MAX_ITER="Max iterations (default 5): "
set /p SLIP_START="Initial slip start (default 0.01): "
set /p SLIP_INC="Slip increment (default 0.02): "
set /p THRESHOLD="Smoothness threshold (default 0.15): "

REM Set defaults if empty
if "%MAX_ITER%"=="" set MAX_ITER=5
if "%SLIP_START%"=="" set SLIP_START=0.01
if "%SLIP_INC%"=="" set SLIP_INC=0.02
if "%THRESHOLD%"=="" set THRESHOLD=0.15

echo.
echo Running with custom parameters:
echo   Max iterations: %MAX_ITER%
echo   Initial slip: %SLIP_START%
echo   Slip increment: %SLIP_INC%
echo   Smoothness threshold: %THRESHOLD%
echo.

python scripts/run_simulations_quality_check.py --motor "%MOTOR_PATH%" --max-iterations %MAX_ITER% --initial-slip %SLIP_START% --slip-increment %SLIP_INC% --smoothness-threshold %THRESHOLD%
goto END

:END
echo.
echo ========================================================================
echo  Quality Check Simulation Complete!
echo ========================================================================
echo.
echo Results are stored in mcad_results.db
echo.
echo Next steps:
echo   - View results: python scripts/view_results.py --list-motors
echo   - Generate reports: Generate_Reports.bat
echo   - Open GUI: Launch_GUI.bat
echo.
pause
