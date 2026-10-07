# DISTMOB final audit - reviewer-fix release

## What was changed

1. Stable-global no longer shares the evaluator's exact service model. The primary planner uses a fixed imperfect proxy: pathloss exponent 2.60, SNR bias -1.20 dB, and rate scale 7.60. The evaluator remains unchanged.
2. Added `stable_global_oracle` and `stable_global_no_switch` for explicit reviewer-facing comparisons.
3. Added a 7-seed planner model-mismatch experiment and a 10-seed zero-switch ablation.
4. Executive summary now leads with the 10-seed robustness study, explicitly states that served-demand improvement is not significant, and surfaces the P05 throughput penalty.
5. Runtime definitions are explicit; historical v10 runtime values are not mixed with final-release measurements.
6. Long report tables were reformatted for PDF readability; underlying result CSVs are unchanged and complete.

## Primary evidence

- 10-seed stable-global: served demand 0.9482 vs 0.9275 for load-aware; outage 0.1692 vs 0.2602; Jain 0.8674 vs 0.7757; latency proxy 1.3416 vs 1.8111; handover rate 0.00142 vs 0.2420.
- Served-demand improvement is positive but not significant after Holm correction (paired t p=0.0925; Wilcoxon p=0.0840).
- P05 throughput decreases from 3.4521 to 3.0335 Mbps (-12.1%); paired t Holm p=0.0523, Wilcoxon Holm p=0.0645.
- Zero-switch ablation increases mean handovers from 4.4 to 109.9 per 120-step run while improving QoS.
- Strong planner mismatch retains the outage/fairness advantage over the same-seed load-aware reference.

## Verification

- `pytest -q`: **7 passed**.
- Final report regenerated from the result tables.
- Final PDF rendered to PNG and inspected for layout integrity.


## Closing refinements

- Planner mismatch now reports internal planner-rate drift versus the oracle, so mild/moderate cases are not interpreted as “no score perturbation” merely because the balanced-slot assignment stayed unchanged. Mean drift is approximately 20.2% for mild mismatch, 28.7% for moderate mismatch, and 43.7% for the strong mismatch used by the primary controller.
- Runtime note is stated explicitly in the release documentation: historical v10 timings used a different implementation/workload and are not directly comparable.
- An optional external-trace validation protocol is documented using the X-Fi public Wi-Fi association dataset; raw third-party data are not bundled into the repository and the external route is deliberately kept separate from the primary counterfactual benchmark.
- Added `SOP_FRAMING.md` with the hypothesis-testing/falsification framing for applications and research statements.

## Final presentation regression audit - 2026-10-04

This pass changed **report generation only**; the result CSV/JSON files and controller implementation were left untouched.

Checks completed:
- `pytest -q`: **8 passed**.
- PDF regenerated from `scripts/build_report.py`.
- PDF rendered with the project PDF render tool at 140 dpi.
- Core frozen-trace table: all six policy rows now appear together under Section 5 on a fresh page.
- Stress grid: all six disturbance/mobility combinations are visible in the report as a compact comparison table, including P05 throughput; the full matrix remains in `results/joint_stress_grid.csv`.
- PDF extraction contains no `igure`, `load_aware_reference0.`, `ewpage`, `1ntentionally`, or repeated-`1` artifact pattern.
- Page-number-only `1`, `6`, `15`, etc. remain normal footer page numbers and are not content artifacts.

Scientific results were not recomputed or edited in this presentation-only pass.
