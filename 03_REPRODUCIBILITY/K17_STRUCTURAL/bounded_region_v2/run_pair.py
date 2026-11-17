"""Sequential M/P pair; never starts another k."""
import os,json,sys,time,hashlib
from pathlib import Path
from launch import launch
root=Path(__file__).resolve().parent
for name,digest in json.loads((root/'FROZEN_SHA256.json').read_text()).items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
k=int(sys.argv[1]);base=Path(sys.argv[2]).resolve();base.mkdir(parents=True,exist_ok=False)
status={'k':k,'state':'RUNNING','started_utc':time.time(),'regime':None}
for reg in ['M','P']:
    status['regime']=reg;(base/'PAIR_STATUS.json').write_text(json.dumps(status,indent=2))
    launch(k,reg,base/reg)
    r=json.loads((base/reg/'result.json').read_text())
    status[reg]={'complete':r['complete'],'unresolved_regions':len(r['unresolved']),'points':[(w['C10'],w['Dsum']) for w in r['points']]}
status.update(state='FINISHED',finished_utc=time.time());(base/'PAIR_STATUS.json').write_text(json.dumps(status,indent=2))
