# Quality Check Feature - Summary of Changes

## Overview
Added automatic quality checking system that validates simulation result smoothness and iteratively adjusts IM_InitialSlip_MotorLAB parameter until smooth torque/power curves are obtained.

## New Files Created

### 1. Core Implementation
- **Modified**: `src/mcad_interface.py`
  - Added `check_results_smoothness()` function
  - Added `run_and_load_with_quality_check()` function
  - Updated `run_mcad_simulation()` to accept `initial_slip` parameter
  - Updated `run_and_load()` to accept `initial_slip` parameter

- **Modified**: `src/config.py`
  - Added `QUALITY_CHECK_MAX_ITERATIONS = 5`
  - Added `QUALITY_CHECK_INITIAL_SLIP_START = 0.01`
  - Added `QUALITY_CHECK_SLIP_INCREMENT = 0.02`
  - Added `QUALITY_CHECK_MAX_SLIP = 0.20`
  - Added `QUALITY_CHECK_SMOOTHNESS_THRESHOLD = 0.15`

### 2. Scripts and Launchers
- **Created**: `scripts/run_simulations_quality_check.py`
  - Command-line interface for running simulations with quality check
  - Supports single motor, directory, and list modes
  - Custom quality check parameters via command-line arguments

- **Created**: `Run_With_Quality_Check.bat`
  - Windows batch launcher for quality check mode
  - Interactive menu for different simulation modes
  - Custom parameter configuration

- **Created**: `example_quality_check.py`
  - Python code examples demonstrating quality check usage
  - Shows 4 different usage patterns

### 3. Documentation
- **Updated**: `README.md`
  - Added quality checking to features list
  - Added complete "Automatic Quality Checking" section with:
    - How it works explanation
    - Configuration parameters
    - Usage examples (Python, CLI, Batch)
    - Example output
    - When to use guidance
  - Updated project structure to include new files

- **Updated**: `PROJECT_INSTRUCTIONS.md`
  - Added quality check functions to mcad_interface.py section
  - Added quality check parameters to config.py section
  - Added `run_simulations_quality_check.py` to executable scripts section
  - Updated project structure diagram
  - Added technical details about CV calculation and workflow

## Key Features

### Smoothness Metric
- Uses Coefficient of Variation (CV) of consecutive differences
- CV = std(diff(values)) / mean(abs(values))
- Lower CV = smoother curves
- Default threshold: 0.15 (15%)

### Iterative Algorithm
1. Run simulation with current initial_slip
2. Calculate CV for torque and power
3. If smooth (CV < threshold) → success
4. If not smooth → increase initial_slip and retry
5. Repeat until smooth or max_iterations reached

### Configuration Options
All parameters are configurable via:
- Python function arguments
- Command-line arguments
- config.py constants (defaults)

## Usage Examples

### Python API
```python
from src import mcad_interface

# Basic usage (default parameters)
results = mcad_interface.run_and_load_with_quality_check(
    mcad, voltage, current_density, motor_dict, model_dict, mot_file_path
)

# Custom parameters
results = mcad_interface.run_and_load_with_quality_check(
    mcad, voltage, current_density, motor_dict, model_dict, mot_file_path,
    max_iterations=10,
    initial_slip_start=0.02,
    slip_increment=0.03,
    smoothness_threshold=0.10
)
```

### Command Line
```bash
# Basic
python scripts/run_simulations_quality_check.py --motor "motor.mot"

# Custom parameters
python scripts/run_simulations_quality_check.py --motor "motor.mot" \
    --max-iterations 10 --initial-slip 0.02 --slip-increment 0.03
```

### Windows Batch
```batch
Run_With_Quality_Check.bat
```

## Performance Impact
- Adds ~2-5x time per simulation (typically)
- Depends on how many iterations needed
- Trade-off: Better quality vs longer simulation time

## When to Use
**Use Quality Check For:**
- New motor designs
- Complex geometries
- Professional reports requiring smooth curves
- Motors showing oscillating results

**Standard Mode Sufficient For:**
- Previously validated motors
- Quick parameter sweeps
- Batch processing where time is critical

## Testing
To test the feature:
1. Run `example_quality_check.py` for Python API examples
2. Run `Run_With_Quality_Check.bat` for interactive mode
3. Run `python scripts/run_simulations_quality_check.py --motor "path/to/motor.mot"`

---
**Date**: February 21, 2026  
**Author**: MotorCAD Analysis Team
