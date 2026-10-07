from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from distmob.config import SimConfig
from distmob.experiment import paired_significance_tests
from distmob.simulator import DistMobSim, generate_trace


def test_trace_reproducibility():
    cfg = SimConfig(seed=7, n_users=8, n_aps=3, steps=30)
    a = generate_trace(cfg, seed=101, steps=30)
    b = generate_trace(cfg, seed=101, steps=30)
    for k in a:
        assert np.array_equal(a[k], b[k])


def test_trace_policy_fairness():
    cfg = SimConfig(seed=7, n_users=8, n_aps=3, steps=30)
    trace = generate_trace(cfg, seed=101, steps=30)
    sim1 = DistMobSim(cfg, trace_data=trace, policy_seed=123)
    sim2 = DistMobSim(cfg, trace_data=trace, policy_seed=123)
    m1 = sim1.run("load_aware", steps=30)
    m2 = sim2.run("load_aware", steps=30)
    assert np.array_equal(m1["user_assoc"], m2["user_assoc"])
    assert np.allclose(m1["user_thr"], m2["user_thr"])


def test_service_metrics_are_consistent():
    cfg = SimConfig(seed=7, n_users=8, n_aps=3, steps=20)
    trace = generate_trace(cfg, seed=102, steps=20)
    metrics = DistMobSim(cfg, trace_data=trace, policy_seed=555).run("stable_global", steps=20)
    assert 0.0 <= metrics["mean_served_demand_fraction"] <= 1.0
    assert 0.0 <= metrics["mean_outage_rate"] <= 1.0
    assert 0.0 <= metrics["mean_jain"] <= 1.0 + 1e-9
    assert metrics["total_handovers"] >= 0


def test_darc_prediction_changes_with_horizon():
    cfg = SimConfig(seed=7, n_users=4, n_aps=2, steps=10, prediction_horizon=1)
    trace = generate_trace(cfg, seed=103, steps=10)
    sim = DistMobSim(cfg, trace_data=trace, policy_seed=1)
    sim._load_trace_step(3)
    sim._observe_trace_disturbance(3)
    cfg2 = SimConfig(**{**cfg.__dict__, "prediction_horizon": 8})
    sim2 = DistMobSim(cfg2, trace_data=trace, policy_seed=1)
    sim2._load_trace_step(3)
    sim2._observe_trace_disturbance(3)
    pos1 = sim._predict_user_position(0, cfg.prediction_horizon)
    pos2 = sim2._predict_user_position(0, cfg2.prediction_horizon)
    d1 = sim._predict_disturbance(0, cfg.prediction_horizon, True)
    d2 = sim2._predict_disturbance(0, cfg2.prediction_horizon, True)
    assert not np.allclose(pos1, pos2) or not np.isclose(d1, d2)


def test_paired_significance_runs():
    import pandas as pd
    df = pd.DataFrame({
        "seed": [1,2,3,1,2,3],
        "policy": ["load_aware"]*3 + ["stable_global"]*3,
        "served_demand_fraction": [0.70,0.71,0.69,0.80,0.79,0.82],
        "mean_outage": [0.30,0.29,0.31,0.20,0.21,0.19],
        "p05_throughput": [2.0,2.1,1.9,3.0,2.9,3.1],
        "mean_jain": [0.80,0.81,0.79,0.90,0.92,0.89],
        "mean_latency_proxy": [4.0,4.1,3.9,3.0,3.05,2.85],
        "mean_handover_rate": [0.05,0.06,0.05,0.04,0.04,0.03],
        "pingpong_events": [20,21,19,10,9,11],
    })
    out = paired_significance_tests(df)
    assert not out.empty


def test_planner_proxy_rate_differs_from_evaluator_rate():
    cfg = SimConfig(seed=7, n_users=4, n_aps=2, steps=10)
    trace = generate_trace(cfg, seed=104, steps=10)
    sim = DistMobSim(cfg, trace_data=trace, policy_seed=2)
    sim._load_trace_step(3)
    sim._observe_trace_disturbance(3)
    future_pos = sim._predict_user_position(0, cfg.prediction_horizon)
    future_dist = sim._predict_disturbance(0, cfg.prediction_horizon, True)
    true_snr = sim._snr_for_state(future_pos, [future_dist])[0, 0]
    proxy_snr = sim._planner_snr_for_state(future_pos, [future_dist])[0, 0]
    assert not np.isclose(true_snr, proxy_snr)


def test_zero_switch_penalty_increases_churn_on_same_trace():
    cfg = SimConfig(seed=7, n_users=8, n_aps=3, steps=60)
    trace = generate_trace(cfg, seed=105, steps=60)
    normal = DistMobSim(cfg, trace_data=trace, policy_seed=3).run("stable_global", 60)
    no_switch = DistMobSim(cfg, trace_data=trace, policy_seed=3).run("stable_global_no_switch", 60)
    assert no_switch["total_handovers"] >= normal["total_handovers"]


def test_report_source_has_core_table_page_break_and_compact_stress_view():
    report = (ROOT / "scripts" / "build_report.py").read_text(encoding="utf-8")
    assert "Core frozen-trace results" in report
    assert "\\\\newpage" in report
    assert "All **6 disturbance/mobility combinations** are shown above." in report
