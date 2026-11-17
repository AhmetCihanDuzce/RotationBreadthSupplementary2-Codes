"""Independent exact structural certificate; no optimization solver, no feedback to DPA."""
from pathlib import Path
from decimal import Decimal
from fractions import Fraction
import csv,json,hashlib
root=Path(__file__).resolve().parent
rows=list(csv.reader((root/'standard_data_audit/processing_times_standard_1decimal.csv').open()))[1:]
P=list(map(list,zip(*[[int(Decimal(v)*10) for v in row[1:]] for row in rows])))
R=[int(Decimal(row[1])*10) for row in list(csv.reader((root/'standard_data_audit/reba_standard.csv').open()))[1:]]
def decompose(q):
    remain=[row[:] for row in q];schedule=[[] for _ in range(18)]
    for period in range(18):
        match=[-1]*18
        def dfs(i,seen):
            for j in range(18):
                if remain[i][j] and j not in seen:
                    seen.add(j)
                    if match[j]<0 or dfs(match[j],seen):match[j]=i;return True
            return False
        for i in range(18):assert dfs(i,set())
        assert sorted(match)==list(range(18))
        for j,i in enumerate(match):remain[i][j]-=1;schedule[i].append(j+1)
    assert all(v==0 for row in remain for v in row)
    return schedule
def witness(swaps):
    q=[[1]*18 for _ in range(18)]
    used=set()
    # Swap two workers' omissions/repetitions; each pair conserves both station columns.
    for worker,partner,omit,repeat in swaps:
        i,h,j,l=worker-1,partner-1,omit-1,repeat-1
        assert i not in used and h not in used;used|={i,h}
        q[i][j]-=1;q[i][l]+=1;q[h][l]-=1;q[h][j]+=1
    assert all(sum(row)==18 for row in q)
    assert all(sum(q[i][j] for i in range(18))==18 for j in range(18))
    assert min(sum(v>0 for v in row) for row in q)>=17
    C=max(P[i][j] for i in range(18) for j in range(18) if q[i][j])
    L=[sum(q[i][j]*R[j] for j in range(18)) for i in range(18)];D=max(L)-min(L)
    sch=decompose(q)
    for t in range(18):assert sorted(row[t] for row in sch)==list(range(1,19))
    return dict(C10=C,Dsum=D,C_seconds=C/10,D_fraction=str(Fraction(D,180)),counts=q,schedule=sch,Smin_actual=min(sum(v>0 for v in row) for row in q),load_differences=[v-sum(R) for v in L])

row_bottleneck=max(sorted(row)[-2] for row in P)
assert row_bottleneck==768
assert P[7][7]==771 and R[7]==57 and R.count(57)==1
assert max(v for v in R if v<57)==52 and min(v for v in R if v>57)==61
assert P[1][13]==775 and R[13]==52 and R.count(52)==1
a=witness([(1,4,9,1),(2,6,14,4),(3,7,14,4),(5,9,3,1),(8,10,8,11),(11,12,15,6)])
b=witness([(2,4,14,4),(11,6,15,6)])
c=witness([])
assert [(v['C10'],v['Dsum']) for v in [a,b,c]]==[(768,8),(771,2),(775,0)]
proof='''# Independent k=17 exact structural certificate

This certificate uses the frozen standard input, exact integer arithmetic and explicit schedules; no MILP or DPA solution is used. It does not replace or shorten the separately running DPA timing experiment.

Let P=10p, R=10r. Every row of visit counts has 18 visits and at least 17 positive entries. It is either all ones, or exactly one omitted station j and one repeated station l. Relative to B=sum_j R_j, worker load difference is delta=R_l−R_j (or zero for an all-ones row). Column sums imply omitted and repeated station counts balance, and sum_i delta_i=0. Across any station subset, the number of omission→repetition arcs leaving it equals the number entering it. All such differences are integers. Dsum=max delta−min delta, real D=Dsum/180.

1. No solution with C10<768: each worker needs 17 available stations. The maximum, over rows, of the second-largest processing time is 768. An explicit witness at C10=768 is given.

2. For C10<771, worker 8 must omit station 8 because P[8,8]=771 (one-based). That station's R=57 is unique. The nearest lower station score is 52 and nearest higher score is 61. If the worker repeats a higher-score station, its arc crosses the cut {R<=57}→{R>=61} with delta>=4. Station balance forces a reverse crossing, with delta<=−4. Thus Dsum>=8. If it repeats a lower-score station, delta<=−5 across the cut {R<=52}/{R>=57}; a reverse arc has delta>=5 and Dsum>=10. Consequently Dsum>=8 in either case. The first explicit witness attains (768,8).

3. For C10<775, worker 2 must omit station 14 because P[2,14]=775 and its R=52 is unique. Its delta is a nonzero integer. Since all delta sum to zero, a delta with the opposite sign must exist; Dsum>=2. The second witness attains (771,2).

4. At C10=775, the all-ones matrix is feasible, gives Dsum=0 and yields a cyclic/matching schedule. No negative D is possible.

These lower bounds cover the entire C axis: below768 infeasible; [768,771) Dsum>=8; [771,775) Dsum>=2; at/above775 Dsum>=0. The three feasible witnesses attain each lower envelope level. Thus the complete mathematical Pareto set is exactly (C10,Dsum)={(768,8),(771,2),(775,0)}.

Practical labels are (77.0,0.0), (77.0,0.0), (77.5,0.0). Only class (77.0,0.0) survives. Within it the prescribed raw-C then raw-D representative is (768,8). This also certifies the practical class set independently of DPA. This is a structural oracle result; DPA completion and its measured time remain separate statuses.
'''
out=root/'K17_INDEPENDENT_ORACLE';out.mkdir(exist_ok=True)
(out/'STRUCTURAL_PROOF_EN.md').write_text(proof)
(out/'EXACT_REFERENCE.json').write_text(json.dumps(dict(status='COMPLETE_INDEPENDENT_STRUCTURAL_REFERENCE',data_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'standard_data_audit').glob('*standard*.csv')},M_points=[a,b,c],P_class_indices=[[154,0]],P_representative_C10_Dsum=[768,8],DPA_status='separate; not certified finished by this oracle'),indent=2))
print('Independent structural reference complete: M={(76.8,8/180),(77.1,2/180),(77.5,0)}; P={(77.0,0.0)}, representative=(76.8,8/180). DPA timing remains independent.')
