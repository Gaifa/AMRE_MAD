@echo off
REM MotorCAD Performance Report Generator
REM Generates PDF reports for all motors in the database

echo ========================================
echo MotorCAD Performance Report Generator
echo ========================================
echo.
echo Generating PDF reports for all motors...
echo This may take a few minutes depending on the number of motors.
echo.

python scripts\generate_performance_reports.py

if errorlevel 1 (
    echo.
    echo ERROR: Failed to generate reports
    echo Please check that:
    echo   - Database file exists (mcad_results.db)
    echo   - Required packages are installed: pip install reportlab matplotlib
    echo   - Motor types config file exists (motor_types_config.json)
    echo.
    pause
) else (
    echo.
    echo ========================================
    echo Reports generated successfully!
    echo Check the 'generated_pdfs' folder
    echo ========================================
    echo.
    pause
)
