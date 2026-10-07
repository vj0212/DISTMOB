from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from distmob.config import SimConfig
from distmob.experiment import (
    bootstrap_ci,
    paired_significance_tests,
    run_global_ablation,
    run_model_mismatch_sensitivity,
    summarize_metrics,
)
from distmob.simulator import DistMobSim, generate_trace

RESULTS = ROOT / "results"
DATA = ROOT / "data"

SEEDS = [3, 7, 11, 13, 17, 19, 23, 29, 31, 37]
ROBUSTNESS_POLICIES = ["ttt_handover", "load_aware", "darc", "robust_darc", "shield_darc", "stable_global", "regime_orchestrator"]
SIGMAS = [0.8, 1.4, 2.1, 2.6, 3.2]
STRESS_SIGMAS = [0.8, 3.2]
STRESS_SPEEDS = [1.2, 2.3, 2.8]
STRESS_SEEDS = [3, 13]


def run_on_trace(cfg: SimConfig, trace: dict[str, np.ndarray], policy: str, seed: int, steps: int):
    sim = DistMobSim(cfg, trace_data=trace, policy_seed=seed)
    return sim.run(policy=policy, steps=steps)


def replace_policy_rows(path: Path, new_rows: pd.DataFrame, policy_col: str = "policy") -> pd.DataFrame:
    old = pd.read_csv(path)
    policies = new_rows[policy_col].unique().tolist()
    merged = pd.concat([old[~old[policy_col].isin(policies)], new_rows], ignore_index=True)
    return merged.sort_values([c for c in ["disturbance_sigma", "sigma", "max_speed", "policy", "seed"] if c in merged.columns]).reset_index(drop=True)


def recompute_core(cfg: SimConfig) -> None:
    trace = {k: v for k, v in np.load(DATA / "core_trace.npz").items()}
    m = run_on_trace(cfg, trace, "stable_global", 10_000, cfg.steps)
    row = pd.DataFrame([summarize_metrics(m, "stable_global", cfg.seed, cfg.disturbance_sigma)])
    out = replace_policy_rows(RESULTS / "core_results.csv", row)
    out.to_csv(RESULTS / "core_results.csv", index=False)
    cols = ["policy", "served_demand_fraction", "mean_outage", "mean_jain", "mean_handover_rate"]
    out[cols].to_csv(RESULTS / "core_highlights.csv", index=False)


def recompute_seed(cfg: SimConfig) -> pd.DataFrame:
    rows = []
    for seed in SEEDS:
        c = SimConfig(**{**cfg.__dict__, "seed": seed, "steps": 120})
        trace = generate_trace(c, seed=seed, steps=120)
        m = run_on_trace(c, trace, "stable_global", 20_000 + seed, 120)
        rows.append(summarize_metrics(m, "stable_global", seed, c.disturbance_sigma))
    new = pd.DataFrame(rows)
    out = replace_policy_rows(RESULTS / "seed_robustness.csv", new)
    out.to_csv(RESULTS / "seed_robustness.csv", index=False)
    summary_rows = []
    for policy, g in out.groupby("policy"):
        row = {"policy": policy}
        for metric in ["mean_outage", "served_demand_fraction", "mean_satisfaction", "p05_satisfaction", "p05_throughput", "mean_jain", "mean_latency_proxy", "mean_handover_rate"]:
            row[f"{metric}_mean"] = float(g[metric].mean())
            row[f"{metric}_std"] = float(g[metric].std(ddof=1))
            lo, hi = bootstrap_ci(g[metric].to_numpy(), seed=500 + len(summary_rows))
            row[f"{metric}_ci_low"] = lo
            row[f"{metric}_ci_high"] = hi
        summary_rows.append(row)
    pd.DataFrame(summary_rows).sort_values("policy").to_csv(RESULTS / "seed_robustness_summary.csv", index=False)
    sig = paired_significance_tests(out, reference_policy="load_aware")
    sig.to_csv(RESULTS / "significance_tests.csv", index=False)
    return out


def recompute_disturbance(cfg: SimConfig) -> None:
    rows = []
    for sigma in SIGMAS:
        for seed in [3, 7, 13]:
            c = SimConfig(**{**cfg.__dict__, "disturbance_sigma": sigma, "seed": seed, "steps": 100})
            trace = generate_trace(c, seed=seed, steps=100)
            m = run_on_trace(c, trace, "stable_global", 30_000 + seed, 100)
            rows.append(summarize_metrics(m, "stable_global", seed, sigma))
    new = pd.DataFrame(rows)
    out = replace_policy_rows(RESULTS / "disturbance_sweep.csv", new)
    out.to_csv(RESULTS / "disturbance_sweep.csv", index=False)


def recompute_stress(cfg: SimConfig) -> None:
    rows = []
    for sigma in STRESS_SIGMAS:
        for speed in STRESS_SPEEDS:
            for seed in STRESS_SEEDS:
                c = SimConfig(**{**cfg.__dict__, "disturbance_sigma": sigma, "max_speed": speed, "seed": seed, "steps": 90})
                trace = generate_trace(c, seed=seed, steps=90)
                m = run_on_trace(c, trace, "stable_global", 40_000 + seed, 90)
                rows.append({"sigma": sigma, "max_speed": speed, **summarize_metrics(m, "stable_global", seed, sigma)})
    new = pd.DataFrame(rows)
    out = replace_policy_rows(RESULTS / "joint_stress_grid.csv", new)
    out.to_csv(RESULTS / "joint_stress_grid.csv", index=False)


def recompute_runtime(cfg: SimConfig) -> None:
    trace = {k: v for k, v in np.load(DATA / "core_trace.npz").items()}
    import time
    timings = []
    for rep in range(3):
        sim = DistMobSim(cfg, trace_data=trace, policy_seed=60_000 + rep)
        t0 = time.perf_counter()
        sim.run("stable_global", 180)
        timings.append(time.perf_counter() - t0)
    avg = float(np.mean(timings))
    row = pd.DataFrame([{
        "policy": "stable_global",
        "mean_runtime_sec": avg,
        "std_runtime_sec": float(np.std(timings, ddof=1)),
        "runtime_ms_per_step": 1000.0 * avg / 180,
        "runtime_ms_per_user_step": 1000.0 * avg / (180 * cfg.n_users),
        "steps": 180,
        "repeats": 3,
    }])
    out = replace_policy_rows(RESULTS / "runtime_benchmark.csv", row)
    out.to_csv(RESULTS / "runtime_benchmark.csv", index=False)


def recompute_scaling(cfg: SimConfig) -> None:
    import time
    rows = []
    for n_users, n_aps, seed, scenario_steps in [(24, 6, 3, 60), (50, 10, 7, 60), (100, 20, 13, 30)]:
        c = SimConfig(**{**cfg.__dict__, "n_users": n_users, "n_aps": n_aps, "seed": seed, "steps": scenario_steps})
        trace = generate_trace(c, seed=seed, steps=scenario_steps)
        timings, metric_rows = [], []
        for rep in range(2):
            sim = DistMobSim(c, trace_data=trace, policy_seed=70_000 + rep)
            t0 = time.perf_counter()
            m = sim.run("stable_global", scenario_steps)
            timings.append(time.perf_counter() - t0)
            metric_rows.append(summarize_metrics(m, "stable_global", seed + rep, c.disturbance_sigma))
        md = pd.DataFrame(metric_rows)
        avg = float(np.mean(timings))
        rows.append({
            "n_users": n_users,
            "n_aps": n_aps,
            "policy": "stable_global",
            "mean_runtime_sec": avg,
            "std_runtime_sec": float(np.std(timings, ddof=1)),
            "runtime_ms_per_user_step": 1000.0 * avg / (scenario_steps * n_users),
            "served_demand_fraction": float(md.served_demand_fraction.mean()),
            "mean_outage": float(md.mean_outage.mean()),
            "p05_throughput": float(md.p05_throughput.mean()),
            "mean_handover_rate": float(md.mean_handover_rate.mean()),
            "steps": scenario_steps,
            "repeats": 2,
        })
    new = pd.DataFrame(rows)
    old = pd.read_csv(RESULTS / "scaling_benchmark.csv")
    old = old[old.policy != "stable_global"]
    out = pd.concat([old, new], ignore_index=True).sort_values(["n_users", "n_aps", "policy"]).reset_index(drop=True)
    out.to_csv(RESULTS / "scaling_benchmark.csv", index=False)


def main() -> None:
    cfg = SimConfig(**json.loads((RESULTS / "config.json").read_text()))
    recompute_core(cfg)
    recompute_seed(cfg)
    recompute_disturbance(cfg)
    recompute_stress(cfg)
    global_df = run_global_ablation(cfg, seeds=SEEDS, steps=120, out_dir=RESULTS)
    mismatch_df = run_model_mismatch_sensitivity(cfg, seeds=[3, 7, 13, 19, 29, 31, 37], steps=120, out_dir=RESULTS)
    recompute_runtime(cfg)
    recompute_scaling(cfg)
    protocol = {
        "policy_benchmark": {"environment": "frozen core_trace.npz", "steps": 180, "repeats": 3, "timed_operation": "DistMobSim.run only", "excluded": ["trace generation", "CSV writing", "figure generation", "PDF generation"]},
        "scaling_benchmark": {"scenarios": [[24, 6, 60], [50, 10, 60], [100, 20, 30]], "repeats": 2, "timed_operation": "DistMobSim.run only on a frozen scenario trace"},
        "historical_note": "The prior v10 runtime measurements came from an earlier implementation/workload and are not apples-to-apples with this final code path.",
    }
    (RESULTS / "runtime_protocol.json").write_text(json.dumps(protocol, indent=2), encoding="utf-8")
    print("review fixes complete")
    print("global ablation summary")
    print(global_df.groupby("policy")[['served_demand_fraction','mean_outage','p05_throughput','mean_jain','mean_latency_proxy','mean_handover_rate','total_handovers']].mean().to_string())
    print("model mismatch summary")
    print(mismatch_df.groupby("model")[['served_demand_fraction','mean_outage','p05_throughput','mean_jain','mean_latency_proxy','mean_handover_rate']].mean().to_string())


if __name__ == "__main__":
    main()
