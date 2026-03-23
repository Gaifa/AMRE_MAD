"""
Motor Selector — Find best-matching motors from the database.

Searches the database for motors that best satisfy given performance targets
(torque, power, speed) at a given battery voltage and duty cycle.
Results are sorted from best fit to worst and displayed as a combined
bar-chart + specification table.

Usage examples
--------------
    # All three — consistent (P ≈ T·ω), used directly:
    python find_motor.py --torque 50 --power 5 --speed 3000 --voltage 48 --duty S2-20min

    # Two only — missing value is derived automatically:
    python find_motor.py --torque 120 --speed 1500 --voltage 96 --duty S1
    python find_motor.py --power 8 --speed 2000 --voltage 72 --duty S2-5min

    # All three but inconsistent — first two in argv order are kept, third derived:
    python find_motor.py --torque 80 --power 8 --speed 999 --voltage 72 --duty S2-5min

Scoring
-------
A "fitness score" is assigned to each motor/type combination:
  - Motors that cannot deliver the requested torque OR power at the target
    speed receive a negative score (they still appear in the ranking so the
    user can see how close they come).
  - Among passing motors, the one closest to the target (ratio ≈ 1.0–1.1) wins;
    heavily over-sized motors are gently penalized.
"""

import os
import sys
import json
import sqlite3
import argparse

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src import database, config

CONFIG_FILE = os.path.join(os.path.dirname(__file__), '..', 'config', 'motor_types_config.json')

# ── palette (one colour per result rank) ──────────────────────────────────────
RANK_COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
               '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
HEADER_COLOR = '#203764'


# =============================================================================
# HELPERS
# =============================================================================

def load_types_config(path=CONFIG_FILE):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_motor_info(motor_json):
    """Extract physical motor parameters from the motor_json dict."""
    raw_conn = motor_json.get('winding_connection', {}).get('value', None)
    if raw_conn is not None:
        try:
            conn_int = int(float(raw_conn))
            connection = "Star" if conn_int == 0 else "Delta" if conn_int == 1 else "Unknown"
        except (ValueError, TypeError):
            connection = "Unknown"
    else:
        connection = "Unknown"

    phases_raw = motor_json.get('MagPhases', {}).get('value', None)
    try:
        phases = int(float(phases_raw)) if phases_raw is not None else None
    except (ValueError, TypeError):
        phases = None

    return {
        'diameter':   motor_json.get('Stator_Lam_Dia',     {}).get('value', 0),
        'length':     motor_json.get('Stator_Lam_Length',  {}).get('value', 0),
        'turns':      motor_json.get('Number_turns_coil',  {}).get('value', 0),
        'poles':      motor_json.get('Pole_number',        {}).get('value', 0),
        'slots':      motor_json.get('Slot_number',        {}).get('value', 0),
        'phases':     phases,
        'connection': connection,
    }


def perf_at_speed(run_data, target_speed):
    """
    Interpolate torque, power, efficiency and current at *target_speed* rpm.

    Returns None if the target speed exceeds the simulated range.
    Power is whatever unit MotorCAD stored (kW for Shaft_Power in this project).
    """
    speed      = np.asarray(run_data.get('Speed',                      [])).flatten()
    torque     = np.asarray(run_data.get('Shaft_Torque',               [])).flatten()
    power      = np.asarray(run_data.get('Shaft_Power',                [])).flatten()
    efficiency = np.asarray(run_data.get('Efficiency',                 [])).flatten()
    current    = np.asarray(run_data.get('Stator_Current_Line_RMS',    [])).flatten()
    voltage_ph = np.asarray(run_data.get('Voltage_Phase_RMS',          [])).flatten()

    if len(speed) == 0:
        return None

    # Motor can only operate up to its max simulated speed
    if target_speed > np.max(speed):
        return None

    # Sort ascending by speed for np.interp
    idx = np.argsort(speed)
    speed      = speed[idx]
    torque     = torque[idx]
    power      = power[idx]
    efficiency = efficiency[idx] if len(efficiency) == len(idx) else efficiency
    current    = current[idx]    if len(current)    == len(idx) else current
    voltage_ph = voltage_ph[idx] if len(voltage_ph) == len(idx) else voltage_ph

    return {
        'torque':      float(np.interp(target_speed, speed, torque)),
        'power':       float(np.interp(target_speed, speed, power)),
        'efficiency':  float(np.interp(target_speed, speed, efficiency)) if len(efficiency) == len(idx) else None,
        'current':     float(np.interp(target_speed, speed, current))    if len(current)    == len(idx) else None,
        'voltage_ph':  float(np.interp(target_speed, speed, voltage_ph)) if len(voltage_ph) == len(idx) else None,
        'max_speed':   float(np.max(speed)),
    }


def resolve_targets(torque, power, speed, argv):
    """
    Ensure exactly two of the three (torque, power, speed) are pinned and
    derive the third from  P [kW] = T [Nm] * n [rpm] * 2π / 60 / 1000.

    Rules
    -----
    - Exactly 2 provided → derive the missing one, no warning.
    - All 3 provided and consistent (within 5 %) → use as-is.
    - All 3 provided but inconsistent → keep the first two in argv order,
      re-derive the third and emit a warning.

    Returns
    -------
    (torque, power, speed, note)   note is None when no adjustment was made.
    """
    _OMEGA = lambda n: n * 2 * np.pi / 60          # rpm → rad/s
    _P_TOL = 0.05                                   # 5 % consistency tolerance

    provided = [(k, v) for k, v in [('torque', torque), ('power', power), ('speed', speed)]
                if v is not None]

    if len(provided) < 2:
        raise ValueError("At least two of --torque / --power / --speed must be supplied.")

    if len(provided) == 2:
        keys = {k for k, _ in provided}
        if 'speed' not in keys:
            # derive speed
            s = power * 1000 * 60 / (torque * 2 * np.pi)
            return torque, power, s, f"Speed not given — derived: {s:.0f} rpm"
        elif 'power' not in keys:
            # derive power
            p = torque * _OMEGA(speed) / 1000
            return torque, p, speed, f"Power not given — derived: {p:.3f} kW"
        else:
            # derive torque
            t = power * 1000 / _OMEGA(speed)
            return t, power, speed, f"Torque not given — derived: {t:.2f} Nm"

    # All three given — check consistency
    p_expected = torque * _OMEGA(speed) / 1000
    if abs(p_expected - power) / max(p_expected, power, 1e-9) <= _P_TOL:
        return torque, power, speed, None   # consistent, nothing to change

    # Inconsistent — honour the first two in argv order
    _ARG_KEYS = {'--torque': 'torque', '--power': 'power', '--speed': 'speed'}
    arg_order = []
    for a in argv:
        k = _ARG_KEYS.get(a)
        if k and k not in arg_order:
            arg_order.append(k)
    # fallback if parsing fails
    if len(arg_order) < 2:
        arg_order = ['torque', 'power', 'speed']

    keep = arg_order[:2]
    vals = {'torque': torque, 'power': power, 'speed': speed}
    note = (f"All 3 given but inconsistent (P ≠ T·ω, Δ={abs(p_expected - power)/power*100:.1f}%). "
            f"Using first two: {keep[0]} and {keep[1]}.")

    if set(keep) == {'torque', 'power'}:
        s = vals['power'] * 1000 * 60 / (vals['torque'] * 2 * np.pi)
        return vals['torque'], vals['power'], s, note + f" Speed re-derived: {s:.0f} rpm"
    elif set(keep) == {'torque', 'speed'}:
        p = vals['torque'] * _OMEGA(vals['speed']) / 1000
        return vals['torque'], p, vals['speed'], note + f" Power re-derived: {p:.3f} kW"
    else:  # power + speed
        t = vals['power'] * 1000 / _OMEGA(vals['speed'])
        return t, vals['power'], vals['speed'], note + f" Torque re-derived: {t:.2f} Nm"


# Weight of the size penalty relative to the performance score.
# 0.20 means the smallest motor gains +0.10 and the largest loses -0.10
# compared to motors of average size (same performance score).
_SIZE_WEIGHT = 0.20

# Motor-type preference penalty  (deducted directly from the score).
# FL (Frameless) is preferred → 0 penalty.
# MEC → small penalty.  MEC-V (ventilated) → larger penalty.
_TYPE_PENALTY = {
    'FL':    0.00,
    'MEC':   0.08,
    'MEC-V': 0.16,
}


def _perf_score(achieved, target_torque, target_power):
    """
    Pure performance fitness score in (-∞, 1]  (ignores motor dimensions).

    Passing motors  (both torque ≥ target AND power ≥ target): score in (0, 1]
      Perfect fit (ratio ≈ 1.05) → score ≈ 1.0
      Large over-sizing           → score decreases gently

    Failing motors: score = min(t_ratio, p_ratio) - 1  ∈ (-1, 0)
    """
    if achieved is None:
        return -999.0

    t_ratio = achieved['torque'] / target_torque if target_torque > 0 else 1.0
    p_ratio = achieved['power']  / target_power  if target_power  > 0 else 1.0

    if t_ratio < 1.0 or p_ratio < 1.0:
        return min(t_ratio, p_ratio) - 1.0     # negative → does not meet target

    # Both targets met: penalise over-sizing (ideal is just 5 % above target)
    combined = (t_ratio + p_ratio) / 2.0
    return max(0.0, 1.0 - abs(combined - 1.05) * 0.4)


def _apply_penalties(results):
    """
    Adjust each result's score with two independent penalties:

    1. Size penalty (normalised across the candidate set)
       Envelope volume ∝ D² × L.  Smallest motor → 0 deduction;
       largest → _SIZE_WEIGHT deduction.  Others are linear in between.

    2. Motor-type preference penalty (fixed deduction per type)
       FL (Frameless) → 0.00  (preferred)
       MEC            → 0.08
       MEC-V          → 0.16
       Unknown types  → 0.16  (treated as least preferred)
    """
    # ── size penalty ──────────────────────────────────────────────────────────
    volumes = [
        r['motor_info']['diameter'] ** 2 * r['motor_info']['length']
        for r in results
    ]
    vol_min   = min(volumes)
    vol_max   = max(volumes)
    vol_range = vol_max - vol_min

    for r, vol in zip(results, volumes):
        size_factor = (vol - vol_min) / vol_range if vol_range > 0 else 0.0
        r['score']      -= _SIZE_WEIGHT * size_factor
        r['size_factor'] = round(size_factor, 4)   # stored for transparency

    # ── type preference penalty ───────────────────────────────────────────────
    for r in results:
        type_penalty = _TYPE_PENALTY.get(r['motor_type'], 0.16)
        r['score'] -= type_penalty
        r['type_penalty'] = type_penalty             # stored for transparency


# =============================================================================
# MAIN SEARCH
# =============================================================================

def search_motors(target_torque, target_power, target_speed, voltage,
                  duty_name, db_path=None, config_path=CONFIG_FILE, top_n=5):
    """
    Query every (motor × motor_type) combination in the database and rank
    them by fitness score for the given operating point.

    Parameters
    ----------
    target_torque : float   [Nm]
    target_power  : float   [kW]
    target_speed  : float   [rpm]
    voltage       : float   [V]
    duty_name     : str     e.g. 'S1', 'S2-20min'
    top_n         : int     how many results to return

    Returns
    -------
    List of result dicts, sorted best → worst (length ≤ top_n).
    """
    if db_path is None:
        db_path = config.DB_PATH

    types_config = load_types_config(config_path)
    motors = database.list_all_motors(db_path)

    if not motors:
        print("No motors found in database.")
        return []

    results = []
    con = sqlite3.connect(db_path)

    for motor in motors:
        motor_info = get_motor_info(motor['motor_json'])
        motor_id   = motor['id']

        for motor_type, type_cfg in types_config['motor_types'].items():
            duties = type_cfg.get('duties', {})

            if duty_name not in duties:
                continue

            current_density = duties[duty_name]['current_density']
            run_data = database.load_run_data(con, motor_id, voltage, current_density)
            if run_data is None:
                continue

            achieved = perf_at_speed(run_data, target_speed)
            score    = _perf_score(achieved, target_torque, target_power)

            results.append({
                'motor_id':        motor_id,
                'motor_type':      motor_type,
                'motor_info':      motor_info,
                'duty':            duty_name,
                'current_density': current_density,
                'voltage':         voltage,
                'achieved':        achieved,
                'score':           score,
                'size_factor':     0.0,
                'type_penalty':    0.0,
            })

    con.close()

    # Apply size + type penalties across the full candidate set, then rank
    if results:
        _apply_penalties(results)
    results.sort(key=lambda r: r['score'], reverse=True)
    return results[:top_n]


# =============================================================================
# OUTPUT — terminal
# =============================================================================

def print_results(results, target_torque, target_power, target_speed, duty_name, note=None):
    print("\n" + "=" * 80)
    print("MOTOR SEARCH RESULTS")
    if note:
        print(f"  NOTE: {note}")
    print(f"  Target torque  : ≥ {target_torque:.2f} Nm")
    print(f"  Target power   : ≥ {target_power:.3f} kW")
    print(f"  Target speed   : {target_speed:.0f} rpm")
    print(f"  Duty           : {duty_name}")
    print("=" * 80)

    if not results:
        print("No matching data found. Check voltage, duty and database content.")
        return

    for i, r in enumerate(results):
        mi  = r['motor_info']
        ach = r['achieved']
        ok  = "✓ PASS" if r['score'] >= 0 else "✗ FAIL"
        print(
            f"\n  #{i+1}  [{ok}]  Type={r['motor_type']}  "
            f"Ø{mi['diameter']:.0f} × {mi['length']:.0f} mm  "
            f"{int(mi['turns'])}T-{mi['connection']}  "
            f"(ID {r['motor_id']})"
        )
        if ach:
            t_pct = ach['torque'] / target_torque * 100 if target_torque else 0
            p_pct = ach['power']  / target_power  * 100 if target_power  else 0
            print(
                f"        Torque = {ach['torque']:.2f} Nm ({t_pct:.0f}% of target)  |  "
                f"Power = {ach['power']:.3f} kW ({p_pct:.0f}% of target)  |  "
                f"Eff = {ach['efficiency']:.1f}%  |  J = {r['current_density']} A/mm²  |  "
                f"Score = {r['score']:.4f}"
            )
        else:
            ach_speed = r['achieved']['max_speed'] if r['achieved'] else 0
            print(f"        Speed exceeds motor range (max {ach_speed:.0f} rpm)")
    print()


# =============================================================================
# OUTPUT — chart
# =============================================================================

def plot_results(results, target_torque, target_power, target_speed,
                 voltage, duty_name, output_path=None):
    """
    Build a two-panel figure:
      Left  — normalised bar chart (% of target) for torque and power
      Right — specification table
    """
    if not results:
        return

    n = len(results)

    # ── labels ────────────────────────────────────────────────────────────────
    short_labels = []
    for i, r in enumerate(results):
        mi = r['motor_info']
        short_labels.append(
            f"#{i+1}  {r['motor_type']}\n"
            f"Ø{int(mi['diameter'])}×{int(mi['length'])} mm  "
            f"{int(mi['turns'])}T-{mi['connection']}"
        )

    fig_h = max(7, n * 1.8 + 3)
    fig = plt.figure(figsize=(20, fig_h))
    gs  = gridspec.GridSpec(1, 2, width_ratios=[2, 3], figure=fig,
                            left=0.04, right=0.98, wspace=0.08)

    ax_bar   = fig.add_subplot(gs[0])
    ax_table = fig.add_subplot(gs[1])
    ax_table.axis('off')

    # ── normalised values (% of target) ───────────────────────────────────────
    t_pct = []
    p_pct = []
    for r in results:
        ach = r['achieved']
        t_pct.append(ach['torque'] / target_torque * 100 if (ach and target_torque) else 0)
        p_pct.append(ach['power']  / target_power  * 100 if (ach and target_power)  else 0)

    bar_h  = 0.35
    y_pos  = np.arange(n)
    colors = [RANK_COLORS[i % len(RANK_COLORS)] for i in range(n)]

    # torque bars
    bars_t = ax_bar.barh(
        y_pos + bar_h / 2, t_pct, bar_h,
        color=[c + 'cc' for c in colors],          # slightly transparent
        edgecolor=colors, linewidth=1.2,
        label='Torque  (% of target)'
    )
    # power bars
    bars_p = ax_bar.barh(
        y_pos - bar_h / 2, p_pct, bar_h,
        color=[c + '66' for c in colors],          # more transparent
        edgecolor=colors, linewidth=1.2, hatch='//',
        label='Power  (% of target)'
    )

    # 100 % target line
    ax_bar.axvline(100, color='black', linestyle='--', linewidth=1.5, label='Target  (100 %)')

    # value annotations
    for bar, val in zip(bars_t, t_pct):
        ax_bar.text(bar.get_width() + 1.5, bar.get_y() + bar.get_height() / 2,
                    f'{val:.0f}%', va='center', ha='left', fontsize=8)
    for bar, val in zip(bars_p, p_pct):
        ax_bar.text(bar.get_width() + 1.5, bar.get_y() + bar.get_height() / 2,
                    f'{val:.0f}%', va='center', ha='left', fontsize=8)

    ax_bar.set_yticks(y_pos)
    ax_bar.set_yticklabels(short_labels, fontsize=8)
    ax_bar.invert_yaxis()
    ax_bar.set_xlabel('Achievement  [% of target]', fontsize=10)
    ax_bar.set_title(
        f'Performance @ {target_speed:.0f} rpm  —  {duty_name}  @  {voltage:.0f} V',
        fontsize=11, fontweight='bold'
    )
    ax_bar.legend(fontsize=8, loc='lower right')
    ax_bar.grid(axis='x', alpha=0.3, linestyle='--')

    # ── specification table ────────────────────────────────────────────────────
    col_labels = [
        'Rank', 'DB\nID', 'Type', 'Ø [mm]', 'L [mm]', 'Turns', 'Conn.',
        'Torque\n[Nm]', 'Power\n[kW]', 'Eff.\n[%]', 'Current\n[Arms]', 'Score'
    ]
    table_rows = []
    cell_colors = []

    for i, r in enumerate(results):
        mi  = r['motor_info']
        ach = r['achieved']
        passing = r['score'] >= 0

        def _fmt(val, fmt):
            return (fmt % val) if val is not None else '—'

        row = [
            f"#{i+1}",
            str(r['motor_id']),
            r['motor_type'],
            f"{mi['diameter']:.0f}",
            f"{mi['length']:.0f}",
            f"{int(mi['turns'])}",
            mi['connection'],
            _fmt(ach['torque'],     '%.2f') if ach else '—',
            _fmt(ach['power'],      '%.3f') if ach else '—',
            _fmt(ach['efficiency'], '%.1f') if ach else '—',
            _fmt(ach['current'],    '%.2f') if ach else '—',
            f"{r['score']:.4f}",
        ]
        table_rows.append(row)

        base_c = '#f0f7ff' if i % 2 == 0 else '#ffffff'
        pass_c = '#d4edda' if passing else '#f8d7da'
        # 1 rank col (coloured) + 6 spec cols (neutral) + 5 perf/score cols (pass/fail)
        row_c  = [RANK_COLORS[i % len(RANK_COLORS)] + '44'] + [base_c] * 6 + [pass_c] * 5
        cell_colors.append(row_c)

    tbl = ax_table.table(
        cellText   = table_rows,
        colLabels  = col_labels,
        cellColours= cell_colors,
        cellLoc    = 'center',
        loc        = 'center',
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8.5)
    tbl.scale(1.0, 1.9)

    # style header row
    for j in range(len(col_labels)):
        cell = tbl[0, j]
        cell.set_facecolor(HEADER_COLOR)
        cell.set_text_props(color='white', fontweight='bold')

    ax_table.set_title('Motor Specifications & Achieved Values', fontsize=11,
                       fontweight='bold', pad=14)

    # legend: pass / fail
    legend_patches = [
        Patch(facecolor='#d4edda', edgecolor='gray', label='Meets target'),
        Patch(facecolor='#f8d7da', edgecolor='gray', label='Below target'),
    ]
    ax_table.legend(handles=legend_patches, loc='lower center',
                    bbox_to_anchor=(0.5, -0.02), ncol=2, fontsize=8,
                    framealpha=0.8)

    # ── super-title ───────────────────────────────────────────────────────────
    fig.suptitle(
        f"Motor Search  ·  Target: ≥ {target_torque:.2f} Nm  |  ≥ {target_power:.3f} kW  "
        f"|  @ {target_speed:.0f} rpm  |  {voltage:.0f} V  |  Duty: {duty_name}",
        fontsize=12, fontweight='bold', y=1.005
    )

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Chart saved to: {output_path}")
    else:
        # When run non-interactively, always save next to this script
        default_out = os.path.join(os.path.dirname(__file__), 'motor_search_result.png')
        plt.savefig(default_out, dpi=150, bbox_inches='tight')
        print(f"Chart saved to: {default_out}")

    plt.close(fig)


# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description=(
            'Find best matching motors from the simulation database.\n'
            'Supply any TWO of --torque / --power / --speed; '
            'the third is derived via P = T·ω.\n'
            'If all three are given but inconsistent, the first two in argv order are used.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--torque',   type=float, default=None,
                        help='Minimum required shaft torque [Nm]')
    parser.add_argument('--power',    type=float, default=None,
                        help='Minimum required shaft power [kW]')
    parser.add_argument('--speed',    type=float, default=None,
                        help='Operating speed [rpm]')
    parser.add_argument('--voltage',  type=float, required=True,
                        help='Battery / DC bus voltage [V]')
    parser.add_argument('--duty',     type=str,   required=True,
                        help='Duty cycle label, e.g.  S1  S2-5min  S2-20min')
    parser.add_argument('--top',      type=int,   default=5,
                        help='Number of top results to show')
    parser.add_argument('--db',       type=str,   default=None,
                        help='Override path to the SQLite database')
    parser.add_argument('--output',   type=str,   default=None,
                        help='Save chart to this file path (PNG/PDF/SVG)')
    parser.add_argument('--config',   type=str,   default=None,
                        help='Override path to motor_types_config.json')

    args = parser.parse_args()
    cfg_path = args.config or CONFIG_FILE

    # ── resolve / derive the third target from the two given ──────────────────
    try:
        torque, power, speed, note = resolve_targets(
            args.torque, args.power, args.speed, sys.argv
        )
    except ValueError as exc:
        parser.error(str(exc))

    print(f"\nSearching database for motors matching:")
    if note:
        print(f"  NOTE: {note}")
    print(f"  Torque  ≥ {torque:.2f} Nm")
    print(f"  Power   ≥ {power:.3f} kW")
    print(f"  Speed      {speed:.0f} rpm")
    print(f"  Voltage    {args.voltage:.0f} V")
    print(f"  Duty       {args.duty}")
    print(f"  Top        {args.top} results\n")

    results = search_motors(
        target_torque = torque,
        target_power  = power,
        target_speed  = speed,
        voltage       = args.voltage,
        duty_name     = args.duty,
        db_path       = args.db,
        config_path   = cfg_path,
        top_n         = args.top,
    )

    print_results(results, torque, power, speed, args.duty, note=note)

    plot_results(
        results       = results,
        target_torque = torque,
        target_power  = power,
        target_speed  = speed,
        voltage       = args.voltage,
        duty_name     = args.duty,
        output_path   = args.output,
    )


if __name__ == '__main__':
    main()
