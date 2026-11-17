# Verimli Rotasyon reproducibility package

English release • Public summary edition, 11 November 2026

Companion to **Ergonomic fairness, rotation breadth and decision resolution in automotive assembly**. The package contains the standardized inputs, unchanged solver implementations, retained run evidence, seeds, verification scripts and the analysis that produces the revised results. The instance has 18 workers, 18 stations and 18 equal periods.

The complete mathematical and practical objective sets cover all 18 coverage layers. The primary timing comparison covers 14 layers under a common V1.1 protocol. K2, K5, K6 and K17 contribute objective values but are excluded from that timing aggregate for the reasons in `docs/PROTOCOL_AND_CERTIFICATION.md`.

## Start here

Extract the ZIP and open a terminal in this directory. Use Python 3.12.14 for the recorded solver environment. A Python virtual environment is recommended:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/reproduce.py check-environment
```

The recorded versions are NumPy 2.3.5, SciPy 1.17.0, HiGHS 1.8.0 and openpyxl 3.1.5. Matplotlib 3.10.8 is used for analysis figures. The solver imports SciPy's private `scipy.optimize._highspy._core` interface. A distribution with a different bundled HiGHS version is not the recorded environment, even if its SciPy version matches. No original binary wheel set, container image or exact CPU model is archived. The preflight command reports version differences; it does not install or reconstruct the original binary environment.

If you only need to regenerate tables and figures from the archived results, `requirements-analysis.txt` is sufficient. This workflow does not import a MILP solver:

```bash
python -m pip install -r requirements-analysis.txt
python scripts/reproduce.py verify --output ../rotation_verification
```

The output directory must not already exist. The command checks the release manifest, all 28 primary-panel runs, 68 selected witness records, all layer projections, global dominance, follow-up cap coverage and the K5 audit values. It regenerates the English CSVs, figures and JSON files in `../rotation_verification/derived`, and compares the regenerated CSV/JSON files with the distributed references. The expected final message is `PASS: archived references reproduced without MILP calls.` Figures may have binary-level rendering differences across platforms; their numerical sources are checked separately.

For analysis alone, without the full release checks:

```bash
python scripts/analyze_results.py --output ../rotation_derived
```

This command writes only to the selected derived-output directory; it never changes retained run evidence. Do not use Python's `-O` option: the scientific consistency checks use assertions.

To rebuild the English supplementary Word document as well:

```bash
python -m pip install -r requirements-document.txt
python scripts/build_supplement.py --output ../rotation_supplement_rebuilt
```

This creates a new directory containing the DOCX, English README, tables, figures and evidence files. The distributed DOCX was rendered and every page visually reviewed; Word/LibreOffice layout may vary with locally installed fonts.

## Seeds and settings

`SEEDS_AND_SETTINGS.json` is the complete settings register. `SEED_REGISTER.csv` extracts the seed and environment from 35 archived environment files: 28 primary runs, six follow-up runs and one incomplete K17 diagnostic. The diagnostic is not an additional completed experiment.

| Use | Seed | Interpretation |
|---|---:|---|
| Official scalar MILPs in M and P | 20261019 | The same explicit HiGHS seed for every layer and scalar call |
| K5 targeted audit | 20261019 | Same backend and seed; presolve disabled for the closing checks |
| Exhaustive small-instance fixtures | 1, 2, 3, 4 | Synthetic input generation for validation only |
| Native time-limit fixture | 9 | Synthetic 12-worker fixture in the V2 test harness only |
| Factory instance | Not applicable | Observed data, not randomly generated |
| K17 structural oracle | Not applicable | Deterministic integer construction, no optimizer |

The official runs use one solver thread, CPU affinity `[0]`, and `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS` and `NUMEXPR_NUM_THREADS` all set to `1`. Relative and absolute MIP gaps are zero; primal, dual and MIP feasibility tolerances are `1e-7`. These settings do not eliminate numerical tolerances or guarantee identical witnesses or times on another machine.

## Reproduce the standardized inputs

```bash
python scripts/rebuild_standard_data.py --output ../rotation_rebuilt_inputs
```

The public workbook `project_sources/Verimli_Rotasyon_Model_Inputs.xlsx` under the V1.1 panel contains only the final model inputs from `toplusayfa`: 324 summary processing times in `L2:AC19`, 18 summary REBA coefficients in `H2:H19`, and coded station and worker labels. Pilot worksheets and individual measurement records are excluded from this release. The script applies decimal ROUND_HALF_UP once to one decimal place and compares all three generated CSVs byte-for-byte with the archive. CSV time rows are stations and columns are workers; the model transposes once. This verifies the preparation of the model inputs from the final summary values.

## Optional solver reruns

These commands perform optimization and can take substantial time. They write into new directories and preserve the archived evidence. No full 18-worker optimization was launched when preparing this English release.

Run a single V1.1 layer pair (example K1):

```bash
python scripts/reproduce.py solve --layer 1 --regime PAIR --output ../rotation_k01_rerun
```

V1.1 is available for layers `1,3,4,7,8,9,10,11,12,13,14,15,16,18`. Odd layers run M then P; even layers run P then M. Each regime is a separate process, without shared warm starts. The original V1.1 protocol has no per-call or layer time limit. Select `--regime M` or `--regime P` for a single regime.

Run a V2.1 follow-up pair (example K6):

```bash
python scripts/reproduce.py solve --layer 6 --regime PAIR --output ../rotation_k06_rerun
```

V2.1 is available for layers `2,5,6` and runs M then P. Each scalar MILP has up to 600 seconds to find the first incumbent, then up to 1800 additional seconds from that first incumbent to finish its proof. Later improvements do not reset the clock. A 2400-second native hard ceiling also applies to each call. The layer contains many calls; these are not total layer budgets. The archived K2/K5/K6 calls did not time out.

The wrapper uses CPU 0 by default. If that CPU is unavailable, it fails with a clear message. You may explicitly select an allowed CPU, for example `--cpu 2`, but this changes the timing environment. Version drift requires explicit `--allow-environment-drift`; such a run is exploratory and must not be presented as an identical-environment timing replication.

The frozen V2.1 search can retain unresolved regions, including numerically inconsistent infeasibility outcomes. A new `complete=false` result must be interpreted from its own evidence. The historical K2/K5 closure arguments do not automatically certify an arbitrary modified rerun.

## Reproduce the targeted audit and structural certificate

The K5 audit reruns the contradictory presolve-on C call and the closing presolve-off C and D checks, using the same HiGHS backend through SciPy. It is not validation by a second solver. Its per-call ceiling is 2400 seconds; these audit times are outside the primary timing panel.

```bash
python scripts/reproduce.py audit-k5 --output ../rotation_k05_audit
```

The K17 oracle constructs the three exact witnesses and verifies the structural premises, then checks the witnesses against the frozen V2.1 model. It needs the full dependencies for the model check but does not solve a MILP:

```bash
python scripts/reproduce.py oracle --output ../rotation_k17_oracle
```

Both commands work on a new copy. The unchanged archived K17 script regenerates a historical proof text that refers to a separately running timing experiment. That temporal sentence is superseded by `docs/K17_STRUCTURAL_CERTIFICATE.md` and the archived final status: the diagnostic stopped, and no completed M/P timing pair exists.

## Small-instance validation

```bash
python scripts/reproduce.py validate --protocol both --output ../rotation_small_tests
```

Each protocol is checked against exhaustive enumeration on 22 layer/regime cases from fixture seeds 1–4. The V2 harness additionally checks timeout handling and a native time-limit fixture (seed 9). These tests are separate from the factory results and their timings.

The frozen `bounded_region_v2/test_bounded.py` retains a stale V2.0 clock assertion expecting an 1800-second default search limit. V2.1 actually defaults to 600 seconds. The English release harness `tests/test_bounded_v2_1.py` corrects only that assertion, import location and output location. The frozen solver and test sources remain unchanged and their original hashes remain available. Use the release harness through the command above for the current V2.1 check.

## Expected scientific outputs

| Quantity | M | P |
|---|---:|---:|
| Records across 18 layers before cross-layer dominance filtering | 38 | 30 |
| Global nondominated triples/classes | 28 | 17 |
| Records in the 14-layer timing panel | 25 | 21 |
| Scalar calls in that panel | 100 | 84 |
| Total panel elapsed seconds | 1661.896469 | 1479.925305 |

The global class count falls by 39.2857%. The panel total is 10.9496% shorter for P, but excluding K16 makes P 10.1560% slower. One paired observation per layer supports a descriptive comparison, not a claim of universal or statistically established speedup.

M uses exact input-derived integer objective coordinates `C10=10*C` and `Dsum=180*D`. P uses the same input and model, with class resolutions 0.5 seconds and 0.1 score units. Its class indices are `(2*C10+5)//10` and `(2*Dsum+18)//36`. A displayed P disparity of zero covers `[0,0.05)` and does not establish exact workload equality. The global front minimizes C and D and maximizes certified k; it is not the two-dimensional union of layer points. No separately timed three-objective search was performed.

## File map

- `02_SUPPLEMENTARY/`: English tables, figures, aggregate metrics, common hashes and 68 selected witness records. This is the reference output set used by `verify`.
- `03_REPRODUCIBILITY/PANEL14_V1_1/`: public model input workbook, standardized inputs, frozen V1.1 code and 28 archived solver runs.
- `03_REPRODUCIBILITY/K02_V2_1/`, `K05_V2_1/`, `K06_V2_1/`: frozen V2.1 code, standardized inputs and raw follow-up runs; K5 also contains the targeted audit script and result.
- `03_REPRODUCIBILITY/K17_STRUCTURAL/`: deterministic oracle, exact witnesses, model checks and the clearly separate incomplete timing diagnostic.
- `scripts/`: safe entry points, read-only evidence checks, input reconstruction and English analysis.
- `tests/`: the documented V2.1 release test harness.
- `docs/`: protocol, completeness arguments, K17 proof and data dictionary.
- `SEEDS_AND_SETTINGS.json`, `SEED_REGISTER.csv`: seed and environment registers.
- `PROVENANCE_AND_ADAPTATIONS.json`: original hashes of every retained file and explicit analysis/verifier adaptations.
- `FILE_MANIFEST_SHA256.json`: hashes of all distributed files except itself.
- `RELEASE_VALIDATION.json`: checks performed while assembling this release and their scope.

## Corrections and archival limitations

K5's first P representative is corrected in the derived tables from `(692,67)` to `(691,67)` using the targeted audit. Original raw results and completion flags remain unchanged. K2 has 96 closed plus five unresolved M caps, hence 101 processed caps; an older summary's 91/96 counts were incorrect. Partial V2.1 event traces are preserved as received; the complete call arrays and states are retained. Do not infer missing solver calls from partial `events.jsonl` alone.

The V1.1 frozen manifest also lists two Turkish prose documents omitted from this English release. `scripts/verify_panel.py` skips only those two documentation hashes and still verifies all frozen code and data. This release has its own full manifest. Old `PENDING` fields in the retained initial data QA describe the historical extraction stage, not the final experimental status. See `PROVENANCE_AND_ADAPTATIONS.json` for the exact packaging scope.

Witness verification establishes feasibility and objective arithmetic. MILP-based optimality/completeness uses the retained solver outcomes and closure arguments under recorded numerical tolerances; no independently checkable rational branch-and-bound proof archive is supplied. K17 additionally has a solver-free integer structural proof. The implementation is a newly implemented DPA-style objective-box method, not author-supplied code for a published DPA, and this package makes no AUGMECON performance comparison.

No new software or data license is asserted by this packaging step. Attribution, third-party dependency licenses and journal-specific repository/license requirements should be handled by the authors when depositing the package.
