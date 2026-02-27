"""
Configuration module for MotorCAD simulation framework.

This module contains all configuration parameters, constants, and default values
used throughout the simulation framework.

Author: MotorCAD Analysis Team
Date: February 2026
"""

import os

# Project root directory (two levels up from this file: src/ -> project root)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# Path to the SQLite database file where simulation results are stored
DB_PATH = os.path.join(_PROJECT_ROOT, "mcad_results.db")

# Keys to extract and save from MotorCAD .mat output files
# These represent the core performance metrics for each motor simulation
SAVE_KEYS = [
    "Shaft_Torque",                          # Shaft torque [Nm]
    "Speed",                                  # Rotational speed [rpm]
    "Shaft_Power",                            # Shaft power output [W]
    "Voltage_Phase_RMS",                      # RMS phase voltage [V]
    "Stator_Current_Line_RMS",                # RMS line current [A]
    "Power_Factor_From_Power_Balance",        # Power factor [-]
    "Efficiency",                             # Motor efficiency [%]
    "Frequency",                              # Electrical frequency [Hz]
    "DC_Bus_Voltage"                          # DC bus voltage [V]
]

# Canonical key names (lowercase with underscores) for data normalization
# Used to handle variations in key naming conventions from different MotorCAD versions
CANON_KEYS = [
    "shaft_torque",
    "speed",
    "shaft_power",
    "voltage_phase_rms",
    "stator_current_line_rms",
    "power_factor_from_power_balance",
    "efficiency",
    "frequency",
    "dc_bus_voltage"
]

# =============================================================================
# SIMULATION PARAMETERS
# =============================================================================

# Default model configuration dictionary
# These parameters define the operating envelope for motor simulations
DEFAULT_MODEL_DICT = {
    'Maximum speed': 5000,              # Maximum rotational speed [rpm]
    'Minimum speed': 50,                # Minimum rotational speed [rpm]
    'Maximum current density': 15,      # Maximum current density [A/mm²]
    'Battery voltage': [96],#[24, 48, 80, 96, 120, 144],  # DC bus voltages to test [V]
    'Current density': [3.5,4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 9, 13]  # Current densities to test [A/mm²]
}

# Speed increment for simulation sweep [rpm]
SPEED_INCREMENT = 50

# Modulation index for inverter control (typical value for SVPWM)
MODULATION_INDEX = 0.95

# =============================================================================
# QUALITY CHECK PARAMETERS
# =============================================================================

# Maximum number of iterations to try for smooth results
QUALITY_CHECK_MAX_ITERATIONS = 5

# Starting value for IM_InitialSlip_MotorLAB
QUALITY_CHECK_INITIAL_SLIP_START = 0.01

# Amount to increase initial slip each iteration
QUALITY_CHECK_SLIP_INCREMENT = 0.02

# Maximum value for initial slip (safety limit)
QUALITY_CHECK_MAX_SLIP = 0.20

# Smoothness threshold: maximum acceptable coefficient of variation (CV)
# CV = std(differences) / mean(absolute values)
# Lower values = stricter smoothness requirement
# 0.15 = 15% relative variation is acceptable
QUALITY_CHECK_SMOOTHNESS_THRESHOLD = 0.15

# =============================================================================
# MOTORCAD INTERFACE SETTINGS
# =============================================================================

# MotorCAD message display state (2 = suppress messages)
MESSAGE_DISPLAY_STATE = 2

# Motor parameter names mapping
# Maps internal variable names to MotorCAD API variable names
MOTOR_PARAM_MAPPING = {
    'Stator_Lam_Dia': ('Stator_Lam_Dia', 'Stator External diameter'),
    'Stator_Lam_Length': ('Stator_Lam_Length', 'Stator Length'),
    'Number_turns_coil': ('MagTurnsConductor', 'Number of turns per coil'),
    'Slot_number': ('Slot_number', 'Number of slots'),
    'Pole_number': ('Pole_number', 'Number of poles'),
    'MagThrow': ('MagThrow', 'Magnetic throw'),
    'MagPhases': ('MagPhases', 'Number of phases'),
    'Liner_layer_definition': ('Liner_Layers_Definition', 
                                 'Liner layer definition (0 = Single_Layer, 1 = Double_Layers)'),
    'winding_connection': ('WindingConnection', 
                           'Winding connection type (0: Star, 1: Delta)'),
    'RMScurrentdensity': ('RMScurrentdensity', 'RMS current density in A/mm^2'),
    'ParallelPaths': ('ParallelPaths', 'Number of parallel paths in the winding'),
    'ArmatureTurnCSA': ('ArmatureTurnCSA', 'Armature turn cross-sectional area'),
}

# =============================================================================
# COMPARISON TOLERANCES
# =============================================================================

# Relative tolerance for numerical array comparison
# Used when checking if simulation results match database records
RTOL = 1e-4

# Absolute tolerance for numerical array comparison
ATOL = 1e-4

# Keys used for comparing simulation results to detect differences
COMPARISON_KEYS = ["shaft_torque", "shaft_power", "efficiency", "speed"]

# =============================================================================
# FILE PATHS
# =============================================================================

# Default motor files directory
MOTORS_DIR = os.path.join(_PROJECT_ROOT, "motors")

# Lab results subdirectory within each motor folder
LAB_SUBDIR = "Lab"

# MotorCAD electromagnetic data filename
MAT_FILENAME = "MotorLAB_elecdata.mat"
