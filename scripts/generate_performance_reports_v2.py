"""
MotorCAD Performance Report Generator - Layout V2

Layout order:
    Header → General Data → Rated Performance → Performance Curves → Footer

Usage (identical to the original):
    python scripts/generate_performance_reports_v2.py
    python scripts/generate_performance_reports_v2.py --motor-id 3
    python scripts/generate_performance_reports_v2.py --output generated_pdfs/v2

Author: MotorCAD Analysis Team
Date: February 2026
"""

import os
import sys

# ---------------------------------------------------------------------------
# Import everything from the base module, then patch only generate_pdf_report
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(__file__))
import generate_performance_reports as _base  # noqa: E402

# Pull shared names into this namespace so they are available below
from generate_performance_reports import (  # noqa: F401, E402
    load_motor_types_config,
    get_motor_info_from_json,
    generate_performance_plot,
    get_run_performance_data,
    generate_reports_for_motor,
    generate_all_reports,
    CONFIG_FILE,
    COLORS,
    FONT_NAME,
    FONT_NAME_BOLD,
)

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics

from datetime import datetime


def generate_pdf_report(motor_id, motor_info, voltage, motor_type, type_config,
                        performance_data, plot_path, output_path, pdf_settings):
    """
    Generate a PDF performance report for a motor.

    Layout V2 — plot is placed BELOW both tables:
        Header → General Data → Rated Performance → Performance Curves → Footer
    """
    # Create document
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        topMargin=8 * mm, bottomMargin=18 * mm,
        leftMargin=10 * mm, rightMargin=10 * mm,
    )
    elements = []
    styles = getSampleStyleSheet()

    # -----------------------------------------------------------------------
    # Styles
    # -----------------------------------------------------------------------
    header_box_color = colors.HexColor("#203764")

    style_title = ParagraphStyle(
        name='title', parent=styles['Title'],
        alignment=1, fontSize=18, spaceAfter=10,
        fontName=FONT_NAME, textColor=colors.white,
    )
    style_center = ParagraphStyle(
        name='center', parent=styles['Normal'],
        alignment=1, fontSize=14, spaceAfter=10,
        fontName=FONT_NAME,
    )
    style_table_header = ParagraphStyle(
        name='table_header', parent=styles['Normal'],
        fontSize=13, textColor=colors.white,
        fontName=FONT_NAME_BOLD, wordWrap=None,
        alignment=1,
    )
    style_table_cell = ParagraphStyle(
        name='table_cell', parent=styles['Normal'],
        fontSize=9, fontName=FONT_NAME,
    )
    style_table_cell_white = ParagraphStyle(
        name='table_cell_white', parent=styles['Normal'],
        fontSize=9, fontName=FONT_NAME_BOLD,
        textColor=colors.white, wordWrap=None,
    )
    style_label_blue = ParagraphStyle(
        name='label_blue', parent=styles['Normal'],
        fontSize=9, fontName=FONT_NAME_BOLD,
        textColor=colors.HexColor("#203764"),
    )
    style_col_header = ParagraphStyle(
        name='col_header', parent=styles['Normal'],
        fontSize=8, fontName=FONT_NAME_BOLD,
        textColor=colors.HexColor("#203764"),
        alignment=1,
    )

    # -----------------------------------------------------------------------
    # Header
    # -----------------------------------------------------------------------
    model_name = (
        f"IM-D{int(motor_info['diameter'])}-H{int(motor_info['length'])}"
        f"-{int(motor_info['turns'])}T-{motor_info['connection']}"
    )
    title = "PERFORMANCE REPORT"

    _vario = os.path.join(os.path.dirname(__file__), '..', 'vario')
    logo_filename = pdf_settings.get('logo_path', 'AMRE_Logo.png')
    logo_path = os.path.join(_vario, logo_filename)
    if not os.path.exists(logo_path):
        logo_path = os.path.join(os.path.dirname(__file__), logo_filename)

    header_data = [[]]
    if os.path.exists(logo_path):
        _ir = ImageReader(logo_path)
        _orig_w, _orig_h = _ir.getSize()
        _logo_w = 45 * mm
        _logo_h = _logo_w * _orig_h / _orig_w
        header_data[0].append(Image(logo_path, width=_logo_w, height=_logo_h, mask='auto'))
    else:
        header_data[0].append(Paragraph("", style_table_cell))

    header_data[0].append(Paragraph(f"<b>{title}</b>", style_title))

    date_str = datetime.now().strftime("%d-%m-%Y")
    info_table = Table([
        [Paragraph("Model", style_table_cell_white), Paragraph(model_name, style_table_cell_white)],
        [Paragraph("Type",  style_table_cell_white), Paragraph(motor_type,  style_table_cell_white)],
        [Paragraph("Date",  style_table_cell_white), Paragraph(date_str,    style_table_cell_white)],
    ], colWidths=[20 * mm, 48 * mm])
    info_table.setStyle(TableStyle([
        ('ALIGN',         (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME',      (0, 0), (-1, -1), FONT_NAME),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    header_data[0].append(info_table)

    header_table = Table(header_data, colWidths=[50 * mm, 70 * mm, 70 * mm], hAlign='CENTER')
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), header_box_color),
        ('BOX',        (0, 0), (-1, -1), 2, header_box_color),
        ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',      (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME',   (0, 0), (-1, -1), FONT_NAME),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 10))

    # -----------------------------------------------------------------------
    # General Data table
    # -----------------------------------------------------------------------
    general_data = [
        ["Battery voltage", f"{voltage} V"],
        ["Poles",           f"{int(motor_info['poles'])}"],
        ["Connection",      motor_info['connection']],
        ["Max temperature", pdf_settings.get('max_temperature', '80°C')],
        ["Ambient temperature", pdf_settings.get('ambient_temperature', '40°C')],
        ["IP class",        type_config.get('ip_class', 'IP00')],
    ]

    gen_table_data = [[Paragraph("General Data", style_table_header), ""]]
    gen_table_data += [
        [Paragraph(row[0], style_label_blue), Paragraph(str(row[1]), style_table_cell)]
        for row in general_data
    ]

    gen_table = Table(gen_table_data, colWidths=[60 * mm, 60 * mm], hAlign='CENTER')
    gen_table.setStyle(TableStyle([
        ('SPAN',       (0, 0), (-1, 0)),
        ('BACKGROUND', (0, 0), (-1, 0), header_box_color),
        ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
        ('FONTNAME',   (0, 0), (-1, -1), FONT_NAME),
        ('BOX',        (0, 0), (-1, -1), 1, header_box_color),
        ('INNERGRID',  (0, 0), (-1, -1), 0.5, header_box_color),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR',  (0, 1), (-1, -1), header_box_color),
        ('ALIGN',      (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN',      (0, 0), (-1,  0), 'CENTER'),
    ]))
    elements.append(gen_table)
    elements.append(Spacer(1, 6))

    # -----------------------------------------------------------------------
    # Rated Performance table
    # -----------------------------------------------------------------------
    perf_header = [
        "Duty", "Torque [Nm]", "Power [kW]", "Speed [rpm]",
        "Efficiency [%]", "Motor Current [Arms]", "Motor Voltage [Vrms]",
    ]

    perf_data = [[Paragraph("Rated Performance", style_table_header)] +
                 ["" for _ in range(len(perf_header) - 1)]]
    perf_data.append([Paragraph(h, style_col_header) for h in perf_header])

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
                f"{perf['voltage']:.1f}",
            ]
        else:
            row = [duty_name] + ["-"] * 6
        perf_data.append([Paragraph(str(cell), style_table_cell) for cell in row])

    perf_table = Table(perf_data, colWidths=[25 * mm] * 7, hAlign='CENTER')
    perf_table.setStyle(TableStyle([
        ('SPAN',       (0, 0), (-1, 0)),
        ('BACKGROUND', (0, 0), (-1, 0), header_box_color),
        ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
        ('FONTNAME',   (0, 0), (-1, -1), FONT_NAME),
        ('BOX',        (0, 0), (-1, -1), 1, header_box_color),
        ('INNERGRID',  (0, 0), (-1, -1), 0.5, header_box_color),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR',  (0, 1), (-1, -1), header_box_color),
        ('ALIGN',      (0, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(perf_table)
    elements.append(Spacer(1, 6))

    # -----------------------------------------------------------------------
    # Performance plot — BELOW both tables
    # -----------------------------------------------------------------------
    #elements.append(Paragraph("Performance Curves", style_center))
    #elements.append(Spacer(1, 4))

    if os.path.exists(plot_path):
        elements.append(Image(plot_path, width=185 * mm, height=110 * mm))
    else:
        elements.append(Paragraph("[Plot not available]", style_table_cell))

    # -----------------------------------------------------------------------
    # Footer — anchored to page bottom via canvas callback
    # -----------------------------------------------------------------------
    _dmc_config  = _base.load_dmc_config()
    _cur_s2_5    = (performance_data.get('S2-5min')  or {}).get('current')
    _cur_s2_60   = (performance_data.get('S2-60min') or {}).get('current')
    _inverter, _inv_note = _base.find_suggested_inverter(voltage, _cur_s2_5, _cur_s2_60, _dmc_config)
    if _inverter and _inv_note:
        _footer_text = f"The values reported are simulated  |  Suggested Inverter: {_inverter}  [{_inv_note}]"
    elif _inverter:
        _footer_text = f"The values reported are simulated  |  Suggested Inverter: {_inverter}"
    else:
        _footer_text = "The values reported are simulated  |  Suggested Inverter: not found in catalogue"
    _footer_color = header_box_color
    _footer_font  = FONT_NAME

    def _draw_footer(canvas, doc):
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

    doc.build(elements, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    print(f"  PDF generated: {output_path}")


# ---------------------------------------------------------------------------
# Patch the base module so generate_reports_for_motor uses this layout
# ---------------------------------------------------------------------------
_base.generate_pdf_report = generate_pdf_report


# ---------------------------------------------------------------------------
# CLI — identical interface to the original script
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    from src import config as _cfg

    parser = argparse.ArgumentParser(
        description="Generate PDF performance reports (layout V2: plot below tables)"
    )
    parser.add_argument('--db',       type=str, help='Path to database file')
    parser.add_argument('--config',   type=str, help='Path to motor types config JSON')
    parser.add_argument('--output',   type=str, help='Output directory for PDFs')
    parser.add_argument('--motor-id', type=int, help='Generate report only for a specific motor ID')

    args = parser.parse_args()

    if args.motor_id:
        db_path    = args.db or _cfg.DB_PATH
        cfg_path   = args.config or CONFIG_FILE
        output_dir = args.output or os.path.join(os.path.dirname(__file__), "..", "generated_pdfs")
        os.makedirs(output_dir, exist_ok=True)

        from src import database
        types_config = load_motor_types_config(cfg_path)
        motors = database.list_all_motors(db_path)
        motor_data = next((m for m in motors if m['id'] == args.motor_id), None)

        if motor_data:
            generate_reports_for_motor(args.motor_id, motor_data, types_config, db_path, output_dir)
        else:
            print(f"Motor ID {args.motor_id} not found in database")
    else:
        generate_all_reports(
            db_path=args.db or None,
            config_path=args.config or CONFIG_FILE,
            output_dir=args.output or None,
        )
