from bounded import *
import tempfile
import bounded

def main():
    records=[]
    with tempfile.TemporaryDirectory() as tmp:
        for seed,n in [(1,2),(2,3),(3,3),(4,3)]:
            rng=np.random.default_rng(seed);P=rng.integers(10,35,(n,n));R=rng.integers(1,9,n);m=Model(P,R)
            witnesses=[]
            for sch in itertools.product(list(itertools.permutations(range(n))),repeat=n):
                q=np.zeros((n,n),int)
                for period in sch:
                    for i,j in enumerate(period):q[i,j]+=1
                loads=q@R;witnesses.append((int(P[q>0].max()),int(loads.max()-loads.min()),int((q>0).sum(1).min())))
            for k in range(1,n+1):
                for reg in ['M','P']:
                    r=run(m,k,reg,Path(tmp)/f'{seed}_{k}_{reg}',5,5)
                    expected=nd({cls(c,d,n,reg) for c,d,s in witnesses if s>=k})
                    got={(p['class_C'],p['class_D']) for p in r['points']}
                    assert r['complete'] and got==expected,(seed,k,reg,got,expected)
                    for p in r['points']:
                        eligible=[(c,d) for c,d,s in witnesses if s>=k and cls(c,d,n,reg)==(p['class_C'],p['class_D'])]
                        assert (p['C10'],p['Dsum'])==min(eligible)
                    records.append(dict(seed=seed,k=k,regime=reg,status='PASS'))
        # Force first region timeout: queue must continue, no unproven region is closed.
        original=bounded.solve;seen=[]
        def interrupted(*args,**kwargs):
            seen.append(1)
            if len(seen)==1:return dict(optimal=False,infeasible=False,witness=None,status='INJECTED_TIMEOUT')
            return original(*args,**kwargs)
        bounded.solve=interrupted
        r=run(Model([[10,20],[20,10]],[1,4]),1,'M',Path(tmp)/'interrupt',5,5)
        assert len(r['unresolved'])==1 and r['closed'] and not r['pending'] and not r['complete']
        bounded.solve=original
    c=Clock();assert not c.expired(1799) and c.expired(1800)
    c.observe(100,10);c.observe(300,8);assert c.first==100 and c.last==300 and c.expired(1900) and not c.expired(1899)
    # Real solver time limit with no guarantee of a feasible solution.
    rng=np.random.default_rng(9);m=Model(rng.integers(100,500,(12,12)),rng.integers(1,80,12))
    limited=solve(m,7,'D',[],lambda x:None,0.00001,0.00001)
    assert not limited['optimal'] and not limited['infeasible']
    result=dict(status='PASS',exhaustive_cases=records,timeout_queue='PASS',deadline_clock='PASS',native_time_limit='PASS',native_limited_status=limited['status'])
    Path(__file__).with_name('TEST_RESULTS.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()
