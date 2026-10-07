from __future__ import annotations

from dataclasses import asdict
import json
import time
from pathlib import Path
from typing import Dict, Iterable

import numpy as np
import pandas as pd
from scipy import stats

from .config import SimConfig
from .simulator import DistMobSim, POLICY_NAMES, generate_trace


def bootstrap_ci(samples: np.ndarray, n_boot: int = 5000, alpha: float = 0.05, seed: int = 123) -> tuple[float, float]:
    x = np.asarray(samples, dtype=float)
    x = x[np.isfinite(x)]
    if x.size <= 1:
        return (float(x[0]), float(x[0])) if x.size else (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, x.size, size=(n_boot, x.size))
    means = x[idx].mean(axis=1)
    return float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2))


def holm_bonferroni(pvals: Iterable[float]) -> np.ndarray:
    vals = np.asarray(list(pvals), dtype=float)
    vals = np.where(np.isfinite(vals), vals, 1.0)
    order = np.argsort(vals)
    adjusted = np.empty_like(vals)
    m = len(vals)
    running = 0.0
    for k, idx in enumerate(order):
        running = max(running, min(1.0, (m - k) * vals[idx]))
        adjusted[idx] = running
    return adjusted


def summarize_metrics(metrics: Dict[str, object], policy: str, seed: int, disturbance_sigma: float) -> Dict[str, float | str | int]:
    return {
        "policy": policy,
        "seed": int(seed),
        "disturbance_sigma": float(disturbance_sigma),
        "mean_throughput": float(metrics["mean_throughput"]),
        "mean_outage": float(metrics["mean_outage_rate"]),
        "served_demand_fraction": float(metrics["mean_served_demand_fraction"]),
        "mean_satisfaction": float(metrics["mean_mean_satisfaction"]),
        "p05_satisfaction": float(metrics["mean_p05_satisfaction"]),
        "mean_shortfall_fraction": float(metrics["mean_mean_shortfall_fraction"]),
        "p05_throughput": float(metrics["mean_p05_throughput"]),
        "median_throughput": float(metrics["mean_median_throughput"]),
        "mean_jain": float(metrics["mean_jain"]),
        "mean_latency_proxy": float(metrics["mean_latency_proxy"]),
        "mean_load_cv": float(metrics["mean_mean_load_cv"]),
        "mean_handover_rate": float(metrics["mean_handover_rate"]),
        "total_handovers": int(metrics["total_handovers"]),
        "pingpong_events": int(metrics["pingpong_events"]),
        "mean_shield_mode": float(metrics["mean_shield_mode"]),
        "mean_shock_index": float(metrics["mean_shock_index"]),
        "mean_reward": float(metrics["mean_reward_mean"]),
        "mean_regime_switches": float(metrics["mean_regime_switches"]),
        "mean_mode_darc": float(metrics["mean_mode_darc"]),
        "mean_mode_robust": float(metrics["mean_mode_robust"]),
        "mean_mode_shield": float(metrics["mean_mode_shield"]),
    }


def run_policy_on_trace(cfg: SimConfig, trace: Dict[str, np.ndarray], policy: str, policy_seed: int = 991, steps: int | None = None):
    sim = DistMobSim(cfg, trace_data=trace, policy_seed=policy_seed)
    return sim.run(policy=policy, steps=steps or trace["user_pos"].shape[0])


def run_policy_suite(cfg: SimConfig, trace: Dict[str, np.ndarray], policies: Iterable[str] = POLICY_NAMES, out_dir: Path | None = None):
    rows, detailed = [], {}
    for policy in policies:
        metrics = run_policy_on_trace(cfg, trace, policy, policy_seed=10_000)
        detailed[policy] = metrics
        rows.append(summarize_metrics(metrics, policy, cfg.seed, cfg.disturbance_sigma))
    df = pd.DataFrame(rows).sort_values("policy").reset_index(drop=True)
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_dir / "core_results.csv", index=False)
    return df, detailed


def run_seed_robustness(base_cfg: SimConfig, seeds: Iterable[int], policies: Iterable[str], steps: int, out_dir: Path | None = None):
    rows = []
    for seed in seeds:
        cfg = SimConfig(**{**base_cfg.__dict__, "seed": int(seed), "steps": int(steps)})
        trace = generate_trace(cfg, seed=seed, steps=steps)
        for policy in policies:
            metrics = run_policy_on_trace(cfg, trace, policy, policy_seed=20_000 + int(seed))
            rows.append(summarize_metrics(metrics, policy, seed, cfg.disturbance_sigma))
    df = pd.DataFrame(rows).sort_values(["policy", "seed"]).reset_index(drop=True)
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_dir / "seed_robustness.csv", index=False)
        summary_rows = []
        for policy, g in df.groupby("policy"):
            row = {"policy": policy}
            for metric in ["mean_outage", "served_demand_fraction", "mean_satisfaction", "p05_satisfaction", "p05_throughput", "mean_jain", "mean_latency_proxy", "mean_handover_rate"]:
                row[f"{metric}_mean"] = float(g[metric].mean())
                row[f"{metric}_std"] = float(g[metric].std(ddof=1))
                lo, hi = bootstrap_ci(g[metric].to_numpy(), seed=500 + len(summary_rows))
                row[f"{metric}_ci_low"] = lo
                row[f"{metric}_ci_high"] = hi
            summary_rows.append(row)
        pd.DataFrame(summary_rows).to_csv(out_dir / "seed_robustness_summary.csv", index=False)
    return df


def paired_significance_tests(seed_df: pd.DataFrame, reference_policy: str = "load_aware") -> pd.DataFrame:
    metrics = {
        "served_demand_fraction": "higher",
        "mean_satisfaction": "higher",
        "p05_satisfaction": "higher",
        "mean_outage": "lower",
        "p05_throughput": "higher",
        "mean_jain": "higher",
        "mean_latency_proxy": "lower",
        "mean_handover_rate": "lower",
        "pingpong_events": "lower",
    }
    rows = []
    for policy in sorted(p for p in seed_df["policy"].unique() if p != reference_policy):
        ref = seed_df[seed_df.policy == reference_policy].sort_values("seed")
        other = seed_df[seed_df.policy == policy].sort_values("seed")
        merged = ref.merge(other, on="seed", suffixes=("_ref", "_other"))
        for metric, direction in metrics.items():
            if metric not in seed_df.columns:
                continue
            x = merged[f"{metric}_ref"].to_numpy(float)
            y = merged[f"{metric}_other"].to_numpy(float)
            if len(x) < 2:
                continue
            diff = y - x
            improvement = diff if direction == "higher" else -diff
            t_stat, t_p = stats.ttest_rel(y, x, nan_policy="omit")
            try:
                w_stat, w_p = stats.wilcoxon(y, x, alternative="two-sided")
            except ValueError:
                w_stat, w_p = np.nan, 1.0
            sd = float(np.std(improvement, ddof=1))
            lo, hi = bootstrap_ci(improvement, seed=900 + len(rows))
            rows.append({
                "reference": reference_policy,
                "policy": policy,
                "metric": metric,
                "direction": direction,
                "n_pairs": int(len(x)),
                "ref_mean": float(np.mean(x)),
                "policy_mean": float(np.mean(y)),
                "improvement_mean": float(np.mean(improvement)),
                "improvement_ci_low": lo,
                "improvement_ci_high": hi,
                "cohen_dz": float(np.mean(improvement) / (sd + 1e-9)),
                "t_stat": float(t_stat),
                "t_pvalue": float(t_p),
                "wilcoxon_pvalue": float(w_p),
                "t_pvalue_holm": np.nan,
                "wilcoxon_pvalue_holm": np.nan,
            })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    for metric in df.metric.unique():
        mask = df.metric == metric
        df.loc[mask, "t_pvalue_holm"] = holm_bonferroni(df.loc[mask, "t_pvalue"])
        df.loc[mask, "wilcoxon_pvalue_holm"] = holm_bonferroni(df.loc[mask, "wilcoxon_pvalue"])
    return df


def run_global_ablation(base_cfg: SimConfig, seeds: Iterable[int], steps: int, out_dir: Path | None = None):
    """Compare proxy-model stable-global, oracle-model stable-global, and zero-switch ablation."""
    rows = []
    policies = ["stable_global", "stable_global_oracle", "stable_global_no_switch"]
    for seed in seeds:
        cfg = SimConfig(**{**base_cfg.__dict__, "seed": int(seed), "steps": int(steps)})
        trace = generate_trace(cfg, seed=seed, steps=steps)
        for policy in policies:
            metrics = run_policy_on_trace(cfg, trace, policy, policy_seed=25_000 + int(seed))
            rows.append(summarize_metrics(metrics, policy, seed, cfg.disturbance_sigma))
    df = pd.DataFrame(rows).sort_values(["policy", "seed"]).reset_index(drop=True)
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_dir / "global_ablation.csv", index=False)
        summary_rows = []
        for policy, g in df.groupby("policy"):
            summary_rows.append({
                "policy": policy,
                "served_demand_mean": float(g.served_demand_fraction.mean()),
                "mean_satisfaction": float(g.mean_satisfaction.mean()),
                "p05_satisfaction": float(g.p05_satisfaction.mean()),
                "mean_outage": float(g.mean_outage.mean()),
                "p05_throughput": float(g.p05_throughput.mean()),
                "mean_jain": float(g.mean_jain.mean()),
                "mean_latency_proxy": float(g.mean_latency_proxy.mean()),
                "mean_handover_rate": float(g.mean_handover_rate.mean()),
                "total_handovers_mean": float(g.total_handovers.mean()),
            })
        pd.DataFrame(summary_rows).to_csv(out_dir / "global_ablation_summary.csv", index=False)
    return df


def run_model_mismatch_sensitivity(base_cfg: SimConfig, seeds: Iterable[int], steps: int, out_dir: Path | None = None):
    """Evaluate stable-global under fixed planner/evaluator model mismatch on shared traces.

    Besides outcome metrics, report the mean absolute change in the planner's internal
    predicted-rate matrix versus the evaluator-matched oracle planner. This distinguishes
    a genuine score perturbation from a coincidentally unchanged discrete assignment.
    """
    rows = []
    scenarios = [
        ("oracle", False, base_cfg.global_model_pathloss_exp, 0.0, base_cfg.global_model_rate_scale),
        ("mild_mismatch", True, 2.45, -0.50, 7.90),
        ("moderate_mismatch", True, 2.50, -0.75, 7.80),
        ("strong_mismatch", True, 2.60, -1.20, 7.60),
    ]
    for seed in seeds:
        cfg_base = SimConfig(**{**base_cfg.__dict__, "seed": int(seed), "steps": int(steps)})
        trace = generate_trace(cfg_base, seed=seed, steps=steps)
        baseline = run_policy_on_trace(cfg_base, trace, "load_aware", policy_seed=26_000 + int(seed))
        base_row = summarize_metrics(baseline, "load_aware_reference", seed, cfg_base.disturbance_sigma)

        oracle_cfg = SimConfig(**{
            **cfg_base.__dict__,
            "global_model_pathloss_exp": float(base_cfg.global_model_pathloss_exp),
            "global_model_snr_bias_db": 0.0,
            "global_model_rate_scale": float(base_cfg.global_model_rate_scale),
        })
        oracle_sim = DistMobSim(oracle_cfg, trace_data=trace, policy_seed=26_000 + int(seed))
        oracle_scores = []
        for t in range(steps):
            oracle_sim._load_trace_step(t)
            oracle_scores.append(oracle_sim.planner_rate_matrix(use_proxy_model=False))
        oracle_scores = np.asarray(oracle_scores)
        oracle_mean = float(np.mean(np.abs(oracle_scores))) + 1e-9

        for label, use_proxy, pathloss_exp, snr_bias, rate_scale in scenarios:
            cfg = SimConfig(**{
                **cfg_base.__dict__,
                "global_model_pathloss_exp": float(pathloss_exp),
                "global_model_snr_bias_db": float(snr_bias),
                "global_model_rate_scale": float(rate_scale),
            })
            policy = "stable_global" if use_proxy else "stable_global_oracle"
            metrics = run_policy_on_trace(cfg, trace, policy, policy_seed=26_000 + int(seed))

            score_diffs = []
            sim = DistMobSim(cfg, trace_data=trace, policy_seed=26_000 + int(seed))
            for t in range(steps):
                sim._load_trace_step(t)
                planner_scores = sim.planner_rate_matrix(use_proxy_model=use_proxy)
                score_diffs.append(float(np.mean(np.abs(planner_scores - oracle_scores[t]))))

            row = summarize_metrics(metrics, policy, seed, cfg.disturbance_sigma)
            row.update({
                "model": label,
                "planner_pathloss_exp": pathloss_exp,
                "planner_snr_bias_db": snr_bias,
                "planner_rate_scale": rate_scale,
                "planner_rate_mae_vs_oracle": float(np.mean(score_diffs)),
                "planner_rate_mae_pct_vs_oracle": float(100.0 * np.mean(score_diffs) / oracle_mean),
            })
            rows.append(row)

        base_row.update({
            "model": "load_aware_reference",
            "planner_pathloss_exp": np.nan,
            "planner_snr_bias_db": np.nan,
            "planner_rate_scale": np.nan,
            "planner_rate_mae_vs_oracle": np.nan,
            "planner_rate_mae_pct_vs_oracle": np.nan,
        })
        rows.append(base_row)
    df = pd.DataFrame(rows).sort_values(["model", "seed"]).reset_index(drop=True)
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_dir / "model_mismatch_sensitivity.csv", index=False)
    return df


def run_disturbance_sweep(base_cfg: SimConfig, sigma_values: Iterable[float], policies: Iterable[str], seeds: Iterable[int], steps: int, out_dir: Path | None = None):
    rows = []
    for sigma in sigma_values:
        for seed in seeds:
            cfg = SimConfig(**{**base_cfg.__dict__, "disturbance_sigma": float(sigma), "seed": int(seed), "steps": int(steps)})
            trace = generate_trace(cfg, seed=seed, steps=steps)
            for policy in policies:
                metrics = run_policy_on_trace(cfg, trace, policy, policy_seed=30_000 + seed)
                rows.append(summarize_metrics(metrics, policy, seed, sigma))
    df = pd.DataFrame(rows).sort_values(["disturbance_sigma", "policy", "seed"]).reset_index(drop=True)
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_dir / "disturbance_sweep.csv", index=False)
    return df


def run_joint_stress_grid(base_cfg: SimConfig, sigma_values: Iterable[float], speed_values: Iterable[float], seeds: Iterable[int], policies: Iterable[str], steps: int, out_dir: Path | None = None):
    rows = []
    for sigma in sigma_values:
        for speed in speed_values:
            for seed in seeds:
                cfg = SimConfig(**{**base_cfg.__dict__, "disturbance_sigma": float(sigma), "max_speed": float(speed), "seed": int(seed), "steps": int(steps)})
                trace = generate_trace(cfg, seed=seed, steps=steps)
                for policy in policies:
                    metrics = run_policy_on_trace(cfg, trace, policy, policy_seed=40_000 + seed)
                    rows.append({"sigma": sigma, "max_speed": speed, **summarize_metrics(metrics, policy, seed, sigma)})
    df = pd.DataFrame(rows).sort_values(["sigma", "max_speed", "policy", "seed"]).reset_index(drop=True)
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_dir / "joint_stress_grid.csv", index=False)
    return df


def run_horizon_sensitivity(base_cfg: SimConfig, horizons: Iterable[int], seeds: Iterable[int], steps: int, out_dir: Path | None = None):
    rows = []
    for horizon in horizons:
        for seed in seeds:
            cfg = SimConfig(**{**base_cfg.__dict__, "prediction_horizon": int(horizon), "seed": int(seed), "steps": int(steps)})
            trace = generate_trace(cfg, seed=seed, steps=steps)
            metrics = run_policy_on_trace(cfg, trace, "darc", policy_seed=50_000 + seed)
            rows.append({"prediction_horizon": horizon, **summarize_metrics(metrics, "darc", seed, cfg.disturbance_sigma)})
    df = pd.DataFrame(rows).sort_values(["prediction_horizon", "seed"]).reset_index(drop=True)
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_dir / "horizon_sensitivity.csv", index=False)
    return df


def run_runtime_benchmark(base_cfg: SimConfig, policies: Iterable[str], trace: Dict[str, np.ndarray], steps: int, repeats: int = 3, out_dir: Path | None = None):
    rows = []
    for policy in policies:
        timings = []
        for rep in range(repeats):
            sim = DistMobSim(base_cfg, trace_data=trace, policy_seed=60_000 + rep)
            t0 = time.perf_counter()
            sim.run(policy=policy, steps=steps)
            timings.append(time.perf_counter() - t0)
        avg = float(np.mean(timings))
        rows.append({
            "policy": policy,
            "mean_runtime_sec": avg,
            "std_runtime_sec": float(np.std(timings, ddof=1)),
            "runtime_ms_per_step": 1000.0 * avg / steps,
            "runtime_ms_per_user_step": 1000.0 * avg / (steps * base_cfg.n_users),
            "steps": int(steps),
            "repeats": int(repeats),
        })
    df = pd.DataFrame(rows).sort_values("mean_runtime_sec").reset_index(drop=True)
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_dir / "runtime_benchmark.csv", index=False)
    return df


def run_scaling_benchmark(base_cfg: SimConfig, scenarios: Iterable[tuple[int, int, int] | tuple[int, int, int, int]], policies: Iterable[str], steps: int = 120, repeats: int = 2, out_dir: Path | None = None):
    rows = []
    for scenario in scenarios:
        if len(scenario) == 3:
            n_users, n_aps, seed = scenario
            scenario_steps = int(steps)
        else:
            n_users, n_aps, seed, scenario_steps = scenario
            scenario_steps = int(scenario_steps)
        cfg = SimConfig(**{**base_cfg.__dict__, "n_users": int(n_users), "n_aps": int(n_aps), "seed": int(seed), "steps": scenario_steps})
        trace = generate_trace(cfg, seed=seed, steps=scenario_steps)
        for policy in policies:
            timings, metric_rows = [], []
            for rep in range(repeats):
                sim = DistMobSim(cfg, trace_data=trace, policy_seed=70_000 + rep)
                t0 = time.perf_counter()
                metrics = sim.run(policy=policy, steps=scenario_steps)
                timings.append(time.perf_counter() - t0)
                metric_rows.append(summarize_metrics(metrics, policy, seed + rep, cfg.disturbance_sigma))
            m = pd.DataFrame(metric_rows)
            avg = float(np.mean(timings))
            rows.append({
                "n_users": n_users,
                "n_aps": n_aps,
                "policy": policy,
                "mean_runtime_sec": avg,
                "std_runtime_sec": float(np.std(timings, ddof=1)),
                "runtime_ms_per_user_step": 1000.0 * avg / (scenario_steps * n_users),
                "served_demand_fraction": float(m.served_demand_fraction.mean()),
                "mean_outage": float(m.mean_outage.mean()),
                "p05_throughput": float(m.p05_throughput.mean()),
                "mean_handover_rate": float(m.mean_handover_rate.mean()),
                "steps": scenario_steps,
                "repeats": repeats,
            })
    df = pd.DataFrame(rows).sort_values(["n_users", "n_aps", "policy"]).reset_index(drop=True)
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_dir / "scaling_benchmark.csv", index=False)
    return df


def export_trace_bundle(trace: Dict[str, np.ndarray], cfg: SimConfig, out_dir: Path, label: str = "heldout_trace") -> Dict[str, Path]:
    data_dir = out_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    npz_path = data_dir / f"{label}.npz"
    np.savez_compressed(npz_path, **{k: np.asarray(v) for k, v in trace.items()})
    meta = {**asdict(cfg), "trace_seed": int(cfg.seed), "description": "Exogenous environment trace; controller observer states are reconstructed online."}
    meta_path = data_dir / f"{label}_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {"npz": npz_path, "meta": meta_path}
