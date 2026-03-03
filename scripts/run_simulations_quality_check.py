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
from datetime import datetime

# Add parent directory to path to import src modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import config, database, mcad_interface, motor_analyzer


class QualityCheckLogger:
    """Logger for quality check failures and statistics."""
    
    def __init__(self, log_file_path):
        self.log_file_path = log_file_path
        self.failures = []
        
    def log_motor_failure(self, motor_path, failed_runs):
        """
        Log a motor that failed one or more runs.
        
        Args:
            motor_path: Full path to the motor file
            failed_runs: List of dictionaries with failure details
        """
        self.failures.append({
            'motor_path': motor_path,
            'failed_runs': failed_runs
        })
    
    def write_log(self):
        """Write the log file to disk."""
        if not self.failures:
            # No failures, create a success log
            with open(self.log_file_path, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write("MOTORCAD QUALITY CHECK SIMULATION LOG\n")
                f.write("="*80 + "\n")
                f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Status: ALL SIMULATIONS SUCCESSFUL\n")
                f.write("="*80 + "\n\n")
                f.write("No failures detected. All motors simulated successfully.\n")
            return
        
        # Write failure log
        with open(self.log_file_path, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("MOTORCAD QUALITY CHECK SIMULATION LOG - FAILURES DETECTED\n")
            f.write("="*80 + "\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total motors with failures: {len(self.failures)}\n")
            f.write("="*80 + "\n\n")
            
            for idx, failure_info in enumerate(self.failures, 1):
                f.write(f"\n{'#'*80}\n")
                f.write(f"FAILED MOTOR #{idx}\n")
                f.write(f"{'#'*80}\n\n")
                f.write(f"Motor Path: {failure_info['motor_path']}\n")
                f.write(f"Number of failed runs: {len(failure_info['failed_runs'])}\n")
                f.write("\n" + "-"*80 + "\n")
                f.write("FAILED RUNS DETAILS:\n")
                f.write("-"*80 + "\n\n")
                
                for run_idx, run_failure in enumerate(failure_info['failed_runs'], 1):
                    f.write(f"  Run #{run_idx}:\n")
                    f.write(f"    Voltage: {run_failure['voltage']} V\n")
                    f.write(f"    Current Density: {run_failure['current_density']} A/mm²\n")
                    f.write(f"    Initial Slip (start): {run_failure['slip_start']:.4f}\n")
                    f.write(f"    Initial Slip (final): {run_failure['slip_final']:.4f}\n")
                    f.write(f"    Iterations attempted: {run_failure['iterations']}\n")
                    f.write(f"    Reason: {run_failure['reason']}\n")
                    
                    if 'torque_cv' in run_failure and run_failure['torque_cv'] is not None:
                        f.write(f"    Final Torque CV: {run_failure['torque_cv']:.4f}\n")
                    if 'power_cv' in run_failure and run_failure['power_cv'] is not None:
                        f.write(f"    Final Power CV: {run_failure['power_cv']:.4f}\n")
                    
                    f.write("\n")
            
            f.write("\n" + "="*80 + "\n")
            f.write("END OF LOG\n")
            f.write("="*80 + "\n")
        
        print(f"\n⚠ Failure log written to: {self.log_file_path}")


def run_motor_with_quality_check(mcad, mot_file_path, model_dict, db_path, logger,
                                 max_iterations=None, initial_slip_start=None,
                                 slip_increment=None, smoothness_threshold=None):
    """
    Run simulation for a single motor with quality checking enabled.
    
    This function collects ALL results before saving to database.
    If ANY run fails, NO data is saved to database (transactional behavior).
    
    Args:
        mcad: MotorCAD application object
        mot_file_path: Path to .mot file
        model_dict: Model configuration dictionary
        db_path: Database path
        logger: QualityCheckLogger instance
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
        return {'success': False, 'error': 'Failed to load motor file', 'motor_path': mot_file_path}
    
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
        return {'success': False, 'error': 'Failed to build model', 'motor_path': mot_file_path}
    
    # Get default parameters
    if max_iterations is None:
        max_iterations = config.QUALITY_CHECK_MAX_ITERATIONS
    if initial_slip_start is None:
        initial_slip_start = config.QUALITY_CHECK_INITIAL_SLIP_START
    if slip_increment is None:
        slip_increment = config.QUALITY_CHECK_SLIP_INCREMENT
    if smoothness_threshold is None:
        smoothness_threshold = config.QUALITY_CHECK_SMOOTHNESS_THRESHOLD
    
    # Collect all results in memory before saving to database
    # This implements transactional behavior: save all or nothing
    all_results = []
    failed_runs = []
    runs_to_skip = []
    
    voltages = model_dict['Battery voltage']
    current_densities = model_dict['Current density']
    
    total_runs = 0
    
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
                runs_to_skip.append({'voltage': voltage, 'current_density': current_density})
                continue
            
            total_runs += 1
            
            # Track slip values for this run
            current_slip = initial_slip_start
            iterations_done = 0
            final_metrics = None
            last_temp_results = None   # retain most recent results for slip extraction
            
            # Run simulation with quality check - we need to track the details
            results = None
            for iteration in range(1, max_iterations + 1):
                iterations_done = iteration
                
                # Run single simulation
                temp_results = mcad_interface.run_and_load(
                    mcad=mcad,
                    voltage=voltage,
                    current_density=current_density,
                    motor_dict=motor_dict,
                    model_dict=model_dict,
                    mot_file_path=mot_file_path,
                    initial_slip=current_slip
                )
                
                if temp_results is None:
                    # Simulation failed completely
                    failed_runs.append({
                        'voltage': voltage,
                        'current_density': current_density,
                        'slip_start': initial_slip_start,
                        'slip_final': current_slip,
                        'iterations': iterations_done,
                        'reason': 'Simulation execution failed',
                        'torque_cv': None,
                        'power_cv': None
                    })
                    print(f"✗ Simulation execution failed at iteration {iteration}\n")
                    break

                last_temp_results = temp_results

                # Check smoothness
                is_smooth, metrics = mcad_interface.check_results_smoothness(
                    temp_results, smoothness_threshold
                )
                final_metrics = metrics
                
                if is_smooth:
                    # Success!
                    results = temp_results
                    print(f"✓ Smooth results obtained at iteration {iteration}\n")
                    break
                
                # Not smooth – choose next slip value
                if iteration < max_iterations:
                    if iteration == 1:
                        # After first failure, try to seed from the slip values
                        # observed at high-torque / high-speed operating points.
                        extracted = mcad_interface.extract_slip_from_results(last_temp_results)
                        if extracted is not None and extracted > current_slip:
                            print(f"  → Using slip extracted from results: {extracted:.5f}")
                            current_slip = extracted
                        else:
                            print(f"  → Extracted slip ({extracted}) not usable; "
                                  f"falling back to increment (+{slip_increment})")
                            current_slip += slip_increment
                    else:
                        current_slip += slip_increment

                    if current_slip > config.QUALITY_CHECK_MAX_SLIP:
                        current_slip = config.QUALITY_CHECK_MAX_SLIP
                else:
                    # Reached max iterations without success
                    failed_runs.append({
                        'voltage': voltage,
                        'current_density': current_density,
                        'slip_start': initial_slip_start,
                        'slip_final': current_slip,
                        'iterations': iterations_done,
                        'reason': f'Max iterations ({max_iterations}) reached without smooth results',
                        'torque_cv': final_metrics.get('torque', None) if final_metrics else None,
                        'power_cv': final_metrics.get('power', None) if final_metrics else None
                    })
                    print(f"✗ Failed to achieve smooth results after {max_iterations} iterations\n")

            
            if results is not None:
                # Store successful result
                all_results.append({
                    'voltage': voltage,
                    'current_density': current_density,
                    'data': results,
                    'slip_final': current_slip,
                    'iterations': iterations_done
                })
                print(f"✓ Run successful (slip={current_slip:.4f}, iterations={iterations_done})\n")
    
    # Decision point: Save to database only if ALL runs succeeded
    successful_runs = len(all_results)
    failed_count = len(failed_runs)
    skipped_count = len(runs_to_skip)
    
    print(f"\n{'='*80}")
    print(f"SUMMARY FOR: {os.path.basename(mot_file_path)}")
    print(f"{'='*80}")
    print(f"Total new simulations attempted: {total_runs}")
    print(f"Successful simulations: {successful_runs}")
    print(f"Failed simulations: {failed_count}")
    print(f"Skipped (already in DB): {skipped_count}")
    
    if failed_count > 0:
        print(f"\n⚠ MOTOR FAILED: {failed_count} run(s) did not achieve smooth results")
        print(f"⚠ NO DATA WILL BE SAVED TO DATABASE for this motor")
        print(f"{'='*80}\n")
        
        # Log the failure
        logger.log_motor_failure(mot_file_path, failed_runs)
        
        return {
            'success': False,
            'motor_name': os.path.basename(mot_file_path),
            'motor_path': mot_file_path,
            'motor_hash': mhash,
            'total_runs': total_runs,
            'successful_runs': 0,  # None saved due to transactional behavior
            'failed_runs': failed_count,
            'error': f'{failed_count} run(s) failed quality check'
        }
    
    # All runs successful - save to database
    if successful_runs > 0:
        print(f"\n✓ All {successful_runs} new run(s) passed quality check")
        print(f"✓ Saving all results to database...")
        
        con = database.sqlite3.connect(db_path)
        try:
            for result_info in all_results:
                database.save_run(
                    con, motor_id, 
                    result_info['voltage'], 
                    result_info['current_density'], 
                    result_info['data']
                )
                print(f"  ✓ Saved: {result_info['voltage']}V, {result_info['current_density']} A/mm² "
                      f"(slip={result_info['slip_final']:.4f}, iter={result_info['iterations']})")
            con.close()
            print(f"✓ All results saved successfully")
        except Exception as e:
            con.close()
            print(f"✗ Database save failed: {e}")
            print(f"⚠ NO DATA SAVED due to database error")
            
            # Log as failure
            logger.log_motor_failure(mot_file_path, [{
                'voltage': 'all',
                'current_density': 'all',
                'slip_start': initial_slip_start,
                'slip_final': 'N/A',
                'iterations': 'N/A',
                'reason': f'Database save error: {e}',
                'torque_cv': None,
                'power_cv': None
            }])
            
            return {
                'success': False,
                'motor_name': os.path.basename(mot_file_path),
                'motor_path': mot_file_path,
                'motor_hash': mhash,
                'total_runs': total_runs,
                'successful_runs': 0,
                'failed_runs': 0,
                'error': f'Database error: {e}'
            }
    else:
        print(f"  (No new runs to save - all already existed in database)")
    
    print(f"{'='*80}\n")
    
    return {
        'success': True,
        'motor_name': os.path.basename(mot_file_path),
        'motor_path': mot_file_path,
        'motor_hash': mhash,
        'total_runs': total_runs,
        'successful_runs': successful_runs,
        'failed_runs': 0,
        'skipped_runs': skipped_count
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
    
    # Create logger with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file_path = f"quality_check_log_{timestamp}.txt"
    logger = QualityCheckLogger(log_file_path)
    print(f"Log file will be saved as: {log_file_path}\n")
    
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
            error_result = {
                'motor_name': os.path.basename(mot_file),
                'motor_path': mot_file,
                'success': False,
                'error': 'File not found'
            }
            results_summary.append(error_result)
            
            # Log as failure
            logger.log_motor_failure(mot_file, [{
                'voltage': 'N/A',
                'current_density': 'N/A',
                'slip_start': 'N/A',
                'slip_final': 'N/A',
                'iterations': 0,
                'reason': 'Motor file not found',
                'torque_cv': None,
                'power_cv': None
            }])
            continue
        
        result = run_motor_with_quality_check(
            mcad=mcad,
            mot_file_path=mot_file,
            model_dict=model_dict,
            db_path=args.db,
            logger=logger,
            max_iterations=args.max_iterations,
            initial_slip_start=args.initial_slip,
            slip_increment=args.slip_increment,
            smoothness_threshold=args.smoothness_threshold
        )
        
        results_summary.append(result)
    
    # Close MotorCAD
    mcad_interface.close_mcad(mcad)
    
    # Write log file
    print(f"\n{'='*80}")
    print("Writing log file...")
    print(f"{'='*80}")
    logger.write_log()
    
    # Print final summary
    print(f"\n{'='*80}")
    print("FINAL SUMMARY")
    print(f"{'='*80}")
    print(f"Total motors processed: {len(motor_files)}")
    
    successful_motors = sum(1 for r in results_summary if r.get('success', False))
    failed_motors = len(motor_files) - successful_motors
    
    print(f"Successful: {successful_motors}")
    print(f"Failed: {failed_motors}")
    
    if failed_motors > 0:
        print("\nFailed motors:")
        for result in results_summary:
            if not result.get('success', False):
                error_msg = result.get('error', 'Unknown error')
                failed_runs = result.get('failed_runs', 0)
                if failed_runs > 0:
                    error_msg = f"{error_msg} ({failed_runs} runs failed quality check)"
                print(f"  - {result.get('motor_path', result.get('motor_name', 'Unknown'))}")
                print(f"    Error: {error_msg}")
        print(f"\n  ⚠ Detailed failure information saved in: {log_file_path}")
    else:
        print(f"\n  ✓ All motors successful! Log saved in: {log_file_path}")
    
    print(f"{'='*80}\n")
    
    return 0 if failed_motors == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
