"""English release adaptation of the archived read-only panel verifier. Checks arithmetic, schedules, code/data identities and recorded closure; no MILP calls. The two archival Turkish prose files are not distributed or hash-checked; frozen code and data are checked unchanged."""
from pathlib import Path
from decimal import Decimal
import csv,json,hashlib,math

KS=[1,3,4,7,8,9,10,11,12,13,14,15,16,18]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def nondominated(points):
    return {p for p in points if not any(q!=p and q[0]<=p[0] and q[1]<=p[1] for q in points)}
def verify(root):
    root=Path(root)
    frozen=json.loads((root/'validated_runner/FROZEN_SHA256.json').read_text())
    for n,h in frozen.items():
        if n in ('VERIMLI_ROTASYON_PROTOKOL_V1_1_TR.md','validated_runner/IMPLEMENTATION_FREEZE_TR.md'):
            continue  # Prose-only archival files intentionally omitted from this English release.
        assert sha(root/n)==h,n
    source=json.loads((root/'standard_data_audit/DATA_QA.json').read_text())
    published=json.loads((root/'project_sources/PUBLISHED_SUMMARY.json').read_text())
    assert sha(root/published['path_relative_to_panel'])==published['sha256']
    assert published['historical_source_sha256']==source['source_sha256']
    for name,h in source['outputs_sha256'].items():
        assert sha(root/'standard_data_audit'/name)==h,name
    def read(p):return list(csv.reader((root/p).open()))[1:]
    station_p=[[int(Decimal(v)*10) for v in row[1:]] for row in read('standard_data_audit/processing_times_standard_1decimal.csv')]
    P=list(map(list,zip(*station_p)));R=[int(Decimal(row[1])*10) for row in read('standard_data_audit/reba_standard.csv')]
    assert len(P)==len(R)==18
    all_records=[];witnesses=0;calls=0;baseline=None;common_env=None
    for k in KS:
        pairs={}
        for reg in ['M','P']:
            folder=root/f'official_k{k:02d}_{reg}'
            r=json.loads((folder/'result.json').read_text());t=json.loads((folder/'timing.json').read_text());e=json.loads((folder/'environment.json').read_text())
            assert r['k']==t['k']==k and r['regime']==t['regime']==reg
            assert t['exit_code']==0 and t['time_limit'] is None and t['T_total']>0 and t['affinity']==[0]
            assert t['launcher_sha256']==frozen['validated_runner/launch.py']
            assert abs((t['end_utc']-t['start_utc'])-t['T_total'])<.01
            ids=(r['source_code_sha256'],r['data_sha256'],r['base_model_sha256'])
            if baseline is None:baseline=ids;common_env=e
            assert ids==baseline and e==common_env,(k,reg,'identity/environment mismatch')
            for name,h in r['source_code_sha256'].items():assert sha(root/'validated_runner'/name)==h
            for name,h in r['data_sha256'].items():assert sha(root/'standard_data_audit'/name)==h
            assert e['options']['threads']==1 and e['options']['random_seed']==20261019
            assert r['milp_calls']==len(r['calls'])
            for i,c in enumerate(r['calls'],1):
                assert c['call']==i and c['status'] in (0,2)
                if c['status']==0:assert c['gap'] is not None and c['gap']<=1e-9
            assert math.isclose(sum(c['seconds'] for c in r['calls']),r['solver_seconds'],abs_tol=1e-8)
            assert r['closure'] in ('remaining objective box infeasible','nonnegative D lower bound reached')
            clsset=set()
            for p in r['points']:
                q=p['counts'];sch=p['schedule_station_by_worker_period'];assert p['station_index_base']==1
                assert len(q)==len(sch)==18 and all(len(row)==18 for row in q+sch)
                assert all(isinstance(v,int) and v>=0 for row in q for v in row)
                assert all(sum(row)==18 for row in q)
                assert all(sum(q[i][j] for i in range(18))==18 for j in range(18))
                achieved=min(sum(v>0 for v in row) for row in q);assert achieved==p['Smin_actual'] and achieved>=k
                rebuilt=[[0]*18 for _ in range(18)]
                for period in range(18):
                    assert sorted(sch[i][period] for i in range(18))==list(range(1,19))
                    for i in range(18):rebuilt[i][sch[i][period]-1]+=1
                assert rebuilt==q
                c=max(P[i][j] for i in range(18) for j in range(18) if q[i][j])
                loads=[sum(q[i][j]*R[j] for j in range(18)) for i in range(18)];d=max(loads)-min(loads)
                assert (c,d)==(p['C10'],p['Dsum'])
                assert abs(p['C']-c/10)<1e-12 and abs(p['D']-d/180)<1e-12
                cl=(c,d) if reg=='M' else ((2*c+5)//10,(2*d+18)//36)
                assert cl==(p['class_C'],p['class_D']) and cl not in clsset;clsset.add(cl)
                witnesses+=1
            assert clsset==nondominated(clsset)
            if r['closure']=='nonnegative D lower bound reached':assert min(p['class_D'] for p in r['points'])==0
            events=[json.loads(x) for x in (folder/'events.jsonl').read_text().splitlines()]
            assert sum(x['event']=='call_end' for x in events)==r['milp_calls']
            assert sum(x['event']=='point' for x in events)==len(r['points'])
            if t['T_total']>=300:assert (folder/'checkpoint_000300.json').is_file()
            calls+=r['milp_calls'];pairs[reg]=(r,t)
            all_records.append(dict(k=k,regime=reg,status='PASS',points=len(r['points']),milp_calls=r['milp_calls'],T_total=t['T_total']))
        m,mt=pairs['M'];p,pt=pairs['P']
        projection=nondominated({((2*x['C10']+5)//10,(2*x['Dsum']+18)//36) for x in m['points']})
        assert projection=={(x['class_C'],x['class_D']) for x in p['points']}
        raw_m={(x['C10'],x['Dsum']) for x in m['points']}
        assert all((x['C10'],x['Dsum']) in raw_m for x in p['points'])
        first,second=(mt,pt) if k%2 else (pt,mt)
        assert first['end_utc']<=second['start_utc']
    return dict(status='PASS',completed_layers=KS,layers_outside_this_timing_panel=[2,5,6,17],runs=len(all_records),witnesses=witnesses,milp_calls=calls,records=all_records,
                scope='No solver runs. Checks recorded identities, optimal/infeasible closure records, arithmetic and all schedules. Does not independently prove MILP dual certificates or source-fidelity to published DPA.')

if __name__=='__main__':
    import sys
    report=verify(Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'03_REPRODUCIBILITY/PANEL14_V1_1')
    if len(sys.argv)>2:Path(sys.argv[2]).write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
