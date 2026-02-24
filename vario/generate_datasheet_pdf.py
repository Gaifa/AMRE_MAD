import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

# Font registration (Aptos)
APTOS_FONT_PATH = "Aptos-Regular.ttf"  # Inserisci il file Aptos nella cartella script
if os.path.exists(APTOS_FONT_PATH):
    pdfmetrics.registerFont(TTFont("Aptos", APTOS_FONT_PATH))
    FONT_NAME = "Aptos"
else:
    FONT_NAME = "Helvetica"

# Paths
LOGO_PATH = "AMRE_logo.png"  # Place the logo in the same directory as the script or provide the correct path
OUTPUT_PDF = "datasheet_motore.pdf"

def generate_datasheet(
    output_path=OUTPUT_PDF,
    logo_path=LOGO_PATH,
    title="PERFOMANCE REPORT - ##Vdc",
    mod= "xxx-xxx-hx", #IM Dext_statore axial lenght ( N turns + 33 ) Hex,
    rev="Rev. 1.0",
    date=None,
    general_data=None,
    rated_performance=None,
):
    if date is None:
        date = datetime.now().strftime("%d-%m-%Y")
    if general_data is None:
        general_data = [
            ["Battery voltage", "--"],
            ["Pole", "--"],
            ["Connection", "--"],
            ["Max temperature", "--"],
            ["Ambient temperature", "--"],
            ["IP class", "--"]
        ]
    if rated_performance is None:
        rated_performance = [
            ["Duty", "Torque [Nm]", "Power [kW]", "Speed [rpm]", "Efficiency [%]", "Motor Current [Arms]", "Motor Voltage [Vrms]"],
            ["S1", "-", "-", "-", "-", "-", "-"],
            ["S2-60min", "-", "-", "-", "-", "-", "-"],
            ["S2-20min", "-", "-", "-", "-", "-", "-"],
            ["S2-10min", "-", "-", "-", "-", "-", "-"],
            ["S2-5min", "-", "-", "-", "-", "-", "-"]
        ]

    doc = SimpleDocTemplate(output_path, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    style_center = ParagraphStyle(name='center', parent=styles['Normal'], alignment=1, fontSize=14, spaceAfter=10, fontName=FONT_NAME)
    style_title = ParagraphStyle(name='title', parent=styles['Title'], alignment=1, fontSize=18, spaceAfter=10, fontName=FONT_NAME, textColor=colors.white)
    style_footer = ParagraphStyle(name='footer', parent=styles['Normal'], alignment=1, fontSize=10, textColor=colors.white, fontName=FONT_NAME)
    style_table_header = ParagraphStyle(name='table_header', parent=styles['Normal'], fontSize=12, textColor=colors.white, fontName=FONT_NAME)
    style_table_cell = ParagraphStyle(name='table_cell', parent=styles['Normal'], fontSize=11, fontName=FONT_NAME)

    # Header trasposto in riquadro colorato
    header_box_color = colors.HexColor("#203764")
    header_table_data = [
        [
            Image(logo_path, width=30*mm, height=20*mm, mask='auto'),
            Paragraph(f"<b>{title}</b>", style_title),
            Table([
                [Paragraph("Mod", style_table_header), Paragraph(mod, style_table_cell)],
                [Paragraph("Rev", style_table_header), Paragraph(rev, style_table_cell)],
                [Paragraph("Date", style_table_header), Paragraph(date, style_table_cell)]
            ], colWidths=[40, 70], style=TableStyle([
                ('BACKGROUND', (0,0), (-1,0), header_box_color),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (-1,-1), FONT_NAME),
                ('BOX', (0,0), (-1,-1), 1, header_box_color),
                ('INNERGRID', (0,0), (-1,-1), 0.5, header_box_color)
            ]))
        ]
    ]
    header_table = Table(header_table_data, colWidths=[50*mm, 70*mm, 70*mm], hAlign='CENTER')
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), header_box_color),
        ('BOX', (0,0), (-1,-1), 2, header_box_color),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,-1), FONT_NAME)
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 10))

    # General Data Table trasposta con titolo integrato
    gen_table_data = [[Paragraph("General Data", style_table_header), ""]] + [[Paragraph(row[0], style_table_cell), Paragraph(row[1], style_table_cell)] for row in general_data]
    gen_table = Table(gen_table_data, colWidths=[60*mm, 60*mm], hAlign='CENTER')
    gen_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), header_box_color),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,-1), FONT_NAME),
        ('BOX', (0,0), (-1,-1), 1, header_box_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, header_box_color),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('TEXTCOLOR', (0,1), (-1,-1), header_box_color)
    ]))
    elements.append(gen_table)
    elements.append(Spacer(1, 12))

    # Rated Performance Table con titolo integrato
    perf_table_data = [
        [Paragraph("Rated Performance", style_table_header)] + ["" for _ in range(len(rated_performance[0])-1)]
    ] + [
        [Paragraph(cell, style_table_cell) for cell in row] for row in rated_performance
    ]
    perf_table = Table(perf_table_data, colWidths=[25*mm]*7, hAlign='CENTER')
    perf_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), header_box_color),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,-1), FONT_NAME),
        ('BOX', (0,0), (-1,-1), 1, header_box_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, header_box_color),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('TEXTCOLOR', (0,1), (-1,-1), header_box_color)
    ]))
    elements.append(perf_table)
    elements.append(Spacer(1, 20))

    # Footer
    elements.append(Spacer(1, 30))
    footer_box = Table([[Paragraph("the values reported are simulated - suggested Inverter : DMC model", style_footer)]], colWidths=[180*mm])
    footer_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), header_box_color),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.white),
        ('FONTNAME', (0,0), (-1,-1), FONT_NAME),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BOX', (0,0), (-1,-1), 1, header_box_color)
    ]))
    elements.append(footer_box)

    # Page 2: Graph placeholders (font Aptos)
    elements.append(PageBreak())
    elements.append(Paragraph("Torque-Power Graph", style_center))
    elements.append(Spacer(1, 100))
    elements.append(Paragraph("[Insert torque-power graph here]", style_table_cell))
    elements.append(Spacer(1, 40))
    elements.append(Paragraph("Efficiency Graph", style_center))
    elements.append(Spacer(1, 100))
    elements.append(Paragraph("[Insert efficiency graph here]", style_table_cell))

    doc.build(elements)
    print(f"PDF generated: {output_path}")

if __name__ == "__main__":
    generate_datasheet()
