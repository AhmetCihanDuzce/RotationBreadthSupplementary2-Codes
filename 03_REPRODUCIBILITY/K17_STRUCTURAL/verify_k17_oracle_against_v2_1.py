"""Cross-check the existing K17 structural oracle witnesses against frozen V2.1 data/model."""
from pathlib import Path
from types import SimpleNamespace
import json, hashlib, sys
import numpy as np
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'bounded_region_v2'))
from runner import Model, load_data, qa, cls
P,R=load_data(); m=Model(P,R)
ref=json.loads((ROOT/'K17_INDEPENDENT_ORACLE/EXACT_REFERENCE.json').read_text())
original=json.loads((ROOT/'K17_INDEPENDENT_ORACLE/EXACT_REFERENCE_2026-10-20.json').read_text())
expected_hashes={
 'processing_times_standard_1decimal.csv':hashlib.sha256((ROOT/'standard_data_audit/processing_times_standard_1decimal.csv').read_bytes()).hexdigest(),
 'reba_standard.csv':hashlib.sha256((ROOT/'standard_data_audit/reba_standard.csv').read_bytes()).hexdigest(),
}
assert ref['data_sha256']==expected_hashes
assert original['data_sha256']==expected_hashes
assert [(x['C10'],x['Dsum']) for x in ref['M_points']]==[(768,8),(771,2),(775,0)]
assert [(x['C10'],x['Dsum']) for x in original['M_points']]==[(768,8),(771,2),(775,0)]
rows=[]
for point in ref['M_points']:
    q=np.asarray(point['counts'],dtype=int)
    got=qa(m,SimpleNamespace(counts=q),17)
    assert (got['C10'],got['Dsum'])==(point['C10'],point['Dsum'])
    assert got['Smin_actual']>=17
    oracle_schedule=np.asarray(point['schedule'],dtype=int)
    assert oracle_schedule.shape==(18,18)
    oracle_counts=np.zeros((18,18),dtype=int)
    for worker in range(18):
        for station in oracle_schedule[worker]: oracle_counts[worker,station-1]+=1
    assert np.array_equal(oracle_counts,q)
    for t in range(18): assert sorted(oracle_schedule[:,t].tolist())==list(range(1,19))
    z=np.zeros(m.nvar);z[:m.nq]=q.ravel();z[m.nq:m.nq+m.ny]=(q>0).ravel()
    loads=q@m.R;z[m.idx_C]=got['C10'];z[m.idx_E0:m.idx_E0+m.n]=loads
    z[m.idx_Emax]=loads.max();z[m.idx_Emin]=loads.min();z[m.idx_D]=loads.max()-loads.min();z[m.idx_Smin]=got['Smin_actual']
    ax=m._A@z
    violation=float(max(np.max(m._lb-ax),np.max(ax-m._ub),0.0))
    integ=float(np.max(np.abs(z[m._integrality>0]-np.rint(z[m._integrality>0]))))
    assert violation<1e-7 and integ<1e-7
    rows.append({'C10':got['C10'],'Dsum':got['Dsum'],'D_fraction':point['D_fraction'],
                 'Smin_actual':got['Smin_actual'],'base_model_max_row_violation':violation,
                 'integrality_max_error':integ,'oracle_18_period_schedule_valid':True,'independent_decomposition_schedule_valid':True,'qa':'PASS'})
assert [cls(x['C10'],x['Dsum'],18,'P') for x in ref['M_points']]==[(154,0),(154,0),(155,0)]
assert ref['P_class_indices']==[[154,0]]
assert ref['P_representative_C10_Dsum']==[768,8]
# Structural premises in the proof, checked against the exact input arrays.
assert max(sorted(row)[-2] for row in P)==768
assert int(P[7,7])==771 and int(R[7])==57 and list(R).count(57)==1
assert max(int(v) for v in R if v<57)==52 and min(int(v) for v in R if v>57)==61
assert int(P[1,13])==775 and int(R[13])==52 and list(R).count(52)==1
out={'status':'PASS_K17_ORACLE_MATCHED_TO_FROZEN_V2_1_DATA_AND_MODEL',
     'oracle_status':ref['status'],'data_sha256':expected_hashes,
     'same_points_in_regenerated_and_archived_oracle':True,
     'witnesses_revalidated_against_v2_1_model':rows,
     'practical_P_class_indices':ref['P_class_indices'],
     'practical_P_representative_C10_Dsum':ref['P_representative_C10_Dsum'],
     'structural_bound_premises_checked':True,
     'timed_M_P_run_status':'separate; not closed by this oracle'}
(ROOT/'K17_V2_1_ORACLE_QA.json').write_text(json.dumps(out,indent=2))
print(json.dumps({'status':out['status'],'points':[(r['C10'],r['Dsum']) for r in rows],
                  'full_model_QA':[r['qa'] for r in rows],'P_class':ref['P_class_indices']},indent=2))
