"""Portable entry points for checking evidence and optional solver reruns.
No solver is launched by 'verify'. Frozen evidence is never overwritten.
"""
from pathlib import Path
import argparse, hashlib, json, os, platform, shutil, subprocess, sys

ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'03_REPRODUCIBILITY'
PANEL=[1,3,4,7,8,9,10,11,12,13,14,15,16,18]

def run(command, cpu=None):
    env=os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE']='1'
    for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:env[k]='1'
    kwargs={}
    if cpu is not None:
        if not hasattr(os,'sched_getaffinity') or cpu not in os.sched_getaffinity(0):
            raise SystemExit(f'CPU {cpu} is unavailable. Select an allowed CPU explicitly with --cpu; changed hardware/affinity is not timing-equivalent to the archive.')
        kwargs['preexec_fn']=lambda:os.sched_setaffinity(0,{cpu})
    subprocess.run([sys.executable,*map(str,command)],check=True,env=env,**kwargs)

def preflight(cpu,allow_drift=False):
    import numpy, scipy
    from scipy.optimize._highspy._core import _Highs
    got={'python':platform.python_version(),'numpy':numpy.__version__,'scipy':scipy.__version__,'highs':_Highs().version()}
    expected={'python':'3.12.14','numpy':'2.3.5','scipy':'1.17.0','highs':'1.8.0'}
    drift={k:{'expected':expected[k],'actual':v} for k,v in got.items() if v!=expected[k]}
    info={'versions':got,'version_drift':drift,'requested_cpu':cpu,'original_cpu':0,'platform':platform.platform(),
          'original_binary_image_available':False,'timing_equivalence_guaranteed':False}
    print(json.dumps(info,indent=2),flush=True)
    if drift and not allow_drift:raise SystemExit('Recorded versions differ. Use the archived environment, or explicitly pass --allow-environment-drift for an exploratory rerun.')
    return info

def fresh(path):
    path=path.resolve()
    protected=[E,ROOT/'02_SUPPLEMENTARY',ROOT/'scripts',ROOT/'tests',ROOT/'docs']
    if any(path==p or p in path.parents for p in protected):raise SystemExit('Output must be outside the frozen evidence, scripts and reference tables.')
    path.mkdir(parents=True,exist_ok=False)
    return path

def manifest_check():
    records=json.loads((ROOT/'FILE_MANIFEST_SHA256.json').read_text())['files']
    for name,h in records.items():
        p=ROOT/name
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=h:raise RuntimeError(f'Manifest mismatch: {name}')
    print(f'Manifest PASS: {len(records)} files',flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    subs=p.add_subparsers(dest='action',required=True)
    subs.add_parser('check-environment')
    a=subs.add_parser('verify',help='Check hashes, all panel records and all 68 witnesses; regenerate English tables/figures without solving.')
    a.add_argument('--output',type=Path,required=True)
    a=subs.add_parser('oracle',help='Regenerate the solver-free K17 construction and check it against the frozen model in a new copy.')
    a.add_argument('--output',type=Path,required=True)
    a=subs.add_parser('solve',help='Run an official algorithm afresh; potentially long-running.')
    a.add_argument('--layer',type=int,choices=PANEL+[2,5,6],required=True)
    a.add_argument('--regime',choices=['M','P','PAIR'],default='PAIR')
    a.add_argument('--output',type=Path,required=True)
    a.add_argument('--cpu',type=int,default=0)
    a.add_argument('--allow-environment-drift',action='store_true')
    a=subs.add_parser('audit-k5',help='Rerun the targeted presolve-off audit in a new copy; uses the same HiGHS backend.')
    a.add_argument('--output',type=Path,required=True)
    a.add_argument('--cpu',type=int,default=0)
    a.add_argument('--allow-environment-drift',action='store_true')
    a=subs.add_parser('validate',help='Small synthetic exhaustive checks; not a rerun of the 18-worker experiments.')
    a.add_argument('--protocol',choices=['V1.1','V2.1','both'],default='both')
    a.add_argument('--output',type=Path,required=True)
    a.add_argument('--cpu',type=int,default=0)
    a.add_argument('--allow-environment-drift',action='store_true')
    args=p.parse_args()
    if args.action=='check-environment':preflight(0,True);return
    if args.action in ['solve','audit-k5','validate']:info=preflight(args.cpu,args.allow_environment_drift)
    out=fresh(args.output)
    if args.action=='verify':
        manifest_check()
        run([ROOT/'scripts/verify_panel.py',E/'PANEL14_V1_1',out/'panel_verification.json'])
        run([ROOT/'scripts/analyze_results.py','--output',out/'derived'])
        run([ROOT/'scripts/check_followup_evidence.py',out/'followup_verification.json'])
        names=[p.name for p in (ROOT/'02_SUPPLEMENTARY').iterdir() if p.suffix in ['.csv','.json']]
        for name in names:
            if (out/'derived'/name).read_bytes()!=(ROOT/'02_SUPPLEMENTARY'/name).read_bytes():raise RuntimeError(f'Derived reference mismatch: {name}')
        (out/'verification_summary.json').write_text(json.dumps({'status':'PASS','reference_data_files_matched':len(names),'solver_calls':0,'scope':'Hashes, recorded closure, witness arithmetic and derived results; no independent MILP dual proof.'},indent=2))
        print('PASS: archived references reproduced without MILP calls.')
    elif args.action=='oracle':
        dest=out/'K17_STRUCTURAL';shutil.copytree(E/'K17_STRUCTURAL',dest)
        run([dest/'k17_structural_oracle.py'])
        run([dest/'verify_k17_oracle_against_v2_1.py'])
        for name in ['EXACT_REFERENCE.json']:
            a=json.loads((dest/'K17_INDEPENDENT_ORACLE'/name).read_text());b=json.loads((E/'K17_STRUCTURAL/K17_INDEPENDENT_ORACLE'/name).read_text())
            if a!=b:raise RuntimeError('Regenerated structural reference differs from archive')
        print('PASS: deterministic K17 oracle regenerated; no MILP optimization was run.')
    else:
        (out/'execution_context.json').write_text(json.dumps(info,indent=2))
        if args.action=='solve':
            k=args.layer
            if k in PANEL:
                order=['M','P'] if k%2 else ['P','M']
                for reg in order if args.regime=='PAIR' else [args.regime]:run([E/'PANEL14_V1_1/validated_runner/launch.py',k,reg,out/reg],args.cpu)
            else:
                code=E/f'K{k:02d}_V2_1/bounded_region_v2'
                if args.regime=='PAIR':run([code/'run_pair.py',k,out/'runs'],args.cpu)
                else:run([code/'launch.py',k,args.regime,out/args.regime],args.cpu)
        elif args.action=='audit-k5':
            dest=out/'K05_V2_1';shutil.copytree(E/'K05_V2_1',dest)
            run([dest/'K05_DELIVERY/K05_TARGETED_AUDIT_2026-10-22/audit_k5_cap692.py'],args.cpu)
        elif args.action=='validate':
            if args.protocol in ['V1.1','both']:run([E/'PANEL14_V1_1/validated_runner/runner.py','test',out/'V1_1_tests.json'],args.cpu)
            if args.protocol in ['V2.1','both']:run([ROOT/'tests/test_bounded_v2_1.py',out/'V2_1_tests.json'],args.cpu)

if __name__=='__main__':main()
