# AMRE_MAD — MotorCAD Simulation Framework

A comprehensive Python framework for automated MotorCAD electromagnetic simulations with intelligent result caching and batch processing capabilities.

> **Requires Windows + a licensed MotorCAD installation** (COM automation via `pywin32`).

## 🎯 Features

- **Graphical User Interface**: Easy-to-use GUI for all operations
- **Web-Based Interface**: Alternative GUI that works in any browser (no tkinter needed)
- **PDF Report Generation**: Automatic performance reports for all motor types
- **Automatic Quality Checking**: Validates result smoothness and auto-adjusts parameters (NEW!)
- **Batch Motor Processing**: Simulate multiple motors with a single command
- **Intelligent Caching**: Automatically detects and skips previously simulated motors
- **Database Storage**: SQLite database for organized result storage and retrieval
- **Flexible Configuration**: Customize simulation parameters via JSON or Python
- **Performance Curves**: Extract and store torque, power, efficiency vs. speed
- **Multi-Voltage/Current Sweep**: Test motors across multiple operating points
- **Interactive Plotting**: Visualize performance curves directly in the GUI
- **Robust Error Handling**: Graceful handling of missing files and simulation errors

## 📁 Project Structure

```
AMRE_MAD/
├── src/                          # Core library modules
│   ├── __init__.py
│   ├── config.py                # Dynamic paths & constants (no hardcoding!)
│   ├── database.py              # SQLite management
│   ├── mcad_interface.py        # MotorCAD COM automation
│   ├── motor_analyzer.py        # Analysis orchestration
│   └── utils.py
│
├── scripts/                      # Entry-point scripts
│   ├── gui_main.py              # Desktop GUI (Tkinter)
│   ├── gui_web.py               # Web GUI (Flask)
│   ├── run_simulations.py       # CLI batch runner
│   ├── run_simulations_quality_check.py  # CLI with quality checking
│   ├── view_results.py          # Results viewer (CLI)
│   └── generate_performance_reports.py  # PDF report generator
│
├── motors/                       # Motor definition files (.mot)
│
├── config/                       # Configuration JSON files
│   ├── motor_types_config.json
│   └── full_simulation_config.json
│
├── examples/                     # Example configs and usage scripts
│   ├── example_config.json
│   ├── example_motor_list.txt
│   └── example_quality_check.py
│
├── docs/                         # Extended documentation
│   ├── CHANGELOG.md
│   ├── PROJECT_INSTRUCTIONS.md
│   ├── QUALITY_CHECK_FEATURE.md
│   ├── README_GUI_WEB.md
│   └── README_PDF_REPORTS.md
│
├── tools/                        # Standalone utilities & sizing scripts
├── vario/                        # Assets, templates and legacy scripts
├── TEMPLATE/                     # Report document templates
├── datasheet competitor/         # Reference competitor datasheets
│
├── mcad_results.db               # Auto-created results database (gitignored)
├── requirements.txt
├── LICENSE
├── CONTRIBUTING.md
├── README.md
├── Launch_GUI.bat                # Double-click launcher
├── Launch_GUI_Web.bat
├── Generate_Reports.bat
└── Run_With_Quality_Check.bat
```

## 🚀 Quick Start

### Prerequisites

- **Windows OS** (required for MotorCAD COM automation)
- **MotorCAD** installed and licensed
- **Python 3.8+**

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Gaifa/AMRE_MAD.git
   cd AMRE_MAD
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify installation**:
   ```bash
   python scripts/run_simulations.py --help
   `Quick Start with GUI (Recommended)

**Launch the graphical interface**:
*Option 1 - Double-click launcher (Windows):*
```
Launch_GUI.bat
```

*Option 2 - Command line:*```bash
python scripts/gui_main.py
```

The GUI provides four main tabs:
- **Run Simulations**: Select motors and execute batch simulations
- **View Results**: Browse motors in database and view run details
- **Plot Results**: Generate interactive performance curves
- **About**: Application information and help

### Basic Usage (Command Line)

### Basic Usage

#### Simulate a Single Motor

```bash
python scripts/run_simulations.py --motor "motors/D106 H65 25sp DT ( 2x0.63 + 2x0.5 ).mot"
```

#### Simulate Multiple Motors from List

Create a text file `motors_to_simulate.txt`:
```
motors/D106 H65 25sp DT ( 2x0.63 + 2x0.5 ).mot
motors/D135 H100 12sp DT ( 2x0.9 + 2x0.8 ).mot
motors/D150 H120 6sp DT ( 8x0.9 ).mot
```

Run simulations:
```bash
python scripts/run_simulations.py --list motors_to_simulate.txt
```

#### Simulate All Motors in Directory

```bash
python scripts/run_simulations.py --directory "Motori"
```

With recursive search:
```bash
python scripts/run_simulations.py --directory "Motori" --recursive
```

#### Dry Run (Preview Without Simulating)

```bash
python scripts/run_simulations.py --directory "Motori" --dry-run
```

## ⚙️ Configuration

### Default Configuration

The default configuration is defined in `src/config.py`:

```python
DEFAULT_MODEL_DICT = {
    'Maximum speed': 5000,              # rpm
    'Minimum speed': 50,                # rpm
    'Maximum current density': 15,      # A/mm²
    'Battery voltage': [24, 48, 80, 96, 120, 144],  # V
    'Current density': [4, 4.5, 5, 5.5, 7, 7.5, 8, 13]  # A/mm²
}
```

### Custom Configuration

Create a JSON file (e.g., `my_config.json`):

```json
{
    "Maximum speed": 6000,
    "Minimum speed": 100,
    "Maximum current density": 20,
    "Battery voltage": [48, 96, 144],
    "Current density": [5, 10, 15]
}
```

Use it:
```bash
python scripts/run_simulations.py --motor "motor.mot" --config my_config.json
```

## 🎯 Automatic Quality Checking (NEW!)

The framework now includes an intelligent quality checking system that automatically validates the smoothness of torque and power simulation results.

### How It Works

When simulations produce non-smooth or oscillating torque/power curves, it often indicates convergence issues. The quality checker:

1. **Analyzes Results**: Calculates the coefficient of variation (CV) of differences between consecutive points in torque and power curves
2. **Validates Smoothness**: Compares CV against configurable threshold (default: 15%)
3. **Auto-Adjusts Parameters**: If results aren't smooth, automatically increases `IM_InitialSlip_MotorLAB` parameter
4. **Iterates Until Smooth**: Repeats simulation with adjusted parameters until smooth results are obtained

### Quality Check Configuration

In `src/config.py`, the following parameters control the quality checking behavior:

```python
# Maximum iterations to attempt for smooth results
QUALITY_CHECK_MAX_ITERATIONS = 5

# Starting value for IM_InitialSlip_MotorLAB
QUALITY_CHECK_INITIAL_SLIP_START = 0.01

# Amount to increase slip each iteration
QUALITY_CHECK_SLIP_INCREMENT = 0.02

# Maximum slip value (safety limit)
QUALITY_CHECK_MAX_SLIP = 0.20

# Smoothness threshold (coefficient of variation)
# Lower = stricter, Higher = more permissive
QUALITY_CHECK_SMOOTHNESS_THRESHOLD = 0.15
```

### Using Quality Checking

**In Python:**
```python
from src import mcad_interface

# Standard simulation (no quality checking)
results = mcad_interface.run_and_load(mcad, voltage, current_density, 
                                      motor_dict, model_dict, mot_file_path)

# With automatic quality checking (recommended)
results = mcad_interface.run_and_load_with_quality_check(
    mcad, voltage, current_density, motor_dict, model_dict, mot_file_path
)

# With custom parameters
results = mcad_interface.run_and_load_with_quality_check(
    mcad, voltage, current_density, motor_dict, model_dict, mot_file_path,
    max_iterations=10,              # Try up to 10 times
    initial_slip_start=0.02,        # Start with higher slip
    slip_increment=0.03,            # Increase more aggressively
    smoothness_threshold=0.10       # Stricter smoothness requirement
)
```

**Command Line:**
```bash
# Run simulations with quality checking enabled
python scripts/run_simulations_quality_check.py --motor "motor.mot"

# Directory with recursive search
python scripts/run_simulations_quality_check.py --directory "Motori" --recursive

# From motor list file
python scripts/run_simulations_quality_check.py --list "motors_list.txt"

# With custom quality parameters
python scripts/run_simulations_quality_check.py --motor "motor.mot" \
    --max-iterations 10 --initial-slip 0.02 --slip-increment 0.03
```

**Batch Script:**
```bash
# Use the dedicated quality check launcher (Windows)
Run_With_Quality_Check.bat
```

### Example Output

```
======================================================================
Starting simulation with quality checking
  Voltage: 48V, Current Density: 7 A/mm²
  Initial Slip Range: 0.01 to 0.20
  Smoothness Threshold: 0.15
======================================================================

--- Iteration 1/5 ---
Trying IM_InitialSlip_MotorLAB = 0.0100
✗ Results not smooth: Torque CV=0.2341, Power CV=0.1876 (threshold=0.15)

--- Iteration 2/5 ---
Trying IM_InitialSlip_MotorLAB = 0.0300
✓ Results are smooth: Torque CV=0.0892, Power CV=0.1124

======================================================================
✓ SUCCESS: Smooth results obtained after 2 iteration(s)
  Final IM_InitialSlip_MotorLAB: 0.0300
  Torque CV: 0.0892
  Power CV: 0.1124
======================================================================
```

### When to Use Quality Checking

**Use quality checking when:**
- Simulating new motor designs
- Working with motors that have challenging geometries
- You need reliable, smooth performance curves for reports
- Previous simulations showed oscillating results

**Standard simulation may suffice when:**
- Re-running previously validated motors
- Quick parameter sweeps where exact smoothness isn't critical
- Batch processing large numbers of motors (quality check adds ~2-5x time)

### Transactional Behavior and Failure Logging

The quality check system implements **transactional behavior** for database operations:

- **All-or-Nothing Policy**: If ANY run fails quality check for a motor, NO runs are saved to the database for that motor
- **Automatic Failure Logging**: All failures are logged to a timestamped log file
- **Detailed Tracking**: Log includes motor paths, failed runs, initial/final slip values, and failure reasons

**Log File Format:**
```
quality_check_log_YYYYMMDD_HHMMSS.txt
```

**Log Contents:**
```
================================================================================
MOTORCAD QUALITY CHECK SIMULATION LOG - FAILURES DETECTED
================================================================================
Date: 2026-02-27 14:30:45
Total motors with failures: 2
================================================================================

################################################################################
FAILED MOTOR #1
################################################################################

Motor Path: C:\Users\...\D106 H65 40sp DT ( 1x0.9 ).mot
Number of failed runs: 2

--------------------------------------------------------------------------------
FAILED RUNS DETAILS:
--------------------------------------------------------------------------------

  Run #1:
    Voltage: 48 V
    Current Density: 13.0 A/mm²
    Initial Slip (start): 0.0100
    Initial Slip (final): 0.0900
    Iterations attempted: 5
    Reason: Max iterations (5) reached without smooth results
    Final Torque CV: 0.2156
    Final Power CV: 0.1923

  Run #2:
    Voltage: 96 V
    Current Density: 8.0 A/mm²
    Initial Slip (start): 0.0100
    Initial Slip (final): 0.0700
    Iterations attempted: 4
    Reason: Max iterations (5) reached without smooth results
    Final Torque CV: 0.1842
    Final Power CV: 0.1678

================================================================================
END OF LOG
================================================================================
```

**Benefits:**
- **Data Integrity**: Prevents partial/inconsistent data in database
- **Traceability**: Complete audit trail of failures
- **Debugging**: Detailed information for troubleshooting problematic motors
- **Efficiency**: Easy identification of motors requiring parameter adjustment

## 🗄️ Database Schema

The framework uses SQLite with two main tables:

### `motors` Table
Stores unique motor configurations identified by SHA256 hash.

| Column       | Type    | Description                           |
|-------------|---------|---------------------------------------|
| id          | INTEGER | Primary key                           |
| motor_hash  | TEXT    | SHA256 hash of motor configuration    |
| motor_json  | TEXT    | Full motor parameters as JSON         |
| created_at  | TEXT    | Timestamp (ISO 8601)                  |

### `runs` Table
Stores simulation results for each motor/voltage/current_density combination.

| Column                              | Type    | Description                    |
|------------------------------------|---------|--------------------------------|
| id                                 | INTEGER | Primary key                    |
| motor_id                           | INTEGER | Foreign key to motors table    |
| voltage                            | REAL    | Battery voltage [V]            |
| current_density                    | REAL    | Current density [A/mm²]        |
| Shaft_Torque                       | BLOB    | Torque curve (numpy array)     |
| Speed                              | BLOB    | Speed points (numpy array)     |
| Shaft_Power                        | BLOB    | Power curve (numpy array)      |
| Voltage_Phase_RMS                  | BLOB    | Phase voltage curve            |
| Stator_Current_Line_RMS            | BLOB    | Line current curve             |
| Power_Factor_From_Power_Balance    | BLOB    | Power factor curve             |
| Efficiency                         | BLOB    | Efficiency curve               |
| Frequency                          | BLOB    | Frequency curve                |
| DC_Bus_Voltage                     | BLOB    | DC bus voltage curve           |
| created_at                         | TEXT    | Timestamp                      |

## 🧠 How It Works

### Intelligent Caching Algorithm

1. **Motor Identification**: Each motor is uniquely identified by a hash of its parameters
2. **First-Run Comparison**: For each voltage, the first current density point is simulated
3. **Database Check**: Results are compared with existing database entries
4. **Decision**:
   - If results **match**: Skip all other current densities for this voltage
   - If results **differ** or **missing**: Run full sweep and save all results

This approach significantly reduces simulation time for repeated runs while ensuring data integrity.

### Simulation Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                     Load Motor File (.mot)                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Extract Motor Parameters (COM API)                 │
│  • Geometry (diameter, length, slots, poles)                    │
│  • Winding (turns, CSA, connection, parallel paths)             │
│  • Compute Equivalent CSA                                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Check/Build MotorLAB Model                         │
│  • Verify build speed and current are sufficient                │
│  • Rebuild if necessary                                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Compute Motor Hash (SHA256)                        │
│  • Unique identifier based on motor parameters                  │
│  • Check if motor exists in database                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
               ┌─────────────┴─────────────┐
               │  For Each Voltage         │
               └─────────────┬─────────────┘
                             │
                             ▼
       ┌─────────────────────────────────────────────┐
       │  Simulate First Current Density             │
       └─────────────────┬───────────────────────────┘
                         │
                         ▼
       ┌─────────────────────────────────────────────┐
       │  Database Entry Exists?                     │
       └──────┬──────────────────────┬───────────────┘
              │ NO                   │ YES
              │                      │
              ▼                      ▼
    ┌──────────────────┐   ┌────────────────────────┐
    │ Run Full Sweep   │   │ Compare Results        │
    │ All Current      │   └─────────┬──────────────┘
    │ Densities        │             │
    └────┬─────────────┘    ┌────────┴────────┐
         │                  │ Match? │ Differ? │
         │                  └────┬────┴────┬────┘
         │                       │         │
    �️ Using the Graphical Interface

### Starting the GUI

```bash
python scripts/gui_main.py
```

### GUI Features

#### 1. Run Simulations Tab

**Motor Selection:**
- **Single Motor**: Select one .mot file using file dialog
- **Directory**: Select a folder containing .mot files (with recursive option)
- **Load List**: Load motor paths from a text file

**Configuration:**
- Edit simulation parameters directly in the GUI
- Load/save custom configurations from/to JSON files
- Reset to default values with one click

**Execution:**
- Real-time log display during simulations
- Background processing keeps GUI responsive
- Automatic progress reporting and error handling

#### 2. View Results Tab

**Motor Database Browser:**
- View all motors with key parameters:
  - Stator diameter (mm)
  - Axial length (mm)
  - Number of turns per coil
  - Winding connection type (Star/Delta)
  - Creation timestamp
- Select a motor to view detailed run information
- Refresh database listing at any time

#### 3. Plot Results Tab

**Interactive Plotting:**
- Enter Motor ID, Voltage, and Current Density
- Select plot type:
  - Torque-Speed curve
  - Power-Speed curve
  - Efficiency-Speed curve
  - All curves (3 subplots)
- Plots update instantly in the GUI
- Export plots using matplotlib toolbar

#### 4. About Tab

Contains application information, usage guide, and support details.

### GUI Tips

- Use the **View Results** tab to find Motor IDs for plotting
- The status bar at tfor SQLite (External Tool)

For advanced database exploration:

1. Download **DB Browser for SQLite** (free): https://sqlitebrowser.org/
2. Open `mcad_results.db`
3. Browse tables, run SQL queries, export data

**Note**: The built-in GUI (gui_main.py) provides motor viewing and plotting without additional tools.

## 📄 Generating Performance Reports (PDF)

The framework includes an automated PDF report generator that creates professional performance reports for all motors in the database.

### Motor Type Configuration

The system supports three motor types, each with different duty cycles and current densities:

- **FL** (Floor Cleaning): Lower current densities for continuous operation
- **MC** (Material Handling / Cart): Medium to high current densities
- **MV** (Material Handling / Vehicle): Optimized for vehicle applications

Configuration is defined in `motor_types_config.json`:

```json
{
    "motor_types": {
        "FL": {
            "duties": {
                "S1": {"current_density": 4.0, "duration_min": "continuous"},
                "S2-60min": {"current_density": 4.5, "duration_min": 60},
                "S2-20min": {"current_density": 5.0, "duration_min": 20},
                "S2-5min": {"current_density": 5.5, "duration_min": 5}
            }
        },
        "MC": { ... },
        "MV": { ... }
    }
}
```

### Generating Reports

**Quick Start (Windows):**
```bash
# Double-click:
Generate_Reports.bat
```

**Command Line:**
```bash
# Generate reports for all motors
python scripts/generate_performance_reports.py

# Generate report for specific motor
python scripts/generate_performance_reports.py --motor-id 1

# Custom options
python scripts/generate_performance_reports.py --db custom.db --output my_reports/
```

### Report Features

Each PDF report includes:

1. **Header Section**
   - Motor model designation
   - Motor type (FL/MC/MV)
   - Battery voltage
   - Date and revision

2. **General Data Table**
   - Battery voltage
   - Number of poles
   - Connection type (Star/Delta)
   - Temperature ratings
   - IP class

3. **Rated Performance Table**
   - Performance data for all duty cycles (S1, S2-60min, S2-20min, S2-5min)
   - Torque, Power, Speed, Efficiency
   - Motor current and voltage at maximum power point

4. **Performance Curves (Page 2)**
   - **Torque vs Speed**: Solid lines, different colors per duty
   - **Power vs Speed**: Dashed lines, same colors as corresponding torque curves
   - Legend with duty cycle labels
   - Professional formatting with grid and labels

### Report Naming Convention

PDFs are named according to this pattern:
```
{Type}_performance_report_D{diameter}_H{length}_T{turns}_{connection}_{voltage}V.pdf
```

Example:
```
MC_performance_report_D135_H120_T45_Star_48V.pdf
```

### Output Structure

Reports are saved to `generated_pdfs/` directory:
```
generated_pdfs/
├── FL_performance_report_D106_H65_T30_Star_24V.pdf
├── FL_performance_report_D106_H65_T30_Star_48V.pdf
├── MC_performance_report_D106_H65_T30_Star_24V.pdf
├── MC_performance_report_D106_H65_T30_Star_48V.pdf
└── ...
```

### Requirements

```bash
pip install reportlab matplotlib
```

### Customization

Edit `motor_types_config.json` to:
- Add new motor types
- Modify duty cycle definitions
- Change current density values
- Update PDF settings (logo, temperature limits, IP class)

### Using the GUI

See the "Using the Graphical Interface" section above for visual result viewing and plotting.

### Using Python (Programmatic Access)      │ (Use cached)        RUN FULL  │
         │            │                     SWEEP     │
         │            │                               │
         └────────────┴───────────┬───────────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │   Save Results to Database    │
                  └───────────────────────────────┘
```

## 📊 Accessing Results

### Using Python

```python
from src import database

# List all motors in database
motors = database.list_all_motors()
for motor in motors:
    print(f"Motor ID: {motor['id']}, Hash: {motor['hash'][:16]}...")

# List runs for a specific motor
runs = database.list_runs_for_motor(motor_id=1)
for run in runs:
    print(f"V={run['voltage']} V, J={run['current_density']} A/mm²")

# Load specific run data
data = database.load_run_data(
    con=database.sqlite3.connect(database.config.DB_PATH),
    motor_id=1,
    voltage=48,
    current_density=5.5
)

# Access performance curves
import numpy as np
speed = data['Speed']  # numpy array
torque = data['Shaft_Torque']  # numpy array
power = data['Shaft_Power']  # numpy array
efficiency = data['Efficiency']  # numpy array
```

### Plotting Results

```python
import matplotlib.pyplot as plt
from src import database
import sqlite3

# Load data
con = sqlite3.connect('mcad_results.db')
data = database.load_run_data(con, motor_id=1, voltage=48, current_density=7)
con.close()

# Plot torque-speed curve
speed = data['Speed'].flatten()
torque = data['Shaft_Torque'].flatten()

plt.figure(figsize=(10, 6))
plt.plot(speed, torque, linewidth=2)
plt.xlabel('Speed [rpm]')
plt.ylabel('Torque [Nm]')
plt.title('Torque-Speed Curve (V=48V, J=7 A/mm²)')
plt.grid(True)
plt.show()
```

### Using DB Browser (GUI)

1. Download **DB Browser for SQLite** (free): https://sqlitebrowser.org/
2. Open `mcad_results.db`
3. Browse tables, run SQL queries, export data

## 🔧 Advanced Usage

### Programmatic Access

You can import the framework in your own Python scripts:

```python
fro

### GUI Not Starting

**Problem**: GUI window doesn't appear or crashes on startup

**Solution**:
- Ensure tkinter is installed (usually comes with Python)
- For matplotlib plotting features: `pip install matplotlib`
- Check Python version is 3.8 or higher
- On some systems: `sudo apt-get install python3-tk` (Linux)m src import motor_analyzer, config

# Custom configuration
my_config = config.DEFAULT_MODEL_DICT.copy()
my_config['Battery voltage'] = [24, 48]
my_config['Current density'] = [4, 8]

# Analyze motors
motor_paths = [
    'Motori/motor1.mot',
    'Motori/motor2.mot'
]

results = motor_analyzer.analyze_motor_batch(
    mot_file_paths=motor_paths,
    model_dict=my_config,
    db_path='my_results.db'
)

# Process results
for result in results:
    if result['success']:
        print(f"{result['motor_name']}: {len(result['results'])} runs")
```

### Database Management

```python
from src import database

# Delete all runs for a motor (force re-simulation)
database.delete_motor_runs(motor_id=1)

# Re-initialize database (WARNING: deletes all data!)
imporcripts.gui_main
Graphical user interface (tkinter-based) for all framework operations

### scripts.run_simulations
Command-line interface for batch motor simulations

### scripts.view_results
Command-line results viewer with plotting capabilities

### st os
os.remove('mcad_results.db')
database.init_db('mcad_results.db')
```

## 🐛 Troubleshooting

### MotorCAD COM Error

**Problem**: `pywintypes.com_error: MotorCAD.AppAutomation`

**Solution**:
- Ensure MotorCAD is installed
- Check MotorCAD license is valid
- Try running MotorCAD manually first
- Run Python as administrator

### Array Comparison Issues

**Problem**: Database says results differ even when motor is unchanged

**Solution**: The framework uses normalized comparison with tolerances defined in `src/config.py`. Adjust if needed:

```python
# In src/config.py
RTOL = 1e-4  # Relative tolerance
ATOL = 1e-4  # Absolute tolerance
```

### Missing Dependencies

**Problem**: `ModuleNotFoundError: No module named 'win32com'`

**Solution**:
```bash
pip install pywin32
```

## 📝 Modifying the Code

### Adding New Parameters to Save

Edit `src/config.py`:

```python
SAVE_KEYS = [
    "Shaft_Torque",
    "Speed",
    # ... existing keys ...
    "Your_New_Parameter",  # Add here
]
```

### Changing Comparison Logic

Edit `src/motor_analyzer.py`, function `analyze_motor()`, comparison section:

```python
# Compare key arrays
match = True
for key in ["shaft_torque", "shaft_power", "efficiency", "speed", "your_new_key"]:
    if not utils.arrays_equal(stored_canon.get(key), first_canon.get(key)):
        match = False
        break
```

### Custom Tolerance Per Key

Edit `src/utils.py`, function `arrays_equal()`:

```python
def arrays_equal(a, b, rtol=config.RTOL, atol=config.ATOL, key_name=None):
    # Custom tolerances
    if key_name == "efficiency":
        rtol = 1e-3  # More relaxed for efficiency
    # ... rest of function
```

## 📚 Module Reference

### src.config
Configuration constants and default parameters

### src.database
Database initialization, motor/run storage and retrieval

### src.mcad_interface
MotorCAD COM automation (initialization, parameter extraction, simulation)

### src.motor_analyzer
Motor analysis orchestration and batch processing

### src.utils
Data normalization, array comparison, validation

## 🤝 Contributing

## 🚀 GUI vs Command Line

**Use the GUI when:**
- You prefer visual interfaces
- You want to browse results interactively
- You need to generate plots quickly
- You're new to the framework

**Use the Command Line when:**
- You need to automate workflows
- You're running on a remote server
- You want to integrate with other scripts
- You prefer text-based interfaces

Both interfaces provide the same functionality and use the same database.

---

**Last Updated**: February 15this framework:

1. **Maintain Documentation**: Update docstrings and README
2. **Follow Style**: Use existing code style and naming conventions
3. **Test Thoroughly**: Test with multiple motors before batch runs
4. **Comment Complex Logic**: Add inline comments for non-obvious code
5. **Version Control**: Use git or backup before major changes

## 📄 License

Internal use - MotorCAD Analysis Team

## 👥 Authors

MotorCAD Analysis Team  
February 2026

## 📧 Support

For questions or issues, contact the MotorCAD Analysis Team.

---

**Last Updated**: February 8, 2026
