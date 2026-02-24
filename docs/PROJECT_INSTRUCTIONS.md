# PROJECT INSTRUCTIONS - MotorCAD Simulation Framework

> **Questo documento fornisce il contesto completo del progetto per assistenti AI e sviluppatori.**
> Data creazione: 16 Febbraio 2026
> Versione: 1.0.0

---

## 📋 INDICE

1. [Panoramica del Progetto](#panoramica-del-progetto)
2. [Architettura e Struttura](#architettura-e-struttura)
3. [Moduli Principali](#moduli-principali)
4. [Database Schema](#database-schema)
5. [Flusso di Lavoro](#flusso-di-lavoro)
6. [File di Configurazione](#file-di-configurazione)
7. [Script Eseguibili](#script-eseguibili)
8. [Interfacce Utente](#interfacce-utente)
9. [Convenzioni e Best Practices](#convenzioni-e-best-practices)
10. [Estensione del Progetto](#estensione-del-progetto)
11. [Troubleshooting](#troubleshooting)

---

## 📖 PANORAMICA DEL PROGETTO

### Scopo
Framework Python per automatizzare simulazioni elettromagnetiche di motori elettrici usando MotorCAD. Il sistema include:
- **Caching intelligente** per evitare simulazioni duplicate
- **Batch processing** di molteplici motori
- **Database SQLite** per storage organizzato dei risultati
- **GUI desktop e web** per interazione user-friendly
- **Generazione automatica di report PDF professionali**

### Dominio Applicativo
Progettazione e analisi di motori elettrici brushless (BLDC/PMSM) per applicazioni industriali:
- **FL (FrameLess)**: Motori privi di Frame esterno, bassa protezione IP e densità di corrente ridotte
- **MC (MEC)**: Motori con FRAME in alluminio alettato , grado IP65 e densita di corrente medie
- **MV (MEC ventilated)**: Motori con FRAME in alluminio alettato e ventola per aria forzata , grado IP65 e densita di corrente alte

### Tecnologie Principali
- **Python 3.8+** (linguaggio principale)
- **MotorCAD COM Automation** (integrazione con MotorCAD via pywin32)
- **SQLite** (database per risultati)
- **NumPy/SciPy** (calcoli scientifici)
- **Matplotlib** (visualizzazione curve prestazionali)
- **ReportLab** (generazione PDF)
- **Flask** (GUI web alternativa)
- **Tkinter** (GUI desktop)

### Requisiti di Sistema
- **Windows OS** (obbligatorio per COM automation di MotorCAD)
- **MotorCAD** installato e licenziato
- **Python 3.8+** con dipendenze in `requirements.txt`

---

## 🏗️ ARCHITETTURA E STRUTTURA

### Organizzazione Directory

```
MCAD_jack/
│
├── src/                              # Moduli Python core
│   ├── __init__.py                   # Package initialization
│   ├── config.py                     # Configurazione e costanti
│   ├── database.py                   # Gestione database SQLite
│   ├── mcad_interface.py             # Automazione MotorCAD COM
│   ├── motor_analyzer.py             # Orchestrazione analisi motori
│   └── utils.py                      # Funzioni di utilità
│
├── scripts/                          # Script eseguibili
│   ├── run_simulations.py            # CLI per simulazioni batch
│   ├── run_simulations_quality_check.py  # CLI con quality check (NEW!)
│   ├── gui_main.py                   # GUI desktop (tkinter)
│   ├── gui_web.py                    # GUI web (Flask)
│   ├── view_results.py               # Viewer risultati (CLI)
│   └── generate_performance_reports.py  # Generatore report PDF
│
├── Motori/                           # File motori (.mot, .bak)
│   └── [file .mot]                   # File MotorCAD dei motori
│
├── configurazioni/                   # Configurazioni simulazione
│   └── full_simulation_config.json   # Config completa
│
├── generated_pdfs/                   # Output report PDF
│   └── [report PDF generati]
│
├── TEMPLATE/                         # Template per report
│
├── datasheet competitor/             # Datasheet concorrenza
│
├── Newscripts/                       # Script sperimentali
│
├── vario/                            # File vari
│
├── mcad_results.db                   # Database SQLite (auto-generato)
│
├── example_config.json               # Config esempio per simulazioni
├── example_motor_list.txt            # Lista motori esempio
├── motor_types_config.json           # Config tipologie motori e PDF
│
├── requirements.txt                  # Dipendenze Python
│
├── Launch_GUI.bat                    # Launcher GUI desktop (Windows)
├── Launch_GUI_Web.bat                # Launcher GUI web (Windows)
├── Generate_Reports.bat              # Launcher generazione PDF (Windows)
├── Run_With_Quality_Check.bat        # Launcher quality check (NEW!)
│
├── README.md                         # Documentazione principale
├── README_GUI_WEB.md                 # Guida GUI web
├── README_PDF_REPORTS.md             # Guida report PDF
├── CHANGELOG.md                      # Registro modifiche
│
└── testing.ipynb                     # Notebook originale (preservato)
```

### Principi Architetturali

1. **Modularità**: Separazione clara tra logica business (src/), interfacce (scripts/), e dati (Motori/, database)
2. **Separation of Concerns**: Ogni modulo ha una responsabilità specifica
3. **DRY (Don't Repeat Yourself)**: Funzioni riusabili in utils.py
4. **Configuration over Code**: Parametri configurabili via JSON
5. **Caching Intelligente**: Confronto hash per evitare simulazioni duplicate

---

## 🔧 MODULI PRINCIPALI

### 1. `src/config.py` - Configurazione Centrale

**Scopo**: Definisce tutte le costanti e parametri di configurazione del framework.

**Elementi Chiave**:
```python
# Path database
DB_PATH = r"c:\Users\grell\Desktop\MCAD_jack\mcad_results.db"

# Metriche da salvare da MotorCAD
SAVE_KEYS = [
    "Shaft_Torque",                          # Coppia albero [Nm]
    "Speed",                                  # Velocità [rpm]
    "Shaft_Power",                            # Potenza albero [W]
    "Voltage_Phase_RMS",                      # Tensione fase RMS [V]
    "Stator_Current_Line_RMS",                # Corrente linea RMS [A]
    "Power_Factor_From_Power_Balance",        # Fattore di potenza
    "Efficiency",                             # Efficienza [%]
    "Frequency",                              # Frequenza elettrica [Hz]
    "DC_Bus_Voltage"                          # Tensione bus DC [V]
]

# Parametri simulazione di default
DEFAULT_MODEL_DICT = {
    'Maximum speed': 5000,              # Velocità massima [rpm]
    'Minimum speed': 50,                # Velocità minima [rpm]
    'Maximum current density': 15,      # Densità corrente max [A/mm²]
    'Battery voltage': [24, 48, 96],    # Tensioni da testare [V]
    'Current density': [4, 5, 7, 8]     # Densità correnti da testare [A/mm²]
}

SPEED_INCREMENT = 50                    # Incremento velocità [rpm]
MODULATION_INDEX = 0.95                 # Indice modulazione inverter

# Parametri controllo qualità (NEW!)
QUALITY_CHECK_MAX_ITERATIONS = 5       # Numero massimo tentativi
QUALITY_CHECK_INITIAL_SLIP_START = 0.01  # Valore iniziale slip
QUALITY_CHECK_SLIP_INCREMENT = 0.02    # Incremento slip per iterazione
QUALITY_CHECK_MAX_SLIP = 0.20          # Limite massimo slip (safety)
QUALITY_CHECK_SMOOTHNESS_THRESHOLD = 0.15  # Soglia CV per smoothness (15%)
```

**Quando Modificare**:
- Aggiungere nuove metriche da salvare → aggiornare `SAVE_KEYS` e `CANON_KEYS`
- Cambiare parametri di default → modificare `DEFAULT_MODEL_DICT`
- Cambiare path database → aggiornare `DB_PATH`
- Modificare comportamento quality check → aggiornare `QUALITY_CHECK_*` parametri

---

### 2. `src/database.py` - Gestione Database

**Scopo**: Interfaccia completa con database SQLite per storage e retrieval di risultati.

**Schema Database**:

#### Tabella `motors`
```sql
CREATE TABLE motors(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    motor_hash TEXT UNIQUE NOT NULL,      -- SHA256 hash del motor_dict
    motor_json TEXT NOT NULL,              -- Configurazione motore (JSON)
    created_at TEXT NOT NULL               -- Timestamp creazione
)
```

#### Tabella `runs`
```sql
CREATE TABLE runs(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    motor_id INTEGER NOT NULL,             -- FK a motors.id
    voltage REAL NOT NULL,                 -- Tensione batteria [V]
    current_density REAL NOT NULL,         -- Densità corrente [A/mm²]
    Shaft_Torque BLOB,                     -- Array numpy serializzato
    Speed BLOB,                            -- Array numpy serializzato
    Shaft_Power BLOB,                      -- Array numpy serializzato
    Voltage_Phase_RMS BLOB,                -- Array numpy serializzato
    Stator_Current_Line_RMS BLOB,          -- Array numpy serializzato
    Power_Factor_From_Power_Balance BLOB,  -- Array numpy serializzato
    Efficiency BLOB,                       -- Array numpy serializzato
    Frequency BLOB,                        -- Array numpy serializzato
    DC_Bus_Voltage BLOB,                   -- Array numpy serializzato
    created_at TEXT NOT NULL,              -- Timestamp simulazione
    FOREIGN KEY(motor_id) REFERENCES motors(id),
    UNIQUE(motor_id, voltage, current_density)  -- Un solo run per combinazione
)
```

**Funzioni Principali**:

```python
# Inizializzazione
init_db(db_path)                    # Crea database e tabelle

# Identificazione motori
motor_hash(motor_dict)              # SHA256 hash per identificazione unica
motor_exists(motor_hash, db_path)   # Verifica esistenza in DB
get_motor_id(motor_hash, db_path)   # Ottieni ID da hash
insert_motor(motor_dict, db_path)   # Inserisci nuovo motore

# Gestione runs
run_exists(motor_id, voltage, current_density, db_path)  # Verifica run esistente
insert_run(motor_id, voltage, current_density, data, db_path)  # Inserisci run
get_run(motor_id, voltage, current_density, db_path)  # Recupera run specifico
get_runs_for_motor(motor_id, db_path)  # Tutti i run di un motore

# Query e listing
list_all_motors(db_path)            # Lista tutti i motori in DB
search_motors_by_param(param, value, db_path)  # Ricerca per parametro

# Serializzazione array
_serialize_array(arr)               # Numpy array → BLOB
_deserialize_array(blob)            # BLOB → Numpy array
```

**Note Importanti**:
- **Hash per Deduplicazione**: Il motor_hash identifica univocamente un motore basandosi sui suoi parametri geometrici ed elettrici
- **Array come BLOB**: Le curve prestazionali sono array numpy serializzati e compressi
- **Unique Constraint**: Un solo run per ogni combinazione (motor_id, voltage, current_density)

---

### 3. `src/mcad_interface.py` - Interfaccia MotorCAD

**Scopo**: Gestisce tutte le interazioni con l'API COM di MotorCAD.

**Funzioni Principali**:

```python
# Connessione
initialize_mcad(suppress_messages=True)  # Inizializza connessione COM
close_mcad(mcad)                         # Chiude connessione

# Caricamento file
load_motor_file(mcad, mot_file_path)     # Carica file .mot

# Estrazione parametri
get_mcad_variables(mcad, var_names)      # Legge variabili da MotorCAD
_compute_equivalent_csa(motor_params)    # Calcola sezione equivalente conduttori

# Costruzione e validazione modello
check_and_build_model(mcad, motor_dict, voltage, current_density, 
                      speed_min, speed_max, speed_inc, mod_index)
# Verifica parametri e costruisce modello per simulazione

# Esecuzione simulazioni
run_mcad_simulation(mcad, voltage, current_density, motor_dict, 
                    model_dict, initial_slip=0.01)
# Esegue simulazione elettromagnetica con parametro initial_slip configurabile

# Caricamento risultati
load_simulation_results(mot_file_path)   # Legge file .mat risultati

# Funzioni combinate
run_and_load(mcad, voltage, current_density, motor_dict, model_dict,
             mot_file_path, initial_slip=0.01)
# Esegue simulazione + carica risultati in un'unica chiamata

# Controllo qualità (NEW!)
check_results_smoothness(results, smoothness_threshold=0.15)
# Verifica la smoothness delle curve di coppia e potenza
# Return: (is_smooth: bool, metrics: dict)

run_and_load_with_quality_check(mcad, voltage, current_density, 
                                motor_dict, model_dict, mot_file_path,
                                max_iterations=None, initial_slip_start=None,
                                slip_increment=None, smoothness_threshold=None)
# Esegue simulazione con controllo qualità automatico e aggiustamento iterativo
# di IM_InitialSlip_MotorLAB fino a ottenere risultati smooth
# Return: results dict o None se fallisce
```

**Controllo Qualità Risultati (Nuova Funzionalità)**:

Il framework include ora un sistema di controllo qualità che valida automaticamente la smoothness dei risultati:

```python
# Metrica di Smoothness: Coefficient of Variation (CV)
CV = std(diff(values)) / mean(abs(values))

# Dove:
# - diff(values) = differenze tra punti consecutivi
# - Valori bassi di CV indicano curve smooth
# - Valori alti indicano oscillazioni/irregolarità

# Workflow Iterativo:
1. Esegui simulazione con initial_slip corrente
2. Calcola CV per coppia e potenza
3. Se CV < soglia → successo, return risultati
4. Se CV >= soglia → incrementa initial_slip e riprova
5. Ripeti fino a max_iterations o CV accettabile
```

**Parametri Configurabili**:
```python
# In src/config.py
QUALITY_CHECK_MAX_ITERATIONS = 5           # Tentativi massimi
QUALITY_CHECK_INITIAL_SLIP_START = 0.01    # Valore iniziale slip
QUALITY_CHECK_SLIP_INCREMENT = 0.02        # Incremento per iterazione
QUALITY_CHECK_MAX_SLIP = 0.20              # Limite massimo slip
QUALITY_CHECK_SMOOTHNESS_THRESHOLD = 0.15  # Soglia CV (15%)
```

**Quando Usare Quality Check**:
- **Sì**: Motori nuovi, geometrie complesse, report professionali
- **No**: Batch processing rapidi, motori già validati
- **Trade-off**: Migliore qualità vs ~2-5x tempo simulazione

**Parametri Motore Estratti**:
```python
MOTOR_PARAM_MAPPING = {
    'Stator_Lam_Dia': 'Diametro esterno statore',      # [mm]
    'Stator_Lam_Length': 'Lunghezza statore',          # [mm]
    'Number_turns_coil': 'Numero spire per bobina',    # [-]
    'MagWindingLayers': 'Numero strati avvolgimento',  # [-]
    'MagPathsInParallel': 'Percorsi in parallelo',     # [-]
    'MagTurnsConductor': 'Conduttori per spira',       # [-]
    'MagSlotConductorArea': 'Area conduttore cava',    # [mm²]
    'Slot_Number': 'Numero cave',                      # [-]
    'Magnet_Pole_Number': 'Numero poli magnete',       # [-]
    'DC_Bus_Voltage': 'Tensione bus DC',               # [V]
    'Connection': 'Tipo connessione (Star/Delta)'      # [-]
}
```

**Note Tecniche**:
- Usa `win32com.client.Dispatch("MotorCAD.AppAutomation")` per connessione COM
- I risultati sono salvati come file `.mat` (formato Matlab) nella stessa directory del `.mot`
- `MessageDisplayState = 2` sopprime dialogs MotorCAD per automazione

---

### 4. `src/motor_analyzer.py` - Orchestrazione Analisi

**Scopo**: Coordina il workflow completo di analisi motori, implementando caching intelligente.

**Funzioni Principali**:

```python
analyze_motor(mcad, mot_file_path, model_dict, db_path)
# Analizza singolo motore con caching intelligente
# Return: dict con motor_hash, motor_dict, results, skipped_voltages, success

analyze_motor_batch(mot_file_paths, model_dict, db_path, parallel=False)
# Elabora batch di motori in sequenza
# Return: list di analysis_result per ogni motore

find_mot_files(directory, recursive=False)
# Cerca file .mot in directory
# Return: list di path assoluti
```

**Algoritmo di Caching Intelligente**:

```python
Per ogni motore:
    1. Carica file .mot ed estrai parametri
    2. Calcola motor_hash
    3. Controlla se motore esiste in DB
    
    4. Per ogni voltaggio:
        a. Prendi PRIMA densità corrente dalla lista
        b. Esegui simulazione per (voltaggio, prima_corrente)
        c. Confronta risultati con DB (se esiste run per questo voltaggio)
        
        d. Se match trovato:
            → SKIP tutte le altre densità correnti per questo voltaggio
            → Segna voltaggio come "cached"
        
        e. Se NO match o NO DB entry:
            → Esegui sweep completo di tutte le densità correnti
            → Salva tutti i risultati nel DB
    
    5. Return: risultati + lista voltages skipped
```

**Criterio di Match**:
```python
# Due run sono considerati uguali se:
- Tutti gli array hanno stessa length
- Tutti i valori corrispondenti rispettano:
  |a - b| <= (atol + rtol * |b|)
  
  dove:
    atol = 1e-8  (absolute tolerance)
    rtol = 1e-5  (relative tolerance, 0.001%)
```

**Vantaggi del Caching**:
- Evita ri-simulazioni costose (ogni simulazione ~1-3 minuti)
- Permette aggiunta incrementale di voltages/correnti
- Mantiene consistenza: stesso motore → stesso hash

---

### 5. `src/utils.py` - Utilità Generali

**Scopo**: Funzioni di supporto per processing dati e validazione.

**Funzioni Principali**:

```python
# Gestione chiavi dati
try_keys(data_dict, *key_variants)
# Cerca chiavi con varianti (case-insensitive, spazi, underscores)

build_canon_dict_from_mat(mat_data)
# Costruisce dict canonico da file .mat MotorCAD

# Normalizzazione array
normalise_array(arr)
# Converte a numpy array 1D

# Confronto array
arrays_equal(a, b, rtol=1e-5, atol=1e-8)
# Confronta array numpy con tolleranze

# Validazione
validate_motor_dict(motor_dict)
# Verifica presenza campi obbligatori in motor_dict

validate_model_dict(model_dict)
# Verifica validità parametri simulazione

# Debugging
summarize_array(arr, name="Array")
# Restituisce stringa riassuntiva di array (min, max, mean, length)
```

**Gestione Variazioni Naming**:
```python
# MotorCAD può usare naming variants:
"Shaft_Torque"  →  ["Shaft Torque", "shaft_torque", "ShaftTorque"]

# try_keys gestisce automaticamente queste variazioni
```

---

## 💾 DATABASE SCHEMA

### Concetti Chiave

1. **Motor Hash**: SHA256 del motor_dict serializzato → identificazione univoca
2. **Motor Dict**: JSON con parametri geometrici ed elettrici del motore
3. **Run**: Una simulazione per specifica combinazione (motore, voltaggio, densità corrente)
4. **Performance Curves**: Array numpy di ~100 punti (velocità da min a max con increment)

### Relazioni

```
motors (1) ←→ (N) runs
    |
    └─ Un motore può avere molti run
    └─ Ogni run è per una specifica (voltage, current_density)
    └─ UNIQUE constraint previene duplicati
```

### Esempi Query Utili

```sql
-- Lista motori con numero run
SELECT m.id, m.motor_json, COUNT(r.id) as num_runs
FROM motors m
LEFT JOIN runs r ON m.id = r.motor_id
GROUP BY m.id;

-- Trova run per diametro specifico
SELECT m.motor_json, r.voltage, r.current_density
FROM motors m
JOIN runs r ON m.id = r.motor_id
WHERE m.motor_json LIKE '%"Stator_Lam_Dia": 135%';

-- Esporta curve per motore/voltage/current
SELECT Speed, Shaft_Torque, Efficiency
FROM runs
WHERE motor_id = ? AND voltage = ? AND current_density = ?;
```

---

## 🔄 FLUSSO DI LAVORO

### Workflow Tipico: Simulazione Batch

```
1. PREPARAZIONE
   ├─ Utente prepara file .mot in cartella Motori/
   ├─ (Opzionale) Crea config.json personalizzato
   └─ (Opzionale) Crea lista motori in .txt

2. AVVIO SIMULAZIONE
   ├─ CLI: python scripts/run_simulations.py --directory Motori/
   ├─ GUI Desktop: Launch_GUI.bat → Tab "Run Simulations"
   └─ GUI Web: Launch_GUI_Web.bat → Tab "Run Simulations"

3. PROCESSING (per ogni motore)
   ├─ Inizializza connessione MotorCAD
   ├─ Carica file .mot
   ├─ Estrae parametri motore → motor_dict
   ├─ Calcola motor_hash
   ├─ Controlla DB per esistenza motore
   │
   ├─ Per ogni voltaggio:
   │   ├─ Esegui prima simulazione (prima densità corrente)
   │   ├─ Confronta con DB
   │   ├─ Se match → SKIP resto densità per questo voltaggio
   │   └─ Se NO match → Esegui sweep completo + salva in DB
   │
   └─ Chiude connessione MotorCAD

4. VISUALIZZAZIONE RISULTATI
   ├─ CLI: python scripts/view_results.py --list-motors
   ├─ GUI Desktop: Tab "View Results"
   └─ GUI Web: Tab "View Results" (auto-refresh)

5. PLOTTING
   ├─ CLI: python scripts/view_results.py --motor-id 1 --voltage 48 --current-density 7 --plot
   ├─ GUI Desktop: Tab "Plot Results" → Inserisci parametri → "Generate Plot"
   └─ GUI Web: Tab "Plot Results" → Form → "Generate Plot"

6. GENERAZIONE REPORT PDF
   ├─ Doppio click: Generate_Reports.bat
   └─ CLI: python scripts/generate_performance_reports.py
   │
   ├─ Legge motor_types_config.json
   ├─ Per ogni motore nel DB:
   │   └─ Per ogni tipo motore (FL, MC, MV):
   │       └─ Genera PDF con tabelle e grafici prestazionali
   │
   └─ Output: generated_pdfs/[tipo]_performance_report_[params].pdf
```

### Diagramma Flusso Dati

```
File .mot (MotorCAD)
    ↓
mcad_interface.py (estrazione parametri)
    ↓
motor_dict (dict Python con parametri)
    ↓
motor_hash (SHA256)
    ↓
database.py (check esistenza)
    ↓
    ├─ Esiste → Confronta prima simulazione
    │   ├─ Match → Skip
    │   └─ Diverso → Simula + Salva
    │
    └─ Non esiste → Simula + Salva
        ↓
    File .mat (risultati MotorCAD)
        ↓
    utils.py (normalizzazione array)
        ↓
    database.py (serializzazione + storage)
        ↓
    SQLite Database (mcad_results.db)
        ↓
        ├─ View/Query (scripts/view_results.py)
        ├─ Plotting (matplotlib)
        └─ PDF Reports (scripts/generate_performance_reports.py)
```

---

## ⚙️ FILE DI CONFIGURAZIONE

### 1. `example_config.json` - Configurazione Simulazione

**Uso**: Overriding dei parametri di default per simulazioni custom.

```json
{
  "Maximum speed": 6000,           // Velocità massima sweep [rpm]
  "Minimum speed": 100,             // Velocità minima sweep [rpm]
  "Maximum current density": 20,    // Limite densità corrente [A/mm²]
  
  "Battery voltage": [24, 48, 96],  // Lista tensioni da testare [V]
  
  "Current density": [              // Lista densità correnti [A/mm²]
    4, 6, 8, 10, 12
  ]
}
```

**Utilizzo**:
```bash
python scripts/run_simulations.py --motor Motori/motor.mot --config example_config.json
```

---

### 2. `motor_types_config.json` - Tipologie Motori e PDF

**Uso**: Definisce tipologie motori e parametri per generazione report PDF.

```json
{
    "motor_types": {
        "FL": {                              // FrameLess - Lavapavimenti
            "description": "FrameLess Motors",
            "duties": {
                "S1": {                       // Continuo
                    "current_density": 4.0,
                    "duration_min": "continuous"
                },
                "S2-60min": {                 // 60 minuti
                    "current_density": 4.5,
                    "duration_min": 60
                },
                "S2-20min": {                 // 20 minuti
                    "current_density": 5.0,
                    "duration_min": 20
                },
                "S2-5min": {                  // 5 minuti
                    "current_density": 5.5,
                    "duration_min": 5
                }
            }
        },
        "MC": {                              // Material Handling Cart - Carrelli
            "description": "MEC motors",
            "duties": {
                "S1": {"current_density": 7.0, "duration_min": "continuous"},
                "S2-60min": {"current_density": 7.5, "duration_min": 60},
                "S2-20min": {"current_density": 8.0, "duration_min": 20},
                "S2-5min": {"current_density": 13.0, "duration_min": 5}
            }
        },
        "MV": {                              // Material Handling Vehicle - Veicoli
            "description": "MEC Ventilated Motors",
            "duties": {
                "S1": {"current_density": 5.0, "duration_min": "continuous"},
                "S2-60min": {"current_density": 5.5, "duration_min": 60},
                "S2-20min": {"current_density": 7.0, "duration_min": 20},
                "S2-5min": {"current_density": 8.0, "duration_min": 5}
            }
        }
    },
    "pdf_settings": {
        "logo_path": "AMRE_logo.png",
        "output_directory": "generated_pdfs",
        "max_temperature": "80°C",
        "ambient_temperature": "40°C",
        "ip_class": "IP54"
    }
}
```

**Note**:
- **S1, S2-Xmin**: Duty cycle secondo IEC 60034-1
- **current_density**: Densità corrente nominale per quel duty cycle [A/mm²]
- Ogni motore viene simulato per tutte e 3 le tipologie (FL, MC, MV)

---

### 3. `example_motor_list.txt` - Lista Motori per Batch

**Formato**: Un path per riga (assoluto o relativo)

```
Motori/D106 H65 25sp DT ( 2x0.63 + 2x0.5 ).mot
Motori/D135 H100 12sp DT ( 2x0.9 + 2x0.8 ).mot
Motori/D150 H120 12sp DT ( 4x0.9 ).mot
```

**Utilizzo**:
```bash
python scripts/run_simulations.py --list example_motor_list.txt
```

---

## 🖥️ SCRIPT ESEGUIBILI

### 1. `scripts/run_simulations.py` - CLI Simulazioni

**Funzione**: Interfaccia command-line per eseguire simulazioni batch.

**Utilizzo**:

```bash
# Singolo motore
python scripts/run_simulations.py --motor "Motori/D135 H100 12sp DT.mot"

# Directory (non ricorsiva)
python scripts/run_simulations.py --directory "Motori"

# Directory ricorsiva
python scripts/run_simulations.py --directory "Motori" --recursive

# Da file lista
python scripts/run_simulations.py --list "motors_to_simulate.txt"

# Con config personalizzata
python scripts/run_simulations.py --directory "Motori" --config "myconfig.json"

# Con database custom
python scripts/run_simulations.py --directory "Motori" --db "custom_results.db"

# Help
python scripts/run_simulations.py --help
```

**Argomenti**:
```
--motor PATH          Path a singolo file .mot
--directory PATH      Path a directory con file .mot
--recursive           Cerca .mot ricorsivamente nelle sottocartelle
--list PATH           Path a file .txt con lista motori
--config PATH         Config JSON personalizzato
--db PATH             Path database custom (default: mcad_results.db)
```

**Output Console**:
```
================================================================================
ANALYZING MOTOR: D135 H100 12sp DT ( 2x0.9 + 2x0.8 ).mot
================================================================================
Loading motor file: D135 H100 12sp DT ( 2x0.9 + 2x0.8 ).mot
Extracting motor parameters...
Motor hash: a3f582b9c1...
Motor found in database. ID=12

Testing voltage: 24V
  Running simulation: 24V, 4.0 A/mm²...
  Comparing with database...
  ✓ Match found! Skipping remaining current densities for 24V.

Testing voltage: 48V
  Running simulation: 48V, 4.0 A/mm²...
  No existing run found in database.
  Running full sweep for 48V:
    - 4.0 A/mm²... Done.
    - 4.5 A/mm²... Done.
    - 5.0 A/mm²... Done.
  Saved 3 runs to database.

SUMMARY:
- Motor: D135 H100 12sp DT ( 2x0.9 + 2x0.8 ).mot
- Cached voltages: [24V]
- New simulations: 3 runs (48V)
- Total time: 4.5 minutes
================================================================================
```

---

### 1b. `scripts/run_simulations_quality_check.py` - CLI con Quality Check (NEW!)

**Funzione**: Interfaccia command-line per simulazioni con controllo qualità automatico.

**Utilizzo**:

```bash
# Singolo motore con quality check
python scripts/run_simulations_quality_check.py --motor "Motori/D135 H100 12sp DT.mot"

# Directory con quality check
python scripts/run_simulations_quality_check.py --directory "Motori" --recursive

# Da file lista con quality check
python scripts/run_simulations_quality_check.py --list "motors_to_simulate.txt"

# Con parametri personalizzati
python scripts/run_simulations_quality_check.py --motor "motor.mot" \
    --max-iterations 10 \
    --initial-slip 0.02 \
    --slip-increment 0.03 \
    --smoothness-threshold 0.10

# Launcher Windows
Run_With_Quality_Check.bat
```

**Argomenti Addizionali**:
```
--max-iterations N         Numero massimo iterazioni per smooth results
--initial-slip VALUE       Valore iniziale per IM_InitialSlip_MotorLAB
--slip-increment VALUE     Incremento slip per ogni iterazione
--smoothness-threshold N   Soglia CV per validare smoothness (0.0-1.0)
```

**Output Console con Quality Check**:
```
======================================================================
Starting simulation with quality checking
  Voltage: 48V, Current Density: 7 A/mm²
  Initial Slip Range: 0.01 to 0.20
  Smoothness Threshold: 0.15
======================================================================

--- Iteration 1/5 ---
Trying IM_InitialSlip_MotorLAB = 0.0100
Running MotorCAD simulation...
✗ Results not smooth: Torque CV=0.2341, Power CV=0.1876 (threshold=0.15)

--- Iteration 2/5 ---
Trying IM_InitialSlip_MotorLAB = 0.0300
Running MotorCAD simulation...
✓ Results are smooth: Torque CV=0.0892, Power CV=0.1124

======================================================================
✓ SUCCESS: Smooth results obtained after 2 iteration(s)
  Final IM_InitialSlip_MotorLAB: 0.0300
  Torque CV: 0.0892
  Power CV: 0.1124
======================================================================

✓ Results saved to database.
```

**Quando Usare**:
- **Quality Check Mode**: Nuovi motori, geometrie complesse, report professionali
- **Standard Mode**: Batch rapidi, motori validati, sweep parametrici veloci
- **Trade-off**: +qualità vs ~2-5x tempo

---

### 2. `scripts/view_results.py` - Viewer Risultati CLI

**Funzione**: Interroga database e visualizza risultati da command-line.

**Utilizzo**:

```bash
# Lista tutti i motori
python scripts/view_results.py --list-motors

# Info motore specifico
python scripts/view_results.py --motor-id 12

# Lista run per motore
python scripts/view_results.py --motor-id 12 --list-runs

# Visualizza run specifico
python scripts/view_results.py --motor-id 12 --voltage 48 --current-density 7

# Plot curve prestazionali
python scripts/view_results.py --motor-id 12 --voltage 48 --current-density 7 --plot

# Esporta dati in CSV
python scripts/view_results.py --motor-id 12 --voltage 48 --current-density 7 --export output.csv

# Database custom
python scripts/view_results.py --db "custom_results.db" --list-motors
```

**Argomenti**:
```
--db PATH                 Path database (default: mcad_results.db)
--list-motors             Lista tutti i motori in DB
--motor-id ID             ID motore da ispezionare
--list-runs               Lista tutti i run per motor-id
--voltage V               Filtra per tensione specifica
--current-density CD      Filtra per densità corrente specifica
--plot                    Mostra grafici matplotlib
--export PATH             Esporta dati in CSV
```

---

### 3. `scripts/generate_performance_reports.py` - Generatore PDF

**Funzione**: Genera report PDF professionali per tutti i motori nel database.

**Utilizzo**:

```bash
# Genera tutti i report
python scripts/generate_performance_reports.py

# Solo per un motore
python scripts/generate_performance_reports.py --motor-id 5

# Con configurazioni custom
python scripts/generate_performance_reports.py --config custom_motor_types.json

# Output directory custom
python scripts/generate_performance_reports.py --output reports_output/

# Database custom
python scripts/generate_performance_reports.py --db custom_results.db
```

**Argomenti**:
```
--db PATH              Path database (default: mcad_results.db)
--config PATH          Config tipologie motori (default: motor_types_config.json)
--output PATH          Directory output PDF (default: generated_pdfs/)
--motor-id ID          Genera solo per questo motore
```

**Struttura Report PDF**:

```
Pagina 1:
┌─────────────────────────────────────────────────────────┐
│ [Logo]              MOTOR PERFORMANCE REPORT             │
├─────────────────────────────────────────────────────────┤
│ Motor Type: MC (Material Handling Cart)                 │
│ Geometry: D=135mm, H=120mm                              │
│ Winding: 45 turns, Star connection                      │
│ Voltage: 48V DC                                          │
├─────────────────────────────────────────────────────────┤
│ PERFORMANCE TABLE                                        │
│                                                          │
│ Duty    Current   Torque   Power   Efficiency   Speed   │
│ S1      7.0 A/mm² 12.3 Nm  3.2 kW  91.2%       2500 rpm│
│ S2-60   7.5 A/mm² 13.1 Nm  3.4 kW  90.8%       2450 rpm│
│ S2-20   8.0 A/mm² 13.9 Nm  3.6 kW  90.3%       2400 rpm│
│ S2-5    13.0 A/mm²21.5 Nm  5.5 kW  87.5%       2200 rpm│
└─────────────────────────────────────────────────────────┘

Pagina 2:
┌─────────────────────────────────────────────────────────┐
│ PERFORMANCE CURVES                                       │
│                                                          │
│ [Grafico Coppia vs Velocità]                           │
│ [Grafico Potenza vs Velocità]                          │
└─────────────────────────────────────────────────────────┘
```

**Naming Convention PDF**:
```
{TIPO}_performance_report_D{diam}_H{length}_T{turns}_{conn}_{volt}V.pdf

Esempio:
MC_performance_report_D135_H120_T45_Star_48V.pdf
```

---

## 🖼️ INTERFACCE UTENTE

### 1. GUI Desktop (Tkinter) - `scripts/gui_main.py`

**Avvio**:
```bash
# Windows batch
Launch_GUI.bat

# Command line
python scripts/gui_main.py
```

**Tab Disponibili**:

1. **Run Simulations**
   - Selezione directory/lista motori
   - Caricamento config JSON
   - Pulsante "Start Simulations"
   - Progress bar e log output

2. **View Results**
   - Lista motori nel DB (con ID, Diametro, Lunghezza, Spire, Connessione)
   - Selezione motore → visualizza lista run (Voltage, Current Density)
   - Pulsante "Refresh" per aggiornare

3. **Plot Results**
   - Form: Motor ID, Voltage, Current Density
   - Scelta tipo plot:
     - Torque vs Speed
     - Power vs Speed
     - Efficiency vs Speed
     - All Curves
   - Pulsante "Generate Plot" → apre matplotlib

4. **About**
   - Informazioni applicazione
   - Versione
   - Guide rapide

**Pro**:
- Nativa Windows
- Veloce e responsive
- Integrazione matplotlib diretta

**Contro**:
- Richiede tkinter (non sempre disponibile in Python di sistema)

---

### 2. GUI Web (Flask) - `scripts/gui_web.py`

**Avvio**:
```bash
# Windows batch
Launch_GUI_Web.bat

# Command line
python scripts/gui_web.py
```

**URL**: http://localhost:5000 (si apre automaticamente nel browser)

**Pagine Disponibili**:

1. **Run Simulations**
   - Form per visualizzare/modificare configurazione
   - Pulsanti Save/Load config JSON
   - Istruzioni per usare CLI (la GUI web non esegue simulazioni direttamente)

2. **View Results**
   - Tabella HTML con tutti i motori nel DB
   - Colonne: ID, Diametro, Lunghezza, Spire, Connessione, Num Runs
   - Click su motore → mostra dettagli run
   - Pulsante "Refresh" (AJAX)

3. **Plot Results**
   - Form: Motor ID, Voltage, Current Density, Plot Type
   - Pulsante "Generate Plot"
   - Plot generato come immagine PNG embedded

4. **About**
   - Informazioni applicazione
   - Guide e links a README

**Pro**:
- Non richiede tkinter
- Accessibile da qualsiasi browser
- Design responsive e moderno
- Può essere esposto in rete locale

**Contro**:
- Simulazioni devono essere eseguite da CLI (non integrato)
- Server Flask deve rimanere attivo

---

## 📐 CONVENZIONI E BEST PRACTICES

### Naming Conventions

**File Motori**:
```
Format: D{diam} H{length} {turns}sp {conn} ( {winding_info} ).mot

Esempi:
D135 H120 45sp DT ( 1x0.6+1x0.63 ).mot
D106 H65 25sp DS ( 2x0.63 + 2x0.5 ).mot

Dove:
- D{diam}: Diametro esterno statore [mm]
- H{length}: Lunghezza assiale [mm]
- {turns}sp: Numero spire per bobina
- {conn}: DT=Delta, DS=Star
- {winding_info}: Configurazione avvolgimento (opzionale)
```

**Variabili Python**:
```python
# Costanti: UPPER_SNAKE_CASE
DB_PATH = "..."
MAX_SPEED = 5000

# Variabili/funzioni: lower_snake_case
motor_dict = {...}
def analyze_motor():

# Classi: PascalCase (se implementate in futuro)
class MotorAnalyzer:

# Privato/Interno: _prefisso_underscore
def _compute_hash():
```

**Database**:
```sql
-- Tabelle: lowercase, plurale
motors, runs

-- Colonne: lowercase_snake_case per metadati
motor_id, created_at, current_density

-- Colonne: CamelCase per dati MotorCAD (match con SAVE_KEYS)
Shaft_Torque, Speed, Efficiency
```

---

### Code Style

**Docstrings**: Google Style

```python
def function_name(param1: type, param2: type) -> return_type:
    """
    Brief description of function.
    
    Extended description if needed. Can span multiple lines
    and include implementation details.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ExceptionType: When this exception is raised
        
    Example:
        >>> function_name(val1, val2)
        expected_output
    """
    pass
```

**Type Hints**: Usare sempre quando possibile

```python
from typing import Dict, List, Optional, Any, Tuple

def process_motor(motor_dict: Dict[str, Any], 
                 voltages: List[float]) -> Optional[Dict[str, Any]]:
    ...
```

**Error Handling**: Graceful degradation

```python
try:
    risky_operation()
except SpecificException as e:
    print(f'ERROR: Descriptive message: {e}')
    # Fallback o return None invece di crash
    return None
```

---

### Testing Considerations

**Attualmente**: Nessun test automatico implementato.

**Se implementare test**:

```python
# tests/test_database.py
import pytest
from src import database

def test_motor_hash_deterministic():
    motor_dict = {'Stator_Lam_Dia': 135, 'Stator_Lam_Length': 120}
    hash1 = database.motor_hash(motor_dict)
    hash2 = database.motor_hash(motor_dict)
    assert hash1 == hash2

def test_array_serialization_roundtrip():
    import numpy as np
    arr = np.array([1.0, 2.0, 3.0])
    blob = database._serialize_array(arr)
    arr_restored = database._deserialize_array(blob)
    assert np.array_equal(arr, arr_restored)
```

**Framework testuale suggerito**: pytest

```bash
pip install pytest
pytest tests/
```

---

### Git Workflow (se applicato)

```bash
# Branch per nuove feature
git checkout -b feature/pdf-reports

# Commit incrementali con messaggi descrittivi
git commit -m "Add: PDF report generation with ReportLab"
git commit -m "Fix: Handle missing logo file gracefully"
git commit -m "Docs: Update README with PDF generation instructions"

# Merge su main/master
git checkout main
git merge feature/pdf-reports
```

**Commit Message Convention**:
```
Type: Brief description

Types:
- Add: Nuova funzionalità
- Fix: Bug fix
- Refactor: Ristrutturazione codice senza cambio behavior
- Docs: Aggiornamenti documentazione
- Style: Formatting, whitespace (no logic change)
- Test: Aggiunta/modifica test
- Perf: Miglioramenti performance
```

---

## 🔧 ESTENSIONE DEL PROGETTO

### Aggiungere Nuova Metrica da Salvare

**1. Aggiorna `src/config.py`**:

```python
SAVE_KEYS = [
    "Shaft_Torque",
    "Speed",
    # ... existing keys ...
    "New_Metric_Name"  # <-- AGGIUNGI QUI
]

CANON_KEYS = [
    "shaft_torque",
    "speed",
    # ... existing keys ...
    "new_metric_name"  # <-- AGGIUNGI QUI (lowercase + underscores)
]
```

**2. Database auto-aggiorna**:
- `init_db()` creerà automaticamente colonna `New_Metric_Name BLOB` nella tabella `runs`
- Se database già esiste, fare migration manuale:

```sql
ALTER TABLE runs ADD COLUMN New_Metric_Name BLOB;
```

**3. MotorCAD deve salvare questa metrica**:
- Verifica che MotorCAD output `.mat` contenga questo campo
- Se nome diverso, aggiungere variante in `utils.try_keys()`

---

### Aggiungere Nuovo Tipo Motore

**1. Aggiorna `motor_types_config.json`**:

```json
{
    "motor_types": {
        "FL": { ... },
        "MC": { ... },
        "MV": { ... },
        "NEW_TYPE": {
            "description": "New Motor Type Description",
            "duties": {
                "S1": {
                    "current_density": X.X,
                    "duration_min": "continuous"
                },
                "S2-60min": {
                    "current_density": Y.Y,
                    "duration_min": 60
                }
                // ... altri duty cycle ...
            }
        }
    }
}
```

**2. Nessun cambio codice necessario**:
- `generate_performance_reports.py` itera automaticamente su tutti i `motor_types` nel JSON

---

### Aggiungere Nuovo Script/Comando

**Esempio**: Script per esportare tutti i motori in Excel

**1. Crea `scripts/export_to_excel.py`**:

```python
"""
Export all motors and runs from database to Excel file.
"""

import sqlite3
import pandas as pd
from src import config, database

def export_to_excel(db_path: str = config.DB_PATH, 
                    output_path: str = "motors_export.xlsx"):
    """
    Export motors and runs to Excel with multiple sheets.
    """
    con = sqlite3.connect(db_path)
    
    # Sheet 1: Motors
    motors_df = pd.read_sql_query("SELECT * FROM motors", con)
    
    # Sheet 2: Runs (without BLOB columns)
    runs_df = pd.read_sql_query(
        "SELECT id, motor_id, voltage, current_density, created_at FROM runs", 
        con
    )
    
    con.close()
    
    # Write to Excel
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        motors_df.to_excel(writer, sheet_name='Motors', index=False)
        runs_df.to_excel(writer, sheet_name='Runs', index=False)
    
    print(f"Exported to: {output_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Export database to Excel")
    parser.add_argument('--db', default=config.DB_PATH, help="Database path")
    parser.add_argument('--output', default="motors_export.xlsx", help="Output file")
    args = parser.parse_args()
    
    export_to_excel(args.db, args.output)
```

**2. Documentazione**:

Aggiungere sezione in README:

```markdown
### Export to Excel

```bash
python scripts/export_to_excel.py --output my_export.xlsx
```
```

---

### Aggiungere Nuovo Launcher .bat

**Esempio**: Launcher per export Excel

**Crea `Export_Excel.bat`**:

```batch
@echo off
echo ========================================
echo  Excel Export Tool
echo ========================================
echo.

cd /d "%~dp0"

python scripts/export_to_excel.py --output "motors_export_%date:~-4%%date:~3,2%%date:~0,2%.xlsx"

echo.
echo Export completed!
pause
```

---

### Parallelizzazione Simulazioni

**Attualmente**: Simulazioni sono sequenziali.

**Per parallelizzare** (attenzione: richiede multiple licenze MotorCAD):

```python
# src/motor_analyzer.py

from multiprocessing import Pool

def analyze_motor_batch_parallel(mot_file_paths: List[str], 
                                 model_dict: Dict[str, Any],
                                 db_path: str = config.DB_PATH,
                                 num_workers: int = 4) -> List[Dict]:
    """
    Analyze multiple motors in parallel using multiprocessing.
    
    WARNING: Requires multiple MotorCAD licenses (one per worker).
    """
    
    def worker(mot_file_path):
        # Each worker needs its own MotorCAD instance
        mcad = mcad_interface.initialize_mcad()
        result = analyze_motor(mcad, mot_file_path, model_dict, db_path)
        mcad_interface.close_mcad(mcad)
        return result
    
    with Pool(processes=num_workers) as pool:
        results = pool.map(worker, mot_file_paths)
    
    return results
```

**Considerazioni**:
- Ogni worker MotorCAD richiede licenza separata
- Database locking: SQLite gestisce automaticamente con timeout
- Potenziale speedup: Nx (se N licenze disponibili)

---

## 🐛 TROUBLESHOOTING

### Problema: "ModuleNotFoundError: No module named 'win32com'"

**Causa**: pywin32 non installato (richiesto per COM automation)

**Soluzione**:
```bash
pip install pywin32
```

---

### Problema: "ModuleNotFoundError: No module named 'tkinter'"

**Causa**: tkinter non disponibile (su alcuni Python installati via pip/pyenv)

**Soluzione 1**: Usa GUI Web invece
```bash
python scripts/gui_web.py
```

**Soluzione 2**: Installa tkinter
```bash
# Windows: reinstalla Python from python.org con opzione "tcl/tk"
# Linux:
sudo apt-get install python3-tk
```

---

### Problema: MotorCAD non si connette / "Failed to initialize MotorCAD"

**Causa**: MotorCAD non installato, non licenziato, o processo bloccato

**Soluzione**:
1. Verifica MotorCAD installato: `C:\Program Files\Motor Design Ltd\...`
2. Apri MotorCAD manualmente e verifica licenza valida
3. Chiudi tutte le istanze MotorCAD esistenti (Task Manager)
4. Prova di nuovo

---

### Problema: Simulazione fallisce con "Model build failed"

**Causa**: Parametri motore non validi o file .mot corrotto

**Soluzione**:
1. Apri file .mot manualmente in MotorCAD
2. Verifica che si carichi senza errori
3. Esegui "Tools → Check Model" in MotorCAD GUI
4. Correggi eventuali errori segnalati
5. Salva e riprova

---

### Problema: Array comparison failing (falsi negativi in caching)

**Causa**: Tolleranze troppo strette o dati con noise

**Soluzione**: Modifica tolleranze in `src/utils.py`

```python
def arrays_equal(a: Optional[Any], b: Optional[Any], 
                rtol=1e-4,  # <-- Aumenta da 1e-5 a 1e-4
                atol=1e-6)  # <-- Aumenta da 1e-8 a 1e-6
```

---

### Problema: Database locked errors

**Causa**: Multiple connessioni simultanee al DB (parallelismo)

**Soluzione**:
```python
# In database connection code, add timeout:
con = sqlite3.connect(db_path, timeout=30.0)  # 30 secondi timeout
```

---

### Problema: Out of memory con molti motori

**Causa**: Troppi array in memoria simultaneamente

**Soluzione 1**: Processa in batch più piccoli
```bash
python scripts/run_simulations.py --list motors_batch1.txt
python scripts/run_simulations.py --list motors_batch2.txt
```

**Soluzione 2**: Modifica per non caricare tutti gli array in memoria (streaming)

---

### Problema: PDF generation fails - "AMRE_logo.png not found"

**Causa**: File logo mancante

**Soluzione**:
1. Verifica `motor_types_config.json → pdf_settings → logo_path`
2. Assicurati che file esista nella root directory
3. O modifica config per puntare a logo esistente
4. O commenta codice logo in `generate_performance_reports.py`

---

### Problema: Grafici non si aprono / matplotlib error

**Causa**: Backend matplotlib non configurato

**Soluzione**:
```python
# In scripts/view_results.py o gui_main.py, prima di importare matplotlib:
import matplotlib
matplotlib.use('TkAgg')  # o 'Qt5Agg' o 'Agg' per no-display
import matplotlib.pyplot as plt
```

---

### Problema: Performance lente (simulazioni troppo lunghe)

**Ottimizzazioni**:

1. **Ridurre speed range**:
```json
{
  "Maximum speed": 3000,  // invece di 5000
  "Minimum speed": 500    // invece di 50
}
```

2. **Aumentare speed increment**:
```python
# src/config.py
SPEED_INCREMENT = 100  # invece di 50
```

3. **Ridurre numero di correnti testate**:
```json
{
  "Current density": [4, 7, 10]  // invece di [4, 4.5, 5, ...]
}
```

4. **Usare caching**:
- Esegui prima run con tutte le config
- Successive run con stesse config saranno istantanee (cached)

---

## 📚 RISORSE AGGIUNTIVE

### File Documentazione

- [README.md](README.md) - Documentazione utente principale
- [README_GUI_WEB.md](README_GUI_WEB.md) - Guida GUI web
- [README_PDF_REPORTS.md](README_PDF_REPORTS.md) - Guida report PDF
- [CHANGELOG.md](CHANGELOG.md) - Storico modifiche

### MotorCAD Documentation

- MotorCAD User Manual (Help → User Guide in MotorCAD)
- MotorCAD Scripting Guide (per COM automation API)
- https://www.motordesign.com/

### Python Libraries

- NumPy: https://numpy.org/doc/
- SciPy: https://docs.scipy.org/
- Matplotlib: https://matplotlib.org/stable/contents.html
- ReportLab: https://www.reportlab.com/docs/
- Flask: https://flask.palletsprojects.com/

---

## 🎯 QUICK REFERENCE

### Comandi Più Usati

```bash
# Simulazioni
python scripts/run_simulations.py --directory Motori

# Visualizza risultati
python scripts/view_results.py --list-motors

# Genera report PDF
python scripts/generate_performance_reports.py

# Apri GUI (tkinter o web)
python scripts/gui_main.py
python scripts/gui_web.py
```

### Paths Importanti

```
Database:          mcad_results.db
Config motori:     motor_types_config.json
Config simulaz:    example_config.json
File motori:       Motori/*.mot
Report PDF:        generated_pdfs/
```

### Parametri Chiave

```python
# Velocità simulazione
Minima: 50-500 rpm
Massima: 3000-6000 rpm
Incremento: 50-100 rpm

# Tensioni tipiche
24V, 48V, 80V, 96V, 120V, 144V

# Densità correnti tipiche
FL (lavapavimenti): 4.0 - 5.5 A/mm²
MC (carrelli): 7.0 - 13.0 A/mm²
MV (veicoli): 5.0 - 8.0 A/mm²
```

---

## 📞 CONTATTI E SUPPORTO

**Sviluppatori/Maintainers**: MotorCAD Analysis Team

**Per Bug Report**: Creare issue dettagliato con:
- Descrizione problema
- Steps to reproduce
- File .mot problematico (se applicabile)
- Traceback completo dell'errore
- Versione Python e MotorCAD

**Per Richieste Feature**: Descrivere caso d'uso e benefit atteso

---

## 📝 VERSION HISTORY

### v1.0.0 (2026-02-08)
- Release iniziale con architettura modulare
- GUI desktop e web
- Generazione report PDF
- Caching intelligente
- Documentazione completa

---

**Fine del documento**

Questo file fornisce tutto il contesto necessario per lavorare efficacemente con il MotorCAD Simulation Framework. Mantenerlo aggiornato ad ogni modifica significativa del progetto.
