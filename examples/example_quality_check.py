"""
Example: Using Quality Check in Python Code

This script demonstrates how to use the quality checking feature
directly in Python for custom workflows.

Author: MotorCAD Analysis Team
Date: February 2026
"""

from src import mcad_interface, database, config

# Initialize database
database.init_db()

# Configuration
model_dict = config.DEFAULT_MODEL_DICT.copy()
mot_file_path = r"Motori\D135 H100 12sp DT ( 2x0.9 + 2x0.8 ).mot"

# Initialize MotorCAD
print("Initializing MotorCAD...")
mcad = mcad_interface.initialize_mcad()

# Load motor file
print(f"Loading motor: {mot_file_path}")
mcad_interface.load_motor_file(mcad, mot_file_path)

# Extract motor parameters
motor_dict = mcad_interface.get_mcad_variables(mcad)

# Example 1: Standard simulation (no quality check)
print("\n" + "="*70)
print("EXAMPLE 1: Standard Simulation")
print("="*70)

results_standard = mcad_interface.run_and_load(
    mcad=mcad,
    voltage=48,
    current_density=7.0,
    motor_dict=motor_dict,
    model_dict=model_dict,
    mot_file_path=mot_file_path
)

if results_standard:
    print("✓ Standard simulation completed")


# Example 2: Simulation with quality check (default parameters)
print("\n" + "="*70)
print("EXAMPLE 2: Simulation with Quality Check (Default Parameters)")
print("="*70)

results_quality = mcad_interface.run_and_load_with_quality_check(
    mcad=mcad,
    voltage=48,
    current_density=7.5,
    motor_dict=motor_dict,
    model_dict=model_dict,
    mot_file_path=mot_file_path
)

if results_quality:
    print("✓ Quality-checked simulation completed")


# Example 3: Quality check with custom parameters
print("\n" + "="*70)
print("EXAMPLE 3: Quality Check with Custom Parameters")
print("="*70)

results_custom = mcad_interface.run_and_load_with_quality_check(
    mcad=mcad,
    voltage=48,
    current_density=8.0,
    motor_dict=motor_dict,
    model_dict=model_dict,
    mot_file_path=mot_file_path,
    max_iterations=10,              # Try up to 10 times
    initial_slip_start=0.02,        # Start with higher slip
    slip_increment=0.03,            # Increase more aggressively
    smoothness_threshold=0.10       # Stricter smoothness requirement (10%)
)

if results_custom:
    print("✓ Custom quality-checked simulation completed")


# Example 4: Check smoothness of existing results
print("\n" + "="*70)
print("EXAMPLE 4: Manual Smoothness Check")
print("="*70)

if results_quality:
    is_smooth, metrics = mcad_interface.check_results_smoothness(
        results_quality,
        smoothness_threshold=0.15
    )
    
    print(f"Smoothness check: {'PASS' if is_smooth else 'FAIL'}")
    print(f"Torque CV: {metrics.get('torque', 0):.4f}")
    print(f"Power CV: {metrics.get('power', 0):.4f}")


# Close MotorCAD
mcad_interface.close_mcad(mcad)

print("\n" + "="*70)
print("All examples completed!")
print("="*70)
