"""
MotorCAD Performance Report Generator

Generates PDF performance reports for motors stored in the database.
Creates reports for different motor types (FL, MC, MV) with duty cycle analysis.

Author: MotorCAD Analysis Team
Date: February 2026
"""

import os
import sys
import json
import sqlite3
from datetime import datetime
import numpy as np

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src import database, config

# PDF generation
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

# Plotting
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

# Font registration (Aptos)
APTOS_FONT_PATH = os.path.join(os.path.dirname(__file__), "Aptos-Regular.ttf")
APTOS_BOLD_PATH = os.path.join(os.path.dirname(__file__), "Aptos-Bold.ttf")
if os.path.exists(APTOS_FONT_PATH):
    pdfmetrics.registerFont(TTFont("Aptos", APTOS_FONT_PATH))
    FONT_NAME = "Aptos"
    if os.path.exists(APTOS_BOLD_PATH):
        pdfmetrics.registerFont(TTFont("Aptos-Bold", APTOS_BOLD_PATH))
        FONT_NAME_BOLD = "Aptos-Bold"
    else:
        FONT_NAME_BOLD = "Aptos"   # fallback: same font
else:
    FONT_NAME = "Helvetica"
    FONT_NAME_BOLD = "Helvetica-Bold"

# Configuration file
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "config", "motor_types_config.json")

# DMC inverter catalogue
DMC_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "config", "dmc_types_dictionary.json")

# Color palette for plots
COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']


def load_motor_types_config(config_path=CONFIG_FILE):
    """Load motor types and duty cycle configuration from JSON file."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_dmc_config(dmc_path=DMC_CONFIG_FILE):
    """Load the DMC inverter catalogue from JSON file."""
    if not dmc_path or not os.path.exists(dmc_path):
        return None
    try:
        with open(dmc_path, 'r', encoding='utf-8-sig') as f:
            content = f.read().strip()
            if not content:
                return None
            return json.loads(content)
    except (json.JSONDecodeError, OSError):
        return None


def find_suggested_inverter(battery_voltage, current_s2_5min, current_s2_60min, dmc_config):
    """
    Find the smallest suitable DMC inverter for the given operating point.

    Selection criteria (full match):
      - model.maxVoltageV          >= battery_voltage
      - size.maxCurrentArms        >= current_s2_5min   (peak / S2-5 min)
      - size.continuousCurrentArms >= current_s2_60min  (continuous / S2-60 min)

    If no size fully matches the current requirements, the function falls back to
    size 4 at the correct voltage and reports which duties it can actually cover.

    Returns:
        (label, note)  where label is e.g. "DMC SSigma2 96V  size 2" and note is
                       None for a full match or a coverage string for a fallback.
        (None, None)   if no inverter at the required voltage is found at all.
    """
    if dmc_config is None:
        return None, None

    full_candidates  = []   # fully satisfy both current requirements
    fallback_size4   = []   # size-4 entries at correct voltage (partial coverage)

    for family in dmc_config.get('inverterFamilies', []):
        for model in family.get('models', []):
            if model['maxVoltageV'] < battery_voltage:
                continue                              # voltage too low — skip entirely
            for sz in model.get('sizes', []):
                peak_ok = (current_s2_5min  is None) or (sz['maxCurrentArms']       >= current_s2_5min)
                cont_ok = (current_s2_60min is None) or (sz['continuousCurrentArms'] >= current_s2_60min)
                if peak_ok and cont_ok:
                    full_candidates.append((
                        model['maxVoltageV'], sz['maxCurrentArms'],
                        model['modelName'], sz['size'],
                    ))
                elif sz['size'] == 4:                 # collect as fallback
                    fallback_size4.append((
                        model['maxVoltageV'], sz['maxCurrentArms'],
                        model['modelName'], sz['size'],
                        peak_ok, cont_ok,
                    ))

    # --- full match found ---
    if full_candidates:
        full_candidates.sort(key=lambda c: (c[0], c[1]))
        _, _, model_name, size = full_candidates[0]
        return f"DMC {model_name}  size {size}", None

    # --- fallback: recommend size 4 with coverage note ---
    if not fallback_size4:
        return None, None

    fallback_size4.sort(key=lambda c: (c[0], c[1]))
    _, _, model_name, size, peak_ok, cont_ok = fallback_size4[0]
    label = f"DMC {model_name}  size {size}"

    if cont_ok and not peak_ok:
        note = "covers up to S2-60min"
    elif peak_ok and not cont_ok:
        note = "covers up to S2-20min"
    else:
        note = "motor current exceeds inverter limits"

    return label, note


def get_motor_info_from_json(motor_json):
    """Extract motor parameters from motor_json dict."""
    info = {
        'diameter': motor_json.get('Stator_Lam_Dia', {}).get('value', 0),
        'length': motor_json.get('Stator_Lam_Length', {}).get('value', 0),
        'turns': motor_json.get('Number_turns_coil', {}).get('value', 0),
        'connection_value': motor_json.get('winding_connection', {}).get('value', None),
        'poles': motor_json.get('Pole_number', {}).get('value', 0),
        'slots': motor_json.get('Slot_number', {}).get('value', 0),
    }
    
    # Format connection type
    if info['connection_value'] is not None:
        try:
            conn_int = int(float(info['connection_value']))
            info['connection'] = "Star" if conn_int == 0 else "Delta" if conn_int == 1 else "Unknown"
        except:
            info['connection'] = "Unknown"
    else:
        info['connection'] = "Unknown"
    
    return info


def generate_performance_plot(run_data_list, duty_labels, output_path):
    """
    Generate combined torque and power plot for multiple duty cycles.
    
    Args:
        run_data_list: List of run data dictionaries (one per duty)
        duty_labels: List of duty labels (e.g., ['S2-5min', 'S2-20min', 'S2-60min'])
        output_path: Path to save the plot image
    """
    fig, ax1 = plt.subplots(figsize=(11, 6))
    ax2 = ax1.twinx()

    legend_handles = []

    # Plot for each duty cycle
    for idx, (run_data, duty_label) in enumerate(zip(run_data_list, duty_labels)):
        if run_data is None:
            continue

        color = COLORS[idx % len(COLORS)]

        # Extract data
        speed = np.asarray(run_data.get('Speed', [])).flatten()
        torque = np.asarray(run_data.get('Shaft_Torque', [])).flatten()
        power = np.asarray(run_data.get('Shaft_Power', [])).flatten() 

        if len(speed) == 0:
            continue

        # Torque — solid line on left axis
        ax1.plot(speed, torque, color=color, linewidth=2, linestyle='-')

        # Power — dashed line on right axis
        ax2.plot(speed, power, color=color, linewidth=2, linestyle='--')

        # One legend entry per duty (coloured patch)
        legend_handles.append(
            plt.Line2D([0], [0], color=color, linewidth=2, label=duty_label)
        )

    # Left axis — torque
    ax1.set_xlabel('Speed [rpm]', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Torque [Nm]', fontsize=12, fontweight='bold', color='black')
    ax1.tick_params(axis='y', labelcolor='black')
    ax1.grid(True, alpha=0.3, linestyle='--')

    # Right axis — power
    ax2.set_ylabel('Power [kW]', fontsize=12, fontweight='bold', color='dimgray')
    ax2.tick_params(axis='y', labelcolor='black')

    # Style hint lines (no data, just for the legend)
    solid_line = plt.Line2D([0], [0], color='black', linewidth=2, linestyle='-',  label='Torque [Nm]')
    dashed_line = plt.Line2D([0], [0], color='dimgray', linewidth=2, linestyle='--', label='Power [kW]')

    # Duty legend — above the axes at figure level, never overlaps curves
    fig.legend(
        handles=legend_handles,
        loc='upper center',
        bbox_to_anchor=(0.5, 1.0),
        ncol=len(legend_handles),
        fontsize=10,
        framealpha=0.9,
        title='Duty cycle',
        title_fontsize=10,
        borderaxespad=0.3
    )

    # Small style legend inside the axes (lower right)
    ax1.legend(
        handles=[solid_line, dashed_line],
        loc='upper right',
        fontsize=9,
        framealpha=0.7
    )

    # Leave room at the top for the figure-level legend
    plt.tight_layout(rect=[0, 0, 1, 0.87])
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close(fig)

    return output_path


def get_run_performance_data(con, motor_id, voltage, current_density):
    """
    Get performance data for a specific run and extract key metrics.
    
    Returns dict with torque, power, speed, efficiency, current, voltage at max power point.
    """
    run_data = database.load_run_data(con, motor_id, voltage, current_density)
    
    if run_data is None:
        return None
    
    # Extract arrays
    speed = np.asarray(run_data.get('Speed', [])).flatten()
    torque = np.asarray(run_data.get('Shaft_Torque', [])).flatten()
    power = np.asarray(run_data.get('Shaft_Power', [])).flatten()
    efficiency = np.asarray(run_data.get('Efficiency', [])).flatten()
    current = np.asarray(run_data.get('Stator_Current_Line_RMS', [])).flatten()
    voltage_phase = np.asarray(run_data.get('Voltage_Phase_RMS', [])).flatten()
    
    if len(power) == 0:
        return None
    
    # Find max power point
    max_power_idx = np.argmax(power)
    
    return {
        'torque': torque[max_power_idx] if len(torque) > max_power_idx else 0,
        'power': power[max_power_idx] if len(power) > max_power_idx else 0,  # kW
        'speed': speed[max_power_idx] if len(speed) > max_power_idx else 0,
        'efficiency': efficiency[max_power_idx] if len(efficiency) > max_power_idx else 0,
        'current': current[max_power_idx] if len(current) > max_power_idx else 0,
        'voltage': voltage_phase[max_power_idx] if len(voltage_phase) > max_power_idx else 0,
        'current_density': current_density
    }


def generate_pdf_report(motor_id, motor_info, voltage, motor_type, type_config, 
                        performance_data, plot_path, output_path, pdf_settings):
    """
    Generate a PDF performance report for a motor.
    
    Args:
        motor_id: Database motor ID
        motor_info: Dict with motor parameters
        voltage: Battery voltage
        motor_type: Motor type (FL, MC, MV)
        type_config: Configuration for this motor type
        performance_data: Dict with performance data for each duty
        plot_path: Path to the performance plot image
        output_path: Output PDF file path
        pdf_settings: PDF generation settings
    """
    # Create document — tighter margins to fit everything on one page
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        topMargin=8*mm, bottomMargin=18*mm,
        leftMargin=10*mm, rightMargin=10*mm
    )
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    header_box_color = colors.HexColor("#203764")
    #cl= colors.rgb2cmyk(r=32, g=55, b=100)

    style_title = ParagraphStyle(name='title', parent=styles['Title'], 
                                 alignment=1, fontSize=18, spaceAfter=10, 
                                 fontName=FONT_NAME, textColor=colors.white)
    style_center = ParagraphStyle(name='center', parent=styles['Normal'], 
                                  alignment=1, fontSize=14, spaceAfter=10, 
                                  fontName=FONT_NAME)
    style_footer = ParagraphStyle(name='footer', parent=styles['Normal'], 
                                  alignment=1, fontSize=10, textColor=colors.white, 
                                  fontName=FONT_NAME)
    style_table_header = ParagraphStyle(name='table_header', parent=styles['Normal'],
                                        fontSize=11, textColor=colors.white,
                                        fontName=FONT_NAME_BOLD, wordWrap=None,
                                        alignment=1)
    style_table_cell = ParagraphStyle(name='table_cell', parent=styles['Normal'],
                                      fontSize=9, fontName=FONT_NAME)
    style_table_cell_white = ParagraphStyle(name='table_cell_white', parent=styles['Normal'],
                                            fontSize=9, fontName=FONT_NAME_BOLD,
                                            textColor=colors.white, wordWrap=None,
                                            alignment=1)
    
    # Generate model name
    model_name = f"IM-D{int(motor_info['diameter'])}-H{int(motor_info['length'])}-{int(motor_info['turns'])}T-{motor_info['connection']}"
    
    # Title
    title = f"PERFORMANCE REPORT"
    
    # Header table
    # Logo: look first in vario/, then next to the script
    _vario = os.path.join(os.path.dirname(__file__), '..', 'vario')
    logo_filename = pdf_settings.get('logo_path', 'AMRE_Logo.png')
    logo_path = os.path.join(_vario, logo_filename)
    if not os.path.exists(logo_path):
        logo_path = os.path.join(os.path.dirname(__file__), logo_filename)
    
    header_data = [[]]
    
    # Logo (if exists) — scale proportionally to width=45mm
    if os.path.exists(logo_path):
        _ir = ImageReader(logo_path)
        _orig_w, _orig_h = _ir.getSize()
        _logo_w = 45 * mm
        _logo_h = _logo_w * _orig_h / _orig_w
        header_data[0].append(Image(logo_path, width=_logo_w, height=_logo_h, mask='auto'))
    else:
        header_data[0].append(Paragraph("", style_table_cell))
    
    # Title
    header_data[0].append(Paragraph(f"<b>{title}</b>", style_title))
    
    # Info box — all white text, wider columns
    date_str = datetime.now().strftime("%d-%m-%Y")
    info_table = Table([
        [Paragraph("Model", style_table_cell_white), Paragraph(model_name, style_table_cell_white)],
        [Paragraph("Type",  style_table_cell_white), Paragraph(motor_type,  style_table_cell_white)],
        [Paragraph("Date",  style_table_cell_white), Paragraph(date_str,     style_table_cell_white)]
    ], colWidths=[20*mm, 48*mm])
    info_table.setStyle(TableStyle([
        ('ALIGN',    (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    header_data[0].append(info_table)
    
    header_table = Table(header_data, colWidths=[50*mm, 70*mm, 70*mm], hAlign='CENTER')
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), header_box_color),
        ('BOX', (0,0), (-1,-1), 2, header_box_color),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,-1), FONT_NAME)
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 10))
    
    # General Data Table
    general_data = [
        ["Battery voltage", f"{voltage} V"],
        ["Poles", f"{int(motor_info['poles'])}"],
        ["Connection", motor_info['connection']],
        ["Max temperature", pdf_settings.get('max_temperature', '80°C')],
        ["Ambient temperature", pdf_settings.get('ambient_temperature', '40°C')],
        ["IP class", type_config.get('ip_class', 'IP00')]
    ]
    
    gen_table_data = [[Paragraph("General Data", style_table_header), ""]]
    gen_table_data += [[Paragraph(row[0], ParagraphStyle(name='label', parent=styles['Normal'],
                                                         fontSize=9, fontName=FONT_NAME_BOLD,
                                                         textColor=colors.HexColor("#203764"))),
                        Paragraph(str(row[1]), style_table_cell)] for row in general_data]
    
    gen_table = Table(gen_table_data, colWidths=[60*mm, 60*mm], hAlign='CENTER')
    gen_table.setStyle(TableStyle([
        ('SPAN',       (0,0), (-1,0)),
        ('BACKGROUND', (0,0), (-1,0), header_box_color),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,-1), FONT_NAME),
        ('BOX', (0,0), (-1,-1), 1, header_box_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, header_box_color),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('TEXTCOLOR', (0,1), (-1,-1), header_box_color),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('ALIGN', (0,0), (-1,0),  'CENTER'),
    ]))
    elements.append(gen_table)
    elements.append(Spacer(1, 6))

    # Performance plot — between General Data and Rated Performance
    #elements.append(Paragraph("Performance Curves", style_center))
    #elements.append(Spacer(1, 4))

    if os.path.exists(plot_path):
        plot_img = Image(plot_path, width=185*mm, height=110*mm)
        elements.append(plot_img)
    else:
        elements.append(Paragraph("[Plot not available]", style_table_cell))

    elements.append(Spacer(1, 6))

    # Rated Performance Table
    perf_header = ["Duty", "Torque [Nm]", "Power [kW]", "Speed [rpm]",
                  "Efficiency [%]", "Motor Current [Arms]", "Motor Voltage [Vrms]"]

    perf_data = [[Paragraph("Rated Performance", style_table_header)] +
                ["" for _ in range(len(perf_header)-1)]]
    perf_data.append([Paragraph(h, ParagraphStyle(name='col_header', parent=styles['Normal'],
                                                   fontSize=8, fontName=FONT_NAME_BOLD,
                                                   textColor=colors.HexColor("#203764"),
                                                   alignment=1)) for h in perf_header])

    # Add data rows
    for duty_name, duty_info in type_config['duties'].items():
        perf = performance_data.get(duty_name)
        if perf:
            row = [
                duty_name,
                f"{perf['torque']:.2f}",
                f"{perf['power']:.2f}",
                f"{perf['speed']:.0f}",
                f"{perf['efficiency']:.1f}",
                f"{perf['current']:.2f}",
                f"{perf['voltage']:.1f}"
            ]
        else:
            row = [duty_name] + ["-"] * 6

        perf_data.append([Paragraph(str(cell), style_table_cell) for cell in row])

    perf_table = Table(perf_data, colWidths=[25*mm]*7, hAlign='CENTER')
    perf_table.setStyle(TableStyle([
        ('SPAN',       (0,0), (-1,0)),
        ('BACKGROUND', (0,0), (-1,0), header_box_color),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,-1), FONT_NAME),
        ('BOX', (0,0), (-1,-1), 1, header_box_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, header_box_color),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('TEXTCOLOR', (0,1), (-1,-1), header_box_color),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    elements.append(perf_table)

    # Footer — drawn via canvas callback so it is always anchored to the page bottom
    _dmc_config  = load_dmc_config()
    _cur_s2_5    = (performance_data.get('S2-5min')  or {}).get('current')
    _cur_s2_60   = (performance_data.get('S2-60min') or {}).get('current')
    _inverter, _inv_note = find_suggested_inverter(voltage, _cur_s2_5, _cur_s2_60, _dmc_config)
    if _inverter and _inv_note:
        _footer_text = f"The values reported are simulated  |  Suggested Inverter: {_inverter}  [{_inv_note}]"
    elif _inverter:
        _footer_text = f"The values reported are simulated  |  Suggested Inverter: {_inverter}"
    else:
        _footer_text = "The values reported are simulated  |  Suggested Inverter: not found in catalogue"
    _footer_color = header_box_color
    _footer_font  = FONT_NAME

    def _draw_footer(canvas, doc):
        from reportlab.lib.pagesizes import A4
        _pw, _ = A4
        _fh = 8 * mm
        _y  = doc.bottomMargin - _fh
        canvas.saveState()
        canvas.setFillColor(_footer_color)
        canvas.rect(doc.leftMargin, _y,
                    _pw - doc.leftMargin - doc.rightMargin, _fh,
                    fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont(_footer_font, 9)
        canvas.drawCentredString(_pw / 2, _y + 2 * mm, _footer_text)
        canvas.restoreState()

    # Build PDF — footer injected at canvas level on every page
    doc.build(elements, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    print(f"  PDF generated: {output_path}")


def generate_reports_for_motor(motor_id, motor_data, types_config, db_path, output_dir):
    """
    Generate all PDF reports for a single motor (all types and voltages).
    
    Args:
        motor_id: Database motor ID
        motor_data: Motor data from database
        types_config: Motor types configuration
        db_path: Path to database
        output_dir: Output directory for PDFs
    """
    motor_json = motor_data['motor_json']
    motor_info = get_motor_info_from_json(motor_json)
    
    print(f"\nGenerating reports for Motor ID {motor_id}:")
    print(f"  Diameter: {motor_info['diameter']:.1f} mm")
    print(f"  Length: {motor_info['length']:.1f} mm")
    print(f"  Turns: {motor_info['turns']:.0f}")
    print(f"  Connection: {motor_info['connection']}")
    
    # Get all runs for this motor
    con = sqlite3.connect(db_path)
    runs = database.list_runs_for_motor(motor_id, db_path)
    
    # Group runs by voltage
    runs_by_voltage = {}
    for run in runs:
        v = run['voltage']
        if v not in runs_by_voltage:
            runs_by_voltage[v] = []
        runs_by_voltage[v].append(run)
    
    pdf_settings = types_config.get('pdf_settings', {})
    
    # For each voltage
    for voltage in sorted(runs_by_voltage.keys()):
        voltage_runs = runs_by_voltage[voltage]
        
        # For each motor type
        for motor_type, type_config in types_config['motor_types'].items():
            print(f"\n  Processing Type {motor_type}, Voltage {voltage}V:")
            
            # Collect performance data for each duty
            performance_data = {}
            run_data_list = []
            duty_labels = []

            # Duties shown in the plot (fixed set, order matters)
            PLOT_DUTIES = ['S2-5min', 'S2-20min', 'S2-60min', 'S1']
            
            # Get duties in order: ascending duration (all duties, for the table)
            duties_sorted = sorted(type_config['duties'].items(), 
                                 key=lambda x: x[1]['duration_min'] if isinstance(x[1]['duration_min'], (int, float)) else 999)
            
            for duty_name, duty_info in duties_sorted:
                current_density = duty_info['current_density']
                
                # Find matching run
                matching_run = None
                for run in voltage_runs:
                    if abs(run['current_density'] - current_density) < 0.01:
                        matching_run = run
                        break
                
                if matching_run:
                    perf = get_run_performance_data(con, motor_id, voltage, current_density)
                    if perf:
                        # Always add to performance_data (used by the table)
                        performance_data[duty_name] = perf
                        # Only add to the plot if it's one of the standard plot duties
                        if duty_name in PLOT_DUTIES:
                            run_data = database.load_run_data(con, motor_id, voltage, current_density)
                            run_data_list.append(run_data)
                            duty_labels.append(duty_name)
                        print(f"    {duty_name}: J={current_density} A/mm² - Data found")
                    else:
                        print(f"    {duty_name}: J={current_density} A/mm² - No performance data")
                else:
                    print(f"    {duty_name}: J={current_density} A/mm² - Run not found in database")

            # Re-sort plot lists to match the canonical PLOT_DUTIES order
            if run_data_list:
                _paired = sorted(zip(duty_labels, run_data_list),
                                 key=lambda p: PLOT_DUTIES.index(p[0]) if p[0] in PLOT_DUTIES else 99)
                duty_labels, run_data_list = zip(*_paired)
                duty_labels, run_data_list = list(duty_labels), list(run_data_list)
            
            # Skip if no data found
            if not performance_data:
                print(f"    Skipping - no data for any duty cycle")
                continue
            
            # Generate plot
            temp_plot_path = os.path.join(output_dir, f"temp_plot_{motor_id}_{motor_type}_{int(voltage)}.png")
            try:
                generate_performance_plot(run_data_list, duty_labels, temp_plot_path)
            except Exception as e:
                print(f"    Warning: Failed to generate plot: {e}")
                temp_plot_path = ""
            
            # Generate PDF filename
            pdf_filename = f"{motor_type}_performance_report_D{int(motor_info['diameter'])}_" \
                          f"H{int(motor_info['length'])}_T{int(motor_info['turns'])}_" \
                          f"{motor_info['connection']}_{int(voltage)}V.pdf"
            pdf_path = os.path.join(output_dir, pdf_filename)
            
            # Generate PDF
            try:
                generate_pdf_report(
                    motor_id=motor_id,
                    motor_info=motor_info,
                    voltage=voltage,
                    motor_type=motor_type,
                    type_config=type_config,
                    performance_data=performance_data,
                    plot_path=temp_plot_path,
                    output_path=pdf_path,
                    pdf_settings=pdf_settings
                )
            except Exception as e:
                print(f"    Error generating PDF: {e}")
                import traceback
                traceback.print_exc()
            
            # Clean up temp plot
            if temp_plot_path and os.path.exists(temp_plot_path):
                try:
                    os.remove(temp_plot_path)
                except:
                    pass
    
    con.close()


def generate_all_reports(db_path=None, config_path=CONFIG_FILE, output_dir=None):
    """
    Generate PDF reports for all motors in the database.
    
    Args:
        db_path: Path to database (default: from config)
        config_path: Path to motor types config JSON
        output_dir: Output directory for PDFs
    """
    if db_path is None:
        db_path = config.DB_PATH

    if config_path is None:
        config_path = CONFIG_FILE

    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "..", "generated_pdfs")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Load configuration
    print("="*80)
    print("MotorCAD Performance Report Generator")
    print("="*80)
    print(f"\nDatabase: {db_path}")
    print(f"Output directory: {output_dir}")
    print(f"Config file: {config_path}")
    
    types_config = load_motor_types_config(config_path)
    
    print(f"\nMotor types configured:")
    for mtype, tconfig in types_config['motor_types'].items():
        print(f"  {mtype}: {tconfig['description']}")
        print(f"    Duties: {', '.join(tconfig['duties'].keys())}")
    
    # Get all motors from database
    motors = database.list_all_motors(db_path)
    
    if not motors:
        print("\nNo motors found in database!")
        return
    
    print(f"\nFound {len(motors)} motor(s) in database")
    print("="*80)
    
    # Generate reports for each motor
    for motor in motors:
        try:
            generate_reports_for_motor(
                motor_id=motor['id'],
                motor_data=motor,
                types_config=types_config,
                db_path=db_path,
                output_dir=output_dir
            )
        except Exception as e:
            print(f"\nError processing Motor ID {motor['id']}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*80)
    print("Report generation complete!")
    print(f"PDFs saved to: {output_dir}")
    print("="*80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate PDF performance reports for motors")
    parser.add_argument('--db', type=str, help='Path to database file')
    parser.add_argument('--config', type=str, help='Path to motor types config JSON')
    parser.add_argument('--output', type=str, help='Output directory for PDFs')
    parser.add_argument('--motor-id', type=int, help='Generate report only for specific motor ID')
    
    args = parser.parse_args()
    
    if args.motor_id:
        # Generate report for single motor
        db_path = args.db or config.DB_PATH
        config_path = args.config or CONFIG_FILE
        output_dir = args.output or os.path.join(os.path.dirname(__file__), "..", "generated_pdfs")
        
        os.makedirs(output_dir, exist_ok=True)
        types_config = load_motor_types_config(config_path)
        motors = database.list_all_motors(db_path)
        
        motor_data = None
        for m in motors:
            if m['id'] == args.motor_id:
                motor_data = m
                break
        
        if motor_data:
            generate_reports_for_motor(args.motor_id, motor_data, types_config, db_path, output_dir)
        else:
            print(f"Motor ID {args.motor_id} not found in database")
    else:
        # Generate reports for all motors
        generate_all_reports(
            db_path=args.db or None,
            config_path=args.config or CONFIG_FILE,
            output_dir=args.output or None
        )
