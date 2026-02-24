"""
MotorCAD Simulation Runner with Quality Checking

This script runs motor simulations with automatic quality validation.
It uses run_and_load_with_quality_check() to ensure smooth torque/power curves.

Usage:
    python run_simulations_quality_check.py --motor "path/to/motor.mot"
    python run_simulations_quality_check.py --directory "motors/" --recursive
    python run_simulations_quality_check.py --list "motor_list.txt"
    
Custom parameters:
    python run_simulations_quality_check.py --motor "motor.mot" \\
        --max-iterations 10 --initial-slip 0.02 --slip-increment 0.03 \\
        --smoothness-threshold 0.10

Author: MotorCAD Analysis Team
Date: February 2026
"""

import argparse
import os
import sys
from pathlib import Path

# Add parent directory to path to import src modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import config, database, mcad_interface, motor_analyzer


def run_motor_with_quality_check(mcad, mot_file_path, model_dict, db_path,
                                 max_iterations=None, initial_slip_start=None,
                                 slip_increment=None, smoothness_threshold=None):
    """
    Run simulation for a single motor with quality checking enabled.
    
    Args:
        mcad: MotorCAD application object
        mot_file_path: Path to .mot file
        model_dict: Model configuration dictionary
        db_path: Database path
        max_iterations: Maximum iterations for quality check
        initial_slip_start: Starting initial slip value
        slip_increment: Slip increment per iteration
        smoothness_threshold: Smoothness threshold (CV)
        
    Returns:
        Dictionary with analysis results
    """
    print(f"\n{'='*80}")
    print(f"ANALYZING MOTOR WITH QUALITY CHECK: {os.path.basename(mot_file_path)}")
    print(f"{'='*80}\n")
    
    # Load motor file
    if not mcad_interface.load_motor_file(mcad, mot_file_path):
        return {'success': False, 'error': 'Failed to load motor file'}
    
    # Extract motor parameters
    print('Extracting motor parameters...')
    motor_dict = mcad_interface.get_mcad_variables(mcad)
    
    # Calculate and display motor hash
    mhash = database.motor_hash(motor_dict)
    print(f'Motor hash: {mhash[:16]}...')
    
    # Get or create motor ID in database
    con = database.sqlite3.connect(db_path)
    motor_id = database.get_motor_id(con, mhash, motor_dict)
    print(f'Motor ID in database: {motor_id}\n')
    con.close()
    
    # Check and build model
    print('Checking/building MotorLAB model...')
    if not mcad_interface.check_and_build_model(mcad, motor_dict, model_dict, mot_file_path):
        return {'success': False, 'error': 'Failed to build model'}
    
    # Run simulations with quality check for each voltage/current combination
    voltages = model_dict['Battery voltage']
    current_densities = model_dict['Current density']
    
    total_runs = 0
    successful_runs = 0
    
    for voltage in voltages:
        print(f"\n{'='*80}")
        print(f"Testing voltage: {voltage}V")
        print(f"{'='*80}")
        
        for current_density in current_densities:
            print(f"\n--- Current Density: {current_density} A/mm² ---")
            
            # Check if run already exists
            con = database.sqlite3.connect(db_path)
            existing_run = database.get_run_row(con, motor_id, voltage, current_density)
            con.close()
            
            if existing_run is not None:
                print(f"✓ Run already exists in database. Skipping.\n")
                continue
            
            # Run simulation with quality check
            results = mcad_interface.run_and_load_with_quality_check(
                mcad=mcad,
                voltage=voltage,
                current_density=current_density,
                motor_dict=motor_dict,
                model_dict=model_dict,
                mot_file_path=mot_file_path,
                max_iterations=max_iterations,
                initial_slip_start=initial_slip_start,
                slip_increment=slip_increment,
                smoothness_threshold=smoothness_threshold
            )
            
            total_runs += 1
            
            if results is not None:
                # Save to database
                con = database.sqlite3.connect(db_path)
                try:
                    database.save_run(con, motor_id, voltage, current_density, results)
                    con.close()
                    successful_runs += 1
                    print(f"✓ Results saved to database.\n")
                except Exception as e:
                    con.close()
                    print(f"✗ Failed to save to database: {e}\n")
            else:
                print(f"✗ Simulation failed.\n")
    
    print(f"\n{'='*80}")
    print(f"SUMMARY FOR: {os.path.basename(mot_file_path)}")
    print(f"{'='*80}")
    print(f"Total simulations attempted: {total_runs}")
    print(f"Successful simulations: {successful_runs}")
    print(f"Failed simulations: {total_runs - successful_runs}")
    print(f"{'='*80}\n")
    
    return {
        'success': True,
        'motor_name': os.path.basename(mot_file_path),
        'motor_hash': mhash,
        'total_runs': total_runs,
        'successful_runs': successful_runs
    }


def main():
    """Main entry point for quality check simulation runner."""
    parser = argparse.ArgumentParser(
        description='Run MotorCAD simulations with automatic quality checking',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Single motor:
    python %(prog)s --motor "motors/D135 H100 12sp DT.mot"
  
  Directory:
    python %(prog)s --directory "motors" --recursive
  
  Motor list:
    python %(prog)s --list "motors_to_simulate.txt"
  
  Custom parameters:
    python %(prog)s --motor "motor.mot" --max-iterations 10 --initial-slip 0.02
        """
    )
    
    # Input sources
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--motor', type=str, help='Path to single .mot file')
    input_group.add_argument('--directory', type=str, help='Directory containing .mot files')
    input_group.add_argument('--list', type=str, help='Text file with list of .mot file paths')
    
    # Options
    parser.add_argument('--recursive', action='store_true',
                       help='Search for .mot files recursively in subdirectories')
    parser.add_argument('--config', type=str, default=None,
                       help='Path to custom configuration JSON file')
    parser.add_argument('--db', type=str, default=config.DB_PATH,
                       help=f'Path to database file (default: {config.DB_PATH})')
    
    # Quality check parameters
    parser.add_argument('--max-iterations', type=int, default=None,
                       help=f'Maximum iterations (default: {config.QUALITY_CHECK_MAX_ITERATIONS})')
    parser.add_argument('--initial-slip', type=float, default=None,
                       help=f'Initial slip start value (default: {config.QUALITY_CHECK_INITIAL_SLIP_START})')
    parser.add_argument('--slip-increment', type=float, default=None,
                       help=f'Slip increment per iteration (default: {config.QUALITY_CHECK_SLIP_INCREMENT})')
    parser.add_argument('--smoothness-threshold', type=float, default=None,
                       help=f'Smoothness threshold (default: {config.QUALITY_CHECK_SMOOTHNESS_THRESHOLD})')
    
    args = parser.parse_args()
    
    # Initialize database
    print(f"Initializing database: {args.db}")
    database.init_db(args.db)
    
    # Load configuration
    if args.config:
        import json
        print(f"Loading configuration from: {args.config}")
        with open(args.config, 'r') as f:
            model_dict = json.load(f)
    else:
        model_dict = config.DEFAULT_MODEL_DICT.copy()
    
    print("\nConfiguration:")
    print(f"  Max speed: {model_dict['Maximum speed']} rpm")
    print(f"  Min speed: {model_dict['Minimum speed']} rpm")
    print(f"  Voltages: {model_dict['Battery voltage']}")
    print(f"  Current densities: {model_dict['Current density']}")
    print(f"\nQuality Check Parameters:")
    print(f"  Max iterations: {args.max_iterations or config.QUALITY_CHECK_MAX_ITERATIONS}")
    print(f"  Initial slip: {args.initial_slip or config.QUALITY_CHECK_INITIAL_SLIP_START}")
    print(f"  Slip increment: {args.slip_increment or config.QUALITY_CHECK_SLIP_INCREMENT}")
    print(f"  Smoothness threshold: {args.smoothness_threshold or config.QUALITY_CHECK_SMOOTHNESS_THRESHOLD}")
    
    # Get list of motor files
    motor_files = []
    
    if args.motor:
        motor_files = [os.path.abspath(args.motor)]
    elif args.directory:
        print(f"\nSearching for .mot files in: {args.directory}")
        motor_files = motor_analyzer.find_mot_files(args.directory, args.recursive)
    elif args.list:
        print(f"\nLoading motor list from: {args.list}")
        with open(args.list, 'r') as f:
            motor_files = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        motor_files = [os.path.abspath(f) for f in motor_files]
    
    if not motor_files:
        print("ERROR: No motor files found!")
        return 1
    
    print(f"\nFound {len(motor_files)} motor(s) to process.\n")
    
    # Initialize MotorCAD
    print("Initializing MotorCAD...")
    mcad = mcad_interface.initialize_mcad()
    
    # Process each motor
    results_summary = []
    
    for i, mot_file in enumerate(motor_files, 1):
        print(f"\n{'#'*80}")
        print(f"# Processing motor {i}/{len(motor_files)}")
        print(f"{'#'*80}")
        
        if not os.path.exists(mot_file):
            print(f"ERROR: File not found: {mot_file}")
            results_summary.append({
                'motor_name': os.path.basename(mot_file),
                'success': False,
                'error': 'File not found'
            })
            continue
        
        result = run_motor_with_quality_check(
            mcad=mcad,
            mot_file_path=mot_file,
            model_dict=model_dict,
            db_path=args.db,
            max_iterations=args.max_iterations,
            initial_slip_start=args.initial_slip,
            slip_increment=args.slip_increment,
            smoothness_threshold=args.smoothness_threshold
        )
        
        results_summary.append(result)
    
    # Close MotorCAD
    mcad_interface.close_mcad(mcad)
    
    # Print final summary
    print(f"\n{'='*80}")
    print("FINAL SUMMARY")
    print(f"{'='*80}")
    print(f"Total motors processed: {len(motor_files)}")
    
    successful_motors = sum(1 for r in results_summary if r['success'])
    failed_motors = len(motor_files) - successful_motors
    
    print(f"Successful: {successful_motors}")
    print(f"Failed: {failed_motors}")
    
    if failed_motors > 0:
        print("\nFailed motors:")
        for result in results_summary:
            if not result['success']:
                print(f"  - {result.get('motor_name', 'Unknown')}: {result.get('error', 'Unknown error')}")
    
    print(f"{'='*80}\n")
    
    return 0 if failed_motors == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
