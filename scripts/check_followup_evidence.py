"""Check the archived follow-up cap coverage, terminal states and audit values.
This is an evidence consistency check, not an independent solver proof.
"""
from pathlib import Path
from decimal import Decimal
import csv,json,sys
ROOT=Path(__file__).resolve().parents[1];E=ROOT/'03_REPRODUCIBILITY'
rows=list(csv.reader((E/'PANEL14_V1_1/standard_data_audit/processing_times_standard_1decimal.csv').open()))[1:]
P=list(zip(*[[int(Decimal(x)*10) for x in r[1:]] for r in rows]))
report=[]
for k in [2,5,6]:
    pair=next((E/f'K{k:02d}_V2_1/RUNS').glob('*'))
    lower=max(sorted(row)[k-1] for row in P)
    for reg in ['M','P']:
        r=json.loads((pair/reg/'result.json').read_text())
        cl=lambda c:c if reg=='M' else (2*c+5)//10
        expected={cl(c) for row in P for c in row if cl(c)>=cl(lower)}
        closed={x['class_C_cap'] for x in r['closed']};unresolved={x['class_C_cap'] for x in r['unresolved']}
        assert len(closed)==len(r['closed']) and len(unresolved)==len(r['unresolved'])
        assert not closed&unresolved and closed|unresolved==expected and not r['pending']
        assert all(c['optimal'] or c['infeasible'] for c in r['calls'])
        if k==2 and reg=='M':
            assert unresolved=={759,760,763,764,770}
            assert {c for c in expected if c<=715}<=closed
            assert any((w['C10'],w['Dsum'])==(715,0) for w in r['points'])
        if k==5:
            assert unresolved==({692} if reg=='M' else {138})
            audit=json.loads((E/'K05_V2_1/K05_DELIVERY/K05_TARGETED_AUDIT_2026-10-22/K5_CAP692_TARGETED_AUDIT.json').read_text())['regimes'][reg]
            for key,v in [('fresh_presolve_off_C_minimization',691),('fresh_presolve_off_D_tie_break',67)]:
                a=audit[key];assert a['success'] and a['mip_gap']==0 and abs(a['mip_dual_bound']-v)<1e-7
                assert a['full_model_qa']['passes']
        if k==6:assert r['complete'] and not unresolved
        events=[json.loads(line) for line in (pair/reg/'events.jsonl').read_text().splitlines()]
        report.append({'k':k,'regime':reg,'raw_complete':r['complete'],'processed_caps':len(expected),'closed_caps':len(closed),'unresolved_caps':len(unresolved),'full_call_array_length':len(r['calls']),'retained_call_end_events':sum(x['event']=='call_end' for x in events),'status':'PASS'})
result={'status':'PASS','runs':report,'note':'Partial event logs are retained unchanged; full call arrays remain in result.json and state.json.'}
if len(sys.argv)>1:Path(sys.argv[1]).write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
