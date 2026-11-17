# Exact structural certificate for coverage layer 17

This certificate uses the frozen standardized input, integer arithmetic and explicit schedules. It establishes the objective frontier independently of MILP termination. The separate timing diagnostic is incomplete and supplies no official M/P timing pair.

Let P = 10p and R = 10r. Each row of visit counts has 18 visits and at least 17 positive entries. Therefore it is either all ones, or it omits exactly one station j and repeats exactly one station l. Relative to the all-ones load B = sum_j Rj, a worker's load difference is delta = Rl - Rj, or zero for an all-ones row.

The station-column sums imply that omissions and repetitions balance at every station, and sum_i delta_i = 0. Treat each omission/repetition as an arc from the omitted station to the repeated station. Across any station subset, the number of outgoing arcs equals the number of incoming arcs. All differences are integers, and Dsum = max_i delta_i - min_i delta_i.

## Feasibility lower bound

No solution exists with C10 < 768. Every worker needs 17 available stations; the maximum across workers of the second-largest processing time is 768. The first archived witness attains C10 = 768.

## Disparity bound below 771

For C10 < 771, worker 8 must omit station 8 because P[8,8] = 771, using one-based indices. Its station score R = 57 is unique. The nearest lower score is 52 and the nearest higher score is 61.

If that worker repeats a higher-score station, its arc crosses the cut {R <= 57} to {R >= 61} and has delta >= 4. Station balance forces a reverse crossing with delta <= -4, so Dsum >= 8. If it repeats a lower-score station, delta <= -5 across the cut {R <= 52}/{R >= 57}; a reverse arc has delta >= 5, giving Dsum >= 10. Hence Dsum >= 8 in either case. An explicit witness attains (C10,Dsum) = (768,8).

## Disparity bound below 775

For C10 < 775, worker 2 must omit station 14 because P[2,14] = 775. Its score R = 52 is unique, so its delta is a nonzero integer. Since all deltas sum to zero, an opposite-sign delta exists. Therefore Dsum >= 2. A second witness attains (771,2).

## Equality and complete front

At C10 = 775, the all-ones matrix is feasible and gives Dsum = 0. No negative disparity is possible. The bounds cover the full C axis: below 768 is infeasible; [768,771) requires Dsum >= 8; [771,775) requires Dsum >= 2; and at or above 775, Dsum >= 0. The three schedules attain each lower-envelope level. Thus the complete M frontier is exactly {(768,8), (771,2), (775,0)}.

The P class labels are respectively (77.0,0.0), (77.0,0.0) and (77.5,0.0). Only class (77.0,0.0) survives class dominance. Within it, minimizing raw C and then raw D selects (768,8). Its displayed zero disparity is a class label; the raw value is 8/180 = 2/45. The witnesses and schedules are in `03_REPRODUCIBILITY/K17_STRUCTURAL/K17_INDEPENDENT_ORACLE/EXACT_REFERENCE.json`; the deterministic construction is `k17_structural_oracle.py` in its parent directory.
