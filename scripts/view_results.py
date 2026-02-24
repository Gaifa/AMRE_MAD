"""
Database visualization and data export script.

This script provides tools to:
- List all motors in database
- View simulation runs for each motor
- Plot performance curves
- Export data to CSV

Usage:
    python scripts/view_results.py

Author: MotorCAD Analysis Team
Date: February 2026
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src import database, config
import sqlite3
import numpy as np


try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("Warning: matplotlib not installed. Plotting features disabled.")
    print("Install with: pip install matplotlib")


# =============================================================================
# LISTING FUNCTIONS
# =============================================================================

def list_motors():
    """List all motors in database with basic info."""
    motors = database.list_all_motors()
    
    if not motors:
        print("No motors found in database.")
        return
    
    print("\n" + "="*140)
    print("MOTORS IN DATABASE")
    print("="*140)
    print(f"{'ID':<5} {'Diameter (mm)':<15} {'Length (mm)':<15} {'Turns/Coil':<15} {'Connection':<15} {'Created':<25}")
    print("-"*140)
    
    for motor in motors:
        motor_json = motor['motor_json']
        
        # Extract motor parameters with safe fallback
        diameter = motor_json.get('Stator_Lam_Dia', {}).get('value', 'N/A')
        length = motor_json.get('Stator_Lam_Length', {}).get('value', 'N/A')
        turns = motor_json.get('Number_turns_coil', {}).get('value', 'N/A')
        connection_value = motor_json.get('winding_connection', {}).get('value', None)
        
        # Format connection type
        if connection_value is not None:
            try:
                conn_int = int(float(connection_value))
                connection = "Star" if conn_int == 0 else "Delta" if conn_int == 1 else f"Unknown({conn_int})"
            except Exception:
                connection = "N/A"
        else:
            connection = "N/A"
        
        # Format numerical values
        diameter_str = f"{diameter:.2f}" if isinstance(diameter, (int, float)) else str(diameter)
        length_str = f"{length:.2f}" if isinstance(length, (int, float)) else str(length)
        turns_str = f"{turns:.0f}" if isinstance(turns, (int, float)) else str(turns)
        
        print(f"{motor['id']:<5} {diameter_str:<15} {length_str:<15} {turns_str:<15} {connection:<15} {motor['created_at']:<25}")
    
    print("="*140)
    print(f"Total motors: {len(motors)}\n")


def list_motor_runs(motor_id):
    """List all simulation runs for a specific motor."""
    runs = database.list_runs_for_motor(motor_id)
    
    if not runs:
        print(f"No runs found for motor ID {motor_id}")
        return
    
    print("\n" + "="*80)
    print(f"SIMULATION RUNS FOR MOTOR ID {motor_id}")
    print("="*80)
    print(f"{'Run ID':<8} {'Voltage (V)':<15} {'Current Density (A/mm²)':<25} {'Created':<25}")
    print("-"*80)
    
    for run in runs:
        print(f"{run['run_id']:<8} {run['voltage']:<15.1f} {run['current_density']:<25.2f} {run['created_at']:<25}")
    
    print("="*80)
    print(f"Total runs: {len(runs)}\n")


def summarize_run(motor_id, voltage, current_density):
    """Print summary statistics for a specific run."""
    con = sqlite3.connect(config.DB_PATH)
    data = database.load_run_data(con, motor_id, voltage, current_density)
    con.close()
    
    if data is None:
        print(f"No data found for motor {motor_id}, V={voltage}, J={current_density}")
        return
    
    print("\n" + "="*80)
    print(f"RUN SUMMARY: Motor {motor_id}, Voltage={voltage}V, Current Density={current_density} A/mm²")
    print("="*80)
    
    for key in config.SAVE_KEYS:
        arr = data.get(key)
        if arr is None:
            print(f"{key:<35}: None")
        else:
            arr = np.asarray(arr).flatten()
            print(f"{key:<35}: shape={arr.shape}, min={np.nanmin(arr):.3f}, max={np.nanmax(arr):.3f}, mean={np.nanmean(arr):.3f}")
    
    print("="*80 + "\n")


# =============================================================================
# PLOTTING FUNCTIONS
# =============================================================================

def plot_torque_speed(motor_id, voltage, current_density):
    """Plot torque-speed curve."""
    if not HAS_MATPLOTLIB:
        print("Matplotlib not available for plotting.")
        return
    
    con = sqlite3.connect(config.DB_PATH)
    data = database.load_run_data(con, motor_id, voltage, current_density)
    con.close()
    
    if data is None:
        print("No data found.")
        return
    
    speed = data.get('Speed')
    torque = data.get('Shaft_Torque')
    
    if speed is None or torque is None:
        print("Speed or torque data not available.")
        return
    
    speed = np.asarray(speed).flatten()
    torque = np.asarray(torque).flatten()
    
    plt.figure(figsize=(10, 6))
    plt.plot(speed, torque, linewidth=2, color='blue')
    plt.xlabel('Speed [rpm]', fontsize=12)
    plt.ylabel('Torque [Nm]', fontsize=12)
    plt.title(f'Torque-Speed Curve (Motor {motor_id}, V={voltage}V, J={current_density} A/mm²)', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


def plot_power_speed(motor_id, voltage, current_density):
    """Plot power-speed curve."""
    if not HAS_MATPLOTLIB:
        print("Matplotlib not available for plotting.")
        return
    
    con = sqlite3.connect(config.DB_PATH)
    data = database.load_run_data(con, motor_id, voltage, current_density)
    con.close()
    
    if data is None:
        print("No data found.")
        return
    
    speed = data.get('Speed')
    power = data.get('Shaft_Power')
    
    if speed is None or power is None:
        print("Speed or power data not available.")
        return
    
    speed = np.asarray(speed).flatten()
    power = np.asarray(power).flatten() / 1000  # Convert to kW
    
    plt.figure(figsize=(10, 6))
    plt.plot(speed, power, linewidth=2, color='green')
    plt.xlabel('Speed [rpm]', fontsize=12)
    plt.ylabel('Power [kW]', fontsize=12)
    plt.title(f'Power-Speed Curve (Motor {motor_id}, V={voltage}V, J={current_density} A/mm²)', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


def plot_efficiency_speed(motor_id, voltage, current_density):
    """Plot efficiency-speed curve."""
    if not HAS_MATPLOTLIB:
        print("Matplotlib not available for plotting.")
        return
    
    con = sqlite3.connect(config.DB_PATH)
    data = database.load_run_data(con, motor_id, voltage, current_density)
    con.close()
    
    if data is None:
        print("No data found.")
        return
    
    speed = data.get('Speed')
    efficiency = data.get('Efficiency')
    
    if speed is None or efficiency is None:
        print("Speed or efficiency data not available.")
        return
    
    speed = np.asarray(speed).flatten()
    efficiency = np.asarray(efficiency).flatten()
    
    plt.figure(figsize=(10, 6))
    plt.plot(speed, efficiency, linewidth=2, color='red')
    plt.xlabel('Speed [rpm]', fontsize=12)
    plt.ylabel('Efficiency [%]', fontsize=12)
    plt.title(f'Efficiency-Speed Curve (Motor {motor_id}, V={voltage}V, J={current_density} A/mm²)', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.ylim(0, 100)
    plt.tight_layout()
    plt.show()


def plot_all_curves(motor_id, voltage, current_density):
    """Plot torque, power, and efficiency on separate subplots."""
    if not HAS_MATPLOTLIB:
        print("Matplotlib not available for plotting.")
        return
    
    con = sqlite3.connect(config.DB_PATH)
    data = database.load_run_data(con, motor_id, voltage, current_density)
    con.close()
    
    if data is None:
        print("No data found.")
        return
    
    speed = data.get('Speed')
    torque = data.get('Shaft_Torque')
    power = data.get('Shaft_Power')
    efficiency = data.get('Efficiency')
    
    if speed is None:
        print("Speed data not available.")
        return
    
    speed = np.asarray(speed).flatten()
    
    fig, axes = plt.subplots(3, 1, figsize=(10, 12))
    
    # Torque
    if torque is not None:
        torque_arr = np.asarray(torque).flatten()
        axes[0].plot(speed, torque_arr, linewidth=2, color='blue')
        axes[0].set_ylabel('Torque [Nm]', fontsize=11)
        axes[0].grid(True, alpha=0.3)
    
    # Power
    if power is not None:
        power_arr = np.asarray(power).flatten() / 1000  # kW
        axes[1].plot(speed, power_arr, linewidth=2, color='green')
        axes[1].set_ylabel('Power [kW]', fontsize=11)
        axes[1].grid(True, alpha=0.3)
    
    # Efficiency
    if efficiency is not None:
        eff_arr = np.asarray(efficiency).flatten()
        axes[2].plot(speed, eff_arr, linewidth=2, color='red')
        axes[2].set_ylabel('Efficiency [%]', fontsize=11)
        axes[2].set_ylim(0, 100)
        axes[2].grid(True, alpha=0.3)
    
    axes[2].set_xlabel('Speed [rpm]', fontsize=11)
    fig.suptitle(f'Performance Curves (Motor {motor_id}, V={voltage}V, J={current_density} A/mm²)', fontsize=14)
    plt.tight_layout()
    plt.show()


# =============================================================================
# INTERACTIVE MENU
# =============================================================================

def main_menu():
    """Display interactive menu."""
    while True:
        print("\n" + "="*80)
        print("MOTORCAD RESULTS VIEWER")
        print("="*80)
        print("1. List all motors")
        print("2. List runs for a motor")
        print("3. Summarize a specific run")
        print("4. Plot torque-speed curve")
        print("5. Plot power-speed curve")
        print("6. Plot efficiency-speed curve")
        print("7. Plot all curves (3 subplots)")
        print("0. Exit")
        print("="*80)
        
        choice = input("\nSelect option: ").strip()
        
        if choice == '0':
            print("Exiting...")
            break
        
        elif choice == '1':
            list_motors()
        
        elif choice == '2':
            motor_id = input("Enter motor ID: ").strip()
            try:
                list_motor_runs(int(motor_id))
            except ValueError:
                print("Invalid motor ID")
        
        elif choice == '3':
            motor_id = input("Enter motor ID: ").strip()
            voltage = input("Enter voltage: ").strip()
            current_density = input("Enter current density: ").strip()
            try:
                summarize_run(int(motor_id), float(voltage), float(current_density))
            except ValueError:
                print("Invalid input")
        
        elif choice == '4':
            motor_id = input("Enter motor ID: ").strip()
            voltage = input("Enter voltage: ").strip()
            current_density = input("Enter current density: ").strip()
            try:
                plot_torque_speed(int(motor_id), float(voltage), float(current_density))
            except ValueError:
                print("Invalid input")
        
        elif choice == '5':
            motor_id = input("Enter motor ID: ").strip()
            voltage = input("Enter voltage: ").strip()
            current_density = input("Enter current density: ").strip()
            try:
                plot_power_speed(int(motor_id), float(voltage), float(current_density))
            except ValueError:
                print("Invalid input")
        
        elif choice == '6':
            motor_id = input("Enter motor ID: ").strip()
            voltage = input("Enter voltage: ").strip()
            current_density = input("Enter current density: ").strip()
            try:
                plot_efficiency_speed(int(motor_id), float(voltage), float(current_density))
            except ValueError:
                print("Invalid input")
        
        elif choice == '7':
            motor_id = input("Enter motor ID: ").strip()
            voltage = input("Enter voltage: ").strip()
            current_density = input("Enter current density: ").strip()
            try:
                plot_all_curves(int(motor_id), float(voltage), float(current_density))
            except ValueError:
                print("Invalid input")
        
        else:
            print("Invalid option")


if __name__ == '__main__':
    # Check if database exists
    if not os.path.exists(config.DB_PATH):
        print(f"ERROR: Database not found at {config.DB_PATH}")
        print("Run simulations first to create the database.")
        sys.exit(1)
    
    main_menu()
