import win32com.client
import math
import os
import scipy.io
import pandas as pd
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle, Spacer,
                                Image, Paragraph, PageBreak)
import tempfile
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import numpy as np
from reportlab.pdfgen import canvas
from datetime import datetime

# =========================================================
# A) Funzione che trova il punto nominale (da rep8.py)
# =========================================================
def trova_punto_nominale(df):
    """
    Restituisce l'indice (0-based) in cui la tensione
    diventa costante per almeno 4 righe consecutive 
    (entro il 2% di tolleranza).
    """
    colonna_tensione = 'Motor Voltage'
    tensioni = df[colonna_tensione]
    tolleranza = 0.02
    for i in range(len(tensioni) - 3):
        if all(abs(tensioni.iloc[i + j] - tensioni.iloc[i]) / tensioni.iloc[i] <= tolleranza for j in range(4)):
            return i + 1
    return None

# =========================================================
# B) Funzione per disegnare il footer (da pro5.py)
# =========================================================
def draw_footer(canv, doc):
    canv.saveState()
    # Disegna la barra in fondo: larghezza fissa di 510 pt centrata
    canv.setStrokeColor(colors.HexColor("#203764"))
    canv.setLineWidth(2)
    y_line = 45  # distanza dal fondo in punti
    bar_width = 510
    page_width = doc.pagesize[0]
    x_start = (page_width - bar_width) / 2
    canv.line(x_start, y_line, x_start + bar_width, y_line)
    
    # A sinistra, in grigio, la data odierna + "AMRE srl - Simulated Values"
    current_date = datetime.now().strftime('%d/%m/%Y')
    left_text = f"{current_date} - AMRE srl - Simulated Values - FRAMELESS"
    canv.setFont("Helvetica", 10)
    canv.setFillColor(colors.grey)
    canv.drawString(x_start, y_line - 22, left_text)
    
    # A destra, in nero, il numero di pagina
    canv.setFillColor(colors.black)
    page_num = canv.getPageNumber()
    canv.drawRightString(x_start + bar_width, y_line - 22, f"Pag. {page_num} di 3")
    canv.restoreState()

# =========================================================
# C) Stili e impostazioni per la tabella (da pro5.py)
# =========================================================
header_style_title = ParagraphStyle(
    name='HeaderStyleTitle',
    fontName='Helvetica-Bold',
    fontSize=12,
    alignment=TA_CENTER,
    leading=15
)
header_style = ParagraphStyle(
    name='HeaderStyle',
    fontName='Helvetica',
    fontSize=9.5,
    alignment=TA_CENTER,
    leading=10
)
headers_paragraphs = [
    Paragraph("Speed<br/><font size='8'>[rpm]</font>", header_style),
    Paragraph("Shaft Torque<br/><font size='8'>[Nm]</font>", header_style),
    Paragraph("Shaft Power<br/><font size='8'>[kW]</font>", header_style),
    Paragraph("Motor Voltage<br/><font size='8'>[Vrms]</font>", header_style),
    Paragraph("Motor Current<br/><font size='8'>[Arms]</font>", header_style),
    Paragraph("Power Factor<br/><font size='8'>[-]</font>", header_style),
    Paragraph("Efficiency<br/><font size='8'>[%]</font>", header_style),
    Paragraph("Frequency<br/><font size='8'>[Hz]</font>", header_style)
]
col_widths = [40.91, 69.81, 66.47, 74.25, 73.68, 71.46, 54.79, 59.24]

# =========================================================
# D) Funzione principale (integrando rep8.py e grafici da MEC.py)
# =========================================================
def main():
    print('Avvio Inizializzazione')
    mcad = win32com.client.Dispatch("MotorCAD.AppAutomation")
    mcad.SetVariable('MessageDisplayState', 2)
    print('Inizializzazione Completata')
    
    # 1) PARAMETRI DI INPUT
    Vm = 6000
    txt_file_path = r"C:\Users\grell\Desktop\MCAD_jack\simulazioni_frameless.txt"
    final_pdf_name = "Performance_Report"
    logo_path = r"C:\Users\grell\Desktop\Script\AMRE_Logo.png"
    

    if not os.path.exists(txt_file_path):
        print("Il percorso specificato per il file di testo non esiste.")
        return
    
    with open(txt_file_path, 'r') as file:
        lines = file.readlines()
    
    # 2) LETTURA FILE .TXT A COPPIE (MCAD-FILE, TENSIONE)
    for i in range(0, len(lines), 2):
        mcad_file_path = lines[i].strip()
        if i + 1 < len(lines):
            tensione_nominale = lines[i+1].strip()
            indice_tensione = i+1
            try:
                print(f"\n=== Inizio Simulazione File: {mcad_file_path} ===")
                print(f"Tensione utilizzata: {tensione_nominale}Vdc")
                print(f"Numero di giri max: {Vm}rpm")
                
                mcad.LoadFromFile(mcad_file_path)
                
                # 3) CALCOLO CORRENTI (NOMINALE, POMPA, MAX)
                variable_value = mcad.GetVariable("ArmatureTurnCSA")
                parallel_path = mcad.GetVariable("ParallelPaths")
                sezione = float(variable_value[1])
                paralleli = int(float(parallel_path[1]))
                print(f"Paralleli: {paralleli}")
                sezione_equivalente = round(sezione * math.sqrt(3) * paralleli, 2)
                print(f"Sezione Equivalente: {sezione_equivalente} mm2")
                
                corrente_nominale = round(sezione_equivalente * 4, 1)
                corrente_pompa = round(sezione_equivalente * 7, 1)
                corrente_max = round(sezione_equivalente * 13, 1)
                print(f"Corrente nominale: {corrente_nominale}Arms")
                print(f"Corrente pompa: {corrente_pompa}Arms")
                print(f"Corrente massima: {corrente_max}Arms")
                
                # 4) VERIFICA BUILD MODEL ED EVENTUALE RICALCOLO
                matlabpath = os.path.splitext(mcad_file_path)[0]
                BuildSpeed = mcad.GetVariable('ModelBuildSpeed_MotorLAB')
                BuildCurrent = mcad.GetVariable('MaxModelCurrent_RMS_MotorLAB')
                Max_Speed = float(BuildSpeed[1])
                Max_Current = round(float(BuildCurrent[1]), 1)
                print(f"Modello: speed={Max_Speed}rpm, corrente max={Max_Current}Arms")
                
                if Max_Current >= corrente_max and Max_Speed >= Vm:
                    print("Il modello presente soddisfa i requisiti.")
                    Imax = int(corrente_max * 1.2)
                    Imin = int(Imax * 0.01)
                else:
                    print("Ricalcolo modello con saturazione...")
                    mcad.SetVariable('ModelBuildSpeed_MotorLAB', Vm)
                    Imax = int(corrente_max * 1.2)
                    Imin = int(Imax * 0.01)
                    mcad.SetVariable('MaxModelCurrent_RMS_MotorLAB', Imax)
                    mcad.SetVariable('BuildSatModel_MotorLAB', True)
                    mcad.SetMotorLABContext()
                    mcad.BuildModel_Lab()
                
                # 5) CREAZIONE DI UN UNICO PDF CON 3 PAGINE
                pdf_name = f"{final_pdf_name}_{tensione_nominale}Vdc.pdf"
                pdf_path = os.path.join(os.path.dirname(mcad_file_path), pdf_name)
                doc = SimpleDocTemplate(pdf_path, pagesize=letter, topMargin=30, bottomMargin=20)
                all_flowables = []
                
                # 6) CICLO SULLE 3 CORRENTI (3 PAGINE)
                for idx, corrente in enumerate([corrente_nominale, corrente_pompa, corrente_max]):
                    print(f"\n-- Simulazione per corrente: {corrente}Arms --")
                    
                    # 6.1) Simulazione "semplice" (Excel + punto nominale)
                    mcad.ShowMagneticContext()
                    mcad.DisplayScreen('Scripting')
                    mcad.SetVariable("EmagneticCalcType_Lab", 0)
                    mcad.SetVariable("DCBusVoltage", tensione_nominale)
                    mcad.SetVariable("ModulationIndex_MotorLAB", 0.95)
                    mcad.SetVariable("CurrentSpec_MotorLAB", 1)
                    mcad.SetVariable("CurrentDefinition", 1)
                    mcad.SetVariable("Imax_RMS_MotorLAB", corrente)
                    mcad.SetVariable("SpeedMax_MotorLAB", Vm)
                    mcad.SetVariable('Speedinc_MotorLAB', 50)
                    mcad.SetVariable('SpeedMin_MotorLAB', 50)
                    mcad.SetVariable("AutoShowResults_MotorLAB", True)
                    mcad.CalculateMagnetic_Lab()
                    
                    mat_file_simple = os.path.join(matlabpath, r"Lab\MotorLAB_elecdata.mat")
                    data_simple = scipy.io.loadmat(mat_file_simple)
                    
                    Speed_simple = data_simple['Speed']
                    ShaftTorque_simple = data_simple['Shaft_Torque']
                    ShaftPower_simple = data_simple['Shaft_Power']
                    MotorVoltage_simple = data_simple['Voltage_Phase_RMS']
                    MotorCurrent_simple = data_simple['Stator_Current_Line_RMS']
                    PowerFactor_simple = data_simple['Power_Factor_From_Power_Balance']
                    Efficiency_simple = data_simple['Efficiency']
                    Frequency_simple = data_simple['Frequency']
                    
                    excel_name = f"{corrente}Arms @ {tensione_nominale}Vdc.xlsx"
                    excel_path = os.path.join(os.path.dirname(mcad_file_path), excel_name)
                    df_simple = pd.DataFrame({
                        'Speed': Speed_simple.flatten(),
                        'Shaft Torque': ShaftTorque_simple.flatten(),
                        'Shaft Power': ShaftPower_simple.flatten(),
                        'Motor Voltage': MotorVoltage_simple.flatten(),
                        'Motor Current': MotorCurrent_simple.flatten(),
                        'Power Factor': PowerFactor_simple.flatten(),
                        'Efficiency': Efficiency_simple.flatten(),
                        'Frequency': Frequency_simple.flatten()
                    })
                    df_simple.to_excel(excel_path, sheet_name=f"{corrente}Arms @ {tensione_nominale}Vdc", index=False)
                    print(f"Salvato file Excel: {excel_name}")
                    
                    # Trovo il punto nominale
                    df_for_nominal = pd.read_excel(excel_path)
                    idx_nominal = trova_punto_nominale(df_for_nominal)
                    
                    # 6.1.1) Creazione tabella "Nominal Working Point" in stile pro5
                    table_data_nominal = []
                    if idx_nominal is not None:
                        print(f"Punto nominale trovato alla riga {idx_nominal + 2}.")
                        punto_nominale = df_for_nominal.iloc[idx_nominal]
                        # Riga 1: Titolo "Nominal Working Point" su tutte le colonne
                        table_data_nominal.append([Paragraph("Nominal Working Point", header_style_title)] * len(headers_paragraphs))
                        # Riga 2: intestazioni con unità (due dimensioni)
                        table_data_nominal.append(headers_paragraphs)
                        # Riga 3: valori del punto nominale
                        row_data = []
                        for j in range(len(headers_paragraphs)):
                            val = punto_nominale.iloc[j] #modifica per errore indicizzazione
                            if j == 5:
                                row_data.append(round(val, 3))
                            elif j == 0:
                                row_data.append(int(val))
                            else:
                                row_data.append(round(val, 1))
                        table_data_nominal.append(row_data)
                    
                    # 6.2) Generazione dei tre grafici (come in MEC.py)
                    # Calcolo limiti per Torque e Power
                    max_torque = max(ShaftTorque_simple)
                    max_power = max(ShaftPower_simple)
                    tolerance = 0.2
                    torque_y_max = max_torque + (max_torque * tolerance)
                    power_y_max = max_power + (max_power * tolerance)
                    
                    # GENERO GRAFICO COPPIA/VELOCITA
                    plt.figure(figsize=(12,5.3))
                    plt.plot(df_simple['Speed'], df_simple['Shaft Torque'], label='Torque')
                    plt.xlabel('Speed [rpm]', fontsize=13)
                    plt.ylabel('Torque [Nm]', fontsize=13)
                    plt.title('Torque vs Speed', fontsize=15, fontweight='bold')
                    plt.grid(True)
                    plt.legend()
                    plt.ylim(0, torque_y_max)
                    plt.xlim(0, Vm)
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmpfile1:
                        grafico_path1 = tmpfile1.name
                        plt.savefig(grafico_path1, dpi=800)
                    plt.close()
                    
                    # GENERO GRAFICO POTENZA/VELOCITA
                    plt.figure(figsize=(12,5.3))
                    plt.plot(df_simple['Speed'], df_simple['Shaft Power'], label='Power')
                    plt.xlabel('Speed [rpm]', fontsize=13)
                    plt.ylabel('Shaft Power [kW]', fontsize=13)
                    plt.title('Power vs Speed', fontsize=15, fontweight='bold')
                    plt.grid(True)
                    plt.legend()
                    plt.ylim(0, power_y_max)
                    plt.xlim(0, Vm)
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmpfile2:
                        grafico_path2 = tmpfile2.name
                        plt.savefig(grafico_path2, dpi=800)
                    plt.close()
                    
                    # GENERO GRAFICO EFFICIENZA/VELOCITA
                    plt.figure(figsize=(12,5.3))
                    plt.plot(df_simple['Speed'], df_simple['Efficiency'], label='Efficiency')
                    plt.xlabel('Speed [rpm]', fontsize=13)
                    plt.ylabel('Efficiency [%]', fontsize=13)
                    plt.title('Efficiency vs Speed', fontsize=15, fontweight='bold')
                    plt.grid(True)
                    plt.legend()
                    plt.ylim(50,100)
                    plt.xlim(0, Vm)
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmpfile3:
                        grafico_path3 = tmpfile3.name
                        plt.savefig(grafico_path3, dpi=800)
                    plt.close()
                    
                    # 6.3) Creazione del titolo della pagina con duty time
                    duty_time = "60-min duty" if corrente == corrente_nominale else ("20-min duty" if corrente == corrente_pompa else "5-min duty")
                    title_string = f"<para>{'&nbsp;' * 18}{duty_time} @ {tensione_nominale}Vdc</para>"
                    title_style_page = ParagraphStyle(
                        name='TitleStyle',
                        fontName='Helvetica',
                        fontSize=14,
                        textColor=colors.white,
                        alignment=TA_CENTER
                    )
                    title_paragraph = Paragraph(title_string, title_style_page)
                    
                    if os.path.exists(logo_path):
                        logo_img = Image(logo_path, width=90, height=30)
                        logo_img.hAlign = 'RIGHT'
                    else:
                        logo_img = Paragraph("(Logo non trovato)", getSampleStyleSheet()['Normal'])
                    
                    title_table_data = [[title_paragraph, logo_img]]
                    title_table = Table(title_table_data, colWidths=[420, 90])
                    title_table.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0070C0")),
                        ('VALIGN', (0,0), (-1,0), 'MIDDLE'),
                        ('ALIGN', (0,0), (0,0), 'LEFT'),
                        ('ALIGN', (1,0), (1,0), 'RIGHT'),
                        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                        ('TOPPADDING', (0,0), (-1,0), 0),
                        ('BOTTOMPADDING', (0,0), (-1,0), 7),
                        ('TOPPADDING', (1,0), (1,0), 3),
                        ('BOTTOMPADDING', (1,0), (1,0), 3),
                    ]))
                    
                    all_flowables.append(title_table)
                    all_flowables.append(Spacer(1,10))
                    
                    if table_data_nominal:
                        nominal_table = Table(table_data_nominal, colWidths=col_widths)
                        nominal_table.setStyle(TableStyle([
                            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica'),
                            ('SPAN', (0, 0), (-1, 0)),
                            ('BACKGROUND', (0, 0), (-1, 0), colors.white),
                        ]))
                        all_flowables.append(nominal_table)
                        all_flowables.append(Spacer(1,20))
                    
                    # Inserisco i tre grafici nel report
                    if os.path.exists(grafico_path1):
                        all_flowables.append(Image(grafico_path1, width=407, height=180))
                        all_flowables.append(Spacer(1,15))
                    if os.path.exists(grafico_path2):
                        all_flowables.append(Image(grafico_path2, width=407, height=180))
                        all_flowables.append(Spacer(1,15))
                    if os.path.exists(grafico_path3):
                        all_flowables.append(Image(grafico_path3, width=407, height=180))
                    
                    if idx < 2:
                        all_flowables.append(PageBreak())
                
                # 7) BUILD DEL PDF UNICO (3 PAGINE) + FOOTER
                doc.build(all_flowables, onFirstPage=draw_footer, onLaterPages=draw_footer)
                print(f"Generato PDF unico: {pdf_name}")
                
                lines[indice_tensione] = f"{tensione_nominale} \n"
                print("Simulazione Completata")
            
            except Exception as e:
                print(f"Si è verificato un errore: {e}")
    
    with open(txt_file_path, 'w') as file:
        file.writelines(lines)
    
    mcad.Quit()
    print("Simulazioni Completate")


if __name__ == "__main__":
    main()
