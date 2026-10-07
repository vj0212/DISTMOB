# DISTMOB - Reviewer-Fix Results Summary

## Primary 10-seed robustness study

Stable-global now uses an intentionally imperfect planner-side service model while the evaluator retains the authoritative model. Across 10 paired seeds, all policies are evaluated on the same frozen exogenous trace per seed.

| Metric | Load-aware | Stable-global | Delta (SG - LA) |
|---|---:|---:|---:|
| Served-demand fraction | 0.9275 | **0.9482** | +0.0206 |
| Mean satisfaction | 0.9439 | **0.9573** | +0.0135 |
| P05 satisfaction | 0.7525 | **0.7687** | +0.0162 |
| Outage | 0.2602 | **0.1692** | -0.0910 |
| P05 throughput [Mbps] | **3.4521** | 3.0335 | -0.4186 |
| Jain fairness | 0.7757 | **0.8674** | +0.0917 |
| Latency proxy | 1.8111 | **1.3416** | -0.4696 |
| Handover rate | 0.2420 | **0.00142** | -0.2406 |

Derived effects: outage is 35.0% lower, Jain fairness is 11.8% higher, latency proxy is 25.9% lower, and handover rate is 99.4% lower. The served-demand improvement is positive but not statistically significant after Holm correction (paired t p=0.0925; Wilcoxon p=0.0840). The P05 throughput trade-off is real: -0.4186 Mbps (-12.1%); paired t Holm p=0.0523 and Wilcoxon Holm p=0.0645.

## Planner/evaluator model mismatch

The evaluator model is unchanged. Stable-global uses a proxy with pathloss exponent 2.60 instead of 2.35, SNR bias -1.20 dB, and rate scale 7.60 instead of 8.00.

Across 7 seeds:

| Planner model | Served demand | Outage | P05 throughput | Jain | Latency proxy |
|---|---:|---:|---:|---:|---:|
| Load-aware reference | 0.9379 | 0.2413 | 3.5984 | 0.7890 | 1.7178 |
| Oracle planner | 0.9402 | 0.1828 | 3.0122 | 0.8744 | 1.3945 |
| Mild mismatch | 0.9402 | 0.1828 | 3.0122 | 0.8744 | 1.3945 |
| Moderate mismatch | 0.9402 | 0.1828 | 3.0122 | 0.8744 | 1.3945 |
| Strong mismatch / primary proxy | 0.9392 | 0.1859 | 3.0179 | 0.8723 | 1.3999 |

The result remains favorable under the primary strong mismatch. Mild/moderate proxy perturbations happen to preserve the selected balanced-slot assignments in this setup, but their internal planner-rate scores still move by 20.2% and 28.7% of the oracle rate scale, respectively; the strong mismatch moves them by 43.7%. The strong mismatch changes aggregate behavior and still retains the outage/fairness advantage.

## Switch-penalty ablation

| Variant | Served demand | Outage | P05 Mbps | Jain | Latency proxy | HO rate | Mean HOs |
|---|---:|---:|---:|---:|---:|---:|---:|
| Stable-global | 0.9488 | 0.1741 | 3.0241 | 0.8727 | 1.3386 | 0.00153 | 4.4 |
| Zero switch penalty | **0.9864** | **0.0679** | **4.3410** | **0.9645** | **1.0864** | 0.03816 | 109.9 |
| Oracle stable-global | 0.9490 | 0.1738 | 3.0289 | 0.8731 | 1.3366 | 0.00146 | 4.2 |

This removes the degeneracy concern: low churn is not accidental. Removing the switch penalty buys substantial QoS improvements but increases mean handovers from 4.4 to 109.9 over 120 steps.

## Runtime protocol

Policy benchmark: frozen core trace, 180 steps, 3 repeats, timing only `DistMobSim.run`, excluding trace generation, file I/O, plotting and PDF generation.

Scaling benchmark: frozen scenario traces at 24/6 (60 steps), 50/10 (60 steps), and 100/20 (30 steps), 2 repeats.

Final stable-global runtime: 0.7111 s per 180-step run, or 3.9504 ms/step and 0.1646 ms/user-step under the final protocol.

Historical v10 runtime numbers are not directly comparable because they came from an earlier implementation/workload. The final report deliberately uses only the final-release protocol for runtime claims.

## Verification

`pytest -q` -> **7 passed**.

The final PDF was rendered to PNG and visually checked for clipped text, overlapping table content, broken glyphs, and figure layout.


## Optional external validation

The repository documents an external validation route using the X-Fi public Wi-Fi association dataset. It is intentionally not injected into the primary counterfactual policy benchmark because its real-world observables do not expose every synchronized latent state required by DISTMOB. The intended use is to validate mobility speed, association dwell time, signal variability and goodput relationships separately.
