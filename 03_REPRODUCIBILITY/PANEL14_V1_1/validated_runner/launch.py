"""Common measured launcher; starts one child, snapshots every 300 seconds."""
import subprocess,time,json,sys,os,hashlib
from pathlib import Path
def launch(k,reg,out):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    env=os.environ.copy()
    for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):env[name]='1'
    runner=Path(__file__).with_name('runner.py').resolve()
    started=time.perf_counter();epoch=time.time();next_checkpoint=300
    with (out/'stdout.log').open('w') as log:
        child=subprocess.Popen([sys.executable,str(runner),str(k),reg,str(out)],stdout=log,stderr=subprocess.STDOUT,env=env)
        while child.poll() is None:
            elapsed=time.perf_counter()-started
            if elapsed>=next_checkpoint:
                events=out/'events.jsonl';last=None
                if events.exists():
                    with events.open() as f:
                        for line in f:
                            try:last=json.loads(line)
                            except json.JSONDecodeError:pass
                checkpoint=dict(k=k,regime=reg,elapsed=elapsed,utc=time.time(),pid=child.pid,last_safe_event=last,
                                state='RUNNING',time_limit=None)
                (out/f'checkpoint_{next_checkpoint:06d}.json').write_text(json.dumps(checkpoint,indent=2))
                print(json.dumps(dict(checkpoint=next_checkpoint,elapsed=elapsed,k=k,regime=reg)),flush=True)
                next_checkpoint+=300
            time.sleep(.2)
    elapsed=time.perf_counter()-started
    result=dict(k=k,regime=reg,T_total=elapsed,start_utc=epoch,end_utc=time.time(),exit_code=child.returncode,
                time_limit=None,affinity=sorted(os.sched_getaffinity(0)),
                launcher_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (out/'timing.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
    if child.returncode:raise RuntimeError('Child failed; inspect stdout.log')
if __name__=='__main__':launch(int(sys.argv[1]),sys.argv[2],sys.argv[3])
