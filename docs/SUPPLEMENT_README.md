# Supplementary material

English release • 22 October 2026

Companion to **Ergonomic fairness, rotation breadth and decision resolution in automotive assembly**.

Start with `Supplementary_Material_EN.docx`. It describes the common inputs, exact and practical objective definitions, all 18 layers, the global fronts, the 14-layer timing comparison, and the additional completeness evidence for K2, K5, K6 and K17.

## Contents

| File or directory | Contents |
|---|---|
| `Supplementary_Material_EN.docx` | English supplementary narrative, tables and methodological qualifications |
| `tables/S1_all18_layers.csv` | 18 layer summaries |
| `tables/S2_all68_layer_records.csv` | All 38 M vectors and 30 P representatives, with exact values and provenance |
| `tables/S3_global_M_28.csv` | 28 global mathematical triples |
| `tables/S4_global_P_17.csv` | 17 global practical classes and their raw representatives |
| `tables/S5_paired14_timing.csv` | Common-protocol M/P elapsed times and scalar-call counts for 14 layers |
| `tables/S6_followup_run_status.csv` | Original K2/K5/K6 completion flags, caps, calls and separate elapsed times |
| `figures/` | Three English scientific figures in PNG format |
| `evidence/SELECTED_WITNESSES.json` | All 68 selected count matrices and period schedules |
| `evidence/METRICS_AND_QA.json` | Derived counts, percentages and arithmetic checks |
| `evidence/COMMON_INPUT_AND_MODEL_HASHES.json` | Matching inputs and shared model files across the evidence groups |
| `evidence/SEEDS_AND_SETTINGS.json` | Solver seed, test seeds and protocol/environment settings |
| `DATA_DICTIONARY.md` | Units, field definitions, indexing and figure captions |
| `PROTOCOL_AND_CERTIFICATION.md` | Full protocol and K2/K5/K6 closure explanations |
| `K17_STRUCTURAL_CERTIFICATE.md` | Complete integer structural proof for K17 |
| `FILE_MANIFEST_SHA256.json` | SHA-256 checksums of the distributed files except itself |

## Reading the results

The 38 M layer vectors and 30 P layer classes become 28 M and 17 P global nondominated triples after filtering across layers with C and D minimized and k maximized. The global class count decreases by 39.2857%. These are objective vectors/classes, not a count of every possible schedule.

P uses the same standardized input as M. It applies objective-class resolutions of 0.5 seconds and 0.1 score units. A displayed P disparity of zero represents [0,0.05); exact equality requires `Dsum=0`. Raw values are supplied beside all practical labels.

The timing comparison uses only the 14 common V1.1 pairs. K2/K5/K6 use a different V2.1 search, K2 and K5 require additional closure evidence, and K17 is closed by a structural proof. Their objective values enter the global fronts, while their heterogeneous certification times do not enter the primary timing aggregate. K6 completed both regimes; exclusion is not a failure classification. The 600 + 1800 second V2.1 allowance is per scalar MILP, not per layer. No archived K2/K5/K6 scalar call timed out.

The first K5 P representative is corrected from (C10,Dsum) = (692,67) to (691,67) using the targeted presolve-off audit. The companion code archive preserves original raw files and flags. K2's correct cap count is 96 closed + 5 unresolved = 101 processed.

## Reproduce these files

Use the separate `Verimli_Rotasyon_Reproducibility_EN_2026-10-22.zip`. It contains frozen solver code, the public model input workbook, standardized inputs, raw results, audit/oracle scripts, a seed register and a detailed English README. From its extracted root:

```bash
python -m pip install -r requirements-analysis.txt
python scripts/reproduce.py verify --output ../rotation_verification
```

This regenerates the reference tables and figures without launching MILP searches. S2 `source` paths refer to the **companion reproducibility package root**, not to this supplementary ZIP. Repeated witness records across layers or regimes should not be interpreted as distinct experimental replications.

Recorded MILP optimality is subject to the supplied numerical tolerances and closure evidence. Witness checks establish feasibility and arithmetic; they do not independently prove MILP optimality. The K17 structural proof provides a separate exact integer argument. Full environment and archival limitations are documented in the companion README.
