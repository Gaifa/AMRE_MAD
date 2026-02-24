"""
MotorCAD Simulation Framework

A comprehensive framework for automated MotorCAD simulation,
result caching, and batch motor analysis.

Modules:
- config: Configuration and constants
- database: SQLite database management
- mcad_interface: MotorCAD COM automation
- motor_analyzer: Motor analysis orchestration
- utils: Utility functions for data processing

Author: MotorCAD Analysis Team
Date: February 2026
"""

__version__ = "1.0.0"
__author__ = "MotorCAD Analysis Team"

# Import main components for convenience
from . import config
from . import database
from . import mcad_interface
from . import motor_analyzer
from . import utils

# Expose key functions at package level
from .motor_analyzer import analyze_motor, analyze_motor_batch, find_mot_files
from .database import init_db, list_all_motors, list_runs_for_motor

__all__ = [
    'config',
    'database',
    'mcad_interface',
    'motor_analyzer',
    'utils',
    'analyze_motor',
    'analyze_motor_batch',
    'find_mot_files',
    'init_db',
    'list_all_motors',
    'list_runs_for_motor',
]
