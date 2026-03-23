"""
Programma per il dimensionamento del motore di un veicolo elettrico
Considera tutti i requisiti operativi: accelerazione, velocità massima, pendenze
"""

import math
import numpy as np
from dataclasses import dataclass
from typing import Dict, Tuple, List
from datetime import datetime


@dataclass
class VehicleParameters:
    """Parametri del veicolo"""
    peso_vuoto: float  # kg
    peso_carico: float  # kg
    diametro_ruota: float  # m
    rapporto_riduzione: float  # giri_motore/giri_ruota
    coeff_rotolamento: float  # Cr (adimensionale)
    densita_aria: float = 1.225  # kg/m³
    coeff_drag: float = 0.7  # Cd (tipico per veicolo commerciale)
    area_frontale: float = 2.5  # m² (area frontale del veicolo)
    rendimento_meccanico: float = 0.90  # efficienza trasmissione
    rendimento_motore: float = 0.85  # efficienza motore
    num_ruote_motrici: int = 2  # numero ruote che trasmettono coppia al suolo
    num_motori: int = 1  # numero di motori che forniscono coppia (1=motore centrale, 2=2 motori in-wheel, ecc.)


@dataclass
class RequiredPerformance:
    """Requisiti di prestazione"""
    # Pianura a vuoto
    v_max_vuoto: float  # m/s
    t_acc_vuoto: float  # s (tempo 0-v_max)
    
    # Pianura a carico
    v_max_carico: float  # m/s
    t_acc_carico: float  # s (tempo 0-v_max)
    
    # Pendenza a vuoto
    pendenza_perc_vuoto: float  # % (es: 20 = 20%)
    v_pendenza_vuoto: float  # m/s
    t_acc_pendenza_vuoto: float  # s
    
    # Pendenza a carico
    pendenza_perc_carico: float  # % (es: 15 = 15%)
    v_pendenza_carico: float  # m/s
    t_acc_pendenza_carico: float  # s


class MotorSizing:
    """Classe per il dimensionamento del motore"""
    
    def __init__(self, vehicle: VehicleParameters, performance: RequiredPerformance):
        self.vehicle = vehicle
        self.performance = performance
        self.g = 9.81  # m/s²
        
        # Risultati
        self.scenarios = {}
        self.motor_requirements = {}
    
    def calcola_raggio_ruota(self) -> float:
        """Calcola il raggio della ruota"""
        return self.vehicle.diametro_ruota / 2
    
    def calcola_velocita_angolare_ruota(self, v_lineare: float) -> float:
        """Calcola la velocità angolare della ruota (rad/s)"""
        r = self.calcola_raggio_ruota()
        return v_lineare / r
    
    def calcola_velocita_motore(self, v_lineare: float) -> float:
        """Calcola la velocità del motore (rpm)"""
        omega_ruota = self.calcola_velocita_angolare_ruota(v_lineare)
        rpm_ruota = omega_ruota * 60 / (2 * math.pi)
        rpm_motore = rpm_ruota * self.vehicle.rapporto_riduzione
        return rpm_motore
    
    def calcola_forza_rotolamento(self, massa: float) -> float:
        """Calcola la forza di resistenza al rotolamento"""
        return self.vehicle.coeff_rotolamento * massa * self.g
    
    def calcola_forza_drag(self, velocita: float) -> float:
        """Calcola la forza di resistenza aerodinamica"""
        return 0.5 * self.vehicle.densita_aria * self.vehicle.coeff_drag * \
               self.vehicle.area_frontale * velocita**2
    
    def calcola_forza_pendenza(self, massa: float, pendenza_perc: float) -> float:
        """Calcola la forza dovuta alla pendenza"""
        angolo = math.atan(pendenza_perc / 100)
        return massa * self.g * math.sin(angolo)
    
    def calcola_forza_inerzia(self, massa: float, accelerazione: float) -> float:
        """Calcola la forza necessaria per l'accelerazione (include inerzia rotante)"""
        # Fattore di massa equivalente per inerzia rotante (tipico 1.05-1.15)
        fattore_inerzia = 1.10
        return massa * accelerazione * fattore_inerzia
    
    def calcola_forze_scenario(self, massa: float, velocita: float, 
                                accelerazione: float, pendenza_perc: float = 0) -> Dict:
        """Calcola tutte le forze per uno scenario specifico"""
        F_roll = self.calcola_forza_rotolamento(massa)
        F_drag = self.calcola_forza_drag(velocita)
        F_grade = self.calcola_forza_pendenza(massa, pendenza_perc)
        F_inertia = self.calcola_forza_inerzia(massa, accelerazione)
        
        # Forza totale alla ruota
        F_totale_ruota = F_roll + F_drag + F_grade + F_inertia
        
        return {
            'F_rotolamento': F_roll,
            'F_drag': F_drag,
            'F_pendenza': F_grade,
            'F_inerzia': F_inertia,
            'F_totale_ruota': F_totale_ruota
        }
    
    def calcola_coppia_potenza_motore(self, F_ruota: float, velocita: float) -> Tuple[float, float, float]:
        """
        Calcola coppia e potenza richieste al motore (per singolo motore)
        Returns: (coppia_motore_Nm, potenza_motore_kW, rpm_motore)
        """
        r = self.calcola_raggio_ruota()
        
        # Coppia totale alle ruote motrici
        coppia_totale_ruote = F_ruota * r
        
        # Coppia per singolo motore (divisa per numero motori, considerando riduzione e rendimenti)
        # Se num_motori=1 → il motore vede tutta la coppia
        # Se num_motori=2 → ogni motore fornisce metà della coppia
        coppia_motore = coppia_totale_ruote / (self.vehicle.num_motori * 
                                               self.vehicle.rapporto_riduzione * 
                                               self.vehicle.rendimento_meccanico)
        
        # Velocità motore
        rpm_motore = self.calcola_velocita_motore(velocita)
        omega_motore = rpm_motore * 2 * math.pi / 60
        
        # Potenza meccanica al motore
        potenza_meccanica = coppia_motore * omega_motore / 1000  # kW
        
        # Potenza elettrica richiesta (considerando rendimento motore)
        potenza_elettrica = potenza_meccanica / self.vehicle.rendimento_motore
        
        return coppia_motore, potenza_elettrica, rpm_motore
    
    def analizza_scenario_accelerazione(self, nome: str, massa: float, v_finale: float, 
                                        t_acc: float, pendenza: float = 0) -> Dict:
        """Analizza uno scenario con accelerazione (da 0 a v_finale in t_acc secondi)"""
        # Accelerazione media
        acc_media = v_finale / t_acc
        
        # Calcola forze alla velocità finale e con accelerazione
        forze = self.calcola_forze_scenario(massa, v_finale, acc_media, pendenza)
        
        # Calcola coppia e potenza motore
        coppia, potenza, rpm = self.calcola_coppia_potenza_motore(
            forze['F_totale_ruota'], v_finale
        )
        
        return {
            'nome': nome,
            'tipo': 'accelerazione',
            'massa': massa,
            'velocita': v_finale,
            'velocita_kmh': v_finale * 3.6,
            'tempo_accelerazione': t_acc,
            'accelerazione': acc_media,
            'pendenza_perc': pendenza,
            'forze': forze,
            'coppia_motore_Nm': coppia,
            'potenza_motore_kW': potenza,
            'rpm_motore': rpm
        }
    
    def analizza_scenario_velocita_costante(self, nome: str, massa: float, velocita: float,
                                            pendenza: float = 0) -> Dict:
        """Analizza uno scenario a velocità costante (accelerazione = 0)"""
        # A velocità costante: accelerazione = 0
        acc = 0.0
        
        # Calcola forze alla velocità costante (senza inerzia)
        forze = self.calcola_forze_scenario(massa, velocita, acc, pendenza)
        
        # Calcola coppia e potenza motore
        coppia, potenza, rpm = self.calcola_coppia_potenza_motore(
            forze['F_totale_ruota'], velocita
        )
        
        return {
            'nome': nome,
            'tipo': 'velocita_costante',
            'massa': massa,
            'velocita': velocita,
            'velocita_kmh': velocita * 3.6,
            'tempo_accelerazione': 0,
            'accelerazione': acc,
            'pendenza_perc': pendenza,
            'forze': forze,
            'coppia_motore_Nm': coppia,
            'potenza_motore_kW': potenza,
            'rpm_motore': rpm
        }
    
    def esegui_analisi_completa(self):
        """Esegue l'analisi completa di tutti gli scenari"""
        perf = self.performance
        veh = self.vehicle
        
        print("="*80)
        print("ANALISI DIMENSIONAMENTO MOTORE VEICOLO")
        print("="*80)
        
        # Scenario 1: Pianura a vuoto - velocità massima costante
        self.scenarios['pianura_vuoto_vmax'] = self.analizza_scenario_velocita_costante(
            "Pianura a vuoto - V.max costante",
            veh.peso_vuoto,
            perf.v_max_vuoto,
            0
        )
        
        # Scenario 2: Pianura a vuoto - accelerazione
        self.scenarios['pianura_vuoto_acc'] = self.analizza_scenario_accelerazione(
            "Pianura a vuoto - Accelerazione",
            veh.peso_vuoto,
            perf.v_max_vuoto,
            perf.t_acc_vuoto,
            0
        )
        
        # Scenario 3: Pianura a carico - velocità massima costante
        self.scenarios['pianura_carico_vmax'] = self.analizza_scenario_velocita_costante(
            "Pianura a carico - V.max costante",
            veh.peso_carico,
            perf.v_max_carico,
            0
        )
        
        # Scenario 4: Pianura a carico - accelerazione
        self.scenarios['pianura_carico_acc'] = self.analizza_scenario_accelerazione(
            "Pianura a carico - Accelerazione",
            veh.peso_carico,
            perf.v_max_carico,
            perf.t_acc_carico,
            0
        )
        
        # Scenario 5: Pendenza a vuoto - velocità costante
        self.scenarios['pendenza_vuoto_v'] = self.analizza_scenario_velocita_costante(
            "Pendenza a vuoto - Velocità costante",
            veh.peso_vuoto,
            perf.v_pendenza_vuoto,
            perf.pendenza_perc_vuoto
        )
        
        # Scenario 6: Pendenza a vuoto - accelerazione
        self.scenarios['pendenza_vuoto_acc'] = self.analizza_scenario_accelerazione(
            "Pendenza a vuoto - Accelerazione",
            veh.peso_vuoto,
            perf.v_pendenza_vuoto,
            perf.t_acc_pendenza_vuoto,
            perf.pendenza_perc_vuoto
        )
        
        # Scenario 7: Pendenza a carico - velocità costante
        self.scenarios['pendenza_carico_v'] = self.analizza_scenario_velocita_costante(
            "Pendenza a carico - Velocità costante",
            veh.peso_carico,
            perf.v_pendenza_carico,
            perf.pendenza_perc_carico
        )
        
        # Scenario 8: Pendenza a carico - accelerazione
        self.scenarios['pendenza_carico_acc'] = self.analizza_scenario_accelerazione(
            "Pendenza a carico - Accelerazione",
            veh.peso_carico,
            perf.v_pendenza_carico,
            perf.t_acc_pendenza_carico,
            perf.pendenza_perc_carico
        )
        
        self.stampa_risultati()
        self.determina_requisiti_motore()
    
    def stampa_risultati(self):
        """Stampa i risultati dettagliati per ogni scenario"""
        for key, scenario in self.scenarios.items():
            print(f"\n{'='*80}")
            print(f"SCENARIO: {scenario['nome']}")
            print(f"{'='*80}")
            print(f"Tipo: {scenario['tipo'].upper()}")
            print(f"Massa veicolo: {scenario['massa']:.0f} kg")
            print(f"Velocità: {scenario['velocita_kmh']:.1f} km/h ({scenario['velocita']:.2f} m/s)")
            if scenario['tipo'] == 'accelerazione':
                print(f"Tempo accelerazione: {scenario['tempo_accelerazione']:.1f} s")
                print(f"Accelerazione media: {scenario['accelerazione']:.2f} m/s²")
            else:
                print(f"Regime: Velocità costante (accelerazione = 0)")
            if scenario['pendenza_perc'] > 0:
                print(f"Pendenza: {scenario['pendenza_perc']:.1f}%")
            
            print(f"\nANALISI FORZE:")
            print(f"  - Resistenza rotolamento: {scenario['forze']['F_rotolamento']:.0f} N")
            print(f"  - Resistenza aerodinamica: {scenario['forze']['F_drag']:.0f} N")
            if scenario['pendenza_perc'] > 0:
                print(f"  - Forza pendenza: {scenario['forze']['F_pendenza']:.0f} N")
            print(f"  - Forza inerzia: {scenario['forze']['F_inerzia']:.0f} N")
            print(f"  - FORZA TOTALE: {scenario['forze']['F_totale_ruota']:.0f} N")
            
            print(f"\nREQUISITI MOTORE:")
            print(f"  - Coppia: {scenario['coppia_motore_Nm']:.1f} Nm")
            print(f"  - Potenza: {scenario['potenza_motore_kW']:.1f} kW")
            print(f"  - Velocità: {scenario['rpm_motore']:.0f} rpm")
    
    def determina_requisiti_motore(self):
        """Determina i requisiti finali del motore (massimi tra tutti gli scenari)"""
        coppia_max = 0
        potenza_max = 0
        rpm_max = 0
        
        scenario_coppia = ""
        scenario_potenza = ""
        scenario_rpm = ""
        
        for key, scenario in self.scenarios.items():
            if scenario['coppia_motore_Nm'] > coppia_max:
                coppia_max = scenario['coppia_motore_Nm']
                scenario_coppia = scenario['nome']
            
            if scenario['potenza_motore_kW'] > potenza_max:
                potenza_max = scenario['potenza_motore_kW']
                scenario_potenza = scenario['nome']
            
            if scenario['rpm_motore'] > rpm_max:
                rpm_max = scenario['rpm_motore']
                scenario_rpm = scenario['nome']
        
        self.motor_requirements = {
            'coppia_nominale_Nm': coppia_max,
            'potenza_nominale_kW': potenza_max,
            'velocita_max_rpm': rpm_max,
            'scenario_critico_coppia': scenario_coppia,
            'scenario_critico_potenza': scenario_potenza,
            'scenario_critico_rpm': scenario_rpm
        }
        
        print(f"\n{'='*80}")
        print("REQUISITI FINALI MOTORE")
        print(f"{'='*80}")
        print(f"Coppia nominale richiesta: {coppia_max:.1f} Nm")
        print(f"  → Scenario critico: {scenario_coppia}")
        print(f"\nPotenza nominale richiesta: {potenza_max:.1f} kW ({potenza_max*1.34:.1f} HP)")
        print(f"  → Scenario critico: {scenario_potenza}")
        print(f"\nVelocità massima richiesta: {rpm_max:.0f} rpm")
        print(f"  → Scenario critico: {scenario_rpm}")
        
        # Suggerimenti per la scelta del motore
        print(f"\n{'='*80}")
        print("RACCOMANDAZIONI")
        print(f"{'='*80}")
        print(f"Scegliere un motore con:")
        print(f"  - Coppia nominale: ≥ {coppia_max*1.15:.0f} Nm (margine 15%)")
        print(f"  - Potenza nominale: ≥ {potenza_max*1.15:.1f} kW (margine 15%)")
        print(f"  - Velocità massima: ≥ {rpm_max*1.1:.0f} rpm (margine 10%)")
        print(f"\nParametri di trasmissione:")
        print(f"  - Rapporto di riduzione: {self.vehicle.rapporto_riduzione:.2f}:1")
        print(f"  - Diametro ruota: {self.vehicle.diametro_ruota*1000:.0f} mm")
        print(f"  - Numero motori: {self.vehicle.num_motori}")
        print(f"  - Numero ruote motrici: {self.vehicle.num_ruote_motrici}")
        print(f"  - Rendimento trasmissione: {self.vehicle.rendimento_meccanico*100:.0f}%")
        print(f"  - Rendimento motore: {self.vehicle.rendimento_motore*100:.0f}%")
    
    def salva_report_txt(self, nome_file: str = "motor_sizing_report.txt"):
        """Salva il report completo in un file di testo"""
        with open(nome_file, 'w', encoding='utf-8') as f:
            # Intestazione
            f.write("="*80 + "\n")
            f.write("REPORT DIMENSIONAMENTO MOTORE VEICOLO ELETTRICO\n")
            f.write(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")
            
            # Parametri veicolo
            f.write("PARAMETRI VEICOLO:\n")
            f.write("-"*80 + "\n")
            f.write(f"Peso a vuoto: {self.vehicle.peso_vuoto:.0f} kg\n")
            f.write(f"Peso a carico: {self.vehicle.peso_carico:.0f} kg\n")
            f.write(f"Diametro ruota: {self.vehicle.diametro_ruota*1000:.0f} mm\n")
            f.write(f"Rapporto riduzione: {self.vehicle.rapporto_riduzione:.2f}:1\n")
            f.write(f"Coefficiente rotolamento: {self.vehicle.coeff_rotolamento:.3f}\n")
            f.write(f"Coefficiente drag: {self.vehicle.coeff_drag:.2f}\n")
            f.write(f"Area frontale: {self.vehicle.area_frontale:.2f} m²\n")
            f.write(f"Numero motori: {self.vehicle.num_motori}\n")
            f.write(f"Numero ruote motrici: {self.vehicle.num_ruote_motrici}\n")
            f.write(f"Rendimento meccanico: {self.vehicle.rendimento_meccanico*100:.0f}%\n")
            f.write(f"Rendimento motore: {self.vehicle.rendimento_motore*100:.0f}%\n\n")
            
            # Scenari analizzati
            f.write("\n" + "="*80 + "\n")
            f.write("SCENARI ANALIZZATI\n")
            f.write("="*80 + "\n")
            
            for key, scenario in self.scenarios.items():
                f.write(f"\n{'-'*80}\n")
                f.write(f"SCENARIO: {scenario['nome']}\n")
                f.write(f"{'-'*80}\n")
                f.write(f"Tipo: {scenario['tipo'].upper()}\n")
                f.write(f"Massa veicolo: {scenario['massa']:.0f} kg\n")
                f.write(f"Velocità: {scenario['velocita_kmh']:.1f} km/h ({scenario['velocita']:.2f} m/s)\n")
                
                if scenario['tipo'] == 'accelerazione':
                    f.write(f"Tempo accelerazione: {scenario['tempo_accelerazione']:.1f} s\n")
                    f.write(f"Accelerazione media: {scenario['accelerazione']:.2f} m/s²\n")
                else:
                    f.write(f"Regime: Velocità costante (accelerazione = 0)\n")
                
                if scenario['pendenza_perc'] > 0:
                    f.write(f"Pendenza: {scenario['pendenza_perc']:.1f}%\n")
                
                f.write(f"\nANALISI FORZE:\n")
                f.write(f"  - Resistenza rotolamento: {scenario['forze']['F_rotolamento']:.0f} N\n")
                f.write(f"  - Resistenza aerodinamica: {scenario['forze']['F_drag']:.0f} N\n")
                if scenario['pendenza_perc'] > 0:
                    f.write(f"  - Forza pendenza: {scenario['forze']['F_pendenza']:.0f} N\n")
                f.write(f"  - Forza inerzia: {scenario['forze']['F_inerzia']:.0f} N\n")
                f.write(f"  - FORZA TOTALE: {scenario['forze']['F_totale_ruota']:.0f} N\n")
                
                f.write(f"\nREQUISITI MOTORE (per singolo motore):\n")
                f.write(f"  - Coppia: {scenario['coppia_motore_Nm']:.1f} Nm\n")
                f.write(f"  - Potenza: {scenario['potenza_motore_kW']:.1f} kW\n")
                f.write(f"  - Velocità: {scenario['rpm_motore']:.0f} rpm\n")
            
            # Requisiti finali
            f.write(f"\n\n{'='*80}\n")
            f.write("REQUISITI FINALI MOTORE\n")
            f.write(f"{'='*80}\n")
            req = self.motor_requirements
            f.write(f"Coppia nominale richiesta: {req['coppia_nominale_Nm']:.1f} Nm\n")
            f.write(f"  → Scenario critico: {req['scenario_critico_coppia']}\n\n")
            f.write(f"Potenza nominale richiesta: {req['potenza_nominale_kW']:.1f} kW ")
            f.write(f"({req['potenza_nominale_kW']*1.34:.1f} HP)\n")
            f.write(f"  → Scenario critico: {req['scenario_critico_potenza']}\n\n")
            f.write(f"Velocità massima richiesta: {req['velocita_max_rpm']:.0f} rpm\n")
            f.write(f"  → Scenario critico: {req['scenario_critico_rpm']}\n")
            
            # Raccomandazioni
            f.write(f"\n{'='*80}\n")
            f.write("RACCOMANDAZIONI\n")
            f.write(f"{'='*80}\n")
            f.write(f"Scegliere un motore con:\n")
            f.write(f"  - Coppia nominale: ≥ {req['coppia_nominale_Nm']*1.15:.0f} Nm (margine 15%)\n")
            f.write(f"  - Potenza nominale: ≥ {req['potenza_nominale_kW']*1.15:.1f} kW (margine 15%)\n")
            f.write(f"  - Velocità massima: ≥ {req['velocita_max_rpm']*1.1:.0f} rpm (margine 10%)\n")
        
        print(f"\n✓ Report salvato in: {nome_file}")


@dataclass
class DutyCycleSegment:
    """Definisce un segmento del duty cycle"""
    nome: str  # Nome descrittivo del segmento
    pendenza_perc: float  # % pendenza
    distanza_metri: float  # metri da percorrere
    velocita_mps: float  # m/s velocità target
    massa_kg: float  # kg massa del veicolo in questo segmento


class DutyCycleAnalysis:
    """Analisi di un duty cycle completo"""
    
    
    class DutyCycleAnalysis:
        """Analisi di un duty cycle completo"""
        
    def __init__(self, vehicle: VehicleParameters, segmenti: List[DutyCycleSegment], 
                    performance: RequiredPerformance):
        self.vehicle = vehicle
        self.segmenti = segmenti
        self.motor_sizing = MotorSizing(vehicle, performance)
        self.risultati_segmenti = []
        self.energia_totale = 0
        self.tempo_totale = 0
        self.distanza_totale = 0
    
    
    def analizza_duty_cycle(self):
        """Analizza tutti i segmenti del duty cycle"""
        print(f"\n{'='*80}")
        print("ANALISI DUTY CYCLE")
        print(f"{'='*80}\n")
        
        self.risultati_segmenti = []
        self.energia_totale = 0
        self.tempo_totale = 0
        self.distanza_totale = 0
        
        for i, segmento in enumerate(self.segmenti, 1):
            risultato = self.analizza_segmento(segmento, i)
            self.risultati_segmenti.append(risultato)
            self.energia_totale += risultato['energia_kWh']
            self.tempo_totale += risultato['tempo_s']
            self.distanza_totale += segmento.distanza_metri
        
        self.stampa_riepilogo()
    
    def analizza_segmento(self, segmento: DutyCycleSegment, numero: int) -> Dict:
        """Analizza un singolo segmento del duty cycle"""
        print(f"\n{'-'*80}")
        print(f"SEGMENTO {numero}: {segmento.nome}")
        print(f"{'-'*80}")
        print(f"Pendenza: {segmento.pendenza_perc:.1f}%")
        print(f"Distanza: {segmento.distanza_metri:.0f} m")
        print(f"Velocità: {segmento.velocita_mps*3.6:.1f} km/h ({segmento.velocita_mps:.2f} m/s)")
        print(f"Massa: {segmento.massa_kg:.0f} kg")
        
        # Calcola tempo di percorrenza
        tempo_s = segmento.distanza_metri / segmento.velocita_mps
        
        # Calcola forze a velocità costante (duty cycle assume velocità costante)
        forze = self.motor_sizing.calcola_forze_scenario(
            segmento.massa_kg,
            segmento.velocita_mps,
            0,  # accelerazione = 0 (velocità costante)
            segmento.pendenza_perc
        )
        
        # Calcola coppia e potenza
        coppia, potenza_kW, rpm = self.motor_sizing.calcola_coppia_potenza_motore(
            forze['F_totale_ruota'],
            segmento.velocita_mps
        )
        
        # Calcola energia per questo segmento
        energia_kWh = potenza_kW * (tempo_s / 3600)
        
        print(f"\nTempo percorrenza: {tempo_s:.1f} s ({tempo_s/60:.2f} min)")
        print(f"\nForze:")
        print(f"  - Rotolamento: {forze['F_rotolamento']:.0f} N")
        print(f"  - Drag: {forze['F_drag']:.0f} N")
        print(f"  - Pendenza: {forze['F_pendenza']:.0f} N")
        print(f"  - Totale: {forze['F_totale_ruota']:.0f} N")
        print(f"\nMotore (per singolo motore):")
        print(f"  - Coppia: {coppia:.1f} Nm")
        print(f"  - Potenza: {potenza_kW:.1f} kW")
        print(f"  - RPM: {rpm:.0f}")
        print(f"  - Energia: {energia_kWh:.3f} kWh")
        
        return {
            'segmento': segmento,
            'tempo_s': tempo_s,
            'forze': forze,
            'coppia_Nm': coppia,
            'potenza_kW': potenza_kW,
            'rpm': rpm,
            'energia_kWh': energia_kWh
        }
    
    def stampa_riepilogo(self):
        """Stampa il riepilogo del duty cycle"""
        print(f"\n\n{'='*80}")
        print("RIEPILOGO DUTY CYCLE")
        print(f"{'='*80}")
        print(f"Numero segmenti: {len(self.segmenti)}")
        print(f"Distanza totale: {self.distanza_totale:.0f} m ({self.distanza_totale/1000:.2f} km)")
        print(f"Tempo totale: {self.tempo_totale:.1f} s ({self.tempo_totale/60:.2f} min)")
        print(f"Energia totale: {self.energia_totale:.3f} kWh")
        print(f"Velocità media: {self.distanza_totale/self.tempo_totale*3.6:.1f} km/h")
        print(f"Potenza media: {self.energia_totale/(self.tempo_totale/3600):.1f} kW")
        
        # Trova picchi
        coppia_max = max([r['coppia_Nm'] for r in self.risultati_segmenti])
        potenza_max = max([r['potenza_kW'] for r in self.risultati_segmenti])
        rpm_max = max([r['rpm'] for r in self.risultati_segmenti])
        
        print(f"\nPicchi motore (per singolo motore):")
        print(f"  - Coppia max: {coppia_max:.1f} Nm")
        print(f"  - Potenza max: {potenza_max:.1f} kW")
        print(f"  - RPM max: {rpm_max:.0f}")
        print(f"\nConsumo specifico: {self.energia_totale/(self.distanza_totale/1000):.2f} kWh/km")
    
    def salva_report_duty_cycle(self, nome_file: str = "duty_cycle_report.txt"):
        """Salva il report del duty cycle in un file di testo"""
        with open(nome_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("REPORT ANALISI DUTY CYCLE\n")
            f.write(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")
            
            # Parametri veicolo
            f.write("PARAMETRI VEICOLO:\n")
            f.write("-"*80 + "\n")
            f.write(f"Diametro ruota: {self.vehicle.diametro_ruota*1000:.0f} mm\n")
            f.write(f"Rapporto riduzione: {self.vehicle.rapporto_riduzione:.2f}:1\n")
            f.write(f"Numero motori: {self.vehicle.num_motori}\n")
            f.write(f"Rendimenti: mec={self.vehicle.rendimento_meccanico*100:.0f}%, ")
            f.write(f"mot={self.vehicle.rendimento_motore*100:.0f}%\n\n")
            
            # Dettaglio segmenti
            f.write("\nDETTAGLIO SEGMENTI:\n")
            f.write("="*80 + "\n")
            
            for i, ris in enumerate(self.risultati_segmenti, 1):
                seg = ris['segmento']
                f.write(f"\nSegmento {i}: {seg.nome}\n")
                f.write("-"*80 + "\n")
                f.write(f"Pendenza: {seg.pendenza_perc:.1f}% | ")
                f.write(f"Distanza: {seg.distanza_metri:.0f} m | ")
                f.write(f"Velocità: {seg.velocita_mps*3.6:.1f} km/h | ")
                f.write(f"Massa: {seg.massa_kg:.0f} kg\n")
                f.write(f"Tempo: {ris['tempo_s']:.1f} s | ")
                f.write(f"Coppia: {ris['coppia_Nm']:.1f} Nm | ")
                f.write(f"Potenza: {ris['potenza_kW']:.1f} kW | ")
                f.write(f"Energia: {ris['energia_kWh']:.3f} kWh\n")
            
            # Riepilogo
            f.write(f"\n\n{'='*80}\n")
            f.write("RIEPILOGO\n")
            f.write(f"{'='*80}\n")
            f.write(f"Distanza totale: {self.distanza_totale:.0f} m ({self.distanza_totale/1000:.2f} km)\n")
            f.write(f"Tempo totale: {self.tempo_totale:.1f} s ({self.tempo_totale/60:.2f} min)\n")
            f.write(f"Energia totale: {self.energia_totale:.3f} kWh\n")
            f.write(f"Velocità media: {self.distanza_totale/self.tempo_totale*3.6:.1f} km/h\n")
            f.write(f"Consumo specifico: {self.energia_totale/(self.distanza_totale/1000):.2f} kWh/km\n")
            
            coppia_max = max([r['coppia_Nm'] for r in self.risultati_segmenti])
            potenza_max = max([r['potenza_kW'] for r in self.risultati_segmenti])
            rpm_max = max([r['rpm'] for r in self.risultati_segmenti])
            
            f.write(f"\nPicchi motore:\n")
            f.write(f"  - Coppia max: {coppia_max:.1f} Nm\n")
            f.write(f"  - Potenza max: {potenza_max:.1f} kW\n")
            f.write(f"  - RPM max: {rpm_max:.0f}\n")
        
        print(f"✓ Report duty cycle salvato in: {nome_file}")


def main():
    """Esempio di utilizzo con dati tipici"""
    print("PROGRAMMA DIMENSIONAMENTO MOTORE VEICOLO ELETTRICO\n")
    
    # Definizione parametri veicolo
    vehicle = VehicleParameters(
        peso_vuoto=3875,  # kg
        peso_carico=6250,  # kg
        diametro_ruota=0.7439,  # m (743.9mm)
        rapporto_riduzione=15.04,  # giri_motore/giri_ruota
        coeff_rotolamento=0.018,  # tipico per pneumatici su asfalto
        densita_aria=1.225,  # kg/m³
        coeff_drag=0,  # Cd
        area_frontale=2.5,  # m²
        rendimento_meccanico=0.90,  # 90%
        rendimento_motore=0.85,  # 85%
        num_ruote_motrici=2,  # 2 ruote posteriori motrici
        num_motori=1   # 1 motore
    )
    
    # Definizione requisiti di prestazione
    performance = RequiredPerformance(
        # Pianura a vuoto
        v_max_vuoto=50/3.6,  # 50 km/h → m/s
        t_acc_vuoto=24,  # secondi
        
        # Pianura a carico
        v_max_carico=40/3.6,  # 40 km/h → m/s
        t_acc_carico=32,  # secondi
        
        # Pendenza a vuoto
        pendenza_perc_vuoto=16,  # 15%
        v_pendenza_vuoto=22/3.6,  # 13 km/h → m/s
        t_acc_pendenza_vuoto=16,  # secondi
        
        # Pendenza a carico
        pendenza_perc_carico=16,  # 15%
        v_pendenza_carico=16/3.6,  # 13 km/h → m/s
        t_acc_pendenza_carico=20  # secondi
    )
    
    # Esegui analisi
    sizing = MotorSizing(vehicle, performance)
    sizing.esegui_analisi_completa()
    
    # Salva report in file txt
    report_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    os.makedirs(report_dir, exist_ok=True)
    sizing.salva_report_txt(os.path.join(report_dir, "motor_sizing_report.txt"))
    
    print(f"\n{'='*80}")
    print("ANALISI COMPLETATA")
    print(f"{'='*80}\n")
    
    # ESEMPIO DUTY CYCLE
    print("\n\n" + "="*80)
    print("ESEMPIO ANALISI DUTY CYCLE")
    print("="*80)
    
    # Definizione di un duty cycle di esempio
    duty_cycle_segmenti = [
        DutyCycleSegment(
            nome="Segmento 1",
            pendenza_perc=2,
            distanza_metri=1200,
            velocita_mps=35/3.6,  # 35 km/h
            massa_kg=3000  # a carico
        ),
        DutyCycleSegment(
            nome="Segmento 2",
            pendenza_perc=4,
            distanza_metri=750,
            velocita_mps=35/3.6,  # 35 km/h
            massa_kg=3000
        ),
        DutyCycleSegment(
            nome="Segmento 3",
            pendenza_perc=6,
            distanza_metri=300,
            velocita_mps=35/3.6,  # 35 km/h
            massa_kg=3000
        ),
        DutyCycleSegment(
            nome="Segmento 4",
            pendenza_perc=8,
            distanza_metri=300,
            velocita_mps=35/3.6,  # 35 km/h
            massa_kg=3000
        ),
        DutyCycleSegment(
            nome="Segmento 5",
            pendenza_perc=10,
            distanza_metri=300,
            velocita_mps=35/3.6,  # 35 km/h
            massa_kg=3000  # a vuoto
        ),
        DutyCycleSegment(
            nome="Segmento 6",
            pendenza_perc=15,
            distanza_metri=150,
            velocita_mps=13/3.6,  # 13 km/h
            massa_kg=3000
        )
    ]
    
    # Analizza il duty cycle
    #duty_cycle_analysis = DutyCycleAnalysis(vehicle,  duty_cycle_segmenti, performance)
    #duty_cycle_analysis.analizza_duty_cycle()
    
    # Salva report duty cycle
    #duty_cycle_analysis.salva_report_duty_cycle("duty_cycle_report.txt")
    
    print("\n" + "="*80)
    print("TUTTI I REPORT SONO STATI GENERATI")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
