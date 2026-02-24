"""
Main script for running MotorCAD simulations.

This script provides a command-line interface for batch motor analysis.
It can process:
- Single motor file
- Multiple motor files specified as list
- All motors in a directory
- Custom motor file discovery

Usage examples:
    # Single motor
    python run_simulations.py --motor "path/to/motor.mot"
    
    # Multiple motors from list file
    python run_simulations.py --list motors_to_simulate.txt
    
    # All motors in directory
    python run_simulations.py --directory "c:/path/to/motors" --recursive
    
    # Custom configuration
    python run_simulations.py --motor "motor.mot" --config custom_config.json

Author: MotorCAD Analysis Team
Date: February 2026
"""

import argparse
import json
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src import config
from src import motor_analyzer
from src import database


# =============================================================================
# CONFIGURATION HELPERS
# =============================================================================

def load_config_file(config_path: str) -> dict:
    """
    Load custom configuration from JSON file.
    
    Args:
        config_path: Path to JSON configuration file
        
    Returns:
        Configuration dictionary
    """
    with open(config_path, 'r') as f:
        return json.load(f)


def load_motor_list(list_path: str) -> list:
    """
    Load list of motor file paths from text file.
    
    Each line should contain one .mot file path.
    Lines starting with # are ignored (comments).
    
    Args:
        list_path: Path to text file containing motor paths
        
    Returns:
        List of motor file paths
    """
    motors = []
    with open(list_path, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if line and not line.startswith('#'):
                motors.append(line)
    return motors


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main execution function."""
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Run MotorCAD simulations for one or more motors.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simulate single motor
  python run_simulations.py --motor "motors/D106 H65 25sp DT ( 2x0.63 + 2x0.5 ).mot"
  
  # Simulate motors from list file
  python run_simulations.py --list motors_to_simulate.txt
  
  # Simulate all motors in directory
  python run_simulations.py --directory "motors" --recursive
  
  # Use custom configuration
  python run_simulations.py --motor "motor.mot" --config custom_config.json
        """
    )
    
    # Motor selection (mutually exclusive group)
    motor_group = parser.add_mutually_exclusive_group(required=True)
    motor_group.add_argument(
        '--motor', '-m',
        type=str,
        help='Path to single .mot file'
    )
    motor_group.add_argument(
        '--list', '-l',
        type=str,
        help='Path to text file containing list of .mot file paths'
    )
    motor_group.add_argument(
        '--directory', '-d',
        type=str,
        help='Directory containing .mot files'
    )
    
    # Additional options
    parser.add_argument(
        '--recursive', '-r',
        action='store_true',
        help='Search directory recursively (used with --directory)'
    )
    parser.add_argument(
        '--config', '-c',
        type=str,
        help='Path to custom configuration JSON file'
    )
    parser.add_argument(
        '--db', '-db',
        type=str,
        default=config.DB_PATH,
        help=f'Path to database file (default: {config.DB_PATH})'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print motors to be simulated without running simulations'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    if args.config:
        print(f"Loading custom configuration from: {args.config}")
        model_dict = load_config_file(args.config)
    else:
        print("Using default configuration")
        model_dict = config.DEFAULT_MODEL_DICT.copy()
    
    # Print configuration
    print("\n" + "="*80)
    print("SIMULATION CONFIGURATION")
    print("="*80)
    print(f"Maximum speed:        {model_dict['Maximum speed']} rpm")
    print(f"Minimum speed:        {model_dict['Minimum speed']} rpm")
    print(f"Speed increment:      {config.SPEED_INCREMENT} rpm")
    print(f"Maximum current dens: {model_dict['Maximum current density']} A/mm²")
    print(f"Battery voltages:     {model_dict['Battery voltage']}")
    print(f"Current densities:    {model_dict['Current density']}")
    print(f"Database:             {args.db}")
    print("="*80 + "\n")
    
    # Determine motor files to process
    mot_files = []
    
    if args.motor:
        # Single motor file
        mot_files = [args.motor]
        print(f"Mode: Single motor file")
        
    elif args.list:
        # Load list from file
        print(f"Mode: Motor list from file: {args.list}")
        mot_files = load_motor_list(args.list)
        print(f"Loaded {len(mot_files)} motor(s) from list")
        
    elif args.directory:
        # Scan directory
        print(f"Mode: Directory scan: {args.directory}")
        if args.recursive:
            print("  Recursive search enabled")
        mot_files = motor_analyzer.find_mot_files(args.directory, recursive=args.recursive)
        print(f"Found {len(mot_files)} .mot file(s)")
    
    # Validate motor files exist and ensure absolute paths
    mot_files_valid = []
    for mot_path in mot_files:
        # Convert to absolute path
        abs_mot_path = os.path.abspath(mot_path)
        
        if os.path.exists(abs_mot_path):
            mot_files_valid.append(abs_mot_path)
        else:
            print(f"WARNING: File not found: {mot_path}")
    
    if not mot_files_valid:
        print("\nERROR: No valid motor files to process!")
        return 1
    
    print(f"\nTotal valid motor files: {len(mot_files_valid)}")
    
    # Dry run mode: just list motors and exit
    if args.dry_run:
        print("\n" + "="*80)
        print("DRY RUN - Motors to be simulated:")
        print("="*80)
        for idx, mot_path in enumerate(mot_files_valid, 1):
            print(f"{idx:3d}. {mot_path}")
        print("="*80)
        print("\nDry run complete. No simulations were run.")
        return 0
    
    # Confirm before proceeding
    print("\n" + "="*80)
    print("Motors to be simulated:")
    print("="*80)
    for idx, mot_path in enumerate(mot_files_valid, 1):
        print(f"{idx:3d}. {os.path.basename(mot_path)}")
    print("="*80)
    
    # Calculate total number of simulations
    n_voltages = len(model_dict['Battery voltage'])
    n_currents = len(model_dict['Current density'])
    max_sims = len(mot_files_valid) * n_voltages * n_currents
    
    print(f"\nMaximum possible simulations: {max_sims}")
    print("(Actual number may be lower due to database caching)\n")
    
    response = input("Proceed with simulations? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Simulation cancelled by user.")
        return 0
    
    # Run batch analysis
    print("\n" + "#"*80)
    print("STARTING BATCH SIMULATION")
    print("#"*80 + "\n")
    
    batch_results = motor_analyzer.analyze_motor_batch(
        mot_file_paths=mot_files_valid,
        model_dict=model_dict,
        db_path=args.db
    )
    
    # Print final summary
    print("\n" + "#"*80)
    print("FINAL SUMMARY")
    print("#"*80)
    
    successful = [r for r in batch_results if r['success']]
    failed = [r for r in batch_results if not r['success']]
    
    print(f"\nTotal motors processed:   {len(batch_results)}")
    print(f"Successful:               {len(successful)}")
    print(f"Failed:                   {len(failed)}")
    
    if successful:
        total_runs = sum(len(r.get('results', [])) for r in successful)
        total_skipped = sum(len(r.get('skipped_voltages', [])) for r in successful)
        print(f"\nTotal simulations saved:  {total_runs}")
        print(f"Voltages skipped (cache): {total_skipped}")
    
    if failed:
        print("\nFailed motors:")
        for r in failed:
            error_msg = r.get('error', 'Unknown error')
            print(f"  - {r['motor_name']}: {error_msg}")
    
    print("\n" + "#"*80)
    print(f"Results database: {args.db}")
    print("#"*80 + "\n")
    
    return 0 if len(failed) == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
