# GUI Web - Guida Rapida

## Problema con tkinter?

Se ricevi l'errore `ModuleNotFoundError: No module named 'tkinter'`, usa l'interfaccia Web invece!

## Soluzione: GUI Web-Based (Nessun tkinter richiesto)

### Installazione

```bash
pip install flask
```

(Opzionale, per i grafici):
```bash
pip install matplotlib
```

### Avvio

**Metodo 1 - Doppio click (Windows):**
```
Launch_GUI_Web.bat
```

**Metodo 2 - Command line:**
```bash
python scripts/gui_web.py
```

Il browser si aprirà automaticamente all'indirizzo: http://localhost:5000

### Funzionalità

L'interfaccia web fornisce:

1. **Run Simulations Tab**
   - Visualizza e modifica la configurazione simulazioni
   - Salva/carica file di configurazione JSON
   - Guida per usare i comandi CLI

2. **View Results Tab**
   - Lista di tutti i motori nel database
   - Visualizza: Diametro, Lunghezza, Spire, Connessione
   - Pulsante "Refresh" per aggiornare i dati
   - Visualizza run dettagliati per ogni motore

3. **Plot Results Tab**
   - Genera grafici interattivi
   - Scelta tra 4 tipi di plot:
     - Coppia-Velocità
     - Potenza-Velocità  
     - Efficienza-Velocità
     - Tutti i grafici insieme
   - Inserisci Motor ID, Voltage, Current Density

4. **About Tab**
   - Informazioni sull'applicazione
   - Guida all'uso
   - Requisiti di sistema

### Eseguire Simulazioni

Per eseguire simulazioni, usa la command line:

```bash
# Singolo motore
python scripts/run_simulations.py --motor "Motori/nome_motore.mot"

# Directory di motori
python scripts/run_simulations.py --directory "Motori"

# Da file lista
python scripts/run_simulations.py --list motors_to_simulate.txt
```

I risultati appariranno poi nell'interfaccia web sotto "View Results".

### Vantaggi dell'interfaccia Web

- ✅ Nessuna dipendenza da tkinter
- ✅ Funziona su qualsiasi sistema operativo
- ✅ Accessibile da qualsiasi browser
- ✅ Design moderno e responsive
- ✅ Facile da usare

### Problemi?

Se il server non parte, assicurati che:
- Flask sia installato: `pip install flask`
- La porta 5000 non sia già in uso
- Python sia versione 3.8 o superiore

Per fermare il server: `Ctrl+C` nel terminale
