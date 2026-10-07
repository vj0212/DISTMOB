from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from distmob.config import SimConfig
from distmob.experiment import (
    export_trace_bundle,
    paired_significance_tests,
    run_disturbance_sweep,
    run_global_ablation,
    run_horizon_sensitivity,
    run_joint_stress_grid,
    run_model_mismatch_sensitivity,
    run_policy_suite,
    run_runtime_benchmark,
    run_scaling_benchmark,
    run_seed_robustness,
)
from distmob.simulator import POLICY_NAMES, generate_trace


def main() -> None:
    results = ROOT / "results"
    figures = ROOT / "figures"
    data = ROOT / "data"
    report = ROOT / "report"
    for d in (results, figures, data, report):
        d.mkdir(parents=True, exist_ok=True)

    cfg = SimConfig(seed=11, steps=180, disturbance_sigma=2.1, max_speed=2.3)
    core_trace = generate_trace(cfg, seed=cfg.seed, steps=cfg.steps)

    # Core evaluation on one frozen environment trace.
    core_df, core_details = run_policy_suite(
        cfg,
        core_trace,
        policies=POLICY_NAMES,
        out_dir=results,
    )

    # Statistical robustness: all policies face exactly the same trace for each seed.
    robustness_policies = ["ttt_handover", "load_aware", "darc", "robust_darc", "shield_darc", "stable_global", "regime_orchestrator"]
    seeds = [3, 7, 11, 13, 17, 19, 23, 29, 31, 37]
    seed_df = run_seed_robustness(cfg, seeds=seeds, policies=robustness_policies, steps=120, out_dir=results)
    sig_df = paired_significance_tests(seed_df, reference_policy="load_aware")
    sig_df.to_csv(results / "significance_tests.csv", index=False)

    sweep_df = run_disturbance_sweep(
        cfg,
        sigma_values=[0.8, 1.4, 2.1, 2.6, 3.2],
        policies=["load_aware", "darc", "robust_darc", "shield_darc", "stable_global", "regime_orchestrator"],
        seeds=[3, 7, 13],
        steps=100,
        out_dir=results,
    )

    stress_df = run_joint_stress_grid(
        cfg,
        sigma_values=[0.8, 3.2],
        speed_values=[1.2, 2.3, 2.8],
        seeds=[3, 13],
        policies=["load_aware", "darc", "robust_darc", "shield_darc", "stable_global", "regime_orchestrator"],
        steps=90,
        out_dir=results,
    )

    horizon_df = run_horizon_sensitivity(cfg, horizons=[1, 3, 6, 9, 12], seeds=[3, 13], steps=120, out_dir=results)

    # Targeted reviewer-facing ablations: model mismatch and switch-cost removal.
    global_ablation_df = run_global_ablation(cfg, seeds=seeds, steps=120, out_dir=results)
    mismatch_df = run_model_mismatch_sensitivity(cfg, seeds=[3, 7, 13, 19, 29, 31, 37], steps=120, out_dir=results)

    runtime_df = run_runtime_benchmark(cfg, policies=["rssi", "hysteresis", "ttt_handover", "load_aware", "darc", "robust_darc", "shield_darc", "stable_global", "regime_orchestrator", "q_learning"], trace=core_trace, steps=180, repeats=3, out_dir=results)

    scaling_df = run_scaling_benchmark(
        cfg,
        scenarios=[(24, 6, 3, 60), (50, 10, 7, 60), (100, 20, 13, 30)],
        policies=["load_aware", "stable_global"],
        steps=60,
        repeats=2,
        out_dir=results,
    )

    trace_paths = export_trace_bundle(core_trace, cfg, ROOT, label="core_trace")

    (results / "config.json").write_text(json.dumps(cfg.__dict__, indent=2), encoding="utf-8")
    manifest = {
        "core_policies": POLICY_NAMES,
        "robustness_seeds": seeds,
        "files": sorted(p.name for p in results.iterdir() if p.is_file()),
        "trace": {k: str(v.relative_to(ROOT)) for k, v in trace_paths.items()},
        "reviewer_ablations": ["global_ablation.csv", "global_ablation_summary.csv", "model_mismatch_sensitivity.csv"],
    }
    (results / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    runtime_protocol = {
        "policy_benchmark": {
            "environment": "frozen core_trace.npz",
            "steps": 180,
            "repeats": 3,
            "timed_operation": "DistMobSim.run only",
            "excluded": ["trace generation", "CSV writing", "figure generation", "PDF generation"],
            "normalization": ["ms/step", "ms/user-step"],
        },
        "scaling_benchmark": {
            "scenarios": [[24, 6, 60], [50, 10, 60], [100, 20, 30]],
            "repeats": 2,
            "timed_operation": "DistMobSim.run on one frozen trace per scenario",
        },
        "historical_note": "The prior v10 report used an earlier implementation and workload. Its runtime numbers are not directly comparable; only this final protocol is used for runtime claims in the final report.",
    }
    (results / "runtime_protocol.json").write_text(json.dumps(runtime_protocol, indent=2), encoding="utf-8")

    print("\n=== CORE ===")
    cols = ["policy", "served_demand_fraction", "mean_outage", "p05_throughput", "mean_jain", "mean_latency_proxy", "mean_handover_rate", "total_handovers"]
    print(core_df[cols].to_string(index=False))
    print("\n=== ROBUSTNESS (mean across seeds) ===")
    print(seed_df.groupby("policy")[cols[1:-1]].mean().sort_values("served_demand_fraction", ascending=False).to_string())
    print("\n=== SIGNIFICANCE vs LOAD-AWARE ===")
    print(sig_df[sig_df.metric.isin(["served_demand_fraction", "mean_outage", "p05_throughput", "mean_jain", "mean_handover_rate"])].to_string(index=False))
    print("\n=== SCALING ===")
    print(scaling_df.to_string(index=False))


if __name__ == "__main__":
    main()
