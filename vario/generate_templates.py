import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

def create_template(template_code, output_dir):
    """Crea un template PDF di due pagine per i dati del motore."""
    file_path = os.path.join(output_dir, f"{template_code}.pdf")
    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    # Stile dell'header ispirato a FRAMELESS_v2 (ipotetico)
    header_color = (0.1, 0.2, 0.5)  # Blu scuro
    c.setFillColorRGB(*header_color)
    c.rect(0, height - 1.5 * cm, width, 1.5 * cm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)  # Bianco
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1.5 * cm, height - 1 * cm, f"Template Motore: {template_code}")

    # Pagina 1: Informazioni di base
    c.setFillColorRGB(0, 0, 0)  # Nero
    c.setFont("Helvetica-Bold", 18)
    c.drawString(2 * cm, height - 3 * cm, "Pagina 1: Informazioni di Base del Motore")

    c.setFont("Helvetica", 12)
    y_position = height - 4.5 * cm
    info_labels = [
        "Nome Motore:", "Codice Prodotto:", "Tensione Nominale (V):",
        "Corrente a Vuoto (A):", "Velocità a Vuoto (rpm):", "Coppia Nominale (Nm):",
        "Potenza di Uscita (W):", "Efficienza (%):"
    ]
    for label in info_labels:
        c.drawString(2 * cm, y_position, label)
        y_position -= 1 * cm

    c.showPage()  # Termina la prima pagina

    # Pagina 2: Grafici di Coppia ed Efficienza
    c.setFillColorRGB(*header_color)
    c.rect(0, height - 1.5 * cm, width, 1.5 * cm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1.5 * cm, height - 1 * cm, f"Template Motore: {template_code}")

    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(2 * cm, height - 3 * cm, "Pagina 2: Grafici Prestazionali")

    # Placeholder per il grafico di coppia
    c.setFont("Helvetica", 14)
    c.drawString(2 * cm, height - 4.5 * cm, "Grafico Curva di Coppia")
    c.setStrokeColorRGB(0.2, 0.2, 0.2)
    c.grid([2 * cm, 18 * cm], [height - 12 * cm, height - 5 * cm])
    c.drawString(2 * cm, height - 12.5 * cm, "Velocità (rpm)")
    c.saveState()
    c.rotate(90)
    c.drawString(height - 11.5 * cm, -1.5 * cm, "Coppia (Nm)")
    c.restoreState()

    # Placeholder per il grafico di efficienza
    c.setFont("Helvetica", 14)
    c.drawString(2 * cm, height - 14.5 * cm, "Grafico Curva di Efficienza")
    c.grid([2 * cm, 18 * cm], [height - 22 * cm, height - 15 * cm])
    c.drawString(2 * cm, height - 22.5 * cm, "Velocità (rpm)")
    c.saveState()
    c.rotate(90)
    c.drawString(height - 21.5 * cm, -1.5 * cm, "Efficienza (%)")
    c.restoreState()

    c.save()
    print(f"Creato template: {file_path}")

def main():
    """Funzione principale per generare i template."""
    output_directory = "TEMPLATE"
    if not os.path.isdir(output_directory):
        print(f"Errore: La cartella '{output_directory}' non è stata trovata.")
        return

    # Creazione di 4 template con codici univoci
    for i in range(1, 5):
        template_code = f"TPL_FRM_{i:03d}"
        create_template(template_code, output_directory)

if __name__ == "__main__":
    main()
