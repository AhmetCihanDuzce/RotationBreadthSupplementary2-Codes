# Supplementary data dictionary

CSV files use UTF-8, comma separators, decimal points and a header row. `True`/`False` are Boolean values. k, objective integers and class indices are integers. Fractions such as `2/45` are exact textual fractions. No table contains missing numerical measurements encoded as zero.

## Shared definitions

| Field | Definition |
|---|---|
| `k` | Certified minimum number of distinct stations visited by every worker; 1 to 18 |
| `regime` | `M`: mathematical integer-lattice objectives; `P`: practical objective classes |
| `C10` | Raw bottleneck processing time multiplied by 10; integer |
| `Dsum` | Range of integer worker load sums; reported D = Dsum/180 |
| `C_seconds` | C10/10, in seconds |
| `D_fraction` | Exact reduced fraction for Dsum/180 |
| `D` | Decimal display of Dsum/180; use Dsum or D_fraction for exact comparisons |
| `class_C`, `class_D` | Practical class indices bC = (2*C10+5)//10 and bD = (2*Dsum+18)//36 in the derived tables, including M rows |
| `C_label`, `D_label` | Practical labels bC/2 seconds and bD/10 score units |
| `Smin_witness` | Actual minimum station count of the selected feasible witness; may exceed k |
| `closure_basis` | Evidence route supporting the layer frontier |
| `source` | Relative path inside the companion reproducibility package to the original run or targeted audit |

**Raw-format distinction:** frozen solver `result.json` uses `class_C=C10` and `class_D=Dsum` for M. The derived S2 table uses practical class projections in these fields for both M and P. In all formats the raw `C10` and `Dsum` fields have the same meaning.

## S1 all layers

`S1_all18_layers.csv` has 18 rows. `M_points` and `P_classes` count nondominated objective vectors/classes within each fixed-k layer, not all distinct schedules. `Cmin_s` is the mathematical layer's minimum C; `D_at_Cmin_fraction` is its associated exact D. `C_at_D0_s` is the lowest mathematical C attaining exact D = 0. `timing_in_primary_panel` identifies the 14 common-protocol pairs. Layer counts must not be mistaken for the global count after cross-layer dominance filtering.

## S2 all selected layer records

`S2_all68_layer_records.csv` contains 38 M records and 30 P representatives. `source` for the corrected K5 P vector (691,67) points to the targeted audit. These 68 rows are selected witness records, not necessarily 68 distinct schedules or 68 distinct global objective vectors. Some records appear in multiple layers or regimes.

## S3 and S4 global fronts

`S3_global_M_28.csv` contains 28 nondominated triples (C,D,k), with C and D minimized and k maximized. `retained_as_P_representative` indicates that the identical raw triple is the selected representative of a retained global P class at the same k.

`S4_global_P_17.csv` contains 17 nondominated triples (bC,bD,k), plus each selected raw representative. P class labels and raw coordinates are deliberately both provided. A P label D = 0 covers [0,0.05), while exact equality requires Dsum = 0.

## S5 primary timing panel

`S5_paired14_timing.csv` has 14 rows. `M_total_s` and `P_total_s` are recorded child-creation-to-exit elapsed seconds, not summed solver-only time. `M_calls` and `P_calls` count scalar MILPs. `M_over_P` is M_total_s/P_total_s. Values above one mean P was faster in that observed pair. All times are single observations; no standard deviation or confidence interval is implied.

## S6 follow-up status

`S6_followup_run_status.csv` has six rows, M/P for K2/K5/K6. `raw_complete` is the original queue flag, without retrospective rewriting. `closed_caps` and `unresolved_caps` are disjoint array lengths; their sum is the number of processed caps because the pending queues are empty. `scalar_calls`, `optimal_calls` and `infeasible_calls` describe retained terminal statuses. Some infeasibility outcomes in unresolved K2/K5 tie calls are contradicted by witnesses; completeness uses the separate closure arguments.

`longest_scalar_s` is the largest archived `total_call_seconds`, including model preparation and native solver time. `original_elapsed_s` is the original whole-run elapsed time. `primary_timing_eligible` is false for all six rows. K17 has no completed pair and is described separately; no zero or imputed elapsed time is inserted for it.

## Witnesses and JSON evidence

`SELECTED_WITNESSES.json` holds all 68 selected layer records. `counts[i][j]` is the visit count for zero-based worker i and station j. `schedule_station_by_worker_period[i][t]`, or `schedule[i][t]` in the audit/oracle formats, is a **one-based station identifier** for worker i in period t. Both matrices are 18 by 18. Every period is a permutation of stations 1–18, and counting all periods reconstructs `counts`. Some witnesses include redundant raw values or source-specific QA fields; `C10`, `Dsum`, k, counts and schedule are the common evidence.

`METRICS_AND_QA.json` contains aggregate counts, percentage changes and verification flags. `P_range_seconds` is the processing-time input range, not the P-regime objective range. `COMMON_INPUT_AND_MODEL_HASHES.json` compares the two standardized CSVs and the shared `legacy_model.py` and `runner.py` across five evidence groups. It does not claim that V1.1 and V2.1 search control is identical: V2.1 also uses `bounded.py`.

## Figure definitions

`Figure1_global_EN.png` gives two projections of the three-objective front, raw C versus k and raw D versus k. P markers show selected raw representatives, not rounded class labels. These projections are not separate two-dimensional Pareto frontiers.

`Figure2_resolution_EN.png` shows the raw M layer vectors and retained P representatives for k = 3, 16 and 17. Connecting lines guide the eye; they do not assert feasible interpolation between discrete schedules.

`Figure3_timing_EN.png` compares the 14 paired V1.1 elapsed times on a logarithmic vertical axis. K2/K5/K6/K17 are absent from this timing panel for the protocol/certification reasons in the accompanying note.
