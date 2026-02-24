"""
MotorCAD Simulation Framework - Web-Based GUI

Alternative GUI using Flask web framework (works in any browser).
No tkinter required.

Usage:
    python scripts/gui_web.py
    Then open browser at: http://localhost:5000

Author: MotorCAD Analysis Team
Date: February 2026
"""

import sys
import os
import json
import threading
import webbrowser
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src import config, motor_analyzer, database

try:
    from flask import Flask, render_template, request, jsonify, send_file
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False
    print("ERROR: Flask is not installed.")
    print("Install with: pip install flask")
    sys.exit(1)

try:
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import io
    import base64
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

app = Flask(__name__)
app.config['SECRET_KEY'] = 'motorcad-sim-framework-2026'

# Global state
simulation_status = {
    'running': False,
    'progress': '',
    'log': []
}

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MotorCAD Simulation Framework</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 { font-size: 2em; margin-bottom: 10px; }
        .header p { opacity: 0.9; }
        .tabs {
            display: flex;
            background: #f8f9fa;
            border-bottom: 2px solid #dee2e6;
        }
        .tab {
            flex: 1;
            padding: 15px;
            text-align: center;
            cursor: pointer;
            background: #f8f9fa;
            border: none;
            font-size: 16px;
            transition: all 0.3s;
        }
        .tab:hover { background: #e9ecef; }
        .tab.active {
            background: white;
            border-bottom: 3px solid #667eea;
            font-weight: bold;
        }
        .tab-content {
            display: none;
            padding: 30px;
        }
        .tab-content.active { display: block; }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: 600;
            color: #333;
        }
        .form-group input, .form-group select, .form-group textarea {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        .form-group textarea {
            min-height: 100px;
            font-family: monospace;
        }
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.3s;
            margin-right: 10px;
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(102,126,234,0.4); }
        .btn-secondary {
            background: #6c757d;
            color: white;
        }
        .btn-secondary:hover { background: #5a6268; }
        .log-area {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 15px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            max-height: 400px;
            overflow-y: auto;
            white-space: pre-wrap;
        }
        .table-container {
            overflow-x: auto;
            margin-top: 20px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background: #f8f9fa;
            font-weight: 600;
            position: sticky;
            top: 0;
        }
        tr:hover { background: #f8f9fa; }
        .status-bar {
            background: #343a40;
            color: white;
            padding: 10px 30px;
            font-size: 14px;
        }
        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        .card {
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 20px;
            background: #fafafa;
        }
        .card h3 {
            margin-bottom: 15px;
            color: #667eea;
        }
        .alert {
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .alert-info {
            background: #d1ecf1;
            border: 1px solid #bee5eb;
            color: #0c5460;
        }
        .alert-success {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        .plot-container {
            text-align: center;
            margin-top: 20px;
        }
        .plot-container img {
            max-width: 100%;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚡ MotorCAD Simulation Framework</h1>
            <p>Web-Based Interface for Motor Analysis</p>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="showTab('simulations')">Run Simulations</button>
            <button class="tab" onclick="showTab('results')">View Results</button>
            <button class="tab" onclick="showTab('plot')">Plot Results</button>
            <button class="tab" onclick="showTab('about')">About</button>
        </div>
        
        <!-- SIMULATIONS TAB -->
        <div id="simulations" class="tab-content active">
            <h2>Run Simulations</h2>
            
            <div class="alert alert-info">
                <strong>Note:</strong> Use the command line for selecting motor files. This web interface shows results and configuration only.
                Run: <code>python scripts/run_simulations.py --help</code>
            </div>
            
            <div class="card">
                <h3>Quick Start</h3>
                <p>To run simulations, use these commands in your terminal:</p>
                <div class="log-area" style="max-height: 200px;">
# Single motor
python scripts/run_simulations.py --motor "motors/D106 H65 25sp DT ( 2x0.63 + 2x0.5 ).mot"

# Directory of motors
python scripts/run_simulations.py --directory "motors"

# From list file
python scripts/run_simulations.py --list motors_to_simulate.txt
                </div>
            </div>
            
            <div class="grid-2" style="margin-top: 20px;">
                <div class="card">
                    <h3>Current Configuration</h3>
                    <div class="form-group">
                        <label>Max Speed (rpm):</label>
                        <input type="number" id="max_speed" value="5000">
                    </div>
                    <div class="form-group">
                        <label>Min Speed (rpm):</label>
                        <input type="number" id="min_speed" value="50">
                    </div>
                    <div class="form-group">
                        <label>Max Current Density (A/mm²):</label>
                        <input type="number" id="max_current" value="15" step="0.1">
                    </div>
                </div>
                
                <div class="card">
                    <h3>Sweep Parameters</h3>
                    <div class="form-group">
                        <label>Battery Voltages (comma-separated):</label>
                        <input type="text" id="voltages" value="24, 48, 80, 96, 120, 144">
                    </div>
                    <div class="form-group">
                        <label>Current Densities (comma-separated):</label>
                        <input type="text" id="currents" value="4, 4.5, 5, 5.5, 7, 7.5, 8, 13">
                    </div>
                </div>
            </div>
            
            <div style="margin-top: 20px;">
                <button class="btn btn-primary" onclick="saveConfig()">Save Configuration</button>
                <button class="btn btn-secondary" onclick="loadConfig()">Load Configuration</button>
            </div>
        </div>
        
        <!-- RESULTS TAB -->
        <div id="results" class="tab-content">
            <h2>View Results</h2>
            <button class="btn btn-primary" onclick="loadMotors()">Refresh Motor List</button>
            
            <div class="table-container">
                <table id="motorsTable">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Diameter (mm)</th>
                            <th>Length (mm)</th>
                            <th>Turns/Coil</th>
                            <th>Connection</th>
                            <th>Created</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="motorsTableBody">
                        <tr><td colspan="7" style="text-align:center;">Click "Refresh Motor List" to load data</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- PLOT TAB -->
        <div id="plot" class="tab-content">
            <h2>Plot Results</h2>
            
            <div class="grid-2">
                <div class="form-group">
                    <label>Motor ID:</label>
                    <input type="number" id="plot_motor_id" placeholder="e.g., 1">
                </div>
                <div class="form-group">
                    <label>Voltage (V):</label>
                    <input type="number" id="plot_voltage" placeholder="e.g., 48">
                </div>
            </div>
            
            <div class="grid-2">
                <div class="form-group">
                    <label>Current Density (A/mm²):</label>
                    <input type="number" id="plot_current" placeholder="e.g., 7" step="0.1">
                </div>
                <div class="form-group">
                    <label>Plot Type:</label>
                    <select id="plot_type">
                        <option value="all">All Curves</option>
                        <option value="torque">Torque-Speed</option>
                        <option value="power">Power-Speed</option>
                        <option value="efficiency">Efficiency-Speed</option>
                    </select>
                </div>
            </div>
            
            <button class="btn btn-primary" onclick="generatePlot()">Generate Plot</button>
            
            <div class="plot-container" id="plotContainer">
                <p style="color: #999;">Plot will appear here after generation</p>
            </div>
        </div>
        
        <!-- ABOUT TAB -->
        <div id="about" class="tab-content">
            <h2>About MotorCAD Simulation Framework</h2>
            
            <div class="card">
                <h3>Version Information</h3>
                <p><strong>Version:</strong> 1.0 (Web Interface)</p>
                <p><strong>Date:</strong> February 2026</p>
                <p><strong>Author:</strong> MotorCAD Analysis Team</p>
            </div>
            
            <div class="card" style="margin-top: 20px;">
                <h3>Features</h3>
                <ul style="line-height: 2em; padding-left: 20px;">
                    <li>Batch motor simulation with intelligent caching</li>
                    <li>Database storage of simulation results</li>
                    <li>Performance curve visualization</li>
                    <li>Multi-voltage and multi-current density sweep</li>
                    <li>Web-based interface (no tkinter required)</li>
                </ul>
            </div>
            
            <div class="card" style="margin-top: 20px;">
                <h3>Usage</h3>
                <p>This web interface provides viewing and plotting capabilities. For running simulations, use the command-line interface:</p>
                <div class="log-area" style="max-height: 150px; margin-top: 10px;">
python scripts/run_simulations.py --motor "path/to/motor.mot"
python scripts/view_results.py  # Alternative CLI viewer
                </div>
            </div>
            
            <div class="card" style="margin-top: 20px;">
                <h3>Requirements</h3>
                <ul style="line-height: 2em; padding-left: 20px;">
                    <li>Windows OS (for MotorCAD COM automation)</li>
                    <li>MotorCAD installed and licensed</li>
                    <li>Python 3.8+</li>
                    <li>Flask (for web interface): <code>pip install flask</code></li>
                    <li>Matplotlib (optional, for plotting): <code>pip install matplotlib</code></li>
                </ul>
            </div>
        </div>
        
        <div class="status-bar">
            <span id="statusText">Ready</span>
        </div>
    </div>
    
    <script>
        function showTab(tabName) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Show selected tab
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
            
            updateStatus('Switched to ' + tabName + ' tab');
        }
        
        function updateStatus(message) {
            document.getElementById('statusText').textContent = message;
        }
        
        async function loadMotors() {
            updateStatus('Loading motors from database...');
            try {
                const response = await fetch('/api/motors');
                const data = await response.json();
                
                const tbody = document.getElementById('motorsTableBody');
                tbody.innerHTML = '';
                
                if (data.motors.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">No motors found in database</td></tr>';
                } else {
                    data.motors.forEach(motor => {
                        const row = tbody.insertRow();
                        row.innerHTML = `
                            <td>${motor.id}</td>
                            <td>${motor.diameter}</td>
                            <td>${motor.length}</td>
                            <td>${motor.turns}</td>
                            <td>${motor.connection}</td>
                            <td>${motor.created}</td>
                            <td><button class="btn btn-secondary" style="padding: 5px 10px; margin: 0;" onclick="viewMotorRuns(${motor.id})">View Runs</button></td>
                        `;
                    });
                }
                
                updateStatus(`Loaded ${data.motors.length} motor(s)`);
            } catch (error) {
                updateStatus('Error loading motors: ' + error);
                alert('Failed to load motors from database');
            }
        }
        
        async function viewMotorRuns(motorId) {
            try {
                const response = await fetch(`/api/motor/${motorId}/runs`);
                const data = await response.json();
                
                let message = `Motor ID ${motorId} - Simulation Runs:\\n\\n`;
                data.runs.forEach(run => {
                    message += `Run ${run.run_id}: V=${run.voltage}V, J=${run.current_density} A/mm²\\n`;
                });
                
                alert(message);
            } catch (error) {
                alert('Failed to load runs for motor ' + motorId);
            }
        }
        
        async function generatePlot() {
            const motorId = document.getElementById('plot_motor_id').value;
            const voltage = document.getElementById('plot_voltage').value;
            const current = document.getElementById('plot_current').value;
            const plotType = document.getElementById('plot_type').value;
            
            if (!motorId || !voltage || !current) {
                alert('Please fill in all fields');
                return;
            }
            
            updateStatus('Generating plot...');
            
            try {
                const response = await fetch('/api/plot', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        motor_id: parseInt(motorId),
                        voltage: parseFloat(voltage),
                        current_density: parseFloat(current),
                        plot_type: plotType
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('plotContainer').innerHTML = 
                        `<img src="data:image/png;base64,${data.image}" alt="Performance Plot">`;
                    updateStatus('Plot generated successfully');
                } else {
                    alert('Error: ' + data.error);
                    updateStatus('Failed to generate plot');
                }
            } catch (error) {
                alert('Failed to generate plot: ' + error);
                updateStatus('Error generating plot');
            }
        }
        
        function saveConfig() {
            const config = {
                'Maximum speed': parseInt(document.getElementById('max_speed').value),
                'Minimum speed': parseInt(document.getElementById('min_speed').value),
                'Maximum current density': parseFloat(document.getElementById('max_current').value),
                'Battery voltage': document.getElementById('voltages').value.split(',').map(v => parseFloat(v.trim())),
                'Current density': document.getElementById('currents').value.split(',').map(v => parseFloat(v.trim()))
            };
            
            const blob = new Blob([JSON.stringify(config, null, 4)], {type: 'application/json'});
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'config.json';
            a.click();
            
            updateStatus('Configuration saved');
        }
        
        function loadConfig() {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = '.json';
            input.onchange = e => {
                const file = e.target.files[0];
                const reader = new FileReader();
                reader.onload = event => {
                    try {
                        const config = JSON.parse(event.target.result);
                        document.getElementById('max_speed').value = config['Maximum speed'];
                        document.getElementById('min_speed').value = config['Minimum speed'];
                        document.getElementById('max_current').value = config['Maximum current density'];
                        document.getElementById('voltages').value = config['Battery voltage'].join(', ');
                        document.getElementById('currents').value = config['Current density'].join(', ');
                        updateStatus('Configuration loaded');
                    } catch (error) {
                        alert('Failed to load configuration: ' + error);
                    }
                };
                reader.readAsText(file);
            };
            input.click();
        }
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """Main page."""
    return HTML_TEMPLATE


@app.route('/api/motors')
def api_motors():
    """Get list of all motors in database."""
    try:
        motors = database.list_all_motors(config.DB_PATH)
        
        result = []
        for motor in motors:
            motor_json = motor['motor_json']
            
            diameter = motor_json.get('Stator_Lam_Dia', {}).get('value', 'N/A')
            length = motor_json.get('Stator_Lam_Length', {}).get('value', 'N/A')
            turns = motor_json.get('Number_turns_coil', {}).get('value', 'N/A')
            connection_value = motor_json.get('winding_connection', {}).get('value', None)
            
            if connection_value is not None:
                try:
                    conn_int = int(float(connection_value))
                    connection = "Star" if conn_int == 0 else "Delta" if conn_int == 1 else f"Unk({conn_int})"
                except:
                    connection = "N/A"
            else:
                connection = "N/A"
            
            diameter_str = f"{diameter:.2f}" if isinstance(diameter, (int, float)) else str(diameter)
            length_str = f"{length:.2f}" if isinstance(length, (int, float)) else str(length)
            turns_str = f"{turns:.0f}" if isinstance(turns, (int, float)) else str(turns)
            
            result.append({
                'id': motor['id'],
                'diameter': diameter_str,
                'length': length_str,
                'turns': turns_str,
                'connection': connection,
                'created': motor['created_at']
            })
        
        return jsonify({'motors': result})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/motor/<int:motor_id>/runs')
def api_motor_runs(motor_id):
    """Get runs for a specific motor."""
    try:
        runs = database.list_runs_for_motor(motor_id, config.DB_PATH)
        return jsonify({'runs': runs})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/plot', methods=['POST'])
def api_plot():
    """Generate plot."""
    if not HAS_MATPLOTLIB:
        return jsonify({'success': False, 'error': 'Matplotlib not installed'})
    
    try:
        data = request.json
        motor_id = data['motor_id']
        voltage = data['voltage']
        current_density = data['current_density']
        plot_type = data['plot_type']
        
        # Load data from database
        import sqlite3
        con = sqlite3.connect(config.DB_PATH)
        run_data = database.load_run_data(con, motor_id, voltage, current_density)
        con.close()
        
        if run_data is None:
            return jsonify({'success': False, 'error': 'No data found'})
        
        # Generate plot
        fig, axes = _generate_plot(run_data, motor_id, voltage, current_density, plot_type)
        
        # Convert to base64
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        plt.close(fig)
        
        return jsonify({'success': True, 'image': img_base64})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


def _generate_plot(data, motor_id, voltage, current_density, plot_type):
    """Generate matplotlib plot."""
    speed = np.asarray(data.get('Speed')).flatten()
    
    if plot_type == 'all':
        fig, axes = plt.subplots(3, 1, figsize=(10, 9))
        
        torque = np.asarray(data.get('Shaft_Torque')).flatten()
        power = np.asarray(data.get('Shaft_Power')).flatten() / 1000
        efficiency = np.asarray(data.get('Efficiency')).flatten()
        
        axes[0].plot(speed, torque, linewidth=2, color='blue')
        axes[0].set_ylabel('Torque [Nm]', fontsize=11)
        axes[0].grid(True, alpha=0.3)
        axes[0].set_title(f'Motor {motor_id} - V={voltage}V, J={current_density} A/mm²')
        
        axes[1].plot(speed, power, linewidth=2, color='green')
        axes[1].set_ylabel('Power [kW]', fontsize=11)
        axes[1].grid(True, alpha=0.3)
        
        axes[2].plot(speed, efficiency, linewidth=2, color='red')
        axes[2].set_ylabel('Efficiency [%]', fontsize=11)
        axes[2].set_xlabel('Speed [rpm]', fontsize=11)
        axes[2].set_ylim(0, 100)
        axes[2].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
    else:
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        
        if plot_type == 'torque':
            torque = np.asarray(data.get('Shaft_Torque')).flatten()
            ax.plot(speed, torque, linewidth=2, color='blue')
            ax.set_ylabel('Torque [Nm]', fontsize=12)
            ax.set_title(f'Torque-Speed (Motor {motor_id}, V={voltage}V, J={current_density} A/mm²)')
        
        elif plot_type == 'power':
            power = np.asarray(data.get('Shaft_Power')).flatten() / 1000
            ax.plot(speed, power, linewidth=2, color='green')
            ax.set_ylabel('Power [kW]', fontsize=12)
            ax.set_title(f'Power-Speed (Motor {motor_id}, V={voltage}V, J={current_density} A/mm²)')
        
        elif plot_type == 'efficiency':
            efficiency = np.asarray(data.get('Efficiency')).flatten()
            ax.plot(speed, efficiency, linewidth=2, color='red')
            ax.set_ylabel('Efficiency [%]', fontsize=12)
            ax.set_ylim(0, 100)
            ax.set_title(f'Efficiency-Speed (Motor {motor_id}, V={voltage}V, J={current_density} A/mm²)')
        
        ax.set_xlabel('Speed [rpm]', fontsize=12)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
    
    return fig, axes if plot_type == 'all' else ax


def main():
    """Main entry point."""
    print("="*60)
    print("MotorCAD Simulation Framework - Web Interface")
    print("="*60)
    print()
    print("Starting web server...")
    print("Open your browser at: http://localhost:5000")
    print()
    print("Press Ctrl+C to stop the server")
    print("="*60)
    
    # Try to open browser automatically
    threading.Timer(1.5, lambda: webbrowser.open('http://localhost:5000')).start()
    
    # Run server
    app.run(debug=False, host='0.0.0.0', port=5000)


if __name__ == '__main__':
    main()
