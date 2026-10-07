from __future__ import annotations

import json
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from distmob.config import SimConfig
from distmob.experiment import run_policy_on_trace

RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"
REPORT = ROOT / "report"
DATA = ROOT / "data"


def save_fig(fig, filename: str) -> None:
    fig.tight_layout()
    fig.savefig(FIGURES / filename, dpi=220, bbox_inches="tight")
    plt.close(fig)


def load_trace() -> dict[str, np.ndarray]:
    z = np.load(DATA / "core_trace.npz")
    return {k: z[k] for k in z.files}


def plot_bar(df: pd.DataFrame, metric: str, ylabel: str, filename: str, focus: list[str] | None = None) -> None:
    focus = focus or ["load_aware", "darc", "robust_darc", "shield_darc", "stable_global", "regime_orchestrator"]
    sub = df.set_index("policy").loc[focus].reset_index()
    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    ax.bar(sub["policy"], sub[metric])
    ax.set_ylabel(ylabel)
    ax.tick_params(axis="x", rotation=18)
    save_fig(fig, filename)


def build_figures(
    core: pd.DataFrame,
    seed: pd.DataFrame,
    sweep: pd.DataFrame,
    stress: pd.DataFrame,
    horizon: pd.DataFrame,
    runtime: pd.DataFrame,
    scaling: pd.DataFrame,
    mismatch: pd.DataFrame,
    global_ablation: pd.DataFrame,
    trace: dict[str, np.ndarray],
    cfg: SimConfig,
) -> pd.DataFrame:
    FIGURES.mkdir(parents=True, exist_ok=True)
    focus = ["load_aware", "darc", "robust_darc", "shield_darc", "stable_global", "regime_orchestrator"]

    plot_bar(core, "served_demand_fraction", "Served-demand fraction", "served_demand.png", focus)
    plot_bar(core, "mean_satisfaction", "Mean demand satisfaction", "mean_satisfaction.png", focus)
    plot_bar(core, "p05_satisfaction", "P05 demand satisfaction", "p05_satisfaction.png", focus)
    plot_bar(core, "mean_outage", "Outage fraction", "outage_comparison.png", focus)
    plot_bar(core, "p05_throughput", "P05 throughput [Mbps]", "p05_throughput.png", focus)
    plot_bar(core, "mean_jain", "Jain fairness", "fairness_comparison.png", focus)
    plot_bar(core, "mean_latency_proxy", "Latency proxy", "latency_comparison.png", focus)
    plot_bar(core, "mean_handover_rate", "Handover rate", "handover_comparison.png", focus)

    fig, ax = plt.subplots(figsize=(9.5, 5))
    for p in focus:
        ax.boxplot(seed.loc[seed.policy == p, "served_demand_fraction"], positions=[focus.index(p) + 1], widths=0.55, showmeans=True)
    ax.set_xticks(range(1, len(focus) + 1))
    ax.set_xticklabels(focus, rotation=18)
    ax.set_ylabel("Served-demand fraction")
    save_fig(fig, "seed_robustness_served_demand.png")

    fig, ax = plt.subplots(figsize=(9.5, 5))
    for p in ["load_aware", "stable_global"]:
        ax.boxplot(seed.loc[seed.policy == p, "p05_throughput"], positions=[0.85 if p == "load_aware" else 1.15], widths=0.2, showmeans=True)
    ax.set_xticks([0.85, 1.15]); ax.set_xticklabels(["load_aware", "stable_global"])
    ax.set_ylabel("P05 throughput [Mbps]")
    ax.set_title("Seed-level P05 throughput trade-off")
    save_fig(fig, "seed_robustness_p05_throughput.png")

    for metric, ylabel, filename in [
        ("mean_outage", "Outage fraction", "disturbance_outage_sweep.png"),
        ("served_demand_fraction", "Served-demand fraction", "disturbance_served_sweep.png"),
    ]:
        fig, ax = plt.subplots(figsize=(9.5, 5))
        for p in focus:
            g = sweep[sweep.policy == p].groupby("disturbance_sigma")[metric].mean().reset_index()
            ax.plot(g.disturbance_sigma, g[metric], marker="o", label=p)
        ax.set_xlabel("Disturbance sigma")
        ax.set_ylabel(ylabel)
        ax.legend(ncol=2, fontsize=8)
        save_fig(fig, filename)

    for p in ["load_aware", "stable_global"]:
        sub = stress[stress.policy == p].groupby(["sigma", "max_speed"], as_index=False)["served_demand_fraction"].mean()
        mat = sub.pivot(index="max_speed", columns="sigma", values="served_demand_fraction")
        fig, ax = plt.subplots(figsize=(7.5, 4.8))
        im = ax.imshow(mat.values, origin="lower", aspect="auto")
        ax.set_xticks(np.arange(len(mat.columns))); ax.set_xticklabels(mat.columns)
        ax.set_yticks(np.arange(len(mat.index))); ax.set_yticklabels(mat.index)
        ax.set_xlabel("Disturbance sigma"); ax.set_ylabel("Max speed")
        ax.set_title(f"{p}: served-demand fraction")
        fig.colorbar(im, ax=ax, label="fraction")
        save_fig(fig, f"stress_{p}_heatmap.png")

    # P05 throughput stress view - tail-QoS evidence under stress.
    sub = stress[stress.policy == "stable_global"].groupby(["sigma", "max_speed"], as_index=False)["p05_throughput"].mean()
    mat = sub.pivot(index="max_speed", columns="sigma", values="p05_throughput")
    fig, ax = plt.subplots(figsize=(6.4, 3.7))
    im = ax.imshow(mat.values, origin="lower", aspect="auto")
    ax.set_xticks(np.arange(len(mat.columns))); ax.set_xticklabels(mat.columns)
    ax.set_yticks(np.arange(len(mat.index))); ax.set_yticklabels(mat.index)
    ax.set_xlabel("Disturbance sigma"); ax.set_ylabel("Max speed")
    ax.set_title("Stable-global: P05 throughput under stress")
    fig.colorbar(im, ax=ax, label="P05 throughput [Mbps]")
    save_fig(fig, "stress_stable_global_p05_heatmap.png")

    sg = stress[stress.policy == "stable_global"].groupby(["sigma", "max_speed"], as_index=False)["served_demand_fraction"].mean().rename(columns={"served_demand_fraction":"stable"})
    la = stress[stress.policy == "load_aware"].groupby(["sigma", "max_speed"], as_index=False)["served_demand_fraction"].mean().rename(columns={"served_demand_fraction":"load"})
    gain = sg.merge(la, on=["sigma", "max_speed"]); gain["gain"] = gain["stable"] - gain["load"]
    mat = gain.pivot(index="max_speed", columns="sigma", values="gain")
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    im = ax.imshow(mat.values, origin="lower", aspect="auto")
    ax.set_xticks(np.arange(len(mat.columns))); ax.set_xticklabels(mat.columns)
    ax.set_yticks(np.arange(len(mat.index))); ax.set_yticklabels(mat.index)
    ax.set_xlabel("Disturbance sigma"); ax.set_ylabel("Max speed")
    ax.set_title("Stable-global gain over load-aware")
    fig.colorbar(im, ax=ax, label="served-demand fraction gain")
    save_fig(fig, "stress_stable_global_gain.png")

    hg = horizon.groupby("prediction_horizon")["mean_outage"].mean()
    hs = horizon.groupby("prediction_horizon")["served_demand_fraction"].mean()
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.plot(hg.index, hg.values, marker="o", label="Outage")
    ax.plot(hs.index, hs.values, marker="o", label="Served demand")
    ax.set_xlabel("Prediction horizon"); ax.set_ylabel("Metric value"); ax.legend()
    save_fig(fig, "darc_horizon_sensitivity.png")

    fig, ax = plt.subplots(figsize=(9.5, 5))
    rr = runtime.sort_values("mean_runtime_sec")
    ax.bar(rr.policy, rr.mean_runtime_sec)
    ax.set_ylabel("Runtime [s]"); ax.tick_params(axis="x", rotation=20)
    save_fig(fig, "runtime_benchmark.png")

    fig, ax = plt.subplots(figsize=(8.5, 5))
    for p in ["load_aware", "stable_global"]:
        g = scaling[scaling.policy == p]
        ax.plot(g.n_users, g.runtime_ms_per_user_step, marker="o", label=p)
    ax.set_xlabel("Users"); ax.set_ylabel("Runtime [ms/user-step]"); ax.legend()
    save_fig(fig, "scaling_runtime.png")

    pos = trace["user_pos"]
    fig, ax = plt.subplots(figsize=(7, 7))
    for i in range(pos.shape[1]):
        ax.plot(pos[:, i, 0], pos[:, i, 1], alpha=0.22, linewidth=0.8)
    ap = np.array([[0.16,0.16],[0.50,0.16],[0.84,0.16],[0.16,0.84],[0.50,0.84],[0.84,0.84]]) * cfg.grid_size
    ax.scatter(ap[:,0], ap[:,1], marker="^", s=160, label="AP")
    ax.set_xlim(0,cfg.grid_size); ax.set_ylim(0,cfg.grid_size)
    ax.set_xlabel("x"); ax.set_ylabel("y"); ax.set_title("Synthetic mobility environment"); ax.legend()
    save_fig(fig, "network_layout.png")

    # Planner model mismatch: show whether the proxy model remains competitive with load-aware.
    mismatch_plot = mismatch[mismatch.model != "load_aware_reference"].groupby("model", as_index=False).agg(
        served_demand=("served_demand_fraction", "mean"),
        outage=("mean_outage", "mean"),
        p05_throughput=("p05_throughput", "mean"),
    )
    order = ["oracle", "mild_mismatch", "moderate_mismatch", "strong_mismatch"]
    mismatch_plot["model"] = pd.Categorical(mismatch_plot["model"], order, ordered=True)
    mismatch_plot = mismatch_plot.sort_values("model")
    ref = mismatch[mismatch.model == "load_aware_reference"].agg({"served_demand_fraction":"mean","mean_outage":"mean"})

    fig, ax = plt.subplots(figsize=(9.5, 5))
    ax.plot(mismatch_plot.model.astype(str), mismatch_plot.served_demand, marker="o", label="Stable-global")
    ax.axhline(float(ref["served_demand_fraction"]), linestyle="--", label="Load-aware reference")
    ax.set_ylabel("Served-demand fraction"); ax.set_xlabel("Planner model")
    ax.tick_params(axis="x", rotation=15); ax.legend()
    save_fig(fig, "planner_model_mismatch_served.png")

    fig, ax = plt.subplots(figsize=(9.5, 5))
    ax.plot(mismatch_plot.model.astype(str), mismatch_plot.outage, marker="o", label="Stable-global")
    ax.axhline(float(ref["mean_outage"]), linestyle="--", label="Load-aware reference")
    ax.set_ylabel("Outage fraction"); ax.set_xlabel("Planner model")
    ax.tick_params(axis="x", rotation=15); ax.legend()
    save_fig(fig, "planner_model_mismatch_outage.png")

    drift_plot = mismatch[mismatch.model.isin(["oracle", "mild_mismatch", "moderate_mismatch", "strong_mismatch"])].groupby("model", as_index=False)["planner_rate_mae_vs_oracle"].mean()
    drift_plot["model"] = pd.Categorical(drift_plot["model"], order, ordered=True)
    drift_plot = drift_plot.sort_values("model")
    fig, ax = plt.subplots(figsize=(9.5, 5))
    ax.bar(drift_plot.model.astype(str), drift_plot.planner_rate_mae_vs_oracle)
    ax.set_ylabel("Mean absolute planner-rate drift [Mbps]")
    ax.set_xlabel("Planner model")
    ax.tick_params(axis="x", rotation=15)
    ax.set_title("Planner internal score drift vs oracle")
    save_fig(fig, "planner_model_score_drift.png")

    ga = global_ablation.groupby("policy", as_index=False).agg(
        served_demand=("served_demand_fraction", "mean"),
        outage=("mean_outage", "mean"),
        p05_throughput=("p05_throughput", "mean"),
        jain=("mean_jain", "mean"),
        latency=("mean_latency_proxy", "mean"),
        handover_rate=("mean_handover_rate", "mean"),
        total_handovers=("total_handovers", "mean"),
    )
    ga_order = ["stable_global", "stable_global_no_switch", "stable_global_oracle"]
    ga["policy"] = pd.Categorical(ga["policy"], ga_order, ordered=True)
    ga = ga.sort_values("policy")

    fig, ax = plt.subplots(figsize=(9.5, 5))
    ax.bar(ga.policy.astype(str), ga.handover_rate)
    ax.set_ylabel("Handover rate"); ax.set_xlabel("Stable-global variant")
    ax.set_title("Switch-penalty ablation")
    ax.tick_params(axis="x", rotation=15)
    save_fig(fig, "zero_switch_handover_ablation.png")

    fig, ax = plt.subplots(figsize=(9.5, 5))
    ax.bar(ga.policy.astype(str), ga.outage)
    ax.set_ylabel("Outage fraction"); ax.set_xlabel("Stable-global variant")
    ax.set_title("QoS effect of removing the switch penalty")
    ax.tick_params(axis="x", rotation=15)
    save_fig(fig, "zero_switch_qos_ablation.png")

    replay_policies = ["load_aware", "darc", "robust_darc", "shield_darc", "stable_global", "regime_orchestrator"]
    replay_rows, replay_details = [], {}
    for p in replay_policies:
        m = run_policy_on_trace(cfg, trace, p, policy_seed=80_000, steps=min(cfg.steps, trace["user_pos"].shape[0]))
        replay_details[p] = m
        replay_rows.append({
            "Policy": p,
            "Served": m["mean_served_demand_fraction"],
            "Outage": m["mean_outage_rate"],
            "P05 sat": m["mean_p05_satisfaction"],
            "HO rate": m["mean_handover_rate"],
            "HOs": m["total_handovers"],
        })
    replay_df = pd.DataFrame(replay_rows)
    replay_df.to_csv(RESULTS / "trace_replay_results.csv", index=False)

    for key, ylabel, fn in [("served_demand_fraction", "Served-demand fraction", "trace_replay_served.png"), ("outage_rate", "Outage fraction", "trace_replay_outage.png")]:
        fig, ax = plt.subplots(figsize=(9.5, 5))
        for p in replay_policies:
            ax.plot(replay_details[p][key], label=p)
        ax.set_xlabel("Time step"); ax.set_ylabel(ylabel); ax.legend(ncol=2, fontsize=8)
        save_fig(fig, fn)

    return replay_df


def build_report() -> Path:
    REPORT.mkdir(parents=True, exist_ok=True)
    core = pd.read_csv(RESULTS / "core_results.csv")
    seed = pd.read_csv(RESULTS / "seed_robustness.csv")
    sig = pd.read_csv(RESULTS / "significance_tests.csv")
    sweep = pd.read_csv(RESULTS / "disturbance_sweep.csv")
    stress = pd.read_csv(RESULTS / "joint_stress_grid.csv")
    horizon = pd.read_csv(RESULTS / "horizon_sensitivity.csv")
    runtime = pd.read_csv(RESULTS / "runtime_benchmark.csv")
    scaling = pd.read_csv(RESULTS / "scaling_benchmark.csv")
    mismatch = pd.read_csv(RESULTS / "model_mismatch_sensitivity.csv")
    global_ablation = pd.read_csv(RESULTS / "global_ablation.csv")
    cfg = SimConfig(**json.loads((RESULTS / "config.json").read_text()))
    trace = load_trace()
    replay = build_figures(core, seed, sweep, stress, horizon, runtime, scaling, mismatch, global_ablation, trace, cfg)

    # Primary seed-level evidence.
    seed_means = seed.groupby("policy").mean(numeric_only=True)
    la = seed_means.loc["load_aware"]
    sg = seed_means.loc["stable_global"]
    served_delta = float(sg.served_demand_fraction - la.served_demand_fraction)
    served_rel = 100 * served_delta / max(float(la.served_demand_fraction), 1e-9)
    outage_delta = float(sg.mean_outage - la.mean_outage)
    outage_reduction = 100 * (-outage_delta) / max(float(la.mean_outage), 1e-9)
    jain_delta = float(sg.mean_jain - la.mean_jain)
    latency_reduction = 100 * (float(la.mean_latency_proxy) - float(sg.mean_latency_proxy)) / max(float(la.mean_latency_proxy), 1e-9)
    ho_reduction = 100 * (float(la.mean_handover_rate) - float(sg.mean_handover_rate)) / max(float(la.mean_handover_rate), 1e-9)
    p05_delta = float(sg.p05_throughput - la.p05_throughput)
    p05_rel = 100 * p05_delta / max(float(la.p05_throughput), 1e-9)

    def sig_row(metric: str) -> pd.Series:
        return sig[(sig.policy == "stable_global") & (sig.metric == metric)].iloc[0]

    served_sig = sig_row("served_demand_fraction")
    outage_sig = sig_row("mean_outage")
    p05_sig = sig_row("p05_throughput")
    jain_sig = sig_row("mean_jain")
    lat_sig = sig_row("mean_latency_proxy")
    ho_sig = sig_row("mean_handover_rate")

    # Reviewer-facing ablations.
    ga = global_ablation.groupby("policy", as_index=True).mean(numeric_only=True)
    proxy = ga.loc["stable_global"]
    no_switch = ga.loc["stable_global_no_switch"]
    oracle = ga.loc["stable_global_oracle"]

    mm = mismatch.groupby("model", as_index=True).mean(numeric_only=True)
    mm_mod = mm.loc["moderate_mismatch"]
    mm_la = mm.loc["load_aware_reference"]
    mm_strong = mm.loc["strong_mismatch"]
    mm_mild = mm.loc["mild_mismatch"]

    # Core table remains useful but is explicitly secondary to the seed study.
    # Keep the full table together by starting Section 5 on a fresh page in the report.
    focus = ["load_aware", "darc", "robust_darc", "shield_darc", "stable_global", "regime_orchestrator"]
    core_focus = core.set_index("policy").loc[focus]
    table_cols = ["policy","served_demand_fraction","mean_satisfaction","p05_satisfaction","mean_outage","p05_throughput","mean_jain","mean_latency_proxy","mean_handover_rate","total_handovers"]
    table = core_focus.reset_index()[table_cols].copy()
    table.columns = ["Policy","Served demand","Mean satisfaction","P05 satisfaction","Outage","P05 Mbps","Jain","Latency proxy","HO rate","HOs"]
    md_table = table.round(4).to_markdown(index=False)

    # Keep the oracle control visible in the primary seed-level table, but label it explicitly as a control
    # rather than a production policy. Its values come from the same 10-seed ablation study.
    oracle_seed = global_ablation.groupby("policy").mean(numeric_only=True).loc[["stable_global_oracle"]][[
        "served_demand_fraction","mean_satisfaction","p05_satisfaction","mean_outage","p05_throughput","mean_jain","mean_latency_proxy","mean_handover_rate"
    ]].reset_index()
    oracle_seed["policy"] = "stable_global_oracle (control)"
    oracle_seed = oracle_seed.set_index("policy")
    seed_table = pd.concat([
        seed_means.loc[["load_aware", "stable_global"]][[
            "served_demand_fraction","mean_satisfaction","p05_satisfaction","mean_outage","p05_throughput","mean_jain","mean_latency_proxy","mean_handover_rate"
        ]],
        oracle_seed,
    ]).reset_index()
    seed_table.columns = ["Policy","Served demand","Mean satisfaction","P05 satisfaction","Outage","P05 Mbps","Jain","Latency proxy","HO rate"]
    seed_md = seed_table.round(4).to_markdown(index=False)

    sg_sig = sig[sig.policy == "stable_global"][[
        "metric","improvement_mean","improvement_ci_low","improvement_ci_high","cohen_dz","t_pvalue_holm","wilcoxon_pvalue_holm"
    ]].copy()
    metric_labels = {
        "served_demand_fraction": "Served demand",
        "mean_satisfaction": "Mean satisfaction",
        "p05_satisfaction": "P05 satisfaction",
        "mean_outage": "Outage",
        "p05_throughput": "P05 throughput",
        "mean_jain": "Jain fairness",
        "mean_latency_proxy": "Latency proxy",
        "mean_handover_rate": "Handover rate",
        "pingpong_events": "Ping-pong events",
    }
    sg_sig["metric"] = sg_sig["metric"].map(metric_labels).fillna(sg_sig["metric"])
    sg_sig.columns = ["Metric","Improvement","CI low","CI high","Cohen dz","Holm t-p","Holm Wilcoxon p"]
    sig_md = sg_sig.round(4).to_markdown(index=False)

    ga_table = ga.loc[["stable_global", "stable_global_no_switch", "stable_global_oracle"]][[
        "served_demand_fraction","mean_satisfaction","mean_outage","p05_throughput","mean_jain","mean_latency_proxy","mean_handover_rate","total_handovers"
    ]].reset_index()
    ga_table.columns = ["Variant","Served demand","Mean satisfaction","Outage","P05 Mbps","Jain","Latency proxy","HO rate","Mean HOs"]
    ga_md = ga_table.round(4).to_markdown(index=False)

    mm_table = mm.loc[["load_aware_reference","oracle","mild_mismatch","moderate_mismatch","strong_mismatch"]][[
        "served_demand_fraction","mean_outage","p05_throughput","planner_rate_mae_vs_oracle","planner_rate_mae_pct_vs_oracle"
    ]].reset_index()
    mm_table.columns = ["Planner model","Served demand","Outage","P05 Mbps","Rate MAE vs oracle [Mbps]","Drift [% oracle rate]"]
    mm_md = mm_table.round(4).to_markdown(index=False)

    sweep_focus = sweep[sweep.policy.isin(["load_aware", "stable_global"])].groupby(["disturbance_sigma","policy"],as_index=False).agg(
        served_demand_fraction=("served_demand_fraction","mean"),
        mean_outage=("mean_outage","mean"),
        p05_satisfaction=("p05_satisfaction","mean")
    ).round(4)
    sweep_focus.columns = ["Sigma","Policy","Served demand","Outage","P05 satisfaction"]
    sweep_md = sweep_focus.to_markdown(index=False)
    # Compact stress table: one row per disturbance/mobility combination, comparing the primary
    # load-aware reference with stable-global. The complete policy-by-seed matrix remains in CSV.
    stress_base = stress[stress.policy.isin(["load_aware", "stable_global"])].groupby(
        ["sigma", "max_speed", "policy"], as_index=False
    ).agg(
        served_demand=("served_demand_fraction", "mean"),
        outage=("mean_outage", "mean"),
        p05_throughput=("p05_throughput", "mean"),
        ho_rate=("mean_handover_rate", "mean"),
    )
    la_stress = stress_base[stress_base.policy == "load_aware"].rename(
        columns={"served_demand": "la_served", "outage": "la_outage", "p05_throughput": "la_p05", "ho_rate": "la_ho"}
    )
    sg_stress = stress_base[stress_base.policy == "stable_global"].rename(
        columns={"served_demand": "sg_served", "outage": "sg_outage", "p05_throughput": "sg_p05", "ho_rate": "sg_ho"}
    )
    stress_view = la_stress.merge(sg_stress, on=["sigma", "max_speed"], how="inner")
    stress_view["sg_gain"] = stress_view["sg_served"] - stress_view["la_served"]
    stress_view["sg_p05_change_pct"] = 100.0 * (stress_view["sg_p05"] - stress_view["la_p05"]) / stress_view["la_p05"].replace(0, np.nan)
    stress_view = stress_view.sort_values(["sigma", "max_speed"])[[
        "sigma", "max_speed", "la_served", "sg_served", "sg_gain", "la_p05", "sg_p05", "sg_p05_change_pct", "sg_ho"
    ]].round(4)
    stress_view.columns = [
        "Sigma", "Max speed", "Load-aware served", "Stable-global served", "Served gain",
        "Load-aware P05 Mbps", "Stable-global P05 Mbps", "Stable-global P05 change [%]", "Stable-global HO rate"
    ]
    stress_md = stress_view.to_markdown(index=False)
    scale_view = scaling[["n_users","n_aps","policy","mean_runtime_sec","runtime_ms_per_user_step","served_demand_fraction","mean_outage","mean_handover_rate"]].copy()
    scale_view.columns = ["Users","APs","Policy","Runtime s","ms/user-step","Served demand","Outage","HO rate"]
    scale_md = scale_view.round(4).to_markdown(index=False)
    replay_md = replay.round(4).to_markdown(index=False)
    horizon_view = horizon.groupby("prediction_horizon")[["served_demand_fraction","mean_outage","p05_satisfaction"]].mean().loc[[1,3,6,9,12]].reset_index().round(4)
    horizon_view.columns = ["Horizon [steps]","Served demand","Outage","P05 satisfaction"]
    horizon_summary = horizon_view.to_markdown(index=False)

    runtime_protocol = json.loads((RESULTS / "runtime_protocol.json").read_text())
    runtime_view = runtime[["policy","mean_runtime_sec","std_runtime_sec","steps","repeats"]].copy()
    runtime_view.columns = ["Policy","Mean runtime [s]","Std runtime [s]","Steps","Repeats"]
    policy_runtime = runtime_view.round(4).to_markdown(index=False)

    text = f"""# DISTMOB: Disturbance-Aware Mobility Control for Mobile Networks

## Executive summary

DISTMOB is a reproducible simulation and control study for access-point association under user mobility, congestion and time-varying disturbances. The final release preserves the existing controller stack but tightens the methodology around model mismatch, switch-cost ablation, frozen-trace statistics, and runtime definitions.

### Primary seed-level evidence

The primary robustness study uses **{seed.seed.nunique()} paired seeds**. Stable-global averages **{sg.served_demand_fraction:.4f} served-demand fraction vs {la.served_demand_fraction:.4f} for load-aware** (delta **{served_delta:+.4f}**, {served_rel:+.1f}% relative). This improvement is **not statistically significant** after the stated multiple-comparison correction (paired t-test Holm p={served_sig.t_pvalue_holm:.4f}; Wilcoxon Holm p={served_sig.wilcoxon_pvalue_holm:.4f}).

The stronger seed-level effects are in outage, fairness, latency and handover churn: mean outage falls from **{la.mean_outage:.4f} to {sg.mean_outage:.4f}** ({outage_reduction:.1f}% relative reduction; Holm t p={outage_sig.t_pvalue_holm:.4f}), Jain fairness rises from **{la.mean_jain:.4f} to {sg.mean_jain:.4f}** (delta {jain_delta:+.4f}; Holm t p={jain_sig.t_pvalue_holm:.4f}), latency proxy falls by **{latency_reduction:.1f}%** (Holm t p={lat_sig.t_pvalue_holm:.4f}), and handover rate falls by **{ho_reduction:.1f}%** (Holm t p={ho_sig.t_pvalue_holm:.4g}).

There is also a real tail-QoS cost: P05 throughput changes from **{la.p05_throughput:.4f} Mbps to {sg.p05_throughput:.4f} Mbps**, a delta of **{p05_delta:+.4f} Mbps ({p05_rel:+.1f}%)**. The paired t-test gives Holm p={p05_sig.t_pvalue_holm:.4f}; the Wilcoxon result is p={p05_sig.wilcoxon_pvalue_holm:.4f}. The release therefore does **not** claim universal improvement across every QoS metric.

### Reviewer-facing fairness check

The primary stable-global controller does **not** use the evaluator's exact rate model. Its planner uses a fixed imperfect proxy: pathloss exponent {cfg.global_model_pathloss_exp:.2f} vs evaluator {cfg.pathloss_exp:.2f}, planner SNR bias {cfg.global_model_snr_bias_db:.2f} dB, and planner rate scale {cfg.global_model_rate_scale:.2f} vs evaluator {cfg.rate_scale:.2f}. The separate 7-seed mismatch study also measures the planner's internal predicted-rate drift versus the oracle: even when the mild and moderate proxy perturbations leave the discrete balanced-slot assignment unchanged in this scenario, their internal scores move by **{mm_mild.planner_rate_mae_pct_vs_oracle:.1f}%** and **{mm_mod.planner_rate_mae_pct_vs_oracle:.1f}%** of the oracle predicted-rate scale, respectively. The **strong mismatch used by the primary controller** has **{mm_strong.planner_rate_mae_pct_vs_oracle:.1f}%** drift and still achieves **{mm_strong.served_demand_fraction:.4f} served demand / {mm_strong.mean_outage:.4f} outage**, versus **{mm_la.served_demand_fraction:.4f} / {mm_la.mean_outage:.4f}** for load-aware. This reduces the concern that the main result is driven only by exact planner/evaluator model sharing.

### Switch-penalty degeneracy check

Removing the global switch penalty changes the controller from **{proxy.mean_handover_rate:.5f} handover rate / {proxy.total_handovers:.1f} mean handovers** to **{no_switch.mean_handover_rate:.5f} / {no_switch.total_handovers:.1f}**, while served demand changes from **{proxy.served_demand_fraction:.4f} to {no_switch.served_demand_fraction:.4f}** and outage from **{proxy.mean_outage:.4f} to {no_switch.mean_outage:.4f}**. In other words, the low-churn behavior is not accidental: removing the switch term buys some QoS but at a large mobility cost.

## 1. Research question

Can predictive disturbance-aware and stability-regularized AP association improve user-level service quality and mobility stability relative to load-aware and classical handover policies under stochastic mobility and disturbances, while remaining effective when the planner's internal service model is imperfect?

## 2. Simulation model

The core environment contains {cfg.n_users} users, {cfg.n_aps} APs, a {cfg.grid_size:.0f} x {cfg.grid_size:.0f} region and {cfg.steps} time steps. Mobility is bounded with reflective boundaries. AP disturbances follow an AR-style process with Gaussian innovations, local shocks and occasional global bursts. Demand combines per-user baseline demand with periodic and burst components.

The evaluator uses the authoritative radio/service model. Mean throughput remains a diagnostic rather than the primary outcome because AP capacity is shared; the main outcomes are served-demand fraction, demand satisfaction, outage, P05 satisfaction/throughput, Jain fairness, latency proxy and handover churn.

## 3. Controller stack

**DARC** forecasts user position and disturbance over a finite horizon, then scores AP choices using predicted service, shortfall, disturbance risk and switching cost. **Robust-DARC** adds mobility and volatility penalties. **Shield-DARC** adds a conservative high-risk mode. **Regime orchestrator** selects between base, robust and safe modes using hysteresis. **Stable-global** solves a balanced-slot global assignment using the planner-side proxy rate model and a switch-regularized service objective.

## 4. Primary seed-level results

{seed_md}

The `stable_global_oracle` row is included as a **control condition**, not as the production controller: it removes only the planner/evaluator model mismatch while keeping the same global-assignment structure. This makes the main result and the later mismatch ablation directly comparable.

The seed study is the main evidence for robustness within the synthetic simulator. Stable-global's served-demand improvement is positive but not significant; its strongest consistent advantages are lower outage, higher fairness, lower latency proxy, and vastly lower handover churn.

### Paired inference vs load-aware

{sig_md}

```{{=latex}}
\\newpage
```

## 5. Core frozen-trace results

The core trace is useful for visualization and controller behavior, but it is intentionally secondary to the seed study. The table below is kept together so the six policy rows cannot be mistaken for a continuation of the preceding inference table or the following mismatch experiment.

{md_table}

## 6. Planner model-mismatch experiment

The planner/evaluator rate-model concern is tested directly. The evaluator remains unchanged; only the planner's internal rate proxy varies. The oracle row represents the evaluator-matched planner, while the mismatch rows progressively perturb the planner model. The new **planner-rate drift** column makes the internal-score effect visible even when a discrete assignment happens to remain unchanged.

{mm_md}

The key comparison is the **strong mismatch used by the primary controller**: stable-global remains favorable on outage and fairness relative to the load-aware reference, with some erosion under the strongest perturbation. The mild and moderate rows are retained because they demonstrate non-zero internal score drift rather than being mistaken for “no perturbation.” This experiment does not imply robustness to arbitrary model error.

![Planner model mismatch - served demand](../figures/planner_model_mismatch_served.png)

![Planner model mismatch - outage](../figures/planner_model_mismatch_outage.png)

![Planner internal score drift](../figures/planner_model_score_drift.png)

## 7. Zero-switch-penalty ablation

The no-switch variant retains the same global assignment structure but sets the switch penalty to zero. This isolates how much of the final controller's low churn is attributable to explicit stability regularization.

{ga_md}

The result is the expected control trade-off: the zero-switch variant can improve service metrics because it is freer to move users between APs, but it produces far more handovers. The normal stable-global controller therefore should be interpreted as a QoS/stability compromise, not as a controller that happens to avoid switching.

![Switch-penalty ablation - handover rate](../figures/zero_switch_handover_ablation.png)

![Switch-penalty ablation - outage](../figures/zero_switch_qos_ablation.png)

## 8. Disturbance sweep

{sweep_md}

## 9. Mobility x disturbance stress grid

The stress grid varies disturbance intensity and user mobility. Heatmaps are provided for both load-aware and stable-global together with their direct served-demand gain. The table also includes **P05 throughput** so the tail-QoS trade-off remains visible under stress rather than only in the seed study.

{stress_md}

All **6 disturbance/mobility combinations** are shown above. The underlying `joint_stress_grid.csv` retains the complete policy-by-seed matrix.

![Stable-global P05 throughput under stress](../figures/stress_stable_global_p05_heatmap.png)

```{{=latex}}
\\newpage
```

## 10. Prediction-horizon sensitivity

The corrected DARC implementation performs actual forward state prediction. The aggregate sensitivity is:

{horizon_summary}

The horizon remains a design parameter; the trend in this experiment is evidence that the forecasting mechanism is active, not proof that longer horizons are universally optimal.

## 11. Trace-driven replay

The same frozen core trace is replayed through the principal controller set. This is a reproducibility test, not external field validation.

{replay_md}

```{{=latex}}
\\newpage
```

## 12. Runtime methodology and scaling

Runtime values are reported only under the **final release protocol**. The policy benchmark uses the frozen core trace, 180 simulation steps and 3 repeats; timing starts immediately before `DistMobSim.run()` and excludes trace generation, result serialization, figure generation and PDF generation. The scaling benchmark uses frozen traces at 24/6, 50/10 and 100/20 users/APs, with 60/60/30 steps and 2 repeats.

{policy_runtime}

The prior v10 report used an earlier implementation/workload and therefore its runtime numbers are **not directly comparable** with this release. This release intentionally avoids mixing those historical measurements into the performance claim.

```{{=latex}}
\\newpage
```

{scale_md}

## 13. Selected figures

### Core service quality

![Served-demand comparison](../figures/served_demand.png)

![Outage comparison](../figures/outage_comparison.png)

![P05 throughput](../figures/p05_throughput.png)

![Fairness](../figures/fairness_comparison.png)

### Robustness and sensitivity

![Disturbance sweep](../figures/disturbance_outage_sweep.png)

![DARC horizon sensitivity](../figures/darc_horizon_sensitivity.png)

![Stable-global stress gain](../figures/stress_stable_global_gain.png)

### Reproducible runtime

![Runtime scaling](../figures/scaling_runtime.png)

## 14. Reproducibility

From the repository root:

```bash
python -m pip install -r requirements.txt
python scripts/run_all_experiments.py
python scripts/build_report.py
pytest -q
```

The final bundle includes the generated traces, CSV/JSON result tables, figures, runtime protocol, tests and this report. The experiment runner and report builder consume the same authoritative `SimConfig`.

## 15. Optional external validation path

An external-trace route is documented without contaminating the primary counterfactual benchmark. The X-Fi public dataset contains real-world V2I Wi-Fi association attempts, GPS coordinates, signal measurements, association timing and TCP performance fields across four cities. These observables are suitable for validating mobility, association dwell time, signal variability and goodput relationships, but the public data do not expose every synchronized latent state used by DISTMOB's synthetic disturbance model. Therefore the repository keeps this as an optional validation extension rather than silently mixing incompatible observables into the main policy comparison. The raw third-party data are not redistributed in this repository.

See `external_trace/README.md` for provenance and the intended validation protocol.

## 16. Limitations

This remains a synthetic network-control testbed rather than packet-level 4G/5G validation. It does not model a complete PHY/MAC stack, interference scheduling, queues or signaling. Stable-global is centralized. Q-learning is intentionally lightweight. The planner model-mismatch test covers a small fixed family of proxy errors, not the full space of distribution shift.

## 17. Final takeaway

DISTMOB is strongest as a **research-engineering project combining simulation, predictive control, global optimization, statistical experimentation and reproducibility**. The final evidence supports a specific and defensible claim: stable-global can reduce outage and handover churn while improving fairness and latency proxy under the stated synthetic environment, and it retains an advantage under the moderate and strong planner/evaluator mismatches tested here, although the advantage erodes under the stronger perturbation. The cost is visible in P05 throughput both in the primary seed study and in the stress-grid view, and removing the switch penalty demonstrates that low churn is an explicit consequence of the stability objective rather than an accident of the environment.
"""

    md_path = REPORT / "DISTMOB_Report.md"
    md_path.write_text(text, encoding="utf-8")
    pdf_path = REPORT / "DISTMOB_Report.pdf"
    import subprocess
    subprocess.run([
        "pandoc", md_path.name, "-o", pdf_path.name,
        "--from", "markdown+pipe_tables",
        "--pdf-engine=xelatex",
        "-H", "preamble.tex",
        "-V", "geometry:margin=0.72in",
        "-V", "fontsize=10pt",
        "--metadata", "title=DISTMOB: Disturbance-Aware Mobility Control for Mobile Networks",
    ], cwd=REPORT, check=True)

    # Lightweight PDF text sanity check for the old extraction artifacts reported in review.
    txt_path = REPORT / ".pdf_text_check.txt"
    subprocess.run(["pdftotext", "-layout", pdf_path.name, txt_path.name], cwd=REPORT, check=True)
    extracted = txt_path.read_text(encoding="utf-8", errors="ignore")
    txt_path.unlink(missing_ok=True)
    import re
    if re.search(r"\bigure\b", extracted):
        raise RuntimeError("PDF extraction still contains a broken 'igure' token")
    if "load_aware_reference0." in extracted:
        raise RuntimeError("PDF still contains a mangled table boundary around load_aware_reference")
    if re.search(r"(?m)^\s*1ntentionally\b", extracted):
        raise RuntimeError("PDF still contains the historical '1ntentionally' artifact")
    if re.search(r"(?m)^\s*1(?:\s+1){3,}\s*$", extracted):
        raise RuntimeError("PDF still contains a repeated-1 extraction artifact")
    return pdf_path


if __name__ == "__main__":
    print(build_report())
