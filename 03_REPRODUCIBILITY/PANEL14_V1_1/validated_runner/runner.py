"""Integer-lattice defining-point objective-box runner; new audited implementation.
Not author-supplied DPA source. Solver exactness is subject to recorded MILP tolerances.
"""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
import csv,json,time,hashlib,sys,warnings,itertools,platform
from pathlib import Path
from decimal import Decimal
import numpy as np
import scipy
from scipy.optimize._highspy._core import _Highs
from legacy_model import RotationMILP

OPTIONS=dict(disp=False,presolve=True,mip_rel_gap=0.0,mip_abs_gap=0.0,threads=1,random_seed=20261019,
             mip_feasibility_tolerance=1e-7,primal_feasibility_tolerance=1e-7,dual_feasibility_tolerance=1e-7)
class Config:
    def scipy_options(self): return dict(OPTIONS)

class Model(RotationMILP):
    def __init__(self,P,R,T=None):
        self.P=np.asarray(P,dtype=int);self.R=np.asarray(R,dtype=int)
        super().__init__(self.P,self.R*(T or len(R)),periods=T)
        # Internal C = tenth seconds; E_i = sum_j R_j*q_ij; D = range of those integer sums.
        self._integrality[self.idx_C:]=1

def cls(c,d,T,regime):
    if regime=='M': return c,d
    return (2*c+5)//10,(2*d+T)//(2*T)

def upper(c,d,T,regime):
    if regime=='M': return c,d
    return (10*c+4)//2, ((2*d+1)*T-1)//2

def qa(m,sol,k):
    q=np.rint(sol.counts).astype(int)
    assert np.max(np.abs(sol.counts-q))<1e-6
    assert (q>=0).all() and (q.sum(0)==m.T).all() and (q.sum(1)==m.T).all()
    s=int((q>0).sum(1).min());assert s>=k
    c=int(m.P[q>0].max());loads=q@m.R;d=int(loads.max()-loads.min())
    x=m.decompose_counts_to_schedule(q)
    assert (x.sum(0)==1).all() and (x.sum(1)==1).all() and np.array_equal(x.sum(2),q)
    return dict(C10=c,Dsum=d,C=c/10,D=d/(10*m.T),Smin_actual=s,counts=q.tolist(),
                schedule_station_by_worker_period=(x.argmax(axis=1)+1).tolist(),station_index_base=1,verified=True)

def enumerate_layer(m,k,regime,emit=lambda x:None):
    calls=[];points=[];config=Config();start=time.perf_counter()
    def solve(obj,extra):
        emit(dict(event='call_start',call=len(calls)+1,objective=obj))
        t=time.perf_counter()
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore',message='Unrecognized options detected:.*')
            s=m.solve_objective(obj,extra,config)
        r=dict(call=len(calls)+1,objective=obj,status=s.status,seconds=time.perf_counter()-t,
               gap=getattr(s.raw,'mip_gap',None),dual_bound=getattr(s.raw,'mip_dual_bound',None),message=s.message)
        calls.append(r);emit(dict(event='call_end',**r))
        if s.status==2:return None
        if not s.success or s.status!=0: raise RuntimeError(r)
        if getattr(s.raw,'mip_gap',0)>1e-9: raise RuntimeError('Nonzero final gap')
        return s
    dbound=int((m.R.max()-m.R.min())*m.T)
    while dbound>=0:
        base=[m.smin_ge(k),m.d_le(dbound)]
        a=solve('C',base)
        if a is None:
            closure='remaining objective box infeasible';break
        wa=qa(m,a,k);cc=cls(wa['C10'],wa['Dsum'],m.T,regime)[0]
        ccap=upper(cc,0,m.T,regime)[0]
        b=solve('D',base+[m.c_le(ccap)]);assert b is not None
        wb=qa(m,b,k);dd=cls(wb['C10'],wb['Dsum'],m.T,regime)[1]
        dcap=min(dbound,upper(cc,dd,m.T,regime)[1])
        # Common four-stage scalarization in both regimes. Select raw C, then D representative.
        c=solve('C',base+[m.c_le(ccap),m.d_le(dcap)]);assert c is not None
        wc=qa(m,c,k)
        d=solve('D',base+[m.c_eq(wc['C10']),m.d_le(dcap)]);assert d is not None
        wd=qa(m,d,k);assert cls(wd['C10'],wd['Dsum'],m.T,regime)==(cc,dd)
        assert wd['C10']==wc['C10']
        points.append(dict(class_C=cc,class_D=dd,**wd));emit(dict(event='point',point=points[-1]))
        # Min-C proof closes all smaller C classes; min-D within C class closes its dominated region.
        # The remaining defining-point box has D class <= dd-1.
        dbound=upper(cc,dd-1,m.T,regime)[1]
    else:closure='nonnegative D lower bound reached'
    for a,b in zip(points,points[1:]):assert a['class_C']<b['class_C'] and a['class_D']>b['class_D']
    return dict(k=k,regime=regime,points=points,milp_calls=len(calls),calls=calls,
                solver_seconds=sum(c['seconds'] for c in calls),inner_seconds=time.perf_counter()-start,
                exactness='complete_under_recorded_MILP_tolerances',closure=closure)

def load_data():
    root=Path(__file__).resolve().parent.parent/'standard_data_audit'
    def read(name):
        return list(csv.reader((root/name).open()))[1:]
    p=[[int(Decimal(v)*10) for v in row[1:]] for row in read('processing_times_standard_1decimal.csv')]
    r=[int(Decimal(row[1])*10) for row in read('reba_standard.csv')]
    return np.array(p).T,np.array(r)

def nd(vals):return {p for p in vals if not any(q[0]<=p[0] and q[1]<=p[1] and q!=p for q in vals)}
def tests(out):
    records=[]
    # Enumerate every period assignment independently of the aggregated MILP.
    for seed,n in [(1,2),(2,3),(3,3),(4,3)]:
        rng=np.random.default_rng(seed);P=rng.integers(10,35,(n,n));R=rng.integers(1,9,n);m=Model(P,R)
        schedules=list(itertools.product(list(itertools.permutations(range(n))),repeat=n))
        witnesses=[]
        for sch in schedules:
            q=np.zeros((n,n),int)
            for period in sch:
                for i,j in enumerate(period):q[i,j]+=1
            loads=q@R;witnesses.append((int(P[q>0].max()),int(loads.max()-loads.min()),int((q>0).sum(1).min())))
        for k in range(1,n+1):
            for reg in ['M','P']:
                expected=nd({cls(c,d,n,reg) for c,d,s in witnesses if s>=k})
                actual=enumerate_layer(m,k,reg)
                got={(p['class_C'],p['class_D']) for p in actual['points']};assert got==expected,(seed,k,reg,got,expected)
                for p in actual['points']:
                    eligible=[(c,d) for c,d,s in witnesses if s>=k and cls(c,d,n,reg)==(p['class_C'],p['class_D'])]
                    assert (p['C10'],p['Dsum'])==min(eligible)
                records.append(dict(seed=seed,n=n,k=k,regime=reg,points=len(got),status='PASS'))
    assert cls(702,8,18,'P')==(140,0)
    assert cls(703,9,18,'P')==(141,1)
    assert upper(140,0,18,'P')==(702,8)
    assert upper(141,1,18,'P')==(707,26)
    m=Model([[10,20],[20,10]],[1,4]);assert enumerate_layer(m,3,'M')['points']==[]
    result=dict(status='PASS',cases=records,boundary_tests='PASS',infeasible_test='PASS')
    Path(out).write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)

def env():
    h=_Highs();checks={}
    for key,value in OPTIONS.items():
        if key in ('disp','presolve'):continue
        status=h.setOptionValue(key,value);actual=h.getOptionValue(key)
        assert str(status).endswith('kOk') and actual[1]==value,(key,status,actual)
        checks[key]=actual[1]
    return dict(python=sys.version,scipy=scipy.__version__,highs=h.version(),platform=platform.platform(),
                affinity=sorted(os.sched_getaffinity(0)),options=OPTIONS,native_option_validation=checks,
                thread_env={k:os.environ[k] for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')})

if __name__=='__main__':
    if sys.argv[1]=='test':tests(sys.argv[2])
    else:
        k=int(sys.argv[1]);reg=sys.argv[2];out=Path(sys.argv[3]);out.mkdir(parents=True,exist_ok=True)
        (out/'environment.json').write_text(json.dumps(env(),indent=2))
        log=(out/'events.jsonl').open('w',buffering=1)
        def emit(v):v['utc']=time.time();log.write(json.dumps(v)+'\n');print(json.dumps(v),flush=True)
        P,R=load_data();m=Model(P,R)
        result=enumerate_layer(m,k,reg,emit)
        result['source_code_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')}
        result['data_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__).parent.parent/'standard_data_audit').glob('*standard*.csv')}
        result['base_model_sha256']=hashlib.sha256(m._A.data.tobytes()+m._A.indices.tobytes()+m._A.indptr.tobytes()+m._lb.tobytes()+m._ub.tobytes()+m._integrality.tobytes()+m._bounds.lb.tobytes()+m._bounds.ub.tobytes()).hexdigest()
        (out/'result.json').write_text(json.dumps(result,indent=2));log.close()
