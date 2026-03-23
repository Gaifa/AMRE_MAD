"""
Database management module for MotorCAD simulation results.

This module provides a complete interface to a SQLite database for storing
and retrieving motor simulation results. It handles:
- Database initialization and schema creation
- Motor identification via hashing
- Simulation result storage and retrieval
- Data serialization (numpy arrays <-> BLOBs)

The database schema consists of two main tables:
1. motors: Stores unique motor configurations
2. runs: Stores simulation results for each motor/voltage/current_density combination

Author: MotorCAD Analysis Team
Date: February 2026
"""

import sqlite3
import hashlib
import json
import numpy as np
import io
import datetime
from typing import Dict, List, Optional, Tuple, Any

from . import config


# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================

def init_db(db_path: str = config.DB_PATH) -> None:
    """
    Initialize the SQLite database and create tables if they don't exist.
    
    Creates two tables:
    - motors: Stores unique motor configurations identified by hash
    - runs: Stores simulation results linked to motors
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        None
    """
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    
    # Create motors table
    # motor_hash: SHA256 hash of motor_dict for unique identification
    # motor_json: Full motor configuration as JSON string
    # created_at: Timestamp when motor was first added to database
    cur.execute("""
    CREATE TABLE IF NOT EXISTS motors(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        motor_hash TEXT UNIQUE NOT NULL,
        motor_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""")
    
    # Create runs table
    # Stores simulation results for each combination of motor, voltage, and current density
    # Each performance curve is stored as a BLOB (serialized numpy array)
    save_keys_columns = ", ".join([f"{k} BLOB" for k in config.SAVE_KEYS])
    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS runs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        motor_id INTEGER NOT NULL,
        voltage REAL NOT NULL,
        current_density REAL NOT NULL,
        {save_keys_columns},
        created_at TEXT NOT NULL,
        FOREIGN KEY(motor_id) REFERENCES motors(id),
        UNIQUE(motor_id, voltage, current_density)
    )""")
    
    con.commit()
    con.close()


# =============================================================================
# MOTOR IDENTIFICATION AND MANAGEMENT
# =============================================================================

def motor_hash(motor_dict: Dict[str, Any]) -> str:
    """
    Generate a unique SHA256 hash for a motor configuration.
    
    The hash is computed from the JSON representation of the motor_dict,
    ensuring that identical motor configurations produce identical hashes.
    
    Args:
        motor_dict: Dictionary containing motor parameters and characteristics
        
    Returns:
        Hexadecimal string representation of SHA256 hash
        
    Example:
        >>> motor_hash({'Slot_number': {'value': 24}, 'Pole_number': {'value': 8}})
        'a3f5b8c...'
    """
    # Sort keys to ensure consistent ordering for identical configurations
    json_str = json.dumps(motor_dict, sort_keys=True)
    hash_obj = hashlib.sha256(json_str.encode("utf-8"))
    return hash_obj.hexdigest()


def get_motor_id(con: sqlite3.Connection, mhash: str, motor_dict: Dict[str, Any]) -> int:
    """
    Get or create a motor ID in the database.
    
    If a motor with the given hash exists, returns its ID.
    Otherwise, creates a new motor record and returns the new ID.
    
    Args:
        con: Active SQLite database connection
        mhash: Motor hash (from motor_hash function)
        motor_dict: Complete motor configuration dictionary
        
    Returns:
        Motor ID (integer primary key)
    """
    cur = con.cursor()
    
    # Check if motor already exists
    cur.execute("SELECT id FROM motors WHERE motor_hash=?", (mhash,))
    row = cur.fetchone()
    
    if row:
        return row[0]
    
    # Create new motor record
    cur.execute(
        "INSERT INTO motors(motor_hash, motor_json, created_at) VALUES (?, ?, ?)",
        (mhash, json.dumps(motor_dict), datetime.datetime.utcnow().isoformat())
    )
    con.commit()
    return cur.lastrowid


# =============================================================================
# DATA SERIALIZATION
# =============================================================================

def to_blob(arr: np.ndarray) -> bytes:
    """
    Convert a numpy array to a binary BLOB for database storage.
    
    Uses numpy's save function to serialize the array to a binary format
    that preserves dtype, shape, and all data.
    
    Args:
        arr: Numpy array to serialize
        
    Returns:
        Binary blob (bytes) suitable for SQLite BLOB column
    """
    buf = io.BytesIO()
    np.save(buf, np.asarray(arr))
    return buf.getvalue()


def from_blob(blob: bytes) -> Optional[np.ndarray]:
    """
    Reconstruct a numpy array from a binary BLOB retrieved from database.
    
    Args:
        blob: Binary data from SQLite BLOB column
        
    Returns:
        Reconstructed numpy array, or None if blob is None
    """
    if blob is None:
        return None
    buf = io.BytesIO(blob)
    buf.seek(0)
    return np.load(buf, allow_pickle=True)


# =============================================================================
# SIMULATION RESULTS STORAGE AND RETRIEVAL
# =============================================================================

def get_run_row(con: sqlite3.Connection, motor_id: int, voltage: float, 
                current_density: float) -> Optional[Tuple]:
    """
    Retrieve a complete run record from the database.
    
    Args:
        con: Active SQLite database connection
        motor_id: Motor ID (foreign key to motors table)
        voltage: Battery voltage [V]
        current_density: Current density [A/mm²]
        
    Returns:
        Complete database row as tuple, or None if not found
    """
    cur = con.cursor()
    cur.execute(
        "SELECT * FROM runs WHERE motor_id=? AND voltage=? AND current_density=?",
        (motor_id, float(voltage), float(current_density))
    )
    return cur.fetchone()


def save_run(con: sqlite3.Connection, motor_id: int, voltage: float, 
             current_density: float, mat_data: Dict[str, np.ndarray]) -> None:
    """
    Save simulation results to the database.
    
    Stores all performance curves specified in config.SAVE_KEYS as BLOBs.
    If a run with the same (motor_id, voltage, current_density) exists,
    this will fail due to UNIQUE constraint.
    
    Args:
        con: Active SQLite database connection
        motor_id: Motor ID (foreign key to motors table)
        voltage: Battery voltage [V]
        current_density: Current density [A/mm²]
        mat_data: Dictionary of simulation results (key -> numpy array)
        
    Returns:
        None
        
    Raises:
        sqlite3.IntegrityError: If run already exists
    """
    cur = con.cursor()
    
    # Serialize all arrays to BLOBs
    blobs = []
    for k in config.SAVE_KEYS:
        val = mat_data.get(k, None)
        blobs.append(to_blob(val) if val is not None else None)
    
    # Build dynamic SQL query
    cols = "motor_id, voltage, current_density, " + ", ".join(config.SAVE_KEYS) + ", created_at"
    placeholders = ", ".join(["?"] * (3 + len(config.SAVE_KEYS) + 1))
    
    cur.execute(
        f"INSERT INTO runs({cols}) VALUES ({placeholders})",
        (motor_id, float(voltage), float(current_density), *blobs, 
         datetime.datetime.utcnow().isoformat())
    )
    con.commit()


def load_run_data(con: sqlite3.Connection, motor_id: int, voltage: float, 
                  current_density: float) -> Optional[Dict[str, np.ndarray]]:
    """
    Load simulation results from the database.
    
    Retrieves all performance curves for a specific run and deserializes
    them from BLOBs back to numpy arrays.
    
    Args:
        con: Active SQLite database connection
        motor_id: Motor ID (foreign key to motors table)
        voltage: Battery voltage [V]
        current_density: Current density [A/mm²]
        
    Returns:
        Dictionary mapping key names to numpy arrays, or None if run not found
        
    Example:
        >>> data = load_run_data(con, 1, 24.0, 4.5)
        >>> data['Shaft_Torque']
        array([0.5, 0.8, 1.2, ...])
    """
    row = get_run_row(con, motor_id, voltage, current_density)
    if not row:
        return None
    
    # Row format: id, motor_id, voltage, current_density, <SAVE_KEYS...>, created_at
    # SAVE_KEYS start at index 4
    offset = 4
    data = {}
    
    for i, k in enumerate(config.SAVE_KEYS):
        blob = row[offset + i]
        data[k] = from_blob(blob) if blob is not None else None
    
    return data


# =============================================================================
# QUERY HELPERS
# =============================================================================

def list_all_motors(db_path: str = config.DB_PATH) -> List[Dict[str, Any]]:
    """
    List all motors in the database.
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        List of dictionaries, each containing motor information:
        - id: Motor ID
        - hash: Motor hash
        - created_at: Creation timestamp
        - motor_json: Motor configuration (as dict)
    """
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("SELECT id, motor_hash, created_at, motor_json FROM motors ORDER BY id")
    rows = cur.fetchall()
    con.close()
    
    motors = []
    for r in rows:
        try:
            motor_json = json.loads(r[3])
        except Exception:
            motor_json = r[3]
        
        motors.append({
            'id': r[0],
            'hash': r[1],
            'created_at': r[2],
            'motor_json': motor_json
        })
    
    return motors


def list_runs_for_motor(motor_id: int, db_path: str = config.DB_PATH) -> List[Dict[str, Any]]:
    """
    List all simulation runs for a specific motor.
    
    Args:
        motor_id: Motor ID to query
        db_path: Path to SQLite database file
        
    Returns:
        List of dictionaries, each containing run information:
        - run_id: Run ID
        - voltage: Battery voltage [V]
        - current_density: Current density [A/mm²]
        - created_at: Creation timestamp
    """
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute(
        "SELECT id, voltage, current_density, created_at FROM runs "
        "WHERE motor_id=? ORDER BY voltage, current_density",
        (int(motor_id),)
    )
    rows = cur.fetchall()
    con.close()
    
    return [
        {
            'run_id': r[0],
            'voltage': r[1],
            'current_density': r[2],
            'created_at': r[3]
        }
        for r in rows
    ]


def delete_motor_runs(motor_id: int, db_path: str = config.DB_PATH) -> int:
    """
    Delete all simulation runs for a specific motor.
    
    Useful when you want to force re-simulation of a motor.
    
    Args:
        motor_id: Motor ID whose runs should be deleted
        db_path: Path to SQLite database file
        
    Returns:
        Number of runs deleted
    """
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("DELETE FROM runs WHERE motor_id=?", (int(motor_id),))
    deleted = cur.rowcount
    con.commit()
    con.close()
    return deleted


def delete_runs_by_current_density(current_density: float, db_path: str = config.DB_PATH) -> int:
    """
    Delete all runs across all motors at a specific current density.

    Useful to purge a current density point that needs to be re-simulated
    for every motor in the database.

    Args:
        current_density: Current density [A/mm²] to delete
        db_path: Path to SQLite database file

    Returns:
        Number of runs deleted
    """
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("DELETE FROM runs WHERE current_density=?", (float(current_density),))
    deleted = cur.rowcount
    con.commit()
    con.close()
    return deleted


def delete_run(motor_id: int, voltage: float, current_density: float,
               db_path: str = config.DB_PATH) -> int:
    """
    Delete a single specific run identified by motor, voltage and current density.

    Args:
        motor_id: Motor ID (foreign key to motors table)
        voltage: Battery voltage [V]
        current_density: Current density [A/mm²]
        db_path: Path to SQLite database file

    Returns:
        1 if the run was deleted, 0 if it did not exist
    """
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute(
        "DELETE FROM runs WHERE motor_id=? AND voltage=? AND current_density=?",
        (int(motor_id), float(voltage), float(current_density))
    )
    deleted = cur.rowcount
    con.commit()
    con.close()
    return deleted
