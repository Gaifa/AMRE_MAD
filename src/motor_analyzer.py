"""
Motor analysis and batch processing module.

This module orchestrates the complete motor analysis workflow:
- Loading motor files
- Checking database for existing results
- Running simulations only when needed
- Storing results in database
- Processing multiple motors in batch

The key feature is intelligent caching: if a motor has already been simulated
with identical parameters, the simulation is skipped.

Author: MotorCAD Analysis Team
Date: February 2026
"""

import os
import sqlite3
from typing import Dict, List, Any, Optional

from . import config
from . import database
from . import mcad_interface
from . import utils


# =============================================================================
# SINGLE MOTOR ANALYSIS
# =============================================================================

def analyze_motor(mcad: Any, mot_file_path: str, model_dict: Dict[str, Any],
                 db_path: str = config.DB_PATH) -> Dict[str, Any]:
    """
    Analyze a single motor across all voltage and current density combinations.
    
    This function implements intelligent caching:
    1. Loads motor and extracts parameters
    2. Checks database for existing results
    3. For each voltage, runs first current density and compares with DB
    4. If match found, skips remaining simulations for that voltage
    5. If no match or no DB entry, runs full sweep and saves results
    
    Args:
        mcad: MotorCAD application object (already initialized)
        mot_file_path: Path to .mot file
        model_dict: Simulation configuration dictionary
        db_path: Path to SQLite database
        
    Returns:
        Dictionary with:
        - 'motor_name': Motor filename
        - 'motor_hash': Unique motor hash
        - 'motor_dict': Motor parameters
        - 'results': List of simulation results
        - 'skipped_voltages': List of voltages that were skipped
        - 'success': Boolean indicating overall success
    """
    motor_name = os.path.basename(mot_file_path)
    print(f"\n{'='*80}")
    print(f"ANALYZING MOTOR: {motor_name}")
    print(f"{'='*80}")
    
    # Initialize result structure
    analysis_result = {
        'motor_name': motor_name,
        'motor_path': mot_file_path,
        'motor_hash': None,
        'motor_dict': None,
        'results': [],
        'skipped_voltages': [],
        'success': False
    }
    
    # Load motor file
    if not mcad_interface.load_motor_file(mcad, mot_file_path):
        print(f"ERROR: Failed to load motor file: {motor_name}\n")
        return analysis_result
    
    # Extract motor parameters
    motor_dict = mcad_interface.get_mcad_variables(mcad)
    
    if not utils.validate_motor_dict(motor_dict):
        print(f"ERROR: Invalid motor parameters for: {motor_name}\n")
        return analysis_result
    
    equiv_csa = motor_dict['Equivalent_CSA']['value']
    print(f"Motor equivalent CSA: {equiv_csa:.3f} mm²")
    
    analysis_result['motor_dict'] = motor_dict
    
    # Build/check MotorLAB model
    if not mcad_interface.check_and_build_model(mcad, motor_dict, model_dict, mot_file_path):
        print(f"ERROR: Failed to build model for: {motor_name}\n")
        return analysis_result
    
    # Initialize database
    database.init_db(db_path)
    con = sqlite3.connect(db_path)
    
    # Get or create motor ID
    mhash = database.motor_hash(motor_dict)
    motor_id = database.get_motor_id(con, mhash, motor_dict)
    analysis_result['motor_hash'] = mhash
    
    print(f"Motor hash: {mhash[:16]}...")
    print(f"Motor ID in database: {motor_id}")
    
    # Process each voltage
    results = []
    skipped_voltages = []
    
    for voltage in model_dict['Battery voltage']:
        print(f"\n{'-'*80}")
        print(f"Processing voltage: {voltage} V")
        print(f"{'-'*80}")
        
        current_densities = model_dict['Current density']
        
        if not current_densities:
            print("Warning: No current densities defined, skipping voltage.")
            continue
        
        # Get first current density for comparison
        J0 = current_densities[0]
        
        # Check if this run exists in database
        existing_run = database.get_run_row(con, motor_id, voltage, J0)
        
        # Always run first current density to compare
        print(f"Running first current density: {J0} A/mm² (for comparison)")
        first_results = mcad_interface.run_and_load(
            mcad, voltage, J0, motor_dict, model_dict, mot_file_path
        )
        
        if first_results is None:
            print(f"ERROR: Failed to run simulation for V={voltage}, J={J0}")
            continue
        
        # If database has this run, compare results
        if existing_run:
            print("Database entry found for this motor/voltage/current_density.")
            print("Comparing results...")
            
            stored_data = database.load_run_data(con, motor_id, voltage, J0)
            
            if stored_data is None:
                print("Warning: Could not load stored data, will re-run all simulations.")
                match = False
            else:
                # Normalize both datasets for comparison
                stored_canon = utils.build_canon_dict_from_mat(stored_data)
                first_canon = utils.build_canon_dict_from_mat(first_results)
                
                # Compare key arrays
                match = True
                for key in config.COMPARISON_KEYS:
                    if not utils.arrays_equal(stored_canon.get(key), first_canon.get(key)):
                        print(f"  Mismatch detected in: {key}")
                        match = False
                        break
                
                if match:
                    print("  ✓ Results match database! Skipping remaining current densities.")
                    skipped_voltages.append(voltage)
                    results.append({
                        'voltage': voltage,
                        'skipped': True,
                        'reason': 'Results match database'
                    })
                    continue
                else:
                    print("  ✗ Results differ from database. Will re-run and save all simulations.")
        else:
            print("No database entry found. Running full sweep.")
        
        # Run full sweep for this voltage
        print(f"Running {len(current_densities)} current density points...")
        
        for J in current_densities:
            print(f"  Simulating: V={voltage} V, J={J} A/mm²... ", end='')
            
            # Use cached first run if available
            if J == J0 and first_results is not None:
                sim_results = first_results
                print("(using cached result)")
            else:
                sim_results = mcad_interface.run_and_load(
                    mcad, voltage, J, motor_dict, model_dict, mot_file_path
                )
                print("done")
            
            if sim_results is None:
                print(f"    ERROR: Failed simulation")
                continue
            
            # Save to database
            try:
                database.save_run(con, motor_id, voltage, J, sim_results)
                print(f"    Saved to database")
            except sqlite3.IntegrityError:
                # Run already exists, skip
                print(f"    Already in database, skipping")
            except Exception as e:
                print(f"    ERROR saving to database: {e}")
            
            # Add to results
            results.append({
                'voltage': voltage,
                'current_density': J,
                'data': sim_results,
                'skipped': False
            })
    
    con.close()
    
    analysis_result['results'] = results
    analysis_result['skipped_voltages'] = skipped_voltages
    analysis_result['success'] = True
    
    print(f"\n{'='*80}")
    print(f"MOTOR ANALYSIS COMPLETE: {motor_name}")
    print(f"  Total simulations run: {len([r for r in results if not r.get('skipped', False)])}")
    print(f"  Voltages skipped: {len(skipped_voltages)}")
    print(f"{'='*80}\n")
    
    return analysis_result


# =============================================================================
# BATCH PROCESSING
# =============================================================================

def analyze_motor_batch(mot_file_paths: List[str], model_dict: Dict[str, Any],
                       db_path: str = config.DB_PATH) -> List[Dict[str, Any]]:
    """
    Analyze multiple motors in batch.
    
    Initializes MotorCAD once and processes all motors sequentially.
    This is more efficient than initializing MotorCAD for each motor.
    
    Args:
        mot_file_paths: List of paths to .mot files
        model_dict: Simulation configuration dictionary
        db_path: Path to SQLite database
        
    Returns:
        List of analysis results (one dict per motor)
        
    Example:
        >>> mot_files = ['/path/to/motor1.mot', '/path/to/motor2.mot']
        >>> results = analyze_motor_batch(mot_files, model_dict)
        >>> for result in results:
        ...     print(f"{result['motor_name']}: {len(result['results'])} runs")
    """
    print(f"\n{'#'*80}")
    print(f"BATCH MOTOR ANALYSIS")
    print(f"{'#'*80}")
    print(f"Total motors to analyze: {len(mot_file_paths)}")
    print(f"Database: {db_path}")
    print(f"{'#'*80}\n")
    
    # Validate model configuration
    if not utils.validate_model_dict(model_dict):
        print("ERROR: Invalid model_dict configuration")
        return []
    
    # Initialize MotorCAD
    try:
        mcad = mcad_interface.initialize_mcad()
    except Exception as e:
        print(f"ERROR: Failed to initialize MotorCAD: {e}")
        return []
    
    # Process each motor
    batch_results = []
    
    for idx, mot_path in enumerate(mot_file_paths, 1):
        print(f"\nProcessing motor {idx}/{len(mot_file_paths)}")
        
        if not os.path.exists(mot_path):
            print(f"ERROR: File not found: {mot_path}")
            batch_results.append({
                'motor_name': os.path.basename(mot_path),
                'motor_path': mot_path,
                'success': False,
                'error': 'File not found'
            })
            continue
        
        try:
            result = analyze_motor(mcad, mot_path, model_dict, db_path)
            batch_results.append(result)
        except Exception as e:
            print(f"ERROR: Exception during motor analysis: {e}")
            batch_results.append({
                'motor_name': os.path.basename(mot_path),
                'motor_path': mot_path,
                'success': False,
                'error': str(e)
            })
    
    # Close MotorCAD
    mcad_interface.close_mcad(mcad)
    
    # Print summary
    print(f"\n{'#'*80}")
    print(f"BATCH ANALYSIS COMPLETE")
    print(f"{'#'*80}")
    print(f"Total motors processed: {len(batch_results)}")
    print(f"Successful: {sum(1 for r in batch_results if r['success'])}")
    print(f"Failed: {sum(1 for r in batch_results if not r['success'])}")
    print(f"{'#'*80}\n")
    
    return batch_results


# =============================================================================
# MOTOR DISCOVERY
# =============================================================================

def find_mot_files(directory: str, recursive: bool = False) -> List[str]:
    """
    Find all .mot files in a directory.
    
    Args:
        directory: Directory to search
        recursive: If True, search subdirectories as well
        
    Returns:
        List of full paths to .mot files
    """
    mot_files = []
    
    if recursive:
        for root, dirs, files in os.walk(directory):
            for filename in files:
                if filename.lower().endswith('.mot'):
                    mot_files.append(os.path.join(root, filename))
    else:
        for filename in os.listdir(directory):
            if filename.lower().endswith('.mot'):
                mot_files.append(os.path.join(directory, filename))
    
    return sorted(mot_files)
