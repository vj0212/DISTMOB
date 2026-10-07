from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SimConfig:
    """Authoritative configuration for the DISTMOB simulation and experiments."""

    seed: int = 11
    grid_size: float = 120.0
    n_aps: int = 6
    n_users: int = 24
    steps: int = 240
    dt: float = 1.0

    # Mobility
    noise_std: float = 0.18
    max_speed: float = 2.3

    # Radio / service model
    base_snr_db: float = 40.0
    pathloss_exp: float = 2.35
    ap_bias_span: float = 0.32
    load_penalty_db: float = 0.45
    capacity_per_ap: float = 24.0
    rate_scale: float = 8.0
    max_potential_rate: float = 34.0
    capacity_load_factor: float = 0.09
    outage_thr_mbps: float = 3.0

    # Disturbance process
    disturbance_ar: float = 0.90
    disturbance_sigma: float = 2.10
    disturbance_clip: float = 15.0
    global_burst_prob: float = 0.06
    local_burst_prob: float = 0.045
    global_burst_decay: float = 0.93
    global_burst_scale_low: float = 4.0
    global_burst_scale_high: float = 9.0
    local_burst_scale_low: float = 6.0
    local_burst_scale_high: float = 11.0

    # Observer
    observer_alpha: float = 0.24
    volatility_beta: float = 0.82

    # Handover / classical baselines
    hysteresis_db: float = 1.8
    ttt_trigger_steps: int = 3
    handover_cost: float = 1.25

    # Predictive controller
    prediction_horizon: int = 6
    disturbance_weight: float = 0.50
    demand_weight: float = 0.65
    switch_weight: float = 1.0
    robust_mobility_weight: float = 0.09
    robust_uncertainty_weight: float = 0.20
    safe_uncertainty_weight: float = 0.27
    safe_switch_scale: float = 1.45
    safe_inertia_weight: float = 0.12

    # Supervisory regime controller
    regime_risk_scale: float = 0.50
    regime_risk_offset: float = 0.95
    regime_mobility_threshold: float = 0.60
    regime_hysteresis: float = 0.12
    regime_safe_margin: float = 1.05
    regime_robust_margin: float = 2.10

    # Stable-global assignment
    global_switch_weight: float = 1.15
    global_served_weight: float = 1.00
    global_shortfall_weight: float = 0.80
    global_risk_weight: float = 0.15
    global_mobility_weight: float = 0.03

    # Deliberately imperfect planner-side service model. The evaluator uses the true
    # radio/service parameters above; stable-global uses this proxy model. Values are
    # fixed model-mismatch assumptions, not fitted to any outcome.
    global_model_pathloss_exp: float = 2.60
    global_model_snr_bias_db: float = -1.20
    global_model_rate_scale: float = 7.60
    global_model_max_potential_rate: float = 33.0
    global_model_capacity_load_factor: float = 0.10
    global_min_load_fraction: float = 0.0
    global_max_load_fraction: float = 1.5

    # Tabular RL baseline (kept explicitly as a lightweight baseline)
    q_learning_alpha: float = 0.25
    q_learning_gamma: float = 0.90
    q_learning_epsilon: float = 0.10
    q_learning_epsilon_min: float = 0.02
    q_learning_epsilon_decay: float = 0.995
    q_state_bins: int = 4

    trace_path: Optional[str] = None
