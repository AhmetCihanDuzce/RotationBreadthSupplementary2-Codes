from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
import csv

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp, linear_sum_assignment
from scipy.sparse import coo_matrix, csr_matrix, hstack, vstack


@dataclass
class SolveConfig:
    time_limit: Optional[float] = None
    mip_rel_gap: float = 0.0
    presolve: bool = True

    def scipy_options(self) -> dict:
        opts = {"disp": False, "presolve": self.presolve, "mip_rel_gap": self.mip_rel_gap}
        if self.time_limit is not None:
            opts["time_limit"] = float(self.time_limit)
        return opts


@dataclass
class Solution:
    success: bool
    status: int
    message: str
    objective: Optional[float]
    C: Optional[float]
    D: Optional[float]
    Smin: Optional[int]
    Stotal: Optional[int]
    E: Optional[np.ndarray]
    counts: Optional[np.ndarray]
    y: Optional[np.ndarray]
    raw: object = None


class RotationMILP:
    """Exact aggregated MILP for the manuscript's sequence-independent model.

    Instead of period-level x_ijt binaries, this reference implementation uses
    integer visit counts q_ij = sum_t x_ijt. Under the manuscript assumptions
    (complete one-to-one assignment each period and no sequence-dependent terms),
    this is exactly equivalent: every nonnegative integer q matrix with row and
    column sums T is a T-regular bipartite multigraph and can be decomposed into
    T one-to-one period assignments. The aggregation greatly reduces symmetry
    and makes independent reproduction practical.
    """

    def __init__(self, processing_times: np.ndarray, reba: np.ndarray,
                 periods: Optional[int] = None, structured_blocks: Optional[dict] = None):
        self.p = np.asarray(processing_times, dtype=float)
        self.r = np.asarray(reba, dtype=float)
        if self.p.ndim != 2 or self.p.shape[0] != self.p.shape[1]:
            raise ValueError("processing_times must be a square worker x station matrix")
        self.n = self.p.shape[0]
        if self.r.shape != (self.n,):
            raise ValueError("reba must contain one score per station")
        self.T = int(periods or self.n)
        self.structured_blocks = structured_blocks

        self.nq = self.n * self.n
        self.ny = self.n * self.n
        self.idx_C = self.nq + self.ny
        self.idx_E0 = self.idx_C + 1
        self.idx_Emax = self.idx_E0 + self.n
        self.idx_Emin = self.idx_Emax + 1
        self.idx_D = self.idx_Emin + 1
        self.idx_Smin = self.idx_D + 1
        self.nvar = self.idx_Smin + 1

        self._A, self._lb, self._ub = self._build_base_constraints()
        self._bounds, self._integrality = self._build_bounds_integrality()

    @staticmethod
    def from_csv(data_dir: str | Path, structured_blocks: Optional[dict] = None) -> "RotationMILP":
        data_dir = Path(data_dir)
        # CSV rows are stations and columns are workers. Transpose to p[worker,station].
        station_by_worker: List[List[float]] = []
        with open(data_dir / "processing_times.csv", newline="", encoding="utf-8") as f:
            reader = csv.reader(f); next(reader)
            for row in reader:
                station_by_worker.append([float(v) for v in row[1:]])
        p = np.asarray(station_by_worker, dtype=float).T
        r_vals: List[float] = []
        with open(data_dir / "reba.csv", newline="", encoding="utf-8") as f:
            reader = csv.reader(f); next(reader)
            for row in reader: r_vals.append(float(row[1]))
        return RotationMILP(p, np.asarray(r_vals), structured_blocks=structured_blocks)

    def iq(self, i: int, j: int) -> int:
        return i * self.n + j

    def iy(self, i: int, j: int) -> int:
        return self.nq + i * self.n + j

    def iE(self, i: int) -> int:
        return self.idx_E0 + i

    def _build_bounds_integrality(self) -> Tuple[Bounds, np.ndarray]:
        lo = np.zeros(self.nvar)
        hi = np.full(self.nvar, np.inf)
        hi[:self.nq] = float(self.T)
        hi[self.nq:self.nq+self.ny] = 1.0
        hi[self.idx_C] = float(np.max(self.p))
        lo[self.idx_E0:self.idx_E0+self.n] = float(np.min(self.r))
        hi[self.idx_E0:self.idx_E0+self.n] = float(np.max(self.r))
        lo[self.idx_Emax] = float(np.min(self.r)); hi[self.idx_Emax] = float(np.max(self.r))
        lo[self.idx_Emin] = float(np.min(self.r)); hi[self.idx_Emin] = float(np.max(self.r))
        hi[self.idx_D] = float(np.max(self.r)-np.min(self.r))
        lo[self.idx_Smin] = 1.0; hi[self.idx_Smin] = float(self.n)
        integrality = np.zeros(self.nvar, dtype=int)
        integrality[:self.nq+self.ny] = 1
        integrality[self.idx_Smin] = 1
        return Bounds(lo, hi), integrality

    def _build_base_constraints(self):
        rows=[]; cols=[]; data=[]; lbs=[]; ubs=[]; rid=0
        def add(coeff: Dict[int,float], lb=-np.inf, ub=np.inf):
            nonlocal rid
            for c,v in coeff.items():
                if v:
                    rows.append(rid); cols.append(c); data.append(float(v))
            lbs.append(float(lb)); ubs.append(float(ub)); rid += 1

        # Each worker has T visits; each station is staffed T times.
        for i in range(self.n):
            add({self.iq(i,j):1.0 for j in range(self.n)}, self.T, self.T)
        for j in range(self.n):
            add({self.iq(i,j):1.0 for i in range(self.n)}, self.T, self.T)

        # y_ij = 1 iff q_ij >= 1: q <= T y and y <= q.
        for i in range(self.n):
            for j in range(self.n):
                add({self.iq(i,j):1.0, self.iy(i,j):-float(self.T)}, -np.inf, 0.0)
                add({self.iy(i,j):1.0, self.iq(i,j):-1.0}, -np.inf, 0.0)

        # Bottleneck criterion.
        for i in range(self.n):
            for j in range(self.n):
                add({self.iy(i,j):float(self.p[i,j]), self.idx_C:-1.0}, -np.inf, 0.0)

        # Worker-average REBA exposure.
        for i in range(self.n):
            coeff={self.iE(i):1.0}
            for j in range(self.n): coeff[self.iq(i,j)] = -float(self.r[j])/float(self.T)
            add(coeff,0.0,0.0)

        for i in range(self.n):
            add({self.iE(i):1.0,self.idx_Emax:-1.0},-np.inf,0.0)
            add({self.idx_Emin:1.0,self.iE(i):-1.0},-np.inf,0.0)
        add({self.idx_D:1.0,self.idx_Emax:-1.0,self.idx_Emin:1.0},0.0,0.0)

        for i in range(self.n):
            coeff={self.idx_Smin:1.0}
            for j in range(self.n): coeff[self.iy(i,j)] = -1.0
            add(coeff,-np.inf,0.0)

        if self.structured_blocks is not None:
            wb=self.structured_blocks["worker_blocks"]; sb=self.structured_blocks["station_blocks"]
            w2b={}; s2b={}
            for b,grp in enumerate(wb):
                for i1 in grp: w2b[int(i1)-1]=b
            for b,grp in enumerate(sb):
                for j1 in grp: s2b[int(j1)-1]=b
            for i in range(self.n):
                for j in range(self.n):
                    val=1.0 if w2b[i]==s2b[j] else 0.0
                    add({self.iy(i,j):1.0},val,val)

        return coo_matrix((data,(rows,cols)),shape=(rid,self.nvar)).tocsr(), np.asarray(lbs), np.asarray(ubs)

    def constraint(self, coeff, lb=-np.inf, ub=np.inf): return coeff,float(lb),float(ub)
    def c_le(self,v): return self.constraint({self.idx_C:1.0},-np.inf,v)
    def c_ge(self,v): return self.constraint({self.idx_C:1.0},v,np.inf)
    def c_eq(self,v): return self.constraint({self.idx_C:1.0},v,v)
    def d_le(self,v): return self.constraint({self.idx_D:1.0},-np.inf,v)
    def d_ge(self,v): return self.constraint({self.idx_D:1.0},v,np.inf)
    def d_eq(self,v): return self.constraint({self.idx_D:1.0},v,v)
    def smin_ge(self,v): return self.constraint({self.idx_Smin:1.0},v,np.inf)
    def smin_eq(self,v): return self.constraint({self.idx_Smin:1.0},v,v)

    def _extra_matrix(self, extra, nvar=None):
        nvar=int(nvar or self.nvar)
        if not extra: return csr_matrix((0,nvar)),np.array([]),np.array([])
        rr=[];cc=[];dd=[];lb=[];ub=[]
        for r,(coeff,l,u) in enumerate(extra):
            for c,v in coeff.items(): rr.append(r);cc.append(c);dd.append(float(v))
            lb.append(float(l));ub.append(float(u))
        return coo_matrix((dd,(rr,cc)),shape=(len(extra),nvar)).tocsr(),np.asarray(lb),np.asarray(ub)

    def solve_vector(self,c,extra=(),config=SolveConfig()):
        Ae,le,ue=self._extra_matrix(extra)
        A=vstack([self._A,Ae],format="csr") if Ae.shape[0] else self._A
        lb=np.concatenate([self._lb,le]) if le.size else self._lb
        ub=np.concatenate([self._ub,ue]) if ue.size else self._ub
        res=milp(c=np.asarray(c,float),integrality=self._integrality,bounds=self._bounds,
                 constraints=LinearConstraint(A,lb,ub),options=config.scipy_options())
        return self._extract(res)

    def solve_objective(self,objective,extra=(),config=SolveConfig()):
        c=np.zeros(self.nvar)
        if objective=="C": c[self.idx_C]=1.0
        elif objective=="D": c[self.idx_D]=1.0
        elif objective=="Smin": c[self.idx_Smin]=-1.0
        elif objective=="Stotal":
            for i in range(self.n):
                for j in range(self.n): c[self.iy(i,j)] = -1.0
        else: raise ValueError(objective)
        return self.solve_vector(c,extra,config)

    def solve_augmented_epsilon(self,k,epsilon_D,rho,R_D,extra=(),config=SolveConfig()):
        if rho<=0 or R_D<=0: raise ValueError("rho and R_D must be positive")
        n2=self.nvar+1; slack=self.nvar
        Ab=hstack([self._A,csr_matrix((self._A.shape[0],1))],format="csr")
        Ae0,le,ue=self._extra_matrix(list(extra)+[self.smin_ge(k)],self.nvar)
        Ae=hstack([Ae0,csr_matrix((Ae0.shape[0],1))],format="csr")
        eq=coo_matrix(([1.0,1.0],([0,0],[self.idx_D,slack])),shape=(1,n2)).tocsr()
        A=vstack([Ab,Ae,eq],format="csr")
        lb=np.concatenate([self._lb,le,[epsilon_D]]); ub=np.concatenate([self._ub,ue,[epsilon_D]])
        blo=np.concatenate([self._bounds.lb,[0.0]]); bhi=np.concatenate([self._bounds.ub,[max(float(epsilon_D),0.0)]])
        integ=np.concatenate([self._integrality,[0]])
        c=np.zeros(n2); c[self.idx_C]=1.0; c[slack]=-float(rho)/float(R_D)
        res=milp(c=c,integrality=integ,bounds=Bounds(blo,bhi),constraints=LinearConstraint(A,lb,ub),options=config.scipy_options())
        if not res.success:
            return Solution(False,res.status,res.message,None,None,None,None,None,None,None,None,res)
        class R: pass
        rr=R(); rr.success=res.success; rr.status=res.status; rr.message=res.message; rr.fun=res.fun; rr.x=res.x[:self.nvar]
        return self._extract(rr)

    def _extract(self,res):
        if not getattr(res,"success",False) or getattr(res,"x",None) is None:
            return Solution(False,int(getattr(res,"status",-1)),str(getattr(res,"message","")),getattr(res,"fun",None),None,None,None,None,None,None,None,res)
        z=np.asarray(res.x)
        q=z[:self.nq].reshape(self.n,self.n)
        y=z[self.nq:self.nq+self.ny].reshape(self.n,self.n)
        E=z[self.idx_E0:self.idx_E0+self.n]
        return Solution(True,int(res.status),str(res.message),float(res.fun),float(z[self.idx_C]),float(z[self.idx_D]),
                        int(round(z[self.idx_Smin])),int(round(np.sum(y))),E,q,y,res)

    def largest_admissible_C(self,nominal_bound):
        vals=np.unique(np.round(self.p.flatten(),10)); feasible=vals[vals<=nominal_bound+1e-10]
        if len(feasible)==0: raise ValueError("No processing-time level is below the nominal bound")
        return float(np.max(feasible))

    def decompose_counts_to_schedule(self, counts: np.ndarray) -> np.ndarray:
        """Return binary schedule x[i,j,t] from an integer visit-count matrix."""
        q=np.rint(np.asarray(counts)).astype(int).copy()
        if not (np.all(q.sum(axis=1)==self.T) and np.all(q.sum(axis=0)==self.T)):
            raise ValueError("counts do not have row/column sums T")
        x=np.zeros((self.n,self.n,self.T),dtype=int)
        for t in range(self.T):
            cost=np.where(q>0,0.0,1e6)
            ri,cj=linear_sum_assignment(cost)
            if np.any(q[ri,cj]<=0): raise RuntimeError("Could not find positive-support perfect matching")
            x[ri,cj,t]=1; q[ri,cj]-=1
        if np.any(q!=0): raise RuntimeError("decomposition left residual counts")
        return x
