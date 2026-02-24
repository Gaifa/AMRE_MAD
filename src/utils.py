"""
Utility functions for data processing and comparison.

This module provides helper functions for:
- Data normalization (handling different key naming conventions)
- Array comparison with tolerance
- Key lookup with fuzzy matching

Author: MotorCAD Analysis Team
Date: February 2026
"""

import numpy as np
from typing import Dict, Optional, Any

from . import config


# =============================================================================
# KEY NORMALIZATION AND FUZZY LOOKUP
# =============================================================================

def try_keys(data_dict: Optional[Dict[str, Any]], *key_variants) -> Optional[Any]:
    """
    Attempt to retrieve a value from a dictionary using multiple key variants.
    
    This function handles inconsistencies in key naming across different
    MotorCAD versions or .mat file formats. It tries exact matches first,
    then tries normalized (lowercase, underscore) versions.
    
    Args:
        data_dict: Dictionary to search (may be None)
        *key_variants: Multiple possible key names to try
        
    Returns:
        Value if found, None otherwise
        
    Example:
        >>> data = {'Shaft_Torque': [1,2,3], 'Speed': [100,200,300]}
        >>> try_keys(data, 'shaft_torque', 'Shaft_Torque', 'SHAFT_TORQUE')
        [1, 2, 3]
    """
    if data_dict is None:
        return None
    
    # Try exact matches first
    for key_name in key_variants:
        if key_name in data_dict and data_dict[key_name] is not None:
            return data_dict[key_name]
    
    # Try normalized matching (lowercase, replace spaces with underscores)
    for existing_key in data_dict.keys():
        if existing_key is None:
            continue
        
        normalized_existing = existing_key.lower().replace(" ", "_")
        
        for key_name in key_variants:
            normalized_variant = key_name.lower().replace(" ", "_")
            if normalized_existing == normalized_variant:
                return data_dict[existing_key]
    
    return None


def build_canon_dict_from_mat(mat_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a canonicalized dictionary from MotorCAD .mat data.
    
    Converts various possible key naming conventions to a standard set
    defined in config.CANON_KEYS. This ensures consistent data access
    regardless of the source format.
    
    Args:
        mat_data: Raw data dictionary from .mat file or database
        
    Returns:
        Dictionary with canonical key names
        
    Example:
        >>> raw = {'Shaft_Torque': [1,2,3], 'SPEED': [100,200,300]}
        >>> canon = build_canon_dict_from_mat(raw)
        >>> canon['shaft_torque']
        [1, 2, 3]
        >>> canon['speed']
        [100, 200, 300]
    """
    out = {}
    
    for canon_key in config.CANON_KEYS:
        # Try multiple common variations of each key
        # e.g., for "shaft_torque" try: "shaft_torque", "Shaft_Torque", "SHAFT_TORQUE", "Shaft Torque"
        value = try_keys(
            mat_data,
            canon_key,                          # lowercase with underscore
            canon_key.title(),                  # Title Case With Underscore
            canon_key.upper(),                  # UPPERCASE WITH UNDERSCORE
            canon_key.replace("_", " ").title() # Title Case With Spaces
        )
        out[canon_key] = value
    
    return out


# =============================================================================
# ARRAY NORMALIZATION AND COMPARISON
# =============================================================================

def normalise_array(arr: Optional[Any]) -> Optional[np.ndarray]:
    """
    Normalize an array-like object to a 1D numpy array.
    
    Handles various input formats:
    - Removes singleton dimensions
    - Flattens multi-dimensional arrays
    - Converts to float dtype if possible
    
    Args:
        arr: Array-like object (list, numpy array, nested array, etc.)
        
    Returns:
        1D numpy array, or None if input is None
        
    Example:
        >>> normalise_array([[1, 2], [3, 4]])
        array([1., 2., 3., 4.])
        >>> normalise_array(np.array([[[5]]]))
        array([5.])
    """
    if arr is None:
        return None
    
    # Convert to numpy array
    arr_np = np.asarray(arr)
    
    # Remove singleton dimensions (e.g., (1, 100, 1) -> (100,))
    arr_np = np.squeeze(arr_np)
    
    # Attempt conversion to float for numerical comparison
    try:
        return arr_np.astype(float).flatten()
    except Exception:
        # If conversion fails (e.g., string data), just flatten
        return arr_np.flatten()


def arrays_equal(a: Optional[Any], b: Optional[Any], 
                 rtol: float = config.RTOL, atol: float = config.ATOL) -> bool:
    """
    Compare two arrays for equality within tolerance.
    
    Uses numpy's allclose function with specified tolerances.
    Handles edge cases:
    - None values (returns False if either is None)
    - Shape mismatches (returns False)
    - NaN values (treats NaN == NaN as True)
    
    The comparison uses the formula:
        |a - b| <= (atol + rtol * |b|)
    
    Args:
        a: First array (can be None)
        b: Second array (can be None)
        rtol: Relative tolerance (default from config)
        atol: Absolute tolerance (default from config)
        
    Returns:
        True if arrays are equal within tolerance, False otherwise
        
    Example:
        >>> arrays_equal([1.0, 2.0, 3.0], [1.0001, 2.0001, 3.0001])
        True
        >>> arrays_equal([1.0, 2.0], [1.0, 2.0, 3.0])
        False
    """
    # Handle None cases
    if a is None or b is None:
        return False
    
    # Normalize both arrays
    try:
        a_norm = normalise_array(a)
        b_norm = normalise_array(b)
    except Exception:
        return False
    
    # Check shape compatibility
    if a_norm.shape != b_norm.shape:
        return False
    
    # Perform element-wise comparison with tolerance
    # equal_nan=True treats NaN == NaN as True
    try:
        return np.allclose(a_norm, b_norm, rtol=rtol, atol=atol, equal_nan=True)
    except Exception:
        return False


# =============================================================================
# DATA VALIDATION
# =============================================================================

def validate_motor_dict(motor_dict: Dict[str, Any]) -> bool:
    """
    Validate that a motor dictionary contains required fields.
    
    Checks for the presence of critical motor parameters needed for simulation.
    
    Args:
        motor_dict: Motor configuration dictionary
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ['Equivalent_CSA']
    
    for field in required_fields:
        if field not in motor_dict:
            return False
        if motor_dict[field].get('value') is None:
            return False
    
    return True


def validate_model_dict(model_dict: Dict[str, Any]) -> bool:
    """
    Validate that a model configuration dictionary contains required fields.
    
    Args:
        model_dict: Model configuration dictionary
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = [
        'Maximum speed',
        'Minimum speed',
        'Maximum current density',
        'Battery voltage',
        'Current density'
    ]
    
    for field in required_fields:
        if field not in model_dict:
            return False
    
    # Check that lists are not empty
    if not model_dict['Battery voltage']:
        return False
    if not model_dict['Current density']:
        return False
    
    return True


def summarize_array(arr: Optional[np.ndarray], name: str = "Array") -> str:
    """
    Generate a human-readable summary of an array.
    
    Args:
        arr: Numpy array to summarize
        name: Name to display for the array
        
    Returns:
        Formatted string with array statistics
        
    Example:
        >>> print(summarize_array(np.array([1, 2, 3, 4, 5]), "Torque"))
        Torque: shape=(5,), dtype=int64, min=1.00, max=5.00, mean=3.00
    """
    if arr is None:
        return f"{name}: None"
    
    arr = np.asarray(arr)
    
    try:
        min_val = np.nanmin(arr)
        max_val = np.nanmax(arr)
        mean_val = np.nanmean(arr)
        return (f"{name}: shape={arr.shape}, dtype={arr.dtype}, "
                f"min={min_val:.2f}, max={max_val:.2f}, mean={mean_val:.2f}")
    except Exception:
        return f"{name}: shape={arr.shape}, dtype={arr.dtype}"
