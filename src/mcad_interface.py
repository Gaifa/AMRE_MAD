"""
MotorCAD interface module.

This module handles all interactions with the MotorCAD COM automation API:
- Initialization and connection to MotorCAD
- Motor parameter extraction
- Model building and validation
- Electromagnetic simulation execution
- Results file loading

Author: MotorCAD Analysis Team
Date: February 2026
"""

import os
import win32com.client
import scipy.io
from math import sqrt
from typing import Dict, Any, Optional, Tuple
import numpy as np

from . import config


# =============================================================================
# MOTORCAD CONNECTION
# =============================================================================

def initialize_mcad(suppress_messages: bool = True) -> Any:
    """
    Initialize and connect to MotorCAD via COM automation.
    
    Args:
        suppress_messages: If True, suppress MotorCAD GUI messages
        
    Returns:
        MotorCAD application object
        
    Raises:
        Exception: If MotorCAD cannot be initialized
    """
    print('Initializing MotorCAD connection...')
    
    try:
        mcad = win32com.client.Dispatch("MotorCAD.AppAutomation")
        
        if suppress_messages:
            mcad.SetVariable('MessageDisplayState', config.MESSAGE_DISPLAY_STATE)
        
        print('MotorCAD initialized successfully.')
        return mcad
        
    except Exception as e:
        print(f'ERROR: Failed to initialize MotorCAD: {e}')
        raise


def load_motor_file(mcad: Any, mot_file_path: str) -> bool:
    """
    Load a .mot file into MotorCAD.
    
    Args:
        mcad: MotorCAD application object
        mot_file_path: Full path to .mot file
        
    Returns:
        True if successful, False otherwise
    """
    if not os.path.exists(mot_file_path):
        print(f'ERROR: Motor file not found: {mot_file_path}')
        return False
    
    try:
        print(f'Loading motor file: {os.path.basename(mot_file_path)}')
        mcad.LoadFromFile(mot_file_path)
        return True
    except Exception as e:
        print(f'ERROR: Failed to load motor file: {e}')
        return False


# =============================================================================
# MOTOR PARAMETER EXTRACTION
# =============================================================================

def get_mcad_variables(mcad: Any, var_names: Optional[list] = None) -> Dict[str, Dict[str, Any]]:
    """
    Extract motor parameters from MotorCAD.
    
    Retrieves motor geometric and electrical parameters and computes
    the equivalent conductor cross-sectional area (CSA) accounting for
    parallel paths and winding connection type.
    
    Args:
        mcad: MotorCAD application object
        var_names: List of variable names to extract (None = all)
        
    Returns:
        Dictionary mapping parameter names to {'value': ..., 'description': ...}
        
    Example:
        >>> motor_dict = get_mcad_variables(mcad)
        >>> motor_dict['Slot_number']['value']
        24
        >>> motor_dict['Equivalent_CSA']['value']
        5.67  # mm²
    """
    mapping = config.MOTOR_PARAM_MAPPING
    
    # Determine which parameters to extract
    keys_to_extract = (
        list(mapping.keys()) if var_names is None 
        else [k for k in var_names if k in mapping]
    )
    
    result = {}
    
    # Extract each parameter from MotorCAD
    for key in keys_to_extract:
        mcad_var_name, description = mapping[key]
        try:
            value = mcad.GetVariable(mcad_var_name)[1]
        except Exception as e:
            print(f'Warning: Failed to get variable {mcad_var_name}: {e}')
            value = None
        
        result[key] = {'value': value, 'description': description}
    
    # Compute equivalent CSA
    result['Equivalent_CSA'] = _compute_equivalent_csa(result)
    
    return result


def _compute_equivalent_csa(motor_params: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute equivalent conductor cross-sectional area.
    
    The equivalent CSA accounts for:
    - Armature turn CSA
    - Number of parallel paths
    - Winding connection (Star vs Delta)
    
    For Delta connection, multiply by sqrt(3) due to line-to-phase relationship.
    
    Args:
        motor_params: Dictionary of motor parameters
        
    Returns:
        Dictionary with 'value' and 'description' keys
    """
    def to_float(x):
        """Safe conversion to float."""
        if x is None:
            return None
        try:
            return float(x)
        except Exception:
            return None
    
    # Extract relevant parameters
    winding_conn = motor_params.get('winding_connection', {}).get('value')
    armature_csa = motor_params.get('ArmatureTurnCSA', {}).get('value')
    parallel_paths = motor_params.get('ParallelPaths', {}).get('value')
    
    # Convert to floats
    wc_float = to_float(winding_conn)
    ac_float = to_float(armature_csa)
    pp_float = to_float(parallel_paths)
    
    # Compute equivalent CSA
    equiv_csa = None
    
    if ac_float is not None and pp_float is not None:
        if wc_float is None:
            # Assume Star connection if not specified
            equiv_csa = ac_float * pp_float
        else:
            try:
                wc_int = int(wc_float)
                if wc_int == 0:  # Star connection
                    equiv_csa = ac_float * pp_float
                elif wc_int == 1:  # Delta connection
                    equiv_csa = ac_float * pp_float * sqrt(3)
                else:
                    # Unknown connection type, use Star formula
                    equiv_csa = ac_float * pp_float
            except Exception:
                equiv_csa = ac_float * pp_float
    
    return {
        'value': equiv_csa,
        'description': (
            'Equivalent CSA (mm²) computed from ArmatureTurnCSA, '
            'ParallelPaths and WindingConnection'
        )
    }


# =============================================================================
# MODEL BUILDING
# =============================================================================

import math

def _geq(a, b, rel_tol=1e-7, abs_tol=1e-8):
    """Return True if a >= b within a tolerance."""
    return a > b or math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol)

def check_and_build_model(mcad: Any, motor_dict: Dict[str, Any], 
                          model_dict: Dict[str, Any], mot_file_path: str) -> bool:
    """
    Check if MotorLAB model needs rebuilding and build if necessary.
    The model needs rebuilding if:
    - Build speed is lower than required maximum speed
    - Build current is lower than required maximum current
    - Saturation, AC loss, or iron loss currents are lower than required maximum current
    """
    import os
    try:
        # Assicura che il percorso del file motore sia assoluto
        mot_file_path = os.path.abspath(mot_file_path)

        # Get current build parameters
        build_speed = float(mcad.GetVariable('ModelBuildSpeed_MotorLAB')[1])
        build_current = float(mcad.GetVariable('MaxModelCurrent_RMS_MotorLAB')[1])
        saturation_current = float(mcad.GetVariable('LabModel_Saturation_StatorCurrent_RMS')[1])
        ac_loss_current = float(mcad.GetVariable('LabModel_ACLoss_StatorCurrent_RMS')[1])
        iron_loss_current = float(mcad.GetVariable('LabModel_IronLoss_StatorCurrent_RMS')[1])

        # Calculate required build current
        equiv_csa = motor_dict['Equivalent_CSA']['value']
        if equiv_csa is None:
            print('ERROR: Equivalent CSA is None, cannot build model')
            return False

        required_current = float(model_dict['Maximum current density'] * equiv_csa)
        max_speed = float(model_dict['Maximum speed'])

        # debug print
        print(f"Current build parameters:")
        print(f"  Build speed: {build_speed:.8f} rpm")
        print(f"  Build current: {build_current:.8f} A")    
        print(f"  Saturation current: {saturation_current:.8f} A")
        print(f"  AC loss current: {ac_loss_current:.8f} A")
        print(f"  Iron loss current: {iron_loss_current:.8f} A")
        print(f"  Required current: {required_current:.8f} A")
        print(f"  Required speed: {max_speed:.8f} rpm")
        print(f"Diffs: speed={build_speed-max_speed}, build={build_current-required_current}, sat={saturation_current-required_current}, ac={ac_loss_current-required_current}, iron={iron_loss_current-required_current}")

        # Check if rebuild is needed (with tolerance)
        if (
            _geq(build_speed, max_speed)
            and _geq(build_current, required_current)
            and _geq(saturation_current, required_current)
            and _geq(ac_loss_current, required_current)
            and _geq(iron_loss_current, required_current)
        ):
            print("Model already built with sufficient parameters.\n")
            return True

        # Model needs rebuilding
        print("Building MotorLAB model...")
        print(f"  Target speed: {max_speed} rpm")
        print(f"  Target current: {required_current:.2f} A")

        mcad.SetVariable("HybridACLossMethod",1) # 0=analytical, 1=FEA-hybrid, 2=FEA full
        mcad.SetVariable('ModelBuildSpeed_MotorLAB', max_speed)
        mcad.SetVariable('MaxModelCurrent_RMS_MotorLAB', required_current)
        mcad.SetVariable('BuildSatModel_MotorLAB', True)
        mcad.SetVariable('BuildLossModel_MotorLAB', True)
        mcad.SetVariable('LossModel_Lab', 1)  # 0=analytical, 1=FEA-based

        mcad.SetMotorLABContext()
        mcad.BuildModel_Lab()

        # Save updated model
        mcad.SaveToFile(mot_file_path)
        print(f"Model built and saved successfully at {mot_file_path}\n")

        return True

    except Exception as e:
        print(f'ERROR: Failed to build model: {e}')
        return False

# =============================================================================
# SIMULATION EXECUTION
# =============================================================================


def check_results_smoothness(results: Dict[str, Any], 
                            smoothness_threshold: float = 0.15) -> Tuple[bool, Dict[str, float]]:
    """
    Check if torque and power results are smooth.
    
    Evaluates smoothness by calculating the coefficient of variation (CV) of 
    differences between consecutive points in the torque and power curves.
    A lower CV indicates smoother results.
    
    Args:
        results: Dictionary containing simulation results with 'Shaft_Torque' and 'Shaft_Power' keys
        smoothness_threshold: Maximum acceptable CV for relative variation (default 0.15 = 15%)
        
    Returns:
        Tuple of (is_smooth, metrics_dict) where:
            - is_smooth: True if results pass smoothness criteria
            - metrics_dict: Dictionary with CV values for 'torque' and 'power'
            
    Example:
        >>> is_smooth, metrics = check_results_smoothness(results)
        >>> if not is_smooth:
        ...     print(f"Torque CV: {metrics['torque']:.3f}, Power CV: {metrics['power']:.3f}")
    """
    metrics = {}
    
    try:
        # Extract torque and power arrays
        torque = results.get('Shaft_Torque')
        power = results.get('Shaft_Power')
        
        if torque is None or power is None:
            print('Warning: Missing torque or power data for smoothness check')
            return False, {}
        
        # Flatten arrays if needed
        torque = np.atleast_1d(torque).flatten()
        power = np.atleast_1d(power).flatten()
        
        # Need at least 3 points to check smoothness
        if len(torque) < 3 or len(power) < 3:
            print('Warning: Insufficient data points for smoothness check')
            return False, {}
        
        # Calculate differences between consecutive points
        torque_diff = np.abs(np.diff(torque))
        power_diff = np.abs(np.diff(power))
        
        # Calculate coefficient of variation (CV) of differences
        # CV = std(diff) / mean(abs(values))
        # This gives a relative measure of oscillation
        torque_mean = np.mean(np.abs(torque[torque != 0])) if np.any(torque != 0) else 1.0
        power_mean = np.mean(np.abs(power[power != 0])) if np.any(power != 0) else 1.0
        
        torque_cv = np.std(torque_diff) / torque_mean if torque_mean > 0 else float('inf')
        power_cv = np.std(power_diff) / power_mean if power_mean > 0 else float('inf')
        
        metrics['torque'] = float(torque_cv)
        metrics['power'] = float(power_cv)
        
        # Results are smooth if both CVs are below threshold
        is_smooth = (torque_cv < smoothness_threshold) and (power_cv < smoothness_threshold)
        
        if is_smooth:
            print(f'✓ Results are smooth: Torque CV={torque_cv:.4f}, Power CV={power_cv:.4f}')
        else:
            print(f'✗ Results not smooth: Torque CV={torque_cv:.4f}, Power CV={power_cv:.4f} (threshold={smoothness_threshold})')
        
        return is_smooth, metrics
        
    except Exception as e:
        print(f'ERROR: Smoothness check failed: {e}')
        return False, {}


def run_mcad_simulation(mcad: Any, voltage: float, current_density: float,
                        motor_dict: Dict[str, Any], model_dict: Dict[str, Any],
                        initial_slip: float = 0.01) -> bool:
    """
    Execute a single MotorCAD electromagnetic simulation.
    
    Configures MotorCAD with specified voltage and current density,
    then runs the electromagnetic calculation using MotorLAB.
    
    Args:
        mcad: MotorCAD application object
        voltage: DC bus voltage [V]
        current_density: Current density [A/mm²]
        motor_dict: Motor parameters dictionary
        model_dict: Simulation configuration dictionary
        initial_slip: Initial slip value for MotorLAB convergence (default: 0.01)
        
    Returns:
        True if simulation completed successfully, False otherwise
    """
    try:
        # Calculate RMS current from current density and equivalent CSA
        equiv_csa = motor_dict['Equivalent_CSA']['value']
        if equiv_csa is None:
            print('ERROR: Equivalent CSA is None')
            return False
        
        rms_current = current_density * equiv_csa
        
        # Configure simulation parameters
        mcad.ShowMagneticContext()
        mcad.DisplayScreen('Scripting')
        
        mcad.SetVariable("EmagneticCalcType_Lab", 0)
        mcad.SetVariable("DCBusVoltage", voltage)
        mcad.SetVariable("ModulationIndex_MotorLAB", config.MODULATION_INDEX)
        mcad.SetVariable("CurrentSpec_MotorLAB", 1)
        mcad.SetVariable("CurrentDefinition", 1)
        mcad.SetVariable("IM_InitialSlip_MotorLAB", initial_slip)
        mcad.SetVariable("Imax_RMS_MotorLAB", rms_current)
        mcad.SetVariable("SpeedMax_MotorLAB", model_dict['Maximum speed'])
        mcad.SetVariable('Speedinc_MotorLAB', config.SPEED_INCREMENT)
        mcad.SetVariable('SpeedMin_MotorLAB', model_dict['Minimum speed'])
        mcad.SetVariable("AutoShowResults_MotorLAB", True)
        
        # Run electromagnetic calculation
        mcad.CalculateMagnetic_Lab()
        
        return True
        
    except Exception as e:
        print(f'ERROR: Simulation failed: {e}')
        return False


def load_simulation_results(mot_file_path: str) -> Optional[Dict[str, Any]]:
    """
    Load simulation results from MotorCAD output .mat file.
    
    Extracts the performance curves specified in config.SAVE_KEYS
    from the MotorLAB electromagnetic data file.
    
    Args:
        mot_file_path: Path to .mot file (results are in subfolder)
        
    Returns:
        Dictionary mapping key names to numpy arrays, or None on failure
        
    Example:
        >>> results = load_simulation_results('path/to/motor.mot')
        >>> results['Shaft_Torque']
        array([0.5, 0.8, 1.2, ...])
    """
    try:
        # Construct path to results file
        model_folder = os.path.splitext(mot_file_path)[0]
        mat_file_path = os.path.join(model_folder, config.LAB_SUBDIR, config.MAT_FILENAME)
        
        if not os.path.exists(mat_file_path):
            print(f'ERROR: Results file not found: {mat_file_path}')
            return None
        
        # Load .mat file
        data = scipy.io.loadmat(mat_file_path)
        
        # Extract relevant keys
        results = {}
        for key in config.SAVE_KEYS:
            results[key] = data.get(key, None)
        
        return results
        
    except Exception as e:
        print(f'ERROR: Failed to load results: {e}')
        return None


def run_and_load(mcad: Any, voltage: float, current_density: float,
                motor_dict: Dict[str, Any], model_dict: Dict[str, Any],
                mot_file_path: str, initial_slip: float = 0.01) -> Optional[Dict[str, Any]]:
    """
    Convenience function: run simulation and load results.
    
    Combines run_mcad_simulation and load_simulation_results.
    
    Args:
        mcad: MotorCAD application object
        voltage: DC bus voltage [V]
        current_density: Current density [A/mm²]
        motor_dict: Motor parameters dictionary
        model_dict: Simulation configuration dictionary
        mot_file_path: Path to .mot file
        initial_slip: Initial slip value for MotorLAB convergence (default: 0.01)
        
    Returns:
        Dictionary of simulation results, or None on failure
    """
    success = run_mcad_simulation(mcad, voltage, current_density, motor_dict, model_dict, initial_slip)
    
    if not success:
        return None
    
    return load_simulation_results(mot_file_path)


def run_and_load_with_quality_check(mcad: Any, voltage: float, current_density: float,
                                   motor_dict: Dict[str, Any], model_dict: Dict[str, Any],
                                   mot_file_path: str,
                                   max_iterations: Optional[int] = None,
                                   initial_slip_start: Optional[float] = None,
                                   slip_increment: Optional[float] = None,
                                   smoothness_threshold: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """
    Run simulation with automatic quality checking and IM_InitialSlip_MotorLAB adjustment.
    
    This function iteratively runs the simulation, checks the smoothness of torque and power
    results, and increases the initial slip parameter if results are not smooth. This process
    continues until smooth results are obtained or maximum iterations are reached.
    
    Args:
        mcad: MotorCAD application object
        voltage: DC bus voltage [V]
        current_density: Current density [A/mm²]
        motor_dict: Motor parameters dictionary
        model_dict: Simulation configuration dictionary
        mot_file_path: Path to .mot file
        max_iterations: Maximum number of retry attempts (default: from config)
        initial_slip_start: Starting value for initial slip (default: from config)
        slip_increment: Amount to increase slip each iteration (default: from config)
        smoothness_threshold: Maximum acceptable CV for smoothness (default: from config)
        
    Returns:
        Dictionary of simulation results with smooth torque/power, or None on failure
        
    Example:
        >>> results = run_and_load_with_quality_check(mcad, 48, 7.5, motor_dict, model_dict, 'motor.mot')
        >>> if results:
        ...     print("Smooth results obtained!")
    """
    # Use config defaults if not provided
    if max_iterations is None:
        max_iterations = config.QUALITY_CHECK_MAX_ITERATIONS
    if initial_slip_start is None:
        initial_slip_start = config.QUALITY_CHECK_INITIAL_SLIP_START
    if slip_increment is None:
        slip_increment = config.QUALITY_CHECK_SLIP_INCREMENT
    if smoothness_threshold is None:
        smoothness_threshold = config.QUALITY_CHECK_SMOOTHNESS_THRESHOLD
    
    max_slip = config.QUALITY_CHECK_MAX_SLIP
    
    print(f"\n{'='*70}")
    print(f"Starting simulation with quality checking")
    print(f"  Voltage: {voltage}V, Current Density: {current_density} A/mm²")
    print(f"  Initial Slip Range: {initial_slip_start} to {max_slip}")
    print(f"  Smoothness Threshold: {smoothness_threshold}")
    print(f"{'='*70}\n")
    
    current_slip = initial_slip_start
    
    for iteration in range(1, max_iterations + 1):
        print(f"\n--- Iteration {iteration}/{max_iterations} ---")
        print(f"Trying IM_InitialSlip_MotorLAB = {current_slip:.4f}")
        
        # Run simulation with current slip value
        results = run_and_load(mcad, voltage, current_density, motor_dict, model_dict, 
                              mot_file_path, initial_slip=current_slip)
        
        if results is None:
            print(f"ERROR: Simulation failed at iteration {iteration}")
            return None
        
        # Check smoothness of results
        is_smooth, metrics = check_results_smoothness(results, smoothness_threshold)
        
        if is_smooth:
            print(f"\n{'='*70}")
            print(f"✓ SUCCESS: Smooth results obtained after {iteration} iteration(s)")
            print(f"  Final IM_InitialSlip_MotorLAB: {current_slip:.4f}")
            print(f"  Torque CV: {metrics.get('torque', 0):.4f}")
            print(f"  Power CV: {metrics.get('power', 0):.4f}")
            print(f"{'='*70}\n")
            return results
        
        # Results not smooth, increase slip for next iteration
        if iteration < max_iterations:
            current_slip += slip_increment
            
            # Check if we've exceeded maximum slip
            if current_slip > max_slip:
                print(f"\nWarning: Reached maximum slip value ({max_slip})")
                current_slip = max_slip
                # Continue with max slip value - this is the last attempt
                if iteration == max_iterations - 1:
                    print("This is the final iteration with maximum slip value.")
        else:
            print(f"\n{'='*70}")
            print(f"⚠ WARNING: Maximum iterations reached without smooth results")
            print(f"  Last IM_InitialSlip_MotorLAB: {current_slip:.4f}")
            print(f"  Last Torque CV: {metrics.get('torque', 0):.4f}")
            print(f"  Last Power CV: {metrics.get('power', 0):.4f}")
            print(f"  Returning last results anyway.")
            print(f"{'='*70}\n")
            return results
    
    # Should not reach here, but return last results as fallback
    return results


def close_mcad(mcad: Any) -> None:
    """
    Safely close MotorCAD connection.
    
    Args:
        mcad: MotorCAD application object
    """
    try:
        mcad.Quit()
        print('MotorCAD connection closed.')
    except Exception as e:
        print(f'Warning: Error closing MotorCAD: {e}')
