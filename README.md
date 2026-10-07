# DISTMOB

## Disturbance-Aware Mobility Control for Mobile Networks

**DISTMOB** is a research-engineering simulation project that studies a practical question:

> **When a person is moving through a wireless network, how should the system decide which Access Point (AP) they should be connected to when signal quality, congestion, and disturbances keep changing?**

In everyday life, this is the problem behind situations such as:

- Walking through a building while your phone moves from one Wi-Fi AP to another.
- Moving through a crowded area where one AP becomes overloaded.
- Staying connected while the quality of the current AP deteriorates.
- Avoiding unnecessary AP switches that can interrupt connectivity.
- Making a decision not only based on **what is best right now**, but also on **what is likely to happen a few moments from now**.

DISTMOB models this as a dynamic AP-association and control problem and compares several increasingly sophisticated strategies, from simple signal-based rules to predictive control, global optimization, supervisory safety logic, and a lightweight reinforcement-learning baseline.

---

# 1. The Problem — In Everyday Terms

Imagine a person walking through a large building:

```text
                 AP 1
                  📡
                 /   \
                /     \
       👤 → → → → → → 👤
                         \
                          \
                           📡
                          AP 2
```

At the beginning, AP 1 may be the best choice.

As the person moves:

- AP 1's signal may weaken.
- AP 2 may become stronger.
- AP 1 may become congested.
- A temporary disturbance may affect either AP.
- Switching too aggressively may cause unnecessary handovers.

So the system continuously faces a decision:

> **Stay with the current AP, or switch to another AP?**

With many users, this becomes more difficult because the decision for one user can affect everyone else through congestion and AP capacity.

DISTMOB therefore treats **AP association as a dynamic control problem** rather than simply choosing the strongest signal.

---

# 2. Where We Started → Where We Reached

The project evolved through several iterations rather than starting with the final controller.

### Starting point

The initial question was simple:

> **Can a disturbance-aware controller make better AP-association decisions than conventional handover rules?**

The first versions focused on local, user-level decisions such as:

- RSSI-based association
- Hysteresis
- Time-to-trigger (TTT)
- Load-aware association
- Disturbance-aware predictive control

During development, several assumptions were challenged.

For example, an early version of the predictive controller did not actually propagate future user mobility correctly. The planner's internal rate model also differed from the evaluator's authoritative model.

Instead of hiding these problems, the project turned them into explicit experiments.

### Where we reached

The final system contains:

- **10 paired random seeds** for robustness analysis
- **6 stress combinations** across disturbance and mobility
- predictive horizon sensitivity experiments
- planner/evaluator model-mismatch experiments
- zero-switch-penalty ablation
- tail-QoS analysis
- statistical significance testing
- runtime benchmarking
- trace-driven replay
- an optional external-trace validation path
- reproducible experiment and report-generation scripts

The project ultimately became less about proving that **one controller always wins** and more about understanding **why a particular policy works, where it fails, and what trade-offs it introduces**.

---

# 3. The Controllers

DISTMOB compares progressively more sophisticated association strategies.

| Controller | Everyday interpretation |
|---|---|
| **RSSI** | "Connect to whichever AP looks strongest right now." |
| **Hysteresis** | "Don't switch unless the new AP is clearly better." |
| **TTT** | "Wait and see whether the new AP remains better." |
| **Load-aware** | "Avoid APs that are already crowded." |
| **DARC-no-observer** | "Use the current disturbance directly." |
| **DARC** | "Estimate disturbance and account for what may happen next." |
| **Robust-DARC** | "Also consider mobility and uncertainty." |
| **Shield-DARC** | "When conditions become risky, behave more conservatively." |
| **Regime orchestrator** | "Change control strategy depending on the current operating regime." |
| **Stable-global** | "Coordinate all user-AP assignments globally while explicitly penalizing unnecessary switching." |
| **Q-learning** | "Learn association decisions from interaction with the simulated environment." |

The central distinction is:

```text
Simple rules
     ↓
Local awareness
     ↓
Prediction
     ↓
Robustness / safety
     ↓
Global coordination
     ↓
Supervisory control
```

---

# 4. What the Final System Actually Optimizes

DISTMOB does not define success as simply getting the highest instantaneous throughput.

The system evaluates multiple objectives:

### Quality of service

- Served-demand fraction
- Mean satisfaction
- P05 satisfaction
- P05 throughput
- Outage

### Network fairness

- Jain's fairness index

### Stability

- Handover rate
- Total handovers

### Responsiveness

- Latency proxy

This matters because a controller can improve one metric while making another worse.

For example:

> A policy that constantly switches users between APs might find slightly better short-term connections but create excessive mobility churn.

DISTMOB therefore treats **QoS and stability as competing objectives**.

---

# 5. Primary Result — 10 Paired Seeds

The main robustness comparison uses **10 paired random seeds** rather than relying on a single simulation run.

### Stable-global vs Load-aware

| Metric | Load-aware | Stable-global | Interpretation |
|---|---:|---:|---|
| Served-demand fraction | **0.9275** | **0.9482** | +2.07 percentage points |
| Outage | **0.2602** | **0.1692** | ↓ ~35% |
| Jain fairness | **0.7757** | **0.8674** | Higher fairness |
| Latency proxy | **1.8111** | **1.3416** | ↓ ~26% |
| Handover rate | **0.2420** | **0.00142** | Dramatically lower |
| P05 throughput | **3.4521 Mbps** | **3.0335 Mbps** | ↓ 12.1% |

### What this means in everyday language

The stable-global policy behaves more like a **careful traffic manager**.

Instead of constantly chasing whichever AP looks slightly better, it coordinates assignments across users and penalizes unnecessary switching.

The result is:

- fewer users falling into outage,
- more balanced resource usage,
- lower latency proxy,
- dramatically less AP switching,

but with a measurable cost:

> **The bottom 5% of throughput becomes worse.**

That trade-off is deliberately reported rather than hidden.

---

# 6. The Most Interesting Result: Stability Has a Cost — and a Cause

One important question was:

> **Why does stable-global produce such low handover rates?**

Was it genuinely because of the stability term, or was the simulator somehow making users naturally stable?

To answer this, the project removes the explicit switch penalty.

### Zero-switch-penalty ablation

```text
Stable-global
    ↓
Switch penalty ON
    ↓
~4.4 mean handovers


Stable-global-no-switch
    ↓
Switch penalty OFF
    ↓
~109.9 mean handovers
```

That's approximately a **25× increase in mean handovers**.

Interestingly, removing the penalty improves some QoS metrics.

This gives an important causal interpretation:

> **The low-churn behavior is not simply a property of the environment. It is produced by the stability regularization in the optimization objective.**

In everyday terms:

> If you tell the system, **"Don't unnecessarily move people between APs,"** it actually learns/optimizes for staying put. If you remove that rule, it becomes much more willing to chase better instantaneous opportunities.

---

# 7. Planner vs Evaluator — Avoiding an Unrealistic "Oracle"

Another important methodological question was:

> **Does the global planner know exactly what the evaluator will use to score the network?**

If yes, the planner effectively gets privileged information.

To avoid hiding this issue, DISTMOB deliberately uses an **imperfect fixed planner proxy**:

```text
Planner model
pathloss exponent = 2.60
SNR bias          = -1.20 dB
rate scale        = 7.60
        ↓
makes decisions
        ↓
Authoritative evaluator
        ↓
measures actual outcome
```

The project also includes:

### `stable_global_oracle`

This version gives the planner the evaluator-matched model and is used as a sensitivity/control condition.

The final release therefore distinguishes between:

- normal planner assumptions,
- oracle planner assumptions,
- model mismatch,
- actual evaluated performance.

This makes the global-planner results more defensible.

---

# 8. Model-Mismatch Experiment

The project explicitly tests what happens when the planner's internal model becomes increasingly different from the evaluator.

The purpose is not to claim:

> "The planner is perfect."

Instead, the question is:

> **Does the approach remain useful when its internal model is wrong?**

The experiment includes mild, moderate and strong mismatch conditions and tracks the resulting internal planner-score drift.

This is important because real engineering systems rarely have a perfect model of the environment.

---

# 9. Predictive Control

One of the lessons from the early versions was that simply calling something "predictive" is not enough.

The corrected DARC implementation actually propagates future user state when evaluating future decisions.

Conceptually:

```text
Current state
     │
     ▼
Predict user movement
     │
     ▼
Estimate future AP conditions
     │
     ▼
Estimate future rate / risk
     │
     ▼
Choose association
```

The horizon-sensitivity experiment evaluates different prediction horizons.

In the tested configuration, increasing the horizon from **1 → 12 steps** reduced outage from approximately:

```text
0.465  →  0.210
```

while increasing served-demand fraction from approximately:

```text
0.812  →  0.951
```

This supports the intuition that, under the stated simulation model, giving the controller more temporal context can improve its decisions.

---

# 10. Stress Testing

The system is also evaluated across combinations of:

- disturbance volatility
- maximum user speed
- random seeds

The stress grid covers **6 disturbance/mobility combinations**:

```text
                 Maximum speed
              1.2    2.3    2.8
           ┌──────┬──────┬──────┐
σ = 0.8    │  ✓   │  ✓   │  ✓   │
           ├──────┼──────┼──────┤
σ = 3.2    │  ✓   │  ✓   │  ✓   │
           └──────┴──────┴──────┘
```

This asks a more useful question than:

> "Does the controller work on one scenario?"

Instead:

> **How does the controller behave when the environment becomes more difficult?**

---

# 11. Statistical Validation

The project does not rely only on visually comparing averages.

The seed-level analysis includes:

- paired t-test
- Wilcoxon signed-rank test
- Cohen's \(d_z\)
- bootstrap confidence intervals
- Holm multiple-comparison correction

An important result is that:

> **The served-demand improvement of stable-global over load-aware is positive but not statistically significant after Holm correction.**

This is an important limitation of the result — and deliberately remains in the README.

The project therefore does **not** make the claim:

> "Stable-global statistically dominates every baseline."

Instead, the defensible claim is narrower:

> **Stable-global consistently improves several important metrics under the tested model, particularly outage, fairness, latency proxy and handover stability, while introducing a measurable P05-throughput trade-off.**

---

# 12. External-Trace Extension

The core benchmark intentionally remains **synthetic and frozen**.

This is deliberate.

A controlled simulation allows different controllers to experience the **same underlying trajectory**, making counterfactual comparison cleaner.

As an optional external-validation path, the repository documents the **X-Fi public Wi-Fi association dataset**, which contains:

- GPS traces
- Wi-Fi association attempts
- signal measurements
- TCP performance fields

across:

- Paris
- Bologna
- Macao
- Los Angeles

The external dataset is **not copied into this repository**. Users should obtain it from the original authors and follow the associated citation and usage terms.

Source: Yang et al., *Revisiting WiFi offloading in the wild for V2I applications* (Computer Networks, 2022).

---

# 13. What I Learned From the Project

The most important outcome wasn't simply finding a controller with better numbers.

The project went through a cycle of:

```text
Hypothesis
    ↓
Implementation
    ↓
Experiment
    ↓
Unexpected result
    ↓
Investigate assumption
    ↓
Fix / redesign experiment
    ↓
Ablation / validation
    ↓
More defensible conclusion
```

Several examples:

### 1. "Predictive" must actually predict

An early implementation discounted future disturbance but did not properly propagate future mobility.

**Lesson:** a label is not evidence of a mechanism.

### 2. A strong baseline can beat a complicated controller

Instead of hiding this, the project made the comparison part of the research story.

**Lesson:** complexity is not automatically an advantage.

### 3. Optimization objectives create behavior

The zero-switch ablation showed that stability regularization directly drives the low-churn behavior.

**Lesson:** understand what the objective function is incentivizing.

### 4. More metrics reveal more truth

Average throughput alone would have hidden important differences.

**Lesson:** evaluate the distribution and tail behavior, not only the mean.

### 5. Model mismatch matters

The planner and evaluator should not silently assume perfect agreement.

**Lesson:** engineering systems operate with imperfect models.

---

# 14. Technical Architecture

```text
                    DISTMOB
                       │
          ┌────────────┴────────────┐
          │                         │
       Mobility                 Disturbance
       Process                    Process
          │                         │
          └────────────┬────────────┘
                       │
                 Network State
                       │
              ┌────────┴────────┐
              │                 │
         Local Policies    Global Planner
              │                 │
              └────────┬────────┘
                       │
              Supervisory Control
                       │
                       ▼
                AP Association
                       │
                       ▼
                  Evaluation
                       │
          ┌────────────┼────────────┐
          │            │            │
         QoS        Fairness      Stability
          │            │            │
          └────────────┴────────────┘
                       │
                       ▼
             Statistical Analysis
```

---

# 15. Repository Structure

```text
DISTMOB/
├── distmob/
│   ├── __init__.py
│   ├── config.py
│   ├── simulator.py
│   └── experiment.py
│
├── scripts/
│   ├── run_all_experiments.py
│   ├── recompute_review_fixes.py
│   └── build_report.py
│
├── tests/
├── external_trace/
│   └── test_distmob.py
│
├── data/
├── results/
├── figures/
├── report/
│
├── requirements.txt
├── RESULTS_SUMMARY.md
├── CHANGELOG.md
├── FINAL_AUDIT.md
├── SOP_FRAMING.md
└── README.md
```

---

# 16. Reproduce the Experiments

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run the complete experiment suite:

```bash
python scripts/run_all_experiments.py
```

Build the report:

```bash
python scripts/build_report.py
```

Run tests:

```bash
pytest -q
```

For a faster reviewer-focused refresh when the main release results already exist:

```bash
python scripts/recompute_review_fixes.py
python scripts/build_report.py
pytest -q
```

---

# 17. Scientific Scope and Limitations

DISTMOB is a **synthetic comparative control study**.

It is **not**:

- a packet-level 4G/5G simulator,
- a complete 3GPP network simulator,
- field-validation evidence,
- a claim of universal controller superiority.

The model does not attempt to reproduce every detail of a production cellular/Wi-Fi stack such as full packet scheduling, detailed interference/fading, MCS selection, queue dynamics, or real handover signaling.

The strongest defensible conclusion is narrower:

> **Under the stated simulation model, stable-global improves outage, fairness, latency proxy and mobility stability, while retaining the outage/fairness advantage under the tested planner/evaluator mismatch conditions.**

The project also documents a real downside:

> **P05 throughput decreases by 12.1%, and served-demand improvement is not statistically significant at the seed level.**

These trade-offs are part of the result, not something removed from it.

---

# 18. Final Takeaway

DISTMOB started as a question about **whether disturbance-aware AP association could outperform conventional handover rules**.

It evolved into a broader study of:

> **How should a network make association decisions when users move, APs become congested, disturbances change over time, models are imperfect, and switching itself has a cost?**

The final system combines:

- predictive control,
- robustness and safety mechanisms,
- global constrained assignment,
- supervisory regime control,
- reinforcement-learning baseline,
- controlled simulation,
- statistical testing,
- ablation studies,
- model-mismatch analysis,
- and reproducible experimentation.

The most valuable outcome is not:

> **"This algorithm always wins."**

It is:

> **"Here is a reproducible control system, here is how its assumptions were tested, here is where it performs well, here is where it loses, and here is evidence explaining why."**

That is the engineering and research question DISTMOB is designed to answer.
