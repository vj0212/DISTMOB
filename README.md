> Last polished: 2026-10-04. Final pass adds a stable core-table page break, a compact six-combination stress table, and PDF regression checks; scientific result files are unchanged in this presentation-only pass.
# DISTMOB

**Disturbance-Aware Mobility Control for Mobile Networks**

DISTMOB is a research-engineering simulation project for AP association under user mobility, congestion, and time-varying disturbances. It compares classical handover rules, predictive disturbance-aware control, robustness/safety extensions, a constrained global assignment planner, a supervisory regime controller, and a lightweight tabular RL baseline.

## Reviewer-fix release

This release keeps the previously solid architecture and adds targeted methodological checks:

- **Planner/evaluator model mismatch:** stable-global uses an intentionally imperfect fixed proxy (pathloss exponent 2.60, SNR bias -1.20 dB, rate scale 7.60), while evaluation uses the authoritative model.
- **Oracle comparison:** `stable_global_oracle` uses the evaluator-matched planner model for sensitivity analysis.
- **Zero-switch ablation:** `stable_global_no_switch` removes the explicit switch penalty to show how much low churn is caused by stability regularization.
- **Seed-level executive summary:** the main robustness claim uses 10 paired seeds. Served-demand improvement is reported as positive but not significant.
- **Tail QoS:** P05 throughput is explicitly reported as a cost of the stability-oriented policy.
- **Runtime reconciliation:** the final protocol is frozen and historical v10 timings are treated as non-comparable.

## Runtime note

The runtime numbers in this release are not comparable to v10 because the timed operation and implementation/workload changed; only final-release protocol measurements are used for runtime claims.

## Primary evidence

Across 10 paired seeds, stable-global averages 0.9482 served-demand fraction versus 0.9275 for load-aware, outage 0.1692 versus 0.2602, Jain fairness 0.8674 versus 0.7757, latency proxy 1.3416 versus 1.8111, and handover rate 0.00142 versus 0.2420. The served-demand improvement is not significant after Holm correction. P05 throughput decreases from 3.4521 to 3.0335 Mbps (-12.1%), which is treated as a real trade-off.

The zero-switch ablation raises mean handovers from 4.4 to 109.9 over the 120-step robustness runs while improving QoS metrics. This establishes that the low-churn result is an explicit consequence of the switch-regularized objective rather than a degeneracy in the environment.

## External-trace extension (optional)

The final core benchmark intentionally remains synthetic and frozen for clean counterfactual policy comparison. As an external validation path, the repository documents the X-Fi public Wi-Fi association dataset, which contains GPS traces, Wi-Fi association attempts, signal measurements and TCP performance fields across Paris, Bologna, Macao and Los Angeles. The external dataset is **not copied into this repository**; users should obtain it from the authors' public repository and follow its citation/usage terms. This extension is for validating mobility/association assumptions, not for substituting incomplete external observables into the controlled policy benchmark.

Source: Yang et al., *Revisiting WiFi offloading in the wild for V2I applications* (Computer Networks, 2022): https://github.com/yangfurong/X-Fi_dataset

## Run

```bash
python -m pip install -r requirements.txt
python scripts/run_all_experiments.py
python scripts/build_report.py
pytest -q
```

For a faster reviewer-focused refresh after the main release results already exist:

```bash
python scripts/recompute_review_fixes.py
python scripts/build_report.py
pytest -q
```

## Repository structure

```text
DISTMOB/
├── distmob/
│   ├── __init__.py
│   ├── config.py
│   ├── simulator.py
│   └── experiment.py
├── scripts/
│   ├── run_all_experiments.py
│   ├── recompute_review_fixes.py
│   └── build_report.py
├── tests/
├── external_trace/
│   └── test_distmob.py
├── data/
├── results/
├── figures/
├── report/
├── requirements.txt
├── RESULTS_SUMMARY.md
├── CHANGELOG.md
├── FINAL_AUDIT.md
├── SOP_FRAMING.md
└── README.md
```

## Application framing

For an SOP or research statement, the strongest framing is methodological rather than “my controller always won.” I built a reproducible control simulator, discovered that a strong simple baseline could outperform parts of my first design, and then used successive controlled experiments to isolate why. That process taught me to formulate hypotheses, compare against meaningful baselines, expose trade-offs, and design experiments capable of falsifying my own assumptions.

## Interpretation

This is a synthetic comparative control study, not a packet-level 4G/5G simulator and not field-validation evidence. The strongest defensible claim is that stable-global improves outage, fairness, latency proxy and mobility stability under the stated model and retains the outage/fairness advantage under the tested planner/evaluator model mismatch. The project does **not** claim universal improvement in every metric: P05 throughput is a documented trade-off, and served-demand improvement is not significant at the seed level.
