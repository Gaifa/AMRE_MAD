"""
MotorCAD Simulation Framework - Graphical User Interface

This GUI application provides a user-friendly interface for:
- Running MotorCAD simulations (batch processing)
- Viewing and analyzing stored results
- Plotting performance curves

Author: MotorCAD Analysis Team
Date: February 2026
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from threading import Thread
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src import config, motor_analyzer, database
import sqlite3

try:
    import matplotlib
    matplotlib.use('TkAgg')
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import numpy as np
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


class MotorCADGUI:
    """Main GUI application for MotorCAD simulation framework."""
    
    def __init__(self, root):
        """Initialize the GUI application."""
        self.root = root
        self.root.title("MotorCAD Simulation Framework")
        self.root.geometry("1200x800")
        
        # Variables
        self.selected_mot_files = []
        self.current_config = config.DEFAULT_MODEL_DICT.copy()
        self.db_path = config.DB_PATH
        
        # Create main notebook (tabs)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create tabs
        self.create_simulation_tab()
        self.create_results_tab()
        self.create_plotting_tab()
        self.create_about_tab()
        
        # Status bar
        self.status_bar = ttk.Label(root, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    # =========================================================================
    # SIMULATION TAB
    # =========================================================================
    
    def create_simulation_tab(self):
        """Create the simulation configuration and execution tab."""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Run Simulations")
        
        # Left panel: Motor selection
        left_frame = ttk.LabelFrame(tab, text="Motor Selection", padding=10)
        left_frame.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
        
        ttk.Button(left_frame, text="Select Single Motor File", 
                  command=self.select_single_motor).pack(fill='x', pady=2)
        ttk.Button(left_frame, text="Select Directory of Motors", 
                  command=self.select_motor_directory).pack(fill='x', pady=2)
        ttk.Button(left_frame, text="Load Motor List from File", 
                  command=self.load_motor_list).pack(fill='x', pady=2)
        ttk.Button(left_frame, text="Clear Selection", 
                  command=self.clear_motor_selection).pack(fill='x', pady=2)
        
        ttk.Separator(left_frame, orient='horizontal').pack(fill='x', pady=10)
        
        ttk.Label(left_frame, text="Selected Motors:").pack(anchor='w')
        self.motor_list_text = scrolledtext.ScrolledText(left_frame, height=15, width=40)
        self.motor_list_text.pack(fill='both', expand=True, pady=5)
        
        self.motor_count_label = ttk.Label(left_frame, text="0 motors selected")
        self.motor_count_label.pack(anchor='w')
        
        # Right panel: Configuration
        right_frame = ttk.LabelFrame(tab, text="Simulation Configuration", padding=10)
        right_frame.grid(row=0, column=1, sticky='nsew', padx=5, pady=5)
        
        # Configuration fields
        config_grid = ttk.Frame(right_frame)
        config_grid.pack(fill='x', pady=5)
        
        ttk.Label(config_grid, text="Max Speed (rpm):").grid(row=0, column=0, sticky='w', pady=2)
        self.max_speed_var = tk.StringVar(value=str(self.current_config['Maximum speed']))
        ttk.Entry(config_grid, textvariable=self.max_speed_var, width=15).grid(row=0, column=1, padx=5)
        
        ttk.Label(config_grid, text="Min Speed (rpm):").grid(row=1, column=0, sticky='w', pady=2)
        self.min_speed_var = tk.StringVar(value=str(self.current_config['Minimum speed']))
        ttk.Entry(config_grid, textvariable=self.min_speed_var, width=15).grid(row=1, column=1, padx=5)
        
        ttk.Label(config_grid, text="Max Current Density (A/mm²):").grid(row=2, column=0, sticky='w', pady=2)
        self.max_current_var = tk.StringVar(value=str(self.current_config['Maximum current density']))
        ttk.Entry(config_grid, textvariable=self.max_current_var, width=15).grid(row=2, column=1, padx=5)
        
        ttk.Label(config_grid, text="Battery Voltages (V):").grid(row=3, column=0, sticky='w', pady=2)
        self.voltages_var = tk.StringVar(value=str(self.current_config['Battery voltage'])[1:-1])
        ttk.Entry(config_grid, textvariable=self.voltages_var, width=30).grid(row=3, column=1, padx=5)
        ttk.Label(config_grid, text="(comma-separated)").grid(row=3, column=2, sticky='w')
        
        ttk.Label(config_grid, text="Current Densities (A/mm²):").grid(row=4, column=0, sticky='w', pady=2)
        self.currents_var = tk.StringVar(value=str(self.current_config['Current density'])[1:-1])
        ttk.Entry(config_grid, textvariable=self.currents_var, width=30).grid(row=4, column=1, padx=5)
        ttk.Label(config_grid, text="(comma-separated)").grid(row=4, column=2, sticky='w')
        
        # Config file buttons
        config_buttons = ttk.Frame(right_frame)
        config_buttons.pack(fill='x', pady=10)
        ttk.Button(config_buttons, text="Load Config from File", 
                  command=self.load_config_file).pack(side='left', padx=2)
        ttk.Button(config_buttons, text="Save Config to File", 
                  command=self.save_config_file).pack(side='left', padx=2)
        ttk.Button(config_buttons, text="Reset to Default", 
                  command=self.reset_config).pack(side='left', padx=2)
        
        ttk.Separator(right_frame, orient='horizontal').pack(fill='x', pady=10)
        
        # Database path
        db_frame = ttk.Frame(right_frame)
        db_frame.pack(fill='x', pady=5)
        ttk.Label(db_frame, text="Database:").pack(side='left')
        self.db_path_var = tk.StringVar(value=self.db_path)
        ttk.Entry(db_frame, textvariable=self.db_path_var, width=40).pack(side='left', padx=5)
        ttk.Button(db_frame, text="Browse", command=self.select_database).pack(side='left')
        
        ttk.Separator(right_frame, orient='horizontal').pack(fill='x', pady=10)
        
        # Output log
        ttk.Label(right_frame, text="Simulation Log:").pack(anchor='w')
        self.sim_log = scrolledtext.ScrolledText(right_frame, height=15)
        self.sim_log.pack(fill='both', expand=True, pady=5)
        
        # Run button
        self.run_button = ttk.Button(right_frame, text="▶ RUN SIMULATIONS", 
                                     command=self.run_simulations, style='Accent.TButton')
        self.run_button.pack(fill='x', pady=10)
        
        # Configure grid weights
        tab.columnconfigure(0, weight=1)
        tab.columnconfigure(1, weight=2)
        tab.rowconfigure(0, weight=1)
    
    def select_single_motor(self):
        """Open file dialog to select a single .mot file."""
        filename = filedialog.askopenfilename(
            title="Select Motor File",
            filetypes=[("MotorCAD Files", "*.mot"), ("All Files", "*.*")],
            initialdir=config.MOTORS_DIR
        )
        if filename:
            self.selected_mot_files = [filename]
            self.update_motor_list_display()
    
    def select_motor_directory(self):
        """Open directory dialog to select a folder containing .mot files."""
        directory = filedialog.askdirectory(
            title="Select Directory Containing Motor Files",
            initialdir=config.MOTORS_DIR
        )
        if directory:
            # Ask if recursive search
            recursive = messagebox.askyesno("Recursive Search", 
                                           "Search subdirectories recursively?")
            mot_files = motor_analyzer.find_mot_files(directory, recursive=recursive)
            if mot_files:
                self.selected_mot_files = mot_files
                self.update_motor_list_display()
                messagebox.showinfo("Success", f"Found {len(mot_files)} motor file(s)")
            else:
                messagebox.showwarning("No Files", "No .mot files found in directory")
    
    def load_motor_list(self):
        """Load motor file list from text file."""
        filename = filedialog.askopenfilename(
            title="Select Motor List File",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if filename:
            try:
                motors = []
                with open(filename, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            motors.append(line)
                self.selected_mot_files = motors
                self.update_motor_list_display()
                messagebox.showinfo("Success", f"Loaded {len(motors)} motor(s) from list")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load motor list: {e}")
    
    def clear_motor_selection(self):
        """Clear the current motor selection."""
        self.selected_mot_files = []
        self.update_motor_list_display()
    
    def update_motor_list_display(self):
        """Update the motor list text display."""
        self.motor_list_text.delete('1.0', tk.END)
        for mot_file in self.selected_mot_files:
            self.motor_list_text.insert(tk.END, os.path.basename(mot_file) + "\n")
        self.motor_count_label.config(text=f"{len(self.selected_mot_files)} motor(s) selected")
    
    def load_config_file(self):
        """Load configuration from JSON file."""
        filename = filedialog.askopenfilename(
            title="Load Configuration",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    self.current_config = json.load(f)
                self.update_config_display()
                messagebox.showinfo("Success", "Configuration loaded successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load configuration: {e}")
    
    def save_config_file(self):
        """Save current configuration to JSON file."""
        filename = filedialog.asksaveasfilename(
            title="Save Configuration",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if filename:
            try:
                self.update_config_from_fields()
                with open(filename, 'w') as f:
                    json.dump(self.current_config, f, indent=4)
                messagebox.showinfo("Success", "Configuration saved successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save configuration: {e}")
    
    def reset_config(self):
        """Reset configuration to default values."""
        self.current_config = config.DEFAULT_MODEL_DICT.copy()
        self.update_config_display()
    
    def update_config_display(self):
        """Update configuration fields from current_config."""
        self.max_speed_var.set(str(self.current_config['Maximum speed']))
        self.min_speed_var.set(str(self.current_config['Minimum speed']))
        self.max_current_var.set(str(self.current_config['Maximum current density']))
        self.voltages_var.set(str(self.current_config['Battery voltage'])[1:-1])
        self.currents_var.set(str(self.current_config['Current density'])[1:-1])
    
    def update_config_from_fields(self):
        """Update current_config from field values."""
        try:
            self.current_config['Maximum speed'] = int(self.max_speed_var.get())
            self.current_config['Minimum speed'] = int(self.min_speed_var.get())
            self.current_config['Maximum current density'] = float(self.max_current_var.get())
            
            # Parse comma-separated lists
            voltages_str = self.voltages_var.get()
            self.current_config['Battery voltage'] = [float(v.strip()) for v in voltages_str.split(',')]
            
            currents_str = self.currents_var.get()
            self.current_config['Current density'] = [float(c.strip()) for c in currents_str.split(',')]
            
            return True
        except Exception as e:
            messagebox.showerror("Configuration Error", f"Invalid configuration values: {e}")
            return False
    
    def select_database(self):
        """Select database file path."""
        filename = filedialog.asksaveasfilename(
            title="Select Database File",
            defaultextension=".db",
            filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")],
            initialfile=os.path.basename(config.DB_PATH)
        )
        if filename:
            self.db_path = filename
            self.db_path_var.set(filename)
    
    def run_simulations(self):
        """Execute simulations in background thread."""
        if not self.selected_mot_files:
            messagebox.showwarning("No Motors", "Please select motor files first")
            return
        
        if not self.update_config_from_fields():
            return
        
        # Confirm
        n_motors = len(self.selected_mot_files)
        n_voltages = len(self.current_config['Battery voltage'])
        n_currents = len(self.current_config['Current density'])
        max_sims = n_motors * n_voltages * n_currents
        
        msg = f"Run simulations for {n_motors} motor(s)?\n\n"
        msg += f"Maximum possible simulations: {max_sims}\n"
        msg += "(Actual number may be lower due to caching)"
        
        if not messagebox.askyesno("Confirm Simulation", msg):
            return
        
        # Disable button and run in thread
        self.run_button.config(state='disabled')
        self.sim_log.delete('1.0', tk.END)
        self.log_message("Starting simulations...\n")
        
        # Run in separate thread to keep GUI responsive
        thread = Thread(target=self._run_simulations_thread)
        thread.daemon = True
        thread.start()
    
    def _run_simulations_thread(self):
        """Background thread for running simulations."""
        try:
            # Redirect stdout to log
            import io
            from contextlib import redirect_stdout
            
            log_buffer = io.StringIO()
            
            with redirect_stdout(log_buffer):
                batch_results = motor_analyzer.analyze_motor_batch(
                    mot_file_paths=self.selected_mot_files,
                    model_dict=self.current_config,
                    db_path=self.db_path
                )
            
            # Display results
            output = log_buffer.getvalue()
            self.root.after(0, lambda: self.log_message(output))
            
            # Summary
            successful = [r for r in batch_results if r['success']]
            failed = [r for r in batch_results if not r['success']]
            
            summary = f"\n{'='*60}\n"
            summary += "SIMULATION COMPLETE\n"
            summary += f"{'='*60}\n"
            summary += f"Total motors:     {len(batch_results)}\n"
            summary += f"Successful:       {len(successful)}\n"
            summary += f"Failed:           {len(failed)}\n"
            
            if successful:
                total_runs = sum(len(r.get('results', [])) for r in successful)
                summary += f"Simulations saved: {total_runs}\n"
            
            self.root.after(0, lambda: self.log_message(summary))
            self.root.after(0, lambda: messagebox.showinfo("Complete", "Simulations finished!"))
            
        except Exception as e:
            error_msg = f"\nERROR: {str(e)}\n"
            self.root.after(0, lambda: self.log_message(error_msg))
            self.root.after(0, lambda: messagebox.showerror("Error", f"Simulation failed: {e}"))
        
        finally:
            self.root.after(0, lambda: self.run_button.config(state='normal'))
    
    def log_message(self, message):
        """Append message to simulation log."""
        self.sim_log.insert(tk.END, message)
        self.sim_log.see(tk.END)
    
    # =========================================================================
    # RESULTS TAB
    # =========================================================================
    
    def create_results_tab(self):
        """Create the results viewing tab."""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="View Results")
        
        # Top panel: Motor list
        top_frame = ttk.LabelFrame(tab, text="Motors in Database", padding=10)
        top_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(top_frame)
        button_frame.pack(fill='x', pady=5)
        ttk.Button(button_frame, text="Refresh List", 
                  command=self.refresh_motor_list).pack(side='left', padx=2)
        ttk.Button(button_frame, text="View Motor Details", 
                  command=self.view_motor_details).pack(side='left', padx=2)
        
        # Treeview for motors
        columns = ('ID', 'Diameter', 'Length', 'Turns', 'Connection', 'Created')
        self.motor_tree = ttk.Treeview(top_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.motor_tree.heading(col, text=col)
            if col == 'ID':
                self.motor_tree.column(col, width=50)
            elif col in ['Diameter', 'Length', 'Turns']:
                self.motor_tree.column(col, width=100)
            elif col == 'Connection':
                self.motor_tree.column(col, width=100)
            else:
                self.motor_tree.column(col, width=200)
        
        scrollbar = ttk.Scrollbar(top_frame, orient='vertical', command=self.motor_tree.yview)
        self.motor_tree.configure(yscrollcommand=scrollbar.set)
        
        self.motor_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Automatically load motor list
        self.root.after(100, self.refresh_motor_list)
    
    def refresh_motor_list(self):
        """Refresh the motor list from database."""
        try:
            # Clear existing items
            for item in self.motor_tree.get_children():
                self.motor_tree.delete(item)
            
            # Check if database exists
            if not os.path.exists(self.db_path):
                self.status_bar.config(text="Database not found")
                return
            
            # Load motors
            motors = database.list_all_motors(self.db_path)
            
            for motor in motors:
                motor_json = motor['motor_json']
                
                # Extract parameters
                diameter = motor_json.get('Stator_Lam_Dia', {}).get('value', 'N/A')
                length = motor_json.get('Stator_Lam_Length', {}).get('value', 'N/A')
                turns = motor_json.get('Number_turns_coil', {}).get('value', 'N/A')
                connection_value = motor_json.get('winding_connection', {}).get('value', None)
                
                # Format connection
                if connection_value is not None:
                    try:
                        conn_int = int(float(connection_value))
                        connection = "Star" if conn_int == 0 else "Delta" if conn_int == 1 else f"Unk({conn_int})"
                    except:
                        connection = "N/A"
                else:
                    connection = "N/A"
                
                # Format values
                diameter_str = f"{diameter:.2f}" if isinstance(diameter, (int, float)) else str(diameter)
                length_str = f"{length:.2f}" if isinstance(length, (int, float)) else str(length)
                turns_str = f"{turns:.0f}" if isinstance(turns, (int, float)) else str(turns)
                
                self.motor_tree.insert('', 'end', values=(
                    motor['id'],
                    diameter_str,
                    length_str,
                    turns_str,
                    connection,
                    motor['created_at']
                ))
            
            self.status_bar.config(text=f"Loaded {len(motors)} motor(s) from database")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load motors: {e}")
            self.status_bar.config(text="Error loading database")
    
    def view_motor_details(self):
        """View detailed run information for selected motor."""
        selection = self.motor_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a motor first")
            return
        
        item = self.motor_tree.item(selection[0])
        motor_id = int(item['values'][0])
        
        # Create details window
        detail_window = tk.Toplevel(self.root)
        detail_window.title(f"Motor ID {motor_id} - Run Details")
        detail_window.geometry("800x600")
        
        # Runs list
        ttk.Label(detail_window, text=f"Simulation Runs for Motor ID {motor_id}", 
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        columns = ('Run ID', 'Voltage (V)', 'Current Density (A/mm²)', 'Created')
        runs_tree = ttk.Treeview(detail_window, columns=columns, show='headings')
        
        for col in columns:
            runs_tree.heading(col, text=col)
            runs_tree.column(col, width=150)
        
        scrollbar = ttk.Scrollbar(detail_window, orient='vertical', command=runs_tree.yview)
        runs_tree.configure(yscrollcommand=scrollbar.set)
        
        runs_tree.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        scrollbar.pack(side='right', fill='y', pady=10)
        
        # Load runs
        try:
            runs = database.list_runs_for_motor(motor_id, self.db_path)
            for run in runs:
                runs_tree.insert('', 'end', values=(
                    run['run_id'],
                    f"{run['voltage']:.1f}",
                    f"{run['current_density']:.2f}",
                    run['created_at']
                ))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load runs: {e}")
    
    # =========================================================================
    # PLOTTING TAB
    # =========================================================================
    
    def create_plotting_tab(self):
        """Create the plotting tab."""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Plot Results")
        
        if not HAS_MATPLOTLIB:
            ttk.Label(tab, text="Matplotlib not installed. Plotting features disabled.", 
                     font=('Arial', 14)).pack(pady=50)
            ttk.Label(tab, text="Install with: pip install matplotlib").pack()
            return
        
        # Controls frame
        control_frame = ttk.LabelFrame(tab, text="Plot Controls", padding=10)
        control_frame.pack(fill='x', padx=5, pady=5)
        
        # Input fields
        fields_frame = ttk.Frame(control_frame)
        fields_frame.pack(fill='x', pady=5)
        
        ttk.Label(fields_frame, text="Motor ID:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.plot_motor_id = tk.StringVar()
        ttk.Entry(fields_frame, textvariable=self.plot_motor_id, width=10).grid(row=0, column=1, padx=5)
        
        ttk.Label(fields_frame, text="Voltage:").grid(row=0, column=2, sticky='w', padx=5, pady=2)
        self.plot_voltage = tk.StringVar()
        ttk.Entry(fields_frame, textvariable=self.plot_voltage, width=10).grid(row=0, column=3, padx=5)
        
        ttk.Label(fields_frame, text="Current Density:").grid(row=0, column=4, sticky='w', padx=5, pady=2)
        self.plot_current = tk.StringVar()
        ttk.Entry(fields_frame, textvariable=self.plot_current, width=10).grid(row=0, column=5, padx=5)
        
        # Plot type selection
        ttk.Label(fields_frame, text="Plot Type:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        self.plot_type = tk.StringVar(value="All Curves")
        plot_types = ["Torque-Speed", "Power-Speed", "Efficiency-Speed", "All Curves"]
        ttk.Combobox(fields_frame, textvariable=self.plot_type, values=plot_types, 
                    width=15, state='readonly').grid(row=1, column=1, columnspan=2, padx=5, sticky='w')
        
        ttk.Button(fields_frame, text="Generate Plot", 
                  command=self.generate_plot).grid(row=1, column=3, columnspan=2, padx=5)
        
        # Plot area
        plot_frame = ttk.Frame(tab)
        plot_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.figure = Figure(figsize=(10, 6))
        self.canvas = FigureCanvasTkAgg(self.figure, plot_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def generate_plot(self):
        """Generate the selected plot."""
        if not HAS_MATPLOTLIB:
            return
        
        try:
            motor_id = int(self.plot_motor_id.get())
            voltage = float(self.plot_voltage.get())
            current_density = float(self.plot_current.get())
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid Motor ID, Voltage, and Current Density")
            return
        
        try:
            # Load data
            con = sqlite3.connect(self.db_path)
            data = database.load_run_data(con, motor_id, voltage, current_density)
            con.close()
            
            if data is None:
                messagebox.showerror("No Data", "No data found for the specified parameters")
                return
            
            # Clear previous plot
            self.figure.clear()
            
            plot_type = self.plot_type.get()
            
            if plot_type == "All Curves":
                self._plot_all_curves(data, motor_id, voltage, current_density)
            elif plot_type == "Torque-Speed":
                self._plot_torque_speed(data, motor_id, voltage, current_density)
            elif plot_type == "Power-Speed":
                self._plot_power_speed(data, motor_id, voltage, current_density)
            elif plot_type == "Efficiency-Speed":
                self._plot_efficiency_speed(data, motor_id, voltage, current_density)
            
            self.canvas.draw()
            
        except Exception as e:
            messagebox.showerror("Plot Error", f"Failed to generate plot: {e}")
    
    def _plot_torque_speed(self, data, motor_id, voltage, current_density):
        """Plot torque-speed curve."""
        speed = np.asarray(data.get('Speed')).flatten()
        torque = np.asarray(data.get('Shaft_Torque')).flatten()
        
        ax = self.figure.add_subplot(111)
        ax.plot(speed, torque, linewidth=2, color='blue')
        ax.set_xlabel('Speed [rpm]', fontsize=12)
        ax.set_ylabel('Torque [Nm]', fontsize=12)
        ax.set_title(f'Torque-Speed Curve (Motor {motor_id}, V={voltage}V, J={current_density} A/mm²)')
        ax.grid(True, alpha=0.3)
    
    def _plot_power_speed(self, data, motor_id, voltage, current_density):
        """Plot power-speed curve."""
        speed = np.asarray(data.get('Speed')).flatten()
        power = np.asarray(data.get('Shaft_Power')).flatten() / 1000  # kW
        
        ax = self.figure.add_subplot(111)
        ax.plot(speed, power, linewidth=2, color='green')
        ax.set_xlabel('Speed [rpm]', fontsize=12)
        ax.set_ylabel('Power [kW]', fontsize=12)
        ax.set_title(f'Power-Speed Curve (Motor {motor_id}, V={voltage}V, J={current_density} A/mm²)')
        ax.grid(True, alpha=0.3)
    
    def _plot_efficiency_speed(self, data, motor_id, voltage, current_density):
        """Plot efficiency-speed curve."""
        speed = np.asarray(data.get('Speed')).flatten()
        efficiency = np.asarray(data.get('Efficiency')).flatten()
        
        ax = self.figure.add_subplot(111)
        ax.plot(speed, efficiency, linewidth=2, color='red')
        ax.set_xlabel('Speed [rpm]', fontsize=12)
        ax.set_ylabel('Efficiency [%]', fontsize=12)
        ax.set_title(f'Efficiency-Speed Curve (Motor {motor_id}, V={voltage}V, J={current_density} A/mm²)')
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 100)
    
    def _plot_all_curves(self, data, motor_id, voltage, current_density):
        """Plot all curves on separate subplots."""
        speed = np.asarray(data.get('Speed')).flatten()
        torque = np.asarray(data.get('Shaft_Torque')).flatten()
        power = np.asarray(data.get('Shaft_Power')).flatten() / 1000  # kW
        efficiency = np.asarray(data.get('Efficiency')).flatten()
        
        # Create subplots
        ax1 = self.figure.add_subplot(311)
        ax1.plot(speed, torque, linewidth=2, color='blue')
        ax1.set_ylabel('Torque [Nm]', fontsize=10)
        ax1.grid(True, alpha=0.3)
        ax1.set_title(f'Performance Curves (Motor {motor_id}, V={voltage}V, J={current_density} A/mm²)')
        
        ax2 = self.figure.add_subplot(312)
        ax2.plot(speed, power, linewidth=2, color='green')
        ax2.set_ylabel('Power [kW]', fontsize=10)
        ax2.grid(True, alpha=0.3)
        
        ax3 = self.figure.add_subplot(313)
        ax3.plot(speed, efficiency, linewidth=2, color='red')
        ax3.set_ylabel('Efficiency [%]', fontsize=10)
        ax3.set_xlabel('Speed [rpm]', fontsize=10)
        ax3.set_ylim(0, 100)
        ax3.grid(True, alpha=0.3)
        
        self.figure.tight_layout()
    
    # =========================================================================
    # ABOUT TAB
    # =========================================================================
    
    def create_about_tab(self):
        """Create the about/help tab."""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="About")
        
        about_text = scrolledtext.ScrolledText(tab, wrap=tk.WORD, font=('Arial', 10))
        about_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        about_content = """
MotorCAD Simulation Framework - GUI Application
==============================================

Version: 1.0
Date: February 2026
Author: MotorCAD Analysis Team

FEATURES
--------
• Batch motor simulation with intelligent caching
• Database storage of simulation results
• Performance curve visualization
• Multi-voltage and multi-current density sweep
• User-friendly graphical interface

USAGE
-----
1. Run Simulations Tab:
   - Select motor files (single, directory, or list)
   - Configure simulation parameters
   - Execute batch simulations
   - Monitor progress in real-time

2. View Results Tab:
   - Browse all motors in database
   - View motor parameters (diameter, length, turns, connection)
   - Inspect simulation runs for each motor

3. Plot Results Tab:
   - Generate performance curves
   - Compare different operating points
   - Export plots as images

REQUIREMENTS
------------
• Windows OS (for MotorCAD COM automation)
• MotorCAD installed and licensed
• Python 3.8+
• Required packages: numpy, scipy, pywin32
• Optional: matplotlib (for plotting)

DATABASE
--------
All simulation results are stored in SQLite database:
• Location: mcad_results.db (configurable)
• Motor identification via SHA256 hash
• Intelligent caching prevents redundant simulations

SUPPORT
-------
For questions or issues, contact the MotorCAD Analysis Team.

LICENSE
-------
Internal use - MotorCAD Analysis Team
        """
        
        about_text.insert('1.0', about_content)
        about_text.config(state='disabled')


def main():
    """Main entry point for GUI application."""
    root = tk.Tk()
    app = MotorCADGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
