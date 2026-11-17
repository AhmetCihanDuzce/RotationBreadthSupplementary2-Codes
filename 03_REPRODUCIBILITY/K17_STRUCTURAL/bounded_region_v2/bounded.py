"""Cumulative C-cap region queue. Separate method, not source-faithful DPA."""
from runner import *
from scipy.optimize._highspy._core import _Highs,HighsLp,HighsSparseMatrix,MatrixFormat,HighsVarType,HighsModelStatus,cb
from scipy.sparse import vstack
from types import SimpleNamespace

class Clock:
    def __init__(self,search=600,proof=1800):self.search=search;self.proof=proof;self.first=None;self.best=None;self.last=None
    def observe(self,t,value):
        if self.first is None:self.first=t
        if self.best is None or value<self.best:self.best=value;self.last=t
    def expired(self,t):return t >= (self.search if self.first is None else self.first+self.proof)

def solve(m,k,obj,extra,emit,search=600,proof=1800):
    h=_Highs();clock=Clock(search,proof);start=time.perf_counter()
    for key,val in OPTIONS.items():
        key={'disp':'output_flag'}.get(key,key)
        if key=='presolve':val='on' if val else 'off'
        assert str(h.setOptionValue(key,val)).endswith('kOk'),key
    # Hard safety ceiling; callback enforces the earlier first-incumbent deadline.
    h.setOptionValue('time_limit',search+proof)
    Ae,le,ue=m._extra_matrix([m.smin_ge(k)]+extra)
    A=vstack([m._A,Ae],format='csr');cost=np.zeros(m.nvar);cost[m.idx_C if obj=='C' else m.idx_D]=1
    lp=HighsLp();lp.num_col_=m.nvar;lp.num_row_=A.shape[0];lp.col_cost_=cost
    lp.col_lower_=m._bounds.lb;lp.col_upper_=m._bounds.ub
    lp.row_lower_=np.concatenate([m._lb,le]);lp.row_upper_=np.concatenate([m._ub,ue])
    lp.integrality_=[HighsVarType.kInteger if v else HighsVarType.kContinuous for v in m._integrality]
    mat=HighsSparseMatrix();mat.format_=MatrixFormat.kRowwise;mat.num_col_=m.nvar;mat.num_row_=A.shape[0]
    mat.start_=A.indptr;mat.index_=A.indices;mat.value_=A.data;lp.a_matrix_=mat
    assert str(h.passModel(lp)).endswith('kOk')
    def callback(kind,msg,out,inp,user):
        t=time.perf_counter()-runstart
        if kind==int(cb.kCallbackMipImprovingSolution):
            clock.observe(t,float(out.objective_function_value))
            emit(dict(event='incumbent',seconds=t,objective=obj,value=clock.best,first_seconds=clock.first))
        if kind in [int(cb.kCallbackMipInterrupt),int(cb.kCallbackSimplexInterrupt),int(cb.kCallbackIpmInterrupt)] and clock.expired(t):inp.user_interrupt=True
    h.setCallback(callback,None)
    for typ in [cb.kCallbackMipImprovingSolution,cb.kCallbackMipInterrupt,cb.kCallbackSimplexInterrupt,cb.kCallbackIpmInterrupt]:h.startCallback(typ)
    runstart=time.perf_counter();h.run();elapsed=time.perf_counter()-runstart
    info=h.getInfo();s=h.getSolution();status=h.getModelStatus()
    witness=None
    if s.value_valid:
        z=np.asarray(s.col_value)
        assert np.max(np.maximum(lp.row_lower_-A@z,0))<1e-5
        assert np.max(np.maximum(A@z-lp.row_upper_,0))<1e-5
        assert np.max(np.abs(z[m._integrality>0]-np.rint(z[m._integrality>0])))<1e-5
        witness=qa(m,SimpleNamespace(counts=z[:m.nq].reshape(m.n,m.n)),k)
        assert witness['C10']<=min([e[2] for e in extra if e[0]=={m.idx_C:1.0}]+[np.inf])+1e-6
    result=dict(objective=obj,status=str(status),optimal=status==HighsModelStatus.kOptimal,
        infeasible=status==HighsModelStatus.kInfeasible,seconds=elapsed,total_call_seconds=time.perf_counter()-start,
        first_solution_seconds=clock.first,best_solution_seconds=clock.last,objective_value=float(info.objective_function_value) if witness else None,
        dual_bound=float(info.mip_dual_bound),gap=float(info.mip_gap),nodes=int(info.mip_node_count),witness=witness,
        callback_first_observed=clock.first is not None)
    emit(dict(event='call_end',**result));return result

def caps(m,reg):
    # A bottleneck is one of the input processing times; caps cover every possible C class.
    return sorted({cls(int(c),0,m.T,reg)[0] for c in m.P.flat})

def run(m,k,reg,out,search=600,proof=1800):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);assert not (out/'state.json').exists();log=(out/'events.jsonl').open('w',buffering=1)
    def emit(e):e['utc']=time.time();log.write(json.dumps(e)+'\n')
    (out/'environment.json').write_text(json.dumps(env(),indent=2))
    # Row kth-smallest yields a valid necessary lower C bound, independent of oracle.
    lower=int(np.sort(m.P,axis=1)[:,k-1].max()) if k<=m.n else 0
    queue=[c for c in caps(m,reg) if c>=cls(lower,0,m.T,reg)[0]]
    state=dict(k=k,regime=reg,method='cumulative_C_cap_queue_v2',search_seconds=search,proof_seconds=proof,
               pending=queue.copy(),unresolved=[],closed=[],calls=[],candidates=[],complete=False)
    def save():
        tmp=out/'state.tmp';tmp.write_text(json.dumps(state,indent=2));tmp.replace(out/'state.json')
    save()
    for c in queue:
        cap=upper(c,0,m.T,reg)[0];region=dict(class_C_cap=c,C10_cap=cap)
        emit(dict(event='region_start',**region));ok=True
        a=solve(m,k,'D',[m.c_le(cap)],emit,search,proof);state['calls'].append(a)
        if a['witness']:state['candidates'].append(a['witness'])
        if a['infeasible']:state['closed'].append(dict(**region,reason='infeasible'))
        elif a['optimal']:
            d=cls(0,a['witness']['Dsum'],m.T,reg)[1];dcap=upper(c,d,m.T,reg)[1]
            b=solve(m,k,'C',[m.c_le(cap),m.d_le(dcap)],emit,search,proof);state['calls'].append(b)
            if b['witness']:state['candidates'].append(b['witness'])
            if b['optimal']:
                cc=b['witness']['C10'];z=solve(m,k,'D',[m.c_le(cc),m.d_le(dcap)],emit,search,proof);state['calls'].append(z)
                if z['witness']:state['candidates'].append(z['witness'])
                if z['optimal']:state['closed'].append(dict(**region,reason='minimum_D_class_and_lex_representative_proven',representative=z['witness']))
                else:ok=False
            else:ok=False
        else:ok=False
        if not ok:state['unresolved'].append(region)
        state['pending'].remove(c);save()
    vals={cls(w['C10'],w['Dsum'],m.T,reg) for w in state['candidates']};front=nd(vals)
    state['points']=[]
    for cl in sorted(front):
        w=min((w for w in state['candidates'] if cls(w['C10'],w['Dsum'],m.T,reg)==cl),key=lambda w:(w['C10'],w['Dsum']))
        state['points'].append(dict(class_C=cl[0],class_D=cl[1],**w))
    state['complete']=not state['unresolved'];save();(out/'result.json').write_text(json.dumps(state,indent=2));log.close();return state

if __name__=='__main__':
    P,R=load_data();run(Model(P,R),int(sys.argv[1]),sys.argv[2],sys.argv[3])
