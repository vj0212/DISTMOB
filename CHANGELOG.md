# DISTMOB change log

## Reviewer-fix release

### Methodology

- Stable-global now uses an intentionally imperfect planner-side proxy service model; the evaluator retains the authoritative radio/service model.
- Primary stable-global configuration: planner pathloss exponent 2.60, SNR bias -1.20 dB, rate scale 7.60.
- Added `stable_global_oracle` as an evaluator-matched comparison and `stable_global_no_switch` as a zero-switch-penalty ablation.
- Preserved frozen exogenous traces and online observer reconstruction.
- Preserved the corrected finite-horizon DARC prediction and global assignment objective.

### Reviewer-facing experiments

- Mismatch sensitivity now reports planner-rate score drift versus the oracle, so unchanged discrete assignments do not hide changed internal scores.
- Added an optional external-trace validation protocol for the X-Fi public Wi-Fi dataset without copying third-party raw data into the repository.
- Added SOP framing notes focused on hypothesis testing and falsification rather than claiming universal controller dominance.

- Added planner/evaluator model-mismatch sensitivity over 7 seeds.
- Added zero-switch-penalty ablation over the same 10-seed robustness design.
- Primary executive-summary evidence is now seed-level, not a single core trace.
- P05 throughput trade-off is explicitly reported as a cost.
- Runtime protocol is explicitly defined and historical v10 numbers are treated as non-comparable.

### Verification

- Automated test suite expanded from 5 to **7 tests**.
- Final report tables shortened where necessary for PDF readability without removing underlying CSV evidence.
- Final PDF regenerated and rendered for visual inspection.

## Closing refinements

- Added planner internal score-drift diagnostics to the mismatch study.
- Added explicit one-line runtime comparability note across release versions.
- Documented an optional X-Fi external-trace validation route without bundling third-party raw data.
- Added SOP application framing centered on hypothesis testing and falsification.

## Final presentation pass - 2026-10-04
- Fixed the core frozen-trace table pagination so all six policy rows stay under Section 5.
- Replaced the long stress-grid report table with a compact six-combination comparison while retaining the complete policy-by-seed CSV.
- Added explicit stress-grid coverage text confirming all six disturbance/mobility combinations are represented.
- Added PDF regression checks for historical `igure`, `load_aware_reference0.`, `1ntentionally`, and repeated-`1` extraction artifacts.
- Added a regression test covering the report-build safeguards.
- No experiment data, controller code, statistical results, or scientific conclusions were changed in this pass.
