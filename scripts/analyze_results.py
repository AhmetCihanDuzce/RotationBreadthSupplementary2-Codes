"""Rebuild manuscript tables and figures from retained results, without solving a MILP.
Run from any directory; requires numpy and matplotlib. Integer arithmetic is used
for objective verification and dominance. Raw run files are never overwritten.
"""
from pathlib import Path
import json, csv, hashlib
from fractions import Fraction
from decimal import Decimal
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parents[1]
import argparse
parser = argparse.ArgumentParser(description='Verify archived results and regenerate English tables and figures; no MILP calls.')
parser.add_argument('--output', type=Path, default=ROOT / 'reproduced_analysis')
args = parser.parse_args()
E = ROOT / '03_REPRODUCIBILITY'
O = args.output.resolve()
O.mkdir(parents=True, exist_ok=True)

def read(p):
    return json.loads(p.read_text())

def write(name, rows):
    with (O / name).open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

def nd(points):
    points = set(points)
    return sorted((p for p in points if not any((q != p and all((x <= y for x, y in zip(q, p))) for q in points))))

def cls(c, d):
    return ((2 * c + 5) // 10, (2 * d + 18) // 36)
data = E / 'PANEL14_V1_1/standard_data_audit'
p_rows = list(csv.reader((data / 'processing_times_standard_1decimal.csv').open()))[1:]
r_rows = list(csv.reader((data / 'reba_standard.csv').open()))[1:]
P = np.array([[int(Decimal(x) * 10) for x in r[1:]] for r in p_rows]).T
R = np.array([int(Decimal(r[1]) * 10) for r in r_rows])

def qa(w, k):
    q = np.array(w['counts'])
    assert np.issubdtype(q.dtype, np.integer)
    assert np.all(q >= 0) and np.all(q.sum(0) == 18) and np.all(q.sum(1) == 18)
    assert int((q > 0).sum(1).min()) >= k
    loads = q @ R
    assert int(P[q > 0].max()) == w['C10'] and int(loads.max() - loads.min()) == w['Dsum']
    sch = np.array(w.get('schedule_station_by_worker_period', w.get('schedule')))
    assert sch.shape == (18, 18) and np.all((sch >= 1) & (sch <= 18))
    assert all((sorted(sch[:, t]) == list(range(1, 19)) for t in range(18)))
    q2 = np.array([[int(np.sum(sch[i] == j + 1)) for j in range(18)] for i in range(18)])
    assert np.array_equal(q, q2)
    return int((q > 0).sum(1).min())
panel = [1, 3, 4, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 18]
fronts = {}
timings = []
provenance = []
witnesses = []
for k in range(1, 19):
    fronts[k] = {}
    for reg in ['M', 'P']:
        if k in panel:
            run = E / 'PANEL14_V1_1' / f'official_k{k:02d}_{reg}'
            result = read(run / 'result.json')
            points = result['points']
            method = 'V1.1 complete'
        elif k != 17:
            run = next((E / f'K{k:02d}_V2_1/RUNS').glob('*')) / reg
            result = read(run / 'result.json')
            points = result['points']
            method = 'V2.1 complete' if k == 6 else 'V2.1 plus dominance closure' if k == 2 else 'V2.1 plus targeted presolve-off audit'
            if k == 5 and reg == 'P':
                ap = E / 'K05_V2_1/K05_DELIVERY/K05_TARGETED_AUDIT_2026-10-22/K5_CAP692_TARGETED_AUDIT.json'
                correction = read(ap)['regimes']['P']['fresh_presolve_off_D_tie_break']
                assert (correction['C10'], correction['Dsum']) == (691, 67)
                points = [correction if cls(w['C10'], w['Dsum']) == (138, 4) else w for w in points]
        else:
            run = E / 'K17_STRUCTURAL/K17_INDEPENDENT_ORACLE'
            result = read(run / 'EXACT_REFERENCE.json')
            points = result['M_points'] if reg == 'M' else [result['M_points'][0]]
            method = 'Structural lower bounds and attaining witnesses'
        fronts[k][reg] = points
        for w in points:
            s = qa(w, k)
            c, d = (w['C10'], w['Dsum'])
            bc, bd = cls(c, d)
            source = ap if k == 5 and reg == 'P' and ((c, d) == (691, 67)) else run
            provenance.append(dict(k=k, regime=reg, C10=c, Dsum=d, C_seconds=c / 10, D_fraction=str(Fraction(d, 180)), D=d / 180, class_C=bc, class_D=bd, C_label=bc / 2, D_label=bd / 10, Smin_witness=s, closure_basis=method, source=str(source.relative_to(ROOT))))
            witnesses.append(dict(k=k, regime=reg, **w))
        if k in panel:
            ti = read(run / 'timing.json')
            timings.append(dict(k=k, regime=reg, T_total_s=ti['T_total'], MILP_calls=result['milp_calls']))
    projected = nd((cls(w['C10'], w['Dsum']) for w in fronts[k]['M']))
    observed = sorted((cls(w['C10'], w['Dsum']) for w in fronts[k]['P']))
    assert projected == observed, (k, projected, observed)
Gm = nd(((w['C10'], w['Dsum'], -k) for k in fronts for w in fronts[k]['M']))
Gp = nd(((*cls(w['C10'], w['Dsum']), -k) for k in fronts for w in fronts[k]['P']))
assert nd(((*cls(c, d), s) for c, d, s in Gm)) == Gp
assert len(Gm) == 28 and len(Gp) == 17 and (len(provenance) == 68)
gmrows = [dict(k=-s, C10=c, Dsum=d, C_seconds=c / 10, D_fraction=str(Fraction(d, 180)), D=d / 180, retained_as_P_representative=any((cls(w['C10'], w['Dsum']) == cls(c, d) and (w['C10'], w['Dsum']) == (c, d) and ((*cls(c, d), s) in Gp) for w in fronts[-s]['P']))) for c, d, s in Gm]
gprows = []
for bc, bd, s in Gp:
    w = next((w for w in fronts[-s]['P'] if cls(w['C10'], w['Dsum']) == (bc, bd)))
    assert (w['C10'], w['Dsum'], s) in Gm
    gprows.append(dict(k=-s, class_C=bc, class_D=bd, C_label=bc / 2, D_label=bd / 10, C10=w['C10'], Dsum=w['Dsum'], C_seconds=w['C10'] / 10, D_fraction=str(Fraction(w['Dsum'], 180)), D=w['Dsum'] / 180))
layers = []
for k in fronts:
    m = sorted(fronts[k]['M'], key=lambda w: (w['C10'], w['Dsum']))
    eq = min((w['C10'] for w in m if w['Dsum'] == 0))
    layers.append(dict(k=k, M_points=len(m), P_classes=len(fronts[k]['P']), Cmin_s=m[0]['C10'] / 10, D_at_Cmin_fraction=str(Fraction(m[0]['Dsum'], 180)), C_at_D0_s=eq / 10, timing_in_primary_panel=k in panel))
paired = []
for k in panel:
    m = next((t for t in timings if t['k'] == k and t['regime'] == 'M'))
    p = next((t for t in timings if t['k'] == k and t['regime'] == 'P'))
    paired.append(dict(k=k, M_total_s=m['T_total_s'], P_total_s=p['T_total_s'], M_calls=m['MILP_calls'], P_calls=p['MILP_calls'], M_over_P=m['T_total_s'] / p['T_total_s']))
tm = sum((r['M_total_s'] for r in paired))
tp = sum((r['P_total_s'] for r in paired))
metrics = dict(M_layer_records=sum((r['M_points'] for r in layers)), P_layer_records=sum((r['P_classes'] for r in layers)), M_global=len(Gm), P_global=len(Gp), global_reduction_pct=100 * (1 - len(Gp) / len(Gm)), layer_reduction_pct=100 * (1 - 30 / 38), panel_M_points=25, panel_P_classes=21, panel_M_calls=sum((r['M_calls'] for r in paired)), panel_P_calls=sum((r['P_calls'] for r in paired)), panel_M_s=tm, panel_P_s=tp, panel_time_reduction_pct=100 * (1 - tp / tm), without_k16_P_increase_pct=100 * (sum((r['P_total_s'] for r in paired if r['k'] != 16)) / sum((r['M_total_s'] for r in paired if r['k'] != 16)) - 1), all68_witnesses_integer_and_schedule_QA='PASS', all18_projection_checks='PASS', global_projection_check='PASS', P_representatives_on_M_global='PASS', P_range_seconds=[P.min() / 10, P.max() / 10], R_range=[R.min() / 10, R.max() / 10])
write('S1_all18_layers.csv', layers)
write('S2_all68_layer_records.csv', provenance)
write('S3_global_M_28.csv', gmrows)
write('S4_global_P_17.csv', gprows)
write('S5_paired14_timing.csv', paired)
(O / 'METRICS_AND_QA.json').write_text(json.dumps(metrics, indent=2))
(O / 'SELECTED_WITNESSES.json').write_text(json.dumps(witnesses, indent=2))
followups = []
for k in [2, 5, 6]:
    run = next((E / f'K{k:02d}_V2_1/RUNS').glob('*'))
    for reg in ['M', 'P']:
        result = read(run / reg / 'result.json')
        ti = read(run / reg / 'timing.json')
        assert not result['pending']
        assert all((c['optimal'] or c['infeasible'] for c in result['calls']))
        if k == 2 and reg == 'M':
            assert result['complete'] is False and len(result['unresolved']) == 5
            assert all((r['C10_cap'] > 715 for r in result['unresolved']))
            assert any((w['C10'] == 715 and w['Dsum'] == 0 for w in result['points']))
        if k == 5:
            audit = read(E / 'K05_V2_1/K05_DELIVERY/K05_TARGETED_AUDIT_2026-10-22/K5_CAP692_TARGETED_AUDIT.json')['regimes'][reg]
            assert audit['frontier_region_closed_by_targeted_audit']
            for key, objective in [('fresh_presolve_off_C_minimization', 691), ('fresh_presolve_off_D_tie_break', 67)]:
                a = audit[key]
                assert a['success'] and a['mip_gap'] == 0 and (abs(a['mip_dual_bound'] - objective) < 1e-06)
        if k == 6:
            assert result['complete']
        followups.append(dict(k=k, regime=reg, raw_complete=result['complete'], closed_caps=len(result['closed']), unresolved_caps=len(result['unresolved']), scalar_calls=len(result['calls']), optimal_calls=sum((c['optimal'] for c in result['calls'])), infeasible_calls=sum((c['infeasible'] for c in result['calls'])), longest_scalar_s=max((c['total_call_seconds'] for c in result['calls'])), original_elapsed_s=ti['T_total'], primary_timing_eligible=False))
write('S6_followup_run_status.csv', followups)
ids = {}
for directory in ['PANEL14_V1_1', 'K02_V2_1', 'K05_V2_1', 'K06_V2_1', 'K17_STRUCTURAL']:
    folder = E / directory
    model = 'validated_runner' if directory == 'PANEL14_V1_1' else 'bounded_region_v2'
    files = [folder / 'standard_data_audit' / n for n in ['processing_times_standard_1decimal.csv', 'reba_standard.csv']] + [folder / model / n for n in ['legacy_model.py', 'runner.py']]
    ids[directory] = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
assert all((value == ids['PANEL14_V1_1'] for value in ids.values()))
(O / 'COMMON_INPUT_AND_MODEL_HASHES.json').write_text(json.dumps(ids, indent=2))
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9, 'axes.spines.top': False, 'axes.spines.right': False, 'savefig.dpi': 230})
blue = '#24557A'
orange = '#CA642C'
for lang in ['EN']:
    fig, axes = plt.subplots(1, 2, figsize=(7.5, 3.3), layout='constrained')
    for ax, key, label in [(axes[0], 'C_seconds', 'Bottleneck time C (s)'), (axes[1], 'D', 'Score disparity D')]:
        ax.scatter([r['k'] for r in gmrows], [r[key] for r in gmrows], facecolors='none', edgecolors=blue, s=52, label='M (28)')
        ax.scatter([r['k'] for r in gprows], [r[key] for r in gprows], color=orange, marker='x', s=30, label='P representatives (17)')
        ax.set(xlabel='Minimum station coverage k', ylabel=label, xticks=[1, 3, 6, 9, 12, 15, 18])
        ax.grid(alpha=0.15)
    axes[0].legend(frameon=False)
    fig.savefig(O / f'Figure1_global_{lang}.png')
    plt.close(fig)
    fig, axes = plt.subplots(1, 3, figsize=(7.5, 2.7), layout='constrained')
    for ax, k in zip(axes, [3, 16, 17]):
        m = fronts[k]['M']
        p = fronts[k]['P']
        ax.plot([w['C10'] / 10 for w in m], [w['Dsum'] / 180 for w in m], '-o', color=blue, markersize=5, label='M')
        ax.scatter([w['C10'] / 10 for w in p], [w['Dsum'] / 180 for w in p], marker='x', s=55, color=orange, zorder=3, label='P representative')
        ax.set(title=f'k = {k}', xlabel='C (s)', ylabel='D')
        ax.grid(alpha=0.15)
    axes[0].legend(frameon=False)
    fig.savefig(O / f'Figure2_resolution_{lang}.png')
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(7.5, 3.3), layout='constrained')
    x = np.arange(len(paired))
    ax.bar(x - 0.18, [r['M_total_s'] for r in paired], width=0.36, color=blue, label='M')
    ax.bar(x + 0.18, [r['P_total_s'] for r in paired], width=0.36, color=orange, label='P')
    ax.set(yscale='log', xticks=x, xticklabels=panel, xlabel='Minimum station coverage k', ylabel='Total wall time (s), log scale')
    ax.legend(frameon=False, ncol=2, loc='lower left', bbox_to_anchor=(0, 1.01))
    ax.grid(axis='y', alpha=0.15)
    fig.savefig(O / f'Figure3_timing_{lang}.png')
    plt.close(fig)
print(json.dumps(metrics, indent=2))
