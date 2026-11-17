"""Independent targeted audit for the K5 V2.1 cap=692 contradiction.
Uses a fresh aggregated model through scipy.optimize.milp with HiGHS presolve OFF.
It never edits the official M/P state.json or result.json files.
"""
import json, sys, time, hashlib, warnings
from pathlib import Path
import numpy as np, scipy
from scipy.optimize import OptimizeResult

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / 'bounded_region_v2'
RUNS = ROOT / 'RUNS' / 'bounded_v2_1_k05_PAIR_20261021'
sys.path.insert(0, str(MODEL_DIR))
from runner import Model, load_data, cls, qa
from legacy_model import SolveConfig

class AuditConfig(SolveConfig):
    def __init__(self, presolve):
        super().__init__(time_limit=2400, mip_rel_gap=0.0, presolve=presolve)
        self._presolve = presolve
    def scipy_options(self):
        return {
            'disp': False, 'presolve': self._presolve, 'mip_rel_gap': 0.0,
            'time_limit': 2400.0, 'mip_abs_gap': 0.0, 'threads': 1,
            'random_seed': 20261019,
            'mip_feasibility_tolerance': 1e-7,
            'primal_feasibility_tolerance': 1e-7,
            'dual_feasibility_tolerance': 1e-7,
        }

P, R = load_data()
results = {
    'audit': 'K5 V2.1 targeted cap=692 recheck',
    'date': '2026-10-22',
    'scope': 'M/P unresolved boundary only; not a replacement for official run',
    'input_sha256': {
        'processing_times_standard_1decimal.csv': hashlib.sha256((ROOT/'standard_data_audit/processing_times_standard_1decimal.csv').read_bytes()).hexdigest(),
        'reba_standard.csv': hashlib.sha256((ROOT/'standard_data_audit/reba_standard.csv').read_bytes()).hexdigest(),
    },
    'solver': {'scipy': scipy.__version__, 'backend': 'SciPy milp / HiGHS', 'presolve': False,
               'mip_rel_gap': 0.0, 'time_limit_seconds_per_call': 2400,
               'threads': 1, 'seed': 20261019},
    'regimes': {}
}
def result_summary(sol, elapsed):
    raw = sol.raw
    return {
        'status': sol.status, 'success': sol.success, 'message': sol.message,
        'seconds': elapsed,
        'objective': getattr(raw, 'fun', None),
        'mip_gap': getattr(raw, 'mip_gap', None),
        'mip_node_count': getattr(raw, 'mip_node_count', None),
        'mip_dual_bound': getattr(raw, 'mip_dual_bound', None),
    }

def verify_witness(m, w, ccap, dcap, ceq=None):
    q = np.asarray(w['counts'], dtype=int)
    z = np.zeros(m.nvar)
    z[:m.nq] = q.ravel()
    z[m.nq:m.nq+m.ny] = (q>0).ravel()
    loads = q @ m.R
    z[m.idx_C] = w['C10']
    z[m.idx_E0:m.idx_E0+m.n] = loads
    z[m.idx_Emax] = loads.max(); z[m.idx_Emin] = loads.min()
    z[m.idx_D] = loads.max()-loads.min()
    z[m.idx_Smin] = (q>0).sum(axis=1).min()
    rows = m._A @ z
    row_violation = float(max(np.max(m._lb-rows), np.max(rows-m._ub), 0.0))
    extra_violation = float(max(5-z[m.idx_Smin], z[m.idx_C]-ccap,
                                z[m.idx_D]-dcap,
                                abs(z[m.idx_C]-ceq) if ceq is not None else 0.0,
                                0.0))
    integ = float(np.max(np.abs(z[m._integrality>0]-np.rint(z[m._integrality>0]))))
    return {'max_base_row_violation': row_violation,
            'max_region_violation': extra_violation,
            'integrality_max_error': integ,
            'passes': row_violation < 1e-7 and extra_violation < 1e-7 and integ < 1e-7}

for regime, dcap in [('M', 67), ('P', 80)]:
    state = json.loads((RUNS/regime/'state.json').read_text())
    dcall = next(c for c in state['calls'] if c.get('objective')=='D' and c.get('witness',{}).get('C10')==692 and c.get('witness',{}).get('Dsum')==67)
    oldw = dcall['witness']
    m0 = Model(P,R)
    q = np.asarray(oldw['counts'], dtype=int)
    z = np.zeros(m0.nvar)
    z[:m0.nq] = q.ravel()
    z[m0.nq:m0.nq+m0.ny] = (q>0).ravel()
    loads = q @ m0.R
    z[m0.idx_C] = oldw['C10']
    z[m0.idx_E0:m0.idx_E0+m0.n] = loads
    z[m0.idx_Emax] = loads.max(); z[m0.idx_Emin] = loads.min()
    z[m0.idx_D] = loads.max()-loads.min()
    z[m0.idx_Smin] = (q>0).sum(axis=1).min()
    base = m0._A @ z
    max_base_violation = float(max(np.max(m0._lb-base), np.max(base-m0._ub), 0.0))
    max_extra_violation = float(max(5-z[m0.idx_Smin], z[m0.idx_C]-692, z[m0.idx_D]-dcap, 0.0))
    old_witness_check = {
        'source_call_status': dcall['status'], 'source_call_optimal': dcall['optimal'],
        'C10': int(oldw['C10']), 'Dsum': int(oldw['Dsum']),
        'max_base_row_violation': max_base_violation,
        'max_region_violation': max_extra_violation,
        'integrality_max_error': float(np.max(np.abs(z[m0._integrality>0]-np.rint(z[m0._integrality>0])))),
        'passes': max_base_violation < 1e-7 and max_extra_violation < 1e-7,
    }
    assert old_witness_check['passes']

    # Reproduce the status flip with the same high-level API and fresh models.
    m_on = Model(P,R)
    on_extra = [m_on.smin_ge(5), m_on.c_le(692), m_on.d_le(dcap)]
    t_on = time.perf_counter()
    on_sol = m_on.solve_objective('C', on_extra, AuditConfig(presolve=True))
    on_seconds = time.perf_counter()-t_on
    on_result = result_summary(on_sol, on_seconds)

    m = Model(P,R)
    common = [m.smin_ge(5), m.c_le(692), m.d_le(dcap)]
    t0 = time.perf_counter()
    csol = m.solve_objective('C', common, AuditConfig(presolve=False))
    c_seconds = time.perf_counter()-t0
    c_result = result_summary(csol, c_seconds)
    if csol.success:
        cw = qa(m, csol, 5)
        c_check = verify_witness(m, cw, 692, dcap)
        assert c_check['passes']
        c_result.update({'C10': cw['C10'], 'Dsum': cw['Dsum'], 'Smin_actual': cw['Smin_actual'],
                         'counts': cw['counts'], 'schedule': cw['schedule_station_by_worker_period'],
                         'full_model_qa': c_check})
        m2 = Model(P,R)
        tie = [m2.smin_ge(5), m2.c_eq(cw['C10']), m2.d_le(dcap)]
        t1 = time.perf_counter()
        dsol = m2.solve_objective('D', tie, AuditConfig(presolve=False))
        d_seconds = time.perf_counter()-t1
        d_result = result_summary(dsol, d_seconds)
        if dsol.success:
            dw = qa(m2, dsol, 5)
            d_check = verify_witness(m2, dw, 692, dcap, ceq=cw['C10'])
            assert d_check['passes']
            d_result.update({'C10': dw['C10'], 'Dsum': dw['Dsum'], 'Smin_actual': dw['Smin_actual'],
                             'counts': dw['counts'], 'schedule': dw['schedule_station_by_worker_period'],
                             'full_model_qa': d_check})
            assert dw['C10'] == cw['C10']
    else:
        d_result = None
    results['regimes'][regime] = {
        'region': {'k': 5, 'C10_cap': 692, 'Dsum_cap': dcap, 'Smin_min': 5},
        'prior_D_optimum_witness_rechecked': old_witness_check,
        'presolve_on_C_call_reproduction': on_result,
        'fresh_presolve_off_C_minimization': c_result,
        'fresh_presolve_off_D_tie_break': d_result,
        'frontier_region_closed_by_targeted_audit': bool(csol.success and d_result and d_result['success']),
    }
    assert results['regimes'][regime]['frontier_region_closed_by_targeted_audit']
out = Path(__file__).with_name('K5_CAP692_TARGETED_AUDIT.json')
out.write_text(json.dumps(results, indent=2))
print(json.dumps({r:{'C':v['fresh_presolve_off_C_minimization'].get('C10'),
                     'D':(v['fresh_presolve_off_D_tie_break'] or {}).get('Dsum'),
                     'secs_C':v['fresh_presolve_off_C_minimization']['seconds'],
                     'secs_D':(v['fresh_presolve_off_D_tie_break'] or {}).get('seconds'),
                     'closed':v['frontier_region_closed_by_targeted_audit']}
                  for r,v in results['regimes'].items()}, indent=2))
print('saved', out)
