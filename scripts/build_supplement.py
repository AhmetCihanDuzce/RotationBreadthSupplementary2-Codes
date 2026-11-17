from pathlib import Path
import csv,json,shutil
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT

import argparse
R=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description='Build the English supplementary Word document and companion data in a new directory.')
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
S=args.output.resolve();S.mkdir(parents=True,exist_ok=False)
for sub in ['tables','figures','evidence']:(S/sub).mkdir()
shutil.copy2(R/'docs/SUPPLEMENT_README.md',S/'README.md')
A=R/'02_SUPPLEMENTARY'
for p in A.iterdir():
    dest=S/('tables' if p.suffix=='.csv' else 'figures' if p.suffix=='.png' else 'evidence')/p.name
    shutil.copy2(p,dest)
for name in ['DATA_DICTIONARY.md','PROTOCOL_AND_CERTIFICATION.md','K17_STRUCTURAL_CERTIFICATE.md']:shutil.copy2(R/'docs'/name,S/name)
shutil.copy2(R/'SEEDS_AND_SETTINGS.json',S/'evidence/SEEDS_AND_SETTINGS.json')
def rows(n):return list(csv.DictReader((A/n).open()))
d=Document();sec=d.sections[0]
sec.page_width=Inches(8.5);sec.page_height=Inches(11)
sec.top_margin=sec.bottom_margin=Inches(.7);sec.left_margin=sec.right_margin=Inches(.75)
sec.footer_distance=Inches(.3)
for name in ['Normal','Title','Subtitle','Heading 1','Heading 2','Caption']:
    st=d.styles[name];st.font.name='Calibri';st.font.color.rgb=RGBColor(0,0,0)
for style in d.styles:
    for border in list(style.element.iter(qn('w:pBdr'))):
        border.getparent().remove(border)
d.styles['Normal'].font.size=Pt(11)
d.styles['Normal'].paragraph_format.line_spacing=1.06
d.styles['Normal'].paragraph_format.space_after=Pt(7)
d.styles['Title'].font.size=Pt(23)
d.styles['Title'].paragraph_format.space_after=Pt(10)
d.styles['Heading 1'].font.size=Pt(16)
d.styles['Heading 1'].paragraph_format.space_after=Pt(9)
d.styles['Heading 2'].font.size=Pt(12)
d.styles['Heading 2'].paragraph_format.space_before=Pt(9)
d.styles['Heading 2'].paragraph_format.space_after=Pt(5)
d.styles['Caption'].font.size=Pt(10)
d.styles['Caption'].font.italic=False
d.styles['Caption'].paragraph_format.space_before=Pt(7)
d.styles['Caption'].paragraph_format.space_after=Pt(5)
d.core_properties.title='Supplementary material for automotive job rotation'
d.core_properties.subject='All 18 coverage layers, objective resolution, timing and completeness evidence'
d.core_properties.author=''
d.core_properties.keywords='job rotation, Pareto frontier, reproducibility, mathematical optimization'
foot=sec.footer.paragraphs[0];foot.alignment=WD_ALIGN_PARAGRAPH.RIGHT
run=foot.add_run('Supplementary material | ');run.font.size=Pt(9)
f=OxmlElement('w:fldSimple');f.set(qn('w:instr'),'PAGE');foot._p.append(f)

def p(s):return d.add_paragraph(s)
def h(s):return d.add_heading(s,1)
def h2(s):return d.add_heading(s,2)
def page(title):h(title).paragraph_format.page_break_before=True
def table(caption,headers,records,widths):
    c=d.add_paragraph(caption,'Caption');c.paragraph_format.keep_with_next=True
    t=d.add_table(rows=1,cols=len(headers));t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
    pr=t._tbl.tblPr;borders=OxmlElement('w:tblBorders')
    for side in ['top','left','bottom','right','insideH','insideV']:
        b=OxmlElement('w:'+side);b.set(qn('w:val'),'single');b.set(qn('w:sz'),'4');b.set(qn('w:color'),'D9D9D9');borders.append(b)
    pr.append(borders)
    for col,w in zip(t.columns,widths):col.width=Inches(w)
    for j,text in enumerate(headers):t.rows[0].cells[j].text=text
    for record in records:
        for cell,text in zip(t.add_row().cells,record):cell.text=str(text)
    for i,row in enumerate(t.rows):
        no=OxmlElement('w:cantSplit');row._tr.get_or_add_trPr().append(no)
        if i==0:
            repeat=OxmlElement('w:tblHeader');row._tr.get_or_add_trPr().append(repeat)
        for j,cell in enumerate(row.cells):
            cell.width=Inches(widths[j]);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            cp=cell._tc.get_or_add_tcPr();mar=OxmlElement('w:tcMar')
            for side,val in [('top','35'),('bottom','35'),('left','80'),('right','80')]:
                el=OxmlElement('w:'+side);el.set(qn('w:w'),val);el.set(qn('w:type'),'dxa');mar.append(el)
            cp.append(mar)
            if i==0:
                sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'E8EDF2');cp.append(sh)
            for para in cell.paragraphs:
                para.alignment=WD_ALIGN_PARAGRAPH.CENTER
                para.paragraph_format.space_before=Pt(0);para.paragraph_format.space_after=Pt(0);para.paragraph_format.line_spacing=1.03
                for run in para.runs:run.font.size=Pt(9.5);run.font.bold=i==0
    gap=d.add_paragraph();gap.paragraph_format.space_after=Pt(0);gap.paragraph_format.space_before=Pt(0);gap.paragraph_format.line_spacing=Pt(3)
    return t

d.add_paragraph('Supplementary material for automotive job rotation','Title')
p('Companion to “Ergonomic fairness, rotation breadth and decision resolution in automotive assembly”')
p('English release • 22 October 2026')
h('1 Study scope and objective definitions')
p('This supplement reports the mathematical and practical objective sets for all 18 minimum-coverage layers, their combined global fronts, and the paired elapsed-time comparison for 14 layers evaluated under a common protocol. It also documents the additional evidence used to close K2, K5, K6 and K17. The global mathematical front contains 28 triples; the practical front contains 17 classes, a reduction of 39.29%.')
h2('Common input and feasible schedules')
p('The case contains 18 workers, 18 stations and 18 equal periods. Every period assigns each worker to exactly one station and each station to exactly one worker. The integer visit-count matrix q has row and column sums of 18. At coverage layer k, each worker visits at least k distinct stations. Every retained witness includes a count matrix and a valid 18-period schedule.')
p('The authoritative workbook summary is worksheet toplusayfa: processing times are in L2:AC19 and mean REBA scores in H2:H19. Cached numerical means are rounded once to one decimal place using decimal ROUND_HALF_UP. Of 324 time entries, 220 change; 17 of 18 REBA entries change. Standardized processing times range from 61.5 to 77.5 seconds and scores from 3.6 to 6.8. CSV rows are stations and columns are workers; the model transposes once. The public workbook contains the final summary values used as model inputs. Pilot and individual measurement records are excluded from the public release.')
h2('Mathematical and practical objectives')
p('Let Pij = 10 pij and Rj = 10 rj be the integer inputs. The bottleneck coordinate is C10 = max{Pij : qij > 0}. For integer worker loads Li = sum_j qij Rj, Dsum = max_i Li − min_i Li. Reported values are C = C10/10 seconds and D = Dsum/180 score units. Regime M uses this input-derived integer lattice.')
p('Regime P uses the same input and feasible model. Its class indices are bC = floor((2 C10 + 5)/10) and bD = floor((2 Dsum + 18)/36), with labels bC/2 seconds and bD/10. Thus the illustrative decision resolutions are 0.5 seconds and 0.1 score units. Each retained class is represented by minimum raw C followed by minimum raw D. No additional coverage or total-coverage tie-break is optimized.')
p('A P label D = 0 covers [0, 0.05); exact equality requires Dsum = 0. These class resolutions are not empirically established measurement-error bounds or ergonomic indifference thresholds. Raw values accompany every practical label in the data tables.')

page('2 Results for all 18 coverage layers')
p('Table S1 summarizes each fixed-k layer before cross-layer dominance filtering. Counts refer to objective vectors or practical classes, rather than all possible schedules. The complete selected records, including raw coordinates, practical projections, witness coverage and source paths, are provided electronically in Table S2.')
rr=rows('S1_all18_layers.csv')
table('Table S1. Layer counts and mathematical endpoints.', ['k','M points','P classes','Minimum\nC (s)','D at\nminimum C','C at exact\nD = 0 (s)','Primary\ntiming'], [[r['k'],r['M_points'],r['P_classes'],r['Cmin_s'],r['D_at_Cmin_fraction'],r['C_at_D0_s'],'Yes' if r['timing_in_primary_panel']=='True' else 'No'] for r in rr],[.4,.7,.7,1.0,1.25,1.5,1.45])
p('Across the 18 layers, there are 38 M vectors and 30 P classes, a 21.05% reduction before cross-layer filtering. The mathematical minimum C attaining exact equality is 71.5 seconds for layers 1–6. Full rotation, k = 18, requires C = 77.5 seconds and has D = 0.')
p('The 14 primary timing layers are 1, 3, 4, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16 and 18. The objective values of K2, K5, K6 and K17 remain part of the global-front calculation; only their heterogeneous certification times are separated from the primary elapsed-time comparison.')
h2('Electronic Table S2 and witness records')
p('S2_all68_layer_records.csv contains all 38 M records and 30 P representatives. SELECTED_WITNESSES.json supplies their count matrices and schedules. These are 68 selected records; repetition across layers or regimes does not imply 68 distinct schedules or independent experimental replications. All 68 records pass integer objective and schedule checks.')

page('3 Global mathematical frontier')
p('The global front is the nondominated subset of the union of all certified layer triples (C,D,k), with C and D minimized and k maximized. The last column flags the identical raw triples selected for retained P classes at the same k. This is not a two-dimensional C–D union or a separately timed three-objective search.')
rr=rows('S3_global_M_28.csv')
table('Table S3. Global mathematical triples and practical retention.', ['k','C10','Dsum','C (s)','Exact D','Selected as P\nrepresentative'], [[r['k'],r['C10'],r['Dsum'],r['C_seconds'],r['D_fraction'],'Yes' if r['retained_as_P_representative']=='True' else 'No'] for r in rr],[.5,.85,.85,1.0,1.6,2.2])


page('4 Global practical frontier')
p('Table S4 contains the 17 nondominated practical triples (bC,bD,k). The labels express decision classes; raw values describe the actual selected schedules. The global count is 39.29% lower than the 28-vector mathematical front.')
rr=rows('S4_global_P_17.csv')
table('Table S4. Global practical classes and selected raw coordinates.', ['k','bC','bD','C label\n(s)','D label','Raw C\n(s)','Exact raw D'], [[r['k'],r['class_C'],r['class_D'],r['C_label'],r['D_label'],r['C_seconds'],r['D_fraction']] for r in rr],[.4,.65,.65,1.1,1.0,1.1,1.9])
h2('Consequences of coarser objective classes')
p('For K3 and K4, the minimum mathematical C is 68.8 seconds, while the first retained practical representative has C = 69.1 seconds. At K16, P keeps (75.9, 1/36), while M also offers exact equality at C = 76.7 seconds. A practical zero-disparity label therefore can hide a meaningful distinction between small positive disparity and exact equality.')
p('At K17, the raw vectors (76.8, 2/45) and (77.1, 1/90) share class (77.0, 0.0), represented by the first. Across layers, zero-disparity C values 72.5, 72.6 and 72.7 at k = 9, 10 and 11 share the C label 72.5, so the higher-coverage class survives. These examples show why the class count and the raw decision alternatives should be reported together.')
p('Projecting the mathematical global front into practical classes and filtering again reproduces the 17-class P front. Every selected P raw triple is also present on the M global front. These checks concern this instance and the stated representative rule; they do not imply that coarsening preserves every mathematical alternative.')

page('5 Paired timing panel')
p('The common V1.1 protocol uses the same four-stage scalarization for M and P: C minimization, D minimization within the selected C class, raw-C representative selection, and raw-D tie resolution. Both regimes use the same inputs, model, seed, tolerances and one-thread environment. There is no per-call or layer time limit in this panel.')
rr=rows('S5_paired14_timing.csv')
table('Table S5. Recorded elapsed times and scalar MILP counts.', ['k','M time (s)','P time (s)','M calls','P calls','M / P time'], [[r['k'],f"{float(r['M_total_s']):.3f}",f"{float(r['P_total_s']):.3f}",r['M_calls'],r['P_calls'],f"{float(r['M_over_P']):.3f}"] for r in rr]+[['Total','1661.896','1479.925','100','84','1.123']],[.5,1.5,1.5,1.0,1.0,1.5])
p('Elapsed time spans child-process creation to exit, including initialization, model construction, all solver calls, witness verification and output. The launcher polls every 0.2 seconds. Odd k runs M then P; even k runs P then M. Each regime is measured once in a separate process, without shared warm starts.')
p('P reduces the panel point count from 25 to 21 and the scalar-call count from 100 to 84, both by 16%. The total elapsed time is 10.95% shorter for P. This aggregate is sensitive to K16, which changes from 324.419 to 6.614 seconds. Excluding K16 yields totals of 1337.477 seconds for M and 1473.311 seconds for P, making P 10.16% slower.')
p('The results support a descriptive statement about the observed panel, not a general speedup claim. The very short K18 runs differ by approximately one millisecond, which is not a meaningful timing advantage under this measurement setup. The electronic table retains unrounded values; Figure3_timing_EN.png uses a logarithmic vertical axis.')

page('6 Follow up experiments and closure')
p('V2.1 evaluates cumulative C caps, with D minimization followed by C and D representative selection. Each scalar MILP receives up to 600 seconds to find its first incumbent and 1800 further seconds from that incumbent for proof. Later improvements do not restart the clock; the native hard ceiling is 2400 seconds per call. These are not total layer budgets. None of the retained K2/K5/K6 calls timed out.')
rr=rows('S6_followup_run_status.csv')
table('Table S6. Follow-up raw status and separate run times.', ['k','Regime','Raw\ncomplete','Closed\ncaps','Unresolved\ncaps','Scalar\ncalls','Elapsed\n(s)'], [[r['k'],r['regime'],'Yes' if r['raw_complete']=='True' else 'No',r['closed_caps'],r['unresolved_caps'],r['scalar_calls'],f"{float(r['original_elapsed_s']):.3f}"] for r in rr],[.4,.65,1.05,1.0,1.25,1.05,1.6])
h2('K2 dominance closure')
p('M has 96 closed caps and five unresolved caps at C10 = 759, 760, 763, 764 and 770, hence 101 processed caps. Every relevant cap at or below 715 is closed, and (715,0) is established. Nonnegative Dsum means that (715,0) dominates every possible candidate with C10 > 715. The unresolved high-C regions cannot add a nondominated vector. The raw M complete=false flag is retained; frontier closure follows from dominance. P completes its queue.')
h2('K5 targeted audit')
p('Both queues leave one unresolved region, at M cap 692 and P class cap 138. A feasible D-optimal witness (692,67) contradicts the presolve-on C call’s infeasibility outcome. Fresh checks with presolve disabled return matching primal and dual objective 691 for C and 67 for the subsequent D tie. Witness model-row and integrality errors are zero. The P representative is corrected to (691,67) in derived tables, while raw files and flags remain unchanged. The audit uses the same HiGHS backend, not a second solver, and its times are excluded from the primary panel.')
h2('K6 completion and timing eligibility')
p('K6 completes both queues: M closes 68 caps in 204 calls and P closes 16 caps in 48 calls. It is excluded from the primary timing aggregate because V2.1 uses a different search protocol. Across all four follow-up layers, common inputs, feasible models, scaling and class rules permit combining certified objective values. Search and certification workloads differ, so elapsed times are reported separately. K17 is covered by the structural proof on the next page.')

page('7 Exact structural certificate for K17')
p('The structural certificate uses the same standardized integer input and explicit attaining schedules. A row of visit counts has 18 visits and at least 17 positive entries. It is therefore either all ones or has exactly one omitted station j and one repeated station l. Relative to the all-ones load B = sum_j Rj, the worker load difference is delta = Rl − Rj, or zero for an all-ones row.')
p('Column sums require omitted and repeated station counts to balance at each station, and all worker deltas sum to zero. Represent an omission/repetition by an arc from the omitted station to the repeated station. Across any subset of stations, the number of outgoing arcs equals the number of incoming arcs. Dsum is the range of these integer deltas.')
h2('Feasibility lower bound')
p('Every worker needs 17 available stations. The maximum, over workers, of the second-largest processing time is 768. Thus C10 < 768 is infeasible; an explicit schedule attains C10 = 768.')
h2('Disparity below C10 equal to 771')
p('For C10 < 771, worker 8 must omit station 8 because P[8,8] = 771, using one-based indices. Its score R = 57 is unique. The nearest lower score is 52 and the nearest higher score is 61. Repeating a higher-score station creates an arc across {R ≤ 57}/{R ≥ 61} with delta ≥ 4. Station balance forces a reverse crossing with delta ≤ −4, so Dsum ≥ 8. Repeating a lower-score station yields delta ≤ −5 and a reverse delta ≥ 5, so Dsum ≥ 10. Hence Dsum ≥ 8 in either case. A witness attains (768,8).')
h2('Disparity below C10 equal to 775')
p('For C10 < 775, worker 2 must omit station 14 because P[2,14] = 775. Its score R = 52 is unique, so its delta is a nonzero integer. Since all deltas sum to zero, an opposite-sign delta must exist, giving Dsum ≥ 2. A second witness attains (771,2). At C10 = 775, the all-ones count matrix is feasible and attains Dsum = 0.')
h2('Complete objective sets and separate timing status')
p('These bounds cover the full axis: C10 < 768 is infeasible; [768,771) requires Dsum ≥ 8; [771,775) requires Dsum ≥ 2; and C10 ≥ 775 requires Dsum ≥ 0. The three attaining witnesses establish the complete M front {(768,8), (771,2), (775,0)}. Their P labels are (77.0,0.0), (77.0,0.0) and (77.5,0.0). Only class (77.0,0.0) survives, represented by (768,8).')
p('The deterministic oracle and a check against the frozen model are included in the companion code package. There is no completed K17 M/P timing pair: the M diagnostic stopped at about 300 seconds without a completed scalar call; P was not started. That diagnostic is neither a completed observation nor a 600 + 1800 second timeout.')

page('8 Reproducibility and interpretation limits')
table('Table S7. Seeds and recorded computational settings.', ['Component','Value or policy'],[
 ['Official solver seed','20261019 for every scalar MILP'],
 ['Exhaustive fixture seeds','1, 2, 3 and 4; validation only'],
 ['Time-limit fixture seed','9; native timeout validation only'],
 ['Factory data and K17 oracle','No generation seed; oracle is deterministic'],
 ['Python / NumPy','3.12.14 / 2.3.5'],
 ['SciPy / bundled HiGHS','1.17.0 / 1.8.0'],
 ['Solver threads / CPU affinity','1 / [0]'],
 ['Relative and absolute MIP gap','0 / 0'],
 ['Primal, dual and MIP feasibility tolerances','1e-7 for each'],
 ['Presolve','On in official searches; off in closing K5 audit checks'],
 ['Primary panel repetitions','One M and one P run per included layer'],
 ],[3.1,3.9])
p('The companion reproducibility ZIP contains frozen solver code, input data, the public model input workbook, retained solver runs, the K5 audit, K17 oracle, seeds and English execution instructions. The read-only verification command rebuilds all CSV/JSON reference outputs and English figures without solving a MILP. Separate commands reconstruct the standardized inputs, rerun a selected layer or audit, and regenerate the K17 certificate in a new directory.')
p('The 68 selected records pass integer count, coverage, objective and schedule checks. Every layer’s mathematical-to-practical projection matches its P classes, and the global projection matches the 17-class practical front. Input and shared model hashes match across all five evidence groups. V1.1 and V2.1 search control nevertheless differs.')
p('MILP optimality remains subject to recorded numerical tolerances and terminal solver outcomes. Feasible-witness arithmetic is not an independent optimality proof, and no rational branch-and-bound proof archive is supplied. K2 uses dominance closure; K5 uses a same-backend presolve-off numerical audit; K17 has an exact integer structural argument. Partial V2.1 event logs are preserved as partial logs, with full call arrays and states retained separately.')
p('The original CPU model, binary wheel set and container image are not archived. Host load was not fully controlled, and a single paired observation per layer cannot establish statistical significance or portable elapsed times. Version pins and fixed seeds support reproducibility of the procedure but do not guarantee identical schedules, solver paths or execution times on different systems.')
p('Electronic Tables S1–S6, exact witness JSON, checksums and the data dictionary accompany this document. The three English figures use those same data. Their captions and coordinate conventions are stated in DATA_DICTIONARY.md. The implementation is a newly implemented DPA-style objective-box search; it is not author-supplied code for a published DPA and supplies no AUGMECON performance comparison.')

out=S/'Supplementary_Material_EN.docx';d.save(out)
print(out)
