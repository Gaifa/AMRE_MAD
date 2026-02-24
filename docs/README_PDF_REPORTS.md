# Guida alla Generazione dei Report PDF

## Panoramica

Il sistema genera automaticamente report PDF professionali per tutti i motori nel database. Ogni report include:

- Dati generali del motore
- Tabella delle prestazioni per diversi duty cycle
- Grafici coppia/potenza vs velocità

## Tipi di Motore

Il sistema supporta tre tipologie di motore, ognuna con diverse densità di corrente:

### FL - Floor Cleaning (Pulizia Pavimenti)
Motori per macchine lavapavimenti, operazione continua a basse correnti:
- **S1** (continuo): 4.0 A/mm²
- **S2-60min**: 4.5 A/mm²
- **S2-20min**: 5.0 A/mm²
- **S2-5min**: 5.5 A/mm²

### MC - Material Handling / Cart (Carrelli)
Motori per carrelli elevatori e movimentazione, correnti medie/alte:
- **S1** (continuo): 7.0 A/mm²
- **S2-60min**: 7.5 A/mm²
- **S2-20min**: 8.0 A/mm²
- **S2-5min**: 13.0 A/mm²

### MV - Material Handling / Vehicle (Veicoli)
Motori per veicoli industriali, correnti ottimizzate:
- **S1** (continuo): 5.0 A/mm²
- **S2-60min**: 5.5 A/mm²
- **S2-20min**: 7.0 A/mm²
- **S2-5min**: 8.0 A/mm²

## Come Generare i Report

### Metodo 1: Launcher Windows (Più Semplice)
```
Doppio click su: Generate_Reports.bat
```

### Metodo 2: Command Line

**Genera tutti i report:**
```bash
python scripts/generate_performance_reports.py
```

**Solo per un motore specifico:**
```bash
python scripts/generate_performance_reports.py --motor-id 1
```

**Con opzioni personalizzate:**
```bash
python scripts/generate_performance_reports.py ^
    --db percorso/database.db ^
    --config percorso/config.json ^
    --output cartella_output/
```

## Struttura dei Report Generati

### Nome File
I PDF vengono salvati con questo formato:
```
{Tipo}_performance_report_D{diametro}_H{lunghezza}_T{spire}_{connessione}_{voltaggio}V.pdf
```

**Esempio:**
```
MC_performance_report_D135_H120_T45_Star_48V.pdf
```

Dove:
- **MC** = Tipo motore (Material Handling Cart)
- **D135** = Diametro esterno 135mm
- **H120** = Lunghezza assiale 120mm
- **T45** = 45 spire per bobina
- **Star** = Connessione a stella
- **48V** = Tensione batteria 48V

### Cartella Output
```
generated_pdfs/
├── FL_performance_report_D106_H65_T30_Star_24V.pdf
├── FL_performance_report_D106_H65_T30_Star_48V.pdf
├── MC_performance_report_D106_H65_T30_Star_24V.pdf
├── MC_performance_report_D106_H65_T30_Star_48V.pdf
├── MV_performance_report_D106_H65_T30_Star_24V.pdf
└── ... (un PDF per ogni combinazione tipo/motore/voltaggio)
```

## Contenuto del Report PDF

### Pagina 1: Dati e Tabelle

**Header:**
- Logo aziendale
- Titolo con tipo motore e voltaggio
- Codice modello
- Revisione e data

**Dati Generali:**
- Tensione batteria
- Numero poli
- Tipo connessione (Star/Delta)
- Temperature massima e ambiente
- Classe IP

**Prestazioni Nominali:**
Tabella con dati per ogni duty cycle:
- Coppia [Nm]
- Potenza [kW]
- Velocità [rpm]
- Efficienza [%]
- Corrente motore [Arms]
- Tensione motore [Vrms]

### Pagina 2: Grafici Prestazioni

**Grafico Coppia vs Velocità:**
- Linee continue, colori diversi per ogni duty
- Legenda con etichette duty cycle

**Grafico Potenza vs Velocità:**
- Linee tratteggiate, stessi colori della coppia corrispondente
- Stessa legenda

**Formato:**
- Griglia per facilitare la lettura
- Assi etichettati chiaramente
- Alta risoluzione (300 DPI)

## Personalizzazione

### Modifica Configurazione Tipi Motore

Edita il file `motor_types_config.json`:

```json
{
    "motor_types": {
        "NUOVO_TIPO": {
            "description": "Descrizione tipo motore",
            "duties": {
                "S1": {
                    "current_density": 5.0,
                    "duration_min": "continuous"
                },
                "S2-30min": {
                    "current_density": 7.0,
                    "duration_min": 30
                }
            }
        }
    }
}
```

### Modifica Impostazioni PDF

Nel file `motor_types_config.json`, sezione `pdf_settings`:

```json
{
    "pdf_settings": {
        "logo_path": "percorso/al/logo.png",
        "output_directory": "cartella_output",
        "max_temperature": "85°C",
        "ambient_temperature": "40°C",
        "ip_class": "IP65"
    }
}
```

## Requisiti

**Librerie Python necessarie:**
```bash
pip install reportlab matplotlib
```

**File necessari:**
- Database con simulazioni: `mcad_results.db`
- File configurazione: `motor_types_config.json`
- Logo aziendale (opzionale): `AMRE_logo.png`

## Risoluzione Problemi

### "No motors found in database"
- Esegui prima le simulazioni con `run_simulations.py`
- Verifica che il database esista

### "Run not found in database"
- Le densità di corrente nel config devono corrispondere a quelle simulate
- Controlla che le simulazioni includano tutte le correnti necessarie

### "Failed to generate plot"
- Verifica che matplotlib sia installato: `pip install matplotlib`
- Controlla che ci siano dati validi per almeno un duty cycle

### Logo non appare nel PDF
- Verifica che il file logo esista nel percorso specificato
- Formati supportati: PNG, JPG
- Il PDF verrà generato anche senza logo

## Esempio Workflow Completo

1. **Esegui simulazioni:**
   ```bash
   python scripts/run_simulations.py --directory Motori
   ```

2. **Genera report PDF:**
   ```bash
   python scripts/generate_performance_reports.py
   ```
   oppure doppio click su `Generate_Reports.bat`

3. **Trova i PDF:**
   - Apri cartella `generated_pdfs/`
   - I PDF sono organizzati per tipo/motore/voltaggio

4. **Personalizza (opzionale):**
   - Modifica `motor_types_config.json` per nuovi tipi
   - Rigenera i report

## Note Importanti

- **Un PDF per ogni combinazione**: Il sistema genera un PDF separato per ogni combinazione di tipo motore, motore specifico e voltaggio
- **Dati simulati**: I valori riportati sono da simulazione MotorCAD
- **Densità corrente**: Ogni tipo motore ha densità di corrente specifiche per i vari duty cycle
- **Grafici multipli**: Ogni grafico mostra le curve per S2-5min, S2-20min, S2-60min simultaneamente
- **Colori consistenti**: Stessa coppia/potenza hanno lo stesso colore (linea continua vs tratteggiata)

## Supporto

Per domande o problemi, contatta il team MotorCAD Analysis.
