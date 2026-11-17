# Protocol and certification of the revised results

## Common instance and objective definitions

All 18 coverage layers and both decision resolutions use the same standardized processing times and station REBA scores. A visit-count matrix q has nonnegative integer entries, every worker row sums to 18 and every station column sums to 18. At layer k, every worker visits at least k distinct stations. The retained count matrices are decomposed into 18 period assignments, each assigning every worker to one station and every station to one worker.

Let Pij = 10 pij and Rj = 10 rj be the integer standardized inputs. The bottleneck coordinate is C10 = max{Pij : qij > 0}. Worker load is Li = sum_j qij Rj, and Dsum = max_i Li - min_i Li. Reported objectives are C = C10/10 seconds and D = Dsum/180 score units. Exact zero disparity means Dsum = 0.

The mathematical regime M enumerates the nondominated objective vectors on this integer lattice. The practical regime P classifies objective vectors by bC = floor((2 C10 + 5)/10) and bD = floor((2 Dsum + 18)/36), with labels bC/2 and bD/10. Within a surviving class, the representative minimizes raw C first and raw D second. Neither S_total nor an additional S_min tie-break is optimized. The class resolutions are illustrative decision resolutions, not measured ergonomic indifference or measurement-error thresholds.

For each regime, the global front is obtained by taking the union over all 18 certified layers and applying three-dimensional nondominance with C and D minimized and k maximized. Equal objective coordinates at different k retain the largest nondominated certified k. Witness coverage is checked separately and is not substituted for this layer certification. There is no separately timed three-objective optimization.

## Primary timing panel

Layers 1, 3, 4, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16 and 18 use the common V1.1 four-stage scalarization: minimize C in the current D-bounded box, minimize D in the selected C class, minimize raw C in that class pair, and minimize raw D at the selected raw C. The remaining D-class bound decreases after each accepted point. An infeasible remaining box or the nonnegative D lower bound closes the layer.

The same scalarization, data, model, tolerances, one-thread setting, seed 20261019 and CPU affinity [0] are used for M and P. Odd k runs M then P; even k runs P then M. Runs use separate child processes without shared warm starts. Each regime was measured once. Total elapsed time spans child creation to exit, including initialization, model construction, all scalar calls, verification and output. The launcher polls at 0.2-second intervals. There is no imposed V1.1 per-call or layer time limit.

The panel contains 25 M and 21 P points, 100 and 84 scalar calls, and total times 1661.896469 and 1479.925305 seconds. P is 10.9496% shorter in aggregate. K16 contributes a large change, from 324.419159 to 6.614053 seconds; excluding K16 changes the aggregate direction to a 10.1560% increase for P. The comparison is descriptive and does not establish a general speedup.

## Follow-up algorithm and time limits

V2.1 uses a cumulative C-cap queue, with D minimization followed by C and D representative selection. This search differs from V1.1 even though the inputs and shared model are identical. For each scalar call, the first-incumbent search limit is 600 seconds and the proof allowance is 1800 seconds from the first incumbent. Later improving incumbents do not restart the proof clock. A native hard ceiling of 2400 seconds also applies per call. These budgets are not total layer limits. All retained K2/K5/K6 scalar calls terminated as optimal or infeasible; none terminated by time limit.

## K2 dominance closure

The raw M run has 96 closed caps and five unresolved caps at C10 = 759, 760, 763, 764 and 770. The 101 processed caps account for 254 scalar calls. All relevant caps at or below 715 are closed, and the feasible point (715,0) is established. Because Dsum is nonnegative, any candidate with C10 > 715 is dominated by (715,0). Thus the unresolved high-C regions cannot add a nondominated vector or alter a retained practical representative. The M front is {(688,112), (691,43), (693,26), (715,0)}. P completes its queue and retains representatives (691,43), (693,26) and (715,0).

The raw M `complete=false` flag remains unchanged: queue completion and mathematical frontier closure are different statements. The failed C tie calls in the high-C regions are numerically inconsistent with feasible zero-disparity witnesses, but the dominance argument makes those regions unnecessary for frontier completeness. This is not a claim that every infeasibility status in that run is valid.

## K5 targeted closure and representative correction

Both raw queues retain one unresolved region: M at C10 cap 692 and P at class cap 138. A prior D-optimal witness at (692,67) establishes feasibility, whereas the presolve-on C call reports infeasibility. A fresh targeted check disables presolve using the same HiGHS backend through SciPy, with the same seed, zero absolute/relative gap and 1e-7 feasibility tolerances. The C checks return matching primal and dual objective 691; the D tie checks at C10 = 691 return matching primal and dual objective 67. Their witnesses have zero recorded model-row violation and integrality error.

For M, the region has Dsum cap 67; for P it has Dsum cap 80, the upper limit of class bD = 4. The original D-class optimality, the fresh lexicographic checks and closure of the remaining caps complete the frontier argument. The M front is {(689,136), (691,67), (693,48), (715,0)}. P uses (691,67), (693,48) and (715,0).

The first P representative is therefore corrected from (692,67) to (691,67) in the derived tables. Raw results and their `complete=false` flags are preserved. The audit is a same-backend numerical cross-check, not an independent second-solver certificate. Its 2400-second per-call ceiling and audit times are separate from the primary panel.

## K6 completed follow-up

M closes all 68 caps in 204 scalar calls; P closes all 16 caps in 48 scalar calls. Both return `complete=true`. Their raw representative sets are {(700,58), (715,0)}. K6 is excluded from the primary timing comparison because its V2.1 search protocol differs from V1.1, not because its runs failed or timed out.

## K17 structural closure

The integer lower bounds and explicit attaining schedules in `K17_STRUCTURAL_CERTIFICATE.md` establish M = {(768,8), (771,2), (775,0)} and the single P class (154,0), represented by (768,8). These witnesses are also checked against the frozen model. No completed V2.1 M/P timing pair exists: a fresh M diagnostic was stopped at approximately 300 seconds without a completed scalar call, and P was not started. That diagnostic is not a 600 + 1800 second timeout or a completed timing observation.

## Why objective values are combined but timing is separated

The four follow-up layers share the same feasible set definition, input hashes, objective scaling, class boundaries and representative rule as the primary panel. Their additional closure evidence therefore permits combining certified objective sets across all 18 layers. Elapsed times depend on the search protocol and certification route. V2.1, targeted audit and structural proof workloads do not match the common V1.1 work definition, so their times are reported separately and excluded from the 14-layer M/P aggregate. Omitting their times does not omit their objective values.

The numerical qualification remains explicit: witness arithmetic verifies feasibility; solver-based optimality is accepted under the archived tolerances and terminal records. No rational solver-proof archive is supplied. Partial event traces are not treated as complete traces. The K17 proof is independent of optimizer termination and uses exact integer premises checked against the same input.
