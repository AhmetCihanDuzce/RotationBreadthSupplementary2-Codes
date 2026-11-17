"""Recreate the standardized CSVs from the published model input summary."""
from pathlib import Path
from decimal import Decimal,ROUND_HALF_UP
import argparse,csv,hashlib,json
from openpyxl import load_workbook
ROOT=Path(__file__).resolve().parents[1]/'03_REPRODUCIBILITY/PANEL14_V1_1'
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
published=json.loads((ROOT/'project_sources/PUBLISHED_SUMMARY.json').read_text())
src=ROOT/published['path_relative_to_panel']
assert hashlib.sha256(src.read_bytes()).hexdigest()==published['sha256']
workbook=load_workbook(src,data_only=True)
assert workbook.sheetnames==['toplusayfa']
w=workbook['toplusayfa']
assert [w.cell(1,c).value for c in range(12,30)]==[f'\u00e7{i}' for i in range(1,19)]
times=[];reba=[];mapping=[]
for j in range(18):
    assert w.cell(j+2,11).value==f'ist{j+1}'
    row=[]
    for i in range(18):
        c=w.cell(j+2,i+12);v=c.value;assert isinstance(v,(int,float)) and v>0
        q=Decimal(str(v)).quantize(Decimal('0.1'),rounding=ROUND_HALF_UP);row.append(str(q))
        mapping.append(['time',i+1,j+1,c.coordinate,str(v),str(q),str(q-Decimal(str(v)))])
    times.append([f'ist{j+1}',*row])
    c=w.cell(j+2,8);v=c.value;assert isinstance(v,(int,float)) and v>0
    q=Decimal(str(v)).quantize(Decimal('0.1'),rounding=ROUND_HALF_UP)
    reba.append([f'ist{j+1}',str(q)]);mapping.append(['reba','',j+1,c.coordinate,str(v),str(q),str(q-Decimal(str(v)))])
files={
 'processing_times_standard_1decimal.csv':[['station',*[f'W{i}' for i in range(1,19)]],*times],
 'reba_standard.csv':[['station','mean_reba'],*reba],
 'cell_mapping_and_rounding.csv':[['quantity','worker','station','source_cell_toplusayfa','source_value','standard_value','difference'],*mapping]}
for name,rows in files.items():
    with (out/name).open('w',newline='',encoding='utf-8') as f:csv.writer(f).writerows(rows)
    assert (out/name).read_bytes()==(ROOT/'standard_data_audit'/name).read_bytes(),name
report={'status':'PASS','source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'regenerated_files':list(files),'byte_identical_to_archive':True,'underlying_means_recalculated':False}
(out/'rebuild_verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
